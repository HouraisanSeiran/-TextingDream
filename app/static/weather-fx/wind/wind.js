/*
 * 织梦 · 天气美术：强风天气叠层（typhoon 台风 / 飓风、tornado 龙卷风）—— window.WeatherFX_wind
 * 接口见 docs/weather-spec.md 3.1 / 第 8 节：create → resize → setScene → update(state, dt) → draw(ctx, pass) → dispose
 * pass：reflect（水面压暗、白沫条纹、浪尖、飞沫）
 *       precip （树冠摆动残影、轮廓抖动光带、屋脊飞沫、风线、碎叶树枝碎屑、龙卷漏斗 / 尘环 / 吸入碎屑）
 *       fog    （快速低云影、眼墙白茫雨幕、风眼放亮与四周眼墙暗边、龙卷壁云与尘雾）
 * 雨不在这里画：降水交给 WeatherFX_rain，传入 WeatherFX_wind.rainState(state)；天色交给 WeatherFX_daylight，
 * 传入 WeatherFX_wind.daylightState(state)。两个函数只把台风 / 龙卷风改写成那两个模块认识的 kind，不改原对象。
 * 坐标：CSS 像素；draw 内部 setTransform(dpr)。只读天气状态；所有随机由 seed 派生。
 */
(function (root) {
  'use strict';
  var KINDS = { typhoon: 1, tornado: 1 };
  var KW = 96, KH = 62;          // 云影 / 白茫低分辨率缓冲
  var FW = 84, FH = 150;         // 漏斗缓冲（屏幕包围盒内的低分辨率栅格）
  var GW = 24, GH = 40;          // 漏斗 fbm3 粗网格（沿角度采样）
  var TS = 128;                  // 漏斗条纹平铺纹理边长
  var SMOOTH = ['pw', 'sea', 'sheet', 'shadow', 'bright', 'v', 'sway'];
  function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }
  function sstep(a, b, x) { var t = clamp01((x - a) / (b - a)); return t * t * (3 - 2 * t); }
  function mix(a, b, t) { return a + (b - a) * t; }
  function mkCanvas(w, h) { var c = document.createElement('canvas'); c.width = Math.max(1, w | 0); c.height = Math.max(1, h | 0); return c; }
  function copy(o) { var r = {}; for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) r[k] = o[k]; return r; }

  // 对象池：激活的放在前 n 个，删除时与末尾交换
  function Pool(cap, make) { this.a = []; this.n = 0; this.cap = cap; for (var i = 0; i < cap; i++) this.a.push(make()); }
  Pool.prototype.get = function () { return this.n < this.cap ? this.a[this.n++] : null; };
  Pool.prototype.kill = function (i) { var t = this.a[i]; this.a[i] = this.a[--this.n]; this.a[this.n] = t; };
  Pool.prototype.clear = function () { this.n = 0; };

  function catOf(st) { var c = st.cyclone || {}; return Math.max(1, Math.min(5, Math.round(+c.category || 1))); }
  function phaseOf(st) { var c = st.cyclone || {}; return c.phase === 'eye' || c.phase === 'eyewall' ? c.phase : 'outer'; }
  function vortexOf(st) { return st.vortex != null && +st.vortex > 0 ? clamp01(+st.vortex) : clamp01(+st.intensity || 0); }

  /** 由天气状态派生本帧目标参数（只读 state，不推断天气）；sm 里是平滑后的值，phase 切换约 1 秒过渡 */
  function derive(st) {
    st = st || {};
    var kind = st.kind, on = !!KINDS[kind], I = clamp01(+st.intensity || 0);
    var w = st.wind || {}, dir = (+w.dir_deg || 0) * Math.PI / 180;
    var p = { on: on, kind: kind || 'clear', I: I, ty: on && kind === 'typhoon', to: on && kind === 'tornado',
      dx: Math.sin(dir), dy: -Math.cos(dir), sp: clamp01(+w.speed || 0), gu: clamp01(+w.gust || 0),
      cat: catOf(st), phase: phaseOf(st), eye: false, wall: false,
      cloud: clamp01(st.cloud_cover != null ? +st.cloud_cover : 0.9),
      pw: 0, sea: 0, sheet: 0, shadow: 0, bright: 0, v: 0, sway: 0, vs: 0, cloudV: 0.1 };
    if (p.ty) {
      var catF = 0.8 + 0.1 * (p.cat - 1);                 // 1 级 0.8 … 5 级 1.2
      var base = (0.3 + 0.7 * I) * catF;
      p.eye = p.phase === 'eye'; p.wall = p.phase === 'eyewall';
      p.pw = clamp01(base * (p.eye ? 0.1 : p.wall ? 1.18 : 0.85));
      p.sea = clamp01(p.eye ? 0.45 * base : base * (p.wall ? 1.15 : 0.95));
      p.sheet = p.eye ? 0 : p.wall ? 0.45 + 0.55 * I : 0.35 * sstep(0.72, 1, I);
      p.shadow = p.eye ? 0.05 : (0.2 + 0.26 * p.pw) * (p.wall ? 0.5 : 1);   // 眼墙以白茫为主，暗云影减半
      p.bright = p.eye ? 1 : 0;
      p.sway = p.eye ? 0.04 : p.pw;
      p.vs = p.eye ? p.sp * 0.1 : p.sp;
      p.cloudV = p.eye ? 0.05 : 0.3 + 1.0 * p.vs;           // 云影：噪波单位 / 秒（画面宽约 4 单位）
    } else if (p.to) {
      p.v = vortexOf(st);
      p.pw = 0.18 + 0.5 * p.v;
      p.sea = 0.15 + 0.45 * p.v * (0.4 + 0.6 * p.sp);
      p.shadow = 0.16 + 0.12 * p.v;
      p.sway = 0.25 + 0.55 * p.v;
      p.vs = p.sp;
      p.cloudV = 0.12 + 0.45 * p.sp;
    }
    return p;
  }

  function Layer(opts) {
    opts = opts || {};
    this.N = opts.noise || root.WeatherNoise;
    if (!this.N) throw new Error('WeatherFX_wind 需要 WeatherNoise（noise.js）');
    this.seed = (opts.seed >>> 0) || 1;
    this.R = this.N.rng(this.seed ^ 0x3c6ef372);
    this.w = 1; this.h = 1; this.dpr = 1; this.time = 0; this.frame = 0; this.scene = null;
    this.p = derive(null); this.sm = { on: 0 };
    for (var i = 0; i < SMOOTH.length; i++) this.sm[SMOOTH[i]] = 0;
    this.debris = new Pool(900, function () { return { x: 0, y: 0, vx: 0, vy: 0, k: 0, rot: 0, spin: 0, sz: 1, c: 0, ph: 0, m: 1, t: 0, life: 1, a: 1 }; });
    this.lines = new Pool(240, function () { return { x: 0, y: 0, len: 0, v: 1, t: 0, life: 1, a: 0 }; });
    this.crests = new Pool(380, function () { return { x: 0, y: 0, len: 0, t: 0, life: 1 }; });
    this.orbit = new Pool(420, function () { return { a: 0, r: 0, h: 0, vh: 0, k: 0, sz: 1, c: 0, rot: 0, spin: 0, t: 0, life: 1 }; });
    this.puffs = new Pool(80, function () { return { a: 0, r: 0, h: 0, s: 1, t: 0, life: 1, w: 1 }; });
    this.cloudCv = mkCanvas(KW, KH); this.cloudImg = this.cloudCv.getContext('2d').createImageData(KW, KH);
    this.sheetCv = mkCanvas(KW, KH); this.sheetImg = this.sheetCv.getContext('2d').createImageData(KW, KH);
    this.funCv = mkCanvas(FW, FH); this.funImg = this.funCv.getContext('2d').createImageData(FW, FH);
    this.fgrid = new Float32Array(GW * GH);
    this.cloudOff = 0; this.sheetOff = 0; this.foamOff = 0; this.rot = 0;
    this.gust = 1; this.speed = 0; this.big = 0; this.bigE = 0; this.nextBig = 5 + this.R() * 5;
    this.acc = { debris: 0, lines: 0, crests: 0, orbit: 0, puffs: 0 };
    var R = this.N.rng(this.seed + 77), side = R() < 0.5 ? -1 : 1;
    this.tor = { fx: 0.5 + side * (0.18 + R() * 0.15), ph: R() * 6.283, g: null, box: null };   // 避开画面正中
    this.edges = null; this.treeCv = null; this.wPath = null; this.wRects = []; this.wArea = 0;
    this.bake();
  }
  var P = Layer.prototype;

  /** 预烘：水面白沫条纹（两张可平铺噪波，按风向拉长）、尘团 sprite */
  P.bake = function () {
    var N = this.N, s = this.seed;
    function toCanvas(size, data, rgb, aMap) {
      var c = mkCanvas(size, size), g = c.getContext('2d'), img = g.createImageData(size, size), d = img.data;
      for (var i = 0; i < size * size; i++) { d[i * 4] = rgb[0]; d[i * 4 + 1] = rgb[1]; d[i * 4 + 2] = rgb[2]; d[i * 4 + 3] = aMap(data[i] / 255); }
      g.putImageData(img, 0, 0); return c;
    }
    this.foamA = toCanvas(256, N.tile(s + 11, 256, 8, 3), [236, 242, 244], function (v) { return Math.round(255 * sstep(0.56, 0.78, v)); });
    this.foamB = toCanvas(128, N.tile(s + 12, 128, 16, 2), [246, 250, 250], function (v) { return Math.round(255 * sstep(0.66, 0.86, v)); });
    this.darkTile = toCanvas(128, N.tile(s + 13, 128, 4, 3), [24, 40, 52], function (v) { return Math.round(255 * (0.35 + 0.65 * v)); });
    var c = mkCanvas(64, 64), g = c.getContext('2d'), gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, 'rgba(150,132,108,0.85)'); gr.addColorStop(0.5, 'rgba(140,124,102,0.45)'); gr.addColorStop(1, 'rgba(130,118,100,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 64, 64); this.dustSp = c;
    this.pats = null;
  };

  P.resize = function (w, h, dpr) {
    this.w = Math.max(1, w | 0); this.h = Math.max(1, h | 0); this.dpr = dpr || 1;
    if (this.scene && this.scene.occluder) this.buildEdges(this.scene.occluder);
  };

  P.setScene = function (sc) {
    this.scene = sc || null; this.edges = null; this.silCv = null; this.rimCv = null;
    this.wPath = null; this.wRects = []; this.wArea = 0; this.wBox = null; this.crests.clear();
    if (!sc) return;
    var water = sc.water || [];
    if (water.length && root.Path2D) {
      var p = new root.Path2D(), x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9, a = 0;
      water.forEach(function (r) { p.rect(r[0], r[1], r[2], r[3]); a += r[2] * r[3];
        x0 = Math.min(x0, r[0]); y0 = Math.min(y0, r[1]); x1 = Math.max(x1, r[0] + r[2]); y1 = Math.max(y1, r[1] + r[3]); });
      this.wPath = p; this.wRects = water; this.wArea = a; this.wBox = [x0, y0, x1 - x0, y1 - y0];
      // 按面积累计，便于按面积均匀撒浪尖
      var cum = [], acc = 0; water.forEach(function (r) { acc += r[2] * r[3]; cum.push(acc); }); this.wCum = cum;
    }
    if (sc.occluder) this.buildEdges(sc.occluder); else this.edgesFromBoxes(sc.buildings || []);
  };

  /** 从 occluder 剪影取上沿点（不透明且上方透明），并做一张半分辨率的浅色剪影给「摆动残影」用 */
  P.buildEdges = function (oc) {
    var sc = this.scene || {}, W = sc.width || this.w, H = sc.height || this.h, S = 3;
    var gw = Math.ceil(W / S), gh = Math.ceil(H / S), small = mkCanvas(gw, gh), g = small.getContext('2d'), d;
    g.drawImage(oc, 0, 0, gw, gh);
    try { d = g.getImageData(0, 0, gw, gh).data; } catch (e) { this.edgesFromBoxes(sc.buildings || []); return; }
    var pts = [], R = this.N.rng(this.seed + 404);
    for (var y = 2; y < gh; y++) for (var x = 0; x < gw; x++) {
      var i = (y * gw + x) * 4 + 3;
      if (d[i] > 120 && d[i - gw * 4] < 40 && d[i - gw * 8] < 40) pts.push({ x: x * S + S * 0.5, y: y * S, ph: R() * 100, c: R() });
    }
    for (var k = pts.length - 1; k > 0; k--) { var j = (R() * (k + 1)) | 0, t = pts[k]; pts[k] = pts[j]; pts[j] = t; }
    this.edges = pts.slice(0, 2600);
    var hw = Math.ceil(W / 2), hh = Math.ceil(H / 2), sil = mkCanvas(hw, hh), q = sil.getContext('2d');
    q.drawImage(oc, 0, 0, hw, hh);
    q.globalCompositeOperation = 'source-in'; q.fillStyle = 'rgb(226,234,232)'; q.fillRect(0, 0, hw, hh);
    this.silCv = sil; this.rimCv = mkCanvas(hw, hh); this.silScale = 2;
  };
  /** 没有 occluder 时：用建筑包围盒屋顶上沿近似 */
  P.edgesFromBoxes = function (bs) {
    var pts = [], R = this.N.rng(this.seed + 405);
    bs.forEach(function (b) { var y = b.roofY != null ? b.roofY : b.y;
      for (var x = b.x + 2; x < b.x + b.w - 2; x += 4) pts.push({ x: x, y: y, ph: R() * 100, c: R() }); });
    this.edges = pts.slice(0, 2600); this.silCv = null; this.rimCv = null;
  };

  P.update = function (state, dt) {
    dt = Math.max(0, Math.min(0.1, +dt || 0));
    this.time += dt; this.frame++;
    var p = this.p = derive(state), sm = this.sm, N = this.N, s = this.seed, t = this.time, i;
    var k = this.frame < 3 ? 1 : 1 - Math.exp(-dt * 1.8);           // 第一帧直接到位；之后 phase / 强度切换约 1 秒过渡
    sm.on += ((p.on ? 1 : 0) - sm.on) * k;
    for (i = 0; i < SMOOTH.length; i++) { var nm = SMOOTH[i]; sm[nm] += (p[nm] - sm[nm]) * k; }
    this.cv = this.cv == null ? p.cloudV : this.cv + (p.cloudV - this.cv) * k;
    // 阵风：一维 fbm 随时间起伏；按种子间隔来一阵大风（约 0.5 秒冲上去、2 秒退下）
    var gb = N.fbm2(s + 5, t * 0.7, 0.37, 3) * 2 - 1;
    this.nextBig -= dt;
    if (this.nextBig <= 0) { this.big = p.on && sm.pw > 0.15 ? 1 : 0; this.nextBig = (p.ty ? 5 : 8) + this.R() * 8 * (1.3 - p.gu); }
    this.bigE += ((this.big > 0 ? 1 : 0) - this.bigE) * (1 - Math.exp(-dt * (this.big > 0 ? 4 : 0.8)));
    if (this.big > 0) this.big -= dt / 0.9;
    this.gust = Math.max(0.35, 1 + (0.2 + 0.55 * p.gu) * gb + (0.45 + 0.5 * p.gu) * this.bigE);
    this.speed = (160 + 1050 * p.vs) * (0.2 + 0.8 * sm.pw) * this.gust;      // 碎屑水平速度 px/s
    this.cloudOff += this.cv * dt * (0.6 + 0.4 * this.gust);
    this.sheetOff += (0.5 + 1.8 * p.vs) * dt * this.gust;
    this.foamOff += this.speed * dt * 0.22;
    this.rot += dt * (1.1 + 2.8 * sm.v);
    if (this.frame % 2 === 1 || this.frame < 3) this.updateClouds(p);
    if (sm.sheet > 0.01 && (this.frame % 2 === 0 || this.frame < 3)) this.updateSheet(p);
    if (p.to || sm.v > 0.02) this.updateTornado(p, dt);
    this.updateDebris(p, dt);
    this.updateLines(p, dt);
    this.updateCrests(p, dt);
  };

  /** 低云影：fbm3（第三维 = 时间），坐标转到风向坐标系里沿风拉长，随风快速平移 */
  P.updateClouds = function (p) {
    var N = this.N, s = this.seed, t = this.time, d = this.cloudImg.data, sm = this.sm;
    var dx = p.dx, dy = p.dy, off = this.cloudOff, a0 = sm.shadow * sm.on;
    var lo = p.to ? 0.3 : mix(0.5, 0.34, sm.pw);
    for (var y = 0; y < KH; y++) for (var x = 0; x < KW; x++) {
      var u = x / KW * 4.2, v = y / KH * 2.7;
      var al = u * dx + v * dy, ac = -u * dy + v * dx;            // 沿风 / 横风
      var n = N.fbm3(s + 31, al * 0.7 - off, ac * 1.5, t * 0.32, 3);
      var c = sstep(lo, lo + 0.34, n), j = (y * KW + x) * 4;
      if (p.to) c = Math.max(c, 0.55 * (1 - y / KH));              // 龙卷：画面上部压着暗色壁云
      d[j] = 22; d[j + 1] = 28; d[j + 2] = 36; d[j + 3] = Math.round(255 * clamp01(a0 * (0.35 + 0.9 * c)));
    }
    this.cloudCv.getContext('2d').putImageData(this.cloudImg, 0, 0);
  };

  /** 眼墙白茫雨幕：沿风高频、横风低频的条带，向下风扫过；底色一层白雾 */
  P.updateSheet = function (p) {
    var N = this.N, s = this.seed, t = this.time, d = this.sheetImg.data, sm = this.sm;
    var dx = p.dx, dy = p.dy, off = this.sheetOff, a0 = sm.sheet * sm.on;
    for (var y = 0; y < KH; y++) for (var x = 0; x < KW; x++) {
      var u = x / KW * 4.2, v = y / KH * 2.7, al = u * dx + v * dy, ac = -u * dy + v * dx;
      var n = N.fbm3(s + 47, al * 1.9 - off, ac * 0.55, t * 0.45, 2);
      var b = sstep(0.38, 0.72, n), j = (y * KW + x) * 4;
      d[j] = 214; d[j + 1] = 222; d[j + 2] = 228; d[j + 3] = Math.round(255 * clamp01(a0 * (0.18 + 0.52 * b)));
    }
    this.sheetCv.getContext('2d').putImageData(this.sheetImg, 0, 0);
  };

  /** 龙卷几何：随强度从远处细漏斗（不着地）→ 着地 → 粗大楔形；位置按种子选在画面左 / 右，缓慢漂移 */
  P.updateTornado = function (p, dt) {
    var T = this.tor, W = this.w, H = this.h, v = this.sm.v, t = this.time;
    var touch = sstep(0.26, 0.42, v);
    var gy = H * (0.66 + 0.1 * Math.sin(T.ph * 3.1));               // 漏斗着地处
    var drift = 0.07 * Math.sin(t * 0.045 + T.ph) + 0.02 * Math.sin(t * 0.13 + T.ph * 2);
    var xb = W * (T.fx + drift), tilt = (34 + 60 * (1 - v)) * Math.sin(t * 0.07 + T.ph * 1.7) * (T.fx < 0.5 ? 1 : -1);
    var tw = 70 + 420 * v, bw = 5 + 150 * Math.pow(v, 1.6);
    var yt = -24, yb = mix(yt + (gy - yt) * 0.5, gy, touch);
    T.g = { xt: xb + tilt, yt: yt, xb: xb, yb: yb, gy: gy, tw: tw, bw: bw, touch: touch, v: v };
    var pad = 14 + bw * 0.4, bx0 = Math.min(xb - bw, xb + tilt - tw * 0.55) - pad, bx1 = Math.max(xb + bw, xb + tilt + tw * 0.55) + pad;
    T.box = [bx0, yt, bx1 - bx0, yb - yt + 6];
    // fbm3 粗网格：列 = 漏斗正面的角度 θ∈[-π/2, π/2]（加自转与随高度扭转成螺旋条纹），行 = 高度 q
    var N = this.N, s = this.seed, G = this.fgrid, rot = this.rot;
    if (this.frame % 2 === 0 || this.frame < 3) {
      for (var j = 0; j < GH; j++) {
        var q = j / (GH - 1);
        for (var i = 0; i < GW; i++) {
          var th = (i / (GW - 1) - 0.5) * Math.PI;
          G[j * GW + i] = N.fbm3(s + 61, (th - rot * (1.4 - 0.8 * q)) * 1.6 + q * 3.4, q * 5.5, t * 0.6, 2);
        }
      }
      this.renderFunnel(p);
    }
    this.spawnOrbit(p, dt);
  };

  /** 漏斗栅格：圆柱明暗 + 条纹 + 噪波粗糙边，写进 FW×FH 缓冲，draw 时放大到包围盒 */
  P.renderFunnel = function (p) {
    var T = this.tor, g = T.g, box = T.box, d = this.funImg.data, G = this.fgrid, t = this.time;
    var far = 1 - sstep(0.2, 0.55, g.v);                            // 远处：偏灰蓝、半透明
    var dust = sstep(0.3, 0.6, g.v) * g.touch;
    for (var y = 0; y < FH; y++) {
      var py = box[1] + (y + 0.5) / FH * box[3], q = (py - g.yt) / (g.yb - g.yt);
      var o = (y * FW) * 4;
      if (q < 0 || q > 1.02) { for (var x0 = 0; x0 < FW; x0++) d[o + x0 * 4 + 3] = 0; continue; }
      var qc = Math.min(1, q);
      // 中心线：上下两端插值，加一点随高度的蛇形摆动（细漏斗更明显）
      var cx = mix(g.xt, g.xb, Math.pow(qc, 0.85)) + Math.sin(qc * 5.2 - t * 0.9) * (3 + 10 * far) * qc;
      var hw = mix(g.tw * 0.5, g.bw * 0.5, Math.pow(qc, 0.6));      // 上宽下窄，上部收得快（凹形）
      var gj = Math.min(GH - 1, qc * (GH - 1)), j0 = gj | 0, j1 = Math.min(GH - 1, j0 + 1), fj = gj - j0;
      var topF = sstep(0, 0.12, q), botF = g.touch > 0.5 ? 1 - sstep(0.99, 1.02, q) : 1 - sstep(0.7, 1, q) * (1 - g.touch * 2);
      for (var x = 0; x < FW; x++) {
        var px = box[0] + (x + 0.5) / FW * box[2], rel = (px - cx) / hw, k = o + x * 4;
        var ar = Math.abs(rel);
        if (ar > 1.35) { d[k + 3] = 0; continue; }
        var gi = (Math.max(-1, Math.min(1, rel)) * 0.5 + 0.5) * (GW - 1), i0 = gi | 0, i1 = Math.min(GW - 1, i0 + 1), fi = gi - i0;
        var n = mix(mix(G[j0 * GW + i0], G[j0 * GW + i1], fi), mix(G[j1 * GW + i0], G[j1 * GW + i1], fi), fj);
        var edge = 1 - sstep(0.86, 1.04, ar + (n - 0.5) * 0.4);      // 边缘收紧：漏斗轮廓清楚
        if (edge <= 0) { d[k + 3] = 0; continue; }
        var stripe = sstep(0.32, 0.72, n);
        var shade = 0.55 + 0.45 * Math.cos(Math.min(1, ar) * 1.4) - 0.25 * Math.max(0, rel);   // 左侧受光
        var L = (50 + 64 * shade + 72 * stripe) * (1 - 0.18 * (1 - qc)) + (rel < -0.62 && rel > -1 ? 34 * (1 - far) : 0);   // 条纹加对比 + 左侧亮边
        var r = L, gg = L * 1.02, b = L * 1.08;
        var du = dust * sstep(0.72, 1, qc);
        r = mix(r, 128 + 30 * stripe, du); gg = mix(gg, 108 + 24 * stripe, du); b = mix(b, 86 + 18 * stripe, du);
        r = mix(r, 150, far * 0.45); gg = mix(gg, 158, far * 0.45); b = mix(b, 170, far * 0.45);
        d[k] = r; d[k + 1] = gg; d[k + 2] = b;
        d[k + 3] = Math.round(255 * edge * topF * botF * (0.82 + 0.18 * stripe) * (0.96 - 0.4 * far));
      }
    }
    this.funCv.getContext('2d').putImageData(this.funImg, 0, 0);
  };

  /** 漏斗底部：碎屑环绕（极坐标，向内螺旋、角速度 ∝ 1/r、靠近时被抬升）+ 尘环团块；同时推进二者 */
  P.spawnOrbit = function (p, dt) {
    var T = this.tor, g = T.g, R = this.R, O = this.orbit, U = this.puffs, A = this.acc, i, o;
    var on = p.to ? this.sm.on : 0, ground = g.touch * on, v = g.v;
    // 生成：着地后才有；数量随强度
    A.orbit += dt * ground * (30 + 150 * v * v);
    while (A.orbit >= 1) { A.orbit -= 1; o = O.get(); if (!o) { A.orbit = 0; break; }
      o.a = R() * 6.283; o.r = g.bw * (1.6 + R() * (2 + 4 * v)) + 30; o.h = R() * 6; o.vh = 0;
      o.k = R() < 0.45 ? 0 : R() < 0.7 ? 1 : 2; o.sz = 1 + R() * (1.5 + 2.5 * v); o.c = R(); o.rot = R() * 6.283; o.spin = (R() - 0.5) * 16;
      o.t = 0; o.life = 2.5 + R() * 3; }
    A.puffs += dt * ground * (4 + 14 * v);
    while (A.puffs >= 1) { A.puffs -= 1; o = U.get(); if (!o) { A.puffs = 0; break; }
      o.a = R() * 6.283; o.r = g.bw * (0.7 + R() * 0.9) + 8; o.h = R() * g.bw * 0.3; o.s = (12 + R() * 20) * (0.5 + v * 1.2);
      o.t = 0; o.life = 1.6 + R() * 1.6; o.w = R(); }
    var core = g.bw * 0.8 + 6;
    for (i = O.n - 1; i >= 0; i--) { o = O.a[i]; o.t += dt;
      if (o.t >= o.life || o.h > g.gy * 0.55) { O.kill(i); continue; }
      var near = clamp01(core * 2.2 / Math.max(core, o.r));
      o.a += dt * (1.2 + 3.2 * v) * Math.min(4, core * 1.6 / Math.max(core * 0.6, o.r)) * 1.7;
      o.r = Math.max(core * 0.75, o.r - dt * (30 + 110 * v) * (0.4 + 0.6 * near));
      o.vh += dt * (near * near * (40 + 160 * v) - 10); o.vh = Math.max(-20, o.vh); o.h = Math.max(0, o.h + o.vh * dt);
      o.rot += o.spin * dt; }
    for (i = U.n - 1; i >= 0; i--) { o = U.a[i]; o.t += dt;
      if (o.t >= o.life) { U.kill(i); continue; }
      o.a += dt * (0.9 + 1.8 * v); o.r += dt * (16 + 40 * v); o.h += dt * (5 + 20 * v); }
  };
  /** 漏斗中心线在某高度的 x（给粒子绕转用） */
  P.funnelX = function (y) {
    var g = this.tor.g; if (!g) return 0;
    var q = clamp01((y - g.yt) / (g.yb - g.yt));
    return mix(g.xt, g.xb, Math.pow(q, 0.85));
  };

  /** 碎叶 / 树枝 / 碎屑 / 尘粒：从上风边缘吹入，阵风调制密度与速度；龙卷时额外向漏斗底部旋转汇聚 */
  P.updateDebris = function (p, dt) {
    var D = this.debris, R = this.R, W = this.w, H = this.h, sm = this.sm, A = this.acc, N = this.N, s = this.seed, t = this.time, i, o;
    var dx = p.dx, dy = p.dy, sp = this.speed, on = sm.on;
    var dens = p.ty ? Math.pow(sm.pw, 1.4) : p.to ? 0.12 + 0.5 * sm.v * sm.v : 0;
    var rate = on * dens * (30 + 620 * dens) * (0.5 + 0.5 * this.gust) * (1 + 1.6 * this.bigE);
    A.debris += rate * dt;
    var g = this.tor.g, inflow = p.to && g ? sm.v * g.touch : 0;
    while (A.debris >= 1) {
      A.debris -= 1; o = D.get(); if (!o) { A.debris = 0; break; }
      var r = R();
      o.k = r < 0.38 ? 0 : r < 0.56 ? 1 : r < 0.72 ? 2 : 3;   // 叶 / 枝 / 碎片 / 尘
      o.sz = o.k === 3 ? 0.8 + R() * 1.2 : o.k === 1 ? 5 + R() * 10 : 2 + R() * 3.5;
      o.c = R(); o.ph = R() * 50; o.rot = R() * 6.283; o.spin = (R() - 0.5) * (o.k === 1 ? 10 : 22);
      o.m = o.k === 3 ? 1.2 : o.k === 1 ? 0.75 : 0.9 + R() * 0.25;  // 越轻越跟风
      o.t = 0; o.life = 2 + R() * 2.5; o.a = 0.55 + R() * 0.45;
      // 上风边：沿风方向的反向，落在画面外 20px；一部分直接在画面里出现（淡入），避免只有边缘有东西
      if (R() < 0.35 || sp < 120) { o.x = R() * W; o.y = R() * H; }
      else if (Math.abs(dx) > Math.abs(dy) * (W / H) * 0.6 ? R() < Math.abs(dx) / (Math.abs(dx) + Math.abs(dy)) : R() < 0.5) {
        o.x = dx > 0 ? -20 : W + 20; o.y = R() * H; }
      else { o.y = dy > 0 ? -20 : H + 20; o.x = R() * W; }
      o.vx = dx * sp * o.m; o.vy = dy * sp * o.m;
    }
    for (i = D.n - 1; i >= 0; i--) {
      o = D.a[i]; o.t += dt;
      if (o.t >= o.life || o.x < -60 || o.x > W + 60 || o.y < -60 || o.y > H + 60) { D.kill(i); continue; }
      // 湍流：低频噪波给横风扰动与上下翻飞
      var tu = N.noise3(s + 91, o.x * 0.006, o.y * 0.006, t * 0.8 + o.ph) * 2 - 1;
      var tx = dx * sp * o.m - dy * tu * sp * 0.35, ty = dy * sp * o.m + dx * tu * sp * 0.35 + Math.sin(t * 6 + o.ph) * 30 * o.m;
      if (inflow > 0) {
        var ex = o.x - g.xb, ey = (o.y - g.gy) * 2.4, dd = Math.sqrt(ex * ex + ey * ey) + 1;
        var pull = inflow * (260 + 420 * sm.v) * Math.min(1.6, 260 / dd);
        tx += (-ex / dd * 0.75 - ey / dd * 1.0) * pull; ty += (-ey / dd * 0.75 + ex / dd * 1.0) * pull * 0.42;
        if (dd < g.bw * 1.4 + 16) { o.vy -= 300 * dt; if (o.y < g.gy - 120) o.t = o.life; }
      }
      var k = 1 - Math.exp(-dt * 3.5 / o.m);
      o.vx += (tx - o.vx) * k; o.vy += (ty - o.vy) * k;
      o.x += o.vx * dt; o.y += o.vy * dt; o.rot += o.spin * dt * (0.5 + 0.5 * this.gust);
    }
  };

  /** 风线：贴地顺风的细长淡白流线（台风多、龙卷少）；阵风大时更长更亮 */
  P.updateLines = function (p, dt) {
    var L = this.lines, R = this.R, W = this.w, H = this.h, sm = this.sm, A = this.acc, i, o;
    var dens = p.ty ? sm.pw : p.to ? 0.35 * sm.v : 0;
    A.lines += dt * sm.on * dens * (10 + 70 * dens) * this.gust;
    while (A.lines >= 1) { A.lines -= 1; o = L.get(); if (!o) { A.lines = 0; break; }
      o.x = R() * W; o.y = R() * H; o.len = (60 + R() * 160) * (0.6 + 0.5 * dens); o.v = 0.8 + R() * 0.5;
      o.t = 0; o.life = 0.5 + R() * 0.7; o.a = (0.08 + 0.14 * R()) * (0.5 + dens); }
    var sp = this.speed;
    for (i = L.n - 1; i >= 0; i--) { o = L.a[i]; o.t += dt;
      if (o.t >= o.life) { L.kill(i); continue; }
      o.x += p.dx * sp * o.v * dt * 1.3; o.y += p.dy * sp * o.v * dt * 1.3; }
  };

  /** 浪尖：按面积均匀撒在水面格，垂直于风向的短亮弧，风大时被吹出飞沫 */
  P.updateCrests = function (p, dt) {
    var C = this.crests, R = this.R, sm = this.sm, A = this.acc, i, o;
    if (!this.wRects.length) { C.clear(); return; }
    var dens = sm.sea * sm.on;
    A.crests += dt * dens * dens * this.wArea / 600 * (0.6 + 0.4 * this.gust);
    while (A.crests >= 1) { A.crests -= 1; o = C.get(); if (!o) { A.crests = 0; break; }
      var u = R() * this.wArea, cum = this.wCum, lo = 0, hi = cum.length - 1;
      while (lo < hi) { var mid = (lo + hi) >> 1; if (cum[mid] < u) lo = mid + 1; else hi = mid; }
      var r = this.wRects[lo];
      o.x = r[0] + R() * r[2]; o.y = r[1] + R() * r[3]; o.len = (6 + R() * 18) * (0.6 + 0.8 * dens);
      o.t = 0; o.life = 0.7 + R() * 1.1; }
    var sp = this.speed * 0.12;
    for (i = C.n - 1; i >= 0; i--) { o = C.a[i]; o.t += dt;
      if (o.t >= o.life) { C.kill(i); continue; }
      o.x += p.dx * sp * dt; o.y += p.dy * sp * dt; }
  };

  P.draw = function (ctx, pass) {
    var p = this.p, sm = this.sm;
    if (!p || sm.on < 0.005) return;
    ctx.save();
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    if (pass === 'reflect') this.drawSea(ctx, p);
    else if (pass === 'precip') {
      if (this.dpr > 1.25) {
        // 高 dpr：在 CSS 分辨率离屏缓冲里画，再一次放大合成（同 rain.js）
        var pw = Math.ceil(this.w), ph = Math.ceil(this.h);
        if (!this.precipCv || this.precipCv.width !== pw || this.precipCv.height !== ph) this.precipCv = mkCanvas(pw, ph);
        var pc = this.precipCv.getContext('2d');
        pc.setTransform(1, 0, 0, 1, 0, 0); pc.globalAlpha = 1; pc.globalCompositeOperation = 'source-over'; pc.clearRect(0, 0, pw, ph);
        this.drawPrecip(pc, p);
        ctx.imageSmoothingEnabled = true; ctx.drawImage(this.precipCv, 0, 0, this.w, this.h);
      } else this.drawPrecip(ctx, p);
    }
    else if (pass === 'fog') this.drawFog(ctx, p);
    ctx.restore();
  };

  /** 水面：压暗翻涌、两层白沫条纹（沿风拉长、随风推移）、浪尖短弧与飞沫 */
  P.drawSea = function (ctx, p) {
    if (!this.wPath) return;
    var sm = this.sm, a = sm.sea * sm.on, B = this.wBox;
    if (a < 0.01) return;
    if (!this.pats) this.pats = { a: ctx.createPattern(this.foamA, 'repeat'), b: ctx.createPattern(this.foamB, 'repeat'), d: ctx.createPattern(this.darkTile, 'repeat') };
    var ang = Math.atan2(p.dy, p.dx), off = this.foamOff, t = this.time;
    ctx.save(); ctx.clip(this.wPath);
    // 压暗：深色噪波翻涌（慢平移）
    ctx.globalAlpha = 0.25 + 0.4 * a;
    ctx.translate(B[0], B[1]); ctx.rotate(ang);
    ctx.translate(-(off * 0.3) % 512, (t * 6) % 512);
    ctx.fillStyle = this.pats.d; ctx.fillRect(-1600, -1600, 3200, 3200);
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    // 白沫条纹：沿风方向拉长 3 倍，阵风时更亮
    var fa = sstep(0.12, 0.6, a) * (0.55 + 0.35 * clamp01(this.gust - 0.6));
    if (fa > 0.01) {
      ctx.globalAlpha = Math.min(0.95, fa);
      ctx.translate(B[0], B[1]); ctx.rotate(ang); ctx.scale(3.2, 0.9);
      ctx.translate(-(off / 3.2) % 768, Math.sin(t * 0.4) * 6);
      ctx.fillStyle = this.pats.a; ctx.fillRect(-900, -1900, 1800, 3800);
      ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
      ctx.globalAlpha = Math.min(0.9, fa * sstep(0.35, 0.85, a) * 1.1);
      ctx.translate(B[0], B[1]); ctx.rotate(ang); ctx.scale(2.2, 0.8);
      ctx.translate(-(off * 1.3 / 2.2) % 256, 0);
      ctx.fillStyle = this.pats.b; ctx.fillRect(-1300, -2200, 2600, 4400);
      ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    }
    // 浪尖：垂直于风向的短亮弧，生命中段最亮；风大时背风侧拖出飞沫
    var C = this.crests, nx = -p.dy, ny = p.dx, spray = sstep(0.5, 0.95, a);
    ctx.globalAlpha = 1; ctx.lineCap = 'round';
    ctx.strokeStyle = 'rgba(248,251,252,0.95)'; ctx.lineWidth = 2;
    ctx.beginPath();
    for (var i = 0; i < C.n; i++) {
      var o = C.a[i], f = o.t / o.life, al = Math.sin(f * Math.PI), L = o.len * (0.4 + 0.6 * al) * 0.5;
      if (al < 0.15) continue;
      ctx.moveTo(o.x - nx * L, o.y - ny * L);
      ctx.quadraticCurveTo(o.x + p.dx * 3, o.y + p.dy * 3, o.x + nx * L, o.y + ny * L);
    }
    ctx.stroke();
    if (spray > 0.01) {
      ctx.fillStyle = 'rgba(236,242,246,' + (0.35 * spray).toFixed(3) + ')';
      for (i = 0; i < C.n; i++) {
        o = C.a[i]; f = o.t / o.life; if (f < 0.3) continue;
        var dd = (f - 0.3) * 40 * (0.5 + spray);
        ctx.fillRect(o.x + p.dx * dd - 1.5, o.y + p.dy * dd - 1.5, 3 + 4 * spray, 2);
      }
    }
    ctx.restore();
  };

  // 碎屑配色：叶（绿 / 黄绿 / 枯黄）、枝（褐）、碎片（灰褐 / 瓦红 / 草黄）、尘
  var LEAF = ['rgba(74,112,52,A)', 'rgba(118,138,58,A)', 'rgba(150,128,62,A)'];
  var FRAG = ['rgba(108,96,84,A)', 'rgba(150,84,62,A)', 'rgba(176,156,98,A)'];
  function colA(c, a) { return c.replace('A', a.toFixed(3)); }

  P.drawPrecip = function (ctx, p) {
    var sm = this.sm, on = sm.on, t = this.time, i, o;
    // 1) 树冠 / 屋顶摆动：浅色剪影顺风来回错位成残影（不改底图，只叠一层淡影）
    var sw = sm.sway * on;
    if (this.silCv && sw > 0.03) {
      var amp = (1.2 + 3.5 * sw) * (0.6 + 0.4 * this.gust), ph = Math.sin(t * (5 + 4 * sw)) * 0.6 + Math.sin(t * 11.3) * 0.4;
      ctx.globalAlpha = 0.05 + 0.13 * sw;
      ctx.drawImage(this.silCv, p.dx * amp * ph, p.dy * amp * ph * 0.5 - amp * 0.3, this.w, this.h);
      ctx.globalAlpha = 1;
    }
    // 2) 上沿抖动光带：剪影上沿的点各自沿风方向抖出一小段亮线（风越大越长、越密）
    var E = this.edges;
    if (E && sw > 0.03) {
      var n = Math.min(E.length, Math.round(E.length * (0.2 + 0.8 * sw))), nx = p.dx, ny = p.dy;
      ctx.lineCap = 'butt'; ctx.lineWidth = 1.2;
      ctx.strokeStyle = 'rgba(232,240,236,' + (0.16 + 0.3 * sw).toFixed(3) + ')';
      ctx.beginPath();
      for (i = 0; i < n; i++) {
        var e = E[i], w = Math.sin(t * (6 + 5 * e.c) + e.ph + e.x * 0.03);
        if (w < 0.2) continue;
        var L = (2 + 9 * sw * this.gust) * w;
        ctx.moveTo(e.x, e.y + 1); ctx.lineTo(e.x + nx * L, e.y + 1 + ny * L * 0.5 - L * 0.15);
      }
      ctx.stroke();
    }
    // 3) 风线
    var Ls = this.lines;
    if (Ls.n) {
      // 按亮度分 4 档批量描边；每条分头（亮）、尾（半长、更淡）两段，代替逐条渐变
      ctx.lineWidth = 1; ctx.lineCap = 'butt';
      for (var b = 0; b < 4; b++) {
        var lo = b * 0.08, hi = lo + 0.08, any = false;
        ctx.beginPath();
        for (i = 0; i < Ls.n; i++) {
          o = Ls.a[i]; var al = o.a * Math.sin(o.t / o.life * Math.PI);
          if (al < lo || (al >= hi && b < 3) || al < 0.01) continue;
          ctx.moveTo(o.x, o.y); ctx.lineTo(o.x - p.dx * o.len * 0.45, o.y - p.dy * o.len * 0.45); any = true;
        }
        if (any) { ctx.strokeStyle = 'rgba(236,242,246,' + (lo + 0.04).toFixed(3) + ')'; ctx.stroke(); }
        ctx.beginPath(); any = false;
        for (i = 0; i < Ls.n; i++) {
          o = Ls.a[i]; al = o.a * Math.sin(o.t / o.life * Math.PI);
          if (al < lo || (al >= hi && b < 3) || al < 0.01) continue;
          ctx.moveTo(o.x - p.dx * o.len * 0.45, o.y - p.dy * o.len * 0.45); ctx.lineTo(o.x - p.dx * o.len, o.y - p.dy * o.len); any = true;
        }
        if (any) { ctx.strokeStyle = 'rgba(236,242,246,' + ((lo + 0.04) * 0.4).toFixed(3) + ')'; ctx.stroke(); }
      }
    }
    if (p.to || sm.v > 0.02) this.drawTornado(ctx, p);
    // 4) 碎屑：按种类和色桶分批描边，避免逐个 setTransform
    this.drawDebrisSet(ctx, this.debris.a, this.debris.n, function (o) { return { x: o.x, y: o.y }; });
  };

  /** 批量画碎屑：叶 = 粗短线，枝 = 线 + 侧杈，碎片 = 方头短线，尘 = 小点；fade 按生命首尾淡入淡出 */
  P.drawDebrisSet = function (ctx, arr, n, pos) {
    var on = this.sm.on, b, i, o, q, f, a, c, s;
    ctx.lineCap = 'round';
    for (b = 0; b < 3; b++) {           // 叶
      ctx.strokeStyle = colA(LEAF[b], 0.9 * on); ctx.beginPath();
      for (i = 0; i < n; i++) { o = arr[i]; if (o.k !== 0 || ((o.c * 3) | 0) !== b) continue;
        q = pos(o); c = Math.cos(o.rot) * o.sz, s = Math.sin(o.rot) * o.sz * Math.abs(Math.cos(o.rot * 1.7));
        ctx.moveTo(q.x - c, q.y - s); ctx.lineTo(q.x + c, q.y + s); }
      ctx.lineWidth = 2.2; ctx.stroke();
    }
    ctx.strokeStyle = colA('rgba(86,64,44,A)', 0.92 * on); ctx.lineWidth = 1.3; ctx.beginPath();
    for (i = 0; i < n; i++) { o = arr[i]; if (o.k !== 1) continue;   // 枝
      q = pos(o); c = Math.cos(o.rot) * o.sz * 0.5; s = Math.sin(o.rot) * o.sz * 0.5;
      ctx.moveTo(q.x - c, q.y - s); ctx.lineTo(q.x + c, q.y + s);
      ctx.moveTo(q.x + c * 0.2, q.y + s * 0.2); ctx.lineTo(q.x + c * 0.2 - s * 0.5 + c * 0.3, q.y + s * 0.2 + c * 0.5 + s * 0.3); }
    ctx.stroke();
    ctx.lineCap = 'butt';
    for (b = 0; b < 3; b++) {           // 碎片
      ctx.strokeStyle = colA(FRAG[b], 0.88 * on); ctx.beginPath();
      for (i = 0; i < n; i++) { o = arr[i]; if (o.k !== 2 || ((o.c * 3) | 0) !== b) continue;
        q = pos(o); c = Math.cos(o.rot) * o.sz * 0.6; s = Math.sin(o.rot) * o.sz * 0.6;
        ctx.moveTo(q.x - c, q.y - s); ctx.lineTo(q.x + c, q.y + s); }
      ctx.lineWidth = 2.4; ctx.stroke();
    }
    ctx.fillStyle = colA('rgba(150,136,112,A)', 0.6 * on);   // 尘
    for (i = 0; i < n; i++) { o = arr[i]; if (o.k !== 3) continue; q = pos(o); ctx.fillRect(q.x, q.y, o.sz * 1.6, o.sz); }
  };

  /** 龙卷：后半圈碎屑 → 漏斗缓冲 → 地面尘裙 + 尘环团块 → 前半圈碎屑 */
  P.drawTornado = function (ctx, p) {
    var T = this.tor, g = T.g, box = T.box, on = p.to ? this.sm.on : 0, self = this, tmp = { x: 0, y: 0 };
    if (!g || on < 0.01) return;
    var O = this.orbit, U = this.puffs, i, o;
    function orbitPos(front) {
      return function (o) {
        var sn = Math.sin(o.a);
        if ((sn >= 0) !== front) { tmp.x = -9999; tmp.y = -9999; return tmp; }
        var cx = self.funnelX(g.gy - o.h);
        tmp.x = cx + Math.cos(o.a) * o.r; tmp.y = g.gy - o.h + sn * o.r * 0.3; return tmp;
      };
    }
    this.drawDebrisSet(ctx, O.a, O.n, orbitPos(false));
    ctx.globalAlpha = on; ctx.imageSmoothingEnabled = true;
    ctx.drawImage(this.funCv, box[0], box[1], box[2], box[3]);
    ctx.globalAlpha = 1;
    // 地面尘裙：着地点一圈扁平褐色雾
    var dust = g.touch * on * sstep(0.22, 0.5, g.v);
    if (dust > 0.01) {
      var rx = g.bw * 1.5 + 24 + 90 * g.v, gr = ctx.createRadialGradient(g.xb, g.gy, 0, g.xb, g.gy, rx);
      gr.addColorStop(0, 'rgba(132,116,94,' + (0.75 * dust).toFixed(3) + ')');
      gr.addColorStop(0.55, 'rgba(126,112,94,' + (0.4 * dust).toFixed(3) + ')'); gr.addColorStop(1, 'rgba(120,110,96,0)');
      ctx.save(); ctx.translate(g.xb, g.gy); ctx.scale(1, 0.34); ctx.translate(-g.xb, -g.gy);
      ctx.fillStyle = gr; ctx.fillRect(g.xb - rx, g.gy - rx, rx * 2, rx * 2); ctx.restore();
      for (i = 0; i < U.n; i++) {
        o = U.a[i]; var f = o.t / o.life, al = Math.sin(f * Math.PI) * dust * (0.55 + 0.3 * o.w);
        var px = g.xb + Math.cos(o.a) * o.r, py = g.gy - o.h + Math.sin(o.a) * o.r * 0.3, s = o.s * (0.7 + f * 0.8);
        ctx.globalAlpha = al; ctx.drawImage(this.dustSp, px - s, py - s * 0.7, s * 2, s * 1.4);
      }
      ctx.globalAlpha = 1;
    }
    this.drawDebrisSet(ctx, O.a, O.n, orbitPos(true));
  };

  /** fog：快速低云影、眼墙白茫雨幕、风眼放亮与四周眼墙暗边、龙卷压顶暗云与下风尘雾 */
  P.drawFog = function (ctx, p) {
    var sm = this.sm, on = sm.on, W = this.w, H = this.h, gr;
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(this.cloudCv, 0, 0, W, H);
    if (sm.sheet * on > 0.01) ctx.drawImage(this.sheetCv, 0, 0, W, H);
    // 台风整体灰白水汽（能见度下降），随风力
    if (p.ty) {
      var haze = on * (0.04 + 0.12 * sstep(0.4, 1.1, sm.pw)) * (1 - sm.bright);
      if (haze > 0.01) { ctx.fillStyle = 'rgba(190,198,206,' + haze.toFixed(3) + ')'; ctx.fillRect(0, 0, W, H); }
    }
    // 风眼：中间放亮偏暖，画面四角压着眼墙的暗云
    var br = sm.bright * on;
    if (br > 0.01) {
      ctx.fillStyle = 'rgba(255,246,222,' + (0.1 * br).toFixed(3) + ')'; ctx.fillRect(0, 0, W, H);
      var R0 = Math.min(W, H) * 0.5, R1 = Math.sqrt(W * W + H * H) * 0.62;
      gr = ctx.createRadialGradient(W * 0.5, H * 0.45, R0, W * 0.5, H * 0.45, R1);
      gr.addColorStop(0, 'rgba(40,46,56,0)'); gr.addColorStop(0.6, 'rgba(40,46,56,' + (0.32 * br).toFixed(3) + ')');
      gr.addColorStop(1, 'rgba(30,36,44,' + (0.62 * br).toFixed(3) + ')');
      ctx.fillStyle = gr; ctx.fillRect(0, 0, W, H);
    }
    if (p.to) {
      var v = sm.v, top = H * (0.22 + 0.2 * v);
      gr = ctx.createLinearGradient(0, 0, 0, top);
      gr.addColorStop(0, 'rgba(18,22,28,' + (on * (0.22 + 0.18 * v)).toFixed(3) + ')'); gr.addColorStop(1, 'rgba(18,22,28,0)');
      ctx.fillStyle = gr; ctx.fillRect(0, 0, W, top);
      var g = this.tor.g;
      if (g && g.touch > 0.1) {   // 下风尘雾：漏斗底部拖向下风的一片褐雾
        var a = on * g.touch * 0.15 * v, rx = 160 + 360 * v, cx = g.xb + p.dx * rx * 0.5, cy = g.gy + p.dy * rx * 0.2;
        gr = ctx.createRadialGradient(cx, cy, 0, cx, cy, rx);
        gr.addColorStop(0, 'rgba(140,124,100,' + a.toFixed(3) + ')'); gr.addColorStop(1, 'rgba(140,124,100,0)');
        ctx.fillStyle = gr; ctx.fillRect(cx - rx, cy - rx, rx * 2, rx * 2);
      }
    }
  };

  P.stats = function () {
    var g = this.tor.g;
    return { debris: this.debris.n, lines: this.lines.n, crests: this.crests.n, orbit: this.orbit.n, puffs: this.puffs.n,
      gust: +this.gust.toFixed(2), bigGust: +this.bigE.toFixed(2), edges: this.edges ? this.edges.length : 0,
      phase: this.p.phase, funnel: g && this.p.to ? { x: Math.round(g.xb), touch: +g.touch.toFixed(2) } : null };
  };
  P.dispose = function () {
    this.scene = null; this.edges = null; this.silCv = this.rimCv = null; this.wPath = null; this.pats = null;
    this.debris.clear(); this.lines.clear(); this.crests.clear(); this.orbit.clear(); this.puffs.clear();
  };

  /** 给 WeatherFX_rain 的状态：台风外围 / 眼墙 → storm 大雨；风眼 → 雨停（kind=clear，地面湿度照旧，由 rain 画）；龙卷 → storm */
  function rainState(st) {
    st = st || {}; var o = copy(st), I = clamp01(+st.intensity || 0), w = copy(st.wind || {});
    if (st.kind === 'typhoon') {
      var ph = phaseOf(st), cf = 0.9 + 0.05 * (catOf(st) - 1);
      w.speed = Math.max(0.7, +w.speed || 0);
      if (ph === 'eye') { o.kind = 'clear'; o.intensity = 0; w.speed *= 0.12; }
      else { o.kind = 'storm'; o.intensity = clamp01((ph === 'eyewall' ? 0.78 + 0.22 * I : 0.22 + 0.7 * I) * cf);
        o.lightning = st.lightning != null ? +st.lightning : ph === 'eyewall' ? 0.25 : 0.12; }
      o.precipitation = { type: 'rain', rate: o.intensity };
    } else if (st.kind === 'tornado') {
      var v = vortexOf(st);
      o.kind = 'storm'; o.intensity = clamp01(Math.max(I, 0.45 + 0.45 * v));
      o.lightning = st.lightning != null ? +st.lightning : 0.45 + 0.4 * v;
    }
    o.wind = w; return o;
  }
  /** 给 WeatherFX_daylight 的状态：天色按 storm 压暗；风眼转成少云、天空转亮 */
  function daylightState(st) {
    st = st || {}; var o = copy(st);
    if (st.kind === 'typhoon') {
      if (phaseOf(st) === 'eye') { o.kind = 'cloudy'; o.cloud_cover = 0.4; o.intensity = 0.3; }
      else if (phaseOf(st) === 'eyewall') { o.kind = 'storm'; o.cloud_cover = 1; o.intensity = Math.max(+st.intensity || 0, 0.9); }
      else {   // 外围雨带：弱档按 rain 调色（阴而不黑），强档才到 storm
        var Io = clamp01(+st.intensity || 0);
        o.kind = Io < 0.35 ? 'rain' : 'storm'; o.cloud_cover = 0.8 + 0.2 * Io; o.intensity = Io < 0.35 ? 0.15 + Io : Io;
      }
    } else if (st.kind === 'tornado') {   // 远处细漏斗时天色只是阴雨，着地后才压成雷暴暗色
      var vt = vortexOf(st);
      o.kind = vt < 0.3 ? 'rain' : 'storm'; o.cloud_cover = 0.85 + 0.15 * vt; o.intensity = vt < 0.3 ? 0.3 + vt : Math.max(+st.intensity || 0, vt);
    }
    return o;
  }

  var API = { kinds: Object.keys(KINDS), passes: ['reflect', 'precip', 'fog'],
    create: function (opts) { return new Layer(opts); }, rainState: rainState, daylightState: daylightState };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.WeatherFX_wind = API;
})(this);
