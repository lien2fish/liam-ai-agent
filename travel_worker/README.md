# 親子旅遊 PWA · 後端代打 Worker

讓一般使用者**免自備金鑰**就能用 AI 規劃。金鑰存在 Cloudflare Secret，前端永遠看不到。

## 三道防線

| 防線 | 設定值 | 作用 |
|------|--------|------|
| Anthropic Console 月支出上限 | US$30 | **平台級硬限制，最可靠**，程式有 bug 也擋得住 |
| 全站每日熔斷 `DAILY_GLOBAL_CAP` | 40 次／日 | 保護帳單，每月最壞約 NT$1,000 |
| 每 IP 每日 `DAILY_PER_IP_CAP` | 5 次／日 | 擋單人重度使用 |
| CORS Origin 白名單 | github.io | 弱防線，擋瀏覽器跨站、擋不住 curl |
| Turnstile | **選用** | 真正擋 bot；沒設 `TURNSTILE_SECRET` 就跳過 |

另有熱門組合快取（7 天），同樣條件直接回，成本歸零。

## 部署步驟

```bash
cd travel_worker
npm install -g wrangler          # 只需一次
wrangler login                   # 會開瀏覽器要你授權

# ① 建立兩個 KV namespace，各會印出一組 id
wrangler kv namespace create LIMITS
wrangler kv namespace create CACHE
# → 把印出的 id 貼進 wrangler.toml 對應的 PUT_..._HERE

# ② 存金鑰（貼上後按 Enter，不會顯示在畫面上）
wrangler secret put ANTHROPIC_API_KEY

# ③ 部署
wrangler deploy
# → 會印出網址，形如 https://travel-planner.<你的帳號>.workers.dev
```

部署後把網址填進 `docs/travel/app.js` 最上方的 `WORKER_URL`，commit 推上去即生效。

## 測試

```bash
# 應回 403（Origin 不符）
curl -s -X POST https://travel-planner.<帳號>.workers.dev \
  -H 'content-type: application/json' -d '{"params":{"region":"宜蘭"}}'

# 應正常回傳兩個方案
curl -s -X POST https://travel-planner.<帳號>.workers.dev \
  -H 'content-type: application/json' \
  -H 'Origin: https://lien2fish.github.io' \
  -d '{"params":{"region":"宜蘭","days":2,"adults":2,"kids":[5],"maxDrive":90,"transport":"自駕"}}' \
  | head -c 400
```

看即時 log：`wrangler tail`

## 調整用量上限

改 `worker.js` 最上方的 `DAILY_GLOBAL_CAP` / `DAILY_PER_IP_CAP`，重新 `wrangler deploy`。

有真實用量再往上調。**沒有導購收入抵銷，每一次規劃都是純支出。**

## ⚠️ 維護注意

`worker.js` 裡的 `PLAN_SCHEMA` 與 `planPrompt` 是從 `docs/travel/app.js` 複製而來，**兩邊必須一致**：

- 前端自帶金鑰模式用 `app.js` 那份
- 後端代打模式用 Worker 這份

改了任何一邊的 schema 或 prompt，另一邊要同步改並重新部署。可用這個指令檢查是否一致：

```bash
node -e "
const fs=require('fs');
const w=fs.readFileSync('travel_worker/worker.js','utf8');
const a=fs.readFileSync('docs/travel/app.js','utf8');
const grab=(s,x,y)=>s.slice(s.indexOf(x),s.indexOf(y)).trim();
console.log('schema:', grab(w,'const PLAN_SCHEMA','\nfunction planPrompt')===grab(a,'const PLAN_SCHEMA','\nfunction planPrompt')?'一致':'不一致');
console.log('prompt:', grab(w,'function planPrompt','\n/* ---------- 工具')===grab(a,'function planPrompt','/* 找出跨天重複')?'一致':'不一致');
"
```

## 開放大眾前還要做

- [ ] 加 Turnstile（建 widget → 前端放 site key → `wrangler secret put TURNSTILE_SECRET`）
- [ ] 首次使用引導、空狀態、必填引導、額度用完的人話提示
