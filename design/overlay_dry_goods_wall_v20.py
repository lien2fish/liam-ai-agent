#!/usr/bin/env python3
"""志工牆 v20 = v9 空白模板(nobanner，標題白底已移除) 填入：
- 志工格：37 位真人照片(志工-*.jpg/.png，頭高統一正規化、肩膀以上)＋3 位無照者(張吳菊梅/楊佳靜/劉麗萍)用女性插畫，依姓名筆劃排序。
- 廚師排(牆頂5格)：從右邊數第1格=連科盛(標籤改「廚師」)、第2格=李鳳君廚助(標籤改「廚助」)，其餘3格留空。
幾何常數對齊 overlay_dry_goods_wall_v9.py（唯一真實來源）。"""
import os, sys, glob
from PIL import Image, ImageDraw, ImageFont

SP = os.path.dirname(os.path.abspath(__file__)).replace(
    "/Users/lien/Downloads/Liam AI agent/design",
    "/private/tmp/claude-501/-Users-lien-Downloads-Liam-AI-agent/ddbfd06c-c552-4b8c-9b01-8af25af2627a/scratchpad",
)
sys.path.insert(0, SP)
from cellphoto import cell_photo

DESIGN = os.path.dirname(os.path.abspath(__file__))
DESK = "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/一樓乾貨牆-志工名單（可拆換）"
PHOTOS = "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/志工照片"
SRC = DESK + "/dry_goods_wall_v9_clean_base.png"
OUT = DESK + "/dry_goods_wall_v20_志工照片版.png"
NAMEFONT = "/System/Library/Fonts/STHeiti Medium.ttc"
CHEFFONT = "/System/Library/Fonts/ヒラギノ角ゴシック W7.ttc"
UNIHAN = SP + "/Unihan_IRGSources.txt"
DGREEN = (6, 104, 44)
GREEN = (108, 168, 74)
WHITE = (255, 255, 255)

NO_PHOTO = "張吳菊梅 楊佳靜".split()
FEMALE = set(NO_PHOTO)
# 白底棚拍 png 頭部偵測受寬髮/帽子影響，逐張微調頭高倍率(其餘預設 1.0)
SCALE_MUL = {
    "曾秀珠": 1.22,
    "陳玉欣": 1.12,
    "劉麗萍": 2.0,
    "徐富祐": 1.6,
    "馬秀芳": 1.15,
}
# 廚師排(從右邊數)：廚師在右側先排、廚助接續在左。第1格連科盛、2徐富祐(皆廚師)、3李鳳君、4劉麗萍(皆廚助)，第5格留空
CHEF_FROM_RIGHT = [
    ("連科盛", "廚師", "廚師-連科盛.jpg"),
    ("徐富祐", "廚師", "廚師-徐富祐.png"),
    ("李鳳君", "廚助", "廚助-李鳳君.jpg"),
    ("劉麗萍", "廚助", "廚助-劉麗萍.png"),
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

    img = Image.open(SRC).convert("RGB").convert("RGBA")
    W, H = img.size

    # 標題帶：用兩側食材圖示對稱填滿標題左右米色空白(不覆蓋標題文字 x1352~1795)
    ICONS = [
        Image.open(f"{DESIGN}/assets/dry_goods_ic_{n}.png").convert("RGBA")
        for n in ("box", "carrot", "tomato", "bowl", "heart")
    ]
    IH, ICY = 78, 112

    def place_icons(seq, x0, x1):
        import numpy as np

        for cx, ic in zip(np.linspace(x0, x1, len(seq)), seq):
            s = IH / ic.height
            r = ic.resize((max(1, round(ic.width * s)), IH), Image.LANCZOS)
            img.alpha_composite(r, (int(cx - r.width / 2), int(ICY - r.height / 2)))

    place_icons(ICONS, 240, 1250)
    place_icons(ICONS[::-1], 1898, 2908)
    img = img.convert("RGB")
    d = ImageDraw.Draw(img)

    MARGIN, GAP, TITLE_H = 60, 14, 110
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

    def ctext(box, t, f, fill, bold=1):
        """bold＝stroke_width 假粗體(字型無更粗字重，用描邊加粗)"""
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
        pb = (x0 + 8, y0 + hh + 8, x1 - 8, y1 - 24)
        pw, ph = int(pb[2] - pb[0]), int(pb[3] - pb[1])
        cell, mask = cell_photo(files[name], pw, ph, scale_mul=SCALE_MUL.get(name, 1.0))
        img.paste(cell, (int(pb[0]), int(pb[1])), mask)
        idx += 1

    for j, name in enumerate(noimg_names):
        x0, y0, x1, y1 = slot(idx)
        ctext((x0, y0, x1, y0 + hh), name, namef, DGREEN)
        pb = (x0 + 8, y0 + hh + 8, x1 - 8, y1 - 24)
        pw, ph = int(pb[2] - pb[0]), int(pb[3] - pb[1])
        cell = Image.new("RGB", (pw, ph), (255, 255, 255))
        av, a_ht, a_hh, a_cx = AV["F" if name in FEMALE else "M"]
        target_head = ph * 0.62
        s = target_head / a_hh
        a = av.resize(
            (max(1, round(av.width * s)), max(1, round(av.height * s))), Image.LANCZOS
        )
        cell.paste(a, (round(pw / 2 - a_cx * s), round(9 - a_ht * s)), a)
        m = Image.new("L", (pw, ph), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, pw, ph), radius=9, fill=255)
        img.paste(cell, (int(pb[0]), int(pb[1])), m)
        idx += 1

    # ===== 廚師排(牆頂5格)：從右邊數第1、2格 =====
    n = 5
    cgap = (gw - n * vw) / (n - 1)
    hh_c = vh * 0.26
    for k, (name, label, fname) in enumerate(CHEF_FROM_RIGHT):
        i = (n - 1) - k  # 從右邊數
        x0 = vl + i * (vw + cgap)
        x1 = x0 + vw
        y0, y1 = chef_top, chef_top + vh
        d.rounded_rectangle((x0, y0, x1, y0 + hh_c), radius=12, fill=GREEN)
        d.rectangle((x0, y0 + hh_c - 12, x1, y0 + hh_c), fill=GREEN)
        ctext((x0, y0, x1, y0 + hh_c), label, cheff, WHITE)
        pb = (x0 + 8, y0 + hh_c + 8, x1 - 8, y1 - 24)
        pw, ph = int(pb[2] - pb[0]), int(pb[3] - pb[1])
        cell, mask = cell_photo(
            f"{PHOTOS}/{fname}", pw, ph, rad=10, scale_mul=SCALE_MUL.get(name, 1.0)
        )
        img.paste(cell, (int(pb[0]), int(pb[1])), mask)

    # 最左空格改標籤「廚助」(與廚助群一致)，不放照片、保留灰色佔位
    i = (n - 1) - len(CHEF_FROM_RIGHT)
    if i >= 0:
        x0 = vl + i * (vw + cgap)
        x1 = x0 + vw
        d.rounded_rectangle((x0, chef_top, x1, chef_top + hh_c), radius=12, fill=GREEN)
        d.rectangle((x0, chef_top + hh_c - 12, x1, chef_top + hh_c), fill=GREEN)
        ctext((x0, chef_top, x1, chef_top + hh_c), "廚助", cheff, WHITE)

    img.save(OUT)
    print("志工格填", idx, "格(", len(photo_names), "照片+", len(noimg_names), "插畫)")
    print("廚師排:", "、".join(f"{lbl}={nm}" for nm, lbl, _ in CHEF_FROM_RIGHT))
    print("已存", OUT)


if __name__ == "__main__":
    main()
