"""把 ms-01（《錢的誤會》最低工資實拿多少）腳本寫進 scripts.json。只做 Short，不發長片。"""

import json
import pathlib

P = pathlib.Path(__file__).resolve().parent.parent / "scripts.json"
B = {"kind": "broll"}


def stat(head, big, note=""):
    return {"kind": "stat", "head": head, "big": big, "note": note}


def bars(head, *rows):
    return {"kind": "bars", "head": head, "bars": [{"label": a, "v": b, "show": c} for a, b, c in rows]}


L = [
    ("2027 年 1 月 1 日起，最低工資月薪從 29,500 元調到 30,900 元，多了 1,400 元。",
     "二零二七年一月一日起，最低工資月薪，從兩萬九千五百元，升到三萬零九百元，多了一千四百元。",
     ["MW01"], stat("2027 年最低工資", "30,900 元", "原 29,500 元，月薪多 1,400 元"), "tw_mrt"),
    ("但加薪 1,400 元，不代表入帳就多 1,400 元。",
     "但加薪一千四百元，不代表入帳就多一千四百元。", ["MW01"], B, "tw_city"),
    ("以公司幫你投保的全職月薪族為例，每個月要先扣保費。", None, [], B, "tw_mrt"),
    ("勞保加就保的費率，明年從 12.5% 調到 13%，勞工自己付其中的 20%。",
     "勞保加上就保的費率，明年從百分之十二點五，升到百分之十三，勞工自己付其中的百分之二十。",
     ["MW02"], stat("勞保＋就業保險費率", "12.5% → 13%", "勞工自付 20%"), "tw_city"),
    ("健保先用現行的 5.17% 試算，自己付 30%。",
     "健保先用現行的百分之五點一七來算，自己付百分之三十。",
     ["MW04"], stat("健保費率（現行）", "5.17%", "受僱者自付 30%｜2027 年費率以正式公告為準"), "tw_mrt"),
    ("用月薪 30,900 元試算：勞保加就保大約 800 元，健保大約 480 元。",
     "用月薪三萬零九百元來算，勞工寶險加上就業寶險，大約八百元，健保大約四百八十元。",
     ["MWFX", "MW03"], bars("月薪 30,900 元，每月自付（本頻道試算）", ("勞保＋就保", 804, "約 800 元"), ("健保", 479, "約 480 元")), "bk_atm"),
    ("只扣勞健保，大約剩 29,600 元。",
     "只扣勞健保，大約剩兩萬九千六百元。",
     ["MWFX"], stat("扣完勞健保（本頻道試算）", "約 29,600 元", "只算本人；不含眷屬健保、勞退自提與其他扣項"), "bk_atm"),
    ("同樣條件下，比今年多拿大約 1,310 元，不是整整 1,400 元。",
     "同樣條件下，比今年多拿大約一千三百一十元，不是整整一千四百元。",
     ["MWFX"], stat("實拿比今年多（本頻道試算）", "約 1,310 元", "薪資多 1,400 元"), "bk_atm"),
    ("少拿的這 80 多元，來自投保金額提高，以及勞保費率調高。",
     "少拿的這八十多元，來自投保金額提高，以及勞保費率調高。", ["MWFX", "MW02", "MW03"], B, "tw_city"),
    ("以上用投保金額 30,900 元試算，真正扣多少，以勞保局和健保署公告為準。",
     "以上用投保金額三萬零九百元試算，真正扣多少，以勞保局和健保署公告為準。", ["MWFX", "MW03"], B, "tw_mrt"),
    ("關注我，給你更多錢的大小事。", None, [], {"kind": "outro", "a": "關注我", "b": "給你更多錢的大小事", "btn": "訂閱"}, None),
]

REJECT = ["broll/bk_atm_00", "broll/bk_atm_12", "broll/bk_atm_15", "broll/bk_atm_16", "broll/tw_mrt_00", "broll/tw_mrt_01", "broll/tw_mrt_09", "broll/tw_mrt_10", "broll/tw_city_11"]

EP = {
    "format": "slides",
    "aspect": "16:9",
    "tts": "clone",
    "gap": 0.15,
    "speed": 1.2,
    "shot": 5.0,
    "lang": "zh",
    "ui": "zh",
    "title": "最低工資多 1,400 元，扣完勞健保實拿多多少？",
    "caption": "資料：勞動部、勞動部勞工保險局、行政院、衛生福利部、全民健康保險法",
    "note": "資訊整理，非法律建議｜金額為本頻道試算｜資料來源見說明欄",
    "bgm": {"src": "~/liam-workspace/assets/bgm/night_music.mp3", "volume": 0.12},
    "reject": REJECT,
    "clip_max": 6.0,
    "lines": [
        {
            "speaker": "narr",
            "text": t,
            "say": s or t,
            "facts": f,
            "screen": sc,
            **({"dim": True} if sc["kind"] in ("stat", "bars", "calendar") else {}),
            **({"pool": p} if p else {}),
        }
        for t, s, f, sc, p in L
    ],
}

d = json.loads(P.read_text())
d["episodes"]["ms-01"] = EP
P.write_text(json.dumps(d, ensure_ascii=False, indent=1))
print(len(L), "句", sum(len(x[0]) for x in L), "字")
