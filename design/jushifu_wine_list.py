"""聚食釜 酒單 — A4 直式雙面，兩種美編調性。

    python3 design/jushifu_wine_list.py              # 兩版都產
    python3 design/jushifu_wine_list.py brick        # 只產 台式懷舊·紅磚金
    python3 design/jushifu_wine_list.py minimal      # 只產 米白極簡·日式留白

輸出：~/Desktop/聚食釜_酒單/
"""

import os
import sys
from PIL import Image, ImageDraw, ImageFont

DPI = 300
W, H = 2480, 3508

SONGTI = "/System/Library/Fonts/Supplemental/Songti.ttc"
PINGFANG = "/System/Library/Fonts/PingFang.ttc"
BASKERVILLE = "/System/Library/Fonts/Supplemental/Baskerville.ttc"
AVENIR = "/System/Library/Fonts/Avenir Next.ttc"

OUT_DIR = os.path.expanduser("~/Desktop/聚食釜_酒單")

BRAND_ZH = "聚食釜"
BRAND_EN = "JU SHI FU"
TAGLINE = "台式頂級蝦湯鍋物"
ADDRESS = "台北市大安區敦化南路二段 11 巷 2 號　02-2706-6600"

FOOTNOTES = [
    "以上均為單瓶售價，另收 10% 服務費",
    "酒款年份依實際到貨為準，售完為止",
]
LEGAL = "未滿十八歲禁止飲酒　禁止酒後駕車"


def item(name, winery, region, price, pair, cjk=False, winery_zh=""):
    return {
        "name": name,
        "winery": winery,
        "winery_zh": winery_zh,
        "region": region,
        "price": price,
        "pair": pair,
        "cjk": cjk,
    }


PAGE_FRONT = [
    {
        "zh": "氣泡酒",
        "en": "SPARKLING",
        "items": [
            item(
                "Canevel Brut Setàge",
                "CANEVEL",
                "義大利．瓦爾多比亞德內",
                1950,
                "細緻氣泡開場最有儀式感，也壓得住濃郁的綜合海鮮與蝦膏雜炊粥。",
            ),
        ],
    },
    {
        "zh": "白　酒",
        "en": "WHITE WINE",
        "items": [
            item(
                "Rosso & Bianco Chardonnay",
                "FRANCIS FORD COPPOLA WINERY",
                "美國．加州",
                988,
                "圓潤帶奶油與熟果香，遇上金黃蝦湯不打架，配鮮甜白肉與海鮮拼盤最順口。",
                winery_zh="教父酒莊",
            ),
            item(
                "Riesling Red Label",
                "SELBACH OSTER",
                "德國．摩塞爾",
                1288,
                "清冽酸度襯著一絲甜潤，解膩一流，最適合開場的冷前菜與有機菜盤。",
                winery_zh="賽爾巴哈奧斯特酒廠",
            ),
            item(
                "Marlborough Sauvignon Blanc",
                "KIM CRAWFORD",
                "紐西蘭．馬爾堡",
                1508,
                "熱帶果香奔放、酸度俐落，襯得出蝦湯的鮮甜，配醉仙花枝與紅蟹腿肉特別對味。",
                winery_zh="金卡佛",
            ),
            item(
                "Diamond Vibrance Pinot Grigio",
                "FRANCIS FORD COPPOLA WINERY",
                "美國．加州",
                1430,
                "爽脆明亮、口感輕盈，配雞胸肉與清爽海鮮，從菜盤喝到主食都不搶戲。",
                winery_zh="教父酒莊",
            ),
        ],
    },
]

PAGE_BACK = [
    {
        "zh": "紅　酒",
        "en": "RED WINE",
        "items": [
            item(
                "Estate Shiraz",
                "VIÑA ERRÁZURIZ",
                "智利．阿空加瓜谷",
                988,
                "黑莓與胡椒香氣、單寧柔順，為美國頂級肋眼與炙燒肉品而生。",
                winery_zh="伊拉蘇",
            ),
        ],
    },
    {
        "zh": "清　酒",
        "en": "SAKE",
        "items": [
            item(
                "雪之茅舎 純米 山廢",
                "齋彌酒造店",
                "秋田",
                1288,
                "山廢釀造的厚實酸度與米香，溫潤不搶味，最襯蝦湯的甘鮮。",
                cjk=True,
            ),
            item(
                "天吹 特別純米 夏之戀",
                "天吹酒造",
                "佐賀",
                2080,
                "花酵母釀成，香氣輕盈、口感微酸，冰鎮飲用最適合開場。",
                cjk=True,
            ),
            item(
                "秀鳳 純米大吟釀 出羽燦燦",
                "秀鳳酒造場",
                "山形",
                2340,
                "果香華麗、質地細緻綿長，配生食級海鮮與清爽前菜最見層次。",
                cjk=True,
            ),
        ],
    },
    {
        "zh": "甜　酒",
        "en": "DESSERT WINE",
        "items": [
            item(
                "Moscato d'Asti DOCG",
                "TOSTI",
                "義大利．皮埃蒙特",
                1027,
                "低酒精、蜜甜微氣泡，最能安撫辣度，也適合佐餐後甜點收尾。",
            ),
        ],
    },
]


THEMES = {
    "brick": {
        "label": "紅磚金",
        "bg": (245, 237, 224),
        "ink": (58, 42, 32),
        "accent": (156, 59, 40),
        "gold": (200, 147, 64),
        "muted": (128, 104, 86),
        "noise": True,
        "band": True,
        "leader": True,
        "margin": 200,
        "zh_title": (SONGTI, 2),
        "zh_med": (SONGTI, 2),
        "zh_body": (SONGTI, 7),
        "zh_light": (SONGTI, 5),
        "latin": (BASKERVILLE, 0),
        "latin_it": (BASKERVILLE, 2),
        "rule_w": 3,
        "hair_w": 2,
    },
    "minimal": {
        "label": "米白極簡",
        "bg": (250, 248, 244),
        "ink": (40, 38, 35),
        "accent": (40, 38, 35),
        "gold": (168, 160, 150),
        "muted": (134, 128, 120),
        "noise": False,
        "band": False,
        "leader": False,
        "margin": 270,
        "zh_title": (PINGFANG, 1),
        "zh_med": (PINGFANG, 4),
        "zh_body": (PINGFANG, 4),
        "zh_light": (PINGFANG, 1),
        "latin": (AVENIR, 7),
        "latin_it": (AVENIR, 5),
        "rule_w": 2,
        "hair_w": 1,
    },
}


def font(spec, size):
    path, index = spec
    return ImageFont.truetype(path, size, index=index)


def tw(draw, text, f, tracking=0):
    if not text:
        return 0
    w = draw.textlength(text, font=f)
    return w + tracking * (len(text) - 1)


def draw_track(draw, x, y, text, f, fill, tracking=0, anchor_left=True):
    if tracking == 0:
        draw.text((x, y), text, font=f, fill=fill)
        return draw.textlength(text, font=f)
    cx = x
    for ch in text:
        draw.text((cx, y), ch, font=f, fill=fill)
        cx += draw.textlength(ch, font=f) + tracking
    return cx - tracking - x


def center_track(draw, cx, y, text, f, fill, tracking=0):
    w = tw(draw, text, f, tracking)
    draw_track(draw, cx - w / 2, y, text, f, fill, tracking)
    return w


def wrap_cjk(draw, text, f, max_w):
    lines, cur = [], ""
    for ch in text:
        if tw(draw, cur + ch, f) > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def paper(theme):
    img = Image.new("RGB", (W, H), theme["bg"])
    if theme["noise"]:
        n = Image.effect_noise((W // 3, H // 3), 30).convert("L")
        n = n.resize((W, H), Image.BILINEAR).convert("RGB")
        img = Image.blend(img, n, 0.05)
    return img


def brick_band(img, y, h, color, alpha=30):
    ov = Image.new("RGBA", (W, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    bw, bh = 96, 32
    c = color + (alpha,)
    row = 0
    yy = 0
    while yy < h:
        d.line([(0, yy), (W, yy)], fill=c, width=2)
        off = 0 if row % 2 == 0 else bw // 2
        x = off
        while x < W:
            d.line([(x, yy), (x, min(yy + bh, h))], fill=c, width=2)
            x += bw
        yy += bh
        row += 1
    img.paste(
        Image.alpha_composite(img.crop((0, y, W, y + h)).convert("RGBA"), ov).convert(
            "RGB"
        ),
        (0, y),
    )


def diamond_rule(draw, theme, cx, y, half, with_gem=True):
    g = theme["gold"]
    gem = 13 if with_gem else 0
    draw.line([(cx - half, y), (cx - gem - 14, y)], fill=g, width=theme["hair_w"])
    draw.line([(cx + gem + 14, y), (cx + half, y)], fill=g, width=theme["hair_w"])
    if with_gem:
        draw.polygon(
            [(cx, y - gem), (cx + gem, y), (cx, y + gem), (cx - gem, y)],
            fill=theme["accent"],
        )


# ---------------------------------------------------------------- 版面


def build_page(theme, sections, front, want_height=False):
    img = paper(theme)
    d = ImageDraw.Draw(img)
    m = theme["margin"]
    cx = W // 2
    inner = W - 2 * m

    f_brand = font(theme["zh_title"], 168 if front else 92)
    f_brand_en = font(theme["latin"], 40)
    f_tag = font(theme["zh_light"], 44)
    f_wl = font(theme["latin"], 50)
    f_sec = font(theme["zh_med"], 68)
    f_sec_en = font(theme["latin"], 33)
    f_name = font(theme["zh_body"], 62)
    f_wine = font(theme["latin"], 60)
    f_winery = font(theme["latin"], 31)
    f_reg = font(theme["zh_light"], 30)
    f_price = font(theme["latin"], 62)
    f_pair = font(theme["zh_light"], 40)
    f_note = font(theme["zh_light"], 34)
    f_legal = font(theme["zh_light"], 32)

    if theme["band"]:
        brick_band(img, 0, 96, theme["accent"], 26)
        brick_band(img, H - 96, 96, theme["accent"], 26)

    y = m + (60 if front else 40)

    # ---- 抬頭
    if front:
        center_track(d, cx, y, BRAND_EN, f_brand_en, theme["gold"], 22)
        y += 84
        center_track(d, cx, y, BRAND_ZH, f_brand, theme["accent"], 34)
        y += 232
        center_track(d, cx, y, TAGLINE, f_tag, theme["muted"], 10)
        y += 104
        diamond_rule(d, theme, cx, y, inner // 2 - 120, with_gem=theme["band"])
        y += 62
        center_track(d, cx, y, "WINE LIST", f_wl, theme["ink"], 26)
        y += 130
    else:
        center_track(d, cx, y, BRAND_ZH, f_brand, theme["accent"], 24)
        y += 130
        diamond_rule(d, theme, cx, y, inner // 2 - 120, with_gem=theme["band"])
        y += 90

    # ---- 量測：先算內容高度，把剩餘空間分配到間距
    pair_w = int(inner * 0.78)
    sec_h, item_gap, sec_gap = 132, 54, 92
    blocks = []
    for si, sec in enumerate(sections):
        blocks.append(("sec", sec_h, sec))
        for ii, it in enumerate(sec["items"]):
            lines = wrap_cjk(d, it["pair"], f_pair, pair_w)
            h = 84 + 46 + 58 * len(lines)
            blocks.append(("item", h, (it, lines)))
            if ii < len(sec["items"]) - 1:
                blocks.append(("gap", item_gap, None))
        if si < len(sections) - 1:
            blocks.append(("gap", sec_gap, None))

    foot_h = 0
    if not front:
        foot_h = 60 + 52 * len(FOOTNOTES) + 44 + 52 + 60

    content_h = sum(b[1] for b in blocks)
    avail = H - m - (100 if theme["band"] else 0) - foot_h - y
    slack = avail - content_h
    n_gaps = sum(1 for b in blocks if b[0] == "gap") + len(sections)
    extra = max(0, min(slack / max(n_gaps, 1), 110))

    # ---- 繪製
    for kind, h, payload in blocks:
        if kind == "gap":
            y += h + extra
            continue
        if kind == "sec":
            sec = payload
            draw_track(d, m, y, sec["zh"], f_sec, theme["accent"], 6)
            ew = tw(d, sec["en"], f_sec_en, 14)
            draw_track(d, W - m - ew, y + 30, sec["en"], f_sec_en, theme["gold"], 14)
            ry = y + 96
            d.line([(m, ry), (W - m, ry)], fill=theme["gold"], width=theme["rule_w"])
            y += h + extra
            continue

        it, lines = payload
        price = f"{it['price']:,}"
        pw = d.textlength(price, font=f_price)
        f_main = f_name if it["cjk"] else f_wine
        nw = d.textlength(it["name"], font=f_main)
        d.text((m, y), it["name"], font=f_main, fill=theme["ink"])
        d.text((W - m - pw, y), price, font=f_price, fill=theme["accent"])
        if theme["leader"]:
            lx = m + nw + 34
            rx = W - m - pw - 34
            dy = y + 44
            while lx < rx:
                d.ellipse([lx, dy, lx + 4, dy + 4], fill=theme["gold"])
                lx += 26
        y += 84
        if it["cjk"]:
            sub_x = m + draw_track(d, m, y + 4, it["winery"], f_reg, theme["gold"], 6)
        else:
            sub_x = m + draw_track(
                d, m, y + 6, it["winery"], f_winery, theme["gold"], 9
            )
            if it["winery_zh"]:
                sub_x += 18
                sub_x += draw_track(
                    d, sub_x, y + 4, it["winery_zh"], f_reg, theme["gold"], 2
                )
        sx = sub_x + 26
        d.line([(sx, y + 8), (sx, y + 38)], fill=theme["gold"], width=theme["hair_w"])
        d.text((sx + 20, y + 4), it["region"], font=f_reg, fill=theme["muted"])
        y += 46
        for ln in lines:
            d.text((m, y + 8), ln, font=f_pair, fill=theme["muted"])
            y += 58

    # ---- 頁尾
    if not front:
        fy = H - m - (100 if theme["band"] else 0) - foot_h + 60
        diamond_rule(d, theme, cx, fy, inner // 2 - 260, with_gem=False)
        fy += 44
        for t in FOOTNOTES:
            center_track(d, cx, fy, t, f_note, theme["muted"], 4)
            fy += 52
        fy += 22
        center_track(d, cx, fy, ADDRESS, f_note, theme["ink"], 3)
        fy += 62
        center_track(d, cx, fy, LEGAL, f_legal, theme["accent"], 6)

    return img


def main():
    which = sys.argv[1:] or list(THEMES)
    os.makedirs(OUT_DIR, exist_ok=True)
    for key in which:
        theme = THEMES[key]
        front = build_page(theme, PAGE_FRONT, True)
        back = build_page(theme, PAGE_BACK, False)
        tag = theme["label"]
        front.save(f"{OUT_DIR}/聚食釜酒單_{tag}_正面.png", dpi=(DPI, DPI))
        back.save(f"{OUT_DIR}/聚食釜酒單_{tag}_背面.png", dpi=(DPI, DPI))
        front.save(
            f"{OUT_DIR}/聚食釜酒單_{tag}.pdf",
            "PDF",
            resolution=DPI,
            save_all=True,
            append_images=[back],
        )
        print(f"✅ {tag}：正面 / 背面 PNG + 雙頁 PDF")
    print(f"→ {OUT_DIR}")


if __name__ == "__main__":
    main()
