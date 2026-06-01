#!/usr/bin/env python3
"""
台灣北部漁獲市場價格追蹤
每日 08:10 由 GitHub Actions 執行，結果寫入 Notion 頁面。
資料來源：
  Layer 1 — Gemini + Google Search grounding（即時搜尋今日行情）
  Layer 2 — 農業部 MOA 開放資料 API（備援）
"""

import json
import os
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

# ── 路徑與設定 ────────────────────────────────────────────────────
WORKSPACE = Path(
    os.environ.get("GITHUB_WORKSPACE", "/Users/lien/Downloads/Liam AI agent")
)
CONFIG_FILE = WORKSPACE / "seafood/price_config.json"
HISTORY_FILE = WORKSPACE / "seafood/price_history.json"
SEASONAL_FILE = WORKSPACE / "seafood/seasonal_fish.json"

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
GEMINI_KEY = os.environ.get("GEMINI_KEY", "")
NOTION_VER = "2022-06-28"
NOTION_API = "https://api.notion.com/v1"
MOA_API = "https://data.moa.gov.tw/Service/OpenData/FromM/FishMarketData.aspx"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

NORTH_MARKETS = ["基隆", "台北", "臺北", "萬里", "富基", "龜吼", "石門"]


# ── 工具函式 ──────────────────────────────────────────────────────


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def get_seasonal_fish() -> list[str]:
    data = json.loads(SEASONAL_FILE.read_text(encoding="utf-8"))
    month = datetime.now().month
    for key, fish_list in data.items():
        lo, hi = map(int, key.split("-"))
        if lo <= month <= hi:
            return fish_list
    return []


def notion_request(method: str, path: str, body: dict = None):
    url = f"{NOTION_API}/{path}"
    data = json.dumps(body).encode() if body else None
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


# ── Layer 1：Gemini + Google Search grounding ────────────────────


def fetch_with_gemini_search(seasonal: list[str]) -> list[dict]:
    """使用 Gemini Google Search grounding 搜尋今日北部漁市場行情。"""
    if not GEMINI_KEY:
        return []

    today = datetime.now().strftime("%Y年%m月%d日")
    seasonal_str = "、".join(seasonal)

    prompt = (
        f"請搜尋 {today} 台灣北部漁市場（基隆崁仔頂、基隆漁會、萬里漁港）的批發行情。"
        f"特別關注當季品項：{seasonal_str}。"
        f"整理成 JSON 陣列，每筆包含：\n"
        f"  name: 品名（繁體中文）\n"
        f"  high: 上價（元/kg，float）\n"
        f"  mid: 中價（元/kg，float）\n"
        f"  low: 下價（元/kg，float）\n"
        f"  volume: 交易量（kg，float，不確定填 0）\n"
        f"  market: 市場名稱\n"
        f"若無法確認今日價格，回傳最近可查到的價格（標註日期在 market 欄位）。"
        f"只回傳 JSON 陣列，不加任何說明文字。"
    )

    payload = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {"maxOutputTokens": 2048, "temperature": 0},
        }
    ).encode()

    req = urllib.request.Request(
        f"{GEMINI_URL}?key={GEMINI_KEY}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())

    # Gemini 可能在多個 parts 中回傳（search grounding 的引用在另一個 part）
    full_text = ""
    for part in data["candidates"][0]["content"].get("parts", []):
        full_text += part.get("text", "")
    full_text = full_text.replace("```json", "").replace("```", "").strip()
    start = full_text.find("[")
    end = full_text.rfind("]") + 1
    if start == -1 or end == 0:
        log(f"  Gemini Search 回傳無 JSON 陣列，原始回覆前200字：{full_text[:200]}")
        return []
    result = json.loads(full_text[start:end])
    return result


def gemini_reference_prices(seasonal: list[str]) -> list[dict]:
    """當 Search 拿不到資料時，用 Gemini 知識庫產生當月北部市場參考行情。"""
    if not GEMINI_KEY:
        return []

    month = datetime.now().month
    seasonal_str = "、".join(seasonal)
    prompt = (
        f"你是台灣北部漁市場（基隆崁仔頂、萬里漁港）的行情專家。"
        f"請根據你的知識，提供 {month} 月份台灣北部漁市場的批發參考行情。"
        f"當季重點品項：{seasonal_str}。"
        f"請同時列出其他常見北部市場漁獲品項。"
        f"整理成 JSON 陣列，每筆包含：\n"
        f"  name: 品名\n"
        f"  high: 上價（元/kg）\n"
        f"  mid: 中價（元/kg）\n"
        f"  low: 下價（元/kg）\n"
        f"  volume: 0\n"
        f'  market: "參考行情（非即時）"\n'
        f"只回傳 JSON 陣列，不加說明。"
    )
    payload = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.2},
        }
    ).encode()
    req = urllib.request.Request(
        f"{GEMINI_URL}?key={GEMINI_KEY}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    text = text.replace("```json", "").replace("```", "").strip()
    start = text.find("[")
    end = text.rfind("]") + 1
    if start == -1 or end == 0:
        return []
    return json.loads(text[start:end])


# ── Layer 2：農業部 MOA 開放資料 API（備援）────────────────────


def fetch_from_moa() -> list[dict]:
    params = urllib.parse.urlencode({"$top": "1000", "$format": "JSON"})
    url = f"{MOA_API}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = json.loads(r.read())

    today = datetime.now().strftime("%Y.%m.%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y.%m.%d")
    results = []
    for item in raw:
        market = item.get("市場名稱", "")
        if not any(k in market for k in NORTH_MARKETS):
            continue
        if item.get("交易日期", "") not in (today, yesterday):
            continue
        try:
            results.append(
                {
                    "name": item["品種名稱"],
                    "high": float(item.get("上價") or 0),
                    "mid": float(item.get("中價") or 0),
                    "low": float(item.get("下價") or 0),
                    "volume": float(item.get("交易量") or 0),
                    "market": market,
                    "date": item.get("交易日期", ""),
                }
            )
        except (KeyError, ValueError):
            continue
    return results


# ── 歷史記錄 ─────────────────────────────────────────────────────


def load_history() -> dict:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return {}


def save_history(history: dict, today_data: list[dict]) -> dict:
    today_str = datetime.now().strftime("%Y-%m-%d")
    history[today_str] = {i["name"]: i["mid"] for i in today_data if i.get("mid")}
    cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    history = {k: v for k, v in history.items() if k >= cutoff}
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return history


def calc_trend(name: str, current_mid: float, history: dict) -> str:
    for date in sorted(history.keys(), reverse=True):
        prev = history[date].get(name)
        if prev and prev > 0 and current_mid > 0:
            pct = (current_mid - prev) / prev * 100
            if pct > 3:
                return f"↑+{pct:.0f}%"
            elif pct < -3:
                return f"↓{pct:.0f}%"
            return "→持平"
    return "—"


# ── Notion 頁面操作 ───────────────────────────────────────────────


def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {
        "notion_page_id": "",
        "notion_parent_page_id": "358f4149-a6aa-8088-9e6d-f5361d05cd12",
    }


def save_config(cfg: dict):
    CONFIG_FILE.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def create_notion_page(parent_id: str) -> str:
    result = notion_request(
        "POST",
        "pages",
        {
            "parent": {"page_id": parent_id},
            "icon": {"type": "emoji", "emoji": "🐟"},
            "properties": {"title": {"title": [{"text": {"content": "漁獲市場行情"}}]}},
        },
    )
    return result["id"]


def make_table_block(rows: list[dict], history: dict) -> dict:
    header = [
        [{"type": "text", "text": {"content": c}}]
        for c in ["品名", "上價", "中價", "下價", "交易量(kg)", "市場", "趨勢"]
    ]
    table_rows = [
        {"object": "block", "type": "table_row", "table_row": {"cells": header}}
    ]
    for item in rows:
        trend = calc_trend(item["name"], item.get("mid", 0), history)
        cells = [
            [{"type": "text", "text": {"content": item["name"]}}],
            [
                {
                    "type": "text",
                    "text": {
                        "content": f"{item['high']:.0f}" if item.get("high") else "—"
                    },
                }
            ],
            [
                {
                    "type": "text",
                    "text": {
                        "content": f"{item['mid']:.0f}" if item.get("mid") else "—"
                    },
                }
            ],
            [
                {
                    "type": "text",
                    "text": {
                        "content": f"{item['low']:.0f}" if item.get("low") else "—"
                    },
                }
            ],
            [
                {
                    "type": "text",
                    "text": {
                        "content": (
                            f"{item['volume']:.0f}" if item.get("volume") else "—"
                        )
                    },
                }
            ],
            [{"type": "text", "text": {"content": item.get("market", "—")}}],
            [{"type": "text", "text": {"content": trend}}],
        ]
        table_rows.append(
            {"object": "block", "type": "table_row", "table_row": {"cells": cells}}
        )
    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": 7,
            "has_column_header": True,
            "has_row_header": False,
            "children": table_rows,
        },
    }


def build_notion_blocks(
    items: list[dict], seasonal: list[str], history: dict
) -> list[dict]:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    blocks = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": f"更新時間：{now_str}｜資料來源：Gemini Google Search / 農業部漁市場行情"
                        },
                    }
                ],
                "color": "gray",
            },
        }
    ]

    seasonal_items = [i for i in items if any(s in i["name"] for s in seasonal)]
    other_items = [i for i in items if not any(s in i["name"] for s in seasonal)]

    if seasonal_items:
        blocks.append(
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "🌊 今日當季行情（北部市場）"},
                        }
                    ]
                },
            }
        )
        blocks.append(make_table_block(seasonal_items, history))

    if other_items:
        blocks.append(
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "📦 其他到貨品項"}}
                    ]
                },
            }
        )
        blocks.append(make_table_block(other_items[:20], history))

    if not items:
        blocks.append(
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "今日暫無行情資料，可能為休市日或 API 暫時不可用。"
                            },
                        }
                    ],
                    "icon": {"type": "emoji", "emoji": "⚠️"},
                },
            }
        )
    return blocks


def update_notion_page(page_id: str, blocks: list[dict]):
    existing = notion_request("GET", f"blocks/{page_id}/children?page_size=100")
    for block in existing.get("results", []):
        try:
            notion_request("DELETE", f"blocks/{block['id']}")
        except Exception:
            pass
    for i in range(0, len(blocks), 50):
        notion_request(
            "PATCH", f"blocks/{page_id}/children", {"children": blocks[i : i + 50]}
        )


# ── 主流程 ────────────────────────────────────────────────────────


def main():
    seasonal = get_seasonal_fish()
    log(f"當季魚種：{', '.join(seasonal)}")

    # Layer 1: Gemini + Google Search grounding
    items = []
    try:
        items = fetch_with_gemini_search(seasonal)
        log(f"Gemini Search 取得 {len(items)} 筆行情")
    except Exception as e:
        log(f"Gemini Search 失敗：{e}")

    # Layer 2: MOA API
    if not items:
        try:
            items = fetch_from_moa()
            log(f"MOA API 取得 {len(items)} 筆北部市場資料")
        except Exception as e:
            log(f"MOA API 失敗：{e}")

    # Layer 3: Gemini 知識庫參考行情（當所有即時來源失敗時）
    if not items:
        try:
            log("改用 Gemini 知識庫產生當月參考行情...")
            items = gemini_reference_prices(seasonal)
            log(f"Gemini 參考行情：{len(items)} 筆")
        except Exception as e:
            log(f"Gemini 參考行情失敗：{e}")

    history = load_history()
    history = save_history(history, items)

    cfg = load_config()
    page_id = cfg.get("notion_page_id", "")
    if not page_id:
        parent_id = cfg.get("notion_parent_page_id", "")
        log("建立新 Notion 頁面...")
        page_id = create_notion_page(parent_id)
        cfg["notion_page_id"] = page_id
        save_config(cfg)
        log(f"✅ 頁面建立：{page_id}")

    blocks = build_notion_blocks(items, seasonal, history)
    update_notion_page(page_id, blocks)
    log(f"✅ Notion 更新完成，{len(items)} 筆行情，{len(blocks)} 個 block")


if __name__ == "__main__":
    main()
