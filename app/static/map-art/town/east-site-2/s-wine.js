/*
 * 织梦 · east-site-2 · 酒坊（wine / distillery）：酿酒作坊（酒缸成排、酒糟堆、酒旗）、高粱 / 糯米晾晒场。
 * 浏览器挂 window.TownArtES2_wine，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./kit.js'), require('./kit2.js'), require('./kit3.js'));
  else root.TownArtES2_wine = factory(root.TownArtES2_core, root.TownArtES2_kit, root.TownArtES2_kit2, root.TownArtES2_kit3);
})(this, function (C, K, K2, K3) {
  'use strict';
  var S = C.S, f = C.f, poly = C.poly, path = C.path, rect = C.rect, ell = C.ell, circ = C.circ, ln = C.ln;
  var G = S.ink, G2 = S.ink2, LW = S.lw, LD = S.lwd;
  var SG = '#a8402a', SG2 = '#c95f3a', RICE = '#f5ecd0', MASH = '#9a6a3a';
  var defs = [];
  function def(o) { defs.push(o); }
  /** 酒旗上的“酒”字示意：几笔金线（不写真字，只作纹样）。 */
  function mark(x, y) { return ln(x, y, x + 6, y, S.vermil, 1.4) + ln(x + 3, y - 3, x + 3, y + 7, S.vermil, 1.4) + ln(x, y + 5, x + 6, y + 5, S.vermil, 1.2); }
  /** 晒场底纹：夯土 + 竹席 + 铺开的高粱（红）/ 糯米（白）。 */
  function dryTile(v) {
    var grain = v === 1 ? SG : RICE, grain2 = v === 1 ? SG2 : '#e6dcb8';
    return { id: 'east-common-ground-wine-drymat-0' + v, name: v === 1 ? '高粱晒场' : '糯米晒场', category: 'ground', kind: 'ground_drying_floor', resource: 'wine', subtype: 'distillery', facility: null,
      variant: v, w: 1, d: 1, up: 0, tags: ['tileable', 'drying', v === 1 ? 'sorghum' : 'glutinous_rice'], note: '每格一张竹席（席边距格边 3 px），席上粒点全在席内，可任意平铺',
      draw: function (W, D, r) {
        var o = rect(-0.5, -0.5, 49, 49, S.earth) + rect(3, 3, 42, 42, S.thatch, G, 0.7), i;
        for (i = 6; i < 44; i += 5) o += ln(3.5, i, 44.5, i, S.thatch2, 0.6, C.op(0.6));
        o += rect(6, 6, 36, 36, grain2, null, 0, C.fop(0.85));
        for (i = 0; i < 40; i++) o += circ(8 + r() * 32, 8 + r() * 32, 1 + r() * 0.6, grain, null, 0);
        return o;
      } };
  }
  def(dryTile(1)); def(dryTile(2));

  def({ id: 'east-common-site-wine-distillery-01', name: '酒坊·酿酒作坊', category: 'site', kind: 'site_distillery', resource: 'wine', subtype: 'distillery', facility: null,
    w: 4, d: 3, up: 74, tags: ['distillery', 'wine_jars', 'still', 'wine_flag'], roof: 'gable_tile',
    note: '青瓦作坊内砖灶上叠蒸馏甑（天锅冒汽），前檐下三排封泥酒缸，左侧酒糟堆与木锨，门前高杆挂锯齿边酒旗；无对应 FacilityKind',
    draw: function (W, D, r, id) {
      var o = K2.pad(4, 6, W - 4, D - 4, S.earth, 0.45);
      // 作坊：后墙 + 灶 + 甑
      var inner = K2.box(56, 116, 80, 12, 8, S.brown2, S.brown);
      inner += path('M66 60 L66 50 Q86 44 106 50 L106 60 Z', S.wood, G, LD) + ln(66, 55, 106, 55, S.wood3, 1.2) + ell(86, 49, 16, 3.6, S.gray2, G, LD);
      inner += path('M82 80 L82 73 Q86 70 90 73 L90 80 Z', '#1d1b20', G, 0.8) + circ(86, 77, 2.2, S.orange, null, 0);
      inner += K2.bar(106, 54, 130, 64, 1.2, S.gray2) + K3.jar(136, 80, 13, 16, S.brown2, null) + K3.jar(156, 80, 13, 16, S.brown2, null);
      inner += circ(44, 62, 3.6, S.cream, G, 0.8) + rect(40, 65, 8, 11, S.navy2, G, 0.8);
      o += K3.shed(id + '-s', 20, 172, 44, 84, 40, S.navy2, 'tile', inner, S.cream);
      o += K2.smoke(84, -12, 0.9) + K2.smoke(98, -16, 0.7);
      // 前檐下两排酒缸（后排泥封、前排红布封）
      for (var row = 0; row < 2; row++) for (var i = 0; i < 6; i++) {
        var x = 52 + i * 18 + row * 9, yb = 104 + row * 16;
        o += K3.jar(x, yb, 15, 16, S.brown2, row ? S.vermil : S.earth2);
      }
      // 左：酒糟堆 + 木锨
      o += K.heap(22, 122, 18, 6, MASH, '#7d5230', r, 12);
      o += K2.bar(30, 130, 44, 106, 1.4, S.wood3) + poly([[42, 104], [48, 108], [46, 112], [40, 108]], S.wood2, G, 0.6);
      // 右前：酒旗
      o += K3.flag(176, -40, 132, 14, 28, S.cream2, S.teal, mark(180, 4));
      return o;
    } });
  def({ id: 'east-common-prop-wine-jarrow-01', name: '封坛酒缸', category: 'prop', kind: 'prop_wine_jars', resource: 'wine', subtype: 'distillery', facility: null,
    w: 1, d: 1, up: 6, tags: ['wine_jars'],
    draw: function () { return K3.jar(14, 30, 15, 17, S.brown2, S.vermil) + K3.jar(34, 30, 15, 17, S.brown2, S.earth2) + K3.jar(24, 44, 16, 18, S.brown2, S.vermil); } });
  def({ id: 'east-common-prop-wine-mash-01', name: '酒糟堆', category: 'prop', kind: 'prop_mash_heap', resource: 'wine', subtype: 'distillery', facility: null,
    w: 1, d: 1, up: 2, tags: ['mash', 'spent_grain'],
    draw: function (W, D, r) {
      var o = C.shadowEll(26, 42, 19, 3) + K.heap(24, 40, 19, 6, MASH, '#7d5230', r, 12);
      for (var i = 0; i < 8; i++) o += circ(10 + r() * 28, 28 + r() * 10, 0.9, SG2, null, 0);
      return o + K2.bar(36, 44, 46, 20, 1.3, S.wood3) + poly([[44, 18], [49, 21], [47, 25], [42, 22]], S.wood2, G, 0.6);
    } });
  def({ id: 'east-common-prop-wine-flag-01', name: '酒旗杆', category: 'prop', kind: 'prop_wine_flag', resource: 'wine', subtype: 'distillery', facility: null,
    w: 1, d: 1, up: 46, tags: ['wine_flag', 'sign'],
    draw: function () { return C.shadow([[16, 42], [24, 42], [28, 46], [20, 46]]) + K3.flag(16, -44, 44, 22, 30, S.cream2, S.teal, mark(24, -26)); } });
  def({ id: 'east-common-prop-wine-sorghumrack-01', name: '高粱穗晾架', category: 'prop', kind: 'prop_sorghum_rack', resource: 'wine', subtype: 'distillery', facility: null,
    w: 1, d: 1, up: 20, tags: ['sorghum', 'drying_rack'],
    draw: function () {
      var o = C.shadow([[8, 40], [44, 40], [46, 45], [10, 45]]);
      o += K.post(8, -14, 42, 2.4) + K.post(40, -14, 42, 2.4) + ln(6, -10, 42, -10, S.wood3, 2) + ln(6, 12, 42, 12, S.wood3, 2);
      for (var i = 0; i < 6; i++) {
        var x = 11 + i * 5.4;
        o += ln(x, -10, x, -2, S.thatch2, 0.8) + ell(x, 2, 2.4, 5, SG, G, 0.5);
        o += ln(x + 1, 12, x + 1, 19, S.thatch2, 0.8) + ell(x + 1, 23, 2.4, 5, i % 2 ? SG2 : SG, G, 0.5);
      }
      return o;
    } });

  var scenes = [{ key: 'wine', title: '酒坊（wine / distillery）',
    ground: [['east-common-ground-wine-drymat-01', 1, 5, 3, 2], ['east-common-ground-wine-drymat-02', 6, 5, 3, 2]],
    road: [[5, 5], [5, 6], [5, 7]],
    site: ['east-common-site-wine-distillery-01', 3, 2],
    props: [['east-common-prop-wine-jarrow-01', 7, 3], ['east-common-prop-wine-jarrow-01', 8, 4], ['east-common-prop-wine-mash-01', 2, 3], ['east-common-prop-wine-flag-01', 4, 5], ['east-common-prop-wine-sorghumrack-01', 1, 4], ['east-common-prop-wine-sorghumrack-01', 9, 6]] }];
  return { all: function () { return defs.map(C.make); }, scenes: scenes };
});
