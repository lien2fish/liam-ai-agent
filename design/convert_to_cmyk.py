#!/usr/bin/env python3
"""批次將 惜食廚房輸出/ 的 PNG 轉為 CMYK TIFF（印刷用）"""

from PIL import Image
import os

SRC  = "/Users/lien/Desktop/惜食廚房輸出"
DEST = "/Users/lien/Desktop/惜食廚房輸出/CMYK_印刷版"
os.makedirs(DEST, exist_ok=True)

def to_cmyk_tif(src_path, dest_path, dpi=300):
    img = Image.open(src_path)
    
    if img.mode == "RGBA":
        # 透明區域壓平到白底（印刷無透明概念）
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        rgb = bg
    elif img.mode == "RGB":
        rgb = img
    else:
        rgb = img.convert("RGB")

    cmyk = rgb.convert("CMYK")
    cmyk.save(dest_path, "TIFF", dpi=(dpi, dpi), compression="lzw")
    kb = os.path.getsize(dest_path) // 1024
    print(f"  ✅ {os.path.basename(dest_path)}  ({kb:,} KB)")

print(f"🎨 CMYK 轉換開始 → {DEST}\n")
count = 0
for fname in sorted(os.listdir(SRC)):
    if not fname.lower().endswith(".png"):
        continue
    src  = os.path.join(SRC, fname)
    dest = os.path.join(DEST, fname.replace(".png", ".tif"))
    print(f"  處理：{fname}")
    to_cmyk_tif(src, dest)
    count += 1

print(f"\n🎉 完成！共轉換 {count} 張 → {DEST}")
