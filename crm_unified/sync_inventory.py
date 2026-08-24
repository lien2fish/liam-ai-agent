"""把流動資產 xlsx 同步進 Notion（三品牌各一個庫存 DB）。

首次執行會建立父頁面與三個 DB，並把 ID 寫入 inventory_config.json；
之後再跑就是增量同步：以「品名」為鍵，新增/更新/封存。

用法：python3 crm_unified/sync_inventory.py [xlsx路徑]
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_inventory import SRC, TAEL_TO_CATTY, WINE_SRC, parse

CONFIG = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "inventory_config.json"
)
CRM_PAGE = "358f4149-a6aa-8088-9e6d-f5361d05cd12"
API = "https://api.notion.com/v1"


def token():
    t = os.environ.get("NOTION_TOKEN")
    if t:
        return t.strip()
    return open(os.path.expanduser("~/.config/notion_token")).read().strip()


TOKEN = token()
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def call(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"{API}{path}", data=data, headers=HEADERS, method=method
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if e.code in (429, 502, 503) and attempt < 3:
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError(f"{method} {path} -> {e.code} {body}")
    raise RuntimeError("unreachable")


def load_config():
    if os.path.exists(CONFIG):
        return json.load(open(CONFIG))
    return {}


def save_config(cfg):
    json.dump(cfg, open(CONFIG, "w"), ensure_ascii=False, indent=2)


def text(v):
    return {"rich_text": [{"text": {"content": str(v)[:2000]}}] if v else []}


def title(v):
    return {"title": [{"text": {"content": str(v)[:2000]}}]}


def num(v):
    return {"number": None if v in (None, "") else round(float(v), 2)}


def sel(v):
    return {"select": {"name": str(v)[:100]} if v else None}


SCHEMAS = {
    "鑫海產": {
        "emoji": "🐟",
        "name": "🐟 鑫海產 庫存 / 品項表",
        "properties": {
            "品名": {"title": {}},
            "產品種類": {"select": {}},
            "供貨狀態": {"select": {}},
            "庫存數量": {"number": {"format": "number"}},
            "數量單位": {"select": {}},
            "分裝單位": {"rich_text": {}},
            "進價": {"number": {"format": "number"}},
            "計價單位": {"select": {}},
            "估算庫存成本": {"number": {"format": "number"}},
            "成本狀態": {"select": {}},
            "備註": {"rich_text": {}},
        },
    },
    "鑫酒藏": {
        "emoji": "🍷",
        "name": "🍷 鑫酒藏 酒款庫存",
        "properties": {
            "品名": {"title": {}},
            "存放位置": {"select": {}},
            "分類": {"select": {}},
            "國家": {"select": {}},
            "酒莊": {"rich_text": {}},
            "酒種": {"select": {}},
            "品種": {"rich_text": {}},
            "庫存數量": {"number": {"format": "number"}},
            "匠鑫私廚": {"number": {"format": "number"}},
            "綠塔": {"number": {"format": "number"}},
            "進價": {"number": {"format": "number"}},
            "庫存成本": {"number": {"format": "number"}},
            "進貨總值": {"number": {"format": "number"}},
            "產品定價": {"number": {"format": "number"}},
            "批發價": {"number": {"format": "number"}},
            "零售價": {"number": {"format": "number"}},
            "備註": {"rich_text": {}},
        },
    },
    "鑫茶坊": {
        "emoji": "🍵",
        "name": "🍵 鑫茶坊 茶品庫存",
        "properties": {
            "品名": {"title": {}},
            "品種": {"rich_text": {}},
            "產地": {"rich_text": {}},
            "海拔": {"rich_text": {}},
            "製程": {"select": {}},
            "庫存數量": {"number": {"format": "number"}},
            "單位": {"select": {}},
            "庫存成本": {"number": {"format": "number"}},
            "進貨價_斤": {"number": {"format": "number"}},
            "單包成本": {"number": {"format": "number"}},
            "零售價": {"number": {"format": "number"}},
            "毛利率": {"number": {"format": "percent"}},
        },
    },
}


SEAFOOD_UNITS = {
    k: v
    for k, v in json.load(
        open(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "seafood_units.json"
            )
        )
    ).items()
    if not k.startswith("_")
}


def seafood_cost(name, qty, price, price_unit):
    """回傳 (估算成本, 成本狀態)。進價以斤計但庫存以顆/包計時，需 catty_per_unit 才能換算。"""
    if not qty or not price:
        return None, None
    spec = SEAFOOD_UNITS.get(name, {})
    if not price_unit:
        return qty * price, "已確認"
    per_unit = spec.get("catty_per_unit")
    if per_unit:
        return qty * per_unit * price, "已確認"
    if spec.get("unit"):
        return None, f"待補：每{spec['unit']}幾{price_unit}"
    return qty * price, "待確認單位"


def to_props(brand, item):
    if brand == "鑫海產":
        qty = item["庫存數量"] or 0
        price = item["進價"]
        cost, status = seafood_cost(item["品名"], qty, price, item["計價單位"])
        return {
            "品名": title(item["品名"]),
            "產品種類": sel(item["產品種類"]),
            "供貨狀態": sel("現有庫存" if qty > 0 else "可調貨"),
            "庫存數量": num(qty),
            "數量單位": sel(SEAFOOD_UNITS.get(item["品名"], {}).get("unit")),
            "分裝單位": text(item["分裝單位"]),
            "進價": num(price),
            "計價單位": sel(item["計價單位"]),
            "估算庫存成本": num(cost),
            "成本狀態": sel(status),
            "備註": text(item["備註"]),
        }
    if brand == "鑫酒藏":
        return {
            "品名": title(item["品名"]),
            "存放位置": sel(item["存放位置"]),
            "分類": sel(item["分類"]),
            "國家": sel(item["國家"]),
            "酒莊": text(item["酒莊"]),
            "酒種": sel(item["酒種"]),
            "品種": text(item["品種"]),
            "庫存數量": num(item["庫存數量"]),
            "匠鑫私廚": num(item["匠鑫私廚"]),
            "綠塔": num(item["綠塔"]),
            "進價": num(item["進價"]),
            "庫存成本": num(item["庫存成本"]),
            "進貨總值": num(item["進貨總值"]),
            "產品定價": num(item["產品定價"]),
            "批發價": num(item["批發價"]),
            "零售價": num(item["零售價"]),
            "備註": text(item["備註"]),
        }
    unit_cost = None
    if item["進貨價_斤"] and item["單位"] in TAEL_TO_CATTY:
        unit_cost = item["進貨價_斤"] * TAEL_TO_CATTY[item["單位"]]
    margin = None
    if unit_cost and item["零售價"]:
        margin = (item["零售價"] - unit_cost) / item["零售價"]
    return {
        "品名": title(item["品名"]),
        "品種": text(item["品種"]),
        "產地": text(item["產地"]),
        "海拔": text(item["海拔"]),
        "製程": sel(item["製程"]),
        "庫存數量": num(item["庫存數量"]),
        "單位": sel(item["單位"]),
        "庫存成本": num(item["庫存成本"]),
        "進貨價_斤": num(item["進貨價_斤"]),
        "單包成本": num(unit_cost),
        "零售價": num(item["零售價"]),
        "毛利率": num(margin),
    }


def ensure_parent(cfg):
    if cfg.get("parent_page_id"):
        return cfg["parent_page_id"]
    page = call(
        "POST",
        "/pages",
        {
            "parent": {"type": "page_id", "page_id": CRM_PAGE},
            "icon": {"type": "emoji", "emoji": "📦"},
            "properties": {"title": title("📦 全品牌流動資產（庫存）管理")},
        },
    )
    cfg["parent_page_id"] = page["id"]
    save_config(cfg)
    return page["id"]


def ensure_db(cfg, brand, parent_page):
    key = f"db_{brand}"
    spec = SCHEMAS[brand]
    if cfg.get(key):
        db = call("GET", f"/databases/{cfg[key]}")
        missing = {
            name: definition
            for name, definition in spec["properties"].items()
            if name not in db["properties"]
        }
        if missing:
            call("PATCH", f"/databases/{cfg[key]}", {"properties": missing})
            print(f"  {brand}: 新增欄位 {'、'.join(missing)}")
        return cfg[key]
    db = call(
        "POST",
        "/databases",
        {
            "parent": {"type": "page_id", "page_id": parent_page},
            "icon": {"type": "emoji", "emoji": spec["emoji"]},
            "title": [{"type": "text", "text": {"content": spec["name"]}}],
            "properties": spec["properties"],
        },
    )
    cfg[key] = db["id"]
    save_config(cfg)
    return db["id"]


def flatten(props):
    """把 Notion 屬性壓成可比較的簡值，用來判斷是否需要 PATCH。"""
    out = {}
    for key, v in props.items():
        t = v.get("type")
        if t == "number":
            out[key] = None if v["number"] is None else round(float(v["number"]), 2)
        elif t == "select":
            out[key] = (v["select"] or {}).get("name")
        elif t in ("title", "rich_text"):
            out[key] = "".join(x["plain_text"] for x in v[t])
    return out


def flatten_request(props):
    """把要送出的屬性壓成與 flatten() 同格式，供比對用。"""
    out = {}
    for key, v in props.items():
        if "number" in v:
            out[key] = None if v["number"] is None else round(float(v["number"]), 2)
        elif "select" in v:
            out[key] = (v["select"] or {}).get("name")
        elif "title" in v:
            out[key] = "".join(x["text"]["content"] for x in v["title"])
        elif "rich_text" in v:
            out[key] = "".join(x["text"]["content"] for x in v["rich_text"])
    return out


def existing_pages(db_id):
    pages, cursor = {}, None
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        res = call("POST", f"/databases/{db_id}/query", payload)
        for p in res["results"]:
            t = p["properties"]["品名"]["title"]
            name = t[0]["plain_text"] if t else ""
            pages.setdefault(name, []).append((p["id"], flatten(p["properties"])))
        if not res.get("has_more"):
            return pages
        cursor = res["next_cursor"]


def sync_brand(cfg, brand, items, parent_page):
    db_id = ensure_db(cfg, brand, parent_page)
    current = existing_pages(db_id)
    created = updated = archived = skipped = 0
    seen = set()
    for item in items:
        name = item["品名"]
        props = to_props(brand, item)
        ids = current.get(name, [])
        if name in seen or not ids:
            call(
                "POST",
                "/pages",
                {"parent": {"database_id": db_id}, "properties": props},
            )
            created += 1
        else:
            pid, snapshot = ids.pop(0)
            if flatten_request(props) == snapshot:
                skipped += 1
            else:
                call("PATCH", f"/pages/{pid}", {"properties": props})
                updated += 1
        seen.add(name)
    for ids in current.values():
        for pid, _ in ids:
            call("PATCH", f"/pages/{pid}", {"archived": True})
            archived += 1
    print(
        f"  {brand}: 新增 {created} / 更新 {updated} / 未變動 {skipped} / 封存 {archived}"
    )
    return db_id


def heading(txt):
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": txt}}]},
    }


def para(txt):
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": txt}}]},
    }


def bullet(txt):
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [{"type": "text", "text": {"content": txt}}]
        },
    }


def write_summary(parent, data, src_path):
    for block in call("GET", f"/blocks/{parent}/children?page_size=100")["results"]:
        if block["type"] == "child_database":
            continue  # 這是三個庫存 DB 本身，封存它＝把資料庫丟進垃圾桶
        call("PATCH", f"/blocks/{block['id']}", {"archived": True})

    wine = data["鑫酒藏"]
    tea = data["鑫茶坊"]
    sea = data["鑫海產"]
    wine_cost = sum(i["庫存成本"] or 0 for i in wine)
    tea_cost = sum(i["庫存成本"] or 0 for i in tea)
    sea_stock = [i for i in sea if (i["庫存數量"] or 0) > 0]
    sea_costs = [
        (i["品名"], *seafood_cost(i["品名"], i["庫存數量"], i["進價"], i["計價單位"]))
        for i in sea_stock
    ]
    sea_cost = sum(c or 0 for _, c, _ in sea_costs)
    sea_pending = [f"{n}（{s}）" for n, c, s in sea_costs if c is None]
    tea_missing = [i["品名"] for i in tea if i["庫存成本"] is None]

    blocks = [
        para(
            f"資料來源：{os.path.basename(src_path)}（{time.strftime('%Y-%m-%d')} 同步）"
        ),
        heading("庫存成本總覽"),
        bullet(
            f"🍷 鑫酒藏：{len(wine)} 款 / 鑫酒藏 {sum(i['庫存數量'] for i in wine)} 瓶"
            f"（匠鑫私廚 {sum(i['匠鑫私廚'] for i in wine)}、綠塔 {sum(i['綠塔'] for i in wine)}）"
            f" ─ NT$ {wine_cost:,.0f}"
            f"（{sum(1 for i in wine if not i['進價'])} 款未填進貨價未計入）"
        ),
        bullet(
            f"🍵 鑫茶坊：{len(tea)} 項 ─ NT$ {tea_cost:,.0f}（{len(tea_missing)} 項無進價資料未計入）"
        ),
        bullet(
            f"🐟 鑫海產：{len(sea_stock)} 項有庫存 ─ NT$ {sea_cost:,.0f}"
            f"（{len(sea_pending)} 項待補換算未計入，另 {len(sea) - len(sea_stock)} 項為可調貨品項）"
        ),
        bullet(f"合計流動資產（庫存成本）：NT$ {wine_cost + tea_cost + sea_cost:,.0f}"),
        heading("待補資料"),
        bullet(
            f"鑫茶坊未填進貨價：{'、'.join(tea_missing)}"
            if tea_missing
            else "鑫茶坊資料完整"
        ),
        bullet(
            f"鑫海產待補換算：{'、'.join(sea_pending)}"
            if sea_pending
            else "鑫海產成本換算完整"
        ),
        bullet(
            "鑫海產數量單位維護在 crm_unified/seafood_units.json，補上 catty_per_unit 即可自動計入成本"
        ),
        bullet("鑫海產、鑫酒藏的產品編號欄全空，若要做出貨掃碼建議補編號"),
    ]
    call("PATCH", f"/blocks/{parent}/children", {"children": blocks})


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else SRC
    wine_path = sys.argv[2] if len(sys.argv) > 2 else WINE_SRC
    data = parse(path, wine_path)
    cfg = load_config()
    parent = ensure_parent(cfg)
    print(f"父頁面 {parent}")
    for brand in ("鑫酒藏", "鑫茶坊", "鑫海產"):
        sync_brand(cfg, brand, data[brand], parent)
    write_summary(parent, data, path)
    save_config(cfg)
    print("完成")


if __name__ == "__main__":
    main()
