/*
 * 织梦 · east-site-2 · 农田（二）：果园（grain / orchard：柑橘）、棉田（cotton_farm：弹棉棚）、苎麻田（flax_farm：沤麻池）。
 * 浏览器挂 window.TownArtES2_field2，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./kit.js'), require('./kit2.js'), require('./kit3.js'));
  else root.TownArtES2_field2 = factory(root.TownArtES2_core, root.TownArtES2_kit, root.TownArtES2_kit2, root.TownArtES2_kit3);
})(this, function (C, K, K2, K3) {
  'use strict';
  var S = C.S, f = C.f, poly = C.poly, path = C.path, rect = C.rect, ell = C.ell, circ = C.circ, ln = C.ln;
  var G = S.ink, G2 = S.ink2, LW = S.lw, LD = S.lwd;
  var ORG = '#f08a24', CT = '#fbf6ea', RAMIE = '#8fb06a', RAMIE2 = '#6f9450';
  var defs = [];
  function def(o) { defs.push(o); }

  // ---------------- 果园（柑橘） ----------------
  def({ id: 'east-common-ground-orchard-grass-01', name: '果园草地', category: 'ground', kind: 'ground_orchard_grass', resource: 'grain', subtype: 'orchard', facility: null, variant: 1,
    w: 1, d: 1, up: 0, tags: ['tileable', 'orchard', 'grass'], note: '草色底 + 格内落果与草簇，距边 ≥5 px，可任意平铺',
    draw: function (W, D, r) {
      var o = rect(-0.5, -0.5, 49, 49, '#c9c27e'), i;
      for (i = 0; i < 7; i++) { var x = 6 + r() * 36, y = 8 + r() * 34; o += path('M' + f(x - 2) + ' ' + f(y) + 'l1 -4M' + f(x + 1) + ' ' + f(y) + 'l0 -5', null, S.leaf, 1); }
      for (i = 0; i < 3; i++) o += circ(8 + r() * 32, 8 + r() * 32, 1.4, ORG, G, 0.4);
      return o;
    } });
  def({ id: 'east-common-site-orchard-01', name: '果园·柑橘园', category: 'site', kind: 'site_citrus_orchard', resource: 'grain', subtype: 'orchard', facility: 'warehouse',
    w: 4, d: 3, up: 46, tags: ['orchard', 'citrus', 'fruit_shed', 'ladder'], roof: 'gable_tile',
    note: '三行柑橘树挂满橙果，树间木梯与摘果人，右后青瓦果棚堆果筐；主体按果品储放归 warehouse',
    draw: function (W, D, r, id) {
      var o = K2.pad(4, 4, W - 4, D - 4, '#c9c27e', 0.5);
      var inner = '';
      for (var i = 0; i < 3; i++) inner += K2.basket(144 + i * 14, 40, 11, 8, ORG, S.ochre, r);
      o += K3.shed(id + '-s', 132, 188, 18, 42, 26, S.navy2, 'tile', inner);
      var rows = [[16, 26, 4], [12, 72, 5], [16, 118, 5]];
      rows.forEach(function (rw, k) {
        for (var j = 0; j < rw[2]; j++) {
          var x = rw[0] + j * (k === 0 ? 30 : 38) + (k % 2) * 6;
          if (k === 0 && x > 112) continue;
          o += K3.tree(x + 10, rw[1] + 10, 13, S.leaf3, S.leaf, ORG, r);
        }
      });
      o += K2.ladder(70, 64, 92, 7) + circ(70, 60, 3.4, S.cream, G, 0.8) + rect(66, 63, 8, 9, S.teal, G, 0.8);
      o += K2.basket(84, 96, 11, 8, ORG, S.ochre, r);
      return o;
    } });
  def({ id: 'east-common-prop-orchard-tree-01', name: '柑橘树', category: 'prop', kind: 'prop_citrus_tree', resource: 'grain', subtype: 'orchard', facility: null,
    w: 1, d: 1, up: 20, tags: ['tree', 'citrus'],
    draw: function (W, D, r) { return K3.tree(24, 42, 16, S.leaf3, S.leaf, ORG, r); } });
  def({ id: 'east-common-prop-orchard-fruitbaskets-01', name: '橘筐', category: 'prop', kind: 'prop_fruit_baskets', resource: 'grain', subtype: 'orchard', facility: null,
    w: 1, d: 1, up: 4, tags: ['basket', 'fruit'],
    draw: function (W, D, r) { return K2.basket(15, 36, 14, 10, ORG, S.ochre, r) + K2.basket(33, 38, 14, 10, ORG, S.ochre, r) + K2.basket(24, 46, 14, 10, ORG, S.leaf, r); } });
  def({ id: 'east-common-prop-orchard-ladder-01', name: '摘果梯', category: 'prop', kind: 'prop_fruit_ladder', resource: 'grain', subtype: 'orchard', facility: null,
    w: 1, d: 1, up: 24, tags: ['ladder'],
    draw: function () { return C.shadow([[18, 42], [34, 42], [36, 45], [20, 45]]) + K2.ladder(18, -20, 42, 8) + K2.ladder(32, -20, 42, 8) + ln(18, -20, 32, -20, S.wood3, 1.6); } });

  // ---------------- 棉田（弹棉棚） ----------------
  /** 一株棉：脚底 (x, y)，几团白棉桃。 */
  function cottonPlant(x, y) {
    return ln(x, y, x, y - 7, S.leaf3, 0.9) + circ(x - 2, y - 4, 1.8, S.leaf, null, 0) + circ(x + 2, y - 6, 1.8, S.leaf, null, 0) +
      circ(x - 1.5, y - 7.5, 1.9, CT, G, 0.4) + circ(x + 2, y - 3.5, 1.6, CT, G, 0.4);
  }
  def({ id: 'east-common-ground-cotton-rows-01', name: '棉田垄', category: 'ground', kind: 'ground_cotton_rows', resource: 'grain', subtype: 'cotton_farm', facility: null, variant: 1,
    w: 1, d: 1, up: 0, tags: ['tileable', 'cotton', 'rows'], note: '每格四道横垄（周期 12 px），棉株间距 8 px 从 4 起，左右上下平铺无缝',
    draw: function () {
      var o = rect(-0.5, -0.5, 49, 49, S.earth2), y, x;
      for (y = 0; y < 48; y += 12) {
        o += rect(-0.5, y + 8, 49, 3, S.earth3, null, 0);
        for (x = 4; x < 48; x += 8) o += cottonPlant(x, y + 9);
      }
      return o;
    } });
  def({ id: 'east-common-site-cottonfarm-01', name: '棉田·弹棉棚', category: 'site', kind: 'site_cotton_farm', resource: 'grain', subtype: 'cotton_farm', facility: null,
    w: 4, d: 3, up: 48, tags: ['cotton', 'fluffing_bow', 'shed', 'rows'], roof: 'gable_thatch',
    note: '后排茅草弹棉棚，棚下匠人持大弓弹棉、案上棉胎，棚旁棉花堆；前方四垄棉田与摘棉人背篓；弹棉无对应 FacilityKind',
    draw: function (W, D, r, id) {
      var o = K2.pad(4, 4, W - 4, 56, S.earth, 0.5);
      var inner = rect(30, 58, 86, 10, S.cream2, G, LD) + rect(32, 68, 3, 12, S.wood3, null, 0) + rect(111, 68, 3, 12, S.wood3, null, 0);
      for (var i = 0; i < 8; i++) inner += circ(36 + i * 10, 57 - (i % 2), 3.2, CT, G, 0.4);
      inner += circ(72, 36, 3.6, S.cream, G, 0.8) + rect(68, 39, 8, 12, S.navy2, G, 0.8);
      inner += path('M54 30 Q72 18 96 34', null, S.wood3, 2.2) + ln(54, 30, 96, 34, S.cream, 0.6) + ln(72, 22, 72, 10, S.wood3, 0.9);
      o += K3.shed(id + '-s', 20, 128, 40, 80, 40, S.thatch, 'thatch', inner);
      // 棚旁棉花堆
      o += C.shadowEll(158, 78, 22, 4) + path('M136 78 Q136 52 158 50 Q182 52 180 78 Z', CT, G, LD);
      for (i = 0; i < 6; i++) o += circ(144 + i * 6, 62 + (i % 2) * 6, 3, null, S.gray3, 0.6);
      // 前方棉垄
      for (var y = 96; y < 142; y += 12) {
        o += rect(8, y, 176, 3, S.earth3, null, 0);
        for (var x = 12; x < 182; x += 8) o += cottonPlant(x, y + 1);
      }
      o += circ(120, 104, 3.4, S.cream, G, 0.8) + rect(116, 107, 8, 9, S.teal, G, 0.8) + K2.basket(128, 118, 10, 8, CT, CT, r);
      return o;
    } });
  def({ id: 'east-common-prop-cotton-bales-01', name: '棉包', category: 'prop', kind: 'prop_cotton_bales', resource: 'grain', subtype: 'cotton_farm', facility: null,
    w: 1, d: 1, up: 10, tags: ['cotton', 'bale'],
    draw: function () {
      var o = C.shadow([[8, 40], [44, 40], [46, 45], [10, 45]]);
      o += K2.box(6, 26, 42, 13, 7, CT, '#ece4cc') + K2.box(24, 44, 42, 13, 7, CT, '#ece4cc') + K2.box(14, 34, 22, 12, 6, CT, '#ece4cc');
      return o + ln(16, 22, 16, 42, S.wood3, 1) + ln(34, 22, 34, 42, S.wood3, 1) + ln(24, 5, 24, 22, S.wood3, 1);
    } });
  def({ id: 'east-common-prop-cotton-bow-01', name: '弹棉弓与棉胎', category: 'prop', kind: 'prop_fluffing_bow', resource: 'grain', subtype: 'cotton_farm', facility: null,
    w: 1, d: 1, up: 16, tags: ['cotton', 'bow', 'quilt'],
    draw: function () {
      var o = C.shadow([[6, 40], [44, 40], [46, 45], [8, 45]]) + K2.box(4, 44, 42, 8, 16, CT, S.cream);
      for (var i = 0; i < 4; i++) o += ln(8, 22 + i * 4, 40, 22 + i * 4, S.vermil, 0.6, C.op(0.6));
      return o + path('M6 4 Q22 -14 44 6', null, S.wood3, 2.2) + ln(6, 4, 44, 6, S.cream2, 0.7);
    } });
  def({ id: 'east-common-prop-cotton-pickbasket-01', name: '摘棉背篓', category: 'prop', kind: 'prop_pick_basket', resource: 'grain', subtype: 'cotton_farm', facility: null,
    w: 1, d: 1, up: 4, tags: ['basket', 'cotton'],
    draw: function (W, D, r) { return K2.basket(16, 38, 15, 14, CT, CT, r) + K2.basket(34, 44, 13, 12, CT, '#ece4cc', r); } });

  // ---------------- 苎麻田（沤麻池） ----------------
  /** 一丛苎麻：脚底 (x, y)，高茎 + 心形大叶（叶背发白）。 */
  function ramie(x, y, h) {
    h = h || 14;
    var o = ln(x, y, x, y - h, RAMIE2, 1) + ln(x + 3, y, x + 3.5, y - h * 0.85, RAMIE2, 1);
    o += ell(x - 2.5, y - h * 0.7, 3, 2, RAMIE, null, 0) + ell(x + 5, y - h * 0.55, 3, 2, '#c9d8b0', null, 0) + ell(x + 1, y - h - 1, 3.2, 2.2, RAMIE, null, 0);
    return o;
  }
  def({ id: 'east-common-ground-ramie-rows-01', name: '苎麻田', category: 'ground', kind: 'ground_ramie_rows', resource: 'grain', subtype: 'flax_farm', facility: null, variant: 1,
    w: 1, d: 1, up: 0, tags: ['tileable', 'ramie', 'fiber'], note: '每格三行苎麻（行距 16 px、株距 8 px 从 3 起），叶不出格上沿以外的同行周期，可平铺',
    draw: function () {
      var o = rect(-0.5, -0.5, 49, 49, S.earth2), y, x;
      for (y = 15; y < 48; y += 16) { o += rect(-0.5, y, 49, 2.4, S.earth3, null, 0); for (x = 3; x < 48; x += 8) o += ramie(x, y + 1, 11); }
      return o;
    } });
  def({ id: 'east-common-site-ramiefarm-01', name: '苎麻田·沤麻池', category: 'site', kind: 'site_ramie_farm', resource: 'grain', subtype: 'flax_farm', facility: null,
    w: 4, d: 3, up: 44, tags: ['ramie', 'retting_pond', 'fiber', 'drying_rack'], roof: 'gable_thatch',
    note: '后排苎麻丛，中间石砌沤麻池（池里压石泡麻捆），右侧竹竿晾麻架挂淡绿麻皮，前方剥麻人与刮麻刀；规范的 flax_farm 取东方苎麻；无对应 FacilityKind',
    draw: function (W, D, r, id) {
      var o = K2.pad(4, 4, W - 4, D - 4, S.earth, 0.45), x, y;
      for (y = 6; y <= 30; y += 12) for (x = 8 + (y % 24 ? 4 : 0); x < W - 6; x += 9) o += ramie(x, y, 16);
      // 沤麻池
      o += rect(14, 44, 112, 56, S.gray2, G, LW) + rect(14, 44, 112, 5, S.gray3, null, 0);
      for (x = 22; x < 126; x += 14) o += ln(x, 44, x, 49, S.gray, 0.8);
      o += K2.water([[20, 52], [120, 52], [120, 94], [20, 94]], id + '-pond', r, true);
      o += rect(20, 52, 100, 42, '#5f8a52', null, 0, C.fop(0.35));
      for (var i = 0; i < 5; i++) { var bx = 30 + i * 19, by = 64 + (i % 2) * 14; o += rect(bx - 7, by - 3, 14, 6, '#b8c890', G, 0.7) + K.rock(bx, by - 3, 4, 2, S.gray2, S.gray, r); }
      // 晾麻架
      o += K.post(140, 46, 100, 2.6) + K.post(182, 46, 100, 2.6) + ln(138, 50, 184, 50, S.wood3, 2);
      for (x = 144; x < 180; x += 5) o += path('M' + x + ' 50 L' + (x - 1) + ' 80 L' + (x + 2) + ' 80 Z', '#d8e2b8', G, 0.4);
      // 剥麻人 + 麻捆
      o += circ(60, 112, 3.6, S.cream, G, 0.8) + rect(56, 115, 8, 10, S.navy2, G, 0.8) + K2.bar(64, 120, 74, 116, 1.2, S.gray2);
      o += K.log(80, 116, 128, 3, '#b8c890') + K.log(84, 120, 134, 3, '#c9d8b0');
      return o;
    } });
  def({ id: 'east-common-prop-ramie-bundles-01', name: '麻捆', category: 'prop', kind: 'prop_fiber_bundles', resource: 'grain', subtype: 'flax_farm', facility: null,
    w: 1, d: 1, up: 4, tags: ['ramie', 'bundle'],
    draw: function () {
      var o = C.shadow([[6, 40], [44, 40], [46, 45], [8, 45]]);
      o += K.log(4, 42, 40, 3.4, '#b8c890') + K.log(6, 44, 32, 3.4, '#c9d8b0') + K.log(10, 40, 24, 3.2, '#b8c890');
      return o + ln(16, 20, 16, 43, S.wood3, 1.2) + ln(32, 20, 32, 43, S.wood3, 1.2);
    } });
  def({ id: 'east-common-prop-ramie-dryrack-01', name: '晾麻竹架', category: 'prop', kind: 'prop_fiber_rack', resource: 'grain', subtype: 'flax_farm', facility: null,
    w: 1, d: 1, up: 20, tags: ['ramie', 'drying_rack'],
    draw: function () {
      var o = C.shadow([[8, 40], [44, 40], [46, 45], [10, 45]]) + K2.bamboo(8, 42, 8, -18, 1.3) + K2.bamboo(40, 42, 40, -18, 1.3) + K2.bamboo(6, -14, 42, -14, 1.3);
      for (var x = 11; x < 38; x += 4) o += path('M' + x + ' -14 L' + (x - 1) + ' 22 L' + (x + 2) + ' 22 Z', '#d8e2b8', G, 0.4);
      return o;
    } });
  def({ id: 'east-common-prop-ramie-scraper-01', name: '刮麻凳', category: 'prop', kind: 'prop_fiber_scraper', resource: 'grain', subtype: 'flax_farm', facility: null,
    w: 1, d: 1, up: 6, tags: ['ramie', 'scraper', 'bench'],
    draw: function () {
      var o = C.shadow([[8, 40], [44, 40], [46, 45], [10, 45]]) + K2.box(8, 40, 42, 8, 10, S.wood2, S.wood);
      o += path('M12 22 L34 20 L36 26 L14 28 Z', '#c9d8b0', G, 0.6) + K2.bar(30, 18, 40, 14, 1.2, S.gray2) + rect(38, 10, 6, 6, S.wood3, G, 0.6);
      return o;
    } });

  var scenes = [
    { key: 'orchard', title: '果园（grain / orchard）',
      ground: [['east-common-ground-orchard-grass-01', 0, 0, 10, 8]],
      road: [[5, 5], [5, 6], [5, 7]],
      site: ['east-common-site-orchard-01', 3, 2],
      props: [['east-common-prop-orchard-tree-01', 1, 1], ['east-common-prop-orchard-tree-01', 1, 3], ['east-common-prop-orchard-tree-01', 8, 2], ['east-common-prop-orchard-tree-01', 8, 5],
        ['east-common-prop-orchard-fruitbaskets-01', 4, 5], ['east-common-prop-orchard-ladder-01', 2, 5], ['east-common-prop-orchard-tree-01', 1, 6]] },
    { key: 'cotton_farm', title: '棉田（grain / cotton_farm）',
      ground: [['east-common-ground-cotton-rows-01', 0, 5, 4, 3], ['east-common-ground-cotton-rows-01', 6, 5, 4, 3], ['east-common-ground-cotton-rows-01', 8, 1, 2, 3]],
      road: [[5, 5], [5, 6], [5, 7]],
      site: ['east-common-site-cottonfarm-01', 3, 2],
      props: [['east-common-prop-cotton-bales-01', 2, 3], ['east-common-prop-cotton-bow-01', 7, 3], ['east-common-prop-cotton-pickbasket-01', 1, 4], ['east-common-prop-cotton-bales-01', 7, 4]] },
    { key: 'flax_farm', title: '苎麻田（grain / flax_farm）',
      ground: [['east-common-ground-ramie-rows-01', 0, 0, 3, 3], ['east-common-ground-ramie-rows-01', 7, 0, 3, 2], ['east-common-ground-ramie-rows-01', 0, 5, 4, 3], ['east-common-ground-ramie-rows-01', 6, 5, 4, 3]],
      road: [[5, 5], [5, 6], [5, 7]],
      site: ['east-common-site-ramiefarm-01', 3, 2],
      props: [['east-common-prop-ramie-bundles-01', 2, 4], ['east-common-prop-ramie-dryrack-01', 7, 3], ['east-common-prop-ramie-scraper-01', 7, 4], ['east-common-prop-ramie-dryrack-01', 1, 3]] }
  ];
  return { all: function () { return defs.map(C.make); }, scenes: scenes };
});
