import requests
from config import NOTION_TOKEN, NOTION_VERSION

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


def get(path):
    r = requests.get(f"https://api.notion.com/v1{path}", headers=HEADERS)
    r.raise_for_status()
    return r.json()


def post(path, data):
    r = requests.post(f"https://api.notion.com/v1{path}", headers=HEADERS, json=data)
    if not r.ok:
        raise RuntimeError(f"Notion POST {path} {r.status_code}: {r.text[:400]}")
    return r.json()


def patch(path, data):
    r = requests.patch(f"https://api.notion.com/v1{path}", headers=HEADERS, json=data)
    r.raise_for_status()
    return r.json()


def query_db(db_id, filter_obj=None):
    body = {"page_size": 100}
    if filter_obj:
        body["filter"] = filter_obj
    r = requests.post(
        f"https://api.notion.com/v1/databases/{db_id}/query", headers=HEADERS, json=body
    )
    r.raise_for_status()
    return r.json().get("results", [])
