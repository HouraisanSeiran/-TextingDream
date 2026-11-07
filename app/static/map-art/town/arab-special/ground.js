/*
 * 阿拉伯风格地面画笔：八角净池、石板缝、树（椰枣/柏）、花坛、水渠。地面进深略压 0.8 以显斜俯视。
 * 浏览器挂 window.TownArtAS_ground；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var N = typeof module !== 'undefined' && module.exports;
  var K = N ? require('./core.js') : root.TownArtAS_core;
  var C = K.C, f = K.f;

  function octPts(cx, cy, rx, ry) {
    var p = [];
    for (var i = 0; i < 8; i++) { var a = Math.PI * (i + 0.5) / 4; p.push([cx + Math.cos(a) * rx, cy + Math.sin(a) * ry]); }
    return p;
  }
  /** 八角净池：石沿 + 水面 + 中心喷口 */
  function pool(cx, cy, rx, ry, spout) {
    var s = K.poly(octPts(cx, cy + 1.5, rx, ry), C.adobe3, 1.2);
    s += K.poly(octPts(cx, cy, rx, ry), C.lime2, 1.3);
    s += K.poly(octPts(cx, cy, rx * 0.8, ry * 0.78), C.water, 1);
    s += K.ln('M' + f(cx - rx * 0.45) + ' ' + f(cy - ry * 0.15) + 'q' + f(rx * 0.12) + ' -1.2 ' + f(rx * 0.24) + ' 0' +
      'M' + f(cx + rx * 0.1) + ' ' + f(cy + ry * 0.35) + 'q' + f(rx * 0.12) + ' -1.2 ' + f(rx * 0.24) + ' 0', 0.7, 0.55, C.lime);
    if (spout !== false) {
      s += K.rect(cx - 1.8, cy - 6, 3.6, 6, C.lime, 0.8);
      s += K.ellipse(cx, cy - 6.5, 3.4, 1.6, C.lime2, 0.8);
    }
    return s;
  }
  /** 矩形水池/水渠 */
  function basin(x, y, w, h, rim) {
    var t = rim == null ? 2.5 : rim;
    return K.rect(x, y + 1.5, w, h, C.adobe3, 1) + K.rect(x, y, w, h, C.lime2, 1.2) + K.rect(x + t, y + t, w - 2 * t, h - 2 * t, C.water, 0.9);
  }
  /** 石板缝（地面矩形内，种子决定错缝） */
  function pavers(x0, y0, x1, y1, step, seed, op) {
    var r = K.rng(seed || 7), d = '', st = step || 12, row = 0;
    for (var y = y0 + st; y < y1 - 1; y += st * 0.8, row++) d += K.seg(x0 + 1, y, x1 - 1, y);
    row = 0;
    for (var yy = y0; yy < y1 - 1; yy += st * 0.8, row++) {
      var off = (row % 2) * st * 0.5 + r() * 2;
      for (var x = x0 + off + st; x < x1 - 2; x += st) d += K.seg(x, yy + 0.6, x, Math.min(y1 - 0.6, yy + st * 0.8 - 0.6));
    }
    return K.ln(d, 0.6, op == null ? 0.35 : op);
  }
  /** 椰枣树：干底 x,by；高 h */
  function palm(x, by, h, seed) {
    var r = K.rng(seed || 3), tx = x + (r() - 0.5) * 6, ty = by - h, s = '';
    s += K.ellipse(x + 5, by, 6, 2, C.shadow, 0, 'stroke="none" fill-opacity="0.18"');
    s += K.path('M' + f(x - 1.6) + ' ' + f(by) + 'Q' + f(x - 1) + ' ' + f(by - h * 0.5) + ' ' + f(tx - 1) + ' ' + f(ty) +
      'L' + f(tx + 1) + ' ' + f(ty) + 'Q' + f(x + 1) + ' ' + f(by - h * 0.5) + ' ' + f(x + 1.6) + ' ' + f(by) + 'Z', C.adobe3, 1);
    var d = ''; for (var k = 1; k < 6; k++) { var yy = by - h * k / 6; d += K.seg(x - 1.4 + (tx - x) * k / 6, yy, x + 1.4 + (tx - x) * k / 6, yy - 1); }
    s += K.ln(d, 0.6, 0.6);
    for (var i = 0; i < 7; i++) {
      var a = -Math.PI + Math.PI * i / 6 + (r() - 0.5) * 0.3, L = h * (0.42 + r() * 0.12);
      var ex = tx + Math.cos(a) * L, ey = ty + Math.sin(a) * L * 0.55 + L * 0.35;
      var mx = tx + Math.cos(a) * L * 0.5, my = ty + Math.sin(a) * L * 0.5 - 2;
      s += K.path('M' + f(tx) + ' ' + f(ty) + 'Q' + f(mx) + ' ' + f(my - 2) + ' ' + f(ex) + ' ' + f(ey) + 'Q' + f(mx + 1) + ' ' + f(my + 2) + ' ' + f(tx) + ' ' + f(ty + 1.5) + 'Z', i % 2 ? C.palm : C.palm2, 0.8);
    }
    return s;
  }
  /** 柏树（园林用）：细长尖椭圆 */
  function cypress(x, by, h) {
    return K.ellipse(x + 4, by, 4.5, 1.6, C.shadow, 0, 'stroke="none" fill-opacity="0.18"') +
      K.path('M' + f(x) + ' ' + f(by - h) + 'C' + f(x + 5) + ' ' + f(by - h * 0.6) + ' ' + f(x + 5) + ' ' + f(by - 2) + ' ' + f(x) + ' ' + f(by) +
        'C' + f(x - 5) + ' ' + f(by - 2) + ' ' + f(x - 5) + ' ' + f(by - h * 0.6) + ' ' + f(x) + ' ' + f(by - h) + 'Z', C.palm, 1) +
      K.ln(K.seg(x + 1.5, by - h * 0.75, x + 2.2, by - h * 0.25), 0.7, 0.5, C.palm2);
  }
  /** 花坛（低矮灌丛块） */
  function bed(x, y, w, h, seed) {
    var r = K.rng(seed || 11), s = K.rect(x, y, w, h, C.palm2, 0.9), d = '';
    for (var i = 0; i < Math.round(w * h / 30); i++) {
      var px = x + 2 + r() * (w - 4), py = y + 2 + r() * (h - 4);
      d += 'M' + f(px - 1.5) + ' ' + f(py) + 'q1.5 -2 3 0';
    }
    s += K.ln(d, 0.6, 0.6, C.palm);
    var dots = ''; for (var j = 0; j < Math.round(w * h / 80); j++) dots += K.circle(x + 2 + r() * (w - 4), y + 2 + r() * (h - 4), 0.9, j % 2 ? C.ochre2 : C.gold, 0.3);
    return s + dots;
  }

  var G = { octPts: octPts, pool: pool, basin: basin, pavers: pavers, palm: palm, cypress: cypress, bed: bed };
  if (N) module.exports = G; else root.TownArtAS_ground = G;
})(this);
