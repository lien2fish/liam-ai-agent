#!/usr/bin/env python3
"""給成品加上自合成 BGM，音量依「這支自己的人聲響度」算出來。

為什麼不直接用 dessert_longform 的 bgm 欄位：
  ① 它會就地覆蓋，無配樂母帶就沒了。千層那批因此要改 BGM 只能整個重跑 build。
  ② 它用 amix 固定混，人聲大小不同的片子聽起來就會一支太吵一支聽不到。

這裡的做法：先把母帶複製到 無配樂母帶/，量人聲的 LUFS，
算出讓 BGM 剛好低 GAP dB 的增益，混完再過一道限幅。

用法：python3 dessert/加配樂.py <mp4> [warm|lively|halftime|happy] [GAP]
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAP = 15.0  # BGM 比人聲低幾 dB。低於 20 幾乎聽不到，低於 10 會蓋住講話

spec = importlib.util.spec_from_file_location(
    "dl", os.path.join(ROOT, "tools", "dessert_longform.py")
)
dl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dl)


def lufs(path):
    r = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            path,
            "-af",
            "loudnorm=print_format=summary",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    for line in r.stderr.splitlines():
        if "Input Integrated" in line:
            return float(line.split(":")[1].strip().split()[0])
    raise RuntimeError("量不到響度：" + path)


def main(video, style="lively", gap=GAP):
    master_dir = os.path.join(os.path.dirname(video), "無配樂母帶")
    os.makedirs(master_dir, exist_ok=True)
    master = os.path.join(master_dir, os.path.basename(video))
    if not os.path.exists(master):
        shutil.copy2(video, master)
        print(f"  母帶已存 {master}")

    dur = float(
        subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                master,
            ],
            capture_output=True,
            text=True,
        ).stdout
    )
    bed = {
        "lively": dl.gen_lively_bgm,
        "halftime": dl.gen_halftime_bgm,
        "happy": dl.gen_happy_bgm,
    }.get(style, dl.gen_warm_bgm)(dur)

    voice, music = lufs(master), lufs(bed)
    adjust = (voice - gap) - music
    out = tempfile.mktemp(suffix=".mp4")
    subprocess.run(
        # fmt: off
        ["ffmpeg", "-v", "error", "-i", master, "-i", bed,
         "-filter_complex",
         f"[1:a]volume={adjust:.2f}dB,afade=t=in:st=0:d=1.2,"
         f"afade=t=out:st={max(0, dur-1.5):.2f}:d=1.5[m];"
         # ⚠️ alimiter 的 level 預設 true＝限幅後又自動把音量拉回去，等於沒限幅。
         # dessert_longform 的母帶本身峰值就只剩 -0.4dB，混進 BGM 就爆表。
         "[0:a][m]amix=inputs=2:duration=first:normalize=0,"
         "alimiter=limit=-1.5dB:level=false[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-movflags", "+faststart", out],
        # fmt: on
        check=True,
    )
    os.replace(out, video)
    os.remove(bed)
    print(
        f"✅ {os.path.basename(video)}　{style}　人聲 {voice:.1f} LUFS／"
        f"BGM {voice-gap:.1f}（{adjust:+.1f}dB）"
    )


if __name__ == "__main__":
    main(
        sys.argv[1],
        sys.argv[2] if len(sys.argv) > 2 else "lively",
        float(sys.argv[3]) if len(sys.argv) > 3 else GAP,
    )
