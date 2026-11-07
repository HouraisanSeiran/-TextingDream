/*
 * 织梦 · east-ground · 摆件：石作与器物（湖石 ×3、石灯笼、小石狮、太平缸、水缸 ×2、石桌石凳、拴马桩、土地庙、灯笼柱）
 * def 格式同 props-plants.js。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./prop-kit.js'));
  else root.TownArtEG_propsStone = factory(root.TownArtEG_core, root.TownArtEG_kit);
})(this, function (K, P) {
  'use strict';
  var C = K.C, f = K.f, mix = K.mix, G = P.G, G2 = P.G2, defs = [];

  defs.push({
    kind: 'taihu_rock', name: '湖石', tags: ['rock', 'garden', 'taihu'],
    variants: [{ w: 16, h: 30, holes: 3 }, { w: 22, h: 20, holes: 2 }, { w: 12, h: 38, holes: 4 }],
    draw: function (r, v) {
      var s = K.ell(24, -14, v.w * 0.75, 3, mix(C.grass, C.rockD, 0.3), G, 0.4) + P.rock(24, -14, v.w, v.h, r, v.holes);
      if (v.w > 18) s += P.rock(35, -11, 8, 9, r, 1);
      return s;
    }
  });

  defs.push({
    kind: 'stone_lantern', name: '石灯笼', tags: ['stone', 'lantern', 'temple', 'garden'], variants: [{}],
    draw: function () {
      var s = P.shade(26, -14, 7);
      s += P.box(18, 30, -14, 3, 4, C.rock) + K.rect(22, -33, 4, 16, C.rock, G, 0.8);
      s += P.box(17, 31, -33, 3, 4, C.rockL);
      s += K.rect(18.5, -44, 11, 9, C.rock, G, 0.8) + K.rect(21, -42, 6, 5, C.ochreL, G, 0.5) + K.rect(23.4, -42, 1.2, 5, C.orange);
      s += K.path('M14 -44Q24 -47 34 -44L31 -49Q24 -52 17 -49Z', C.rockD, G, 0.8) + K.ell(24, -51.5, 2.4, 2.6, C.rockL, G, 0.6);
      return s;
    }
  });

  defs.push({
    kind: 'stone_lion', name: '小石狮', tags: ['stone', 'guardian', 'gate', 'pair'],
    variants: [{ dir: 1 }, { dir: -1 }],
    draw: function (r, v) {
      var d = v.dir, s = P.shade(26, -12, 9), cx = 24;
      s += P.box(15, 33, -12, 4, 5, C.rock);
      // 蹲身：后腿团块 + 前胸 + 前腿
      s += K.path('M' + f(cx - 7 * d) + ' -16Q' + f(cx - 9 * d) + ' -26 ' + f(cx - 2 * d) + ' -27L' + f(cx + 5 * d) + ' -24L' + f(cx + 6 * d) + ' -16Z', C.rock, G, 0.8);
      s += K.rect(cx + (d > 0 ? 1 : -5), -22, 4, 6, C.rockL, G, 0.6);
      // 头 + 卷鬃
      s += K.circ(cx + 2 * d, -31, 6, C.rock, G, 0.8);
      for (var i = 0; i < 5; i++) s += K.circ(cx + 2 * d + Math.cos(i * 1.25 + 0.3) * 4.6, -31 + Math.sin(i * 1.25 + 0.3) * 4.6, 1.3, C.rockL, G, 0.35);
      s += K.circ(cx + 4.5 * d, -31.5, 0.9, C.navy) + K.path('M' + f(cx + 2 * d) + ' -28q' + f(2 * d) + ' 1.2 ' + f(4 * d) + ' 0', null, C.vermil, 0.8);
      // 绣球（踩在前爪下）
      s += K.circ(cx + 7 * d, -17.5, 2.4, C.rockL, G, 0.6) + K.line('M' + f(cx + 5 * d) + ' -17.5h' + f(4 * d), C.rockD, 0.5);
      return s;
    }
  });

  defs.push({
    kind: 'taiping_vat', name: '太平缸', tags: ['vat', 'fire_water', 'bronze', 'civic'], variants: [{}],
    draw: function () {
      var s = P.shade(26, -12, 13);
      s += P.box(12, 36, -12, 3, 3, C.rockD) + P.jar(24, -15, 10, 12, 15, mix(C.umber, C.gray, 0.35), C.water, G2);
      s += K.circ(13.5, -24, 2, 'none', G2, 0.9) + K.circ(34.5, -24, 2, 'none', G2, 0.9);
      return s;
    }
  });

  defs.push({
    kind: 'water_jar', name: '水缸', tags: ['vat', 'water', 'household'],
    variants: [{ col: mix(C.umber, C.umberL, 0.4), lid: false }, { col: mix(C.navyL, C.gray, 0.3), lid: true }],
    draw: function (r, v) {
      var s = P.jar(22, -14, 7, 9, 12, v.col, C.water, null);
      if (v.lid) s += K.path('M14 -27Q22 -31 30 -27Q22 -24 14 -27Z', C.bamboo, G, 0.7) + K.line('M15 -27.2H29', C.umber, 0.5, K.sop(0.6)) +
        K.line('M28 -28L36 -38', C.umber, 1) + K.ell(37, -39, 2.6, 1.6, C.wood, G, 0.5);
      else s += P.cyl(35, -13, 3.6, 5, C.wood, null, 0.6) + K.line('M31.4 -16H38.6', C.umber, 0.6);
      return s;
    }
  });

  defs.push({
    kind: 'stone_table', name: '石桌石凳', tags: ['stone', 'furniture', 'courtyard'], variants: [{}],
    draw: function () {
      var s = P.shade(26, -18, 16);
      [[13, -24], [35, -24], [13, -11], [35, -11]].forEach(function (p) { s += P.cyl(p[0], p[1], 3.4, 5, C.rock, C.rockL, 0.6); });
      s += P.cyl(24, -15, 3, 7, C.rock, null, 0.7) + P.cyl(24, -21, 11, 3, C.rock, C.rockL, 0.8);
      s += K.line('M18 -21.5h3M27 -20h4', C.rockD, 0.5, K.sop(0.6));
      // 前排两只凳盖住桌脚
      [[13, -9], [35, -9]].forEach(function (p) { s += P.cyl(p[0], p[1], 3.4, 5, C.rock, C.rockL, 0.6); });
      return s;
    }
  });

  defs.push({
    kind: 'hitching_post', name: '拴马桩', tags: ['stone', 'horse', 'street'], variants: [{}],
    draw: function () {
      var s = P.shade(26, -14, 5);
      s += K.rect(21, -40, 6, 26, C.rock, G, 0.8) + K.rect(20, -44, 8, 5, C.rockL, G, 0.7);
      s += K.circ(24, -48, 3, C.rock, G, 0.7) + K.circ(23.2, -48.8, 1, C.rockL);
      s += K.line('M22 -34h4M22 -26h4', C.rockD, 0.5, K.sop(0.6)) + K.ell(24, -36, 2.4, 1.4, 'none', C.umber, 0.9);
      s += K.path('M26 -36Q33 -30 30 -20Q28 -16 31 -14', null, C.umberL, 0.8);
      return s;
    }
  });

  defs.push({
    kind: 'tudi_shrine', name: '土地庙', tags: ['shrine', 'earth_god', 'roadside', 'religion'], variants: [{}],
    draw: function () {
      var s = P.shade(27, -12, 13);
      s += P.box(12, 36, -12, 4, 4, C.rock);
      s += K.rect(14, -32, 20, 16, C.cream, G, 0.8) + K.rect(19, -29, 10, 13, mix(C.umber, C.navy, 0.3), G, 0.6);
      s += K.circ(24, -24, 2.4, C.ochre, G, 0.4) + K.rect(22, -22, 4, 4, C.vermil);
      s += K.rect(14, -32, 2, 16, C.vermil) + K.rect(32, -32, 2, 16, C.vermil);
      s += K.path('M9 -32Q24 -34 39 -32L41 -36L35 -36Q24 -44 13 -36L7 -36Z', C.gray, G, 0.8) + K.line('M12 -35.5Q24 -38 36 -35.5', C.grayL, 0.8);
      s += K.rect(21, -15, 6, 3, C.umber, G, 0.4) + K.line('M23 -15v-4M25 -15v-3', C.vermil, 0.6) + K.circ(23, -19.5, 0.6, C.ochre);
      return s;
    }
  });

  defs.push({
    kind: 'lantern_post', name: '灯笼柱', tags: ['wood', 'lantern', 'street', 'festival'], variants: [{}],
    draw: function () {
      var s = P.shade(27, -14, 6);
      s += K.rect(22, -66, 4, 52, C.vermil, G, 0.8) + K.rect(20, -17, 8, 4, C.rock, G, 0.6);
      s += K.path('M22 -62H34', null, G, 2.6) + K.path('M22 -62H34', null, C.umber, 1.4);
      s += K.line('M32 -62v3', C.umber, 0.6);
      s += K.ell(32, -53, 5, 6, C.vermil, G2, 0.8) + K.line('M27.6 -53H36.4M32 -59v12', C.orange, 0.6, K.sop(0.8));
      s += K.rect(29.5, -59.8, 5, 1.6, C.ochre, G, 0.4) + K.rect(29.5, -48, 5, 1.6, C.ochre, G, 0.4) + K.line('M32 -46.4v4', C.ochre, 0.8);
      return s;
    }
  });

  return { defs: defs };
});
