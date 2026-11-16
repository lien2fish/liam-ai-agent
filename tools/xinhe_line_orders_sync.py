#!/usr/bin/python3
"""
把 LINE 助理建的炘和個人銷售，補記進桌面的個人帳務表。

LINE 只寫得到 Notion「個人銷售（未開發票）」，備註帶 profile.js 的 syncNote。
這支找出那些單，寫進 個人帳務_2026.xlsx 的「個人銷售」頁，成功才把備註改成「已記」。
寫入前先查單號，重跑不會重複。

用法（homebrew 的 python3 沒有 openpyxl，要用系統內建那支）：
  /usr/bin/python3 tools/xinhe_line_orders_sync.py           # 只列出會做什麼
  /usr/bin/python3 tools/xinhe_line_orders_sync.py --apply   # 真的寫入

金鑰：config/.xinhe_notion_token（只連炘和頁面與個人銷售的 integration，不可用鉅鑫那把）。
"""
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
PROFILE = (ROOT / "line_assistant/profile.js").read_text()
WRANGLER = (ROOT / "line_assistant/wrangler.toml").read_text()

# 跟 Worker 讀同一份設定，兩邊才不會改一邊漏一邊
SYNC_NOTE = re.search(r'syncNote:\s*"([^"]+)"', PROFILE).group(1)
SALES_DB = re.search(r'XINHE_SALES_DB\s*=\s*"([0-9a-f]+)"', WRANGLER).group(1)

YEAR = date.today().year
BOOK = (
    Path.home()
    / f"Desktop/炘和管理顧問/01_個人帳務_目前使用/{YEAR}/個人帳務_{YEAR}.xlsx"
)
BACKUP_DIR = Path.home() / "Desktop/炘和管理顧問/_備份_LINE同步"
SHEET = "個人銷售"
# Notion 收款方式 → 帳務表收款帳戶（選項名稱不同）
PAY_MAP = {
    "個人帳戶轉帳": "個人銀行帳戶",
    "現金": "現金",
    "LINE Pay": "LINE Pay",
    "其他": "其他",
}


def token():
    p = ROOT / "config/.xinhe_notion_token"
    if not p.exists():
        sys.exit(
            f"❌ 找不到 {p}。請先在 Notion 建只連炘和的 integration，把金鑰存進這個檔。"
        )
    return p.read_text().strip()


def notion(method, path, body=None):
    req = urllib.request.Request(
        f"https://api.notion.com/v1{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        method=method,
    )
    return json.load(urllib.request.urlopen(req))


def plain(prop):
    if not prop:
        return None
    t = prop["type"]
    if t in ("title", "rich_text"):
        return "".join(x["plain_text"] for x in prop[t])
    if t == "number":
        return prop["number"]
    if t == "select":
        return (prop["select"] or {}).get("name")
    if t == "date":
        return (prop["date"] or {}).get("start")
    if t == "relation":
        return [r["id"] for r in prop["relation"]]
    return None


def pending_orders():
    out, cursor = [], None
    while True:
        body = {
            "page_size": 100,
            "filter": {"property": "備註", "rich_text": {"contains": SYNC_NOTE}},
        }
        if cursor:
            body["start_cursor"] = cursor
        r = notion("POST", f"/databases/{SALES_DB}/query", body)
        out += r["results"]
        if not r["has_more"]:
            break
        cursor = r["next_cursor"]
    names = {}
    orders = []
    for page in out:
        p = page["properties"]
        cids = plain(p["客戶"]) or []
        if cids and cids[0] not in names:
            names[cids[0]] = plain(
                notion("GET", f"/pages/{cids[0]}")["properties"]["姓名"]
            )
        note = plain(p["備註"]) or ""
        orders.append(
            {
                "page_id": page["id"],
                "id": plain(p["訂單編號"]),
                "date": plain(p["下單日"]),
                "customer": names.get(cids[0]) if cids else None,
                "line": plain(p["營業線"]),
                "items": plain(p["商品"]),
                "qty": plain(p["數量"]),
                "unit_price": plain(p["單價"]),
                "amount": plain(p["金額"]),
                "cost": plain(p["成本"]),
                "pay": plain(p["收款方式"]),
                "status": plain(p["狀態"]),
                "raw_note": note,
                "note": note.replace(SYNC_NOTE, "").strip("｜ "),
            }
        )
    return sorted(orders, key=lambda o: o["id"])


def numbers_running():
    return (
        subprocess.run(["pgrep", "-x", "Numbers"], capture_output=True).returncode == 0
    )


def row_values(o):
    paid = o["status"] in ("已收款", "完成")
    note = "LINE 建檔" + (f"；{o['note']}" if o["note"] else "")
    # 第 11 欄（毛利）是預先鋪好的公式，不寫
    return {
        1: o["id"],
        2: datetime.strptime(o["date"], "%Y-%m-%d"),
        3: o["customer"],
        4: o["line"],
        5: o["items"],
        6: o["qty"],
        8: o["unit_price"],
        9: o["amount"],
        10: o["cost"],
        12: "已收" if paid else "未收",
        14: PAY_MAP.get(o["pay"]) if o["pay"] else None,
        15: note,
    }


def main():
    apply = "--apply" in sys.argv
    orders = pending_orders()
    if not orders:
        print("沒有待記的 LINE 訂單。")
        return
    numbers_copy = BOOK.with_suffix(".numbers")
    if numbers_copy.exists():
        sys.exit(
            f"❌ 同資料夾有 {numbers_copy.name}，正本可能已經換成 Numbers 版，這支只會寫 xlsx。先確認要記在哪一份。"
        )
    if apply and numbers_running():
        sys.exit("❌ Numbers 開著。先關掉再跑，不然存檔會被它蓋回去。")

    wb = openpyxl.load_workbook(BOOK)
    ws = wb[SHEET]
    have = {ws.cell(r, 1).value for r in range(2, ws.max_row + 1)}
    print(f"{'寫入' if apply else '預覽（加 --apply 才會寫）'}：{len(orders)} 張待記\n")

    todo, problems = [], []
    for o in orders:
        label = (
            f"{o['id']}　{o['date']}　{o['customer']}　{o['line']}　{o['amount']:,.0f}"
        )
        if not o["customer"]:
            problems.append(f"⚠️ {label}：沒有關聯客戶，跳過")
        elif o["id"] in have:
            print(f"── {label}\n  帳務表已有這張，只補 Notion 標記")
            todo.append((o, None))
        else:
            todo.append((o, label))

    r = 2
    for o, label in todo:
        if label is None:
            continue
        while ws.cell(r, 1).value is not None:
            r += 1
        if r > 501:
            problems.append(f"❌ {o['id']}：個人銷售頁 500 列寫滿了")
            continue
        print(f"── {label}\n  寫入個人銷售第 {r} 列")
        if apply:
            for c, v in row_values(o).items():
                if v is not None:
                    ws.cell(r, c, v)
        r += 1

    for p in problems:
        print(p)
    if not apply:
        print(f"\n預覽完畢：{len(todo)} 張會處理。確認後加 --apply")
        return

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    bk = BACKUP_DIR / f"{BOOK.stem}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    shutil.copy2(BOOK, bk)
    wb.save(BOOK)

    # 存檔後抓回來確認，再改 Notion 標記
    check = openpyxl.load_workbook(BOOK)[SHEET]
    saved = {check.cell(x, 1).value for x in range(2, check.max_row + 1)}
    stamp = f"LINE建檔，已記個人帳務表 {date.today()}"
    done = 0
    for o, _ in todo:
        if o["id"] not in saved:
            print(f"❌ {o['id']} 存檔後找不到，Notion 標記不改")
            continue
        new = o["raw_note"].replace(SYNC_NOTE, stamp)
        notion(
            "PATCH",
            f"/pages/{o['page_id']}",
            {
                "properties": {
                    "備註": {"rich_text": [{"type": "text", "text": {"content": new}}]}
                }
            },
        )
        done += 1
    print(f"\n✅ 完成 {done} 張；帳務表備份在 {bk}")


if __name__ == "__main__":
    TOKEN = token()
    main()
