#!/usr/bin/env python3
"""建立 Notion CRM 資料庫：鑫酒藏＋鑫海產各一套客戶名單＋銷售紀錄"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from notion_api import post
from config import DB

PARENT = {"type": "page_id", "page_id": DB["crm_page"]}

# ── 欄位定義 ──────────────────────────────────────────────────

WINE_CUSTOMER_PROPS = {
    "客戶姓名": {"title": {}},
    "聯絡電話": {"phone_number": {}},
    "地址": {"rich_text": {}},
    "Email": {"email": {}},
    "VIP等級": {
        "select": {
            "options": [
                {"name": "VIP", "color": "yellow"},
                {"name": "一般", "color": "gray"},
            ]
        }
    },
    "備註": {"rich_text": {}},
}

WINE_SALES_PROPS = {
    "出貨單號": {"title": {}},
    "出貨日期": {"date": {}},
    "客戶名稱": {"rich_text": {}},
    "商品代碼": {"rich_text": {}},
    "商品名稱": {"rich_text": {}},
    "品牌/酒廠": {"rich_text": {}},
    "類別": {
        "select": {
            "options": [
                {"name": "紅酒", "color": "red"},
                {"name": "白酒", "color": "yellow"},
                {"name": "氣泡酒", "color": "green"},
                {"name": "威士忌", "color": "brown"},
                {"name": "香檳", "color": "pink"},
                {"name": "清酒", "color": "blue"},
                {"name": "梅酒", "color": "purple"},
            ]
        }
    },
    "單價": {"number": {"format": "number"}},
    "數量": {"number": {"format": "number"}},
    "小計": {"number": {"format": "number"}},
    "折扣%": {"number": {"format": "percent"}},
    "折後小計": {"number": {"format": "number"}},
    "付款方式": {
        "select": {
            "options": [
                {"name": "LINE轉帳", "color": "green"},
                {"name": "現金", "color": "blue"},
                {"name": "匯款", "color": "orange"},
            ]
        }
    },
    "備註": {"rich_text": {}},
}

SEAFOOD_CUSTOMER_PROPS = {
    "姓名": {"title": {}},
    "客戶編號": {"rich_text": {}},
    "電話": {"phone_number": {}},
    "聯絡方式": {"rich_text": {}},
    "Email": {"email": {}},
    "偏好品項": {"rich_text": {}},
    "會員等級": {
        "select": {
            "options": [
                {"name": "VIP", "color": "yellow"},
                {"name": "一般", "color": "gray"},
            ]
        }
    },
    "累計消費": {"number": {"format": "number"}},
    "備註": {"rich_text": {}},
}

SEAFOOD_SALES_PROPS = {
    "訂單編號": {"title": {}},
    "出貨日期": {"date": {}},
    "客戶名稱": {"rich_text": {}},
    "品項明細": {"rich_text": {}},
    "訂購金額": {"number": {"format": "number"}},
    "成本": {"number": {"format": "number"}},
    "毛利": {"number": {"format": "number"}},
    "毛利率%": {"number": {"format": "percent"}},
    "付款方式": {
        "select": {
            "options": [
                {"name": "LINE轉帳", "color": "green"},
                {"name": "現金", "color": "blue"},
                {"name": "匯款", "color": "orange"},
            ]
        }
    },
    "備註": {"rich_text": {}},
}

DATABASES = [
    ("🍷 鑫酒藏 客戶名單", WINE_CUSTOMER_PROPS, "wine_customers"),
    ("🍷 鑫酒藏 銷售紀錄", WINE_SALES_PROPS, "wine_sales"),
    ("🐟 鑫海產 客戶名單", SEAFOOD_CUSTOMER_PROPS, "seafood_customers"),
    ("🐟 鑫海產 銷售紀錄", SEAFOOD_SALES_PROPS, "seafood_sales"),
]


def create_database(title, properties):
    return post(
        "/databases",
        {
            "parent": PARENT,
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": properties,
        },
    )


def main():
    ids = {}
    for title, props, key in DATABASES:
        print(f"建立 {title}...", end=" ", flush=True)
        result = create_database(title, props)
        db_id = result["id"]
        ids[key] = db_id
        print(f"✅ {db_id}")

    print("\n── 新 DB ID（貼入 config.py）──")
    for k, v in ids.items():
        print(f'    "{k}": "{v}",')


if __name__ == "__main__":
    main()
