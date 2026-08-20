# -*- coding: utf-8 -*-
"""次牆 02 右上角致贈格的替換補片 → 原尺寸 DeviceCMYK PDF。

尺寸、圓角、描邊寬與油墨值全部量自既有送印檔
`次牆_02_…_359cmx130cm_CMYK.pdf` 的內嵌 CMYK 影像，補片貼上去才不會有色差。

⚠️ 直接以 CMYK 作圖、不走 RGB→ICC 轉換：來源已是 CMYK，繞一圈回來必然位移。
"""
import argparse
import os
import zlib

import numpy as np
from PIL import Image, ImageDraw, ImageFont

DPI = 100
W_PX, H_PX = 3293, 553  # 原致贈格外框（含描邊）；寬度可隨字數改，高度固定
RADIUS, STROKE = 61, 20
SIDE_PAD = 218  # 文字左右留白，取自原格（左 5.64 / 右 5.44 cm）
SS = 4  # 超取樣倍率，圓角與字才不會有鋸齒

# 量自原檔的油墨值
INK_WHITE = (4, 2, 4, 0)
INK_LINE = (124, 0, 184, 0)
INK_TEXT = (177, 13, 251, 44)

# 原檔與致贈格在原圖中的位置——圓角外的四個角落要填回原本的照片背景，
# 補片才能裁成方形直接貼，不會露出四塊白角。
SRC_PDF = (
    "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/外牆防水布（已完成）/"
    "輸出用_分面PDF_調亮100dpi/次牆_02_你的小動作就是惜食_359cmx130cm_CMYK.pdf"
)
SRC_BOX = (10646, 237)  # 致贈格左上角在原圖的像素座標

TEXT = "惜食台灣行動協會"
# 加長版沿用同一個右上角錨點：右緣與頂緣不動、往左延伸，
# 角落背景才取得到（原圖只有這一段有畫面）。
CAP_H = 266  # 原「國際扶輪3501地區捐贈」的字面高，沿用以維持整批一致
ZHF = "/System/Library/Fonts/STHeiti Medium.ttc"


def ink_box(text, font):
    """CJK 的 textbbox 給的是 layout box，要 render 後取墨色框。"""
    pad = font.size
    im = Image.new("L", (len(text) * font.size + 2 * pad, font.size * 3), 0)
    ImageDraw.Draw(im).text((pad, pad), text, font=font, fill=255)
    b = im.getbbox()
    return b[0] - pad, b[1] - pad, b[2] - pad, b[3] - pad


def fit_font(target_h, probe="國際扶輪地區捐贈"):
    """用固定樣本字串定字級——不同字串的墨色高會差幾 px，
    改用樣本才能保證各版本字面高一致。"""
    size = target_h
    for _ in range(24):
        f = ImageFont.truetype(ZHF, size)
        b = ink_box(probe, f)
        h = b[3] - b[1]
        if abs(h - target_h) <= 1:
            return f
        size = max(1, round(size * target_h / h))
    return ImageFont.truetype(ZHF, size)


def auto_width(text):
    """字數決定框寬：文字墨色寬＋左右各 SIDE_PAD。不短於原格。"""
    f = fit_font(CAP_H * SS)
    b = ink_box(text, f)
    return max(W_PX, round((b[2] - b[0]) / SS) + 2 * SIDE_PAD)


def masks(text, box_w):
    """回傳 (框內白遮罩, 描邊遮罩, 文字遮罩)，皆為 0~1 的浮點陣列。"""
    w, h = box_w * SS, H_PX * SS
    outer = Image.new("L", (w, h), 0)
    ImageDraw.Draw(outer).rounded_rectangle((0, 0, w - 1, h - 1), RADIUS * SS, fill=255)
    inner = Image.new("L", (w, h), 0)
    s = STROKE * SS
    ImageDraw.Draw(inner).rounded_rectangle(
        (s, s, w - 1 - s, h - 1 - s), max(0, (RADIUS - STROKE) * SS), fill=255
    )

    font = fit_font(CAP_H * SS)
    b = ink_box(text, font)
    tx = (w - (b[2] - b[0])) / 2 - b[0]
    ty = (h - (b[3] - b[1])) / 2 - b[1]
    tm = Image.new("L", (w, h), 0)
    ImageDraw.Draw(tm).text((tx, ty), text, font=font, fill=255)

    r = lambda m: np.asarray(m.resize((box_w, H_PX), Image.LANCZOS), np.float32) / 255.0
    return r(outer), r(inner), r(tm), font.size / SS


def source_corners(src_pdf, box_w):
    """從原檔取出致贈格範圍的照片背景。取不到就回傳 None（角落留白）。

    右緣與頂緣對齊原格，往左延伸。
    """
    import re

    if not src_pdf or not os.path.exists(src_pdf):
        return None
    d = open(src_pdf, "rb").read()
    m = re.search(rb"/Width\s+(\d+).*?/Height\s+(\d+)", d[:400000], re.S)
    im = re.search(rb"/Subtype\s*/Image.*?stream\r?\n", d, re.S)
    if not (m and im):
        return None
    W, H = int(m.group(1)), int(m.group(2))
    raw = zlib.decompress(d[im.end() : d.find(b"\nendstream", im.end())])
    a = np.frombuffer(raw, np.uint8).reshape(H, W, 4)
    x, y = SRC_BOX
    x1 = x + W_PX
    x0 = max(0, x1 - box_w)
    seg = a[y : y + H_PX, x0:x1].astype(np.float32)
    if seg.shape[1] < box_w:  # 往左超出畫面就靠右擺、左側鏡射補齊
        pad = box_w - seg.shape[1]
        seg = np.concatenate([seg[:, :pad][:, ::-1], seg], 1)
    return seg


def build_vector(out_pdf, text=TEXT, box_w=None):
    """只有圓角框與文字的向量 PDF——圓角外完全無墨，不含任何點陣底圖。

    尺寸／字級／油墨值與點陣版一致，位置由 PIL 的墨色框換算成 reportlab 的基線座標。
    """
    from reportlab.lib.colors import CMYKColor
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas as rl_canvas

    pdfmetrics.registerFont(TTFont("Hei", ZHF, subfontIndex=0))
    box_w = box_w or auto_width(text)

    font = fit_font(CAP_H * SS)
    size_px = font.size / SS
    pil = ImageFont.truetype(ZHF, round(size_px))
    b = ink_box(text, pil)
    tx = (box_w - (b[2] - b[0])) / 2 - b[0]
    baseline_px = (H_PX - (b[3] - b[1])) / 2 - b[1] + pil.getmetrics()[0]

    pt = lambda px: px / DPI * 72
    ink = lambda v: CMYKColor(*[c / 255 for c in v])
    c = rl_canvas.Canvas(out_pdf, pagesize=(pt(box_w), pt(H_PX)))
    c.setFillColor(ink(INK_WHITE))
    c.setStrokeColor(ink(INK_LINE))
    c.setLineWidth(pt(STROKE))
    c.roundRect(
        pt(STROKE / 2),
        pt(STROKE / 2),
        pt(box_w - STROKE),
        pt(H_PX - STROKE),
        pt(RADIUS - STROKE / 2),
        stroke=1,
        fill=1,
    )
    c.setFillColor(ink(INK_TEXT))
    c.setFont("Hei", pt(size_px))
    c.drawString(pt(tx), pt(H_PX - baseline_px), text)
    c.save()

    print(f"✅ {out_pdf}（向量）")
    print(
        f"   {box_w/DPI*2.54:.2f}×{H_PX/DPI*2.54:.2f} cm"
        f"　字級 {size_px:.0f}px　{os.path.getsize(out_pdf)/1e3:.0f}KB"
    )


def build(out_pdf, src_pdf=None, text=TEXT, box_w=None, corners="white"):
    box_w = box_w or auto_width(text)
    outer, inner, tm, fsize = masks(text, box_w)
    bg = source_corners(src_pdf, box_w) if corners == "photo" else None
    stroke = np.clip(outer - inner, 0, 1)

    canvas = np.zeros((H_PX, box_w, 4), np.float32)
    for i in range(4):
        v = inner * INK_WHITE[i] + stroke * INK_LINE[i]
        v = v * (1 - tm) + tm * INK_TEXT[i]
        base = bg[..., i] if bg is not None else 0.0
        canvas[..., i] = v * outer + base * (1 - outer)
    cmyk = np.clip(canvas, 0, 255).astype(np.uint8)

    stream = zlib.compress(cmyk.tobytes(), 6)
    w_pt = box_w / DPI * 72
    h_pt = H_PX / DPI * 72
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
            f"<< /Type /XObject /Subtype /Image /Width {box_w} /Height {H_PX} "
            f"/ColorSpace /DeviceCMYK /BitsPerComponent 8 /Filter /FlateDecode "
            f"/Length {len(stream)} >>\nstream\n"
        ).encode()
        + stream
        + b"\nendstream",
    }
    with open(out_pdf, "wb") as f:
        f.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        off = {}
        for n in sorted(objs):
            off[n] = f.tell()
            f.write(f"{n} 0 obj\n".encode() + objs[n] + b"\nendobj\n")
        xref = f.tell()
        f.write(b"xref\n0 6\n0000000000 65535 f \n")
        for n in range(1, 6):
            f.write(f"{off[n]:010d} 00000 n \n".encode())
        f.write(
            f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
        )

    Image.fromarray(cmyk[..., :4], "CMYK").convert("RGB").save(
        os.path.splitext(out_pdf)[0] + "_預覽.png"
    )
    print(f"✅ {out_pdf}")
    print(
        f"   {box_w}×{H_PX}px @{DPI}dpi = {box_w/DPI*2.54:.2f}×{H_PX/DPI*2.54:.2f} cm"
        f"　字級 {fsize:.0f}px　{os.path.getsize(out_pdf)/1e6:.1f}MB"
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--src", default=SRC_PDF, help="原檔 PDF，用來填圓角外的背景")
    ap.add_argument("--text", default=TEXT)
    ap.add_argument("--width", type=int, help="框寬 px@100dpi；省略＝依字數自動")
    ap.add_argument(
        "--corners",
        choices=("white", "photo"),
        default="white",
        help="圓角外：white＝純白（沿圓角裁形用）／photo＝取原檔照片背景（方形直貼用）",
    )
    ap.add_argument(
        "--vector", action="store_true", help="輸出純向量版（圓角外無墨，無點陣底圖）"
    )
    a = ap.parse_args()
    if a.vector:
        build_vector(a.out, a.text, a.width)
    else:
        build(a.out, a.src, a.text, a.width, a.corners)
