#!/usr/bin/env python3
"""從長片成品切直式 Shorts。

用法：python3 finance_shorts/make_shorts.py tw-01 [a b ...]

設定寫在 finance_shorts/<集>/shorts.json：
    {"shorts": [{"id": "a", "title": ["第一行", "第二行"], "lines": [6, 19, 20, 96]}]}
lines 是句號（1 起算），不連續也可以。每句從它的開頭切到下一句開頭。
開場鉤子：{"hook": {"say": "餵給克隆聲音的字", "text": "字幕", "visual": 句號}}，
畫面借 visual 那句的開頭、配同一首背景音樂。
句首要去掉幾個字（例如脫離上下文的「第二，」）就寫 {"n": 19, "skip": 0.75, "text": "新字幕"}。
版面：上標題、中間整張 16:9 畫面、下方放大字幕、背景是同一段畫面模糊放大。
"""
import hashlib, json, re, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
W, H = 1080, 1920
FRAME_Y = 700
TAIL = 0.3  # 旁白結束後最多留幾秒
CROP_H = 880  # 裁掉原片底部的小字幕、頁碼、進度條
FRAME_H = round(W * CROP_H / 1920 / 2) * 2
INK, GOLD = (243, 241, 234), (217, 178, 106)


def line_starts(ep_dir, speed):
    html = (ep_dir / "index.html").read_text()
    starts = {
        int(n): float(s)
        for s, n in re.findall(
            r'<audio[^>]*data-start="([0-9.]+)"[^>]*src="audio/l(\d+)\.mp3"', html
        )
    }
    return {i: s / speed for i, s in starts.items()}


def line_ends(ep_dir, speed):
    """每句旁白結束的秒數。舊版產線每頁畫面比旁白長，切到下一句開頭會夾到空白。"""
    html = (ep_dir / "index.html").read_text()
    out = {}
    for tag in re.findall(r'<audio[^>]*src="audio/l\d+\.mp3"[^>]*>', html):
        n = int(re.search(r"audio/l(\d+)\.mp3", tag).group(1))
        st = float(re.search(r'data-start="([0-9.]+)"', tag).group(1))
        du = float(re.search(r'data-duration="([0-9.]+)"', tag).group(1))
        out[n] = (st + min(du, speech_end(ep_dir / "audio" / f"l{n}.mp3"))) / speed
    return out


def speech_end(path):
    """音檔裡人聲最後結束的秒數（克隆聲音有時會在句尾多吐一兩秒空白）。"""
    if not path.exists():
        return float("inf")
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af",
                          "silencedetect=noise=-45dB:d=0.3", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    total = duration(path)
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", log)]
    ends += [total] * (len(starts) - len(ends))
    if not starts or ends[-1] < total - 0.2:
        return total
    i = len(starts) - 1
    while i > 0 and starts[i] - ends[i - 1] < 0.2:  # 兩段空白中間不到 0.2 秒的聲音當雜訊
        i -= 1
    return starts[i]


def asset_windows(ep_dir, speed):
    """長片時間軸上每個畫面素材出現的區間（換算成成品秒數）。"""
    html = (ep_dir / "index.html").read_text()
    pages = {
        pid: (float(a), float(d))
        for pid, a, d in re.findall(
            r'<section id="(p\d+)"[^>]*data-start="([0-9.]+)" data-duration="([0-9.]+)"', html
        )
    }
    out = []
    tags = [t for t in re.findall(r"<(?:video|img)[^>]*>", html) if "shared/bg/" in t or "shared/broll/" in t]
    for tag in tags:
        m = re.search(r"""src=["']shared/((?:bg|broll)/[^"']+)\.\w+["']""", tag)
        st = re.search(r'data-start="([0-9.]+)"', tag)
        du = re.search(r'data-duration="([0-9.]+)"', tag)
        pg = re.search(r'id="(p\d+)-', tag)
        if m and st and du:
            a, d = float(st.group(1)), float(du.group(1))
        elif m and pg and pg.group(1) in pages:  # 舊版：圖片沒有時間，時間在外層 <section id="pN">
            a, d = pages[pg.group(1)]
        else:
            continue
        out.append((m.group(1), a / speed, (a + d) / speed))
    if len(out) != len(tags):
        raise SystemExit(f"素材標籤 {len(tags)} 個只解析到 {len(out)} 個，授權清單會漏列，先修解析")
    return out


def duration(path):
    out = subprocess.run(
        ["ffmpeg", "-i", str(path)], capture_output=True, text=True
    ).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def wrap(text, font, width, draw):
    rows, cur = [], ""
    for ch in re.findall(r"[0-9A-Za-z][0-9A-Za-z,.%]*|.", text):
        if draw.textlength(cur + ch, font=font) > width and cur:
            if ch in "，。、；：？！）」』":
                cur += ch
                rows.append(cur)
                cur = ""
                continue
            rows.append(cur)
            cur = ""
        cur += ch
    if cur:
        rows.append(cur)
    return rows


def overlay_png(title, text, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    tf = ImageFont.truetype(FONT, 92)
    y = 330
    for i, row in enumerate(title):
        tw = d.textlength(row, font=tf)
        d.text(
            ((W - tw) / 2, y),
            row,
            font=tf,
            fill=GOLD if i == 0 else INK,
            stroke_width=4,
            stroke_fill=(0, 0, 0),
        )
        y += 120
    sf = ImageFont.truetype(FONT, 62)
    rows = wrap(text, sf, W - 140, d)
    if len(rows) > 5:
        raise SystemExit(f"字幕超過 5 行會超出畫面，請縮短：{text}")
    lh = 86
    top = FRAME_Y + FRAME_H + 70
    d.rounded_rectangle(
        (40, top - 30, W - 40, top + lh * len(rows) + 20), 24, fill=(7, 13, 26, 190)
    )
    for i, row in enumerate(rows):
        tw = d.textlength(row, font=sf)
        d.text(((W - tw) / 2, top + i * lh), row, font=sf, fill=INK)
    img.save(path)


ENC = ["-r", "30", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
       "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
VIDEO_FC = (
    f"[0:v]crop=1920:{CROP_H}:0:0,split[a][b];"
    f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
    "boxblur=30:4,eq=brightness=-0.28[bg];"
    f"[b]scale={W}:-2[fg];[bg][fg]overlay=0:{FRAME_Y}[v1];"
    "[v1][1:v]overlay=0:0,format=yuv420p[v];"
)


def hook_voice(ep_dir, say, speed):
    """Shorts 專用開場句：克隆聲音，依片子倍速加快。音檔留在 audio/（不進版控）。"""
    key = hashlib.sha1(f"{say}|{speed}".encode()).hexdigest()[:10]
    out = ep_dir / "audio" / f"hook_{key}.wav"
    if not out.exists():
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["python3", str(Path.home() / "聲音素材/tts/say.py"), say,
                            "-o", f"{td}/x", "--no-fix"], check=True, capture_output=True)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{td}/x_000.wav",
                            "-af", f"atempo={speed}", "-ar", "48000", str(out)], check=True)
    return out


def main():
    ep_id, only = sys.argv[1], set(sys.argv[2:])
    ep_dir = ROOT / ep_id
    ep = json.load(open(ROOT / "scripts.json"))["episodes"][ep_id]
    cfg = json.load(open(ep_dir / "shorts.json"))
    speed = ep.get("speed", 1)
    src = ep_dir / "renders" / f"final_{speed:.2f}x.mp4"
    bgm = ep_dir / "audio" / "bgm.mp3"
    bgm_vol = ep.get("bgm", {}).get("volume", 0.12)
    starts = line_starts(ep_dir, speed)
    end_all = duration(src)
    windows = asset_windows(ep_dir, speed)
    ends = line_ends(ep_dir, speed)
    for sh in cfg["shorts"]:
        if only and sh["id"] not in only:
            continue
        tmp = Path(tempfile.mkdtemp(prefix=f"short_{ep_id}_{sh['id']}_"))
        parts = []
        spans = []
        if "hook" in sh:
            hk = sh["hook"]
            voice = hook_voice(ep_dir, hk["say"], speed)
            dur = round((duration(voice) + 0.25) * 30) / 30
            png = tmp / "hook.png"
            overlay_png(sh["title"], hk["text"], png)
            part = tmp / "p0.mp4"
            # 沒有背景音樂的集（例：mw-01-zc）就只放人聲
            mix = (f"[3:a]volume={bgm_vol}[m];[2:a]volume=2dB[vo];[vo][m]amix=inputs=2:duration=longest:normalize=0,"
                   if bgm.exists() else "[2:a]volume=2dB,apad,")
            fc = VIDEO_FC + (
                mix + f"atrim=0:{dur:.3f},afade=t=out:st={dur - 0.05:.3f}:d=0.05[au]"
            )
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                            "-ss", f"{starts[hk['visual']]:.3f}", "-t", f"{dur:.3f}", "-i", str(src),
                            "-i", str(png), "-i", str(voice), *(["-i", str(bgm)] if bgm.exists() else []),
                            "-filter_complex", fc, "-map", "[v]", "-map", "[au]", *ENC, "-t", f"{dur:.3f}", str(part)],
                           check=True)
            parts.append(part)
            spans.append((starts[hk["visual"]], starts[hk["visual"]] + dur))
        for k, item in enumerate(sh["lines"], 1):
            if isinstance(item, int):
                item = {"n": item}
            n = item["n"]
            a = starts[n] + item.get("skip", 0)
            b = min(starts.get(n + 1, end_all), ends[n] + TAIL)
            if not 0 <= starts[n] <= a < b - 0.3:
                raise SystemExit(f"short {sh['id']} 第 {n} 句切點不合理：{a:.2f}～{b:.2f}")
            dur = round((b - a) * 30) / 30
            png = tmp / f"o{k}.png"
            overlay_png(sh["title"], item.get("text", ep["lines"][n - 1]["text"]), png)
            part = tmp / f"p{k}.mp4"
            fc = VIDEO_FC + (
                f"[0:a]afade=t=in:d=0.03,afade=t=out:st={dur - 0.04:.3f}:d=0.04,"
                f"apad,atrim=0:{dur:.3f}[au]"
            )
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{a:.3f}", "-t", f"{dur:.3f}",
                            "-i", str(src), "-i", str(png), "-filter_complex", fc,
                            "-map", "[v]", "-map", "[au]", *ENC, "-t", f"{dur:.3f}", str(part)],
                           check=True)
            parts.append(part)
            spans.append((a, a + dur))
        lst = tmp / "list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in parts))
        out = ep_dir / "renders" / f"short_{sh['id']}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(out)],
                       check=True)
        used = sorted({k for k, x, y in windows for a, b in spans if x < b and a < y})
        (ep_dir / "renders" / f"short_{sh['id']}.assets.json").write_text(
            json.dumps(used, ensure_ascii=False, indent=1))
        print(f"  ✅ {out.relative_to(ROOT)}  {duration(out):.1f} 秒  {''.join(sh['title'])}")


if __name__ == "__main__":
    main()
