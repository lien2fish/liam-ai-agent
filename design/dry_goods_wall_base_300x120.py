#!/usr/bin/env python3
"""志工牆底圖改尺寸 342×146cm → 300×120cm（比例 2.3423 → 2.5，不能等比放大）。

由 v20 的 clean_base(3148×1344) 重組成 3150×1260：
  頂部帶(標題＋加入志工群組標籤) 與 底部裝飾帶 原樣保留、不變形，
  中段只留左右側欄食材圖示——逐個平移(不縮放)吸收掉少掉的 84px，
  格子區整片洗成米色，改由 overlay_dry_goods_wall_v21.py 依新版面重畫。
原始 AI 底圖 dry_goods_wall_v5_final.png 已不存在，只能由 clean_base 逆推。
"""
import os
import qrcode
from PIL import Image, ImageDraw, ImageFont

DESK = "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/一樓乾貨牆-志工名單（可拆換）"
SRC = DESK + "/dry_goods_wall_v9_clean_base.png"
OUT = DESK + "/dry_goods_wall_v21_clean_base_300x120.png"
FONT = "/System/Library/Fonts/ヒラギノ角ゴシック W7.ttc"
CREAM = (253, 239, 201)
WHITE = (255, 255, 255)
DGREEN = (6, 104, 44)
DK = (60, 55, 45)

W, H = 3150, 1260  # 300×120cm，10.5px/cm
TOP_H = 220  # 頂部帶(含「加入志工群組」標籤下緣 214)
BOT_H = 60  # 底部裝飾帶
SRC_TOP, SRC_BOT = 220, 1284  # 來源的同兩條分界線

# 來源中段的側欄食材圖示（左 5 個、右 4 個；右側第 5 個原本就被右下 QR 面板蓋住）
LEFT_ICONS = [(447, 622), (660, 740), (783, 927), (972, 1134), (1175, 1284)]
RIGHT_ICONS = [(473, 621), (660, 740), (775, 948), (962, 1000)]
LEFT_X, RIGHT_X = (0, 240), (2900, 3148)
LINE_QR = (2880, 224, 3120, 464)  # LINE 群組 QR（連結未知，只能沿用原圖像素）


def main():
    src = Image.open(SRC).convert("RGB")
    img = Image.new("RGB", (W, H), CREAM)

    img.paste(
        src.crop((0, 0, src.width, SRC_TOP)).resize((W, TOP_H), Image.LANCZOS), (0, 0)
    )
    # 頂部帶取到 220 是為了保住「加入志工群組」標籤(下緣 214)，順帶夾進舊廚師卡綠標籤上緣
    ImageDraw.Draw(img).rectangle((280, 184, 2870, TOP_H), fill=CREAM)
    img.paste(
        src.crop((0, SRC_BOT, src.width, src.height)).resize((W, BOT_H), Image.LANCZOS),
        (0, H - BOT_H),
    )

    k = (H - BOT_H - TOP_H) / (SRC_BOT - SRC_TOP)
    for x0, x1 in (LEFT_X, RIGHT_X):
        for y0, y1 in LEFT_ICONS if x0 == 0 else RIGHT_ICONS:
            cy = TOP_H + ((y0 + y1) / 2 - SRC_TOP) * k
            img.paste(src.crop((x0, y0, x1, y1)), (x0, round(cy - (y1 - y0) / 2)))

    img.paste(src.crop(LINE_QR), (W - 28 - 240, LINE_QR[1]))
    draw_site_qr(img)
    img.save(OUT)
    print(f"已存 {OUT}（{W}×{H}px＝300×120cm）")


def draw_site_qr(img):
    """右下官網 QR 面板：沿用 overlay_dry_goods_wall_v9.py 的畫法與尺寸"""
    d = ImageDraw.Draw(img)
    QS, PAD, CAPH = 214, 18, 74
    PW, PH = QS + 2 * PAD, PAD + QS + CAPH
    x1, y1 = W - 30, H - 30
    x0, y0 = x1 - PW, y1 - PH
    d.rounded_rectangle(
        (x0, y0, x1, y1), radius=20, fill=WHITE, outline=DGREEN, width=4
    )
    q = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2
    )
    q.add_data("https://www.savefood.org.tw")
    q.make(fit=True)
    img.paste(
        q.make_image().convert("RGB").resize((QS, QS), Image.NEAREST),
        (x0 + PAD, y0 + PAD),
    )
    cx = x0 + PW / 2
    for y, t, f, fill in (
        (y0 + PAD + QS + 8, "惜食廚房官網", ImageFont.truetype(FONT, 34), DGREEN),
        (y0 + PAD + QS + 46, "savefood.org.tw", ImageFont.truetype(FONT, 26), DK),
    ):
        bb = d.textbbox((0, 0), t, font=f)
        d.text((cx - (bb[2] - bb[0]) / 2 - bb[0], y), t, font=f, fill=fill)


if __name__ == "__main__":
    main()
