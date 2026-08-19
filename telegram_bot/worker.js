/**
 * Liam 手機助理 — Telegram Bot on Cloudflare Worker
 *
 * 兩個入口：
 *   POST /tg      Telegram webhook（你傳訊息／語音進來）
 *   POST /notify  自動化推播（GitHub Actions 呼叫，帶 Bearer NOTIFY_TOKEN）
 *
 * 能做：記待辦、存筆記到知識庫、查客戶、查庫存、查銷售紀錄、語音轉文字。
 * 不能做：跑腳本、剪片、改本機檔案——那些走 claude.ai/code。
 */

const ANTHROPIC_URL = "https://api.anthropic.com/v1/messages";
const NOTION_URL = "https://api.notion.com/v1";
const NOTION_VERSION = "2022-06-28";
const WORKSPACE_REPO = "lien2fish/liam-workspace";
const AGENT_REPO = "lien2fish/liam-ai-agent";

// 中文任務名 → workflow 檔名。17 個全部支援 workflow_dispatch。
const WORKFLOWS = {
  市場日報: "market_daily.yml",
  漁獲行情: "seafood_prices.yml",
  保單到期: "policy_expiry_check.yml",
  回購提醒: "repurchase_reminder.yml",
  生日提醒: "birthday_reminder.yml",
  壽險拜訪: "life_visit_reminder.yml",
  扶輪生日: "rotary_birthday_reminder.yml",
  營收週報: "weekly_revenue_sprint.yml",
  YouTube留言: "yt_comment_monitor.yml",
  頻道日報: "yt_channel_report.yml",
  Gmail清理: "gmail_automation.yml",
  月報: "notion_monthly_report.yml",
  IG發文: "daily_post.yml",
  限動預告: "ig_story_teaser.yml",
  IG留言回覆: "ig_comment_reply.yml",
  YouTube影片: "yt_auto_post.yml",
};

// 這些會對外發布，發出去收不回來（IG 限動 API 刪不掉）
const PUBLISHES = new Set(["IG發文", "限動預告", "IG留言回覆", "YouTube影片"]);
const MAX_TG = 4000;
const HISTORY_TURNS = 8;

const SYSTEM = `你是 Lien（連傳正／鉅鑫管理顧問）的手機助理，透過 Telegram 對話。

Lien 的事業：鑫酒藏（葡萄酒）、鑫茶坊（茶葉）、鑫海產（龜吼現流海鮮）、匠鑫私廚，
另有磊山保經壽險/產險業務。品牌核心價值「鉅鑫只提供最高品質」。

回覆規則：
- 一律繁體中文，**簡短**。這是手機聊天視窗，不是報告——通常 3 行以內講完。
- 不要用 Markdown 表格（Telegram 不會渲染）。多筆資料用「・」條列。
- 金額寫成 12,500 這種帶千分位的形式。
- 查不到資料就直說查不到，不要猜。

他常在漁港、餐廳、客戶端用手機打字，句子會很短、可能有錯字，用常識判斷他的意思。
他丟一句想法過來通常是要你記下來（add_todo 或 save_note），不是要你分析。
語音訊息轉出來的逐字稿可能有辨識錯誤，海鮮或酒的專有名詞要用常識修正。

存到知識庫（save_note）的時機：他在講產地知識、辨別方法、處理手法、經營心得
——這些是他腦裡才有的東西，要留下來。純粹的待辦事項用 add_todo。`;

const HELP = `🆓 打指令＝直接查資料庫，不花錢

/客戶 王先生      查客戶（也可打 /c）
/買 王先生        查他買過什麼（/s）
/庫存 白蝦        查三品牌庫存（/i，留空列全部）
/待辦 下週三報價   記進 TODO.md（/t）
/筆記 內容        原樣存進知識庫，不整理（/n）

💰 講人話或傳語音＝走 AI，每次約 0.2 元

「王先生上次買什麼」這種自由問法、需要判斷的事，
還有語音訊息（會轉文字＋整理分類存進知識庫），都走這條。

🎙 在漁港挑魚時按住麥克風講十分鐘，
是這個 bot 最有價值的用法——那些知識只在你腦裡。

剪片、送印、建訂單、改程式：到 claude.ai/code。`;

const TOOLS = [
  {
    name: "add_todo",
    description: "把一件待辦事項加進 liam-workspace 的 TODO.md。用於「記得要…」「提醒我…」這類明確的行動項目。",
    input_schema: {
      type: "object",
      properties: {
        text: { type: "string", description: "待辦內容，一句話寫清楚要做什麼" },
      },
      required: ["text"],
    },
  },
  {
    name: "save_note",
    description:
      "把一段知識或想法存進 liam-workspace 的知識庫。用於 Lien 口述的產地知識、海鮮辨別方法、經營心得、客戶互動觀察——這些只存在他腦裡、值得長期留存的內容。",
    input_schema: {
      type: "object",
      properties: {
        category: {
          type: "string",
          enum: ["seafood", "wine", "tea", "business", "misc"],
          description: "分類：seafood 海鮮知識／wine 葡萄酒／tea 茶葉／business 經營與客戶／misc 其他",
        },
        title: { type: "string", description: "短標題，5-15 字" },
        content: { type: "string", description: "整理過的內容。保留他講的所有具體細節與數字，不要精簡掉。" },
      },
      required: ["category", "title", "content"],
    },
  },
  {
    name: "query_customer",
    description: "在全品牌客戶總表查客戶。可查到品牌、電話、會員等級、累計消費、最後購買日、偏好品項。",
    input_schema: {
      type: "object",
      properties: { name: { type: "string", description: "客戶姓名或公司名，可只給部分字" } },
      required: ["name"],
    },
  },
  {
    name: "query_sales",
    description: "查某位客戶買過什麼。回傳該客戶的銷售紀錄（日期、品項、數量、金額），最近的排前面。",
    input_schema: {
      type: "object",
      properties: { customer: { type: "string", description: "客戶名稱" } },
      required: ["customer"],
    },
  },
  {
    name: "run_workflow",
    description:
      "觸發 GitHub Actions 自動化任務，讓它現在就跑一次（平常是排程自動跑）。用於「重跑一次市場日報」「現在幫我發 IG」這類要求。標示⚠️的會對外發布內容，執行前務必先問清楚 Lien 是不是真的要發。",
    input_schema: {
      type: "object",
      properties: {
        task: {
          type: "string",
          enum: [
            "市場日報",
            "漁獲行情",
            "保單到期",
            "回購提醒",
            "生日提醒",
            "壽險拜訪",
            "扶輪生日",
            "營收週報",
            "YouTube留言",
            "頻道日報",
            "Gmail清理",
            "月報",
            "IG發文",
            "限動預告",
            "IG留言回覆",
            "YouTube影片",
          ],
          description:
            "要跑哪個任務。⚠️會對外發布的：IG發文（發限時動態）、限動預告（發限時動態）、IG留言回覆（公開回覆留言）、YouTube影片（產片並排程發布）",
        },
      },
      required: ["task"],
    },
  },
  {
    name: "query_inventory",
    description: "查三品牌庫存（鑫酒藏／鑫茶坊／鑫海產）。回傳品項、數量、單價。",
    input_schema: {
      type: "object",
      properties: {
        keyword: { type: "string", description: "品項關鍵字。留空則列出全部。" },
        brand: {
          type: "string",
          enum: ["鑫酒藏", "鑫茶坊", "鑫海產", "全部"],
          description: "要查哪個品牌的庫存，預設全部",
        },
      },
      required: ["keyword"],
    },
  },
];

// ---------- Telegram ----------

async function tgSend(env, text) {
  const chunks = [];
  for (let i = 0; i < text.length; i += MAX_TG) chunks.push(text.slice(i, i + MAX_TG));
  for (const chunk of chunks) {
    await fetch(`https://api.telegram.org/bot${env.TG_BOT_TOKEN}/sendMessage`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ chat_id: env.TG_CHAT_ID, text: chunk, disable_web_page_preview: true }),
    });
  }
}

async function tgTyping(env) {
  await fetch(`https://api.telegram.org/bot${env.TG_BOT_TOKEN}/sendChatAction`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ chat_id: env.TG_CHAT_ID, action: "typing" }),
  });
}

async function transcribe(env, fileId) {
  const info = await fetch(
    `https://api.telegram.org/bot${env.TG_BOT_TOKEN}/getFile?file_id=${fileId}`
  ).then((r) => r.json());
  if (!info.ok) throw new Error("getFile 失敗");

  const audio = await fetch(
    `https://api.telegram.org/file/bot${env.TG_BOT_TOKEN}/${info.result.file_path}`
  ).then((r) => r.blob());

  const form = new FormData();
  form.append("file", audio, "voice.ogg");
  form.append("model", "whisper-1");
  form.append("language", "zh");
  form.append("prompt", "繁體中文。可能出現的詞：龜吼、現流、鑫海產、鑫酒藏、鑫茶坊、匠鑫私廚、鉅鑫。");

  const r = await fetch("https://api.openai.com/v1/audio/transcriptions", {
    method: "POST",
    headers: { authorization: `Bearer ${env.OPENAI_API_KEY}` },
    body: form,
  });
  if (!r.ok) throw new Error(`Whisper ${r.status}: ${(await r.text()).slice(0, 200)}`);
  return (await r.json()).text;
}

// ---------- Notion ----------

async function notionQuery(env, dbId, filter, sorts) {
  const body = {};
  if (filter) body.filter = filter;
  if (sorts) body.sorts = sorts;
  body.page_size = 25;

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
    const file = (await ghGet(env, "TODO.md")) || { sha: null, text: "# TODO\n" };
    const line = `- [ ] ${input.text}　（${today()} 手機記錄）\n`;
    await ghPut(env, "TODO.md", file.text.trimEnd() + "\n" + line, `todo: ${input.text.slice(0, 40)}`, file.sha);
    return "已加進 TODO.md";
  }

  if (name === "save_note") {
    const slug = today();
    const path = `knowledge/${input.category}/${slug}.md`;
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

  if (name === "query_customer") {
    const rows = await notionQuery(env, env.CUSTOMER_DB, {
      property: "客戶姓名",
      title: { contains: input.name },
    });
    if (!rows.length) return `找不到「${input.name}」`;
    return rows
      .slice(0, 8)
      .map((p) =>
        row(p.properties, ["客戶姓名", "品牌", "聯絡電話", "會員等級", "累計消費", "最後購買日", "偏好品項"])
      )
      .join("\n");
  }

  if (name === "query_sales") {
    const rows = await notionQuery(
      env,
      env.SALES_DB,
      { property: "客戶名稱", rich_text: { contains: input.customer } },
      [{ property: "出貨日期", direction: "descending" }]
    );
    if (!rows.length) return `「${input.customer}」沒有銷售紀錄`;
    return rows
      .slice(0, 12)
      .map((p) => row(p.properties, ["出貨日期", "品牌", "品項", "數量", "金額"]))
      .join("\n");
  }

  if (name === "query_inventory") {
    const dbs = {
      鑫酒藏: env.INV_WINE_DB,
      鑫茶坊: env.INV_TEA_DB,
      鑫海產: env.INV_SEAFOOD_DB,
    };
    const targets =
      input.brand && input.brand !== "全部" ? { [input.brand]: dbs[input.brand] } : dbs;

    const out = [];
    for (const [brand, db] of Object.entries(targets)) {
      if (!db) continue;
      const rows = await notionQuery(env, db, null);
      const hit = rows.filter((p) => {
        if (!input.keyword) return true;
        return JSON.stringify(p.properties).includes(input.keyword);
      });
      if (hit.length) {
        out.push(`【${brand}】`);
        out.push(...hit.slice(0, 15).map((p) => row(p.properties, ["品項", "數量", "單位", "單價", "金額"])));
      }
    }
    return out.length ? out.join("\n") : `庫存查不到「${input.keyword}」`;
  }

  return `未知工具 ${name}`;
}

// ---------- 直達指令（不走 AI，零 API 成本） ----------
//
// 查資料庫和寫檔案本來就不需要 AI，需要 AI 的只是「把人話翻譯成查詢」。
// 願意打指令就跳過那一步。記不住指令時照樣可以講人話，只是那次會走 Claude。

const COMMANDS = [
  { keys: ["/todo", "/待辦", "/t"], tool: "add_todo", arg: "text", need: true },
  { keys: ["/客戶", "/c"], tool: "query_customer", arg: "name", need: true },
  { keys: ["/買", "/銷售", "/s"], tool: "query_sales", arg: "customer", need: true },
  { keys: ["/庫存", "/i"], tool: "query_inventory", arg: "keyword", need: false },
  { keys: ["/note", "/筆記", "/n"], tool: "save_note", arg: null, need: true },
  { keys: ["/跑", "/run", "/r"], tool: "run_workflow", arg: "task", need: true },
];

function parseCommand(text) {
  const trimmed = text.trim();
  for (const cmd of COMMANDS) {
    for (const key of cmd.keys) {
      if (trimmed === key || trimmed.startsWith(key + " ")) {
        const rest = trimmed.slice(key.length).trim();
        if (cmd.need && !rest) return { error: `${key} 後面要接內容` };

        if (cmd.tool === "save_note") {
          // 原樣存進 misc，不做整理——要整理過的筆記就講人話或傳語音（走 AI）
          return {
            tool: "save_note",
            input: { category: "misc", title: rest.slice(0, 15), content: rest },
          };
        }
        return { tool: cmd.tool, input: { [cmd.arg]: rest } };
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
      if (request.headers.get("authorization") !== `Bearer ${env.NOTIFY_TOKEN}`) {
        return new Response("unauthorized", { status: 401 });
      }
      const { text } = await request.json();
      await tgSend(env, String(text || "").slice(0, MAX_TG));
      return new Response("ok");
    }

    if (url.pathname === "/tg" && request.method === "POST") {
      if (request.headers.get("x-telegram-bot-api-secret-token") !== env.TG_WEBHOOK_SECRET) {
        return new Response("forbidden", { status: 403 });
      }

      const update = await request.json();
      const msg = update.message || update.edited_message;
      if (!msg) return new Response("ok");

      // 只有 Lien 本人能用
      if (String(msg.chat.id) !== String(env.TG_CHAT_ID)) return new Response("ok");

      ctx.waitUntil(handle(env, msg));
      return new Response("ok");
    }

    return new Response("Liam TG bot", { status: 200 });
  },
};

async function handle(env, msg) {
  try {
    await tgTyping(env);

    let text = msg.text || msg.caption || "";
    if (msg.voice || msg.audio) {
      const heard = await transcribe(env, (msg.voice || msg.audio).file_id);
      await tgSend(env, `🎙 聽到：${heard}`);
      text = heard;
    }
    if (!text.trim()) return;

    if (text.trim() === "/start" || text.trim() === "/help") {
      await tgSend(env, HELP);
      return;
    }

    // 斜線指令直接查，不花 AI 的錢
    const cmd = parseCommand(text);
    if (cmd) {
      if (cmd.error) {
        await tgSend(env, cmd.error);
        return;
      }
      const out = await runTool(env, cmd.tool, cmd.input);
      await tgSend(env, out);
      return;
    }

    const history = await loadHistory(env);
    const messages = [...history, { role: "user", content: text }];
    const reply = await think(env, messages);

    await tgSend(env, reply || "（沒有回覆內容）");
    await saveHistory(env, [...messages, { role: "assistant", content: reply }]);
  } catch (e) {
    await tgSend(env, `⚠️ 出錯了：${e.message}`);
  }
}
