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

---

## 技能索引（Skills）

**專案細節與地雷全部搬進 skills，本檔只留通則。** 遇到下列工作時先載入對應 skill，不要憑印象動手：

| Skill | 什麼時候載入 |
|-------|-------------|
| **`ops-rescue`** | **自動化掛了**——任務沒跑、報告沒出、提醒沒收到。含症狀對照、共用金鑰連鎖失效、手機能不能修 |
| `reel` | 剪短影音／長影音（連老闆海鮮、樂器演奏、甜點頻道長片） |
| `ig-fb-auto` | IG+FB 發文、IG 留言回覆、限動預告、IG Token 更新 |
| `youtube-lien` | 連老闆／甜點頻道上傳排程、標題與 hashtag、Shorts 留言通知 |
| `youtube-auto` | The Unknown Hour 自動影片、Finn's Why 動畫 |
| `print-cmyk` | 惜食防水布、歷史發展牆、乾貨牆、捐款卡等大圖送印 |
| `poster` | 鮮味聚海報、A1 表揚海報、圓形徽章 |
| `vector-ai` | 點陣圖轉向量 .ai、六邊形理監事牌換姓名 |
| `crm-order` | 訂單建檔、客戶資料、回購提醒、名片數位化 |
| `insurance` | 產險保單到期、壽險拜訪、生日提醒 |
| `market-finance` | 股市日報、個人資產負債表 |
| `gmail-ops` | Gmail 清理／新聞摘要腳本、OAuth 重新授權 |
| `meeting-minutes` | 會議錄音轉會議記錄 PDF |
| `company-docs` | 報價單、發票、合約等正式文件（公司統編／帳戶） |

- **新增 Skill 的判準：連續三次在不同對話講同一件事，就寫成 Skill。**
- 封存專案與歷史紀錄見 `docs/archive/封存專案與歷史紀錄.md`（不主動提及）。

---

## 社群平台自動化總覽

| 平台 | 類型 | 排程 | 狀態 |
|------|------|------|------|
| IG + FB | 每日發文 | 每天 08:00 | ✅ 運行中 |
| IG | 留言自動回覆 | 每 5 分鐘 | ✅ 運行中 |
| YouTube | Shorts 留言通知（不回覆） | 每天 08:30 | ✅ 運行中 |
| YouTube | 手動上傳＋排定發布（連老闆／泥馬的真心話） | 手動觸發 | ✅ 見下方 |
| TikTok | — | — | 手動，不自動化 |

---

## GitHub Actions 自動化總覽（2026-06-02 更新）

所有雲端自動化任務均透過 GitHub Actions 執行，不依賴本機開機。

| Workflow 檔案 | 任務 | 排程 |
|--------------|------|------|
| `daily_post.yml` | IG+FB 每日發文 | 每天 08:00 |
| `ig_comment_reply.yml` | IG 留言自動回覆 | 每 5 分鐘（**實測常delay 1.5~4小時，GitHub高頻排程平台限制，非設定錯誤**） |
| `ig_story_teaser.yml` | IG 限動 Reels 預告（從已發布 Reels 剪 3 秒＋「Reels完整版～」，30 天不重複） | 每天 18:05（接 Reels 18:00） |
| `gmail_automation.yml` | Gmail 清理 + 新聞摘要 | 每天 08:00，自動 commit 報告 |
| `notion_monthly_report.yml` | Notion 月報 | 每月 1 日 08:00（**2026-07-02 修**：CRM 於 06-26 整併後，`notion_crm/monthly_report.py` 原引用不存在的 `DB["sales"]` 且欄位名對不上，已改讀「全品牌銷售紀錄」統一DB `38bf4149-a6aa-81db-9b89-c47410857a2c`，欄位＝金額/出貨日期/客戶名稱）|
| `market_daily.yml` | 每日股市全面分析報告 | 每天 **12:00**（台灣），自動 commit 報告 |
| `seafood_prices.yml` | 漁獲市場行情追蹤 | 每天 09:30 |
| `yt_comment_monitor.yml` | YouTube Shorts 留言通知 | 每天 08:30 |
| `policy_expiry_check.yml` | 產險保單到期提醒 | 每天 08:00，自動 commit 報告 |
| `life_visit_reminder.yml` | 壽險客戶固定拜訪提醒 | 每天 08:40，讀Notion算下次拜訪日，本週到期Email（**無commit，客戶個資只走Email**）|
| `birthday_reminder.yml` | 壽險客戶生日提醒 | 每天 08:05，未來7天內生日則Email（含歲數，無commit）|
| `repurchase_reminder.yml` | 三品牌客戶回購提醒 | 每天 09:00，超60天未回購則 Email，自動 commit 報告 |
| `weekly_revenue_sprint.yml` | 營收衝刺週報（本週壽險該接觸名單＋話術：A組未來14天生日切入、B組壽產保單健檢每週輪替6位） | 每週一 08:00，Email（**無commit，客戶個資只走Email**）|
| `yt_auto_post.yml` | YouTube 自動影片（宇宙/古文明未解之謎，無人臉，頻道=The Unknown Hour；**Shorts 週二/五、長片週日，約隔兩天一支**） | 每天 10:00 檢查，發片日才製作上傳，**排程當天 18:00 自動轉公開** |
| `yt_channel_report.yml` | The Unknown Hour 頻道每日表現日報（觀看/讚/留言+新留言Email） | 每天 08:20，用YT_API_KEY讀公開數據，自動commit報告 |
| `claude_task_runner.yml` | Claude 任務讀取器（列出GitHub Issue中標記`claude-task,pending`的待辦） | 手動觸發（workflow_dispatch） |
| `rotary_birthday_reminder.yml` | 中城網路扶輪社社友生日提醒（剛好前14天Email一次；資料=私人repo `liam-workspace/rotary/中城網路社友通訊錄.json` 71位，用`WORKSPACE_PAT` checkout，**個資不進公開repo、無commit**） | 每天 08:10 |
| `weekly_review.yml` | **AI 工作週報**（上週做了什麼＋可精進＋自動化健康＋下期建議，Email 附正式 PDF）。資料＝私人repo `daily/` 工作日誌＋公開repo git log＋Actions runs API＋`TODO.md` diff；**報告只進私人repo `liam-workspace/reviews/`，不進公開repo** | 每週一 08:50（錯開 08:00 營收週報）|

### GitHub Secrets 總覽
| Secret | 用途 |
|--------|------|
| `ANTHROPIC_API_KEY` | Claude API Key。2026-06-26 新增，Console 已儲值（**預付制、非訂閱**，與 Claude Code 訂閱是兩筆帳）。四處在用：IG 發文文案＋畫圖 prompt（`instagram/generate_post.py`，**Sonnet 5**）、YouTube 影片腳本（`youtube_auto/generate_script.py`，**Sonnet 5**）、AI 工作週報（`scripts/weekly_review.py`，**Sonnet 5**，每週一次約 6K token）、Telegram 手機助理（Haiku 4.5）。模型常數 `CLAUDE_MODEL` 在各腳本頂端。⚠️ **Sonnet 5 起 `content[0]` 可能是 thinking block**，解析回應一律遍歷找 `type == "text"` |
| `GEMINI_KEY` | Gemini AI Key（claude-workspace-495009，**2.5-flash** 模型）。**注意：實為免費額度，未開通Cloud Billing**（2026-06-23實測證實，`2.5-flash`限20次/天、`2.5-pro`免費額度0），所有共用此Key的自動化共用同一日額度池，理論上會互搶額度 |
| `OPENAI_API_KEY` | OpenAI 生圖（IG 插圖＋YouTube 場景圖），`gpt-image-1-mini`。2026-08-06 設定，預付制需儲值。本機備份於 `config/.openai_key` |
| `HF_TOKEN` | （已停用）Hugging Face FLUX→Pollinations→OpenAI，兩任前身皆因免費額度取消而汰換 |
| `IG_TOKEN` | Instagram Graph API（到期 2026-07-16）|
| `IG_ID` | Instagram 帳號 ID |
| `FB_PAGE_TOKEN` | Facebook Page Token（永不過期）|
| `FB_PAGE_ID` | Facebook Page ID |
| `GMAIL_CLIENT_ID` | Gmail OAuth |
| `GMAIL_CLIENT_SECRET` | Gmail OAuth |
| `GMAIL_REFRESH_TOKEN` | Gmail OAuth |
| `NOTION_TOKEN` | Notion API Token |
| `YT_API_KEY` | YouTube Data API v3 金鑰（無到期問題；連老闆留言通知＋The Unknown Hour 頻道日報共用）|
| `YT_CHANNEL_ID` | YouTube 頻道 ID（連老闆-產地到餐桌）|
| `YT_OAUTH_CLIENT_ID` / `YT_OAUTH_CLIENT_SECRET` / `YT_OAUTH_REFRESH_TOKEN` | The Unknown Hour 自動上傳 OAuth（scope youtube.upload，同意畫面已發Production不過期）2026-06-29設 |
| `GMAIL_APP_PASSWORD` | Gmail App 密碼，供 YouTube 留言通知＋頻道日報＋回購提醒寄信用 |
| `WORKSPACE_PAT` | 存取私人 repo `liam-workspace` 的 PAT（＝本機 liam-workspace remote 內同一組，永不過期），供扶輪社生日提醒 checkout 個資 |

---

## Telegram 手機助理（2026-08-19 建立）

人在外面時的輕量入口，Cloudflare Worker + Telegram Webhook + Claude API。
**部署步驟、成本、能做／不能做的界線全在 `telegram_bot/README.md`。**

| 項目 | 說明 |
|------|------|
| 程式 | `telegram_bot/worker.js`（單檔，raw fetch，無 npm 依賴，同 `travel_worker` 風格）|
| 推播 | `telegram_bot/notify.py` — 任何腳本 `from telegram_bot.notify import notify` 即可用；**未設環境變數時靜默跳過**，不會弄壞既有流程 |
| 能做 | 記待辦、口述存知識庫（含語音轉文字）、查客戶／銷售／庫存、接收自動化推播 |
| **兩種模式** | **斜線指令**（`/客戶` `/買` `/庫存` `/待辦` `/筆記`，含 `/c /s /i /t /n` 簡寫）直達 Notion／GitHub，**零 API 成本**；**自然語言與語音**才走 Claude。日常九成操作免費，月費從 NT$150 降到約 **NT$10** |
| 不做 | 跑腳本、剪片、送印、**建訂單**（要同步四個系統，手機打錯字沒得檢查）|
| 白名單 | 只認 `TG_CHAT_ID` 一個 chat，其他人傳訊息一律忽略 |
| 知識庫 | 寫進私人 repo `liam-workspace/knowledge/{seafood,wine,tea,business,misc}/` |

⚠️ **模型**：`wrangler.toml` 的 `MODEL` ＝ `claude-haiku-4-5`（估 NT$120~180/月，每天 30 則）。
每則固定輸入 1,683 token（工具定義 1,179＋system 504）。**換模型只改那一行**——
`effort` 參數由 `worker.js` 的 `EFFORT_OK` 正則自動開關（Haiku 4.5／Sonnet 4.5 收到 effort 會 400）。
知識筆記整理品質變差就升 `claude-sonnet-5`，判斷訊號見 README。

---

## 跨裝置存取（電腦＋手機 Claude Code，2026-07-06 建立）

雙 repo 架構，讓手機也能讀改任務/記憶/待辦：

| repo | 可見性 | 內容 |
|------|--------|------|
| `lien2fish/liam-ai-agent`（本 repo）| 🌐 公開 | 任務腳本、tools/、workflows |
| `lien2fish/liam-workspace` | 🔒 私人 | 記憶(`memory/`)、`MEMORY.md`、`DISCUSSIONS.md`(決策摘要)、`TODO.md`、`plans/`、`PHONE_START.md` |

- **敏感資料（客戶/財務/身分證）只進私人 repo**，永不進公開庫；身分證等最高敏感原始檔維持純本機、不進任何 repo。
- 本機 clone：`~/liam-workspace/`；同步腳本 `~/liam-workspace/sync_workspace.sh`（`push`＝本機→repo、`pull`＝repo→本機並先備份）。
- **同步方式＝手動**（2015 Air 記憶體吃緊，不掛 SessionStart 自動同步 hook）。使用者說「手機改過了」→ 跑 `pull`；本機記憶更新後 → `push`。
- **例外：`daily/` 工作日誌自動 push**（`scripts/session_log.py` 的 `push_daily()`，SessionEnd 背景 detach 執行，只 add `daily/`）。週報 workflow 每週一在雲端讀這份日誌，不自動推就會讀到舊資料。失敗一律靜默，不影響 session 結束。
- 手機：claude.ai/code 登入同帳號→授權兩個 repo→開 `liam-workspace` 貼 `PHONE_START.md` 開場提示。
- 詳見 memory `project_cross_device_workspace.md`。

---

## 瀏覽器操作原則

- **一律使用 Safari**：`open -a Safari "URL"`
- **不使用 Playwright Chromium**（除非純粹截圖分析，與登入無關）
- Google OAuth 授權流程：啟動 `python3 /tmp/oauth_capture2.py &`（port 8888）→ 開 Safari 授權 → code 自動寫入 `/tmp/yt_oauth_code.txt`

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

## 剪輯短影音／長影音

三套獨立工具：`tools/reel_maker.py`（海鮮實拍）、`tools/music_reel.py`（樂器演奏）、
`tools/dessert_longform.py`（甜點頻道）。**規格、config 寫法、所有地雷都在 `reel` skill**，
要剪片時載入它，不要憑印象動手——三者音訊處理哲學相反，混用會毀掉產線。

渲染前一律先跑 `python3 tools/reel_check.py <config>`，修完 ❌ 才 build。

⚠️**剪片暫存不會自清、會把硬碟塞爆**（2026-08-03 實測）：每跑一次就在系統暫存區
`/private/var/folders/nx/*/T/tmp*/` 留下整套 `seg*.mp4`＋`joined.mp4`＋`.wav`，
三天累積 **394 份共 23.7GB**，把 113GB 磁碟壓到只剩 146MB。連帶災情：**iCloud 會自動
evict Desktop 上的檔案**（志工照片變 `.icloud` stub）、Bash 連寫 output 都失敗。
查用量 `du -sh /private/var/folders/*/*/T`，清完空間一放出來 iCloud 檔案通常會自己回來。

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
