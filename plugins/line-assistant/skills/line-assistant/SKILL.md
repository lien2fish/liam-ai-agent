---
name: line-assistant
description: 部署一個只有自己能用的 LINE AI 助理（Cloudflare Worker）。含範本連結、設定流程、LINE 平台的計費與時效規則，以及兩道非設不可的防護機制。要建 LINE bot、接 Messaging API、或排查 webhook 驗證失敗時載入。
---

# LINE AI 助理

一人專用的 LINE 助理，跑在 Cloudflare Worker 上——無伺服器、無月費、單檔無依賴。
使用者用 LINE 跟它對話、傳語音，它可以查資料、記待辦、把口述內容整理歸檔。

**這個 skill 不含程式碼。** 程式在下方的範本 repo，這裡是部署方法與安全要求。

## 範本

```
https://github.com/lien2fish/liam-ai-agent　→　line_assistant/
```

| 檔案 | 作用 |
|------|------|
| `worker.js` | 引擎，**不含任何商業資訊** |
| `profile.example.js` | 設定範本。複製成 `profile.js` 改自己的 |
| `README.md` | 完整部署步驟 |
| `導入手冊.md` | 幫別人導入時的流程與定價思路 |

設定與程式分離：改語氣、加減功能、換欄位對照**一律改 `profile.js`，不要改 `worker.js`**。
沒設定的區塊會自動關閉——工具清單與指令表都由設定組出來，
所以 Claude 不會提議做不到的事，也省下每則訊息的固定 token。

---

## ⚠️ 兩道非設不可的防護

LINE 官方帳號**任何人都能加好友**。這支 bot 查得到的東西（客戶名單、消費紀錄、
內部資料）沒有第二層保護，這兩道就是全部。**一定要實測，不能只看程式碼有寫。**

### 一、Webhook 簽章驗證

```
header: X-Line-Signature
演算法: base64( HMAC-SHA256( 原始 request body, Channel secret ) )
```

三個必須做對的地方：

| 要點 | 做錯的後果 |
|------|-----------|
| **用原始 body 字串算**，先 `JSON.parse` 再 `stringify` 就對不起來 | 永遠 403 |
| **Channel secret 沒設定時回 false**，不要寫成「比對不到才擋」 | 未設定＝全部放行 |
| 用常數時間比較 | 時序推測 |

### 二、使用者白名單

只認一個 LINE user ID（`U` 開頭 32 碼，在 Developers Console → Basic settings → Your user ID）。

**一律預設拒絕**，以下每一種都要擋下：

- 設定未填、或還是佔位字串
- **設定為空字串「且」傳來的 userId 也是空字串**（最容易寫成漏洞的一種）
- 群組訊息（有 `groupId` 但沒有 `userId`）
- userId 只是設定值的前綴

### ⚠️ user ID 不要寫進設定檔

那是綁在本人身上的識別碼。走 `wrangler secret put`，不要進版控。

### 驗收方式

程式碼有寫不算數，**要實測**：

| 測 | 預期 |
|----|------|
| 用**另一支手機**加好友傳訊息 | 完全沒反應，連錯誤訊息都不回 |
| `curl -X POST <worker>/line -d '{}'`（不帶簽章） | 403 |
| 帶偽造簽章 | 403 |

---

## LINE 平台的三個規則，會決定程式怎麼寫

先知道這些，否則會覺得某些做法很奇怪。

| 規則 | 影響 |
|------|------|
| **reply 不計額度、push 計** | 對話回覆免費無上限；只有主動推播花額度 |
| **免費額度 200 則／月**（輕用量方案，月費 0） | 約每天 6 則。推播只接失敗警報與需要決策的事 |
| **replyToken 60 秒失效、只能用一次** | 同一事件的回覆要合併成一次送出，最多 5 個 message object |

實務後果：語音訊息**不要**先回一則「聽到你說⋯」再回答案——那樣第二則得走 push
花額度。改成先亮輸入中動畫，逐字稿和答案一起送達。

AI 回覆可能超過 60 秒，要偵測逾時並自動退回 push，否則訊息會消失。

---

## 部署流程

| 步驟 | 內容 |
|------|------|
| 1 | LINE Developers Console 建 Provider → **Messaging API channel** |
| 2 | 抄 Channel secret、Your user ID、Channel access token |
| 3 | Official Account Manager：**關**自動回應訊息、**關**允許被搜尋、**開** Webhook |
| 4 | `cp profile.example.js profile.js` 並填寫 |
| 5 | `npx wrangler kv namespace create CHAT`，id 貼進 `wrangler.toml` |
| 6 | `wrangler secret put` 設定金鑰 |
| 7 | `npx wrangler deploy` |
| 8 | Webhook URL 填 `https://<worker>.workers.dev/line`（**結尾要有 `/line`**）→ Verify → 開 Use webhook |
| 9 | 加好友、實測，**包含用別支手機測擋不擋** |

### 帳號命名

取**內部用的名字**（例如「我的助理」），**不要用品牌名**。
它只認一個人、不回應任何其他人；取品牌名會讓誤加的人以為是客服帳號跑來下單。
對外的客服帳號另外開，兩者互不影響。

### 未認證帳號（灰盾）就夠

Messaging API 的功能與免費額度跟認證帳號完全一樣。
認證帳號（藍盾）的用途是讓人搜尋得到你——**私人助理正好相反**。

---

## 已知陷阱

| 症狀 | 原因 |
|------|------|
| bot 回一句、罐頭訊息又回一句 | Official Account Manager 的「自動回應訊息」沒關 |
| Verify 一直 403 | 簽章對不上：secret 設錯、或用了 parse 過的 body |
| Verify 403 但 secret 看起來有設 | **secret 可能是空字串**，見下方 |
| Webhook 完全收不到 | URL 忘了加 `/line`，或 Use webhook 沒開 |
| 語音沒反應 | 媒體要跟 `api-data.line.me` 拿（不是 `api.line.me`），大檔會先回 202 要重試，格式是 m4a |

### ⚠️ `wrangler secret put` 會靜默存成空字串

在**沒有互動終端機**的環境（例如 AI 助理的對話框、CI）執行時，
互動提示讀到空值後**照樣印出「✨ Success! Uploaded secret」**，
實際存進去的是空字串——毫無徵兆，而且所有驗證都會失敗。

**一律開真正的終端機跑。** 非互動要灌就用管線：

```bash
printf '%s' "$(tr -d '\r\n' < 金鑰檔)" | npx wrangler secret put NAME
```

本機金鑰檔通常有換行結尾，不先 `tr -d` 會讓金鑰失效。

> **診斷方式**：部署一個臨時端點，回報 `env.X` 的**長度**（不要回傳值）。
> 長度是 0 就一眼看穿。查完立刻移除。

### ⚠️ 驗證要能分辨「擋下」與「根本沒設定」

排查簽章失敗時，很容易用「拿舊 secret 打過去被擋 → 所以換發成功了」下結論。
**那證明不了任何事**——secret 是空字串時，什麼簽章都會被擋，兩者長得一模一樣。

---

## 設計上刻意不做的事

- **會同步多個系統的寫入操作**（例如建訂單）：手機上打錯字沒得檢查
- **不經確認就對外發布**：斜線指令不經過 AI、沒有確認步驟，
  而社群平台的貼文與限動發出去往往 API 刪不掉。這類任務要擋在指令層，
  只允許走自然語言路徑（由模型先跟使用者確認）

寫入型操作若真的要做，用**兩段式**：先回一份差異清單（要改什麼、從什麼變成什麼、
哪些對不上），使用者確認後才寫入。**那張差異清單就是「手機上沒得檢查」的解法。**
