# 金錢怪物：無人值守做一支獨立 Short《錢的誤會》

本機排程（`auto_shorts.py`）每週三次（週日、二、四 00:20，2026-11-26 起）啟動 Claude Code 照這份跑，**沒有人在電腦前**。
2026-11-15 Lien 同意 Shorts 自動開工，先試跑 4 支（兩週）再決定要不要擴大；長片不在這份的範圍。

通則（內容原則、查證規則、渲染規則、發音替代字、跟 Codex 協作）都在 `RUNBOOK.md`，這裡只寫獨立 Short 不一樣的地方。

## 無人值守的規矩

- **不提問、不等回覆**。需要 Lien 決定的事一律當成「這題不做」，換下一題；沒有下一題就照最後一節收工
- **一次只做一支**，做到排程上片、紀錄、commit 就結束
- 不花錢：不生圖、不呼叫任何付費 API（克隆配音在本機跑，不算）
- 不碰長片、不改既有影片的排程、不發 IG／FB
- 不改產線程式（`slides.py`／`make_shorts.py`／`publish.py`／`tts.py`）。程式出錯就收工回報，等 Lien 開對話再修
- Claude 撞到用量上限時，`auto_shorts.py` 會讓 Codex 接手做到第 7 步（關沙盒全權、不上傳、不 commit、不傳 LINE，2026-11-24 Lien 決定）。上傳前一定要 Claude 審查過

## 步驟

### 0. 先接續做到一半的集數（2026-11-23 加）

有 `ms-xx` 資料夾或 `scripts.json` 有這集、`<集>/shorts.json` 卻沒有 `video_id`＝上一輪中途斷掉（撞到用量上限、當機）。`auto_shorts.py` 會在開工指示裡點名；有就**接著做這集，不開新集、不換題**。

從現有檔案判斷做到哪，**拿不準有沒有做完的步驟就重做那一步**：

| 看到什麼 | 代表 | 接著做 |
|---|---|---|
| `facts.json`／`scripts.json` 有這集 | 查證、腳本寫完 | 重跑 `verify.py` |
| `_review/codex_handoff.md` | Claude 撞到用量上限時 **Codex 接手做過**（2026-11-24 起，Codex 全權、不上傳） | 先讀交接紀錄。**第 4 步審查改由 Claude 親自做**：逐條對 `facts.json` 原文核對事實與腳本（Codex 寫的就不再送 Codex 審）。有改腳本就重配音、重渲染、重切；第 7 步驗收一律重做 |
| `<集>/_review/` 有 Codex 審查輸出 | 審查做過 | 對照輸出確認意見已改進腳本；沒有輸出就重審 |
| `audio/l*.mp3` 齊全 | 配音做過 | 重跑 `check_vo.py`（會抓出跟現行 `say` 對不上的舊配音） |
| `renders/final_*.mp4` 比 `add_script.py` 新、長度＝原片÷倍速 | 渲染完成 | 否則重新渲染 |
| `renders/short_a.mp4` 比 `final_*.mp4` **和** `shorts.json` 都新 | 直式切好 | 否則重切（沒有 `shorts.json` 就先照第 6 步補寫）；接著做第 7 步驗收（不論之前驗過沒有都重驗） |
| `_review/` 的審查輸出比 `add_script.py` 舊、而且之後腳本有大改 | 舊審查不算數 | 重審 |

⚠️ 上片前先查頻道有沒有這集——上一輪可能已經上傳、只是沒來得及寫回 `video_id`。用 `publish.token()`（頻道擁有者授權）列出上傳播放清單，**私人與排程中的影片也會列出**；比對「標題相同、7 天內上傳」。剛好一支就把 ID 補進 `shorts.json`、**不要再傳一次**；超過一支或拿不準，照「收工回報」停下來，不上傳。

### 1. 選題：自動選題（2026-11-28 Lien：「之後短片就給你自動進行，長片再給我審題」）

**順序**：題庫「待做」那一列有標「✅核准」還沒做的，先由左到右做完；沒有了才自己選題。長片題一律不自己定，只有 Shorts 自動。

**自己選題的做法**（11-26～11-28 跟 Lien 選過三輪的方法，照做）：
1. **查熱搜**（只用 Firecrawl `firecrawl-trends`，一輪最多 25 點）：`alexandria_library_read` 跑 `trends/trending_now`（geo TW，需要外國題再加 JP 或 US），結果太大會存成檔，用 `python3` 讀檔挑「Business and Finance／Law and Government」類和跟錢有關的詞；再挑 3～5 個候選詞跑一次 `trends/interest_over_time`（geo TW、`now 7-d`）比熱度，必要時 `trends/related_queries` 找切角。⛔ 不呼叫 `firecrawl-trends` 以外的 provider。Firecrawl 回額度不足就改用 WebSearch 查新聞熱度，熱度記「未查」
2. **打分**：照 `選題參考.md` 四題打分（5 分以上才做）＋「頻道定位三問」至少過兩問
3. **排除**：下面「不做」表、跟已公開／排程中的影片比**同主題隔 14 天、同國家不連發**、**實用題（規定、申報、領錢方法）同一週（週日～週六）最多 1 支**——先用 YouTube API 列出已排程影片再判斷，不要只看題目紀錄
4. **第二意見**：前 3 名送 Codex 唯讀審一次（`env -u NODE_OPTIONS codex exec -s read-only --skip-git-repo-check -o ...`），重點是查證風險；Codex 說核心主張站不住就換下一名
5. **記錄**：選定的題寫進題庫「待做」列最前面，標「🤖自動選題（日期）」＋分數、熱度依據、三問、類型，落選的前兩名也記進去當備用
6. 選題本身不另外傳 LINE；上片時 `publish.py` 的 LINE 通知就是 Lien 喊「停」的機會

選不出 5 分以上又過得了表的題，就照最後一節收工，LINE 寫「🟡 金錢怪物 Short 這輪找不到夠格的題目」。

核准過或自選的題一樣要過下表與查證閘門；過不了就在題庫註明原因、換下一題。

題目裡寫明「**Lien 核准的例外**」的（例：ETF 分割點名基金、尚未定案的提案），那一條不做表不套用，改照題目裡寫的限制做；查證閘門照樣要過，題目裡寫「找不到就不做」的就照做（2026-11-28 加）。自動選題不能自己開例外。

**不做表**（題庫的題或自選的題都適用，任何一條中了就跳過、在題庫那題後面註明原因）：

| 不做 | 例子 |
|---|---|
| 保險、投資、理財商品 | 儲蓄險、ETF、信用卡點數比較 |
| 點名特定公司或個人 | 某銀行的分期方案 |
| 牽涉現任公職或參選人 | 候選人政見 |
| 答案取決於還沒定案的事 | 審議中的法案、未公告的費率 |
| 找不到官方原文 | 只有媒體或部落格講法 |

外國題（2026-11-18 起試）：外國那一半要有該國政府原文，台灣對照那一半要有台灣政府原文，兩邊都要。要不要放台灣對照依題目熱度彈性決定，題庫有寫就照寫的做。

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
- 畫面用 `shared/broll/` 現有素材，**不下載新素材**：台灣用 `tw_mrt`、`tw_city`、`tw_tm`、`mm_store`、`mm_laptop`、`bk_phone`、`bk_atm`；外國題用該國現有分類（日本 `jp_city`、`jp_res`、`jp_aerial`、`jp_street`），抽格確認沒有招牌價格、近距離人臉、別人的浮水印。該國沒有現成素材就跳過這題；`reject` 先抄 `ms-01`、`ms-02` 的清單再加；**🔴 一律排除 `tw_city_00`～`tw_city_07`、`tw_res_00`～`tw_res_08`（leodv999 空拍：左上原作者標誌、右下「4K」、左下地名字幕；2026-10-25 就判定不能用，但只記在記憶裡，11-19 查到 ms-01、ms-03、ms-04、tw-02、tw-03、tw-04、bn-01 都用到）**，台灣城市畫面改用 `tw_city_08`～`10`、`tw_tm`、`tw_mrt`
- `note` 固定含「資訊整理，非法律建議｜資料來源見說明欄」

### 4. 兩道閘門（都要過）

```
python3 finance_shorts/verify.py <集>
```

再把這集的事實與腳本送 Codex 唯讀審查（指令與審核清單在全域 skill `codex-delegate`，要加 `env -u NODE_OPTIONS`）。
請它找：沒對到事實的數字、被省略的條件與例外、像建議的用語、`say` 裡會唸錯的字。
逐條驗證後修正；**修完再跑一次 `verify.py`**。審查輸出存成 `<集>/_review/codex_r<輪數>.txt`（第 0 步靠它判斷做過沒有）。Codex 叫不起來就收工，不跳過這道。

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
python3 finance_shorts/publish.py <集> --short a --at "YYYY-MM-DD 18:55"
```

- **發布時間＝距離現在至少 48 小時、而且那天 18:55 還沒有其他 Short 排程的第一天（2026-11-19 Lien 定 Shorts 一律 18:55；11-22 起長片也是 18:55，長片當天不算佔用）**（先用 YouTube API 列出頻道已排程的影片再決定，不要只看 `題目紀錄.md`）。Lien 要有時間回「停」
- `publish.py` 會自己驗收並傳 LINE。回 `uploadLimitExceeded`＝今天上傳額度用完：不要重試，在題目紀錄註明「成品已完成、待上傳」，收工通知
- **上傳只跑一次**。出現「已上傳」之後的任何錯誤都不要重跑，把 video_id 手動補進 `shorts.json`

### 9. 收尾

- `題目紀錄.md`：題庫那一列改成這集的紀錄（集數、題目、事實編號、Codex 審幾條採幾條、video_id、公開時間）
- 新踩到的唸錯詞記在 `題目紀錄.md` 這集那一列（無人值守寫不進 `.claude/skills/`，要人按同意；Lien 開對話時再搬進 voice-clone skill）
- 照 `safe-commit` skill 檢查後 commit、push（只收這集的 `add_facts.py`／`add_script.py`／`shorts.json`、`facts.json`、`scripts.json`、`題目紀錄.md`）

## 收工回報（做不成的時候）

1. 不上片、不硬湊
2. `~/bin/gh workflow run line_notify.yml -f text="🔴 金錢怪物 Short 今天沒做成：<原因一句話>"`
3. 做到哪、卡在哪寫進 `題目紀錄.md`，下次開工先接著做這支
4. 最後一行輸出 `AUTO_SHORTS_RESULT: failed <原因>`

做成了，最後一行輸出 `AUTO_SHORTS_RESULT: ok <集> <video_id> <公開時間>`。
