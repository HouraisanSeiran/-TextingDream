/*
 * 织梦 · 天气美术：雾（kind = fog，以及任何 state.fog > 0 的天气）
 * window.WeatherFX_fog；接口见 docs/weather-spec.md 第 3 节。只画 pass = 'fog'。
 * 做法：低分辨率 fbm3 雾场（第三维是时间）分帧算出下一帧目标、与当前帧交叉淡化，
 * 放大到四分之一分辨率离屏画布，用预烘细节纹理挖出丝缕，再整体放大贴到屏幕。
 */
(function (root) {
  'use strict';
  var CELL = 10;          // 雾场一个采样格 = 10 CSS px
  var PERIOD = 0.7;       // 每 0.7 s 算完一张新雾场
  var Q = 4;              // 离屏合成画布的降采样倍数

  function clamp01(x) { return x < 0 ? 0 : x > 1 ? 1 : x; }
  function sstep(a, b, x) { var t = clamp01((x - a) / (b - a)); return t * t * (3 - 2 * t); }
  function canvas(w, h) {
    var c = document.createElement('canvas');
    c.width = Math.max(1, Math.ceil(w)); c.height = Math.max(1, Math.ceil(h));
    return c;
  }
  function fogAmount(st) {
    var f = clamp01(st.fog || 0);
    if (st.kind === 'fog') f = Math.max(f, clamp01(st.intensity == null ? 0.5 : st.intensity));
    return f;
  }
  /** 白天程度 0..1，按日出日落平滑过渡；用于决定灯光是否亮、晕光多强 */
  function dayness(st) {
    var t = st.time || {}, h = t.hour == null ? 12 : t.hour, sr = t.sunrise || 6, ss = t.sunset || 18;
    return sstep(sr - 0.7, sr + 0.8, h) * (1 - sstep(ss - 0.8, ss + 0.7, h));
  }

  function create(opts) {
    opts = opts || {};
    var N = opts.noise || root.WeatherNoise;
    if (!N) throw new Error('WeatherFX_fog 需要 WeatherNoise');
    var L = { N: N, seed: (opts.seed >>> 0) || 1, W: 1, H: 1, dpr: 1, t: 0, state: null, scene: null,
      amt: 0, shown: 0, sceneId: 0, lowId: -1, gw: 0, gh: 0, cur: null, nxt: null, row: 0, phase: 0,
      z: 0, drift: 0, lights: [] };
    initTextures(L);
    return {
      resize: function (w, h, dpr) { L.W = w; L.H = h; L.dpr = dpr || 1; L.sceneId++; },
      setScene: function (scene) { L.scene = scene || null; L.sceneId++; },
      update: function (state, dt) { update(L, state || {}, Math.min(0.1, Math.max(0, dt || 0))); },
      draw: function (ctx, pass) { if (pass === 'fog' && L.state) drawFog(L, ctx); },
      dispose: function () { L.cur = L.nxt = L.low = null; L.scene = null; L.tex = {}; },
      kinds: ['fog'],
      _debug: L
    };
  }
  function initTextures(L) {
    var N = L.N, size = 128, t = N.tile(L.seed + 71, size, 6, 4);
    // 细节"洞"：值高处 alpha 高，用 destination-out 从雾里挖掉，形成丝缕
    var c = canvas(size, size), g = c.getContext('2d'), img = g.createImageData(size, size);
    for (var i = 0; i < size * size; i++) {
      img.data[i * 4 + 3] = Math.round(sstep(0.5, 0.85, t[i] / 255) * 255);
    }
    g.putImageData(img, 0, 0);
    L.tex = { holes: c };
    // 灯光晕：暖色径向渐变
    var s = 128, h = canvas(s, s), hg = h.getContext('2d'), gr = hg.createRadialGradient(64, 64, 0, 64, 64, 64);
    gr.addColorStop(0, 'rgba(255,226,170,0.9)'); gr.addColorStop(0.25, 'rgba(255,208,140,0.45)');
    gr.addColorStop(0.6, 'rgba(255,196,128,0.12)'); gr.addColorStop(1, 'rgba(255,190,120,0)');
    hg.fillStyle = gr; hg.fillRect(0, 0, s, s);
    L.tex.halo = h;
  }
  /** 低洼度：水面附近最高、空地道路居中、建筑上半部（屋顶露出雾面）最低。场景变化时重算。 */
  function bakeLow(L) {
    var sc = L.scene || {}, water = sc.water || [], ground = sc.ground || [], bs = sc.buildings || [];
    var gw = Math.ceil(L.W / CELL) + 2, gh = Math.ceil(L.H / CELL) + 2, low = new Float32Array(gw * gh);
    for (var j = 0; j < gh; j++) for (var i = 0; i < gw; i++) {
      var x = (i - 0.5) * CELL, y = (j - 0.5) * CELL, v = 0.3, k;
      for (k = 0; k < water.length; k++) {
        var r = water[k], dx = Math.max(r[0] - x, 0, x - r[0] - r[2]), dy = Math.max(r[1] - y, 0, y - r[1] - r[3]);
        v = Math.max(v, 1 - Math.sqrt(dx * dx + dy * dy) / 150);
      }
      for (k = 0; k < ground.length && v < 0.5; k++) {
        var gr = ground[k];
        if (x >= gr[0] && x < gr[0] + gr[2] && y >= gr[1] && y < gr[1] + gr[3]) v = 0.5;
      }
      for (k = 0; k < bs.length; k++) {
        var b = bs[k], top = b.roofY == null ? b.y : b.roofY, mid = top + (b.y + b.h - top) * 0.55;
        if (x > b.x + 4 && x < b.x + b.w - 4 && y > top - 6 && y < mid) v -= 0.45 * sstep(top - 6, top + 10, y);
      }
      low[j * gw + i] = v;
    }
    L.low = low; L.gw = gw; L.gh = gh; L.lowId = L.sceneId;
    L.row = 0; L.phase = 0;
    L.comp = canvas(Math.ceil(L.W / Q), Math.ceil(L.H / Q));
  }
  // ---------------------------------------------------------------- 雾场：分帧计算
  /** 算第 j 行雾场写进 img；d 为 fbm3 密度，叠加低洼度，阈值随雾量下降（雾量大则连成片） */
  function fieldRow(L, img, j, z, drift) {
    var N = L.N, gw = L.gw, low = L.low, a = L.amt, d = img.data;
    var th = 0.62 - a * 0.5, soft = 0.22 + a * 0.18;
    for (var i = 0; i < gw; i++) {
      var x = (i - 0.5) * CELL - drift, y = (j - 0.5) * CELL;
      // 横向拉长的 fbm3（3/4 视角下雾带是扁的），第三维 z 让形状缓慢翻涌
      var n = N.fbm3(L.seed + 5, x / 260, y / 120, z, 3);
      var lw = low[j * gw + i];
      var v = n * 0.75 + lw * (0.55 - 0.25 * a);
      var al = sstep(th, th + soft, v) * (0.35 + 0.65 * a);
      var o = (j * gw + i) * 4;
      d[o] = 226 + 14 * n; d[o + 1] = 232 + 12 * n; d[o + 2] = 238 + 10 * n;
      d[o + 3] = Math.round(clamp01(al) * 255);
    }
  }
  function fullField(L, buf) {
    for (var j = 0; j < L.gh; j++) fieldRow(L, buf.img, j, L.z, L.drift);
    buf.c.getContext('2d').putImageData(buf.img, 0, 0); buf.drift = L.drift;
  }
  function makeBuf(L) {
    var c = canvas(L.gw, L.gh);
    return { c: c, img: c.getContext('2d').createImageData(L.gw, L.gh), drift: 0 };
  }
  function update(L, st, dt) {
    L.state = st; L.t += dt;
    var target = fogAmount(st);
    L.amt += (target - L.amt) * Math.min(1, dt * 2);
    if (!L.started) { L.amt = target; L.started = true; }
    L.vis = st.visibility == null ? 1 - L.amt * 0.8 : clamp01(st.visibility);
    L.day = dayness(st);
    var w = st.wind || {}, ang = (w.dir_deg || 90) * Math.PI / 180, sp = clamp01(w.speed || 0);
    L.vx = Math.sin(ang) * (6 + 40 * sp);           // 雾漂得很慢
    L.drift += L.vx * dt;
    L.z += dt * 0.05 * (1 + sp);
    if (L.amt <= 0.005) return;
    if (L.lowId !== L.sceneId || !L.bufs) {
      bakeLow(L);
      L.bufs = [makeBuf(L), makeBuf(L), makeBuf(L)];
      fullField(L, L.bufs[0]); fullField(L, L.bufs[1]);
      L.row = 0; L.phase = 0; L.bakedAmt = L.amt;
    }
    // 每帧算若干行进 work 缓冲；PERIOD 内算完，然后轮换 prev ← cur ← work
    L.phase += dt / PERIOD;
    var want = Math.min(L.gh, Math.ceil(L.gh * L.phase));
    var work = L.bufs[2];
    if (L.row === 0) { work.z = L.z + 0.05 * PERIOD; work.drift = L.drift + L.vx * PERIOD; }
    while (L.row < want) { fieldRow(L, work.img, L.row, work.z, work.drift); L.row++; }
    if (L.phase >= 1) {
      work.c.getContext('2d').putImageData(work.img, 0, 0);
      L.bufs = [L.bufs[1], work, L.bufs[0]];
      L.row = 0; L.phase = 0;
    }
  }

  // ---------------------------------------------------------------- 绘制
  function drawFog(L, ctx) {
    var a = L.amt;
    if (a <= 0.005 || !L.bufs) return;
    var W = L.W, H = L.H, cw = L.comp.width, ch = L.comp.height, g = L.comp.getContext('2d');
    var p = L.phase, prev = L.bufs[0], cur = L.bufs[1], s = CELL / Q;
    g.setTransform(1, 0, 0, 1, 0, 0); g.globalCompositeOperation = 'source-over';
    g.clearRect(0, 0, cw, ch); g.imageSmoothingEnabled = true;
    // 交叉淡化：雾场随风平移（当前漂移 - 该缓冲计算时的漂移）
    // 'lighter' 叠加预乘色：结果正好是 (1-p)·prev + p·cur，轮换缓冲时不跳变
    var k = sstep(0, 1, p);
    g.globalAlpha = 1 - k;
    g.drawImage(prev.c, (L.drift - prev.drift - CELL) / Q, -CELL / Q, L.gw * s, L.gh * s);
    g.globalCompositeOperation = 'lighter'; g.globalAlpha = k;
    g.drawImage(cur.c, (L.drift - cur.drift - CELL) / Q, -CELL / Q, L.gw * s, L.gh * s);
    // 细节丝缕：两层可平铺噪波以不同速度挖洞
    g.globalCompositeOperation = 'destination-out';
    g.globalAlpha = 0.55 - 0.25 * a; tiled(g, L.tex.holes, 2.2, -L.drift * 1.6 / Q, L.t * 1.5 / Q, cw, ch);
    g.globalAlpha = 0.35 - 0.15 * a; tiled(g, L.tex.holes, 1.1, -L.drift * 2.6 / Q + 40, -L.t * 2 / Q, cw, ch);
    g.globalCompositeOperation = 'source-over';
    ctx.save();
    // 远处（画面上方）整体发白：能见度越低越白
    var far = clamp01((1 - L.vis) * 1.05) * Math.min(1, a * 1.6);
    if (far > 0.01) {
      var gr = ctx.createLinearGradient(0, 0, 0, H);
      gr.addColorStop(0, 'rgba(222,228,234,' + Math.min(0.9, far * 0.85) + ')');
      gr.addColorStop(0.5, 'rgba(222,228,234,' + far * 0.42 + ')');
      gr.addColorStop(1, 'rgba(222,228,234,' + far * 0.16 + ')');
      ctx.fillStyle = gr; ctx.fillRect(0, 0, W, H);
    }
    ctx.globalAlpha = Math.min(1, 0.55 + a * 0.6);
    ctx.drawImage(L.comp, 0, 0, cw * Q, ch * Q);
    drawHalos(L, ctx);
    ctx.restore();
  }
  function tiled(g, tex, scale, ox, oy, W, H) {
    var s = tex.width * scale, x0 = -(((ox % s) + s) % s), y0 = -(((oy % s) + s) % s);
    for (var y = y0; y < H; y += s) for (var x = x0; x < W; x += s) g.drawImage(tex, x, y, s + 0.5, s + 0.5);
  }
  /** 灯光在雾里晕开：夜间强、白天只剩一圈淡暖色；雾越浓晕越大越软 */
  function drawHalos(L, ctx) {
    var lights = (L.scene && L.scene.lights) || [], k = (1 - L.day * 0.85) * Math.min(1, L.amt * 1.4);
    if (!lights.length || k < 0.02) return;
    ctx.globalCompositeOperation = 'lighter';
    var base = 26 + 70 * L.amt, halo = L.tex.halo;
    for (var i = 0; i < lights.length; i++) {
      var l = lights[i], f = l.kind === 'fire' ? 1.4 : l.kind === 'lamp' ? 1.1 : 0.8;
      var fl = l.kind === 'fire' ? 0.85 + 0.15 * L.N.noise2(L.seed + i, L.t * 3, 0) : 1;
      var r = base * f * fl;
      ctx.globalAlpha = Math.min(1, 0.55 * k * fl);
      ctx.drawImage(halo, l.x - r, l.y - r * 0.8, r * 2, r * 1.6);
    }
    ctx.globalCompositeOperation = 'source-over';
  }
  root.WeatherFX_fog = { create: create, kinds: ['fog'] };
})(typeof window !== 'undefined' ? window : this);
