/*
 * 织梦 · 天气美术：可直接看见的极光叠层（window.WeatherFX_aurora）
 * pass：aurora（新 pass 名，画在 light 之后、flash 之前）。其他 pass 名一律不画。
 *   1. 帘幕：1/4 分辨率缓冲逐列算（fbm3 射线、fbm2 下沿摆动、褶皱处加亮），逐行查色表累加，放大后 lighter 叠上画面上部。
 *   2. 光弧：画面上缘一道椭圆环渐变（弱档主角）。
 *   3. 地面环境光：整体柔光淡染 + 自上而下的 lighter 渐变；有 scene.occluder 时屋顶朝上部分再加亮。
 * 参数规则与 daylight.js 的 auroraParams 一致：state.aurora{strength,hue}；kind='aurora' 而没给 aurora 时用 intensity；
 *   只在夜里（天黑程度曲线逐字照搬 daylight 的 palette.dark）；云量 > 0.35 起遮挡，雾、降水再压暗。
 * 坐标：scene 与绘制都用 CSS 像素；draw 内部自己 setTransform(dpr)。
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

  // 颜色与 daylight.js 的 auroraCol 相同：hue 0 绿 / 0.5 青紫 / 1 品红
  var AUR = [[70, 255, 140], [110, 150, 255], [255, 90, 210]];
  function auroraCol(h) { h = clamp(+h || 0, 0, 1); return h < 0.5 ? mixc(AUR[0], AUR[1], h * 2) : mixc(AUR[1], AUR[2], (h - 0.5) * 2); }
  var RAINY = { drizzle: 0.45, rain: 0.75, storm: 1, sleet: 0.7 };

  // 天黑程度：daylight.js palette() 的 dark 一栏（关键帧、压缩规则、午夜帧都相同），保证两个模块的 night 一致
  var DK = [['sr', -2.0, 1], ['sr', -0.9, 0.80], ['sr', -0.25, 0.45], ['sr', 0.35, 0.10], ['sr', 1.5, 0], ['sr', 3.0, 0],
    ['ss', -2.6, 0], ['ss', -1.2, 0], ['ss', -0.2, 0.15], ['ss', 0.35, 0.50], ['ss', 1.1, 0.88], ['ss', 2.2, 1]];
  function nightness(h, sr, ss) {
    sr = clamp(sr == null ? 6 : sr, 1, 12); ss = clamp(ss == null ? 18 : ss, sr + 3, 23);
    var dayLen = ss - sr, f = Math.min(1, dayLen / 7.5), g = Math.min(1, (24 - dayLen) / 6.5);
    var ks = DK.map(function (k) {
      var base = k[0] === 'sr' ? sr : ss, o = k[1], sc = (k[0] === 'sr') === (o > 0) ? f : g;
      return { t: base + o * sc, v: k[2] };
    });
    var last = ks[ks.length - 1].t, first = ks[0].t;
    ks.push({ t: (last + first + 24) / 2, v: 1 });
    ks.push({ t: first + 24, v: ks[0].v });
    var hh = h; while (hh < first) hh += 24; while (hh >= first + 24) hh -= 24;
    var i = 0; while (i < ks.length - 2 && hh >= ks[i + 1].t) i++;
    var a = ks[i], b = ks[i + 1], s = sstep((hh - a.t) / Math.max(1e-6, b.t - a.t));
    return a.v + (b.v - a.v) * s;
  }

  var S = 4;           // 帘幕缓冲缩放：1/4 分辨率
  var BUF_H = 0.66;    // 缓冲覆盖画面上方 66%

  function Layer(o) {
    o = o || {};
    this.N = o.noise || root.WeatherNoise; this.seed = (o.seed | 0) || 1;
    this.W = 1400; this.H = 900; this.dpr = 1; this.t = 0; this.ph = 0; this.state = {}; this.scene = null;
    this.streak = this.N.tile(this.seed + 907, 128, 16, 3);   // 竖向条纹：横向取原频、纵向拉长
    this.cloud = this.N.tile(this.seed + 911, 128, 4, 4);     // 云遮挡斑块
    this.buf = canvas(2, 2); this.img = null; this.acc = null; this.bw = 1; this.bh = 1;
    this.luts = []; this.lutKey = '';
    this.roof = null; this.roofTint = null; this.roofKey = '';
    this.cols = null; this.dirty = true;
    this.resize(this.W, this.H, 1);
  }
  var P = Layer.prototype;
  P.resize = function (w, h, dpr) {
    this.W = Math.max(1, w | 0); this.H = Math.max(1, h | 0); this.dpr = dpr || 1;
    this.bw = Math.ceil(this.W / S); this.bh = Math.ceil(this.H * BUF_H / S);
    if (this.buf) {
      this.buf.width = this.bw; this.buf.height = this.bh;
      var g = this.buf.getContext('2d'); this.img = g.createImageData(this.bw, this.bh);
      for (var i = 3; i < this.img.data.length; i += 4) this.img.data[i] = 255;
    }
    this.acc = new Float32Array(this.bw * this.bh * 3);
    this.vmask = new Float32Array(this.bh);   // 缓冲下部渐隐到 0
    for (var y = 0; y < this.bh; y++) this.vmask[y] = 1 - sstep((y / this.bh - 0.55) / 0.45);
    this.cols = { yb: new Float32Array(this.bw), a: new Float32Array(this.bw), rl: new Float32Array(this.bw),
      ray: new Float32Array(this.bw), sx: new Float32Array(this.bw) };
    if (this.scene) this.bakeRoof(this.scene);
    this.dirty = true;
  };
  P.setScene = function (sc) { this.scene = sc || null; this.roof = null; this.roofKey = ''; if (sc) this.bakeRoof(sc); };
  /** 屋顶朝上部分：前景剪影减去「下移 D px 的自身」，剩下每个剪影顶部一条带；两次半透明扣除做出渐变。纯合成，不读像素。 */
  P.bakeRoof = function (sc) {
    var oc = sc && sc.occluder; this.roof = null;
    if (!oc || !oc.width || !root.document) return;
    var w = Math.ceil(this.W / 2), h = Math.ceil(this.H / 2), c = canvas(w, h), g = c.getContext('2d');
    var sw = sc.width || this.W, sh = sc.height || this.H, k = 0.5 * this.W / sw;
    g.drawImage(oc, 0, 0, sw * k, sh * this.H / sh * 0.5);
    g.globalCompositeOperation = 'destination-out';
    g.globalAlpha = 0.45; g.drawImage(oc, 0, 5, sw * k, sh * this.H / sh * 0.5);
    g.globalAlpha = 1; g.drawImage(oc, 0, 11, sw * k, sh * this.H / sh * 0.5);
    this.roof = c; this.roofTint = canvas(w, h); this.roofKey = '';
  };
  /** 与 daylight.auroraParams 同规则 */
  P.params = function () {
    var st = this.state || {}, au = st.aurora || {}, s = au.strength, k = st.kind, tm = st.time || {};
    if (s == null) s = k === 'aurora' ? (st.intensity == null ? 0.6 : st.intensity) : 0;
    s = clamp(+s || 0, 0, 1);
    var night = nightness(tm.hour == null ? 0 : +tm.hour, tm.sunrise, tm.sunset);
    var cc = clamp(st.cloud_cover || 0, 0, 1), vis = night * (1 - sstep((cc - 0.35) / 0.5)) * (1 - 0.8 * clamp(st.fog || 0, 0, 1));
    if (RAINY[k] != null || k === 'snow' || k === 'blizzard' || k === 'sandstorm') vis *= 0.15;
    return { s: s, hue: clamp(au.hue == null ? 0 : +au.hue, 0, 1), vis: vis, night: night, cc: cc };
  };
  P.update = function (state, dt) {
    this.state = state || {}; dt = clamp(+dt || 0, 0, 0.25);
    var A = this.params();
    this.t += dt; this.ph += dt * (0.3 + 1.5 * A.s * A.s);   // 摆动相位：强度越高越快（积分，不随强度跳变）
    this.dirty = true;
  };
  /** 每条帘幕一张 64 级色表（下沿 → 上部）：主色、高强度下沿品红/紫边、上部偏绿、下沿亮芯 */
  P.ensureLut = function (A) {
    var multi = sstep((A.s - 0.6) / 0.25), key = Math.round(A.hue * 50) + '|' + Math.round(A.s * 20);
    if (key === this.lutKey) return; this.lutKey = key;
    var c0 = auroraCol(A.hue), c1 = mixc(c0, A.hue < 0.5 ? [255, 80, 170] : [120, 220, 255], 0.2 + 0.65 * multi);
    var mains = [c0, mixc(c0, c1, 0.55), c1];
    var fringe = A.hue < 0.75 ? [255, 70, 175] : [170, 95, 255], fa = 0.75 * sstep((A.s - 0.5) / 0.35);
    var ta = 0.5 * sstep((A.s - 0.5) / 0.35), green = [80, 255, 150];
    this.luts = mains.map(function (m) {
      var L = new Float32Array(64 * 3);
      for (var i = 0; i < 64; i++) {
        var u = i / 63 * 1.4 - 0.12, c = m;
        c = mixc(c, green, ta * sstep((u - 0.25) / 0.55));
        c = mixc(c, fringe, fa * sstep((0.1 - u) / 0.16));
        c = mixc(c, [225, 255, 240], 0.12 * sstep(1 - Math.abs(u - 0.02) / 0.06));
        L[i * 3] = c[0]; L[i * 3 + 1] = c[1]; L[i * 3 + 2] = c[2];
      }
      return L;
    });
  };
  /** 帘幕层配置（按强度插值）：[下沿位置(缓冲高度比), 高度比, 摆幅, 透明度系数, 色表] */
  P.curtains = function (s) {
    var mid = sstep((s - 0.22) / 0.2), multi = sstep((s - 0.62) / 0.25), L = [];
    if (mid > 0.01) L.push({ y: 0.34 + 0.2 * multi, h: 0.28 + 0.2 * s + 0.08 * multi, amp: 0.2 + 0.08 * multi, a: mid * (0.6 + 0.25 * s), lut: 0, k: 0 });
    if (multi > 0.01) {
      L.push({ y: 0.24, h: 0.30 + 0.06 * multi, amp: 0.2, a: multi * 0.55, lut: 1, k: 1 });
      L.push({ y: 0.08, h: 0.24, amp: 0.16, a: multi * 0.42, lut: 2, k: 2 });
    }
    return L;
  };
  /** 1/4 分辨率缓冲：逐列算下沿 / 射线 / 褶皱亮度，逐像素查色表累加 */
  P.compute = function (A, curA) {
    var N = this.N, bw = this.bw, bh = this.bh, acc = this.acc, t = this.t, ph = this.ph, sd = this.seed + 301;
    var cols = this.cols, streak = this.streak, cl = this.cloud, cc = A.cc, vm = this.vmask, S4 = S;
    acc.fill(0);
    var Ls = this.curtains(A.s), wind = (this.state.wind && this.state.wind.speed) || 0.2;
    for (var li = 0; li < Ls.length; li++) {
      var C = Ls[li], k = C.k, lut = this.luts[C.lut], ka = C.a * curA, kh = C.h * bh;
      // 逐列
      for (var x = 0; x < bw; x++) {
        var f = N.fbm2(sd + k * 13, x * 0.0068 + k * 7.3, ph * 0.045, 3) - 0.5;          // 低频：下沿褶皱与横向流动
        var g2 = N.noise2(sd + 40 + k, x * 0.021 + ph * 0.05, k * 3.1 + ph * 0.11) - 0.5; // 中频：小褶
        var big = N.fbm2(sd + 120 + k * 5, x * 0.0026 + k * 4.1, ph * 0.03, 2) - 0.5;      // 超低频：整条帘幕大幅弯折
        var yb = bh * (C.y + 0.62 * C.h) + f * bh * C.amp * 3 + big * bh * 0.55 + g2 * bh * 0.05 + Math.sin(x * 0.018 + ph * 0.32 + k * 2) * bh * 0.025;
        cols.yb[x] = yb;
        var sx = x + f * 70 + ph * (2.2 + k);                                             // 射线随褶皱横移
        cols.sx[x] = sx;
        var ray = N.fbm3(sd + 50 + k * 7, sx * 0.16, k * 4.7, t * 0.22, 3);
        cols.ray[x] = ray;
        var env = sstep((N.fbm2(sd + 90 + k, x * 0.0045 + k * 2.9, ph * 0.02 + k, 2) - 0.28) / 0.3); // 横向断续
        var pulse = N.noise2(sd + 10 + k, x * 0.012 - t * 0.06, t * 0.09 + k);
        cols.a[x] = ka * env * (0.3 + 1.2 * pulse * pulse);
        cols.rl[x] = kh * (0.65 + 0.7 * N.noise2(sd + 70 + k, sx * 0.05, t * 0.05));       // 射线长度
      }
      for (x = 0; x < bw; x++) {
        var a = cols.a[x]; if (a < 0.004) continue;
        var d = x > 0 && x < bw - 1 ? Math.abs(cols.yb[x + 1] - cols.yb[x - 1]) * 0.5 : 0;
        var fold = 1 + Math.min(1.6, d * 0.9);                 // 褶子侧看处更亮
        var rv = cols.ray[x]; rv = rv * rv * 2.2;
        a *= fold * (0.25 + rv);
        yb = cols.yb[x]; var hh = cols.rl[x], tx = ((cols.sx[x] * 2) | 0) & 127;
        var y0 = Math.max(0, Math.floor(yb - hh)), y1 = Math.min(bh - 1, Math.ceil(yb + 8));
        for (var y = y0; y <= y1; y++) {
          var u = (yb - y) / hh, prof;
          if (u < 0) { var dd = 1 + u * hh / 8; prof = dd > 0 ? dd * dd * dd : 0; }
          else { var q = 1 - u; prof = q * (0.5 + 0.5 * q * q * q * q); }
          if (prof <= 0) continue;
          var tv = streak[((((y * 0.14 + k * 31 + t * 0.6) | 0) & 127) << 7) + tx] / 255;
          var v = a * prof * (0.55 + 0.9 * tv) * vm[y];
          if (cc > 0.08) { // 云团挡住部分帘幕
            var cv = cl[((((y * 0.5 + t * wind * 3) | 0) & 127) << 7) + (((x * 0.4 + t * wind * 6) | 0) & 127)] / 255;
            v *= 1 - 0.92 * sstep((cv - 1 + cc * 1.25) / 0.22);
          }
          var li3 = (Math.max(0, Math.min(63, ((u + 0.12) / 1.4 * 63) | 0))) * 3, o = (y * bw + x) * 3;
          acc[o] += lut[li3] * v; acc[o + 1] += lut[li3 + 1] * v; acc[o + 2] += lut[li3 + 2] * v;
        }
      }
    }
    var dta = this.img.data, n = bw * bh;
    for (var i = 0; i < n; i++) {
      var r = acc[i * 3], gg = acc[i * 3 + 1], b = acc[i * 3 + 2];
      dta[i * 4] = r > 255 ? 255 : r; dta[i * 4 + 1] = gg > 255 ? 255 : gg; dta[i * 4 + 2] = b > 255 ? 255 : b;
    }
    this.buf.getContext('2d').putImageData(this.img, 0, 0);
    return Ls.length;
  };
  /** 上缘光弧：椭圆环渐变，环下沿落在画面顶部约 12–20% 处 */
  P.drawArc = function (ctx, A, c0) {
    var multi = sstep((A.s - 0.62) / 0.25), arcA = A.vis * Math.min(1, A.s / 0.1) * (0.55 + 0.25 * A.s) * (1 - 0.5 * multi);
    if (arcA < 0.01) return;
    var W = this.W, H = this.H, R = W * 0.75, sy = 0.24, sway = Math.sin(this.ph * 0.15) * 0.012 * H;
    ctx.save(); ctx.translate(W * 0.5 + Math.sin(this.ph * 0.07) * W * 0.03, H * (0.16 + 0.04 * A.s) - R * 0.8 * sy + sway); ctx.scale(1, sy);
    var rg = ctx.createRadialGradient(0, 0, 0, 0, 0, R);
    rg.addColorStop(0, rgb(c0, 0)); rg.addColorStop(0.6, rgb(c0, arcA * 0.12)); rg.addColorStop(0.77, rgb(c0, arcA * 0.5));
    rg.addColorStop(0.8, rgb(mixc(c0, [220, 255, 235], 0.3), arcA * 0.72)); rg.addColorStop(0.86, rgb(c0, arcA * 0.18)); rg.addColorStop(1, rgb(c0, 0));
    ctx.fillStyle = rg; ctx.fillRect(-R, -R, R * 2, R * 2); ctx.restore();
  };
  /** 地面环境光：柔光整体淡染 + 自上而下的 lighter 渐变（天光从上方来）；有 occluder 时屋顶朝上部分再加亮 */
  P.drawGround = function (ctx, A, c0, aa) {
    var W = this.W, H = this.H, strong = sstep((A.s - 0.5) / 0.4);
    ctx.globalCompositeOperation = 'soft-light';
    ctx.fillStyle = rgb(c0, clamp(0.08 + 0.13 * strong, 0, 1) * aa); ctx.fillRect(0, 0, W, H);
    ctx.globalCompositeOperation = 'lighter';
    var lg = ctx.createLinearGradient(0, 0, 0, H), d = [c0[0] * 0.5, c0[1] * 0.5, c0[2] * 0.5];
    lg.addColorStop(0, rgb(d, (0.04 + 0.07 * strong) * aa)); lg.addColorStop(0.55, rgb(d, (0.02 + 0.035 * strong) * aa));
    lg.addColorStop(1, rgb(d, (0.01 + 0.025 * strong) * aa));
    ctx.fillStyle = lg; ctx.fillRect(0, 0, W, H);
    if (this.roof) {
      var key = Math.round(A.hue * 50) + '';
      if (key !== this.roofKey) {
        this.roofKey = key; var r = this.roofTint, g = r.getContext('2d');
        g.globalCompositeOperation = 'copy'; g.drawImage(this.roof, 0, 0);
        g.globalCompositeOperation = 'source-in'; g.fillStyle = rgb(mixc(c0, [255, 255, 255], 0.15)); g.fillRect(0, 0, r.width, r.height);
        g.globalCompositeOperation = 'source-over';
      }
      ctx.globalAlpha = clamp((0.08 + 0.2 * A.s) * aa, 0, 1); ctx.drawImage(this.roofTint, 0, 0, W, H); ctx.globalAlpha = 1;
    }
  };
  P.draw = function (ctx, pass) {
    if (pass !== 'aurora' || !ctx) return;
    var A = this.params(), aa = A.s * A.vis;
    if (A.s < 0.01 || A.vis < 0.02) return;
    var c0 = auroraCol(A.hue), W = this.W, H = this.H;
    ctx.save(); ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0); ctx.globalAlpha = 1;
    this.drawGround(ctx, A, c0, aa);
    ctx.globalCompositeOperation = 'lighter';
    this.drawArc(ctx, A, c0);
    var curA = A.vis * sstep((A.s - 0.2) / 0.22);
    if (curA > 0.01 && this.buf) {
      this.ensureLut(A);
      if (this.dirty) { this.compute(A, curA); this.dirty = false; }
      ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(this.buf, 0, 0, this.bw, this.bh, 0, 0, this.bw * S, this.bh * S);
      // 第二遍：放大 2 倍的模糊副本当辉光
      ctx.globalAlpha = 0.25 + 0.12 * A.s;
      ctx.drawImage(this.buf, 0, 0, this.bw, this.bh, -S * 2, -S, this.bw * S + S * 4, this.bh * S + S * 3);
      ctx.globalAlpha = 1;
    }
    ctx.restore();
  };
  P.info = function () { var A = this.params(); return { s: A.s, hue: A.hue, vis: A.vis, night: A.night, curtains: this.curtains(A.s).length }; };
  P.dispose = function () { this.buf = null; this.img = null; this.acc = null; this.roof = null; this.roofTint = null; this.scene = null; };

  var API = { create: function (o) { return new Layer(o); }, auroraCol: auroraCol, nightness: nightness };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.WeatherFX_aurora = API;
})(this);
