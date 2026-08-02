#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ElevenLabs Scribe 轉錄後端 — 產出與 reel_maker.transcribe() 完全相同的 JSON 格式。

目的是驗證「換掉本機 Whisper 是否值得」，所以刻意做成獨立腳本：
reel_maker.py 一行不動，比輸了直接刪掉這支就好。

用法：
  python3 tools/transcribe_scribe.py scribe  <影片>          只跑 Scribe
  python3 tools/transcribe_scribe.py compare <影片> [秒數]    兩邊都跑並出比對報告
                                                            （秒數＝只取前 N 秒，預設 90）

金鑰：環境變數 ELEVENLABS_API_KEY，或 config/.elevenlabs_key（已被 config/ gitignore）

與 Whisper 版的關鍵差異：
  fg（前景/主講者）判定改用 Scribe 的講者分離，不再用音量門檻。
  reel_maker 現行的 −8dB 門檻會把「較小聲的對話」誤判成背景而漏掉字幕。
"""

import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import uuid
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reel_maker as rm

API = "https://api.elevenlabs.io/v1/speech-to-text"
KEY_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    ".elevenlabs_key",
)
PAUSE_SPLIT = 0.7  # 停頓超過這個秒數就切下一個 segment


def load_key():
    k = os.environ.get("ELEVENLABS_API_KEY", "")
    if not k and os.path.exists(KEY_FILE):
        k = open(KEY_FILE, encoding="utf-8").read().strip()
    if not k:
        sys.exit(
            f"找不到金鑰。請設 ELEVENLABS_API_KEY 環境變數，或把金鑰寫進 {KEY_FILE}"
        )
    return k


def post_multipart(url, key, filepath, fields):
    """純 urllib 手組 multipart，維持本專案不裝額外套件的慣例。"""
    boundary = uuid.uuid4().hex
    body = b""
    for k, v in fields.items():
        body += (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'
        ).encode()
    body += (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{os.path.basename(filepath)}"\r\n'
        f"Content-Type: audio/wav\r\n\r\n"
    ).encode()
    body += open(filepath, "rb").read() + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "xi-api-key": key,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


def wav_duration(path):
    w = wave.open(path, "rb")
    return w.getnframes() / w.getframerate()


def measure_db(wav):
    w = wave.open(wav, "rb")
    sr = w.getframerate()
    a = (
        np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
        / 32768.0
    )

    def db(s, e):
        seg = a[int(s * sr) : int(e * sr)]
        return (
            float(20 * np.log10(np.sqrt(np.mean(seg**2)) + 1e-9)) if len(seg) else -99.0
        )

    return db


def to_traditional(text):
    """Scribe 一律吐簡體，轉成台灣繁體。

    s2twp 連詞彙一起換（软件→軟體），但會把 台灣 寫成 臺灣，
    與品牌既有用字不符，最後統一改回「台」。
    """
    try:
        from opencc import OpenCC
    except ImportError:
        return text
    global _CC
    if "_CC" not in globals():
        _CC = OpenCC("s2twp")
    return _CC.convert(text).replace("臺", "台")


def group_words(words):
    """Scribe 回傳詞流，依「講者切換」或「長停頓」切成 segment。"""
    segs = []
    cur = None
    for w in words:
        if w.get("type") != "word":
            continue
        txt = (w.get("text") or "").strip()
        if not txt:
            continue
        spk = w.get("speaker_id", "S0")
        s, e = float(w["start"]), float(w["end"])
        if cur and (spk != cur["spk"] or s - cur["end"] > PAUSE_SPLIT):
            segs.append(cur)
            cur = None
        if cur is None:
            cur = {"spk": spk, "start": s, "end": e, "words": []}
        cur["end"] = e
        cur["words"].append({"w": txt, "s": round(s, 2), "e": round(e, 2)})
    if cur:
        segs.append(cur)
    return segs


def to_reel_format(segs, db_fn):
    """轉成 reel_maker 的 transcript JSON；fg 用講者判定而非音量。"""
    if not segs:
        return []
    talk = {}
    for s in segs:
        talk[s["spk"]] = talk.get(s["spk"], 0.0) + (s["end"] - s["start"])
    main_spk = max(talk, key=talk.get)

    out = []
    for s in segs:
        out.append(
            {
                "start": round(s["start"], 2),
                "end": round(s["end"], 2),
                "text": to_traditional("".join(w["w"] for w in s["words"])),
                "db": round(db_fn(s["start"], s["end"]), 1),
                "words": [{**w, "w": to_traditional(w["w"])} for w in s["words"]],
                "fg": s["spk"] == main_spk,
                "speaker": s["spk"],
            }
        )
    return out


def run_scribe(video, limit_sec=None):
    wav = tempfile.mktemp(suffix=".wav")
    cmd = ["ffmpeg", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000"]
    if limit_sec:
        cmd += ["-t", str(limit_sec)]
    subprocess.run(cmd + [wav], capture_output=True)

    dur = wav_duration(wav)
    print(f"  音訊長度 {dur:.1f}s（{dur/60:.1f} 分）→ 送 Scribe...", flush=True)

    data = post_multipart(
        API,
        load_key(),
        wav,
        {
            "model_id": "scribe_v1",
            "language_code": "zho",
            "diarize": "true",
            "tag_audio_events": "true",
            "timestamps_granularity": "word",
        },
    )
    words = data.get("words", [])
    if not words:
        print("  ⚠️ 回應沒有 words 欄位，原始回應前 400 字：")
        print("  " + json.dumps(data, ensure_ascii=False)[:400])
    segs = to_reel_format(group_words(words), measure_db(wav))
    os.remove(wav)

    spks = sorted({s["speaker"] for s in segs})
    print(f"  Scribe：{len(segs)} 段、講者 {len(spks)} 位 {spks}")
    return segs


def run_whisper(video, limit_sec=None):
    if limit_sec:
        clip = tempfile.mktemp(suffix=".mov")
        subprocess.run(
            ["ffmpeg", "-y", "-i", video, "-t", str(limit_sec), "-c", "copy", clip],
            capture_output=True,
        )
        video = clip
    print("  Whisper small 轉錄中（Intel CPU 很慢，約 1~3 倍實時）...", flush=True)
    segs = rm.transcribe(video)
    print(f"  Whisper：{len(segs)} 段")
    return segs


def load_corrections():
    p = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "whisper_corrections.json"
    )
    raw = json.load(open(p, encoding="utf-8"))
    return {
        wrong: right
        for g, pairs in raw.items()
        if not g.startswith("_")
        for wrong, right in pairs.items()
    }


def compare(video, limit_sec):
    print(f"\n素材：{os.path.basename(video)}（只取前 {limit_sec}s 做比對）\n")
    print("[1/2] Scribe")
    sc = run_scribe(video, limit_sec)
    print("[2/2] Whisper")
    wh = run_whisper(video, limit_sec)

    corr = load_corrections()

    def known_errors(segs):
        hits = []
        for s in segs:
            for wrong, right in corr.items():
                if wrong in s["text"]:
                    hits.append((s["start"], wrong, right))
        return hits

    sc_err, wh_err = known_errors(sc), known_errors(wh)
    sc_fg = sum(1 for s in sc if s["fg"])
    wh_fg = sum(1 for s in wh if s["fg"])

    print("\n" + "=" * 64)
    print("{:<26} {:>16} {:>16}".format("項目", "Scribe", "Whisper"))
    print("-" * 64)
    rows = [
        ("段數", len(sc), len(wh)),
        ("總字數", sum(len(s["text"]) for s in sc), sum(len(s["text"]) for s in wh)),
        ("判為前景的段數", f"{sc_fg}/{len(sc)}", f"{wh_fg}/{len(wh)}"),
        ("命中已知錯字", len(sc_err), len(wh_err)),
    ]
    for name, a, b in rows:
        print("{:<26} {:>16} {:>16}".format(name, str(a), str(b)))
    print("=" * 64)

    for label, errs in (("Scribe", sc_err), ("Whisper", wh_err)):
        if errs:
            print(f"\n{label} 命中的已知錯字：")
            for t, wrong, right in errs:
                print(f"  {t:6.1f}s 「{wrong}」→ 是不是 {right}？")

    out = os.path.splitext(video)[0] + "_轉錄比對.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# 轉錄比對：{os.path.basename(video)}（前 {limit_sec}s）\n\n")
        f.write("兩邊聽到的內容並排，請人工判斷哪邊正確。\n\n")
        f.write("## Scribe\n\n")
        for s in sc:
            tag = "" if s["fg"] else "（背景）"
            f.write(
                f'- `{s["start"]:6.1f}-{s["end"]:5.1f}` [{s["speaker"]}]{tag} {s["text"]}\n'
            )
        f.write("\n## Whisper\n\n")
        for s in wh:
            tag = "" if s["fg"] else "（背景）"
            f.write(f'- `{s["start"]:6.1f}-{s["end"]:5.1f}`{tag} {s["text"]}\n')
    print(f"\n並排逐字稿已寫入：{out}")
    print("→ 請人工看過，數一下哪邊錯字少、前景判定哪邊準")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    mode, video = sys.argv[1], os.path.expanduser(sys.argv[2])
    if not os.path.exists(video):
        sys.exit(f"找不到影片：{video}")
    if mode == "scribe":
        segs = run_scribe(video)
        out = os.path.splitext(video)[0] + "_transcript_scribe.json"
        json.dump(segs, open(out, "w"), ensure_ascii=False, indent=1)
        print("已寫入", out)
    elif mode == "compare":
        compare(video, int(sys.argv[3]) if len(sys.argv) > 3 else 90)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
