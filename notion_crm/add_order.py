#!/usr/bin/env python3
"""
新增訂單 → 自動推送 Notion + 輸出發票/出貨單

用法：
  python3 add_order.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date
import notion_api as api
from config import DB, BRAND_LABELS, BRAND_PREFIXES

BRAND_MENU = {
    "1": "seafood",
    "2": "wine",
    "3": "tea",
}

def get_next_order_id(brand):
    prefix = BRAND_PREFIXES[brand]
    rows = api.query_db(DB["sales"], {
        "property": "品牌",
        "select": {"equals": BRAND_LABELS[brand]}
    })
    nums = []
    for r in rows:
        title = r["properties"]["訂單編號"]["title"]
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
    db_id = DB[brand]
    rows = api.query_db(db_id)
    for r in rows:
        title_prop = r["properties"]["姓名"]["title"]
        customer_name = title_prop[0]["plain_text"] if title_prop else ""
        id_prop = r["properties"].get("客戶編號", {}).get("rich_text", [])
        customer_id = id_prop[0]["plain_text"] if id_prop else ""
        if name_or_id in customer_name or name_or_id == customer_id:
            return r["id"], customer_name
    return None, name_or_id

def update_customer_total(brand, page_id, amount):
    page = api.get(f"/pages/{page_id}")
    current = page["properties"].get("累計消費金額", {}).get("number") or 0
    api.patch(f"/pages/{page_id}", {
        "properties": {
            "累計消費金額": {"number": current + amount}
        }
    })
    return current + amount

def create_sales_record(order_id, order_date, customer_name, brand, items, amount, cost):
    props = {
        "訂單編號": {"title": [{"type": "text", "text": {"content": order_id}}]},
        "訂單日期": {"date": {"start": order_date}},
        "客戶姓名": {"rich_text": [{"type": "text", "text": {"content": customer_name}}]},
        "品牌": {"select": {"name": BRAND_LABELS[brand]}},
        "購買品項": {"rich_text": [{"type": "text", "text": {"content": items}}]},
        "訂購金額": {"number": amount},
    }
    if cost:
        props["成本"] = {"number": cost}
    return api.post("/pages", {"parent": {"type": "database_id", "database_id": DB["sales"]}, "properties": props})

def print_invoice(order_id, order_date, customer_name, items, amount):
    print("\n" + "="*45)
    print("           發  票")
    print("="*45)
    print(f"  訂單編號：{order_id}")
    print(f"  日    期：{order_date}")
    print(f"  客    戶：{customer_name}")
    print("-"*45)
    print(f"  品    項：{items}")
    print("-"*45)
    print(f"  應付金額：NT$ {amount:,}")
    print("="*45)
    print()
    print("="*45)
    print("           出  貨  單")
    print("="*45)
    print(f"  出貨日期：{order_date}")
    print(f"  收貨人員：{customer_name}")
    print(f"  出貨品項：{items}")
    print(f"  訂單金額：NT$ {amount:,}")
    print("  簽    收：_______________")
    print("="*45)

def main():
    print("\n🏢 鉅鑫管理顧問 — 訂單快速記帳")
    print("─"*35)

    # 選品牌
    print("品牌：")
    print("  1. 🐟 鑫海產")
    print("  2. 🍷 鑫酒藏")
    print("  3. 🍵 鑫茶坊")
    choice = input("請選擇 (1-3)：").strip()
    brand = BRAND_MENU.get(choice)
    if not brand:
        print("❌ 無效選擇")
        return

    # 客戶
    name_input = input("客戶姓名或編號：").strip()
    customer_page_id, customer_name = find_customer(brand, name_input)
    if customer_page_id:
        print(f"  ✅ 找到客戶：{customer_name}")
    else:
        print(f"  ⚠️  新客戶：{customer_name}（不更新累計）")

    # 訂單內容
    items = input("品項（例：干貝M×2盒）：").strip()
    amount = int(input("訂購金額（NT$）：").strip().replace(",", ""))
    cost_input = input("成本（NT$，可留空）：").strip().replace(",", "")
    cost = int(cost_input) if cost_input else None

    order_date = input(f"訂單日期（YYYY-MM-DD，留空 = 今天 {date.today()}）：").strip()
    if not order_date:
        order_date = str(date.today())

    # 產生訂單編號
    order_id = get_next_order_id(brand)

    # 寫入 Notion
    print(f"\n⏳ 寫入 Notion...")
    create_sales_record(order_id, order_date, customer_name, brand, items, amount, cost)

    # 更新客戶累計消費
    if customer_page_id:
        new_total = update_customer_total(brand, customer_page_id, amount)
        print(f"  ✅ 客戶累計消費更新：NT$ {new_total:,}")

    print(f"  ✅ 銷售紀錄已建立：{order_id}")

    # 輸出發票 + 出貨單
    print_invoice(order_id, order_date, customer_name, items, amount)

    # 詢問是否繼續
    again = input("繼續輸入下一筆？(y/N)：").strip().lower()
    if again == "y":
        main()

if __name__ == "__main__":
    main()
