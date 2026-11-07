/*
 * 织梦 · east-site-2 · 畜牧（一）：耕牛牛栏（livestock / cattle_ranch）、牦牛奶场（dairy_farm）、猪圈（pig_farm）。
 * 浏览器挂 window.TownArtES2_herd，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./kit.js'), require('./kit2.js'), require('./kit3.js'));
  else root.TownArtES2_herd = factory(root.TownArtES2_core, root.TownArtES2_kit, root.TownArtES2_kit2, root.TownArtES2_kit3);
})(this, function (C, K, K2, K3) {
  'use strict';
  var S = C.S, f = C.f, poly = C.poly, path = C.path, rect = C.rect, ell = C.ell, circ = C.circ, ln = C.ln;
  var G = S.ink, G2 = S.ink2, LW = S.lw, LD = S.lwd, A = K3.A;
  var defs = [];
  function def(o) { defs.push(o); }
  /** 草料槽：x0..x1，脚底 yb。 */
  function trough(x0, x1, yb, fill) {
    return C.shadow([[x0 + 2, yb], [x1 + 4, yb], [x1 + 4, yb + 3], [x0 + 3, yb + 3]]) +
      poly([[x0, yb - 8], [x1, yb - 8], [x1 - 2, yb], [x0 + 2, yb]], S.wood, G, LD) + rect(x0 + 1.5, yb - 9.5, x1 - x0 - 3, 2.4, fill || S.thatch, null, 0);
  }
  /** 牛棚：茅顶敞棚，棚下拴牛。 */
  function barn(id, x0, x1, yBack, yb, h, inner) { return K3.shed(id, x0, x1, yBack, yb, h, S.thatch, 'thatch', inner, S.earth); }

  def(K3.speckTile({ id: 'east-common-ground-muddyyard-01', name: '牲口踩泥地', kind: 'ground_trampled_mud', resource: 'livestock', subtype: 'cattle_ranch', v: 1,
    base: '#b08a58', n: 12, cols: ['#8f6b40', '#c79c5c', S.thatch2], specks: [S.thatch], tags: ['mud', 'yard', 'livestock'],
    note: '牛栏、猪圈共用的踩实泥地；泥块与草屑都在格内（距边 ≥4 px），可任意平铺' }));
  def(K3.speckTile({ id: 'east-common-ground-muddyyard-02', name: '牲口踩泥地 2（带水洼）', kind: 'ground_trampled_mud', resource: 'livestock', subtype: 'pig_farm', v: 2,
    base: '#b08a58', n: 8, cols: ['#8f6b40', '#9c7a4c'], specks: [S.thatch], tags: ['mud', 'puddle', 'livestock'],
    under: function (r) { return ell(16 + r() * 16, 18 + r() * 12, 9, 4, '#8f6b40', null, 0) + ell(16 + r() * 16, 20 + r() * 10, 6, 2.4, S.water, null, 0, C.fop(0.7)); } }));

  // ---------------- 耕牛牛栏 ----------------
  def({ id: 'east-common-site-cattlebarn-01', name: '耕牛牛栏', category: 'site', kind: 'site_cattle_barn', resource: 'livestock', subtype: 'cattle_ranch', facility: null,
    w: 4, d: 3, up: 48, tags: ['cattle', 'ox', 'barn', 'plough', 'pen'], roof: 'gable_thatch',
    note: '后排茅顶牛棚拴两头黄牛、草料槽；左前木栅牛圈里三头耕牛；右前犁、耙与草垛；牛棚与 stable（马厩）不同类，填 null',
    draw: function (W, D, r, id) {
      var o = K2.pad(4, 4, W - 4, D - 4, '#b08a58', 0.45);
      var inner = trough(40, 120, 66, S.thatch) + A.cow(54, 62, 1) + A.cow(100, 62, -1);
      o += barn(id + '-b', 22, 138, 34, 70, 36, inner);
      o += path('M150 70 Q150 30 166 26 Q184 30 184 70 Z', S.thatch, G, LD) + path('M153 54 q13 -4 28 0', null, S.thatch2, 0.9) + path('M155 40 q11 -4 22 0', null, S.thatch2, 0.9);
      o += K3.penBack(10, 84, 120, 136, 10);
      o += A.cow(36, 108, 1, 18) + A.cow(80, 104, -1, 18) + A.cow(58, 128, 1, 17);
      o += K3.penFront(10, 120, 136, 10, null, 18);
      // 犁 + 耙
      o += K2.bar(136, 122, 170, 106, 1.8, S.wood3) + poly([[132, 118], [142, 116], [140, 126], [130, 128]], S.gray, G, 0.8) + ln(150, 114, 156, 128, S.wood3, 1.4);
      o += rect(152, 130, 34, 4, S.wood, G, 0.7);
      for (var x = 155; x < 186; x += 5) o += ln(x, 134, x, 138, S.gray, 1);
      return o;
    } });
  def({ id: 'east-common-prop-cattle-ox-01', name: '耕牛', category: 'prop', kind: 'prop_ox', resource: 'livestock', subtype: 'cattle_ranch', facility: null,
    w: 1, d: 1, up: 4, tags: ['animal', 'ox'],
    draw: function () { return A.cow(22, 38, 1, 22); } });
  def({ id: 'east-common-prop-cattle-plough-01', name: '曲辕犁', category: 'prop', kind: 'prop_plough', resource: 'livestock', subtype: 'cattle_ranch', facility: null,
    w: 1, d: 1, up: 6, tags: ['plough', 'tool'],
    draw: function () {
      var o = C.shadow([[8, 40], [44, 40], [46, 45], [10, 45]]);
      o += path('M8 38 Q24 30 44 8', null, G, 4) + path('M8 38 Q24 30 44 8', null, S.wood3, 2.4);
      o += poly([[4, 36], [16, 34], [14, 44], [2, 44]], S.gray, G, 0.8) + K2.bar(14, 36, 20, 16, 1.6, S.wood);
      return o + ln(18, 14, 26, 18, S.wood3, 2);
    } });
  def({ id: 'east-common-prop-cattle-trough-01', name: '草料槽', category: 'prop', kind: 'prop_feed_trough', resource: 'livestock', subtype: 'cattle_ranch', facility: null,
    w: 1, d: 1, up: 0, tags: ['trough', 'fodder'],
    draw: function () { return trough(4, 44, 40, S.thatch) + path('M10 30 q4 -6 8 0 q4 -6 8 0', null, S.thatch2, 1); } });

  // ---------------- 牦牛奶场 ----------------
  /** 奶桶：木桶 + 铁箍 + 奶面。 */
  function milkPail(cx, yb, w) {
    return C.shadowEll(cx + 2, yb, w * 0.6, 2.2) + poly([[cx - w / 2, yb - w * 0.9], [cx + w / 2, yb - w * 0.9], [cx + w * 0.4, yb], [cx - w * 0.4, yb]], S.wood, G, LD) +
      ell(cx, yb - w * 0.9, w / 2, w * 0.16, S.cream2, G, LD) + ln(cx - w * 0.46, yb - w * 0.45, cx + w * 0.46, yb - w * 0.45, S.gray, 1.1);
  }
  /** 打酥油长木桶（竖筒 + 搅杆）。 */
  function churn(cx, yb, h) {
    return C.shadowEll(cx + 2, yb, 7, 2) + rect(cx - 5, yb - h, 10, h, S.wood, G, LD) + ln(cx - 5, yb - h * 0.3, cx + 5, yb - h * 0.3, S.gray, 1.1) +
      ln(cx - 5, yb - h * 0.75, cx + 5, yb - h * 0.75, S.gray, 1.1) + ell(cx, yb - h, 5, 1.6, S.cream2, G, 0.7) + ln(cx, yb - h, cx, yb - h - 12, S.wood3, 1.6) + ln(cx - 4, yb - h - 12, cx + 4, yb - h - 12, S.wood3, 1.6);
  }
  def(K3.speckTile({ id: 'east-common-ground-highpasture-01', name: '高山草甸', kind: 'ground_alpine_meadow', resource: 'livestock', subtype: 'dairy_farm', v: 1,
    base: '#b9c07a', n: 10, cols: [S.leaf, S.leaf2, '#9aa86a'], specks: [S.cream2, S.ochre], tags: ['meadow', 'alpine', 'grass'] }));
  def({ id: 'east-common-site-yakdairy-01', name: '牦牛奶场·挤奶棚与酥油房', category: 'site', kind: 'site_yak_dairy', resource: 'livestock', subtype: 'dairy_farm', facility: null,
    w: 4, d: 3, up: 50, tags: ['yak', 'dairy', 'milking', 'butter_churn', 'prayer_flags'], roof: 'flat_mud',
    note: '后排平顶石墙酥油房（门旁打酥油木桶、屋顶晒奶渣），屋前风马彩旗；左前石墙牦牛圈与挤奶人；右前奶桶、奶渣竹匾；乳品无对应 FacilityKind',
    draw: function (W, D, r, id) {
      var o = K2.pad(4, 4, W - 4, D - 4, '#b9c07a', 0.4);
      // 酥油房：石墙平顶
      o += C.shadow([[150, 0], [158, 4], [158, 52], [150, 48]]);
      o += rect(60, 4, 90, 44, S.cream, G, LD);
      for (var y = 10; y < 48; y += 7) o += ln(60, y, 150, y, S.gray3, 0.7, C.op(0.7));
      o += rect(56, -4, 98, 8, S.brown, G, LD) + rect(56, -4, 98, 3, S.brown2, null, 0);
      o += rect(98, 20, 14, 28, S.brown, G, LD) + rect(72, 16, 12, 10, S.navy, G, 0.8) + rect(126, 16, 12, 10, S.navy, G, 0.8);
      o += path('M72 16 l6 -4 l6 4', null, S.vermil, 1.4) + path('M126 16 l6 -4 l6 4', null, S.vermil, 1.4);
      o += ell(80, -6, 12, 2.6, S.thatch, G, 0.7) + ell(80, -6.4, 9, 1.6, S.cream2, null, 0);
      o += churn(120, 52, 18);
      // 风马彩旗绳
      o += K.post(16, -20, 40, 2.4) + K.post(184, -18, 44, 2.4) + path('M16 -16 Q100 6 184 -14', null, S.wood3, 0.8);
      var FC = [S.navy2, S.cream2, S.vermil, S.leaf, S.ochre];
      for (var i = 0; i < 14; i++) { var t = (i + 0.5) / 14, fx = 16 + 168 * t, fy = -16 + 2 * t + 20 * t * (1 - t) * 2 * 0.98; if (fx > 56 && fx < 154) continue; o += rect(fx - 3, fy, 6, 7, FC[i % 5], G, 0.4); }
      // 左前石墙牛圈 + 牦牛 + 挤奶人
      o += rect(8, 76, 104, 4, S.gray3, G, 0.8);
      o += A.yak(30, 100, 1) + A.yak(78, 96, -1) + A.yak(52, 124, 1, 18);
      o += circ(98, 112, 3.4, S.cream, G, 0.8) + rect(94, 115, 8, 8, S.vermil, G, 0.8) + milkPail(92, 128, 8);
      o += rect(8, 134, 104, 5, S.gray3, G, 0.8) + rect(8, 76, 4, 62, S.gray3, G, 0.8);
      // 右前：奶桶与奶渣竹匾
      o += milkPail(138, 120, 12) + milkPail(156, 124, 10);
      o += ell(170, 104, 15, 4.6, S.thatch, G, LD) + ell(170, 103.6, 11, 3, S.cream2, null, 0);
      for (i = 0; i < 6; i++) o += circ(162 + i * 3.2, 103 + (i % 2), 0.9, S.ochre, null, 0);
      return o;
    } });
  def({ id: 'east-common-prop-dairy-churn-01', name: '打酥油桶', category: 'prop', kind: 'prop_butter_churn', resource: 'livestock', subtype: 'dairy_farm', facility: null,
    w: 1, d: 1, up: 12, tags: ['churn', 'butter'],
    draw: function () { return churn(18, 42, 26) + milkPail(36, 44, 11); } });
  def({ id: 'east-common-prop-dairy-yak-01', name: '牦牛', category: 'prop', kind: 'prop_yak', resource: 'livestock', subtype: 'dairy_farm', facility: null,
    w: 1, d: 1, up: 2, tags: ['animal', 'yak'],
    draw: function () { return A.yak(22, 38, 1, 22); } });
  def({ id: 'east-common-prop-dairy-cheesemat-01', name: '晒奶渣竹匾', category: 'prop', kind: 'prop_cheese_mat', resource: 'livestock', subtype: 'dairy_farm', facility: null,
    w: 1, d: 1, up: 8, tags: ['dried_curd', 'drying'],
    draw: function (W, D, r) {
      var o = K2.bar(10, 42, 14, 26, 1.2, S.wood3) + K2.bar(38, 42, 34, 26, 1.2, S.wood3) + ell(24, 26, 20, 6, S.thatch, G, LD) + ell(24, 25.6, 15, 4, S.cream2, null, 0);
      for (var i = 0; i < 10; i++) o += rect(12 + r() * 22, 23 + r() * 4, 2, 1.6, S.ochre, null, 0);
      return o;
    } });

  // ---------------- 猪圈 ----------------
  def({ id: 'east-common-site-pigfarm-01', name: '猪圈·猪舍与泔水缸', category: 'site', kind: 'site_pig_farm', resource: 'livestock', subtype: 'pig_farm', facility: null,
    w: 3, d: 3, up: 44, tags: ['pigs', 'sty', 'swill', 'mud'], roof: 'monopitch',
    note: '后排土坯单坡猪舍（三个低矮舍门），前方石砌矮墙围泥圈、石食槽，五头猪；右前泔水缸与喂猪木勺；无对应 FacilityKind',
    draw: function (W, D, r, id) {
      var o = K2.pad(4, 4, W - 4, D - 4, '#b08a58', 0.5);
      o += C.shadow([[132, 8], [140, 12], [140, 50], [132, 46]]);
      o += rect(12, 8, 120, 40, S.earth, G, LD);
      [30, 72, 114].forEach(function (x) { o += path('M' + (x - 8) + ' 48 L' + (x - 8) + ' 34 Q' + x + ' 28 ' + (x + 8) + ' 34 L' + (x + 8) + ' 48 Z', '#3a2a22', G, 0.8); });
      o += poly([[6, 10], [138, 10], [140, -14], [4, -14]], S.thatch, G, LD);
      for (var x = 8; x < 138; x += 5) o += ln(x, -12, x + 0.5, 9, S.thatch2, 0.8, C.op(0.7));
      o += ln(4, -14, 140, -14, S.wood3, 2.4);
      // 泥圈
      o += ell(64, 96, 50, 22, '#8f6b40', null, 0, C.fop(0.5)) + ell(80, 102, 14, 5, S.water, null, 0, C.fop(0.6));
      o += K2.box(36, 92, 76, 6, 8, S.gray2, S.gray) + rect(38, 69, 52, 4, '#c9a26a', null, 0);
      o += A.pig(30, 92, 1) + A.pig(102, 90, -1) + A.pig(48, 112, 1) + A.pig(76, 120, -1, 14) + A.pig(104, 114, 1, 11);
      // 前石矮墙（中留门）
      o += rect(8, 128, 50, 8, S.gray3, G, LD) + rect(78, 128, 52, 8, S.gray3, G, LD) + rect(8, 54, 6, 82, S.gray3, G, LD) + rect(124, 54, 6, 82, S.gray3, G, LD);
      for (x = 14; x < 130; x += 10) if (x < 58 || x > 78) o += ln(x, 128, x, 136, S.gray, 0.7);
      // 泔水缸 + 木勺
      o += K3.jar(134, 136, 14, 16, S.brown2, null) + ell(134, 120, 5, 1.4, '#c9a26a', null, 0) + K2.bar(130, 118, 140, 104, 1.2, S.wood3);
      return o;
    } });
  def({ id: 'east-common-prop-pig-trough-01', name: '石猪槽', category: 'prop', kind: 'prop_pig_trough', resource: 'livestock', subtype: 'pig_farm', facility: null,
    w: 1, d: 1, up: 0, tags: ['trough', 'stone'],
    draw: function () { return C.shadow([[6, 40], [46, 40], [46, 45], [8, 45]]) + K2.box(4, 44, 42, 8, 10, S.gray2, S.gray) + rect(7, 26, 34, 5, '#c9a26a', null, 0); } });
  def({ id: 'east-common-prop-pig-piglets-01', name: '猪仔', category: 'prop', kind: 'prop_piglets', resource: 'livestock', subtype: 'pig_farm', facility: null,
    w: 1, d: 1, up: 0, tags: ['animal', 'pig'],
    draw: function () { return A.pig(16, 24, 1, 15) + A.pig(34, 32, -1, 10) + A.pig(18, 42, 1, 10) + A.pig(36, 44, -1, 11); } });
  def({ id: 'east-common-prop-pig-swilljar-01', name: '泔水缸', category: 'prop', kind: 'prop_swill_jar', resource: 'livestock', subtype: 'pig_farm', facility: null,
    w: 1, d: 1, up: 4, tags: ['swill', 'jar'],
    draw: function () { return K3.jar(20, 42, 20, 22, S.brown2, null) + ell(20, 21, 7, 1.8, '#c9a26a', null, 0) + K2.bar(26, 22, 40, 2, 1.3, S.wood3) + K2.basket(38, 44, 10, 8, S.leaf2, S.leaf); } });

  var scenes = [
    { key: 'cattle_ranch', title: '耕牛牛栏（livestock / cattle_ranch）',
      ground: [['east-common-ground-muddyyard-01', 2, 3, 5, 3], ['east-common-ground-muddyyard-01', 7, 4, 2, 2]],
      road: [[5, 6], [5, 7], [6, 6], [7, 6], [8, 6], [9, 6]],
      site: ['east-common-site-cattlebarn-01', 2, 2],
      props: [['east-common-prop-cattle-ox-01', 7, 3], ['east-common-prop-cattle-plough-01', 1, 4], ['east-common-prop-cattle-trough-01', 7, 4], ['east-common-prop-cattle-ox-01', 1, 6]] },
    { key: 'dairy_farm', title: '牦牛奶场（livestock / dairy_farm）',
      ground: [['east-common-ground-highpasture-01', 0, 0, 10, 8]],
      road: [[4, 5], [4, 6], [4, 7]],
      site: ['east-common-site-yakdairy-01', 2, 2],
      props: [['east-common-prop-dairy-churn-01', 6, 3], ['east-common-prop-dairy-yak-01', 1, 5], ['east-common-prop-dairy-yak-01', 7, 5], ['east-common-prop-dairy-cheesemat-01', 7, 2], ['east-common-prop-dairy-yak-01', 2, 6]] },
    { key: 'pig_farm', title: '猪圈（livestock / pig_farm）',
      ground: [['east-common-ground-muddyyard-02', 3, 2, 3, 3], ['east-common-ground-muddyyard-01', 6, 3, 2, 2]],
      road: [[4, 5], [4, 6], [4, 7]],
      site: ['east-common-site-pigfarm-01', 3, 2],
      props: [['east-common-prop-pig-trough-01', 6, 3], ['east-common-prop-pig-piglets-01', 7, 4], ['east-common-prop-pig-swilljar-01', 2, 4], ['east-common-prop-pig-piglets-01', 5, 5]] }
  ];
  return { all: function () { return defs.map(C.make); }, scenes: scenes };
});
