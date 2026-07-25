"use strict";

/* ---------- 狀態 ---------- */
const LS_KEY = "tripPlanner.v1";
const CATS = ["景點", "住宿", "餐飲", "交通", "其他"];
const KEY_LS = "anthropicKey";
const CLAUDE_MODEL = "claude-haiku-4-5"; // 實測 Sonnet 5 貴 11 倍慢 5.7 倍，只多 14pt 定位率，不值得
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
          ${unlocated ? `<button class="iconbtn locate" title="地圖上查不到，手動定位">📍</button>` : ""}
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
  box.innerHTML = `<div class="gen-loading"><div class="spin"></div><p>AI 規劃中… 約 20-30 秒，請勿關閉</p></div>`;
  try {
    renderPlan(await generatePlan(cond));
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
  required: ["title", "summary", "notes", "days"],
  properties: {
    title: { type: "string", description: "行程標題，簡短有畫面感" },
    summary: { type: "string", description: "這趟行程的設計邏輯：為什麼這樣排、動線與體力如何安排，一段話" },
    notes: { type: "string", description: "整趟的注意事項與提醒（帶小孩要準備什麼、時段陷阱等）" },
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
};

function planPrompt(c) {
  const kids = c.kids.length ? c.kids.map((a) => a + "歲").join("、") : "無";
  const extra = [
    c.wants.length ? `偏好類型：${c.wants.join("、")}` : "",
    c.pace ? `步調：${c.pace}` : "",
  ].filter(Boolean).join("\n");
  return `你是熟悉台灣各地親子旅遊的規劃專家。請為以下家庭規劃一趟行程。

目的地：${c.region}
天數：${c.days} 天
大人：${c.adults} 位　小孩：${kids}
交通方式：${c.transport}
單日車程上限：${c.maxDrive} 分鐘
預算：${c.budget ? "NT$" + c.budget : "未設定"}
特殊需求：${c.needs || "無"}
${extra}

【硬條件】
- 依孩子年齡與體力篩選，每個景點都要說明為什麼適合
- 同一天景點之間的車程總和不得超過 ${c.maxDrive} 分鐘
- 交通方式為 ${c.transport}，據此決定景點之間的可行性
- 每天至少安排一個室內景點（indoor=true）作為雨天備案
- 11:30-13:00、17:30-19:00 前後必須有餐飲安排
- 避開常見公休（多數館所週一休）

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

async function generatePlan(cond) {
  const key = apiKey();
  if (!key) { await sleep(900); return mockPlan(cond); } // 未設金鑰＝示範行程

  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-api-key": key,
      "anthropic-version": "2023-06-01",
      "anthropic-dangerous-direct-browser-access": "true",
    },
    body: JSON.stringify({
      model: CLAUDE_MODEL,
      max_tokens: 8000,
      output_config: { format: { type: "json_schema", schema: PLAN_SCHEMA } }, // Haiku 不支援 effort，加了會 400
      messages: [{ role: "user", content: planPrompt(cond) }],
    }),
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    if (res.status === 401) throw new Error("金鑰無效，請到設定重新貼上");
    if (res.status === 429) throw new Error("呼叫太頻繁或額度用完，稍後再試");
    throw new Error((detail && detail.error && detail.error.message) || `伺服器回應 ${res.status}`);
  }

  const data = await res.json();
  if (data.stop_reason === "refusal") throw new Error("AI 婉拒了這個請求，換個描述試試");
  if (data.stop_reason === "max_tokens") throw new Error("行程太長被截斷，請減少天數再試");
  const text = (data.content || []).filter((b) => b.type === "text").map((b) => b.text).join("");
  if (!text) throw new Error("AI 沒有回傳內容，請再試一次");
  return JSON.parse(text);
}

function renderPlan(plan) {
  const box = $("planResults");
  const days = plan.days || [];
  if (!days.length) return (box.innerHTML = `<p class="empty">沒有產生行程，換個條件試試</p>`);
  const spots = days.reduce((a, d) => a + (d.spots || []).length, 0);
  const cost = days.reduce((a, d) => a + (d.spots || []).reduce((x, s) => x + (+s.cost_estimate || 0), 0), 0);
  const heads = (lastCond ? lastCond.adults + lastCond.kids.length : 1) || 1;

  box.innerHTML = `
    <div class="plan-card">
      <h3>${escapeHtml(plan.title || "行程")}</h3>
      <p class="plan-sum">${escapeHtml(plan.summary || "")}</p>
      <div class="plan-meta">
        <span>📅 ${days.length} 天</span>
        <span>📍 ${spots} 個點</span>
        <span>💰 每人估 <b>$${cost.toLocaleString()}</b>${heads > 1 ? `（全家約 $${(cost * heads).toLocaleString()}）` : ""}</span>
      </div>
      <ul class="plan-days">
        ${days.map((d) => `
          <li>
            <div class="d-head">Day ${d.day} · ${escapeHtml(d.theme || "")}</div>
            <div class="d-items">${(d.spots || []).map((s) => `${s.indoor ? "🏠" : "🌤"} ${escapeHtml(s.name)}`).join("　")}</div>
            ${d.rainy_alternative ? `<div class="d-rainy">☔️ 雨天：${escapeHtml(d.rainy_alternative)}</div>` : ""}
          </li>`).join("")}
      </ul>
      ${plan.notes ? `<div class="plan-acc">📝 ${escapeHtml(plan.notes)}</div>` : ""}
      <button class="primary plan-adopt">採用這份行程 →</button>
      <p class="hint">營業時間與費用為 AI 概估，出發前請向店家確認。</p>
    </div>`;
  box.querySelector(".plan-adopt").onclick = () => adoptPlan(plan);
}

async function adoptPlan(plan) {
  const region = (lastCond && lastCond.region) || "旅程";
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
        cost: +s.cost_estimate || 0,
        note: s.reason || "",
        indoor: !!s.indoor,
        minutes: +s.duration_minutes || 0,
        _q: `${s.name}, ${region}`,
      })
    )
  );
  state.trips.push(t);
  state.activeTripId = t.id;
  state.activeDay = 1;
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
function mockPlan(cond) {
  const region = cond.region || "台灣";
  const presets = {
    宜蘭: ["蘭陽博物館", "國立傳統藝術中心", "羅東林業文化園區", "冬山河親水公園"],
    台北: ["國立故宮博物院", "台北市立動物園", "大安森林公園", "北投溫泉博物館"],
    花蓮: ["七星潭", "鯉魚潭", "花蓮觀光糖廠", "石梯坪"],
    台中: ["國立自然科學博物館", "東勢林場", "台中市中山公園", "高美濕地"],
  };
  const key = Object.keys(presets).find((k) => region.includes(k));
  const pool = key ? presets[key] : [`${region}火車站`, `${region}文化中心`, `${region}公園`, `${region}老街`];
  const days = [];
  let idx = 0;
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
    days.push({ day: d, theme: `${region}示範行程第 ${d} 天`, rainy_alternative: "示範資料", spots });
  }
  return { title: `${region}示範行程`, summary: "這是未設定金鑰時的內建示範，不是 AI 規劃結果。", notes: "到設定頁貼上 API 金鑰即可使用真正的 AI 規劃。", days };
}

/* ---------- 金鑰設定 ---------- */
function renderKeyState() {
  const k = apiKey();
  el.keyState.textContent = k
    ? `✅ 已設定（${k.slice(0, 7)}…${k.slice(-4)}），智慧規劃走真 AI`
    : "尚未設定，智慧規劃跑內建示範方案";
}
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
