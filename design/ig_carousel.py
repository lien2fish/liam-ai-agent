#!/usr/bin/env python3
"""IG 收藏型輪播圖卡（1080×1350，4:5）。

用法：
  python3 design/ig_carousel.py design/ig_carousel/白帶魚看幾指.json

內容全部寫在 JSON：每張的畫面來源（影片＋秒數＋裁切框）與文字。
文字一律手動斷行（中文自動斷行容易切在詞中間），超出安全寬度直接報錯。
配色沿用鑫海產商務版海報（design/seafood_poster_rotary.py）。
輸出到 成品/IG輪播/<名稱>/，不進版控。
"""
import json
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1080, 1350
MARGIN = 88
SAFE_W = W - MARGIN * 2

DEEP = (8, 26, 44)
INK = (243, 238, 228)
INK_SOFT = (156, 180, 200)
GOLD = (198, 164, 98)
GOLD_DIM = (140, 116, 70)

FONT_DIR = os.path.expanduser("~/Library/Fonts")
HEAVY = os.path.join(FONT_DIR, "SourceHanSansTC-Heavy.otf")
BOLD = os.path.join(FONT_DIR, "SourceHanSansTC-Bold.otf")
REGULAR = os.path.join(FONT_DIR, "SourceHanSansTC-Regular.otf")
LATIN = "/System/Library/Fonts/Supplemental/Avenir Next.ttc"


def font(path, size, index=0):
    return ImageFont.truetype(path, size, index=index)


def grab_frame(video, t):
    path = video if os.path.isabs(video) else os.path.join(REPO, video)
    if not os.path.exists(path):
        raise FileNotFoundError(f"素材不存在：{path}")
    out = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
    r = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-ss",
            str(t),
            "-i",
            path,
            "-frames:v",
            "1",
            out,
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 or not os.path.getsize(out):
        raise RuntimeError(f"抽畫面失敗 {path} @ {t}s：{r.stderr}")
    im = Image.open(out).convert("RGB")
    os.remove(out)
    return im


def cover_fit(im, box, size):
    """box＝原始畫面上的裁切框 [x, y, w, h]；再等比放滿 size，多的從中間裁掉。"""
    if box:
        x, y, w, h = box
        im = im.crop((x, y, x + w, y + h))
    tw, th = size
    scale = max(tw / im.width, th / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    left = (im.width - tw) // 2
    top = (im.height - th) // 2
    return im.crop((left, top, left + tw, top + th))


def gradient(size, top_alpha, bottom_alpha, start=0.0, end=1.0):
    w, h = size
    g = Image.new("L", (1, h))
    for y in range(h):
        p = min(1.0, max(0.0, (y / h - start) / (end - start)))
        g.putpixel((0, y), round(top_alpha + (bottom_alpha - top_alpha) * p))
    return g.resize((w, h))


def text_w(draw, s, f):
    return draw.textlength(s, font=f)


def lines(draw, xy, text, f, fill, gap, name):
    x, y = xy
    for line in text.split("\n"):
        w = text_w(draw, line, f)
        if w > SAFE_W:
            raise ValueError(f"「{name}」這行超出安全寬度 {w:.0f}>{SAFE_W}px：{line}")
        draw.text((x, y), line, font=f, fill=fill)
        y += f.size + gap
    return y


def block_h(text, f, gap):
    n = len(text.split("\n"))
    return n * f.size + (n - 1) * gap


def footer(draw, handle, idx, total):
    y = H - 96
    draw.line([(MARGIN, y - 28), (W - MARGIN, y - 28)], fill=GOLD_DIM, width=2)
    draw.text((MARGIN, y), handle, font=font(REGULAR, 30), fill=INK_SOFT)
    page = f"{idx} / {total}"
    fp = font(LATIN, 30, index=0)
    draw.text((W - MARGIN - text_w(draw, page, fp), y + 2), page, font=fp, fill=GOLD)


def slide_cover(s, handle, idx, total):
    im = cover_fit(grab_frame(s["video"], s["t"]), s.get("crop"), (W, H))
    shade = Image.new("RGB", (W, H), DEEP)
    im = Image.composite(shade, im, gradient((W, H), 0, 240, start=0.3, end=0.62))
    d = ImageDraw.Draw(im)
    f_eye, f_title, f_sub = font(BOLD, 34), font(HEAVY, 92), font(REGULAR, 36)
    title_h = block_h(s["title"], f_title, 18)
    y = H - 190 - title_h - 150
    d.text((MARGIN, y), s["eyebrow"], font=f_eye, fill=GOLD)
    y = lines(d, (MARGIN, y + 70), s["title"], f_title, INK, 18, "title")
    lines(d, (MARGIN, y + 26), s["sub"], f_sub, INK_SOFT, 12, "sub")
    footer(d, handle, idx, total)
    return im


def slide_card(s, handle, idx, total):
    im = Image.new("RGB", (W, H), DEEP)
    d = ImageDraw.Draw(im)
    y = 110
    if s.get("video"):
        band_h = 560
        photo = cover_fit(
            grab_frame(s["video"], s["t"]), s.get("crop"), (W - MARGIN * 2, band_h)
        )
        im.paste(photo, (MARGIN, y))
        y += band_h + 64
    f_label, f_title, f_body, f_note = (
        font(BOLD, 36),
        font(HEAVY, 72),
        font(REGULAR, 40),
        font(REGULAR, 28),
    )
    if not s.get("video"):
        content_h = 74 + block_h(s["title"], f_title, 14)
        if s.get("body"):
            content_h += 30 + block_h(s["body"], f_body, 16)
        y = (H - 124 - content_h) // 2 - 40
    d.rectangle([MARGIN, y + 6, MARGIN + 8, y + 42], fill=GOLD)
    d.text((MARGIN + 28, y), s["label"], font=f_label, fill=GOLD)
    y = lines(d, (MARGIN, y + 74), s["title"], f_title, INK, 14, "title")
    if s.get("body"):
        y = lines(d, (MARGIN, y + 30), s["body"], f_body, INK_SOFT, 16, "body")
    if s.get("note"):
        lines(d, (MARGIN, H - 96 - 28 - 70), s["note"], f_note, GOLD_DIM, 8, "note")
    footer(d, handle, idx, total)
    return im


def slide_end(s, handle, idx, total):
    im = Image.new("RGB", (W, H), DEEP)
    d = ImageDraw.Draw(im)
    f_title, f_body = font(HEAVY, 96), font(REGULAR, 40)
    y = 380
    d.line([(MARGIN, y - 60), (MARGIN + 120, y - 60)], fill=GOLD, width=4)
    y = lines(d, (MARGIN, y), s["title"], f_title, INK, 20, "title")
    lines(d, (MARGIN, y + 50), s["body"], f_body, INK_SOFT, 18, "body")
    footer(d, handle, idx, total)
    return im


def slide_summary(s, handle, idx, total):
    im = Image.new("RGB", (W, H), DEEP)
    d = ImageDraw.Draw(im)
    y = 96
    if s.get("video"):
        band_h = 340
        photo = cover_fit(
            grab_frame(s["video"], s["t"]), s.get("crop"), (W - MARGIN * 2, band_h)
        )
        im.paste(photo, (MARGIN, y))
        y += band_h + 52
    f_label, f_term, f_value, f_note, f_cta = (
        font(BOLD, 34),
        font(BOLD, 40),
        font(REGULAR, 40),
        font(REGULAR, 26),
        font(HEAVY, 50),
    )
    d.rectangle([MARGIN, y + 6, MARGIN + 8, y + 40], fill=GOLD)
    d.text((MARGIN + 28, y), s["label"], font=f_label, fill=GOLD)
    y += 70
    term_w = s.get("term_w", 250)
    for term, value in s["rows"]:
        if text_w(d, term, f_term) > term_w - 20:
            raise ValueError(f"「rows」左欄太長：{term}")
        if text_w(d, value, f_value) > SAFE_W - term_w:
            raise ValueError(f"「rows」右欄太長：{value}")
        d.text((MARGIN, y + 20), term, font=f_term, fill=GOLD)
        d.text((MARGIN + term_w, y + 20), value, font=f_value, fill=INK)
        y += 88
        d.line([(MARGIN, y), (W - MARGIN, y)], fill=(34, 56, 78), width=2)
    if s.get("note"):
        lines(d, (MARGIN, y + 16), s["note"], f_note, GOLD_DIM, 6, "note")
    lines(d, (MARGIN, H - 124 - 44 - f_cta.size), s["cta"], f_cta, INK, 10, "cta")
    footer(d, handle, idx, total)
    return im


def render_story(s):
    """限時動態導流圖，1080×1920。上方約 250px、下方約 340px 會被 IG 介面蓋住，文字放中段。"""
    sw, sh = 1080, 1920
    im = cover_fit(grab_frame(s["video"], s["t"]), s.get("crop"), (sw, sh))
    shade = Image.new("RGB", (sw, sh), DEEP)
    im = Image.composite(shade, im, gradient((sw, sh), 0, 235, start=0.35, end=0.62))
    d = ImageDraw.Draw(im)
    f_eye, f_title, f_sub = font(BOLD, 40), font(HEAVY, 100), font(REGULAR, 44)
    y = 1040
    d.text((MARGIN, y), s["eyebrow"], font=f_eye, fill=GOLD)
    y = lines(d, (MARGIN, y + 76), s["title"], f_title, INK, 18, "story title")
    lines(d, (MARGIN, y + 34), s["sub"], f_sub, INK_SOFT, 14, "story sub")
    return im


RENDER = {
    "cover": slide_cover,
    "card": slide_card,
    "summary": slide_summary,
    "end": slide_end,
}


def main(cfg_path):
    cfg = json.load(open(cfg_path))
    out_dir = os.path.join(REPO, "成品", "IG輪播", cfg["name"])
    os.makedirs(out_dir, exist_ok=True)
    total = len(cfg["slides"])
    for i, s in enumerate(cfg["slides"], 1):
        im = RENDER[s["type"]](s, cfg["handle"], i, total)
        path = os.path.join(out_dir, f"{i:02d}.jpg")
        im.save(path, quality=92, subsampling=0)
        print(f"  {path}")
    if cfg.get("story"):
        story_path = os.path.join(out_dir, "限動.jpg")
        render_story(cfg["story"]).save(story_path, quality=92, subsampling=0)
        print(f"  {story_path}")
    if cfg.get("caption"):
        with open(os.path.join(out_dir, "文案.txt"), "w") as fh:
            fh.write(cfg["caption"])
    print(f"完成 {total} 張 → {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
