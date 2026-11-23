"""把 ms-05（《錢的誤會》特休沒休完，年底就作廢？）腳本寫進 scripts.json。只做 Short，不發長片。"""

import json
import pathlib

P = pathlib.Path(__file__).resolve().parent.parent / "scripts.json"
B = {"kind": "broll"}


def stat(head, big, note=""):
    return {"kind": "stat", "head": head, "big": big, "note": note}


L = [
    (
        "很多人以為：特休沒休完，年底就作廢了。真的是這樣嗎？",
        "很多人以為，特休沒休完，年底就作廢了。真的是這樣嗎？",
        [],
        B,
        "tw_mrt",
    ),
    (
        "其實勞基法第 38 條規定：特休年度結束沒休完的天數，不論原因都要折算工資給你，雙方同意遞延的除外。",
        "其實勞基法第三十八條規定：特休年度結束沒休完的天數，不論原因，都要折算工資給你，雙方同意遞延的除外。",
        ["PT01"],
        stat(
            "勞動基準法第 38 條第 4 項",
            "未休要折發工資",
            "特休年度終結｜雙方協商遞延的日數除外",
        ),
        "tw_city",
    ),
    (
        "離職也一樣：辭職或被資遣，沒休完的天數都要折發。",
        "離職也一樣：辭職，或被資遣，沒休完的天數，都要折發。",
        ["PT01"],
        B,
        "tw_tm",
    ),
    (
        "例外是：你和公司談好、雙方同意，延到下一個特休年度再休。",
        "例外是：你和公司談好，雙方同意，延到下一個特休年度再休。",
        ["PT02"],
        stat(
            "例外：協商遞延",
            "雙方同意才算",
            "勞動部：不得強制遞延",
        ),
        "tw_mrt",
    ),
    (
        "延過去的天數，到下一年度結束或離職時還沒休，一樣要折發。",
        "延過去的天數，到下一年度結束，或離職時還沒休，一樣要折發。",
        ["PT02"],
        stat(
            "遞延後仍未休",
            "一樣要折發",
            "按原年度結束時的工資基準計算",
        ),
        "tw_city",
    ),
    (
        "怎麼算？未休天數乘以一日工資；月薪制是年度結束或離職前最近一個月正常工時工資除以 30。",
        "怎麼算？未休天數，乘以一日工資；月薪制是年度結束或離職前最近一個月，正常工時工資，除以三十。",
        ["PT03"],
        stat(
            "施行細則第 24 條之 1",
            "天數×一日工資",
            "月薪制：年度結束或離職前最近一個月正常工時工資 ÷ 30",
        ),
        "tw_tm",
    ),
    (
        "舉例：月薪制，年度結束時 5 天沒休也沒延後，正常工時工資 30,000，除以 30 再乘以 5，就是 5,000 元。",
        "舉例：月薪制，年度結束時五天沒休，也沒延後，正常工時工資三萬，除以三十，再乘以五，就是五千元。",
        ["PTFX"],
        stat(
            "本頻道試算",
            "5,000 元",
            "30,000 ÷ 30 × 5 天｜正常工時工資、未協商遞延",
        ),
        "tw_mrt",
    ),
    (
        "年度結算在約定發薪日或年度結束後 30 天內給；離職原則上當時結清，最晚在原發薪日。",
        "年度結算，在約定發薪日，或年度結束後三十天內給；離職原則上當時結清，最晚在原發薪日。",
        ["PT03"],
        B,
        "tw_tm",
    ),
    (
        "「年度」可以是到職週年、曆年或會計年度，看你和公司的約定。",
        "年度可以是到職週年，曆年，或會計年度，看你和公司的約定。",
        ["PT04"],
        B,
        "tw_city",
    ),
    (
        "想核對，看公司每年的書面通知，要寫特休日期和未休折發金額；有疑問，可洽勞工局處。",
        "想核對，看公司每年的書面通知，要寫特休日期，和未休折發金額；有疑問，可以洽勞工局處。",
        ["PT05", "PT06"],
        stat(
            "勞動基準法第 38 條第 5 項",
            "每年書面通知",
            "特休期日與未休折發金額｜記入工資清冊",
        ),
        "tw_tm",
    ),
    (
        "關注我，給你更多錢的大小事。",
        None,
        [],
        {"kind": "outro", "a": "關注我", "b": "給你更多錢的大小事", "btn": "訂閱"},
        None,
    ),
]

EPS = json.loads(P.read_text())["episodes"]
REJECT = set()
for e in ("ms-01", "ms-02", "ms-03", "ms-04"):
    REJECT |= set(EPS[e]["reject"])
REJECT |= {f"broll/tw_city_{n:02d}" for n in range(8)}
REJECT |= {f"broll/tw_res_{n:02d}" for n in range(9)}
# 2026-11-23 抽格：12、13 有地名字幕＋4K；mrt_03 站名疊字；mrt_05 車廂人臉；mrt_07 殘影；tm_14、tm_19 人物＋車牌；bk_atm_01 外國 ATM、02 近距離人物
REJECT |= {
    "broll/tw_city_12",
    "broll/tw_city_13",
    "broll/tw_mrt_03",
    "broll/tw_mrt_05",
    "broll/tw_mrt_07",
    "broll/tw_tm_14",
    "broll/tw_tm_19",
    "broll/bk_atm_01",
    "broll/bk_atm_02",
}

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
    "title": "特休沒休完，年底就作廢？",
    "caption": "資料：勞動基準法、勞動基準法施行細則、勞動部新聞稿",
    "note": "資訊整理，非法律建議｜個案可洽當地勞工主管機關｜資料來源見說明欄｜畫面為資料畫面",
    "bgm": {"src": "~/liam-workspace/assets/bgm/night_music.mp3", "volume": 0.12},
    "reject": sorted(REJECT),
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
d["episodes"]["ms-05"] = EP
P.write_text(json.dumps(d, ensure_ascii=False, indent=1))
print(len(L), "句", sum(len(x[0]) for x in L), "字")
