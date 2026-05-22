/**
 * IG 留言自動回覆 Webhook Worker
 * 龜吼現流活海產 / From Source To TABLE
 *
 * 環境變數（Cloudflare Secrets）：
 *   VERIFY_TOKEN  - Webhook 驗證碼
 *   IG_TOKEN      - Instagram Graph API Token（含 instagram_manage_comments）
 *   IG_ID         - Instagram 用戶 ID
 *   GEMINI_KEY    - Google Gemini API Key
 */

const GRAPH_API = 'https://graph.facebook.com/v19.0';
const GEMINI_API = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname !== '/webhook') {
      return new Response('Not Found', { status: 404 });
    }

    // ── GET：Meta Webhook 驗證 ──────────────────────────────────
    if (request.method === 'GET') {
      const mode      = url.searchParams.get('hub.mode');
      const token     = url.searchParams.get('hub.verify_token');
      const challenge = url.searchParams.get('hub.challenge');

      if (mode === 'subscribe' && token === env.VERIFY_TOKEN) {
        return new Response(challenge, { status: 200 });
      }
      return new Response('Forbidden', { status: 403 });
    }

    // ── POST：接收事件 ─────────────────────────────────────────
    if (request.method === 'POST') {
      const body = await request.json().catch(() => null);
      if (!body) return new Response('Bad Request', { status: 400 });

      ctx.waitUntil(processWebhook(body, env));
      return new Response('OK', { status: 200 });
    }

    return new Response('Method Not Allowed', { status: 405 });
  }
};

async function processWebhook(body, env) {
  if (!Array.isArray(body.entry)) return;

  for (const entry of body.entry) {
    if (!Array.isArray(entry.changes)) continue;
    for (const change of entry.changes) {
      if (change.field === 'comments' && change.value) {
        await handleComment(change.value, env).catch(console.error);
      }
    }
  }
}

async function handleComment(value, env) {
  // 不回覆自己的留言
  if (String(value.from?.id) === String(env.IG_ID)) return;

  const commentId   = value.id;
  const commentText = value.text || '';
  if (!commentId || !commentText.trim()) return;

  const reply = await generateReply(commentText, env);

  const res = await fetch(`${GRAPH_API}/${commentId}/replies`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: reply, access_token: env.IG_TOKEN })
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    console.error('留言回覆失敗', JSON.stringify(err));
  } else {
    console.log('留言回覆成功：', reply.substring(0, 30));
  }
}

async function generateReply(text, env) {
  const prompt = `你是「龜吼現流活海產 / From Source To TABLE」品牌的客服助理。
品牌特色：野生現流海鮮，龜吼漁港直送，品質第一，服務高端客群，台灣在地漁業。
情境：用戶在我們的 Instagram 貼文或 Reels 下方留言。

請根據以下留言，用繁體中文回覆一段溫暖、專業的短回應：
- 字數不超過 60 字
- 自然親切，符合高端海鮮品牌調性
- 可適當加入 1～2 個相關 emoji
- 若留言與購買/詢價/採購相關，鼓勵私訊詢問
- 只輸出回覆內容本身，不要加引號或任何前綴說明

留言內容：${text}`;

  try {
    const res = await fetch(`${GEMINI_API}?key=${env.GEMINI_KEY}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { maxOutputTokens: 120, temperature: 0.75 }
      })
    });

    const data = await res.json();
    const reply = data.candidates?.[0]?.content?.parts?.[0]?.text?.trim();
    return reply || FALLBACK_REPLY;
  } catch {
    return FALLBACK_REPLY;
  }
}

const FALLBACK_REPLY = '感謝您的留言！有任何海鮮採購需求，歡迎私訊詢問 🐟';
