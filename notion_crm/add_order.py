#!/usr/bin/env python3
"""
新增訂單 → 本機 Numbers（主）→ Notion 備份

用法：
  python3 add_order.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import json
from datetime import date
from pathlib import Path
from numbers_parser import Document
import notion_api as api
from config import DB, BRAND_PREFIXES, CUSTOMER_DB, CUSTOMER_NAME_FIELD

# 本機 Numbers 檔路徑
NUMBERS_FILES = {
    "seafood": Path(
        "/Users/lien/Desktop/鉅鑫管理顧問/鑫海產/鑫海產品項＆客戶紀錄單.numbers"
    ),
    "wine": Path("/Users/lien/Desktop/鉅鑫管理顧問/鑫酒藏/鑫酒藏販售清單.numbers"),
    "tea": Path(
        "/Users/lien/Desktop/鉅鑫管理顧問/鑫茶坊/鑫茶坊品項＆客戶紀錄單.numbers"
    ),
}
SALES_SHEET = {
    "seafood": "📊 銷售報表",
    "wine": "📊 銷售報表",
    "tea": "📊 銷售報表",
}
CUSTOMER_SHEET = {
    "seafood": "👥 客戶名單",
    "wine": "👥 客戶名單",
    "tea": "👥 客戶名單",
}

PRICE_HISTORY = Path(__file__).parent.parent / "seafood/price_history.json"

BRAND_MENU = {
    "1": "seafood",
    "2": "wine",
    "3": "tea",
}

# 各品牌對應的銷售 DB 和主鍵欄位名
SALES_DB = {
    "seafood": "seafood_sales",
    "wine": "wine_sales",
    "tea": "tea_sales",
}
TITLE_FIELD = {
    "seafood": "訂單編號",
    "wine": "出貨單號",
    "tea": "訂單編號",
}

# 全品牌統一總表（crm_unified）— 每筆訂單同步到此，維持回購提醒資料正確
_UNIFIED_CFG = json.load(
    open(Path(__file__).parent.parent / "crm_unified" / "config.json")
)
UNIFIED_CUSTOMER_DB = _UNIFIED_CFG["customer_db"]
UNIFIED_SALES_DB = _UNIFIED_CFG["sales_db"]
BRAND_ZH = {"seafood": "鑫海產", "wine": "鑫酒藏", "tea": "鑫茶坊"}


def rt(text):
    return {"rich_text": [{"type": "text", "text": {"content": str(text)}}]}


# ── 本機 Numbers 寫入 ─────────────────────────────────────────────


def _find_empty_row(table, start=3):
    for r in range(start, table.num_rows):
        try:
            if not table.cell(r, 0).value:
                return r
        except Exception:
            pass
    return table.num_rows


def write_to_numbers(brand, row_data: list):
    fpath = NUMBERS_FILES[brand]
    if not fpath.exists():
        print(f"  ⚠️  本機檔案不存在：{fpath.name}，跳過")
        return False
    doc = Document(str(fpath))
    sheet_name = SALES_SHEET[brand]
    for sheet in doc.sheets:
        if sheet.name == sheet_name:
            table = sheet.tables[0]
            r = _find_empty_row(table)
            for c, val in enumerate(row_data):
                if val is not None:
                    table.write(r, c, val)
            doc.save(str(fpath))
            print(f"  ✅ 本機 Numbers 已寫入（{sheet_name} 第{r}列）")
            return True
    print(f"  ⚠️  找不到工作表「{sheet_name}」")
    return False


def update_numbers_customer(brand, customer_name, amount):
    fpath = NUMBERS_FILES[brand]
    if not fpath.exists():
        return
    doc = Document(str(fpath))
    sheet_name = CUSTOMER_SHEET[brand]
    for sheet in doc.sheets:
        if sheet.name == sheet_name:
            table = sheet.tables[0]
            for r in range(3, table.num_rows):
                try:
                    name = table.cell(r, 1).value
                    if name and customer_name.split()[0] in str(name):
                        col_total = 7  # 累計消費欄（第8欄，index 7）
                        current = table.cell(r, col_total).value or 0
                        table.write(r, col_total, float(current) + amount)
                        doc.save(str(fpath))
                        print(
                            f"  ✅ 本機客戶累計消費更新：{name} NT${float(current)+amount:,.0f}"
                        )
                        return
                except Exception:
                    pass


def get_market_prices():
    if not PRICE_HISTORY.exists():
        return None, None
    history = json.loads(PRICE_HISTORY.read_text(encoding="utf-8"))
    if not history:
        return None, None
    latest_date = sorted(history.keys())[-1]
    return history.get(latest_date, {}), latest_date


def get_next_order_id(brand):
    prefix = BRAND_PREFIXES[brand]
    db_key = SALES_DB[brand]
    title_field = TITLE_FIELD[brand]
    rows = api.query_db(DB[db_key])
    nums = []
    for r in rows:
        title = r["properties"].get(title_field, {}).get("title", [])
        if title:
            text = title[0]["plain_text"]
            if text.startswith(prefix + "-"):
                try:
                    nums.append(int(text.split("-")[1]))
                except ValueError:
                    pass
    next_num = (max(nums) + 1) if nums else 1
    return f"{prefix}-{next_num:03d}"


def find_customer(brand, name_or_id):
    db_key = CUSTOMER_DB.get(brand, f"{brand}_customers")
    name_field = CUSTOMER_NAME_FIELD.get(brand, "姓名")
    rows = api.query_db(DB[db_key])
    for r in rows:
        title_prop = r["properties"][name_field]["title"]
        customer_name = title_prop[0]["plain_text"] if title_prop else ""
        id_prop = r["properties"].get("客戶編號", {}).get("rich_text", [])
        customer_id = id_prop[0]["plain_text"] if id_prop else ""
        if name_or_id in customer_name or name_or_id == customer_id:
            return r["id"], customer_name
    return None, name_or_id


def update_customer_total(brand, page_id, amount):
    field = "累計消費" if brand == "seafood" else "累計消費金額"
    page = api.get(f"/pages/{page_id}")
    current = page["properties"].get(field, {}).get("number") or 0
    api.patch(
        f"/pages/{page_id}",
        {"properties": {field: {"number": current + amount}}},
    )
    return current + amount


def create_seafood_record(
    order_id, order_date, customer_name, items, amount, cost, market_ref, pay
):
    gross = (amount - cost) if cost else 0
    margin = round(gross / amount * 100, 1) if amount and cost else 0
    props = {
        "訂單編號": {"title": [{"type": "text", "text": {"content": order_id}}]},
        "出貨日期": {"date": {"start": order_date}},
        "客戶名稱": rt(customer_name),
        "品項明細": rt(items),
        "訂購金額": {"number": amount},
        "付款方式": {"select": {"name": pay}} if pay else None,
        "備註": rt(""),
    }
    if cost:
        props["成本"] = {"number": cost}
        props["毛利"] = {"number": gross}
        props["毛利率%"] = {"number": margin}
    if market_ref:
        props["市場參考單價"] = rt(market_ref)
    props = {k: v for k, v in props.items() if v is not None}
    return api.post(
        "/pages", {"parent": {"database_id": DB["seafood_sales"]}, "properties": props}
    )


def create_wine_record(
    order_id,
    order_date,
    customer_name,
    product_name,
    product_code,
    winery,
    category,
    unit_price,
    qty,
    discount,
    pay,
):
    subtotal = unit_price * qty if unit_price and qty else 0
    final = round(subtotal * (1 - discount / 100), 0) if discount else subtotal
    props = {
        "出貨單號": {"title": [{"type": "text", "text": {"content": order_id}}]},
        "出貨日期": {"date": {"start": order_date}},
        "客戶名稱": rt(customer_name),
        "商品名稱": rt(product_name),
        "數量": {"number": qty} if qty else None,
        "小計": {"number": subtotal} if subtotal else None,
        "折後小計": {"number": final} if final else None,
    }
    if product_code:
        props["商品代碼"] = rt(product_code)
    if winery:
        props["品牌/酒廠"] = rt(winery)
    if category:
        props["類別"] = {"select": {"name": category}}
    if unit_price:
        props["單價"] = {"number": unit_price}
    if discount:
        props["折扣%"] = {"number": discount}
    if pay:
        props["付款方式"] = {"select": {"name": pay}}
    props = {k: v for k, v in props.items() if v is not None}
    return api.post(
        "/pages", {"parent": {"database_id": DB["wine_sales"]}, "properties": props}
    )


def create_tea_record(order_id, order_date, customer_name, items, amount, cost, pay):
    gross = (amount - cost) if cost else 0
    margin = round(gross / amount * 100, 1) if amount and cost else 0
    props = {
        "訂單編號": {"title": [{"type": "text", "text": {"content": order_id}}]},
        "出貨日期": {"date": {"start": order_date}},
        "客戶名稱": rt(customer_name),
        "品項明細": rt(items),
        "訂購金額": {"number": amount},
        "備註": rt(""),
    }
    if cost:
        props["成本"] = {"number": cost}
        props["毛利"] = {"number": gross}
        props["毛利率%"] = {"number": margin}
    if pay:
        props["付款方式"] = {"select": {"name": pay}}
    return api.post(
        "/pages", {"parent": {"database_id": DB["tea_sales"]}, "properties": props}
    )


def sync_to_unified(
    brand, order_id, order_date, customer_name, item_desc, qty, amount, cost, gross, pay
):
    """同步到全品牌統一總表：新增銷售紀錄 + 更新客戶最後購買日/累計消費（找不到則新增）"""
    bz = BRAND_ZH[brand]
    # 1. 銷售紀錄總表
    props = {
        "訂單編號": {"title": [{"type": "text", "text": {"content": order_id}}]},
        "品牌": {"select": {"name": bz}},
        "出貨日期": {"date": {"start": order_date}},
        "客戶名稱": rt(customer_name),
        "品項": rt(item_desc),
    }
    if qty:
        props["數量"] = {"number": qty}
    if amount:
        props["金額"] = {"number": amount}
    if cost:
        props["成本"] = {"number": cost}
    if gross:
        props["毛利"] = {"number": gross}
    if pay:
        props["付款方式"] = {"select": {"name": pay}}
    api.post(
        "/pages", {"parent": {"database_id": UNIFIED_SALES_DB}, "properties": props}
    )
    print(f"  ✅ 統一銷售紀錄總表已新增 {order_id}")

    # 2. 客戶總表：同名同品牌則更新，否則新增
    found = None
    for r in api.query_db(UNIFIED_CUSTOMER_DB):
        p = r["properties"]
        title = p.get("客戶姓名", {}).get("title", [])
        nm = title[0]["plain_text"] if title else ""
        bsel = p.get("品牌", {}).get("select") or {}
        if nm == customer_name and bsel.get("name") == bz:
            found = r
            break
    if found:
        cur = found["properties"].get("累計消費", {}).get("number") or 0
        api.patch(
            f"/pages/{found['id']}",
            {
                "properties": {
                    "最後購買日": {"date": {"start": order_date}},
                    "累計消費": {"number": cur + amount},
                }
            },
        )
        print(
            f"  ✅ 統一總表客戶更新：{customer_name} 最後購買日={order_date} 累計NT${cur+amount:,.0f}"
        )
    else:
        api.post(
            "/pages",
            {
                "parent": {"database_id": UNIFIED_CUSTOMER_DB},
                "properties": {
                    "客戶姓名": {
                        "title": [{"type": "text", "text": {"content": customer_name}}]
                    },
                    "品牌": {"select": {"name": bz}},
                    "累計消費": {"number": amount},
                    "最後購買日": {"date": {"start": order_date}},
                },
            },
        )
        print(f"  ✅ 統一總表新增客戶：{customer_name}（{bz}）")


def ask_payment(options):
    print("付款方式：")
    for i, o in enumerate(options, 1):
        print(f"  {i}. {o}")
    c = input(f"請選擇 (1-{len(options)})：").strip()
    try:
        return options[int(c) - 1]
    except (ValueError, IndexError):
        return options[0]


def main():
    print("\n🏢 鉅鑫管理顧問 — 訂單快速記帳")
    print("─" * 35)

    print("品牌：")
    print("  1. 🐟 鑫海產")
    print("  2. 🍷 鑫酒藏")
    print("  3. 🍵 鑫茶坊")
    choice = input("請選擇 (1-3)：").strip()
    brand = BRAND_MENU.get(choice)
    if not brand:
        print("❌ 無效選擇")
        return

    name_input = input("客戶姓名或編號：").strip()
    customer_page_id, customer_name = find_customer(brand, name_input)
    if customer_page_id:
        print(f"  ✅ 找到客戶：{customer_name}")
    else:
        print(f"  ⚠️  新客戶：{customer_name}（不更新累計）")

    order_date = input(f"出貨日期（YYYY-MM-DD，留空=今天 {date.today()}）：").strip()
    if not order_date:
        order_date = str(date.today())

    order_id = get_next_order_id(brand)
    amount = 0
    numbers_row = None

    # ── 🐟 鑫海產 ───────────────────────────────────────────────
    if brand == "seafood":
        prices, price_date = get_market_prices()
        if prices:
            print(f"\n📊 市場行情參考（{price_date}）：")
            for fish, mid in list(prices.items())[:10]:
                print(f"   {fish}：NT${mid:.0f}/kg")
            print()
        items = input("品項明細（例：黑鮪魚金三角×8兩）：").strip()
        amount = int(input("訂購金額（NT$）：").strip().replace(",", ""))
        cost_input = input("成本（NT$，可留空）：").strip().replace(",", "")
        cost = int(cost_input) if cost_input else None
        market_ref = input(
            "市場參考單價（可留空，例：黑鮪魚金三角 6000/台斤）："
        ).strip()
        pay = ask_payment(["LINE轉帳", "現金", "匯款"])
        gross = (amount - cost) if cost else None
        margin = round(gross / amount * 100, 1) if gross and amount else None
        if margin:
            print(f"  📈 毛利率：{margin}%（毛利 NT${gross:,}）")
        # Numbers 欄位順序：出貨日期, 訂單編號, 客戶名稱, 品項明細, 訂購金額, 成本, 毛利, 毛利率%, 付款方式, 備註
        numbers_row = [
            order_date,
            order_id,
            customer_name,
            items,
            amount,
            cost,
            gross,
            margin,
            pay,
            market_ref,
        ]

    # ── 🍷 鑫酒藏 ───────────────────────────────────────────────
    elif brand == "wine":
        product_name = input("商品名稱：").strip()
        product_code = input("商品代碼（可留空）：").strip()
        winery = input("品牌/酒廠（可留空）：").strip()
        category = input("類別（紅酒/白酒/氣泡酒/威士忌/其他）：").strip() or "紅酒"
        unit_price = int(input("單價（NT$）：").strip().replace(",", ""))
        qty = int(input("數量：").strip())
        disc_input = input("折扣%（無折扣留空）：").strip()
        discount = float(disc_input) if disc_input else 0
        subtotal = unit_price * qty
        final = round(subtotal * (1 - discount / 100), 0) if discount else subtotal
        amount = int(final)
        print(f"  💰 折後小計：NT${amount:,}")
        pay = ask_payment(["VIP優惠價", "匯款", "LINE轉帳", "現金"])
        # Numbers 欄位順序：出貨日期, 出貨單號, 客戶名稱, 商品代碼, 商品名稱, 品牌/酒廠, 類別, 單價, 數量, 小計, 折扣%, 折後小計, 業務, 備註
        numbers_row = [
            order_date,
            order_id,
            customer_name,
            product_code,
            product_name,
            winery,
            category,
            unit_price,
            qty,
            subtotal,
            discount or None,
            amount,
            "",
            "",
        ]

    # ── 🍵 鑫茶坊 ───────────────────────────────────────────────
    elif brand == "tea":
        items = input("品項明細（例：阿里山金萱150g×2）：").strip()
        amount = int(input("訂購金額（NT$）：").strip().replace(",", ""))
        cost_input = input("成本（NT$，可留空）：").strip().replace(",", "")
        cost = int(cost_input) if cost_input else None
        pay = ask_payment(["LINE轉帳", "現金", "匯款"])
        gross = (amount - cost) if cost else None
        margin = round(gross / amount * 100, 1) if gross and amount else None
        if margin:
            print(f"  📈 毛利率：{margin}%（毛利 NT${gross:,}）")
        numbers_row = [
            order_date,
            order_id,
            customer_name,
            items,
            amount,
            cost,
            gross,
            margin,
            pay,
            "",
        ]

    # ── 1. 寫入本機 Numbers（主）──────────────────────────────
    print(f"\n💾 寫入本機...")
    write_to_numbers(brand, numbers_row)
    update_numbers_customer(brand, customer_name, amount)

    # ── 2. 備份至 Notion ────────────────────────────────────────
    print(f"☁️  備份 Notion...")
    if brand == "seafood":
        create_seafood_record(
            order_id,
            order_date,
            customer_name,
            items,
            amount,
            cost if cost_input else None,
            market_ref,
            pay,
        )
    elif brand == "wine":
        create_wine_record(
            order_id,
            order_date,
            customer_name,
            product_name,
            product_code,
            winery,
            category,
            unit_price,
            qty,
            discount,
            pay,
        )
    elif brand == "tea":
        create_tea_record(
            order_id,
            order_date,
            customer_name,
            items,
            amount,
            cost if cost_input else None,
            pay,
        )

    if customer_page_id:
        new_total = update_customer_total(brand, customer_page_id, amount)
        print(f"  ✅ Notion 客戶累計消費更新：NT$ {new_total:,}")

    # ── 3. 同步全品牌統一總表（維持回購提醒資料正確）────────────
    print("🗂️  同步統一總表...")
    item_desc = items if brand in ("seafood", "tea") else product_name
    qty_val = qty if brand == "wine" else None
    cost_val = cost if (brand in ("seafood", "tea") and cost_input) else None
    gross_val = gross if brand in ("seafood", "tea") else None
    sync_to_unified(
        brand,
        order_id,
        order_date,
        customer_name,
        item_desc,
        qty_val,
        amount,
        cost_val,
        gross_val,
        pay,
    )

    print(f"\n✅ {order_id} 完成 — 本機已儲存，Notion 已備份")

    again = input("\n繼續輸入下一筆？(y/N)：").strip().lower()
    if again == "y":
        main()


if __name__ == "__main__":
    main()
