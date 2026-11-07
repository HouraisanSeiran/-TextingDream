/*
 * 织梦 · east-site-2 · 矿类：稀有金属矿（rare_metals / adit 山腹平硐 + 手选矿棚）、青金石矿（lapis / open_pit 山崖露天采坑）。
 * 浏览器挂 window.TownArtES2_mine，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./kit.js'), require('./kit2.js'), require('./kit3.js'));
  else root.TownArtES2_mine = factory(root.TownArtES2_core, root.TownArtES2_kit, root.TownArtES2_kit2, root.TownArtES2_kit3);
})(this, function (C, K, K2, K3) {
  'use strict';
  var S = C.S, f = C.f, poly = C.poly, path = C.path, rect = C.rect, ell = C.ell, circ = C.circ, ln = C.ln;
  var G = S.ink, G2 = S.ink2, LW = S.lw, LD = S.lwd;
  var LAP = '#26478f', LAP2 = '#3d63b5', LAP3 = '#16305f', ORE = '#4a5866', ORE2 = '#8fa6b8';
  var defs = [];
  function def(o) { defs.push(o); }
  /** 山体背景：从左到右一道起伏的山脊，下沿 yb。 */
  function hill(id, W, yTop, yb, col, col2, r) {
    var a = [[0, yb], [0, yTop + 22]], n = 6, i;
    for (i = 1; i < n; i++) a.push([W * i / n, yTop + (i % 2 ? 0 : 14) + r() * 8]);
    a.push([W, yTop + 26], [W, yb]);
    var o = K3.cliff(a, id, col, col2, r);
    for (i = 0; i < 4; i++) o += circ(14 + r() * (W - 28), yTop + 12 + r() * 10, 4 + r() * 3, S.leaf3, G, 0.8);
    return o;
  }

  // ---------------- 稀有金属矿 ----------------
  def(K3.speckTile({ id: 'east-common-ground-raremetal-tailings-01', name: '稀有金属尾矿地', kind: 'ground_tailings', resource: 'rare_metals', v: 1,
    base: '#a39a8a', n: 16, cols: [ORE, '#8a8070', ORE2], specks: [S.gray3], tags: ['tailings', 'mine'] }));
  def(K3.speckTile({ id: 'east-common-ground-raremetal-tailings-02', name: '稀有金属尾矿地 2', kind: 'ground_tailings', resource: 'rare_metals', v: 2,
    base: '#a39a8a', n: 10, cols: ['#8a8070', ORE], specks: [ORE2, S.cream2], tags: ['tailings', 'mine'] }));

  def({ id: 'east-common-site-raremetal-adit-01', name: '稀有金属矿·山腹平硐', category: 'site', kind: 'site_mine_adit', resource: 'rare_metals', subtype: 'adit', facility: 'mine_head',
    w: 4, d: 3, up: 66, tags: ['adit', 'rails', 'hand_sorting', 'mine'], roof: 'gable_thatch',
    note: '山体正面开平硐，木框硐口挂红布符，铁轨与矿车出硐；右侧茅草手选矿棚，矿工在案上拣出银灰矿块入筐',
    draw: function (W, D, r, id) {
      var o = hill(id + '-h', W, -62, 58, '#8e8678', '#6e675c', r);
      // 平硐口：黑洞 + 木框 + 门楣
      o += path('M70 58 L70 22 Q92 6 114 22 L114 58 Z', '#1d1b20', G, LW);
      o += K.post(72, 18, 58, 5, S.wood) + K.post(112, 18, 58, 5, S.wood);
      o += rect(64, 12, 56, 7, S.wood3, G, LD) + rect(64, 12, 56, 2.4, S.wood2, null, 0);
      o += rect(86, 19, 12, 9, S.vermil, G, 0.8) + ln(89, 22, 95, 22, S.gold2, 0.8) + ln(89, 25, 95, 25, S.gold2, 0.8);
      // 硐口出来的轨道 + 矿车
      o += K3.rails(92, 56, 82, 136, 13);
      o += K3.cart(84, 102, 26, ORE, ORE2, r);
      // 左前废石堆
      o += K.heap(30, 118, 22, 7, '#8a8070', '#a39a8a', r, 12);
      // 右：手选矿棚
      var inner = rect(130, 62, 50, 9, S.wood2, G, LD) + rect(132, 71, 3, 12, S.wood3, null, 0) + rect(175, 71, 3, 12, S.wood3, null, 0);
      for (var i = 0; i < 7; i++) inner += circ(136 + i * 6.5, 61 - (i % 2) * 1.5, 2.2, i % 3 ? ORE : ORE2, G, 0.5);
      inner += circ(146, 52, 3.6, S.cream, G, 0.8) + rect(142, 55, 8, 9, S.teal, G, 0.8);
      inner += circ(166, 52, 3.6, S.cream, G, 0.8) + rect(162, 55, 8, 9, S.navy2, G, 0.8);
      o += K3.shed(id + '-s', 124, 186, 66, 94, 34, S.thatch, 'thatch', inner);
      o += K2.basket(140, 118, 13, 10, ORE2, ORE, r) + K2.basket(162, 122, 13, 10, ORE, '#8a8070', r);
      return o;
    } });
  def({ id: 'east-common-prop-raremetal-sorttable-01', name: '手选矿台', category: 'prop', kind: 'prop_sorting_table', resource: 'rare_metals', subtype: 'adit', facility: null,
    w: 1, d: 1, up: 10, tags: ['sorting', 'ore'],
    draw: function (W, D, r) {
      var o = C.shadow([[8, 40], [44, 40], [46, 45], [10, 45]]);
      o += K2.box(6, 42, 40, 10, 14, S.wood2, S.wood);
      for (var i = 0; i < 9; i++) o += circ(10 + r() * 28, 18 + r() * 9, 1.8 + r(), i % 3 ? ORE : ORE2, G, 0.5);
      o += rect(30, 18, 9, 7, S.cream2, G, 0.6);
      return o;
    } });
  def({ id: 'east-common-prop-raremetal-orecart-01', name: '稀有金属矿车', category: 'prop', kind: 'prop_ore_cart', resource: 'rare_metals', subtype: 'adit', facility: null,
    w: 1, d: 1, up: 0, tags: ['cart', 'rails'],
    draw: function (W, D, r) { return K3.rails(24, 6, 24, 46, 13) + K3.cart(24, 38, 28, ORE, ORE2, r); } });
  def({ id: 'east-common-prop-raremetal-ingots-01', name: '矿锭木箱', category: 'prop', kind: 'prop_ingot_crate', resource: 'rare_metals', subtype: 'adit', facility: null,
    w: 1, d: 1, up: 6, tags: ['ingot', 'crate'],
    draw: function () {
      var o = C.shadow([[10, 40], [42, 40], [44, 45], [12, 45]]);
      o += K2.box(8, 40, 42, 14, 12, S.wood3, S.wood);
      for (var i = 0; i < 4; i++) o += poly([[12 + i * 7, 26], [17 + i * 7, 26], [18 + i * 7, 22], [13 + i * 7, 22]], ORE2, G, 0.6);
      o += ln(10, 35, 38, 35, S.wood3, 0.8) + rect(20, 31, 12, 6, S.cream2, G, 0.6) + ln(23, 34, 29, 34, S.vermil, 0.8);
      return o;
    } });

  // ---------------- 青金石矿 ----------------
  def(K3.speckTile({ id: 'east-common-ground-lapis-rock-01', name: '青金石碎岩地', kind: 'ground_lapis_rock', resource: 'lapis', subtype: 'open_pit', v: 1,
    base: '#9b958c', n: 14, cols: ['#7d776d', LAP, '#b7b0a3'], specks: [S.gold2], tags: ['rock', 'lapis'] }));
  def(K3.speckTile({ id: 'east-common-ground-lapis-rock-02', name: '青金石碎岩地 2', kind: 'ground_lapis_rock', resource: 'lapis', subtype: 'open_pit', v: 2,
    base: '#9b958c', n: 9, cols: ['#7d776d', '#b7b0a3'], specks: [LAP2, S.gold2], tags: ['rock', 'lapis'] }));

  /** 岩面上的青金石矿脉：一道深蓝弯带 + 金色黄铁矿斑点。 */
  function vein(x1, y1, x2, y2, w, r) {
    var mx = (x1 + x2) / 2 + (r() * 10 - 5), my = (y1 + y2) / 2 + (r() * 8 - 4);
    var d = 'M' + f(x1) + ' ' + f(y1) + 'Q' + f(mx) + ' ' + f(my - w) + ' ' + f(x2) + ' ' + f(y2) + 'Q' + f(mx) + ' ' + f(my + w) + ' ' + f(x1) + ' ' + f(y1) + 'Z';
    var o = path(d, LAP, LAP3, 0.8) + path('M' + f(x1 + 3) + ' ' + f(y1) + 'Q' + f(mx) + ' ' + f(my - w * 0.4) + ' ' + f(x2 - 3) + ' ' + f(y2), null, LAP2, 1.4);
    for (var i = 0; i < 10; i++) { var t = 0.12 + r() * 0.76; o += circ(x1 + (x2 - x1) * t + (r() * 6 - 3), (y1 + y2) / 2 + ((y2 - y1) / 2) * (t * 2 - 1) + (r() * 2 - 1) * w * 0.45, 1 + r() * 0.7, S.gold2, null, 0); }
    return o;
  }
  def({ id: 'east-common-site-lapis-pit-01', name: '青金石矿·山崖露天采坑', category: 'site', kind: 'site_lapis_pit', resource: 'lapis', subtype: 'open_pit', facility: 'mine_head',
    w: 4, d: 3, up: 72, tags: ['open_pit', 'cliff', 'ore_vein', 'sorting'], roof: 'monopitch',
    note: '灰白山崖开两级台阶采面，岩面露出深蓝矿脉与金色黄铁矿斑点；崖下木梯、采坑，前方单坡棚下选矿台堆蓝色矿块；按资源点归 mine_head（露天无井架）',
    draw: function (W, D, r, id) {
      var o = K3.cliff([[0, 60], [0, -50], [36, -68], [92, -60], [148, -70], [192, -52], [192, 60]], id + '-c1', '#b7b0a3', '#8f897f', r);
      o += K3.cliff([[18, 60], [22, -8], [96, -16], [170, -6], [176, 60]], id + '-c2', '#a29b90', '#7d776d', r);
      o += rect(22, -10, 152, 4, '#cfc9bd', null, 0);
      o += vein(24, -46, 92, -30, 9, r) + vein(104, -60, 176, -38, 8, r) + vein(70, -40, 118, -22, 5, r);
      o += vein(30, 10, 104, 30, 10, r) + vein(116, 0, 168, 20, 8, r) + vein(84, 20, 120, 40, 5, r);
      o += K2.ladder(108, -12, 50, 8);
      // 崖脚采坑
      o += K2.pit(36, 50, 100, 74, 8, '#7d776d', '#8f897f');
      o += K.heap(68, 66, 12, 3, LAP, '#7d776d', r, 6);
      // 前方单坡选矿棚
      var inner = rect(126, 82, 52, 9, S.wood2, G, LD);
      for (var i = 0; i < 9; i++) inner += poly([[130 + i * 5.4, 81], [132 + i * 5.4, 77 - (i % 2) * 2], [135 + i * 5.4, 78], [135 + i * 5.4, 81]], i % 3 ? LAP : LAP2, G, 0.5);
      inner += circ(150, 70, 3.6, S.cream, G, 0.8) + rect(146, 73, 8, 9, S.teal, G, 0.8);
      o += K3.shed(id + '-s', 120, 184, 84, 112, 32, S.gray2, 'tile', inner);
      o += K.heap(40, 120, 16, 4, LAP, LAP2, r, 10);
      o += K2.basket(84, 128, 13, 10, LAP2, LAP, r);
      return o;
    } });
  def({ id: 'east-common-prop-lapis-oreheap-01', name: '青金石矿块堆', category: 'prop', kind: 'prop_ore_heap', resource: 'lapis', subtype: 'open_pit', facility: null,
    w: 1, d: 1, up: 4, tags: ['ore', 'lapis'],
    draw: function (W, D, r) {
      var o = C.shadowEll(26, 42, 18, 3) + K.heap(24, 40, 18, 6, LAP, LAP2, r, 12);
      for (var i = 0; i < 6; i++) o += circ(12 + r() * 24, 26 + r() * 12, 0.9, S.gold2, null, 0);
      return o;
    } });
  def({ id: 'east-common-prop-lapis-sorttable-01', name: '青金石选矿台', category: 'prop', kind: 'prop_sorting_table', resource: 'lapis', subtype: 'open_pit', facility: null,
    w: 1, d: 1, up: 12, tags: ['sorting', 'lapis'],
    draw: function (W, D, r) {
      var o = C.shadow([[8, 40], [44, 40], [46, 45], [10, 45]]);
      o += K2.box(6, 42, 40, 10, 14, S.wood2, S.wood);
      for (var i = 0; i < 8; i++) { var x = 10 + i * 3.6, y = 22 + (i % 3) * 2.5; o += poly([[x, y], [x + 2, y - 3.5], [x + 4.5, y - 2], [x + 4, y + 1]], i % 2 ? LAP : LAP2, G, 0.5); }
      o += K2.basket(36, 32, 9, 7, LAP2, LAP, r);
      return o;
    } });
  def({ id: 'east-common-prop-lapis-chisels-01', name: '凿钎与矿篓', category: 'prop', kind: 'prop_mining_tools', resource: 'lapis', subtype: 'open_pit', facility: null,
    w: 1, d: 1, up: 14, tags: ['tools', 'lapis'],
    draw: function (W, D, r) {
      var o = K2.bar(8, 42, 24, 4, 1.6, S.wood3) + K2.bar(14, 44, 30, 8, 1.6, S.gray2);
      o += poly([[22, 2], [27, 6], [25, 9]], S.gray, G, 0.7);
      o += K2.basket(34, 44, 14, 12, LAP, LAP2, r);
      return o;
    } });

  var scenes = [
    { key: 'rare_metals', title: '稀有金属矿（rare_metals / adit）',
      ground: [['east-common-ground-raremetal-tailings-01', 2, 4, 3, 2], ['east-common-ground-raremetal-tailings-02', 5, 4, 2, 2], ['east-common-ground-raremetal-tailings-02', 1, 6, 2, 1]],
      road: [[3, 4], [3, 5], [3, 6], [3, 7]],
      site: ['east-common-site-raremetal-adit-01', 2, 1],
      props: [['east-common-prop-raremetal-sorttable-01', 6, 4], ['east-common-prop-raremetal-orecart-01', 2, 5], ['east-common-prop-raremetal-ingots-01', 7, 5], ['east-common-prop-raremetal-ingots-01', 5, 6]] },
    { key: 'lapis', title: '青金石矿（lapis / open_pit）',
      ground: [['east-common-ground-lapis-rock-01', 2, 2, 5, 3], ['east-common-ground-lapis-rock-02', 2, 5, 4, 1], ['east-common-ground-lapis-rock-02', 7, 3, 1, 2]],
      road: [[4, 5], [4, 6], [4, 7]],
      site: ['east-common-site-lapis-pit-01', 3, 2],
      props: [['east-common-prop-lapis-oreheap-01', 2, 4], ['east-common-prop-lapis-sorttable-01', 7, 4], ['east-common-prop-lapis-chisels-01', 2, 3], ['east-common-prop-lapis-oreheap-01', 5, 5]] }
  ];
  return { all: function () { return defs.map(C.make); }, scenes: scenes };
});
