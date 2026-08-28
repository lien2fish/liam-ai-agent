# liam-scheduler

把六支有時效的任務的**計時**從 GitHub Actions 搬到 Cloudflare Worker。
GitHub 只負責執行，不負責計時。

## 為什麼

2026-08-28 查到：GitHub 的 schedule 觸發數 08-26 有 38 次、08-27 剩 5 次、
08-28 剩 1 次。早上整批客戶提醒**連兩天沒跑**，而負責抓漏的巡邏任務自己也沒被
觸發——安全網跟被監控者同一條命，所以沒有人發現。

但同一天手動 `workflow_dispatch` 的 14 支**全部在幾秒內開始執行並成功**。
⇒ 執行沒問題，壞的只有計時。

## 管哪幾支

| 台灣時間 | UTC | workflow |
|---|---|---|
| 08:17 | 00:17 | `policy_expiry_check.yml` 產險保單到期 |
| 08:23 | 00:23 | `birthday_reminder.yml` 壽險客戶生日 |
| 08:27 | 00:27 | `rotary_birthday_reminder.yml` 扶輪社友生日 |
| 08:37 | 00:37 | `daily_post.yml` IG＋FB 每日發文 |
| 08:43 | 00:43 | `life_visit_reminder.yml` 壽險固定拜訪 |
| 09:07 | 01:07 | `repurchase_reminder.yml` 三品牌回購提醒 |
| 10:30 | 02:30 | 回頭稽核上面六支有沒有真的跑，缺就推 LINE |

## ⛔ 最重要的一條

**搬過來的 workflow 一定要拿掉自己的 `schedule:` 區塊，只留 `workflow_dispatch`。**
兩邊都留＝一天觸發兩次。`daily_post` 會變成發兩則限動，而 **IG 發出去 API 刪不掉**。

反過來也一樣：要搬回 GitHub 就先把這裡的時段拿掉，再把 cron 加回 workflow。

## 部署

```bash
cd scheduler_worker
npx wrangler deploy
```

金鑰要在**真正的終端機**（Terminal.app）跑，不能在 Claude Code 的對話框：

```bash
npx wrangler secret put GITHUB_PAT     # 需要對 liam-ai-agent 的 Actions 寫入權限
npx wrangler secret put NOTIFY_URL     # liam-assistant 的 /notify 網址
npx wrangler secret put NOTIFY_TOKEN   # 與 liam-assistant 的 NOTIFY_TOKEN 同值
```

⚠️ `wrangler secret put` 在沒有互動 TTY 的環境會讀到空值、存成**空字串**，
然後照樣印「✨ Success」。非互動要灌就用：

```bash
printf '%s' "$(tr -d '\r\n' < 金鑰檔)" | npx wrangler secret put NAME
```

**建議 `GITHUB_PAT` 用 fine-grained token**，只給 `lien2fish/liam-ai-agent`
這一個 repo 的 `Actions: read and write`。現有那把 classic PAT（`repo`+`workflow`、
永不過期）雖然也能用，但它能改 Actions 就等於能讀所有 Secrets，爆炸半徑太大。

## 驗證

不必等到隔天早上：

```bash
# 對照表有沒有載對（不會實際觸發）
curl -s https://liam-scheduler.<你的子網域>.workers.dev | python3 -m json.tool

# 某個時段會觸發什麼
curl -s 'https://liam-scheduler.<...>.workers.dev/?key=00:37'

# 直接觸發一次 cron（本機模擬，不碰正式環境）
npx wrangler dev --test-scheduled
curl 'http://localhost:8787/__scheduled?cron=37+0+*+*+*'
```

正式環境要驗，最快是看隔天早上 GitHub 上那六支有沒有出現 `workflow_dispatch`
的執行紀錄（不是 `schedule`）：

```bash
gh run list --workflow=daily_post.yml --limit 3 --json event,createdAt,conclusion
```

## 改時間

`worker.js` 的 `SCHEDULE` 與 `wrangler.toml` 的 `crons` **必須同時改**。
只改一邊會靜默失效——對不到 key 就什麼都不做，也不會報錯。改完跑一次交叉檢查：

```bash
node --input-type=module -e "$(sed 's/^export default/const _d =/' worker.js)
import {readFileSync} from 'node:fs';
const b=readFileSync('wrangler.toml','utf8').split('crons = [')[1].split(']')[0];
const s=new Set();
for(const c of [...b.matchAll(/\"([0-9,*\/ -]+)\"/g)].map(m=>m[1])){
  const [mm,hh]=c.trim().split(/\s+/);
  for(const h of hh.split(','))for(const m of mm.split(','))
    s.add(String(h).padStart(2,'0')+':'+String(m).padStart(2,'0'));}
const w=new Set([...Object.keys(SCHEDULE),AUDIT_AT]);
console.log([...w].filter(k=>!s.has(k)).length||[...s].filter(k=>!w.has(k)).length?'❌ 對不上':'✅ 一致');"
```

## 還留在 GitHub schedule 上的

其餘任務（股市日報、漁獲行情、YouTube 三支、Gmail、Token 檢查、週報、月報、
IG 限動預告、IG 留言回覆、排程巡邏）**維持原樣**。先搬最有時效的六支，
跑幾天穩了再決定要不要搬其餘的。
