#!/usr/bin/env python3
"""
Gmail 每日自動清理腳本
執行時機：每天 08:05
功能：
  1. 刪除純廣告信件（多個指定寄件者）
  2. 刪除 30 天前的銀行登入通知信
"""
import json
import os
import urllib.request
import urllib.parse
import urllib.error
import time
from datetime import datetime, timedelta

LOG_PATH = os.path.join(os.path.dirname(__file__), "財務", "gmail_cleanup_log.txt")

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def get_access_token():
    # 優先用環境變數（GitHub Actions），fallback 到本地 token 檔
    client_id = os.environ.get("GMAIL_CLIENT_ID")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET")
    refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        token_path = os.path.expanduser("~/.config/gmail-cleanup-token.json")
        with open(token_path) as f:
            data = json.load(f)
        client_id = data["client_id"]
        client_secret = data["client_secret"]
        refresh_token = data["refresh_token"]

    payload = urllib.parse.urlencode({
        "client_id":     client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type":    "refresh_token",
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )
    with urllib.request.urlopen(req) as r:
        resp = json.loads(r.read())

    return resp["access_token"]

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
    # 購物 / 時尚
    ("GU TAIWAN",        "from:ec-system@mm.gu-global.com"),
    ("Burberry",         "from:BurberryEmails@news.burberry.com"),
    ("Pinkoi",           "from:notifications@account.pinkoi.com"),
    ("Coupang",          "from:no_reply@info.coupang.com"),
    ("ASUS",             "from:noreply@nedm.asus.com"),
    ("星巴克",            "from:member@e.starbucks.com.tw"),
    ("京站時尚廣場",       "from:epaperqs@qsquare.com.tw"),
    ("STARLUX星宇航空",   "from:marketing@e.starlux-airlines.com"),
    ("長榮航空",           "from:eservice@mh1.evaair.com"),
    # 銀行 / 金融廣告
    ("中國信託廣告",       "from:bank.csc@inedm.ctbcbank.com"),
    ("台新銀行廣告",       "from:TSB@mhurcv.taishinbank.com.tw"),
    ("玉山銀行廣告",       "from:Service@msg.esunbank.com"),
    ("富邦銀行廣告",       "from:service@mhu.taipeifubon.com.tw"),
    ("國泰世華廣告",       "from:cathaybk@news.mybank.com.tw"),
    # 外送 / 旅遊
    ("Uber Eats",        "from:uber.taiwan@uber.com"),
    ("Uber One",         "from:uberone@uber.com"),
    ("Booking.com",      "from:noreply@booking.com OR from:email.campaign@sg.booking.com"),
    ("ShopBack",         "from:deals@promo.shopback.com.tw"),
    # 電子報 / 行銷
    ("誠品線上",          "from:member@eslitebooks.com OR from:eslite@eslitebooks.com"),
    ("Adobe",            "from:mail@mail.adobe.com"),
    ("Artlist",          "from:team@newsletter.artlist.io"),
    ("Prezi",            "from:email@create.prezi.com"),
    ("HappyGo",          "from:member@edm.happygocard.com.tw"),
    ("天下Cheers",        "from:chsadmin@cw.com.tw"),
    ("天下雜誌",           "from:sub1@cw.com.tw"),
    ("親子天下",          "from:parenting@cw.com.tw"),
    ("康健雜誌",           "from:chmk@cw.com.tw"),
    ("風潮音樂",          "from:wind.edm@msa.hinet.net"),
    ("Meta Business廣告", "from:advertise-noreply@global.metamail.com"),
    ("Hami書城",          "from:edm@hamibook.com.tw"),
    ("104人力銀行",        "from:104news@ms1.104.com.tw"),
    ("BitoPro幣託",        "from:service@edm.bitopro.com"),
    ("WeMo Scooter",      "from:info@wemoscooter.com"),
    ("Gogoro",            "from:no-reply@gogoro.com"),
    ("CapCut",            "from:admin@mail.capcut.com"),
    ("Supercell",         "from:no-reply@info.supercell.com"),
    # 保險平台 OTP / 登入驗證（立即刪除，OTP秒失效）
    ("遠雄人壽OTP",       "from:admin@fglife.com.tw"),
    ("安達人壽OTP",       "from:CustomerService.TWLife@chubb.com"),
    ("全景安達OTP",       "from:Tpeb2b.tw@chubb.com"),
    ("台灣人壽OTP",       "from:service@taiwanlife.com"),
    ("全球人壽mPOS",      "from:mPOS_ProdMailAcct@transglobe.com.tw"),
]

# ── 登入通知（保留 30 天後刪除）────────────────────────────────
LOGIN_SENDERS = [
    # 銀行登入通知
    ("華南銀行登入通知",   "from:service@ms3.hncb.com.tw"),
    ("台北富邦登入通知",   "from:mbank@dfm.taipeifubon.com.tw"),
    ("台新銀行登入通知",   "from:webmaster@taishinbank.com.tw"),
    ("玉山銀行登入通知",   "from:Service@info.esunbank.com"),
    ("中信銀行登入通知",   "from:bank.csc@inib.ctbcbank.com"),
    ("國泰世華登入通知",   "from:webservice@cathaybk.com.tw"),
    # 電商安全通知
    ("蝦皮安全通知",       "from:info@mail.shopee.tw subject:安全性提醒"),
]

def main():
    log("=" * 50)
    log("Gmail 每日清理開始")

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

    log(f"每日清理完成，本次共刪除 {total} 封")
    log("=" * 50)

if __name__ == "__main__":
    main()
