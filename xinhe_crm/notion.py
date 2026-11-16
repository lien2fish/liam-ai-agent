"""炘和 CRM 共用：金鑰、資料庫 ID、讀寫 Notion。

⛔ 一律用只連炘和的 XINHE_NOTION_TOKEN，不可退回鉅鑫的 NOTION_TOKEN
（那把看得到整個鉅鑫 CRM 與壽險原始名單）。
"""
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((Path(__file__).parent / "config.json").read_text())


def _token():
    t = os.environ.get("XINHE_NOTION_TOKEN")
    if t:
        return t.strip()
    p = ROOT / "config/.xinhe_notion_token"
    if p.exists():
        return p.read_text().strip()
    raise SystemExit("❌ 沒有炘和金鑰：設環境變數 XINHE_NOTION_TOKEN，或本機 config/.xinhe_notion_token")


H = {
    "Authorization": f"Bearer {_token()}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def call(method, path, body=None):
    req = urllib.request.Request(
        f"https://api.notion.com/v1{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers=H,
        method=method,
    )
    return json.load(urllib.request.urlopen(req))


def query_all(db_key, filter_obj=None):
    out, cur = [], None
    while True:
        body = {"page_size": 100}
        if filter_obj:
            body["filter"] = filter_obj
        if cur:
            body["start_cursor"] = cur
        d = call("POST", f"/databases/{CFG[db_key]}/query", body)
        out += d["results"]
        if not d.get("has_more"):
            return out
        cur = d["next_cursor"]


def val(prop):
    t = prop["type"]
    v = prop[t]
    if t in ("title", "rich_text"):
        return "".join(x["plain_text"] for x in v)
    if t in ("phone_number", "email"):
        return v or ""
    if t == "number":
        return v
    if t == "select":
        return v["name"] if v else ""
    if t == "multi_select":
        return [x["name"] for x in v]
    if t == "date":
        return v["start"] if v else ""
    if t == "checkbox":
        return bool(v)
    if t == "relation":
        return [x["id"] for x in v]
    if t == "formula":
        return v.get(v["type"])
    return ""


def getter(row):
    p = row["properties"]
    return lambda k: val(p[k]) if k in p else ""
