/*
 * 织梦 · 奇幻天气叠层（魔力风暴 / 灵雾 / 瘴气 / 灰烬雨），挂 window.WeatherFX_fantasy。
 * 本文件是分派核心与共用工具；各 kind 的实现在 fantasy-*.js 里，加载顺序：noise.js → fantasy.js → fantasy-*.js。
 * 接口见 docs/weather-spec.md 第 3 节：create / resize / setScene / update / draw / dispose。
 * 只用 Canvas 2D；逐像素噪波只在低分辨率缓冲上采样预烘纹理（不逐帧调 noise2），再平滑放大。
 */
(function (root) {
  'use strict';
  var KINDS = {};

  // ------------------------------------------------------------------ 小工具
  function clamp(x, a, b) { return x < a ? a : x > b ? b : x; }
  function sstep(a, b, x) { var t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  /** h,s,l ∈ [0,1] → [r,g,b] 0–255 */
  function hsl(h, s, l) {
    h = ((h % 1) + 1) % 1; var a = s * Math.min(l, 1 - l);
    function f(n) { var k = (n + h * 12) % 12; return Math.round(255 * (l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1)))); }
    return [f(0), f(8), f(4)];
  }
  function rgba(c, a) { return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + a + ')'; }
  /** magic 字段（缺省时按强度给默认值）；hue 0 = 紫，0.25 = 青蓝，0.5 = 翠绿，0.75 = 赤橙，1 回到紫 */
  function magic(st, I) {
    var m = (st && st.magic) || {};
    var hue = m.hue == null ? 0 : clamp(m.hue, 0, 1);
    return { strength: m.strength == null ? 0.3 + 0.7 * I : clamp(m.strength, 0, 1), hue: hue,
      h: (((280 - 360 * hue) / 360) % 1 + 1) % 1, pulse: m.pulse == null ? 0.4 : clamp(m.pulse, 0, 1) };
  }
  /** 夜间程度 0（白天）–1（深夜），按日出日落平滑过渡 */
  function night(st) {
    var t = (st && st.time) || {}, h = t.hour == null ? 12 : t.hour, sr = t.sunrise || 6, ss = t.sunset || 18;
    return h < (sr + ss) / 2 ? 1 - sstep(sr - 1, sr + 0.6, h) : sstep(ss - 0.6, ss + 1, h);
  }
  /** 风向量（像素/秒，speed=1 约 220px/s）；dir_deg 是吹向，0 = 屏幕上方 */
  function wind(st, scale) {
    var w = (st && st.wind) || {}, a = (w.dir_deg || 0) * Math.PI / 180, s = (w.speed || 0) * (scale || 220);
    return { x: Math.sin(a) * s, y: -Math.cos(a) * s, gust: w.gust || 0 };
  }
  function ground(st, k) { var g = (st && st.ground) || {}; return clamp(+g[k] || 0, 0, 1); }

  // ------------------------------------------------------------------ 低分辨率缓冲 + 纹理采样
  function canvas(w, h) { var c = document.createElement('canvas'); c.width = Math.max(1, w | 0); c.height = Math.max(1, h | 0); return c; }
  function buf(w, h) {
    var cv = canvas(w, h), cx = cv.getContext('2d'), img = cx.createImageData(cv.width, cv.height);
    return { cv: cv, cx: cx, img: img, d: img.data, w: cv.width, h: cv.height, flush: function () { cx.putImageData(img, 0, 0); } };
  }
  /** 双线性采样可平铺纹理（坐标单位 = 纹素，自动环绕），返回 [0,1] */
  function samp(t, x, y) {
    var sz = t.size, m = sz - 1, xi = Math.floor(x), yi = Math.floor(y), fx = x - xi, fy = y - yi;
    xi &= m; yi &= m; var x1 = (xi + 1) & m, y1 = (yi + 1) & m, r0 = yi * sz, r1 = y1 * sz;
    var a = t[r0 + xi], b = t[r0 + x1], c = t[r1 + xi], d = t[r1 + x1];
    return (a + (b - a) * fx + (c - a + (a - b + d - c) * fx) * fy) * 0.00392156862745098;
  }
  // 把 fbm 值噪波（集中在 0.5 附近）按 1%–99% 分位拉伸到 0–255
  function stretch(t) {
    var hist = new Uint32Array(256), n = t.length, lo = 0, hi = 255, acc = 0, i;
    for (i = 0; i < n; i++) hist[t[i]]++;
    for (i = 0; i < 256; i++) { acc += hist[i]; if (acc > n * 0.01) { lo = i; break; } }
    for (acc = 0, i = 255; i >= 0; i--) { acc += hist[i]; if (acc > n * 0.01) { hi = i; break; } }
    var out = new Uint8ClampedArray(n), k = 255 / Math.max(1, hi - lo);
    for (i = 0; i < n; i++) out[i] = (t[i] - lo) * k;
    return out;
  }
  var TEX = {};
  /** 每个种子预烘一次：a=主体 fbm（256，周期 4），b/c=扭曲场（128，周期 3），f=细节（128，周期 8） */
  function texSet(N, seed) {
    if (TEX[seed]) return TEX[seed];
    var s = {};
    [['a', 256, 4, 5], ['b', 128, 3, 3], ['c', 128, 3, 3], ['f', 128, 8, 3]].forEach(function (p, i) {
      var t = stretch(N.tile((seed + 101 * (i + 1)) | 0, p[1], p[2], p[3])); t.size = p[1]; s[p[0]] = t;
    });
    return (TEX[seed] = s);
  }
  var SPR = {};
  /** 径向发光小图（lighter 叠加用），按颜色 + 半径缓存 */
  function glow(c, r) {
    var k = c.join(',') + '/' + r; if (SPR[k]) return SPR[k];
    var cv = canvas(r * 2, r * 2), x = cv.getContext('2d'), g = x.createRadialGradient(r, r, 0, r, r, r);
    g.addColorStop(0, rgba(c, 1)); g.addColorStop(0.25, rgba(c, 0.45)); g.addColorStop(1, rgba(c, 0));
    x.fillStyle = g; x.fillRect(0, 0, r * 2, r * 2);
    return (SPR[k] = cv);
  }
  function band(I) { return I < 0.3 ? 0 : I < 0.7 ? 1 : 2; }

  var U = { clamp: clamp, sstep: sstep, lerp: lerp, hsl: hsl, rgba: rgba, magic: magic, night: night, wind: wind,
    ground: ground, canvas: canvas, buf: buf, samp: samp, glow: glow, band: band };

  /**
   * 场景权重图（低分辨率，每格 s 像素）：路 / 空地 = 1，水面 = wWater，其余 = 0，再做两次 3×3 模糊让边缘柔和。
   * 瘴气、积灰、晶屑用它决定"低洼和道路处更浓"。scene 为空时返回全 0.35 的均匀图。
   */
  function sceneMask(scene, W, H, s, wWater) {
    var w = Math.ceil(W / s), h = Math.ceil(H / s), m = new Float32Array(w * h), i, j;
    if (!scene) { m.fill(0.35); return { m: m, w: w, h: h, s: s }; }
    function rects(list, v) {
      (list || []).forEach(function (r) {
        var x0 = Math.max(0, Math.floor(r[0] / s)), y0 = Math.max(0, Math.floor(r[1] / s));
        var x1 = Math.min(w, Math.ceil((r[0] + r[2]) / s)), y1 = Math.min(h, Math.ceil((r[1] + r[3]) / s));
        for (j = y0; j < y1; j++) for (i = x0; i < x1; i++) m[j * w + i] = Math.max(m[j * w + i], v);
      });
    }
    rects(scene.ground, 1); rects(scene.water, wWater == null ? 1 : wWater);
    for (var pass = 0; pass < 2; pass++) {
      var o = new Float32Array(w * h);
      for (j = 0; j < h; j++) for (i = 0; i < w; i++) {
        var acc = 0, n = 0;
        for (var dy = -1; dy <= 1; dy++) for (var dx = -1; dx <= 1; dx++) {
          var x = i + dx, y = j + dy; if (x < 0 || y < 0 || x >= w || y >= h) continue; acc += m[y * w + x]; n++;
        }
        o[j * w + i] = acc / n;
      }
      m = o;
    }
    return { m: m, w: w, h: h, s: s };
  }
  function maskAt(M, x, y) {
    var i = clamp((x / M.s) | 0, 0, M.w - 1), j = clamp((y / M.s) | 0, 0, M.h - 1); return M.m[j * M.w + i];
  }
  U.sceneMask = sceneMask; U.maskAt = maskAt; U.texSet = texSet;
  /**
   * 域扭曲采样（坐标单位 = 主纹理 a 的纹素，64 纹素 ≈ 1 个噪波格）：先用 b/c 两张扭曲场偏移，再取 a。
   * 返回 [0,1]。每帧只在低分辨率缓冲（约 1/8 屏）上调用，开销 ≈ 3 次双线性采样 / 像素。
   */
  function warp(tex, x, y, amt) {
    var qx = samp(tex.b, x * 0.5, y * 0.5) - 0.5, qy = samp(tex.c, x * 0.5 + 37, y * 0.5 + 11) - 0.5;
    return samp(tex.a, x + amt * qx, y + amt * qy);
  }
  /** 把低分辨率缓冲平滑放大画到屏幕（逻辑像素坐标，调用方已设好 dpr 变换） */
  function blit(ctx, b, W, H, alpha, op) {
    b.flush(); ctx.globalAlpha = alpha == null ? 1 : alpha; if (op) ctx.globalCompositeOperation = op;
    ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high'; ctx.drawImage(b.cv, 0, 0, W, H);
    ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
  }
  /** 中点位移折线（电弧）：返回 [x0,y0,x1,y1,...]，r 为种子随机函数 */
  function bolt(r, x0, y0, x1, y1, rough, depth) {
    var pts = [x0, y0, x1, y1];
    for (var d = 0; d < depth; d++) {
      var o = [pts[0], pts[1]];
      for (var i = 0; i + 3 < pts.length; i += 2) {
        var ax = pts[i], ay = pts[i + 1], bx = pts[i + 2], by = pts[i + 3], len = Math.hypot(bx - ax, by - ay);
        var off = (r() - 0.5) * rough * len, nx = -(by - ay) / (len || 1), ny = (bx - ax) / (len || 1);
        o.push((ax + bx) / 2 + nx * off, (ay + by) / 2 + ny * off, bx, by);
      }
      pts = o;
    }
    return pts;
  }
  function path(ctx, p) { ctx.beginPath(); ctx.moveTo(p[0], p[1]); for (var i = 2; i < p.length; i += 2) ctx.lineTo(p[i], p[i + 1]); }
  U.warp = warp; U.blit = blit; U.bolt = bolt; U.path = path;

  // ------------------------------------------------------------------ 叠层对象（按 state.kind 分派）
  function create(opts) {
    opts = opts || {};
    var N = opts.noise || root.WeatherNoise, seed = (opts.seed == null ? 1 : opts.seed) | 0;
    var env = { N: N, U: U, seed: seed, tex: texSet(N, seed), W: 1, H: 1, dpr: 1, scene: null, t: 0 };
    var inst = {}, cur = null, curKind = null;
    function get(kind) {
      if (!KINDS[kind]) return null;
      if (!inst[kind]) {
        inst[kind] = KINDS[kind](env, (seed ^ N.hash32(kind.length * 7919 + kind.charCodeAt(0))) | 0);
        if (inst[kind].resize) inst[kind].resize();
        if (inst[kind].setScene) inst[kind].setScene();
      }
      return inst[kind];
    }
    function each(fn) { Object.keys(inst).forEach(function (k) { if (inst[k][fn]) inst[k][fn](); }); }
    return {
      kinds: Object.keys(KINDS),
      resize: function (w, h, dpr) { env.W = w; env.H = h; env.dpr = dpr || 1; each('resize'); },
      setScene: function (scene) { env.scene = scene || null; each('setScene'); },
      update: function (state, dt) {
        dt = clamp(+dt || 0, 0, 0.1); env.t += dt;
        curKind = state && state.kind; cur = get(curKind);
        if (cur) cur.update(state, dt);
      },
      draw: function (ctx, pass) {
        if (!cur || !cur[pass]) return;
        ctx.save(); cur[pass](ctx); ctx.restore();
      },
      dispose: function () { each('dispose'); inst = {}; cur = null; }
    };
  }

  var API = { create: create, register: function (kind, factory) { KINDS[kind] = factory; }, util: U, kinds: KINDS };
  root.WeatherFX_fantasy = API;
})(typeof window !== 'undefined' ? window : this);
