#!/usr/bin/env python3
"""一次性匯入：從本機 Numbers 讀取現有資料並推送至 Notion"""
import subprocess
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notion_api import post
from config import DB

WINE_FILE = "/Users/lien/Desktop/鉅鑫管理顧問/鑫酒藏/鑫酒藏販售清單.numbers"
SEAFOOD_FILE = "/Users/lien/Desktop/鉅鑫管理顧問/鑫海產/鑫海產品項＆客戶紀錄單.numbers"


def run_applescript_file(script):
    """將 AppleScript 寫入暫存檔執行，避免 -e 的跳脫字元問題"""
    tmp = "/tmp/import_numbers.applescript"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(script)
    r = subprocess.run(["osascript", tmp], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"AppleScript 失敗：{r.stderr}")
    return r.stdout.strip()


HEADER_KEYWORDS = {"客戶姓名", "姓名", "出貨日期", "訂單編號", "出貨單號", "品項"}


def get_sheet_data(filepath, sheet_name, start_row=3):
    """讀取 Numbers 指定工作表（row 1=凍結標題、row 2=欄位名稱，從 start_row 開始取資料）"""
    script = f"""tell application "Numbers"
    open POSIX file "{filepath}"
    delay 1
    set tbl to table 1 of sheet "{sheet_name}" of document 1
    set rowCount to row count of tbl
    set colCount to column count of tbl
    set output to ""
    repeat with r from {start_row} to rowCount
        set rowStr to ""
        set hasData to false
        repeat with colIdx from 1 to colCount
            set cellVal to value of cell r of column colIdx of tbl
            if cellVal is missing value then
                set cellStr to ""
            else
                set cellStr to cellVal as text
                if cellStr is not "" then set hasData to true
            end if
            if colIdx > 1 then set rowStr to rowStr & "|||"
            set rowStr to rowStr & cellStr
        end repeat
        if hasData then set output to output & rowStr & "@@@"
    end repeat
    return output
end tell"""
    raw = run_applescript_file(script)
    rows = []
    for line in raw.split("@@@"):
        line = line.strip()
        if not line:
            continue
        cols = line.split("|||")
        # 過濾彙計列和標題列
        first = cols[0].strip() if cols else ""
        if first.startswith("共") or first in HEADER_KEYWORDS:
            continue
        # 過濾欄位名稱列（第一欄含「姓名」「日期」等關鍵字且為純文字）
        if any(first == kw for kw in HEADER_KEYWORDS):
            continue
        rows.append(cols)
    return rows


def rt(text):
    """rich_text 屬性值"""
    return {"rich_text": [{"text": {"content": str(text or "")}}]}


def num(val):
    """number 屬性值，空值回傳 None"""
    try:
        v = str(val).replace(",", "").replace("NT$", "").replace("%", "").strip()
        return {"number": float(v)} if v else {"number": None}
    except Exception:
        return {"number": None}


def sel(val):
    """select 屬性值"""
    return (
        {"select": {"name": str(val)}} if val and str(val).strip() else {"select": None}
    )


def date_prop(val):
    """date 屬性值，支援多種格式（含中文日期）"""
    import re

    if not val or not str(val).strip():
        return {"date": None}
    v = str(val).strip()
    # 中文日期：2026年5月7日 → 2026-05-07
    m = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日", v)
    if m:
        return {
            "date": {
                "start": f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            }
        }
    v = v.replace("/", "-")
    return {"date": {"start": v[:10]}}


# ── 鑫酒藏 客戶名單 ────────────────────────────────────────────


def import_wine_customers():
    print("讀取鑫酒藏客戶名單...", flush=True)
    rows = get_sheet_data(WINE_FILE, "👥 客戶名單")
    print(f"  找到 {len(rows)} 筆", flush=True)
    db_id = DB["wine_customers"]
    for i, row in enumerate(rows):
        while len(row) < 7:
            row.append("")
        _, name, phone, address, email, vip, note = (
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
        )
        if not name.strip():
            continue
        props = {
            "客戶姓名": {"title": [{"text": {"content": name}}]},
            "聯絡電話": {"phone_number": phone or None},
            "地址": rt(address),
            "Email": {"email": email or None},
            "VIP等級": sel(vip if vip in ("VIP", "一般") else "一般"),
            "備註": rt(note),
        }
        post("/pages", {"parent": {"database_id": db_id}, "properties": props})
        print(f"  ✅ {name}", flush=True)


# ── 鑫酒藏 銷售紀錄 ────────────────────────────────────────────


def import_wine_sales():
    print("讀取鑫酒藏銷售紀錄...", flush=True)
    rows = get_sheet_data(WINE_FILE, "📊 銷售報表")
    print(f"  找到 {len(rows)} 筆", flush=True)
    db_id = DB["wine_sales"]
    for row in rows:
        while len(row) < 14:
            row.append("")
        (
            date,
            order_no,
            customer,
            code,
            name,
            brand,
            category,
            price,
            qty,
            subtotal,
            discount,
            discounted,
            staff,
            note,
        ) = (
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            row[7],
            row[8],
            row[9],
            row[10],
            row[11],
            row[12],
            row[13],
        )
        # 跳過空列或彙計列（日期欄含「合計」「▶」等非日期文字）
        if not order_no.strip() or not str(date).strip():
            continue
        if any(kw in str(date) for kw in ("合計", "▶", "小計", "總計")):
            continue
        # 折扣%：Numbers 存整數（25 = 25%），Notion percent 格式需除以 100
        disc_val = None
        try:
            disc_val = float(str(discount).replace("%", "").strip()) / 100
        except Exception:
            pass

        props = {
            "出貨單號": {"title": [{"text": {"content": order_no}}]},
            "出貨日期": date_prop(date),
            "客戶名稱": rt(customer),
            "商品代碼": rt(code),
            "商品名稱": rt(name),
            "品牌/酒廠": rt(brand),
            "類別": sel(category),
            "單價": num(price),
            "數量": num(qty),
            "小計": num(subtotal),
            "折扣%": {"number": disc_val},
            "折後小計": num(discounted),
            "備註": rt(note),
        }
        post("/pages", {"parent": {"database_id": db_id}, "properties": props})
        print(f"  ✅ {order_no} {customer}", flush=True)


# ── 鑫海產 客戶名單 ────────────────────────────────────────────


def import_seafood_customers():
    print("讀取鑫海產客戶名單...", flush=True)
    rows = get_sheet_data(SEAFOOD_FILE, "👥 客戶名單")
    print(f"  找到 {len(rows)} 筆", flush=True)
    db_id = DB["seafood_customers"]
    for row in rows:
        while len(row) < 9:
            row.append("")
        cust_id, name, phone, contact, email, pref, vip, total, note = (
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            row[7],
            row[8],
        )
        if not name.strip():
            continue
        props = {
            "姓名": {"title": [{"text": {"content": name}}]},
            "客戶編號": rt(cust_id),
            "電話": {"phone_number": phone or None},
            "聯絡方式": rt(contact),
            "Email": {"email": email or None},
            "偏好品項": rt(pref),
            "會員等級": sel(vip if vip in ("VIP", "一般") else "一般"),
            "累計消費": num(total),
            "備註": rt(note),
        }
        post("/pages", {"parent": {"database_id": db_id}, "properties": props})
        print(f"  ✅ {name}", flush=True)


# ── 鑫海產 銷售紀錄 ────────────────────────────────────────────


def import_seafood_sales():
    print("讀取鑫海產銷售紀錄...", flush=True)
    rows = get_sheet_data(SEAFOOD_FILE, "📊 銷售報表")
    print(f"  找到 {len(rows)} 筆", flush=True)
    db_id = DB["seafood_sales"]
    for row in rows:
        while len(row) < 10:
            row.append("")
        date, order_no, customer, items, amount, cost, profit, margin, payment, note = (
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            row[7],
            row[8],
            row[9],
        )
        if not order_no.strip() or not str(date).strip():
            continue
        if any(kw in str(date) for kw in ("合計", "▶", "小計", "總計")):
            continue
        margin_val = None
        try:
            margin_val = float(str(margin).replace("%", "").strip()) / 100
        except Exception:
            pass

        props = {
            "訂單編號": {"title": [{"text": {"content": order_no}}]},
            "出貨日期": date_prop(date),
            "客戶名稱": rt(customer),
            "品項明細": rt(items),
            "訂購金額": num(amount),
            "成本": num(cost),
            "毛利": num(profit),
            "毛利率%": {"number": margin_val},
            "付款方式": sel(payment),
            "備註": rt(note),
        }
        post("/pages", {"parent": {"database_id": db_id}, "properties": props})
        print(f"  ✅ {order_no} {customer}", flush=True)


if __name__ == "__main__":
    import_wine_customers()
    import_wine_sales()
    import_seafood_customers()
    import_seafood_sales()
    print("\n✅ 所有資料匯入完成")
