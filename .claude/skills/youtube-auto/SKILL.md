---
name: youtube-auto
description: 全自動 AI 影片頻道：The Unknown Hour（宇宙／古文明未解之謎，腳本+生圖+配音+上傳全自動）與 Finn's Why（兒童 3D 動畫）。要改風格、調節奏、修生圖或字幕、處理發布排程時載入。
---

## YouTube 自動 Shorts 頻道系統（2026-06-28 建立）

### 定位
全新**無人臉 AI 頻道**，主題 **宇宙未解之謎 + 古代文明之謎 + 激發好奇心**（2026-06-29 從療癒系改回神秘方向；療癒系曾於 06-28 試做後捨棄）。電影感寫實畫面、沉穩英文男聲、繁中字幕、史詩氛圍。架構複用 IG 發文系統。
- 風格參數在 `build_video.py`：`VOICE`(en-US-GuyNeural 沉穩男聲)、`RATE`(-3%)、`gen_image` 畫風(cinematic/epic/photoreal/dramatic)、Ken Burns(0.0004→1.10)。要再換方向只改這幾處＋`generate_script` 的 prompt
- **長片自訂縮圖**（2026-06-30 加）：16:9 長片自動產 1280×720 縮圖（`make_thumbnail`：中段場景圖+底部漸層+左下大標題+金色重點條），存 workdir/thumb.png，`upload.set_thumbnail` 上傳後設定。Shorts 用影格不需。**需頻道完成電話驗證**才能設自訂縮圖，失敗會 try/except 記 log 不中斷
- **開場標題卡**（2026-06-29 加）：影片最前 `INTRO_DUR`(4.5s) 顯示——暗化的首張場景 ＋ 吸睛英文標題(`title`) ＋ 金色分隔線 ＋ 中文主題介紹(`intro_zh`，Claude 新增欄位)。`make_title_card`(PIL) + `title_card_clip`(ffmpeg zoom+fade)；字幕時間後移 INTRO_DUR、旁白用 `adelay` 延後，BGM 從頭播
- **固定收尾角色**：`MASCOT_SCENE`＝大角鴞(琥珀眼、滿月星空、面向觀眾如要透露秘密)，每支影片結尾自動 append 一張「對你說話」的角色圖（靜態圖+輕推鏡，非真對嘴；真lip-sync需Kling無法全自動）
- **聲線**：旁白加 `aecho` 殘響+highpass（宇宙回音/份量感）
- **BGM**：`youtube_auto/bgm.mp3`（ffmpeg 生成的低沉神秘氛圍 drone，可換無版權音樂或 `YT_BGM` 指定），`amix` 低音量(0.16)混入；輸出 44.1kHz 立體聲。**注意：這版 ffmpeg 的 `tremolo` filter 會 exit 222（Result too large），生成 BGM 別用 tremolo**
- **長度＝2～3 分鐘一般影片**：`generate_script` prompt 要 18-24 句、10-14 場景、290-380字；`max_tokens`=3000；`make_and_upload` 無 `#shorts`。改長度調 prompt 句數/場景數。**生圖約 15~18 秒/張**（OpenAI，實測）：本機約 5 分鐘/支，workflow `timeout-minutes` 已調 30，尚有餘裕
- **生圖容錯**：單張最終失敗不中止，沿用前一張場景圖（首張才用 `_placeholder_image` 備援底圖），吉祥物結尾同理。**但過半場景失敗即 `raise` 中止**（2026-08-06 加）——⚠️ 原本只有「沿用前一張」沒有底線，08-05 Pollinations 全掛時產出**整支同一張底圖的影片、workflow 還回報 success 並照排程自動公開**，這種「假成功」比明顯失敗更難發現。重試只在 408/429/5xx，4xx（認證／額度／內容政策）直接中止並印出狀態碼
- **約隔兩天發一支**（2026-08-06 改，`SHORT_WEEKDAYS={1,4}`／`LONG_WEEKDAYS={6}`）：`make_and_upload.formats_for_today()` 決定當天產出——**Shorts(9:16, ~50秒, 6-8句)週二、週五；長片(16:9, 2-3分鐘, 18-24句)週日**，一週三支，其餘日子直接跳過不製作。要改節奏只動這兩個常數（週一=0），並同步改 `main()` 裡「今天非發片日」那行提示字。可用 `YT_FORMAT=long/short` 手動覆寫成只產一支。多格式日各格式跑獨立 subprocess（避免 build_video 模組級 `YT_ASPECT` 只在 import 時生效）；make_and_upload 設好 `YT_ASPECT` 後才 import build_video；short 模式自動加 `#shorts`、開場卡縮短為 3s。workflow `timeout-minutes` 已提到 55（兩支影片）
- **影片比例**：`YT_ASPECT`（16:9=1920×1080 / 9:16=1080×1920）。W/H、生圖尺寸、Ken Burns、字幕字級(16:9=54/9:16=60)與位置、開場卡時長皆隨比例自動調整

### 模組 `youtube_auto/`
| 檔案 | 職責 |
|------|------|
| `generate_script.py` | **Claude Sonnet 5** 生英文腳本 JSON（title/narration/scenes/description/tags/topic），主題去重 `recent_topics.json`。**2026-07-25 加 Gemini fallback**（Claude 重試3次仍失敗→降級 2.5-flash→2.0-flash→2.0-flash-lite），避免 API 額度耗盡/當機時整支影片開天窗；workflow 需帶 `GEMINI_KEY`。⚠️ **Sonnet 5 預設開 adaptive thinking，`content[0]` 是 thinking block**——不可寫 `content[0]["text"]`（KeyError），要遍歷找 `type == "text"`；`max_tokens` 4096→8192 留空間給 thinking |
| `build_video.py` | **OpenAI `gpt-image-2`**（2026-09-05 從 `gpt-image-1-mini` 遷移，舊模型 12/01 停用）生10-14張電影感插圖 ＋ **edge-tts**英文配音 ＋ ffmpeg Ken Burns ＋ 燒錄字幕 → 1080×1920 MP4。⚠️OpenAI 只接受 1024²/1024×1536/1536×1024，與影片比例對不上，`_fit_to_frame()` 置中裁切後縮放（16:9 與 9:16 各裁掉約16%，實測構圖安全） |
| `upload.py` | YouTube Data API v3 resumable 上傳（OAuth refresh token，純 urllib） |
| `make_and_upload.py` | 每日進入點：生腳本→產影片→上傳→記錄去重 |
| `oauth_setup.py` | 一次性取得 refresh token（手動授權流程，同 Gmail） |
| `SETUP.md` | 一次性人工設定步驟（建頻道/OAuth/Secrets） |

### 排程與發布
⛔ **2026-09-05 停排程（Lien 指示）。** 從 `scheduler_worker/worker.js` 的 `SCHEDULE`
拿掉 02:07，同時從 `AUDITS["02:30"]` 拿掉該時段（留著會每天誤報「沒執行」）。
`yt_auto_post.yml` 本身與程式全部保留，要跑走 `workflow_dispatch`；要恢復就把兩處加回去。

停的理由是實測數據：開台 66 天（06-30→09-03）只到 **11 訂閱／2,738 觀看**，
最近 19 天僅 +1 訂閱、近期 12 支影片留言全 0，題材與五個品牌零關聯。
對照組——泥馬的真心話開台 20 天就到 5,431 觀看，單支最高 2,383。

（先前這裡寫「2026-08-26 起全部暫停」是過期的：當天暫停半天後即恢復，
排程一直掛在 Worker 上跑到 09-05。）**下面是停排程前的運作方式，恢復時照這個看。**

`.github/workflows/yt_auto_post.yml`，每天 10:00 台灣（UTC 02:00）**製作並上傳**影片，用 YouTube 排程發布（`status.publishAt`）設**當天 18:00 台灣自動轉公開**。

⚠️ 暫停排程**不影響已上傳且排定稍後公開的影片**，它們照樣會到點公開。
要一併攔下必須到 YouTube Studio「內容 → 已排程」手動改。
⚠️ 上傳用的 OAuth scope 只有 `youtube.upload`，**讀不了頻道清單**（列出已排程影片會回 403），
所以這件事沒辦法用程式查，只能開 Studio。
- 控制：workflow env `YT_PUBLISH_HOUR='18'`（台灣整點，有設＝排程發布、影片先 private 屆時自動公開；不設則用 `YT_PRIVACY`）
- `make_and_upload.scheduled_publish_at()` 算 publishAt；`upload.upload(publish_at=...)` 帶入。**頻道＝Finn's Why**（2026-06-29 已完成 OAuth＋3個 Secret＋測試上傳確認）

### 需新增 GitHub Secrets（共用 ANTHROPIC_API_KEY 與 OPENAI_API_KEY；HF_TOKEN 已停用）
`YT_OAUTH_CLIENT_ID` / `YT_OAUTH_CLIENT_SECRET` / `YT_OAUTH_REFRESH_TOKEN`（scope: `youtube.upload`）

### 重要技術細節
- **字幕為繁體中文、旁白為英文**（2026-06-28 使用者指定中文字幕；標題/描述維持英文利全球 SEO）
- **逐句配音對齊**：`generate_script` 讓 Claude 同時產 `sentences:[{en,zh}]`；`build_video.synth_sentences` 逐句 edge-tts 配音→量測時長→串接，取得每句精確時間，中文字幕(zh)據此對齊（比 edge-tts 的 SentenceBoundary 更穩，edge-tts 7.2.8 預設只回句邊界非字邊界）
- **CJK 字型**：`CJK_FONT` mac 用 `Heiti TC`、Linux 用 `Noto Sans CJK TC`；workflow 需 `apt install fonts-noto-cjk`
- 字幕字級 60、CJK 依字數切（每段16字）、拉丁依詞數切（每段8詞）——字小、每次顯示字數多（2026-06-29 調）
- 本機 evermeet 版 ffmpeg **無 ffprobe**：`get_duration` 改用 `ffmpeg -i` 解析 Duration（雲端 apt 版有 ffprobe 不受影響）
- **OAuth 同意畫面須發布 Production**，否則 refresh token 每 7 天失效（同 Gmail OAuth 雷）
- 憑證 `config/youtube_client.json`、`config/youtube_oauth.json` 已被 config/ gitignore 保護
- 本機已驗證：完整產出帶字幕 MP4（Pollinations插圖+配音+Ken Burns 皆正常）
- **一次性人工步驟**（無法自動化）：建 YouTube 頻道、Google Cloud OAuth、首次授權，見 `youtube_auto/SETUP.md`
- 變現非保證：YPP 門檻 1,000 訂閱 + 90天1,000萬 Shorts 觀看，且需原創價值避開低品質AI內容政策


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
