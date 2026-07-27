# -*- coding: utf-8 -*-
"""惜食廚房三角牆活動相簿（頂邊295 / 左邊180 / 底斜邊350 cm）。1px = 1mm。

母檔已預先反向補償 tarp_face_pdf.enhance()，母檔看起來偏暗屬正常，
審稿一律看 預覽_三角布_印刷模擬.png。

用法:
  python3 design/tri_wall_savefood.py                        # 灰色佔位版型
  python3 design/tri_wall_savefood.py --photos <照片資料夾>
  python3 design/tri_wall_savefood.py --photos <dir> --pdf   # 送印 CMYK PDF
"""
import argparse
import glob
import math
import os
import re
import sys
import time

import numpy as np
from PIL import (
    Image,
    ImageChops,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
    ImageOps,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tarp_face_pdf import build as build_cmyk_pdf
from tarp_solo_photo import enhance_like_pdf, ink_bbox, tone_compress

Image.MAX_IMAGE_PIXELS = None

OUT_DIR = "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/三角牆_歷屆活動相簿"
ZHF = "/System/Library/Fonts/STHeiti Medium.ttc"

SIDE_TOP, SIDE_LEFT, SIDE_SLANT = 2950.0, 1800.0, 3500.0

BLEED, PAD, BORDER, MARGIN = 25, 40, 26, 60
ROWS, GAP, CELL_ASPECT = 4, 28, 1.7
TITLE_H, TITLE_GAP, TITLE_PAD_X, TITLE_PAD_Y = 340, 40, 80, 30
APEX_SKIP = 130
CARD_RADIUS, STROKE, CORNER_KEEPOUT = 44, 12, 120

TITLE_TEXT = "一餐一飯 ‧ 都是疼惜"
GREEN, ORANGE, WHITE, BLACK = (7, 154, 63), (232, 121, 15), (255, 255, 255), (0, 0, 0)
# ×1.65 後為 (224,224,224)。用 (150,150,150) 會變 (247,247,247) 幾乎看不見。
PLACEHOLDER_FILL, PLACEHOLDER_INK = (136, 136, 136), (48, 48, 48)

PHOTO_COLOR, PHOTO_UNSHARP = 0.64, 45
MIN_DPI = 35.0

# 底圖：滿版實景照壓暗，同外牆既有 12 面語彙。目標亮度＝那 12 面母檔實測 42~50
POLLI = "https://image.pollinations.ai/prompt/"
# 暖褐比深綠溫馨；綠色版留著是因為與外牆 12 面同色系，之後要對齊時可切回
TINTS = {"warm": (48, 26, 10), "green": (12, 40, 22)}
BACKDROP_BLUR, BACKDROP_TINT = 0.8, 0.26
# 飽和與暖偏也自動校準（實測既有 12 面母檔：飽和 32~46、R−B +27~+38）。
# 憑感覺調會過橘——暖提示詞＋暖增益＋暖混色三層疊起來實測飽和衝到 66
BACKDROP_TARGET_SAT, BACKDROP_TARGET_RB = 38.0, 30.0
# 白標題壓在亮窗上對比不足，加細描邊保底（228mm 字高下 7mm 不會讓 CJK 筆劃黏連）
TITLE_STROKE, TITLE_STROKE_FILL = 7, (10, 34, 18)
# 顆粒只為抑制大面積暗部的 CMYK 分色帶狀；下游 UnsharpMask(2,120) 會再放大約一倍，
# 用 3.0 在 1:1 印刷尺度看得到明顯雜訊，1.2 才剛好
BACKDROP_TARGET_LUM, BACKDROP_GRAIN, BACKDROP_CEIL = 46.0, 1.2, 150.0
_NO_TEXT = "no text, no signage, no logos, no watermark, no people's faces in focus"
BACKDROP_PROMPTS = {
    "volunteers": (
        "candid documentary photograph inside a warm community charity kitchen in Taiwan, "
        "a group of adult volunteers in aprons working together packing hot lunch boxes, "
        "hands scooping rice and vegetables into bento boxes, gentle steam rising, "
        "warm natural window light, shallow depth of field, natural film grain, "
        + _NO_TEXT
    ),
    "table": (
        "warm cozy still life photograph of a home style wooden dining table set for a shared meal, "
        "bowls of steaming white rice, a clay pot of soup, small plates of simple home cooked "
        "vegetables, wooden chopsticks resting on ceramic rests, a woven bamboo basket, "
        "a folded linen cloth, soft golden hour light spilling across the table from the side, "
        "gentle rising steam, deep warm amber and honey tones, shallow depth of field, "
        "cosy inviting family atmosphere, natural film grain, " + _NO_TEXT
    ),
    "bento": (
        "warm intimate close up photograph of a pair of hands gently passing a warm lunch box "
        "wrapped in a soft cloth to another pair of older hands, steam escaping from the lid, "
        "rustic wooden table underneath, soft golden backlight, blurred cosy kitchen behind, "
        "deep amber and caramel tones, tender caring mood, shallow depth of field, "
        "natural film grain, " + _NO_TEXT
    ),
    "pantry": (
        "warm cosy photograph of a home style kitchen pantry corner bathed in golden afternoon "
        "light, wooden shelves with glass jars of rice grains and dried beans, woven baskets of "
        "fresh vegetables, hanging garlic and dried herbs, a well used enamel pot with gentle "
        "steam, a stack of simple ceramic bowls, soft amber and honey tones, no people, "
        "quiet abundant nourishing atmosphere, shallow depth of field, natural film grain, "
        + _NO_TEXT
    ),
}

THEMES = [
    "歷屆活動",
    "歷屆活動",
    "歷屆活動",
    "志工互動",
    "志工互動",
    "志工互動",
    "惜食備餐",
    "惜食備餐",
    "送餐到里長",
    "送餐到里長",
]
CROP_ANCHOR = {}  # {格號: (0.5, 0.4)} 主體不在正中時微調
EXPOSURE = {}  # {格號: 1.08} 舊照偏暗，全域 gamma（非局部漸層）

CROPMARK_T = (0.15, 0.50, 0.85)
CROPMARK_IN, CROPMARK_OUT, CROPMARK_W = 30, 55, 2


# ---------------------------------------------------------------- 幾何


def solve_triangle(top=SIDE_TOP, left=SIDE_LEFT, slant=SIDE_SLANT):
    """頂邊水平、左端為原點。回傳 (P2 左上, P3 右上, P1 左下尖角)。"""
    assert top + left > slant and top + slant > left and left + slant > top
    x = (left**2 - slant**2 + top**2) / (2 * top)
    y = math.sqrt(left**2 - x**2)
    return (0.0, 0.0), (top, 0.0), (x, y)


def incenter_r(verts):
    p2, p3, p1 = verts
    a, b, c = math.dist(p3, p1), math.dist(p2, p1), math.dist(p2, p3)
    s = a + b + c
    i = (
        (a * p2[0] + b * p3[0] + c * p1[0]) / s,
        (a * p2[1] + b * p3[1] + c * p1[1]) / s,
    )
    return i, 2 * tri_area(verts) / s


def tri_area(verts):
    (x1, y1), (x2, y2), (x3, y3) = verts
    return abs(x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2)) / 2


def offset_tri(verts, i, r, d):
    """三邊同時垂直內縮 d（d<0 為外擴），等同以內心相似縮放 k=(r-d)/r。"""
    k = (r - d) / r
    return [(i[0] + k * (p[0] - i[0]), i[1] + k * (p[1] - i[1])) for p in verts]


def canvas_frame():
    cut = solve_triangle()
    i, r = incenter_r(cut)
    bleed = offset_tri(cut, i, r, -BLEED)
    x0 = min(p[0] for p in bleed) - PAD
    y0 = min(p[1] for p in bleed) - PAD
    w = math.ceil(max(p[0] for p in bleed) + PAD - x0)
    h = math.ceil(max(p[1] for p in bleed) + PAD - y0)
    shift = lambda t: [(p[0] - x0, p[1] - y0) for p in t]
    return {
        "W": w,
        "H": h,
        "tx": -x0,
        "ty": -y0,
        "bleed": shift(bleed),
        "cut": shift(cut),
        "inner": shift(offset_tri(cut, i, r, BORDER)),
        "safe": shift(offset_tri(cut, i, r, MARGIN)),
    }


def edge_fns(tri):
    """回傳 lx(y), rx(y)：三角形在高度 y 處的左右界（tri = P2, P3, P1）。"""
    p2, p3, p1 = tri

    def interp(a, b):
        return lambda y: a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1])

    return interp(p2, p1), interp(p3, p1)


def angle_at(o, a, b):
    va, vb = (a[0] - o[0], a[1] - o[1]), (b[0] - o[0], b[1] - o[1])
    cos = (va[0] * vb[0] + va[1] * vb[1]) / (math.hypot(*va) * math.hypot(*vb))
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


# ---------------------------------------------------------------- 遮罩


def tri_mask(verts, w, h):
    """凸多邊形半平面 signed distance 解析反鋸齒，比全畫布超取樣省 4 倍記憶體。"""
    xs = (np.arange(w, dtype=np.float32) + 0.5)[None, :]
    ys = (np.arange(h, dtype=np.float32) + 0.5)[:, None]
    cx = sum(p[0] for p in verts) / 3.0
    cy = sum(p[1] for p in verts) / 3.0
    cov = np.ones((h, w), dtype=np.float32)
    for k in range(3):
        ax, ay = verts[k]
        bx, by = verts[(k + 1) % 3]
        nx, ny = ay - by, bx - ax
        norm = math.hypot(nx, ny)
        nx, ny, c = nx / norm, ny / norm, (nx * ax + ny * ay) / norm
        if nx * cx + ny * cy - c > 0:
            nx, ny, c = -nx, -ny, -c
        np.minimum(cov, np.clip(0.5 - (nx * xs + ny * ys - c), 0.0, 1.0), out=cov)
    return Image.fromarray((cov * 255).astype(np.uint8))


def rrect_mask(w, h, radius, ss=4):
    big = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(big).rounded_rectangle(
        (0, 0, w * ss - 1, h * ss - 1), radius=radius * ss, fill=255
    )
    return big.resize((w, h), Image.LANCZOS)


def erode(mask, width):
    """必須先補 0 邊：PIL 的 RankFilter 會複製邊界像素，貼齊影像邊界的直線邊侵蝕不到。"""
    p = ImageOps.expand(mask, border=width, fill=0)
    p = p.filter(ImageFilter.MinFilter(2 * width + 1))
    return p.crop((width, width, width + mask.width, width + mask.height))


# ---------------------------------------------------------------- 版面


class Cell:
    def __init__(self, idx, row, col, x, y, w, h, cw, slanted):
        self.idx, self.row, self.col = idx, row, col
        self.x, self.y, self.w, self.h = x, y, w, h
        self.cw, self.slanted = cw, slanted
        self.theme = THEMES[idx - 1] if idx <= len(THEMES) else ""

    @property
    def box(self):
        return (self.x, self.y, self.x + self.w, self.y + self.h)


def plan_cells(frame, rows=ROWS):
    lx, rx = edge_fns(frame["safe"])
    top = frame["safe"][0][1] + TITLE_H + TITLE_GAP
    apex_y = frame["safe"][2][1]
    h = (apex_y - APEX_SKIP - top - (rows - 1) * GAP) / rows

    cells, idx = [], 0
    for i in range(rows):
        yt = top + i * (h + GAP)
        yb = yt + h
        ym = (yt + yb) / 2
        wn = rx(ym) - lx(ym)
        n = max(1, round(wn / (h * CELL_ASPECT)))
        cw = (wn - (n - 1) * GAP) / n
        for j in range(n):
            idx += 1
            x = lx(ym) + j * (cw + GAP)
            last = j == n - 1
            # 末格用帶頂寬當外接框，再與 SAFE 三角形相交 → 斜切邊與底邊平行
            w = (rx(yt) - x) if last else cw
            cells.append(
                Cell(
                    idx, i + 1, j + 1, round(x), round(yt), round(w), round(h), cw, last
                )
            )
    return cells


def plan_title(frame):
    lx, rx = edge_fns(frame["safe"])
    y0 = frame["safe"][0][1]
    ink_y = y0 + TITLE_PAD_Y  # 齊上：文字往寬處靠，右側可用寬度多 150mm
    left = lx(ink_y)  # 左界最緊的是墨色框頂緣（左斜邊往下才外移）
    maxh = TITLE_H - 2 * TITLE_PAD_Y

    lo, hi = 40, 600
    while lo < hi:
        mid = (lo + hi + 1) // 2
        bx0, by0, bx1, by1 = ink_bbox(TITLE_TEXT, ImageFont.truetype(ZHF, mid))
        w, h = bx1 - bx0, by1 - by0
        # 右界取墨色框底緣（斜邊往左收），不是整條標題帶的底緣
        if h <= maxh and w <= rx(ink_y + h) - left - TITLE_PAD_X:
            lo = mid
        else:
            hi = mid - 1
    font = ImageFont.truetype(ZHF, lo)
    bx0, by0, bx1, by1 = ink_bbox(TITLE_TEXT, font)
    return font, (round(left), round(ink_y)), (bx1 - bx0, by1 - by0), (bx0, by0)


# ---------------------------------------------------------------- 內容


def prep_photo(path, w, h, idx):
    im = Image.open(path).convert("RGB")
    sw, sh = im.size
    scale = max(w / sw, h / sh)
    im = im.filter(ImageFilter.GaussianBlur(0.5))
    im = im.resize(
        (max(w, round(sw * scale)), max(h, round(sh * scale))), Image.LANCZOS
    )
    ax, ay = CROP_ANCHOR.get(idx, (0.5, 0.5))
    x = round((im.size[0] - w) * ax)
    y = round((im.size[1] - h) * ay)
    im = im.crop((x, y, x + w, y + h))
    im = im.filter(
        ImageFilter.UnsharpMask(radius=1, percent=PHOTO_UNSHARP, threshold=3)
    )
    if idx in EXPOSURE:
        g = EXPOSURE[idx]
        im = im.point(
            [min(255, int(round(255 * (v / 255) ** (1 / g)))) for v in range(256)] * 3
        )
    im = ImageEnhance.Color(im).enhance(PHOTO_COLOR)
    return tone_compress(im), (sw, sh)


def placeholder_cell(cell, rx):
    im = Image.new("RGB", (cell.w, cell.h), PLACEHOLDER_FILL)
    d = ImageDraw.Draw(im)
    need_w = math.ceil(cell.w * MIN_DPI / 25.4)
    need_h = math.ceil(cell.h * MIN_DPI / 25.4)
    lines = [
        (f"{cell.idx:02d}  {cell.theme}", 56, PLACEHOLDER_INK),
        (
            f"{cell.w/10:.1f}×{cell.h/10:.1f}cm ‧ {'斜切梯形' if cell.slanted else '矩形'}",
            24,
            PLACEHOLDER_INK,
        ),
        (f"≥{need_w}×{need_h}px", 24, PLACEHOLDER_INK),
    ]
    if cell.slanted:
        lines.append(("主體靠左上", 24, ORANGE))  # STHeiti 無 ▸/→，會變豆腐方框

    y = 30
    for text, size, fill in lines:
        # 斜切格越往下越窄，逐行按該行實際可用寬度縮字
        avail = min(cell.x + cell.w, rx(cell.y + y + size)) - cell.x - 80
        font = ImageFont.truetype(ZHF, size)
        while size > 16:
            bx0, _, bx1, _ = ink_bbox(text, font)
            if bx1 - bx0 <= avail:
                break
            size -= 2
            font = ImageFont.truetype(ZHF, size)
        d.text((40, y), text, font=font, fill=fill)
        y += size + (10 if size > 30 else 6)
    return im


def load_sources(photo_dir):
    if not photo_dir:
        return {}
    src = {}
    for f in sorted(
        glob.glob(f"{photo_dir}/*.jpg")
        + glob.glob(f"{photo_dir}/*.jpeg")
        + glob.glob(f"{photo_dir}/*.png")
    ):
        m = re.match(r"(\d{1,2})[_\-]", os.path.basename(f))
        if m:
            src[int(m.group(1))] = f
    return src


# ---------------------------------------------------------------- 繪製


def draw_edge_band(canvas, frame):
    w, h = frame["W"], frame["H"]
    band = ImageChops.subtract(
        tri_mask(frame["bleed"], w, h), tri_mask(frame["inner"], w, h)
    )
    canvas.paste(GREEN, (0, 0, w, h), band)


def draw_cropmarks(canvas, frame):
    d = ImageDraw.Draw(canvas)
    cut = frame["cut"]
    cx = sum(p[0] for p in cut) / 3.0
    cy = sum(p[1] for p in cut) / 3.0
    for k in range(3):
        ax, ay = cut[k]
        bx, by = cut[(k + 1) % 3]
        nx, ny = ay - by, bx - ax
        norm = math.hypot(nx, ny)
        nx, ny = nx / norm, ny / norm
        if nx * (cx - ax) + ny * (cy - ay) > 0:  # 指向外側
            nx, ny = -nx, -ny
        for t in CROPMARK_T:
            px, py = ax + (bx - ax) * t, ay + (by - ay) * t
            d.line(
                (
                    px + nx * CROPMARK_IN,
                    py + ny * CROPMARK_IN,
                    px + nx * CROPMARK_OUT,
                    py + ny * CROPMARK_OUT,
                ),
                fill=BLACK,
                width=CROPMARK_W,
            )


def draw_cells(canvas, frame, cells, sources):
    safe = tri_mask(frame["safe"], frame["W"], frame["H"])
    _, rx = edge_fns(frame["safe"])
    stats = {}
    for c in cells:
        m = rrect_mask(c.w, c.h, CARD_RADIUS)
        m = ImageChops.multiply(m, safe.crop(c.box))
        inner = erode(m, STROKE)
        if c.idx in sources:
            content, src_size = prep_photo(sources[c.idx], c.w, c.h, c.idx)
            stats[c.idx] = src_size
        else:
            content = placeholder_cell(c, rx)
        canvas.paste(content, (c.x, c.y), inner)
        canvas.paste(GREEN, c.box, ImageChops.subtract(m, inner))
    return stats


def draw_title(canvas, frame, color=GREEN):
    font, (ix, iy), _, (bx0, by0) = plan_title(frame)
    kw = (
        {"stroke_width": TITLE_STROKE, "stroke_fill": TITLE_STROKE_FILL}
        if color == WHITE
        else {}
    )
    ImageDraw.Draw(canvas).text(
        (ix - bx0, iy - by0), TITLE_TEXT, font=font, fill=color, **kw
    )


def draw_draft_warning(canvas, frame):
    ImageDraw.Draw(canvas).text(
        (frame["W"] - 900, frame["H"] - 46),
        "佔位樣板 ‧ 非印刷檔 ‧ 請勿送印",
        font=ImageFont.truetype(ZHF, 30),
        fill=BLACK,
    )


def gen_backdrop(path, seed, scene):
    """Pollinations.ai 免金鑰生圖（Gemini 影像模型在本 key 免費額度為 0）。
    ⚠️ 不論要多大它都固定回 991×594，大圖輸出得接受 3 倍以上放大。"""
    import urllib.parse
    import urllib.request

    q = urllib.parse.urlencode(
        {"width": 1920, "height": 1152, "model": "flux", "nologo": "true", "seed": seed}
    )
    url = POLLI + urllib.parse.quote(BACKDROP_PROMPTS[scene]) + "?" + q
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for _ in range(4):
        try:
            data = urllib.request.urlopen(req, timeout=300).read()
            if len(data) > 5000:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                open(path, "wb").write(data)
                print(f"✅ 底圖素材 {path}  {Image.open(path).size}")
                return path
        except Exception as e:
            print(f"   重試：{e}")
        time.sleep(5)
    raise RuntimeError("Pollinations 生圖失敗")


def _rolloff(a, knee=110.0, ceil=None):
    """高光滾降：上限 150 ×1.65 = 248 < 250，保證下游提亮後不過曝。"""
    ceil = BACKDROP_CEIL if ceil is None else ceil
    hi = a > knee
    t = (a[hi] - knee) / (255.0 - knee)
    a[hi] = knee + (ceil - knee) * (1 - (1 - t) ** 2)
    return a


def backdrop(path, frame, visible, tint="warm"):
    """滿版實景照壓暗成氛圍底：目標平均亮度對齊既有 12 面母檔（42~50）。"""
    im = Image.open(path).convert("RGB")
    w, h = frame["W"], frame["H"]
    scale = max(w / im.size[0], h / im.size[1])
    im = im.resize(
        (math.ceil(im.size[0] * scale), math.ceil(im.size[1] * scale)), Image.LANCZOS
    )
    im = im.crop(
        (
            (im.size[0] - w) // 2,
            (im.size[1] - h) // 2,
            (im.size[0] - w) // 2 + w,
            (im.size[1] - h) // 2 + h,
        )
    )
    im = im.filter(ImageFilter.GaussianBlur(BACKDROP_BLUR))  # 抹掉 3.3 倍放大的插值痕跡

    im = Image.blend(im, Image.new("RGB", (w, h), TINTS[tint]), BACKDROP_TINT)

    a = np.asarray(im).astype(np.float32)
    # 只用三角形內的可見像素校準（整張矩形會被裁掉的暗角會拉偏平均）
    t = BACKDROP_TARGET_LUM
    a *= t / a[visible].mean()

    # 飽和與暖偏收斂到既有 12 面的實測值。兩者都繞「通道平均」操作，
    # 不影響亮度，故可與亮度正規化分開做
    for _ in range(3):
        g = a.mean(axis=2, keepdims=True)
        p = a[visible]
        a = g + (a - g) * (BACKDROP_TARGET_SAT / (p.max(axis=1) - p.min(axis=1)).mean())
        if tint == "warm":
            r, gr, b = a[visible].mean(axis=0)
            # 解 r'-b'=目標R−B 且 r'+b'=r+b（總亮度不變）
            a[..., 0] *= (r + b + BACKDROP_TARGET_RB) / 2 / r
            a[..., 2] *= (r + b - BACKDROP_TARGET_RB) / 2 / b
        np.clip(a, 0, 255, out=a)

    # 滾降必然壓低平均，若以它收尾會系統性欠亮；先估收縮率 k、預先降低上限，
    # 最後一步才正規化，讓上限剛好彈回 BACKDROP_CEIL
    k = _rolloff(a.copy())[visible].mean() / a[visible].mean()
    a = _rolloff(a, ceil=BACKDROP_CEIL * k)
    a *= t / a[visible].mean()
    rng = np.random.default_rng(7)
    a += rng.normal(0, BACKDROP_GRAIN, a.shape)  # 顆粒同時抑制 CMYK 分色帶狀
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def build(sources, opts):
    frame = canvas_frame()
    cells = plan_cells(frame)
    canvas = Image.new("RGB", (frame["W"], frame["H"]), WHITE)
    if opts.bg:
        clip = tri_mask(frame["bleed"], frame["W"], frame["H"])
        visible = np.asarray(tri_mask(frame["safe"], frame["W"], frame["H"])) > 200
        # 校準區排除標題帶：白字會蓋掉那塊，且部分素材上緣特別亮會拉偏平均
        visible[: int(frame["safe"][0][1] + TITLE_H), :] = False
        canvas.paste(backdrop(opts.bg, frame, visible, opts.tint), (0, 0), clip)
    draw_edge_band(canvas, frame)
    stats = draw_cells(canvas, frame, cells, sources) if (sources or opts.cells) else {}
    draw_title(canvas, frame, WHITE if opts.bg else GREEN)
    draw_cropmarks(canvas, frame)
    if opts.draft:
        draw_draft_warning(canvas, frame)
    return canvas, frame, cells, stats


# ---------------------------------------------------------------- 驗證


def verify(master, sim, frame, cells, sources, stats, opts):
    a = np.asarray(master).astype(int)
    s = np.asarray(sim).astype(int)
    ok = []
    cut, safe = frame["cut"], frame["safe"]

    ok.append((f"母檔尺寸 {master.size}", master.size == (frame["W"], frame["H"])))

    sides = [
        ("頂邊", math.dist(cut[0], cut[1]), SIDE_TOP),
        ("左邊", math.dist(cut[0], cut[2]), SIDE_LEFT),
        ("底斜邊", math.dist(cut[1], cut[2]), SIDE_SLANT),
    ]
    for name, got, want in sides:
        ok.append((f"{name} {got:.3f}mm (應 {want:.0f})", abs(got - want) < 0.01))
    area = tri_area(cut) / 1e6
    ok.append((f"面積 {area:.4f} m²", abs(area - 2.6539) < 0.001))
    ang = angle_at(cut[0], cut[1], cut[2])
    ok.append((f"左上角 {ang:.3f}° (非直角!)", abs(ang - 91.659) < 0.01))

    def sample(edge_pts, dist, inward):
        cx = sum(p[0] for p in cut) / 3.0
        cy = sum(p[1] for p in cut) / 3.0
        out = []
        for k in range(3):
            ax, ay = edge_pts[k]
            bx, by = edge_pts[(k + 1) % 3]
            nx, ny = ay - by, bx - ax
            norm = math.hypot(nx, ny)
            nx, ny = nx / norm, ny / norm
            if (nx * (cx - ax) + ny * (cy - ay) > 0) != inward:
                nx, ny = -nx, -ny
            for t in np.linspace(0.06, 0.94, 21):
                if min(abs(t - m) for m in CROPMARK_T) < 0.02:
                    continue
                px = ax + (bx - ax) * t + nx * dist
                py = ay + (by - ay) * t + ny * dist
                out.append(tuple(a[int(round(py)), int(round(px))]))
        return out

    ok.append(("綠帶內側 13mm 全為綠", all(c == GREEN for c in sample(cut, 13, True))))
    ok.append(("出血外側 10mm 全為綠", all(c == GREEN for c in sample(cut, 10, False))))
    ok.append(
        (
            "外側 35mm 全為白 (未整片刷綠)",
            all(c == WHITE for c in sample(cut, 35, False)),
        )
    )
    ok.append(
        (
            f"綠色 = {GREEN} #079A3F",
            tuple(a[0, 0]) != GREEN
            and GREEN in [tuple(c) for c in sample(cut, 13, True)],
        )
    )

    safe_mask = np.asarray(tri_mask(safe, frame["W"], frame["H"]))
    cover = np.zeros((frame["H"], frame["W"]), dtype=np.int32)
    overflow = 0
    for c in cells:
        m = rrect_mask(c.w, c.h, CARD_RADIUS)
        m = np.asarray(
            ImageChops.multiply(m, tri_mask(safe, frame["W"], frame["H"]).crop(c.box))
        )
        overflow += int(
            ((m > 8) & (safe_mask[c.y : c.y + c.h, c.x : c.x + c.w] == 0)).sum()
        )
        cover[c.y : c.y + c.h, c.x : c.x + c.w] += (m > 128).astype(np.int32)
    ok.append((f"格子超出安全區 {overflow}px", overflow == 0))
    ok.append((f"格子重疊 {int((cover > 1).sum())}px", int((cover > 1).sum()) == 0))
    ok.append((f"格數 {len(cells)}", len(cells) == 10))

    drawn = bool(sources or opts.cells)
    if drawn:
        widths = []
        for c in cells:
            n = 0
            for px in a[c.y + c.h // 2, c.x : c.x + 3 * STROKE]:
                if tuple(px) == GREEN:
                    n += 1
                elif n:
                    break
            widths.append(n)
        ok.append(
            (
                f"綠描邊寬 {min(widths)}~{max(widths)}px (應 {STROKE})",
                all(abs(n - STROKE) <= 2 for n in widths),
            )
        )

    keep = []
    for vx, vy in cut:
        for c in cells:
            cxs = np.clip([c.x, c.x + c.w], 0, None)
            near = math.hypot(
                max(cxs[0] - vx, 0, vx - cxs[1]), max(c.y - vy, 0, vy - (c.y + c.h))
            )
            keep.append(near >= CORNER_KEEPOUT)
    ok.append((f"三頂點 {CORNER_KEEPOUT}mm 淨空", all(keep)))

    font, (ix, iy), (tw, th), _ = plan_title(frame)
    lx, rx = edge_fns(safe)
    ok.append((f"標題字高 {th}mm", th >= 180))
    ok.append(
        (
            f"標題墨色框 x{ix}~{ix+tw} y{iy}~{iy+th} 在安全區內",
            ix >= lx(iy + th)
            and ix + tw <= rx(iy + th)
            and iy + th <= safe[0][1] + TITLE_H,
        )
    )
    want = WHITE if opts.bg else GREEN
    hit = (a[iy : iy + th, ix : ix + tw] == want).all(axis=2).mean() * 100
    ok.append((f"標題色 {want} 覆蓋 {hit:.1f}%", hit > 10.0))

    worst_dpi, worst = None, None
    for c in cells:
        if c.idx not in stats:
            continue
        sw, _ = stats[c.idx]
        dpi = sw / (c.w / 25.4)
        if worst_dpi is None or dpi < worst_dpi:
            worst_dpi, worst = dpi, c.idx
        ok.append((f"#{c.idx:02d} 照片為縮小非放大 ({sw}→{c.w})", sw >= c.w))
    if worst_dpi is not None:
        ok.append(
            (f"最低有效解析度 {worst_dpi:.1f} dpi (#{worst})", worst_dpi >= MIN_DPI)
        )

    if sources:
        blown = []
        for c in cells:
            reg = s[
                c.y + STROKE : c.y + c.h - STROKE, c.x + STROKE : c.x + c.w - STROKE
            ]
            b = (reg >= 250).all(axis=2).mean() * 100
            blown.append(b)
            if c.idx in sources:
                ok.append((f"#{c.idx:02d} 過曝 {b:.2f}%", b < 8.0))
        ok.append(
            (f"照片區整體過曝 {np.mean(blown):.2f}%", float(np.mean(blown)) < 5.0)
        )

    if opts.bg:
        # 白色標題本身就是 255，量底圖亮度/過曝一律排除標題帶
        below = np.asarray(tri_mask(safe, frame["W"], frame["H"])) > 200
        below[: int(safe[0][1] + TITLE_H), :] = False
        if drawn:  # 校稿模式的灰框／照片會蓋住底圖，量到的不是底圖本身
            for c in cells:
                below[c.y : c.y + c.h, c.x : c.x + c.w] = False
        lum = a.mean(axis=2)[below].mean()
        ok.append((f"底圖母檔平均亮度 {lum:.1f} (既有12面 42~50)", 38 <= lum <= 54))
        p = a[below]
        sat = (p.max(axis=1) - p.min(axis=1)).mean()
        ok.append((f"底圖飽和度 {sat:.1f} (既有12面 32~46)", 28 <= sat <= 50))
        rb = p[:, 0].mean() - p[:, 2].mean()
        ok.append((f"底圖暖偏 R−B {rb:+.1f} (既有12面 +27~+38)", 20 <= rb <= 45))
        blown = (s >= 250).all(axis=2)[below].mean() * 100
        ok.append(
            (
                f"底圖印刷模擬亮度 {s.mean(axis=2)[below].mean():.1f}／過曝 {blown:.2f}%",
                blown < 2.0,
            )
        )
        holes = ((a == 255).all(axis=2) & below).sum()
        ok.append((f"三角形內未上底圖的白洞 {holes}px", holes == 0))
    band_sim = tuple(s[int(cut[0][1]) + 13, int((cut[0][0] + cut[1][0]) / 2)])
    ok.append((f"綠帶印刷模擬 {band_sim} (1.65 已頂天)", band_sim == (0, 255, 52)))

    print("\n{:<48} {}".format("檢查項目", "結果"))
    print("-" * 60)
    for name, passed in ok:
        print("{:<48} {}".format(name, "✅" if passed else "❌"))
    return all(p for _, p in ok)


# ---------------------------------------------------------------- 輸出


def verify_pdf(path, frame):
    """抽驗油墨未反相：三冠彩印的 RIP 曾把 CMYK 影像整張負片化。"""
    import zlib

    raw = open(path, "rb").read()
    head = raw.index(b"5 0 obj")
    hdr = raw[head : head + 400]
    w = int(re.search(rb"/Width (\d+)", hdr).group(1))
    h = int(re.search(rb"/Height (\d+)", hdr).group(1))
    cmyk = b"/DeviceCMYK" in hdr
    mb = re.search(rb"/MediaBox \[0 0 ([\d.]+) ([\d.]+)\]", raw)
    page_cm = (float(mb.group(1)) / 72 * 2.54, float(mb.group(2)) / 72 * 2.54)

    start = raw.index(b"stream\n", head) + 7
    scale = w / frame["W"]
    buf = zlib.decompressobj().decompress(raw[start : start + (1 << 24)], 500 * w * 4)
    del raw

    def px(xmm, ymm):
        i = (round(ymm * scale) * w + round(xmm * scale)) * 4
        return tuple(buf[i : i + 4])

    ok = [
        (
            f"PDF 頁面 {page_cm[0]:.1f}×{page_cm[1]:.1f} cm",
            abs(page_cm[0] - frame["W"] / 10) < 0.1,
        ),
        (
            f"PDF 影像 {w}×{h}px",
            (w, h) == (round(frame["W"] * 100 / 25.4), round(frame["H"] * 100 / 25.4)),
        ),
        ("色彩空間 DeviceCMYK", cmyk),
        (f"三角形外白區油墨 {px(60, 20)} 應近 0", max(px(60, 20)) <= 6),
        (f"左上 PAD 白區油墨 {px(30, 100)} 應近 0", max(px(30, 100)) <= 6),
    ]
    print("\n{:<48} {}".format("PDF 抽驗", "結果"))
    print("-" * 60)
    for name, passed in ok:
        print("{:<48} {}".format(name, "✅" if passed else "❌"))
    return all(p for _, p in ok)


def write_spec(frame, cells, path):
    cut = frame["cut"]
    lines = [
        "# 三角布 裁切規格說明",
        "",
        "## 成品尺寸（裁切線）",
        "",
        "| 邊 | 長度 |",
        "|---|---|",
        f"| 頂邊 | {math.dist(cut[0], cut[1])/10:.1f} cm |",
        f"| 左邊 | {math.dist(cut[0], cut[2])/10:.1f} cm |",
        f"| 底斜邊 | {math.dist(cut[1], cut[2])/10:.1f} cm |",
        "",
        f"面積 {tri_area(cut)/1e6:.4f} m²，外接框 "
        f"{max(p[0] for p in cut)-min(p[0] for p in cut):.1f} × "
        f"{max(p[1] for p in cut)-min(p[1] for p in cut):.1f} mm。",
        "",
        f"角度：左上 {angle_at(cut[0], cut[1], cut[2]):.3f}°／"
        f"右上 {angle_at(cut[1], cut[0], cut[2]):.3f}°／"
        f"左下 {angle_at(cut[2], cut[0], cut[1]):.3f}°。",
        "",
        "⚠️ 左上角是 91.66° **不是直角**。若強制做成直角，斜邊只有 345.6cm，短 4.4cm 會露牆。",
        "",
        "## 裁切線頂點（PDF 頁面左上角為原點，單位 mm，1px=1mm ×100dpi 輸出）",
        "",
        "| 頂點 | X | Y |",
        "|---|---|---|",
    ]
    for name, p in zip(("左上", "右上", "左下尖角"), cut):
        lines.append(f"| {name} | {p[0]:.1f} | {p[1]:.1f} |")
    lines += [
        "",
        f"頁面尺寸 {frame['W']/10:.1f} × {frame['H']/10:.1f} cm（含出血與裁切標記留邊）。",
        "",
        "## 出血",
        "",
        f"- 出血 **{BLEED}mm**：品牌綠帶自裁切線往外延伸 {BLEED}mm，往內 {BORDER}mm。",
        f"- 裁切後可見綠邊寬 {BORDER}mm（與既有 12 面外牆防水布一致）。",
        f"- 裁切公差 ±{BLEED}mm 內只會讓綠邊變粗細，不會露白。",
        "- 三邊各有 3 支黑色裁切標記（垂直邊線、位於裁切線外 30~55mm），裁切後即消失。",
        "- 不做折邊車縫、不打雞眼（同外牆現有 12 面做法）。",
        "",
        "## 色彩",
        "",
        "- DeviceCMYK，ICC = Generic CMYK Profile，rendering intent = PERCEPTUAL。",
        "- 100dpi 全尺寸內嵌影像，FlateDecode。",
        "- 品牌綠 #079A3F。",
        "",
        "## 格位表",
        "",
        "| # | 主題 | 位置 (mm) | 尺寸 | 形狀 |",
        "|---|---|---|---|---|",
    ]
    for c in cells:
        lines.append(
            f"| {c.idx:02d} | {c.theme} | x{c.x} y{c.y} | {c.w/10:.1f}×{c.h/10:.1f}cm | "
            f"{'斜切梯形' if c.slanted else '矩形'} |"
        )
    open(path, "w").write("\n".join(lines) + "\n")


def print_photo_request(cells):
    print("\n給協會的照片需求清單")
    print("-" * 74)
    print(
        f"{'#':>3}  {'主題':<10} {'尺寸':<14} {'形狀':<10} {'最低解析度':<14} 建議檔名"
    )
    for c in cells:
        need = f"≥{math.ceil(c.w*MIN_DPI/25.4)}×{math.ceil(c.h*MIN_DPI/25.4)}px"
        print(
            f"{c.idx:>3}  {c.theme:<10} {c.w/10:.1f}×{c.h/10:.1f}cm   "
            f"{'斜切梯形' if c.slanted else '矩形':<10} {need:<14} "
            f"{c.idx:02d}_{c.theme}_XXX.jpg"
        )
    print("\n共 10 張（建議先給 20~25 張候選）。全部橫式約 5:3，建議長邊 ≥1600px。")
    print(
        "斜切格 "
        + "／".join(f"#{c.idx:02d}" for c in cells if c.slanted)
        + " 右下角會被斜邊裁掉，主體請靠左上。"
    )
    print("⚠️ 每張需確認肖像同意，特別是送餐對象（受助長者）。")


def main():
    global TITLE_TEXT
    ap = argparse.ArgumentParser()
    ap.add_argument("--photos", help="照片資料夾，檔名前兩碼為格號")
    ap.add_argument("--bg", help="底圖素材路徑（滿版實景照）")
    ap.add_argument(
        "--gen-bg", type=int, metavar="SEED", help="用 Pollinations 生一張底圖素材"
    )
    ap.add_argument(
        "--scene", default="table", choices=sorted(BACKDROP_PROMPTS), help="底圖場景"
    )
    ap.add_argument("--tint", default="warm", choices=sorted(TINTS), help="底圖色調")
    ap.add_argument(
        "--cells", action="store_true", help="疊出照片框位置（校稿用，非交付檔）"
    )
    ap.add_argument("--pdf", action="store_true", help="產出 100dpi CMYK PDF")
    ap.add_argument("--name", default="", help="輸出檔名附註，例如 _A")
    ap.add_argument("--title", default=TITLE_TEXT)
    args = ap.parse_args()
    TITLE_TEXT = args.title

    os.makedirs(OUT_DIR, exist_ok=True)
    if args.gen_bg:
        args.bg = gen_backdrop(
            f"{OUT_DIR}/素材/底圖素材_{args.scene}_seed{args.gen_bg}.png",
            args.gen_bg,
            args.scene,
        )

    sources = load_sources(args.photos)
    args.draft = bool(sources) and len(sources) < len(THEMES)
    if args.cells and not sources:
        args.draft = True

    master, frame, cells, stats = build(sources, args)
    tag = ("_佔位樣板_勿印" if args.draft else "") + args.name
    kind = "底圖" if args.bg and not sources else "相簿"
    out = f"{OUT_DIR}/三角布_惜食廚房{kind}_295-180-350cm_母檔{tag}.png"
    master.save(out)

    sim = enhance_like_pdf(master)
    sim.save(f"{OUT_DIR}/預覽_三角布_印刷模擬{tag}.png")
    sim.resize((1200, round(1200 * frame["H"] / frame["W"])), Image.LANCZOS).save(
        f"{OUT_DIR}/預覽_三角布_縮圖{tag}.png"
    )
    # 1:1 印刷尺度抽驗：底圖模式取左側人物區（細節最多），相簿模式取第 06 格
    c6 = next(c for c in cells if c.idx == 6)
    ox, oy = (380, 420) if (args.bg and not sources) else (c6.x + 60, c6.y + 20)
    face = sim.crop((ox, oy, ox + 240, oy + 240))
    face.resize((int(240 * 3.937), int(240 * 3.937)), Image.LANCZOS).save(
        f"{OUT_DIR}/預覽_三角布_1比1{tag}.png"
    )
    write_spec(frame, cells, f"{OUT_DIR}/三角布_裁切規格說明.md")

    print(f"✅ 母檔 {out}")
    print(
        f"   {frame['W']/10:.1f} × {frame['H']/10:.1f} cm 頁面，"
        f"{'底圖（無照片框）' if kind == '底圖' else f'{len(cells)} 格'}，"
        f"照片 {len(sources)}/{len(THEMES)} 張"
    )

    passed = verify(master, sim, frame, cells, sources, stats, args)
    print("\n" + ("全部通過" if passed else "⚠️ 有項目未通過，見上表"))

    if args.draft:
        print_photo_request(cells)

    if args.pdf:
        pdf = f"{OUT_DIR}/三角布_惜食廚房相簿_295x180x350cm_含出血_CMYK{tag}.pdf"
        build_cmyk_pdf(out, 0, 0, pdf)
        passed = verify_pdf(pdf, frame) and passed
        print("\n" + ("全部通過" if passed else "⚠️ 有項目未通過，見上表"))


if __name__ == "__main__":
    main()
