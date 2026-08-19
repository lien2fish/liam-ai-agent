---
name: insurance
description: 磊山保經業務系統：產險保單到期提醒、壽險客戶名單與固定拜訪、生日提醒。含資料來源、Notion DB、隱私規則（客戶個資只走 Email 不 commit）。要處理保單、拜訪名單、客戶提醒時載入。
---

## 產險保單到期提醒系統（2026-06-22 建立）

### 核心資訊
| 項目 | 說明 |
|------|------|
| 資料來源 | `insurance/active_policies.json`（105筆磊山保經有效保單，已去重複） |
| 腳本 | `insurance/policy_expiry_check.py`（讀取保單→算下次續保日→14天內到期則寄信+寫報告）/ `insurance/process_policies.py`（資料處理）/ `insurance/policy_data.py`（原始資料，含身分證號等個資，**gitignore僅本機保留**） |
| 排程 | GitHub Actions `policy_expiry_check.yml`，每天08:00台灣時間 |
| 通知 | `GMAIL_APP_PASSWORD` smtplib寄信（與OAuth系統無關不會過期） |
| 報告 | `reports/產險到期提醒_YYYY-MM-DD.md`，自動commit進repo |
| 提醒窗口 | `REMINDER_WINDOW_DAYS = 14`（續保日落在未來14天內才提醒） |

## 壽險客戶名單 + 固定拜訪系統（2026-07-01 建立）

### 核心資訊
| 項目 | 說明 |
|------|------|
| 來源 | `/Users/lien/Desktop/20260701_連傳正_客戶清單.xlsx`（磊山保經416筆），篩選**保單類型含「壽」＝180位**（壽103/壽產65/壽團7/壽產團5）|
| 建置腳本 | `insurance/build_life_clients.py`（擷取→本機xlsx+numbers→建Notion DB+匯入，一次性）|
| 本機檔 | `/Users/lien/Desktop/鉅鑫管理顧問/磊山保經/客戶名單/壽險客戶名單_20260701.xlsx`＋`.numbers`（**保留完整欄位含身分證**）|
| Notion DB | 「🛡️ 壽險客戶名單（固定拜訪）」`390f4149-a6aa-81bf-98e1-c3bffc0caad2`（建在CRM主頁下，**不含身分證**）|
| 拜訪欄位 | 拜訪週期(select:每季/每半年/每年，**預設每半年**)、上次拜訪日、下次拜訪日、拜訪狀態(待拜訪/已完成/暫緩)、拜訪備註 |
| 提醒腳本 | `insurance/visit_reminder.py`：讀Notion→下次拜訪日＝上次+週期月數→本週(7天內)到期則Email；上次拜訪日空＝待首次安排；順便PATCH回Notion下次拜訪日 |
| 排程 | `.github/workflows/life_visit_reminder.yml`，每天08:40台灣，env NOTION_TOKEN+GMAIL_APP_PASSWORD |
| 設定 | `insurance/visit_config.json`（Notion DB id、reminder_days=7，已進版控）|

### 重要
- **隱私**：repo為public，`visit_reminder.py` 只寄Email、**不commit報告**（含客戶姓名/電話），workflow無commit步驟。本機xlsx/numbers含身分證只留Desktop不進repo
- 使用流程：拜訪後在Notion填「上次拜訪日」→系統自動算下次拜訪日並在到期前7天Email提醒。週期可在Notion個別改每季/每年
- 已雲端驗證通過（180位全部待首次安排、0到期）
- **生日提醒**（2026-07-01加）：`insurance/birthday_reminder.py`+`birthday_reminder.yml`，每天08:05讀壽險名單「生日」欄，未來7天內生日則Email（含歲數）。共用 visit_config.json(birthday_days=7)。**只壽險有生日**；鑫酒藏/海產/茶坊名單無生日欄，之後要納入需先加生日欄+填資料
- **名單更新（2026-07-07）**：來源已改成 `/Users/lien/Desktop/20260701_連傳正_客戶清單.numbers`（xlsx 已不存在，用 `numbers_parser` 讀）。名單縮減為 **134 位**（壽67/壽產59/壽產團2/壽團6），Notion DB 180→134（移除45位失效客戶、含一組同名重複的多餘頁）。本機檔改 `壽險客戶名單_20260707.xlsx`+`.numbers`。⚠️`build_life_clients.py` 是**一次性建新DB**腳本（SRC仍指失效xlsx），**日後更新勿直接重跑**（會複製重複DB+洗掉拜訪追蹤）；改用**增量同步**：Notion API 依姓名比對 archive移除者/PATCH刷新欄位、保留拜訪欄與同一DB id。更新前確認拜訪資料全空才可放心（本次0筆）

---
