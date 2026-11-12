"""把 ms-02（《錢的誤會》網購拆封就不能退？）腳本寫進 scripts.json。只做 Short，不發長片。"""

import json
import pathlib

P = pathlib.Path(__file__).resolve().parent.parent / "scripts.json"
B = {"kind": "broll"}


def stat(head, big, note=""):
    return {"kind": "stat", "head": head, "big": big, "note": note}


def cards(head, *items):
    return {"kind": "calendar", "head": head, "items": [{"date": d, "what": w} for d, w in items]}


L = [
    ("網購頁面寫著：「一經拆封，恕不退換」。拆了，就真的沒辦法退嗎？",
     "網購頁面寫著：一經拆封，恕不退換。拆了，就真的沒辦法退嗎？", [], B, "mm_store"),
    ("向業者網購，收到商品後 7 天內，一般可以不說理由，解除契約、退回商品。",
     "向業者網購，收到商品後七天內，一般可以不說理由，解除契約，退回商品。",
     ["RT01"], stat("消費者保護法第 19 條", "7 天內可解除契約", "向業者網購｜不必說理由"), "mm_laptop"),
    ("一般從收到商品的隔天起算；期限內寄出商品，或發出書面通知，就算數。",
     "一般從收到商品的隔天起算；期限內寄出商品，或發出書面通知，就算數。", ["RT01"], B, "mm_store"),
    ("拆封呢？在檢查必要的範圍內拆開、使用，解除權不會因此消失。", None, ["RT02"], B, "mm_phone"),
    ("業者也不能用「拆封不退」，一概排除這個權利。",
     "業者也不能用拆封不退，一概排除這個權利。",
     ["RT02"], stat("消保會函釋｜「拆封不退」條款", "不能一概排除", "排除必要檢查權利的條款無效"), "mm_store"),
    ("不過，商品如果有毀損或減損，退貨時可能要按比例，償還減少的價值。", None, ["RT03"], B, "mm_laptop"),
    ("另外，法律列了 7 類例外：符合條件、而且業者事先告知，才可以排除這 7 天的權利。",
     "另外，法律列了七類例外：符合條件，而且業者事先告知，才可以排除這七天的權利。", ["RT04"], B, "mm_store"),
    ("像容易腐敗或保存期限短的商品、照你要求客製的商品，還有報紙、期刊、雜誌；",
     "像容易腐敗，或保存期限短的商品，照你要求客製的商品，還有報紙，期刊，雜誌；",
     ["RT04"], cards("7 類例外（要符合條件＋事先告知）", ("①", "易腐敗、保存期短"), ("②", "依你要求客製"), ("③", "報紙、期刊、雜誌")), "mm_store"),
    ("以及拆封的影音和電腦軟體、拆封的個人衛生用品、你事先同意提供的線上數位內容，和國際航空客運。",
     "以及拆封的影音和電腦軟體，拆封的個人衛生用品，你事先同意提供的線上數位內容，和飛國外的航空客運。",
     ["RT04"], cards("7 類例外（續）", ("④", "拆封的影音、軟體"), ("⑤", "拆封的個人衛生用品"), ("⑥", "事先同意的線上數位內容"), ("⑦", "國際航空客運")), "mm_store"),
    ("這 7 天的規定，是給網購這類交易；在實體店面現場買，沒有這條。",
     "這七天的規定，是針對網購這類交易；在實體店面現場買，沒有這條。", ["RT01"], B, "mm_store"),
    ("所以，拆封不一定就失去退貨的權利。", None, ["RT02", "RT04"], B, "mm_phone"),
    ("關注我，給你更多錢的大小事。", None, [], {"kind": "outro", "a": "關注我", "b": "給你更多錢的大小事", "btn": "訂閱"}, None),
]

CARD_TIMING = {
    "7 類例外（要符合條件＋事先告知）": {"card_at": [0.3, 1.6, 3.0], "hold": 0.8},
    "7 類例外（續）": {"card_at": [0.4, 1.8, 3.4, 5.2], "hold": 0.8},
}
REJECT = json.loads(P.read_text())["episodes"]["mem-01"]["reject"]

EP = {
    "format": "slides",
    "aspect": "16:9",
    "tts": "clone",
    "gap": 0.15,
    "speed": 1.2,
    "shot": 5.0,
    "lang": "zh",
    "ui": "zh",
    "title": "網購拆封就不能退？7 天退貨的真相",
    "caption": "資料：消費者保護法、消費者保護法施行細則、行政院消費者保護會",
    "note": "資訊整理，非法律建議｜個案可洽消保官｜資料來源見說明欄｜畫面為資料畫面，非片中提及品牌",
    "bgm": {"src": "~/liam-workspace/assets/bgm/night_music.mp3", "volume": 0.12},
    "reject": REJECT,
    "lines": [
        {
            "speaker": "narr",
            "text": t,
            "say": s or t,
            "facts": f,
            "screen": sc,
            **({"dim": True} if sc["kind"] in ("stat", "bars", "calendar") else {}),
            **({"pool": p} if p else {}),
            **CARD_TIMING.get(sc.get("head"), {}),
        }
        for t, s, f, sc, p in L
    ],
}

d = json.loads(P.read_text())
d["episodes"]["ms-02"] = EP
P.write_text(json.dumps(d, ensure_ascii=False, indent=1))
print(len(L), "句", sum(len(x[0]) for x in L), "字")
