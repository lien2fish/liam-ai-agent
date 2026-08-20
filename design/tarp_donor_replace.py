# -*- coding: utf-8 -*-
"""把致贈格直接蓋回整面防水布的送印 PDF，輸出同規格的整面 DeviceCMYK PDF。

與 `tarp_donor_patch.py` 的差別：那支產獨立補片（廠商另外印了貼上去），
這支是整面重出，圓角外沿用原面自己的背景，所以沒有角落色塊的問題。

⚠️ 整面影像 400×130cm@100dpi 就有 322MB，全程走 memmap 與串流壓縮，
不要改成一次讀進記憶體（8GB 機器會被打爆）。
"""
import argparse
import os
import re
import zlib

import numpy as np

from tarp_donor_patch import (
    DPI,
    H_PX,
    INK_LINE,
    INK_TEXT,
    INK_WHITE,
    auto_width,
    masks,
)

CHUNK = 1 << 22


def _image_obj(pdf_bytes):
    m = re.search(rb"/Width\s+(\d+)\s*/Height\s+(\d+)", pdf_bytes, re.S)
    if not m:
        m = re.search(rb"/Width\s+(\d+).*?/Height\s+(\d+)", pdf_bytes[:400000], re.S)
    im = re.search(rb"/Subtype\s*/Image.*?stream\r?\n", pdf_bytes, re.S)
    end = pdf_bytes.find(b"\nendstream", im.end())
    return int(m.group(1)), int(m.group(2)), im.end(), end


def unpack(face_pdf, raw_path):
    """把整面影像解壓到 raw 檔，回傳 (寬, 高)。"""
    d = open(face_pdf, "rb").read()
    W, H, s, e = _image_obj(d)
    dec = zlib.decompressobj()
    with open(raw_path, "wb") as f:
        for i in range(s, e, CHUNK):
            f.write(dec.decompress(d[i : min(i + CHUNK, e)]))
        f.write(dec.flush())
    got = os.path.getsize(raw_path)
    if got != W * H * 4:
        raise SystemExit(f"解出來 {got} bytes，與 {W}×{H}×4={W*H*4} 不符")
    return W, H


def paint(raw_path, W, H, x, y, text, box_w=None):
    """就地把致贈格畫進 raw 影像。圓角外保留原背景。"""
    box_w = box_w or auto_width(text)
    outer, inner, tm, fsize = masks(text, box_w)
    stroke = np.clip(outer - inner, 0, 1)
    if x + box_w > W or y + H_PX > H:
        raise SystemExit(f"致贈格 {box_w}×{H_PX} 放在 ({x},{y}) 會超出 {W}×{H}")

    a = np.memmap(raw_path, np.uint8, "r+", shape=(H, W, 4))
    seg = a[y : y + H_PX, x : x + box_w].astype(np.float32)
    for i in range(4):
        v = inner * INK_WHITE[i] + stroke * INK_LINE[i]
        v = v * (1 - tm) + tm * INK_TEXT[i]
        seg[..., i] = v * outer + seg[..., i] * (1 - outer)
    a[y : y + H_PX, x : x + box_w] = np.clip(seg, 0, 255).astype(np.uint8)
    a.flush()
    del a
    return box_w, fsize


def repack(raw_path, W, H, out_pdf, tmp_z):
    """raw 影像串流壓縮後組成整面 PDF，MediaBox 依 100dpi 換算。"""
    co = zlib.compressobj(6)
    with open(raw_path, "rb") as fi, open(tmp_z, "wb") as fo:
        while True:
            b = fi.read(CHUNK)
            if not b:
                break
            fo.write(co.compress(b))
        fo.write(co.flush())
    zlen = os.path.getsize(tmp_z)

    w_pt, h_pt = W / DPI * 72, H / DPI * 72
    content = f"q {w_pt:.2f} 0 0 {h_pt:.2f} 0 0 cm /Im0 Do Q".encode()
    head = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w_pt:.2f} {h_pt:.2f}] "
            f"/TrimBox [0 0 {w_pt:.2f} {h_pt:.2f}] "
            f"/Resources << /XObject << /Im0 5 0 R >> >> /Contents 4 0 R >>"
        ).encode(),
        4: f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream",
    }
    with open(out_pdf, "wb") as f:
        f.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        off = {}
        for n in sorted(head):
            off[n] = f.tell()
            f.write(f"{n} 0 obj\n".encode() + head[n] + b"\nendobj\n")
        off[5] = f.tell()
        f.write(
            f"5 0 obj\n<< /Type /XObject /Subtype /Image /Width {W} /Height {H} "
            f"/ColorSpace /DeviceCMYK /BitsPerComponent 8 /Filter /FlateDecode "
            f"/Length {zlen} >>\nstream\n".encode()
        )
        with open(tmp_z, "rb") as fz:
            while True:
                b = fz.read(CHUNK)
                if not b:
                    break
                f.write(b)
        f.write(b"\nendstream\nendobj\n")
        xref = f.tell()
        f.write(b"xref\n0 6\n0000000000 65535 f \n")
        for n in range(1, 6):
            f.write(f"{off[n]:010d} 00000 n \n".encode())
        f.write(f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("face_pdf")
    ap.add_argument("out_pdf")
    ap.add_argument("--text", required=True)
    ap.add_argument("--at", required=True, help="致贈格左上角像素座標 x,y")
    ap.add_argument("--width", type=int, help="框寬 px@100dpi；省略＝依字數自動")
    ap.add_argument("--tmp", default="/tmp", help="放 raw 中繼檔的目錄（需 ~700MB）")
    a = ap.parse_args()

    raw = os.path.join(a.tmp, "face_raw.cmyk")
    tz = os.path.join(a.tmp, "face_raw.z")
    W, H = unpack(a.face_pdf, raw)
    x, y = (int(v) for v in a.at.split(","))
    bw, fs = paint(raw, W, H, x, y, a.text, a.width)
    repack(raw, W, H, a.out_pdf, tz)
    for p in (raw, tz):
        os.remove(p)
    print(f"✅ {a.out_pdf}")
    print(
        f"   整面 {W}×{H}px @{DPI}dpi = {W/DPI*2.54:.1f}×{H/DPI*2.54:.1f} cm"
        f"　致贈格 {bw}×{H_PX} @({x},{y})　字級 {fs:.0f}px"
        f"　{os.path.getsize(a.out_pdf)/1e6:.0f}MB"
    )
