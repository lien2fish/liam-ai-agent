# IG 自動回覆系統 — 部署步驟

## 架構
```
用戶留言/限動回覆
    ↓
Meta Webhook → Cloudflare Workers → Gemini 2.0 Flash 生成回覆
                                  → Meta Graph API 發送回覆
```

---

## Step 1：安裝 Wrangler

```bash
npm install -g wrangler
wrangler login   # 會開瀏覽器登入 Cloudflare
```

---

## Step 2：設定 Secrets

```bash
cd "/Users/lien/Downloads/Liam AI agent/instagram/auto_reply"

wrangler secret put VERIFY_TOKEN
# 輸入任意字串，例如：liam_ig_webhook_2026（記住，Meta 設定時要填）

wrangler secret put IG_TOKEN
# 貼上 GitHub Secret 裡的 IG_TOKEN 值

wrangler secret put IG_ID
# 貼上 GitHub Secret 裡的 IG_ID 值

wrangler secret put GEMINI_KEY
# 貼上 GitHub Secret 裡的 GEMINI_KEY 值
```

---

## Step 3：部署

```bash
wrangler deploy
```

部署完成後記下 Worker URL，格式：
`https://ig-auto-reply.{你的subdomain}.workers.dev`

---

## Step 4：確認 IG Token 權限

目前 token 需要包含以下權限（在 Meta Graph API Explorer 確認）：

| 權限 | 用途 |
|------|------|
| `instagram_manage_comments` | 回覆留言 |
| `instagram_manage_messages` | 回覆私訊/限動 |
| `instagram_basic` | 讀取基本資訊 |
| `pages_messaging` | 透過 Page 發訊 |

**檢查方式**：
```
GET https://graph.facebook.com/debug_token
   ?input_token={IG_TOKEN}
   &access_token={IG_TOKEN}
```

若缺少 `instagram_manage_messages`，需重新從 Meta Graph API Explorer 取得含該權限的 token。

---

## Step 5：在 Meta App 設定 Webhook

1. 進入 [Meta for Developers](https://developers.facebook.com) → Liam AI App
2. 左側選單 → **Webhooks**
3. 選擇 **Instagram** → **Subscribe to this object**
4. 填入：
   - **Callback URL**：`https://ig-auto-reply.{subdomain}.workers.dev/webhook`
   - **Verify Token**：Step 2 設定的 `VERIFY_TOKEN` 值
5. 點 **Verify and Save**
6. 訂閱欄位：勾選 **`comments`** 和 **`messages`**

---

## Step 6：測試

```bash
# 測試 Webhook 驗證
curl "https://ig-auto-reply.{subdomain}.workers.dev/webhook?hub.mode=subscribe&hub.verify_token=你的VERIFY_TOKEN&hub.challenge=test123"
# 應回傳：test123

# 查看 Worker 即時 Log
wrangler tail
```

然後去 IG 帳號的貼文下留言，或回覆限時動態，觀察是否自動回覆。

---

## 日後維護

| 操作 | 指令 |
|------|------|
| 查看即時 log | `wrangler tail` |
| 更新 worker | 修改 worker.js 後 `wrangler deploy` |
| 更新 secret | `wrangler secret put {名稱}` |
| 暫停回覆 | Cloudflare Dashboard → Workers → 停用 |

---

## 注意事項

- **IG Token 2026-07-16 到期**，到期後自動回覆會失效，需更新 `IG_TOKEN` secret
- Meta 送 Webhook 事件有時會重複，目前設計為每次都回覆（若造成雙重回覆，可加 Cloudflare KV 去重）
- `instagram_manage_messages` 若需要 Meta 審核，測試期間只對 App 測試人員有效
