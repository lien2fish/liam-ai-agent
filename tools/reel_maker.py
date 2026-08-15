#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reel_maker — 長片轉品牌短影音 一鍵工具（連老闆-產地到餐桌 定案規格）

兩步流程：
  1) 轉錄＋出字幕稿（人工校對字幕）：
       python3 tools/reel_maker.py transcribe "/path/長片.MOV"
     產出：<長片>_transcript.json（逐字稿）、<長片>_字幕稿.txt（可編輯，改字用）
     ＋ <長片>_config_範本.json（把段落/字幕填好給下一步）

  1b) 多支素材一次轉錄（跨檔重組用）：
       python3 tools/reel_maker.py batch <工作資料夾> <影片1> <影片2> ...
     產出：<工作資料夾>/transcripts/*.json、<工作資料夾>/字幕稿_全部.txt

  2) 依設定產出 影片＋封面＋發文案：
       python3 tools/reel_maker.py build config.json
     產出（存到設定的 out_dir，預設桌面）：<主題>.mp4、<主題>_封面.jpg、<主題>_發文案.md

定案規格（已核准，寫死在此）：
  - 畫面：原始拍攝畫面「滿版不放大」（模糊背景 letterbox，不硬裁緊）
  - 字幕：關鍵字橘黃高光、位置往上(MarginV 560)、STHeiti、整句好讀
  - 前景過濾：領夾麥音量差濾掉背景/旁人講話（<最大-8dB 剔除）
  - 音訊：highpass+afftdn 降噪 + speechnorm 拉齊小聲對話 ＋ 自合成輕快 BGM（無 whoosh 音效）
  - 完整版：1.3 倍速（字幕/BGM 同步）
  - CTA：片尾金句「留言加一，下次OO出現通知你」（放進 cues 即可）
  - 檔名：用主題名，不加「完整版/版本/倍速」字樣
  - 封面卡：另存 _封面.jpg，同一張壓進影片開頭 cover_intro 秒（預設 1.0，0=關）

config 支援單/多來源：
  單來源 "video": 路徑，segments [[s,e]]、cues [[s,e,文字,[高光詞]]]
  多來源 "videos": [路徑...]，segments [[vi,s,e]]、cues [[vi,s,e,文字,[高光詞]]]

聲畫分離(配音蓋圖)：segments 元素改寫成 dict，借用別段的對白配這段畫面
  {"v": [2, 12.0, 20.0], "a": [0, 88.5, 96.0]}
  v=畫面來源/區間，a=聲音來源/區間(省略即畫聲同源)。以畫面長度為準，
  聲音較短補靜音、較長裁掉；該段原始現場音完全丟棄。
  字幕 cue 用「對白來源」的時間碼寫（a 的那支、那段時間）。

相依：ffmpeg（完整版）、openai-whisper、numpy、Pillow。字型 STHeiti（mac 內建）。
"""
import sys, os, re, json, subprocess, wave, tempfile
import numpy as np

ZHF = "/System/Library/Fonts/STHeiti Medium.ttc"
SHORTS_MAX_SEC = 180  # 超過就不是 Shorts，會掉進 16:9 一般影片版位
ASS_FONT = "Heiti TC"
ORANGE_BGR = r"\c&H00309CF5&"  # 橘黃(ASS 是 BGR)
WHITE_BGR = r"\c&H00FFFFFF&"
BASE_FS = 64  # 字幕基準字級(需與 build_ass Style 的 Fontsize 一致)
HL_FS = 82  # 關鍵字放大字級
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


# ---------- 音訊/轉錄 ----------


def _cleanup(path):
    """用完就清。這幾支工具原本只建暫存不清理，跑幾十輪累積 394 個目錄、
    塞爆 113GB 磁碟，導致長片換音軌中途失敗（No space left on device）。"""
    import shutil

    shutil.rmtree(path, ignore_errors=True)


def extract_audio(video, out=None):
    out = out or tempfile.mktemp(suffix=".wav")
    subprocess.run(
        ["ffmpeg", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", out],
        capture_output=True,
    )
    return out


def transcribe(video):
    import whisper, warnings

    warnings.filterwarnings("ignore")
    wav = extract_audio(video)
    m = whisper.load_model("small")
    r = m.transcribe(
        wav,
        language="zh",
        fp16=False,
        word_timestamps=True,
        initial_prompt="以下是台灣海鮮市場的口語介紹，繁體中文。",
    )
    # 前景音量
    w = wave.open(wav, "rb")
    sr = w.getframerate()
    a = (
        np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
        / 32768.0
    )

    def db(s, e):
        seg = a[int(s * sr) : int(e * sr)]
        return 20 * np.log10(np.sqrt(np.mean(seg**2)) + 1e-9) if len(seg) else -99.0

    segs = []
    for s in r["segments"]:
        d = float(db(s["start"], s["end"]))
        segs.append(
            {
                "start": round(float(s["start"]), 2),
                "end": round(float(s["end"]), 2),
                "text": s["text"].strip(),
                "db": round(d, 1),
                "words": [
                    {
                        "w": x["word"].strip(),
                        "s": round(x["start"], 2),
                        "e": round(x["end"], 2),
                    }
                    for x in s.get("words", [])
                    if x["word"].strip()
                ],
            }
        )
    mx = max(x["db"] for x in segs)
    for x in segs:
        x["fg"] = bool(x["db"] >= mx - 8)
    os.remove(wav)
    return segs


# ---------- 前景逐字→cue 斷句 ----------
def clean(t):
    return re.sub(r"[、﹑，。,\.！？!?\s]", "", t)


def seg_to_cues(seg):
    """把一個前景 segment 依標點/12字切成短 cue，回傳 [(s,e,text)]"""
    cues = []
    words = seg.get("words", [])
    if not words:
        return [(seg["start"], seg["end"], clean(seg["text"]))]
    buf = []
    bs = None
    for wd in words:
        ch = clean(wd["w"])
        if bs is None:
            bs = wd["s"]
        stop = bool(re.search(r"[、﹑，。,\.！？!?]", wd["w"]))
        if ch:
            buf.append((ch, wd["e"]))
        if (stop or len("".join(c for c, _ in buf)) >= 12) and buf:
            cues.append((bs, buf[-1][1], "".join(c for c, _ in buf)))
            buf = []
            bs = None
    if buf:
        cues.append((bs, buf[-1][1], "".join(c for c, _ in buf)))
    return [c for c in cues if c[2].strip()]


# ---------- 字幕稿(人工校對) ----------
def write_draft(segs, video):
    base = os.path.splitext(video)[0]
    with open(base + "_字幕稿.txt", "w", encoding="utf-8") as f:
        f.write("字幕稿 — 只列你的話(前景)，請改成真正要講的字\n")
        f.write("格式：時間 | Whisper聽到(可能錯) → 你的版本\n" + "=" * 60 + "\n")
        for x in segs:
            if not x["fg"]:
                continue
            f.write(f'{x["start"]:6.1f}-{x["end"]:5.1f} | {clean(x["text"]):30} → \n')
    json.dump(segs, open(base + "_transcript.json", "w"), ensure_ascii=False, indent=1)
    # config 範本
    fg = [x for x in segs if x["fg"]]
    cfg = {
        "video": video,
        "subject": "主題名",
        "speed": 1.3,
        "out_dir": os.path.expanduser("~/Desktop"),
        "segments": [[round(fg[0]["start"], 1), round(fg[-1]["end"], 1)]] if fg else [],
        "cues": [[x["start"], x["end"], clean(x["text"]), []] for x in fg],
        "cover": {
            "time": round(fg[0]["start"] + 3, 1) if fg else 3,
            "main": "四字高光",
            "line2": "",
            "sub": "副標籤",
        },
        "hooks": {"A": "鉤子一句", "B": "教學一句", "C": "稀有一句"},
    }
    json.dump(cfg, open(base + "_config_範本.json", "w"), ensure_ascii=False, indent=1)
    print("已產出：")
    print(" ", base + "_字幕稿.txt   ← 改字")
    print(" ", base + "_config_範本.json ← 填段落/cues/封面後給 build")
    print(" ", base + "_transcript.json")


def batch_transcribe(work_dir, videos):
    """多支素材一次轉錄，產出集中在 work_dir，字幕稿合成單一檔供一次校對。"""
    work_dir = os.path.expanduser(work_dir)
    tdir = os.path.join(work_dir, "transcripts")
    os.makedirs(tdir, exist_ok=True)
    draft = open(os.path.join(work_dir, "字幕稿_全部.txt"), "w", encoding="utf-8")
    draft.write("字幕稿 — 只列你的話(前景)，請改成真正要講的字\n")
    draft.write("格式：[片#] 時間 | Whisper聽到(可能錯) → 你的版本\n" + "=" * 70 + "\n")
    for v in videos:
        name = os.path.splitext(os.path.basename(v))[0]
        print(f"轉錄 {name} ...", flush=True)
        segs = transcribe(v)
        json.dump(
            segs,
            open(os.path.join(tdir, name + ".json"), "w"),
            ensure_ascii=False,
            indent=1,
        )
        draft.write(f"\n----- {name} -----\n")
        for x in segs:
            if not x["fg"]:
                continue
            draft.write(
                f'[{name}] {x["start"]:6.1f}-{x["end"]:5.1f} | {clean(x["text"]):30} → \n'
            )
        draft.flush()
    draft.close()
    print("完成，產出在", work_dir)


# ---------- BGM(自合成輕快，快取) ----------
def gen_bgm():
    os.makedirs(ASSETS, exist_ok=True)
    path = os.path.join(ASSETS, "bgm_light.wav")
    if os.path.exists(path):
        return path
    sr = 44100
    bpm = 104
    beat = 60 / bpm
    NOTES = {
        "C3": 130.81,
        "D3": 146.83,
        "E3": 164.81,
        "F3": 174.61,
        "G3": 196.0,
        "A3": 220.0,
        "B3": 246.94,
        "C4": 261.63,
        "D4": 293.66,
        "E4": 329.63,
        "F4": 349.23,
        "G4": 392.0,
        "A4": 440.0,
        "C5": 523.25,
        "E5": 659.25,
        "G5": 783.99,
    }

    def tone(f, dur, vol, pluck, harm=(1, 0.5, 0.25)):
        n = int(dur * sr)
        t = np.arange(n) / sr
        w = np.zeros(n)
        for i, h in enumerate(harm):
            w += h * np.sin(2 * np.pi * f * (i + 1) * t)
        w /= sum(harm)
        e = np.ones(n)
        ai = int(0.01 * sr)
        di = int(0.25 * sr)
        ri = int(0.06 * sr)
        sus = 0.0 if pluck else 0.5
        e[:ai] = np.linspace(0, 1, ai)
        e[ai : ai + di] = np.linspace(1, sus, di)
        e[ai + di :] = sus
        e[-ri:] *= np.linspace(1, 0, ri)
        return w * e * vol

    def kick(dur=0.18, vol=0.5):
        n = int(dur * sr)
        t = np.arange(n) / sr
        f = 110 * np.exp(-t * 30) + 45
        return np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t * 14) * vol

    prog = [
        ("C4", "E4", "G4"),
        ("G3", "B3", "D4"),
        ("A3", "C4", "E4"),
        ("F3", "A3", "C4"),
    ]
    mel = ["G4", "E5", "C5", "E5", "G4", "C5", "E5", "G5"]
    loops = 7
    L = np.zeros(int(loops * 8 * beat * sr) + sr)
    pos = 0.0
    for lp in range(loops):
        for ci, ch in enumerate(prog):
            cs = pos + ci * 2 * beat
            for nf in ch:
                s = int(cs * sr)
                seg = tone(NOTES[nf], 2 * beat, 0.10, False, (1, 0.4))
                L[s : s + len(seg)] += seg
            for k in range(4):
                nf = mel[(ci * 2 + k) % len(mel)]
                ns = int((cs + k * 0.5 * beat) * sr)
                seg = tone(NOTES[nf], 0.5 * beat, 0.22, True)
                L[ns : ns + len(seg)] += seg
            for b in range(2):
                ks = int((cs + b * beat) * sr)
                kk = kick()
                L[ks : ks + len(kk)] += kk * 0.5
        pos += 8 * beat
    L /= np.max(np.abs(L)) + 1e-6
    L *= 0.85
    fo = int(1.5 * sr)
    L[-fo:] *= np.linspace(1, 0, fo)
    pcm = (np.stack([L, L], 1) * 32767).astype(np.int16)
    w = wave.open(path, "wb")
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(sr)
    w.writeframes(pcm.tobytes())
    w.close()
    return path


def bgm_bed(duration, vol=0.15):
    src = gen_bgm()
    sr = 44100
    N = int((duration + 0.3) * sr)
    b = wave.open(src, "rb")
    bf = (
        np.frombuffer(b.readframes(b.getnframes()), dtype=np.int16).astype(np.float32)
        / 32768.0
    )
    mono = bf.reshape(-1, 2).mean(axis=1)
    full = np.tile(mono, int(np.ceil(N / len(mono))))[:N] * vol
    out = tempfile.mktemp(suffix=".wav")
    pcm = (np.stack([full, full], 1) * 32767).astype(np.int16)
    w = wave.open(out, "wb")
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(sr)
    w.writeframes(pcm.tobytes())
    w.close()
    return out


# ---------- 高光 ASS ----------
def hl(text, kws):
    # 關鍵字：橘黃高光 + 字體放大（需大括號包 override 才生效）
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


# 單行安全寬度(px)。版面可用寬 920(1080-左右margin 80)，扣描邊 12 剩 908；
# 取 820 讓左右各留約 130px 淨空，避免手機上貼邊或被平台 UI 蓋到。
SAFE_W = 820


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
    return fs * 0.55 if ch.isascii() else fs  # 拉丁/數字半形較窄


def _word_bounds(t):
    """中文詞邊界(可換行位置)。沒裝 jieba 就回 None，改用啟發式斷點。"""
    try:
        import jieba
    except ImportError:
        return None
    jieba.setLogLevel(60)
    bounds = set()
    i = 0
    for word in jieba.cut(t):
        i += len(word)
        bounds.add(i)
    return bounds


def wrap_lines(t, kws):
    """超過 SAFE_W 就換行；切完仍過寬會繼續切，不切斷高光詞。"""
    mask = _hl_mask(t, kws)
    w = [_char_w(c, mask[i]) for i, c in enumerate(t)]
    if sum(w) <= SAFE_W:
        return [t]
    n = len(t)
    spans = []
    stack = []
    for idx, c in enumerate(t):
        if c in "（(「":
            stack.append(idx)
        elif c in "）)」" and stack:
            spans.append((stack.pop(), idx))

    def ok(i):
        if not (0 < i < n) or (mask[i - 1] and mask[i]):  # 不切斷高光詞
            return False
        if any(s < i <= e for s, e in spans):  # 不切在括號內
            return False
        if t[i] in "的了嗎呢啊吧喔）」，、。！？":  # 虛字/標點不當行首
            return False
        return t[i - 1] not in "（「"

    puncts = [i + 1 for i, c in enumerate(t) if c in "，、。！？"]
    # 詞邊界(jieba)；沒有就退回：高光詞開頭 + 常見詞首字
    wb = _word_bounds(t)
    if wb is None:
        good = [i for i in range(1, n) if mask[i] and not mask[i - 1]]
        good += [
            i
            for i in range(1, n)
            if t[i] in "就也都我你他這那所因而然再不沒要會把被從在是有可請讓每"
        ]
    else:
        good = [i for i in range(1, n) if i in wb or (mask[i] and not mask[i - 1])]
    cand = (
        [i for i in puncts if ok(i)]
        or sorted(set(i for i in good if ok(i)))
        or [i for i in range(1, n) if ok(i)]
        or [i for i in range(1, n) if not (mask[i - 1] and mask[i])]
    )
    best = min(cand, key=lambda i: max(sum(w[:i]), sum(w[i:])))
    l1 = t[:best].rstrip("，、")
    l2 = t[best:].lstrip("，、")
    if not l1 or not l2:
        return [t]
    return wrap_lines(l1, kws) + wrap_lines(l2, kws)


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


# ---------- 封面 ----------
def make_cover(video, t, main, sub, out, line2=""):
    from PIL import Image, ImageDraw, ImageFont

    base = tempfile.mktemp(suffix=".jpg")
    fc = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:2,eq=brightness=-0.12[bg];"
        "[0:v]scale=1080:-1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(t),
            "-i",
            video,
            "-frames:v",
            "1",
            "-filter_complex",
            fc,
            base,
        ],
        capture_output=True,
    )
    img = Image.open(base).convert("RGB")
    draw_cover_title(img, main, sub, line2)
    img.save(out, quality=92)
    os.remove(base)


# 四字高光大標（亮黃厚黑描邊、壓中下方，可紅色第二行）
HL_YELLOW = (255, 205, 35)
HL_RED = (228, 46, 38)


def draw_cover_title(img, main, sub="", line2=""):
    from PIL import Image, ImageDraw, ImageFont

    # STHeiti 沒有這些字形，會畫成豆腐方框
    fix = lambda t: t.replace("・", "·").replace("／", "/")
    main, sub, line2 = fix(main), fix(sub), fix(line2)
    d = ImageDraw.Draw(img)
    W, H = img.size

    # 中下方加深，讓高光字更突出、好讀
    scrim = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(scrim)
    for y in range(H):
        a = int(170 * ((y - H * 0.38) / (H * 0.62))) if y > H * 0.38 else 0
        sd.line([(0, y), (W, y)], fill=max(0, min(a, 170)))
    img.paste(Image.new("RGB", (W, H), (0, 0, 0)), (0, 0), scrim)
    d = ImageDraw.Draw(img)

    def fit(tx, cap):
        fs = cap
        while fs > 44:
            f = ImageFont.truetype(ZHF, fs)
            ls = fs * 0.05
            w = sum(d.textlength(c, font=f) + ls for c in tx) - ls
            if w <= W - 150:
                return f, ls
            fs -= 6
        return ImageFont.truetype(ZHF, 44), 44 * 0.05

    lines = [(main, HL_YELLOW, 250 if not line2 else 240)]
    if line2:
        lines.append((line2, HL_RED, 210))
    measured = []
    for tx, fill, cap in lines:
        f, ls = fit(tx, cap)
        asc, desc = f.getmetrics()
        measured.append((tx, fill, f, ls, asc + desc))

    gap = 20
    block_h = sum(m[4] for m in measured) + gap * (len(measured) - 1)
    y = int(H * 0.60) - block_h // 2
    for tx, fill, f, ls, h in measured:
        w = sum(d.textlength(c, font=f) + ls for c in tx) - ls
        x = (W - w) / 2
        sw = max(14, f.size // 10)
        for c in tx:
            d.text(
                (x, y), c, font=f, fill=fill, stroke_width=sw, stroke_fill=(18, 18, 18)
            )
            x += d.textlength(c, font=f) + ls
        y += h + gap

    if sub:
        f2 = ImageFont.truetype(ZHF, 60)
        tw = d.textlength(sub, font=f2)
        d.rounded_rectangle(
            [W / 2 - tw / 2 - 32, y + 6, W / 2 + tw / 2 + 32, y + 110],
            radius=16,
            fill=(18, 18, 18),
        )
        d.text((W / 2 - tw / 2, y + 22), sub, font=f2, fill=(255, 255, 255))


# 超過 3 分鐘的直式片會掉進 YouTube 一般影片版位（16:9），直式封面塞進去只剩中間一條，
# 所以另出一張橫式縮圖：模糊放大的同一影格當底、原影格靠右滿高、標題排左邊。
def make_cover_169(video, t, main, sub, out, line2=""):
    from PIL import Image, ImageDraw, ImageFont, ImageFilter

    fix = lambda s: s.replace("・", "·").replace("／", "/")
    main, sub, line2 = fix(main), fix(sub), fix(line2)

    raw = tempfile.mktemp(suffix=".jpg")
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(t), "-i", video, "-frames:v", "1", raw],
        capture_output=True,
    )
    frame = Image.open(raw).convert("RGB")
    os.remove(raw)

    W, H = 1280, 720
    s = max(W / frame.width, H / frame.height)
    bg = frame.resize((int(frame.width * s), int(frame.height * s)))
    bg = bg.crop(
        ((bg.width - W) // 2, (bg.height - H) // 2,
         (bg.width - W) // 2 + W, (bg.height - H) // 2 + H)
    )  # fmt: skip
    img = Image.blend(
        bg.filter(ImageFilter.GaussianBlur(18)),
        Image.new("RGB", (W, H), (0, 0, 0)),
        0.4,
    )

    fw = int(frame.width * H / frame.height)
    img.paste(frame.resize((fw, H)), (W - fw - 40, 0))

    d = ImageDraw.Draw(img)
    tx_w = W - fw - 130

    def fit(tx, cap):
        fs = cap
        while fs > 40:
            f = ImageFont.truetype(ZHF, fs)
            if d.textlength(tx, font=f) <= tx_w:
                return f
            fs -= 4
        return ImageFont.truetype(ZHF, 40)

    lines = [(main, HL_YELLOW, 124)] + ([(line2, HL_RED, 104)] if line2 else [])
    measured = [(tx, fill, fit(tx, cap)) for tx, fill, cap in lines]
    block_h = sum(sum(f.getmetrics()) for _, _, f in measured) + 16 * (
        len(measured) - 1
    )
    y = (H - block_h) // 2 - 40
    for tx, fill, f in measured:
        d.text(
            (50, y), tx, font=f, fill=fill,
            stroke_width=max(10, f.size // 12), stroke_fill=(18, 18, 18),
        )  # fmt: skip
        y += sum(f.getmetrics()) + 16
    if sub:
        f2 = ImageFont.truetype(ZHF, 44)
        tw = d.textlength(sub, font=f2)
        d.rounded_rectangle(
            [50, y + 14, 50 + tw + 48, y + 104], radius=14, fill=(18, 18, 18)
        )
        d.text((74, y + 28), sub, font=f2, fill=(255, 255, 255))
    img.save(out, quality=92)


def prepend_intro(out_mp4, card_jpg, dur=1.0):
    """封面卡壓進影片開頭 dur 秒（同編碼參數，concat copy 不重編正片）。"""
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
            card_jpg,
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
            # profile/level 必須與正片一致：concat copy 只保留第一段的 SPS/PPS
            "-profile:v",
            "high",
            "-level",
            "4.0",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
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
    # 才會在下一步報「無法上傳影片」。畫面仍 copy，正片不重編、零畫質損失。
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
            "-ac",
            "2",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            merged,
        ],  # fmt: skip
        capture_output=True,
    )
    ok = r.returncode == 0 and os.path.getsize(merged) > os.path.getsize(out_mp4)
    if ok:
        os.replace(merged, out_mp4)
    _cleanup(tmp)
    if not ok:
        raise RuntimeError("intro concat 失敗")


# ---------- build 主流程 ----------
def build(cfg):
    # 單來源 video:[s,e]/[s,e,文字,[高光]]；多來源 videos:[vi,s,e]/[vi,s,e,文字,[高光]]
    multi = "videos" in cfg
    videos = cfg["videos"] if multi else [cfg["video"]]
    subject = cfg["subject"]
    speed = cfg.get("speed", 1.3)
    out_dir = os.path.expanduser(cfg.get("out_dir", "~/Desktop"))
    os.makedirs(out_dir, exist_ok=True)
    # segments 元素：[vi,s,e] 畫聲同源；{"v":[vi,s,e],"a":[vi,s,e]} 聲畫分離(借用別段對白)
    segs = []
    for x in cfg["segments"]:
        if isinstance(x, dict):
            v, a = list(x["v"]), (list(x["a"]) if x.get("a") else None)
        else:
            v, a = list(x), None
        if not multi:
            v = [0] + v
            a = [0] + a if a else None
        segs.append((v, a))
    caps = cfg["cues"] if multi else [[0] + list(x) for x in cfg["cues"]]
    # 純環境音素材(留白給旁白)可設 af 關掉動態壓縮、bgm=false 不混配樂
    af = cfg.get("af", "highpass=f=100,afftdn=nf=-28,speechnorm=e=6.25:r=0.00015")
    LB = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:2,eq=brightness=-0.08[bg];"
        "[0:v]scale=1080:-1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"
    )
    tmp = tempfile.mkdtemp()
    parts = []
    offs = []
    cum = 0.0
    for i, ((vi, s, e), a) in enumerate(segs):
        offs.append((cum, vi, s, e, a))
        cum += e - s
        p = os.path.join(tmp, f"seg{i}.mp4")
        if a:  # 借用別段對白：畫面長度為準，聲音短則補靜音、長則裁掉
            avi, as_, ae = a
            src = [
                "-ss", str(s), "-t", str(e - s), "-i", videos[vi],
                "-ss", str(as_), "-t", str(ae - as_), "-i", videos[avi],
            ]  # fmt: skip
            amap = [
                "-filter_complex", f"{LB};[1:a]{af},apad[a]",
                "-map", "[v]", "-map", "[a]", "-t", str(e - s),
            ]  # fmt: skip
        else:
            src = ["-ss", str(s), "-t", str(e - s), "-i", videos[vi]]
            amap = [
                "-filter_complex", LB,
                "-map", "[v]", "-map", "0:a", "-af", af,
            ]  # fmt: skip
        subprocess.run(
            [
                "ffmpeg",
                "-y",
            ]
            + src
            + amap
            + [
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
        tag = f"，聲音借自 {os.path.basename(videos[a[0]])} {a[1]}-{a[2]}s" if a else ""
        print(f"  seg {i+1}/{len(segs)} 完成 ({e-s:.1f}s{tag})", flush=True)
    cc = os.path.join(tmp, "cc.txt")
    open(cc, "w").write("\n".join(f"file '{p}'" for p in parts))
    joined = os.path.join(tmp, "joined.mp4")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", cc, "-c", "copy", joined],
        capture_output=True,
    )
    total = cum

    # cues → 新時間軸(concat) → 再 /speed
    def newt(vi, t):
        # 借音段優先：字幕跟著對白走，用對白來源的時間碼寫 cue
        for cs, svi, s, e, a in offs:
            if a and a[0] == vi and a[1] - 0.05 <= t <= a[2] + 0.05:
                return (cs + min(max(t - a[1], 0.0), e - s)) / speed
        for cs, svi, s, e, a in offs:
            # 借音段的畫面時間碼不拿來對字幕（原場音已丟棄，對到會是幽靈字幕）
            if not a and svi == vi and s - 0.05 <= t <= e + 0.05:
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
    vf = f"[0:v]setpts=PTS/{speed}[vs];[vs]subtitles={ass}[v];"
    use_bgm = cfg.get("bgm", True)
    mute = cfg.get("mute_source", False)  # 去掉原始收音，只留 BGM
    if use_bgm:
        bed = bgm_bed(total / speed, cfg.get("bgm_vol", 0.15))
        src = ["-i", joined, "-i", bed]
        fc = vf + (
            "[1:a]anull[a]"
            if mute
            else f"[0:a]atempo={speed}[va];[va][1:a]amix=inputs=2:duration=first[a]"
        )
    else:
        src = ["-i", joined]
        fc = vf + (f"[0:a]atempo={speed}[a]" if not mute else "anullsrc[a]")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
        ]
        + src
        + [
            "-filter_complex",
            fc,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            # 不釘死的話 pix_fmt 隨來源跑（444 素材會編成 High 4:4:4），
            # 與封面卡的 yuv420p 對不上，concat copy 後解碼參數就錯了
            "-pix_fmt",
            "yuv420p",
            "-profile:v",
            "high",
            "-level",
            "4.0",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-b:a",
            "160k",
            "-r",
            "24",
            "-movflags",
            "+faststart",
            out_mp4,
        ],
        capture_output=True,
    )
    # 封面（另存縮圖用，同一張再壓進影片開頭）
    cov = cfg.get("cover")
    if cov:
        card = os.path.join(out_dir, f"{subject}_封面.jpg")
        make_cover(
            videos[cov.get("video_index", 0)],
            cov["time"],
            cov.get("main", subject),
            cov.get("sub", ""),
            card,
            cov.get("line2", ""),
        )
        intro_dur = float(cfg.get("cover_intro", 1.0))
        if intro_dur > 0:
            prepend_intro(out_mp4, card, intro_dur)
            print(f"  封面卡已壓進開頭 {intro_dur:.0f} 秒", flush=True)
        if total / speed + intro_dur > SHORTS_MAX_SEC:
            card169 = os.path.join(out_dir, f"{subject}_封面_16x9.jpg")
            make_cover_169(
                videos[cov.get("video_index", 0)],
                cov["time"],
                cov.get("main", subject),
                cov.get("sub", ""),
                card169,
                cov.get("line2", ""),
            )
            print("  超過 3 分鐘＝一般影片版位，已另出 16:9 縮圖", flush=True)
    # 發文案
    write_captions(cfg, os.path.join(out_dir, f"{subject}_發文案.md"))
    _cleanup(tmp)
    print("完成，已存到", out_dir)
    print(" ", f"{subject}.mp4  (約{total/speed:.0f}秒, {speed}x)")
    if cov:
        print(" ", f"{subject}_封面.jpg")
        if total / speed + float(cfg.get("cover_intro", 1.0)) > SHORTS_MAX_SEC:
            print(" ", f"{subject}_封面_16x9.jpg  ← YouTube 一般影片版位用")
    print(" ", f"{subject}_發文案.md")


def write_captions(cfg, path):
    s = cfg["subject"]
    h = cfg.get("hooks", {})
    md = f"# {s} · Reels 發佈文案\n\n"
    md += (
        "**IG Reels**\n- 標題："
        + h.get("A", "")
        + "\n- Hashtag：#鑫海產 #連老闆 #產地到餐桌 #漁港生活 #海鮮知識\n\n"
    )
    md += (
        "**YouTube Shorts**\n- 標題："
        + (h.get("A", "") + f"｜連老闆 {s}")
        + "\n- 描述："
        + h.get("B", "")
        + " #Shorts #海鮮\n\n"
    )
    md += "**TikTok**\n- 文案：" + h.get("A", "") + " #海鮮 #漁港生活 #漲知識 #foryou\n"
    open(path, "w", encoding="utf-8").write(md)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("transcribe", "batch", "build"):
        print(__doc__)
        return
    if sys.argv[1] == "transcribe":
        video = sys.argv[2]
        segs = transcribe(video)
        write_draft(segs, video)
    elif sys.argv[1] == "batch":
        batch_transcribe(sys.argv[2], sys.argv[3:])
    else:
        cfg = json.load(open(sys.argv[2], encoding="utf-8"))
        build(cfg)


if __name__ == "__main__":
    main()
