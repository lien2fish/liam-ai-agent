#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""成品驗證檢查點 — 在燒掉幾小時渲染之前，先驗音訊處理有沒有出錯。

reel_check 只驗渲染前的 config（字幕、時間軸），驗不出音訊鏈的問題。
實際踩過的雷：增益加在限幅器之後，導致訊號被死命壓成「爆音」——峰值
檢查完全正常，只有 crest factor（峰值−均值）會掉下來。

用法：
  python3 tools/reel_verify.py preflight <config>      只算音訊（約 1 分鐘），渲染前先驗
  python3 tools/reel_verify.py final <config> <mp4>    成品完整驗證（含畫面規格）

preflight 是重點：它讓「順序放錯」這類錯誤在渲染前就被抓出來。
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reel_remix as rr

CREST_MIN = 9.0  # 低於此值代表被過度限幅，人聲會有壓扁感
PEAK_MAX = -1.0  # dBFS
NOISE_MARGIN = 6.0  # 雜音至少要比人聲低這麼多
SPEAKER_GAP = 6.0  # 兩位講者音量差上限



LEDGER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "reels", "驗收清單.json")
COMMON_WORDS = ["野生", "養殖", "公斤", "台斤", "漁會", "價格", "彈性", "肉質", "手臂",
                "大小", "虱目", "土魠", "白蝦", "文蛤", "蛤蜊", "吳郭", "紅條", "崁仔",
                "龜吼", "集散", "散客", "店家", "魚貨", "單位", "計算", "冷凍", "保鮮"]


def applies(entry, name):
    return "*" in entry["適用"] or any(a in name for a in entry["適用"])


def check_requirements(cfg, name, ok):
    """逐條驗使用者交代過的要求——避免改過又被重產蓋掉。"""
    if not os.path.exists(LEDGER):
        return
    led = json.load(open(LEDGER, encoding="utf-8"))
    cues = sorted(cfg["cues"], key=lambda c: (c[0], c[1]))
    texts = [c[3] for c in cues]

    for group, entries in led.items():
        if group.startswith("_"):
            continue
        for e in entries:
            if not applies(e, name):
                continue
            rule, val, req = e["規則"], e["值"], e["要求"]
            if rule == "present":
                ok.append((f"[{group}] {req}", any(val in t for t in texts)))
            elif rule == "absent":
                ok.append((f"[{group}] {req}", not any(val in t for t in texts)))
            elif rule == "詞不切斷":
                words = COMMON_WORDS if val == "*" else [val]
                bad = [
                    a[3][-1] + b[3][0]
                    for a, b in zip(cues, cues[1:])
                    if a[0] == b[0] and b[1] - a[2] <= 1.5 and (a[3][-1] + b[3][0]) in words
                ]
                ok.append((f"[{group}] {req}" + (f"（切斷：{bad}）" if bad else ""), not bad))
            elif rule == "起點早於":
                txt, limit = val
                hit = [c for c in cues if txt in c[3]]
                ok.append((f"[{group}] {req}", bool(hit) and hit[0][1] <= limit))
            elif rule == "cover_intro>0":
                ok.append((f"[{group}] {req}", float(cfg.get("cover_intro", 0)) > 0))
            elif rule == "bgm_vol":
                ok.append((f"[{group}] {req}", abs(cfg.get("bgm_vol", 0.15) - val) < 0.001))


def check_readability(cfg, ok):
    """觀看品質：字幕要來得及讀、不可互相重疊。"""
    speed = cfg.get("speed", 1.3)
    cues = sorted(cfg["cues"], key=lambda c: (c[0], c[1]))
    slow = [
        c[3]
        for c in cues
        if len(c[3]) and (c[2] - c[1]) / speed / len(c[3]) < 0.13
    ]
    ok.append((f"字幕來得及讀（太快 {len(slow)} 句）" + (f"：{slow[:2]}" if slow else ""), not slow))
    overlap = [
        (a[3][:8], b[3][:8])
        for a, b in zip(cues, cues[1:])
        if a[0] == b[0] and b[1] < a[2] - 0.05
    ]
    ok.append((f"字幕無重疊（{len(overlap)} 處）", not overlap))


def load_wav(path):
    w = wave.open(path, "rb")
    sr = w.getframerate()
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    return a / 32768.0, sr


def db(x):
    return float(20 * np.log10(np.sqrt(np.mean(x**2)) + 1e-9)) if len(x) else None


def to_wav(src, out, extra=None):
    subprocess.run(
        ["ffmpeg", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000"]
        + (extra or [])
        + [out],
        capture_output=True,
    )


def ranges_in_output(cfg, kind):
    """把逐字稿的講者區間換算到輸出時間軸。kind: mine / others / gaps"""
    import glob

    speed, intro = cfg.get("speed", 1.3), float(cfg.get("cover_intro", 1.0))
    mine, others, spoken, cum = [], [], [], 0.0
    for x in cfg["segments"]:
        v = list(x["v"]) if isinstance(x, dict) else list(x)
        vi, s, e = v
        base = os.path.splitext(os.path.basename(cfg["videos"][vi]))[0]
        hits = [f for f in glob.glob(f"素材/transcripts/{base}*.json") if "scribe" in f]
        segs = json.load(open(hits[0], encoding="utf-8")) if hits else []
        seg_span = (intro + cum / speed, intro + (cum + (e - s)) / speed)
        cur = []
        for t in segs:
            if t["end"] <= s or t["start"] >= e or len(t["text"]) < 3:
                continue
            a = intro + (cum + max(0.0, t["start"] - s)) / speed
            b = intro + (cum + min(e - s, t["end"] - s)) / speed
            cur.append((a, b))
            (mine if t.get("fg") else others).append((a, b))
        t0 = seg_span[0]
        for a, b in sorted(cur):
            if a - t0 > 0.6:
                spoken.append((t0, a))
            t0 = max(t0, b)
        if seg_span[1] - t0 > 0.6:
            spoken.append((t0, seg_span[1]))
        cum += e - s
    return {"mine": mine, "others": others, "gaps": spoken}[kind]


def slice_db(A, sr, ranges):
    ch = [A[int(a * sr) : int(b * sr)] for a, b in ranges]
    ch = [c for c in ch if len(c)]
    return db(np.concatenate(ch)) if ch else None


def audio_checks(cfg, A, sr, ok):
    peak = float(20 * np.log10(np.abs(A).max() + 1e-9))
    ok.append((f"峰值 {peak:.2f}dB（上限 {PEAK_MAX}）", peak <= PEAK_MAX))
    ok.append(
        (f"滿格取樣 {(np.abs(A) > 0.98).sum()} 個", (np.abs(A) > 0.98).sum() == 0)
    )

    mine = ranges_in_output(cfg, "mine")
    if mine:
        seg = np.concatenate([A[int(a * sr) : int(b * sr)] for a, b in mine if b > a])
        crest = float(20 * np.log10(np.abs(seg).max() + 1e-9)) - db(seg)
        # 這一項是「爆音」的真正指標：峰值正常但被壓扁時只有它會掉
        ok.append(
            (f"人聲動態 crest {crest:.1f}dB（下限 {CREST_MIN}）", crest >= CREST_MIN)
        )

    m = slice_db(A, sr, mine) if mine else None
    o = slice_db(A, sr, ranges_in_output(cfg, "others"))
    g = slice_db(A, sr, ranges_in_output(cfg, "gaps"))
    if m is not None and o is not None:
        ok.append(
            (f"你 {m:.1f} / 旁人 {o:.1f}（差 {m-o:+.1f}dB）", abs(m - o) <= SPEAKER_GAP)
        )
    if m is not None and g is not None:
        ok.append((f"雜音 {g:.1f}dB，低於人聲 {m-g:.1f}dB", (m - g) >= NOISE_MARGIN))
    return m


def segment_consistency(cfg, A, sr, ok):
    """段與段之間不該忽大忽小——長片最容易出這個問題。"""
    speed, intro = cfg.get("speed", 1.3), float(cfg.get("cover_intro", 1.0))
    levels, cum = [], 0.0
    for x in cfg["segments"]:
        v = list(x["v"]) if isinstance(x, dict) else list(x)
        _, s, e = v
        a, b = intro + cum / speed, intro + (cum + (e - s)) / speed
        seg = A[int(a * sr) : int(b * sr)]
        if len(seg):
            levels.append(db(seg))
        cum += e - s
    if len(levels) > 1:
        spread = max(levels) - min(levels)
        ok.append((f"段間音量落差 {spread:.1f}dB（上限 8）", spread <= 8.0))


def report(title, ok):
    print(f"\n{'='*62}\n{title}\n{'='*62}")
    for name, passed in ok:
        print(f"  {'✅' if passed else '❌'} {name}")
    bad = [n for n, p in ok if not p]
    print("\n" + ("✅ 全部通過" if not bad else f"❌ {len(bad)} 項未過，先修再繼續"))
    return not bad


def preflight(config):
    """只算音訊、不渲畫面——1 分鐘內驗出音訊鏈有沒有問題。"""
    cfg = json.load(open(config, encoding="utf-8"))
    env = lambda k, d=None: os.environ.get(k, d)
    tmp = tempfile.mkdtemp()
    print("重建音訊（不渲畫面）...", flush=True)
    audio = rr.rebuild_audio(
        cfg,
        float(env("BGM_VOL", "0.05")),
        tmp,
        voice_boost=float(env("VOICE_BOOST", "0")),
        voice_target=float(env("VOICE_TARGET")) if env("VOICE_TARGET") else None,
        denoise=env("DENOISE", "") not in ("", "0"),
        duck=float(env("DUCK", "0")),
        match=env("MATCH", "") not in ("", "0"),
        seg_norm=float(env("SEG_NORM")) if env("SEG_NORM") else None,
    )
    wav = os.path.join(tmp, "chk.wav")
    to_wav(audio, wav)
    A, sr = load_wav(wav)
    # preflight 的音訊沒有封面卡靜音，補上才對得齊輸出時間軸
    intro = float(cfg.get("cover_intro", 1.0))
    A = np.concatenate([np.zeros(int(intro * sr), dtype=np.float32), A])
    ok = []
    name = os.path.basename(config)
    check_requirements(cfg, name, ok)
    check_readability(cfg, ok)
    audio_checks(cfg, A, sr, ok)
    segment_consistency(cfg, A, sr, ok)
    return report(f"渲染前檢查點：{cfg['subject']}", ok)


def final(config, mp4):
    cfg = json.load(open(config, encoding="utf-8"))
    ok = []
    info = subprocess.run(["ffmpeg", "-i", mp4], capture_output=True).stderr.decode()
    ok.append(("解析度 1080x1920", "1080x1920" in info))
    # 接片尾後 concat 會讓平均幀率變成 23.98（tbr 仍是 24），等同 24fps 標準
    fps = re.search(r"([\d.]+) fps", info)
    fps = float(fps.group(1)) if fps else 0
    ok.append((f"幀率 {fps} fps（23.9~24.1）", 23.9 <= fps <= 24.1))
    ok.append(("固定幀率 CFR（tbr 24）", "24 tbr" in info))
    ok.append(("色彩 yuv420p(tv)", "yuv420p(tv" in info or "yuv420p," in info))
    d = open(mp4, "rb").read(4_000_000)
    sz = os.path.getsize(mp4)
    ok.append(("faststart（moov 在檔頭）", 0 <= d.find(b"moov") < sz * 0.05))
    err = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-f", "null", "-"],
                         capture_output=True).stderr.decode().strip()  # fmt: skip
    ok.append((f"解碼無錯{('：' + err[:40]) if err else ''}", not err))

    tmp = tempfile.mkdtemp()
    wav = os.path.join(tmp, "a.wav")
    to_wav(mp4, wav)
    A, sr = load_wav(wav)
    check_requirements(cfg, os.path.basename(config), ok)
    check_readability(cfg, ok)
    audio_checks(cfg, A, sr, ok)
    segment_consistency(cfg, A, sr, ok)
    dur = float([l for l in info.split("\n") if "Duration" in l][0].split(",")[0].split()[-1]
                .replace(":", " ").split()[-1]) if "Duration" in info else 0
    ok.append(("片尾已接上（長度含 1.6s 片尾）", dur > 1.0))
    return report(f"成品驗證：{os.path.basename(mp4)}", ok)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    if sys.argv[1] == "preflight":
        return 0 if preflight(sys.argv[2]) else 1
    if sys.argv[1] == "final" and len(sys.argv) > 3:
        return 0 if final(sys.argv[2], sys.argv[3]) else 1
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
