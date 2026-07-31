#!/usr/bin/env python3
"""market_report.verify() 的回歸測試 — 合成資料，不打任何 API、不碰正式產出。

用法: python3 market/test_verify.py        （全過回傳 0，有情境不符預期回傳 1）
      python3 market/test_verify.py -v     （連每個情境的驗證表一起印）
"""

import io
import sys
import tempfile
import time
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import market_report as m

NOW = int(time.time())
VERBOSE = "-v" in sys.argv


def quote(code, name, price, holding=False):
    return {
        "code": code,
        "name": name,
        "price": price,
        "change": 1.0 if price else None,
        "change_pct": 0.5 if price else None,
        "ts": NOW if price else 0,
        "currency": "",
        "dec": 2,
        "holding": holding,
    }


def market_data():
    return {
        "indices": [
            quote("^TWII", "台灣加權指數", 23000),
            quote("^GSPC", "S&P 500", 6000),
        ],
        "macro": [quote("^VIX", "VIX 恐慌指數", 15)],
        "stocks": [
            quote("2610.TW", "華航", 20, True),
            quote("2330.TW", "台積電", 1100),
        ],
        "us_stocks": [],
    }


PREDICTION = {
    "sentiment": "多頭",
    "sentiment_score": 7,
    "key_news": ["新聞"],
    "week_outlook": "展望",
    "risks": ["風險"],
    "holdings_advice": [{"code": "2610", "name": "華航", "action": "持有"}],
}


def no_quotes(md):
    for d in md["indices"] + md["macro"] + md["stocks"]:
        d["price"] = None


def no_taiex(md):
    md["indices"][0]["price"] = None


def stale(md):
    for d in md["indices"] + md["macro"] + md["stocks"]:
        d["ts"] = NOW - 9 * 86400


# (情境, md 破壞函式, prediction, Notion 實際區塊數偏移, 硬性是否該通過)
CASES = [
    ("正常", None, PREDICTION, 0, True),
    ("Yahoo 全掛", no_quotes, PREDICTION, 0, False),
    ("加權指數缺", no_taiex, PREDICTION, 0, False),
    ("Gemini 額度用罄", None, {}, 0, True),
    ("Notion 只寫一半", None, PREDICTION, -8, False),
    (
        "持股漏建議+分數非整數",
        None,
        dict(PREDICTION, holdings_advice=[], sentiment_score="七"),
        0,
        True,
    ),
    ("報價過期 9 天", stale, PREDICTION, 0, True),
]


def run_case(break_md, prediction, notion_delta, tmpdir):
    md = market_data()
    if break_md:
        break_md(md)
    blocks = m.build_notion_blocks(md, prediction)
    m.notion_req = lambda *a, **k: {"results": [{}] * (len(blocks) + notion_delta)}
    m.REPORTS_DIR = tmpdir

    buf = io.StringIO()
    with redirect_stdout(buf):
        path = m.save_markdown_report(md, prediction, "2000-01-01")
        passed = m.verify(md, prediction, blocks, "fake-page-id", path)
    return passed, buf.getvalue()


def main():
    with tempfile.TemporaryDirectory() as td:
        results = [
            (label, expect) + run_case(fn, pred, delta, Path(td))
            for label, fn, pred, delta, expect in CASES
        ]

    print("\n{:<24} {:<8} {}".format("情境", "硬性", "是否符合預期"))
    print("-" * 48)
    all_ok = True
    for label, expect, passed, detail in results:
        hit = passed == expect
        all_ok &= hit
        print(
            "{:<24} {:<8} {}".format(
                label, "通過" if passed else "擋下", "✅" if hit else "❌ 不符預期"
            )
        )
        if VERBOSE or not hit:
            print(detail)

    print("\n" + ("全部符合預期" if all_ok else "⚠️ 有情境不符預期"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
