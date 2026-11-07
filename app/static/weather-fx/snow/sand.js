/*
 * 织梦 · 天气美术：沙暴（kind = sandstorm）
 * window.WeatherFX_sand；接口见 docs/weather-spec.md 第 3 节。
 * pass：ground（地面沙尘积层）、precip（细沙粒子 + 贴地流沙线）、fog（三层尘幕 + 整体黄褐）。
 * 尘幕全部是预烘可平铺 fbm 纹理，放大后随风平移，不逐像素算。
 */
(function (root) {
  'use strict';
  function clamp01(x) { return x < 0 ? 0 : x > 1 ? 1 : x; }
  function sstep(a, b, x) { var t = clamp01((x - a) / (b - a)); return t * t * (3 - 2 * t); }
  function canvas(w, h) {
    var c = document.createElement('canvas');
    c.width = Math.max(1, Math.ceil(w)); c.height = Math.max(1, Math.ceil(h));
    return c;
  }
  function tileCanvas(N, seed, size, period, oct, fn) {
    var t = N.tile(seed, size, period, oct), c = canvas(size, size), g = c.getContext('2d');
    var img = g.createImageData(size, size), d = img.data;
    for (var i = 0, n = size * size; i < n; i++) {
      var px = fn(t[i] / 255, i % size, (i / size) | 0);
      d[i * 4] = px[0]; d[i * 4 + 1] = px[1]; d[i * 4 + 2] = px[2]; d[i * 4 + 3] = px[3];
    }
    g.putImageData(img, 0, 0);
    return c;
  }
  /** 纹理可按 sx/sy 不等比放大（尘幕横向拉长） */
  function drawTiled(ctx, tex, sx, sy, ox, oy, W, H) {
    var w = tex.width * sx, h = tex.height * sy, x0 = -(((ox % w) + w) % w), y0 = -(((oy % h) + h) % h);
    for (var y = y0; y < H; y += h) for (var x = x0; x < W; x += w) ctx.drawImage(tex, x, y, w + 0.5, h + 0.5);
  }

  // 三层尘幕：远层大而慢、颜色浅；近层细碎、快、颜色深
  var VEILS = [
    { seed: 11, size: 128, period: 3, oct: 5, sx: 12, sy: 3.5, speed: 0.45, lo: 0.35, hi: 0.85, rgb: [214, 170, 112], a: 0.7 },
    { seed: 23, size: 128, period: 5, oct: 4, sx: 9, sy: 1.6, speed: 0.8, lo: 0.45, hi: 0.88, rgb: [196, 146, 86], a: 0.6 },
    { seed: 37, size: 128, period: 8, oct: 3, sx: 4, sy: 1.4, speed: 1.35, lo: 0.55, hi: 0.92, rgb: [184, 136, 80], a: 0.45 }
  ];
  var MAXP = 900, STREAKS = 70;

  function create(opts) {
    opts = opts || {};
    var N = opts.noise || root.WeatherNoise;
    if (!N) throw new Error('WeatherFX_sand 需要 WeatherNoise');
    var L = { N: N, seed: (opts.seed >>> 0) || 1, W: 1, H: 1, dpr: 1, t: 0, state: null, scene: null,
      active: 0, it: 0, off: 0, sceneId: 0, bakedId: -1, bakedK: -1, pool: [], streaks: [], n: 0, ns: 0 };
    init(L);
    return {
      resize: function (w, h, dpr) { L.W = w; L.H = h; L.dpr = dpr || 1; L.sceneId++; },
      setScene: function (scene) { L.scene = scene || null; L.sceneId++; },
      update: function (state, dt) { update(L, state || {}, Math.min(0.1, Math.max(0, dt || 0))); },
      draw: function (ctx, pass) {
        if (!L.state || L.active <= 0.01) return;
        if (pass === 'ground') drawGround(L, ctx);
        else if (pass === 'precip') drawPrecip(L, ctx);
        else if (pass === 'fog') drawVeil(L, ctx);
      },
      dispose: function () { L.pool = []; L.streaks = []; L.veils = []; L.scene = null; L.gc = null; },
      kinds: ['sandstorm'],
      _debug: L
    };
  }
  function init(L) {
    var N = L.N, r = N.rng(L.seed + 3);
    L.veils = VEILS.map(function (v) {
      return { def: v, tex: tileCanvas(N, L.seed + v.seed, v.size, v.period, v.oct, function (x) {
        var a = sstep(v.lo, v.hi, x);
        return [v.rgb[0] + (x - 0.5) * 30 | 0, v.rgb[1] + (x - 0.5) * 26 | 0, v.rgb[2] + (x - 0.5) * 20 | 0, a * 255 | 0];
      }) };
    });
    // 地面沙尘积层纹理：波纹状沙痕（横向条纹被噪波扭曲）
    L.duneTex = tileCanvas(N, L.seed + 51, 128, 4, 4, function (v, x, y) {
      var rip = 0.5 + 0.5 * Math.sin((y / 128) * Math.PI * 2 * 12 + v * 9);
      var a = sstep(0.25, 0.75, v) * (0.55 + 0.45 * rip);
      return [196 + 30 * rip | 0, 154 + 24 * rip | 0, 98 + 16 * rip | 0, a * 255 | 0];
    });
    for (var i = 0; i < MAXP; i++) L.pool.push({ x: r(), y: r(), z: r(), ph: r() * 50, init: false });
    for (var j = 0; j < STREAKS; j++) L.streaks.push({ x: r(), y: r(), len: 40 + r() * 140, life: r(), sp: 0.6 + r() * 0.8, init: false });
  }
  // ---------------------------------------------------------------- 推进
  function update(L, st, dt) {
    var N = L.N, it = clamp01(st.intensity == null ? 0.5 : st.intensity);
    L.state = st; L.t += dt;
    var want = st.kind === 'sandstorm' ? 1 : 0;
    L.active += (want - L.active) * Math.min(1, dt * 3);
    if (!L.started) { L.active = want; L.started = true; }
    L.it = it;
    var w = st.wind || {}, ang = (w.dir_deg == null ? 90 : w.dir_deg) * Math.PI / 180;
    var sp = Math.max(0.25, clamp01(w.speed == null ? 0.6 : w.speed));
    // 阵风：低频噪波，沙暴里一阵一阵地压过来
    L.gust = 1 + (N.fbm2(L.seed + 9, L.t * 0.3, 1.7, 3) - 0.5) * 1.4 * (0.3 + clamp01(w.gust || 0));
    L.wx = Math.sin(ang); L.wy = -Math.cos(ang) * 0.5;          // 斜俯视：纵向位移压扁
    var len = Math.sqrt(L.wx * L.wx + L.wy * L.wy) || 1; L.wx /= len; L.wy /= len;
    L.speed = (160 + 900 * sp * (0.4 + 0.6 * it)) * L.gust;     // px/s
    L.off += L.speed * dt;
    L.vis = st.visibility == null ? 1 - it * 0.75 : clamp01(st.visibility);
    var W = L.W, H = L.H, M = 30;
    L.n = Math.round(MAXP * (0.15 + 0.85 * it) * L.active);
    for (var i = 0; i < L.n; i++) {
      var p = L.pool[i];
      if (!p.init) { p.x = p.x * (W + 2 * M) - M; p.y = p.y * (H + 2 * M) - M; p.init = true; }
      var f = 0.5 + p.z;                                          // 近处粒子更快
      var bob = (N.noise2(L.seed + 21, p.ph + L.t * 1.3, p.z * 9) - 0.5) * 90;
      p.x += L.wx * L.speed * f * dt; p.y += (L.wy * L.speed * f + bob + 12) * dt;
      if (p.x > W + M) p.x -= W + 2 * M; else if (p.x < -M) p.x += W + 2 * M;
      if (p.y > H + M) p.y -= H + 2 * M; else if (p.y < -M) p.y += H + 2 * M;
    }
    L.ns = Math.round(STREAKS * sstep(0.05, 0.9, it) * L.active);
    for (var j = 0; j < L.ns; j++) {
      var s = L.streaks[j];
      if (!s.init) { s.x = s.x * W; s.y = s.y * H; s.init = true; }
      s.life += dt * s.sp * 0.45;
      if (s.life >= 1) { s.life -= 1; s.x = N.rng(L.seed + j * 31 + (L.t * 10 | 0))() * W; s.y = N.rng(L.seed + j * 17 + (L.t * 7 | 0))() * H; }
      s.x += L.wx * L.speed * 0.7 * s.sp * dt; s.y += L.wy * L.speed * 0.7 * s.sp * dt;
      if (s.x > W + 200) s.x -= W + 400; else if (s.x < -200) s.x += W + 400;
      if (s.y > H + 40) s.y -= H + 80; else if (s.y < -40) s.y += H + 80;
    }
    // 地面积沙：随强度累积（这里直接用强度近似；规范 ground 里没有沙尘累积量）
    var k = Math.round(it * L.active * 20) / 20;
    if (k !== L.bakedK || L.bakedId !== L.sceneId) bakeGround(L, k);
  }
  function bakeGround(L, k) {
    L.bakedK = k; L.bakedId = L.sceneId;
    var W = L.W, H = L.H, dpr = L.dpr, cw = Math.ceil(W * dpr), ch = Math.ceil(H * dpr);
    if (!L.gc || L.gc.width !== cw || L.gc.height !== ch) L.gc = canvas(cw, ch);
    var g = L.gc.getContext('2d');
    g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, cw, ch);
    if (k <= 0.01) return;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    var sc = L.scene || {};
    // 底层：整体蒙一层薄黄土；上层：沙痕纹理，强度越高越连片
    g.globalAlpha = 0.12 + 0.22 * k; g.fillStyle = '#c9a26a'; g.fillRect(0, 0, W, H);
    g.globalAlpha = 0.25 + 0.55 * k; drawTiled(g, L.duneTex, 2.6, 1.3, 0, 0, W, H);
    // 道路积沙更多（车辙槽里存沙）
    g.globalAlpha = 0.2 * k; g.fillStyle = '#d8b47c';
    (sc.ground || []).forEach(function (r) { g.fillRect(r[0], r[1], r[2], r[3]); });
    // 水面与建筑主体不积沙（建筑立面挖掉，屋顶保留一层薄沙）
    g.globalAlpha = 1; g.globalCompositeOperation = 'destination-out';
    (sc.water || []).forEach(function (r) { g.fillRect(r[0], r[1], r[2], r[3]); });
    // 有前景剪影就按剪影挖（立面不积沙，保留 25% 当屋顶薄沙）；没有就不挖——包围盒上方是空白，按盒挖会露出浅色矩形
    if (sc.occluder && sc.occluder.width) { g.globalAlpha = 0.75; g.drawImage(sc.occluder, 0, 0, W, H); }
    g.globalCompositeOperation = 'source-over'; g.globalAlpha = 1;
  }

  // ---------------------------------------------------------------- 绘制
  function drawGround(L, ctx) {
    if (!L.gc || L.bakedK <= 0.01) return;
    ctx.save(); ctx.drawImage(L.gc, 0, 0, L.W, L.H); ctx.restore();
  }
  var GRAIN_RGB = ['150,104,58', '196,150,92', '232,200,148'];
  function drawPrecip(L, ctx) {
    var a = L.active, n = L.n, pool = L.pool, wx = L.wx, wy = L.wy;
    ctx.save(); ctx.lineCap = 'round';
    // 贴地流沙线：顺风的波浪细线，淡入淡出
    var N = L.N;
    ctx.strokeStyle = 'rgba(236,206,150,1)'; ctx.lineWidth = 1.3;
    for (var j = 0; j < L.ns; j++) {
      var s = L.streaks[j], fade = Math.sin(Math.PI * s.life);
      ctx.globalAlpha = 0.45 * fade * a * (0.4 + 0.6 * L.it);
      ctx.beginPath();
      for (var k = 0; k <= 8; k++) {
        var t = k / 8, x = s.x - wx * s.len * t, y = s.y - wy * s.len * t;
        var off = (N.noise2(L.seed + 77 + j, t * 3 + L.t * 2, j) - 0.5) * 10;
        x += -wy * off; y += wx * off;
        if (k) ctx.lineTo(x, y); else ctx.moveTo(x, y);
      }
      ctx.stroke();
    }
    // 细沙粒子：按景深分三批，每批一次 stroke；长度 = 速度造成的运动拖影
    for (var b = 0; b < 3; b++) {
      var z0 = b / 3, z1 = (b + 1) / 3, len = (0.006 + 0.012 * z1) * L.speed;
      ctx.strokeStyle = 'rgb(' + GRAIN_RGB[b] + ')'; ctx.lineWidth = 0.8 + b * 0.6;
      ctx.globalAlpha = (0.35 + 0.25 * b) * a;
      ctx.beginPath();
      for (var i = 0; i < n; i++) {
        var p = pool[i];
        if (p.z < z0 || p.z >= z1) continue;
        ctx.moveTo(p.x, p.y); ctx.lineTo(p.x - wx * len, p.y - wy * len);
      }
      ctx.stroke();
    }
    ctx.restore();
  }
  function drawVeil(L, ctx) {
    var W = L.W, H = L.H, a = L.active, it = L.it, thick = clamp01((1 - L.vis) * 0.5 + it * 0.1) * a;
    ctx.save();
    // 整体偏黄褐：先正片叠底压暗染色，再盖一层尘雾
    ctx.globalCompositeOperation = 'multiply';
    ctx.fillStyle = 'rgba(222,178,118,' + (0.2 + 0.4 * it) * a + ')'; ctx.fillRect(0, 0, W, H);
    ctx.globalCompositeOperation = 'source-over';
    var gr = ctx.createLinearGradient(0, 0, 0, H);
    gr.addColorStop(0, 'rgba(206,160,102,' + Math.min(0.85, thick * 0.78) + ')');
    gr.addColorStop(0.55, 'rgba(200,152,94,' + thick * 0.34 + ')');
    gr.addColorStop(1, 'rgba(192,144,88,' + thick * 0.16 + ')');
    ctx.fillStyle = gr; ctx.fillRect(0, 0, W, H);
    // 三层尘幕：各自速度不同，沿风向平移
    for (var i = 0; i < L.veils.length; i++) {
      var v = L.veils[i], d = v.def, o = L.off * d.speed;
      ctx.globalAlpha = Math.min(1, d.a * (0.15 + 0.55 * thick) * (i === 2 ? 0.3 + 0.5 * it : 1));
      drawTiled(ctx, v.tex, d.sx, d.sy, -L.wx * o + i * 211, -L.wy * o + i * 97, W, H);
    }
    ctx.restore();
  }
  root.WeatherFX_sand = { create: create, kinds: ['sandstorm'] };
})(typeof window !== 'undefined' ? window : this);
