/*
 * 织梦 · east-ground · 水面双网格：自然河岸 bank × 16、条石驳岸 quay × 16，外加驳岸石阶叠加件
 *
 * 水色 = C.water #6cc1b3（与 special-infra 东方码头 / 拱桥水面同色）；水纹用米白 #fbf0d4 短波线，与码头水纹同色。
 * 水纹按周期 48 摆放并在瓦片边环绕，所以按世界坐标对齐，任何相邻瓦片都接得上。
 * 岸壁：只在「水在南、岸在北」的分界上露出（3/4 俯视看得到北岸朝南的那一面），高度随分界朝向连续变化，
 * 在瓦片边中点处由分界方向唯一决定，相邻瓦片一致。岸壁画在水面一侧、瓦片之内。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./grid.js'));
  else root.TownArtEG_water = factory(root.TownArtEG_core, root.TownArtEG_grid);
})(this, function (K, GR) {
  'use strict';
  var C = K.C, f = K.f, mix = K.mix;
  var DARK = mix(C.water, C.teal, 0.55), FOAM = mix(C.water, C.creamL, 0.32);

  // ---------- 水纹（周期 48，世界对齐） ----------
  function waterTex() {
    var s = K.rect(-1, -1, 50, 50, C.water), r = K.rng(4813), d = '', dk = '', cr = '';
    for (var j = 0; j < 6; j++) {
      var y = 4 + j * 8, x0 = (j % 2 ? 15 : 3) + r() * 5;
      for (var n = 0; n < 2; n++) {
        var w = 7 + r() * 5, x = (x0 + n * 24 + r() * 3) % 48, dy = r() * 1.5;
        d += K.wrap(x, y - 2 + dy, w, 3, function (px, py) { return 'M' + f(px) + ' ' + f(py + 2) + 'q' + f(w / 4) + ' -1.4 ' + f(w / 2) + ' 0t' + f(w / 2) + ' 0'; });
      }
    }
    // 小卷浪：一道上扬的浪脊末端卷一个小钩，下面两道平行深色水纹
    [[9, 22], [33, 44], [38, 12]].forEach(function (c) {
      cr += K.wrap(c[0] - 3, c[1] - 6, 14, 10, function (x, y) {
        x += 3; y += 6;
        dk += 'M' + f(x - 2) + ' ' + f(y + 1.6) + 'q5 -2.6 11 0M' + f(x) + ' ' + f(y + 3.4) + 'q4 -1.8 8 0';
        return 'M' + f(x) + ' ' + f(y) + 'Q' + f(x + 3) + ' ' + f(y - 4.6) + ' ' + f(x + 6.6) + ' ' + f(y - 4.2) +
          'Q' + f(x + 8.8) + ' ' + f(y - 3.8) + ' ' + f(x + 8.4) + ' ' + f(y - 2.3) + 'Q' + f(x + 7.8) + ' ' + f(y - 1.2) + ' ' + f(x + 6.6) + ' ' + f(y - 2.1);
      });
    });
    return s + K.line(d, C.creamL, 0.75, K.sop(0.5)) + K.line(dk, DARK, 0.7, K.sop(0.45)) + K.line(cr, C.creamL, 0.85, K.sop(0.7));
  }

  // ---------- 分界线工具 ----------
  function norms(P) {
    return P.map(function (p, i) {
      var a = P[Math.max(0, i - 1)], b = P[Math.min(P.length - 1, i + 1)], dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1;
      return [-dy / L, dx / L];
    });
  }
  function offset(P, dist) { var N = norms(P); return P.map(function (p, i) { return [p[0] + N[i][0] * dist, p[1] + N[i][1] * dist]; }); }
  /** 两端沿切向各外延 e px（瓦片外），描线时笔头不会在瓦片边上收口。 */
  function extend(P, e) {
    var a = P[0], b = P[1], y = P[P.length - 1], z = P[P.length - 2];
    var ta = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1, tz = Math.hypot(y[0] - z[0], y[1] - z[1]) || 1;
    return [[a[0] - (b[0] - a[0]) / ta * e, a[1] - (b[1] - a[1]) / ta * e]].concat(P, [[y[0] + (y[0] - z[0]) / tz * e, y[1] + (y[1] - z[1]) / tz * e]]);
  }
  /** 岸壁多边形：分界往下垂 h·max(0, ny)。 */
  function facePoly(P, H) {
    var N = norms(P), lo = P.map(function (p, i) { return [p[0], p[1] + H * Math.max(0, N[i][1])]; });
    return K.poly(P.concat(lo.reverse()));
  }
  function hashMask(m, k) { return K.rng(7001 + m * 131 + k * 17); }

  // ---------- 岸边小件 ----------
  function pebble(x, y, s) { return K.ell(x, y, 1.7 * s, 1.15 * s, C.rock, C.gold, 0.4) + K.ell(x - 0.4 * s, y - 0.35 * s, 0.8 * s, 0.4 * s, C.rockL); }
  function reeds(x, y, r) {
    var d = '', o = '', lv = '';
    for (var k = 0; k < 4; k++) {
      var bx = x + (k - 1.5) * 1.7 + r() * 0.6, top = y - 8 - r() * 4, ln = (r() - 0.5) * 3;
      d += 'M' + f(bx) + ' ' + f(y) + 'Q' + f(bx + ln * 0.3) + ' ' + f((y + top) / 2) + ' ' + f(bx + ln) + ' ' + f(top);
      if (k % 2 === 0) o += K.ell(bx + ln, top + 1.4, 0.85, 2.1, C.umberL, C.umber, 0.3);
      var sd = k % 2 ? 1 : -1;
      lv += 'M' + f(bx) + ' ' + f(y - 2) + 'q' + f(sd * 2.5) + ' -3 ' + f(sd * 5) + ' -2.2';
    }
    return K.line(d, C.bambooD, 0.8) + K.line(lv, C.leaf, 0.8) + o;
  }
  function calamus(x, y, r) {
    var o = '';
    for (var k = 0; k < 5; k++) {
      var a = -Math.PI / 2 + (k - 2) * 0.32 + (r() - 0.5) * 0.1, L = 7 + r() * 3 - Math.abs(k - 2), tx = x + Math.cos(a) * L, ty = y + Math.sin(a) * L;
      o += K.path('M' + f(x - 0.8) + ' ' + f(y) + 'Q' + f((x + tx) / 2 - 0.9) + ' ' + f((y + ty) / 2) + ' ' + f(tx) + ' ' + f(ty) +
        'Q' + f((x + tx) / 2 + 0.9) + ' ' + f((y + ty) / 2) + ' ' + f(x + 0.8) + ' ' + f(y) + 'Z', k % 2 ? C.leafL : C.leaf, C.gold, 0.25);
    }
    return o;
  }
  function bollard(x, y) {
    return K.shadow(x + 1.6, y + 0.6, 3, 1) + K.rect(x - 2, y - 6, 4, 6, C.stone, C.gold, 0.6) + K.ell(x, y - 6, 2, 0.9, C.rockL, C.gold, 0.5) +
      K.path('M' + f(x + 2) + ' ' + f(y - 3.6) + 'q2.2 0.4 2 2.4', null, C.umber, 0.6);
  }

  return { waterTex: waterTex, norms: norms, offset: offset, extend: extend, facePoly: facePoly, hashMask: hashMask,
    pebble: pebble, reeds: reeds, calamus: calamus, bollard: bollard, DARK: DARK, FOAM: FOAM };
});
