/*
 * 织梦 · east-site-2 · 硫磺矿（sulfur / open_pit）：火山口边的硫磺坑、炼磺土灶。
 * 浏览器挂 window.TownArtES2_hot，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./kit.js'), require('./kit2.js'), require('./kit3.js'));
  else root.TownArtES2_hot = factory(root.TownArtES2_core, root.TownArtES2_kit, root.TownArtES2_kit2, root.TownArtES2_kit3);
})(this, function (C, K, K2, K3) {
  'use strict';
  var S = C.S, f = C.f, poly = C.poly, path = C.path, rect = C.rect, ell = C.ell, circ = C.circ, ln = C.ln;
  var G = S.ink, G2 = S.ink2, LW = S.lw, LD = S.lwd;
  var SU = '#f2d64a', SU2 = '#d9b62c', SU3 = '#b8922a', VR = '#6e5a52', VR2 = '#57463f', VR3 = '#8a7468';
  var defs = [];
  function def(o) { defs.push(o); }
  /** 炼磺土灶：土坯灶身 + 上扣陶罐 + 前方接磺槽（脚底中点 cx, yb）。 */
  function stove(cx, yb, w) {
    var o = C.shadow([[cx + w / 2, yb - 16], [cx + w / 2 + 8, yb - 12], [cx + w / 2 + 8, yb + 3], [cx + w / 2, yb]]);
    o += K2.box(cx - w / 2, cx + w / 2, yb, 16, 8, S.earth2, S.earth3);
    o += path('M' + f(cx - 5) + ' ' + f(yb) + 'L' + f(cx - 5) + ' ' + f(yb - 8) + 'Q' + f(cx) + ' ' + f(yb - 12) + ' ' + f(cx + 5) + ' ' + f(yb - 8) + 'L' + f(cx + 5) + ' ' + f(yb) + 'Z', '#1d1b20', G, 0.8);
    o += circ(cx, yb - 3.5, 2.4, S.orange, null, 0) + circ(cx, yb - 3, 1.2, S.ochre, null, 0);
    [-0.25, 0.25].forEach(function (t) {
      var x = cx + t * w;
      o += path('M' + f(x - 6) + ' ' + f(yb - 22) + 'Q' + f(x - 7) + ' ' + f(yb - 32) + ' ' + f(x) + ' ' + f(yb - 33) + 'Q' + f(x + 7) + ' ' + f(yb - 32) + ' ' + f(x + 6) + ' ' + f(yb - 22) + 'Z', S.brown2, G, LD);
      o += ell(x, yb - 33, 2.6, 1.1, S.brown, G, 0.6);
    });
    return o + K2.smoke(cx - w * 0.25, yb - 34, 0.7);
  }
  def(K3.speckTile({ id: 'east-common-ground-sulfur-crust-01', name: '火山灰硫磺地', kind: 'ground_volcanic', resource: 'sulfur', subtype: 'open_pit', v: 1,
    base: VR3, n: 14, cols: [VR, VR2, SU2], specks: [SU], tags: ['volcanic', 'ash', 'sulfur'] }));
  def(K3.speckTile({ id: 'east-common-ground-sulfur-crust-02', name: '硫磺结壳地', kind: 'ground_volcanic', resource: 'sulfur', subtype: 'open_pit', v: 2,
    base: VR3, n: 10, cols: [SU, SU2, VR], specks: [S.cream2], tags: ['volcanic', 'sulfur'],
    under: function (r) { return ell(16 + r() * 16, 18 + r() * 12, 10, 5, SU2, null, 0, C.fop(0.55)); } }));

  def({ id: 'east-common-site-sulfur-pit-01', name: '硫磺矿·火山口硫磺坑', category: 'site', kind: 'site_sulfur_pit', resource: 'sulfur', subtype: 'open_pit', facility: 'kiln',
    w: 4, d: 3, up: 64, tags: ['volcano', 'fumarole', 'sulfur_pit', 'smelting_stove'], roof: 'none',
    note: '后方暗紫褐火山锥口冒白烟，锥脚硫磺坑壁结黄色磺壳；前方两座炼磺土灶（扣陶罐升华取磺）；炼磺按窑类归 kiln',
    draw: function (W, D, r, id) {
      var o = K3.cliff([[0, 48], [10, -20], [60, -58], [82, -50], [112, -52], [136, -60], [182, -18], [192, 48]], id + '-v', VR, VR2, r);
      o += path('M60 -58 Q96 -44 136 -60 Q100 -66 60 -58 Z', VR2, G, LD);
      o += K2.smoke(84, -56, 1.3) + K2.smoke(112, -58, 1.0);
      // 硫磺流痕
      [[70, -54, 58, -10], [124, -56, 140, -18], [100, -48, 96, -14]].forEach(function (s) { o += path('M' + s[0] + ' ' + s[1] + 'Q' + (s[0] + s[2]) / 2 + ' ' + (s[1] + s[3]) / 2 + ' ' + s[2] + ' ' + s[3], null, SU2, 3); });
      // 硫磺坑
      o += K2.pit(30, 30, 136, 70, 10, VR2, SU2);
      for (var i = 0; i < 14; i++) o += circ(40 + r() * 86, 46 + r() * 18, 1.6 + r() * 2.2, i % 2 ? SU : SU3, null, 0);
      o += K2.smoke(66, 48, 0.7) + K2.ladder(118, 30, 66, 7);
      o += K2.box(146, 182, 70, 3, 16, SU2, SU3) + K.heap(164, 58, 14, 4, SU, SU2, r, 9);
      // 前方炼磺土灶 + 接磺槽
      o += stove(54, 116, 44) + stove(132, 120, 44);
      o += K2.box(36, 72, 132, 4, 6, SU, SU3) + K2.box(114, 150, 136, 4, 6, SU, SU3);
      o += K2.basket(176, 130, 14, 11, SU, SU2, r);
      return o;
    } });
  def({ id: 'east-common-prop-sulfur-stove-01', name: '炼磺土灶', category: 'prop', kind: 'prop_sulfur_stove', resource: 'sulfur', subtype: 'open_pit', facility: null,
    w: 1, d: 1, up: 30, tags: ['stove', 'smelting', 'sulfur'],
    draw: function () { return stove(24, 42, 40); } });
  def({ id: 'east-common-prop-sulfur-cakes-01', name: '硫磺块垛', category: 'prop', kind: 'prop_sulfur_cakes', resource: 'sulfur', subtype: 'open_pit', facility: null,
    w: 1, d: 1, up: 6, tags: ['sulfur', 'stack'],
    draw: function () {
      var o = C.shadow([[8, 40], [46, 40], [47, 45], [10, 45]]);
      return o + K2.box(6, 26, 42, 9, 7, SU, SU2) + K2.box(24, 44, 42, 9, 7, SU, SU2) + K2.box(14, 34, 26, 9, 7, SU, SU2) + K2.box(18, 32, 10, 7, 5, SU, SU2);
    } });
  def({ id: 'east-common-prop-sulfur-fumarole-01', name: '喷气孔', category: 'prop', kind: 'prop_fumarole', resource: 'sulfur', subtype: 'open_pit', facility: null,
    w: 1, d: 1, up: 30, tags: ['fumarole', 'smoke', 'volcanic'],
    draw: function (W, D, r) {
      var o = ell(24, 38, 16, 6, SU2, G, LD) + ell(24, 37, 9, 3.4, VR2, null, 0);
      for (var i = 0; i < 8; i++) o += circ(12 + r() * 24, 34 + r() * 8, 1.4, SU, null, 0);
      return o + K2.smoke(22, 36, 1.0);
    } });

  var scenes = [{ key: 'sulfur', title: '硫磺矿（sulfur / open_pit）',
    ground: [['east-common-ground-sulfur-crust-01', 0, 0, 10, 4], ['east-common-ground-sulfur-crust-01', 1, 4, 8, 2], ['east-common-ground-sulfur-crust-02', 1, 1, 2, 2], ['east-common-ground-sulfur-crust-02', 7, 2, 2, 2]],
    road: [[5, 5], [5, 6], [5, 7]],
    site: ['east-common-site-sulfur-pit-01', 3, 2],
    props: [['east-common-prop-sulfur-stove-01', 1, 4], ['east-common-prop-sulfur-cakes-01', 7, 5], ['east-common-prop-sulfur-fumarole-01', 1, 1], ['east-common-prop-sulfur-fumarole-01', 8, 2], ['east-common-prop-sulfur-cakes-01', 2, 5]] }];
  return { all: function () { return defs.map(C.make); }, scenes: scenes };
});
