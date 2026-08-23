# LINE 手機助理（Cloudflare Worker）

**一人專用的 LINE 助理**：查自己的資料庫、記待辦、口述存知識庫、看自動化有沒有掛。
跑在 Cloudflare Worker 上，無伺服器、無月費、單檔無依賴。

人在外面時的輕量入口，不取代電腦——剪片、送印、改程式那些還是要用電腦。

| 能做 | 不能做 |
|------|--------|
| 記待辦進 `TODO.md` | 跑腳本、剪片、產送印檔 |
| 口述知識存進知識庫（含語音） | 改本機檔案 |
| 查客戶、查銷售紀錄、查三品牌庫存 | 建訂單（會動到四個系統，風險太高） |
| 觸發 12 個查詢類 GitHub Actions | 用指令觸發**會對外發布**的任務（見下方） |
| 接收 GitHub Actions 的即時推播 | |

## 設定與程式分離

`worker.js` **不含任何商業資訊**。身分、品牌、資料庫欄位、自動化任務全部從
`profile.js` 讀。要導入新使用者只要複製 `profile.example.js` 改成 `profile.js`，
程式碼一行不動。

**沒設定的區塊會自動關掉對應功能**——沒有 Notion 就不會出現查客戶的指令，
沒有 GitHub Actions 就不會出現 `/跑` 和 `/查`，連 Claude 的工具清單裡都不會有，
所以它不會提議做不到的事，也省下每則訊息的固定 token。

---

## LINE 的三個規則，決定了這支程式長什麼樣

看設定步驟之前先知道這些，否則會覺得某些做法很怪。

| 規則 | 影響 |
|------|------|
| **reply 訊息不計額度，push 計** | 你跟它對話**完全免費、無上限**；只有自動化推播花額度 |
| **免費額度 200 則／月**（輕用量方案，月費 0 元） | 約每天 6 則，推播要克制。中用量 NT$800／月給 3,000 則 |
| **replyToken 60 秒失效、只能用一次** | 同一則訊息的回覆必須合併成一次送出，最多 5 段 |

所以語音訊息**不會**先回一則「聽到你說⋯」再回答案——那樣第二則要走 push 花額度。
改成先亮「輸入中」動畫，然後逐字稿和答案一起送達。

---

## 一次性設定（約 30 分鐘）

### 1. 建 LINE 官方帳號與 Messaging API channel

到 [LINE Developers Console](https://developers.line.biz/console/)：

1. 建 **Provider**（隨便取，通常是公司名）
2. 建 **Messaging API channel**——這會同時產生一個 LINE 官方帳號
3. 帳號名稱取**內部用的**

> ⚠️ **不要取品牌名。** 取品牌名會讓誤加的人以為是客服帳號跑來下單，
> 而它只認你一個人、不會回應任何人。對外的客服帳號請另外開，兩者互不影響。

從 console 抄三樣東西：

| 位置 | 要抄什麼 |
|------|---------|
| Basic settings | **Channel secret** |
| Basic settings | **Your user ID**（`U` 開頭 32 碼，這就是步驟 7 要的） |
| Messaging API | **Channel access token（long-lived）**，沒有就按發行 |

### 2. 關掉會打架的預設行為

到 [LINE Official Account Manager](https://manager.line.biz/) → 設定：

| 設定 | 改成 | 為什麼 |
|------|------|--------|
| 自動回應訊息 | **關閉** | 不關的話你的 bot 回一句、LINE 罐頭再回一句 |
| 加入好友的歡迎訊息 | **關閉** | 同上 |
| Webhook | **開啟** | 不開你的程式收不到訊息 |
| **允許被搜尋** | **關閉** | 別人搜不到，只有拿 QR code 才加得到 |

> 就算被加好友也沒關係——程式只認你的 user ID，其他人傳訊息會被靜默忽略，
> 連錯誤訊息都不會回。關閉搜尋只是少一層打擾。

### 3. 改設定檔

```bash
cp profile.example.js profile.js
```

打開 `profile.js`，填你的身分、事業描述、資料庫欄位、自動化任務。
每個區塊都有註解說明；用不到的留空即可。

### 4. 建 KV（存 1 小時對話記憶）

```bash
cd line_assistant
npx wrangler kv namespace create CHAT
```

把印出的 `id` 貼進 `wrangler.toml` 的 `[[kv_namespaces]]`。

### 5. 設定八個 secret

```bash
cd line_assistant
npx wrangler secret put ANTHROPIC_API_KEY    # Claude 對話
npx wrangler secret put OPENAI_API_KEY       # 語音轉文字（Whisper）
npx wrangler secret put NOTION_TOKEN         # 查資料庫，沒用到 Notion 可略過
npx wrangler secret put GITHUB_PAT           # 需 repo scope，沒用到可略過
npx wrangler secret put LINE_USER_ID         # 步驟 1，Basic settings → Your user ID
npx wrangler secret put LINE_CHANNEL_SECRET  # 步驟 1，Basic settings
npx wrangler secret put LINE_ACCESS_TOKEN    # 步驟 1，Messaging API 分頁
npx wrangler secret put NOTIFY_TOKEN         # 自己產一串：openssl rand -hex 16
```

> ⚠️ **一律走 `wrangler secret put`，不要寫進任何檔案。**
>
> ⚠️ **一定要在真正的終端機跑。** 在沒有互動 TTY 的環境（例如 AI 助理的對話框）
> 提示會讀到空值、存成**空字串**，然後照樣印「✨ Success」——毫無徵兆。
> 非互動要灌就用管線：
> ```bash
> printf '%s' "$(tr -d '\r\n' < 金鑰檔)" | npx wrangler secret put NAME
> ```
> 本機金鑰檔通常有換行結尾，不先 `tr -d` 會讓金鑰失效。

### 6. 第一次部署

```bash
npx wrangler deploy
```

記下網址（形如 `https://<worker名稱>.<你的子網域>.workers.dev`）。

此時 `LINE_USER_ID` 還是佔位符，程式會**擋掉所有人**（包含你自己）——這是刻意的，
確保在白名單設好之前，沒有任何人能碰到客戶資料。

### 7. 掛 webhook

回 LINE Developers Console → Messaging API 分頁 → Webhook URL 填：

```
https://<worker名稱>.<你的子網域>.workers.dev/line
```

**注意結尾是 `/line`。** 填好按 **Verify**，要回 Success。
（Verify 送的是假 token，程式會認出來並略過，不會出錯。）

再確認 **Use webhook** 是開啟的。

### 8. 確認白名單已設定

`LINE_USER_ID` 在步驟 5 就用 `wrangler secret put` 設好了。

> ⚠️ **不要把 user ID 寫進 `wrangler.toml`。** 這個 repo 是公開的，
> user ID 是綁在你本人身上的識別碼。走 secret 不會進版控。

抄不到 user ID 的話：用手機加官方帳號好友（Messaging API 分頁有 QR code），傳一則訊息，
同時跑 `npx wrangler tail`。白名單還沒設定時，程式會把收到的 userId 印出來給你抄。
**一旦設定好，就不再記錄任何人的 ID。**

設好 secret 後重新部署：

```bash
npx wrangler deploy
```

### 9. 測試

用手機**加官方帳號好友**（沒加就沒有聊天視窗），然後：

| 測 | 預期 |
|----|------|
| 傳「hi」 | 回你話 |
| 打 `/help` | 出現指令清單 |
| 打 `/i` | 列出三品牌庫存 |
| 傳一段語音 | 先亮輸入中動畫，然後回逐字稿＋回應 |
| 打 `/跑 IG發文` | **被擋下**，告訴你這個不能用指令跑 |

### 10.（選用）打開自動化推播

把 Worker 網址與 `NOTIFY_TOKEN` 加進 GitHub Secrets（`LINE_NOTIFY_URL`、`LINE_NOTIFY_TOKEN`），
然後在 workflow 的 step 裡：

```yaml
env:
  LINE_NOTIFY_URL: ${{ secrets.LINE_NOTIFY_URL }}
  LINE_NOTIFY_TOKEN: ${{ secrets.LINE_NOTIFY_TOKEN }}
```

腳本裡 `from line_assistant.notify import notify` 後直接呼叫。**沒設環境變數就靜默跳過**，
所以可以先加進腳本、之後再開通，不會弄壞既有流程。

> ⚠️ **推播計入 200 則／月的免費額度**（約每天 6 則）。
> 只接「失敗警報」與「需要你決策的事」，成功訊息不要推——
> 17 個 workflow 全接會是每月 500＋ 則，直接爆掉。

---

## 兩種模式

**查資料庫和寫檔案本來就不需要 AI**，需要 AI 的只是「把人話翻譯成查詢」。
願意打指令就跳過那一步，那次完全不花錢。

### 🆓 斜線指令 — 零成本

| 指令 | 簡寫 | 做什麼 |
|------|------|--------|
| `/客戶 王先生` | `/c` | 查客戶：品牌、電話、等級、累計消費、最後購買日 |
| `/買 王先生` | `/s` | 查他買過什麼（日期／品項／數量／金額，最近的在前） |
| `/庫存 關鍵字` | `/i` | 查庫存（留空列全部）|
| `/待辦 內容` | `/t` | 寫進 `TODO.md` |
| `/筆記 內容` | `/n` | **原樣**存進 `knowledge/misc/`，不整理不分類 |
| `/跑 市場日報` | `/r` | 立刻跑一次 GitHub Actions 任務 |
| `/查 自動化` | `/k` | 看排程任務有沒有掛（純唯讀，不觸發）|

### ⛔ `/跑` 不接受會對外發布的任務

斜線指令**直接執行、不經過 AI，沒有任何確認步驟**。所以這四個一律擋下：

`IG發文`、`IG留言回覆`、`限動預告`、`YouTube影片`

**IG 限動發出去 API 刪不掉**，手機誤觸或選單點錯的代價收不回來。
真的要發就**用講的**（Claude 會先跟你確認），或到電腦上跑。

其餘 12 個查詢類任務照常：市場日報、漁獲行情、保單到期、回購提醒、生日提醒、
壽險拜訪、扶輪生日、營收週報、YouTube留言、頻道日報、Gmail清理、月報。

### `/查` 回報什麼

四種狀態，只列出需要你注意的，正常的只給總數：

| 標記 | 意思 |
|------|------|
| ❌ 有問題 | 最後一次執行失敗 |
| ⚠️ 不穩定 | **最後一次成功，但最近 5 次裡有失敗**——這種最容易被漏掉 |
| ⏳ 執行中 | 還沒跑完 |
| ⚪️ 沒跑過 | 從未執行 |

「不穩定」是刻意加的：只看最後一次的話，時好時壞的任務會顯示成正常。
實際上 實務上就遇過某個月報最近 5 次失敗 3 次，卻因最後一次成功而被歸類為健康。

**主動問比推播划算**：問它走 reply（不計額度、無上限），推播走 push
（計入 200 則／月）。想知道才問，不會變成雜訊。

### 💰 講人話或傳語音 — 每次約 NT$0.2

- 「王先生上次買什麼」「陳老闆多久沒回購了」→ 自由問法，AI 判斷該查哪張表
- 需要跨資料判斷、你講不清楚要哪個工具時
- **語音訊息** → Whisper 轉文字 → AI 整理分類 → 存進 `knowledge/{seafood,wine,...}/`

`/筆記` 和語音的差別就在**整理**：前者原樣丟進去，後者會判斷這是海鮮還是酒、
抓出標題、把口語贅字修掉、修正專有名詞。要留給未來用的知識，值得那 0.2 元。

**按住麥克風講十分鐘，是這個 bot 最有價值的用法。**
你這行的判斷方法、經驗法則、產地知識——那些只在你腦裡，打字打不出來，
但用講的十分鐘就有了。`profile.js` 的 `vocabulary` 填上你這行的專有名詞，
辨識率差很多。

記不住指令沒關係，講人話一樣通，只是那次會走 AI。`/help` 隨時看清單。

---

## 成本

`MODEL` 在 `wrangler.toml` 裡，換模型只改那一行。Worker 本身在免費額度內（每天 10 萬次請求）。
LINE 官方帳號輕用量方案月費 0 元，且**對話回覆不計額度**，所以固定成本是零。

實測每則走 AI 的訊息，固定輸入是 **1,683 token**（工具定義 1,179 ＋ 系統提示 504）——
不管你打幾個字都要送這麼多，因為 API 無狀態，每次呼叫都得重送整包 context。
斜線指令繞過這整段，成本為零。

| 模型 | 每 1M token（輸入／輸出） | 全走 AI | 混合模式（現在） |
|------|--------------------------|---------|-----------------|
| `claude-haiku-4-5`（**現在用這個**） | $1 / $5 | NT$120~180／月 | **約 NT$10／月** |
| `claude-sonnet-5` | $3 / $15 | NT$350~550／月 | 約 NT$30／月 |
| `claude-opus-5` | $5 / $25 | NT$600~900／月 | 約 NT$50／月 |

> ⚠️ 以上皆為**估算**，這套尚未實際運行過，不是實測值。
> 混合模式估算＝日常查詢全走指令（零成本）＋每月約 20 次自由問法＋10 次語音口述。

語音轉文字另計，OpenAI Whisper 約 $0.006/分鐘（每月 30 分鐘 ≈ NT$6）。
Cloudflare Workers AI 也有免費的 Whisper（每天 10,000 neurons 額度內），
但 OpenAI 那版可以用 `prompt` 參數餵行業專有名詞提高辨識率，差很多，
所以預設用 OpenAI。

### 什麼時候該升級

Haiku 對「查客戶」「記待辦」這種明確指令綽綽有餘。**會露餡的是 `save_note`**——
把口述的逐字稿整理成有結構的知識筆記，需要判斷什麼是重點、什麼是贅字、
專有名詞怎麼修正。看到這些訊號就換 `claude-sonnet-5`：

- 存進 `knowledge/` 的筆記像逐字稿沒整理過，或漏掉你講的關鍵數字
- 「上次那個誰」這種省略主詞的話常被誤解
- 該存知識庫的內容被丟進 TODO，或反過來

`effort` 參數由 `worker.js` 的 `EFFORT_OK` 正則依模型自動開關
（Haiku 4.5 / Sonnet 4.5 收到 `effort` 會回 400），**換模型只改 `MODEL` 一行就好**。

---

## 安全邊界

這支 bot 查得到**客戶姓名、電話、消費紀錄**，而 LINE 官方帳號誰都能加好友。
所以兩道驗證都是**預設拒絕**——設定沒填、header 沒帶、格式不對，一律擋下：

| 情境 | 行為 |
|------|------|
| `LINE_USER_ID` 沒填或還是 `PUT_` 佔位符 | 擋下所有人（含你自己） |
| `LINE_USER_ID` 空字串**且**傳來的 userId 也空 | 擋下（最容易寫成漏洞的情境） |
| 群組訊息（有 groupId 無 userId） | 擋下 |
| `LINE_CHANNEL_SECRET` 沒設 | 拒收所有 webhook |
| 簽章對不上、body 被竄改 | 拒收 |
| 別人加好友後傳訊息 | 靜默忽略，不回任何東西 |

比對使用常數時間，避免時序推測。共 26 項邊界測試涵蓋以上情境。

---

## 注意

- **對話記憶只留 1 小時、最近 8 輪**，且只留純文字。隔天問「昨天那個」他不會記得——
  要長期留的東西他會存進知識庫。
- **知識庫寫進 `profile.js` 指定的 repo，務必用私人 repo**——那裡會累積你的商業知識。
- **不做建訂單**：訂單要同步 Numbers、兩個 Notion DB、統一總表四個地方，
  手機上打錯字沒得檢查。訂單還是在電腦上跑 `notion_crm/add_order.py`。
- Worker 收到 LINE 訊息會立刻回 200 再背景處理（`ctx.waitUntil`），
  所以你會先看到輸入中動畫，答案幾秒後才到。
- **Claude 回覆超過 50 秒**，replyToken 會過期，程式自動改走 push（花一則額度）。
  斜線指令不會發生這種事。
- 輸入中動畫的端點名稱有兩種寫法流通，程式包在 try/catch 裡——
  **萬一寫錯只是沒有動畫，不影響功能**。`worker.js` 的 `lineLoading()` 留了 TODO。
