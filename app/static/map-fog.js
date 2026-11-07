// 玩家地图的「灰蓝卷云墙」迷雾：在浏览器里按屏幕分辨率画在 canvas 上。
//
// 只是装饰。安全由服务端负责：底图 PNG 里揭示圈外的像素已经是一种与地形无关的纯色。
// 这里的透明区严格落在服务端揭示区之内：用与 app/fog_art.py 相同的公式（大圆距离 +
// 同一份 edge 轮廓）算出 ratio。
//   ratio <= INNER_CLEAR 一律完全透明（可见区里绝不铺东西）
//   ratio >= OPAQUE_AT   一律完全不透明（硬约束，不看云画到哪儿）
//   中间只有一道会向内收的雾边：扰动只作用在 ratio 上，比例关系单调。
//
// 画法（只参考《天国：拯救》系列地图上那圈手绘云墙的**风格**，不裁图、不用它的素材）：
// - 云是「沿探索边界的极坐标云岸」，不是散在平面的气泡：格子按 (方位角弧长, 离边界的
//   距离) 分，所以一圈云自然成排、成片、大体成圆，而每片云的形状由世界坐标的种子
//   与域扭曲决定；
// - 三层由远及近叠：最大最暗的灰褐/炭灰云层 → 中尺度云岸 → 贴地图的细小浅灰蓝扇贝云缘。
//   后者叠在前两者上并给它们投淡影，于是边界处是一圈细扇贝云缘，往后才是云岸与暗云；
// - 每团云由 3~5 个高斯球融合成一道云岸（metaball），径向压扁，只在整道云的外轮廓描
//   一道细墨线（越靠地图越实，越深越淡），不会把每颗小球都描成圆圈；
// - 云体内部是起伏的暗面/亮面，加一层很淡的卷云细弧（短、弯、断续）；不是噪点，也没
//   满铺的斜线；
// - 越往外天空越暗（深灰蓝，不是平黑）；很低频的场让每个地区的冷暖、云量略有差别；
//   最上面一层极轻的纸纹。没有动画。
(function () {
  'use strict';
  const OPAQUE_AT = 0.985;   // ratio 达到这里就必定完全不透明
  const CLEAR_AT = 0.80;     // 兼容旧接口：低于这里一定透明
  const INNER_CLEAR = 0.93;  // 这里以内完全不画雾（与 fog_art.CLEAR_FRACTION 对齐）
  const EDGE_AT = 0.962;     // 雾边的中位位置（扰动后只向内收）
  const EARTH_R = 6371.0088;
  const D2R = Math.PI / 180;
  const KM_PER_DEG = 111.19492664455873;
  const T = 0.5;             // 云团场阈值
  const FAR_MAX = 4.4;       // 云的绘制上限：ratio 超过这里就不必有云（也避免了 Infinity 参与运算）

  // ---------------------------------------------------------------- noise
  function hash2(ix, iy, seed) {
    let h = Math.imul(ix, 374761393) ^ Math.imul(iy, 668265263) ^ Math.imul(seed, 1442695041);
    h = Math.imul(h ^ (h >>> 13), 1274126177);
    h ^= h >>> 16;
    return (h >>> 8) / 16777216;
  }
  function vnoise(x, y, seed) {
    const xi = Math.floor(x), yi = Math.floor(y);
    let fx = x - xi, fy = y - yi;
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy);
    const a = hash2(xi, yi, seed), b = hash2(xi + 1, yi, seed);
    const c = hash2(xi, yi + 1, seed), d = hash2(xi + 1, yi + 1, seed);
    return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy;
  }
  function fbm(x, y, seed, oct) {
    let s = 0, amp = 0.5, norm = 0;
    for (let i = 0; i < oct; i++) {
      s += amp * vnoise(x, y, seed + i * 131);
      norm += amp; amp *= 0.5;
      const nx = x * 1.6 - y * 1.2, ny = x * 1.2 + y * 1.6;
      x = nx + 17.3; y = ny - 9.1;
    }
    return s / norm;
  }
  const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
  const lerp = (a, b, t) => a + (b - a) * t;

  // ------------------------------------------------------------- geometry
  // 与 fog_art.reveal_ratio 同一公式：大圆距离 / (半径 × 该方位的 edge 比例)。
  function prepare(reveal) {
    return (reveal || []).map((c) => {
      const clat = c.lat * D2R;
      const reach = c.radius_km / EARTH_R / D2R * 1.7;
      return { lon: c.lon, lat: c.lat, r: c.radius_km, edge: c.edge,
               rdeg: c.radius_km / KM_PER_DEG,
               sinC: Math.sin(clat), cosC: Math.cos(clat), cosK: Math.max(0.02, Math.cos(clat)),
               dlat: reach, dlon: reach / Math.max(0.05, Math.cos(clat)) };
    });
  }
  // 最近圆的信息（ratio、方位角、半径角尺度），复用同一个对象以免逐像素分配。
  const RI = { r: Infinity, bearing: 0, rdeg: 1, ci: -1 };
  function ratioInfo(lon, lat, circles) {
    let best = Infinity, bearing = 0, rdeg = 1, ci = -1;
    const sinP = Math.sin(lat * D2R), cosP = Math.cos(lat * D2R);
    for (let i = 0; i < circles.length; i++) {
      const c = circles[i];
      if (Math.abs(lat - c.lat) > c.dlat || Math.abs(lon - c.lon) > c.dlon) continue;
      let cosD = c.sinC * sinP + c.cosC * cosP * Math.cos((lon - c.lon) * D2R);
      cosD = Math.max(-1, Math.min(1, cosD));
      const dist = Math.acos(cosD) * EARTH_R;
      const b = Math.atan2(lat - c.lat, (lon - c.lon) * c.cosK);
      const n = c.edge.length;
      const t = (((b % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI)) / (2 * Math.PI) * n;
      const i0 = Math.floor(t) % n, i1 = (i0 + 1) % n, f = t - Math.floor(t);
      const reff = c.r * (c.edge[i0] * (1 - f) + c.edge[i1] * f);
      const r = dist / Math.max(1e-6, reff);
      if (r < best) { best = r; bearing = b; rdeg = c.rdeg; ci = i; }
    }
    RI.r = best; RI.bearing = bearing; RI.rdeg = rdeg; RI.ci = ci;
    return RI;
  }
  function ratioAt(lon, lat, circles) { return ratioInfo(lon, lat, circles).r; }

  // ---------------------------------------------------------------- clouds
  // 一层云岸（由远到近）。
  //   cell：切向格宽（cloudDeg 倍率）；格子按「方位角弧长」分，所以云沿边界成排
  //   min ：格宽的屏幕下限（CSS 像素），小地图上云不会细成噪点
  //   ball：球半径 / 格宽，接近 1 时相邻格子的云相连成一道云岸
  //   pres：该层格子里有云的比例（留缺口，云缘局部凹进）
  //   band：[in0,in1,out0,out1]，按 d = ratio-1 的连续权重（越靠外越深）
  //   wob ：方位角调制幅度（ratio 单位）。让这层「离边界多远」沿圆周高低错落，
  //         否则每层都沿 ratio 等值线成排，一整圈就是一道轨道。
  //   ink ：外轮廓墨线的深浅
  const LAYERS = [
    { cell: 0.260, min: 34, ball: 1.00, pres: 0.90, balls: 4, seed: 6300, ink: 0.10, wob: 0.85,
      band: [0.28, 0.72, 1.70, 3.30] },    // 最远：最大、最暗的灰褐/炭灰云层
    { cell: 0.155, min: 18, ball: 0.95, pres: 0.78, balls: 3, seed: 5200, ink: 0.30, wob: 0.52,
      band: [-0.02, 0.16, 0.32, 1.15] },   // 中尺度云岸（与上下两层大幅重叠）
    { cell: 0.072, min: 10, ball: 0.86, pres: 0.68, balls: 2, seed: 4100, ink: 0.55, wob: 0.20,
      band: [-0.030, 0.004, 0.022, 0.095] }, // 贴地图：细小扇贝云缘，时隐时现
  ];

  // 方位角低频调制：几个谐波相加，本身以 2π 为周期，所以绕一圈没有接缝。
  function angWobble(b, seed) {
    const p = (seed % 997) / 997 * 6.283185307;
    return 0.62 * Math.sin(2 * b + p) + 0.30 * Math.sin(3 * b + p * 1.7 + 1.1)
      + 0.16 * Math.sin(5 * b + p * 2.3 + 2.2);
  }

  // 在「方位角弧长 s × 离边距离 d」平面里求一层的云场。
  function polarField(lon, lat, info, L, w, cellA) {
    const rDeg = info.rdeg;
    if (!(rDeg > 0) || !(cellA > 0)) return 0;
    const per = 2 * Math.PI * rDeg;                   // 一圈的弧长（度）
    const na = Math.max(6, Math.round(per / cellA));
    const sa = per / na;                              // 实际切向格宽（度）
    const cellD = sa / rDeg;                          // 径向格高（ratio 单位）
    // 世界坐标上的域扭曲：连续、无接缝，让云岸起伏、不排队
    const fq = 1.45 / cellA;
    const n1 = fbm(lon * fq + 3.1, lat * fq - 1.7, L.seed + 7, 2) - 0.5;
    const n2 = fbm(lon * fq - 5.2, lat * fq + 4.3, L.seed + 9, 2) - 0.5;
    const s0 = (info.bearing + Math.PI) * rDeg + n1 * 0.60 * sa;
    // 方位角调制：把这一层摞离边界的高度按方位高高低低地错开，打散同心环
    const dOff = L.wob * angWobble(info.bearing, L.seed);
    const d0 = (info.r - 1) + dOff + n2 * 0.60 * cellD;
    const ia0 = Math.floor(s0 / sa), id0 = Math.floor(d0 / cellD);
    const base = L.seed + info.ci * 131;
    const reachD = 1.7 * cellD, reachA = 1.35 * sa;
    let sum = 0;
    for (let jd = id0 - 1; jd <= id0 + 1; jd++) {
      const dd0 = d0 - (jd + 0.5) * cellD;
      if (Math.abs(dd0) > reachD) continue;
      // 每排云错位，不然极化格子会排出一圈圈同心弧
      const rowShift = (hash2(jd, 977, base) - 0.5) * sa;
      for (let ja = ia0 - 1; ja <= ia0 + 1; ja++) {
        const iw = ((ja % na) + na) % na;
        const wgt = smooth(0, 1, (L.pres - hash2(iw, jd, base)) * 5);
        if (wgt <= 0) continue;
        const pa = (ja + 0.5 + (hash2(iw, jd, base + 2) - 0.5) * 0.55) * sa;
        let ds0 = s0 - rowShift - pa;
        ds0 -= per * Math.round(ds0 / per);
        if (Math.abs(ds0) > reachA + sa) continue;
        const pd = dd0 + (hash2(iw, jd, base + 3) - 0.5) * 0.55 * cellD;
        const nb = 2 + Math.floor(hash2(iw, jd, base + 1) * (L.balls - 1));
        const bw = (0.20 + 0.30 * hash2(iw, jd, base + 4)) * sa;   // 云岸半长（小于格宽，靠球半径叠成一道墙）
        const size = 0.85 + 0.42 * hash2(iw, jd, base + 5);
        for (let k = 0; k < nb; k++) {
          const u = nb === 1 ? 0 : (k / (nb - 1)) * 2 - 1;
          const qa = u * bw + (hash2(iw, jd, base + 20 + k) - 0.5) * 0.18 * sa;
          const qd = pd - (1 - u * u) * 0.20 * cellD + (hash2(iw, jd, base + 30 + k) - 0.5) * 0.18 * cellD;
          const r = sa * L.ball * (0.78 + 0.40 * hash2(iw, jd, base + 40 + k))
            * (1 - 0.20 * Math.abs(u)) * size;
          const rd = r * 0.86;                                     // 径向略扁
          let ds = ds0 - qa;
          ds -= per * Math.round(ds / per);
          let dd = d0 - qd;
          if (dd > 0) dd *= 1.35;
          const q = (ds * ds) / (r * r) + (dd * dd) / (rd * rd);
          if (q < 5.5) sum += wgt * (Math.exp(-q) - 0.0041);
        }
      }
    }
    // 卷边：小尺度噪声切出云头（扇贝），只在云的上缘起作用
    if (sum > 0.02) {
      const fq2 = 1.5 / cellA;
      const sc = fbm(lon * fq2, lat * fq2, L.seed + 50, 2) - 0.5;
      sum += 0.26 * sc * smooth(0.02, 0.42, sum);
    }
    return sum;
  }

  // -------------------------------------------------------------- palette
  // 每层：[背光, 主体, 迎光]。C = 冷（灰蓝），W = 暖（灰褐），按地区场混合。
  const PAL_C = [
    [[24, 28, 36], [50, 54, 64], [86, 90, 100]],        // 远处：狄灰/炭灰
    [[46, 52, 66], [86, 94, 110], [136, 146, 162]],     // 云岸：深灰蓝（主体）
    [[118, 134, 156], [162, 176, 196], [214, 224, 234]],// 贴地图：浅灰蓝细小云缘
  ];
  const PAL_W = [
    [[28, 28, 32], [54, 52, 52], [90, 87, 83]],
    [[50, 50, 56], [90, 90, 94], [140, 140, 144]],
    [[132, 136, 142], [192, 192, 195], [232, 232, 230]],
  ];
  const SKY_N = [168, 172, 178];       // 靠地图一侧云隙里露出的天空
  const SKY_F = [30, 34, 44];          // 深处：深灰蓝，不是平黑
  const INK = [44, 50, 62];            // 云的墨线（灰蓝墨）
  const SWIRL_W = [96, 84, 70];        // 卷云线：褐
  const SWIRL_C = [32, 34, 42];        // 卷云线：炭灰
  const EDGE_INSET = 0.86;             // 只有雾底色、没有云压着的那圈边略压深一点

  // ------------------------------------------------------------------ paint
  // opts: { box:[lonMin,lonMax,latMin,latMax], reveal:[...], cloudDeg,
  //         rect:{left,top,width,height}（底图在画布 CSS 坐标里的位置）, scale: 设备像素/CSS 像素 }
  function paint(canvas, opts) {
    const scale = opts.scale || 1;
    const W = canvas.width, H = canvas.height;
    const ctx = canvas.getContext('2d');
    if (!W || !H || !opts.box || !opts.rect || !opts.rect.width) { ctx.clearRect(0, 0, W, H); return; }
    const [lonMin, lonMax, latMin, latMax] = opts.box;
    const rect = opts.rect;
    const degX = (lonMax - lonMin) / (rect.width * scale);
    const degY = (latMax - latMin) / (rect.height * scale);
    const lon0 = lonMin - rect.left * scale * degX;
    const lat0 = latMax + rect.top * scale * degY;
    const C = Math.max(1e-4, opts.cloudDeg || 1);
    const circles = prepare(opts.reveal);
    const NL = LAYERS.length;
    // 严格只在底图矩形内画雾（向外取整会把雾画到底图外一像素，留透明更安全）
    const outL = Math.max(0, Math.ceil(rect.left * scale));
    const outT = Math.max(0, Math.ceil(rect.top * scale));
    const outR = Math.min(W, Math.floor((rect.left + rect.width) * scale));
    const outB = Math.min(H, Math.floor((rect.top + rect.height) * scale));
    // 每层的切向格宽（度）与它在屏幕上的像素尺寸（用于光照/墨线的尺度）
    const CELL = [], CELL_PX = [];
    for (let l = 0; l < NL; l++) {
      let a = LAYERS[l].cell * C;
      const minA = LAYERS[l].min * scale * degX;
      if (a < minA) a = minA;
      CELL.push(a); CELL_PX.push(a / degX);
    }

    // 粗网格（每 S 设备像素）上算云场，逐像素双线性插值并取梯度。
    // 网格点 i 采样在像素坐标 x = i*S，读像素时按像素中心 (x+0.5) 折算到网格坐标。
    const S = Math.max(2, Math.round(1.5 * scale));
    const gw = Math.ceil(W / S) + 2, gh = Math.ceil(H / S) + 2;
    const F = LAYERS.map(() => new Float32Array(gw * gh));
    // ratio 不入网格：它逐像素用精确值算（精确值便宜，插值反而引入台阶）。
    const REG = new Float32Array(gw * gh);
    const PHS = new Float32Array(gw * gh);
    const swirlCell = Math.max(0.05 * C, 10 * degX);   // 卷云线的相位尺度
    for (let j = 0; j < gh; j++) {
      const lat = lat0 - j * S * degY;
      for (let i = 0; i < gw; i++) {
        const lon = lon0 + i * S * degX, k = j * gw + i;
        const info = ratioInfo(lon, lat, circles);
        const rr = info.r;
        const rv = fbm(lon * 0.35 / C + 41.7, lat * 0.35 / C - 7.3, 901, 2);  // 地区差异场
        REG[k] = rv;
        PHS[k] = (fbm(lon / swirlCell + 11.3, lat / swirlCell - 4.1, 941, 3) - 0.5) * 2;
        if (!(rr < 4.4) || info.ci < 0) continue;      // 太远就不必有云
        const d = rr - 1;
        for (let l = 0; l < NL; l++) {
          const B = LAYERS[l].band;
          const w = smooth(B[0], B[1], d) * (1 - smooth(B[2], B[3], d)) * (0.66 + 0.70 * rv);
          F[l][k] = w > 0.006 ? polarField(lon, lat, info, LAYERS[l], w, CELL[l]) : 0;
        }
      }
    }

    const img = ctx.createImageData(W, H);
    const out = img.data;
    const LX = -0.55, LY = -0.83;                 // 光从左上（屏幕 y 向下）
    const col = [0, 0, 0];
    out.fill(0);
    // ratio 逐列只算一次，存两个行缓存：本行和上一行。梯度用相邻像素的差，
    // 不用粗网格差分（粗网格差分会在采样点处突变，把平缓的等值线切成方块）。
    const ratRow = (y) => {
      const lat = lat0 - y * degY, row = new Float64Array(outR - outL + 1);
      for (let x = outL; x <= outR; x++) {
        const r = ratioAt(lon0 + x * degX, lat, circles);
        row[x - outL] = r > FAR_MAX ? FAR_MAX : r;
      }
      return row;
    };
    for (let y = outT; y < outB; y++) {
      const gy = (y + 0.5) / S, j0 = Math.floor(gy), fy = gy - j0;
      const ratRowNow = ratRow(y);
      for (let x = outL; x < outR; x++) {
        const o = (y * W + x) * 4;
        const gx = (x + 0.5) / S, i0 = Math.floor(gx), fx = gx - i0;
        const k = j0 * gw + i0, k1 = k + 1, k2 = k + gw, k3 = k2 + 1;
        const lon = lon0 + x * degX;
        const ratio = ratRowNow[x - outL];
        // 可见区里不铺任何东西
        if (!(ratio > INNER_CLEAR)) { out[o + 3] = 0; continue; }

        // 地区场与卷云相位必须插值：直接取最近网格点会在云体上留下网格步长的方块
        const rv = REG[k] * (1 - fx) * (1 - fy) + REG[k1] * fx * (1 - fy)
          + REG[k2] * (1 - fx) * fy + REG[k3] * fx * fy;
        const phs = PHS[k] * (1 - fx) * (1 - fy) + PHS[k1] * fx * (1 - fy)
          + PHS[k2] * (1 - fx) * fy + PHS[k3] * fx * fy;
        const warm = smooth(0.42, 0.78, rv);
        // 底色：云隙里的天空（越往外越暗，带一点横向晕染）
        const skyT = smooth(1.02, 3.20, ratio);
        const streak = fbm(lon * 2.2 / C, (lat0 - y * degY) * 11.0 / C, 61, 2) - 0.5;
        const streakK = 1 + streak * 0.16;
        col[0] = lerp(SKY_N[0], SKY_F[0], skyT) * streakK;
        col[1] = lerp(SKY_N[1], SKY_F[1], skyT) * streakK;
        col[2] = lerp(SKY_N[2], SKY_F[2], skyT) * streakK;

        let cover = 0;
        for (let l = 0; l < NL; l++) {          // 由远及近：后面的云盖住前面的
          const A = F[l];
          const a = A[k], b = A[k1], c = A[k2], e = A[k3];
          const m = a + (b - a) * fx + (c - a) * fy + (a - b - c + e) * fx * fy;
          if (m < 0.03) continue;
          const dx = ((b - a) * (1 - fy) + (e - c) * fy) / S;
          const dy = ((c - a) * (1 - fx) + (e - b) * fx) / S;
          const g = Math.max(Math.hypot(dx, dy), 0.005 / scale);   // 平台处不让距离爆掉
          const dist = (m - T) / g;                  // 到轮廓的有符号像素距离（>0 在云里）
          const cellPx = CELL_PX[l];
          // 近处的云在它下面那些云上投的淡影（只落在轮廓外、偏下方的一小圈）
          if (l > 0 && dist < 0 && dist > -0.35 * cellPx) {
            const below = Math.max(0, dy / g);
            const sh = (1 + dist / (0.35 * cellPx)) * (0.09 + 0.17 * below);
            col[0] *= 1 - sh; col[1] *= 1 - sh; col[2] *= 1 - sh;
          }
          const cov = smooth(-0.9, 0.9, dist);
          if (cov <= 0) continue;
          const P = PAL_C[l], Q = PAL_W[l];
          const nx = -dx / g, ny = -dy / g;
          const facing = nx * LX + ny * LY;          // 1 = 迎光的上缘
          const dScale = Math.max(0.50 * cellPx, 9 * scale);   // 云厚度的像素尺度
          // 云体「厚度」（场值）当起伏用：同一条云岸里、叠在一起的气团是一整块云
          const relief = smooth(0.48, 1.70, m);
          // 明暗只由「云体多厚 + 迎光面」决定，不再叠像素级晕染：
          // 多源噪声叠加会把三角形/块状的深浅拼接晒到画面上。
          let tone = 0.12 + 0.50 * relief + 0.30 * facing * (1 - 0.5 * relief);
          tone = tone < 0 ? 0 : (tone > 1 ? 1 : tone);
          let cr, cg, cb;
          if (tone < 0.5) {
            const t2 = tone * 2;
            cr = lerp(lerp(P[0][0], Q[0][0], warm), lerp(P[1][0], Q[1][0], warm), t2);
            cg = lerp(lerp(P[0][1], Q[0][1], warm), lerp(P[1][1], Q[1][1], warm), t2);
            cb = lerp(lerp(P[0][2], Q[0][2], warm), lerp(P[1][2], Q[1][2], warm), t2);
          } else {
            const t2 = (tone - 0.5) * 2;
            cr = lerp(lerp(P[1][0], Q[1][0], warm), lerp(P[2][0], Q[2][0], warm), t2);
            cg = lerp(lerp(P[1][1], Q[1][1], warm), lerp(P[2][1], Q[2][1], warm), t2);
            cb = lerp(lerp(P[1][2], Q[1][2], warm), lerp(P[2][2], Q[2][2], warm), t2);
          }
          // 墨线：只在外轮廓内侧一道，背光处粗，断笔更多（不然一圈太连续）
          const brk = vnoise(gx * 0.020 / scale + l * 7, gy * 0.020 / scale, 577 + l);
          const wInk = (0.5 + 1.0 * Math.max(0, -facing)) * scale * smooth(0.22, 0.55, brk) * LAYERS[l].ink;
          if (wInk > 0.05) {
            const inkA = (1 - smooth(wInk * 0.6, wInk * 0.6 + 1.2 * scale, Math.abs(dist - wInk * 0.45))) * 0.62;
            cr = lerp(cr, INK[0], inkA); cg = lerp(cg, INK[1], inkA); cb = lerp(cb, INK[2], inkA);
          }
          // 卷云线：云内部很淡的细弧（褐 ↔ 炭灰），短、弯、断续
          if (dist > 2 * scale) {
            const sv = Math.sin(phs * 3.1 + l * 1.7);
            const thick = 1 - smooth(0.10, 0.42, Math.abs(sv));
            const drk = vnoise(gx * 0.030 + l * 13, gy * 0.030, 559 + l);
            const ln = thick * smooth(0.30, 0.66, drk) * smooth(3 * scale, dScale, dist)
              * (l === 0 ? 0.34 : 0.24);
            if (ln > 0.02) {
              cr = lerp(cr, lerp(SWIRL_W[0], SWIRL_C[0], warm * 0.6), ln);
              cg = lerp(cg, lerp(SWIRL_W[1], SWIRL_C[1], warm * 0.6), ln);
              cb = lerp(cb, lerp(SWIRL_W[2], SWIRL_C[2], warm * 0.6), ln);
            }
          }
          col[0] = lerp(col[0], cr, cov); col[1] = lerp(col[1], cg, cov); col[2] = lerp(col[2], cb, cov);
          cover = Math.max(cover, cov);
        }

        // 越往外整体压暗（外围很暗但不是平黑）
        const dark = 1 - 0.26 * smooth(1.05, 3.40, ratio);
        col[0] *= dark; col[1] *= dark; col[2] *= dark;

        // ---- 不透明度：硬约束 + 一道只会向内收的雾边 ----
        // 这里**不再**画那道「细墨 + 亮边」的双线：云的轮廓本身已经有一圈墨线，
        // 再在雾边描一道就在近缘形成一圈连续的双层描边，看上去像环形道路。
        let alpha;
        if (ratio >= OPAQUE_AT) {
          alpha = 1;
        } else {
          // 扰动只加在 ratio 上（幅度小于余量），所以边只会往里多盖，绝不向外让
          const rip = (vnoise(lon * 26 / C, (lat0 - y * degY) * 26 / C, 733) - 0.5) * 0.056
            + (vnoise(lon * 62 / C, (lat0 - y * degY) * 62 / C, 737) - 0.5) * 0.022;
          const e = ratio + rip;
          // 梯度用本行相邻两个像素的精确 ratio 差：粗网格差分会在采样点处突变，
          // 把边界距离算成一个方块状的量。只在雾边那一圈用。
          const gr = Math.max(Math.abs(ratRowNow[x - outL + 1] - ratio), 1e-6);
          const dEdge = (e - EDGE_AT) / gr;          // 到雾边的像素距离（>0 在雾里）
          const fogA = smooth(-1.6 * scale, 1.6 * scale, dEdge);
          alpha = Math.max(cover, fogA);
          if (alpha > 0.02 && cover < 0.35) {
            // 只给「没有云压着、只靠雾底色」的那圈压一点深，让边有个柔软过渡
            col[0] *= EDGE_INSET; col[1] *= EDGE_INSET; col[2] *= EDGE_INSET;
          }
        }
        if (alpha <= 0) { out[o + 3] = 0; continue; }
        // 纸纹（极轻，低频）
        const grain = vnoise(lon * 6 / C, (lat0 - y * degY) * 6 / C, 71) - 0.5;
        const kk = 1 + grain * 0.02;
        out[o] = col[0] * kk; out[o + 1] = col[1] * kk; out[o + 2] = col[2] * kk;
        out[o + 3] = alpha * 255;
      }
    }
    ctx.putImageData(img, 0, 0);
  }

  window.TDMapFog = { paint, ratioAt: (lon, lat, reveal) => ratioAt(lon, lat, prepare(reveal)),
                      OPAQUE_AT, CLEAR_AT, INNER_CLEAR, EDGE_AT };
})();
