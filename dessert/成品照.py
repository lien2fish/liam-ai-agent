#!/usr/bin/env python3
"""把現場拍的成品照做成 9:16 成品照卡，並串成長片片尾。

原始照片背景是廚房（插座、烤盤、糖袋），直接貼上去不像成品照，
所以做法是：同一張照片模糊當底 → 裁緊的主體放在卡片上 → 下方壓品牌字。

輸出：
  成品/達克瓦茲/成品照_1..3.jpg     單張可直接用（IG／縮圖）
  成品/達克瓦茲/成品照片尾.mp4      每張 4 秒、緩慢推近，接在長片最後

⚠️ 片尾的編碼參數必須跟 dessert_longform 的正片一致，
   否則 concat copy 之後 YouTube 會在「處理中」跑完才說無法上傳。
"""
import os
import subprocess

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "成品", "達克瓦茲")
ZHF = "/System/Library/Fonts/STHeiti Medium.ttc"

W, H = 1080, 1920
CREAM = (250, 243, 233)
GOLD = (199, 143, 60)

# (來源, 裁切框, 主標)　裁切框是在長邊縮到 1600 的 jpg 座標上量的
SHOTS = [
    ("IMG_4712.HEIC", (355, 95, 905, 1125), "達克瓦茲"),
    ("IMG_4713.HEIC", (470, 100, 1190, 1100), "糖珠"),
    ("IMG_4714.jpg", (300, 385, 880, 1025), "成品"),
]
SRCDIR = os.path.join(ROOT, "素材")
WORK = os.path.join(HERE, "工作檔_成品照")


def fetch(name):
    """HEIC 走 sips 轉 jpg（PIL 讀不了），長邊統一縮到 1600 好對裁切框。"""
    os.makedirs(WORK, exist_ok=True)
    out = os.path.join(WORK, "photo_" + os.path.splitext(name)[0] + ".jpg")
    if not os.path.exists(out):
        subprocess.run(
            ["sips", "-s", "format", "jpeg", "-Z", "1600",
             os.path.join(SRCDIR, name), "--out", out],
            check=True, capture_output=True,
        )
    return out
SUBS = ["外殼脆、裡面鬆軟", "表面那層糖珠", "配方可以簡單，但話要說真的"]


def prep(src, box):
    """裁緊主體並做基本調色：微提對比與飽和、暖一點、輕銳化。"""
    im = Image.open(src).convert("RGB").crop(box)
    im = ImageEnhance.Contrast(im).enhance(1.10)
    im = ImageEnhance.Color(im).enhance(1.08)
    r, g, b = im.split()
    r = r.point(lambda v: min(255, int(v * 1.03)))
    b = b.point(lambda v: int(v * 0.97))
    im = Image.merge("RGB", (r, g, b))
    return im.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=3))


def card(src, box, main, sub, out):
    photo = prep(fetch(src), box)

    # 底：同一張照片放大到滿版、重模糊、壓暗
    bg = photo.copy()
    s = max(W / bg.width, H / bg.height)
    bg = bg.resize((int(bg.width * s) + 1, int(bg.height * s) + 1), Image.LANCZOS)
    x = (bg.width - W) // 2
    y = (bg.height - H) // 2
    bg = bg.crop((x, y, x + W, y + H)).filter(ImageFilter.GaussianBlur(48))
    bg = ImageEnhance.Brightness(bg).enhance(0.55)
    canvas = bg

    # 主體卡片
    cw = 880
    ch = int(photo.height * cw / photo.width)
    ch = min(ch, 1120)
    shot = photo.resize((cw, ch), Image.LANCZOS)
    cx, cy = (W - cw) // 2, 250
    plate = Image.new("RGB", (cw + 24, ch + 24), CREAM)
    plate.paste(shot, (12, 12))
    mask = Image.new("L", plate.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, plate.size[0] - 1, plate.size[1] - 1], 28, fill=255
    )
    shadow = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(shadow).rounded_rectangle(
        [cx - 12, cy - 4, cx + cw + 12, cy + ch + 28], 28, fill=150
    )
    canvas = Image.composite(
        Image.new("RGB", canvas.size, (0, 0, 0)),
        canvas,
        shadow.filter(ImageFilter.GaussianBlur(26)),
    )
    canvas.paste(plate, (cx - 12, cy - 12), mask)

    d = ImageDraw.Draw(canvas)
    f_main = ImageFont.truetype(ZHF, 118)
    f_sub = ImageFont.truetype(ZHF, 46)
    f_brand = ImageFont.truetype(ZHF, 40)
    ty = H - 380
    w = d.textlength(main, font=f_main)
    d.text(((W - w) / 2, ty), main, font=f_main, fill=CREAM)
    w = d.textlength(sub, font=f_sub)
    d.text(((W - w) / 2, ty + 148), sub, font=f_sub, fill=(228, 218, 204))
    d.line([(W / 2 - 90, ty + 226), (W / 2 + 90, ty + 226)], fill=GOLD, width=3)
    b = "泥馬的真心話"
    w = d.textlength(b, font=f_brand)
    d.text(((W - w) / 2, ty + 252), b, font=f_brand, fill=GOLD)

    canvas.save(out, quality=95)
    return out


def tail(cards, out, per=4.0, fade=0.6):
    """每張緩慢推近 4 秒、交疊 0.6 秒，編碼參數對齊正片。"""
    fps = 24
    parts = []
    fc = []
    for i, c in enumerate(cards):
        parts += ["-loop", "1", "-t", str(per), "-i", c]
        # zoompan 的 z 要用 'on'（輸出格號）算，用 't' 在 loop 輸入上不穩
        fc.append(
            f"[{i}:v]scale=2160:-1,zoompan=z='1+0.055*on/{int(per*fps)}':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(per*fps)}:s={W}x{H}:fps={fps},"
            f"setsar=1[v{i}]"
        )
    chain = ";".join(fc)
    prev = "v0"
    for i in range(1, len(cards)):
        off = per * i - fade * i
        chain += (
            f";[{prev}][v{i}]xfade=transition=fade:duration={fade}:offset={off}[x{i}]"
        )
        prev = f"x{i}"
    chain += f";[{prev}]format=yuv420p[v]"
    subprocess.run(
        # fmt: off
        ["ffmpeg", "-v", "error", *parts,
         "-f", "lavfi", "-t", str(per * len(cards)), "-i", "anullsrc=r=48000:cl=mono",
         "-filter_complex", chain, "-map", "[v]", "-map", f"{len(cards)}:a",
         "-shortest", "-c:v", "libx264", "-crf", "20", "-preset", "medium",
         "-pix_fmt", "yuv420p", "-color_range", "tv",
         "-profile:v", "high", "-level", "4.0", "-r", str(fps),
         "-video_track_timescale", "12288",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "1",
         "-movflags", "+faststart", out, "-y"],
        # fmt: on
        check=True,
    )
    return out


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    cards = []
    for i, ((src, box, main), sub) in enumerate(zip(SHOTS, SUBS), 1):
        p = os.path.join(OUT, f"成品照_{i}.jpg")
        card(src, box, main, sub, p)
        cards.append(p)
        print("✅", p)
    t = tail(cards, os.path.join(OUT, "成品照片尾.mp4"))
    print("✅", t)
