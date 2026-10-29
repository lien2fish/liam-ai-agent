"""實拍影片片段（B-roll）：只抓 YouTube「創用 CC 姓名標示」的影片，剪成無聲 1080p 片段。

隨便抓新聞台或別人影片會吃 Content ID／版權警告（三次刪頻道），所以：
1. 下載前先讀 YouTube 回報的授權欄位，不是 Creative Commons 一律拒絕
2. 出處（頻道、標題、網址、授權）寫進 shared/broll/credits.json，上片時列進說明欄
⚠️ 有人會把別人的影片重傳再標 CC——優先挑原創者自己拍的（街拍、空拍頻道）

用法：
  python3 finance_shorts/broll.py search "tokyo residential walk"     # 列出 CC 搜尋結果
  python3 finance_shorts/broll.py peek VIDEO_ID                       # 每 1/12 長度抽一格拼成總覽，挑時間點
  python3 finance_shorts/broll.py take 名稱 VIDEO_ID 開始秒 長度秒      # 剪出 shared/broll/名稱.mp4
"""

import json
import pathlib
import subprocess
import sys

from build import ROOT

YTDLP = str(pathlib.Path.home() / ".local/share/ytdlp-venv/bin/yt-dlp")
OUT = ROOT / "shared" / "broll"
CC = "EgIwAQ%253D%253D"  # YouTube 搜尋的「創用 CC」篩選


def ytdlp(*args):
    return subprocess.run(
        [YTDLP, "--no-warnings", *args], capture_output=True, text=True
    )


def info(vid):
    r = ytdlp("-J", "--skip-download", f"https://www.youtube.com/watch?v={vid}")
    return json.loads(r.stdout)


def search(q):
    url = f"https://www.youtube.com/results?search_query={q.replace(' ', '+')}&sp={CC}"
    print(
        ytdlp(
            "--flat-playlist",
            "--playlist-end",
            "10",
            "--print",
            "%(id)s|%(duration)s|%(channel)s|%(title)s",
            url,
        ).stdout
    )


def peek(vid):
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / f"_peek_{vid}.mp4"
    ytdlp(
        "-f",
        "bv*[height<=360]",
        "-o",
        str(tmp),
        f"https://www.youtube.com/watch?v={vid}",
    )
    d = float(
        subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(tmp),
            ],
            capture_output=True,
            text=True,
        ).stdout
    )
    step = d / 13
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(tmp),
            "-vf",
            f"fps=1/{step:.2f},scale=320:-1,drawtext=text='%{{pts\\:hms}}':x=6:y=6:fontsize=20:fontcolor=yellow:box=1:boxcolor=black,tile=4x3",
            "-frames:v",
            "1",
            str(OUT / f"_peek_{vid}.png"),
        ],
        check=True,
    )
    print(f"  {d:.0f} 秒，每 {step:.0f} 秒一格 → {OUT / f'_peek_{vid}.png'}")


def take(name, vid, start, dur):
    meta = info(vid)
    lic = meta.get("license") or ""
    if "creative commons" not in lic.lower():
        raise SystemExit(
            f"⛔ {vid} 授權是「{lic or '標準 YouTube 授權'}」，不是創用 CC，不能用"
        )
    OUT.mkdir(parents=True, exist_ok=True)
    raw = OUT / f"_raw_{name}.mp4"
    start, dur = float(start), float(dur)
    ytdlp(
        "-f",
        "bv*[height<=1080][ext=mp4]/bv*[height<=1080]",
        "--download-sections",
        f"*{start}-{start + dur + 1}",
        "--force-keyframes-at-cuts",
        "-o",
        str(raw),
        f"https://www.youtube.com/watch?v={vid}",
    )
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(raw),
            "-t",
            str(dur),
            "-an",
            "-vf",
            "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=24",
            "-c:v",
            "libx264",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            str(OUT / f"{name}.mp4"),
        ],
        check=True,
    )
    raw.unlink()
    cpath = OUT / "credits.json"
    credits = json.loads(cpath.read_text()) if cpath.exists() else {}
    credits[name] = {
        "id": vid,
        "title": meta.get("title"),
        "channel": meta.get("channel"),
        "url": f"https://www.youtube.com/watch?v={vid}",
        "license": lic,
        "start": start,
        "dur": dur,
    }
    cpath.write_text(json.dumps(credits, ensure_ascii=False, indent=1))
    print(f"  ✅ {name}.mp4  {dur:.1f}s  {meta.get('channel')}｜{lic}")


if __name__ == "__main__":
    cmd, *a = sys.argv[1:]
    {"search": search, "peek": peek, "take": take}[cmd](*a)
