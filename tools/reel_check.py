#!/usr/bin/env python3
"""reel_maker config 的渲染前檢查 — 只讀不寫，不動 reel_maker.py。

build 約 5 倍實時，2 分鐘的片重跑一次要 10 分鐘。這支在幾毫秒內用同一套
時間軸對映邏輯先算過，把「渲染完才會發現」的問題提前抓出來。

用法: python3 tools/reel_check.py reels/xxx_config.json [更多 config...]
      ❌ 有 → 一定要修，不修渲染出來就是錯的
      ⚠️ 有 → 人工確認，可能是刻意的（無人聲 B-roll、口誤照實呈現）
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reel_maker as rm

CORRECTIONS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "whisper_corrections.json"
)
TOFU = "・／"  # STHeiti 沒有這兩個字，封面會印成豆腐方框
SILENT_SEG_SEC = 3.0  # 超過這個長度又整段沒字幕才值得提醒


def load_corrections():
    raw = json.load(open(CORRECTIONS, encoding="utf-8"))
    return {
        wrong: (right, group)
        for group, pairs in raw.items()
        if not group.startswith("_")
        for wrong, right in pairs.items()
    }


def normalize(cfg):
    """展開成 build() 內部用的形式：videos / segs[(v, a)] / caps[vi,s,e,txt,kw]。"""
    multi = "videos" in cfg
    videos = cfg["videos"] if multi else [cfg["video"]]
    segs = []
    for x in cfg["segments"]:
        if isinstance(x, dict):
            v, a = list(x["v"]), (list(x["a"]) if x.get("a") else None)
        else:
            v, a = list(x), None
        if not multi:
            v = [0] + v
            a = [0] + a if a else None
        segs.append((v, a))
    caps = cfg["cues"] if multi else [[0] + list(x) for x in cfg["cues"]]
    return videos, segs, caps


def timeline(segs, speed):
    """複製 build() 的 offs 與 newt()，確保與實際渲染同一套判定。"""
    offs, cum = [], 0.0
    for (vi, s, e), a in segs:
        offs.append((cum, vi, s, e, a))
        cum += e - s

    def newt(vi, t):
        for cs, svi, s, e, a in offs:
            if a and a[0] == vi and a[1] - 0.05 <= t <= a[2] + 0.05:
                return (cs + min(max(t - a[1], 0.0), e - s)) / speed
        for cs, svi, s, e, a in offs:
            if not a and svi == vi and s - 0.05 <= t <= e + 0.05:
                return (cs + min(max(t - s, 0.0), e - s)) / speed
        return None

    return offs, newt, cum


def check_sources(videos, issues):
    for i, v in enumerate(videos):
        p = os.path.expanduser(v)
        if os.path.exists(p + ".icloud") or os.path.basename(p).startswith("."):
            issues.append(
                ("❌", f"videos[{i}] 是 iCloud 佔位檔，先 brctl download：{v}")
            )
        elif not os.path.exists(p):
            issues.append(("❌", f"videos[{i}] 找不到：{v}"))
        elif os.path.getsize(p) < 100_000:
            issues.append(
                (
                    "❌",
                    f"videos[{i}] 只有 {os.path.getsize(p)} bytes，八成被回收了：{v}",
                )
            )


def check_segments(videos, segs, issues):
    for i, ((vi, s, e), a) in enumerate(segs):
        if not 0 <= vi < len(videos):
            issues.append(("❌", f"seg{i} 畫面 video_index {vi} 超出 videos 範圍"))
        if e <= s:
            issues.append(("❌", f"seg{i} 畫面時間碼 {s}→{e} 不合法"))
        if a:
            avi, as_, ae = a
            if not 0 <= avi < len(videos):
                issues.append(("❌", f"seg{i} 聲音 video_index {avi} 超出 videos 範圍"))
            if ae <= as_:
                issues.append(("❌", f"seg{i} 聲音時間碼 {as_}→{ae} 不合法"))
            elif (ae - as_) < (e - s) * 0.5:
                issues.append(
                    (
                        "⚠️",
                        f"seg{i} 借的聲音 {ae-as_:.1f}s 只有畫面 {e-s:.1f}s 的一半不到，後段會是靜音",
                    )
                )


def check_cues(offs, newt, caps, issues):
    """對不上時間軸的 cue 不會出現在成片，這是渲染完才發現的頭號問題。"""
    ghosts = []
    for n, (vi, s, e, txt, kw) in enumerate(caps):
        ns, ne = newt(vi, s), newt(vi, e)
        if ns is None or ne is None or ne <= ns:
            # 落在借音段的畫面區間 → 幾乎都是誤用畫面時間碼寫 cue
            借音畫面 = any(
                a and svi == vi and sg - 0.05 <= s <= eg + 0.05
                for _, svi, sg, eg, a in offs
            )
            why = (
                "用了借音段的畫面時間碼（cue 要用對白來源的時間碼寫）"
                if 借音畫面
                else "沒有任何 segment 涵蓋這個時間點"
            )
            ghosts.append((n, vi, s, e, txt, why))
    for n, vi, s, e, txt, why in ghosts:
        issues.append(
            ("❌", f"cue[{n}] 不會出現：「{txt[:18]}」 [{vi}] {s}→{e}s — {why}")
        )
    return len(caps) - len(ghosts)


def check_coverage(offs, caps, issues):
    """整段沒半句字幕的 segment：可能是忘了給 cue，也可能是刻意的無人聲 B-roll。"""
    if not caps:  # 整支都不上字幕（留白給旁白）是刻意的，逐段提醒只是雜訊
        return
    for i, (cs, svi, s, e, a) in enumerate(offs):
        avi, as_, ae = a if a else (svi, s, e)
        dur = e - s
        if dur < SILENT_SEG_SEC:
            continue
        covered = sum(
            max(0.0, min(ae, ce) - max(as_, cs2))
            for vi, cs2, ce, _, _ in caps
            if vi == avi
        )
        if covered <= 0.05:
            src = (
                f"聲音借自 videos[{avi}] {as_}→{ae}s"
                if a
                else f"videos[{svi}] {s}→{e}s"
            )
            issues.append(
                ("⚠️", f"seg{i}（{dur:.1f}s）整段沒有字幕 — {src}。有講話就是漏給 cue")
            )


def check_text(caps, issues):
    corrections = load_corrections()
    for n, (vi, s, e, txt, kw) in enumerate(caps):
        for k in kw:
            if k not in txt:
                # 最常見原因是字幕有空格而高光詞沒有（「一斤 240」vs「一斤240」）
                hint = (
                    f"，高光詞改成含空格的寫法就對了"
                    if k.replace(" ", "") in txt.replace(" ", "")
                    else ""
                )
                issues.append(
                    (
                        "❌",
                        f"cue[{n}] 高光詞「{k}」不在字幕裡，不會變橘黃{hint}：「{txt[:18]}」",
                    )
                )
        for line in rm.wrap_lines(txt, kw):
            mask = rm._hl_mask(line, kw)
            w = sum(rm._char_w(c, mask[i]) for i, c in enumerate(line))
            if w > rm.SAFE_W:
                issues.append(
                    (
                        "❌",
                        f"cue[{n}] 換行後仍有 {w:.0f}px > {rm.SAFE_W}，會貼邊：「{line}」",
                    )
                )
        for wrong, (right, group) in corrections.items():
            if wrong in txt:
                issues.append(
                    (
                        "⚠️",
                        f"cue[{n}] 出現「{wrong}」（{group}）→ 是不是 {right}？「{txt[:18]}」",
                    )
                )


def check_cover(videos, segs, cfg, issues):
    cov = cfg.get("cover")
    if not cov:
        return
    vi = cov.get("video_index", 0)
    if not 0 <= vi < len(videos):
        issues.append(("❌", f"cover.video_index {vi} 超出 videos 範圍"))
    for field in ("main", "line2", "sub"):
        text = cov.get(field, "")
        bad = [c for c in TOFU if c in text]
        if bad:
            issues.append(
                (
                    "⚠️",
                    f"cover.{field} 含 {''.join(bad)}，STHeiti 會印成豆腐（reel_maker 會自動替換，確認一下就好）",
                )
            )


def check_config(path):
    cfg = json.load(open(path, encoding="utf-8"))
    issues = []
    videos, segs, caps = normalize(cfg)
    speed = cfg.get("speed", 1.3)
    offs, newt, total = timeline(segs, speed)

    check_sources(videos, issues)
    check_segments(videos, segs, issues)
    hit = check_cues(offs, newt, caps, issues)
    check_coverage(offs, caps, issues)
    check_text(caps, issues)
    check_cover(videos, segs, cfg, issues)

    out = total / speed + float(cfg.get("cover_intro", 1.0))
    print(
        f"\n{'='*66}\n{cfg.get('subject', os.path.basename(path))}  —  {os.path.basename(path)}"
    )
    print(
        f"  {len(segs)} 段（{sum(1 for _, a in segs if a)} 段借音）"
        f"｜cues 對上 {hit}/{len(caps)}"
        f"｜speed {speed}｜預估成片 {int(out//60)}:{int(out%60):02d}"
    )
    errors = [m for lv, m in issues if lv == "❌"]
    for lv, m in issues:
        print(f"  {lv} {m}")
    if not issues:
        print("  ✅ 全部通過")
    return len(errors)


def main():
    paths = sys.argv[1:]
    if not paths:
        print(__doc__)
        return 1
    total_err = sum(check_config(p) for p in paths)
    print(f"\n{'='*66}")
    print(
        f"❌ 共 {total_err} 項必修，修完再 build"
        if total_err
        else "✅ 沒有必修項目，可以 build"
    )
    return 1 if total_err else 0


if __name__ == "__main__":
    sys.exit(main())
