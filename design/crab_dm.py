"""龜吼大花蟹推薦 DM（1080x1920）：靜態圖給 LINE、影片版給 IG 限動。

靜態圖源：成品/IG輪播/花蟹怎麼挑/01.jpg 上半部（原始影片已清掉，只剩這張）。
影片源：~/Downloads/IMG_1840.mov（龜吼夜間上岸理網，Lien 2026-10-28 確認是花蟹、人臉可入鏡）。
事實出處同 design/ig_carousel/花蟹怎麼挑.json 的 sources。
"""

import os
import subprocess
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ig_carousel import (
    BOLD,
    DEEP,
    GOLD,
    GOLD_DIM,
    HEAVY,
    INK,
    INK_SOFT,
    REGULAR,
    REPO,
    font,
)

W, H = 1080, 1920
MARGIN = 88
SRC = os.path.join(REPO, "成品/IG輪播/花蟹怎麼挑/01.jpg")
SRC_CROP = (150, 0, 1010, 690)
PHOTO_H = 960
OUT_DIR = os.path.join(REPO, "成品/DM/龜吼大花蟹")
VIDEO_SRC = os.path.expanduser("~/Downloads/IMG_1840.mov")
VIDEO_SHIFT = 400
VIDEO_SLOW = 2

COPY = {
    "eyebrow": "龜吼漁港｜大花蟹",
    "title": ["一台斤以上", "大花蟹"],
    "sub": "這個尺寸不常遇到，一隻就是一道主菜",
    "rows": [
        ("肉質", "個頭大、肉緊實，帶一股鮮甜"),
        ("外觀", "活蟹橘黑花紋，蒸熟轉紅白相間"),
        ("吃法", "整隻清蒸，宴客上桌最體面"),
    ],
    "note": "數量與價格依當天船況",
    "handle": "@lienstable｜連老闆・鑫海產",
}
VIDEO_EYEBROW = "龜吼漁港｜夜間上岸理網"


def photo():
    im = Image.open(SRC).convert("RGB").crop(SRC_CROP)
    scale = W / im.width
    im = im.resize((W, round(im.height * scale)), Image.LANCZOS)
    top = max(0, (im.height - PHOTO_H) // 2)
    return im.crop((0, top, W, top + PHOTO_H)) if im.height >= PHOTO_H else im


def panel(photo_h, eyebrow):
    """photo_h 以上透明（放照片或影片），往下漸層到深藍並寫字。"""
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    y0 = photo_h - 380
    alpha = Image.new("L", (1, H))
    for i in range(H):
        t = min(1, max(0, (i - y0) / 380))
        alpha.putpixel((0, i), round(255 * t**1.4))
    shade = Image.new("RGBA", (W, H), DEEP + (255,))
    shade.putalpha(alpha.resize((W, H)))
    canvas.alpha_composite(shade)
    d = ImageDraw.Draw(canvas)

    y = photo_h - 210
    d.text((MARGIN, y), eyebrow, font=font(BOLD, 40), fill=GOLD)
    y += 74
    f_title = font(HEAVY, 128)
    for line in COPY["title"]:
        d.text((MARGIN, y), line, font=f_title, fill=INK)
        y += 150
    y += 40
    d.text((MARGIN, y), COPY["sub"], font=font(REGULAR, 42), fill=INK_SOFT)
    y += 100

    f_term, f_val = font(BOLD, 42), font(REGULAR, 42)
    for term, val in COPY["rows"]:
        d.line([(MARGIN, y), (W - MARGIN, y)], fill=(34, 56, 78), width=2)
        d.text((MARGIN, y + 26), term, font=f_term, fill=GOLD)
        d.text((MARGIN + 150, y + 26), val, font=f_val, fill=INK)
        y += 100
    d.line([(MARGIN, y), (W - MARGIN, y)], fill=(34, 56, 78), width=2)
    d.text((MARGIN, y + 22), COPY["note"], font=font(REGULAR, 32), fill=GOLD_DIM)

    y += 120
    f_h = font(REGULAR, 32)
    hw = d.textlength(COPY["handle"], font=f_h)
    d.text(((W - hw) / 2, y), COPY["handle"], font=f_h, fill=INK_SOFT)

    return canvas


def build():
    canvas = Image.new("RGBA", (W, H), DEEP + (255,))
    ph = photo()
    canvas.paste(ph, (0, 0))
    canvas.alpha_composite(panel(ph.height, COPY["eyebrow"]))
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "龜吼大花蟹_1080x1920.jpg")
    canvas.convert("RGB").save(out, quality=94)
    print(out)


def build_video():
    os.makedirs(OUT_DIR, exist_ok=True)
    ov = os.path.join(OUT_DIR, "_video_overlay.png")
    panel(PHOTO_H, VIDEO_EYEBROW).save(ov)
    out = os.path.join(OUT_DIR, "龜吼大花蟹_限動_1080x1920.mp4")
    vf = (
        f"[0:v]scale={W}:-2,setpts={VIDEO_SLOW}*PTS,"
        f"minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:vsbmc=1,"
        f"pad={W}:{H}:0:0:color=0x{DEEP[0]:02x}{DEEP[1]:02x}{DEEP[2]:02x}[bg];"
        f"[bg]crop={W}:{H}:0:0[bg2];"
        f"color=c=0x{DEEP[0]:02x}{DEEP[1]:02x}{DEEP[2]:02x}:s={W}x{H}[base];"
        f"[base][bg2]overlay=0:-{VIDEO_SHIFT}:shortest=1[v1];"
        f"[v1][1:v]overlay=0:0:shortest=1,format=yuv420p,"
        f"colorspace=all=bt709:iall=bt709:range=tv[v]"
    )
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", VIDEO_SRC, "-loop", "1", "-i", ov,
         "-filter_complex", vf, "-map", "[v]", "-an", "-r", "30",
         "-c:v", "libx264", "-crf", "18", "-preset", "slow",
         "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
         "-movflags", "+faststart", out],
        check=True,
    )
    os.remove(ov)
    print(out)


if __name__ == "__main__":
    build_video() if "--video" in sys.argv else build()
