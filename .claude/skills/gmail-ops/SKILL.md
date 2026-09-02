---
name: gmail-ops
description: Gmail 自動化腳本與 OAuth 維運：月度清理、新聞摘要、雙模式認證、token 失效時的重新授權完整步驟。遇到 invalid_grant 或要改 Gmail 腳本時載入。
---

## Gmail 自動化腳本系統

### 本機 Crontab（僅剩 1 條）
| 腳本 | 排程 | 說明 |
|------|------|------|
| `cache_cleanup.sh` | `0 6 * * *` | Mac 快取清理，只能本機跑 |

> Gmail 清理、新聞摘要、IG 發文、Notion 月報均已移至 GitHub Actions（見上方總覽）

### Gmail 腳本認證方式（2026-05-24 更新）
兩支腳本均支援雙模式：
- **GitHub Actions**：讀環境變數 `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` / `GMAIL_REFRESH_TOKEN`
- **本機執行**：fallback 讀 `~/.config/gmail-cleanup-token.json`（gitignore，不進 repo）

### Gmail 產出去向

| 產出 | 去向 | 進版控？ |
|------|------|---------|
| 清理報告 | **Email 寄給 Lien**，本機留 `reports/gmail_cleanup_YYYY-MM.md` | ❌ 已 gitignore |
| 執行 log | `/tmp/gmail_cleanup.log` | ❌ 純暫存 |
| 新聞摘要 | `今日新聞摘要.md`（每日覆寫）＋ `day/新聞日報_*.pdf` | ✅ 公開新聞，不敏感 |

🔴 **清理報告不可以進公開 repo。** 報告表格列出各寄件者清了幾封，
**只要某銀行的數字 >0，就等於對外證實這個信箱是該行客戶**。
2026-09-03 改成寄 Email，並把 05~09 五份既有報告與含它的 PDF 從版控移除
（備份在 `liam-workspace/backup/20260903_公開repo移除/`）。
⚠️ **但歷史 commit 裡還在**，要徹底清除得走 `filter-repo` ＋ force push，見 `safe-commit` skill。

寄信沿用 `GMAIL_APP_PASSWORD`（與回購提醒同一把）。**未設就靜默跳過**，
不會弄壞清理本身——本機測試不必配置也能跑。

### Gmail OAuth Token
| 項目 | 路徑 |
|------|------|
| Token 檔 | `~/.config/gmail-cleanup-token.json` |
| 憑證檔 | `~/.config/gmail-cleanup-credentials.json` |
| 授權腳本 | `gmail_auth_setup.py` |

> **2026-07-12：OAuth 同意畫面已發布 Production**（GCP 專案 `liam-gmail-cleanup`），refresh token **不再每 7 天過期**，已根治。若仍出現 `invalid_grant`，那是其他原因（撤銷/改密碼），走下方重新授權流程即可。瀏覽器一律用 **Safari**。

**Token 失效症狀**：`invalid_grant: Token has been expired or revoked.`

**重新授權步驟（已驗證可行）：**
1. 生成 OAuth URL：
   ```bash
   python3 -c "
   import json,urllib.parse
   c=json.load(open('/Users/lien/.config/gmail-cleanup-credentials.json'))
   cl=c.get('installed',c)
   print('https://accounts.google.com/o/oauth2/v2/auth?'+urllib.parse.urlencode({'client_id':cl['client_id'],'redirect_uri':'http://localhost:8888','response_type':'code','scope':'https://www.googleapis.com/auth/gmail.modify','access_type':'offline','prompt':'consent'}))
   "
   ```
2. 在 Chrome 開啟 URL → 登入 `lien2fish@gmail.com` → 點「進階」→「前往（不安全）」→「允許」
3. 瀏覽器跳到 `http://localhost:8888/?code=4/0A...`，複製完整網址
4. 執行換取 token：
   ```bash
   python3 -c "
   import json,urllib.parse,urllib.request
   CODE='貼上授權碼'
   c=json.load(open('/Users/lien/.config/gmail-cleanup-credentials.json'))
   cl=c.get('installed',c)
   r=json.loads(urllib.request.urlopen(urllib.request.Request('https://oauth2.googleapis.com/token',data=urllib.parse.urlencode({'code':CODE,'client_id':cl['client_id'],'client_secret':cl['client_secret'],'redirect_uri':'http://localhost:8888','grant_type':'authorization_code'}).encode(),headers={'Content-Type':'application/x-www-form-urlencoded'},method='POST')).read())
   json.dump({'token':r['access_token'],'refresh_token':r['refresh_token'],'token_uri':'https://oauth2.googleapis.com/token','client_id':cl['client_id'],'client_secret':cl['client_secret'],'scopes':['https://www.googleapis.com/auth/gmail.modify']},open('/Users/lien/.config/gmail-cleanup-token.json','w'),indent=2)
   print('✅ Token 儲存完成')
   "
   ```
- **注意**：`gmail_auth_setup.py` 的 Playwright 自動化流程因 Google 封鎖自動化瀏覽器而無法使用，改用上述手動方式

---
