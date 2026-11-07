/*
 * 织梦 · 西式地面摆件 B：货物与车具（木桶堆、木箱、干草堆、木柴堆、手推车、马车、水槽）
 * 局部坐标：x 0..48；y = 0 是脚底（锚点高度），向上为负。top = 脚底以上最高像素。
 * 浏览器挂 window.TownArtWG_propsB；Node 用 module.exports。依赖 core.js、kit.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWG_core;
  var K = isNode ? require('./kit.js') : root.TownArtWG_kit;
  var P = C.P, f = C.f, defs = [];
  function def(o) { o.race = o.race || 'common'; defs.push(o); }

  /** 车轮：正视的扁轮（3/4 俯视下轮子略压扁） */
  function wheel(cx, cy, r) {
    var sp = '';
    for (var i = 0; i < 6; i++) { var a = i * Math.PI / 3; sp += C.seg(cx, cy, cx + Math.cos(a) * r * 0.82, cy + Math.sin(a) * r * 0.82); }
    return C.ell(cx, cy, r * 0.92, r, P.timber, 1.3) + C.ell(cx, cy, r * 0.62, r * 0.68, 'none', 0.7) + C.line(sp, 0.9, 0.85, P.dark) +
      C.ell(cx, cy, r * 0.2, r * 0.2, P.iron, 0.6);
  }

  def({ kind: 'barrel_stack', name: '木桶堆', vars: 3, top: 30, tags: ['goods', 'barrel'], draw: function (c, v) {
    var o = K.gshadow(27, -2, 16, 3.6);
    if (v === 1) return o + K.barrel(17, -4, 7, 15) + K.barrel(31, -2, 7.5, 16);
    if (v === 2) return o + K.barrel(15, -6, 6.5, 14) + K.barrel(29, -7, 6.5, 14) + K.barrel(22, -1, 7, 15, P.water);
    return o + K.barrel(24, -2, 8, 17) + K.logs(6, -1, 1, 1, 3.4);
  } });

  def({ kind: 'crate', name: '木箱', vars: 3, top: 32, tags: ['goods', 'crate'], draw: function (c, v) {
    var o = K.gshadow(27, -2, 15, 3.4);
    if (v === 1) return o + K.crate(14, -2, 20);
    if (v === 2) return o + K.crate(8, -2, 17) + K.crate(25, -1, 15) + K.crate(12, -15.6, 13);
    return o + K.crate(12, -3, 16) + K.crate(27, -1, 11) +
      C.path('M30 -10q4 -6 9 -1q0 2 -4.5 2.4q-4 -0.2 -4.5 -1.4Z', P.paper, 1).replace('/>', '/>') +
      C.line('M33.5 -11.6l2.2 0.8', 1, 0.8, P.timber);
  } });

  def({ kind: 'hay_bale', name: '干草堆', vars: 2, top: 34, tags: ['farm', 'hay'], draw: function (c, v) {
    var o = K.gshadow(27, -2, 17, 3.8), d, h = '';
    if (v === 1) {
      d = 'M8 -2Q6 -18 14 -26Q24 -33 34 -26Q42 -18 40 -2Q24 1 8 -2Z';
      for (var i = 0; i < 6; i++) h += 'M' + f(12 + i * 4.6) + ' ' + f(-4 - c.rnd(0, 3)) + 'q' + f(c.rnd(-1, 1)) + ' -6 ' + f(c.rnd(-2, 2)) + ' -' + f(c.rnd(8, 13));
      return o + C.path(d, P.thatch, 1.5) + C.path('M30 -27Q41 -18 40 -2Q34 -1 30 -0.8Z', P.thatch2, 0, 0.7) +
        C.line(h, 0.8, 0.55) + C.line('M10 -14q14 4 29 0', 0.9, 0.5, P.timber);
    }
    // 方草捆两层
    o += K.box(6, 26, -2, 7, 11, P.thatch, '#dcc283') + K.box(23, 43, -1, 7, 11, P.thatch, '#dcc283') + K.box(13, 33, -14.5, 6, 10, P.thatch, '#dcc283');
    for (var j = 0; j < 5; j++) h += C.seg(8 + j * 4, -4, 8.6 + j * 4, -11) + C.seg(25 + j * 4, -3, 25.6 + j * 4, -10);
    return o + C.line(h, 0.7, 0.4) + C.line(C.seg(16, -9, 16, -2) + C.seg(33, -8, 33, -1) + C.seg(23, -21, 23, -15), 1, 0.7, P.timber);
  } });

  def({ kind: 'woodpile', name: '木柴堆', vars: 2, top: 26, tags: ['goods', 'firewood'], draw: function (c, v) {
    var o = K.gshadow(27, -2, 17, 3.4);
    if (v === 1) return o + K.logs(6, -1, 6, 3, 3.1) + K.post(4, -1, 2.4, 14) + K.post(44, -1, 2.4, 14);
    // 劈柴墩 + 斧头 + 散柴
    o += K.logs(4, -6, 4, 2, 2.8) + K.cyl(34, -2, 6.5, 2.8, 7, P.wood, '#d8b77c');
    o += C.ell(34, -9, 3.5, 1.4, 'none', 0.6) + C.line('M31 -9L38 -22', 1.6, 1, P.timber) + C.path('M36 -24l5 -1l-1.5 5Z', P.iron, 0.8);
    return o + C.path('M12 -1l9 -2.4l0.8 2.2l-9 2.2Z', P.wood, 0.9) + C.path('M22 0l7 -1.5l0.6 1.8l-7 1.4Z', P.wood, 0.9);
  } });

  def({ kind: 'handcart', name: '手推车', vars: 1, top: 24, tags: ['vehicle', 'cart'], draw: function (c) {
    var o = K.gshadow(26, -2, 18, 3.4);
    o += C.line('M30 -8L44 -2M30 -12L45 -6', 1.8, 1, P.timber);
    o += K.box(6, 32, -7, 8, 9, P.wood, P.timber) + C.line(C.seg(6, -11.5, 32, -11.5) + C.seg(19, -16, 19, -7), 0.7, 0.5);
    o += K.crate(10, -15.5, 8, 3) + C.path('M20 -16q4 -6 9 -1z', P.thatch, 1);
    return o + wheel(13, -5, 5) + C.rect(28, -7, 2, 7, P.timber, 0.8);
  } });

  def({ kind: 'wagon', name: '马车（货车）', vars: 1, top: 34, tags: ['vehicle', 'wagon'], draw: function (c) {
    var o = K.gshadow(26, -1, 22, 4);
    o += C.line('M37 -11L47 -15M37 -7L47 -11', 1.6, 1, P.timber);
    // 车厢 + 帆布篷
    o += K.box(4, 38, -7, 10, 9, P.wood, P.dark);
    o += C.path('M5 -17Q5 -33 21 -33Q37 -33 37 -17Z', P.paper, 1.4) + C.path('M27 -32Q37 -30 37 -17L29 -17Z', P.shadow, 0, 0.12);
    o += C.line('M13 -31.5V-17M21 -33V-17M29 -32V-17', 0.9, 0.5) + C.line(C.seg(4, -11.5, 38, -11.5), 0.7, 0.5);
    return o + wheel(10, -5, 5.5) + wheel(32, -5, 5.5);
  } });

  def({ kind: 'trough', name: '水槽', vars: 1, top: 16, tags: ['water', 'livestock'], draw: function (c) {
    var o = K.gshadow(26, -2, 18, 3.2);
    o += K.post(10, -1, 3, 6) + K.post(38, -1, 3, 6);
    o += K.box(6, 42, -3, 7, 7, P.wood, P.dark) + C.rect(8, -15, 32, 4.4, P.water, 0.8);
    o += C.line('M12 -13h6M24 -12.6h7', 0.8, 0.35) + C.line(C.seg(6, -6.5, 42, -6.5), 0.7, 0.5);
    return o;
  } });

  var api = { defs: defs, wheel: wheel };
  root.TownArtWG_propsB = api;
  if (isNode) module.exports = api;
})(typeof window !== 'undefined' ? window : this);
