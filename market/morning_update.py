# -*- coding: utf-8 -*-
"""早盤修正（每天 08:41，開盤前）：用昨夜美股（費半）修正今日加權指數收盤區間，推 LINE。

預測紀錄寫進 market/forecast_log.json（kind=morning），晚報到期結算命中率。

用法：
    python3 market/morning_update.py            # 正式
    python3 market/morning_update.py --no-send  # 只印不推
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "market"))
sys.path.insert(0, str(ROOT))
from tw_daily import *  # noqa: E402,F401
from datetime import date, timedelta  # noqa: E402
from evening_report import load_log, save_log  # noqa: E402


def holidays():
    """證交所休市日（「開始交易日／最後交易日」那幾列是交易日，不算）。"""
    rows = json.loads(urllib.request.urlopen(urllib.request.Request(
        "https://openapi.twse.com.tw/v1/holidaySchedule/holidaySchedule", headers=UA), timeout=20).read())
    out = {}
    for h in rows:
        if "交易日" not in h["Name"]:
            r = h["Date"]
            out[date(int(r[:-4]) + 1911, int(r[-4:-2]), int(r[-2:]))] = h["Name"]
    return out


def prev_trading_day(d, hol):
    p = d - timedelta(days=1)
    while p.weekday() >= 5 or p in hol:
        p -= timedelta(days=1)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-send", action="store_true")
    args = ap.parse_args()
    d = now_tw().date()
    if d.weekday() >= 5:
        print("週末不出早盤修正")
        return
    hol = holidays()
    if d in hol:
        print(f"今日休市（{hol[d]}），不出早盤修正")
        return

    # 基準＝上一個交易日的「官方」收盤（晚報記下的）。Yahoo 常晚一天，落後就補上官方數字，
    # 否則會拿前天的收盤當基準、還會把預測結算到錯的日子。
    base_date = prev_trading_day(d, hol)
    log = load_log()
    tx = [(k, c) for k, c in yf_daily("^TWII", 10) if k <= base_date]
    official = next((e["base_close"] for e in log["forecasts"]
                     if e["kind"] == "evening" and e["base_date"] == base_date.isoformat()), None)
    if tx[-1][0] < base_date:
        if official is None:
            raise SystemExit(f"Yahoo 只到 {tx[-1][0]}，且沒有 {base_date} 的晚報官方收盤，不出修正")
        tx = merge_today(tx, base_date, official)
    base_close = tx[-1][1]
    ev = [
        e
        for e in log["forecasts"]
        if e["kind"] == "evening"
        and e["h"] == 1
        and e["base_date"] == base_date.isoformat()
    ]
    if ev and abs(ev[-1]["base_close"] / base_close - 1) > 0.001:
        raise SystemExit(
            f"Yahoo 收盤 {base_close:.2f} 與晚報官方收盤 {ev[-1]['base_close']:.2f} 不符，不出修正"
        )

    sox = [(k, c) for k, c in yf_daily("^SOX", 3) if k < d]
    if sox[-1][0] >= base_date:
        us_date, us_ret = sox[-1][0], math.log(sox[-1][1] / sox[-2][1])
        us_note = f"費半 {us_date:%m/%d} {fmt((math.exp(us_ret) - 1) * 100, sign=True, pct=True)}"
    else:
        us_ret, us_note = 0.0, "昨夜美股休市，未修正方向"
    mf = morning_forecast(tx, sox, us_ret)
    mbt = morning_backtest(tx, sox)
    q = mf["q"]

    adr_note = ""
    try:
        tsm = yf_daily("TSM", 0.1)[-1][1]
        twd = yf_daily("TWD=X", 0.1)[-1][1]
        tsmc = [c for k, c in yf_daily("2330.TW", 0.1) if k < d][-1]
        adr_note = f"台積電 ADR 換算 {fmt(tsm * twd / 5, 0)} 元，較台股收盤 {fmt((tsm * twd / 5 / tsmc - 1) * 100, 1, sign=True, pct=True)}"
    except Exception as e:
        print(f"ADR 換算略過：{e}")

    log["forecasts"] = [
        e
        for e in log["forecasts"]
        if not (e["kind"] == "morning" and e["base_date"] == base_date.isoformat())
    ]
    log["forecasts"].append(
        {
            "kind": "morning",
            "base_date": base_date.isoformat(),
            "h": 1,
            "base_close": round(base_close, 2),
            "q": qkey(q),
            "us_ret": us_ret,
        }
    )
    save_log(log)

    evening_mid = f"（昨晚預估中位 {fmt(ev[-1]['q']['0.5'], 0)}）" if ev else ""
    msg = (
        f"☀️ 台股早盤修正 {d:%m/%d}\n"
        f"{us_note}；{adr_note}\n"
        f"今日收盤 80% 區間：{fmt(q[0.1], 0)}～{fmt(q[0.9], 0)}\n"
        f"中位數 {fmt(q[0.5], 0)}{evening_mid}，昨收 {fmt(base_close, 0)}\n"
        f"燈號：{log['state'].get('status', '尚無')}\n"
        f"（費半解釋台股隔日漲跌約 {mf['r2'] * 100:.0f}%；近 {mbt['n']} 日回測 80% 區間命中 {mbt['cov80']:.0f}%）"
    )
    print(msg)
    if not args.no_send:
        from line_assistant.notify import notify

        if not notify(msg):
            raise SystemExit("LINE 推播失敗")


if __name__ == "__main__":
    main()
