"""中新網 2020 陽澄湖開捕影片（CC BY 3.0）剪成 8 秒以上 b-roll：裁掉左上角台標、去聲音、1080p。

用法：python3 finance_shorts/cn-01/cut_clips.py <Commons 原始 webm>
"""

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "shared" / "broll"
SHOTS = {
    "boats": (11.83, 23.23),
    "netting": (23.43, 28.03),
    "net": (39.91, 45.15),
    "net2": (45.35, 47.87),
    "tank": (100.2, 102.4),
    "under": (102.7, 106.7),
    "pack": (106.91, 109.87),
    "scale": (114.55, 117.27),
    "clasp": (117.47, 119.55),
    "crate": (119.75, 122.43),
    "tags": (122.63, 127.99),
}
CLIPS = {
    "cr_boats_01": [("boats", 0.6, 6.4, 11.4)],
    "cr_net_00": [("net", 0.62, 0, 5.24)],
    "cr_net_01": [("netting", 0.6, 0, 2.6), ("net2", 0.65, 0, 2.52)],
    "cr_pack_00": [("scale", 0.6, 0, 2.72), ("crate", 0.75, 0, 2.68)],
    "cr_tags_00": [("tags", 0.62, 0, 5.36)],
    "cr_tags_01": [("clasp", 0.6, 0, 2.08), ("tags", 1, 0, 5.36)],
    "cr_under_00": [("under", 0.48, 0, 4.0)],
    "cr_tank_00": [("tank", 0.55, 0, 2.2), ("under", 1, 0, 4.0)],
}
NO_SUBS = {"cr_net_00", "cr_net_01", "cr_pack_00", "cr_boats_00", "cr_boats_01"}
CREDIT = {
    "channel": "中國新聞網（經 Wikimedia Commons）",
    "title": "2020年9月21日 苏州阳澄湖大闸蟹开捕 总产量预计超1万吨",
    "url": "https://commons.wikimedia.org/wiki/File:2020年9月21日_苏州阳澄湖大闸蟹开捕_总产量预计超1万吨.webm",
    "license": "CC BY 3.0；已裁切、變速、去除聲音",
}


def cut(src, name, plan):
    # 2020 年的旁白字幕燒在畫面下方，要裁掉才不會出現舊數字
    crop = "crop=960:540:160:90" if name in NO_SUBS else "crop=1127:634:153:86"
    parts, labels = [], []
    for i, (shot, speed, a, b) in enumerate(plan):
        s = SHOTS[shot][0]
        parts.append(
            f"[0:v]trim={s + a}:{s + b},setpts=(PTS-STARTPTS)/{speed},fps=30,"
            f"{crop},scale=1920:1080:out_color_matrix=bt709,format=yuv420p[s{i}]"
        )
        labels.append(f"[s{i}]")
    graph = ";".join(parts) + f";{''.join(labels)}concat=n={len(labels)}:v=1:a=0[v]"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", graph, "-map", "[v]", "-an",
         "-c:v", "libx264", "-threads", "2", "-preset", "medium", "-crf", "20",
         "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
         "-movflags", "+faststart", str(OUT / f"{name}.mp4")],
        check=True,
    )  # fmt: skip


if __name__ == "__main__":
    for name, plan in CLIPS.items():
        cut(sys.argv[1], name, plan)
        print(name)
    p = OUT / "credits.json"
    d = json.loads(p.read_text())
    d.update({n: {"id": "commons", **CREDIT} for n in CLIPS})
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1))
