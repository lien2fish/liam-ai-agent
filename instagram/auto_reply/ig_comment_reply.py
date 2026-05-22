#!/usr/bin/env python3
"""
IG 留言自動回覆 - 輪詢版
本機 cron 或 GitHub Actions 皆可執行
"""

import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── 路徑設定 ──────────────────────────────────────────────────────
# GitHub Actions 時使用 GITHUB_WORKSPACE，本機用預設路徑
WORKSPACE   = Path(os.environ.get('GITHUB_WORKSPACE', '/Users/lien/Downloads/Liam AI agent'))
CONFIG_FILE = WORKSPACE / 'config/instagram_config.json'
STATE_FILE  = WORKSPACE / 'instagram/auto_reply/reply_state.json'
LOG_FILE    = Path('/tmp/ig_comment_reply.log')

GRAPH_API     = 'https://graph.facebook.com/v19.0'
GEMINI_MODELS = [
    'gemini-3.5-flash',    # 主要：最新模型，回覆品質最佳
    'gemini-2.5-flash',    # 備用一
    'gemini-2.0-flash',    # 備用二
]
FALLBACK = '感謝您的留言！有任何海鮮採購需求，歡迎私訊詢問 🐟'
MAX_IDS    = 2000

# ── 載入設定（env var 優先，本機用 config 檔）────────────────────
def load_config():
    ig_token   = os.environ.get('IG_TOKEN')
    ig_id      = os.environ.get('IG_ID')
    gemini_key = os.environ.get('GEMINI_KEY')

    if not all([ig_token, ig_id, gemini_key]):
        cfg = json.loads(CONFIG_FILE.read_text())
        ig_token   = ig_token   or cfg['long_lived_user_token']
        ig_id      = ig_id      or cfg['ig_account_id']
        gemini_key = gemini_key or cfg['gemini_api_key']

    return ig_token, ig_id, gemini_key

IG_TOKEN, IG_ID, GEMINI_KEY = load_config()

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

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    since = (datetime.now(timezone.utc) - timedelta(minutes=6)).strftime('%Y-%m-%dT%H:%M:%S+0000')
    return {'last_checked': since, 'replied_ids': []}

def save_state(state):
    state['replied_ids'] = state['replied_ids'][-MAX_IDS:]
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

def api_get(path, params=None):
    p = dict(params or {})
    p['access_token'] = IG_TOKEN
    url = f"{GRAPH_API}/{path}?{urllib.parse.urlencode(p)}"
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read())

def api_post(path, data=None):
    d = dict(data or {})
    d['access_token'] = IG_TOKEN
    req = urllib.request.Request(
        f"{GRAPH_API}/{path}",
        data=urllib.parse.urlencode(d).encode(),
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def gemini_reply(text):
    prompt = f"""你是「龜吼現流活海產 / From Source To TABLE」品牌的客服助理。
品牌特色：野生現流海鮮，龜吼漁港直送，品質第一，服務高端客群，台灣在地漁業。
情境：用戶在我們的 Instagram 貼文或 Reels 下方留言。

請根據以下留言，用繁體中文回覆一段溫暖、專業的短回應：
- 字數不超過 60 字
- 自然親切，符合高端海鮮品牌調性
- 可適當加入 1～2 個相關 emoji
- 若留言與購買/詢價/採購相關，鼓勵私訊詢問
- 只輸出回覆內容本身，不要加引號或任何前綴說明

留言內容：{text}"""

    for model in GEMINI_MODELS:
        # 思考型模型（3.x / 2.5）關閉思考模式，避免 token 被內部推理佔光
        is_thinking_model = any(x in model for x in ['3.5', '3.1', '3-', '2.5'])
        config_extra = {'thinkingConfig': {'thinkingBudget': 0}} if is_thinking_model else {}

        payload = json.dumps({
            'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {'maxOutputTokens': 256, 'temperature': 0.75, **config_extra}
        }).encode()

        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
        req = urllib.request.Request(
            api_url, data=payload,
            headers={'Content-Type': 'application/json'}, method='POST'
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read())
            candidate = data['candidates'][0]
            reply = candidate['content']['parts'][0]['text'].strip()
            if candidate.get('finishReason') == 'MAX_TOKENS' or len(reply) < 8:
                log(f"  {model} 回覆不完整，切換下一個模型")
                continue
            return reply
        except urllib.request.HTTPError as e:
            if e.code in (429, 503):
                log(f"  {model} 失敗（{e.code}），切換下一個模型")
                continue
            raise
    raise Exception("所有 Gemini 模型均無法使用")

# ── 主流程 ────────────────────────────────────────────────────────

def main():
    state       = load_state()
    since_ts    = state['last_checked']
    replied_ids = set(state['replied_ids'])
    now_ts      = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+0000')
    new_replies = 0

    try:
        media_list = api_get(f"{IG_ID}/media", {'fields': 'id,timestamp', 'limit': '20'}).get('data', [])
    except Exception as e:
        log(f"❌ 取得貼文列表失敗：{e}")
        sys.exit(1)

    log(f"查詢 {len(media_list)} 篇貼文（since {since_ts[:16]}）")

    for media in media_list:
        media_id = media['id']
        try:
            comments = api_get(f"{media_id}/comments", {
                'fields': 'id,text,from,timestamp',
                'limit': '50'
            }).get('data', [])
        except Exception as e:
            log(f"  貼文 {media_id} 取留言失敗：{e}")
            continue

        new_comments = [
            c for c in comments
            if c.get('timestamp', '') > since_ts
            and c.get('from', {}).get('id') != IG_ID
            and c['id'] not in replied_ids
            and c.get('text', '').strip()
        ]

        for c in new_comments:
            cid  = c['id']
            text = c['text'].strip()

            try:
                reply = gemini_reply(text)
            except Exception as e:
                log(f"  Gemini 失敗：{e}，使用備用回覆")
                reply = FALLBACK

            try:
                api_post(f"{cid}/replies", {'message': reply})
                replied_ids.add(cid)
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
