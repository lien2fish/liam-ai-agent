#!/usr/bin/env python3
"""把腳本組裝成一支 1080x1920 Shorts MP4。

流程：FLUX 生場景插圖 → edge-tts 英文旁白(含字級時間軸) → ffmpeg Ken Burns + 燒錄字幕。
只用 stdlib + requests + edge-tts + 系統 ffmpeg。
"""
import json, os, io, asyncio, platform, subprocess, tempfile, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)

W, H = 1080, 1920
FPS = 30
VOICE = os.environ.get("YT_VOICE", "en-US-AriaNeural")  # 柔和女聲（療癒系）
RATE = os.environ.get("YT_RATE", "-8%")  # 放慢語速，更舒緩
# 中文字幕字型：macOS 用黑體-繁，Linux(GitHub Actions) 用 Noto CJK
CJK_FONT = "Heiti TC" if platform.system() == "Darwin" else "Noto Sans CJK TC"

# 頻道固定吉祥物——每支影片結尾出現、面向觀眾「對你說話」
MASCOT_SCENE = (
    "Mochi the cozy channel mascot, a small round cream-colored cat with a tiny "
    "glowing crescent moon mark on its forehead, big gentle sleepy eyes, sitting and "
    "facing the viewer with a warm caring expression as if softly speaking to you, "
    "soft pastel storybook style, dreamy cozy bokeh background"
)
# 背景音樂（療癒墊音）；可用 YT_BGM 指定，預設 youtube_auto/bgm.mp3
_bgm_default = os.path.join(BASE, "bgm.mp3")
BGM = os.environ.get("YT_BGM") or (_bgm_default if os.path.exists(_bgm_default) else "")
HF_URL = (
    "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
)


def _hf_token():
    if os.environ.get("HF_TOKEN"):
        return os.environ["HF_TOKEN"]
    cfg = os.path.join(REPO, "config", "instagram_config.json")
    return json.load(open(cfg)).get("hf_token", "") if os.path.exists(cfg) else ""


HF_TOKEN = _hf_token()


def gen_image(prompt, out_path):
    full = (
        f"{prompt}, soft pastel storybook illustration, cozy and dreamy, "
        "Studio Ghibli inspired, gentle warm lighting, kawaii, calming soft colors, "
        "hand-drawn animation style, vertical composition, no text, no watermark"
    )
    req = urllib.request.Request(
        HF_URL,
        data=json.dumps({"inputs": full}).encode(),
        headers={
            "Authorization": f"Bearer {HF_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        open(out_path, "wb").write(r.read())


async def _synth_one(text, mp3_path):
    import edge_tts

    comm = edge_tts.Communicate(text, VOICE, rate=RATE)
    with open(mp3_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])


def synth_sentences(sentences, mp3_path, tmp):
    """逐句配音→量測時長→串接成單一 mp3，回傳每句 (start,dur) 供字幕對齊"""
    parts, segs, cursor = [], [], 0.0
    for i, s in enumerate(sentences):
        p = os.path.join(tmp, f"s_{i}.mp3")
        asyncio.run(_synth_one(s, p))
        d = get_duration(p)
        segs.append({"start": cursor, "dur": d})
        cursor += d
        parts.append(p)
    lst = os.path.join(tmp, "alist.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            lst,
            "-c",
            "copy",
            mp3_path,
        ],
        check=True,
        capture_output=True,
    )
    return segs


def _ass_time(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def _is_cjk(s):
    return any("㐀" <= c <= "鿿" for c in s)


def build_captions(segs, texts, ass_path):
    """每個句子時間段配上對應字幕（CJK 依字數、拉丁依詞數切短句，時間等分）"""
    groups = []  # (start, end, text)
    for seg, raw in zip(segs, texts):
        raw = (raw or "").strip().replace("\n", " ")
        if not raw:
            continue
        cjk = _is_cjk(raw)
        units = list(raw) if cjk else raw.split()
        size, join = (11, "") if cjk else (5, " ")
        per = seg["dur"] / max(1, len(units))
        for i in range(0, len(units), size):
            chunk = units[i : i + size]
            start = seg["start"] + i * per
            end = seg["start"] + (i + len(chunk)) * per
            txt = join.join(chunk)
            groups.append((start, end, txt if cjk else txt.upper()))

    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Cap, {CJK_FONT}, 82, &H00FFFFFF, &H00000000, &H64000000, 1, 1, 6, 3, 2, 70, 70, 520, 1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines = []
    for start, end, txt in groups:
        lines.append(
            f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Cap,,0,0,0,,{txt}"
        )
    open(ass_path, "w", encoding="utf-8").write(header + "\n".join(lines) + "\n")


def kenburns_clip(img, dur, out):
    frames = max(1, int(dur * FPS))
    vf = (
        f"scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
        f"zoompan=z='min(zoom+0.0004,1.10)':d={frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
        f"format=yuv420p"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            img,
            "-t",
            f"{dur:.3f}",
            "-vf",
            vf,
            "-r",
            str(FPS),
            "-an",
            out,
        ],
        check=True,
        capture_output=True,
    )


def get_duration(path):
    import re

    r = subprocess.run(["ffmpeg", "-i", path], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", r.stderr)
    if not m:
        return 0.0
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def build_video(script, out_path, workdir=None):
    tmp = workdir or tempfile.mkdtemp(prefix="ytshort_")
    scenes = script["scenes"]
    sents = script.get("sentences") or []
    en_list = [s["en"] for s in sents] if sents else [script.get("narration", "")]
    zh_list = script.get("subtitles_zh") or [s.get("zh", "") for s in sents] or en_list

    print(f"[1/4] 逐句配音 edge-tts（{VOICE}）...", flush=True)
    voice_mp3 = os.path.join(tmp, "voice.mp3")
    segs = synth_sentences(en_list, voice_mp3, tmp)
    audio_dur = get_duration(voice_mp3)
    print(f"   旁白 {audio_dur:.1f}s、{len(en_list)} 句、中文字幕對齊", flush=True)

    print(f"[2/4] 生成 {len(scenes)} 張場景插圖 + 吉祥物結尾（FLUX）...", flush=True)
    imgs = []
    for i, sc in enumerate(scenes):
        p = os.path.join(tmp, f"scene_{i}.png")
        gen_image(sc, p)
        imgs.append(p)
        print(f"   場景 {i+1}/{len(scenes)} 完成", flush=True)
    # 結尾固定吉祥物（面向觀眾說話）
    mp = os.path.join(tmp, "mascot.png")
    gen_image(MASCOT_SCENE, mp)
    imgs.append(mp)
    print("   吉祥物結尾完成", flush=True)

    print("[3/4] 製作中文字幕 + Ken Burns 片段...", flush=True)
    ass = os.path.join(tmp, "caps.ass")
    build_captions(segs, zh_list, ass)
    per = (audio_dur + 0.6) / len(imgs)  # 多 0.6s 收尾
    clips = []
    for i, img in enumerate(imgs):
        c = os.path.join(tmp, f"clip_{i}.mp4")
        kenburns_clip(img, per, c)
        clips.append(c)

    concat_list = os.path.join(tmp, "list.txt")
    open(concat_list, "w").write("".join(f"file '{c}'\n" for c in clips))
    silent = os.path.join(tmp, "silent.mp4")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list,
            "-c",
            "copy",
            silent,
        ],
        check=True,
        capture_output=True,
    )

    print("[4/4] 合成旁白(空靈殘響) + BGM + 燒錄字幕 → 最終 MP4...", flush=True)
    ass_esc = ass.replace("\\", "/").replace(":", "\\:")
    inputs = ["-i", silent, "-i", voice_mp3]
    # 旁白加殘響做空靈感
    filt = [
        f"[0:v]subtitles='{ass_esc}'[v]",
        "[1:a]aecho=0.8:0.85:60|110:0.35|0.22,highpass=f=90[va]",
    ]
    if BGM:
        inputs += ["-stream_loop", "-1", "-i", BGM]
        filt += [
            "[2:a]volume=0.16,afade=t=in:st=0:d=2[bg]",
            "[va][bg]amix=inputs=2:duration=first:dropout_transition=0[a]",
        ]
        amap = "[a]"
    else:
        amap = "[va]"
    subprocess.run(
        ["ffmpeg", "-y"]
        + inputs
        + [
            "-filter_complex",
            ";".join(filt),
            "-map",
            "[v]",
            "-map",
            amap,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-shortest",
            out_path,
        ],
        check=True,
        capture_output=True,
    )
    print(f"✅ 影片完成：{out_path}（{get_duration(out_path):.1f}s）", flush=True)
    return out_path


if __name__ == "__main__":
    import sys

    src = sys.argv[1] if len(sys.argv) > 1 else None
    if src:
        script = json.load(open(src))
    else:
        from generate_script import generate

        script = generate()
    out = os.path.join(BASE, "out.mp4")
    build_video(script, out)
