#!/usr/bin/env python3
"""
YouTube 留言自動回覆 - 輪詢版
GitHub Actions 每 10 分鐘執行
"""

import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── 路徑設定 ──────────────────────────────────────────────────────
WORKSPACE  = Path(os.environ.get('GITHUB_WORKSPACE', '/Users/lien/Downloads/Liam AI agent'))
STATE_FILE = WORKSPACE / 'youtube/auto_reply/reply_state.json'
LOG_FILE   = Path('/tmp/yt_comment_reply.log')

YT_API       = 'https://www.googleapis.com/youtube/v3'
OAUTH_URL    = 'https://oauth2.googleapis.com/token'
CLAUDE_API   = 'https://api.anthropic.com/v1/messages'
CLAUDE_MODEL = 'claude-haiku-4-5-20251001'
FALLBACK     = '感謝您的留言！有任何海鮮採購需求，歡迎私訊詢問 🐟'
MAX_IDS  = 2000

# ── 載入設定（env var）────────────────────────────────────────────
CLIENT_ID     = os.environ['YT_CLIENT_ID']
CLIENT_SECRET = os.environ['YT_CLIENT_SECRET']
REFRESH_TOKEN = os.environ['YT_REFRESH_TOKEN']
CHANNEL_ID    = os.environ['YT_CHANNEL_ID']
ANTHROPIC_KEY = os.environ['ANTHROPIC_API_KEY']

# ── 工具函式 ──────────────────────────────────────────────────────

def log(msg):
    ts   = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass

def get_access_token():
    data = urllib.parse.urlencode({
        'client_id':     CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN,
        'grant_type':    'refresh_token',
    }).encode()
    req = urllib.request.Request(OAUTH_URL, data=data, method='POST')
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())['access_token']

def yt_get(path, params, token):
    url = f"{YT_API}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def yt_post(path, body, token):
    url  = f"{YT_API}/{path}?part=snippet"
    data = json.dumps(body).encode()
    req  = urllib.request.Request(
        url, data=data,
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    since = (datetime.now(timezone.utc) - timedelta(minutes=11)).strftime('%Y-%m-%dT%H:%M:%SZ')
    return {'last_checked': since, 'replied_ids': []}

def save_state(state):
    state['replied_ids'] = state['replied_ids'][-MAX_IDS:]
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

def claude_reply(text):
    prompt = (
        "你是「龜吼現流活海產 / From Source To TABLE」品牌的客服助理。\n"
        "品牌特色：野生現流海鮮，龜吼漁港直送，品質第一，服務高端客群，台灣在地漁業。\n"
        "情境：用戶在我們的 YouTube 影片下方留言。\n\n"
        "請根據以下留言，用繁體中文回覆一句簡短、溫暖的回應：\n"
        "- 字數 15～25 字之間\n"
        "- 自然親切，符合高端海鮮品牌調性\n"
        "- 加入 1 個相關 emoji\n"
        "- 若留言與購買/詢價/採購相關，鼓勵私訊或留下聯絡方式\n"
        "- 只輸出回覆內容本身，不要加引號或任何前綴說明\n\n"
        f"留言內容：{text}"
    )
    payload = json.dumps({
        'model':      CLAUDE_MODEL,
        'max_tokens': 256,
        'messages':   [{'role': 'user', 'content': prompt}]
    }).encode()
    req = urllib.request.Request(
        CLAUDE_API, data=payload,
        headers={
            'x-api-key':         ANTHROPIC_KEY,
            'anthropic-version': '2023-06-01',
            'content-type':      'application/json'
        },
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())
    return data['content'][0]['text'].strip()

# ── 主流程 ────────────────────────────────────────────────────────

def main():
    state       = load_state()
    since_ts    = state['last_checked']
    replied_ids = set(state['replied_ids'])
    now_ts      = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    new_replies = 0

    try:
        token = get_access_token()
    except Exception as e:
        log(f"❌ 取得 Access Token 失敗：{e}")
        sys.exit(1)

    # 取最近 50 筆留言（以頻道為單位，按時間排序）
    try:
        result  = yt_get('commentThreads', {
            'part':                         'snippet',
            'allThreadsRelatedToChannelId': CHANNEL_ID,
            'order':                        'time',
            'maxResults':                   '50',
        }, token)
        threads = result.get('items', [])
    except Exception as e:
        log(f"❌ 取得留言失敗：{e}")
        sys.exit(1)

    # 過濾：只取 since_ts 之後的新留言
    new_threads = [
        t for t in threads
        if t['snippet']['topLevelComment']['snippet']['publishedAt'] > since_ts
    ]
    log(f"查詢到 {len(new_threads)} 筆新留言（since {since_ts[:16]}）")

    for thread in new_threads:
        top        = thread['snippet']['topLevelComment']
        comment_id = top['id']
        snippet    = top['snippet']
        author_ch  = snippet.get('authorChannelId', {}).get('value', '')
        text       = snippet.get('textOriginal', '').strip()

        # 排除：空白、自己的留言、已回覆
        if not text or author_ch == CHANNEL_ID or comment_id in replied_ids:
            continue

        try:
            reply = claude_reply(text)
        except Exception as e:
            log(f"  Claude 失敗：{e}，使用備用回覆")
            reply = FALLBACK

        try:
            yt_post('comments', {
                'snippet': {
                    'parentId':     comment_id,
                    'textOriginal': reply,
                }
            }, token)
            replied_ids.add(comment_id)
            new_replies += 1
            log(f"  ✅ {text[:25]}… → {reply[:40]}…")
        except Exception as e:
            log(f"  ❌ 回覆失敗：{e}")

    state['last_checked'] = now_ts
    state['replied_ids']  = list(replied_ids)
    save_state(state)
    log(f"完成，共回覆 {new_replies} 則留言")

if __name__ == '__main__':
    main()
