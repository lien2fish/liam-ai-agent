#!/usr/bin/env python3
"""把素材裡的手寫配方紙用頻道頭像蓋掉（追蹤式，不是固定位置）。

為什麼要追蹤：鏡頭是手持會移動的，固定位置的遮擋只有第一格會蓋對。
2026-09-12 發現舊的 IMG_4703_遮擋版.MOV 就是固定橫幅，而且只遮了 229.5~305.5，
實際上那張紙在 4703 的 98.5~534.5 都在檯面上。

用法：
    track  <src> <t0> <t1> <x,y,w,h>[@t] ...   追蹤並輸出逐格座標 JSON
    check  <track.json> [每幾秒抽一格]          產出覆核用的接觸表（一定要看）
    render <src> <track.json> <out>            套頭像貼紙重新編碼

座標一律是「代理片」的 540 寬座標，render 時自動換算回原尺寸。
錨點可以給多個，格式 `x,y,w,h@秒數`；每個錨點會重新初始化追蹤器，
用來救鏡頭大幅移動之後追丟的段落。

⚠️ cv2 的 MIL 追蹤器**永遠回傳 True**，「lost 0」不代表沒追丟。
判斷只能看 check 產出的畫面，不要相信回傳值。
"""
import json
import os
import subprocess
import sys

import cv2
from PIL import Image, ImageDraw

PROXY_W = 540
AVATAR = os.path.join(os.path.dirname(__file__), "..", "dessert", "avatar_round.png")


def proxy(src, t0, t1, path):
    if os.path.exists(path):
        return path
    subprocess.run(
        # fmt: off
        ["ffmpeg", "-v", "error", "-ss", str(t0), "-t", str(round(t1 - t0, 3)),
         "-i", src, "-vf", f"scale={PROXY_W}:-1", "-an",
         "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", path, "-y"],
        # fmt: on
        check=True,
    )
    return path


def track(src, t0, t1, anchors, out):
    """anchors = [(秒數, (x, y, w, h)), ...]，第一個必須落在 t0。"""
    pv = out.replace(".json", ".proxy.mp4")
    proxy(src, t0, t1, pv)
    cap = cv2.VideoCapture(pv)
    fps = cap.get(cv2.CAP_PROP_FPS)
    marks = {int(round((t - t0) * fps)): box for t, box in anchors}

    boxes, tr, i = [], None, 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i in marks:
            tr = cv2.TrackerMIL_create()
            tr.init(frame, marks[i])
            box = marks[i]
        elif tr is not None:
            _, b = tr.update(frame)
            box = tuple(float(v) for v in b)
        else:
            box = None
        boxes.append(None if box is None else [round(v, 1) for v in box])
        i += 1
    cap.release()

    data = {
        "src": src,
        "t0": t0,
        "t1": t1,
        "fps": fps,
        "proxy_w": PROXY_W,
        "anchors": [[t, list(b)] for t, b in anchors],
        "boxes": boxes,
    }
    json.dump(data, open(out, "w"))
    print(f"✅ {out}  {len(boxes)} 格 @ {fps:.2f}fps　錨點 {len(anchors)} 個")
    print("⚠️ 一定要跑 check 看畫面——MIL 追丟不會報錯")
    return data


def track_flow(src, t0, t1, anchors, out, win=2.2):
    """光流＋單應矩陣傳遞。檯面是平面，紙躺在上面，
    所以用「框周圍的特徵點怎麼動」去推框怎麼動，比一般物件追蹤器穩得多。

    win＝取框的幾倍範圍當特徵來源（太小點不夠，太大會吃到走過鏡前的人）。
    回傳的 boxes 另附每格存活的點數，太少就是追丟了，check 會標出來。
    """
    import numpy as np

    pv = out.replace(".json", ".proxy.mp4")
    proxy(src, t0, t1, pv)
    cap = cv2.VideoCapture(pv)
    fps = cap.get(cv2.CAP_PROP_FPS)
    marks = {int(round((t - t0) * fps)): box for t, box in anchors}

    def seed(gray, box):
        x, y, w, h = box
        cx, cy = x + w / 2, y + h / 2
        rw, rh = w * win / 2, h * win / 2
        x0, y0 = max(0, int(cx - rw)), max(0, int(cy - rh))
        x1, y1 = min(gray.shape[1], int(cx + rw)), min(gray.shape[0], int(cy + rh))
        roi = gray[y0:y1, x0:x1]
        pts = cv2.goodFeaturesToTrack(roi, 220, 0.01, 4)
        if pts is None:
            return None
        pts = pts.reshape(-1, 2) + np.float32([x0, y0])
        return pts.reshape(-1, 1, 2)

    grays = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        grays.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
    cap.release()

    def step(prev_gray, gray, box, pts):
        """用 prev→gray 的特徵位移推 box 的新位置，回傳 (box, pts)。"""
        nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev_gray, gray, pts, None,
                                              winSize=(21, 21), maxLevel=3)
        back, st2, _ = cv2.calcOpticalFlowPyrLK(gray, prev_gray, nxt, None,
                                                winSize=(21, 21), maxLevel=3)
        good = (st.ravel() == 1) & (st2.ravel() == 1)
        good &= np.linalg.norm(pts.reshape(-1, 2) - back.reshape(-1, 2), axis=1) < 1.5
        a, b = pts[good], nxt[good]
        if len(a) >= 8:
            M, _ = cv2.estimateAffinePartial2D(a, b, method=cv2.RANSAC,
                                               ransacReprojThreshold=2.0)
            if M is not None:
                c = np.float32([[box[0] + box[2] / 2, box[1] + box[3] / 2]])
                nc = cv2.transform(c.reshape(1, -1, 2), M).reshape(2)
                sc = float(np.hypot(M[0, 0], M[0, 1]))
                box = [nc[0] - box[2] * sc / 2, nc[1] - box[3] * sc / 2,
                       box[2] * sc, box[3] * sc]
        return box, seed(gray, box)

    n = len(grays)
    boxes = [None] * n
    live = [0] * n

    # 第一個錨點之前的畫格：反向推回去（不然 t0 到第一個錨點之間會沒有遮擋）
    first = min(marks) if marks else 0
    if first > 0:
        box = [float(v) for v in marks[first]]
        pts = seed(grays[first], box)
        for i in range(first - 1, -1, -1):
            if pts is None or len(pts) < 8:
                break
            box, pts = step(grays[i + 1], grays[i], box, pts)
            boxes[i] = [round(float(v), 1) for v in box]
            live[i] = 0 if pts is None else int(len(pts))

    prev_gray, pts, box = None, None, None
    for i in range(n):
        gray = grays[i]
        if i in marks:
            box = [float(v) for v in marks[i]]
            pts = seed(gray, box)
        elif box is not None and pts is not None and len(pts) >= 8:
            box, pts = step(prev_gray, gray, box, pts)   # 每格重新撒點，點被遮掉也不會死光
        if box is not None:
            boxes[i] = [round(float(v), 1) for v in box]
            live[i] = 0 if pts is None else int(len(pts))
        prev_gray = gray

    data = {"src": src, "t0": t0, "t1": t1, "fps": fps, "proxy_w": PROXY_W,
            "anchors": [[t, list(b)] for t, b in anchors], "boxes": boxes, "live": live}
    json.dump(data, open(out, "w"))
    thin = sum(1 for n in live if n < 30)
    print(f"✅ {out}  {len(boxes)} 格 @ {fps:.2f}fps　錨點 {len(anchors)} 個")
    print(f"　 特徵點不足(<30)的格數：{thin}（多半是被人擋住，看 check 確認）")
    return data


def check(track_json, every=2.0, cols=6, tile=320):
    d = json.load(open(track_json))
    cap = cv2.VideoCapture(track_json.replace(".json", ".proxy.mp4"))
    fps, t0 = d["fps"], d["t0"]
    step = max(1, int(round(every * fps)))
    tiles, i = [], 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if i % step == 0:
            b = d["boxes"][i]
            if b:
                cv2.rectangle(
                    f,
                    (int(b[0]), int(b[1])),
                    (int(b[0] + b[2]), int(b[1] + b[3])),
                    (0, 0, 255),
                    3,
                )
            cv2.putText(
                f,
                f"{t0 + i / fps:.1f}",
                (6, 34),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 255),
                2,
            )
            h = int(tile * f.shape[0] / f.shape[1])
            tiles.append(
                Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)).resize((tile, h))
            )
        i += 1
    cap.release()
    th = tiles[0].size[1]
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (tile * cols, th * rows), "black")
    for j, im in enumerate(tiles):
        sheet.paste(im, ((j % cols) * tile, (j // cols) * th))
    out = track_json.replace(".json", "_check.jpg")
    sheet.save(out, quality=88)
    print(f"✅ {out}  {len(tiles)} 格")
    return out


def sticker(w, h, path):
    """產生跟紙張同比例的圓角貼紙（圓形會露出矩形紙的四個角）。"""
    from PIL import ImageFilter

    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    r = min(w, h) // 4
    d.rounded_rectangle(
        [0, 0, w - 1, h - 1],
        r,
        fill=(250, 243, 233, 255),
        outline=(199, 143, 60, 255),
        width=max(3, min(w, h) // 26),
    )
    face = Image.open(os.path.abspath(AVATAR)).convert("RGBA")
    side = int(min(w, h) * 0.82)
    face = face.resize((side, side), Image.LANCZOS)
    card.alpha_composite(face, ((w - side) // 2, (h - side) // 2))
    # 邊緣稍微柔化，疊在畫面上比較不像貼圖
    card.putalpha(card.getchannel("A").filter(ImageFilter.GaussianBlur(1.2)))
    card.save(path)
    return path


def render(src, track_json, out, pad=1.45, size=None, cmd_path=None):
    """pad＝貼紙比追蹤框大多少倍；size＝直接指定貼紙的 proxy 尺寸 "w,h"。"""
    d = json.load(open(track_json))
    probe = (
        subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "csv=p=0",
                src,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        .stdout.strip()
        .split(",")
    )
    # ffprobe 給的是旋轉前的尺寸，直式素材要對調
    w, h = int(probe[0]), int(probe[1])
    if w > h:
        w, h = h, w
    scale = w / d["proxy_w"]

    fps, t0 = d["fps"], d["t0"]
    cmd_path = cmd_path or track_json.replace(".json", ".cmd")
    lines, ws, hs = [], [], []
    for i, b in enumerate(d["boxes"]):
        if not b:
            continue
        lines.append(
            (t0 + i / fps, (b[0] + b[2] / 2) * scale, (b[1] + b[3] / 2) * scale)
        )
        ws.append(b[2])
        hs.append(b[3])
    # 換錨點時追蹤框會跳一下，滑動平均把跳動與逐格抖動抹平（貼紙夠大不怕這點延遲）
    if len(lines) > 5:
        sm = []
        for i in range(len(lines)):
            win = lines[max(0, i - 2) : i + 3]
            sm.append(
                (
                    lines[i][0],
                    sum(p[1] for p in win) / len(win),
                    sum(p[2] for p in win) / len(win),
                )
            )
        lines = sm

    if size:
        sw, sh = (int(round(float(v) * scale)) for v in size.split(","))
    else:
        # 取最大不取平均：MIL 的框不會隨鏡頭遠近縮放，用平均會在鏡頭推近時蓋不滿
        sw, sh = round(max(ws) * scale * pad), round(max(hs) * scale * pad)
    sw += sw % 2
    sh += sh % 2

    st_path = track_json.replace(".json", "_sticker.png")
    sticker(sw, sh, st_path)

    cmds = [
        f"{t:.3f} overlay@paper x {round(cx - sw / 2)}, overlay@paper y {round(cy - sh / 2)};"
        for t, cx, cy in lines
    ]
    open(cmd_path, "w").write("\n".join(cmds) + "\n")

    # 有些段落紙根本不在鏡頭裡（boxes 是 None），那時候不能讓貼紙留在畫面上，
    # 所以 enable 要是「每一段連續有框的區間」的聯集，不是頭尾一條。
    runs, start, prev = [], None, None
    for i, b in enumerate(d["boxes"]):
        if b and start is None:
            start = i
        elif not b and start is not None:
            runs.append((start, prev))
            start = None
        if b:
            prev = i
    if start is not None:
        runs.append((start, prev))
    en = "+".join(
        f"between(t,{t0 + a / fps:.3f},{t0 + (b + 1) / fps:.3f})" for a, b in runs
    )
    t_on, t_off = lines[0][0], lines[-1][0] + 1 / fps
    fc = (
        f"[0:v]sendcmd=f='{cmd_path}'[m];"
        f"[m][1:v]overlay@paper=x=-9999:y=-9999:enable='{en}'[v]"
    )
    subprocess.run(
        # fmt: off
        ["ffmpeg", "-v", "error", "-stats", "-i", src, "-i", st_path,
         "-filter_complex", fc, "-map", "[v]", "-map", "0:a?",
         "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-pix_fmt", "yuv420p", "-color_range", "tv",
         "-c:a", "copy", "-movflags", "+faststart", out, "-y"],
        # fmt: on
        check=True,
    )
    print(f"✅ {out}　貼紙 {sw}x{sh}px　遮擋 {len(runs)} 段，{t_on:.1f}~{t_off:.1f}s")


def parse_anchor(s, default_t):
    body, _, at = s.partition("@")
    # cv2 的 Tracker.init 只吃整數框，給 float 會在 overload 解析就掛掉
    x, y, w, h = (int(round(float(v))) for v in body.split(","))
    return (float(at) if at else default_t, (x, y, w, h))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode in ("track", "flow"):
        src, t0, t1 = sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
        out = sys.argv[5]
        anchors = sorted(parse_anchor(a, t0) for a in sys.argv[6:])
        (track if mode == "track" else track_flow)(src, t0, t1, anchors, out)
    elif mode == "check":
        check(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 2.0)
    elif mode == "merge":
        out = sys.argv[2]
        parts = [json.load(open(f)) for f in sys.argv[3:]]
        fps = parts[0]["fps"]
        t0 = min(p["t0"] for p in parts)
        t1 = max(p["t1"] for p in parts)
        n = int(round((t1 - t0) * fps))
        boxes = [None] * n
        for pt in parts:
            off = int(round((pt["t0"] - t0) * fps))
            for k, b in enumerate(pt["boxes"]):
                if b and 0 <= off + k < n:
                    boxes[off + k] = b
        json.dump({"src": parts[0]["src"], "t0": t0, "t1": t1, "fps": fps,
                   "proxy_w": parts[0]["proxy_w"], "boxes": boxes}, open(out, "w"))
        print(f"✅ {out}  {n} 格，有框 {sum(1 for b in boxes if b)} 格")
    elif mode == "render":
        size = sys.argv[5] if len(sys.argv) > 5 else None
        render(sys.argv[2], sys.argv[3], sys.argv[4], size=size)
    else:
        sys.exit(__doc__)
