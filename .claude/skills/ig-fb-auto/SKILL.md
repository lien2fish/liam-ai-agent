---
name: ig-fb-auto
description: IG + FB 每日自動發文、IG 留言自動回覆、IG 限動 Reels 預告三套系統的維運。要改發文內容/畫圖 prompt、修留言回覆、調限動預告挑片邏輯、更新 IG Token（含 data_access_expires_at 陷阱）時載入。
---

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
1. **Claude Sonnet 5** 生成知識 JSON（5～6句＋畫圖提示詞 `illustration_prompt`，三大類：海鮮/捕魚/漁船）。`generate_knowledge()` 以 Claude 為主、Gemini 為 fallback（Claude API 當機時自動降級，當天不開天窗）。模型常數 `CLAUDE_MODEL` 在腳本頂端，省錢可改 Haiku 4.5。
   - ⚠️ **不支援 assistant message prefill**（會回 invalid_request_error），改用單一 user message＋從回應擷取 `{...}` JSON 子字串
   - ⚠️ **Sonnet 5 預設開 adaptive thinking，`content[0]` 是 thinking block 不是 text**（2026-08-19 實測 `['thinking','text']`）。**不可寫 `content[0]["text"]`**——會 KeyError。要遍歷找 `type == "text"` 的 block。`max_tokens` 也因此從 1024 提到 2048，留空間給 thinking，否則文案會被截斷
2. **OpenAI `gpt-image-1-mini`**（quality=low、1024×1024）生成圖文對應水彩插圖（吃 Claude 寫的 `illustration_prompt`）。**2026-08-06 從 Pollinations 改來**：Pollinations 轉 pollen 付費制且 flux 下架，402 被包成 HTTP 500 難辨識。模型／品質可用 `OPENAI_IMAGE_MODEL`／`OPENAI_IMAGE_QUALITY` 覆蓋。實測畫風正確、去背門檻 245>228 通過，約 $0.005/張
3. **PIL** 動態排版合成（插圖大小＋字型大小依內容量自動調整）
4. **GitHub API** 上傳圖片 → raw.githubusercontent.com 公開 URL（repo 必須 public）
5. **Meta Graph API v19.0** 同時發送：
   - IG 限時動態（`{IG_ID}/media`，media_type=STORIES，帶 `cross_post_ids={FB_PAGE_ID}`）
   - FB 限時動態透過 `cross_post_ids` 跨發，**不使用** `photo_stories`（該端點持續回傳 unknown error）

### GitHub Secrets（7個）
`ANTHROPIC_API_KEY`（文案＋畫圖prompt）/ `OPENAI_API_KEY`（生圖）/ `GEMINI_KEY`（fallback）/ `HF_TOKEN`（已停用）/ `IG_TOKEN` / `IG_ID` / `FB_PAGE_TOKEN` / `FB_PAGE_ID`

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
- IG Token 有**三種死法，不要只盯 `expires_at`**：
  | 欄位／狀況 | 現況 | 意義 |
  |------|------|------|
  | `expires_at` | **2026-10-24**（2026-08-25 換發） | token 字串本身失效 |
  | `data_access_expires_at` | **2026-11-23**（2026-08-25 重新授權 +90 天） | 到期後 API 拒絕存取資料 |
  | session 被作廢 | **無預警，隨時** | 改 FB 密碼或 Meta 安全性重設就會發生 |

  ⚠️ **「`expires_at`＝0 永不過期」已被推翻（2026-08-25）。**
  先前紀錄說 token 本身永不過期，但這次 `fb_exchange_token` 換出來的長效 token
  是 **60 天期**（`expires_in` 5183910 秒，到期 2026-10-24）。
  **不要再假設 token 永不過期**——`expires_at` 比 `data_access_expires_at` 早一個月，
  它才是先炸的那個。每次換發都用 `debug_token` 讀出實際值寫回 config，不要憑印象。

  ⚠️ **`fb_exchange_token` 換發不會重置 `data_access_expires_at`**——換出來的新 token
  到期日跟舊的完全一樣（2026-08-15 實測）。這個日期**只有使用者真的走一次授權對話框才會 +90 天**
  （2026-08-25 走完對話框，確實從 11-13 推到 11-23，＝授權當天 +90 天）。

  ⚠️ **session 被作廢（`OAuthException` code 190 / subcode 460）跟到期無關**，
  訊息是「The session has been invalidated because the user changed their password
  or Facebook has changed the session for security reasons」。
  **`fb_exchange_token` 救不回來，一定要走完整授權對話框。**
  2026-08-25 就是這樣：三套 IG 系統在到期日還有兩個多月時同時掛掉。

  更新流程見下方〈IG Token 更新步驟〉，兩個地方都要改：
  `config/instagram_config.json` 與 GitHub Secret `IG_TOKEN`

> ✅ **不用自己記日期**：`token_expiry_check.yml` 每天 08:45 問 `debug_token` 實際狀態，
> 提前 30 天起分批提醒（Email＋LINE），token 失效或缺權限當天就 🔴。
> 腳本 `scripts/token_expiry_check.py`，**不寫死到期日**，換發後不用改程式。

### IG Token 更新步驟

**首選：在 Terminal.app 跑 `python3 scripts/ig_reauth.py`**（2026-08-25 建立）

短效 token 用隱藏輸入貼進去——**不回顯、不進 shell history、不留暫存檔、不經過對話框**。
腳本會一次做完：換長效 → 驗六項權限 → 驗 `data_access_expires_at` 有往後推 →
實際打一次 API → 重簽 FB Page token → 備份並寫回 config → 更新兩個 GitHub Secret。
全程不印任何金鑰的值；到期日沒往後推會停下來問（那代表沒真的走完授權對話框）。

⚠️ **不要在 Claude Code 對話框裡跑**——沒有互動終端機，`getpass` 讀不到東西，
腳本會直接拒絕執行。**也不要請使用者把 token 貼進對話**（2026-08-25 我這樣做過，
等於讓金鑰在 transcript 裡多留一份）。

下面是手動步驟，腳本壞掉時當備援：

#### 手動步驟（2026-08-15 實跑驗證）

1. Safari 開 `https://developers.facebook.com/tools/explorer/1310018353798687/`
2. User Token → Permissions 勾滿六項：`instagram_basic` / `instagram_content_publish` /
   `instagram_manage_comments` / `pages_show_list` / `pages_read_engagement` / `pages_manage_posts`
3. Generate Access Token → 授權（已授權過要點「編輯先前的設定」確認權限都開）
4. 拿到的是**短效 token（約 1 小時）**，用 `fb_exchange_token` 換長效：
   `GET /v19.0/oauth/access_token?grant_type=fb_exchange_token&client_id=<app_id>&client_secret=<app_secret>&fb_exchange_token=<短效>`
5. `debug_token` 驗證 **`data_access_expires_at` 確實往後推了**（這是唯一的驗收條件）
6. 寫回 `config/instagram_config.json`（先備份）＋ 用 PyNaCl `SealedBox` 更新 Secret `IG_TOKEN`
   - GitHub PAT 只在 **keychain**（2026-08-27 起明文檔已刪；**不在** remote URL，remote 是乾淨的 https）

> 這組 token 由三套系統共用：限動預告、IG 留言自動回覆（每 5 分鐘）、IG+FB 每日發文（每天 08:00）。過期會一起掛掉。
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
- **IG Token：`expires_at` 2026-10-24 先到期**，「資料存取權」2026-11-23 才到期
  （2026-08-25 重新授權後 +90 天）。**以早的那個為準，10 月中就該重跑一次**上方〈IG Token 更新步驟〉。
  ⚠️ 也可能在到期前就因 session 被作廢而提前掛掉（見上方 190/460）
- **FB Page Token：`expires_at`＝0，但不等於不會失效**——2026-08-25 隨 user session
  被作廢一起死（同 190/460）。重簽很快：拿新的 user token 打 `GET /{page-id}?fields=access_token`。
  ⚠️ 目前**沒有腳本真的用到它**（FB 跨發走 IG 的 `cross_post_ids`），所以它死掉不會有功能症狀，
  只有 `token_expiry_check` 會抓到
- 更新 Token 方式：用 `nacl.public.SealedBox` 直接寫入 GitHub Secret（系統 PyNaCl 1.6.2 已支援）
- **GitHub PAT（舊）：2026-08-15 到期** — 已廢棄，改用新 PAT
- **GitHub PAT（新）：永不過期**，含 `repo` + `workflow` scope，**只存在 macOS keychain**
  （2026-08-27 移除 local 的 `store` helper 並刪掉 `~/.git-credentials` 明文檔）。
  （**不是** remote URL，remote 已改回乾淨的 https）
  ⚠️ 取用一律 `git credential fill`，寫法見 `secrets-ops` skill
  ⚠️ 缺 `read:org`，`gh auth login` 會拒收——`~/bin/gh` 是注入 `GH_TOKEN` 的 wrapper，見 CLAUDE.md

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

## IG 限動預告（Reels 導流，2026-08-16 已自動化）

從**已發布的 Reels** 剪 3 秒預告貼限時動態，結尾標「Reels完整版～」。
帳號 `lienstable`（連老闆｜產地到餐桌）。

| 項目 | 說明 |
|------|------|
| 腳本 | `instagram/story_teaser.py`（`--dry-run` 只剪不發）|
| 排程 | `.github/workflows/ig_story_teaser.yml`，每天 **18:05 台灣**（Reels 固定 18:00 落地，隔 5 分鐘接上）|
| 選片紀錄 | `instagram/story_teaser_state.json`（workflow 自動 commit）|
| 影片暫存 | `instagram/stories/`，發完自動刪掉前一支（每天約 6MB，不清會撐爆 public repo）|

**挑片**＝取「30 天內沒用過」的 Reels 中**最新的一支**——新片優先，用完才往回翻舊片。

**挑片段**＝把可用區間切三等分，每段抽 6 個候選格算**梯度能量**取最銳利的。
⚠️ 這步不能省：改用等距取樣實測會挑到運鏡糊掉的畫面與靜態解說牌。

⚠️ **18:05 是目標不是保證**：GitHub 排程常誤點（同 `ig_comment_reply` 的 1.5~4 小時），
真的很在意分秒就得手動觸發。誤點不會壞掉——若新 Reel 還沒上，挑片邏輯會自動退回舊片，
隔天新片仍在「30 天內沒用過」名單裡，不會漏掉。

### 規格（使用者定案）

| 項目 | 規則 |
|------|------|
| 長度 | **正好 3.00 秒**——使用者要求「最多 3 秒」，而 IG 限動影片**最短也是 3 秒**，只有這個值同時成立 |
| 結構 | **不同片段拼接**（目前用 3 段，約 1 秒／段），怎麼切由我決定 |
| ⚠️ 必須跳過 | **開頭的封面／標題卡**與**結尾的訂閱卡**，只取中間內容——標題卡會把梗一次講完，預告就失去意義 |
| 標記 | 「Reels完整版～」黃字深底膠囊，**燒進畫面**、置中 y≈1430（IG 上下各約 250px 是 UI 安全區）|
| 選片 | 同一支 Reel **至少一個月內不可重複** |

### 流程

1. 取素材：`GET /{ig-user-id}/media?fields=media_url` → **已發布 Reels 可直接下載 mp4**，
   不需要外接硬碟（目前 60 支可選）
2. ffmpeg 切段 → **concat filter** 合併 → overlay 標記 → 3.0 秒
3. 上傳到 repo `instagram/stories/` 取得 `raw.githubusercontent.com` 公開網址
4. `POST /{ig-user-id}/media`（`media_type=STORIES`, `video_url=…`）→ 輪詢 `status_code`
   到 `FINISHED` → `POST /{ig-user-id}/media_publish`

### ⚠️ 地雷

- **發布後刪不掉**：Graph API 只能建立、不能刪除媒體（`DELETE` 回 `(#10) Insufficient
  permissions`，是平台限制不是權限沒勾）。**發之前一定要先抽格預覽確認**，發錯只能請使用者到 App 手動刪
- **驗收方式**：發完用 `GET /{media-id}?fields=media_url` 把限動抓回來抽格比對，
  確認發出去的真的是想發的那支——別只看 API 回 200
- **`concat` demuxer 的時間戳不連續**：三段接起來後每段都從 0.04 重新計時，
  `overlay=…:enable='gte(t,N)'` 因此永遠不觸發，**字卡沒疊上去也不會報錯**。
  改用 **concat filter**（每段當獨立輸入）才正常
- **`-t` 要放在 `-i` 之後**：放前面是「輸入讀取長度」，不會確實截斷輸出（實測 1.0 秒切成 1.83 秒）
- **`raw.githubusercontent.com` 覆蓋同一路徑有 CDN 快取延遲**：HEAD 可能還回舊檔大小。
  不要據此判定失敗，以「抓回已發布的限動比對」為準
- **API 加不了互動貼紙**（連結／Reels／@提及），所以「Reels完整版～」**點不下去**，
  觀眾得自己去主頁找。要可點的只能在 App 手動「分享 → 新增到限時動態」

---
