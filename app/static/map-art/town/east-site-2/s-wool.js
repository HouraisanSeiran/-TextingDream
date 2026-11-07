/*
 * 织梦 · east-site-2 · 羊场（wool / sheep_station）：毡房、羊圈、擀毡场。
 * 浏览器挂 window.TownArtES2_wool，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./kit.js'), require('./kit2.js'), require('./kit3.js'));
  else root.TownArtES2_wool = factory(root.TownArtES2_core, root.TownArtES2_kit, root.TownArtES2_kit2, root.TownArtES2_kit3);
})(this, function (C, K, K2, K3) {
  'use strict';
  var S = C.S, f = C.f, poly = C.poly, path = C.path, rect = C.rect, ell = C.ell, circ = C.circ, ln = C.ln;
  var G = S.ink, G2 = S.ink2, LW = S.lw, LD = S.lwd, A = K3.A;
  var defs = [];
  function def(o) { defs.push(o); }
  /** 草场底纹：草簇都落在格内，任意排列无缝。 */
  function pastureTile(v) {
    return { id: 'east-common-ground-steppe-0' + v, name: '草场 ' + v, category: 'ground', kind: 'ground_pasture', resource: 'wool', facility: null,
      variant: v, w: 1, d: 1, up: 0, tags: ['tileable', 'pasture', 'grass'], note: '草簇全在格内，四边都是同一草色，可任意平铺',
      draw: function (W, D, r) {
        var o = rect(-0.5, -0.5, 49, 49, '#cdbf7e'), i;
        for (i = 0; i < 7 + v; i++) {
          var x = 5 + r() * 38, y = 6 + r() * 38;
          o += path('M' + f(x - 3) + ' ' + f(y) + 'q1 -4 1.5 -5M' + f(x) + ' ' + f(y) + 'l0 -6M' + f(x + 3) + ' ' + f(y) + 'q-1 -4 -1.5 -5', null, i % 2 ? S.leaf : S.leaf2, 1);
        }
        if (v === 2) o += circ(14, 34, 1.3, S.cream2, null, 0) + circ(36, 12, 1.3, S.ochre, null, 0);
        return o;
      } };
  }
  def(pastureTile(1)); def(pastureTile(2));

  def({ id: 'east-common-site-sheepstation-01', name: '羊场·毡房羊圈', category: 'site', kind: 'site_sheep_station', resource: 'wool', subtype: 'sheep_station', facility: null,
    w: 4, d: 3, up: 46, tags: ['yurt', 'sheep_pen', 'felt_making', 'pastoral'], roof: 'none',
    note: '后排两座毡房（顶毡带红腰带与天窗圈），左前木栅羊圈，右前擀毡场铺毡卷毡；无对应 FacilityKind（剪毛/擀毡不属于 tannery）',
    draw: function (W, D, r, id) {
      var o = K2.pad(4, 6, W - 4, D - 4, S.earth, 0.45);
      // 后排毡房
      o += K3.yurt(52, 52, 24, 20) + K3.yurt(118, 46, 19, 16);
      // 拴马桩与晾毛绳
      o += K.post(150, 12, 46, 2.6, S.wood) + K.post(182, 14, 48, 2.6, S.wood);
      o += path('M150 18 Q166 26 182 20', null, S.wood3, 0.9);
      [156, 164, 172].forEach(function (x, i) { o += rect(x - 3, 20 + (i === 1 ? 2.5 : 1), 6, 8, i === 1 ? S.ochre : S.cream2, G, 0.7); });
      // 左前：羊圈
      o += K3.penBack(10, 74, 98, 132, 10);
      o += ell(54, 104, 36, 18, S.earth2, null, 0, C.fop(0.5));
      [[30, 92, 1], [52, 88, -1], [74, 96, 1], [40, 112, -1], [64, 116, 1], [84, 112, -1], [24, 124, 1]].forEach(function (p) { o += A.sheep(p[0], p[1], p[2]); });
      o += ell(78, 126, 9, 3, S.wood2, G, LD) + ell(78, 125.4, 6, 1.6, S.water, null, 0);
      o += K3.penFront(10, 98, 132, 10, null, 16);
      // 右前：擀毡场（铺开的毡片 + 毡卷 + 木杖）
      o += poly([[112, 86], [176, 86], [184, 118], [106, 118]], S.cream2, G, LD);
      for (var k = 0; k < 4; k++) o += ln(114 + k * 2, 94 + k * 7, 178 + k * 1.5, 94 + k * 7, S.earth2, 0.8, C.op(0.7));
      o += path('M126 102 q8 -5 16 0 q8 5 16 0', null, S.vermil, 1.4) + path('M126 110 q8 -5 16 0 q8 5 16 0', null, S.teal, 1.2);
      o += C.shadowEll(150, 133, 22, 3) + rect(126, 120, 46, 12, S.cream, G, LD);
      for (k = 0; k < 4; k++) o += ln(132 + k * 11, 120, 132 + k * 11, 132, S.wood3, 1.2);
      o += ell(172, 126, 3.5, 6, S.cream2, G, LD) + path('M172 122 q-2.5 4 0 8', null, S.earth3, 0.7);
      o += K2.bar(118, 136, 186, 116, 1.6, S.wood3);
      return o;
    } });

  def({ id: 'east-common-prop-woolbale-01', name: '羊毛捆', category: 'prop', kind: 'prop_wool_bale', resource: 'wool', facility: null,
    w: 1, d: 1, up: 12, tags: ['wool', 'bale'],
    draw: function () {
      var o = C.shadow([[8, 40], [44, 40], [46, 45], [10, 45]]);
      o += K2.box(6, 26, 42, 13, 6, S.cream2, S.cream) + K2.box(24, 44, 42, 13, 6, S.cream2, S.cream) + K2.box(14, 34, 23, 12, 6, S.cream2, S.cream);
      [[16, 42], [34, 42], [24, 23]].forEach(function (p) { o += ln(p[0], p[1] - 19, p[0], p[1], S.wood3, 1.2); });
      return o;
    } });
  def({ id: 'east-common-prop-feltrack-01', name: '晾毡架', category: 'prop', kind: 'prop_felt_rack', resource: 'wool', facility: null,
    w: 1, d: 1, up: 24, tags: ['felt', 'rack'],
    draw: function () {
      var o = C.shadow([[10, 38], [44, 38], [46, 44], [12, 44]]);
      o += K.post(8, -14, 40, 2.6) + K.post(40, -14, 40, 2.6) + ln(6, -12, 42, -12, S.wood3, 2);
      o += path('M10 -12 L38 -12 L38 18 L31 22 L24 18 L17 22 L10 18 Z', S.cream2, G, LD);
      o += path('M12 2 q6 -4 12 0 q6 4 12 0', null, S.vermil, 1.3) + rect(10, -12, 28, 3, S.teal, null, 0);
      return o;
    } });
  def({ id: 'east-common-prop-sheepflock-01', name: '小羊群', category: 'prop', kind: 'prop_sheep_flock', resource: 'wool', facility: null,
    w: 1, d: 1, up: 0, tags: ['animal', 'sheep'],
    draw: function () { return A.sheep(14, 22, 1, 11) + A.sheep(34, 28, -1, 12) + A.sheep(18, 42, 1, 12) + A.sheep(36, 44, -1, 10); } });

  var scenes = [{ key: 'wool', title: '羊场（wool / sheep_station）', ground: [['east-common-ground-steppe-01', 0, 0, 10, 8], ['east-common-ground-steppe-02', 1, 5, 3, 2], ['east-common-ground-steppe-02', 7, 1, 2, 2]],
    road: [[5, 7], [5, 6], [5, 5], [6, 5], [7, 5], [8, 5], [9, 5]],
    site: ['east-common-site-sheepstation-01', 3, 1], props: [['east-common-prop-woolbale-01', 7, 2], ['east-common-prop-feltrack-01', 8, 3], ['east-common-prop-sheepflock-01', 1, 5], ['east-common-prop-sheepflock-01', 2, 6]] }];
  return { all: function () { return defs.map(C.make); }, scenes: scenes };
});
