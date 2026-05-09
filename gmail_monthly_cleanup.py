#!/usr/bin/env python3
"""
Gmail 每月自動清理腳本
執行時機：每月1日 09:07
功能：
  1. 刪除純廣告信件（10 個指定寄件者）
  2. 刪除 30 天前的銀行登入通知信
"""
import json
import subprocess
import urllib.request
import urllib.parse
import time
from datetime import datetime, timedelta

LOG_PATH = "/Users/lien/Downloads/Liam AI agent/財務/gmail_cleanup_log.txt"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def get_access_token():
    result = subprocess.run(
        ["security", "find-generic-password", "-s", "gemini-cli-workspace-oauth", "-w"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout.strip())
    return data["token"]["accessToken"]

def get_all_message_ids(token, query):
    ids = []
    page_token = None
    while True:
        params = {"q": query, "maxResults": 500}
        if page_token:
            params["pageToken"] = page_token
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
        ids.extend(m["id"] for m in result.get("messages", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    return ids

def batch_trash(token, ids):
    if not ids:
        return 0
    total = 0
    for i in range(0, len(ids), 1000):
        batch = ids[i:i+1000]
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/batchModify"
        payload = json.dumps({
            "ids": batch,
            "addLabelIds": ["TRASH"],
            "removeLabelIds": ["INBOX"]
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }, method="POST")
        with urllib.request.urlopen(req) as r:
            pass
        total += len(batch)
        time.sleep(0.3)
    return total

# ── 廣告寄件者清單 ──────────────────────────────────────────
AD_SENDERS = [
    ("GU TAIWAN",       "from:ec-system@mm.gu-global.com"),
    ("中國信託",         "from:bank.csc@inedm.ctbcbank.com"),
    ("台新銀行",         "from:TSB@mhurcv.taishinbank.com.tw"),
    ("誠品線上",         "from:member@eslitebooks.com"),
    ("ShopBack",        "from:deals@promo.shopback.com.tw"),
    ("ASUS",            "from:noreply@nedm.asus.com"),
    ("Uber One",        "from:uberone@uber.com"),
    ("Meta Business",   "from:advertise-noreply@global.metamail.com"),
    ("富邦銀行",         "from:service@mhu.taipeifubon.com.tw"),
    ("玉山銀行",         "from:Service@msg.esunbank.com"),
]

# ── 登入通知（保留 30 天內）──────────────────────────────────
LOGIN_SENDERS = [
    ("華南銀行登入通知",   "from:service@ms3.hncb.com.tw"),
    ("台北富邦登入通知",   "from:mbank@dfm.taipeifubon.com.tw"),
]

def main():
    log("=" * 50)
    log("Gmail 每月清理開始")

    token = get_access_token()
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y/%m/%d")
    total = 0

    # 1. 廣告信
    log("── 清理廣告信件 ──")
    for name, query in AD_SENDERS:
        try:
            ids = get_all_message_ids(token, query)
            if ids:
                n = batch_trash(token, ids)
                log(f"  {name}：刪除 {n} 封")
                total += n
            else:
                log(f"  {name}：無信件")
        except Exception as e:
            log(f"  {name}：錯誤 {e}")

    # 2. 登入通知（30天前）
    log(f"── 清理 {cutoff} 前的登入通知 ──")
    for name, base_query in LOGIN_SENDERS:
        try:
            query = f"{base_query} before:{cutoff}"
            ids = get_all_message_ids(token, query)
            if ids:
                n = batch_trash(token, ids)
                log(f"  {name}：刪除 {n} 封")
                total += n
            else:
                log(f"  {name}：無舊記錄")
        except Exception as e:
            log(f"  {name}：錯誤 {e}")

    log(f"清理完成，本次共刪除 {total} 封")
    log("=" * 50)

if __name__ == "__main__":
    main()
