"""YouTube 封面（1280×720）：實景照片＋左側暗化＋大字。

文字寫在 scripts.json 該集的 "thumbs"（可放多款），每款：
  {"bg": "hook1", "lines": [["美國房貸", "white", 120], ["7.4%", "yellow", 230], ...], "tag": "全世界又升息"}
數字跟片中一樣要對得到事實表——封面不另外查核，只能用片中已出現的數字。

用法：python3 finance_shorts/thumbnail.py mw-01-zc
"""

import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from build import ROOT, SCRIPTS

W, H = 1280, 720
FONT = "/Users/lien/Library/Fonts/SourceHanSansTC-Heavy.otf"
COLORS = {"white": (255, 255, 255), "yellow": (255, 212, 0), "red": (229, 57, 53)}


def cover(img):
    s = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x, y = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))


def make(spec, out):
    img = cover(Image.open(ROOT / "shared/bg" / f"{spec['bg']}.jpg").convert("RGB"))
    img = ImageEnhance.Brightness(img).enhance(0.75)
    shade = Image.new("L", (W, H))
    for x in range(W):
        shade.paste(int(max(0, 215 - x * 0.28)), (x, 0, x + 1, H))
    img = Image.composite(Image.new("RGB", (W, H)), img, shade)
    d = ImageDraw.Draw(img)
    y = spec.get("top", 70)
    for text, color, size in spec["lines"]:
        f = ImageFont.truetype(FONT, size)
        d.text(
            (60, y),
            text,
            font=f,
            fill=COLORS[color],
            stroke_width=max(4, size // 22),
            stroke_fill=(0, 0, 0),
        )
        y = d.textbbox((60, y), text, font=f, stroke_width=max(4, size // 22))[3] + 24
    if spec.get("tag"):
        f = ImageFont.truetype(FONT, 64)
        l, t, r, b = d.textbbox((0, 0), spec["tag"], font=f)
        d.rounded_rectangle(
            (52, y + 10, 52 + r - l + 40, y + 10 + b - t + 36), 14, fill=COLORS["red"]
        )
        d.text((72 - l, y + 28 - t), spec["tag"], font=f, fill=(255, 255, 255))
    img.save(out, quality=92)
    print(f"  🖼  {out}")


def main():
    eid = sys.argv[1]
    for i, spec in enumerate(SCRIPTS["episodes"][eid]["thumbs"]):
        make(spec, ROOT / eid / f"thumb_{chr(65 + i)}.jpg")


if __name__ == "__main__":
    main()
