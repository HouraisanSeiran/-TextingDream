/*
 * 织梦 · east-site · 珍稀与奇幻资源点：玉石矿（gems）、灵石矿（mana）、龙骨坑（dragonbone）。
 * 浏览器挂 window.TownArtES_rare，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./kit.js'), require('./kit2.js'));
  else root.TownArtES_rare = factory(root.TownArtES_core, root.TownArtES_kit, root.TownArtES_kit2);
})(this, function (C, K, K2) {
  'use strict';
  var S = C.S, f = C.f, poly = C.poly, path = C.path, rect = C.rect, ell = C.ell, circ = C.circ, ln = C.ln;
  var G = S.ink, G2 = S.ink2, LW = S.lw, LD = S.lwd;
  var JADE = '#7fc4a0', JADE2 = '#4f9a78', JADE3 = '#cfe9d6';
  var defs = [];
  function def(o) { defs.push(o); }
  /** 一块玉料：粗皮（赭）包着一个切开的玉面。 */
  function jadeStone(cx, yb, s, cut) {
    var o = path('M' + f(cx - 8 * s) + ' ' + f(yb) + 'Q' + f(cx - 10 * s) + ' ' + f(yb - 9 * s) + ' ' + f(cx - 2 * s) + ' ' + f(yb - 11 * s) +
      'Q' + f(cx + 9 * s) + ' ' + f(yb - 12 * s) + ' ' + f(cx + 9 * s) + ' ' + f(yb) + 'Z', S.earth3, G, LD);
    if (cut) o += path('M' + f(cx - 3 * s) + ' ' + f(yb - 1) + 'L' + f(cx - 1 * s) + ' ' + f(yb - 9 * s) + 'L' + f(cx + 7 * s) + ' ' + f(yb - 8 * s) + 'L' + f(cx + 7 * s) + ' ' + f(yb - 1) + 'Z', JADE, G, 0.7) +
      ln(cx, yb - 7 * s, cx + 4 * s, yb - 6 * s, JADE3, 0.9);
    return o;
  }

  // ---------------- 玉石矿 gems ----------------
  def({ id: 'east-common-site-jadepit-01', name: '玉石矿·玉料坑', category: 'site', kind: 'site_jade_pit', resource: 'gems', facility: 'mine_head',
    w: 3, d: 2, up: 44, tags: ['gems', 'jade', 'pit', 'windlass'], roof: 'none', note: '河谷崖脚开的露天玉料坑：坑壁露出青绿玉脉，坑沿木三脚吊架起吊玉料，旁堆带皮籽料',
    draw: function (W, D, r, id) {
      var o = K2.pad(0, 0, W, D, S.earth3, 0.4);
      // 后侧崖壁带玉脉
      o += path('M0 30 L0 -14 Q30 -34 70 -26 Q110 -40 144 -16 L144 30 Z', S.gray2, G, LW);
      for (var i = 0; i < 4; i++) { var x = 14 + i * 32; o += path('M' + x + ' ' + (-14 + (i % 2) * 6) + ' q8 6 16 2 q6 -2 12 4', null, JADE2, 3) + path('M' + x + ' ' + (-14 + (i % 2) * 6) + ' q8 6 16 2 q6 -2 12 4', null, JADE, 1.4); }
      o += K2.pit(14, 24, 104, 78, 10, S.brown2, S.earth3);
      o += path('M26 46 Q40 38 56 44', null, JADE, 2.2) + path('M70 40 Q84 36 94 44', null, JADE, 2.2);
      // 三脚吊架
      o += K2.bar(48, 70, 64, 4, 2.2, S.wood3) + K2.bar(82, 72, 64, 4, 2.2, S.wood3) + K2.bar(64, 30, 64, 4, 2.2, S.wood);
      o += ln(64, 6, 64, 44, S.thatch2, 1.1) + jadeStone(64, 54, 0.9, false);
      // 坑外玉料堆
      o += C.shadowEll(124, 88, 16, 4) + jadeStone(114, 88, 1, true) + jadeStone(132, 90, 0.8, false) + jadeStone(124, 80, 0.7, true);
      o += K2.basket(20, 92, 12, 9, JADE, JADE2, r);
      return o;
    } });
  def({ id: 'east-common-site-jadeshop-01', name: '玉石矿·琢玉棚', category: 'site', kind: 'site_jade_workshop', resource: 'gems', facility: null,
    w: 3, d: 2, up: 52, tags: ['gems', 'jade', 'workshop', 'lathe'], roof: 'gable_tile', note: '瓦顶敞棚，棚下两架脚踏琢玉砣机（立轮砣具 + 水盆解玉砂），案上摆半成品玉璧；无对应 FacilityKind',
    draw: function (W, D, r, id) {
      var o = K2.pad(2, 4, W - 2, D - 2, S.earth, 0.5);
      o += C.shadow([[118, 22], [128, 28], [128, 66], [118, 60]]);
      o += rect(12, 20, 106, 42, S.cream, G, LD) + rect(12, 20, 106, 42, S.shadow, null, 0, C.fop(0.15));
      // 两架砣机：木凳台 + 立轮 + 水盆
      [36, 82].forEach(function (x) {
        o += K2.box(x - 16, x + 16, 62, 10, 8, S.wood2, S.wood);
        o += K2.wheel(x, 36, 8, 6, S.gray) + K.post(x - 11, 30, 44, 2, S.wood3) + K.post(x + 11, 30, 44, 2, S.wood3);
        o += ell(x + 4, 44, 6, 2, S.water, G, 0.7) + ln(x - 14, 62, x - 6, 70, S.wood3, 1.6);
      });
      [12, 65, 118].forEach(function (x) { o += K.post(x, 18, 64, 3.2, S.vermil); });
      o += K.roof(id, 10, 120, -18, 20, 6, S.teal, 'tile', 4);
      // 前方玉案 + 玉璧
      o += K2.box(40, 96, 90, 8, 8, S.wood2, S.wood3);
      [52, 68, 84].forEach(function (x, i) { o += ell(x, 78, 5.4, 2.2, i === 1 ? JADE3 : JADE, G, 0.7) + ell(x, 78, 1.6, 0.7, S.wood2, null, 0); });
      o += jadeStone(122, 92, 0.9, true);
      return o;
    } });
  def({ id: 'east-common-prop-gems-rawjade-01', name: '玉料堆', category: 'prop', kind: 'prop_raw_jade', resource: 'gems', facility: null,
    w: 1, d: 1, up: 14, tags: ['gems', 'jade'], note: '几块带赭皮的籽料，两块开了窗露出青玉',
    draw: function () { return C.shadowEll(26, 44, 20, 4) + jadeStone(14, 44, 1, true) + jadeStone(34, 45, 0.9, false) + jadeStone(25, 38, 0.8, true); } });
  def({ id: 'east-common-prop-gems-sandtub-01', name: '解玉砂盆', category: 'prop', kind: 'prop_jade_sand', resource: 'gems', facility: null,
    w: 1, d: 1, up: 12, tags: ['gems', 'jade', 'sand', 'water'], note: '木盆盛水调解玉砂，旁边一袋砂和一把木勺',
    draw: function () {
      var o = C.shadowEll(24, 44, 18, 3.4) + path('M8 34 Q8 44 20 45 Q32 44 32 34 Z', S.wood, G, LD) + ell(20, 34, 12, 3.4, S.water, G, LD) + ell(20, 34.4, 7, 1.6, S.gray3, null, 0);
      return o + path('M32 45 Q30 32 38 30 Q46 32 44 45 Z', S.thatch, G, LD) + ln(34, 33, 42, 33, S.wood3, 1.2) + K2.bar(14, 26, 22, 34, 1.2, S.wood2);
    } });
  def({ id: 'east-common-prop-gems-cutjade-01', name: '玉坯木箱', category: 'prop', kind: 'prop_jade_crate', resource: 'gems', facility: null,
    w: 1, d: 1, up: 14, tags: ['gems', 'jade', 'crate'], note: '敞口木箱里垫稻草放着切好的方玉坯',
    draw: function () {
      var o = C.shadow([[6, 44], [44, 42], [47, 47], [9, 48]]);
      o += K2.box(6, 42, 44, 12, 12, S.thatch2, S.wood);
      o += K2.box(12, 22, 28, 5, 4, JADE3, JADE) + K2.box(24, 34, 27, 5, 4, JADE3, JADE2);
      return o + ln(6, 38, 42, 38, S.wood3, 0.8) + rect(20, 34, 8, 5, S.vermil, null, 0);
    } });

  // ---------------- 灵石矿 mana ----------------
  var MANA = '#7fe0e6', MANA2 = '#3fb0c8', MANA3 = '#e8fbff';
  /** 一簇发光灵石晶柱：外圈一道半透明光晕（平涂，不用模糊）。 */
  function crystal(cx, yb, s) {
    var o = ell(cx, yb - 8 * s, 13 * s, 12 * s, MANA, null, 0, C.fop(0.18)) + ell(cx, yb - 8 * s, 8 * s, 8 * s, MANA3, null, 0, C.fop(0.2));
    [[-5, 12, -0.25], [0, 18, 0], [5, 11, 0.3]].forEach(function (p) {
      var x = cx + p[0] * s, h = p[1] * s, k = p[2] * h;
      o += poly([[x - 2.6 * s, yb], [x - 2.6 * s + k, yb - h + 3 * s], [x + k, yb - h], [x + 2.6 * s + k, yb - h + 3 * s], [x + 2.6 * s, yb]], MANA2, G2, 0.8);
      o += poly([[x - 0.8 * s, yb - 1], [x + k * 0.9 - 0.8 * s, yb - h + 3.5 * s], [x + k, yb - h + 1], [x + k * 0.9 + 0.6 * s, yb - h + 3.5 * s], [x + 0.4 * s, yb - 1]], MANA, null, 0);
    });
    return o;
  }
  /** 镇守符箓石柱：方石柱 + 朱砂符纸 + 顶上宝珠。 */
  function talismanPillar(x, yb, h) {
    var o = C.shadow([[x + 4, yb], [x + 12, yb - 2], [x + 14, yb + 3], [x + 4, yb + 4]]);
    o += rect(x - 6, yb - 4, 12, 4, S.gray, G, LD) + rect(x - 4.5, yb - h, 9, h - 4, S.gray2, G, LW) + rect(x - 4.5, yb - h, 3, h - 4, S.gray3, null, 0, C.fop(0.6));
    o += rect(x - 3, yb - h + 6, 6, h * 0.5, S.ochre, G, 0.6);
    for (var i = 0; i < 4; i++) o += ln(x - 1.6, yb - h + 9 + i * h * 0.1, x + 1.6, yb - h + 10 + i * h * 0.1, S.vermil, 1);
    return o + ell(x, yb - h - 1, 6, 2, S.gray, G, LD) + circ(x, yb - h - 5, 3.4, MANA, G2, 0.8) + circ(x - 1, yb - h - 6, 1.2, MANA3, null, 0);
  }
  def({ id: 'east-common-site-manavein-01', name: '灵石矿·发光矿脉', category: 'site', kind: 'site_mana_vein', resource: 'mana', facility: 'mine_head',
    w: 3, d: 2, up: 76, tags: ['mana', 'spirit_stone', 'vein', 'glow', 'fantasy'], roof: 'none', note: '山岩裂开露出发光青蓝灵石晶簇，四角立镇守符箓石柱，地上画一圈朱砂阵线；光晕用平涂半透明色块，不用模糊',
    draw: function (W, D, r, id) {
      var o = K2.pad(0, 0, W, D, S.gray3, 0.3);
      o += path('M4 50 L6 -20 Q30 -54 66 -46 Q100 -62 132 -34 Q142 -20 140 50 Z', S.gray, G, LW);
      o += path('M64 -46 Q98 -58 130 -32 Q140 -18 138 48 L104 48 Q108 0 64 -46 Z', S.navy2, null, 0, C.fop(0.5));
      // 岩缝：发光矿脉
      var crack = [[30, 40], [44, 14], [58, 4], [70, -24], [86, -6], [98, 20], [110, 40]];
      o += C.pl(crack, S.navy, 7) + C.pl(crack, MANA2, 4) + C.pl(crack, MANA3, 1.4);
      o += crystal(58, 34, 1.3) + crystal(92, 30, 1) + crystal(74, -12, 0.8);
      // 朱砂阵线（地面椭圆）
      o += ell(72, 70, 58, 18, null, S.vermil, 1.4, C.op(0.8)) + ell(72, 70, 50, 14, null, S.vermil, 0.8, C.op(0.5));
      for (var i = 0; i < 8; i++) { var a = i / 8 * Math.PI * 2; o += circ(72 + Math.cos(a) * 54, 70 + Math.sin(a) * 16, 1.6, S.vermil, null, 0); }
      o += talismanPillar(14, 92, 40) + talismanPillar(130, 92, 40);
      o += crystal(40, 80, 0.7) + crystal(104, 84, 0.6);
      return o;
    } });
  def({ id: 'east-common-prop-mana-pillar-01', name: '镇守符箓石柱', category: 'prop', kind: 'prop_talisman_pillar', resource: 'mana', facility: null,
    w: 1, d: 1, up: 44, tags: ['mana', 'talisman', 'pillar', 'fantasy'], note: '方石柱贴朱砂黄符，顶托一颗灵石宝珠，镇住矿脉灵气',
    draw: function () { return talismanPillar(24, 44, 42); } });
  def({ id: 'east-common-prop-mana-crystals-01', name: '灵石晶簇', category: 'prop', kind: 'prop_mana_crystals', resource: 'mana', facility: null,
    w: 1, d: 1, up: 20, tags: ['mana', 'crystal', 'glow', 'fantasy'], note: '散落在地的灵石晶簇，外有一圈平涂光晕',
    draw: function () { return crystal(20, 42, 1.1) + crystal(36, 44, 0.7); } });
  def({ id: 'east-common-prop-mana-chest-01', name: '灵石玉匣', category: 'prop', kind: 'prop_mana_chest', resource: 'mana', facility: null,
    w: 1, d: 1, up: 16, tags: ['mana', 'chest', 'fantasy'], note: '贴封条的朱漆木匣，盖半开露出灵石微光',
    draw: function () {
      var o = C.shadow([[8, 44], [44, 42], [47, 47], [10, 48]]);
      o += K2.box(8, 40, 44, 12, 9, S.brown, S.vermil) + ell(24, 27, 10, 2.6, MANA, null, 0, C.fop(0.6));
      o += poly([[8, 23], [40, 23], [42, 14], [10, 14]], S.vermil, G, LD) + rect(21, 32, 6, 12, S.ochre, G, 0.6);
      return o + ln(22, 35, 26, 35, S.vermil, 0.8) + ln(22, 39, 26, 39, S.vermil, 0.8);
    } });
  function manaTile(v) {
    return { id: 'east-common-ground-manarock-0' + v, name: '灵脉裸岩 ' + v, category: 'ground', kind: 'ground_mana_rock', resource: 'mana', facility: null,
      variant: v, w: 1, d: 1, up: 0, tags: ['tileable', 'mana', 'fantasy'], note: '灰岩裸地，散布发光碎晶；底色同 east-ground 黄土，碎晶离边 ≥3 px',
      draw: function (W, D, r) {
        var o = rect(-0.5, -0.5, 49, 49, S.grass), i;
        for (i = 0; i < 3; i++) o += ell(8 + r() * 32, 8 + r() * 32, 4 + r() * 3, 2 + r() * 1.5, S.gray2, null, 0, C.fop(0.3));
        for (i = 0; i < 6 + v * 2; i++) { var x = 6 + r() * 36, y = 6 + r() * 36, s = 1.2 + r() * 1.8; o += poly([[x - s, y], [x, y - s * 1.6], [x + s, y]], i % 3 ? S.gray : MANA2, G2, 0.4); }
        return o + circ(16 + v * 8, 30 - v * 4, 2, MANA, null, 0, C.fop(0.7));
      } };
  }
  def(manaTile(1)); def(manaTile(2));

  // ---------------- 龙骨坑 dragonbone ----------------
  var BONE = '#efe2c0', BONE2 = '#cdb88a';
  /** 一节龙脊骨：椎体 + 向上的棘突。 */
  function vertebra(x, y, s) {
    return ell(x, y, 5 * s, 4 * s, BONE, G, LD) + poly([[x - 2 * s, y - 3 * s], [x + 1 * s, y - 12 * s], [x + 3 * s, y - 3 * s]], BONE, G, 0.8) + ell(x, y + 0.5, 2 * s, 1.4 * s, BONE2, null, 0);
  }
  /** 一根肋骨（弧）。 */
  function rib(x, y, h, dir) {
    var d = 'M' + f(x) + ' ' + f(y) + 'Q' + f(x + dir * h * 0.6) + ' ' + f(y - h * 0.2) + ' ' + f(x + dir * h * 0.5) + ' ' + f(y + h * 0.5);
    return path(d, null, G, 4.4) + path(d, null, BONE, 2.6);
  }
  def({ id: 'east-common-site-dragonpit-01', name: '龙骨坑·巨骨发掘', category: 'site', kind: 'site_dragonbone_dig', resource: 'dragonbone', facility: null,
    w: 4, d: 3, up: 60, tags: ['dragonbone', 'excavation', 'skull', 'fantasy'], roof: 'none', note: '方形发掘坑里露出半截巨龙骸骨：龙首带角、一串脊骨与两排肋骨；坑沿木桩拉红绳分区，竹梯下坑；无对应 FacilityKind',
    draw: function (W, D, r, id) {
      var o = K2.pad(0, 0, W, D, S.earth3, 0.35);
      o += path('M6 20 L186 16 L182 126 L10 130 Z', S.earth3, G, LW) + path('M12 24 L180 21 L176 120 L16 124 Z', S.brown2, null, 0);
      o += path('M16 38 L176 34 L176 120 L16 124 Z', S.earth2, null, 0);
      for (var i = 0; i < 12; i++) o += ln(16 + i * 14, 26, 14 + i * 14, 36, S.brown, 0.8, C.op(0.5));
      // 脊骨一串 + 两排肋骨
      for (i = 0; i < 9; i++) { var x = 58 + i * 13, y = 78 - Math.sin(i / 8 * Math.PI) * 10; o += rib(x, y, 22, -1) + rib(x, y + 2, 20, 1); }
      for (i = 0; i < 9; i++) o += vertebra(58 + i * 13, 78 - Math.sin(i / 8 * Math.PI) * 10, 1);
      // 龙首（左）：吻部、眼窝、上颚齿、两支后弯角
      o += path('M18 84 Q22 64 44 62 Q58 64 58 80 Q50 96 30 96 Q18 94 18 84 Z', BONE, G, LW);
      o += ell(42, 72, 4, 3, '#4a3826', null, 0) + ell(26, 84, 2, 1.4, '#4a3826', null, 0);
      for (i = 0; i < 5; i++) o += poly([[22 + i * 6, 92], [25 + i * 6, 92], [23.5 + i * 6, 97]], BONE, G, 0.6);
      o += path('M48 64 Q58 44 74 46', null, G, 5) + path('M48 64 Q58 44 74 46', null, BONE2, 3);
      o += path('M40 62 Q44 42 60 36', null, G, 5) + path('M40 62 Q44 42 60 36', null, BONE2, 3);
      // 木桩红绳 + 竹梯
      [[8, 18], [100, 14], [184, 12], [6, 128], [188, 124]].forEach(function (p) { o += K.post(p[0], p[1] - 14, p[1], 2.4, S.wood3); });
      o += C.pl([[8, 8], [100, 4], [184, 2]], S.vermil, 1) + C.pl([[6, 118], [188, 114]], S.vermil, 1);
      o += K2.ladder(172, 40, 110, 8);
      o += K2.basket(150, 136, 12, 8, BONE2, BONE, r);
      return o;
    } });
  def({ id: 'east-common-prop-dragon-altar-01', name: '祭龙香案', category: 'prop', kind: 'prop_incense_altar', resource: 'dragonbone', facility: null,
    w: 1, d: 1, up: 30, tags: ['dragonbone', 'altar', 'incense', 'fantasy'], note: '朱漆香案上摆香炉、三炷香和供果，发掘前祭龙',
    draw: function () {
      var o = C.shadow([[6, 44], [44, 42], [47, 47], [9, 48]]);
      o += K.post(9, 30, 44, 2.6, S.vermil) + K.post(39, 30, 44, 2.6, S.vermil);
      o += K2.box(4, 44, 32, 4, 9, S.vermil, S.brown) + rect(8, 32, 32, 7, S.vermil, G, 0.8) + ln(10, 35.5, 38, 35.5, S.gold2, 0.8);
      o += path('M18 22 L30 22 L28 28 L20 28 Z', S.gold, G, 0.8) + ell(24, 22, 6, 1.8, S.gold2, G, 0.6);
      for (var i = -1; i <= 1; i++) o += ln(24 + i * 2.4, 22, 24 + i * 3, 10, S.vermil, 0.9) + circ(24 + i * 3, 10, 0.9, S.orange, null, 0);
      return o + circ(12, 21, 2.6, S.orange, G, 0.6) + circ(36, 21, 2.6, S.orange, G, 0.6) + K2.smoke(26, 8, 0.4);
    } });
  def({ id: 'east-common-prop-dragon-bones-01', name: '龙骨堆', category: 'prop', kind: 'prop_bone_pile', resource: 'dragonbone', facility: null,
    w: 1, d: 1, up: 16, tags: ['dragonbone', 'bones', 'fantasy'], note: '起出的龙肋骨与脊骨码在草席上，一支断角',
    draw: function () {
      var o = poly([[2, 28], [46, 28], [48, 46], [0, 46]], S.thatch2, G, LD);
      o += rib(8, 34, 26, 1) + rib(14, 38, 26, 1) + vertebra(36, 40, 0.9) + vertebra(26, 42, 0.8);
      return o + path('M6 44 Q18 38 28 30', null, G, 4.4) + path('M6 44 Q18 38 28 30', null, BONE2, 2.6);
    } });
  def({ id: 'east-common-prop-dragon-tools-01', name: '发掘工具架', category: 'prop', kind: 'prop_dig_tools', resource: 'dragonbone', facility: null,
    w: 1, d: 1, up: 30, tags: ['dragonbone', 'tools'], note: '木架上靠着铲、镐和扫骨用的竹刷',
    draw: function () {
      var o = C.shadow([[8, 44], [42, 42], [46, 46], [10, 48]]);
      o += K2.bar(6, 20, 42, 20, 1.6, S.wood2) + K.post(8, 18, 44, 2.2, S.wood3) + K.post(40, 18, 44, 2.2, S.wood3);
      o += K2.bar(14, 14, 18, 42, 1.2, S.wood2) + poly([[16, 38], [22, 39], [21, 46], [15, 45]], S.gray3, G, 0.7);
      o += K2.bar(26, 12, 28, 42, 1.2, S.wood2) + path('M20 14 Q27 9 34 14', null, S.gray3, 2.2);
      return o + K2.bar(36, 22, 34, 40, 1, S.thatch2) + rect(31, 38, 6, 6, S.thatch, G, 0.6);
    } });

  return { defs: defs, all: function () { return defs.map(C.make); } };
});
