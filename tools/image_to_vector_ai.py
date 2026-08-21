# -*- coding: utf-8 -*-
import sys, os, subprocess, tempfile, re
import numpy as np
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas
from reportlab.lib.colors import CMYKColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

DIR = sys.argv[1]
OUT = sys.argv[2]
QA = sys.argv[3]
pdfmetrics.registerFont(
    TTFont("Hei", "/System/Library/Fonts/STHeiti Medium.ttc", subfontIndex=0)
)
S = 72.0 / 300.0
CAL = 776.0 / 703.0  # em_px / source_glyph_height calibration

# (source filename, line1, line2, output basename)
# 轉檔清單含 43 位理監事的職稱與姓名，repo 為 public，改放 config/（已 gitignore）。
# 沒有這份檔案時給明確訊息，不要靜默跑出空結果。
try:
    from config.hex_badge_jobs import JOBS
except ImportError:
    JOBS = []
    print("⚠️ 找不到 config/hex_badge_jobs.py，沒有可轉檔的名單")


def load_rgb(path):
    tmp = tempfile.mktemp(suffix=".png")
    subprocess.run(
        ["sips", "-s", "format", "png", path, "--out", tmp], capture_output=True
    )
    im = Image.open(tmp).convert("RGB")
    a = np.asarray(im)
    os.remove(tmp)
    return a


def load_cmyk(path):
    im = Image.open(path)
    if im.mode != "CMYK":
        im = im.convert("CMYK")
    return np.asarray(im)


def bands_of(mask, minfrac=0.02):
    rows = mask.sum(axis=1)
    th = mask.shape[1] * minfrac
    r = np.where(rows > th)[0]
    if len(r) == 0:
        return []
    gap = mask.shape[0] * 0.03
    bands = []
    start = r[0]
    prev = r[0]
    for v in r[1:]:
        if v - prev > gap:
            bands.append((start, prev))
            start = v
        prev = v
    bands.append((start, prev))
    return bands


def process(job):
    src, l1, l2, ob = job
    path = os.path.join(DIR, src)
    a = load_rgb(path)
    H, W, _ = a.shape
    nearwhite = (a[:, :, 0] > 235) & (a[:, :, 1] > 235) & (a[:, :, 2] > 235)
    colored = ~nearwhite
    ys, xs = np.where(colored)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    fillfrac = colored[y0 : y1 + 1, x0 : x1 + 1].mean()
    cmyk = load_cmyk(path)
    lines = [l1, l2]
    hexmode = fillfrac > 0.55
    # 若為六邊形且檔名有「邊長Xcm」，依邊長鎖定實際尺寸（平頂正六邊形寬=2*邊長）
    m = re.search(r"邊長([\d.]+)cm", ob)
    if hexmode and m:
        S = (2 * float(m.group(1)) * 28.346456692913385) / (x1 - x0)
    else:
        S = 72.0 / 300.0
    canv = canvas.Canvas(os.path.join(OUT, ob + ".ai"), pagesize=(W * S, H * S))

    def X(px):
        return px * S

    def Y(py):
        return (H - py) * S

    if hexmode:
        # hexagon fill mask = colored
        ymid = (y0 + y1) // 2
        toprow = colored[y0 + int((y1 - y0) * 0.01) + 2]
        tc = np.where(toprow)[0]
        tlx, trx = tc.min(), tc.max()
        V = [(tlx, y0), (trx, y0), (x1, ymid), (trx, y1), (tlx, y1), (x0, ymid)]
        cx = (x0 + x1) // 2
        # fill color: sample body point above text
        sx, sy = cx, y0 + int((y1 - y0) * 0.10)
        cc = cmyk[sy, sx]
        fill = CMYKColor(cc[0] / 255, cc[1] / 255, cc[2] / 255, cc[3] / 255)
        p = canv.beginPath()
        p.moveTo(X(V[0][0]), Y(V[0][1]))
        for x, y in V[1:]:
            p.lineTo(X(x), Y(y))
        p.close()
        canv.setFillColor(fill)
        canv.drawPath(p, fill=1, stroke=0)
        # text = white inside polygon
        pm = Image.new("L", (W, H), 0)
        ImageDraw.Draw(pm).polygon(V, fill=255)
        polym = np.asarray(pm) > 0
        # shrink to avoid AA edges
        inset = int((x1 - x0) * 0.04)
        pm2 = Image.new("L", (W, H), 0)
        Vi = [
            (tlx + inset, y0 + inset),
            (trx - inset, y0 + inset),
            (x1 - inset, ymid),
            (trx - inset, y1 - inset),
            (tlx + inset, y1 - inset),
            (x0 + inset, ymid),
        ]
        ImageDraw.Draw(pm2).polygon(Vi, fill=255)
        tm = (
            (a[:, :, 0] > 200)
            & (a[:, :, 1] > 200)
            & (a[:, :, 2] > 200)
            & (np.asarray(pm2) > 0)
        )
        txt_cmyk = (0, 0, 0, 0)  # white
        tcx = cx
    else:
        # no hexagon; text = colored
        tm = colored
        # text color = median cmyk over colored
        med = np.median(cmyk[colored], axis=0).astype(int)
        txt_cmyk = (med[0], med[1], med[2], med[3])
        tcx = (x0 + x1) // 2
    bd = bands_of(tm)
    if len(bd) != len(lines):
        # fallback: even split of text bbox
        ty0, ty1 = (tm.any(axis=1)).nonzero()[0][[0, -1]]
        n = len(lines)
        seg = (ty1 - ty0) / n
        bd = [(int(ty0 + i * seg), int(ty0 + (i + 1) * seg)) for i in range(n)]
    tc = CMYKColor(
        txt_cmyk[0] / 255, txt_cmyk[1] / 255, txt_cmyk[2] / 255, txt_cmyk[3] / 255
    )
    canv.setFillColor(tc)
    canv.setStrokeColor(tc)
    for (b0, b1), t in zip(bd, lines):
        gh = b1 - b0
        em = gh * CAL
        fs = em * S
        cy = (b0 + b1) / 2.0
        baseline = cy + 0.38 * em
        canv.setFont("Hei", fs)
        canv.setLineWidth(em * 8.0 / 776.0 * S)
        w = pdfmetrics.stringWidth(t, "Hei", fs)
        to = canv.beginText(X(tcx) - w / 2, Y(baseline))
        to.setTextRenderMode(2)
        to.textOut(t)
        canv.drawText(to)
    canv.showPage()
    canv.save()
    # QA render
    qp = os.path.join(QA, ob + ".png")
    subprocess.run(
        [
            "sips",
            "-s",
            "format",
            "png",
            "-Z",
            "500",
            os.path.join(OUT, ob + ".ai"),
            "--out",
            qp,
        ],
        capture_output=True,
    )
    return (ob, "hex" if hexmode else "text", f"{W}x{H}", f"lines={len(bd)}")


FILTER = sys.argv[4] if len(sys.argv) > 4 else None  # 只跑檔名含此字串的 job
ok = 0
err = []
jobs = [j for j in JOBS if not FILTER or FILTER in j[0]]
for j in jobs:
    try:
        r = process(j)
        ok += 1
        print("OK  ", r[0], r[1], r[2], r[3])
    except Exception as e:
        err.append((j[0], str(e)))
        print("ERR ", j[0], e)
print(f"\n完成 {ok}/{len(jobs)}  失敗 {len(err)}")
