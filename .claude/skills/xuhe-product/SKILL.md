---
name: xuhe-product
description: 旭和管理顧問「丟圖→查資料→官網商品頁＋IG 草稿」流程。Lien 丟商品照片說要上旭和官網、做商品介紹、或要旭和的 IG 貼文時載入。含查證規則、商品 JSON 格式、tools/xuhe_product.py 指令、兩道人工確認關卡。
---

# 旭和商品上架流程

```
Lien 丟圖 → 辨識商品 → 上網查證（每條附出處）→ 寫 design/xuhe_products/<slug>.json
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
| 價格、促銷用語 | 酒依法不得線上販售；海鮮價格天天變 |
| 產季、到貨時間、「現在有貨」 | 只有 Lien 知道 |
| 「自家漁船」、船數、老闆出海 | 漁船是鉅鑫的資產；旭和只能寫「與龜吼在地共捕漁船長期合作」 |
| 酒評分數、得獎紀錄 | 除非找得到原始出處且年份完全對上 |
| 網路評論、搜尋摘要講鉅鑫或旭和的事 | 曾被誤傳成事實（見 `seafood-brand`） |

**查不到或互相矛盾的欄位填 `＿＿`**，`publish` 會擋下來等 Lien 補。空白比編造好。

⚠️ 只靠網路資料寫出來的都是「查得到的通用知識」，實測這類內容墊底。
**在 preview 時順便問 Lien 一句：這項商品有沒有只有你知道的事**（為什麼選它、跟誰合作、客人怎麼吃），有的話寫進 `intro` 或 `features`。

## 3. 商品 JSON

放 `design/xuhe_products/<slug>.json`，原圖放 `design/xuhe_products/src/<slug>.jpg`（png／heic 也可）。
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

## 4. 指令

```bash
python3 tools/xuhe_product.py check <slug>     # 護欄
python3 tools/xuhe_product.py preview <slug>   # 含草稿，Safari 開預覽（不動官網）
python3 tools/xuhe_product.py publish <slug>   # 有＿＿或違規就擋；過了才改 published 並重建官網
python3 tools/xuhe_product.py ig <slug>        # IG 草稿 → design/xuhe_products/ig/<slug>/（不進版控）
```

護欄（寫在腳本裡，不靠記得）：價格與促銷字、「生食級」、「自家漁船」、船數、老闆出海；
酒另擋「線上購買／下單／購物車／宅配／網購」。酒的商品頁與 IG 圖文**自動加上**「禁止酒駕　未滿十八歲禁止飲酒」。

## 5. 部署官網

⏸️ **還沒建 Cloudflare Pages 專案、還沒上線過**（2026-10-13）。第一次上線前要 Lien 點頭。
建好之後：

```bash
npx wrangler pages deploy design/xuhe_site --project-name=<待定> --branch=main --commit-dirty=true
```

部署完要**把線上的商品頁抓回來確認**，不是看指令回 Success。

## 6. 發 IG

⏸️ **未接通**：要發到哪個帳號取決於開局計畫「決策 2」（掛連老闆個人帳號 or 新公司另開），還沒拍板。
在那之前只產生草稿，由 Lien 自己貼或等決定。接通時沿用 `ig-fb-auto` 的發文串接；
IG 圖片網址可直接用官網上的 `img/<slug>.jpg`（要先部署）。**IG 發出去 API 刪不掉，每則都要 Lien 說 OK。**

## 日後：LINE 傳圖

第二階段才做（2026-10-13 定）：等這個流程跑順，再讓 LINE 助理收圖丟進同一條管線。
