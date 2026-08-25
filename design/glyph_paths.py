"""把 TrueType 字形轉成 PDF 路徑運算子（字體轉外框用）。

fontTools 的 qCurveTo 是二次貝茲，PDF 只有三次，需要轉換；
連續離曲線點之間的隱含在曲線點也要自己補。
"""

from fontTools.ttLib import TTFont, TTCollection
from fontTools.pens.recordingPen import DecomposingRecordingPen


def load_face(path, index=0):
    if path.lower().endswith(".ttc"):
        return TTCollection(path).fonts[index]
    return TTFont(path)


def _quad_to_cubic(p0, q, p1):
    c1 = (p0[0] + 2.0 / 3 * (q[0] - p0[0]), p0[1] + 2.0 / 3 * (q[1] - p0[1]))
    c2 = (p1[0] + 2.0 / 3 * (q[0] - p1[0]), p1[1] + 2.0 / 3 * (q[1] - p1[1]))
    return c1, c2


def glyph_contours(face, char):
    """回傳 [(cmd, pts...), ...]，座標為字體單位。"""
    cmap = face.getBestCmap()
    gname = cmap[ord(char)]
    gs = face.getGlyphSet()
    pen = DecomposingRecordingPen(gs)
    gs[gname].draw(pen)

    out = []
    cur = None
    start = None
    for op, args in pen.value:
        if op == "moveTo":
            cur = args[0]
            start = cur
            out.append(("m", cur))
        elif op == "lineTo":
            cur = args[0]
            out.append(("l", cur))
        elif op == "curveTo":
            out.append(("c", args[0], args[1], args[2]))
            cur = args[-1]
        elif op == "qCurveTo":
            pts = list(args)
            if pts[-1] is None:
                # 全離曲線的封閉輪廓：以首尾中點當起點
                offs = pts[:-1]
                mid = ((offs[0][0] + offs[-1][0]) / 2.0, (offs[0][1] + offs[-1][1]) / 2.0)
                cur = mid
                start = mid
                out.append(("m", mid))
                pts = offs + [mid]
            on_end = pts[-1]
            offs = pts[:-1]
            for i, q in enumerate(offs):
                if i < len(offs) - 1:
                    nxt = offs[i + 1]
                    end = ((q[0] + nxt[0]) / 2.0, (q[1] + nxt[1]) / 2.0)
                else:
                    end = on_end
                c1, c2 = _quad_to_cubic(cur, q, end)
                out.append(("c", c1, c2, end))
                cur = end
        elif op == "closePath":
            out.append(("h",))
            cur = start
        elif op == "endPath":
            pass
    return out


def advance(face, char):
    cmap = face.getBestCmap()
    return face["hmtx"][cmap[ord(char)]][0]


def upem(face):
    return face["head"].unitsPerEm


def path_ops(contours, scale, dx, dy, prec=4):
    """字體單位 -> 使用者單位（scale 已含 1/upem），輸出 PDF 路徑字串。"""
    f = "%%.%df" % prec
    def P(p):
        return (f % (dx + p[0] * scale)) + " " + (f % (dy + p[1] * scale))
    ops = []
    for seg in contours:
        if seg[0] == "m":
            ops.append(P(seg[1]) + " m")
        elif seg[0] == "l":
            ops.append(P(seg[1]) + " l")
        elif seg[0] == "c":
            ops.append(P(seg[1]) + " " + P(seg[2]) + " " + P(seg[3]) + " c")
        elif seg[0] == "h":
            ops.append("h")
    return "\n".join(ops)


def ink_bbox(contours, scale=1.0):
    xs, ys = [], []
    for seg in contours:
        for p in seg[1:]:
            xs.append(p[0] * scale)
            ys.append(p[1] * scale)
    return min(xs), min(ys), max(xs), max(ys)
