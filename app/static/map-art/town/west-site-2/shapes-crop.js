/*
 * 织梦 · 西式资源点第二批 —— 种植：grain/wheat_farm 麦田农庄、grain/vegetable_farm 菜园、grain/flax_farm 亚麻田
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWS2_core;
  var P = C.P, K = C.K, f = C.f, path = C.path, line = C.line, ell = C.ell, poly = C.poly, seg = C.seg, shade = C.shade;

  /** 麦穗一簇 */
  function wheatTuft(ctx, x, y) {
    return line(seg(x - 1.5, y, x - 2, y - 6) + seg(x, y, x, y - 7) + seg(x + 1.5, y, x + 2, y - 6), 0.9, 1, P.wheat2) +
      ell(x, y - 7.2, 1, 1.8, P.wheat, 0.5);
  }
  /** 麦捆（立着的一束，腰上扎绳） */
  function sheaf(x, yb) {
    return C.shadowEll(x + 2, yb, 5, 1.6) + path(poly([[x - 4, yb], [x - 2, yb - 7], [x - 4, yb - 14], [x + 4, yb - 14], [x + 2, yb - 7], [x + 4, yb]]), P.wheat, 1) +
      line(seg(x - 2.4, yb - 7, x + 2.4, yb - 7), 1.2, 1, P.dark);
  }
  C.sheaf = sheaf;

  /* 麦田农庄：后半麦田（一部分已收割、立着麦捆），前左木筋农舍，前右两座谷物堆垛 + 草顶小谷仓 */
  C.def({
    idKind: 'site-wheat-farmstead', name: '麦田农庄', cat: 'site', resource: 'grain', subtype: 'wheat_farm', facility: 'granary',
    w: 4, d: 3, up: 56, roof: 'gable_thatch', tags: ['wheat_field', 'farmhouse', 'grain_stack', 'barn'],
    note: '农舍 + 谷物堆垛 + 小谷仓；谷仓按 granary 记',
    draw: function (ctx, W, D) {
      var s = K.field(ctx, 6, D - 140, 120, D - 74, P.wheat2, 7, 6, wheatTuft);
      s += K.field(ctx, 124, D - 140, W - 6, D - 74, '#cdb57a', 7, 0, null);
      for (var i = 0; i < 4; i++) for (var j = 0; j < 2; j++) s += sheaf(136 + i * 14 + j * 6, D - 112 + j * 22);
      // 农舍（木筋 + 茅顶 + 烟囱）
      s += K.shed(ctx, 10, D - 10, 74, 28, 26, { timber: true, win: 3, roof: P.thatch, roof2: P.thatch2 });
      s += path(K.q(62, D - 72, 70, D - 54), P.stone2, 1.2);
      // 小谷仓（深木板墙，大门）
      s += K.shed(ctx, 100, D - 30, 44, 26, 22, { wall: P.wood, roof: P.thatch, roof2: P.thatch2, door: 'none' });
      s += path(K.q(112, D - 50, 132, D - 30), P.dark, 1.2) + line(seg(112, D - 50, 132, D - 30) + seg(132, D - 50, 112, D - 30), 0.9, 0.8, P.timber);
      // 两座谷物堆垛
      s += K.stack(ctx, 164, D - 12, 14, P.wheat, P.wheat2) + K.stack(ctx, W - 16, D - 22, 11, P.wheat, P.wheat2);
      return s + C.tuft(ctx, 92, D - 4, 6, 4);
    }
  });
  C.def({
    idKind: 'prop-grain-sheaves', name: '麦捆', cat: 'prop', resource: 'grain', subtype: 'wheat_farm', w: 1, d: 1, up: 6, tags: ['sheaf'],
    draw: function (ctx, W, D) { return sheaf(14, D - 14) + sheaf(30, D - 18) + sheaf(24, D - 8) + sheaf(38, D - 9); }
  });
  C.def({
    idKind: 'prop-grain-rick', name: '谷物堆垛', cat: 'prop', resource: 'grain', subtype: 'wheat_farm', w: 1, d: 1, up: 30, tags: ['rick', 'grain_stack'],
    draw: function (ctx, W, D) { return K.stack(ctx, 24, D - 8, 16, P.wheat, P.wheat2); }
  });
  C.def({
    idKind: 'prop-grain-cart', name: '运麦板车', cat: 'prop', resource: 'grain', subtype: 'wheat_farm', w: 1, d: 1, up: 16, tags: ['cart'],
    draw: function (ctx, W, D) {
      var s = C.shadowEll(26, D - 8, 19, 4) + line(seg(34, D - 18, 46, D - 12), 1.8, 1, P.dark);
      s += C.block(4, D - 12, 34, 8, 5, P.wood, P.timber, 1.3);
      s += path('M6 ' + (D - 25) + 'Q20 ' + (D - 40) + ' 36 ' + (D - 25) + 'Z', P.wheat, 1.2) + line(seg(12, D - 30, 16, D - 26) + seg(22, D - 34, 24, D - 28), 0.7, 0.6);
      return s + C.wheel(12, D - 10, 6) + C.wheel(30, D - 10, 6);
    }
  });

  /** 卷心菜 / 豆架 / 胡萝卜叶：菜园用小植株 */
  function cabbage(ctx, x, y) { return ell(x, y - 2, 3, 2.2, P.leaf2, 0.7) + ell(x - 0.4, y - 2.6, 1.5, 1.1, '#bdbb7e', 0); }
  function carrot(ctx, x, y) { return C.tuft(ctx, x, y, 4, 3, P.leaf, 0.9); }
  function beanPole(x, yb) {
    return line(seg(x - 3, yb, x, yb - 20) + seg(x + 3, yb, x, yb - 20), 1.2, 1, P.timber) +
      path(C.blob(new C.Ctx('bean' + x), x, yb - 9, 4, 8, 6, 0.2), P.leaf, 0.8) + ell(x + 1, yb - 7, 0.8, 1.6, P.leaf3, 0);
  }
  /** 稻草人 */
  function scarecrow(x, yb) {
    return C.post(x, yb, 28, 2.4) + line(seg(x - 10, yb - 20, x + 10, yb - 20), 1.8, 1, P.timber) +
      path(poly([[x - 6, yb - 22], [x + 6, yb - 22], [x + 5, yb - 10], [x - 5, yb - 10]]), P.madder2, 1) +
      ell(x, yb - 26, 3.6, 3.4, P.straw, 0.9) + path(poly([[x - 6, yb - 28], [x + 6, yb - 28], [x, yb - 34]]), P.dark, 0.8);
  }
  /* 菜园：枝条编栏围出四块菜畦（卷心菜、胡萝卜、豆架、葱韭）+ 后右茅草小屋 + 水桶 + 稻草人 */
  C.def({
    idKind: 'site-vegetable-garden', name: '菜园', cat: 'site', resource: 'grain', subtype: 'vegetable_farm', facility: null,
    w: 4, d: 3, up: 40, roof: 'gable_thatch', tags: ['vegetable_beds', 'wattle_fence', 'bean_poles', 'scarecrow'],
    note: '菜畦 + 豆架 + 农舍小屋；无对应 FacilityKind（田园型资源点）',
    draw: function (ctx, W, D) {
      var s = C.fence(6, D - 128, W - 6, D - 128, 12, 12);
      s += K.field(ctx, 10, D - 124, 70, D - 72, P.soil, 8, 8, cabbage) + K.field(ctx, 76, D - 124, 120, D - 72, P.soil, 6, 6, carrot);
      s += K.field(ctx, 10, D - 64, 70, D - 14, P.soil, 12, 0, null);
      for (var i = 0; i < 6; i++) s += beanPole(16 + i * 10, D - 18 - (i % 2) * 12);
      s += K.field(ctx, 76, D - 64, 120, D - 14, P.soil, 6, 5, function (c, x, y) { return line(seg(x, y, x, y - 5) + seg(x + 1, y, x + 2, y - 4), 0.8, 0.9, P.leaf2); });
      s += K.shed(ctx, 132, D - 74, 50, 24, 20, { win: 1, roof: P.thatch, roof2: P.thatch2, wall: P.plaster });
      s += K.barrel(150, D - 14, 7, P.wood, 12) + ell(150, D - 26, 5, 1.6, P.water, 0);
      s += scarecrow(176, D - 22) + C.fence(124, D - 6, W - 6, D - 6, 6, 10);
      return s + C.tuft(ctx, 6, D - 4, 5, 3);
    }
  });
  C.def({
    idKind: 'prop-veg-cabbagebed', name: '卷心菜畦', cat: 'prop', resource: 'grain', subtype: 'vegetable_farm', w: 1, d: 1, up: 0, tags: ['bed'],
    draw: function (ctx, W, D) { return K.field(ctx, 4, D - 40, 44, D - 6, P.soil, 8, 8, cabbage); }
  });
  C.def({
    idKind: 'prop-veg-scarecrow', name: '稻草人', cat: 'prop', resource: 'grain', subtype: 'vegetable_farm', w: 1, d: 1, up: 20, tags: ['scarecrow'],
    draw: function (ctx, W, D) { return C.shadowEll(26, D - 8, 8, 2) + scarecrow(24, D - 8); }
  });
  C.def({
    idKind: 'prop-veg-beanpoles', name: '豆架', cat: 'prop', resource: 'grain', subtype: 'vegetable_farm', w: 1, d: 1, up: 6, tags: ['bean_poles'],
    draw: function (ctx, W, D) { return beanPole(12, D - 10) + beanPole(24, D - 14) + beanPole(36, D - 10); }
  });

  /** 亚麻株：细茎 + 淡蓝小花 */
  function flaxPlant(ctx, x, y) { return line(seg(x, y, x, y - 6), 0.7, 0.9, P.leaf3) + ell(x, y - 6.8, 1.9, 1.4, P.flax, 0.5) + ell(x, y - 6.8, 0.5, 0.4, '#f1ead6', 0); }
  /** 亚麻束（收割后倒立成锥） */
  function flaxStook(x, yb) {
    return C.shadowEll(x + 2, yb, 6, 1.8) + path(poly([[x - 6, yb], [x, yb - 15], [x + 6, yb]]), '#c8b874', 1) +
      line(seg(x - 3, yb - 6, x + 3, yb - 6), 1.1, 1, P.dark) + line(seg(x - 2, yb, x - 1, yb - 10) + seg(x + 2, yb, x + 1, yb - 10), 0.6, 0.6);
  }
  /* 亚麻田：后半蓝花亚麻田，中左沤麻池（水下浸麻束、压石），右侧收割后的麻束锥 + 碎麻台 */
  C.def({
    idKind: 'site-flax-field', name: '亚麻田', cat: 'site', resource: 'grain', subtype: 'flax_farm', facility: null,
    w: 4, d: 3, up: 30, tags: ['flax_field', 'retting_pond', 'flax_stooks', 'flax_brake'],
    note: '亚麻田 + 沤麻池 + 麻束 + 碎麻台；无对应 FacilityKind；按规范 16.2 归 grain',
    draw: function (ctx, W, D) {
      var s = K.field(ctx, 6, D - 150, W - 6, D - 82, P.herb, 7, 6, flaxPlant);
      s += K.pond(ctx, 54, D - 44, 44, 20);
      for (var i = 0; i < 5; i++) s += path(K.q(24 + i * 12, D - 50, 32 + i * 12, D - 44), '#b3a46a', 0.8, 0.8) + C.rock(ctx, 28 + i * 12, D - 46, 3, P.stone, P.stone2, 0.8);
      for (i = 0; i < 6; i++) s += flaxStook(118 + (i % 3) * 18, D - 50 + Math.floor(i / 3) * 22);
      // 碎麻台（木架 + 压杆）
      s += C.post(W - 34, D - 8, 12, 2.6) + C.post(W - 12, D - 8, 12, 2.6) + C.block(W - 40, D - 16, 34, 5, 3, P.wood, P.timber, 1.2);
      s += line(seg(W - 38, D - 26, W - 6, D - 20), 2, 1, P.timber) + line(seg(W - 36, D - 22, W - 10, D - 22), 0.8, 0.8, '#c8b874');
      return s + C.tuft(ctx, 6, D - 4, 5, 3);
    }
  });
  C.def({
    idKind: 'prop-flax-stooks', name: '亚麻束', cat: 'prop', resource: 'grain', subtype: 'flax_farm', w: 1, d: 1, up: 4, tags: ['stook'],
    draw: function (ctx, W, D) { return flaxStook(14, D - 18) + flaxStook(32, D - 20) + flaxStook(24, D - 6); }
  });
  C.def({
    idKind: 'prop-flax-rettingpit', name: '沤麻小池', cat: 'prop', resource: 'grain', subtype: 'flax_farm', w: 1, d: 1, up: 0, tags: ['retting', 'water'],
    draw: function (ctx, W, D) {
      var s = K.pond(ctx, 24, D - 20, 18, 11);
      return s + path(K.q(12, D - 23, 34, D - 18), '#b3a46a', 0.8, 0.8) + C.rock(ctx, 22, D - 19, 3, P.stone, P.stone2, 0.8);
    }
  });
})(typeof window !== 'undefined' ? window : this);
