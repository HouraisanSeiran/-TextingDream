/*
 * 织梦 · east-site-2 · 农田（一）：稻作农庄（grain / rice_paddy：农舍 + 水田 + 龙骨水车）、粟黍旱田（millet_farm：梯田）、菜园（vegetable_farm）。
 * 浏览器挂 window.TownArtES2_field，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./kit.js'), require('./kit2.js'), require('./kit3.js'));
  else root.TownArtES2_field = factory(root.TownArtES2_core, root.TownArtES2_kit, root.TownArtES2_kit2, root.TownArtES2_kit3);
})(this, function (C, K, K2, K3) {
  'use strict';
  var S = C.S, f = C.f, poly = C.poly, path = C.path, rect = C.rect, ell = C.ell, circ = C.circ, ln = C.ln;
  var G = S.ink, G2 = S.ink2, LW = S.lw, LD = S.lwd;
  var MIL = '#e0b44a', MIL2 = '#c8932e';
  var defs = [];
  function def(o) { defs.push(o); }
  /** 一行秧苗（沿 x，y 处，间距 6）：小 V 形绿叶。 */
  function seedRow(x0, x1, y, col) {
    var o = '';
    for (var x = x0; x <= x1; x += 6) o += path('M' + f(x - 1.6) + ' ' + f(y - 3) + 'L' + f(x) + ' ' + f(y) + 'L' + f(x + 1.6) + ' ' + f(y - 3), null, col || S.leaf, 1);
    return o;
  }
  /** 龙骨水车（翻车）：斜槽从低 (x1,y1) 到高 (x2,y2)，高端带脚踏轮架与踩车人。 */
  function dragonBone(x1, y1, x2, y2) {
    var o = K2.bar(x1, y1, x2, y2, 5, S.wood);
    var L = Math.hypot(x2 - x1, y2 - y1), n = Math.floor(L / 5);
    for (var i = 1; i < n; i++) { var t = i / n, x = x1 + (x2 - x1) * t, y = y1 + (y2 - y1) * t; o += rect(x - 1, y - 4.5, 2, 3, S.wood3, null, 0); }
    o += K.post(x2 - 8, y2 - 18, y2 + 6, 2.4) + K.post(x2 + 8, y2 - 18, y2 + 6, 2.4) + ln(x2 - 10, y2 - 16, x2 + 10, y2 - 16, S.wood3, 2);
    o += K2.wheel(x2, y2 - 2, 6, 6, S.wood3);
    o += circ(x2, y2 - 26, 3.4, S.cream, G, 0.8) + rect(x2 - 4, y2 - 23, 8, 9, S.teal, G, 0.8) + ln(x2 - 2, y2 - 14, x2 - 3, y2 - 6, S.brown, 1.4) + ln(x2 + 2, y2 - 14, x2 + 3, y2 - 8, S.brown, 1.4);
    return o;
  }
  /** 水田块：田埂框 + 水面 + 秧苗行。 */
  function paddy(id, x0, y0, x1, y1, r) {
    var o = rect(x0 - 2, y0 - 2, x1 - x0 + 4, y1 - y0 + 4, S.earth2, G, LD);
    o += K2.water([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], id, r, true);
    for (var y = y0 + 6; y < y1 - 1; y += 6) o += seedRow(x0 + 4, x1 - 3, y, S.leaf);
    return o;
  }

  // ---------------- 稻作农庄 ----------------
  def({ id: 'east-common-ground-ricefield-01', name: '秧田水格', category: 'ground', kind: 'ground_paddy_seedling', resource: 'grain', subtype: 'rice_paddy', facility: null, variant: 1,
    w: 1, d: 1, up: 0, tags: ['tileable', 'paddy', 'water'], note: '整格水面带秧苗行，四边田埂各占 2 px（相邻两格拼成 4 px 宽埂），水色同 east-ground',
    draw: function (W, D, r, id) { return rect(-0.5, -0.5, 49, 49, S.earth2) + paddy(id, 2, 2, 46, 46, r); } });
  def({ id: 'east-common-ground-ricefield-02', name: '稻熟水格', category: 'ground', kind: 'ground_paddy_ripe', resource: 'grain', subtype: 'rice_paddy', facility: null, variant: 2,
    w: 1, d: 1, up: 0, tags: ['tileable', 'paddy', 'ripe'], note: '同 01 的田埂，水面上是成熟金黄稻穗',
    draw: function (W, D, r, id) {
      var o = rect(-0.5, -0.5, 49, 49, S.earth2) + K2.water([[2, 2], [46, 2], [46, 46], [2, 46]], id, r, true);
      for (var y = 8; y < 46; y += 6) for (var x = 6; x < 44; x += 6) o += path('M' + f(x) + ' ' + f(y) + 'l0 -4q2 -1 3 1', null, S.ochre, 1.2);
      return o;
    } });
  def({ id: 'east-common-site-ricefarm-01', name: '稻作农庄·农舍水田龙骨水车', category: 'site', kind: 'site_rice_farm', resource: 'grain', subtype: 'rice_paddy', facility: null,
    w: 4, d: 3, up: 50, tags: ['farmhouse', 'paddy', 'dragon_bone_pump', 'irrigation'], roof: 'gable_thatch',
    note: '后排茅顶农舍与稻草垛，前方三块水田（秧苗行），左侧水渠用龙骨水车（翻车）踩水上田；农庄无对应 FacilityKind',
    draw: function (W, D, r, id) {
      var o = K2.pad(4, 4, W - 4, 40, S.earth, 0.45);
      // 后：农舍 + 草垛
      o += K3.house(id + '-h', 70, 150, 34, 30, -12, S.cream, S.thatch, 'thatch', 96);
      o += rect(124, 12, 10, 10, S.navy, G, 0.8) + ln(129, 12, 129, 22, G2, 0.6) + ln(124, 17, 134, 17, G2, 0.6);
      o += path('M160 38 Q160 6 172 4 Q184 6 184 38 Z', S.thatch, G, LD) + path('M164 26 q8 -3 16 0', null, S.thatch2, 0.9) + path('M163 16 q9 -3 18 0', null, S.thatch2, 0.9) + ell(172, 4, 3, 2, S.thatch2, G, 0.7);
      // 左：水渠
      o += K2.water([[4, 44], [22, 44], [22, 140], [4, 140]], id + '-ca', r);
      // 三块水田
      o += paddy(id + '-p1', 34, 50, 108, 92, r) + paddy(id + '-p2', 118, 50, 186, 92, r) + paddy(id + '-p3', 34, 102, 186, 138, r);
      // 龙骨水车：从水渠斜拉到田埂
      o += dragonBone(10, 120, 32, 96);
      // 田里插秧人与斗笠
      o += ell(150, 112, 7, 2.6, S.thatch, G, 0.8) + path('M144 112 L150 106 L156 112', S.thatch, G, 0.8) + rect(147, 112, 6, 8, S.navy2, G, 0.7);
      return o;
    } });
  def({ id: 'east-common-prop-rice-sheaves-01', name: '稻草垛', category: 'prop', kind: 'prop_straw_stack', resource: 'grain', subtype: 'rice_paddy', facility: null,
    w: 1, d: 1, up: 20, tags: ['straw', 'stack'],
    draw: function () {
      var o = C.shadowEll(27, 43, 16, 3);
      o += path('M10 44 Q8 6 24 -14 Q40 6 38 44 Z', S.thatch, G, LD);
      for (var y = 0; y < 40; y += 8) o += path('M' + f(13 - y * 0.05) + ' ' + f(y) + 'q11 -3 22 0', null, S.thatch2, 0.9);
      return o + ell(24, -13, 3, 2, S.thatch2, G, 0.7) + ln(24, -16, 24, -20, S.wood3, 1.4);
    } });
  def({ id: 'east-common-prop-rice-pump-01', name: '龙骨水车', category: 'prop', kind: 'prop_dragon_bone_pump', resource: 'grain', subtype: 'rice_paddy', facility: null,
    w: 1, d: 1, up: 30, tags: ['irrigation', 'pump'],
    draw: function () { return C.shadow([[20, 40], [40, 40], [44, 45], [24, 45]]) + dragonBone(4, 44, 30, 22); } });
  def({ id: 'east-common-prop-rice-thresher-01', name: '打谷桶', category: 'prop', kind: 'prop_threshing_tub', resource: 'grain', subtype: 'rice_paddy', facility: null,
    w: 1, d: 1, up: 12, tags: ['threshing', 'tub'],
    draw: function () {
      var o = C.shadow([[10, 40], [44, 40], [46, 45], [12, 45]]);
      o += poly([[6, 20], [42, 20], [38, 42], [10, 42]], S.wood, G, LD) + ell(24, 20, 18, 5, S.wood3, G, LD) + ell(24, 21, 14, 3, S.ochre, null, 0);
      for (var x = 12; x < 38; x += 6) o += ln(x, 24, x + (x - 24) * -0.1, 41, S.wood3, 0.7);
      return o + path('M10 20 L12 -4 L36 -4 L38 20', null, S.thatch2, 1.2) + ln(12, -4, 36, -4, S.wood3, 1.2);
    } });

  // ---------------- 粟黍旱田（梯田） ----------------
  /** 一级旱作梯田：前坎 y 处（坎高 hh），田面从 y-dp 到 y，穗行颜色 col。 */
  function terrace(x0, x1, y, dp, hh, col, col2, r) {
    var o = rect(x0, y - dp, x1 - x0, dp, MIL2, null, 0, C.fop(0.35));
    for (var yy = y - dp + 4; yy < y - 1; yy += 5) for (var x = x0 + 3 + (yy % 2) * 2; x < x1 - 2; x += 5) {
      o += ln(x, yy, x, yy - 4, S.leaf3, 0.8) + ell(x + 0.8, yy - 4.5, 1.2, 2.2, (x + yy) % 3 ? col : col2, null, 0);
    }
    o += path('M' + f(x0) + ' ' + f(y) + 'Q' + f((x0 + x1) / 2) + ' ' + f(y + 2) + ' ' + f(x1) + ' ' + f(y) + 'L' + f(x1) + ' ' + f(y + hh) + 'L' + f(x0) + ' ' + f(y + hh) + 'Z', S.earth3, G, LD);
    for (var k = 0; k < 6; k++) o += circ(x0 + 6 + r() * (x1 - x0 - 12), y + hh * 0.5, 1.4, S.earth2, null, 0);
    return o;
  }
  def({ id: 'east-common-ground-millet-terrace-01', name: '粟田梯坎', category: 'ground', kind: 'ground_millet_terrace', resource: 'grain', subtype: 'millet_farm', facility: null, variant: 1,
    w: 1, d: 1, up: 0, tags: ['tileable', 'terrace', 'millet'], note: '每格两级旱作梯坎，坎与穗行横贯整格（穗行周期 5 px、坎在固定 y），左右平铺无缝、上下平铺连成连续梯田',
    draw: function () {
      var o = rect(-0.5, -0.5, 49, 49, S.earth2), k;
      for (k = 0; k < 2; k++) {
        var y = k * 24 + 19;
        o += rect(-0.5, y - 19, 49, 19, MIL2, null, 0, C.fop(0.35));
        for (var yy = y - 15; yy < y - 1; yy += 5) for (var x = 2.5; x < 48; x += 5) o += ln(x, yy, x, yy - 4, S.leaf3, 0.8) + ell(x + 0.8, yy - 4.5, 1.2, 2.2, MIL, null, 0);
        o += rect(-0.5, y, 49, 5, S.earth3) + ln(-0.5, y, 48.5, y, S.ink, 0.8);
      }
      return o;
    } });
  def({ id: 'east-common-site-milletfarm-01', name: '粟黍旱田·梯田', category: 'site', kind: 'site_millet_terrace', resource: 'grain', subtype: 'millet_farm', facility: 'granary',
    w: 4, d: 3, up: 60, tags: ['terrace', 'millet', 'dry_farming', 'granary'], roof: 'gable_thatch',
    note: '黄土坡开四级旱作梯田（金黄粟穗与红黍穗），坡顶土窑洞式小粮仓，梯坎间有土阶小路；粮仓归 granary',
    draw: function (W, D, r, id) {
      var o = K3.cliff([[0, 20], [0, -40], [60, -58], [130, -52], [192, -60], [192, 20]], id + '-c', S.earth2, S.earth3, r);
      // 坡顶粮仓（土墙圆仓 + 茅顶）
      o += C.shadowEll(150, -24, 18, 4) + rect(134, -48, 30, 24, S.earth, G, LD) + path('M130 -46 Q149 -72 168 -46 Z', S.thatch, G, LD) + rect(144, -40, 10, 16, S.brown, G, 0.8);
      o += path('M137 -54 q12 -6 24 0', null, S.thatch2, 0.9);
      // 四级梯田
      var rows = [[6, 120, -20, 16], [10, 186, 4, 18], [6, 180, 30, 20], [4, 188, 58, 22]];
      rows.forEach(function (t, i) { o += terrace(t[0], t[1], t[2], t[3], 7, i % 2 ? MIL : '#b5452c', MIL2, r); });
      o += terrace(4, 188, 86, 22, 6, MIL, MIL2, r) + terrace(4, 188, 114, 22, 6, '#b5452c', MIL, r);
      // 土阶小路
      for (var k = 0; k < 6; k++) o += rect(122 - k * 3, -16 + k * 22, 12, 5, S.earth, G, 0.7);
      // 田里锄地人
      o += circ(60, 74, 3.4, S.cream, G, 0.8) + rect(56, 77, 8, 10, S.vermil, G, 0.8) + K2.bar(64, 84, 74, 76, 1.2, S.wood3) + ell(60, 72, 6, 2.2, S.thatch, G, 0.7);
      return o;
    } });
  def({ id: 'east-common-prop-millet-sheaves-01', name: '粟穗捆', category: 'prop', kind: 'prop_millet_sheaves', resource: 'grain', subtype: 'millet_farm', facility: null,
    w: 1, d: 1, up: 14, tags: ['millet', 'sheaves'],
    draw: function () {
      var o = C.shadowEll(26, 43, 18, 3);
      [[14, 42], [34, 42], [24, 38]].forEach(function (p) {
        o += path('M' + (p[0] - 5) + ' ' + p[1] + ' L' + (p[0] - 2) + ' ' + (p[1] - 30) + ' L' + (p[0] + 2) + ' ' + (p[1] - 30) + ' L' + (p[0] + 5) + ' ' + p[1] + ' Z', S.thatch, G, LD);
        o += rect(p[0] - 3.5, p[1] - 16, 7, 2.4, S.wood3, null, 0);
        for (var k = -1; k <= 1; k++) o += ell(p[0] + k * 3, p[1] - 33, 2, 5, MIL, G, 0.5);
      });
      return o;
    } });
  def({ id: 'east-common-prop-millet-mortar-01', name: '石碾', category: 'prop', kind: 'prop_stone_roller', resource: 'grain', subtype: 'millet_farm', facility: null,
    w: 1, d: 1, up: 8, tags: ['roller', 'milling'],
    draw: function () {
      var o = C.shadowEll(27, 42, 20, 4) + ell(24, 38, 20, 7, S.gray2, G, LD) + ell(24, 36, 17, 5, S.gray3, null, 0);
      for (var i = 0; i < 9; i++) o += circ(12 + i * 3, 36 + (i % 2), 1, MIL, null, 0);
      o += rect(16, 22, 16, 12, S.gray, G, LD) + ell(32, 28, 3, 6, S.gray2, G, 0.8) + K2.bar(24, 30, 46, 22, 1.4, S.wood3);
      return o + ln(24, 36, 24, 18, S.wood3, 1.6);
    } });

  // ---------------- 菜园 ----------------
  /** 一畦菜：x0..x1 × y0..y1，kind = cabbage / scallion / pepper。 */
  function bed(x0, y0, x1, y1, kind) {
    var o = rect(x0, y0, x1 - x0, y1 - y0, S.earth3, G, LD) + rect(x0 + 1.5, y0 + 1.5, x1 - x0 - 3, y1 - y0 - 3, '#9a6b3c', null, 0);
    for (var y = y0 + 7; y < y1 - 1; y += 8) for (var x = x0 + 6; x < x1 - 3; x += 9) {
      if (kind === 'cabbage') o += circ(x, y - 1, 3.4, S.leaf2, G, 0.6) + circ(x, y - 1.4, 1.6, '#c9e3a0', null, 0);
      else if (kind === 'scallion') o += ln(x - 2, y, x - 3, y - 7, S.leaf, 1) + ln(x, y, x, y - 8, S.leaf2, 1) + ln(x + 2, y, x + 3, y - 7, S.leaf, 1);
      else o += circ(x, y - 2, 3, S.leaf, null, 0) + circ(x - 1.4, y - 1, 1.1, S.vermil, null, 0) + circ(x + 1.5, y - 2.4, 1.1, S.vermil, null, 0);
    }
    return o;
  }
  def({ id: 'east-common-ground-vegbed-rows-01', name: '菜畦格', category: 'ground', kind: 'ground_vegetable_bed', resource: 'grain', subtype: 'vegetable_farm', facility: null, variant: 1,
    w: 1, d: 1, up: 0, tags: ['tileable', 'vegetable', 'beds'], note: '每格一畦白菜，畦距格边 3 px，格边是同色走道土，可任意平铺',
    draw: function () { return rect(-0.5, -0.5, 49, 49, S.earth) + bed(3, 3, 45, 45, 'cabbage'); } });
  def({ id: 'east-common-ground-vegbed-rows-02', name: '葱畦格', category: 'ground', kind: 'ground_vegetable_bed', resource: 'grain', subtype: 'vegetable_farm', facility: null, variant: 2,
    w: 1, d: 1, up: 0, tags: ['tileable', 'vegetable', 'beds'], note: '同 01 规格，畦里是葱',
    draw: function () { return rect(-0.5, -0.5, 49, 49, S.earth) + bed(3, 3, 45, 45, 'scallion'); } });
  def({ id: 'east-common-site-vegfarm-01', name: '菜园·竹篱菜畦', category: 'site', kind: 'site_vegetable_garden', resource: 'grain', subtype: 'vegetable_farm', facility: 'well',
    w: 4, d: 3, up: 44, tags: ['vegetable', 'beds', 'bamboo_trellis', 'well'], roof: 'gable_thatch',
    note: '后排茅顶小屋与丝瓜竹架，中间辘轳井，前方竹篱围出白菜、葱、辣椒六畦，挑粪桶人；主设施按水井归 well',
    draw: function (W, D, r, id) {
      var o = K2.pad(4, 4, W - 4, D - 4, S.earth, 0.5);
      o += K3.house(id + '-h', 12, 66, 30, 26, -10, S.cream, S.thatch, 'thatch', 40);
      // 丝瓜竹架
      for (var x = 84; x <= 140; x += 14) o += K2.bamboo(x, 36, x, 2, 1.2);
      o += K2.bamboo(80, 4, 144, 4, 1.2);
      for (x = 86; x < 140; x += 6) o += circ(x, 6 + (x % 4), 3.4, S.leaf, null, 0) + (x % 12 === 2 ? ell(x, 14, 1.6, 4.5, S.leaf2, G, 0.5) : '');
      // 井
      o += ell(168, 30, 12, 4.4, S.gray2, G, LD) + rect(156, 30, 24, 8, S.gray, G, LD) + ell(168, 30, 8, 2.6, S.waterDeep, null, 0);
      o += K.post(158, 8, 32, 2.4) + K.post(178, 8, 32, 2.4) + ln(156, 12, 180, 12, S.wood3, 2.4) + ln(168, 12, 168, 26, S.wood3, 0.8);
      // 六畦
      var kinds = ['cabbage', 'scallion', 'pepper'];
      for (var i = 0; i < 6; i++) { var cx = 14 + (i % 3) * 58, cy = 52 + Math.floor(i / 3) * 42; o += bed(cx, cy, cx + 50, cy + 34, kinds[(i + Math.floor(i / 3)) % 3]); }
      // 前竹篱
      o += K3.fence(6, 140, 80, 140, 8, 6, S.leaf2) + K3.fence(112, 140, 186, 140, 8, 6, S.leaf2);
      o += circ(96, 112, 3.4, S.cream, G, 0.8) + rect(92, 115, 8, 10, S.teal, G, 0.8) + K2.bar(84, 112, 108, 112, 1.2, S.wood3);
      o += path('M84 112 l-2 8 l6 0 z', S.wood, G, 0.6) + path('M108 112 l-2 8 l6 0 z', S.wood, G, 0.6);
      return o;
    } });
  def({ id: 'east-common-prop-veg-trellis-01', name: '瓜豆竹架', category: 'prop', kind: 'prop_bean_trellis', resource: 'grain', subtype: 'vegetable_farm', facility: null,
    w: 1, d: 1, up: 26, tags: ['trellis', 'bamboo', 'gourd'],
    draw: function () {
      var o = C.shadow([[8, 40], [44, 40], [46, 45], [10, 45]]);
      o += K2.bamboo(8, 42, 18, -20, 1.2) + K2.bamboo(28, 42, 18, -20, 1.2) + K2.bamboo(22, 42, 34, -20, 1.2) + K2.bamboo(44, 42, 34, -20, 1.2) + K2.bamboo(14, -18, 38, -18, 1.2);
      for (var i = 0; i < 8; i++) o += circ(14 + (i % 4) * 7, -12 + Math.floor(i / 4) * 18 + (i % 2) * 4, 3.6, i % 3 ? S.leaf : S.leaf2, null, 0);
      return o + ell(20, 6, 1.8, 5, S.leaf2, G, 0.5) + ell(32, 14, 1.8, 5, S.leaf2, G, 0.5);
    } });
  def({ id: 'east-common-prop-veg-buckets-01', name: '浇菜木桶', category: 'prop', kind: 'prop_water_buckets', resource: 'grain', subtype: 'vegetable_farm', facility: null,
    w: 1, d: 1, up: 6, tags: ['bucket', 'carry_pole'],
    draw: function () {
      var o = '';
      [14, 34].forEach(function (x) { o += C.shadowEll(x + 2, 42, 9, 2.4) + poly([[x - 8, 26], [x + 8, 26], [x + 6, 42], [x - 6, 42]], S.wood, G, LD) + ell(x, 26, 8, 2.6, S.water, G, LD) + ln(x - 7, 33, x + 7, 33, S.wood3, 1); });
      return o + K2.bar(4, 22, 46, 18, 1.6, S.wood3);
    } });
  def({ id: 'east-common-prop-veg-baskets-01', name: '菜筐', category: 'prop', kind: 'prop_veg_baskets', resource: 'grain', subtype: 'vegetable_farm', facility: null,
    w: 1, d: 1, up: 4, tags: ['basket', 'vegetable'],
    draw: function (W, D, r) { return K2.basket(15, 36, 14, 10, S.leaf2, S.leaf, r) + K2.basket(33, 38, 14, 10, S.vermil, S.leaf, r) + K2.basket(24, 46, 14, 10, '#c9e3a0', S.leaf2, r); } });

  var scenes = [
    { key: 'rice_paddy', title: '稻作农庄（grain / rice_paddy）',
      ground: [['east-common-ground-ricefield-01', 0, 5, 4, 3], ['east-common-ground-ricefield-02', 6, 5, 4, 3], ['east-common-ground-ricefield-01', 7, 1, 3, 2]],
      road: [[5, 4], [5, 5], [5, 6], [5, 7], [4, 4]],
      site: ['east-common-site-ricefarm-01', 1, 1],
      props: [['east-common-prop-rice-sheaves-01', 5, 1], ['east-common-prop-rice-pump-01', 6, 3], ['east-common-prop-rice-thresher-01', 6, 4], ['east-common-prop-rice-sheaves-01', 0, 4]] },
    { key: 'millet_farm', title: '粟黍旱田（grain / millet_farm）',
      ground: [['east-common-ground-millet-terrace-01', 0, 5, 3, 3], ['east-common-ground-millet-terrace-01', 7, 4, 3, 4]],
      road: [[4, 5], [4, 6], [4, 7]],
      site: ['east-common-site-milletfarm-01', 2, 2],
      props: [['east-common-prop-millet-sheaves-01', 6, 4], ['east-common-prop-millet-mortar-01', 5, 5], ['east-common-prop-millet-sheaves-01', 3, 5], ['east-common-prop-millet-mortar-01', 1, 3]] },
    { key: 'vegetable_farm', title: '菜园（grain / vegetable_farm）',
      ground: [['east-common-ground-vegbed-rows-01', 0, 5, 2, 2], ['east-common-ground-vegbed-rows-02', 6, 5, 2, 2], ['east-common-ground-vegbed-rows-02', 7, 1, 2, 2]],
      road: [[4, 5], [4, 6], [4, 7]],
      site: ['east-common-site-vegfarm-01', 2, 2],
      props: [['east-common-prop-veg-trellis-01', 1, 3], ['east-common-prop-veg-buckets-01', 5, 5], ['east-common-prop-veg-baskets-01', 3, 5], ['east-common-prop-veg-trellis-01', 6, 2]] }
  ];
  return { all: function () { return defs.map(C.make); }, scenes: scenes };
});
