#!/usr/bin/env python3
"""志工牆 v15 = v9 空白模板填入 25 位照片(頭高統一正規化、肩膀以上、比例不變、頭大者縮小留白補牆色)
+ 15 位有名無照者用暖色插畫風卡通人物頭(依性別，肩膀以上)。皆依姓名筆劃排序，25 在前、15 接續(第26~40格)。"""
import os, sys, glob
from PIL import Image, ImageDraw, ImageFont

SP = "/private/tmp/claude-501/-Users-lien-Downloads-Liam-AI-agent/f6d67c10-25ad-4118-bdf4-859cb0b868df/scratchpad"
sys.path.insert(0, SP)
from cellphoto import cell_photo

DESIGN = os.path.dirname(os.path.abspath(__file__))
DESK = "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/一樓乾貨牆-志工名單（可拆換）"
PHOTOS = "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/志工照片"
SRC = DESK + "/dry_goods_wall_v9_nobanner.png"
OUT = DESK + "/dry_goods_wall_v19_志工照片版.png"
NAMEFONT = "/System/Library/Fonts/STHeiti Medium.ttc"
UNIHAN = SP + "/Unihan_IRGSources.txt"
DGREEN = (6, 104, 44)

# 2026-07-23：李鳳君/張德貴/陳玉欣/曾秀珠/黃秀卿/黃清枝 已補真實照片，從插畫清單移除
NO_PHOTO = "邱俊傑 江武成 丁淑美 張吳菊梅 連科盛 楊佳靜 劉麗萍 施秀桃 陳麗玉".split()
FEMALE = set(
    "丁淑美 李鳳君 施秀桃 陳玉欣 陳麗玉 張吳菊梅 曾秀珠 黃秀卿 楊佳靜 劉麗萍".split()
)
# ChatGPT 生成、去背後的男/女插畫頭像 ＋ 各自 (head_top, head_h, face_cx)
AV = {
    "F": (Image.open(DESIGN + "/assets/dry_goods_avatar_female_v2.png").convert("RGBA"), 3, 610, 505),
    "M": (Image.open(DESIGN + "/assets/dry_goods_avatar_male_v2.png").convert("RGBA"), 3, 700, 560),
}  # fmt: skip
# 人物格柔和粉彩底（循環）
PASTELS = [
    (255, 240, 220), (226, 242, 234), (232, 238, 250), (250, 234, 238),
    (242, 238, 250), (255, 246, 224), (228, 244, 240), (246, 238, 230),
]  # fmt: skip


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
    photo_names = sorted(
        [os.path.basename(f)[3:-4] for f in glob.glob(PHOTOS + "/志工-*.jpg")], key=key
    )
    noimg_names = sorted(NO_PHOTO, key=key)

    img = Image.open(SRC).convert("RGB")
    W, H = img.size
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
    namef = ImageFont.truetype(NAMEFONT, int(hh * 0.80))

    def ctext(box, t, f, fill):
        x0, y0, x1, y1 = box
        bb = d.textbbox((0, 0), t, font=f)
        w, h = bb[2] - bb[0], bb[3] - bb[1]
        d.text(
            (x0 + ((x1 - x0) - w) / 2 - bb[0], y0 + ((y1 - y0) - h) / 2 - bb[1]),
            t,
            font=f,
            fill=fill,
        )

    def slot(i):
        r, c = divmod(i, VC)
        x0 = vl + c * (vw + GAP)
        y0 = vol_top + r * (vh + GAP)
        return x0, y0, x0 + vw, y0 + vh

    idx = 0
    for name in photo_names:
        x0, y0, x1, y1 = slot(idx)
        ctext((x0, y0, x1, y0 + hh), name, namef, DGREEN)
        pb = (x0 + 8, y0 + hh + 8, x1 - 8, y1 - 24)
        pw, ph = int(pb[2] - pb[0]), int(pb[3] - pb[1])
        cell, mask = cell_photo(f"{PHOTOS}/志工-{name}.jpg", pw, ph)
        img.paste(cell, (int(pb[0]), int(pb[1])), mask)
        idx += 1

    for j, name in enumerate(noimg_names):
        x0, y0, x1, y1 = slot(idx)
        ctext((x0, y0, x1, y0 + hh), name, namef, DGREEN)
        pb = (x0 + 8, y0 + hh + 8, x1 - 8, y1 - 24)
        pw, ph = int(pb[2] - pb[0]), int(pb[3] - pb[1])
        cell = Image.new("RGB", (pw, ph), PASTELS[j % len(PASTELS)])
        av, a_ht, a_hh, a_cx = AV["F" if name in FEMALE else "M"]
        target_head = ph * 0.62  # 頭高對齊照片(≈0.57~0.62格高)
        s = target_head / a_hh
        a = av.resize(
            (max(1, round(av.width * s)), max(1, round(av.height * s))), Image.LANCZOS
        )
        cell.paste(
            a, (round(pw / 2 - a_cx * s), round(9 - a_ht * s)), a
        )  # 頭頂留白置頂、臉置中
        m = Image.new("L", (pw, ph), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, pw, ph), radius=9, fill=255)
        img.paste(cell, (int(pb[0]), int(pb[1])), m)
        idx += 1

    img.save(OUT)
    print("已填", idx, "格，存", OUT)
    print(
        "人物:",
        "、".join(f"{'♀' if n in FEMALE else '♂'}{n}" for n in noimg_names),
    )


if __name__ == "__main__":
    main()
