/*
 * 织梦 · east-ground · 摆件：院落（竹篱笆段 横 / 竖 / 转角、晾衣竹竿、鸡群）
 * def 格式同 props-plants.js。
 * 篱笆段按格拼接：横段沿 y = -24 从 x = 0 通到 48；竖段沿 x = 24 从 y = -48 通到 0；
 * 转角从格心通向东、南两边。相邻格的篱笆在格边上首尾相接。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./prop-kit.js'));
  else root.TownArtEG_propsYard = factory(root.TownArtEG_core, root.TownArtEG_kit);
})(this, function (K, P) {
  'use strict';
  var C = K.C, f = K.f, mix = K.mix, G = P.G, defs = [];
  var POST = mix(C.bamboo, C.umber, 0.25), RAIL = C.bamboo, PH = 13;

  /** 竹桩：(x, y) 脚底。 */
  function post(x, y, h) {
    return K.rect(x - 1.3, y - h, 2.6, h, POST, G, 0.6) + K.ell(x, y - h, 1.3, 0.6, mix(POST, C.creamL, 0.35)) + K.line('M' + f(x - 1.3) + ' ' + f(y - h * 0.5) + 'h2.6', C.umber, 0.5, K.sop(0.6));
  }
  /** 东西向篱笆：x0..x1，地面线 y。两道横竹 + 斜编竹片。 */
  function fenceH(x0, x1, y) {
    var s = K.shadow((x0 + x1) / 2 + 2, y + 1, (x1 - x0) / 2, 1.4), w = '';
    for (var x = x0 - 6; x < x1 + 6; x += 4) w += 'M' + f(x) + ' ' + f(y - 1) + 'L' + f(x + 6) + ' ' + f(y - PH + 2);
    s += K.clip(this.ctx, 'M' + f(x0) + ' ' + f(y - PH + 2) + 'H' + f(x1) + 'V' + f(y - 1) + 'H' + f(x0) + 'Z', K.line(w, mix(RAIL, C.ochre, 0.2), 1.1) + K.line(w, C.umber, 0.3, K.sop(0.5)));
    var rails = 'M' + f(x0) + ' ' + f(y - PH + 3) + 'H' + f(x1) + 'M' + f(x0) + ' ' + f(y - 4) + 'H' + f(x1);
    s += K.line(rails, G, 2.4) + K.line(rails, RAIL, 1.4);
    return s;
  }
  /** 南北向篱笆：沿 x，从 y0 到 y1（屏幕上只看到窄窄一条竖着的篱笆顶 + 一侧）。 */
  function fenceV(x, y0, y1) {
    var s = K.path('M' + f(x + 1) + ' ' + f(y0) + 'H' + f(x + 4) + 'V' + f(y1 + 1) + 'H' + f(x + 1) + 'Z', C.shadow, null, 0, K.op(0.2)), w = '';
    s += K.rect(x - 1, y0 - PH + 3, 2, y1 - y0, mix(RAIL, C.ochre, 0.2), G, 0.5);
    for (var y = y0; y < y1; y += 4) w += 'M' + f(x - 1) + ' ' + f(y - PH + 3) + 'v' + f(PH - 4);
    s += K.line(w, mix(RAIL, C.umber, 0.25), 0.9, K.sop(0.7));
    s += K.line('M' + f(x) + ' ' + f(y0 - PH + 3) + 'V' + f(y1 - PH + 3), G, 2.4) + K.line('M' + f(x) + ' ' + f(y0 - PH + 3) + 'V' + f(y1 - PH + 3), RAIL, 1.4);
    return s;
  }

  defs.push({
    kind: 'bamboo_fence', name: '竹篱笆', tags: ['fence', 'bamboo', 'tileable_segment'],
    variants: [{ seg: 'h', note: '横段（东西向），沿格心 y 通到格子东西两边' }, { seg: 'v', note: '竖段（南北向），沿格心 x 通到格子南北两边' },
      { seg: 'corner', note: '转角，从格心通向东边与南边' }],
    draw: function (r, v) {
      var s = '', ctx = this;
      if (v.seg === 'h') { s += fenceH.call({ ctx: ctx.ctx }, 0, 48, -24); [6, 18, 30, 42].forEach(function (x) { s += post(x, -23, PH + 2); }); }
      else if (v.seg === 'v') { s += fenceV(24, -48, 0); [-42, -30, -18, -6].forEach(function (y) { s += post(24, y, PH + 2); }); }
      else {
        s += fenceV(24, -24, 0) + post(24, -6, PH + 2) + post(24, -18, PH + 2);
        s += fenceH.call({ ctx: ctx.ctx }, 24, 48, -24) + post(24, -24, PH + 4) + post(36, -23, PH + 2);
      }
      return s;
    }
  });

  defs.push({
    kind: 'drying_pole', name: '晾衣竹竿', tags: ['laundry', 'bamboo', 'household'], variants: [{}],
    draw: function () {
      var s = K.shadow(26, -15, 18, 1.6), cl = [[10, C.navyL, 9], [20, C.creamL, 11], [30, C.vermilL, 8], [37, C.tealL, 7]];
      s += K.line('M6 -14L8 -42M6 -42L10 -46M10 -42L6 -46M42 -14L40 -42M38 -46L42 -42M42 -46L38 -42', G, 2.4) +
        K.line('M6 -14L8 -42M6 -42L10 -46M10 -42L6 -46M42 -14L40 -42M38 -46L42 -42M42 -46L38 -42', POST, 1.4);
      cl.forEach(function (c, i) {
        var y = -43, w = c[0] + 6 < 40 ? 7 : 5, x = c[0];
        s += K.path('M' + f(x) + ' ' + f(y) + 'H' + f(x + w) + 'L' + f(x + w + 0.6) + ' ' + f(y + c[2]) + 'Q' + f(x + w / 2) + ' ' + f(y + c[2] + 1.6) + ' ' + f(x - 0.4) + ' ' + f(y + c[2]) + 'Z', c[1], G, 0.6);
        if (i === 1) s += K.line('M' + f(x + 1) + ' ' + f(y + 3) + 'H' + f(x + w - 1), C.vermil, 0.7);
      });
      s += K.path('M5 -43.6Q24 -42 43 -43.6', null, G, 2.6) + K.path('M5 -43.6Q24 -42 43 -43.6', null, RAIL, 1.5);
      return s;
    }
  });

  function hen(x, y, d, col) {
    var s = K.ell(x + 1, y + 0.4, 3.6, 1, C.shadow, null, 0, K.op(0.2));
    s += K.path('M' + f(x - 3.6 * d) + ' ' + f(y - 4) + 'Q' + f(x - 4.4 * d) + ' ' + f(y - 7.6) + ' ' + f(x - 2.4 * d) + ' ' + f(y - 7) + 'Q' + f(x - 0.6 * d) + ' ' + f(y - 1) + ' ' + f(x + 2.6 * d) + ' ' + f(y - 2.6) +
      'Q' + f(x + 3.4 * d) + ' ' + f(y - 6) + ' ' + f(x + 2.4 * d) + ' ' + f(y - 7.6) + 'Q' + f(x + 1 * d) + ' ' + f(y - 6.4) + ' ' + f(x - 3.6 * d) + ' ' + f(y - 4) + 'Z', col, G, 0.5);
    s += K.circ(x + 2.8 * d, y - 8.2, 1.7, col, G, 0.5) + K.path('M' + f(x + 2.6 * d) + ' ' + f(y - 10.6) + 'l' + f(0.6 * d) + ' 1l' + f(0.8 * d) + ' -1', C.vermil, null, 0) +
      K.path('M' + f(x + 4.4 * d) + ' ' + f(y - 8.6) + 'l' + f(1.4 * d) + ' 0.5l' + f(-1.4 * d) + ' 0.4Z', C.ochre) + K.circ(x + 3.2 * d, y - 8.6, 0.4, C.navy);
    s += K.line('M' + f(x) + ' ' + f(y - 2) + 'v2M' + f(x + 1.2 * d) + ' ' + f(y - 2) + 'v2', C.ochre, 0.6);
    return s;
  }
  defs.push({
    kind: 'chickens', name: '鸡群', tags: ['animal', 'poultry', 'farm'], variants: [{}],
    draw: function () {
      var s = K.ell(24, -18, 14, 4, mix(C.grass, C.umberL, 0.25), null, 0, K.op(0.6)), g = '';
      [[14, -24], [20, -16], [33, -21], [28, -14], [38, -15]].forEach(function (p) { g += 'M' + f(p[0]) + ' ' + f(p[1]) + 'h0.8'; });
      s += K.line(g, C.ochreL, 1);
      s += hen(16, -22, 1, C.creamL) + hen(34, -22, -1, C.umberL) + hen(24, -11, 1, mix(C.ochre, C.umberL, 0.4));
      s += K.path('M9 -14q1 -2 2 0q1 -2 2 0', null, C.ochre, 0.8) + K.ell(11, -14.6, 1.6, 1.2, C.ochreL, G, 0.3) + K.ell(41, -10.6, 1.6, 1.2, C.ochreL, G, 0.3);
      return s;
    }
  });

  return { defs: defs };
});
