"""布丁短片設定檔產生器。字幕從逐字稿自動切（同長片的校正表），產出 dessert/布丁_短*_config.json。
段落：(素材, 起, 迄, 裁切中心 cx)。cx＝9:16 裁切框在橫式畫面的水平中心（0~1），每段抽格畫框校過。"""

import json
import subprocess
from common import ROOT, HERE, OVR, snap, cues_for

SRC = f"{ROOT}/素材/布丁"
FIXED = {
    5585: f"{ROOT}/成品/布丁長片/工作檔/IMG_5585_fixed.MOV"
}  # 旋轉標記錯誤，用清掉標記的版本
OUT = f"{ROOT}/成品/布丁"
TAGS = [
    "泥馬的真心話",
    "甜點輕鬆做",
    "師傅真心話",
    "布丁",
    "焦糖布丁",
    "甜點師",
    "在家做甜點",
]
HASH = "#布丁 #焦糖布丁 #甜點 #甜點師 #在家做甜點 #泥馬的真心話 #甜點輕鬆做 #shorts"
MERGE_TAIL = set()
MAXC = 13


def probe_dur(n):
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            FIXED.get(n, f"{SRC}/IMG_{n}.MOV"),
        ],
        capture_output=True,
        text=True,
    ).stdout
    return float(out)


SHORTS = [  # (檔名鍵, 封面字, 標題, 說明, 段落, 封面(素材, 秒))
    (
        "短1_靠布丁繳房貸",
        "一杯布丁60塊　他靠這個繳房貸",
        "一杯布丁60塊，甜點師曾靠它繳房貸 #甜點師",
        "剛從北京回台灣、房子剛買，賺不到錢，就靠自己做布丁、賣布丁貼補家用。\n一次最多做 200 杯，一杯 60 塊，要做好幾天。",
        [(5573, 12.2, 38.0, 0.5), (5573, 58.2, 65.9, 0.55), (5574, 0.7, 22.5, 0.58)],
        (5573, 30),
    ),
    (
        "短2_焦糖別攪拌",
        "煮焦糖千萬不要攪拌",
        "煮焦糖千萬不要攪拌，一攪就翻砂 #甜點師",
        "糖受熱融化後一直攪拌，會重新結晶，變成沙沙的「翻砂」。\n顏色不均勻可以晃鍋子，不要攪。",
        [(5574, 44.5, 79.5, 0.56)],
        (5574, 50),
    ),
    (
        "短3_炸到天花板",
        "熱水一次倒下去　會炸到天花板",
        "焦糖加熱水一次倒下去，會炸到天花板 #甜點師",
        "焦糖煮好要加熱水，記得關火、慢慢加。\n才 50 克的糖就冒成這樣，一大鍋直接倒下去會炸到天花板。",
        [(5578, 34.5, 71.3, 0.5)],
        (5578, 58),
    ),
    (
        "短4_南北焦糖",
        "南部人不愛苦焦糖？",
        "焦糖要多深？甜點師說南北口味不一樣 #甜點師",
        "焦糖顏色很看個人喜好：去中南部出差，焦糖要淺一些；北部的同學喜歡帶一點微苦。\n你喜歡哪一種？",
        # 人放右側；12.09–13.47 鏡頭後拉，那 1.4 秒畫面另從 cx 0.62 版接回（見 備份_南部改裁切前）
        [(5575, 7.6, 40.3, 0.52)],
        (5575, 12),
    ),
    (
        "短5_保鮮膜消泡",
        "布丁表面的泡泡　以前用紙巾吸",
        "布丁表面的泡泡，甜點師用保鮮膜一貼就沒了 #甜點師",
        "以前入行的時候，是拿廚房紙巾貼在表面吸泡泡，不衛生又耗損。\n現在用保鮮膜完全貼面，邊邊要塞進去，倒出來泡泡就留在保鮮膜上。",
        [
            (5585, 19.2, 39.7, 0.45),
            (5586, 0.5, 11.0, 0.52),
            (5586, 15.9, 30.7, 0.48),
            (5586, 40.2, 46.6, 0.58),
        ],
        (5586, 5),
    ),
    (
        "短6_大同電鍋",
        "大同電鍋也能蒸布丁",
        "沒有烤箱？大同電鍋就能蒸布丁 #甜點師",
        "布丁用蒸的效果最好，大同電鍋就可以。\n鍋蓋斜放、兩邊留兩指，網架一定要放，大概五分鐘看一下、換個邊。\n表面都是泡泡、邊邊都是氣孔，就是溫度太高。",
        [(5588, 121.7, 133.8, 0.5), (5589, 6.2, 39.3, 0.5), (5589, 47.2, 58.1, 0.45)],
        (5589, 10),
    ),
    (
        "短7_不能冷凍",
        "布丁不能冷凍　熱的也不好吃",
        "布丁可以冷凍嗎？甜點師：會變沙沙的 #甜點師",
        "布丁放涼之後冷藏，冰過再吃比較好吃；冷凍就跟牛奶一樣，口感不會恢復，會沙沙的。\n熱的也不好吃：甜度變高、蛋的腥味還壓不下來。",
        [(5592, 30.9, 49.6, 0.55), (5593, 2.1, 21.4, 0.55)],
        (5593, 8),
    ),
]
for key, subject, title, desc, segs, cover in SHORTS:
    vids = []

    def vi(n):
        p = FIXED.get(n, f"{SRC}/IMG_{n}.MOV")
        if p not in vids:
            vids.append(p)
        return vids.index(p)

    S, C = [], []
    for n, a, b, cx in segs:
        a, b = snap(n, a, b)
        S.append([vi(n), a, b, cx])
        C += [[vi(c[0])] + c[1:] for c in cues_for(n, a, b, MAXC)]
    # 結尾留白：最後一條字幕結束後要留 1 秒以上（輸出時間，1.2 倍速＝素材 1.2 秒）
    n_last = segs[-1][0]
    v, a, b, cx = S[-1]
    ce = max(c[2] for c in C if c[0] == v and a <= c[1] <= b)
    if b - ce < 1.2:
        words = [
            w
            for x in json.load(open(f"{HERE}/transcripts/IMG_{n_last}.json"))
            for w in x["words"]
        ]
        ns = min([w["s"] for w in words if w["s"] >= ce + 0.05] or [ce + 99])
        dur = probe_dur(n_last)
        if min(ns - 0.2, dur - 0.1) >= ce + 1.2:
            S[-1][2] = round(min(ns - 0.2, dur - 0.1, ce + 1.8), 2)
        else:
            # 提早收掉後短於 0.5 秒的就拿掉、改收前一句（聲音還在，只是不上字幕）
            while True:
                last = max(
                    (c for c in C if c[0] == v and a <= c[1] <= b), key=lambda c: c[2]
                )
                if last[2] <= b - 1.2:
                    break
                if b - 1.2 - last[1] >= 0.5:
                    last[2] = round(b - 1.2, 2)
                    break
                prev = max(
                    (c for c in C if c is not last and c[0] == v and a <= c[1] <= b),
                    key=lambda c: c[2],
                )
                if (
                    key in MERGE_TAIL
                ):  # 同一人講的結論句：併進前一句再提早收，不要讓結論沒字幕
                    prev[3] = f"{prev[3]}，{last[3]}"
                    prev[4] = prev[4] + last[4]
                C.remove(last)
    for i, (v1, a1, b1, _) in enumerate(S):
        for v2, a2, b2, _ in S[i + 1 :]:
            if v1 == v2 and a1 < b2 + 0.15 and a2 < b1 + 0.15:
                raise SystemExit(
                    f"❌ {key}：同素材段落 {a1}-{b1} 與 {a2}-{b2} 重疊或太近（newt 會對錯段）"
                )
    cfg = {
        "videos": vids,
        "subject": subject,
        "out_dir": OUT,
        "speed": 1.2,
        "bgm": False,
        "cover_intro": 0,
        "fit": "crop",
        "segments": S,
        "cues": C,
        "cover": {
            "video_index": vi(cover[0]),
            "time": cover[1],
            "main": subject,
            "sub": "",
        },
        "youtube": {"title": title, "description": f"{desc}\n\n{HASH}", "tags": TAGS},
    }
    json.dump(
        cfg,
        open(f"{ROOT}/dessert/布丁_{key}_config.json", "w"),
        ensure_ascii=False,
        indent=1,
    )
    src = sum(b - a for _, a, b, _ in S)
    print(f"{key}：{len(S)} 段、字幕 {len(C)}、約 {src / 1.2:.0f} 秒")
