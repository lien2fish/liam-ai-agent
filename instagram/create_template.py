#!/usr/bin/env python3
"""一次性執行：建立空白卡片模板（清除原圖可變內容區域）"""

from PIL import Image, ImageDraw
import os

ORIGINAL = '/Users/lien/Downloads/Gemini_Generated_Image_uzxp08uzxp08uzxp.png'
OUTPUT = os.path.join(os.path.dirname(__file__), 'template.png')

img = Image.open(ORIGINAL).convert('RGBA')
W, H = img.size  # 2816 x 1536
draw = ImageDraw.Draw(img)

# 卡片紙張底色（暖白，從原圖取樣）
PAPER = (248, 244, 234, 255)

# 清除：海鮮插圖區域（保留上方標題區 y<430）
draw.rectangle([600, 430, 2240, 820], fill=PAPER)

# 清除：日期/標題/內文區域
draw.rectangle([605, 830, 2240, 1280], fill=PAPER)

# 清除：左下角「海洋講堂」logo 區域
draw.rectangle([605, 1220, 1050, 1310], fill=PAPER)

img.save(OUTPUT, 'PNG')
print(f"模板已儲存：{OUTPUT}")
print(f"尺寸：{W} x {H}")
