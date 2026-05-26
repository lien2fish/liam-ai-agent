#!/usr/bin/env python3
"""
Gmail 每月自動清理腳本
執行時機：每月1日 08:00（台灣時間），GitHub Actions 排程
功能：
  1. 刪除純廣告信件（10 個指定寄件者）
  2. 刪除 30 天前的銀行登入通知信
  3. 將報告寫入 reports/gmail_cleanup_YYYY-MM.md
"""
import json
import os
import urllib.request
import urllib.parse
import time
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE   = Path(os.environ.get('GITHUB_WORKSPACE', '/Users/lien/Downloads/Liam AI agent'))
REPORTS_DIR = WORKSPACE / 'reports'
REPORTS_DIR.mkdir(exist_ok=True)

now        = datetime.now()
REPORT_FILE = REPORTS_DIR / f"gmail_cleanup_{now.strftime('%Y-%m')}.md"
LOG_FILE    = Path('/tmp/gmail_cleanup.log')

_report_lines = []

def log(msg):
    ts   = now.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    _report_lines.append(msg)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass

def get_access_token():
    data = urllib.parse.urlencode({
        'client_id':     os.environ['GMAIL_CLIENT_ID'],
        'client_secret': os.environ['GMAIL_CLIENT_SECRET'],
        'refresh_token': os.environ['GMAIL_REFRESH_TOKEN'],
        'grant_type':    'refresh_token',
    }).encode()
    req = urllib.request.Request(
        'https://oauth2.googleapis.com/token',
        data=data, method='POST'
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())['access_token']

def get_all_message_ids(token, query):
    ids        = []
    page_token = None
    while True:
        params = {'q': query, 'maxResults': 500}
        if page_token:
            params['pageToken'] = page_token
        url = 'https://gmail.googleapis.com/gmail/v1/users/me/messages?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
        with urllib.request.urlopen(req) as r:
            result = json.loads(r.read())
        ids.extend(m['id'] for m in result.get('messages', []))
        page_token = result.get('nextPageToken')
        if not page_token:
            break
    return ids

def batch_trash(token, ids):
    if not ids:
        return 0
    total = 0
    for i in range(0, len(ids), 1000):
        batch   = ids[i:i+1000]
        payload = json.dumps({
            'ids':            batch,
            'addLabelIds':    ['TRASH'],
            'removeLabelIds': ['INBOX']
        }).encode()
        req = urllib.request.Request(
            'https://gmail.googleapis.com/gmail/v1/users/me/messages/batchModify',
            data=payload,
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req):
            pass
        total += len(batch)
        time.sleep(0.3)
    return total

# ── 廣告寄件者清單 ────────────────────────────────────────────
AD_SENDERS = [
    ("GU TAIWAN",      "from:ec-system@mm.gu-global.com"),
    ("中國信託",        "from:bank.csc@inedm.ctbcbank.com"),
    ("台新銀行",        "from:TSB@mhurcv.taishinbank.com.tw"),
    ("誠品線上",        "from:member@eslitebooks.com"),
    ("ShopBack",       "from:deals@promo.shopback.com.tw"),
    ("ASUS",           "from:noreply@nedm.asus.com"),
    ("Uber One",       "from:uberone@uber.com"),
    ("Meta Business",  "from:advertise-noreply@global.metamail.com"),
    ("富邦銀行",        "from:service@mhu.taipeifubon.com.tw"),
    ("玉山銀行",        "from:Service@msg.esunbank.com"),
]

# ── 登入通知（保留 30 天內）──────────────────────────────────
LOGIN_SENDERS = [
    ("華南銀行登入通知", "from:service@ms3.hncb.com.tw"),
    ("台北富邦登入通知", "from:mbank@dfm.taipeifubon.com.tw"),
]

def save_report(total, ad_results, login_results, read_count, read_err):
    lines = [
        f"# 📧 Gmail 清理報告｜{now.strftime('%Y年%m月%d日')}",
        "",
        f"> 執行時間：{now.strftime('%Y-%m-%d %H:%M')}（台灣時間）",
        f"> **本次共清理：{total} 封**",
        "",
        "## 廣告信件",
        "",
        "| 寄件者 | 清理數量 |",
        "|--------|---------|",
    ]
    for name, n, err in ad_results:
        lines.append(f"| {name} | {'❌ ' + err if err else str(n) + ' 封'} |")

    lines += [
        "",
        "## 銀行登入通知（30 天前）",
        "",
        "| 寄件者 | 清理數量 |",
        "|--------|---------|",
    ]
    for name, n, err in login_results:
        lines.append(f"| {name} | {'❌ ' + err if err else str(n) + ' 封'} |")

    lines += [
        "",
        "## 已讀舊信（30 天前）",
        "",
        f"| 項目 | 結果 |",
        f"|------|------|",
        f"| 已讀 + 超過 30 天 + 非星號/重要 | {'❌ ' + read_err if read_err else str(read_count) + ' 封'} |",
    ]

    REPORT_FILE.write_text('\n'.join(lines), encoding='utf-8')
    print(f"報告已寫入：{REPORT_FILE}")

def main():
    print("=" * 50)
    print("Gmail 每月清理開始")

    token  = get_access_token()
    cutoff = (now - timedelta(days=30)).strftime('%Y/%m/%d')
    total  = 0

    # 1. 廣告信
    ad_results = []
    print("── 清理廣告信件 ──")
    for name, query in AD_SENDERS:
        try:
            ids = get_all_message_ids(token, query)
            n   = batch_trash(token, ids) if ids else 0
            print(f"  {name}：{'刪除 ' + str(n) + ' 封' if n else '無信件'}")
            total += n
            ad_results.append((name, n, None))
        except Exception as e:
            print(f"  {name}：錯誤 {e}")
            ad_results.append((name, 0, str(e)))

    # 2. 登入通知（30天前）
    login_results = []
    print(f"── 清理 {cutoff} 前的登入通知 ──")
    for name, base_query in LOGIN_SENDERS:
        try:
            ids = get_all_message_ids(token, f"{base_query} before:{cutoff}")
            n   = batch_trash(token, ids) if ids else 0
            print(f"  {name}：{'刪除 ' + str(n) + ' 封' if n else '無舊記錄'}")
            total += n
            login_results.append((name, n, None))
        except Exception as e:
            print(f"  {name}：錯誤 {e}")
            login_results.append((name, 0, str(e)))

    # 3. 已讀舊信（30天前，非星號、非重要）
    read_count, read_err = 0, None
    print(f"── 清理 {cutoff} 前的已讀信件 ──")
    try:
        query = f"is:read before:{cutoff} -is:starred -is:important in:inbox"
        ids   = get_all_message_ids(token, query)
        read_count = batch_trash(token, ids) if ids else 0
        print(f"  已讀舊信：{'刪除 ' + str(read_count) + ' 封' if read_count else '無符合信件'}")
        total += read_count
    except Exception as e:
        print(f"  已讀舊信：錯誤 {e}")
        read_err = str(e)

    print(f"清理完成，本次共刪除 {total} 封")
    print("=" * 50)

    save_report(total, ad_results, login_results, read_count, read_err)

if __name__ == '__main__':
    main()
