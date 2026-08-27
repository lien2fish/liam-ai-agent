---
name: ops-rescue
description: 自動化急救手冊——17 個 GitHub Actions 掛掉時怎麼判斷與修復。含症狀對照、共用金鑰的連鎖失效、什麼能直接重跑、什麼手機做不到、金鑰到期日。發現任務沒跑、報告沒出、提醒沒收到，或使用者在外面說「XX 掛了」時載入。
---

# 自動化急救手冊

> 手機端（claude.ai/code）也讀得到 Actions log，所以在外面能完成整套判斷與修復。
> 電腦端一樣適用。

## 三步驟

**① 先確認是真掛了還是誤點**

```bash
gh run list --workflow=<檔名>.yml --limit 5
gh run view <run-id> --log-failed
```

✅ **本機已裝 `gh` CLI**（2026-08-27，`~/bin/gh` wrapper → `~/bin/gh-bin` v2.98.0，
不經 Homebrew）。**這是唯一讀得到失敗 traceback 的路**，見下方。

手機端（claude.ai/code）沒有 gh，或想免金鑰快掃時，repo 是公開的，**Actions API 不帶金鑰也讀得到**：

```bash
R=lien2fish/liam-ai-agent
curl -s "https://api.github.com/repos/$R/actions/workflows/<檔名>.yml/runs?per_page=30"   # 每次執行的成敗與時間
curl -s "https://api.github.com/repos/$R/actions/runs/<run-id>/jobs"                      # 停在哪一個 step
curl -s "https://api.github.com/repos/$R/check-runs/<job-id>/annotations"                 # 只給得到 exit code
curl -s "https://api.github.com/repos/$R/actions/runs?per_page=100"                       # 全部任務一次掃，最快看出是單一系統還是全面失效
```

⚠️ **免金鑰讀不到 log**（`/logs` 回 403 `Must have admin rights`），只拿得到 exit code。
**帶認證才有 traceback**——2026-08-27 實測同一個 run：免金鑰 403、帶 PAT 302。
所以根因判斷一律用 `gh run view <run-id> --log-failed`，不要再走「本機拿同一把金鑰重現一次」。
（Secrets 在 log 裡已被 GitHub 遮成 `***`。）

⚠️ **`gh` 的認證走 wrapper 從 keychain 現取，不是 `gh auth login`。**
既有 PAT 只有 `repo`／`workflow` 兩個 scope，缺 `gh auth login` 硬性要求的 `read:org`，
故改注入 `GH_TOKEN`（gh 對環境變數不做 scope 檢查）。`gh auth status` 會抱怨缺 `read:org`，
**那是正常的、不用修**——個人 repo 用不到組織相關指令。

⚠️ **手機端（claude.ai/code）沒有 gh**，仍受限於上面的免金鑰寫法，讀不到 traceback。
需要 log 才判得出根因的狀況，得等回到電腦。

⚠️ **GitHub 排程常誤點 1.5~4 小時**（平台限制，非設定錯誤），高頻的 `ig_comment_reply` 最明顯。
**還沒到就急著修，會改壞沒壞的東西。** 先看「上一次成功是什麼時候」。

**② 判斷屬於哪一類**（見下方症狀表）

**③ 分兩種處置**：偶發 → 直接重跑；根因 → 改程式後再跑

```bash
gh workflow run <檔名>.yml        # 重跑
```

⛔ **`daily_post`／`ig_story_teaser`／`ig_comment_reply`／`yt_auto_post` 不可自行 `gh workflow run`**，
一律先問——觸發等於自動對外發布，IG 發出去 API 刪不掉。與 `schedule_watchdog` 的保護一致。

---

## 症狀 → 原因 → 處置

| 症狀（log 裡看到的） | 原因 | 處置 | 手機能做？ |
|---|---|---|---|
| Claude API 5xx／逾時 | 偶發 | **直接重跑**，別改程式 | ✅ |
| `Claude 回傳異常` + `content` KeyError | Sonnet 5 開 adaptive thinking，`content[0]` 是 thinking block | 遍歷找 `type == "text"`，**不可寫 `content[0]["text"]`**（2026-08-19 已修 IG 與 YT 兩支） | ✅ |
| Gemini 429 `RESOURCE_EXHAUSTED` | 免費額度 20 次/天用完，**五個系統共用同一把 key** | 重跑無效，等隔天重置（**UTC 00:00 ＝台北 15:00**） | ✅ 等 |
| Gemini 503 UNAVAILABLE | 伺服器過載，暫時性 | 間隔 10~15 秒重試幾次會好。**跟 429 是不同問題，別搞混** | ✅ |
| OpenAI 生圖 4xx | 額度沒了／內容政策 | 去 Console 儲值。**4xx 不重試**（腳本已設計成直接中止） | ⚠️ 要開 Console |
| 生圖過半失敗 → `raise` 中止 | 生圖服務整體異常 | 這是**刻意的保護**（2026-08-05 曾產出整支同一張底圖的假成功影片）。等服務恢復再重跑 | ✅ |
| IG／FB 回 `OAuthException` **190 / subcode 460** | **session 被作廢**（改 FB 密碼或 Meta 安全性重設），**跟到期日無關、隨時會發生** | 走完整重新授權（見 `ig-fb-auto` skill）。⚠️ `fb_exchange_token` 換發救不回來 | ❌ **手機做不到** |
| IG／FB 回 `OAuthException`（其他） | IG Token 的**資料存取權**到期 | 走完整重新授權流程（見 `ig-fb-auto` skill） | ❌ **手機做不到** |
| Notion 404／400 | DB ID 錯或頁面被封存 | 對照各 skill 裡的 DB ID | ✅ |
| Gmail `invalid_grant` | refresh token 被撤銷／改密碼 | 重新授權（見 `gmail-ops` skill）。⚠️ 2026-07-12 已發 Production，**不再是每 7 天過期那個老問題** | ❌ 要開瀏覽器 |
| YouTube 上傳「查得到但卡 processing、時長 `P0D`」 | 上傳中斷的半成品 | **不是成功。** 驗收條件是 `processingStatus == succeeded`。刪掉重傳 | ⚠️ |
| YouTube 403 quota | 三頻道共用配額，一天最多 6 支 | 等重置（**太平洋午夜＝台灣下午 3 點**） | ✅ 等 |
| **LINE 推播該來卻沒來** | `notify.py` 的 User-Agent 被 Cloudflare 回 403，而 `silent_fail=True` 會把它吞掉 | 確認有送 `User-Agent: liam-notify/1`（2026-08-25 已修）。⚠️ `/notify` 連打會被限流，測試要隔開 | ✅ |
| 剪片相關失敗、磁碟爆掉 | 暫存不自清（曾累積 23.7GB） | 只發生在本機，Actions 不受影響 | — |
| `git push` 回 **HTTP 400** ＋ `send-pack: unexpected disconnect` | 改動量大，超過 git 預設的 HTTP 緩衝區 | **不是網路壞掉、不是權限問題，重試一樣會失敗。** 見下方「大包推送」 | ⚠️ 要開終端機 |

---

## git push 回 HTTP 400（大包推送）

**症狀**
```
error: RPC failed; HTTP 400 curl 22 The requested URL returned error: 400
send-pack: unexpected disconnect while reading sideband packet
fatal: the remote end hung up unexpectedly
```
有時後面還會跟一句 `Everything up-to-date`，很容易誤判成「已經推過了」——**沒有，遠端完全沒動。**

**原因**：git 預設的 HTTP 緩衝區太小，一次要傳的量超過就會被截斷。
不是網路問題、不是權限問題，**重試幾次都一樣**。

**處置**（2026-08-25 已在所有 repo 設好，理論上不會再遇到）
```bash
git config http.postBuffer 524288000   # 500MB
git config http.version HTTP/1.1       # HTTP/2 在某些網路下也會觸發
git push
```

**若仍失敗，分段推**——把歷史拆成幾包送：
```bash
MID=$(git rev-list --reverse HEAD | sed -n '500p')
git push --force origin ${MID}:refs/heads/main   # 先推一半
git push --force origin main                     # 再推其餘
```
分段期間遠端會停在中間的 commit，**全部跑完才算完成，中途不要停**。

**已設定的 repo**：`Liam AI agent`（主工作區，`work/2`~`work/5` 因共用 config 自動涵蓋）、
`liam-workspace`。**新 clone 的 repo 要重設**——這是 repo 層級設定，不會跟著帳號走。

**踩過的場合**：2026-08-21 公開 repo 歷史改寫後的 force push（123MB）、
2026-08-25 私人 repo 推備份與 PDF。兩次都是這個原因。

---

## ⚠️ 共用金鑰的連鎖失效

**一把金鑰掛掉會同時打死好幾個系統。** 排查時先看是不是共用的那把。

**完整的爆炸半徑表與到期規律在 `secrets-ops` skill**——這裡只留最會咬人的三條：

| 金鑰 | 連帶影響 | 為什麼危險 |
|---|---|---|
| `GMAIL_APP_PASSWORD` | **7 個提醒類任務** | 🔴 **失效是靜默的**——你只會覺得「最近沒收到提醒」，沒有任何錯誤通知。**超過一週沒收到提醒信就主動查** |
| `NOTION_TOKEN` | **6 個** | 🔴 一次死一片 |
| `GEMINI_KEY` | **5 個** | 🟡 免費額度共用會互搶，不是失效也可能不夠用 |

✅ IG／FB 那幾把已有 `token_expiry_check.yml` 每天 08:45 自動盯，不必靠人記日期。

## 排程時間表（台灣時間）

| 時間 | 任務 | 有 commit？ |
|---|---|---|
| 每 5 分鐘 | IG 留言回覆（**實測常延遲 1.5~4 小時**） | — |
| 08:00 | IG+FB 發文、Gmail 清理＋新聞、保單到期 | Gmail✓ 保單✓ |
| 08:05 / 08:10 / 08:40 | 生日提醒／扶輪生日／壽險拜訪 | — |
| 08:20 / 08:30 | YT 頻道日報／YT 留言通知 | ✓ |
| 08:45 | **Token 到期提醒**（IG／FB，Email＋LINE） | — |
| 09:00 / 09:30 | 回購提醒／漁獲行情 | ✓ |
| 10:00 | YouTube 自動影片（**只在週二、五、日製作**） | — |
| 12:00 | 市場日報 | ✓ |
| 18:05 | IG 限動預告（接 18:00 的 Reels） | ✓ |
| 週一 08:00 | 營收衝刺週報 | — |
| 每月 1 日 08:00 | Notion 月報 | — |

**「有 commit」的任務失敗時，repo 裡不會有當天的報告檔**——這是最快的自我診斷法：
看 `reports/` 有沒有今天的檔案。

---

## 手機做得到 / 做不到

| ✅ 手機（claude.ai/code）能做 | ❌ 要回電腦 |
|---|---|
| 讀 Actions log、判斷原因 | IG Token 重新授權（要走授權對話框） |
| 改程式、commit、重跑 | Gmail OAuth 重新授權 |
| 觸發任何 workflow（17 個全支援 dispatch） | 剪片、送印、動桌面素材 |
| 查 repo 裡的 skill 找地雷紀錄 | 需要本機 MCP 的任務 |

**GitHub 手機 App** 另外裝：Actions 失敗會推播（**這是唯一會主動告訴你掛了的東西**），
也能三個點擊重跑，不用開 AI。

---

## 到期日（會準時炸的東西）

> ✅ **2026-08-25 起有 `token_expiry_check.yml` 每天 08:45 自動盯**，
> 剩 30/21/14/10/7/5/3/2/1 天會 Email＋LINE 提醒，失效當天 run 直接變紅。
> 下表留著當背景知識，但**不需要靠人記日期了**。

| 項目 | 到期 | 症狀 |
|---|---|---|
| **IG Token 本身（`expires_at`）** | **2026-10-24** | 三個 IG 系統同時掛。⚠️ **2026-08-25 推翻舊紀錄**：長效 token 不是永不過期，是 60 天 |
| **IG Token 資料存取權** | **2026-11-23** | 同上。⚠️ `fb_exchange_token` 換發**不會**重置這個日期，必須走使用者授權對話框 |
| **IG session**（無到期日） | 隨時 | 改 FB 密碼就會被作廢，見症狀表 190/460。**2026-08-25 發生過一次** |
| FB Page Token | `expires_at`＝0 | **但會隨 user session 被作廢一起死**（2026-08-25 發生過）。重簽＝用 user token 打 `GET /{page-id}?fields=access_token` |
| GitHub PAT（新） | 永不過期 | — |
| Gemini 免費額度 | 每天重置（台北 15:00） | 429 |
| YouTube API 配額 | 每天重置（台北 15:00） | 403 |

---

## 修完之後

1. **重跑並確認真的成功**——不是「workflow 顯示綠燈」就算，要看實際產出：
   報告檔有沒有進 `reports/`、IG 限動是不是真的發出去（`GET /{media-id}` 抓回來比對）
2. **把新踩到的坑寫進對應 skill**，不要只留在對話裡。今天修的地雷，三個月後的你不會記得
3. ⚠️ **IG 限動與貼文發出去 API 刪不掉**（`DELETE` 回 `(#10) Insufficient permissions`，是平台限制）。
   重跑 `daily_post` 或 `ig_story_teaser` 前先想清楚——發錯只能請使用者到 App 手動刪
