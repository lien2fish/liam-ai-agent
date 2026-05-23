#!/usr/bin/env python3
"""
Personal Finance OS v2.0 — Notion Template Creator
個人財務作業系統 v2.0 — Notion 模板生成器

執行一次，在 Notion 建立完整雙語財務模板（含示範資料）
Run once to create the full bilingual finance template with sample data.

Usage:
    NOTION_PARENT_ID=<page_id> python3 finance/create_commercial_template.py
    python3 finance/create_commercial_template.py --parent-id <page_id>
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date

from dateutil.relativedelta import relativedelta


# ── Token ─────────────────────────────────────────────────────────────────────


def _load_token() -> str:
    token = os.environ.get("NOTION_TOKEN")
    if token:
        return token
    try:
        config_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "notion_crm"
        )
        sys.path.insert(0, os.path.abspath(config_dir))
        import config as _cfg

        sys.path.pop(0)
        return _cfg.NOTION_TOKEN
    except (ImportError, AttributeError):
        pass
    raise RuntimeError("NOTION_TOKEN 未設定 / not set")


TOKEN = _load_token()
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


# ── API helpers ────────────────────────────────────────────────────────────────


def api(method, path, data=None):
    url = f"https://api.notion.com/v1{path}"
    body = json.dumps(data, ensure_ascii=False).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        err_body = e.read()
        try:
            err = json.loads(err_body)
            print(f"  ❌ {e.code}: {err.get('message', err_body)}")
        except Exception:
            print(f"  ❌ HTTP {e.code}: {err_body}")
        raise


def sleep():
    time.sleep(0.4)


def txt(content, bold=False, italic=False, color="default"):
    ann = {}
    if bold:
        ann["bold"] = True
    if italic:
        ann["italic"] = True
    if color != "default":
        ann["color"] = color
    obj = {"type": "text", "text": {"content": content}}
    if ann:
        obj["annotations"] = ann
    return obj


# ── Database schemas ───────────────────────────────────────────────────────────


def create_assets_db(parent_id: str) -> str:
    db = api(
        "POST",
        "/databases",
        {
            "parent": {"page_id": parent_id},
            "icon": {"type": "emoji", "emoji": "💰"},
            "title": [{"type": "text", "text": {"content": "💰 Assets  ·  資產明細"}}],
            "properties": {
                "項目名稱 / Asset Name": {"title": {}},
                "類別 / Category": {
                    "select": {
                        "options": [
                            {"name": "不動產 Real Estate", "color": "orange"},
                            {"name": "股權 Equity", "color": "yellow"},
                            {"name": "保單 Insurance", "color": "green"},
                            {"name": "投資 Investment", "color": "blue"},
                            {"name": "黃金 Gold", "color": "yellow"},
                            {"name": "存款 Savings", "color": "gray"},
                            {"name": "其他 Other", "color": "default"},
                        ]
                    }
                },
                "當前金額 / Current Value": {"number": {"format": "number"}},
                "成本 / Cost Basis": {"number": {"format": "number"}},
                "上次更新 / Last Updated": {"date": {}},
                "自動更新 / Auto Updated": {"checkbox": {}},
                "說明 / Notes": {"rich_text": {}},
            },
        },
    )
    sleep()
    return db["id"]


def create_liabilities_db(parent_id: str) -> str:
    db = api(
        "POST",
        "/databases",
        {
            "parent": {"page_id": parent_id},
            "icon": {"type": "emoji", "emoji": "💳"},
            "title": [
                {"type": "text", "text": {"content": "💳 Liabilities  ·  負債明細"}}
            ],
            "properties": {
                "項目名稱 / Liability Name": {"title": {}},
                "類別 / Category": {
                    "select": {
                        "options": [
                            {"name": "房貸 Mortgage", "color": "red"},
                            {"name": "信貸 Personal Loan", "color": "orange"},
                            {"name": "車貸 Auto Loan", "color": "yellow"},
                            {"name": "信用卡 Credit Card", "color": "pink"},
                            {"name": "其他 Other", "color": "default"},
                        ]
                    }
                },
                "餘額 / Balance": {"number": {"format": "number"}},
                "原始金額 / Original Amount": {"number": {"format": "number"}},
                "年利率 / Annual Rate": {"number": {"format": "percent"}},
                "月還款 / Monthly Payment": {"number": {"format": "number"}},
                "到期日 / Due Date": {"date": {}},
                "說明 / Notes": {"rich_text": {}},
            },
        },
    )
    sleep()
    return db["id"]


def create_snapshot_db(parent_id: str) -> str:
    db = api(
        "POST",
        "/databases",
        {
            "parent": {"page_id": parent_id},
            "icon": {"type": "emoji", "emoji": "📊"},
            "title": [
                {
                    "type": "text",
                    "text": {"content": "📊 Monthly Snapshot  ·  月度快照"},
                }
            ],
            "properties": {
                "月份 / Month": {"title": {}},
                "總資產 / Total Assets": {"number": {"format": "number"}},
                "總負債 / Total Liabilities": {"number": {"format": "number"}},
                "淨值 / Net Worth": {"number": {"format": "number"}},
                "月收入 / Monthly Income": {"number": {"format": "number"}},
                "月支出 / Monthly Expenses": {"number": {"format": "number"}},
                "月結餘 / Net Cash Flow": {"number": {"format": "number"}},
                "儲蓄率 / Savings Rate %": {
                    "formula": {
                        "expression": (
                            'if(prop("月收入 / Monthly Income") > 0, '
                            'round(prop("月結餘 / Net Cash Flow") / prop("月收入 / Monthly Income") * 10000) / 100, '
                            "0)"
                        )
                    }
                },
                "備註 / Notes": {"rich_text": {}},
            },
        },
    )
    sleep()
    return db["id"]


# ── Sample data ────────────────────────────────────────────────────────────────

SAMPLE_ASSETS = [
    {
        "name": "自住房產 / Primary Residence",
        "cat": "不動產 Real Estate",
        "value": 8_000_000,
        "cost": 6_500_000,
        "auto": False,
        "notes": "市場估值，每年手動更新 / Market value, update annually",
    },
    {
        "name": "公司股權 / Company Equity",
        "cat": "股權 Equity",
        "value": 3_000_000,
        "cost": 1_000_000,
        "auto": False,
        "notes": "依出資比例估算 / Based on contribution ratio",
    },
    {
        "name": "黃金存摺 / Gold Savings",
        "cat": "黃金 Gold",
        "value": 280_000,
        "cost": 250_000,
        "auto": True,
        "notes": "✅ GitHub Actions 每月 1 日自動更新 / Auto-updated on 1st of each month",
    },
    {
        "name": "台灣50 ETF (0050)",
        "cat": "投資 Investment",
        "value": 450_000,
        "cost": 380_000,
        "auto": False,
        "notes": "定期定額 / Dollar-cost averaging",
    },
    {
        "name": "人壽保單 / Life Insurance Policy",
        "cat": "保單 Insurance",
        "value": 600_000,
        "cost": 480_000,
        "auto": False,
        "notes": "2035 年到期 / Matures 2035",
    },
    {
        "name": "銀行存款 / Bank Savings",
        "cat": "存款 Savings",
        "value": 920_000,
        "cost": 920_000,
        "auto": False,
        "notes": "活存 + 定存 / Checking + Fixed deposit",
    },
]

SAMPLE_LIABILITIES = [
    {
        "name": "房貸 / Mortgage",
        "cat": "房貸 Mortgage",
        "balance": 3_200_000,
        "original": 4_500_000,
        "rate": 0.018,
        "payment": 22_000,
        "due": "2040-06-01",
        "notes": "20 年期房貸 / 20-year mortgage",
    },
    {
        "name": "信貸 / Personal Loan",
        "cat": "信貸 Personal Loan",
        "balance": 480_000,
        "original": 600_000,
        "rate": 0.049,
        "payment": 8_452,
        "due": "2030-07-29",
        "notes": "✅ GitHub Actions 每月 1 日自動更新 / Auto-updated on 1st of each month",
    },
]


def seed_assets(db_id: str):
    today = date.today().isoformat()
    for a in SAMPLE_ASSETS:
        api(
            "POST",
            "/pages",
            {
                "parent": {"database_id": db_id},
                "properties": {
                    "項目名稱 / Asset Name": {
                        "title": [{"text": {"content": a["name"]}}]
                    },
                    "類別 / Category": {"select": {"name": a["cat"]}},
                    "當前金額 / Current Value": {"number": a["value"]},
                    "成本 / Cost Basis": {"number": a["cost"]},
                    "上次更新 / Last Updated": {"date": {"start": today}},
                    "自動更新 / Auto Updated": {"checkbox": a["auto"]},
                    "說明 / Notes": {"rich_text": [{"text": {"content": a["notes"]}}]},
                },
            },
        )
        sleep()
        print(f"    + 資產: {a['name']}")


def seed_liabilities(db_id: str):
    for l in SAMPLE_LIABILITIES:
        api(
            "POST",
            "/pages",
            {
                "parent": {"database_id": db_id},
                "properties": {
                    "項目名稱 / Liability Name": {
                        "title": [{"text": {"content": l["name"]}}]
                    },
                    "類別 / Category": {"select": {"name": l["cat"]}},
                    "餘額 / Balance": {"number": l["balance"]},
                    "原始金額 / Original Amount": {"number": l["original"]},
                    "年利率 / Annual Rate": {"number": l["rate"]},
                    "月還款 / Monthly Payment": {"number": l["payment"]},
                    "到期日 / Due Date": {"date": {"start": l["due"]}},
                    "說明 / Notes": {"rich_text": [{"text": {"content": l["notes"]}}]},
                },
            },
        )
        sleep()
        print(f"    + 負債: {l['name']}")


def seed_snapshots(db_id: str):
    base = date.today()
    for i in range(7, -1, -1):
        d = base - relativedelta(months=i)
        label = f"{d.year}-{d.month:02d}"
        step = 7 - i
        assets = 13_250_000 + step * 40_000
        liab = 3_680_000 - step * 20_000
        net = assets - liab
        income = 200_200 if d.month == 9 else 43_000
        expenses = 46_870
        cashflow = income - expenses
        api(
            "POST",
            "/pages",
            {
                "parent": {"database_id": db_id},
                "properties": {
                    "月份 / Month": {"title": [{"text": {"content": label}}]},
                    "總資產 / Total Assets": {"number": assets},
                    "總負債 / Total Liabilities": {"number": liab},
                    "淨值 / Net Worth": {"number": net},
                    "月收入 / Monthly Income": {"number": income},
                    "月支出 / Monthly Expenses": {"number": expenses},
                    "月結餘 / Net Cash Flow": {"number": cashflow},
                    "備註 / Notes": {
                        "rich_text": [
                            {"text": {"content": "📊 示範資料 / Sample Data"}}
                        ]
                    },
                },
            },
        )
        sleep()
        print(f"    + 快照: {label}  淨值 {net:,}")


# ── Dashboard builder ──────────────────────────────────────────────────────────


def _placeholder_col():
    """Column with a single space paragraph (Notion requires non-empty columns)"""
    return {
        "type": "column",
        "column": {
            "children": [
                {
                    "type": "paragraph",
                    "paragraph": {"rich_text": [txt(" ")]},
                }
            ]
        },
    }


def _fill_column(col_id: str, blocks: list):
    """Replace placeholder in column with real content blocks."""
    children = api("GET", f"/blocks/{col_id}/children").get("results", [])
    # Add real content first (column must never be empty)
    api("PATCH", f"/blocks/{col_id}/children", {"children": blocks})
    sleep()
    # Delete placeholder(s)
    for child in children:
        api("DELETE", f"/blocks/{child['id']}")
        sleep()


def _callout(emoji, title_zh, title_en, desc_zh, desc_en, color):
    return {
        "type": "callout",
        "callout": {
            "rich_text": [
                txt(f"{title_zh}  ·  {title_en}\n", bold=True),
                txt(f"{desc_zh}\n{desc_en}", italic=True, color="gray"),
            ],
            "icon": {"type": "emoji", "emoji": emoji},
            "color": color,
        },
    }


def build_dashboard(root_id: str):
    print("  → 建立儀表板區塊 / Building dashboard blocks...")

    # ── Phase 1: top-level blocks (no deep nesting) ────────────────────────────
    api(
        "PATCH",
        f"/blocks/{root_id}/children",
        {
            "children": [
                {
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            txt(
                                "個人財務作業系統  ·  自動更新  ·  Auto-Updated Monthly  ·  v2.0",
                                italic=True,
                                color="gray",
                            )
                        ]
                    },
                },
                {"type": "divider", "divider": {}},
                {
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [txt("📊 現況速覽  ·  Current Snapshot")]
                    },
                },
            ]
        },
    )
    sleep()

    # ── Phase 2: Metric row 1 (3 columns) ─────────────────────────────────────
    r1 = api(
        "PATCH",
        f"/blocks/{root_id}/children",
        {
            "children": [
                {
                    "type": "column_list",
                    "column_list": {
                        "children": [
                            _placeholder_col(),
                            _placeholder_col(),
                            _placeholder_col(),
                        ]
                    },
                }
            ]
        },
    )
    sleep()
    cl1_id = r1["results"][0]["id"]
    cols1 = api("GET", f"/blocks/{cl1_id}/children")["results"]

    metric_callouts = [
        (
            "📈",
            "淨資產",
            "Net Worth",
            "查看月度快照最新一筆",
            "See latest Monthly Snapshot",
            "yellow_background",
        ),
        (
            "💰",
            "總資產",
            "Total Assets",
            "查看資產明細合計",
            "Sum of all asset values",
            "orange_background",
        ),
        (
            "💳",
            "總負債",
            "Total Liabilities",
            "查看負債明細合計",
            "Sum of all balances",
            "brown_background",
        ),
    ]
    for col, (emoji, zh, en, desc_zh, desc_en, color) in zip(cols1, metric_callouts):
        _fill_column(col["id"], [_callout(emoji, zh, en, desc_zh, desc_en, color)])

    # ── Phase 3: Metric row 2 (3 columns) ─────────────────────────────────────
    r2 = api(
        "PATCH",
        f"/blocks/{root_id}/children",
        {
            "children": [
                {
                    "type": "column_list",
                    "column_list": {
                        "children": [
                            _placeholder_col(),
                            _placeholder_col(),
                            _placeholder_col(),
                        ]
                    },
                }
            ]
        },
    )
    sleep()
    cl2_id = r2["results"][0]["id"]
    cols2 = api("GET", f"/blocks/{cl2_id}/children")["results"]

    row2_callouts = [
        (
            "💹",
            "儲蓄率",
            "Savings Rate",
            "月結餘 ÷ 月收入",
            "Net Cash Flow ÷ Income",
            "green_background",
        ),
        (
            "🤖",
            "自動更新",
            "Auto-Updated",
            "每月 1 日 08:00 執行",
            "Runs on 1st of each month",
            "gray_background",
        ),
        (
            "✏️",
            "手動待填",
            "Manual Fields",
            "佣金、日常生活費",
            "Commissions, Daily expenses",
            "pink_background",
        ),
    ]
    for col, (emoji, zh, en, desc_zh, desc_en, color) in zip(cols2, row2_callouts):
        _fill_column(col["id"], [_callout(emoji, zh, en, desc_zh, desc_en, color)])

    # ── Phase 4: Chart guide + Automation info ─────────────────────────────────
    api(
        "PATCH",
        f"/blocks/{root_id}/children",
        {
            "children": [
                {"type": "divider", "divider": {}},
                {
                    "type": "heading_2",
                    "heading_2": {"rich_text": [txt("📈 圖表設定  ·  Chart Setup")]},
                },
                {
                    "type": "callout",
                    "callout": {
                        "rich_text": [
                            txt(
                                "Notion 原生圖表建立步驟  ·  How to create charts\n\n",
                                bold=True,
                            ),
                            txt(
                                "1. 開啟「月度快照」資料庫  /  Open Monthly Snapshot database\n"
                            ),
                            txt("2. 右上角「+ Add view」→ 選「Chart」\n"),
                            txt(
                                "3. 淨值趨勢：X = 月份  Y = 淨值  /  Net Worth trend: X = Month, Y = Net Worth\n"
                            ),
                            txt("4. 資產對比：加入「總資產」「總負債」到 Y 軸\n"),
                            txt(
                                "5. 儲蓄率：Y = 儲蓄率  /  Savings Rate: Y = Savings Rate %"
                            ),
                        ],
                        "icon": {"type": "emoji", "emoji": "💡"},
                        "color": "blue_background",
                    },
                },
                {"type": "divider", "divider": {}},
                {
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [txt("⚙️ 自動化說明  ·  Automation Info")]
                    },
                },
                {
                    "type": "callout",
                    "callout": {
                        "rich_text": [
                            txt("自動更新項目 / Auto-updated fields\n", bold=True),
                            txt("✅ 黃金存摺餘額（每月投入自動累計）\n"),
                            txt("✅ 信貸剩餘本金（攤還公式精確計算）\n"),
                            txt("✅ 月度快照（自動建立，避免重複）\n\n"),
                            txt("手動填寫 / Fill manually\n", bold=True),
                            txt("✏️ 佣金收入  ✏️ 日常生活費  ✏️ 房產估值（每年）"),
                        ],
                        "icon": {"type": "emoji", "emoji": "🤖"},
                        "color": "yellow_background",
                    },
                },
                {"type": "divider", "divider": {}},
                {
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            txt(
                                "🤖 Powered by GitHub Actions  ·  Personal Finance OS v2.0  ·  查看 Quick Start Guide ↓",
                                italic=True,
                                color="gray",
                            )
                        ]
                    },
                },
            ]
        },
    )
    sleep()
    print("  ✅ 儀表板完成 / Dashboard built")


# ── Setup Guide page ──────────────────────────────────────────────────────────


def create_guide_page(parent_id: str) -> str:
    page = api(
        "POST",
        "/pages",
        {
            "parent": {"page_id": parent_id},
            "icon": {"type": "emoji", "emoji": "📖"},
            "properties": {
                "title": {
                    "title": [
                        {
                            "type": "text",
                            "text": {
                                "content": "📖 Quick Start Guide  ·  快速上手指南"
                            },
                        }
                    ]
                }
            },
        },
    )
    sleep()
    page_id = page["id"]

    guide_blocks = [
        {
            "type": "callout",
            "callout": {
                "rich_text": [
                    txt(
                        "本模板包含完整自動化腳本，搭配 GitHub Actions 免費運行。\n",
                        bold=True,
                    ),
                    txt(
                        "This template includes a full automation script that runs free on GitHub Actions."
                    ),
                ],
                "icon": {"type": "emoji", "emoji": "🎯"},
                "color": "yellow_background",
            },
        },
        {"type": "divider", "divider": {}},
        {
            "type": "heading_2",
            "heading_2": {
                "rich_text": [txt("Step 1 — 複製模板  ·  Duplicate Template")]
            },
        },
        {
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": [
                    txt("點擊右上角「Duplicate」複製整個模板到你的 Notion workspace")
                ]
            },
        },
        {
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": [
                    txt(
                        "記錄三個資料庫的 ID（網址列 32 碼）/ Note the 3 database IDs from the URL"
                    )
                ]
            },
        },
        {"type": "divider", "divider": {}},
        {
            "type": "heading_2",
            "heading_2": {
                "rich_text": [
                    txt("Step 2 — 設定參數  ·  Configure finance_config.json")
                ]
            },
        },
        {
            "type": "code",
            "code": {
                "rich_text": [
                    txt(
                        "# 複製範本 / Copy template\ncp finance_config.json.template finance_config.json\n\n# 填入你的資料 / Fill in your values:\n# - notion.assets_db_id\n# - notion.liabilities_db_id  \n# - notion.snapshot_db_id\n# - gold_savings.initial_value / initial_date\n# - personal_loan.principal / start_date / annual_rate / monthly_payment\n# - income.monthly_base\n# - fixed_expenses (每項固定支出)"
                    )
                ],
                "language": "bash",
            },
        },
        {"type": "divider", "divider": {}},
        {
            "type": "heading_2",
            "heading_2": {
                "rich_text": [txt("Step 3 — 設定 GitHub Actions  ·  Setup Automation")]
            },
        },
        {
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": [
                    txt("Fork 或 clone 程式庫 / Fork or clone the repository")
                ]
            },
        },
        {
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": [
                    txt(
                        "在 GitHub Settings → Secrets 新增 NOTION_TOKEN / Add NOTION_TOKEN to GitHub Secrets"
                    )
                ]
            },
        },
        {
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": [
                    txt(
                        "上傳 finance_config.json（不進 git）或改用環境變數 / Upload config or use env vars"
                    )
                ]
            },
        },
        {
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": [
                    txt(
                        "啟用 .github/workflows/finance_monthly.yml / Enable the workflow"
                    )
                ]
            },
        },
        {
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": [
                    txt(
                        "每月 1 日 08:00（台灣）自動執行 / Runs automatically at 08:00 TWN on 1st of each month"
                    )
                ]
            },
        },
        {"type": "divider", "divider": {}},
        {
            "type": "heading_2",
            "heading_2": {
                "rich_text": [txt("Step 4 — 建立圖表  ·  Create Charts in Notion")]
            },
        },
        {
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [txt("月度快照 → Add view → Chart → 淨值趨勢線圖")]
            },
        },
        {
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [
                    txt("月度快照 → Add view → Chart → 總資產 vs 總負債 長條圖")
                ]
            },
        },
        {
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [txt("資產明細 → Add view → Chart → 類別 Pie Chart")]
            },
        },
        {"type": "divider", "divider": {}},
        {
            "type": "heading_2",
            "heading_2": {"rich_text": [txt("每月工作流程  ·  Monthly Workflow")]},
        },
        {
            "type": "callout",
            "callout": {
                "rich_text": [
                    txt("每月 1 日流程 / Monthly routine\n\n"),
                    txt("🤖 自動：黃金存摺、信貸餘額更新 + 月度快照建立\n"),
                    txt("✏️ 手動（3 分鐘）：開啟快照 → 填入佣金收入 + 日常生活費"),
                ],
                "icon": {"type": "emoji", "emoji": "📅"},
                "color": "green_background",
            },
        },
    ]

    api("PATCH", f"/blocks/{page_id}/children", {"children": guide_blocks})
    sleep()
    print("  ✅ 快速上手指南建立 / Setup guide created")
    return page_id


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Create Personal Finance OS template in Notion"
    )
    parser.add_argument(
        "--parent-id",
        default=os.environ.get("NOTION_PARENT_ID"),
        help="Parent Notion page ID",
    )
    args = parser.parse_args()

    if not args.parent_id:
        print("❌ 請提供 parent page ID:")
        print("   NOTION_PARENT_ID=<id> python3 finance/create_commercial_template.py")
        print("   python3 finance/create_commercial_template.py --parent-id <id>")
        sys.exit(1)

    parent_id = args.parent_id.replace("-", "")

    print("=" * 55)
    print("Personal Finance OS v2.0 — Template Creator")
    print("=" * 55)

    # 1. Root page
    print("\n[1/6] 建立根頁面 / Creating root page...")
    root = api(
        "POST",
        "/pages",
        {
            "parent": {"page_id": parent_id},
            "icon": {"type": "emoji", "emoji": "💼"},
            "cover": {
                "type": "external",
                "external": {
                    "url": "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=1500&q=80"
                },
            },
            "properties": {
                "title": {
                    "title": [
                        {
                            "type": "text",
                            "text": {
                                "content": "💼 Personal Finance OS  ·  個人財務作業系統"
                            },
                        }
                    ]
                }
            },
        },
    )
    sleep()
    root_id = root["id"]
    root_url = root.get("url", f"https://notion.so/{root_id.replace('-','')}")
    print(f"  ✅ 根頁面 ID: {root_id}")

    # 2. Databases
    print("\n[2/6] 建立資料庫 / Creating databases...")
    assets_id = create_assets_db(root_id)
    print(f"  ✅ 資產明細 DB: {assets_id}")
    liab_id = create_liabilities_db(root_id)
    print(f"  ✅ 負債明細 DB: {liab_id}")
    snap_id = create_snapshot_db(root_id)
    print(f"  ✅ 月度快照 DB: {snap_id}")

    # 3. Sample data
    print("\n[3/6] 填入示範資產 / Seeding assets...")
    seed_assets(assets_id)

    print("\n[4/6] 填入示範負債 / Seeding liabilities...")
    seed_liabilities(liab_id)

    print("\n[5/6] 填入 8 個月快照 / Seeding 8-month snapshots...")
    seed_snapshots(snap_id)

    # 4. Dashboard content
    print("\n[6/6] 建立儀表板 + 指南 / Building dashboard + guide...")
    build_dashboard(root_id)
    create_guide_page(root_id)

    # Output summary
    print("\n" + "=" * 55)
    print("✅ 模板建立完成 / Template created successfully!")
    print(f"\n🔗 開啟 / Open: {root_url}")
    print("\n📋 資料庫 IDs（填入 finance_config.json）:")
    print(f"   assets_db_id:      {assets_id}")
    print(f"   liabilities_db_id: {liab_id}")
    print(f"   snapshot_db_id:    {snap_id}")
    print("\n下一步 / Next steps:")
    print("  1. 複製上方 DB IDs 到 finance_config.json")
    print("  2. 填入你的真實財務參數")
    print("  3. 在 Notion 月度快照中新增 Chart view")
    print("  4. 設定 GitHub Actions（詳見 Quick Start Guide）")
    print("=" * 55)


if __name__ == "__main__":
    main()
