/*
 * 织梦 · 东方资源点（east-site）共用部件：棚顶、原木、石块、筐、堆、矿洞口、辘轳等。
 * 坐标都是“地面坐标”：x 向右，y 向下（y 大 = 靠前），高度画成负 y。
 * 浏览器挂 window.TownArtES_kit，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'));
  else root.TownArtES_kit = factory(root.TownArtES_core);
})(this, function (C) {
  'use strict';
  var S = C.S, f = C.f, poly = C.poly, pl = C.pl, path = C.path, rect = C.rect, ell = C.ell, circ = C.circ, ln = C.ln;
  var G = S.ink, G2 = S.ink2, LW = S.lw, LD = S.lwd;

  /**
   * 前坡屋顶（屋脊东西向）：x0..x1 墙宽，ry 屋脊 y，ey 檐口 y，ov 出檐，fill 屋面色，
   * kind = 'thatch'（茅草：密短线）/ 'tile'（瓦垄：竖线），lift 檐角起翘。
   */
  function roof(id, x0, x1, ry, ey, ov, fill, kind, lift) {
    var L = x0 - ov, R = x1 + ov, k = lift == null ? 4 : lift;
    var d = 'M' + f(L + 3) + ' ' + f(ry) + 'L' + f(R - 3) + ' ' + f(ry) + 'L' + f(R) + ' ' + f(ey - k) +
      'Q' + f(R - 5) + ' ' + f(ey) + ' ' + f(R - 12) + ' ' + f(ey) + 'L' + f(L + 12) + ' ' + f(ey) +
      'Q' + f(L + 5) + ' ' + f(ey) + ' ' + f(L) + ' ' + f(ey - k) + 'Z';
    var o = path(d, fill, G, LW), lines = '', x;
    if (kind === 'tile') {
      for (x = L + 4; x < R; x += 4.5) lines += ln(x, ry, x + (x - (L + R) / 2) * 0.06, ey + 1, S.navy, 0.9, C.op(0.55));
    } else {
      var r = C.rng(C.hash(id));
      for (var yy = ry + 3; yy < ey; yy += 3.4) {
        for (x = L + 2 + r() * 4; x < R - 2; x += 5 + r() * 3) lines += ln(x, yy, x + 1.2, yy + 2.6, S.thatch2, 0.9);
      }
    }
    o += C.clip(id + '-rf', path(d, '#000'), lines);
    o += path('M' + f(L + 1) + ' ' + f(ry - 2.5) + 'L' + f(R - 1) + ' ' + f(ry - 2.5), null, G, 3.2);
    o += path('M' + f(L + 1) + ' ' + f(ry - 2.5) + 'L' + f(R - 1) + ' ' + f(ry - 2.5), null, kind === 'tile' ? S.navy : S.thatch2, 1.6);
    return o;
  }
  /** 木柱。 */
  function post(x, yTop, yBot, w, col) {
    w = w || 3;
    return rect(x - w / 2, yTop, w, yBot - yTop, col || S.wood, G, LD) + rect(x - w / 2 - 1, yBot - 1.6, w + 2, 1.6, S.gray3, G, 0.7);
  }
  /** 横躺的原木（沿 x 方向），x0..x1，中心线 cy，半径 rr；右端露截面年轮。 */
  function log(x0, x1, cy, rr, col) {
    var o = rect(x0, cy - rr, x1 - x0, rr * 2, col || S.wood, G, LD);
    o += ln(x0 + 3, cy - rr * 0.35, x1 - 4, cy - rr * 0.35, S.wood3, 0.7, C.op(0.6));
    o += ln(x0 + 6, cy + rr * 0.3, x1 - 7, cy + rr * 0.3, S.wood3, 0.7, C.op(0.5));
    o += ell(x1, cy, rr * 0.55, rr, S.wood2, G, LD) + ell(x1, cy, rr * 0.3, rr * 0.55, null, S.wood3, 0.6);
    return o;
  }
  /** 立着看到的原木截面（原木排的端面）。 */
  function logEnd(cx, cy, rr) {
    return circ(cx, cy, rr, S.wood2, G, LD) + circ(cx, cy, rr * 0.6, null, S.wood3, 0.6) + circ(cx, cy, rr * 0.22, S.wood3, null, 0);
  }
  /** 树桩：截面椭圆 + 一圈树皮。 */
  function stump(cx, cy, rr, hh) {
    hh = hh == null ? 4 : hh;
    return C.shadowEll(cx + 2, cy + 1, rr + 1, rr * 0.45) +
      path('M' + f(cx - rr) + ' ' + f(cy - hh) + 'L' + f(cx - rr) + ' ' + f(cy) + 'Q' + f(cx) + ' ' + f(cy + rr * 0.55) + ' ' + f(cx + rr) + ' ' + f(cy) +
        'L' + f(cx + rr) + ' ' + f(cy - hh) + 'Z', S.wood3, G, LD) +
      ell(cx, cy - hh, rr, rr * 0.5, S.wood2, G, LD) + ell(cx, cy - hh, rr * 0.5, rr * 0.25, null, S.wood3, 0.6);
  }
  /** 不规则石块：rw×rh，顶面亮、前面暗。 */
  function rock(cx, cy, rw, rh, col, col2, r) {
    var a = [], n = 7, i;
    for (i = 0; i < n; i++) {
      var t = Math.PI + i / (n - 1) * Math.PI, k = 0.8 + r() * 0.25;
      a.push([cx + Math.cos(t) * rw * k, cy + Math.sin(t) * rh * 2 * k]);
    }
    a.push([cx + rw * 0.8, cy + rh * 0.25], [cx - rw * 0.8, cy + rh * 0.25]);
    var top = [[cx - rw * 0.6, cy - rh * 0.9], [cx + rw * 0.1, cy - rh * 1.7], [cx + rw * 0.65, cy - rh * 0.8], [cx + rw * 0.05, cy - rh * 0.35]];
    return poly(a, col2 || S.gray, G, LD) + poly(top, col || S.gray2, null, 0);
  }
  /** 一堆块状物（矿石、煤、碎石）：n 个小块从后往前叠。 */
  function heap(cx, cy, rw, rh, col, col2, r, n) {
    var o = path('M' + f(cx - rw) + ' ' + f(cy) + 'Q' + f(cx) + ' ' + f(cy - rh * 2.2) + ' ' + f(cx + rw) + ' ' + f(cy) + 'Z', col2, G, LD);
    n = n || 9;
    for (var i = 0; i < n; i++) {
      var t = i / n, yy = cy - rh * (1.5 - t * 1.3), span = rw * (0.35 + t * 0.55);
      var xx = cx + (r() * 2 - 1) * span, s = 2.2 + r() * 2.2;
      o += poly([[xx - s, yy], [xx - s * 0.3, yy - s], [xx + s, yy - s * 0.4], [xx + s * 0.6, yy + s * 0.5]], i % 2 ? col : col2, G, 0.6);
    }
    return o;
  }
  return { roof: roof, post: post, log: log, logEnd: logEnd, stump: stump, rock: rock, heap: heap };
});
