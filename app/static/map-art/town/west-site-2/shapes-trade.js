/*
 * 织梦 · 西式资源点第二批 —— 贸易品：香草香料园 spices（番红花）、养蚕缫丝坊 silk
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWS2_core;
  var P = C.P, K = C.K, f = C.f, path = C.path, line = C.line, ell = C.ell, poly = C.poly, seg = C.seg, shade = C.shade;

  /** 一株番红花：短茎 + 紫花 + 红柱头 */
  function crocus(ctx, x, y) {
    return line(seg(x - 1.5, y, x, y - 3) + seg(x + 1.5, y, x, y - 3), 0.7, 0.8, P.leaf3) +
      ell(x, y - 4.2, 2.2, 1.7, P.saffron, 0.6) + ell(x - 0.5, y - 4.7, 0.9, 0.7, P.saffron2, 0) + ell(x + 0.6, y - 4.9, 0.6, 0.45, P.stigma, 0);
  }
  C.crocus = crocus;
  /** 编筐（梯形）+ 里面的东西 fillFn(x, y) */
  function basket(ctx, x, yb, w, h, fillFn) {
    var s = C.shadowEll(x + w * 0.55, yb, w * 0.6, 3.5);
    s += path(poly([[x, yb - h], [x + w, yb - h], [x + w - 3, yb], [x + 3, yb]]), P.thatch2, 1.3);
    s += line(seg(x + 1, yb - h * 0.6, x + w - 1, yb - h * 0.6) + seg(x + 2, yb - h * 0.25, x + w - 2, yb - h * 0.25), 0.7, 0.6);
    return s + (fillFn ? fillFn(x, yb - h) : '');
  }
  C.basket = basket;
  /** 筛子（圆托盘，俯视椭圆）上摊着红色柱头 */
  function sieve(ctx, cx, cy, rx, dots) {
    var s = ell(cx, cy, rx, rx * 0.4, P.wood, 1.2) + ell(cx, cy - 0.8, rx * 0.82, rx * 0.3, P.straw, 0.6);
    for (var i = 0; i < (dots || 10); i++) s += ell(cx + ctx.rnd(-rx * 0.7, rx * 0.7), cy - 0.8 + ctx.rnd(-rx * 0.2, rx * 0.2), 0.9, 0.5, P.stigma, 0);
    return s;
  }
  C.sieve = sieve;

  /* 香草香料园：番红花田 + 晒花棚（敞棚内筛架）+ 花筐 */
  C.def({
    idKind: 'site-saffron-garden', name: '番红花香料园', cat: 'site', resource: 'spices', subtype: 'saffron_garden', facility: null,
    w: 4, d: 3, up: 44, roof: 'gable_thatch', tags: ['saffron', 'crocus_field', 'drying_shed'],
    note: '番红花田 + 晒花棚；无对应 FacilityKind（田园型资源点）',
    draw: function (ctx, W, D) {
      var s = K.field(ctx, 8, D - 124, 116, D - 10, P.soil, 9, 7, crocus);
      // 田埂小径
      s += path(K.q(116, D - 124, 126, D - 10), P.yard, 0.8);
      // 晒花棚（敞棚）
      s += K.shed(ctx, 132, D - 76, 54, 28, 22, { open: true, roof: P.thatch, roof2: P.thatch2 });
      for (var j = 0; j < 3; j++) {
        s += path(K.q(136, D - 78 - 8 - j * 7, 182, D - 78 - 6 - j * 7), P.wood, 0.9);
        for (var i = 0; i < 8; i++) s += ell(139 + i * 5.6 + ctx.rnd(-1, 1), D - 79 - 7 - j * 7, 1.1, 0.6, P.stigma, 0);
      }
      // 前面的筛架（条凳 + 三只筛子）
      s += C.post(134, D - 18, 10, 2.4) + C.post(184, D - 18, 10, 2.4);
      s += C.block(130, D - 26, 58, 6, 3, P.wood, P.timber, 1.2);
      for (i = 0; i < 3; i++) s += sieve(ctx, 140 + i * 19, D - 33, 8, 7);
      // 花筐
      s += basket(ctx, 128, D - 6, 14, 9, function (x, y) { var t = ''; for (var k = 0; k < 6; k++) t += ell(x + 2 + k * 2, y - ctx.rnd(0, 2), 2, 1.5, P.saffron, 0.6); return t; });
      return s + C.tuft(ctx, 6, D - 4, 6, 4);
    }
  });
  C.def({
    idKind: 'prop-spice-flowerbasket', name: '番红花花筐', cat: 'prop', resource: 'spices', w: 1, d: 1, up: 12, tags: ['basket', 'crocus'],
    draw: function (ctx, W, D) {
      return basket(ctx, 10, D - 8, 28, 16, function (x, y) {
        var t = ''; for (var k = 0; k < 11; k++) t += ell(x + 3 + k * 2.2, y - ctx.rnd(0, 4), 2.4, 1.8, k % 3 ? P.saffron : P.saffron2, 0.6) + (k % 2 ? ell(x + 3 + k * 2.2, y - 3, 0.6, 0.4, P.stigma, 0) : '');
        return t;
      });
    }
  });
  C.def({
    idKind: 'prop-spice-sieve', name: '晒花筛架', cat: 'prop', resource: 'spices', w: 1, d: 1, up: 10, tags: ['sieve', 'trestle'],
    draw: function (ctx, W, D) {
      var s = shade(K.q(10, D - 9, 44, D - 6));
      s += C.post(10, D - 6, 12, 2.4) + C.post(38, D - 6, 12, 2.4) + C.block(6, D - 16, 36, 6, 3, P.wood, P.timber, 1.2);
      return s + sieve(ctx, 16, D - 23, 9, 9) + sieve(ctx, 33, D - 23, 8, 8);
    }
  });
  C.def({
    idKind: 'prop-spice-jars', name: '香料陶罐', cat: 'prop', resource: 'spices', w: 1, d: 1, up: 6, tags: ['jar', 'sealed'],
    draw: function (ctx, W, D) {
      var s = C.shadowEll(26, D - 8, 16, 4);
      [[14, 10, P.clay], [28, 12, P.clay2], [38, 8, P.clay]].forEach(function (j) {
        var x = j[0], h = j[1] + 6, y = D - 8;
        s += path('M' + f(x - 5) + ' ' + f(y) + 'Q' + f(x - 8) + ' ' + f(y - h * 0.6) + ' ' + f(x - 3) + ' ' + f(y - h) + 'L' + f(x + 3) + ' ' + f(y - h) +
          'Q' + f(x + 8) + ' ' + f(y - h * 0.6) + ' ' + f(x + 5) + ' ' + f(y) + 'Z', j[2], 1.2);
        s += ell(x, y - h, 3.4, 1.4, P.wash, 1) + line(seg(x - 3.5, y - h + 2.5, x + 3.5, y - h + 2.5), 0.9, 1, P.red);
      });
      return s;
    }
  });

  /** 桑树：矮截干（修剪成拳头状）+ 深绿树冠 */
  function mulberryTree(ctx, x, yb, r) { return K.tree(ctx, x, yb, r, P.leaf3, P.mulberry, 4, P.leaf); }
  /** 蚕茧：小白椭圆 */
  function cocoon(x, y) { return ell(x, y, 1.8, 1.1, P.silkw, 0.5); }
  /** 缫丝车：煮茧锅（小灶）+ 大绕丝轮 + 丝线 */
  function reel(ctx, x, yb) {
    var s = shade(K.q(x, yb - 4, x + 48, yb));
    // 灶 + 锅
    s += C.block(x, yb, 16, 6, 12, P.stone, P.stone2, 1.3) + path(K.q(x + 5, yb - 7, x + 11, yb - 2), '#2e241a', 0.8) + ell(x + 8, yb - 4, 2, 1.4, P.fire, 0);
    s += ell(x + 8, yb - 18, 7, 2.6, P.iron, 1.2) + ell(x + 8, yb - 18.4, 5.4, 1.8, P.water, 0);
    for (var i = 0; i < 4; i++) s += cocoon(x + 5 + i * 2.2, yb - 18.5 + (i % 2) * 0.6);
    // 绕丝轮架
    s += C.post(x + 26, yb, 24, 2.6) + C.post(x + 44, yb, 24, 2.6);
    s += ell(x + 35, yb - 22, 11, 11, 'none', 1.4) + ell(x + 35, yb - 22, 2, 2, P.dark, 0.8);
    var d = ''; for (i = 0; i < 6; i++) { var a = i * Math.PI / 3; d += seg(x + 35, yb - 22, x + 35 + Math.cos(a) * 11, yb - 22 + Math.sin(a) * 11); }
    s += line(d, 1, 1, P.timber) + line(C.ellD(x + 35, yb - 22, 9.5, 9.5), 2.2, 1, P.silkw);
    // 丝线从锅到轮
    return s + line(seg(x + 10, yb - 19, x + 26, yb - 31), 0.6, 0.9, P.silkw);
  }
  C.reel = reel;

  /* 养蚕缫丝坊：后排桑园 + 中右两层蚕室（多排气窗、木筋墙）+ 前左缫丝车 + 晒簇架 */
  C.def({
    idKind: 'site-silk-filature', name: '养蚕缫丝坊', cat: 'site', resource: 'silk', subtype: 'sericulture', facility: null,
    w: 4, d: 3, up: 64, roof: 'gable_tile', tags: ['mulberry', 'silkworm_house', 'reeling', 'two_storey'],
    note: '桑园 + 蚕室 + 缫丝车；无对应 FacilityKind（作坊型资源点，最近似 warehouse 但不是仓储）',
    draw: function (ctx, W, D) {
      var s = '';
      for (var i = 0; i < 5; i++) s += mulberryTree(ctx, 14 + i * 20, D - 108 - (i % 2) * 6, 10);
      for (i = 0; i < 4; i++) s += mulberryTree(ctx, 22 + i * 22, D - 80, 9);
      // 蚕室：两层，木筋墙，楼层间一排气窗
      var hx = 108, hy = D - 30, hw = 76;
      s += shade(poly([[hx + hw, hy], [hx + hw + 10, hy - 4], [hx + hw + 10, hy - 56], [hx + hw, hy - 52]]));
      s += path(K.q(hx, hy - 50, hx + hw, hy), P.plaster, 1.5);
      s += line(seg(hx, hy - 25, hx + hw, hy - 25) + seg(hx + hw / 3, hy - 50, hx + hw / 3, hy) + seg(hx + hw * 2 / 3, hy - 50, hx + hw * 2 / 3, hy) +
        seg(hx, hy - 50, hx + hw / 3, hy - 25) + seg(hx + hw, hy - 50, hx + hw * 2 / 3, hy - 25), 1.6, 1, P.timber);
      for (i = 0; i < 6; i++) s += path(K.q(hx + 5 + i * 12, hy - 44, hx + 11 + i * 12, hy - 40), '#2e241a', 0.8) + line(seg(hx + 5 + i * 12, hy - 42, hx + 11 + i * 12, hy - 42), 0.6, 0.7, P.wood);
      s += path(K.q(hx + 32, hy - 18, hx + 44, hy), P.dark, 1.1) + path(K.q(hx + 8, hy - 18, hx + 18, hy - 10), '#2e241a', 0.9) + path(K.q(hx + 58, hy - 18, hx + 68, hy - 10), '#2e241a', 0.9);
      s += C.roofGable(hx - 6, hx + hw + 6, hy - 48, hy - 72, 10, P.tile, P.red, 5);
      // 屋脊气楼（蚕室通风）
      s += path(K.q(hx + 26, hy - 80, hx + 50, hy - 71), P.wood, 1.2) + C.roofGable(hx + 22, hx + 54, hy - 78, hy - 86, 4, P.tile, P.red, 2);
      // 前左缫丝车 + 晒簇架
      s += reel(ctx, 20, D - 8);
      var rk = K.rack(78, D - 8, 22, 24, 3); s += rk.svg;
      rk.bars.forEach(function (y) { for (var k = 0; k < 5; k++) s += cocoon(81 + k * 4, y + 2); });
      return s + C.tuft(ctx, 6, D - 4, 5, 3) + C.tuft(ctx, W - 6, D - 4, 5, 3);
    }
  });
  C.def({
    idKind: 'prop-silk-cocoontray', name: '蚕匾（蚕茧）', cat: 'prop', resource: 'silk', w: 1, d: 1, up: 6, tags: ['tray', 'cocoon'],
    draw: function (ctx, W, D) {
      var s = C.shadowEll(26, D - 8, 19, 5) + ell(24, D - 12, 18, 7, P.thatch2, 1.3) + ell(24, D - 12.5, 15, 5.4, P.straw, 0.6);
      for (var i = 0; i < 16; i++) s += cocoon(24 + ctx.rnd(-12, 12), D - 12.5 + ctx.rnd(-3.4, 3.4));
      return s;
    }
  });
  C.def({
    idKind: 'prop-silk-reel', name: '缫丝车', cat: 'prop', resource: 'silk', w: 1, d: 1, up: 30, tags: ['reeling_wheel'],
    draw: function (ctx, W, D) { return reel(ctx, 0, D - 6); }
  });
  C.def({
    idKind: 'prop-silk-mulberry', name: '桑树', cat: 'prop', resource: 'silk', w: 1, d: 1, up: 30, tags: ['tree', 'mulberry'],
    draw: function (ctx, W, D) { return mulberryTree(ctx, 24, D - 8, 15); }
  });
})(typeof window !== 'undefined' ? window : this);
