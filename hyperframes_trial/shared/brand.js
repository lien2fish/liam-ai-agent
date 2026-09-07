// 四支短片共用的圖元。幾何沿用 tools/knowledge_short.py，
// 只是從 PIL 逐格繪製改成一次產生 SVG、之後交給 GSAP 動。
// 全部由索引與參數決定，沒有亂數——渲染必須可重現。

// markHostId 省略時行為與原本相同。
// 有滿版照片的場景要把品牌標記放到最上層的空 clip，否則會被照片的遮罩壓暗
// （check 的版面稽核會報 text_occluded）。
function brandChrome(hostId, markHostId) {
  document
    .getElementById(hostId)
    .insertAdjacentHTML("beforeend", '<div class="glow"></div><div class="vignette"></div>');
  document
    .getElementById(markHostId || hostId)
    .insertAdjacentHTML(
      "beforeend",
      '<div id="brand-top">海鮮冷知識</div>' +
        '<div id="brand-bottom">連老闆 · 產地到餐桌</div>'
    );
}

// 六角冰晶：三條交叉主軸 ＋ 兩層分枝
function crystalMarkup(width) {
  const parts = [];
  for (let k = 0; k < 3; k++) {
    const a = (Math.PI / 180) * (60 * k);
    const ca = Math.cos(a), sa = Math.sin(a);
    parts.push(line(-90 * ca, -90 * sa, 90 * ca, 90 * sa));
    for (const s of [0.45, 0.75]) {
      for (const sign of [-1, 1]) {
        const bx = 90 * s * ca * sign, by = 90 * s * sa * sign;
        for (const d of [45, -45]) {
          const ba = a + (Math.PI / 180) * d;
          parts.push(line(bx, by, bx + 19.8 * Math.cos(ba), by + 19.8 * Math.sin(ba)));
        }
      }
    }
  }
  return svg("-100 -100 200 200", group(parts.join(""), width));
}

// 側視魚。身體拉長、尾鰭夠大才看得出是魚。
function fishMarkup(w, h, strokeW) {
  const body =
    '<ellipse cx="' + -0.19 * w + '" cy="0" rx="' + 0.81 * w + '" ry="' + h + '"/>';
  const tail = poly([
    [0.58 * w, 0], [1.04 * w, -0.85 * h], [0.88 * w, 0], [1.04 * w, 0.85 * h],
  ]);
  const dorsal = poly([
    [-0.25 * w, -0.88 * h], [0.10 * w, -1.32 * h], [0.22 * w, -0.80 * h],
  ]);
  const eye =
    '<circle cx="' + -0.66 * w + '" cy="' + -0.22 * h + '" r="13"/>';
  const box = [-1.1 * w, -1.45 * h, 2.3 * w, 2.9 * h].join(" ");
  return svg(box, group(body + tail + dorsal + eye, strokeW));
}

// 魚鰾：魚體上半的一顆空氣囊，聲波真正反射的東西
function bladderMarkup(w, h, strokeW) {
  const cx = (-0.30 * w + 0.20 * w) / 2, cy = (-0.34 * h + 0.02 * h) / 2;
  const rx = (0.20 * w + 0.30 * w) / 2, ry = (0.34 * h + 0.02 * h) / 2;
  const box = [-1.1 * w, -1.45 * h, 2.3 * w, 2.9 * h].join(" ");
  return svg(
    box,
    group('<ellipse cx="' + cx + '" cy="' + cy + '" rx="' + rx + '" ry="' + ry + '"/>', strokeW)
  );
}

// 聲波弧。dir = -1 由船往下打、+1 由魚往上反射。
function arcsMarkup(count, r0, step, rx, dir, strokeW) {
  const parts = [];
  for (let i = 0; i < count; i++) {
    const r = r0 + i * step, ry = r * rx;
    // 只畫朝向 dir 的半弧
    parts.push(
      '<path d="M ' + -r + ' 0 A ' + r + ' ' + ry + ' 0 0 ' + (dir < 0 ? 0 : 1) +
        ' ' + r + ' 0" class="arc-' + i + '"/>'
    );
  }
  const R = r0 + count * step;
  return svg([-R - 10, -R * rx - 10, 2 * R + 20, 2 * R * rx + 20].join(" "),
             group(parts.join(""), strokeW));
}

function line(x1, y1, x2, y2) {
  return '<line x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 + '"/>';
}
function poly(pts) {
  return '<polygon points="' + pts.map((p) => p.join(",")).join(" ") + '"/>';
}
function group(inner, width) {
  return '<g stroke="currentColor" stroke-width="' + width +
    '" fill="none" stroke-linecap="round" stroke-linejoin="round">' + inner + "</g>";
}
function svg(viewBox, inner) {
  return '<svg viewBox="' + viewBox + '" width="100%" height="100%" ' +
    'preserveAspectRatio="xMidYMid meet">' + inner + "</svg>";
}
