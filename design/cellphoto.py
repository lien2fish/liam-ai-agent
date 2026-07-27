"""胸部以上完整頭像，比例不變：u2net 去背合成白底 → 頭高正規化 → 置中塞進橫式格。"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import onnxruntime as ort

_sess = None
# u2net.onnx 168MB 不進 repo，放 scratchpad 或任意路徑後用 U2NET_ONNX 指定
MODEL = os.environ.get("U2NET_ONNX", os.path.expanduser("~/.cache/u2net.onnx"))


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


WHITE = (255, 255, 255)
FEATHER_DIV = 200  # 羽化半徑＝短邊/此值，相對量才能跨解析度一致


def _on_white(im, m):
    """去背合成白底：解決「白底png vs 灰底jpg」不一致，邊緣羽化避免硬切。"""
    al = Image.fromarray((m * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(min(im.size) / FEATHER_DIV)
    )
    return Image.composite(im, Image.new("RGB", im.size, WHITE), al)


def cell_photo(path, cw, ch, rad=9, target_frac=0.57, headroom=0.34, scale_mul=1.0):
    """頭高正規化：所有照片的頭統一縮放到 target_frac*格高，肩膀以上構圖。
    去背合成白底，頭太大者自動縮小、格子留白補白。比例一律不變。
    scale_mul＝逐張微調（寬髮/帽子會讓頭寬估測失準）。"""
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
    im = _on_white(im, m)

    H_target = target_frac * ch
    s = H_target / head_h * scale_mul  # 縮放使頭高 = 目標
    im2 = im.resize((max(1, round(W * s)), max(1, round(H * s))), Image.LANCZOS)
    ht2, cx2 = head_top * s, cx * s
    left2 = cx2 - cw / 2  # 水平置中於臉
    top2 = ht2 - headroom * H_target  # 頭頂上方留白

    cell = Image.new("RGB", (cw, ch), WHITE)
    cell.paste(im2, (round(-left2), round(-top2)))  # 超出處自動裁、不足處留白
    mask = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, cw, ch), radius=rad, fill=255)
    return cell, mask


def contain_photo(path, cw, ch, rad=9):
    """整張不裁、等比縮到塞得進格子，去背白底置中補邊。供原圖人像已緊裁者用。
    注意：不吃 target_frac，頭會比正規化的小。"""
    im = Image.open(path).convert("RGB")
    im = _on_white(im, _mask(im))
    s = min(cw / im.width, ch / im.height)
    im2 = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)  # fmt: skip
    cell = Image.new("RGB", (cw, ch), WHITE)
    cell.paste(im2, ((cw - im2.width) // 2, (ch - im2.height) // 2))
    mask = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, cw, ch), radius=rad, fill=255)
    return cell, mask
