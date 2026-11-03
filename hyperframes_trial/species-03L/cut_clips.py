"""從中新網 2020 陽澄湖開捕影片（CC BY 3.0）剪出各場 b-roll，長度要超過該場旁白，畫面才不會停住。

用法：python3 cut_clips.py <Commons 原始 webm>
切點避開鏡頭交界 0.1 秒，speed 小於 1 為慢放。不用訪談與人臉特寫鏡頭。
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

SHOTS = {
    "boats": (11.83, 23.23),
    "netting": (23.43, 28.03),
    "net": (39.91, 45.15),
    "net2": (45.35, 47.87),
    "pack": (106.91, 109.87),
    "scale": (114.55, 117.27),
    "clasp": (117.47, 119.55),
    "crate": (119.75, 122.43),
    "tags": (122.63, 127.99),
}

PLAYLISTS = {
    "v_net": [("net", 1)],
    "v_tags": [("tags", 1)],
    "v_ask1": [("scale", 0.5), ("pack", 1), ("scale", 1), ("crate", 1)],
    "v_split": [("net", 1), ("net2", 1), ("netting", 1), ("boats", 1)],
    "v_clasp": [("clasp", 0.6), ("tags", 1), ("crate", 1), ("pack", 1), ("scale", 1)],
    "v_ch3": [("clasp", 1), ("crate", 1)],
}


def cut(src, name, playlist):
    parts, labels = [], []
    for i, (shot, speed) in enumerate(playlist):
        a, b = SHOTS[shot]
        parts.append(
            f"[0:v]trim={a}:{b},setpts=(PTS-STARTPTS)/{speed},fps=24,"
            f"scale=1280:720:out_color_matrix=bt709,format=yuv420p[s{i}]"
        )
        labels.append(f"[s{i}]")
    graph = ";".join(parts) + f";{''.join(labels)}concat=n={len(labels)}:v=1:a=0[v]"
    out = os.path.join(HERE, "assets", f"{name}.mp4")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", graph, "-map", "[v]", "-an",
         "-c:v", "libx264", "-threads", "2", "-preset", "medium", "-crf", "20",
         "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
         "-movflags", "+faststart", out],
        check=True,
    )  # fmt: skip
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-sseof", "-0.2", "-i", out, "-frames:v", "1", "-update", "1",
         "-q:v", "3", os.path.join(HERE, "assets", f"{name}_end.jpg")],
        check=True,
    )  # fmt: skip
    print(
        name, round(sum((SHOTS[s][1] - SHOTS[s][0]) / v for s, v in playlist), 2), "秒"
    )


if __name__ == "__main__":
    for name, playlist in PLAYLISTS.items():
        cut(sys.argv[1], name, playlist)
