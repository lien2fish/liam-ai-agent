#!/usr/bin/env python3
"""把農業部魚類圖鑑的官方圖（白底＋紅色標註）處理成可用的去背 PNG。

用法：
  python3 design/moa_fish_cutout.py 原圖.png 輸出.png

官方圖都是同一種格式：純白背景、魚體側面、紅色箭頭與說明文字疊在上面。
這支做三件事：抹掉紅色標註、算出連續的 alpha、把邊緣沾到的白色扣掉。

⚠️ 不要用「二值遮罩→侵蝕→模糊」那套。那會把原圖的抗鋸齒毀掉，
邊緣變鋸齒狀，而且半透明像素裡的白色沒扣掉會留一圈白鑲邊。
"""
import sys

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

WHITE = 255.0
EDGE_K = 30.0  # 交界帶裡，離純白多遠算完全不透明


def find_annotations(rgb):
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    return (r > 90) & (r - g > 45) & (r - b > 45)


def inpaint(rgb, mask, rounds=150):
    work = rgb.copy()
    work[mask] = np.nan
    for _ in range(rounds):
        hole = np.isnan(work[:, :, 0])
        if not hole.any():
            break
        pad = np.pad(work, ((1, 1), (1, 1), (0, 0)), constant_values=np.nan)
        nb = np.stack([pad[:-2, 1:-1], pad[2:, 1:-1], pad[1:-1, :-2], pad[1:-1, 2:],
                       pad[:-2, :-2], pad[:-2, 2:], pad[2:, :-2], pad[2:, 2:]])
        with np.errstate(invalid="ignore"):
            avg = np.nanmean(nb, axis=0)
        work[hole] = avg[hole]
    work = np.nan_to_num(work, nan=WHITE)

    blur = np.asarray(
        Image.fromarray(work.clip(0, 255).astype("uint8")).filter(ImageFilter.GaussianBlur(1.2))
    ).astype(float)
    seam = ndimage.gaussian_filter(ndimage.binary_dilation(mask, np.ones((3, 3))).astype(float), 1.5)
    return work * (1 - seam[..., None]) + blur * seam[..., None]


def matte(rgb):
    """背景先用連通性找出來，只在交界那幾像素算連續過渡。

    不要單憑「離純白有多遠」判斷——魚鰭的膜本來就很淡，
    那樣會把鰭判成半透明，邊緣就會透出底色、看起來像白鑲邊。
    """
    n = WHITE - rgb.min(2)                      # 離純白的距離

    bg_seed = n < 6
    lab, cnt = ndimage.label(bg_seed)
    border = set(lab[0].tolist()) | set(lab[-1].tolist()) | set(lab[:, 0].tolist()) | set(lab[:, -1].tolist())
    border.discard(0)
    bg = np.isin(lab, list(border))

    fg = ndimage.binary_fill_holes(~bg)
    lab, cnt = ndimage.label(fg)
    if cnt == 0:
        raise SystemExit("找不到魚體")
    fg = ndimage.binary_fill_holes(lab == (np.argmax(ndimage.sum(fg, lab, range(1, cnt + 1))) + 1))

    band = ndimage.binary_dilation(bg, np.ones((3, 3)), 2) & ndimage.binary_dilation(fg, np.ones((3, 3)), 2)
    alpha = np.where(fg, 1.0, 0.0)
    alpha = np.where(band, np.clip(n / EDGE_K, 0, 1), alpha)
    smooth = ndimage.gaussian_filter(alpha, 0.6)
    alpha = np.where(band, smooth, alpha)
    return alpha.clip(0, 1), band


def decontaminate(rgb, alpha, band):
    """C_obs = a*C_fg + (1-a)*白。只在交界帶反解，把沾到的白色扣掉。"""
    a = np.maximum(alpha, 0.15)[..., None]
    fg = ((rgb - (1 - alpha[..., None]) * WHITE) / a).clip(0, 255)
    return np.where(band[..., None], fg, rgb)


def main(src, dst):
    rgb = np.asarray(Image.open(src).convert("RGB")).astype(float)
    clean = inpaint(rgb, ndimage.binary_dilation(find_annotations(rgb), np.ones((3, 3)), 3))
    alpha, band = matte(clean)
    fg = decontaminate(clean, alpha, band)

    out = Image.fromarray(np.dstack([fg, alpha * 255]).astype("uint8"))
    bbox = out.getchannel("A").point(lambda v: 255 if v > 6 else 0).getbbox()
    pad = 6
    out = out.crop((max(0, bbox[0] - pad), max(0, bbox[1] - pad),
                    min(out.width, bbox[2] + pad), min(out.height, bbox[3] + pad)))
    out.save(dst)
    print(f"{dst}  {out.size[0]}x{out.size[1]}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
