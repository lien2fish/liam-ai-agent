#!/usr/bin/env python3
"""
每日財金日報：台股、美股、美債利率、匯率、黃金與原物料的走勢，
加上 AI 的中長期資產配置比例與波段訊號。
輸出：Notion 頁面＋reports/ Markdown＋day/ PDF（Email 由 market/send_report.py 寄出）。
資料來源：
  Layer 1 — Yahoo Finance 一年日線（走勢與均線自己算，不靠 AI）
  Layer 2 — Gemini + Google Search grounding（新聞、事件、配置判斷）
  Layer 3 — Gemini 知識庫分析（備援）
"""

import json
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

# ── 路徑與設定 ────────────────────────────────────────────────────
WORKSPACE = Path(
    os.environ.get("GITHUB_WORKSPACE", "/Users/lien/Downloads/Liam AI agent")
)
CONFIG_FILE = WORKSPACE / "market/market_config.json"
HISTORY_FILE = WORKSPACE / "market/market_history.json"
ALLOC_FILE = WORKSPACE / "market/allocation_history.json"
REPORTS_DIR = WORKSPACE / "reports"
PDF_DIR = WORKSPACE / "day"

NOTION_VER = "2022-06-28"
NOTION_API = "https://api.notion.com/v1"
YF_CHART = "https://query1.finance.yahoo.com/v8/finance/chart"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

GEMINI_KEY = os.environ.get("GEMINI_KEY", "")

ASSET_CLASSES = ["台股", "美股", "美債", "黃金", "原物料", "現金"]
SECTIONS = ["台股", "美股", "美債與利率", "匯率", "黃金與原物料"]


# ── Token ────────────────────────────────────────────────────────
def _load_token():
    t = os.environ.get("NOTION_TOKEN", "")
    if t:
        return t
    try:
        sys.path.insert(0, str(WORKSPACE / "notion_crm"))
        import config as c

        return c.NOTION_TOKEN
    except Exception:
        return ""


NOTION_TOKEN = _load_token()


# ── 工具函式 ──────────────────────────────────────────────────────
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def notion_req(method, path, body=None):
    url = f"{NOTION_API}/{path}"
    data = json.dumps(body, ensure_ascii=False).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {NOTION_TOKEN}",
            "Notion-Version": NOTION_VER,
            "Content-Type": "application/json",
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def gemini_call(payload, retries=3):
    data = json.dumps(payload).encode()
    for attempt in range(retries):
        req = urllib.request.Request(
            f"{GEMINI_URL}?key={GEMINI_KEY}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = 60 * (attempt + 1)
                log(f"  Gemini 429，等 {wait}s 後重試...")
                time.sleep(wait)
            else:
                raise
    return {}


def extract_json_obj(text):
    text = text.replace("```json", "").replace("```", "").strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        return {}
    try:
        return json.loads(text[start:end])
    except Exception:
        return {}


def clean(text):
    # md_to_pdf 把內文丟進 reportlab Paragraph（迷你 XML），裸的 < & 會讓整份 PDF 建不出來
    return (
        str(text)
        .replace("&", "＆")
        .replace("<", "＜")
        .replace(">", "＞")
        .replace("|", "／")
        .replace("\n", " ")
        .strip()
    )


# ── Yahoo Finance：一年日線＋自算走勢 ─────────────────────────────
def fetch_closes(symbol):
    encoded = urllib.parse.quote(symbol, safe=".=")
    url = f"{YF_CHART}/{encoded}?interval=1d&range=1y"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    res = data["chart"]["result"][0]
    ts = res.get("timestamp") or []
    closes = res["indicators"]["quote"][0].get("close") or []
    series = [(t, c) for t, c in zip(ts, closes) if c is not None]
    live = res["meta"].get("regularMarketPrice")
    live_ts = res["meta"].get("regularMarketTime", 0)
    if live is not None and series and live_ts > series[-1][0]:
        series.append((live_ts, live))
    elif live is not None and series:
        series[-1] = (series[-1][0], live)
    return series


def _pct(now, then):
    return (now - then) / then * 100 if then else None


def compute_stats(series, kind):
    closes = [c for _, c in series]
    price = closes[-1]

    def back(n):
        return closes[-1 - n] if len(closes) > n else None

    def diff(then):
        if then is None:
            return None
        return (price - then) * 100 if kind == "yield" else _pct(price, then)

    ma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
    ma200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else None
    hi, lo = max(closes), min(closes)

    if ma50 and ma200:
        if price > ma50 > ma200:
            trend = "上升"
        elif price < ma50 < ma200:
            trend = "下降"
        else:
            trend = "盤整"
    elif ma50:
        trend = "上升" if price > ma50 else "下降"
    else:
        trend = "—"

    return {
        "price": price,
        "d1": diff(back(1)),
        "w1": diff(back(5)),
        "m1": diff(back(21)),
        "m3": diff(back(63)),
        "ma50": ma50,
        "ma200": ma200,
        "hi": hi,
        "lo": lo,
        "from_hi": _pct(price, hi),
        "trend": trend,
        "ts": series[-1][0],
    }


def fetch_all_market_data(cfg):
    groups = []
    for g in cfg["groups"]:
        log(f"抓取{g['title']}...")
        rows = []
        for it in g["items"]:
            row = {
                "code": it["code"],
                "name": it["name"],
                "kind": it.get("kind", "price"),
                "dec": it.get("dec", 2),
                "price": None,
            }
            try:
                series = fetch_closes(it["code"])
                if series:
                    row.update(compute_stats(series, row["kind"]))
            except Exception as e:
                log(f"  YF {it['code']} 失敗：{e}")
            rows.append(row)
            time.sleep(0.3)
        groups.append({"title": g["title"], "rows": rows})

    valid = sum(1 for g in groups for r in g["rows"] if r["price"] is not None)
    total = sum(len(g["rows"]) for g in groups)
    log(f"  有效 {valid}/{total} 筆")
    return groups


def find(groups, code):
    return next((r for g in groups for r in g["rows"] if r["code"] == code), None)


def yield_curve(groups):
    """10 年減 3 個月利差（bp）。倒掛是景氣衰退的領先訊號。"""
    t10, t3m = find(groups, "^TNX"), find(groups, "^IRX")
    if not (t10 and t3m and t10["price"] is not None and t3m["price"] is not None):
        return None
    return round((t10["price"] - t3m["price"]) * 100)


# ── 格式化 ────────────────────────────────────────────────────────
def _chg(v, kind):
    if v is None:
        return "—"
    if kind == "yield":
        return f"{v:+.0f}bp"
    return f"{v:+.2f}%"


def fmt_row(r):
    if r["price"] is None:
        return [r["name"], "—", "—", "—", "—", "—", "—"]
    k = r["kind"]
    return [
        r["name"],
        f"{r['price']:,.{r['dec']}f}",
        _chg(r.get("d1"), k),
        _chg(r.get("w1"), k),
        _chg(r.get("m1"), k),
        _chg(r.get("m3"), k),
        r.get("trend", "—"),
    ]


TABLE_HEAD = ["項目", "現值", "日", "週", "月", "3個月", "趨勢"]


def market_summary_str(groups):
    lines = []
    for g in groups:
        lines.append(f"【{g['title']}】")
        for r in g["rows"]:
            if r["price"] is None:
                lines.append(f"  {r['name']}: 無資料")
                continue
            k, dec = r["kind"], r["dec"]
            ma = []
            if r.get("ma50"):
                ma.append(f"50日均 {r['ma50']:,.{dec}f}")
            if r.get("ma200"):
                ma.append(f"200日均 {r['ma200']:,.{dec}f}")
            lines.append(
                f"  {r['name']}: {r['price']:,.{dec}f}｜日 {_chg(r.get('d1'), k)}"
                f"｜週 {_chg(r.get('w1'), k)}｜月 {_chg(r.get('m1'), k)}"
                f"｜3月 {_chg(r.get('m3'), k)}｜{'、'.join(ma)}"
                f"｜距一年高點 {r['from_hi']:+.1f}%｜趨勢 {r['trend']}"
            )
    yc = yield_curve(groups)
    if yc is not None:
        lines.append(f"【殖利率曲線】10年減3個月 = {yc:+d}bp（負值＝倒掛）")
    return "\n".join(lines)


# ── 配置歷史 ─────────────────────────────────────────────────────
def load_alloc_history():
    if ALLOC_FILE.exists():
        return json.loads(ALLOC_FILE.read_text(encoding="utf-8"))
    return {}


def last_allocation(hist, today):
    past = sorted(k for k in hist if k < today)
    return (past[-1], hist[past[-1]]) if past else (None, None)


def save_alloc_history(hist, today, prediction):
    alloc = prediction.get("allocation")
    if not alloc:
        return
    hist[today] = {"allocation": alloc, "regime": prediction.get("regime", "")}
    cutoff = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    hist = {k: v for k, v in hist.items() if k >= cutoff}
    ALLOC_FILE.write_text(
        json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def normalize_allocation(raw):
    """Gemini 給的比例常常加總不是 100 或漏類別，這裡修正；修不了就回 None。"""
    if not isinstance(raw, dict):
        return None
    vals = {}
    for k in ASSET_CLASSES:
        try:
            vals[k] = max(0, float(raw.get(k, 0)))
        except (TypeError, ValueError):
            return None
    total = sum(vals.values())
    if total <= 0:
        return None
    scaled = {k: round(v / total * 100) for k, v in vals.items()}
    gap = 100 - sum(scaled.values())
    if gap:
        biggest = max(scaled, key=scaled.get)
        scaled[biggest] += gap
    return scaled


# ── Gemini 分析 ──────────────────────────────────────────────────
JSON_SCHEMA = (
    '{"headline":"今天最重要的一件事，一句話",'
    '"regime":"目前所處的市場／景氣階段（例：降息循環中段、通膨再起、衰退風險升高），一句",'
    '"sentiment":"偏多/中性/偏空",'
    '"key_events":[{"event":"今日或近期重要事件／數據（含具體數字）","impact":"影響哪類資產、方向如何"}],'
    '"upcoming":["未來一週要注意的事件與日期（Fed、CPI、非農、央行、重要財報等）"],'
    '"assets":[{"asset":"台股/美股/美債/黃金/原物料/美元與台幣（六項都要有）",'
    '"trend":"上升/盤整/下降","outlook":"未來 1-3 個月判斷，1-2 句",'
    '"basis":"判斷依據，必須引用上面提供的數據（漲跌幅、均線、殖利率、利差）或搜尋到的事件"}],'
    '"allocation":{"台股":整數,"美股":整數,"美債":整數,"黃金":整數,"原物料":整數,"現金":整數},'
    '"allocation_change":"跟上期配置比調了什麼、為什麼；沒有上期就說明這個起始配置的邏輯",'
    '"allocation_basis":["支撐這個配置的關鍵理由1","理由2","理由3"],'
    '"swing":[{"target":"標的（限上面數據有的指數／ETF／商品）","signal":"偏多/偏空/觀望",'
    '"entry":"參考進場區間（以現值與均線推算）","invalidation":"判斷失效條件或停損位",'
    '"reason":"1-2 句"}],'
    '"taiex_range":"台灣加權本週預估區間",'
    '"foreign_flow":"外資昨日買賣超台股金額（查不到填 N/A）",'
    '"risks":["可能讓上述判斷出錯的風險1","風險2","風險3"],'
    '"confidence":"高/中/低，與原因一句"}'
)


def build_prompt(groups, prev, with_search):
    today = datetime.now().strftime("%Y年%m月%d日")
    prev_str = (
        f"上期（{prev[0]}）建議配置：{json.dumps(prev[1]['allocation'], ensure_ascii=False)}"
        f"，當時判斷的階段：{prev[1].get('regime', '')}"
        if prev[0]
        else "沒有上期配置（這是第一次）。"
    )
    task = (
        "1. 先搜尋今天與近一週影響全球資產價格的重要新聞：Fed 與台灣央行動向、美國通膨與就業數據、"
        "美債殖利率、美元與台幣、地緣政治、能源與黃金、台股外資買賣超、AI 與半導體產業動態\n"
        "2. 結合下面的市場數據與新聞，輸出 JSON\n"
        if with_search
        else "根據下面的市場數據與你的知識，輸出 JSON\n"
    )
    return (
        f"今天是 {today}。你是一位替台灣個人投資者寫每日財金日報的資產配置顧問。\n"
        f"投資者目前**全部是現金、沒有任何持股**，要的是兩件事：\n"
        f"  (a) 中長期（1-3 個月調整一次）資產配置比例\n"
        f"  (b) 幾週到幾個月的波段進出場訊號\n"
        f"以台幣計價、可投資台股、美股、美債、黃金、原物料，現金可以是台幣或美元。\n\n"
        f"以下是 Yahoo Finance 一年日線算出的數據（趨勢＝現價與 50／200 日均線的相對位置；殖利率的變動單位是 bp）：\n"
        f"{market_summary_str(groups)}\n\n"
        f"{prev_str}\n\n"
        f"{task}\n"
        f"規則：\n"
        f"- 數字只能用上面提供的或搜尋到的，不可以自己編價格或數據\n"
        f"- allocation 六項加總必須是 100，單一資產不超過 60\n"
        f"- 配置不要每天大幅翻轉：除非有明確的新事件或趨勢改變，跟上期的差距每項不超過 5 個百分點\n"
        f"- swing 給 2 到 4 個，沒有好機會就給「觀望」並說明在等什麼\n"
        f"- 全部用繁體中文\n\n"
        f"只回傳 JSON 物件（不含其他文字）：\n{JSON_SCHEMA}"
    )


def analyze(groups, prev, with_search):
    if not GEMINI_KEY:
        return {}
    payload = {
        "contents": [{"parts": [{"text": build_prompt(groups, prev, with_search)}]}],
        "generationConfig": {
            "maxOutputTokens": 6000,
            "temperature": 0.3,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    if with_search:
        payload["tools"] = [{"google_search": {}}]
    label = "Gemini Search" if with_search else "Gemini 知識庫"
    try:
        data = gemini_call(payload)
        text = "".join(
            p.get("text", "") for p in data["candidates"][0]["content"].get("parts", [])
        )
        result = extract_json_obj(text)
        if not result:
            log(f"  {label} 無法解析 JSON，回覆前200字：{text[:200]}")
            return {}
        result["allocation"] = normalize_allocation(result.get("allocation"))
        result["source"] = label
        log(f"  {label}：{result.get('sentiment', '?')}｜配置 {result['allocation']}")
        return result
    except Exception as e:
        log(f"  {label} 失敗：{e}")
        return {}


# ── Notion Block 建構工具 ─────────────────────────────────────────
def _rt(text, bold=False):
    b = {"type": "text", "text": {"content": str(text)[:1900]}}
    if bold:
        b["annotations"] = {"bold": True}
    return b


def _para(text, color=None):
    b = {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [_rt(text)]},
    }
    if color:
        b["paragraph"]["color"] = color
    return b


def _h2(text):
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [_rt(text, bold=True)]},
    }


def _callout(emoji, text, color="gray_background"):
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "icon": {"type": "emoji", "emoji": emoji},
            "rich_text": [_rt(text, bold=True)],
            "color": color,
        },
    }


def _divider():
    return {"object": "block", "type": "divider", "divider": {}}


def _bullet(text):
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [_rt(text)]},
    }


def _make_table(headers, rows):
    def row(cells):
        return {
            "object": "block",
            "type": "table_row",
            "table_row": {
                "cells": [[{"type": "text", "text": {"content": str(c)}}] for c in cells]
            },
        }

    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": len(headers),
            "has_column_header": True,
            "has_row_header": False,
            "children": [row(headers)] + [row(r) for r in rows],
        },
    }


def alloc_rows(prediction, prev):
    alloc = prediction.get("allocation") or {}
    prev_alloc = (prev[1] or {}).get("allocation", {}) if prev[0] else {}
    rows = []
    for k in ASSET_CLASSES:
        if k not in alloc:
            continue
        if k in prev_alloc:
            d = alloc[k] - prev_alloc[k]
            delta = f"{d:+d}" if d else "持平"
        else:
            delta = "—"
        rows.append([k, f"{alloc[k]}%", delta])
    return rows


def build_notion_blocks(groups, prediction, prev):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    color = {"偏多": "green_background", "偏空": "red_background"}.get(
        prediction.get("sentiment"), "yellow_background"
    )
    blocks = [
        _para(
            f"更新時間：{now_str}｜數據：Yahoo Finance｜分析：{prediction.get('source', '無')}",
            "gray",
        )
    ]
    if prediction.get("headline"):
        blocks.append(_callout("📌", prediction["headline"], color))
    if prediction.get("regime"):
        blocks.append(_para(f"市場階段：{prediction['regime']}"))
    blocks.append(_divider())

    if prediction.get("allocation"):
        blocks.append(_h2("💼 建議資產配置"))
        blocks.append(
            _make_table(["資產", "建議比例", "與上期比"], alloc_rows(prediction, prev))
        )
        if prediction.get("allocation_change"):
            blocks.append(_callout("🔁", prediction["allocation_change"], "blue_background"))
        for b in prediction.get("allocation_basis", []):
            blocks.append(_bullet(b))
        blocks.append(_divider())

    if prediction.get("assets"):
        blocks.append(_h2("🔭 各資產走勢判斷"))
        blocks.append(
            _make_table(
                ["資產", "趨勢", "未來 1-3 個月", "依據"],
                [
                    [a.get("asset", ""), a.get("trend", ""), a.get("outlook", ""), a.get("basis", "")]
                    for a in prediction["assets"]
                ],
            )
        )
        blocks.append(_divider())

    if prediction.get("swing"):
        blocks.append(_h2("🎯 波段訊號"))
        blocks.append(
            _make_table(
                ["標的", "訊號", "參考進場", "失效條件", "理由"],
                [
                    [s.get("target", ""), s.get("signal", ""), s.get("entry", ""),
                     s.get("invalidation", ""), s.get("reason", "")]
                    for s in prediction["swing"]
                ],
            )
        )
        if prediction.get("taiex_range"):
            blocks.append(_para(f"台灣加權本週預估區間：{prediction['taiex_range']}"))
        blocks.append(_divider())

    for g in groups:
        blocks.append(_h2(f"📊 {g['title']}"))
        blocks.append(_make_table(TABLE_HEAD, [fmt_row(r) for r in g["rows"]]))
    yc = yield_curve(groups)
    if yc is not None:
        blocks.append(
            _para(f"殖利率曲線（10年減3個月）：{yc:+d}bp" + ("　⚠️ 倒掛" if yc < 0 else ""))
        )
    blocks.append(_divider())

    if prediction.get("key_events"):
        blocks.append(_h2("📰 重要事件"))
        for e in prediction["key_events"]:
            blocks.append(_bullet(f"{e.get('event', '')} → {e.get('impact', '')}"))
        ff = prediction.get("foreign_flow", "")
        if ff and ff != "N/A":
            blocks.append(_bullet(f"外資動向：{ff}"))
    if prediction.get("upcoming"):
        blocks.append(_h2("🗓️ 未來一週要注意"))
        for u in prediction["upcoming"]:
            blocks.append(_bullet(u))
    if prediction.get("risks"):
        blocks.append(_h2("⚠️ 可能出錯的地方"))
        for r in prediction["risks"]:
            blocks.append(_bullet(r))
    if prediction.get("confidence"):
        blocks.append(_para(f"判斷信心：{prediction['confidence']}", "gray"))
    if not prediction:
        blocks.append(_callout("⚠️", "AI 分析暫時無法取得，今天只有數據。", "red_background"))
    blocks.append(_para("AI 依公開資料產生的參考意見，不構成投資建議。", "gray"))
    return blocks


# ── Notion 頁面操作 ───────────────────────────────────────────────
def create_notion_page(parent_id):
    result = notion_req(
        "POST",
        "pages",
        {
            "parent": {"page_id": parent_id},
            "icon": {"type": "emoji", "emoji": "📈"},
            "properties": {"title": {"title": [{"text": {"content": "每日財金日報"}}]}},
        },
    )
    return result["id"]


def update_notion_page(page_id, blocks):
    existing = notion_req("GET", f"blocks/{page_id}/children?page_size=100")
    # Notion 限流約 3 req/s，連打 DELETE 會被擋；以前 except: pass 靜默吞掉，
    # 舊區塊殘留導致隔天「Notion 區塊 N/M」驗證對不上（2026-09-01）。
    failed = []
    for b in existing.get("results", []):
        try:
            notion_req("DELETE", f"blocks/{b['id']}")
        except Exception:
            failed.append(b["id"])
        time.sleep(0.12)
    for bid in failed:
        try:
            notion_req("DELETE", f"blocks/{bid}")
        except Exception as e:
            print(f"⚠️ 舊區塊 {bid} 刪不掉，頁面會殘留：{e}")
        time.sleep(0.12)
    for i in range(0, len(blocks), 50):
        notion_req(
            "PATCH", f"blocks/{page_id}/children", {"children": blocks[i : i + 50]}
        )
        time.sleep(0.2)


# ── 歷史記錄 ─────────────────────────────────────────────────────
def load_history():
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return {}


def save_history(history, groups):
    today = datetime.now().strftime("%Y-%m-%d")
    history[today] = {
        r["code"]: r["price"] for g in groups for r in g["rows"] if r["price"] is not None
    }
    cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    history = {k: v for k, v in history.items() if k >= cutoff}
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── Markdown 報告（PDF 與 Email 都從這份產生，不放 emoji：PDF 字型沒有）──
def _md_table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(clean(c) for c in r) + " |" for r in rows]
    return out


def save_markdown_report(groups, prediction, prev, date_str):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    p = prediction
    lines = [
        f"# 財金日報 {date_str}",
        "",
        f"> 更新時間：{now_str}｜數據：Yahoo Finance｜分析：{p.get('source', '無')}",
        "",
    ]
    if p.get("headline"):
        lines += [f"**今日重點：{clean(p['headline'])}**", ""]
    if p.get("regime") or p.get("sentiment"):
        lines += [
            f"市場階段：{clean(p.get('regime', '—'))}｜整體偏向：{clean(p.get('sentiment', '—'))}",
            "",
        ]

    if p.get("allocation"):
        lines += ["## 建議資產配置"]
        lines += _md_table(["資產", "建議比例", "與上期比"], alloc_rows(p, prev))
        if p.get("allocation_change"):
            lines += ["", f"**調整說明：** {clean(p['allocation_change'])}"]
        for b in p.get("allocation_basis", []):
            lines.append(f"- {clean(b)}")
        lines.append("")

    if p.get("assets"):
        lines += ["## 各資產走勢判斷"]
        lines += _md_table(
            ["資產", "趨勢", "未來 1-3 個月", "依據"],
            [[a.get("asset", ""), a.get("trend", ""), a.get("outlook", ""), a.get("basis", "")]
             for a in p["assets"]],
        )
        lines.append("")

    if p.get("swing"):
        lines += ["## 波段訊號"]
        lines += _md_table(
            ["標的", "訊號", "參考進場", "失效條件", "理由"],
            [[s.get("target", ""), s.get("signal", ""), s.get("entry", ""),
              s.get("invalidation", ""), s.get("reason", "")] for s in p["swing"]],
        )
        if p.get("taiex_range"):
            lines += ["", f"台灣加權本週預估區間：{clean(p['taiex_range'])}"]
        lines.append("")

    lines += ["## 市場數據", "> 趨勢：現價在 50 與 200 日均線之上＝上升、之下＝下降、其餘＝盤整。殖利率變動單位 bp。", ""]
    for g in groups:
        lines += [f"### {g['title']}"]
        lines += _md_table(TABLE_HEAD, [fmt_row(r) for r in g["rows"]])
        lines.append("")
    yc = yield_curve(groups)
    if yc is not None:
        lines += [f"殖利率曲線（10年減3個月）：{yc:+d}bp" + ("（倒掛）" if yc < 0 else ""), ""]

    if p.get("key_events"):
        lines += ["## 重要事件"]
        for e in p["key_events"]:
            lines.append(f"- {clean(e.get('event', ''))} → {clean(e.get('impact', ''))}")
        ff = p.get("foreign_flow", "")
        if ff and ff != "N/A":
            lines.append(f"- 外資動向：{clean(ff)}")
        lines.append("")
    if p.get("upcoming"):
        lines += ["## 未來一週要注意"] + [f"- {clean(u)}" for u in p["upcoming"]] + [""]
    if p.get("risks"):
        lines += ["## 可能出錯的地方"] + [f"- {clean(r)}" for r in p["risks"]] + [""]
    if p.get("confidence"):
        lines += [f"判斷信心：{clean(p['confidence'])}", ""]
    if not p:
        lines += ["**AI 分析暫時無法取得，今天只有數據。**", ""]
    lines.append("> AI 依公開資料產生的參考意見，不構成投資建議。")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"市場日報_{date_str}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    log(f"  Markdown 已儲存：{path.name}")
    return path


# ── 產出驗證 ──────────────────────────────────────────────────────
def verify(groups, prediction, blocks, page_id, report_path):
    """這支不會崩，只會安靜產出爛報告，所以驗的是「內容夠不夠格交件」。

    硬性沒過 → exit 1，workflow 不 commit、不寄信；軟性只警告
    （Gemini 免費額度用罄是常態，不該天天擋掉整份日報）。
    """
    hard, soft = [], []

    rows = [r for g in groups for r in g["rows"]]
    valid = [r for r in rows if r["price"] is not None]
    hard.append((f"有效報價 {len(valid)}/{len(rows)} 筆", len(valid) * 2 >= len(rows)))

    taiex = find(groups, "^TWII")
    hard.append(("台灣加權指數有報價", bool(taiex and taiex["price"] is not None)))

    text = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    hard.append((f"Markdown 共 {len(text.splitlines())} 行", len(text.splitlines()) >= 20))

    missing = [s for s in SECTIONS if f"### {s}" not in text]
    hard.append(
        ("數據區塊齊全" + ("，缺 " + "、".join(missing) if missing else ""), not missing)
    )

    if page_id:
        try:
            got = len(
                notion_req("GET", f"blocks/{page_id}/children?page_size=100").get(
                    "results", []
                )
            )
            hard.append((f"Notion 區塊 {got}/{len(blocks)}", got == len(blocks)))
        except Exception as e:
            hard.append((f"Notion 頁面可讀取（{e}）", False))

    soft.append((f"AI 分析（{prediction.get('source', '無')}）", bool(prediction)))
    soft.append(("配置比例有效", bool(prediction.get("allocation"))))
    covered = {a.get("asset", "") for a in prediction.get("assets", [])}
    soft.append((f"走勢判斷涵蓋 {len(covered)} 類資產", len(covered) >= 5))

    ts = max((r["ts"] for r in valid), default=0)
    age = (datetime.now() - datetime.fromtimestamp(ts)).days if ts else 99
    soft.append((f"報價新鮮度 {age} 天前", age <= 4))

    print("\n{:<40} {}".format("驗證項目", "結果"))
    print("-" * 52)
    for name, passed in hard:
        print("{:<40} {}".format(name, "✅" if passed else "❌"))
    for name, passed in soft:
        print("{:<40} {}".format(name, "✅" if passed else "⚠️"))
    return all(p for _, p in hard)


# ── 主流程 ────────────────────────────────────────────────────────
def build_pdf(md_path, date_str):
    sys.path.insert(0, str(WORKSPACE / "scripts"))
    from md_to_pdf import build_pdf as _build

    PDF_DIR.mkdir(exist_ok=True)
    for old in PDF_DIR.glob("市場日報_*.pdf"):
        old.unlink()
    pdf = PDF_DIR / f"市場日報_{date_str}.pdf"
    _build(str(pdf), [str(md_path)])
    return pdf


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    log(f"📈 每日財金日報開始 {today}")

    cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    groups = fetch_all_market_data(cfg)

    alloc_hist = load_alloc_history()
    prev = last_allocation(alloc_hist, today)

    log("Gemini Search 分析中...")
    prediction = analyze(groups, prev, with_search=True)
    if not prediction:
        log("  降級至 Gemini 知識庫分析...")
        prediction = analyze(groups, prev, with_search=False)

    save_history(load_history(), groups)
    save_alloc_history(alloc_hist, today, prediction)

    page_id = cfg.get("notion_page_id")
    blocks = build_notion_blocks(groups, prediction, prev)
    if NOTION_TOKEN:
        if not page_id:
            page_id = create_notion_page(cfg["notion_parent_page_id"])
            cfg["notion_page_id"] = page_id
            CONFIG_FILE.write_text(
                json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        log(f"更新 Notion ({len(blocks)} blocks)...")
        update_notion_page(page_id, blocks)
    else:
        log("⚠️ 沒有 NOTION_TOKEN，略過 Notion")
        page_id = None

    report_path = save_markdown_report(groups, prediction, prev, today)
    pdf = build_pdf(report_path, today)
    log(f"  PDF 已儲存：{pdf.name}")

    ok = verify(groups, prediction, blocks, page_id, report_path)
    log("✅ 完成！" if ok else "❌ 硬性驗證未過，不交件")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
