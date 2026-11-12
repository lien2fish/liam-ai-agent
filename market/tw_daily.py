# -*- coding: utf-8 -*-
"""盤後日報與早盤修正共用的資料層與計算層。

原則：
- 台股數字以證交所官方為準，Yahoo 只補歷史與海外，且每個數字都帶日期。
- 抓不到就是 None，報告顯示「未公布／N/A」，不拿別天的數字頂替。
- 預測只用程式算的歷史分布，不用 AI。
"""
import json
import math
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

TW = timezone(timedelta(hours=8))
UA = {"User-Agent": "Mozilla/5.0"}
TWSE = "https://www.twse.com.tw/rwd/zh"
YF = "https://query1.finance.yahoo.com/v8/finance/chart"


def now_tw():
    return datetime.now(TW)


def _get_json(url, timeout=30, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(5 * (i + 1))


def _num(s):
    if s is None:
        return None
    s = str(s).replace(",", "").strip()
    if s in ("", "-", "--", "---"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _sign(html):
    return -1 if "-" in str(html) else 1


# ───────────── 證交所 ─────────────


def twse_day(d):
    """MI_INDEX type=ALL：加權指數、漲跌家數、成交值、全部個股收盤。非交易日回 None。"""
    ds = d.strftime("%Y%m%d")
    j = _get_json(f"{TWSE}/afterTrading/MI_INDEX?date={ds}&type=ALL&response=json")
    if j.get("stat") != "OK" or j.get("date") != ds:
        return None
    out = {"date": d.isoformat(), "stocks": {}}
    for t in j.get("tables", []):
        title = t.get("title") or ""
        rows = t.get("data") or []
        if title.endswith("價格指數(臺灣證券交易所)"):
            for r in rows:
                if r[0] == "發行量加權股價指數":
                    out["taiex"] = _num(r[1])
                    out["taiex_chg"] = _sign(r[2]) * (_num(r[3]) or 0)
                    out["taiex_pct"] = _num(r[4])
        elif title == "漲跌證券數合計":
            m = {r[0][:2]: r[2] for r in rows}  # 「股票」欄
            out["up"] = int(_num(m.get("上漲", "").split("(")[0]) or 0)
            out["down"] = int(_num(m.get("下跌", "").split("(")[0]) or 0)
            out["flat"] = int(_num(m.get("持平", "").split("(")[0]) or 0)
        elif title.endswith("大盤統計資訊"):
            for r in rows:
                if r[0].startswith("總計"):
                    out["turnover"] = _num(r[1])
        elif "每日收盤行情" in title:
            f = t["fields"]
            ic, ichg, isg = f.index("收盤價"), f.index("漲跌價差"), f.index("漲跌(+/-)")
            for r in rows:
                close = _num(r[ic])
                if close is None:
                    continue
                chg = _num(r[ichg]) or 0
                sg = -1 if "-" in r[isg] else (1 if "+" in r[isg] else 0)
                prev = close - sg * chg
                out["stocks"][r[0]] = {
                    "name": r[1],
                    "close": close,
                    "chg": sg * chg,
                    "pct": round(sg * chg / prev * 100, 2) if prev else None,
                }
    if out.get("taiex") is None:
        return None
    return out


def twse_institutional(d):
    """三大法人買賣超（元）。未公布回 None。"""
    ds = d.strftime("%Y%m%d")
    j = _get_json(f"{TWSE}/fund/BFI82U?dayDate={ds}&type=day&response=json")
    if j.get("stat") != "OK" or j.get("date") != ds:
        return None
    rows = {r[0]: _num(r[3]) for r in j.get("data", [])}
    foreign = sum(v or 0 for k, v in rows.items() if k.startswith("外資"))
    trust = rows.get("投信")
    dealer = sum(v or 0 for k, v in rows.items() if k.startswith("自營商"))
    return {
        "date": d.isoformat(),
        "foreign": foreign,
        "trust": trust,
        "dealer": dealer,
        "total": rows.get("合計"),
    }


def twse_margin(d):
    """融資餘額（仟元）。證交所約 21:00 才公布，未公布回 None。"""
    ds = d.strftime("%Y%m%d")
    j = _get_json(
        f"{TWSE}/marginTrading/MI_MARGN?date={ds}&selectType=MS&response=json"
    )
    if j.get("stat") != "OK" or j.get("date") != ds:
        return None
    for t in j.get("tables", []):
        for r in t.get("data") or []:
            if r[0].startswith("融資金額"):
                prev, today = _num(r[4]), _num(r[5])
                return {"date": d.isoformat(), "balance": today, "change": today - prev}
    return None


def twse_valuation(d):
    """BWIBBU_d：個股本益比／殖利率／股價淨值比。"""
    ds = d.strftime("%Y%m%d")
    j = _get_json(
        f"{TWSE}/afterTrading/BWIBBU_d?date={ds}&selectType=ALL&response=json"
    )
    if j.get("stat") != "OK" or j.get("date") != ds:
        return {}
    f = j["fields"]
    ipe, iy, ipb = f.index("本益比"), f.index("殖利率(%)"), f.index("股價淨值比")
    return {
        r[0]: {"pe": _num(r[ipe]), "yield": _num(r[iy]), "pb": _num(r[ipb])}
        for r in j.get("data", [])
    }


def recent_trading_days(end, n, fetch):
    """往回找 n 個有資料的交易日（含 end），每次呼叫間隔避免被證交所限流。"""
    out, d = [], end
    while len(out) < n and (end - d).days < n * 3 + 10:
        if d.weekday() < 5:
            r = fetch(d)
            time.sleep(2.5)
            if r:
                out.append(r)
        d -= timedelta(days=1)
    return out


# ───────────── Yahoo（歷史與海外） ─────────────


def yf_daily(symbol, years=6):
    """日線收盤 [(date, close)]，用 period1/period2（range=max 會變月線）。"""
    p2 = int(time.time()) + 86400
    p1 = p2 - int(years * 365.25 * 86400)
    url = f"{YF}/{urllib.parse.quote(symbol)}?interval=1d&period1={p1}&period2={p2}"
    j = _get_json(url)
    res = j["chart"]["result"][0]
    tz = res["meta"].get("gmtoffset", 0)
    closes = res["indicators"]["quote"][0]["close"]
    out = {}
    for ts, c in zip(res.get("timestamp", []), closes):
        if c is None:
            continue
        out[datetime.fromtimestamp(ts + tz, timezone.utc).date()] = c
    return sorted(out.items())


def merge_today(series, d, close):
    """把官方收盤接到 Yahoo 歷史尾端（Yahoo 常延遲或給盤中價）。"""
    s = [(k, v) for k, v in series if k < d]
    s.append((d, close))
    return s


# ───────────── 指標 ─────────────


def sma(vals, n):
    return sum(vals[-n:]) / n if len(vals) >= n else None


def rsi(vals, n=14):
    if len(vals) < n + 1:
        return None
    gains = losses = 0.0
    for a, b in zip(vals[-n - 1 : -1], vals[-n:]):
        diff = b - a
        gains += max(diff, 0)
        losses += max(-diff, 0)
    if losses == 0:
        return 100.0
    rs = gains / losses
    return 100 - 100 / (1 + rs)


def log_returns(series):
    return [
        (series[i][0], math.log(series[i][1] / series[i - 1][1]))
        for i in range(1, len(series))
    ]


def ann_vol(series, n=60):
    r = [x for _, x in log_returns(series)[-n:]]
    if len(r) < n:
        return None
    m = sum(r) / n
    return math.sqrt(sum((x - m) ** 2 for x in r) / (n - 1)) * math.sqrt(252) * 100


def beta(series, bench, n=120):
    """按日期對齊後算 Beta；共同樣本不足 n 筆回 None。"""
    b = dict(log_returns(bench))
    pairs = [(x, b[d]) for d, x in log_returns(series) if d in b][-n:]
    if len(pairs) < n:
        return None
    xs, ys = [p[1] for p in pairs], [p[0] for p in pairs]
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    var = sum((x - mx) ** 2 for x in xs)
    return cov / var if var else None


def stock_metrics(series, bench):
    closes = [c for _, c in series]
    hi = max(closes[-252:]) if len(closes) >= 252 else None
    return {
        "ma20": sma(closes, 20),
        "ma60": sma(closes, 60),
        "ma240": sma(closes, 240),
        "rsi": rsi(closes),
        "vol60": ann_vol(series),
        "beta": beta(series, bench),
        "from_high": (closes[-1] / hi - 1) * 100 if hi else None,
    }


def streak(closes, ma_n, above):
    """最近連續幾天收在 ma_n 日均線之上（above=True）或之下。"""
    k = 0
    for i in range(len(closes) - 1, ma_n - 2, -1):
        m = sum(closes[i - ma_n + 1 : i + 1]) / ma_n
        if (closes[i] > m) == above:
            k += 1
        else:
            break
    return k


# ───────────── 預測：波動調整後的歷史分布 ─────────────

LAMBDA = 0.94
QS = (0.10, 0.25, 0.50, 0.75, 0.90)


def ewma_sigmas(rets):
    """sig[i]＝在第 i 天收盤前就能知道的波動估計（只用 i 之前的報酬）。"""
    var = sum(r * r for r in rets[:20]) / 20
    sig = []
    for i, r in enumerate(rets):
        sig.append(math.sqrt(var) if i >= 20 else 0.0)  # 前 20 筆的初值用到了它們自己，標 0 讓下游跳過
        var = LAMBDA * var + (1 - LAMBDA) * r * r
    return sig, math.sqrt(var)  # 後者＝下一個交易日的波動估計


def quantile(xs, q):
    s = sorted(xs)
    pos = (len(s) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def standardized(rets, sig, h):
    """h 日累積報酬除以起點的 σ·√h。"""
    return [
        sum(rets[i : i + h]) / (sig[i] * math.sqrt(h))
        for i in range(len(rets) - h + 1)
        if sig[i] > 0
    ]


def forecast(series, h, window=1250):
    """回傳 h 個交易日後收盤的分位數（價格）。"""
    rets = [x for _, x in log_returns(series)]
    sig, sig_next = ewma_sigmas(rets)
    z = standardized(rets, sig, h)[-window:]
    base = series[-1][1]
    return {
        "q": {q: base * math.exp(quantile(z, q) * sig_next * math.sqrt(h)) for q in QS},
        "sigma_daily_pct": sig_next * 100,
        "n": len(z),
    }


def backtest_coverage(series, h, days=500, window=1250):
    """逐日向前驗證：每一天只用當時以前的資料，看 50%／80% 區間的實際涵蓋率。"""
    rets = [x for _, x in log_returns(series)]
    sig, _ = ewma_sigmas(rets)
    hit50 = hit80 = n = 0
    start = max(len(rets) - days - h, window + h)
    for t in range(start, len(rets) - h + 1):
        z = standardized(rets[:t], sig[:t], h)[-window:]
        if len(z) < 250:
            continue
        s = sig[t] * math.sqrt(h)
        actual = sum(rets[t : t + h])
        q = {k: quantile(z, k) * s for k in QS}
        hit50 += q[0.25] <= actual <= q[0.75]
        hit80 += q[0.10] <= actual <= q[0.90]
        n += 1
    return {
        "n": n,
        "cov50": hit50 / n * 100 if n else None,
        "cov80": hit80 / n * 100 if n else None,
    }


def overnight_model(tw_series, us_series, years=2):
    """台股當日報酬 vs 前一個美股交易日報酬的迴歸（按日期對齊，美股日期必須早於台股日期）。"""
    tw = log_returns(tw_series)
    us = log_returns(us_series)
    cut = tw[-1][0] - timedelta(days=int(365 * years))
    pairs, j = [], 0
    for d, y in tw:
        while j + 1 < len(us) and us[j + 1][0] < d:
            j += 1
        if us[j][0] < d and (d - us[j][0]).days <= 4 and d >= cut:
            pairs.append((us[j][1], y))
    n = len(pairs)
    xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
    mx, my = sum(xs) / n, sum(ys) / n
    b = sum((x - mx) * (y - my) for x, y in pairs) / sum((x - mx) ** 2 for x in xs)
    a = my - b * mx
    resid = [y - a - b * x for x, y in pairs]
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1 - sum(e * e for e in resid) / ss_tot
    return {"a": a, "b": b, "r2": r2, "resid": resid, "n": n}


def morning_forecast(tw_series, us_series, us_ret):
    """以昨夜美股報酬修正今日收盤分布：中心＝a＋b·美股報酬，寬度＝殘差先除以自身 EWMA 波動取分布、再乘目前殘差波動。

    2026-11-12 回測近 250 日：原本用「指數波動比」縮放殘差，80% 區間只命中 71.6%（太自信）；
    改用殘差自身的 EWMA 後 77.6%，與晚報的 76.4% 相當且區間較窄。
    """
    m = overnight_model(tw_series, us_series)
    sig, sig_next = ewma_sigmas(m["resid"])
    z = [e / s for e, s in zip(m["resid"], sig) if s > 0]
    base = tw_series[-1][1]
    center = m["a"] + m["b"] * us_ret
    q = {k: base * math.exp(center + quantile(z, k) * sig_next) for k in QS}
    return {"q": q, "beta": m["b"], "r2": m["r2"], "n": m["n"], "resid_sd_pct": sig_next * 100}


def morning_backtest(tw_series, us_series, days=250):
    """逐日向前驗證早盤修正：每一天只用當時以前的台股與美股資料。"""
    ud = [k for k, _ in us_series]
    h50 = h80 = n = 0
    for t in range(len(tw_series) - days, len(tw_series)):
        d = tw_series[t][0]
        js = [i for i, k in enumerate(ud) if k < d]
        if len(js) < 2 or (d - ud[js[-1]]).days > 4:
            continue
        j = js[-1]
        r = math.log(us_series[j][1] / us_series[j - 1][1])
        q = morning_forecast(tw_series[:t], us_series[: j + 1], r)["q"]
        a = tw_series[t][1]
        h50 += q[0.25] <= a <= q[0.75]
        h80 += q[0.1] <= a <= q[0.9]
        n += 1
    return {"n": n, "cov50": h50 / n * 100 if n else None, "cov80": h80 / n * 100 if n else None}


# ───────────── 預測紀錄與結算 ─────────────


def settle(log, trading_days, closes):
    """到期的預測補上實際收盤與是否落在區間內。trading_days 為排序後的日期字串清單。"""
    idx = {d: i for i, d in enumerate(trading_days)}
    for e in log["forecasts"]:
        if "actual" in e or e["base_date"] not in idx:
            continue
        i = idx[e["base_date"]] + e["h"]
        if i >= len(trading_days):
            continue
        tgt = trading_days[i]
        a = closes[tgt]
        q = e["q"]
        e.update(
            target_date=tgt,
            actual=a,
            hit50=q["0.25"] <= a <= q["0.75"],
            hit80=q["0.1"] <= a <= q["0.9"],
        )


def scorecard(log, kind, h, last=60):
    done = [
        e
        for e in log["forecasts"]
        if e["kind"] == kind and e["h"] == h and "actual" in e
    ][-last:]
    if not done:
        return None
    n = len(done)
    return {
        "n": n,
        "cov50": sum(e["hit50"] for e in done) / n * 100,
        "cov80": sum(e["hit80"] for e in done) / n * 100,
        "width80": sum(
            (e["q"]["0.9"] - e["q"]["0.1"]) / e["base_close"] * 100 for e in done
        )
        / n,
    }


def qkey(q):
    return {str(k): round(v, 2) for k, v in q.items()}


def fmt(v, nd=2, pct=False, sign=False):
    if v is None:
        return "N/A"
    s = f"{v:+,.{nd}f}" if sign else f"{v:,.{nd}f}"
    return s + ("%" if pct else "")


def yi(v):
    """元 → 億元。"""
    return None if v is None else v / 1e8
