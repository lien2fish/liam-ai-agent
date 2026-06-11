#!/usr/bin/env python3
"""惜食廚房一樓主視覺牆 v4 — 志工格改為橫向半A4以上 (A5橫式 210x148mm 比例)

牆面實際尺寸：3.42m x 1.46m
版面：10欄 x 4列志工格(共40格，剛好用完) + 5張廚師卡
來源背景：/Users/lien/Downloads/Gemini_Generated_Image_qfba0aqfba0aqfba.png (1584x672)
輸出：design/output/dry_goods_wall_v4_final.png
"""
import os
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = "/Users/lien/Downloads/Liam AI agent"
SRC = "/Users/lien/Downloads/Gemini_Generated_Image_qfba0aqfba0aqfba.png"
OUT_DIR = os.path.join(BASE_DIR, "design/output")

FONT_BOLD = "/System/Library/Fonts/ヒラギノ角ゴシック W7.ttc"

WALL_RATIO = 3.42 / 1.46  # ≈ 2.3425

GREEN = (108, 168, 74)
AMBER = (255, 201, 113)
WHITE = (255, 255, 255)
GRAY = (224, 224, 224)
SILHOUETTE = (190, 190, 190)
TITLE_COLOR = (201, 90, 46)
NUM_COLOR = (245, 163, 60)

# 放大2倍提升解析度
img = Image.open(SRC).convert("RGB")
W2, H2 = img.size[0] * 2, img.size[1] * 2
img = img.resize((W2, H2), Image.LANCZOS)

# 裁切為牆面比例
target_w = round(H2 * WALL_RATIO)
crop_x = (W2 - target_w) // 2
img = img.crop((crop_x, 0, crop_x + target_w, H2))
W, H = img.size  # ≈ 3148 x 1344
d = ImageDraw.Draw(img)


def rounded_rect(box, radius, fill):
    d.rounded_rectangle(box, radius=radius, fill=fill)


def draw_centered_text(box, text, font, fill):
    x0, y0, x1, y1 = box
    bb = d.textbbox((0, 0), text, font=font)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    x = x0 + ((x1 - x0) - w) / 2 - bb[0]
    y = y0 + ((y1 - y0) - h) / 2 - bb[1]
    d.text((x, y), text, font=font, fill=fill)


def draw_person_silhouette(box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    cx = (x0 + x1) / 2
    head_r = h * 0.18
    head_cy = y0 + h * 0.32
    d.ellipse(
        (cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r), fill=SILHOUETTE
    )
    body_w = w * 0.4
    body_top = head_cy + head_r * 0.6
    d.rounded_rectangle(
        (cx - body_w / 2, body_top, cx + body_w / 2, y1 - h * 0.08),
        radius=h * 0.06,
        fill=SILHOUETTE,
    )


# ---- 版面參數 ----
MARGIN = 60
GAP = 14
CONTENT_W = W - 2 * MARGIN

TITLE_H = 110
CHEF_H = 300

# 志工卡：10欄 x 4列 = 40格，橫向比例 210:148 (A5橫式)
VOL_COLS = 10
VOL_ROWS = 4
A5_RATIO = 210 / 148

remain_h = H - 2 * MARGIN - TITLE_H - GAP - CHEF_H - GAP - (VOL_ROWS - 1) * GAP
VOL_H = remain_h / VOL_ROWS
VOL_W = VOL_H * A5_RATIO

grid_w = VOL_COLS * VOL_W + (VOL_COLS - 1) * GAP
side_pad = (CONTENT_W - grid_w) / 2

# ---- 標題框 ----
title_box = (MARGIN, MARGIN, W - MARGIN, MARGIN + TITLE_H)
rounded_rect(title_box, radius=24, fill=WHITE)
title_font = ImageFont.truetype(FONT_BOLD, 64)
draw_centered_text(title_box, "惜食廚房大家庭", title_font, TITLE_COLOR)

# ---- 廚師卡片 (5張) ----
chef_top = title_box[3] + GAP
chef_w = (CONTENT_W - 4 * GAP) / 5
chef_font = ImageFont.truetype(FONT_BOLD, 48)

for i in range(5):
    x0 = MARGIN + i * (chef_w + GAP)
    x1 = x0 + chef_w
    y0 = chef_top
    y1 = chef_top + CHEF_H
    rounded_rect((x0, y0, x1, y1), radius=20, fill=WHITE)
    header_h = CHEF_H * 0.16
    rounded_rect((x0, y0, x1, y0 + header_h), radius=20, fill=GREEN)
    d.rectangle((x0, y0 + header_h - 20, x1, y0 + header_h), fill=GREEN)
    draw_centered_text((x0, y0, x1, y0 + header_h), f"廚師{i+1}", chef_font, WHITE)

    photo_box = (x0 + 14, y0 + header_h + 14, x1 - 14, y1 - 60)
    rounded_rect(photo_box, radius=14, fill=GRAY)
    draw_person_silhouette(photo_box)

    d.line((x0 + 36, y1 - 26, x1 - 36, y1 - 26), fill=(210, 200, 190), width=4)

# ---- 志工卡片 (10欄 x 4列 = 40, 橫向) ----
vol_top = chef_top + CHEF_H + GAP
vol_left = MARGIN + side_pad
badge_font = ImageFont.truetype(FONT_BOLD, 30)

num = 1
for r in range(VOL_ROWS):
    for c in range(VOL_COLS):
        x0 = vol_left + c * (VOL_W + GAP)
        y0 = vol_top + r * (VOL_H + GAP)
        x1 = x0 + VOL_W
        y1 = y0 + VOL_H

        rounded_rect((x0, y0, x1, y1), radius=14, fill=WHITE)
        header_h = VOL_H * 0.16
        rounded_rect((x0, y0, x1, y0 + header_h), radius=14, fill=AMBER)
        d.rectangle((x0, y0 + header_h - 14, x1, y0 + header_h), fill=AMBER)

        # 編號圓形徽章
        badge_d = header_h * 0.85
        bx1 = x1 - 8
        by_c = y0 + header_h / 2
        d.ellipse(
            (bx1 - badge_d, by_c - badge_d / 2, bx1, by_c + badge_d / 2), fill=WHITE
        )
        text = str(num)
        bb = d.textbbox((0, 0), text, font=badge_font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        d.text(
            (bx1 - badge_d / 2 - tw / 2 - bb[0], by_c - th / 2 - bb[1]),
            text,
            font=badge_font,
            fill=NUM_COLOR,
        )

        photo_box = (x0 + 8, y0 + header_h + 8, x1 - 8, y1 - 30)
        rounded_rect(photo_box, radius=10, fill=GRAY)
        draw_person_silhouette(photo_box)

        d.line((x0 + 16, y1 - 14, x1 - 16, y1 - 14), fill=(210, 200, 190), width=3)
        num += 1

os.makedirs(OUT_DIR, exist_ok=True)
out_path = os.path.join(OUT_DIR, "dry_goods_wall_v4_final.png")
img.save(out_path)

mm_per_px = 3420 / W
print(f"已儲存：{out_path}　尺寸：{img.size}　比例：{W/H:.4f}（目標 {WALL_RATIO:.4f}）")
print(
    f"志工卡尺寸：{VOL_W*mm_per_px:.1f} x {VOL_H*mm_per_px:.1f} mm（橫向，A5=210x148mm）"
)
print(f"廚師卡尺寸：{chef_w*mm_per_px:.1f} x {CHEF_H*mm_per_px:.1f} mm")
