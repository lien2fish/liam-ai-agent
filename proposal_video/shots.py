#!/usr/bin/env python3
"""從渲染好的影片抽「每個場景的中點」合成一張拼圖，用來目視驗收。

⚠️ 不要等距抽樣——場景之間有間隙，等距會抽到轉場的空畫面，
看起來像圖元沒渲染出來（2026-09-12 因此誤判過一次）。
"""
import os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
proj = sys.argv[1] if len(sys.argv) > 1 else "full-wide"
d = f"{HERE}/{proj}"

html = open(f"{d}/index.html", encoding="utf-8").read()
mids = [(m.group(1), round(float(m.group(2)) + float(m.group(3)) / 2, 2))
        for m in re.finditer(
            r'<section id="(\w+)" class="clip" data-start="([\d.]+)" data-duration="([\d.]+)"', html)]

vids = sorted((f for f in os.listdir(f"{d}/renders") if f.endswith(".mp4")), reverse=True)
if not vids:
    sys.exit(f"{proj}/renders/ 裡沒有 mp4，先 render")
vid = f"{d}/renders/{vids[0]}"

out = f"{HERE}/{proj}/shots"
os.makedirs(out, exist_ok=True)
files = []
for sid, t in mids:
    f = f"{out}/{sid}.png"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(t), "-i", vid,
                    "-frames:v", "1", "-vf", "scale=640:-1", f], check=True)
    files.append(f)
    print(f"  {sid}  t={t}")

cols = 4
rows = (len(files) + cols - 1) // cols
layout = "|".join(
    ("0" if i % cols == 0 else "+".join(f"w{j}" for j in range(i % cols))) + "_" +
    ("0" if i < cols else "+".join(f"h{j*cols}" for j in range(i // cols)))
    for i in range(len(files)))
args = []
for f in files:
    args += ["-i", f]
grid = f"{out}/_grid.png"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args, "-filter_complex",
                f"{''.join(f'[{i}]' for i in range(len(files)))}"
                f"xstack=inputs={len(files)}:layout={layout}:fill=black", grid], check=True)
print(f"\n{grid}  （{len(files)} 個場景 / {cols}×{rows}）")
