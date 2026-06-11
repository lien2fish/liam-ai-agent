#!/usr/bin/env python3
"""惜食廚房一樓主視覺牆 v2 — 在 Gemini 生成的暖色公益背景上用 PIL 疊加版面網格

來源圖：/Users/lien/Downloads/Gemini_Generated_Image_qfba0aqfba0aqfba.png (1584x672)
輸出：design/output/dry_goods_wall_v2_final.png，裁切為牆面比例 3.42:1.46
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
d = ImageDraw.Draw(img)

# 內容安全區（避開邊框圖案）
LEFT, RIGHT = 150, W2 - 150
TOP, BOTTOM = 150, H2 - 150
INNER_W = RIGHT - LEFT
INNER_H = BOTTOM - TOP


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
    body_w = w * 0.5
    body_top = head_cy + head_r * 0.6
    d.rounded_rectangle(
        (cx - body_w / 2, body_top, cx + body_w / 2, y1 - h * 0.06),
        radius=h * 0.08,
        fill=SILHOUETTE,
    )


# ---- 標題框 ----
title_w, title_h = 1200, 100
title_box = ((W2 - title_w) // 2, TOP + 8, (W2 + title_w) // 2, TOP + 8 + title_h)
rounded_rect(title_box, radius=24, fill=WHITE)
title_font = ImageFont.truetype(FONT_BOLD, 58)
draw_centered_text(title_box, "惜食廚房大家庭", title_font, TITLE_COLOR)

# ---- 廚師卡片 (5張) ----
chef_top = title_box[3] + 20
chef_h = 170
gap = 20
chef_w = (INNER_W - gap * 4) / 5
chef_font = ImageFont.truetype(FONT_BOLD, 36)

for i in range(5):
    x0 = LEFT + i * (chef_w + gap)
    x1 = x0 + chef_w
    y0 = chef_top
    y1 = chef_top + chef_h
    rounded_rect((x0, y0, x1, y1), radius=20, fill=WHITE)
    header_h = chef_h * 0.22
    rounded_rect((x0, y0, x1, y0 + header_h), radius=20, fill=GREEN)
    d.rectangle((x0, y0 + header_h - 20, x1, y0 + header_h), fill=GREEN)
    draw_centered_text((x0, y0, x1, y0 + header_h), f"廚師{i+1}", chef_font, WHITE)

    photo_box = (x0 + 12, y0 + header_h + 12, x1 - 12, y1 - 50)
    rounded_rect(photo_box, radius=12, fill=GRAY)
    draw_person_silhouette(photo_box)

    # caption strip (留白待填姓名)
    d.line((x0 + 30, y1 - 22, x1 - 30, y1 - 22), fill=(210, 200, 190), width=3)

# ---- 志工卡片 (8欄 x 5列 = 40) ----
vol_top = chef_top + chef_h + 20
vol_h = INNER_H - (vol_top - TOP)
cols, rows = 8, 5
vgap = 10
col_w = (INNER_W - vgap * (cols - 1)) / cols
row_h = (vol_h - vgap * (rows - 1)) / rows
badge_font = ImageFont.truetype(FONT_BOLD, 26)

num = 1
for r in range(rows):
    for c in range(cols):
        x0 = LEFT + c * (col_w + vgap)
        y0 = vol_top + r * (row_h + vgap)
        x1 = x0 + col_w
        y1 = y0 + row_h
        rounded_rect((x0, y0, x1, y1), radius=10, fill=WHITE)
        header_h = row_h * 0.22
        rounded_rect((x0, y0, x1, y0 + header_h), radius=10, fill=AMBER)
        d.rectangle((x0, y0 + header_h - 10, x1, y0 + header_h), fill=AMBER)

        # 編號圓形徽章
        badge_d = header_h * 0.85
        bx1 = x1 - 6
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

        photo_box = (x0 + 6, y0 + header_h + 6, x1 - 6, y1 - 16)
        rounded_rect(photo_box, radius=8, fill=GRAY)
        draw_person_silhouette(photo_box)

        d.line((x0 + 12, y1 - 8, x1 - 12, y1 - 8), fill=(210, 200, 190), width=2)
        num += 1

# ---- 裁切為牆面比例 ----
target_w = round(H2 * WALL_RATIO)
crop_x = (W2 - target_w) // 2
img = img.crop((crop_x, 0, crop_x + target_w, H2))

os.makedirs(OUT_DIR, exist_ok=True)
out_path = os.path.join(OUT_DIR, "dry_goods_wall_v2_final.png")
img.save(out_path)
print(
    f"已儲存：{out_path}　尺寸：{img.size}　比例：{img.size[0]/img.size[1]:.4f}（目標 {WALL_RATIO:.4f}）"
)
