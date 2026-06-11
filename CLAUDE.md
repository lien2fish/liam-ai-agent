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

## YouTube Shorts 留言每日通知系統（2026-06-11 建立）

### 核心資訊
| 項目 | 說明 |
|------|------|
| 腳本 | `youtube/comment_monitor.py` |
| 排程 | GitHub Actions，每天 08:30（台灣）|
| Workflow | `.github/workflows/yt_comment_monitor.yml` |
| 狀態快取 | GitHub Actions Cache（`yt-monitor-state-*`，`youtube/monitor_state.json`） |
| 頻道 | 連老闆-產地到餐桌（`UCKScBZqHjasWfizXWna1Huw`） |

### 機制（不用 OAuth，無到期問題）
- 用 **API Key**（`YT_API_KEY`，限制為 YouTube Data API v3）讀取公開留言，不需 OAuth refresh token
- 取頻道 uploads playlist 最近 25 部影片，篩選出 `duration <= 60s` 視為 Shorts
- 對每部 Shorts 取 `commentThreads`，與快取的已讀留言 ID 比對找出新留言
- 有新留言 → 寫入 `reports/youtube_comments_YYYY-MM-DD.md` + Email 通知；無新留言則只寫報告不寄信

### Email 通知
- 用 **Gmail App 密碼**（`GMAIL_APP_PASSWORD`）+ smtplib 寄送，與 OAuth 系統無關，不會過期
- 寄件/收件皆為 `lien2fish@gmail.com`

### GitHub Secrets（3個）
`YT_API_KEY` / `YT_CHANNEL_ID` / `GMAIL_APP_PASSWORD`

---

## 社群平台自動化總覽

| 平台 | 類型 | 排程 | 狀態 |
|------|------|------|------|
| IG + FB | 每日發文 | 每天 08:00 | ✅ 運行中 |
| IG | 留言自動回覆 | 每 5 分鐘 | ✅ 運行中 |
| YouTube | Shorts 留言通知（不回覆） | 每天 08:30 | ✅ 運行中 |
| TikTok | — | — | 手動，不自動化 |

## GitHub Actions 自動化總覽（2026-06-02 更新）

所有雲端自動化任務均透過 GitHub Actions 執行，不依賴本機開機。

| Workflow 檔案 | 任務 | 排程 |
|--------------|------|------|
| `daily_post.yml` | IG+FB 每日發文 | 每天 08:00 |
| `ig_comment_reply.yml` | IG 留言自動回覆 | 每 5 分鐘 |
| `gmail_automation.yml` | Gmail 清理 + 新聞摘要 | 每天 08:00，自動 commit 報告 |
| `notion_monthly_report.yml` | Notion 月報 | 每月 1 日 08:00 |
| `market_daily.yml` | 每日股市全面分析報告 | 每天 **12:00**（台灣），自動 commit 報告 |
| `seafood_prices.yml` | 漁獲市場行情追蹤 | 每天 09:30 |
| `yt_comment_monitor.yml` | YouTube Shorts 留言通知 | 每天 08:30 |

### GitHub Secrets 總覽
| Secret | 用途 |
|--------|------|
| `GEMINI_KEY` | Gemini AI 付費 Key（claude-workspace-495009，**2.5-flash** 模型）|
| `HF_TOKEN` | Hugging Face FLUX 圖片生成 |
| `IG_TOKEN` | Instagram Graph API（到期 2026-07-16）|
| `IG_ID` | Instagram 帳號 ID |
| `FB_PAGE_TOKEN` | Facebook Page Token（永不過期）|
| `FB_PAGE_ID` | Facebook Page ID |
| `GMAIL_CLIENT_ID` | Gmail OAuth |
| `GMAIL_CLIENT_SECRET` | Gmail OAuth |
| `GMAIL_REFRESH_TOKEN` | Gmail OAuth |
| `NOTION_TOKEN` | Notion API Token |
| `YT_API_KEY` | YouTube Data API v3 金鑰（無到期問題）|
| `YT_CHANNEL_ID` | YouTube 頻道 ID |
| `GMAIL_APP_PASSWORD` | Gmail App 密碼，供 YouTube 留言通知寄信用 |

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

## 每日股市全面分析報告系統（2026-06-02 建立）

### 核心資訊
| 項目 | 說明 |
|------|------|
| 腳本 | `market/market_report.py` |
| 設定 | `market/market_config.json`（觀察股清單、Notion Page ID）|
| 歷史 | `market/market_history.json`（90天，自動維護）|
| 排程 | GitHub Actions，每天 12:00 台灣時間（UTC 04:00）|
| Workflow | `.github/workflows/market_daily.yml` |
| Notion | 固定頁面「每日市場日報」（每日覆寫，手機可查）|
| Markdown | `reports/市場日報_YYYY-MM-DD.md`（每日 commit）|

### 資料來源（三層）
| 層 | 來源 | 說明 |
|----|------|------|
| L1 | Yahoo Finance | 全球指數、宏觀指標、台灣觀察股（`urllib`，無需 key）|
| L2 | Gemini 2.5-flash + Google Search | 今日新聞、外資動向、AI 預測 |
| L3 | Gemini 知識庫 | L2 失敗時備援 |

### 報告內容
1. 市場情緒（多頭/空頭/震盪）+ 樂觀指數 1-10
2. 全球 6 大指數（台灣、美三大、日、港）
3. 宏觀指標（VIX、USD/TWD、布蘭特油、黃金）
4. 台灣觀察清單（8 支，含持有標記 ★）
5. 今日市場新聞 + 外資動向（Gemini Search 即時搜尋）
6. AI 一週展望 + 加權預估區間 + 主要風險

### 觀察股清單（可在 market_config.json 增刪）
| 代號 | 名稱 | 持有 |
|------|------|------|
| 2330.TW | 台積電 | — |
| 0050.TW | 元大台灣50 ETF | — |
| 006208.TW | 富邦台灣50 ETF | — |
| 009816.TW | 凱基優選ETF | ★ |
| 2610.TW | 華航 | ★ |
| 2303.TW | 聯電 | — |
| 2454.TW | 聯發科 | — |
| 2317.TW | 鴻海 | — |

### Gemini 設定（重要）
- **模型**：`gemini-2.5-flash`（付費 Key，`claude-workspace-495009` 專案）
- **必須設定** `thinkingConfig: {thinkingBudget: 0}`，否則思考型輸出截斷導致 JSON 解析失敗
- `gemini-2.0-flash` 在此付費專案有配額異常（free_tier limit: 0 但 paid tier 未生效），已改用 2.5-flash
- Notion 父頁面：`358f4149-a6aa-8088-9e6d-f5361d05cd12`（CRM 主頁）
- Finance OS 頁面（36af4149）已封存，不可當 parent

---

## Gmail 自動化腳本系統

### 本機 Crontab（僅剩 1 條）
| 腳本 | 排程 | 說明 |
|------|------|------|
| `cache_cleanup.sh` | `0 6 * * *` | Mac 快取清理，只能本機跑 |

> Gmail 清理、新聞摘要、IG 發文、Notion 月報均已移至 GitHub Actions（見上方總覽）

### Gmail 腳本認證方式（2026-05-24 更新）
兩支腳本均支援雙模式：
- **GitHub Actions**：讀環境變數 `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` / `GMAIL_REFRESH_TOKEN`
- **本機執行**：fallback 讀 `~/.config/gmail-cleanup-token.json`（gitignore，不進 repo）

### Gmail 產出（自動 commit 進 repo）
| 腳本 | 產出位置 |
|------|---------|
| `gmail_monthly_cleanup.py` | `財務/gmail_cleanup_log.txt`（追加）|
| `gmail_news_digest.py` | `今日新聞摘要.md`（每日覆寫）|

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

## Claude Code 工具設定（2026-05-24 建立）

### PostToolUse Hook — Python 自動格式化
每次編輯 `.py` 檔案後，自動執行 `black` 格式化。
- black 安裝位置：`/Users/lien/Library/Python/3.9/bin/black`（已加入 PATH）
- 設定於 `~/.claude/settings.json` → `hooks.PostToolUse`

### 自訂 Slash Commands（`~/.claude/commands/`）
| 指令 | 說明 |
|------|------|
| `/morning` | 每日早報（行事曆、Gmail、新聞摘要）|
| `/commit-push-pr` | 自動 add → AI生成commit訊息 → push → 開PR |
| `/verify` | 驗證當前腳本或任務是否正常運作 |
| `/simplify` | 審視並重構程式碼（不改功能，只改結構）|

### Git Worktrees（平行作業）
Boris Cherny 風格的多工設定，`worktree.sh` 管理：

| 快捷指令 | 目錄 | 說明 |
|---------|------|------|
| `cc` / `w1` | `Liam AI agent/`（main）| 主工作區 |
| `w2` | `Liam AI agent/work/2` | 平行任務 2 |
| `w3` | `Liam AI agent/work/3` | 平行任務 3 |
| `w4` | `Liam AI agent/work/4` | 平行任務 4 |
| `w5` | `Liam AI agent/work/5` | 平行任務 5 |

```bash
wt init    # 建立 work/2 ~ work/5
wt list    # 列出所有 worktree
wt clean   # 清除額外 worktree
```

### SessionStart Hooks（每次開啟 Claude Code 自動觸發）
| 腳本 | 說明 |
|------|------|
| `cache_cleanup.sh` | Mac 快取清理（背景執行）|
| `gmail_monthly_cleanup.py` | Gmail 清理（背景執行，GitHub Actions 為主、本機為備）|

---

---

## 海報圖片生成系統（2026-05-26 建立）

### 公益活動圓形徽章（4張）
| 項目 | 說明 |
|------|------|
| 腳本 | `/Users/lien/Downloads/gen_circles_hq.py`（或類似名稱） |
| 輸出 | `/Users/lien/Downloads/circle_1_愛心捐款_HQ.png` ～ `circle_4_物資捐贈_HQ.png` |
| 規格 | 2400×2400px，300dpi，透明背景圓形 |
| 設計 | 相片底圖 + 暗色覆蓋 + 愛心底紋 + 白色文字 + 白色邊框 |
| 四張內容 | 愛心捐款（含匯款帳號）、半日志工、惜食送餐、物資捐贈 |

### A1 表揚海報（惜食台灣行動協會）
| 項目 | 說明 |
|------|------|
| 腳本 | `/Users/lien/Downloads/gen_a1_list.py` |
| 輸出 | `/Users/lien/Downloads/海報/累積100萬以上捐款_名單.png` |
|      | `/Users/lien/Downloads/海報/累積50萬以上捐款_名單.png` |
| 規格 | 7016×9933px（A1），300dpi |
| 底圖 | 100萬：`/Users/lien/Desktop/未命名設計-1.jpg`（手持愛心）|
|      | 50萬：`/Users/lien/Desktop/191214-growth-1170x780.jpg`（嫩芽）|
| 版面結構 | 主標題「惜食台灣行動協會」→ 子標題（累積XXX萬以上捐款）→ 捐款名單 → 底部標語 |
| 名單邊界 | 對齊角落愛心圓心 x=700，名字左齊、金額右齊，col_gap=700px |
| 換行邏輯 | 名字超過 name_col_w（≈3499px）時自動找最平衡斷點（兩行都需 ≤ name_col_w）|
| 底部標語 | 裝飾線上方：「等一個便當，等一個疼惜」/ 下方：「疼惜食物。疼惜台灣」|
| 裝飾線 | x=1000 ～ x=6016（避開角落愛心），accent色粗線 + 白色細線 |

#### 100萬捐款名單
| 捐款人 | 金額 |
|--------|------|
| 僑威科技 | 2,500,000 |
| 簡承盈 | 1,700,000 |
| 楊奕蘭 | 1,500,000 |
| 謝德璋 | 1,200,000 |
| 簡清潭 | 1,100,000 |
| 鉅陞建設 | 1,000,000 |

#### 50萬捐款名單
| 捐款人 | 金額 |
|--------|------|
| 王光明 | 600,000 |
| 林子軒 | 600,000 |
| 邱正宏美學教育基金會 | 600,000 |
| 謝明達 | 500,000 |
| 國寶社會福利慈善事業基金會 | 500,000 |
| 海悅國際 | 500,000 |
| 白俊宇 | 全區磁磚捐贈 |

### 重新產出指令
```bash
python3 /Users/lien/Downloads/gen_a1_list.py
```

---

## HOC 服務點簽收表系統（2026-06-05 更新）

### 核心資訊
| 項目 | 說明 |
|------|------|
| 腳本 | `/Users/lien/Desktop/HOC團隊/sync_and_pdf.py` |
| 來源 Numbers | `/Users/lien/Desktop/HOC團隊/服務點物品清單彙整.numbers` |
| PDF 輸出 | `/Users/lien/Desktop/HOC團隊/服務點簽收表/` |
| 合併 PDF | `/Users/lien/Desktop/HOC團隊/服務點簽收表/服務點物品簽收表_全站點.pdf` |

### 執行方式
```bash
cd "/Users/lien/Desktop/HOC團隊" && python3 sync_and_pdf.py
```

### 簽收表欄位格式（2026-06-05 定稿）
- 表格：物品名稱 / 數量 / 備註 / **點組長確認**（□）
- 底部簽名欄：**點組長簽名：＿＿＿＿＿＿＿＿**（單一簽名欄）
- **已移除**：到位確認欄、交班確認欄、到位/交班簽名欄

### 站點數量
共 31 個站點，每站一頁，合併為一份 PDF

---

## 鑫酒藏 CRM 欄位規格（2026-06-05 更新）

### 客戶名單欄位（9欄）
`#` / `客戶姓名／公司` / `聯絡電話` / `地址` / `Email` / `VIP等級` / `備註` / `公司` / `統編`

### 檔案位置
| 檔案 | 路徑 |
|------|------|
| Numbers | `/Users/lien/Desktop/鉅鑫管理顧問/鑫酒藏/鑫酒藏販售清單.numbers` |
| Excel | `/Users/lien/Desktop/鉅鑫管理顧問/鑫酒藏/鑫酒藏販售清單.xlsx` |

### Notion DB ID
- 鑫酒藏客戶名單：`374f4149-a6aa-816f-ab2c-fcaad143f5b4`
- Notion 屬性：客戶姓名(title) / 聯絡電話 / Email / 地址 / VIP等級(select) / 備註 / 公司 / 統編

### 排版設計規範
- 標題列：深藍 `#1F4E79`、白色粗體 14pt
- Header 列：深藍底、白色粗體 10pt、全欄置中
- 資料列：淺藍 `#DEEAF1` / 白色交替
- 置中欄：#、電話、Email、VIP等級、統編

---

## Finn's Why — 兒童動畫頻道（2026-06-05 建立）

### 頻道定位
| 項目 | 說明 |
|------|------|
| 頻道名稱 | Finn's Why |
| 平台 | YouTube（主）+ YouTube Shorts |
| 風格 | 3D Pixar 等級，反 Cocomelon（慢節奏、不過度刺激）|
| 語言 | 英文（全球受眾）|
| 目標年齡 | 3–8 歲 |
| 製作工具 | Kling AI Pro（895/月，**15秒/shot**）|
| 發布頻率 | 每週一集（目標）|

### 角色設定
| 角色 | 說明 |
|------|------|
| Finn | 6歲小狐狸，橘毛白胸，琥珀眼，**永遠穿藍色T恤** |
| Luna | 媽媽，淺橘毛，**永遠穿軟綠圍裙** |
| Rex | 爸爸，橘毛，**永遠穿白色T恤** |
| Mimi | 4歲妹妹，黃色小花洋裝 |
| Oliver | 客座貓頭鷹爺爺，灰羽，金圓眼鏡，棕色背心 |

**角色一致性**：prompt 開頭加 `IMPORTANT: FINN is ALWAYS wearing light blue t-shirt`
**多角色警告**：同框超過 3 隻橘色狐狸容易複製角色，收尾 shot 只放 Finn + 客座角色即可

### 集數進度
| 集數 | 標題 | 狀態 |
|------|------|------|
| EP01 | Why Is the Sky Blue? 🦊☁️ | ⚠️ 3幕完成（44秒），待補完 |
| EP02 | Why Do Fireflies Glow? 🦊✨ | ✅ 影片完成（72秒，含旁白腳本），待配音+BGM |
| EP03 | Why Can Owls See in the Dark? 🦊🦉 | ✅ 影片完成（5 shots × 15秒），待後製 |

### 剪輯檔位置
| 集數 | 路徑 |
|------|------|
| EP02 | `/Users/lien/Desktop/Finn's Why-Sparks.mp4` |
| EP03 | Downloads 資料夾，檔名 `kling_20260610_VIDEO_IMPORTANT__*.mp4`（5個檔）|

### EP03 Shot 清單（2026-06-10 完成）
| Shot | 檔名關鍵字 | 內容 |
|------|-----------|------|
| 1 | `5666` | 黃昏開場 + Oliver 現身 |
| 2 | `6117` | Finn 發問 + 全像瞳孔圖 |
| 3 | `3D_Pixar_s_23` | 眼球內部視覺化 |
| 4 | `299` | Oliver 轉頭 + Finn 模仿笑點 |
| 5 | `515` | Finn + Oliver 看星空 + 銀河收尾 |

### 製作流程
1. 用 Kling AI Pro 逐 Shot 生成（每 shot **15 秒**）
2. Subject Reference 上傳角色參考圖鎖定外觀（每次開啟 Kling 需重新選取）
3. CapCut / iMovie 串接 + 轉場，剪至約 65-70 秒
4. 旁白腳本依實際剪輯畫面撰寫
5. 加入 AI 配音（ElevenLabs）+ 背景音樂（Suno/Udio）
6. 上傳 YouTube，附頻道描述 + 影片描述 + hashtags

### YouTube 頻道描述
```
Every night, a little fox named Finn looks at the world 
and asks one big question: WHY?

🦊 Finn's Why is a cozy, Pixar-style animated series 
for curious kids ages 3–8. Each episode follows Finn 
and his family as they explore one of nature's most 
fascinating questions — together.

No rush. No noise. Just wonder.

✨ New episodes every week
🌿 Science made simple, stories made warm
💛 Perfect for bedtime, family time, or anytime

Subscribe and never miss a new Why. 🔔
```

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
