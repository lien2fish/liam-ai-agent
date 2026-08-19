# Liam 手機助理（Telegram × Cloudflare Worker）

人在漁港、餐廳、客戶端時的輕量入口。**不取代 claude.ai/code**——剪片、送印、改程式那些還是要用電腦。

| 能做 | 不能做 |
|------|--------|
| 記待辦進 `TODO.md` | 跑腳本、剪片、產送印檔 |
| 口述知識存進知識庫（含語音） | 改本機檔案 |
| 查客戶、查銷售紀錄、查三品牌庫存 | 建訂單（會動到四個系統，風險太高） |
| 接收 GitHub Actions 的即時推播 | |

---

## 一次性設定（約 20 分鐘，多數步驟只有你能做）

### 1. 建 Telegram Bot

在 Telegram 找 **@BotFather** → `/newbot` → 取名（例：`Liam 助理`）→ 帳號名需以 `bot` 結尾。
記下他給的 **token**（形如 `7xxxxxxxxx:AAF...`）。

### 2. 拿你的 chat id

先對你的新 bot 傳一句「hi」，然後在瀏覽器開：

```
https://api.telegram.org/bot<你的TOKEN>/getUpdates
```

找 `"chat":{"id":123456789` —— 那串數字就是 chat id。填進 `wrangler.toml` 的 `TG_CHAT_ID`。
**這是唯一的白名單**，別人傳訊息給 bot 一律被忽略。

### 3. 建 KV 並填 id

```bash
cd telegram_bot
npx wrangler kv namespace create CHAT
```

把印出的 `id` 貼進 `wrangler.toml` 的 `[[kv_namespaces]]`。

### 4. 設定七個 secret

```bash
cd telegram_bot
npx wrangler secret put ANTHROPIC_API_KEY    # 與 GitHub Secret 同一組
npx wrangler secret put OPENAI_API_KEY       # 語音轉文字用，本機備份在 config/.openai_key
npx wrangler secret put NOTION_TOKEN         # ~/.config/notion_token
npx wrangler secret put GITHUB_PAT           # ~/.git-credentials 裡那組（需 repo scope）
npx wrangler secret put TG_BOT_TOKEN         # 步驟 1 拿到的
npx wrangler secret put TG_WEBHOOK_SECRET    # 自己隨便產一串，例：openssl rand -hex 16
npx wrangler secret put NOTIFY_TOKEN         # 同上，另產一串
```

### 5. 部署並掛上 webhook

```bash
npx wrangler deploy
```

記下網址（形如 `https://liam-assistant.lien2fish.workers.dev`），然後告訴 Telegram 往哪送：

```bash
curl -X POST "https://api.telegram.org/bot<TG_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://liam-assistant.<你的子網域>.workers.dev/tg",
       "secret_token":"<步驟4的 TG_WEBHOOK_SECRET>"}'
```

回 `{"ok":true,...}` 就成了。到 Telegram 傳「hi」測試。

### 6.（選用）打開自動化推播

把 Worker 網址與 `NOTIFY_TOKEN` 加進 GitHub Secrets（`TG_NOTIFY_URL`、`TG_NOTIFY_TOKEN`），
然後在任何 workflow 的 step 裡：

```yaml
env:
  TG_NOTIFY_URL: ${{ secrets.TG_NOTIFY_URL }}
  TG_NOTIFY_TOKEN: ${{ secrets.TG_NOTIFY_TOKEN }}
```

腳本裡 `from telegram_bot.notify import notify` 後直接呼叫。**沒設環境變數就靜默跳過**，
所以可以先加進腳本、之後再開通，不會弄壞既有流程。

---

## 成本

`MODEL` 在 `wrangler.toml` 裡，換模型只改那一行。Worker 本身在免費額度內（每天 10 萬次請求）。

**兩條路徑，只有一條花錢**（見上方「兩種模式」）。

實測每則走 AI 的訊息，固定輸入是 **1,683 token**（工具定義 1,179 ＋ 系統提示 504）——
不管你打幾個字都要送這麼多，因為 API 無狀態，每次呼叫都得重送整包 context。
斜線指令繞過這整段，成本為零。

| 模型 | 每 1M token（輸入／輸出） | 全走 AI | 混合模式（現在） |
|------|--------------------------|---------|-----------------|
| `claude-haiku-4-5`（**現在用這個**） | $1 / $5 | NT$120~180／月 | **約 NT$10／月** |
| `claude-sonnet-5` | $3 / $15 | NT$350~550／月 | 約 NT$30／月 |
| `claude-opus-5` | $5 / $25 | NT$600~900／月 | 約 NT$50／月 |

混合模式估算＝日常查詢全走指令（零成本）＋每月約 20 次自由問法＋10 次語音口述。

語音轉文字另計，OpenAI Whisper 約 $0.006/分鐘（每月 30 分鐘 ≈ NT$6）。
Cloudflare Workers AI 也有免費的 Whisper（每天 10,000 neurons 額度內），
但 OpenAI 那版可以用 `prompt` 參數餵「龜吼／現流／鑫海產」這些詞彙提高辨識率，
海鮮專有名詞差很多，暫時維持 OpenAI。

### 什麼時候該升級

Haiku 對「查客戶」「記待辦」這種明確指令綽綽有餘。**會露餡的是 `save_note`**——
把漁港錄的口語逐字稿整理成有結構的知識筆記，需要判斷什麼是重點、什麼是贅字、
專有名詞怎麼修正。看到這些訊號就換 `claude-sonnet-5`：

- 存進 `knowledge/` 的筆記像逐字稿沒整理過，或漏掉你講的關鍵數字
- 「上次那個誰」這種省略主詞的話常被誤解
- 該存知識庫的內容被丟進 TODO，或反過來

`effort` 參數由 `worker.js` 的 `EFFORT_OK` 正則依模型自動開關
（Haiku 4.5 / Sonnet 4.5 收到 `effort` 會回 400），**換模型只改 `MODEL` 一行就好**。

---

## 兩種模式

**查資料庫和寫檔案本來就不需要 AI**，需要 AI 的只是「把人話翻譯成查詢」。
願意打指令就跳過那一步，那次完全不花錢。

### 🆓 斜線指令 — 零成本

| 指令 | 簡寫 | 做什麼 |
|------|------|--------|
| `/客戶 王先生` | `/c` | 查客戶：品牌、電話、等級、累計消費、最後購買日 |
| `/買 王先生` | `/s` | 查他買過什麼（日期／品項／數量／金額，最近的在前） |
| `/庫存 白蝦` | `/i` | 查三品牌庫存（留空列全部） |
| `/待辦 下週三給張董報價` | `/t` | 寫進 `TODO.md` |
| `/筆記 內容` | `/n` | **原樣**存進 `knowledge/misc/`，不整理不分類 |

### 💰 講人話或傳語音 — 每次約 NT$0.2

- 「王先生上次買什麼」「陳老闆多久沒回購了」→ 自由問法，AI 判斷該查哪張表
- 需要跨資料判斷、你講不清楚要哪個工具時
- **語音訊息** → Whisper 轉文字 → AI 整理分類 → 存進 `knowledge/{seafood,wine,...}/`

`/筆記` 和語音的差別就在**整理**：前者原樣丟進去，後者會判斷這是海鮮還是酒、
抓出標題、把口語贅字修掉、修正專有名詞。要留給未來用的知識，值得那 0.2 元。

**在漁港挑魚時按住麥克風講十分鐘，是這個 bot 最有價值的用法。**
那些知識只在你腦裡，卡著漁船遊戲的圖鑑、IG 文案深度、影片的差異化。

記不住指令沒關係，講人話一樣通，只是那次會走 AI。`/help` 隨時看清單。

---

## 注意

- **對話記憶只留 1 小時、最近 8 輪**，且只留純文字。隔天問「昨天那個」他不會記得——
  要長期留的東西他會存進知識庫。
- **知識庫寫進私人 repo `liam-workspace`**，不會進公開的 liam-ai-agent。
- **不做建訂單**：訂單要同步 Numbers、兩個 Notion DB、統一總表四個地方，
  手機上打錯字沒得檢查。訂單還是在電腦上跑 `notion_crm/add_order.py`。
- Worker 收到 Telegram 訊息會立刻回 200 再背景處理（`ctx.waitUntil`），
  所以你會先看到「正在輸入…」，答案幾秒後才到。
