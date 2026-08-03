#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""品牌片尾卡 — 產生 ＋ 接到成品尾端。

原本拿到的片尾是簡體抖音模板（「记得点赞关注哦」），用語與品牌調性不符，
改用同樣的圓框頭像版型重做繁體版。

用法：
  python3 tools/reel_outro.py make <頭像圖> [輸出mp4]      產生片尾卡
  python3 tools/reel_outro.py append <片尾mp4> <影片...>    接到影片尾端

規格對齊（與 reel_maker 成品一致，否則 concat 會壞檔）：
  1080×1920 / 24fps / yuv420p(tv) / High@4.0 / aac 48000 stereo
拿到的原片尾是 60fps + 44.1kHz，直接接會出 DTS 錯亂，所以一律重編。
"""

import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 24
DUR = 2.0
ZHF = "/System/Library/Fonts/STHeiti Medium.ttc"
ORANGE = (245, 156, 48)  # 與字幕高光同色
WHITE = (255, 255, 255)
BG = (0, 0, 0)

AVATAR_C, AVATAR_R = (540, 800), 190
BTN_C, BTN_R = (540, 1010), 58
TEXT_Y, TEXT_SIZE = 1120, 76
TEXT = "記得按讚訂閱"


def run(args):
    r = subprocess.run(args, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode()[-600:])


def circle_avatar(path, r):
    """把來源圖裁成正方形後套圓形遮罩，外圈加白環。"""
    im = Image.open(path).convert("RGB")
    s = min(im.size)
    im = im.crop(
        (
            (im.width - s) // 2,
            (im.height - s) // 2,
            (im.width + s) // 2,
            (im.height + s) // 2,
        )
    ).resize((r * 2, r * 2), Image.LANCZOS)
    mask = Image.new("L", (r * 2, r * 2), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, r * 2 - 1, r * 2 - 1), fill=255)
    out = Image.new("RGBA", (r * 2, r * 2), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    ImageDraw.Draw(out).ellipse(
        (0, 0, r * 2 - 1, r * 2 - 1), outline=WHITE + (255,), width=9
    )
    return out


def draw_check(d, cx, cy, size, color, w):
    """打勾用線段畫，不用字型——STHeiti 沒有 ✓，會變豆腐方框。"""
    d.line(
        [(cx - size * 0.42, cy + size * 0.04),
         (cx - size * 0.10, cy + size * 0.34),
         (cx + size * 0.44, cy - size * 0.32)],
        fill=color, width=w, joint="curve",
    )  # fmt: skip


def frame(avatar, t):
    """t = 0..1 的進度。前 40% 做 ease-out 放大，其餘定住。"""
    p = min(1.0, t / 0.4)
    ease = 1 - (1 - p) ** 3
    scale = 0.86 + 0.14 * ease

    img = Image.new("RGB", (W, H), BG)
    r = int(AVATAR_R * scale)
    av = avatar.resize((r * 2, r * 2), Image.LANCZOS)
    img.paste(av, (AVATAR_C[0] - r, AVATAR_C[1] - r), av)

    d = ImageDraw.Draw(img)
    br = int(BTN_R * scale)
    d.ellipse((BTN_C[0] - br, BTN_C[1] - br, BTN_C[0] + br, BTN_C[1] + br), fill=ORANGE)
    draw_check(d, BTN_C[0], BTN_C[1], br, WHITE, max(6, int(br * 0.18)))

    fs = int(TEXT_SIZE * scale)
    f = ImageFont.truetype(ZHF, fs)
    tw = d.textlength(TEXT, font=f)
    d.text((W / 2 - tw / 2, TEXT_Y), TEXT, font=f, fill=WHITE)
    return img


def make(avatar_path, out):
    tmp = tempfile.mkdtemp()
    av = circle_avatar(avatar_path, AVATAR_R)
    n = int(DUR * FPS)
    for i in range(n):
        frame(av, i / (n - 1)).save(os.path.join(tmp, f"f{i:04d}.png"))
    run([
        "ffmpeg", "-y", "-framerate", str(FPS), "-i", os.path.join(tmp, "f%04d.png"),
        "-f", "lavfi", "-t", str(DUR), "-i", "anullsrc=r=48000:cl=stereo",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0", "-color_range", "tv",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "160k",
        "-r", str(FPS), "-shortest", "-movflags", "+faststart", out,
    ])  # fmt: skip
    print(f"✅ 片尾卡：{out}（{DUR}s）")


def normalize(outro, tmp):
    """外部工具做的片尾時間基準常是 600 tbn，成品是 12288 tbn，直接 concat copy
    會在接縫出 non-monotonic DTS（YouTube 處理完才報無法上傳的元凶）。
    片尾只有一兩秒，重編成本可忽略。"""
    out = os.path.join(tmp, "outro_norm.mp4")
    run([
        "ffmpeg", "-y", "-i", outro,
        "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
               f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0", "-color_range", "tv",
        # 外部片尾常匯出成 0dB 滿格，跟正片講話（約 −25dB）差 25dB，
        # 看完影片會被音效嚇到，平台響度正規化也會反過來壓低整支
        "-af", "volume=-12dB",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "160k",
        "-r", str(FPS), "-video_track_timescale", "12288", out,
    ])  # fmt: skip
    return out


def append(outro, videos):
    tmp0 = tempfile.mkdtemp()
    outro = normalize(outro, tmp0)
    for v in videos:
        if not os.path.exists(v):
            print(f"  ⚠️ 找不到 {v}")
            continue
        tmp = tempfile.mkdtemp()
        cc = os.path.join(tmp, "cc.txt")
        open(cc, "w").write(
            f"file '{os.path.abspath(v)}'\nfile '{os.path.abspath(outro)}'\n"
        )
        merged = os.path.join(tmp, "m.mp4")
        # 音訊重編修接縫 DTS，畫面 copy（正片不重編、零畫質損失）
        run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", cc,
            "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "160k",
            "-movflags", "+faststart", merged,
        ])  # fmt: skip
        os.replace(merged, v)
        print(f"  ✅ {os.path.basename(v)}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    if sys.argv[1] == "make":
        make(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "片尾卡.mp4")
    elif sys.argv[1] == "append":
        append(sys.argv[2], sys.argv[3:])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
