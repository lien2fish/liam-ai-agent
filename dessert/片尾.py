#!/usr/bin/env python3
"""泥馬的真心話 品牌片尾卡（記得按讚追蹤）。

    make            產生 dessert/片尾卡.mp4
    append <mp4>    接在影片最後（就地覆蓋）

⚠️ 編碼參數必須跟 dessert_longform 的正片一致，否則 concat copy 之後
   YouTube 會在「處理中」跑完才報無法上傳（見 reel skill）。

⚠️ 要接在**無配樂母帶**上，接完再跑 加配樂.py。
   反過來的話片尾那幾秒會是死寂，而且 BGM 會在片尾開始前就淡出。

🔴 聲道數一定要跟正片一樣（dessert_longform 出的是 48k 立體聲）。
   片尾卡做成單聲道時，concat 不會報錯，但有兩支的片尾段直接把正片
   最後的聲音延續下去（實測 -20.8 dB），長片的成品照那 11 秒也是。
"""
import math
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AVATAR = os.path.join(HERE, "avatar_round.png")
ZHF = "/System/Library/Fonts/STHeiti Medium.ttc"
CARD = os.path.join(HERE, "片尾卡.mp4")

W, H, FPS = 1080, 1920, 24
DUR = 2.8
CREAM = (250, 243, 233)
GOLD = (199, 143, 60)
MAIN = "記得按讚追蹤喔！"
BRAND = "泥馬的真心話"
TAG = "配方可以簡單，但話要說真的"


def ease(t):
    return 1 - (1 - t) ** 3


def background():
    bg = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(bg)
    for y in range(H):
        k = y / H
        d.line(
            [(0, y), (W, y)], fill=(int(44 - 14 * k), int(34 - 11 * k), int(28 - 9 * k))
        )
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse([W // 2 - 430, 300, W // 2 + 430, 1160], fill=90)
    glow = glow.filter(ImageFilter.GaussianBlur(150))
    return Image.composite(Image.new("RGB", (W, H), (92, 66, 40)), bg, glow)


def avatar_card(side):
    card = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle(
        [0, 0, side - 1, side - 1],
        side // 5,
        fill=CREAM + (255,),
        outline=GOLD + (255,),
        width=max(4, side // 60),
    )
    face = Image.open(AVATAR).convert("RGBA")
    s = int(side * 0.84)
    card.alpha_composite(
        face.resize((s, s), Image.LANCZOS), ((side - s) // 2, (side - s) // 2)
    )
    return card


def frames():
    bg = background()
    base = avatar_card(560)
    f_main = ImageFont.truetype(ZHF, 92)
    f_tag = ImageFont.truetype(ZHF, 40)
    f_brand = ImageFont.truetype(ZHF, 52)
    n = int(DUR * FPS)
    for i in range(n):
        t = i / FPS
        im = bg.copy()
        # 頭像卡：0~0.45 秒彈進來
        k = ease(min(1.0, t / 0.45))
        side = int(560 * (0.86 + 0.14 * k))
        card = base.resize((side, side), Image.LANCZOS)
        a = card.getchannel("A").point(lambda v: int(v * k))
        card.putalpha(a)
        im.paste(card, ((W - side) // 2, 560 - (side - 560) // 2), card)

        d = ImageDraw.Draw(im)

        def line(text, font, y, colour, t0, t1):
            k = max(0.0, min(1.0, (t - t0) / (t1 - t0)))
            if k <= 0:
                return
            layer = Image.new("RGBA", (W, 160), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            w = ld.textlength(text, font=font)
            ld.text(
                ((W - w) / 2, 0), text, font=font, fill=colour + (int(255 * ease(k)),)
            )
            im.paste(layer, (0, y), layer)

        line(MAIN, f_main, 1240, CREAM, 0.25, 0.65)
        line(TAG, f_tag, 1380, (214, 200, 182), 0.45, 0.85)
        if t > 0.6:
            k = min(1.0, (t - 0.6) / 0.3)
            d.line(
                [(W / 2 - 110 * k, 1480), (W / 2 + 110 * k, 1480)], fill=GOLD, width=3
            )
        line(BRAND, f_brand, 1510, GOLD, 0.7, 1.05)
        yield im


def make():
    p = subprocess.Popen(
        # fmt: off
        ["ffmpeg", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-f", "lavfi", "-t", str(DUR), "-i", "anullsrc=r=48000:cl=stereo",
         "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-pix_fmt", "yuv420p", "-color_range", "tv",
         "-profile:v", "high", "-level", "4.0", "-r", str(FPS),
         "-video_track_timescale", "12288",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         "-movflags", "+faststart", CARD, "-y"],
        # fmt: on
        stdin=subprocess.PIPE,
    )
    for im in frames():
        p.stdin.write(im.tobytes())
    p.stdin.close()
    assert p.wait() == 0
    print(f"✅ {CARD}　{DUR}s")
    return CARD


def append(video):
    if not os.path.exists(CARD):
        make()
    lst = tempfile.mktemp(suffix=".txt")
    open(lst, "w").write(
        f"file '{os.path.abspath(video)}'\nfile '{os.path.abspath(CARD)}'\n"
    )
    out = tempfile.mktemp(suffix=".mp4")
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            lst,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            out,
            "-y",
        ],
        check=True,
    )
    os.replace(out, video)
    os.remove(lst)
    print(f"✅ 已接片尾　{os.path.basename(video)}")


if __name__ == "__main__":
    if sys.argv[1] == "make":
        make()
    else:
        for v in sys.argv[2:]:
            append(v)
