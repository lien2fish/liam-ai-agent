"""大閘蟹推薦 DM（1080x1920）：IG 限動與 LINE 社團群組共用一張。

不寫產地、不放價格（Lien 2026-10-29 指定），導 IG 私訊。
照片：Wikimedia Commons「Roe inside steamed female hairy crab.jpg」，
Jpatokal，CC BY-SA 4.0——授權要求標示作者，所以底部有一行小字，不可拿掉。
（Lien 10-30 定案用母蟹實拍。可商用的公蟹蟹膏實拍找不到；
 AI 生成的公母版 ai_steamed_pair.png、v1 清蒸擺盤照 steamed_plate.jpg 都留在 assets。）
公母辨別出處：人民網 2017-09-28〈大闸蟹攻略〉、維基百科「中華絨螯蟹」。
"""

import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ig_carousel import (
    BOLD,
    DEEP,
    GOLD,
    GOLD_DIM,
    HEAVY,
    INK,
    INK_SOFT,
    REGULAR,
    REPO,
    font,
)

W, H = 1080, 1920
MARGIN = 88
SRC = os.path.join(REPO, "design/assets/hairy_crab/roe_steamed.jpg")
PHOTO_H = 940
PHOTO_FOCUS_Y = 0.56
OUT_DIR = os.path.join(REPO, "成品/DM/大閘蟹")

COPY = {
    "eyebrow": "連老闆・當季推薦",
    "title": "大閘蟹",
    "spec": "每隻 5.8–6.4 兩",
    "sub": "公母都有，一次吃到蟹黃與蟹膏",
    "rows": [
        ("母蟹", "圓臍，吃的是蟹黃"),
        ("公蟹", "尖臍，吃的是蟹膏"),
        ("吃法", "整隻清蒸，原味最好"),
    ],
    "cta": "私訊詢問",
    "handle": "@lienstable｜連老闆・鑫海產",
    "credit": "Photo: Jpatokal / CC BY-SA 4.0",
}


def photo():
    im = Image.open(SRC).convert("RGB")
    scale = W / im.width
    im = im.resize((W, round(im.height * scale)), Image.LANCZOS)
    top = min(max(0, round(im.height * PHOTO_FOCUS_Y - PHOTO_H / 2)), im.height - PHOTO_H)
    return im.crop((0, top, W, top + PHOTO_H))


def panel():
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    y0 = PHOTO_H - 420
    alpha = Image.new("L", (1, H))
    for i in range(H):
        t = min(1, max(0, (i - y0) / 420))
        alpha.putpixel((0, i), round(255 * t**1.4))
    shade = Image.new("RGBA", (W, H), DEEP + (255,))
    shade.putalpha(alpha.resize((W, H)))
    canvas.alpha_composite(shade)
    d = ImageDraw.Draw(canvas)

    y = PHOTO_H - 130
    d.text((MARGIN, y), COPY["eyebrow"], font=font(BOLD, 40), fill=GOLD)
    y += 62
    d.text((MARGIN, y), COPY["title"], font=font(HEAVY, 150), fill=INK)
    y += 190
    d.text((MARGIN, y), COPY["spec"], font=font(BOLD, 64), fill=GOLD)
    y += 92
    d.text((MARGIN, y), COPY["sub"], font=font(REGULAR, 40), fill=INK_SOFT)
    y += 84

    f_term, f_val = font(BOLD, 42), font(REGULAR, 42)
    for term, val in COPY["rows"]:
        d.line([(MARGIN, y), (W - MARGIN, y)], fill=(34, 56, 78), width=2)
        d.text((MARGIN, y + 21), term, font=f_term, fill=GOLD)
        d.text((MARGIN + 150, y + 21), val, font=f_val, fill=INK)
        y += 90
    d.line([(MARGIN, y), (W - MARGIN, y)], fill=(34, 56, 78), width=2)

    y += 48
    f_cta = font(BOLD, 46)
    cw = d.textlength(COPY["cta"], font=f_cta)
    bw, bh = cw + 120, 88
    bx = (W - bw) / 2
    d.rounded_rectangle([bx, y, bx + bw, y + bh], radius=bh / 2, outline=GOLD, width=3)
    d.text(((W - cw) / 2, y + 16), COPY["cta"], font=f_cta, fill=GOLD)

    y += bh + 28
    f_h = font(REGULAR, 34)
    hw = d.textlength(COPY["handle"], font=f_h)
    d.text(((W - hw) / 2, y), COPY["handle"], font=f_h, fill=INK_SOFT)

    f_c = font(REGULAR, 22)
    cw = d.textlength(COPY["credit"], font=f_c)
    d.text(((W - cw) / 2, y + 56), COPY["credit"], font=f_c, fill=GOLD_DIM)
    return canvas


def build():
    canvas = Image.new("RGBA", (W, H), DEEP + (255,))
    canvas.paste(photo(), (0, 0))
    canvas.alpha_composite(panel())
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "大閘蟹_1080x1920.jpg")
    canvas.convert("RGB").save(out, quality=94)
    print(out)


if __name__ == "__main__":
    build()
