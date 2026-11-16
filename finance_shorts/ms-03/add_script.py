"""把 ms-03（《錢的誤會》年終獎金一定要發？）腳本寫進 scripts.json。只做 Short，不發長片。"""

import json
import pathlib

P = pathlib.Path(__file__).resolve().parent.parent / "scripts.json"
B = {"kind": "broll"}


def stat(head, big, note=""):
    return {"kind": "stat", "head": head, "big": big, "note": note}


def cards(head, *items):
    return {
        "kind": "calendar",
        "head": head,
        "items": [{"date": d, "what": w} for d, w in items],
    }


L = [
    (
        "很多人以為：年終獎金是法律規定，公司一定要發。真的是這樣嗎？",
        None,
        [],
        B,
        "tw_mrt",
    ),
    (
        "其實，勞基法對年終獎金怎麼發、發多少，沒有強制規定，主要看你和公司的約定。",
        "其實，勞基法對年終獎金怎麼發，發多少，沒有強制規定，主要看你和公司的約定。",
        ["YB02"],
        stat(
            "勞委會 89 年函釋",
            "沒有強制標準",
            "年終獎金的發放標準及方式｜宜由勞雇雙方協商",
        ),
        "tw_city",
    ),
    (
        "約定通常寫在勞動契約、工作規則，或團體協約。",
        "約定通常寫在勞動契約，工作規則，或團體協約。",
        ["YB02"],
        cards(
            "年終獎金的約定，寫在哪？",
            ("①", "勞動契約"),
            ("②", "工作規則"),
            ("③", "團體協約"),
        ),
        "tw_tm",
    ),
    (
        "法律有寫的是勞基法第 29 條：公司年度結算有盈餘，繳完稅、填補虧損、提列股息和公積金之後，",
        "法律有寫的是，勞基法第二十九條：公司年度結算有盈餘，繳完稅，填補虧損，提列股息和公積金之後，",
        ["YB01"],
        B,
        "tw_city",
    ),
    (
        "符合這些條件，對全年工作、沒有過失的勞工，要發獎金或分配紅利。",
        "符合這些條件，對全年工作，沒有過失的勞工，要發獎金，或分配紅利。",
        ["YB01"],
        stat(
            "勞動基準法第 29 條",
            "扣除後仍有盈餘",
            "扣稅捐、虧損、股息公積金｜全年無過失者應給獎金或紅利",
        ),
        "tw_mrt",
    ),
    (
        "但這一條沒有寫要發多少、怎麼算。",
        "但這一條沒有寫要發多少，怎麼算。",
        ["YB01"],
        B,
        "tw_tm",
    ),
    (
        "相反的，契約如果寫明「保證年薪 14 個月」，多出來的部分可能被認定是工資。",
        "相反的，契約如果寫明，保證年薪十四個月，多出來的部分，可能被認定是工資。",
        ["YB03"],
        stat(
            "約定成固定薪資結構",
            "可能算工資",
            "例：保證年薪 14 個月｜是否屬工資依個案判斷",
        ),
        "bk_atm",
    ),
    ("被認定是工資，公司就不能因為沒賺錢而不發。", None, ["YB03"], B, "tw_city"),
    (
        "發放前離職呢？恩惠性的獎金，多半約定發放當天要在職；屬於工資的部分，仍可能依在職時間比例要求。",
        None,
        ["YB04"],
        B,
        "tw_mrt",
    ),
    (
        "所以，年終獎金有沒有，要看法定條件、約定和獎金性質。",
        "所以，年終獎金有沒有，要看法定條件，約定，和獎金性質。",
        ["YB01", "YB02", "YB03"],
        B,
        "tw_tm",
    ),
    (
        "想知道自己的情況，看勞動契約和工作規則；30 人以上的公司，工作規則要公開揭示。有疑問可洽勞工主管機關。",
        "想知道自己的情況，看勞動契約，和工作規則；三十人以上的公司，工作規則要公開揭示。有疑問，可以洽勞工主管機關。",
        ["YB05", "YB02"],
        stat(
            "勞動基準法第 70 條",
            "30 人以上",
            "工作規則要訂「津貼及獎金」｜核備後公開揭示",
        ),
        "tw_city",
    ),
    (
        "關注我，給你更多錢的大小事。",
        None,
        [],
        {"kind": "outro", "a": "關注我", "b": "給你更多錢的大小事", "btn": "訂閱"},
        None,
    ),
]

CARD_TIMING = {"年終獎金的約定，寫在哪？": {"card_at": [0.9, 1.8, 2.8], "hold": 0.8}}
EPS = json.loads(P.read_text())["episodes"]
REJECT = sorted(set(EPS["ms-01"]["reject"]) | set(EPS["ms-02"]["reject"]))

EP = {
    "format": "slides",
    "aspect": "16:9",
    "tts": "clone",
    "gap": 0.15,
    "speed": 1.2,
    "shot": 5.0,
    "clip_max": 6.0,
    "lang": "zh",
    "ui": "zh",
    "title": "年終獎金一定要發？法律怎麼寫",
    "caption": "資料：勞動基準法、勞動基準法施行細則、勞動部勞動法令查詢系統",
    "note": "資訊整理，非法律建議｜個案可洽當地勞工主管機關｜資料來源見說明欄｜畫面為資料畫面",
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
d["episodes"]["ms-03"] = EP
P.write_text(json.dumps(d, ensure_ascii=False, indent=1))
print(len(L), "句", sum(len(x[0]) for x in L), "字")
