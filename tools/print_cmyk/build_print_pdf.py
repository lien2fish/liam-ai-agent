#!/usr/bin/env python3
"""Build a lossless CMYK or RGB PDF for large-format printing from an RGB master.

Examples:
  python3 build_print_pdf.py master.png banner.pdf --width-cm 300 --height-cm 100 --icc shop.icc
  python3 build_print_pdf.py master.png banner.pdf --width-cm 300 --height-cm 100 --color rgb
"""
import argparse
import io
import json
import os
import sys
import tempfile
import zlib

from PIL import Image, ImageCms, ImageOps

from print_common import (
    KNOWN_CMYK_PROFILES,
    ToolError,
    find_cmyk_profile,
    profile_label,
)

PDF_MAX_PT = 14400
ASPECT_TOLERANCE = 0.01
STRIP_ROWS = 256


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="RGB master (PNG recommended)")
    parser.add_argument("output", help="Output .pdf path")
    parser.add_argument("--width-cm", type=float, required=True, help="Finished width")
    parser.add_argument(
        "--height-cm", type=float, required=True, help="Finished height"
    )
    parser.add_argument("--dpi", type=float, default=100, help="Default 100")
    parser.add_argument(
        "--bleed-cm", type=float, default=1.0, help="Per side. Default 1"
    )
    parser.add_argument(
        "--art-includes-bleed",
        action="store_true",
        help="The input already contains the bleed. Otherwise edge pixels are extended.",
    )
    parser.add_argument("--scale", choices=("auto", "1", "10"), default="auto")
    parser.add_argument(
        "--color",
        choices=("cmyk", "rgb"),
        default="cmyk",
        help="Use rgb only if the shop confirms it accepts RGB and converts on its RIP",
    )
    parser.add_argument("--icc", help="CMYK ICC profile, ideally from the print shop")
    parser.add_argument("--max-megapixels", type=float, default=1000)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON")
    return parser.parse_args(argv)


def validate_args(args):
    if args.width_cm <= 0 or args.height_cm <= 0 or args.dpi <= 0:
        raise ToolError("--width-cm, --height-cm and --dpi must be greater than 0.")
    if args.bleed_cm < 0:
        raise ToolError("--bleed-cm cannot be negative.")
    if not args.output.lower().endswith(".pdf"):
        raise ToolError("The output path must end in .pdf.")
    if args.color == "rgb" and args.icc:
        raise ToolError("--icc only applies to CMYK output. Remove it or the --color rgb.")


def to_pixels(cm, dpi):
    return max(1, round(cm / 2.54 * dpi))


def open_master(path, max_pixels, warnings):
    Image.MAX_IMAGE_PIXELS = None
    if not os.path.isfile(path):
        raise ToolError(f"Input not found: {path}")
    try:
        image = Image.open(path)
    except OSError as exc:
        raise ToolError(f"Cannot open image {path}: {exc}")
    if image.width * image.height > max_pixels:
        raise ToolError(
            f"Input has {image.width * image.height / 1e6:.0f} MP, above --max-megapixels."
        )
    if image.mode == "CMYK":
        raise ToolError(
            "The input is already CMYK. Re-export from the RGB master: "
            "every color-space conversion loses color."
        )
    if image.mode.startswith(("I", "F")):
        raise ToolError(
            f"Unsupported image mode {image.mode}. Export an 8-bit RGB PNG."
        )
    embedded_profile = image.info.get("icc_profile")
    image = ImageOps.exif_transpose(image)
    return flatten_to_rgb(image, warnings), embedded_profile


def flatten_to_rgb(image, warnings):
    if image.mode == "P" and "transparency" in image.info:
        image = image.convert("RGBA")
    if image.mode in ("RGBA", "LA", "PA"):
        rgba = image.convert("RGBA")
        if rgba.getchannel("A").getextrema()[0] < 255:
            warnings.append("Transparent areas were flattened onto white.")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def build_transform(embedded_profile, cmyk_profile, warnings):
    source = ImageCms.createProfile("sRGB")
    if embedded_profile:
        try:
            profile = ImageCms.ImageCmsProfile(io.BytesIO(embedded_profile))
            return ImageCms.buildTransform(
                profile, cmyk_profile, "RGB", "CMYK", ImageCms.Intent.PERCEPTUAL
            )
        except (OSError, ImageCms.PyCMSError):
            warnings.append(
                "The embedded profile could not be used; treated the input as sRGB."
            )
    return ImageCms.buildTransform(
        source, cmyk_profile, "RGB", "CMYK", ImageCms.Intent.PERCEPTUAL
    )


def build_srgb_transform(embedded_profile, warnings):
    if not embedded_profile:
        return None
    try:
        profile = ImageCms.ImageCmsProfile(io.BytesIO(embedded_profile))
        return ImageCms.buildTransform(
            profile,
            ImageCms.createProfile("sRGB"),
            "RGB",
            "RGB",
            ImageCms.Intent.PERCEPTUAL,
        )
    except (OSError, ImageCms.PyCMSError):
        warnings.append(
            "The embedded profile could not be used; treated the input as sRGB."
        )
        return None


def extend_edges(art, bleed_px):
    if bleed_px == 0:
        return art
    width, height = art.size
    canvas = Image.new("RGB", (width + 2 * bleed_px, height + 2 * bleed_px))
    canvas.paste(art, (bleed_px, bleed_px))
    canvas.paste(art.crop((0, 0, 1, height)).resize((bleed_px, height)), (0, bleed_px))
    canvas.paste(
        art.crop((width - 1, 0, width, height)).resize((bleed_px, height)),
        (width + bleed_px, bleed_px),
    )
    full_width = canvas.width
    canvas.paste(
        canvas.crop((0, bleed_px, full_width, bleed_px + 1)).resize(
            (full_width, bleed_px)
        ),
        (0, 0),
    )
    canvas.paste(
        canvas.crop((0, bleed_px + height - 1, full_width, bleed_px + height)).resize(
            (full_width, bleed_px)
        ),
        (0, bleed_px + height),
    )
    return canvas


def fit_to_page(master, args, warnings):
    trim_w = to_pixels(args.width_cm, args.dpi)
    trim_h = to_pixels(args.height_cm, args.dpi)
    bleed = round(args.bleed_cm / 2.54 * args.dpi)
    total_w, total_h = trim_w + 2 * bleed, trim_h + 2 * bleed
    if total_w * total_h > args.max_megapixels * 1e6:
        raise ToolError(
            f"Output would be {total_w * total_h / 1e6:.0f} MP, above --max-megapixels. "
            "Lower --dpi for large prints seen from afar."
        )
    if args.art_includes_bleed:
        expected = (args.width_cm + 2 * args.bleed_cm) / (
            args.height_cm + 2 * args.bleed_cm
        )
    else:
        expected = args.width_cm / args.height_cm
    actual = master.width / master.height
    if abs(actual - expected) / expected > ASPECT_TOLERANCE:
        raise ToolError(
            f"Input aspect ratio {actual:.4f} does not match the requested size {expected:.4f}. "
            "Crop or re-export the master; the tool will not stretch artwork."
        )
    source_width_cm = args.width_cm + (
        2 * args.bleed_cm if args.art_includes_bleed else 0
    )
    source_dpi = master.width / (source_width_cm / 2.54)
    if source_dpi < args.dpi * 0.5:
        warnings.append(
            f"The master is only {source_dpi:.0f} dpi at this size; "
            f"resampling to {args.dpi:g} dpi adds no detail."
        )
    if args.art_includes_bleed:
        page_image = master.resize((total_w, total_h), Image.LANCZOS)
    else:
        art = master.resize((trim_w, trim_h), Image.LANCZOS)
        page_image = extend_edges(art, bleed)
        if bleed:
            warnings.append(
                "Bleed was made by repeating edge pixels. Check photo edges for streaks, "
                "or supply artwork that includes real bleed."
            )
    return page_image, source_dpi


def choose_scale(args):
    longest_pt = max(args.width_cm, args.height_cm) + 2 * args.bleed_cm
    longest_pt = longest_pt / 2.54 * 72
    if args.scale == "auto":
        scale = 10 if longest_pt > PDF_MAX_PT else 1
    else:
        scale = int(args.scale)
    if longest_pt / scale > PDF_MAX_PT:
        raise ToolError(
            f"The page would exceed the {PDF_MAX_PT} pt PDF limit at 1:{scale}. "
            "Split the job into panels."
        )
    return scale


def output_path(path, scale):
    if scale == 1:
        return path
    stem, extension = os.path.splitext(path)
    marker = f"_SCALE-1to{scale}"
    return path if stem.endswith(marker) else stem + marker + extension


def write_pdf(path, page_image, transform, args, scale):
    width_pt = (args.width_cm + 2 * args.bleed_cm) / 2.54 * 72 / scale
    height_pt = (args.height_cm + 2 * args.bleed_cm) / 2.54 * 72 / scale
    bleed_pt = args.bleed_cm / 2.54 * 72 / scale
    trim = (bleed_pt, bleed_pt, width_pt - bleed_pt, height_pt - bleed_pt)
    pixel_w, pixel_h = page_image.size
    is_rgb = args.color == "rgb"
    color_space = "[/ICCBased 7 0 R]" if is_rgb else "/DeviceCMYK"
    color_info = " /PrintColor (RGB)" if is_rgb else ""
    content = f"q {width_pt:.4f} 0 0 {height_pt:.4f} 0 0 cm /Im0 Do Q".encode()
    objects = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width_pt:.4f} {height_pt:.4f}] "
            f"/BleedBox [0 0 {width_pt:.4f} {height_pt:.4f}] "
            f"/TrimBox [{trim[0]:.4f} {trim[1]:.4f} {trim[2]:.4f} {trim[3]:.4f}] "
            "/Resources << /XObject << /Im0 5 0 R >> >> /Contents 4 0 R >>"
        ).encode(),
        4: f"<< /Length {len(content)} >>\nstream\n".encode()
        + content
        + b"\nendstream",
        6: f"<< /Producer (build_print_pdf) /PrintScale {scale}{color_info} >>".encode(),
    }
    if is_rgb:
        srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        objects[7] = (
            f"<< /N 3 /Alternate /DeviceRGB /Length {len(srgb)} >>\nstream\n".encode()
            + srgb
            + b"\nendstream"
        )
    object_count = max(objects) + 1
    directory = os.path.dirname(os.path.abspath(path))
    temp_stream = tempfile.NamedTemporaryFile(
        dir=directory, suffix=".stream", delete=False
    )
    temp_pdf = tempfile.NamedTemporaryFile(
        dir=directory, suffix=".partial", delete=False
    )
    try:
        compressor = zlib.compressobj(6)
        with temp_stream as stream:
            for top in range(0, pixel_h, STRIP_ROWS):
                strip = page_image.crop(
                    (0, top, pixel_w, min(top + STRIP_ROWS, pixel_h))
                )
                pixels = ImageCms.applyTransform(strip, transform) if transform else strip
                stream.write(compressor.compress(pixels.tobytes()))
            stream.write(compressor.flush())
        stream_size = os.path.getsize(temp_stream.name)
        with temp_pdf as pdf:
            pdf.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
            offsets = {}
            for number in (1, 2, 3, 4):
                offsets[number] = pdf.tell()
                pdf.write(
                    f"{number} 0 obj\n".encode() + objects[number] + b"\nendobj\n"
                )
            offsets[5] = pdf.tell()
            pdf.write(
                (
                    f"5 0 obj\n<< /Type /XObject /Subtype /Image /Width {pixel_w} "
                    f"/Height {pixel_h} /ColorSpace {color_space} /BitsPerComponent 8 "
                    f"/Filter /FlateDecode /Length {stream_size} >>\nstream\n"
                ).encode()
            )
            with open(temp_stream.name, "rb") as stream:
                for chunk in iter(lambda: stream.read(1 << 22), b""):
                    pdf.write(chunk)
            pdf.write(b"\nendstream\nendobj\n")
            offsets[6] = pdf.tell()
            pdf.write(b"6 0 obj\n" + objects[6] + b"\nendobj\n")
            if is_rgb:
                offsets[7] = pdf.tell()
                pdf.write(b"7 0 obj\n" + objects[7] + b"\nendobj\n")
            xref_offset = pdf.tell()
            pdf.write(f"xref\n0 {object_count}\n0000000000 65535 f \n".encode())
            for number in range(1, object_count):
                pdf.write(f"{offsets[number]:010d} 00000 n \n".encode())
            pdf.write(
                f"trailer\n<< /Size {object_count} /Root 1 0 R /Info 6 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode()
            )
        os.replace(temp_pdf.name, path)
    finally:
        for leftover in (temp_stream.name, temp_pdf.name):
            if os.path.exists(leftover):
                os.remove(leftover)


def build(args):
    validate_args(args)
    scale = choose_scale(args)
    destination = output_path(args.output, scale)
    if os.path.exists(destination) and not args.overwrite:
        raise ToolError(
            f"{destination} already exists. Pass --overwrite to replace it."
        )
    warnings = []
    icc_path, profile_name = None, "sRGB (embedded)"
    cmyk_profile = None
    if args.color == "cmyk":
        icc_path, cmyk_profile = find_cmyk_profile(args.icc)
        profile_name = profile_label(cmyk_profile)
        if icc_path in KNOWN_CMYK_PROFILES:
            warnings.append(
                "Using a generic system profile, not your print shop's. "
                "Actual color depends on the shop's machine and material."
            )
    master, embedded_profile = open_master(
        args.input, args.max_megapixels * 1e6, warnings
    )
    if cmyk_profile:
        transform = build_transform(embedded_profile, cmyk_profile, warnings)
    else:
        transform = build_srgb_transform(embedded_profile, warnings)
    page_image, source_dpi = fit_to_page(master, args, warnings)
    write_pdf(destination, page_image, transform, args, scale)
    report = {
        "output": destination,
        "finished_size_cm": [args.width_cm, args.height_cm],
        "bleed_cm_per_side": args.bleed_cm,
        "pixels": list(page_image.size),
        "output_dpi": args.dpi,
        "source_dpi": round(source_dpi, 1),
        "scale": f"1:{scale}",
        "color": args.color.upper(),
        "icc_profile": profile_name,
        "icc_path": icc_path,
        "file_mb": round(os.path.getsize(destination) / 1e6, 1),
        "warnings": warnings,
    }
    instructions = []
    if scale != 1:
        instructions.append(
            f"TELL THE PRINT SHOP: this page is 1:{scale}. Print at {scale * 100}% "
            f"to get {args.width_cm:g} x {args.height_cm:g} cm."
        )
    if args.color == "rgb":
        instructions.append(
            "TELL THE PRINT SHOP: this file is RGB (sRGB). Confirm you accept RGB and "
            "convert it on your RIP, and send a proof: color is set at the shop."
        )
    if instructions:
        report["shop_instruction"] = "\n".join(instructions)
    return report


def main(argv=None):
    args = parse_args(argv)
    try:
        report = build(args)
    except ToolError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    print(f"OK {report['output']}")
    print(
        f"Finished {args.width_cm:g} x {args.height_cm:g} cm, bleed {args.bleed_cm:g} cm, "
        f"{report['pixels'][0]} x {report['pixels'][1]} px, {report['file_mb']} MB"
    )
    print(f"Profile: {report['icc_profile']}")
    for warning in report["warnings"]:
        print(f"WARNING: {warning}")
    if "shop_instruction" in report:
        print(report["shop_instruction"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
