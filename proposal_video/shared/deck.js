// 提案影片的圖元。全部由參數決定，沒有亂數——渲染必須可重現。
// 線條風格與 hyperframes_trial/shared/brand.js 一致（currentColor、fill:none），
// 但這裡是鉅鑫管理顧問的識別，不共用那邊的配色與品牌標記。

function brandChrome(hostId, markHostId) {
  document
    .getElementById(hostId)
    .insertAdjacentHTML("beforeend", '<div class="glow"></div><div class="vignette"></div>');
  document
    .getElementById(markHostId || hostId)
    .insertAdjacentHTML(
      "beforeend",
      '<div id="brand-top">鉅鑫管理顧問</div>' +
        '<div id="brand-bottom">A I 導 入 服 務</div>'
    );
}

const G = (inner, w) =>
  '<g stroke="currentColor" stroke-width="' + w +
  '" fill="none" stroke-linecap="round" stroke-linejoin="round">' + inner + "</g>";

const SVG = (box, inner) =>
  '<svg viewBox="' + box + '" preserveAspectRatio="xMidYMid meet">' + inner + "</svg>";

// 手機外框。訊息泡泡另外疊上去，才能各自進場。
function phoneMarkup(w) {
  const W = 190, H = 380, r = 26;
  const body =
    '<rect x="' + -W / 2 + '" y="' + -H / 2 + '" width="' + W + '" height="' + H +
    '" rx="' + r + '"/>';
  const speaker = '<line x1="-26" y1="' + (-H / 2 + 24) + '" x2="26" y2="' + (-H / 2 + 24) + '"/>';
  return SVG("-140 -230 280 460", G(body + speaker, w));
}

// 對話泡泡。dir=-1 對方（左、灰）、+1 自己（右、金）
function bubbleMarkup(w, h, dir, strokeW) {
  const r = 18;
  const tailX = dir < 0 ? -w / 2 : w / 2;
  const tail =
    '<path d="M ' + tailX + ' ' + (h / 2 - 18) + ' L ' + (tailX + dir * 16) + ' ' + (h / 2 + 14) +
    ' L ' + (tailX + dir * -4) + ' ' + (h / 2 - 2) + '"/>';
  const box =
    '<rect x="' + -w / 2 + '" y="' + -h / 2 + '" width="' + w + '" height="' + h +
    '" rx="' + r + '"/>';
  // 泡泡裡的三個點（「對方正在輸入」）。空的泡泡在畫面上很空洞，
  // 有了點才讀得出「有人正在問你事情」。G() 帶 fill:none，所以點要放在它外面。
  const dots = [-1, 0, 1]
    .map((i) =>
      '<circle class="bd bd-' + (i + 1) + '" cx="' + i * 38 +
      '" cy="0" r="10" fill="currentColor" stroke="none"/>')
    .join("");
  const pad = 30;
  return SVG(
    [-w / 2 - pad, -h / 2 - pad, w + 2 * pad, h + 2 * pad].join(" "),
    G(box + tail, strokeW) + dots
  );
}

// 麥克風 ＋ 兩側聲波弧。波弧給 class 方便 GSAP 個別動。
function micMarkup(strokeW) {
  const cap =
    '<rect x="-30" y="-96" width="60" height="120" rx="30"/>' +
    '<path d="M -54 -4 A 54 54 0 0 0 54 -4"/>' +
    '<line x1="0" y1="50" x2="0" y2="86"/>' +
    '<line x1="-34" y1="86" x2="34" y2="86"/>';
  const waves = [1, 2, 3]
    .map((i) => {
      const r = 52 + i * 34;
      return (
        '<path class="mw mw-' + i + '" d="M ' + -r + ' ' + -r * 0.72 +
        ' A ' + r + ' ' + r + ' 0 0 0 ' + -r + ' ' + r * 0.72 + '"/>' +
        '<path class="mw mw-' + i + '" d="M ' + r + ' ' + -r * 0.72 +
        ' A ' + r + ' ' + r + ' 0 0 1 ' + r + ' ' + r * 0.72 + '"/>'
      );
    })
    .join("");
  return SVG("-200 -160 400 300", G(cap, strokeW) + G(waves, strokeW - 1));
}

// 資料庫堆疊。由下往上長，代表一年累積下來的知識。
function stackMarkup(n, strokeW) {
  const rx = 118, ry = 30, gap = 52;
  const parts = [];
  for (let i = 0; i < n; i++) {
    const cy = (n - 1 - i) * gap;
    parts.push(
      '<g class="sl sl-' + i + '">' +
        '<ellipse cx="0" cy="' + cy + '" rx="' + rx + '" ry="' + ry + '"/>' +
        '<path d="M ' + -rx + ' ' + cy + ' L ' + -rx + ' ' + (cy - gap) + '"/>' +
        '<path d="M ' + rx + ' ' + cy + ' L ' + rx + ' ' + (cy - gap) + '"/>' +
      "</g>"
    );
  }
  const H = (n - 1) * gap;
  return SVG([-rx - 30, -gap - ry - 20, 2 * rx + 60, H + gap + 2 * ry + 40].join(" "),
             G(parts.join(""), strokeW));
}

// 中心節點 ＋ n 個衛星（品牌／自動排程）。連線與節點各自給 class。
function nodesMarkup(n, strokeW) {
  const R = 150;
  const edges = [], dots = [];
  for (let i = 0; i < n; i++) {
    const a = (Math.PI * 2 * i) / n - Math.PI / 2;
    const x = R * Math.cos(a), y = R * Math.sin(a);
    edges.push('<line class="ne ne-' + i + '" x1="0" y1="0" x2="' + x + '" y2="' + y + '"/>');
    dots.push('<circle class="nd nd-' + i + '" cx="' + x + '" cy="' + y + '" r="26"/>');
  }
  const hub = '<circle class="hub" cx="0" cy="0" r="42"/>';
  return SVG("-220 -220 440 440", G(edges.join("") + hub + dots.join(""), strokeW));
}

// 打勾。用 pathLength 固定成 1000，dasharray 就不必量實際長度。
function checkMarkup(strokeW) {
  return SVG(
    "-90 -90 180 180",
    '<g fill="none" stroke="currentColor" stroke-width="' + strokeW +
      '" stroke-linecap="round" stroke-linejoin="round">' +
      '<circle cx="0" cy="0" r="70"/>' +
      '<path class="ck" d="M -32 2 L -8 30 L 34 -26" pathLength="1000" ' +
      'stroke-dasharray="1000" stroke-dashoffset="1000"/>' +
      "</g>"
  );
}

// 一張紙／空白筆記，代表沒有被記下來的東西
function sheetMarkup(strokeW) {
  const W = 190, H = 250;
  const body =
    '<path d="M ' + -W / 2 + ' ' + -H / 2 + ' L ' + (W / 2 - 46) + ' ' + -H / 2 +
    ' L ' + W / 2 + ' ' + (-H / 2 + 46) + ' L ' + W / 2 + ' ' + H / 2 +
    ' L ' + -W / 2 + ' ' + H / 2 + ' Z"/>' +
    '<path d="M ' + (W / 2 - 46) + ' ' + -H / 2 + ' L ' + (W / 2 - 46) + ' ' + (-H / 2 + 46) +
    ' L ' + W / 2 + ' ' + (-H / 2 + 46) + '"/>';
  const rules = [0, 1, 2]
    .map((i) => '<line class="sr sr-' + i + '" x1="-58" y1="' + (-12 + i * 44) +
                '" x2="58" y2="' + (-12 + i * 44) + '"/>')
    .join("");
  return SVG("-130 -160 260 320", G(body, strokeW) + G(rules, strokeW - 1));
}
