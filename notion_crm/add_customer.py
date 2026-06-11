#!/usr/bin/env python3
"""新增客戶 → 本機 Numbers（主）→ Notion 備份"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from pathlib import Path
from numbers_parser import Document
import notion_api as api
from config import DB, BRAND_PREFIXES, CUSTOMER_DB, CUSTOMER_NAME_FIELD

NUMBERS_FILES = {
    "seafood": Path(
        "/Users/lien/Desktop/鉅鑫管理顧問/鑫海產/鑫海產品項＆客戶紀錄單.numbers"
    ),
    "wine": Path("/Users/lien/Desktop/鉅鑫管理顧問/鑫酒藏/鑫酒藏販售清單.numbers"),
}
CUSTOMER_SHEET = {
    "seafood": "👥 客戶名單",
    "wine": "👥 客戶名單",
}


def rt(text):
    return {"rich_text": [{"type": "text", "text": {"content": str(text or "")}}]}


def get_next_customer_id(brand):
    db_key = CUSTOMER_DB[brand]
    name_field = CUSTOMER_NAME_FIELD[brand]
    prefix = BRAND_PREFIXES[brand]
    rows = api.query_db(DB[db_key])
    nums = []
    for r in rows:
        id_prop = r["properties"].get("客戶編號", {}).get("rich_text", [])
        cust_id = id_prop[0]["plain_text"] if id_prop else ""
        if cust_id.startswith(prefix + "-"):
            try:
                nums.append(int(cust_id.split("-")[1]))
            except ValueError:
                pass
    next_num = (max(nums) + 1) if nums else 1
    return f"{prefix}-{next_num:03d}"


def write_customer_to_numbers(brand, row_data: list):
    fpath = NUMBERS_FILES[brand]
    if not fpath.exists():
        print(f"  ⚠️  本機檔案不存在：{fpath.name}，跳過")
        return False
    doc = Document(str(fpath))
    sheet_name = CUSTOMER_SHEET[brand]
    for sheet in doc.sheets:
        if sheet.name == sheet_name:
            table = sheet.tables[0]
            # 找第一個空列（從 row 3 開始，row 0=標題 row 1=欄位名 row 2=第一筆）
            empty_row = table.num_rows
            for r in range(2, table.num_rows):
                try:
                    if not table.cell(r, 1).value:
                        empty_row = r
                        break
                except Exception:
                    pass
            for c, val in enumerate(row_data):
                if val is not None and val != "":
                    table.write(empty_row, c, val)
            doc.save(str(fpath))
            print(f"  ✅ 本機 Numbers 已寫入（{sheet_name} 第{empty_row}列）")
            return True
    print(f"  ⚠️  找不到工作表「{sheet_name}」")
    return False


def add_seafood_customer(
    name, phone=None, contact=None, email=None, pref=None, vip="一般", note=None
):
    cust_id = get_next_customer_id("seafood")
    print(f"  客戶編號：{cust_id}")

    # Numbers 欄位順序：客戶編號, 姓名, 電話, 聯絡方式, Email, 偏好品項, 會員等級, 累計消費, 備註
    write_customer_to_numbers(
        "seafood",
        [
            cust_id,
            name,
            phone or "",
            contact or "",
            email or "",
            pref or "",
            vip,
            0,
            note or "",
        ],
    )

    props = {
        "姓名": {"title": [{"text": {"content": name}}]},
        "客戶編號": rt(cust_id),
        "會員等級": {"select": {"name": vip}},
        "累計消費": {"number": 0},
    }
    if phone:
        props["電話"] = {"phone_number": phone}
    if contact:
        props["聯絡方式"] = rt(contact)
    if email:
        props["Email"] = {"email": email}
    if pref:
        props["偏好品項"] = rt(pref)
    if note:
        props["備註"] = rt(note)

    api.post(
        "/pages",
        {"parent": {"database_id": DB["seafood_customers"]}, "properties": props},
    )
    print(f"  ✅ Notion 已備份：{name}（{cust_id}）")
    return cust_id


def add_wine_customer(
    name, phone=None, address=None, email=None, vip="一般", note=None
):
    cust_id = get_next_customer_id("wine")
    print(f"  客戶編號：{cust_id}")

    # Numbers 欄位順序（依 import）: 客戶編號（col 0 不一定，看實際）, 客戶姓名, 電話, 地址, Email, VIP等級, 備註
    write_customer_to_numbers(
        "wine", [name, phone or "", address or "", email or "", vip, note or ""]
    )

    props = {
        "客戶姓名": {"title": [{"text": {"content": name}}]},
        "VIP等級": {"select": {"name": vip}},
    }
    if phone:
        props["聯絡電話"] = {"phone_number": phone}
    if address:
        props["地址"] = rt(address)
    if email:
        props["Email"] = {"email": email}
    if note:
        props["備註"] = rt(note)

    api.post(
        "/pages", {"parent": {"database_id": DB["wine_customers"]}, "properties": props}
    )
    print(f"  ✅ Notion 已備份：{name}（{cust_id}）")
    return cust_id


if __name__ == "__main__":
    # 詹傑涵 — 鑫海產新客戶
    add_seafood_customer(
        name="詹傑涵",
        note="公司：麗山投資有限公司｜統編：52482387｜地址：台北市內湖區內湖路一段387巷8號7樓",
    )
    print("\n✅ 新客戶建立完成")
