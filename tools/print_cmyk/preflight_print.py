#!/usr/bin/env python3
"""Check a print PDF before it goes to the shop. Exits 1 if any check fails.

Example:
  python3 preflight_print.py banner.pdf --width-cm 300 --height-cm 100 \
      --master master.png --preview preview.png --viewing-distance-m 5
"""
import argparse
import io
import json
import math
import os
import re
import sys
import zlib

from PIL import Image, ImageCms, ImageOps
import pypdf.filters
from pypdf import PdfReader
from pypdf.errors import PyPdfError, PdfReadError
from pypdf.generic import ContentStream

from print_common import ToolError, find_cmyk_profile, profile_label

PDF_MAX_PT = 14400
SAMPLE_MAX_PIXELS = 2000
COMPARE_MAX_PIXELS = 400
NEGATIVE_CORRELATION = -0.2
VERSION_WORDS = re.compile(
    r"(?<![a-z])(final|draft|copy|new|old|rev\d*|v\d+)(?![a-z])|最終|定稿|修改|最新",
    re.I,
)


class Results:
    def __init__(self):
        self.items = []

    def add(self, status, check, detail):
        self.items.append({"status": status, "check": check, "detail": detail})

    @property
    def failed(self):
        return any(item["status"] == "FAIL" for item in self.items)


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf")
    parser.add_argument("--width-cm", type=float, help="Expected finished width")
    parser.add_argument("--height-cm", type=float, help="Expected finished height")
    parser.add_argument(
        "--scale", type=int, help="Declare a scaled page, e.g. 10 for 1:10"
    )
    parser.add_argument("--min-bleed-cm", type=float, default=1.0)
    parser.add_argument("--min-dpi", type=float, default=100)
    parser.add_argument("--master", help="RGB master for color and negative checks")
    parser.add_argument(
        "--max-delta", type=float, default=30, help="Normal RGB residual"
    )
    parser.add_argument(
        "--color",
        choices=("cmyk", "rgb"),
        help="Expected color. Defaults to what the file declares, otherwise cmyk",
    )
    parser.add_argument("--icc", help="The CMYK profile used to build the PDF")
    parser.add_argument(
        "--preview", help="Write an sRGB preview PNG and a phone-size copy"
    )
    parser.add_argument("--viewing-distance-m", type=float)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def resolve(value):
    return value.get_object() if hasattr(value, "get_object") else value


def box(page, name):
    return [float(value) for value in getattr(page, name)]


def multiply(m, n):
    return [
        m[0] * n[0] + m[1] * n[2],
        m[0] * n[1] + m[1] * n[3],
        m[2] * n[0] + m[3] * n[2],
        m[2] * n[1] + m[3] * n[3],
        m[4] * n[0] + m[5] * n[2] + n[4],
        m[4] * n[1] + m[5] * n[3] + n[5],
    ]


def walk_content(reader, contents, resources, ctm, images, fonts, depth=0):
    if contents is None or depth > 8:
        return
    resources = resolve(resources) or {}
    for font in (resolve(resources.get("/Font")) or {}).values():
        fonts.append(resolve(font))
    xobjects = resolve(resources.get("/XObject")) or {}
    stack = []
    for operands, operator in ContentStream(contents, reader).operations:
        if operator == b"q":
            stack.append(list(ctm))
        elif operator == b"Q" and stack:
            ctm = stack.pop()
        elif operator == b"cm":
            ctm = multiply([float(value) for value in operands], ctm)
        elif operator == b"Do":
            xobject = resolve(xobjects.get(operands[0]))
            if xobject is None:
                continue
            if xobject.get("/Subtype") == "/Image":
                images.append((xobject, list(ctm)))
            elif xobject.get("/Subtype") == "/Form":
                matrix = [
                    float(value) for value in xobject.get("/Matrix", [1, 0, 0, 1, 0, 0])
                ]
                walk_content(
                    reader,
                    xobject,
                    xobject.get("/Resources", resources),
                    multiply(matrix, ctm),
                    images,
                    fonts,
                    depth + 1,
                )


def filters_of(xobject):
    value = resolve(xobject.get("/Filter"))
    if value is None:
        return []
    return (
        [str(value)]
        if not isinstance(value, list)
        else [str(resolve(v)) for v in value]
    )


def color_kind(xobject):
    space = resolve(xobject.get("/ColorSpace"))
    if isinstance(space, list):
        family = str(resolve(space[0]))
        if family == "/ICCBased":
            components = resolve(space[1]).get("/N")
            return {1: "gray", 3: "rgb", 4: "cmyk"}.get(components, "unknown")
        return {"/Indexed": "indexed", "/Separation": "spot", "/DeviceN": "spot"}.get(
            family, "unknown"
        )
    return {"/DeviceCMYK": "cmyk", "/DeviceRGB": "rgb", "/DeviceGray": "gray"}.get(
        str(space), "unknown"
    )


def font_is_embedded(font):
    if font.get("/Subtype") == "/Type3":
        return True
    if font.get("/Subtype") == "/Type0":
        descendants = resolve(font.get("/DescendantFonts")) or []
        return bool(descendants) and all(
            font_is_embedded(resolve(d)) for d in descendants
        )
    descriptor = resolve(font.get("/FontDescriptor"))
    return bool(descriptor) and any(
        key in descriptor for key in ("/FontFile", "/FontFile2", "/FontFile3")
    )


def declared_scale(reader, requested):
    if requested:
        return requested, True
    info = reader.trailer.get("/Info")
    value = resolve(info).get("/PrintScale") if info is not None else None
    if value is None:
        return 1, False
    return int(value), True


def expected_color(reader, requested):
    if requested:
        return requested
    info = reader.trailer.get("/Info")
    declared = resolve(info).get("/PrintColor") if info is not None else None
    return "rgb" if str(declared) == "RGB" else "cmyk"


def check_size(results, page, scale, is_declared, args, label):
    media, trim = box(page, "mediabox"), box(page, "trimbox")
    user_unit = float(page.get("/UserUnit", 1))
    to_cm = user_unit * scale / 72 * 2.54
    width_cm = (trim[2] - trim[0]) * to_cm
    height_cm = (trim[3] - trim[1]) * to_cm
    if max(media[2] - media[0], media[3] - media[1]) > PDF_MAX_PT:
        results.add(
            "WARN",
            f"{label}page limit",
            f"Page exceeds {PDF_MAX_PT} pt; many RIPs reject it.",
        )
    if scale != 1:
        results.add(
            "WARN",
            f"{label}scale",
            f"Page is 1:{scale}. Tell the shop to print at {scale * 100}%, or it comes out 1/{scale} size.",
        )
    if args.width_cm and args.height_cm:
        tolerance = max(0.2, 0.002 * max(args.width_cm, args.height_cm))
        if (
            abs(width_cm - args.width_cm) <= tolerance
            and abs(height_cm - args.height_cm) <= tolerance
        ):
            results.add("PASS", f"{label}size", f"{width_cm:.1f} x {height_cm:.1f} cm")
        elif (
            not is_declared
            and abs(width_cm * 10 - args.width_cm) <= tolerance * 10
            and abs(height_cm * 10 - args.height_cm) <= tolerance * 10
        ):
            results.add(
                "FAIL",
                f"{label}size",
                "Page is 1/10 of the expected size and no scale is declared. "
                "Rebuild at full size, or pass --scale 10 and tell the shop to print at 1000%.",
            )
        else:
            results.add(
                "FAIL",
                f"{label}size",
                f"Got {width_cm:.1f} x {height_cm:.1f} cm, expected {args.width_cm:g} x {args.height_cm:g} cm.",
            )
    else:
        results.add(
            "MANUAL",
            f"{label}size",
            f"Reads {width_cm:.1f} x {height_cm:.1f} cm; confirm it is right.",
        )
    sides = (
        trim[0] - media[0],
        trim[1] - media[1],
        media[2] - trim[2],
        media[3] - trim[3],
    )
    bleed_cm = min(sides) * to_cm
    if bleed_cm + 0.01 < args.min_bleed_cm:
        results.add(
            "WARN",
            f"{label}bleed",
            f"Smallest bleed is {bleed_cm:.2f} cm, below {args.min_bleed_cm:g} cm. Confirm with the shop.",
        )
    else:
        results.add("PASS", f"{label}bleed", f"{bleed_cm:.2f} cm per side")


def check_images(results, images, scale, user_unit, args, label, color):
    if not images:
        results.add(
            "MANUAL",
            f"{label}images",
            "No raster images found; check vector colors in the shop's proof.",
        )
    for index, (xobject, ctm) in enumerate(images, 1):
        name = f"{label}image {index}"
        kind = color_kind(xobject)
        if kind == "rgb" and color == "rgb":
            tagged = isinstance(resolve(xobject.get("/ColorSpace")), list)
            results.add(
                "PASS" if tagged else "WARN",
                f"{name} color",
                "rgb with an embedded profile"
                if tagged
                else "rgb with no embedded profile: the shop's RIP has to guess the color.",
            )
        elif kind == "rgb":
            results.add(
                "FAIL",
                f"{name} color",
                "RGB image in a CMYK print file. Convert it through ICC, "
                "or pass --color rgb if the shop confirms it accepts RGB.",
            )
        elif kind == "cmyk" and color == "rgb":
            results.add(
                "WARN",
                f"{name} color",
                "CMYK image in an RGB job. Confirm how the shop handles it.",
            )
        elif kind in ("cmyk", "gray", "spot"):
            results.add("PASS", f"{name} color", kind)
        else:
            results.add(
                "WARN",
                f"{name} color",
                f"Color space is {kind}; confirm how the shop handles it.",
            )
        decode = resolve(xobject.get("/Decode"))
        if decode and float(resolve(decode[0])) > float(resolve(decode[1])):
            results.add(
                "FAIL",
                f"{name} decode",
                "Inverted /Decode array: this can print as a negative.",
            )
        filters = filters_of(xobject)
        if "/DCTDecode" in filters or "/JPXDecode" in filters:
            results.add(
                "WARN",
                f"{name} compression",
                "Lossy compression can block on large flat areas.",
            )
        width_pt = math.hypot(ctm[0], ctm[1]) * user_unit * scale
        if width_pt > 0:
            dpi = float(xobject.get("/Width")) / (width_pt / 72)
            status = "PASS" if dpi + 0.5 >= args.min_dpi else "WARN"
            results.add(
                status,
                f"{name} resolution",
                f"{dpi:.0f} dpi at finished size (minimum {args.min_dpi:g})",
            )


def check_fonts(results, fonts, label):
    missing = sorted(
        {
            str(font.get("/BaseFont", "unnamed"))
            for font in fonts
            if not font_is_embedded(font)
        }
    )
    if missing:
        results.add("FAIL", f"{label}fonts", "Not embedded: " + ", ".join(missing))
    elif fonts:
        results.add("PASS", f"{label}fonts", "All embedded")


def sample_image(xobject):
    kind = color_kind(xobject)
    if kind not in ("cmyk", "rgb") or filters_of(xobject) != ["/FlateDecode"]:
        return None
    components = 4 if kind == "cmyk" else 3
    if xobject.get("/DecodeParms") or xobject.get("/BitsPerComponent") != 8:
        return None
    raw = getattr(xobject, "_data", None)
    if raw is None:
        return None
    width, height = int(xobject["/Width"]), int(xobject["/Height"])
    step = max(1, math.ceil(max(width, height) / SAMPLE_MAX_PIXELS))
    row_bytes = width * components
    decompressor = zlib.decompressobj()
    buffer = bytearray()
    rows = []
    row_index = 0
    for start in range(0, len(raw), 1 << 20):
        buffer += decompressor.decompress(bytes(raw[start : start + (1 << 20)]))
        while len(buffer) >= row_bytes:
            if row_index % step == 0:
                row = bytes(buffer[:row_bytes])
                rows.append(
                    b"".join(
                        row[x * components : (x + 1) * components]
                        for x in range(0, width, step)
                    )
                )
            del buffer[:row_bytes]
            row_index += 1
    if row_index != height or not rows:
        return None
    sampled_width = math.ceil(width / step)
    mode = "CMYK" if kind == "cmyk" else "RGB"
    return Image.frombytes(mode, (sampled_width, len(rows)), b"".join(rows))


def load_master(path):
    Image.MAX_IMAGE_PIXELS = None
    image = ImageOps.exif_transpose(Image.open(path))
    embedded = image.info.get("icc_profile")
    if image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info:
        rgba = image.convert("RGBA")
        flattened = Image.new("RGB", rgba.size, (255, 255, 255))
        flattened.paste(rgba, mask=rgba.getchannel("A"))
        image = flattened
    else:
        image = image.convert("RGB")
    if embedded:
        try:
            source = ImageCms.ImageCmsProfile(io.BytesIO(embedded))
            image = ImageCms.profileToProfile(
                image, source, ImageCms.createProfile("sRGB"), outputMode="RGB"
            )
        except (OSError, ImageCms.PyCMSError):
            pass
    return image


def correlation(first, second):
    a, b = list(first.getdata()), list(second.getdata())
    mean_a, mean_b = sum(a) / len(a), sum(b) / len(b)
    covariance = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
    spread_a = math.sqrt(sum((x - mean_a) ** 2 for x in a))
    spread_b = math.sqrt(sum((y - mean_b) ** 2 for y in b))
    if spread_a == 0 or spread_b == 0:
        return None
    return covariance / (spread_a * spread_b)


def compare_master(results, preview, page, master_path, max_delta, is_cmyk):
    media, trim = box(page, "mediabox"), box(page, "trimbox")
    master = load_master(master_path)
    media_w, media_h = media[2] - media[0], media[3] - media[1]
    trim_w, trim_h = trim[2] - trim[0], trim[3] - trim[1]
    master_ratio = master.width / master.height
    if abs(master_ratio - trim_w / trim_h) <= abs(master_ratio - media_w / media_h):
        left = (trim[0] - media[0]) / media_w * preview.width
        top = (media[3] - trim[3]) / media_h * preview.height
        right = (trim[2] - media[0]) / media_w * preview.width
        bottom = (media[3] - trim[1]) / media_h * preview.height
        preview = preview.crop((round(left), round(top), round(right), round(bottom)))
    scale = COMPARE_MAX_PIXELS / max(preview.size)
    size = (max(1, round(preview.width * scale)), max(1, round(preview.height * scale)))
    small_preview = preview.resize(size, Image.BOX)
    small_master = master.resize(size, Image.BOX)
    r = correlation(small_preview.convert("L"), small_master.convert("L"))
    if r is not None and r < NEGATIVE_CORRELATION:
        results.add(
            "FAIL",
            "negative check",
            f"Tones run opposite to the master (correlation {r:.2f}): looks like a negative.",
        )
    elif r is None:
        results.add(
            "MANUAL",
            "negative check",
            "The artwork is a flat color; compare the preview by eye.",
        )
    else:
        results.add(
            "PASS", "negative check", f"Tones follow the master (correlation {r:.2f})"
        )
    bands = zip(small_preview.split(), small_master.split())
    differences = [
        abs(x - y)
        for first, second in bands
        for x, y in zip(first.getdata(), second.getdata())
    ]
    differences.sort()
    p95 = differences[int(len(differences) * 0.95)]
    if p95 <= max_delta:
        results.add(
            "PASS",
            "color round trip",
            f"95th percentile RGB difference {p95} (normal up to {max_delta:g})",
        )
    else:
        results.add(
            "WARN",
            "color round trip",
            f"95th percentile RGB difference {p95}, above {max_delta:g}. "
            + (
                "Check --icc matches the build, then whether saturated colors are out of the CMYK gamut."
                if is_cmyk
                else "Check this PDF was built from this master."
            ),
        )


def check_color(results, images, page, args):
    if not (args.master or args.preview):
        results.add(
            "MANUAL",
            "negative check",
            "No --master or --preview given: open the PDF and confirm white is white.",
        )
        return
    candidates = sorted(
        images,
        key=lambda item: int(item[0]["/Width"]) * int(item[0]["/Height"]),
        reverse=True,
    )
    sample = sample_image(candidates[0][0]) if candidates else None
    if sample is None:
        results.add(
            "MANUAL",
            "negative check",
            "This image layout cannot be sampled: compare the shop's proof by eye.",
        )
        return
    is_cmyk = sample.mode == "CMYK"
    if is_cmyk:
        try:
            _, cmyk_profile = find_cmyk_profile(args.icc)
        except ToolError:
            if args.icc:
                raise
            results.add(
                "MANUAL",
                "negative check",
                "No CMYK ICC profile, so color cannot be checked here. "
                "Pass --icc, or compare the shop's proof by eye.",
            )
            return
        results.add("PASS", "color profile", profile_label(cmyk_profile))
        preview = ImageCms.profileToProfile(
            sample, cmyk_profile, ImageCms.createProfile("sRGB"), outputMode="RGB"
        )
    else:
        preview = sample
    if args.preview:
        preview.save(args.preview)
        stem, extension = os.path.splitext(args.preview)
        phone = preview.resize(
            (360, max(1, round(preview.height * 360 / preview.width))), Image.LANCZOS
        )
        phone.save(f"{stem}_phone{extension}")
        results.add(
            "MANUAL",
            "phone-size view",
            f"Look at {stem}_phone{extension}: is the text still readable?",
        )
    if args.master:
        compare_master(results, preview, page, args.master, args.max_delta, is_cmyk)
    else:
        results.add(
            "MANUAL",
            "negative check",
            "No --master given: confirm in the preview that white is white.",
        )


def run(args):
    results = Results()
    if not os.path.isfile(args.pdf):
        raise ToolError(f"PDF not found: {args.pdf}")
    if args.scale is not None and args.scale < 1:
        raise ToolError("--scale must be 1 or greater.")
    if bool(args.width_cm) != bool(args.height_cm):
        raise ToolError("Pass --width-cm and --height-cm together.")
    pypdf.filters.MAX_DECLARED_STREAM_LENGTH = max(
        getattr(pypdf.filters, "MAX_DECLARED_STREAM_LENGTH", 0),
        os.path.getsize(args.pdf),
    )
    try:
        reader = PdfReader(args.pdf, strict=False)
        if reader.is_encrypted:
            results.add(
                "FAIL", "file", "The PDF is encrypted; the shop's RIP may refuse it."
            )
            return results
        pages = list(reader.pages)
    except (PdfReadError, OSError, ValueError) as exc:
        raise ToolError(f"Cannot read PDF: {exc}")
    if not pages:
        raise ToolError("The PDF has no pages.")
    if len(pages) > 1:
        results.add(
            "WARN",
            "pages",
            f"{len(pages)} pages. Confirm the shop expects a multi-page file.",
        )
    if VERSION_WORDS.search(os.path.basename(args.pdf)):
        results.add(
            "WARN",
            "file name",
            "Contains a version word; the wrong file can get picked or printed.",
        )
    scale, is_declared = declared_scale(reader, args.scale)
    color = expected_color(reader, args.color)
    first_images = None
    for number, page in enumerate(pages, 1):
        label = f"page {number} " if len(pages) > 1 else ""
        images, fonts = [], []
        walk_content(
            reader,
            page.get_contents(),
            page.get("/Resources"),
            [1, 0, 0, 1, 0, 0],
            images,
            fonts,
        )
        check_size(results, page, scale, is_declared, args, label)
        check_images(
            results, images, scale, float(page.get("/UserUnit", 1)), args, label, color
        )
        check_fonts(results, fonts, label)
        if number == 1:
            first_images = images
    check_color(results, first_images, pages[0], args)
    if color == "rgb":
        results.add(
            "MANUAL",
            "RGB handoff",
            "Confirm the shop accepts RGB, and ask for a proof: its RIP sets the final color.",
        )
    results.add(
        "MANUAL",
        "QR codes",
        "Scan every QR code on a real phone, from the printed proof if possible.",
    )
    results.add(
        "MANUAL",
        "finishing",
        "Ask how the shop finishes edges: grommets and hemming need a wider safe margin.",
    )
    results.add(
        "MANUAL",
        "internal data",
        "Read every page for costs, customer names and internal codes.",
    )
    if args.viewing_distance_m:
        results.add(
            "MANUAL",
            "text size",
            f"From {args.viewing_distance_m:g} m, letters should be at least {args.viewing_distance_m / 2:.1f} cm tall.",
        )
    return results


def main(argv=None):
    args = parse_args(argv)
    try:
        results = run(args)
    except (ToolError, PyPdfError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(
            json.dumps(
                {"passed": not results.failed, "checks": results.items},
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for item in results.items:
            print(f"[{item['status']:<6}] {item['check']}: {item['detail']}")
        print(
            "RESULT: FAILED"
            if results.failed
            else "RESULT: no automatic failures; finish the MANUAL items"
        )
    return 1 if results.failed else 0


if __name__ == "__main__":
    sys.exit(main())
