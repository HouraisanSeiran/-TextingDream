/*
 * 织梦 · east-site-2 · 作坊类：牙行作坊（ivory：象牙仓 + 牙雕作坊，不画猎杀）、琥珀坑（amber：林间挖掘坑 + 筛料台）。
 * 浏览器挂 window.TownArtES2_craft，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./kit.js'), require('./kit2.js'), require('./kit3.js'));
  else root.TownArtES2_craft = factory(root.TownArtES2_core, root.TownArtES2_kit, root.TownArtES2_kit2, root.TownArtES2_kit3);
})(this, function (C, K, K2, K3) {
  'use strict';
  var S = C.S, f = C.f, poly = C.poly, path = C.path, rect = C.rect, ell = C.ell, circ = C.circ, ln = C.ln;
  var G = S.ink, G2 = S.ink2, LW = S.lw, LD = S.lwd;
  var IV = '#f6ecd2', IV2 = '#e3d2ab', AM = '#e8902a', AM2 = '#f4b64a', AM3 = '#b5601c';
  var defs = [];
  function def(o) { defs.push(o); }
  /** 一根象牙（弯弧，粗端在 x1）。 */
  function tusk(x1, y1, x2, y2, w, bend) {
    var mx = (x1 + x2) / 2, my = (y1 + y2) / 2 - (bend == null ? 6 : bend);
    var d = 'M' + f(x1) + ' ' + f(y1 - w / 2) + 'Q' + f(mx) + ' ' + f(my - w * 0.3) + ' ' + f(x2) + ' ' + f(y2) + 'Q' + f(mx) + ' ' + f(my + w * 0.6) + ' ' + f(x1) + ' ' + f(y1 + w / 2) + 'Z';
    return path(d, IV, G, 0.8) + ell(x1, y1, 1.4, w / 2, IV2, G, 0.6);
  }
  /** 小瓦房作坊（敞开前檐）：x0..x1，后墙 yBack，前沿 yb。 */
  function workshop(id, x0, x1, yBack, yb, h, inner) { return K3.shed(id, x0, x1, yBack, yb, h, S.navy2, 'tile', inner, S.cream2); }

  // ---------------- 牙行作坊 ----------------
  def({ id: 'east-common-site-ivory-workshop-01', name: '牙行·象牙仓与牙雕作坊', category: 'site', kind: 'site_ivory_workshop', resource: 'ivory', subtype: 'carving_workshop', facility: 'warehouse',
    w: 4, d: 3, up: 60, tags: ['ivory', 'warehouse', 'carving', 'trade_house'], roof: 'gable_tile',
    note: '左为带锁的青瓦象牙仓（库门旁立牙行招牌），右为敞檐牙雕作坊，案上雕牙球与牙梳；只画成品与原料，不画猎杀。主体按仓储归 warehouse',
    draw: function (W, D, r, id) {
      var o = K2.pad(4, 6, W - 4, D - 4, S.earth, 0.45);
      // 左：象牙仓（封闭砖仓 + 锁门）
      o += C.shadow([[92, 0], [100, 4], [100, 66], [92, 62]]);
      o += rect(10, 0, 82, 62, S.cream, G, LD) + rect(10, 50, 82, 12, S.gray2, G, LD);
      o += rect(38, 18, 26, 44, S.vermil, G, LD) + ln(51, 18, 51, 62, G2, 0.8) + rect(47, 36, 8, 5, S.gold2, G, 0.6);
      [22, 80].forEach(function (x) { o += rect(x - 6, 16, 12, 10, S.navy, G, 0.8) + ln(x, 16, x, 26, G2, 0.6) + ln(x - 6, 21, x + 6, 21, G2, 0.6); });
      o += K.roof(id + '-a', 10, 92, -26, 1, 5, S.navy, 'tile', 5);
      o += rect(68, 24, 9, 26, S.brown, G, 0.8) + ln(70, 28, 75, 28, S.gold2, 0.8) + ln(70, 34, 75, 34, S.gold2, 0.8) + ln(70, 40, 75, 40, S.gold2, 0.8);
      // 右：牙雕作坊
      var inner = circ(132, 56, 3.6, S.cream, G, 0.8) + rect(128, 59, 8, 9, S.navy2, G, 0.8);
      inner += circ(160, 56, 3.6, S.cream, G, 0.8) + rect(156, 59, 8, 9, S.teal, G, 0.8);
      inner += rect(110, 68, 66, 8, S.wood2, G, LD) + rect(112, 76, 3, 6, S.wood3, null, 0) + rect(171, 76, 3, 6, S.wood3, null, 0);
      inner += circ(122, 64, 4, IV, G, 0.7) + circ(122, 64, 2, null, IV2, 0.6) + rect(134, 62, 12, 5, IV, G, 0.6);
      for (var i = 0; i < 5; i++) inner += ln(135 + i * 2.4, 67, 135 + i * 2.4, 70, IV2, 0.6);
      inner += tusk(150, 66, 174, 62, 3.4, 3);
      o += workshop(id + '-w', 104, 184, 52, 82, 36, inner);
      // 前：象牙原料架（交叉木架上横放两根）+ 货箱
      o += K.post(28, 92, 120, 2.6) + K.post(76, 92, 120, 2.6) + ln(26, 100, 78, 100, S.wood3, 2);
      o += tusk(30, 99, 76, 96, 5, 7) + tusk(32, 108, 74, 106, 4.5, 6);
      o += K2.box(116, 150, 132, 12, 10, S.wood2, S.wood) + rect(126, 122, 14, 6, S.cream2, G, 0.6) + ln(129, 125, 137, 125, S.vermil, 0.8);
      o += K2.box(154, 180, 130, 10, 8, S.wood2, S.wood);
      return o;
    } });
  def({ id: 'east-common-prop-ivory-tuskrack-01', name: '象牙原料架', category: 'prop', kind: 'prop_tusk_rack', resource: 'ivory', subtype: 'carving_workshop', facility: null,
    w: 1, d: 1, up: 10, tags: ['ivory', 'rack'],
    draw: function () {
      var o = C.shadow([[6, 40], [44, 40], [46, 45], [8, 45]]);
      o += K.post(8, 14, 42, 2.4) + K.post(40, 14, 42, 2.4) + ln(6, 20, 42, 20, S.wood3, 2) + ln(6, 32, 42, 32, S.wood3, 2);
      return o + tusk(6, 18, 44, 14, 4.6, 6) + tusk(8, 30, 42, 27, 4, 5);
    } });
  def({ id: 'east-common-prop-ivory-carvingbench-01', name: '牙雕案', category: 'prop', kind: 'prop_carving_bench', resource: 'ivory', subtype: 'carving_workshop', facility: null,
    w: 1, d: 1, up: 8, tags: ['ivory', 'carving', 'bench'],
    draw: function () {
      var o = C.shadow([[8, 40], [44, 40], [46, 45], [10, 45]]);
      o += K2.box(6, 42, 40, 10, 14, S.wood2, S.wood);
      o += circ(14, 22, 4, IV, G, 0.7) + circ(14, 22, 2, null, IV2, 0.6);
      o += rect(22, 19, 10, 6, IV, G, 0.6) + poly([[34, 26], [38, 16], [41, 26]], IV, G, 0.6);
      o += ln(30, 28, 38, 30, S.gray, 1.2) + ln(10, 28, 18, 29, S.gray2, 1);
      return o;
    } });
  def({ id: 'east-common-prop-ivory-crates-01', name: '牙行货箱', category: 'prop', kind: 'prop_trade_crates', resource: 'ivory', subtype: 'carving_workshop', facility: null,
    w: 1, d: 1, up: 12, tags: ['crate', 'trade'],
    draw: function () {
      var o = C.shadow([[8, 40], [46, 40], [47, 45], [10, 45]]);
      o += K2.box(4, 28, 42, 14, 8, S.wood2, S.wood) + K2.box(26, 46, 42, 12, 8, S.wood2, S.wood3) + K2.box(10, 32, 20, 12, 7, S.wood2, S.wood);
      o += rect(12, 31, 10, 6, S.cream2, G, 0.6) + ln(14, 34, 20, 34, S.vermil, 0.8) + rect(15, 10, 8, 5, S.vermil, G, 0.5);
      return o;
    } });

  // ---------------- 琥珀坑 ----------------
  def(K3.speckTile({ id: 'east-common-ground-amber-forestfloor-01', name: '林下腐殖土', kind: 'ground_forest_floor', resource: 'amber', subtype: 'forest_dig', v: 1,
    base: '#9c7a4c', n: 12, cols: [S.leaf3, '#7d5e36', S.ochre], specks: [AM2], tags: ['forest', 'humus'] }));
  def(K3.speckTile({ id: 'east-common-ground-amber-forestfloor-02', name: '林下腐殖土 2', kind: 'ground_forest_floor', resource: 'amber', subtype: 'forest_dig', v: 2,
    base: '#9c7a4c', n: 9, cols: [S.leaf, '#7d5e36', S.leaf3], specks: [S.cream2], tags: ['forest', 'humus'] }));

  /** 一个筛料台：竹框筛子架在两条腿上，筛面上有琥珀粒。 */
  function sieve(cx, yb, w, r) {
    var o = C.shadowEll(cx + 2, yb, w * 0.6, 2.4);
    o += K2.bar(cx - w * 0.4, yb, cx - w * 0.3, yb - 14, 1.4, S.wood3) + K2.bar(cx + w * 0.4, yb, cx + w * 0.3, yb - 14, 1.4, S.wood3);
    o += ell(cx, yb - 15, w / 2, w * 0.18, S.thatch, G, LD) + ell(cx, yb - 15, w / 2 - 3, w * 0.12, '#7d5e36', null, 0);
    for (var i = 0; i < 6; i++) o += circ(cx - w * 0.3 + r() * w * 0.6, yb - 15 + (r() * 2 - 1) * w * 0.07, 1.5, i % 2 ? AM : AM2, G, 0.4);
    return o;
  }
  def({ id: 'east-common-site-amber-dig-01', name: '琥珀坑·林间挖掘场', category: 'site', kind: 'site_amber_dig', resource: 'amber', subtype: 'forest_dig', facility: null,
    w: 4, d: 3, up: 58, tags: ['forest', 'dig_pit', 'sieve', 'amber'], roof: 'monopitch',
    note: '松林空地里挖两处阶梯土坑（坑壁露出橙色琥珀粒），坑边木梯、土堆，前方筛料台与晾珀竹匾，右侧茅草小棚；无对应 FacilityKind',
    draw: function (W, D, r, id) {
      var o = '';
      // 后排松树
      [[14, 34, 15], [44, 22, 17], [160, 24, 16], [184, 38, 13]].forEach(function (p) { o += K3.tree(p[0], p[1], p[2], S.leaf3, S.leaf, null, r); });
      o += K2.pad(10, 34, W - 10, D - 4, '#7d5e36', 0.35);
      // 两处挖掘坑
      o += K2.pit(30, 44, 104, 86, 14, '#8a5a2e', '#6e4626');
      o += path('M40 62 q16 -4 32 0 q16 4 26 -1', null, '#a26b36', 1.2);
      for (var i = 0; i < 7; i++) o += circ(40 + r() * 56, 56 + r() * 10, 1.6, i % 2 ? AM : AM2, G, 0.4);
      o += K2.ladder(84, 46, 80, 7);
      o += K2.pit(112, 54, 160, 82, 10, '#8a5a2e', '#6e4626');
      o += K.heap(176, 74, 14, 6, '#9c7a4c', '#7d5e36', r, 8);
      // 右：茅草小棚
      var inner = rect(150, 30, 34, 8, S.wood2, G, 0.8) + circ(160, 28, 1.6, AM, G, 0.4) + circ(167, 28, 1.6, AM2, G, 0.4) + circ(173, 29, 1.8, AM, G, 0.4);
      o += K3.shed(id + '-s', 144, 188, 34, 50, 28, S.thatch, 'thatch', inner);
      // 前：筛料台、晾珀竹匾、人
      o += sieve(54, 122, 30, r) + sieve(98, 128, 26, r);
      o += ell(146, 118, 18, 5, S.thatch, G, LD) + ell(146, 117.5, 13, 3, '#7d5e36', null, 0);
      for (i = 0; i < 8; i++) o += circ(136 + r() * 20, 116 + r() * 3, 1.5, i % 2 ? AM : AM2, G, 0.4);
      o += circ(76, 106, 3.6, S.cream, G, 0.8) + rect(72, 109, 8, 10, S.teal, G, 0.8) + K2.bar(80, 110, 88, 104, 1.2, S.wood3);
      o += K2.basket(176, 130, 13, 10, AM2, AM, r);
      return o;
    } });
  def({ id: 'east-common-prop-amber-sieve-01', name: '琥珀筛料台', category: 'prop', kind: 'prop_sieve', resource: 'amber', subtype: 'forest_dig', facility: null,
    w: 1, d: 1, up: 0, tags: ['sieve', 'amber'],
    draw: function (W, D, r) { return sieve(24, 42, 34, r); } });
  def({ id: 'east-common-prop-amber-basket-01', name: '琥珀料筐', category: 'prop', kind: 'prop_amber_basket', resource: 'amber', subtype: 'forest_dig', facility: null,
    w: 1, d: 1, up: 0, tags: ['basket', 'amber'],
    draw: function (W, D, r) { return K2.basket(16, 40, 14, 11, AM2, AM, r) + K2.basket(34, 44, 13, 10, AM, AM3, r); } });
  def({ id: 'east-common-prop-amber-pine-01', name: '流脂老松', category: 'prop', kind: 'prop_resin_pine', resource: 'amber', subtype: 'forest_dig', facility: null,
    w: 1, d: 1, up: 40, tags: ['tree', 'pine', 'resin'],
    draw: function (W, D, r) {
      var o = K3.tree(24, 42, 18, S.leaf3, S.leaf, null, r);
      return o + path('M23 24 q-1 5 1 9', null, AM2, 1.8) + circ(24, 33, 1.6, AM, G, 0.4);
    } });

  var scenes = [
    { key: 'ivory', title: '牙行作坊（ivory / carving_workshop）', ground: [],
      road: [[4, 5], [4, 6], [4, 7]],
      site: ['east-common-site-ivory-workshop-01', 2, 2],
      props: [['east-common-prop-ivory-tuskrack-01', 6, 4], ['east-common-prop-ivory-carvingbench-01', 7, 3], ['east-common-prop-ivory-crates-01', 2, 5], ['east-common-prop-ivory-crates-01', 6, 5]] },
    { key: 'amber', title: '琥珀坑（amber / forest_dig）',
      ground: [['east-common-ground-amber-forestfloor-01', 0, 0, 10, 5], ['east-common-ground-amber-forestfloor-02', 1, 5, 3, 2], ['east-common-ground-amber-forestfloor-02', 7, 1, 2, 3]],
      road: [[5, 5], [5, 6], [5, 7]],
      site: ['east-common-site-amber-dig-01', 3, 2],
      props: [['east-common-prop-amber-pine-01', 1, 1], ['east-common-prop-amber-pine-01', 8, 2], ['east-common-prop-amber-pine-01', 0, 4], ['east-common-prop-amber-sieve-01', 7, 4], ['east-common-prop-amber-basket-01', 2, 5], ['east-common-prop-amber-pine-01', 9, 6]] }
  ];
  return { all: function () { return defs.map(C.make); }, scenes: scenes };
});
