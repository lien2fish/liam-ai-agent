"""podcast 版排版：上標題、中間 16:9 對嘴畫面、下字幕＋重點卡。

對嘴片段（lipsync.py 產出）一句一段，底下墊同一位說話者的近景靜態圖，
句與句之間的空檔不會黑掉。聲音一律用 tts.py 的配音，對嘴片段靜音。

用法：python3 finance_shorts/podcast.py ins-03p [--render]
"""

import json
import shutil
import subprocess
import sys

from build import (
    GAP,
    HF,
    hf_render,
    REPO,
    ROOT,
    SCRIPTS,
    esc,
    fade_in,
    fade_out,
    fit,
    scene_bounds,
    timeline,
)

VIDEO_TOP, VIDEO_H = 600, 608  # 1080×608 = 16:9
# 近景是從同一張合照切出來的（studio_wide.png 的裁切框），換算到成品畫面上的位置，
# 對嘴片段貼回原位、邊緣淡化，另一隻維持原圖不動。
WIDE_CROP_Y0, WIDE_SCALE = (
    140,
    1280 / 1536,
)  # studio_wide169 = studio_wide 的 (0,140)-(1536,1004)
CLOSE_BOX = {
    "cat": (0, 250, 900, 506),
    "dog": (640, 220, 896, 504),
}  # 在 studio_wide 上的 x, y, w, h
FEATHER = {
    "cat": "linear-gradient(to right, #000 0%, #000 80%, transparent 100%)",
    "dog": "linear-gradient(to left, #000 0%, #000 80%, transparent 100%)",
}


def overlay_style(who):
    x, y, w, h = CLOSE_BOX[who]
    k = WIDE_SCALE * 1080 / 1280
    left, top = x * k, VIDEO_TOP + (y - WIDE_CROP_Y0) * k
    mask = f"{FEATHER[who]}, linear-gradient(to bottom, transparent 0%, #000 12%, #000 88%, transparent 100%)"
    return (
        f"position: absolute; left: {left:.1f}px; top: {top:.1f}px; width: {w * k:.1f}px; height: {h * k:.1f}px; object-fit: fill; "
        f"-webkit-mask-image: {mask}; -webkit-mask-composite: source-in; mask-image: {mask}; mask-composite: intersect"
    )


STILL = {"cat": "shared/chars/studio_cat.png", "dog": "shared/chars/studio_dog.png"}


def build(eid):
    ep = SCRIPTS["episodes"][eid]
    two = ep.get("shot") == "two"
    clips = "lipsync_two" if two else "lipsync"
    lines, total = timeline(eid)
    scene_bounds(lines, total, SCRIPTS["episodes"][eid].get("gap", GAP))
    last_end = lines[-1]["start"] + lines[-1]["dur"] + 0.2
    lines[-1]["s1"] = round(last_end, 3)

    blocks, js = [], []
    track = 1
    title = "".join(
        f'<span class="line" style="font-size: 76px; font-weight: 800">{esc(t)}</span>'
        for t in ep["title"].split("，")
    )
    blocks.append(f'<div class="stack" id="title" style="top: 340px">{title}</div>')
    blocks.append(
        f'<div id="frame" style="position: absolute; left: 0; top: {VIDEO_TOP}px; width: 1080px; height: {VIDEO_H}px; background: #000"></div>'
    )

    for ln in lines:
        i, s0, s1 = ln["i"], ln["s0"], ln["s1"]
        pos = f"position: absolute; left: 0; top: {VIDEO_TOP}px; width: 1080px; height: {VIDEO_H}px; object-fit: cover"
        blocks.append(
            f'<img class="clip" id="st{i}" src="{"shared/chars/studio_wide169.png" if two else STILL[ln["speaker"]]}" style="{pos}" '
            f'data-start="{s0:.3f}" data-duration="{s1 - s0:.3f}" data-track-index="{track}" alt="" />'
        )
        if two and (ROOT / eid / f"lipsync_close/l{i}.mp4").exists():
            src, vpos = f"lipsync_close/l{i}.mp4", overlay_style(ln["speaker"])
        else:
            src, vpos = f"{clips}/l{i}.mp4", pos
        blocks.append(
            f'<video class="clip" id="v{i}" src="{src}" muted data-volume="0" style="{vpos}" '
            f'data-start="{ln["start"]:.3f}" data-duration="{ln["dur"]:.3f}" data-track-index="{track + 1}"></video>'
        )
        track += 2

        sid = f"s{i}"
        body = [
            f'<div class="sub" id="{sid}-sub" style="top: 1250px; font-size: 50px">{esc(ln["text"].rstrip("。"))}</div>'
        ]
        js.append(
            f'tl.fromTo("#{sid}-sub", {{ autoAlpha: 0 }}, {{ autoAlpha: 1, duration: 0.15 }}, {ln["start"]:.3f});'
        )
        sc = ln.get("screen")
        if sc:
            warn = " warn" if sc.get("warn") else ""
            color = "warn" if sc.get("warn") else "gold"
            body += [
                f'<div class="panel{warn}" id="{sid}-p" style="top: 1420px; height: 300px"></div>',
                f'<div class="tag{warn}" id="{sid}-h" style="top: 1445px; font-size: 38px">{esc(sc["head"])}</div>',
                f'<div class="stack" id="{sid}-b" style="top: 1505px"><span class="line {color}" style="font-size: {fit(sc["body"], 860, 64)}px; font-weight: 800">{esc(sc["body"])}</span></div>',
            ]
            js += [
                fade_in(f"#{sid}-p", ln["start"] + 0.2, 0, 0.3),
                fade_in(f"#{sid}-h", ln["start"] + 0.3, 16, 0.4),
                fade_in(f"#{sid}-b", ln["start"] + 0.5, 20, 0.4),
            ]
            if sc.get("cite"):
                body.append(
                    f'<div class="cite" id="{sid}-c" style="top: 1660px; font-size: 32px">{esc(sc["cite"])}</div>'
                )
                js.append(fade_in(f"#{sid}-c", ln["start"] + 0.9, 10, 0.4))
        blocks.append(
            f'<section id="{sid}" class="clip" data-start="{s0:.3f}" data-duration="{s1 - s0:.3f}" data-track-index="{track}">'
            f'<div class="sin" id="{sid}-in">' + "".join(body) + "</div></section>"
        )
        js += fade_out(f"#{sid}-in", s1 - 0.25, s1)
        track += 1

    # 片尾：合照＋資料來源
    blocks.append(
        f'<section id="end" class="clip" data-start="{last_end:.3f}" data-duration="{total - last_end:.3f}" data-track-index="{track}"><div class="sin">'
        f'<img id="wide" src="shared/chars/studio_wide.png" style="position: absolute; left: 0; top: {VIDEO_TOP}px; width: 1080px; height: {VIDEO_H}px; object-fit: cover" alt="" />'
        f'<div class="cite" id="end-c" style="top: 1300px">{esc(ep["caption"])}</div></div></section>'
    )
    js += [
        fade_in("#wide", last_end, 0, 0.3),
        fade_in("#end-c", last_end + 0.2, 10, 0.4),
    ]

    audio = "\n".join(
        f'<audio id="vo-{l["i"]}" data-start="{l["start"]:.3f}" data-duration="{l["dur"]:.3f}" src="audio/l{l["i"]}.mp3"></audio>'
        for l in lines
    )
    cid = eid.replace("-", "")
    page = f"""<!doctype html>
<html lang="zh-Hant" data-resolution="portrait">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1080, height=1920" />
<title>{esc(ep["title"])}</title>
<link rel="stylesheet" href="shared/brand.css" />
<script src="vendor/gsap.min.js"></script>
</head>
<body>
<div id="root" data-composition-id="{cid}" data-start="0" data-duration="{total}" data-fps="24" data-width="1080" data-height="1920">
<div id="bg" class="clip" data-start="0" data-duration="{total}" data-track-index="0"><div class="glow"></div></div>
{chr(10).join(blocks)}
<div id="chrome" class="clip" data-start="0" data-duration="{total}" data-track-index="{track + 1}">
<div id="brand-top">保 險 冷 知 識</div>
<div id="brand-bottom">一般知識分享，非個別投保或稅務建議・AI 生成影像</div>
</div>
{audio}
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(js)}
window.__timelines["{cid}"] = tl;
</script>
</body>
</html>
"""
    pdir = ROOT / eid
    (pdir / "index.html").write_text(page)
    (pdir / "meta.json").write_text(
        json.dumps({"id": eid, "name": ep["title"]}, ensure_ascii=False) + "\n"
    )
    shutil.copy(
        REPO / "hyperframes_trial/coldchain-03/hyperframes.json",
        pdir / "hyperframes.json",
    )
    for d in ("shared", "vendor"):
        if (pdir / d).exists():
            shutil.rmtree(pdir / d)
    shutil.copytree(ROOT / "shared", pdir / "shared")
    shutil.copytree(REPO / "hyperframes_trial/vendor", pdir / "vendor")
    print(f"  {eid}：{len(lines)} 句、{total:.1f} 秒")
    return pdir


def main():
    eid = [a for a in sys.argv[1:] if not a.startswith("--")][0]
    if subprocess.run([sys.executable, str(ROOT / "verify.py"), eid]).returncode != 0:
        raise SystemExit(f"⛔ {eid} 事實查核沒過，不產片")
    missing = [
        i
        for i in range(1, len(SCRIPTS["episodes"][eid]["lines"]) + 1)
        if not (
            ROOT
            / eid
            / (
                "lipsync_two"
                if SCRIPTS["episodes"][eid].get("shot") == "two"
                else "lipsync"
            )
            / f"l{i}.mp4"
        ).exists()
    ]
    if missing:
        raise SystemExit(f"⛔ 還缺對嘴片段：{missing}")
    pdir = build(eid)
    if "--render" in sys.argv:
        subprocess.run(["npx", "--yes", HF, "check"], cwd=pdir, check=True)
        hf_render(pdir)


if __name__ == "__main__":
    main()
