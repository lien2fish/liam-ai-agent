# GitHub Secrets 清單

> Repo: lien2fish/liam-ai-agent
> 設定位置: Settings → Secrets and variables → Actions

## IG + FB 自動發文（6個）

| Secret | 說明 | 到期日 |
|--------|------|--------|
| `GEMINI_KEY` | Google Gemini API Key | 永久 |
| `HF_TOKEN` | Hugging Face Token（FLUX圖片生成） | 永久 |
| `IG_TOKEN` | Instagram User Token | **2026-07-16** ⚠️ |
| `IG_ID` | Instagram Account ID | 永久 |
| `FB_PAGE_TOKEN` | Facebook Page Token | 永久（長效Token） |
| `FB_PAGE_ID` | Facebook Page ID：1081333268402454 | 永久 |

### IG Token 更新方式（到期前執行）
1. 至 [Meta Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. 選 App：Liam AI（ID: 1310018353798687）
3. 勾選權限：`instagram_manage_comments` + 其他現有權限
4. 複製 Token
5. 更新 `config/instagram_config.json` + GitHub Secret `IG_TOKEN`

---

## YouTube 留言自動回覆（4個）

| Secret | 說明 | 到期日 |
|--------|------|--------|
| `YT_CLIENT_ID` | Google OAuth Client ID | 永久 |
| `YT_CLIENT_SECRET` | Google OAuth Client Secret | 永久 |
| `YT_REFRESH_TOKEN` | YouTube Refresh Token | 永久 |
| `YT_CHANNEL_ID` | 頻道 ID：UCKScBZqHjasWfizXWna1Huw | 永久 |

### YouTube Token 重授權步驟（若失效）
```bash
python3 /tmp/oauth_capture2.py &
open -a Safari "https://accounts.google.com/o/oauth2/v2/auth?client_id=879735593233-0r9qp9q9v5gea8j36dtcbrj6fmi660vh.apps.googleusercontent.com&redirect_uri=http%3A%2F%2Flocalhost%3A8888&response_type=code&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fyoutube.force-ssl&access_type=offline&prompt=consent"
# 授權後 code 存於 /tmp/yt_oauth_code.txt
# 用 PyNaCl 寫入 GitHub Secret
```

---

## GitHub PAT

| 項目 | 說明 |
|------|------|
| Scope | `repo` + `workflow` |
| 到期日 | 永不過期 |
| 用途 | git push（含 workflow 檔）、寫入 Secrets |
| 存放 | git remote URL |
