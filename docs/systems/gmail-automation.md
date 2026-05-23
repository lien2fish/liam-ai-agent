# Gmail 自動化系統

## 腳本清單

| 腳本 | 功能 | 排程 |
|------|------|------|
| `gmail_monthly_cleanup.py` | 清理舊郵件（訂閱、通知類） | 每天 08:05 |
| `gmail_news_digest.py` | 抓取新聞摘要寫入 md 檔 | 每天 08:00 |

## OAuth Token

| 項目 | 路徑 |
|------|------|
| Token | `~/.config/gmail-cleanup-token.json` |
| 憑證 | `~/.config/gmail-cleanup-credentials.json` |

**Token 失效症狀**：`invalid_grant: Token has been expired or revoked.`

## 重新授權步驟

```bash
# Step 1：生成授權 URL
python3 -c "
import json,urllib.parse
c=json.load(open('/Users/lien/.config/gmail-cleanup-credentials.json'))
cl=c.get('installed',c)
print('https://accounts.google.com/o/oauth2/v2/auth?'+urllib.parse.urlencode({
    'client_id':cl['client_id'],
    'redirect_uri':'http://localhost:8888',
    'response_type':'code',
    'scope':'https://www.googleapis.com/auth/gmail.modify',
    'access_type':'offline','prompt':'consent'
}))
"

# Step 2：用 Safari 開啟 → 授權 → 複製 code

# Step 3：換取 token（替換 CODE）
python3 -c "
import json,urllib.parse,urllib.request
CODE='貼上授權碼'
c=json.load(open('/Users/lien/.config/gmail-cleanup-credentials.json'))
cl=c.get('installed',c)
r=json.loads(urllib.request.urlopen(urllib.request.Request(
    'https://oauth2.googleapis.com/token',
    data=urllib.parse.urlencode({'code':CODE,'client_id':cl['client_id'],
    'client_secret':cl['client_secret'],'redirect_uri':'http://localhost:8888',
    'grant_type':'authorization_code'}).encode(),
    headers={'Content-Type':'application/x-www-form-urlencoded'},method='POST'
)).read())
json.dump({'token':r['access_token'],'refresh_token':r['refresh_token'],
    'token_uri':'https://oauth2.googleapis.com/token','client_id':cl['client_id'],
    'client_secret':cl['client_secret'],'scopes':['https://www.googleapis.com/auth/gmail.modify']},
    open('/Users/lien/.config/gmail-cleanup-token.json','w'),indent=2)
print('✅ Token 儲存完成')
"
```

> 注意：gmail_auth_setup.py 的 Playwright 流程已廢棄（Google 封鎖自動化瀏覽器）
