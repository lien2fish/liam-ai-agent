---
name: safe-commit
description: commit／push 前的敏感資料檢查與落點判斷。任何要進版控的檔案都先過這一關：判斷敏感等級、決定該進哪個 repo（或根本不該進版控）、並實際查證目的地的公開程度。要 commit、push、新增資料檔、或不確定某份資料能不能進 repo 時載入。
---

# 進版控前的敏感資料檢查

## 為什麼有這個 skill

**2026-08-21 實際出事過一次。** 公開 repo `lien2fish/liam-ai-agent` 裡被發現四個檔案：

| 檔案 | 內容 |
|---|---|
| `客戶名單/鑫海產_客戶名單.csv` | 2 筆客戶：姓名、電話、Email、地址、消費金額 |
| `客戶名單/鑫酒藏_客戶名單.csv` | 1 筆客戶，同樣欄位 |
| `財務/個人資產負債表.xlsx` | 個人資產負債表 |
| `財務/gmail_cleanup_log.txt` | 1,155 行，列出往來銀行與消費平台 |

從 2026-05 起就公開可見，直到 08-21 才因為別的問題被順手查到。
處理成本：移除 → 加 .gitignore → 全庫鏡像備份 → `git filter-repo` 改寫 1,053 個 commit → force push。
**而且要當作資料已經外流**，因為在那之前誰看過查不到。

代價高的不是修，是「不知道自己漏了」。所以每次 commit 都檢查。

---

## 三步驟，順序不能顛倒

### 第一步：這份資料是什麼等級

| 等級 | 判準 | 例子 | 該去哪 |
|---|---|---|---|
| 🔴 **絕不進任何 repo** | 外洩＝立即實害 | 身分證號、金鑰／token／密碼、原始保單、銀行帳號密碼 | **純本機**：`~/Desktop/`、`config/`（已被 .gitignore） |
| 🟠 **只進私人 repo** | 可識別到特定個人或揭露財務狀況 | 客戶姓名／電話／Email／地址、報價與成交金額、個人財務、工作日誌、會議記錄 | **`liam-workspace`**（私人） |
| 🟡 **可進公開，但要逐檔看過** | 本身無害，但可能夾帶 | 報告、設計檔、資料處理腳本、CSV／XLSX 任何資料檔 | `liam-ai-agent`，**打開來確認過才進** |
| 🟢 **公開沒問題** | 純邏輯，不含資料 | 程式碼、workflow、文件、.gitignore | `liam-ai-agent` |

**判斷不出來就當高一級。** 猜錯往低走的代價遠高於往高走。

### 第二步：查證目的地的公開程度——不要靠記憶

**repo 名稱不代表可見性。** 每次都實際查：

```bash
# 公開的會回 "public"，私人的會回 "private"
curl -s https://api.github.com/repos/lien2fish/liam-ai-agent | python3 -c "import json,sys; print(json.load(sys.stdin).get('visibility','查不到'))"
curl -s https://api.github.com/repos/lien2fish/liam-workspace | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('visibility') or d.get('message'))"
```

私人 repo 未帶認證時 API 會回 `Not Found`——**那就是「私人」的證據**，不是查詢失敗。

目前狀態（每次仍要重查，別抄這張表）：

| repo | 可見性 | 放什麼 |
|---|---|---|
| `lien2fish/liam-ai-agent` | 🌐 **公開** | 腳本、workflow、文件 |
| `lien2fish/liam-workspace` | 🔒 私人 | 記憶、待辦、工作日誌、客戶相關、財務 |
| `lien2fish/fishing-tycoon` | 🔒 私人 | 漁船遊戲 |

### 第三步：掃過暫存區才 commit

```bash
python3 .claude/skills/safe-commit/check_staged.py
```

沒有 ❌ 才 commit。有 ❌ 就停下來問，不要自己判斷「應該還好」。

---

## 已知地雷

- 🔴 **`git ls-files`／`git diff --name-only`／`git log --name-only` 預設會把中文檔名
  輸出成八進位跳脫**（`reports/回購提醒_x.md` → `reports/\345\233\236...`）。
  拿去 `open()` 會開不到檔、拿去 `grep` 中文會永遠 0 命中，而且**兩者都不報錯**。
  **2026-08-21 一天之內因此誤判三次**：誤以為歷史已清乾淨、誤以為已 force push、
  全庫掃描靜默跳過所有中文檔名的檔案（漏掉 57 份含客戶個資的報告）。
  **任何用 git 列檔名的指令，一律加 `-c core.quotepath=false`。**
- **只靠「值的樣式」會漏。** 客戶名單的電話被 Excel 吃掉開頭的 0 變 9 碼，手機正則抓不到；
  只有姓名沒電話的 Markdown 報告，48 份全部漏掉。
  **要同時看：欄位標題、人名表格結構、值的樣式。**

- **`.gitignore` 不會讓已追蹤的檔案消失。** 加規則只擋新檔；既有的要 `git rm`。
- **`git rm` 不會清掉歷史。** 刪掉只是擋隨手瀏覽，任何人仍能從舊 commit 撈回。
  真的要清必須 `git filter-repo` ＋ force push（見下方流程）。
- **force push 之後 GitHub 仍會用 SHA 提供舊 commit**，直到它自己 GC。
  要徹底斷，**必須寫信給 GitHub Support 請他們清除快取**。這步最常被漏掉。
- **別人 fork 或 clone 過的副本控制不了。** 只要曾經公開過，就當作已外流。
- `git push --force` 與 `git reset --hard` 都在使用者的 deny 清單裡（刻意設的）。
  **不要用 `-f` 之類的寫法繞過**——請使用者自己用 `!` 前綴跑。
  要讓本機跟上被改寫的遠端，用 `git checkout -B main origin/main`（不在封鎖清單，且保留未追蹤檔案）。

---

## 萬一又漏出去了：止血流程

順序照做，每一步做完先驗證再進下一步。

1. **備份**——`cp` 到 `~/liam-workspace/backup/YYYYMMDD_公開repo移除/`，比對 SHA-256 確認一致
2. **確認沒有腳本依賴**——`grep -rn "<檔名>" --include=*.py --include=*.yml --include=*.sh .`
3. **從最新版移除**——`git rm` ＋ commit ＋ push（commit 訊息寫中性，不要變成尋寶圖）
4. **加 .gitignore** 擋掉整個資料夾，並實測 `git check-ignore -v` 確認規則命中
5. **全庫鏡像備份**——`git clone --mirror <url> ~/repo_backup_YYYYMMDD/<name>.git`
6. **改寫歷史**（在另一份新 clone 上做，不要在使用者的工作目錄動手）：
   ```bash
   pip3 install --quiet git-filter-repo
   git clone <url> ~/repo_backup_YYYYMMDD/rewrite && cd $_
   ~/Library/Python/3.9/bin/git-filter-repo --invert-paths --path <資料夾>/ --force
   ```
7. **驗證三件事**——⚠️ **每一條都必須加 `-c core.quotepath=false`**：
   ```bash
   git -c core.quotepath=false log --all --pretty=format: --name-only \
     | sort -u | grep -cE "^(<資料夾>)/"          # 要是 0
   git -c core.quotepath=false rev-list --all --objects \
     | grep -E "<資料夾>"                          # 要無輸出
   ```
   再把原始 HEAD `git archive` 出來 `diff -rq` 比對，確認其餘內容未動。

   **這裡踩過一次（2026-08-21）**：git 預設把非 ASCII 路徑輸出成八進位跳脫
   （`客戶名單/` 會變成 `\345\256\242\346\210\266...`），拿中文去 grep **永遠 0 命中**，
   於是「已清乾淨」與「遠端已推送」兩個判斷同時誤判。
   **中文路徑的專案，任何用 grep 比對 git 輸出的驗證都要先關掉 quotepath。**
8. **force push**——**請使用者自己跑**。推之前先確認遠端沒有新 commit
   （排程隨時在推，有新的就重做第 6 步）
9. **本機跟上**——`git fetch origin && git checkout -B main origin/main`
10. **寫信給 GitHub Support** 請求清除快取的舊 commit

---

## 這個專案的固定判斷

- **repo 是 public，這件事要一直記得。** 預設「不確定就不要進」。
- 客戶個資類的提醒**只走 Email，不 commit 報告**（壽險拜訪、生日、扶輪社已經是這樣做）。
- 身分證等最高敏感原始檔**只留本機**，不進任何 repo。
- 對外簡報／文宣要放公開處之前，**逐頁確認沒有客戶名、報價、庫存成本、個人財務**。
