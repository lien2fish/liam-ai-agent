#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""品牌片尾卡 — 產生 ＋ 接到成品尾端。

原本拿到的片尾是簡體抖音模板（「记得点赞关注哦」），用語與品牌調性不符，
改用同樣的圓框頭像版型重做繁體版。

用法：
  python3 tools/reel_outro.py make <頭像圖> [輸出mp4] [--profile=wide]  產生片尾卡
  python3 tools/reel_outro.py append <片尾mp4> <影片...>                接到影片尾端

規格對齊（與 reel_maker 成品一致，否則 concat 會壞檔）：
  1080×1920（--profile=wide 則 1920×1080）/ 24fps / yuv420p(tv) / High@4.0 / aac 48000 stereo
append 的畫幅由正片決定，不用指定；一批混了直式與橫式會被擋下來。
拿到的原片尾是 60fps + 44.1kHz，直接接會出 DTS 錯亂，所以一律重編。
"""

import os
import re
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

FPS = 24
DUR = 2.0
ZHF = "/System/Library/Fonts/STHeiti Medium.ttc"
PINK = (232, 16, 80)  # 從現行片尾的勾勾取樣，讓長短片的片尾看起來是同一個
WHITE = (255, 255, 255)
BG = (0, 0, 0)
TEXT = "记得點讚加訂閱/追蹤哦"  # 與現行片尾同字（首字簡體，2026-08-04 確認不改）

# 版面。橫式不是把直式等比縮小——16:9 垂直空間只剩 56%，元素照比例縮會小到看不見，
# 所以頭像相對放大、整組重新排一次。
PROFILES = {
    "shorts": {"W": 1080, "H": 1920, "avatar": (540, 800, 190), "btn": (540, 1010, 58), "text_y": 1120, "text_fs": 76},
    "wide": {"W": 1920, "H": 1080, "avatar": (960, 430, 160), "btn": (960, 650, 49), "text_y": 730, "text_fs": 64},
}  # fmt: skip
P = PROFILES["shorts"]
W, H = P["W"], P["H"]


def use(name):
    global P, W, H
    if name not in PROFILES:
        raise SystemExit(f"❌ profile 只能是 {'/'.join(PROFILES)}，收到「{name}」")
    P = PROFILES[name]
    W, H = P["W"], P["H"]


def _cleanup(path):
    """用完就清。這幾支工具原本只建暫存不清理，跑幾十輪累積 394 個目錄、
    塞爆 113GB 磁碟，導致長片換音軌中途失敗（No space left on device）。"""
    import shutil

    shutil.rmtree(path, ignore_errors=True)


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

    ax, ay, ar = P["avatar"]
    bx, by, br0 = P["btn"]
    img = Image.new("RGB", (W, H), BG)
    r = int(ar * scale)
    av = avatar.resize((r * 2, r * 2), Image.LANCZOS)
    img.paste(av, (ax - r, ay - r), av)

    d = ImageDraw.Draw(img)
    br = int(br0 * scale)
    d.ellipse((bx - br, by - br, bx + br, by + br), fill=WHITE)
    draw_check(d, bx, by, br, PINK, max(6, int(br * 0.18)))

    fs = int(P["text_fs"] * scale)
    f = ImageFont.truetype(ZHF, fs)
    tw = d.textlength(TEXT, font=f)
    d.text((W / 2 - tw / 2, P["text_y"]), TEXT, font=f, fill=WHITE)
    return img


def make(avatar_path, out):
    tmp = tempfile.mkdtemp()
    av = circle_avatar(avatar_path, P["avatar"][2])
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
    _cleanup(tmp)
    print(f"✅ 片尾卡：{out}（{DUR}s）")


# 直式成品是 bt470bg、橫式是 bt709（ffmpeg 依解析度推導的預設不同）。
# append() 會改成正片的實際矩陣；寫死一種，另一種就會被多轉一次而偏色。
TARGET_CS = "bt470bg"
CS_SYSTEM = {"bt709": "bt709", "bt470bg": "bt601-6-625", "smpte170m": "bt601-6-525"}


def probe_colorspace(path):
    """取影片的色彩矩陣標記，如 yuv420p(tv, bt709, progressive) → bt709。"""
    err = subprocess.run(["ffmpeg", "-i", path], capture_output=True, text=True).stderr
    m = re.search(r"yuv420p\(\w+, ([\w-]+)", err)
    return m.group(1) if m else None


def normalize(outro, tmp):
    """外部工具做的片尾時間基準常是 600 tbn，成品是 12288 tbn，直接 concat copy
    會在接縫出 non-monotonic DTS（YouTube 處理完才報無法上傳的元凶）。
    片尾只有一兩秒，重編成本可忽略。"""
    out = os.path.join(tmp, "outro_norm.mp4")
    # 外部片尾多半是 bt709，成品是 bt470bg。concat copy 只保留正片的 SPS，
    # 片尾會被套上正片的色彩參數解碼而偏色，所以先做真正的矩陣轉換。
    src_cs = probe_colorspace(outro)
    cs = ""
    if src_cs in CS_SYSTEM and src_cs != TARGET_CS:
        cs = (
            f"colorspace=iall={CS_SYSTEM[src_cs]}:all={CS_SYSTEM[TARGET_CS]}"
            f":irange=tv:range=tv,"
        )
    run([
        "ffmpeg", "-y", "-i", outro,
        "-vf", f"{cs}scale={W}:{H}:force_original_aspect_ratio=decrease,"
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


def probe_size(path):
    err = subprocess.run(["ffmpeg", "-i", path], capture_output=True, text=True).stderr
    m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", err)
    return (int(m.group(1)), int(m.group(2))) if m else None


def append(outro, videos):
    # concat 是 -c:v copy，片尾畫幅跟正片不一樣不會報錯，只會產出播放器認不出第二段的壞檔。
    # 所以畫幅一律由正片決定，不讓呼叫端指定。
    global W, H, TARGET_CS
    sizes = {}
    for v in videos:
        if os.path.exists(v):
            sizes.setdefault(probe_size(v), []).append(os.path.basename(v))
    if len(sizes) > 1:
        rows = "\n".join(f"  {s[0]}×{s[1]}：{'、'.join(n)}" for s, n in sizes.items())
        raise SystemExit(f"❌ 這批正片畫幅不一致，要分開接：\n{rows}")
    if sizes:
        W, H = next(iter(sizes))
        cs = {probe_colorspace(v) for v in videos if os.path.exists(v)}
        if len(cs) == 1 and next(iter(cs)) in CS_SYSTEM:
            TARGET_CS = next(iter(cs))
        print(f"  片尾對齊正片 {W}×{H} / {TARGET_CS}")
    tmp0 = tempfile.mkdtemp()
    outro = normalize(outro, tmp0)
    try:
        _append(outro, videos, tmp0)
    finally:
        _cleanup(tmp0)


def _append(outro, videos, tmp0):
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
        _cleanup(tmp)
        print(f"  ✅ {os.path.basename(v)}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    if sys.argv[1] == "make":
        args = [a for a in sys.argv[2:] if not a.startswith("--")]
        for a in sys.argv[2:]:
            if a.startswith("--profile="):
                use(a.split("=", 1)[1])
        make(args[0], args[1] if len(args) > 1 else "片尾卡.mp4")
    elif sys.argv[1] == "append":
        append(sys.argv[2], sys.argv[3:])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
