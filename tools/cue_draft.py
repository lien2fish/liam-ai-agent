#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""從逐字稿撈出指定區間的 cue 候選，貼進 config 後再人工修字。

手抄時間碼最容易出錯（抄錯一位數字幕就對不上），所以一律用這支產。
產出的文字仍需人工潤稿：去掉「呃」、重複語、把被切斷的句子補完。

用法：
  python3 tools/cue_draft.py <逐字稿json> <vi> <起秒> <迄秒> [更多區間...]
  例：python3 tools/cue_draft.py 素材/transcripts/IMG_4226_scribe.json 0 869 910 1012 1058
"""

import json
import sys

MIN_LEN = 2  # 太短的語助詞不值得上字幕
MAX_CHARS = 18  # 一句字幕的上限，超過就在標點處切
PUNCT = "，。、？！"
FILLER = ("呃，", "嗯，", "，呃", "對，", "，對")


def split_seg(seg):
    """用逐詞時間碼在標點處切句，避免一張字幕塞 50 個字停 13 秒。"""
    words = seg.get("words") or []
    if not words:
        return [(seg["start"], seg["end"], seg["text"])]
    out, buf, start = [], [], None
    for w in words:
        ch = w["w"]
        if start is None:
            start = w["s"]
        buf.append((ch, w["e"]))
        text = "".join(c for c, _ in buf)
        if ch in PUNCT and len(text.strip(PUNCT)) >= 8 or len(text) >= MAX_CHARS:
            out.append((start, buf[-1][1], text))
            buf, start = [], None
    if buf:
        out.append((start, buf[-1][1], "".join(c for c, _ in buf)))
    return [(s, e, t.strip(PUNCT)) for s, e, t in out if len(t.strip(PUNCT)) >= MIN_LEN]


def _corrections():
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whisper_corrections.json")
    raw = json.load(open(path, encoding="utf-8"))
    return {
        w: r.split("（")[0]
        for g, pairs in raw.items()
        if isinstance(pairs, dict) and not g.startswith("_")
        for w, r in pairs.items()
        if "勿誤改" not in r and "同上" not in r and "幻覺" not in r
    }


CORR = _corrections()


def clean(t):
    # words 陣列保留原始聽寫，錯字要在組回句子後才改（錯字常跨多個 word）
    for wrong, right in CORR.items():
        t = t.replace(wrong, right)
    for f in FILLER:
        t = t.replace(f, "，" if f.endswith("，") else "")
    return t.strip("，。、").replace("，，", "，")


def main():
    if len(sys.argv) < 5:
        print(__doc__)
        return 1
    path, vi = sys.argv[1], int(sys.argv[2])
    nums = [float(x) for x in sys.argv[3:]]
    ranges = list(zip(nums[::2], nums[1::2]))

    segs = json.load(open(path, encoding="utf-8"))
    for a, b in ranges:
        print(f"  // {a}-{b}s")
        for s in segs:
            if a <= s["start"] <= b and len(s["text"]) >= MIN_LEN:
                who = "" if s["fg"] else "  // 旁人"
                for cs, ce, txt in split_seg(s):
                    txt = clean(txt)
                    if len(txt) >= MIN_LEN:
                        print(f'  [{vi}, {cs:.1f}, {ce:.1f}, "{txt}", []],{who}')
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
