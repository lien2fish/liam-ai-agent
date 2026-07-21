# -*- coding: utf-8 -*-
"""六邊形理監事牌換姓名 — 直接在 CMYK 空間就地重繪，不做色彩轉換故零偏色。

排版參數由原稿反解得出（對「黃秀敏」重建 IoU 0.94）：
每字置中於等距格子，advance 416.5、中心 x=1334、字級 460、
Hiragino Sans GB index 3（實測 IoU 0.88~0.98，STHeiti/PingFang 皆不符）。

用法: python3 design/hex_badge_rename.py <來源tiff> <新姓名> [輸出tiff]
"""
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"
FONT_INDEX, FONT_SIZE = 3, 460
ADVANCE, CENTER_X = 416.5, 1334
NAME_CY = 1420
ERASE = (700, 1180, 2000, 1660)  # 姓名行擦除範圍，不觸及第一行職稱（底 1088）


def name_positions(n):
    return [CENTER_X + (i - (n - 1) / 2) * ADVANCE for i in range(n)]


def rename(src, new_name, out):
    im = Image.open(src)
    if im.mode != "CMYK":
        raise SystemExit(f"來源不是 CMYK：{im.mode}")
    arr = np.asarray(im).astype(np.float64)

    x0, y0, x1, y1 = ERASE
    bg = arr[300, CENTER_X].copy()  # 六邊形內純背景取樣
    arr[y0:y1, x0:x1] = bg

    mask = Image.new("L", im.size, 0)
    d = ImageDraw.Draw(mask)
    font = ImageFont.truetype(FONT, FONT_SIZE, index=FONT_INDEX)
    for ch, cx in zip(new_name, name_positions(len(new_name))):
        d.text((cx, NAME_CY), ch, font=font, fill=255, anchor="mm")

    # 白字 CMYK=(0,0,0,0)，故直接依覆蓋率衰減背景即可，抗鋸齒自然保留
    m = (np.asarray(mask).astype(np.float64) / 255.0)[:, :, None]
    arr = arr * (1 - m)

    Image.fromarray(arr.round().astype(np.uint8), "CMYK").save(out, compression="lzw")
    return im.size, bg, mask


def verify(src, out, new_name):
    a = np.asarray(Image.open(out)).astype(int)
    o = np.asarray(Image.open(src)).astype(int)
    ok = []

    ok.append(("輸出為 CMYK", Image.open(out).mode == "CMYK"))
    ok.append(("尺寸不變", a.shape == o.shape))

    # 第一行職稱必須逐像素不變
    ok.append(("職稱行未被動到", np.array_equal(a[:1150], o[:1150])))

    m = a.sum(axis=2) < 60
    m[:1150] = False
    m[1700:] = False
    m[:, :600] = False
    m[:, 2100:] = False
    cols = m.any(axis=0)
    segs, s = [], None
    for x in range(len(cols)):
        if cols[x] and s is None:
            s = x
        elif not cols[x] and s is not None:
            segs.append((s, x - 1))
            s = None
    ok.append((f"姓名字數 {len(segs)} 字", len(segs) == len(new_name)))

    want = name_positions(len(new_name))
    for (sx0, sx1), ch, wx in zip(segs, new_name, want):
        cx = (sx0 + sx1) / 2
        ok.append((f"「{ch}」中心 {cx:.0f}（應 {wx:.0f}）", abs(cx - wx) <= 12))

    ys = np.where(m.any(axis=1))[0]
    ok.append((f"姓名行 y{ys.min()}-{ys.max()}", 1190 <= ys.min() and ys.max() <= 1650))

    # 擦除區內、扣掉新字及其抗鋸齒邊緣後，應全為背景色
    x0, y0, x1, y1 = ERASE
    glyphs = Image.new("L", Image.open(out).size, 0)
    gd = ImageDraw.Draw(glyphs)
    font = ImageFont.truetype(FONT, FONT_SIZE, index=FONT_INDEX)
    for ch, cx in zip(new_name, name_positions(len(new_name))):
        gd.text((cx, NAME_CY), ch, font=font, fill=255, anchor="mm")
    clean = np.asarray(glyphs.filter(ImageFilter.MaxFilter(11)))[y0:y1, x0:x1] == 0
    reg = a[y0:y1, x0:x1]
    bg = o[300, CENTER_X]
    resid = np.abs(reg[clean] - bg).max() if clean.any() else 0
    ok.append((f"無舊字殘留（殘差 {resid}）", resid <= 6))

    print("\n{:<34} {}".format("檢查項目", "結果"))
    print("-" * 46)
    for name, passed in ok:
        print("{:<34} {}".format(name, "✅" if passed else "❌"))
    return all(p for _, p in ok)


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    src, new_name = sys.argv[1], sys.argv[2]
    out = (
        sys.argv[3] if len(sys.argv) > 3 else src.replace(".tiff", f"_{new_name}.tiff")
    )
    rename(src, new_name, out)
    print(f"✅ {out}")
    if not verify(src, out, new_name):
        print("\n⚠️ 有項目未通過")


if __name__ == "__main__":
    main()
