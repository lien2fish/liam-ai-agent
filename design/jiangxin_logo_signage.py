"""匠鑫私廚 LOGO 送印檔產生器

來源：/Users/lien/Desktop/LOGO.ai（A4 橫式，左＝深色版、右＝淺色版，純向量 CMYK）
輸出：指定尺寸的送印 PDF，全版面不出血（頁面＝完成尺寸，無裁切標記）。

色彩全程沿用來源的 ICCBased CMYK（Japan Color 2001 Coated），不做任何轉換。
"""

import fitz

CM = 28.346456692913385
MM = 2.8346456692913385

SRC = "/Users/lien/Desktop/LOGO.ai"

SETS = {
    "直式": ("/Users/lien/Desktop/匠鑫私廚_LOGO送印", [(45.0, 65.4), (44.0, 57.0)]),
    "橫式": ("/Users/lien/Desktop/匠鑫私廚_LOGO送印_橫式", [(65.4, 45.0), (57.0, 44.0)]),
}

LOGO_HEIGHT_FRAC = 0.84

# 全版面不出血：頁面＝完成尺寸，無出血、無頁邊、不畫裁切標記。
# 要回到含出血版把這三個值改回 3*MM / 12*MM / True 即可。
BLEED = 0
MEDIA_PAD = 0
DRAW_MARKS = False
MARK_GAP = 3.5 * MM
MARK_LEN = 7 * MM
MARK_WIDTH = 0.25

VARIANTS = {
    "深色版": {
        "clip": (132.36, 208.20, 246.84, 428.40),
        "bg": (0.917, 0.856, 0.605, 0.395),
    },
    "淺色版": {
        "clip": (567.00, 207.72, 682.08, 428.40),
        "bg": None,
    },
}


def strip_optional_content(path):
    """把來源的 Optional Content 圖層攤平，避免 RIP 判定為隱藏而整組不印。"""
    doc = fitz.open(path)
    page = doc[0]
    content = page.read_contents().decode("latin-1")
    prefix = "/OC /MC0 BDC \n"
    if content.startswith(prefix):
        content = content[len(prefix):]
        tail = content.rfind("EMC ")
        content = content[:tail] + content[tail + 4:]
        xref = doc.get_new_xref()
        doc.update_object(xref, "<<>>")
        doc.update_stream(xref, content.encode("latin-1"))
        doc.xref_set_key(page.xref, "Contents", "%d 0 R" % xref)
    doc.xref_set_key(doc.pdf_catalog(), "OCProperties", "null")
    return doc


def find_icc_colorspace(doc, page):
    """找出 show_pdf_page 複製進來的 ICCBased 色彩空間 xref。"""
    xobjects = page.get_xobjects()
    for item in xobjects:
        xref = item[0]
        cs = doc.xref_get_key(xref, "Resources/ColorSpace/CS0")
        if cs[0] == "xref":
            return int(cs[1].split()[0])
    raise RuntimeError("找不到來源的 ICCBased 色彩空間")


def build(src, trim_w_cm, trim_h_cm, variant, out_path):
    spec = VARIANTS[variant]
    trim_w, trim_h = trim_w_cm * CM, trim_h_cm * CM
    W = trim_w + 2 * MEDIA_PAD
    H = trim_h + 2 * MEDIA_PAD

    out = fitz.open()
    page = out.new_page(width=W, height=H)

    cx0, cy0, cx1, cy1 = spec["clip"]
    logo_h = trim_h * LOGO_HEIGHT_FRAC
    logo_w = logo_h * (cx1 - cx0) / (cy1 - cy0)
    lx0 = MEDIA_PAD + (trim_w - logo_w) / 2
    ly0 = MEDIA_PAD + (trim_h - logo_h) / 2

    page.show_pdf_page(
        fitz.Rect(lx0, H - (ly0 + logo_h), lx0 + logo_w, H - ly0),
        src,
        0,
        clip=fitz.Rect(cx0, cy0, cx1, cy1),
    )

    icc = find_icc_colorspace(out, page)
    res_kind, res_val = out.xref_get_key(page.xref, "Resources")
    res_xref = int(res_val.split()[0]) if res_kind == "xref" else page.xref
    res_key = "ColorSpace/CS0" if res_kind == "xref" else "Resources/ColorSpace/CS0"
    out.xref_set_key(res_xref, res_key, "%d 0 R" % icc)

    before = ["q", "/CS0 cs"]
    if spec["bg"]:
        before.append("%.4f %.4f %.4f %.4f scn" % spec["bg"])
        before.append(
            "%.4f %.4f %.4f %.4f re f"
            % (
                MEDIA_PAD - BLEED,
                MEDIA_PAD - BLEED,
                trim_w + 2 * BLEED,
                trim_h + 2 * BLEED,
            )
        )
    before.append("Q")

    # 裁切標記畫成填色矩形而非描邊線：描邊需另外設 /CS0 CS，
    # 只設填色的 /CS0 cs 會讓 SCN 失效、標記整組不印。
    marks = ["q", "/CS0 cs", "1 1 1 1 scn"]
    x_edges = [MEDIA_PAD, MEDIA_PAD + trim_w]
    y_edges = [MEDIA_PAD, MEDIA_PAD + trim_h]
    half = MARK_WIDTH / 2
    for i, x in enumerate(x_edges):
        outward = -1 if i == 0 else 1
        start = x + outward * (MARK_GAP + MARK_LEN)
        for y in y_edges:
            marks.append(
                "%.4f %.4f %.4f %.4f re f"
                % (min(start, x + outward * MARK_GAP), y - half, MARK_LEN, MARK_WIDTH)
            )
    for j, y in enumerate(y_edges):
        outward = -1 if j == 0 else 1
        start = y + outward * (MARK_GAP + MARK_LEN)
        for x in x_edges:
            marks.append(
                "%.4f %.4f %.4f %.4f re f"
                % (x - half, min(start, y + outward * MARK_GAP), MARK_WIDTH, MARK_LEN)
            )
    marks.append("Q")

    head = out.get_new_xref()
    out.update_object(head, "<<>>")
    out.update_stream(head, "\n".join(before).encode("latin-1"))
    contents = [head] + list(page.get_contents())
    if DRAW_MARKS:
        tail = out.get_new_xref()
        out.update_object(tail, "<<>>")
        out.update_stream(tail, "\n".join(marks).encode("latin-1"))
        contents.append(tail)

    out.xref_set_key(
        page.xref,
        "Contents",
        "[%s]" % " ".join("%d 0 R" % x for x in contents),
    )

    box = lambda x0, y0, x1, y1: "[%.4f %.4f %.4f %.4f]" % (x0, y0, x1, y1)
    out.xref_set_key(page.xref, "MediaBox", box(0, 0, W, H))
    out.xref_set_key(page.xref, "CropBox", box(0, 0, W, H))
    out.xref_set_key(
        page.xref,
        "BleedBox",
        box(
            MEDIA_PAD - BLEED,
            MEDIA_PAD - BLEED,
            MEDIA_PAD + trim_w + BLEED,
            MEDIA_PAD + trim_h + BLEED,
        ),
    )
    trimbox = box(MEDIA_PAD, MEDIA_PAD, MEDIA_PAD + trim_w, MEDIA_PAD + trim_h)
    out.xref_set_key(page.xref, "TrimBox", trimbox)
    out.xref_set_key(page.xref, "ArtBox", trimbox)

    out.set_metadata(
        {
            "title": "匠鑫私廚 LOGO %s %gx%gcm" % (variant, trim_w_cm, trim_h_cm),
            "producer": "",
            "creator": "",
        }
    )
    out.save(out_path, garbage=3, deflate=True, clean=True)
    out.close()
    return logo_w / CM, logo_h / CM


def main():
    import os
    import sys

    wanted = sys.argv[1:] or list(SETS)
    src = strip_optional_content(SRC)
    for key in wanted:
        out_dir, sizes = SETS[key]
        os.makedirs(out_dir, exist_ok=True)
        print("== %s -> %s" % (key, out_dir))
        for w_cm, h_cm in sizes:
            for variant in VARIANTS:
                name = "匠鑫私廚_LOGO_%s_%gx%gcm_無出血滿版.pdf" % (variant, w_cm, h_cm)
                path = os.path.join(out_dir, name)
                lw, lh = build(src, w_cm, h_cm, variant, path)
                print("   %s  logo %.2f x %.2f cm" % (name, lw, lh))
    src.close()


if __name__ == "__main__":
    main()
