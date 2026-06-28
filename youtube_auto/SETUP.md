# YouTube 自動 Shorts — 一次性設定指南

程式已寫好（生腳本→產影片→上傳→每日排程）。以下是**只需做一次**的人工步驟，因為 Google 帳號註冊與 OAuth 授權無法自動化。

## 1. 建立 YouTube 頻道
用一個 Google 帳號到 youtube.com 建立新頻道（建議用品牌名，英文，主題 History & Unsolved Mysteries）。

## 2. Google Cloud 設定
1. console.cloud.google.com → 建/選一個專案
2. 「API 和服務」→ 啟用 **YouTube Data API v3**
3. 「OAuth 同意畫面」→ User type 選 **External** →填基本資料
4. **發布狀態改為「正式（In production）」**（⚠️ 關鍵：留在「測試」模式 refresh token 每 7 天失效，自動上傳會斷）
5. 「憑證」→ 建立憑證 → OAuth 用戶端 ID → 應用程式類型 **桌面應用程式**
6. 下載該用戶端的 JSON，存成 `config/youtube_client.json`

## 3. 取得 refresh token（沿用 Gmail 那套手動流程）
```bash
# 1) 產生授權網址
python3 youtube_auto/oauth_setup.py
# 2) 複製網址 → 用 Safari 開啟 → 登入該頻道帳號 → 允許
#    瀏覽器跳到 http://localhost:8888/?code=4/0A...，複製整段 code
# 3) 換取並儲存 refresh token
python3 youtube_auto/oauth_setup.py "貼上code"
```
完成後 `config/youtube_oauth.json` 會有 client_id / client_secret / refresh_token。

## 4. 設定 GitHub Secrets（3 個）
到 repo → Settings → Secrets and variables → Actions 新增：
| Secret | 值來源 |
|--------|--------|
| `YT_OAUTH_CLIENT_ID` | youtube_oauth.json 的 client_id |
| `YT_OAUTH_CLIENT_SECRET` | youtube_oauth.json 的 client_secret |
| `YT_OAUTH_REFRESH_TOKEN` | youtube_oauth.json 的 refresh_token |

（`ANTHROPIC_API_KEY`、`HF_TOKEN` 已存在，共用）

## 5. 驗證與上線
```bash
# 本機完整測一支（會以 private 上傳到你的頻道）
python3 youtube_auto/make_and_upload.py
```
1. 先在頻道看到 private 影片、檢查畫面/配音/字幕
2. 雲端：GitHub Actions → 「YouTube 每日自動 Shorts」→ Run workflow 手動測一次
3. 都 OK 後，把 `.github/workflows/yt_auto_post.yml` 裡 `YT_PRIVACY` 從 `private` 改成 `public`，即每天 10:00 自動公開發片

## 注意
- 影片預設 **private**，確認品質前不會公開
- 主題自動去重（`recent_topics.json`）
- 升級配音音質：把 `make_and_upload` 的配音改接 ElevenLabs（目前用免費 edge-tts）
- 變現需達 YPP 門檻（1,000 訂閱 + 90 天 1,000 萬 Shorts 觀看）且內容需有原創價值，非保證
