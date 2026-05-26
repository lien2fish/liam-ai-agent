#!/usr/bin/env python3
"""
Personal Finance OS v2.0 — Auto Updater
個人財務作業系統 v2.0 — 自動更新腳本

讀取 finance_config.json，每月 1 日自動：
  1. 計算黃金存摺、信貸最新餘額
  2. 更新 Notion 資產明細 / 負債明細
  3. 建立當月快照（避免重複）
  4. 寫入執行日誌

Reads finance_config.json and runs on the 1st of each month.
"""
import json
import os
import urllib.request
from datetime import date, datetime
from dateutil.relativedelta import relativedelta


# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "finance_config.json"
)
LOG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "財務", "finance_update_log.txt"
)


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(
            f"找不到設定檔 / Config not found: {CONFIG_PATH}\n"
            "請複製 finance_config.json.template 為 finance_config.json 並填入數值。\n"
            "Please copy finance_config.json.template to finance_config.json and fill in your values."
        )
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


# ── Notion Token ──────────────────────────────────────────────────────────────


def _load_token() -> str:
    token = os.environ.get("NOTION_TOKEN")
    if token:
        return token
    try:
        import sys

        config_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "notion_crm"
        )
        sys.path.insert(0, os.path.abspath(config_dir))
        import config as _cfg

        sys.path.pop(0)
        return _cfg.NOTION_TOKEN
    except (ImportError, AttributeError):
        pass
    raise RuntimeError("NOTION_TOKEN 未設定 / NOTION_TOKEN not set")


# ── Notion API ────────────────────────────────────────────────────────────────


def _make_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }


def _request(method, path, data=None, headers=None):
    url = f"https://api.notion.com/v1{path}"
    body = json.dumps(data, ensure_ascii=False).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def query_db(db_id, filter_obj, headers):
    body = {"page_size": 100}
    if filter_obj:
        body["filter"] = filter_obj
    return _request("POST", f"/databases/{db_id}/query", body, headers).get(
        "results", []
    )


# ── Calculations ──────────────────────────────────────────────────────────────


def calc_loan_balance(cfg: dict, as_of: date) -> int:
    """攤還公式 / Loan amortization formula"""
    loan = cfg["personal_loan"]
    principal = loan["principal"]
    r = loan["annual_rate"] / 12
    payment = loan["monthly_payment"]
    start = date.fromisoformat(loan["start_date"])
    first_payment = start + relativedelta(months=1)
    if as_of < first_payment:
        return principal
    n = (as_of.year - first_payment.year) * 12 + (as_of.month - first_payment.month) + 1
    factor = (1 + r) ** n
    balance = principal * factor - payment * (factor - 1) / r
    return max(0, round(balance))


def calc_gold_balance(cfg: dict, as_of: date) -> int:
    """黃金存摺累積餘額 / Gold savings accumulated balance"""
    gold = cfg["gold_savings"]
    initial_date = date.fromisoformat(gold["initial_date"])
    months = (as_of.year - initial_date.year) * 12 + (as_of.month - initial_date.month)
    return gold["initial_value"] + months * gold["monthly_contribution"]


def calc_fixed_income(cfg: dict, month: int) -> int:
    inc = cfg["income"]
    base = inc["monthly_base"]
    if month == 9:
        base += inc.get("september_bonus", 0)
    return base


def calc_fixed_expenses(cfg: dict) -> int:
    return sum(cfg["fixed_expenses"].values())


# ── Log ───────────────────────────────────────────────────────────────────────


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ── Notion Operations ─────────────────────────────────────────────────────────


def find_page(db_id: str, title_prop: str, title: str, headers: dict):
    results = query_db(
        db_id, {"property": title_prop, "title": {"equals": title}}, headers
    )
    return results[0] if results else None


def update_asset(db_id, asset_name, amount, today, headers, cost_basis=None):
    page = find_page(db_id, "項目名稱 / Asset Name", asset_name, headers)
    if not page:
        log(f"  ⚠️  找不到資產 / Asset not found: {asset_name}")
        return
    props = {
        "當前金額 / Current Value": {"number": amount},
        "上次更新 / Last Updated": {"date": {"start": today.isoformat()}},
    }
    if cost_basis is not None:
        props["成本 / Cost Basis"] = {"number": cost_basis}
    _request(
        "PATCH",
        f"/pages/{page['id']}",
        {"properties": props},
        headers,
    )
    log(f"  ✅ 資產更新 / Asset updated: {asset_name} → NT${amount:,}")


def update_liability(db_id, liability_name, balance, headers):
    page = find_page(db_id, "項目名稱 / Liability Name", liability_name, headers)
    if not page:
        log(f"  ⚠️  找不到負債 / Liability not found: {liability_name}")
        return
    _request(
        "PATCH",
        f"/pages/{page['id']}",
        {"properties": {"餘額 / Balance": {"number": balance}}},
        headers,
    )
    log(f"  ✅ 負債更新 / Liability updated: {liability_name} → NT${balance:,}")


def snapshot_exists(db_id, year, month, headers) -> bool:
    label = f"{year}-{month:02d}"
    results = query_db(
        db_id, {"property": "月份 / Month", "title": {"equals": label}}, headers
    )
    return bool(results)


def create_snapshot(
    db_id, year, month, total_assets, total_liab, income, expenses, cfg, headers
):
    label = f"{year}-{month:02d}"
    net = total_assets - total_liab
    cashflow = income - expenses
    notes_cfg = cfg.get("snapshot_notes", {})
    note = (
        f"⚠️ {notes_cfg.get('variable_income', 'Pending: Variable income')}  |  "
        f"{notes_cfg.get('variable_expense', 'Pending: Variable expenses')}\n"
        f"固定收入 {income:,} | 固定支出 {expenses:,} | 固定結餘 {cashflow:,}"
    )
    _request(
        "POST",
        "/pages",
        {
            "parent": {"database_id": db_id},
            "properties": {
                "月份 / Month": {"title": [{"text": {"content": label}}]},
                "總資產 / Total Assets": {"number": total_assets},
                "總負債 / Total Liabilities": {"number": total_liab},
                "淨值 / Net Worth": {"number": net},
                "月收入 / Monthly Income": {"number": income},
                "月支出 / Monthly Expenses": {"number": expenses},
                "月結餘 / Net Cash Flow": {"number": cashflow},
                "備註 / Notes": {"rich_text": [{"text": {"content": note}}]},
            },
        },
        headers,
    )
    log(
        f"  ✅ 月度快照建立 / Snapshot created: {label}  淨值 NT${net:,}  結餘 {cashflow:,}"
    )


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    cfg = load_config()
    token = _load_token()
    h = _make_headers(token)
    notion = cfg["notion"]

    today = date.today()
    year, month = today.year, today.month

    log("=" * 55)
    log(f"Personal Finance OS v2.0  |  {today.isoformat()}")

    # 1. Dynamic balances
    gold, loan = None, None

    if cfg["gold_savings"]["enabled"]:
        gold = calc_gold_balance(cfg, today)
        log(f"黃金存摺估算 / Gold balance: NT${gold:,}")

    if cfg["personal_loan"]["enabled"]:
        loan = calc_loan_balance(cfg, today)
        log(f"信貸剩餘 / Loan balance: NT${loan:,}")

    # 2. Update Notion
    assets_db = notion["assets_db_id"]
    liab_db = notion["liabilities_db_id"]
    snap_db = notion["snapshot_db_id"]

    if gold is not None:
        update_asset(assets_db, cfg["gold_savings"]["asset_name"], gold, today, h)

    if loan is not None:
        update_liability(liab_db, cfg["personal_loan"]["liability_name"], loan, h)

    # 3. Totals
    static_total = sum(a["value"] for a in cfg.get("static_assets", []))
    total_assets = static_total + (gold or 0)
    total_liab = loan or 0
    fixed_income = calc_fixed_income(cfg, month)
    fixed_expenses = calc_fixed_expenses(cfg)

    log(
        f"總資產 / Total assets: NT${total_assets:,}  (靜態 {static_total:,} + 黃金 {gold or 0:,})"
    )
    log(
        f"固定收入 / Fixed income: NT${fixed_income:,}  支出 / Expenses: NT${fixed_expenses:,}"
    )

    # 4. Monthly snapshot
    if snapshot_exists(snap_db, year, month, h):
        log(f"  ⏭  {year}-{month:02d} 快照已存在，跳過 / Snapshot exists, skipped")
    else:
        create_snapshot(
            snap_db,
            year,
            month,
            total_assets,
            total_liab,
            fixed_income,
            fixed_expenses,
            cfg,
            h,
        )

    log(f"完成 / Done  {today.isoformat()}")
    log("=" * 55)


if __name__ == "__main__":
    main()
