/*
 * 织梦 · 天气美术：雪 / 暴风雪 / 雨夹雪（雪部分）
 * window.WeatherFX_snow；接口见 docs/weather-spec.md 第 3 节。
 * pass：ground（地面积雪、屋顶积雪、水面结冰）、precip（三层雪花）、fog（暴风雪白茫）。
 * 调用方负责 ctx.setTransform(dpr,0,0,dpr,0,0)，本模块一律按 CSS 像素坐标作画。
 */
(function (root) {
  'use strict';
  var KINDS = { snow: 1, blizzard: 1, sleet: 1 };
  var BAKE = 2;          // 积雪遮罩的降采样倍数（场景像素 / 遮罩像素）

  function clamp01(x) { return x < 0 ? 0 : x > 1 ? 1 : x; }
  function sstep(a, b, x) { var t = clamp01((x - a) / (b - a)); return t * t * (3 - 2 * t); }
  function canvas(w, h) {
    var c = document.createElement('canvas');
    c.width = Math.max(1, Math.ceil(w)); c.height = Math.max(1, Math.ceil(h));
    return c;
  }
  function windVec(state) {
    var w = (state && state.wind) || {}, a = (w.dir_deg || 0) * Math.PI / 180;
    return { x: Math.sin(a), y: -Math.cos(a), s: clamp01(w.speed || 0), g: clamp01(w.gust || 0) };
  }
  /** 双线性采样一张 size×size 的可平铺 Uint8 噪波，返回 [0,1] */
  function sampler(tex, size) {
    return function (u, v) {
      u = ((u % size) + size) % size; v = ((v % size) + size) % size;
      var x0 = u | 0, y0 = v | 0, fx = u - x0, fy = v - y0, x1 = (x0 + 1) % size, y1 = (y0 + 1) % size;
      var a = tex[y0 * size + x0], b = tex[y0 * size + x1], c = tex[y1 * size + x0], d = tex[y1 * size + x1];
      return ((a + (b - a) * fx) * (1 - fy) + (c + (d - c) * fx) * fy) / 255;
    };
  }
  /** 一张软圆点精灵（雪花 / 失焦雪片） */
  function dotSprite(r, soft, rgb) {
    var s = Math.ceil(r * 2 + 2), c = canvas(s, s), g = c.getContext('2d'), m = s / 2;
    var gr = g.createRadialGradient(m, m, 0, m, m, r);
    gr.addColorStop(0, 'rgba(' + rgb + ',1)');
    gr.addColorStop(clamp01(1 - soft), 'rgba(' + rgb + ',0.85)');
    gr.addColorStop(1, 'rgba(' + rgb + ',0)');
    g.fillStyle = gr; g.fillRect(0, 0, s, s);
    return c;
  }
  /** 带一圈淡蓝灰描边的雪花：落在白色积雪上也能看出来 */
  function flakeSprite(r, soft) {
    var s = Math.ceil(r * 2 + 4), c = canvas(s, s), g = c.getContext('2d'), m = s / 2;
    var sh = g.createRadialGradient(m + 0.6, m + 0.8, 0, m + 0.6, m + 0.8, r + 1.2);
    sh.addColorStop(0.5, 'rgba(90,110,140,0.32)'); sh.addColorStop(1, 'rgba(90,110,140,0)');
    g.fillStyle = sh; g.fillRect(0, 0, s, s);
    g.drawImage(dotSprite(r, soft, '255,255,255'), m - Math.ceil(r * 2 + 2) / 2, m - Math.ceil(r * 2 + 2) / 2);
    return c;
  }
  /** 一张可平铺的 RGBA 纹理：fn(v, x, y) 返回 [r,g,b,a]，v 来自 WeatherNoise.tile */
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
  /** 把一张可平铺纹理按 scale 放大、偏移 (ox,oy) 铺满 W×H */
  function drawTiled(ctx, tex, scale, ox, oy, W, H) {
    var s = tex.width * scale, x0 = -(((ox % s) + s) % s), y0 = -(((oy % s) + s) % s);
    for (var y = y0; y < H; y += s) for (var x = x0; x < W; x += s) ctx.drawImage(tex, x, y, s + 0.5, s + 0.5);
  }

  function create(opts) {
    opts = opts || {};
    var N = opts.noise || root.WeatherNoise;
    if (!N) throw new Error('WeatherFX_snow 需要 WeatherNoise');
    var seed = (opts.seed >>> 0) || 1;
    var tint = opts.tint !== false;    // 雪天偏冷提亮；接入 daylight 后可关掉避免重复调色
    var L = {
      N: N, seed: seed, tint: tint, W: 1, H: 1, dpr: 1, t: 0, state: null, scene: null,
      wind: { x: 0, y: 1, s: 0, g: 0 }, gust: 1, active: 0, bliz: 0, sleet: 0,
      layers: [], sprites: {}, tex: {}, bakedCover: -1, bakedSceneId: -1, sceneId: 0,
      field: null, roofs: [], ice: 0, iceTex: null, fogTex: null
    };
    initTextures(L);
    initPools(L);
    return {
      resize: function (w, h, dpr) { L.W = w; L.H = h; L.dpr = dpr || 1; L.sceneId++; },
      setScene: function (scene) { L.scene = scene || null; L.sceneId++; },
      update: function (state, dt) { update(L, state || {}, Math.min(0.1, Math.max(0, dt || 0))); },
      draw: function (ctx, pass) {
        if (!L.state) return;
        if (pass === 'ground') drawGround(L, ctx);
        else if (pass === 'precip') drawPrecip(L, ctx);
        else if (pass === 'fog') drawFog(L, ctx);
      },
      dispose: function () { L.layers = []; L.field = null; L.roofs = []; L.tex = {}; L.sprites = {}; L.scene = null; },
      _debug: L
    };
  }
  // ---------------------------------------------------------------- 预烘纹理
  var TS = 256;
  function initTextures(L) {
    var N = L.N, s = L.seed;
    // 积雪场用的三张可平铺噪波：大块起伏、细颗粒、扭曲偏移
    L.nBig = sampler(N.tile(s + 11, TS, 4, 4), TS);
    L.nFine = sampler(N.tile(s + 23, TS, 16, 3), TS);
    L.nSpeck = sampler(N.tile(s + 29, TS, 64, 2), TS);
    L.nWx = sampler(N.tile(s + 37, TS, 6, 3), TS);
    L.nWy = sampler(N.tile(s + 41, TS, 6, 3), TS);
    // 暴风雪雾团：两张白色软雾，alpha 来自 fbm
    L.tex.fogA = tileCanvas(N, s + 51, 128, 4, 5, function (v) {
      var a = sstep(0.35, 0.85, v); return [244, 248, 255, Math.round(a * 255)];
    });
    L.tex.fogB = tileCanvas(N, s + 67, 128, 8, 4, function (v) {
      var a = sstep(0.45, 0.9, v); return [236, 242, 252, Math.round(a * 220)];
    });
    L.tex.ice = bakeIce(L);
    L.sprites.far = dotSprite(2.0, 0.55, '236,242,252');
    L.sprites.mid = flakeSprite(3.2, 0.45);
    L.sprites.near = flakeSprite(5.2, 0.4);
    L.sprites.bokeh = dotSprite(24, 0.9, '255,255,255');
    L.sprites.sleet = dotSprite(2.2, 0.5, '214,226,236');
  }
  /** 冰面纹理：噪波斑驳的冰色 + 带抖动的裂纹（裂纹在边界处环绕绘制，保证可平铺） */
  function bakeIce(L) {
    var N = L.N, size = 192;
    var c = tileCanvas(N, L.seed + 83, size, 6, 4, function (v) {
      var k = sstep(0.2, 0.8, v);
      return [Math.round(196 + 40 * k), Math.round(218 + 28 * k), Math.round(230 + 22 * k), 255];
    });
    var g = c.getContext('2d'), r = N.rng(L.seed + 97);
    g.lineCap = 'round';
    for (var i = 0; i < 9; i++) {
      var x = r() * size, y = r() * size, ang = r() * Math.PI * 2, pts = [[x, y]];
      var n = 4 + (r() * 6 | 0);
      for (var k = 0; k < n; k++) {
        ang += (r() - 0.5) * 1.1; var len = 8 + r() * 20;
        x += Math.cos(ang) * len; y += Math.sin(ang) * len; pts.push([x, y]);
      }
      for (var ox = -1; ox <= 1; ox++) for (var oy = -1; oy <= 1; oy++) {
        [[ 'rgba(255,255,255,0.75)', 1.6, 0.8 ], [ 'rgba(92,128,150,0.55)', 0.8, 0 ]].forEach(function (st) {
          g.strokeStyle = st[0]; g.lineWidth = st[1]; g.beginPath();
          pts.forEach(function (p, j) {
            var px = p[0] + ox * size, py = p[1] + oy * size + st[2];
            if (j) g.lineTo(px, py); else g.moveTo(px, py);
          });
          g.stroke();
        });
      }
    }
    return c;
  }

  // ---------------------------------------------------------------- 雪花对象池
  // 景深层：max = 满强度数量；r = 半径缩放；v = 下落速度 px/s；a = 不透明度；wind = 受风程度
  var LAYERS = [
    { name: 'far', max: 650, r: [0.55, 0.9], v: [26, 42], a: 0.55, wind: 0.45, sway: 6, from: 0.0 },
    { name: 'mid', max: 300, r: [0.7, 1.05], v: [55, 80], a: 0.85, wind: 0.75, sway: 12, from: 0.0 },
    { name: 'near', max: 90, r: [0.7, 1.1], v: [105, 150], a: 0.95, wind: 1.0, sway: 20, from: 0.15 },
    { name: 'bokeh', max: 14, r: [0.6, 1.2], v: [190, 260], a: 0.22, wind: 1.3, sway: 30, from: 0.4 }
  ];
  function initPools(L) {
    var r = L.N.rng(L.seed + 5);
    L.layers = LAYERS.map(function (def) {
      var pool = [];
      for (var i = 0; i < def.max; i++) {
        pool.push({ x: r(), y: r(), s: def.r[0] + r() * (def.r[1] - def.r[0]),
          v: def.v[0] + r() * (def.v[1] - def.v[0]), ph: r() * 100, k: r(), init: false });
      }
      return { def: def, pool: pool, n: 0 };
    });
  }

  // ---------------------------------------------------------------- 推进
  function update(L, st, dt) {
    var N = L.N, kind = st.kind || 'clear', it = clamp01(st.intensity || 0);
    L.state = st; L.t += dt;
    L.wind = windVec(st);
    // 阵风：低频噪波调制，gust 越大起伏越大
    L.gust = 1 + (N.fbm2(L.seed + 3, L.t * 0.35, 0.5, 3) - 0.5) * 2.2 * (0.25 + L.wind.g);
    var want = KINDS[kind] ? 1 : 0;
    L.active += (want - L.active) * Math.min(1, dt * 3);
    if (!L.initDone) { L.active = want; L.initDone = true; }
    L.it = it;
    L.bliz = kind === 'blizzard' ? 0.55 + 0.45 * it : 0;
    L.sleet = kind === 'sleet' ? 1 : 0;
    L.vis = st.visibility == null ? 1 - it * 0.6 : clamp01(st.visibility);
    // 横向风速（px/s）：常规雪轻飘，暴风雪横飞
    var ws = L.wind.s * L.gust;
    L.vx = L.wind.x * (40 + 220 * ws + L.bliz * (260 + 420 * ws));
    L.vyWind = L.wind.y * (20 + 80 * ws) * (1 + L.bliz);
    var W = L.W, H = L.H, M = 40;
    for (var li = 0; li < L.layers.length; li++) {
      var lay = L.layers[li], def = lay.def;
      var dens = it <= def.from ? 0 : sstep(def.from, 1, it) * 0.85 + 0.15 * (it > def.from ? 1 : 0);
      if (def.name === 'bokeh') dens = sstep(0.4, 1, it) * (0.4 + 0.6 * L.bliz);
      if (L.sleet) dens *= def.name === 'bokeh' ? 0 : 0.55;
      lay.n = Math.round(def.max * dens * L.active * (L.bliz ? 1.25 : 1));
      if (lay.n > def.max) lay.n = def.max;
      var fall = (1 + it * 0.6) * (L.sleet ? 1.9 : 1) * (1 - L.bliz * 0.25);
      for (var i = 0; i < lay.n; i++) {
        var p = lay.pool[i];
        if (!p.init) { p.x = p.x * (W + 2 * M) - M; p.y = p.y * (H + 2 * M) - M; p.init = true; }
        // 噪波飘摆：每片雪一条独立的一维噪波轨迹
        var sw = (N.noise2(L.seed + 17 + li, p.ph + L.t * (0.35 + p.k * 0.4), li * 7.3) - 0.5) * 2;
        p.dx = sw * def.sway * (1 - L.bliz * 0.6);
        p.x += (L.vx * def.wind + p.dx * 2.2) * dt;
        p.y += (p.v * fall + L.vyWind * def.wind) * dt;
        if (p.y > H + M) { p.y -= H + 2 * M; p.x = (p.k * 9301 + L.t * 37) % (W + 2 * M) - M; }
        else if (p.y < -M) p.y += H + 2 * M;
        if (p.x > W + M) p.x -= W + 2 * M; else if (p.x < -M) p.x += W + 2 * M;
      }
    }
    var cover = clamp01((st.ground && st.ground.snow_cover) || 0);
    var temp = st.temperature_c == null ? 0 : st.temperature_c;
    L.cover = cover;
    L.ice = sstep(0.35, 0.75, cover) * sstep(1, -5, temp);
    if (Math.abs(cover - L.bakedCover) > 0.008 || Math.abs(L.ice - (L.bakedIce || 0)) > 0.03 ||
        L.bakedSceneId !== L.sceneId) bakeCover(L);
  }
  // ---------------------------------------------------------------- 积雪烘焙（只在 cover / 场景 / 尺寸变化时）
  function sceneRects(L) {
    var sc = L.scene || {};
    return { water: sc.water || [], ground: sc.ground || [], buildings: sc.buildings || [] };
  }
  function inRects(rs, x, y, pad) {
    for (var i = 0; i < rs.length; i++) {
      var r = rs[i];
      if (x >= r[0] - pad && x < r[0] + r[2] + pad && y >= r[1] - pad && y < r[1] + r[3] + pad) return true;
    }
    return false;
  }
  /** 建筑主体对地面积雪的遮挡：返回 0..1（1 = 完全挡住），边缘柔化，左右略内收 */
  function bodyMask(bs, x, y) {
    var m = 0;
    for (var i = 0; i < bs.length; i++) {
      var b = bs[i], ry = b.roofY == null ? b.y : b.roofY;
      if (x < b.x || x > b.x + b.w || y < ry || y > b.y + b.h) continue;
      var ex = Math.min(x - b.x, b.x + b.w - x) / Math.max(4, b.w * 0.1);
      var ey = (b.y + b.h - 3 - y) / 6;
      var v = clamp01(Math.min(ex, ey));
      if (v > m) m = v;
    }
    return m;
  }
  function bakeCover(L) {
    var R = sceneRects(L), W = L.W, H = L.H, cover = L.cover, occ = occluder(L);
    L.bakedCover = cover; L.bakedSceneId = L.sceneId; L.bakedIce = L.ice;
    var mw = Math.ceil(W / BAKE), mh = Math.ceil(H / BAKE), n = mw * mh;
    if (!L.mask || L.mask.width !== mw || L.mask.height !== mh) L.mask = canvas(mw, mh);
    if (!L.vbuf || L.vbuf.length !== n) { L.vbuf = new Float32Array(n); L.sbuf = new Float32Array(n); }
    var g = L.mask.getContext('2d'), img = g.createImageData(mw, mh), d = img.data, V = L.vbuf, S = L.sbuf;
    var sheet = sstep(0.15, 0.8, cover), speck = 1 - sstep(0.05, 0.5, cover);
    var big = L.nBig, fine = L.nFine, spk = L.nSpeck, wx = L.nWx, wy = L.nWy, sc = 0.55 * BAKE / 3;
    var hist = new Uint32Array(256), cnt = 0, k, j, i, rf = roadField(L, R.ground);
    // 第一遍：算积雪势场 = 域扭曲后的大块 fbm + 中频 + 高频星点（低积雪时星点权重高）
    for (j = 0; j < mh; j++) for (i = 0; i < mw; i++) {
      k = j * mw + i;
      var X = i * BAKE, Y = j * BAKE, u = i * sc, v = j * sc;
      if (cover <= 0.001 || inRects(R.water, X, Y, 0)) { V[k] = -1; continue; }
      var du = (wx(u * 0.7, v * 0.7) - 0.5) * 34, dv = (wy(u * 0.7, v * 0.7) - 0.5) * 34;
      var b = big(u + du, v + dv), f = fine(u * 1.7 + du * 0.5, v * 1.7 + dv * 0.5);
      var val = b * (0.3 + 0.5 * sheet) + f * (0.4 - 0.2 * sheet) + spk(u * 2 + du * 0.2, v * 2 + dv * 0.2) * 0.45 * speck;
      val /= 0.7 + 0.3 * sheet + 0.45 * speck;
      // 道路被踩，积得慢：按格平滑插值的道路度（再用扭曲噪波抖动坐标），路边不出直线硬边
      var rd = roadAt(rf, X + du * 2.2, Y + dv * 2.2);
      if (rd > 0) val -= rd * (0.08 + 0.08 * (1 - cover));
      if (!occ) val -= 0.6 * bodyMask(R.buildings, X, Y);
      V[k] = val; S[k] = b - big(u + du + 1.2, v + dv + 1.2);
      hist[Math.max(0, Math.min(255, val * 255 | 0))]++; cnt++;
    }
    // 阈值取分位数：snow_cover 直接对应覆盖面积（0.2≈一成星点，0.5≈四成，0.9≈九成）
    var frac = cover <= 0.001 ? 0 : Math.min(0.985, Math.pow(cover, 1.3) * 1.05), acc = 0, th = 1;
    for (k = 255; k >= 0; k--) { acc += hist[k]; if (acc >= frac * cnt) { th = k / 255; break; } }
    var soft = 0.015 + 0.05 * sheet;
    for (k = 0; k < n; k++) {
      var o = k * 4, w = V[k];
      var a = frac > 0 && w >= 0 ? sstep(th - soft * 0.3, th + soft, w) : 0;
      if (a <= 0.003) { d[o + 3] = 0; continue; }
      // 边缘偏蓝（雪层薄、朝阴），内部近白；势场梯度给出背光面
      var e = clamp01((w - th) / (0.06 + 0.1 * sheet)), sh = clamp01(0.55 + e * 0.5 - S[k] * 5);
      d[o] = 186 + 68 * sh; d[o + 1] = 202 + 52 * sh; d[o + 2] = 226 + 29 * sh;
      d[o + 3] = Math.round(a * 255);
    }
    g.putImageData(img, 0, 0);
    bakeGround(L, R, occ);
  }
  /** 道路度场：每个 cell 一格，落在 scene.ground 矩形里记 1；采样时双线性插值得到 0..1 的柔和过渡 */
  function roadField(L, ground) {
    var c = (L.scene && L.scene.cell) || 48, gw = Math.ceil(L.W / c) + 1, gh = Math.ceil(L.H / c) + 1;
    var f = new Float32Array(gw * gh);
    // 网格原点取第一块地面矩形的余数：城镇被缩放居中后格线不一定落在 0
    var ox = ground.length ? ((ground[0][0] % c) + c) % c : 0, oy = ground.length ? ((ground[0][1] % c) + c) % c : 0;
    ground.forEach(function (r) {
      for (var y = Math.floor((r[1] - oy) / c + 0.01); y < Math.ceil((r[1] + r[3] - oy) / c - 0.01); y++)
        for (var x = Math.floor((r[0] - ox) / c + 0.01); x < Math.ceil((r[0] + r[2] - ox) / c - 0.01); x++)
          if (x >= 0 && y >= 0 && x < gw && y < gh) f[y * gw + x] = 1;
    });
    return { f: f, gw: gw, gh: gh, c: c, ox: ox, oy: oy };
  }
  function roadAt(rf, X, Y) {
    var fx = (X - rf.ox) / rf.c - 0.5, fy = (Y - rf.oy) / rf.c - 0.5, x0 = Math.floor(fx), y0 = Math.floor(fy), tx = fx - x0, ty = fy - y0;
    function g(x, y) { return x < 0 || y < 0 || x >= rf.gw || y >= rf.gh ? 0 : rf.f[y * rf.gw + x]; }
    var v = (g(x0, y0) * (1 - tx) + g(x0 + 1, y0) * tx) * (1 - ty) + (g(x0, y0 + 1) * (1 - tx) + g(x0 + 1, y0 + 1) * tx) * ty;
    return sstep(0.25, 0.85, v);
  }
  /** 可选 scene.occluder：与场景同尺寸（CSS px）的前景剪影画布（建筑、树）。有它就按剪影抠地面积雪、沿剪影上沿堆雪。 */
  function occluder(L) {
    var o = L.scene && L.scene.occluder;
    if (!o || !o.width) return null;
    if (L.occSrc !== o || L.occId !== L.sceneId) {
      var c = canvas(L.W, L.H), g = c.getContext('2d');
      g.drawImage(o, 0, 0, L.W, L.H);
      L.occSrc = o; L.occId = L.sceneId; L.occ = c; L.occA = null;
      try { L.occA = g.getImageData(0, 0, c.width, c.height).data; } catch (e) { L.occA = null; }
    }
    return L.occ;
  }
  /** 把降采样遮罩放大 + 屋顶积雪 + 冰面合成成一张整屏画布，draw 时只需一次 drawImage */
  function bakeGround(L, R, occ) {
    var W = L.W, H = L.H, dpr = L.dpr, cw = Math.ceil(W * dpr), ch = Math.ceil(H * dpr);
    if (!L.gc || L.gc.width !== cw || L.gc.height !== ch) L.gc = canvas(cw, ch);
    var g = L.gc.getContext('2d');
    g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, cw, ch);
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (L.ice > 0.01) drawIce(L, g, R.water);
    if (L.cover > 0.001) {
      g.imageSmoothingEnabled = true;
      g.drawImage(L.mask, 0, 0, L.mask.width * BAKE, L.mask.height * BAKE);
      if (occ) {
        g.globalCompositeOperation = 'destination-out'; g.drawImage(occ, 0, 0, W, H);
        g.globalCompositeOperation = 'source-over';
        if (L.occA) drawCaps(L, g); else drawRoofs(L, g, R.buildings);
      } else drawRoofs(L, g, R.buildings);
    }
  }
  /** 沿前景剪影的上沿逐列堆雪：屋脊、屋檐、烟囱、树冠顶都会自然积雪；厚度随 cover 与噪波起伏 */
  function drawCaps(L, g) {
    var A = L.occA, W = L.occ.width, H = L.occ.height, N = L.N, k = sstep(0.12, 0.8, L.cover);
    if (k <= 0.01) return;
    var c = L.capC && L.capC.width === W && L.capC.height === H ? L.capC : (L.capC = canvas(W, H));
    var cg = c.getContext('2d'), img = cg.createImageData(W, H), d = img.data, fine = L.nFine;
    var base = 1.2 + 8 * k;
    for (var x = 0; x < W; x++) {
      var prev = 0;
      for (var y = 1; y < H; y++) {
        var al = A[(y * W + x) * 4 + 3], up = prev; prev = al;
        if (al < 140 || up >= 140) continue;
        // 上沿：向下铺 t 像素（只铺在剪影内部），顶上再鼓出 1 像素
        var nz = fine(x * 0.35, y * 0.35), t = Math.round(base * (0.45 + 0.9 * nz));
        for (var dy = -1; dy <= t; dy++) {
          var yy = y + dy; if (yy < 0 || yy >= H) continue;
          var p = yy * W + x;
          if (dy >= 0 && A[p * 4 + 3] < 100) break;
          if (dy < 0 && k < 0.45) continue;
          var q = dy / Math.max(1, t), sh = dy < 0 ? 1 : clamp01(1.05 - q * q * 0.8);
          d[p * 4] = 178 + 77 * sh; d[p * 4 + 1] = 196 + 59 * sh; d[p * 4 + 2] = 224 + 31 * sh;
          d[p * 4 + 3] = dy < 0 ? 170 : 255;
        }
        // 剪影内紧接雪下 1 像素一道冷色阴影
        var ps = (y + t + 1) * W + x;
        if (y + t + 1 < H && A[ps * 4 + 3] > 100 && !d[ps * 4 + 3]) { d[ps * 4] = 70; d[ps * 4 + 1] = 90; d[ps * 4 + 2] = 120; d[ps * 4 + 3] = 70; }
      }
    }
    cg.putImageData(img, 0, 0);
    g.globalAlpha = 0.55 + 0.45 * k; g.drawImage(c, 0, 0, L.W, L.H); g.globalAlpha = 1;
  }
  function drawIce(L, g, water) {
    var pat = g.createPattern(L.tex.ice, 'repeat'), a = L.ice;
    water.forEach(function (r) {
      g.save(); g.beginPath(); g.rect(r[0], r[1], r[2], r[3]); g.clip();
      g.globalAlpha = 0.25 + 0.65 * a; g.fillStyle = pat; g.fillRect(r[0], r[1], r[2], r[3]);
      g.restore();
    });
    // 冰面外缘一圈薄雪（只描与非水面相邻的边，相邻水格之间不画线）
    g.save(); g.globalAlpha = 0.6 * a; g.strokeStyle = '#f4f8ff'; g.lineWidth = 4; g.lineCap = 'round';
    g.beginPath();
    water.forEach(function (r) {
      var x = r[0], y = r[1], w = r[2], h = r[3];
      if (!inRects(water, x + w / 2, y - 1, 0)) { g.moveTo(x, y + 2); g.lineTo(x + w, y + 2); }
      if (!inRects(water, x + w / 2, y + h + 1, 0)) { g.moveTo(x, y + h - 2); g.lineTo(x + w, y + h - 2); }
      if (!inRects(water, x - 1, y + h / 2, 0)) { g.moveTo(x + 2, y); g.lineTo(x + 2, y + h); }
      if (!inRects(water, x + w + 1, y + h / 2, 0)) { g.moveTo(x + w - 2, y); g.lineTo(x + w - 2, y + h); }
    });
    g.stroke(); g.restore();
  }
  /** 屋顶积雪：沿 roofY 一条上沿微鼓、下沿噪波起伏（高积雪时带下垂雪檐）的白带 */
  function drawRoofs(L, g, bs) {
    var N = L.N, k = sstep(0.18, 0.75, L.cover);
    if (k <= 0.01) return;
    bs.forEach(function (b, bi) {
      var ry = b.roofY == null ? b.y : b.roofY, inset = Math.max(3, b.w * 0.12);
      var x0 = b.x + inset, x1 = b.x + b.w - inset, span = x1 - x0;
      if (span < 6) return;
      var thick = (2.5 + Math.min(16, (b.h) * 0.09)) * (0.35 + 0.65 * k);
      var steps = Math.max(6, Math.round(span / 4)), top = [], bot = [];
      for (var i = 0; i <= steps; i++) {
        var t = i / steps, x = x0 + span * t, edge = Math.sin(Math.PI * t);
        var nt = N.fbm2(L.seed + 201 + bi, x * 0.09, 0.3, 3), nb = N.fbm2(L.seed + 307 + bi, x * 0.13, 4.1, 3);
        top.push([x, ry + 1.5 - edge * (0.6 + 2.2 * k) * (0.6 + nt)]);
        var drip = sstep(0.62, 0.8, nb) * 7 * sstep(0.55, 1, L.cover);   // 雪檐下垂
        bot.push([x, ry + 1 + thick * edge * (0.55 + 0.7 * nb) + drip * edge]);
      }
      var gr = g.createLinearGradient(0, ry - 3, 0, ry + thick + 6);
      gr.addColorStop(0, '#ffffff'); gr.addColorStop(0.55, '#eef4fc'); gr.addColorStop(1, '#b9cbe2');
      // 先画一道下投阴影，再画雪带本体
      g.save(); g.globalAlpha = 0.28 * k; g.fillStyle = '#4a5f7a';
      polyBand(g, top, bot, 0, 2.2); g.fill(); g.restore();
      g.save(); g.globalAlpha = 0.6 + 0.4 * k; g.fillStyle = gr;
      polyBand(g, top, bot, 0, 0); g.fill();
      g.globalAlpha = 0.7 * k; g.strokeStyle = '#ffffff'; g.lineWidth = 1;
      g.beginPath(); top.forEach(function (p, i) { if (i) g.lineTo(p[0], p[1] + 0.6); else g.moveTo(p[0], p[1] + 0.6); });
      g.stroke(); g.restore();
    });
  }
  function polyBand(g, top, bot, dx, dy) {
    g.beginPath();
    top.forEach(function (p, i) { if (i) g.lineTo(p[0] + dx, p[1] + dy); else g.moveTo(p[0] + dx, p[1] + dy); });
    for (var i = bot.length - 1; i >= 0; i--) g.lineTo(bot[i][0] + dx, bot[i][1] + dy);
    g.closePath();
  }

  // ---------------------------------------------------------------- 绘制
  function drawGround(L, ctx) {
    if (!L.gc || (L.cover <= 0.001 && L.ice <= 0.01)) return;
    ctx.save(); ctx.globalAlpha = 1;
    ctx.drawImage(L.gc, 0, 0, L.W, L.H);
    ctx.restore();
  }
  function drawPrecip(L, ctx) {
    if (L.active <= 0.01) return;
    var bl = L.bliz, sl = L.sleet;
    var vx = L.vx, vy0 = 60, ang = Math.atan2(vy0 + L.vyWind, vx);
    ctx.save();
    for (var li = 0; li < L.layers.length; li++) {
      var lay = L.layers[li], def = lay.def, n = lay.n;
      if (!n) continue;
      var spr = L.sprites[sl && def.name !== 'far' ? 'sleet' : def.name], sw = spr.width, pool = lay.pool;
      ctx.globalAlpha = def.a * L.active * (sl ? 0.8 : 1);
      if (def.name === 'bokeh') { drawBokeh(L, ctx, lay, spr); continue; }
      // 暴风雪 / 雨夹雪：中近景画成顺风的短线（运动模糊），一次 stroke 批量完成
      if ((bl > 0 && def.name !== 'far') || (sl && def.name === 'near')) {
        var len = (bl ? (def.name === 'near' ? 26 : 13) * (0.6 + bl) : 9), ca = Math.cos(ang), sa = Math.sin(ang);
        ctx.strokeStyle = sl ? 'rgba(210,222,234,1)' : 'rgba(250,252,255,1)';
        ctx.lineCap = 'round';
        ctx.lineWidth = def.name === 'near' ? 2.6 : 1.6;
        ctx.beginPath();
        for (var i = 0; i < n; i++) {
          var p = pool[i], l2 = len * p.s;
          ctx.moveTo(p.x, p.y); ctx.lineTo(p.x - ca * l2, p.y - sa * l2);
        }
        ctx.stroke();
        continue;
      }
      for (var j = 0; j < n; j++) {
        var q = pool[j], s = sw * q.s;
        ctx.drawImage(spr, q.x - s / 2, q.y - s / 2, s, s);
      }
    }
    ctx.restore();
  }
  /** 近镜失焦大雪片：大而虚；暴风雪时沿风向拉长成糊镜的雪痕 */
  function drawBokeh(L, ctx, lay, spr) {
    var ang = Math.atan2(60 + L.vyWind, L.vx), str = 1 + L.bliz * 1.8;
    for (var i = 0; i < lay.n; i++) {
      var p = lay.pool[i], s = spr.width * p.s;
      ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(ang); ctx.scale(str, 1 / Math.sqrt(str));
      ctx.drawImage(spr, -s / 2, -s / 2, s, s); ctx.restore();
    }
  }
  function drawFog(L, ctx) {
    var a = L.active;
    if (a <= 0.01) return;
    var W = L.W, H = L.H, it = L.it, bl = L.bliz;
    // 白茫量：能见度越低越白；暴风雪满额，普通雪只给轻微远处发白
    var wo = clamp01((1 - L.vis) * (bl ? 0.62 : 0.4) + bl * 0.06) * a;
    ctx.save();
    if (L.tint) { ctx.globalAlpha = 1; ctx.fillStyle = 'rgba(228,236,250,' + (0.05 + 0.08 * it) * a + ')'; ctx.fillRect(0, 0, W, H); }
    if (wo > 0.01) {
      var gr = ctx.createLinearGradient(0, 0, 0, H);
      gr.addColorStop(0, 'rgba(236,242,250,' + Math.min(0.85, wo * 0.75) + ')');
      gr.addColorStop(0.5, 'rgba(232,239,248,' + wo * 0.3 + ')');
      gr.addColorStop(1, 'rgba(228,236,246,' + wo * 0.12 + ')');
      ctx.fillStyle = gr; ctx.fillRect(0, 0, W, H);
      // 两层预烘雾团随风滚动：大团慢、小团快，叠加出翻滚感
      var t = L.t, sx = L.vx, sy = 18 + L.vyWind * 0.3;
      ctx.globalAlpha = Math.min(1, wo * 0.7);
      drawTiled(ctx, L.tex.fogA, 6, -t * sx * 0.55, -t * sy * 0.4, W, H);
      ctx.globalAlpha = Math.min(1, wo * 0.45);
      drawTiled(ctx, L.tex.fogB, 3.2, -t * sx * 1.05 + 300, -t * sy * 0.8 + 170, W, H);
    }
    ctx.restore();
  }
  root.WeatherFX_snow = { create: create, kinds: Object.keys(KINDS) };
})(typeof window !== 'undefined' ? window : this);
