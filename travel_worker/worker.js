/* 親子旅遊 PWA — 後端代打 Worker
 *
 * 目的：讓一般使用者免自備金鑰就能用 AI 規劃，同時把帳單風險鎖死。
 * 金鑰存在 Cloudflare Secret，前端永遠看不到。
 *
 * ⚠️ 下方 PLAN_SCHEMA 與 planPrompt 由 docs/travel/app.js 複製而來，
 *    兩邊必須一致。改了前端的 schema 或 prompt，這裡要一起改並重新部署。
 *    （前端自帶金鑰模式用它自己那份，後端模式用這份。）
 */
const ALLOWED_ORIGINS = [
  "https://lien2fish.github.io",
  "http://localhost:8899", // 本機測試
];
const DAILY_GLOBAL_CAP = 10; // 全站每日熔斷：沒有導購收入抵銷，抓保守值（每月最壞約 NT$750）
const DAILY_PER_IP_CAP = 5;  // 每人每日
const CATS = ["景點", "住宿", "餐飲", "交通", "其他"];
const MODEL = "claude-haiku-4-5"; // 不可帶 output_config.effort，Haiku 不支援會 400

const PLAN_SCHEMA = {
  type: "object",
  additionalProperties: false,
  required: ["plans"],
  properties: {
    plans: {
      type: "array",
      description: "兩種風格明顯不同的行程方案",
      items: {
  type: "object",
  additionalProperties: false,
  required: ["title", "theme", "summary", "notes", "accommodation", "days"],
  properties: {
    title: { type: "string", description: "行程標題，簡短有畫面感" },
    theme: { type: "string", description: "這個方案的風格標籤，4-8 字，例：室內文化路線、戶外放電路線" },
    summary: { type: "string", description: "這趟行程的設計邏輯：為什麼這樣排、動線與體力如何安排，一段話" },
    notes: { type: "string", description: "整趟的注意事項與提醒（帶小孩要準備什麼、時段陷阱等）" },
    accommodation: {
      type: "array",
      description: "建議住宿；同一區連住就合併成一筆，換區才多一筆",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["nights", "nights_count", "area", "reason", "price_range", "cost_per_night"],
        properties: {
          nights: { type: "string", description: "住哪幾晚，例：第1-2晚" },
          nights_count: { type: "integer", description: "這筆住幾晚（數字），用於花費試算" },
          area: { type: "string", description: "建議住宿區域，只寫地圖查得到的乾淨地名（例：礁溪、羅東、花蓮市），不加括號補述" },
          reason: { type: "string", description: "為什麼住這區：動線、親子友善設施、生活機能" },
          price_range: { type: "string", description: "每晚價位帶，例：$3,000-4,500" },
          cost_per_night: { type: "integer", description: "每晚每間房概估（新台幣），用於花費試算" },
        },
      },
    },
    days: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["day", "theme", "rainy_alternative", "spots"],
        properties: {
          day: { type: "integer", description: "第幾天，從 1 開始" },
          theme: { type: "string", description: "當日主題一句話，例：海邊放電日" },
          rainy_alternative: { type: "string", description: "當日下雨時的室內替代方案（具體地點或做法）" },
          spots: {
            type: "array",
            items: {
              type: "object",
              additionalProperties: false,
              required: ["name", "reason", "age_range", "indoor", "duration_minutes", "category", "opening_hours", "cost_estimate"],
              properties: {
                name: { type: "string", description: "地點的官方正式名稱，必須是真實存在、地圖上查得到的地點" },
                reason: { type: "string", description: "一句話說明為什麼適合這個家庭，要具體對應孩子年齡與需求" },
                age_range: { type: "string", description: "適合年齡帶，例：3-8歲、全年齡" },
                indoor: { type: "boolean", description: "true=室內可避雨，false=室外" },
                duration_minutes: { type: "integer", description: "建議停留時間（分鐘）" },
                category: { type: "string", enum: CATS },
                opening_hours: { type: "string", description: "營業時間與公休日；不確定就寫「請自行確認」" },
                cost_estimate: { type: "integer", description: "每人預估花費（新台幣），免費景點填 0" },
              },
            },
          },
        },
      },
    },
  },
      },
    },
  },
};

function planPrompt(c) {
  const kids = c.kids.length ? c.kids.map((a) => a + "歲").join("、") : "無";
  const extra = [
    c.wants.length ? `偏好類型：${c.wants.join("、")}` : "",
    c.pace ? `步調：${c.pace}` : "",
  ].filter(Boolean).join("\n");
  return `你是熟悉台灣各地親子旅遊的規劃專家。請為以下家庭規劃**兩種風格明顯不同**的行程方案。

目的地：${c.region}
天數：${c.days} 天
大人：${c.adults} 位　小孩：${kids}
交通方式：${c.transport}
單日車程上限：${c.maxDrive} 分鐘
預算：${c.budget ? "NT$" + c.budget : "未設定"}
特殊需求：${c.needs || "無"}
${extra}

【兩個方案的差異】
- 必須是**真的不同的玩法**，不是同一份行程換順序或換餐廳
- 兩案的景點重疊不得超過一個；住宿區域也盡量不同
- 用 theme 標出風格差異，例如：室內文化路線 vs 戶外放電路線、經典必玩 vs 在地深度、
  緊湊多點 vs 悠閒少點。依這個家庭的條件選兩個最合適的方向
- summary 要讓人一眼看出「什麼情況下該選這個方案」

【硬條件｜兩個方案都要遵守】
- 依孩子年齡與體力篩選，每個景點都要說明為什麼適合
- 同一天景點之間的車程總和不得超過 ${c.maxDrive} 分鐘
- 交通方式為 ${c.transport}，據此決定景點之間的可行性${
    c.transport === "大眾運輸"
      ? `
  · 可用工具包含：**高鐵**（跨縣市長途最快）、台鐵（區域與高鐵到不了的城鎮）、
    捷運與市區公車（市內）、國道與公路客運（客運才到得了的景區）、計程車或包車接駁
  · **跨縣市或長距離移動優先考慮高鐵**，不要一律假設搭台鐵
  · 高鐵站常在市郊，抵達後要接駁（台鐵、接駁公車、計程車），請把接駁一併說明
  · 大眾運輸到不了的景點就**不要排**，或明確寫出從哪個站搭什麼車、車程多久`
      : ""
  }
- 每天至少安排一個室內景點（indoor=true）作為雨天備案
- 11:30-13:00、17:30-19:00 前後必須有餐飲安排
- 避開常見公休（多數館所週一休）
- **同一個方案內，同一個地點只能出現一次**：不同天不可重複排同一個景點或餐廳，
  也不要換個寫法重排同一個地方（例如「羅東夜市」與「羅東觀光夜市」算同一個）。
  ${c.days} 天就要有 ${c.days} 天份的不同內容，想不出來寧可該天少排一個點

【住宿建議】
- 只推薦**住宿區域**，**絕對不要指定飯店或民宿名稱**——訂不到房會造成實質困擾
- area 只寫**地圖查得到的乾淨地名**（如「礁溪」「羅東」「花蓮市」），**不要加括號或「周邊」「一帶」等補述**，細節寫在 reason
- reason 說明選這區的理由：離隔天行程近、有親子設施、生活機能好、停車方便等
- 同一區連住就合併成一筆；只有換區才多一筆
- ${c.days > 1 ? `這趟 ${c.days} 天，需要 ${c.days - 1} 晚住宿` : "當日來回，accommodation 回傳空陣列"}
- cost_per_night 是**每晚每間房**的概估，不是每人

【地點名稱｜最重要】
- name 必須是地圖查得到的**單一具體地點正式全名**，之後要拿去查座標
- 嚴禁描述性寫法：不可出現「在地」「附近」「或」「等」「（如…）」，也不可只寫「海鮮餐廳」「素食小館」這種類別
- 餐飲同樣要給得出正式店名；**寫不出具體店名就不要排這個餐飲點**，改把該時段併入鄰近有明確名稱的地點
- 不要自創、不要用俗稱或簡稱，不要把兩個地點合併成一個名字

【誠實原則】
- 只依「適合這個家庭」推薦，不考慮任何商業因素
- opening_hours 不確定就寫「請自行確認」，不要猜
- cost_estimate 是概估，抓不準就給保守數字
- 全部用繁體中文`;
}
/* ---------- 工具 ---------- */
const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json" } });

function cors(res, origin) {
  const h = new Headers(res.headers);
  h.set("Access-Control-Allow-Origin", origin || ALLOWED_ORIGINS[0]);
  h.set("Access-Control-Allow-Headers", "content-type");
  h.set("Access-Control-Allow-Methods", "POST, OPTIONS");
  h.set("Vary", "Origin");
  return new Response(res.body, { status: res.status, headers: h });
}

async function sha256(str) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/* Turnstile 為選用：沒設 TURNSTILE_SECRET 就跳過（先上線、要開放大眾前再加） */
async function verifyTurnstile(token, env, request) {
  if (!env.TURNSTILE_SECRET) return true;
  if (!token) return false;
  const form = new FormData();
  form.append("secret", env.TURNSTILE_SECRET);
  form.append("response", token);
  form.append("remoteip", request.headers.get("CF-Connecting-IP") || "");
  const r = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
    method: "POST", body: form,
  });
  const d = await r.json().catch(() => ({}));
  return !!d.success;
}

/* 只收前端表單欄位，不接受任意 prompt——否則等於開放別人用你的金鑰跑任何東西 */
function sanitize(p) {
  const s = (v, max) => String(v == null ? "" : v).slice(0, max);
  const n = (v, def, min, max) => {
    const x = parseInt(v, 10);
    return isNaN(x) ? def : Math.min(max, Math.max(min, x));
  };
  return {
    region: s(p.region, 40),
    days: n(p.days, 2, 1, 10),
    adults: n(p.adults, 2, 0, 20),
    kids: Array.isArray(p.kids) ? p.kids.slice(0, 8).map((k) => n(k, 6, 0, 18)) : [],
    budget: p.budget ? n(p.budget, 0, 0, 10000000) : null,
    transport: p.transport === "大眾運輸" ? "大眾運輸" : "自駕",
    maxDrive: n(p.maxDrive, 90, 20, 480),
    needs: s(p.needs, 200),
    wants: Array.isArray(p.wants) ? p.wants.slice(0, 12).map((w) => s(w, 20)) : [],
    pace: s(p.pace, 10),
  };
}

export default {
  async fetch(request, env, ctx) {
    const origin = request.headers.get("Origin") || "";
    const allowed = ALLOWED_ORIGINS.includes(origin);

    if (request.method === "OPTIONS") return cors(new Response(null, { status: 204 }), origin);
    if (request.method !== "POST") return cors(json({ error: "method_not_allowed" }, 405), origin);
    // 弱防線：擋得住瀏覽器跨站，擋不住 curl。真正的財務保護是下方全站熔斷。
    if (!allowed) return cors(json({ error: "forbidden" }, 403), origin);

    let body;
    try {
      body = await request.json();
    } catch (e) {
      return cors(json({ error: "bad_request" }, 400), origin);
    }

    if (!(await verifyTurnstile(body.turnstileToken, env, request)))
      return cors(json({ error: "verification_failed", message: "驗證失敗，請重新整理再試" }, 403), origin);

    const params = sanitize(body.params || {});
    if (!params.region)
      return cors(json({ error: "bad_request", message: "請填目標城市／地區" }, 400), origin);

    const today = new Date().toISOString().slice(0, 10);

    // 全站每日熔斷（最重要的一道：保護帳單）
    const gKey = `global:${today}`;
    const gCount = parseInt((await env.LIMITS.get(gKey)) || "0", 10);
    if (gCount >= DAILY_GLOBAL_CAP)
      return cors(json({ error: "service_busy", message: "今日 AI 規劃額度已滿，明天再試，或到設定貼上自己的 API 金鑰不受限制" }, 429), origin);

    // 每 IP 每日次數
    const ip = request.headers.get("CF-Connecting-IP") || "unknown";
    const ipKey = `ip:${today}:${ip}`;
    const ipCount = parseInt((await env.LIMITS.get(ipKey)) || "0", 10);
    if (ipCount >= DAILY_PER_IP_CAP)
      return cors(json({ error: "rate_limited", message: "今日規劃次數已用完，明天再來，或到設定貼上自己的 API 金鑰" }, 429), origin);

    // 熱門組合快取：同樣條件直接回，成本歸零
    const cacheKey = `plan:${await sha256(JSON.stringify(params))}`;
    const cached = await env.CACHE.get(cacheKey);
    if (cached) return cors(json({ plans: JSON.parse(cached), cached: true }), origin);

    const resp = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key": env.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model: MODEL,
        max_tokens: 16000,
        output_config: { format: { type: "json_schema", schema: PLAN_SCHEMA } },
        messages: [{ role: "user", content: planPrompt(params) }],
      }),
    });

    if (!resp.ok) {
      console.error("anthropic_error", resp.status, (await resp.text()).slice(0, 500));
      return cors(json({ error: "upstream_error", message: "AI 服務暫時不可用，稍後再試" }, 502), origin);
    }

    const data = await resp.json();
    if (data.stop_reason === "refusal")
      return cors(json({ error: "refusal", message: "AI 婉拒了這個請求，換個描述試試" }, 400), origin);
    if (data.stop_reason === "max_tokens")
      return cors(json({ error: "truncated", message: "行程太長被截斷，請減少天數再試" }, 400), origin);

    const text = (data.content || []).filter((b) => b.type === "text").map((b) => b.text).join("");
    let plans;
    try {
      plans = JSON.parse(text).plans || [];
    } catch (e) {
      return cors(json({ error: "parse_error", message: "AI 回傳格式異常，請再試一次" }, 502), origin);
    }
    if (!plans.length)
      return cors(json({ error: "empty", message: "沒有產生行程，換個條件試試" }, 502), origin);

    // 成功才計數：失敗不該扣使用者額度
    ctx.waitUntil(Promise.all([
      env.LIMITS.put(gKey, String(gCount + 1), { expirationTtl: 172800 }),
      env.LIMITS.put(ipKey, String(ipCount + 1), { expirationTtl: 172800 }),
      env.CACHE.put(cacheKey, JSON.stringify(plans), { expirationTtl: 604800 }),
    ]));

    return cors(json({ plans }), origin);
  },
};
