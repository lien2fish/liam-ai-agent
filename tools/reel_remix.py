#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只換音軌、不重編畫面 — 改 BGM 音量不必等 30 分鐘重渲。

素材收音大小差很多（同一批 IMG_4228 比 IMG_4226 大 13dB），固定的
bgm_vol 在安靜素材上就會蓋過人聲。這支依 config 重建音訊、換上新的
BGM 音量，畫面用 -c:v copy 直接沿用，零畫質損失。

用法：
  python3 tools/reel_remix.py <config.json> <新的bgm_vol> [成品mp4]
  VOICE_BOOST=6 python3 tools/reel_remix.py <config.json> 0.05   # 只放大主講者 6dB

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


def boost_filter(ranges, gain_db):
    """只在主講者說話的區間套增益，旁人音量不動。"""
    if not ranges or not gain_db:
        return ""
    cond = "+".join(f"between(t,{a:.2f},{b:.2f})" for a, b in ranges)
    return f",volume=volume={gain_db}dB:enable='{cond}'"


def rebuild_audio(cfg, bgm_vol, tmp, voice_boost=0):
    """完全比照 build() 的音訊路徑：逐段 af → concat → atempo → 混 BGM。"""
    videos = cfg["videos"] if "videos" in cfg else [cfg["video"]]
    speed = cfg.get("speed", 1.3)
    af = cfg.get("af", "highpass=f=100,afftdn=nf=-28,speechnorm=e=6.25:r=0.00015")

    parts, total = [], 0.0
    for i, x in enumerate(cfg["segments"]):
        v, a = (list(x["v"]), x.get("a")) if isinstance(x, dict) else (list(x), None)
        if "videos" not in cfg:
            v = [0] + v
        vi, s, e = v
        src_i, ss, dur = (a[0], a[1], a[2] - a[1]) if a else (vi, s, e - s)
        p = os.path.join(tmp, f"a{i}.wav")
        vf = af + boost_filter(speaker_ranges(cfg, src_i, ss, ss + dur), voice_boost)
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
        fc = (f"[0:a]atempo={speed}[va];[va][1:a]amix=inputs=2:duration=first[a]"
              if not cfg.get("mute_source") else "[1:a]anull[a]")  # fmt: skip
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
    out_dir = os.path.expanduser(cfg.get("out_dir", "~/Desktop"))
    mp4 = (
        sys.argv[3]
        if len(sys.argv) > 3
        else os.path.join(out_dir, f'{cfg["subject"]}.mp4')
    )
    if not os.path.exists(mp4):
        sys.exit(f"找不到成品：{mp4}")

    tmp = tempfile.mkdtemp()
    print(f"重建音訊（bgm_vol {vol}，主講增益 +{boost}dB）...", flush=True)
    audio = rebuild_audio(cfg, vol, tmp, boost)

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
