/*
 * 织梦 · 东方玄幻迷雾：祥云 + 海水纹（美术样板，尚未接入游戏）
 *
 * 画法参考国潮插画（只参考画法，不使用任何参考图像素，全部是原创程序化路径）：
 *   祥云 —— 一簇簇圆云头合成一团云，整团金线勾边；云团里再向下缩两圈（叠晕），
 *           由外到内颜色渐浅，形成一道道月牙形的轮廓线；最大的云头里勾一枚金色卷纹。
 *   海水 —— 地图底部一排排波浪色带：上沿金线勾边，下方三道平行水纹，波峰卷起带螺旋的浪花。
 *   点缀 —— 螺旋日轮、平底小金云（朵云）。
 *
 * 浏览器里挂到 window.FogXiangyun；Node 里 module.exports（给 export-svg.js 用）。
 */
(function (root) {
  'use strict';
  var PI2 = Math.PI * 2, uid = 0;

  function rng(seed) { // mulberry32
    return function () {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      var t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  function f(n) { return String(Math.round(n * 100) / 100); }
  function hx(c) { return [1, 3, 5].map(function (i) { return parseInt(c.slice(i, i + 2), 16); }); }
  function mix(a, b, t) {
    var A = hx(a), B = hx(b);
    return '#' + A.map(function (v, i) { var x = Math.round(v + (B[i] - v) * t); return (x < 16 ? '0' : '') + x.toString(16); }).join('');
  }

  // 色板：fill 本色、lite 叠晕最里一圈的浅色、line 勾边线（多为金色）
  var PAL = {
    cream:  { name: '米白', fill: '#f1dcae', lite: '#fbf0d4', line: '#c98f3c' },
    ochre:  { name: '赭黄', fill: '#eeb24f', lite: '#f8d78e', line: '#b06c24' },
    orange: { name: '橘红', fill: '#e47c36', lite: '#f3ae66', line: '#f4d07a' },
    vermil: { name: '朱红', fill: '#cd5030', lite: '#e7864f', line: '#f3c46a' },
    umber:  { name: '赭褐', fill: '#8c3d22', lite: '#b5623a', line: '#eeb75a' },
    teal:   { name: '青绿', fill: '#2e938d', lite: '#6cc1b3', line: '#f1cf7a' },
    navy:   { name: '藏青', fill: '#1f3c5b', lite: '#30697f', line: '#e9bb5a' }
  };

  function spiralPath(cx, cy, r0, r1, a0, turns, dir, n) {
    var d = '';
    for (var i = 0; i <= n; i++) {
      var t = i / n, a = a0 + dir * t * turns * PI2, r = r0 + (r1 - r0) * Math.pow(t, 0.85);
      d += (i ? 'L' : 'M') + f(cx + Math.cos(a) * r) + ' ' + f(cy + Math.sin(a) * r);
    }
    return d;
  }
  // c = [x, y, r, 长短比, 旋转角]：后两项缺省时是正圆；有了它们云头是略扁、略斜的椭圆，不再个个标准正圆
  function discs(C, k, drop, pad, fill) {
    return '<g fill="' + fill + '">' + C.map(function (c) {
      var cy = c[1] + (1 - k) * c[2] * drop, rr = Math.max(0.5, c[2] * k + pad);
      if (!c[3]) return '<circle cx="' + f(c[0]) + '" cy="' + f(cy) + '" r="' + f(rr) + '"/>';
      return '<ellipse cx="' + f(c[0]) + '" cy="' + f(cy) + '" rx="' + f(rr * c[3]) + '" ry="' + f(rr / c[3]) +
        '" transform="rotate(' + f(c[4]) + ' ' + f(c[0]) + ' ' + f(cy) + ')"/>';
    }).join('') + '</g>';
  }
  // 勾边并集：先画加粗一圈的线色圆，再画本色圆，露出来的正好是整团云的外轮廓线
  function inked(C, k, drop, fill, line, lw) { return discs(C, k, drop, lw, line) + discs(C, k, drop, 0, fill); }

  /**
   * 一团祥云。R = 尺度（像素）。云头朝 -y（排云墙时朝向地图），云顶在 y = -0.3R，云脚到 y ≈ +1.3R。
   */
  /**
   * form 决定云团的轮廓（不传则随机）：
   *   mound —— 馒头形，中间两三枚大云头（默认）
   *   tower —— 高耸的云堆，大云头一层层往上摞（主角云）
   *   bank  —— 又长又低的云带，底排许多小云头、只一枚大云头（贴地图一排用，避免碎成气泡）
   *   tuft  —— 一小簇，三四枚云头
   */
  function cluster(R, pal, seed, form) {
    var r = rng(seed), C = [], big = [];
    if (!form) { var q0 = r(); form = q0 < 0.45 ? 'mound' : q0 < 0.65 ? 'bank' : q0 < 0.85 ? 'tuft' : 'tower'; }
    var spec = {
      mound: { W: 2.6 + r() * 0.9, n: 5 + Math.floor(r() * 3), m: 2 + Math.floor(r() * 2), base: 0.36, bigR: 0.5, lift: 0 },
      tower: { W: 1.7 + r() * 0.5, n: 4 + Math.floor(r() * 2), m: 3 + Math.floor(r() * 2), base: 0.38, bigR: 0.5, lift: 1 },
      bank:  { W: 3.6 + r() * 1.0, n: 5 + Math.floor(r() * 2), m: 2, base: 0.4, bigR: 0.5, lift: 0 },
      tuft:  { W: 1.3 + r() * 0.4, n: 3, m: 1, base: 0.42, bigR: 0.52, lift: 0 }
    }[form];
    var W = R * spec.W, n = spec.n;
    for (var i = 0; i < n; i++) {
      var t = i / (n - 1) - 0.5, rr = R * (spec.base * 0.78 + 0.34 * r()) * (1.15 - 1.1 * t * t);
      C.push([t * W + (r() - 0.5) * R * 0.15, -rr * 0.6, rr]);
    }
    // 云头不要正圆：约一半云头上再鼓一枚小云瓣，整团轮廓更饱满、更随意
    var nb = C.length;
    for (var u = 0; u < nb; u++) {
      if (r() < 0.55) {
        var cc = C[u], an = -Math.PI / 2 + (r() - 0.5) * 2.2;
        C.push([cc[0] + Math.cos(an) * cc[2] * 0.62, cc[1] + Math.sin(an) * cc[2] * 0.62, cc[2] * (0.38 + r() * 0.2)]);
      }
    }
    var m = spec.m;
    for (var j = 0; j < m; j++) {
      var r2 = R * (spec.bigR + 0.22 * r()), c2;
      if (spec.lift) {
        // 摞起来：每一层往上抬、稍微左右摆，越往上越小一点
        r2 *= 1 - 0.1 * j;
        c2 = [(r() - 0.5) * R * 0.7 + (j % 2 ? -1 : 1) * R * 0.25, -R * 0.45 - j * R * 0.62 - r() * R * 0.1, r2];
      } else {
        c2 = [((m > 1 ? j / (m - 1) : 0.5) - 0.5) * W * 0.5 + (r() - 0.5) * R * 0.3, -R * 0.5 - r2 * 0.5 - r() * R * 0.15, r2];
      }
      C.push(c2); big.push(c2);
    }
    var top = Math.min.apply(null, C.map(function (c) { return c[1] - c[2]; }));
    C.forEach(function (c) { c[1] += -0.3 * R - top; });
    // 每枚云头各自略扁、略斜（宽 0.9–1.18 倍，斜 ±22°），整团轮廓更饱满随意
    C.forEach(function (c) { c[3] = 0.9 + r() * 0.28; c[4] = (r() - 0.5) * 44; });

    // 叠晕圈数也随云团变：小簇两圈，主角云四圈
    var rings = form === 'tower' ? 4 : form === 'tuft' ? 2 : 3;
    var out = [], lw = Math.max(1.6, R * 0.05);
    out.push(inked(C, 1, 0, pal.fill, pal.line, lw));
    for (var g = 1; g < rings; g++) {
      var tt = g / (rings - 1);
      out.push(inked(C, 1 - 0.52 * tt, 0.55 + 0.2 * tt, mix(pal.fill, pal.lite, 0.35 + 0.65 * tt), pal.line, Math.max(1, 1.4 - 0.2 * g)));
    }
    // 最大的一两枚云头里勾金色卷纹（主角云每枚大云头都勾）
    var nSp = form === 'tower' ? big.length : r() < 0.5 ? 1 : 2;
    big.sort(function (a, b) { return b[2] - a[2]; }).slice(0, nSp).forEach(function (c, q) {
      var dir = (q + (r() < 0.5 ? 0 : 1)) % 2 ? -1 : 1;
      var cy = c[1] + c[2] * 0.3;
      out.push('<path d="' + spiralPath(c[0], cy, c[2] * 0.42, c[2] * 0.05, dir > 0 ? Math.PI : 0, 1.5, dir, 54) +
        '" fill="none" stroke="' + pal.line + '" stroke-width="' + f(Math.max(1.4, R * 0.04)) + '" stroke-linecap="round"/>');
    });
    return '<g>' + out.join('') + '</g>';
  }

  /** 平底小金云（朵云），浮在云海上方作点缀。底边在 y = 0。 */
  function cloudlet(R, pal, seed) {
    var r = rng(seed), C = [], id = 'xy-cl' + (++uid), n = 3 + Math.floor(r() * 2);
    for (var i = 0; i < n; i++) {
      var t = i / (n - 1) - 0.5, rr = R * (0.36 + 0.16 * r()) * (1.2 - 1.2 * t * t);
      C.push([t * R * 2.2, -rr * 0.35, rr]);
    }
    C.push([(r() - 0.5) * R * 0.4, -R * 0.55, R * 0.5]);
    var x0 = Infinity, x1 = -Infinity;
    C.forEach(function (c) {
      if (Math.abs(c[1]) < c[2]) { var h = Math.sqrt(c[2] * c[2] - c[1] * c[1]); x0 = Math.min(x0, c[0] - h); x1 = Math.max(x1, c[0] + h); }
    });
    return '<defs><clipPath id="' + id + '"><rect x="' + f(-R * 3) + '" y="' + f(-R * 3) + '" width="' + f(R * 6) + '" height="' + f(R * 3) + '"/></clipPath></defs>' +
      '<g clip-path="url(#' + id + ')">' + inked(C, 1, 0, pal.fill, pal.line, 1.6) + inked(C, 0.62, 0.6, pal.lite, pal.line, 1.1) + '</g>' +
      '<path d="M' + f(x0 - 1) + ' 0H' + f(x1 + 1) + '" stroke="' + pal.line + '" stroke-width="1.8" stroke-linecap="round"/>' +
      '<path d="' + spiralPath(x1 + R * 0.12, -R * 0.28, R * 0.3, R * 0.04, Math.PI * 0.5, 1.2, -1, 30) +
      '" fill="none" stroke="' + pal.line + '" stroke-width="1.5" stroke-linecap="round"/>';
  }

  /** 螺旋日轮。 */
  function sun(cx, cy, r, pal) {
    return '<circle cx="' + f(cx) + '" cy="' + f(cy) + '" r="' + f(r + 2.5) + '" fill="' + pal.line + '"/>' +
      '<circle cx="' + f(cx) + '" cy="' + f(cy) + '" r="' + f(r) + '" fill="' + pal.fill + '"/>' +
      '<circle cx="' + f(cx) + '" cy="' + f(cy) + '" r="' + f(r * 0.6) + '" fill="' + mix(pal.fill, pal.lite, 0.6) + '"/>' +
      '<path d="' + spiralPath(cx, cy, r * 0.9, r * 0.03, 0, 4.2, 1, 260) + '" fill="none" stroke="' + pal.line + '" stroke-width="1.6" stroke-linecap="round"/>';
  }

  /**
   * 卷起的浪头：一道浪舌从后方贴着水面升起，到前方卷成一圈（像逗号 / 蝌蚪），
   * 圈里勾螺旋，浪舌上再勾两道顺着它的水纹。dir = 浪往哪边卷（1 向右）。
   */
  function crest(cx, cy, s, dir, pal) {
    var tail = [cx - dir * s * 2.6, cy + s * 1.05];
    var d = 'M' + f(tail[0]) + ' ' + f(tail[1]) +
      'Q' + f(cx - dir * s * 1.3) + ' ' + f(cy - s * 0.9) + ' ' + f(cx) + ' ' + f(cy - s) +
      'A' + f(s) + ' ' + f(s) + ' 0 0 ' + (dir > 0 ? 1 : 0) + ' ' + f(cx) + ' ' + f(cy + s) +
      'Q' + f(cx - dir * s * 1.1) + ' ' + f(cy + s * 1.15) + ' ' + f(tail[0]) + ' ' + f(tail[1]) + 'Z';
    var o = '<path d="' + d + '" fill="' + pal.lite + '" stroke="' + pal.line + '" stroke-width="1.8" stroke-linejoin="round"/>';
    for (var k = 1; k <= 2; k++) {
      var e = k * 0.28;
      o += '<path d="M' + f(cx - dir * s * (2.3 - e)) + ' ' + f(cy + s * (1.0 - e * 0.2)) + 'Q' + f(cx - dir * s * (1.25 - e * 0.4)) + ' ' + f(cy - s * (0.6 - e)) +
        ' ' + f(cx - dir * s * 0.05) + ' ' + f(cy - s * (1 - e * 1.1)) + '" fill="none" stroke="' + pal.line + '" stroke-opacity="0.8" stroke-width="1.2" stroke-linecap="round"/>';
    }
    o += '<path d="' + spiralPath(cx + dir * s * 0.05, cy + s * 0.05, s * 0.72, s * 0.06, dir > 0 ? -Math.PI / 2 : -Math.PI / 2, 1.5, dir, 60) +
      '" fill="none" stroke="' + pal.line + '" stroke-width="1.6" stroke-linecap="round"/>';
    return o;
  }

  // 一道波浪色带：先画浪花（下半截被色带盖住），再画色带、三道平行水纹、上沿勾边
  function band(W, H, base, bh, pal, r) {
    var lam = 180 + r() * 120, A = Math.min(bh * 0.24, 7 + r() * 7), ph = r() * PI2, ph2 = r() * PI2;
    function yAt(x) { return base + A * Math.sin(x / lam * PI2 + ph) + A * 0.3 * Math.sin(x / lam * 2.6 * PI2 + ph2); }
    var top = '', xs = [], ys = [];
    for (var x = -30; x <= W + 30; x += 4) { var y = yAt(x); xs.push(x); ys.push(y); top += (x === -30 ? 'M' : 'L') + f(x) + ' ' + f(y); }
    var o = [], dir = r() < 0.5 ? -1 : 1;
    for (var i = 1; i < ys.length - 1; i++) {
      if (ys[i] < ys[i - 1] && ys[i] <= ys[i + 1] && base - ys[i] > A * 0.5 && r() < 0.8) {
        var s = (A * 1.1 + bh * 0.14) * (0.7 + r() * 0.7);
        o.push(crest(xs[i] + dir * s * 0.3, ys[i] - s * 0.55, s, dir, pal));
      }
    }
    o.push('<path d="' + top + 'L' + (W + 30) + ' ' + (H + 30) + 'L-30 ' + (H + 30) + 'Z" fill="' + pal.fill + '"/>');
    for (var j = 1; j <= 3; j++) {
      o.push('<path d="' + top + '" transform="translate(0 ' + f(j * bh * 0.15) + ')" fill="none" stroke="' + pal.line +
        '" stroke-opacity="' + f(0.92 - 0.16 * j) + '" stroke-width="1.3"/>');
    }
    o.push('<path d="' + top + '" fill="none" stroke="' + pal.line + '" stroke-width="2.2"/>');
    return o.join('');
  }

  /**
   * 福船（国潮画法）：尖首方尾、艉楼高翘，船首画一只船眼；三桅硬帆（前桅略前倾），帆上一道道竹篾帆骨，
   * 整船平涂 + 金线勾边。(x, y) = 吃水线中点，dir = 船头朝向（1 向右）。
   * 局部坐标：船长约 112，吃水线 y = 0，主桅顶 y = -78；吃水线以下由海浪色带盖住。
   */
  function fuchuan(x, y, sc, dir) {
    var G = '#f3c46a', o = [], hullC = PAL.umber.fill, sail = PAL.vermil, lw = 'stroke="' + G + '" stroke-linejoin="round" stroke-linecap="round"';
    // 硬帆：[左, 右, 顶, 底, 前倾]，前缘直、后缘外鼓，帆骨横贯
    function junk(l, rr, t, b, lean) {
      var d = 'M' + f(l + lean) + ' ' + t + 'L' + rr + ' ' + (t + 5) + 'Q' + (rr + 7) + ' ' + f((t + b) / 2) + ' ' + rr + ' ' + b + 'L' + l + ' ' + b + 'Z';
      var s = '<path d="' + d + '" fill="' + sail.fill + '" ' + lw + ' stroke-width="1.6"/>';
      for (var i = 1; i <= 4; i++) {
        var yy = t + (b - t) * i / 5, xl = l + lean * (1 - i / 5);
        s += '<path d="M' + f(xl + 1) + ' ' + f(yy) + 'L' + f(rr + 3 * Math.sin(Math.PI * i / 5)) + ' ' + f(yy + 1.5) + '" fill="none" ' + lw + ' stroke-width="1.1"/>';
      }
      return s;
    }
    o.push(junk(-48, -24, -58, -30, 2));
    o.push(junk(-16, 18, -76, -20, 3));
    o.push(junk(20, 46, -62, -20, 4));
    o.push('<g fill="none" stroke="' + PAL.navy.fill + '" stroke-width="2.4" stroke-linecap="round"><path d="M-34 -26L-34 -60M0 -16L0 -80M30 -14L34 -64"/></g>');
    // 主桅飘带
    o.push('<path d="M0 -80Q-10 -84 -22 -80Q-14 -78 -10 -75Q-6 -77 0 -76Z" fill="' + PAL.ochre.fill + '" ' + lw + ' stroke-width="1"/>');
    // 船身：方尾高翘、尖首上扬
    var hull = 'M-58 -36L-44 -34L-40 -22L28 -14Q46 -16 58 -28L53 -10Q42 10 14 12L-30 12Q-50 8 -54 -12Z';
    o.push('<path d="' + hull + '" fill="' + hullC + '" ' + lw + ' stroke-width="2"/>');
    o.push('<path d="M-54 -20Q-6 -8 54 -18M-52 -6Q0 4 50 -6" fill="none" ' + lw + ' stroke-width="1.3"/>');
    // 艉楼彩绘板与栏杆
    o.push('<path d="M-55 -32L-45 -31L-42 -22L-53 -22Z" fill="' + PAL.teal.fill + '" ' + lw + ' stroke-width="1"/>' +
      '<path d="M-44 -34L-44 -38L-26 -36L-26 -21M-38 -37L-38 -22M-32 -36.5L-32 -21.5" fill="none" ' + lw + ' stroke-width="1"/>');
    // 船眼
    o.push('<circle cx="42" cy="-9" r="4" fill="' + PAL.cream.lite + '" ' + lw + ' stroke-width="1.2"/><circle cx="43" cy="-9" r="1.9" fill="' + PAL.navy.fill + '"/>');
    return '<g transform="translate(' + f(x) + ' ' + f(y) + ') scale(' + f(sc * dir) + ' ' + f(sc) + ')">' + o.join('') + '</g>';
  }

  /** 海水纹：从 y0 铺到 H，rows 道色带，由远（上）到近（下）叠放；色带间散几艘福船。 */
  function waves(W, y0, H, seed, rows) {
    var r = rng(seed), out = [], N = rows || 4, bh = (H - y0) / N, fleet = [];
    var order = ['teal', 'navy', 'orange', 'teal', 'vermil', 'navy', 'ochre', 'umber'];
    var start = Math.floor(r() * order.length);
    for (var k = 0; k < N + 1; k++) {
      var base = y0 + k * bh * 0.86, ships = '', want = k === 0 ? 1 : (r() < 0.55 ? 1 : 0), tries = 0, placed = 0;
      // 福船画在这一排色带之前：吃水线以下被浪盖住；同排、相邻排都要错开
      while (placed < want && tries++ < 20) {
        var sx = 90 + r() * (W - 180);
        if (fleet.some(function (p) { return Math.abs(p[0] - sx) < 200; })) continue;   // 任何两排之间都错开，免得上下叠成一摞
        fleet.push([sx, k]); placed++;
        ships += fuchuan(sx, base + bh * 0.05, bh / 60 * (0.95 + 0.2 * k) * (0.9 + r() * 0.2), r() < 0.5 ? 1 : -1);
      }
      out.push(ships + band(W, H, base, bh, PAL[order[(start + k * 3) % order.length]], r));
    }
    return '<g>' + out.join('') + '</g>';
  }

  var API = { PAL: PAL, mix: mix, cluster: cluster, cloudlet: cloudlet, sun: sun, fuchuan: fuchuan, waves: waves };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.FogXiangyun = API;
})(this);
