/*
 * 织梦 · 西式地面摆件 C：院落小件（木栅栏横/竖/转角、菜畦、晾衣绳、鸡群、路标、长凳、花坛、井台小件、篝火堆）
 * 栅栏可首尾相接：横段沿 y=-16 贯穿 x 0..48；竖段沿 x=24 贯穿 y -48..0；转角 = 东段 + 南段。
 * 局部坐标：x 0..48；y = 0 是脚底（锚点高度），向上为负。
 * 浏览器挂 window.TownArtWG_propsC；Node 用 module.exports。依赖 core.js、kit.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWG_core;
  var K = isNode ? require('./kit.js') : root.TownArtWG_kit;
  var P = C.P, f = C.f, defs = [];
  function def(o) { o.race = o.race || 'common'; defs.push(o); }
  var FY = -16, FH = 11; // 横栅栏基线与柱高

  function hRun(x0, x1) {
    var o = C.path(C.poly([[x0, FY + 0.5], [x1, FY + 0.5], [x1, FY + 2.6], [x0, FY + 2.6]]), P.shadow, 0, 0.16);
    o += C.line(C.seg(x0, FY - FH + 3, x1, FY - FH + 3), 3, 1) + C.line(C.seg(x0, FY - FH + 3, x1, FY - FH + 3), 1.8, 1, P.wood);
    o += C.line(C.seg(x0, FY - 3.5, x1, FY - 3.5), 3, 1) + C.line(C.seg(x0, FY - 3.5, x1, FY - 3.5), 1.8, 1, P.wood);
    for (var x = x0 + 6; x < x1; x += 12) o += K.post(x, FY, 3, FH, P.timber, P.wood);
    return o;
  }
  function vRun(y0, y1) {
    var o = C.path(C.poly([[25.5, y0], [28, y0], [28, y1], [25.5, y1]]), P.shadow, 0, 0.16), posts = '';
    o += C.line(C.seg(23, y0 - 8, 23, y1 - 8), 2.8, 1) + C.line(C.seg(23, y0 - 8, 23, y1 - 8), 1.6, 1, P.wood);
    o += C.line(C.seg(25, y0 - 3, 25, y1 - 3), 2.8, 1) + C.line(C.seg(25, y0 - 3, 25, y1 - 3), 1.6, 1, P.wood);
    for (var y = y0 + 6; y < y1; y += 12) posts += K.post(24, y, 3, FH - 1, P.timber, P.wood);
    return o + posts;
  }

  def({ kind: 'fence_h', name: '木栅栏·横段', vars: 1, top: 28, tags: ['fence', 'tileable_ew'], draw: function () { return hRun(0, 48); } });
  def({ kind: 'fence_v', name: '木栅栏·竖段', vars: 1, top: 58, tags: ['fence', 'tileable_ns'], draw: function () { return vRun(-48, 0); } });
  def({ kind: 'fence_corner', name: '木栅栏·转角', vars: 1, top: 28, tags: ['fence', 'corner_es'], draw: function () {
    return vRun(FY, 0) + hRun(24, 48) + K.post(24, FY, 3.4, FH + 1, P.timber, P.wood);
  } });

  def({ kind: 'vegetable_bed', name: '菜畦', vars: 1, top: 40, tags: ['farm', 'garden'], draw: function (c) {
    var o = C.path(C.poly([[4, -38], [44, -38], [46, -2], [2, -2]]), P.soil, 1.2);
    for (var r = 0; r < 4; r++) {
      var y = -33 + r * 9;
      o += C.line('M' + f(5 - r * 0.5) + ' ' + f(y + 3) + 'H' + f(43 + r * 0.5), 2.2, 0.3, P.soil2);
      for (var x = 9; x < 42; x += 6.5) o += C.path(C.blob(c, x + c.rnd(-0.8, 0.8), y, 2.6, 1.9, 5, 0.2), r % 2 ? P.leaf2 : P.leaf, 0.6);
    }
    return o + C.line('M4 -38L2 -2', 0.8, 0.5);
  } });

  def({ kind: 'clothesline', name: '晾衣绳', vars: 1, top: 34, tags: ['yard', 'laundry'], draw: function () {
    var o = K.gshadow(26, -6, 18, 2.4) + K.post(6, -6, 2.4, 26) + K.post(42, -6, 2.4, 26);
    o += C.line('M6 -30Q24 -25 42 -30', 0.8, 0.9);
    o += C.path('M11 -28.4h8l-0.6 10h-7Z', P.paper, 0.9) + C.path('M22 -27.4h7l0.4 7.6l-3.8 -1.8l-3.6 1.6Z', '#b5654a', 0.9) +
      C.path('M32 -28h6l-0.4 12h-5.2Z', '#d9cfe0', 0.9);
    return o + C.line('M12.5 -24h5M33 -22h4', 0.6, 0.4);
  } });

  def({ kind: 'chickens', name: '鸡群', vars: 1, top: 14, tags: ['livestock', 'farm'], draw: function (c) {
    var o = '';
    [[14, -8, 1], [27, -4, -1], [36, -11, 1], [20, -15, -1]].forEach(function (h, i) {
      var x = h[0], y = h[1], s = h[2], col = i === 2 ? P.wood : P.paper;
      o += C.ell(x + 1, y + 0.4, 4, 1.2, P.shadow, 0, 0.18) +
        C.path('M' + f(x - 4 * s) + ' ' + f(y - 3) + 'q' + f(-1.5 * s) + ' -3.5 ' + f(-0.5 * s) + ' -5q' + f(2.5 * s) + ' 1 ' + f(2 * s) + ' 3Z', P.dark, 0.6) +
        C.ell(x, y - 2.6, 4.2, 2.8, col, 0.9) + C.ell(x + 3.4 * s, y - 5.4, 1.8, 1.8, col, 0.9) +
        C.path('M' + f(x + 5 * s) + ' ' + f(y - 5.6) + 'l' + f(1.6 * s) + ' 0.6l' + f(-1.6 * s) + ' 0.5Z', P.wash, 0) +
        C.ell(x + 3.4 * s, y - 7.2, 0.9, 0.8, P.red, 0) +
        C.line(C.seg(x - 0.6, y, x - 0.6, y - 0.6) + C.seg(x + 1, y, x + 1, y - 0.6), 0.7, 0.9, P.dark);
    });
    return o + C.line('M30 -14l1 0.4M8 -3l0.8 0.3M42 -6l0.8 -0.2', 0.8, 0.6, P.wash);
  } });

  def({ kind: 'signpost', name: '路标', vars: 1, top: 40, tags: ['road', 'sign'], draw: function () {
    var o = K.gshadow(27, -2, 6, 2) + K.post(24, -1, 3.4, 36);
    o += C.path('M25 -34h13l4 3l-4 3H25Z', P.wood, 1.1) + C.path('M23 -25h-13l-4 3l4 3h13Z', '#d8b77c', 1.1);
    return o + C.line('M28 -31h8M10 -22h9', 0.8, 0.55);
  } });

  def({ kind: 'bench', name: '长凳', vars: 1, top: 16, tags: ['plaza', 'seat'], draw: function () {
    var o = K.gshadow(26, -2, 17, 2.6);
    o += C.rect(9, -9, 3, 7, P.dark, 0.9) + C.rect(36, -9, 3, 7, P.dark, 0.9);
    o += K.box(6, 42, -8, 4, 2.6, P.wood, '#d8b77c', 1.1) + C.line('M7 -12h34', 0.6, 0.5);
    return o;
  } });

  def({ kind: 'flower_bed', name: '花坛', vars: 1, top: 22, tags: ['plaza', 'flowers'], draw: function (c) {
    var o = K.gshadow(26, -2, 18, 3) + K.box(6, 42, -2, 12, 6, P.stone2, P.soil, 1.2);
    o += C.line('M12 -8V-2M20 -8V-2M28 -8V-2M36 -8V-2', 0.7, 0.45);
    for (var i = 0; i < 10; i++) {
      var x = 10 + c.rnd(0, 28), y = -10 - c.rnd(0, 8);
      o += C.path(C.blob(c, x, y, 2.4, 1.8, 5, 0.2), P.leaf, 0.5) + C.ell(x + c.rnd(-0.6, 0.6), y - 1.2, 1.2, 1, ['#b5654a', '#e3c47a', '#efdfb2'][i % 3], 0.4);
    }
    return o;
  } });

  def({ kind: 'well_bits', name: '井台小件（水桶与辘轳绳）', vars: 1, top: 18, tags: ['water', 'well'], draw: function () {
    var o = K.gshadow(26, -2, 16, 2.8) + C.path(C.poly([[6, -10], [42, -10], [44, -1], [4, -1]]), P.stone, 1);
    o += C.line('M17 -10l-1 9M30 -10l1 9M4.6 -5h39', 0.7, 0.4);
    o += K.cyl(16, -4, 5, 2, 8, P.wood, P.water) + C.line('M11 -12q5 -6 10 0', 0.9, 0.9, P.iron);
    return o + K.cyl(31, -3, 4.2, 1.7, 6, P.wood, P.timber) + C.line('M36 -4q4 -3 2 -6q-3 -2 -1 -4', 0.8, 0.8, P.timber);
  } });

  def({ kind: 'campfire', name: '篝火堆', vars: 1, top: 24, tags: ['fire'], draw: function () {
    var o = K.gshadow(26, -3, 13, 2.6), st = '';
    for (var i = 0; i < 8; i++) { var a = i / 8 * Math.PI * 2; st += C.ell(24 + Math.cos(a) * 9, -6 + Math.sin(a) * 3.6, 2.4, 1.6, i % 2 ? P.stone2 : P.stone, 0.8); }
    o += C.ell(24, -6, 8, 3, P.dark, 0) + st.slice(0, st.length);
    o += C.line('M18 -6L30 -10M18 -10L30 -5', 2.6, 1, P.timber);
    o += C.path('M20 -8Q19 -14 23 -21Q24 -15 26 -17Q29 -13 27 -8Z', P.fire, 1) + C.path('M22.4 -8.5Q22 -12 24 -15Q25.6 -12 25.4 -8.5Z', P.glow, 0);
    return o + C.line('M26 -24q2 -3 0 -6M23 -26q-2 -2 0 -5', 0.8, 0.35);
  } });

  var api = { defs: defs };
  root.TownArtWG_propsC = api;
  if (isNode) module.exports = api;
})(typeof window !== 'undefined' ? window : this);
