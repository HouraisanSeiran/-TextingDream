/*
 * 织梦 · east-site-2 · 汉白玉采石场（marble / open_pit）：白色崖面、石料吊架、石雕坯。
 * 浏览器挂 window.TownArtES2_stone，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./kit.js'), require('./kit2.js'), require('./kit3.js'));
  else root.TownArtES2_stone = factory(root.TownArtES2_core, root.TownArtES2_kit, root.TownArtES2_kit2, root.TownArtES2_kit3);
})(this, function (C, K, K2, K3) {
  'use strict';
  var S = C.S, f = C.f, poly = C.poly, path = C.path, rect = C.rect, ell = C.ell, circ = C.circ, ln = C.ln;
  var G = S.ink, G2 = S.ink2, LW = S.lw, LD = S.lwd;
  var MB = '#f4f1e8', MB2 = '#dcd8cc', MB3 = '#bdb8aa';
  var defs = [];
  function def(o) { defs.push(o); }
  /** 汉白玉方料：前面 x0..x1，脚底 yb，高 h，顶深 dp。 */
  function block(x0, x1, yb, h, dp) { return K2.box(x0, x1, yb, h, dp, MB, MB2) + ln(x0 + 2, yb - h * 0.5, x1 - 3, yb - h * 0.45, MB3, 0.6, C.op(0.7)); }
  /** 石狮坯：粗凿的蹲狮轮廓（脚底中点 cx, yb，高 h）。 */
  function lionBlank(cx, yb, h) {
    var w = h * 0.7, o = C.shadowEll(cx + 3, yb, w * 0.7, 2.6);
    o += K2.box(cx - w * 0.6, cx + w * 0.6, yb, h * 0.2, 5, MB2, MB3);
    var y0 = yb - h * 0.2;
    o += path('M' + f(cx - w * 0.45) + ' ' + f(y0) + 'L' + f(cx - w * 0.5) + ' ' + f(y0 - h * 0.45) + 'Q' + f(cx - w * 0.55) + ' ' + f(y0 - h * 0.8) + ' ' + f(cx - w * 0.1) + ' ' + f(y0 - h * 0.82) +
      'Q' + f(cx + w * 0.45) + ' ' + f(y0 - h * 0.85) + ' ' + f(cx + w * 0.42) + ' ' + f(y0 - h * 0.45) + 'L' + f(cx + w * 0.45) + ' ' + f(y0) + 'Z', MB, G, LD);
    for (var i = 0; i < 5; i++) o += circ(cx - w * 0.28 + i * w * 0.14, y0 - h * 0.66 - (i % 2) * 2, 2, MB2, null, 0);
    o += ln(cx - w * 0.1, y0, cx - w * 0.1, y0 - h * 0.3, MB3, 0.9) + ln(cx + w * 0.15, y0, cx + w * 0.15, y0 - h * 0.3, MB3, 0.9);
    o += ln(cx - w * 0.3, y0 - h * 0.4, cx + w * 0.3, y0 - h * 0.42, MB3, 0.7, C.op(0.7));
    return o;
  }
  /** 三脚吊架：顶点 (x, yt)，两前腿到 yb，绳吊 load。 */
  function hoist(x, yt, yb, spread, ropeTo) {
    var o = K2.bar(x, yt, x - spread, yb, 2, S.wood) + K2.bar(x, yt, x + spread, yb, 2, S.wood);
    o += K2.bar(x, yt, x + spread * 0.25, yb - 10, 1.6, S.wood3);
    o += circ(x, yt + 3, 3, S.wood2, G, 0.8) + ln(x, yt + 3, x, ropeTo, S.wood3, 1);
    o += circ(x - spread * 0.55, yb - (yb - yt) * 0.45, 4, null, S.wood3, 1.6) + ln(x - spread * 0.55 - 4, yb - (yb - yt) * 0.45, x + spread * 0.55, yb - (yb - yt) * 0.45, S.wood3, 1);
    return o;
  }

  def(K3.speckTile({ id: 'east-common-ground-marble-chips-01', name: '汉白玉碎屑地', kind: 'ground_marble_chips', resource: 'marble', subtype: 'open_pit', v: 1,
    base: '#d9d4c4', n: 16, cols: [MB, MB2, '#c8c2b2'], specks: [S.cream2], tags: ['chips', 'quarry'] }));
  def(K3.speckTile({ id: 'east-common-ground-marble-chips-02', name: '汉白玉碎屑地 2', kind: 'ground_marble_chips', resource: 'marble', subtype: 'open_pit', v: 2,
    base: '#d9d4c4', n: 9, cols: [MB, MB3], specks: [MB], tags: ['chips', 'quarry'] }));

  def({ id: 'east-common-site-marble-quarry-01', name: '汉白玉采石场', category: 'site', kind: 'site_marble_quarry', resource: 'marble', subtype: 'open_pit', facility: null,
    w: 4, d: 3, up: 70, tags: ['quarry', 'white_cliff', 'hoist', 'carving'], roof: 'none',
    note: '白色崖面按方料凿出三级台阶，崖顶三脚吊架吊下方料，崖下方料垛与石狮坯；采石无对应 FacilityKind',
    draw: function (W, D, r, id) {
      var o = K3.cliff([[0, 56], [0, -46], [40, -64], [110, -58], [160, -68], [192, -50], [192, 56]], id + '-c', MB2, MB3, r);
      // 三级台阶采面（方格切缝）
      [[14, -30, 178, -14], [24, -2, 168, 16], [34, 28, 158, 50]].forEach(function (s, k) {
        o += rect(s[0], s[1], s[2] - s[0], s[3] - s[1], MB, G, LD) + rect(s[0], s[3] - 3, s[2] - s[0], 3, MB3, null, 0);
        for (var x = s[0] + 18 + k * 6; x < s[2]; x += 22) o += ln(x, s[1], x, s[3] - 3, MB3, 0.8);
      });
      o += K2.ladder(40, -14, 30, 7) + K2.ladder(150, 16, 54, 7);
      // 崖顶吊架吊着方料
      o += hoist(118, -70, -24, 16, -6);
      o += K2.box(110, 126, 4, 9, 4, MB, MB2) + ln(112, -5, 118, -6, S.wood3, 0.8) + ln(124, -5, 118, -6, S.wood3, 0.8);
      // 崖下：方料垛、石狮坯、凿工
      o += block(12, 44, 104, 14, 8) + block(18, 40, 90, 12, 7) + block(48, 80, 108, 13, 8);
      o += lionBlank(120, 116, 36) + lionBlank(160, 118, 30);
      o += circ(96, 96, 3.4, S.cream, G, 0.8) + rect(92, 99, 8, 10, S.navy2, G, 0.8) + K2.bar(99, 102, 106, 96, 1.2, S.gray2);
      return o;
    } });
  def({ id: 'east-common-prop-marble-blocks-01', name: '汉白玉方料垛', category: 'prop', kind: 'prop_stone_blocks', resource: 'marble', subtype: 'open_pit', facility: null,
    w: 1, d: 1, up: 8, tags: ['blocks', 'marble'],
    draw: function () {
      var o = C.shadow([[8, 40], [46, 40], [47, 45], [10, 45]]);
      return o + block(4, 26, 42, 12, 7) + block(24, 46, 42, 12, 7) + block(12, 36, 23, 11, 6);
    } });
  def({ id: 'east-common-prop-marble-lionblank-01', name: '石狮坯', category: 'prop', kind: 'prop_carving_blank', resource: 'marble', subtype: 'open_pit', facility: null,
    w: 1, d: 1, up: 14, tags: ['carving', 'lion', 'marble'],
    draw: function () { return lionBlank(24, 42, 42); } });
  def({ id: 'east-common-prop-marble-sledge-01', name: '石料拖橇', category: 'prop', kind: 'prop_stone_sledge', resource: 'marble', subtype: 'open_pit', facility: null,
    w: 1, d: 1, up: 2, tags: ['sledge', 'rollers', 'marble'],
    draw: function () {
      var o = C.shadow([[6, 40], [44, 40], [46, 45], [8, 45]]);
      o += K.log(4, 42, 41, 2.6, S.wood) + K.log(4, 42, 33, 2.6, S.wood);
      o += K2.box(8, 40, 32, 4, 12, S.wood2, S.wood3) + block(12, 36, 26, 14, 7);
      o += path('M8 30 Q2 26 0 18', null, S.wood3, 1.2);
      return o;
    } });

  var scenes = [{ key: 'marble', title: '汉白玉采石场（marble / open_pit）',
    ground: [['east-common-ground-marble-chips-01', 2, 4, 5, 2], ['east-common-ground-marble-chips-02', 1, 5, 2, 2], ['east-common-ground-marble-chips-02', 7, 4, 2, 2]],
    road: [[5, 6], [5, 7], [6, 6], [7, 6], [8, 6], [9, 6]],
    site: ['east-common-site-marble-quarry-01', 2, 2],
    props: [['east-common-prop-marble-blocks-01', 7, 3], ['east-common-prop-marble-lionblank-01', 1, 5], ['east-common-prop-marble-sledge-01', 4, 5], ['east-common-prop-marble-blocks-01', 2, 6], ['east-common-prop-marble-lionblank-01', 8, 4]] }];
  return { all: function () { return defs.map(C.make); }, scenes: scenes };
});
