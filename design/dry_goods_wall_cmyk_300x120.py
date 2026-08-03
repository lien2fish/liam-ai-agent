# -*- coding: utf-8 -*-
"""志工牆 300×120cm 版 RGB PNG → 調亮 → CMYK 送印檔（342×146 版見 dry_goods_wall_cmyk.py）。

與 342 版的差別只有兩點：成品尺寸改 300×120、**多做 1cm 出血**（使用者指定 300×120 為
成品尺寸、出血另計）。出血用邊緣像素往外延伸，PDF 的 MediaBox＝含出血、TrimBox＝成品，
印刷廠依 TrimBox 裁切。
WALL_W 要與 overlay_dry_goods_wall_v21.py 產出時同值：3150=27dpi(太低) / 8504=72dpi(送印用)。
.ai ＝與 PDF 同一份位元組另存副檔名；牆面是照片合成、無法真向量化。
"""
import os, zlib
from PIL import Image, ImageCms, ImageEnhance

DESK = "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/一樓乾貨牆-志工名單（可拆換）"
WALL_W = int(os.environ.get("WALL_W", 8504))
SUF = f"_{WALL_W}px" if WALL_W != 3150 else ""
SRC = DESK + f"/dry_goods_wall_v21_志工照片版_300x120{SUF}.png"
PDF = DESK + f"/dry_goods_wall_v21_CMYK_300x120{SUF}.pdf"
TIF = DESK + f"/dry_goods_wall_v21_CMYK_300x120{SUF}.tif"
AI = DESK + f"/dry_goods_wall_v21_CMYK_300x120{SUF}.ai"
ICC = "/System/Library/ColorSync/Profiles/Generic CMYK Profile.icc"
OUT_W_CM, OUT_H_CM = 300.0, 120.0  # 成品(裁切後)尺寸，DPI 由此回推
BLEED_CM = 1.0
BRIGHTNESS, COLOR = 1.12, 1.06  # 沿用 342 版：使用者要整體調亮(含背景)


def add_bleed(im, b):
    """四邊各外擴 b px，用最外圈像素拉出去填滿——牆面邊緣是米色底與裝飾帶，複製即可"""
    W, H = im.size
    out = Image.new("RGB", (W + 2 * b, H + 2 * b))
    out.paste(im, (b, b))
    out.paste(im.crop((0, 0, W, 1)).resize((W, b)), (b, 0))
    out.paste(im.crop((0, H - 1, W, H)).resize((W, b)), (b, H + b))
    out.paste(im.crop((0, 0, 1, H)).resize((b, H)), (0, b))
    out.paste(im.crop((W - 1, 0, W, H)).resize((b, H)), (W + b, b))
    for cx, cy, px, py in (
        (0, 0, 0, 0),
        (W - 1, 0, W + b, 0),
        (0, H - 1, 0, H + b),
        (W - 1, H - 1, W + b, H + b),
    ):
        out.paste(im.crop((cx, cy, cx + 1, cy + 1)).resize((b, b)), (px, py))
    return out


def main():
    im = Image.open(SRC).convert("RGB")
    DPI = im.width / (OUT_W_CM / 2.54)
    assert (
        abs(im.height / (OUT_H_CM / 2.54) - DPI) < 0.1
    ), "母檔比例與成品尺寸不符，需重排版"
    bleed = round(BLEED_CM / 2.54 * DPI)
    im = ImageEnhance.Brightness(im).enhance(BRIGHTNESS)
    im = ImageEnhance.Color(im).enhance(COLOR)
    im = add_bleed(im, bleed)
    cm = ImageCms.profileToProfile(
        im,
        ImageCms.createProfile("sRGB"),
        ImageCms.getOpenProfile(ICC),
        renderingIntent=ImageCms.Intent.PERCEPTUAL,
        outputMode="CMYK",
    )
    W, H = cm.size
    cm.save(TIF, dpi=(round(DPI), round(DPI)))

    data = zlib.compress(cm.tobytes(), 6)
    bl_pt = BLEED_CM / 2.54 * 72
    w_pt, h_pt = (OUT_W_CM + 2 * BLEED_CM) / 2.54 * 72, (
        OUT_H_CM + 2 * BLEED_CM
    ) / 2.54 * 72
    content = f"q {w_pt:.2f} 0 0 {h_pt:.2f} 0 0 cm /Im0 Do Q".encode()
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w_pt:.2f} {h_pt:.2f}] "
            f"/TrimBox [{bl_pt:.2f} {bl_pt:.2f} {w_pt - bl_pt:.2f} {h_pt - bl_pt:.2f}] "
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
        f"OK {W}x{H}px → 成品 {OUT_W_CM:.0f}×{OUT_H_CM:.0f}cm"
        f"＋出血 {BLEED_CM}cm（頁面 {OUT_W_CM + 2 * BLEED_CM:.0f}×{OUT_H_CM + 2 * BLEED_CM:.0f}cm，1:1 實際 {DPI:.1f}dpi）"
    )
    for label, path in (("PDF", PDF), ("TIF", TIF), ("AI", AI)):
        print(label, round(os.path.getsize(path) / 1e6, 2), "MB")


if __name__ == "__main__":
    main()
