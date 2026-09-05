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
// 值可以是檔名字串（每天跑），或帶條件的物件：
//   { wf, dow: 1 }  只在 UTC 星期一跑（0=日）
//   { wf, dom: 1 }  只在 UTC 每月 1 日跑
// 條件用 UTC 判斷，而這些任務都排在 UTC 上午＝台灣同一天的白天，日期不會跨掉。
const SCHEDULE = {
  "00:03": [{ wf: "weekly_revenue_sprint.yml", dow: 1 }], // 台灣一 08:03 營收衝刺週報
  "00:13": ["gmail_automation.yml"], // 台灣 08:13 Gmail 清理＋新聞摘要
  "00:17": ["policy_expiry_check.yml"], // 台灣 08:17 產險保單到期
  "00:23": ["birthday_reminder.yml"], // 台灣 08:23 壽險客戶生日
  "00:27": ["rotary_birthday_reminder.yml"], // 台灣 08:27 扶輪社友生日
  "00:29": ["festival_reminder.yml"], // 台灣 08:29 節慶送禮備料提醒
  "00:33": ["yt_channel_report.yml"], // 台灣 08:33 The Unknown Hour 頻道日報
  "00:37": ["daily_post.yml"], // 台灣 08:37 IG+FB 每日發文
  "00:43": ["life_visit_reminder.yml"], // 台灣 08:43 壽險固定拜訪
  "00:47": ["token_expiry_check.yml"], // 台灣 08:47 IG／FB Token 到期檢查
  "00:53": [{ wf: "weekly_review.yml", dow: 1 }], // 台灣一 08:53 AI 工作週報
  "00:57": [{ wf: "notion_monthly_report.yml", dom: 1 }], // 台灣 1 日 08:57 Notion 月報
  "01:07": ["repurchase_reminder.yml"], // 台灣 09:07 三品牌回購提醒
  "01:37": ["seafood_prices.yml"], // 台灣 09:37 漁獲市場行情
  // 02:07 yt_auto_post.yml（The Unknown Hour）2026-09-05 停排程：開台 66 天只到
  // 11 訂閱／2,738 觀看，最近 19 天僅 +1 訂閱、留言全 0，與五個品牌零關聯。
  // 程式與 workflow 都保留，要跑走 workflow_dispatch。
  "04:07": ["market_daily.yml"], // 台灣 12:07 每日股市分析
  "10:08": ["ig_story_teaser.yml"], // 台灣 18:08 IG 限動預告（接 18:00 的 Reels）
};

// 每 30 分鐘一次的高頻任務——不進 SCHEDULE，因為它跟「幾點幾分」無關。
// 由 cron 的 */30 打進來，在每個 :00 與 :30 觸發，與時段表和稽核並行不衝突。
const EVERY_30MIN = ["ig_comment_reply.yml"];

// 每小時一次——掛在 */30 的 :00 那次，不必為它多開一條 cron。
// 留言回覆多數情況只是把已回過的跳過（判斷方式是問 API 有沒有本頻道的回覆），
// 真正呼叫 Gemini 的次數很少；每次上限 5 則，避免吃掉共用的免費額度。
const EVERY_HOUR = ["yt_comment_reply.yml"];

const name = (job) => (typeof job === "string" ? job : job.wf);

/** 帶條件的任務今天到底該不該跑。 */
function due(job, now) {
  if (typeof job === "string") return true;
  if (job.dow !== undefined && now.getUTCDay() !== job.dow) return false;
  if (job.dom !== undefined && now.getUTCDate() !== job.dom) return false;
  return true;
}

// 回頭確認上面那些真的都跑了。安全網留在這裡，不放回 GitHub——
// 否則計時器壞掉時偵測器會一起壞。
//
// ⚠️ 分兩輪，因為稽核只對「已經過去的時段」有意義：限動預告排在 UTC 10:08，
//    早上那輪（UTC 02:30）跑的時候它根本還沒到，一起查會每天誤報一次「沒執行」。
// key＝稽核時間（UTC），value＝這一輪負責回頭檢查 SCHEDULE 的哪些時段。
const AUDITS = {
  // 台灣 10:30——查凌晨到 02:30 之間（台灣早上）那一批
  "02:30": [
    "00:03", "00:13", "00:17", "00:23", "00:27", "00:29", "00:33",
    "00:37", "00:43", "00:47", "00:53", "00:57", "01:07", "01:37",
  ],
  // 台灣 20:30——查下午到傍晚那兩支，外加高頻的留言回覆今天有沒有跑過
  "12:30": ["04:07", "10:08"],
};

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
  const wfs = (SCHEDULE[key] || []).filter((j) => due(j, now)).map(name);
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

async function audit(env, key, now) {
  const all = (AUDITS[key] || [])
    .flatMap((slot) => SCHEDULE[slot] || [])
    .filter((j) => due(j, now))
    .map(name)
    .concat(key === "12:30" ? EVERY_30MIN.concat(EVERY_HOUR) : []);
  const missing = [];
  const unknown = [];
  for (const wf of all) {
    const ran = await ranToday(env, wf, now);
    if (ran === null) unknown.push(wf);
    else if (!ran) missing.push(wf);
  }
  console.log(`[${key}] 稽核 ${all.length} 支：缺 ${missing.length}、查不到 ${unknown.length}`);

  // SCHEDULE 加了新時段卻忘了掛進 AUDITS，就再也沒有人回頭查它——
  // 這種漏法是靜默的，所以每天主動比對一次。
  const covered = new Set(Object.values(AUDITS).flat());
  const orphan = Object.keys(SCHEDULE).filter((slot) => !covered.has(slot));
  if (orphan.length && key === Object.keys(AUDITS)[0]) {
    await notify(env, "⚠️ 這些排程時段沒有任何一輪稽核在看：" + orphan.join("、"));
  }

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
    const jobs = [];

    // 高頻任務先處理，且不受下面的分支影響——02:30 與 12:30 同時是稽核輪，
    // 若寫成 if/else 就會每天少跑兩次留言回覆。
    //
    // 失敗只寫 log 不推 LINE：一天 48 次，真的壞掉會洗掉整個月的推播額度。
    // 漏跑由 12:30 那輪稽核統一報一次（AUDITS 的 12:30 有把 EVERY_30MIN 算進去）。
    if (key.endsWith(":00") || key.endsWith(":30")) {
      jobs.push(
        (async () => {
          const hourly = key.endsWith(":00") ? EVERY_HOUR : [];
          for (const wf of EVERY_30MIN.concat(hourly)) {
            const r = await dispatch(env, wf);
            console.log(`[${key}] 高頻 ${wf} ${r.ok ? "已觸發" : "失敗：" + r.detail}`);
          }
        })(),
      );
    }

    jobs.push(AUDITS[key] ? audit(env, key, now) : runSlot(env, key, now));
    return ctx.waitUntil(Promise.all(jobs));
  },

  /**
   * GET /            對照表（公開，不含機密）
   * GET /?key=00:37  那個時段會觸發什麼（不實際觸發）
   * GET /selftest    實際驗三個 secret 的「值」對不對，需 Bearer NOTIFY_TOKEN
   *
   * 為什麼要有 selftest：`wrangler secret list` 只列名字不列值，
   * 而 `wrangler secret put` 在沒有互動 TTY 時會把值存成空字串卻照樣印 Success。
   * 所以「名字在」完全不代表「值是對的」，一定要讓 Worker 真的拿去用一次。
   */
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/selftest") {
      const auth = request.headers.get("Authorization") || "";
      if (!env.NOTIFY_TOKEN || auth !== "Bearer " + env.NOTIFY_TOKEN) {
        return new Response("unauthorized", { status: 401 });
      }
      const out = {};
      // ① GITHUB_PAT 讀取權：列得出 workflow 就代表 token 有效且看得到這個 repo
      const r1 = await gh(env, "/actions/workflows?per_page=1");
      out.github_read = r1.status === 200 ? "✅ 200" : `❌ HTTP ${r1.status}`;
      // ② GITHUB_PAT 寫入權：拿一支「只列 issue、不對外」的任務當測試靶
      const r2 = await dispatch(env, "claude_task_runner.yml");
      out.github_dispatch = r2.ok ? "✅ 204（Actions 寫入權正常）" : `❌ ${r2.detail}`;
      // ③ NOTIFY_URL + NOTIFY_TOKEN：真的推一則出去
      out.notify_configured = env.NOTIFY_URL ? "✅ 有設" : "❌ 沒設";
      await notify(env, "✅ liam-scheduler 自我測試：三個設定都通了");
      return new Response(JSON.stringify(out, null, 2), {
        headers: { "Content-Type": "application/json; charset=utf-8" },
      });
    }

    const key = url.searchParams.get("key");
    const now = new Date();
    const body = key
      ? {
          slot: key,
          would_dispatch: (SCHEDULE[key] || []).filter((j) => due(j, now)).map(name),
          all_in_slot: (SCHEDULE[key] || []).map(name),
          plus_every_30min:
            key.endsWith(":00")
              ? EVERY_30MIN.concat(EVERY_HOUR)
              : key.endsWith(":30")
                ? EVERY_30MIN
                : [],
        }
      : {
          schedule: SCHEDULE,
          every_30min: EVERY_30MIN,
          every_hour: EVERY_HOUR,
          audits: AUDITS,
          note: "全部為 UTC；台灣時間 = UTC+8",
        };
    return new Response(JSON.stringify(body, null, 2), {
      headers: { "Content-Type": "application/json; charset=utf-8" },
    });
  },
};
