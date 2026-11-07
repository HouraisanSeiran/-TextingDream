/*
 * 织梦 · east-ground · 摆件：植物（竹丛 ×3、芭蕉、梅树 ×2、柳树 ×2、松 ×2、菜畦）
 *
 * 每项 { kind, name, variants:[...], fp:[1,1], draw(r, v) }；draw 在摆件局部坐标里画（x∈[0,48]，y=0 前沿地面线，向上为负）。
 * 树根落在格子中央偏前（y ≈ -16），树冠可以伸出占地格往上，但总高不超过 96 px（占地 48 + 上伸 48）。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./prop-kit.js'));
  else root.TownArtEG_propsPlants = factory(root.TownArtEG_core, root.TownArtEG_kit);
})(this, function (K, P) {
  'use strict';
  var C = K.C, f = K.f, mix = K.mix, G = P.G, defs = [];
  var CULM = mix(C.teal, '#6f8a2c', 0.4), CULM2 = mix(C.tealL, '#a9c46a', 0.35);

  // ---------- 竹丛 ----------
  function culm(x, y, h, lean, r) {
    var tx = x + lean, ty = y - h, d = 'M' + f(x) + ' ' + f(y) + 'Q' + f(x + lean * 0.2) + ' ' + f(y - h * 0.5) + ' ' + f(tx) + ' ' + f(ty), s = '', n = '';
    s += K.line(d, G, 2.6) + K.line(d, CULM, 1.6);
    for (var k = 1; k < 5; k++) { var t = k / 5, nx = x + lean * t * t, ny = y - h * t; n += 'M' + f(nx - 1.1) + ' ' + f(ny) + 'h2.2'; }
    s += K.line(n, CULM2, 0.7);
    for (var j = 0; j < 4; j++) {
      var t2 = 0.55 + j * 0.13, lx = x + lean * t2 * t2, ly = y - h * t2, sd = (j % 2 ? 1 : -1) * (lean >= 0 ? 1 : -1);
      for (var q = 0; q < 3; q++) s += P.leaf(lx, ly, (sd > 0 ? 0 : Math.PI) + sd * (0.35 + q * 0.32) + (r() - 0.5) * 0.2, 5.5 + r() * 2, q === 1 ? C.leafL : C.leaf, 1.3);
    }
    return s;
  }
  defs.push({
    kind: 'bamboo', name: '竹丛', tags: ['plant', 'bamboo', 'screen'],
    variants: [{ n: 5, h: 54, w: 14 }, { n: 7, h: 66, w: 20 }, { n: 3, h: 44, w: 9 }],
    draw: function (r, v) {
      var s = P.shade(26, -14, v.w * 0.9), i, cs = [];
      for (i = 0; i < v.n; i++) cs.push([24 + (i - (v.n - 1) / 2) * (v.w * 2 / v.n) + (r() - 0.5) * 2, -12 - r() * 6]);
      cs.sort(function (a, b) { return a[1] - b[1]; });
      cs.forEach(function (c, k) { s += culm(c[0], c[1], v.h * (0.75 + r() * 0.3), (c[0] - 24) * 0.35 + (r() - 0.5) * 4, r); });
      s += K.ell(24, -12, v.w * 0.7, 2.4, mix(C.grass, C.leaf, 0.35), G, 0.5);
      for (i = 0; i < 3; i++) s += P.leaf(16 + i * 7, -11, -Math.PI / 2 + (i - 1) * 0.6, 3.5, C.leafL, 1);
      return s;
    }
  });

  // ---------- 芭蕉 ----------
  defs.push({
    kind: 'plantain', name: '芭蕉', tags: ['plant', 'banana_leaf', 'courtyard'], variants: [{}],
    draw: function (r) {
      var s = P.shade(26, -14, 12) + P.trunk(24, -14, 20, 5, 0.5, mix(C.leaf, C.ochre, 0.3));
      var L = [[-2.6, 24, C.leaf], [-0.5, 26, C.leafL], [-1.9, 22, C.leafD], [-1.2, 25, C.leaf], [-0.15, 20, C.leafL], [-2.95, 18, C.leafD]];
      L.forEach(function (l) {
        var a = l[0], x0 = 24, y0 = -32, tx = x0 + Math.cos(a) * l[1], ty = y0 + Math.sin(a) * l[1] * 0.9 + 6, nx = -Math.sin(a) * 6, ny = Math.cos(a) * 6;
        var d = 'M' + f(x0) + ' ' + f(y0) + 'Q' + f((x0 + tx) / 2 + nx) + ' ' + f((y0 + ty) / 2 + ny - 6) + ' ' + f(tx) + ' ' + f(ty) + 'Q' + f((x0 + tx) / 2 - nx * 0.5) + ' ' + f((y0 + ty) / 2 - ny * 0.5 - 4) + ' ' + f(x0) + ' ' + f(y0) + 'Z';
        s += K.path(d, l[2], G, 0.7) + K.line('M' + f(x0) + ' ' + f(y0) + 'Q' + f((x0 + tx) / 2) + ' ' + f((y0 + ty) / 2 - 4) + ' ' + f(tx) + ' ' + f(ty), C.leafL, 0.6, K.sop(0.8));
      });
      return s;
    }
  });

  // ---------- 梅树 ----------
  defs.push({
    kind: 'plum', name: '梅树', tags: ['plant', 'tree', 'blossom', 'plum'],
    variants: [{ col: '#f3a0a0', lean: 6 }, { col: C.creamL, lean: -7 }],
    draw: function (r, v) {
      var s = P.shade(26, -14, 11), d = 'M24 -14Q' + f(24 + v.lean * 0.2) + ' -30 ' + f(24 + v.lean) + ' -40', br = '';
      br += 'M' + f(24 + v.lean * 0.4) + ' -28q' + f(-v.lean * 1.4) + ' -6 ' + f(-v.lean * 2) + ' -16';
      br += 'M' + f(24 + v.lean) + ' -40q' + f(v.lean * 0.6) + ' -6 ' + f(v.lean * 1.4) + ' -8M' + f(24 + v.lean) + ' -40q' + f(-v.lean * 0.4) + ' -8 ' + f(-v.lean * 0.2) + ' -16';
      br += 'M' + f(24 + v.lean * 0.15) + ' -22q' + f(v.lean * 1.3) + ' -3 ' + f(v.lean * 2) + ' -10';
      s += K.line(d, G, 4.6) + K.line(d, C.umber, 3.2) + K.line(br, G, 2.6) + K.line(br, C.umber, 1.5);
      var tips = [[24 + v.lean * 2.4, -50], [24 - v.lean * 1.6, -44], [24 + v.lean * 1.2, -56], [24 + v.lean * 2.2, -32], [24 - v.lean * 0.4, -60], [24 + v.lean * 0.6, -36]];
      tips.forEach(function (t) {
        for (var k = 0; k < 4; k++) {
          var x = t[0] + (r() - 0.5) * 9, y = t[1] + (r() - 0.5) * 8;
          s += K.circ(x, y, 1.9, v.col, G, 0.4) + K.circ(x, y, 0.6, C.vermil);
        }
      });
      return s + K.ell(24, -13, 6, 2, mix(C.grass, C.umberL, 0.3), G, 0.4);
    }
  });

  // ---------- 柳树 ----------
  defs.push({
    kind: 'willow', name: '柳树', tags: ['plant', 'tree', 'willow', 'waterside'],
    variants: [{ R: 17, h: 34 }, { R: 13, h: 28 }],
    draw: function (r, v) {
      var cy = -14 - v.h, s = P.shade(28, -14, v.R * 0.9) + P.trunk(24, -14, v.h, 6, 2, C.umber);
      s += P.canopy(25, cy, v.R * 0.9, r, C.leafD, C.leaf, 5, 0.55);
      var d = '', d2 = '';
      for (var i = 0; i < 13; i++) {
        var x = 25 - v.R + i * v.R * 2 / 12 + (r() - 0.5) * 2, y0 = cy - 2 + Math.abs(i - 6) * 0.8, L = v.h * (0.55 + r() * 0.3) - Math.abs(i - 6) * 1.6;
        var dd = 'M' + f(x) + ' ' + f(y0) + 'q' + f((x - 25) * 0.12) + ' ' + f(L * 0.5) + ' ' + f((x - 25) * 0.18 + 1) + ' ' + f(L);
        if (i % 2) d += dd; else d2 += dd;
      }
      s += K.line(d + d2, G, 2.2, K.sop(0.8)) + K.line(d, C.leafL, 1.3) + K.line(d2, C.leaf, 1.3);
      return s;
    }
  });

  // ---------- 松 ----------
  defs.push({
    kind: 'pine', name: '松', tags: ['plant', 'tree', 'pine', 'evergreen'],
    variants: [{ tiers: 3, h: 26, lean: 4 }, { tiers: 4, h: 30, lean: -3 }],
    draw: function (r, v) {
      var s = P.shade(28, -14, 13), top = -14 - v.h, d = 'M24 -14Q' + f(24 + v.lean * 0.5) + ' ' + f(-14 - v.h * 0.5) + ' ' + f(24 + v.lean) + ' ' + f(top);
      s += K.line(d, G, 5.4) + K.line(d, mix(C.umber, C.vermil, 0.25), 4) +
        K.line('M23 -20l-1 -4M25.5 -28l1 -3', C.umberL, 0.7);
      for (var t = 0; t < v.tiers; t++) {
        var y = top + 6 - t * 9 + v.tiers * 3, w = 9 + (v.tiers - t) * 2.4 + r() * 2, sd = t % 2 ? 1 : -1, x = 24 + v.lean * 0.8 + sd * (5 + r() * 3);
        var pad = 'M' + f(x - w) + ' ' + f(y) + 'Q' + f(x - w * 0.5) + ' ' + f(y - 6) + ' ' + f(x) + ' ' + f(y - 5.5) + 'Q' + f(x + w * 0.6) + ' ' + f(y - 6) + ' ' + f(x + w) + ' ' + f(y) + 'Q' + f(x) + ' ' + f(y + 2.4) + ' ' + f(x - w) + ' ' + f(y) + 'Z';
        s += K.line('M' + f(24 + v.lean * 0.7) + ' ' + f(y + 2) + 'L' + f(x) + ' ' + f(y - 1), C.umber, 1.4);
        s += K.path(pad, C.leafD, G, 0.9) + K.path('M' + f(x - w * 0.7) + ' ' + f(y - 1.2) + 'Q' + f(x - w * 0.2) + ' ' + f(y - 5) + ' ' + f(x + w * 0.4) + ' ' + f(y - 3.6), null, C.leaf, 2.2);
        var nd = '';
        for (var k = -2; k <= 2; k++) nd += 'M' + f(x + k * w * 0.32) + ' ' + f(y - 0.6) + 'l' + f(k * 0.4) + ' -2.4';
        s += K.line(nd, C.leafL, 0.6, K.sop(0.8));
      }
      return s;
    }
  });

  // ---------- 菜畦 ----------
  defs.push({
    kind: 'veg_bed', name: '菜畦', tags: ['farm', 'vegetable', 'ground_level'], variants: [{}],
    draw: function (r) {
      var s = K.rect(5, -42, 38, 32, mix(C.umberL, C.grass, 0.45), G, 0.8) + K.rect(5, -10, 38, 2.4, mix(C.umber, C.umberL, 0.4));
      for (var row = 0; row < 4; row++) {
        var y = -36 + row * 8;
        s += K.line('M7 ' + f(y + 3) + 'H41', C.umber, 1, K.sop(0.45));
        for (var c = 0; c < 6; c++) {
          var x = 9.5 + c * 6 + (r() - 0.5) * 1.2, col = row % 2 ? C.leaf : C.leafL;
          s += K.ell(x, y + 1.6, 2.4, 1.6, col, G, 0.35) + K.ell(x - 0.5, y + 1, 1.1, 0.7, mix(col, C.creamL, 0.35));
        }
      }
      return s;
    }
  });

  return { defs: defs };
});
