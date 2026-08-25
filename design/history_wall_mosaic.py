# -*- coding: utf-8 -*-
"""惜食廚房歷史發展牆 直角梯形 · 滿版照片版。

同一塊牆（頂 295／左 250／右 85／斜底 338）。整面鋪不規則照片馬賽克、
照片之間零間隙，往品牌深綠壓暗當底，文字直接壓在照片上。
文案與照片取自協會官網 savefood.org.tw。

用法: python3 design/history_wall_mosaic.py [--dpi 100] [--div 4] [--seed 19]
  --div 4   出 1/4 草稿（預設）；--div 1 出 1:1 母檔
  --seed    換一組馬賽克切法
  --precomp 預先反向補償 tarp_face_pdf.py 的 enhance（要走該腳本轉 CMYK 才加）
"""
import argparse
import glob
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

Image.MAX_IMAGE_PIXELS = None

OUT_DIR = (
    "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/三角牆_歷史發展"
)
PHOTO_DIR = OUT_DIR + "/官網照片"
ZHF = "/System/Library/Fonts/STHeiti Medium.ttc"
ZHF_L = "/System/Library/Fonts/STHeiti Light.ttc"

W_CM, HL_CM, HR_CM = 295.0, 250.0, 85.0
SLANT_CM = math.hypot(W_CM, HL_CM - HR_CM)
BLEED_CM, SAFE_CM = 2.5, 6.0
BAND_CM = 45.0

WHITE = (255, 255, 255)
CREAM = (250, 246, 236)
GREEN = (7, 154, 63)
DEEP = (8, 77, 34)
GOLD = (240, 186, 41)

# 壓暗＝往品牌深綠混色，不是單純降亮度——純黑會讓照片變灰髒，
# 混深綠則整面統一在品牌色調裡，文字反白也更乾淨。
TINT_BASE = 0.20   # 照片區的底噪壓暗，看得出內容但不搶字
TINT_TEXT = 0.64   # 文字帶的壓暗上限
# 文字帶要「先高原、後漸層」。單純從邊緣往內線性淡出的話，
# 文字下緣剛好落在漸層尾端，等於完全沒壓到，白字就會被亮照片吃掉。
TOP_HOLD, TOP_FADE = 44.0, 30.0     # 頂部：全暗 44cm，再漸淡 30cm
# 頂部壓暗只罩數據那半邊——左上已無標題，整條壓下去會白白吃掉一片照片
TOP_X0, TOP_X1 = 122.0, 158.0
BAND_HOLD, BAND_FADE = 37.0, 26.0   # 斜底時間軸帶同上
GLOW_CM = 1.15     # 文字外柔光暈，讓白字不被局部亮塊吃掉

STATS = [
    ("10萬+", "份／年", "送出愛心便當"),
    ("450", "份／日", "惜食廚房穩定產出"),
    ("17,000", "公斤", "首期募集蔬菜"),
]

EVENTS = [
    ("2015", "惜食計畫起源", (0xC9, 0x7A, 0xC4)),
    ("2018", "協會正式成立", (0x9A, 0xD4, 0x74)),
    ("2020", "中央廚房啟用", (0x7F, 0xB6, 0xDC)),
    ("2021", "惜食共餐聯歡", (0xF2, 0xA3, 0x66)),
    ("2022", "扶輪基金會關注", (0x8F, 0xC9, 0x86)),
    ("2023", "愛在惜食永續", (0x8E, 0xCB, 0xEE)),
    ("2025", "惜食教育推廣", (0x6F, 0xD8, 0x9B)),
]

# 理事長任期。年份對到時間軸節點的位置，名字置中在該任期區間下方。
# 末任 None＝任期未結束，往斜底末端延伸。
# (起年, 迄年, 姓名, 職稱, 名字是否收進括號內)。
# 郭俊良的括號從時間軸最開頭拉到首任理事長就任，但名字維持在排序後的位置——
# 那段區間有 93cm 寬，把名字置中進去會離簡承盈太遠、整列間隙就不勻了。
TERMS = [
    ("2015", "2020", "郭俊良", "榮譽創會發起人", False),
    ("2020", "2022", "簡承盈", "理事長", True),
    ("2022", "2023", "葉秀惠", "理事長", True),
    ("2023", "2025", "謝德璋", "理事長", True),
    ("2025", None, "楊奕蘭", "理事長", True),
]

PHOTO_ORDER = [
    "p01_便當特寫.jpg",
    "p14_廚房備料.jpg",
    "p04_竣工祈福典禮.jpg",
    "p08_副總統親臨.jpg",
    "p02_廚房動工儀式.jpg",
    "p05_志工與長者.jpg",
    "p09_扶輪年會展演.jpg",
    "p15_惜食廚房外觀.jpg",
    "p12_大型送餐活動.jpg",
    "p03_廚房落成合影.jpg",
    "p11_國際訪客參訪.jpg",
    "p06_捐贈儀式.jpg",
    "p07_社區關懷.jpg",
    "p00_貴賓參訪.jpg",
]


def slant_y(x, inset):
    a = HR_CM - HL_CM
    return (a * x + W_CM * HL_CM - inset * math.hypot(a, W_CM)) / W_CM


def quad_pts(left, top, right, slant):
    a = HR_CM - HL_CM
    L = math.hypot(a, W_CM)
    xr = W_CM - right
    if slant_y(xr, slant) <= top:
        return [(left, top),
                ((W_CM * top - W_CM * HL_CM + slant * L) / a, top),
                (left, slant_y(left, slant))]
    return [(left, top), (xr, top), (xr, slant_y(xr, slant)), (left, slant_y(left, slant))]


def px(pts, S, bleed):
    return [(p[0] * S + bleed, p[1] * S + bleed) for p in pts]


def ink_bbox(text, font):
    """CJK 的 textbbox 回傳 layout box 不是墨色框，要 render 後取 getbbox。"""
    pad = font.size
    tmp = Image.new("L", (len(text) * font.size + 2 * pad, font.size * 3), 0)
    ImageDraw.Draw(tmp).text((pad, pad), text, font=font, fill=255)
    b = tmp.getbbox()
    return (b[0] - pad, b[1] - pad, b[2] - pad, b[3] - pad)


def glow_tile(parts, fill, S):
    """文字＋深綠柔光暈的貼圖。parts＝[(文字, 字型)]，同一基線接排。"""
    g = max(2, round(GLOW_CM * S))
    pad = g * 4
    big = max(f.size for _, f in parts)
    w = sum(round(f.getlength(t)) for t, f in parts)
    mask = Image.new("L", (w + 2 * pad, big * 3 + 2 * pad), 0)
    dm = ImageDraw.Draw(mask)
    x, base = pad, pad + big * 2
    for t, f in parts:
        dm.text((x, base), t, font=f, fill=255, anchor="ls")
        x += f.getlength(t)
    b = mask.getbbox()
    box = (b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad)
    mask = mask.crop(box)
    glow = mask.filter(ImageFilter.GaussianBlur(g))
    glow = glow.point(lambda v: min(255, round(v * 2.6)))
    tile = Image.new("RGBA", mask.size, DEEP + (0,))
    tile.putalpha(glow)
    tile.paste(Image.new("RGBA", mask.size, fill + (255,)), (0, 0), mask)
    return tile, (pad + b[0] - box[0] - pad, pad + b[1] - box[1] - pad)


def draw_text(canvas, xy, text, font, fill, S):
    """xy＝墨色框左上角。"""
    tile, _ = glow_tile([(text, font)], fill, S)
    g = max(2, round(GLOW_CM * S)) * 4
    canvas.paste(tile, (round(xy[0]) - g, round(xy[1]) - g), tile)


def draw_rot_text(canvas, parts, fill, cx, cy, angle, S):
    tile, _ = glow_tile(parts, fill, S)
    tile = tile.rotate(angle, expand=True, resample=Image.BICUBIC)
    canvas.paste(tile, (round(cx - tile.width / 2), round(cy - tile.height / 2)), tile)


def guillotine(rect, rng, stop_area, min_side):
    """遞迴對切成不規則格子。切線就是相鄰兩格的共用邊，所以零間隙。"""
    x0, y0, x1, y1 = rect
    w, h = x1 - x0, y1 - y0
    if w * h < stop_area * rng.uniform(0.65, 2.2):
        return [rect]
    can_v, can_h = w >= min_side * 2, h >= min_side * 2
    if not (can_v or can_h):
        return [rect]
    vert = can_v and (not can_h or (w > h) == (rng.random() < 0.8))
    # 三成的機率切得很不平均，才會出現大格旁邊挨著小格的節奏
    if rng.random() < 0.32:
        r = rng.uniform(0.18, 0.30)
        if rng.random() < 0.5:
            r = 1 - r
    else:
        r = rng.uniform(0.38, 0.62)
    if vert:
        xm = x0 + w * r
        a, b = (x0, y0, xm, y1), (xm, y0, x1, y1)
    else:
        ym = y0 + h * r
        a, b = (x0, y0, x1, ym), (x0, ym, x1, y1)
    return guillotine(a, rng, stop_area, min_side) + guillotine(b, rng, stop_area, min_side)


def cover(img, w, h, anchor_y=0.40):
    """等比放大蓋滿後裁切。anchor_y<0.5 偏上——人臉多半在畫面上半。"""
    k = max(w / img.width, h / img.height)
    im = img.resize((max(w, round(img.width * k)), max(h, round(img.height * k))), Image.LANCZOS)
    x = (im.width - w) // 2
    y = round((im.height - h) * anchor_y)
    return im.crop((x, y, x + w, y + h))


def tone_compress(im, knee=130, ceil_=145, low=0.82, sat=0.64):
    """反向補償 tarp_face_pdf.enhance() 的 Brightness1.65／Color1.83。"""
    lut = []
    for v in range(256):
        if v <= knee:
            lut.append(round(v * low))
        else:
            t = (v - knee) / (255 - knee)
            lut.append(round(knee * low + (ceil_ - knee * low) * (1 - (1 - t) ** 2)))
    return ImageEnhance.Color(im.point(lut * 3)).enhance(sat)


def load_photos():
    if not os.path.isdir(PHOTO_DIR):
        return []
    out = [Image.open(os.path.join(PHOTO_DIR, n)).convert("RGB")
           for n in PHOTO_ORDER if os.path.exists(os.path.join(PHOTO_DIR, n))]
    return out or [Image.open(p).convert("RGB") for p in sorted(glob.glob(f"{PHOTO_DIR}/*.jpg"))]


def build_mosaic(CW, CH, S, bleed, seed, photos, precomp):
    """整面鋪滿的不規則馬賽克，之後用梯形遮罩裁掉溢出成品框的部分。"""
    rng = random.Random(seed)
    top = quad_pts(-BLEED_CM, -BLEED_CM, -BLEED_CM, -BLEED_CM)
    xs, ys = [p[0] for p in top], [p[1] for p in top]
    cells = guillotine((min(xs), min(ys), max(xs), max(ys)), rng, 2100.0, 30.0)

    def visible(c):
        x0, y0, x1, y1 = c
        n = tot = 0
        for i in range(7):
            for j in range(7):
                x = x0 + (x1 - x0) * (i + 0.5) / 7
                y = y0 + (y1 - y0) * (j + 0.5) / 7
                tot += 1
                if -BLEED_CM <= x <= W_CM + BLEED_CM and -BLEED_CM <= y <= slant_y(x, -BLEED_CM):
                    n += 1
        return (x1 - x0) * (y1 - y0) * n / tot

    cells.sort(key=visible, reverse=True)
    layer = Image.new("RGB", (CW, CH), DEEP)
    if not photos:
        return layer, [(c, visible(c)) for c in cells]

    # 配圖同時看「上牆優先度」與「長寬比合不合」。只照優先度排，
    # 橫幅照片會被硬拉進直式格子，放大倍率暴增、有效 dpi 掉三分之一。
    pool, used, placed = list(range(len(photos))), [], []
    for cell in cells:
        x0, y0, x1, y1 = cell
        a = (round(x0 * S + bleed), round(y0 * S + bleed))
        b = (round(x1 * S + bleed), round(y1 * S + bleed))
        w, h = max(1, b[0] - a[0]), max(1, b[1] - a[1])
        if not pool:
            pool = list(range(len(photos)))
        ar = w / h
        # 格子數比照片多，同一張一定會重複用；重複本身沒關係，
        # 但兩張一樣的照片挨在一起會被一眼看穿，所以鄰格用過的要避開。
        near = {j for c, j in placed if c[0] < x1 + 1 and c[2] > x0 - 1
                and c[1] < y1 + 1 and c[3] > y0 - 1}

        def score(k):
            pa = photos[k].width / photos[k].height
            fit = min(ar / pa, pa / ar) ** 0.7 * (1.0 + 1.4 * (1 - k / len(photos)))
            return fit * (0.05 if k in near else 1.0)

        k = max(pool, key=score)
        pool.remove(k)
        placed.append((cell, k))
        im = cover(photos[k], w, h)
        if precomp:
            im = tone_compress(im)
        layer.paste(im, a)
        used.append(((x0, y0, x1, y1), visible((x0, y0, x1, y1))))
    return layer, used


def tint(layer, S, bleed, rows=1024):
    """往深綠壓暗：頂部與斜底兩條文字帶壓得重，中段只壓一層薄的。

    逐塊處理——整張 118M px 一次進 float 會吃掉 1.4GB。
    """
    a = np.asarray(layer)
    H, W = a.shape[:2]
    deep = np.array(DEEP, dtype=np.float32)
    smooth = lambda t: t * t * (3 - 2 * t)
    xs = (np.arange(W, dtype=np.float32) - bleed) / S
    y_slant = np.array([slant_y(float(x), 0.0) for x in xs], dtype=np.float32)
    perp = W_CM / math.hypot(W_CM, HL_CM - HR_CM)
    topx = smooth(np.clip((xs - TOP_X0) / (TOP_X1 - TOP_X0), 0, 1))[None, :]
    out = np.empty_like(a)
    for y0 in range(0, H, rows):
        y1 = min(H, y0 + rows)
        ys = (np.arange(y0, y1, dtype=np.float32) - bleed) / S
        top = TINT_TEXT * (1 - smooth(np.clip((ys - TOP_HOLD) / TOP_FADE, 0, 1)))[:, None] * topx
        d = (y_slant[None, :] - ys[:, None]) * perp
        band = TINT_TEXT * (1 - smooth(np.clip((d - BAND_HOLD) / BAND_FADE, 0, 1)))
        al = np.maximum(TINT_BASE, np.maximum(top, band))[..., None]
        blk = a[y0:y1].astype(np.float32)
        out[y0:y1] = (blk * (1 - al) + deep * al).astype(np.uint8)
    return Image.fromarray(out)


def build(S, seed, precomp, draft):
    bleed = round(BLEED_CM * S)
    CW, CH = round(W_CM * S) + 2 * bleed, round(HL_CM * S) + 2 * bleed
    out_pts = px(quad_pts(*([-BLEED_CM] * 4)), S, bleed)
    cut_pts = px(quad_pts(0, 0, 0, 0), S, bleed)

    canvas = Image.new("RGB", (CW, CH), WHITE)
    photos = load_photos()
    mosaic, cells = build_mosaic(CW, CH, S, bleed, seed, photos, precomp)
    mosaic = tint(mosaic, S, bleed)
    m = Image.new("L", (CW, CH), 0)
    ImageDraw.Draw(m).polygon(out_pts, fill=255)
    canvas.paste(mosaic, (0, 0), m)
    del mosaic
    d = ImageDraw.Draw(canvas)

    # ── 頂部：三組數據靠右
    nf = ImageFont.truetype(ZHF, round(11.0 * S))
    uf = ImageFont.truetype(ZHF_L, round(4.6 * S))
    lf = ImageFont.truetype(ZHF_L, round(5.2 * S))
    y = 12.5 * S + bleed

    right = (W_CM - SAFE_CM) * S + bleed
    colw = 46.0 * S
    left = right - colw * len(STATS)
    for i, (num, unit, label) in enumerate(STATS):
        cx = left + colw * (i + 0.5)
        nb, ub = ink_bbox(num, nf), ink_bbox(unit, uf)
        x = cx - ((nb[2] - nb[0]) + 1.4 * S + (ub[2] - ub[0])) / 2
        draw_text(canvas, (x - nb[0], y - nb[1]), num, nf, GOLD, S)
        draw_text(canvas, (x + (nb[2] - nb[0]) + 1.4 * S - ub[0],
                           y + (nb[3] - nb[1]) - (ub[3] - ub[1]) - ub[1]),
                  unit, uf, (206, 224, 208), S)
        lb = ink_bbox(label, lf)
        draw_text(canvas, (cx - (lb[2] - lb[0]) / 2 - lb[0], y + 18.0 * S - lb[1]), label, lf, WHITE, S)
        if i:
            xg = left + colw * i
            d.line([(xg, y - 1.5 * S), (xg, y + 15.0 * S)], fill=(150, 176, 152),
                   width=max(1, round(0.35 * S)))

    # ── 時間軸（沿斜底，壓在壓暗過的照片上）
    rise = HL_CM - HR_CM
    L = math.hypot(rise, W_CM)
    ang = math.degrees(math.atan2(rise, W_CM))
    nx, ny = rise / L, W_CM / L  # 法線，指向斜底側
    axis = px(quad_pts(SAFE_CM, SAFE_CM, SAFE_CM, BAND_CM * 0.74), S, bleed)
    P1, P2 = np.array(axis[-1], float), np.array(axis[-2], float)
    n_ev = len(EVENTS)
    for i, (_, _, col) in enumerate(EVENTS):
        a = P1 + (P2 - P1) * (i / n_ev)
        b = P1 + (P2 - P1) * ((i + 1) / n_ev)
        d.line([tuple(a), tuple(b)], fill=col, width=max(2, round(1.5 * S)))
    ux = W_CM / L  # 沿斜底方向的水平分量
    span = W_CM - 2 * SAFE_CM

    def t_max(off, half_cm, h_cm):
        """該列上，文字中心的 t 上限，使墨色右緣不越過安全線。

        沿法線外推會同時把整列往右推（nx>0），所以每一列的可用 t
        都比軸線本身短。字塊斜放後**高度也會佔掉水平寬度**（h_cm/2*nx），
        漏掉這一項右緣會多吃掉近 2cm。
        ⚠️ 超界一律沿斜線方向往回收，不可用水平位移——斜列上水平推
        等於把字推離那一列，看起來就是「跑到上面去」。
        """
        return (W_CM - 2 * SAFE_CM - half_cm * ux - h_cm / 2 * nx - off * nx) / span

    def put(txt_parts, fill, t, off, h_cm):
        half = sum(f.getlength(x) for x, f in txt_parts) / S / 2
        t = min(t, t_max(off, half, h_cm))
        cx, cy = P1 + (P2 - P1) * t + np.array([nx, ny]) * off * S
        draw_rot_text(canvas, txt_parts, fill, cx, cy, ang, S)

    # 三列的法線位置：年份 9.6cm 高、事件 5.0、理事長 5.8。
    # 相鄰兩列的間距要大於兩者半高相加，否則「惜食教育推廣」會壓到「2025」。
    YEAR_OFF, EVENT_OFF, BAR_OFF, CHAIR_OFF = 6.0, 14.8, 18.6, 22.2
    yf = ImageFont.truetype(ZHF, round(9.6 * S))
    tf = ImageFont.truetype(ZHF, round(5.0 * S))
    dot = round(2.4 * S)
    for i, (year, label, col) in enumerate(EVENTS):
        t = (i + 0.5) / n_ev
        cx, cy = P1 + (P2 - P1) * t
        d.ellipse((cx - dot, cy - dot, cx + dot, cy + dot), fill=col,
                  outline=WHITE, width=max(2, round(0.8 * S)))
        put([(year, yf)], col, t, YEAR_OFF, 11.5)
        put([(label, tf)], WHITE, t, EVENT_OFF, 6.0)

    # ── 理事長任期：括號標出年份區間，名字置中在區間下方
    year_t = {e[0]: (i + 0.5) / n_ev for i, e in enumerate(EVENTS)}
    cf = ImageFont.truetype(ZHF, round(5.8 * S))
    rf = ImageFont.truetype(ZHF_L, round(4.2 * S))  # 「理事長」比名字小一級
    parts = [[(nm, cf), (role, rf)] for _, _, nm, role, _ in TERMS]
    half = [sum(f.getlength(t) for t, f in p) / S / 2 for p in parts]

    def need(i):
        """第 i 與 i+1 位之間的最小中心距（t）。各人寬度不同，要逐對算——
        用單一固定值的話，最長的那個職稱會壓到隔壁。"""
        return (half[i] + half[i + 1] + 6.0) / (span / ux)

    # 末位先貼齊右界，其餘由右往左依序讓開，形成等寬的視覺間隙
    spans = [(year_t[a], 1.0 if b is None else year_t[b]) if a else None
             for a, b, _, _, _ in TERMS]
    ts = [None] * len(TERMS)
    for i in range(len(TERMS) - 1, -1, -1):
        cap = t_max(CHAIR_OFF, half[i], 7.0)
        if i < len(TERMS) - 1:
            cap = min(cap, ts[i + 1] - need(i))
        if spans[i] and TERMS[i][4]:
            cap = min(cap, spans[i][1])
        ts[i] = cap

    for i, sp in enumerate(spans):
        if sp:
            ta, tb = sp[0], min(sp[1], t_max(BAR_OFF, 0.0, 0.0))
            pa = P1 + (P2 - P1) * ta + np.array([nx, ny]) * BAR_OFF * S
            pb = P1 + (P2 - P1) * tb + np.array([nx, ny]) * BAR_OFF * S
            d.line([tuple(pa), tuple(pb)], fill=GOLD, width=max(1, round(0.35 * S)))
            for q in (pa, pb):
                d.line([tuple(q), tuple(q - np.array([nx, ny]) * 1.8 * S)],
                       fill=GOLD, width=max(1, round(0.35 * S)))
        cx, cy = P1 + (P2 - P1) * ts[i] + np.array([nx, ny]) * CHAIR_OFF * S
        draw_rot_text(canvas, parts[i], GOLD, cx, cy, ang, S)

    # ── 出血區與裁切標記
    if draft:
        grey = Image.new("RGB", (CW, CH), (222, 222, 220))
        mk = Image.new("L", (CW, CH), 255)
        ImageDraw.Draw(mk).polygon(out_pts, fill=0)
        canvas.paste(grey, (0, 0), mk)
        d = ImageDraw.Draw(canvas)
        d.line(cut_pts + [cut_pts[0]], fill=(190, 190, 190), width=max(1, round(0.25 * S)))
    for a, b in zip(cut_pts, cut_pts[1:] + cut_pts[:1]):
        va, vb = np.array(a, float), np.array(b, float)
        u = (vb - va) / np.linalg.norm(vb - va)
        nrm = np.array([-u[1], u[0]])
        if np.dot(nrm, np.array([CW / 2, CH / 2]) - va) > 0:
            nrm = -nrm
        for t in (0.15, 0.5, 0.85):
            p = va + (vb - va) * t
            d.line([tuple(p + nrm * 3.0 * S), tuple(p + nrm * 5.5 * S)],
                   fill=(0, 0, 0), width=max(1, round(0.3 * S)))
    return canvas, cut_pts, cells, (CW, CH), len(photos)


def verify(cut, cells, size, S, n_photo):
    CW, CH = size
    sl = math.hypot(cut[2][0] - cut[3][0], cut[2][1] - cut[3][1]) / S
    vis = [v for _, v in cells if v > 1000]
    areas = sorted(v / 10000 for v in vis)
    checks = [
        (f"畫布 {CW}×{CH}px（含出血各 {BLEED_CM}cm）",
         abs(CW - (W_CM + 2 * BLEED_CM) * S) <= 2 and abs(CH - (HL_CM + 2 * BLEED_CM) * S) <= 2),
        (f"頂邊 {(cut[1][0]-cut[0][0])/S:.1f}cm（應 {W_CM}）", abs((cut[1][0] - cut[0][0]) / S - W_CM) < 0.5),
        (f"左邊 {(cut[3][1]-cut[0][1])/S:.1f}cm（應 {HL_CM}）", abs((cut[3][1] - cut[0][1]) / S - HL_CM) < 0.5),
        (f"右邊 {(cut[2][1]-cut[1][1])/S:.1f}cm（應 {HR_CM}）", abs((cut[2][1] - cut[1][1]) / S - HR_CM) < 0.5),
        (f"斜底 {sl:.1f}cm（應 {SLANT_CM:.1f}）", abs(sl - SLANT_CM) < 1),
        ("左上、右上皆為直角",
         abs(cut[0][1] - cut[1][1]) < 2 and abs(cut[3][0] - cut[0][0]) < 2 and abs(cut[2][0] - cut[1][0]) < 2),
        (f"馬賽克 {len(cells)} 格、上牆可見 {len(vis)} 格", len(vis) >= 14),
        (f"單格 {areas[0]:.2f}~{areas[-1]:.2f} m²（大小差 {areas[-1]/areas[0]:.1f} 倍）",
         areas[-1] / areas[0] >= 3.0),
        (f"照片 {n_photo} 張", n_photo >= 10),
    ]
    print("-" * 60)
    for item, ok in checks:
        print("{:<48} {}".format(item, "✅" if ok else "❌"))
    return all(o for _, o in checks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dpi", type=float, default=100)
    ap.add_argument("--div", type=int, default=4)
    ap.add_argument("--seed", type=int, default=19)
    ap.add_argument("--precomp", action="store_true")
    args = ap.parse_args()

    S = args.dpi / 2.54 / args.div
    os.makedirs(OUT_DIR, exist_ok=True)
    canvas, cut, cells, size, n = build(S, args.seed, args.precomp, args.div != 1)
    tag = "" if args.div == 1 else f"_1of{args.div}"
    tag += "_precomp" if args.precomp else ""
    p = f"{OUT_DIR}/歷史發展牆_滿版照片版_seed{args.seed}{tag}.png"
    canvas.save(p)
    print(f"✅ {p}　{size[0]}×{size[1]}px　{args.dpi/args.div:.0f}dpi\n")
    verify(cut, cells, size, S, n)


if __name__ == "__main__":
    main()
