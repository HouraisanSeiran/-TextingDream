/*
 * 织梦 · east-ground · 摆件：农家与运输（竹筐 ×2、箩筐 ×2、扁担、独轮车、牛车、柴垛 ×2、稻草垛 ×2、晒谷席）
 * def 格式同 props-plants.js。篱笆、晾衣竿、鸡群在 props-yard.js。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./prop-kit.js'));
  else root.TownArtEG_propsFarm = factory(root.TownArtEG_core, root.TownArtEG_kit);
})(this, function (K, P) {
  'use strict';
  var C = K.C, f = K.f, mix = K.mix, G = P.G, defs = [];

  function pile(col, lite) {
    return function (cx, y, rt) { return K.path('M' + f(cx - rt + 1) + ' ' + f(y) + 'Q' + f(cx) + ' ' + f(y - rt * 0.9) + ' ' + f(cx + rt - 1) + ' ' + f(y) + 'Z', col, G, 0.5) + K.ell(cx - 1, y - rt * 0.35, rt * 0.4, rt * 0.15, lite); };
  }
  function veg(cx, y, rt) { var s = ''; for (var k = -1; k <= 1; k++) s += K.circ(cx + k * rt * 0.45, y - 1.6 - (k ? 0 : 1.2), 2.1, k ? C.leaf : C.leafL, G, 0.4); return s; }

  defs.push({
    kind: 'bamboo_basket', name: '竹筐', tags: ['basket', 'bamboo', 'market'],
    variants: [{ load: 'veg' }, { load: 'none', two: true }],
    draw: function (r, v) {
      var s = '';
      if (v.two) s += P.basket(16, -20, 7, 5, 8, C.bamboo, null) + P.basket(31, -13, 8, 5.5, 9, mix(C.bamboo, C.ochre, 0.3), pile(C.ochreL, C.creamL));
      else s += P.basket(24, -15, 9, 6, 11, C.bamboo, veg);
      return s;
    }
  });

  defs.push({
    kind: 'luo_basket', name: '箩筐', tags: ['basket', 'grain', 'round'],
    variants: [{ load: 'grain' }, { load: 'cotton' }],
    draw: function (r, v) {
      var load = v.load === 'grain' ? pile(C.ochre, C.ochreL) : pile(C.creamL, '#ffffff');
      return P.basket(19, -18, 9, 8.5, 8, mix(C.bamboo, C.umberL, 0.25), load) + P.basket(32, -11, 7, 6.5, 6, mix(C.bamboo, C.umberL, 0.25), null);
    }
  });

  defs.push({
    kind: 'carry_pole', name: '扁担', tags: ['pole', 'baskets', 'porter'], variants: [{}],
    draw: function () {
      var s = P.basket(11, -13, 6, 5, 7, C.bamboo, veg) + P.basket(37, -13, 6, 5, 7, C.bamboo, pile(C.vermilL, C.ochreL));
      s += K.line('M11 -20L11 -30M37 -20L37 -30', C.umber, 0.6) + K.line('M7 -20L11 -30L15 -20M33 -20L37 -30L41 -20', C.umber, 0.5, K.sop(0.8));
      s += K.path('M4 -29Q24 -33 44 -29', null, G, 3) + K.path('M4 -29Q24 -33 44 -29', null, C.bamboo, 1.8);
      return s;
    }
  });

  defs.push({
    kind: 'wheelbarrow', name: '独轮车', tags: ['cart', 'wheelbarrow', 'transport'], variants: [{}],
    draw: function () {
      var s = P.shade(26, -12, 15);
      s += K.line('M8 -22L40 -18M8 -16L40 -14', G, 2.6) + K.line('M8 -22L40 -18M8 -16L40 -14', C.wood, 1.4);
      s += K.line('M36 -16l2 5M14 -18l-1 5', C.umber, 1.2);
      s += P.wheel(24, -21, 8, 0.6);
      s += P.box(15, 33, -22, 5, 6, mix(C.wood, C.ochre, 0.3)) + K.line('M15 -24.5H33', C.umber, 0.5, K.sop(0.6));
      s += P.box(17, 23, -27, 4, 3, C.creamL) + P.box(24, 31, -27, 5, 3, C.cream);
      return s;
    }
  });

  defs.push({
    kind: 'ox_cart', name: '牛车', tags: ['cart', 'ox', 'transport', 'animal'], variants: [{}],
    draw: function () {
      var s = P.shade(26, -10, 20), ox = mix(C.umber, C.gray, 0.25);
      // 车厢 + 车轮（右侧）
      s += K.line('M6 -22L30 -20', G, 2.4) + K.line('M6 -22L30 -20', C.wood, 1.3);
      s += P.box(26, 46, -18, 7, 8, C.wood) + K.line('M26 -21.5H46', C.umber, 0.5, K.sop(0.6)) + P.box(28, 44, -25, 4, 3, C.ochreL);
      s += P.wheel(37, -14, 7, 0.55);
      // 牛（左侧，朝左）
      s += K.path('M8 -22Q8 -30 15 -30H25Q29 -29 28 -22Q26 -18 22 -18H12Q8 -18 8 -22Z', ox, G, 0.8);
      s += K.line('M11 -18v-1M11 -18v6M15 -18v6M22 -18v6M26 -19v6', ox, 1.6) + K.line('M10 -12h2M14 -12h2M21 -12h2M25 -12h2', C.navy, 0.8);
      s += K.path('M9 -27Q3 -28 2 -23Q3 -20 7 -21Z', ox, G, 0.7) + K.circ(4.2, -24.6, 0.6, C.creamL);
      s += K.path('M8 -27q-2 -4 -5 -4M8 -27q1 -4 4 -4', null, C.creamL, 1);
      s += K.ell(12, -28, 2.2, 1, mix(ox, C.creamL, 0.3)) + K.path('M27 -24q3 2 2 7', null, ox, 0.8);
      return s;
    }
  });

  defs.push({
    kind: 'woodpile', name: '柴垛', tags: ['firewood', 'fuel', 'household'],
    variants: [{ rows: 3, n: 5 }, { rows: 2, n: 4, bundle: true }],
    draw: function (r, v) {
      var s = P.shade(27, -12, 16), rr = 3.2, x0 = 24 - v.n * rr;
      s += K.rect(x0 - 1, -12 - v.rows * rr * 1.7 - 2, v.n * rr * 2 + 2, v.rows * rr * 1.7 + 2, mix(C.wood, C.umber, 0.4), G, 0.7);
      for (var j = 0; j < v.rows; j++) for (var i = 0; i < v.n - (j === v.rows - 1 && v.rows > 2 ? 1 : 0); i++) {
        var cx = x0 + i * rr * 2 + rr + (j % 2 ? rr * 0.5 : 0), cy = -12 - rr - j * rr * 1.7;
        s += K.circ(cx, cy, rr, C.ochreL, G, 0.6) + K.circ(cx, cy, 1.4, 'none', C.umberL, 0.5) + K.circ(cx, cy, 0.5, C.umber);
      }
      if (v.bundle) s += K.path('M35 -12L41 -30M37 -12L44 -29M39 -12L44 -26', null, C.umberL, 1.2) + K.line('M37 -21h5', C.vermil, 1);
      return s;
    }
  });

  defs.push({
    kind: 'haystack', name: '稻草垛', tags: ['straw', 'farm', 'harvest'],
    variants: [{ h: 30, w: 15 }, { h: 22, w: 18, flat: true }],
    draw: function (r, v) {
      var s = P.shade(28, -12, v.w), t = -12 - v.h, d;
      if (v.flat) d = 'M' + f(24 - v.w) + ' -12Q' + f(24 - v.w - 1) + ' ' + f(t + 6) + ' ' + f(24 - v.w * 0.5) + ' ' + f(t) + 'H' + f(24 + v.w * 0.5) + 'Q' + f(24 + v.w + 1) + ' ' + f(t + 6) + ' ' + f(24 + v.w) + ' -12Z';
      else d = 'M' + f(24 - v.w) + ' -12Q' + f(24 - v.w) + ' ' + f(t + 10) + ' 24 ' + f(t) + 'Q' + f(24 + v.w) + ' ' + f(t + 10) + ' ' + f(24 + v.w) + ' -12Z';
      s += K.path(d, C.straw, G, 0.9);
      var sh = '';
      for (var k = 0; k < 9; k++) { var x = 24 - v.w + 3 + k * (v.w * 2 - 6) / 8, y = -14 - r() * v.h * 0.7; sh += 'M' + f(x) + ' ' + f(y) + 'l' + f((x - 24) * 0.08) + ' 4'; }
      s += K.line(sh, C.strawD, 0.7, K.sop(0.7)) + K.path('M' + f(24 - v.w * 0.6) + ' ' + f(t + v.h * 0.3) + 'Q24 ' + f(t + v.h * 0.15) + ' ' + f(24 + v.w * 0.2) + ' ' + f(t + v.h * 0.25), null, C.ochreL, 1.6);
      s += K.path('M' + f(24 - v.w + 1) + ' ' + f(t + v.h * 0.55) + 'Q24 ' + f(t + v.h * 0.65) + ' ' + f(24 + v.w - 1) + ' ' + f(t + v.h * 0.55), null, C.umber, 0.9);
      if (!v.flat) s += K.path('M22 ' + f(t + 1) + 'l2 -5l2 5', null, C.umber, 1);
      return s;
    }
  });

  defs.push({
    kind: 'drying_mat', name: '晒谷席', tags: ['mat', 'grain', 'drying', 'ground_level'], variants: [{}],
    draw: function (r) {
      var s = K.path('M5 -40H43L45 -9H3Z', mix(C.bamboo, C.cream, 0.35), G, 0.8), w = '';
      for (var k = 1; k < 8; k++) w += 'M' + f(5 - k * 0.25) + ' ' + f(-40 + k * 3.9) + 'H' + f(43 + k * 0.25);
      s += K.line(w, C.umber, 0.4, K.sop(0.35));
      s += K.path('M9 -35Q24 -38 39 -34Q42 -24 38 -14Q24 -12 10 -14Q6 -24 9 -35Z', C.ochre, null, 0) + K.path('M13 -31Q24 -33 34 -30Q36 -24 33 -18Q24 -17 15 -18Q12 -24 13 -31Z', C.ochreL, null, 0);
      var g = '';
      for (var i = 0; i < 26; i++) g += 'M' + f(11 + r() * 26) + ' ' + f(-33 + r() * 18) + 'h0.8';
      s += K.line(g, C.strawD, 0.8, K.sop(0.8)) + K.path('M30 -24l10 -8', null, C.umber, 1.2) + K.rect(38, -34, 6, 2.4, C.wood, G, 0.4);
      return s;
    }
  });

  return { defs: defs };
});
