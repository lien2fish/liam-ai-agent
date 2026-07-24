"use strict";

/* ---------- 狀態 ---------- */
const LS_KEY = "tripPlanner.v1";
const LS_MAPKEY = "gmapsKey";
const CATS = ["景點", "住宿", "餐飲", "交通", "其他"];
const MODE_LABEL = { DRIVING: "🚗", TRANSIT: "🚆", WALKING: "🚶" };

let state = load();
let addCat = "景點";

function load() {
  try {
    const s = JSON.parse(localStorage.getItem(LS_KEY));
    if (s && s.trips) return s;
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
  return { id: uid(), name, days: 3, travelMode: "DRIVING", budget: null, stops: [] };
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
  "keyInput", "saveKeyBtn", "importFile",
].forEach((k) => (el[k] = $(k)));

/* ---------- 分頁切換 ---------- */
document.querySelectorAll(".tab").forEach((b) =>
  b.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
    document.querySelectorAll(".view").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    $("view-" + b.dataset.tab).classList.add("active");
    if (b.dataset.tab === "budget") renderBudget();
    if (window.google && window.google.maps) setTimeout(fitMap, 60);
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
      return `
      <li class="stop" data-id="${s.id}">
        <div class="stop-head">
          <div class="badge">${i + 1}</div>
          <div class="stop-name">${escapeHtml(s.name)}<div class="stop-cat">${s.category}</div></div>
          <button class="iconbtn up" title="上移">▲</button>
          <button class="iconbtn down" title="下移">▼</button>
          <button class="iconbtn danger del" title="刪除">✕</button>
        </div>
        ${s.address ? `<div class="stop-addr">${escapeHtml(s.address)}</div>` : ""}
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

/* ================= Google Maps ================= */
let map, autocomplete, directionsService, directionsRenderer, markers = [];

function loadMaps(key) {
  if (window.google && window.google.maps) return initMaps();
  const s = document.createElement("script");
  s.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(key)}&libraries=places&loading=async&callback=initMaps&v=weekly`;
  s.async = true;
  s.onerror = () => toast("地圖載入失敗，請檢查金鑰");
  document.head.appendChild(s);
}

window.initMaps = function () {
  map = new google.maps.Map(el.map, {
    center: { lat: 23.9738, lng: 120.9797 }, // 台灣中心
    zoom: 7,
    mapTypeControl: false,
    streetViewControl: false,
    fullscreenControl: false,
    clickableIcons: true,
  });
  directionsService = new google.maps.DirectionsService();
  directionsRenderer = new google.maps.DirectionsRenderer({
    map, suppressMarkers: true, preserveViewport: true,
    polylineOptions: { strokeColor: "#e8804a", strokeWeight: 5, strokeOpacity: 0.85 },
  });

  autocomplete = new google.maps.places.Autocomplete(el.placeSearch, {
    fields: ["name", "geometry", "formatted_address", "place_id"],
  });
  autocomplete.addListener("place_changed", () => {
    const p = autocomplete.getPlace();
    if (!p.geometry) return toast("找不到這個地點");
    addStop({
      name: p.name || p.formatted_address,
      address: p.formatted_address || "",
      lat: p.geometry.location.lat(),
      lng: p.geometry.location.lng(),
      placeId: p.place_id || "",
    });
    el.placeSearch.value = "";
  });

  // 點地圖上的 POI 也能加
  map.addListener("click", (e) => {
    if (!e.placeId) return;
    e.stop();
    new google.maps.places.PlacesService(map).getDetails(
      { placeId: e.placeId, fields: ["name", "geometry", "formatted_address", "place_id"] },
      (p, st) => {
        if (st === "OK" && p.geometry) {
          if (confirm(`加入「${p.name}」到 Day ${state.activeDay}？`))
            addStop({
              name: p.name,
              address: p.formatted_address || "",
              lat: p.geometry.location.lat(),
              lng: p.geometry.location.lng(),
              placeId: p.place_id || "",
            });
        }
      }
    );
  });

  renderMapRoute();
};

function addStop(info) {
  const order = dayStops(state.activeDay).length;
  activeTrip().stops.push({
    id: uid(), day: state.activeDay, order,
    name: info.name, address: info.address, lat: info.lat, lng: info.lng,
    placeId: info.placeId, category: addCat, cost: 0, note: "",
  });
  save();
  renderStops();
  renderMapRoute();
  renderBudget();
  toast(`已加入 ${info.name}`);
}

function clearMarkers() {
  markers.forEach((m) => m.setMap(null));
  markers = [];
}
function fitMap() {
  if (!map) return;
  const stops = dayStops(state.activeDay);
  if (!stops.length) return;
  const b = new google.maps.LatLngBounds();
  stops.forEach((s) => b.extend({ lat: s.lat, lng: s.lng }));
  map.fitBounds(b, 60);
}

function renderMapRoute() {
  if (!map) return;
  clearMarkers();
  if (directionsRenderer) directionsRenderer.set("directions", null);
  const stops = dayStops(state.activeDay);
  document.querySelectorAll(".leg").forEach((l) => (l.textContent = ""));
  if (!stops.length) return;

  stops.forEach((s, i) => {
    markers.push(
      new google.maps.Marker({
        position: { lat: s.lat, lng: s.lng }, map, label: { text: String(i + 1), color: "#fff", fontWeight: "700" },
        title: s.name,
      })
    );
  });
  fitMap();

  if (stops.length < 2) return;
  const mode = activeTrip().travelMode;
  directionsService.route(
    {
      origin: { lat: stops[0].lat, lng: stops[0].lng },
      destination: { lat: stops[stops.length - 1].lat, lng: stops[stops.length - 1].lng },
      waypoints: stops.slice(1, -1).map((s) => ({ location: { lat: s.lat, lng: s.lng }, stopover: true })),
      travelMode: google.maps.TravelMode[mode],
    },
    (res, status) => {
      if (status !== "OK") {
        if (mode === "TRANSIT") toast("此路段查無大眾運輸，改用開車看看");
        return;
      }
      directionsRenderer.setDirections(res);
      const legs = res.routes[0].legs;
      legs.forEach((leg, i) => {
        const node = document.querySelector(`.leg[data-leg="${i}"]`);
        if (node) node.textContent = `${MODE_LABEL[mode]} ${leg.duration.text} · ${leg.distance.text}`;
      });
      const totMin = Math.round(legs.reduce((a, l) => a + l.duration.value, 0) / 60);
      el.dayTotals.textContent += ` · 交通約 ${totMin} 分`;
    }
  );
}

/* ---------- 金鑰設定 ---------- */
el.saveKeyBtn.addEventListener("click", () => {
  const k = el.keyInput.value.trim();
  if (!k) return toast("請貼上金鑰");
  localStorage.setItem(LS_MAPKEY, k);
  toast("金鑰已儲存，載入地圖中…");
  loadMaps(k);
});

/* ---------- 啟動 ---------- */
renderAll();
const savedKey = localStorage.getItem(LS_MAPKEY);
if (savedKey) {
  el.keyInput.value = savedKey;
  loadMaps(savedKey);
} else {
  document.querySelector('.tab[data-tab="settings"]').click();
  el.map.innerHTML = '<div class="empty" style="padding-top:70px">請先到「設定」貼上 Google Maps 金鑰以載入地圖</div>';
}

/* ---------- Service Worker ---------- */
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));
}
