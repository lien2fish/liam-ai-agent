/**
 * Lien（鉅鑫管理顧問）的助理設定。
 * 這是 profile.example.js 的一個實例——程式碼不含任何商業資訊，全部從這裡讀。
 */

export default {
  owner: {
    name: "Lien",
    intro: "你是 Lien（連傳正／鉅鑫管理顧問）的手機助理，透過 LINE 對話。",
  },

  business: `Lien 的事業：炘和管理顧問（籌備中，營業線＝嚴選海鮮、世界名酒、台灣精品茶、肉品；2026-11-16 起新紀錄都記炘和），
過去在鉅鑫的鑫酒藏、鑫海產（龜吼現流海鮮）留作歷史；另有匠鑫私廚、磊山保經壽險/產險業務。品牌核心價值「鉅鑫只提供最高品質」。`,

  tone: `- 一律繁體中文，**簡短**。這是手機聊天視窗，不是報告——通常 3 行以內講完。
- 不要用 Markdown 表格（LINE 不會渲染）。多筆資料用「・」條列。
- 金額寫成 12,500 這種帶千分位的形式。
- 查不到資料就直說查不到，不要猜。
- **工具查出來的清單不要自行摘要、分組或省略。** 要嘛逐筆完整轉述，
  要嘛明講「共 N 筆，這裡列前 M 筆」。使用者無法分辨你是全列了還是偷偷刪減，
  少講了幾筆比講得冗長嚴重得多。`,

  context: `他常在漁港、餐廳、客戶端用手機打字，句子會很短、可能有錯字，用常識判斷他的意思。
他丟一句想法過來通常是要你記下來（add_todo 或 save_note），不是要你分析。
語音訊息轉出來的逐字稿可能有辨識錯誤，海鮮或酒的專有名詞要用常識修正。

存到知識庫（save_note）的時機：他在講產地知識、辨別方法、處理手法、經營心得
——這些是他腦裡才有的東西，要留下來。純粹的待辦事項用 add_todo。`,

  vocabulary: ["龜吼", "現流", "炘和", "嚴選海鮮", "世界名酒", "台灣精品茶", "鑫海產", "鑫酒藏", "匠鑫私廚", "鉅鑫"],

  github: {
    workspaceRepo: "lien2fish/liam-workspace",
    agentRepo: "lien2fish/liam-ai-agent",
    todoPath: "TODO.md",
    knowledgeDir: "knowledge",
    knowledgeBacklog: "_待補清單.md",
  },

  knowledgeCategories: {
    seafood: "海鮮知識",
    wine: "葡萄酒",
    tea: "茶葉",
    business: "經營與客戶",
    misc: "其他",
  },

  crm: {
    customer: {
      db: "CUSTOMER_DB",
      titleField: "客戶姓名",
      fields: ["客戶姓名", "品牌", "聯絡電話", "會員等級", "累計消費", "最後購買日", "偏好品項"],
    },
    sales: {
      db: "SALES_DB",
      matchField: "客戶名稱",
      sortField: "出貨日期",
      fields: ["出貨日期", "品牌", "品項", "數量", "金額"],
    },
  },

  // 手機建訂單（炘和）：打「訂單」叫出格式 → 填好傳回 → 看確認卡 → 回 /確認 才寫入。
  // 公司成立前一律記「個人銷售（未開發票）」（2026-11-10 規則）；成立後要加發票欄分流到炘和訂單。
  // ⛔ 用只連炘和頁面的金鑰（tokenEnv），不可用鉅鑫那把——它看得到整個鉅鑫 CRM 與壽險名單。
  orders: {
    tokenEnv: "XINHE_NOTION_TOKEN",
    salesDb: "XINHE_SALES_DB",
    customerDb: "XINHE_CUSTOMER_DB",
    idPrefix: "P-",
    lines: ["嚴選海鮮", "肉品", "世界名酒", "台灣精品茶", "禮盒", "其他"],
    // 炘和客戶「品類」的選項；禮盒、其他不算品類，不會加到客戶身上
    customerLines: ["嚴選海鮮", "肉品", "世界名酒", "台灣精品茶"],
    payments: ["個人帳戶轉帳", "現金", "LINE Pay"],
    status: "已確認",
    fields: {
      id: "訂單編號", date: "下單日", customer: "客戶", line: "營業線", items: "商品",
      qty: "數量", unitPrice: "單價", amount: "金額", cost: "成本", pay: "收款方式",
      status: "狀態", note: "備註",
    },
    customerFields: {
      title: "姓名", lines: "品類", source: "來源", first: "首次下單日", last: "最後下單日",
    },
    newCustomerSource: "LINE",
    syncNote: "LINE建檔，未記個人帳務表",
  },

  // 允許用 /改庫存 貼表更新數量（兩段式：先看差異清單，回 /確認 才寫入）。
  inventoryWrite: true,

  // ⚠️ 三個品牌的 Notion 欄位名稱互不相同，不要假設一樣。
  inventory: [
    { brand: "鑫酒藏", db: "INV_WINE_DB", name: "品名", qty: "庫存數量", unit: null, price: "進價", priceLabel: "進價" },
    { brand: "鑫海產", db: "INV_SEAFOOD_DB", name: "品名", qty: "庫存數量", unit: "數量單位", price: "進價", priceLabel: "進價" },
  ],

  workflows: {
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
  },

  publishes: ["IG發文", "限動預告", "IG留言回覆", "YouTube影片"],
};
