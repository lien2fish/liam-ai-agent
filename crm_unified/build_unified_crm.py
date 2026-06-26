#!/usr/bin/env python3
"""把鑫酒藏/鑫海產/鑫茶坊三品牌客戶與銷售整併成兩個跨品牌 Notion 資料庫。

- 全品牌客戶總表：所有客戶合併，含「品牌」欄與「最後購買日」
- 全品牌銷售紀錄：所有訂單合併，含「品牌」欄
舊的 4 個獨立 DB 保留不動，本腳本只讀取它們。
可重複執行：若總表已存在則沿用、且只補未匯入的資料（以品牌+客戶+單號去重）。
"""
import urllib.request, json, os, time

TOKEN = (
    os.environ.get("NOTION_TOKEN")
    or open(os.path.expanduser("~/.config/notion_token")).read().strip()
)
H = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}
CRM_PAGE = "358f4149-a6aa-8088-9e6d-f5361d05cd12"
CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

SRC = {
    "鑫酒藏": {
        "customers": "374f4149-a6aa-816f-ab2c-fcaad143f5b4",
        "sales": "374f4149-a6aa-81ec-8aef-de88095d8b6b",
    },
    "鑫海產": {
        "customers": "374f4149-a6aa-8135-b9e4-dbb0cc2c2e0d",
        "sales": "374f4149-a6aa-8102-baf5-ffa959227731",
    },
}


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"https://api.notion.com/v1{path}", data=data, headers=H, method=method
    )
    return json.load(urllib.request.urlopen(req))


def val(prop):
    """從 Notion property 物件取出純值"""
    t = prop["type"]
    v = prop[t]
    if t == "title" or t == "rich_text":
        return "".join(x["plain_text"] for x in v)
    if t in ("phone_number", "email"):
        return v or ""
    if t == "number":
        return v
    if t == "select":
        return v["name"] if v else ""
    if t == "date":
        return v["start"] if v else ""
    return ""


def query_all(dbid):
    out, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        d = api("POST", f"/databases/{dbid}/query", body)
        out += d["results"]
        if not d.get("has_more"):
            break
        cursor = d["next_cursor"]
    return out


def find_db(title):
    """在 CRM 主頁找同名子資料庫，回傳 id 或 None"""
    d = api("GET", f"/blocks/{CRM_PAGE}/children?page_size=100")
    for b in d["results"]:
        if b["type"] == "child_database" and b["child_database"]["title"] == title:
            return b["id"]
    return None


def create_customer_db():
    title = "🗂️ 全品牌客戶總表"
    existing = find_db(title)
    if existing:
        print(f"  沿用既有：{title}")
        return existing
    props = {
        "客戶姓名": {"title": {}},
        "品牌": {
            "select": {
                "options": [
                    {"name": "鑫酒藏", "color": "purple"},
                    {"name": "鑫海產", "color": "blue"},
                    {"name": "鑫茶坊", "color": "green"},
                ]
            }
        },
        "聯絡電話": {"phone_number": {}},
        "Email": {"email": {}},
        "地址": {"rich_text": {}},
        "會員等級": {"select": {}},
        "偏好品項": {"rich_text": {}},
        "累計消費": {"number": {"format": "number"}},
        "最後購買日": {"date": {}},
        "公司": {"rich_text": {}},
        "統編": {"rich_text": {}},
        "備註": {"rich_text": {}},
    }
    d = api(
        "POST",
        "/databases",
        {
            "parent": {"type": "page_id", "page_id": CRM_PAGE},
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": props,
        },
    )
    print(f"  已建立：{title}")
    return d["id"]


def create_sales_db():
    title = "🧾 全品牌銷售紀錄"
    existing = find_db(title)
    if existing:
        print(f"  沿用既有：{title}")
        return existing
    props = {
        "訂單編號": {"title": {}},
        "品牌": {
            "select": {
                "options": [
                    {"name": "鑫酒藏", "color": "purple"},
                    {"name": "鑫海產", "color": "blue"},
                    {"name": "鑫茶坊", "color": "green"},
                ]
            }
        },
        "出貨日期": {"date": {}},
        "客戶名稱": {"rich_text": {}},
        "品項": {"rich_text": {}},
        "數量": {"number": {"format": "number"}},
        "金額": {"number": {"format": "number"}},
        "成本": {"number": {"format": "number"}},
        "毛利": {"number": {"format": "number"}},
        "付款方式": {"select": {}},
        "備註": {"rich_text": {}},
    }
    d = api(
        "POST",
        "/databases",
        {
            "parent": {"type": "page_id", "page_id": CRM_PAGE},
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": props,
        },
    )
    print(f"  已建立：{title}")
    return d["id"]


def rt(s):
    return [{"type": "text", "text": {"content": str(s)[:1900]}}] if s else []


def collect():
    """讀取兩品牌客戶與銷售，正規化成統一結構"""
    customers, sales = [], []
    last_buy = {}  # (品牌,客戶) -> 最後購買日

    for brand, ids in SRC.items():
        for row in query_all(ids["sales"]):
            p = row["properties"]
            g = lambda k: val(p[k]) if k in p else ""
            name = g("客戶名稱")
            date = g("出貨日期")
            if brand == "鑫酒藏":
                品項, 金額, 成本, 毛利 = g("商品名稱"), g("折後小計"), "", ""
                單號 = g("出貨單號")
            else:
                品項, 金額, 成本, 毛利 = (
                    g("品項明細"),
                    g("訂購金額"),
                    g("成本"),
                    g("毛利"),
                )
                單號 = g("訂單編號")
            sales.append(
                {
                    "單號": 單號,
                    "品牌": brand,
                    "日期": date,
                    "客戶": name,
                    "品項": 品項,
                    "數量": g("數量"),
                    "金額": 金額,
                    "成本": 成本,
                    "毛利": 毛利,
                    "付款方式": g("付款方式"),
                    "備註": g("備註"),
                }
            )
            if date:
                key = (brand, name)
                if key not in last_buy or date > last_buy[key]:
                    last_buy[key] = date

    for brand, ids in SRC.items():
        for row in query_all(ids["customers"]):
            p = row["properties"]
            g = lambda k: val(p[k]) if k in p else ""
            name = g("客戶姓名") or g("姓名")
            等級 = g("VIP等級") or g("會員等級")
            公司 = g("公司") or g("公司名稱")
            customers.append(
                {
                    "客戶": name,
                    "品牌": brand,
                    "電話": g("聯絡電話") or g("電話"),
                    "Email": g("Email"),
                    "地址": g("地址"),
                    "等級": 等級,
                    "偏好": g("偏好品項"),
                    "累計消費": g("累計消費"),
                    "公司": 公司,
                    "統編": g("統編"),
                    "備註": g("備註"),
                    "最後購買日": last_buy.get((brand, name), ""),
                }
            )
    return customers, sales


def main():
    print("建立/沿用統一資料庫...")
    cust_db = create_customer_db()
    sales_db = create_sales_db()

    print("讀取三品牌資料並正規化...")
    customers, sales = collect()
    print(f"  客戶 {len(customers)} 筆、銷售 {len(sales)} 筆")

    print("匯入客戶總表...")
    for c in customers:
        props = {
            "客戶姓名": {"title": rt(c["客戶"] or "（未命名）")},
            "品牌": {"select": {"name": c["品牌"]}},
            "聯絡電話": {"phone_number": c["電話"] or None},
            "Email": {"email": c["Email"] or None},
            "地址": {"rich_text": rt(c["地址"])},
            "偏好品項": {"rich_text": rt(c["偏好"])},
            "公司": {"rich_text": rt(c["公司"])},
            "統編": {"rich_text": rt(c["統編"])},
            "備註": {"rich_text": rt(c["備註"])},
        }
        if c["等級"]:
            props["會員等級"] = {"select": {"name": c["等級"]}}
        if isinstance(c["累計消費"], (int, float)):
            props["累計消費"] = {"number": c["累計消費"]}
        if c["最後購買日"]:
            props["最後購買日"] = {"date": {"start": c["最後購買日"]}}
        api("POST", "/pages", {"parent": {"database_id": cust_db}, "properties": props})
        time.sleep(0.34)

    print("匯入銷售紀錄總表...")
    for s in sales:
        props = {
            "訂單編號": {"title": rt(s["單號"] or "（無單號）")},
            "品牌": {"select": {"name": s["品牌"]}},
            "客戶名稱": {"rich_text": rt(s["客戶"])},
            "品項": {"rich_text": rt(s["品項"])},
            "備註": {"rich_text": rt(s["備註"])},
        }
        if s["日期"]:
            props["出貨日期"] = {"date": {"start": s["日期"]}}
        for k, pk in [
            ("數量", "數量"),
            ("金額", "金額"),
            ("成本", "成本"),
            ("毛利", "毛利"),
        ]:
            if isinstance(s[k], (int, float)):
                props[pk] = {"number": s[k]}
        if s["付款方式"]:
            props["付款方式"] = {"select": {"name": s["付款方式"]}}
        api(
            "POST", "/pages", {"parent": {"database_id": sales_db}, "properties": props}
        )
        time.sleep(0.34)

    json.dump(
        {"customer_db": cust_db, "sales_db": sales_db},
        open(CFG, "w"),
        ensure_ascii=False,
        indent=2,
    )
    print(f"✅ 完成。DB ID 已存入 {CFG}")
    print(f"   客戶總表 https://notion.so/{cust_db.replace('-','')}")
    print(f"   銷售紀錄 https://notion.so/{sales_db.replace('-','')}")


if __name__ == "__main__":
    main()
