/*
 * 织梦 · 西式种族地面摆件：兽人 orc（骨堆、小图腾、篝火坑、尖桩、兽皮晾架）
 * 局部坐标：x 0..48；y = 0 是脚底（锚点高度），向上为负。top = 脚底以上最高像素。
 * 浏览器挂 window.TownArtWG_propsOrc；Node 用 module.exports。依赖 core.js、kit.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWG_core;
  var K = isNode ? require('./kit.js') : root.TownArtWG_kit;
  var P = C.P, f = C.f, defs = [];
  function def(o) { o.race = 'orc'; defs.push(o); }
  // 兽人补色（与 west-orc/core.js 一致）
  var O = { hide: '#9b7550', hide2: '#6e4e33', hide3: '#b48f66', bone: '#e6dcc2', bone2: '#cbbf9f', rust: '#8f3a26', moss: '#6f7a4a', iron: '#6a6660', fire: '#d9893a', fire2: '#efc463', hole: '#3b2d1f' };

  /** 一根骨头：两端圆头 */
  function bone(x1, y1, x2, y2, w) {
    var dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy) || 1, nx = -dy / L * w * 0.5, ny = dx / L * w * 0.5;
    var shaft = C.poly([[x1 + nx, y1 + ny], [x2 + nx, y2 + ny], [x2 - nx, y2 - ny], [x1 - nx, y1 - ny]]);
    var knob = function (x, y) { return C.ell(x + nx * 0.9, y + ny * 0.9, w * 0.62, w * 0.62, O.bone, 0.8) + C.ell(x - nx * 0.9, y - ny * 0.9, w * 0.62, w * 0.62, O.bone, 0.8); };
    return knob(x1, y1) + knob(x2, y2) + C.path(shaft, O.bone, 0) + C.line(C.seg(x1 + nx, y1 + ny, x2 + nx, y2 + ny) + C.seg(x1 - nx, y1 - ny, x2 - nx, y2 - ny), 0.8, 0.9);
  }
  function skull(cx, cy, s) {
    return C.path('M' + f(cx - s) + ' ' + f(cy) + 'Q' + f(cx - s) + ' ' + f(cy - s * 1.5) + ' ' + f(cx) + ' ' + f(cy - s * 1.5) + 'Q' + f(cx + s) + ' ' + f(cy - s * 1.5) + ' ' + f(cx + s) + ' ' + f(cy) +
      'L' + f(cx + s * 0.6) + ' ' + f(cy + s * 0.6) + 'H' + f(cx - s * 0.6) + 'Z', O.bone, 1) +
      C.ell(cx - s * 0.42, cy - s * 0.4, s * 0.28, s * 0.3, O.hole, 0) + C.ell(cx + s * 0.42, cy - s * 0.4, s * 0.28, s * 0.3, O.hole, 0) +
      C.line(C.seg(cx - s * 0.2, cy + s * 0.2, cx - s * 0.2, cy + s * 0.55) + C.seg(cx + s * 0.2, cy + s * 0.2, cx + s * 0.2, cy + s * 0.55), 0.6, 0.7);
  }

  def({ kind: 'bone_pile', name: '骨堆', vars: 1, top: 18, tags: ['orc', 'bones'], draw: function () {
    var o = K.gshadow(26, -2, 17, 3) + C.path('M6 -1Q14 -10 24 -10Q36 -10 42 -1Q24 1 6 -1Z', O.bone2, 1);
    o += bone(9, -4, 25, -8, 2.6) + bone(22, -3, 39, -6, 2.6) + bone(16, -11, 30, -12, 2.2);
    return o + skull(31, -11, 4.2) + C.line('M11 -1l3 -1M36 -1l2 -1', 0.7, 0.5);
  } });

  def({ kind: 'totem_small', name: '小图腾', vars: 1, top: 46, tags: ['orc', 'totem', 'shrine'], draw: function () {
    var o = K.gshadow(27, -2, 10, 2.6) + C.path('M16 -1Q18 -6 24 -6Q30 -6 32 -1Q24 1 16 -1Z', P.stone2, 1);
    o += C.rect(20, -36, 8, 32, O.hide2, 1.3) + C.line('M21 -30h6M21 -20h6', 0.8, 0.6, O.bone2);
    o += C.path('M20 -28L14 -31L20 -24ZM28 -28L34 -31L28 -24Z', O.rust, 1);
    o += C.rect(21.5, -27, 2, 2, O.fire2, 0) + C.rect(24.5, -27, 2, 2, O.fire2, 0);
    o += skull(24, -37, 5) + C.path('M19 -40Q13 -42 12 -47Q17 -45 20 -43ZM29 -40Q35 -42 36 -47Q31 -45 28 -43Z', O.bone, 0.9);
    return o + C.line('M22 -14l2 3l2 -3', 0.9, 0.8, O.bone);
  } });

  def({ kind: 'fire_pit', name: '篝火坑', vars: 1, top: 26, tags: ['orc', 'fire'], draw: function () {
    var o = K.gshadow(26, -3, 17, 3) + C.ell(24, -7, 16, 6, P.soil2, 1.1) + C.ell(24, -7.6, 11, 4, O.hole, 0);
    for (var i = 0; i < 10; i++) { var a = i / 10 * Math.PI * 2; if (Math.sin(a) < -0.2) o += C.ell(24 + Math.cos(a) * 14, -7 + Math.sin(a) * 5, 2.6, 1.8, i % 2 ? P.stone3 : O.iron, 0.8); }
    o += C.line('M15 -7L33 -11M15 -11L33 -6', 2.8, 1, O.hide2);
    o += C.path('M17 -8Q16 -16 21 -24Q22 -17 25 -20Q30 -14 31 -8Z', O.fire, 1) + C.path('M20.4 -8.6Q20.6 -13 23.2 -17Q25 -12 27.4 -8.6Z', O.fire2, 0);
    for (var j = 0; j < 10; j++) { var b = j / 10 * Math.PI * 2; if (Math.sin(b) >= -0.2) o += C.ell(24 + Math.cos(b) * 14, -7 + Math.sin(b) * 5, 2.6, 1.8, j % 2 ? P.stone3 : O.iron, 0.8); }
    return o;
  } });

  def({ kind: 'stake_row', name: '尖桩', vars: 1, top: 34, tags: ['orc', 'defense', 'stakes'], draw: function () {
    var o = C.path('M2 -6H46V-2H2Z', P.shadow, 0, 0.16) + C.line('M3 -10H45', 2.6, 1) + C.line('M3 -10H45', 1.4, 1, O.hide);
    [[6, 26, -0.18], [15, 30, 0.1], [24, 27, -0.05], [33, 31, 0.15], [42, 25, -0.1]].forEach(function (s) {
      var x = s[0], h = s[1], lean = s[2] * h, w = 3.4;
      o += C.path(C.poly([[x - w, -3], [x - w + lean, -h + 6], [x + lean, -h], [x + w + lean, -h + 6], [x + w, -3]]), O.hide3, 1.2) +
        C.path(C.poly([[x + lean * 0.3, -3], [x + lean, -h + 6], [x + w + lean, -h + 6], [x + w, -3]]), P.shadow, 0, 0.16) +
        C.line(C.seg(x - w + lean, -h + 6, x + w + lean, -h + 6), 0.7, 0.5);
    });
    return o + C.path('M36 -24l2 -3l2 3Z', O.rust, 0.6);
  } });

  def({ kind: 'hide_rack', name: '兽皮晾架', vars: 1, top: 42, tags: ['orc', 'tannery', 'hide'], draw: function () {
    var o = K.gshadow(26, -3, 19, 2.6) + K.post(7, -2, 3, 36, O.hide2, O.hide) + K.post(41, -2, 3, 36, O.hide2, O.hide);
    o += C.line('M5 -36L43 -36', 2.6, 1) + C.line('M5 -36L43 -36', 1.4, 1, O.hide);
    o += C.path('M11 -35Q9 -26 12 -16Q16 -13 22 -16Q24 -24 22 -35Z', O.hide, 1.1) + C.line('M13 -30q4 2 7 0M13 -24q4 2 7 0', 0.7, 0.45);
    o += C.path('M26 -35L38 -35Q40 -26 36 -18L33 -12L30 -18Q25 -26 26 -35Z', O.hide3, 1.1) + C.ell(32, -26, 2, 1.6, O.hide2, 0);
    return o + C.line('M16.5 -35v-2M32 -35v-2', 1, 0.9, O.bone2) + K.cyl(18, -2, 4, 1.6, 5, O.hide2, O.hide);
  } });

  var api = { defs: defs, O: O, bone: bone, skull: skull };
  root.TownArtWG_propsOrc = api;
  if (isNode) module.exports = api;
})(typeof window !== 'undefined' ? window : this);
