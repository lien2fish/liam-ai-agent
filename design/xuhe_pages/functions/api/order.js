// 旭和官網訂購表單 → 推 LINE 給 Lien。不落地儲存任何客戶資料。
// 價格一律以站上 products.json 為準，不採用瀏覽器送來的數字。
// 環境變數（Pages 專案 secret）：LINE_NOTIFY_URL、LINE_NOTIFY_TOKEN

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
  // 機器人會填隱藏欄位：假裝成功，不推播（推播計入每月 200 則額度）
  if (data.website) return reply(200, { ok: true });
  if (data.consent !== true) return reply(400, { error: "請勾選同意個人資料告知事項" });

  const f = {};
  for (const [key, max] of Object.entries(LIMITS)) {
    f[key] = String(data[key] || "").trim().slice(0, max);
  }
  if (!f.name || !f.address) return reply(400, { error: "請填寫姓名與地址" });
  if (!/^[0-9+\-\s()]{8,20}$/.test(f.phone)) return reply(400, { error: "手機號碼格式不正確" });
  const qty = parseInt(data.qty, 10);
  if (!(qty >= 1 && qty <= 999)) return reply(400, { error: "數量不正確" });

  const shop = await (await env.ASSETS.fetch(new URL("/products.json", request.url))).json();
  const p = shop.find((x) => x.slug === data.slug);
  if (!p) return reply(400, { error: "找不到這項商品" });
  const t = today();
  const c = p.campaigns.find((x) => x.start <= t && t <= x.end);
  const price = (c && c.price) || p.price;
  if (!price) return reply(400, { error: "這項商品目前不開放線上訂購" });

  const lines = [
    "🛒 旭和官網新訂單",
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
    "",
    "→ 確認後回覆客人並提供匯款資訊",
  ].filter((x) => x !== null);

  if (!env.LINE_NOTIFY_URL || !env.LINE_NOTIFY_TOKEN) {
    return reply(503, { error: "線上訂購暫時無法使用" });
  }
  let r;
  try {
    r = await fetch(env.LINE_NOTIFY_URL.replace(/\/$/, "") + "/notify", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + env.LINE_NOTIFY_TOKEN,
        "User-Agent": "xuhe-order/1",
      },
      body: JSON.stringify({ text: lines.join("\n") }),
    });
  } catch (e) {
    return reply(502, { error: "訂單沒有送達" });
  }
  if (!r.ok) return reply(502, { error: "訂單沒有送達" });
  return reply(200, { ok: true });
}
