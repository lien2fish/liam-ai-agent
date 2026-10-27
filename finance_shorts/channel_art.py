"""頻道大頭貼（800×800）與橫幅（2560×1440，安全區 1546×423 置中）。

配色沿用影片：深藍底＋金字。純圖形、不用照片——橫幅放不了 CC BY 要求的作者標註。
用法：python3 finance_shorts/channel_art.py → 試做成品/頻道_大頭貼.png、頻道_橫幅.png
"""

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from build import ROOT

HEAVY = "/Users/lien/Library/Fonts/SourceHanSansTC-Heavy.otf"
MED = "/Users/lien/Library/Fonts/SourceHanSansTC-Medium.otf"
NAVY0, NAVY1 = (7, 13, 26), (22, 41, 74)
GOLD = (226, 184, 92)
INK = (243, 241, 234)
OUT = ROOT / "試做成品"


def navy(w, h, cx, cy):
    """影片同款：深藍底、左上一團偏亮的光暈＋淡格線。"""
    bg = Image.new("RGB", (w, h), NAVY0)
    glow = Image.new("L", (w, h))
    r = max(w, h) * 0.55
    ImageDraw.Draw(glow).ellipse((cx - r, cy - r * 0.7, cx + r, cy + r * 0.7), fill=255)
    bg = Image.composite(Image.new("RGB", (w, h), NAVY1), bg, glow.filter(ImageFilter.GaussianBlur(r * 0.45)))
    d = ImageDraw.Draw(bg)
    step = w // 20
    for x in range(0, w, step):
        d.line((x, 0, x, h), fill=(26, 40, 64), width=1)
    for y in range(0, h, step):
        d.line((0, y, w, y), fill=(26, 40, 64), width=1)
    return bg


def centered(d, xy, text, font, fill, **kw):
    l, t, r, b = d.textbbox((0, 0), text, font=font, **kw)
    d.text((xy[0] - (l + r) / 2, xy[1] - (t + b) / 2), text, font=font, fill=fill, **kw)


def avatar():
    S = 800
    img = navy(S, S, S * 0.3, S * 0.25)
    d = ImageDraw.Draw(img)
    d.ellipse((40, 40, S - 40, S - 40), outline=GOLD, width=10)
    f = ImageFont.truetype(HEAVY, 196)
    for i, ch in enumerate("富可敵國"):
        centered(
            d, (S / 2 + (i % 2 - 0.5) * 212, S / 2 + (i // 2 - 0.5) * 220), ch, f, GOLD
        )
    img.save(OUT / "頻道_大頭貼.png")


def banner():
    W, H = 2560, 1440
    img = navy(W, H, W * 0.35, H * 0.3)
    glow = Image.new("L", (W, H))
    ImageDraw.Draw(glow).ellipse(
        (W / 2 - 900, H / 2 - 260, W / 2 + 900, H / 2 + 260), fill=90
    )
    img = Image.composite(
        Image.new("RGB", (W, H), (40, 60, 100)),
        img,
        glow.filter(ImageFilter.GaussianBlur(160)),
    )
    d = ImageDraw.Draw(img)
    cy = H / 2
    centered(d, (W / 2, cy - 95), "金錢怪物", ImageFont.truetype(HEAVY, 160), GOLD)
    centered(
        d,
        (W / 2, cy + 30),
        "一睜眼，就是錢的世界",
        ImageFont.truetype(MED, 58),
        INK,
    )
    tag = "看懂全世界的錢事"
    f = ImageFont.truetype(MED, 40)
    l, t, r, b = d.textbbox((0, 0), tag, font=f)
    w = r - l + 60
    d.rounded_rectangle(
        (W / 2 - w / 2, cy + 105, W / 2 + w / 2, cy + 105 + 66),
        35,
        outline=GOLD,
        width=3,
    )
    centered(d, (W / 2, cy + 138), tag, f, GOLD)
    img.save(OUT / "頻道_橫幅.png")
    # 檢查用：標出電腦／手機都看得到的安全區
    chk = img.copy()
    ImageDraw.Draw(chk).rectangle(
        ((W - 1546) / 2, (H - 423) / 2, (W + 1546) / 2, (H + 423) / 2),
        outline=(255, 0, 0),
        width=4,
    )
    chk.resize((1280, 720)).save(ROOT / "shared" / "banner_check.png")


if __name__ == "__main__":
    avatar()
    banner()
    print(f"  🖼  {OUT / '頻道_大頭貼.png'}\n  🖼  {OUT / '頻道_橫幅.png'}")
