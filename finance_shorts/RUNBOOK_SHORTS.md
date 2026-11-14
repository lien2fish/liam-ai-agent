# 金錢怪物：無人值守做一支獨立 Short《錢的誤會》

本機排程（`auto_shorts.py`）每週兩次啟動 Claude Code 照這份跑，**沒有人在電腦前**。
2026-11-15 Lien 同意 Shorts 自動開工，先試跑 4 支（兩週）再決定要不要擴大；長片不在這份的範圍。

通則（內容原則、查證規則、渲染規則、發音替代字、跟 Codex 協作）都在 `RUNBOOK.md`，這裡只寫獨立 Short 不一樣的地方。

## 無人值守的規矩

- **不提問、不等回覆**。需要 Lien 決定的事一律當成「這題不做」，換下一題；沒有下一題就照最後一節收工
- **一次只做一支**，做到排程上片、紀錄、commit 就結束
- 不花錢：不生圖、不呼叫任何付費 API（克隆配音在本機跑，不算）
- 不碰長片、不改既有影片的排程、不發 IG／FB
- 不改產線程式（`slides.py`／`make_shorts.py`／`publish.py`／`tts.py`）。程式出錯就收工回報，等 Lien 開對話再修

## 步驟

### 1. 選題：`題目紀錄.md` 的《錢的誤會》題庫（「待做」那一列），由左到右拿第一個沒做的

題庫空了就收工並通知，不自己開新題。拿到題目後先過這張表，任何一條中了就跳過、在題庫那題後面註明原因：

| 不做 | 例子 |
|---|---|
| 保險、投資、理財商品 | 儲蓄險、ETF、信用卡點數比較 |
| 點名特定公司或個人 | 某銀行的分期方案 |
| 牽涉現任公職或參選人 | 候選人政見 |
| 答案取決於還沒定案的事 | 審議中的法案、未公告的費率 |
| 找不到官方原文 | 只有媒體或部落格講法 |

集數編號接續 `ms-xx`（看 `scripts.json` 現有最大號加一）。

### 2. 查證 → `<集>/add_facts.py` → `facts.json`

- 格式照 `ms-02/add_facts.py`。每條事實 ≥2 個獨立來源、至少 1 個官方原文，`quote` 要是原文摘句
- 法規題的官方原文＝全國法規資料庫的條文＋主管機關函釋或問答（勞動部、行政院消保會、金管會）。**條文要讀現行版**，寫明查詢日期
- 例外與條件要一起查：ms-02 的教訓是「例外要符合條件＋業者有告知」「生鮮不等於法定例外」「實體店不適用」，少了這些答案就是錯的
- 試算數字另立一條事實（照 `MWFX`），寫清楚算式與假設

### 3. 腳本 → `<集>/add_script.py` → `scripts.json`

- 格式照 `ms-02/add_script.py`：`format: slides`、`aspect: 16:9`、`tts: clone`、`speed: 1.2`、`gap: 0.15`、`clip_max: 6.0`
- **9～12 句**，成品 45～65 秒。Short 本身給完整答案
- 第 1 句是那個「大家信以為真的說法」，第 2～3 句給結論，中段講條件與例外，最後一句講「所以你可以怎麼確認」（查哪個機關、看哪份文件），不下指導棋
- 每句的 `say` 另外寫：阿拉伯數字全寫成中文、套 voice-clone skill 的替代字
- 畫面用 `shared/broll/` 現有的台灣素材分類（`tw_mrt`、`tw_city`、`tw_tm`、`mm_store`、`mm_laptop`、`bk_phone`、`bk_atm`），**不下載新素材**；`reject` 先抄 `ms-01`、`ms-02` 的清單再加
- `note` 固定含「資訊整理，非法律建議｜資料來源見說明欄」

### 4. 兩道閘門（都要過）

```
python3 finance_shorts/verify.py <集>
```

再把這集的事實與腳本送 Codex 唯讀審查（指令與審核清單在全域 skill `codex-delegate`，要加 `env -u NODE_OPTIONS`）。
請它找：沒對到事實的數字、被省略的條件與例外、像建議的用語、`say` 裡會唸錯的字。
逐條驗證後修正；**修完再跑一次 `verify.py`**。Codex 叫不起來就收工，不跳過這道。

### 5. 配音、回聽、渲染

```
taskpolicy -b python3 finance_shorts/tts.py <集>
taskpolicy -b python3 finance_shorts/check_vo.py <集>     # 逐句比對數字，唸錯就改 say 重產
python3 finance_shorts/slides.py <集> --render           # 不要加 taskpolicy
```

渲染一律經 `tools/hf_render.py`（`slides.py` 已接好）。崩過一次不要原樣重跑，直接收工。

### 6. 切直式：寫 `<集>/shorts.json`，然後 `python3 finance_shorts/make_shorts.py <集> a`

- 格式照 `ms-02/shorts.json`：`"long": null`、只有一支 `a`、`lines` 取第 2 句到最後一句、`hook` 另寫一句直接問觀眾的開場
- `yt.summary` 把條件、例外、試算假設寫完整；`hashtags` 第一個是 `shorts`、最後一個是 `金錢怪物`

### 7. 驗收（全部要過才上片）

| 項目 | 怎麼驗 |
|---|---|
| 規格 | `ffprobe`：1080×1920、45～65 秒、`color_transfer` 是 `bt709` |
| 聲音 | `afconvert` 轉 wav 後量開頭、中段、結尾音量，三處都要有聲音 |
| 開場鉤子 | Whisper 回聽 `hook`，數字與關鍵詞要對 |
| 畫面 | 抽 6 格以上實際看：標題與字幕沒貼邊或掉字、沒有黑畫面、沒有別人的浮水印、近距離人臉、看得到的價格或電話 |
| 內容 | 成品字幕逐句對回 `facts.json`，沒有多出來的數字 |

任何一項修兩輪還不過，就收工。

### 8. 上片

```
python3 finance_shorts/publish.py <集> --short a --dry-run
python3 finance_shorts/publish.py <集> --short a --at "YYYY-MM-DD 18:00"
```

- **發布時間＝距離現在至少 48 小時、而且那天 18:00 還沒有任何影片排程的第一天**（先用 YouTube API 列出頻道已排程的影片再決定，不要只看 `題目紀錄.md`）。Lien 要有時間回「停」
- `publish.py` 會自己驗收並傳 LINE。回 `uploadLimitExceeded`＝今天上傳額度用完：不要重試，在題目紀錄註明「成品已完成、待上傳」，收工通知
- **上傳只跑一次**。出現「已上傳」之後的任何錯誤都不要重跑，把 video_id 手動補進 `shorts.json`

### 9. 收尾

- `題目紀錄.md`：題庫那一列改成這集的紀錄（集數、題目、事實編號、Codex 審幾條採幾條、video_id、公開時間）
- 新踩到的唸錯詞寫進 `.claude/skills/voice-clone/SKILL.md`
- 照 `safe-commit` skill 檢查後 commit、push（只收這集的 `add_facts.py`／`add_script.py`／`shorts.json`、`facts.json`、`scripts.json`、`題目紀錄.md`）

## 收工回報（做不成的時候）

1. 不上片、不硬湊
2. `~/bin/gh workflow run line_notify.yml -f text="🔴 金錢怪物 Short 今天沒做成：<原因一句話>"`
3. 做到哪、卡在哪寫進 `題目紀錄.md`，下次開工先接著做這支
4. 最後一行輸出 `AUTO_SHORTS_RESULT: failed <原因>`

做成了，最後一行輸出 `AUTO_SHORTS_RESULT: ok <集> <video_id> <公開時間>`。
