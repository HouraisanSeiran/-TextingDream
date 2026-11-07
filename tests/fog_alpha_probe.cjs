// 雾的硬约束自检（Node 沙箱里跑真实的 map-fog.js，不依赖浏览器）。
//
// 用法: node fog_alpha_probe.cjs <map-fog.js> <regions.json> [Dpr]
//
// 场景覆盖：三地区 × zoom 1/2 × 单圆/全部圆。
// 注意：zoom（底图在视口里放多大）与 dpr（设备像素比）是两回事，两者都要扫：
//   zoom 只改 rect 的大小，dpr 只改 canvas 分辨率与 scale。
const fs = require('fs');
const vm = require('vm');

const jsPath = process.argv[2];
const regionsPath = process.argv[3];
const DPRS = (process.argv[4] || '1,2').split(',').map(Number);

function mockCanvas(w, h) {
  const state = { data: null };
  const ctx = {
    createImageData(width, height) {
      return { width, height, data: new Uint8ClampedArray(width * height * 4) };
    },
    putImageData(img) { state.data = img.data; },
    clearRect() { state.data = new Uint8ClampedArray(w * h * 4); },
  };
  return { canvas: { width: w, height: h, getContext: () => ctx }, state };
}

const sandbox = { window: {}, Math, Float32Array, Uint8ClampedArray, console };
sandbox.window.window = sandbox.window;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(jsPath, 'utf8'), sandbox, { filename: jsPath });
const fog = sandbox.window.TDMapFog;
if (!fog || typeof fog.paint !== 'function') {
  console.error('TDMapFog 未定义');
  process.exit(2);
}

// W/H 是 CSS 视口；zoom 是底图缩放；dpr 是设备像素比（= 传给 paint 的 scale）。
function run(region, discs, zoom, dpr, W, H) {
  const reveal = region.fog.reveal.slice(0, discs);
  const nw = region.basemap.width, nh = region.basemap.height;
  const s = Math.min(W / nw, H / nh) * zoom;
  const rect = { width: nw * s, height: nh * s, left: (W - nw * s) / 2, top: (H - nh * s) / 2 };
  const { canvas, state } = mockCanvas(Math.round(W * dpr), Math.round(H * dpr));
  const t0 = process.hrtime.bigint();
  fog.paint(canvas, { box: region.basemap.bbox, reveal, cloudDeg: region.fog.cloud_deg, rect, scale: dpr });
  const ms = Number(process.hrtime.bigint() - t0) / 1e6;
  const data = state.data;
  const [lonMin, lonMax, latMin, latMax] = region.basemap.bbox;
  const degX = (lonMax - lonMin) / (rect.width * dpr);
  const degY = (latMax - latMin) / (rect.height * dpr);
  const lon0 = lonMin - rect.left * dpr * degX;
  const lat0 = latMax + rect.top * dpr * degY;
  const clamp = (v, hi) => Math.max(0, Math.min(hi, v));
  const x0 = clamp(Math.ceil(rect.left * dpr), canvas.width);
  const x1 = clamp(Math.floor((rect.left + rect.width) * dpr), canvas.width);
  const y0 = clamp(Math.ceil(rect.top * dpr), canvas.height);
  const y1 = clamp(Math.floor((rect.top + rect.height) * dpr), canvas.height);
  let total = 0, inside = 0, insideCovered = 0, insideMaxAlpha = 0;
  let hardFogged = 0, hardOpaque = 0, softFogged = 0, softOpaque = 0;
  let outsideRect = 0, outsideRectPainted = 0;
  const bad = [];
  for (let y = 0; y < canvas.height; y++) {
    for (let x = 0; x < canvas.width; x++) {
      if (x >= x0 && x < x1 && y >= y0 && y < y1) continue;
      outsideRect++;
      if (data[(y * canvas.width + x) * 4 + 3] !== 0) outsideRectPainted++;
    }
  }
  for (let y = y0; y < y1; y++) {
    const lat = lat0 - y * degY;
    for (let x = x0; x < x1; x++) {
      const a = data[(y * canvas.width + x) * 4 + 3];
      const r = fog.ratioAt(lon0 + x * degX, lat, reveal);
      total++;
      // 硬约束：ratio >= OPAQUE_AT（0.985）必须 alpha=255
      if (r >= fog.OPAQUE_AT) { hardFogged++; if (a === 255) hardOpaque++; }
      // 强约束（更严）：ratio >= 1（揭示圆外）必须 alpha=255
      if (r >= 1.0) {
        softFogged++;
        if (a === 255) softOpaque++;
        else if (bad.length < 4) bad.push({ lon: lon0 + x * degX, lat, ratio: r, alpha: a });
      } else {
        inside++;
        if (a > 0) { insideCovered++; if (a > insideMaxAlpha) insideMaxAlpha = a; }
      }
    }
  }
  return { region: region.title, discs, zoom, dpr, W, H, ms: Math.round(ms), total,
           inside, insideCovered, insideCoveredPct: Math.round(insideCovered / Math.max(1, inside) * 100),
           insideMaxAlpha, hardFogged, hardOpaque, softFogged, softOpaque,
           outsideRect, outsideRectPainted, bad };
}

const regions = JSON.parse(fs.readFileSync(regionsPath, 'utf8'));
const out = [];
for (const region of regions) {
  const all = region.fog.reveal.length;
  for (const discs of [1, all]) {
    for (const zoom of [1, 2]) {
      for (const dpr of DPRS) {
        out.push(run(region, discs, zoom, dpr, 300, 220));
      }
    }
  }
}
console.log(JSON.stringify(out));
