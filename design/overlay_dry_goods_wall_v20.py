#!/usr/bin/env python3
"""志工牆 v20 = v9 空白模板(clean_base，標題白底/切斷散圖/殘影已清) 填入：
- 志工格：真人照片(志工-*.jpg/.png，頭高正規化＋去背白底)＋無照者用女性插畫，依姓名筆劃排序。
- 廚師排(牆頂5格，右錨點：廚師在右、廚助在左)：綠標籤重繪(角色)＋照片＋下方姓名。
- 標題帶：兩側食材圖示對稱填滿。
幾何常數對齊 overlay_dry_goods_wall_v9.py（唯一真實來源），全部乘上 S 以支援高解析輸出。

WALL_W 指定輸出寬度(px，預設母檔 3148)。成品板面 342×146cm：
  3148px=23dpi(太低) / 9696px=72dpi(送印用)。文字與裱框是程式畫的→放大真的變銳利，
  志工照片重新從原始檔取樣→也真的變清楚；只有水彩底圖是 LANCZOS 放大的。"""
import os, sys, glob
from PIL import Image, ImageDraw, ImageFont, ImageFilter

DESIGN = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DESIGN)
from cellphoto import cell_photo, contain_photo

BASE_W = 3148  # 母檔寬度，S 由此回推
OUT_W = int(os.environ.get("WALL_W", BASE_W))
DESK = "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/一樓乾貨牆-志工名單（可拆換）"
PHOTOS = "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/志工照片"
SRC = DESK + "/dry_goods_wall_v9_clean_base.png"
OUT = DESK + "/dry_goods_wall_v20_志工照片版" + (f"_{OUT_W}px" if OUT_W != BASE_W else "") + ".png"  # fmt: skip
NAMEFONT = "/System/Library/Fonts/STHeiti Medium.ttc"
CHEFFONT = "/System/Library/Fonts/ヒラギノ角ゴシック W7.ttc"
UNIHAN = os.environ["UNIHAN_TXT"]  # unicode.org UCD Unihan.zip 解出，13MB 不進 repo
DGREEN = (6, 104, 44)
GREEN = (108, 168, 74)
WHITE = (255, 255, 255)

NO_PHOTO = []  # 全員已有真人照片（張吳菊梅 2026-07-26 補齊）
FEMALE = set(NO_PHOTO)
# 白底棚拍 png 頭部偵測受寬髮/帽子影響，逐張微調頭高倍率(其餘預設 1.0)
SCALE_MUL = {
    "曾秀珠": 1.22,
    "陳玉欣": 1.12,
    "劉麗萍": 2.0,
    "馬秀芳": 1.15,
    "張吳菊梅": 1.12,
    "徐富祐": 1.15,
}
# 證件照(下巴以下素材少)者：頭往上移多露肩膀，避免浮頭。其餘預設 0.34
HEADROOM = {"張吳菊梅": 0.22}
# 原照片人像偏小/緊裁去背者：整張不裁 contain 塞進格子(目前無)
CONTAIN_NAMES = set()
# 廚師排(從右邊數)：順序右→左＝連科盛(主廚)/劉麗萍/李鳳君/楊佳靜/徐富祐
CHEF_FROM_RIGHT = [
    ("連科盛", "主廚", "廚師-連科盛.jpg"),
    ("劉麗萍", "廚師", "廚助-劉麗萍.png"),
    ("李鳳君", "廚師", "廚助-李鳳君.jpg"),
    ("楊佳靜", "廚師", "廚師-楊佳靜.jpg"),
    ("徐富祐", "廚師", "廚師-徐富祐.png"),
]
AV = {"F": (Image.open(DESIGN + "/assets/dry_goods_avatar_female_v2.png").convert("RGBA"), 3, 610, 505),
      "M": (Image.open(DESIGN + "/assets/dry_goods_avatar_male_v2.png").convert("RGBA"), 3, 700, 560)}  # fmt: skip
PASTELS = [(255, 240, 220), (226, 242, 234), (232, 238, 250), (250, 234, 238),
           (242, 238, 250), (255, 246, 224), (228, 244, 240), (246, 238, 230)]  # fmt: skip


def load_strokes():
    st = {}
    for line in open(UNIHAN):
        if line[0] == "U" and "kTotalStrokes" in line:
            p = line.split("\t")
            if len(p) >= 3 and p[1] == "kTotalStrokes":
                st[chr(int(p[0][2:], 16))] = int(p[2].split()[0])
    return st


def main():
    st = load_strokes()
    key = lambda n: ([st.get(c, 99) for c in n], n)
    files = {}
    for f in glob.glob(PHOTOS + "/志工-*.jpg") + glob.glob(PHOTOS + "/志工-*.png"):
        name = os.path.splitext(os.path.basename(f))[0][3:]
        if name not in files or f.endswith(".png"):  # 同名優先 png
            files[name] = f
    photo_names = sorted(files, key=key)
    noimg_names = sorted(NO_PHOTO, key=key)

    img = Image.open(SRC).convert("RGB")
    S = OUT_W / img.width  # 全部幾何常數的縮放倍率
    if S != 1:
        img = img.resize((OUT_W, round(img.height * S)), Image.LANCZOS)
    W, H = img.size

    # 標題帶：兩側食材圖示對稱填滿標題左右米色空白(不覆蓋標題文字 x1352~1795)
    ICONS = [
        Image.open(f"{DESIGN}/assets/dry_goods_ic_{n}.png").convert("RGBA")
        for n in ("box", "carrot", "tomato", "bowl", "heart")
    ]
    IH, ICY = 78 * S, 112 * S

    def place_icons(seq, x0, x1):
        import numpy as np

        for cx, ic in zip(np.linspace(x0 * S, x1 * S, len(seq)), seq):
            s = IH / ic.height
            r = ic.resize((max(1, round(ic.width * s)), round(IH)), Image.LANCZOS)
            img.paste(r, (int(cx - r.width / 2), int(ICY - r.height / 2)), r)

    place_icons(ICONS, 240, 1250)
    place_icons(ICONS[::-1], 1898, 2908)
    d = ImageDraw.Draw(img)

    MARGIN, GAP, TITLE_H = 60 * S, 14 * S, 110 * S
    A5 = 210 / 148
    CONTENT_W = W - 2 * MARGIN
    chef_top = MARGIN + TITLE_H + GAP
    vh = (H - 2 * MARGIN - TITLE_H - GAP - GAP - 4 * GAP) / 6.0
    vw = vh * A5
    VC = 10
    gw = VC * vw + (VC - 1) * GAP
    vl = MARGIN + (CONTENT_W - gw) / 2
    vol_top = chef_top + vh + GAP
    hh = vh * 0.16
    namef = ImageFont.truetype(NAMEFONT, int(hh * 0.88))
    cheff = ImageFont.truetype(CHEFFONT, int(vh * 0.27))

    def ctext(box, t, f, fill, bold=0):
        """bold＝stroke_width 假粗體。CJK 多筆劃字 stroke=1 就會黏連，維持 0 最好讀"""
        x0, y0, x1, y1 = box
        bb = d.textbbox((0, 0), t, font=f, stroke_width=bold)
        w, hgt = bb[2] - bb[0], bb[3] - bb[1]
        d.text(
            (x0 + ((x1 - x0) - w) / 2 - bb[0], y0 + ((y1 - y0) - hgt) / 2 - bb[1]),
            t,
            font=f,
            fill=fill,
            stroke_width=bold,
            stroke_fill=fill,
        )

    def frame_paste(pb, cell, mask, rad):
        """照片格立體效果：柔和投影(凸起) ＋ 內襯裱框(深棕外框＋米色內襯＋金色細線)。
        投影遮罩只在格子局部建立(高解析下全畫布遮罩+模糊會慢到不可用)。"""
        pb = [int(v) for v in pb]
        blur, pad = 5 * S, int(5 * S * 3) + 8
        ox, oy = round(3 * S), round(4 * S)
        sa = Image.new("L", (pb[2] - pb[0] + 2 * pad, pb[3] - pb[1] + 2 * pad), 0)
        ImageDraw.Draw(sa).rounded_rectangle(
            (pad + ox, pad + oy, sa.width - pad + ox, sa.height - pad + oy),
            radius=round(rad + 2 * S),
            fill=150,
        )
        sa = sa.filter(ImageFilter.GaussianBlur(blur))
        img.paste((40, 30, 20), (pb[0] - pad, pb[1] - pad), sa)  # 投影(就地)
        img.paste(cell, (pb[0], pb[1]), mask)  # 照片蓋回，投影只留在框外
        # 內襯裱框(往內)：米色內襯 → 深棕外框 → 金色細線
        inset = round(9 * S)
        d.rounded_rectangle(pb, radius=rad, outline=(253, 239, 202), width=round(8 * S))
        d.rounded_rectangle(pb, radius=rad, outline=(90, 62, 38), width=round(3 * S))
        d.rounded_rectangle(
            (pb[0] + inset, pb[1] + inset, pb[2] - inset, pb[3] - inset),
            radius=max(2, round(rad - 4 * S)),
            outline=(198, 150, 60),
            width=round(2 * S),
        )  # 金線

    def slot(i):
        r, c = divmod(i, VC)
        x0 = vl + c * (vw + GAP)
        y0 = vol_top + r * (vh + GAP)
        return x0, y0, x0 + vw, y0 + vh

    # ===== 志工格 =====
    idx = 0
    for name in photo_names:
        x0, y0, x1, y1 = slot(idx)
        ctext((x0, y0, x1, y0 + hh), name, namef, DGREEN)
        pb = (x0 + 8 * S, y0 + hh + 8 * S, x1 - 8 * S, y1 - 24 * S)
        pw, ph = int(pb[2] - pb[0]), int(pb[3] - pb[1])
        if name in CONTAIN_NAMES:
            cell, mask = contain_photo(files[name], pw, ph)
        else:
            cell, mask = cell_photo(
                files[name], pw, ph,
                scale_mul=SCALE_MUL.get(name, 1.0),
                headroom=HEADROOM.get(name, 0.34),
            )  # fmt: skip
        frame_paste(pb, cell, mask, round(9 * S))
        idx += 1

    for j, name in enumerate(noimg_names):
        x0, y0, x1, y1 = slot(idx)
        ctext((x0, y0, x1, y0 + hh), name, namef, DGREEN)
        pb = (x0 + 8 * S, y0 + hh + 8 * S, x1 - 8 * S, y1 - 24 * S)
        pw, ph = int(pb[2] - pb[0]), int(pb[3] - pb[1])
        cell = Image.new("RGB", (pw, ph), (255, 255, 255))
        av, a_ht, a_hh, a_cx = AV["F" if name in FEMALE else "M"]
        target_head = ph * 0.62
        s = target_head / a_hh
        a = av.resize(
            (max(1, round(av.width * s)), max(1, round(av.height * s))), Image.LANCZOS
        )
        cell.paste(a, (round(pw / 2 - a_cx * s), round(9 * S - a_ht * s)), a)
        m = Image.new("L", (pw, ph), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, pw, ph), radius=round(9 * S), fill=255)
        frame_paste(pb, cell, m, round(9 * S))
        idx += 1

    # ===== 廚師排(牆頂5格)：綠標籤=「角色-姓名」(上方)＋照片(原大小) =====
    n = 5
    cgap = (gw - n * vw) / (n - 1)
    hh_c = vh * 0.26
    # 廚師標籤較高→照片框較矮→頭部偏小。target_frac 補償，使頭部絕對大小＝志工
    vol_ph = vh - hh - 8 * S - 24 * S
    chef_ph = vh - hh_c - 8 * S - 24 * S
    CHEF_TF = 0.57 * vol_ph / chef_ph

    def fit_font(text, maxw, maxsize):
        sz = maxsize
        while (
            sz > 12 * S
            and d.textlength(text, font=ImageFont.truetype(CHEFFONT, sz)) > maxw
        ):
            sz -= 1
        return ImageFont.truetype(CHEFFONT, sz)

    for k, (name, label, fname) in enumerate(CHEF_FROM_RIGHT):
        i = (n - 1) - k  # 從右邊數
        x0 = vl + i * (vw + cgap)
        x1 = x0 + vw
        y0, y1 = chef_top, chef_top + vh
        d.rounded_rectangle((x0, y0, x1, y0 + hh_c), radius=round(12 * S), fill=GREEN)
        d.rectangle((x0, y0 + hh_c - 12 * S, x1, y0 + hh_c), fill=GREEN)
        txt = f"{label}-{name}"  # 例：廚師-連科盛 / 廚助-李鳳君
        ctext((x0, y0, x1, y0 + hh_c), txt, fit_font(txt, vw - 26 * S, cheff.size), WHITE)
        pb = (x0 + 8 * S, y0 + hh_c + 8 * S, x1 - 8 * S, y1 - 24 * S)  # 照片恢復原大小
        pw, ph = int(pb[2] - pb[0]), int(pb[3] - pb[1])
        if name in CONTAIN_NAMES:
            cell, mask = contain_photo(f"{PHOTOS}/{fname}", pw, ph, rad=round(10 * S))
        else:
            cell, mask = cell_photo(
                f"{PHOTOS}/{fname}", pw, ph, rad=round(10 * S),
                target_frac=CHEF_TF, headroom=0.15, scale_mul=SCALE_MUL.get(name, 1.0),
            )  # fmt: skip
        frame_paste(pb, cell, mask, round(10 * S))

    img.save(OUT)
    print(f"輸出 {W}x{H}px（S={S:.4f}）")
    print("志工格填", idx, "格(", len(photo_names), "照片+", len(noimg_names), "插畫)")
    print("廚師排:", "、".join(f"{lbl}={nm}" for nm, lbl, _ in CHEF_FROM_RIGHT))
    print("已存", OUT)


if __name__ == "__main__":
    main()
