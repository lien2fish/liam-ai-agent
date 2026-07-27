# -*- coding: utf-8 -*-
"""志工牆 RGB PNG → 調亮 → CMYK 送印檔（DeviceCMYK PDF 交三冠彩印 ＋ CMYK TIF 其他廠 ＋ 同內容 .ai）。
原像素當 150dpi：3148×1344px = 53.3×22.8cm。實際板尺寸不同再改 DPI。
.ai ＝與 PDF 同一份位元組另存副檔名（Illustrator 讀 PDF 相容檔）；牆面是照片合成、無法真向量化。
"""
import os, zlib
from PIL import Image, ImageCms, ImageEnhance

DESK = "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/一樓乾貨牆-志工名單（可拆換）"
SRC = DESK + "/dry_goods_wall_v20_志工照片版.png"
PDF = DESK + "/dry_goods_wall_v20_CMYK.pdf"
TIF = DESK + "/dry_goods_wall_v20_CMYK.tif"
AI = DESK + "/dry_goods_wall_v20_CMYK.ai"
ICC = "/System/Library/ColorSync/Profiles/Generic CMYK Profile.icc"
DPI = 150
BRIGHTNESS, COLOR = 1.12, 1.06  # 使用者要整體調亮(含背景)


def main():
    im = Image.open(SRC).convert("RGB")
    im = ImageEnhance.Brightness(im).enhance(BRIGHTNESS)
    im = ImageEnhance.Color(im).enhance(COLOR)
    cm = ImageCms.profileToProfile(
        im,
        ImageCms.createProfile("sRGB"),
        ImageCms.getOpenProfile(ICC),
        renderingIntent=ImageCms.Intent.PERCEPTUAL,
        outputMode="CMYK",
    )
    cm.save(TIF, dpi=(DPI, DPI))

    W, H = cm.size
    data = zlib.compress(cm.tobytes(), 6)
    w_pt, h_pt = W / DPI * 72, H / DPI * 72
    content = f"q {w_pt:.2f} 0 0 {h_pt:.2f} 0 0 cm /Im0 Do Q".encode()
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w_pt:.2f} {h_pt:.2f}] "
            f"/Resources << /XObject << /Im0 5 0 R >> >> /Contents 4 0 R >>"
        ).encode(),
        4: b"",
        5: b"",
    }
    with open(PDF, "wb") as f:
        f.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        off = {}
        for n in (1, 2, 3):
            off[n] = f.tell()
            f.write(f"{n} 0 obj\n".encode() + objs[n] + b"\nendobj\n")
        off[4] = f.tell()
        f.write(
            f"4 0 obj\n<< /Length {len(content)} >>\nstream\n".encode()
            + content
            + b"\nendstream\nendobj\n"
        )
        off[5] = f.tell()
        f.write(
            (
                f"5 0 obj\n<< /Type /XObject /Subtype /Image /Width {W} /Height {H} "
                f"/ColorSpace /DeviceCMYK /BitsPerComponent 8 /Filter /FlateDecode "
                f"/Length {len(data)} >>\nstream\n"
            ).encode()
            + data
            + b"\nendstream\nendobj\n"
        )
        xref = f.tell()
        f.write(b"xref\n0 6\n0000000000 65535 f \n")
        for n in range(1, 6):
            f.write(f"{off[n]:010d} 00000 n \n".encode())
        f.write(
            f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
        )
    with open(PDF, "rb") as f, open(AI, "wb") as g:
        g.write(f.read())

    print(f"OK {W}x{H}px = {W/DPI*2.54:.1f}×{H/DPI*2.54:.1f}cm @{DPI}dpi")
    for label, path in (("PDF", PDF), ("TIF", TIF), ("AI", AI)):
        print(label, round(os.path.getsize(path) / 1e6, 2), "MB")


if __name__ == "__main__":
    main()
