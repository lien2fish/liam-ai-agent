"""大閘蟹怎麼分級 DM（1080x1920）：規格 × 肥滿度 → 精品／優選／標準。

版型沿用 design/hairy_crab_story.py。數字出處：江蘇省漁業協會團體標準
《陽澄湖大閘蟹等級標準》編制說明（2025-07 徵求意見稿）表 2～表 4。
只講分級方法，不宣稱自家貨屬於哪一級、不寫產地、不放價格。
台兩＝37.5 g（大陸的「兩」是 50 g，兩邊不同）。
"""

import os
import sys

from PIL import ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hairy_crab_merged import cta_band
from hairy_crab_story import BRUSH, W, background, brush, text_shadow
from ig_carousel import BOLD, GOLD, HEAVY, INK, INK_SOFT, REGULAR, REPO, font

OUT = os.path.join(REPO, "成品/DM/大閘蟹/大閘蟹_分級_1080x1920.jpg")
LINE = (90, 80, 60)
SIZES = [("A", 200, 175), ("B", 175, 150), ("C", 150, 125)]
MATRIX = [
    ("A", "精品", "優選", "標準"),
    ("B", "優選", "標準", "—"),
    ("C", "標準", "—", "—"),
]


def step(d, y, s):
    d.text((110, y), s, font=font(HEAVY, 50), fill=BRUSH)


def grade():
    c = background(5)
    d = ImageDraw.Draw(c)
    d.text((W / 2, 70), "鑫海產", font=font(HEAVY, 52), fill=GOLD, anchor="ma")
    d.text(
        (W / 2, 136),
        "連老闆・產地到餐桌",
        font=font(REGULAR, 24),
        fill=INK_SOFT,
        anchor="ma",
    )
    text_shadow(c, (W / 2, 190), "大閘蟹怎麼分級", font(HEAVY, 124), INK, "ma")
    text_shadow(c, (W / 2, 350), "看重量，也看肥不肥", font(HEAVY, 72), BRUSH, "ma")
    brush(c, 190, 890, 448, 14, 55)

    d = ImageDraw.Draw(c)
    step(d, 500, "① 先秤重")
    y = 570
    for x, s in ((200, "規格"), (520, "公蟹"), (850, "母蟹")):
        d.text((x, y), s, font=font(BOLD, 36), fill=INK_SOFT, anchor="ma")
    for k, m, f in SIZES:
        y += 100
        if k == "A":
            d.line([(110, y - 30), (W - 110, y - 30)], fill=LINE, width=2)
        d.text((200, y + 4), k, font=font(HEAVY, 46), fill=BRUSH, anchor="ma")
        for x, g in ((520, m), (850, f)):
            d.text((x, y - 6), f"≥ {g} g", font=font(BOLD, 40), fill=INK, anchor="ma")
            d.text((x, y + 42), f"約 {g / 37.5:.1f} 台兩", font=font(REGULAR, 26), fill=INK_SOFT, anchor="ma")

    step(d, 985, "② 再看肥滿度，分三檔")
    for i, s in enumerate(
        (
            "第三對腳越硬、背跟肚子之間越鼓、",
            "掀開蟹臍透出的顏色越深，檔次越高",
        )
    ):
        d.text((110, 1062 + i * 58), s, font=font(BOLD, 40), fill=INK)

    step(d, 1200, "③ 兩者合起來定等級")
    y = 1278
    cols = (170, 420, 660, 900)
    for x, s in zip(cols, ("", "第一檔", "第二檔", "第三檔")):
        d.text((x, y), s, font=font(BOLD, 36), fill=INK_SOFT, anchor="ma")
    for row in MATRIX:
        y += 74
        d.line([(110, y - 14), (W - 110, y - 14)], fill=LINE, width=2)
        d.text((cols[0], y), row[0], font=font(HEAVY, 46), fill=BRUSH, anchor="ma")
        for x, s in zip(cols[1:], row[1:]):
            color = BRUSH if s == "精品" else (INK if s != "—" else LINE)
            d.text(
                (x, y),
                s,
                font=font(HEAVY if s == "精品" else BOLD, 42),
                fill=color,
                anchor="ma",
            )

    cta_band(c, 1585)
    d = ImageDraw.Draw(c)
    for i, s in enumerate(
        (
            "資料：江蘇省漁業協會《陽澄湖大閘蟹等級標準》",
            "編制說明（2025 徵求意見稿）｜1 台兩＝37.5 g",
        )
    ):
        d.text(
            (W / 2, 1800 + i * 36),
            s,
            font=font(REGULAR, 24),
            fill=INK_SOFT,
            anchor="ma",
        )
    return c


if __name__ == "__main__":
    grade().convert("RGB").save(OUT, quality=94)
    print(OUT)
