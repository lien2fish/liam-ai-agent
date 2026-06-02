#!/usr/bin/env python3
"""
每日股市全面分析報告
每日 09:00 由 GitHub Actions 執行，結果寫入 Notion 頁面 + reports/ Markdown
資料來源：
  Layer 1 — Yahoo Finance（指數、個股、宏觀指標）
  Layer 2 — Gemini + Google Search grounding（新聞、外資動向、AI 預測）
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
REPORTS_DIR = WORKSPACE / "reports"

NOTION_VER = "2022-06-28"
NOTION_API = "https://api.notion.com/v1"
YF_CHART = "https://query1.finance.yahoo.com/v8/finance/chart"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

GEMINI_KEY = os.environ.get("GEMINI_KEY", "")


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
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = 30 * (attempt + 1)
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


# ── Yahoo Finance ────────────────────────────────────────────────
def fetch_yf(symbol):
    encoded = urllib.parse.quote(symbol, safe=".")
    url = f"{YF_CHART}/{encoded}?interval=1d&range=5d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read())
        meta = data["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice")
        prev = meta.get("chartPreviousClose") or meta.get("regularMarketPreviousClose")
        change = round(price - prev, 4) if price and prev else None
        change_pct = round(change / prev * 100, 2) if change and prev else None
        return {
            "price": price,
            "change": change,
            "change_pct": change_pct,
            "ts": meta.get("regularMarketTime", 0),
            "currency": meta.get("currency", ""),
        }
    except Exception as e:
        log(f"  YF {symbol} 失敗：{e}")
        return {
            "price": None,
            "change": None,
            "change_pct": None,
            "ts": 0,
            "currency": "",
        }


def fetch_all_market_data(cfg):
    indices_def = [
        ("^TWII", "台灣加權指數", 0),
        ("^GSPC", "S&P 500", 0),
        ("^IXIC", "NASDAQ", 0),
        ("^DJI", "道瓊斯", 0),
        ("^N225", "日經225", 0),
        ("^HSI", "恒生指數", 0),
    ]
    macro_def = [
        ("^VIX", "VIX 恐慌指數", 2),
        ("USDTWD=X", "美元/台幣", 3),
        ("BZ=F", "布蘭特原油(USD/桶)", 2),
        ("GC=F", "黃金(USD/oz)", 0),
    ]
    watch = cfg.get("watch_stocks", [])

    result = {"indices": [], "macro": [], "stocks": []}

    log("抓取全球指數...")
    for code, name, dec in indices_def:
        d = fetch_yf(code)
        d.update({"code": code, "name": name, "dec": dec})
        result["indices"].append(d)
        time.sleep(0.3)

    log("抓取宏觀指標...")
    for code, name, dec in macro_def:
        d = fetch_yf(code)
        d.update({"code": code, "name": name, "dec": dec})
        result["macro"].append(d)
        time.sleep(0.3)

    log("抓取台灣觀察清單...")
    for s in watch:
        d = fetch_yf(s["code"])
        d.update(
            {
                "code": s["code"],
                "name": s["name"],
                "holding": s.get("holding", False),
                "dec": 2,
            }
        )
        result["stocks"].append(d)
        time.sleep(0.3)

    valid = sum(1 for g in result.values() for d in g if d["price"])
    log(f"  共 {valid} 筆有效數據")
    return result


# ── Gemini 分析 ──────────────────────────────────────────────────
def _market_summary_str(md):
    lines = ["【全球指數】"]
    for d in md["indices"]:
        p = f"{d['price']:,.0f}" if d["price"] else "N/A"
        c = f"{d['change_pct']:+.2f}%" if d["change_pct"] is not None else "N/A"
        lines.append(f"  {d['name']}: {p} ({c})")
    lines.append("【宏觀指標】")
    for d in md["macro"]:
        p = f"{d['price']:.2f}" if d["price"] else "N/A"
        c = f"{d['change_pct']:+.2f}%" if d["change_pct"] is not None else ""
        lines.append(f"  {d['name']}: {p} {c}".strip())
    lines.append("【台灣觀察股】")
    for d in md["stocks"]:
        p = f"{d['price']:.2f}" if d["price"] else "N/A"
        c = f"{d['change_pct']:+.2f}%" if d["change_pct"] is not None else "N/A"
        lines.append(f"  {d['name']} ({d['code']}): {p} ({c})")
    return "\n".join(lines)


def analyze_with_gemini(md):
    if not GEMINI_KEY:
        return {}
    today = datetime.now().strftime("%Y年%m月%d日")
    market_str = _market_summary_str(md)

    prompt = (
        f"今天是 {today}。以下是 Yahoo Finance 最新市場數據（可能為前一交易日收盤）：\n"
        f"{market_str}\n\n"
        f"請完成：\n"
        f"1. 搜尋今日台灣股市重要新聞（外資買超/賣超金額、法說會、重大政策、美股影響）\n"
        f"2. 根據市場數據與今日新聞，輸出 JSON 分析報告\n\n"
        f"只回傳 JSON 物件（不含其他文字）：\n"
        f'{{"sentiment":"多頭/空頭/震盪",'
        f'"sentiment_score":1到10的整數（10最樂觀）,'
        f'"key_news":["最重要新聞1","新聞2","新聞3"],'
        f'"foreign_flow":"外資今日買超或賣超XX億元（查不到填N/A）",'
        f'"week_outlook":"一週大盤展望，2到3句繁體中文",'
        f'"risks":["主要風險1","風險2","風險3"],'
        f'"taiex_range":"本週台灣加權預估區間（如：22000-23500）"}}'
    )

    try:
        data = gemini_call(
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "tools": [{"google_search": {}}],
                "generationConfig": {"maxOutputTokens": 2048, "temperature": 0.3},
            }
        )
        text = "".join(
            p.get("text", "") for p in data["candidates"][0]["content"].get("parts", [])
        )
        result = extract_json_obj(text)
        if result:
            log(
                f"  情緒：{result.get('sentiment','?')}  score={result.get('sentiment_score','?')}"
            )
        else:
            log(f"  Gemini Search 無法解析 JSON，回覆前200字：{text[:200]}")
        return result
    except Exception as e:
        log(f"  Gemini Search 失敗：{e}")
        return {}


def fallback_analysis(md):
    if not GEMINI_KEY:
        return {}
    market_str = _market_summary_str(md)
    prompt = (
        f"根據以下市場數據，提供台灣股市分析。只回傳 JSON，不含其他文字：\n"
        f"{market_str}\n\n"
        f'{{"sentiment":"多頭/空頭/震盪","sentiment_score":1到10,'
        f'"key_news":["觀察點1","觀察點2","觀察點3"],'
        f'"foreign_flow":"N/A",'
        f'"week_outlook":"一週展望說明（2-3句）",'
        f'"risks":["風險1","風險2","風險3"],'
        f'"taiex_range":"預估區間"}}'
    )
    try:
        data = gemini_call(
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.3},
            }
        )
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return extract_json_obj(text)
    except Exception as e:
        log(f"  Gemini fallback 失敗：{e}")
        return {}


# ── Notion Block 建構工具 ─────────────────────────────────────────
def _rt(text, bold=False):
    b = {"type": "text", "text": {"content": str(text)}}
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


def _toggle(text, children):
    return {
        "object": "block",
        "type": "toggle",
        "toggle": {"rich_text": [_rt(text, bold=True)], "children": children},
    }


def _cell(text):
    return [{"type": "text", "text": {"content": str(text)}}]


def _make_table(headers, rows):
    table_rows = [
        {
            "object": "block",
            "type": "table_row",
            "table_row": {"cells": [_cell(h) for h in headers]},
        }
    ]
    for row in rows:
        table_rows.append(
            {
                "object": "block",
                "type": "table_row",
                "table_row": {"cells": [_cell(v) for v in row]},
            }
        )
    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": len(headers),
            "has_column_header": True,
            "has_row_header": False,
            "children": table_rows,
        },
    }


def _fmt(d):
    """格式化一個股票/指數資料，回傳 (現值, 漲跌, 漲跌幅)。"""
    dec = d.get("dec", 2)
    if d["price"] is None:
        return "—", "—", "—"
    price = f"{d['price']:,.{dec}f}"
    if d["change"] is None:
        return price, "—", "—"
    sign = "▲" if d["change"] > 0 else ("▼" if d["change"] < 0 else "→")
    change = f"{sign} {abs(d['change']):,.{dec}f}"
    pct = f"{d['change_pct']:+.2f}%"
    return price, change, pct


# ── Notion 頁面內容 ───────────────────────────────────────────────
def build_notion_blocks(md, prediction):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    sentiment = prediction.get("sentiment", "震盪")
    score = prediction.get("sentiment_score", 5)
    color_map = {
        "多頭": "green_background",
        "空頭": "red_background",
        "震盪": "yellow_background",
    }
    emoji_map = {"多頭": "📈", "空頭": "📉", "震盪": "↔️"}
    sentiment_color = color_map.get(sentiment, "gray_background")
    sentiment_emoji = emoji_map.get(sentiment, "📊")

    blocks = [
        _para(
            f"更新時間：{now_str}｜來源：Yahoo Finance / Gemini Google Search", "gray"
        ),
        _callout(
            sentiment_emoji,
            f"市場情緒：{sentiment}　樂觀指數 {score}/10",
            sentiment_color,
        ),
        _divider(),
        _h2("🌏 全球指數"),
        _make_table(
            ["指數", "現值", "漲跌", "漲跌幅"],
            [[d["name"]] + list(_fmt(d)) for d in md["indices"]],
        ),
        _divider(),
        _h2("📊 宏觀指標"),
        _make_table(
            ["指標", "現值", "漲跌", "漲跌幅"],
            [[d["name"]] + list(_fmt(d)) for d in md["macro"]],
        ),
        _divider(),
        _h2("🇹🇼 台灣觀察清單"),
        _make_table(
            ["股票名稱", "代號", "現價", "漲跌", "漲跌幅", "持有"],
            [
                [d["name"], d["code"]]
                + list(_fmt(d))
                + ["★" if d.get("holding") else ""]
                for d in md["stocks"]
            ],
        ),
        _divider(),
    ]

    if prediction.get("key_news"):
        blocks.append(_h2("📰 今日市場新聞"))
        for news in prediction["key_news"]:
            blocks.append(_bullet(news))
        ff = prediction.get("foreign_flow", "")
        if ff and ff != "N/A":
            blocks.append(_bullet(f"💹 外資動向：{ff}"))
        blocks.append(_divider())

    blocks.append(_h2("🤖 AI 市場預估"))
    if prediction.get("taiex_range"):
        blocks.append(
            _callout(
                "📐",
                f"本週台灣加權預估區間：{prediction['taiex_range']}",
                "blue_background",
            )
        )
    if prediction.get("week_outlook"):
        blocks.append(_callout("🔭", prediction["week_outlook"], "gray_background"))
    if prediction.get("risks"):
        blocks.append(
            _toggle("⚠️ 主要風險提示", [_bullet(r) for r in prediction["risks"]])
        )
    if not prediction:
        blocks.append(_callout("⚠️", "AI 分析暫時無法取得。", "red_background"))

    return blocks


# ── Notion 頁面操作 ───────────────────────────────────────────────
def create_notion_page(parent_id):
    result = notion_req(
        "POST",
        "pages",
        {
            "parent": {"page_id": parent_id},
            "icon": {"type": "emoji", "emoji": "📈"},
            "properties": {"title": {"title": [{"text": {"content": "每日市場日報"}}]}},
        },
    )
    return result["id"]


def update_notion_page(page_id, blocks):
    existing = notion_req("GET", f"blocks/{page_id}/children?page_size=100")
    for b in existing.get("results", []):
        try:
            notion_req("DELETE", f"blocks/{b['id']}")
        except Exception:
            pass
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


def save_history(history, md):
    today = datetime.now().strftime("%Y-%m-%d")
    entry = {}
    for group in md.values():
        for d in group:
            if d.get("price"):
                entry[d["code"]] = d["price"]
    history[today] = entry
    cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    history = {k: v for k, v in history.items() if k >= cutoff}
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return history


# ── Markdown 報告 ─────────────────────────────────────────────────
def save_markdown_report(md, prediction, date_str):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    sentiment = prediction.get("sentiment", "—")
    score = prediction.get("sentiment_score", "—")

    lines = [
        f"# 📈 每日市場日報 {date_str}",
        f"",
        f"> 更新時間：{now_str}｜來源：Yahoo Finance / Gemini Search",
        f"",
        f"**市場情緒：{sentiment}　樂觀指數 {score}/10**",
        f"",
        f"## 🌏 全球指數",
        f"| 指數 | 現值 | 漲跌 | 漲跌幅 |",
        f"|------|------|------|--------|",
    ]
    for d in md["indices"]:
        p, ch, pct = _fmt(d)
        lines.append(f"| {d['name']} | {p} | {ch} | {pct} |")

    lines += [
        "",
        "## 📊 宏觀指標",
        "| 指標 | 現值 | 漲跌 | 漲跌幅 |",
        "|------|------|------|--------|",
    ]
    for d in md["macro"]:
        p, ch, pct = _fmt(d)
        lines.append(f"| {d['name']} | {p} | {ch} | {pct} |")

    lines += [
        "",
        "## 🇹🇼 台灣觀察清單",
        "| 股票 | 代號 | 現價 | 漲跌 | 漲跌幅 |",
        "|------|------|------|------|--------|",
    ]
    for d in md["stocks"]:
        p, ch, pct = _fmt(d)
        tag = "★" if d.get("holding") else ""
        lines.append(f"| {tag}{d['name']} | {d['code']} | {p} | {ch} | {pct} |")

    if prediction.get("key_news"):
        lines += ["", "## 📰 今日市場新聞"]
        for n in prediction["key_news"]:
            lines.append(f"- {n}")
        ff = prediction.get("foreign_flow", "")
        if ff and ff != "N/A":
            lines.append(f"- 💹 外資動向：{ff}")

    if prediction.get("week_outlook"):
        lines += ["", "## 🔭 一週展望", prediction["week_outlook"]]

    if prediction.get("taiex_range"):
        lines += ["", f"**本週台灣加權預估區間：{prediction['taiex_range']}**"]

    if prediction.get("risks"):
        lines += ["", "## ⚠️ 主要風險"]
        for r in prediction["risks"]:
            lines.append(f"- {r}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"市場日報_{date_str}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    log(f"  Markdown 已儲存：{path.name}")


# ── Config ───────────────────────────────────────────────────────
def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {
        "notion_page_id": None,
        "notion_parent_page_id": "36af4149-a6aa-8192-9065-f9e5f97ebabf",
        "watch_stocks": [],
    }


def save_config(cfg):
    CONFIG_FILE.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── 主流程 ────────────────────────────────────────────────────────
def main():
    today = datetime.now().strftime("%Y-%m-%d")
    log(f"📈 每日市場日報開始 {today}")

    cfg = load_config()

    md = fetch_all_market_data(cfg)

    log("Gemini Search 分析中...")
    prediction = analyze_with_gemini(md)
    if not prediction:
        log("  降級至 Gemini 知識庫分析...")
        prediction = fallback_analysis(md)

    history = load_history()
    save_history(history, md)

    page_id = cfg.get("notion_page_id")
    if not page_id:
        log("建立 Notion 頁面...")
        page_id = create_notion_page(cfg["notion_parent_page_id"])
        cfg["notion_page_id"] = page_id
        save_config(cfg)
        log(f"  頁面 ID：{page_id}")

    blocks = build_notion_blocks(md, prediction)
    log(f"更新 Notion ({len(blocks)} blocks)...")
    update_notion_page(page_id, blocks)

    save_markdown_report(md, prediction, today)

    log("✅ 完成！")
    log(f"   https://notion.so/{page_id.replace('-', '')}")


if __name__ == "__main__":
    main()
