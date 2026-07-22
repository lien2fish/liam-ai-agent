"""ChatGPT 插畫去背：暗色外框當屏障、四角 flood 去米底，只留最大連通區塊(去愛心/星星)。"""

import sys
import numpy as np
from PIL import Image, ImageFilter
from collections import deque


def cut(path, out, sw=760, barrier=185):
    im = Image.open(path).convert("RGB")
    W, H = im.size
    sh = int(H * sw / W)
    small = np.asarray(im.resize((sw, sh), Image.LANCZOS)).astype(np.int16)
    gray = small.mean(2)
    solid = gray >= barrier  # 非暗框

    # 1) 四角 flood 去外部米底（走 non-barrier）
    bg = np.zeros((sh, sw), bool)
    dq = deque()
    for y, x in [(0, 0), (0, sw - 1), (sh - 1, 0), (sh - 1, sw - 1)]:
        if solid[y, x]:
            bg[y, x] = True
            dq.append((y, x))
    for x in range(sw):
        for y in (0, sh - 1):
            if solid[y, x] and not bg[y, x]:
                bg[y, x] = True
                dq.append((y, x))
    for y in range(sh):
        for x in (0, sw - 1):
            if solid[y, x] and not bg[y, x]:
                bg[y, x] = True
                dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < sh and 0 <= nx < sw and solid[ny, nx] and not bg[ny, nx]:
                bg[ny, nx] = True
                dq.append((ny, nx))

    fg = ~bg  # 前景(含外框)=人物+愛心+星星

    # 2) 只留最大連通前景區塊(=人物)，去掉愛心/星星
    seen = np.zeros((sh, sw), bool)
    best = None
    best_n = 0
    for sy in range(sh):
        for sx in range(sw):
            if fg[sy, sx] and not seen[sy, sx]:
                comp = []
                seen[sy, sx] = True
                q = deque([(sy, sx)])
                while q:
                    y, x = q.popleft()
                    comp.append((y, x))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if (
                            0 <= ny < sh
                            and 0 <= nx < sw
                            and fg[ny, nx]
                            and not seen[ny, nx]
                        ):
                            seen[ny, nx] = True
                            q.append((ny, nx))
                if len(comp) > best_n:
                    best_n = len(comp)
                    best = comp
    mask = np.zeros((sh, sw), np.uint8)
    for y, x in best:
        mask[y, x] = 255

    am = (
        Image.fromarray(mask)
        .resize((W, H), Image.BILINEAR)
        .filter(ImageFilter.GaussianBlur(1.2))
    )
    r = im.convert("RGBA")
    r.putalpha(am)
    r = r.crop(r.getbbox())
    r.save(out)
    print(out, r.size)


if __name__ == "__main__":
    cut("gpt_woman.png", "gpt_woman_cut.png")
    cut("gpt_man.png", "gpt_man_cut.png")
    for n in ["gpt_woman_cut", "gpt_man_cut"]:
        im = Image.open(n + ".png")
        bg = Image.new("RGB", im.size, (255, 240, 222))
        bg.paste(im, (0, 0), im)
        bg.save(n + "_v.png")
