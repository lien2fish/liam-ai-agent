#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只換音軌、不重編畫面 — 改 BGM 音量不必等 30 分鐘重渲。

素材收音大小差很多（同一批 IMG_4228 比 IMG_4226 大 13dB），固定的
bgm_vol 在安靜素材上就會蓋過人聲。這支依 config 重建音訊、換上新的
BGM 音量，畫面用 -c:v copy 直接沿用，零畫質損失。

用法：
  python3 tools/reel_remix.py <config.json> <新的bgm_vol> [成品mp4]
  VOICE_BOOST=6  python3 tools/reel_remix.py <config> 0.05   # 全片主講者 +6dB
  VOICE_TARGET=-34 python3 tools/reel_remix.py <config> 0.05  # 逐段校準到 −34dB（長片用）

主講增益用逐字稿的講者分離定位，只在主講者說話的區間套用，旁人音量不動——
對話式影片裡「對方比較大聲、自己比較小聲」就靠這個補。
"""

import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reel_maker as rm


def run(args):
    r = subprocess.run(args, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode()[-600:])


def speaker_ranges(cfg, vi, s, e):
    """從逐字稿取出「主講者」在這段裡的時間範圍，轉成段落相對秒數。

    ffmpeg 用 -ss 抽段後 t 從 0 起算，所以要扣掉段落起點。
    """
    import glob

    base = os.path.splitext(os.path.basename(cfg["videos"][vi]))[0]
    hits = [f for f in glob.glob(f"素材/transcripts/{base}*.json") if "scribe" in f]
    if not hits:
        return []
    segs = json.load(open(hits[0], encoding="utf-8"))
    return [
        (max(0.0, t["start"] - s), min(e - s, t["end"] - s))
        for t in segs
        if t.get("fg") and t["end"] > s and t["start"] < e
    ]


def measure(video, ss, dur, ranges):
    """量出指定區間集合的 RMS（dB）。"""
    import wave

    import numpy as np

    if not ranges:
        return None
    wav = tempfile.mktemp(suffix=".wav")
    run(["ffmpeg", "-y", "-ss", str(ss), "-t", str(dur), "-i", video,
         "-vn", "-ac", "1", "-ar", "8000", wav])  # fmt: skip
    w = wave.open(wav, "rb")
    sr = w.getframerate()
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    os.remove(wav)
    chunks = [a[int(x * sr) : int(y * sr)] for x, y in ranges]
    chunks = [c for c in chunks if len(c)]
    if not chunks:
        return None
    return float(20 * np.log10(np.sqrt(np.mean(np.concatenate(chunks) ** 2)) + 1e-9))


def seg_norm_gain(cfg, vi, ss, dur, target_db, cap=16.0):
    """整段（含兩人）拉到同一個目標音量。

    MATCH 只讓兩位講者在段內平衡，段與段之間的落差還在——長片九段的
    原始音量從 −31.8 到 −47.6dB，差 16dB，後半段聽起來就是「變小聲」。
    """
    rs = all_speech(cfg, vi, ss, ss + dur)
    lvl = measure(cfg["videos"][vi], ss, dur, rs)
    if lvl is None:
        return 0.0
    return round(min(cap, max(0.0, target_db - lvl)), 1)


def match_gain(cfg, vi, ss, dur, mine, cap=12.0):
    """把主講者拉到與同段旁人相同音量。

    「盡量大聲」會把峰值推到 0dBFS 爆掉；使用者要的是兩人一樣大，
    所以直接量旁人的音量當目標，不設絕對值。
    """
    others = other_ranges(cfg, vi, ss, ss + dur)
    v = cfg["videos"][vi]
    a, b = measure(v, ss, dur, mine), measure(v, ss, dur, others)
    if a is None or b is None:
        return 0.0
    return round(min(cap, max(0.0, b - a)), 1)


def segment_gain(video, ss, dur, ranges, target_db, cap=None):
    """逐段把主講者拉到同一個目標音量。

    長片橫跨多個拍攝地點，收音距離差很多（實測同一支片內主講者從 −31dB
    到 −47dB）。統一增益會把近距離那段推爆、又補不夠遠距離那段，所以
    改成逐段量測後各自校準；上限 cap 避免把環境雜訊一起放大。
    """
    import wave

    import numpy as np

    cap = float(os.environ.get("GAIN_CAP", "14")) if cap is None else cap
    if not ranges:
        return 0.0
    wav = tempfile.mktemp(suffix=".wav")
    run(["ffmpeg", "-y", "-ss", str(ss), "-t", str(dur), "-i", video,
         "-vn", "-ac", "1", "-ar", "8000", wav])  # fmt: skip
    w = wave.open(wav, "rb")
    sr = w.getframerate()
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    os.remove(wav)
    chunks = [a[int(x * sr) : int(y * sr)] for x, y in ranges]
    chunks = [c for c in chunks if len(c)]
    if not chunks:
        return 0.0
    cur = 20 * np.log10(np.sqrt(np.mean(np.concatenate(chunks) ** 2)) + 1e-9)
    return round(min(cap, max(0.0, target_db - cur)), 1)


def other_ranges(cfg, vi, s, e):
    """旁人（非主講者）說話的區間，段落相對秒數。"""
    import glob

    base = os.path.splitext(os.path.basename(cfg["videos"][vi]))[0]
    hits = [f for f in glob.glob(f"素材/transcripts/{base}*.json") if "scribe" in f]
    if not hits:
        return []
    segs = json.load(open(hits[0], encoding="utf-8"))
    return [
        (max(0.0, t["start"] - s), min(e - s, t["end"] - s))
        for t in segs
        if not t.get("fg") and t["end"] > s and t["start"] < e and len(t["text"]) >= 3
    ]


def all_speech(cfg, vi, s, e):
    """任何人說話的區間（含旁人），其餘就是純環境噪音。"""
    import glob

    base = os.path.splitext(os.path.basename(cfg["videos"][vi]))[0]
    hits = [f for f in glob.glob(f"素材/transcripts/{base}*.json") if "scribe" in f]
    if not hits:
        return []
    segs = json.load(open(hits[0], encoding="utf-8"))
    rs = sorted(
        (max(0.0, t["start"] - s - 0.25), min(e - s, t["end"] - s + 0.35))
        for t in segs
        if t["end"] > s and t["start"] < e
    )
    merged = []
    for a, b in rs:  # 合併相鄰區間，避免濾鏡條件式爆長
        if merged and a <= merged[-1][1] + 0.1:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged


def gaps_of(ranges, dur):
    out, t = [], 0.0
    for a, b in ranges:
        if a - t > 0.4:
            out.append((t, a))
        t = max(t, b)
    if dur - t > 0.4:
        out.append((t, dur))
    return out


def duck_filter(gaps, atten_db):
    """沒人說話的空檔壓低——市場環境音是寬頻噪音，降噪器修不掉，
    但那些片段本來就沒有內容，直接壓下去最有效。"""
    if not gaps or not atten_db:
        return ""
    cond = "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in gaps)
    return f",volume=volume=-{atten_db}dB:enable='{cond}'"


def boost_filter(ranges, gain_db):
    """只在主講者說話的區間套增益，旁人音量不動。"""
    if not ranges or not gain_db:
        return ""
    cond = "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in ranges)
    return f",volume=volume={gain_db}dB:enable='{cond}'"


def rebuild_audio(cfg, bgm_vol, tmp, voice_boost=0, voice_target=None,
                  denoise=False, duck=0.0, match=False, seg_norm=None):
    """完全比照 build() 的音訊路徑：逐段 af → concat → atempo → 混 BGM。"""
    videos = cfg["videos"] if "videos" in cfg else [cfg["video"]]
    speed = cfg.get("speed", 1.3)
    af = cfg.get("af", "highpass=f=100,afftdn=nf=-28,speechnorm=e=6.25:r=0.00015")
    if denoise:
        # 原鏈只做輕度降噪，且 speechnorm 在無人聲時會把環境噪音一起拉高。
        # 強化：切掉語音頻段外的低頻隆隆與高頻嘶聲、加重降噪、補人聲清晰度
        # 的 3kHz 齒音帶，最後用 limiter 保護峰值。
        af = (
            # 頻段收窄到人聲帶，切掉低頻隆隆與高頻嘶聲
            "highpass=f=160,lowpass=f=6500,"
            "afftdn=nf=-48:tn=1,"
            # 噪音閘門吃掉「同一句話裡字與字之間」的環境音——DUCK 只處理
            # 整段沒人講話的空檔，字縫要靠這個。實測字縫降 21dB、人聲只掉 0.2dB
            "agate=threshold=0.012:ratio=4:attack=8:release=180,"
            "equalizer=f=2800:t=q:w=1.4:g=5,"
            "speechnorm=e=10:r=0.0003:l=1,"
            "alimiter=limit=0.92"
        )

    parts, total = [], 0.0
    for i, x in enumerate(cfg["segments"]):
        v, a = (list(x["v"]), x.get("a")) if isinstance(x, dict) else (list(x), None)
        if "videos" not in cfg:
            v = [0] + v
        vi, s, e = v
        src_i, ss, dur = (a[0], a[1], a[2] - a[1]) if a else (vi, s, e - s)
        p = os.path.join(tmp, f"a{i}.wav")
        rg = speaker_ranges(cfg, src_i, ss, ss + dur)
        af_seg = af
        n = 0.0
        if seg_norm is not None:  # 先把整段拉齊，再讓兩人在段內平衡
            n = seg_norm_gain(cfg, src_i, ss, dur, seg_norm)
            if n:
                af_seg = af + f",volume={n}dB"
        if match:
            g = match_gain(cfg, src_i, ss, dur, rg)
        elif voice_target is not None:
            g = segment_gain(videos[src_i], ss, dur, rg, voice_target)
        else:
            g = voice_boost
        if match or voice_target is not None:
            print(f"  seg{i}: 整段 +{n}dB、主講再 +{g}dB", flush=True)
        vf = af_seg + boost_filter(rg, g)
        if duck:
            vf += duck_filter(gaps_of(all_speech(cfg, src_i, ss, ss + dur), dur), duck)
        run(["ffmpeg", "-y", "-ss", str(ss), "-t", str(dur), "-i", videos[src_i],
             "-vn", "-af", vf, "-ar", "48000", "-ac", "2", p])  # fmt: skip
        if a and dur < (e - s):  # 借音較短：補靜音到畫面長度
            p2 = os.path.join(tmp, f"a{i}pad.wav")
            run(["ffmpeg", "-y", "-i", p, "-af", f"apad=whole_dur={e-s}", p2])
            p = p2
        parts.append(p)
        total += e - s

    lst = os.path.join(tmp, "a.txt")
    open(lst, "w").write("\n".join(f"file '{p}'" for p in parts))
    joined = os.path.join(tmp, "joined.wav")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, joined])

    out = os.path.join(tmp, "final.wav")
    if cfg.get("bgm", True):
        bed = rm.bgm_bed(total / speed, bgm_vol)
        # af 鏈裡的 alimiter 只保護單段；主講增益與 BGM 都在它之後才混入，
        # 所以最終混音要再收一次，否則峰值會逼近 0dBFS
        fc = (f"[0:a]atempo={speed}[va];[va][1:a]amix=inputs=2:duration=first,"
              "alimiter=limit=0.89[a]"
              if not cfg.get("mute_source") else "[1:a]alimiter=limit=0.89[a]")  # fmt: skip
        run(["ffmpeg", "-y", "-i", joined, "-i", bed, "-filter_complex", fc,
             "-map", "[a]", out])  # fmt: skip
    else:
        run(["ffmpeg", "-y", "-i", joined, "-af", f"atempo={speed}", out])
    return out


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    vol = float(sys.argv[2])
    boost = float(os.environ.get("VOICE_BOOST", "0"))
    tgt = os.environ.get("VOICE_TARGET")
    tgt = float(tgt) if tgt else None
    dn = os.environ.get("DENOISE", "") not in ("", "0")
    duck = float(os.environ.get("DUCK", "0"))
    match = os.environ.get("MATCH", "") not in ("", "0")
    sn = os.environ.get("SEG_NORM")
    sn = float(sn) if sn else None
    out_dir = os.path.expanduser(cfg.get("out_dir", "~/Desktop"))
    mp4 = (
        sys.argv[3]
        if len(sys.argv) > 3
        else os.path.join(out_dir, f'{cfg["subject"]}.mp4')
    )
    if not os.path.exists(mp4):
        sys.exit(f"找不到成品：{mp4}")

    tmp = tempfile.mkdtemp()
    mode = ("逐段對齊旁人音量" if match else
            f"逐段校準到 {tgt}dB" if tgt is not None else f"主講增益 +{boost}dB")
    print(f"重建音訊（bgm_vol {vol}，{mode}）...", flush=True)
    audio = rebuild_audio(cfg, vol, tmp, boost, tgt, dn, duck, match, sn)

    intro = float(cfg.get("cover_intro", 1.0))
    if intro > 0:  # 成品開頭有封面卡，音軌要補上同長度的靜音才對得齊
        padded = os.path.join(tmp, "padded.wav")
        run(["ffmpeg", "-y", "-f", "lavfi", "-t", str(intro),
             "-i", "anullsrc=r=48000:cl=stereo", "-i", audio,
             "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[a]", "-map", "[a]", padded])  # fmt: skip
        audio = padded

    merged = os.path.join(tmp, "merged.mp4")
    run(["ffmpeg", "-y", "-i", mp4, "-i", audio, "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-b:a", "160k",
         "-movflags", "+faststart", "-shortest", merged])  # fmt: skip
    os.replace(merged, mp4)

    lvl = subprocess.run(["ffmpeg", "-i", mp4, "-vn", "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True).stderr.decode()  # fmt: skip
    mean = [l for l in lvl.split("\n") if "mean_volume" in l]
    print(f"✅ 已換音軌：{mp4}")
    if mean:
        print(" ", mean[0].split("]")[-1].strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
