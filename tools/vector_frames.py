#!/usr/bin/env python3
"""
白底幾何外框向量產生器 → 輸出 .ai（PDF 相容，Illustrator 可開、無限放大）

用法：
  python3 tools/vector_frames.py <輸出資料夾> [選項]

選項：
  --hex   8.5,11,19     產生這些「邊長(cm)」的平頂正六邊形外框（逗號分隔）
  --circle 38           產生這些「直徑(cm)」的圓形外框（逗號分隔）
  --stroke-mm 2.0       邊框線寬（mm，絕對值），預設 2
  --margin-cm 1.0       四周留白（cm），預設 1
  --color  K100         框線顏色：K100(黑) / GREEN(品牌綠 RGB7,153,61) / 或 "C,M,Y,K" 0-100

範例：
  python3 tools/vector_frames.py ./out --hex 8.5,11,19 --circle 38
  python3 tools/vector_frames.py ./out --hex 11 --stroke-mm 1 --color GREEN
"""
import sys, math, argparse
from reportlab.pdfgen import canvas
from reportlab.lib.colors import CMYKColor

CM = 28.346456692913385
MM = CM / 10.0
WHITE = CMYKColor(0, 0, 0, 0)


def parse_color(s):
    s = s.strip().upper()
    if s in ("K100", "BLACK"):
        return CMYKColor(0, 0, 0, 1)
    if s == "GREEN":  # 惜食品牌綠 RGB(7,153,61) 近似 CMYK
        return CMYKColor(0.95, 0.0, 0.60, 0.40)
    parts = [float(x) / 100 for x in s.split(",")]
    return CMYKColor(*parts)


def hexagon(path, side_cm, stroke, margin, color):
    s = side_cm * CM
    w, h = 2 * s, math.sqrt(3) * s
    W, H = w + 2 * margin, h + 2 * margin
    cx, cy = W / 2, H / 2
    c = canvas.Canvas(path, pagesize=(W, H))
    c.setFillColor(WHITE)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    V = [
        (cx - s, cy),
        (cx - s / 2, cy + h / 2),
        (cx + s / 2, cy + h / 2),
        (cx + s, cy),
        (cx + s / 2, cy - h / 2),
        (cx - s / 2, cy - h / 2),
    ]
    p = c.beginPath()
    p.moveTo(*V[0])
    for v in V[1:]:
        p.lineTo(*v)
    p.close()
    c.setStrokeColor(color)
    c.setLineWidth(stroke)
    c.setLineJoin(1)
    c.drawPath(p, stroke=1, fill=0)
    c.showPage()
    c.save()
    return W / CM, H / CM


def circle(path, dia_cm, stroke, margin, color):
    d = dia_cm * CM
    W = d + 2 * margin
    c = canvas.Canvas(path, pagesize=(W, W))
    c.setFillColor(WHITE)
    c.rect(0, 0, W, W, fill=1, stroke=0)
    c.setStrokeColor(color)
    c.setLineWidth(stroke)
    c.circle(W / 2, W / 2, d / 2, stroke=1, fill=0)
    c.showPage()
    c.save()
    return W / CM, W / CM


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--hex", default="")
    ap.add_argument("--circle", default="")
    ap.add_argument("--stroke-mm", type=float, default=2.0)
    ap.add_argument("--margin-cm", type=float, default=1.0)
    ap.add_argument("--color", default="K100")
    a = ap.parse_args()
    stroke = a.stroke_mm * MM
    margin = a.margin_cm * CM
    color = parse_color(a.color)
    for side in [float(x) for x in a.hex.split(",") if x.strip()]:
        W, H = hexagon(
            f"{a.out}/六邊形邊框_邊長{side:g}cm_白底.ai", side, stroke, margin, color
        )
        print(f"六邊形 邊長{side:g}cm  畫板 {W:.2f}x{H:.2f}cm")
    for dia in [float(x) for x in a.circle.split(",") if x.strip()]:
        W, H = circle(
            f"{a.out}/圓形邊框_直徑{dia:g}cm_白底.ai", dia, stroke, margin, color
        )
        print(f"圓形 直徑{dia:g}cm  畫板 {W:.2f}x{H:.2f}cm")


if __name__ == "__main__":
    main()
