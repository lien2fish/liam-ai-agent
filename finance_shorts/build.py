"""從 scripts.json＋配音長度產生 HyperFrames 專案（index.html），可選擇直接 check／render。

時間軸由配音長度決定：每句從上一句結束＋GAP 開始，畫面跟著句子切換。
開場兩句對話共用一個場景（狗貓＋對話框），其餘每句一張卡。

用法：
  python3 finance_shorts/build.py ins-01            # 只產 index.html
  python3 finance_shorts/build.py ins-01 --render   # verify → check → render
"""

import html
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parent
SCRIPTS = json.loads((ROOT / "scripts.json").read_text())
sys.path.insert(0, str(REPO / "tools"))
from hf_render import HF, render as hf_render

LEAD = 0.25  # 片頭第一句前的空白
GAP = 0.35  # 句與句之間
TAIL = 1.6  # 最後一句講完後停留
WHO = {"cat": "貓", "dog": "狗"}


def esc(s):
    return html.escape(s).replace("\n", "<br>")


def fit(text, width=880, cap=92):
    """大字一行塞得下就不折行：依最長那行的字數縮字級。"""
    return min(cap, width // max(len(t) for t in text.split("\n")))


def timeline(eid):
    dur = json.loads((ROOT / eid / "audio/durations.json").read_text())
    gap = SCRIPTS["episodes"][eid].get("gap", GAP)
    t, out = LEAD, []
    for i, line in enumerate(SCRIPTS["episodes"][eid]["lines"], 1):
        d = dur[f"l{i}"]["dur"]
        out.append({**line, "i": i, "start": round(t, 3), "dur": d})
        t += d + gap
    total = round(t - gap + TAIL, 2)
    return out, total


def scene_bounds(lines, total, gap=GAP):
    """每句畫面從自己開始，到下一句開始為止；最後一句到片尾。"""
    for k, ln in enumerate(lines):
        ln["s0"] = 0 if k == 0 else round(ln["start"] - gap / 2, 3)
        ln["s1"] = (
            total if k == len(lines) - 1 else round(lines[k + 1]["start"] - gap / 2, 3)
        )


def fade_in(sel, at, y=28, d=0.5):
    return f'tl.fromTo("{sel}", {{ autoAlpha: 0, y: {y} }}, {{ autoAlpha: 1, y: 0, duration: {d}, ease: "power2.out" }}, {at:.3f});'


def fade_out(sel, at, end):
    return [
        f'tl.to("{sel}", {{ opacity: 0, duration: 0.25, ease: "power1.in" }}, {max(at, end - 0.28):.3f});',
        f'tl.set("{sel}", {{ opacity: 0 }}, {end:.3f});',
    ]


def dialog_scene(ep, lines, track):
    """開場：標題＋狗貓＋輪流的對話框，自成一層跨兩句。"""
    s0, s1 = 0, lines[-1]["s1"]
    title = "".join(
        f'<span class="line hook">{esc(t)}</span>' for t in ep["title"].split("，")
    )
    parts = [
        f'<div id="dlg" class="clip" data-start="{s0}" data-duration="{s1 - s0:.3f}" data-track-index="{track}"><div class="sin" id="dlg-in">',
        f'<div class="stack" id="hook" style="top: 350px">{title}</div>',
        '<img class="char" id="dog" src="shared/chars/dog_cut.png" style="left: 30px; top: 1010px; height: 640px" alt="" />',
        '<img class="char" id="cat" src="shared/chars/cat_cut.png" style="left: 640px; top: 1010px; height: 640px" alt="" />',
    ]
    js = [
        f'tl.fromTo("#hook", {{ scale: 1 }}, {{ scale: 1.03, duration: {s1:.3f}, ease: "none" }}, 0);',
        'tl.fromTo("#dog", { autoAlpha: 0, x: -80 }, { autoAlpha: 1, x: 0, duration: 0.5, ease: "power3.out" }, 0.05);',
        'tl.fromTo("#cat", { autoAlpha: 0, x: 80 }, { autoAlpha: 1, x: 0, duration: 0.5, ease: "power3.out" }, 0.12);',
    ]
    for ln in lines:
        side = "left" if ln["speaker"] == "dog" else "right"
        bid = f"b{ln['i']}"
        parts.append(
            f'<div class="bubble {side}" id="{bid}" style="top: 700px"><span class="who">{WHO[ln["speaker"]]}</span>{esc(ln["text"])}</div>'
        )
        js.append(
            f'tl.fromTo("#{bid}", {{ autoAlpha: 0, scale: 0.9 }}, {{ autoAlpha: 1, scale: 1, duration: 0.3, ease: "back.out(1.6)" }}, {ln["start"]:.3f});'
        )
        if ln is not lines[-1]:
            js.append(
                f'tl.to("#{bid}", {{ autoAlpha: 0, duration: 0.2 }}, {ln["start"] + ln["dur"] + 0.05:.3f});'
            )
        who = "#dog" if ln["speaker"] == "dog" else "#cat"
        bounces = max(1, int(ln["dur"] / 0.5))
        js.append(
            f'tl.fromTo("{who}", {{ y: 0 }}, {{ y: -18, duration: 0.25, ease: "sine.inOut", yoyo: true, repeat: {bounces * 2 - 1} }}, {ln["start"]:.3f});'
        )
    parts.append("</div></div>")
    js += fade_out("#dlg-in", s1 - 0.3, s1)
    return "\n".join(parts), js


def card_scene(ln, track):
    sc, i = ln["screen"], ln["i"]
    s0, s1 = ln["s0"], ln["s1"]
    sid = f"s{i}"
    body, js = [], []
    t0 = ln["start"]
    kind = sc["kind"]
    warn = " warn" if sc.get("warn") else ""

    if kind == "rule":
        body += [
            f'<div class="panel{warn}" id="{sid}-p" style="top: 560px; height: 600px"></div>',
            f'<div class="tag{warn}" id="{sid}-h" style="top: 620px">{esc(sc["head"])}</div>',
            f'<div class="stack" id="{sid}-b" style="top: 760px"><span class="line big{" warn" if sc.get("warn") else " gold"}" style="font-size: {fit(sc["body"])}px">{esc(sc["body"])}</span></div>',
        ]
        js += [
            fade_in(f"#{sid}-p", t0 - 0.1, 0, 0.4),
            fade_in(f"#{sid}-h", t0),
            fade_in(f"#{sid}-b", t0 + 0.35),
        ]
        if sc.get("cite"):
            body.append(
                f'<div class="cite" id="{sid}-c" style="top: 1060px">{esc(sc["cite"])}</div>'
            )
            js.append(fade_in(f"#{sid}-c", t0 + 0.9, 12))

    elif kind == "tiles":
        n = len(sc["items"])
        step = max(0.35, (ln["dur"] - 0.6) / n)
        for k, item in enumerate(sc["items"]):
            x = 90 + (k % 2) * 470
            y = 520 + (k // 2) * 190
            last = k == n - 1
            body.append(
                f'<div class="tile" id="{sid}-t{k}" style="left: {x}px; top: {y}px{"; color: var(--warn)" if last else ""}">{esc(item)}</div>'
            )
            js.append(
                f'tl.fromTo("#{sid}-t{k}", {{ autoAlpha: 0, scale: 0.85 }}, {{ autoAlpha: 1, scale: 1, duration: 0.3, ease: "back.out(1.7)" }}, {t0 + k * step:.3f});'
            )

    elif kind == "stat":
        body += [
            f'<div class="tag" id="{sid}-h" style="top: 520px">{esc(sc["head"])}</div>',
            f'<div class="stack" id="{sid}-big" style="top: 620px"><span class="line gold" style="font-size: 190px; font-weight: 800">{esc(sc["big"])}</span></div>',
            f'<div class="barrow" id="{sid}-bar" style="top: 900px"><div class="track"><div class="fill" id="{sid}-fill" style="right: {100 - sc["pct"]:.2f}%; background: var(--gold)"></div></div></div>',
            f'<div class="stack" id="{sid}-b" style="top: 1080px"><span class="line mid">{esc(sc["body"])}</span></div>',
            f'<div class="cite" id="{sid}-c" style="top: 1190px">{esc(sc["cite"])}</div>',
        ]
        js += [
            fade_in(f"#{sid}-h", t0),
            fade_in(f"#{sid}-big", t0 + 0.4),
            fade_in(f"#{sid}-bar", t0 + 0.4, 0, 0.3),
            f'tl.fromTo("#{sid}-fill", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 1.2, ease: "power2.out" }}, {t0 + 0.6:.3f});',
            fade_in(f"#{sid}-b", t0 + 1.6),
            fade_in(f"#{sid}-c", t0 + 2.2, 12),
        ]

    elif kind == "days":
        colors = ["var(--dim)", "var(--warn)", "var(--ok)"]
        step = max(0.5, (ln["dur"] - 1.2) / len(sc["bars"]))
        for k, b in enumerate(sc["bars"]):
            pct = b["days"] / 37 * 100
            note = (
                f'　<span style="color: var(--ok)">{esc(b["note"])}</span>'
                if b.get("note")
                else ""
            )
            body.append(
                f'<div class="barrow" id="{sid}-r{k}" style="top: {560 + k * 220}px"><div class="lbl">{esc(b["label"])}</div>'
                f'<div class="val">{b["days"]} 天{note}</div><div class="track"><div class="fill" id="{sid}-f{k}" style="right: {100 - pct:.2f}%; background: {colors[k]}"></div></div></div>'
            )
            at = t0 + k * step
            js += [
                fade_in(f"#{sid}-r{k}", at, 16, 0.35),
                f'tl.fromTo("#{sid}-f{k}", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.8, ease: "power2.out" }}, {at + 0.15:.3f});',
            ]

    elif kind == "end":
        body += [
            f'<div class="stack" id="{sid}-a" style="top: 520px"><span class="line mid dim">{esc(sc["a"])}</span></div>',
            f'<div class="stack" id="{sid}-b" style="top: 640px"><span class="line big gold" style="font-size: {fit(sc["b"])}px">{esc(sc["b"])}</span></div>',
            f'<div class="cite" id="{sid}-c" style="top: 900px">{esc(ln["caption"])}</div>',
            '<img class="char" id="end-dog" src="shared/chars/dog_cut.png" style="left: 150px; top: 1040px; height: 380px" alt="" />',
            '<img class="char" id="end-cat" src="shared/chars/cat_cut.png" style="left: 660px; top: 1040px; height: 380px" alt="" />',
        ]
        js += [
            fade_in(f"#{sid}-a", t0),
            f'tl.fromTo("#{sid}-b", {{ autoAlpha: 0, y: 30, scale: 0.92 }}, {{ autoAlpha: 1, y: 0, scale: 1, duration: 0.6, ease: "back.out(1.6)" }}, {t0 + 0.6:.3f});',
            fade_in(f"#{sid}-c", t0 + 1.4, 12),
            fade_in("#end-dog", t0 + 0.3, 40),
            fade_in("#end-cat", t0 + 0.45, 40),
        ]

    if kind != "end":
        body.append(
            f'<div class="sub" id="{sid}-sub">{esc(ln["text"].rstrip("。"))}</div>'
        )
        js.append(
            f'tl.fromTo("#{sid}-sub", {{ autoAlpha: 0 }}, {{ autoAlpha: 1, duration: 0.2 }}, {t0:.3f});'
        )

    html_ = (
        f'<section id="{sid}" class="clip" data-start="{s0:.3f}" data-duration="{s1 - s0:.3f}" data-track-index="{track}">'
        f'<div class="sin" id="{sid}-in">\n' + "\n".join(body) + "\n</div></section>"
    )
    if kind != "end":
        js += fade_out(f"#{sid}-in", s1 - 0.3, s1)
    return html_, js


def build(eid):
    ep = SCRIPTS["episodes"][eid]
    lines, total = timeline(eid)
    scene_bounds(lines, total, SCRIPTS["episodes"][eid].get("gap", GAP))
    dialog = [l for l in lines if l["speaker"] in WHO]
    cards = [l for l in lines if l["speaker"] == "narr"]
    if dialog:
        dialog[-1]["s1"] = cards[0]["s0"]

    blocks, js = [], []
    h, j = dialog_scene(ep, dialog, 1)
    blocks.append(h)
    js += j
    for k, ln in enumerate(cards):
        ln["caption"] = ep["caption"]
        h, j = card_scene(ln, 2 + k)
        blocks.append(h)
        js += j

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
<div id="chrome" class="clip" data-start="0" data-duration="{total}" data-track-index="20">
<div id="brand-top">保 險 冷 知 識</div>
<div id="brand-bottom">一般知識分享，非個別投保或稅務建議</div>
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
    (pdir / "package.json").write_text(
        json.dumps(
            {
                "name": eid,
                "private": True,
                "type": "module",
                "scripts": {
                    "check": f"npx --yes {HF} check",
                    "render": f"npx --yes {HF} render",
                },
            },
            indent=2,
        )
        + "\n"
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
    print(f"  {eid}：{len(lines)} 句、{total:.1f} 秒 → {pdir / 'index.html'}")
    return pdir


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    render = "--render" in sys.argv
    for eid in args or list(SCRIPTS["episodes"]):
        if (
            subprocess.run([sys.executable, str(ROOT / "verify.py"), eid]).returncode
            != 0
        ):
            raise SystemExit(f"⛔ {eid} 事實查核沒過，不產片")
        pdir = build(eid)
        if render:
            subprocess.run(["npx", "--yes", HF, "check"], cwd=pdir, check=True)
            hf_render(pdir)


if __name__ == "__main__":
    main()
