---
name: crm-order
description: 三品牌 CRM 與訂單建檔：全品牌統一 Notion 總表、鑫酒藏／鑫海產／鑫茶坊客戶與銷售 DB、三個庫存 DB、訂單三同步、回購提醒、名片數位化。含所有 Notion DB ID 與欄位規格，以及 **Notion API 與 xlsx 處理的已知地雷**。要建訂單、查客戶、改 CRM、動庫存、或用程式讀寫任何 .xlsx 進出 Notion 時載入。
---

## 全品牌統一 CRM ＋回購提醒系統（2026-06-26 建立）

### 核心資訊
| 項目 | 說明 |
|------|------|
| 整併腳本 | `crm_unified/build_unified_crm.py`（讀酒藏/海產4個舊DB→建2個跨品牌總表→匯入，可重複跑會沿用既有總表） |
| 回購腳本 | `crm_unified/repurchase_reminder.py`（掃描客戶總表→超門檻未回購→Email） |
| 設定 | `crm_unified/config.json`（兩個總表DB ID，**已進版控**，workflow 需讀） |
| 排程 | `.github/workflows/repurchase_reminder.yml`，每天09:00台灣，超60天未回購則寄信＋commit報告 |
| 報告 | `reports/回購提醒_YYYY-MM-DD.md` |

### 兩個跨品牌 Notion 資料庫（建在 CRM 主頁 `358f4149-a6aa-8088-9e6d-f5361d05cd12` 下）
| DB | ID | 欄位 |
|----|----|------|
| 🗂️ 全品牌客戶總表 | `38bf4149-a6aa-816e-9850-f3dfbbb925ec` | 客戶姓名/品牌(select:鑫酒藏/鑫海產/鑫茶坊)/聯絡電話/Email/地址/會員等級/偏好品項/累計消費/最後購買日/公司/統編/備註 |
| 🧾 全品牌銷售紀錄 | `38bf4149-a6aa-81db-9b89-c47410857a2c` | 訂單編號/品牌/出貨日期/客戶名稱/品項/數量/金額/成本/毛利/付款方式/備註 |

### 資料來源（整併自既有4個獨立DB，保留不刪）
- 🍷鑫酒藏 客戶`374f4149-a6aa-816f-ab2c-fcaad143f5b4`／銷售`374f4149-a6aa-81ec-8aef-de88095d8b6b`
- 🐟鑫海產 客戶`374f4149-a6aa-8135-b9e4-dbb0cc2c2e0d`／銷售`374f4149-a6aa-8102-baf5-ffa959227731`
- 🍵鑫茶坊：尚無獨立 Notion DB／無歷史資料，已列為品牌選項；經 `add_order.py` 新增的茶坊訂單會自動進統一總表

### 新訂單自動同步（2026-06-26 接通）
`notion_crm/add_order.py` 每筆新訂單現在同步 **4 個目標**：① 本機 Numbers ② 舊品牌 Notion 銷售DB ③ 舊品牌 Notion 客戶DB累計消費 ④ **統一總表**（銷售紀錄新增＋客戶「最後購買日」更新/新增）。第④步確保回購提醒讀到的「最後購買日」永遠是最新，不會誤判。

### 回購邏輯
- 門檻天數 `REPURCHASE_DAYS`（預設60，workflow env 可調）
- 「最後購買日」由銷售紀錄每客戶取最新出貨日算出
- 待回購＝曾購買且距今>門檻；從未消費（無最後購買日）另列參考區不算逾期
- 認證沿用 `NOTION_TOKEN`＋`GMAIL_APP_PASSWORD`（與保單提醒同套，無到期問題）


## 鑫酒藏 CRM 欄位規格（2026-06-05 更新）

### 客戶名單欄位（9欄）
`#` / `客戶姓名／公司` / `聯絡電話` / `地址` / `Email` / `VIP等級` / `備註` / `公司` / `統編`

### 檔案位置
| 檔案 | 路徑 |
|------|------|
| Numbers | `/Users/lien/Desktop/鉅鑫管理顧問/鑫酒藏/鑫酒藏販售清單.numbers` |
| Excel | `/Users/lien/Desktop/鉅鑫管理顧問/鑫酒藏/鑫酒藏販售清單.xlsx` |

### Notion DB ID
- 鑫酒藏客戶名單：`374f4149-a6aa-816f-ab2c-fcaad143f5b4`
- Notion 屬性：客戶姓名(title) / 聯絡電話 / Email / 地址 / VIP等級(select) / 備註 / 公司 / 統編

### 排版設計規範
- 標題列：深藍 `#1F4E79`、白色粗體 14pt
- Header 列：深藍底、白色粗體 10pt、全欄置中
- 資料列：淺藍 `#DEEAF1` / 白色交替
- 置中欄：#、電話、Email、VIP等級、統編

---


## 名片數位化系統（2026-06-25 建立）

### 核心資訊
| 項目 | 說明 |
|------|------|
| 名片照片來源 | `/Users/lien/Desktop/鉅鑫管理顧問/名片資料`（手機拍照後AirDrop/iCloud同步） |
| Notion：扶輪社名片名單 | `38af4149-a6aa-8136-a515-e9d8a468a3bb`（姓名/扶輪社名稱/扶輪職位/公司商號/職稱/聯絡電話/Email/地址/備註/取得日期） |
| Notion：公司行號名片名單 | `38af4149-a6aa-81b8-87e9-c94d4dd8d809`（姓名/公司商號/職稱/聯絡電話/Email/地址/統編/備註/取得日期） |
| 與既有名單關係 | 完全獨立於鑫海產/鑫酒藏/磊山保經客戶名單，都建在CRM主頁面（`358f4149-a6aa-8088-9e6d-f5361d05cd12`）下 |

### 處理流程
1. HEIC用 `sips -s format jpeg` 轉jpg（Read工具不支援HEIC直讀）
2. 逐張用Read工具讀圖辨識文字（姓名/公司/職稱/電話/Email/地址）
3. 分類依據：卡片有Rotary標誌/扶輪社名稱 → 扶輪社名單；純公司行號名片 → 公司行號名單
4. **同一人有兩張卡**（扶輪社卡+一般公司卡）時合併成一筆，優先放扶輪社名單並把公司資訊填進公司/商號欄，不重複建檔
5. 寫入用Python urllib直接呼叫Notion API（`POST /v1/pages`，`Notion-Version: 2022-06-28`）

### 重要技術細節
- **建立新Notion資料庫不可用notion-mcp的`API-create-a-data-source`**：新版API（2025-09-03+）已不支援這endpoint建資料庫，會回400要求改用「Create Database API」。改用Python直接呼叫舊版endpoint `POST https://api.notion.com/v1/databases`（帶 `Notion-Version: 2022-06-28`），parent用`{"type":"page_id","page_id":...}`即可成功
- Token讀取：`~/.config/notion_token`

---


---

## ⚠️ 用程式改 xlsx 的地雷

**預設不要用程式改使用者的 xlsx。** 需要調整的差異放在**解析階段**處理
（鑫酒藏的重複登錄就是改成在 `parse_wine` 裡去重，原檔完全不動）。

**openpyxl 存檔會把整個活頁簿的公式快取值清空，而且不報錯：**

| 載入方式 | 存檔後果 |
|---|---|
| `load_workbook(p)` | 保留公式字串，**但快取值全沒了**——之後 `data_only=True` 讀取全回 `None` |
| `load_workbook(p, data_only=True)` | 相反：**公式被替換成死值** |

**兩種都會破壞原檔，沒有第三種選項。**

`delete_rows()` 更糟：**openpyxl 不調整公式的儲存格參照**。刪掉第 10–14 列後，
`M18 '=O18*70%'` 變成 `M13 '=O18*70%'`——位置移了、參照沒移。
**絕不用 `delete_rows`／`insert_rows` 動有公式的表。**

2026-08-25 實際災情：鑫酒藏三項進貨價消失（庫存成本 807,586 → 656,716）；
**前一天改鑫海產分頁時連帶洗掉鑫茶坊 8 項零售價**——不同分頁也會被波及，
因為 save 是整本重寫。當下還誤判成「Notion 原本就跟 xlsx 有落差」。

非改不可時，**先掃一次公式格**：

```python
wf = load_workbook(p); wd = load_workbook(p, data_only=True)
[(c.coordinate, c.value, wd[s][c.coordinate].value)
 for s in wf.sheetnames for r in wf[s].iter_rows() for c in r
 if isinstance(c.value, str) and c.value.startswith("=")]
```

有公式就換做法。**改動前備份是唯一救命索**——那兩次都是靠備份比對才發現與還原。

---

## ⚠️ Notion API 的地雷

- 🔴 **不要假設不同 DB 的欄位一樣。** 三個庫存 DB 欄位名互不相同——
  鑫酒藏無「單位」、鑫海產叫「數量單位」，價格分別是進價／零售價／進價；
  鑫茶坊的 `進貨價_斤` 是**每斤價**，跟「2兩」「4兩」的數量單位對不上，要改讀 `單包成本`。
  2026-08-24 就是這樣讓 LINE 助理的 `/庫存` 印出一片空白。
- 🔴 **查詢預設只回第一頁。** 沒處理分頁就會靜默少資料，不會報錯。
- 🔴 **DB 建在頁面下時是該頁的 `child_database` 區塊。** 清空頁面重寫彙總時若一併
  archive，等於**把三個資料庫丟進垃圾桶**。`write_summary` 必須跳過 `child_database`。
- **schema 加新欄位時既有 DB 不會自動長出來**，PATCH 頁面會 400
  `is not a property that exists`。要先 GET 現有 schema、把缺的欄位 PATCH 進 `/databases/{id}`。
- 建 DB 一律用舊版 `POST /v1/databases` + `Notion-Version: 2022-06-28`。
- **SQL 模式有工作區用量上限**（2026-08-25 實測用完）；**view 模式沒有額度限制**，
  但一次最多 100 列要自己翻頁，且**空值欄位會整個省略**。
- ⚠️ **三個庫存 DB 是「型錄＋庫存」混在一起**：酒藏 236 筆只有 72 筆真有庫存，
  海產 72 筆是「可調貨」不是缺貨。**算庫存金額前先確認你在算哪一種。**
