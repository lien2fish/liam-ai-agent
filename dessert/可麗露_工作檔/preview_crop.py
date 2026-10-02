"""每段抽頭中尾三格，畫出 9:16 裁切框，檢查主角有沒有在框內。用法：python3 preview_crop.py <config.json> <out.jpg>"""
import json, sys, subprocess, tempfile, os
from PIL import Image, ImageDraw
cfg = json.load(open(sys.argv[1]))
tiles = []
for seg in cfg["segments"]:
    vi, s, e = seg[:3]; cx = seg[3] if len(seg) > 3 else 0.5
    row = []
    for t in (s + 0.3, (s + e) / 2, e - 0.3):
        p = tempfile.mktemp(suffix=".jpg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", cfg["videos"][vi], "-frames:v", "1", "-vf", "scale=-2:270", p])
        im = Image.open(p).convert("RGB"); os.remove(p)
        W, H = im.size; cw = H * 9 / 16
        x0 = min(max(W * cx - cw / 2, 0), W - cw)
        d = ImageDraw.Draw(im); d.rectangle((x0, 0, x0 + cw, H - 1), outline=(255, 60, 60), width=3)
        d.text((4, 4), f"{os.path.basename(cfg['videos'][vi])[4:8]} {t:.0f}s cx{cx}", fill=(255, 255, 0))
        row.append(im)
    tiles.append(row)
w = sum(i.width for i in tiles[0]); out = Image.new("RGB", (w, 270 * len(tiles)))
for r, row in enumerate(tiles):
    x = 0
    for im in row: out.paste(im, (x, r * 270)); x += im.width
out.save(sys.argv[2], quality=80)
