# -*- coding: utf-8 -*-
"""惜食廚房歷史發展牆 直角梯形（頂 295／左 250／右 85／斜底 338）。

直角在左上與右上，斜底由左下 (0,250) 升到右下 (295,85)。
時間軸沿斜底由左下 2015 爬升到右下 2023，照片區在內側。
沿用惜食廚房品牌語彙（綠 #079A3F、金黃 #E0A50A、STHeiti）。

用法: python3 design/trap_wall_history.py [--dpi 100] [--div 4] [--cells]
  --div 4  出 1/4 草稿快速看版面（預設）
  --cells  畫照片佔位格
"""
import argparse
import glob
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None

OUT_DIR = (
    "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/三角牆_歷史發展"
)
ZHF = "/System/Library/Fonts/STHeiti Medium.ttc"
ZHF_L = "/System/Library/Fonts/STHeiti Light.ttc"
PHOTO_DIR = OUT_DIR + "/模擬照片"


# 背景色。麥穗素材只有 238×63px，放到 2.9m 會糊，只能當小尺寸點綴，
# 主要背景一律程式生成，沒有解析度上限。
BG_BASE = {
    "plain": (255, 255, 255),
    "warm": (250, 243, 227),
    "band": (255, 255, 255),
    "stripe": (250, 246, 236),
}
ORANGE = (0xD9, 0x78, 0x41)

# 現場複量：左 250、頂 295、右 85 三條直邊為準；斜底由幾何鎖死＝√(295²+165²)。
W_CM = 295.0  # 頂邊（水平）
HL_CM = 250.0  # 左邊（直立）
HR_CM = 85.0  # 右邊（直立）
SLANT_CM = math.hypot(W_CM, HL_CM - HR_CM)

BLEED_CM = 2.5  # 出血：四邊各往外
BAND_CM = 28.0  # 斜底側的時間軸帶寬
CELL_H_CM = 36.0  # 照片帶高
MIN_CELL_W_CM = 58.0  # 一格最小寬，低於此就併成單格
SAFE_CM = 6.0  # 內容距裁切線的安全距離

WHITE = (255, 255, 255)
GREEN = (7, 154, 63)
GOLD = (224, 165, 10)
INK = (58, 72, 52)
GREY = (136, 136, 136)

STAT_BIG = "22萬+"
STAT_SUB = "累積送出愛心餐盒"

TITLE = "認識惜食廚房"
SUBTITLE = "從一個念頭，到每天送出的一餐"

# (年, 短標題, 色)——大牆面遠觀，只留年份與一句話；細節要點在簡報裡不上牆。
# 六色取自協會 2025 簡報第 006 頁的時間軸橫條，沿用其視覺語彙。
EVENTS = [
    ("2015", "惜食計畫起源", (0x93, 0x34, 0x8E)),
    ("2018", "協會正式成立", (0x65, 0xA6, 0x42)),
    ("2020", "惜食廚房開幕", (0x30, 0x5E, 0x7F)),
    ("2021", "惜食共餐聯歡", (0xD9, 0x78, 0x41)),
    ("2022", "扶輪基金會關注", (0x33, 0x69, 0x2D)),
    ("2023", "愛在惜食永續", (0x4A, 0x9D, 0xD1)),
]


def slant_y(x, inset, W, HL, HR):
    """斜底往內縮 inset 後，在 x 處的 y。inset 為負＝往外擴（出血）。"""
    a = HR - HL
    return (a * x + W * HL - inset * math.hypot(a, W)) / W


def quad_pts(left, top, right, slant, W, HL, HR):
    """四邊**各自**內縮後的頂點（順時針：左上、右上、右下、左下）。

    時間軸帶只佔斜底側，其餘三邊只需要安全距離；四邊一律內縮同樣距離
    會讓內容區白白少掉一塊。斜底沿法線平移後再與左右兩股求交點——
    直接把頂點往內移會讓斜底的縮距不等於 slant。

    斜底內縮到切過上緣時右側收成尖角，回傳三角形（band/stripe 背景會用到）。
    """
    a = HR - HL
    L = math.hypot(a, W)
    xr = W - right
    ys = lambda x: slant_y(x, slant, W, HL, HR)
    if ys(xr) <= top:
        return [
            (left, top),
            ((W * top - W * HL + slant * L) / a, top),
            (left, ys(left)),
        ]
    return [(left, top), (xr, top), (xr, ys(xr)), (left, ys(left))]


def draw_rot_text(canvas, text, font, fill, cx, cy, angle):
    """以 (cx, cy) 為中心畫旋轉文字。"""
    pad = font.size
    tmp = Image.new("RGBA", (len(text) * font.size + 2 * pad, font.size * 3), (0,) * 4)
    d = ImageDraw.Draw(tmp)
    d.text((pad, pad), text, font=font, fill=fill + (255,))
    tmp = tmp.crop(tmp.getbbox())
    tmp = tmp.rotate(angle, expand=True, resample=Image.BICUBIC)
    canvas.paste(tmp, (round(cx - tmp.width / 2), round(cy - tmp.height / 2)), tmp)
    return tmp.size


def make_bg(style, CW, CH, S, W, HL, HR, bleed):
    """整張背景圖；之後用梯形遮罩貼上，不會溢出成品框。"""
    bg = Image.new("RGB", (CW, CH), BG_BASE.get(style, (255, 255, 255)))
    d = ImageDraw.Draw(bg)

    def pts(slant):
        return [
            (p[0] + bleed, p[1] + bleed) for p in quad_pts(0, 0, 0, slant, W, HL, HR)
        ]

    if style == "band":
        # 沿斜底往內的綠色漸層帶。只內縮斜底——四邊一起縮會變成一塊色塊。
        # 分 60 階畫，逐 px 畫要跑三千次多邊形填充。
        band, steps = 78 * S, 60
        for i in range(steps):
            k = i / steps
            col = tuple(round(255 - (255 - c) * 0.20 * (1 - k) ** 1.5) for c in GREEN)
            d.polygon(pts(band * k), fill=col)

    if style == "stripe":
        # 六色細條紋沿斜底平行排列，取時間軸同一組色。由外往內畫，
        # 後畫的蓋在前一條上，形成等寬帶。
        pitch = 15.5 * S
        n = int(W * HL / math.hypot(HR - HL, W) / pitch) + 1
        for i in range(n):
            col = EVENTS[i % len(EVENTS)][2]
            soft = tuple(round(255 - (255 - c) * 0.13) for c in col)
            d.polygon(pts(i * pitch), fill=soft if i % 2 == 0 else BG_BASE["stripe"])

    if style in ("warm", "stripe"):
        d.rectangle((0, 0, CW, round(1.3 * S)), fill=ORANGE)

    # 三角版的麥穗點綴在此拿掉：梯形把左下角補成 60.8° 的鈍楔形，
    # 那塊空白現在是時間軸起點（2015／惜食計畫起源），塞不下也搶焦點。
    return bg


def build(S, cells, draft=False, nofill=False, bg_style="plain"):
    """S = px per cm。"""
    bleed = round(BLEED_CM * S)
    W, HL, HR = round(W_CM * S), round(HL_CM * S), round(HR_CM * S)
    CW, CH = W + 2 * bleed, HL + 2 * bleed  # 含出血的畫布

    canvas = Image.new("RGB", (CW, CH), WHITE)
    d = ImageDraw.Draw(canvas)

    def shift(pts):
        return [(p[0] + bleed, p[1] + bleed) for p in pts]

    # 出血層：把梯形往外擴 bleed，避免裁切公差露白
    out_pts = shift(quad_pts(*([-bleed] * 4), W, HL, HR))
    cut_pts = shift(quad_pts(0, 0, 0, 0, W, HL, HR))
    d.polygon(out_pts, fill=WHITE)
    if bg_style != "plain":
        m = Image.new("L", (CW, CH), 0)
        ImageDraw.Draw(m).polygon(out_pts, fill=255)
        canvas.paste(make_bg(bg_style, CW, CH, S, W, HL, HR, bleed), (0, 0), m)
        d = ImageDraw.Draw(canvas)
    if draft:
        grey = Image.new("RGB", (CW, CH), (222, 222, 220))
        m = Image.new("L", (CW, CH), 255)
        ImageDraw.Draw(m).polygon(out_pts, fill=0)
        canvas.paste(grey, (0, 0), m)
        d.line(
            cut_pts + [cut_pts[0]], fill=(190, 190, 190), width=max(1, round(0.25 * S))
        )

    # 斜底方向：由左下 (0,HL) 指向右下 (W,HR)，往右上爬
    rise = HL - HR
    L = math.hypot(rise, W)
    ang = math.degrees(math.atan2(rise, W))  # PIL rotate 逆時針為正
    ux, uy = W / L, -rise / L
    nx, ny = -uy, ux  # 外法線：指向斜底那側（右下）

    # ── 時間軸主線：斜底往內 BAND_CM，與斜底平行
    line_in = round(BAND_CM * S)
    lp = shift(quad_pts(SAFE_CM * S, SAFE_CM * S, SAFE_CM * S, line_in, W, HL, HR))

    # ── 主線分六色段，對應六個事件（同簡報橫條）
    P1, P2 = np.array(lp[3], float), np.array(lp[2], float)  # 左下→右下
    n_ev = len(EVENTS)
    lw = max(2, round(1.6 * S))
    for i, (_, _, col) in enumerate(EVENTS):
        a = P1 + (P2 - P1) * (i / n_ev)
        b = P1 + (P2 - P1) * ((i + 1) / n_ev)
        d.line([tuple(a), tuple(b)], fill=col, width=lw)

    # ── 事件節點：圓點落在各色段中心，文字往斜底側（帶內）錯開
    yf = ImageFont.truetype(ZHF, round(11.0 * S))
    tf = ImageFont.truetype(ZHF, round(5.6 * S))
    dot_r = round(2.6 * S)
    for i, (year, label, col) in enumerate(EVENTS):
        t = (i + 0.5) / n_ev
        px, py = P1 + (P2 - P1) * t
        d.ellipse((px - dot_r, py - dot_r, px + dot_r, py + dot_r),
                  fill=WHITE, outline=col, width=max(2, round(0.8 * S)))  # fmt: skip
        for off, txt, fnt, tcol in (
            (8.0, year, yf, col),
            (17.0, label, tf, INK),
        ):
            draw_rot_text(canvas, txt, fnt, tcol,
                          px + nx * off * S, py + ny * off * S, ang)  # fmt: skip

    # ── 標題：內容區頂部，靠左
    inner = shift(
        quad_pts(SAFE_CM * S, SAFE_CM * S, SAFE_CM * S, line_in + 4 * S, W, HL, HR)
    )
    big = ImageFont.truetype(ZHF, round(20.0 * S))
    sub = ImageFont.truetype(ZHF_L, round(7.0 * S))
    tx, ty = inner[0][0] + round(6 * S), inner[0][1] + round(8 * S)
    d.text((tx, ty), TITLE, font=big, fill=GREEN)
    d.text((tx + round(1 * S), ty + round(26 * S)), SUBTITLE, font=sub, fill=INK)

    boxes = []
    if cells:
        boxes = photo_cells(inner, S)
        pics = (
            []
            if nofill
            else (
                sorted(glob.glob(f"{PHOTO_DIR}/*.jpg"))
                if os.path.isdir(PHOTO_DIR)
                else []
            )
        )
        for i, b in enumerate(boxes):
            ib = tuple(round(v) for v in b)
            if i < len(pics):
                canvas.paste(fill_photo(Image.open(pics[i]).convert("RGB"), b), ib[:2])
                d.rectangle(ib, outline=WHITE, width=max(2, round(0.8 * S)))
                d.rectangle(ib, outline=(206, 206, 206), width=max(1, round(0.25 * S)))
            else:
                d.rounded_rectangle(b, radius=round(2 * S), fill=(228, 228, 228),
                                    outline=GREY, width=max(1, round(0.4 * S)))  # fmt: skip
                cf = ImageFont.truetype(ZHF, round(6 * S))
                n = f"{i+1:02d}"
                tw = d.textlength(n, font=cf)
                d.text(((b[0] + b[2]) / 2 - tw / 2, (b[1] + b[3]) / 2 - 3 * S), n,
                       font=cf, fill=(120, 120, 120))  # fmt: skip

        # 數據區塊放右上角：梯形右側比原三角版多出一塊 85cm 高的牆面，
        # 那裡照片格塞不下（帶高不足），留給數據才不會空一片
        bf = ImageFont.truetype(ZHF, round(18.0 * S))
        sf2 = ImageFont.truetype(ZHF_L, round(7.0 * S))
        sx = inner[1][0] - round(6 * S) - d.textlength(STAT_SUB, font=sf2)
        sy = inner[0][1] + round(10 * S)
        d.text((sx, sy), STAT_BIG, font=bf, fill=GOLD)
        d.text((sx, sy + bf.size * 1.2), STAT_SUB, font=sf2, fill=INK)

    # ── 裁切標記：四邊各 3 支，畫在出血區
    for a, b in zip(cut_pts, cut_pts[1:] + cut_pts[:1]):
        va, vb = np.array(a, float), np.array(b, float)
        u = (vb - va) / np.linalg.norm(vb - va)
        nrm = np.array([-u[1], u[0]])
        if np.dot(nrm, np.array([CW / 2, CH / 2]) - va) > 0:
            nrm = -nrm  # 一律指向畫布外
        for t in (0.15, 0.5, 0.85):
            p = va + (vb - va) * t
            q0 = p + nrm * (0.3 * S * 10)
            q1 = p + nrm * (0.55 * S * 10)
            d.line([tuple(q0), tuple(q1)], fill=(0, 0, 0), width=max(1, round(0.3 * S)))  # fmt: skip

    return canvas, cut_pts, inner, boxes, (CW, CH)


def fill_photo(img, box):
    """cover 模式填滿格子：等比放大到蓋滿後居中裁切，不變形。"""
    w, h = round(box[2] - box[0]), round(box[3] - box[1])
    k = max(w / img.width, h / img.height)
    im = img.resize(
        (max(w, round(img.width * k)), max(h, round(img.height * k))), Image.LANCZOS
    )
    return im.crop(((im.width - w) // 2, (im.height - h) // 2,
                    (im.width - w) // 2 + w, (im.height - h) // 2 + h))  # fmt: skip


def photo_cells(inner, S):
    """在內容區裡切照片格。

    固定帶高、由上而下逐帶切；每帶用**底緣**（該帶最窄處）算可用寬，
    格子才不會右下角戳出斜底。可用寬不足一格時整帶併成單格，
    低於 MIN_CELL_W_CM 就收工——右下角硬塞會切出無法用的細條。
    """
    (x0, y0), (x1, _) = inner[0], inner[1]
    safe = SAFE_CM * S
    top = y0 + 48 * S  # 讓開標題與副標（副標底在 41cm 處）
    gap, row_h = 4.0 * S, CELL_H_CM * S
    # 斜底內緣（inner 的底邊）：由 (x0, yD) 到 (x1, yC)
    (xd, yd), (xc, yc) = inner[-1], inner[-2]
    slope = (yc - yd) / (xc - xd)
    x_at = lambda y: xd + (y - yd) / slope  # 該高度處內容區的右界

    rows, y = [], top
    while True:
        avail = min(x1, x_at(y + row_h)) - x0 - safe
        if avail < MIN_CELL_W_CM * S:
            break
        n = max(1, int((avail + gap) // (MIN_CELL_W_CM * S)))
        cw = (avail - gap * (n - 1)) / n
        for k in range(n):
            cx = x0 + safe + k * (cw + gap)
            rows.append((cx, y, cx + cw, y + row_h))
        y += row_h + gap
    return rows


def verify(canvas, cut, inner, boxes, size, S):
    CW, CH = size
    W, HL, HR = round(W_CM * S), round(HL_CM * S), round(HR_CM * S)

    def inside(p):
        x, y = p[0] - cut[0][0], p[1] - cut[0][1]
        return (x >= -1 and y >= -1 and x <= W + 1
                and y <= slant_y(x, 0, W, HL, HR) + 1)  # fmt: skip

    sl = math.hypot(cut[2][0] - cut[3][0], cut[2][1] - cut[3][1]) / S
    ok = [
        (f"畫布 {CW}×{CH}px（含出血各 {BLEED_CM}cm）",
         abs(CW - (W_CM + 2*BLEED_CM)*S) <= 2 and abs(CH - (HL_CM + 2*BLEED_CM)*S) <= 2),
        (f"頂邊 {(cut[1][0]-cut[0][0])/S:.1f}cm（應 {W_CM}）",
         abs((cut[1][0] - cut[0][0]) / S - W_CM) < 0.5),
        (f"左邊 {(cut[3][1]-cut[0][1])/S:.1f}cm（應 {HL_CM}）",
         abs((cut[3][1] - cut[0][1]) / S - HL_CM) < 0.5),
        (f"右邊 {(cut[2][1]-cut[1][1])/S:.1f}cm（應 {HR_CM}）",
         abs((cut[2][1] - cut[1][1]) / S - HR_CM) < 0.5),
        (f"斜底 {sl:.1f}cm（應 {SLANT_CM:.1f}）", abs(sl - SLANT_CM) < 1),
        ("左上、右上皆為直角",
         abs(cut[0][1] - cut[1][1]) < 2 and abs(cut[3][0] - cut[0][0]) < 2
         and abs(cut[2][0] - cut[1][0]) < 2),
        (f"左右兩直邊平行、面積 {(HL_CM+HR_CM)/2*W_CM/10000:.2f} m²", True),
    ]  # fmt: skip
    if boxes:
        allin = all(inside((b[2], b[3])) and inside((b[0], b[1])) for b in boxes)
        ok.append((f"照片格 {len(boxes)} 個全在成品框內", allin))
        areas = [(b[2] - b[0]) * (b[3] - b[1]) / (S * S) / 10000 for b in boxes]
        ok.append((f"單格面積 {min(areas):.2f}~{max(areas):.2f} m²", min(areas) > 0.08))

    print("-" * 60)
    for item, passed in ok:
        print("{:<48} {}".format(item, "✅" if passed else "❌"))
    return all(p for _, p in ok)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dpi", type=float, default=100)
    ap.add_argument("--div", type=int, default=4)
    ap.add_argument("--cells", action="store_true")
    ap.add_argument("--nofill", action="store_true", help="照片格只留框，不填模擬照片")
    ap.add_argument("--bg", default="plain", choices=list(BG_BASE))
    args = ap.parse_args()

    S = args.dpi / 2.54 / args.div  # px per cm
    os.makedirs(OUT_DIR, exist_ok=True)
    canvas, cut, inner, boxes, size = build(
        S, args.cells, args.div != 1, args.nofill, args.bg
    )

    tag = ("_底圖" if args.nofill else "") if args.div == 1 else f"_1of{args.div}"
    tag += "" if args.bg == "plain" else f"_{args.bg}"
    p = f"{OUT_DIR}/歷史發展牆_梯形295x250x85{tag}.png"
    canvas.save(p)
    print(f"✅ {p}　{size[0]}×{size[1]}px　{args.dpi/args.div:.0f}dpi\n")
    verify(canvas, cut, inner, boxes, size, S)


if __name__ == "__main__":
    main()
