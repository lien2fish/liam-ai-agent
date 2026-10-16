#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""參考影片拆解——量出別人的剪輯手法，跟自己的並排比。

用法：
  python3 tools/reference_analyze.py 參考1.mp4 參考2.mp4 ...
  python3 tools/reference_analyze.py 參考*.mp4 --mine 我的成品.mp4
  python3 tools/reference_analyze.py 參考.mp4 --speech     # 多跑 Whisper 算語速(慢)

學手法不是抄內容：量的是節奏、開場密度、有沒有配樂這些**做法**，
具體的腳本與視覺設計是人家的，不要照搬。

2026-09 手動做過一次（12 支 IG 破萬短影音），結論是中位 0.7 秒一刀、
連老闆當時 7.9 秒，據此把螃蟹那批切到 3.6 秒一刀。這支把那次的程式固定下來。
"""
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import wave

import numpy as np

# 場景變化門檻。九月那批（別人的快剪短影音）用 0.25 剛好。
# ⚠️ 門檻要看素材：手持實拍在 0.08 以下會把鏡頭晃動當成切點——
# 韓國精華那支實測 0.25→16 刀、0.15→24 刀、0.08→307 刀、0.04→2849 刀，
# 0.08 到 0.15 之間是斷崖。別人的片跟自己的片要用同一個門檻才能比。
SCENE_TH = 0.25
HOOK_SEC = 3.0  # 「開場」算前幾秒


def probe(path):
    out = subprocess.run(["ffmpeg", "-i", path], capture_output=True, text=True).stderr
    d = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", out)
    wh = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", out)
    if not d:
        raise SystemExit(f"❌ 讀不到影片規格：{path}")
    h, m, s = d.groups()
    dur = int(h) * 3600 + int(m) * 60 + float(s)
    w, hh = (int(wh.group(1)), int(wh.group(2))) if wh else (0, 0)
    return dur, w, hh


def cuts(path, th=SCENE_TH):
    """場景變化的時間點。
    ⚠️ 不要用 showinfo 配 -v error——那樣訊息會被整個吞掉，每支都回報 1 刀。"""
    r = subprocess.run(
        # fmt: off
        ["ffmpeg", "-i", path, "-vf",
         f"select='gt(scene,{th})',metadata=print:file=-", "-f", "null", "-"],
        # fmt: on
        capture_output=True,
        text=True,
    )
    return [float(m) for m in re.findall(r"pts_time:([\d.]+)", r.stdout + r.stderr)]


def has_bgm(path):
    """用 onset 包絡的自相關找穩定節拍。
    ⚠️ 不能用「講話空檔安不安靜」判斷——魚市環境音會被當成配樂（九月誤判過）。"""
    wav = tempfile.mktemp(suffix=".wav")
    subprocess.run(
        # fmt: off
        ["ffmpeg", "-y", "-v", "error", "-i", path, "-ac", "1", "-ar", "22050", wav],
        # fmt: on
        capture_output=True,
    )
    if not os.path.exists(wav):
        return None, 0.0
    with wave.open(wav) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(
            np.float32
        )
    os.remove(wav)
    if len(x) < sr * 3:
        return None, 0.0

    hop, win = 256, 1024
    n = (len(x) - win) // hop
    if n < 64:
        return None, 0.0
    frames = np.lib.stride_tricks.as_strided(
        x, shape=(n, win), strides=(x.strides[0] * hop, x.strides[0])
    )
    spec = np.abs(np.fft.rfft(frames * np.hanning(win), axis=1))
    # 頻譜通量：只取變大的部分，那是「敲下去」的瞬間
    flux = np.maximum(spec[1:] - spec[:-1], 0).sum(axis=1)
    flux -= flux.mean()
    if flux.std() < 1e-6:
        return None, 0.0
    flux /= flux.std()

    ac = np.correlate(flux, flux, mode="full")[len(flux) - 1 :]
    ac /= ac[0] if ac[0] else 1
    fps_env = sr / hop
    lo, hi = int(fps_env * 60 / 180), int(fps_env * 60 / 60)  # 60~180 BPM
    seg = ac[lo : min(hi, len(ac))]
    if not len(seg):
        return None, 0.0
    peak = float(seg.max())
    bpm = 60 * fps_env / (lo + int(seg.argmax()))
    return (round(bpm), peak) if peak > 0.18 else (None, peak)


def speech_rate(path):
    """每秒幾個字、停頓多長。要跑 Whisper，慢。"""
    try:
        import whisper
    except ImportError:
        return None
    wav = tempfile.mktemp(suffix=".wav")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", wav],
        capture_output=True,
    )
    r = whisper.load_model("small").transcribe(
        wav, language="zh", condition_on_previous_text=False
    )
    os.remove(wav)
    segs = [s for s in r.get("segments", []) if s.get("text", "").strip()]
    if not segs:
        return None
    chars = sum(len(s["text"].strip()) for s in segs)
    talk = sum(s["end"] - s["start"] for s in segs)
    gaps = [
        b["start"] - a["end"] for a, b in zip(segs, segs[1:]) if b["start"] > a["end"]
    ]
    return {
        "字數": chars,
        "說話秒數": round(talk, 1),
        "字每秒": round(chars / talk, 2) if talk else 0,
        "停頓次數": len(gaps),
        "最長停頓": round(max(gaps), 2) if gaps else 0,
    }


def analyze(path, with_speech=False, th=SCENE_TH):
    dur, w, h = probe(path)
    cs = cuts(path, th)
    spans = [b - a for a, b in zip([0.0] + cs, cs + [dur])]
    spans = [s for s in spans if s > 0.04]  # 濾掉同一刀的重複偵測
    bpm, strength = has_bgm(path)
    # 一刀都沒偵測到就是單鏡到底，不能拿整支長度當「中位一刀」——那是誤導的數字
    solo = not cs
    r = {
        "檔名": os.path.basename(path),
        "長度": round(dur, 1),
        "畫幅": f"{w}x{h}" + ("（直式）" if h > w else "（橫式）"),
        "刀數": len(cs),
        "中位": "單鏡" if solo else round(float(np.median(spans)), 2),
        "最短": "—" if solo else round(min(spans), 2),
        "最長": "—" if solo else round(max(spans), 2),
        "開場刀數": sum(1 for c in cs if c <= HOOK_SEC),
        "配樂": f"有 約{bpm}BPM" if bpm else "沒有",
        "_節拍強度": round(strength, 3),
        "_單鏡": solo,
    }
    if with_speech:
        r["語速"] = speech_rate(path)
    return r


def table(rows, title):
    if not rows:
        return
    cols = ["檔名", "長度", "畫幅", "刀數", "中位", "最短", "最長", "開場刀數", "配樂"]
    wid = {c: max(len(c) * 2, *(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    print(f"\n━━━ {title} ━━━")
    print("  ".join(c.ljust(wid[c]) for c in cols))
    for r in rows:
        print("  ".join(str(r.get(c, "")).ljust(wid[c]) for c in cols))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    with_speech = "--speech" in sys.argv
    th = SCENE_TH
    for a in sys.argv[1:]:
        if a.startswith("--th="):
            th = float(a.split("=", 1)[1])
    mine = []
    if "--mine" in sys.argv:
        i = sys.argv.index("--mine")
        mine = [a for a in sys.argv[i + 1 :] if not a.startswith("--")]
        args = [a for a in args if a not in mine]

    refs = []
    for p in args:
        if not os.path.exists(p):
            print(f"⚠️ 找不到 {p}")
            continue
        print(f"  分析中 {os.path.basename(p)} …", flush=True)
        refs.append(analyze(p, with_speech, th))
    mines = []
    for p in mine:
        if os.path.exists(p):
            print(f"  分析中 {os.path.basename(p)} …", flush=True)
            mines.append(analyze(p, with_speech, th))

    table(refs, f"參考影片 {len(refs)} 支")
    table(mines, f"我的影片 {len(mines)} 支")

    cut = lambda rs: [r["中位"] for r in rs if not r["_單鏡"]]

    def summary(rs, who):
        c = cut(rs)
        solo = sum(1 for r in rs if r["_單鏡"])
        print(f"\n━━━ {who} ━━━")
        if c:
            print(
                f"  鏡頭中位長度　{float(np.median(c)):.2f} 秒一刀（{len(c)} 支有切）"
            )
        if solo:
            print(f"  單鏡到底　　　{solo}/{len(rs)} 支")
        print(
            f"  有配樂的　　　{sum(1 for r in rs if r['配樂'] != '沒有')}/{len(rs)} 支"
        )
        print(
            f"  前 {HOOK_SEC:.0f} 秒切幾刀　中位 {float(np.median([r['開場刀數'] for r in rs])):.0f} 刀"
        )
        return float(np.median(c)) if c else None

    rm = summary(refs, "參考影片的共同點") if refs else None
    mm = summary(mines, "我的影片") if mines else None
    if rm and mm:
        d = mm / rm
        how = (
            "慢 %.1f 倍" % d
            if d > 1.3
            else "差不多" if d > 0.77 else "快 %.1f 倍" % (1 / d)
        )
        print(f"\n━━━ 差距 ━━━")
        print(f"  鏡頭長度　我 {mm:.2f} 秒 vs 他們 {rm:.2f} 秒（{how}）")

    print(
        f"\n（場景門檻 {th}；手持實拍低於 0.08 會把鏡頭晃動當切點，"
        f"比較時兩邊要用同一個門檻。改門檻：--th=0.15）"
    )
    out = os.path.join(
        os.path.dirname(os.path.abspath((args or mine)[0])), "參考影片分析.json"
    )
    json.dump(
        {"門檻": th, "參考": refs, "我的": mines},
        open(out, "w"),
        ensure_ascii=False,
        indent=2,
    )
    print(f"✅ 明細存到 {out}")


if __name__ == "__main__":
    main()
