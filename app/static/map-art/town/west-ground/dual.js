/*
 * 织梦 · 西式水面/地面双网格的公共几何（照 west-base/tiles.js 的分界线规则）
 * 四角编码 mask = NW*8 + NE*4 + SW*2 + SE*1；瓦片内部坐标 0..48（y 向下），四角 = 四个逻辑格中心。
 * 「在」区（水 / 土地）= 是的那个角所在的象限；分界线落在 x=24 / y=24 两条中线上，
 * 过瓦片边中点且垂直于边，只在瓦片内部有手绘起伏；中心转角做圆角（半径 rad）。
 * 浏览器挂 window.TownArtWG_dual；Node 用 module.exports。依赖 core.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWG_core;
  var f = C.f, S = 48, M = 24;
  var BITS = [8, 4, 2, 1]; // 象限 q = qy*2+qx：NW NE SW SE
  function on(mask, qx, qy) { return !!(mask & BITS[qy * 2 + qx]); }
  function bin(m) { return ('000' + m.toString(2)).slice(-4); }
  var TILE = 'M0 0L48 0L48 48L0 48Z';

  /** a→b 的手绘线段：两端切线沿线段方向（在瓦片边上垂直于边），中点偏 w */
  function curve(a, b, w) {
    var dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1, nx = -dy / L, ny = dx / L;
    var m = [(a[0] + b[0]) / 2 + nx * w, (a[1] + b[1]) / 2 + ny * w];
    return 'C' + f(a[0] + dx * 0.25) + ' ' + f(a[1] + dy * 0.25) + ' ' + f(m[0] - dx * 0.18) + ' ' + f(m[1] - dy * 0.18) + ' ' + f(m[0]) + ' ' + f(m[1]) +
      'S' + f(b[0] - dx * 0.25) + ' ' + f(b[1] - dy * 0.25) + ' ' + f(b[0]) + ' ' + f(b[1]);
  }
  /** 象限内侧边界：从瓦片边中点进到中心圆角，再出到另一条边中点 */
  function inner(qx, qy, r, w1, w2) {
    var ox = qx * S, oy = qy * S, sx = qx ? 1 : -1, sy = qy ? 1 : -1;
    var A = [M, oy], E1 = [M, M + sy * r], E2 = [M + sx * r, M], B = [ox, M];
    return 'M' + f(A[0]) + ' ' + f(A[1]) + curve(A, E1, w1) + 'Q' + M + ' ' + M + ' ' + f(E2[0]) + ' ' + f(E2[1]) + curve(E2, B, w2);
  }
  function quadFill(qx, qy, r, w1, w2) { return inner(qx, qy, r, w1, w2) + 'L' + qx * S + ' ' + qy * S + 'Z'; }

  /**
   * 「在」区形状。返回 { k, fill, rule, outline, land }：
   *   fill/rule = 在区；outline = 分界线（开放路径）；land = 补集（evenodd），k = 在的角数。
   * opt.rad 中心圆角半径；opt.wig 起伏幅度；opt.diagRad 对角组合用的圆角（更大，保证两块不连通）。
   */
  function shape(ctx, mask, opt) {
    opt = opt || {};
    var rad = opt.rad || 10, wig = opt.wig == null ? 1.6 : opt.wig, k = 0, i, qs = [];
    for (i = 0; i < 4; i++) { var qx = i % 2, qy = i >> 1; if (on(mask, qx, qy)) { k++; qs.push([qx, qy]); } }
    var w = function () { return ctx.rnd(-wig, wig); };
    var out;
    if (k === 0) return { k: 0, fill: '', rule: 'nonzero', outline: '', land: TILE };
    if (k === 4) return { k: 4, fill: TILE, rule: 'nonzero', outline: '', land: '' };
    if (k === 3) {
      for (i = 0; i < 4; i++) if (!on(mask, i % 2, i >> 1)) break;
      var a = w(), b = w(), q = inner(i % 2, i >> 1, rad, a, b);
      out = { fill: TILE + quadFill(i % 2, i >> 1, rad, a, b), rule: 'evenodd', outline: q };
    } else if (k === 2 && mask !== 9 && mask !== 6) {
      var c = w(), sg;
      if (mask === 12) sg = ['M0 0L48 0L48 24', [48, 24], [0, 24]];
      else if (mask === 3) sg = ['M0 48L48 48L48 24', [48, 24], [0, 24]];
      else if (mask === 10) sg = ['M0 0L0 48L24 48', [24, 48], [24, 0]];
      else sg = ['M48 0L48 48L24 48', [24, 48], [24, 0]];
      var cv = curve(sg[1], sg[2], c);
      out = { fill: sg[0] + cv + 'Z', rule: 'nonzero', outline: 'M' + sg[1].join(' ') + cv };
    } else {
      var rr = k === 2 ? (opt.diagRad || rad + 4) : rad, fl = '', ol = '';
      qs.forEach(function (p) { var a1 = w(), b1 = w(); fl += quadFill(p[0], p[1], rr, a1, b1); ol += inner(p[0], p[1], rr, a1, b1); });
      out = { fill: fl, rule: 'nonzero', outline: ol };
    }
    out.k = k;
    out.land = out.rule === 'evenodd' ? out.fill.slice(TILE.length) : TILE + out.fill;
    return out;
  }

  /** 点到「在」区（各象限矩形之并）的近似距离；点在在区里返回负的到边界距离 */
  function distOn(mask, x, y) {
    var best = 1e9, inside = false;
    for (var i = 0; i < 4; i++) {
      if (!on(mask, i % 2, i >> 1)) continue;
      var x0 = (i % 2) * M, y0 = (i >> 1) * M, dx = Math.max(x0 - x, 0, x - x0 - M), dy = Math.max(y0 - y, 0, y - y0 - M);
      if (dx === 0 && dy === 0) inside = true;
      best = Math.min(best, Math.hypot(dx, dy));
    }
    if (!inside) return best;
    var d = 1e9;
    for (var j = 0; j < 4; j++) {
      if (on(mask, j % 2, j >> 1)) continue;
      var ax = (j % 2) * M, ay = (j >> 1) * M, ex = Math.max(ax - x, 0, x - ax - M), ey = Math.max(ay - y, 0, y - ay - M);
      d = Math.min(d, Math.hypot(ex, ey));
    }
    return -d;
  }
  /**
   * 在 [lo, hi] 距离带内取 n 个点（正 = 不在区一侧，负 = 在区一侧），离瓦片边至少 margin，点间距至少 gap。
   */
  function band(ctx, mask, n, lo, hi, margin, gap) {
    var pts = [], tries = 0;
    while (pts.length < n && tries++ < 400) {
      var x = ctx.rnd(margin, S - margin), y = ctx.rnd(margin, S - margin), d = distOn(mask, x, y);
      if (d < lo || d > hi) continue;
      if (pts.some(function (p) { return Math.hypot(p[0] - x, p[1] - y) < gap; })) continue;
      pts.push([x, y, d]);
    }
    return pts;
  }
  /** 沿分界线的宽描边（stroke 版的带子） */
  function stripe(d, w, color, op, dash) {
    if (!d) return '';
    return '<path d="' + d + '" fill="none" stroke="' + color + '" stroke-width="' + f(w) + '" stroke-linejoin="round" stroke-linecap="butt"' +
      (op != null && op < 1 ? ' stroke-opacity="' + f(op) + '"' : '') + (dash ? ' stroke-dasharray="' + dash + '"' : '') + '/>';
  }

  var api = { S: S, M: M, TILE: TILE, on: on, bin: bin, curve: curve, shape: shape, distOn: distOn, band: band, stripe: stripe };
  root.TownArtWG_dual = api;
  if (isNode) module.exports = api;
})(typeof window !== 'undefined' ? window : this);
