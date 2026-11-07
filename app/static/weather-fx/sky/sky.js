/*
 * 织梦 · 天气美术：天色天气（window.WeatherFX_sky），docs/weather-spec.md 第 8 节。
 * kind：haze 霾、dust 浮尘、blowing_sand 扬沙、heatwave 热浪、sunshower 太阳雨；
 * 另外对任何 kind 读 aerosol / rainbow / heat / ground.dust_cover（彩虹、热浪可叠在别的天气上）。
 * kind = sandstorm 的尘幕归 snow/sand.js，这里不重复画。
 * pass：ground（积灰 dust_cover）、precip（扬沙流沙带与沙粒、浮尘细粒、太阳雨雨丝与地面亮斑）、
 *       fog（热浪折射 → 去饱和压色 → 远近递增的气溶胶幕）、light（太阳雨暖金光束）、bow（彩虹）。
 * 热浪折射从调用方 ctx 的画布回读像素：要求调用方在 fog pass 之前已经把城镇底图画进同一张 canvas。
 * 坐标：scene 与绘制都用 CSS 像素；draw 内部 setTransform(dpr)。噪波全部预烘成可平铺纹理或低分辨率缓冲。
 */
(function (root) {
  'use strict';
  function clamp(x, a, b) { return x < a ? a : x > b ? b : x; }
  function c01(x) { return x < 0 ? 0 : x > 1 ? 1 : x; }
  function sstep(a, b, x) { var t = c01((x - a) / (b - a)); return t * t * (3 - 2 * t); }
  function num(v, d) { return typeof v === 'number' && isFinite(v) ? v : d; }
  function canvas(w, h) {
    var c = document.createElement('canvas'); c.width = Math.max(1, Math.ceil(w)); c.height = Math.max(1, Math.ceil(h)); return c;
  }
  function rgba(c, a) { return 'rgba(' + (c[0] | 0) + ',' + (c[1] | 0) + ',' + (c[2] | 0) + ',' + c01(a).toFixed(3) + ')'; }
  function approach(cur, tgt, dt, rate) { return cur + (tgt - cur) * (1 - Math.exp(-dt * rate)); }
  /** 预烘可平铺噪波 → 白色 alpha 纹理；fn(n) 返回 alpha 0..1 */
  function alphaTile(N, seed, size, period, oct, fn) {
    var t = N.tile(seed, size, period, oct), c = canvas(size, size), g = c.getContext('2d');
    var img = g.createImageData(size, size), d = img.data;
    for (var i = 0, n = size * size; i < n; i++) {
      d[i * 4] = d[i * 4 + 1] = d[i * 4 + 2] = 255; d[i * 4 + 3] = Math.round(255 * c01(fn(t[i] / 255)));
    }
    g.putImageData(img, 0, 0); return c;
  }
  /** 平铺纹理铺满 [x0,x0+W]×[y0,y0+H]；ox/oy 偏移做流动，sx/sy 可不等比放大 */
  function drawTiled(g, tex, sx, sy, ox, oy, W, H, x0, y0) {
    x0 = x0 || 0; y0 = y0 || 0;
    var w = tex.width * sx, h = tex.height * sy, bx = x0 - (((ox % w) + w) % w), by = y0 - (((oy % h) + h) % h);
    for (var y = by; y < y0 + H; y += h) for (var x = bx; x < x0 + W; x += w) g.drawImage(tex, x, y, w + 0.6, h + 0.6);
  }
  /** 太阳：白天 elev∈(0,1]（正午 1），theta 为日出→日落的 0..π（与 daylight.js 的 sunOf 一致） */
  function sunOf(h, sr, ss) {
    sr = clamp(num(sr, 6), 1, 12); ss = clamp(num(ss, 18), sr + 3, 23);
    if (h < sr || h > ss) return { up: false, elev: 0, theta: h > ss ? Math.PI : 0 };
    var th = Math.PI * (h - sr) / (ss - sr); return { up: true, elev: Math.sin(th), theta: th };
  }

  // 气溶胶外观：veil 幕色、tint 正片叠底压色、soft 柔光染色、base 近处底、far 远处增量、clump 霾团、
  // desat 去饱和、cs 霾团纹理放大（缓冲像素 / 纹理像素）、st 顺风拉长、drift 流动速度（CSS px/s，静风 + 风速项）
  var AERO = {
    haze: { veil: [178, 168, 146], tint: [206, 194, 170], tintA: 0.62, soft: null, base: 0.2, far: 0.74, clump: 0.55,
      desat: 0.5, cs: 1.25, st: 1.5, drift: [3, 10] },
    dust: { veil: [232, 206, 150], tint: [248, 230, 186], tintA: 0.4, soft: [246, 200, 112], base: 0.08, far: 0.56, clump: 0.3,
      desat: 0.28, cs: 1.0, st: 2.2, drift: [8, 34] },
    sand: { veil: [216, 176, 116], tint: [240, 216, 170], tintA: 0.34, soft: [230, 176, 98], base: 0.05, far: 0.34, clump: 0.34,
      desat: 0.18, cs: 0.7, st: 4.5, drift: [30, 130] }
  };
  var AKEYS = ['haze', 'dust', 'sand'];
  var VB = 6, FB = 4, DC = 4, RB = 3;            // 低分辨率缓冲缩小倍数（CSS 像素 / 缓冲像素）
  var MAX_DUST = 520, MAX_GRAIN = 900, MAX_DROP = 470, MAX_SPLASH = 140, N_GLINT = 80;
  // 彩虹色谱：内（紫）→ 外（红）
  var SPEC = [[150, 84, 214], [86, 96, 236], [56, 150, 244], [70, 204, 112], [252, 232, 70], [255, 152, 48], [238, 62, 52]];
  function spec(u) {
    var f = c01(u) * 6, i = Math.min(5, f | 0), t = f - i, a = SPEC[i], b = SPEC[i + 1];
    return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
  }

  function create(opts) {
    opts = opts || {};
    var N = opts.noise || root.WeatherNoise;
    if (!N) throw new Error('WeatherFX_sky 需要 WeatherNoise');
    var L = { N: N, seed: (opts.seed >>> 0) || 1, W: 1400, H: 900, dpr: 1, t: 0, st: null, scene: null, inited: false,
      ae: { haze: 0, dust: 0, sand: 0 }, drift: { haze: [0, 0], dust: [0, 0], sand: [0, 0] },
      heat: 0, bow: 0, flow: 0, shower: 0, cover: 0, tone: 0, cloud: 0, cloudOff: 0, flowOff: 0,
      wind: { x: 1, y: 0, ang: 0, sp: 0 }, sun: { up: true, elev: 0.6, theta: 1.2 },
      dust: [], grains: [], drops: [], splashes: [], glints: [], rbKey: '', dcKey: '' };
    L.R = N.rng(L.seed * 7 + 3);
    bake(L); initParticles(L); resize(L, 1400, 900, 1);
    return {
      resize: function (w, h, dpr) { resize(L, w, h, dpr); },
      setScene: function (sc) { L.scene = sc || null; bakeScene(L); },
      update: function (state, dt) { update(L, state || {}, clamp(num(dt, 0), 0, 0.1)); },
      draw: function (ctx, pass) { draw(L, ctx, pass); },
      dispose: function () {
        L.dust = L.grains = L.drops = L.splashes = L.glints = []; L.scene = null;
        L.hb = L.sm = L.rbC = L.rw = L.dcC = L.vb = L.fb = L.occFb = null;
      },
      kinds: ['haze', 'dust', 'blowing_sand', 'heatwave', 'sunshower'],
      passes: ['ground', 'precip', 'fog', 'light', 'bow'],
      _debug: L
    };
  }

  // ---------------------------------------------------------------- 预烘
  function tinted(tex, col) {
    var c = canvas(tex.width, tex.height), g = c.getContext('2d');
    g.drawImage(tex, 0, 0); g.globalCompositeOperation = 'source-in'; g.fillStyle = rgba(col, 1); g.fillRect(0, 0, c.width, c.height);
    return c;
  }
  function bake(L) {
    var N = L.N, s = L.seed;
    L.clumpTex = alphaTile(N, s + 11, 128, 4, 4, function (n) { return sstep(0.36, 0.82, n); });   // 霾团 / 尘团
    L.clump = {};
    AKEYS.forEach(function (k) { L.clump[k] = tinted(L.clumpTex, AERO[k].veil); });
    // 流沙带断续：稀 / 中 / 密三张阈值不同的遮罩，按强度交叉淡化
    L.holeTex = [0.64, 0.52, 0.38].map(function (th) { return alphaTile(N, s + 29, 128, 3, 3, function (n) { return sstep(th, th + 0.12, n); }); });
    L.streakTex = alphaTile(N, s + 41, 128, 8, 3, function (n) { return sstep(0.5, 0.78, n); });    // 流沙纹
    L.cloudTex = alphaTile(N, s + 53, 128, 3, 4, function (n) { return sstep(0.42, 0.8, n); });     // 遮彩虹的云
    L.heatTex = alphaTile(N, s + 67, 128, 5, 3, function (n) { return sstep(0.52, 0.78, n); });     // 近处热气团
  }
  function resize(L, w, h, dpr) {
    w = Math.max(1, num(w, 1400)); h = Math.max(1, num(h, 900));
    var sizeChanged = !L.dcField || w !== L.W || h !== L.H;
    L.W = w; L.H = h; L.dpr = clamp(num(dpr, 1), 0.5, 4);
    L.vb = canvas(w / VB + 2, h / VB + 2);
    L.fb = canvas(w / FB, h / FB);
    L.rbC = canvas(w / RB, h / RB);
    L.hb = canvas(w / 22, h / 6);
    if (sizeChanged) bakeField(L);
    bakeScene(L);
  }
  /** 积灰噪波场（只依赖画幅）：域扭曲 fbm，DC 倍缩小，值存 Float32 */
  function bakeField(L) {
    var N = L.N, dw = Math.ceil(L.W / DC), dh = Math.ceil(L.H / DC), f = new Float32Array(dw * dh), sx = L.W / 210, sy = L.H / 210;
    for (var y = 0; y < dh; y++) for (var x = 0; x < dw; x++) {
      var u = x / dw * sx, v = y / dh * sy;
      f[y * dw + x] = 0.72 * N.warp2(L.seed + 71, u, v, 1.5, 4) + 0.28 * N.noise2(L.seed + 73, u * 9, v * 9);
    }
    L.dcField = f; L.dw = dw; L.dh = dh; L.dcC = canvas(dw, dh); L.dcImg = L.dcC.getContext('2d').createImageData(dw, dh);
  }
  /** 场景遮罩：道路（少积灰）、前景剪影（建筑/树不积灰、流沙带从它们下面流过） */
  function bakeScene(L) {
    var sc = L.scene, dw = L.dw, dh = L.dh;
    L.road = null; L.occ = null; L.occFb = null; L.dcKey = '';
    if (!sc || !dw) return;
    var rc = canvas(dw, dh), rg = rc.getContext('2d');
    rg.fillStyle = '#fff';
    (sc.ground || []).forEach(function (r) { rg.fillRect(r[0] / DC - 0.5, r[1] / DC - 0.5, r[2] / DC + 1, r[3] / DC + 1); });
    var rd = rg.getImageData(0, 0, dw, dh).data, road = new Uint8Array(dw * dh), occ = new Uint8Array(dw * dh), i;
    for (i = 0; i < dw * dh; i++) road[i] = rd[i * 4 + 3];
    var oc = canvas(dw, dh), og = oc.getContext('2d');
    if (sc.occluder) og.drawImage(sc.occluder, 0, 0, dw, dh);
    else (sc.buildings || []).forEach(function (b) { og.fillStyle = '#000'; og.fillRect(b.x / DC, b.y / DC, b.w / DC, b.h / DC); });
    var od = og.getImageData(0, 0, dw, dh).data;
    for (i = 0; i < dw * dh; i++) occ[i] = od[i * 4 + 3];
    // 水面也不积灰
    var wc = canvas(dw, dh), wg = wc.getContext('2d'); wg.fillStyle = '#fff';
    (sc.water || []).forEach(function (r) { wg.fillRect(r[0] / DC, r[1] / DC, r[2] / DC, r[3] / DC); });
    var wd = wg.getImageData(0, 0, dw, dh).data;
    for (i = 0; i < dw * dh; i++) occ[i] = Math.max(occ[i], wd[i * 4 + 3]);
    L.road = road; L.occ = occ;
    var fb = canvas(L.fb.width, L.fb.height), fg = fb.getContext('2d');
    if (sc.occluder) fg.drawImage(sc.occluder, 0, 0, fb.width, fb.height);
    else (sc.buildings || []).forEach(function (b) { fg.fillStyle = '#000'; fg.fillRect(b.x / FB, b.y / FB, b.w / FB, b.h / FB); });
    L.occFb = fb;
    // 太阳雨地面亮斑：落在道路 / 空地格上（没有 ground 时随机）
    var R = L.N.rng(L.seed + 97), gr = sc.ground || [];
    L.glints = [];
    for (i = 0; i < N_GLINT; i++) {
      var x, y;
      if (gr.length) { var r = gr[(R() * gr.length) | 0]; x = r[0] + R() * r[2]; y = r[1] + R() * r[3]; }
      else { x = R() * L.W; y = R() * L.H; }
      L.glints.push({ x: x, y: y, ph: R() * 100, s: 0.6 + R() * 0.9 });
    }
  }
  function initParticles(L) {
    var R = L.R, i;
    for (i = 0; i < MAX_DUST; i++) L.dust.push({ x: R() * 1400, y: R() * 900, z: R(), ph: R() * 100 });
    for (i = 0; i < MAX_GRAIN; i++) L.grains.push({ x: R() * 1400, y: R() * 900, z: R(), ph: R() * 100 });
    for (i = 0; i < MAX_DROP; i++) L.drops.push(newDrop(L, true));
  }
  function newDrop(L, scatter) {
    var R = L.R, ty = R() * (L.H + 40), fall = 160 + R() * 380;
    return { x: R() * (L.W + 200) - 100, y: ty - (scatter ? R() * fall : fall), ty: ty, len: 9 + R() * 10, z: R() };
  }

  // ---------------------------------------------------------------- update：从 state 取目标量，平滑逼近，推进粒子
  function targets(st) {
    var k = st.kind || 'clear', it = c01(num(st.intensity, 0.5)), ae = st.aerosol || {}, at = ae.type, ad = c01(num(ae.density, 0));
    var tg = { haze: 0, dust: 0, sand: 0 };
    if (tg[at] != null && !(at === 'sand' && k === 'sandstorm')) tg[at] = ad;      // 沙暴的尘幕归 sand.js
    if (k === 'haze' && at !== 'haze') tg.haze = it;
    if (k === 'dust' && at !== 'dust') tg.dust = it;
    if (k === 'blowing_sand' && at !== 'sand') tg.sand = it;
    var g = st.ground || {};
    return {
      k: k, it: it, ae: tg,
      heat: st.heat != null ? c01(num(st.heat, 0)) : k === 'heatwave' ? it : 0,
      bow: st.rainbow != null ? c01(num(st.rainbow, 0)) : k === 'sunshower' ? it * 0.8 : 0,
      shower: k === 'sunshower' ? Math.max(0.12, it) : 0,
      cover: g.dust_cover != null ? c01(num(g.dust_cover, 0)) : k === 'dust' ? 0.12 + 0.6 * it : k === 'blowing_sand' ? 0.1 + 0.5 * it : 0,
      cloud: c01(num(st.cloud_cover, 0))
    };
  }
  function update(L, st, dt) {
    L.st = st; L.t += dt;
    var T = targets(st), r = L.inited ? 1 : 1e9, i;
    L.it = T.it; L.kind = T.k;
    AKEYS.forEach(function (a) { L.ae[a] = approach(L.ae[a], T.ae[a], dt * r, 2.5); if (!L.inited) L.ae[a] = T.ae[a]; });
    ['heat', 'bow', 'shower', 'cover', 'cloud'].forEach(function (q) { L[q] = L.inited ? approach(L[q], T[q], dt, 2.5) : T[q]; });
    L.inited = true;
    var w = st.wind || {}, ang = num(w.dir_deg, 90) * Math.PI / 180, sp = c01(num(w.speed, 0.3));
    L.wind = { x: Math.sin(ang), y: -Math.cos(ang), ang: Math.atan2(-Math.cos(ang), Math.sin(ang)), sp: sp, gust: c01(num(w.gust, 0)) };
    var tm = st.time || {};
    L.sun = sunOf(((num(tm.hour, 12) % 24) + 24) % 24, tm.sunrise, tm.sunset);
    var gustK = 1 + L.wind.gust * 0.6 * (L.N.noise2(L.seed + 5, L.t * 0.35, 3) - 0.3);
    AKEYS.forEach(function (a) {
      var A = AERO[a], v = (A.drift[0] + A.drift[1] * sp) * gustK * dt;
      L.drift[a][0] += L.wind.x * v; L.drift[a][1] += L.wind.y * v * 0.6 + dt * 0.8;
    });
    L.flowOff += (70 + 260 * sp) * gustK * dt;
    L.cloudOff += (4 + 10 * sp) * dt;
    var W = L.W, H = L.H, t = L.t, N = L.N, wx = L.wind.x, wy = L.wind.y;
    // 浮尘细粒：缓慢、稀疏，随风漂 + 噪波摆动（也给扬沙补一些细尘）
    var dD = Math.max(L.ae.dust, L.ae.sand * 0.5, L.ae.haze * 0.15);
    L.nDust = Math.round(MAX_DUST * Math.pow(dD, 1.1));
    for (i = 0; i < L.nDust; i++) {
      var p = L.dust[i], v0 = (6 + 34 * sp) * (0.35 + p.z);
      p.x += (wx * v0 + (N.noise2(L.seed + 13, p.ph + t * 0.25, 0) - 0.5) * 22) * dt;
      p.y += (wy * v0 * 0.6 + (N.noise2(L.seed + 17, p.ph + t * 0.22, 5) - 0.5) * 16 + 2) * dt;
      wrap(p, W, H, 10);
    }
    // 扬沙沙粒：快、斜飘、贴近地面层
    L.nGrain = Math.round(MAX_GRAIN * Math.pow(L.ae.sand, 1.15));
    for (i = 0; i < L.nGrain; i++) {
      var q = L.grains[i], v1 = (110 + 360 * sp) * (0.45 + 0.9 * q.z) * gustK;
      q.x += wx * v1 * dt; q.y += (wy * v1 * 0.55 + 18 + 26 * q.z + (N.noise2(L.seed + 19, q.ph + t * 1.3, 1) - 0.5) * 60) * dt;
      wrap(q, W, H, 20);
    }
    // 太阳雨：雨丝落到各自的目标地面 y 后溅一下再重生
    L.nDrop = Math.round(MAX_DROP * L.shower * (0.25 + 0.75 * T.it));
    var vx = wx * sp * 260;
    for (i = 0; i < L.nDrop; i++) {
      var d = L.drops[i], vy = 760 + d.z * 320;
      d.x += vx * dt; d.y += vy * dt; d.vx = vx; d.vy = vy;
      if (d.y >= d.ty) {
        if (L.splashes.length < MAX_SPLASH && L.R() < 0.55) L.splashes.push({ x: d.x, y: d.ty, age: 0, z: d.z });
        L.drops[i] = newDrop(L, false);
      }
    }
    for (i = L.splashes.length - 1; i >= 0; i--) { L.splashes[i].age += dt; if (L.splashes[i].age > 0.3) L.splashes.splice(i, 1); }
  }
  function wrap(p, W, H, m) {
    if (p.x < -m) p.x += W + 2 * m; else if (p.x > W + m) p.x -= W + 2 * m;
    if (p.y < -m) p.y += H + 2 * m; else if (p.y > H + m) p.y -= H + 2 * m;
  }

  // ---------------------------------------------------------------- draw
  /** 按需建 / 复用缓冲画布 */
  function buf(L, name, w, h) {
    w = Math.max(1, Math.ceil(w)); h = Math.max(1, Math.ceil(h));
    var c = L[name]; if (!c || c.width !== w || c.height !== h) c = L[name] = canvas(w, h);
    return c;
  }
  function draw(L, ctx, pass) {
    if (!L.st || !ctx) return;
    ctx.save(); ctx.setTransform(L.dpr, 0, 0, L.dpr, 0, 0);
    ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1;
    if (pass === 'ground') drawGround(L, ctx);
    else if (pass === 'precip') drawPrecip(L, ctx);
    else if (pass === 'fog') { drawHeat(L, ctx); drawAerosol(L, ctx); drawMotes(L, ctx); }
    else if (pass === 'light') drawLight(L, ctx);
    else if (pass === 'bow') drawBow(L, ctx);
    ctx.restore();
  }
  // ---- ground：积灰斑块（噪波阈值随 dust_cover 降低，道路少积、建筑和水面不积）+ 太阳雨地面亮斑
  function rebakeCover(L) {
    var f = L.dcField, d = L.dcImg.data, c = L.cover, road = L.road, occ = L.occ, n = L.dw * L.dh;
    var thr0 = 0.7 - 0.46 * c, amp = 0.5 + 0.4 * c;
    for (var i = 0; i < n; i++) {
      var rd = road ? road[i] / 255 : 0, oc = occ ? occ[i] / 255 : 0, v = f[i], thr = thr0 + rd * 0.14;
      var a = sstep(thr, thr + 0.1, v) * amp * (1 - 0.72 * rd) * (1 - oc);
      var k = sstep(0.3, 0.8, v);
      d[i * 4] = 194 + 32 * k; d[i * 4 + 1] = 158 + 36 * k; d[i * 4 + 2] = 98 + 36 * k; d[i * 4 + 3] = 255 * a;
    }
    L.dcC.getContext('2d').putImageData(L.dcImg, 0, 0);
  }
  function drawGround(L, g) {
    if (L.cover > 0.01 && L.dcField) {
      var key = Math.round(L.cover * 60) + '/' + (L.scene ? 1 : 0);
      if (key !== L.dcKey) { rebakeCover(L); L.dcKey = key; }
      g.imageSmoothingEnabled = true; g.drawImage(L.dcC, 0, 0, L.W, L.H);
    }
    if (L.shower > 0.02 && L.sun.up && L.glints.length) {
      var spr = glintSprite(L), n = Math.round(L.glints.length * (0.3 + 0.7 * L.shower)), t = L.t;
      g.globalCompositeOperation = 'lighter';
      for (var i = 0; i < n; i++) {
        var p = L.glints[i], a = Math.pow(L.N.noise2(L.seed + 61, p.ph + t * 1.6, 0), 3) * 2.2 * L.shower;
        if (a < 0.03) continue;
        var s = 10 * p.s; g.globalAlpha = c01(a); g.drawImage(spr, p.x - s, p.y - s * 0.5, s * 2, s);
      }
      g.globalAlpha = 1; g.globalCompositeOperation = 'source-over';
    }
  }
  function glintSprite(L) {
    if (L.glintSpr) return L.glintSpr;
    var c = canvas(32, 32), g = c.getContext('2d'), gr = g.createRadialGradient(16, 16, 0, 16, 16, 16);
    gr.addColorStop(0, 'rgba(255,246,206,0.95)'); gr.addColorStop(0.35, 'rgba(255,222,140,0.45)'); gr.addColorStop(1, 'rgba(255,200,110,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 32, 32); return (L.glintSpr = c);
  }
  // ---- precip：扬沙流沙带 + 沙粒、浮尘细粒、太阳雨
  function drawPrecip(L, g) {
    if (L.ae.sand > 0.01) drawSandFlow(L, g);
    if (L.nDrop > 0) drawShower(L, g);
  }
  /** 飘尘粒子（扬沙沙粒、浮尘细粒）：画在气溶胶幕之后（fog pass 末尾），否则被幕盖掉看不见 */
  function drawMotes(L, g) {
    var i, p;
    if (L.nGrain > 0) {
      var sp = L.wind.sp, wx = L.wind.x, wy = L.wind.y, bins = [[], []];
      for (i = 0; i < L.nGrain; i++) bins[L.grains[i].z > 0.62 ? 1 : 0].push(L.grains[i]);
      var cols = [[176, 128, 70, 0.6], [242, 210, 150, 0.85]];
      for (var b = 0; b < 2; b++) {
        g.strokeStyle = rgba(cols[b], cols[b][3] * (0.55 + 0.45 * L.ae.sand)); g.lineWidth = b ? 1.5 : 1.0; g.beginPath();
        bins[b].forEach(function (q) {
          var len = (3 + q.z * 9) * (0.6 + 0.9 * sp);
          g.moveTo(q.x, q.y); g.lineTo(q.x - wx * len, q.y - wy * len * 0.55 - 1.5);
        });
        g.stroke();
      }
    }
    if (L.nDust > 0) {
      // 亮细粒 + 少量深色粒，在黄幕上都看得出
      var dc = L.ae.dust >= L.ae.sand ? [255, 244, 210] : [248, 226, 176];
      for (var z = 0; z < 3; z++) {
        g.fillStyle = rgba(z === 0 ? [150, 116, 70] : dc, z === 0 ? 0.45 : 0.4 + 0.25 * z); g.beginPath();
        for (i = 0; i < L.nDust; i++) {
          p = L.dust[i]; if (((p.z * 3) | 0) !== z) continue;
          var s = 1.2 + z * 0.8; g.rect(p.x, p.y, s, s);
        }
        g.fill();
      }
    }
  }
  /** 贴地流沙带：在 1/FB 缓冲里沿风向铺拉长的流沙纹 → 用断续遮罩挖成一条条带 → 抠掉建筑剪影（沙从房子底下流过）→ 染色 */
  function drawSandFlow(L, g) {
    var a = L.ae.sand, fb = L.fb, fw = fb.width, fh = fb.height, fg = fb.getContext('2d'), diag = Math.hypot(fw, fh) + 8;
    var mk = buf(L, 'mk', fw, fh), mg = mk.getContext('2d');
    // 断续遮罩：三档阈值交叉淡化（0.2 零星几条，0.5 成带，0.9 连成片）
    var u = clamp(a * 2.2 - 0.2, 0, 2), i0 = Math.min(1, u | 0), f = u - i0;
    mg.setTransform(1, 0, 0, 1, 0, 0); mg.clearRect(0, 0, fw, fh);
    mg.translate(fw / 2, fh / 2); mg.rotate(L.wind.ang);
    var hx = L.drift.sand[0] / FB * 0.35, hy = L.drift.sand[1] / FB * 0.1;
    mg.globalAlpha = 1 - f * 0.5; drawTiled(mg, L.holeTex[i0], 2.6, 1.1, hx, hy, diag, diag, -diag / 2, -diag / 2);
    mg.globalAlpha = f; drawTiled(mg, L.holeTex[i0 + 1], 2.6, 1.1, hx, hy, diag, diag, -diag / 2, -diag / 2);
    mg.globalAlpha = 1;
    fg.setTransform(1, 0, 0, 1, 0, 0); fg.globalCompositeOperation = 'source-over'; fg.clearRect(0, 0, fw, fh);
    fg.translate(fw / 2, fh / 2); fg.rotate(L.wind.ang);
    drawTiled(fg, L.streakTex, 5, 0.55, L.flowOff / FB, 0, diag, diag, -diag / 2, -diag / 2);
    fg.globalAlpha = 0.6; drawTiled(fg, L.streakTex, 3.2, 0.4, L.flowOff / FB * 0.62, 37, diag, diag, -diag / 2, -diag / 2);
    fg.globalAlpha = 1; fg.setTransform(1, 0, 0, 1, 0, 0);
    fg.globalCompositeOperation = 'destination-in'; fg.drawImage(mk, 0, 0);
    if (L.occFb) { fg.globalCompositeOperation = 'destination-out'; fg.drawImage(L.occFb, 0, 0); }
    fg.globalCompositeOperation = 'source-in'; fg.fillStyle = 'rgb(232,200,140)'; fg.fillRect(0, 0, fw, fh);
    fg.globalCompositeOperation = 'source-over';
    g.imageSmoothingEnabled = true; g.globalAlpha = c01(0.35 + 0.6 * a); g.drawImage(fb, 0, 0, L.W, L.H); g.globalAlpha = 1;
  }
  /** 太阳雨：短、稀、亮的暖金雨丝（lighter 叠加，不压暗）+ 落地小溅环 */
  function drawShower(L, g) {
    var sunK = L.sun.up ? 0.55 + 0.45 * sstep(0.05, 0.5, L.sun.elev) : 0.35, i, d;
    g.globalCompositeOperation = 'lighter'; g.lineCap = 'round';
    var cols = [[236, 196, 112], [255, 226, 150], [255, 250, 226]];
    for (var z = 0; z < 3; z++) {
      g.strokeStyle = rgba(cols[z], (0.5 + 0.22 * z) * sunK); g.lineWidth = 1.2 + 0.5 * z; g.beginPath();
      for (i = 0; i < L.nDrop; i++) {
        d = L.drops[i]; if (((d.z * 3) | 0) !== z) continue;
        var k = d.len / Math.hypot(d.vx || 0, d.vy || 1);
        g.moveTo(d.x, d.y); g.lineTo(d.x - (d.vx || 0) * k, d.y - (d.vy || 1) * k);
      }
      g.stroke();
    }
    g.strokeStyle = rgba([255, 232, 170], 0.5 * sunK); g.lineWidth = 0.8; g.beginPath();
    L.splashes.forEach(function (s) {
      var r = 1.5 + s.age * 18 * (0.6 + s.z * 0.6); g.moveTo(s.x + r, s.y); g.ellipse(s.x, s.y, r, r * 0.4, 0, 0, Math.PI * 2);
    });
    g.stroke();
    g.globalCompositeOperation = 'source-over';
  }

  // ---- fog（一）：热浪折射。回读调用方画布 → 1/2 缓冲 → 横向条带错位 + 分带竖向列位移 → 远处强、近处弱地贴回
  var SR = 2;
  function drawHeat(L, g) {
    var h = L.heat; if (h < 0.01 || !g.canvas) return;
    var W = L.W, H = L.H, sw = Math.ceil(W / SR), shh = Math.ceil(H / SR), t = L.t, N = L.N, s = L.seed;
    var sm = buf(L, 'sm', sw, shh), rw = buf(L, 'rw', sw, shh), sg = sm.getContext('2d'), rg = rw.getContext('2d');
    sg.setTransform(1, 0, 0, 1, 0, 0); sg.globalCompositeOperation = 'copy'; sg.globalAlpha = 1;
    sg.drawImage(g.canvas, 0, 0, g.canvas.width, g.canvas.height, 0, 0, sw, shh);
    sg.globalCompositeOperation = 'source-over';
    // 横向条带：每 2 缓冲像素一条，按 (y, t) 的噪波横移；越靠上（越远）位移越大；强档再叠一次反向半透明做拖影
    var amp = 0.8 + 6 * h, y, dx, far;
    rg.setTransform(1, 0, 0, 1, 0, 0); rg.globalCompositeOperation = 'copy'; rg.drawImage(sm, 0, 0);
    rg.globalCompositeOperation = 'source-over';
    for (y = 0; y < shh; y += 2) {
      far = Math.pow(1 - y / shh, 1.4);
      dx = amp * far * (N.noise2(s + 31, y * 0.11, t * 2.4) * 2 - 1 + 0.4 * (N.noise2(s + 37, y * 0.37, t * 5.1) * 2 - 1));
      if (Math.abs(dx) < 0.15) continue;
      rg.globalAlpha = 1; rg.drawImage(sm, 0, y, sw, 2, dx, y, sw, 2);
      if (h > 0.55) { rg.globalAlpha = (h - 0.55) * 1.3 * far; rg.drawImage(sm, 0, y, sw, 2, -dx * 1.6, y, sw, 2); }
    }
    // 竖向列位移：列宽 4，三条竖带各自的幅度（远带最大），噪波随时间上行 = 热气上升的抖动
    sg.globalCompositeOperation = 'copy'; sg.globalAlpha = 1; sg.drawImage(rw, 0, 0); sg.globalCompositeOperation = 'source-over';
    var bands = 3, bh = Math.ceil(shh / bands);
    for (var b = 0; b < bands; b++) {
      var by = b * bh, ab = (0.5 + 3.2 * h) * Math.pow(1 - b / bands, 1.2);
      if (ab < 0.25) continue;
      for (var x = 0; x < sw; x += 4) {
        var dy = ab * (N.noise2(s + 43 + b, x * 0.07, t * 1.7 + b * 3.1) * 2 - 1);
        sg.drawImage(rw, x, Math.max(0, by + dy), 4, bh, x, by, 4, bh);
      }
    }
    // 极强档：远景融成横向色带（再降采样成 22×6 一格的粗缓冲，平滑放大）
    var melt = sstep(0.55, 1, h);
    if (melt > 0.01) {
      var hb = L.hb, hg = hb.getContext('2d');
      hg.globalCompositeOperation = 'copy'; hg.drawImage(sm, 0, 0, hb.width, hb.height); hg.globalCompositeOperation = 'source-over';
      sg.save(); sg.imageSmoothingEnabled = true;
      var gr = sg.createLinearGradient(0, 0, 0, shh * 0.5);
      gr.addColorStop(0, 'rgba(0,0,0,1)'); gr.addColorStop(1, 'rgba(0,0,0,0)');
      var mel = buf(L, 'mel', sw, Math.ceil(shh * 0.5)), mgc = mel.getContext('2d');
      mgc.globalCompositeOperation = 'copy'; mgc.drawImage(hb, 0, 0, hb.width, hb.height * 0.5, 0, 0, sw, mel.height);
      mgc.globalCompositeOperation = 'destination-in'; mgc.fillStyle = gr; mgc.fillRect(0, 0, sw, mel.height);
      sg.globalAlpha = 0.75 * melt; sg.drawImage(mel, 0, 0); sg.restore();
    }
    // 贴回：远处整幅、近处只剩零星热气团（遮罩 = 竖向渐变 ∪ 上行的噪波热气团；先在独立缓冲里拼好再一次 destination-in）
    var hm = buf(L, 'hm', sw, shh), hmg = hm.getContext('2d');
    hmg.setTransform(1, 0, 0, 1, 0, 0); hmg.globalAlpha = 1; hmg.globalCompositeOperation = 'copy';
    var mg = hmg.createLinearGradient(0, 0, 0, shh);
    mg.addColorStop(0, 'rgba(0,0,0,1)'); mg.addColorStop(0.45, 'rgba(0,0,0,' + (0.45 + 0.4 * h).toFixed(3) + ')');
    mg.addColorStop(1, 'rgba(0,0,0,' + (0.05 + 0.25 * h).toFixed(3) + ')');
    hmg.fillStyle = mg; hmg.fillRect(0, 0, sw, shh);
    hmg.globalCompositeOperation = 'source-over'; hmg.globalAlpha = 0.35 + 0.6 * h;
    drawTiled(hmg, L.heatTex, 2.2, 1.2, 0, t * 9, sw, shh);
    hmg.globalAlpha = 1;
    sg.globalCompositeOperation = 'destination-in'; sg.drawImage(hm, 0, 0);
    sg.globalCompositeOperation = 'source-over';
    g.imageSmoothingEnabled = true; g.globalAlpha = c01(0.4 + 0.7 * h); g.drawImage(sm, 0, 0, W, H); g.globalAlpha = 1;
    // 天色发白、饱和度略降：灰色 saturation 混合 + 上浓下淡的白色 screen
    g.globalCompositeOperation = 'saturation'; g.fillStyle = rgba([128, 128, 128], 0.1 + 0.28 * h); g.fillRect(0, 0, W, H);
    g.globalCompositeOperation = 'screen';
    var wg = g.createLinearGradient(0, 0, 0, H);
    wg.addColorStop(0, rgba([255, 248, 230], 0.1 + 0.46 * h)); wg.addColorStop(0.6, rgba([255, 246, 228], 0.04 + 0.22 * h));
    wg.addColorStop(1, rgba([255, 244, 226], 0.03 + 0.08 * h));
    g.fillStyle = wg; g.fillRect(0, 0, W, H);
    g.globalCompositeOperation = 'source-over';
  }
  // ---- fog（二）：气溶胶。去饱和 → 正片叠底压色 → （浮尘/扬沙）柔光染黄 → 低分辨率霾团流动 → 远近递增的幕
  function drawAerosol(L, g) {
    var W = L.W, H = L.H;
    for (var ai = 0; ai < AKEYS.length; ai++) {
      var key = AKEYS[ai], d = L.ae[key], A = AERO[key];
      if (d < 0.01) continue;
      g.globalCompositeOperation = 'saturation'; g.fillStyle = rgba([128, 128, 128], A.desat * d); g.fillRect(0, 0, W, H);
      g.globalCompositeOperation = 'multiply'; g.fillStyle = rgba(A.tint, A.tintA * Math.pow(d, 1.1)); g.fillRect(0, 0, W, H);
      if (A.soft) { g.globalCompositeOperation = 'soft-light'; g.fillStyle = rgba(A.soft, 0.55 * d); g.fillRect(0, 0, W, H); }
      g.globalCompositeOperation = 'source-over';
      // 霾团：两层平铺噪波反向错动，竖向渐变（上 = 远处更浓）后放大
      var vb = L.vb, vg = vb.getContext('2d'), bw = vb.width, bh = vb.height, tex = L.clump[key], dr = L.drift[key];
      vg.setTransform(1, 0, 0, 1, 0, 0); vg.globalCompositeOperation = 'source-over'; vg.globalAlpha = 1; vg.clearRect(0, 0, bw, bh);
      drawTiled(vg, tex, A.cs * A.st, A.cs, -dr[0] / VB, -dr[1] / VB, bw, bh);
      vg.globalAlpha = 0.6; drawTiled(vg, tex, A.cs * A.st * 0.62, A.cs * 0.7, -dr[0] / VB * 0.55 + 41, -dr[1] / VB * 0.5 + 23, bw, bh);
      vg.globalAlpha = 1; vg.globalCompositeOperation = 'destination-in';
      var cg = vg.createLinearGradient(0, 0, 0, bh);
      cg.addColorStop(0, 'rgba(0,0,0,1)'); cg.addColorStop(0.55, 'rgba(0,0,0,0.7)'); cg.addColorStop(1, 'rgba(0,0,0,0.35)');
      vg.fillStyle = cg; vg.fillRect(0, 0, bw, bh); vg.globalCompositeOperation = 'source-over';
      g.imageSmoothingEnabled = true; g.globalAlpha = c01(A.clump * (0.4 + 0.8 * d) * d);
      g.drawImage(vb, 0, 0, bw, bh, -VB, -VB, bw * VB, bh * VB); g.globalAlpha = 1;
      // 远近幕：画面上方 = 远处，能见度随 density 下降
      // 线性随密度增长（原 d^0.75 让 0.2 / 0.5 两档太接近）
      var top = clamp(A.base * d + A.far * Math.pow(d, 0.8), 0, 0.95), mid = clamp(A.base * d + A.far * 0.45 * Math.pow(d, 1.1), 0, 0.85);
      var vgr = g.createLinearGradient(0, 0, 0, H);
      vgr.addColorStop(0, rgba(A.veil, top)); vgr.addColorStop(0.5, rgba(A.veil, mid)); vgr.addColorStop(1, rgba(A.veil, A.base * d));
      g.fillStyle = vgr; g.fillRect(0, 0, W, H);
      if (key === 'dust') {   // 浮尘天色更亮：screen 一层暖白
        g.globalCompositeOperation = 'screen'; g.fillStyle = rgba([255, 236, 186], 0.12 * d); g.fillRect(0, 0, W, H);
        g.globalCompositeOperation = 'source-over';
      }
    }
  }
  // ---- light：太阳雨暖金光（柔光染暖 + 几道斜光束，lighter，不压暗）
  function drawLight(L, g) {
    var s = L.shower; if (s < 0.02 || !L.sun.up) return;
    var W = L.W, H = L.H, k = s * (0.5 + 0.5 * sstep(0.05, 0.4, L.sun.elev));
    // 柔光染暖压得轻一点（太重在绿地上发橄榄色），再加一层暖白 screen 提亮
    g.globalCompositeOperation = 'soft-light'; g.fillStyle = rgba([255, 214, 140], 0.16 * k); g.fillRect(0, 0, W, H);
    g.globalCompositeOperation = 'screen'; g.fillStyle = rgba([255, 238, 196], 0.1 * k); g.fillRect(0, 0, W, H);
    g.globalCompositeOperation = 'lighter';
    var dir = Math.cos(L.sun.theta) > 0 ? 1 : -1, x0 = dir > 0 ? W : 0;
    for (var i = 0; i < 4; i++) {
      var ph = L.N.noise2(L.seed + 83, i * 3.7, L.t * 0.08), a = 0.05 * k * (0.4 + ph);
      var cx = x0 - dir * W * (0.18 + i * 0.22 + 0.05 * Math.sin(L.t * 0.05 + i)), wd = 50 + 70 * L.N.noise2(L.seed + 89, i, 0);
      g.save(); g.translate(cx, 0); g.rotate(dir * 0.42);
      var gr = g.createLinearGradient(-wd, 0, wd, 0);
      gr.addColorStop(0, 'rgba(255,220,150,0)'); gr.addColorStop(0.5, rgba([255, 224, 156], a)); gr.addColorStop(1, 'rgba(255,220,150,0)');
      g.fillStyle = gr; g.fillRect(-wd, -50, wd * 2, H * 1.4); g.restore();
    }
    g.globalCompositeOperation = 'source-over';
  }
  // ---- bow：彩虹。背阳一侧、画面上方；1/RB 缓冲画同心色带 → 噪波云遮、两端与下沿淡出 → screen 叠上
  function drawBow(L, g) {
    var b = L.bow; if (b < 0.01 || !L.sun.up) return;
    var W = L.W, H = L.H, sun = L.sun;
    var lowK = 1 - 0.55 * sstep(0.55, 0.95, sun.elev);            // 太阳越高，虹越低越淡
    var amt = b * lowK; if (amt < 0.01) return;
    // 太阳在东（theta≈0，画面右）→ 虹在左；正午太阳在南（画面下）→ 虹在正上方
    // 太阳低 → 虹大而高（弧顶贴近画面上沿）；太阳高 → 虹缩小下沉
    var R = H * (0.86 - 0.3 * sun.elev), topY = H * (0.06 + 0.16 * sun.elev);
    var cx = W / 2 - Math.cos(sun.theta) * W * 0.28, cy = topY + R;
    var c = L.rbC, rg = c.getContext('2d'), bw = c.width, bh = c.height, k = 1 / RB;
    rg.setTransform(1, 0, 0, 1, 0, 0); rg.globalCompositeOperation = 'source-over'; rg.globalAlpha = 1; rg.clearRect(0, 0, bw, bh);
    rg.setTransform(k, 0, 0, k, 0, 0);
    var w1 = R * 0.045, dbl = sstep(0.62, 0.85, b);
    cy += dbl * R * 0.24;                                           // 双虹时整体下移，让副虹弧顶留在画面里
    // 主虹内侧的亮区（虹里面天更亮）
    var ig = rg.createRadialGradient(cx, cy, R * 0.55, cx, cy, R - w1);
    ig.addColorStop(0, 'rgba(255,255,250,0)'); ig.addColorStop(1, 'rgba(255,255,248,0.16)');
    rg.fillStyle = ig; rg.beginPath(); rg.arc(cx, cy, R - w1, 0, Math.PI * 2); rg.fill();
    bowBand(rg, cx, cy, R, w1, false, 0.85, W, H);
    if (dbl > 0.01) bowBand(rg, cx, cy, R * 1.27, w1 * 1.35, true, 0.6 * dbl, W, H);
    rg.setTransform(1, 0, 0, 1, 0, 0);
    // 云遮：平铺云纹 destination-out，弱档挖得多（只剩几段），强档整弧完整
    rg.globalCompositeOperation = 'destination-out'; rg.globalAlpha = c01(0.2 + 0.45 * L.cloud + 0.55 * (1 - sstep(0.15, 0.55, b)));
    drawTiled(rg, L.cloudTex, 2.4, 1.4, L.cloudOff / RB, 0, bw, bh);
    // 下沿淡出（虹脚落到远处地面里）
    rg.globalAlpha = 1;
    var fg = rg.createLinearGradient(0, bh * 0.35, 0, bh * 0.92);
    fg.addColorStop(0, 'rgba(0,0,0,0)'); fg.addColorStop(1, 'rgba(0,0,0,1)');
    rg.fillStyle = fg; rg.fillRect(0, 0, bw, bh); rg.globalCompositeOperation = 'source-over';
    g.imageSmoothingEnabled = true; g.globalCompositeOperation = 'screen';
    g.globalAlpha = c01(0.35 + 0.75 * amt); g.drawImage(c, 0, 0, bw, bh, 0, 0, bw * RB, bh * RB);
    g.globalAlpha = 1; g.globalCompositeOperation = 'source-over';
  }
  /** 一条虹带：径向渐变按色谱排色，边缘 alpha 柔和（钟形）；rev = 副虹色序反（红在内） */
  function bowBand(g, cx, cy, R, w, rev, a, W, H) {
    var gr = g.createRadialGradient(cx, cy, R - w, cx, cy, R + w), n = 14;
    for (var i = 0; i <= n; i++) {
      var u = i / n, e = Math.sin(Math.PI * u), col = spec(rev ? 1 - u : u);
      gr.addColorStop(u, rgba(col, a * Math.pow(e, 0.8)));
    }
    g.fillStyle = gr; g.beginPath(); g.arc(cx, cy, R + w, 0, Math.PI * 2); g.arc(cx, cy, Math.max(1, R - w), 0, Math.PI * 2, true); g.fill();
  }

  root.WeatherFX_sky = { create: create, AERO: AERO, sunOf: sunOf };
})(this);
