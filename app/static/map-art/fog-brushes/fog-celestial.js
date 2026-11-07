/*
 * 织梦 · 迷雾角饰：日、月、星与海水（美术样板，尚未接入游戏）
 *
 * 两套风格各自一组，全部是原创程序化路径：
 *   东方玄幻 —— 红日（朱红日轮 + 金线光环）、新月（米金月牙 + 金色双勾）。
 *   西方中世纪 —— 木刻风格的人面太阳（直芒与火焰芒交替）、带眼的月牙（月牙内刻线排线）、
 *                 八芒小星、雕版式海浪（一排排尖谷圆峰的浪 + 卷钩 + 虚线刻纹）。
 *
 * 浏览器里挂到 window.FogCelestial；Node 里 module.exports。
 */
(function (root) {
  'use strict';
  var PI2 = Math.PI * 2, uid = 0;
  function f(n) { return String(Math.round(n * 100) / 100); }
  function P(p) { return f(p[0]) + ' ' + f(p[1]); }
  function rng(seed) { // mulberry32
    return function () {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      var t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  function spiral(cx, cy, r0, r1, a0, turns, dir, n) {
    var d = '';
    for (var i = 0; i <= n; i++) {
      var t = i / n, a = a0 + dir * t * turns * PI2, r = r0 + (r1 - r0) * Math.pow(t, 0.85);
      d += (i ? 'L' : 'M') + f(cx + Math.cos(a) * r) + ' ' + f(cy + Math.sin(a) * r);
    }
    return d;
  }

  /** 月牙：圆 A(cx,cy,r) 减去圆 B(cx+ox, cy+oy, r2)。返回 { d, bx, by, r2 }。 */
  function crescent(cx, cy, r, ox, oy, r2) {
    var d = Math.hypot(ox, oy), ux = ox / d, uy = oy / d;
    var a = (r * r - r2 * r2 + d * d) / (2 * d), h = Math.sqrt(Math.max(0, r * r - a * a));
    var mx = cx + ux * a, my = cy + uy * a;
    var p1 = [mx - uy * h, my + ux * h], p2 = [mx + uy * h, my - ux * h];
    return {
      d: 'M' + P(p1) + 'A' + f(r) + ' ' + f(r) + ' 0 1 1 ' + P(p2) + 'A' + f(r2) + ' ' + f(r2) + ' 0 0 0 ' + P(p1) + 'Z',
      bx: cx + ox, by: cy + oy, r2: r2, ux: ux, uy: uy
    };
  }
  // 月牙内顺着内弧刻几道线（clip 在月牙里）
  function crescentLines(c, n, step, color, op, w) {
    var id = 'fc-cl' + (++uid), o = '<defs><clipPath id="' + id + '"><path d="' + c.d + '"/></clipPath></defs><g clip-path="url(#' + id + ')" fill="none" stroke="' + color + '">';
    for (var k = 1; k <= n; k++) {
      o += '<circle cx="' + f(c.bx) + '" cy="' + f(c.by) + '" r="' + f(c.r2 + k * step) + '" stroke-opacity="' + f(op * (1 - 0.15 * (k - 1))) + '" stroke-width="' + f(w) + '"/>';
    }
    return o + '</g>';
  }

  // ================= 东方玄幻 =================
  var GOLD = '#f3c46a', GOLD_D = '#c98f3c';

  /** 红日：两道金线光环、金边、朱红日轮、内圈一道细金线。 */
  function redSun(cx, cy, r) {
    return '<circle cx="' + f(cx) + '" cy="' + f(cy) + '" r="' + f(r * 1.32) + '" fill="none" stroke="' + GOLD + '" stroke-opacity="0.5" stroke-width="2"/>' +
      '<circle cx="' + f(cx) + '" cy="' + f(cy) + '" r="' + f(r * 1.16) + '" fill="none" stroke="' + GOLD + '" stroke-opacity="0.8" stroke-width="2.4"/>' +
      '<circle cx="' + f(cx) + '" cy="' + f(cy) + '" r="' + f(r + 3.5) + '" fill="' + GOLD + '"/>' +
      '<circle cx="' + f(cx) + '" cy="' + f(cy) + '" r="' + f(r) + '" fill="#c8321f"/>' +
      '<circle cx="' + f(cx - r * 0.06) + '" cy="' + f(cy - r * 0.06) + '" r="' + f(r * 0.8) + '" fill="#d9472b"/>' +
      '<circle cx="' + f(cx) + '" cy="' + f(cy) + '" r="' + f(r * 0.64) + '" fill="none" stroke="' + GOLD + '" stroke-opacity="0.55" stroke-width="1.4"/>';
  }

  /** 新月：米金月牙、金边、月牙内两道金色双勾，外围一道淡金光环。 */
  function eastMoon(cx, cy, r) {
    var c = crescent(cx, cy, r, r * 0.5, -r * 0.22, r * 0.86);
    return '<circle cx="' + f(cx) + '" cy="' + f(cy) + '" r="' + f(r * 1.22) + '" fill="none" stroke="' + GOLD + '" stroke-opacity="0.45" stroke-width="1.8"/>' +
      '<path d="' + c.d + '" fill="#f7e8bd" stroke="' + GOLD_D + '" stroke-width="2.4" stroke-linejoin="round"/>' +
      crescentLines(c, 2, r * 0.13, GOLD_D, 0.8, 1.5);
  }

  // ================= 西方中世纪 =================
  var INK = '#4a3826', WASH = '#e3c47a', PAPER = '#efdfb2';

  /** 木刻人面太阳：直芒与火焰芒交替，日轮里画一张简单的脸。 */
  function westSun(cx, cy, r) {
    var o = [], N = 16;
    for (var i = 0; i < N; i++) {
      var a = i / N * PI2 - Math.PI / 2;
      if (i % 2 === 0) {
        var w = 0.12, L = r * 1.6;
        o.push('M' + P([cx + Math.cos(a - w) * r, cy + Math.sin(a - w) * r]) + 'L' + P([cx + Math.cos(a) * L, cy + Math.sin(a) * L]) +
          'L' + P([cx + Math.cos(a + w) * r, cy + Math.sin(a + w) * r]) + 'Z');
      } else {
        // 火焰芒：两侧各弯一下，尖端偏一侧
        var w2 = 0.1, L2 = r * 1.85, b = a + 0.12;
        var tip = [cx + Math.cos(b) * L2, cy + Math.sin(b) * L2];
        var m1 = [cx + Math.cos(a - 0.16) * r * 1.38, cy + Math.sin(a - 0.16) * r * 1.38];
        var m2 = [cx + Math.cos(a + 0.02) * r * 1.42, cy + Math.sin(a + 0.02) * r * 1.42];
        o.push('M' + P([cx + Math.cos(a - w2) * r, cy + Math.sin(a - w2) * r]) + 'Q' + P(m1) + ' ' + P(tip) +
          'Q' + P(m2) + ' ' + P([cx + Math.cos(a + w2) * r, cy + Math.sin(a + w2) * r]) + 'Z');
      }
    }
    var s = '<path d="' + o.join('') + '" fill="' + WASH + '" stroke="' + INK + '" stroke-width="1.4" stroke-linejoin="round"/>' +
      '<circle cx="' + f(cx) + '" cy="' + f(cy) + '" r="' + f(r) + '" fill="' + PAPER + '" stroke="' + INK + '" stroke-width="2"/>' +
      '<circle cx="' + f(cx) + '" cy="' + f(cy) + '" r="' + f(r * 0.86) + '" fill="none" stroke="' + INK + '" stroke-opacity="0.4" stroke-width="0.9" stroke-dasharray="3 3"/>';
    // 脸
    var g = '<g fill="none" stroke="' + INK + '" stroke-width="' + f(Math.max(1.5, r * 0.04)) + '" stroke-linecap="round">';
    [-1, 1].forEach(function (sd) {
      var ex = cx + sd * r * 0.3, ey = cy - r * 0.1;
      g += '<path d="M' + P([ex - r * 0.13, ey]) + 'Q' + P([ex, ey - r * 0.1]) + ' ' + P([ex + r * 0.13, ey]) + 'Q' + P([ex, ey + r * 0.07]) + ' ' + P([ex - r * 0.13, ey]) + '"/>' +
        '<path d="M' + P([ex - r * 0.15, ey - r * 0.16]) + 'Q' + P([ex, ey - r * 0.27]) + ' ' + P([ex + r * 0.15, ey - r * 0.17]) + '"/>' +
        '<path d="M' + P([cx + sd * r * 0.42, cy + r * 0.2]) + 'l' + f(sd * -r * 0.06) + ' ' + f(r * 0.06) + 'm' + f(sd * r * 0.03) + ' ' + f(-r * 0.1) + 'l' + f(sd * -r * 0.06) + ' ' + f(r * 0.06) + '" stroke-width="1" stroke-opacity="0.6"/>';
    });
    g += '<path d="M' + P([cx, cy - r * 0.05]) + 'L' + P([cx + r * 0.07, cy + r * 0.2]) + 'Q' + P([cx, cy + r * 0.26]) + ' ' + P([cx - r * 0.06, cy + r * 0.22]) + '"/>' +
      '<path d="M' + P([cx - r * 0.24, cy + r * 0.4]) + 'Q' + P([cx, cy + r * 0.54]) + ' ' + P([cx + r * 0.24, cy + r * 0.4]) + '"/></g>';
    g += '<g fill="' + INK + '"><circle cx="' + f(cx - r * 0.3) + '" cy="' + f(cy - r * 0.1) + '" r="' + f(r * 0.065) + '"/><circle cx="' + f(cx + r * 0.3) + '" cy="' + f(cy - r * 0.1) + '" r="' + f(r * 0.065) + '"/></g>';
    return s + g;
  }

  /** 月牙：纸色填充、墨线勾边、内弧刻线排线，内弧上一只闭着的眼。 */
  function westMoon(cx, cy, r) {
    var c = crescent(cx, cy, r, r * 0.52, -r * 0.18, r * 0.84);
    var ix = c.bx - c.ux * c.r2, iy = c.by - c.uy * c.r2;           // 内弧中点
    var ex = ix - c.ux * r * 0.14, ey = iy - c.uy * r * 0.14 - r * 0.12;
    return '<path d="' + c.d + '" fill="' + PAPER + '" stroke="' + INK + '" stroke-width="2" stroke-linejoin="round"/>' +
      crescentLines(c, 4, r * 0.09, INK, 0.45, 0.9) +
      '<path d="M' + P([ex - r * 0.14, ey]) + 'Q' + P([ex, ey + r * 0.11]) + ' ' + P([ex + r * 0.14, ey]) + '" fill="none" stroke="' + INK + '" stroke-width="' + f(Math.max(1.6, r * 0.04)) + '" stroke-linecap="round"/>' +
      '<path d="M' + P([ex - r * 0.14, ey - r * 0.1]) + 'Q' + P([ex, ey - r * 0.2]) + ' ' + P([ex + r * 0.14, ey - r * 0.1]) + '" fill="none" stroke="' + INK + '" stroke-width="' + f(Math.max(1.2, r * 0.028)) + '" stroke-linecap="round"/>' +
      // 鼻尖与嘴角：月牙脸的侧影
      '<path d="M' + P([ix - c.ux * r * 0.02, iy - c.uy * r * 0.02 + r * 0.06]) + 'l' + f(-c.ux * r * 0.1) + ' ' + f(r * 0.06) + 'l' + f(c.ux * r * 0.08) + ' ' + f(r * 0.03) + '" fill="none" stroke="' + INK + '" stroke-width="' + f(Math.max(1.3, r * 0.03)) + '" stroke-linecap="round" stroke-linejoin="round"/>' +
      '<path d="M' + P([ix - c.ux * r * 0.06, iy + r * 0.24]) + 'q' + f(-c.ux * r * 0.07) + ' ' + f(r * 0.05) + ' ' + f(-c.ux * r * 0.14) + ' ' + f(r * 0.01) + '" fill="none" stroke="' + INK + '" stroke-width="' + f(Math.max(1.3, r * 0.03)) + '" stroke-linecap="round"/>';
  }

  /** 八芒小星。 */
  function westStar(cx, cy, r) {
    var d = '';
    for (var i = 0; i < 16; i++) {
      var a = i / 16 * PI2 - Math.PI / 2, rr = i % 2 ? r * 0.38 : (i % 4 ? r * 0.7 : r);
      d += (i ? 'L' : 'M') + P([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr]);
    }
    return '<path d="' + d + 'Z" fill="' + WASH + '" stroke="' + INK + '" stroke-width="1.1" stroke-linejoin="round"/>';
  }

  /**
   * 雕版式海浪：一排排尖谷圆峰的浪，浪峰上随机卷一枚墨线钩，浪身下两道虚线刻纹。
   * 从 y0 铺到 H，rows 道，由远（上）到近（下）叠放；颜色与西方云墙同属旧纸灰褐。
   */
  /** 卷起的大浪头（木刻风）：浪舌升起、前端卷成一圈，圈里螺旋，浪舌上几道刻线，浪尖甩出两枚小卷沫。 */
  function breaker(cx, cy, s, dir, fill) {
    var tail = [cx - dir * s * 2.5, cy + s * 1.1];
    var d = 'M' + P(tail) + 'Q' + P([cx - dir * s * 1.25, cy - s * 0.95]) + ' ' + P([cx, cy - s]) +
      'A' + f(s) + ' ' + f(s) + ' 0 0 ' + (dir > 0 ? 1 : 0) + ' ' + P([cx, cy + s]) +
      'Q' + P([cx - dir * s * 1.05, cy + s * 1.15]) + ' ' + P(tail) + 'Z';
    var o = '<path d="' + d + '" fill="' + fill + '" stroke="' + INK + '" stroke-width="1.7" stroke-linejoin="round"/>';
    for (var k = 1; k <= 3; k++) {
      var e = k * 0.22;
      o += '<path d="M' + P([cx - dir * s * (2.2 - e), cy + s * (1.0 - e * 0.15)]) + 'Q' + P([cx - dir * s * (1.2 - e * 0.4), cy - s * (0.62 - e)]) +
        ' ' + P([cx - dir * s * 0.1, cy - s * (0.95 - e * 1.1)]) + '" fill="none" stroke="' + INK + '" stroke-opacity="0.55" stroke-width="0.9" stroke-dasharray="' + (k === 2 ? '6 3' : 'none') + '"/>';
    }
    o += '<path d="' + spiral(cx + dir * s * 0.04, cy + s * 0.04, s * 0.74, s * 0.08, -Math.PI / 2, 1.5, dir, 60) +
      '" fill="none" stroke="' + INK + '" stroke-width="1.5" stroke-linecap="round"/>';
    [[0.55, -1.25, 0.22], [1.0, -0.95, 0.15]].forEach(function (q) {
      var fx = cx + dir * s * q[0], fy = cy + s * q[1];
      o += '<path d="' + spiral(fx, fy, s * q[2], s * 0.02, Math.PI / 2, 1.1, dir, 20) + '" fill="none" stroke="' + INK + '" stroke-width="1.1" stroke-linecap="round"/>';
    });
    return o;
  }

  var CROSS = '#9a3b2a';
  function lwAttr() { return 'stroke="' + INK + '" stroke-linejoin="round" stroke-linecap="round"'; }

  /**
   * 方帆：顶边挂在帆桁上，两侧向船头鼓起，底边向下兜成一道弧；帆面几道竖向缝线。cross = true 画红十字。
   * bulge 越大越鼓风。
   */
  function squareSail(l, rr, t, b, bulge, cross) {
    var lw = lwAttr(), m = (t + b) / 2, cx = (l + rr) / 2, o = '';
    var d = 'M' + f(l) + ' ' + f(t) + 'L' + f(rr) + ' ' + f(t) + 'Q' + f(rr + bulge) + ' ' + f(m) + ' ' + f(rr - 1) + ' ' + f(b) +
      'Q' + f(cx + bulge * 0.4) + ' ' + f(b + bulge * 0.5) + ' ' + f(l + 1) + ' ' + f(b) + 'Q' + f(l + bulge * 0.9) + ' ' + f(m) + ' ' + f(l) + ' ' + f(t) + 'Z';
    o += '<path d="' + d + '" fill="' + PAPER + '" ' + lw + ' stroke-width="1.6"/>';
    for (var i = 1; i <= 3; i++) {
      var sx = l + (rr - l) * i / 4;
      o += '<path d="M' + f(sx) + ' ' + f(t + 1) + 'Q' + f(sx + bulge * 0.9) + ' ' + f(m) + ' ' + f(sx + bulge * 0.15) + ' ' + f(b + bulge * 0.35) +
        '" fill="none" ' + lw + ' stroke-width="0.7" stroke-opacity="0.38"/>';
    }
    if (cross) {
      var w = Math.max(2.6, (rr - l) * 0.075), vx = cx + bulge * 0.55, hy = t + (b - t) * 0.42;
      o += '<path d="M' + f(vx) + ' ' + f(t + (b - t) * 0.16) + 'L' + f(vx) + ' ' + f(b - (b - t) * 0.12) +
        'M' + f(l + (rr - l) * 0.2 + bulge * 0.5) + ' ' + f(hy) + 'L' + f(rr - (rr - l) * 0.2 + bulge * 0.5) + ' ' + f(hy) +
        '" fill="none" stroke="' + CROSS + '" stroke-width="' + f(w) + '" stroke-linecap="butt"/>';
    }
    o += '<path d="M' + f(l - 3) + ' ' + f(t) + 'L' + f(rr + 3) + ' ' + f(t) + '" fill="none" ' + lw + ' stroke-width="2"/>';
    return o;
  }
  // 船身：淡彩平涂 + 墨线勾边；inner = 船壳内（被船身轮廓裁切）的细节
  function hullWith(id, hull, inner) {
    return '<defs><clipPath id="' + id + '"><path d="' + hull + '"/></clipPath></defs>' +
      '<path d="' + hull + '" fill="' + WASH + '" ' + lwAttr() + ' stroke-width="2"/>' +
      '<g clip-path="url(#' + id + ')">' + inner + '</g>';
  }
  function place(x, y, sc, dir, o) {
    return '<g transform="translate(' + f(x) + ' ' + f(y) + ') scale(' + f(sc * dir) + ' ' + f(sc) + ')">' + o.join('') + '</g>';
  }
  function boxes(xs, y, w, h) {
    return xs.map(function (bx) { return '<rect x="' + f(bx) + '" y="' + f(y) + '" width="' + f(w) + '" height="' + f(h) + '"/>'; }).join('');
  }
  function range(a, b, step) { var r = []; for (var v = a; v <= b + 1e-6; v += step) r.push(v); return r; }

  /**
   * 木刻卡拉克船（哥伦布圣玛利亚号一类）：高耸的艉楼与外悬的艏楼、船腰低；三桅——
   * 前桅、主桅方帆（主帆极宽大、帆脚几乎压到船腰甲板，上面一面小顶帆），后桅三角帆；帆上红十字。
   * 主桅高（桅顶约高出甲板一个船长），主帆挂在桅杆中下段、帆脚贴近船腰甲板；主帆上方有桅楼，再上一面小顶帆。
   * (x, y) = 吃水线中点；sc = 缩放；dir = 船头朝向（1 向右）。局部坐标：船长约 118，吃水线 y = 0，主桅顶 y = -114。
   * 船身吃水线以下的部分由调用方用海浪色带盖住。
   */
  function carrack(x, y, sc, dir) {
    var id = 'fc-ship' + (++uid), lw = lwAttr(), o = [];
    var hull = 'M-56 -36L-30 -36L-30 -24L-24 -17L24 -17L28 -24L30 -33L62 -33L60 -25Q54 -4 36 8L30 12L-34 12Q-52 6 -57 -14Z';
    // 索具与桅杆（画在帆后面）
    o.push('<g fill="none" ' + lw + ' stroke-width="0.9" stroke-opacity="0.6"><path d="M4 -114L62 -30M4 -114L-54 -36M4 -80L-50 -36M42 -88L82 -43M-40 -90L-56 -37M4 -106L42 -84"/></g>');
    o.push('<g fill="none" ' + lw + ' stroke-width="2.4"><path d="M4 -17L4 -114M42 -33L42 -88M-40 -36L-40 -90M58 -28L84 -44"/></g>');
    // 后桅三角帆：斜帆桁，帆脚落在艉楼上
    o.push('<path d="M-60 -43L-22 -94Q-26 -66 -36 -41Q-46 -39 -60 -43Z" fill="' + PAPER + '" ' + lw + ' stroke-width="1.6"/>' +
      '<path d="M-50 -50Q-36 -66 -29 -78M-45 -44Q-36 -54 -33 -60" fill="none" ' + lw + ' stroke-width="0.7" stroke-opacity="0.4"/>' +
      '<path d="M-64 -39L-18 -99" fill="none" ' + lw + ' stroke-width="1.8"/>');
    // 主帆（挂在桅杆中下段，帆脚贴近船腰甲板）、前帆（帆脚贴近艏楼）
    o.push(squareSail(-26, 34, -70, -22, 8, true));
    o.push(squareSail(28, 58, -78, -40, 4.5, true));
    // 主帆上方的桅楼（瞭望台）与一面小顶帆
    o.push('<path d="M-4 -80L12 -80L10 -73L-2 -73Z" fill="' + WASH + '" ' + lw + ' stroke-width="1.4"/>' +
      '<path d="M1 -80L1 -73M7 -80L7 -73" fill="none" ' + lw + ' stroke-width="0.8" stroke-opacity="0.6"/>');
    o.push(squareSail(-9, 17, -106, -86, 3, false));
    // 桅顶旗
    o.push('<path d="M4 -114L22 -111L4 -108Z" fill="' + CROSS + '" ' + lw + ' stroke-width="1"/>' +
      '<path d="M42 -88L52 -86L42 -84Z" fill="' + CROSS + '" ' + lw + ' stroke-width="1"/>' +
      '<path d="M-40 -90L-30 -88L-40 -86Z" fill="' + CROSS + '" ' + lw + ' stroke-width="1"/>');
    // 船身：两道腰板、艉楼与艏楼的窗、船腰几个炮门
    o.push(hullWith(id, hull,
      '<g fill="none" ' + lw + '><path d="M-60 -10Q0 -2 64 -14" stroke-width="1.4"/><path d="M-60 2Q0 10 54 0" stroke-width="1.4"/>' +
      '<path d="M-58 -30L-30 -30M30 -27L62 -27" stroke-width="0.9" stroke-opacity="0.6"/></g>' +
      '<g fill="' + INK + '">' + boxes(range(-52, -36, 5.5), -34, 3.2, 3.6) + boxes(range(34, 56, 5.5), -32, 3.2, 3.4) + boxes(range(-16, 20, 12), -13, 3.6, 3.6) + '</g>'));
    // 艉楼、艏楼栏杆
    o.push('<path d="M-56 -36L-56 -41L-30 -41L-30 -36M-49 -41L-49 -36M-43 -41L-43 -36M-37 -41L-37 -36' +
      'M30 -33L30 -38L62 -38L62 -33M38 -38L38 -33M46 -38L46 -33M54 -38L54 -33" fill="none" ' + lw + ' stroke-width="1"/>');
    return place(x, y, sc, dir, o);
  }

  /**
   * 柯克船（13–14 世纪）：圆胖的叠板船身，单桅一面大方帆，艉部一座小城楼，艉杆一面旗。参考样，暂不进雾效。
   * 局部坐标：船长约 98，吃水线 y = 0，桅顶 y = -98。
   */
  function cog(x, y, sc, dir) {
    var id = 'fc-ship' + (++uid), lw = lwAttr(), o = [];
    var hull = 'M-48 -28L-24 -26Q8 -22 38 -26L50 -32L48 -22Q44 0 28 10L-32 10Q-46 4 -50 -12Z';
    o.push('<g fill="none" ' + lw + ' stroke-width="0.9" stroke-opacity="0.6"><path d="M2 -98L50 -30M2 -98L-44 -40M2 -98L-14 -24M2 -98L18 -24"/></g>');
    o.push('<path d="M2 -22L2 -98" fill="none" ' + lw + ' stroke-width="2.6"/>');
    o.push(squareSail(-30, 36, -88, -32, 8, false));
    o.push('<path d="M-28 -50Q4 -46 38 -50" fill="none" ' + lw + ' stroke-width="0.9" stroke-opacity="0.55"/>');
    o.push(hullWith(id, hull, '<g fill="none" ' + lw + '>' + [-20, -12, -4, 4].map(function (yy) {
      return '<path d="M-54 ' + yy + 'Q0 ' + (yy + 6) + ' 54 ' + (yy - 4) + '" stroke-width="1.1" stroke-opacity="0.75"/>';
    }).join('') + '</g>'));
    // 艉部小城楼、艏部小平台
    o.push('<path d="M-50 -28L-50 -40L-26 -40L-26 -27Z" fill="' + WASH + '" ' + lw + ' stroke-width="1.6"/>' +
      '<path d="M-50 -40L-50 -44L-46 -44L-46 -40M-42 -40L-42 -44L-38 -44L-38 -40M-34 -40L-34 -44L-30 -44L-30 -40" fill="none" ' + lw + ' stroke-width="1"/>' +
      '<path d="M38 -26L38 -35L52 -35L50 -32" fill="none" ' + lw + ' stroke-width="1.3"/>');
    o.push('<path d="M-48 -44L-48 -58M-48 -58L-36 -55L-48 -51Z" fill="' + CROSS + '" ' + lw + ' stroke-width="1"/>');
    return place(x, y, sc, dir, o);
  }

  /**
   * 战列舰 / 盖伦式大帆船：长船身三层炮门，三桅各挂四层方帆、主桅最高，艏斜桅上两面三角帆，后桅一面纵帆。
   * 参考样，暂不进雾效。局部坐标：船长约 172，吃水线 y = 0，主桅顶 y = -152。
   */
  function galleon(x, y, sc, dir) {
    var id = 'fc-ship' + (++uid), lw = lwAttr(), o = [];
    var hull = 'M-84 -34L-70 -36L-60 -32L66 -30L86 -34L84 -26Q76 -2 62 8L56 12L-68 12Q-82 6 -86 -16Z';
    o.push('<g fill="none" ' + lw + ' stroke-width="0.8" stroke-opacity="0.55"><path d="M48 -140L128 -55M2 -152L48 -122M2 -152L-84 -36M-50 -126L2 -112M2 -152L-50 -118"/></g>');
    o.push('<g fill="none" ' + lw + ' stroke-width="2.4"><path d="M-50 -32L-50 -126M2 -30L2 -152M48 -30L48 -140M80 -30L130 -56"/></g>');
    // 艏三角帆
    o.push('<path d="M48 -128L126 -55L78 -40Z" fill="' + PAPER + '" ' + lw + ' stroke-width="1.4"/>' +
      '<path d="M48 -100L104 -45L62 -36Z" fill="' + PAPER + '" ' + lw + ' stroke-width="1.4"/>');
    // 后桅纵帆与两层顶帆
    o.push('<path d="M-50 -96L-84 -86L-86 -42L-50 -40Z" fill="' + PAPER + '" ' + lw + ' stroke-width="1.5"/>' +
      '<path d="M-50 -96L-88 -84M-52 -40L-90 -42" fill="none" ' + lw + ' stroke-width="1.6"/>');
    o.push(squareSail(-66, -34, -118, -100, 2, false) + squareSail(-68, -32, -96, -72, 3, false));
    // 主桅、前桅各四层
    [[-26, 30, -72, -38, 5], [-22, 26, -104, -76, 4], [-16, 20, -128, -108, 3], [-10, 14, -146, -131, 2]].forEach(function (q) { o.push(squareSail(q[0], q[1], q[2], q[3], q[4], false)); });
    [[24, 72, -68, -36, 5], [28, 68, -98, -72, 4], [32, 64, -120, -102, 3], [36, 60, -136, -123, 2]].forEach(function (q) { o.push(squareSail(q[0], q[1], q[2], q[3], q[4], false)); });
    o.push('<path d="M2 -152L20 -156L14 -150L20 -144L2 -146Z" fill="#3d4f6a" ' + lw + ' stroke-width="1"/>');
    // 船身：三道腰板，每道下面一排炮门
    var ports = '';
    [-24, -14, -4].forEach(function (py, i) { ports += boxes(range(-72 + i * 3, 70 - i * 6, 8), py, 3.6, 3.4); });
    o.push(hullWith(id, hull,
      '<g fill="none" ' + lw + '><path d="M-90 -27L90 -26M-90 -17L90 -16M-90 -7L86 -6" stroke-width="1.3"/></g>' +
      '<g fill="' + INK + '">' + ports + '</g>'));
    o.push('<path d="M-84 -34L-84 -40L-60 -38L-60 -32M66 -30L66 -36L86 -38L86 -34" fill="none" ' + lw + ' stroke-width="1"/>');
    return place(x, y, sc, dir, o);
  }


  function westWaves(W, y0, H, seed, rows) {
    var r = rng(seed), out = [], N = rows || 4, bh = (H - y0) / N;
    var fills = ['#cdc1a1', '#bfb291', '#d6caab', '#b3a584'];
    var fleet = []; // 所有已放的船 [x, 排号]，相邻排之间也要错开，免得前后两艘叠成一团
    for (var k = 0; k < N + 1; k++) {
      var base = y0 + k * bh * 0.82, lam = 46 + r() * 34, A = 6 + r() * 4, ph = r() * Math.PI;
      // 振幅沿岸起伏：两道慢正弦叠成包络，浪有高有低，不再像一条均匀花边
      var e1 = r() * PI2, e2 = r() * PI2, el = 240 + r() * 220;
      var amp = function (x) {
        return A * (0.45 + 0.75 * (0.5 + 0.5 * Math.sin(x / el * PI2 + e1)) + 0.4 * (0.5 + 0.5 * Math.sin(x / (el * 0.41) * PI2 + e2)));
      };
      var yAt = function (x) { return base - amp(x) * Math.pow(Math.abs(Math.sin(x / lam * Math.PI + ph)), 0.55); };
      var top = '';
      for (var x = -30; x <= W + 30; x += 3) top += (x === -30 ? 'M' : 'L') + f(x) + ' ' + f(yAt(x));
      // 大浪头画在色带之前：下半身沉进水里，只露出卷起的浪尖，不像一枚枚贝壳搁在水面上
      var pre = [];
      var o = ['<path d="' + top + 'L' + (W + 30) + ' ' + (H + 30) + 'L-30 ' + (H + 30) + 'Z" fill="' + fills[k % fills.length] + '"/>'];
      for (var j = 1; j <= 2; j++) {
        o.push('<path d="' + top + '" transform="translate(' + f(j * 7) + ' ' + f(j * bh * 0.2) + ')" fill="none" stroke="' + INK +
          '" stroke-opacity="' + f(0.55 - 0.15 * j) + '" stroke-width="1" stroke-dasharray="' + (j === 1 ? '16 5' : '9 6') + '"/>');
      }
      o.push('<path d="' + top + '" fill="none" stroke="' + INK + '" stroke-width="1.6" stroke-linejoin="round"/>');
      // 卡拉克船：每排一到两艘，远排小、近排大；画在色带之前，吃水线以下被这一排浪盖住
      var ships = [], want = 1 + (r() < 0.6 ? 1 : 0), tries = 0;
      while (ships.length < want && tries++ < 20) {
        var sx = 80 + r() * (W - 160);
        if (ships.some(function (p) { return Math.abs(p - sx) < 260; })) continue;
        if (fleet.some(function (p) { return Math.abs(p[1] - k) <= 2 && Math.abs(p[0] - sx) < 150; })) continue;
        ships.push(sx); fleet.push([sx, k]);
        var ssc = bh / 80 * (0.95 + 0.2 * k) * (0.88 + r() * 0.24);
        pre.push(carrack(sx, base - amp(sx) * 0.3, ssc, r() < 0.5 ? 1 : -1));
      }
      // 浪峰卷钩：每个峰顶右侧卷一小圈（像木刻里的浪尖）
      var dir = r() < 0.5 ? 1 : -1, lastBig = -1e9;
      for (var n = Math.ceil(-30 / lam - ph / Math.PI); ; n++) {
        var px = (n + 0.5 - ph / Math.PI) * lam;
        if (px > W + 30) break;
        if (px < -30) continue;
        var a = amp(px);
        // 振幅最高处偶尔掀起一个大浪头（相隔至少 260px）
        var nearShip = ships.some(function (p) { return Math.abs(p - px) < 80; });
        if (!nearShip && a > A * 1.15 && px - lastBig > 260 && r() < 0.55) {
          var sb = a * (1.45 + r() * 0.5) + bh * 0.12;
          pre.push(breaker(px + dir * sb * 0.3, base - a - sb * 0.12, sb, dir, fills[(k + 2) % fills.length]));
          lastBig = px; continue;
        }
        if (r() > 0.7) continue;
        var s = a * (0.75 + r() * 0.4), cx = px + dir * s * 0.55, cy = base - a + s * 0.85;
        o.push('<path d="' + spiral(cx, cy, s, s * 0.12, dir > 0 ? -Math.PI * 0.95 : -Math.PI * 0.05, 1.25, dir, 34) +
          '" fill="none" stroke="' + INK + '" stroke-width="1.4" stroke-linecap="round"/>');
      }
      out.push(pre.join('') + o.join(''));
    }
    return '<g>' + out.join('') + '</g>';
  }

  var API = { redSun: redSun, eastMoon: eastMoon, westSun: westSun, westMoon: westMoon, westStar: westStar, carrack: carrack, cog: cog, galleon: galleon, westWaves: westWaves };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.FogCelestial = API;
})(this);
