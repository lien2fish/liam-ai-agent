#!/usr/bin/env python3
"""
冷鏈知識動畫字卡（9:16）——不需要實拍素材、不涉版權、不涉食安數字。

    python3 instagram/coldchain_reel.py [輸出路徑]

第一支主題：急速冷凍 vs 慢速冷凍（最大冰晶生成帶）。
畫面全部程式生成，逐格用 rawvideo 餵給 ffmpeg，不落地成 PNG——
剪片暫存把硬碟塞爆過一次（2026-08-03，23.7GB），這裡從源頭避免。

⚠️ 文案只准出現兩個已查證的數字：−18°C、最大冰晶生成帶 −1～−5°C。
   依據見 .claude/skills/seafood-brand/references/cold-chain.md
"""

import math
import random
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 24
FONT_PATH = "/System/Library/Fonts/PingFang.ttc"
FONT_IDX = 3

BG_TOP = (9, 26, 41)
BG_BOTTOM = (4, 14, 24)
INK = (238, 244, 249)
DIM = (128, 152, 172)
GOLD = (214, 168, 92)
COLD = (122, 190, 226)
WARN = (206, 106, 74)


def font(size):
    return ImageFont.truetype(FONT_PATH, size, index=FONT_IDX)


def background():
    """深藍漸層底，全片共用，只算一次。"""
    bg = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(bg)
    for y in range(H):
        t = y / H
        d.line(
            [(0, y), (W, y)],
            fill=tuple(int(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM)),
        )
    return bg


def center_text(d, y, text, f, fill, alpha=255):
    w = d.textbbox((0, 0), text, font=f)[2]
    if alpha >= 255:
        d.text(((W - w) // 2, y), text, font=f, fill=fill)
    else:
        d.text(((W - w) // 2, y), text, font=f, fill=fill + (alpha,))
    return w


def ease(t):
    """0→1 的平滑進場，字卡用。"""
    return 1 - (1 - min(max(t, 0.0), 1.0)) ** 3


def draw_crystal(d, cx, cy, r, color, width=3):
    """六角冰晶：三條交叉線＋分枝，慢速冷凍畫大的、急速畫小的。"""
    for k in range(3):
        a = math.radians(60 * k)
        x1, y1 = cx - r * math.cos(a), cy - r * math.sin(a)
        x2, y2 = cx + r * math.cos(a), cy + r * math.sin(a)
        d.line([(x1, y1), (x2, y2)], fill=color, width=width)
        for s in (0.45, 0.75):
            for sign in (-1, 1):
                bx, by = (
                    cx + r * s * math.cos(a) * sign,
                    cy + r * s * math.sin(a) * sign,
                )
                for ba in (a + math.radians(45), a - math.radians(45)):
                    d.line(
                        [
                            (bx, by),
                            (
                                bx + r * 0.22 * math.cos(ba),
                                by + r * 0.22 * math.sin(ba),
                            ),
                        ],
                        fill=color,
                        width=max(1, width - 1),
                    )


def draw_cell(d, cx, cy, rw, rh, broken, color):
    """細胞外框。broken=True 時邊緣被冰晶撐出缺口。"""
    box = [cx - rw, cy - rh, cx + rw, cy + rh]
    if not broken:
        d.ellipse(box, outline=color, width=4)
        return
    # 破裂：分段畫弧，留缺口
    for a0, a1 in [(10, 80), (100, 165), (195, 260), (285, 350)]:
        d.arc(box, a0, a1, fill=color, width=4)


def temp_bar(d, y, marker_t, highlight=True):
    """0°C → −18°C 溫度條，marker_t 0~1 表示目前落點。"""
    x0, x1 = 150, W - 150
    d.rounded_rectangle([x0, y, x1, y + 16], 8, fill=(30, 48, 66))
    # 最大冰晶生成帶 −1～−5°C ＝ 全長的 1/18 ~ 5/18
    zx0 = x0 + (x1 - x0) * (1 / 18)
    zx1 = x0 + (x1 - x0) * (5 / 18)
    if highlight:
        d.rounded_rectangle([zx0, y, zx1, y + 16], 8, fill=WARN)
    f = font(34)
    d.text((x0, y - 52), "0°C", font=f, fill=DIM)
    d.text((x1 - 92, y - 52), "−18°C", font=f, fill=DIM)
    if highlight:
        lab = "−1～−5°C"
        lw = d.textbbox((0, 0), lab, font=f)[2]
        # 指標畫在 y+22~y+42，區間標籤要再往下讓開
        d.text(((zx0 + zx1) / 2 - lw / 2, y + 56), lab, font=f, fill=WARN)
    mx = x0 + (x1 - x0) * min(max(marker_t, 0.0), 1.0)
    # 指標畫在條的下方朝上，避免與上方的 0°C／−18°C 標籤重疊
    d.polygon([(mx, y + 22), (mx - 13, y + 42), (mx + 13, y + 42)], fill=GOLD)


# 每段：(秒數, 畫面模式, 字卡行)
SCENES = [
    (3.0, "title", ["你家冰箱的冷凍", "和我們的急凍", "差別不在幾度"]),
    (3.5, "zone", ["水在 −1°C 到 −5°C 之間結冰", "八成的水分都在這裡變成冰晶"]),
    (4.5, "slow", ["慢慢通過這一段", "冰晶就長得又大又尖", "撐破細胞"]),
    (4.0, "fast", ["快速通過", "冰晶細小", "細胞保持完整"]),
    (3.5, "drip", ["細胞破了", "解凍時鮮味會隨著水流走"]),
    (3.5, "end", ["所以急凍不是凍得更冷", "是凍得更快"]),
]


def render_frame(bg, scene, p, seed):
    """p = 該段內的進度 0~1。"""
    img = bg.copy()
    d = ImageDraw.Draw(img)
    rnd = random.Random(seed)
    mode, lines = scene[1], scene[2]

    if mode == "title":
        temp_bar(d, 560, 0.0, highlight=False)
    elif mode == "zone":
        temp_bar(d, 560, min(p * 1.6, 1.0) * (5 / 18))
    elif mode == "slow":
        temp_bar(d, 520, (1 / 18) + (4 / 18) * min(p * 1.2, 1.0))
        cx, cy = W // 2, 880
        draw_cell(
            d, cx, cy, 300, 210, broken=p > 0.55, color=COLD if p <= 0.55 else WARN
        )
        for i in range(3):
            g = min(max((p - 0.15 - i * 0.12) * 2.2, 0), 1)
            if g > 0:
                draw_crystal(
                    d,
                    cx + (i - 1) * 170,
                    cy + (i % 2) * 60 - 30,
                    46 + 132 * g,
                    COLD,
                    width=5,
                )
    elif mode == "fast":
        temp_bar(d, 520, min(p * 2.4, 1.0))
        cx, cy = W // 2, 880
        draw_cell(d, cx, cy, 300, 210, broken=False, color=COLD)
        n = int(26 * min(p * 1.6, 1.0))
        for i in range(n):
            rnd2 = random.Random(i)
            ang = rnd2.uniform(0, math.tau)
            rad = math.sqrt(rnd2.uniform(0, 1)) * 0.72
            ax = cx + 300 * rad * math.cos(ang)
            ay = cy + 210 * rad * math.sin(ang)
            draw_crystal(d, ax, ay, 15, COLD, width=2)
    elif mode == "drip":
        cx, cy = W // 2, 860
        draw_cell(d, cx, cy, 300, 200, broken=True, color=WARN)
        for i in range(7):
            ph = (p * 1.5 + i * 0.14) % 1.0
            dx = cx + (i - 3) * 78
            dy = cy + 200 + ph * 300
            r = 11 - 4 * ph
            d.ellipse([dx - r, dy - r, dx + r, dy + r], fill=(90, 150, 190))
    elif mode == "end":
        temp_bar(d, 560, 1.0, highlight=False)

    # 字卡：逐行淡入，最後一段用金色強調
    base_y = 1240
    f_main = font(72)
    for i, line in enumerate(lines):
        t = ease((p - i * 0.22) * 3.2)
        if t <= 0:
            continue
        col = GOLD if (mode == "end" and i == len(lines) - 1) else INK
        shade = tuple(int(c * (0.35 + 0.65 * t)) for c in col)
        center_text(d, base_y + i * 104, line, f_main, shade)

    # 眉標（系列名）
    f_e = font(38)
    center_text(d, 300, "冷鏈知識", f_e, GOLD)

    # 品牌角標
    f_s = font(34)
    center_text(d, H - 130, "連老闆 ・ 產地到餐桌", f_s, DIM)
    return img


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "instagram/coldchain_01.mp4"
    bg = background()
    total = sum(s[0] for s in SCENES)
    print(f"總長 {total:.1f} 秒 / {int(total * FPS)} 格 → {out}", flush=True)

    ff = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{W}x{H}",
            "-r",
            str(FPS),
            "-i",
            "-",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            out,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    n = 0
    for si, scene in enumerate(SCENES):
        frames = int(scene[0] * FPS)
        for i in range(frames):
            img = render_frame(bg, scene, i / max(frames - 1, 1), si * 1000 + i)
            ff.stdin.write(img.tobytes())
            n += 1
            if n % 48 == 0:
                print(f"  {n}/{int(total * FPS)} 格", flush=True)
    ff.stdin.close()
    ff.wait()
    print(f"✅ 完成：{out}", flush=True)


if __name__ == "__main__":
    main()
