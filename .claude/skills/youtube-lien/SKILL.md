---
name: youtube-lien
description: 連老闆-產地到餐桌／泥馬的真心話（甜點）頻道的 YouTube 手動上傳與排程發布：yt_upload.py、yt_batch_schedule.py、profile 設定、發布節奏、標題與 hashtag 規則、Shorts 留言通知。要上傳影片、排發布時間、寫標題文案時載入。
---

## YouTube 手動上傳＋排程發布（2026-08-13 擴充到甜點頻道）

剪好的成品用指令上傳並排定發布時間，影片先私人、屆時 YouTube 自動轉公開。
與 `yt_auto_post.yml`（The Unknown Hour 全自動生成）是兩回事。

| 工具 | 用途 |
|------|------|
| `tools/yt_upload.py` | 單支上傳。`--desc 發文案.md --at "2026-08-14 18:00" --profile dessert` |
| `tools/yt_batch_schedule.py` | 批次上傳＋自動排時間表 |
| `youtube_auto/oauth_setup.py` | 一次性授權，`--profile <名稱>`；要改既有影片再加 `--write` |

### 頻道（profile）與預設值

`upload.py` 的 `PROFILE_DEFAULTS` 分頻道設定，**不可共用一組**：

| profile | 頻道 | categoryId | 語言 |
|---------|------|-----------|------|
| （無） | The Unknown Hour | 27 教育 | en |
| `lien` | 連老闆-產地到餐桌 | 22 人物與網誌 | zh-Hant |
| `dessert` | **泥馬的真心話**（台名；「甜點輕鬆做．師傅真心話」是標語） | 26 教學與風格 | zh-Hant |

憑證 `config/youtube_oauth_<profile>.json`（gitignore）。

### 批次排程用法

**甜點頻道發布節奏＝每兩天一支**（EP 與 Shorts 混在同一條序列，不分開排）。
`--every` 預設就是 2，照下面這樣打即可；**不要再加 `--days`**（會蓋掉每兩天的節奏）。

```bash
# 每兩天 18:00 一支，資料夾內依檔名排序
python3 tools/yt_batch_schedule.py 成品/某資料夾 --profile dessert \
    --start "2026-08-16 18:00" --dry-run

# 用排程表（可讓多支同一天發，例：長片＋EP1 同天開場）
python3 tools/yt_batch_schedule.py --plan dessert/千層排程.json --profile dessert
```

Shorts 要**平均穿插在 EP 之間**、不要連著發也不要擠在尾巴。資料夾模式是依檔名排序，
Shorts 若另存子資料夾就不會自動穿插，這種情況改用 `--plan` 排程表指定順序。

已上傳的記在 `<資料夾>/.yt_uploaded_<profile>.json`（在 gitignore 的 `成品/` 內），
中斷後重跑同一行會自動跳過。

### 發布節奏（2026-08-15 使用者指定）

- **Shorts 每兩天 18:00 一支**（連老闆與甜點頻道同節奏）
- **長片放進兩支 Shorts 之間的空檔日**，不與 Shorts 同日發。
  排長片時**只動長片**，Shorts 的日期一律不改
- 長片與某支 Shorts 內容重疊時，**長片排在該 Shorts 前一天**，
  讓 Shorts 上線時長片已經在那裡接得住（推薦影片是這個頻道的主要流量來源）

### 標題與 hashtag 規則（2026-08-15 使用者指定，連老闆＋甜點頻道都適用）

**每支影片的標題與說明都要帶上「能吸引人也能被搜尋」的 hashtag。**

| 規則 | 說明 |
|------|------|
| 標題長度 | **≤30 字**。瀏覽／推薦版位只顯示到約 30 字，後面會被截掉 |
| 標題 hashtag | **1～2 個**。系列名可就地變成 hashtag（`｜#千層蛋糕研發日記 EP1`），不增加長度 |
| 描述 hashtag | 12～13 個，**前 3 個會顯示在標題正上方**，該支的主題字排最前面 |
| 總數上限 | **15 個（標題＋描述合計）。超過一個，整支影片的 hashtag 全部失效** |
| 集數編號 | 寫 `EP1` 不要寫 `#1`——`#1` 會被算成一個 hashtag，八集就吃掉八個額度 |
| `#shorts` | 只放描述、不放標題。是不是 Shorts 由「直式且 ≤3 分」決定，標題掛著純浪費額度 |

- 連老闆：`reel_maker.write_captions()` 已自動產出三平台 hashtag——該支主題字寫在 config 的
  `hashtags`，品牌字（`BRAND_TAGS`）自動墊後，標題超過 30 字會在文案裡標警告
- 甜點頻道：`dessert_longform.py` 是照 config 的 `youtube` 區塊原樣輸出，**要自己寫足**
- **實測依據**：連老闆長片 17 字標題 CTR **9.3%**、49 字標題 **1.3%**

### ⚠️ 地雷

- **驗收條件＝`processingStatus == succeeded`**，不是「videos.list 查得到」。
  上傳中斷會留下半成品：查得到、時長 `P0D`、永遠卡在 processing，
  既不發布也不報錯，放久了還會被 YouTube 清成 `Deleted video`
- **API 配額三頻道共用**（同一組 OAuth client）：上傳 1600／`videos.update` 50／
  每日 10,000 → **一天最多 6 支**。重置＝太平洋午夜＝**台灣下午 3 點**
- **Shorts 一律不設自訂縮圖**，直接用影片畫面。`<片名>_封面.jpg` 是壓進影片開頭
  1 秒的**直式封面卡**、不是縮圖，上傳工具已不再把它當縮圖送（Shorts 的縮圖 API
  本來也無效，回 200 但不生效）。長片才設縮圖，但**頻道要先完成電話驗證**
  （https://www.youtube.com/verify），否則 403
- **1080×1920 且 ≤3 分鐘一律被當 Shorts 收錄**，會活在 Shorts 頁籤而非一般影片版位
- **發文案 .md 有兩種格式**，`read_desc` 兩種都吃：連老闆是 IG/YT/TikTok 三段式
  （`- 標題：`），甜點頻道是 `**標題**`／`**描述**` 程式碼區塊／`**Tags**` 逗號清單
- `youtube.upload` scope **不含讀取**，查頻道／影片一律 403
- 背景執行時 `input()` 的提示字尾沒換行，會被誤判成「waiting for interactive input」。
  看 `.yt_uploaded_*.json` 判斷實際進度，不要砍掉重跑


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
