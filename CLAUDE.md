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
- **`gh` CLI**：v2.98.0，2026-08-27 裝於 `~/bin/`（**不經 Homebrew**，macOS 12 已不被 brew 支援）。
  `~/bin/gh` 是 wrapper，執行時經 `git credential` 取 PAT 注入 `GH_TOKEN`；本體是 `~/bin/gh-bin`。
  ⚠️ **`gh auth status` 會警告缺 `read:org`，那是正常的不用修**——PAT 只有 `repo`+`workflow`，
  而 `gh auth login` 硬性要求 `read:org`，所以刻意不走 gh 自己的認證儲存。
  ⚠️ 讀 Actions 失敗 traceback **只有 gh 做得到**（免金鑰 API 讀 log 回 403），詳見 `ops-rescue` skill。
  ⛔ 不可用 `gh workflow run` 觸發 `daily_post`／`ig_story_teaser`／`ig_comment_reply`／`yt_auto_post`。

## MCP 工具（已安裝，scope: user）
| 工具 | 套件 | 說明 |
|------|------|------|
| firecrawl | `firecrawl-mcp` | 抓取任何網頁內容，API Key 已設定於環境變數 |
| filesystem | `@modelcontextprotocol/server-filesystem` | 存取 Desktop / Documents / Downloads |
| playwright | `@playwright/mcp` | 控制 Chromium 瀏覽器 |
| notion-mcp | Notion MCP | 搜尋、新增頁面等 Notion 操作 |

- ⛔ **google-workspace MCP 已於 2026-08-27 移除**：`@presto-ai/google-workspace-mcp` 借用 Gemini CLI 的 Workspace OAuth client，token 從未寫入本機，導致每次開 session 都跳一次授權頁（scope 含 gmail.modify、drive 全權）。Gmail／行事曆改走 GitHub Actions 自己的 Secret 與 Claude 內建連接器，不要重裝
- 查看 MCP 狀態：`/mcp`

## 已授權工具權限（settings.json allow 清單）

### MCP 工具已允許功能
| 工具 | 已允許的操作 |
|------|-------------|
| filesystem | write_file |
| playwright | navigate、screenshot、snapshot、click、type、press_key、evaluate、resize、close |
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
| **`safe-commit`** | **任何東西要進版控之前**——commit、push、新增資料檔。判斷敏感等級、決定該進哪個 repo、實際查證目的地公開程度。含 2026-08-21 客戶名單外洩事件的止血流程 |
| **`secrets-ops`** | **動任何金鑰之前**——新增／輪替 API key、token、密碼，或判斷「是不是過期了」。21 把金鑰的爆炸半徑、到期規律、`scripts/set_secret.py` 用法、Cloudflare Worker secret 的坑 |
| **`ops-rescue`** | **自動化掛了**——任務沒跑、報告沒出、提醒沒收到。含症狀對照、共用金鑰連鎖失效、手機能不能修 |
| **`seafood-brand`** | **任何對外的海鮮內容**——IG 發文與留言、影片腳本、海報與酒單文案、官網簡報。產地事實界線（有自家漁船 ✅／本人出海 ❌）、五條不可編造紅線、品牌口吻，以及只有 Lien 知道的待補知識清單 |
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
| IG + FB | 每日發文 | 每天 08:07 | ✅ 運行中 |
| IG | 留言自動回覆 | 每 5 分鐘 | ✅ 運行中 |
| YouTube | Shorts 留言通知（不回覆） | 每天 08:37 | ✅ 運行中 |
| YouTube | 手動上傳＋排定發布（連老闆／泥馬的真心話） | 手動觸發 | ✅ 見下方 |
| TikTok | — | — | 手動，不自動化 |

---

## GitHub Actions 自動化總覽（2026-06-02 更新）

所有雲端自動化任務均透過 GitHub Actions 執行，不依賴本機開機。

⚠️ **所有 cron 都刻意避開整點與 :00/:15/:30/:45**（2026-08-27 調整）。UTC 整點是全球最壅塞的時刻，GitHub 官方明說 schedule 在高負載時會延遲、甚至**整次跳過**（2026-08-27 就有 11 支完全沒觸發）。改動 cron 時**不要挪回整點**。

| Workflow 檔案 | 任務 | 排程 |
|--------------|------|------|
| `daily_post.yml` | IG+FB 每日發文 | 每天 08:07 |
| `ig_comment_reply.yml` | IG 留言自動回覆 | 每 5 分鐘（**實測常delay 1.5~4小時，GitHub高頻排程平台限制，非設定錯誤**） |
| `ig_story_teaser.yml` | IG 限動 Reels 預告（從已發布 Reels 剪 3 秒＋「Reels完整版～」，30 天不重複） | 每天 18:08（接 Reels 18:00） |
| `gmail_automation.yml` | Gmail 清理 + 新聞摘要 | 每天 08:13，自動 commit 報告 |
| `notion_monthly_report.yml` | Notion 月報 | 每月 1 日 08:57（**2026-07-02 修**：CRM 於 06-26 整併後，`notion_crm/monthly_report.py` 原引用不存在的 `DB["sales"]` 且欄位名對不上，已改讀「全品牌銷售紀錄」統一DB `38bf4149-a6aa-81db-9b89-c47410857a2c`，欄位＝金額/出貨日期/客戶名稱）|
| `market_daily.yml` | 每日股市全面分析報告 | 每天 **12:00**（台灣），自動 commit 報告 |
| `seafood_prices.yml` | 漁獲市場行情追蹤 | 每天 09:37 |
| `yt_comment_monitor.yml` | YouTube Shorts 留言通知 | 每天 08:37 |
| `policy_expiry_check.yml` | 產險保單到期提醒 | 每天 08:17，自動 commit 報告 |
| `life_visit_reminder.yml` | 壽險客戶固定拜訪提醒 | 每天 08:43，讀Notion算下次拜訪日，本週到期Email（**無commit，客戶個資只走Email**）|
| `birthday_reminder.yml` | 壽險客戶生日提醒 | 每天 08:23，未來7天內生日則Email（含歲數，無commit）|
| `repurchase_reminder.yml` | 三品牌客戶回購提醒 | 每天 09:07，超60天未回購則 Email（**2026-08-21 起無commit，客戶個資只走Email**——原本每天 commit 報告，已累積 56 份含姓名與手機的報告在公開 repo）|
| `weekly_revenue_sprint.yml` | 營收衝刺週報（本週壽險該接觸名單＋話術：A組未來14天生日切入、B組壽產保單健檢每週輪替6位） | 每週一 08:03，Email（**無commit，客戶個資只走Email**）|
| `yt_auto_post.yml` | YouTube 自動影片（宇宙/古文明未解之謎，無人臉，頻道=The Unknown Hour；Shorts 週二/五、長片週日）| 每天 10:07（**2026-08-26 當日暫停半天後即恢復**，Lien 指示）|
| `yt_channel_report.yml` | The Unknown Hour 頻道每日表現日報 | 每天 08:33（隨發片一起恢復，2026-08-26）|
| `claude_task_runner.yml` | Claude 任務讀取器（列出GitHub Issue中標記`claude-task,pending`的待辦） | 手動觸發（workflow_dispatch） |
| `rotary_birthday_reminder.yml` | 中城網路扶輪社社友生日提醒（剛好前14天Email一次；資料=私人repo `liam-workspace/rotary/中城網路社友通訊錄.json` 71位，用`WORKSPACE_PAT` checkout，**個資不進公開repo、無commit**） | 每天 08:27 |
| `token_expiry_check.yml` | **IG／FB Token 到期與失效檢查**（不寫死日期，每天問 `debug_token` 實際狀態；剩 30/21/14/10/7/5/3/2/1 天時提醒，失效或缺權限則 🔴 並讓 run 變紅）。**Email＋LINE 雙通道** | 每天 08:47 |
| `weekly_review.yml` | **AI 工作週報**（上週做了什麼＋可精進＋自動化健康＋下期建議，Email 附正式 PDF）。資料＝私人repo `daily/` 工作日誌＋公開repo git log＋Actions runs API＋`TODO.md` diff；**報告只進私人repo `liam-workspace/reviews/`，不進公開repo** | 每週一 08:53（錯開 08:03 營收週報）|
| `schedule_watchdog.yml` | **排程巡邏**（GitHub 的 schedule 會誤點、負載高時整次跳過。檢查今天該跑的有沒有跑，超過 2 小時寬限仍沒跑就自動 `workflow_dispatch` 補觸發，並回頭確認真的多出一次 run 才算成功）。⛔ **`daily_post`／`ig_story_teaser`／`yt_auto_post` 只通知不補跑**——自動補跑等於自動對外發布，發出去 API 刪不掉。時間表直接讀各 workflow 的 cron，改排程不用同步兩邊 | 台灣 08:19~14:19 每小時一次，另加 20:19（限動預告排 18:08，寬限後要 20:08 才判得出來）|

### GitHub Secrets 總覽
| Secret | 用途 |
|--------|------|
| `ANTHROPIC_API_KEY` | Claude API Key。2026-06-26 新增，Console 已儲值（**預付制、非訂閱**，與 Claude Code 訂閱是兩筆帳）。四處在用：IG 發文文案＋畫圖 prompt（`instagram/generate_post.py`，**Sonnet 5**）、YouTube 影片腳本（`youtube_auto/generate_script.py`，**Sonnet 5**）、AI 工作週報（`scripts/weekly_review.py`，**Sonnet 5**，每週一次約 6K token）。手機助理（Haiku 4.5）已寫好但**未接通、不計費**。模型常數 `CLAUDE_MODEL` 在各腳本頂端。⚠️ **Sonnet 5 起 `content[0]` 可能是 thinking block**，解析回應一律遍歷找 `type == "text"` |
| `GEMINI_KEY` | Gemini AI Key（claude-workspace-495009，**2.5-flash** 模型）。**注意：實為免費額度，未開通Cloud Billing**（2026-06-23實測證實，`2.5-flash`限20次/天、`2.5-pro`免費額度0），所有共用此Key的自動化共用同一日額度池，理論上會互搶額度 |
| `OPENAI_API_KEY` | OpenAI 生圖（IG 插圖＋YouTube 場景圖），`gpt-image-1-mini`。2026-08-06 設定，預付制需儲值。本機備份於 `config/.openai_key` |
| `HF_TOKEN` | （已停用）Hugging Face FLUX→Pollinations→OpenAI，兩任前身皆因免費額度取消而汰換 |
| `IG_TOKEN` | Instagram Graph API（到期 2026-07-16）|
| `IG_ID` | Instagram 帳號 ID |
| `FB_PAGE_TOKEN` | Facebook Page Token（`expires_at`＝0，但**「永不過期」不等於不會失效**——2026-08-25 隨 user session 被作廢一起死掉。用 user token 打 `GET /{page-id}?fields=access_token` 重簽即可。⚠️ 目前**沒有任何腳本真的用到它**，FB 跨發走 IG 的 `cross_post_ids`）|
| `FB_PAGE_ID` | Facebook Page ID |
| `GMAIL_CLIENT_ID` | Gmail OAuth |
| `GMAIL_CLIENT_SECRET` | Gmail OAuth |
| `GMAIL_REFRESH_TOKEN` | Gmail OAuth |
| `NOTION_TOKEN` | Notion API Token |
| `YT_API_KEY` | YouTube Data API v3 金鑰（無到期問題；連老闆留言通知＋The Unknown Hour 頻道日報共用）|
| `YT_CHANNEL_ID` | YouTube 頻道 ID（連老闆-產地到餐桌）|
| `YT_OAUTH_CLIENT_ID` / `YT_OAUTH_CLIENT_SECRET` / `YT_OAUTH_REFRESH_TOKEN` | The Unknown Hour 自動上傳 OAuth（scope youtube.upload，同意畫面已發Production不過期）2026-06-29設 |
| `GMAIL_APP_PASSWORD` | Gmail App 密碼，供 YouTube 留言通知＋頻道日報＋回購提醒寄信用 |
| `LINE_NOTIFY_URL` | liam-assistant Worker 網址，供 `line_assistant/notify.py` 推 LINE（2026-08-25 新增）|
| `LINE_NOTIFY_TOKEN` | 與 Worker secret `NOTIFY_TOKEN` 同值。**2026-08-25 輪替過一次**（舊值沒留存，當時無人使用）|
| `WORKSPACE_PAT` | 存取私人 repo `liam-workspace` 的 PAT（＝本機 liam-workspace remote 內同一組，永不過期）。兩個用途：扶輪社生日提醒 checkout 個資、YouTube 自動影片 checkout 授權配樂（`assets/bgm/`，音檔不進公開 repo）|

---

## 手機助理（LINE，2026-08-24 上線）

✅ **已接通並實測可用。** Cloudflare Worker `liam-assistant`
（`https://liam-assistant.lien2fish.workers.dev`），LINE 官方帳號「Liam 助理」，
白名單只認 Lien 一個 LINE user ID。前身是 Telegram 版，帳號無法使用而改接 LINE；
資料夾 `line_assistant/`（原 `telegram_bot/`，2026-08-24 改名，實測沒有任何腳本 import 它）。

**部署與維運在 `line_assistant/README.md`**，導入客戶的流程與定價在 `line_assistant/導入手冊.md`。

⚠️ **程式碼不含商業資訊。** 身分、品牌、Notion 欄位、workflow 清單全部在
`line_assistant/profile.js`（範本＝`profile.example.js`）。要改助理的語氣、加減功能、
換欄位對照，**改 profile.js，不要改 worker.js**。沒設定的區塊會自動關掉對應的
工具與指令。

⚠️ **`wrangler secret put` 不能在 Claude Code 的對話框裡跑。**
那裡沒有互動終端機，互動提示讀到空值也照樣印「✨ Success」，
結果是 secret 存成**空字串**而毫無徵兆（2026-08-24 因此卡了三輪）。
一律開 Terminal.app 跑；或非互動地用 `printf '%s' "$(tr -d '\r\n' < 檔案)" | npx wrangler secret put NAME`。

⚠️ **LINE 額度**：reply（對話回覆）不計額度、無上限；push（`/notify` 推播）
計入輕用量方案的 **200 則／月**。推播只接失敗警報與需要決策的事。

| 項目 | 說明 |
|------|------|
| 程式 | `line_assistant/worker.js`（單檔，raw fetch，無 npm 依賴，同 `travel_worker` 風格）|
| 指令 | `/客戶 /買 /庫存 /待辦 /筆記 /跑 /查`（簡寫 `/c /s /i /t /n /r /k`）|
| `/查` | 查 16 個排程任務健康度，純唯讀。含「**不穩定**」分類——只看最後一次的話，時好時壞的任務會顯示成正常（月報最近 5 次失敗 3 次就是這樣被漏掉的）|
| ⛔ 保護 | **`/跑` 不接受會對外發布的四個任務**（IG發文／IG留言回覆／限動預告／YouTube影片）——斜線指令不經過 AI、沒有確認步驟。要發走自然語言或電腦 |
| 推播 | `line_assistant/notify.py` — 任何腳本 `from line_assistant.notify import notify` 即可用；**未設環境變數時靜默跳過**，不會弄壞既有流程。⚠️ **2026-08-25 修**：原本用 urllib 預設 User-Agent，**被 Cloudflare 回 403 擋掉**，而 `silent_fail` 會把它吞掉——等於推播從來沒送出去過也不會有人發現。已改送 `User-Agent: liam-notify/1`。⚠️ `/notify` 連打會被限流（回 500／連線中斷），測試要隔開 |
| 能做 | 記待辦、口述存知識庫（含語音轉文字）、查客戶／銷售／庫存、接收自動化推播 |
| **兩種模式** | **斜線指令**（`/客戶` `/買` `/庫存` `/待辦` `/筆記`，含 `/c /s /i /t /n` 簡寫）直達 Notion／GitHub，**零 API 成本**；**自然語言與語音**才走 Claude。日常九成操作免費，**估**月費約 NT$10（2026-08-24 上線，尚未累積實際帳單）|
| 不做 | 跑腳本、剪片、送印、**建訂單**（要同步四個系統，手機打錯字沒得檢查）|
| 白名單 | 只認 `LINE_USER_ID`，其他人傳訊息一律靜默忽略。**兩道驗證皆 fail closed**（簽章＋user ID），26 項邊界測試涵蓋 |
| 知識庫 | 寫進私人 repo `liam-workspace/knowledge/{seafood,wine,tea,business,misc}/` |

⚠️ **模型**（成本為估算，尚未累積實際帳單）：`wrangler.toml` 的 `MODEL` ＝ `claude-haiku-4-5`。
每則固定輸入 1,683 token（工具定義 1,179＋system 504）。**換模型只改那一行**——
`effort` 參數由 `worker.js` 的 `EFFORT_OK` 正則自動開關（Haiku 4.5／Sonnet 4.5 收到 effort 會 400）。
知識筆記整理品質變差就升 `claude-sonnet-5`，判斷訊號見 README。

**三個庫存 DB 的欄位名互不相同**（鑫酒藏無「單位」、鑫海產叫「數量單位」、
價格分別是進價／零售價／進價），`worker.js` 的 `INV_FIELDS` 各給一組對照。
**不要假設三個品牌欄位一樣**——2026-08-24 就是這樣讓 `/庫存` 印出一片空白。

**日後可考慮**：LINE 官方帳號能直接對客戶開放，變成訂單與詢問的入口。
但那要獨立的 prompt 與工具集，**不可與私人助理共用同一條路徑**（工具查得到客戶資料）。

---

## 對外發布的 Plugin（2026-08-25 建立）

獨立 repo **`lien2fish/lien-plugins`**（🌐 公開，MIT），四個 Claude Code plugin：
`line-assistant`／`print-cmyk`／`reel`／`safe-commit`。
本機 clone 在 `~/lien-plugins/`。

```
/plugin marketplace add lien2fish/lien-plugins
```

⚠️ **plugin 版是去識別化過的通用版本，跟 `.claude/skills/` 的原版是兩份東西。**

| | `.claude/skills/`（本機） | `lien-plugins`（公開） |
|---|---|---|
| 內容 | 特定檔名、路徑、客戶資訊——留著才有用 | 只有通用 know-how |
| `safe-commit` | 詳載本專案的外洩事故 | **改寫成不指名的案例**（無 repo 名／公司名／日期）|
| `print-cmyk` | 惜食廚房各面牆、志工表單網址 | 拿掉全部特定資訊 |

**改動要同步時，判斷該進哪一份**：特定細節進本機、通用教訓進 plugin。
散布前一律重跑一次去識別化檢查——`safe-commit` 那份直接散布等於自己公告公司外洩過客戶資料。

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
