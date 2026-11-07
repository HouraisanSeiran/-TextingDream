/*
 * 织梦 · east-site · 土石类资源点：采石场（stone）、黏土坑（clay）、玉石矿（gems）。
 * 浏览器挂 window.TownArtES_stone，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./kit.js'), require('./kit2.js'));
  else root.TownArtES_stone = factory(root.TownArtES_core, root.TownArtES_kit, root.TownArtES_kit2);
})(this, function (C, K, K2) {
  'use strict';
  var S = C.S, f = C.f, poly = C.poly, path = C.path, rect = C.rect, ell = C.ell, circ = C.circ, ln = C.ln;
  var G = S.ink, LW = S.lw, LD = S.lwd;
  var defs = [];
  function def(o) { defs.push(o); }

  /** 阶梯采面：从后往前三级台阶状崖面，每级顶面亮、立面暗并刻凿痕。 */
  function cliffSteps(x0, x1, yb, steps, r, top, face) {
    var o = '';
    steps.forEach(function (s, i) {
      var y = yb - s.back, h = s.h, a = x0 + s.inL, b = x1 - s.inR;
      o += rect(a, y - h - 8, b - a, 8, top || '#d3c8b4', G, LD);
      o += rect(a, y - h, b - a, h, face || '#a8998a', G, LW) + rect(a, y - h, 6, h, '#c1b4a2', null, 0);
      for (var k = 0; k < (b - a) / 7; k++) { var x = a + 4 + k * 7 + r() * 2; o += ln(x, y - h + 3, x - 1.5, y - 3, S.brown, 0.8, C.op(0.4)); }
      o += ln(a + 2, y - h * 0.5, b - 2, y - h * 0.5 + 1, S.gray3, 0.7, C.op(0.6));
    });
    return o;
  }

  def({ id: 'east-common-site-quarry-01', name: '采石场·凿石崖面', category: 'site', kind: 'site_quarry_face', resource: 'stone', facility: null,
    w: 4, d: 3, up: 70, tags: ['quarry', 'cliff', 'derrick'], note: '三级阶梯凿石崖面 + 木吊杆，前方石料与凿石人用的木凳；无对应 FacilityKind',
    draw: function (W, D, r, id) {
      var o = K2.pad(0, 0, W, D, S.gray3, 0.35);
      // 后方山体
      o += path('M0 70 L0 -40 Q30 -66 70 -58 Q110 -70 150 -54 Q180 -56 192 -34 L192 70 Z', '#b8ab98', G, LW);
      o += path('M120 -56 Q170 -52 190 -32 L190 70 L150 70 Q160 0 120 -56 Z', '#9c8e7e', null, 0);
      o += path('M20 -40 Q50 -56 80 -48 M118 -56 Q150 -60 170 -44', null, '#d3c8b4', 1.2);
      o += cliffSteps(8, 184, 100, [{ back: 64, h: 54, inL: 0, inR: 0 }, { back: 34, h: 34, inL: 10, inR: 30 }, { back: 10, h: 18, inL: 24, inR: 62 }], r);
      // 木吊杆：立柱 + 斜臂 + 绳 + 吊石
      o += C.shadow([[150, 128], [176, 130], [176, 136], [150, 134]]);
      o += K2.bar(160, 132, 160, 30, 3.4, S.wood3) + K2.bar(160, 40, 120, 10, 2.6, S.wood) + K2.bar(160, 70, 140, 132, 2, S.wood3);
      o += ln(122, 12, 122, 52, S.thatch2, 1.2) + K2.box(114, 130, 66, 10, 5, S.gray3, S.gray2);
      o += K2.wheel(160, 112, 7, 6) + ln(160, 112, 122, 14, S.thatch2, 0.8, C.op(0.7));
      // 前排石料
      o += K2.box(20, 46, 136, 10, 6, S.gray3, S.gray2) + K2.box(50, 70, 136, 10, 6, S.gray3, S.gray2) + K2.box(30, 56, 126, 9, 5, S.gray3, S.gray2);
      o += K.heap(98, 138, 16, 4, S.gray2, S.gray, r, 8);
      return o;
    } });

  def({ id: 'east-common-prop-stone-blocks-01', name: '石料垛', category: 'prop', kind: 'prop_stone_blocks', resource: 'stone', facility: null,
    w: 1, d: 1, up: 14, tags: ['quarry', 'blocks'], note: '凿好的方石料两层码放，木楔垫底',
    draw: function () {
      var o = C.shadow([[6, 44], [46, 42], [48, 47], [8, 48]]);
      o += K2.box(4, 22, 44, 11, 9, S.gray3, S.gray2) + K2.box(24, 44, 44, 11, 9, S.gray3, S.gray2);
      o += K2.box(12, 34, 33, 11, 8, S.gray3, S.gray2) + ln(16, 19, 30, 19, S.navy, 0.7, C.op(0.4));
      return o;
    } });
  def({ id: 'east-common-prop-stone-rubble-01', name: '碎石堆', category: 'prop', kind: 'prop_rubble', resource: 'stone', facility: null,
    w: 1, d: 1, up: 10, tags: ['quarry', 'rubble'],
    draw: function (W, D, r) { return C.shadowEll(26, 44, 20, 4) + K.heap(24, 44, 20, 6, S.gray2, S.gray, r, 12) + K.rock(36, 44, 6, 3, S.gray3, S.gray, r); } });
  def({ id: 'east-common-prop-stone-trolley-01', name: '石料木轮车', category: 'prop', kind: 'prop_stone_cart', resource: 'stone', facility: null,
    w: 1, d: 1, up: 18, tags: ['quarry', 'cart'], note: '独轮推车载一块石料',
    draw: function () {
      var o = C.shadow([[8, 44], [44, 42], [46, 46], [10, 48]]);
      o += K2.bar(6, 30, 40, 34, 1.8, S.wood3) + K2.bar(8, 34, 40, 38, 1.8, S.wood3);
      o += poly([[14, 24], [38, 26], [36, 38], [14, 36]], S.wood, G, LD) + K2.box(18, 34, 30, 8, 6, S.gray3, S.gray2);
      return o + K2.wheel(36, 40, 6, 6);
    } });

  function rubbleTile(v) {
    return { id: 'east-common-ground-rubble-0' + v, name: '碎石地 ' + v, category: 'ground', kind: 'ground_rubble', resource: 'stone', facility: null,
      variant: v, w: 1, d: 1, up: 0, tags: ['tileable', 'quarry'], note: '采石场碎石裸地：底色与 east-ground 黄土同色 #d9c58f，碎石离边 ≥3 px，任意排列无缝',
      draw: function (W, D, r) {
        var o = rect(-0.5, -0.5, 49, 49, S.grass), i;
        for (i = 0; i < 3; i++) o += ell(8 + r() * 32, 8 + r() * 32, 4 + r() * 3, 2 + r() * 1.5, S.gray3, null, 0, C.fop(0.3));
        for (i = 0; i < 9 + v * 2; i++) { var x = 6 + r() * 36, y = 6 + r() * 36, s = 1.4 + r() * 2.4; o += poly([[x - s, y], [x, y - s * 0.8], [x + s, y - s * 0.2], [x + s * 0.3, y + s * 0.6]], i % 3 ? S.gray2 : S.gray3, G, 0.5); }
        return o;
      } };
  }
  def(rubbleTile(1)); def(rubbleTile(2));

  // ---------------- 黏土坑 clay ----------------
  /** 一块土坯（3/4 视小方块）。 */
  function brick(x, yb, col) { return K2.box(x, x + 9, yb, 4, 3.4, S.earth, col || S.earth3, 0.7); }

  def({ id: 'east-common-site-claypit-01', name: '黏土坑·取土坑', category: 'site', kind: 'site_clay_pit', resource: 'clay', facility: null,
    w: 3, d: 2, up: 30, tags: ['clay', 'pit', 'ladder'], note: '台阶状挖开的取土坑，坑底积一汪浑水，坑沿搭木板坡道与竹筐；无对应 FacilityKind（制坯烧砖另见 kiln）',
    draw: function (W, D, r, id) {
      var o = K2.pad(2, 4, W - 2, D - 2, S.earth3, 0.45);
      // 坑：外沿 + 两级台阶壁 + 坑底浑水
      o += path('M10 30 Q20 8 70 10 Q122 8 134 30 Q140 62 120 80 Q72 90 24 80 Q4 62 10 30 Z', S.earth2, G, LW);
      o += path('M22 36 Q30 20 70 22 Q112 20 122 36 Q126 60 110 72 Q72 80 34 72 Q18 60 22 36 Z', S.brown2, G, LD);
      o += path('M30 50 Q40 38 72 40 Q104 38 112 50 Q114 64 100 70 Q72 76 42 70 Q28 64 30 50 Z', S.earth3, null, 0);
      o += K2.water([[46, 58], [96, 56], [100, 64], [86, 70], [52, 70], [42, 64]], id, r);
      for (var i = 0; i < 9; i++) { var x = 30 + i * 10; o += ln(x, 26 + (i % 2), x - 2, 34, S.brown, 0.8, C.op(0.5)); }
      // 木板坡道 + 梯
      o += K2.bar(118, 84, 100, 52, 4.2, S.wood2) + ln(116, 78, 112, 72, S.wood3, 0.8) + ln(110, 68, 106, 62, S.wood3, 0.8);
      o += K2.ladder(36, 24, 60, 7);
      // 坑沿：铁锹、两只泥筐、湿泥堆
      o += K2.basket(16, 92, 12, 9, S.brown2, S.earth3, r) + K2.basket(132, 90, 12, 9, S.brown2, S.earth3, r);
      o += K.heap(70, 94, 16, 3, S.earth3, S.brown2, r, 7);
      o += K2.bar(140, 50, 128, 70, 1.4, S.wood2) + poly([[124, 68], [130, 70], [128, 78], [122, 75]], S.gray3, G, LD);
      return o;
    } });

  def({ id: 'east-common-site-brickyard-01', name: '晾坯场', category: 'site', kind: 'site_brick_drying', resource: 'clay', facility: null,
    w: 3, d: 2, up: 40, tags: ['clay', 'adobe', 'drying', 'shed'], note: '夯平场地上成行码放土坯晾干，后侧一溜低矮茅草遮雨棚和木制坯模；烧砖成窑另用 kiln',
    draw: function (W, D, r, id) {
      var o = K2.pad(2, 2, W - 2, D - 2, S.earth, 0.6);
      o += C.shadow([[132, 18], [140, 22], [140, 40], [132, 36]]);
      [8, 50, 92, 134].forEach(function (x) { o += K.post(x, 6, 38, 2.6); });
      o += K.roof(id, 8, 134, -12, 8, 4, S.thatch, 'thatch', 2);
      // 棚下两摞坯
      for (var k = 0; k < 3; k++) { o += brick(14 + k * 11, 36) + brick(70 + k * 11, 36); o += brick(19 + k * 11, 31) + brick(75 + k * 11, 31); }
      // 场地上一行行人字码放的土坯
      for (var row = 0; row < 3; row++) {
        var y = 56 + row * 14;
        for (var c = 0; c < 10; c++) o += brick(10 + c * 13 + (row % 2) * 5, y, row === 2 ? S.brown2 : S.earth3);
      }
      // 坯模 + 一只泥桶
      o += K2.box(116, 134, 92, 3, 8, S.wood2, S.wood3) + ln(122, 82, 122, 89, S.wood3, 0.8) + ln(128, 82, 128, 89, S.wood3, 0.8);
      return o;
    } });

  def({ id: 'east-common-prop-clay-mud-01', name: '泥料堆', category: 'prop', kind: 'prop_clay_mud', resource: 'clay', facility: null,
    w: 1, d: 1, up: 12, tags: ['clay'], note: '闷好的湿泥，上插木锹',
    draw: function (W, D, r) {
      var o = C.shadowEll(26, 44, 20, 4) + path('M6 44 Q12 28 24 26 Q38 24 44 44 Z', S.brown2, G, LD);
      o += path('M12 38 Q22 30 34 34', null, S.earth3, 1.2) + K2.bar(30, 14, 26, 32, 1.4, S.wood2) + poly([[22, 30], [30, 31], [29, 38], [21, 37]], S.gray3, G, LD);
      return o;
    } });
  def({ id: 'east-common-prop-clay-adobe-01', name: '土坯垛', category: 'prop', kind: 'prop_adobe_stack', resource: 'clay', facility: null,
    w: 1, d: 1, up: 14, tags: ['clay', 'adobe'], note: '晾干的土坯交错码成方垛',
    draw: function () {
      var o = C.shadow([[6, 44], [44, 42], [47, 47], [9, 48]]);
      for (var l = 0; l < 4; l++) for (var c = 0; c < 3; c++) o += brick(8 + c * 11 + (l % 2) * 4, 44 - l * 5, l % 2 ? S.earth3 : S.brown2);
      return o;
    } });
  def({ id: 'east-common-prop-clay-baskets-01', name: '挑泥担', category: 'prop', kind: 'prop_clay_baskets', resource: 'clay', facility: null,
    w: 1, d: 1, up: 22, tags: ['clay', 'basket', 'carry_pole'], note: '一根扁担两只泥筐',
    draw: function (W, D, r) {
      var o = K2.basket(12, 42, 14, 10, S.brown2, S.earth3, r) + K2.basket(36, 42, 14, 10, S.brown2, S.earth3, r);
      return o + ln(12, 30, 12, 18, S.thatch2, 0.9) + ln(36, 30, 36, 18, S.thatch2, 0.9) + K2.bar(4, 18, 44, 17, 1.8, S.bamboo || S.wood2);
    } });

  return { defs: defs, all: function () { return defs.map(C.make); } };
});
