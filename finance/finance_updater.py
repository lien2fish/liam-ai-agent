#!/usr/bin/env python3
"""
個人財務自動追蹤系統
每月 1 日自動執行：
  1. 計算黃金存摺、信貸最新餘額
  2. 更新 Notion 資產明細 / 負債明細
  3. 建立當月快照（預填固定項目，留白變動項目）
  4. 寫入 repo 日誌
"""
import json
import os
import urllib.request
import urllib.parse
from datetime import date, datetime
from dateutil.relativedelta import relativedelta


# ── Notion Token ─────────────────────────────────────────────────────────────
def _load_notion_token() -> str:
    """優先用環境變數，本機 fallback import gitignored 的 notion_crm/config.py"""
    token = os.environ.get("NOTION_TOKEN")
    if token:
        return token
    try:
        import sys

        config_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "notion_crm"
        )
        sys.path.insert(0, os.path.abspath(config_dir))
        import config as notion_config

        sys.path.pop(0)
        return notion_config.NOTION_TOKEN
    except (ImportError, AttributeError):
        pass
    raise RuntimeError(
        "NOTION_TOKEN 未設定：請設定環境變數或確認 notion_crm/config.py 存在"
    )


NOTION_TOKEN = _load_notion_token()
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# ── Notion DB IDs ─────────────────────────────────────────────────────────────
ASSETS_DB = "369f4149-a6aa-817e-b94f-cf38e5274648"
LIAB_DB = "369f4149-a6aa-81d3-adad-dc98535e26e2"
SNAP_DB = "369f4149-a6aa-81bf-93d7-e535bc9e53f4"

# ── 資產常數（靜態，需每年手動更新） ─────────────────────────────────────────
EQUITY_JUJIN = 6_600_000  # 鉅鑫管理顧問股本
EQUITY_JIANGXIN = 2_000_000  # 匠鑫私廚股本
INSURANCE = 775_000  # 保誠人壽保單（2032年到期）

# ── 黃金存摺 ──────────────────────────────────────────────────────────────────
GOLD_INITIAL = 302_380  # 2026-05-04 餘額
GOLD_INITIAL_DATE = date(2026, 5, 4)
GOLD_MONTHLY = 3_500  # 每月定期投入

# ── 玉山信貸 ──────────────────────────────────────────────────────────────────
LOAN_PRINCIPAL = 600_000
LOAN_START = date(2024, 7, 29)
LOAN_ANNUAL_RATE = 0.049
LOAN_MONTHLY_PAYMENT = 8_452

# ── 固定月收入 ────────────────────────────────────────────────────────────────
SALARY = 38_000
SUBSIDY = 5_000
ANNUAL_INTEREST = 157_200  # 每年 9 月入帳（鉅鑫顧問利息）

# ── 固定月支出 ────────────────────────────────────────────────────────────────
FIXED_EXPENSES = {
    "玉山信貸還款": 8_452,
    "孝親費": 10_000,
    "幼兒園": 5_000,
    "扶輪社社費": 3_500,
    "黃金存摺投資": 3_500,
    "個人保費": 2_413,
    "保誠教育金": 2_667,
    "子女保費": 2_071,
    "AI工具": 1_600,
    "汽車費": 7_667,
}

# ── Log 路徑 ──────────────────────────────────────────────────────────────────
LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "財務",
    "finance_update_log.txt",
)


# ─────────────────────────────────────────────────────────────────────────────
# Notion API helpers
# ─────────────────────────────────────────────────────────────────────────────


def _request(method, path, data=None):
    url = f"https://api.notion.com/v1{path}"
    payload = json.dumps(data, ensure_ascii=False).encode() if data else None
    req = urllib.request.Request(url, data=payload, headers=HEADERS, method=method)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def notion_get(path):
    return _request("GET", path)


def notion_post(path, data):
    return _request("POST", path, data)


def notion_patch(path, data):
    return _request("PATCH", path, data)


def query_db(db_id, filter_obj=None):
    body = {"page_size": 100}
    if filter_obj:
        body["filter"] = filter_obj
    return notion_post(f"/databases/{db_id}/query", body).get("results", [])


# ─────────────────────────────────────────────────────────────────────────────
# 計算函式
# ─────────────────────────────────────────────────────────────────────────────


def calc_loan_balance(as_of: date) -> int:
    """攤還公式計算信貸剩餘本金"""
    r = LOAN_ANNUAL_RATE / 12
    # 已繳期數：from 第一期（LOAN_START 後一個月）到 as_of 當月
    first_payment = LOAN_START + relativedelta(months=1)
    if as_of < first_payment:
        return LOAN_PRINCIPAL
    n = (as_of.year - first_payment.year) * 12 + (as_of.month - first_payment.month) + 1
    factor = (1 + r) ** n
    balance = LOAN_PRINCIPAL * factor - LOAN_MONTHLY_PAYMENT * (factor - 1) / r
    return max(0, round(balance))


def calc_gold_balance(as_of: date) -> int:
    """黃金存摺：初始值 + 月數 × 每月投入"""
    months = (as_of.year - GOLD_INITIAL_DATE.year) * 12 + (
        as_of.month - GOLD_INITIAL_DATE.month
    )
    return GOLD_INITIAL + months * GOLD_MONTHLY


def calc_fixed_income(year: int, month: int) -> int:
    """固定月收入（9月加年度利息）"""
    base = SALARY + SUBSIDY
    if month == 9:
        base += ANNUAL_INTEREST
    return base


# ─────────────────────────────────────────────────────────────────────────────
# Log
# ─────────────────────────────────────────────────────────────────────────────


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Notion 操作
# ─────────────────────────────────────────────────────────────────────────────


def find_page_by_title(db_id: str, title: str):
    """在資料庫中找標題完全相符的第一筆記錄"""
    results = query_db(
        db_id,
        {"property": "項目名稱", "title": {"equals": title}},
    )
    return results[0] if results else None


def find_snapshot(year: int, month: int):
    """找當月快照"""
    label = f"{year}-{month:02d}"
    results = query_db(
        SNAP_DB,
        {"property": "月份", "title": {"equals": label}},
    )
    return results[0] if results else None


def update_asset_amount(asset_name: str, amount: int, today: date):
    page = find_page_by_title(ASSETS_DB, asset_name)
    if not page:
        log(f"  ⚠️  找不到資產記錄：{asset_name}")
        return
    notion_patch(
        f"/pages/{page['id']}",
        {
            "properties": {
                "當前金額": {"number": amount},
                "上次更新": {"date": {"start": today.isoformat()}},
            }
        },
    )
    log(f"  ✅ 資產更新：{asset_name} → NT${amount:,}")


def update_liability_balance(liability_name: str, balance: int, today: date):
    page = find_page_by_title(LIAB_DB, liability_name)
    if not page:
        log(f"  ⚠️  找不到負債記錄：{liability_name}")
        return
    notion_patch(
        f"/pages/{page['id']}",
        {"properties": {"餘額": {"number": balance}}},
    )
    log(f"  ✅ 負債更新：{liability_name} 餘額 → NT${balance:,}")


def create_monthly_snapshot(
    year: int,
    month: int,
    total_assets: int,
    total_liab: int,
    fixed_income: int,
    fixed_expense: int,
):
    label = f"{year}-{month:02d}"
    net_worth = total_assets - total_liab
    net_cashflow = fixed_income - fixed_expense

    note = (
        f"⚠️ 待填：磊山佣金（約16,667）、日常生活費（約28,333）\n"
        f"固定收入 {fixed_income:,} | 固定支出 {fixed_expense:,} | 固定結餘 {net_cashflow:,}"
    )

    notion_post(
        "/pages",
        {
            "parent": {"database_id": SNAP_DB},
            "properties": {
                "月份": {"title": [{"type": "text", "text": {"content": label}}]},
                "總資產": {"number": total_assets},
                "總負債": {"number": total_liab},
                "淨值": {"number": net_worth},
                "月收入": {"number": fixed_income},
                "月支出": {"number": fixed_expense},
                "月結餘": {"number": net_cashflow},
                "備註": {"rich_text": [{"type": "text", "text": {"content": note}}]},
            },
        },
    )
    log(f"  ✅ 月度快照建立：{label}　淨值 NT${net_worth:,}　固定結餘 {net_cashflow:,}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main():
    today = date.today()
    year, month = today.year, today.month

    log("=" * 55)
    log(f"個人財務自動更新開始　{today.isoformat()}")

    # 1. 計算動態資產
    gold = calc_gold_balance(today)
    loan = calc_loan_balance(today)
    log(f"黃金存摺估算餘額：NT${gold:,}")
    log(f"玉山信貸估算餘額：NT${loan:,}")

    # 2. 更新 Notion
    log("── 更新 Notion 資產明細 ──")
    update_asset_amount("華南銀行黃金存摺", gold, today)

    log("── 更新 Notion 負債明細 ──")
    update_liability_balance("玉山銀行信貸", loan, today)

    # 3. 計算總資產
    total_assets = EQUITY_JUJIN + EQUITY_JIANGXIN + INSURANCE + gold
    fixed_income = calc_fixed_income(year, month)
    fixed_expense = sum(FIXED_EXPENSES.values())

    log(f"總資產（含靜態股權）：NT${total_assets:,}")
    log(f"固定月收入：NT${fixed_income:,}　固定月支出：NT${fixed_expense:,}")

    # 4. 建立月度快照（避免重複）
    log("── 月度快照 ──")
    if find_snapshot(year, month):
        log(f"  ⏭  {year}-{month:02d} 快照已存在，跳過")
    else:
        create_monthly_snapshot(
            year, month, total_assets, loan, fixed_income, fixed_expense
        )

    log(f"個人財務自動更新完成　{today.isoformat()}")
    log("=" * 55)


if __name__ == "__main__":
    main()
