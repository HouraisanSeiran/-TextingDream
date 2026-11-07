/*
 * 织梦 · 西式资源点第二批 —— 公共构件：小屋 / 敞棚、田垄、树、水塘、桶、草垛、晾架
 * 全部挂在 C.K 上；坐标同 draw(ctx, W, D) 的地面坐标。
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWS2_core;
  var P = C.P, f = C.f, path = C.path, line = C.line, ell = C.ell, poly = C.poly, seg = C.seg, shade = C.shade;
  var K = C.K = C.K || {};
  function q(x0, y0, x1, y1) { return poly([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]); }
  K.q = q;
  /** 小屋：x 左，yb 墙脚，w 宽，hw 墙高，rh 屋面纵深；o: wall roof roof2 rows door('open'|'none') doorX win timber open(敞棚) */
  K.shed = function (ctx, x, yb, w, hw, rh, o) {
    o = o || {};
    var s = shade(poly([[x + w, yb], [x + w + 9, yb - 4], [x + w + 9, yb - hw - rh * 0.6], [x + w, yb - hw]]));
    if (o.open) {
      s += path(q(x, yb - hw, x + w, yb), '#2e241a', 1.2, 0.85);
      var n = Math.max(2, Math.round(w / 22));
      for (var i = 0; i <= n; i++) s += C.post(x + 2 + (w - 4) * i / n, yb, hw, 3);
    } else {
      s += path(q(x, yb - hw, x + w, yb), o.wall || P.plaster, 1.4);
      if (o.timber) s += line(seg(x, yb - hw * 0.5, x + w, yb - hw * 0.5) + seg(x + w * 0.33, yb - hw, x + w * 0.33, yb) +
        seg(x + w * 0.67, yb - hw, x + w * 0.67, yb), 1.5, 1, P.timber);
      var dw = Math.min(12, w * 0.3), dx = o.doorX != null ? o.doorX : x + w / 2 - dw / 2;
      if (o.door !== 'none') s += path(q(dx, yb - Math.min(hw - 2, 16), dx + dw, yb), o.door === 'open' ? '#2e241a' : P.dark, 1.1);
      for (var j = 0; j < (o.win || 0); j++) {
        var wx = x + 5 + j * (w - 16) / Math.max(1, o.win - 1);
        if (Math.abs(wx + 3 - (dx + dw / 2)) < dw) continue;
        s += path(q(wx, yb - hw + 5, wx + 6, yb - hw + 11), '#2e241a', 0.9);
      }
    }
    s += C.roofGable(x - 5, x + w + 5, yb - hw + 2, yb - hw - rh, Math.min(10, rh * 0.5), o.roof || P.thatch, o.roof2 || P.thatch2, o.rows || 4);
    return s;
  };
  /** 田垄：矩形区内横向垄沟 + 每垄一行作物 plant(ctx, x, y) */
  K.field = function (ctx, x0, y0, x1, y1, soil, gap, step, plant) {
    var s = path(q(x0, y0, x1, y1), soil || P.soil, 1.2), d = '', x, y;
    for (y = y0 + gap; y < y1 - 1; y += gap) d += seg(x0 + 2, y, x1 - 2, y);
    s += line(d, 0.8, 0.55, P.soil2);
    if (plant) for (y = y0 + gap - 1; y < y1 - 1; y += gap) for (x = x0 + step / 2; x < x1 - 2; x += step) s += plant(ctx, x + ctx.rnd(-1, 1), y);
    return s;
  };
  /** 树：干 + 两层树冠 + nf 个果 */
  K.tree = function (ctx, x, yb, r, leaf, fruit, nf, leafHi) {
    var s = C.shadowEll(x + r * 0.5, yb, r * 0.9, r * 0.3);
    s += path(poly([[x - 1.8, yb], [x - 1.2, yb - r * 0.9], [x + 1.2, yb - r * 0.9], [x + 1.8, yb]]), P.dark, 1);
    s += path(C.blob(ctx, x, yb - r * 1.5, r, r * 0.8, 7, 0.15), leaf || P.leaf, 1.3);
    s += path(C.blob(ctx, x - r * 0.25, yb - r * 1.75, r * 0.5, r * 0.35, 5, 0.15), leafHi || P.leaf2, 0);
    for (var i = 0; i < (nf || 0); i++) s += ell(x + ctx.rnd(-r * 0.7, r * 0.7), yb - r * 1.5 + ctx.rnd(-r * 0.5, r * 0.45), 1.5, 1.4, fruit, 0.6);
    return s;
  };
  /** 水塘：泥岸 + 水面 #a9b8ad + 两道水纹 */
  K.pond = function (ctx, cx, cy, rx, ry) {
    var s = path(C.blob(ctx, cx, cy, rx + 3, ry + 2, 8, 0.05), P.mud, 1.2);
    s += path(C.blob(ctx, cx, cy, rx, ry, 8, 0.05), P.water, 1.4);
    return s + line(seg(cx - rx * 0.5, cy - ry * 0.2, cx - rx * 0.1, cy - ry * 0.2) + seg(cx + rx * 0.1, cy + ry * 0.3, cx + rx * 0.5, cy + ry * 0.3), 0.8, 0.7, P.water2);
  };
  /** 方池（发酵池、沤麻池、洗矿槽）：石沿 + 液面 */
  K.basin = function (x, yb, w, dp, liquid, rim) {
    var s = shade(poly([[x + w, yb], [x + w + 5, yb - 2], [x + w + 5, yb - dp], [x + w, yb - dp]]));
    s += C.block(x, yb, w, dp, 5, rim || P.stone, P.stone2, 1.4);
    return s + path(q(x + 3, yb - 5 - dp + 3, x + w - 3, yb - 8), liquid || P.water, 1);
  };
  /** 木桶 */
  K.barrel = function (x, yb, r, fill, h) {
    h = h || r * 2.2;
    var s = C.shadowEll(x + 2, yb, r * 1.2, r * 0.35);
    s += path('M' + f(x - r) + ' ' + f(yb - h) + 'L' + f(x - r) + ' ' + f(yb) + 'A' + f(r) + ' ' + f(r * 0.35) + ' 0 0 0 ' + f(x + r) + ' ' + f(yb) +
      'L' + f(x + r) + ' ' + f(yb - h) + 'Z', fill || P.wood, 1.2);
    s += line(seg(x - r, yb - h * 0.3, x + r, yb - h * 0.3) + seg(x - r, yb - h * 0.75, x + r, yb - h * 0.75), 1, 1, P.dark);
    return s + ell(x, yb - h, r, r * 0.35, P.wash, 1.1);
  };
  /** 草垛 / 谷物堆垛：圆顶 + 草茎短线 */
  K.stack = function (ctx, x, yb, r, fill, fill2) {
    var s = C.shadowEll(x + r * 0.4, yb, r * 1.1, r * 0.35);
    s += path('M' + f(x - r) + ' ' + f(yb) + 'Q' + f(x - r * 1.05) + ' ' + f(yb - r * 1.9) + ' ' + f(x) + ' ' + f(yb - r * 2) +
      'Q' + f(x + r * 1.05) + ' ' + f(yb - r * 1.9) + ' ' + f(x + r) + ' ' + f(yb) + 'Z', fill || P.wheat, 1.3);
    var d = '';
    for (var i = 0; i < 7; i++) { var u = ctx.rnd(-0.7, 0.7), v = ctx.rnd(0.3, 1.5); d += seg(x + u * r, yb - v * r, x + u * r + 2, yb - v * r + 3); }
    s += line(d, 0.7, 0.55);
    return s + path('M' + f(x + r * 0.3) + ' ' + f(yb - r * 1.9) + 'Q' + f(x + r) + ' ' + f(yb - r * 1.6) + ' ' + f(x + r) + ' ' + f(yb) + 'L' + f(x + r * 0.55) + ' ' + f(yb) + 'Z', fill2 || P.wheat2, 0, 0.8);
  };
  /** 晾架：两根立柱 + n 根横杆；返回 { svg, bars:[y...] } */
  K.rack = function (x, yb, w, h, n) {
    var s = C.post(x, yb, h, 2.6) + C.post(x + w, yb, h, 2.6), bars = [], d = '';
    for (var i = 0; i < n; i++) { var y = yb - h + 2 + i * (h * 0.5 / Math.max(1, n - 1)); bars.push(y); d += seg(x - 2, y, x + w + 2, y); }
    return { svg: s + line(d, 1.6, 1, P.dark), bars: bars };
  };
})(typeof window !== 'undefined' ? window : this);
