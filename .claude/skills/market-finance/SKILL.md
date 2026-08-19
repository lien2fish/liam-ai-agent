---
name: market-finance
description: 每日股市全面分析報告（market/market_report.py）與個人資產負債表更新（finance/update_balance_sheet.py）。含觀察股清單、Gemini 設定、Notion 頁面 ID、資產負債 DB 維護流程。要看市場、更新資產數字時載入。
---

## 每日股市全面分析報告系統（2026-06-02 建立）

### 核心資訊
| 項目 | 說明 |
|------|------|
| 腳本 | `market/market_report.py` |
| 設定 | `market/market_config.json`（觀察股清單、Notion Page ID）|
| 歷史 | `market/market_history.json`（90天，自動維護）|
| 排程 | GitHub Actions，每天 12:00 台灣時間（UTC 04:00）|
| Workflow | `.github/workflows/market_daily.yml` |
| Notion | 固定頁面「每日市場日報」（每日覆寫，手機可查）|
| Markdown | `reports/市場日報_YYYY-MM-DD.md`（每日 commit）|

### 資料來源（三層）
| 層 | 來源 | 說明 |
|----|------|------|
| L1 | Yahoo Finance | 全球指數、宏觀指標、台灣觀察股（`urllib`，無需 key）|
| L2 | Gemini 2.5-flash + Google Search | 今日新聞、外資動向、AI 預測 |
| L3 | Gemini 知識庫 | L2 失敗時備援 |

### 報告內容
1. 市場情緒（多頭/空頭/震盪）+ 樂觀指數 1-10
2. 全球 6 大指數（台灣、美三大、日、港）
3. 宏觀指標（VIX、USD/TWD、布蘭特油、黃金）
4. 台灣觀察清單（8 支，含持有標記 ★）
5. 今日市場新聞 + 外資動向（Gemini Search 即時搜尋）
6. AI 一週展望 + 加權預估區間 + 主要風險

### 觀察股清單（可在 market_config.json 增刪）
| 代號 | 名稱 | 持有 |
|------|------|------|
| 2330.TW | 台積電 | — |
| 0050.TW | 元大台灣50 ETF | — |
| 006208.TW | 富邦台灣50 ETF | — |
| 009816.TW | 凱基優選ETF | ★ |
| 2610.TW | 華航 | ★ |
| 2303.TW | 聯電 | — |
| 2454.TW | 聯發科 | — |
| 2317.TW | 鴻海 | — |

### Gemini 設定（重要）
- **模型**：`gemini-2.5-flash`（`claude-workspace-495009` 專案，**實為免費額度，非付費**——2026-06-23實測證實）
- **必須設定** `thinkingConfig: {thinkingBudget: 0}`，否則思考型輸出截斷導致 JSON 解析失敗
- `gemini-2.0-flash` 在此專案有配額異常（free_tier limit: 0 但 paid tier 未生效），已改用 2.5-flash
- `gemini-2.5-flash` 免費額度上限20次/天，`gemini-2.5-pro` 免費額度直接0，市場日報與其他自動化（IG留言回覆等）共用同一額度池
- Notion 父頁面：`358f4149-a6aa-8088-9e6d-f5361d05cd12`（CRM 主頁）
- Finance OS 頁面（36af4149）已封存，不可當 parent

---


## 個人資產負債表更新系統（2026-06-26 更新）

### 核心資訊
| 項目 | 說明 |
|------|------|
| 腳本 | `finance/update_balance_sheet.py`（讀取Notion 3個DB→重建「💼 個人資產負債表」頁面）|
| 設定 | `finance/finance_config.json`（收入、固定支出、Notion DB/頁面ID；已進版控）|
| 執行 | `python3 finance/update_balance_sheet.py`（每次重建整頁，安全可重複跑）|
| Notion頁面 | 個人資產負債表 `38af4149-a6aa-8178-9d8f-fd8a47091a73` |

### Notion 資料庫（在 Personal Finance OS 主頁 `38af4149-a6aa-81d3-9480-cfb0944c8824` 下）
| DB | ID | 維護方式 |
|----|----|---------|
| 資產 Assets | `38af4149-a6aa-81f6-bb8b-e938ad9825e4` | 使用者直接在Notion維護，腳本只讀 |
| 負債 Liabilities | `38af4149-a6aa-8101-9faf-f4c57a8fe3f7` | 同上 |
| 訂閱費用管理 Subs | `38af4149-a6aa-81bb-aabb-d6b3a9a788e2` | 同上（狀態=啟用才計入月支出）|

### 更新流程（資產/負債有變動時）
1. **資產數字變動**用 Python REST（`Notion-Version: 2022-06-28`）直接 PATCH/POST/archive 對應 page；新版MCP的query-data-source吃data_source_id會404，改用舊版 `POST /v1/databases/{db}/query` 端點
2. Assets DB 欄位：`項目名稱 / Asset Name`(title)、`類別 / Category`(select：股權/保險/存款/股票/其他)、`當前金額 / Current Value`(number)、`成本 / Cost Basis`(number)
3. **收入/固定支出變動**改 `finance_config.json`（`income` / `fixed_expenses` 區塊）
4. 改完一律 `python3 finance/update_balance_sheet.py` 重建頁面，再把finance變動 commit+push（push前先 stash 未暫存的自動報告→pull --rebase→push→stash pop）
5. 投資概況區塊只統計類別屬 `股票/黃金/ETF/Stock/Gold` 的資產；存款類（含黃金存摺、實體金條）不列入投資損益

> 完整財務數字（資產明細/收支/指標）見 memory `finance_personal.md`，不在此重複。

---
