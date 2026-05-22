# Liam AI Agent 專案

## 身份與背景
- **使用者**：Lien（企業主 / 管理顧問）
- **公司**：鉅鑫管理顧問有限公司
- **品牌**：鑫酒坊（葡萄酒）、鑫茶坊（茶葉）、匠鑫私廚、龜吼現流活海產
- **核心價值**：鉅鑫只提供最高品質

## 工作目錄
所有開發與任務的根目錄：`/Users/lien/Downloads/Liam AI agent`

## 語言規則
- 一律使用**繁體中文**回覆
- 技術術語、程式碼保留英文原文
- 回覆簡潔有力，重點優先

## 技術環境
- **Shell**：bash（不是 zsh）
- **啟動指令**：`cc`（alias，自動進入此目錄並啟動 Claude Code with NO_FLICKER）
- **設定檔**：`~/.bashrc`（PATH + aliases）、`~/.bash_profile`（引入 .bashrc）
- **Node.js**：v24.15.0，透過 nvm 安裝（`~/.nvm`）

## MCP 工具（已安裝，scope: user）
| 工具 | 套件 | 說明 |
|------|------|------|
| firecrawl | `firecrawl-mcp` | 抓取任何網頁內容，API Key 已設定於環境變數 |
| filesystem | `@modelcontextprotocol/server-filesystem` | 存取 Desktop / Documents / Downloads |
| playwright | `@playwright/mcp` | 控制 Chromium 瀏覽器 |
| google-workspace | `@presto-ai/google-workspace-mcp` | Gmail、Calendar、Drive、Sheets 等，首次使用需 OAuth 登入 |
| notion-mcp | Notion MCP | 搜尋、新增頁面等 Notion 操作 |

- OAuth 憑證存放：`~/.config/google-workspace-mcp/credentials.json`
- 查看 MCP 狀態：`/mcp`

## 已授權工具權限（settings.json allow 清單）

### MCP 工具已允許功能
| 工具 | 已允許的操作 |
|------|-------------|
| filesystem | write_file |
| playwright | navigate、screenshot、snapshot、click、type、press_key、evaluate、resize、close |
| google-workspace | gmail_search、gmail_get、calendar_list、calendar_listEvents、sheets_getRange、people_getMe、time_getCurrentDate |
| firecrawl | map、scrape、crawl、agent、agent_status |
| notion-mcp | post-search、get-self、post-page |

### Bash 指令已允許
| 類別 | 允許的指令 |
|------|-----------|
| npm/Node | `npm list *`、`npx --version`、`node -e ...` |
| Python | `python3 *`、`pip3 install *`、`pip3 --version` |
| 系統工具 | `curl *`、`osascript *`、`open *`、`trash *`、`mv`、`cp`、`mkdir`、`sort`、`env`、`chmod +x` |
| 安全鑰匙圈 | `security find-generic-password *`、`security find-internet-password *` |
| Cron/Shell | `crontab *`、`/bin/bash *`、`bash` |
| 其他 | `log show *`、`convert --version`、`npm cache *`、`xargs du -ch`、`kill <PID>` |

### 內建工具已允許
- `Edit`（無限制，可編輯所有路徑）

### WebFetch 已允許網域
- `raw.githubusercontent.com`

### 技能（Skill）
- `schedule`

## 安全設定（已配置，請勿修改）
- `rm` 已 alias 為 `trash`，刪除會進垃圾桶而非永久刪除
- 永久刪除請用 `rm!`
- `~/.claude/settings.json` 已封鎖危險指令：`rm -rf`、`sudo`、`dd`、`mkfs`、`diskutil erase`、`chmod 777`、`git reset --hard`、`git push --force`、`git clean -f`、`git branch -D`、`shutdown`、`reboot`、`truncate`、`: >`
- 權限模式：**acceptEdits**（檔案編輯自動通過；遇到清單外新工具彈一次確認，允許後自動加入清單）
- **不可用 `dontAsk`**：此模式會靜默封鎖所有需確認的操作（包含 allow 清單內的 Edit），導致任務中斷卡死

## IG + FB 每日自動發文系統

### 核心資訊
| 項目 | 說明 |
|------|------|
| 腳本 | `instagram/generate_post.py` |
| 排程 | GitHub Actions，每天 UTC 00:00（台灣 08:00）自動執行 |
| Workflow | `.github/workflows/daily_post.yml` |
| 底圖 | `instagram/template.png`（2700×3375px → 輸出 1080×1920） |
| 圖片存放 | `instagram/posts/YYYY-MM-DD.jpg`（每次 workflow 自動 commit） |

### 流程
1. **Gemini 2.5 Flash** 生成知識 JSON（5～6句，三大類：海鮮/捕魚/漁船）
2. **HF FLUX.1-schnell** 生成圖文對應水彩插圖
3. **PIL** 動態排版合成（插圖大小＋字型大小依內容量自動調整）
4. **GitHub API** 上傳圖片 → raw.githubusercontent.com 公開 URL（repo 必須 public）
5. **Meta Graph API v19.0** 同時發送：
   - IG 限時動態（`{IG_ID}/media`，media_type=STORIES，帶 `cross_post_ids={FB_PAGE_ID}`）
   - FB 限時動態透過 `cross_post_ids` 跨發，**不使用** `photo_stories`（該端點持續回傳 unknown error）

### GitHub Secrets（6個，已設定）
`GEMINI_KEY` / `HF_TOKEN` / `IG_TOKEN` / `IG_ID` / `FB_PAGE_TOKEN` / `FB_PAGE_ID`

---

## IG 留言自動回覆系統

### 核心資訊
| 項目 | 說明 |
|------|------|
| 腳本 | `instagram/auto_reply/ig_comment_reply.py` |
| 排程 | GitHub Actions，每 5 分鐘（`*/5 * * * *`） |
| Workflow | `.github/workflows/ig_comment_reply.yml` |
| 狀態快取 | GitHub Actions Cache（`ig-reply-state-*`） |
| AI 回覆 | Gemini 3.5-flash（主）→ 2.5-flash → 2.0-flash（降級），繁體中文，15～25 字 |

### Gemini 模型設定（重要）
- **主力：`gemini-3.5-flash`**（思考型模型，需設 `thinkingBudget: 0` 否則輸出截斷）
- 降級順序：3.5-flash → 2.5-flash → 2.0-flash（遇 429/503 自動切換）
- `maxOutputTokens: 256`、`temperature: 0.75`
- 思考型模型判斷：model 名稱含 `3.5` / `3.1` / `3-` / `2.5` → 套用 `thinkingBudget: 0`

### 流程
1. 取最近 20 篇貼文的留言（since 上次執行時間）
2. 過濾：排除自己、已回覆、空白留言
3. Gemini 生成 15～25 字回覆（失敗/截斷時切換模型，最終備用固定回覆）
4. `POST /{comment_id}/replies` 發布回覆

### 所需權限
- `instagram_manage_comments`（2026-05-22 已加入 Liam AI App）
- IG Token 需含此權限，更新時記得重新從 Graph API Explorer 取得（需勾選 `instagram_manage_comments`）

### 注意事項
- Meta Webhook 機制限制多（新版 Use Cases 架構無法用 `subscribed_apps`），改用輪詢
- Cloudflare Worker（`ig-auto-reply.lien2fish.workers.dev`）已部署但未使用，可保留或刪除
- IG Token 到期（2026-07-16）後需同時更新 `config/instagram_config.json` 和 GitHub Secret `IG_TOKEN`
- `gemini-3.5-flash` 不設 `thinkingBudget: 0` 會導致回覆只輸出幾個字（MAX_TOKENS 截斷）

### Facebook 粉絲專頁資訊
| 項目 | 說明 |
|------|------|
| 名稱 | From Source To TABLE |
| Page ID | `1081333268402454` |
| FB_PAGE_TOKEN | 永不過期（長效 Page Token） |
| Meta App | Liam AI（ID: 1310018353798687），已切換 Live Mode |
| 管理方式 | Meta Business Suite（Business ID: 2163986274210892） |
| 隱私政策頁 | https://lien2fish.github.io/liam-ai-agent/privacy.html |

### 重要到期日
- **IG Token：2026-07-16 到期**，需從 Meta Graph API Explorer 重新取得（需含 `instagram_manage_comments` 權限）
- **FB Page Token：永不過期**（無需更新）
- 更新 Token 方式：用 `nacl.public.SealedBox` 直接寫入 GitHub Secret（系統 PyNaCl 1.6.2 已支援）
- **GitHub PAT（舊）：2026-08-15 到期** — 已廢棄，改用新 PAT
- **GitHub PAT（新）：永不過期**，含 `repo` + `workflow` scope，已設定於 git remote URL

### 注意事項
- Repo 維持 **public**（config/ 已 gitignore，無憑證外洩風險）
- 每次 workflow 跑完會 commit 圖片，本地 push 前需 `git pull --rebase`
- Linux 字型用 `fc-list :lang=zh` 動態查找 Noto CJK TTC（index=3）
- catbox.moe / transfer.sh 均因 GitHub Actions IP 被封鎖，已廢棄
- GitHub PAT 現在有 `workflow` scope，可直接 push workflow 檔
- Instagram Webhook（Meta）訂閱機制限制多，改用輪詢（Polling）方式取代
- FB Page 透過 Business Suite 管理，`/me/accounts` 不會回傳；需用 `debug_token` 的 `granular_scopes` 找真正 Page ID
- `photo_stories` API 不可用（任何版本皆回傳 unknown error），FB 限時動態改用 IG `cross_post_ids`
- prompt 為 f-string 時，JSON 範本的 `{}` 必須寫成 `{{}}`，否則 ValueError

---

## YouTube 留言自動回覆系統

### 核心資訊
| 項目 | 說明 |
|------|------|
| 腳本 | `youtube/auto_reply/yt_comment_reply.py` |
| 排程 | GitHub Actions，每 10 分鐘（`*/10 * * * *`） |
| Workflow | `.github/workflows/yt_comment_reply.yml` |
| 狀態快取 | GitHub Actions Cache（`yt-reply-state-*`） |
| AI 回覆 | Gemini 3.5-flash（主）→ 2.5-flash → 2.0-flash（降級），繁體中文，15～25 字 |
| 頻道 | 連老闆-產地到餐桌（`UCKScBZqHjasWfizXWna1Huw`） |

### GitHub Secrets（4個，已設定）
`YT_CLIENT_ID` / `YT_CLIENT_SECRET` / `YT_REFRESH_TOKEN` / `YT_CHANNEL_ID`
- OAuth 使用 `claude-workspace-495009` 既有專案（同 Google Workspace MCP）
- Refresh Token **永不過期**（無需定期更新）
- API 配額：每日 10,000 單位，回覆留言 50 單位/則，約可回覆 ~190 則/天

### 流程
1. 取頻道最近 50 筆留言（`allThreadsRelatedToChannelId`，`order=time`）
2. 過濾：only since 上次執行時間、排除自己、排除空白
3. Gemini 生成 15～25 字回覆（失敗時切換模型，最終備用固定回覆）
4. `POST /youtube/v3/comments?part=snippet` 發布回覆

### OAuth 重新授權步驟（Refresh Token 若失效）
```bash
# Step 1：啟動捕捉 server
python3 /tmp/oauth_capture2.py &
# Step 2：開啟授權頁（Safari）
open -a Safari "https://accounts.google.com/o/oauth2/v2/auth?client_id=879735593233-0r9qp9q9v5gea8j36dtcbrj6fmi660vh.apps.googleusercontent.com&redirect_uri=http%3A%2F%2Flocalhost%3A8888&response_type=code&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fyoutube.force-ssl&access_type=offline&prompt=consent"
# Step 3：授權後用 code 換 token，再用 PyNaCl 寫入 GitHub Secret
```
- **注意**：`lien2fish@gmail.com` 需在 [cloud.google.com/auth/audience](https://console.cloud.google.com/auth/audience?project=claude-workspace-495009) 測試使用者清單中

### 注意事項
- Gemini 設定與 IG 系統相同：thinking model 需 `thinkingBudget: 0`
- 若 Access Blocked（403）：確認 Google Cloud Console 測試使用者清單已加入 `lien2fish@gmail.com`
- YouTube Data API v3 需在 `claude-workspace-495009` 專案啟用

---

## 社群平台自動化總覽

| 平台 | 類型 | 排程 | 狀態 |
|------|------|------|------|
| IG + FB | 每日發文 | 每天 08:00 | ✅ 運行中 |
| IG | 留言自動回覆 | 每 5 分鐘 | ✅ 運行中 |
| YouTube | 留言自動回覆 | 每 10 分鐘 | ✅ 運行中 |
| TikTok | — | — | 手動，不自動化 |

---

## 瀏覽器操作原則

- **一律使用 Safari**：`open -a Safari "URL"`
- **不使用 Playwright Chromium**（除非純粹截圖分析，與登入無關）
- Google OAuth 授權流程：啟動 `python3 /tmp/oauth_capture2.py &`（port 8888）→ 開 Safari 授權 → code 自動寫入 `/tmp/yt_oauth_code.txt`

---

## 指引牌產圖系統（2026 扶輪年會）

### 腳本與資料檔
| 項目 | 路徑 |
|------|------|
| 主要腳本 | `/Users/lien/Downloads/南港展覽館/generate_from_numbers.py` |
| Numbers 資料檔 | `/Users/lien/Desktop/HOC團隊/舉牌規格/指引牌資料.numbers` |
| 輸出：立牌 | `/Users/lien/Desktop/HOC團隊/舉牌規格/指引牌/放置立牌/` |
| 輸出：手舉牌 | `/Users/lien/Desktop/HOC團隊/舉牌規格/指引牌/手舉牌/` |

**執行方式：**
```bash
cd /Users/lien/Downloads/南港展覽館 && python3 generate_from_numbers.py
```
腳本會自動跳過已存在的 PNG，只產出新的。

### Numbers 欄位（A~M）
| 欄 | 名稱 | 說明 |
|----|------|------|
| A | 編號 | E1-1, B1-2... |
| B | 版型 | `標準` / `多活動` / `多館別` |
| C | 類型 | `手舉牌` / `立牌` |
| D | 活動區塊 | 依版型（多活動型每行一條，多館別留空） |
| E | 活動區塊英文 | 標準型才填，其他留空 |
| F | 出口①標籤 | Gate 5 / Exit 1 / 多館別館別標題 |
| G | 出口①說明 | 多活動才填 / 多館別子項目（換行分隔） |
| H | 出口②標籤 | 多活動才填 / 多館別第二館標題 |
| I | 出口②說明 | 多活動才填 / 多館別第二館子項目 |
| J | 場地（中） | 中英合行可直接填此欄，K 留空 |
| K | 場地（英） | 分開填寫時才用 |
| L | 底部說明（中） | 標準型才填 |
| M | 底部說明（英） | 標準型才填 |

### 三種版型
- **標準型**：單一活動 + 單一出口，D/E/F/J/K/L/M
- **多活動型**：多活動列表（D 換行分隔）+ 最多兩個 Gate（F-I）+ 場地（J-K）
- **多館別型**：D/E 留空，F/H 館別大標題（紅色），G/I 子項目，J/K 場地

### 字型規格（已確認，2026-05-08）
| 角色 | 字型檔 | Index |
|------|--------|-------|
| zh_font（中文/混合/箭頭） | `/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc` | 2 |
| en_font（純英文） | `/System/Library/Fonts/HelveticaNeue.ttc` | 1 |

### 排版關鍵常數
| 常數 | 值 | 說明 |
|------|-----|------|
| `W × H` | 3535 × 5000 px | 畫布尺寸 |
| `HEADER_BTM` | 1310 | "2026 RIC" 文字下緣，置中頂部基準 |
| `VENUE_Y` | 3750 | 場地文字起始 Y |
| `CONTENT_TOP` | 1380 | 標準型專用 |

**置中邏輯：**
- 多館別：整體內容垂直置中於 `HEADER_BTM` ～ (`VENUE_Y` 有場地 / `H` 無場地)
- 多活動：D/E 活動區塊置中於 `HEADER_BTM` ～ `fm_top`（Gate 區塊上方）；Gate 從 `fm_top` 往下；場地 = `max(y_after_gate + 80 + label_sz, VENUE_Y)`
- 標準型：D/E/F 整體置中於 `CONTENT_TOP` ～ `CONTENT_BTM`

## Gmail 自動化腳本系統

### Crontab 排程（每天 08:00 台灣時間）
| 腳本 | 排程 | Log |
|------|------|-----|
| `gmail_monthly_cleanup.py` | `5 8 * * *` | `財務/gmail_cleanup_log.txt` |
| `gmail_news_digest.py` | `0 8 * * *` | `今日新聞摘要.md`（覆寫） |
| `notion_crm/monthly_report.py` | `0 8 1 * *` | `/tmp/notion_monthly_report.log` |
| `instagram/generate_post.py` | `0 8 * * *`（本機備用） | `/tmp/ig_post.log` |
| `cache_cleanup.sh` | `0 6 * * *` | `/tmp/liam_cache_cleanup.log` |

### Gmail OAuth Token
| 項目 | 路徑 |
|------|------|
| Token 檔 | `~/.config/gmail-cleanup-token.json` |
| 憑證檔 | `~/.config/gmail-cleanup-credentials.json` |
| 授權腳本 | `gmail_auth_setup.py` |

**Token 失效症狀**：`invalid_grant: Token has been expired or revoked.`

**重新授權步驟（已驗證可行）：**
1. 生成 OAuth URL：
   ```bash
   python3 -c "
   import json,urllib.parse
   c=json.load(open('/Users/lien/.config/gmail-cleanup-credentials.json'))
   cl=c.get('installed',c)
   print('https://accounts.google.com/o/oauth2/v2/auth?'+urllib.parse.urlencode({'client_id':cl['client_id'],'redirect_uri':'http://localhost:8888','response_type':'code','scope':'https://www.googleapis.com/auth/gmail.modify','access_type':'offline','prompt':'consent'}))
   "
   ```
2. 在 Chrome 開啟 URL → 登入 `lien2fish@gmail.com` → 點「進階」→「前往（不安全）」→「允許」
3. 瀏覽器跳到 `http://localhost:8888/?code=4/0A...`，複製完整網址
4. 執行換取 token：
   ```bash
   python3 -c "
   import json,urllib.parse,urllib.request
   CODE='貼上授權碼'
   c=json.load(open('/Users/lien/.config/gmail-cleanup-credentials.json'))
   cl=c.get('installed',c)
   r=json.loads(urllib.request.urlopen(urllib.request.Request('https://oauth2.googleapis.com/token',data=urllib.parse.urlencode({'code':CODE,'client_id':cl['client_id'],'client_secret':cl['client_secret'],'redirect_uri':'http://localhost:8888','grant_type':'authorization_code'}).encode(),headers={'Content-Type':'application/x-www-form-urlencoded'},method='POST')).read())
   json.dump({'token':r['access_token'],'refresh_token':r['refresh_token'],'token_uri':'https://oauth2.googleapis.com/token','client_id':cl['client_id'],'client_secret':cl['client_secret'],'scopes':['https://www.googleapis.com/auth/gmail.modify']},open('/Users/lien/.config/gmail-cleanup-token.json','w'),indent=2)
   print('✅ Token 儲存完成')
   "
   ```
- **注意**：`gmail_auth_setup.py` 的 Playwright 自動化流程因 Google 封鎖自動化瀏覽器而無法使用，改用上述手動方式

---

## 開發原則
- 所有檔案操作預設在此資料夾進行
- 不寫不必要的註解，程式碼命名清楚就是最好的說明
- 不過度抽象化，解決當下問題為主
- 不加多餘的錯誤處理，除非是真實的邊界情況

## 回覆風格
- 直接給結論，不囉嗦
- 商業分析附具體數據與建議
- 文案符合高端品牌調性
- 表格優先於長段文字
