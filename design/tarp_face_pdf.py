# -*- coding: utf-8 -*-
"""單面防水布 → 調亮銳利化 → 100dpi 全尺寸 CMYK PDF（分段串流寫入，低記憶體）。
用法: python3 make_face_pdf.py <來源PNG或母檔> <x0> <x1> <輸出pdf>
x0=x1=0 表示整張。1000px = 1m。
"""
import sys, os, zlib
from PIL import Image, ImageCms, ImageEnhance, ImageFilter

Image.MAX_IMAGE_PIXELS = None
ICC = "/System/Library/ColorSync/Profiles/Generic CMYK Profile.icc"
SRGB = ImageCms.createProfile("sRGB")
CMYK = ImageCms.getOpenProfile(ICC)
PXMM = 100 / 25.4  # 100dpi → px per mm

# 2026-07-17：使用者要求鮮豔度與亮度再各 +50%（相對前版 1.10/1.22）
BRIGHTNESS = 1.65  # 前版 1.10 × 1.5
COLOR = 1.83  # 前版 1.22 × 1.5


def enhance(img):
    img = ImageEnhance.Brightness(img).enhance(BRIGHTNESS)
    img = ImageEnhance.Color(img).enhance(COLOR)
    return img.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=3))


def build(src, x0, x1, out_pdf):
    im = Image.open(src).convert("RGB")
    if x1 > x0:
        im = im.crop((x0, 0, x1, im.size[1]))
    im = enhance(im)
    w_mm, h_mm = im.size  # 1px = 1mm
    W = round(w_mm * PXMM)
    H = round(h_mm * PXMM)
    big = im.resize((W, H), Image.LANCZOS)
    del im

    tmp = out_pdf + ".imgstream"
    comp = zlib.compressobj(6)
    with open(tmp, "wb") as fo:
        strip = 256
        for y in range(0, H, strip):
            seg = big.crop((0, y, W, min(y + strip, H)))
            cm = ImageCms.profileToProfile(
                seg,
                SRGB,
                CMYK,
                renderingIntent=ImageCms.Intent.PERCEPTUAL,
                outputMode="CMYK",
            )
            fo.write(comp.compress(cm.tobytes()))
        fo.write(comp.flush())
    del big
    stream_len = os.path.getsize(tmp)

    w_pt = w_mm / 25.4 * 72
    h_pt = h_mm / 25.4 * 72
    content = f"q {w_pt:.2f} 0 0 {h_pt:.2f} 0 0 cm /Im0 Do Q".encode()

    objs = {}
    objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[2] = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
    objs[3] = (
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w_pt:.2f} {h_pt:.2f}] "
        f"/Resources << /XObject << /Im0 5 0 R >> >> /Contents 4 0 R >>"
    ).encode()

    with open(out_pdf, "wb") as f:
        f.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = {}
        for n in (1, 2, 3):
            offsets[n] = f.tell()
            f.write(f"{n} 0 obj\n".encode() + objs[n] + b"\nendobj\n")
        offsets[4] = f.tell()
        f.write(
            f"4 0 obj\n<< /Length {len(content)} >>\nstream\n".encode()
            + content
            + b"\nendstream\nendobj\n"
        )
        offsets[5] = f.tell()
        f.write(
            (
                f"5 0 obj\n<< /Type /XObject /Subtype /Image /Width {W} /Height {H} "
                f"/ColorSpace /DeviceCMYK /BitsPerComponent 8 /Filter /FlateDecode "
                f"/Length {stream_len} >>\nstream\n"
            ).encode()
        )
        with open(tmp, "rb") as fi:
            while True:
                chunk = fi.read(1 << 22)
                if not chunk:
                    break
                f.write(chunk)
        f.write(b"\nendstream\nendobj\n")
        xref = f.tell()
        f.write(b"xref\n0 6\n0000000000 65535 f \n")
        for n in range(1, 6):
            f.write(f"{offsets[n]:010d} 00000 n \n".encode())
        f.write(
            (f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n").encode()
        )
    os.remove(tmp)
    print(
        f"OK {out_pdf}  {w_mm/1000:.3f}m x {h_mm/1000:.2f}m  {W}x{H}px  "
        f"{os.path.getsize(out_pdf)/1e6:.0f}MB"
    )


if __name__ == "__main__":
    build(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
