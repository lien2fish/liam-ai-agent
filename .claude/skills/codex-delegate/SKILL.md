---
name: codex-delegate
description: Claude 當總管、Codex 當子代理的協作手冊——判斷要不要交給 Codex、要不要先討論、怎麼派工（codex exec／resume／fork）、worktree 隔離、審核清單、派工紀錄與門檻檢視。任何考慮把工作交給 Codex、Lien 提到 Codex／ChatGPT 協作、或派工紀錄滿 10 筆要檢視時載入。
---

# Claude × Codex 協作手冊

> 2026-10-20 Lien 授權：Claude 自行決定交不交、要不要討論；Codex 的產出一律經 Claude 審核才回報。
> Codex 額度＝ChatGPT 會員，Claude 額度＝Claude Code 訂閱，**兩邊都不另外花錢**，代價是額度消耗。

## 角色

| | Claude | Codex |
|---|---|---|
| 定位 | 總管：拆任務、派工、審核、回報 | 執行者 |
| 知道什麼 | 記憶、偏好、品牌紅線、過去決定 | 只有 `AGENTS.md`、skills、任務說明裡寫的 |
| 對 Lien | 唯一窗口 | 不直接回報 |

## 一、交不交、要不要討論

| 情況 | 做法 |
|---|---|
| 小到「寫說明比自己做久」 | **自己做** |
| 需要記憶／品牌判斷／海鮮事實／文案 | **自己做** |
| 對外發布、客戶個資、金鑰、commit 落點 | **自己做**（⛔ 絕不交） |
| 單一做法、錯了影響小 | **直接派工** |
| 多種做法、可能有隱藏邊界、動共用程式 | **先討論**：唯讀提方案→我追問邊界→定驗收→才動手 |
| 自己也不確定哪個好 | **fork 兩條**各試一種，比對 |
| 大量讀檔、機械性批次修改、第二意見審查 | **派工**（這類反而省 Claude 額度） |

討論通常 1~2 輪收，方案、邊界、驗收三樣講清楚就動手。

## 二、派工流程

```bash
# ① 準備：獨立 worktree（work/ 已 gitignore）＋回歸基準
git worktree add work/2 -b codex/<任務>
python3 <腳本> <輸入> "$SCRATCH/baseline.xxx"     # 改動前先存基準

# ② 派工（cd 進 worktree；</dev/null 防卡 stdin；-o 拿最後回覆）
cd work/2
codex exec -s read-only        -o "$SCRATCH/out.txt" "任務" </dev/null 2>"$SCRATCH/err.txt"   # 審查／提方案
codex exec -s workspace-write --add-dir "$SCRATCH" -o "$SCRATCH/out.txt" "任務" </dev/null 2>"$SCRATCH/err.txt"  # 修改

# ③ 延續討論／分岔
codex exec resume --last "追問"          # 或 resume <session-id>
codex exec fork <session-id> "改試另一種做法"

# token 用量
grep -A1 'tokens used' "$SCRATCH/err.txt" | tail -1
```

### 任務說明一定要有

1. **只准改哪些檔**，不准 commit／push
2. **已知事實**（我查到的、試過不行的），省它重踩
3. **驗收條件附數字**，要它自己跑過並回報數字
4. 程式風格：跟周邊一致、不加多餘註解與錯誤處理
5. 繁體中文回報

## 三、審核清單（最關鍵，不可省）

- [ ] `git diff` 只動到准改的檔、沒有順手改別處
- [ ] **自己補邊界測試**——Codex 只會測我指定的案例（10-20 只測粉紅色，深紅魚身只剩 7.6%）
- [ ] 看實際產出（圖就看圖），不只信它回報的數字
- [ ] 回歸：跟基準比，差異要有解釋
- [ ] 審查類：逐條驗證，標「真 bug／取捨／誤報」，嚴重度自己重估

不過 → 退回並附具體反例，或我直接改寫（小改動改寫比來回快）。

## 四、收尾

```bash
git add <檔> && git commit -m "..."            # 在 worktree commit
cd "<repo 根>" && git merge --ff-only codex/<任務>
git worktree remove work/2 && git branch -d codex/<任務>
git push origin main   # 被拒＝自動化剛推過 → git pull --rebase --autostash origin main 再推
```

回報 Lien：哪部分是 Codex 做的、「直接派工」或「討論 N 輪」、討論改掉什麼、驗了什麼、剩什麼限制。

## 五、派工紀錄與門檻檢視

每次派工後追加一列到 `~/.codex/delegation_log.tsv`：

```
日期 任務 方式 輪數 Codex_tokens 結果(照單全收／小修／我重寫) Codex獨家發現 備註
```

**每滿 10 筆，或任一邊被限速時，主動向 Lien 報數字並建議：**

| 訊號 | 調整 |
|---|---|
| 「我重寫」> 1/3 | 拉高門檻，少交 |
| Codex 常抓到我漏的 | 降低門檻，多交審查 |
| 限速 | 拉高門檻或減討論輪數 |
| 討論常 > 2 輪 | 檢討我的任務說明，不是門檻 |

## 六、權限護欄

| sandbox | 用途 | 能做 |
|---|---|---|
| `read-only` | 審查、調查、提方案 | 只讀 |
| `workspace-write` | 修改 | 只寫 worktree（＋`--add-dir` 指定的暫存），無網路 |
| 不開放 | — | push、對外 API、改 main |

## 七、環境與地雷

| 項目 | 說明 |
|---|---|
| 安裝 | `npm i -g @openai/codex`（nvm 底下）；登入在 `~/.codex/auth.json`（ChatGPT.app 登入共用） |
| 設定正本 | 專案 `AGENTS.md`→symlink `CLAUDE.md`；`.agents/skills/*`→symlink `.claude/skills/*`。**只改 `.claude/` 原版**。新增 skill 若要給 Codex 用，要另外 `ln -s ../../.claude/skills/<名> .agents/skills/<名>`（本 skill 刻意不連） |
| 自動匯入 | `~/.codex/config.toml` 的 `external-agent-import-sync-enabled = false`（10-20 關）。打開會把 Claude 設定整批「Claude→Codex」取代、蓋掉 symlink |
| 舊副本備份 | `~/.codex/backup_import_20261020/` |
| 能不能叫到 | Mac 上的 session（含 Remote Control）✅；claude.ai/code 雲端 session ❌（沒裝也沒登入） |
| macOS 沒有 `timeout` | 用 Bash tool 的 timeout 參數 |
| black hook | Edit `.py` 會觸發 black 重排整檔 → 改既有檔的最小 diff 用 Bash 寫入 |
| Codex 會寫到 `/tmp` | 它可能自建備份在 `/tmp`，收尾時順手看一眼 |
