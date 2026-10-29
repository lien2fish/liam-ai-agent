"""全球金錢頻道：PPT 風格 16:9 投影片影片（只有旁白，沒有角色）。

每句台詞一頁：頁面從右推入、元素依序飛入、長條長出來、利率數字配上升箭頭彈出，
底部有頁碼與進度條。版面種類：title／rate／stat／bars／calendar／end。

用法：python3 finance_shorts/slides.py mw-01-zh [--render]
"""

import math
import json
import pathlib
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
    fade_out,
    fit,
    scene_bounds,
    timeline,
)

W, H = 1920, 1080
BRAND = {"zh": "金錢怪物", "en": "Money Around the World"}
NOTE = {
    "zh": "資訊整理，非投資建議",
    "en": "For information only, not financial advice",
}

CSS = """
html, body, #root { width: 1920px; height: 1080px; }
#bg { background: radial-gradient(120% 90% at 20% 0%, #16294a 0%, #0b1426 55%, #070d1a 100%); }
#grid { position: absolute; inset: 0; opacity: 0.08;
  background-image: linear-gradient(#9fb3d1 1px, transparent 1px), linear-gradient(90deg, #9fb3d1 1px, transparent 1px);
  background-size: 96px 96px; }
.brand { position: absolute; left: 64px; top: 48px; font-size: 30px; color: var(--gold); letter-spacing: 0.12em; text-shadow: 0 2px 8px rgba(0,0,0,0.95); }
.disc { position: absolute; right: 64px; top: 52px; font-size: 22px; color: rgba(243,241,234,0.88); text-shadow: 0 1px 4px rgba(0,0,0,0.9); }
.pg { position: absolute; right: 64px; bottom: 34px; font-size: 24px; color: var(--dim); }
.prog { position: absolute; left: 0; bottom: 0; height: 8px; width: 1920px; background: var(--gold); transform-origin: left center; }
.sub2 { position: absolute; left: 50%; bottom: 74px; transform: translateX(-50%); width: max-content; max-width: 1560px;
  padding: 10px 30px; border-radius: 18px; background: rgba(7, 13, 26, 0.75); color: var(--ink);
  font-size: 42px; line-height: 1.35; text-align: center; text-wrap: balance; }
.h1 { position: absolute; left: 0; right: 0; text-align: center; color: var(--ink); font-weight: 800; }
.chip { position: absolute; padding: 8px 26px; border-radius: 999px; border: 3px solid var(--gold); color: var(--gold); font-size: 40px; }
.bank { position: absolute; left: 160px; top: 300px; font-size: 76px; font-weight: 800; color: var(--ink); }
.rate { position: absolute; left: 960px; top: 330px; font-size: 190px; font-weight: 800; color: var(--gold); white-space: nowrap; }
.rnote { position: absolute; left: 160px; top: 640px; font-size: 48px; color: var(--ink); }
.arrow { position: absolute; color: var(--warn); }
.card { position: absolute; border-radius: 30px; background: rgba(255,255,255,0.06); border: 3px solid var(--panel-line); }
.bl { position: absolute; left: 220px; font-size: 46px; color: var(--ink); }
.btrack { position: absolute; left: 480px; width: 1000px; height: 64px; border-radius: 32px; background: rgba(255,255,255,0.06); }
.bfill { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 32px; transform-origin: left center; }
.bv { position: absolute; font-size: 42px; color: var(--ink); }
.bgw { position: absolute; inset: 0; overflow: hidden; }
.vclip { position: absolute; inset: 0; width: 1920px; height: 1080px; object-fit: cover; }
.vshade { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(0,0,0,0.78) 0%, rgba(0,0,0,0) 22%, rgba(0,0,0,0) 60%, rgba(0,0,0,0.85) 100%); }
.callout { position: absolute; left: 96px; bottom: 210px; padding: 18px 34px 22px; border-radius: 18px;
  background: rgba(7,13,26,0.82); border-left: 10px solid var(--gold); max-width: 900px; }
.ctag, .cbig, .cnote { display: block; position: relative; }
.ctag { font-size: 34px; line-height: 1.4; color: var(--gold); font-weight: 700; }
.cbig { font-size: 120px; line-height: 1.25; margin: 4px 0; font-weight: 800; color: #ffd400; }
.cnote { font-size: 30px; line-height: 1.4; color: var(--ink); margin-top: 6px; }
.bgw img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; transform-origin: 60% 40%; }
.shade { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(5,10,20,0.66) 0%, rgba(5,10,20,0.60) 45%, rgba(5,10,20,0.86) 100%); }
.sin .h1, .sin .bank, .sin .rate, .sin .rnote, .sin .bl, .sin .bv { text-shadow: 0 4px 18px rgba(0,0,0,0.85), 0 1px 3px rgba(0,0,0,0.9); }
.card { background: rgba(7,13,26,0.70) !important; }
.btrack { background: rgba(7,13,26,0.65) !important; }
"""


def fit(text, width, cap):
    """字級：英數字約半個中文字寬，否則英文標題會被縮得太小。"""
    longest = max(sum(0.55 if c.isascii() else 1 for c in t) for t in text.split("\n"))
    return min(cap, int(width / max(longest, 1)))


# 維持不動用橫向箭頭：上升箭頭會讓觀眾以為也升息了（10-19 台灣央行那頁差點這樣發出去）
FLAT = (
    '<svg viewBox="0 0 100 100" width="100%" height="100%"><g fill="none" stroke="currentColor" stroke-width="12" '
    'stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="50" x2="86" y2="50"/><polyline points="58,22 88,50 58,78"/></g></svg>'
)
BELL = (
    '<svg viewBox="0 0 100 100" width="100%" height="100%"><g fill="none" stroke="currentColor" stroke-width="8" stroke-linejoin="round">'
    '<path d="M50 14 C30 14 26 32 26 46 L26 64 L16 76 L84 76 L74 64 L74 46 C74 32 70 14 50 14 Z"/><path d="M40 84 C42 92 58 92 60 84"/></g></svg>'
)
ARROW = (
    '<svg viewBox="0 0 100 100" width="100%" height="100%"><g fill="none" stroke="currentColor" stroke-width="12" '
    'stroke-linecap="round" stroke-linejoin="round"><line x1="50" y1="88" x2="50" y2="14"/><polyline points="18,44 50,12 82,44"/></g></svg>'
)


def enter(sel, at, dx=0, dy=40, d=0.45, ease="power3.out"):
    return f'tl.fromTo("{sel}", {{ autoAlpha: 0, x: {dx}, y: {dy} }}, {{ autoAlpha: 1, x: 0, y: 0, duration: {d}, ease: "{ease}" }}, {at:.3f});'


def slide(ln, n, total_pages, lang):
    sc, i, t0 = ln["screen"], ln["i"], ln["start"]
    sid = f"p{i}"
    b, js = [], []
    k = sc["kind"]
    if k == "title":
        b += [
            f'<div class="h1" id="{sid}-h" style="top: 360px; font-size: {fit(sc["head"], 1600, 120)}px">{esc(sc["head"])}</div>',
            f'<div class="h1" id="{sid}-s" style="top: 560px; font-size: 46px; font-weight: 600; color: var(--gold)">{esc(sc["sub"])}</div>',
        ]
        if sc.get("arrow", True):
            b.append(
                f'<div class="arrow" id="{sid}-a" style="left: 1580px; top: 180px; width: 150px; height: 150px">{ARROW}</div>'
            )
        js += [
            f'tl.fromTo("#{sid}-h", {{ autoAlpha: 0, scale: 0.85 }}, {{ autoAlpha: 1, scale: 1, duration: 0.6, ease: "back.out(1.6)" }}, {t0:.3f});',
            enter(f"#{sid}-s", t0 + 0.6),
        ]
        if sc.get("arrow", True):
            js.append(enter(f"#{sid}-a", t0 + 0.9, 0, 80, 0.5, "back.out(2)"))
    elif k == "rate":
        b += [
            f'<div class="bank" id="{sid}-b" style="font-size: {fit(sc["bank"], 640, 76)}px">{esc(sc["bank"])}</div>',
            f'<div class="chip" id="{sid}-d" style="left: 160px; top: 430px">{esc(sc["date"])}</div>',
            f'<div class="rate" id="{sid}-r" style="font-size: {min(190, int(880 / max(1, len(sc["rate"]) * 0.58)))}px{"; color: var(--ink)" if sc.get("held") else ""}">{esc(sc["rate"])}</div>',
            f'<div class="arrow" id="{sid}-a" style="left: 860px; top: 380px; width: 110px; height: 110px{"; color: var(--dim)" if sc.get("held") else ""}">{FLAT if sc.get("held") else ARROW}</div>',
            f'<div class="rnote" id="{sid}-n">{esc(sc["note"])}</div>',
        ]
        js += [
            enter(f"#{sid}-b", t0, -80, 0),
            enter(f"#{sid}-d", t0 + 0.3, -60, 0),
            f'tl.fromTo("#{sid}-r", {{ autoAlpha: 0, scale: 0.6 }}, {{ autoAlpha: 1, scale: 1, duration: 0.6, ease: "back.out(1.8)" }}, {t0 + 0.7:.3f});',
            enter(f"#{sid}-a", t0 + 1.1, 0, 70, 0.5, "back.out(2)"),
            enter(f"#{sid}-n", t0 + 1.6),
        ]
    elif k == "stat":
        b += [
            f'<div class="h1" id="{sid}-h" style="top: 170px; font-size: 54px; line-height: 1.2; color: var(--gold)">{esc(sc["head"])}</div>',
            f'<div class="h1" id="{sid}-big" style="top: 300px; font-size: 220px; line-height: 1.3; color: var(--warn)">{esc(sc["big"])}</div>',
            f'<div class="h1" id="{sid}-n" style="top: 640px; font-size: 48px; line-height: 1.2; font-weight: 600">{esc(sc["note"])}</div>',
        ]
        js += [
            enter(f"#{sid}-h", t0),
            f'tl.fromTo("#{sid}-big", {{ autoAlpha: 0, scale: 0.5 }}, {{ autoAlpha: 1, scale: 1, duration: 0.7, ease: "back.out(1.8)" }}, {t0 + 0.4:.3f});',
            enter(f"#{sid}-n", t0 + 1.3),
        ]
    elif k == "bars":
        vmax = max(float(x["v"]) for x in sc["bars"])
        colors = ["var(--warn)", "var(--gold)", "var(--ok)", "#7abee2"]
        step = max(0.35, (ln["dur"] - 1.0) / len(sc["bars"]))
        b.append(
            f'<div class="h1" id="{sid}-h" style="top: 170px; font-size: 54px; color: var(--gold)">{esc(sc["head"])}</div>'
        )
        js.append(enter(f"#{sid}-h", t0))
        for j, x in enumerate(sc["bars"]):
            y = 300 + j * 140
            pct = float(x["v"]) / vmax * 100
            b += [
                f'<div class="bl" id="{sid}-l{j}" style="top: {y + 4}px">{esc(x["label"])}</div>',
                f'<div class="btrack" id="{sid}-t{j}" style="top: {y}px"><div class="bfill" id="{sid}-f{j}" style="right: {100 - pct:.2f}%; background: {colors[j % 4]}"></div></div>',
                f'<div class="bv" id="{sid}-v{j}" style="top: {y + 6}px; left: {480 + 1000 * pct / 100 + 24:.0f}px">{esc(x["show"])}</div>',
            ]
            at = t0 + 0.4 + j * step
            js += [
                enter(f"#{sid}-l{j}", at, -40, 0, 0.3),
                enter(f"#{sid}-t{j}", at, 0, 0, 0.2),
                f'tl.fromTo("#{sid}-f{j}", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.7, ease: "power2.out" }}, {at + 0.1:.3f});',
                enter(f"#{sid}-v{j}", at + 0.6, 0, 0, 0.3),
            ]
    elif k == "calendar":
        b.append(
            f'<div class="h1" id="{sid}-h" style="top: 180px; font-size: 64px; color: var(--gold)">{esc(sc["head"])}</div>'
        )
        js.append(enter(f"#{sid}-h", t0))
        for j, x in enumerate(sc["items"]):
            left = 260 + j * 720
            b += [
                f'<div class="card" id="{sid}-c{j}" style="left: {left}px; top: 320px; width: 640px; height: 360px"></div>',
                f'<div class="h1" id="{sid}-cd{j}" style="left: {left}px; right: auto; width: 640px; top: 380px; font-size: 96px; color: var(--gold)">{esc(x["date"])}</div>',
                f'<div class="h1" id="{sid}-cw{j}" style="left: {left}px; right: auto; width: 640px; top: 540px; font-size: 50px; font-weight: 600">{esc(x["what"])}</div>',
            ]
            at = t0 + 0.5 + j * 1.2
            js += [
                enter(f"#{sid}-c{j}", at, 0, 60, 0.5, "back.out(1.4)"),
                enter(f"#{sid}-cd{j}", at + 0.2),
                enter(f"#{sid}-cw{j}", at + 0.4),
            ]
    elif k == "outro":
        # 片尾：大字＋頻道名＋會彈出的訂閱按鈕與鈴鐺
        b += [
            f'<div class="h1" id="{sid}-a" style="top: 250px; font-size: {fit(sc["a"], 1500, 130)}px">{esc(sc["a"])}</div>',
            f'<div class="h1" id="{sid}-b" style="top: 440px; font-size: 64px; color: var(--gold)">{esc(sc["b"])}</div>',
            f'<div id="{sid}-btn" style="position: absolute; left: 710px; top: 620px; width: 420px; height: 110px; border-radius: 22px; '
            f'background: #e53935; color: #fff; font-size: 48px; font-weight: 800; letter-spacing: 0.08em; display: flex; align-items: center; justify-content: center">{esc(sc["btn"])}</div>',
            f'<div id="{sid}-bell" style="position: absolute; left: 1160px; top: 630px; width: 90px; height: 90px; color: var(--gold)">{BELL}</div>',
        ]
        js += [
            f'tl.fromTo("#{sid}-a", {{ autoAlpha: 0, scale: 0.8 }}, {{ autoAlpha: 1, scale: 1, duration: 0.6, ease: "back.out(1.6)" }}, {t0:.3f});',
            enter(f"#{sid}-b", t0 + 0.5),
            f'tl.fromTo("#{sid}-btn", {{ autoAlpha: 0, scale: 0.4 }}, {{ autoAlpha: 1, scale: 1, duration: 0.5, ease: "back.out(2.2)" }}, {t0 + 1.0:.3f});',
            f'tl.fromTo("#{sid}-btn", {{ scale: 1 }}, {{ scale: 1.06, duration: 0.35, ease: "sine.inOut", yoyo: true, repeat: 3 }}, {t0 + 1.6:.3f});',
            f'tl.fromTo("#{sid}-bell", {{ autoAlpha: 0, rotation: 0 }}, {{ autoAlpha: 1, rotation: 0, duration: 0.3 }}, {t0 + 1.4:.3f});',
            f'tl.fromTo("#{sid}-bell", {{ rotation: -18 }}, {{ rotation: 18, duration: 0.12, ease: "sine.inOut", yoyo: true, repeat: 7 }}, {t0 + 1.7:.3f});',
        ]
    elif k == "broll":
        # 窮奢極欲式：實拍片段滿版，只在左下角放一個小數字框，不蓋住畫面
        if sc.get("big"):
            b += [
                f'<div class="callout" id="{sid}-co">'
                + (
                    f'<span class="ctag">{esc(sc["tag"])}</span>'
                    if sc.get("tag")
                    else ""
                )
                + f'<span class="cbig">{esc(sc["big"])}</span>'
                + (
                    f'<span class="cnote">{esc(sc["note"])}</span>'
                    if sc.get("note")
                    else ""
                )
                + "</div>"
            ]
            js.append(enter(f"#{sid}-co", t0 + 0.3, -40, 0, 0.45, "back.out(1.4)"))
    elif k == "end":
        b += [
            f'<div class="h1" id="{sid}-a" style="top: 320px; font-size: {fit(sc["a"], 1600, 80)}px">{esc(sc["a"])}</div>',
            f'<div class="h1" id="{sid}-b" style="top: 460px; font-size: {fit(sc["b"], 1600, 80)}px; color: var(--gold)">{esc(sc["b"])}</div>',
            f'<div class="h1" id="{sid}-c" style="top: 680px; font-size: 32px; font-weight: 500; color: var(--dim)">{esc(ln["caption"])}</div>',
        ]
        js += [
            enter(f"#{sid}-a", t0),
            enter(f"#{sid}-b", t0 + 0.5),
            enter(f"#{sid}-c", t0 + 1.0, 0, 20),
        ]

    if k != "end":
        b.append(
            f'<div class="sub2" id="{sid}-sub">{esc(ln.get("sub", ln["text"]))}</div>'
        )
        js.append(
            f'tl.fromTo("#{sid}-sub", {{ autoAlpha: 0 }}, {{ autoAlpha: 1, duration: 0.15 }}, {t0:.3f});'
        )
    b.append(f'<div class="pg">{n} / {total_pages}</div>')

    s0, s1 = ln["s0"], ln["s1"]
    # 推入式轉場：整頁從右邊滑進來
    js.insert(
        0,
        (
            f'tl.fromTo("#{sid}-in", {{ autoAlpha: 0 }}, {{ autoAlpha: 1, duration: 0.2 }}, {s0:.3f});'
            if k == "broll"
            else f'tl.fromTo("#{sid}-in", {{ x: 160, autoAlpha: 0 }}, {{ x: 0, autoAlpha: 1, duration: 0.45, ease: "power3.out" }}, {s0:.3f});'
        ),
    )
    if ln is not None and s1 < 1e9:
        js += fade_out(f"#{sid}-in", s1 - 0.3, s1)
    bg = ""
    if ln.get("bg"):
        # 實景照片滿版＋緩慢推近（窮奢極欲式）；照片出處記在 shared/bg/credits.json
        bg = f'<div class="bgw" id="{sid}-bgw"><img id="{sid}-bgi" src="shared/bg/{ln["bg"]}.jpg" alt="" /><div class="shade"></div></div>'
        js += [
            f'tl.fromTo("#{sid}-bgw", {{ autoAlpha: 0 }}, {{ autoAlpha: 1, duration: 0.5, ease: "none" }}, {s0:.3f});',
            f'tl.fromTo("#{sid}-bgi", {{ scale: 1.0 }}, {{ scale: 1.1, duration: {s1 - s0:.3f}, ease: "none" }}, {s0:.3f});',
        ]
        js += fade_out(f"#{sid}-bgw", s1 - 0.3, s1)
    if ln.get("clips") or ln.get("pool"):
        bg = '<div class="vshade"></div>'
    html_ = (
        f'<section id="{sid}" class="clip" data-start="{s0:.3f}" data-duration="{s1 - s0:.3f}" data-track-index="{n + 1}">'
        + bg
        + f'<div class="sin" id="{sid}-in">'
        + "".join(b)
        + "</div></section>"
    )
    return html_, js


def build(eid):
    ep = SCRIPTS["episodes"][eid]
    lang = ep.get(
        "ui", ep.get("lang", "zh")
    )  # 畫面文字語言；克隆英文旁白版用中文畫面＋中文字幕
    lines, total = timeline(eid)
    scene_bounds(lines, total, ep.get("gap", GAP))
    blocks, js = [], []
    for n, ln in enumerate(lines, 1):
        ln["caption"] = ep["caption"]
        h, j = slide(ln, n, len(lines), lang)
        blocks.append(h)
        js += j
    js.append(
        f'tl.fromTo(".prog", {{ scaleX: 0 }}, {{ scaleX: 1, duration: {total}, ease: "none" }}, 0);'
    )
    # 素材池：句子只寫 pool（如 jp_res）時，依句長自動配片段——約 4 秒一刀（1.2 倍速後）、整支不重複
    reject = set(ep.get("reject", []))
    pools = {}
    for ln in lines:
        name = ln.get("pool")
        if name and name not in pools:
            files = sorted(
                f"broll/{f.stem}"
                for f in (ROOT / "shared" / "broll").glob(f"{name}_*.mp4")
            )
            pools[name] = [
                c
                for c in ep.get("pool_extra", {}).get(name, []) + files
                if c not in reject
            ]
    cursor = {k: 0 for k in pools}
    for ln in lines:
        if ln.get("pool") and not ln.get("clips"):
            a, b_ = (0.0 if ln["i"] == 1 else ln["s0"]), ln["s1"]
            n = max(
                1, round((b_ - a) / ep.get("shot", 4.8))
            )  # shot：每刀秒數（渲染時間軸），es-01 起 3.0＝1.2 倍速後 2.5 秒
            n = max(
                n, math.ceil((b_ - a) / ep.get("clip_max", 7.9))
            )  # 每段素材最長能用幾秒（es-01 切成 4 秒半段）
            pool = pools[ln["pool"]]
            if cursor[ln["pool"]] + n > len(pool):
                print(f"  ⚠️ 素材池 {ln['pool']} 不夠用（{len(pool)} 段），開始重複")
            ln["clips"] = [pool[(cursor[ln["pool"]] + j) % len(pool)] for j in range(n)]
            cursor[ln["pool"]] += n
    # 實拍片段層（track 1）：每句的 clips 平均分配該句時間，一個接一個，約 4 秒一刀
    vids = []
    for ln in lines:
        clips = ln.get("clips") or []
        if not clips:
            continue
        a, b_ = (0.0 if ln["i"] == 1 else ln["s0"]), ln["s1"]
        step = (b_ - a) / len(clips)
        for j, c in enumerate(clips):
            cs, cid_ = a + j * step, f"c{ln['i']}_{j}"
            if c.startswith("bg/"):
                vids.append(
                    f'<img class="clip vclip" id="{cid_}" src="shared/{c}.jpg" data-start="{cs:.3f}" data-duration="{step:.3f}" data-track-index="1" alt="" />'
                )
                js.append(
                    f'tl.fromTo("#{cid_}", {{ scale: 1.0 }}, {{ scale: 1.08, duration: {step:.3f}, ease: "none" }}, {cs:.3f});'
                )
            else:
                src = ROOT / "shared" / f"{c}.mp4"
                have = float(
                    subprocess.run(
                        [
                            "ffprobe",
                            "-v",
                            "error",
                            "-show_entries",
                            "format=duration",
                            "-of",
                            "csv=p=0",
                            str(src),
                        ],
                        capture_output=True,
                        text=True,
                    ).stdout
                )
                if have + 0.05 < step:
                    raise SystemExit(
                        f"⛔ {c} 只有 {have:.1f} 秒，第 {ln['i']} 句要 {step:.1f} 秒，片段要剪長一點或多給一段"
                    )
                vids.append(
                    f'<video class="clip vclip" id="{cid_}" src="shared/{c}.mp4" muted data-volume="0" data-start="{cs:.3f}" data-duration="{step:.3f}" data-track-index="1"></video>'
                )
    bgm = ""
    if ep.get("bgm"):
        # 背景音樂墊底：窮奢極欲全片都有，音量約低人聲 20dB（10-21 實測）
        # 曲子比影片短就循環接上
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-stream_loop",
                "-1",
                "-i",
                str(pathlib.Path(ep["bgm"]["src"]).expanduser()),
                "-t",
                f"{total:.2f}",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "192k",
                str(ROOT / eid / "audio" / "bgm.mp3"),
            ],
            check=True,
        )
        bgm = f'<audio id="bgm" data-start="0" data-duration="{total}" data-volume="{ep["bgm"]["volume"]}" src="audio/bgm.mp3"></audio>'
    blocks = vids + blocks
    audio = "\n".join(
        f'<audio id="vo-{l["i"]}" data-start="{l["start"]:.3f}" data-duration="{l["dur"]:.3f}" src="audio/l{l["i"]}.mp3"></audio>'
        for l in lines
    )
    cid = eid.replace("-", "")
    page = f"""<!doctype html>
<html lang="{'zh-Hant' if lang == 'zh' else 'en'}" data-resolution="landscape">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<title>{esc(ep["title"])}</title>
<link rel="stylesheet" href="shared/brand.css" />
<style>{CSS}</style>
<script src="vendor/gsap.min.js"></script>
</head>
<body>
<div id="root" data-composition-id="{cid}" data-start="0" data-duration="{total}" data-fps="24" data-width="{W}" data-height="{H}">
<div id="bg" class="clip" data-start="0" data-duration="{total}" data-track-index="0"><div id="grid"></div></div>
{chr(10).join(blocks)}
<div id="chrome" class="clip" data-start="0" data-duration="{total}" data-track-index="{len(lines) + 2}">
<div class="brand">{esc(BRAND[lang])}</div>
<div class="disc">{esc(ep.get("note", NOTE[lang]))}</div>
<div class="prog"></div>
</div>
{audio}
{bgm}
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
    shutil.copytree(
        ROOT / "shared",
        pdir / "shared",
        ignore=shutil.ignore_patterns("chars", "_candidates"),
    )
    shutil.copytree(REPO / "hyperframes_trial/vendor", pdir / "vendor")
    print(f"  {eid}：{len(lines)} 頁、{total:.1f} 秒")
    return pdir


def main():
    for eid in [a for a in sys.argv[1:] if not a.startswith("--")]:
        if (
            subprocess.run([sys.executable, str(ROOT / "verify.py"), eid]).returncode
            != 0
        ):
            raise SystemExit(f"⛔ {eid} 事實查核沒過，不產片")
        pdir = build(eid)
        if "--render" in sys.argv:
            subprocess.run(["npx", "--yes", HF, "check"], cwd=pdir, check=True)
            hf_render(pdir)
            from podcast_wide import speed_up

            speed_up(pdir, SCRIPTS["episodes"][eid])


if __name__ == "__main__":
    main()
