/*
 * 织梦 · east-site-2 · 煤：露天煤场（coal / open_pit：阶梯黑色采坑 + 煤堆 + 运煤轨道）、木炭窑（coal / charcoal_kiln：土包窑 + 柴垛）。
 * 浏览器挂 window.TownArtES2_coal，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./kit.js'), require('./kit2.js'), require('./kit3.js'));
  else root.TownArtES2_coal = factory(root.TownArtES2_core, root.TownArtES2_kit, root.TownArtES2_kit2, root.TownArtES2_kit3);
})(this, function (C, K, K2, K3) {
  'use strict';
  var S = C.S, f = C.f, poly = C.poly, path = C.path, rect = C.rect, ell = C.ell, circ = C.circ, ln = C.ln;
  var G = S.ink, G2 = S.ink2, LW = S.lw, LD = S.lwd, CO = S.coal, CO2 = S.coal2, CO3 = '#6a6d74';
  var defs = [];
  function def(o) { defs.push(o); }
  /** 土包炭窑：半球土窑（脚底中点 cx, yb，半宽 rw，高 h），前开拱形窑门，顶冒烟。 */
  function kilnDome(cx, yb, rw, h, lit) {
    var o = C.shadowEll(cx + 5, yb, rw + 4, rw * 0.28);
    o += path('M' + f(cx - rw) + ' ' + f(yb) + 'Q' + f(cx - rw) + ' ' + f(yb - h * 1.25) + ' ' + f(cx) + ' ' + f(yb - h) + 'Q' + f(cx + rw) + ' ' + f(yb - h * 1.25) + ' ' + f(cx + rw) + ' ' + f(yb) +
      'Q' + f(cx) + ' ' + f(yb + rw * 0.22) + ' ' + f(cx - rw) + ' ' + f(yb) + 'Z', S.earth2, G, LW);
    o += path('M' + f(cx - rw * 0.7) + ' ' + f(yb - h * 0.55) + 'Q' + f(cx) + ' ' + f(yb - h * 0.4) + ' ' + f(cx + rw * 0.7) + ' ' + f(yb - h * 0.55), null, S.earth3, 1, C.op(0.7));
    o += path('M' + f(cx - rw * 0.55) + ' ' + f(yb - h * 0.85) + 'Q' + f(cx - rw * 0.2) + ' ' + f(yb - h * 1.02) + ' ' + f(cx + rw * 0.1) + ' ' + f(yb - h * 0.98), null, S.earth, 1.6);
    o += path('M' + f(cx - 6) + ' ' + f(yb + 1) + 'L' + f(cx - 6) + ' ' + f(yb - 9) + 'Q' + f(cx) + ' ' + f(yb - 15) + ' ' + f(cx + 6) + ' ' + f(yb - 9) + 'L' + f(cx + 6) + ' ' + f(yb + 1) + 'Z', lit ? '#1d1b20' : S.brown, G, 0.9);
    if (lit) o += circ(cx, yb - 4, 2.6, S.orange, null, 0) + circ(cx, yb - 3.5, 1.3, S.ochre, null, 0);
    else for (var i = 0; i < 3; i++) o += ln(cx - 5, yb - 8 + i * 3.5, cx + 5, yb - 8 + i * 3.5, S.earth3, 0.8);
    o += rect(cx + rw * 0.35 - 2.5, yb - h * 1.08, 5, 6, S.earth3, G, 0.7);
    return o + (lit ? K2.smoke(cx + rw * 0.35, yb - h * 1.08, 0.9) : '');
  }
  /** 码好的柴垛：x0..x1，脚底 yb，层数 n。 */
  function woodStack(x0, x1, yb, n) {
    var o = C.shadow([[x0 + 2, yb], [x1 + 6, yb], [x1 + 6, yb + 3], [x0 + 4, yb + 3]]), rr = 2.6;
    for (var k = 0; k < n; k++) for (var x = x0 + rr + (k % 2) * rr; x < x1 - rr + 0.1; x += rr * 2) o += K.logEnd(x, yb - rr - k * rr * 1.75, rr);
    return o;
  }

  def(K3.speckTile({ id: 'east-common-ground-coalyard-dust-01', name: '煤场煤尘地', kind: 'ground_coal_dust', resource: 'coal', subtype: 'open_pit', v: 1,
    base: '#5b5a5c', n: 16, cols: [CO, CO2, CO3], specks: ['#8a8a8e'], tags: ['coal', 'dust'] }));
  def(K3.speckTile({ id: 'east-common-ground-coalyard-dust-02', name: '煤场煤尘地 2', kind: 'ground_coal_dust', resource: 'coal', subtype: 'open_pit', v: 2,
    base: '#5b5a5c', n: 9, cols: [CO, CO3], specks: [S.earth3, '#8a8a8e'], tags: ['coal', 'dust'] }));
  def(K3.speckTile({ id: 'east-common-ground-charcoal-ash-01', name: '炭窑灰土地', kind: 'ground_charcoal_ash', resource: 'coal', subtype: 'charcoal_kiln', v: 1,
    base: '#8f7f6a', n: 12, cols: [CO2, '#6f6253', S.earth3], specks: [S.gray3], tags: ['ash', 'charcoal'] }));

  def({ id: 'east-common-site-coal-openpit-01', name: '露天煤场', category: 'site', kind: 'site_coal_open_pit', resource: 'coal', subtype: 'open_pit', facility: 'mine_head',
    w: 4, d: 3, up: 56, tags: ['open_pit', 'coal_seam', 'rails', 'coal_heap'], roof: 'monopitch',
    note: '黄土坡上剥开三级台阶，台阶断面露出黑亮煤层；轨道斜坡把煤车拉上来，右侧瓦顶过秤棚，前方大煤堆与煤筐；按资源点归 mine_head（露天无井架）',
    draw: function (W, D, r, id) {
      var o = K3.cliff([[0, 70], [0, -40], [50, -54], [120, -48], [192, -56], [192, 70]], id + '-c', S.earth2, S.earth3, r);
      // 三级台阶：每级上沿亮土 + 黑煤层断面
      [[10, -34, 182, -20], [22, -8, 170, 8], [34, 18, 158, 36]].forEach(function (s, i) {
        o += rect(s[0], s[1], s[2] - s[0], 4, S.earth, null, 0);
        o += rect(s[0], s[1] + 4, s[2] - s[0], s[3] - s[1] - 4, CO, G, LD);
        for (var x = s[0] + 6; x < s[2] - 4; x += 9 + r() * 6) o += ln(x, s[1] + 6, x + 4, s[1] + 6, CO3, 1, C.op(0.8));
        o += rect(s[0], s[3], s[2] - s[0], 3, S.earth3, null, 0);
      });
      // 坑底
      o += poly([[34, 39], [158, 39], [150, 62], [42, 62]], CO2, G, LD);
      o += K.heap(70, 58, 16, 4, CO, CO2, r, 9) + K2.ladder(140, -4, 40, 7);
      // 运煤斜轨 + 煤车
      o += K3.rails(110, 40, 112, 132, 13) + K3.cart(111, 96, 26, CO, CO2, r);
      // 右：过秤棚
      var inner = rect(158, 72, 6, 22, S.wood3, G, 0.7) + ln(150, 74, 178, 74, S.wood3, 1.6) + rect(146, 80, 10, 4, S.gray2, G, 0.6) + rect(170, 82, 8, 6, S.gray, G, 0.6);
      o += K3.shed(id + '-s', 140, 188, 72, 100, 30, S.gray2, 'tile', inner);
      // 前：大煤堆 + 煤筐 + 人
      o += K.heap(40, 126, 30, 9, CO, CO2, r, 16);
      o += K2.basket(162, 126, 13, 10, CO2, CO, r) + K2.basket(180, 130, 13, 10, CO, CO2, r);
      o += circ(80, 112, 3.6, S.cream, G, 0.8) + rect(76, 115, 8, 10, S.navy2, G, 0.8) + K2.bar(84, 120, 92, 104, 1.2, S.wood3);
      return o;
    } });
  def({ id: 'east-common-prop-coalyard-heap-01', name: '露天煤堆', category: 'prop', kind: 'prop_coal_heap', resource: 'coal', subtype: 'open_pit', facility: null,
    w: 1, d: 1, up: 4, tags: ['coal', 'heap'],
    draw: function (W, D, r) { return C.shadowEll(26, 42, 20, 3) + K.heap(24, 40, 20, 7, CO, CO2, r, 14) + K2.bar(38, 44, 46, 18, 1.3, S.wood3); } });
  def({ id: 'east-common-prop-coalyard-cart-01', name: '运煤车道', category: 'prop', kind: 'prop_coal_cart', resource: 'coal', subtype: 'open_pit', facility: null,
    w: 1, d: 1, up: 0, tags: ['cart', 'rails', 'coal'],
    draw: function (W, D, r) { return K3.rails(24, 4, 24, 46, 13) + K3.cart(24, 36, 28, CO, CO2, r); } });
  def({ id: 'east-common-prop-coalyard-scale-01', name: '煤筐秤架', category: 'prop', kind: 'prop_coal_scale', resource: 'coal', subtype: 'open_pit', facility: null,
    w: 1, d: 1, up: 18, tags: ['scale', 'basket', 'coal'],
    draw: function (W, D, r) {
      var o = C.shadow([[8, 40], [44, 40], [46, 45], [10, 45]]);
      o += K2.bar(10, 42, 24, -14, 1.6, S.wood) + K2.bar(38, 42, 24, -14, 1.6, S.wood) + ln(8, -10, 42, -12, S.wood3, 1.8);
      o += ln(14, -10, 14, 20, S.wood3, 0.8) + rect(36, -12, 6, 5, S.gray, G, 0.6);
      return o + K2.basket(14, 32, 14, 11, CO, CO2, r) + K2.basket(34, 44, 12, 9, CO2, CO, r);
    } });

  // ---------------- 木炭窑 ----------------
  def({ id: 'east-common-site-charcoal-kiln-01', name: '木炭窑', category: 'site', kind: 'site_charcoal_kiln', resource: 'coal', subtype: 'charcoal_kiln', facility: 'kiln',
    w: 4, d: 3, up: 52, tags: ['charcoal', 'earth_kiln', 'firewood', 'smoke'], roof: 'gable_thatch',
    note: '林边两座土包炭窑（左窑封门焖烧冒烟、右窑开门出炭），后有码好的柴垛，右前茅草炭棚下装炭篓；按窑归 kiln',
    draw: function (W, D, r, id) {
      var o = '';
      [[12, 30, 14], [40, 18, 16], [176, 26, 15]].forEach(function (p) { o += K3.tree(p[0], p[1], p[2], S.leaf3, S.leaf, null, r); });
      o += K2.pad(6, 30, W - 6, D - 4, '#8f7f6a', 0.4);
      o += woodStack(70, 150, 36, 4);
      o += kilnDome(52, 84, 32, 40, true) + kilnDome(128, 92, 28, 34, false);
      // 右窑门口出的炭
      o += K.heap(128, 112, 12, 3.5, CO, CO2, r, 7);
      var inner = rect(158, 96, 28, 6, S.wood2, G, LD);
      inner += K2.basket(164, 96, 10, 8, CO, CO2, r) + K2.basket(180, 96, 10, 8, CO2, CO, r);
      o += K3.shed(id + '-s', 150, 190, 98, 124, 28, S.thatch, 'thatch', inner);
      o += circ(98, 112, 3.6, S.cream, G, 0.8) + rect(94, 115, 8, 10, S.brown2, G, 0.8) + K2.bar(102, 120, 112, 106, 1.2, S.wood3);
      o += K2.basket(28, 130, 13, 10, CO, CO2, r);
      return o;
    } });
  def({ id: 'east-common-prop-charcoal-woodstack-01', name: '炭窑柴垛', category: 'prop', kind: 'prop_firewood_stack', resource: 'coal', subtype: 'charcoal_kiln', facility: null,
    w: 1, d: 1, up: 4, tags: ['firewood', 'stack'],
    draw: function () { return K.post(6, 14, 42, 2.4) + K.post(42, 14, 42, 2.4) + woodStack(7, 41, 42, 6); } });
  def({ id: 'east-common-prop-charcoal-baskets-01', name: '木炭篓', category: 'prop', kind: 'prop_charcoal_baskets', resource: 'coal', subtype: 'charcoal_kiln', facility: null,
    w: 1, d: 1, up: 6, tags: ['charcoal', 'basket'],
    draw: function (W, D, r) { return K2.basket(14, 30, 14, 12, CO, CO2, r) + K2.basket(34, 32, 14, 12, CO2, CO, r) + K2.basket(24, 46, 15, 12, CO, CO2, r); } });
  def({ id: 'east-common-prop-charcoal-smallkiln-01', name: '小炭窑', category: 'prop', kind: 'prop_small_kiln', resource: 'coal', subtype: 'charcoal_kiln', facility: null,
    w: 1, d: 1, up: 30, tags: ['kiln', 'smoke'],
    draw: function () { return kilnDome(24, 42, 20, 26, true); } });

  var scenes = [
    { key: 'coal_open_pit', title: '露天煤场（coal / open_pit）',
      ground: [['east-common-ground-coalyard-dust-01', 2, 4, 5, 2], ['east-common-ground-coalyard-dust-02', 1, 6, 3, 1], ['east-common-ground-coalyard-dust-02', 7, 4, 2, 2]],
      road: [[4, 5], [4, 6], [4, 7]],
      site: ['east-common-site-coal-openpit-01', 2, 2],
      props: [['east-common-prop-coalyard-heap-01', 7, 4], ['east-common-prop-coalyard-cart-01', 4, 5], ['east-common-prop-coalyard-scale-01', 8, 5], ['east-common-prop-coalyard-heap-01', 1, 6], ['east-common-prop-coalyard-heap-01', 2, 5]] },
    { key: 'coal_charcoal', title: '木炭窑（coal / charcoal_kiln）',
      ground: [['east-common-ground-charcoal-ash-01', 2, 3, 5, 3], ['east-common-ground-charcoal-ash-01', 7, 4, 2, 2]],
      road: [[5, 6], [5, 7], [6, 6], [7, 6], [8, 6], [9, 6]],
      site: ['east-common-site-charcoal-kiln-01', 2, 3],
      props: [['east-common-prop-charcoal-woodstack-01', 1, 3], ['east-common-prop-charcoal-woodstack-01', 7, 3], ['east-common-prop-charcoal-baskets-01', 7, 5], ['east-common-prop-charcoal-smallkiln-01', 8, 4], ['east-common-prop-charcoal-smallkiln-01', 1, 5]] }
  ];
  return { all: function () { return defs.map(C.make); }, scenes: scenes };
});
