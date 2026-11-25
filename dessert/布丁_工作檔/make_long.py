"""布丁 16:9 長片設定：段落手選，字幕從逐字稿自動切再套校正表。產出 dessert/布丁_長片_config.json
沿用 奶酪_工作檔/make_long.py。不用：5572（蜘蛛、麥克風）、5577（幻覺）、5590 21 秒後與 5584 181~205（氣炸鍋，廠商樣品＝置入）。
IMG_5585 的旋轉標記錯誤（實際橫拍卻標 90 度），用清掉標記的 IMG_5585_fixed.MOV。"""

import json, os
from common import ROOT, HERE, snap, cues_for

SECTIONS = [  # (章節名, [(素材, 起, 迄)])
    ("熱水一次倒下去，會炸到天花板", [(5578, 56.0, 71.3)]),
    (
        "一杯 60 塊，靠賣布丁繳房貸",
        [(5573, 0.7, 43.3), (5573, 51.8, 65.9), (5574, 0.7, 38.6)],
    ),
    (
        "焦糖千萬不要攪拌",
        [(5574, 44.5, 83.7), (5574, 101.4, 107.4), (5574, 117.4, 125.5)],
    ),
    ("南部人不愛苦焦糖？", [(5575, 7.6, 40.3)]),
    ("完美顏色的前一秒就關火", [(5575, 42.7, 79.2), (5576, 4.5, 29.3)]),
    ("熱水要慢慢加", [(5578, 0.0, 24.4), (5578, 34.5, 55.2), (5578, 107.4, 126.5)]),
    ("一罐牛奶、6 顆蛋、100 克糖", [(5579, 22.0, 101.6)]),
    ("焦糖鍋這樣洗", [(5579, 103.1, 114.0), (5580, 3.4, 15.8)]),
    ("怎麼看布丁新不新鮮", [(5581, 12.2, 22.0), (5581, 123.3, 197.4)]),
    ("練習不要用貴的香草", [(5582, 31.1, 60.4)]),
    ("這個爐子怎麼這麼髒", [(5583, 0.0, 30.9)]),
    ("牛奶溫度用小指頭試", [(5584, 116.8, 180.9), (5584, 206.2, 225.3)]),
    (
        "表面泡泡：以前用紙巾，現在用保鮮膜",
        [(5585, 2.6, 39.7), (5585, 56.4, 60.4), (5586, 0.5, 46.6), (5587, 0.0, 26.6)],
    ),
    (
        "蒸汽烤箱、水浴、大同電鍋",
        [(5588, 38.7, 95.9), (5588, 112.6, 133.8), (5589, 6.2, 58.1)],
    ),
    ("蒸多久？蒸過頭會怎樣", [(5591, 12.5, 31.4), (5591, 56.2, 95.3)]),
    ("不能冷凍、熱的不好吃、怎麼脫模", [(5592, 30.9, 52.1), (5593, 2.1, 45.6)]),
    ("試吃：沒有氣孔", [(5594, 18.4, 60.4), (5597, 3.9, 32.6), (5595, 0.0, 13.4)]),
    ("下次想看什麼？", [(5590, 0.0, 20.2)]),
]
SECTIONS = [
    (name, [(n, *snap(n, a, b)) for n, a, b in rngs]) for name, rngs in SECTIONS
]

# 2026-11-21 Lien：沒在講話的場景剪掉。素材秒 1.8（成片 1.5 秒）以上的空檔剪掉，句間前後各留 PAD、段尾留 TAIL
GAP, PAD, TAIL = 1.8, 0.3, 0.6


def trim_gaps(n, a, b):
    ws = sorted(
        (
            w
            for s in json.load(open(f"{HERE}/transcripts/IMG_{n}.json"))
            for w in s["words"]
            if a <= w["s"] < b
        ),
        key=lambda w: w["s"],
    )
    if not ws:
        return [(n, a, b)]
    if ws[0]["s"] - a > GAP:
        a = round(ws[0]["s"] - PAD, 2)
    if b - ws[-1]["e"] > GAP:
        b = round(ws[-1]["e"] + TAIL, 2)
    out, cur = [], a
    for w1, w2 in zip(ws, ws[1:]):
        if w2["s"] - w1["e"] > GAP:
            out.append((n, cur, round(w1["e"] + PAD, 2)))
            cur = round(w2["s"] - PAD, 2)
    out.append((n, cur, b))
    return out


SECTIONS = [(name, [p for r in rngs for p in trim_gaps(*r)]) for name, rngs in SECTIONS]

_flat = [(n, a, b) for _, r in SECTIONS for n, a, b in r]
for i, (n1, a1, b1) in enumerate(_flat):
    for n2, a2, b2 in _flat[i + 1 :]:
        if n1 == n2 and a1 < b2 + 0.15 and a2 < b1 + 0.15:
            raise SystemExit(f"❌ IMG_{n1} 段落 {a1}-{b1} 與 {a2}-{b2} 重疊或太近")

vids, segs, cues = [], [], []


def vi(n):
    p = (
        f"{ROOT}/成品/布丁長片/工作檔/IMG_5585_fixed.MOV"
        if n == 5585
        else f"{ROOT}/素材/布丁/IMG_{n}.MOV"
    )
    if p not in vids:
        vids.append(p)
    return vids.index(p)


for name, rngs in SECTIONS:
    for n, a, b in rngs:
        segs.append([vi(n), a, b])
        cues += [[vi(c[0])] + c[1:] for c in cues_for(n, a, b)]

DESC = """一杯布丁 60 塊，一次最多做 200 杯、要做好幾天。甜點師說，剛從北京回台灣、房子剛買的那幾年，就是靠賣布丁貼補家用、繳房貸。

這次在家做焦糖布丁：一罐牛奶（約 1000）、6 顆蛋、糖約 100 克。
焦糖為什麼不能攪拌、熱水為什麼要慢慢加、表面泡泡怎麼用保鮮膜消掉、沒有蒸汽烤箱怎麼用大同電鍋蒸，邊做邊講給你聽。

00:00 熱水一次倒下去，會炸到天花板
00:12 一杯 60 塊，靠賣布丁繳房貸
01:30 焦糖千萬不要攪拌
02:15 南部人不愛苦焦糖？
02:41 完美顏色的前一秒就關火
03:24 熱水要慢慢加
04:12 一罐牛奶、6 顆蛋、100 克糖
05:19 焦糖鍋這樣洗
05:36 怎麼看布丁新不新鮮
06:46 練習不要用貴的香草
07:10 這個爐子怎麼這麼髒
07:29 牛奶溫度用小指頭試
08:32 表面泡泡：以前用紙巾，現在用保鮮膜
09:59 蒸汽烤箱、水浴、大同電鍋
11:46 蒸多久？蒸過頭會怎樣
12:34 不能冷凍、熱的不好吃、怎麼脫模
13:27 試吃：沒有氣孔
14:29 下次想看什麼？

原理動畫資料：Harold McGee《On Food and Cooking》、Exploratorium、《Introduction to Baking and Pastries》

#布丁 #焦糖布丁 #甜點師 #在家做甜點 #大同電鍋 #泥馬的真心話 #甜點輕鬆做"""
# 封面另做：成品/布丁長片/工作檔/封面候選.jpg（IMG_5595 0.3 秒 4K 裁切讓盤子偏右，同一支 make_cover_169 加字）
cfg = {
    "videos": vids,
    "subject": "一杯布丁60塊，甜點師曾靠它繳房貸",
    "out_dir": f"{ROOT}/成品/布丁長片",
    "speed": 1.2,
    "bgm": False,
    "cover_intro": 0,
    "fit": "wide",
    "segments": segs,
    "cues": cues,
    "cover": {
        "video_index": vi(5596),
        "time": 7,
        "main": "一杯布丁60塊\n曾靠它繳房貸",
        "sub": "甜點師的焦糖布丁",
    },
    "youtube": {
        "title": "一杯布丁60塊，甜點師曾靠它繳房貸 #布丁",
        "description": DESC,
        "tags": [
            "泥馬的真心話",
            "甜點輕鬆做",
            "師傅真心話",
            "布丁",
            "焦糖布丁",
            "甜點師",
            "在家做甜點",
            "大同電鍋",
            "保鮮膜消泡",
            "焦糖",
        ],
    },
}
json.dump(
    cfg,
    open(f"{ROOT}/dessert/布丁_長片_config.json", "w"),
    ensure_ascii=False,
    indent=1,
)
json.dump(
    [[name, rngs[0][0], rngs[0][1]] for name, rngs in SECTIONS],
    open(f"{HERE}/long_sections.json", "w"),
    ensure_ascii=False,
)
src = sum(b - a for _, r in SECTIONS for _, a, b in r)
print(
    f"段落 {len(segs)}、字幕 {len(cues)}、素材 {src:.0f} 秒 → 成片約 {src / 1.2 / 60:.1f} 分"
)
