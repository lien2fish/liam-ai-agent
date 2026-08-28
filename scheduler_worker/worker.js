/**
 * liam-scheduler —— 把「計時」搬離 GitHub Actions。
 *
 * 為什麼有這個東西（2026-08-28）：
 *   GitHub 的 schedule 是 best-effort。2026-08-26 還有 38 次觸發，08-27 剩 5 次、
 *   08-28 剩 1 次，早上整批客戶提醒連兩天沒跑，而且連負責抓漏的巡邏任務自己也
 *   沒被觸發——安全網跟被監控者同一條命。
 *
 *   但同一天手動 dispatch 的 14 支全部在幾秒內開始執行並成功。
 *   ⇒ GitHub 的「執行」沒問題，壞的只有「計時」。所以把計時搬到這裡，
 *     GitHub 只負責執行。
 *
 * ⚠️ 搬過來的 workflow 必須拿掉自己的 schedule 區塊，只留 workflow_dispatch。
 *    兩邊都留＝一天觸發兩次；daily_post 會變成發兩則限動，而 IG 發出去刪不掉。
 *
 * 沒有 KV、沒有狀態：用 event.scheduledTime（Cloudflare 給的「原定時間」，
 * 就算執行被延遲也還是原定值）去對照表，所以不會因為延遲而對到別的時段。
 */

const REPO = "lien2fish/liam-ai-agent";

// key = UTC 的 HH:MM，要跟 wrangler.toml 的 crons 對得上。
// 台灣時間 = UTC + 8。改時間要兩邊一起改，不然這裡對不到就什麼都不會做。
const SCHEDULE = {
  "00:17": ["policy_expiry_check.yml"], // 台灣 08:17 產險保單到期
  "00:23": ["birthday_reminder.yml"], // 台灣 08:23 壽險客戶生日
  "00:27": ["rotary_birthday_reminder.yml"], // 台灣 08:27 扶輪社友生日
  "00:37": ["daily_post.yml"], // 台灣 08:37 IG+FB 每日發文
  "00:43": ["life_visit_reminder.yml"], // 台灣 08:43 壽險固定拜訪
  "01:07": ["repurchase_reminder.yml"], // 台灣 09:07 三品牌回購提醒
};

// 這一輪負責回頭確認上面那些真的都跑了（台灣 10:30）。
// 安全網也留在這裡，不放回 GitHub——否則計時器壞掉時偵測器會一起壞。
const AUDIT_AT = "02:30";

const UA = "liam-scheduler/1";

function gh(env, path, init = {}) {
  return fetch(`https://api.github.com/repos/${REPO}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${env.GITHUB_PAT}`,
      Accept: "application/vnd.github+json",
      "User-Agent": UA,
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(init.headers || {}),
    },
  });
}

async function dispatch(env, wf) {
  const r = await gh(env, `/actions/workflows/${wf}/dispatches`, {
    method: "POST",
    body: JSON.stringify({ ref: "main" }),
  });
  // dispatch 成功是 204 No Content，不是 200
  if (r.status === 204) return { wf, ok: true };
  return { wf, ok: false, detail: `HTTP ${r.status} ${(await r.text()).slice(0, 200)}` };
}

/** 今天（台灣）這支有沒有執行紀錄——不分排程或手動。 */
async function ranToday(env, wf, now) {
  const r = await gh(env, `/actions/workflows/${wf}/runs?per_page=20`);
  if (!r.ok) return null; // 查不到就回 null，讓呼叫端知道是「不確定」而不是「沒跑」
  const twToday = new Date(now.getTime() + 8 * 3600e3).toISOString().slice(0, 10);
  return (await r.json()).workflow_runs.some(
    (x) => new Date(new Date(x.created_at).getTime() + 8 * 3600e3).toISOString().slice(0, 10) === twToday,
  );
}

/** 推 LINE。沒設定就靜默跳過——通知壞掉不該連累排程本身。
 *
 * ⚠️ 契約要跟 line_assistant/notify.py 完全一致：
 *    網址是「基底 + /notify」、token 走 Authorization header（不是放在 body）、
 *    body 只有 {text}。而且 User-Agent 不能用預設值——Cloudflare 會回 403，
 *    2026-08-25 就因此推播了好幾天都沒送出而沒人發現。
 */
async function notify(env, text) {
  if (!env.NOTIFY_URL || !env.NOTIFY_TOKEN) return;
  try {
    const r = await fetch(env.NOTIFY_URL.replace(/\/+$/, "") + "/notify", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + env.NOTIFY_TOKEN,
        "User-Agent": UA,
      },
      body: JSON.stringify({ text: String(text).slice(0, 900) }),
    });
    if (!r.ok) console.log(`notify 回 ${r.status}（不影響排程）`);
  } catch (e) {
    console.log("notify 失敗（不影響排程）：" + e);
  }
}

async function runSlot(env, key, now) {
  const wfs = SCHEDULE[key] || [];
  const results = [];
  for (const wf of wfs) results.push(await dispatch(env, wf));
  const bad = results.filter((r) => !r.ok);
  console.log(`[${key}] 觸發 ${results.length} 支，失敗 ${bad.length} 支`);
  if (bad.length) {
    await notify(
      env,
      "🔴 排程觸發失敗\n" + bad.map((b) => `・${b.wf}\n  ${b.detail}`).join("\n") +
        "\n\n這幾支今天不會自己跑，要手動補。",
    );
  }
}

async function audit(env, now) {
  const all = Object.values(SCHEDULE).flat();
  const missing = [];
  const unknown = [];
  for (const wf of all) {
    const ran = await ranToday(env, wf, now);
    if (ran === null) unknown.push(wf);
    else if (!ran) missing.push(wf);
  }
  console.log(`稽核：缺 ${missing.length} 支、查不到 ${unknown.length} 支`);
  if (missing.length || unknown.length) {
    await notify(
      env,
      "⚠️ 今天早上這幾支沒有執行紀錄\n" +
        missing.map((w) => "・" + w).join("\n") +
        (unknown.length ? "\n查詢失敗：" + unknown.join("、") : "") +
        "\n\n（計時已改由 Cloudflare 負責，這代表 dispatch 有送出但 GitHub 沒跑，或 token 有問題。）",
    );
  }
}

export default {
  async scheduled(event, env, ctx) {
    const now = new Date(event.scheduledTime); // 原定時間，不是實際執行時間
    const key = now.toISOString().slice(11, 16); // UTC HH:MM
    if (key === AUDIT_AT) return ctx.waitUntil(audit(env, now));
    return ctx.waitUntil(runSlot(env, key, now));
  },

  // 手動驗證用：GET /?key=00:37 會回報那個時段會觸發什麼（不實際觸發）。
  async fetch(request, env) {
    const key = new URL(request.url).searchParams.get("key");
    const body = key
      ? { slot: key, would_dispatch: SCHEDULE[key] || [] }
      : { schedule: SCHEDULE, audit_at: AUDIT_AT, note: "全部為 UTC；台灣時間 = UTC+8" };
    return new Response(JSON.stringify(body, null, 2), {
      headers: { "Content-Type": "application/json; charset=utf-8" },
    });
  },
};
