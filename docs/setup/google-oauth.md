# Google OAuth 設定

## 專案資訊

| 項目 | 值 |
|------|-----|
| 專案名稱 | claude-workspace-495009 |
| Client ID | 879735593233-0r9qp9q9v5gea8j36dtcbrj6fmi660vh.apps.googleusercontent.com |
| 憑證類型 | 電腦版應用程式（Installed App） |
| 憑證存放 | ~/.config/google-workspace-mcp/credentials.json |

## 已授權 Scope

| Scope | 用途 | Token 存放 |
|-------|------|-----------|
| `gmail.modify` | Gmail 清理、新聞摘要 | ~/.config/gmail-cleanup-token.json |
| `youtube.force-ssl` | YouTube 留言回覆 | GitHub Secret: YT_REFRESH_TOKEN |
| Google Workspace（多個） | MCP 工具（Gmail/Calendar/Drive/Sheets） | ~/.config/google-workspace-mcp/ |

## 測試使用者設定（重要）

App 處於 **Testing 模式**，必須將使用者加入清單才能授權：

1. 前往：https://console.cloud.google.com/auth/audience?project=claude-workspace-495009
2. 確認 `lien2fish@gmail.com` 在測試使用者清單中

## Gmail OAuth 重授權步驟

```bash
# 生成授權 URL
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
# 在 Safari 開啟 → 授權 → 複製 code → 換取 token
```

## YouTube OAuth 重授權步驟

```bash
python3 /tmp/oauth_capture2.py &
open -a Safari "[授權URL]"
# 授權後 code 自動存入 /tmp/yt_oauth_code.txt
```
