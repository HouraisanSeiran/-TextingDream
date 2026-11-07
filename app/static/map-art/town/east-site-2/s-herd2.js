/*
 * 织梦 · east-site-2 · 畜牧（二）：山羊场（livestock / goat_farm）、鸡鸭场（poultry_farm：鸭棚 + 鸭塘）、养蜂场（apiary：木桶蜂箱）、
 * 牧马场（horses / horse_stud：马厩 + 圈马栅）。浏览器挂 window.TownArtES2_herd2，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./kit.js'), require('./kit2.js'), require('./kit3.js'));
  else root.TownArtES2_herd2 = factory(root.TownArtES2_core, root.TownArtES2_kit, root.TownArtES2_kit2, root.TownArtES2_kit3);
})(this, function (C, K, K2, K3) {
  'use strict';
  var S = C.S, f = C.f, poly = C.poly, path = C.path, rect = C.rect, ell = C.ell, circ = C.circ, ln = C.ln;
  var G = S.ink, G2 = S.ink2, LW = S.lw, LD = S.lwd, A = K3.A;
  var HONEY = '#e8a62a';
  var defs = [];
  function def(o) { defs.push(o); }
  /** 鸭子：脚底 (x, y)，朝向 d；swim=true 只画水上半身。 */
  function duck(x, y, d, swim, col) {
    var o = swim ? '' : C.shadowEll(x + 1, y, 4, 1.2) + ln(x - 1, y, x - 1, y - 2, S.orange, 0.8) + ln(x + 1, y, x + 1, y - 2, S.orange, 0.8);
    var by = swim ? y : y - 4;
    o += ell(x, by - 2, 4.6, 2.8, col || S.cream2, G, 0.6) + circ(x + d * 3.6, by - 5.6, 2, col || S.cream2, G, 0.6);
    return o + poly([[x + d * 5.2, by - 6], [x + d * 7.6, by - 5.4], [x + d * 5.2, by - 4.6]], S.orange, null, 0) + circ(x + d * 4, by - 6.2, 0.5, S.navy, null, 0);
  }
  /** 鸡：脚底 (x, y)，朝向 d。 */
  function hen(x, y, d, col) {
    var o = C.shadowEll(x + 1, y, 3.6, 1.1) + ln(x, y, x, y - 2.4, S.orange, 0.8);
    o += ell(x, y - 5, 4, 3, col || S.brown2, G, 0.6) + path('M' + f(x - d * 3.5) + ' ' + f(y - 6) + 'l' + f(-d * 2) + ' -4 l' + f(d * 2) + ' 1z', S.navy, null, 0);
    o += circ(x + d * 3, y - 8.4, 1.9, col || S.brown2, G, 0.6) + circ(x + d * 3, y - 10.6, 1, S.vermil, null, 0);
    return o + poly([[x + d * 4.6, y - 8.8], [x + d * 6.4, y - 8.2], [x + d * 4.6, y - 7.6]], S.ochre, null, 0);
  }
  /** 木桶蜂箱（横放圆桶，前端露截面与巢门）：中心 cx，脚底 yb，长 L，半径 rr。 */
  function hive(cx, yb, L, rr) {
    var cy = yb - rr - 3, o = C.shadowEll(cx + 3, yb, L * 0.6, 2.4);
    o += rect(cx - L / 2 + 2, yb - 3, 3, 3, S.wood3, null, 0) + rect(cx + L / 2 - 5, yb - 3, 3, 3, S.wood3, null, 0);
    o += rect(cx - L / 2, cy - rr, L, rr * 2, S.wood, G, LD);
    o += ln(cx - L / 2 + 4, cy - rr, cx - L / 2 + 4, cy + rr, S.gray, 1) + ln(cx + L / 2 - 4, cy - rr, cx + L / 2 - 4, cy + rr, S.gray, 1);
    o += path('M' + f(cx - L / 2 - 2) + ' ' + f(cy - rr - 1) + 'Q' + f(cx) + ' ' + f(cy - rr - 6) + ' ' + f(cx + L / 2 + 2) + ' ' + f(cy - rr - 1) + 'Z', S.thatch, G, 0.7);
    o += ell(cx + L / 2, cy, rr * 0.4, rr, S.wood2, G, LD) + circ(cx + L / 2, cy + rr * 0.4, 1.3, S.coal, null, 0);
    for (var i = 0; i < 3; i++) o += circ(cx + L / 2 + 3 + i * 2.5, cy - 2 - i * 2.5, 0.9, HONEY, null, 0);
    return o;
  }

  // ---------------- 山羊场 ----------------
  def(K3.speckTile({ id: 'east-common-ground-goathill-01', name: '山坡碎石草地', kind: 'ground_rocky_slope', resource: 'livestock', subtype: 'goat_farm', v: 1,
    base: '#bcae7c', n: 12, cols: ['#9a9284', S.leaf, '#a39a8a'], specks: [S.cream2], tags: ['slope', 'rocky', 'grass'] }));
  def({ id: 'east-common-site-goatfarm-01', name: '山羊场·石崖羊圈', category: 'site', kind: 'site_goat_farm', resource: 'livestock', subtype: 'goat_farm', facility: null,
    w: 4, d: 3, up: 60, tags: ['goat', 'rock_pen', 'cliff', 'milking'], roof: 'gable_thatch',
    note: '背靠灰崖，崖台上站着山羊；崖下茅顶羊舍与石块垒的羊圈，圈里一群山羊；右前挂羊奶桶与盐槽；无对应 FacilityKind',
    draw: function (W, D, r, id) {
      var o = K3.cliff([[0, 40], [0, -40], [44, -56], [90, -46], [140, -60], [192, -44], [192, 40]], id + '-c', '#a39a8a', '#857d70', r);
      o += rect(20, -20, 50, 4, '#bdb5a6', null, 0) + rect(128, -32, 50, 4, '#bdb5a6', null, 0);
      o += A.goat(36, -20, 1, 10) + A.goat(150, -32, -1, 10) + A.goat(166, -32, 1, 9);
      o += K3.house(id + '-h', 96, 172, 48, 26, 10, S.cream, S.thatch, 'thatch', 134);
      // 石垒羊圈
      o += rect(10, 62, 100, 5, S.gray2, G, 0.8) + rect(10, 62, 4, 72, S.gray2, G, 0.8) + rect(106, 62, 4, 72, S.gray2, G, 0.8);
      [[30, 86, 1], [56, 82, -1], [82, 88, 1], [40, 108, -1], [70, 112, 1], [94, 106, -1], [26, 126, 1]].forEach(function (p) { o += A.goat(p[0], p[1], p[2]); });
      o += rect(10, 132, 40, 6, S.gray2, G, 0.8) + rect(70, 132, 40, 6, S.gray2, G, 0.8);
      for (var x = 14; x < 108; x += 10) { o += ln(x, 63, x + 4, 63, S.gray, 0.7); }
      // 右前：盐槽 + 奶桶
      o += poly([[124, 112], [168, 112], [166, 122], [126, 122]], S.wood, G, LD) + rect(127, 110, 38, 3, S.salt, null, 0);
      o += poly([[172, 116], [186, 116], [184, 132], [174, 132]], S.wood, G, LD) + ell(179, 116, 7, 2.2, S.cream2, G, 0.7);
      return o;
    } });
  def({ id: 'east-common-prop-goat-herd-01', name: '山羊群', category: 'prop', kind: 'prop_goat_herd', resource: 'livestock', subtype: 'goat_farm', facility: null,
    w: 1, d: 1, up: 4, tags: ['animal', 'goat'],
    draw: function () { return A.goat(14, 24, 1) + A.goat(34, 30, -1) + A.goat(20, 44, 1, 12); } });
  def({ id: 'east-common-prop-goat-saltlick-01', name: '盐槽', category: 'prop', kind: 'prop_salt_lick', resource: 'livestock', subtype: 'goat_farm', facility: null,
    w: 1, d: 1, up: 0, tags: ['salt', 'trough'],
    draw: function () { return C.shadow([[8, 40], [46, 40], [47, 45], [10, 45]]) + poly([[4, 30], [44, 30], [42, 42], [6, 42]], S.wood, G, LD) + rect(7, 28, 34, 4, S.salt, G, 0.6) + K.rock(36, 22, 6, 3, S.gray3, S.gray2, C.rng(5)); } });
  def({ id: 'east-common-prop-goat-rockperch-01', name: '山羊站石', category: 'prop', kind: 'prop_goat_rock', resource: 'livestock', subtype: 'goat_farm', facility: null,
    w: 1, d: 1, up: 18, tags: ['rock', 'goat'],
    draw: function (W, D, r) { return C.shadowEll(26, 42, 18, 3) + K.rock(24, 34, 18, 6, '#bdb5a6', '#9a9284', r) + A.goat(24, 18, 1, 11); } });

  // ---------------- 鸡鸭场 ----------------
  def(K3.speckTile({ id: 'east-common-ground-poultryyard-01', name: '禽场谷壳地', kind: 'ground_poultry_yard', resource: 'livestock', subtype: 'poultry_farm', v: 1,
    base: '#d2b47a', n: 14, cols: [S.thatch, '#c79c5c', S.cream2], specks: [S.ochre, S.cream2], size: 1.4, tags: ['yard', 'chaff', 'feathers'] }));
  def({ id: 'east-common-site-poultryfarm-01', name: '鸡鸭场·鸭棚鸭塘', category: 'site', kind: 'site_poultry_farm', resource: 'livestock', subtype: 'poultry_farm', facility: null,
    w: 4, d: 3, up: 44, tags: ['duck', 'chicken', 'pond', 'coop'], roof: 'gable_thatch',
    note: '左后茅顶竹编鸡舍（高脚栖架），右侧鸭棚临鸭塘，塘里白鸭游水、斜板上岸；前方竹篱鸡场撒谷喂鸡；无对应 FacilityKind',
    draw: function (W, D, r, id) {
      var o = K2.pad(4, 4, W - 4, D - 4, '#d2b47a', 0.45), i;
      // 鸡舍（高脚）
      o += C.shadow([[78, 8], [86, 12], [86, 50], [78, 46]]);
      o += K.post(16, 30, 50, 2.6) + K.post(76, 30, 50, 2.6);
      o += rect(12, 6, 66, 26, S.thatch, G, LD);
      for (i = 0; i < 9; i++) o += ln(14 + i * 7.4, 7, 14 + i * 7.4, 31, S.thatch2, 0.7);
      o += rect(38, 14, 12, 16, S.brown, G, 0.8) + K2.bar(44, 30, 56, 50, 1.4, S.wood2);
      o += K.roof(id + '-c', 12, 78, -14, 7, 5, S.thatch, 'thatch', 2);
      // 鸭棚 + 鸭塘
      o += K2.water([[96, 44], [186, 40], [190, 96], [100, 100], [92, 74]], id + '-pond', r);
      var inner = '';
      for (i = 0; i < 4; i++) inner += duck(116 + i * 10, 34, i % 2 ? 1 : -1);
      o += K3.shed(id + '-s', 104, 168, 18, 38, 22, S.thatch, 'thatch', inner);
      o += poly([[120, 38], [128, 38], [130, 52], [122, 52]], S.wood2, G, 0.7);
      [[120, 66, 1], [140, 74, -1], [160, 62, 1], [172, 84, -1], [132, 90, 1], [154, 88, 1]].forEach(function (p) { o += duck(p[0], p[1], p[2], true); });
      for (i = 0; i < 3; i++) o += path('M' + (140 + i * 14) + ' ' + (58 + i * 12) + 'q4 -2 8 0', null, S.water2, 1);
      // 前方竹篱鸡场
      o += K3.fence(10, 108, 186, 108, 8, 10, S.leaf2);
      [[24, 124, 1, null], [44, 130, -1, S.cream2], [64, 122, 1, null], [86, 132, -1, S.brown], [110, 126, 1, S.cream2], [36, 140, 1, S.brown2]].forEach(function (p) { o += hen(p[0], p[1], p[2], p[3]); });
      for (i = 0; i < 14; i++) o += circ(50 + r() * 50, 128 + r() * 10, 0.7, S.ochre, null, 0);
      o += circ(140, 124, 3.4, S.cream, G, 0.8) + rect(136, 127, 8, 10, S.vermil, G, 0.8) + K2.basket(154, 138, 10, 7, S.ochre, S.thatch, r);
      return o;
    } });
  def({ id: 'east-common-prop-poultry-coop-01', name: '竹编鸡笼', category: 'prop', kind: 'prop_chicken_coop', resource: 'livestock', subtype: 'poultry_farm', facility: null,
    w: 1, d: 1, up: 6, tags: ['coop', 'bamboo', 'chicken'],
    draw: function () {
      var o = C.shadowEll(27, 43, 18, 3) + path('M6 42 Q6 14 24 12 Q42 14 42 42 Z', S.thatch, G, LD);
      for (var i = 0; i < 5; i++) o += path('M' + (10 + i * 7) + ' 41 Q' + (11 + i * 6.5) + ' 18 ' + (24 + (i - 2) * 2) + ' 13', null, S.thatch2, 0.8);
      o += path('M8 30 q16 -3 32 0', null, S.thatch2, 0.8);
      return o + hen(24, 42, 1, S.brown2) + hen(36, 46, -1, S.cream2);
    } });
  def({ id: 'east-common-prop-poultry-ducks-01', name: '鸭群', category: 'prop', kind: 'prop_duck_flock', resource: 'livestock', subtype: 'poultry_farm', facility: null,
    w: 1, d: 1, up: 0, tags: ['animal', 'duck'],
    draw: function () { return duck(12, 22, 1) + duck(26, 26, 1) + duck(38, 32, -1) + duck(16, 40, 1) + duck(32, 44, -1); } });
  def({ id: 'east-common-prop-poultry-hens-01', name: '鸡群与谷盆', category: 'prop', kind: 'prop_hen_flock', resource: 'livestock', subtype: 'poultry_farm', facility: null,
    w: 1, d: 1, up: 0, tags: ['animal', 'chicken', 'feed'],
    draw: function () {
      return ell(24, 34, 9, 3, S.wood2, G, LD) + ell(24, 33.6, 6, 1.6, S.ochre, null, 0) + hen(10, 26, 1) + hen(38, 28, -1, S.cream2) + hen(14, 44, 1, S.brown) + hen(36, 46, -1);
    } });

  // ---------------- 养蜂场 ----------------
  def(K3.speckTile({ id: 'east-common-ground-flowermeadow-01', name: '油菜花草地', kind: 'ground_flower_meadow', resource: 'livestock', subtype: 'apiary', v: 1,
    base: '#c9c27e', n: 10, cols: [S.leaf, S.leaf2], specks: ['#f2d64a', '#f2d64a', S.cream2], tags: ['meadow', 'flowers', 'bees'],
    under: function (r) { var s = ''; for (var i = 0; i < 6; i++) s += circ(8 + r() * 32, 8 + r() * 32, 2.4, '#f2d64a', null, 0); return s; } }));
  def({ id: 'east-common-site-apiary-01', name: '养蜂场·木桶蜂箱', category: 'site', kind: 'site_apiary', resource: 'livestock', subtype: 'apiary', facility: null,
    w: 4, d: 3, up: 40, tags: ['bees', 'log_hive', 'honey', 'flowers'], roof: 'gable_thatch',
    note: '后排茅顶摇蜜小屋（檐下挂蜜罐），前方两排木架上横放木桶蜂箱（桶头巢门有蜂），周围油菜花丛；戴面纱的养蜂人；无对应 FacilityKind',
    draw: function (W, D, r, id) {
      var o = K2.pad(4, 4, W - 4, D - 4, '#c9c27e', 0.4), i;
      o += K3.house(id + '-h', 52, 140, 32, 28, -10, S.cream, S.thatch, 'thatch', 80);
      o += K3.jar(110, 32, 12, 14, HONEY, S.brown2) + K3.jar(126, 32, 11, 12, HONEY, null);
      o += K3.tree(20, 34, 12, S.leaf3, S.leaf, null, r) + K3.tree(170, 30, 13, S.leaf3, S.leaf, null, r);
      // 两排蜂箱架
      [[64, 3], [104, 4]].forEach(function (row, k) {
        var y = row[0];
        o += rect(20, y - 4, 152, 3, S.wood3, G, 0.7);
        for (i = 0; i < row[1]; i++) o += hive(34 + i * (k ? 38 : 50) + (k ? 0 : 16), y - 3, 26, 6.5);
      });
      // 油菜花丛
      for (i = 0; i < 16; i++) { var fx = 10 + r() * 172, fy = 116 + r() * 22; o += circ(fx, fy, 3, S.leaf, null, 0) + circ(fx - 1, fy - 2, 1.6, '#f2d64a', null, 0) + circ(fx + 1.5, fy - 1, 1.4, '#f2d64a', null, 0); }
      // 养蜂人（面纱斗笠）
      o += ell(152, 82, 7, 2.4, S.thatch, G, 0.7) + path('M146 82 L147 90 L157 90 L158 82 Z', S.cream2, G, 0.6, C.fop(0.85)) + rect(148, 90, 8, 10, S.cream, G, 0.8);
      for (i = 0; i < 10; i++) o += circ(30 + r() * 140, 40 + r() * 60, 0.8, S.coal, null, 0);
      return o;
    } });
  def({ id: 'east-common-prop-apiary-hive-01', name: '木桶蜂箱', category: 'prop', kind: 'prop_log_hive', resource: 'livestock', subtype: 'apiary', facility: null,
    w: 1, d: 1, up: 0, tags: ['bees', 'hive'],
    draw: function () { return rect(4, 30, 40, 3, S.wood3, G, 0.7) + hive(22, 30, 30, 7) + hive(24, 46, 30, 6.5); } });
  def({ id: 'east-common-prop-apiary-honeyjars-01', name: '蜜罐', category: 'prop', kind: 'prop_honey_jars', resource: 'livestock', subtype: 'apiary', facility: null,
    w: 1, d: 1, up: 4, tags: ['honey', 'jars'],
    draw: function () { return K3.jar(14, 32, 13, 15, HONEY, S.brown2) + K3.jar(34, 32, 12, 13, HONEY, S.vermil) + K3.jar(24, 46, 14, 16, HONEY, S.brown2); } });
  def({ id: 'east-common-prop-apiary-flowers-01', name: '油菜花丛', category: 'prop', kind: 'prop_rape_flowers', resource: 'livestock', subtype: 'apiary', facility: null,
    w: 1, d: 1, up: 6, tags: ['flowers', 'bees'],
    draw: function (W, D, r) {
      var o = '';
      for (var i = 0; i < 12; i++) { var x = 6 + r() * 36, y = 12 + r() * 32; o += ln(x, y, x, y - 7, S.leaf3, 0.9) + circ(x, y - 7, 2.6, '#f2d64a', G, 0.4) + circ(x + 2, y - 3, 2, S.leaf, null, 0); }
      return o;
    } });

  // ---------------- 牧马场 ----------------
  def({ id: 'east-common-site-horsestud-01', name: '牧马场·马厩圈马栅', category: 'site', kind: 'site_horse_stud', resource: 'horses', subtype: 'horse_stud', facility: 'stable',
    w: 5, d: 3, up: 50, tags: ['stable', 'paddock', 'horses', 'stud'], roof: 'gable_tile',
    note: '后排青瓦长马厩（五间，红柱木隔栏，栏内马首），右后草料垛；前方大圈马栅里枣红、白、黑马奔走，栅门口牵马人；马厩归 stable',
    draw: function (W, D, r, id) {
      var o = K2.pad(4, 4, W - 4, D - 4, S.earth, 0.45), i;
      var inner = '';
      for (i = 0; i < 5; i++) {
        var x = 30 + i * 32;
        inner += rect(x - 12, 46, 24, 16, S.wood2, G, LD) + ln(x - 12, 52, x + 12, 52, S.wood3, 0.8);
        inner += A.horse(x, 50, i % 2 ? 1 : -1, 14, [S.wood, S.cream2, S.coal2, S.brown2, S.wood][i]);
      }
      o += K3.shed(id + '-s', 12, 180, 30, 62, 32, S.navy2, 'tile', inner);
      o += path('M192 62 Q192 26 208 22 Q226 26 226 62 Z', S.thatch, G, LD) + path('M195 48 q13 -4 28 0', null, S.thatch2, 0.9);
      // 圈马栅
      o += K3.penBack(10, 78, 230, 138, 11);
      o += ell(120, 110, 90, 22, S.earth2, null, 0, C.fop(0.4));
      o += A.horse(50, 104, 1, 18, S.wood) + A.horse(100, 98, -1, 18, S.cream2) + A.horse(150, 108, 1, 19, S.coal2) + A.horse(196, 100, -1, 17, S.brown2) + A.horse(80, 128, 1, 17, S.wood2);
      o += K3.penFront(10, 230, 138, 11, null, 22);
      o += circ(132, 136, 3.4, S.cream, G, 0.8) + rect(128, 139, 8, 0.1, S.teal, null, 0);
      return o;
    } });
  def({ id: 'east-common-prop-horse-mare-01', name: '母马与马驹', category: 'prop', kind: 'prop_mare_foal', resource: 'horses', subtype: 'horse_stud', facility: null,
    w: 1, d: 1, up: 6, tags: ['animal', 'horse', 'foal'],
    draw: function () { return A.horse(20, 34, 1, 20, S.wood) + A.horse(32, 46, -1, 12, S.wood2); } });
  def({ id: 'east-common-prop-horse-saddlerack-01', name: '鞍架', category: 'prop', kind: 'prop_saddle_rack', resource: 'horses', subtype: 'horse_stud', facility: null,
    w: 1, d: 1, up: 6, tags: ['saddle', 'tack'],
    draw: function () {
      var o = C.shadow([[8, 40], [44, 40], [46, 45], [10, 45]]) + K.post(10, 18, 42, 2.4) + K.post(38, 18, 42, 2.4) + rect(6, 16, 36, 4, S.wood3, G, 0.7);
      o += path('M12 16 Q12 4 24 6 Q36 4 36 16 Z', S.vermil, G, LD) + path('M14 12 q10 -4 20 0', null, S.gold2, 0.9) + rect(20, 18, 8, 14, S.navy2, G, 0.7);
      return o + ln(16, 20, 14, 34, S.brown, 1) + ln(32, 20, 34, 34, S.brown, 1);
    } });
  def({ id: 'east-common-prop-horse-trough-01', name: '饮马石槽', category: 'prop', kind: 'prop_water_trough', resource: 'horses', subtype: 'horse_stud', facility: null,
    w: 1, d: 1, up: 0, tags: ['trough', 'water'],
    draw: function () { return C.shadow([[8, 40], [46, 40], [47, 45], [10, 45]]) + K2.box(4, 44, 42, 8, 12, S.gray3, S.gray2) + rect(7, 23, 34, 6, S.water, null, 0); } });

  var scenes = [
    { key: 'goat_farm', title: '山羊场（livestock / goat_farm）',
      ground: [['east-common-ground-goathill-01', 1, 1, 7, 5]], road: [[4, 5], [4, 6], [4, 7]],
      site: ['east-common-site-goatfarm-01', 2, 2],
      props: [['east-common-prop-goat-herd-01', 6, 4], ['east-common-prop-goat-saltlick-01', 1, 4], ['east-common-prop-goat-rockperch-01', 7, 2], ['east-common-prop-goat-herd-01', 2, 6]] },
    { key: 'poultry_farm', title: '鸡鸭场（livestock / poultry_farm）',
      ground: [['east-common-ground-poultryyard-01', 1, 2, 7, 4]], road: [[4, 5], [4, 6], [4, 7]],
      site: ['east-common-site-poultryfarm-01', 2, 2],
      props: [['east-common-prop-poultry-coop-01', 1, 4], ['east-common-prop-poultry-ducks-01', 6, 4], ['east-common-prop-poultry-hens-01', 5, 5], ['east-common-prop-poultry-hens-01', 2, 5]] },
    { key: 'apiary', title: '养蜂场（livestock / apiary）',
      ground: [['east-common-ground-flowermeadow-01', 0, 0, 10, 8]], road: [[4, 5], [4, 6], [4, 7]],
      site: ['east-common-site-apiary-01', 2, 2],
      props: [['east-common-prop-apiary-hive-01', 6, 3], ['east-common-prop-apiary-honeyjars-01', 5, 5], ['east-common-prop-apiary-flowers-01', 1, 5], ['east-common-prop-apiary-flowers-01', 7, 5], ['east-common-prop-apiary-hive-01', 1, 3]] },
    { key: 'horse_stud', title: '牧马场（horses / horse_stud）',
      ground: [['east-common-ground-steppe-01', 0, 0, 10, 8]], road: [[4, 5], [4, 6], [4, 7]],
      site: ['east-common-site-horsestud-01', 2, 2],
      props: [['east-common-prop-horse-mare-01', 8, 4], ['east-common-prop-horse-saddlerack-01', 1, 3], ['east-common-prop-horse-trough-01', 1, 4], ['east-common-prop-horse-mare-01', 6, 6]] }
  ];
  return { all: function () { return defs.map(C.make); }, scenes: scenes };
});
