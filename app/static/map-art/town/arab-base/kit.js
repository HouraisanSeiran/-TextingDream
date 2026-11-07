/*
 * 织梦 · 阿拉伯风格民居小件：内院铺地、水池 / 喷泉、拱廊（riwaq）、外挂楼梯、陶罐、晾晒布（美术样板，尚未接入游戏）
 * 浏览器挂 window.TownArtAB_kit；Node 用 module.exports。依赖 core.js、parts.js、parts2.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtAB_core;
  var Q = isNode ? require('./parts.js') : root.TownArtAB_parts;
  var P = C.PAL, f = C.f;

  /** 内院铺地：浅石灰方砖，8 px 一格 */
  function yard(ctx, x0, x1, y0, y1, col) {
    var s = C.rect(x0, y0, x1 - x0, y1 - y0, col || '#eadcb8', 0), d = '';
    for (var x = x0 + 8; x < x1 - 1; x += 8) d += 'M' + f(x) + ' ' + f(y0) + 'V' + f(y1);
    for (var y = y0 + 8; y < y1 - 1; y += 8) d += 'M' + f(x0) + ' ' + f(y) + 'H' + f(x1);
    return s + C.line(d, 0.6, 0.3);
  }
  /** 水池：青瓷砖池沿 + 水面；fount = 中心小喷泉 */
  function pool(ctx, x0, x1, y0, y1, fount) {
    var s = C.rect(x0 - 2.5, y0 - 2.5, x1 - x0 + 5, y1 - y0 + 5, P.turq, 1.1) + C.rect(x0, y0, x1 - x0, y1 - y0, P.water, 1);
    s += C.line('M' + f(x0 + 3) + ' ' + f(y0 + 3) + 'h' + f((x1 - x0) * 0.4) + 'M' + f(x0 + (x1 - x0) * 0.5) + ' ' + f(y1 - 4) + 'h' + f((x1 - x0) * 0.3), 0.8, 0.55, P.lime);
    if (fount) {
      var cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
      s += C.ell(cx, cy + 1, 3.2, 1.8, P.lime2, 0.9) + C.rect(cx - 1, cy - 4, 2, 5, P.lime2, 0.8) + C.line('M' + f(cx) + ' ' + f(cy - 4) + 'q-2 -2 -4 2M' + f(cx) + ' ' + f(cy - 4) + 'q2 -2 4 2', 0.8, 0.9, P.turq2);
    }
    return s;
  }
  /** 拱廊：在 x0..x1 底 yb 的立面上开 n 个拱洞（拱高 ah），kind = pointed / horseshoe */
  function arcade(ctx, x0, x1, yb, ah, n, kind, frame) {
    var pier = 3.2, w = (x1 - x0 - pier * (n + 1)) / n, s = '';
    for (var i = 0; i < n; i++) {
      var x = x0 + pier + i * (w + pier);
      var d = kind === 'horseshoe' ? Q.horseshoeD(x, yb, w, ah - w * 0.75) : Q.pointedD(x, yb, w, ah - w * 0.62);
      if (frame) s += C.path(kind === 'horseshoe' ? Q.horseshoeD(x - 1.2, yb, w + 2.4, ah - w * 0.75) : Q.pointedD(x - 1.2, yb, w + 2.4, ah - w * 0.62, (w + 2.4) * 0.66), frame, 0.8);
      s += C.path(d, P.hole, 1.1);
    }
    return s;
  }
  /** 沿立面斜上的外挂楼梯（从左下 (x, yb) 往右上升 h，宽 w） */
  function stair(ctx, x, yb, w, h, col) {
    var n = Math.max(3, Math.round(h / 4)), sx = w / n, sy = h / n, d = 'M' + f(x) + ' ' + f(yb), t = '';
    for (var i = 0; i < n; i++) { d += 'v' + f(-sy) + 'h' + f(sx); t += 'M' + f(x + i * sx) + ' ' + f(yb - (i + 1) * sy) + 'h' + f(sx); }
    d += 'V' + f(yb) + 'Z';
    return C.path(d, col || P.mud2, 1.1) + C.line(t, 0.8, 0.6, P.lime);
  }
  /** 陶罐 */
  function jar(ctx, x, yb, h, col) {
    var r = h * 0.38;
    return C.ell(x + 2, yb + 0.5, r + 1, 1.3, P.ink, 0, 0.18) +
      C.path('M' + f(x - r * 0.45) + ' ' + f(yb) + 'Q' + f(x - r * 1.25) + ' ' + f(yb - h * 0.55) + ' ' + f(x - r * 0.35) + ' ' + f(yb - h * 0.85) + 'V' + f(yb - h) + 'H' + f(x + r * 0.35) + 'V' + f(yb - h * 0.85) +
        'Q' + f(x + r * 1.25) + ' ' + f(yb - h * 0.55) + ' ' + f(x + r * 0.45) + ' ' + f(yb) + 'Z', col || P.ochre2, 1) +
      C.line('M' + f(x - r * 0.8) + ' ' + f(yb - h * 0.55) + 'h' + f(r * 1.6), 0.7, 0.6);
  }
  /** 屋顶晾布：两根桩之间一条绳挂几块布 */
  function laundry(ctx, x0, x1, y, cols) {
    var s = C.line('M' + f(x0) + ' ' + f(y) + 'v-9M' + f(x1) + ' ' + f(y) + 'v-9M' + f(x0) + ' ' + f(y - 8) + 'Q' + f((x0 + x1) / 2) + ' ' + f(y - 6) + ' ' + f(x1) + ' ' + f(y - 8), 0.8, 0.9, P.wood);
    var n = cols.length, step = (x1 - x0) / (n + 1);
    for (var i = 0; i < n; i++) s += C.rect(x0 + step * (i + 0.6), y - 7.4, step * 0.75, 4.5, cols[i], 0.6);
    ctx.top(y - 10);
    return s;
  }
  var API = { yard: yard, pool: pool, arcade: arcade, stair: stair, jar: jar, laundry: laundry };
  root.TownArtAB_kit = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
