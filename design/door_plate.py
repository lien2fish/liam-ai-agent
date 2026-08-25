"""公司門牌平面輸出檔產生器

版型量測自 ~/Desktop/IMG_4585.jpg（鉅鑫管理顧問門牌）：
照片先做透視校正攤平成正面，再在攤平圖上以像素量測各元件位置，
單位換算依使用者提供的實際尺寸 37.4 x 10 cm。

字體一律轉外框（glyph_paths.py），輸出不依賴字型檔。
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fitz
from glyph_paths import load_face, glyph_contours, advance, upem, path_ops, ink_bbox

CM = 28.346456692913385
MM = CM / 10

OUT_DIR = "/Users/lien/Desktop/門牌_平面輸出"

PLATE_W, PLATE_H = 37.4, 10.0

COMPANY = "言兼言襄股份有限公司"
NUMBER = "495"

# ---- 版型（cm，量測值）----
RECESS_L, RECESS_T, RECESS_B = 11.36, 2.20, 7.80
RECESS_R = PLATE_W                      # 凹槽右側齊板邊
RECESS_LINE_W = 0.06
DRAW_RECESS = True

DIAG_TOP_X = 13.18                      # 對角線與上緣交點
DIAG_W = 0.17                           # 垂直於線的寬度

NUM_SIZE, NUM_ADV = 3.1329, 1.6645      # 495 字級與字距
NUM_INK_L, NUM_INK_T = 1.78, 1.64       # 495 ink 左上角

TXT_SIZE, TXT_ADV = 2.2198, 2.353       # 公司名字級與字距
TXT_CY = 5.34                           # 公司名 ink 垂直中心（實測；改 5.00 則為凹槽正中）
TXT_BOLD = 0.010                        # 加粗量（em 比例），0 = 不加粗

# ---- 顏色（DeviceCMYK）----
# 色值不是憑感覺挑的：用 MuPDF 的 CMYK 印刷模擬算繪出 RGB，
# 再去對照片透視校正後量到的實測值（底 RGB 35,33,30／銀 211,205,196）。
#
#   單色黑K100  算繪 RGB(34,31,31) —— 與原門牌實測 (35,33,30) 幾乎一致，這版是「對原門牌」
#   四色深黑    算繪 RGB(0,0,0)    —— 比原門牌深很多，要更黑的門牌才選這版
#
# 凹槽線隨底色配對，讓它與底色的明度差維持在 +23 左右（比照原門牌陰影線的對比）。
GROUNDS = {
    "單色黑K100": {"ground": (0.00, 0.00, 0.00, 1.00),
                   "recess": (0.35, 0.28, 0.28, 0.80)},
    "四色深黑": {"ground": (0.50, 0.40, 0.40, 1.00),
                 "recess": (0.42, 0.35, 0.35, 0.93)},
}
INK_SILVER = (0.165, 0.150, 0.200, 0.00)   # 算繪 RGB(211,205,196)，與照片零誤差
INK_MARK = (1, 1, 1, 1)

# 全版面不出血：頁面＝完成尺寸，無出血、無頁邊、不畫裁切標記。
# 要回到含出血版把這三個值改回 3*MM / 12*MM / True 即可。
BLEED = 0
MEDIA_PAD = 0
DRAW_MARKS = False
MARK_GAP = 3.5 * MM
MARK_LEN = 7 * MM
MARK_W = 0.25

FONT_CJK = ("/System/Library/Fonts/STHeiti Medium.ttc", 0)
FONT_NUM = ("/System/Library/Fonts/Supplemental/Times New Roman.ttf", 0)


def layout_string(face, text, size_cm, adv_cm):
    """回傳 (每字的 contours 與位移, ink bbox)；座標原點在第一字的字身原點，單位 pt。"""
    u = upem(face)
    scale = size_cm * CM / u
    items = []
    for i, ch in enumerate(text):
        items.append((glyph_contours(face, ch), i * adv_cm * CM))
    xs, ys = [], []
    for contours, dx in items:
        b = ink_bbox(contours, scale)
        xs += [b[0] + dx, b[2] + dx]
        ys += [b[1], b[3]]
    return items, scale, (min(xs), min(ys), max(xs), max(ys))


def build(out_path, company=COMPANY, number=NUMBER, palette=None):
    palette = palette or GROUNDS["單色黑K100"]
    ground = palette["ground"]
    recess = palette["recess"]
    trim_w, trim_h = PLATE_W * CM, PLATE_H * CM
    W = trim_w + 2 * MEDIA_PAD
    H = trim_h + 2 * MEDIA_PAD
    ox, oy = MEDIA_PAD, MEDIA_PAD              # 完成線左下角（PDF 座標）

    def X(cm):
        return ox + cm * CM

    def Y(cm):                                  # cm 由板面「上緣」往下量
        return oy + trim_h - cm * CM

    ops = []
    ops.append("q")
    ops.append("%.4f %.4f %.4f %.4f k" % ground)
    ops.append("%.4f %.4f %.4f %.4f re f" % (ox - BLEED, oy - BLEED,
                                             trim_w + 2 * BLEED, trim_h + 2 * BLEED))
    ops.append("Q")

    # 凹槽輪廓：只畫上緣與左緣。
    # 實體門牌的凹槽是靠上方光源打出陰影，下緣與右緣不會顯現；
    # 右緣又正好落在裁切線上，畫了會被裁掉。
    if DRAW_RECESS:
        ops.append("q")
        ops.append("%.4f %.4f %.4f %.4f K" % recess)
        ops.append("%.4f w 0 J" % (RECESS_LINE_W * CM))
        # 齊板邊那端延伸進出血，裁切偏移才不會露白
        r_end = X(RECESS_R) + (BLEED if RECESS_R >= PLATE_W else 0)
        ops.append("%.4f %.4f m %.4f %.4f l %.4f %.4f l S" % (
            X(RECESS_L), Y(RECESS_B), X(RECESS_L), Y(RECESS_T), r_end, Y(RECESS_T)))
        ops.append("Q")

    # 對角線：裁切在板面（含出血）內
    ops.append("q")
    ops.append("%.4f %.4f %.4f %.4f re W n" % (ox - BLEED, oy - BLEED,
                                               trim_w + 2 * BLEED, trim_h + 2 * BLEED))
    ops.append("%.4f %.4f %.4f %.4f K" % INK_SILVER)
    ops.append("%.4f w 2 J" % (DIAG_W * CM))
    ext = 1.0
    dx, dy = DIAG_TOP_X, -PLATE_H
    ln = (dx * dx + dy * dy) ** 0.5
    ux, uy = dx / ln, dy / ln
    ops.append("%.4f %.4f m %.4f %.4f l S" % (
        X(0 - ux * ext), Y(PLATE_H - uy * ext),
        X(DIAG_TOP_X + ux * ext), Y(0 + uy * ext)))
    ops.append("Q")

    # 495
    face_n = load_face(*FONT_NUM)
    items, scale, bb = layout_string(face_n, number, NUM_SIZE, NUM_ADV)
    dx0 = X(NUM_INK_L) - bb[0]
    dy0 = Y(NUM_INK_T) - bb[3]
    ops.append("q")
    ops.append("%.4f %.4f %.4f %.4f k" % INK_SILVER)
    for contours, off in items:
        ops.append(path_ops(contours, scale, dx0 + off, dy0))
    ops.append("f")
    ops.append("Q")

    # 公司名
    face_c = load_face(*FONT_CJK)
    items, scale, bb = layout_string(face_c, company, TXT_SIZE, TXT_ADV)
    cx = (RECESS_L + RECESS_R) / 2
    dx0 = X(cx) - (bb[0] + bb[2]) / 2
    dy0 = Y(TXT_CY) - (bb[1] + bb[3]) / 2
    ops.append("q")
    ops.append("%.4f %.4f %.4f %.4f k" % INK_SILVER)
    ops.append("%.4f %.4f %.4f %.4f K" % INK_SILVER)
    ops.append("%.4f w 1 J 1 j" % (TXT_BOLD * TXT_SIZE * CM))
    for contours, off in items:
        ops.append(path_ops(contours, scale, dx0 + off, dy0))
    ops.append("B" if TXT_BOLD > 0 else "f")
    ops.append("Q")

    # 裁切標記
    if DRAW_MARKS:
        ops.append("q")
        ops.append("%.4f %.4f %.4f %.4f k" % INK_MARK)
        half = MARK_W / 2
        for i, x in enumerate((ox, ox + trim_w)):
            s = -1 if i == 0 else 1
            for y in (oy, oy + trim_h):
                ops.append("%.4f %.4f %.4f %.4f re f" % (
                    min(x + s * (MARK_GAP + MARK_LEN), x + s * MARK_GAP),
                    y - half, MARK_LEN, MARK_W))
        for j, y in enumerate((oy, oy + trim_h)):
            s = -1 if j == 0 else 1
            for x in (ox, ox + trim_w):
                ops.append("%.4f %.4f %.4f %.4f re f" % (
                    x - half,
                    min(y + s * (MARK_GAP + MARK_LEN), y + s * MARK_GAP),
                    MARK_W, MARK_LEN))
        ops.append("Q")

    doc = fitz.open()
    page = doc.new_page(width=W, height=H)
    xref = doc.get_new_xref()
    doc.update_object(xref, "<<>>")
    doc.update_stream(xref, "\n".join(ops).encode("latin-1"))
    doc.xref_set_key(page.xref, "Contents", "%d 0 R" % xref)
    box = lambda a, b, c, d: "[%.4f %.4f %.4f %.4f]" % (a, b, c, d)
    doc.xref_set_key(page.xref, "MediaBox", box(0, 0, W, H))
    doc.xref_set_key(page.xref, "CropBox", box(0, 0, W, H))
    doc.xref_set_key(page.xref, "BleedBox", box(ox - BLEED, oy - BLEED,
                                                ox + trim_w + BLEED, oy + trim_h + BLEED))
    tb = box(ox, oy, ox + trim_w, oy + trim_h)
    doc.xref_set_key(page.xref, "TrimBox", tb)
    doc.xref_set_key(page.xref, "ArtBox", tb)
    doc.set_metadata({"title": "門牌 %s %s %gx%gcm" % (number, company, PLATE_W, PLATE_H),
                      "producer": "", "creator": ""})
    doc.save(out_path, garbage=3, deflate=True, clean=True)
    doc.close()


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    for label, palette in GROUNDS.items():
        name = "門牌_%s_%s_%gx%gcm_底色%s_無出血滿版.pdf" % (
            NUMBER, COMPANY, PLATE_W, PLATE_H, label)
        build(os.path.join(OUT_DIR, name), palette=palette)
        print("OK ->", name)
