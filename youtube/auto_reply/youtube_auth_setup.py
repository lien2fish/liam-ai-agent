#!/usr/bin/env python3
"""
YouTube OAuth 設定腳本
用途：取得 Refresh Token，存入 GitHub Secrets
執行：python3 youtube/auto_reply/youtube_auth_setup.py
"""

import json
import urllib.request
import urllib.parse

# ── 填入你的 OAuth 憑證（從 Google Cloud Console 下載）──────────
CLIENT_ID     = input("貼上 client_id：").strip()
CLIENT_SECRET = input("貼上 client_secret：").strip()
REDIRECT_URI  = 'urn:ietf:wg:oauth:2.0:oob'   # 桌面應用授權碼模式

SCOPE = 'https://www.googleapis.com/auth/youtube.force-ssl'

# ── Step 1：產生授權 URL ───────────────────────────────────────
auth_url = (
    'https://accounts.google.com/o/oauth2/v2/auth?'
    + urllib.parse.urlencode({
        'client_id':     CLIENT_ID,
        'redirect_uri':  REDIRECT_URI,
        'response_type': 'code',
        'scope':         SCOPE,
        'access_type':   'offline',
        'prompt':        'consent',
    })
)

print('\n① 在瀏覽器開啟以下網址並登入 Google 帳號：')
print(f'\n{auth_url}\n')
print('② 授權後頁面會顯示一組授權碼，複製貼回這裡。')

code = input('\n貼上授權碼：').strip()

# ── Step 2：換取 Token ────────────────────────────────────────
data = urllib.parse.urlencode({
    'code':          code,
    'client_id':     CLIENT_ID,
    'client_secret': CLIENT_SECRET,
    'redirect_uri':  REDIRECT_URI,
    'grant_type':    'authorization_code',
}).encode()

req = urllib.request.Request(
    'https://oauth2.googleapis.com/token',
    data=data, method='POST'
)

with urllib.request.urlopen(req) as r:
    tokens = json.loads(r.read())

refresh_token = tokens.get('refresh_token')
if not refresh_token:
    print('❌ 沒有收到 refresh_token，請確認已勾選 access_type=offline 且 prompt=consent')
    raise SystemExit(1)

print('\n✅ 授權成功！以下是需要設定到 GitHub Secrets 的值：\n')
print(f'YT_CLIENT_ID     = {CLIENT_ID}')
print(f'YT_CLIENT_SECRET = {CLIENT_SECRET}')
print(f'YT_REFRESH_TOKEN = {refresh_token}')
print('\n另外需要 YT_CHANNEL_ID（頻道 ID，格式 UC...），')
print('到 https://studio.youtube.com → 設定 → 頻道 → 進階設定 複製。')
