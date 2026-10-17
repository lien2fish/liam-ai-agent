---
name: market-finance
description: 每日財金日報（market/market_report.py，台股／美股／美債利率／匯率／黃金原物料走勢＋AI 資產配置比例＋波段訊號，Email 附 PDF）與個人資產負債表更新（finance/update_balance_sheet.py）。含追蹤標的清單、Gemini 設定、Notion 頁面 ID、資產負債 DB 維護流程。要看市場、更新資產數字時載入。
---

## 每日財金日報（2026-06-02 建立，2026-10-17 改版）

**2026-10-17 改版**：Lien 股票全部清空，報告從「我的持股怎麼了」改成「錢接下來該放哪」。
Lien 選的方向：中長期配置＋波段訊號兩者都要、**給具體百分比**、追美債利率／匯率／原物料、**Email 附 PDF**。

### 核心資訊
| 項目 | 說明 |
|------|------|
| 腳本 | `market/market_report.py`（產 Notion＋Markdown＋PDF）、`market/send_report.py`（寄信）|
| 設定 | `market/market_config.json`——`groups` 七組追蹤標的，增刪直接改這裡 |
| 配置歷史 | `market/allocation_history.json`（180 天，進版控）——讓 AI 知道上期配置，報告顯示「與上期比」|
| 排程 | Worker 每天 12:07 台灣時間 dispatch `.github/workflows/market_daily.yml` |
| 送達 | **Email 給 lien2fish@gmail.com，內文＝完整報告、附件＝PDF**；Notion「每日市場日報」頁面照樣覆寫 |
| 檔名 | 沿用 `reports/市場日報_日期.md`、`day/市場日報_日期.pdf`（標題已改「財金日報」，檔名不改免得別處對不上）|

### 報告內容（由上而下）
1. 今日重點一句話、市場階段、整體偏向
2. **建議資產配置**：台股／美股／美債／黃金／原物料／現金六類百分比＋與上期比＋調整說明
3. **各資產走勢判斷**：六類資產的趨勢、未來 1-3 個月、判斷依據
4. **波段訊號** 2-4 個：標的、偏多／偏空／觀望、參考進場、失效條件
5. 市場數據七張表（日／週／月／3 個月變動＋趨勢）＋殖利率曲線（10 年減 3 個月）
6. 重要事件、未來一週要注意、可能出錯的地方、判斷信心

### 設計重點
- **走勢與均線由程式從 Yahoo 一年日線自己算**，不讓 AI 算：趨勢＝現價與 50／200 日均線相對位置
- 殖利率類（`kind: yield`）變動單位是 bp，不是 %
- AI 給的配置加總常常不是 100，`normalize_allocation` 會等比例修正；六類缺項或非數字就整段不顯示
- prompt 限制每項跟上期差距 ≤5 個百分點（除非有明確新事件），避免配置每天翻來翻去
- Markdown **不放 emoji**——PDF 字型沒有 emoji 字形會變方框；AI 文字經 `clean()` 換掉 `< > & |`，裸的 `<` 會讓 reportlab 整份 PDF 建不出來
- 寄信步驟排在 commit 之後；缺 `GMAIL_APP_PASSWORD` 或寄信失敗會讓 run 變紅

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
