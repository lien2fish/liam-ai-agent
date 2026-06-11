#!/usr/bin/env python3
"""
個人資產負債表 — Notion 更新腳本
執行：python3 finance/update_balance_sheet.py
每次執行重建「💼 個人資產負債表」頁面，並重建訂閱費用管理 DB（資料從 finance_config.json 讀取）
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from collections import defaultdict
from datetime import datetime


# ── Token ─────────────────────────────────────────────────────────────────────
def _load_token():
    t = os.environ.get("NOTION_TOKEN")
    if t:
        return t
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "notion_crm"))
        import config as c

        return c.NOTION_TOKEN
    except Exception:
        raise RuntimeError(
            "NOTION_TOKEN 未設定：請設定環境變數或確認 notion_crm/config.py 存在"
        )


TOKEN = _load_token()
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# ── Config ────────────────────────────────────────────────────────────────────
CFG_PATH = os.path.join(os.path.dirname(__file__), "finance_config.json")

with open(CFG_PATH) as f:
    CFG = json.load(f)

NOTION_CFG = CFG["notion"]
ASSETS_DB = NOTION_CFG["assets_db_id"]
LIAB_DB = NOTION_CFG["liabilities_db_id"]
FINANCE_OS_ID = "36af4149-a6aa-8192-9065-f9e5f97ebabf"

_inc = CFG["income"]
MONTHLY_INCOME = (
    _inc["monthly_base"]
    + _inc["child_subsidy_monthly"]
    + _inc["insurance_commission_annual"] // 12
    + _inc["company_interest_annual"] // 12
)
MONTHLY_EXPENSES = sum(CFG["fixed_expenses"].values())

BALANCE_SHEET_TITLE = "💼 個人資產負債表"
SUBS_DB_TITLE = "📱 訂閱費用管理"


# ── API helpers ───────────────────────────────────────────────────────────────
def _req(method, path, data=None):
    url = f"https://api.notion.com/v1{path}"
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        r = urllib.request.urlopen(req)
        return json.loads(r.read())
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        raise RuntimeError(f"Notion {method} {path} → {e.code}: {err[:200]}")


def nget(path):
    return _req("GET", path)


def npost(path, d):
    return _req("POST", path, d)


def npatch(path, d):
    return _req("PATCH", path, d)


def ndelete(path):
    return _req("DELETE", path)


# ── Fetch & parse ─────────────────────────────────────────────────────────────
def query_db(db_id):
    results, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        r = npost(f"/databases/{db_id}/query", body)
        results.extend(r.get("results", []))
        if not r.get("has_more"):
            break
        cursor = r["next_cursor"]
    return results


def _title(props, key):
    v = props.get(key, {}).get("title", [])
    return v[0]["plain_text"] if v else ""


def _num(props, key):
    v = props.get(key, {}).get("number")
    return v or 0


def _sel(props, key):
    v = props.get(key, {}).get("select")
    return v["name"] if v else "其他"


def parse_asset(page):
    p = page["properties"]
    return {
        "name": _title(p, "項目名稱 / Asset Name"),
        "category": _sel(p, "類別 / Category"),
        "value": _num(p, "當前金額 / Current Value"),
        "cost": _num(p, "成本 / Cost Basis"),
    }


def parse_liability(page):
    p = page["properties"]
    return {
        "name": _title(p, "項目名稱 / Liability Name"),
        "balance": _num(p, "餘額 / Balance"),
        "original": _num(p, "原始金額 / Original Amount"),
        "monthly_payment": _num(p, "月還款 / Monthly Payment"),
        "annual_rate": _num(p, "年利率 / Annual Rate"),
    }


# ── Block builders ────────────────────────────────────────────────────────────
def _rt(text, bold=False):
    ann = {"bold": True} if bold else {}
    b = {"type": "text", "text": {"content": text}}
    if ann:
        b["annotations"] = ann
    return b


def para(text, bold=False):
    return {"type": "paragraph", "paragraph": {"rich_text": [_rt(text, bold)]}}


def h2(text):
    return {"type": "heading_2", "heading_2": {"rich_text": [_rt(text)]}}


def h3(text):
    return {"type": "heading_3", "heading_3": {"rich_text": [_rt(text)]}}


def callout(emoji, text, color="gray_background"):
    return {
        "type": "callout",
        "callout": {
            "icon": {"type": "emoji", "emoji": emoji},
            "rich_text": [_rt(text, bold=True)],
            "color": color,
        },
    }


def bullet(text):
    return {
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [_rt(text)]},
    }


def divider():
    return {"type": "divider", "divider": {}}


def toggle(text, children, bold=True):
    return {
        "type": "toggle",
        "toggle": {
            "rich_text": [_rt(text, bold=bold)],
            "children": children,
        },
    }


# ── Page helpers ──────────────────────────────────────────────────────────────
def find_child_page(parent_id, title):
    r = nget(f"/blocks/{parent_id}/children?page_size=100")
    for b in r.get("results", []):
        if b.get("type") == "child_page" and b["child_page"].get("title") == title:
            return b["id"]
    return None


def clear_page(page_id):
    r = nget(f"/blocks/{page_id}/children?page_size=100")
    for b in r.get("results", []):
        try:
            ndelete(f"/blocks/{b['id']}")
            time.sleep(0.05)
        except Exception:
            pass


def create_page(parent_id, title, emoji="💼"):
    r = npost(
        "/pages",
        {
            "parent": {"type": "page_id", "page_id": parent_id},
            "icon": {"type": "emoji", "emoji": emoji},
            "properties": {
                "title": {"title": [{"type": "text", "text": {"content": title}}]}
            },
        },
    )
    return r["id"]


def append_blocks(page_id, blocks):
    # Notion API: max 100 blocks per request
    for i in range(0, len(blocks), 95):
        npatch(f"/blocks/{page_id}/children", {"children": blocks[i : i + 95]})
        time.sleep(0.2)


# ── Toggle child blocks (two-pass for toggles with many children) ─────────────
def append_toggle_children(toggle_id, children):
    npatch(f"/blocks/{toggle_id}/children", {"children": children})


# ── Subscription DB ───────────────────────────────────────────────────────────
def create_subs_db(parent_page_id):
    r = npost(
        "/databases",
        {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "icon": {"type": "emoji", "emoji": "📱"},
            "title": [{"type": "text", "text": {"content": SUBS_DB_TITLE}}],
            "properties": {
                "服務名稱": {"title": {}},
                "月費 (NTD)": {"number": {"format": "number"}},
                "計費週期": {
                    "select": {
                        "options": [
                            {"name": "月付", "color": "blue"},
                            {"name": "年付", "color": "green"},
                            {"name": "季付", "color": "yellow"},
                        ]
                    }
                },
                "類別": {
                    "select": {
                        "options": [
                            {"name": "AI工具", "color": "purple"},
                            {"name": "娛樂", "color": "red"},
                            {"name": "生產力", "color": "blue"},
                            {"name": "媒體", "color": "orange"},
                            {"name": "通訊", "color": "gray"},
                            {"name": "其他", "color": "default"},
                        ]
                    }
                },
                "下次扣款": {"date": {}},
                "狀態": {
                    "select": {
                        "options": [
                            {"name": "啟用", "color": "green"},
                            {"name": "暫停", "color": "yellow"},
                            {"name": "取消", "color": "red"},
                        ]
                    }
                },
                "說明": {"rich_text": {}},
            },
        },
    )
    return r["id"]


def populate_subs_db(db_id, subscriptions):
    for s in subscriptions:
        npost(
            "/pages",
            {
                "parent": {"database_id": db_id},
                "properties": {
                    "服務名稱": {
                        "title": [{"type": "text", "text": {"content": s["name"]}}]
                    },
                    "月費 (NTD)": {
                        "number": s.get("amount_ntd", s.get("monthly_ntd", 0))
                    },
                    "計費週期": {"select": {"name": s.get("cycle", "月付")}},
                    "類別": {"select": {"name": s.get("category", "其他")}},
                    "狀態": {"select": {"name": s.get("status", "啟用")}},
                    "說明": {
                        "rich_text": [
                            {"type": "text", "text": {"content": s.get("note", "")}}
                        ]
                    },
                },
            },
        )
        time.sleep(0.1)


# ── Save page ID back to config ───────────────────────────────────────────────
def save_page_id(page_id):
    with open(CFG_PATH) as f:
        raw = f.read()
    updated = raw.replace(
        '"balance_sheet_page_id": null', f'"balance_sheet_page_id": "{page_id}"'
    )
    if updated != raw:
        with open(CFG_PATH, "w") as f:
            f.write(updated)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("📊 讀取 Notion 資料中...")

    assets = sorted(
        [parse_asset(p) for p in query_db(ASSETS_DB)],
        key=lambda a: a["value"],
        reverse=True,
    )
    liabilities = [parse_liability(p) for p in query_db(LIAB_DB)]

    total_assets = sum(a["value"] for a in assets)
    total_liab = sum(l["balance"] for l in liabilities)
    net_worth = total_assets - total_liab
    debt_ratio = total_liab / total_assets * 100 if total_assets else 0
    cashflow = MONTHLY_INCOME - MONTHLY_EXPENSES

    def monthly_equiv(s):
        amt = s.get("amount_ntd", s.get("monthly_ntd", 0))
        return amt / 12 if s.get("cycle") == "年付" else amt

    subs_total = sum(
        monthly_equiv(s)
        for s in CFG.get("subscriptions", [])
        if s.get("status") == "啟用"
    )

    by_cat = defaultdict(list)
    for a in assets:
        by_cat[a["category"]].append(a)
    cat_order = sorted(
        by_cat, key=lambda c: sum(a["value"] for a in by_cat[c]), reverse=True
    )

    invest_cats = {"股票", "黃金", "ETF", "Stock", "Gold"}
    invest_list = [a for a in assets if a["category"] in invest_cats]
    invest_total = sum(a["value"] for a in invest_list)
    invest_cost = sum(a["cost"] for a in invest_list)
    invest_gain = invest_total - invest_cost

    print(
        f"  資產 NT${total_assets/10000:.1f}萬  負債 NT${total_liab/10000:.1f}萬  淨值 NT${net_worth/10000:.1f}萬"
    )

    # ── Find / create page ────────────────────────────────────────────────────
    saved_id = CFG.get("balance_sheet_page_id")
    page_id = (
        saved_id if saved_id else find_child_page(FINANCE_OS_ID, BALANCE_SHEET_TITLE)
    )

    if page_id:
        print(f"\n📄 清空現有頁面...")
        clear_page(page_id)
    else:
        print(f"\n📄 建立新頁面...")
        page_id = create_page(FINANCE_OS_ID, BALANCE_SHEET_TITLE, "💼")
        save_page_id(page_id)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cf_sign = "＋" if cashflow >= 0 else "－"
    cf_color = "green_background" if cashflow >= 0 else "red_background"
    nw_color = "green_background" if net_worth >= 0 else "red_background"

    # ── Build asset detail children (for toggle) ──────────────────────────────
    asset_children = []
    for cat in cat_order:
        cat_val = sum(a["value"] for a in by_cat[cat])
        pct = cat_val / total_assets * 100 if total_assets else 0
        asset_children.append(
            para(f"▸ {cat}　NT${cat_val:,.0f}　{pct:.1f}%", bold=True)
        )
        for a in by_cat[cat]:
            asset_children.append(bullet(f"{a['name']}　NT${a['value']:,.0f}"))

    # ── Build investment children ─────────────────────────────────────────────
    if invest_list:
        gain_str = f"{'＋' if invest_gain >= 0 else '－'}NT${abs(invest_gain):,.0f}" + (
            f"　({invest_gain/invest_cost*100:+.1f}%)" if invest_cost else ""
        )
        invest_children = [
            para(f"投資總值　NT${invest_total:,.0f}", bold=True),
            para(f"投資成本　NT${invest_cost:,.0f}"),
            para(f"損益　{gain_str}"),
            divider(),
        ]
        for a in invest_list:
            gain = a["value"] - a["cost"]
            gain_s = (
                f"　損益 {'＋' if gain >= 0 else '－'}NT${abs(gain):,.0f}"
                if a["cost"]
                else ""
            )
            invest_children.append(bullet(f"{a['name']}　NT${a['value']:,.0f}{gain_s}"))
    else:
        invest_children = [para("— 目前無投資資產 —")]

    # ── Build liability children ──────────────────────────────────────────────
    if liabilities:
        liab_children = []
        for l in liabilities:
            paid_pct = (
                (l["original"] - l["balance"]) / l["original"] * 100
                if l["original"]
                else 0
            )
            liab_children += [
                para(l["name"], bold=True),
                bullet(f"餘額　NT${l['balance']:,.0f}"),
                bullet(f"月還款　NT${l['monthly_payment']:,.0f}"),
                *(
                    []
                    if not l["annual_rate"]
                    else [bullet(f"年利率　{l['annual_rate']*100:.2f}%")]
                ),
                *([] if not l["original"] else [bullet(f"已還清　{paid_pct:.1f}%")]),
            ]
    else:
        liab_children = [para("— 目前無負債 —")]

    # ── Build cash flow children ──────────────────────────────────────────────
    cashflow_children = [
        para(f"月收入　NT${MONTHLY_INCOME:,.0f}", bold=True),
        bullet(f"固定薪資　NT${_inc['monthly_base']:,.0f}"),
        bullet(f"育兒補助　NT${_inc['child_subsidy_monthly']:,.0f}"),
        bullet(
            f"年度佣金（月攤分）　NT${_inc['insurance_commission_annual']//12:,.0f}"
        ),
        bullet(f"公司利息（月攤分）　NT${_inc['company_interest_annual']//12:,.0f}"),
        para(""),
        para(f"月支出（固定）　NT${MONTHLY_EXPENSES:,.0f}", bold=True),
        *[bullet(f"{k}　NT${v:,.0f}") for k, v in CFG["fixed_expenses"].items()],
        para(""),
        callout(
            "📊" if cashflow >= 0 else "⚠️",
            f"月結餘　{cf_sign}NT${abs(cashflow):,.0f}",
            cf_color,
        ),
    ]

    # ── Build subscription summary children ───────────────────────────────────
    subs = CFG.get("subscriptions", [])
    active_subs = [s for s in subs if s.get("status") == "啟用"]
    subs_children = (
        [
            para(
                f"啟用中訂閱　{len(active_subs)} 項，月費合計 NT${subs_total:,.0f}",
                bold=True,
            ),
            *[
                bullet(
                    f"{s['name']}　NT${s.get('amount_ntd', s.get('monthly_ntd', 0)):,.0f}／{'年' if s.get('cycle') == '年付' else '月'}"
                    f"　≈ NT${monthly_equiv(s):,.0f}/月　（{s.get('category', '')}）"
                    + (f"　{s['note']}" if s.get("note") else "")
                )
                for s in active_subs
            ],
            para(""),
            para("→ 完整訂閱清單見下方「📱 訂閱費用管理」資料庫"),
        ]
        if active_subs
        else [para("— 目前無訂閱記錄，見下方資料庫新增 —")]
    )

    # ── Assemble top-level blocks ─────────────────────────────────────────────
    blocks = [
        para(f"最後更新：{now_str}"),
        divider(),
        callout(
            "💰",
            f"總資產　NT${total_assets:,.0f}　（{total_assets/10000:.1f}萬）",
            "gray_background",
        ),
        callout(
            "🏦", f"淨值　　NT${net_worth:,.0f}　（{net_worth/10000:.1f}萬）", nw_color
        ),
        callout(
            "💳",
            f"總負債　NT${total_liab:,.0f}　負債比 {debt_ratio:.1f}%",
            "red_background",
        ),
        callout("📅", f"月結餘　{cf_sign}NT${abs(cashflow):,.0f}", cf_color),
        divider(),
        toggle("📊 資產明細", asset_children),
        divider(),
        toggle("📈 投資概況", invest_children),
        divider(),
        toggle("💳 負債明細", liab_children),
        divider(),
        toggle("📅 月現金流", cashflow_children),
        divider(),
        toggle("📱 訂閱費用管理", subs_children),
        divider(),
    ]

    print("✏️  寫入頁面內容...")
    append_blocks(page_id, blocks)

    # ── Subscription DB ───────────────────────────────────────────────────────
    print("📱 建立訂閱費用資料庫...")
    subs_db_id = create_subs_db(page_id)
    if subs:
        populate_subs_db(subs_db_id, subs)
        print(f"   已寫入 {len(subs)} 筆訂閱")

    url = f"https://www.notion.so/{page_id.replace('-', '')}"
    print(f"\n✅ 完成！")
    print(f"   {url}")


if __name__ == "__main__":
    main()
