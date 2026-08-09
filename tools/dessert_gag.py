#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""甜點頻道迷因特效 — 在已完成的成品上疊特效，不重跑 build。

刻意做成獨立腳本：dessert_longform.py 一行不動，比輸了直接刪掉這支就好。
（同 transcribe_scribe.py 的做法）

用法：
  python3 tools/dessert_gag.py <成品mp4> <特效json> <輸出mp4>

特效 json：
  [{"t": 19.2, "text": "講廢話", "sound": "boing", "punch": true}, ...]
    t     ＝成品時間軸的秒數（不是素材時間）
    text  ＝爆出來的大字，可省略（只要音效時）
    sound ＝ boing / pop / ding / tension / none
    punch ＝ true 則整個畫面同步做一次快速放大回彈

為什麼不做「定格插入」：那會改變時間軸，得切段再 concat，
容易踩到 non-monotonic DTS（見 memory feedback_youtube_upload_reel）。
原地疊加只重編一次，時間軸不動，字幕與音訊都不會跑掉。
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import wave

import numpy as np

ZHF = "/System/Library/Fonts/STHeiti Medium.ttc"
W, H = 1080, 1920
SR = 48000

# 與 dessert_longform 字幕高光同色（橘黃 #F59C30＋深色描邊）
GAG_FILL = (245, 156, 48)
GAG_STROKE = (18, 18, 18)

POP_IN = 0.10  # 彈出動畫時長
HOLD = 0.85  # 停留時長
SCALES = (0.55, 1.18, 1.0)  # 彈出三階段：小 → 過衝 → 定位
GAIN = {"pop": 0.18, "ding": 0.15, "boing": 0.13, "tension": 0.10}


def _wave(kind, dur):
    """回傳音效的 numpy 波形（單聲道 float）。不用 ffmpeg 的 tremolo（這版 exit 222）。"""
    n = int(SR * dur)
    t = np.arange(n) / SR
    if kind == "boing":
        f = 620 * np.exp(-5.5 * t) + 90
        a = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-4.0 * t)
        a += 0.3 * np.sin(4 * np.pi * np.cumsum(f) / SR) * np.exp(-6.0 * t)
    elif kind == "pop":
        a = np.sin(2 * np.pi * 880 * t) * np.exp(-28 * t)
        a += 0.5 * np.sin(2 * np.pi * 1320 * t) * np.exp(-34 * t)
    elif kind == "ding":
        a = np.sin(2 * np.pi * 1568 * t) * np.exp(-5 * t)
        a += 0.45 * np.sin(2 * np.pi * 2093 * t) * np.exp(-7 * t)
    elif kind == "tension":
        f = 110 + 260 * t / max(dur, 1e-6)
        a = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1.0, t * 6) * 0.8
    else:
        return np.zeros(n)
    a = a / (np.max(np.abs(a)) + 1e-9)
    # 脈衝音（pop/ding）的 RMS 天生比持續音低十幾 dB，統一峰值會讓它們聽不見
    return a * GAIN.get(kind, 0.6)


def sound_track(gags, total, out, ref=None, headroom_db=5.0):
    """把所有音效寫進一條與影片等長的音軌。

    原本每個音效各自 adelay 再一起 amix，實測只有部分音效進得去——
    amix 的 dropout_transition 會在短輸入 EOF 時調整其他輸入。
    合成單一音軌後 amix 只剩兩個輸入，就沒有這個問題。

    ref 給了原片音訊時改用**自適應增益**：固定增益碰到小聲的句子就會蓋過人聲，
    所以逐點量該處人聲多大，把音效壓到低 headroom_db（5dB：量測窗與人聲起訖不會完全對齊，
    3dB 餘裕實測仍會有零點幾 dB 的微幅超出）。安靜處則保留原增益，
    不然音效會跟著一起消失。
    """
    buf = np.zeros(int(SR * total) + SR)
    for g in gags:
        k = g.get("sound", "none")
        if not k or k == "none":
            continue
        w = _wave(k, 0.9 if k == "tension" else 0.6)
        i = int(float(g["t"]) * SR)
        if ref is not None and i < len(ref):
            seg = ref[i : i + len(w)]
            if len(seg):
                ref_rms = float(np.sqrt(np.mean(seg**2)))
                w_rms = float(np.sqrt(np.mean(w**2))) + 1e-9
                target = ref_rms * (10 ** (-headroom_db / 20.0))
                # 只壓不放大：安靜段落仍用原增益，音效才不會整個消失
                w = w * min(1.0, target / w_rms)
        buf[i : i + len(w)] += w
    buf = np.clip(buf, -1.0, 1.0)
    f = wave.open(out, "wb")
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(SR)
    f.writeframes((buf * 32767).astype(np.int16).tobytes())
    f.close()
    return out


def read_audio(video):
    """抽出影片音訊供自適應增益量測用。"""
    p = tempfile.mktemp(suffix=".wav")
    subprocess.run(
        ["ffmpeg", "-i", video, "-vn", "-ar", str(SR), "-ac", "1", "-y", p,
         "-loglevel", "error"],
        capture_output=True,
    )
    w = wave.open(p, "rb")
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    w.close()
    os.remove(p)
    return a


def duration(video):
    r = subprocess.run(["ffmpeg", "-i", video], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def _esc(v):
    """filter 參數內的跳脫：冒號會被當成參數分隔、單引號會提前結束字串。"""
    return str(v).replace("\\", "\\\\").replace(":", r"\:").replace("'", r"\'")


def _rgb(c):
    return "0x%02X%02X%02X" % c


def drawtext(text, fs, s, e):
    """一段爆字。用 drawtext 而非 overlay+PNG——
    多個單幀 PNG 串成 overlay 鏈時 framesync 會互相卡住，字整個不出現。"""
    return (
        f"drawtext=fontfile='{_esc(ZHF)}':text='{_esc(text)}':"
        f"fontsize={int(fs)}:fontcolor={_rgb(GAG_FILL)}:"
        f"borderw={max(8, int(fs) // 9)}:bordercolor={_rgb(GAG_STROKE)}:"
        f"x=(w-tw)/2:y=h*0.28:enable='between(t,{s:.3f},{e:.3f})'"
    )


def build(video, gags, out):
    vparts = []
    for g in gags:
        t = float(g["t"])
        if g.get("punch"):
            a, b = t, t + 0.18
            z = f"if(between(t,{a},{b}),1+0.12*sin(3.1416*(t-{a})/{b - a}),1)"
            vparts.append(f"scale=w='iw*({z})':h='ih*({z})':eval=frame,crop={W}:{H}")
        if g.get("text"):
            for si, sc in enumerate(SCALES):
                if si == 0:
                    s0, e0 = t, t + POP_IN * 0.5
                elif si == 1:
                    s0, e0 = t + POP_IN * 0.5, t + POP_IN
                else:
                    s0, e0 = t + POP_IN, t + POP_IN + HOLD
                vparts.append(drawtext(g["text"], 150 * sc, s0, e0))

    has_sound = any(g.get("sound", "none") not in (None, "none") for g in gags)
    inputs = ["-i", video]
    fc = "[0:v]" + ",".join(vparts) + "[vout]"
    if has_sound:
        trk = sound_track(gags, duration(video), tempfile.mktemp(suffix=".wav"),
                          ref=read_audio(video))
        inputs += ["-i", trk]
        fc += (
            ";[0:a][1:a]amix=inputs=2:duration=first:normalize=0,"
            "alimiter=limit=0.7:level=disabled[aout]"
        )
        amap = "[aout]"
    else:
        amap = "0:a"

    cmd = (
        ["ffmpeg", "-y"]
        + inputs
        + [
            "-filter_complex", fc,
            "-map", "[vout]",
            "-map", amap,
            "-c:v", "libx264", "-crf", "20", "-preset", "medium",
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0", "-r", "24",
            "-c:a", "aac", "-ar", "48000", "-b:a", "160k",
            "-movflags", "+faststart",
            out,
        ]
    )
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-2500:])
        raise SystemExit("ffmpeg 失敗")
    print(f"完成：{out}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        raise SystemExit(1)
    build(sys.argv[1], json.load(open(sys.argv[2], encoding="utf-8")), sys.argv[3])
