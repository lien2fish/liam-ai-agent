# -*- coding: utf-8 -*-
"""單面布「惜食台灣行動協會」— 照片改為兩行文字，一次產 A / B 兩版比稿。

A 版：左區完全沿用團體照版，右區原照片卡位置改放「惜食廚房」＋標語。
B 版：整面重排，協會名縮為上方小標，「惜食廚房」放大成主角。

母檔 1px = 1mm，已預先反向補償 tarp_face_pdf.py 的 enhance()，
故母檔看起來偏暗屬正常，審稿請看 _印刷模擬 那份。

用法: python3 design/tarp_solo_kitchen.py
"""
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

Image.MAX_IMAGE_PIXELS = None

BASE = "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出"
DIR = f"{BASE}/外牆防水布"
LOGO = f"{BASE}/二樓面外大logo/惜食台灣_logo_HQ.png"
ZHF = "/System/Library/Fonts/STHeiti Medium.ttc"
REF = f"{DIR}/防水布_惜食台灣行動協會_3.6x1.25m.png"  # 原始單面布，logo 在 y=317
REF_LOGO_Y = 317

W, H, BORDER = 3600, 1250, 26
WHITE = (255, 255, 255)

PDF_BRIGHTNESS, PDF_COLOR = 1.65, 1.83

PRINTED_GREEN = (7, 154, 63)  # 品牌綠 #079A3F
PRINTED_GOLD = (224, 165, 10)  # 深金黃 #E0A50A
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

LOGO_W, LOGO_H = 706, 616
LOGO_X = 287
LOGO_ALPHA_BBOX = (410, 574, 2925, 2765)

TITLE_SIZE, TITLE_X, TITLE_Y, LINE_PITCH = 300, 1090, 190, 370
SUB_SIZE, SUB_CX, SUB_Y = 138, 1682, 930

KITCHEN = "惜食廚房"
SLOGAN = "等一個便當 等一份疼惜"

# A 版右區：沿用原照片卡的橫向範圍，整塊垂直置中
A_LOGO_Y = 209
A_CX = 2957
A_KITCHEN_SIZE, A_SLOGAN_SIZE, A_GAP = 280, 112, 90

# B 版：三行左對齊 TITLE_X，第2、3行寬度配到相同 → 右留白 ≈ logo 左留白
B_LOGO_Y = 317
B_ORG_SIZE, B_KITCHEN_SIZE, B_SLOGAN_SIZE = 130, 560, 216
B_GAP1, B_GAP2 = 40, 48
B_ORG = "惜食台灣行動協會"


def ink_bbox(text, font):
    """CJK 的 textbbox 回傳 layout box 不是墨色框，改 render 後取 getbbox。"""
    pad = font.size * 2
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


def place_logo(canvas, y):
    logo = Image.open(LOGO).convert("RGBA").crop(LOGO_ALPHA_BBOX)
    logo = recolor_logo(logo).resize((LOGO_W, LOGO_H), Image.LANCZOS)
    canvas.paste(logo, (LOGO_X, y), logo)


def draw_ink(d, text, font, x, y, fill):
    """以墨色框左上角 (x, y) 為基準落字，回傳墨色框。"""
    bx0, by0, bx1, by1 = ink_bbox(text, font)
    d.text((x - bx0, y - by0), text, font=font, fill=fill)
    return x, y, x + (bx1 - bx0), y + (by1 - by0)


def draw_ink_center(d, text, font, cx, y, fill):
    bx0, by0, bx1, by1 = ink_bbox(text, font)
    return draw_ink(d, text, font, cx - (bx1 - bx0) // 2, y, fill)


def build_a():
    canvas = Image.new("RGB", (W, H), WHITE)
    ImageDraw.Draw(canvas).rectangle((0, 0, W - 1, H - 1), outline=GREEN, width=BORDER)
    place_logo(canvas, A_LOGO_Y)

    d = ImageDraw.Draw(canvas)
    title = ImageFont.truetype(ZHF, TITLE_SIZE)
    sub = ImageFont.truetype(ZHF, SUB_SIZE)

    # pen-x 只由第一行算出、第二行沿用 → 區塊視覺齊頭而非墨色齊頭
    bx0, by0, _, _ = ink_bbox("惜食台灣", title)
    pen_x, pen_y = TITLE_X - bx0, TITLE_Y - by0
    d.text((pen_x, pen_y), "惜食台灣", font=title, fill=GREEN)
    d.text((pen_x, pen_y + LINE_PITCH), "行動協會", font=title, fill=GREEN)
    draw_ink_center(d, "疼惜食物 ‧ 疼惜台灣", sub, SUB_CX, SUB_Y, ORANGE)

    kf = ImageFont.truetype(ZHF, A_KITCHEN_SIZE)
    sf = ImageFont.truetype(ZHF, A_SLOGAN_SIZE)
    kh = ink_bbox(KITCHEN, kf)[3] - ink_bbox(KITCHEN, kf)[1]
    sh = ink_bbox(SLOGAN, sf)[3] - ink_bbox(SLOGAN, sf)[1]
    top = (H - (kh + A_GAP + sh)) // 2
    boxes = [
        draw_ink_center(d, KITCHEN, kf, A_CX, top, GREEN),
        draw_ink_center(d, SLOGAN, sf, A_CX, top + kh + A_GAP, ORANGE),
    ]
    return canvas, boxes


def build_b():
    canvas = Image.new("RGB", (W, H), WHITE)
    ImageDraw.Draw(canvas).rectangle((0, 0, W - 1, H - 1), outline=GREEN, width=BORDER)
    place_logo(canvas, B_LOGO_Y)

    d = ImageDraw.Draw(canvas)
    of = ImageFont.truetype(ZHF, B_ORG_SIZE)
    kf = ImageFont.truetype(ZHF, B_KITCHEN_SIZE)
    sf = ImageFont.truetype(ZHF, B_SLOGAN_SIZE)
    oh = ink_bbox(B_ORG, of)[3] - ink_bbox(B_ORG, of)[1]
    kh = ink_bbox(KITCHEN, kf)[3] - ink_bbox(KITCHEN, kf)[1]
    sh = ink_bbox(SLOGAN, sf)[3] - ink_bbox(SLOGAN, sf)[1]

    top = (H - (oh + B_GAP1 + kh + B_GAP2 + sh)) // 2
    y2 = top + oh + B_GAP1
    y3 = y2 + kh + B_GAP2
    boxes = [
        draw_ink(d, B_ORG, of, TITLE_X, top, GREEN),
        draw_ink(d, KITCHEN, kf, TITLE_X, y2, GREEN),
        draw_ink(d, SLOGAN, sf, TITLE_X, y3, ORANGE),
    ]
    return canvas, boxes


def enhance_like_pdf(img):
    img = ImageEnhance.Brightness(img).enhance(PDF_BRIGHTNESS)
    img = ImageEnhance.Color(img).enhance(PDF_COLOR)
    return img.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=3))


def modal(a, x0, y0, x1, y1):
    r = a[y0:y1, x0:x1].reshape(-1, 3)
    r = r[r.sum(axis=1) < 720]
    c, n = np.unique(r, axis=0, return_counts=True)
    return tuple(c[n.argmax()])


def printed_core(a, s, box, color):
    """量筆劃核心的印出色。

    整塊取 modal 會量到抗鋸齒邊，且下游 UnsharpMask(radius=2) 會改寫離邊
    2~3px 內的像素——112px 的細筆劃幾乎整條都在影響範圍。侵蝕 5px 後
    只剩真正的核心，量到的才是這塊油墨實際印出的顏色。
    """
    ra, rs = a[box[1] : box[3], box[0] : box[2]], s[box[1] : box[3], box[0] : box[2]]
    pure = Image.fromarray(((ra == np.array(color)).all(axis=2) * 255).astype("uint8"))
    mask = np.asarray(pure.filter(ImageFilter.MinFilter(5))) > 0
    r = rs[mask].reshape(-1, 3)
    c, n = np.unique(r, axis=0, return_counts=True)
    return tuple(c[n.argmax()])


# 容差 12：細筆劃經銳利化後低通道會被推到 0（金黃的 B 由 10 → 0）。
# 真正要擋的是「母檔沒補償」那種偏差，那會差到 50 以上。
COLOR_TOL = 12


def near(a, b, tol):
    return max(abs(x - y) for x, y in zip(a, b)) <= tol


def common_checks(master, sim, logo_y):
    a = np.asarray(master).astype(int)
    s = np.asarray(sim).astype(int)
    ok = [
        ("尺寸 3600×1250", master.size == (W, H)),
        (f"外框色 = 補償綠 {GREEN}", tuple(a[0, 0]) == GREEN),
    ]
    sp = tuple(s[0, 0])
    ok.append(
        (
            "外框印出 #%02X%02X%02X (目標 #%02X%02X%02X)" % (sp + PRINTED_GREEN),
            near(sp, PRINTED_GREEN, 4),
        )
    )
    col = a[:, 1800]
    first = next(y for y in range(H) if tuple(col[y]) != GREEN)
    ok.append((f"外框寬 26px (實測 {first})", first == BORDER))

    # logo 與原始單面布母檔比對形狀。原檔是未補償的品牌綠，深綠會更早跨過
    # 固定門檻使遮罩虛胖，故各自依自身色域正規化混合比。0.932 是同色基準
    # （原母檔經多輪就地修改，抗鋸齒本來就對不齊）。
    ref = np.asarray(Image.open(REF).convert("RGB")).astype(int)
    new_logo = a[logo_y : logo_y + LOGO_H, LOGO_X : LOGO_X + LOGO_W]
    old_logo = ref[REF_LOGO_Y : REF_LOGO_Y + LOGO_H, LOGO_X : LOGO_X + LOGO_W]

    def ink_mask(region, color):
        return (765 - region.sum(axis=2)) / (765 - sum(color)) > 0.5

    nm, om = ink_mask(new_logo, GREEN), ink_mask(old_logo, LOGO_SRC_GREEN)
    iou = (nm & om).sum() / (nm | om).sum()
    ok.append((f"Logo 形狀對位 IoU {iou:.3f}", iou > 0.92))

    # 白底本來就是 255，整圖過曝率沒意義；只看文字/logo 有沒有被下游推爆。
    # 門檻取 400（實心綠 156、實心金黃 225 都遠低於它）以排除抗鋸齒淡邊——
    # 那圈淡邊本來就該被亮度 ×1.65 推成白，不是缺陷。
    ink = a.sum(axis=2) < 400
    blown = (s[ink] >= 250).all(axis=1).mean() * 100
    ok.append((f"墨色被推爆比例 {blown:.2f}%", blown < 1.0))
    return ok


def report(name, ok):
    print(f"\n【{name}】")
    print("{:<44} {}".format("檢查項目", "結果"))
    print("-" * 56)
    for item, passed in ok:
        print("{:<44} {}".format(item, "✅" if passed else "❌"))
    return all(p for _, p in ok)


def verify_a(master, sim, boxes):
    a = np.asarray(master).astype(int)
    s = np.asarray(sim).astype(int)
    ok = common_checks(master, sim, A_LOGO_Y)

    def ink(x0, y0, x1, y1):
        r = a[y0:y1, x0:x1]
        m = r.sum(axis=2) < 720
        ys, xs = np.where(m)
        return (x0 + xs.min(), y0 + ys.min(), x0 + xs.max(), y0 + ys.max())

    # 搜尋區右界避開右區新字，才量得到左區
    t1 = ink(1000, 150, 2330, 500)
    ok.append(
        (f"主標L1 墨色框 {t1}", abs(t1[0] - TITLE_X) <= 2 and abs(t1[1] - TITLE_Y) <= 2)
    )
    t2 = ink(1000, 520, 2330, 880)
    ok.append(
        (f"主標L2 行距 {t2[1] - t1[1]}px", abs((t2[1] - t1[1]) - LINE_PITCH) <= 8)
    )
    sb = ink(1000, 900, 2330, 1100)
    ok.append((f"副標 墨色框 {sb}", abs(sb[1] - SUB_Y) <= 2))
    ok.append(
        (f"副標水平置中 cx={(sb[0]+sb[2])//2}", abs((sb[0] + sb[2]) // 2 - SUB_CX) <= 3)
    )

    kb, sl = boxes
    ok.append(
        (f"惜食廚房 置中 cx={(kb[0]+kb[2])//2}", abs((kb[0] + kb[2]) // 2 - A_CX) <= 2)
    )
    ok.append(
        (f"標語 置中 cx={(sl[0]+sl[2])//2}", abs((sl[0] + sl[2]) // 2 - A_CX) <= 2)
    )
    ok.append((f"兩行行間距 {sl[1] - kb[3]}px", abs((sl[1] - kb[3]) - A_GAP) <= 2))
    ok.append(
        (
            f"新字塊垂直置中 上{kb[1]} 下{H - sl[3]}",
            abs(kb[1] - (H - sl[3])) <= 2,
        )
    )
    gap = min(kb[0], sl[0]) - max(t1[2], t2[2], sb[2])
    ok.append((f"與左區文字最小間距 {gap}px", gap >= 40))
    margin = W - BORDER - max(kb[2], sl[2])
    ok.append((f"右側留白 {margin}px", margin >= 30))
    ok.append(("惜食廚房 色 = 補償綠", modal(a, *kb) == GREEN))
    ok.append(("標語 色 = 補償金黃", modal(a, *sl) == ORANGE))
    kp = printed_core(a, s, kb, GREEN)
    ok.append(
        (
            "惜食廚房印出 #%02X%02X%02X (目標 #%02X%02X%02X)" % (kp + PRINTED_GREEN),
            near(kp, PRINTED_GREEN, COLOR_TOL),
        )
    )
    lp = printed_core(a, s, sl, ORANGE)
    ok.append(
        (
            "標語印出 #%02X%02X%02X (目標 #%02X%02X%02X)" % (lp + PRINTED_GOLD),
            near(lp, PRINTED_GOLD, COLOR_TOL),
        )
    )
    return report("A 版｜左區不動，右區兩行字", ok)


def verify_b(master, sim, boxes):
    a = np.asarray(master).astype(int)
    s = np.asarray(sim).astype(int)
    ok = common_checks(master, sim, B_LOGO_Y)

    org, kb, sl = boxes
    for label, b in (("協會名", org), ("惜食廚房", kb), ("標語", sl)):
        ok.append((f"{label} 左對齊 x={b[0]}", b[0] == TITLE_X))
    ok.append((f"協會名→惜食廚房 行距 {kb[1] - org[3]}px", (kb[1] - org[3]) == B_GAP1))
    ok.append((f"惜食廚房→標語 行距 {sl[1] - kb[3]}px", (sl[1] - kb[3]) == B_GAP2))
    ok.append(
        (f"整塊垂直置中 上{org[1]} 下{H - sl[3]}", abs(org[1] - (H - sl[3])) <= 2)
    )
    ok.append(
        (
            f"惜食廚房與標語等寬 {kb[2]-kb[0]} / {sl[2]-sl[0]}",
            abs((kb[2] - kb[0]) - (sl[2] - sl[0])) <= 25,
        )
    )
    margin = W - BORDER - max(org[2], kb[2], sl[2])
    ok.append((f"右側留白 {margin}px (logo 左留白 {LOGO_X})", margin >= 30))
    ok.append(
        (
            f"與 logo 最小間距 {TITLE_X - (LOGO_X + LOGO_W)}px",
            TITLE_X > LOGO_X + LOGO_W + 40,
        )
    )
    ok.append(("協會名 色 = 補償綠", modal(a, *org) == GREEN))
    ok.append(("惜食廚房 色 = 補償綠", modal(a, *kb) == GREEN))
    ok.append(("標語 色 = 補償金黃", modal(a, *sl) == ORANGE))
    kp = printed_core(a, s, kb, GREEN)
    ok.append(
        (
            "惜食廚房印出 #%02X%02X%02X (目標 #%02X%02X%02X)" % (kp + PRINTED_GREEN),
            near(kp, PRINTED_GREEN, COLOR_TOL),
        )
    )
    lp = printed_core(a, s, sl, ORANGE)
    ok.append(
        (
            "標語印出 #%02X%02X%02X (目標 #%02X%02X%02X)" % (lp + PRINTED_GOLD),
            near(lp, PRINTED_GOLD, COLOR_TOL),
        )
    )
    return report("B 版｜整面重排，惜食廚房當主角", ok)


def emit(tag, master):
    out = f"{DIR}/防水布_惜食台灣行動協會_惜食廚房版{tag}_3.6x1.25m.png"
    master.save(out)
    sim = enhance_like_pdf(master)
    sim.save(f"{DIR}/預覽_惜食廚房版{tag}_印刷模擬.png")
    sim.resize((1200, 417), Image.LANCZOS).save(f"{DIR}/預覽_惜食廚房版{tag}_縮圖.png")
    print(f"✅ 母檔 {out}")
    return sim


def main():
    ma, ba = build_a()
    sa = emit("A", ma)
    mb, bb = build_b()
    sb = emit("B", mb)

    ok = verify_a(ma, sa, ba)
    ok = verify_b(mb, sb, bb) and ok
    print("\n" + ("全部通過" if ok else "⚠️ 有項目未通過，見上表"))


if __name__ == "__main__":
    main()
