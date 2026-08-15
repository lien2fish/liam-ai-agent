# -*- coding: utf-8 -*-
"""二樓面外大 Logo 牆 290×200cm 防水布 — logo ＋ 協會名 ＋ 標語。

防水布只能做矩形，所以整張白底、不留透明。輸出 100dpi，logo 取自既有送印檔
`大Logo牆_345x290cm.tif`（13583×11417，舊尺寸的成品，只當 logo 來源）。

logo 取自那份既有送印 tif（裡面 8593px，縮小不放大，色彩已印刷驗證過）。
設計參數一律以 mm 為單位，改 DPI 不必重調版面。

⚠️ 不套 `tarp_face_pdf.py` 的 enhance(1.65/1.83)：那是給「預先壓暗過」的 12 面
外牆母檔用的，這面的 logo 是既有送印檔原色，套上去會過亮、與已印出的對不起來。

用法: python3 design/big_logo_wall.py [--dpi 100] [--src tif|png] [--no-pdf]
"""
import argparse
import os
import zlib

import numpy as np
from PIL import Image, ImageCms, ImageDraw, ImageFilter, ImageFont

Image.MAX_IMAGE_PIXELS = None

BASE = "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出"
OUT_DIR = f"{BASE}/二樓面外大logo"
SRC_TIF = f"{OUT_DIR}/大Logo牆_345x290cm.tif"
SRC_PNG = f"{OUT_DIR}/惜食台灣_logo_10000px_白底.png"
ICC = "/System/Library/ColorSync/Profiles/Generic CMYK Profile.icc"

ZHF = "/System/Library/Fonts/STHeiti Medium.ttc"

W_CM, H_CM = 290, 200

WHITE = (255, 255, 255)
GREEN = (7, 154, 63)  # #079A3F
GOLD = (200, 138, 8)  # #C88A08

ORG = "惜食台灣行動協會"
SLOGAN = "疼惜食物 疼惜台灣"

# 版面參數，單位 mm。這組是 345×290 版的值，整組乘 K 等比縮到目前畫布高度
LOGO_W_MM = 1800
ORG_MM = 300
SLOGAN_MM = 220
GAP_LOGO_ORG_MM = 160
GAP_ORG_SLOGAN_MM = 100
CONTENT_FILL = 0.87  # 內容總高佔畫布高的比例，其餘平分為上下留白


def ink_bbox(text, font):
    """CJK 的 textbbox 回傳 layout box 不是墨色框，改 render 後取 getbbox。"""
    pad = font.size * 2
    tmp = Image.new("L", (len(text) * font.size + 2 * pad, font.size * 2 + 2 * pad), 0)
    ImageDraw.Draw(tmp).text((pad, pad), text, font=font, fill=255)
    bx0, by0, bx1, by1 = tmp.getbbox()
    return bx0 - pad, by0 - pad, bx1 - pad, by1 - pad


def draw_ink_center(d, text, font, cx, y, fill):
    """以墨色框為準水平置中、上緣對齊 y，回傳墨色框。"""
    bx0, by0, bx1, by1 = ink_bbox(text, font)
    x = cx - (bx1 - bx0) // 2
    d.text((x - bx0, y - by0), text, font=font, fill=fill)
    return x, y, x + (bx1 - bx0), y + (by1 - by0)


def load_logo(src, override=None):
    """回傳白底 RGB 的 logo，已裁到墨色範圍。

    白底與本設計的整張白底同色，直接貼上無縫，不必去背。
    """
    path = override or (SRC_TIF if src == "tif" else SRC_PNG)
    if not os.path.exists(path):
        raise SystemExit(f"找不到 logo 來源：{path}")
    im = Image.open(path).convert("RGB")
    box = im.convert("L").point(lambda v: 255 if v < 245 else 0).getbbox()
    return im.crop(box), os.path.basename(path)


def layout_scale(logo_rgb):
    """整組版面參數共用的縮放倍率，讓內容總高＝畫布高 × CONTENT_FILL。"""
    base = (
        LOGO_W_MM * logo_rgb.height / logo_rgb.width
        + GAP_LOGO_ORG_MM
        + ORG_MM
        + GAP_ORG_SLOGAN_MM
        + SLOGAN_MM
    )
    return CONTENT_FILL * H_CM * 10 / base


def build(logo_rgb, S):
    W, H = round(W_CM * 10 * S), round(H_CM * 10 * S)
    K = layout_scale(logo_rgb)
    logo_w = round(LOGO_W_MM * K * S)
    logo_h = round(logo_w * logo_rgb.height / logo_rgb.width)
    logo = logo_rgb.resize((logo_w, logo_h), Image.LANCZOS)

    of = ImageFont.truetype(ZHF, round(ORG_MM * K * S))
    sf = ImageFont.truetype(ZHF, round(SLOGAN_MM * K * S))
    oh = ink_bbox(ORG, of)[3] - ink_bbox(ORG, of)[1]
    sh = ink_bbox(SLOGAN, sf)[3] - ink_bbox(SLOGAN, sf)[1]

    g1, g2 = round(GAP_LOGO_ORG_MM * K * S), round(GAP_ORG_SLOGAN_MM * K * S)
    total = logo_h + g1 + oh + g2 + sh
    top = (H - total) // 2
    cx = W // 2

    canvas = Image.new("RGB", (W, H), WHITE)
    canvas.paste(logo, (cx - logo_w // 2, top))
    d = ImageDraw.Draw(canvas)
    y2 = top + logo_h + g1
    y3 = y2 + oh + g2
    org_box = draw_ink_center(d, ORG, of, cx, y2, GREEN)
    sl_box = draw_ink_center(d, SLOGAN, sf, cx, y3, GOLD)
    lg = (cx - logo_w // 2, top, cx - logo_w // 2 + logo_w, top + logo_h)
    return canvas, lg, org_box, sl_box, (W, H)


def modal(img, box):
    r = np.asarray(img.crop(box)).reshape(-1, 3)
    r = r[r.sum(axis=1) < 720]
    c, n = np.unique(r, axis=0, return_counts=True)
    return tuple(c[n.argmax()])


def to_cmyk_pdf(img, out_pdf, S):
    """DeviceCMYK + FlateDecode，分段串流寫入。

    影像已經是目標 dpi，不再縮放。三冠彩印的 RIP 會把 PIL 產的 CMYK TIFF
    油墨值反相解讀，所以一律交 PDF。
    """
    W, H = img.size
    srgb = ImageCms.createProfile("sRGB")
    cmyk = ImageCms.getOpenProfile(ICC)
    tmp = out_pdf + ".imgstream"
    comp = zlib.compressobj(6)
    sample = None
    with open(tmp, "wb") as fo:
        for y in range(0, H, 256):
            seg = img.crop((0, y, W, min(y + 256, H)))
            cm = ImageCms.profileToProfile(
                seg, srgb, cmyk,
                renderingIntent=ImageCms.Intent.PERCEPTUAL, outputMode="CMYK",
            )  # fmt: skip
            if sample is None:
                sample = cm.getpixel((5, 5))  # 左上角必為白底，用來擋反相
            fo.write(comp.compress(cm.tobytes()))
        fo.write(comp.flush())
    stream_len = os.path.getsize(tmp)

    w_pt, h_pt = W / S / 25.4 * 72, H / S / 25.4 * 72
    content = f"q {w_pt:.2f} 0 0 {h_pt:.2f} 0 0 cm /Im0 Do Q".encode()
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w_pt:.2f} {h_pt:.2f}] "
            f"/Resources << /XObject << /Im0 5 0 R >> >> /Contents 4 0 R >>"
        ).encode(),
    }
    with open(out_pdf, "wb") as f:
        f.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        off = {}
        for n in (1, 2, 3):
            off[n] = f.tell()
            f.write(f"{n} 0 obj\n".encode() + objs[n] + b"\nendobj\n")
        off[4] = f.tell()
        f.write(
            f"4 0 obj\n<< /Length {len(content)} >>\nstream\n".encode()
            + content
            + b"\nendstream\nendobj\n"
        )
        off[5] = f.tell()
        f.write(
            (
                f"5 0 obj\n<< /Type /XObject /Subtype /Image /Width {W} /Height {H} "
                f"/ColorSpace /DeviceCMYK /BitsPerComponent 8 /Filter /FlateDecode "
                f"/Length {stream_len} >>\nstream\n"
            ).encode()
        )
        with open(tmp, "rb") as fi:
            while True:
                chunk = fi.read(1 << 22)
                if not chunk:
                    break
                f.write(chunk)
        f.write(b"\nendstream\nendobj\n")
        xref = f.tell()
        f.write(b"xref\n0 6\n0000000000 65535 f \n")
        for n in range(1, 6):
            f.write(f"{off[n]:010d} 00000 n \n".encode())
        f.write(
            f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
        )
    os.remove(tmp)
    return sample, (w_pt / 72 * 2.54, h_pt / 72 * 2.54)


def verify(img, lg, org, sl, size, S, K, white_cmyk, pdf_cm):
    W, H = size
    a_top = np.asarray(img.crop((0, 0, W, 4)))
    ok = [
        (f"尺寸 {W}×{H} ({W_CM}×{H_CM}cm @{round(S*25.4)}dpi)",
         (W, H) == (round(W_CM * 10 * S), round(H_CM * 10 * S))),
        ("整張白底、四角為白（防水布矩形）",
         all(img.getpixel(p) == WHITE for p in ((0, 0), (W-1, 0), (0, H-1), (W-1, H-1)))),
        ("上緣整條無雜點", bool((a_top == 255).all())),
        (f"logo 水平置中 cx={(lg[0]+lg[2])//2}", abs((lg[0]+lg[2])//2 - W//2) <= 2),
        (f"協會名 水平置中 cx={(org[0]+org[2])//2}", abs((org[0]+org[2])//2 - W//2) <= 2),
        (f"標語 水平置中 cx={(sl[0]+sl[2])//2}", abs((sl[0]+sl[2])//2 - W//2) <= 2),
        (f"內容垂直置中 上{lg[1]} 下{H-sl[3]}", abs(lg[1] - (H - sl[3])) <= 2),
        (f"logo→協會名 {org[1]-lg[3]}px", abs((org[1]-lg[3]) - round(GAP_LOGO_ORG_MM*K*S)) <= 2),
        (f"協會名→標語 {sl[1]-org[3]}px", abs((sl[1]-org[3]) - round(GAP_ORG_SLOGAN_MM*K*S)) <= 2),
        ("協會名 色 = 品牌綠", modal(img, org) == GREEN),
        ("標語 色 = 金黃", modal(img, sl) == GOLD),
        (f"左右留白 {min(lg[0], org[0], sl[0])}px", min(lg[0], org[0], sl[0]) >= 200),
    ]  # fmt: skip
    if white_cmyk is not None:
        # 反相的話白底會變成高油墨值。白色在 CMYK 應該接近 0
        ok.append((f"CMYK 白底油墨 {white_cmyk} 未反相", max(white_cmyk) <= 12))
        ok.append((f"PDF 頁面 {pdf_cm[0]:.1f}×{pdf_cm[1]:.1f}cm",
                   abs(pdf_cm[0] - W_CM) < 0.5 and abs(pdf_cm[1] - H_CM) < 0.5))  # fmt: skip

    print("-" * 62)
    for item, passed in ok:
        print("{:<50} {}".format(item, "✅" if passed else "❌"))
    return all(p for _, p in ok)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dpi", type=int, default=100)
    ap.add_argument("--src", choices=["tif", "png"], default="tif")
    ap.add_argument("--logo", help="直接指定 logo 來源路徑，蓋過 --src")
    ap.add_argument("--no-pdf", action="store_true")
    args = ap.parse_args()

    S = args.dpi / 25.4  # px per mm
    logo_rgb, name = load_logo(args.src, args.logo)
    K = layout_scale(logo_rgb)
    tgt = round(LOGO_W_MM * K * S)
    print(f"logo 來源 {name}　墨色範圍 {logo_rgb.width}×{logo_rgb.height}px")
    print(
        f"版面等比縮放 K={K:.3f}（協會名 {ORG_MM*K/10:.1f}cm、標語 {SLOGAN_MM*K/10:.1f}cm）"
    )
    print(f"　→ 縮到 {tgt}px（{LOGO_W_MM*K/10:.0f}cm），倍率 {tgt/logo_rgb.width:.2f}×"
          f"{'（縮小，無畫質損失）' if tgt <= logo_rgb.width else '（放大⚠️）'}\n")  # fmt: skip

    img, lg, org, sl, size = build(logo_rgb, S)
    p1 = f"{OUT_DIR}/大Logo牆_{W_CM}x{H_CM}cm_含標題.png"
    img.save(p1)
    print(f"✅ 母檔 RGB {p1}")

    img.resize((900, round(900 * size[1] / size[0])), Image.LANCZOS).save(
        f"{OUT_DIR}/預覽_大Logo牆_{W_CM}x{H_CM}cm_含標題.png"
    )

    white_cmyk, pdf_cm = None, (0, 0)
    if not args.no_pdf:
        p2 = f"{OUT_DIR}/大Logo牆_{W_CM}x{H_CM}cm_含標題_CMYK.pdf"
        white_cmyk, pdf_cm = to_cmyk_pdf(img, p2, S)
        print(f"✅ 送印 CMYK PDF {p2}　{os.path.getsize(p2)/1e6:.0f}MB")

    print()
    ok = verify(img, lg, org, sl, size, S, K, white_cmyk, pdf_cm)
    print("\n" + ("全部通過" if ok else "⚠️ 有項目未通過，見上表"))


if __name__ == "__main__":
    main()
