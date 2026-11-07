/*
 * 织梦 · east-site · 矿山类资源点：铁、铜、锡、金、银、煤（iron/copper/tin/gold/silver/coal）。
 * 每种矿 = 山腹矿洞口（木支护）+ 辘轳竖井 + 矿石筐 + 矿渣地，外加各自的特征件：
 * 铁=焙矿堆，铜=洗矿槽，锡=淘锡簸箕架，金=淘金溜槽，银=炼银小炉，煤=黑煤堆。
 * 浏览器挂 window.TownArtES_mine，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./kit.js'), require('./kit2.js'));
  else root.TownArtES_mine = factory(root.TownArtES_core, root.TownArtES_kit, root.TownArtES_kit2);
})(this, function (C, K, K2) {
  'use strict';
  var S = C.S, f = C.f, poly = C.poly, path = C.path, rect = C.rect, ell = C.ell, circ = C.circ, ln = C.ln;
  var G = S.ink, G2 = S.ink2, LW = S.lw, LD = S.lwd;
  var defs = [];
  function def(o) { defs.push(o); }

  /** 每种矿：中文名、矿石两色、山岩两色、矿脉纹。 */
  var ORE = {
    iron: { cn: '铁', ore: '#a5503a', ore2: '#6e3a2c', rock: '#8f8580', rock2: '#6f6560' },
    copper: { cn: '铜', ore: '#3fa58a', ore2: '#2e6e64', rock: '#86908a', rock2: '#646f6a' },
    tin: { cn: '锡', ore: '#c3cad0', ore2: '#79838c', rock: '#8a8f98', rock2: '#686d76' },
    gold: { cn: '金', ore: '#f3c46a', ore2: '#c98f3c', rock: '#a39486', rock2: '#7c6e62' },
    silver: { cn: '银', ore: '#eef1f4', ore2: '#9aa3ab', rock: '#7b8590', rock2: '#5d6670' },
    coal: { cn: '煤', ore: '#4a4d55', ore2: '#2e3036', rock: '#6b6660', rock2: '#4e4a46' }
  };

  /** 山腹矿洞口：山体 + 矿脉 + 木支护洞门 + 小瓦檐 + 出洞轨道 + 矿石堆。 */
  function adit(m) {
    var P = ORE[m];
    return function (W, D, r, id) {
      var o = K2.pad(0, 40, W, D, S.earth3, 0.4);
      // 山体（后方隆起，左右压低），两级色块表现明暗
      o += path('M0 64 L0 -10 Q14 -46 44 -56 Q66 -78 92 -64 Q120 -60 136 -30 Q144 -16 144 64 Z', P.rock, G, LW);
      o += path('M86 -62 Q118 -56 134 -28 Q142 -12 142 62 L108 62 Q112 10 86 -62 Z', P.rock2, null, 0);
      o += path('M10 -6 Q22 -34 46 -44', null, S.gray3, 1.2, C.op(0.6)) + path('M58 -58 Q72 -64 84 -58', null, S.gray3, 1.2, C.op(0.6));
      // 矿脉：几道折线
      for (var i = 0; i < 4; i++) {
        var x0 = 8 + i * 34 + r() * 8, y0 = -30 + r() * 30;
        o += pl([[x0, y0], [x0 + 8, y0 + 6], [x0 + 14, y0 + 3], [x0 + 22, y0 + 10]], P.ore2, 3.2) + pl([[x0, y0], [x0 + 8, y0 + 6], [x0 + 14, y0 + 3], [x0 + 22, y0 + 10]], P.ore, 1.6);
      }
      // 山脚草与碎石
      for (i = 0; i < 6; i++) o += K.rock(8 + i * 26 + r() * 6, 62, 4 + r() * 3, 2, P.rock, P.rock2, r);
      // 洞口：黑洞 + 内部一道支护影
      o += path('M52 62 L52 22 Q72 8 92 22 L92 62 Z', '#1d1b20', G, LD);
      o += rect(60, 30, 24, 3, S.wood3, null, 0, C.op(0.5)) + rect(61, 30, 2.4, 32, S.wood3, null, 0, C.op(0.5)) + rect(80.6, 30, 2.4, 32, S.wood3, null, 0, C.op(0.5));
      // 木支护门框（立柱 + 横梁 + 斜撑）
      o += K.post(50, 14, 64, 5, S.wood) + K.post(94, 14, 64, 5, S.wood);
      o += K2.bar(42, 13, 102, 13, 4.2, S.wood2) + K2.bar(50, 26, 58, 16, 2, S.wood3) + K2.bar(94, 26, 86, 16, 2, S.wood3);
      // 小瓦檐 + 镇山符牌
      o += K.roof(id, 46, 98, -6, 8, 6, S.navy2, 'tile', 4);
      o += rect(66, -3, 12, 9, S.vermil, G, LD) + ln(72, -1, 72, 4, G2, 1.2);
      // 出洞轨道（向前张开）
      o += poly([[60, 62], [84, 62], [92, 94], [52, 94]], S.earth3, null, 0, C.fop(0.7));
      for (var y = 66; y < 94; y += 6) { var t = (y - 62) / 32; o += ln(58 - t * 6, y, 86 + t * 6, y, S.wood3, 2.2); }
      o += ln(64, 62, 60, 94, S.gray, 1.6) + ln(80, 62, 84, 94, S.gray, 1.6);
      // 洞口右侧矿石堆、左侧鹤嘴锄与矿灯
      o += C.shadowEll(124, 92, 18, 4) + K.heap(120, 92, 18, 5, P.ore, P.ore2, r, 11);
      o += K2.bar(22, 70, 34, 90, 1.6, S.wood2) + path('M16 74 Q22 66 30 70', null, S.gray3, 2.4);
      o += K.post(40, 52, 88, 2, S.wood3) + rect(36.5, 52, 7, 8, S.orange, G, 0.8) + circ(40, 56, 1.6, S.ochre, null, 0);
      return o;
    };
  }
  function pl(a, col, w) { return C.pl(a, col, w); }

  /** 辘轳竖井：井口木框 + 两立柱 + 卷筒摇把 + 绳 + 吊桶，旁边一只矿石筐。 */
  function windlass(m) {
    var P = ORE[m];
    return function (W, D, r, id) {
      var o = K2.pad(4, 8, W - 4, D - 4, S.earth3, 0.45);
      o += C.shadow([[60, 70], [80, 74], [80, 82], [60, 78]]);
      // 井口方框（顶面看到洞，前沿看到一截木壁）
      o += rect(26, 44, 44, 22, S.wood2, G, LW) + rect(31, 48, 34, 14, '#1d1b20', G, LD);
      o += rect(26, 66, 44, 8, S.wood3, G, LD) + ln(26, 70, 70, 70, S.wood, 0.8);
      // 立柱、卷筒、摇把
      o += K2.bar(22, 70, 22, 18, 3, S.wood3) + K2.bar(74, 70, 74, 18, 3, S.wood3);
      o += rect(22, 16, 52, 8, S.wood, G, LD) + ln(28, 16, 28, 24, S.wood3, 0.8) + ln(36, 16, 36, 24, S.wood3, 0.8) + ln(60, 16, 60, 24, S.wood3, 0.8);
      o += K2.bar(74, 20, 84, 20, 1.6, S.gray2) + K2.bar(84, 20, 84, 32, 1.6, S.wood2);
      // 绳与吊桶
      o += ln(48, 24, 48, 44, S.thatch2, 1.4) + K2.basket(48, 54, 10, 8, P.ore, P.ore2, r);
      // 小雨棚
      o += K.roof(id, 16, 80, -14, 10, 4, S.thatch, 'thatch', 3);
      // 前方矿石筐 + 一摞空筐
      o += K2.basket(18, 90, 14, 10, P.ore, P.ore2, r) + K2.basket(78, 88, 12, 8, null) + K2.basket(78, 82, 12, 7, null);
      return o;
    };
  }

  /** 矿渣地底纹：底色同 east-ground 黄土 #d9c58f，渣块离边 ≥3 px。 */
  function slagTile(m) {
    var P = ORE[m];
    return function (W, D, r) {
      var o = rect(-0.5, -0.5, 49, 49, S.grass), i;
      for (i = 0; i < 3; i++) o += ell(8 + r() * 32, 8 + r() * 32, 4 + r() * 3, 2 + r() * 1.5, P.rock2, null, 0, C.fop(0.22));
      for (i = 0; i < 13; i++) {
        var x = 6 + r() * 36, y = 6 + r() * 36, s = 1.2 + r() * 2.2;
        o += poly([[x - s, y], [x - s * 0.2, y - s], [x + s, y - s * 0.3], [x + s * 0.4, y + s * 0.6]], i % 4 ? P.rock2 : P.ore2, G, 0.4);
      }
      return o;
    };
  }

  // ---- 各矿特征摆件 ----
  var SPECIAL = {
    iron: { kind: 'prop_ore_roast', cn: '焙矿堆', up: 30, tags: ['roast', 'smoke'], note: '柴薪与铁矿石层层堆起焙烧，冒一缕烟',
      draw: function (W, D, r) {
        var o = C.shadowEll(26, 44, 20, 4) + path('M6 44 Q14 22 24 20 Q36 20 44 44 Z', S.wood3, G, LD);
        for (var i = 0; i < 4; i++) o += ln(10 + i * 3, 40 - i * 5, 40 - i * 3, 40 - i * 5, S.wood2, 1.2);
        o += K.heap(25, 32, 12, 3, ORE.iron.ore, ORE.iron.ore2, r, 7) + circ(22, 40, 2.6, S.orange, null, 0) + circ(30, 41, 2, S.vermil, null, 0);
        return o + K2.smoke(26, 20, 0.7);
      } },
    copper: { kind: 'prop_ore_wash', cn: '洗矿槽', up: 16, tags: ['wash', 'water'], note: '木槽引水冲洗铜矿砂，槽尾一只接砂竹筐',
      draw: function (W, D, r, id) {
        var o = C.shadow([[4, 40], [44, 38], [46, 44], [6, 46]]);
        o += K.post(8, 26, 40, 2.2, S.wood3) + K.post(40, 30, 42, 2.2, S.wood3);
        o += poly([[2, 20], [44, 26], [44, 34], [2, 28]], S.wood, G, LD) + K2.water([[4, 22], [42, 27], [42, 30], [4, 25]], id, r);
        for (var i = 0; i < 5; i++) o += circ(10 + i * 7, 25.5 + i * 0.9, 1.2, ORE.copper.ore, null, 0);
        return o + K2.basket(38, 46, 10, 7, ORE.copper.ore, ORE.copper.ore2, r);
      } },
    tin: { kind: 'prop_tin_pan', cn: '淘锡簸箕架', up: 26, tags: ['pan', 'sieve'], note: '竹架上晾着淘锡用的簸箕与竹筛，底下一盆锡砂',
      draw: function (W, D, r) {
        var o = C.shadow([[6, 44], [44, 42], [46, 46], [8, 48]]);
        o += K2.bamboo(8, 44, 12, 12, 1.6) + K2.bamboo(40, 44, 36, 12, 1.6) + K2.bamboo(8, 16, 40, 16, 1.6);
        o += ell(17, 26, 8, 6, S.thatch, G, LD) + ell(17, 26, 5, 3.6, null, S.thatch2, 0.8);
        o += ell(32, 28, 7, 7, S.thatch2, G, LD) + ell(32, 28, 4, 4, null, S.thatch, 0.8);
        o += ell(24, 42, 10, 3.6, S.wood3, G, LD) + ell(24, 41, 7, 2.2, ORE.tin.ore, null, 0);
        return o;
      } },
    gold: { kind: 'prop_gold_sluice', cn: '淘金溜槽', up: 24, tags: ['sluice', 'water', 'panning'], note: '斜置木溜槽，槽底横档挂住金砂，槽尾一只淘金木盘',
      draw: function (W, D, r, id) {
        var o = C.shadow([[8, 30], [16, 28], [46, 44], [38, 46]]);
        o += K.post(10, 10, 26, 2.2, S.wood3) + K.post(26, 20, 34, 2.2, S.wood3);
        var a = [[4, 10], [16, 6], [46, 34], [34, 40]];
        o += poly(a, S.wood, G, LD) + K2.water([[7, 10], [15, 7.5], [43, 34], [35, 37.5]], id, r);
        for (var i = 1; i < 6; i++) { var t = i / 6; o += ln(4 + 30 * t + 2, 10 + 30 * t, 16 + 30 * t - 1, 6 + 28 * t, S.wood3, 1.4); o += circ(10 + 30 * t, 9 + 29 * t, 1, ORE.gold.ore, null, 0); }
        o += ell(14, 42, 9, 3.4, S.wood2, G, LD) + ell(14, 41.6, 5, 1.8, S.wood3, null, 0) + circ(14, 41.6, 1.2, ORE.gold.ore, null, 0);
        return o;
      } },
    silver: { kind: 'prop_silver_furnace', cn: '炼银小炉', up: 40, tags: ['furnace', 'cupel', 'smoke'], note: '泥砌小炉吹灰炼银，前开火门，旁有皮风箱；冶炼正式建筑另见 smelter',
      draw: function (W, D, r) {
        var o = C.shadow([[32, 44], [44, 42], [46, 46], [34, 48]]);
        o += path('M10 44 L12 18 Q22 10 32 18 L34 44 Z', S.brown2, G, LW) + path('M12 24 Q22 18 32 24', null, S.earth3, 1);
        o += ell(22, 16, 9, 3, S.earth3, G, LD) + ell(22, 16, 5, 1.6, '#1d1b20', null, 0);
        o += path('M17 44 L17 34 Q22 28 27 34 L27 44 Z', S.vermil, G, LD) + circ(22, 39, 2.6, S.ochre, null, 0);
        o += poly([[34, 40], [44, 34], [46, 42], [36, 44]], S.wood3, G, LD) + ln(36, 38, 30, 36, S.gray2, 1.6);
        o += ell(40, 44, 4, 1.6, ORE.silver.ore, G, 0.6);
        return o + K2.smoke(22, 12, 0.6);
      } },
    coal: { kind: 'prop_coal_heap', cn: '黑煤堆', up: 22, tags: ['coal', 'heap'], note: '出井原煤堆成尖堆，插一把煤锹，旁边一只空筐',
      draw: function (W, D, r) {
        var o = C.shadowEll(26, 44, 21, 4) + path('M3 44 Q16 18 26 16 Q36 18 46 44 Z', S.coal, G2, LD);
        o += K.heap(25, 40, 17, 7, S.coal2, S.coal, r, 14);
        for (var i = 0; i < 6; i++) o += ln(14 + i * 4, 34 - (i % 3) * 5, 16 + i * 4, 33 - (i % 3) * 5, S.gray3, 0.8, C.op(0.7));
        return o + K2.bar(36, 14, 32, 30, 1.4, S.wood2) + poly([[28, 28], [36, 30], [35, 36], [27, 34]], S.gray2, G, LD);
      } }
  };

  Object.keys(ORE).forEach(function (m) {
    var P = ORE[m], sp = SPECIAL[m];
    def({ id: 'east-common-site-mine-' + m + '-01', name: P.cn + '矿·山腹矿洞口', category: 'site', kind: 'site_mine_adit', resource: m, facility: 'mine_head',
      w: 3, d: 2, up: 80, tags: ['mine', 'adit', 'timbering', m], roof: 'gable_tile', note: '山腹开平硐，木支护门框加小瓦檐与镇山符牌，出洞枕木轨道，洞口矿石堆',
      draw: adit(m) });
    def({ id: 'east-common-site-mine-' + m + '-02', name: P.cn + '矿·辘轳竖井', category: 'site', kind: 'site_mine_shaft', resource: m, facility: 'mine_head',
      w: 2, d: 2, up: 26, tags: ['mine', 'shaft', 'windlass', m], roof: 'gable_thatch', note: '方木井框上架辘轳卷筒和摇把，绳吊竹筐出矿，上搭小茅棚',
      draw: windlass(m) });
    def({ id: 'east-common-prop-mine-' + m + '-basket-01', name: P.cn + '矿石筐', category: 'prop', kind: 'prop_ore_basket', resource: m, facility: null,
      w: 1, d: 1, up: 12, tags: ['ore', 'basket', m], note: '一副扁担两只竹筐装满' + P.cn + '矿石',
      draw: function (W, D, r) { return K2.basket(14, 44, 14, 11, P.ore, P.ore2, r) + K2.basket(34, 42, 14, 11, P.ore, P.ore2, r) + K2.bar(4, 24, 44, 22, 1.6, S.wood2); } });
    def({ id: 'east-common-prop-mine-' + m + '-' + sp.kind.replace('prop_', '').replace('_', '') + '-01', name: sp.cn, category: 'prop', kind: sp.kind, resource: m,
      facility: null, w: 1, d: 1, up: sp.up, tags: sp.tags.concat([m]), note: sp.note, draw: sp.draw });
    def({ id: 'east-common-ground-slag-' + m + '-01', name: P.cn + '矿渣地', category: 'ground', kind: 'ground_slag', resource: m, facility: null,
      w: 1, d: 1, up: 0, tags: ['tileable', 'slag', m], note: '矿渣与碎矿石散落的裸地，可平铺', draw: slagTile(m) });
  });

  return { ORE: ORE, adit: adit, windlass: windlass, defs: defs, all: function () { return defs.map(C.make); } };
});
