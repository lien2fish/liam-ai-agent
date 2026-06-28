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
1. **Claude Sonnet 4.6** 生成知識 JSON（5～6句＋畫圖提示詞 `illustration_prompt`，三大類：海鮮/捕魚/漁船）。`generate_knowledge()` 以 Claude 為主、Gemini 為 fallback（Claude API 當機時自動降級，當天不開天窗）。模型常數 `CLAUDE_MODEL` 在腳本頂端，省錢可改 Haiku 4.5。**注意：Sonnet 4.6 不支援 assistant message prefill**（會回 invalid_request_error），改用單一 user message＋從回應擷取 `{...}` JSON 子字串
2. **HF FLUX.1-schnell** 生成圖文對應水彩插圖（吃 Claude 寫的 `illustration_prompt`）
3. **PIL** 動態排版合成（插圖大小＋字型大小依內容量自動調整）
4. **GitHub API** 上傳圖片 → raw.githubusercontent.com 公開 URL（repo 必須 public）
5. **Meta Graph API v19.0** 同時發送：
   - IG 限時動態（`{IG_ID}/media`，media_type=STORIES，帶 `cross_post_ids={FB_PAGE_ID}`）
   - FB 限時動態透過 `cross_post_ids` 跨發，**不使用** `photo_stories`（該端點持續回傳 unknown error）

### GitHub Secrets（7個）
`ANTHROPIC_API_KEY`（文案＋畫圖prompt，**需新增**）/ `GEMINI_KEY`（fallback）/ `HF_TOKEN` / `IG_TOKEN` / `IG_ID` / `FB_PAGE_TOKEN` / `FB_PAGE_ID`

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
| `ig_comment_reply.yml` | IG 留言自動回覆 | 每 5 分鐘（**實測常delay 1.5~4小時，GitHub高頻排程平台限制，非設定錯誤**） |
| `gmail_automation.yml` | Gmail 清理 + 新聞摘要 | 每天 08:00，自動 commit 報告 |
| `notion_monthly_report.yml` | Notion 月報 | 每月 1 日 08:00 |
| `market_daily.yml` | 每日股市全面分析報告 | 每天 **12:00**（台灣），自動 commit 報告 |
| `seafood_prices.yml` | 漁獲市場行情追蹤 | 每天 09:30 |
| `yt_comment_monitor.yml` | YouTube Shorts 留言通知 | 每天 08:30 |
| `policy_expiry_check.yml` | 產險保單到期提醒 | 每天 08:00，自動 commit 報告 |
| `repurchase_reminder.yml` | 三品牌客戶回購提醒 | 每天 09:00，超60天未回購則 Email，自動 commit 報告 |
| `yt_auto_post.yml` | YouTube 自動 Shorts（療癒系動畫，無人臉） | 每天 10:00，AI生影片自動上傳 |
| `claude_task_runner.yml` | Claude 任務讀取器（列出GitHub Issue中標記`claude-task,pending`的待辦） | 手動觸發（workflow_dispatch） |

### GitHub Secrets 總覽
| Secret | 用途 |
|--------|------|
| `ANTHROPIC_API_KEY` | Claude API Key（IG 發文文案＋畫圖 prompt 生成，Sonnet 4.6）。2026-06-26 新增，Console 已儲值（預付制、非訂閱）。模型常數 `CLAUDE_MODEL` 在 `instagram/generate_post.py` 頂端 |
| `GEMINI_KEY` | Gemini AI Key（claude-workspace-495009，**2.5-flash** 模型）。**注意：實為免費額度，未開通Cloud Billing**（2026-06-23實測證實，`2.5-flash`限20次/天、`2.5-pro`免費額度0），所有共用此Key的自動化共用同一日額度池，理論上會互搶額度 |
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
- **模型**：`gemini-2.5-flash`（`claude-workspace-495009` 專案，**實為免費額度，非付費**——2026-06-23實測證實）
- **必須設定** `thinkingConfig: {thinkingBudget: 0}`，否則思考型輸出截斷導致 JSON 解析失敗
- `gemini-2.0-flash` 在此專案有配額異常（free_tier limit: 0 但 paid tier 未生效），已改用 2.5-flash
- `gemini-2.5-flash` 免費額度上限20次/天，`gemini-2.5-pro` 免費額度直接0，市場日報與其他自動化（IG留言回覆等）共用同一額度池
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

## 會議錄音轉會議記錄系統（2026-06-23 建立）

### 核心資訊
| 項目 | 說明 |
|------|------|
| 腳本 | `meetings/audio_to_minutes.py` |
| 用法 | `python3 meetings/audio_to_minutes.py "<音檔路徑>" "<會議名稱>"` |
| 輸出 | `~/Desktop/{會議名稱}_會議記錄.pdf` ＋ `~/Desktop/{會議名稱}_會議記錄_簡化版.pdf` |
| 排程 | 手動執行，非自動化（依需求隨時對單一錄音檔跑） |

### 流程
1. **上傳音檔**：用 Gemini File API resumable upload（音檔通常 >20MB，無法用 inline base64），上傳後 poll `state` 直到 `ACTIVE`
2. **轉錄＋結構化**：呼叫 `gemini-2.5-flash` 的 `generateContent`，傳入 `file_data`（mime_type + file_uri），`thinkingConfig.thinkingBudget: 0`，`responseMimeType: application/json`，輸出結構化 JSON：
   `meeting_title / meeting_date / agenda_items[{topic, discussion_summary, decisions}] / action_items[{task, owner, due}] / overall_summary`（不含 attendees，使用者要求拿掉與會人員欄位）
3. **簡化版**：第二次呼叫 Gemini（純文字，不需重傳音檔），把 `discussion_summary` 濃縮成 `key_points`（3-5條精簡要點，保留所有數字/人名/決議，只精簡敘述文字）
4. **排版 PDF**：用 reportlab 輸出**兩份 PDF**到桌面：
   - `{會議名稱}_會議記錄.pdf`（詳細版，完整討論段落，正式記錄保存用）
   - `{會議名稱}_會議記錄_簡化版.pdf`（簡化版，條列要點，快速瀏覽用）
5. **人名校對**：語音辨識常把人名聽成同音字，產出後務必請使用者校對一次人名再定案。**每份錄音的校對結果只適用該份**，不要把上一份的人名/職稱修正規則直接套用到下一份新錄音（職稱縮寫如扶輪社PG/PP/DG/DK各有不同意義，需使用者逐份確認）

### 重要技術細節
- **字型地雷**：`PingFang.ttc` 在 reportlab 會直接報錯（`postscript outlines are not supported`，因為是 CFF outline 格式）。改用 `/System/Library/Fonts/STHeiti Light.ttc`（index 0，正文）+ `STHeiti Medium.ttc`（index 0，標題），這兩個是 TrueType outline 格式，reportlab 可正常載入
- **GEMINI_KEY 本機快取**：已存放於 `config/.gemini_key`（已 gitignore），本機腳本可直接讀取，不需每次都去 Google Cloud Console 複製
- **GEMINI_KEY 額度地雷**（2026-06-23實測）：這組 Key **沒有開通 Cloud Billing，仍受免費額度限制**——`gemini-2.5-flash` 限20次/天（超過會429 RESOURCE_EXHAUSTED，重試無效需等隔天重置，重置時間約UTC 00:00＝台北15:00）；`gemini-2.5-pro` 免費額度直接0token，完全不可用；`gemini-2.5-flash-lite`額度較寬鬆但對長音檔（60分鐘以上）容易卡進repetition loop或內容變空泛模糊，**避免用於正式會議記錄**。503 UNAVAILABLE（伺服器過載）是暫時性的，重試幾次（間隔10-15秒）通常會恢復，跟429額度問題要分開判斷
- **本機 Whisper 備案**：已安裝 `openai-whisper`（`pip3 install openai-whisper`，含torch CPU版）。這台Mac是Intel x86_64無GPU，65分鐘音檔預估跑1-2小時以上，平時優先用 Gemini API，只有額度/過載卡住才考慮本機Whisper

---

## 鉅鑫管理顧問公司資料與報價單系統（2026-06-23 建立）

### 公司基本資料（用於報價單/發票/合約等正式文件）
| 項目 | 內容 |
|------|------|
| 公司全名 | 鉅鑫管理顧問有限公司 |
| 地址 | 台北市內湖區南京東路六段461號1樓 |
| 電話 | 02-26585560 |
| 傳真 | 02-26585280 |
| 統一編號 | 50877146 |
| 銀行帳戶 | 彰化銀行(009) 南港科學園區分行，戶名：鉅鑫管理顧問有限公司，帳號：5383-01-056001-00 |

### 報價單範本
| 項目 | 說明 |
|------|------|
| 檔案 | `/Users/lien/Desktop/鉅鑫管理顧問/報價單範本.xlsx` |
| 用法 | 每次開新報價單先複製這份檔案，填入客戶資訊（B4客戶/B5聯絡人/G5報價日期/G6報價單號/G7統編）與品項（C9:I24區），合計/營業稅/總計欄位已設公式自動計算 |
| 來源 | 沿用「三冠彩印事業有限公司」報價單版面格式（合併單元格/樣式），替換為鉅鑫管理顧問公司頭 |

---

## 產險保單到期提醒系統（2026-06-22 建立）

### 核心資訊
| 項目 | 說明 |
|------|------|
| 資料來源 | `insurance/active_policies.json`（105筆磊山保經有效保單，已去重複） |
| 腳本 | `insurance/policy_expiry_check.py`（讀取保單→算下次續保日→14天內到期則寄信+寫報告）/ `insurance/process_policies.py`（資料處理）/ `insurance/policy_data.py`（原始資料，含身分證號等個資，**gitignore僅本機保留**） |
| 排程 | GitHub Actions `policy_expiry_check.yml`，每天08:00台灣時間 |
| 通知 | `GMAIL_APP_PASSWORD` smtplib寄信（與OAuth系統無關不會過期） |
| 報告 | `reports/產險到期提醒_YYYY-MM-DD.md`，自動commit進repo |
| 提醒窗口 | `REMINDER_WINDOW_DAYS = 14`（續保日落在未來14天內才提醒） |

---

## 名片數位化系統（2026-06-25 建立）

### 核心資訊
| 項目 | 說明 |
|------|------|
| 名片照片來源 | `/Users/lien/Desktop/鉅鑫管理顧問/名片資料`（手機拍照後AirDrop/iCloud同步） |
| Notion：扶輪社名片名單 | `38af4149-a6aa-8136-a515-e9d8a468a3bb`（姓名/扶輪社名稱/扶輪職位/公司商號/職稱/聯絡電話/Email/地址/備註/取得日期） |
| Notion：公司行號名片名單 | `38af4149-a6aa-81b8-87e9-c94d4dd8d809`（姓名/公司商號/職稱/聯絡電話/Email/地址/統編/備註/取得日期） |
| 與既有名單關係 | 完全獨立於鑫海產/鑫酒藏/磊山保經客戶名單，都建在CRM主頁面（`358f4149-a6aa-8088-9e6d-f5361d05cd12`）下 |

### 處理流程
1. HEIC用 `sips -s format jpeg` 轉jpg（Read工具不支援HEIC直讀）
2. 逐張用Read工具讀圖辨識文字（姓名/公司/職稱/電話/Email/地址）
3. 分類依據：卡片有Rotary標誌/扶輪社名稱 → 扶輪社名單；純公司行號名片 → 公司行號名單
4. **同一人有兩張卡**（扶輪社卡+一般公司卡）時合併成一筆，優先放扶輪社名單並把公司資訊填進公司/商號欄，不重複建檔
5. 寫入用Python urllib直接呼叫Notion API（`POST /v1/pages`，`Notion-Version: 2022-06-28`）

### 重要技術細節
- **建立新Notion資料庫不可用notion-mcp的`API-create-a-data-source`**：新版API（2025-09-03+）已不支援這endpoint建資料庫，會回400要求改用「Create Database API」。改用Python直接呼叫舊版endpoint `POST https://api.notion.com/v1/databases`（帶 `Notion-Version: 2022-06-28`），parent用`{"type":"page_id","page_id":...}`即可成功
- Token讀取：`~/.config/notion_token`

---

## 弓箭傳說風格小遊戲（個人興趣專案，2026-06-25 建立）

### 核心資訊
| 項目 | 說明 |
|------|------|
| 專案位置 | `/Users/lien/Downloads/archer-roguelite/`（獨立於本repo，跟事業自動化系統分開） |
| 技術 | Phaser **3.90**（刻意pin在3.x，4.x API未知不貿然用）+ Vite，純前端瀏覽器遊戲 |
| 啟動 | `cd /Users/lien/Downloads/archer-roguelite && npm run dev`，開Safari到 `http://localhost:5173/` |
| 玩法 | 俯視角自動射箭roguelite（像弓箭傳說Archero）：WASD移動閃避，自動朝最近敵人射箭，清房後3選1升級卡，每5房一個Boss房（有遠程彈幕攻擊） |
| 美術 | MVP階段純幾何圖形佔位（玩家=藍三角、敵人=紅圓、Boss=深紅大圓+金邊），先驗證玩法手感再決定要不要投資正式美術 |
| 現況 | MVP已完成並通過程式化驗證（房間/Boss資料、傷害判定、死亡流程皆正確），**待使用者實際playtest回饋手感**，再依回饋調整數值平衡 |

### 重要技術細節
- `src/main.js` 把 `window.game` 暴露出來方便用瀏覽器Console debug
- 測試這類canvas/Phaser遊戲時，Playwright只能做螢幕截圖分析（依瀏覽器規則不能模擬點擊），若要驗證遊戲內部邏輯（清房/升級/死亡流程），改用 `browser_evaluate` 直接呼叫scene上的方法（如 `scene.selectUpgrade(0)`）做診斷，而不是模擬使用者點擊
- **地雷**：透過Playwright `browser_evaluate` 呼叫 Phaser 的 `scene.scene.restart()` 會讓headless頁面當掉（crash到`about:blank`，`window.game`整個消失）。要測試重來流程時改用重新 `browser_navigate` 到同個網址即可，不要呼叫 `restart()`

---

## 網站架構調整可行性評估（2026-06-25 評估）

### savefood.org.tw（惜食台灣行動協會）
| 項目 | 說明 |
|------|------|
| 平台 | **Wix**（封閉系統，generator確認），無法用程式碼/git直接調整 |
| 結論 | 若要讓我用程式碼處理，只能脫離Wix另建新站（內容/LOGO可沿用現有Wix站爬下來的資料），再把網域DNS指向新主機（建議GitHub Pages） |
| 現況 | **暫停中**，使用者去確認 savefood.org.tw 的DNS管理權限，確認後才會開始動工；不需要額外提供文案/圖片，可直接用現有Wix內容當底 |
| 已發現的現有問題 | 大量未清理的「副本-」重複頁面、FAQ頁還是Wix預設範本內容、捐款芳名錄按年份分散成多頁(108~114) |

### gs-group.com.tw（鉅鑫管理顧問官網）
| 項目 | 說明 |
|------|------|
| 平台 | **WordPress + Elementor**（自架開放系統，非Wix），有真實檔案+MySQL資料庫 |
| 結論 | 若拿到 **wp-admin後台帳密 + 主機FTP/SFTP/SSH權限**，可以直接用程式碼/git處理主題程式碼、客製功能、SEO、效能優化；純版面排列（Elementor拖拉部分）仍需後台操作或我指導 |
| 子頁面 | `/have-a-seat`匠鑫私廚、`/tea`鑫茶坊、`/wine`鑫酒藏、`/seafood`鑫海產、`/education`鉅鑫教育、`/operation`鉅鑫營運處 |

---

## Mac 效能優化紀錄（2026-06-25 完成）

### 硬體限制
2015款 MacBook Air，Intel Core i5-5250U 雙核 1.6GHz、**8GB RAM**，macOS 12.7.6。日常已會用到swap，單一Claude Code process約吃1.3GB RSS。**不建議同時開多個worktree的Claude Code session**（w2~w5平行作業功能存在，但容易吃滿記憶體變超慢）。

### 換機決策（2026-06-26 定案）
已評估比較「本機 / 13" Air M5 / 14" Pro M5」，**結論選 13" MacBook Air M5**：
| 項目 | 內容 |
|------|------|
| 配置 | M5（10核CPU／10核GPU）／**24GB RAM**／**512GB SSD** |
| 官網價 | **NT$49,900**（apple.com/tw 實價，2026-06 M5 Air 已上市） |
| 付款 | 0% 分12期＝月付 NT$4,158；或攤3年每天約NT$46 |
| 不選Pro原因 | Whisper轉錄/大圖輸出是**偶發非常態**，Pro主動散熱優勢用不到，價差約NT$1.5-2萬不值得 |
| 關鍵規格邏輯 | 痛點是8GB RAM不足→**24GB為必選**；24GB只能配10核GPU版（綁定），等於白賺25%繪圖效能給偶發剪片用 |

> 尚未購買，待使用者決定下單。新機到手後需協助搬移環境：Claude Code、Python、MCP、git 設定。

### 已完成優化項目
| 項目 | 內容 |
|------|------|
| `cache_cleanup.sh` 修正 | 原本會清掉`~/Library/Caches/ms-playwright`（這其實是Playwright瀏覽器二進位檔安裝位置，不是快取），且此腳本每天06:00 cron + 每次開Claude Code的SessionStart hook都會跑，等於常態誤刪導致Playwright MCP要重新下載300-500MB。已移除該段邏輯 |
| 登入項目清理 | 移除 BuhoCleanerMenu、NeatDownloadManager、EaseUS Data Recovery Wizard Tray、Typeless（原本Typeless有兩個重複項目，已用`delete every login item whose name is "Typeless"`一次清除），目前登入項目數＝0 |
| LaunchAgents 清理 | trash 掉 `com.mackeeper.MacKeeper-*.plist`（3個）。`org.virtualbox.startup.plist`（556K root擁有殘留檔）需sudo才能清，安全設定封鎖sudo，**已知殘留不處理**，影響極小 |
| Dock 啟動動畫關閉 | `defaults write com.apple.dock launchanim -bool false` + `killall Dock` |
| Reduce Motion / Reduce Transparency | 系統設定 > 輔助使用 > 顯示器，手動開啟（這兩個TCC保護的domain無法從Bash寫入，唯一需使用者手動操作的項目，已完成） |

**Why**：硬體偏弱＋背景軟體（MacKeeper等）＋誤殺Playwright二進位檔，持續拖累原本就吃緊的8GB RAM。
**之後若使用者抱怨變慢**：先查是否又裝了新背景開機軟體，或Playwright快取又被誤清；避免建議同時開多個worktree session。

---

## 個人資產負債表更新系統（2026-06-26 更新）

### 核心資訊
| 項目 | 說明 |
|------|------|
| 腳本 | `finance/update_balance_sheet.py`（讀取Notion 3個DB→重建「💼 個人資產負債表」頁面）|
| 設定 | `finance/finance_config.json`（收入、固定支出、Notion DB/頁面ID；已進版控）|
| 執行 | `python3 finance/update_balance_sheet.py`（每次重建整頁，安全可重複跑）|
| Notion頁面 | 個人資產負債表 `38af4149-a6aa-8178-9d8f-fd8a47091a73` |

### Notion 資料庫（在 Personal Finance OS 主頁 `38af4149-a6aa-81d3-9480-cfb0944c8824` 下）
| DB | ID | 維護方式 |
|----|----|---------|
| 資產 Assets | `38af4149-a6aa-81f6-bb8b-e938ad9825e4` | 使用者直接在Notion維護，腳本只讀 |
| 負債 Liabilities | `38af4149-a6aa-8101-9faf-f4c57a8fe3f7` | 同上 |
| 訂閱費用管理 Subs | `38af4149-a6aa-81bb-aabb-d6b3a9a788e2` | 同上（狀態=啟用才計入月支出）|

### 更新流程（資產/負債有變動時）
1. **資產數字變動**用 Python REST（`Notion-Version: 2022-06-28`）直接 PATCH/POST/archive 對應 page；新版MCP的query-data-source吃data_source_id會404，改用舊版 `POST /v1/databases/{db}/query` 端點
2. Assets DB 欄位：`項目名稱 / Asset Name`(title)、`類別 / Category`(select：股權/保險/存款/股票/其他)、`當前金額 / Current Value`(number)、`成本 / Cost Basis`(number)
3. **收入/固定支出變動**改 `finance_config.json`（`income` / `fixed_expenses` 區塊）
4. 改完一律 `python3 finance/update_balance_sheet.py` 重建頁面，再把finance變動 commit+push（push前先 stash 未暫存的自動報告→pull --rebase→push→stash pop）
5. 投資概況區塊只統計類別屬 `股票/黃金/ETF/Stock/Gold` 的資產；存款類（含黃金存摺、實體金條）不列入投資損益

> 完整財務數字（資產明細/收支/指標）見 memory `finance_personal.md`，不在此重複。

---

## 全品牌統一 CRM ＋回購提醒系統（2026-06-26 建立）

### 核心資訊
| 項目 | 說明 |
|------|------|
| 整併腳本 | `crm_unified/build_unified_crm.py`（讀酒藏/海產4個舊DB→建2個跨品牌總表→匯入，可重複跑會沿用既有總表） |
| 回購腳本 | `crm_unified/repurchase_reminder.py`（掃描客戶總表→超門檻未回購→Email） |
| 設定 | `crm_unified/config.json`（兩個總表DB ID，**已進版控**，workflow 需讀） |
| 排程 | `.github/workflows/repurchase_reminder.yml`，每天09:00台灣，超60天未回購則寄信＋commit報告 |
| 報告 | `reports/回購提醒_YYYY-MM-DD.md` |

### 兩個跨品牌 Notion 資料庫（建在 CRM 主頁 `358f4149-a6aa-8088-9e6d-f5361d05cd12` 下）
| DB | ID | 欄位 |
|----|----|------|
| 🗂️ 全品牌客戶總表 | `38bf4149-a6aa-816e-9850-f3dfbbb925ec` | 客戶姓名/品牌(select:鑫酒藏/鑫海產/鑫茶坊)/聯絡電話/Email/地址/會員等級/偏好品項/累計消費/最後購買日/公司/統編/備註 |
| 🧾 全品牌銷售紀錄 | `38bf4149-a6aa-81db-9b89-c47410857a2c` | 訂單編號/品牌/出貨日期/客戶名稱/品項/數量/金額/成本/毛利/付款方式/備註 |

### 資料來源（整併自既有4個獨立DB，保留不刪）
- 🍷鑫酒藏 客戶`374f4149-a6aa-816f-ab2c-fcaad143f5b4`／銷售`374f4149-a6aa-81ec-8aef-de88095d8b6b`
- 🐟鑫海產 客戶`374f4149-a6aa-8135-b9e4-dbb0cc2c2e0d`／銷售`374f4149-a6aa-8102-baf5-ffa959227731`
- 🍵鑫茶坊：尚無獨立 Notion DB／無歷史資料，已列為品牌選項；經 `add_order.py` 新增的茶坊訂單會自動進統一總表

### 新訂單自動同步（2026-06-26 接通）
`notion_crm/add_order.py` 每筆新訂單現在同步 **4 個目標**：① 本機 Numbers ② 舊品牌 Notion 銷售DB ③ 舊品牌 Notion 客戶DB累計消費 ④ **統一總表**（銷售紀錄新增＋客戶「最後購買日」更新/新增）。第④步確保回購提醒讀到的「最後購買日」永遠是最新，不會誤判。

### 回購邏輯
- 門檻天數 `REPURCHASE_DAYS`（預設60，workflow env 可調）
- 「最後購買日」由銷售紀錄每客戶取最新出貨日算出
- 待回購＝曾購買且距今>門檻；從未消費（無最後購買日）另列參考區不算逾期
- 認證沿用 `NOTION_TOKEN`＋`GMAIL_APP_PASSWORD`（與保單提醒同套，無到期問題）

## YouTube 自動 Shorts 頻道系統（2026-06-28 建立）

### 定位
全新**無人臉 AI 頻道**，主題 **療癒系（Healing/Cozy）**（2026-06-28 從歷史謎團改方向）：柔和粉彩動畫風、溫柔英文女聲（Aria，語速-8%）、繁中字幕、慢運鏡、療癒短語/微故事。架構複用 IG 發文系統。
- 風格參數在 `build_video.py`：`VOICE`(en-US-AriaNeural)、`RATE`(-8%)、`gen_image` 畫風(soft pastel storybook/Ghibli)、Ken Burns 放慢(0.0004→1.10)。要換回戲劇/其他風只改這幾處＋`generate_script` 的 prompt
- **固定吉祥物結尾**：`MASCOT_SCENE`＝Mochi(奶油色小貓+額頭月牙印)，每支影片結尾自動 append 一張面向觀眾「說話」的吉祥物圖（靜態圖+輕推鏡，非真對嘴；真lip-sync需Kling等工具無法全自動）
- **空靈聲線**：最終合成對旁白加 `aecho` 殘響+highpass
- **BGM**：`youtube_auto/bgm.mp3`（ffmpeg 生成的療癒環境墊音，可換無版權音樂，或用 `YT_BGM` 指定），最終以 `amix` 低音量(0.16)混入；輸出音訊 44.1kHz 立體聲
- **長度＝1～3 分鐘一般影片**（2026-06-28 從 Shorts 改長）：`generate_script` prompt 要 14-18 句、8-12 場景、200-280字；`max_tokens` 升到 3000；`make_and_upload` 已移除強制 `#shorts`。要改長度就調 prompt 的句數/場景數。圖片數越多 FLUX 生成越久（本機 Intel Mac 約 4 分鐘/支，雲端 runner 較快、在 20 分鐘上限內）

### 模組 `youtube_auto/`
| 檔案 | 職責 |
|------|------|
| `generate_script.py` | Claude Sonnet 4.6 生英文腳本 JSON（title/narration/scenes/description/tags/topic），主題去重 `recent_topics.json` |
| `build_video.py` | FLUX生4-6張電影感插圖 ＋ **edge-tts**英文配音 ＋ ffmpeg Ken Burns ＋ 燒錄字幕 → 1080×1920 MP4 |
| `upload.py` | YouTube Data API v3 resumable 上傳（OAuth refresh token，純 urllib） |
| `make_and_upload.py` | 每日進入點：生腳本→產影片→上傳→記錄去重 |
| `oauth_setup.py` | 一次性取得 refresh token（手動授權流程，同 Gmail） |
| `SETUP.md` | 一次性人工設定步驟（建頻道/OAuth/Secrets） |

### 排程
`.github/workflows/yt_auto_post.yml`，每天 10:00 台灣（UTC 02:00）。`YT_PRIVACY` 預設 **private**，驗證無誤後改 public。

### 需新增 GitHub Secrets（共用 ANTHROPIC_API_KEY / HF_TOKEN）
`YT_OAUTH_CLIENT_ID` / `YT_OAUTH_CLIENT_SECRET` / `YT_OAUTH_REFRESH_TOKEN`（scope: `youtube.upload`）

### 重要技術細節
- **字幕為繁體中文、旁白為英文**（2026-06-28 使用者指定中文字幕；標題/描述維持英文利全球 SEO）
- **逐句配音對齊**：`generate_script` 讓 Claude 同時產 `sentences:[{en,zh}]`；`build_video.synth_sentences` 逐句 edge-tts 配音→量測時長→串接，取得每句精確時間，中文字幕(zh)據此對齊（比 edge-tts 的 SentenceBoundary 更穩，edge-tts 7.2.8 預設只回句邊界非字邊界）
- **CJK 字型**：`CJK_FONT` mac 用 `Heiti TC`、Linux 用 `Noto Sans CJK TC`；workflow 需 `apt install fonts-noto-cjk`
- CJK 字幕依字數切（每段11字）、拉丁依詞數切（每段5詞）
- 本機 evermeet 版 ffmpeg **無 ffprobe**：`get_duration` 改用 `ffmpeg -i` 解析 Duration（雲端 apt 版有 ffprobe 不受影響）
- **OAuth 同意畫面須發布 Production**，否則 refresh token 每 7 天失效（同 Gmail OAuth 雷）
- 憑證 `config/youtube_client.json`、`config/youtube_oauth.json` 已被 config/ gitignore 保護
- 本機已驗證：完整產出 24s 帶字幕 MP4（FLUX插圖+配音+Ken Burns 皆正常）
- **一次性人工步驟**（無法自動化）：建 YouTube 頻道、Google Cloud OAuth、首次授權，見 `youtube_auto/SETUP.md`
- 變現非保證：YPP 門檻 1,000 訂閱 + 90天1,000萬 Shorts 觀看，且需原創價值避開低品質AI內容政策

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
