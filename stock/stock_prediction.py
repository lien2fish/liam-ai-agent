#!/usr/bin/env python3
"""
台股市場分析與預測系統
每日執行，抓取技術指標與總體經濟數據，透過 Gemini AI 生成預測報告
"""

import json, os, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

# ── 路徑與環境 ────────────────────────────────────────────────────
WORKSPACE    = Path(os.environ.get('GITHUB_WORKSPACE', Path(__file__).parent.parent))
REPORT_DIR   = WORKSPACE / 'reports' / 'stock'
CONFIG_FILE  = WORKSPACE / 'finance' / 'finance_config.json'
GEMINI_KEY   = os.environ.get('GEMINI_KEY', '')

GEMINI_MODELS = ['gemini-2.5-flash', 'gemini-2.0-flash']

YAHOO_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
    ),
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
}

# 市場代號
SYMBOLS = {
    'taiex':   '^TWII',
    'tsmc':    '2330.TW',
    'sp500':   '^GSPC',
    'nasdaq':  '^IXIC',
    'vix':     '^VIX',
    'usdtwd':  'TWD=X',
    'wti':     'CL=F',
    'gold':    'GC=F',
}

# ── 工具函式 ──────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def fmt(v, d=2):
    return f"{v:.{d}f}" if v is not None else 'N/A'


def fmt_pct(v):
    if v is None:
        return 'N/A'
    arrow = '↑' if v > 0 else '↓' if v < 0 else '→'
    return f"{arrow} {v:+.2f}%"


# ── 數據抓取 ──────────────────────────────────────────────────────

def fetch_yahoo(symbol, days=90):
    """抓取 Yahoo Finance OHLCV，回傳含 closes/highs/lows/volumes/price/prev_close 的 dict"""
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{urllib.parse.quote(symbol)}"
        f"?range={days}d&interval=1d&includePrePost=false"
    )
    req = urllib.request.Request(url, headers=YAHOO_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        result = data['chart']['result'][0]
        meta   = result['meta']
        quote  = result['indicators']['quote'][0]

        def clean(lst):
            return [x for x in (lst or []) if x is not None]

        closes  = clean(quote.get('close',  []))
        highs   = clean(quote.get('high',   []))
        lows    = clean(quote.get('low',    []))
        volumes = clean(quote.get('volume', []))

        price      = meta.get('regularMarketPrice') or (closes[-1] if closes else None)
        prev_close = meta.get('previousClose')      or (closes[-2] if len(closes) >= 2 else None)
        return {
            'closes': closes, 'highs': highs, 'lows': lows, 'volumes': volumes,
            'price': price, 'prev_close': prev_close,
        }
    except Exception as e:
        log(f"  ⚠ {symbol} 抓取失敗：{e}")
        return {'closes': [], 'highs': [], 'lows': [], 'volumes': [], 'price': None, 'prev_close': None}


def change_pct(price, prev_close):
    if price and prev_close and prev_close != 0:
        return (price - prev_close) / prev_close * 100
    return None


def fetch_export_yoy():
    """嘗試抓取台灣最新出口年增率，失敗回傳 None"""
    # 財政部關務署 Open Data — 各月出口統計
    url = 'https://service.mof.gov.tw/public/fileSource/FSDB/stat_files/MBF004A.json'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        if isinstance(data, list) and data:
            latest = data[-1]
            for key in ('年增率', 'yoy', 'YOY', 'export_yoy', '出口年增率'):
                if key in latest:
                    return str(latest[key])
    except Exception:
        pass
    return None


def load_positions():
    """讀取 finance_config.json 中的股票持倉"""
    try:
        cfg = json.loads(CONFIG_FILE.read_text())
        return cfg.get('stocks', [])
    except Exception:
        return []


# ── 技術指標 ──────────────────────────────────────────────────────

def calc_ma(closes, period):
    if len(closes) < period:
        return None
    return mean(closes[-period:])


def calc_ema_series(closes, period):
    """計算完整 EMA 序列，回傳 list（長度 = len(closes) - period + 1）"""
    if len(closes) < period:
        return []
    k   = 2 / (period + 1)
    ema = [mean(closes[:period])]
    for price in closes[period:]:
        ema.append(price * k + ema[-1] * (1 - k))
    return ema


def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains  = [max(closes[i] - closes[i-1], 0) for i in range(1, len(closes))]
    losses = [max(closes[i-1] - closes[i], 0) for i in range(1, len(closes))]
    avg_g  = mean(gains[-period:])
    avg_l  = mean(losses[-period:])
    if avg_l == 0:
        return 100.0
    return 100 - 100 / (1 + avg_g / avg_l)


def calc_macd(closes):
    """回傳 (macd_line, signal_line, histogram) 最新值"""
    e12 = calc_ema_series(closes, 12)
    e26 = calc_ema_series(closes, 26)
    if not e12 or not e26:
        return None, None, None
    # EMA12 比 EMA26 多 14 個值，對齊到最後 len(e26) 個
    offset      = len(e12) - len(e26)
    macd_series = [e12[offset + i] - e26[i] for i in range(len(e26))]
    if len(macd_series) < 9:
        return macd_series[-1], None, None
    signal_series = calc_ema_series(macd_series, 9)
    if not signal_series:
        return macd_series[-1], None, None
    macd_val   = macd_series[-1]
    signal_val = signal_series[-1]
    return macd_val, signal_val, macd_val - signal_val


def calc_kd(highs, lows, closes, n=9):
    """計算 KD 隨機指標，回傳最新 (K, D)"""
    if len(closes) < n:
        return None, None
    k_prev, d_prev = 50.0, 50.0
    for i in range(n - 1, len(closes)):
        h   = max(highs[i - n + 1: i + 1])
        l   = min(lows[i - n + 1: i + 1])
        rsv = (closes[i] - l) / (h - l) * 100 if h != l else 50
        k   = k_prev * (2/3) + rsv * (1/3)
        d   = d_prev * (2/3) + k   * (1/3)
        k_prev, d_prev = k, d
    return k_prev, d_prev


def calc_volume_ratio(volumes):
    """今日成交量 vs 近 5 日均量"""
    if len(volumes) < 6:
        return None
    avg5 = mean(volumes[-6:-1])
    return volumes[-1] / avg5 if avg5 else None


# ── 訊號文字 ──────────────────────────────────────────────────────

def price_vs_ma_signal(price, ma):
    if price is None or ma is None:
        return '─'
    return '✅ 站上' if price > ma else '⚠️ 跌破'


def rsi_signal(rsi):
    if rsi is None:  return '─'
    if rsi > 70:     return '⚠️ 超買'
    if rsi < 30:     return '✅ 超賣（可留意反彈）'
    if rsi > 55:     return '偏多'
    if rsi < 45:     return '偏空'
    return '中性'


def macd_signal(hist):
    if hist is None: return '─'
    if hist >  10:   return '✅ 多頭擴張'
    if hist >  0:    return '多頭'
    if hist < -10:   return '⚠️ 空頭擴張'
    return '空頭'


def kd_signal(k, d):
    if k is None or d is None: return '─'
    return '✅ K>D 多頭' if k > d else '⚠️ K<D 空頭'


def vol_signal(ratio):
    if ratio is None: return '─'
    if ratio > 1.5:  return '✅ 明顯放量'
    if ratio > 1.1:  return '放量'
    if ratio < 0.7:  return '⚠️ 明顯縮量'
    return '量能正常'


def vix_signal(vix):
    if vix is None:  return '─'
    if vix > 30:     return '⚠️ 市場恐慌'
    if vix > 20:     return '警戒區間'
    return '✅ 市場平靜'


def usdtwd_signal(chg):
    if chg is None:   return '─'
    if chg < -0.3:    return '✅ 台幣升值（外資偏正面）'
    if chg >  0.3:    return '⚠️ 台幣貶值'
    return '匯率穩定'


# ── Gemini AI 分析 ────────────────────────────────────────────────

def build_prompt(indicators, positions_data, date_str):
    t     = indicators['taiex']
    macro = indicators['macro']

    pos_text = ''
    if positions_data:
        lines = '\n'.join(
            f"  - {p['name']}：均成本 {fmt(p['avg_cost'])} 元，最新 {fmt(p['current'])} 元，損益 {p['pnl_pct']}"
            for p in positions_data
        )
        pos_text = f"\n\n【用戶現有持倉】\n{lines}\n（請針對這兩檔提供簡短操作建議）"

    return f"""你是一位資深台灣股市分析師，擅長整合技術面與總體經濟面進行研判。
今天日期：{date_str}

請根據以下數據，用繁體中文撰寫 250-350 字的台股分析報告，內容需包含：
1. 明確預測走勢方向（標明「上漲」、「下跌」或「盤整」三選一）
2. 3-5 個具體支撐理由（結合技術面與外部環境）
3. 近期需關注的關鍵事件或風險因素
4. 給投資人的一句提醒語{pos_text}

【台灣加權指數技術面】
- 指數收盤：{fmt(t['price'], 0)}（{fmt_pct(t['change_pct'])}）
- 均線：MA5={fmt(t['ma5'])}  MA20={fmt(t['ma20'])}  MA60={fmt(t['ma60'])}
- RSI(14)：{fmt(t['rsi'])}
- MACD 值：{fmt(t['macd'])}，Signal：{fmt(t['signal'])}，柱體：{fmt(t['macd_hist'])}
- KD：K={fmt(t['k'], 1)}  D={fmt(t['d'], 1)}
- 量比（今日 vs 5日均量）：{fmt(t['vol_ratio'], 2)}x

【外部環境（前一交易日）】
- 美股：S&P500 {fmt(macro['sp500_price'], 0)}（{fmt_pct(macro['sp500_chg'])}）  NASDAQ {fmt(macro['nasdaq_price'], 0)}（{fmt_pct(macro['nasdaq_chg'])}）
- VIX：{fmt(macro['vix'])}
- USD/TWD：{fmt(macro['usdtwd'])}（{fmt_pct(macro['usdtwd_chg'])}）
- WTI 原油：${fmt(macro['wti'])}（{fmt_pct(macro['wti_chg'])}）
- 黃金：${fmt(macro['gold'], 0)}（{fmt_pct(macro['gold_chg'])}）
- 台積電：{fmt(indicators.get('tsmc_price'))} 元（{fmt_pct(indicators.get('tsmc_chg'))}）
- 台灣出口年增率（最新月）：{macro.get('export_yoy', '暫無最新資料')}

注意：分析要具體且有見解，不要單純羅列數據。"""


def call_gemini(prompt):
    for model in GEMINI_MODELS:
        is_thinking = any(x in model for x in ['3.5', '3.1', '3-', '2.5'])
        config = {'maxOutputTokens': 1024, 'temperature': 0.7}
        if is_thinking:
            config['thinkingConfig'] = {'thinkingBudget': 0}

        payload = json.dumps({
            'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': config,
        }).encode()

        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model}:generateContent?key={GEMINI_KEY}")
        req = urllib.request.Request(
            url, data=payload,
            headers={'Content-Type': 'application/json'}, method='POST'
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read())
            candidate = data['candidates'][0]
            text = candidate['content']['parts'][0]['text'].strip()
            if candidate.get('finishReason') == 'MAX_TOKENS' or len(text) < 30:
                log(f"  {model} 輸出不完整，切換下一模型")
                continue
            return text
        except urllib.request.HTTPError as e:
            if e.code in (429, 503):
                log(f"  {model} 失敗（{e.code}），切換下一模型")
                continue
            raise
    return "（AI 分析暫時無法使用，請稍後再試）"


# ── 報告產生 ──────────────────────────────────────────────────────

def extract_prediction(ai_text):
    if '上漲' in ai_text or '看多' in ai_text or '偏多' in ai_text or '偏強' in ai_text:
        return '↑ 上漲'
    if '下跌' in ai_text or '看空' in ai_text or '偏空' in ai_text or '偏弱' in ai_text:
        return '↓ 下跌'
    return '→ 盤整'


def generate_report(date_str, indicators, positions_data, ai_text):
    weekday_zh = {0:'一', 1:'二', 2:'三', 3:'四', 4:'五', 5:'六', 6:'日'}
    weekday    = weekday_zh[datetime.strptime(date_str, '%Y-%m-%d').weekday()]
    t          = indicators['taiex']
    macro      = indicators['macro']
    prediction = extract_prediction(ai_text)

    lines = [
        f"# 台股市場分析報告 — {date_str}（週{weekday}）",
        "",
        "## 預測結論",
        "",
        f"**今日走勢預測：{prediction}**",
        "",
        "---",
        "",
        "## 台灣加權指數技術面",
        "",
        "| 指標 | 數值 | 訊號 |",
        "|------|------|------|",
        f"| 加權指數 | {fmt(t['price'], 0)} | {fmt_pct(t['change_pct'])} |",
        f"| MA5 | {fmt(t['ma5'])} | {price_vs_ma_signal(t['price'], t['ma5'])} |",
        f"| MA20 | {fmt(t['ma20'])} | {price_vs_ma_signal(t['price'], t['ma20'])} |",
        f"| MA60 | {fmt(t['ma60'])} | {price_vs_ma_signal(t['price'], t['ma60'])} |",
        f"| RSI(14) | {fmt(t['rsi'])} | {rsi_signal(t['rsi'])} |",
        f"| MACD | {fmt(t['macd'])}（柱：{fmt(t['macd_hist'])}）| {macd_signal(t['macd_hist'])} |",
        f"| KD | K={fmt(t['k'], 1)}  D={fmt(t['d'], 1)} | {kd_signal(t['k'], t['d'])} |",
        f"| 量比 | {fmt(t['vol_ratio'], 2)}x | {vol_signal(t['vol_ratio'])} |",
        "",
        "---",
        "",
        "## 總體經濟環境",
        "",
        "| 指標 | 數值 | 方向 |",
        "|------|------|------|",
        f"| S&P500 | {fmt(macro['sp500_price'], 0)} | {fmt_pct(macro['sp500_chg'])} |",
        f"| NASDAQ | {fmt(macro['nasdaq_price'], 0)} | {fmt_pct(macro['nasdaq_chg'])} |",
        f"| VIX 恐慌指數 | {fmt(macro['vix'])} | {vix_signal(macro['vix'])} |",
        f"| USD/TWD | {fmt(macro['usdtwd'])} | {usdtwd_signal(macro['usdtwd_chg'])} |",
        f"| WTI 原油 | ${fmt(macro['wti'])} | {fmt_pct(macro['wti_chg'])} |",
        f"| 黃金 | ${fmt(macro['gold'], 0)} | {fmt_pct(macro['gold_chg'])} |",
        f"| 台積電 | {fmt(indicators.get('tsmc_price'))} | {fmt_pct(indicators.get('tsmc_chg'))} |",
        f"| 台灣出口年增率 | {macro.get('export_yoy', '─')} | ─ |",
        "",
        "---",
        "",
    ]

    if positions_data:
        lines += [
            "## 持倉損益參考",
            "",
            "| 持股 | 最新收盤 | 均成本 | 損益% |",
            "|------|---------|--------|-------|",
        ]
        for pos in positions_data:
            lines.append(f"| {pos['name']} | {fmt(pos['current'])} | {fmt(pos['avg_cost'])} | {pos['pnl_pct']} |")
        lines += ["", "---", ""]

    lines += [
        "## AI 綜合判斷",
        "",
        ai_text,
        "",
        "---",
        "",
        "> ⚠️ **風險提示**：本報告為 AI 輔助分析，僅供參考，不構成任何投資建議。股市有風險，投資決策需謹慎評估。",
        f">",
        f"> 報告生成時間：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
    ]

    return '\n'.join(lines)


# ── 主流程 ────────────────────────────────────────────────────────

def main():
    date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    log(f"=== 台股市場分析系統啟動 — {date_str} ===")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 抓取所有市場數據
    log("【步驟 1】抓取市場數據…")
    market = {}
    for key, symbol in SYMBOLS.items():
        log(f"  {symbol}…")
        market[key] = fetch_yahoo(symbol)

    # 2. 計算 TAIEX 技術指標
    log("【步驟 2】計算技術指標…")
    closes  = market['taiex']['closes']
    highs   = market['taiex']['highs']
    lows    = market['taiex']['lows']
    volumes = market['taiex']['volumes']

    macd_line, signal_line, macd_hist = calc_macd(closes)
    k_val, d_val = calc_kd(highs, lows, closes)

    taiex_indicators = {
        'price':      market['taiex']['price'],
        'change_pct': change_pct(market['taiex']['price'], market['taiex']['prev_close']),
        'ma5':        calc_ma(closes, 5),
        'ma20':       calc_ma(closes, 20),
        'ma60':       calc_ma(closes, 60),
        'rsi':        calc_rsi(closes),
        'macd':       macd_line,
        'signal':     signal_line,
        'macd_hist':  macd_hist,
        'k':          k_val,
        'd':          d_val,
        'vol_ratio':  calc_volume_ratio(volumes),
    }

    indicators = {
        'taiex': taiex_indicators,
        'tsmc_price': market['tsmc']['price'],
        'tsmc_chg':   change_pct(market['tsmc']['price'], market['tsmc']['prev_close']),
        'macro': {
            'sp500_price':  market['sp500']['price'],
            'sp500_chg':    change_pct(market['sp500']['price'],  market['sp500']['prev_close']),
            'nasdaq_price': market['nasdaq']['price'],
            'nasdaq_chg':   change_pct(market['nasdaq']['price'], market['nasdaq']['prev_close']),
            'vix':          market['vix']['price'],
            'usdtwd':       market['usdtwd']['price'],
            'usdtwd_chg':   change_pct(market['usdtwd']['price'], market['usdtwd']['prev_close']),
            'wti':          market['wti']['price'],
            'wti_chg':      change_pct(market['wti']['price'],    market['wti']['prev_close']),
            'gold':         market['gold']['price'],
            'gold_chg':     change_pct(market['gold']['price'],   market['gold']['prev_close']),
        },
    }

    # 3. 台灣出口統計（選填，失敗不中斷）
    log("【步驟 3】嘗試取得台灣出口統計…")
    export_yoy = fetch_export_yoy()
    if export_yoy:
        indicators['macro']['export_yoy'] = export_yoy
        log(f"  出口年增率：{export_yoy}")
    else:
        log("  暫無法取得，略過")

    # 4. 持倉損益計算
    log("【步驟 4】計算持倉損益…")
    positions = load_positions()
    positions_data = []
    for pos in positions:
        symbol_tw = pos['code'] + '.TW'
        data      = fetch_yahoo(symbol_tw, days=10)
        current   = data['price']
        if current and pos['avg_cost']:
            pnl = (current - pos['avg_cost']) / pos['avg_cost'] * 100
            pnl_str = f"{pnl:+.1f}%"
        else:
            pnl_str = 'N/A'
        positions_data.append({
            'name':     pos['name'],
            'avg_cost': pos['avg_cost'],
            'current':  current,
            'pnl_pct':  pnl_str,
        })
        log(f"  {pos['name']}：{fmt(current)} 元（損益 {pnl_str}）")

    # 5. Gemini AI 分析
    log("【步驟 5】Gemini AI 分析…")
    if not GEMINI_KEY:
        ai_text = "（GEMINI_KEY 未設定，AI 分析略過）"
        log("  ⚠ GEMINI_KEY 未設定")
    else:
        prompt  = build_prompt(indicators, positions_data, date_str)
        ai_text = call_gemini(prompt)
        log(f"  完成（{len(ai_text)} 字）")

    # 6. 產出報告
    log("【步驟 6】產出報告…")
    report      = generate_report(date_str, indicators, positions_data, ai_text)
    report_path = REPORT_DIR / f"{date_str}.md"
    report_path.write_text(report, encoding='utf-8')
    log(f"  已儲存：{report_path}")

    # 印出預測結論
    prediction = extract_prediction(ai_text)
    log(f"=== 完成！預測：{prediction} ===")


if __name__ == '__main__':
    main()
