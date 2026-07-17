# -*- coding: utf-8 -*-
"""把外牆防水布每一面切成獨立檔，轉 CMYK 並輸出印刷用 .ai（PDF 相容，嵌入 CMYK 影像）。"""
import os
from PIL import Image, ImageCms
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

Image.MAX_IMAGE_PIXELS = None
DIR = "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/外牆防水布"
OUT = f"{DIR}/分面_印刷ai檔"
TMP = f"{OUT}/_tmp_cmyk_jpg"
os.makedirs(OUT, exist_ok=True)
os.makedirs(TMP, exist_ok=True)

ICC = "/System/Library/ColorSync/Profiles/Generic CMYK Profile.icc"
srgb = ImageCms.createProfile("sRGB")
cmyk = ImageCms.getOpenProfile(ICC)
PT_PER_M = 39.3701 * 72  # 公尺 → PDF points


def panels(dv, total):
    e = [0] + dv + [total]
    return [(e[i], e[i + 1]) for i in range(len(e) - 1)]


def make_ai(crop_rgb, out_ai):
    w_px, h_px = crop_rgb.size
    cm = ImageCms.profileToProfile(
        crop_rgb,
        srgb,
        cmyk,
        renderingIntent=ImageCms.Intent.PERCEPTUAL,
        outputMode="CMYK",
    )
    jpg = f"{TMP}/{os.path.basename(out_ai)}.jpg"
    cm.save(jpg, "JPEG", quality=100, subsampling=0)
    w_pt = w_px / 1000 * PT_PER_M  # 1000px = 1m
    h_pt = h_px / 1000 * PT_PER_M
    c = canvas.Canvas(out_ai, pagesize=(w_pt, h_pt))
    c.drawImage(ImageReader(jpg), 0, 0, width=w_pt, height=h_pt)
    c.showPage()
    c.save()


jobs = []
# 主牆 25.5m，7 面（招募志工版）
main = Image.open(f"{DIR}/外牆防水布_主牆25m5_招募志工版.png").convert("RGB")
main_labels = [
    "扶輪3523",
    "扶輪3522",
    "扶輪3521",
    "扶輪3482",
    "扶輪3481",
    "珍惜食材_扶輪3490",
    "招募志工",
]
for i, (L, R) in enumerate(panels([3700, 7000, 10300, 13600, 16900, 20700], 25500)):
    jobs.append(
        (
            main.crop((L, 0, R, 1300)),
            f"主牆_第{i+1}面_{(R-L)/1000:.2f}m_{main_labels[i]}.ai",
        )
    )

# 次牆 14.45m，4 面（扶輪捐贈版）
sub = Image.open(f"{DIR}/外牆防水布_次牆14m45_扶輪捐贈版.png").convert("RGB")
sub_labels = ["扶輪3501", "空白框", "空白框", "空白框"]
for i, (L, R) in enumerate(panels([3600, 7600, 10450], 14450)):
    jobs.append(
        (
            sub.crop((L, 0, R, 1300)),
            f"次牆_第{i+1}面_{(R-L)/1000:.2f}m_{sub_labels[i]}.ai",
        )
    )

# 獨立單面布 3.6×1.25m
solo = Image.open(f"{DIR}/防水布_惜食台灣行動協會_3.6x1.25m.png").convert("RGB")
jobs.append((solo, "單面_惜食台灣行動協會_3.60x1.25m.ai"))

for crop, name in jobs:
    make_ai(crop, f"{OUT}/{name}")
    print(f"OK  {crop.size[0]/1000:.2f}m × {crop.size[1]/1000:.2f}m  {name}")

print(f"\n完成 {len(jobs)} 個 .ai → {OUT}")
