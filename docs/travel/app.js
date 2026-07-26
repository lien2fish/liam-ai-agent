"use strict";

/* ---------- 狀態 ---------- */
const LS_KEY = "tripPlanner.v1";
const CATS = ["景點", "住宿", "餐飲", "交通", "其他"];
const KEY_LS = "anthropicKey";
const MODEL_LS = "aiModel";
/* 後端代打：部署 travel_worker 後把網址填這裡，一般使用者就免自備金鑰。
   留空＝只能自帶金鑰或跑示範資料。自帶金鑰者一律走自己的，不吃這裡的配額。*/
const WORKER_URL = "https://travel-planner.lien2fish.workers.dev";
/* 支援自帶金鑰：依金鑰前綴自動判斷供應商，兩邊都用 structured outputs 保證合法 JSON。
   Claude Haiku 4.5 為預設（實測 Sonnet 5 貴 11 倍慢 5.7 倍，只多 14pt 定位率，不值得）。*/
const PROVIDERS = {
  anthropic: {
    label: "Claude",
    model: "claude-haiku-4-5",
    match: (k) => k.startsWith("sk-ant-"),
    url: "https://api.anthropic.com/v1/messages",
    headers: (k) => ({
      "content-type": "application/json",
      "x-api-key": k,
      "anthropic-version": "2023-06-01",
      "anthropic-dangerous-direct-browser-access": "true",
    }),
    body: (model, prompt) => ({
      model,
      max_tokens: 16000,
      output_config: { format: { type: "json_schema", schema: PLAN_SCHEMA } }, // Haiku 不支援 effort，加了會 400
      messages: [{ role: "user", content: prompt }],
    }),
    parse: (d) => {
      if (d.stop_reason === "refusal") throw new Error("AI 婉拒了這個請求，換個描述試試");
      if (d.stop_reason === "max_tokens") throw new Error("行程太長被截斷，請減少天數再試");
      return (d.content || []).filter((b) => b.type === "text").map((b) => b.text).join("");
    },
  },
  openai: {
    label: "ChatGPT",
    model: "gpt-4o-mini",
    match: (k) => k.startsWith("sk-"),
    url: "https://api.openai.com/v1/chat/completions",
    headers: (k) => ({ "content-type": "application/json", authorization: `Bearer ${k}` }),
    body: (model, prompt) => ({
      model,
      max_completion_tokens: 16000,
      response_format: {
        type: "json_schema",
        json_schema: { name: "trip_plans", strict: true, schema: PLAN_SCHEMA },
      },
      messages: [{ role: "user", content: prompt }],
    }),
    parse: (d) => {
      const c = (d.choices || [])[0];
      if (!c) throw new Error("AI 沒有回傳內容，請再試一次");
      if (c.finish_reason === "length") throw new Error("行程太長被截斷，請減少天數再試");
      if (c.message && c.message.refusal) throw new Error("AI 婉拒了這個請求，換個描述試試");
      return (c.message || {}).content || "";
    },
  },
};

function providerFor(key) {
  return Object.values(PROVIDERS).find((p) => p.match(key)) || PROVIDERS.anthropic;
}
function modelFor(p) {
  return (localStorage.getItem(MODEL_LS) || "").trim() || p.model;
}
const MODE_LABEL = { driving: "🚗", walking: "🚶" };

let state = load();
let addCat = "景點";

function load() {
  try {
    const s = JSON.parse(localStorage.getItem(LS_KEY));
    if (s && s.trips) {
      s.trips.forEach((t) => (t.travelMode = /walk/i.test(t.travelMode || "") ? "walking" : "driving"));
      return s;
    }
  } catch (e) {}
  const trip = newTrip("我的第一趟旅程");
  return { trips: [trip], activeTripId: trip.id, activeDay: 1 };
}
function save() {
  localStorage.setItem(LS_KEY, JSON.stringify(state));
}
function uid() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
}
function newTrip(name) {
  return { id: uid(), name, days: 3, travelMode: "driving", budget: null, stops: [] };
}
function activeTrip() {
  return state.trips.find((t) => t.id === state.activeTripId) || state.trips[0];
}
function dayStops(day) {
  return activeTrip()
    .stops.filter((s) => s.day === day)
    .sort((a, b) => a.order - b.order);
}

/* ---------- DOM ---------- */
const $ = (id) => document.getElementById(id);
const el = {};
[
  "map", "tripSelect", "dayTabs", "placeSearch", "catPick", "stopList", "dayTotals",
  "budgetInput", "budgetSummary", "catBreakdown", "dayBreakdown",
  "apiKeyInput", "keyState", "importFile",
].forEach((k) => (el[k] = $(k)));

/* ---------- 分頁切換 ---------- */
document.querySelectorAll(".tab").forEach((b) =>
  b.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
    document.querySelectorAll(".view").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    $("view-" + b.dataset.tab).classList.add("active");
    if (b.dataset.tab === "budget") renderBudget();
    if (lmap) setTimeout(() => { lmap.invalidateSize(); fitMap(); }, 60);
  })
);

/* 加入類別選擇 */
el.catPick.querySelectorAll(".chip").forEach((c) =>
  c.addEventListener("click", () => {
    el.catPick.querySelectorAll(".chip").forEach((x) => x.classList.remove("active"));
    c.classList.add("active");
    addCat = c.dataset.cat;
  })
);

/* 交通方式 */
document.querySelectorAll(".chip.mode").forEach((c) =>
  c.addEventListener("click", () => {
    document.querySelectorAll(".chip.mode").forEach((x) => x.classList.remove("active"));
    c.classList.add("active");
    activeTrip().travelMode = c.dataset.mode;
    save();
    renderMapRoute();
  })
);

/* ---------- 行程/天數/管理 ---------- */
el.tripSelect.addEventListener("change", () => {
  state.activeTripId = el.tripSelect.value;
  state.activeDay = 1;
  save();
  renderAll();
});
$("navDayBtn").addEventListener("click", navigateDay);
$("newTripBtn").addEventListener("click", () => {
  const name = prompt("新行程名稱？", "宜蘭三天兩夜");
  if (!name) return;
  const t = newTrip(name.trim());
  state.trips.push(t);
  state.activeTripId = t.id;
  state.activeDay = 1;
  save();
  renderAll();
});
$("renameTripBtn").addEventListener("click", () => {
  const name = prompt("行程改名", activeTrip().name);
  if (!name) return;
  activeTrip().name = name.trim();
  save();
  renderTripSelect();
});
$("setDaysBtn").addEventListener("click", () => {
  const n = parseInt(prompt("這趟共幾天？", activeTrip().days), 10);
  if (!n || n < 1 || n > 30) return;
  activeTrip().days = n;
  if (state.activeDay > n) state.activeDay = 1;
  save();
  renderAll();
});
$("deleteTripBtn").addEventListener("click", () => {
  if (state.trips.length <= 1) return toast("至少保留一個行程");
  if (!confirm("刪除「" + activeTrip().name + "」？此動作無法復原")) return;
  state.trips = state.trips.filter((t) => t.id !== state.activeTripId);
  state.activeTripId = state.trips[0].id;
  state.activeDay = 1;
  save();
  renderAll();
});
$("exportBtn").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(activeTrip(), null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = activeTrip().name.replace(/\s+/g, "_") + ".json";
  a.click();
});
$("importBtn").addEventListener("click", () => el.importFile.click());
el.importFile.addEventListener("change", (e) => {
  const f = e.target.files[0];
  if (!f) return;
  const r = new FileReader();
  r.onload = () => {
    try {
      const t = JSON.parse(r.result);
      if (!t.stops) throw 0;
      t.id = uid();
      state.trips.push(t);
      state.activeTripId = t.id;
      save();
      renderAll();
      toast("已匯入行程");
    } catch (x) {
      toast("檔案格式不正確");
    }
  };
  r.readAsText(f);
  el.importFile.value = "";
});

/* ---------- 花費 ---------- */
el.budgetInput.addEventListener("input", () => {
  const v = parseFloat(el.budgetInput.value);
  activeTrip().budget = isNaN(v) ? null : v;
  save();
  renderBudget();
});

/* ---------- 渲染 ---------- */
function renderTripSelect() {
  el.tripSelect.innerHTML = state.trips
    .map((t) => `<option value="${t.id}">${escapeHtml(t.name)}</option>`)
    .join("");
  el.tripSelect.value = state.activeTripId;
}
function renderDayTabs() {
  const t = activeTrip();
  let h = "";
  for (let d = 1; d <= t.days; d++) {
    h += `<button class="daytab ${d === state.activeDay ? "active" : ""}" data-day="${d}">Day ${d}</button>`;
  }
  el.dayTabs.innerHTML = h;
  el.dayTabs.querySelectorAll(".daytab").forEach((b) =>
    b.addEventListener("click", () => {
      state.activeDay = parseInt(b.dataset.day, 10);
      save();
      renderDayTabs();
      renderStops();
      renderMapRoute();
    })
  );
}
function renderStops() {
  const stops = dayStops(state.activeDay);
  if (!stops.length) {
    el.stopList.innerHTML = `<li class="empty">還沒有行程點。<br>用上方搜尋加入景點、住宿或餐廳吧！</li>`;
    el.dayTotals.textContent = "";
    return;
  }
  el.stopList.innerHTML = stops
    .map((s, i) => {
      const opts = CATS.map((c) => `<option ${c === s.category ? "selected" : ""}>${c}</option>`).join("");
      const unlocated = typeof s.lat !== "number";
      return `
      <li class="stop${unlocated ? " unlocated" : ""}" data-id="${s.id}">
        <div class="stop-head">
          <div class="badge">${i + 1}</div>
          <div class="stop-name">${escapeHtml(s.name)}<div class="stop-cat">${s.category}${s.minutes ? " · 停留 " + s.minutes + " 分" : ""}</div></div>
          <button class="iconbtn gmap" title="用 Google 地圖開啟">🧭</button>
          ${unlocated ? `<button class="iconbtn locate" title="行程內地圖查不到，手動定位">📍</button>` : ""}
          <button class="iconbtn up" title="上移">▲</button>
          <button class="iconbtn down" title="下移">▼</button>
          <button class="iconbtn danger del" title="刪除">✕</button>
        </div>
        ${s.note ? `<div class="stop-note">${escapeHtml(s.note)}</div>` : ""}
        ${s.address ? `<div class="stop-addr">${escapeHtml(s.address)}</div>` : ""}
        ${unlocated ? `<div class="stop-warn">地圖上查不到這個地點，行程仍會保留。按 📍 可手動搜尋定位。</div>` : ""}
        <div class="stop-ctrls">
          <select class="cat">${opts}</select>
          <input class="cost-in" type="number" inputmode="numeric" placeholder="花費" value="${s.cost || ""}" />
          <span class="stop-cat">元</span>
        </div>
      </li>
      <div class="leg" data-leg="${i}"></div>`;
    })
    .join("");

  el.stopList.querySelectorAll(".stop").forEach((li) => {
    const id = li.dataset.id;
    li.querySelector(".up").onclick = () => move(id, -1);
    li.querySelector(".down").onclick = () => move(id, 1);
    li.querySelector(".gmap").onclick = () => openInGmap(id);
    const locBtn = li.querySelector(".locate");
    if (locBtn) locBtn.onclick = () => relocate(id);
    li.querySelector(".del").onclick = () => {
      activeTrip().stops = activeTrip().stops.filter((x) => x.id !== id);
      reindex();
      save();
      renderStops();
      renderMapRoute();
      renderBudget();
    };
    li.querySelector(".cat").onchange = (e) => {
      getStop(id).category = e.target.value;
      save();
      renderStops();
    };
    li.querySelector(".cost-in").oninput = (e) => {
      getStop(id).cost = parseFloat(e.target.value) || 0;
      save();
      updateDayTotals();
    };
  });
  updateDayTotals();
}
/* ---- Google 地圖導向（吃地名不吃座標，定位失敗的點照樣能導航）---- */
function gmapQuery(s) {
  // 有座標就用座標（最準），沒有就用「地名, 地區」讓 Google 自己找
  if (typeof s.lat === "number") return `${s.lat},${s.lng}`;
  const region = (activeTrip().name.split("·")[0] || "").trim();
  return encodeURIComponent(region && !s.name.includes(region) ? `${s.name} ${region}` : s.name);
}
function openInGmap(id) {
  const s = getStop(id);
  if (!s) return;
  window.open(`https://www.google.com/maps/search/?api=1&query=${gmapQuery(s)}`, "_blank");
}
function navigateDay() {
  const stops = dayStops(state.activeDay);
  if (stops.length < 1) return toast("這天還沒有行程點");
  if (stops.length === 1) return openInGmap(stops[0].id);
  const pts = stops.map(gmapQuery);
  const origin = pts[0];
  const destination = pts[pts.length - 1];
  const mid = pts.slice(1, -1).slice(0, 9); // Google 連結最多 9 個中繼點
  const mode = activeTrip().travelMode === "walking" ? "walking" : "driving";
  let url = `https://www.google.com/maps/dir/?api=1&origin=${origin}&destination=${destination}&travelmode=${mode}`;
  if (mid.length) url += `&waypoints=${mid.join("|")}`;
  window.open(url, "_blank");
  if (stops.length > 11) toast("Google 導航最多 11 個點，已帶入前 11 個");
}

function updateDayTotals() {
  const stops = dayStops(state.activeDay);
  const cost = stops.reduce((a, s) => a + (s.cost || 0), 0);
  el.dayTotals.textContent = `Day ${state.activeDay}：${stops.length} 個點 · 花費 $${cost.toLocaleString()}`;
}
function getStop(id) {
  return activeTrip().stops.find((s) => s.id === id);
}
function move(id, dir) {
  const stops = dayStops(state.activeDay);
  const i = stops.findIndex((s) => s.id === id);
  const j = i + dir;
  if (j < 0 || j >= stops.length) return;
  [stops[i].order, stops[j].order] = [stops[j].order, stops[i].order];
  save();
  renderStops();
  renderMapRoute();
}
function reindex() {
  for (let d = 1; d <= activeTrip().days; d++) {
    dayStops(d).forEach((s, i) => (s.order = i));
  }
}

function renderBudget() {
  const t = activeTrip();
  el.budgetInput.value = t.budget ?? "";
  const total = t.stops.reduce((a, s) => a + (s.cost || 0), 0);
  let sum = `<div class="big">$${total.toLocaleString()}</div><div class="sub">全程總花費</div>`;
  if (t.budget) {
    const pct = Math.min(100, (total / t.budget) * 100);
    const over = total > t.budget;
    sum += `<div class="bar ${over ? "over" : ""}"><i style="width:${pct}%"></i></div>
      <div class="sub">預算 $${t.budget.toLocaleString()} · ${over ? "超支 $" + (total - t.budget).toLocaleString() : "剩餘 $" + (t.budget - total).toLocaleString()}</div>`;
  }
  el.budgetSummary.innerHTML = sum;

  const byCat = {};
  CATS.forEach((c) => (byCat[c] = 0));
  t.stops.forEach((s) => (byCat[s.category] = (byCat[s.category] || 0) + (s.cost || 0)));
  el.catBreakdown.innerHTML =
    CATS.filter((c) => byCat[c] > 0)
      .map((c) => `<li><span>${c}</span><span class="v">$${byCat[c].toLocaleString()}</span></li>`)
      .join("") || `<li class="empty">還沒有花費紀錄</li>`;

  let dh = "";
  for (let d = 1; d <= t.days; d++) {
    const c = dayStops(d).reduce((a, s) => a + (s.cost || 0), 0);
    dh += `<li><span>Day ${d}</span><span class="v">$${c.toLocaleString()}</span></li>`;
  }
  el.dayBreakdown.innerHTML = dh;
}

function renderAll() {
  renderTripSelect();
  renderDayTabs();
  renderStops();
  renderBudget();
  syncModeChips();
  renderMapRoute();
}
function syncModeChips() {
  document.querySelectorAll(".chip.mode").forEach((c) =>
    c.classList.toggle("active", c.dataset.mode === activeTrip().travelMode)
  );
}

/* ---------- 工具 ---------- */
function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
}
let toastT;
function toast(msg) {
  let t = document.querySelector(".toast");
  if (!t) {
    t = document.createElement("div");
    t.className = "toast";
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toastT);
  toastT = setTimeout(() => t.classList.remove("show"), 2200);
}

/* ================= 地圖：Leaflet + OpenStreetMap（免金鑰） ================= */
let lmap, markerLayer, routeLayer;

function initMap() {
  lmap = L.map(el.map, { zoomControl: true }).setView([23.9738, 120.9797], 7);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap",
  }).addTo(lmap);
  markerLayer = L.layerGroup().addTo(lmap);
  routeLayer = L.layerGroup().addTo(lmap);
  setTimeout(() => lmap.invalidateSize(), 200);
  renderMapRoute();
}

/* ---- Nominatim 地名搜尋（免金鑰） ---- */
let searchTimer, searchBox, relocating = null;

/* 定位失敗的點：把名稱帶進搜尋框，選中結果後更新該筆而非新增 */
function relocate(id) {
  const s = getStop(id);
  if (!s) return;
  relocating = id;
  el.placeSearch.value = s.name;
  el.placeSearch.focus();
  el.placeSearch.dispatchEvent(new Event("input"));
  toast("選一個搜尋結果來定位這個點");
}
function shortName(p) {
  return p.name || (p.display_name || "").split(",")[0];
}
function setupSearch() {
  searchBox = document.createElement("ul");
  searchBox.className = "searchresults";
  el.placeSearch.parentNode.appendChild(searchBox);

  const run = () => {
    const q = el.placeSearch.value.trim();
    if (q.length < 2) return (searchBox.innerHTML = "");
    searchBox.innerHTML = '<li class="sr-hint">搜尋中…</li>';
    fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=6&accept-language=zh-TW&q=${encodeURIComponent(q)}`)
      .then((r) => r.json())
      .then((list) => {
        if (!list.length) return (searchBox.innerHTML = '<li class="sr-hint">找不到，換個關鍵字試試</li>');
        searchBox.innerHTML = list
          .map((p, i) => `<li class="sr" data-i="${i}"><b>${escapeHtml(shortName(p))}</b><span>${escapeHtml(p.display_name)}</span></li>`)
          .join("");
        searchBox.querySelectorAll(".sr").forEach((li) =>
          (li.onclick = () => {
            const p = list[+li.dataset.i];
            const info = { name: shortName(p), address: p.display_name || "", lat: +p.lat, lng: +p.lon };
            if (relocating) {
              const s = getStop(relocating);
              if (s) {
                s.lat = info.lat;
                s.lng = info.lng;
                s.address = info.address;
                delete s.locateFail;
                save();
                renderStops();
                renderMapRoute();
                toast(`已定位「${s.name}」`);
              }
              relocating = null;
            } else {
              addStop(info);
            }
            el.placeSearch.value = "";
            searchBox.innerHTML = "";
          })
        );
      })
      .catch(() => (searchBox.innerHTML = '<li class="sr-hint">搜尋失敗，請檢查網路</li>'));
  };
  el.placeSearch.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(run, 550);
  });
  el.placeSearch.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      clearTimeout(searchTimer);
      run();
    }
  });
  document.addEventListener("click", (e) => {
    if (searchBox && !searchBox.contains(e.target) && e.target !== el.placeSearch) searchBox.innerHTML = "";
  });
}

function addStop(info) {
  const order = dayStops(state.activeDay).length;
  activeTrip().stops.push({
    id: uid(), day: state.activeDay, order,
    name: info.name, address: info.address, lat: info.lat, lng: info.lng,
    category: addCat, cost: 0, note: "",
  });
  save();
  renderStops();
  renderMapRoute();
  renderBudget();
  toast(`已加入 ${info.name}`);
}

function numIcon(n) {
  return L.divIcon({ className: "num-marker", html: `<div>${n}</div>`, iconSize: [28, 28], iconAnchor: [14, 14] });
}
function fitMap() {
  if (!lmap) return;
  const stops = dayStops(state.activeDay).filter((s) => typeof s.lat === "number");
  if (!stops.length) return;
  lmap.fitBounds(L.latLngBounds(stops.map((s) => [s.lat, s.lng])), { padding: [40, 40], maxZoom: 15 });
}
function fmtDur(sec) {
  const m = Math.round(sec / 60);
  return m < 60 ? `${m} 分` : `${Math.floor(m / 60)} 時 ${m % 60} 分`;
}
function fmtDist(m) {
  return m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toFixed(1)} km`;
}

function renderMapRoute() {
  if (!lmap) return;
  markerLayer.clearLayers();
  routeLayer.clearLayers();
  document.querySelectorAll(".leg").forEach((l) => (l.textContent = ""));
  const all = dayStops(state.activeDay);
  const located = all.filter((s) => typeof s.lat === "number");
  if (!located.length) return;

  located.forEach((s) =>
    L.marker([s.lat, s.lng], { icon: numIcon(all.indexOf(s) + 1), title: s.name }).addTo(markerLayer)
  );
  fitMap();
  if (all.length < 2 || located.length !== all.length) return; // 尚有點未定位就先不畫路線

  const stops = all;
  const mode = activeTrip().travelMode === "walking" ? "walking" : "driving";
  const coords = stops.map((s) => `${s.lng},${s.lat}`).join(";");
  fetch(`https://router.project-osrm.org/route/v1/driving/${coords}?overview=full&geometries=geojson`)
    .then((r) => r.json())
    .then((res) => {
      if (res.code !== "Ok" || !res.routes || !res.routes.length) return;
      const route = res.routes[0];
      L.polyline(route.geometry.coordinates.map((c) => [c[1], c[0]]), {
        color: "#e8804a", weight: 5, opacity: 0.85,
      }).addTo(routeLayer);
      let totSec = 0;
      route.legs.forEach((leg, i) => {
        const sec = mode === "walking" ? leg.distance / 1.35 : leg.duration; // 步行以距離估算
        totSec += sec;
        const node = document.querySelector(`.leg[data-leg="${i}"]`);
        if (node) node.textContent = `${MODE_LABEL[mode]} ${fmtDur(sec)} · ${fmtDist(leg.distance)}`;
      });
      el.dayTotals.textContent += ` · 交通約 ${fmtDur(totSec)}`;
    })
    .catch(() => {});
}

/* ================= 智慧規劃（AI） ================= */
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let kids = [];
let wants = new Set();
let pace = "適中";
let transport = "自駕";
let lastCond = null;
async function nomSearch(params) {
  try {
    const r = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&accept-language=zh-TW&${params}`);
    const list = await r.json();
    return list && list.length ? list[0] : null;
  } catch (e) {
    return null;
  }
}
// 取地區範圍(含padding)當 viewbox，讓景點只在該地區內搜、避免跨國誤配
async function geocodeRegion(region) {
  if (!region) return null;
  const p = await nomSearch(`q=${encodeURIComponent(region)}`);
  if (!p || !p.boundingbox) return null;
  const bb = p.boundingbox.map(Number); // [minlat, maxlat, minlon, maxlon]
  const pad = 0.25;
  return { lat: +p.lat, lng: +p.lon, viewbox: `${bb[2] - pad},${bb[0] - pad},${bb[3] + pad},${bb[1] + pad}` };
}
function haversineKm(a, b) {
  const R = 6371, d = (x) => (x * Math.PI) / 180;
  const dLat = d(b.lat - a.lat), dLng = d(b.lng - a.lng);
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(d(a.lat)) * Math.cos(d(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
}
// 先在地區範圍內找(bounded)，查不到放寬；離地區中心太遠＝誤配則捨棄(回 null)
async function geocodeNear(q, region) {
  const vb = region && region.viewbox;
  let p = vb ? await nomSearch(`q=${encodeURIComponent(q)}&viewbox=${vb}&bounded=1`) : null;
  if (!p) p = await nomSearch(`q=${encodeURIComponent(q)}`);
  if (!p) return null;
  const pt = { lat: +p.lat, lng: +p.lon };
  if (region && region.lat && haversineKm(pt, region) > 60) return null; // 誤配防線
  return pt;
}

function renderKids() {
  const w = $("kidsWrap");
  w.innerHTML = kids
    .map((age, i) => `<span class="kid"><input type="number" inputmode="numeric" min="0" max="18" value="${age}" data-i="${i}" /><span>歲</span><button data-i="${i}">✕</button></span>`)
    .join("");
  w.querySelectorAll("input").forEach((inp) => (inp.oninput = (e) => (kids[+e.target.dataset.i] = e.target.value)));
  w.querySelectorAll("button").forEach((b) => (b.onclick = () => { kids.splice(+b.dataset.i, 1); renderKids(); }));
}
$("addKid").onclick = () => { kids.push(6); renderKids(); };
$("wantPick").querySelectorAll(".want").forEach((c) =>
  (c.onclick = () => { c.classList.toggle("active"); c.classList.contains("active") ? wants.add(c.dataset.w) : wants.delete(c.dataset.w); })
);
$("pacePick").querySelectorAll(".pace").forEach((c) =>
  (c.onclick = () => { $("pacePick").querySelectorAll(".pace").forEach((x) => x.classList.remove("active")); c.classList.add("active"); pace = c.dataset.pace; })
);
$("transportPick").querySelectorAll(".trans").forEach((c) =>
  (c.onclick = () => { $("transportPick").querySelectorAll(".trans").forEach((x) => x.classList.remove("active")); c.classList.add("active"); transport = c.dataset.t; })
);

function collectCond() {
  return {
    region: $("f_region").value.trim(),
    adults: parseInt($("f_adults").value) || 0,
    kids: kids.map((a) => parseInt(a) || 0),
    days: parseInt($("f_days").value) || 1,
    budget: parseFloat($("f_budget").value) || null,
    transport,
    maxDrive: parseInt($("f_maxdrive").value) || 90,
    needs: $("f_needs").value.trim(),
    wants: [...wants],
    pace,
  };
}

$("genBtn").onclick = async () => {
  const cond = collectCond();
  if (!cond.region) return toast("請填目標城市／地區");
  lastCond = cond;
  const box = $("planResults"), btn = $("genBtn");
  btn.disabled = true;
  box.innerHTML = `<div class="gen-loading"><div class="spin"></div><p>AI 規劃兩種方案中… 約 30-50 秒，請勿關閉</p></div>`;
  try {
    renderPlans(await generatePlans(cond));
  } catch (e) {
    box.innerHTML = `<p class="empty">生成失敗：${escapeHtml(e.message || "請稍後再試")}</p>`;
  } finally {
    btn.disabled = false;
  }
};

/* ---- Claude API（瀏覽器直呼，金鑰存本機） ---- */
function apiKey() {
  return (localStorage.getItem(KEY_LS) || "").trim();
}
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
- 交通方式為 ${c.transport}，據此決定景點之間的可行性
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

/* 找出跨天重複的地點；正規化後比對（去空白/全形括號補述/「觀光」等贅字） */
function normName(s) {
  return (s || "")
    .replace(/[（(].*?[）)]/g, "")
    .replace(/觀光|國立|市立|縣立/g, "")
    .replace(/\s+/g, "")
    .trim();
}
function findDupes(plan) {
  const seen = new Map(), dupes = [];
  (plan.days || []).forEach((d) =>
    (d.spots || []).forEach((s) => {
      const k = normName(s.name);
      if (!k) return;
      if (seen.has(k) && seen.get(k) !== d.day) dupes.push(s.name);
      else if (!seen.has(k)) seen.set(k, d.day);
    })
  );
  return [...new Set(dupes)];
}

const allDupes = (plans) => [...new Set(plans.flatMap(findDupes))];

async function generatePlans(cond) {
  const key = apiKey();
  if (!key && WORKER_URL) return callWorker(cond); // 免金鑰：走後端配額
  if (!key) { await sleep(900); return mockPlans(cond); } // 兩者皆無＝示範行程

  let plans = (await callPlan(cond, key)).plans || [];
  // Haiku 偶爾會跨天重排同一個地點，重生一次通常就乾淨了
  const bad = allDupes(plans);
  if (bad.length) {
    const retry = (await callPlan(cond, key, bad)).plans || [];
    if (retry.length && allDupes(retry).length <= bad.length) plans = retry;
  }
  return plans;
}

/* 後端代打：只送表單欄位，prompt 與金鑰都在 Worker 那邊 */
async function callWorker(cond) {
  let res;
  try {
    res = await fetch(WORKER_URL, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ params: cond }),
    });
  } catch (e) {
    throw new Error("連不上規劃服務，請檢查網路");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.message || `規劃服務回應 ${res.status}`);
  return data.plans || [];
}

async function callPlan(cond, key, avoidDupes) {
  const extra = avoidDupes && avoidDupes.length
    ? `\n\n⚠️ 上一次的結果把「${avoidDupes.join("、")}」重複排在不同天，這次務必讓每個地點只出現一次。`
    : "";
  const p = providerFor(key);
  const model = modelFor(p);
  let res;
  try {
    res = await fetch(p.url, {
      method: "POST",
      headers: p.headers(key),
      body: JSON.stringify(p.body(model, planPrompt(cond) + extra)),
    });
  } catch (e) {
    throw new Error(`連不上 ${p.label}，請檢查網路（若剛換金鑰，確認格式正確）`);
  }

  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    const msg = detail && detail.error && detail.error.message;
    if (res.status === 401) throw new Error(`${p.label} 金鑰無效，請到設定重新貼上`);
    if (res.status === 429) throw new Error("呼叫太頻繁或額度用完，稍後再試");
    if (res.status === 404 || /model/i.test(msg || "")) {
      throw new Error(`${p.label} 找不到模型「${model}」，可到設定改指定模型`);
    }
    throw new Error(msg || `${p.label} 回應 ${res.status}`);
  }

  const text = p.parse(await res.json());
  if (!text) throw new Error("AI 沒有回傳內容，請再試一次");
  return JSON.parse(text);
}

function renderPlans(plans) {
  const box = $("planResults");
  if (!plans.length) return (box.innerHTML = `<p class="empty">沒有產生行程，換個條件試試</p>`);
  box.innerHTML =
    `<h3>為你規劃了 ${plans.length} 種方案</h3>` + plans.map(planCard).join("") +
    `<p class="hint">營業時間與費用為 AI 概估，出發前請向店家確認。</p>`;
  box.querySelectorAll(".plan-adopt").forEach((b) =>
    (b.onclick = () => adoptPlan(plans[+b.dataset.pi]))
  );
}

function planCard(plan, pi) {
  const days = plan.days || [];
  const spots = days.reduce((a, d) => a + (d.spots || []).length, 0);
  const perHead = days.reduce((a, d) => a + (d.spots || []).reduce((x, s) => x + (+s.cost_estimate || 0), 0), 0);
  const heads = (lastCond ? lastCond.adults + lastCond.kids.length : 1) || 1;
  const stays = plan.accommodation || [];
  const stayCost = stays.reduce((a, s) => a + (+s.cost_per_night || 0) * (+s.nights_count || 0), 0);
  const total = perHead * heads + stayCost;
  const dupes = findDupes(plan);

  return `
    <div class="plan-card">
      <h3>${escapeHtml(plan.title || "行程")} <span class="plan-theme">${escapeHtml(plan.theme || "")}</span></h3>
      <p class="plan-sum">${escapeHtml(plan.summary || "")}</p>
      <div class="plan-meta">
        <span>📅 ${days.length} 天</span>
        <span>📍 ${spots} 個點</span>
        <span>💰 全家約 <b>$${total.toLocaleString()}</b></span>
      </div>
      <div class="plan-costbreak">
        景點餐飲 $${(perHead * heads).toLocaleString()}（每人 $${perHead.toLocaleString()} × ${heads} 人）${stayCost ? ` ＋ 住宿 $${stayCost.toLocaleString()}` : ""}
      </div>
      ${stays.length ? `<ul class="plan-stays">${stays.map((s) => `
        <li>
          <div class="s-head">🏨 ${escapeHtml(s.nights || "")} · ${escapeHtml(s.area || "")}</div>
          <div class="s-price">${escapeHtml(s.price_range || "")}／晚　共 ${s.nights_count || 0} 晚　約 $${((+s.cost_per_night || 0) * (+s.nights_count || 0)).toLocaleString()}</div>
          <div class="s-why">${escapeHtml(s.reason || "")}</div>
        </li>`).join("")}</ul>` : ""}
      <ul class="plan-days">
        ${days.map((d) => `
          <li>
            <div class="d-head">Day ${d.day} · ${escapeHtml(d.theme || "")}</div>
            <div class="d-items">${(d.spots || []).map((s) => `${s.indoor ? "🏠" : "🌤"} ${escapeHtml(s.name)}`).join("　")}</div>
            ${d.rainy_alternative ? `<div class="d-rainy">☔️ 雨天：${escapeHtml(d.rainy_alternative)}</div>` : ""}
          </li>`).join("")}
      </ul>
      ${plan.notes ? `<div class="plan-acc">📝 ${escapeHtml(plan.notes)}</div>` : ""}
      ${dupes.length ? `<div class="plan-warn">⚠️ 這份行程把「${escapeHtml(dupes.join("、"))}」重複排在不同天，可再按一次生成換一份。</div>` : ""}
      <button class="primary plan-adopt" data-pi="${pi}">採用這個方案 →</button>
    </div>`;
}

async function adoptPlan(plan) {
  const region = (lastCond && lastCond.region) || "旅程";
  const heads = (lastCond ? lastCond.adults + lastCond.kids.length : 1) || 1;
  const t = newTrip(`${region}·${plan.title || ""}`.slice(0, 28));
  t.days = (plan.days || []).length || 1;
  t.budget = (lastCond && lastCond.budget) || null;
  (plan.days || []).forEach((d, di) =>
    (d.spots || []).forEach((s, oi) =>
      t.stops.push({
        id: uid(), day: d.day || di + 1, order: oi,
        name: s.name,
        address: [s.age_range, s.opening_hours].filter(Boolean).join(" · "),
        lat: null, lng: null,
        category: CATS.includes(s.category) ? s.category : "景點",
        cost: (+s.cost_estimate || 0) * heads, // schema 給每人，行程一律存全家總額
        note: s.reason || "",
        indoor: !!s.indoor,
        minutes: +s.duration_minutes || 0,
        _q: `${s.name}, ${region}`,
      })
    )
  );
  // 住宿：一筆放在該住宿區間的第一天末尾，費用是整段總額（每晚每間房 × 晚數）
  let night = 1;
  (plan.accommodation || []).forEach((a) => {
    const n = +a.nights_count || 0;
    if (!n) return;
    t.stops.push({
      id: uid(), day: Math.min(night, t.days), order: 99,
      name: a.area,
      address: [a.nights, a.price_range ? a.price_range + "／晚" : ""].filter(Boolean).join(" · "),
      lat: null, lng: null,
      category: "住宿",
      cost: (+a.cost_per_night || 0) * n,
      note: a.reason || "",
      minutes: 0,
      _q: `${a.area}, ${region}`,
    });
    night += n;
  });
  state.trips.push(t);
  state.activeTripId = t.id;
  state.activeDay = 1;
  reindex(); // 住宿用 order:99 插在當天最後，設為作用中行程後才能正確重排
  save();
  document.querySelector('.tab[data-tab="trip"]').click();
  renderAll();
  toast("行程已帶入，定位景點中…");

  const regionGeo = await geocodeRegion(region);
  let miss = 0;
  for (const s of t.stops) {
    const g = await geocodeNear(s._q, regionGeo);
    if (g) {
      s.lat = g.lat;
      s.lng = g.lng;
    } else {
      s.locateFail = true; // 查不到不刪除，保留在行程裡供手動定位
      miss++;
    }
    delete s._q;
    save();
    if (state.activeTripId === t.id) { renderStops(); renderMapRoute(); }
    await sleep(1100); // 尊重 Nominatim 1 req/s
  }
  toast(miss ? `定位完成，${miss} 個點地圖上查不到，可按 📍 手動定位` : "景點定位完成 ✓");
}

/* 內建示範行程（未設金鑰時用）*/
function mockPlans(cond) {
  const region = cond.region || "台灣";
  const presets = {
    宜蘭: ["蘭陽博物館", "國立傳統藝術中心", "羅東林業文化園區", "冬山河親水公園"],
    台北: ["國立故宮博物院", "台北市立動物園", "大安森林公園", "北投溫泉博物館"],
    花蓮: ["七星潭", "鯉魚潭", "花蓮觀光糖廠", "石梯坪"],
    台中: ["國立自然科學博物館", "東勢林場", "台中市中山公園", "高美濕地"],
  };
  const key = Object.keys(presets).find((k) => region.includes(k));
  const pool = key ? presets[key] : [`${region}火車站`, `${region}文化中心`, `${region}公園`, `${region}老街`];
  const build = (offset, theme) => {
    const days = [];
    let idx = offset;
    for (let d = 1; d <= Math.max(1, cond.days || 2); d++) {
      const spots = [];
      for (let k = 0; k < 3; k++, idx++) {
        spots.push({
          name: pool[idx % pool.length],
          reason: "示範資料：設定 API 金鑰後才會產生真正依家庭條件規劃的理由",
          age_range: "全年齡", indoor: k === 0, duration_minutes: 90,
          category: "景點", opening_hours: "請自行確認", cost_estimate: 100 * (k + 1),
        });
      }
      days.push({ day: d, theme: `示範行程第 ${d} 天`, rainy_alternative: "示範資料", spots });
    }
    const nights = Math.max(0, days.length - 1);
    return {
      title: `${region}${theme}`, theme,
      summary: "這是未設定金鑰時的內建示範，不是 AI 規劃結果。",
      notes: "到設定頁貼上 API 金鑰即可使用真正的 AI 規劃。",
      accommodation: nights
        ? [{ nights: `第1-${nights}晚`, nights_count: nights, area: `${region}市區`, reason: "示範資料", price_range: "$3,000-4,000", cost_per_night: 3500 }]
        : [],
      days,
    };
  };
  return [build(0, "示範方案A"), build(2, "示範方案B")];
}

/* ---------- 金鑰設定 ---------- */
function renderKeyState() {
  const k = apiKey();
  if (!k) {
    el.keyState.textContent = WORKER_URL
      ? "未設定，使用免費共用額度（每天 5 次）"
      : "尚未設定，智慧規劃跑內建示範方案";
  } else {
    const p = providerFor(k);
    el.keyState.textContent = `✅ 已設定 ${p.label}（${k.slice(0, 7)}…${k.slice(-4)}）· 模型 ${modelFor(p)}`;
  }
  const m = (localStorage.getItem(MODEL_LS) || "").trim();
  $("modelState").textContent = m ? `目前指定：${m}` : "使用各家預設模型";
}
$("saveModelBtn").onclick = () => {
  const v = $("modelInput").value.trim();
  v ? localStorage.setItem(MODEL_LS, v) : localStorage.removeItem(MODEL_LS);
  $("modelInput").value = "";
  renderKeyState();
  toast(v ? `模型已設為 ${v}` : "已改回預設模型");
};
$("saveKeyBtn").onclick = () => {
  const v = el.apiKeyInput.value.trim();
  if (!v) return toast("請先貼上金鑰");
  localStorage.setItem(KEY_LS, v);
  el.apiKeyInput.value = "";
  renderKeyState();
  toast("金鑰已存在本機");
};
$("clearKeyBtn").onclick = () => {
  localStorage.removeItem(KEY_LS);
  el.apiKeyInput.value = "";
  renderKeyState();
  toast("已清除金鑰");
};

/* ---------- 啟動 ---------- */
renderKeyState();
renderAll();
renderKids();
initMap();
setupSearch();

/* ---------- Service Worker ---------- */
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));
}
