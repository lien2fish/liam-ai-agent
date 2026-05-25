#!/usr/bin/env python3
"""
update_dashboard.py — Personal Finance OS 首頁同步工具
讀取 Notion 資料庫的最新數據，自動更新首頁摘要欄位。

使用方式：
  1. 設定下方 CONFIG 區塊（NOTION_TOKEN + DB IDs）
  2. python3 update_dashboard.py
  3. 執行時間約 5 秒

取得 Notion Token：https://www.notion.so/profile/integrations
取得 DB ID：開啟資料庫頁面 → 複製網址中的 32 位英數字串
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date

# ── 設定區（填入你的資料）────────────────────────────────────────────────────
CONFIG = {
    # Notion Integration Token（格式：ntn_...）
    "token": os.environ.get("NOTION_TOKEN", "YOUR_NOTION_TOKEN_HERE"),
    # 以下 ID 從 Notion 資料庫網址取得（32 位英數，去掉橫線）
    "assets_db_id": os.environ.get("ASSETS_DB_ID", "YOUR_ASSETS_DB_ID_HERE"),
    "liab_db_id": os.environ.get("LIAB_DB_ID", "YOUR_LIABILITIES_DB_ID_HERE"),
    "snapshot_db_id": os.environ.get("SNAPSHOT_DB_ID", "YOUR_SNAPSHOT_DB_ID_HERE"),
    # 首頁 page_id（開啟主頁面 → 複製網址中的 32 位字串）
    "homepage_id": os.environ.get("HOMEPAGE_ID", "YOUR_HOMEPAGE_PAGE_ID_HERE"),
}
# ─────────────────────────────────────────────────────────────────────────────


def api(token, method, path, body=None):
    url = f"https://api.notion.com/v1{path}"
    data = json.dumps(body, ensure_ascii=False).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"API {e.code}: {e.read().decode()[:200]}")


def query_all(token, db_id, sorts=None):
    """取出資料庫所有筆資料（處理分頁）。"""
    results, cursor = [], None
    while True:
        body = {"page_size": 100}
        if sorts:
            body["sorts"] = sorts
        if cursor:
            body["start_cursor"] = cursor
        resp = api(token, "POST", f"/databases/{db_id}/query", body)
        results.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    return results


def num(page, prop):
    """取 number 屬性值，不存在回傳 0。"""
    p = page.get("properties", {}).get(prop, {})
    return p.get("number") or 0


def title_text(page, prop):
    """取 title 屬性的文字。"""
    p = page.get("properties", {}).get(prop, {})
    arr = p.get("title", [])
    return arr[0].get("plain_text", "") if arr else ""


def patch_block(token, block_id, block_type, rich_text):
    """更新任意 block 的 rich_text。"""
    api(
        token,
        "PATCH",
        f"/blocks/{block_id}",
        {block_type: {"rich_text": [{"type": "text", "text": {"content": rich_text}}]}},
    )


def get_homepage_blocks(token, homepage_id):
    """取首頁所有 blocks（一層）。"""
    resp = api(token, "GET", f"/blocks/{homepage_id}/children?page_size=100")
    return resp.get("results", [])


def find_block_by_snippet(blocks, block_type, snippet):
    """找包含特定文字片段的 block。"""
    for b in blocks:
        if b["type"] != block_type:
            continue
        rt = b.get(block_type, {}).get("rich_text", [])
        text = "".join(t.get("plain_text", "") for t in rt)
        if snippet in text:
            return b["id"]
    return None


def run(cfg):
    token = cfg["token"]
    today_str = date.today().strftime("%Y-%m")

    print("📡 讀取 Assets 資料庫...")
    assets = query_all(token, cfg["assets_db_id"])
    total_assets = sum(num(a, "當前金額 / Current Value") for a in assets)

    cat_totals = {}
    for a in assets:
        cat = (
            a.get("properties", {}).get("類別 / Category", {}).get("select", {}) or {}
        ).get("name", "其他")
        cat_totals[cat] = cat_totals.get(cat, 0) + num(a, "當前金額 / Current Value")

    sorted_cats = sorted(cat_totals.items(), key=lambda x: -x[1])
    alloc = (
        "  ·  ".join(f"{c} {v / total_assets * 100:.1f}%" for c, v in sorted_cats[:4])
        if total_assets
        else "無資料"
    )

    print("📡 讀取 Liabilities 資料庫...")
    liabs = query_all(token, cfg["liab_db_id"])
    total_liab = sum(num(l, "餘額 / Balance") for l in liabs)
    net_worth = total_assets - total_liab

    print("📡 讀取 Monthly Snapshot 資料庫...")
    snaps = query_all(
        token,
        cfg["snapshot_db_id"],
        sorts=[{"property": "月份 / Month", "direction": "descending"}],
    )
    if snaps:
        latest = snaps[0]
        income = num(latest, "月收入 / Monthly Income")
        expense = num(latest, "月支出 / Monthly Expenses")
        surplus = num(latest, "月結餘 / Net Cash Flow")
        savings_rate = (surplus / income * 100) if income else 0
        snap_month = title_text(latest, "月份 / Month")
    else:
        income = expense = surplus = savings_rate = 0
        snap_month = today_str

    surplus_fmt = f"NT${surplus:,.0f}" if surplus >= 0 else f"-NT${abs(surplus):,.0f}"

    print(f"\n📊 計算結果（{snap_month}）：")
    print(f"  總資產：NT${total_assets:,.0f}")
    print(f"  總負債：NT${total_liab:,.0f}")
    print(f"  淨  值：NT${net_worth:,.0f}")
    print(f"  月收入：NT${income:,.0f}")
    print(f"  月支出：NT${expense:,.0f}")
    print(f"  月結餘：{surplus_fmt}")
    print(f"  儲蓄率：{savings_rate:.1f}%")
    print(f"  配  置：{alloc}")

    print("\n✏️  更新首頁 blocks...")
    blocks = get_homepage_blocks(token, cfg["homepage_id"])

    # 搜尋並更新各 block
    updates = [
        # (block_type, 搜尋片段, 新文字)
        (
            "callout",
            "淨值",
            f"💎 淨值  NT${net_worth:,.0f}\n總資產 NT${total_assets:,.0f}  ·  總負債 NT${total_liab:,.0f}",
        ),
        ("callout", "月收入", f"💰 月收入\nNT${income:,.0f}"),
        ("callout", "月支出", f"💸 月支出\nNT${expense:,.0f}"),
        ("callout", "月結餘", f"📊 月結餘\n{surplus_fmt}"),
        ("callout", "儲蓄率", f"🎯 儲蓄率\n{savings_rate:.1f}%"),
        ("paragraph", "資產配置：", f"資產配置：{alloc}"),
    ]

    updated = 0
    for btype, snippet, new_text in updates:
        bid = find_block_by_snippet(blocks, btype, snippet)
        if bid:
            patch_block(token, bid, btype, new_text)
            print(f"  ✅ {snippet[:10]}...")
            updated += 1
        else:
            # 搜尋 column_list 內部的 blocks
            for b in blocks:
                if b["type"] == "column_list":
                    sub = api(token, "GET", f"/blocks/{b['id']}/children?page_size=20")
                    for col in sub.get("results", []):
                        if col["type"] != "column":
                            continue
                        col_blocks = api(
                            token, "GET", f"/blocks/{col['id']}/children?page_size=20"
                        ).get("results", [])
                        bid2 = find_block_by_snippet(col_blocks, btype, snippet)
                        if bid2:
                            patch_block(token, bid2, btype, new_text)
                            print(f"  ✅ {snippet[:10]}... (in column)")
                            updated += 1
                            break

    # 更新月份標題
    for b in blocks:
        if b["type"] == "heading_2":
            rt = b.get("heading_2", {}).get("rich_text", [])
            text = "".join(t.get("plain_text", "") for t in rt)
            if "本月財務指標" in text:
                api(
                    token,
                    "PATCH",
                    f"/blocks/{b['id']}",
                    {
                        "heading_2": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": f"📅 本月財務指標  ·  {snap_month}"
                                    },
                                }
                            ]
                        }
                    },
                )
                print(f"  ✅ 月份標題 → {snap_month}")
                break

    print(f"\n🎉 完成！共更新 {updated} 個區塊。")
    page_url = f"https://www.notion.so/{cfg['homepage_id'].replace('-', '')}"
    print(f"   頁面連結：{page_url}")


def check_config(cfg):
    missing = [k for k, v in cfg.items() if "YOUR_" in str(v)]
    if missing:
        print("❌ 請先在 update_dashboard.py 填入以下設定：")
        for k in missing:
            print(f"   - {k}")
        print("\n說明請見腳本頂部的設定區。")
        sys.exit(1)


if __name__ == "__main__":
    check_config(CONFIG)
    run(CONFIG)
