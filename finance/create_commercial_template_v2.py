#!/usr/bin/env python3
"""
Personal Finance OS v2.1 — Notion Template Creator
個人財務作業系統 v2.1 — 商業模板生成器（全新重建版）

結構：
  💼 根頁面（導航 Hub）
  ├── 🏠 Dashboard      — KPI + 月度清單
  ├── 📈 Charts         — 3 張圖表專頁
  ├── 💰 Assets DB      — 資產明細（含損益 / ROI 公式）
  ├── 💳 Liabilities DB — 負債明細（含還款進度 / 狀態）
  ├── 📅 Snapshot DB    — 月度快照（含儲蓄率公式）
  └── 📖 Quick Start    — 步驟 + FAQ toggle

Usage:
    NOTION_PARENT_ID=<page_id> python3 finance/create_commercial_template_v2.py
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date

from dateutil.relativedelta import relativedelta

# ── Token ─────────────────────────────────────────────────────────────────────


def _load_token():
    t = os.environ.get("NOTION_TOKEN")
    if t:
        return t
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
    raise RuntimeError("NOTION_TOKEN 未設定")


TOKEN = _load_token()
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

REPO = "lien2fish/liam-ai-agent"
BRANCH = "main"
CHART_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/finance/charts"


# ── API helpers ────────────────────────────────────────────────────────────────


def api(method, path, data=None, _retry=5):
    url = f"https://api.notion.com/v1{path}"
    body = json.dumps(data, ensure_ascii=False).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    for attempt in range(_retry):
        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503) and attempt < _retry - 1:
                wait = 2**attempt + 1
                print(f"  ⏳ {e.code} — 等待 {wait}s 後重試...")
                time.sleep(wait)
                continue
            err = {}
            try:
                err = json.loads(e.read())
            except Exception:
                pass
            print(f"  ❌ {e.code}: {err.get('message','')}")
            raise


def Z():  # rate-limit guard
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


# ── Page / sub-page helpers ────────────────────────────────────────────────────


def create_page(parent_id, emoji, title_text, cover_url=None):
    body = {
        "parent": {"page_id": parent_id},
        "icon": {"type": "emoji", "emoji": emoji},
        "properties": {
            "title": {"title": [{"type": "text", "text": {"content": title_text}}]}
        },
    }
    if cover_url:
        body["cover"] = {"type": "external", "external": {"url": cover_url}}
    p = api("POST", "/pages", body)
    Z()
    return p["id"]


def append_blocks(page_id, blocks):
    api("PATCH", f"/blocks/{page_id}/children", {"children": blocks})
    Z()


def _col_block(children):
    return {"type": "column", "column": {"children": children}}


def _callout(icon, rich_text_list, color="default"):
    return {
        "type": "callout",
        "callout": {
            "rich_text": rich_text_list,
            "icon": {"type": "emoji", "emoji": icon},
            "color": color,
        },
    }


def _h2(text):
    return {
        "type": "heading_2",
        "heading_2": {"rich_text": [txt(text)], "is_toggleable": False},
    }


def _h3(text):
    return {
        "type": "heading_3",
        "heading_3": {"rich_text": [txt(text)], "is_toggleable": False},
    }


def _p(rich_text_list):
    return {"type": "paragraph", "paragraph": {"rich_text": rich_text_list}}


def _div():
    return {"type": "divider", "divider": {}}


def _toggle(icon_text, summary, children_blocks):
    return {
        "type": "callout",
        "callout": {
            "rich_text": [txt(f"{icon_text}  {summary}", bold=True)],
            "icon": {"type": "emoji", "emoji": "▶"},
            "color": "gray_background",
        },
    }


def _image_block(url):
    return {"type": "image", "image": {"type": "external", "external": {"url": url}}}


def _link_to_page(page_id):
    return {
        "type": "link_to_page",
        "link_to_page": {"type": "page_id", "page_id": page_id},
    }


def _link_to_db(db_id):
    return {
        "type": "link_to_page",
        "link_to_page": {"type": "database_id", "database_id": db_id},
    }


# ── Fill column helper ────────────────────────────────────────────────────────


def _placeholder_col():
    return {"type": "column", "column": {"children": [_p([txt(" ")])]}}


def fill_column(col_id, blocks):
    """Replace placeholder content in a column with real blocks."""
    children = api("GET", f"/blocks/{col_id}/children").get("results", [])
    append_blocks(col_id, blocks)
    for c in children:
        api("DELETE", f"/blocks/{c['id']}")
        Z()


def add_column_list(page_id, col_contents):
    """Create a column_list with N columns, fill each from col_contents."""
    r = api(
        "PATCH",
        f"/blocks/{page_id}/children",
        {
            "children": [
                {
                    "type": "column_list",
                    "column_list": {
                        "children": [_placeholder_col() for _ in col_contents]
                    },
                }
            ]
        },
    )
    Z()
    cl_id = r["results"][0]["id"]
    cols = api("GET", f"/blocks/{cl_id}/children")["results"]
    for col, content_blocks in zip(cols, col_contents):
        fill_column(col["id"], content_blocks)


# ══════════════════════════════════════════════════════════════════════════════
# DATABASE SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

GOLD = "yellow"  # Notion colour names


def create_assets_db(parent_id):
    db = api(
        "POST",
        "/databases",
        {
            "parent": {"page_id": parent_id},
            "icon": {"type": "emoji", "emoji": "💰"},
            "title": [{"type": "text", "text": {"content": "💰 Assets  ·  資產明細"}}],
            "is_inline": False,
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
                "損益 / Gain-Loss": {
                    "formula": {
                        "expression": 'prop("當前金額 / Current Value") - prop("成本 / Cost Basis")'
                    }
                },
                "報酬率 / ROI %": {
                    "formula": {
                        "expression": (
                            'if(prop("成本 / Cost Basis") > 0, '
                            'round((prop("當前金額 / Current Value") - prop("成本 / Cost Basis")) '
                            '/ prop("成本 / Cost Basis") * 10000) / 100, 0)'
                        )
                    }
                },
                "上次更新 / Last Updated": {"date": {}},
                "自動更新 / Auto Updated": {"checkbox": {}},
                "說明 / Notes": {"rich_text": {}},
            },
        },
    )
    Z()
    return db["id"]


def create_liabilities_db(parent_id):
    db = api(
        "POST",
        "/databases",
        {
            "parent": {"page_id": parent_id},
            "icon": {"type": "emoji", "emoji": "💳"},
            "title": [
                {"type": "text", "text": {"content": "💳 Liabilities  ·  負債明細"}}
            ],
            "is_inline": False,
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
                "狀態 / Status": {
                    "select": {
                        "options": [
                            {"name": "正常 On Track", "color": "green"},
                            {"name": "警告 Warning", "color": "yellow"},
                            {"name": "完成 Paid Off", "color": "blue"},
                        ]
                    }
                },
                "餘額 / Balance": {"number": {"format": "number"}},
                "原始金額 / Original Amount": {"number": {"format": "number"}},
                "還款進度 / Paydown %": {
                    "formula": {
                        "expression": (
                            'if(prop("原始金額 / Original Amount") > 0, '
                            'round((prop("原始金額 / Original Amount") - prop("餘額 / Balance")) '
                            '/ prop("原始金額 / Original Amount") * 10000) / 100, 0)'
                        )
                    }
                },
                "年利率 / Annual Rate": {"number": {"format": "percent"}},
                "月還款 / Monthly Payment": {"number": {"format": "number"}},
                "到期日 / Due Date": {"date": {}},
                "說明 / Notes": {"rich_text": {}},
            },
        },
    )
    Z()
    return db["id"]


def create_snapshot_db(parent_id):
    db = api(
        "POST",
        "/databases",
        {
            "parent": {"page_id": parent_id},
            "icon": {"type": "emoji", "emoji": "📅"},
            "title": [
                {
                    "type": "text",
                    "text": {"content": "📅 Monthly Snapshot  ·  月度快照"},
                }
            ],
            "is_inline": False,
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
    Z()
    return db["id"]


# ══════════════════════════════════════════════════════════════════════════════
# SAMPLE DATA
# ══════════════════════════════════════════════════════════════════════════════

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
        "value": 302_000,
        "cost": 280_000,
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
        "name": "人壽保單 / Life Insurance",
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
        "status": "正常 On Track",
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
        "status": "正常 On Track",
        "notes": "✅ GitHub Actions 每月 1 日自動更新 / Auto-updated on 1st of each month",
    },
]


def seed_assets(db_id):
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
        Z()
        print(f"    + 資產: {a['name']}")


def seed_liabilities(db_id):
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
                    "狀態 / Status": {"select": {"name": l["status"]}},
                    "餘額 / Balance": {"number": l["balance"]},
                    "原始金額 / Original Amount": {"number": l["original"]},
                    "年利率 / Annual Rate": {"number": l["rate"]},
                    "月還款 / Monthly Payment": {"number": l["payment"]},
                    "到期日 / Due Date": {"date": {"start": l["due"]}},
                    "說明 / Notes": {"rich_text": [{"text": {"content": l["notes"]}}]},
                },
            },
        )
        Z()
        print(f"    + 負債: {l['name']}")


def seed_snapshots(db_id):
    base = date.today()
    for i in range(7, -1, -1):
        d = base - relativedelta(months=i)
        label = f"{d.year}-{d.month:02d}"
        step = 7 - i
        assets = 13_272_000 + step * 40_000
        liab = 3_680_000 - step * 20_000
        income = 200_200 if d.month == 9 else 43_000
        expenses = 46_870
        api(
            "POST",
            "/pages",
            {
                "parent": {"database_id": db_id},
                "properties": {
                    "月份 / Month": {"title": [{"text": {"content": label}}]},
                    "總資產 / Total Assets": {"number": assets},
                    "總負債 / Total Liabilities": {"number": liab},
                    "淨值 / Net Worth": {"number": assets - liab},
                    "月收入 / Monthly Income": {"number": income},
                    "月支出 / Monthly Expenses": {"number": expenses},
                    "月結餘 / Net Cash Flow": {"number": income - expenses},
                    "備註 / Notes": {
                        "rich_text": [
                            {"text": {"content": "📊 示範資料 / Sample Data"}}
                        ]
                    },
                },
            },
        )
        Z()
        print(f"    + 快照: {label}  淨值 {assets - liab:,}")


# ══════════════════════════════════════════════════════════════════════════════
# ROOT PAGE — Navigation Hub
# ══════════════════════════════════════════════════════════════════════════════


def build_root_nav(root_id, ids):
    """Build the root page navigation hub."""
    dashboard_id = ids["dashboard"]
    charts_id = ids["charts"]
    assets_id = ids["assets"]
    liab_id = ids["liab"]
    snap_id = ids["snap"]
    guide_id = ids["guide"]

    # ── subtitle ──
    append_blocks(
        root_id,
        [
            _p(
                [
                    txt(
                        "個人財務作業系統  ·  自動更新  ·  Bilingual Auto-Updated Template  ·  v2.1",
                        italic=True,
                        color="gray",
                    )
                ]
            ),
            _div(),
            _h2("🗂  導航  ·  Navigation"),
        ],
    )

    # ── Row 1: 3 nav cards ──
    nav_row1 = [
        [
            _callout(
                "🏠",
                [
                    txt("Dashboard  ·  儀表板\n", bold=True),
                    txt(
                        "KPI 指標 · 月度任務清單 · 自動化狀態",
                        italic=True,
                        color="gray",
                    ),
                ],
                "yellow_background",
            ),
            _link_to_page(dashboard_id),
        ],
        [
            _callout(
                "💰",
                [
                    txt("Assets  ·  資產明細\n", bold=True),
                    txt("資產總覽 · 損益計算 · 報酬率分析", italic=True, color="gray"),
                ],
                "orange_background",
            ),
            _link_to_db(assets_id),
        ],
        [
            _callout(
                "📅",
                [
                    txt("Monthly Snapshot  ·  月度快照\n", bold=True),
                    txt(
                        "8 個月趨勢 · 儲蓄率 · 每月自動建立", italic=True, color="gray"
                    ),
                ],
                "blue_background",
            ),
            _link_to_db(snap_id),
        ],
    ]
    add_column_list(root_id, nav_row1)

    # ── Row 2: 2 nav cards + 1 empty ──
    nav_row2 = [
        [
            _callout(
                "💳",
                [
                    txt("Liabilities  ·  負債明細\n", bold=True),
                    txt("還款進度 · 狀態追蹤 · 利率管理", italic=True, color="gray"),
                ],
                "red_background",
            ),
            _link_to_db(liab_id),
        ],
        [
            _callout(
                "📈",
                [
                    txt("Charts & Analytics  ·  圖表分析\n", bold=True),
                    txt(
                        "淨值趨勢 · 資產分佈 · 收支對比（每月自動更新）",
                        italic=True,
                        color="gray",
                    ),
                ],
                "green_background",
            ),
            _link_to_page(charts_id),
        ],
        [
            _callout(
                "📖",
                [
                    txt("Quick Start Guide  ·  快速上手\n", bold=True),
                    txt(
                        "5 步驟設定 · FAQ · GitHub Actions 教學",
                        italic=True,
                        color="gray",
                    ),
                ],
                "gray_background",
            ),
            _link_to_page(guide_id),
        ],
    ]
    add_column_list(root_id, nav_row2)

    # ── Automation status ──
    append_blocks(
        root_id,
        [
            _div(),
            _callout(
                "🤖",
                [
                    txt("自動化運作中  ·  Automation Active\n", bold=True),
                    txt("每月 1 日 08:00（台灣）GitHub Actions 自動執行：\n"),
                    txt("① 更新黃金存摺 & 信貸餘額  ② 建立月度快照  ③ 重新生成圖表"),
                ],
                "yellow_background",
            ),
            _div(),
            _p(
                [
                    txt(
                        "Personal Finance OS v2.1  ·  Powered by GitHub Actions  ·  © 2026 鉅鑫管理顧問",
                        italic=True,
                        color="gray",
                    )
                ]
            ),
        ],
    )
    print("  ✅ 根頁面導航完成")


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD PAGE
# ══════════════════════════════════════════════════════════════════════════════


def build_dashboard(page_id):
    """Build the Dashboard sub-page."""

    # ── Subtitle ──
    append_blocks(
        page_id,
        [
            _p(
                [
                    txt(
                        "即時財務概覽  ·  Real-Time Financial Overview",
                        italic=True,
                        color="gray",
                    )
                ]
            ),
            _div(),
            _h2("📊 KPI 總覽  ·  Key Metrics"),
            _p(
                [
                    txt(
                        "以下數字每月 1 日自動更新。請從「月度快照」資料庫查看最新一筆記錄獲取確切數字。",
                        italic=True,
                        color="gray",
                    )
                ]
            ),
        ],
    )

    # ── KPI Row 1: 4 cards ──
    kpi_row = [
        [
            _callout(
                "📈",
                [
                    txt("淨資產  ·  Net Worth\n", bold=True),
                    txt("= 總資產 − 總負債\n"),
                    txt("→ 查看月度快照最新一筆", italic=True, color="gray"),
                ],
                "yellow_background",
            )
        ],
        [
            _callout(
                "💰",
                [
                    txt("總資產  ·  Total Assets\n", bold=True),
                    txt("= 不動產 + 股權 + 投資 + 存款 + 保單\n"),
                    txt("→ 查看資產明細合計", italic=True, color="gray"),
                ],
                "orange_background",
            )
        ],
        [
            _callout(
                "💳",
                [
                    txt("總負債  ·  Total Liabilities\n", bold=True),
                    txt("= 房貸餘額 + 信貸餘額\n"),
                    txt("→ 查看負債明細合計", italic=True, color="gray"),
                ],
                "red_background",
            )
        ],
        [
            _callout(
                "💹",
                [
                    txt("儲蓄率  ·  Savings Rate\n", bold=True),
                    txt("= 月結餘 ÷ 月收入 × 100\n"),
                    txt("→ 查看月度快照「儲蓄率」欄", italic=True, color="gray"),
                ],
                "green_background",
            )
        ],
    ]
    add_column_list(page_id, kpi_row)

    # ── Monthly checklist ──
    append_blocks(
        page_id,
        [
            _div(),
            _h2("📋 本月任務  ·  Monthly Checklist"),
            _callout(
                "✅",
                [
                    txt("每月初工作清單  ·  Monthly Routine\n\n", bold=True),
                    txt("🤖 自動完成（每月 1 日 GitHub Actions）\n"),
                    txt("   · 黃金存摺 & 信貸餘額自動計算更新\n"),
                    txt("   · 月度快照自動建立\n"),
                    txt("   · 圖表自動重新生成\n\n"),
                    txt("✏️ 請手動補齊（約 5 分鐘）\n"),
                    txt("   · 開啟月度快照 → 填入「佣金收入」\n"),
                    txt("   · 填入「日常生活費（食衣住行）」\n"),
                    txt("   · 確認儲蓄率是否符合預期"),
                ],
                "blue_background",
            ),
            _div(),
            _h2("⚡ 快速連結  ·  Quick Links"),
        ],
    )

    # ── Quick links row ──
    ql_row = [
        [
            _callout(
                "📝",
                [
                    txt("本月快照  ·  This Month's Snapshot\n", bold=True),
                    txt(
                        "開啟「月度快照」資料庫\n→ 找到本月記錄 → 填入變動收支",
                        italic=True,
                        color="gray",
                    ),
                ],
                "gray_background",
            )
        ],
        [
            _callout(
                "🔢",
                [
                    txt("更新資產估值  ·  Update Asset Values\n", bold=True),
                    txt(
                        "開啟「資產明細」資料庫\n→ 手動更新房產、股權等估值",
                        italic=True,
                        color="gray",
                    ),
                ],
                "gray_background",
            )
        ],
        [
            _callout(
                "📈",
                [
                    txt("查看趨勢圖  ·  View Charts\n", bold=True),
                    txt(
                        "開啟「Charts & Analytics」頁面\n→ 查看最新淨值趨勢 / 資產分佈圖",
                        italic=True,
                        color="gray",
                    ),
                ],
                "gray_background",
            )
        ],
    ]
    add_column_list(page_id, ql_row)

    print("  ✅ Dashboard 完成")


# ══════════════════════════════════════════════════════════════════════════════
# CHARTS & ANALYTICS PAGE
# ══════════════════════════════════════════════════════════════════════════════


def build_charts_page(page_id):
    """Build the Charts & Analytics sub-page."""

    blocks = [
        _callout(
            "🤖",
            [
                txt(
                    "此頁面每月 1 日自動更新  ·  Auto-updated on 1st of each month\n",
                    bold=True,
                ),
                txt("由 GitHub Actions 驅動，透過 matplotlib 生成後嵌入 Notion。\n"),
                txt(
                    "圖表反映最新月度快照資料。Powered by GitHub Actions + matplotlib."
                ),
            ],
            "yellow_background",
        ),
        _div(),
        # Chart 1: Net Worth Trend
        _h2("📈 淨值趨勢  ·  Net Worth Trend"),
        _p(
            [
                txt(
                    "8 個月淨資產走勢，含總資產（虛線）與總負債（紅點線）對比。",
                    italic=True,
                    color="gray",
                )
            ]
        ),
        _image_block(f"{CHART_BASE}/chart_networth.png"),
        _div(),
        # Chart 2: Asset Breakdown
        _h2("💰 資產分佈  ·  Asset Breakdown"),
        _p(
            [
                txt(
                    "各類別資產占比甜甜圈圖，含金額合計與百分比。",
                    italic=True,
                    color="gray",
                )
            ]
        ),
        _image_block(f"{CHART_BASE}/chart_assets.png"),
        _div(),
        # Chart 3: Cash Flow
        _h2("💹 月收支對比  ·  Monthly Cash Flow"),
        _p(
            [
                txt(
                    "月收入、月支出、月結餘三組長條圖（正值金色 / 負值紅色）。",
                    italic=True,
                    color="gray",
                )
            ]
        ),
        _image_block(f"{CHART_BASE}/chart_cashflow.png"),
        _div(),
        # Update note
        _callout(
            "💡",
            [
                txt("手動刷新圖表  ·  Manual Chart Refresh\n", bold=True),
                txt("在本機執行："),
                txt("  python3 finance/generate_charts.py", color="default"),
                txt("\n或在 GitHub Actions 手動觸發 `finance_monthly.yml`"),
            ],
            "gray_background",
        ),
    ]
    append_blocks(page_id, blocks)
    print("  ✅ Charts & Analytics 完成")


# ══════════════════════════════════════════════════════════════════════════════
# QUICK START GUIDE
# ══════════════════════════════════════════════════════════════════════════════


def build_guide(page_id):
    """Build the Quick Start Guide sub-page."""

    blocks = [
        _callout(
            "🎯",
            [
                txt("5 分鐘完成設定  ·  Setup in 5 Minutes\n", bold=True),
                txt("本模板包含自動化腳本，搭配 GitHub Actions 免費運行。\n"),
                txt(
                    "This template includes automation scripts that run free on GitHub Actions."
                ),
            ],
            "yellow_background",
        ),
        _div(),
        # Steps as callouts
        _callout(
            "1️⃣",
            [
                txt("Duplicate 模板  ·  Duplicate the Template\n", bold=True),
                txt("點擊右上角「Duplicate」→ 複製到你的 Notion workspace\n"),
                txt("記下三個資料庫的 ID（網址列 32 碼）：\n"),
                txt("  · Assets · 資產明細\n"),
                txt("  · Liabilities · 負債明細\n"),
                txt("  · Monthly Snapshot · 月度快照"),
            ],
            "blue_background",
        ),
        _callout(
            "2️⃣",
            [
                txt("設定 finance_config.json  ·  Configure\n", bold=True),
                txt(
                    "cp finance_config.json.template finance_config.json\n",
                    color="default",
                ),
                txt("填入：\n"),
                txt("  · notion.assets_db_id / liabilities_db_id / snapshot_db_id\n"),
                txt("  · gold_savings（初始金額、日期、每月投入）\n"),
                txt("  · personal_loan（本金、起始日、年利率、月還款）\n"),
                txt("  · income.monthly_base / fixed_expenses"),
            ],
            "blue_background",
        ),
        _callout(
            "3️⃣",
            [
                txt("設定 GitHub Actions  ·  Setup Automation\n", bold=True),
                txt("① Fork 或 clone 此 repo\n"),
                txt("② GitHub Settings → Secrets → Actions → New repository secret\n"),
                txt("   名稱: NOTION_TOKEN  值: 你的 Notion API Token\n"),
                txt("③ 啟用 .github/workflows/finance_monthly.yml\n"),
                txt("④ 點「Run workflow」手動測試一次"),
            ],
            "green_background",
        ),
        _callout(
            "4️⃣",
            [
                txt("驗證首次執行  ·  Verify First Run\n", bold=True),
                txt("確認 Notion 更新：\n"),
                txt("  ✅ Assets 資料庫 → 黃金存摺「當前金額」已更新\n"),
                txt("  ✅ Liabilities 資料庫 → 信貸「餘額」已更新\n"),
                txt("  ✅ Monthly Snapshot → 本月快照已建立\n"),
                txt("  ✅ Charts 頁面 → 三張圖表已更新"),
            ],
            "orange_background",
        ),
        _callout(
            "5️⃣",
            [
                txt("每月工作流程  ·  Monthly Routine\n", bold=True),
                txt("🤖 自動（每月 1 日）：數字更新 + 快照建立 + 圖表刷新\n"),
                txt("✏️ 手動（5 分鐘）：\n"),
                txt("  · 開啟本月快照 → 填入佣金收入\n"),
                txt("  · 填入日常生活費\n"),
                txt("  · 查看儲蓄率，評估是否需要調整支出"),
            ],
            "purple_background",
        ),
        _div(),
        _h2("❓ FAQ"),
        _callout(
            "💬",
            [
                txt("NOTION_TOKEN 在哪裡取得？\n", bold=True),
                txt("前往 https://www.notion.so/my-integrations → New Integration\n"),
                txt(
                    "複製 Internal Integration Secret → 設定為 GitHub Secret NOTION_TOKEN"
                ),
            ],
            "gray_background",
        ),
        _callout(
            "💬",
            [
                txt("資料庫 ID 怎麼找？\n", bold=True),
                txt("在 Notion 開啟資料庫頁面 → 複製瀏覽器網址列的 32 位英數字串"),
            ],
            "gray_background",
        ),
        _callout(
            "💬",
            [
                txt("需要 Notion 付費版嗎？\n", bold=True),
                txt("不需要。本模板所有功能在 Notion 免費版均可運作。\n"),
                txt(
                    "圖表採用 image block（GitHub raw URL），無需 Notion Plus 的 Chart view。"
                ),
            ],
            "gray_background",
        ),
        _callout(
            "💬",
            [
                txt("圖表沒有更新怎麼辦？\n", bold=True),
                txt("1. 確認 GitHub Actions 有執行成功（Actions tab 查看 log）\n"),
                txt("2. 在 Notion 圖表上按 Refresh（⟳）強制重新載入圖片快取\n"),
                txt("3. 或手動執行：python3 finance/generate_charts.py"),
            ],
            "gray_background",
        ),
    ]
    append_blocks(page_id, blocks)
    print("  ✅ Quick Start Guide 完成")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-id", default=os.environ.get("NOTION_PARENT_ID"))
    args = parser.parse_args()

    if not args.parent_id:
        print("❌ 需要 parent page ID")
        print(
            "   NOTION_PARENT_ID=<id> python3 finance/create_commercial_template_v2.py"
        )
        sys.exit(1)

    parent_id = args.parent_id.replace("-", "")

    print("=" * 60)
    print("Personal Finance OS v2.1 — Template Creator")
    print("=" * 60)

    # ── 1. Root page ──
    print("\n[1/9] 建立根頁面...")
    root_id = create_page(
        parent_id,
        "💼",
        "💼 Personal Finance OS  ·  個人財務作業系統",
        cover_url="https://images.unsplash.com/photo-1621761191319-c6fb62004040?w=1500&q=80",
    )
    print(f"  ✅ root: {root_id}")

    # ── 2. Sub-pages ──
    print("\n[2/9] 建立子頁面...")
    dash_id = create_page(
        root_id,
        "🏠",
        "🏠 Dashboard  ·  儀表板",
        cover_url="https://images.unsplash.com/photo-1579621970563-ebec7560ff3e?w=1200&q=80",
    )
    charts_id = create_page(
        root_id,
        "📈",
        "📈 Charts & Analytics  ·  圖表分析",
    )
    guide_id = create_page(
        root_id,
        "📖",
        "📖 Quick Start Guide  ·  快速上手指南",
    )
    print(f"  ✅ dashboard: {dash_id}")
    print(f"  ✅ charts:    {charts_id}")
    print(f"  ✅ guide:     {guide_id}")

    # ── 3. Databases ──
    print("\n[3/9] 建立資料庫（含 formula 欄位）...")
    assets_id = create_assets_db(root_id)
    liab_id = create_liabilities_db(root_id)
    snap_id = create_snapshot_db(root_id)
    print(f"  ✅ assets:    {assets_id}")
    print(f"  ✅ liab:      {liab_id}")
    print(f"  ✅ snapshot:  {snap_id}")

    # ── 4-6. Seed data ──
    print("\n[4/9] 填入示範資產...")
    seed_assets(assets_id)

    print("\n[5/9] 填入示範負債...")
    seed_liabilities(liab_id)

    print("\n[6/9] 填入 8 個月快照...")
    seed_snapshots(snap_id)

    # ── 7. Root nav ──
    print("\n[7/9] 建立根頁面導航...")
    build_root_nav(
        root_id,
        {
            "dashboard": dash_id,
            "charts": charts_id,
            "guide": guide_id,
            "assets": assets_id,
            "liab": liab_id,
            "snap": snap_id,
        },
    )

    # ── 8. Dashboard ──
    print("\n[8/9] 建立 Dashboard...")
    build_dashboard(dash_id)

    # ── 9. Charts + Guide ──
    print("\n[9/9] 建立 Charts 頁面 & Quick Start Guide...")
    build_charts_page(charts_id)
    build_guide(guide_id)

    # ── Summary ──
    root_url = f"https://www.notion.so/{root_id.replace('-','')}"
    print("\n" + "=" * 60)
    print("✅ Personal Finance OS v2.1 建立完成！")
    print(f"\n🔗 開啟：{root_url}")
    print("\n📋 資料庫 IDs（填入 finance_config.json）：")
    print(f"   assets_db_id:      {assets_id}")
    print(f"   liabilities_db_id: {liab_id}")
    print(f"   snapshot_db_id:    {snap_id}")
    print(f"\n📈 Charts 頁面 ID（供 generate_charts.py 使用）：")
    print(f"   NOTION_CHARTS_PAGE_ID={charts_id}")
    print("\n下一步：")
    print("  1. 在 Safari 開啟模板，確認版面")
    print("  2. 為 Assets DB 手動新增 Gallery view（Notion UI）")
    print("  3. 為 Liabilities DB 手動新增 Board view（以「狀態」分組）")
    print("  4. 執行 generate_charts.py 更新圖表到新 Charts 頁面")
    print("=" * 60)


if __name__ == "__main__":
    main()
