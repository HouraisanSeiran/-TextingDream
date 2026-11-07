/*
 * 织梦 · 西式种族地面摆件：精灵 elf、矮人 dwarf（每族 5 种）
 * 局部坐标：x 0..48；y = 0 是脚底（锚点高度），向上为负。top = 脚底以上最高像素。
 * 浏览器挂 window.TownArtWG_propsRace；Node 用 module.exports。依赖 core.js、kit.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWG_core;
  var K = isNode ? require('./kit.js') : root.TownArtWG_kit;
  var P = C.P, f = C.f, defs = [];
  function def(o) { defs.push(o); }
  // 精灵补色（与 west-elf/core.js 一致）
  var E = { silver: '#e8e4d4', silver2: '#d8d3c0', silver3: '#c2bca5', moss: '#a7b48a', leaf: '#7f9a5c', leaf2: '#677f4a', moon: '#cfd8d6', moon2: '#aebbb8', bark: '#6b5a44' };
  // 矮人补色（与 west-dwarf/core.js 一致）
  var W = { granite: '#9a958c', granite2: '#aba69c', granite3: '#b6b1a6', deep: '#6f6a62', copper: '#b8763a', copper2: '#9c6230', verd: '#5f8f7e', iron: '#4f4b46', ember: '#f0b04e' };

  function mushroom(x, y, s, cap) {
    return C.rect(x - s * 0.35, y - s * 1.1, s * 0.7, s * 1.1, E.silver, 0.7) +
      C.path('M' + f(x - s * 1.1) + ' ' + f(y - s) + 'Q' + f(x) + ' ' + f(y - s * 2.4) + ' ' + f(x + s * 1.1) + ' ' + f(y - s) + 'Z', cap, 0.8) +
      C.ell(x - s * 0.35, y - s * 1.45, s * 0.22, s * 0.16, E.silver, 0);
  }

  // ———————— 精灵 ————————
  def({ race: 'elf', kind: 'mushroom_ring', name: '蘑菇圈', vars: 1, top: 18, tags: ['elf', 'fairy_ring'], draw: function (c) {
    var o = C.ell(24, -9, 17, 6.5, E.moss, 0, 0.6), list = [];
    for (var i = 0; i < 9; i++) { var a = i / 9 * Math.PI * 2 + 0.2; list.push([24 + Math.cos(a) * 15, -9 + Math.sin(a) * 5.6, 2 + c.rnd(0, 1.4)]); }
    list.sort(function (p, q) { return p[1] - q[1]; });
    list.forEach(function (m, k) { o += mushroom(m[0], m[1], m[2], k % 3 ? '#b5654a' : E.moon); });
    return o;
  } });

  def({ race: 'elf', kind: 'moonstone_lamp', name: '月光石小灯', vars: 1, top: 34, tags: ['elf', 'light'], draw: function () {
    var o = K.gshadow(26, -2, 7, 2) + C.ell(24, -18, 9, 9, E.moon, 0, 0.35);
    o += C.path('M20 -1L22 -6H26L28 -1Z', E.silver2, 1) + C.path('M23 -6L23.2 -22H24.8L25 -6Z', E.silver3, 0.9);
    o += C.path('M24 -22Q18 -24 19 -29M24 -22Q30 -24 29 -29', 'none', 1).replace('fill="none"', 'fill="none"');
    o += C.path('M24 -33L27.4 -27L24 -21.6L20.6 -27Z', E.moon, 1.1) + C.path('M24 -33L27.4 -27L24 -27Z', '#eef2ee', 0);
    return o + C.line('M24 -21.6L27.4 -27', 0.6, 0.45);
  } });

  def({ race: 'elf', kind: 'flower_arch', name: '花藤拱', vars: 1, top: 46, tags: ['elf', 'arch', 'garden'], draw: function (c) {
    var o = K.gshadow(26, -2, 18, 2.4);
    o += C.line('M9 -2V-26Q9 -42 24 -42Q39 -42 39 -26V-2', 4, 1) + C.line('M9 -2V-26Q9 -42 24 -42Q39 -42 39 -26V-2', 2.4, 1, E.silver2);
    for (var i = 0; i < 16; i++) {
      var t = i / 15, a = Math.PI * (1 - t), x, y;
      if (t < 0.25) { x = 9; y = -4 - t * 4 * 22; } else if (t > 0.75) { x = 39; y = -4 - (1 - t) * 4 * 22; } else { x = 24 + Math.cos(Math.PI * (1.5 - (t - 0.25) * 2)) * 15; y = -26 - Math.abs(Math.sin(Math.PI * (t - 0.25) * 2)) * 16; }
      o += C.path(C.blob(c, x + c.rnd(-1.5, 1.5), y, 3, 2.4, 5, 0.25), i % 2 ? E.leaf : E.moss, 0.6);
      if (i % 3 === 0) o += C.ell(x + 1.2, y - 1, 1.3, 1.2, i % 2 ? '#d9cfe0' : '#efdfb2', 0.4);
      void a;
    }
    return o;
  } });

  def({ race: 'elf', kind: 'mossy_stone', name: '苔石', vars: 1, top: 22, tags: ['elf', 'stone', 'moss'], draw: function (c) {
    var o = K.rock(c, 24, -2, 24, 17, [E.silver2, E.silver3]);
    o += C.path('M14 -12Q18 -18 26 -17Q31 -18 34 -14Q28 -15 24 -13Q19 -14 14 -12Z', E.moss, 0.7);
    o += C.line('M17 -9l3 -1M27 -7l2 -2', 0.8, 0.6, E.moon2);
    return o + C.tuft(c, 10, -1, 5, 3, E.leaf2, 0.9) + C.tuft(c, 38, -1, 4, 3, E.leaf2, 0.9);
  } });

  def({ race: 'elf', kind: 'silverleaf_tree', name: '银叶小树', vars: 2, top: 66, tags: ['elf', 'tree'], draw: function (c, v) {
    var o = K.gshadow(30, -2, 15, 3.8);
    o += C.path('M21 -1Q23 -14 20 -28L24 -24L28 -30Q26 -14 27 -1Z', E.silver3, 1.2) + C.line('M23 -6Q24 -16 22 -24', 0.6, 0.5);
    var cy = v === 1 ? -42 : -40;
    o += K.foliage(c, 24, cy, v === 1 ? 14 : 16, v === 1 ? 17 : 14, 9, '#d3d4bc', '#a9ad8e', E.silver, 1.4)[0];
    for (var i = 0; i < 12; i++) o += C.line('M' + f(13 + c.rnd(0, 22)) + ' ' + f(cy - 10 + c.rnd(0, 20)) + 'l1.8 -1.8', 0.9, 0.7, E.leaf2);
    o += C.ell(19, cy - 6, 1.3, 1, E.moon, 0.5) + C.ell(29, cy + 3, 1.2, 0.9, E.moon, 0.5);
    return o;
  } });

  // ———————— 矮人 ————————
  def({ race: 'dwarf', kind: 'ore_heap', name: '矿石堆', vars: 1, top: 22, tags: ['dwarf', 'ore', 'mining'], draw: function (c) {
    var o = K.gshadow(27, -2, 18, 3.6) + C.path('M4 -1Q10 -18 24 -20Q38 -18 44 -1Q24 1 4 -1Z', W.granite, 1.4);
    for (var i = 0; i < 9; i++) {
      var x = 10 + c.rnd(0, 28), y = -3 - c.rnd(0, 13);
      o += C.path(C.poly([[x - 2.6, y], [x - 1, y - 2.4], [x + 2, y - 2], [x + 2.8, y + 0.4]]), i % 3 === 0 ? W.copper : i % 3 === 1 ? W.granite3 : W.deep, 0.6);
    }
    return o + C.path('M31 -17l2 -2l1.4 2.2l-2 1.4Z', W.verd, 0.6) + C.line('M7 -4l1 -1M41 -3l-1 -1', 0.8, 0.5);
  } });

  def({ race: 'dwarf', kind: 'minecart', name: '矿车', vars: 1, top: 26, tags: ['dwarf', 'mining', 'vehicle'], draw: function (c) {
    var o = C.line('M0 -3H48M0 -9H48', 1.6, 1, W.iron);
    for (var x = 3; x < 48; x += 8) o += C.rect(x, -10.5, 3, 9, P.dark, 0.6);
    o += K.gshadow(26, -3, 15, 2.4);
    o += C.path('M10 -22L38 -22L35 -7L13 -7Z', W.copper2, 1.3) + C.path('M10 -22L38 -22L37 -25L11 -25Z', W.iron, 1);
    o += C.line('M15 -18H33M14 -12H34', 0.8, 0.45);
    o += C.path('M13 -25Q18 -32 24 -29Q31 -33 36 -25Z', W.deep, 1) + C.ell(20, -27, 1.6, 1.2, W.copper, 0) + C.ell(29, -27.4, 1.4, 1, W.granite3, 0);
    return o + C.ell(16, -6, 3.2, 3.2, W.iron, 1) + C.ell(32, -6, 3.2, 3.2, W.iron, 1);
  } });

  def({ race: 'dwarf', kind: 'mossy_boulder', name: '苔藓巨石', vars: 1, top: 34, tags: ['dwarf', 'stone', 'moss'], draw: function (c) {
    var o = K.rock(c, 24, -2, 40, 30, [W.granite3, W.granite]);
    o += C.path('M8 -18Q16 -28 26 -27Q36 -29 42 -20Q34 -23 27 -21Q17 -24 8 -18Z', P.leaf, 0.8);
    o += C.line('M30 -14l4 4M14 -10l3 -3', 0.8, 0.5) + C.path('M20 -16l3 -2l2 2l-2 2Z', 'none', 0.6);
    return o + C.tuft(c, 5, -1, 5, 3, P.leaf3, 0.9);
  } });

  def({ race: 'dwarf', kind: 'iron_ingots', name: '铁锭垛', vars: 1, top: 22, tags: ['dwarf', 'metal', 'goods'], draw: function () {
    var o = K.gshadow(27, -2, 17, 3), rows = [[7, -2, 4], [11, -7.5, 3], [15, -13, 2]];
    rows.forEach(function (r) {
      for (var i = 0; i < r[2]; i++) {
        var x = r[0] + i * 9;
        o += C.path(C.poly([[x, r[1]], [x + 8.6, r[1]], [x + 7.6, r[1] - 5.2], [x + 1, r[1] - 5.2]]), W.iron, 0.9) +
          C.path(C.poly([[x + 1, r[1] - 5.2], [x + 7.6, r[1] - 5.2], [x + 7, r[1] - 6.6], [x + 1.6, r[1] - 6.6]]), '#6f6b64', 0.7);
      }
    });
    return o + C.line('M9 -3.4h3M20 -9h3', 0.7, 0.5, '#8d8a82');
  } });

  def({ race: 'dwarf', kind: 'ale_casks', name: '啤酒桶堆', vars: 1, top: 30, tags: ['dwarf', 'ale', 'barrel'], draw: function () {
    function cask(cx, cy, r) {
      return C.ell(cx, cy, r * 1.15, r, P.wood, 1.2) + C.ell(cx, cy, r * 0.75, r * 0.66, '#d8b77c', 0.8) +
        C.ell(cx, cy, r * 1.15, r, 'none', 0).replace('fill="none"', 'fill="none" stroke="' + W.copper2 + '" stroke-width="1.4"') +
        C.ell(cx, cy, r * 0.16, r * 0.16, P.dark, 0);
    }
    var o = K.gshadow(27, -2, 19, 3.4) + C.rect(4, -5, 40, 4, P.dark, 0.9);
    return o + cask(13, -11, 6.5) + cask(28, -11, 6.5) + cask(20.5, -22, 6.5) + C.rect(38, -14, 6, 9, P.wood, 1) + C.line('M41 -14V-5', 0.7, 0.5);
  } });

  var api = { defs: defs, E: E, W: W };
  root.TownArtWG_propsRace = api;
  if (isNode) module.exports = api;
})(typeof window !== 'undefined' ? window : this);
