/**
 * LINE 手機助理 — Cloudflare Worker
 *
 * 這支檔案不含任何商業資訊。身分、品牌、資料庫欄位、自動化任務全部
 * 從 profile.js 讀——導入新使用者只改那一個檔，程式碼一行不動。
 *
 * 兩個入口：
 *   POST /line    LINE webhook（你傳訊息／語音進來）
 *   POST /notify  自動化推播（GitHub Actions 呼叫，帶 Bearer NOTIFY_TOKEN）
 *
 * 能做：記待辦、存筆記到知識庫、查客戶、查庫存、查銷售紀錄、語音轉文字。
 * 不能做：跑腳本、剪片、改本機檔案——那些走 claude.ai/code。
 *
 * ⚠️ LINE 的兩個計費／時效規則決定了這支程式的結構：
 *   1. reply 訊息「不計」免費額度，push 訊息「計」。所以對話一律走 reply，
 *      只有 /notify 與逾時 fallback 才用 push。額度＝輕用量方案 200 則／月。
 *   2. replyToken 一分鐘失效且只能用一次。因此同一次事件的所有回覆必須
 *      合併成「一次請求、最多 5 個 message object」，不能像 Telegram 那樣連發。
 */

import PROFILE from "./profile.js";

const ANTHROPIC_URL = "https://api.anthropic.com/v1/messages";
const NOTION_URL = "https://api.notion.com/v1";
const NOTION_VERSION = "2022-06-28";
const GH = PROFILE.github || {};
const WORKSPACE_REPO = GH.workspaceRepo || null;
const AGENT_REPO = GH.agentRepo || null;
const TODO_PATH = GH.todoPath || "TODO.md";
const KNOWLEDGE_DIR = GH.knowledgeDir || "knowledge";

// 沒設定的區塊就關掉對應功能，工具清單與指令表都會跟著少。
const HAS_NOTES = Boolean(WORKSPACE_REPO);
const HAS_ACTIONS = Boolean(AGENT_REPO) && Object.keys(PROFILE.workflows || {}).length > 0;
const HAS_CRM = Boolean(PROFILE.crm);
const HAS_INVENTORY = (PROFILE.inventory || []).length > 0;
// 寫入庫存預設關閉。範本保持唯讀——手機上改數字沒有復原鍵。
const CAN_WRITE_INVENTORY = HAS_INVENTORY && PROFILE.inventoryWrite === true;
const MAX_INV_UPDATE = 50;
const PENDING_TTL = 600;

const WORKFLOWS = PROFILE.workflows || {};

// 會對外發布、收不回來的任務。不接受斜線指令。
const PUBLISHES = new Set(PROFILE.publishes || []);
const LINE_API = "https://api.line.me/v2/bot";
const LINE_DATA_API = "https://api-data.line.me/v2/bot";

// LINE 單則文字上限 5,000 字，抓 4,500 保守；一次請求最多 5 個 message object。
const MAX_LINE = 4500;
const MAX_OBJECTS = 5;

// replyToken 官方是 60 秒失效，留 10 秒安全邊際；超過就改走 push（會花額度）。
const REPLY_WINDOW_MS = 50000;

// LINE Console 按「Verify」時送的假 token，要略過不處理。
const VERIFY_TOKEN = "00000000000000000000000000000000";

const HISTORY_TURNS = 8;

const SYSTEM = [
  PROFILE.owner?.intro,
  PROFILE.business,
  PROFILE.tone ? `回覆規則：\n${PROFILE.tone}` : "",
  PROFILE.context,
]
  .filter(Boolean)
  .join("\n\n");

const HELP = [
  "🆓 打指令＝直接執行，不經過 AI，不花錢",
  "",
  HAS_CRM && "/客戶 王先生      查客戶（也可打 /c）",
  HAS_CRM && "/買 王先生        查他買過什麼（/s）",
  HAS_INVENTORY && `/庫存 關鍵字      查庫存（/i）。打品牌名列出該品牌全部`,
  HAS_NOTES && `/待辦 內容        記進 ${TODO_PATH}（/t）`,
  HAS_NOTES && "/筆記 內容        原樣存進知識庫，不整理（/n）",
  HAS_ACTIONS && "/查 自動化        看排程任務有沒有掛（/k）",
  HAS_ACTIONS && "/跑 任務名        立刻跑一次（/r）",
  CAN_WRITE_INVENTORY && "/改庫存           貼一份表更新數量（/u，先看差異再確認）",
  "",
  "💰 講人話或傳語音＝走 AI",
  "",
  "需要判斷的事、自由問法，還有語音訊息",
  "（會轉文字＋整理分類存進知識庫），都走這條。",
  HAS_NOTES && "",
  HAS_NOTES && "🎙 按住麥克風講十分鐘是這個 bot 最有價值的用法——",
  HAS_NOTES && "那些知識只在你腦裡。",
]
  .filter((x) => x !== false && x !== undefined)
  .join("\n");

const BRANDS = (PROFILE.inventory || []).map((x) => x.brand);
const CATEGORIES = Object.keys(PROFILE.knowledgeCategories || { misc: "其他" });
const CATEGORY_HINT = Object.entries(PROFILE.knowledgeCategories || {})
  .map(([k, v]) => `${k} ${v}`)
  .join("／");

// 工具清單依設定組出來——沒設定的區塊不會出現在 Claude 眼前，
// 它就不會提議做不到的事，也省下每則訊息的固定 token。
const TOOLS = [
  HAS_NOTES && {
    name: "add_todo",
    description: `把一件待辦事項加進 ${TODO_PATH}。用於「記得要…」「提醒我…」這類明確的行動項目。`,
    input_schema: {
      type: "object",
      properties: { text: { type: "string", description: "待辦內容，一句話寫清楚要做什麼" } },
      required: ["text"],
    },
  },
  HAS_NOTES && {
    name: "save_note",
    description:
      "把一段知識或想法存進知識庫。用於口述的專業知識、判斷方法、處理手法、經營心得——這些只存在他腦裡、值得長期留存的內容。",
    input_schema: {
      type: "object",
      properties: {
        category: { type: "string", enum: CATEGORIES, description: `分類：${CATEGORY_HINT}` },
        title: { type: "string", description: "短標題，5-15 字" },
        content: {
          type: "string",
          description: "整理過的內容。保留他講的所有具體細節與數字，不要精簡掉。",
        },
      },
      required: ["category", "title", "content"],
    },
  },
  HAS_CRM && {
    name: "query_customer",
    description: `在客戶總表查客戶。可查到 ${(PROFILE.crm.customer.fields || []).join("、")}。`,
    input_schema: {
      type: "object",
      properties: { name: { type: "string", description: "客戶姓名或公司名，可只給部分字" } },
      required: ["name"],
    },
  },
  HAS_CRM && {
    name: "query_sales",
    description: "查某位客戶買過什麼。回傳該客戶的銷售紀錄，最近的排前面。",
    input_schema: {
      type: "object",
      properties: { customer: { type: "string", description: "客戶名稱" } },
      required: ["customer"],
    },
  },
  HAS_ACTIONS && {
    name: "run_workflow",
    description:
      "觸發 GitHub Actions 自動化任務，讓它現在就跑一次（平常是排程自動跑）。標示⚠️的會對外發布內容，執行前務必先問清楚是不是真的要發。",
    input_schema: {
      type: "object",
      properties: {
        task: {
          type: "string",
          enum: Object.keys(WORKFLOWS),
          description: `要跑哪個任務。⚠️ 會對外發布、收不回來的：${[...PUBLISHES].join("、") || "（無）"}`,
        },
      },
      required: ["task"],
    },
  },
  HAS_ACTIONS && {
    name: "check_workflows",
    description:
      "查 GitHub Actions 自動化任務目前的健康狀況，回報哪些失敗、哪些正常、哪些還沒跑過。用於「自動化有沒有掛」「昨天的報告有跑嗎」這類問題。純唯讀，不會觸發任何任務。",
    input_schema: {
      type: "object",
      properties: {
        filter: {
          type: "string",
          description: "留空或填「自動化」查全部；填單一任務名稱則只查那一個",
        },
      },
      required: [],
    },
  },
  CAN_WRITE_INVENTORY && {
    name: "preview_inventory_update",
    description:
      "使用者貼了一份庫存表要更新數量時用這個。它會比對現況並回一份「要改什麼」的差異清單，但**不會真的寫入**——使用者確認後才會套用。永遠先用這個，絕對不要跳過預覽直接寫。",
    input_schema: {
      type: "object",
      properties: {
        text: { type: "string", description: "使用者貼的整份庫存表原文，一行一個品項" },
      },
      required: ["text"],
    },
  },
  CAN_WRITE_INVENTORY && {
    name: "confirm_inventory_update",
    description:
      "把上一步預覽過的庫存變更真的寫進資料庫。只有在使用者明確表示確認之後才能呼叫。使用者沒說確認就不要用。",
    input_schema: { type: "object", properties: {}, required: [] },
  },
  HAS_INVENTORY && {
    name: "query_inventory",
    description: `查庫存（${BRANDS.join("／")}）。指定 brand 會列出該品牌全部品項；keyword 則跨品牌搜尋。回傳品項、數量、價格。`,
    input_schema: {
      type: "object",
      properties: {
        keyword: { type: "string", description: "品項關鍵字。留空則列出全部。" },
        brand: {
          type: "string",
          enum: [...BRANDS, "全部"],
          description: "要查哪個品牌的庫存，預設全部",
        },
      },
      required: ["keyword"],
    },
  },
].filter(Boolean);

// 每個品牌的 Notion 欄位名稱很可能不一樣，由 profile 各給一組對照。
// 價格刻意連欄位名一起顯示，免得把進價看成售價。
const INV_FIELDS = Object.fromEntries(
  (PROFILE.inventory || []).map((x) => [x.brand, x])
);

function invRow(props, map) {
  const name = plain(props[map.name || "品名"]);
  if (!name) return "";
  const qty = plain(props[map.qty]);
  const unit = map.unit ? plain(props[map.unit]) : "";
  const price = map.price ? plain(props[map.price]) : "";
  const parts = [name];
  parts.push(qty ? qty + (unit ? " " + unit : "") : "缺貨");
  // 欄位名可能很醜（進貨價_斤），priceLabel 讓畫面顯示統一的說法。
  if (price) parts.push(`${map.priceLabel || map.price} ${price}`);
  return parts.join("　");
}

// ── 貼庫存表：解析 → 比對 → 差異預覽 → 確認才寫 ────────────────
//
// 「手機打錯字沒得檢查」的解法是那張差異清單：按下確認之前，
// 你就看得到它把你的字理解成什麼。所以絕不直接寫入。

// 每行取最後一個數字當數量，前面當品名。「白蝦 8 斤」「2兩烏魚子 5」都吃得下。
function parseInventoryLine(line) {
  const t = String(line || "").trim();
  if (!t) return null;
  const nums = [...t.matchAll(/[0-9]+(?:\.[0-9]+)?/g)];
  if (!nums.length) return null;
  const last = nums[nums.length - 1];
  const name = t.slice(0, last.index).replace(/[\s:：,，=＝\-–]+$/, "").trim();
  const tail = t.slice(last.index + last[0].length).trim();
  // 數字後面只容許短單位。整句話裡剛好有數字的不算一筆。
  if (!name || tail.length > 4) return null;
  return { name, qty: Number(last[0]) };
}

function parseInventoryText(text) {
  const lines = String(text || "").split(/[\n\r]+/);
  const items = [];
  const skipped = [];
  for (const line of lines) {
    const t = line.trim();
    if (!t) continue;
    const parsed = parseInventoryLine(t);
    if (parsed) items.push(parsed);
    else skipped.push(t);
  }
  return { items, skipped };
}

// 只做精確比對，不猜。「白蝦」對不到「活白蝦」就報告，不要自作聰明改錯品項。
async function buildInventoryDiff(env, items) {
  const index = new Map(); // 品名 → [{brand, pageId, qtyField, current}]
  for (const cfg of PROFILE.inventory || []) {
    const db = env[cfg.db];
    if (!db) continue;
    const rows = await notionQueryAll(env, db, null);
    for (const row of rows) {
      const name = plain(row.properties[cfg.name || "品名"]).trim();
      if (!name) continue;
      const prop = row.properties[cfg.qty];
      const current = prop && prop.type === "number" ? prop.number : null;
      if (!index.has(name)) index.set(name, []);
      index.get(name).push({ brand: cfg.brand, pageId: row.id, qtyField: cfg.qty, current });
    }
  }

  const changes = [];
  const same = [];
  const missing = [];
  const ambiguous = [];

  for (const item of items) {
    const hits = index.get(item.name);
    if (!hits || !hits.length) {
      missing.push(item.name);
      continue;
    }
    if (hits.length > 1) {
      ambiguous.push(`${item.name}（${hits.map((h) => h.brand).join("、")}都有）`);
      continue;
    }
    const hit = hits[0];
    if (hit.current === item.qty) {
      same.push(item.name);
      continue;
    }
    changes.push({
      name: item.name,
      brand: hit.brand,
      pageId: hit.pageId,
      qtyField: hit.qtyField,
      from: hit.current,
      to: item.qty,
    });
  }
  return { changes, same, missing, ambiguous };
}

function renderInventoryDiff(diff, skipped) {
  const out = [];
  if (diff.changes.length) {
    out.push(`要改 ${diff.changes.length} 筆：`);
    for (const c of diff.changes) {
      out.push(`・${c.name}　${c.from == null ? "（空白）" : c.from} → ${c.to}`);
    }
  }
  if (diff.same.length) out.push("", `數字沒變 ${diff.same.length} 筆，略過`);
  if (diff.missing.length) out.push("", `⚠️ 找不到這些品項（不會動）：`, ...diff.missing.map((x) => `・${x}`));
  if (diff.ambiguous.length) out.push("", `⚠️ 品名重複、無法判斷（不會動）：`, ...diff.ambiguous.map((x) => `・${x}`));
  if (skipped && skipped.length) out.push("", `⚠️ 看不懂這幾行：`, ...skipped.slice(0, 5).map((x) => `・${x}`));
  out.push("");
  out.push(diff.changes.length ? "確認無誤就回覆　/確認" : "沒有要改的東西。");
  return out.join("\n");
}

// ---------- LINE ----------

// ⚠️ 安全邊界：這支 bot 能查客戶姓名、電話、消費紀錄。
// 底下兩個驗證是唯一擋住外人的東西，一律「預設拒絕」——
// 設定沒填、header 沒帶、格式不對，全部回 false，不要寫成「比對不到才擋」。

function timingSafeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string") return false;
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

// X-Line-Signature = base64( HMAC-SHA256( 原始 request body, Channel secret ) )
// 必須用「原始字串」算，不能先 JSON.parse 再 stringify——序列化差一個空白就對不起來。
async function verifySignature(env, rawBody, signature) {
  if (!env.LINE_CHANNEL_SECRET || !signature) return false;
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(env.LINE_CHANNEL_SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const mac = await crypto.subtle.sign("HMAC", key, enc.encode(rawBody));
  const expected = btoa(String.fromCharCode(...new Uint8Array(mac)));
  return timingSafeEqual(expected, signature);
}

// 只有擁有者本人能用。LINE 官方帳號誰都能加好友，沒有這道就等於把 CRM 打開給所有人。
function isOwner(env, event) {
  const allowed = String(env.LINE_USER_ID || "");
  const sender = String(event?.source?.userId || "");
  if (!allowed || !sender) return false;
  if (allowed.startsWith("PUT_")) return false;
  return timingSafeEqual(allowed, sender);
}

// 把任意段落攤平成 LINE message object；超過 5 個就截斷，不要靜默丟掉。
function toMessages(parts) {
  const chunks = [];
  for (const part of parts) {
    const t = String(part == null ? "" : part).trim();
    if (!t) continue;
    for (let i = 0; i < t.length; i += MAX_LINE) chunks.push(t.slice(i, i + MAX_LINE));
  }
  if (chunks.length > MAX_OBJECTS) {
    chunks.length = MAX_OBJECTS;
    const tail = chunks[MAX_OBJECTS - 1].slice(0, MAX_LINE - 20);
    chunks[MAX_OBJECTS - 1] = tail + "\n\n⋯（內容過長已截斷）";
  }
  return chunks.map((text) => ({ type: "text", text }));
}

async function lineCall(env, path, payload) {
  const r = await fetch(`${LINE_API}${path}`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${env.LINE_ACCESS_TOKEN}`,
      "content-type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return r;
}

// 免費、不計額度。
async function lineReply(env, replyToken, messages) {
  const r = await lineCall(env, "/message/reply", { replyToken, messages });
  return r.ok;
}

// ⚠️ 計入免費額度（輕用量 200 則／月）。只在 /notify 與 reply 逾時 fallback 用。
async function linePush(env, messages) {
  const r = await lineCall(env, "/message/push", { to: env.LINE_USER_ID, messages });
  if (!r.ok) throw new Error(`LINE push ${r.status}: ${(await r.text()).slice(0, 200)}`);
  return true;
}

// 每個事件配一個發送器：優先用免費的 reply，token 過期或已用掉才退回 push。
function makeResponder(env, replyToken) {
  const born = Date.now();
  let spent = false;
  return async function send(...parts) {
    const messages = toMessages(parts);
    if (!messages.length) return;
    const usable = replyToken && !spent && Date.now() - born < REPLY_WINDOW_MS;
    if (usable) {
      spent = true;
      if (await lineReply(env, replyToken, messages)) return;
      // reply 失敗（多半是 token 已逾時）就往下走 push，不要讓訊息消失
    }
    await linePush(env, messages);
  };
}

// 輸入中動畫。純視覺，失敗不影響功能。
// TODO 端點名稱實作時翻一次官方 reference 確認（chat/loading/start 與 message/loading 兩種寫法都查得到）。
async function lineLoading(env) {
  try {
    await lineCall(env, "/chat/loading/start", {
      chatId: env.LINE_USER_ID,
      loadingSeconds: 30,
    });
  } catch (e) {
    // 沒有動畫而已，吞掉
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// LINE 的媒體要跟 api-data.line.me 拿，而且大檔可能先回 202 表示還在準備。
async function fetchAudio(env, messageId) {
  const url = `${LINE_DATA_API}/message/${messageId}/content`;
  for (let attempt = 0; attempt < 5; attempt++) {
    const r = await fetch(url, {
      headers: { authorization: `Bearer ${env.LINE_ACCESS_TOKEN}` },
    });
    if (r.status === 202) {
      await sleep(1000 * (attempt + 1));
      continue;
    }
    if (!r.ok) throw new Error(`取語音失敗 ${r.status}`);
    return await r.blob();
  }
  throw new Error("語音檔準備逾時，再傳一次試試");
}

async function transcribe(env, messageId) {
  const audio = await fetchAudio(env, messageId);

  const form = new FormData();
  // LINE 的語音是 m4a，不是 Telegram 的 ogg。
  form.append("file", audio, "voice.m4a");
  form.append("model", "whisper-1");
  form.append("language", "zh");
  const vocab = (PROFILE.vocabulary || []).join("、");
  form.append("prompt", vocab ? `繁體中文。可能出現的詞：${vocab}。` : "繁體中文。");

  const r = await fetch("https://api.openai.com/v1/audio/transcriptions", {
    method: "POST",
    headers: { authorization: `Bearer ${env.OPENAI_API_KEY}` },
    body: form,
  });
  if (!r.ok) throw new Error(`Whisper ${r.status}: ${(await r.text()).slice(0, 200)}`);
  return (await r.json()).text;
}

// ---------- Notion ----------

async function notionQuery(env, dbId, filter, sorts, pageSize = 25) {
  const body = {};
  if (filter) body.filter = filter;
  if (sorts) body.sorts = sorts;
  body.page_size = pageSize;

  const r = await fetch(`${NOTION_URL}/databases/${dbId}/query`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${env.NOTION_TOKEN}`,
      "notion-version": NOTION_VERSION,
      "content-type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`Notion ${r.status}: ${(await r.text()).slice(0, 300)}`);
  return (await r.json()).results;
}

// Notion 一次最多回 100 筆。庫存動輒上百筆，只抓第一頁會靜默漏掉後面的——
// 查出來少一半不會報錯，比對品名時更會大量誤判成「找不到」。
async function notionQueryAll(env, dbId, filter, sorts, max = 500) {
  const out = [];
  let cursor;
  for (let page = 0; page < 10; page++) {
    const body = { page_size: 100 };
    if (filter) body.filter = filter;
    if (sorts) body.sorts = sorts;
    if (cursor) body.start_cursor = cursor;

    const r = await fetch(`${NOTION_URL}/databases/${dbId}/query`, {
      method: "POST",
      headers: {
        authorization: `Bearer ${env.NOTION_TOKEN}`,
        "notion-version": NOTION_VERSION,
        "content-type": "application/json",
      },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`Notion ${r.status}: ${(await r.text()).slice(0, 300)}`);
    const data = await r.json();
    out.push(...data.results);
    if (!data.has_more || out.length >= max) break;
    cursor = data.next_cursor;
  }
  return out;
}

async function notionSetNumber(env, pageId, field, value) {
  const r = await fetch(`${NOTION_URL}/pages/${pageId}`, {
    method: "PATCH",
    headers: {
      authorization: `Bearer ${env.NOTION_TOKEN}`,
      "notion-version": NOTION_VERSION,
      "content-type": "application/json",
    },
    body: JSON.stringify({ properties: { [field]: { number: value } } }),
  });
  if (!r.ok) throw new Error(`Notion PATCH ${r.status}: ${(await r.text()).slice(0, 200)}`);
}

function plain(prop) {
  if (!prop) return "";
  switch (prop.type) {
    case "title":
      return prop.title.map((t) => t.plain_text).join("");
    case "rich_text":
      return prop.rich_text.map((t) => t.plain_text).join("");
    case "number":
      return prop.number == null ? "" : prop.number.toLocaleString("en-US");
    case "select":
      return prop.select ? prop.select.name : "";
    case "date":
      return prop.date ? prop.date.start : "";
    case "phone_number":
      return prop.phone_number || "";
    case "email":
      return prop.email || "";
    default:
      return "";
  }
}

function twTime(iso) {
  const d = new Date(new Date(iso).getTime() + 8 * 3600 * 1000);
  const p = (n) => String(n).padStart(2, "0");
  return `${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())} ${p(d.getUTCHours())}:${p(d.getUTCMinutes())}`;
}

function row(props, fields) {
  return fields
    .map((f) => {
      const v = plain(props[f]);
      return v ? `${f} ${v}` : "";
    })
    .filter(Boolean)
    .join("／");
}

// ---------- GitHub（寫進私人 workspace repo） ----------

async function ghGet(env, path) {
  const r = await fetch(`https://api.github.com/repos/${WORKSPACE_REPO}/contents/${path}`, {
    headers: {
      authorization: `Bearer ${env.GITHUB_PAT}`,
      accept: "application/vnd.github+json",
      "user-agent": "liam-tg-bot",
    },
  });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`GitHub GET ${r.status}`);
  const j = await r.json();
  return { sha: j.sha, text: new TextDecoder().decode(b64decode(j.content.replace(/\n/g, ""))) };
}

async function ghPut(env, path, text, message, sha) {
  const body = { message, content: b64encode(new TextEncoder().encode(text)) };
  if (sha) body.sha = sha;
  const r = await fetch(`https://api.github.com/repos/${WORKSPACE_REPO}/contents/${path}`, {
    method: "PUT",
    headers: {
      authorization: `Bearer ${env.GITHUB_PAT}`,
      accept: "application/vnd.github+json",
      "content-type": "application/json",
      "user-agent": "liam-tg-bot",
    },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`GitHub PUT ${r.status}: ${(await r.text()).slice(0, 200)}`);
}

function b64encode(bytes) {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s);
}

function b64decode(s) {
  const bin = atob(s);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function today() {
  return new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 10);
}

// ---------- 工具實作 ----------

async function runTool(env, name, input) {
  if (name === "add_todo") {
    const file = (await ghGet(env, TODO_PATH)) || { sha: null, text: "# TODO\n" };
    const line = `- [ ] ${input.text}　（${today()} 手機記錄）\n`;
    await ghPut(env, TODO_PATH, file.text.trimEnd() + "\n" + line, `todo: ${input.text.slice(0, 40)}`, file.sha);
    return `已加進 ${TODO_PATH}`;
  }

  if (name === "save_note") {
    const slug = today();
    const path = `${KNOWLEDGE_DIR}/${input.category}/${slug}.md`;
    const existing = await ghGet(env, path);
    const block = `\n## ${input.title}\n\n${input.content}\n`;
    const text = existing ? existing.text.trimEnd() + "\n" + block : `# ${input.category} ${slug}\n${block}`;
    await ghPut(env, path, text, `note: ${input.title}`, existing ? existing.sha : null);
    return `已存進 ${path}`;
  }

  if (name === "run_workflow") {
    const file = WORKFLOWS[input.task];
    if (!file) return `不認得任務「${input.task}」，可跑的有：${Object.keys(WORKFLOWS).join("、")}`;

    const r = await fetch(
      `https://api.github.com/repos/${AGENT_REPO}/actions/workflows/${file}/dispatches`,
      {
        method: "POST",
        headers: {
          authorization: `Bearer ${env.GITHUB_PAT}`,
          accept: "application/vnd.github+json",
          "content-type": "application/json",
          "user-agent": "liam-tg-bot",
        },
        body: JSON.stringify({ ref: "main" }),
      }
    );
    if (r.status !== 204) throw new Error(`觸發失敗 ${r.status}: ${(await r.text()).slice(0, 200)}`);

    const warn = PUBLISHES.has(input.task) ? "⚠️ 這個會對外發布，收不回來。\n" : "";
    return `${warn}已觸發「${input.task}」，通常 1~5 分鐘跑完。\nhttps://github.com/${AGENT_REPO}/actions/workflows/${file}`;
  }

  if (name === "preview_inventory_update") {
    const { items, skipped } = parseInventoryText(input.text);
    if (!items.length) {
      return "看不懂這份表。一行一個品項，例如：\n白蝦 8\n干貝 15";
    }
    if (items.length > MAX_INV_UPDATE) {
      return `一次最多 ${MAX_INV_UPDATE} 筆，你給了 ${items.length} 筆。分批貼。`;
    }
    const diff = await buildInventoryDiff(env, items);
    if (diff.changes.length && env.CHAT) {
      await env.CHAT.put("pending_inv", JSON.stringify(diff.changes), {
        expirationTtl: PENDING_TTL,
      });
    }
    return renderInventoryDiff(diff, skipped);
  }

  if (name === "confirm_inventory_update") {
    if (!env.CHAT) return "沒有 KV，無法暫存待確認的變更。";
    const raw = await env.CHAT.get("pending_inv");
    if (!raw) return "沒有待確認的變更（或已超過 10 分鐘失效）。請重新貼一次庫存表。";

    const changes = JSON.parse(raw);
    // 先刪再寫：就算中途失敗也不會因為重複確認而改第二次。
    await env.CHAT.delete("pending_inv");

    const done = [];
    const failed = [];
    for (const c of changes) {
      try {
        await notionSetNumber(env, c.pageId, c.qtyField, c.to);
        done.push(`・${c.name}　${c.from == null ? "（空白）" : c.from} → ${c.to}`);
      } catch (e) {
        failed.push(`・${c.name}　失敗：${e.message.slice(0, 60)}`);
      }
    }
    const out = [`已更新 ${done.length} 筆`, ...done];
    if (failed.length) out.push("", `❌ ${failed.length} 筆沒改到`, ...failed);
    return out.join("\n");
  }

  if (name === "check_workflows") {
    const filter = String(input.filter || "").trim();
    const wanted =
      !filter || filter === "自動化" || filter === "全部"
        ? Object.entries(WORKFLOWS)
        : Object.entries(WORKFLOWS).filter(([task]) => task.includes(filter));

    if (!wanted.length) {
      return `不認得任務「${filter}」，可查的有：${Object.keys(WORKFLOWS).join("、")}`;
    }

    // 每個 workflow 各查最近 5 次。不能只抓「全 repo 最近 100 次」——
    // IG留言回覆每 5 分鐘跑一次，會把其他任務全部擠出視窗。
    const results = await Promise.all(
      wanted.map(async ([task, file]) => {
        try {
          const r = await fetch(
            `https://api.github.com/repos/${AGENT_REPO}/actions/workflows/${file}/runs?per_page=5`,
            {
              headers: {
                authorization: `Bearer ${env.GITHUB_PAT}`,
                accept: "application/vnd.github+json",
                "user-agent": "liam-line-bot",
              },
            }
          );
          if (!r.ok) return { task, error: `API ${r.status}` };
          const runs = (await r.json()).workflow_runs || [];
          return { task, runs };
        } catch (e) {
          return { task, error: e.message };
        }
      })
    );

    const bad = [];
    const flaky = [];
    const running = [];
    const never = [];
    const errored = [];
    let ok = 0;

    for (const { task, runs, error } of results) {
      if (error) {
        errored.push(`・${task}　查詢失敗（${error}）`);
        continue;
      }
      if (!runs.length) {
        never.push(`・${task}　從未執行`);
        continue;
      }
      const last = runs[0];
      if (last.status !== "completed") {
        running.push(`・${task}　執行中（${twTime(last.created_at)}）`);
        continue;
      }
      if (last.conclusion === "success") {
        // 最後一次成功不代表健康——月報就曾經 5 次裡失敗 3 次卻顯示正常。
        const fails = runs.filter((x) => x.conclusion === "failure").length;
        if (fails) {
          flaky.push(`・${task}　最近 ${runs.length} 次有 ${fails} 次失敗（最後一次成功 ${twTime(last.created_at)}）`);
        } else {
          ok++;
        }
        continue;
      }
      const streak = runs.filter((x) => x.conclusion === last.conclusion).length;
      const note = streak > 1 ? `，最近 ${runs.length} 次有 ${streak} 次` : "";
      bad.push(`・${task}　${last.conclusion === "failure" ? "失敗" : last.conclusion}　${twTime(last.created_at)}${note}`);
    }

    const out = [];
    if (bad.length) out.push("❌ 有問題", ...bad);
    if (flaky.length) out.push("⚠️ 不穩定", ...flaky);
    if (running.length) out.push("⏳ 執行中", ...running);
    if (never.length) out.push("⚪️ 沒跑過", ...never);
    if (errored.length) out.push("⚠️ 查不到", ...errored);
    if (!bad.length && !flaky.length && !running.length && !never.length && !errored.length) {
      out.push(`✅ ${ok} 個任務全部正常`);
    } else if (ok) {
      out.push("", `✅ 其餘 ${ok} 個正常`);
    }
    return out.join("\n");
  }

  if (name === "query_customer") {
    const cfg = PROFILE.crm.customer;
    const rows = await notionQuery(env, env[cfg.db], {
      property: cfg.titleField,
      title: { contains: input.name },
    });
    if (!rows.length) return `找不到「${input.name}」`;
    return rows
      .slice(0, 8)
      .map((p) => row(p.properties, cfg.fields))
      .join("\n");
  }

  if (name === "query_sales") {
    const cfg = PROFILE.crm.sales;
    const rows = await notionQuery(
      env,
      env[cfg.db],
      { property: cfg.matchField, rich_text: { contains: input.customer } },
      [{ property: cfg.sortField, direction: "descending" }]
    );
    if (!rows.length) return `「${input.customer}」沒有銷售紀錄`;
    return rows
      .slice(0, 12)
      .map((p) => row(p.properties, cfg.fields))
      .join("\n");
  }

  if (name === "query_inventory") {
    const dbs = Object.fromEntries(
      (PROFILE.inventory || []).map((x) => [x.brand, env[x.db]])
    );

    // 斜線指令只吃得下一個參數，所以「/i 鑫茶坊」會把品牌名當關鍵字送進來。
    // 開頭剛好是品牌名就當成指定品牌，剩下的才是關鍵字。
    let keyword = String(input.keyword || "").trim();
    let brand = input.brand;
    for (const b of Object.keys(dbs)) {
      if (keyword === b) {
        brand = b;
        keyword = "";
        break;
      }
      if (keyword.startsWith(b + " ")) {
        brand = b;
        keyword = keyword.slice(b.length).trim();
        break;
      }
    }

    const targets = brand && brand !== "全部" ? { [brand]: dbs[brand] } : dbs;

    // 實測整個品牌全列出來也不到 2,000 字，LINE 一則裝得下（上限 4,500）。
    // 指定品牌就全給；關鍵字搜出來的通常沒幾筆；只有「全部列出」才需要收斂。
    const singleBrand = Boolean(brand && brand !== "全部");
    const LIMIT = singleBrand ? 200 : keyword ? 50 : 20;
    const out = [];
    for (const [brand, db] of Object.entries(targets)) {
      if (!db) continue;
      const map = INV_FIELDS[brand];
      if (!map) continue;
      const rows = await notionQueryAll(env, db, null);
      const hit = rows.filter((p) => {
        if (!keyword) return true;
        return JSON.stringify(p.properties).includes(keyword);
      });
      if (!hit.length) continue;

      const shown = hit.slice(0, LIMIT).map((p) => invRow(p.properties, map)).filter(Boolean);
      out.push(hit.length > LIMIT ? `【${brand}】共 ${hit.length} 筆，顯示前 ${LIMIT}` : `【${brand}】${hit.length} 筆`);
      out.push(...shown);
      out.push("");
    }
    return out.length ? out.join("\n").trim() : `庫存查不到「${keyword || brand || ""}」`;
  }

  return `未知工具 ${name}`;
}

// ---------- 直達指令（不走 AI，零 API 成本） ----------
//
// 查資料庫和寫檔案本來就不需要 AI，需要 AI 的只是「把人話翻譯成查詢」。
// 願意打指令就跳過那一步。記不住指令時照樣可以講人話，只是那次會走 Claude。

const COMMANDS = [
  HAS_NOTES && { keys: ["/todo", "/待辦", "/t"], tool: "add_todo", arg: "text", need: true },
  HAS_CRM && { keys: ["/客戶", "/c"], tool: "query_customer", arg: "name", need: true },
  HAS_CRM && { keys: ["/買", "/銷售", "/s"], tool: "query_sales", arg: "customer", need: true },
  HAS_INVENTORY && { keys: ["/庫存", "/i"], tool: "query_inventory", arg: "keyword", need: false },
  HAS_NOTES && { keys: ["/note", "/筆記", "/n"], tool: "save_note", arg: null, need: true },
  HAS_ACTIONS && { keys: ["/跑", "/run", "/r"], tool: "run_workflow", arg: "task", need: true },
  HAS_ACTIONS && { keys: ["/查", "/check", "/k"], tool: "check_workflows", arg: "filter", need: false },
  CAN_WRITE_INVENTORY && {
    keys: ["/改庫存", "/u"],
    tool: "preview_inventory_update",
    arg: "text",
    need: true,
    multiline: true,
  },
  CAN_WRITE_INVENTORY && {
    keys: ["/確認"],
    tool: "confirm_inventory_update",
    arg: null,
    need: false,
    confirm: true,
  },
].filter(Boolean);

function parseCommand(text) {
  const trimmed = text.trim();
  for (const cmd of COMMANDS) {
    for (const key of cmd.keys) {
      // 換行也算分隔，否則多行的 /改庫存 貼進來會被當成不認得的指令。
      const sep = trimmed.length > key.length ? trimmed[key.length] : "";
      if (trimmed === key || (trimmed.startsWith(key) && /\s/.test(sep))) {
        // 只削頭尾空白，行內換行要留著。
        const rest = trimmed.slice(key.length).trim();
        if (cmd.need && !rest) return { error: `${key} 後面要接內容` };

        // ⚠️ 斜線指令直接執行、不經過 AI，所以沒有任何確認步驟。
        // 會對外發布的任務一律擋在這裡：IG 限動發出去 API 刪不掉，
        // 手機誤觸或選單點錯的代價收不回來。要發就走自然語言（Claude 會先問）或用電腦。
        if (cmd.tool === "run_workflow" && PUBLISHES.has(rest)) {
          return {
            error:
              `「${rest}」會對外發布，不接受斜線指令。\n` +
              `要發請用講的（我會先跟你確認），或到電腦上跑。`,
          };
        }

        if (cmd.tool === "save_note") {
          // 原樣存進 misc，不做整理——要整理過的筆記就講人話或傳語音（走 AI）
          return {
            tool: "save_note",
            input: { category: "misc", title: rest.slice(0, 15), content: rest },
          };
        }
        // arg 為 null 的指令（例如 /確認）不吃參數。
        return { tool: cmd.tool, input: cmd.arg ? { [cmd.arg]: rest } : {} };
      }
    }
  }
  return null;
}

// ---------- Claude agent loop ----------

// effort 只有新世代模型吃；Haiku 4.5 / Sonnet 4.5 收到會回 400。
const EFFORT_OK = /^claude-(opus-(5|4-[678])|sonnet-(5|4-6)|fable-5|mythos-5)/;

async function claude(env, messages) {
  const body = {
    model: env.MODEL,
    max_tokens: 2000,
    system: SYSTEM,
    tools: TOOLS,
    messages,
  };
  if (EFFORT_OK.test(env.MODEL)) body.output_config = { effort: "low" };

  const r = await fetch(ANTHROPIC_URL, {
    method: "POST",
    headers: {
      "x-api-key": env.ANTHROPIC_API_KEY,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`Claude ${r.status}: ${(await r.text()).slice(0, 300)}`);
  return await r.json();
}

async function think(env, messages) {
  for (let turn = 0; turn < 6; turn++) {
    const res = await claude(env, messages);
    messages.push({ role: "assistant", content: res.content });

    if (res.stop_reason !== "tool_use") {
      return res.content
        .filter((b) => b.type === "text")
        .map((b) => b.text)
        .join("\n")
        .trim();
    }

    const results = [];
    for (const block of res.content) {
      if (block.type !== "tool_use") continue;
      try {
        const out = await runTool(env, block.name, block.input);
        results.push({ type: "tool_result", tool_use_id: block.id, content: out });
      } catch (e) {
        results.push({
          type: "tool_result",
          tool_use_id: block.id,
          content: `執行失敗：${e.message}`,
          is_error: true,
        });
      }
    }
    messages.push({ role: "user", content: results });
  }
  return "來回太多次了，這題我處理不動，到電腦上再說。";
}

// ---------- 對話記憶（KV，1 小時） ----------

async function loadHistory(env) {
  if (!env.CHAT) return [];
  const raw = await env.CHAT.get("history");
  return raw ? JSON.parse(raw) : [];
}

async function saveHistory(env, messages) {
  if (!env.CHAT) return;
  const trimmed = messages.filter((m) => typeof m.content === "string").slice(-HISTORY_TURNS);
  await env.CHAT.put("history", JSON.stringify(trimmed), { expirationTtl: 3600 });
}

// ---------- 進入點 ----------

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === "/notify" && request.method === "POST") {
      if (!env.NOTIFY_TOKEN) return new Response("unconfigured", { status: 503 });
      const auth = request.headers.get("authorization") || "";
      if (!timingSafeEqual(auth, `Bearer ${env.NOTIFY_TOKEN}`)) {
        return new Response("unauthorized", { status: 401 });
      }
      const { text } = await request.json();
      // ⚠️ push 計入免費額度（輕用量 200 則／月），推播要克制。
      await linePush(env, toMessages([text]));
      return new Response("ok");
    }

    if (url.pathname === "/line" && request.method === "POST") {
      // 簽章一定要用原始字串驗，所以先 text() 再自己 parse。
      const raw = await request.text();
      const ok = await verifySignature(env, raw, request.headers.get("x-line-signature"));
      if (!ok) return new Response("forbidden", { status: 403 });

      let body;
      try {
        body = JSON.parse(raw);
      } catch (e) {
        return new Response("bad request", { status: 400 });
      }

      for (const event of body.events || []) {
        if (event.type !== "message") continue;
        if (event.replyToken === VERIFY_TOKEN) continue; // Console 的 Verify 測試
        if (!isOwner(env, event)) {
          // 設定階段的輔助：白名單還沒填之前，把來訪者的 user ID 印出來方便你抄
          // （wrangler tail 看得到）。一旦填好，就不再記錄任何人的 ID。
          if (!env.LINE_USER_ID || String(env.LINE_USER_ID).startsWith("PUT_")) {
            console.log("白名單未設定，收到 userId:", event?.source?.userId || "(無)");
          }
          continue; // 別人傳訊息一律靜默忽略
        }
        ctx.waitUntil(handle(env, event));
      }

      // LINE 要求盡快回 200，實際工作在 waitUntil 裡跑。
      return new Response("ok");
    }

    return new Response("Liam LINE bot", { status: 200 });
  },
};

async function handle(env, event) {
  const send = makeResponder(env, event.replyToken);
  try {
    const msg = event.message || {};

    // 逐字稿與答案要合併成同一次 reply（token 只能用一次）。
    // 動畫先開著，讓他知道有在跑，這比先回一則「聽到」省一則額度。
    let heard = null;
    let text = "";

    if (msg.type === "audio") {
      await lineLoading(env);
      heard = await transcribe(env, msg.id);
      text = heard;
    } else if (msg.type === "text") {
      text = msg.text || "";
    } else {
      return; // 圖片、貼圖、位置等暫不處理
    }

    if (!text.trim()) return;

    if (text.trim() === "/start" || text.trim() === "/help") {
      await send(HELP);
      return;
    }

    // 斜線指令直接查，不花 AI 的錢
    const cmd = parseCommand(text);
    if (cmd) {
      await send(heard && `🎙 聽到：${heard}`, cmd.error || (await runTool(env, cmd.tool, cmd.input)));
      return;
    }

    if (!heard) await lineLoading(env);

    const history = await loadHistory(env);
    const messages = [...history, { role: "user", content: text }];
    const reply = await think(env, messages);

    await send(heard && `🎙 聽到：${heard}`, reply || "（沒有回覆內容）");
    await saveHistory(env, [...messages, { role: "assistant", content: reply }]);
  } catch (e) {
    try {
      await send(`⚠️ 出錯了：${e.message}`);
    } catch (_) {
      // 連錯誤訊息都送不出去就算了，不要讓 waitUntil 掛掉
    }
  }
}
