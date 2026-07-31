# -*- coding: utf-8 -*-
"""單面布「惜食台灣行動協會」團體照版 — 從空白畫布重建版面（原始生成腳本已遺失）。

母檔 1px = 1mm。輸出母檔已預先反向補償 tarp_face_pdf.py 的 enhance()，
故母檔看起來偏暗屬正常，審稿請看 _印刷模擬 那份。

用法: python3 design/tarp_solo_photo.py
"""
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

Image.MAX_IMAGE_PIXELS = None

BASE = "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出"
DIR = f"{BASE}/外牆防水布"
LOGO = f"{BASE}/二樓面外大logo/惜食台灣_logo_HQ.png"
PHOTO = f"{DIR}/682115362_1378609137626433_7964303578723884924_n.jpg"
ZHF = "/System/Library/Fonts/STHeiti Medium.ttc"
REF = f"{DIR}/防水布_惜食台灣行動協會_3.6x1.25m.png"

W, H, BORDER = 3600, 1250, 26
WHITE = (255, 255, 255)

# tarp_face_pdf.py 的下游處理，供印刷模擬用
PDF_BRIGHTNESS, PDF_COLOR = 1.65, 1.83

# 母檔直接填 #079A3F 的話，經下游 ×1.65/×1.83 會印成 #00FF34 螢光綠。
# 這裡改填「印出來才是目標色」的補償值，故母檔取色器看到的不是品牌色。
PRINTED_GREEN = (7, 154, 63)  # 品牌綠 #079A3F
PRINTED_GOLD = (224, 165, 10)  # 深金黃 #E0A50A（原為 #FFC900，過亮）
LOGO_SRC_GREEN = (7, 154, 63)


def precompensate(target):
    """反解下游 enhance()：Color 保留 luma，故先反飽和再反亮度即可。"""
    lum = 0.299 * target[0] + 0.587 * target[1] + 0.114 * target[2]
    return tuple(
        max(0, min(255, round((lum + (t - lum) / PDF_COLOR) / PDF_BRIGHTNESS)))
        for t in target
    )


GREEN = precompensate(PRINTED_GREEN)
ORANGE = precompensate(PRINTED_GOLD)

LOGO_BOX = (287, 209, 706, 616)
LOGO_ALPHA_BBOX = (410, 574, 2925, 2765)
TITLE_SIZE, TITLE_X, TITLE_Y, LINE_PITCH = 300, 1090, 190, 370
SUB_SIZE, SUB_CX, SUB_Y = 138, 1682, 930

# 以人為主：裁掉上方 430px 的招牌與外牆，只留雨遮以下到腳底。
# 左右不裁——人群本來就佔滿整個畫面寬度，裁寬等於把邊緣的人切掉。
PHOTO_CROP = (0, 430, 1662, 1534)

# 卡寬 1200 是解析度天花板：原圖僅 1662px 寬，印出 1206mm 即掉到 35dpi 底線。
# 卡高由裁切比例反推、垂直置中，故改 PHOTO_CROP 不必手動算高度。
CARD_X, CARD_W = 2344, 1200
CARD_RADIUS, STROKE = 44, 12

# 亮部壓縮曲線：中間調 ×0.64、高光收斂到 118，避免下游 ×1.65 後牆面死白。
# 純線性壓暗（0.78/0.68）實測整體過曝 9.17%，本曲線 0.10%。
# 0.82/145（過曝 3.60%）與 0.72/130（0.55%）兩版現場審稿都判定過亮，已下修兩階。
PHOTO_KNEE, PHOTO_COMP, PHOTO_CEIL, PHOTO_COLOR = 130, 0.64, 118, 0.64


def card_rect():
    cw, ch_src = PHOTO_CROP[2] - PHOTO_CROP[0], PHOTO_CROP[3] - PHOTO_CROP[1]
    ih = round((CARD_W - 2 * STROKE) * ch_src / cw)
    card_h = ih + 2 * STROKE
    return CARD_X, (H - card_h) // 2, CARD_W, card_h


CARD = card_rect()


def ink_bbox(text, font):
    """CJK 的 textbbox 回傳 layout box 不是墨色框，改 render 後取 getbbox。"""
    pad = font.size
    tmp = Image.new("L", (len(text) * font.size + 2 * pad, font.size * 2 + 2 * pad), 0)
    ImageDraw.Draw(tmp).text((pad, pad), text, font=font, fill=255)
    bx0, by0, bx1, by1 = tmp.getbbox()
    return bx0 - pad, by0 - pad, bx1 - pad, by1 - pad


def recolor_logo(logo):
    """logo 只由品牌綠與白構成，用 R 通道反推綠白混合比後整體位移色差。

    直接重建 t*綠+(1-t)*白 會抹掉原檔的細微色雜訊，改加位移量保留原貌。
    """
    a = np.asarray(logo).astype(float)
    t = np.clip((255 - a[:, :, 0]) / (255 - LOGO_SRC_GREEN[0]), 0, 1)[:, :, None]
    delta = np.array(GREEN, dtype=float) - np.array(LOGO_SRC_GREEN, dtype=float)
    a[:, :, :3] = np.clip(a[:, :, :3] + t * delta, 0, 255)
    return Image.fromarray(a.astype(np.uint8))


def place_logo(canvas):
    logo = Image.open(LOGO).convert("RGBA").crop(LOGO_ALPHA_BBOX)
    logo = recolor_logo(logo).resize((LOGO_BOX[2], LOGO_BOX[3]), Image.LANCZOS)
    canvas.paste(logo, (LOGO_BOX[0], LOGO_BOX[1]), logo)


def draw_text(canvas):
    d = ImageDraw.Draw(canvas)
    title = ImageFont.truetype(ZHF, TITLE_SIZE)
    sub = ImageFont.truetype(ZHF, SUB_SIZE)

    # pen-x 只由第一行算出、第二行沿用 → 區塊視覺齊頭而非墨色齊頭
    bx0, by0, _, _ = ink_bbox("惜食台灣", title)
    pen_x, pen_y = TITLE_X - bx0, TITLE_Y - by0
    d.text((pen_x, pen_y), "惜食台灣", font=title, fill=GREEN)
    d.text((pen_x, pen_y + LINE_PITCH), "行動協會", font=title, fill=GREEN)

    text = "疼惜食物 ‧ 疼惜台灣"
    sx0, sy0, sx1, _ = ink_bbox(text, sub)
    d.text((SUB_CX - (sx1 - sx0) // 2 - sx0, SUB_Y - sy0), text, font=sub, fill=ORANGE)


def tone_compress(im):
    """膝點以下線性壓暗保住臉部，以上 ease-out 收斂到上限拉住高光。"""
    lut = []
    for v in range(256):
        if v <= PHOTO_KNEE:
            o = v * PHOTO_COMP
        else:
            t = (v - PHOTO_KNEE) / (255 - PHOTO_KNEE)
            base = PHOTO_KNEE * PHOTO_COMP
            o = base + (PHOTO_CEIL - base) * (1 - (1 - t) ** 2)
        lut.append(min(255, int(round(o))))
    return im.point(lut * 3)


def prep_photo():
    im = Image.open(PHOTO).convert("RGB").crop(PHOTO_CROP)
    pw = CARD[2] - 2 * STROKE
    ph = CARD[3] - 2 * STROKE
    im = im.filter(ImageFilter.GaussianBlur(0.5))
    im = im.resize((pw, ph), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=1, percent=45, threshold=3))
    im = ImageEnhance.Color(im).enhance(PHOTO_COLOR)
    return tone_compress(im)


def photo_card(canvas, photo):
    x, y, cw, ch = CARD
    card = Image.new("RGB", (cw, ch), GREEN)
    inner = Image.new("L", photo.size, 0)
    ImageDraw.Draw(inner).rounded_rectangle(
        (0, 0, photo.size[0] - 1, photo.size[1] - 1),
        radius=CARD_RADIUS - STROKE,
        fill=255,
    )
    card.paste(photo, (STROKE, STROKE), inner)

    mask = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, cw - 1, ch - 1), radius=CARD_RADIUS, fill=255
    )
    canvas.paste(card, (x, y), mask)


def enhance_like_pdf(img):
    img = ImageEnhance.Brightness(img).enhance(PDF_BRIGHTNESS)
    img = ImageEnhance.Color(img).enhance(PDF_COLOR)
    return img.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=3))


def build():
    canvas = Image.new("RGB", (W, H), WHITE)
    ImageDraw.Draw(canvas).rectangle((0, 0, W - 1, H - 1), outline=GREEN, width=BORDER)
    place_logo(canvas)
    draw_text(canvas)
    photo_card(canvas, prep_photo())
    return canvas


def verify(master, sim):
    a = np.asarray(master).astype(int)
    ok = []

    ok.append(("尺寸 3600×1250", master.size == (W, H)))
    ok.append((f"外框色 = 補償綠 {GREEN}", tuple(a[0, 0]) == GREEN))
    sp = tuple(np.asarray(sim).astype(int)[0, 0])
    ok.append(
        (
            "外框印出 #%02X%02X%02X (目標 #%02X%02X%02X)" % (sp + PRINTED_GREEN),
            max(abs(x - y) for x, y in zip(sp, PRINTED_GREEN)) <= 4,
        )
    )
    col = a[:, 1800]
    first = next(y for y in range(H) if tuple(col[y]) != GREEN)
    ok.append((f"外框寬 26px (實測 {first})", first == BORDER))

    def ink(x0, y0, x1, y1):
        r = a[y0:y1, x0:x1]
        m = r.sum(axis=2) < 720
        ys, xs = np.where(m)
        return (x0 + xs.min(), y0 + ys.min(), x0 + xs.max(), y0 + ys.max())

    # 搜尋區右界必須避開 x=CARD_X 的照片卡，否則綠色卡邊會被當成文字墨色
    t1 = ink(1000, 150, 2330, 500)
    ok.append(
        (f"主標L1 墨色框 {t1}", abs(t1[0] - TITLE_X) <= 2 and abs(t1[1] - TITLE_Y) <= 2)
    )
    # 兩行共用 pen 基準（視覺齊頭），各字字面高度不同故墨色框容許數 px 差
    t2 = ink(1000, 520, 2330, 880)
    ok.append(
        (f"主標L2 行距 {t2[1] - t1[1]}px", abs((t2[1] - t1[1]) - LINE_PITCH) <= 8)
    )
    sb = ink(1000, 900, 2330, 1100)
    ok.append((f"副標 墨色框 {sb}", abs(sb[1] - SUB_Y) <= 2))
    ok.append(
        (f"副標水平置中 cx={(sb[0]+sb[2])//2}", abs((sb[0] + sb[2]) // 2 - SUB_CX) <= 3)
    )

    def modal(x0, y0, x1, y1):
        r = a[y0:y1, x0:x1].reshape(-1, 3)
        r = r[r.sum(axis=1) < 720]
        c, n = np.unique(r, axis=0, return_counts=True)
        return tuple(c[n.argmax()])

    ok.append(("主標色 = 補償綠", modal(1090, 190, 2270, 470) == GREEN))
    ok.append(("副標色 = 補償金黃", modal(1067, 930, 2290, 1055) == ORANGE))

    def printed_modal(x0, y0, x1, y1):
        r = np.asarray(sim).astype(int)[y0:y1, x0:x1].reshape(-1, 3)
        r = r[r.sum(axis=1) < 720]
        c, n = np.unique(r, axis=0, return_counts=True)
        return tuple(c[n.argmax()])

    gp = printed_modal(1090, 190, 2270, 470)
    ok.append(
        (
            "主標印出 #%02X%02X%02X (目標 #%02X%02X%02X)" % (gp + PRINTED_GREEN),
            max(abs(x - y) for x, y in zip(gp, PRINTED_GREEN)) <= 4,
        )
    )
    yp = printed_modal(1067, 930, 2290, 1055)
    ok.append(
        (
            "副標印出 #%02X%02X%02X (目標 #%02X%02X%02X)" % (yp + PRINTED_GOLD),
            max(abs(x - y) for x, y in zip(yp, PRINTED_GOLD)) <= 4,
        )
    )

    src_w = PHOTO_CROP[2] - PHOTO_CROP[0]
    pw = CARD[2] - 2 * STROKE
    dpi = src_w / (pw / 25.4)
    ok.append((f"照片為縮小非放大 ({src_w}→{pw})", pw < src_w))
    ok.append((f"有效解析度 {dpi:.1f} dpi", dpi >= 35))

    s = np.asarray(sim).astype(int)
    px, py, ph2 = CARD[0] + STROKE, CARD[1] + STROKE, CARD[3] - 2 * STROKE
    sreg = s[py : py + ph2, px : px + pw]
    blown = (sreg >= 250).all(axis=2).mean() * 100
    ok.append((f"照片整體過曝 {blown:.2f}%", blown < 5.0))

    gap = CARD[0] - max(t1[2], t2[2], sb[2])
    ok.append((f"卡左緣與文字間距 {gap}px", gap >= 40))
    ok.append(
        (
            f"卡右緣留白 {W - BORDER - (CARD[0] + CARD[2])}px",
            CARD[0] + CARD[2] <= W - BORDER - 20,
        )
    )
    ok.append(
        (
            f"卡垂直置中 上{CARD[1]} 下{H - CARD[1] - CARD[3]}",
            abs(CARD[1] - (H - CARD[1] - CARD[3])) <= 1,
        )
    )

    # logo 已改色，不能再比對原母檔像素，改驗「形狀對位」＋「主色為補償綠」
    ref = np.asarray(Image.open(REF).convert("RGB")).astype(int)
    new_logo = a[
        LOGO_BOX[1] : LOGO_BOX[1] + LOGO_BOX[3], LOGO_BOX[0] : LOGO_BOX[0] + LOGO_BOX[2]
    ]
    old_logo = ref[317 : 317 + LOGO_BOX[3], LOGO_BOX[0] : LOGO_BOX[0] + LOGO_BOX[2]]

    # 深綠比原綠更早跨過固定門檻，遮罩會虛胖；改各自依自身色域正規化混合比
    def ink_mask(region, color):
        return (765 - region.sum(axis=2)) / (765 - sum(color)) > 0.5

    nm, om = ink_mask(new_logo, GREEN), ink_mask(old_logo, LOGO_SRC_GREEN)
    iou = (nm & om).sum() / (nm | om).sum()
    # 0.932 是同色基準（原母檔經多輪就地修改，抗鋸齒本來就對不齊），改色貢獻 0
    ok.append((f"Logo 形狀對位 IoU {iou:.3f}", iou > 0.92))

    lg = modal(*LOGO_BOX[:2], LOGO_BOX[0] + LOGO_BOX[2], LOGO_BOX[1] + LOGO_BOX[3])
    ok.append(
        (f"Logo 主色 = 補償綠 {lg}", max(abs(x - y) for x, y in zip(lg, GREEN)) <= 3)
    )

    print("\n{:<40} {}".format("檢查項目", "結果"))
    print("-" * 52)
    for name, passed in ok:
        print("{:<40} {}".format(name, "✅" if passed else "❌"))
    return all(p for _, p in ok)


def main():
    master = build()
    out = f"{DIR}/防水布_惜食台灣行動協會_團體照版_3.6x1.25m.png"
    master.save(out)

    sim = enhance_like_pdf(master)
    sim.save(f"{DIR}/預覽_團體照版_印刷模擬.png")
    sim.resize((1200, 417), Image.LANCZOS).save(f"{DIR}/預覽_團體照版_縮圖.png")

    # 人臉 1:1 印刷尺度裁切（母檔 1px → 100dpi 輸出 3.937px），取前排臉部
    face = sim.crop((2790, 470, 3030, 710))
    face.resize((int(240 * 3.937), int(240 * 3.937)), Image.LANCZOS).save(
        f"{DIR}/預覽_團體照版_人臉1比1.png"
    )

    print(f"✅ 母檔 {out}")
    ok = verify(master, sim)
    print("\n" + ("全部通過" if ok else "⚠️ 有項目未通過，見上表"))


if __name__ == "__main__":
    main()
