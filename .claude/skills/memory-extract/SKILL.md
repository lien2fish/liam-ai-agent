---
name: memory-extract
description: 從工作日誌萃取「講過但沒記下來」的偏好、決定與糾正，列成候選清單讓 Lien 勾選後才寫入記憶。Lien 說「萃取記憶」、週報提醒有對話尚未萃取、或問「最近講過的東西有沒有記下來」時載入。
---

# 萃取記憶

工作日誌（`~/liam-workspace/daily/`）每次 session 結束自動寫入，但只存檔、不會變成記憶。
這個流程把日誌裡該長期記住的東西挑出來。**Lien 選的規則：候選清單由他確認才寫入**——
寫錯的記憶會一直影響之後的判斷，錯誤容忍度低於慢。

用 Claude Code 訂閱額度跑，不呼叫 API、不增加花費。

## 流程

### 1. 列出待萃取的對話

```bash
python3 scripts/memory_extract.py
```

0 段就回報「沒有待萃取的對話」並結束。日誌只記 Lien 的提問與改動的檔案，
看不懂脈絡時讀列表附的「完整對話」路徑（本機才有，手機 session 沒有）。

### 2. 挑候選

**要挑的**：
| 類型 | 訊號 | 例子 |
|---|---|---|
| feedback | 糾正、不滿、「不要」「改成」「怎麼又」 | 「怎麼又變英文回覆了」 |
| feedback | 確認某個做法是對的、要沿用 | 「以後都照這樣」 |
| project | 決定、暫停、取消、改方向、日期 | 「先不做」「等新機到再討論」 |
| user | 他的角色、習慣、偏好、限制 | 「我進不了漁港作業區」 |

**不要挑的**：
- 一次性的任務細節（這次改了哪個數字）——git 與日誌已經有
- 已經在記憶、skill、CLAUDE.md 裡的——**每個候選先跑 `python3 scripts/find_context.py 關鍵字 --in 記憶,skill,規則` 查過**
- 客戶姓名、電話、金額等個資——那些在 CRM，不進記憶
- 海鮮產地知識——不進記憶，走 `knowledge/seafood/`，並守 `seafood-brand` 的紅線

### 3. 給 Lien 看候選清單

一張表，一列一個候選：

| # | 類型 | 要記住的事（一句話） | 依據（日期時間＋原話） | 寫到哪 |
|---|---|---|---|---|

「寫到哪」寫清楚是**新增** `xxx.md` 還是**更新**既有的 `yyy.md`（更新優先，避免重複）。
請 Lien 回覆要寫入的編號；沒勾的直接捨棄，不另外留紀錄。

⚠️ 沒有 Lien 的明確回覆就不寫入。候選 0 個也要照樣回報，然後直接跳到第 5 步標記進度。

### 4. 寫入

照記憶檔格式（frontmatter 的 `name`／`description`／`metadata.type`，feedback 與 project 附 **Why:** 和 **How to apply:**），
新增的檔案要在 `MEMORY.md` 對應分類加一行。更新既有檔案前先讀全文。

### 5. 驗收與收尾

```bash
python3 scripts/memory_doctor.py --quiet            # ❌ 要歸零
~/liam-workspace/sync_workspace.sh push             # 有寫入才需要
python3 scripts/memory_extract.py --mark '<第 1 步列表最後印出的時間點>'
```

`--mark` 一定用第 1 步印出的時間點，不要用現在時間——中間若有別的 session 結束，會被一起標掉。
