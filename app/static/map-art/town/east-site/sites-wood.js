/*
 * 织梦 · east-site · 林木类资源点：伐木场（timber）、芦苇荡（reed）。
 * def 格式见 core.js make()；draw 在地面坐标里画，占地 x∈[0,W]、y∈[0,D]，高度画成负 y。
 * 浏览器挂 window.TownArtES_wood，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./kit.js'));
  else root.TownArtES_wood = factory(root.TownArtES_core, root.TownArtES_kit);
})(this, function (C, K) {
  'use strict';
  var S = C.S, f = C.f, poly = C.poly, path = C.path, rect = C.rect, ell = C.ell, ln = C.ln;
  var G = S.ink, LW = S.lw, LD = S.lwd;
  var defs = [];
  function def(o) { defs.push(o); }
  function pad(x0, y0, x1, y1, col, o) { return poly([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], col || S.earth2, null, 0, C.fop(o == null ? 0.5 : o)); }
  /** 粗木条（带金线外框的一笔粗线）。 */
  function bar(x1, y1, x2, y2, w, col) { return ln(x1, y1, x2, y2, G, w + 1.8) + ln(x1, y1, x2, y2, col || S.wood, w); }
  function chips(r, x0, y0, x1, y1, n) {
    var o = '';
    for (var i = 0; i < n; i++) { var x = x0 + r() * (x1 - x0), y = y0 + r() * (y1 - y0); o += ln(x, y, x + 1.5 + r() * 1.5, y - 0.8 + r() * 1.6, S.wood2, 1.1); }
    return o;
  }

  def({ id: 'east-common-site-lumber-01', name: '伐木场·锯木棚', category: 'site', kind: 'site_lumber_shed', resource: 'timber', facility: null,
    w: 3, d: 2, up: 56, tags: ['lumber', 'shed', 'saw', 'logpile'], roof: 'gable_thatch', note: '敞口茅草棚，棚下架两人大锯解木，右侧原木垛；无对应 FacilityKind',
    draw: function (W, D, r, id) {
      var o = pad(2, 8, W - 2, D - 2);
      o += C.shadow([[98, 28], [110, 34], [110, 78], [98, 72]]);
      o += rect(12, 30, 84, 42, S.earth3) + rect(12, 30, 84, 42, S.shadow, null, 0, C.fop(0.25)) + chips(r, 16, 56, 92, 70, 14);
      // 锯架：两副交叉木马 + 原木 + 两人大锯
      [30, 78].forEach(function (x) { o += bar(x - 6, 70, x + 5, 50, 2.2, S.wood3) + bar(x + 6, 70, x - 5, 50, 2.2, S.wood3); });
      o += K.log(20, 88, 52, 6);
      o += rect(53, 34, 2.4, 34, S.gray3, G, 0.8) + bar(46, 34, 62, 34, 2, S.wood2) + bar(46, 68, 62, 68, 2, S.wood2);
      for (var y = 37; y < 66; y += 3) o += ln(55.4, y, 56.6, y + 1.5, S.gray, 0.6);
      [12, 54, 96].forEach(function (x) { o += K.post(x, 28, 72, 3.4); });
      o += K.roof(id, 10, 98, -18, 30, 6, S.thatch, 'thatch', 3);
      // 右侧原木垛（端面朝前）+ 木桩挡
      o += C.shadow([[104, 86], [146, 88], [146, 92], [104, 90]]);
      o += K.post(103, 54, 89, 2.6) + K.post(141, 54, 89, 2.6);
      o += rect(105, 54, 34, 30, S.wood3, G, LD);
      [[110, 83], [122, 83], [134, 83], [116, 72], [128, 72], [122, 61]].forEach(function (p) { o += K.logEnd(p[0], p[1], 6); });
      // 前方劈柴墩 + 斧
      o += K.stump(24, 88, 7, 5);
      o += bar(20, 80, 30, 70, 1.6, S.wood2) + poly([[18, 79], [23, 81], [21, 86], [16, 83]], S.gray3, G, LD);
      o += chips(r, 34, 78, 96, 92, 12);
      return o;
    } });

  def({ id: 'east-common-prop-lumber-slide-01', name: '溜木槽', category: 'prop', kind: 'prop_log_slide', resource: 'timber', facility: null,
    w: 1, d: 1, up: 40, tags: ['lumber', 'chute'], note: '从坡上把原木溜下来的木槽，后高前低',
    draw: function () {
      function P(t, h) { var gx = 8 + 32 * t, gy = 10 + 30 * t, hh = 40 - 38 * t; return [gx + (h || 0), gy - hh]; }
      var o = C.shadow([[10, 12], [16, 12], [46, 42], [40, 44]]), i;
      [0.12, 0.45, 0.8].forEach(function (t) { var gx = 8 + 32 * t, gy = 10 + 30 * t, top = gy - (40 - 38 * t); o += K.post(gx, top + 2, gy, 2.4, S.wood3); });
      var a = P(0, -4), b = P(0, 4), c = P(1, 4), d = P(1, -4);
      o += poly([a, b, c, d], S.wood, G, LW);
      o += ln(a[0] + 1.6, a[1] + 1, d[0] + 1.6, d[1] - 1, S.wood3, 1.1) + ln(b[0] - 1.6, b[1] + 1, c[0] - 1.6, c[1] - 1, S.wood3, 1.1);
      for (i = 1; i < 6; i++) { var p = P(i / 6, -4), q = P(i / 6, 4); o += ln(p[0], p[1], q[0], q[1], S.wood3, 0.6, C.op(0.6)); }
      var u = P(0.34), v = P(0.56);
      o += bar(u[0], u[1], v[0], v[1], 6.5, S.wood2) + ell(v[0], v[1], 3.4, 2.2, S.wood2, G, LD);
      o += K.log(28, 46, 43, 3.6);
      return o;
    } });

  def({ id: 'east-common-prop-lumber-logrow-01', name: '原木排', category: 'prop', kind: 'prop_log_row', resource: 'timber', facility: null,
    w: 1, d: 1, up: 6, tags: ['lumber', 'logpile'], note: '端面朝前的三层金字塔原木垛，两侧木楔挡住',
    draw: function () {
      var o = C.shadow([[6, 46], [44, 44], [48, 48], [10, 50]]);
      // 每根原木：向后延伸的顶面条 + 前端截面；从下层往上层画
      [[[12, 43], [24, 43], [36, 43]], [[18, 33], [30, 33]], [[24, 23]]].forEach(function (row) {
        row.forEach(function (p) {
          o += rect(p[0] - 5.6, p[1] - 22, 11.2, 22, S.wood, G, LD) + ln(p[0] - 2, p[1] - 20, p[0] - 2, p[1] - 4, S.wood3, 0.7, C.op(0.6));
          o += K.logEnd(p[0], p[1], 5.6);
        });
      });
      o += poly([[3, 46], [6, 36], [8, 46]], S.wood3, G, LD) + poly([[41, 46], [44, 36], [46, 46]], S.wood3, G, LD);
      return o;
    } });

  function stumpTile(v) {
    return { id: 'east-common-ground-stumps-0' + v, name: '树桩地 ' + v, category: 'ground', kind: 'ground_stumps', resource: 'timber', facility: null,
      variant: v, w: 1, d: 1, up: 0, tags: ['tileable', 'cleared'], note: '伐后林地：草地底色与 east-ground 黄土底纹同色 #d9c58f，细节离边 ≥5 px，任意排列无缝',
      draw: function (W, D, r) {
        var o = rect(-0.5, -0.5, 49, 49, S.grass), i;
        o += ell(14 + r() * 20, 14 + r() * 20, 10, 6, S.earth, null, 0, C.fop(0.6));
        for (i = 0; i < 9; i++) { var x = 6 + r() * 36, y = 6 + r() * 36; o += ln(x, y, x + 2, y - 3, S.leaf, 1, C.op(0.6)); }
        o += chips(r, 8, 8, 40, 40, 8);
        var pts = v === 1 ? [[15, 18], [33, 34]] : [[30, 14], [13, 32], [36, 38]];
        pts.forEach(function (p) { o += K.stump(p[0], p[1], 4.5 + r() * 1.5, 3); });
        return o;
      } };
  }
  def(stumpTile(1)); def(stumpTile(2));

  return { all: function () { return defs.map(C.make); } };
});
