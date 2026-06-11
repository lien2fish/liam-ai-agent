#!/usr/bin/env python3
"""惜食廚房一樓主視覺牆 — 志工名單展示牆底圖生成（Gemini 2.5 Flash Image）

牆面實際尺寸：3.42m x 1.46m（比例約 2.34:1）
版面：標題 + 5位廚師卡片 + 40位志工卡片（8欄x5列）空白範本，文字另外用 PIL 疊加
"""
import base64
import json
import os
import urllib.request
from PIL import Image

BASE_DIR = "/Users/lien/Downloads/Liam AI agent"
CONFIG_PATH = os.path.join(BASE_DIR, "config/instagram_config.json")
OUT_DIR = os.path.join(BASE_DIR, "design/output")

with open(CONFIG_PATH) as f:
    GEMINI_KEY = json.load(f)["gemini_api_key"]

# 牆面比例 3.42 : 1.46
WALL_RATIO = 3.42 / 1.46  # ≈ 2.3425
TARGET_W = 3000
TARGET_H = round(TARGET_W / WALL_RATIO)  # ≈ 1281

PROMPT = """
Create a flat vector illustration design template for a large wall mural,
ultra-wide horizontal banner, aspect ratio approximately 2.34:1 (for a
3.42m x 1.46m wall). Warm golden-cream background (#FFF3DD tone, soft amber
glow gradient) with a thick rounded border made of heartwarming charity and
food-sharing illustrations: hands offering bowls of warm food, hands holding
small hearts, people hugging, volunteers carrying food donation boxes,
steaming bowls of rice/soup, fresh vegetables (tomato, carrot, broccoli),
food donation boxes with heart stickers, small smiling sun icons, scattered
around all four edges in a friendly, playful, flat vector style with a warm
amber, soft orange, and gentle green color palette (#F5A33C, #FFC971,
#6CA84A, #E8855A).

Layout (top to bottom, evenly proportioned for a wide banner):

1. A centered title banner area at the top spanning the full width, with
   empty blank space reserved for a bold rounded Chinese title (do not
   render any text), flanked by decorative hands-holding-heart and
   food-sharing icons on both sides.

2. A single row of 5 equal-width rectangular cards side by side, each card:
   - a header bar in soft green (#6CA84A), left empty for a label
   - below the header, a light-gray rounded rectangle photo placeholder
     showing a simple flat blank silhouette icon of a person in chef uniform
   - a thin empty caption strip below the photo for name and slogan text

3. Below that, a grid of 40 smaller identical cards arranged in 8 columns x
   5 rows, each card:
   - a header bar in warm amber (#FFC971) with a small empty circular
     number badge in the top-right corner
   - a light-gray rounded rectangle photo placeholder showing a simple flat
     blank silhouette icon of a person wearing an apron
   - a thin empty caption strip below for name and slogan text

All cards: soft rounded corners, subtle warm-toned drop shadows, white card
backgrounds, consistent spacing and alignment in a clean grid, evenly
filling the wide banner. Overall mood: warm, caring, hopeful,
community-driven charity kitchen aesthetic, emphasizing human connection
and food sharing rather than just kitchen tools. Flat vector illustration
style, no photographic elements, leave all text areas completely
blank/empty for later text overlay.
"""


def generate():
    model = "gemini-2.5-flash-image"
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={GEMINI_KEY}"
    )
    body = {
        "contents": [{"parts": [{"text": PROMPT}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())

    os.makedirs(OUT_DIR, exist_ok=True)
    parts = data["candidates"][0]["content"]["parts"]
    for part in parts:
        inline = part.get("inlineData") or part.get("inline_data")
        if inline:
            img_bytes = base64.b64decode(inline["data"])
            raw_path = os.path.join(OUT_DIR, "dry_goods_wall_raw.png")
            with open(raw_path, "wb") as f:
                f.write(img_bytes)
            print(f"已儲存原始圖：{raw_path}")
            crop_to_wall_ratio(raw_path)
            return

    print("未取得圖片，回應內容：")
    print(json.dumps(data, ensure_ascii=False, indent=2)[:2000])


def crop_to_wall_ratio(raw_path):
    img = Image.open(raw_path).convert("RGB")
    w, h = img.size
    target_ratio = TARGET_W / TARGET_H

    if w / h > target_ratio:
        new_w = round(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        new_h = round(w / target_ratio)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))

    img = img.resize((TARGET_W, TARGET_H), Image.LANCZOS)
    out_path = os.path.join(OUT_DIR, "dry_goods_wall_3.42x1.46m.png")
    img.save(out_path)
    print(f"已裁切為牆面比例 ({TARGET_W}x{TARGET_H})：{out_path}")


if __name__ == "__main__":
    generate()
