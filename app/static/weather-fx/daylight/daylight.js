/*
 * 织梦 · 天气美术：24 小时昼夜光照 / 天空 / 夜空倒影（window.WeatherFX_daylight）
 * pass：reflect（水面映天色、云、星空、银河、月亮、岸上建筑与灯光倒影 + 噪波水波）、
 *       light（乘色光照图：时段色温 + 建筑投影 + 云影 + 灯光照亮；柔光调色；灯光辉光与萤火）。
 * 坐标：scene 与绘制都用 CSS 像素；draw 内部自己 setTransform(dpr)。
 * light pass 用 multiply / soft-light / saturation 混合，要求调用方的 ctx 里已经画了城镇底图。
 * 可选 scene.objectsImage（只含建筑/树/摆件、透明底的画布，CSS 坐标 × scene.objectsScale）：
 *       有它时水面里是岸上实物的真实镜像，没有时退化为建筑暗色剪影。
 * 雨效接口：layer.setDisturb(0..1) 额外打碎倒影；layer.sky() 返回当前天色，给其他模块参考。
 */
(function (root) {
  'use strict';
  function clamp(x, a, b) { return x < a ? a : x > b ? b : x; }
  function sstep(t) { t = clamp(t, 0, 1); return t * t * (3 - 2 * t); }
  function mixc(a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]; }
  function rgb(c, a) {
    var s = Math.round(clamp(c[0], 0, 255)) + ',' + Math.round(clamp(c[1], 0, 255)) + ',' + Math.round(clamp(c[2], 0, 255));
    return a == null ? 'rgb(' + s + ')' : 'rgba(' + s + ',' + clamp(a, 0, 1).toFixed(3) + ')';
  }
  function canvas(w, h) {
    var c = root.document ? root.document.createElement('canvas') : null;
    if (c) { c.width = Math.max(1, Math.ceil(w)); c.height = Math.max(1, Math.ceil(h)); }
    return c;
  }
  function wrap24(x) { x %= 24; return x < 0 ? x + 24 : x; }

  // ---------------------------------------------------------------- 时段关键帧（规范 3.5）
  // [基准, 偏移小时, 乘色 mul, 柔光色 tint, 柔光强度, 天顶, 地平, 云色, 星空可见度, 天黑程度(亮灯)]
  var DAY = [[255, 253, 248], [255, 255, 255], 0, [118, 174, 230], [188, 214, 236], [255, 255, 255], 0, 0];
  var NIGHT = [[80, 94, 152], [60, 70, 150], 0.10, [12, 18, 44], [30, 38, 78], [46, 52, 82], 1, 1];
  var KEYS = [
    ['sr', -2.0, NIGHT],                                                                                                  // 深夜尾
    ['sr', -0.9, [[118, 124, 168], [120, 140, 200], 0.10, [36, 52, 98], [132, 124, 158], [112, 104, 136], 0.45, 0.80]],   // 黎明 灰蓝
    ['sr', -0.25, [[186, 160, 182], [255, 150, 175], 0.16, [84, 112, 172], [244, 168, 162], [240, 176, 180], 0.08, 0.45]], // 黎明 转粉
    ['sr', 0.35, [[255, 198, 150], [255, 150, 70], 0.24, [124, 166, 218], [255, 188, 128], [255, 208, 168], 0, 0.10]],     // 日出 暖橙
    ['sr', 1.5, [[255, 236, 208], [255, 200, 140], 0.10, [134, 186, 234], [208, 224, 236], [255, 244, 228], 0, 0]],        // 上午 微暖
    ['sr', 3.0, DAY],                                                                                                     // 白天 中性
    ['ss', -2.6, DAY],
    ['ss', -1.2, [[255, 226, 172], [255, 182, 84], 0.20, [118, 160, 214], [255, 204, 140], [255, 226, 176], 0, 0]],        // 黄昏 金橙
    ['ss', -0.2, [[244, 160, 122], [255, 112, 64], 0.28, [104, 116, 186], [255, 140, 92], [255, 152, 112], 0, 0.15]],      // 日落 橙红
    ['ss', 0.35, [[150, 122, 166], [196, 98, 172], 0.17, [62, 58, 128], [206, 104, 146], [176, 102, 150], 0.12, 0.50]],    // 日落后 品红紫
    ['ss', 1.1, [[104, 104, 162], [84, 84, 172], 0.14, [24, 30, 72], [68, 60, 118], [60, 60, 96], 0.6, 0.88]],             // 入夜 亮灯
    ['ss', 2.2, NIGHT]                                                                                                    // 夜
  ];
  var MIDNIGHT = [[70, 84, 142], [56, 64, 150], 0.12, [8, 12, 36], [22, 30, 66], [38, 44, 72], 1, 1];

  /** 按 hour 与日出日落连续插值出调色；昼夜过短时按比例压缩关键帧间距，保证单调 */
  function palette(h, sr, ss) {
    sr = clamp(sr == null ? 6 : sr, 1, 12); ss = clamp(ss == null ? 18 : ss, sr + 3, 23);
    var dayLen = ss - sr, f = Math.min(1, dayLen / 7.5), g = Math.min(1, (24 - dayLen) / 6.5);
    var ks = KEYS.map(function (k) {
      var base = k[0] === 'sr' ? sr : ss, o = k[1];
      var sc = (k[0] === 'sr') === (o > 0) ? f : g;
      return { t: base + o * sc, v: k[2] };
    });
    var last = ks[ks.length - 1].t, first = ks[0].t;
    ks.push({ t: (last + first + 24) / 2, v: MIDNIGHT });
    ks.push({ t: first + 24, v: ks[0].v });
    var hh = h; while (hh < first) hh += 24; while (hh >= first + 24) hh -= 24;
    var i = 0; while (i < ks.length - 2 && hh >= ks[i + 1].t) i++;
    var a = ks[i], b = ks[i + 1], s = sstep((hh - a.t) / Math.max(1e-6, b.t - a.t));
    var A = a.v, B = b.v;
    return { mul: mixc(A[0], B[0], s), tint: mixc(A[1], B[1], s), tintA: A[2] + (B[2] - A[2]) * s,
      zen: mixc(A[3], B[3], s), hor: mixc(A[4], B[4], s), cloud: mixc(A[5], B[5], s),
      star: A[6] + (B[6] - A[6]) * s, dark: A[7] + (B[7] - A[7]) * s };
  }

  /** 太阳：白天 elev∈(0,1]（正午 1），theta 为日出→日落的 0..π；夜里 elev<0 */
  function sunOf(h, sr, ss) {
    sr = clamp(sr == null ? 6 : sr, 1, 12); ss = clamp(ss == null ? 18 : ss, sr + 3, 23);
    var dl = ss - sr;
    if (h >= sr && h <= ss) { var th = Math.PI * (h - sr) / dl; return { elev: Math.sin(th), theta: th, up: true }; }
    var nt = wrap24(h - ss) / (24 - dl);
    return { elev: -Math.sin(Math.PI * nt), theta: h > ss ? Math.PI : 0, up: false };
  }
  /** 月亮：新月正午上中天、满月午夜上中天；ha 为时角（小时），alt 为高度代理，illum 为亮面比例 */
  function moonOf(h, phase) {
    var p = ((phase || 0) % 1 + 1) % 1, tr = wrap24(12 + p * 24), ha = wrap24(h - tr + 12) - 12;
    return { p: p, ha: ha, alt: Math.cos(Math.PI * ha / 12), illum: (1 - Math.cos(2 * Math.PI * p)) / 2 };
  }

  // ---------------------------------------------------------------- 天气对调色的修正
  var RAINY = { drizzle: 0.45, rain: 0.75, storm: 1, sleet: 0.7 };
  /** 返回 { desat, mulMix:[色,量], skyGray, starVis, shadow, disturb, cool } */
  function weatherTone(st) {
    var k = st.kind || 'clear', cc = clamp(st.cloud_cover == null ? 0 : st.cloud_cover, 0, 1);
    var it = clamp(st.intensity == null ? 0.5 : st.intensity, 0, 1), fog = clamp(st.fog || 0, 0, 1);
    var o = { desat: cc * 0.18, mulTo: null, mulAmt: 0, skyGray: Math.pow(cc, 1.3) * 0.85, starVis: Math.pow(1 - cc, 1.4),
      shadow: Math.pow(1 - cc, 1.3), disturb: 0, dim: 1 - cc * 0.12, tintTo: null, tintAmt: 0 };
    if (RAINY[k] != null) {
      var r = RAINY[k] * (0.5 + 0.5 * it);
      o.desat = Math.max(o.desat, 0.28 + 0.32 * r); o.mulTo = [170, 184, 204]; o.mulAmt = 0.35 + 0.3 * r;
      o.dim *= 1 - 0.14 * r; o.tintTo = [120, 140, 170]; o.tintAmt = 0.12; o.disturb = 0.25 + 0.75 * r;
    } else if (k === 'snow' || k === 'blizzard') {
      o.desat = Math.max(o.desat, 0.22 + 0.15 * it); o.mulTo = [238, 244, 255]; o.mulAmt = 0.45; o.dim = 1;
      o.tintTo = [200, 220, 255]; o.tintAmt = 0.14; o.disturb = k === 'blizzard' ? 0.3 : 0;
    } else if (k === 'sandstorm') {
      o.desat = 0.3; o.mulTo = [236, 196, 136]; o.mulAmt = 0.4 + 0.35 * it; o.dim *= 1 - 0.1 * it;
      o.tintTo = [220, 160, 90]; o.tintAmt = 0.22 + 0.15 * it; o.skyGray = Math.max(o.skyGray, 0.6);
      o.starVis *= 0.25; o.shadow *= 0.4; o.disturb = 0.2 * it;
    } else if (k === 'fog') {
      o.desat = Math.max(o.desat, 0.3); o.mulTo = [222, 226, 230]; o.mulAmt = 0.3; o.shadow *= 0.3;
      o.starVis *= 0.3; o.skyGray = Math.max(o.skyGray, 0.7);
    } else if (k === 'overcast') { o.desat = Math.max(o.desat, 0.22); o.mulTo = [205, 212, 222]; o.mulAmt = 0.3; }
    if (fog > 0) { o.desat = Math.max(o.desat, fog * 0.35); o.starVis *= 1 - fog * 0.8; o.shadow *= 1 - fog * 0.7; }
    if (st.wind) o.disturb = Math.max(o.disturb, clamp(st.wind.speed || 0, 0, 1) * 0.35);
    return o;
  }

  // ---------------------------------------------------------------- 预烘纹理（只算一次 / 少量重算）
  /** 平铺绘制：tex 在 (ox,oy) 偏移下铺满 [x0,y0,w,h] */
  function drawTiled(g, tex, ox, oy, x0, y0, w, h, sc) {
    sc = sc || 1; var tw = tex.width * sc, th = tex.height * sc;
    var sx = x0 + (((ox % tw) + tw) % tw) - tw, sy = y0 + (((oy % th) + th) % th) - th;
    for (var y = sy; y < y0 + h; y += th) for (var x = sx; x < x0 + w; x += tw) g.drawImage(tex, x, y, tw, th);
  }
  /** 星空：可平铺 512²；密度由平铺 fbm 决定（成团、留空），layer 0 = 暗星底、1..3 = 亮星的三个闪烁相位 */
  function bakeStars(N, seed) {
    var S = 512, dens = N.tile(seed + 5, 128, 4, 3), R = N.rng(seed + 77);
    var base = canvas(S, S), g = base.getContext('2d'), ph = [canvas(S, S), canvas(S, S), canvas(S, S)];
    var pg = ph.map(function (c) { return c.getContext('2d'); });
    var COL = [[255, 255, 255], [205, 220, 255], [255, 236, 210], [190, 210, 255], [255, 218, 190]];
    for (var i = 0; i < 2600; i++) {
      var x = R() * S, y = R() * S, d = dens[((y / 4) | 0) * 128 + ((x / 4) | 0)] / 255;
      if (R() > d * d * 2.2) continue;
      var c = COL[(R() * COL.length) | 0], m = R();
      if (m < 0.86) { // 暗星：1px
        g.fillStyle = rgb(c, 0.25 + R() * 0.55); g.fillRect(x | 0, y | 0, m < 0.5 ? 1 : 1.5, m < 0.5 ? 1 : 1.5);
      } else {        // 亮星：三相位各自随机亮度 → 交叉淡入就是闪烁
        var r = m > 0.985 ? 2.4 : 1.2 + R() * 0.8;
        for (var k = 0; k < 3; k++) {
          var a = 0.25 + R() * 0.75, q = pg[k];
          var grd = q.createRadialGradient(x, y, 0, x, y, r * 2.6);
          grd.addColorStop(0, rgb(c, a)); grd.addColorStop(0.35, rgb(c, a * 0.5)); grd.addColorStop(1, rgb(c, 0));
          q.fillStyle = grd; q.fillRect(x - r * 3, y - r * 3, r * 6, r * 6);
          if (r > 2) { q.fillStyle = rgb(c, a * 0.5); q.fillRect(x - r * 3, y - 0.4, r * 6, 0.8); q.fillRect(x - 0.4, y - r * 3, 0.8, r * 6); }
        }
      }
    }
    return { base: base, ph: ph };
  }
  /** 银河：384×128 低分辨率带，域扭曲 fbm 做星云、第二张扭曲噪波挖暗尘带；绘制时放大旋转 */
  function bakeMilky(N, seed) {
    var Wm = 384, Hm = 128, c = canvas(Wm, Hm), g = c.getContext('2d'), img = g.createImageData(Wm, Hm), d = img.data;
    for (var y = 0; y < Hm; y++) for (var x = 0; x < Wm; x++) {
      var u = x / Wm, v = y / Hm, ctr = 0.5 + (N.fbm2(seed + 3, u * 3, 0.5, 3) - 0.5) * 0.35;
      var dv = (v - ctr) / (0.16 + 0.1 * N.fbm2(seed + 9, u * 4, 2.5, 2));
      var prof = Math.exp(-dv * dv * 2.2) * Math.min(1, Math.min(u, 1 - u) * 5);
      var neb = N.warp2(seed + 11, u * 7, v * 2.4, 2.2, 4), dust = N.warp2(seed + 23, u * 9, v * 3, 1.6, 3);
      var lane = Math.exp(-Math.pow((v - ctr - 0.02) / 0.06, 2)) * N.smoothstep(0.42, 0.7, dust);
      var a = clamp(prof * Math.pow(neb, 1.6) * 1.9 - lane * 0.55 * prof, 0, 1);
      var warm = clamp(1 - Math.abs(dv) * 1.2, 0, 1) * neb, i = (y * Wm + x) * 4;
      d[i] = 190 + 65 * warm; d[i + 1] = 196 + 34 * warm; d[i + 2] = 255 - 40 * warm; d[i + 3] = a * 255;
    }
    g.putImageData(img, 0, 0);
    var R = N.rng(seed + 99); // 银河里额外的密集细星
    for (var j = 0; j < 900; j++) {
      var sx = R() * Wm, sy = Hm * (0.5 + (R() + R() + R() - 1.5) * 0.22);
      g.fillStyle = 'rgba(235,240,255,' + (0.2 + R() * 0.6).toFixed(2) + ')'; g.fillRect(sx, sy, 0.6, 0.6);
    }
    return c;
  }
  /** 水面闪光：平铺 256²，噪波密度控制的短横亮线（波峰反光） */
  function bakeGlints(N, seed) {
    var S = 256, c = canvas(S, S), g = c.getContext('2d'), dens = N.tile(seed + 41, 64, 4, 3), R = N.rng(seed + 43);
    for (var i = 0; i < 1400; i++) {
      var x = R() * S, y = R() * S, dd = dens[((y / 4) | 0) * 64 + ((x / 4) | 0)] / 255;
      if (R() > Math.pow(dd, 3) * 3) continue;
      var w = 1.5 + R() * 5 * dd;
      g.fillStyle = 'rgba(255,255,255,' + (0.35 + R() * 0.65).toFixed(2) + ')'; g.fillRect(x, y, w, R() < 0.7 ? 1 : 1.6);
    }
    return c;
  }
  /** 云：平铺 256² 的域扭曲 fbm 密度（只算一次），按云量重映射成白色 alpha 纹理（云量变化 >0.04 才重映射） */
  function bakeCloudDensity(N, seed) {
    var S = 256, P = 4, out = new Uint8ClampedArray(S * S), a = N.tile(seed + 61, S, P, 5), b = N.tile(seed + 67, 64, 2, 2);
    for (var y = 0; y < S; y++) for (var x = 0; x < S; x++) { // 低频扭曲：用小纹理偏移采样大纹理，保持可平铺
      var q = b[((y >> 2) & 63) * 64 + ((x >> 2) & 63)] / 255 - 0.5;
      var sx = (x + Math.round(q * 40) + S) % S, sy = (y + Math.round(q * 28) + S) % S;
      out[y * S + x] = a[sy * S + sx];
    }
    return { S: S, d: out };
  }
  function remapClouds(dens, cover, c) {
    var S = dens.S; c = c || canvas(S, S); var g = c.getContext('2d'), img = g.createImageData(S, S), d = img.data;
    var th = 0.72 - cover * 0.5, soft = 0.16;
    for (var i = 0; i < S * S; i++) {
      var v = dens.d[i] / 255, a = sstep((v - th) / soft);
      d[i * 4] = d[i * 4 + 1] = d[i * 4 + 2] = 255; d[i * 4 + 3] = a * (0.55 + 0.45 * a) * 255;
    }
    g.putImageData(img, 0, 0); return c;
  }
  /** 月面：64² 圆盘，fbm 做月海暗斑、高频值噪波做细麻点 */
  function bakeMoon(N, seed) {
    var S = 64, c = canvas(S, S), g = c.getContext('2d'), img = g.createImageData(S, S), d = img.data, r = S / 2 - 1;
    for (var y = 0; y < S; y++) for (var x = 0; x < S; x++) {
      var dx = (x + 0.5 - S / 2) / r, dy = (y + 0.5 - S / 2) / r, rr = dx * dx + dy * dy, i = (y * S + x) * 4;
      if (rr > 1) { d[i + 3] = 0; continue; }
      var mar = N.smoothstep(0.5, 0.68, N.warp2(seed + 31, dx * 1.6 + 3, dy * 1.6 + 3, 1.2, 4));
      var pit = N.noise2(seed + 37, x * 0.6, y * 0.6), limb = 0.82 + 0.18 * Math.sqrt(1 - rr);
      var v = (238 - mar * 52 - pit * 16) * limb;
      d[i] = v; d[i + 1] = v * 0.985; d[i + 2] = v * 0.94; d[i + 3] = 255 * clamp((1 - rr) * r * 0.9, 0, 1);
    }
    g.putImageData(img, 0, 0); return c;
  }
  /** 按月相合成月亮（亮面 + 暗面地照）；p<0.5 渐盈亮在右，>0.5 渐亏亮在左 */
  function composeMoon(out, tex, p) {
    var S = tex.width, g = out.getContext('2d'), r = S / 2 - 1, k = Math.cos(2 * Math.PI * p);
    g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, S, S);
    g.globalAlpha = 0.13; g.drawImage(tex, 0, 0); g.globalAlpha = 1; // 地照
    g.save(); g.translate(S / 2, S / 2); if (p > 0.5) g.scale(-1, 1);
    g.beginPath(); g.arc(0, 0, r + 0.5, -Math.PI / 2, Math.PI / 2, false);
    if (k >= 0) g.ellipse(0, 0, Math.max(0.01, k * (r + 0.5)), r + 0.5, 0, Math.PI / 2, -Math.PI / 2, true);
    else g.ellipse(0, 0, -k * (r + 0.5), r + 0.5, 0, Math.PI / 2, Math.PI * 1.5, false);
    g.closePath(); g.clip(); if (p > 0.5) g.scale(-1, 1);
    g.drawImage(tex, -S / 2, -S / 2); g.restore();
    return out;
  }
  /** 一组相邻水格的最大连通块包围盒（月亮、日光反射放在这里） */
  function mainPool(water, cell) {
    if (!water.length) return null;
    var key = function (x, y) { return x + ',' + y; }, set = {}, cells = [];
    // 水格的像素矩形不一定对齐 0 原点（预览裁窗有偏移），按第一格的余数对齐网格，否则包围盒会错位半格、多出一行
    var gx = ((water[0][0] % cell) + cell) % cell, gy = ((water[0][1] % cell) + cell) % cell;
    water.forEach(function (r) {
      for (var y = Math.floor((r[1] - gy) / cell + 1e-6); y < Math.ceil((r[1] + r[3] - gy) / cell - 1e-6); y++)
        for (var x = Math.floor((r[0] - gx) / cell + 1e-6); x < Math.ceil((r[0] + r[2] - gx) / cell - 1e-6); x++) if (!set[key(x, y)]) { set[key(x, y)] = 1; cells.push([x, y]); }
    });
    var seen = {}, best = null;
    cells.forEach(function (c0) {
      if (seen[key(c0[0], c0[1])]) return;
      var st = [c0], n = 0, x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9; seen[key(c0[0], c0[1])] = 1;
      while (st.length) {
        var c = st.pop(); n++; x0 = Math.min(x0, c[0]); y0 = Math.min(y0, c[1]); x1 = Math.max(x1, c[0]); y1 = Math.max(y1, c[1]);
        [[1, 0], [-1, 0], [0, 1], [0, -1]].forEach(function (o) {
          var kx = c[0] + o[0], ky = c[1] + o[1], kk = key(kx, ky); if (set[kk] && !seen[kk]) { seen[kk] = 1; st.push([kx, ky]); }
        });
      }
      if (!best || n > best.n) best = { n: n, x: x0 * cell + gx, y: y0 * cell + gy, w: (x1 - x0 + 1) * cell, h: (y1 - y0 + 1) * cell };
    });
    return best;
  }
  /** 发光点精灵：白芯 + 彩色外晕，64²，按灯种预烘，绘制时只调 globalAlpha / 尺寸 */
  function bakeGlow(c0, c1) {
    var S = 64, c = canvas(S, S), g = c.getContext('2d'), grd = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    grd.addColorStop(0, rgb(c0, 1)); grd.addColorStop(0.18, rgb(c1, 0.75)); grd.addColorStop(0.5, rgb(c1, 0.22)); grd.addColorStop(1, rgb(c1, 0));
    g.fillStyle = grd; g.fillRect(0, 0, S, S); return c;
  }
  var LKIND = { // 光晕半径 / 照地半径 / 颜色
    window: { glow: 16, pool: 46, c0: [255, 236, 190], c1: [255, 170, 80], pc: [255, 196, 128], pa: 0.5 },
    lamp: { glow: 30, pool: 96, c0: [255, 246, 214], c1: [255, 196, 110], pc: [255, 210, 148], pa: 0.78 },
    fire: { glow: 40, pool: 120, c0: [255, 236, 170], c1: [255, 120, 36], pc: [255, 168, 92], pa: 0.9 }
  };

  // ---------------------------------------------------------------- 极光（规范 5.1–5.3）
  var AUR = [[70, 255, 140], [110, 150, 255], [255, 90, 210]]; // hue 0 绿 / 0.5 青紫 / 1 品红
  function auroraCol(h) { h = clamp(+h || 0, 0, 1); return h < 0.5 ? mixc(AUR[0], AUR[1], h * 2) : mixc(AUR[1], AUR[2], (h - 0.5) * 2); }
  /** 射线噪波：平铺 fbm 纹理取两行（横向无缝），一行定射线亮度、一行定射线长度 */
  function bakeAuroraRays(N, seed) {
    var t = N.tile(seed + 71, 256, 24, 3);
    return { a: t.subarray(0, 256), b: t.subarray(128 * 256, 129 * 256) };
  }
  /** 帘幕纹理 256×128（横向可平铺）。倒影里远岸 = 地平线，所以亮边放在 v=0（贴远岸），射线往近处（下）渐淡；
   *  颜色从亮边 c0 渐变到射线末梢 c1（强档多色）。 */
  function bakeAurora(rays, c0, c1, out) {
    var Wt = 256, Ht = 128; out = out || canvas(Wt, Ht);
    var g = out.getContext('2d'), img = g.createImageData(Wt, Ht), d = img.data;
    for (var x = 0; x < Wt; x++) {
      var r = rays.a[x] / 255, rr = clamp(Math.pow(r, 2.2) * 2.2, 0, 1), len = 0.35 + 0.6 * (rays.b[x] / 255);
      for (var y = 0; y < Ht; y++) {
        var v = y / Ht, edge = sstep(v / 0.06), fall = 1 - sstep(v / len);
        var a = edge * Math.pow(fall, 1.4) * (0.3 + 0.9 * rr), col = mixc(c0, c1, sstep((v - 0.08) / (len * 0.8))), i = (y * Wt + x) * 4;
        d[i] = col[0]; d[i + 1] = col[1]; d[i + 2] = col[2]; d[i + 3] = clamp(a, 0, 1) * 255;
      }
    }
    g.putImageData(img, 0, 0); return out;
  }

  // ---------------------------------------------------------------- 图层
  function Layer(opts) {
    opts = opts || {};
    this.N = opts.noise || root.WeatherNoise; this.seed = (opts.seed >>> 0) || 1;
    this.W = 1; this.H = 1; this.dpr = 1; this.t = 0; this.state = null; this.scene = null; this.ext = 0;
    var N = this.N, s = this.seed;
    this.tex = { stars: bakeStars(N, s), milky: bakeMilky(N, s), glints: bakeGlints(N, s), moon: bakeMoon(N, s),
      moonImg: canvas(64, 64), cloud: null, cloudSh: null, cloudCover: -1 };
    this.cloudDens = bakeCloudDensity(N, s); this.moonPhase = -1;
    this.glow = {}; for (var k in LKIND) this.glow[k] = bakeGlow(LKIND[k].c0, LKIND[k].c1);
    this.glowFly = bakeGlow([240, 255, 200], [170, 230, 90]);
    this.lm = canvas(2, 2); this.sh = canvas(2, 2); this.shKey = '';
    this.aurRays = bakeAuroraRays(N, s); this.aurKey = '';
    this.lights = []; this.flies = [];
  }
  var P = Layer.prototype;
  P.resize = function (w, h, dpr) {
    this.W = Math.max(1, w | 0); this.H = Math.max(1, h | 0); this.dpr = dpr || 1;
    this.lm.width = Math.ceil(this.W / 2); this.lm.height = Math.ceil(this.H / 2);
    this.sh.width = this.lm.width; this.sh.height = this.lm.height; this.shKey = '';
  };
  P.setDisturb = function (v) { this.ext = clamp(+v || 0, 0, 1); };
  P.setScene = function (sc) {
    this.scene = sc || null; this.shKey = ''; this.lights = []; this.flies = []; this.pool = null; this.wPath = null; this.refl = null;
    if (!sc) return;
    var N = this.N, s = this.seed, cell = sc.cell || 48, self = this;
    (sc.lights || []).forEach(function (l, i) {
      var r = N.rng(s + 1000 + i * 7919);
      self.lights.push({ x: l.x, y: l.y, kind: LKIND[l.kind] ? l.kind : 'window', i: i,
        thr: l.kind === 'lamp' ? 0.3 + r() * 0.25 : l.kind === 'fire' ? 0.25 + r() * 0.35 : 0.22 + r() * 0.6,
        off: l.kind === 'window' ? 21.5 + r() * 4.5 : 99, ph: r() * 100, lit: 0 });
    });
    var water = sc.water || [];
    if (water.length) {
      var x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9, p = root.Path2D ? new root.Path2D() : null;
      water.forEach(function (r) {
        x0 = Math.min(x0, r[0]); y0 = Math.min(y0, r[1]); x1 = Math.max(x1, r[0] + r[2]); y1 = Math.max(y1, r[1] + r[3]);
        if (p) p.rect(r[0], r[1], r[2], r[3]);
      });
      this.wBox = { x: Math.floor(x0), y: Math.floor(y0), w: Math.ceil(x1 - x0), h: Math.ceil(y1 - y0) };
      this.wPath = p; this.pool = mainPool(water, cell);
      this.refl = canvas(this.wBox.w, this.wBox.h); this.reflObj = canvas(this.wBox.w, this.wBox.h);
      this.mirror = this.bakeMirror(sc);
    }
    var gr = sc.ground && sc.ground.length ? sc.ground : [[0, 0, sc.width || this.W, sc.height || this.H]], R = N.rng(s + 555);
    for (var f = 0; f < 46; f++) {
      var g = gr[(R() * gr.length) | 0];
      this.flies.push({ x: g[0] + R() * g[2], y: g[1] + R() * g[3], ph: R() * 50, sp: 0.4 + R() * 0.8 });
    }
  };
  /** 水面镜像底稿（场景变化时烘一次）：岸上建筑/树以各自底边为镜轴翻转；无 objectsImage 时画暗色剪影 */
  P.bakeMirror = function (sc) {
    var B = this.wBox, c = canvas(B.w, B.h), g = c.getContext('2d'), water = sc.water, img = sc.objectsImage, k = sc.objectsScale || 1;
    (sc.buildings || []).forEach(function (b) {
      var base = b.y + b.h, hit = false;
      water.forEach(function (r) { if (r[0] < b.x + b.w && r[0] + r[2] > b.x && r[1] >= base - 12 && r[1] <= base + 60) hit = true; });
      if (!hit) return;
      g.setTransform(1, 0, 0, -1, -B.x, 2 * base - B.y);
      var top = b.roofY != null ? Math.min(b.roofY, b.y) : b.y;
      if (img) g.drawImage(img, (b.x - 6) * k, top * k, (b.w + 12) * k, (base - top) * k, b.x - 6, top, b.w + 12, base - top);
      else {
        g.fillStyle = 'rgba(40,36,44,0.85)'; g.beginPath();
        g.moveTo(b.x, base); g.lineTo(b.x, top + (base - top) * 0.4); g.lineTo(b.x + b.w / 2, top); g.lineTo(b.x + b.w, top + (base - top) * 0.4); g.lineTo(b.x + b.w, base); g.fill();
      }
    });
    g.setTransform(1, 0, 0, 1, 0, 0);
    // 倒影随离岸距离淡出（乘一道竖向 alpha 渐变）
    return c;
  };
  P.update = function (state, dt) {
    this.state = state || this.state || {}; this.t += Math.max(0, Math.min(0.25, dt || 0));
    var st = this.state, tm = st.time || {}, h = tm.hour == null ? 12 : wrap24(tm.hour);
    this.h = h; this.sr = tm.sunrise == null ? 6 : tm.sunrise; this.ss = tm.sunset == null ? 18 : tm.sunset;
    this.pal = palette(h, this.sr, this.ss); this.sun = sunOf(h, this.sr, this.ss);
    this.moon = moonOf(h, tm.moon_phase == null ? 0.5 : tm.moon_phase); this.tone = weatherTone(st);
    var cc = clamp(st.cloud_cover == null ? 0 : st.cloud_cover, 0, 1);
    if (Math.abs(cc - this.tex.cloudCover) > 0.03 || !this.tex.cloud) this.remap(cc);
    if (Math.abs(this.moon.p - this.moonPhase) > 0.004) { composeMoon(this.tex.moonImg, this.tex.moon, this.moon.p); this.moonPhase = this.moon.p; }
    this.mix(); this.stepLights();
  };
  P.dispose = function () { this.scene = null; this.lights = []; this.flies = []; this.tex = null; this.refl = this.reflObj = this.mirror = this.mask = null; this.cur = null; };
  P.remap = function (cc) {
    var T = this.tex; T.cloud = remapClouds(this.cloudDens, cc, T.cloud); T.cloudCover = cc;
    T.cloudSh = T.cloudSh || canvas(T.cloud.width, T.cloud.height); T.cloudCol = T.cloudCol || canvas(T.cloud.width, T.cloud.height);
    var g = T.cloudSh.getContext('2d'); g.globalCompositeOperation = 'source-over'; g.clearRect(0, 0, 256, 256); g.drawImage(T.cloud, 0, 0);
    g.globalCompositeOperation = 'source-in'; g.fillStyle = 'rgb(84,94,128)'; g.fillRect(0, 0, 256, 256); g.globalCompositeOperation = 'source-over';
  };
  /** 把时段调色与天气修正合成当前帧参数 this.cur */
  P.mix = function () {
    var p = this.pal, o = this.tone, sun = this.sun, i;
    var gray = function (c) { var l = c[0] * 0.3 + c[1] * 0.59 + c[2] * 0.11; return [l, l, l]; };
    var mul = p.mul.slice();
    if (o.mulTo) mul = mixc(mul, [mul[0] * o.mulTo[0] / 255, mul[1] * o.mulTo[1] / 255, mul[2] * o.mulTo[2] / 255], o.mulAmt);
    for (i = 0; i < 3; i++) mul[i] *= o.dim;
    if (o.mulTo && (this.state.kind === 'snow' || this.state.kind === 'blizzard')) mul = mixc(mul, [255, 255, 255], 0.12 * (1 - p.dark)); // 雪天提亮
    var cl = mixc(p.cloud, gray(p.cloud), 0.5 * o.skyGray);
    var zen = mixc(p.zen, mixc(gray(p.zen), cl, 0.6), o.skyGray), hor = mixc(p.hor, mixc(gray(p.hor), cl, 0.6), o.skyGray);
    var rainy = RAINY[this.state.kind] || 0;
    this.cur = { mul: mul, zen: zen, hor: hor, cloud: cl, tint: p.tint, tintA: p.tintA * (1 - 0.6 * o.skyGray),
      wTint: o.tintTo, wTintA: o.tintAmt, desat: o.desat, star: p.star * o.starVis, skyGray: o.skyGray,
      dark: clamp(p.dark + 0.12 * o.skyGray + 0.14 * rainy * (1 - p.dark), 0, 1), night: p.dark,
      shadow: o.shadow * sstep(sun.elev / 0.12) * (sun.up ? 1 : 0), disturb: Math.max(o.disturb, this.ext) };
  };
  P.sky = function () { return this.cur; };
  P.windOff = function (k) {
    var w = (this.state && this.state.wind) || {}, a = (w.dir_deg || 90) * Math.PI / 180, sp = 10 + 70 * clamp(w.speed || 0.2, 0, 1);
    return [Math.sin(a) * sp * this.t * k, -Math.cos(a) * sp * this.t * k];
  };
  /** 水面羽化遮罩 + 倒影底稿缓冲 */
  P.bakeMask = function () {
    var B = this.wBox, c = canvas(B.w, B.h), g = c.getContext('2d');
    g.filter = 'blur(3px)'; g.fillStyle = '#fff'; g.translate(-B.x, -B.y); g.fill(this.wPath); g.filter = 'none';
    return c;
  };
  /** 建筑投影图（半分辨率、透明底，只在太阳方向 / 高度变化一档时重画）。
   *  每栋建筑在小缓冲里画投影并挖掉自己的墙面/屋顶（不吃自己的影子），再并入总图，邻居的影子不受影响。
   *  树用沿投影方向拉长的椭圆，房子用底面矩形沿投影方向扫过的凸包。 */
  P.bakeShadow = function () {
    var sun = this.sun, key = Math.round(sun.theta * 40) + '|' + Math.round(sun.elev * 40);
    if (key === this.shKey) return; this.shKey = key;
    var g = this.sh.getContext('2d'), bs = (this.scene && this.scene.buildings) || [], cx = Math.cos(sun.theta), cy = Math.sin(sun.theta);
    var alt = Math.max(0.05, sun.elev) * 1.13, L = clamp(Math.cos(alt) / Math.sin(alt), 0.25, 1.9);
    var tmp = this.shTmp || (this.shTmp = canvas(160, 160)), tg = tmp.getContext('2d'), COL = 'rgb(118,126,166)';
    g.setTransform(1, 0, 0, 1, 0, 0); g.globalCompositeOperation = 'source-over'; g.filter = 'none'; g.clearRect(0, 0, this.sh.width, this.sh.height);
    bs.forEach(function (b) {
      if (b.wall) return; // 城墙按格给包围盒（比墙体宽得多），逐格投影会在墙外留一圈方块暗斑
      var base = b.y + b.h, dep = b.depth || Math.min(48, b.h * 0.45), hgt = Math.max(8, b.h - dep) * (b.tree ? 0.8 : 0.7);
      var dx = -cx * hgt * L, dy = -cy * hgt * L, pts;
      var bx0 = Math.min(b.x, b.x + dx) - 8, by0 = Math.min(b.y, base - dep + dy) - 8, bx1 = Math.max(b.x + b.w, b.x + b.w + dx) + 8, by1 = base + 8;
      var tw = Math.ceil((bx1 - bx0) * 0.5) + 6, th = Math.ceil((by1 - by0) * 0.5) + 6;
      if (tmp.width < tw || tmp.height < th) { tmp.width = Math.max(tmp.width, tw); tmp.height = Math.max(tmp.height, th); }
      tg.setTransform(1, 0, 0, 1, 0, 0); tg.globalCompositeOperation = 'source-over'; tg.clearRect(0, 0, tw, th);
      tg.setTransform(0.5, 0, 0, 0.5, 3 - bx0 * 0.5, 3 - by0 * 0.5); tg.fillStyle = COL; tg.beginPath();
      if (b.tree) {
        var len = Math.hypot(dx, dy);
        tg.ellipse(b.x + b.w / 2 + dx * 0.5, base - 5 + dy * 0.5, 9 + len * 0.5, b.w * 0.27, Math.atan2(dy, dx), 0, Math.PI * 2);
      } else {
        var x0 = b.x + 3, x1 = b.x + b.w - 3, y0 = base - dep, y1 = base - 2;
        pts = hull([[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0 + dx, y0 + dy], [x1 + dx, y0 + dy], [x1 + dx, y1 + dy], [x0 + dx, y1 + dy]]);
        pts.forEach(function (q, i) { if (i) tg.lineTo(q[0], q[1]); else tg.moveTo(q[0], q[1]); });
      }
      tg.fill();
      tg.globalCompositeOperation = 'destination-out'; tg.beginPath(); // 挖掉自身实物所在区域
      if (b.tree) tg.ellipse(b.x + b.w / 2, b.y + (b.h - dep) * 0.42, b.w * 0.36, (b.h - dep) * 0.46, 0, 0, Math.PI * 2);
      else tg.rect(b.x + 4, b.y, b.w - 8, b.h - dep + 4);
      tg.fill();
      g.drawImage(tmp, 0, 0, tw, th, bx0 * 0.5 - 3, by0 * 0.5 - 3, tw, th);
    });
    // 整张只模糊一次（逐栋 filter 在 300+ 栋时太慢）
    var s2 = this.sh2 || (this.sh2 = canvas(this.sh.width, this.sh.height));
    if (s2.width !== this.sh.width || s2.height !== this.sh.height) { s2.width = this.sh.width; s2.height = this.sh.height; }
    var g2 = s2.getContext('2d'); g2.clearRect(0, 0, s2.width, s2.height); g2.filter = 'blur(3.5px)'; g2.drawImage(this.sh, 0, 0); g2.filter = 'none';
    g.clearRect(0, 0, this.sh.width, this.sh.height); g.drawImage(s2, 0, 0);
    g.setTransform(0.5, 0, 0, 0.5, 0, 0);
    bs.forEach(function (b) { // 背光面：房子包围盒内按太阳水平分量做横向明暗
      if (b.tree) return;
      var gr = g.createLinearGradient(b.x, 0, b.x + b.w, 0), sh = 'rgba(150,150,182,' + (0.5 * Math.abs(cx)).toFixed(3) + ')';
      gr.addColorStop(cx > 0 ? 1 : 0, 'rgba(150,150,182,0)'); gr.addColorStop(0.5, 'rgba(150,150,182,0)'); gr.addColorStop(cx > 0 ? 0 : 1, sh);
      g.fillStyle = gr; g.fillRect(b.x, b.y, b.w, b.h - 4);
    });
    g.setTransform(1, 0, 0, 1, 0, 0);
  };
  function hull(pts) {
    pts = pts.slice().sort(function (a, b) { return a[0] - b[0] || a[1] - b[1]; });
    var cr = function (o, a, b) { return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]); }, lo = [], up = [], i;
    for (i = 0; i < pts.length; i++) { while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], pts[i]) <= 0) lo.pop(); lo.push(pts[i]); }
    for (i = pts.length - 1; i >= 0; i--) { while (up.length >= 2 && cr(up[up.length - 2], up[up.length - 1], pts[i]) <= 0) up.pop(); up.push(pts[i]); }
    return lo.slice(0, -1).concat(up.slice(0, -1));
  }
  P.draw = function (ctx, pass) {
    if (!this.cur || !ctx) return;
    ctx.save(); ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    if (pass === 'reflect') this.drawReflect(ctx);
    else if (pass === 'light') this.drawLight(ctx);
    ctx.restore();
  };
  /** 灯在水里的倒影位置：以所在建筑底边（或灯下地面）为镜轴；落不进水面返回 null */
  P.reflY = function (l) {
    var axis = l.kind === 'window' ? l.y + 24 : l.kind === 'lamp' ? l.y + 30 : l.y + 14;
    (this.scene.buildings || []).forEach(function (b) {
      if (l.x >= b.x && l.x <= b.x + b.w && l.y >= b.y - 4 && l.y <= b.y + b.h) axis = b.y + b.h;
    });
    var ry = 2 * axis - l.y, inW = false;
    (this.scene.water || []).forEach(function (r) { if (l.x >= r[0] && l.x <= r[0] + r[2] && ry >= r[1] && ry <= r[1] + r[3]) inW = true; });
    return inW ? ry : null;
  };
  P.flick = function (l, t) { // 火光 / 灯焰闪烁：两层值噪波
    if (l.kind === 'window') return 0.92 + 0.08 * this.N.noise2(this.seed + 5, t * 0.4 + l.ph, 1);
    var sp = l.kind === 'fire' ? 7 : 2.2, n = this.N.noise2(this.seed + 3, t * sp + l.ph, 0) * 0.65 + this.N.noise2(this.seed + 4, t * sp * 2.7 + l.ph, 2) * 0.35;
    return l.kind === 'fire' ? 0.62 + 0.55 * n : 0.86 + 0.18 * n;
  };
  /** reflect：先把天空/云/星/银河/月/岸上倒影/灯影合成到水面缓冲，再按噪波横向条带位移贴回水面，最后加闪光 */
  P.drawReflect = function (ctx) {
    var B = this.wBox; if (!B || !this.refl) return;
    if (!this.mask) this.mask = this.bakeMask();
    var c = this.cur, g = this.refl.getContext('2d'), T = this.tex, N = this.N, t = this.t, W = this.W, H = this.H, self = this;
    var pool = this.pool || B, sun = this.sun, m = this.moon, hh = wrap24(this.h + 12) - 12;
    g.setTransform(1, 0, 0, 1, 0, 0); g.globalCompositeOperation = 'source-over'; g.globalAlpha = 1; g.clearRect(0, 0, B.w, B.h);
    g.translate(-B.x, -B.y); // 之后按屏幕坐标作画
    // 1. 天色：远岸（上）映近地平，近处（下）映天顶
    var gr = g.createLinearGradient(0, 0, 0, H); gr.addColorStop(0, rgb(c.hor)); gr.addColorStop(0.75, rgb(mixc(c.hor, c.zen, 0.8))); gr.addColorStop(1, rgb(c.zen));
    g.fillStyle = gr; g.fillRect(B.x, B.y, B.w, B.h);
    var glowA = sstep((sun.elev + 0.35) / 0.35) * Math.pow(1 - Math.max(0, sun.elev), 2) * (1 - 0.7 * c.skyGray);
    if (glowA > 0.01) { // 晨昏太阳一侧的暖辉
      var sx = W * (0.5 + 0.5 * Math.cos(sun.theta)), rg = g.createRadialGradient(sx, B.y, 0, sx, B.y, W * 0.55);
      rg.addColorStop(0, rgb(mixc(c.hor, [255, 236, 200], 0.45), 0.85 * glowA)); rg.addColorStop(1, rgb(c.hor, 0));
      g.fillStyle = rg; g.fillRect(B.x, B.y, B.w, B.h);
    }
    // 2. 星空 + 银河（lighter 叠加；随时间缓慢平移 = 天球转动）
    if (c.star > 0.01) {
      g.globalCompositeOperation = 'lighter';
      var ox = -hh * 22, oy = hh * 6;
      g.globalAlpha = c.star; drawTiled(g, T.stars.base, ox, oy, B.x, B.y, B.w, B.h);
      for (var k = 0; k < 3; k++) { g.globalAlpha = c.star * (0.5 + 0.5 * Math.sin(t * 1.6 + k * 2.094)); drawTiled(g, T.stars.ph[k], ox, oy, B.x, B.y, B.w, B.h); }
      g.globalAlpha = c.star * 0.8 * (1 - 0.8 * c.skyGray);
      g.save(); g.translate(pool.x + pool.w * 0.5 - hh * 26, pool.y + pool.h * 0.5); g.rotate(-0.55 + hh * 0.035);
      g.drawImage(T.milky, -W * 0.7, -H * 0.17, W * 1.4, H * 0.34); g.restore();
      g.globalCompositeOperation = 'source-over';
    }
    // 2b. 极光（与星空同在倒影缓冲里，之后吃同一套水波位移）
    this.drawAurora(g, B, pool);
    g.globalAlpha = 1; g.globalCompositeOperation = 'source-over';
    // 3. 云（白天亮、夜里暗，夜里会盖掉星星）
    if (T.cloud && T.cloudCover > 0.02) {
      var cg = T.cloudCol.getContext('2d'); cg.globalCompositeOperation = 'source-over'; cg.clearRect(0, 0, 256, 256); cg.drawImage(T.cloud, 0, 0);
      cg.globalCompositeOperation = 'source-in'; cg.fillStyle = rgb(c.cloud); cg.fillRect(0, 0, 256, 256); cg.globalCompositeOperation = 'source-over';
      var wo = this.windOff(0.5); g.globalAlpha = 0.92; drawTiled(g, T.cloudCol, wo[0], wo[1], B.x, B.y, B.w, B.h, 3);
    }
    // 4. 月亮（按月相；时角决定横向位置，高度决定纵向；白天很淡）
    this.moonPos = null;
    if (m.alt > -0.05) {
      var ma = sstep((m.alt + 0.05) / 0.25) * (1 - 0.85 * c.skyGray) * (0.22 + 0.78 * c.night), mr = 15;
      var mx = pool.x + pool.w * clamp(0.5 - m.ha / 11, 0.1, 0.9), my = pool.y + pool.h * (0.2 + 0.55 * clamp(m.alt, 0, 1));
      this.moonPos = { x: mx, y: my, a: ma * (0.25 + 0.75 * m.illum) };
      g.globalCompositeOperation = 'lighter';
      var mg = g.createRadialGradient(mx, my, mr * 0.6, mx, my, mr * 5.5);
      mg.addColorStop(0, 'rgba(190,205,240,' + (0.42 * ma * m.illum).toFixed(3) + ')'); mg.addColorStop(1, 'rgba(190,205,240,0)');
      g.fillStyle = mg; g.fillRect(mx - mr * 6, my - mr * 6, mr * 12, mr * 12);
      g.globalAlpha = ma; g.drawImage(T.moonImg, mx - mr, my - mr, mr * 2, mr * 2); g.globalAlpha = 1;
      g.globalCompositeOperation = 'source-over';
    }
    // 5. 岸上建筑倒影（镜像底稿；离岸越远越淡由 alpha 控制）
    if (this.mirror) { g.globalAlpha = 0.62 - 0.2 * c.night; g.drawImage(this.mirror, B.x, B.y); g.globalAlpha = 1; }
    // 6. 灯光倒影：竖向拉长的光柱
    g.globalCompositeOperation = 'lighter';
    this.lights.forEach(function (l) {
      if (l.lit < 0.02) return; var ry = l.ry !== undefined ? l.ry : (l.ry = self.reflY(l)); if (ry == null) return;
      var K = LKIND[l.kind], a = l.lit * self.flick(l, t), r = K.glow * 1.1;
      g.globalAlpha = clamp(a * 0.85, 0, 1); g.drawImage(self.glow[l.kind], l.x - r * 0.45, ry - r * 0.9, r * 0.9, r * 3.2);
    });
    g.globalAlpha = 1; g.globalCompositeOperation = 'source-over';
    g.setTransform(1, 0, 0, 1, 0, 0);
    // 7. 横向条带位移（水波）：每条带按两层值噪波 + 正弦平移，扰动越大条带越碎越抖
    var o = this.reflObj.getContext('2d'), dist = c.disturb, sh = dist > 0.5 ? 2 : 3;
    var amp = 1.2 + 9 * dist, amp2 = 0.6 + 4 * dist, sd = this.seed + 201;
    o.setTransform(1, 0, 0, 1, 0, 0); o.globalCompositeOperation = 'source-over'; o.globalAlpha = 1; o.clearRect(0, 0, B.w, B.h);
    for (var y = 0; y < B.h; y += sh) {
      var wy = B.y + y, n = N.noise2(sd, wy * 0.045, t * 0.35) - 0.5, n2 = N.noise2(sd + 1, wy * 0.21, t * (1.2 + 2 * dist)) - 0.5;
      var dx = n * amp * 2 + n2 * amp2 * 2 + Math.sin(wy * 0.37 + t * 2.1) * 0.6;
      o.drawImage(this.refl, 0, y, B.w, sh, dx, y, B.w, sh);
    }
    // 8. 灯光碎影：光柱下方断续短横（噪波决定每段亮不亮，随时间闪动）
    o.globalCompositeOperation = 'lighter';
    this.lights.forEach(function (l) {
      if (l.lit < 0.05) return; var ry = l.ry !== undefined ? l.ry : (l.ry = self.reflY(l)); if (ry == null) return;
      var K = LKIND[l.kind], a = l.lit * self.flick(l, t), len = K.glow * (2.2 + 2 * dist);
      for (var j = 0; j < len; j += 3) {
        var on = N.noise2(sd + 7, (ry + j) * 0.3 + l.ph, t * 2.4 + l.i);
        if (on < 0.48) continue;
        var w = (K.glow * 0.5) * (1 - j / len) * (0.6 + on), xx = l.x - B.x + (N.noise2(sd + 8, j * 0.2 + l.ph, t * 1.7) - 0.5) * (4 + 14 * dist);
        o.fillStyle = rgb(K.c1, a * (on - 0.4) * (1 - j / len) * 1.4); o.fillRect(xx - w / 2, ry - B.y + j, w, 1.4);
      }
    });
    // 9. 月光 / 日光在水面拉出的闪光带
    var gl = this.moonPos && c.night > 0.3 ? { x: this.moonPos.x, y: this.moonPos.y, a: this.moonPos.a * 0.9, col: [210, 222, 255] } :
      sun.up ? { x: pool.x + pool.w * clamp(0.5 - Math.cos(sun.theta) * 0.42, 0.08, 0.92), y: pool.y + pool.h * 0.5, a: 0.55 * c.shadow, col: mixc(c.hor, [255, 250, 235], 0.6) } : null;
    var go = this.windOff(0.25);
    if (gl && gl.a > 0.02) {
      o.save(); o.beginPath(); o.ellipse(gl.x - B.x, gl.y - B.y + 20, 26 + 30 * dist, pool.h * 0.55, 0, 0, Math.PI * 2); o.clip();
      o.globalAlpha = gl.a; drawTiled(o, T.glints, go[0] * 2 + t * 6, t * 3, 0, 0, B.w, B.h); o.restore();
    }
    // 全水面细碎闪光（白天强，夜里弱）
    o.globalAlpha = (0.10 + 0.25 * dist) * (1 - 0.6 * c.night); drawTiled(o, T.glints, go[0], go[1] + t * 2, 0, 0, B.w, B.h, 1.5);
    o.globalAlpha = 1;
    // 10. 遮罩到水面形状，贴回画面
    o.globalCompositeOperation = 'destination-in'; o.drawImage(this.mask, 0, 0); o.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 0.86; ctx.drawImage(this.reflObj, B.x, B.y); ctx.globalAlpha = 1;
  };
  /** 灯的亮度只由时刻决定（截图 / 拖滑杆可复现）：天黑程度越过各自阈值就亮，窗灯过了各自熄灯时刻就灭 */
  P.stepLights = function () {
    var dark = this.cur.dark, hn = wrap24(this.h - 12) + 12, dawn = this.sr + 24;
    this.lights.forEach(function (l) {
      var on = sstep((dark - l.thr) / 0.07);
      if (l.kind === 'window') on *= hn < l.off ? sstep((l.off - hn) / 0.12) : sstep((hn - dawn + 0.9) / 0.3) * (l.ph > 70 ? 1 : 0);
      l.lit = on;
    });
  };
  /** light：半分辨率光照图（时段乘色 × 投影 × 云影 × 晨昏斜向暗角 + 灯光照地）→ multiply；再去饱和、柔光调色、辉光 */
  P.drawLight = function (ctx) {
    var c = this.cur, W = this.W, H = this.H, sun = this.sun, t = this.t, self = this, T = this.tex;
    var g = this.lm.getContext('2d');
    g.setTransform(0.5, 0, 0, 0.5, 0, 0); g.globalCompositeOperation = 'source-over'; g.globalAlpha = 1;
    g.fillStyle = rgb(c.mul); g.fillRect(0, 0, W, H);
    g.globalCompositeOperation = 'multiply';
    if (c.shadow > 0.01) {
      this.bakeShadow();
      var lowSun = 1 - sun.elev;
      g.globalAlpha = c.shadow * (0.55 + 0.25 * lowSun); g.setTransform(1, 0, 0, 1, 0, 0); g.drawImage(this.sh, 0, 0);
      g.setTransform(0.5, 0, 0, 0.5, 0, 0);
      // 晨昏长影：背向太阳一侧整体斜向压暗
      var cx = Math.cos(sun.theta), sx = W * (0.5 + 0.5 * cx), ex = W - sx;
      var lg = g.createLinearGradient(sx, H * 0.1, ex, H * 0.9), sa = 0.32 * Math.pow(lowSun, 2) * c.shadow;
      lg.addColorStop(0, 'rgb(255,255,255)'); lg.addColorStop(1, rgb([255 - 120 * sa, 255 - 110 * sa, 255 - 70 * sa]));
      g.globalAlpha = 1; g.fillStyle = lg; g.fillRect(0, 0, W, H);
    }
    // 云影：同一张云纹理（暗色版）随风掠过地面，云量中等时最明显
    var cc = T.cloudCover;
    if (T.cloudSh && cc > 0.05 && sun.up) {
      var wo = this.windOff(0.5);
      g.globalAlpha = clamp(0.5 * sstep(sun.elev / 0.25) * (1 - Math.pow(cc, 3)) * Math.min(1, cc * 3), 0, 1);
      drawTiled(g, T.cloudSh, wo[0] - 140, wo[1] - 90, 0, 0, W, H, 3);
    }
    // 灯光照地：在光照图上用暖色盖掉夜色（source-over：中心换成暖光，边缘渐回夜色；比 lighter 不发灰）
    g.globalCompositeOperation = 'source-over';
    this.lights.forEach(function (l) {
      if (l.lit < 0.02) return; var K = LKIND[l.kind], a = l.lit * self.flick(l, t) * K.pa * c.dark, r = K.pool;
      var py = l.y + (l.kind === 'window' ? 18 : l.kind === 'lamp' ? 22 : 0);
      g.globalAlpha = clamp(a, 0, 1); g.drawImage(self.glowPool(l.kind), l.x - r, py - r * 0.75, r * 2, r * 1.5);
    });
    g.globalAlpha = 1; g.globalCompositeOperation = 'source-over';
    // 合成到画面
    ctx.globalCompositeOperation = 'multiply'; ctx.drawImage(this.lm, 0, 0, W, H);
    if (c.desat > 0.01) { ctx.globalCompositeOperation = 'saturation'; ctx.fillStyle = 'rgba(128,128,128,' + c.desat.toFixed(3) + ')'; ctx.fillRect(0, 0, W, H); }
    ctx.globalCompositeOperation = 'soft-light';
    if (c.tintA > 0.01) { ctx.fillStyle = rgb(c.tint, c.tintA); ctx.fillRect(0, 0, W, H); }
    if (c.wTint && c.wTintA > 0.01) { ctx.fillStyle = rgb(c.wTint, c.wTintA); ctx.fillRect(0, 0, W, H); }
    var AU = this.auroraParams(), aa = AU.s * AU.vis; // 极光映在地面上的淡色环境光
    if (aa > 0.01) {
      var ac = auroraCol(AU.hue); ctx.fillStyle = rgb(ac, 0.2 * aa); ctx.fillRect(0, 0, W, H);
      ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = rgb([ac[0] * 0.4, ac[1] * 0.4, ac[2] * 0.4], 0.08 * aa); ctx.fillRect(0, 0, W, H);
    }
    // 灯光辉光（lighter）：窗光小、路灯中、火盆大且闪
    ctx.globalCompositeOperation = 'lighter';
    this.lights.forEach(function (l) {
      if (l.lit < 0.02) return; var K = LKIND[l.kind], f = self.flick(l, t), r = K.glow * (l.kind === 'fire' ? 0.85 + 0.3 * f : 1);
      ctx.globalAlpha = clamp(l.lit * f * (0.35 + 0.65 * c.dark), 0, 1);
      ctx.drawImage(self.glow[l.kind], l.x - r, l.y - r, r * 2, r * 2);
    });
    this.drawFlies(ctx);
    ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
  };
  /** 极光参数：state.aurora{strength,hue}；kind='aurora' 而没给 aurora 时用 intensity。只在夜里，云量高 / 雾 / 降水时被遮 */
  P.auroraParams = function () {
    var st = this.state || {}, au = st.aurora || {}, s = au.strength, k = st.kind;
    if (s == null) s = k === 'aurora' ? (st.intensity == null ? 0.6 : st.intensity) : 0;
    s = clamp(+s || 0, 0, 1);
    var cc = clamp(st.cloud_cover || 0, 0, 1), vis = this.cur.night * (1 - sstep((cc - 0.35) / 0.5)) * (1 - 0.8 * clamp(st.fog || 0, 0, 1));
    if (RAINY[k] != null || k === 'snow' || k === 'blizzard' || k === 'sandstorm') vis *= 0.15;
    return { s: s, hue: clamp(au.hue == null ? 0 : +au.hue, 0, 1), vis: vis };
  };
  /** 三档：①远岸一道淡绿光弧 ②帘幕缓慢摆动 ③三层多色帘幕铺满水面。
   *  帘幕按 6px 竖条贴纹理：低频 fbm 决定每条的纵向位置（褶皱摆动）与取样横移（褶子压缩/拉伸），值噪波决定明暗脉动。 */
  P.drawAurora = function (g, B, pool) {
    var A = this.auroraParams(), s = A.s, a0 = A.vis;
    if (s < 0.01 || a0 < 0.02) return;
    var N = this.N, t = this.t, sd = this.seed + 301, c0 = auroraCol(A.hue), multi = sstep((s - 0.6) / 0.25);
    var c1 = mixc(c0, A.hue < 0.5 ? [255, 80, 170] : [120, 220, 255], 0.2 + 0.65 * multi);
    var key = Math.round(A.hue * 40) + '|' + Math.round(multi * 10);
    if (key !== this.aurKey) { this.aurKey = key; this.tex.aur = bakeAurora(this.aurRays, c0, c1, this.tex.aur); }
    g.globalCompositeOperation = 'lighter';
    // ① 光弧：椭圆环渐变，环的下沿落在水面上部
    var arcA = a0 * Math.min(1, s / 0.12) * (1 - 0.45 * multi), R = pool.w * 0.55, ax = pool.x + pool.w * 0.5;
    if (arcA > 0.01) { // 环下沿落在水面上 1/3 处（窄水道也看得到）
      g.save(); g.translate(ax, pool.y - R * 0.76 * 0.35 + pool.h * 0.38); g.scale(1, 0.35);
      var rg = g.createRadialGradient(0, 0, 0, 0, 0, R);
      rg.addColorStop(0, rgb(c0, 0)); rg.addColorStop(0.55, rgb(c0, arcA * 0.18)); rg.addColorStop(0.74, rgb(c0, arcA * 0.85));
      rg.addColorStop(0.86, rgb(c0, arcA * 0.25)); rg.addColorStop(1, rgb(c0, 0));
      g.fillStyle = rg; g.fillRect(-R, -R, R * 2, R * 2); g.restore();
    }
    // ②③ 帘幕
    var curA = a0 * sstep((s - 0.18) / 0.2), tex = this.tex.aur;
    if (curA < 0.01) return;
    // 窄水道（港口一格宽）也要看得到：帘幕尺度固定 170px、亮边贴远岸，超出水面的部分被遮罩裁掉
    var narrow = pool.h < 120, PH = narrow ? 170 : pool.h, py0 = pool.y + pool.h * 0.5 - PH * 0.5;
    if (narrow) { // 窄水面：先铺一层淡极光色底，亮边与射线贴远岸画在水里
      g.globalAlpha = clamp(curA * (0.1 + 0.18 * s), 0, 1); g.fillStyle = rgb(mixc(c0, c1, 0.3 * multi));
      g.fillRect(B.x, B.y, B.w, B.h); py0 = pool.y - PH * 0.12;
    }
    var n = 1 + Math.round(2 * multi), SW = 6, amp = narrow ? 0.22 : 0.5;
    for (var k = 0; k < n; k++) {
      var by = py0 + PH * ((narrow ? 0.02 : 0.1) + (narrow ? 0.1 : 0.24) * k), hgt = PH * (0.35 + 0.4 * s) * (1 - 0.2 * k), ka = curA * (k ? 0.8 * multi : 1);
      for (var x = B.x; x < B.x + B.w; x += SW) {
        var f = N.fbm2(sd + k * 13, x * 0.0016 + k * 7.3, t * 0.025, 3) - 0.5;
        var yy = by + f * PH * amp + Math.sin(x * 0.004 + t * 0.15 + k * 2) * PH * 0.04;
        var pulse = N.noise2(sd + 10 + k, x * 0.006 - t * 0.05, t * 0.08 + k);
        var sx = x * 0.9 + f * 260 + t * (6 + 3 * k) + k * 97; sx = ((sx % 256) + 256) % 256;
        g.globalAlpha = clamp(ka * (0.25 + 1.5 * pulse * pulse), 0, 1);
        g.drawImage(tex, sx, 0, Math.min(SW * 0.9, 256 - sx), 128, x, yy, SW + 0.6, hgt);
      }
    }
  };
  /** 照地光斑：外缘更软的暖色渐变（与辉光分开，避免地面出现白芯） */
  P.glowPool = function (kind) {
    this.pools = this.pools || {};
    if (!this.pools[kind]) {
      var K = LKIND[kind], c = canvas(64, 64), g = c.getContext('2d'), grd = g.createRadialGradient(32, 32, 0, 32, 32, 32);
      grd.addColorStop(0, rgb(K.pc, 1)); grd.addColorStop(0.4, rgb(K.pc, 0.5)); grd.addColorStop(1, rgb(K.pc, 0));
      g.fillStyle = grd; g.fillRect(0, 0, 64, 64); this.pools[kind] = c;
    }
    return this.pools[kind];
  };
  /** 夜里地面萤火：晴朗、无雨的暖季夜晚出现，噪波驱动游走与明灭 */
  P.drawFlies = function (ctx) {
    var c = this.cur, st = this.state, k = st.kind || 'clear';
    var a0 = c.night * (1 - (RAINY[k] ? 1 : 0)) * (k === 'snow' || k === 'blizzard' || k === 'sandstorm' ? 0 : 1) * (st.season === 'winter' ? 0 : 1);
    if (a0 < 0.05) return;
    var N = this.N, s = this.seed, t = this.t, img = this.glowFly;
    this.flies.forEach(function (f, i) {
      var tt = t * 0.12 * f.sp + f.ph, x = f.x + (N.noise2(s + 91, tt, i) - 0.5) * 90, y = f.y + (N.noise2(s + 92, tt, i + 40) - 0.5) * 60;
      var b = N.smoothstep(0.55, 0.8, N.noise2(s + 93, t * 0.7 + f.ph, i * 3));
      if (b < 0.02) return; ctx.globalAlpha = a0 * b; ctx.drawImage(img, x - 7, y - 7, 14, 14);
    });
  };

  root.WeatherFX_daylight = {
    create: function (opts) { return new Layer(opts); },
    palette: palette, sunOf: sunOf, moonOf: moonOf, KEYS: KEYS
  };
})(this);
