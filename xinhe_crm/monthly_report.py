#!/usr/bin/env python3
"""炘和月報：每月 1 日統計上個月的個人銷售＋炘和訂單 → 在 Notion「炘和管理顧問」頁下建報表。

2026-11-16 起取代鉅鑫的 notion_crm/monthly_report.py（讀鉅鑫全品牌銷售紀錄）。
- 依營業線（嚴選海鮮／世界名酒／台灣精品茶…）統計
- 分開列「個人（未開發票）」與「公司（有開發票）」——兩者稅務上不能混算
- 狀態「取消」的訂單不計
"""
import os
import sys
from collections import defaultdict
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from xinhe_crm.notion import CFG, call, getter, query_all  # noqa: E402

SOURCES = [("personal_sales_db", "個人（未開發票）"), ("orders_db", "公司（有開發票）")]


def last_month():
    end = date.today().replace(day=1) - timedelta(days=1)
    return end.year, end.month


def fetch(year, month):
    start = f"{year}-{month:02d}-01"
    end = f"{year + 1}-01-01" if month == 12 else f"{year}-{month + 1:02d}-01"
    flt = {
        "and": [
            {"property": "下單日", "date": {"on_or_after": start}},
            {"property": "下單日", "date": {"before": end}},
        ]
    }
    rows, names = [], {}
    for key, kind in SOURCES:
        for r in query_all(key, flt):
            g = getter(r)
            if g("狀態") == "取消":
                continue
            cid = (g("客戶") or [None])[0]
            if cid and cid not in names:
                names[cid] = getter(call("GET", f"/pages/{cid}"))("姓名")
            rows.append(
                {
                    "kind": kind,
                    "id": g("訂單編號"),
                    "date": g("下單日"),
                    "line": g("營業線") or "未分類",
                    "customer": names.get(cid, "—"),
                    "amount": g("金額") or 0,
                    "cost": g("成本") or 0,
                }
            )
    return sorted(rows, key=lambda r: (r["date"], r["id"]))


def para(text):
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def heading(text, level=2):
    t = f"heading_{level}"
    return {
        "object": "block",
        "type": t,
        t: {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def summary_lines(rows, key):
    stats = defaultdict(lambda: [0, 0, 0])
    for r in rows:
        s = stats[r[key]]
        s[0] += 1
        s[1] += r["amount"]
        s[2] += r["cost"]
    out = []
    for name, (n, rev, cost) in sorted(stats.items()):
        margin = (rev - cost) / rev * 100 if rev else 0
        out.append(
            para(
                f"{name}：{n} 筆・營收 NT$ {rev:,.0f}・成本 NT$ {cost:,.0f}・毛利 NT$ {rev - cost:,.0f}（{margin:.1f}%）"
            )
        )
    return out


def build_blocks(rows):
    rev = sum(r["amount"] for r in rows)
    cost = sum(r["cost"] for r in rows)
    margin = (rev - cost) / rev * 100 if rev else 0
    divider = {"object": "block", "type": "divider", "divider": {}}
    blocks = [
        heading("📊 總覽"),
        para(f"總營收：NT$ {rev:,.0f}"),
        para(f"總成本：NT$ {cost:,.0f}"),
        para(f"毛利：NT$ {rev - cost:,.0f}（毛利率 {margin:.1f}%）"),
        (
            para("成本空白的訂單以 0 計，毛利會偏高；請到 Notion 補成本。")
            if any(not r["cost"] for r in rows)
            else None
        ),
        divider,
        heading("🧾 個人／公司"),
        *summary_lines(rows, "kind"),
        divider,
        heading("🏪 各營業線"),
        *summary_lines(rows, "line"),
        divider,
        heading("📋 訂單清單"),
    ]
    blocks += [
        para(
            f"{r['date']}  {r['id']}  {r['line']}  {r['customer']}  NT${r['amount']:,.0f}（{r['kind']}）"
        )
        for r in rows
    ]
    return [b for b in blocks if b]


def main():
    year, month = last_month()
    print(f"📊 生成 {year}年{month:02d}月 炘和營收報表...")
    rows = fetch(year, month)
    print(f"  找到 {len(rows)} 筆訂單")
    if not rows:
        print("  ⚠️  本月無訂單，跳過")
        return
    blocks = build_blocks(rows)
    if "--dry-run" in sys.argv:
        for b in blocks:
            print(
                "  ",
                (
                    b[b["type"]]["rich_text"][0]["text"]["content"]
                    if b["type"] != "divider"
                    else "—"
                ),
            )
        return
    page = call(
        "POST",
        "/pages",
        {
            "parent": {"type": "page_id", "page_id": CFG["page_id"]},
            "icon": {"type": "emoji", "emoji": "📈"},
            "properties": {
                "title": [
                    {
                        "type": "text",
                        "text": {"content": f"{year}年{month:02d}月 炘和營收報表"},
                    }
                ]
            },
            "children": blocks[:100],
        },
    )
    # Notion 一次最多 100 個區塊，訂單多時其餘分批接在後面，不能靜默截掉
    for i in range(100, len(blocks), 100):
        call(
            "PATCH", f"/blocks/{page['id']}/children", {"children": blocks[i : i + 100]}
        )
    print(f"  ✅ 報表已推送 Notion：{page['id']}（{len(blocks)} 個區塊）")


if __name__ == "__main__":
    main()
