/*
 * 织梦 · east-site 共用部件（二）：方块、竹筐、坑、梯子、轮、水面、竹竿架、烟。
 * 浏览器挂 window.TownArtES_kit2，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'));
  else root.TownArtES_kit2 = factory(root.TownArtES_core);
})(this, function (C) {
  'use strict';
  var S = C.S, f = C.f, poly = C.poly, path = C.path, rect = C.rect, ell = C.ell, circ = C.circ, ln = C.ln;
  var G = S.ink, LW = S.lw, LD = S.lwd;

  /** 3/4 视方块：前面 x0..x1 × (yb-h..yb)，顶面向后 dp。 */
  function box(x0, x1, yb, h, dp, top, front, sw) {
    return rect(x0, yb - h - dp, x1 - x0, dp, top, G, sw || LD) + rect(x0, yb - h, x1 - x0, h, front, G, sw || LD);
  }
  /** 竹筐：底宽 w，高 h，脚底 (cx, yb)；fill 为筐里的东西（null 则空筐）。 */
  function basket(cx, yb, w, h, fill, fill2, r) {
    var t = w * 0.62, o = C.shadowEll(cx + 2, yb, w * 0.6, 2.4);
    if (fill) {
      o += path('M' + f(cx - t) + ' ' + f(yb - h) + 'Q' + f(cx) + ' ' + f(yb - h - w * 0.5) + ' ' + f(cx + t) + ' ' + f(yb - h) + 'Z', fill2 || fill, G, LD);
      for (var i = 0; i < 4; i++) { var x = cx - t * 0.6 + i * t * 0.4, y = yb - h - 1.5 - (i % 2) * 2.5; o += circ(x, y, 1.6 + (r ? r() : 0.5), fill, null, 0); }
    }
    o += poly([[cx - t, yb - h], [cx + t, yb - h], [cx + w / 2, yb], [cx - w / 2, yb]], S.thatch, G, LD);
    for (var k = 1; k < 4; k++) { var yy = yb - h + h * k / 4; o += ln(cx - t + (t - w / 2) * k / 4, yy, cx + t - (t - w / 2) * k / 4, yy, S.thatch2, 0.8); }
    o += ln(cx - t - 0.5, yb - h, cx + t + 0.5, yb - h, S.wood3, 1.6);
    return o;
  }
  /** 地面上的坑：外沿 (x0..x1, y0..y1) 圆角椭圆，后壁深 dep。 */
  function pit(x0, y0, x1, y1, dep, wall, floor) {
    var cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, rx = (x1 - x0) / 2, ry = (y1 - y0) / 2;
    var o = ell(cx, cy, rx + 2, ry + 2, S.earth3, G, LD);
    o += ell(cx, cy, rx, ry, wall || S.brown2, null, 0);
    o += ell(cx, cy + dep * 0.5, rx * 0.82, Math.max(2, ry - dep * 0.5), floor || S.earth3, null, 0);
    return o;
  }
  /** 竖立的木梯：x 处，从 yt 到 yb，宽 w。 */
  function ladder(x, yt, yb, w) {
    w = w || 7;
    var o = ln(x - w / 2, yt, x - w / 2, yb, S.wood3, 1.6) + ln(x + w / 2, yt, x + w / 2, yb, S.wood3, 1.6);
    for (var y = yt + 3; y < yb; y += 5) o += ln(x - w / 2, y, x + w / 2, y, S.wood2, 1.2);
    return o;
  }
  /** 轮子（正面看）：r 半径，n 辐条。 */
  function wheel(cx, cy, r, n, col) {
    var o = circ(cx, cy, r, null, G, 3.2) + circ(cx, cy, r, null, col || S.wood3, 1.8);
    for (var i = 0; i < n; i++) { var a = i / n * Math.PI * 2; o += ln(cx, cy, cx + Math.cos(a) * r, cy + Math.sin(a) * r, col || S.wood3, 1.1); }
    return o + circ(cx, cy, r * 0.18, S.wood2, G, 0.8);
  }
  /** 水面多边形：底色 + 几道浅色波纹（水色与 east-ground 一致）。 */
  function water(a, id, r, flat) {
    var xs = a.map(function (p) { return p[0]; }), ys = a.map(function (p) { return p[1]; });
    var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs), y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys), w = '';
    for (var y = y0 + 4; y < y1; y += 6) {
      var x = x0 + 3 + (r ? r() * 8 : 2);
      while (x < x1 - 6) { w += path('M' + f(x) + ' ' + f(y) + 'q2.5 -1.6 5 0', null, S.water2, 1); x += 10 + (r ? r() * 8 : 4); }
    }
    return poly(a, S.water, flat ? null : G, flat ? 0 : LD) + C.clip(id + '-wt', poly(a, '#000'), w);
  }
  /** 竹竿（带节）。 */
  function bamboo(x1, y1, x2, y2, w) {
    w = w || 2;
    var o = ln(x1, y1, x2, y2, G, w + 1.4) + ln(x1, y1, x2, y2, S.leaf2, w), L = Math.hypot(x2 - x1, y2 - y1), n = Math.floor(L / 9);
    for (var i = 1; i <= n; i++) { var t = i / (n + 1); o += circ(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, w * 0.55, S.leaf, null, 0); }
    return o;
  }
  /** 一缕烟：从 (x,y) 向上，两三团云头（平涂，半透明）。 */
  function smoke(x, y, s) {
    s = s || 1;
    return circ(x, y - 6 * s, 3.4 * s, S.cream2, G, 0.8, C.fop(0.85)) + circ(x + 4 * s, y - 13 * s, 4.4 * s, S.cream2, G, 0.8, C.fop(0.8)) +
      circ(x + 1 * s, y - 21 * s, 5 * s, S.cream2, G, 0.8, C.fop(0.7));
  }
  /** 场地垫：占地内的半透明夯土。 */
  function pad(x0, y0, x1, y1, col, o) { return poly([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], col || S.earth2, null, 0, C.fop(o == null ? 0.5 : o)); }
  /** 粗木条（金线外框）。 */
  function bar(x1, y1, x2, y2, w, col) { return ln(x1, y1, x2, y2, G, w + 1.8) + ln(x1, y1, x2, y2, col || S.wood, w); }

  return { box: box, basket: basket, pit: pit, ladder: ladder, wheel: wheel, water: water, bamboo: bamboo, smoke: smoke, pad: pad, bar: bar };
});
