"""解析「流動資產管理」xlsx，輸出三品牌正規化庫存資料。

用法：python3 crm_unified/parse_inventory.py [xlsx路徑]
不帶參數則用 SRC 預設路徑。輸出 JSON 到 stdout 供 sync_inventory.py 使用。
"""

import json
import re
import sys

import openpyxl

SRC = (
    "/Users/lien/Desktop/鉅鑫管理顧問/20260728流動資產管理─鑫酒藏、鑫海產、鑫茶坊.xlsx"
)

TAEL_TO_CATTY = {"1斤": 1.0, "4兩": 0.25, "2兩": 0.125}


def parse_price(raw):
    """'1000/台斤' -> (1000.0, '台斤')；'850' -> (850.0, '')"""
    if raw is None:
        return None, ""
    s = str(raw).strip()
    if not s:
        return None, ""
    m = re.match(r"^([\d,.]+)\s*/?\s*(.*)$", s)
    if not m:
        return None, s
    try:
        return float(m.group(1).replace(",", "")), m.group(2).strip()
    except ValueError:
        return None, s


def clean(v):
    return str(v).strip() if v is not None and str(v).strip() else ""


def parse_seafood(ws):
    items = []
    category = ""
    unit_hint = ""
    for r in ws.iter_rows(min_row=3, values_only=True):
        name = clean(r[1])
        if not name:
            continue
        if clean(r[0]):
            category = clean(r[0])
        if clean(r[3]):
            unit_hint = clean(r[3])
        price, price_unit = parse_price(r[5])
        qty = r[4] if isinstance(r[4], (int, float)) else 0
        items.append(
            {
                "品名": name,
                "產品種類": category,
                "分裝單位": unit_hint,
                "庫存數量": qty,
                "進價": price,
                "計價單位": price_unit,
                "備註": clean(r[7]),
            }
        )
    return items


def parse_wine(ws):
    items = []
    location = ""
    for r in ws.iter_rows(values_only=True):
        if clean(r[0]) == "位置":
            location = ""
            continue
        if clean(r[0]):
            location = clean(r[0])
        name = clean(r[2])
        if not name:
            continue
        qty = r[7] if isinstance(r[7], (int, float)) else 0
        price = r[9] if isinstance(r[9], (int, float)) else 0
        country = clean(r[4])
        items.append(
            {
                "品名": name,
                "存放位置": location,
                "分類": clean(r[3]),
                "國家": re.sub(r"\d+$", "", country),
                "酒莊": clean(r[5]),
                "品種": clean(r[6]),
                "庫存數量": qty,
                "進價": price,
                "庫存成本": qty * price,
                "備註": clean(r[10]),
            }
        )
    return items


def parse_tea(ws):
    items = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        name = clean(r[1])
        if not name:
            continue
        qty = r[7] if isinstance(r[7], (int, float)) else 0
        unit = clean(r[8])
        cost_per_catty = r[10] if isinstance(r[10], (int, float)) else None
        subtotal = r[9] if isinstance(r[9], (int, float)) else None
        if subtotal is None and cost_per_catty and unit in TAEL_TO_CATTY:
            subtotal = qty * TAEL_TO_CATTY[unit] * cost_per_catty
        items.append(
            {
                "品名": name,
                "品種": clean(r[2]),
                "產地": clean(r[3]),
                "海拔": clean(r[4]),
                "製程": clean(r[5]),
                "庫存數量": qty,
                "單位": unit,
                "庫存成本": subtotal,
                "進貨價_斤": cost_per_catty,
                "產品定價": r[11] if isinstance(r[11], (int, float)) else None,
                "零售價": r[12] if isinstance(r[12], (int, float)) else None,
            }
        )
    return items


def parse(path=SRC):
    wb = openpyxl.load_workbook(path, data_only=True)
    return {
        "鑫海產": parse_seafood(wb["鑫海產"]),
        "鑫酒藏": parse_wine(wb["鑫酒藏"]),
        "鑫茶坊": parse_tea(wb["鑫茶坊"]),
    }


if __name__ == "__main__":
    data = parse(sys.argv[1] if len(sys.argv) > 1 else SRC)
    print(json.dumps(data, ensure_ascii=False, indent=2))
