/*
 * 织梦 · 天气美术：冰冻天气（冻雨 / 雨凇、霰、霜、雾凇）
 * window.WeatherFX_ice；接口见 docs/weather-spec.md 第 3.1 节与第 8 节。
 * pass：ground（冰壳、霜、霰积层、雾凇毛边、冰凌、亮冰点）、precip（冻雨丝、霰粒）、fog（雾凇淡雾）。
 * 读 kind = freezing_rain / graupel / frost / rime，也读 ground.glaze / frost / rime（晴天清晨只有 frost 累积量也会画霜）。
 * 调用方负责 ctx.setTransform(dpr,0,0,dpr,0,0)，本模块一律按 CSS 像素坐标作画。
 */
(function (root) {
  'use strict';
  var KINDS = { freezing_rain: 1, graupel: 1, frost: 1, rime: 1 };
  var BAKE = 2;           // 地面遮罩降采样倍数
  var TS = 256;           // 预烘噪波边长
  var OPA = 110;          // occluder alpha 阈值

  function clamp01(x) { return x < 0 ? 0 : x > 1 ? 1 : x; }
  function sstep(a, b, x) { var t = clamp01((x - a) / (b - a)); return t * t * (3 - 2 * t); }
  function canvas(w, h) {
    var c = document.createElement('canvas');
    c.width = Math.max(1, Math.ceil(w)); c.height = Math.max(1, Math.ceil(h));
    return c;
  }
  function windVec(st) {
    var w = (st && st.wind) || {}, a = (w.dir_deg || 0) * Math.PI / 180;
    return { x: Math.sin(a), y: -Math.cos(a), s: clamp01(w.speed || 0), g: clamp01(w.gust || 0) };
  }
  /** 双线性采样可平铺 Uint8 噪波，返回 [0,1] */
  function sampler(tex, size) {
    return function (u, v) {
      u = ((u % size) + size) % size; v = ((v % size) + size) % size;
      var x0 = u | 0, y0 = v | 0, fx = u - x0, fy = v - y0, x1 = (x0 + 1) % size, y1 = (y0 + 1) % size;
      var a = tex[y0 * size + x0], b = tex[y0 * size + x1], c = tex[y1 * size + x0], d = tex[y1 * size + x1];
      return ((a + (b - a) * fx) * (1 - fy) + (c + (d - c) * fx) * fy) / 255;
    };
  }
  /** 霰粒：不透明白色小圆粒，边缘一圈淡蓝灰，左上一点高光 */
  function pelletSprite(r) {
    var s = Math.ceil(r * 2 + 3), c = canvas(s, s), g = c.getContext('2d'), m = s / 2;
    g.fillStyle = 'rgba(70,90,115,0.35)'; g.beginPath(); g.arc(m + 0.5, m + 0.7, r + 0.5, 0, Math.PI * 2); g.fill();
    var gr = g.createRadialGradient(m - r * 0.35, m - r * 0.35, 0, m, m, r);
    gr.addColorStop(0, '#ffffff'); gr.addColorStop(0.7, '#f1f4f8'); gr.addColorStop(1, '#d3dbe6');
    g.fillStyle = gr; g.beginPath(); g.arc(m, m, r, 0, Math.PI * 2); g.fill();
    return c;
  }
  /** 亮冰点：中心亮核 + 十字光芒 */
  function glintSprite(r) {
    var s = Math.ceil(r * 2 + 2), c = canvas(s, s), g = c.getContext('2d'), m = s / 2;
    var gr = g.createRadialGradient(m, m, 0, m, m, r * 0.45);
    gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(1, 'rgba(220,240,255,0)');
    g.fillStyle = gr; g.fillRect(0, 0, s, s);
    g.strokeStyle = 'rgba(240,250,255,0.85)'; g.lineWidth = 0.8;
    g.beginPath(); g.moveTo(m - r, m); g.lineTo(m + r, m); g.moveTo(m, m - r); g.lineTo(m, m + r); g.stroke();
    return c;
  }
  /** 一张可平铺 RGBA 纹理：fn(v) → [r,g,b,a]，v 来自 WeatherNoise.tile */
  function tileCanvas(N, seed, size, period, oct, fn) {
    var t = N.tile(seed, size, period, oct), c = canvas(size, size), g = c.getContext('2d');
    var img = g.createImageData(size, size), d = img.data;
    for (var i = 0, n = size * size; i < n; i++) {
      var px = fn(t[i] / 255);
      d[i * 4] = px[0]; d[i * 4 + 1] = px[1]; d[i * 4 + 2] = px[2]; d[i * 4 + 3] = px[3];
    }
    g.putImageData(img, 0, 0);
    return c;
  }
  function drawTiled(ctx, tex, scale, ox, oy, W, H) {
    var s = tex.width * scale, x0 = -(((ox % s) + s) % s), y0 = -(((oy % s) + s) % s);
    for (var y = y0; y < H; y += s) for (var x = x0; x < W; x += s) ctx.drawImage(tex, x, y, s + 0.5, s + 0.5);
  }

  function create(opts) {
    opts = opts || {};
    var N = opts.noise || root.WeatherNoise;
    if (!N) throw new Error('WeatherFX_ice 需要 WeatherNoise');
    var L = {
      N: N, seed: (opts.seed >>> 0) || 1, W: 1, H: 1, dpr: 1, t: 0, dt: 0, state: null, scene: null, sceneId: 0,
      wind: { x: 0, y: 1, s: 0, g: 0 }, gust: 1, active: 0, amt: null, bakedKey: '', empty: true,
      occ: null, rain: [], pel: [], spl: [], glints: [], tex: {}, spr: {}, gc: null
    };
    initTextures(L);
    initPools(L);
    return {
      resize: function (w, h, dpr) { L.W = Math.max(1, w | 0); L.H = Math.max(1, h | 0); L.dpr = dpr || 1; L.sceneId++; },
      setScene: function (sc) { L.scene = sc || null; L.sceneId++; },
      update: function (st, dt) { update(L, st || {}, Math.min(0.1, Math.max(0, dt || 0))); },
      draw: function (ctx, pass) {
        if (!L.state || !L.amt) return;
        if (pass === 'ground') drawGround(L, ctx);
        else if (pass === 'precip') drawPrecip(L, ctx);
        else if (pass === 'fog') drawFog(L, ctx);
      },
      dispose: function () { L.rain = []; L.pel = []; L.spl = []; L.glints = []; L.occ = null; L.gc = null; L.scene = null; L.tex = {}; },
      _debug: L
    };
  }
  // ---------------------------------------------------------------- 预烘纹理（create 时一次）
  function initTextures(L) {
    var N = L.N, s = L.seed;
    L.nBig = sampler(N.tile(s + 11, TS, 4, 4), TS);      // 大块斑块：结冰 / 霜 / 霰的覆盖起伏
    L.nMid = sampler(N.tile(s + 23, TS, 16, 3), TS);     // 中频：霜花脉络、冰面高光条
    L.nFine = sampler(N.tile(s + 29, TS, 48, 2), TS);    // 细颗粒
    L.nWx = sampler(N.tile(s + 37, TS, 6, 3), TS);       // 域扭曲偏移
    L.nWy = sampler(N.tile(s + 41, TS, 6, 3), TS);
    L.tGrain = N.tile(s + 31, TS, 128, 1);               // 近逐像素颗粒（直接按 &255 取）：霜晶、雾凇毛刺
    L.tPel = N.tile(s + 33, TS, 80, 1);                  // 霰粒点阵
    L.tex.fogA = tileCanvas(N, s + 51, 128, 4, 5, function (v) { return [226, 236, 246, Math.round(sstep(0.3, 0.85, v) * 255)]; });
    L.tex.fogB = tileCanvas(N, s + 67, 128, 8, 4, function (v) { return [238, 244, 252, Math.round(sstep(0.45, 0.9, v) * 220)]; });
    L.spr.pel = [pelletSprite(1.25), pelletSprite(1.75), pelletSprite(2.35)];
    L.spr.glint = glintSprite(4.5); L.spr.glintS = glintSprite(2.6);
  }
  function grainAt(L, x, y) { return L.tGrain[((y | 0) & 255) * 256 + ((x | 0) & 255)] / 255; }
  function pelAt(L, x, y) { return L.tPel[((y | 0) & 255) * 256 + ((x | 0) & 255)] / 255; }
  function initPools(L) {
    var r = L.N.rng(L.seed + 5), i;
    for (i = 0; i < 1100; i++) L.rain.push({ x: r(), y: r(), v: 0.75 + r() * 0.5, l: 0.6 + r() * 0.7, z: r(), init: false });
    for (i = 0; i < 900; i++) L.pel.push({ x: r(), y: r(), k: r(), s: r(), st: 0, vy: 0, land: 0, b: 0, life: 0, a: 1, init: false });
  }
  /** 太阳在地平线上的程度 0..1（日出后 1.5 小时到满，日落前 1 小时开始回落） */
  function sunUp(time) {
    var t = time || {}, h = t.hour == null ? 12 : t.hour, sr = t.sunrise == null ? 6 : t.sunrise, ss = t.sunset == null ? 18 : t.sunset;
    return sstep(sr - 0.2, sr + 1.5, h) * (1 - sstep(ss - 1, ss + 0.3, h));
  }
  // ---------------------------------------------------------------- 推进
  function update(L, st, dt) {
    var kind = st.kind || 'clear', it = clamp01(st.intensity || 0), g = st.ground || {}, pr = st.precipitation || {};
    L.state = st; L.t += dt; L.dt = dt; L.wind = windVec(st);
    L.gust = 1 + (L.N.fbm2(L.seed + 3, L.t * 0.35, 0.5, 3) - 0.5) * 1.6 * (0.2 + L.wind.g);
    // 累积量优先读 ground.*；缺省时用当前 kind 的强度近似
    function gv(f, k) { var v = g[f]; return v != null ? clamp01(+v || 0) : kind === k ? it : 0; }
    var rate = pr.rate != null ? clamp01(pr.rate) : it;
    var a = L.amt = {
      kind: kind, it: it,
      glaze: gv('glaze', 'freezing_rain'), frost: gv('frost', 'frost'), rime: gv('rime', 'rime'),
      // ground.graupel 为正式累积量；缺字段时仅为旧预览按强度近似。
      pel: g.graupel != null ? clamp01(+g.graupel || 0) : kind === 'graupel' ? clamp01(0.06 + it * 0.94) : 0,
      rain: kind === 'freezing_rain' || pr.type === 'freezing_rain' ? rate : 0,
      hail: kind === 'graupel' || pr.type === 'graupel' ? rate : 0,
      fog: kind === 'rime' ? Math.max(clamp01(st.fog || 0), 0.12 + 0.4 * it) : 0,
      sun: sunUp(st.time)
    };
    var want = a.rain + a.hail > 0 ? 1 : 0;
    L.active += (want - L.active) * Math.min(1, dt * 3);
    var occ = occInfo(L), q = function (v) { return Math.round(v * 100); };
    var key = [L.sceneId, occ.real ? 1 : 0, q(a.glaze), q(a.frost), q(a.rime), q(a.pel), Math.round(a.sun * 10), L.W, L.H, L.dpr].join(',');
    L.empty = a.glaze + a.frost + a.rime + a.pel < 0.005;
    if (!L.empty && key !== L.bakedKey) { bake(L, occ); L.bakedKey = key; }
    updRain(L, dt);
    updPel(L, dt);
  }

  // ---------------------------------------------------------------- 场景辅助：occluder 与低分辨率场
  /** 前景剪影：有 scene.occluder 就用它（带颜色，可判断树叶 / 屋檐）；没有就用建筑包围盒（roofY 以下）近似 */
  function occInfo(L) {
    if (L.occ && L.occ.id === L.sceneId) return L.occ;
    var sc = L.scene, o = sc && sc.occluder, real = !!(o && o.width), W = L.W, H = L.H;
    var c = canvas(W, H), g = c.getContext('2d');
    if (real) g.drawImage(o, 0, 0, W, H);
    else {
      g.fillStyle = '#808080';
      ((sc && sc.buildings) || []).forEach(function (b) { var ry = b.roofY == null ? b.y : b.roofY; g.fillRect(b.x, ry, b.w, b.y + b.h - ry); });
    }
    var D = null;
    try { D = g.getImageData(0, 0, W, H).data; } catch (e) { D = null; }
    L.occ = { id: L.sceneId, real: real && !!D, c: c, D: D };
    return L.occ;
  }
  /** 在 1/4 分辨率画布上画一组形状并取 alpha（可带模糊），得到平滑的 0..255 场 */
  function lowField(W, H, blur, paint) {
    var f = 4, w = Math.ceil(W / f), h = Math.ceil(H / f), c = canvas(w, h), g = c.getContext('2d');
    if (blur) g.filter = 'blur(' + blur + 'px)';
    g.setTransform(1 / f, 0, 0, 1 / f, 0, 0); g.fillStyle = '#fff';
    paint(g);
    var d = g.getImageData(0, 0, w, h).data, a = new Uint8Array(w * h);
    for (var i = 0; i < a.length; i++) a[i] = d[i * 4 + 3];
    return { a: a, w: w, h: h, at: function (x, y) {
      var i = Math.min(w - 1, Math.max(0, (x / f) | 0)), j = Math.min(h - 1, Math.max(0, (y / f) | 0)); return a[j * w + i] / 255; } };
  }
  function rectsPaint(rs) { return function (g) { rs.forEach(function (r) { g.fillRect(r[0], r[1], r[2], r[3]); }); }; }
  /** 取分位数阈值：让 frac 比例的有效像素超过阈值（累积量直接对应覆盖面积） */
  function quantile(hist, cnt, frac) {
    if (frac <= 0) return 2;
    for (var k = 255, acc = 0; k >= 0; k--) { acc += hist[k]; if (acc >= frac * cnt) return k / 255; }
    return 0;
  }
  function hashU(L, x, y, s) { return L.N.hash32((L.seed + s) ^ Math.imul(x | 0, 374761393) ^ Math.imul(y | 0, 668265263)) / 4294967296; }
  // ---------------------------------------------------------------- 烘焙（只在累积量 / 场景 / 尺寸变化时）
  function bake(L, occ) {
    L.glints = [];
    bakeGround(L, occ);
    bakeEdges(L, occ);
    var W = L.W, H = L.H, dpr = L.dpr, cw = Math.ceil(W * dpr), ch = Math.ceil(H * dpr);
    if (!L.gc || L.gc.width !== cw || L.gc.height !== ch) L.gc = canvas(cw, ch);
    var g = L.gc.getContext('2d');
    g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, cw, ch); g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.imageSmoothingEnabled = true;
    g.drawImage(L.mask, 0, 0, L.mask.width * BAKE, L.mask.height * BAKE);
    drawPelDots(L, g, L.pelDots);
    g.globalCompositeOperation = 'destination-out'; g.drawImage(occ.c, 0, 0, W, H);
    g.globalCompositeOperation = 'source-over';
    if (L.edge) g.drawImage(L.edge, 0, 0, W, H);
    drawPelDots(L, g, L.roofDots);
  }
  /** 把烤好的霰粒落点（x, y, r 三元组）用圆粒精灵画上去 */
  function drawPelDots(L, g, P) {
    if (!P || !P.length) return;
    var spr = L.spr.pel;
    for (var i = 0; i < P.length; i += 3) {
      var im = spr[P[i + 2] < 0.55 ? 0 : P[i + 2] < 0.88 ? 1 : 2];
      g.drawImage(im, P[i] - im.width / 2, P[i + 1] - im.height / 2);
    }
  }
  /** 地面层（1/2 分辨率）：冰壳、霜、霰积层三张势场，各自按分位数取阈值后叠合 */
  function bakeGround(L, occ) {
    var a = L.amt, W = L.W, H = L.H, sc = L.scene || {}, D = occ.D;
    var mw = Math.ceil(W / BAKE), mh = Math.ceil(H / BAKE), n = mw * mh, k, i, j;
    if (!L.mask || L.mask.width !== mw || L.mask.height !== mh) L.mask = canvas(mw, mh);
    if (!L.vF || L.vF.length !== n) { L.vF = new Float32Array(n); L.vG = new Float32Array(n); L.vP = new Float32Array(n); L.aux = new Float32Array(n * 3); }
    var road = lowField(W, H, 3, rectsPaint(sc.ground || []));
    var water = lowField(W, H, 0, rectsPaint(sc.water || []));
    // 背光：前景剪影模糊后向上（北）偏移，建筑北侧与周围一圈霜更厚
    var shade = lowField(W, H, 5, function (g) { g.drawImage(occ.c, 0, -10, W, H); g.drawImage(occ.c, 0, 0, W, H); });
    var fr = Math.max(a.frost, a.rime * 0.45), sun = a.sun, VF = L.vF, VG = L.vG, VP = L.vP, X3 = L.aux;
    var hF = new Uint32Array(256), hG = new Uint32Array(256), hP = new Uint32Array(256), cnt = 0, s = 0.55 * BAKE / 3;
    for (j = 0; j < mh; j++) for (i = 0; i < mw; i++) {
      k = j * mw + i;
      var X = i * BAKE, Y = j * BAKE;
      if (water.at(X, Y) > 0.5 || (D && D[(Y * W + X) * 4 + 3] > 200)) { VF[k] = VG[k] = VP[k] = -1; continue; }
      var u = i * s, v = j * s, du = (L.nWx(u * 0.7, v * 0.7) - 0.5) * 34, dv = (L.nWy(u * 0.7, v * 0.7) - 0.5) * 34;
      var big = L.nBig(u + du, v + dv), mid = L.nMid(u * 1.3 + du * 0.5, v * 1.3 + dv * 0.5), fine = L.nFine(u * 2, v * 2);
      var rd = road.at(X + du * 2, Y + dv * 2), sh = shade.at(X, Y);
      VF[k] = big * 0.42 + mid * 0.22 + fine * 0.14 + sh * (0.3 + 0.45 * sun) - rd * 0.28 - sun * 0.22 * (1 - sh);
      VG[k] = big * 0.5 + mid * 0.3 + fine * 0.2 + rd * 0.12;
      VP[k] = big * 0.6 + mid * 0.25 + fine * 0.15 - rd * 0.18;
      X3[k * 3] = rd; X3[k * 3 + 1] = sh; X3[k * 3 + 2] = mid;
      hF[Math.max(0, Math.min(255, VF[k] * 255 | 0))]++; hG[Math.max(0, Math.min(255, VG[k] * 255 | 0))]++;
      hP[Math.max(0, Math.min(255, VP[k] * 255 | 0))]++; cnt++;
    }
    var thF = quantile(hF, cnt, fr > 0.005 ? Math.min(0.97, Math.pow(fr, 0.85)) : 0);
    var thG = quantile(hG, cnt, a.glaze > 0.005 ? Math.min(0.97, 0.12 + 0.88 * a.glaze) : 0);
    var thP = quantile(hP, cnt, a.pel > 0.005 ? Math.min(0.96, Math.pow(a.pel, 0.9)) : 0);
    L.groundTh = { F: thF, G: thG, P: thP, mw: mw, mh: mh, s: s };
    var g = L.mask.getContext('2d'), img = g.createImageData(mw, mh), d = img.data;
    var sheetF = sstep(0.25, 0.85, fr), sheetP = sstep(0.3, 0.9, a.pel), gl = a.glaze, sunF = 1 - 0.55 * sun;
    for (k = 0; k < n; k++) {
      var o = k * 4; d[o + 3] = 0;
      if (VF[k] < 0) continue;
      i = k % mw; j = (k / mw) | 0;
      var rd2 = X3[k * 3], sh2 = X3[k * 3 + 1], md = X3[k * 3 + 2];
      var R = 0, G = 0, B = 0, A = 0;
      // 1) 冰壳：冷色透明层 + 沿中频噪波等值线的高光条；路面（湿处）更亮
      var cg = VG[k] >= thG ? sstep(thG, thG + 0.05, VG[k]) : 0;
      if (cg > 0) {
        var streak = sstep(0.13, 0, Math.abs(md - 0.55)) * (0.15 + 0.85 * rd2);
        var ag = cg * (0.14 + 0.24 * gl + 0.12 * rd2) + streak * cg * (0.12 + 0.22 * gl);
        A = clamp01(ag); R = (196 + 50 * streak) * A; G = (222 + 30 * streak) * A; B = (244 + 11 * streak) * A;
      }
      // 2) 霜：分位数覆盖 × 霜花纹（中频脉络取峰 + 高频颗粒），背光处厚，日照下化薄
      var cf = VF[k] >= thF ? sstep(thF, thF + 0.04 + 0.06 * sheetF, VF[k]) : 0;
      if (cf > 0) {
        var gr = grainAt(L, i * 2, j * 2), vein = 1 - Math.abs(md * 2 - 1);
        var pat = 0.45 + 0.35 * sstep(0.55, 0.9, vein) + 0.35 * (gr - 0.5);
        var af = clamp01(cf * pat * (0.5 + 0.45 * sheetF + 0.25 * sh2) * sunF);
        var cr = 214 + 32 * gr, cgc = 226 + 24 * gr, cb = 240 + 15 * gr;
        R = cr * af + R * (1 - af); G = cgc * af + G * (1 - af); B = cb * af + B * (1 - af); A = af + A * (1 - af);
      }
      // 3) 霰积层：斑块内的白粒点阵（点阵阈值随密度下降，厚处连成白片），斑块边缘只剩零星粒
      var cp = VP[k] >= thP ? sstep(thP, thP + 0.06, VP[k]) : 0;
      if (cp > 0) {
        // 只铺一层平滑的白底，粒子本身在 bake 里用圆粒精灵盖上去（逐像素点阵会像电视雪花）
        var ap = clamp01(cp * sheetP * (0.25 + 0.3 * sstep(0.4, 0.8, md)));
        R = 240 * ap + R * (1 - ap); G = 244 * ap + G * (1 - ap); B = 250 * ap + B * (1 - ap); A = ap + A * (1 - ap);
      }
      if (A <= 0.004) continue;
      var inv = 1 / A; // R/G/B 是预乘颜色，除回去得到直通色
      d[o] = Math.min(255, R * inv); d[o + 1] = Math.min(255, G * inv); d[o + 2] = Math.min(255, B * inv);
      d[o + 3] = Math.round(A * 255);
    }
    g.putImageData(img, 0, 0);
    // 霰粒落点：6px 网格哈希抖动，斑块内概率随 pel 升高，斑块边缘只剩零星粒
    L.pelDots = [];
    if (a.pel > 0.005) for (j = 0; j < mh; j += 3) for (i = 0; i < mw; i += 3) {
      var px2 = i + hashU(L, i, j, 61) * 3, py2 = j + hashU(L, i, j, 63) * 3; k = (py2 | 0) * mw + (px2 | 0);
      if (k >= n || VP[k] < 0) continue;
      var cov = VP[k] >= thP ? sstep(thP, thP + 0.08, VP[k]) : 0.12 * sstep(thP - 0.12, thP, VP[k]);
      if (hashU(L, i, j, 67) > cov * (0.18 + 0.72 * a.pel)) continue;
      L.pelDots.push(px2 * BAKE, py2 * BAKE, hashU(L, i, j, 69));
    }
    // 亮冰点：在冰壳区按 12px 网格哈希挑点，数量随 glaze 增加；路面优先
    if (gl > 0.005) for (j = 0; j < mh; j += 6) for (i = 0; i < mw; i += 6) {
      var jx = i + ((hashU(L, i, j, 71) * 6) | 0), jy = j + ((hashU(L, i, j, 73) * 6) | 0); if (jx >= mw || jy >= mh) continue;
      k = jy * mw + jx; if (VG[k] < thG) continue;
      if (hashU(L, i, j, 79) > 0.015 + 0.16 * gl * gl + 0.45 * X3[k * 3] * gl) continue;
      L.glints.push({ x: jx * BAKE, y: jy * BAKE, ph: hashU(L, i, j, 83) * 50, big: hashU(L, i, j, 89) < 0.25 + 0.4 * gl });
    }
  }

  /**
   * 前景剪影边缘层（全分辨率，只在烘焙时算）：逐列从上沿向下记深度。
   * 上沿内侧：霜边 / 冰壳亮边 / 霰积白；剪影整体：冰面高光条、霜粉、雾凇覆白（树叶更多）；
   * 上沿与左右边外侧：雾凇白絮（长度按细噪波逐列变化，再用高频颗粒打散成毛刺）。
   */
  function bakeEdges(L, occ) {
    var a = L.amt, W = L.W, H = L.H, D = occ.D;
    if (!L.edge || L.edge.width !== W || L.edge.height !== H) L.edge = canvas(W, H);
    var g = L.edge.getContext('2d'); g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, W, H);
    L.icicles = []; L.roofDots = [];
    if (!D) return;
    var img = g.createImageData(W, H), E = img.data, x, y, o;
    var sunF = 1 - 0.6 * a.sun, fr = a.frost * sunF, rm = a.rime, gl = a.glaze, pe = a.pel;
    var it = a.kind === 'freezing_rain' ? a.it : gl * 0.6;
    function op(x, y) { return x >= 0 && y >= 0 && x < W && y < H && D[(y * W + x) * 4 + 3] > OPA; }
    function leaf(o) { var r = D[o], gg = D[o + 1], b = D[o + 2]; return gg > r + 8 && gg > b + 4; }
    function put(x, y, r, gg, b, al) {
      if (al <= 0.003 || x < 0 || y < 0 || x >= W || y >= H) return;
      if (al > 1) al = 1;
      var o = (y * W + x) * 4, A0 = E[o + 3] / 255, A = al + A0 * (1 - al), k1 = al / A, k0 = 1 - k1;
      E[o] = r * k1 + E[o] * k0; E[o + 1] = gg * k1 + E[o + 1] * k0; E[o + 2] = b * k1 + E[o + 2] * k0; E[o + 3] = A * 255;
    }
    function fuzz(x, y, dx, dy, len, al) { // 一根雾凇毛刺：向 (dx,dy) 方向长 len 像素，越往外越稀
      for (var t = 1; t <= len; t++) {
        var px = x + dx * t, py = y + dy * t, f = t / (len + 1);
        if (op(px, py)) break;
        var gr = grainAt(L, px * 1.7, py * 1.7);
        put(px, py, 242, 247, 253, al * (1 - f * 0.7) * (gr > 0.3 + 0.45 * f ? 1 : 0.2));
      }
    }
    var dF = 1 + 3.5 * fr, dR = 1 + 7 * rm * rm + 2 * rm, dP0 = 1 + 6 * sstep(0.15, 1, pe);
    for (x = 0; x < W; x++) {
      var depth = -1;
      for (y = 0; y < H; y++) {
        o = (y * W + x) * 4;
        if (D[o + 3] <= OPA) { depth = -1; continue; }
        depth = depth < 0 ? 0 : depth + 1;
        var lf = leaf(o), gr = grainAt(L, x, y), n = L.nMid(x * 0.09, y * 0.09), d = depth;
        if (fr > 0.005) {
          if (d < dF) put(x, y, 232, 239, 248, fr * (0.5 + 0.45 * gr) * (1 - 0.6 * d / dF));
          put(x, y, 226, 234, 246, fr * (lf ? 0.55 : 0.3) * sstep(0.55 - 0.15 * fr, 0.85, gr));
        }
        if (gl > 0.005) {
          if (d < 2) put(x, y, 236, 248, 255, gl * (0.45 + 0.3 * gr));
          put(x, y, 214, 236, 252, gl * (0.18 + 0.3 * sstep(0.05, 0, Math.abs(n - 0.5))));
          if (lf) put(x, y, 246, 252, 255, gl * 0.8 * sstep(0.82, 0.94, gr));
        }
        if (pe > 0.005) {
          var dP = dP0 * (0.5 + n);
          if (d < dP) put(x, y, 246, 248, 252, sstep(0, 0.4, pe) * (0.55 + 0.45 * (gr > 0.42 ? 1 : 0)) * (1 - 0.4 * d / Math.max(1, dP)));
          // 屋顶上的霰粒：稀疏网格哈希落点，烤完后用圆粒精灵画
          if ((x % 5) === 0 && (y % 5) === 0 && hashU(L, x, y, 117) < (0.06 + 0.5 * pe * pe) * (0.4 + n))
            L.roofDots.push(x + hashU(L, x, y, 119) * 4, y + hashU(L, x, y, 121) * 4, hashU(L, x, y, 123) * 0.9);
        }
        if (rm > 0.005) {
          if (d < dR * (lf ? 1.5 : 1)) put(x, y, 240, 245, 252, rm * (0.65 + 0.3 * gr));
          if (lf) put(x, y, 236, 242, 250, rm * (0.2 + 0.65 * sstep(0.32, 0.7, n)) * (0.55 + 0.45 * gr));
          else put(x, y, 236, 242, 250, rm * (0.25 + 0.3 * rm) * sstep(0.62 - 0.25 * rm, 0.85 - 0.2 * rm, gr));
        }
        // 上沿外侧白絮（雾凇）与霜晶
        if (d === 0) {
          var rl = rm * (2 + 9 * rm * (lf ? 1.4 : 1)) * (0.35 + 0.65 * L.nFine(x * 0.6, y * 0.6)) + fr * 1.5;
          if (rl >= 1) fuzz(x, y, 0, -1, Math.round(rl), Math.min(1, rm * 0.95 + fr * 0.4));
        }
        // 树叶下沿：冻雨挂小冰珠 / 冰凌
        if (gl > 0.08 && lf && !op(x, y + 1) && hashU(L, x, y, 101) < 0.1 + 0.15 * gl)
          L.icicles.push({ x: x, y: y, len: 1 + 5 * gl * hashU(L, x, y, 103) + 2 * it, w: 0.9 + 0.8 * gl, leaf: 1 });
      }
    }
    // 左右边外侧白絮
    if (rm > 0.05) for (y = 0; y < H; y++) for (x = 1; x < W - 1; x++) {
      var c0 = op(x, y);
      if (c0 === op(x - 1, y) && c0 === op(x + 1, y)) continue;
      if (!c0) continue;
      var lf2 = leaf((y * W + x) * 4), sl = rm * (1.5 + 5 * (lf2 ? 1.4 : 1)) * (0.3 + 0.7 * L.nFine(x * 0.6 + 40, y * 0.6));
      if (sl < 1) continue;
      if (!op(x - 1, y)) fuzz(x, y, -1, 0, Math.round(sl), rm * 0.8);
      if (!op(x + 1, y)) fuzz(x, y, 1, 0, Math.round(sl), rm * 0.8);
    }
    g.putImageData(img, 0, 0);
    eaves(L, occ, it);
    drawIcicles(L, g);
  }
  /**
   * 屋檐线：在每个建筑包围盒里逐列自上而下找「屋顶色（饱和、偏暗）→ 墙面色（浅、低饱和）」的转折，
   * 就是檐口；没有 occluder 颜色时退回 roofY + 0.42h。冰凌 / 檐下冰晶沿这条线挂。
   */
  function eaves(L, occ, it) {
    var a = L.amt, D = occ.D, W = L.W, H = L.H, bs = (L.scene && L.scene.buildings) || [];
    var gl = a.glaze, rm = a.rime, fr = a.frost * (1 - 0.6 * a.sun);
    var crystal = Math.max(rm, fr * 0.8);
    if (gl < 0.03 && crystal < 0.35) return;
    bs.forEach(function (b, bi) {
      var x0 = Math.max(0, Math.floor(b.x)), x1 = Math.min(W - 1, Math.ceil(b.x + b.w)), y0 = Math.max(0, Math.floor(b.roofY == null ? b.y : b.roofY));
      var y1 = Math.min(H - 1, Math.ceil(b.y + b.h)), step = 3 + ((hashU(L, bi, 0, 107) * 3) | 0);
      for (var x = x0 + 2; x < x1 - 2; x += step) {
        var ey = -1;
        if (occ.real) {
          var run = 0;
          for (var y = y0; y < y1; y++) {
            var o = (y * W + x) * 4; if (D[o + 3] <= OPA) { run = 0; continue; }
            var r = D[o], g = D[o + 1], bl = D[o + 2], mx = Math.max(r, g, bl), mn = Math.min(r, g, bl), lum = (r + g + bl) / 3;
            var sat = mx ? (mx - mn) / mx : 0;
            if (lum > 168 && sat < 0.28) { if (run >= 6) { ey = y; break; } run = 0; }
            else run++;
          }
          if (ey < 0 || D[((ey + 2 < H ? ey + 2 : ey) * W + x) * 4 + 3] <= OPA) continue;
        } else ey = Math.round(y0 + (y1 - y0) * 0.42);
        var h = hashU(L, x, ey, 109), h2 = hashU(L, x, ey, 113);
        if (gl >= 0.03 && h < 0.35 + 0.5 * gl) {
          // 冰凌长度随强度与 glaze 增加；少数粗长
          var len = (2 + 7 * gl + 6 * it * gl) * (0.35 + 0.65 * h2) * (h2 > 0.85 ? 1.7 : 1);
          L.icicles.push({ x: x + (h * 2 | 0), y: ey - 1, len: len, w: 1.1 + 1.6 * gl * (0.5 + h2), leaf: 0 });
        } else if (crystal >= 0.35 && h < 0.7) {
          L.icicles.push({ x: x, y: ey - 1, len: 1.5 + 4 * (crystal - 0.3) * (0.4 + h2), w: 1, leaf: 2 });
        }
      }
    });
  }
  /** 冰凌：倒三角，冷白→透明，左侧一道高光；leaf=1 树叶下的冰珠；leaf=2 檐下白色冰晶 */
  function drawIcicles(L, g) {
    var list = L.icicles; if (!list || !list.length) return;
    g.save(); g.setTransform(1, 0, 0, 1, 0, 0); g.lineCap = 'round';
    for (var i = 0; i < list.length; i++) {
      var c = list[i], x = c.x + 0.5, y = c.y, w = c.w, len = c.len;
      if (c.leaf === 2) {
        g.strokeStyle = 'rgba(244,248,253,0.9)'; g.lineWidth = 0.9;
        g.beginPath(); g.moveTo(x, y); g.lineTo(x - 0.8, y + len); g.moveTo(x, y); g.lineTo(x + 1, y + len * 0.7); g.stroke();
        continue;
      }
      var gr = g.createLinearGradient(0, y, 0, y + len);
      gr.addColorStop(0, 'rgba(236,248,255,0.95)'); gr.addColorStop(0.6, 'rgba(196,226,248,0.75)'); gr.addColorStop(1, 'rgba(190,222,248,0.15)');
      g.fillStyle = gr;
      g.beginPath(); g.moveTo(x - w, y); g.lineTo(x + w, y); g.lineTo(x + 0.15, y + len); g.closePath(); g.fill();
      g.strokeStyle = 'rgba(60,90,120,0.35)'; g.lineWidth = 0.5; g.stroke();
      if (len > 3) { g.strokeStyle = 'rgba(255,255,255,0.95)'; g.lineWidth = 0.6; g.beginPath(); g.moveTo(x - w * 0.4, y + 0.5); g.lineTo(x - 0.1, y + len * 0.6); g.stroke(); }
      if (c.leaf === 1) { g.fillStyle = 'rgba(250,253,255,0.95)'; g.beginPath(); g.arc(x, y + len, 0.8, 0, Math.PI * 2); g.fill(); }
    }
    g.restore();
  }
  // ---------------------------------------------------------------- 粒子推进
  function rnd(L) { return L.r ? L.r() : (L.r = L.N.rng(L.seed + 9))(); }
  /** 冻雨：细直雨丝，比普通雨稀、细；落到各自的着地深度后留下一个小冰溅点 */
  function updRain(L, dt) {
    var a = L.amt, W = L.W, H = L.H, M = 60, ws = L.wind.s * L.gust;
    if (a.rain > 0) L.rainRate = a.rain;
    var tgt = a.rain > 0 ? 0.08 + 0.92 * Math.pow(a.rain, 1.2) : 0;
    L.rainK = (L.rainK || 0) + (tgt - (L.rainK || 0)) * Math.min(1, dt * 3);
    var rate = L.rainRate || 0, n = L.rainN = Math.min(L.rain.length, Math.round(L.rain.length * L.rainK));
    L.rvx = L.wind.x * (40 + 260 * ws); L.rvy = 640 + 420 * rate + L.wind.y * 60 * ws;
    for (var i = 0; i < n; i++) {
      var p = L.rain[i];
      if (!p.init) { p.x = p.x * (W + 2 * M) - M; p.y = p.y * (H + 2 * M) - M; p.ty = rnd(L) * (H + M); p.init = true; }
      p.x += L.rvx * p.v * dt; p.y += L.rvy * p.v * dt;
      if (p.y >= p.ty) {
        if (L.spl.length < 260 && rnd(L) < 0.5 + 0.5 * rate) L.spl.push({ x: p.x, y: p.ty, t: 0 });
        p.y = -M * rnd(L); p.x = rnd(L) * (W + 2 * M) - M; p.ty = rnd(L) * (H + M);
      }
      if (p.x > W + M) p.x -= W + 2 * M; else if (p.x < -M) p.x += W + 2 * M;
    }
    for (i = L.spl.length - 1; i >= 0; i--) { L.spl[i].t += dt; if (L.spl[i].t > 0.35) L.spl.splice(i, 1); }
  }
  /** 霰：下落快于雪、慢于冰雹；着地后（中档起）小幅弹跳 1 次，停一会儿淡出，再从上方补充 */
  function updPel(L, dt) {
    var a = L.amt, W = L.W, H = L.H, ws = L.wind.s * L.gust;
    if (a.hail > 0) L.pelRate = a.hail;
    var tgt = a.hail > 0 ? 0.05 + 0.95 * Math.pow(a.hail, 1.15) : 0;
    L.pelK = (L.pelK || 0) + (tgt - (L.pelK || 0)) * Math.min(1, dt * 3);
    var rate = L.pelRate || 0, n = L.pelN = Math.min(L.pel.length, Math.round(L.pel.length * L.pelK));
    var vx = L.wind.x * (30 + 170 * ws), bounce = rate >= 0.3;
    for (var i = 0; i < n; i++) {
      var p = L.pel[i];
      if (!p.init) { p.ty = rnd(L) * (H + 20); p.y = p.ty - rnd(L) * H; p.x = rnd(L) * W; p.st = 0; p.a = 1; p.init = true; }
      if (p.st === 0) {
        p.y += (230 + 170 * p.s) * (1 + 0.35 * rate) * dt; p.x += (vx + Math.sin(p.k * 40 + L.t * 3) * 8) * dt;
        if (p.y >= p.ty) {
          p.y = p.ty;
          if (bounce) { p.st = 1; p.vy = -(35 + 85 * p.k) * (0.6 + 0.6 * rate); p.vx = (p.s - 0.5) * 40; p.b = 0; }
          else { p.st = 2; p.life = 0.5 + 1.2 * p.k; }
        }
      } else if (p.st === 1) {
        p.vy += 900 * dt; p.y += p.vy * dt; p.x += p.vx * dt;
        if (p.y >= p.ty) {
          p.y = p.ty;
          if (p.b < 1 && p.vy > 70) { p.vy = -p.vy * 0.32; p.vx *= 0.5; p.b++; }
          else { p.st = 2; p.life = 0.6 + 1.6 * p.k; }
        }
      } else {
        p.life -= dt; p.a = clamp01(p.life / 0.4);
        if (p.life <= 0) { p.st = 0; p.a = 1; p.ty = rnd(L) * (H + 20); p.y = -6 - rnd(L) * 80; p.x = rnd(L) * W; }
      }
    }
  }
  // ---------------------------------------------------------------- 绘制
  function drawGround(L, ctx) {
    if (L.empty || !L.gc) return;
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.drawImage(L.gc, 0, 0); ctx.restore();
    var gl = L.amt.glaze, list = L.glints; if (gl <= 0.005 || !list.length) return;
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    var t = L.t, N = L.N, s = L.seed + 7, big = L.spr.glint, sm = L.spr.glintS;
    for (var i = 0; i < list.length; i++) {
      var q = list[i], f = N.noise2(s, q.ph + t * 0.8, q.ph * 0.37);
      var al = sstep(0.5, 0.92, f) * (0.3 + 0.7 * gl); if (al < 0.03) continue;
      var sp = q.big ? big : sm; ctx.globalAlpha = al;
      ctx.drawImage(sp, q.x - sp.width / 2, q.y - sp.height / 2);
    }
    ctx.restore();
  }
  function drawPrecip(L, ctx) {
    var i, p;
    ctx.save();
    if (L.rainN > 0) {
      var rate = L.rainRate || 0, sp = Math.hypot(L.rvx, L.rvy) || 1, ux = L.rvx / sp, uy = L.rvy / sp, k = clamp01(L.rainK / 0.2);
      [[0, 0.5, 0.7, 0.26], [0.5, 1, 1.0, 0.44]].forEach(function (lay) {
        ctx.strokeStyle = 'rgba(206,224,242,' + (lay[3] * (0.7 + 0.3 * rate) * k).toFixed(3) + ')'; ctx.lineWidth = lay[2];
        ctx.beginPath();
        for (i = 0; i < L.rainN; i++) {
          p = L.rain[i]; if (p.z < lay[0] || p.z >= lay[1]) continue;
          var len = (7 + 11 * rate) * p.l * (0.6 + 0.6 * p.z);
          ctx.moveTo(p.x, p.y); ctx.lineTo(p.x - ux * len, p.y - uy * len);
        }
        ctx.stroke();
      });
      ctx.strokeStyle = 'rgba(232,244,255,0.75)'; ctx.lineWidth = 0.8; ctx.beginPath();
      for (i = 0; i < L.spl.length; i++) {
        var s = L.spl[i], r = 1 + s.t * 7;
        ctx.moveTo(s.x - r, s.y); ctx.lineTo(s.x - r * 0.3, s.y - r * 0.5); ctx.moveTo(s.x + r, s.y); ctx.lineTo(s.x + r * 0.3, s.y - r * 0.5);
      }
      ctx.stroke();
    }
    if (L.pelN > 0) {
      var pr = L.pelRate || 0, spr = L.spr.pel, kk = clamp01(L.pelK / 0.15);
      for (i = 0; i < L.pelN; i++) {
        p = L.pel[i];
        var im = spr[Math.min(2, Math.floor(p.s * (1.5 + 1.5 * pr)))];
        ctx.globalAlpha = p.a * kk; ctx.drawImage(im, p.x - im.width / 2, p.y - im.height / 2);
      }
    }
    ctx.restore();
  }
  /** rime 淡雾：两层可平铺雾团缓慢漂移 + 一层均匀冷白 */
  function drawFog(L, ctx) {
    var a = L.amt, f = a.fog + (a.rain > 0.6 ? (a.rain - 0.6) * 0.3 : 0); if (f <= 0.005) return;
    var W = L.W, H = L.H, t = L.t, wx = L.wind.x * 6 + 4;
    ctx.save();
    ctx.globalAlpha = f * 0.22; ctx.fillStyle = 'rgb(226,234,244)'; ctx.fillRect(0, 0, W, H);
    ctx.globalAlpha = f * 0.5; drawTiled(ctx, L.tex.fogA, 4.5, t * wx, t * 1.5, W, H);
    ctx.globalAlpha = f * 0.32; drawTiled(ctx, L.tex.fogB, 2.6, -t * wx * 1.7 + 300, t * 2.5, W, H);
    ctx.restore();
  }

  root.WeatherFX_ice = { create: create, KINDS: KINDS };
})(this);
