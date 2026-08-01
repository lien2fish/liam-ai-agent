#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dessert_longform — 甜點頻道「甜點輕鬆做．師傅真心話」長片剪輯工具

與 reel_maker（海鮮 reels）、music_reel（樂器）完全獨立。

用法：
  python3 tools/dessert_longform.py build config.json
  python3 tools/dessert_longform.py bgm "/path/成品.mp4"   # 混入溫暖輕柔BGM(原地覆蓋,影像不重編碼)

config 格式（多來源檔，segments/cues 用 [影片索引, 秒數] 定位）：
{
  "videos": ["/path/a.MOV", "/path/b.MOV"],
  "subject": "影片主題名",
  "out_dir": "~/Desktop",
  "segments": [[0, 10.0, 25.0], [1, 5.0, 40.0]],
  "cues": [[0, 10.5, 13.0, "字幕文字", ["高光詞"]]],
  "cover": {"video_index": 1, "time": 20.0, "main": "大標", "sub": "副標"},
  "youtube": {"title": "...", "description": "...", "tags": ["..."]}
}

定案規格（2026-07-18 使用者核准）：
  - 不加速（speed 1.0）、無 BGM、無前景過濾（對話都是內容）
  - 完整繁中字幕＋關鍵字橘黃高光（同品牌樣式）
  - 音訊 highpass+afftdn 降噪 + speechnorm 拉齊音量
  - 直式素材原生輸出 1080×1920；封面另出 YouTube 16:9 1280×720
"""
import sys, os, re, json, subprocess, tempfile

ZHF = "/System/Library/Fonts/STHeiti Medium.ttc"
ASS_FONT = "Heiti TC"
ORANGE_BGR = r"\c&H00309CF5&"
WHITE_BGR = r"\c&H00FFFFFF&"
BASE_FS = 64
HL_FS = 82
SAFE_W = 900


def hl(text, kws):
    for k in kws:
        text = text.replace(
            k,
            "{"
            + ORANGE_BGR
            + r"\fs"
            + str(HL_FS)
            + "}"
            + k
            + "{"
            + WHITE_BGR
            + r"\fs"
            + str(BASE_FS)
            + "}",
        )
    return text


def ts(x):
    return f"{int(x//3600)}:{int(x%3600//60):02d}:{x%60:05.2f}"


def _hl_mask(t, kws):
    mask = [False] * len(t)
    for k in kws:
        i = t.find(k)
        while i >= 0:
            for j in range(i, i + len(k)):
                mask[j] = True
            i = t.find(k, i + len(k))
    return mask


def _char_w(ch, big):
    fs = HL_FS if big else BASE_FS
    return fs * 0.55 if ch.isascii() else fs


def wrap_lines(t, kws):
    mask = _hl_mask(t, kws)
    w = [_char_w(c, mask[i]) for i, c in enumerate(t)]
    if sum(w) <= SAFE_W:
        return [t]
    n = len(t)
    ok = lambda i: 0 < i < n and not (mask[i - 1] and mask[i])
    puncts = [i + 1 for i, c in enumerate(t) if c in "，、。！？"]
    cand = [i for i in puncts if ok(i)] or [i for i in range(1, n) if ok(i)]
    best = min(cand, key=lambda i: max(sum(w[:i]), sum(w[i:])))
    return [t[:best].rstrip("，、"), t[best:].lstrip("，、")]


def wrap_cue(t, kws):
    return r"\N".join(hl(line, kws) for line in wrap_lines(t, kws))


def build_ass(cues_new, path):
    head = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, "
        "Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Def, {ASS_FONT}, 64, &H00FFFFFF, &H00101010, &H00000000, 1, 1, 6, 2, 2, 80, 80, 560, 1\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    body = "".join(
        f"Dialogue: 0,{ts(s)},{ts(e)},Def,,0,0,0,,{wrap_cue(t,kw)}\n"
        for s, e, t, kw in cues_new
    )
    open(path, "w", encoding="utf-8").write(head + body)


HL_YELLOW = (255, 205, 35)


def make_intro_card_916(video, t, main, sub, out):
    """直式 1080×1920 封面卡（開頭1秒用）：影格滿版＋暗化＋黃字大標＋副標膠囊。"""
    from PIL import Image, ImageDraw, ImageFont

    raw = tempfile.mktemp(suffix=".png")
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(t), "-i", video, "-frames:v", "1", raw],
        capture_output=True,
    )
    frame = Image.open(raw).convert("RGB")
    os.remove(raw)
    W, H = 1080, 1920
    s = max(W / frame.width, H / frame.height)
    bg = frame.resize((int(frame.width * s), int(frame.height * s)))
    bg = bg.crop(
        (
            (bg.width - W) // 2,
            (bg.height - H) // 2,
            (bg.width - W) // 2 + W,
            (bg.height - H) // 2 + H,
        )
    )
    img = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.42)
    d = ImageDraw.Draw(img)

    def fit(tx, cap):
        fs = cap
        while fs > 48:
            f = ImageFont.truetype(ZHF, fs)
            if d.textlength(tx, font=f) <= W - 120:
                return f
            fs -= 4
        return ImageFont.truetype(ZHF, 48)

    lines = main.split("\n")
    fonts = [fit(l, 150) for l in lines]
    total_h = sum(sum(f.getmetrics()) for f in fonts) + 24 * (len(lines) - 1)
    y = int(H * 0.42) - total_h // 2
    for l, f in zip(lines, fonts):
        w = d.textlength(l, font=f)
        d.text(
            ((W - w) / 2, y),
            l,
            font=f,
            fill=HL_YELLOW,
            stroke_width=max(10, f.size // 12),
            stroke_fill=(18, 18, 18),
        )
        y += sum(f.getmetrics()) + 24
    if sub:
        f2 = ImageFont.truetype(ZHF, 52)
        tw = d.textlength(sub, font=f2)
        d.rounded_rectangle(
            [W / 2 - tw / 2 - 36, y + 24, W / 2 + tw / 2 + 36, y + 24 + 88],
            radius=18,
            fill=(18, 18, 18),
        )
        d.text((W / 2 - tw / 2, y + 40), sub, font=f2, fill=(255, 255, 255))
    img.save(out, quality=92)


def prepend_intro(out_mp4, card_png, dur=1.0):
    """封面卡壓進影片開頭 dur 秒（同編碼參數，concat copy 不重編本片）。"""
    tmp = tempfile.mkdtemp()
    intro = os.path.join(tmp, "intro.mp4")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-t",
            str(dur),
            "-i",
            card_png,
            "-f",
            "lavfi",
            "-t",
            str(dur),
            "-i",
            "anullsrc=r=48000:cl=stereo",
            "-vf",
            "scale=1080:1920:out_range=tv,format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-color_range",
            "tv",
            # profile/level 必須與本片一致：concat copy 只保留第一段的 SPS/PPS
            "-profile:v",
            "high",
            "-level",
            "4.0",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-b:a",
            "160k",
            "-r",
            "24",
            "-shortest",
            intro,
        ],
        capture_output=True,
    )
    cc = os.path.join(tmp, "cc.txt")
    open(cc, "w").write(f"file '{intro}'\nfile '{os.path.abspath(out_mp4)}'\n")
    merged = os.path.join(tmp, "merged.mp4")
    # 音訊必須重編：純 -c copy 在接縫會出 non-monotonic DTS，YouTube 處理完
    # 才會在下一步報「無法上傳影片」。畫面仍 copy，本片不重編、零畫質損失。
    r = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            cc,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            merged,
        ],  # fmt: skip
        capture_output=True,
    )
    if r.returncode == 0 and os.path.getsize(merged) > os.path.getsize(out_mp4):
        os.replace(merged, out_mp4)
    else:
        raise RuntimeError("intro concat 失敗")


def make_cover_169(video, t, main, sub, out):
    from PIL import Image, ImageDraw, ImageFont, ImageFilter

    raw = tempfile.mktemp(suffix=".png")
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(t), "-i", video, "-frames:v", "1", raw],
        capture_output=True,
    )
    frame = Image.open(raw).convert("RGB")
    os.remove(raw)
    W, H = 1280, 720
    bg = frame.copy()
    s = max(W / bg.width, H / bg.height)
    bg = bg.resize((int(bg.width * s), int(bg.height * s)))
    bg = bg.crop(
        (
            (bg.width - W) // 2,
            (bg.height - H) // 2,
            (bg.width - W) // 2 + W,
            (bg.height - H) // 2 + H,
        )
    )
    bg = bg.filter(ImageFilter.GaussianBlur(18))
    img = Image.new("RGB", (W, H))
    img.paste(bg)
    dark = Image.new("RGB", (W, H), (0, 0, 0))
    img = Image.blend(img, dark, 0.35)
    fh = H
    fw = int(frame.width * fh / frame.height)
    fg = frame.resize((fw, fh))
    img.paste(fg, (W - fw - 40, 0))
    d = ImageDraw.Draw(img)
    tx_w = W - fw - 100

    def fit(tx, cap):
        fs = cap
        while fs > 40:
            f = ImageFont.truetype(ZHF, fs)
            if d.textlength(tx, font=f) <= tx_w:
                return f
            fs -= 4
        return ImageFont.truetype(ZHF, 40)

    lines = main.split("\n")
    fonts = [fit(l, 128) for l in lines]
    total_h = sum(f.getmetrics()[0] + f.getmetrics()[1] for f in fonts) + 16 * (
        len(lines) - 1
    )
    y = (H - total_h) // 2 - 40
    for l, f in zip(lines, fonts):
        d.text(
            (50, y),
            l,
            font=f,
            fill=HL_YELLOW,
            stroke_width=max(10, f.size // 12),
            stroke_fill=(18, 18, 18),
        )
        y += sum(f.getmetrics()) + 16
    if sub:
        f2 = ImageFont.truetype(ZHF, 44)
        tw = d.textlength(sub, font=f2)
        d.rounded_rectangle(
            [50, y + 14, 50 + tw + 48, y + 14 + 76], radius=14, fill=(18, 18, 18)
        )
        d.text((74, y + 28), sub, font=f2, fill=(255, 255, 255))
    img.save(out, quality=92)


def build(cfg):
    videos = cfg["videos"]
    subject = cfg["subject"]
    out_dir = os.path.expanduser(cfg.get("out_dir", "~/Desktop"))
    os.makedirs(out_dir, exist_ok=True)
    segs = cfg["segments"]
    caps = cfg["cues"]
    LB = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        "boxblur=25:2,eq=brightness=-0.08[bg];"
        "[0:v]scale=1080:-1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"
    )
    tmp = tempfile.mkdtemp()
    parts = []
    offs = []
    cum = 0.0
    for i, (vi, s, e) in enumerate(segs):
        offs.append((cum, vi, s, e))
        cum += e - s
        p = os.path.join(tmp, f"seg{i:03d}.mp4")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                str(s),
                "-t",
                str(e - s),
                "-i",
                videos[vi],
                "-filter_complex",
                LB,
                "-map",
                "[v]",
                "-map",
                "0:a",
                "-af",
                "highpass=f=100,afftdn=nf=-28,speechnorm=e=6.25:r=0.00015",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-b:a",
                "160k",
                "-r",
                "24",
                p,
            ],
            capture_output=True,
        )
        if not os.path.exists(p) or os.path.getsize(p) < 10000:
            raise RuntimeError(
                f"seg{i} 產出失敗（來源 {videos[vi]} 可能被 iCloud 回收，先 brctl download）"
            )
        parts.append(p)
        print(f"  seg {i+1}/{len(segs)} 完成 ({e-s:.1f}s)", flush=True)
    cc = os.path.join(tmp, "cc.txt")
    open(cc, "w").write("\n".join(f"file '{p}'" for p in parts))
    joined = os.path.join(tmp, "joined.mp4")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", cc, "-c", "copy", joined],
        capture_output=True,
    )
    total = cum

    speed = float(cfg.get("speed", 1.0))

    def newt(vi, t):
        for cs, svi, s, e in offs:
            if svi == vi and s - 0.05 <= t <= e + 0.05:
                return (cs + min(max(t - s, 0.0), e - s)) / speed
        return None

    cues_new = []
    for vi, s, e, txt, kw in caps:
        ns, ne = newt(vi, s), newt(vi, e)
        if ns is not None and ne is not None and ne > ns:
            cues_new.append((ns, ne, txt, kw))
    print(f"  cues 對上 {len(cues_new)}/{len(caps)}", flush=True)
    ass = os.path.join(tmp, "sub.ass")
    build_ass(cues_new, ass)
    out_mp4 = os.path.join(out_dir, f"{subject}.mp4")
    if speed != 1.0:
        vfargs = [
            "-filter_complex",
            f"[0:v]setpts=PTS/{speed}[vs];[vs]subtitles={ass}[v];[0:a]atempo={speed}[a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-b:a",
            "160k",
        ]
    else:
        vfargs = ["-vf", f"subtitles={ass}", "-c:a", "copy"]
    subprocess.run(
        ["ffmpeg", "-y", "-i", joined]
        + vfargs
        + [
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-r",
            "24",
            # pix_fmt/profile 要與封面卡一致，否則 concat copy 後解碼參數對不上
            "-pix_fmt",
            "yuv420p",
            "-profile:v",
            "high",
            "-level",
            "4.0",
            "-movflags",
            "+faststart",
            out_mp4,
        ],  # fmt: skip
        capture_output=True,
    )
    cov = cfg.get("cover")
    intro_dur = float(cfg.get("cover_intro", 1.0))
    if cov:
        card = os.path.join(out_dir, f"{subject}_封面.jpg")
        make_intro_card_916(
            videos[cov["video_index"]],
            cov["time"],
            cov.get("main", subject),
            cov.get("sub", ""),
            card,
        )
        if intro_dur > 0:
            prepend_intro(out_mp4, card, intro_dur)
            print(f"  封面卡已壓進開頭 {intro_dur:.0f} 秒", flush=True)
    if cfg.get("bgm"):
        mix_bgm(out_mp4, cfg["bgm"])
    yt = cfg.get("youtube", {})
    md = f"# {subject} · YouTube 發佈資料\n\n"
    md += f"**標題**\n{yt.get('title','')}\n\n"
    md += f"**描述**\n```\n{yt.get('description','')}\n```\n\n"
    md += "**Tags**\n" + ", ".join(yt.get("tags", [])) + "\n"
    open(os.path.join(out_dir, f"{subject}_發文案.md"), "w", encoding="utf-8").write(md)
    print("完成，已存到", out_dir)
    print(
        " ",
        f"{subject}.mp4  (約{total/speed:.0f}秒 = {total/speed/60:.1f}分, {speed}x)",
    )
    print(" ", f"{subject}_封面.jpg")
    print(" ", f"{subject}_發文案.md")


def gen_warm_bgm(duration, vol=0.11):
    """自合成溫暖輕柔BGM（76bpm、柔和琶音、無鼓點），回傳wav路徑。勿用ffmpeg tremolo(會exit 222)。"""
    import wave
    import numpy as np

    sr = 44100
    bpm = 76
    beat = 60 / bpm
    N = {
        "C3": 130.81,
        "E3": 164.81,
        "F3": 174.61,
        "G3": 196.0,
        "A3": 220.0,
        "C4": 261.63,
        "D4": 293.66,
        "E4": 329.63,
        "F4": 349.23,
        "G4": 392.0,
        "A4": 440.0,
        "B4": 493.88,
        "C5": 523.25,
        "D5": 587.33,
        "E5": 659.25,
    }

    def tone(f, dur, vol_, soft=True):
        n = int(dur * sr)
        t = np.arange(n) / sr
        w = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2 * t)
        w += 0.12 * np.sin(2 * np.pi * f * 3 * t)
        w /= 1.47
        e = np.ones(n)
        ai = max(1, int((0.04 if soft else 0.008) * sr))
        e[:ai] = np.linspace(0, 1, ai)
        e[ai:] = np.exp(-np.arange(n - ai) / sr / (1.6 if soft else 0.5))
        return w * e * vol_

    prog = [
        ("C3", ("C4", "E4", "G4"), ["E5", "D5", "C5", "G4"]),
        ("G3", ("B4", "D4", "G4"), ["D5", "B4", "G4", "D4"]),
        ("A3", ("A4", "C4", "E4"), ["C5", "E5", "A4", "E4"]),
        ("F3", ("A4", "C4", "F4"), ["A4", "C5", "F4", "A4"]),
    ]
    bar = 4 * beat
    loop_len = len(prog) * bar
    loops = int(np.ceil((duration + 2) / loop_len))
    L = np.zeros(int(loops * loop_len * sr) + sr)
    pos = 0.0
    for _ in range(loops):
        for root, chord, arp in prog:
            cs = pos
            s = int(cs * sr)
            seg = tone(N[root], bar, 0.20)
            L[s : s + len(seg)] += seg
            for nf in chord:
                seg = tone(N[nf], bar, 0.07)
                L[s : s + len(seg)] += seg
            for k, nf in enumerate(arp):
                ns = int((cs + k * beat) * sr)
                seg = tone(N[nf], beat * 1.5, 0.11, soft=False)
                L[ns : ns + len(seg)] += seg
            pos += bar
    L = L[: int(duration * sr)]
    L /= np.max(np.abs(L)) + 1e-6
    L *= vol
    fi = int(2.0 * sr)
    L[:fi] *= np.linspace(0, 1, fi)
    fo = int(3.0 * sr)
    L[-fo:] *= np.linspace(1, 0, fo)
    out = tempfile.mktemp(suffix=".wav")
    pcm = (np.stack([L, L], 1) * 32767).astype(np.int16)
    w = wave.open(out, "wb")
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(sr)
    w.writeframes(pcm.tobytes())
    w.close()
    return out


def gen_lively_bgm(duration, vol=0.13):
    """自合成輕快活潑BGM（112bpm、彈撥旋律＋輕鼓點＋off-beat hat）。"""
    import wave
    import numpy as np

    sr = 44100
    bpm = 112
    beat = 60 / bpm
    N = {
        "C3": 130.81,
        "F3": 174.61,
        "G3": 196.0,
        "A3": 220.0,
        "C4": 261.63,
        "D4": 293.66,
        "E4": 329.63,
        "F4": 349.23,
        "G4": 392.0,
        "A4": 440.0,
        "B4": 493.88,
        "C5": 523.25,
        "D5": 587.33,
        "E5": 659.25,
        "G5": 783.99,
    }

    def pluck(f, dur, vol_):
        n = int(dur * sr)
        t = np.arange(n) / sr
        w = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2 * t)
        w /= 1.4
        e = np.exp(-t * 6.5)
        ai = max(1, int(0.006 * sr))
        e[:ai] *= np.linspace(0, 1, ai)
        return w * e * vol_

    def kick(vol_=0.4):
        n = int(0.15 * sr)
        t = np.arange(n) / sr
        f = 120 * np.exp(-t * 32) + 48
        return np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t * 16) * vol_

    def hat(vol_=0.10):
        n = int(0.05 * sr)
        rng = np.random.default_rng(7)
        return rng.standard_normal(n) * np.exp(-np.arange(n) / sr * 90) * vol_

    prog = [
        (("C4", "E4", "G4"), ["C5", "E5", "G4", "E5", "C5", "G5", "E5", "C5"]),
        (("G3", "B4", "D4"), ["D5", "B4", "G4", "B4", "D5", "G4", "B4", "D5"]),
        (("A3", "C4", "E4"), ["E5", "C5", "A4", "C5", "E5", "A4", "C5", "E5"]),
        (("F3", "A4", "C4"), ["C5", "A4", "F4", "A4", "C5", "F4", "A4", "C5"]),
    ]
    bar = 4 * beat
    loop_len = len(prog) * bar
    loops = int(np.ceil((duration + 2) / loop_len))
    L = np.zeros(int(loops * loop_len * sr) + sr)
    pos = 0.0
    for _ in range(loops):
        for chord, mel in prog:
            cs = pos
            s = int(cs * sr)
            for nf in chord:
                seg = pluck(N[nf], bar, 0.09)
                L[s : s + len(seg)] += seg
            for k, nf in enumerate(mel):
                ns = int((cs + k * 0.5 * beat) * sr)
                seg = pluck(N[nf], 0.5 * beat * 1.6, 0.16)
                L[ns : ns + len(seg)] += seg
            for b in range(4):
                ks = int((cs + b * beat) * sr)
                kk = kick()
                L[ks : ks + len(kk)] += kk
                hs = int((cs + (b + 0.5) * beat) * sr)
                hh = hat()
                L[hs : hs + len(hh)] += hh
            pos += bar
    L = L[: int(duration * sr)]
    L /= np.max(np.abs(L)) + 1e-6
    L *= vol
    fi = int(1.0 * sr)
    L[:fi] *= np.linspace(0, 1, fi)
    fo = int(3.0 * sr)
    L[-fo:] *= np.linspace(1, 0, fo)
    out = tempfile.mktemp(suffix=".wav")
    pcm = (np.stack([L, L], 1) * 32767).astype(np.int16)
    w = wave.open(out, "wb")
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(sr)
    w.writeframes(pcm.tobytes())
    w.close()
    return out


def mix_bgm(video, style="warm"):
    r = subprocess.run(["ffmpeg", "-i", video], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    bed = gen_lively_bgm(dur) if style == "lively" else gen_warm_bgm(dur)
    out = tempfile.mktemp(suffix=".mp4")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            video,
            "-i",
            bed,
            "-filter_complex",
            "[0:a][1:a]amix=inputs=2:duration=first:normalize=0[a]",
            "-map",
            "0:v",
            "-map",
            "[a]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-b:a",
            "160k",
            # 這是有 BGM 時的最後一道，faststart 要在這裡補回來
            "-movflags",
            "+faststart",
            out,
        ],
        capture_output=True,
    )
    os.replace(out, video)
    os.remove(bed)
    print(f"BGM 已混入：{video} ({dur:.0f}s)")


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "bgm":
        mix_bgm(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "warm")
        return
    if len(sys.argv) < 3 or sys.argv[1] != "build":
        print(__doc__)
        return
    build(json.load(open(sys.argv[2], encoding="utf-8")))


if __name__ == "__main__":
    main()
