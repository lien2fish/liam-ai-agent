#!/usr/bin/env python3
"""
每月自動生成營收報表 → 推送 Notion
cron: 0 8 1 * * python3 /Users/lien/Downloads/Liam\ AI\ agent/notion_crm/monthly_report.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, timedelta
from collections import defaultdict
import notion_api as api
from config import DB, BRAND_LABELS

def get_last_month():
    today = date.today()
    first_of_month = today.replace(day=1)
    last_month_end = first_of_month - timedelta(days=1)
    return last_month_end.year, last_month_end.month

def fetch_sales(year, month):
    start = f"{year}-{month:02d}-01"
    if month == 12:
        end = f"{year+1}-01-01"
    else:
        end = f"{year}-{month+1:02d}-01"

    rows = api.query_db(DB["sales"], {
        "and": [
            {"property": "訂單日期", "date": {"on_or_after": start}},
            {"property": "訂單日期", "date": {"before": end}},
        ]
    })
    return rows

def summarize(rows):
    stats = defaultdict(lambda: {"訂單數": 0, "營收": 0, "成本": 0})
    for r in rows:
        props = r["properties"]
        brand = props.get("品牌", {}).get("select", {})
        brand_name = brand.get("name", "未分類") if brand else "未分類"
        amount = props.get("訂購金額", {}).get("number") or 0
        cost = props.get("成本", {}).get("number") or 0
        stats[brand_name]["訂單數"] += 1
        stats[brand_name]["營收"] += amount
        stats[brand_name]["成本"] += cost
    return stats

def build_report_blocks(year, month, stats, rows):
    total_revenue = sum(v["營收"] for v in stats.values())
    total_cost = sum(v["成本"] for v in stats.values())
    total_profit = total_revenue - total_cost
    margin = (total_profit / total_revenue * 100) if total_revenue else 0

    blocks = []

    def heading2(text):
        return {"object": "block", "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]}}

    def heading3(text):
        return {"object": "block", "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": text}}]}}

    def para(text):
        return {"object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]}}

    def divider():
        return {"object": "block", "type": "divider", "divider": {}}

    # 總覽
    blocks.append(heading2("📊 總覽"))
    blocks.append(para(f"總營收：NT$ {total_revenue:,}"))
    blocks.append(para(f"總成本：NT$ {total_cost:,}"))
    blocks.append(para(f"毛利：NT$ {total_profit:,}　（毛利率 {margin:.1f}%）"))
    blocks.append(divider())

    # 各品牌
    blocks.append(heading2("🏪 各品牌明細"))
    for brand, v in sorted(stats.items()):
        profit = v["營收"] - v["成本"]
        margin_b = (profit / v["營收"] * 100) if v["營收"] else 0
        blocks.append(heading3(brand))
        blocks.append(para(f"訂單數：{v['訂單數']} 筆"))
        blocks.append(para(f"營收：NT$ {v['營收']:,}"))
        blocks.append(para(f"成本：NT$ {v['成本']:,}"))
        blocks.append(para(f"毛利：NT$ {profit:,}　（{margin_b:.1f}%）"))
    blocks.append(divider())

    # 訂單清單
    blocks.append(heading2("📋 訂單清單"))
    for r in rows:
        props = r["properties"]
        order_id = props["訂單編號"]["title"][0]["plain_text"] if props["訂單編號"]["title"] else "-"
        customer_rt = props.get("客戶姓名", {}).get("rich_text", [])
        customer = customer_rt[0]["plain_text"] if customer_rt else "-"
        amount = props.get("訂購金額", {}).get("number") or 0
        order_date = props.get("訂單日期", {}).get("date", {})
        date_str = order_date.get("start", "-") if order_date else "-"
        blocks.append(para(f"{date_str}  {order_id}  {customer}  NT${amount:,}"))

    return blocks

def push_to_notion(year, month, blocks):
    title = f"{year}年{month:02d}月 營收報表"
    page = api.post("/pages", {
        "parent": {"type": "page_id", "page_id": DB["crm_page"]},
        "icon": {"type": "emoji", "emoji": "📈"},
        "properties": {
            "title": [{"type": "text", "text": {"content": title}}]
        },
        "children": blocks
    })
    return page["id"]

def main():
    year, month = get_last_month()
    print(f"📊 生成 {year}年{month:02d}月 營收報表...")

    rows = fetch_sales(year, month)
    print(f"  找到 {len(rows)} 筆訂單")

    if not rows:
        print("  ⚠️  本月無訂單，跳過")
        return

    stats = summarize(rows)
    blocks = build_report_blocks(year, month, stats, rows)
    page_id = push_to_notion(year, month, blocks)

    total = sum(v["營收"] for v in stats.values())
    profit = sum(v["營收"] - v["成本"] for v in stats.values())
    print(f"  ✅ 報表已推送 Notion")
    print(f"  總營收：NT$ {total:,}　毛利：NT$ {profit:,}")
    print(f"  頁面 ID：{page_id}")

if __name__ == "__main__":
    main()
