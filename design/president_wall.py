# -*- coding: utf-8 -*-
"""二樓會議廳外牆面 · 歷屆理事長 295×90cm 底版。

原稿是 2400×1792（比例 1.34）的水彩底圖，295×90 是 3.28 的長條，差太多不能直接拉伸，
改成「重組」：
  底色  逐列取原稿乾淨區的亮部中位數 → 純垂直漸層橫向填滿（拉伸原圖會把水滴／雲邊拖成橫線）
  左右  植物欄維持原比例貼回，內側羽化
  底部  麥穗叢切成兩種、交替鏡射重複，避免看出週期
  標題  原稿單行在長條版面會太小，拆兩行放大重繪；原稿舊標題先用底色補掉

PRES_DPI 預設 100（11614×3543px）。PRES_PREVIEW=4 產 1/4 草稿供快速試版。
名單／照片尚未提供，先出底版＋標題，名單區留空。
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

DESK = "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/二樓會議廳外牆面-歷屆理事長名單"
SRC = DESK + "/Gemini_Generated_Image_2rzluy2rzluy2rzl.png"
TITLEFONT = "/System/Library/Fonts/Supplemental/Songti.ttc"  # Songti TC Bold＝原稿明體
TITLE_IDX = 2
INK = (83, 92, 67)  # 原稿標題筆劃核心色

W_CM, H_CM = 295.0, 90.0
DPI = float(os.environ.get("PRES_DPI", 100))
DIV = int(os.environ.get("PRES_PREVIEW", 1))

SRC_W, SRC_H = 2400, 1792
CLEAN = (1300, 1780)  # 無裝飾且避開原稿標題(至x1243)的取樣帶
OLD_TITLE_Y = 300  # 左欄上方(原稿舊標題所在)整條用下方乾淨列向上外插補掉
LEFT_X1, RIGHT_X0 = 620, 1780  # 左右植物欄
WHEAT = [(500, 1120, 1430, SRC_H), (1000, 1420, 1430, SRC_H)]  # 兩種麥穗叢
SMOOTH = 34  # 底色垂直平滑半徑：不平滑的話原稿的雲邊會變成貫穿全寬的橫帶


def bg_column(a):
    """每列取乾淨帶中較亮的 60% 像素平均＝不含裝飾的底色，再垂直平滑成純漸層。"""
    col = light_mean(a[:, CLEAN[0] : CLEAN[1]])
    k = gauss(SMOOTH)
    pad = np.pad(col, ((3 * SMOOTH, 3 * SMOOTH), (0, 0)), mode="edge")
    return np.stack([np.convolve(pad[:, c], k, "valid") for c in range(3)], 1)


def gauss(sigma):
    k = np.exp(-((np.arange(-3 * sigma, 3 * sigma + 1) / sigma) ** 2) / 2)
    return k / k.sum()


def light_mean(block):
    """每列取較亮的 60% 像素平均＝該列不含裝飾的底色。"""
    b = block.astype(np.float32)
    keep = np.argsort(b.sum(2), 1)[:, int(0.4 * b.shape[1]) :]
    return np.take_along_axis(b, keep[..., None], 1).mean(1)


def feather(size, left=0, right=0, top=0):
    """邊緣線性淡出的遮罩，用來把貼回的區塊融進底色。"""
    w, h = size
    ax = np.ones(w, np.float32)
    if left:
        ax[:left] = np.linspace(0, 1, left)
    if right:
        ax[w - right :] = np.linspace(1, 0, right)
    m = np.tile(ax, (h, 1))
    if top:
        ay = np.ones(h, np.float32)
        ay[:top] = np.linspace(0, 1, top)
        m *= ay[:, None]
    return Image.fromarray((m * 255).astype(np.uint8))


def main():
    W = round(W_CM / 2.54 * DPI) // DIV
    H = round(H_CM / 2.54 * DPI) // DIV
    src = Image.open(SRC).convert("RGB")
    a = np.asarray(src)
    col = bg_column(a)
    s = H / SRC_H  # 原稿縮到目標高度的倍率

    # 原稿去掉舊標題：左欄上方整條用下方乾淨列向上外插。
    # 用全域底色補會與左欄自身的暈染有色差、變成看得見的方塊。
    b = a.astype(np.float32).copy()
    ref = b[OLD_TITLE_Y : OLD_TITLE_Y + 60, :LEFT_X1].mean(0)
    # 參考列會切過麥穗莖，需大幅平滑抹平；再與整體底色各半，避免補出一塊偏黃的色斑
    ref = np.stack([np.convolve(np.pad(ref[:, c], 900, "edge"), gauss(300), "valid")[:LEFT_X1] for c in range(3)], 1)  # fmt: skip
    ref = 0.5 * ref + 0.5 * col[OLD_TITLE_Y]
    w = np.ones(OLD_TITLE_Y, np.float32)
    w[-80:] = np.linspace(1, 0, 80)
    w = w[:, None, None]
    b[:OLD_TITLE_Y, :LEFT_X1] = w * ref + (1 - w) * b[:OLD_TITLE_Y, :LEFT_X1]
    clean_src = Image.fromarray(np.clip(b, 0, 255).astype(np.uint8))

    def sc(box):
        c = clean_src.crop(box)
        return c.resize((max(1, round(c.width * s)), max(1, round(c.height * s))), Image.LANCZOS)  # fmt: skip

    # 1. 底色：垂直漸層橫向填滿
    img = Image.fromarray(np.repeat(col[:, None], 8, 1).astype(np.uint8)).resize((W, H), Image.LANCZOS)  # fmt: skip

    # 2. 左右植物欄，內側羽化
    fade = round(260 * s)
    lp = sc((0, 0, LEFT_X1, SRC_H))
    img.paste(lp, (0, 0), feather(lp.size, right=fade))
    rp = sc((RIGHT_X0, 0, SRC_W, SRC_H))
    img.paste(rp, (W - rp.width, 0), feather(rp.size, left=fade))

    # 3. 底部麥穗：兩種叢交替＋鏡射，蓋滿中段
    # tile 背景正規化：扣掉原稿在該處的雲影換成新底色，只留麥穗本身，接縫才看不出來
    tiles = []
    for bx0, bx1, by0, by1 in WHEAT:
        blk = a[by0:by1, bx0:bx1].astype(np.float32)
        n = blk + (col[by0:by1] - light_mean(blk))[:, None]
        c = Image.fromarray(np.clip(n, 0, 255).astype(np.uint8))
        tiles.append(c.resize((round(c.width * s), round(c.height * s)), Image.LANCZOS))
    masks = [feather(t.size, round(140 * s), round(140 * s), round(260 * s)) for t in tiles]
    span0, span1 = lp.width - fade // 2, W - rp.width + fade // 2
    step = round(tiles[0].width * 0.82)
    n = max(1, round((span1 - span0) / step))
    for i, x in enumerate(np.linspace(span0, span1 - tiles[0].width, n)):
        k = i % 2
        t, m = tiles[k], masks[k]
        if (i // 2) % 2:
            t, m = t.transpose(Image.FLIP_LEFT_RIGHT), m.transpose(Image.FLIP_LEFT_RIGHT)  # fmt: skip
        img.paste(t, (int(x), H - t.height), m)

    # 4. 標題拆兩行重繪
    d = ImageDraw.Draw(img)
    tx = round(lp.width + 260 * s)
    s1, s2 = round(300 * s), round(430 * s)
    f1 = ImageFont.truetype(TITLEFONT, s1, index=TITLE_IDX)
    f2 = ImageFont.truetype(TITLEFONT, s2, index=TITLE_IDX)
    gap = round(150 * s)
    y = (H - (s1 + gap + s2)) / 2
    d.text((tx, y), "疼惜惜食", font=f1, fill=INK)
    d.text((tx, y + s1 + gap), "歷屆理事長", font=f2, fill=INK)

    nx0 = tx + round(d.textlength("歷屆理事長", font=f2)) + round(420 * s)
    nx1 = W - rp.width + fade
    out = DESK + f"/歷屆理事長_底版_295x90cm{'_預覽' if DIV > 1 else ''}.png"
    img.save(out)
    print(f"{W}x{H}px = {W_CM}×{H_CM}cm @{DPI/DIV:.0f}dpi")
    print(f"名單區 x {nx0}~{nx1}（寬 {nx1-nx0}px＝{(nx1-nx0)/W*W_CM:.0f}cm）")
    print("已存", out)
    return img, nx0, nx1


if __name__ == "__main__":
    main()
