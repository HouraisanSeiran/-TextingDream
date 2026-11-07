/*
 * 织梦 · 西式地面摆件 A：植物与石头（草丛、野花丛、灌木、三种小树、石块、水洼）
 * 每项 { kind, name, vars, top, tags, draw(ctx, v) }；top = 脚底以上最高像素（≤ 96，即上伸 ≤ 48）。
 * 局部坐标：x 0..48；y = 0 是脚底（锚点高度），向上为负。
 * 浏览器挂 window.TownArtWG_propsA；Node 用 module.exports。依赖 core.js、kit.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWG_core;
  var K = isNode ? require('./kit.js') : root.TownArtWG_kit;
  var P = C.P, f = C.f, defs = [];
  function def(o) { o.race = o.race || 'common'; defs.push(o); }

  function bushAt(c, cx, yb, rx, ry, cols) {
    cols = cols || [P.leaf, P.leaf3, P.leaf2];
    return K.foliage(c, cx, yb - ry, rx, ry, 7, cols[0], cols[1], cols[2], 1.3)[0];
  }
  function trunk(cx, yb, w, h) {
    return C.path('M' + f(cx - w / 2) + ' ' + f(yb) + 'L' + f(cx - w * 0.35) + ' ' + f(yb - h) + 'L' + f(cx + w * 0.35) + ' ' + f(yb - h) +
      'L' + f(cx + w / 2) + ' ' + f(yb) + 'Q' + f(cx) + ' ' + f(yb + 1.2) + ' ' + f(cx - w / 2) + ' ' + f(yb) + 'Z', P.timber, 1.2) +
      C.line(C.seg(cx + w * 0.15, yb - 1, cx + w * 0.1, yb - h + 2), 0.7, 0.5);
  }
  function tier(cx, yb, w, h, fill) {
    var pts = [[cx, yb - h]], i;
    for (i = 0; i <= 4; i++) pts.push([cx + w / 2 - i * w / 4, yb - (i % 2 ? 2.2 : 0)]);
    var shade = C.poly([[cx, yb - h], [cx + w / 2, yb], [cx + w * 0.12, yb - 1.4]]);
    return C.path(C.poly(pts), fill, 0) + C.path(shade, P.shadow, 0, 0.16) + C.path(C.poly(pts), 'none', 1.3) +
      C.line(C.seg(cx - w * 0.2, yb - h * 0.35, cx - w * 0.05, yb - h * 0.5), 0.7, 0.45);
  }

  def({ kind: 'grass_tuft', name: '草丛', vars: 3, top: 16, tags: ['vegetation'], draw: function (c, v) {
    var n = 2 + v, o = K.gshadow(25, -2, 7 + v * 2.5, 2.6) + C.path(C.blob(c, 24, -4, 5 + v * 2.4, 2.8, 7, 0.2), P.leaf2, 1);
    for (var i = 0; i < n; i++) {
      var x = 24 + (i - (n - 1) / 2) * 4.5 + c.rnd(-1, 1);
      o += C.tuft(c, x, -3 - c.rnd(0, 2.5), c.rnd(8, 12), c.int(5, 7), i % 2 ? P.leaf : P.leaf3, 1.1);
    }
    return o;
  } });

  def({ kind: 'flower_clump', name: '野花丛', vars: 2, top: 16, tags: ['vegetation', 'flowers'], draw: function (c, v) {
    var cols = v === 1 ? ['#b5654a', '#efdfb2'] : ['#e3c47a', '#d9cfe0'];
    var o = K.gshadow(25, -2, 12, 3) + bushAt(c, 24, -1, 11, 5.5, [P.leaf2, P.leaf, '#b6b47a']);
    for (var i = 0; i < 9; i++) {
      var x = 15 + c.rnd(0, 18), y = -3 - c.rnd(1, 8), col = cols[i % 2];
      o += C.line(C.seg(x, y + 1.5, x + c.rnd(-0.5, 0.5), y + 3.4), 0.7, 0.7, P.leaf3);
      for (var k = 0; k < 4; k++) o += C.ell(x + Math.cos(k * 1.57) * 1.3, y + Math.sin(k * 1.57) * 1, 1.2, 1, col, 0.4);
      o += C.ell(x, y, 0.6, 0.55, P.wash, 0);
    }
    return o;
  } });

  def({ kind: 'bush', name: '灌木', vars: 3, top: 28, tags: ['vegetation'], draw: function (c, v) {
    var o = K.gshadow(27, -2, 15, 3.6);
    if (v === 3) return o + bushAt(c, 17, -2, 10, 8) + bushAt(c, 30, -1, 12, 9.5);
    o += bushAt(c, 24, -1, 14, 11);
    if (v === 2) for (var i = 0; i < 6; i++) o += C.ell(15 + c.rnd(0, 18), -18 + c.rnd(0, 12), 1.3, 1.2, '#9a3b2a', 0.5);
    return o;
  } });

  def({ kind: 'tree_oak', name: '小橡树', vars: 2, top: 66, tags: ['vegetation', 'tree'], draw: function (c, v) {
    var rx = v === 1 ? 17 : 15, ry = v === 1 ? 15 : 17, cy = -20 - ry;
    var o = K.gshadow(30, -2, 17, 4) + trunk(24, -1, 6, 24);
    o += K.foliage(c, 24, cy, rx, ry, 9, P.leaf, P.leaf3, P.leaf2, 1.5)[0];
    if (v === 2) o += K.foliage(c, 17, cy + 8, 8, 6.5, 6, P.leaf, P.leaf3, P.leaf2, 1.2)[0];
    return o;
  } });

  def({ kind: 'tree_pine', name: '小松树', vars: 2, top: 72, tags: ['vegetation', 'tree', 'conifer'], draw: function (c, v) {
    var w = v === 1 ? 30 : 26, o = K.gshadow(29, -2, 13, 3.6) + trunk(24, -1, 5, 12);
    var cols = ['#76784a', '#83854f', '#8e8f58'];
    for (var i = 0; i < 3; i++) o += tier(24, -9 - i * 15, w - i * 6, 26 - i * 2, cols[i]);
    return o;
  } });

  def({ kind: 'tree_fruit', name: '小果树', vars: 2, top: 58, tags: ['vegetation', 'tree', 'orchard'], draw: function (c, v) {
    var o = K.gshadow(30, -2, 15, 3.8) + trunk(24, -1, 5, 20);
    o += C.line('M24 -18q-5 -4 -8 -9M24 -19q4 -4 7 -8', 1.6, 1, P.timber);
    o += K.foliage(c, 24, -34, 15, 12.5, 8, P.leaf2, P.leaf, '#b6b47a', 1.4)[0];
    var fruit = v === 1 ? '#b5654a' : '#e3c47a';
    for (var i = 0; i < 7; i++) o += C.ell(13 + c.rnd(0, 22), -42 + c.rnd(0, 15), 1.6, 1.5, fruit, 0.6);
    return o;
  } });

  def({ kind: 'rock', name: '石块', vars: 3, top: 20, tags: ['stone'], draw: function (c, v) {
    if (v === 1) return K.rock(c, 24, -2, 22, 15);
    if (v === 2) return K.rock(c, 19, -3, 17, 12) + K.rock(c, 32, -1, 11, 7, [P.stone2, P.stone3]);
    return K.rock(c, 16, -4, 9, 6) + K.rock(c, 29, -6, 11, 7, [P.stone2, P.stone3]) + K.rock(c, 23, -1, 8, 5) +
      C.tuft(c, 35, -1, 5, 3, P.leaf3, 0.9);
  } });

  def({ kind: 'puddle', name: '水洼', vars: 1, top: 14, tags: ['water'], draw: function (c) {
    var d = C.blob(c, 24, -7, 16, 5.5, 7, 0.14);
    return C.path(C.blob(c, 24, -7, 19, 7, 7, 0.1), '#c2ab7f', 0, 0.8) + C.path(d, P.water, 1.1) +
      C.line('M15 -8h6M26 -6h7M20 -4h4', 0.9, 0.35) + C.line('M12 -9q2 -1 4 -0.4', 0.8, 0.6, P.paper) +
      C.tuft(c, 8, -5, 5, 3, P.leaf3, 0.9) + C.tuft(c, 41, -7, 4.5, 3, P.leaf3, 0.9);
  } });

  var api = { defs: defs, bushAt: bushAt, trunk: trunk };
  root.TownArtWG_propsA = api;
  if (isNode) module.exports = api;
})(typeof window !== 'undefined' ? window : this);
