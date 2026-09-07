#!/usr/bin/env python3
"""鑫海產「鮮味聚」商務沉穩版海報（扶輪社社團推薦用）

與 seafood_poster.py 是兩套版型，共用同一份品項報價（config 的 items_from）。
用法：python3 design/seafood_poster_rotary.py design/seafood_poster/rotary.json
輸出 1080x1920 PNG。
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
HEITI_M = "/System/Library/Fonts/STHeiti Medium.ttc"
HEITI_L = "/System/Library/Fonts/STHeiti Light.ttc"
LATIN = "/System/Library/Fonts/Supplemental/Avenir Next.ttc"

INK = (243, 238, 228)
INK_SOFT = (156, 180, 200)
GOLD = (198, 164, 98)
GOLD_DIM = (140, 116, 70)
DEEP = (8, 26, 44)
DEEP_2 = (5, 17, 30)

MARGIN = 88
LIST_RULE = 528
LIST_TOP = 556
ROW_H = 106
TRUST_TOP = 1452
TAGLINE_Y = 1690
FOOTER_TOP = 1792
X_UNIT = W - MARGIN - 42


def font(path, size, index=0):
    return ImageFont.truetype(path, size, index=index)


def ink_w(draw, text, f):
    return draw.textbbox((0, 0), text, font=f)[2]


def tracked_w(draw, text, f, tracking):
    return sum(ink_w(draw, c, f) for c in text) + tracking * (len(text) - 1)


def draw_tracked(draw, xy, text, f, fill, tracking):
    """逐字繪製以撐開字距——商務調性靠字距，PIL 沒有內建 letter-spacing。"""
    x, y = xy
    for c in text:
        draw.text((x, y), c, font=f, fill=fill)
        x += ink_w(draw, c, f) + tracking
    return x - tracking


def centered_tracked(draw, y, text, f, fill, tracking=0):
    x = (W - tracked_w(draw, text, f, tracking)) / 2
    draw_tracked(draw, (x, y), text, f, fill, tracking)


def build_background(path):
    """深藍夜色底圖壓到幾乎全暗，只留一層海洋質感，避免搶掉文字。"""
    base = Image.new("RGB", (W, H), DEEP)
    if path and Path(path).exists():
        bg = Image.open(path).convert("RGB")
        target = W / H
        bw, bh = bg.size
        if bw / bh > target:
            nw = int(bh * target)
            bg = bg.crop(((bw - nw) // 2, 0, (bw - nw) // 2 + nw, bh))
        else:
            nh = int(bw / target)
            bg = bg.crop((0, (bh - nh) // 2, bw, (bh - nh) // 2 + nh))
        bg = bg.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(3))
        base = Image.blend(base, bg, 0.20)

    veil = Image.new("L", (1, H))
    for y in range(H):
        t = y / H
        veil.putpixel((0, y), int(120 + 105 * (t**1.6)))
    veil = veil.resize((W, H))
    return Image.composite(Image.new("RGB", (W, H), DEEP_2), base, veil).convert("RGBA")


def hairline(draw, y, x0, x1, fill, width=1):
    draw.line([(x0, y), (x1, y)], fill=fill, width=width)


def draw_header(draw):
    f_brand = font(HEITI_M, 40)
    f_brand_en = font(LATIN, 20, index=5)
    f_eyebrow = font(HEITI_L, 26)

    hairline(draw, 118, W / 2 - 60, W / 2 + 60, GOLD + (255,), 2)
    centered_tracked(draw, 158, "鑫海產", f_brand, INK, 14)
    centered_tracked(draw, 222, "XIN SEAFOOD", f_brand_en, GOLD, 8)
    centered_tracked(draw, 268, "龜吼現流．產地直送", f_eyebrow, INK_SOFT, 4)


def draw_title(draw, title, series):
    f_title = font(HEITI_M, 96)
    f_series = font(HEITI_L, 25)
    centered_tracked(draw, 336, title, f_title, INK, 22)
    centered_tracked(draw, 478, series, f_series, GOLD, 6)


def split_zh(zh):
    """current.json 的 zh 欄格式＝「前綴 名稱　形容詞」（全形空格分隔）。"""
    head, _, tail = zh.partition("　")
    parts = head.split(" ", 1)
    prefix, name = (parts[0], parts[1]) if len(parts) == 2 else ("", parts[0])
    return prefix.strip(), name.strip(), tail.strip()


def split_price(price):
    """「NT$500 / 片」拆成金額與單位；「2 尾 NT$400」這種倒裝的整串當金額。"""
    if " / " in price:
        amount, _, unit = price.partition(" / ")
        return amount.strip(), "／" + unit.strip()
    return price.strip(), ""


def split_en(en):
    common, _, latin = en.partition("  ")
    return common.strip(), latin.strip()


def draw_items(draw, items):
    f_no = font(LATIN, 26, index=5)
    f_name = font(HEITI_M, 46)
    f_prefix = font(HEITI_L, 25)
    f_meta = font(HEITI_L, 24)
    f_latin = font(LATIN, 21, index=1)
    f_price = font(HEITI_M, 40)
    f_unit = font(HEITI_L, 24)

    x_no = MARGIN
    x_text = MARGIN + 74

    for i, it in enumerate(items):
        y = LIST_TOP + ROW_H * i
        prefix, name, adj = split_zh(it["zh"])
        common, latin = split_en(it["en"])
        amount, unit = split_price(it["price"])

        draw.text((x_no, y + 12), f"{i + 1:02d}", font=f_no, fill=GOLD_DIM)

        draw.text((x_text, y), name, font=f_name, fill=INK)
        if prefix:
            px = x_text + ink_w(draw, name, f_name) + 16
            draw.text((px, y + 16), prefix, font=f_prefix, fill=GOLD)

        meta = " · ".join(p for p in (adj, latin) if p)
        draw.text((x_text, y + 58), meta, font=f_meta, fill=INK_SOFT)

        aw = ink_w(draw, amount, f_price)
        draw.text((X_UNIT - 10 - aw, y + 4), amount, font=f_price, fill=GOLD)
        if unit:
            draw.text((X_UNIT, y + 22), unit, font=f_unit, fill=GOLD_DIM)

        if i < len(items) - 1:
            hairline(draw, y + ROW_H - 14, MARGIN, W - MARGIN, (70, 92, 112, 150))


def draw_trust(draw, heading, lines):
    f_head = font(HEITI_M, 36)
    f_body = font(HEITI_L, 27)

    draw.rectangle([MARGIN, TRUST_TOP + 4, MARGIN + 6, TRUST_TOP + 42], fill=GOLD)
    draw.text((MARGIN + 24, TRUST_TOP), heading, font=f_head, fill=INK)
    for i, line in enumerate(lines):
        draw.text(
            (MARGIN + 24, TRUST_TOP + 74 + i * 46), line, font=f_body, fill=INK_SOFT
        )


def draw_tagline(img, text):
    f = font(HEITI_L, 27)
    draw = ImageDraw.Draw(img, "RGBA")
    tw = ink_w(draw, text, f)
    box = [(W - tw) / 2 - 40, TAGLINE_Y, (W + tw) / 2 + 40, TAGLINE_Y + 62]
    draw.rounded_rectangle(
        box, radius=31, fill=(16, 38, 62, 255), outline=GOLD + (255,), width=2
    )
    draw.text(((W - tw) / 2, TAGLINE_Y + 16), text, font=f, fill=(255, 252, 246))


def draw_footer(draw, left, right):
    f = font(HEITI_M, 30)
    draw.rectangle([0, FOOTER_TOP, W, H], fill=DEEP_2)
    hairline(draw, FOOTER_TOP, 0, W, GOLD_DIM + (255,), 2)
    y = FOOTER_TOP + (H - FOOTER_TOP) / 2 - 20
    draw.text((MARGIN, y), left, font=f, fill=INK)
    draw.text((W - MARGIN - ink_w(draw, right, f), y), right, font=f, fill=GOLD)


def build(cfg_path):
    cfg = json.loads(Path(cfg_path).read_text(encoding="utf-8"))
    src = json.loads(Path(cfg["items_from"]).read_text(encoding="utf-8"))
    items = src["items"]

    img = build_background(cfg.get("background"))
    draw = ImageDraw.Draw(img, "RGBA")

    draw_header(draw)
    draw_title(draw, cfg["title"], cfg["series"])
    hairline(draw, LIST_RULE, MARGIN, W - MARGIN, GOLD_DIM + (200,))
    draw_items(draw, items)
    hairline(draw, TRUST_TOP - 48, MARGIN, W - MARGIN, GOLD_DIM + (200,))
    draw_trust(draw, cfg["trust_heading"], cfg["trust"])
    draw_tagline(img, cfg["tagline"])
    draw_footer(ImageDraw.Draw(img, "RGBA"), cfg["footer_left"], cfg["footer_right"])

    out = Path(cfg_path).with_suffix(".png")
    img.convert("RGB").save(out, quality=96)
    print(f"✅ {out}  ({len(items)} 項)")
    return out


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "design/seafood_poster/rotary.json")
