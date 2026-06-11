#!/usr/bin/env python3
"""
create_template.py — 建立 Personal Finance OS 公開範本頁面
使用示範資料，建立可分享的 Notion 範本連結

執行：python3 finance/create_template.py
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import date

_LOCAL_SECRETS = os.path.expanduser("~/.config/notion_token")
if os.environ.get("NOTION_TOKEN"):
    TOKEN = os.environ["NOTION_TOKEN"]
elif os.path.exists(_LOCAL_SECRETS):
    TOKEN = open(_LOCAL_SECRETS).read().strip()
else:
    raise RuntimeError(
        "NOTION_TOKEN 未設定，請設定環境變數或建立 ~/.config/notion_token"
    )

# ── 示範資料（一般上班族樣板）────────────────────────────────────────────────
SAMPLE_ASSETS = [
    {"name": "自有住宅", "value": 8_000_000, "cost": 6_500_000, "cat": "不動產"},
    {
        "name": "元大台灣50 ETF (0050)",
        "value": 2_175_000,
        "cost": 1_800_000,
        "cat": "股票",
    },
    {"name": "臺銀定期存款", "value": 500_000, "cost": 500_000, "cat": "存款"},
    {"name": "儲蓄型保險", "value": 320_000, "cost": 300_000, "cat": "保險"},
    {"name": "現金 / 活存", "value": 80_000, "cost": 80_000, "cat": "現金"},
]

SAMPLE_LIABILITIES = [
    {
        "name": "房屋貸款",
        "original": 6_000_000,
        "balance": 4_500_000,
        "rate": 1.6,
        "payment": 26_000,
        "due": "2042-01-01",
        "cat": "房貸",
        "status": "還款中",
    }
]

SAMPLE_SNAPSHOTS = [
    {
        "month": "26-01",
        "assets": 10_800_000,
        "liab": 4_600_000,
        "net": 6_200_000,
        "income": 85_000,
        "expenses": 74_000,
        "cashflow": 11_000,
    },
    {
        "month": "26-02",
        "assets": 10_850_000,
        "liab": 4_574_000,
        "net": 6_276_000,
        "income": 85_000,
        "expenses": 71_000,
        "cashflow": 14_000,
    },
    {
        "month": "26-03",
        "assets": 10_920_000,
        "liab": 4_548_000,
        "net": 6_372_000,
        "income": 85_000,
        "expenses": 68_000,
        "cashflow": 17_000,
    },
    {
        "month": "26-04",
        "assets": 11_000_000,
        "liab": 4_522_000,
        "net": 6_478_000,
        "income": 85_000,
        "expenses": 73_000,
        "cashflow": 12_000,
    },
    {
        "month": "26-05",
        "assets": 11_075_000,
        "liab": 4_500_000,
        "net": 6_575_000,
        "income": 85_000,
        "expenses": 72_000,
        "cashflow": 13_000,
    },
]

MONTHLY_INCOME = 85_000
MONTHLY_EXPENSES = 72_000
MONTHLY_SURPLUS = MONTHLY_INCOME - MONTHLY_EXPENSES
SAVINGS_RATE = MONTHLY_SURPLUS / MONTHLY_INCOME * 100


# ── Notion API ────────────────────────────────────────────────────────────────
def api(method, path, body=None):
    url = f"https://api.notion.com/v1{path}"
    data = json.dumps(body, ensure_ascii=False).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  ❌ API error {e.code}: {e.read().decode()}")
        raise


def rt(text, bold=False, color=None):
    obj = {"type": "text", "text": {"content": text}}
    if bold or color:
        ann = {}
        if bold:
            ann["bold"] = True
        if color:
            ann["color"] = color
        obj["annotations"] = ann
    return obj


# ── 建立資料庫 ────────────────────────────────────────────────────────────────
def create_assets_db(parent_id):
    print("  建立 Assets 資產明細 DB...")
    return api(
        "POST",
        "/databases",
        {
            "parent": {"type": "page_id", "page_id": parent_id},
            "title": [{"type": "text", "text": {"content": "Assets · 資產明細"}}],
            "icon": {"type": "emoji", "emoji": "💼"},
            "properties": {
                "項目名稱 / Asset Name": {"title": {}},
                "類別 / Category": {
                    "select": {
                        "options": [
                            {"name": "不動產", "color": "brown"},
                            {"name": "股票", "color": "blue"},
                            {"name": "存款", "color": "green"},
                            {"name": "保險", "color": "purple"},
                            {"name": "現金", "color": "yellow"},
                            {"name": "股權", "color": "red"},
                            {"name": "其他", "color": "gray"},
                        ]
                    }
                },
                "成本 / Cost Basis": {"number": {"format": "number"}},
                "當前金額 / Current Value": {"number": {"format": "number"}},
                "損益 / Gain-Loss": {
                    "formula": {
                        "expression": 'prop("當前金額 / Current Value") - prop("成本 / Cost Basis")'
                    }
                },
                "報酬率 / ROI %": {
                    "formula": {
                        "expression": 'round((prop("當前金額 / Current Value") - prop("成本 / Cost Basis")) / prop("成本 / Cost Basis") * 1000) / 10'
                    }
                },
                "自動更新 / Auto Updated": {"checkbox": {}},
                "上次更新 / Last Updated": {"date": {}},
                "說明 / Notes": {"rich_text": {}},
            },
        },
    )


def create_liabilities_db(parent_id):
    print("  建立 Liabilities 負債明細 DB...")
    return api(
        "POST",
        "/databases",
        {
            "parent": {"type": "page_id", "page_id": parent_id},
            "title": [{"type": "text", "text": {"content": "Liabilities · 負債明細"}}],
            "icon": {"type": "emoji", "emoji": "💳"},
            "properties": {
                "項目名稱 / Liability Name": {"title": {}},
                "類別 / Category": {
                    "select": {
                        "options": [
                            {"name": "房貸", "color": "red"},
                            {"name": "車貸", "color": "orange"},
                            {"name": "信貸", "color": "yellow"},
                            {"name": "信用卡", "color": "pink"},
                            {"name": "其他", "color": "gray"},
                        ]
                    }
                },
                "原始金額 / Original Amount": {"number": {"format": "number"}},
                "餘額 / Balance": {"number": {"format": "number"}},
                "年利率 / Annual Rate": {"number": {"format": "percent"}},
                "月還款 / Monthly Payment": {"number": {"format": "number"}},
                "還款進度 / Paydown %": {
                    "formula": {
                        "expression": 'round((prop("原始金額 / Original Amount") - prop("餘額 / Balance")) / prop("原始金額 / Original Amount") * 1000) / 10'
                    }
                },
                "到期日 / Due Date": {"date": {}},
                "狀態 / Status": {
                    "select": {
                        "options": [
                            {"name": "還款中", "color": "yellow"},
                            {"name": "已結清", "color": "green"},
                        ]
                    }
                },
                "說明 / Notes": {"rich_text": {}},
            },
        },
    )


def create_snapshot_db(parent_id):
    print("  建立 Monthly Snapshot 月度快照 DB...")
    return api(
        "POST",
        "/databases",
        {
            "parent": {"type": "page_id", "page_id": parent_id},
            "title": [
                {"type": "text", "text": {"content": "Monthly Snapshot · 月度快照"}}
            ],
            "icon": {"type": "emoji", "emoji": "📅"},
            "properties": {
                "月份 / Month": {"title": {}},
                "總資產 / Total Assets": {"number": {"format": "number"}},
                "總負債 / Total Liabilities": {"number": {"format": "number"}},
                "淨值 / Net Worth": {"number": {"format": "number"}},
                "月收入 / Monthly Income": {"number": {"format": "number"}},
                "月支出 / Monthly Expenses": {"number": {"format": "number"}},
                "月結餘 / Net Cash Flow": {"number": {"format": "number"}},
                "儲蓄率 / Savings Rate": {
                    "formula": {
                        "expression": 'round(prop("月結餘 / Net Cash Flow") / prop("月收入 / Monthly Income") * 1000) / 10'
                    }
                },
            },
        },
    )


# ── 填入示範資料 ──────────────────────────────────────────────────────────────
def seed_assets(db_id):
    print("  填入資產示範資料...")
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
                    "成本 / Cost Basis": {"number": a["cost"]},
                    "當前金額 / Current Value": {"number": a["value"]},
                    "上次更新 / Last Updated": {"date": {"start": today}},
                },
            },
        )


def seed_liabilities(db_id):
    print("  填入負債示範資料...")
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
                    "原始金額 / Original Amount": {"number": l["original"]},
                    "餘額 / Balance": {"number": l["balance"]},
                    "年利率 / Annual Rate": {"number": l["rate"] / 100},
                    "月還款 / Monthly Payment": {"number": l["payment"]},
                    "到期日 / Due Date": {"date": {"start": l["due"]}},
                    "狀態 / Status": {"select": {"name": l["status"]}},
                },
            },
        )


def seed_snapshots(db_id):
    print("  填入月度快照示範資料...")
    for s in SAMPLE_SNAPSHOTS:
        api(
            "POST",
            "/pages",
            {
                "parent": {"database_id": db_id},
                "properties": {
                    "月份 / Month": {"title": [{"text": {"content": s["month"]}}]},
                    "總資產 / Total Assets": {"number": s["assets"]},
                    "總負債 / Total Liabilities": {"number": s["liab"]},
                    "淨值 / Net Worth": {"number": s["net"]},
                    "月收入 / Monthly Income": {"number": s["income"]},
                    "月支出 / Monthly Expenses": {"number": s["expenses"]},
                    "月結餘 / Net Cash Flow": {"number": s["cashflow"]},
                },
            },
        )


# ── 建立首頁 blocks ────────────────────────────────────────────────────────────
def col(children):
    """Notion column block：children 放在 column 物件內。"""
    return {"type": "column", "column": {"children": children}}


def collist(columns):
    """Notion column_list：children（column blocks）放在 column_list 物件內。"""
    return {"type": "column_list", "column_list": {"children": columns}}


def build_homepage(page_id, assets_db_id, liab_db_id, snap_db_id):
    """首頁內容，使用 collist/col helper 確保格式正確。"""
    print("  建立首頁內容...")

    total_assets = sum(a["value"] for a in SAMPLE_ASSETS)
    total_liab = SAMPLE_LIABILITIES[0]["balance"]
    net_worth = total_assets - total_liab
    liab = SAMPLE_LIABILITIES[0]
    progress = (liab["original"] - liab["balance"]) / liab["original"] * 100
    today_str = date.today().strftime("%Y-%m")

    cat_totals = {}
    for a in SAMPLE_ASSETS:
        cat_totals[a["cat"]] = cat_totals.get(a["cat"], 0) + a["value"]
    sorted_cats = sorted(cat_totals.items(), key=lambda x: -x[1])
    alloc = "  ·  ".join(f"{c} {v/total_assets*100:.1f}%" for c, v in sorted_cats[:4])

    surplus_fmt = (
        f"NT${MONTHLY_SURPLUS:,}"
        if MONTHLY_SURPLUS >= 0
        else f"-NT${abs(MONTHLY_SURPLUS):,}"
    )
    liab_text = (
        f"{liab['name']}\n"
        f"餘額  NT${liab['balance']:,}\n"
        f"還款進度  {progress:.1f}%\n"
        f"到期  {liab['due'].replace('-', '/')}"
    )

    # ── 組 col1 資產列表 ──
    col1_children = [
        {
            "object": "block",
            "type": "heading_3",
            "heading_3": {"rich_text": [rt("💼 資產帳戶")]},
        },
    ]
    for a in SAMPLE_ASSETS:
        col1_children += [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [rt(a["name"], bold=True)]},
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [rt(f"NT${a['value']:,}  ·  {a['cat']}", color="gray")]
                },
            },
        ]
    col1_children += [
        {"object": "block", "type": "divider", "divider": {}},
        {
            "object": "block",
            "type": "link_to_page",
            "link_to_page": {"type": "database_id", "database_id": assets_db_id},
        },
    ]

    # ── 一次性建立全部 blocks ──
    blocks = [
        # 標題段落
        # 標題
        {
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    rt("💰 Personal Finance OS｜個人財務作業系統", bold=True)
                ],
                "color": "brown_background",
            },
        },
        {"type": "divider", "divider": {}},
        # 主 4 欄
        collist(
            [
                col(
                    [  # 導覽
                        {
                            "type": "heading_3",
                            "heading_3": {"rich_text": [rt("🗂️ 資料庫")]},
                        },
                        {
                            "type": "link_to_page",
                            "link_to_page": {
                                "type": "database_id",
                                "database_id": assets_db_id,
                            },
                        },
                        {
                            "type": "link_to_page",
                            "link_to_page": {
                                "type": "database_id",
                                "database_id": liab_db_id,
                            },
                        },
                        {
                            "type": "link_to_page",
                            "link_to_page": {
                                "type": "database_id",
                                "database_id": snap_db_id,
                            },
                        },
                    ]
                ),
                col(col1_children),  # 資產列表
                col(
                    [  # 總資產概覽
                        {
                            "type": "heading_3",
                            "heading_3": {"rich_text": [rt("📊 總資產概覽")]},
                        },
                        {
                            "type": "callout",
                            "callout": {
                                "rich_text": [
                                    rt(
                                        f"NT${total_assets:,}\n淨值  NT${net_worth:,}",
                                        bold=True,
                                    )
                                ],
                                "icon": {"type": "emoji", "emoji": "📈"},
                                "color": "yellow_background",
                            },
                        },
                        {
                            "type": "paragraph",
                            "paragraph": {"rich_text": [rt("資產配置", bold=True)]},
                        },
                        {
                            "type": "paragraph",
                            "paragraph": {"rich_text": [rt(alloc, color="gray")]},
                        },
                    ]
                ),
                col(
                    [  # 負債狀況
                        {
                            "type": "heading_3",
                            "heading_3": {"rich_text": [rt("💳 負債狀況")]},
                        },
                        {
                            "type": "callout",
                            "callout": {
                                "rich_text": [rt(liab_text)],
                                "icon": {"type": "emoji", "emoji": "📉"},
                                "color": "red_background",
                            },
                        },
                        {
                            "type": "paragraph",
                            "paragraph": {"rich_text": [rt("月還款", bold=True)]},
                        },
                        {
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [
                                    rt(
                                        f"NT${liab['payment']:,}  ·  年利 {liab['rate']}%",
                                        color="gray",
                                    )
                                ]
                            },
                        },
                        {"type": "divider", "divider": {}},
                        {
                            "type": "link_to_page",
                            "link_to_page": {
                                "type": "database_id",
                                "database_id": liab_db_id,
                            },
                        },
                    ]
                ),
            ]
        ),
        {"type": "divider", "divider": {}},
        {
            "type": "heading_2",
            "heading_2": {"rich_text": [rt(f"📅 本月財務指標  ·  {today_str}")]},
        },
        # 月財務指標 4 欄
        collist(
            [
                col(
                    [
                        {
                            "type": "callout",
                            "callout": {
                                "rich_text": [
                                    rt(f"💰 月收入\nNT${MONTHLY_INCOME:,}", bold=True)
                                ],
                                "icon": {"type": "emoji", "emoji": "📌"},
                                "color": "green_background",
                            },
                        }
                    ]
                ),
                col(
                    [
                        {
                            "type": "callout",
                            "callout": {
                                "rich_text": [
                                    rt(f"💸 月支出\nNT${MONTHLY_EXPENSES:,}", bold=True)
                                ],
                                "icon": {"type": "emoji", "emoji": "📌"},
                                "color": "orange_background",
                            },
                        }
                    ]
                ),
                col(
                    [
                        {
                            "type": "callout",
                            "callout": {
                                "rich_text": [
                                    rt(f"📊 月結餘\n{surplus_fmt}", bold=True)
                                ],
                                "icon": {"type": "emoji", "emoji": "📌"},
                                "color": "blue_background",
                            },
                        }
                    ]
                ),
                col(
                    [
                        {
                            "type": "callout",
                            "callout": {
                                "rich_text": [
                                    rt(f"🎯 儲蓄率\n{SAVINGS_RATE:.1f}%", bold=True)
                                ],
                                "icon": {"type": "emoji", "emoji": "📌"},
                                "color": "purple_background",
                            },
                        }
                    ]
                ),
            ]
        ),
        {"type": "divider", "divider": {}},
        {
            "type": "callout",
            "callout": {
                "rich_text": [
                    rt(
                        "每月自動（1日）：更新股票/黃金現價 → 建立月度快照 → 刷新圖表\n每月手動（5分鐘）：更新收入 · 更新日常支出"
                    )
                ],
                "icon": {"type": "emoji", "emoji": "🤖"},
                "color": "gray_background",
            },
        },
    ]

    api("PATCH", f"/blocks/{page_id}/children", {"children": blocks})
    print("  ✅ 首頁 blocks 建立完成")


# ── 建立 Quick Start Guide ────────────────────────────────────────────────────
def build_quick_start(parent_id):
    print("  建立 Quick Start Guide...")
    page = api(
        "POST",
        "/pages",
        {
            "parent": {"page_id": parent_id},
            "icon": {"type": "emoji", "emoji": "🚀"},
            "properties": {
                "title": {"title": [{"text": {"content": "🚀 Quick Start Guide"}}]}
            },
        },
    )
    pid = page["id"]

    api(
        "PATCH",
        f"/blocks/{pid}/children",
        {
            "children": [
                {
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {"rich_text": [rt("快速上手 · Quick Start")]},
                },
                {"object": "block", "type": "divider", "divider": {}},
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": [rt("Step 1：填入你的資產")]},
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            rt("開啟 "),
                            rt("Assets · 資產明細", bold=True),
                            rt(" 資料庫，刪除示範資料，填入你自己的資產。"),
                        ]
                    },
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            rt("項目名稱：資產名稱（例：自有住宅、0050 ETF）")
                        ]
                    },
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": [rt("成本：當初買入金額")]},
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [rt("當前金額：目前市值（股票可設定自動更新）")]
                    },
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [
                            rt("類別：不動產 / 股票 / 存款 / 保險 / 現金 / 其他")
                        ]
                    },
                },
                {"object": "block", "type": "divider", "divider": {}},
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": [rt("Step 2：填入你的負債")]},
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            rt("開啟 "),
                            rt("Liabilities · 負債明細", bold=True),
                            rt("，填入房貸、信貸等負債。"),
                        ]
                    },
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": [rt("原始金額：借款總額")]},
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": [rt("餘額：目前剩餘未還金額")]},
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": [rt("還款進度由系統自動計算")]},
                },
                {"object": "block", "type": "divider", "divider": {}},
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": [rt("Step 3：建立第一筆月度快照")]},
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            rt("開啟 "),
                            rt("Monthly Snapshot · 月度快照", bold=True),
                            rt("，新增一筆本月資料。"),
                        ]
                    },
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [rt("月份格式：YY-MM（例：26-05）")]
                    },
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [rt("填入本月總資產、總負債、收入、支出")]
                    },
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [rt("儲蓄率 / 淨值 / 月結餘 自動計算")]
                    },
                },
                {"object": "block", "type": "divider", "divider": {}},
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": [rt("🔧 進階版（含自動化）")]},
                },
                {
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [
                            rt(
                                "進階版包含 Python 腳本 + GitHub Actions，可自動：\n• 每天抓股票現價更新資產\n• 每月1日自動建立快照\n• 每月刷新 Notion 首頁數字\n\n詳見隨附 README.md"
                            )
                        ],
                        "icon": {"type": "emoji", "emoji": "⚡"},
                        "color": "blue_background",
                    },
                },
            ]
        },
    )
    return pid


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("Personal Finance OS — 建立商業範本頁面")
    print("=" * 60)

    # 1. 建立主頁面（放在與 Personal Finance OS 同層）
    PARENT_PAGE_ID = "369f4149-a6aa-81c8-9a6b-c2cb475ca097"
    print("\n[1/5] 建立主頁面...")
    main_page = api(
        "POST",
        "/pages",
        {
            "parent": {"type": "page_id", "page_id": PARENT_PAGE_ID},
            "icon": {"type": "emoji", "emoji": "💰"},
            "cover": {
                "type": "external",
                "external": {
                    "url": "https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=1200"
                },
            },
            "properties": {
                "title": {
                    "title": [
                        {
                            "type": "text",
                            "text": {
                                "content": "💰 Personal Finance OS｜個人財務作業系統"
                            },
                        }
                    ]
                }
            },
        },
    )
    main_id = main_page["id"]
    print(f"  ✅ 主頁面 ID: {main_id}")

    # 2. 建立三個資料庫
    print("\n[2/5] 建立資料庫...")
    assets_db = create_assets_db(main_id)
    liab_db = create_liabilities_db(main_id)
    snapshot_db = create_snapshot_db(main_id)
    assets_db_id = assets_db["id"]
    liab_db_id = liab_db["id"]
    snapshot_db_id = snapshot_db["id"]
    print(f"  ✅ Assets DB:   {assets_db_id}")
    print(f"  ✅ Liabilities: {liab_db_id}")
    print(f"  ✅ Snapshot:    {snapshot_db_id}")

    # 3. 填入示範資料
    print("\n[3/5] 填入示範資料...")
    seed_assets(assets_db_id)
    seed_liabilities(liab_db_id)
    seed_snapshots(snapshot_db_id)
    print("  ✅ 示範資料填入完成")

    # 4. 建立首頁 blocks
    print("\n[4/5] 建立首頁 blocks...")
    build_homepage(main_id, assets_db_id, liab_db_id, snapshot_db_id)
    build_quick_start(main_id)
    print("  ✅ 首頁與 Quick Start 完成")

    # 5. 輸出分享連結
    page_url = f"https://www.notion.so/{main_id.replace('-', '')}"
    print(
        f"""
[5/5] 完成！

  Notion 頁面：{page_url}

  ⚠️  接下來手動操作（30 秒）：
  1. 開啟上方連結
  2. 右上角 Share → Anyone with the link → Can view
  3. 勾選「Allow duplicate as template」（如有此選項）
  4. 複製連結 → 這就是你的範本銷售連結

  DB IDs（更新 finance_config.json 用）：
  assets_db_id:   {assets_db_id}
  liab_db_id:     {liab_db_id}
  snapshot_db_id: {snapshot_db_id}
"""
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
