#!/usr/bin/env python3
"""把圈選、箭頭、標籤、資訊卡疊到已經剪好的成品上。

用法：
    python3 tools/overlay_fx.py <config.json> --check   先驗，不算圖
    python3 tools/overlay_fx.py <config.json>           產出

config：
{
  "video": "成品/xxx.mp4",
  "out":   "成品/xxx_疊圖.mp4",          # 省略＝原檔名加 _疊圖
  "items": [
    {"type": "circle", "t": [3.0, 5.5], "xy": [540, 900], "r": 180, "label": "背殼這裡"},
    {"type": "arrow",  "t": [6.0, 8.0], "from": [300, 1500], "to": [520, 1150], "label": "鰓"},
    {"type": "label",  "t": [9.0, 11.0], "xy": [540, 700], "text": "蝦頭"},
    {"type": "card",   "t": [12.0, 14.0], "title": "一斤幾顆",
                       "lines": ["4 顆 ＝ 長了 3 年", "8 顆 ＝ 長了 1 年"]}
  ]
}

為什麼不寫進 reel_maker：那支明訂不可改，而且這裡是「成品再加工」，
失敗只要重跑、不會動到母帶。疊圖層是先用 Pillow 畫成透明 PNG，再交給 ffmpeg overlay。

⚠️ PNG 是無限長的輸入，輸出一定要加 `-shortest`，否則 ffmpeg 不會停（第一次實測就跑到 226MB 還在編）。
⚠️ PNG 一定要 `-loop 1 -framerate <fps>` 讀進來。單幀輸入在多層 overlay 串接下
撐不過整條時間軸，後段的 enable 會全部落空（36 歲生日影片踩過）。
⚠️ 輸出編碼參數與 reel_maker 的正片一致（yuv420p／High@4.0／24fps／faststart），
不一致的話 YouTube 會在「處理中」跑完後才說無法上傳。音軌直接 copy，不重編。
"""
import json
import os
import subprocess
import sys

ZHF = "/System/Library/Fonts/STHeiti Medium.ttc"
ORANGE = (245, 156, 48)  # 與字幕高光同色（ASS 的 &H00309CF5 換成 RGB）
WHITE = (255, 255, 255)
INK = (18, 18, 18)
FADE = 0.15
MARGIN = 60  # 畫面邊緣安全距離
MAX_ITEMS = 20

fix_glyph = lambda t: t.replace("・", "·").replace("／", "/")


def probe(video):
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            video,
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    d = json.loads(out)
    s = d["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return (
        s["width"],
        s["height"],
        float(d["format"]["duration"]),
        float(num) / float(den),
    )


def font(size):
    from PIL import ImageFont

    return ImageFont.truetype(ZHF, size)


def text_size(draw, tx, f, ls):
    return sum(draw.textlength(c, font=f) + ls for c in tx) - ls


def draw_text(draw, xy, tx, f, ls, fill, anchor_center=True):
    """逐字畫，才能控字距；描邊讓字在任何畫面上都讀得到。"""
    x, y = xy
    if anchor_center:
        x -= text_size(draw, tx, f, ls) / 2
    for c in tx:
        draw.text((x, y), c, font=f, fill=fill, stroke_width=6, stroke_fill=INK)
        x += draw.textlength(c, font=f) + ls


def layer_circle(img, it, W, H):
    from PIL import ImageDraw

    d = ImageDraw.Draw(img)
    x, y = it["xy"]
    r = it.get("r", 160)
    for w, col in ((14, INK + (170,)), (8, ORANGE + (255,))):
        d.ellipse([x - r, y - r, x + r, y + r], outline=col, width=w)
    if it.get("label"):
        f = font(it.get("fs", 56))
        draw_text(
            d,
            (x, y - r - it.get("fs", 56) - 26),
            fix_glyph(it["label"]),
            f,
            it.get("fs", 56) * 0.05,
            ORANGE + (255,),
        )


def layer_arrow(img, it, W, H):
    import math

    from PIL import ImageDraw

    d = ImageDraw.Draw(img)
    x0, y0 = it["from"]
    x1, y1 = it["to"]
    ang = math.atan2(y1 - y0, x1 - x0)
    head = it.get("head", 46)
    bx, by = x1 - head * math.cos(ang), y1 - head * math.sin(ang)
    for w, col in ((18, INK + (170,)), (10, ORANGE + (255,))):
        d.line([(x0, y0), (bx, by)], fill=col, width=w)
    wing = head * 0.55
    pts = [
        (x1, y1),
        (bx - wing * math.sin(ang), by + wing * math.cos(ang)),
        (bx + wing * math.sin(ang), by - wing * math.cos(ang)),
    ]
    d.polygon(pts, fill=ORANGE + (255,), outline=INK + (200,))
    if it.get("label"):
        fs = it.get("fs", 52)
        draw_text(
            d,
            (x0, y0 + 18),
            fix_glyph(it["label"]),
            font(fs),
            fs * 0.05,
            ORANGE + (255,),
        )


def layer_label(img, it, W, H):
    from PIL import ImageDraw

    d = ImageDraw.Draw(img)
    fs = it.get("fs", 64)
    draw_text(
        d,
        tuple(it["xy"]),
        fix_glyph(it["text"]),
        font(fs),
        fs * 0.05,
        tuple(it.get("color", WHITE)) + (255,),
    )


def layer_card(img, it, W, H):
    """資訊卡：深底半透明，標題橘黃、內容白字。範例影片講法規與數字時就是這樣插一張。"""
    from PIL import Image, ImageDraw

    lines = [fix_glyph(x) for x in it.get("lines", [])]
    title = fix_glyph(it.get("title", ""))
    t_fs, l_fs = it.get("title_fs", 64), it.get("fs", 52)
    pad, gap = 44, 22
    probe_img = Image.new("RGBA", (10, 10))
    pd = ImageDraw.Draw(probe_img)
    tf, lf = font(t_fs), font(l_fs)
    widths = ([text_size(pd, title, tf, t_fs * 0.05)] if title else []) + [
        text_size(pd, x, lf, l_fs * 0.05) for x in lines
    ]
    bw = min(max(widths) + pad * 2, W - MARGIN * 2)
    bh = (
        pad * 2
        + (t_fs + gap if title else 0)
        + len(lines) * (l_fs + gap)
        - (gap if lines else 0)
    )
    cx = it.get("cx", W // 2)
    top = it.get("top", int(H * 0.30))
    box = Image.new("RGBA", (int(bw), int(bh)), (16, 22, 26, 225))
    bd = ImageDraw.Draw(box)
    bd.rectangle([0, 0, bw - 1, bh - 1], outline=ORANGE + (255,), width=4)
    y = pad
    if title:
        draw_text(bd, (bw / 2, y), title, tf, t_fs * 0.05, ORANGE + (255,))
        y += t_fs + gap
    for ln in lines:
        draw_text(bd, (bw / 2, y), ln, lf, l_fs * 0.05, WHITE + (255,))
        y += l_fs + gap
    img.alpha_composite(box, (int(cx - bw / 2), int(top)))


LAYERS = {
    "circle": layer_circle,
    "arrow": layer_arrow,
    "label": layer_label,
    "card": layer_card,
}


def check(cfg, W, H, dur):
    errs = []
    items = cfg.get("items", [])
    if not items:
        errs.append("items 是空的")
    if len(items) > MAX_ITEMS:
        errs.append(f"item 超過 {MAX_ITEMS} 個（{len(items)}），overlay 串太長會很慢")
    if not os.path.exists(ZHF):
        errs.append(f"找不到字型 {ZHF}")
    for i, it in enumerate(items, 1):
        tag = f"item{i}({it.get('type')})"
        if it.get("type") not in LAYERS:
            errs.append(f"{tag} type 不認得，只接受 {'／'.join(LAYERS)}")
            continue
        t = it.get("t")
        if not (isinstance(t, list) and len(t) == 2 and t[1] > t[0]):
            errs.append(f"{tag} 的 t 要是 [起, 迄] 且迄 > 起")
            continue
        if t[1] > dur:
            errs.append(f"{tag} 迄 {t[1]}s 超過影片長度 {dur:.1f}s，這層不會出現")
        if t[1] - t[0] < 0.8:
            errs.append(f"{tag} 只有 {t[1]-t[0]:.2f} 秒，扣掉淡入淡出幾乎看不到")
        pts = []
        if it["type"] == "circle":
            x, y, r = it["xy"][0], it["xy"][1], it.get("r", 160)
            pts = [(x - r, y - r), (x + r, y + r)]
        elif it["type"] == "arrow":
            pts = [tuple(it["from"]), tuple(it["to"])]
        elif it["type"] == "label":
            pts = [tuple(it["xy"])]
        for x, y in pts:
            if not (0 <= x <= W and 0 <= y <= H):
                errs.append(f"{tag} 座標 ({x},{y}) 超出畫面 {W}x{H}")
        if it["type"] == "circle" and (
            it["xy"][1] - it.get("r", 160) < MARGIN
            or it["xy"][1] + it.get("r", 160) > H - MARGIN
        ):
            errs.append(f"{tag} 圈圈貼到畫面邊緣")
    # Shorts 會從橫式中間裁直式，放太邊邊的東西會被裁掉
    return errs


def build(cfg, path):
    from PIL import Image

    video = cfg["video"]
    W, H, dur, fps = probe(video)
    out = cfg.get("out") or os.path.splitext(video)[0] + "_疊圖.mp4"
    tmp = os.path.join(os.path.dirname(os.path.abspath(path)), ".overlay_tmp")
    os.makedirs(tmp, exist_ok=True)

    pngs = []
    for i, it in enumerate(cfg["items"], 1):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        LAYERS[it["type"]](img, it, W, H)
        p = os.path.join(tmp, f"fx_{i:02d}.png")
        img.save(p)
        pngs.append(p)

    cmd = ["ffmpeg", "-y", "-i", video]
    for p in pngs:
        cmd += ["-loop", "1", "-framerate", f"{fps:.6f}", "-i", p]
    chain, last = [], "0:v"
    for i, it in enumerate(cfg["items"], 1):
        s, e = it["t"]
        d = min(FADE, (e - s) / 2)
        chain.append(
            f"[{i}:v]format=rgba,fade=t=in:st={s:.2f}:d={d:.2f}:alpha=1,"
            f"fade=t=out:st={max(s, e-d):.2f}:d={d:.2f}:alpha=1[o{i}]"
        )
        tag = f"v{i}" if i < len(cfg["items"]) else "vout"
        chain.append(
            f"[{last}][o{i}]overlay=0:0:enable='between(t,{s:.2f},{e:.2f})'[{tag}]"
        )
        last = tag
    cmd += [
        "-filter_complex",
        ";".join(chain),
        "-map",
        "[vout]",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "high",
        "-level",
        "4.0",
        "-r",
        f"{fps:.6f}",
        "-c:a",
        "copy",
        # PNG 是 -loop 1 的無限輸入，不加 -shortest 的話 ffmpeg 會一直編下去不會停
        "-shortest",
        "-movflags",
        "+faststart",
        out,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    for p in pngs:
        os.remove(p)
    if r.returncode:
        raise SystemExit("❌ ffmpeg 失敗：\n" + r.stderr[-1200:])
    print(f"✅ {out}")
    return out


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    path = sys.argv[1]
    cfg = json.load(open(path, encoding="utf-8"))
    if not os.path.exists(cfg["video"]):
        raise SystemExit(f"❌ 找不到影片：{cfg['video']}")
    W, H, dur, fps = probe(cfg["video"])
    errs = check(cfg, W, H, dur)
    print(f"影片 {W}x{H} {dur:.1f}s {fps:.2f}fps｜item {len(cfg.get('items', []))} 個")
    for e in errs:
        print("  ❌", e)
    if errs:
        raise SystemExit(1)
    print("  ✅ 檢查通過")
    if "--check" in sys.argv:
        return
    build(cfg, path)


if __name__ == "__main__":
    main()
