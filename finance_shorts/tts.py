"""逐句產生配音（edge-tts），並記下每句長度給 build.py 排時間軸。

文字沒變的句子不重產——edge-tts 每次長度會浮動，重產會讓已經驗過的時間軸跑掉。

用法：python3 finance_shorts/tts.py [ins-01 ...]
"""

import asyncio
import hashlib
import json
import pathlib
import subprocess
import sys

import edge_tts

ROOT = pathlib.Path(__file__).resolve().parent
SCRIPTS = json.loads((ROOT / "scripts.json").read_text())

VOICES = {
    "cat": {"voice": "zh-TW-HsiaoYuNeural", "rate": "+8%", "pitch": "+25Hz"},
    "dog": {"voice": "zh-TW-YunJheNeural", "rate": "+6%", "pitch": "+0Hz"},
    "narr": {"voice": "zh-TW-HsiaoChenNeural", "rate": "+6%", "pitch": "+0Hz"},
}

# TTS 唸錯時，送進 TTS 的文字用同音字替代；畫面字幕仍用原文。
SAY_AS = {}


def duration(path):
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return round(float(out), 3)


# 口語寵物配音（試聽 F 版，10-16 Lien 選定）：OpenAI gpt-4o-mini-tts，可下語氣指示
OPENAI_VOICES = {"cat": "shimmer", "dog": "ballad"}
OPENAI_SPEED = 1.45  # 每秒約 4.8 字，貼近參考影片的 5 字
OPENAI_INSTR = (
    "像短影音裡的寵物配音：可愛、俏皮、有點臭屁又調皮的卡通角色口吻，語調起伏大。"
    "語速非常快，像真人在吵嘴、搶話，字和字之間不要停頓，句子之間也幾乎不停。台灣腔國語，完全不要像播報或唸稿。"
)


# 全球金錢頻道的旁白（10-19）：只有一位旁白，中英各一個聲音
NARR = {
    "zh": ("coral", "像台灣的財經 YouTuber 在講解：口語、輕快、有精神，重點數字講清楚，台灣腔國語，不要像新聞主播唸稿。"),
    "en": ("ash", "Like a friendly finance YouTuber explaining the news: conversational, upbeat, clear on the key numbers, not a stiff news anchor."),
}
NARR_SPEED = 1.25


def openai_synth(text, voice, out, instr=None, speed=None):
    import urllib.request

    key = (ROOT.parent / "config/.openai_key").read_text().strip()
    body = {"model": "gpt-4o-mini-tts", "voice": voice, "input": text, "instructions": instr or OPENAI_INSTR, "response_format": "mp3", "speed": speed or OPENAI_SPEED}
    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/speech",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        out.write_bytes(r.read())


def clone_synth(text, out, fix=False):
    """Lien 的克隆聲音（Qwen3-TTS 本機，聲音是生物特徵，產出只留本機）。只有中文旁白套發音替代表。"""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["python3", str(pathlib.Path.home() / "聲音素材/tts/say.py"), text, "-o", f"{td}/x"] + ([] if fix else ["--no-fix"]), check=True, capture_output=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{td}/x_000.wav", "-ar", "48000", "-b:a", "192k", str(out)], check=True)


async def synth(text, cfg, out):
    for k, v in SAY_AS.items():
        text = text.replace(k, v)
    if cfg.get("engine") == "clone":
        return clone_synth(text, out, cfg.get("fix", False))
    if cfg.get("engine") == "openai":
        return openai_synth(text, cfg["voice"], out, cfg.get("instr"), cfg.get("speed"))
    await edge_tts.Communicate(
        text, cfg["voice"], rate=cfg["rate"], pitch=cfg["pitch"]
    ).save(str(out))


async def run(eid):
    ep = SCRIPTS["episodes"][eid]
    adir = ROOT / eid / "audio"
    adir.mkdir(parents=True, exist_ok=True)
    meta_path = adir / "durations.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    for i, line in enumerate(ep["lines"], 1):
        if ep.get("tts") == "clone":
            cfg = {"engine": "clone", "say": line.get("say", line["text"]), "fix": ep.get("lang") == "zh"}
        elif ep.get("tts") == "openai":
            if line["speaker"] == "narr":
                v, ins = NARR[ep.get("lang", "zh")]
                cfg = {"engine": "openai", "voice": v, "speed": NARR_SPEED, "instr": ins}
            else:
                cfg = {"engine": "openai", "voice": OPENAI_VOICES[line["speaker"]], "speed": OPENAI_SPEED, "instr": OPENAI_INSTR}
        else:
            cfg = {**VOICES[line["speaker"]], **({"rate": ep["rate"]} if "rate" in ep else {})}
        sig = hashlib.sha1(
            json.dumps([line["text"], cfg, SAY_AS], ensure_ascii=False).encode()
        ).hexdigest()
        out = adir / f"l{i}.mp3"
        key = f"l{i}"
        if out.exists() and meta.get(key, {}).get("sig") == sig:
            continue
        await synth(cfg.get("say", line["text"]), cfg, out)
        meta[key] = {"sig": sig, "dur": duration(out), "text": line["text"]}
        print(f"  {eid} {key} {meta[key]['dur']:.2f}s {line['text']}")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")


def main():
    for eid in sys.argv[1:] or list(SCRIPTS["episodes"]):
        asyncio.run(run(eid))


if __name__ == "__main__":
    main()
