#!/usr/bin/env python3
"""把腳本組裝成一支 1080x1920 Shorts MP4。

流程：FLUX 生場景插圖 → edge-tts 英文旁白(含字級時間軸) → ffmpeg Ken Burns + 燒錄字幕。
只用 stdlib + requests + edge-tts + 系統 ffmpeg。
"""
import json, os, io, asyncio, platform, random, subprocess, tempfile, time, urllib.parse, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)

W, H = 1080, 1920
FPS = 30
VOICE = os.environ.get("YT_VOICE", "en-US-GuyNeural")  # 沉穩男聲（神秘/史詩感）
RATE = os.environ.get("YT_RATE", "-3%")  # 略慢增添份量
# 中文字幕字型：macOS 用黑體-繁，Linux(GitHub Actions) 用 Noto CJK
CJK_FONT = "Heiti TC" if platform.system() == "Darwin" else "Noto Sans CJK TC"

# 頻道固定收尾角色——每支影片結尾出現、面向觀眾「對你說話」
MASCOT_SCENE = (
    "A wise great horned owl with luminous amber eyes, perched on an ancient weathered "
    "stone beneath a vast star-filled night sky and a faint glowing nebula, looking "
    "directly toward the viewer as if about to reveal a secret, cinematic, dramatic "
    "moonlight, atmospheric, photoreal, highly detailed"
)
# 背景音樂（療癒墊音）；可用 YT_BGM 指定，預設 youtube_auto/bgm.mp3
_bgm_default = os.path.join(BASE, "bgm.mp3")
BGM = os.environ.get("YT_BGM") or (_bgm_default if os.path.exists(_bgm_default) else "")
# 改用 Pollinations.ai 免費生圖（免金鑰，底層 FLUX）；HF FLUX 免費額度已用罄(402)
POLLI_URL = "https://image.pollinations.ai/prompt/"


def gen_image(prompt, out_path):
    full = (
        f"{prompt}, cinematic, epic and awe-inspiring, dramatic atmospheric lighting, "
        "highly detailed, photoreal, deep moody color grade, sense of mystery and wonder, "
        "vertical composition, no text, no watermark"
    )
    q = urllib.parse.urlencode(
        {
            "width": 1080,
            "height": 1920,
            "model": "flux",
            "nologo": "true",
            "seed": random.randint(1, 9_999_999),
        }
    )
    url = POLLI_URL + urllib.parse.quote(full) + "?" + q
    last = None
    for _ in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=180) as r:
                data = r.read()
            if data and len(data) > 5000:
                open(out_path, "wb").write(data)
                return
        except Exception as e:
            last = e
        time.sleep(5)
    raise RuntimeError(f"Pollinations 生圖失敗：{last}")


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


CJK_PUNCT = "，。！？、；：…—）」』"


def _chunk_units(units, cap_max, cjk):
    """把整句切成 ≤cap_max 的片段；CJK 盡量在標點後斷句"""
    chunks, cur = [], []
    for u in units:
        cur.append(u)
        at_punct = cjk and u in CJK_PUNCT
        if len(cur) >= cap_max or (at_punct and len(cur) >= cap_max * 0.55):
            chunks.append(cur)
            cur = []
    if cur:
        if chunks and len(cur) <= (3 if cjk else 2):
            chunks[-1] += cur  # 末段太短併回前段
        else:
            chunks.append(cur)
    return chunks


def _wrap_balanced(units, cjk, line_max):
    """把片段斷成 ≤2 行（\\N），盡量在中段標點處、兩行平衡"""
    join = "" if cjk else " "
    n = len(units)
    if n <= line_max:
        return join.join(units).strip()
    mid = n / 2
    best = round(mid)
    if cjk:
        cand = [
            i + 1
            for i, c in enumerate(units[:-1])
            if c in CJK_PUNCT and 0.3 * n <= i + 1 <= 0.7 * n
        ]
        if cand:
            best = min(cand, key=lambda i: abs(i - mid))
    return join.join(units[:best]).strip() + "\\N" + join.join(units[best:]).strip()


def build_captions(segs, texts, ass_path):
    """每句依標點自然斷句，每段為完整語意單位，過長才平衡跳兩行"""
    groups = []  # (start, end, text)
    for seg, raw in zip(segs, texts):
        raw = (raw or "").strip().replace("\n", " ")
        if not raw:
            continue
        cjk = _is_cjk(raw)
        line_max = 14 if cjk else 7
        cap_max = line_max * 2
        units = list(raw) if cjk else raw.split()
        per = seg["dur"] / max(1, len(units))
        idx = 0
        for ch in _chunk_units(units, cap_max, cjk):
            start = seg["start"] + idx * per
            end = seg["start"] + (idx + len(ch)) * per
            idx += len(ch)
            txt = _wrap_balanced(ch, cjk, line_max)
            groups.append((start, end, txt if cjk else txt.upper()))

    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Cap, {CJK_FONT}, 60, &H00FFFFFF, &H00000000, &H64000000, 1, 1, 5, 2, 2, 70, 70, 500, 1\n\n"
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
