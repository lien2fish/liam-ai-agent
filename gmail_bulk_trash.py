#!/usr/bin/env python3
import json
import subprocess
import urllib.request
import urllib.parse
import time

def get_access_token():
    result = subprocess.run(
        ["security", "find-generic-password", "-s", "gemini-cli-workspace-oauth", "-w"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout.strip())
    return data["token"]["accessToken"]

def gmail_search(token, query, page_token=None):
    params = {"q": query, "maxResults": 500}
    if page_token:
        params["pageToken"] = page_token
    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def get_all_message_ids(token, query):
    ids = []
    page_token = None
    while True:
        result = gmail_search(token, query, page_token)
        messages = result.get("messages", [])
        ids.extend(m["id"] for m in messages)
        page_token = result.get("nextPageToken")
        print(f"  fetched {len(ids)} messages so far...")
        if not page_token:
            break
    return ids

def batch_trash(token, message_ids):
    if not message_ids:
        return
    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/batchModify"
    payload = json.dumps({
        "ids": message_ids,
        "addLabelIds": ["TRASH"],
        "removeLabelIds": ["INBOX"]
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }, method="POST")
    with urllib.request.urlopen(req) as r:
        return r.status

senders = [
    ("GU TAIWAN",     "from:ec-system@mm.gu-global.com"),
    ("中國信託",       "from:bank.csc@inedm.ctbcbank.com"),
    ("台新銀行",       "from:TSB@mhurcv.taishinbank.com.tw"),
    ("誠品線上",       "from:member@eslitebooks.com"),
    ("ShopBack",      "from:deals@promo.shopback.com.tw"),
    ("ASUS",          "from:noreply@nedm.asus.com"),
    ("Uber One",      "from:uberone@uber.com"),
    ("Meta Business", "from:advertise-noreply@global.metamail.com"),
    ("富邦銀行",       "from:service@mhu.taipeifubon.com.tw"),
    ("玉山銀行",       "from:Service@msg.esunbank.com"),
]

token = get_access_token()
total_deleted = 0

for name, query in senders:
    print(f"\n處理 {name}...")
    try:
        ids = get_all_message_ids(token, query)
        if not ids:
            print(f"  無信件")
            continue
        # batchModify limit is 1000 per request
        batch_size = 1000
        for i in range(0, len(ids), batch_size):
            batch = ids[i:i+batch_size]
            status = batch_trash(token, batch)
            print(f"  移至垃圾桶 {len(batch)} 封 (HTTP {status})")
            time.sleep(0.3)
        total_deleted += len(ids)
        print(f"  完成：{name} 共 {len(ids)} 封")
    except Exception as e:
        print(f"  錯誤：{e}")

print(f"\n總計移至垃圾桶：{total_deleted} 封廣告信件")
