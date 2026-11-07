/*
 * 织梦 · 天气美术：雨天与风暴叠层（drizzle 毛毛雨 / rain 雨 / storm 雷暴 / sleet 雨夹雪里的雨）
 * 接口见 docs/weather-spec.md 第 3 节：create → resize → setScene → update(state, dt) → draw(ctx, pass) → dispose
 * pass：ground（湿地、水洼）、reflect（水面雨麻点、闪电倒影）、precip（雨丝、溅点、涟漪、檐滴）、
 *       fog（云影、雨帘、暴雨水雾、阴雨压暗）、flash（闪电）。
 * 坐标：scene 与绘制都用 CSS 像素；draw 内部自己 setTransform(dpr)，调用方传原始 2D context 即可。
 * 只读天气状态，不推断天气；所有随机由 seed 派生。
 */
(function (root) {
  'use strict';
  var KINDS = { drizzle: 1, rain: 1, storm: 1, sleet: 1, hail: 1 };
  var LOW = 3;                 // 地面噪波缓冲：每 LOW 个 CSS 像素一格，平滑放大
  var CGX = 36, CGY = 24;      // 雨帘密度网格
  var KW = 72, KH = 46;        // 云影低分辨率缓冲
  var FOG_DS = 4;              // 雾层缓冲降采样倍数
  function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }
  function sstep(a, b, x) { var t = clamp01((x - a) / (b - a)); return t * t * (3 - 2 * t); }
  function mix(a, b, t) { return a + (b - a) * t; }
  function mkCanvas(w, h) { var c = document.createElement('canvas'); c.width = Math.max(1, w | 0); c.height = Math.max(1, h | 0); return c; }

  // 对象池：激活的放在前 n 个，删除时与末尾交换
  function Pool(cap, make) { this.a = []; this.n = 0; this.cap = cap; for (var i = 0; i < cap; i++) this.a.push(make()); }
  Pool.prototype.get = function () { return this.n < this.cap ? this.a[this.n++] : null; };
  Pool.prototype.kill = function (i) { var t = this.a[i]; this.a[i] = this.a[--this.n]; this.a[this.n] = t; };
  Pool.prototype.clear = function () { this.n = 0; };

  // 雨丝三层：远（细短淡慢）、中、近（粗长亮快）
  var LAYERS = [
    { share: 0.46, speed: 0.48, len: 0.55, width: 0.7, alpha: 0.55, H: [160, 420] },
    { share: 0.34, speed: 0.72, len: 0.8,  width: 1.0, alpha: 0.8,  H: [260, 620] },
    { share: 0.20, speed: 1.0,  len: 1.0,  width: 1.45, alpha: 1.0, H: [380, 900] }
  ];
  var DROP_CAP = 3200;

  function Layer(opts) {
    opts = opts || {};
    this.N = opts.noise || root.WeatherNoise;
    if (!this.N) throw new Error('WeatherFX_rain 需要 WeatherNoise（noise.js）');
    this.seed = (opts.seed >>> 0) || 1;
    this.tint = opts.tint !== false;          // 阴雨整体压暗；与 daylight 合成时可传 tint:false
    this.R = this.N.rng(this.seed ^ 0x5a17c3);
    this.w = 1; this.h = 1; this.dpr = 1;
    this.scene = null; this.time = 0; this.p = derive(null, 0, this);
    this.drops = []; this.nDrops = 0;
    for (var i = 0; i < DROP_CAP; i++) this.drops.push({ lx: 0, ly: 0, H: 0, v: 0, t: 0, life: 1, L: 0, r: 0, live: false });
    this.sparks = new Pool(1800, function () { return { x: 0, y: 0, vx: 0, vy: 0, t: 0, life: 1 }; });
    this.rings = new Pool(900, function () { return { x: 0, y: 0, r0: 0, r1: 0, t: 0, life: 1, a: 1, flat: 0.42 }; });
    this.drips = new Pool(400, function () { return { x: 0, y: 0, vy: 0, gy: 0 }; });
    // 冰雹：下落中的冰粒（定长数组，同雨丝）、落地弹跳 / 停留的冰粒池、白色击打痕池
    this.hfall = []; this.nHail = 0; this.hSlant = 0; this.hailKey = -1;
    for (i = 0; i < 1600; i++) this.hfall.push({ x: 0, y: 0, H: 0, H0: 1, r: 1, v: 1, rot: 0, live: false });
    this.stones = new Pool(1800, function () { return { x: 0, y: 0, z: 0, vx: 0, vy: 0, vz: 0, r: 1, rot: 0, spin: 0, st: 0, nb: 0, t: 0, life: 1 }; });
    this.marks = new Pool(300, function () { return { x: 0, y: 0, r: 2, t: 0, life: 1 }; });
    this.eaves = [];
    this.curtain = new Float32Array(CGX * CGY);
    this.curtainCv = mkCanvas(CGX, CGY); this.curtainImg = this.curtainCv.getContext('2d').createImageData(CGX, CGY);
    this.cloudCv = mkCanvas(KW, KH); this.cloudImg = this.cloudCv.getContext('2d').createImageData(KW, KH);
    this.cloudOff = [0, 0]; this.curtainOff = 0; this.frame = 0;
    this.flash = 0; this.strikeT = -1; this.pulses = []; this.bolt = null; this.boltX = 0;
    this.nextStrike = 2 + this.R() * 4; this.glowX = 0.5;
    this.gust = 1; this.slant = 0;
    this.groundKey = ''; this.fW = 0; this.fH = 0;
    this.bakeTextures();
  }

  /** 由天气状态派生本帧绘制参数（只读 state，不推断天气） */
  function derive(state, time, L) {
    state = state || {};
    var kind = state.kind, I = clamp01(+state.intensity || 0), on = !!KINDS[kind];
    var e = 0;
    if (kind === 'drizzle') e = 0.05 + I * 0.22;
    else if (kind === 'rain') e = I;
    else if (kind === 'storm') e = I < 0.3 ? I * 0.6 : I;
    else if (kind === 'sleet') e = I * 0.7;
    else if (kind === 'hail') e = I * 0.35;          // 冰雹常夹着雨，但雨量小
    var g = state.ground || {}, w = state.wind || {};
    var pt = state.precipitation && state.precipitation.type, hail = on && (kind === 'hail' || pt === 'hail');
    if (hail && kind !== 'hail') e *= 0.6;            // 雷暴夹冰雹：雨量让一部分给冰粒，避免满屏白噪
    var dir = (+w.dir_deg || 0) * Math.PI / 180, sp = clamp01(+w.speed || 0);
    return {
      on: on, kind: kind || 'clear', I: I, e: on ? e : 0,
      drizzle: kind === 'drizzle', storm: kind === 'storm', sleet: kind === 'sleet',
      hail: hail, hI: hail ? I : 0, hailCover: clamp01(+g.hail_cover || 0),
      wx: Math.sin(dir) * sp, wy: -Math.cos(dir) * sp, wind: sp, gust: clamp01(+w.gust || 0),
      lightning: on ? clamp01(+state.lightning || 0) : 0,
      wet: clamp01(g.wetness != null ? +g.wetness : 0), puddles: clamp01(g.puddles != null ? +g.puddles : 0),
      cloud: clamp01(state.cloud_cover != null ? +state.cloud_cover : (on ? 0.85 : 0)),
      vis: clamp01(state.visibility != null ? +state.visibility : 1),
      hour: state.time && state.time.hour != null ? +state.time.hour : 12
    };
  }

  var P = Layer.prototype;

  /** 预烘可平铺噪波：细纹高光、水雾团、水面碎纹，全部做成 pattern 平移放大 */
  P.bakeTextures = function () {
    var N = this.N, s = this.seed;
    function toCanvas(size, data, rgb, aMap) {
      var c = mkCanvas(size, size), g = c.getContext('2d'), img = g.createImageData(size, size), d = img.data;
      for (var i = 0; i < size * size; i++) { d[i * 4] = rgb[0]; d[i * 4 + 1] = rgb[1]; d[i * 4 + 2] = rgb[2]; d[i * 4 + 3] = aMap(data[i] / 255); }
      g.putImageData(img, 0, 0); return c;
    }
    this.detail = N.tile(s + 101, 128, 8, 3);                 // 细纹：湿地高光、水洼采样
    this.mistTile = toCanvas(256, N.tile(s + 202, 256, 4, 4), [218, 224, 232], function (v) { return Math.round(200 * sstep(0.3, 0.85, v)); });
    this.ruffle = toCanvas(128, N.tile(s + 303, 128, 16, 2), [214, 226, 238], function (v) { return Math.round(255 * sstep(0.62, 0.86, v) * 0.9); });
    this.mistPat = null; this.rufflePat = null;
  };

  P.resize = function (w, h, dpr) {
    this.w = Math.max(1, w | 0); this.h = Math.max(1, h | 0); this.dpr = dpr || 1;
    this.buildField();
  };

  P.setScene = function (scene) {
    this.scene = scene || null;
    var eaves = [];
    if (scene && scene.buildings) scene.buildings.forEach(function (b) {
      var bottom = b.y + b.h, top = b.roofY != null ? b.roofY : b.y;
      // 檐口：没给 eaveY 时按 3/4 视角估在屋顶上沿与地脚之间偏上处
      var ey = b.eaveY != null ? b.eaveY : top + (bottom - top) * 0.42;
      if (b.w > 10) eaves.push({ x0: b.x + 3, x1: b.x + b.w - 3, y: ey, gy: bottom - 2, len: b.w });
    });
    this.eaves = eaves;
    this.buildField();
  };

  /**
   * 地面噪波场（低分辨率，只在 resize / setScene 时算一次）：
   *  fA = 域扭曲 fbm（warp2，纵向压扁符合 3/4 视角）→ 秩变换成均匀分布，阈值直接对应水洼覆盖率
   *  fB = fbm2，决定小湿度时哪些斑块先湿
   *  mask = 地面矩形内、且不在建筑包围盒里
   */
  P.buildField = function () {
    var N = this.N, s = this.seed, gw = Math.ceil(this.w / LOW), gh = Math.ceil(this.h / LOW), n = gw * gh;
    if (gw === this.fW && gh === this.fH && this.fieldScene === this.scene && this.fA) return;
    this.fW = gw; this.fH = gh; this.fieldScene = this.scene;
    var fA = new Float32Array(n), fB = new Float32Array(n), fC = new Float32Array(n), mask = new Uint8Array(n);
    for (var y = 0; y < gh; y++) for (var x = 0; x < gw; x++) {
      var X = x * LOW, Y = y * LOW, i = y * gw + x;
      fA[i] = N.warp2(s + 11, X / 110, Y / 46, 1.1, 4);   // 纵向压扁：3/4 视角下水洼是横向扁长的
      fB[i] = N.fbm2(s + 23, X / 70, Y / 50, 3);
      fC[i] = N.fbm2(s + 37, X / 46, Y / 30, 3);          // 积冰分布：比湿斑更碎
    }
    rankUniform(fA); rankUniform(fB); rankUniform(fC); this.fC = fC; this.hailKey = -1;
    var sc = this.scene;
    if (!sc || !sc.ground || !sc.ground.length) mask.fill(1);
    else {
      sc.ground.forEach(function (r) { fillMask(mask, gw, gh, r[0], r[1], r[2], r[3], 1); });
      (sc.water || []).forEach(function (r) { fillMask(mask, gw, gh, r[0], r[1], r[2], r[3], 0); });
      (sc.buildings || []).forEach(function (b) { fillMask(mask, gw, gh, b.x + 2, b.y, b.w - 4, b.h - 6, 0); });
    }
    var zone = new Uint8Array(n);
    if (!sc) zone.fill(1);
    else {
      for (var k = 0; k < n; k++) zone[k] = mask[k] ? 1 : 0;
      (sc.water || []).forEach(function (r) { fillMask(zone, gw, gh, r[0], r[1], r[2], r[3], 2); });
      (sc.buildings || []).forEach(function (b) { var top = b.roofY != null ? b.roofY : b.y; fillMask(zone, gw, gh, b.x + 3, top + 4, b.w - 6, (b.y + b.h - top) * 0.45, 3); });
    }
    // 羽化遮罩：两遍盒式模糊，让湿斑 / 水洼在建筑脚下、水岸边渐隐而不是被矩形切断
    var fe = new Float32Array(n), tmp = new Float32Array(n);
    for (k = 0; k < n; k++) fe[k] = mask[k];
    boxBlur(fe, tmp, gw, gh, 3); boxBlur(fe, tmp, gw, gh, 3);
    for (k = 0; k < n; k++) fe[k] = mask[k] ? sstep(0.45, 1, fe[k]) : 0;
    // 湿地压暗用的遮罩只排除水面，不排除建筑（湿屋顶本来也该暗；排除包围盒会在房子周围留矩形亮晕）
    var wmask = new Uint8Array(n);
    if (!sc || !sc.ground || !sc.ground.length) wmask.fill(1);
    else {
      sc.ground.forEach(function (r) { fillMask(wmask, gw, gh, r[0], r[1], r[2], r[3], 1); });
      (sc.water || []).forEach(function (r) { fillMask(wmask, gw, gh, r[0], r[1], r[2], r[3], 0); });
    }
    this.fA = fA; this.fB = fB; this.mask = mask; this.wmask = wmask; this.zone = zone; this.feather = fe;
    this.puddle = new Uint8Array(n);
    this.groundCv = mkCanvas(gw, gh); this.groundImg = this.groundCv.getContext('2d').createImageData(gw, gh);
    this.puddleCv = mkCanvas(gw, gh); this.puddleImg = this.puddleCv.getContext('2d').createImageData(gw, gh);
    this.groundKey = '';
  };
  function fillMask(mask, gw, gh, x, y, w, h, v) {
    var x0 = Math.max(0, Math.floor(x / LOW)), y0 = Math.max(0, Math.floor(y / LOW));
    var x1 = Math.min(gw, Math.ceil((x + w) / LOW)), y1 = Math.min(gh, Math.ceil((y + h) / LOW));
    for (var yy = y0; yy < y1; yy++) for (var xx = x0; xx < x1; xx++) mask[yy * gw + xx] = v;
  }
  function boxBlur(a, tmp, w, h, r) {   // 可分离盒式模糊（横 → 竖），r 为半径格数
    var x, y, s, k, d = 2 * r + 1;
    for (y = 0; y < h; y++) { s = 0; for (k = -r; k <= r; k++) s += a[y * w + Math.min(w - 1, Math.max(0, k))];
      for (x = 0; x < w; x++) { tmp[y * w + x] = s / d; s += a[y * w + Math.min(w - 1, x + r + 1)] - a[y * w + Math.max(0, x - r)]; } }
    for (x = 0; x < w; x++) { s = 0; for (k = -r; k <= r; k++) s += tmp[Math.min(h - 1, Math.max(0, k)) * w + x];
      for (y = 0; y < h; y++) { a[y * w + x] = s / d; s += tmp[Math.min(h - 1, y + r + 1) * w + x] - tmp[Math.max(0, y - r) * w + x]; } }
  }
  function rankUniform(a) {   // 把噪波值换成它的分位数，得到 [0,1] 均匀分布
    var idx = new Uint32Array(a.length); for (var i = 0; i < a.length; i++) idx[i] = i;
    var sorted = Array.prototype.slice.call(idx).sort(function (p, q) { return a[p] - a[q]; });
    var out = new Float32Array(a.length), inv = 1 / Math.max(1, a.length - 1);
    for (var k = 0; k < sorted.length; k++) out[sorted[k]] = k * inv;
    a.set(out);
  }

  // 分区查询：0 无 / 1 地面 / 2 水面 / 3 建筑（低分辨率格）
  P.zoneAt = function (x, y) {
    if (!this.zone) return 1;
    var gx = (x / LOW) | 0, gy = (y / LOW) | 0;
    if (gx < 0 || gy < 0 || gx >= this.fW || gy >= this.fH) return 0;
    return this.zone[gy * this.fW + gx];
  };
  P.puddleAt = function (x, y) {
    var gx = (x / LOW) | 0, gy = (y / LOW) | 0;
    if (gx < 0 || gy < 0 || gx >= this.fW || gy >= this.fH) return 0;
    return this.puddle[gy * this.fW + gx];
  };
  /** 雨帘密度（噪波格最近邻查表），返回 0.2–1.8 左右的倍率 */
  P.curtainAt = function (x, y) {
    var gx = Math.min(CGX - 1, Math.max(0, (x / this.w * CGX) | 0)), gy = Math.min(CGY - 1, Math.max(0, (y / this.h * CGY) | 0));
    return this.curtain[gy * CGX + gx];
  };

  P.update = function (state, dt) {
    dt = Math.max(0, Math.min(0.1, +dt || 0));
    this.time += dt; this.frame++;
    var p = this.p = derive(state, this.time, this);
    var N = this.N, s = this.seed, t = this.time;
    // 阵风：一维 fbm 随时间起伏，风暴额外加幅
    var gAmp = p.gust * 0.8 + (p.storm ? 0.25 + 0.35 * p.I : 0);
    this.gust = Math.max(0.2, 1 + gAmp * (N.fbm2(s + 5, t * 0.45, 0.37, 3) * 2 - 1) * 1.6);
    this.vx = p.wx * (80 + 760 * p.wind) * this.gust;           // 雨的水平速度（px/s，符号 = 吹向）
    this.vBase = p.drizzle ? 360 : 900 + 520 * p.e + (p.storm ? 120 : 0);
    this.slant = this.vx / this.vBase;
    // 雨帘：3D 噪波（第三维是时间），随风横移；每 3 帧更新一次
    this.curtainOff += (this.vx * 0.6 + 40) * dt / Math.max(1, this.w) * 3.2;
    if (this.frame % 3 === 1 || this.frame < 3) this.updateCurtain(p);
    // 云影偏移：随风平移，风暴时更快
    var cs = (p.storm ? 2.6 : 1) * (0.25 + 1.4 * p.wind);
    this.cloudOff[0] -= p.wx * cs * dt * 0.09 + dt * 0.006; this.cloudOff[1] -= p.wy * cs * dt * 0.09;
    if (this.frame % 3 === 2 || this.frame < 3) this.updateClouds(p);
    this.updateGroundBuffers(p);          // 地面湿度 / 积冰是累积量：雨停后也照常画，直到它退掉
    this.updateHailGround(p);
    this.updateDrops(p, dt);
    this.updateSplashes(p, dt);
    this.updateDrips(p, dt);
    this.updateHail(p, dt);
    this.updateLightning(p, dt);
  };

  P.updateCurtain = function (p) {
    var N = this.N, s = this.seed, t = this.time, c = this.curtain, d = this.curtainImg.data;
    var str = p.drizzle ? 0.45 : p.storm ? 0.85 : 0.7;
    for (var y = 0; y < CGY; y++) for (var x = 0; x < CGX; x++) {
      // 横向频率高、纵向低：形成斜向一道道的雨帘
      var n = N.fbm3(s + 41, x / CGX * 3.2 - this.curtainOff + y * 0.035 * this.slant * 6, y / CGY * 1.4, t * 0.22, 2);
      var v = sstep(0.28, 0.72, n), i = y * CGX + x;
      c[i] = mix(1, 0.22 + 1.6 * v, str);
      d[i * 4] = 222; d[i * 4 + 1] = 230; d[i * 4 + 2] = 240; d[i * 4 + 3] = Math.round(255 * sstep(0.55, 1, v));
    }
    this.curtainCv.getContext('2d').putImageData(this.curtainImg, 0, 0);
  };

  P.updateClouds = function (p) {
    var N = this.N, s = this.seed, t = this.time, d = this.cloudImg.data, ox = this.cloudOff[0], oy = this.cloudOff[1];
    var cover = p.cloud, lo = mix(0.62, 0.36, cover);
    // 云影强度与阴雨压暗一起烘进同一缓冲（少一次全屏合成）：两层 source-over 预先合成
    var ca = (p.storm ? 0.36 + 0.2 * p.I : 0.22 + 0.16 * p.e) * (0.4 + 0.6 * p.cloud);
    var dk = this.tint ? (p.drizzle ? 0.08 : 0.1 + 0.16 * p.e) + (p.storm ? 0.06 + 0.12 * p.I : 0) : 0;
    for (var y = 0; y < KH; y++) for (var x = 0; x < KW; x++) {
      var n = N.fbm3(s + 61, x / KW * 2.6 + ox * 2.6, y / KH * 1.9 + oy * 1.9, t * 0.035, 3);
      var a = sstep(lo, lo + 0.22, n) * ca, i = (y * KW + x) * 4, ao = a + dk * (1 - a), q = ao > 0 ? 1 / ao : 0;
      d[i] = (18 * a + 28 * dk * (1 - a)) * q; d[i + 1] = (24 * a + 36 * dk * (1 - a)) * q; d[i + 2] = (34 * a + 52 * dk * (1 - a)) * q;
      d[i + 3] = Math.round(255 * ao);
    }
    this.cloudCv.getContext('2d').putImageData(this.cloudImg, 0, 0);
  };

  /** 雨丝：每条记落点 (lx, ly) 与离地高度 H，头部位置 = (lx - slant·H, ly - H) */
  P.spawnDrop = function (d, li, fresh) {
    var R = this.R, Ly = LAYERS[li], H0 = mix(Ly.H[0], Ly.H[1], R());
    var margin = Math.abs(this.slant) * H0 + 20, best = null;
    for (var k = 0; k < 4; k++) {
      var x = -margin + R() * (this.w + margin * 2), y = R() * (this.h + 30);
      var c = this.curtainAt(x - this.slant * H0 * 0.5, y - H0 * 0.5);
      best = [x, y, c];
      if (R() * 1.8 < c) break;
    }
    d.li = li; d.lx = best[0]; d.ly = best[1]; d.H0 = H0; d.H = fresh ? R() * H0 : H0;
    d.b = Math.min(3, (best[2] * 2.2) | 0); d.vj = 0.85 + R() * 0.3; d.live = true;
  };
  P.targetDrops = function (p) {
    if (!p.on) return 0;
    var f = p.drizzle ? 0.1 + 0.25 * p.I : Math.pow(p.e, 1.2) * (p.storm ? 1.1 : 1);
    return Math.min(DROP_CAP, Math.round(DROP_CAP * f * Math.min(1.6, this.w * this.h / (1400 * 900))));
  };

  /** 阴雨天的天色（给水洼映照用）：按小时粗插值，云量越高越灰；完整 24h 调色由 daylight 叠层负责 */
  function skyColor(hour, cloud) {
    var h = ((hour % 24) + 24) % 24, day = sstep(5, 7.5, h) * (1 - sstep(17.5, 20, h));
    var dusk = Math.max(0, 1 - Math.abs(h - 6.3) / 1.4) + Math.max(0, 1 - Math.abs(h - 18.6) / 1.4);
    var r = mix(34, 150, day), g = mix(42, 164, day), b = mix(64, 182, day);
    r = mix(r, 168, dusk * 0.4 * (1 - cloud * 0.5)); g = mix(g, 128, dusk * 0.3 * (1 - cloud * 0.5));
    var grey = (r + g + b) / 3; r = mix(r, grey, cloud * 0.35); g = mix(g, grey, cloud * 0.35); b = mix(b, grey + 6, cloud * 0.35);
    return [r | 0, g | 0, b | 0, day];
  }

  /**
   * 湿地与水洼缓冲（低分辨率，只在湿度 / 水洼 / 小时变化时重算）：
   *  湿斑：fB 分位数 < wetness 的格先湿（小湿度时是一块一块的深色斑），压暗量随湿度增加
   *  高光：detail 细纹噪波 > 0.7 的格在湿地上显出零星反光
   *  水洼：fA 分位数 < puddles·0.32 → 覆盖率与 puddles 成正比；边缘软过渡 + 深色水边
   */
  P.updateGroundBuffers = function (p) {
    var key = Math.round(p.wet * 60) + '|' + Math.round(p.puddles * 60) + '|' + Math.round(p.hour * 4) + '|' + Math.round(p.cloud * 10);
    if (key === this.groundKey || !this.fA) return;
    this.groundKey = key;
    var gw = this.fW, gh = this.fH, fA = this.fA, fB = this.fB, mask = this.mask, det = this.detail, pud = this.puddle;
    var gd = this.groundImg.data, pd = this.puddleImg.data, w = p.wet, sky = skyColor(p.hour, p.cloud);
    var thr = p.puddles * 0.16 * sstep(0.05, 0.45, w), soft = 0.02;
    for (var y = 0; y < gh; y++) for (var x = 0; x < gw; x++) {
      var i = y * gw + x, o = i * 4;
      gd[o + 3] = 0; pd[o + 3] = 0; pud[i] = 0;
      if (!this.wmask[i]) continue;
      var fe = this.feather[i];
      var wetHere = sstep(fB[i] - 0.18, fB[i] + 0.06, w * 1.12);
      if (!mask[i]) { gd[o] = 16; gd[o + 1] = 22; gd[o + 2] = 30; gd[o + 3] = Math.round(255 * wetHere * (0.1 + 0.26 * w)); continue; }
      // 高光：细纹噪波横向拉长采样（x 放慢 3 倍），得到横向一抹一抹的湿反光，而不是点状白斑
      var dv = det[(((y * LOW) >> 0) & 127) * 128 + (((x * LOW / 3) | 0) & 127)] / 255;
      var hl = sstep(0.8, 0.95, dv) * wetHere * w * fe;
      if (hl > 0.05) { gd[o] = 176; gd[o + 1] = 190; gd[o + 2] = 206; gd[o + 3] = Math.round(255 * hl * (0.05 + 0.06 * sky[3])); }
      else { gd[o] = 16; gd[o + 1] = 22; gd[o + 2] = 30; gd[o + 3] = Math.round(255 * wetHere * (0.1 + 0.26 * w)); }
      if (thr > 0) {
        var a = fA[i] + (1 - fe) * 0.5, core = 1 - sstep(thr - soft, thr, a), rim = (1 - sstep(thr, thr + soft * 1.4, a)) - core;
        if (core > 0.02) {
          // 水洼映天：天色压暗约一半（积水是深色镜面），中心略亮；上沿（3/4 视角远岸）多一道亮边
          var depth = clamp01((thr - a) / Math.max(0.02, thr)), up = i >= gw ? fA[i - gw] : a;
          var shade = 0.3 + 0.16 * depth + (up > thr ? 0.14 : 0);
          pd[o] = Math.min(255, sky[0] * shade + 8); pd[o + 1] = Math.min(255, sky[1] * shade + 10); pd[o + 2] = Math.min(255, sky[2] * shade + 16);
          pd[o + 3] = Math.round(255 * core * 0.78);
          if (core > 0.6) pud[i] = 1;
        } else if (rim > 0.02) { pd[o] = 14; pd[o + 1] = 18; pd[o + 2] = 24; pd[o + 3] = Math.round(255 * rim * 0.5); }
      }
    }
    this.groundCv.getContext('2d').putImageData(this.groundImg, 0, 0);
    this.puddleCv.getContext('2d').putImageData(this.puddleImg, 0, 0);
    // 合成湿地 + 水洼到一张低分辨率缓冲，draw 时只放大一次
    if (!this.wetCv || this.wetCv.width !== gw || this.wetCv.height !== gh) this.wetCv = mkCanvas(gw, gh);
    var wc = this.wetCv.getContext('2d');
    wc.clearRect(0, 0, gw, gh); wc.drawImage(this.groundCv, 0, 0); if (thr > 0) wc.drawImage(this.puddleCv, 0, 0);
    this.sky = sky;
  };

  // 层号用黄金分割序列：任意前 n 条的远/中/近比例都稳定，数量变化时不会整层消失
  P.layerOf = function (i) {
    var f = (i * 0.6180339887) % 1;
    return f < LAYERS[0].share ? 0 : f < LAYERS[0].share + LAYERS[1].share ? 1 : 2;
  };

  P.updateDrops = function (p, dt) {
    var n = this.targetDrops(p), drops = this.drops, vb = this.vBase;
    for (var i = 0; i < DROP_CAP; i++) {
      var d = drops[i];
      if (i >= n) { d.live = false; continue; }
      if (!d.live) { this.spawnDrop(d, this.layerOf(i), true); continue; }
      d.H -= vb * LAYERS[d.li].speed * d.vj * dt;
      if (d.H <= 0) { this.land(d, p); this.spawnDrop(d, d.li, false); }
    }
    this.nDrops = n;
  };

  /** 雨丝落地：按落点分区出溅点 / 涟漪；远层只偶尔出小涟漪 */
  P.land = function (d, p) {
    var R = this.R, z = this.zoneAt(d.lx, d.ly);
    if (!z) return;
    var near = d.li, e = p.e, pud = z === 1 && this.puddleAt(d.lx, d.ly);
    if (z === 2 || pud) {
      var pr = near === 0 ? 0.25 : near === 1 ? 0.55 : 0.85;
      if (p.drizzle) pr *= 0.6;
      if (R() < pr) this.ring(d.lx, d.ly, near, p);
      if (near === 2 && e > 0.45 && R() < 0.4) this.spark(d.lx, d.ly, 1 + (R() * 2 | 0), 0.8);
      return;
    }
    var sp = near === 0 ? 0.08 : near === 1 ? 0.35 : 0.7;
    if (p.drizzle) sp *= 0.25;
    if (R() < sp) this.spark(d.lx, d.ly, near === 2 ? 2 + (R() * 3 | 0) : 1 + (R() * 2 | 0), near === 2 ? 1 : 0.7);
  };
  P.spark = function (x, y, k, pow) {
    var R = this.R;
    for (var j = 0; j < k; j++) {
      var s = this.sparks.get(); if (!s) return;
      var a = -Math.PI / 2 + (R() - 0.5) * 2.4;
      var v = (40 + R() * 70) * pow;
      s.x = x; s.y = y; s.gy = y; s.vx = Math.cos(a) * v + this.vx * 0.05; s.vy = Math.sin(a) * v * 0.9;
      s.t = 0; s.life = 0.18 + R() * 0.16;
    }
  };
  P.ring = function (x, y, near, p) {
    var r = this.rings.get(); if (!r) return;
    var R = this.R;
    r.x = x; r.y = y; r.t = 0; r.life = 0.45 + R() * 0.35 + (p.drizzle ? 0.25 : 0);
    r.r1 = (near === 0 ? 3 : near === 1 ? 5 : 8) * (0.8 + R() * 0.5) * (p.drizzle ? 1.25 : 1);
    r.a = near === 0 ? 0.45 : near === 1 ? 0.7 : 0.9; r.two = near === 2 && R() < 0.5;
  };

  P.updateSplashes = function (p, dt) {
    var S = this.sparks, i;
    for (i = S.n - 1; i >= 0; i--) {
      var s = S.a[i]; s.t += dt;
      if (s.t >= s.life) { S.kill(i); continue; }
      s.vy += 520 * dt; s.x += s.vx * dt; s.y += s.vy * dt;
      if (s.y > s.gy + 2) S.kill(i);
    }
    var Rg = this.rings;
    for (i = Rg.n - 1; i >= 0; i--) { var r = Rg.a[i]; r.t += dt; if (r.t >= r.life) Rg.kill(i); }
  };

  /** 檐下滴水：每段檐口按长度与雨量出水滴，重力下落，落地出小溅点 */
  P.updateDrips = function (p, dt) {
    var R = this.R, D = this.drips, i;
    if (p.on && p.e > 0.02) {
      var rate = (p.drizzle ? 0.012 : 0.02 + 0.07 * p.e);
      for (i = 0; i < this.eaves.length; i++) {
        var ev = this.eaves[i];
        if (R() < rate * ev.len * dt * 6) {
          var q = D.get(); if (!q) break;
          q.x = mix(ev.x0, ev.x1, R()); q.y = ev.y; q.vy = 20 + R() * 30; q.gy = ev.gy + R() * 4;
        }
      }
    }
    for (i = D.n - 1; i >= 0; i--) {
      var o = D.a[i]; o.vy += 900 * dt; o.y += o.vy * dt; o.x += this.vx * 0.02 * dt;
      if (o.y >= o.gy) { this.spark(o.x, o.gy, 2, 0.55); if (this.puddleAt(o.x, o.gy) && R() < 0.6) this.ring(o.x, o.gy, 1, p); D.kill(i); }
    }
  };

  /**
   * 闪电：泊松式随机间隔（平均间隔随 state.lightning 从 ~16s 缩到 ~1.6s）。
   * 每次落雷 = 2–4 个亮度脉冲（主闪 + 余闪，每个衰减数帧）+ 一棵递归中点位移的分叉闪电树。
   * storm 低强度（< 0.3）只有远处云层里的暗光，不出闪电枝。
   */
  P.updateLightning = function (p, dt) {
    var R = this.R;
    var rate = p.storm ? p.lightning : p.kind === 'rain' ? p.lightning * 0.4 : p.kind === 'hail' ? p.lightning * 0.6 : 0;
    if (this.forceStrike) { this.forceStrike = false; this.strike(p, true); }
    else if (rate > 0.01) {
      this.nextStrike -= dt;
      if (this.nextStrike <= 0) {
        this.strike(p, false);
        var mean = mix(16, 1.6, rate);
        this.nextStrike = -Math.log(1 - R() * 0.98) * mean * 0.8 + mean * 0.2;
      }
    }
    // 脉冲叠加成本帧亮度
    var f = 0, ps = this.pulses;
    for (var i = ps.length - 1; i >= 0; i--) {
      var q = ps[i]; q.t += dt;
      if (q.t < 0) continue;
      var k = q.t < 0.02 ? q.t / 0.02 : Math.exp(-(q.t - 0.02) / q.decay);
      if (k < 0.01 && q.t > 0.05) { ps.splice(i, 1); continue; }
      f = Math.max(f, k * q.amp);
    }
    this.flash = f;
    if (this.bolt) { this.bolt.t += dt; if (this.bolt.t > this.bolt.life) this.bolt = null; }
  };

  P.strike = function (p, forced) {
    var R = this.R, far = !forced && (p.I < 0.3 || R() < 0.35);
    var amp = far ? 0.25 + 0.2 * R() : 0.65 + 0.35 * R();
    this.pulses.length = 0;
    var n = 2 + (R() * 3 | 0), t = 0;
    for (var i = 0; i < n; i++) {
      this.pulses.push({ t: -t, amp: amp * (i === 0 ? 1 : 0.45 + 0.5 * R()), decay: 0.05 + R() * 0.07 });
      t += 0.06 + R() * 0.14;
    }
    this.glowX = 0.1 + R() * 0.8;
    if (far && p.I < 0.3) { this.bolt = null; return; }        // 远雷：只有云里一闪
    var x = this.w * this.glowX, y1 = this.h * (far ? 0.22 + R() * 0.12 : 0.32 + R() * 0.2);
    var segs = [];
    this.boltPath(segs, x, -10, x + (R() - 0.5) * this.w * 0.12, y1, this.w * 0.07, 0, 7);
    this.bolt = { segs: segs, t: 0, life: t + 0.25, far: far, x: x };
  };

  /** 递归中点位移：每层把线段从中点按法向随机推开，偶尔分出一支更细更短的枝 */
  P.boltPath = function (out, x0, y0, x1, y1, disp, depth, maxD) {
    var R = this.R;
    if (maxD <= 0 || disp < 1.6) { out.push(x0, y0, x1, y1, depth); return; }
    var mx = (x0 + x1) / 2 + (R() - 0.5) * disp * 2, my = (y0 + y1) / 2 + (R() - 0.5) * disp * 0.6;
    this.boltPath(out, x0, y0, mx, my, disp * 0.55, depth, maxD - 1);
    this.boltPath(out, mx, my, x1, y1, disp * 0.55, depth, maxD - 1);
    if (depth < 2 && maxD > 2 && R() < 0.38 - depth * 0.12) {
      var dx = x1 - x0, dy = y1 - y0, ang = Math.atan2(dy, dx) + (R() < 0.5 ? -1 : 1) * (0.4 + R() * 0.6);
      var L = Math.sqrt(dx * dx + dy * dy) * (0.6 + R() * 0.5);
      this.boltPath(out, mx, my, mx + Math.cos(ang) * L, my + Math.sin(ang) * L, disp * 0.6, depth + 1, maxD - 2);
    }
  };
  /** 预览 / 测试用：立刻打一道近处闪电 */
  P.triggerLightning = function () { this.forceStrike = true; };

  // ───────────────────────── 冰雹（precipitation.type = hail，可与 storm 同时出现）─────────────────────────
  // 冰粒：比雨快约 1.3–1.6 倍、受风斜程度只有雨的 0.45；落地后弹跳 1–2 次再停留，停留时逐渐缩小（化掉）。
  // 地面积冰（ground.hail_cover）是累积量：fC（fbm2 秩变换）做斑块分布 + 哈希颗粒，只在 cover 变化时重烘。
  P.targetHail = function (p) {
    if (!p.hail) return 0;
    var f = 0.02 + 0.4 * Math.pow(p.hI, 1.6);           // 上限约 800 粒：再多就成白噪点墙，看不出是冰雹
    return Math.min(this.hfall.length, Math.round(this.hfall.length * f * Math.min(1.6, this.w * this.h / (1400 * 900))));
  };
  P.spawnHail = function (d, fresh, p) {
    var R = this.R, H0 = 220 + R() * 520, m = Math.abs(this.hSlant) * H0 + 20;
    d.x = -m + R() * (this.w + 2 * m); d.y = R() * (this.h + 20); d.H0 = H0; d.H = fresh ? R() * H0 : H0;
    d.v = 0.85 + R() * 0.3; d.rot = R() * 6.283;
    var big = p.hI > 0.7 ? Math.pow(R(), 2) * 2.6 * (p.hI - 0.7) / 0.3 : 0;   // 大冰雹：只在高档出现，少数特别大
    d.r = (0.8 + 0.8 * p.hI) * (0.75 + R() * 0.5) + big; d.live = true;
  };
  P.updateHail = function (p, dt) {
    var n = this.targetHail(p), F = this.hfall, vb = 1150 + 550 * p.hI, i;
    this.hSlant = (this.vx || 0) * 0.45 / vb; this.hailV = vb;
    for (i = 0; i < F.length; i++) {
      var d = F[i];
      if (i >= n) { d.live = false; continue; }
      if (!d.live) { this.spawnHail(d, true, p); continue; }
      d.H -= vb * d.v * dt;
      if (d.H <= 0) { this.hailLand(d, p); this.spawnHail(d, false, p); }
    }
    this.nHail = n;
    var S = this.stones;
    for (i = S.n - 1; i >= 0; i--) {
      var s = S.a[i]; s.t += dt;
      if (s.st === 0) {
        s.vz -= 900 * dt; s.z += s.vz * dt; s.x += s.vx * dt; s.y += s.vy * dt; s.rot += s.spin * dt;
        if (s.z <= 0) {
          s.z = 0;
          if (s.nb < 2 && Math.abs(s.vz) > 45) { s.vz = -s.vz * 0.36; s.vx *= 0.55; s.vy *= 0.55; s.spin *= 0.5; s.nb++; }
          else { s.st = 1; s.t = 0; }
        }
      } else if (s.t >= s.life) S.kill(i);
    }
    var Mk = this.marks;
    for (i = Mk.n - 1; i >= 0; i--) { Mk.a[i].t += dt; if (Mk.a[i].t >= Mk.a[i].life) Mk.kill(i); }
  };
  P.hailLand = function (d, p) {
    var R = this.R, z = this.zoneAt(d.x, d.y);
    if (!z) return;
    if (z === 2 || (z === 1 && this.puddleAt(d.x, d.y))) {        // 落水：涟漪 + 水花
      this.ring(d.x, d.y, d.r > 2 ? 2 : 1, p);
      if (R() < 0.5) this.spark(d.x, d.y, 2 + (R() * 2 | 0), 0.9);
      return;
    }
    if (p.hI > 0.7 && d.r > 2.2 && R() < 0.55) {                 // 高档：白色击打痕 + 溅冰碎屑
      var mk = this.marks.get();
      if (mk) { mk.x = d.x; mk.y = d.y; mk.r = d.r * (1.6 + R()); mk.t = 0; mk.life = 0.9 + R() * 0.8; mk.rot = R() * 6.283; }
      this.spark(d.x, d.y, 3 + (R() * 3 | 0), 1.2);
    }
    if (R() < 0.18 + 0.12 * (1 - p.hI)) {
      var s = this.stones.get(); if (!s) return;
      var roof = z === 3;
      s.x = d.x; s.y = d.y; s.z = 0; s.r = d.r; s.rot = d.rot; s.spin = (R() - 0.5) * 18;
      s.vz = (70 + R() * 110) * (0.7 + 0.12 * d.r) * (roof ? 0.6 : 1);
      s.vx = this.hSlant * this.hailV * 0.08 + (R() - 0.5) * 44; s.vy = (R() - 0.5) * 14;
      s.st = 0; s.nb = 0; s.t = 0; s.life = (0.8 + R() * 1.8) * (roof ? 1.7 : 1);
    }
  };

  /**
   * 地面积冰缓冲：fC 分位数 < hail_cover 的格积冰（斑块状，不均匀），格内再用哈希做颗粒感；
   * 屋顶区（zone 3）积得更快（同样 cover 下更白）。只在 cover 变化 0.02 以上时重烘。
   */
  P.updateHailGround = function (p) {
    if (!this.fC) return;
    var c = p.hailCover, key = Math.round(c * 50);
    if (key === this.hailKey) return;
    this.hailKey = key;
    var gw = this.fW, gh = this.fH, n = gw * gh, H = this.N.hash32, s = this.seed;
    if (!this.hailCv || this.hailCv.width !== gw || this.hailCv.height !== gh) { this.hailCv = mkCanvas(gw, gh); this.hailImg = this.hailCv.getContext('2d').createImageData(gw, gh); }
    var d = this.hailImg.data, fC = this.fC, wm = this.wmask, zn = this.zone;
    for (var i = 0; i < n; i++) {
      var o = i * 4; d[o + 3] = 0;
      if (c < 0.005 || !wm[i]) continue;
      // 冰粒是散落的颗粒，不是积雪：斑块内颗粒密，斑块外只有零星几粒；屋顶略多（滚到檐沟里积着）
      var cc = (zn[i] === 3 ? Math.min(1, c * 1.2) : c) * (0.5 + 0.5 * this.feather[i]);
      var patch = 1 - sstep(cc * 0.7 - 0.1, cc * 0.7 + 0.06, fC[i]);
      var g = (H(s ^ Math.imul(i, 2654435761)) & 1023) / 1023;
      var dens = patch * patch * (0.05 + 0.3 * cc) + 0.008 * cc;   // 斑块内集中、斑块外几乎没有
      if (g < 1 - dens) continue;
      var sh = (H(s + 9 ^ Math.imul(i, 40503)) & 255) / 255;
      d[o] = 214 + (sh * 34 | 0); d[o + 1] = 228 + (sh * 22 | 0); d[o + 2] = 236 + (sh * 18 | 0); d[o + 3] = Math.round(255 * (0.55 + 0.35 * sh));
    }
    this.hailCv.getContext('2d').putImageData(this.hailImg, 0, 0);
  };

  /** 冰雹绘制：下落冰粒（短亮痕 + 亮头）、地面弹跳 / 停留冰粒（影子 + 白偏青粒，停留时逐渐缩小）、白色击打痕 */
  P.drawHail = function (ctx, p) {
    var F = this.hfall, n = this.nHail, sl = this.hSlant, i, b;
    var inv = 1 / Math.sqrt(1 + sl * sl), ux = sl * inv, uy = inv;
    ctx.lineCap = 'round';
    for (b = 0; b < 3; b++) {                       // 按粒径分三批描边
      ctx.beginPath(); var any = false;
      for (i = 0; i < n; i++) {
        var d = F[i]; if (!d.live) continue;
        var bk = d.r < 1.4 ? 0 : d.r < 2.4 ? 1 : 2; if (bk !== b) continue;
        var hx = d.x - sl * d.H, hy = d.y - d.H, L = 5 + d.r * 4;
        if (hy < -L || hy > this.h + 4) continue;
        ctx.moveTo(hx - ux * L, hy - uy * L); ctx.lineTo(hx, hy); any = true;
      }
      if (!any) continue;
      ctx.lineWidth = b === 0 ? 1.3 : b === 1 ? 2.2 : 3.4;
      ctx.strokeStyle = 'rgba(214,232,242,' + (0.38 + 0.12 * b) + ')'; ctx.stroke();
      ctx.lineWidth *= 1.15; ctx.strokeStyle = 'rgba(246,252,255,0.9)';
      ctx.beginPath();
      for (i = 0; i < n; i++) {
        d = F[i]; if (!d.live) continue;
        bk = d.r < 1.4 ? 0 : d.r < 2.4 ? 1 : 2; if (bk !== b) continue;
        hx = d.x - sl * d.H; hy = d.y - d.H; ctx.moveTo(hx - ux * 0.6, hy - uy * 0.6); ctx.lineTo(hx, hy);
      }
      ctx.stroke();
    }
    var Mk = this.marks;
    if (Mk.n) {                                     // 击打痕：放射短线 + 淡白圆斑，逐渐淡出
      ctx.lineWidth = 1;
      for (i = 0; i < Mk.n; i++) {
        var m = Mk.a[i], k = 1 - m.t / m.life;
        ctx.fillStyle = 'rgba(240,246,250,' + (0.35 * k).toFixed(3) + ')';
        ctx.beginPath(); ctx.ellipse(m.x, m.y, m.r, m.r * 0.5, 0, 0, 6.283); ctx.fill();
        ctx.strokeStyle = 'rgba(250,252,255,' + (0.7 * k).toFixed(3) + ')'; ctx.beginPath();
        for (var j = 0; j < 5; j++) { var an = m.rot + j * 1.2566, r1 = m.r * 0.5, r2 = m.r * 1.5; ctx.moveTo(m.x + Math.cos(an) * r1, m.y + Math.sin(an) * r1 * 0.5); ctx.lineTo(m.x + Math.cos(an) * r2, m.y + Math.sin(an) * r2 * 0.5); }
        ctx.stroke();
      }
    }
    var S = this.stones;
    if (!S.n) return;
    ctx.fillStyle = 'rgba(20,28,36,0.28)'; ctx.beginPath();   // 影子（贴地，不随弹跳高度）
    for (i = 0; i < S.n; i++) { var s = S.a[i], rr = this.stoneR(s); ctx.rect(s.x - rr * 0.4, s.y + 0.3, rr * 2 + 0.8, rr * 0.9 + 0.4); }   // 影子用矩形：几千个粒子时比 ellipse 便宜得多
    ctx.fill();
    ctx.fillStyle = 'rgba(226,238,246,0.95)'; ctx.beginPath();
    for (i = 0; i < S.n; i++) { s = S.a[i]; rr = this.stoneR(s); var sy = s.y - s.z - rr * 0.4;
      if (rr < 1.6) { ctx.rect(s.x - rr, sy - rr * 0.8, rr * 2, rr * 1.6); continue; }
      ctx.moveTo(s.x + rr, sy); ctx.ellipse(s.x, sy, rr, rr * 0.82, s.rot, 0, 6.283); }   // 大粒略扁、带旋转：不规则感；小粒直接方块
    ctx.fill();
    ctx.fillStyle = 'rgba(255,255,255,0.95)'; ctx.beginPath();
    for (i = 0; i < S.n; i++) { s = S.a[i]; rr = this.stoneR(s); if (rr < 1.2) continue; ctx.rect(s.x - rr * 0.45, s.y - s.z - rr * 0.95, rr * 0.5, rr * 0.4); }
    ctx.fill();
  };
  P.stoneR = function (s) { return s.st === 1 ? s.r * (1 - 0.6 * s.t / s.life) : s.r; };

  // ───────────────────────── 绘制 ─────────────────────────
  P.draw = function (ctx, pass) {
    var p = this.p;
    if (!p) return;
    // 雨停后：地面湿度 / 积冰是累积量，ground pass 照画；正在弹跳的冰粒画完为止
    if (!p.on && !(pass === 'ground' && (p.wet > 0.01 || p.hailCover > 0.005)) && !(pass === 'precip' && this.stones.n)) return;
    ctx.save();
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    if (pass === 'ground') this.drawGround(ctx, p);
    else if (pass === 'reflect') this.drawReflect(ctx, p);
    else if (pass === 'precip') {
      if (this.dpr > 1.25) {
        // 高 dpr：雨丝成千条描边是主要开销，先在 CSS 分辨率的离屏缓冲里画，再一次放大合成（细丝放大后略柔，肉眼可接受）
        var pw = Math.ceil(this.w), ph = Math.ceil(this.h);
        if (!this.precipCv || this.precipCv.width !== pw || this.precipCv.height !== ph) this.precipCv = mkCanvas(pw, ph);
        var pc = this.precipCv.getContext('2d');
        pc.setTransform(1, 0, 0, 1, 0, 0); pc.clearRect(0, 0, pw, ph);
        this.drawPrecip(pc, p);
        ctx.imageSmoothingEnabled = true; ctx.drawImage(this.precipCv, 0, 0, pw, ph);
      } else this.drawPrecip(ctx, p);
    }
    else if (pass === 'fog') this.drawFog(ctx, p);
    else if (pass === 'flash') this.drawFlash(ctx, p);
    ctx.restore();
  };

  /** ground：低分辨率湿斑 / 高光缓冲平滑放大，再盖水洼缓冲 */
  P.drawGround = function (ctx, p) {
    var w = this.w, h = this.h;
    ctx.imageSmoothingEnabled = true;
    // 阴雨压暗（tint）已烘进云影缓冲：一次放大绘制 = 压暗 + 随风平移的 fbm3 云影；都在雨丝下面
    if (p.on) ctx.drawImage(this.cloudCv, -w * 0.05, -h * 0.05, w * 1.1, h * 1.1);
    // 湿斑与水洼已合成到 wetCv：一次放大绘制
    if (this.wetCv && p.wet > 0.01) ctx.drawImage(this.wetCv, 0, 0, this.fW * LOW, this.fH * LOW);
    // 地面积冰（ground.hail_cover）：噪波斑块 + 颗粒，最近邻放大保留颗粒感
    if (this.hailCv && p.hailCover > 0.005) { ctx.imageSmoothingEnabled = false; ctx.drawImage(this.hailCv, 0, 0, this.fW * LOW, this.fH * LOW); ctx.imageSmoothingEnabled = true; }
  };

  P.waterRects = function () { return (this.scene && this.scene.water) || []; };

  /** reflect：水面雨麻点（碎纹贴图逐帧跳位）、阴天压灰水面、闪电时水面与水洼一起亮 */
  P.drawReflect = function (ctx, p) {
    var W = this.waterRects(), i, r;
    if (W.length) {
      ctx.save();
      ctx.beginPath();
      for (i = 0; i < W.length; i++) { r = W[i]; ctx.rect(r[0], r[1], r[2], r[3]); }
      ctx.clip();
      ctx.fillStyle = 'rgba(40,52,66,' + (0.06 + 0.14 * p.cloud * p.e).toFixed(3) + ')';
      ctx.fill();
      if (!this.rufflePat) this.rufflePat = ctx.createPattern(this.ruffle, 'repeat');
      if (this.frame % 4 === 0 || !this.ruffleOff) this.ruffleOff = [this.R() * 128, this.R() * 128];
      var ra = p.drizzle ? 0.08 : 0.1 + 0.22 * p.e;
      ctx.globalAlpha = ra; ctx.fillStyle = this.rufflePat;
      ctx.translate(-this.ruffleOff[0], -this.ruffleOff[1]);
      ctx.fillRect(this.ruffleOff[0], this.ruffleOff[1], this.w, this.h);
      ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
      if (this.flash > 0.02) {
        // 闪电倒影：整片水面提亮，闪电所在列有一道竖向亮带
        ctx.globalAlpha = 1;
        if (this.bolt) {
          var bx = this.bolt.x, g = ctx.createLinearGradient(bx - 60, 0, bx + 60, 0);
          g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(0.5, 'rgba(250,250,255,' + (this.flash * 0.7).toFixed(3) + ')'); g.addColorStop(1, 'rgba(255,255,255,0)');
          ctx.fillStyle = g; ctx.fillRect(bx - 60, 0, 120, this.h);
        }
      }
      ctx.restore();
    }
    if (this.flash > 0.02 && p.puddles > 0.01 && this.puddleCv) {
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      ctx.globalAlpha = Math.min(1, this.flash * 0.16);
      ctx.imageSmoothingEnabled = true;
      ctx.drawImage(this.puddleCv, 0, 0, this.fW * LOW, this.fH * LOW);
      ctx.restore();
    }
  };

  /**
   * precip：雨丝按「层 × 雨帘亮度档」分 12 批，每批一条 path 一次 stroke；
   * 雨丝沿速度方向 (vx, vBase) 画，长度随强度与层变化；然后涟漪（扁椭圆）、溅点、檐滴。
   */
  P.drawPrecip = function (ctx, p) {
    var drops = this.drops, n = this.nDrops, sl = this.slant;
    var inv = 1 / Math.sqrt(1 + sl * sl), ux = sl * inv, uy = inv;
    var baseLen = p.drizzle ? 6 + 6 * p.I : p.sleet ? 9 + 10 * p.I : 11 + 34 * p.e;
    var baseA = p.drizzle ? 0.34 + 0.3 * p.I : 0.3 + 0.38 * p.e;
    var col = p.sleet ? '214,222,232' : '196,210,228';
    ctx.lineCap = 'round';
    for (var li = 0; li < 3; li++) {
      var Ly = LAYERS[li], len = baseLen * Ly.len;
      ctx.lineWidth = Ly.width * (p.drizzle ? 0.8 : 1) * (p.e > 0.7 && li === 2 ? 1.2 : 1);
      for (var b = 0; b < 4; b++) {
        ctx.beginPath();
        var any = false;
        for (var i = 0; i < n; i++) {
          var d = drops[i];
          if (!d.live || d.li !== li || d.b !== b) continue;
          var hx = d.lx - sl * d.H, hy = d.ly - d.H;
          if (hy < -len || hy > this.h + 4) continue;
          var L = Math.min(len, d.H0 - d.H + 1, len);
          ctx.moveTo(hx - ux * L, hy - uy * L); ctx.lineTo(hx, hy); any = true;
        }
        if (!any) continue;
        var a = baseA * Ly.alpha * (0.55 + b * 0.22);
        ctx.strokeStyle = 'rgba(' + col + ',' + Math.min(1, a).toFixed(3) + ')';
        ctx.stroke();
      }
    }
    this.drawRings(ctx, p);
    this.drawSparks(ctx, p);
    var D = this.drips;
    if (D.n) {
      ctx.beginPath();
      for (var k = 0; k < D.n; k++) { var q = D.a[k], ql = Math.min(9, 2 + q.vy * 0.012); ctx.moveTo(q.x, q.y - ql); ctx.lineTo(q.x, q.y); }
      ctx.lineWidth = 1.4; ctx.strokeStyle = 'rgba(210,222,238,0.75)'; ctx.stroke();
    }
    if (p.hail || this.stones.n || this.marks.n) this.drawHail(ctx, p);
  };

  /** 涟漪：3/4 视角压扁的椭圆圈，半径随时间外扩、透明度衰减；近层一半出双圈 */
  P.drawRings = function (ctx, p) {
    var Rg = this.rings;
    if (!Rg.n) return;
    ctx.lineWidth = 1;
    for (var b = 0; b < 4; b++) {
      ctx.beginPath();
      var any = false;
      for (var i = 0; i < Rg.n; i++) {
        var r = Rg.a[i], k = r.t / r.life, fade = (1 - k) * r.a;
        if (Math.min(3, (fade * 4) | 0) !== b) continue;
        var rad = 0.6 + r.r1 * Math.sqrt(k);
        ctx.moveTo(r.x + rad, r.y); ctx.ellipse(r.x, r.y, rad, rad * 0.42, 0, 0, Math.PI * 2);
        if (r.two && k > 0.25) { var r2 = r.r1 * Math.sqrt(k - 0.25) * 0.8; ctx.moveTo(r.x + r2, r.y); ctx.ellipse(r.x, r.y, r2, r2 * 0.42, 0, 0, Math.PI * 2); }
        any = true;
      }
      if (any) { ctx.strokeStyle = 'rgba(222,232,244,' + (0.18 + b * 0.2).toFixed(2) + ')'; ctx.stroke(); }
    }
  };

  P.drawSparks = function (ctx, p) {
    var S = this.sparks;
    if (!S.n) return;
    ctx.fillStyle = 'rgba(226,234,246,0.85)';
    ctx.beginPath();
    for (var i = 0; i < S.n; i++) {
      var s = S.a[i], z = s.t / s.life < 0.5 ? 1.6 : 1.1;
      ctx.rect(s.x - z / 2, s.y - z / 2, z, z);
    }
    ctx.fill();
  };

  /**
   * fog：① 阴雨压暗（tint，可关）② 云影：低分辨率 fbm3 缓冲放大，随风平移
   *      ③ 雨帘：curtain 密度格放大成淡白纱，跟雨丝密度同一张噪波 ④ 暴雨水雾（e > 0.7）：
   *      远处（屏幕上方，3/4 视角里更远）渐变发白 + 两层平铺雾团 pattern 反向漂移。
   */
  P.drawFog = function (ctx, p) {
    var w = this.w, h = this.h, curtain = !p.drizzle && p.e > 0.25;
    var m = sstep(0.62, 1, p.e) * 0.75 + (1 - p.vis) * 0.2 * sstep(0.5, 0.8, p.e);
    if (!curtain && m <= 0.01) return;
    // 整个雾层先画进 1/FOG_DS 分辨率的缓冲（雾本来就柔），最后一次放大合成
    var F = FOG_DS, fw = Math.ceil(w / F), fh = Math.ceil(h / F), out = ctx;
    if (!this.fogCv || this.fogCv.width !== fw || this.fogCv.height !== fh) { this.fogCv = mkCanvas(fw, fh); this.mistPat = null; }
    ctx = this.fogCv.getContext('2d');
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.clearRect(0, 0, fw, fh);
    ctx.setTransform(1 / F, 0, 0, 1 / F, 0, 0);
    ctx.imageSmoothingEnabled = true;
    if (curtain) {
      ctx.globalAlpha = 0.05 + 0.13 * sstep(0.25, 1, p.e);
      ctx.drawImage(this.curtainCv, 0, 0, w, h);
    }
    ctx.globalAlpha = 1;
    if (m > 0.01) {
      m = Math.min(1, m);
      var g = ctx.createLinearGradient(0, 0, 0, h);
      g.addColorStop(0, 'rgba(196,204,216,' + (0.42 * m).toFixed(3) + ')');
      g.addColorStop(0.45, 'rgba(190,198,210,' + (0.16 * m).toFixed(3) + ')');
      g.addColorStop(1, 'rgba(186,194,206,' + (0.04 * m).toFixed(3) + ')');
      ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
      if (!this.mistPat) this.mistPat = ctx.createPattern(this.mistTile, 'repeat');
      var t = this.time, sx = this.vx * 0.12;
      for (var k = 0; k < 2; k++) {
        var sc = k ? 3.2 : 2, ox = ((t * (k ? 18 : 30) + t * sx * (k ? 0.6 : 1)) % (256 * sc)), oy = (t * (k ? -4 : 6)) % (256 * sc);
        ctx.save();
        ctx.globalAlpha = m * (k ? 0.14 : 0.18);
        ctx.translate(ox, oy); ctx.scale(sc, sc * 0.6);
        ctx.fillStyle = this.mistPat;
        ctx.fillRect(-ox / sc - 256, -oy / (sc * 0.6) - 256, w / sc + 512, h / (sc * 0.6) + 512);
        ctx.restore();
      }
    }
    out.imageSmoothingEnabled = true;
    out.drawImage(this.fogCv, 0, 0, fw * F, fh * F);
  };

  /** flash：全屏闪白（脉冲衰减）+ 云层里的光晕 + 分叉闪电枝（外层宽淡辉光 + 内层亮芯，分支更细更淡） */
  P.drawFlash = function (ctx, p) {
    var f = this.flash, w = this.w, h = this.h;
    if (f < 0.01 && !this.bolt) return;
    ctx.globalCompositeOperation = 'lighter';
    if (f > 0.01) {
      var gx = w * this.glowX, rg = ctx.createRadialGradient(gx, -h * 0.05, 0, gx, -h * 0.05, Math.max(w, h) * 0.8);
      rg.addColorStop(0, 'rgba(210,220,255,' + (0.42 * f).toFixed(3) + ')');
      rg.addColorStop(1, 'rgba(160,175,220,0)');
      ctx.fillStyle = rg; ctx.fillRect(0, 0, w, h);
      ctx.fillStyle = 'rgba(200,210,240,' + (0.1 * f).toFixed(3) + ')';
      ctx.fillRect(0, 0, w, h);
    }
    var B = this.bolt;
    if (B && f > 0.04) {
      var s = B.segs, vis = Math.min(1, f * 1.6) * (B.far ? 0.6 : 1);
      ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      for (var depth = 0; depth < 3; depth++) {
        ctx.beginPath();
        for (var i = 0; i < s.length; i += 5) if (s[i + 4] === depth) { ctx.moveTo(s[i], s[i + 1]); ctx.lineTo(s[i + 2], s[i + 3]); }
        var wMul = (B.far ? 0.6 : 1) * (depth === 0 ? 1 : depth === 1 ? 0.55 : 0.35), aMul = depth === 0 ? 1 : depth === 1 ? 0.6 : 0.4;
        ctx.strokeStyle = 'rgba(150,170,255,' + (0.18 * vis * aMul).toFixed(3) + ')'; ctx.lineWidth = 9 * wMul; ctx.stroke();
        ctx.strokeStyle = 'rgba(200,215,255,' + (0.45 * vis * aMul).toFixed(3) + ')'; ctx.lineWidth = 3.2 * wMul; ctx.stroke();
        ctx.strokeStyle = 'rgba(255,255,255,' + (0.95 * vis * aMul).toFixed(3) + ')'; ctx.lineWidth = Math.max(1, 2.2 * wMul); ctx.stroke();
      }
    }
    ctx.globalCompositeOperation = 'source-over';
  };

  P.dispose = function () {
    this.drops.length = 0; this.sparks.clear(); this.rings.clear(); this.drips.clear();
    this.pulses.length = 0; this.bolt = null; this.scene = null;
    this.fA = this.fB = this.mask = this.zone = this.puddle = null;
    this.groundCv = this.puddleCv = this.cloudCv = this.curtainCv = null; this.p = { on: false };
  };
  /** 调试 / 预览用的统计 */
  P.stats = function () { return { drops: this.nDrops, sparks: this.sparks.n, rings: this.rings.n, drips: this.drips.n, flash: +this.flash.toFixed(3), bolt: !!this.bolt }; };

  var API = { kinds: Object.keys(KINDS), passes: ['ground', 'reflect', 'precip', 'fog', 'flash'],
    create: function (opts) { return new Layer(opts); } };
  root.WeatherFX_rain = API;
})(this);
