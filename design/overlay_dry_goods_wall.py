#!/usr/bin/env python3
"""惜食廚房一樓主視覺牆 — 在 Gemini 生成的空白範本上疊加標題與編號文字

來源圖：/Users/lien/Downloads/Gemini_Generated_Image_u1x0a6u1x0a6u1x0.png (1584x672)
輸出：design/output/dry_goods_wall_final.png，裁切為牆面比例 3.42:1.46
"""
import os
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = "/Users/lien/Downloads/Liam AI agent"
SRC = "/Users/lien/Downloads/Gemini_Generated_Image_u1x0a6u1x0a6u1x0.png"
OUT_DIR = os.path.join(BASE_DIR, "design/output")

FONT_BOLD = "/System/Library/Fonts/ヒラギノ角ゴシック W7.ttc"
FONT_MED = "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc"

# 牆面比例 3.42 : 1.46
WALL_RATIO = 3.42 / 1.46  # ≈ 2.3425

img = Image.open(SRC).convert("RGB")
W, H = img.size  # 1584 x 672

# 兩側微裁切，符合牆面比例
target_w = round(H * WALL_RATIO)
crop_x = (W - target_w) // 2
img = img.crop((crop_x, 0, crop_x + target_w, H))
d = ImageDraw.Draw(img)

# 座標已扣除左側裁切量
ox = -crop_x


def cx_text(text, font):
    bb = d.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1], bb[0], bb[1]


def draw_centered(box, text, font, fill):
    x0, y0, x1, y1 = box
    w, h, bx0, by0 = cx_text(text, font)
    x = x0 + ((x1 - x0) - w) / 2 - bx0
    y = y0 + ((y1 - y0) - h) / 2 - by0
    d.text((x, y), text, font=font, fill=fill)


# ---- 標題 ----
title_box = (507 + ox, 19, 1075 + ox, 85)
title_font = ImageFont.truetype(FONT_BOLD, 50)
draw_centered(title_box, "惜食廚房大家庭", title_font, (200, 90, 40))

# ---- 廚師卡片 (5張) ----
chef_xs = [98, 383, 668, 952, 1237]
chef_w = 248
chef_header_box_y = (130, 163)
chef_font = ImageFont.truetype(FONT_BOLD, 28)
for i, x in enumerate(chef_xs, start=1):
    box = (x + ox, chef_header_box_y[0], x + ox + chef_w, chef_header_box_y[1])
    draw_centered(box, f"廚師{i}", chef_font, (255, 255, 255))

# ---- 志工卡片 (16欄 x 3列, 編號 1~40, 第3列9~16欄留白備用) ----
vol_xs = [
    91,
    179,
    268,
    356,
    445,
    534,
    622,
    711,
    799,
    888,
    976,
    1064,
    1153,
    1241,
    1330,
    1419,
]
vol_w = 59
vol_header_ys = [(303, 323), (408, 428), (512, 532)]
badge_d = 16
badge_font = ImageFont.truetype(FONT_BOLD, 13)

num = 1
for row, (hy0, hy1) in enumerate(vol_header_ys):
    for col, x in enumerate(vol_xs):
        if row == 2 and col >= 8:
            continue  # 第3列後8格留白備用
        cx_pos = x + ox + vol_w - badge_d / 2 - 2
        cy_pos = hy0 + (hy1 - hy0) / 2
        r = badge_d / 2
        d.ellipse(
            (cx_pos - r, cy_pos - r, cx_pos + r, cy_pos + r),
            fill=(255, 255, 255),
        )
        text = str(num)
        bb = d.textbbox((0, 0), text, font=badge_font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        d.text(
            (cx_pos - tw / 2 - bb[0], cy_pos - th / 2 - bb[1]),
            text,
            font=badge_font,
            fill=(241, 157, 60),
        )
        num += 1

os.makedirs(OUT_DIR, exist_ok=True)
out_path = os.path.join(OUT_DIR, "dry_goods_wall_final.png")
img.save(out_path)
print(
    f"已儲存：{out_path}　尺寸：{img.size}　比例：{img.size[0]/img.size[1]:.4f}（目標 {WALL_RATIO:.4f}）"
)
