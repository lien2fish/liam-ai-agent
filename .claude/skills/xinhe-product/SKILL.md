---
name: xinhe-product
description: 炘和管理顧問「丟圖→查資料→官網商品頁＋IG 草稿」流程。Lien 丟商品照片說要上炘和官網、做商品介紹、或要炘和的 IG 貼文時載入。含查證規則、商品 JSON 格式、tools/xinhe_product.py 指令、兩道人工確認關卡。
---

# 炘和商品上架流程

```
Lien 丟圖 → 辨識商品 → 上網查證（每條附出處）→ 寫 design/xinhe_products/<slug>.json
→ preview（Lien 看）→ Lien 說 OK → publish＋部署官網
→ ig 草稿（Lien 看）→ Lien 說 OK → 發 IG（⏸️ 帳號未定，見最下方）
```

**兩道關卡都要 Lien 明確說 OK**，不可以自己判斷「應該沒問題」就往下走。

## 1. 辨識商品

- 看圖認不出、或酒標年份／品名看不清楚 → **問 Lien**，不要猜。猜錯的商品頁比沒有更傷。
- 海鮮先載入 `seafood-brand`，五條紅線全部適用。

## 2. 查證規則

| 可以寫 | 來源要求 |
|---|---|
| 酒莊、產區、品種、釀造方式、風味描述 | 優先酒莊官網，其次進口商／專業酒評。**每一條 specs 與 features 都要能對到 sources 裡的某一筆** |
| 茶的產區、製程、品種 | 官方或產地單位資料優先 |
| 海鮮的物種特徵、料理方式 | 公部門（漁業署、水試所）資料優先 |

| 不可以寫 | 為什麼 |
|---|---|
| 自己估的價格、網路查到的售價、促銷用語 | 價格只能來自 Lien，放 `price` 欄位（見第 3 節） |
| 產季、到貨時間、「現在有貨」 | 只有 Lien 知道 |
| 「自家漁船」、船數、老闆出海 | 漁船是鉅鑫的資產；炘和只能寫「與龜吼在地共捕漁船長期合作」 |
| 酒評分數、得獎紀錄 | 除非找得到原始出處且年份完全對上 |
| 網路評論、搜尋摘要講鉅鑫或炘和的事 | 曾被誤傳成事實（見 `seafood-brand`） |

**查不到或互相矛盾的欄位填 `＿＿`**，`publish` 會擋下來等 Lien 補。空白比編造好。

⚠️ 只靠網路資料寫出來的都是「查得到的通用知識」，實測這類內容墊底。
**在 preview 時順便問 Lien 一句：這項商品有沒有只有你知道的事**（為什麼選它、跟誰合作、客人怎麼吃），有的話寫進 `intro` 或 `features`。

## 3. 商品 JSON

放 `design/xinhe_products/<slug>.json`，原圖放 `design/xinhe_products/src/<slug>.jpg`（png／heic 也可）。
slug 用英文小寫加連字號，例如 `flechas-gran-malbec-2019`。

```json
{
  "slug": "flechas-gran-malbec-2019",
  "category": "wine",
  "status": "draft",
  "name": "中文品名",
  "name_en": "原文品名",
  "subtitle": "一句話定位",
  "intro": "兩三句介紹",
  "features": [{"title": "特色", "text": "說明"}],
  "specs": [["產區", "…"], ["品種", "…"]],
  "pairing": "適合的場合與搭配（可省略）",
  "sources": [{"title": "酒莊官網", "url": "https://…"}],
  "ig_caption": "IG 文案（原生寫法，不貼官網內文）",
  "hashtags": ["#…"]
}
```

`category`：`seafood`／`wine`／`tea`／`gift`。

### 價格與檔期（2026-10-14 加入）

```json
{
  "price": 1280,
  "mixed": false,
  "campaigns": [
    {"festival": "中秋節", "start": "2026-08-20", "end": "2026-09-25",
     "title": "檔期標題", "copy": "檔期文案", "price": 1380,
     "ig_caption": "可省略，省略就用 copy", "hashtags": ["#…"]}
  ]
}
```

- 🔴 **價格只能來自 Lien**。他丟照片沒講價格就問，**不准自己估、不准參考網路售價**。文案裡也不准寫價格數字（護欄會擋），價格只放 `price` 欄位。
- `festival` 必須是 `festivals/festivals.json` 裡的名稱，決定行銷圖配色。
- 檔期沒給 `price` 就沿用原價。官網由瀏覽器依台灣日期切換檔期，**換檔不必重新部署**；但新增檔期要重建＋部署。
- 禮盒必填 `mixed`。混裝（例：海鮮＋茶）在 `MIXED_BOX_PRICING_CLEARED` 改成 True 之前不能標價——要等記帳士確認「併同銷售」。
- 酒：不標價、不能訂購（菸酒管理法 §30）。

## 4. 指令

```bash
python3 tools/xinhe_product.py check <slug>     # 護欄
python3 tools/xinhe_product.py preview <slug>   # 含草稿，Safari 開預覽（不動官網）
python3 tools/xinhe_product.py publish <slug>   # 有＿＿或違規就擋；過了才改 published 並重建官網
python3 tools/xinhe_product.py ig <slug>        # IG 草稿 → design/xinhe_products/ig/<slug>/（不進版控）
python3 tools/xinhe_product.py poster <slug> [起日]  # 節慶行銷圖＋IG 草稿（預設：進行中或下一檔）
```

行銷圖＝實拍照＋節日配色色塊＋檔期標題＋價格。**不用 AI 生圖**（2026-10-14 Lien 選定：商品圖不能跟實物不符）。

## 訂購

`order.html`＋`design/xinhe_pages/functions/api/order.js`：表單送出 → 寫進 Notion → 推 LINE（`/notify`）。

**Notion（2026-10-14 建）**：私人頁「炘和管理顧問」底下的「炘和客戶」（`9cb11bd8a1944a5099b82564f887ab21`）
與「炘和訂單」（`7a048786067b4d30bf6822f1d0d98501`），**跟鉅鑫 CRM 完全分開**（Lien 選定）。
- 同一支手機（去掉 `-` 與空白後比對）＝同一位客人：更新、不重建。累計訂單數／金額是 Notion rollup 自動算。
- 「同意行銷」只在客人勾選時設為 true，表單**不會**把它改回 false；沒勾的客人不可做行銷聯繫。
- 只要 Notion 或 LINE 其中一邊記到就回成功；Notion 失敗時 LINE 訊息會寫「請手動建檔」。
- ⛔ `NOTION_TOKEN` 要用**只連「炘和管理顧問」頁面的新 integration**，不可用鉅鑫那把（它看得到整個鉅鑫 CRM，包含壽險名單）。
- ⚠️ 2026-10-14 只用假 Notion 伺服器測過寫入格式；**第一次接上真正的 integration 時要實際送一張測試單、到 Notion 看過再刪掉**。
價格以站上 `products.json` 為準，客人改不了；隱藏欄位擋機器人（不推播，避免吃掉每月 200 則額度）。
匯款帳號不放網站，Lien 確認訂單後才給。

⛔ **上線前兩個關卡都要 Lien 點頭**：① 這是新的客戶個資流向（姓名／手機／地址 → LINE）② 公司還在籌備，用「炘和」名義收訂單前要確認登記狀態。

護欄（寫在腳本裡，不靠記得）：價格與促銷字、「生食級」、「自家漁船」、船數、老闆出海；
酒另擋「線上購買／下單／購物車／宅配／網購」。酒的商品頁與 IG 圖文**自動加上**「禁止酒駕　未滿十八歲禁止飲酒」。

## 5. 部署官網

⏸️ **還沒建 Cloudflare Pages 專案、還沒上線過**（2026-10-13）。第一次上線前要 Lien 點頭。
建好之後：

```bash
cd design/xinhe_pages && npx wrangler pages deploy ../xinhe_site --project-name=<待定> --branch=main --commit-dirty=true
```

⚠️ **一定要在 `design/xinhe_pages/` 裡執行**——wrangler 從「目前資料夾」找 `functions/`，在別處執行訂購 API 會整個不見。
`functions/` 刻意不放進 `xinhe_site/`，否則原始碼會被當成網頁公開。
Pages 專案要設兩個 secret：`LINE_NOTIFY_URL`、`LINE_NOTIFY_TOKEN`（值同 GitHub Secrets）。

本機測試（2026-10-14 驗證過）：`cd design/xinhe_pages && npx wrangler pages dev <網站資料夾> --binding LINE_NOTIFY_URL=http://127.0.0.1:9999 --binding LINE_NOTIFY_TOKEN=test`，
推播接到本機假接收端，不會真的發到 LINE。

部署完要**把線上的商品頁抓回來確認**，不是看指令回 Success。

## 6. 發 IG

⏸️ **未接通**：要發到哪個帳號取決於開局計畫「決策 2」（掛連老闆個人帳號 or 新公司另開），還沒拍板。
在那之前只產生草稿，由 Lien 自己貼或等決定。接通時沿用 `ig-fb-auto` 的發文串接；
IG 圖片網址可直接用官網上的 `img/<slug>.jpg`（要先部署）。**IG 發出去 API 刪不掉，每則都要 Lien 說 OK。**

## 日後：LINE 傳圖

第二階段才做（2026-10-13 定）：等這個流程跑順，再讓 LINE 助理收圖丟進同一條管線。
