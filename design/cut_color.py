"""顏色判定去背 v2：白牆=低飽和高亮度且與邊界相連(flood-fill)；
內部白圓(中心圓牌)因被彩色包圍、不與邊界相連而保留。輸出全解析度透明 PNG。
用法: python3 cut_color.py 來源 輸出 [sat門檻] [val門檻] [feather]"""

import sys
import numpy as np
from PIL import Image, ImageFilter
from collections import deque

src, out = sys.argv[1], sys.argv[2]
SAT = int(sys.argv[3]) if len(sys.argv) > 3 else 42
VAL = int(sys.argv[4]) if len(sys.argv) > 4 else 135
feather = float(sys.argv[5]) if len(sys.argv) > 5 else 1.2

im = Image.open(src).convert("RGB")
W, H = im.size

sw = 2000
sh = int(H * sw / W)
small = im.resize((sw, sh), Image.LANCZOS)
a = np.asarray(small).astype(np.int16)
mx = a.max(2)
mn = a.min(2)
sat = mx - mn
wall = (sat < SAT) & (mx > VAL)  # 候選白牆

# 邊界 flood-fill：只保留與畫面邊緣相連的白牆為背景
bg = np.zeros((sh, sw), dtype=bool)
dq = deque()
for x in range(sw):
    for y in (0, sh - 1):
        if wall[y, x]:
            bg[y, x] = True
            dq.append((y, x))
for y in range(sh):
    for x in (0, sw - 1):
        if wall[y, x] and not bg[y, x]:
            bg[y, x] = True
            dq.append((y, x))
while dq:
    y, x = dq.popleft()
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ny, nx = y + dy, x + dx
        if 0 <= ny < sh and 0 <= nx < sw and wall[ny, nx] and not bg[ny, nx]:
            bg[ny, nx] = True
            dq.append((ny, nx))

alpha_small = np.where(bg, 0, 255).astype(np.uint8)
am = Image.fromarray(alpha_small)
if feather > 0:
    am = am.filter(ImageFilter.GaussianBlur(feather))
alpha_full = am.resize((W, H), Image.BILINEAR)

res = im.convert("RGBA")
res.putalpha(alpha_full)
res.save(out)
kept = 100 * (1 - bg.mean())
print(f"saved {out} {(W,H)}  前景占比≈{kept:.1f}%")
