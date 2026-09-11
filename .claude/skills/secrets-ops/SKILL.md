---
name: secrets-ops
description: GitHub Actions Secrets 與各種金鑰的維運——21 把金鑰各自誰在用、壞了會連帶打死哪些系統、怎麼安全更新、有哪些到期規律。要新增或輪替任何 API key／token／密碼、排查「是不是金鑰過期了」、判斷某把金鑰的爆炸半徑、或處理 Cloudflare Worker secret 時載入。動到 IG_TOKEN、FB_PAGE_TOKEN、GMAIL_APP_PASSWORD、NOTION_TOKEN、GEMINI_KEY、OPENAI_API_KEY、ANTHROPIC_API_KEY、YT_* 、LINE_NOTIFY_*、WORKSPACE_PAT 任何一把之前先看這裡。
---

# 金鑰維運

19 個 workflow 共用 21 把金鑰。**一把掛掉會同時打死好幾個系統**，
所以動任何一把之前，先看清楚爆炸半徑。

---

## 一、怎麼更新（用腳本，不要每次手寫）

```bash
python3 scripts/set_secret.py --list                 # 看現有的與更新日期
python3 scripts/set_secret.py NAME                   # 隱藏輸入（需終端機）
python3 scripts/set_secret.py NAME --file value.txt  # 從檔案讀
```

值不經過命令列、不回顯、不進 shell history，也不會出現在輸出裡。
**空值會被擋下**——這正是 wrangler 那個坑，這支直接拒絕。

⚠️ **在 Claude Code 對話框裡跑隱藏輸入會失敗**（沒有互動終端機），
腳本會明講失敗。要嘛 `--file`，要嘛去 Terminal.app。

### GitHub PAT 只在 keychain（2026-08-27 起）

**不要再去讀 `~/.git-credentials`，那個檔已經刪了。** 原本 `credential.helper` 在本專案
repo 的 local config 多掛了一個 `store`，等於把一把**永不過期、含 `workflow` scope**
（＝能改 Actions＝能讀所有 Secrets）的 PAT 以明文長期放在磁碟上，還會被備份帶走。

現在統一走 keychain：

```python
out = subprocess.run(
    ["git", "credential", "fill"],
    input="protocol=https\nhost=github.com\n\n",
    capture_output=True, text=True,
    env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
).stdout
m = re.search(r"^password=(.+)$", out, re.M)
```

`GIT_TERMINAL_PROMPT=0` 是必要的——**背景／非互動情境下寧可快速失敗，不要卡在提示等輸入。**
已改的三支：`scripts/set_secret.py`、`scripts/ig_reauth.py`、`instagram/story_teaser.py`
（後者在 Actions 內仍優先用 `GITHUB_TOKEN`）。新寫的腳本要取 PAT 一律照這個寫法。

⚠️ **取 PAT 再打 api.github.com 有時會被權限守門擋下**
（「讀憑證→送網路」的形狀會被判定成外洩風險）。**那是對的，不要繞過**——
請使用者當場核准，或請他自己在終端機跑。

### 🖥 換機檢查清單（M5 Air）

keychain 不像檔案會被 rsync 帶走，**換機時這把 PAT 是會掉的**：

| 情況 | 要做什麼 |
|---|---|
| 走 Migration Assistant | 鑰匙圈會一起搬，通常什麼都不用做。到了先跑 `git push --dry-run` 驗一次 |
| 乾淨安裝 | 舊機先 `security find-internet-password -s github.com -w` 取出（**只在 Terminal.app 做，不要在 Claude Code 對話框**），或直接去 GitHub 產一把新的 |
| 新機第一次 push | git 會跳一次鑰匙圈授權，**要在有螢幕的情況下操作**；背景任務（SessionEnd 日誌推送）不會幫你跳窗 |
| 裝回 `gh` | 見專案 CLAUDE.md 技術環境；`~/bin/gh` wrapper 與 `~/bin/gh-bin` 都要複製，wrapper 不需改 |
| 裝回 `wrangler` | **OAuth 憑證同樣不會跟著搬**——`~/Library/Preferences/.wrangler/config/default.toml` 在新機是空的。要在 Terminal.app 跑 `npx wrangler login`（會開瀏覽器授權），驗證用 `npx wrangler whoami` |

⚠️ **2026-09-10 補：`wrangler login` 有兩個會互相掩蓋的坑。**

1. **`| pipe` 進 stdin 會讓它判定成非互動環境**，於是不走 OAuth、改要求 `CLOUDFLARE_API_TOKEN`。
   錯誤訊息只講 token，**不會告訴你其實是沒登入**。所以 `login` 一定要單獨跑、不接 pipe；
   寫 secret 那行才用 pipe（避開「互動輸入讀到空值卻印 Success」那個坑）。
2. **callback port 8976 被佔用時，login 會直接失敗**——常見於前一次啟動沒清乾淨。
   `wrangler login` 底下有四層進程（zsh → npm exec → wrangler → node cli.js），
   **只 kill 外層不會放掉 port**。查 `lsof -nP -i :8976`，
   或改用 `npx wrangler login --callback-port <其他埠>`。

⚠️ **2026-09-06 補：`~/.git-credentials` 不是唯一的明文藏匿處。**
`git clone https://TOKEN@github.com/...` 會把憑證寫進該 repo 的 `.git/config` remote URL，
**08-27 那次清理漏掉了兩個**（`~/liam-workspace`、`~/Downloads/fishing-tycoon`），
同一把 PAT 因此又在磁碟上明文躺了十天。全機複查一次：

```bash
find ~ -maxdepth 4 -name config -path '*/.git/*' \
  -exec grep -l 'https://[^@/]*@github\.com' {} +
```

修法：`git remote set-url origin https://github.com/OWNER/REPO.git`（拿掉 `TOKEN@`），
改走 keychain。**改完一定要用 `GIT_TERMINAL_PROMPT=0 git push --dry-run` 驗**——
背景任務（SessionEnd 日誌推送）不會有人幫它按授權視窗。

⛔ **不要為了省事把 `store` 加回來。**

---

## 二、爆炸半徑（動之前先查這張表）

| 金鑰 | 連帶影響 | 風險 |
|---|---|---|
| `GMAIL_APP_PASSWORD` | **7 個**：生日／壽險拜訪／扶輪生日／保單到期／回購／營收週報／YT 留言＋頻道日報 | 🔴 **失效是靜默的**——你只會覺得「最近沒收到提醒」，不會有任何錯誤通知。**超過一週沒收到提醒信就該主動查** |
| `NOTION_TOKEN` | **6 個 workflow**：生日／壽險拜訪／市場日報／月報／回購／漁獲行情，**＋ LINE 助理的 `/客戶` `/買` `/庫存`** | 🔴 高。**這把也存在兩個地方**，見下方 |
| `GEMINI_KEY` | **5 個**：IG 留言回覆／市場日報／漁獲行情，＋IG 發文與 YT 影片的 fallback | 🟡 **免費額度共用會互搶**，不是失效也可能不夠用 |
| `IG_TOKEN` | **3 個**：IG+FB 發文／留言回覆／限動預告 | 🔴 見下方到期規律 |
| `ANTHROPIC_API_KEY` | 3 個：IG 發文／YT 影片（**都有 Gemini fallback**）＋**LINE 手機助理的自然語言（無 fallback，直接回 `Claude 401`）** | 🟡 **這把存在兩個地方**：GitHub Secret ＋ Cloudflare Worker secret。**輪替時兩邊都要換**——2026-08-29 就是只換了 GitHub，助理整整三天回 401 卻沒人知道（斜線指令不走 Claude，照常能用，所以症狀只出現在自然語言） |
| `OPENAI_API_KEY` | 2 個：IG 插圖／YT 場景圖（**沒有 fallback**） | 🟡 餘額歸零就停 |
| `YT_API_KEY` | 2 個：YT 留言通知／頻道日報 | 🟢 無到期問題 |
| `LINE_NOTIFY_URL` ＋ `LINE_NOTIFY_TOKEN` | 1 個：Token 到期提醒的 LINE 推播 | 🟢 掛了只是少一條通知管道，Email 還在 |
| `FB_PAGE_TOKEN` | **目前 0 個真的在用**——FB 跨發走 IG 的 `cross_post_ids` | 🟢 只有 `token_expiry_check` 會抓到它壞掉 |
| `WORKSPACE_PAT` | **它就是 keychain 那把主 PAT，不是獨立金鑰**（2026-09-06 比對指紋確認）。scope `repo`+`workflow`、**四個 repo 全部可讀寫**、永不過期。直接用它的有 2 個 workflow（扶輪社生日、YT 配樂）＋ hyperframes 試算取素材 | 🔴 **`workflow` scope ＝ 能改 Actions ＝ 能把其餘 20 把 Secret 全部印出來、也能觸發對外發布的 workflow。外洩＝整套自動化淪陷** |
| `HF_TOKEN` | 已停用 | — |

### 🔁 同一把金鑰散在三個地方（GitHub Secret ＋ 兩個 Cloudflare Worker）

**輪替時漏掉任何一邊 = 那邊靜默壞掉。** 已經踩過三次：
2026-08-29（`ANTHROPIC_API_KEY`）、2026-09-10（`NOTION_TOKEN`）、
2026-09-11（`GITHUB_PAT`，見下方案例）。

⚠️ **有兩個 Worker，不是一個。** 只查 `line_assistant` 會漏掉 `scheduler_worker`：

| 位置 | 持有 |
|---|---|
| GitHub Secrets | 21 把 |
| Cloudflare `liam-assistant`（`line_assistant/`）| `ANTHROPIC_API_KEY`、`OPENAI_API_KEY`、`NOTION_TOKEN`、`GITHUB_PAT`、`NOTIFY_TOKEN`、LINE 三把 |
| Cloudflare `liam-scheduler`（`scheduler_worker/`）| **`GITHUB_PAT`**、`NOTIFY_TOKEN`、`NOTIFY_URL` |

| 金鑰 | 漏掉 Worker 的後果 |
|---|---|
| `ANTHROPIC_API_KEY` | 助理自然語言回 `Claude 401`（斜線指令照常，**症狀不明顯**）|
| `NOTION_TOKEN` | 助理 `/客戶` `/買` `/庫存` 全查不到 |
| `OPENAI_API_KEY` | 助理的語音轉文字（Whisper）|
| `GITHUB_PAT` | assistant：`/待辦` `/筆記` 寫不進 repo、**`/查` 每支都回 401 而顯示成「全部失敗」**<br>scheduler：🔴 **所有排程停擺**（它靠 PAT 打 workflow_dispatch）|
| `NOTIFY_TOKEN` | 自動化推播送不出去 |

```bash
cd line_assistant   && npx wrangler secret list    # 確認漏了誰
cd scheduler_worker && npx wrangler secret list    # ⚠️ 這個也要查
```

**標準輪替流程**（缺一不可）：

1. `python3 scripts/set_secret.py NAME --file <檔案>`
2. `cd line_assistant && printf '%s' "$(tr -d '\r\n' < ../<檔案>)" | npx wrangler secret put NAME`
3. **`GITHUB_PAT`／`NOTIFY_TOKEN` 還要再做 `scheduler_worker` 一次**
4. **每一邊各實跑一次驗收**——GitHub 端重跑一支用到它的 workflow、
   assistant 用 LINE 實際打一則、scheduler 看隔天排程有沒有照常觸發

#### 案例：2026-09-11「自動化全部失敗」其實是助理自己壞了

Lien 用 LINE 打 `/查`，回報全部失敗、要檢查連線或金鑰。
實際查 Actions：**當天 67 次執行、66 成功 0 失敗**，任務根本沒問題。

根因＝2026-09-06 輪替主 PAT 時只更新了 keychain 與 GitHub Secret，
漏掉 `liam-assistant` 的 `GITHUB_PAT`。舊的已撤銷，`/查` 對每支 workflow 打 API 都 401，
逐一累加就變成「全部失敗」。

**這個症狀最會騙人**：助理報的是「任務失敗」，但壞的是助理自己。
⇒ **看到 `/查` 回報全滅，先用 Actions API 對一次**，
免金鑰就讀得到：`curl -s "https://api.github.com/repos/lien2fish/liam-ai-agent/actions/runs?per_page=100"`。
真的全滅通常是 scheduler 掛了（那會是「沒有 run」而不是「run 失敗」）。

⚠️ 同一次也發現 `NOTION_TOKEN`（09-10 輪替）同樣沒同步到 Worker，一併補灌。
**輪替後沒人用到的功能不會報錯，等到用才發現——所以輪替當下就要把三個地方一起做完。**

---

## 三、到期規律

✅ **`token_expiry_check.yml` 每天 08:45 自動盯 IG／FB**，剩 30/21/14/10/7/5/3/2/1 天
分批 Email＋LINE 提醒，失效當天 run 直接變紅。**IG 那兩把不需要靠人記日期了。**
其餘金鑰目前沒有自動監控。

| 項目 | 規律 | 症狀 |
|---|---|---|
| **IG token 本身**（`expires_at`）| **60 天**，2026-10-24 到期 | 三個 IG 系統同時掛。⚠️ 舊紀錄寫「永不過期」是錯的，2026-08-25 推翻 |
| **IG 資料存取權**（`data_access_expires_at`）| 授權當天 +90 天，2026-11-23 | 同上。⚠️ `fb_exchange_token` 換發**不會**重置，必須走使用者授權對話框 |
| **IG／FB session** | **無到期日，隨時** | `OAuthException` **190 / subcode 460**——改 FB 密碼或 Meta 安全性重設就會被作廢。`fb_exchange_token` 救不回來 |
| FB Page token | `expires_at`＝0 | **但會隨 user session 一起死**。重簽＝用 user token 打 `GET /{page-id}?fields=access_token` |
| Gemini 免費額度 | 每天重置（台北 15:00）| 429 `RESOURCE_EXHAUSTED` |
| YouTube API 配額 | 每天重置（台北 15:00）| 403，三頻道共用一天 6 支 |
| Gmail OAuth | 已發 Production，不再 7 天過期 | `invalid_grant` 才是真的被撤銷 |
| GitHub PAT | 永不過期 | 只存在 keychain（2026-08-27 起，明文檔已刪）。**換機會掉**，見上方檢查清單 |

**IG／FB 重新授權**：在 Terminal.app 跑 `python3 scripts/ig_reauth.py`，
細節見 `ig-fb-auto` skill。

---

## 四、Cloudflare Worker 的 secret

LINE 助理的金鑰放在 Worker（`wrangler secret`），跟 GitHub Secrets 是兩套。

🔴 **`wrangler secret put` 不能在 Claude Code 對話框裡跑。**
那裡沒有互動終端機，互動提示讀到空值也照樣印「✨ Success」——
結果是 secret 存成**空字串而毫無徵兆**（2026-08-24 因此卡了三輪）。

```bash
# 非互動寫法（可在對話框裡跑）
printf '%s' "$(tr -d '\r\n' < 檔案)" | npx wrangler secret put NAME
```

**「✨ Success」不算驗收。** 一定要實際打一次 API 確認——
2026-08-25 更新 `NOTIFY_TOKEN` 就是靠 `curl /notify` 回 200 才確定真的寫進去。

⚠️ **wrangler secret 讀不回來。** 舊值沒留存就只能輪替一組新的，
輪替前先確認**沒有別的東西在用**（`grep -rn NAME .github/workflows/`）。

---

## 五、動手前的檢查

1. **這把金鑰壞了會死幾個系統？** 查第二節的表。7 個系統的那把要特別小心。
2. **有沒有 fallback？** 沒有 fallback 的（`OPENAI_API_KEY`）壞掉就是開天窗。
3. **更新完怎麼驗收？** 不是「API 回 200」——是實際跑一次用到它的 workflow 看綠燈。
4. **值會不會外洩？** 不要貼進對話、不要 echo 進指令、暫存檔用完當下就 trash。
   見 `safe-commit` skill。

相關：`ops-rescue`（金鑰以外的故障排查）、`ig-fb-auto`（IG 重新授權流程）、
`gmail-ops`（Gmail OAuth 重新授權）、`safe-commit`（敏感資料處置）。
