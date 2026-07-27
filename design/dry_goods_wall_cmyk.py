# -*- coding: utf-8 -*-
"""志工牆 RGB PNG → 調亮 → CMYK 送印檔（DeviceCMYK PDF 交三冠彩印 ＋ CMYK TIF 其他廠 ＋ 同內容 .ai）。
成品尺寸 342×146cm（實際板面），母檔比例 2.3423 與之吻合，等比放大不需重排版。
WALL_W 要與 overlay_dry_goods_wall_v20.py 產出時同值：3148=23dpi(太低) / 9696=72dpi(送印用)。
.ai ＝與 PDF 同一份位元組另存副檔名（Illustrator 讀 PDF 相容檔）；牆面是照片合成、無法真向量化。
"""
import os, zlib
from PIL import Image, ImageCms, ImageEnhance

DESK = "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/一樓乾貨牆-志工名單（可拆換）"
WALL_W = int(os.environ.get("WALL_W", 9696))
SUF = f"_{WALL_W}px" if WALL_W != 3148 else ""
SRC = DESK + f"/dry_goods_wall_v20_志工照片版{SUF}.png"
PDF = DESK + f"/dry_goods_wall_v20_CMYK{SUF}.pdf"
TIF = DESK + f"/dry_goods_wall_v20_CMYK{SUF}.tif"
AI = DESK + f"/dry_goods_wall_v20_CMYK{SUF}.ai"
ICC = "/System/Library/ColorSync/Profiles/Generic CMYK Profile.icc"
OUT_W_CM, OUT_H_CM = 342.0, 146.0  # 成品板面尺寸，DPI 由此回推
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
    W, H = cm.size
    DPI = W / (OUT_W_CM / 2.54)
    assert abs(H / (OUT_H_CM / 2.54) - DPI) < 0.1, "母檔比例與成品尺寸不符，需重排版"
    cm.save(TIF, dpi=(round(DPI), round(DPI)))

    data = zlib.compress(cm.tobytes(), 6)
    w_pt, h_pt = OUT_W_CM / 2.54 * 72, OUT_H_CM / 2.54 * 72
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

    print(
        f"OK {W}x{H}px → 頁面 {OUT_W_CM:.0f}×{OUT_H_CM:.0f}cm（1:1 實際 {DPI:.1f}dpi）"
    )
    for label, path in (("PDF", PDF), ("TIF", TIF), ("AI", AI)):
        print(label, round(os.path.getsize(path) / 1e6, 2), "MB")


if __name__ == "__main__":
    main()
