"""惜食便當捐款卡右下角愛心 — 單獨輸出版，內容改為 單位／簽名／日期 填寫欄。

來源＝成品點陣圖 惜食便當捐款卡_印刷40cm.png（無原始向量），
做法：抽出愛心輪廓 alpha → 放大 → 重繪白色填寫欄。

輸出 RGB 透明 PNG／預覽／.ai，以及送印用 DeviceCMYK PDF。

用法：python3 design/bento_heart_fields.py [--width-cm 30] [--dpi 300] [--bleed-mm 0]
"""

import argparse
import os
import zlib

import numpy as np
from PIL import Image, ImageCms, ImageDraw, ImageFilter, ImageFont

BASE = "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/惜食便當捐款卡（已完成）"
SRC = os.path.join(BASE, "惜食便當捐款卡_印刷40cm.png")
FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
ICC = "/System/Library/ColorSync/Profiles/Generic CMYK Profile.icc"

HEART_RGB = (242, 72, 50)
CARD_BG = (252, 249, 242)
FIELDS = ["單位", "簽名", "日期"]
ROW_FRACS = (0.30, 0.46, 0.62)
SIDE_MARGIN_FRAC = 0.045  # 每行文字塊距愛心邊緣
FONT_FRAC = 0.068  # 字面高 / 愛心寬
GAP_FRAC = 0.022  # 冒號到底線的間距
RULE_FRAC = 0.0035  # 底線粗細
CLEFT_FIT_ROWS = 30  # 外推凹口尖點時取樣的列數


def runs(row):
    idx = np.nonzero(row)[0]
    if not len(idx):
        return []
    breaks = np.nonzero(np.diff(idx) > 1)[0]
    out, start = [], idx[0]
    for i in breaks:
        out.append((start, idx[i]))
        start = idx[i + 1]
    out.append((start, idx[-1]))
    return out


def gaps(row):
    idx = np.nonzero(row)[0]
    breaks = np.nonzero(np.diff(idx) > 1)[0]
    return [(idx[i] + 1, idx[i + 1] - 1) for i in breaks]


def heart_alpha():
    """回傳愛心的去背 alpha（來源解析度）。

    上緣凹口下半段被白色線稿愛心蓋住、判不出來，改用凹口兩側邊緣線性外推到交點補回，
    否則實心化會把凹口切成平底。
    """
    rgb = np.array(Image.open(SRC).convert("RGB")).astype(int)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    red = (r > 180) & (g < 110) & (b < 90)
    ys, xs = np.nonzero(red)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1

    red = red[y0:y1, x0:x1]
    g = g[y0:y1, x0:x1]
    h, w = red.shape
    cx = (w - 1) / 2.0

    two_lobe = [
        y
        for y in range(h)
        for seg in [runs(red[y])]
        if len(seg) == 2 and seg[0][1] < cx < seg[1][0]
    ]
    y_last = max(two_lobe)  # 再往下就被白色線稿干擾，判讀不可信

    cleft = {}
    for y in range(y_last + 1):
        # 不強求該列只有兩段：邊緣鋸齒偶爾會多切出一段，漏判會讓整列填成紅槓
        for lo, hi in gaps(red[y]):
            if lo <= cx <= hi:
                cleft[y] = (lo, hi)
                break
    fit = sorted(cleft)[-CLEFT_FIT_ROWS:]
    ls, rs = np.array([cleft[y][0] for y in fit]), np.array([cleft[y][1] for y in fit])
    (la, lb), (ra, rb) = np.polyfit(fit, ls, 1), np.polyfit(fit, rs, 1)
    y_tip = int(round((rb - lb) / (la - ra)))
    for y in range(y_last + 1, y_tip + 1):
        lo, hi = int(round(la * y + lb)), int(round(ra * y + rb))
        if lo <= hi:
            cleft[y] = (lo, hi)

    sil = np.zeros((h, w), bool)
    for y in range(h):
        seg = runs(red[y])
        if not seg:
            continue
        sil[y, seg[0][0] : seg[-1][1] + 1] = True
        if y in cleft:
            lo, hi = cleft[y]
            sil[y, lo : hi + 1] = False

    # 外緣抗鋸齒沿用原圖真值（奶白底 G=249 → 紅 G=72 的覆蓋率），
    # 凹口內是白色線稿故 edge=0，不會誤填。
    edge = np.clip((CARD_BG[1] - g) / float(CARD_BG[1] - HEART_RGB[1]), 0, 1)
    silimg = Image.fromarray((sil * 255).astype(np.uint8))
    outer = np.array(silimg.filter(ImageFilter.MaxFilter(5))) > 0
    soft = np.array(silimg.filter(ImageFilter.GaussianBlur(0.7))) / 255.0

    alpha = np.maximum(np.where(outer, edge, 0.0), soft)
    print(f"凹口：可辨識到 y={y_last}，外推尖點 y={y_tip} x={la*y_tip+lb:.0f}")
    return (alpha * 255).astype(np.uint8)


def steepen(alpha_img, lo=0.25, hi=0.75):
    a = np.array(alpha_img).astype(np.float32) / 255.0
    a = np.clip((a - lo) / (hi - lo), 0, 1)
    return Image.fromarray((a * 255).astype(np.uint8))


def ink_metrics(text, font):
    """CJK 的 textbbox 回傳 layout box 不是墨色框，改實際 render 取 getbbox。"""
    pad = font.size
    tmp = Image.new("L", (len(text) * font.size * 2 + 2 * pad, font.size * 3), 0)
    ImageDraw.Draw(tmp).text((pad, pad), text, font=font, fill=255)
    l, t, r, b = tmp.getbbox()
    return l - pad, t - pad, r - l, b - t


def heart_cmyk():
    """愛心紅的 CMYK 值。走 ICC 轉一次就好，不要每個像素各轉一次。"""
    patch = Image.new("RGB", (8, 8), HEART_RGB)
    out = ImageCms.profileToProfile(
        patch,
        ImageCms.createProfile("sRGB"),
        ImageCms.getOpenProfile(ICC),
        renderingIntent=ImageCms.Intent.PERCEPTUAL,
        outputMode="CMYK",
    )
    return out.getpixel((4, 4))


def cmyk_to_srgb(cmyk, w, h):
    patch = Image.new("CMYK", (w, h), tuple(int(v) for v in cmyk))
    return ImageCms.profileToProfile(
        patch,
        ImageCms.getOpenProfile(ICC),
        ImageCms.createProfile("sRGB"),
        renderingIntent=ImageCms.Intent.PERCEPTUAL,
        outputMode="RGB",
    )


def cmyk_pdf(shape_alpha, ink, dpi, bleed_mm, out_pdf):
    """DeviceCMYK + FlateDecode 自組 PDF，透明走 SMask。

    白字＝不上墨（露出紙白），故直接以覆蓋率扣墨，不把整張圖丟進 ICC——
    那會讓純白被推成 1~2% 的髒墨。
    """
    base = heart_cmyk()
    a = shape_alpha
    bleed_px = int(round(bleed_mm / 25.4 * dpi))
    if bleed_px:
        a = a.filter(ImageFilter.MaxFilter(bleed_px * 2 + 1))

    keep = 1.0 - np.array(ink, dtype=np.float32) / 255.0
    W, H = ink.size
    planes = [np.clip(v * keep + 0.5, 0, 255).astype(np.uint8) for v in base]
    raw = np.stack(planes, axis=-1).tobytes()

    img = zlib.compress(raw, 6)
    smask = zlib.compress(np.array(a).tobytes(), 6)
    w_pt, h_pt = W / dpi * 72.0, H / dpi * 72.0
    content = f"q {w_pt:.2f} 0 0 {h_pt:.2f} 0 0 cm /Im0 Do Q".encode()

    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w_pt:.2f} {h_pt:.2f}] "
            f"/TrimBox [0 0 {w_pt:.2f} {h_pt:.2f}] "
            f"/Resources << /XObject << /Im0 5 0 R >> >> /Contents 4 0 R >>"
        ).encode(),
        4: f"<< /Length {len(content)} >>\nstream\n".encode()
        + content
        + b"\nendstream",
        5: (
            f"<< /Type /XObject /Subtype /Image /Width {W} /Height {H} "
            f"/ColorSpace /DeviceCMYK /BitsPerComponent 8 /Filter /FlateDecode "
            f"/SMask 6 0 R /Length {len(img)} >>\nstream\n"
        ).encode()
        + img
        + b"\nendstream",
        6: (
            f"<< /Type /XObject /Subtype /Image /Width {W} /Height {H} "
            f"/ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /FlateDecode "
            f"/Length {len(smask)} >>\nstream\n"
        ).encode()
        + smask
        + b"\nendstream",
    }

    with open(out_pdf, "wb") as f:
        f.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = {}
        for n in sorted(objs):
            offsets[n] = f.tell()
            f.write(f"{n} 0 obj\n".encode() + objs[n] + b"\nendobj\n")
        xref = f.tell()
        f.write(f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode())
        for n in sorted(objs):
            f.write(f"{offsets[n]:010d} 00000 n \n".encode())
        f.write(
            f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n".encode()
        )
    pct = [round(v / 255 * 100, 1) for v in base]
    print(
        f"CMYK 底色 {base} = C{pct[0]} M{pct[1]} Y{pct[2]} K{pct[3]}％，出血 {bleed_mm:g}mm"
    )


def build(width_cm, dpi, outdir, bleed_mm=0.0):
    a_src = Image.fromarray(heart_alpha())
    target_w = int(round(width_cm / 2.54 * dpi))
    target_h = int(round(target_w * a_src.height / a_src.width))
    alpha = steepen(a_src.resize((target_w, target_h), Image.LANCZOS))

    m = np.array(alpha) > 128
    ink = Image.new("L", (target_w, target_h), 0)  # 白色文字的覆蓋率，CMYK 端當作留白
    draw = ImageDraw.Draw(ink)

    font = ImageFont.truetype(FONT, int(target_w * FONT_FRAC))
    gap = int(target_w * GAP_FRAC)
    rule = max(2, int(target_w * RULE_FRAC))
    margin = int(target_w * SIDE_MARGIN_FRAC)

    rows = []
    avail = []
    for f in ROW_FRACS:
        y = int(target_h * f)
        xs = np.nonzero(m[y])[0]
        rows.append(y)
        avail.append((xs.min(), xs.max()))

    block_w = min(hi - lo for lo, hi in avail) - 2 * margin
    cx = (m.shape[1] - 1) / 2.0
    x_left = int(cx - block_w / 2)

    metrics = {t: ink_metrics(f"{t}：", font) for t in FIELDS}
    label_w = max(v[2] for v in metrics.values())
    line_x0 = x_left + label_w + gap
    line_x1 = x_left + block_w

    for y, name in zip(rows, FIELDS):
        dx, dy, _, ink_h = metrics[name]
        draw.text((x_left - dx, y - ink_h / 2 - dy), f"{name}：", font=font, fill=255)
        base = int(y + ink_h / 2)
        draw.rounded_rectangle(
            [line_x0, base - rule, line_x1, base], radius=rule // 2, fill=255
        )

    heart = Image.composite(
        Image.new("RGB", (target_w, target_h), (255, 255, 255)),
        Image.new("RGB", (target_w, target_h), HEART_RGB),
        ink,
    ).convert("RGBA")
    heart.putalpha(alpha)

    os.makedirs(outdir, exist_ok=True)
    stem = f"惜食便當愛心_填寫欄_{width_cm:g}cm"
    png = os.path.join(outdir, stem + "_透明.png")
    heart.save(png)

    prev = Image.new("RGB", (target_w + 240, target_h + 240), CARD_BG)
    prev.paste(heart, (120, 120), heart)
    prev.save(os.path.join(outdir, stem + "_預覽.png"))

    ai = os.path.join(outdir, stem + ".ai")
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    pw, ph = target_w / dpi * 72.0, target_h / dpi * 72.0
    c = canvas.Canvas(ai, pagesize=(pw, ph))
    c.drawImage(ImageReader(png), 0, 0, pw, ph, mask="auto")
    c.showPage()
    c.save()

    pdf = os.path.join(outdir, stem + "_CMYK.pdf")
    cmyk_pdf(alpha, ink, dpi, bleed_mm, pdf)

    # 印刷模擬：走同一支 ICC 轉回 sRGB，審色看這張不要看 RGB 版
    sim = Image.composite(
        Image.new("RGB", (target_w, target_h), (255, 255, 255)),
        cmyk_to_srgb(heart_cmyk(), target_w, target_h),
        ink,
    )
    proof = Image.new("RGB", (target_w + 240, target_h + 240), (255, 255, 255))
    proof.paste(sim, (120, 120), alpha)
    proof.save(os.path.join(outdir, stem + "_印刷模擬.png"))

    print(
        f"愛心尺寸 {target_w}×{target_h}px @{dpi}dpi = {width_cm:g}×{target_h/dpi*2.54:.1f}cm"
    )
    print(
        f"文字塊寬 {block_w}px（{block_w/dpi*2.54:.1f}cm）／字面 {font.size}px／底線 {line_x1-line_x0}px"
    )
    for f, (lo, hi), y in zip(ROW_FRACS, avail, rows):
        print(f"  y={y} 可用 {lo}..{hi} 邊距 左{x_left-lo} 右{hi-line_x1}")
    print(
        "輸出：",
        png,
        os.path.join(outdir, stem + "_預覽.png"),
        ai,
        pdf,
        os.path.join(outdir, stem + "_印刷模擬.png"),
        sep="\n  ",
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--width-cm", type=float, default=30.0)
    p.add_argument("--dpi", type=int, default=300)
    p.add_argument("--out", default=os.path.join(BASE, "愛心_填寫欄_20260831"))
    p.add_argument(
        "--bleed-mm", type=float, default=0.0, help="模切出血：沿輪廓外擴的紅色寬度"
    )
    a = p.parse_args()
    build(a.width_cm, a.dpi, a.out, a.bleed_mm)
