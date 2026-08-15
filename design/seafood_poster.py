#!/usr/bin/env python3
"""匠鑫聚 · 鮮味聚 季節海報產生器

用法：python3 design/seafood_poster.py design/seafood_poster/autumn.json
輸出 1080x1920 PNG，換季只改 config JSON。
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
HEITI_M = "/System/Library/Fonts/STHeiti Medium.ttc"
HEITI_L = "/System/Library/Fonts/STHeiti Light.ttc"
LATIN = "/System/Library/Fonts/Supplemental/Avenir Next.ttc"

THEMES = {
    "light": {
        "ink": (12, 52, 84),
        "ink_soft": (28, 74, 110),
        "accent": (150, 106, 52),
        "footer_bg": (10, 40, 68),
        "footer_ink": (245, 240, 228),
        "panel": (252, 253, 255),
        "panel_alpha": 150,
        "shadow": (36, 58, 68),
    },
    "dark": {
        "ink": (248, 250, 252),
        "ink_soft": (206, 224, 238),
        "accent": (216, 180, 116),
        "footer_bg": (7, 22, 40),
        "footer_ink": (240, 246, 250),
        "panel": (6, 30, 56),
        "panel_alpha": 120,
        "shadow": (0, 8, 20),
    },
}
T = THEMES["light"]

BRAND_Y = 96
TITLE_Y = 148
TITLE_SIZE = 150
TITLE_GAP = 46
SUB_Y = 330
INTRO_Y = 402
INTRO_SIZE = 30
INTRO_LEAD = 42
RULE_Y_PAD = 26
LIST_BOTTOM = 1745
FOOTER_TOP = 1788
STRIP_TOP = 1448
STRIP_BOTTOM = 1772
STRIP_SIDE = 40
BANNER_W = W
BANNER_BOTTOM = 1880
BANNER_GAP = 16
TAGLINE_SIZE = 40
TAGLINE_BOTTOM = 1722
TAGLINE_PAD_X = 44
TAGLINE_PAD_Y = 20


def font(path, size, index=0):
    return ImageFont.truetype(path, size, index=index)


def ink_w(draw, text, f):
    return draw.textbbox((0, 0), text, font=f)[2]


def centered(draw, y, text, f, fill, glow=None):
    x = (W - ink_w(draw, text, f)) / 2
    draw.text((x, y), text, font=f, fill=fill)
    return x


def soft_panel(img, box, radius, alpha):
    layer = Image.new("L", img.size, 0)
    ImageDraw.Draw(layer).rounded_rectangle(box, radius=radius, fill=alpha)
    layer = layer.filter(ImageFilter.GaussianBlur(28))
    tint = Image.new(img.mode, img.size, (T["panel"] + (255,))[: len(img.mode)])
    return Image.composite(tint, img, layer)


def prep_background(path):
    bg = Image.open(path).convert("RGB")
    target = W / H
    bw, bh = bg.size
    if bw / bh > target:
        new_w = int(bh * target)
        bg = bg.crop(((bw - new_w) // 2, 0, (bw - new_w) // 2 + new_w, bh))
    else:
        new_h = int(bw / target)
        bg = bg.crop((0, (bh - new_h) // 2, bw, (bh - new_h) // 2 + new_h))
    return bg.resize((W, H), Image.LANCZOS)


def draw_title(draw, y, chars, size, gap):
    f = font(HEITI_M, size)
    widths = [ink_w(draw, c, f) for c in chars]
    dia = size * 0.095
    total = sum(widths) + (len(chars) - 1) * (gap * 2 + dia * 2)
    x = (W - total) / 2
    cy = y + size * 0.62
    for i, c in enumerate(chars):
        draw.text(
            (x, y), c, font=f, fill=T["ink"], stroke_width=3, stroke_fill=T["ink"]
        )
        x += widths[i]
        if i < len(chars) - 1:
            x += gap
            draw.polygon(
                [(x + dia, cy - dia), (x + dia * 2, cy), (x + dia, cy + dia), (x, cy)],
                fill=T["accent"],
            )
            x += dia * 2 + gap
    return y + size * 1.35


def draw_rule(draw, y, width=300):
    x0 = (W - width) / 2
    draw.line([(x0, y), (x0 + width, y)], fill=T["accent"] + (0,), width=2)
    d = 7
    draw.polygon(
        [(W / 2, y - d), (W / 2 + d, y), (W / 2, y + d), (W / 2 - d, y)],
        fill=T["accent"],
    )


def draw_list(draw, items, top, bottom):
    n = len(items)
    slot = (bottom - top) / n
    f_zh_size = min(42, int(slot * 0.38))
    f_en_size = max(18, int(f_zh_size * 0.70))
    f_pr_size = max(17, int(f_zh_size * 0.60))
    f_zh = font(HEITI_M, f_zh_size)
    f_pr = font(HEITI_L, f_pr_size)
    h_en, h_zh = f_en_size * 1.14, f_zh_size * 1.14
    block = h_en + h_zh + f_pr_size * 1.08
    max_w = W - 120
    for i, it in enumerate(items):
        y = top + slot * i + (slot - block) / 2
        f_en = font(LATIN, f_en_size, index=5)
        while ink_w(draw, it["en"], f_en) > max_w and f_en.size > 16:
            f_en = font(LATIN, f_en.size - 1, index=5)
        centered(draw, y, it["en"], f_en, T["ink_soft"])
        centered(draw, y + h_en, it["zh"], f_zh, T["ink"])
        centered(draw, y + h_en + h_zh, it["price"], f_pr, T["accent"])


def load_trimmed(path):
    item = Image.open(path).convert("RGBA")
    bb = item.getchannel("A").point(lambda v: 255 if v > 10 else 0).getbbox()
    return item.crop(bb) if bb else item


def banner_geometry(path):
    item = load_trimmed(path)
    h = int(item.height * BANNER_W / item.width)
    return BANNER_BOTTOM - h, h


def paste_with_shadow(img, item, x, y):
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sm = item.getchannel("A").point(lambda v: int(v * 0.3))
    shadow.paste(T["shadow"] + (255,), (x, y + 10), sm)
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(16)))
    img.alpha_composite(item, (x, y))


def draw_banner(img, path):
    """單張去背橫幅：滿版居中、底部沒入頁尾條，模擬原版產品排。"""
    item = load_trimmed(path)
    top, h = banner_geometry(path)
    item = item.resize((BANNER_W, h), Image.LANCZOS)
    paste_with_shadow(img, item, (W - BANNER_W) // 2, top)


def draw_strip(img, paths):
    """底部去背海鮮排：等高、底部對齊、平均分佈。找不到檔案就畫佔位框。"""
    n = len(paths)
    if not n:
        return
    if n == 1:
        if Path(paths[0]).exists():
            draw_banner(img, paths[0])
        return
    slot = (W - STRIP_SIDE * 2) / n
    box_h = STRIP_BOTTOM - STRIP_TOP
    draw = ImageDraw.Draw(img, "RGBA")
    f_ph = font(HEITI_L, 26)
    for i, p in enumerate(paths):
        cx = STRIP_SIDE + slot * (i + 0.5)
        if Path(p).exists():
            item = Image.open(p).convert("RGBA")
            scale = min(box_h / item.height, (slot * 1.14) / item.width)
            item = item.resize(
                (max(1, int(item.width * scale)), max(1, int(item.height * scale))),
                Image.LANCZOS,
            )
            shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
            sm = item.getchannel("A").point(lambda v: int(v * 0.32))
            shadow.paste(
                (40, 60, 70, 255),
                (int(cx - item.width / 2), STRIP_BOTTOM - item.height + 8),
                sm,
            )
            img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(14)))
            img.alpha_composite(
                item, (int(cx - item.width / 2), STRIP_BOTTOM - item.height)
            )
        else:
            w = min(slot * 0.92, box_h * 1.15)
            h = min(box_h, w * 0.82)
            draw.rounded_rectangle(
                [cx - w / 2, STRIP_BOTTOM - h, cx + w / 2, STRIP_BOTTOM],
                radius=16,
                fill=(255, 255, 255, 120),
                outline=(120, 150, 160, 190),
                width=2,
            )
            draw.text(
                (cx - ink_w(draw, str(i + 1), f_ph) / 2, STRIP_BOTTOM - h / 2 - 18),
                str(i + 1),
                font=f_ph,
                fill=(90, 125, 138, 220),
            )


def draw_tagline(img, text):
    """疊在底部照片之上的洽詢標語，深藍膠囊條＋金框。"""
    f = font(HEITI_M, TAGLINE_SIZE)
    draw = ImageDraw.Draw(img, "RGBA")
    tw = ink_w(draw, text, f)
    th = TAGLINE_SIZE * 1.2
    box = [
        (W - tw) / 2 - TAGLINE_PAD_X,
        TAGLINE_BOTTOM - th - TAGLINE_PAD_Y * 2,
        (W + tw) / 2 + TAGLINE_PAD_X,
        TAGLINE_BOTTOM,
    ]
    radius = (box[3] - box[1]) / 2

    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [box[0], box[1] + 8, box[2], box[3] + 8], radius=radius, fill=(0, 20, 36, 110)
    )
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(14)))

    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=T["footer_bg"] + (222,),
        outline=T["accent"] + (255,),
        width=2,
    )
    centered(draw, box[1] + TAGLINE_PAD_Y, text, f, T["footer_ink"])


def build(cfg, out):
    global T
    T = THEMES[cfg.get("theme", "light")]
    strip = cfg.get("bottom_strip", [])
    if len(strip) == 1 and Path(strip[0]).exists():
        list_bottom = banner_geometry(strip[0])[0] - BANNER_GAP
    elif strip:
        list_bottom = STRIP_TOP - 34
    else:
        list_bottom = LIST_BOTTOM
    img = prep_background(cfg["background"]).convert("RGBA")
    img = soft_panel(img, (52, 372, W - 52, list_bottom + 26), 60, T["panel_alpha"])
    draw = ImageDraw.Draw(img, "RGBA")

    centered(draw, BRAND_Y, cfg["brand"], font(HEITI_M, 42), T["ink_soft"])
    draw_title(draw, TITLE_Y, list(cfg["title"]), TITLE_SIZE, TITLE_GAP)
    centered(draw, SUB_Y, cfg["subtitle"], font(HEITI_M, 58), T["ink"])

    f_intro = font(HEITI_L, INTRO_SIZE)
    y = INTRO_Y
    for line in cfg["intro"]:
        centered(draw, y, line, f_intro, T["ink_soft"])
        y += INTRO_LEAD
    draw_rule(draw, y + RULE_Y_PAD)

    draw_list(draw, cfg["items"], y + RULE_Y_PAD * 2 + 12, list_bottom)
    draw_strip(img, strip)
    if cfg.get("tagline"):
        draw_tagline(img, cfg["tagline"])

    draw = ImageDraw.Draw(img, "RGBA")
    draw.rectangle([0, FOOTER_TOP, W, H], fill=T["footer_bg"])
    f_foot = font(HEITI_M, 50)
    fy = FOOTER_TOP + (H - FOOTER_TOP - 50 * 1.28) / 2
    centered(draw, fy, cfg["footer"], f_foot, T["footer_ink"])

    img.convert("RGB").save(out, quality=95)
    print(f"✅ {out}  {img.size}")


if __name__ == "__main__":
    cfg_path = Path(sys.argv[1])
    cfg = json.loads(cfg_path.read_text())
    out = sys.argv[2] if len(sys.argv) > 2 else str(cfg_path.with_suffix(".png"))
    build(cfg, out)
