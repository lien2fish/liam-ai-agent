// 炘和官網訂購表單 → 寫進 Notion「炘和客戶／炘和訂單」＋推 LINE 給 Lien。
// 價格一律以站上 products.json 為準，不採用瀏覽器送來的數字。
// 環境變數（Pages 專案 secret）：
//   LINE_NOTIFY_URL、LINE_NOTIFY_TOKEN
//   NOTION_TOKEN —— ⛔ 只連「炘和管理顧問」頁面的專用 integration，不可用鉅鑫那把（它看得到整個鉅鑫 CRM）
//   NOTION_API —— 選填，本機測試時指向假伺服器

const CUSTOMERS_DB = "9cb11bd8a1944a5099b82564f887ab21";
const ORDERS_DB = "7a048786067b4d30bf6822f1d0d98501";
const LIMITS = { name: 40, phone: 20, email: 80, company: 80, address: 120, date: 10, note: 500 };

function today() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Taipei" }).format(new Date());
}

function reply(status, body) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}

function orderNo() {
  const now = new Intl.DateTimeFormat("sv-SE", {
    timeZone: "Asia/Taipei",
    year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
  }).format(new Date()).replace(/\D/g, "");
  const rand = crypto.getRandomValues(new Uint16Array(1))[0].toString(36).toUpperCase().padStart(3, "0");
  return `XH-${now.slice(0, 8)}-${now.slice(8)}-${rand}`;
}

const text = (s) => ({ rich_text: s ? [{ text: { content: s } }] : [] });
const day = (s) => ({ date: s ? { start: s } : null });

async function notion(env, path, method, body) {
  const r = await fetch((env.NOTION_API || "https://api.notion.com") + "/v1/" + path, {
    method,
    headers: {
      Authorization: "Bearer " + env.NOTION_TOKEN,
      "Notion-Version": "2022-06-28",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`Notion ${path} ${r.status}`);
  return r.json();
}

// 同一支手機視為同一位客人：有就更新、沒有就新建。回傳訂單編號。
async function saveToNotion(env, f, phone, marketing, item) {
  const t = today();
  const found = await notion(env, `databases/${CUSTOMERS_DB}/query`, "POST", {
    filter: { property: "手機", phone_number: { equals: phone } },
    page_size: 1,
  });
  const contact = {
    地址: text(f.address),
    ...(f.email && { Email: { email: f.email } }),
    ...(f.company && { "公司抬頭/統編": text(f.company) }),
    // 只會從沒勾變成有勾；客人要取消行銷，由人工改，不讓表單自動清掉
    ...(marketing && { 同意行銷: { checkbox: true } }),
  };
  let customerId;
  if (found.results.length) {
    customerId = found.results[0].id;
    await notion(env, `pages/${customerId}`, "PATCH", {
      properties: { ...contact, 最後下單日: day(t) },
    });
  } else {
    const created = await notion(env, "pages", "POST", {
      parent: { database_id: CUSTOMERS_DB },
      properties: {
        姓名: { title: [{ text: { content: f.name } }] },
        手機: { phone_number: phone },
        來源: { select: { name: "官網訂購" } },
        首次下單日: day(t),
        最後下單日: day(t),
        ...contact,
      },
    });
    customerId = created.id;
  }
  const no = orderNo();
  await notion(env, "pages", "POST", {
    parent: { database_id: ORDERS_DB },
    properties: {
      訂單編號: { title: [{ text: { content: no } }] },
      客戶: { relation: [{ id: customerId }] },
      商品: text(item.name),
      檔期: text(item.festival),
      單價: { number: item.price },
      數量: { number: item.qty },
      金額: { number: item.price * item.qty },
      下單日: day(t),
      希望到貨日: day(f.date),
      收件地址: text(f.address),
      狀態: { select: { name: "新訂單" } },
      備註: text(f.note),
    },
  });
  return no;
}

async function pushLine(env, message) {
  if (!env.LINE_NOTIFY_URL || !env.LINE_NOTIFY_TOKEN) return false;
  try {
    const r = await fetch(env.LINE_NOTIFY_URL.replace(/\/$/, "") + "/notify", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + env.LINE_NOTIFY_TOKEN,
        "User-Agent": "xuhe-order/1",
      },
      body: JSON.stringify({ text: message }),
    });
    return r.ok;
  } catch (e) {
    return false;
  }
}

export async function onRequestPost({ request, env }) {
  if (Number(request.headers.get("content-length") || 0) > 8000) {
    return reply(413, { error: "資料太長" });
  }
  let data;
  try {
    data = await request.json();
  } catch (e) {
    return reply(400, { error: "格式錯誤" });
  }
  // 機器人會填隱藏欄位：假裝成功，不寫入也不推播（推播計入每月 200 則額度）
  if (data.website) return reply(200, { ok: true });
  if (data.consent !== true) return reply(400, { error: "請勾選同意個人資料告知事項" });

  const f = {};
  for (const [key, max] of Object.entries(LIMITS)) {
    f[key] = String(data[key] || "").trim().slice(0, max);
  }
  if (!f.name || !f.address) return reply(400, { error: "請填寫姓名與地址" });
  if (!/^[0-9+\-\s()]{8,20}$/.test(f.phone)) return reply(400, { error: "手機號碼格式不正確" });
  const phone = f.phone.replace(/[^\d+]/g, "");
  if (f.date && !/^\d{4}-\d{2}-\d{2}$/.test(f.date)) f.date = "";
  const qty = parseInt(data.qty, 10);
  if (!(qty >= 1 && qty <= 999)) return reply(400, { error: "數量不正確" });

  const shop = await (await env.ASSETS.fetch(new URL("/products.json", request.url))).json();
  const p = shop.find((x) => x.slug === data.slug);
  if (!p) return reply(400, { error: "找不到這項商品" });
  const t = today();
  const c = p.campaigns.find((x) => x.start <= t && t <= x.end);
  const price = (c && c.price) || p.price;
  if (!price) return reply(400, { error: "這項商品目前不開放線上訂購" });
  const marketing = data.marketing === true;

  let no = null;
  let notionStatus = "⚠️ Notion 未設定，請手動建檔";
  if (env.NOTION_TOKEN) {
    try {
      no = await saveToNotion(env, f, phone, marketing, {
        name: p.name, festival: c ? c.festival : "", price, qty,
      });
      notionStatus = `✅ 已建檔 ${no}`;
    } catch (e) {
      notionStatus = `⚠️ Notion 寫入失敗（${e.message}），請手動建檔`;
    }
  }

  const lines = [
    "🛒 炘和官網新訂單",
    `${p.name}${c ? `（${c.festival}檔期）` : ""}`,
    `NT$ ${price.toLocaleString("en-US")} × ${qty} ＝ NT$ ${(price * qty).toLocaleString("en-US")}`,
    "",
    `姓名：${f.name}`,
    `手機：${f.phone}`,
    f.email ? `Email：${f.email}` : null,
    f.company ? `抬頭／統編：${f.company}` : null,
    `地址：${f.address}`,
    f.date ? `希望到貨：${f.date}` : null,
    f.note ? `備註：${f.note}` : null,
    `同意行銷：${marketing ? "是" : "否"}`,
    "",
    notionStatus,
    "→ 確認後回覆客人並提供匯款資訊",
  ].filter((x) => x !== null);
  const pushed = await pushLine(env, lines.join("\n"));

  // 兩邊都沒記到才算失敗——只要有一邊記到，Lien 就找得到這張訂單
  if (!no && !pushed) return reply(502, { error: "訂單沒有送達" });
  return reply(200, { ok: true, order: no });
}
