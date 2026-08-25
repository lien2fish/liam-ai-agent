# -*- coding: utf-8 -*-
"""歷史發展牆母檔 → 1:1 全尺寸 CMYK PDF（分段串流寫入，低記憶體）。

用法: python3 design/history_wall_cmyk.py <母檔PNG> <輸出PDF> [--dpi 100]

⚠️ 刻意**不套** tarp_face_pdf.py 的 enhance（亮度1.65／飽和1.83）。
那組參數是為平面插畫調的，這面牆是滿版照片，走那條會整片爆白。
母檔本身已經做過往深綠壓暗的分區處理，直接轉色即可。
"""
import argparse
import os
import zlib

from PIL import Image, ImageCms

Image.MAX_IMAGE_PIXELS = None

ICC = "/System/Library/ColorSync/Profiles/Generic CMYK Profile.icc"
BLEED_MM = 25.0  # 母檔四邊各含 2.5cm 出血


def build(src, out_pdf, dpi):
    im = Image.open(src)
    if im.mode != "RGB":
        im = im.convert("RGB")
    W, H = im.size
    w_mm, h_mm = W / dpi * 25.4, H / dpi * 25.4

    srgb = ImageCms.createProfile("sRGB")
    cmyk = ImageCms.getOpenProfile(ICC)

    tmp = out_pdf + ".imgstream"
    comp = zlib.compressobj(6)
    with open(tmp, "wb") as fo:
        for y in range(0, H, 256):
            seg = im.crop((0, y, W, min(y + 256, H)))
            cm = ImageCms.profileToProfile(
                seg, srgb, cmyk,
                renderingIntent=ImageCms.Intent.PERCEPTUAL, outputMode="CMYK",
            )
            fo.write(comp.compress(cm.tobytes()))
        fo.write(comp.flush())
    del im
    stream_len = os.path.getsize(tmp)

    mm2pt = 72 / 25.4
    w_pt, h_pt = w_mm * mm2pt, h_mm * mm2pt
    b_pt = BLEED_MM * mm2pt
    content = f"q {w_pt:.2f} 0 0 {h_pt:.2f} 0 0 cm /Im0 Do Q".encode()

    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w_pt:.2f} {h_pt:.2f}] "
            f"/TrimBox [{b_pt:.2f} {b_pt:.2f} {w_pt-b_pt:.2f} {h_pt-b_pt:.2f}] "
            f"/Resources << /XObject << /Im0 5 0 R >> >> /Contents 4 0 R >>"
        ).encode(),
    }

    with open(out_pdf, "wb") as f:
        f.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        off = {}
        for n in (1, 2, 3):
            off[n] = f.tell()
            f.write(f"{n} 0 obj\n".encode() + objs[n] + b"\nendobj\n")
        off[4] = f.tell()
        f.write(f"4 0 obj\n<< /Length {len(content)} >>\nstream\n".encode()
                + content + b"\nendstream\nendobj\n")
        off[5] = f.tell()
        f.write((
            f"5 0 obj\n<< /Type /XObject /Subtype /Image /Width {W} /Height {H} "
            f"/ColorSpace /DeviceCMYK /BitsPerComponent 8 /Filter /FlateDecode "
            f"/Length {stream_len} >>\nstream\n"
        ).encode())
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
            f.write(f"{off[n]:010d} 00000 n \n".encode())
        f.write(f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    os.remove(tmp)
    print(f"✅ {out_pdf}")
    print(f"   成品 {(w_mm-2*BLEED_MM)/10:.1f}×{(h_mm-2*BLEED_MM)/10:.1f}cm"
          f"　含出血 {w_mm/10:.1f}×{h_mm/10:.1f}cm　{W}×{H}px @{dpi}dpi"
          f"　{os.path.getsize(out_pdf)/1e6:.0f}MB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--dpi", type=float, default=100)
    args = ap.parse_args()
    build(args.src, args.out, args.dpi)
