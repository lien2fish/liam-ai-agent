"""podcast 16:9 橫式版：錄音室合照滿版，說話者的對嘴近景貼回合照原位。

每句都用近景生成（lipsync.py --close），貼回 studio_wide_hd.png 上的原位、邊緣淡化，
所以只有說話的那隻會動、另一隻保證閉嘴。缺對嘴片段時用 --preview 先看版面。

用法：python3 finance_shorts/podcast_wide.py ins-03L [--preview] [--render]
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

W, H = 1920, 1080
BG = "shared/chars/studio_wide_hd.png"  # studio_wide 的 (0,140)-(1536,1004) 放大到 1920×1080
K, Y0 = W / 1536, 140
CLOSE_BOX = {
    "cat": (0, 250, 900, 506),
    "dog": (640, 220, 896, 504),
}  # 近景在 studio_wide 上的 x, y, w, h
FEATHER = {
    "cat": "linear-gradient(to right, #000 0%, #000 80%, transparent 100%)",
    "dog": "linear-gradient(to left, #000 0%, #000 80%, transparent 100%)",
}

CSS = """
.wsub { position: absolute; left: 50%; bottom: 56px; width: max-content; max-width: 1560px; transform: translateX(-50%);
  padding: 12px 34px; border-radius: 22px; background: rgba(7, 13, 26, 0.72);
  color: var(--ink); font-size: 50px; line-height: 1.35; text-align: center; text-wrap: balance; }
.wtitle { position: absolute; left: 50%; transform: translateX(-50%); top: 34px; padding: 10px 36px;
  border-radius: 999px; background: rgba(7, 13, 26, 0.72); color: var(--ink); font-size: 46px; font-weight: 800; white-space: nowrap; }
.wbrand { position: absolute; left: 44px; top: 44px; font-size: 30px; color: var(--gold); letter-spacing: 0.2em; }
.wnote { position: absolute; right: 44px; top: 50px; font-size: 22px; color: rgba(243, 241, 234, 0.8); }
.wcard { position: absolute; left: 660px; width: 600px; top: 150px; height: 250px; border-radius: 28px;
  background: rgba(7, 13, 26, 0.80); border: 3px solid var(--panel-line); }
.wcard.warn { border-color: rgba(224, 122, 95, 0.75); }
"""


def overlay_style(who, box=None):
    x, y, w, h = (box or CLOSE_BOX)[who]
    mask = f"{FEATHER[who]}, linear-gradient(to bottom, transparent 0%, #000 12%, #000 88%, transparent 100%)"
    return (
        f"position: absolute; left: {x * K:.1f}px; top: {(y - Y0) * K:.1f}px; width: {w * K:.1f}px; height: {h * K:.1f}px; object-fit: fill; "
        f"-webkit-mask-image: {mask}; -webkit-mask-composite: source-in; mask-image: {mask}; mask-composite: intersect"
    )


def build(eid, preview):
    ep = SCRIPTS["episodes"][eid]
    studio = ep.get("studio", "studio")
    cx, cw, cy = (
        ep.get("card", []) + [660, 600, 150][len(ep.get("card", [])) :]
    )  # 重點卡的 left、width：放在兩隻中間的空位，換角色時要重看會不會擋臉
    lines, total = timeline(eid)
    scene_bounds(lines, total, ep.get("gap", GAP))
    last_end = round(lines[-1]["start"] + lines[-1]["dur"] + 0.2, 3)
    lines[-1]["s1"] = last_end

    blocks = [
        f'<img id="studio" src="shared/chars/{studio}_wide_hd.png" style="position: absolute; inset: 0; width: {W}px; height: {H}px" alt="" />'
    ]
    js, track = [], 2
    for ln in lines:
        i, s0, s1 = ln["i"], ln["s0"], ln["s1"]
        if not preview:
            blocks.append(
                f'<video class="clip" id="v{i}" src="lipsync_close/l{i}.mp4" muted data-volume="0" style="{overlay_style(ln["speaker"], ep.get("close_box"))}" '
                f'data-start="{ln["start"]:.3f}" data-duration="{ln["dur"]:.3f}" data-track-index="{track}"></video>'
            )
        sid = f"s{i}"
        body = [
            f'<div class="wsub" id="{sid}-sub">{esc(ln["text"].rstrip("。"))}</div>'
        ]
        js.append(
            f'tl.fromTo("#{sid}-sub", {{ autoAlpha: 0 }}, {{ autoAlpha: 1, duration: 0.12 }}, {ln["start"]:.3f});'
        )
        sc = ln.get("screen")
        if sc:
            warn = " warn" if sc.get("warn") else ""
            color = "warn" if sc.get("warn") else "gold"
            body += [
                f'<div class="wcard{warn}" id="{sid}-p" style="left: {cx}px; width: {cw}px; top: {cy}px"></div>',
                f'<div class="tag{warn}" id="{sid}-h" style="left: {cx}px; right: auto; width: {cw}px; top: {cy + 22}px; font-size: 32px">{esc(sc["head"])}</div>',
                f'<div class="stack" id="{sid}-b" style="left: {cx + 20}px; right: auto; width: {cw - 40}px; top: {cy + 76}px"><span class="line {color}" style="font-size: {fit(sc["body"], cw - 60, 56)}px; font-weight: 800">{esc(sc["body"])}</span></div>',
            ]
            js += [
                fade_in(f"#{sid}-p", ln["start"] + 0.15, 0, 0.3),
                fade_in(f"#{sid}-h", ln["start"] + 0.25, 12, 0.35),
                fade_in(f"#{sid}-b", ln["start"] + 0.4, 16, 0.35),
            ]
            if sc.get("cite"):
                body.append(
                    f'<div class="cite" id="{sid}-c" style="left: {cx}px; right: auto; width: {cw}px; top: {cy + 202}px; font-size: 26px">{esc(sc["cite"])}</div>'
                )
                js.append(fade_in(f"#{sid}-c", ln["start"] + 0.7, 8, 0.35))
        blocks.append(
            f'<section id="{sid}" class="clip" data-start="{s0:.3f}" data-duration="{s1 - s0:.3f}" data-track-index="{track + 1}">'
            f'<div class="sin" id="{sid}-in">' + "".join(body) + "</div></section>"
        )
        js += fade_out(f"#{sid}-in", s1 - 0.3, s1)
        track += 2

    blocks.append(
        f'<section id="end" class="clip" data-start="{last_end:.3f}" data-duration="{total - last_end:.3f}" data-track-index="{track}"><div class="sin">'
        f'<div class="wsub" id="end-c" style="font-size: 40px">{esc(ep["caption"])}</div></div></section>'
    )
    js.append(fade_in("#end-c", last_end + 0.1, 10, 0.4))

    audio = "\n".join(
        f'<audio id="vo-{l["i"]}" data-start="{l["start"]:.3f}" data-duration="{l["dur"]:.3f}" src="audio/l{l["i"]}.mp3"></audio>'
        for l in lines
    )
    cid = eid.replace("-", "")
    title = esc(ep["title"])
    page = f"""<!doctype html>
<html lang="zh-Hant" data-resolution="landscape">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<title>{title}</title>
<link rel="stylesheet" href="shared/brand.css" />
<style>html, body, #root {{ width: {W}px; height: {H}px; }} {CSS}</style>
<script src="vendor/gsap.min.js"></script>
</head>
<body>
<div id="root" data-composition-id="{cid}" data-start="0" data-duration="{total}" data-fps="24" data-width="{W}" data-height="{H}">
<div id="bg" class="clip" data-start="0" data-duration="{total}" data-track-index="0">{blocks[0]}</div>
{chr(10).join(blocks[1:])}
<div id="chrome" class="clip" data-start="0" data-duration="{total}" data-track-index="{track + 1}">
<div class="wbrand">保險冷知識</div>
<div class="wtitle">{title}</div>
<div class="wnote">一般知識分享，非個別投保或稅務建議・AI 生成影像</div>
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
    print(
        f"  {eid}：{len(lines)} 句、{total:.1f} 秒（{'版面預覽，無對嘴' if preview else '完整'}）"
    )
    return pdir


def speed_up(pdir, ep):
    """畫面與聲音一起等比例加速，對嘴不會跑掉（10-16 Lien 選定 1.3 倍，每秒約 5.7 字）。"""
    r = ep.get("speed", 1.0)
    src = sorted((pdir / "renders").glob(f"{pdir.name}_*.mp4"))[-1]
    if r == 1.0:
        return src
    out = pdir / "renders" / f"final_{r:.2f}x.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(src),
            "-filter_complex",
            f"[0:v]setpts=PTS/{r}[v];[0:a]atempo={r}[a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-r",
            "24",
            "-c:v",
            "libx264",
            "-threads",
            "4",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(out),
        ],
        check=True,
    )
    print(f"  ⏩ {r} 倍速成品 → {out}")
    return out


def main():
    eid = [a for a in sys.argv[1:] if not a.startswith("--")][0]
    preview = "--preview" in sys.argv
    if subprocess.run([sys.executable, str(ROOT / "verify.py"), eid]).returncode != 0:
        raise SystemExit(f"⛔ {eid} 事實查核沒過，不產片")
    n = len(SCRIPTS["episodes"][eid]["lines"])
    missing = [
        i
        for i in range(1, n + 1)
        if not (ROOT / eid / f"lipsync_close/l{i}.mp4").exists()
    ]
    if missing and not preview:
        raise SystemExit(f"⛔ 還缺對嘴片段：{missing}（可先用 --preview 看版面）")
    pdir = build(eid, preview)
    if "--render" in sys.argv:
        subprocess.run(["npx", "--yes", HF, "check"], cwd=pdir, check=True)
        hf_render(pdir)
        speed_up(pdir, SCRIPTS["episodes"][eid])


if __name__ == "__main__":
    main()
