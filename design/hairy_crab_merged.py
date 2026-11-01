"""大閘蟹限動三連發合成單張（1080x1920）：主視覺＋公母腹面＋規格＋私訊詢問。

版型、照片、事實出處都沿用 design/hairy_crab_story.py；照片作者標示不可拿掉。
"""

import os
import random
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hairy_crab_story import (
    BRUSH,
    CREDIT,
    H,
    W,
    background,
    belly,
    brush,
    fade_top,
    photo,
    text_shadow,
)
from ig_carousel import GOLD, HEAVY, BOLD, INK, INK_SOFT, REGULAR, REPO, font

OUT = os.path.join(REPO, "成品/DM/大閘蟹/大閘蟹_合併版_1080x1920.jpg")
DARK = (20, 16, 10)


def fade_both(img, top, bottom):
    img = fade_top(img, top)
    a = img.getchannel("A")
    d = ImageDraw.Draw(a)
    for i in range(bottom):
        y = img.height - 1 - i
        d.line(
            [(0, y), (img.width, y)], fill=int(a.getpixel((0, y)) * (i / bottom) ** 1.3)
        )
    img.putalpha(a)
    return img


def cta_band(c, by):
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    bd.polygon(
        [(0, by + 18), (W, by + 6), (W, by + 150), (0, by + 140)], fill=BRUSH + (255,)
    )
    rnd = random.Random(44)
    for _ in range(70):
        off = rnd.choice((-1, 1)) * rnd.uniform(55, 82)
        bd.line(
            [
                (rnd.uniform(-20, 40), by + 80 + off),
                (W - rnd.uniform(-20, 60), by + 70 + off + rnd.uniform(-6, 6)),
            ],
            fill=BRUSH + (rnd.randint(170, 255),),
            width=rnd.randint(3, 6),
        )
    c.alpha_composite(band)
    d = ImageDraw.Draw(c)
    d.text((300, by + 72), "私訊詢問", font=font(HEAVY, 92), fill=DARK, anchor="mm")
    d.line([(545, by + 30), (545, by + 116)], fill=DARK, width=4)
    d.text((585, by + 30), "@lienstable", font=font(HEAVY, 46), fill=DARK)
    d.text((585, by + 88), "連老闆・鑫海產", font=font(BOLD, 34), fill=DARK)


def merged():
    c = background(4)
    ph = fade_both(photo(W, 560, 0.55), 160, 160)
    c.alpha_composite(ph, (0, 520))
    ImageDraw.Draw(c).text(
        (W - 40, 1010),
        CREDIT,
        font=font(REGULAR, 20),
        fill=(170, 160, 140),
        anchor="ra",
    )

    d = ImageDraw.Draw(c)
    d.text((W / 2, 70), "鑫海產", font=font(HEAVY, 52), fill=GOLD, anchor="ma")
    d.text(
        (W / 2, 136),
        "連老闆・產地到餐桌",
        font=font(REGULAR, 24),
        fill=INK_SOFT,
        anchor="ma",
    )
    text_shadow(c, (W / 2, 190), "六兩大閘蟹", font(HEAVY, 150), INK, "ma")
    text_shadow(c, (W / 2, 370), "母蟹吃黃・公蟹吃膏", font(HEAVY, 84), BRUSH, "ma")
    brush(c, 150, 930, 488, 14, 11)

    text_shadow(c, (W / 2, 1050), "公的母的，翻過來看肚子", font(HEAVY, 58), INK, "ma")
    belly(c, 290, 1270, 0.72, True)
    belly(c, 790, 1270, 0.72, False)
    d = ImageDraw.Draw(c)
    for x, a, b in ((290, "母蟹・圓臍", "吃蟹黃"), (790, "公蟹・尖臍", "吃蟹膏")):
        d.text((x, 1385), a, font=font(HEAVY, 48), fill=BRUSH, anchor="ma")
        d.text((x, 1445), b, font=font(BOLD, 40), fill=INK, anchor="ma")

    d.line([(110, 1520), (W - 110, 1520)], fill=(90, 80, 60), width=2)
    d.text(
        (W / 2, 1544),
        "每隻 5.8–6.4 兩・公母都有・整隻清蒸",
        font=font(BOLD, 42),
        fill=INK,
        anchor="ma",
    )
    d.text(
        (W / 2, 1604),
        "老話說「九雌十雄」：農曆九月吃母蟹，十月吃公蟹",
        font=font(REGULAR, 30),
        fill=INK_SOFT,
        anchor="ma",
    )

    cta_band(c, 1660)
    d = ImageDraw.Draw(c)
    d.text(
        (W / 2, 1862),
        "腹面為示意圖｜資料：人民網、維基百科「中華絨螯蟹」",
        font=font(REGULAR, 22),
        fill=INK_SOFT,
        anchor="ma",
    )
    return c


if __name__ == "__main__":
    merged().convert("RGB").save(OUT, quality=94)
    print(OUT)
