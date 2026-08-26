#!/usr/bin/env python3
"""
知識型 9:16 動畫短片產生器——餵 YouTube Shorts 與 IG。

    python3 tools/knowledge_short.py <主題代號> [輸出路徑]
    python3 tools/knowledge_short.py --list

畫面全部程式生成：不需實拍素材、不涉版權、不涉產地真實性問題。
逐格用 rawvideo 餵給 ffmpeg，不落地成 PNG——剪片暫存把硬碟塞爆過一次
（2026-08-03，23.7GB），這裡從源頭避免。

⚠️ Shorts 無法用 API 設封面，**第一格就是縮圖**，所以每支都以 hook 開場。
⚠️ 事實只能引用 .claude/skills/seafood-brand/references/ 裡查證過的，
   數字白名單見各 SCRIPT 的 sources 註記。
⚠️ 輸出帶靜音音軌（aac 48000 stereo），否則接 reel_outro.py 的片尾會壞檔。
"""

import math
import pathlib
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
DARK_INK = (14, 26, 38)  # 壓在白色遮罩上的字色


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


# ── 腳本 ────────────────────────────────────────────────────────────
# 每段：(秒數, 畫面模式, [字卡行])
# ⚠️ 第一段一律是 hook——Shorts 沒有 API 封面，第一格就是縮圖。

SCRIPTS = {
    "coldchain-01": {
        "title": "你家冰箱凍不出這種魚",
        "sources": "−1～−5°C 最大冰晶生成帶、八成水分（食力／主婦聯盟／TQF）",
        "scenes": [
            (3.0, "hook", ["你家冰箱", "凍不出這種魚"]),
            (3.5, "zone", ["水在 −1°C 到 −5°C 之間結冰", "八成的水分都在這裡變成冰晶"]),
            (5.0, "slow", ["慢慢通過這一段", "冰晶就長得又大又尖", "撐破細胞"]),
            (4.5, "fast", ["快速通過", "冰晶細小", "細胞保持完整"]),
            (4.0, "drip", ["細胞破了", "解凍時鮮味隨著水流走"]),
            (4.0, "end", ["急凍不是凍得更冷", "是凍得更快"]),
        ],
    },
    "coldchain-02": {
        "title": "生魚片鮪魚要凍到零下 60 度",
        "sources": "−60°C 止住褐變、日本八成超低溫（ScienceDirect／J. Agric. Food Chem.）",
        "scenes": [
            (3.2, "hook", ["生魚片鮪魚", "要凍到零下 60 度"]),
            (4.0, "deepcold", ["一般冷凍是 −18°C", "這裡要再往下三倍"]),
            (5.0, "myo", ["鮪魚的紅色", "來自肌紅蛋白"]),
            (4.5, "myo2", ["它會慢慢氧化", "紅色就轉成褐色"]),
            (4.0, "deepcold2", ["只有 −60°C 以下", "能真正把它停住"]),
            (4.3, "end", ["日本處理的鮪魚", "約八成走超低溫"]),
        ],
    },
    "vessel-01": {
        "title": "魚探機看到的其實不是魚",
        "sources": "魚鰾空氣反射、20-200 kHz、弧形成因（DOSITS／WHOI）",
        "scenes": [
            (3.2, "hook", ["魚探機看到的", "其實不是魚"]),
            (4.2, "sonar", ["船底發出聲波", "打向水裡"]),
            (5.0, "sonar2", ["魚的肌肉密度", "和水幾乎一樣", "聲波幾乎不反射"]),
            (4.8, "bladder", ["會反射的", "是魚鰾裡的空氣"]),
            (4.3, "arch", ["螢幕上的弧形", "是魚游過聲波錐的軌跡"]),
            (4.0, "end", ["看不到魚鰾的魚", "就不容易被找到"]),
        ],
    },
    "vessel-02": {
        "title": "這片光，其實是漁船",
        "sources": "NASA VIIRS 可偵測、南大西洋離岸 300-500km 光之城、2020 全球 251,000 船日"
        "（NASA Earth Observatory／Global Fishing Watch）",
        "scenes": [
            (
                3.4,
                "photo",
                ["這片光", "其實是漁船"],
                {
                    "file": "squid_lights.png",
                    "z0": 1.35,
                    "z1": 1.28,
                    "dim": 0.62,
                    "big": True,
                    "veil": {"mode": "grad", "alpha": 0.9, "y0": 980},
                },
            ),
            (
                4.2,
                "photo",
                ["這是從太空", "拍下來的"],
                {
                    "file": "squid_lights.png",
                    "z0": 1.26,
                    "z1": 1.14,
                    "dim": 0.5,
                    "veil": {"mode": "grad", "alpha": 0.9, "y0": 980},
                },
            ),
            (
                4.6,
                "photo",
                ["南大西洋", "離岸三百公里的海面"],
                {
                    "file": "squid_lights.png",
                    "z0": 1.12,
                    "z1": 1.00,
                    "dim": 0.42,
                    "veil": {"mode": "grad", "alpha": 0.9, "y0": 980},
                },
            ),
            (
                4.2,
                "photo",
                ["會出現一座", "光之城"],
                {
                    "file": "squid_lights.png",
                    "z0": 1.00,
                    "z1": 1.06,
                    "dim": 0.38,
                    "veil": {"mode": "grad", "alpha": 0.9, "y0": 980},
                },
            ),
            (4.4, "stat", ["那是魷釣船", "用強光把魷魚誘到表層"]),
            (5.0, "end", ["龜吼的棒受網也用集魚燈", "同樣的原理", "不同的規模"]),
        ],
    },
}


ASSETS = pathlib.Path(__file__).resolve().parent / "assets/knowledge"

# 背景圖的生成 prompt。tools/assets 不進版控（既有的 .gitignore 決定），
# 所以把 prompt 留在這裡，換機器時 --gen-image 就能重建。
# gpt-image-1-mini，1024x1536，一張約 US$0.005。
IMAGE_PROMPTS = {
    "squid_lights.png": (
        "Aerial night view from very high altitude looking down at a dark ocean. A dense cluster "
        "of intensely bright white-blue fishing vessel lights glows on the black water, like a "
        "city floating in the middle of nowhere. Light bloom and haze over the sea surface, "
        "faint cloud wisps. Deep navy and black palette with brilliant cyan-white light. "
        "Photoreal satellite imagery aesthetic, vertical composition. "
        "No text, no labels, no watermark, no land."
    ),
}


def gen_image(name):
    """重建背景圖。需要 config/.openai_key。"""
    import base64, json, urllib.request

    if name not in IMAGE_PROMPTS:
        raise SystemExit(f"❌ 沒有 {name} 的 prompt")
    root = pathlib.Path(__file__).resolve().parent.parent
    key = (root / "config/.openai_key").read_text().strip()
    body = json.dumps(
        {
            "model": "gpt-image-1-mini",
            "prompt": IMAGE_PROMPTS[name],
            "size": "1024x1536",
            "quality": "medium",
            "n": 1,
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/images/generations",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read())
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / name).write_bytes(base64.b64decode(d["data"][0]["b64_json"]))
    print(f"✅ 已生成 {ASSETS / name}（約 US$0.005）")


_photo_cache = {}


def apply_veil(im, veil):
    """白色半透明遮罩。full＝整張洗白；band＝只在字的區域鋪霧面橫帶。

    底圖偏亮或雜訊多時遮罩才划算；黑底上的單一亮點用了反而洗掉張力。
    """
    if not veil:
        return im
    a = veil.get("alpha", 0.3)
    white = Image.new("RGB", im.size, (255, 255, 255))
    if veil.get("mode") == "full":
        return Image.blend(im, white, a)
    if veil.get("mode") == "grad":
        # 由下往上的深色漸層：字清楚，但不破壞暗底的張力
        y0 = veil.get("y0", 900)
        dark = Image.new("RGB", im.size, veil.get("color", (6, 14, 22)))
        mask = Image.new("L", im.size, 0)
        px = mask.load()
        span = max(H - y0, 1)
        for y in range(y0, H):
            v = int(255 * a * ((y - y0) / span) ** 1.4)
            for x in range(0, W, 8):  # 每列同值，取樣畫就好
                for xx in range(x, min(x + 8, W)):
                    px[xx, y] = v
        return Image.composite(dark, im, mask)
    y0, y1 = veil.get("y0", 1120), veil.get("y1", 1520)
    strip = Image.blend(im.crop((0, y0, W, y1)), white.crop((0, y0, W, y1)), a)
    im = im.copy()
    im.paste(strip, (0, y0))
    return im


def photo_backdrop(name, zoom, dim=0.55):
    """把 3D 生成圖鋪滿 9:16 當背景。zoom 用來做緩慢推拉（Ken Burns）。

    圖只在第一次載入時解碼並快取——每格重新開檔會慢到不能用。
    dim 是壓暗係數，字要壓在上面就得夠暗。
    """
    key = (name, round(zoom, 3), dim)
    if key in _photo_cache:
        return _photo_cache[key].copy()
    path = ASSETS / name
    if not path.exists():
        raise SystemExit(
            f"❌ 找不到背景圖 {path}\n"
            f"   tools/assets 不進版控，clone 後要自己生一次：\n"
            f"   python3 tools/knowledge_short.py --gen-image {name}"
        )
    src = Image.open(path).convert("RGB")
    sw, sh = src.size
    scale = max(W / sw, H / sh) * zoom
    im = src.resize((int(sw * scale), int(sh * scale)), Image.LANCZOS)
    left, top = (im.width - W) // 2, (im.height - H) // 2
    im = im.crop((left, top, left + W, top + H))
    im = Image.eval(im, lambda v: int(v * dim))
    if len(_photo_cache) > 24:
        _photo_cache.clear()
    _photo_cache[key] = im
    return im.copy()


def draw_fish(d, cx, cy, w, h, color, bladder=None):
    """側視魚。身體拉長、尾鰭夠大才看得出是魚——第一版畫得像蝌蚪。"""
    # 身體：兩段弧拼出紡錘形
    d.arc([cx - w, cy - h, cx + w * 0.62, cy + h], 180, 360, fill=color, width=5)
    d.arc([cx - w, cy - h, cx + w * 0.62, cy + h], 0, 180, fill=color, width=5)
    # 尾鰭
    tx = cx + w * 0.58
    d.polygon(
        [
            (tx, cy),
            (tx + w * 0.46, cy - h * 0.85),
            (tx + w * 0.30, cy),
            (tx + w * 0.46, cy + h * 0.85),
        ],
        outline=color,
        width=5,
    )
    # 背鰭
    d.polygon(
        [
            (cx - w * 0.25, cy - h * 0.88),
            (cx + w * 0.10, cy - h * 1.32),
            (cx + w * 0.22, cy - h * 0.80),
        ],
        outline=color,
        width=4,
    )
    # 眼睛（前端）
    ex, ey = cx - w * 0.66, cy - h * 0.22
    d.ellipse([ex - 13, ey - 13, ex + 13, ey + 13], outline=color, width=4)
    if bladder:
        d.ellipse(
            [cx - w * 0.30, cy - h * 0.34, cx + w * 0.20, cy + h * 0.02],
            outline=bladder,
            width=6,
        )


def tuna_slab(d, cx, cy, w, h, brown_ratio):
    """鮪魚肉塊；brown_ratio 0~1 表示褐變從左邊推進多少。"""
    RED, BROWN = (198, 52, 46), (118, 72, 42)
    d.rounded_rectangle([cx - w, cy - h, cx + w, cy + h], 26, fill=RED)
    if brown_ratio > 0:
        bx = cx - w + 2 * w * brown_ratio
        d.rounded_rectangle([cx - w, cy - h, bx, cy + h], 26, fill=BROWN)
        d.line([(bx, cy - h), (bx, cy + h)], fill=(210, 170, 120), width=4)
    d.rounded_rectangle(
        [cx - w, cy - h, cx + w, cy + h], 26, outline=(232, 200, 160), width=4
    )


def render_frame(bg, scene, p, seed):
    """p = 該段內的進度 0~1。"""
    mode, lines = scene[1], scene[2]
    cx = W // 2
    photo = scene[3] if len(scene) > 3 else None
    if photo:
        # 緩慢推近，讓靜態圖有呼吸感
        img = photo_backdrop(
            photo["file"],
            photo["z0"] + (photo["z1"] - photo["z0"]) * p,
            photo.get("dim", 0.55),
        )
        img = apply_veil(img, photo.get("veil"))
    else:
        img = bg.copy()
    d = ImageDraw.Draw(img)

    if mode == "hook":
        # 這一格就是 Shorts 的縮圖，所以只有大字＋一條強調線，不放圖表
        d.line([(cx - 110, 1090), (cx + 110, 1090)], fill=GOLD, width=6)
    elif mode == "title":
        temp_bar(d, 560, 0.0, highlight=False)
    elif mode == "zone":
        temp_bar(d, 560, min(p * 1.6, 1.0) * (5 / 18))
    elif mode == "slow":
        temp_bar(d, 520, (1 / 18) + (4 / 18) * min(p * 1.2, 1.0))
        cy = 880
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
        cy = 880
        draw_cell(d, cx, cy, 300, 210, broken=False, color=COLD)
        for i in range(int(26 * min(p * 1.6, 1.0))):
            r2 = random.Random(i)
            ang, rad = r2.uniform(0, math.tau), math.sqrt(r2.uniform(0, 1)) * 0.72
            draw_crystal(
                d,
                cx + 300 * rad * math.cos(ang),
                cy + 210 * rad * math.sin(ang),
                15,
                COLD,
                width=2,
            )
    elif mode == "drip":
        cy = 860
        draw_cell(d, cx, cy, 300, 200, broken=True, color=WARN)
        for i in range(7):
            ph = (p * 1.5 + i * 0.14) % 1.0
            dx, dy, r = cx + (i - 3) * 78, cy + 200 + ph * 300, 11 - 4 * ph
            d.ellipse([dx - r, dy - r, dx + r, dy + r], fill=(90, 150, 190))
    elif mode in ("deepcold", "deepcold2"):
        # 0°C → −60°C 的刻度，強調 −18 與 −60 的距離
        x0, x1, y = 150, W - 150, 620
        d.rounded_rectangle([x0, y, x1, y + 16], 8, fill=(30, 48, 66))
        x18 = x0 + (x1 - x0) * (18 / 60)
        d.rounded_rectangle([x0, y, x18, y + 16], 8, fill=(52, 86, 116))
        f = font(34)
        d.text((x0, y - 52), "0°C", font=f, fill=DIM)
        d.text((x18 - 46, y - 52), "−18°C", font=f, fill=DIM)
        d.text(
            (x1 - 92, y - 52),
            "−60°C",
            font=f,
            fill=GOLD if mode == "deepcold2" else DIM,
        )
        t = min(p * 1.6, 1.0) if mode == "deepcold" else 1.0
        mx = x0 + (x1 - x0) * (
            (18 / 60) + (42 / 60) * t if mode == "deepcold2" else (18 / 60) * t
        )
        d.polygon([(mx, y + 22), (mx - 13, y + 42), (mx + 13, y + 42)], fill=GOLD)
        if mode == "deepcold2":
            d.rounded_rectangle([x18, y, x1, y + 16], 8, fill=GOLD)
    elif mode in ("myo", "myo2"):
        ratio = min(max(p * 1.25, 0), 1) if mode == "myo2" else 0.0
        tuna_slab(d, cx, 900, 300, 190, ratio)
        f = font(36)
        if mode == "myo":
            center_text(d, 1120, "氧合肌紅蛋白 ＝ 鮮紅", f, DIM)
        else:
            center_text(d, 1120, "變性肌紅蛋白 ＝ 褐色", f, WARN)
    elif mode in ("sonar", "sonar2", "bladder"):
        # 船底發聲波打向魚
        d.polygon(
            [(cx - 150, 560), (cx + 150, 560), (cx + 105, 630), (cx - 105, 630)],
            outline=INK,
            width=4,
        )
        for i in range(4):
            ph = (p * 1.4 + i * 0.25) % 1.0
            rr = 60 + ph * 420
            d.arc(
                [cx - rr, 630 - rr * 0.45, cx + rr, 630 + rr * 0.45],
                20,
                160,
                fill=(70, 120, 160),
                width=3,
            )
        blad = GOLD if mode == "bladder" else None
        draw_fish(
            d, cx, 1080, 230, 120, DIM if mode == "sonar2" else COLD, bladder=blad
        )
        if mode == "sonar2":
            f = font(36)
            center_text(d, 1150, "肌肉 ≈ 水的密度", f, DIM)
        if mode == "bladder":
            for i in range(3):
                ph = (p * 1.6 + i * 0.3) % 1.0
                rr = 40 + ph * 260
                d.arc(
                    [cx - rr, 1010 - rr * 0.5, cx + rr, 1010 + rr * 0.5],
                    200,
                    340,
                    fill=GOLD,
                    width=3,
                )
    elif mode == "arch":
        # 魚探機螢幕上的弧
        d.rounded_rectangle([cx - 330, 660, cx + 330, 1130], 18, outline=DIM, width=4)
        pts = []
        for i in range(60):
            u = i / 59
            pts.append((cx - 280 + 560 * u, 1040 - 300 * math.sin(math.pi * u)))
        n = max(2, int(len(pts) * min(p * 1.4, 1.0)))
        d.line(pts[:n], fill=GOLD, width=7)
    elif mode == "stat":
        f_big = font(150)
        w = d.textbbox((0, 0), "251,000", font=f_big)[2]
        t = ease(min(p * 2.2, 1.0))
        d.text(
            ((W - w) // 2, 760),
            "251,000",
            font=f_big,
            fill=tuple(int(c * (0.3 + 0.7 * t)) for c in GOLD),
        )
        center_text(d, 950, "2020 年全球魷釣船的作業「船日」", font(36), DIM)
    elif mode in ("end", "photo"):
        pass

    # 字卡
    is_hook = mode == "hook" or bool(photo and photo.get("big"))
    if is_hook:
        f = font(92)
        for i, line in enumerate(lines):
            t = ease((p - i * 0.18) * 3.0)
            if t <= 0:
                continue
            v = photo.get("veil") if photo else None
            base = DARK_INK if (v and v.get("mode") in ("full", "band")) else INK
            shade = (
                tuple(int(255 + (c - 255) * t) for c in base)
                if base is DARK_INK
                else tuple(int(c * (0.35 + 0.65 * t)) for c in base)
            )
            # 有圖片背景時字往下讓，別壓在畫面主體上（那一格就是縮圖）
            y0 = 1210 if photo else 820
            center_text(d, y0 + i * 132, line, f, shade)
    else:
        f = font(72)
        for i, line in enumerate(lines):
            t = ease((p - i * 0.22) * 3.2)
            if t <= 0:
                continue
            col = GOLD if (mode == "end" and i == len(lines) - 1) else INK
            shade = tuple(int(c * (0.35 + 0.65 * t)) for c in col)
            center_text(d, 1240 + i * 104, line, f, shade)

    if not is_hook:
        center_text(d, 300, "海鮮冷知識", font(38), GOLD)
    center_text(d, H - 130, "連老闆 ・ 產地到餐桌", font(34), DIM)
    return img


def main():
    args = [a for a in sys.argv[1:]]
    if not args or args[0] in ("--list", "-l"):
        print("可用主題：")
        for k, v in SCRIPTS.items():
            total = sum(s[0] for s in v["scenes"])
            print(f"  {k:14s} {total:4.1f}s  {v['title']}")
            print(f"                 依據：{v['sources']}")
        return
    if args[0] == "--gen-image":
        gen_image(args[1] if len(args) > 1 else "")
        return
    slug = args[0]
    if slug not in SCRIPTS:
        print(f"❌ 沒有這個主題：{slug}（用 --list 看清單）")
        raise SystemExit(1)
    script = SCRIPTS[slug]
    out = args[1] if len(args) > 1 else f"{slug}.mp4"

    bg = background()
    scenes = script["scenes"]
    total = sum(s[0] for s in scenes)
    print(
        f"{script['title']}｜{total:.1f} 秒 / {int(total * FPS)} 格 → {out}", flush=True
    )

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
            # 靜音音軌：沒有它，接 reel_outro 的片尾會壞檔
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=48000:cl=stereo",
            "-shortest",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-profile:v",
            "high",
            "-level",
            "4.0",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            out,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    n = 0
    for si, scene in enumerate(scenes):
        frames = int(scene[0] * FPS)
        for i in range(frames):
            ff.stdin.write(
                render_frame(bg, scene, i / max(frames - 1, 1), si * 1000 + i).tobytes()
            )
            n += 1
            if n % 120 == 0:
                print(f"  {n}/{int(total * FPS)} 格", flush=True)
    ff.stdin.close()
    ff.wait()
    print(f"✅ 完成：{out}", flush=True)


if __name__ == "__main__":
    main()
