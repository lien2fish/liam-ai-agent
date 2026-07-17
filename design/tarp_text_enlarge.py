# -*- coding: utf-8 -*-
"""防水布文字放大：裁切→LANCZOS放大→羽化貼回。ops 以原圖座標描述。"""
from PIL import Image
import numpy as np

Image.MAX_IMAGE_PIXELS = None


def feather_mask(w, h, f):
    a = np.ones((h, w), dtype=np.float32)
    for i in range(f):
        v = (i + 1) / (f + 1)
        a[i, :] *= v
        a[h - 1 - i, :] *= v
        a[:, i] *= v
        a[:, w - 1 - i] *= v
    return Image.fromarray((a * 255).astype(np.uint8), "L")


def apply_ops(img, ops):
    src = img.copy()
    for op in ops:
        x0, y0, x1, y1 = op["box"]
        s = op["scale"]
        dy = op.get("dy", 0)
        dx = op.get("dx", 0)
        anchor = op.get("anchor", "center")
        f = op.get("feather", 12)
        crop = src.crop((x0, y0, x1, y1))
        w, h = crop.size
        nw, nh = round(w * s), round(h * s)
        big = crop.resize((nw, nh), Image.LANCZOS)
        if anchor == "center":
            px = round((x0 + x1) / 2 - nw / 2) + dx
        else:  # left：左緣固定
            px = x0 + dx
        py = round((y0 + y1) / 2 - nh / 2) + dy
        img.paste(big, (px, py), feather_mask(nw, nh, f))
    return img


FACE7_OPS = [
    # 左欄（照片底，羽化大）
    {"box": (101, 133, 912, 387), "scale": 1.18, "feather": 25},  # 志工招募
    {"box": (114, 383, 817, 447), "scale": 1.30, "dy": 20, "feather": 18},  # JOIN US
    {
        "box": (119, 477, 853, 576),
        "scale": 1.15,
        "dy": 5,
        "feather": 18,
    },  # 一起加入惜食志工團
    {"box": (115, 588, 675, 686), "scale": 1.15, "feather": 18},  # 傳遞溫暖與愛
    {"box": (118, 763, 907, 831), "scale": 1.35, "feather": 15},  # 每一次付出
    {"box": (119, 1084, 922, 1173), "scale": 1.25, "feather": 15},  # 洽詢專線
    # 中欄 5 列（圖示+標題+副標整列，左緣固定）
    {"box": (1645, 258, 2245, 387), "scale": 1.35, "anchor": "left", "feather": 8},
    {"box": (1645, 448, 2245, 577), "scale": 1.35, "anchor": "left", "feather": 8},
    {"box": (1645, 638, 2245, 767), "scale": 1.35, "anchor": "left", "feather": 8},
    {"box": (1645, 828, 2245, 957), "scale": 1.35, "anchor": "left", "feather": 8},
    {"box": (1645, 1019, 2245, 1147), "scale": 1.35, "anchor": "left", "feather": 8},
    # 右欄 3 步驟（左緣固定）
    {"box": (3275, 252, 4000, 331), "scale": 1.30, "anchor": "left", "feather": 8},
    {"box": (3275, 358, 4000, 437), "scale": 1.30, "anchor": "left", "feather": 8},
    {"box": (3275, 464, 4000, 543), "scale": 1.30, "anchor": "left", "feather": 8},
    # 白卡綠字
    {"box": (3575, 1000, 3871, 1080), "scale": 1.25, "feather": 12},  # 了解更多
    {"box": (4089, 1000, 4385, 1080), "scale": 1.25, "feather": 12},  # 立即報名
]

if __name__ == "__main__":
    im = Image.open("face7_full.png")
    out = apply_ops(im, FACE7_OPS)
    out.save("face7_enlarged.png")
    out.resize((1920, 520)).save("face7_enlarged_view.png")
    print("done", out.size)
