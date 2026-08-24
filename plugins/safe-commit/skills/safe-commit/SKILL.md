---
name: safe-commit
description: commit／push 前的敏感資料檢查。判斷資料的敏感等級、實際查證目的地 repo 的公開程度、掃描暫存區，並在真的外洩時執行止血流程。要 commit、push、新增資料檔、或不確定某份資料能不能進版控時載入。
---

# 進版控前的敏感資料檢查

## 為什麼需要這一關

**代價高的不是修，是不知道自己漏了。**

一個真實案例：某個公開 repo 裡混進了客戶名單 CSV（姓名、電話、Email、地址、
消費金額）與個人財務試算表，**從加入到被發現隔了三個多月**——
而且不是因為出事才發現，是查別的問題時順手看到的。

處理成本：移除 → 加 `.gitignore` → 全庫鏡像備份 → 改寫上千個 commit → force push。
**而且必須當作資料已經外流**，因為在那之前誰看過查不到。

三十秒的檢查換掉這些，很划算。

---

## 三個步驟，順序不能顛倒

### 一、這份資料是什麼等級

| 等級 | 判準 | 例子 | 該去哪 |
|------|------|------|--------|
| 🔴 **絕不進任何 repo** | 外洩＝立即實害 | 身分證號、金鑰／token／密碼、原始保單、銀行帳號 | **純本機**，並確認已被 `.gitignore` |
| 🟠 **只進私人 repo** | 可識別到特定個人或揭露財務狀況 | 客戶姓名／電話／Email／地址、報價與成交金額、個人財務、工作日誌、會議記錄 | 私人 repo |
| 🟡 **可進公開，但要逐檔看過** | 本身無害，但可能夾帶 | 報告、設計檔、資料處理腳本、任何 CSV／XLSX 資料檔 | 公開 repo，**打開來確認過才進** |
| 🟢 **公開沒問題** | 純邏輯，不含資料 | 程式碼、workflow、文件、`.gitignore` | 公開 repo |

**判斷不出來就當高一級。** 猜錯往低走的代價遠高於往高走。

### 二、查證目的地的公開程度——不要靠記憶

**repo 名稱不代表可見性。** 每次都實際查：

```bash
curl -s https://api.github.com/repos/<owner>/<repo> \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('visibility') or d.get('message'))"
```

私人 repo 未帶認證時 API 會回 `Not Found`——**那就是「私人」的證據**，不是查詢失敗。

### 三、掃過暫存區才 commit

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check_staged.py
```

沒有 ❌ 才 commit。有 ❌ 就**停下來查證**，不要自己判斷「應該還好」。

> 掃描器會誤判。表格多的說明文件常被當成人名表格。
> 遇到 ❌ 時**把命中的內容印出來逐行看過**，確認是誤判再進版控——
> 但不要因為「上次也是誤判」就跳過檢查。

---

## 已知陷阱

### ⚠️ 中文（非 ASCII）檔名會讓 grep 永遠 0 命中

`git ls-files`、`git diff --name-only`、`git log --name-only` **預設把非 ASCII 路徑
輸出成八進位跳脫**：

```
客戶名單/清單.csv  →  \345\256\242\346\210\266\345\220\215\345\226\256/...
```

拿去 `open()` 會開不到檔，拿去 `grep` 中文會**永遠 0 命中**，
而且**兩者都不報錯**。

實際後果：一天之內誤判三次——誤以為歷史已清乾淨、誤以為已經 push、
全庫掃描靜默跳過所有中文檔名的檔案（漏掉數十份含個資的報告）。

**任何用 git 列檔名的指令，一律加：**

```bash
git -c core.quotepath=false <指令>
```

### ⚠️ 只靠「值的樣式」會漏

- 電話號碼被 Excel 吃掉開頭的 0 變成 9 碼，手機正則抓不到
- 只有姓名沒有電話的 Markdown 報告，正則完全抓不到

**要同時看三種訊號：欄位標題、人名表格結構、值的樣式。**

### ⚠️ 這三件事都不等於「清乾淨了」

| 做法 | 實際效果 |
|------|---------|
| 加 `.gitignore` | **只擋新檔**。已追蹤的檔案不會消失，要 `git rm` |
| `git rm` | **不清歷史**。任何人仍能從舊 commit 撈回 |
| `git filter-repo` ＋ force push | 清了歷史，但**GitHub 仍會用 SHA 提供舊 commit**，直到它自己 GC |

要徹底斷，**必須寫信給 GitHub Support 請他們清除快取的舊 commit**。
這步最常被漏掉。

而且**別人 fork 或 clone 過的副本控制不了**——只要曾經公開過，就當作已外流。

---

## 萬一真的漏出去了：止血流程

順序照做，每一步做完先驗證再進下一步。

1. **備份**——複製到 repo 外的地方，比對 SHA-256 確認一致
2. **確認沒有腳本依賴**——`grep -rn "<檔名>" --include=*.py --include=*.yml .`
3. **從最新版移除**——`git rm` ＋ commit ＋ push
   （**commit 訊息寫中性**，不要變成尋寶圖）
4. **加 `.gitignore`** 擋掉整個資料夾，用 `git check-ignore -v` 實測規則命中
5. **全庫鏡像備份**——`git clone --mirror <url> <備份路徑>`
6. **改寫歷史**（在另一份新 clone 上做，不要在工作目錄動手）：
   ```bash
   pip3 install --quiet git-filter-repo
   git clone <url> ./rewrite && cd rewrite
   git-filter-repo --invert-paths --path <資料夾>/ --force
   ```
7. **驗證三件事**——⚠️ 每一條都要加 `-c core.quotepath=false`：
   ```bash
   git -c core.quotepath=false log --all --pretty=format: --name-only \
     | sort -u | grep -cE "^<資料夾>/"        # 要是 0

   git -c core.quotepath=false rev-list --all --objects \
     | grep -E "<資料夾>"                      # 要無輸出
   ```
   再把原始 HEAD `git archive` 出來 `diff -rq` 比對，確認其餘內容未動
8. **force push**
9. **本機跟上**——`git fetch origin && git checkout -B main origin/main`
   （不用 `reset --hard`，這樣保留未追蹤檔案）
10. **寫信給 GitHub Support** 請求清除快取的舊 commit

---

## 幾條固定判斷

- **假設 repo 是公開的**，除非你剛剛才查證過。不確定就不要進。
- **個資類的提醒只走 Email，不 commit 報告。**
  排程任務每天產一份含姓名電話的報告並自動 commit，
  是最容易累積出大量外洩的模式——那些報告會一份一份堆進歷史。
- 最高敏感的原始檔（身分證、保單）**只留本機**，不進任何 repo，包含私人的。
- 對外簡報／文宣放上公開處之前，**逐頁確認**沒有客戶名、報價、成本、財務數字。
