"""奶酪短片設定檔產生器。字幕從逐字稿自動切（同長片的校正表），產出 dessert/奶酪_短*_config.json。
段落：(素材, 起, 迄, 裁切中心 cx)。cx＝9:16 裁切框在橫式畫面的水平中心（0~1），用 preview_crop.py 校。"""

import json
import subprocess
from common import ROOT, HERE, OVR, snap, cues_for

# 只在短片改寫的句子（長片已渲染，不動共用校正表）
OVR.update({"所以這個牛奶跟鮮奶油250250": "牛奶跟鮮奶油250、250"})

SRC = f"{ROOT}/素材/奶酪"
OUT = f"{ROOT}/成品/奶酪"
TAGS = [
    "泥馬的真心話",
    "甜點輕鬆做",
    "師傅真心話",
    "奶酪",
    "義式奶酪",
    "甜點師",
    "在家做甜點",
]
HASH = (
    "#奶酪 #義式奶酪 #甜點 #甜點師 #在家做甜點 #香草 #泥馬的真心話 #甜點輕鬆做 #shorts"
)
MERGE_TAIL = {"短3_香草殼別丟"}  # 結尾句被擠掉時改成併進前一句（其餘直接拿掉）
MAXC = 13  # 9:16 一行約 14 個全形字，wrap_lines 只切一刀，所以每個逗號片段要 ≤13



def probe_dur(n):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          f"{SRC}/IMG_{n}.MOV"], capture_output=True, text=True).stdout
    return float(out)


SHORTS = [  # (檔名鍵, 封面字, 標題, 說明, 段落, 封面(素材, 秒))
    (
        "短1_最貴香草",
        "一根香草300塊　甜點師捨不得用",
        "一根香草300多塊，甜點師說嫁女兒才用 #甜點師",
        "Pompona 大花香草，師傅說一支 300 多塊，平常只拿來觀賞。\n要做什麼才捨得用？嫁女兒、求婚。",
        [
            (5303, 11.9, 16.2, 0.5),
            (5303, 136.2, 163.5, 0.5),
            (5303, 54.4, 71.1, 0.5),
            (5303, 189.1, 211.75, 0.5),
        ],
        (5303, 140),
    ),
    (
        "短2_香草別冰",
        "香草千萬不要放冰箱",
        "香草千萬不要放冰箱，很多店家都放錯 #甜點師",
        "香草放冰箱會加速老化、容易硬掉，進進出出還會產生水氣發黴。\n表面的白霜不是發黴，是香草的油脂遇冷凝結。",
        [(5305, 10.0, 54.7, 0.5)],
        (5305, 2),
    ),
    (
        "短3_香草殼別丟",
        "香草殼不要丟　塞進砂糖裡",
        "用完的香草殼不要丟，法式甜點店都這樣用 #甜點師",
        "香草殼裡還有很多精華：先用牛奶刮洗一次，再洗乾淨曬乾，塞進砂糖罐裡，糖就會有香草味。",
        [(5312, 20.2, 27.9, 0.5), (5312, 1.0, 19.2, 0.5), (5312, 38.4, 90.9, 0.48)],
        (5312, 22),
    ),
    (
        "短4_底部黑黑",
        "奶酪底部黑黑一片？",
        "為什麼你做的奶酪，底部黑黑一片 #甜點師",
        "香草籽和配料都會沉到底。\n煮好先降溫到有點濃稠再灌杯，香草籽就會漂浮在半空中。",
        [
            (5311, 164.9, 186.4, 0.52),
            (5311, 189.0, 212.4, 0.52),
            (5319, 212.8, 223.3, 0.45),
        ],
        (5319, 216),
    ),
    (
        "短5_吉利丁86度",
        "吉利丁超過86度就沒救",
        "吉利丁超過86度，凝固力就回不來了 #甜點師",
        "師傅的說法：86 度是吉利丁的死亡溫度。\n降溫過頭硬掉了可以微波回溫，但溫度不要超過 86 度。",
        [(5313, 50.0, 100.8, 0.48)],
        (5313, 30),
    ),
    (
        "短6_不能脫模",
        "奶酪為什麼不能脫模",
        "奶酪為什麼不能脫模？布丁卻可以 #甜點師",
        "奶酪有鮮奶油的油脂，吉利丁又不會出水，跟杯子之間沒有空隙。\n真的要脫模：灌在金屬杯，泡一下熱水再脫。",
        [(5319, 19.2, 43.3, 0.46), (5319, 107.9, 146.4, 0.46)],
        (5319, 44),
    ),
    (
        "短7_飯店配方",
        "五星級飯店的奶酪配方",
        "五星級飯店的奶酪配方：一千對六片 #甜點師",
        "牛奶、鮮奶油各半，液體一千配六片金級吉利丁（一片 2.5 克），糖 8%。\n師傅以前在台北五星級飯店，就是這個做法。",
        [
            (5311, 41.9, 58.1, 0.6),
            (5311, 76.9, 90.3, 0.6),
            (5311, 117.8, 128.0, 0.6),
            (5319, 56.9, 84.8, 0.46),
        ],
        (5319, 60),
    ),
    (
        "短8_十四歲煮焦",
        "我14歲煮奶酪也會焦",
        "甜點師：我14歲煮奶酪也會煮焦 #甜點師",
        "煮東西的火不要從鍋邊竄上來，維持在鍋底就好。\n沒有溫度計：輕拍鍋底，微微燙手但還貼得住，大概就是 60 度。",
        [(5311, 346.6, 388.0, 0.48), (5311, 482.3, 497.6, 0.56)],
        (5311, 352),
    ),
    (
        "短9_巧克力工廠",
        "他以前在巧克力工廠偷吃",
        "以前在巧克力工廠，他每天跑來偷吃 #甜點師",
        "飯店點心房大概 20 到 22 度，巧克力房常年 18 度。\n以前師傅在巧克力工廠，鏡頭後面這位每天跑來吹冷氣、偷吃巧克力。",
        [(5315, 57.4, 121.9, 0.5)],
        (5315, 100),
    ),
]

for key, subject, title, desc, segs, cover in SHORTS:
    vids = []

    def vi(n):
        p = f"{SRC}/IMG_{n}.MOV"
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
        words = [w for x in json.load(open(f"{HERE}/transcripts/IMG_{n_last}.json")) for w in x["words"]]
        ns = min([w["s"] for w in words if w["s"] >= ce + 0.05] or [ce + 99])
        dur = probe_dur(n_last)
        if min(ns - 0.2, dur - 0.1) >= ce + 1.2:
            S[-1][2] = round(min(ns - 0.2, dur - 0.1, ce + 1.8), 2)
        else:
            # 提早收掉後短於 0.5 秒的就拿掉、改收前一句（聲音還在，只是不上字幕）
            while True:
                last = max((c for c in C if c[0] == v and a <= c[1] <= b), key=lambda c: c[2])
                if last[2] <= b - 1.2:
                    break
                if b - 1.2 - last[1] >= 0.5:
                    last[2] = round(b - 1.2, 2)
                    break
                prev = max((c for c in C if c is not last and c[0] == v and a <= c[1] <= b), key=lambda c: c[2])
                if key in MERGE_TAIL:  # 同一人講的結論句：併進前一句再提早收，不要讓結論沒字幕
                    prev[3] = f"{prev[3]}，{last[3]}"
                    prev[4] = prev[4] + last[4]
                C.remove(last)
    for i, (v1, a1, b1, _) in enumerate(S):
        for v2, a2, b2, _ in S[i + 1:]:
            if v1 == v2 and a1 < b2 + 0.15 and a2 < b1 + 0.15:
                raise SystemExit(f"❌ {key}：同素材段落 {a1}-{b1} 與 {a2}-{b2} 重疊或太近（newt 會對錯段）")
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
        open(f"{ROOT}/dessert/奶酪_{key}_config.json", "w"),
        ensure_ascii=False,
        indent=1,
    )
    src = sum(b - a for _, a, b, _ in S)
    print(f"{key}：{len(S)} 段、字幕 {len(C)}、約 {src / 1.2:.0f} 秒")
