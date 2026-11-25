"""把原理動畫以子母畫面疊到成品上，原聲不動。

    python3 pip.py <成品.mp4> <輸出.mp4> <動畫.mp4>@<開始秒>@<x>@<y>@<寬> ...

動畫照原長度播放（約 9 秒），外加 6px 白框。編碼參數同 tools/overlay_fx.py（yuv420p／High@4.0／faststart），
音軌直接 copy。
"""

import subprocess
import sys

src, out, *specs = sys.argv[1:]
cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", src]
chain, last = [], "0:v"
for k, spec in enumerate(specs, 1):
    path, t0, x, y, w = spec.split("@")
    cmd += ["-i", path]
    t0, w = float(t0), int(w)
    chain.append(
        f"[{k}:v]scale={w}:-2,pad=iw+12:ih+12:6:6:color=white,setpts=PTS-STARTPTS+{t0}/TB[p{k}]"
    )
    chain.append(f"[{last}][p{k}]overlay={x}:{y}:eof_action=pass[v{k}]")
    last = f"v{k}"
fps = subprocess.run(
    [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v",
        "-show_entries",
        "stream=r_frame_rate",
        "-of",
        "csv=p=0",
        src,
    ],
    capture_output=True,
    text=True,
).stdout.strip()
cmd += [
    "-filter_complex",
    ";".join(chain),
    "-map",
    f"[{last}]",
    "-map",
    "0:a?",
    "-c:v",
    "libx264",
    "-threads",
    "2",
    "-preset",
    "veryfast",
    "-crf",
    "20",
    "-pix_fmt",
    "yuv420p",
    "-profile:v",
    "high",
    "-level",
    "4.0",
    "-r",
    fps,
    "-c:a",
    "copy",
    "-movflags",
    "+faststart",
    out,
]
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode:
    raise SystemExit("❌ ffmpeg 失敗：\n" + r.stderr[-1200:])
print(f"✅ {out}")
