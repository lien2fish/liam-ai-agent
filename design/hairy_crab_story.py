"""大閘蟹限動三連發（1080x1920）：參考鑫海產 IG 輪播的版型（深色底、粗黑大標、金色筆刷底線、底部 CTA 橫幅）。

文案依品牌規則克制：不寫產地、不放價格、不用促銷形容詞（Lien 10-30 選「視覺熱鬧、文案克制」）。
照片：Wikimedia Commons「Roe inside steamed female hairy crab.jpg」，Jpatokal，CC BY-SA 4.0——要標作者，不可拿掉。
事實出處同 design/hairy_crab_dm.py。
頂部品牌標目前用文字，拿到鑫海產 logo 原檔後換 LOGO。
"""

import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ig_carousel import BOLD, GOLD, HEAVY, INK, INK_SOFT, REGULAR, REPO, font

W, H = 1080, 1920
BG = (16, 16, 18)
BRUSH = (226, 172, 58)
OUT_DIR = os.path.join(REPO, "成品/DM/大閘蟹/限動三連發")
ROE = os.path.join(REPO, "design/assets/hairy_crab/roe_steamed.jpg")
LOGO = None
CREDIT = "Photo: Jpatokal / CC BY-SA 4.0"
HANDLE = "@lienstable｜連老闆・鑫海產"


def background(seed):
    rnd = random.Random(seed)
    im = Image.new("RGB", (W // 4, H // 4), BG)
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            n = rnd.randint(-7, 7)
            px[x, y] = tuple(max(0, c + n) for c in BG)
    im = im.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(2))
    vig = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vig).ellipse((-300, -200, W + 300, H + 200), fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(220))
    return Image.composite(im, Image.new("RGB", (W, H), (6, 6, 7)), vig).convert("RGBA")


def brush(canvas, x0, x1, y, thick, seed):
    """乾筆刷底線：多條抖動的細線疊出來，兩端收尖。"""
    rnd = random.Random(seed)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for k in range(int(thick * 1.6)):
        off = rnd.uniform(-thick / 2, thick / 2)
        a = rnd.uniform(0, 0.12)
        b = rnd.uniform(0.85, 1.0)
        pts = []
        for i in range(60):
            t = a + (b - a) * i / 59
            x = x0 + (x1 - x0) * t
            taper = math.sin(math.pi * t) ** 0.35
            pts.append((x, y - 6 * t + off * taper + rnd.uniform(-1, 1)))
        d.line(pts, fill=BRUSH + (rnd.randint(150, 255),), width=rnd.randint(2, 4))
    canvas.alpha_composite(layer)


def text_shadow(canvas, xy, s, f, fill, anchor="la", blur=8):
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text(
        (xy[0] + 4, xy[1] + 6), s, font=f, fill=(0, 0, 0, 200), anchor=anchor
    )
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(canvas).text(xy, s, font=f, fill=fill, anchor=anchor)


def tilted(canvas, xy, lines, f, fill, angle=-3, spacing=12):
    """參考圖的斜排小字：先畫在透明層再整塊轉。"""
    lh = f.size + spacing
    w = max(int(ImageDraw.Draw(canvas).textlength(s, font=f)) for s in lines) + 40
    layer = Image.new("RGBA", (w, lh * len(lines) + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i, s in enumerate(lines):
        d.text((20, 20 + i * lh), s, font=f, fill=fill)
    layer = layer.rotate(-angle, resample=Image.BICUBIC, expand=True)
    canvas.alpha_composite(layer, xy)


def ticks(canvas, x, y):
    """參考圖標題旁的兩撇強調記號。"""
    d = ImageDraw.Draw(canvas)
    d.line([(x, y + 40), (x + 14, y)], fill=BRUSH, width=9)
    d.line([(x + 26, y + 46), (x + 44, y + 8)], fill=BRUSH, width=9)


def brand(canvas):
    d = ImageDraw.Draw(canvas)
    if LOGO:
        lg = Image.open(LOGO).convert("RGBA")
        lg.thumbnail((420, 140))
        canvas.alpha_composite(lg, ((W - lg.width) // 2, 250))
        return
    d.text((W / 2, 262), "鑫海產", font=font(HEAVY, 64), fill=GOLD, anchor="ma")
    d.text(
        (W / 2, 342),
        "連老闆・產地到餐桌",
        font=font(REGULAR, 28),
        fill=INK_SOFT,
        anchor="ma",
    )


def photo(box_w, box_h, focus_y, darken=1.0):
    im = Image.open(ROE).convert("RGB")
    s = box_w / im.width
    im = im.resize((box_w, round(im.height * s)), Image.LANCZOS)
    top = min(max(0, round(im.height * focus_y - box_h / 2)), im.height - box_h)
    im = im.crop((0, top, box_w, top + box_h))
    if darken != 1.0:
        im = Image.eval(im, lambda v: int(v * darken))
    return im.convert("RGBA")


def fade_top(img, h):
    a = Image.new("L", img.size, 255)
    d = ImageDraw.Draw(a)
    for i in range(h):
        d.line([(0, i), (img.width, i)], fill=int(255 * (i / h) ** 1.3))
    img.putalpha(a)
    return img


def credit(canvas, y):
    f = font(REGULAR, 22)
    ImageDraw.Draw(canvas).text(
        (W - 60, y), CREDIT, font=f, fill=(150, 140, 120), anchor="ra"
    )


def slide1():
    c = background(1)
    ph = fade_top(photo(W, 1020, 0.55), 260)
    c.alpha_composite(ph, (0, H - 1020 - 90))
    ImageDraw.Draw(c).rectangle([0, H - 90, W, H], fill=(6, 6, 7))
    brand(c)
    text_shadow(c, (W / 2, 420), "大閘蟹", font(HEAVY, 200), INK, "ma")
    text_shadow(c, (W / 2, 650), "母蟹吃黃・公蟹吃膏", font(HEAVY, 92), BRUSH, "ma")
    brush(c, 140, 940, 790, 16, 11)
    tilted(c, (110, 820), ["每隻 5.8–6.4 兩，", "公母都有。"], font(BOLD, 52), INK)
    ticks(c, 640, 860)
    credit(c, H - 70)
    return c


def bezier(p0, p1, p2, p3=None, n=24):
    out = []
    for i in range(n + 1):
        t = i / n
        if p3 is None:
            x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
            y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        else:
            x = (
                (1 - t) ** 3 * p0[0]
                + 3 * (1 - t) ** 2 * t * p1[0]
                + 3 * (1 - t) * t * t * p2[0]
                + t**3 * p3[0]
            )
            y = (
                (1 - t) ** 3 * p0[1]
                + 3 * (1 - t) ** 2 * t * p1[1]
                + 3 * (1 - t) * t * t * p2[1]
                + t**3 * p3[1]
            )
        out.append((x, y))
    return out


def belly(canvas, cx, cy, scale, female):
    """腹面示意，幾何同影片 species-02 的 bellyMarkup。頭在上。"""
    P = lambda x, y: (cx + x * scale, cy + y * scale)
    d = ImageDraw.Draw(canvas)
    shell = (
        bezier(P(-150, -70), P(-135, -122), P(0, -125))
        + bezier(P(0, -125), P(135, -122), P(150, -70))
        + [P(128, 60)]
        + bezier(P(128, 60), P(95, 128), P(0, 132))
        + bezier(P(0, 132), P(-95, 128), P(-128, 60))
    )
    if female:
        abd = (
            bezier(P(-92, 116), P(-112, 30), P(-72, -46), P(0, -48))
            + bezier(P(0, -48), P(72, -46), P(112, 30), P(92, 116))
            + bezier(P(92, 116), P(0, 134), P(-92, 116))
        )
    else:
        abd = [
            P(-40, 122),
            P(-30, 70),
            P(-20, 20),
            P(0, -46),
            P(20, 20),
            P(30, 70),
            P(40, 122),
        ] + bezier(P(40, 122), P(0, 130), P(-40, 122))
    lw = max(3, int(5 * scale))
    d.line(shell + [shell[0]], fill=INK, width=lw, joint="curve")
    for y in (-40, 0, 40, 78):
        d.line([P(-140, y), P(-190, y + 26)], fill=INK, width=lw)
        d.line([P(140, y), P(190, y + 26)], fill=INK, width=lw)
    for sgn in (-1, 1):
        d.line(
            bezier(P(132 * sgn, -100), P(176 * sgn, -150), P(140 * sgn, -182)),
            fill=INK,
            width=lw,
        )
        d.line(
            bezier(P(140 * sgn, -182), P(112 * sgn, -170), P(120 * sgn, -140)),
            fill=INK,
            width=lw,
        )
    fill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(fill).polygon(abd, fill=BRUSH + (90,))
    canvas.alpha_composite(fill)
    d.line(abd + [abd[0]], fill=BRUSH, width=lw + 1, joint="curve")


def slide2():
    c = background(2)
    brand(c)
    text_shadow(c, (W / 2, 420), "公的母的", font(HEAVY, 150), INK, "ma")
    text_shadow(c, (W / 2, 600), "翻過來看肚子", font(HEAVY, 110), BRUSH, "ma")
    brush(c, 170, 910, 745, 14, 22)
    belly(c, 290, 1010, 1.15, True)
    belly(c, 790, 1010, 1.15, False)
    d = ImageDraw.Draw(c)
    for x, a, b in (
        (290, "母蟹・圓臍", "吃的是蟹黃"),
        (790, "公蟹・尖臍", "吃的是蟹膏"),
    ):
        d.text((x, 1200), a, font=font(HEAVY, 56), fill=BRUSH, anchor="ma")
        d.text((x, 1280), b, font=font(BOLD, 46), fill=INK, anchor="ma")
    d.text(
        (W / 2, 1360), "腹面示意圖", font=font(REGULAR, 26), fill=INK_SOFT, anchor="ma"
    )
    d.rounded_rectangle([90, 1440, W - 90, 1640], radius=24, outline=GOLD, width=3)
    d.text(
        (W / 2, 1468),
        "老話說「九雌十雄」",
        font=font(HEAVY, 56),
        fill=BRUSH,
        anchor="ma",
    )
    d.text(
        (W / 2, 1556),
        "農曆九月吃母蟹，十月吃公蟹",
        font=font(BOLD, 44),
        fill=INK,
        anchor="ma",
    )
    d.text(
        (W / 2, 1690),
        "資料：人民網、維基百科「中華絨螯蟹」",
        font=font(REGULAR, 24),
        fill=INK_SOFT,
        anchor="ma",
    )
    return c


def slide3():
    c = background(3)
    ph = fade_top(photo(W, 1400, 0.56, 0.42), 360)
    c.alpha_composite(ph, (0, H - 1400))
    brand(c)
    text_shadow(c, (W / 2, 420), "六兩大閘蟹", font(HEAVY, 150), INK, "ma")
    text_shadow(c, (W / 2, 600), "公母都有", font(HEAVY, 120), BRUSH, "ma")
    brush(c, 250, 830, 760, 14, 33)
    d = ImageDraw.Draw(c)
    rows = [
        ("規格", "每隻 5.8–6.4 兩"),
        ("公母", "母蟹吃黃・公蟹吃膏"),
        ("吃法", "整隻清蒸，原味最好"),
    ]
    y = 850
    for k, v in rows:
        d.line([(110, y), (W - 110, y)], fill=(90, 80, 60), width=2)
        d.text((130, y + 30), k, font=font(HEAVY, 50), fill=BRUSH)
        text_shadow(c, (300, y + 30), v, font(BOLD, 50), INK, blur=6)
        y += 130
    d.line([(110, y), (W - 110, y)], fill=(90, 80, 60), width=2)

    by = 1430
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    bd.polygon([(0, by + 18), (W, by + 6), (W, by + 150), (0, by + 140)], fill=BRUSH + (255,))
    rnd = random.Random(44)
    for k in range(70):
        off = rnd.choice((-1, 1)) * rnd.uniform(55, 82)
        bd.line(
            [
                (rnd.uniform(-20, 40), by + 80 + off),
                (W - rnd.uniform(-20, 60), by + 70 + off + rnd.uniform(-6, 6)),
            ],
            fill=BRUSH + (rnd.randint(170, 255),),
            width=rnd.randint(3, 6),
        )
    c.alpha_composite(band)
    d = ImageDraw.Draw(c)
    d.text(
        (300, by + 72), "私訊詢問", font=font(HEAVY, 92), fill=(20, 16, 10), anchor="mm"
    )
    d.line([(545, by + 30), (545, by + 116)], fill=(20, 16, 10), width=4)
    d.text((585, by + 30), "@lienstable", font=font(HEAVY, 46), fill=(20, 16, 10))
    d.text((585, by + 88), "連老闆・鑫海產", font=font(BOLD, 34), fill=(20, 16, 10))
    credit(c, H - 290)
    return c


def build():
    os.makedirs(OUT_DIR, exist_ok=True)
    for i, f in enumerate((slide1, slide2, slide3), 1):
        out = os.path.join(OUT_DIR, f"大閘蟹_限動{i}_1080x1920.jpg")
        f().convert("RGB").save(out, quality=94)
        print(out)


if __name__ == "__main__":
    build()
