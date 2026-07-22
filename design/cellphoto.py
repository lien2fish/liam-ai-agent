"""胸部以上完整頭像，比例不變：裁頭到胸的直式區塊 → 置中 contain 進橫式格、兩側補牆色。"""

import numpy as np
from PIL import Image, ImageDraw
import onnxruntime as ort

_sess = None
MODEL = "/private/tmp/claude-501/-Users-lien-Downloads-Liam-AI-agent/f6d67c10-25ad-4118-bdf4-859cb0b868df/scratchpad/u2net.onnx"


def _mask(im):
    global _sess
    if _sess is None:
        _sess = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])
    S = 320
    a = np.asarray(im.resize((S, S), Image.LANCZOS)).astype(np.float32) / 255.0
    a = (a - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    a = a.transpose(2, 0, 1)[None].astype(np.float32)
    m = _sess.run(None, {_sess.get_inputs()[0].name: a})[0][0, 0]
    m = (m - m.min()) / (m.max() - m.min() + 1e-8)
    return (
        np.asarray(
            Image.fromarray((m * 255).astype(np.uint8)).resize(im.size, Image.LANCZOS)
        )
        > 85
    )


def _wall_color(im):
    a = np.asarray(im)
    strip = np.concatenate(
        [a[: int(0.06 * im.height), :20], a[: int(0.06 * im.height), -20:]], 1
    )
    return tuple(int(x) for x in np.median(strip.reshape(-1, 3), 0))


def cell_photo(path, cw, ch, rad=9, target_frac=0.57, headroom=0.34):
    """頭高正規化：所有照片的頭統一縮放到 target_frac*格高，肩膀以上構圖。
    頭太大者自動縮小、格子留白用該張牆色補（無縫）。比例一律不變。"""
    im = Image.open(path).convert("RGB")
    W, H = im.size
    m = _mask(im)
    rows = np.where(m.any(1))[0]
    head_top = rows[0]
    band = m[head_top : head_top + int(0.18 * H)]
    cols = np.where(band.any(0))[0]
    cx = (cols[0] + cols[-1]) / 2
    head_w = cols[-1] - cols[0]
    head_h = head_w * 1.35
    wall = _wall_color(im)

    H_target = target_frac * ch
    s = H_target / head_h  # 縮放使頭高 = 目標
    im2 = im.resize((max(1, round(W * s)), max(1, round(H * s))), Image.LANCZOS)
    ht2, cx2 = head_top * s, cx * s
    left2 = cx2 - cw / 2  # 水平置中於臉
    top2 = ht2 - headroom * H_target  # 頭頂上方留白

    cell = Image.new("RGB", (cw, ch), wall)
    cell.paste(im2, (round(-left2), round(-top2)))  # 超出處自動裁、不足處留牆色
    mask = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, cw, ch), radius=rad, fill=255)
    return cell, mask


if __name__ == "__main__":
    from PIL import ImageFont
    import sys

    sys.path.insert(
        0,
        "/private/tmp/claude-501/-Users-lien-Downloads-Liam-AI-agent/f6d67c10-25ad-4118-bdf4-859cb0b868df/scratchpad",
    )
    from animals import draw_cat, draw_rabbit, animal_for, CAT_COLORS, RAB_COLORS

    P = "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/志工照片"
    SP = "/private/tmp/claude-501/-Users-lien-Downloads-Liam-AI-agent/f6d67c10-25ad-4118-bdf4-859cb0b868df/scratchpad"
    CW, CH = 227, 112
    tests = ["黃順圭", "蘇慧珠", "宋隆水", "何金玉", "郭黃豆", "翁巡"]
    pad = 26
    sheet = Image.new("RGB", (CW * 3, (CH + pad) * 4), "white")
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype("/System/Library/Fonts/STHeiti Medium.ttc", 20)
    # 照片樣張
    for i, n in enumerate(tests):
        c, mk = cell_photo(f"{P}/志工-{n}.jpg", CW, CH)
        x, y = (i % 3) * CW, (i // 3) * (CH + pad)
        sheet.paste(c, (x, y + pad), mk)
        d.text((x + 4, y + 2), n, font=f, fill="black")
    # 動物樣張（貓×3 兔×3）
    PAS = (255, 240, 220)
    demos = [("貓灰", draw_cat, CAT_COLORS[0]), ("貓橘", draw_cat, CAT_COLORS[1]), ("貓白", draw_cat, CAT_COLORS[2]),
             ("兔白", draw_rabbit, RAB_COLORS[0]), ("兔灰", draw_rabbit, RAB_COLORS[1]), ("兔米", draw_rabbit, RAB_COLORS[2])]  # fmt: skip
    for i, (lab, fn, col) in enumerate(demos):
        cell = Image.new("RGB", (CW, CH), PAS)
        a = fn(int(CH * 0.94), col)
        cell.paste(a, ((CW - a.width) // 2, (CH - a.height) // 2), a)
        mk = Image.new("L", (CW, CH), 0)
        ImageDraw.Draw(mk).rounded_rectangle((0, 0, CW, CH), radius=9, fill=255)
        x, y = (i % 3) * CW, (2 + i // 3) * (CH + pad)
        sheet.paste(cell, (x, y + pad), mk)
        d.text((x + 4, y + 2), lab, font=f, fill="black")
    sheet.save(f"{SP}/review_sheet.png")
    print("saved review_sheet.png")
