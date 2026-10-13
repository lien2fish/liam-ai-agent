// 依台灣當天日期切換檔期：行銷圖、檔期文案、價格。沒有進行中的檔期就維持原本內容。
function xuheToday() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Taipei" }).format(new Date());
}

function xuheActive(campaigns, today) {
  return campaigns.find((c) => c.start <= today && today <= c.end) || null;
}

function xuhePrice(n) {
  return n ? "NT$ " + Number(n).toLocaleString("en-US") : "";
}

document.addEventListener("DOMContentLoaded", () => {
  const today = xuheToday();
  document.querySelectorAll("[data-campaigns]").forEach((box) => {
    let campaigns = [];
    try {
      campaigns = JSON.parse(box.dataset.campaigns);
    } catch (e) {
      return;
    }
    const c = xuheActive(campaigns, today);
    const priceEl = box.querySelector("[data-price]");
    const orderEl = box.querySelector("[data-order]");
    const base = priceEl ? Number(priceEl.dataset.base) || null : null;
    const price = (c && c.price) || base;
    if (priceEl) priceEl.textContent = xuhePrice(price);
    if (orderEl) orderEl.hidden = !price;
    if (!c) return;
    const img = box.querySelector("[data-cmp-img]");
    if (img) img.src = box.dataset.imgbase + c.img;
    const set = (sel, text) => {
      const el = box.querySelector(sel);
      if (el) {
        el.textContent = text;
        el.hidden = false;
      }
    };
    set("[data-cmp-festival]", c.festival);
    set("[data-cmp-title]", c.title);
    set("[data-cmp-copy]", c.copy);
    const banner = box.querySelector("[data-cmp-banner]");
    if (banner) banner.hidden = false;
  });
});
