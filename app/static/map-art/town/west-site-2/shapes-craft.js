/*
 * 织梦 · 西式资源点第二批 —— 作坊：象牙作坊与牙料仓 ivory（只画收购、仓储、雕刻）、染料场 dye（菘蓝、茜草）
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWS2_core;
  var P = C.P, K = C.K, f = C.f, path = C.path, line = C.line, ell = C.ell, poly = C.poly, seg = C.seg, shade = C.shade;

  /** 一根牙料（弯月形，横放）：x 左端，y 中线，L 长 */
  function tusk(x, y, L, flip) {
    var k = flip ? -1 : 1, X = function (d) { return f(x + k * d); };
    return path('M' + X(0) + ' ' + f(y - 2.6) + 'Q' + X(L * 0.6) + ' ' + f(y - 5) + ' ' + X(L) + ' ' + f(y - 7) +
      'Q' + X(L * 0.62) + ' ' + f(y + 0.4) + ' ' + X(0) + ' ' + f(y + 2.6) + 'Z', P.ivory, 1.1) +
      ell(x, y, 1.4, 2.6, P.ivory2, 0.9);
  }
  C.tusk = tusk;
  /** 一摞牙料（交错叠放） */
  function tuskStack(x, yb, n) {
    var s = shade(K.q(x, yb - 3, x + 40, yb));
    for (var i = 0; i < n; i++) s += tusk(x + (i % 2) * 4, yb - 4 - i * 4.2, 32 + (i % 3) * 3, false);
    return s;
  }
  C.tuskStack = tuskStack;
  /** 秤（收购用）：立柱 + 横杆 + 两只秤盘 */
  function scale(x, yb) {
    var s = C.post(x, yb, 26, 3) + line(seg(x - 14, yb - 24, x + 14, yb - 26), 1.6, 1, P.dark);
    s += line(seg(x - 14, yb - 24, x - 17, yb - 14) + seg(x - 14, yb - 24, x - 11, yb - 14) + seg(x + 14, yb - 26, x + 11, yb - 16) + seg(x + 14, yb - 26, x + 17, yb - 16), 0.6, 0.9);
    return s + ell(x - 14, yb - 14, 5, 1.6, P.iron, 1) + ell(x + 14, yb - 16, 5, 1.6, P.iron, 1);
  }

  /* 象牙作坊：后排石砌牙料仓（铁皮门、小高窗）+ 前右雕刻作坊敞棚（工作台、刻好的小件）+ 前左收购秤与牙料摞 */
  C.def({
    idKind: 'site-ivory-workshop', name: '象牙作坊与牙料仓', cat: 'site', resource: 'ivory', subtype: 'carving_workshop', facility: 'warehouse',
    w: 4, d: 3, up: 60, roof: 'gable_tile', tags: ['ivory_store', 'carving', 'trade_scale'],
    note: '只画收购、仓储、雕刻作坊，不画猎取；仓库按 warehouse 记',
    draw: function (ctx, W, D) {
      var s = path(K.q(6, D - 136, W - 6, D - 4), P.yard, 0, 0.8);
      // 牙料仓（石墙、铁箍门）
      var hx = 14, hy = D - 76, hw = 92;
      s += shade(poly([[hx + hw, hy], [hx + hw + 10, hy - 4], [hx + hw + 10, hy - 40], [hx + hw, hy - 36]]));
      s += path(K.q(hx, hy - 36, hx + hw, hy), P.stone, 1.5);
      var d = ''; for (var r = 1; r < 4; r++) for (var c = 0; c < 6; c++) d += seg(hx + c * 16 + (r % 2) * 8, hy - r * 9, hx + c * 16 + (r % 2) * 8, hy - r * 9 + 9);
      for (r = 1; r < 4; r++) d += seg(hx, hy - r * 9, hx + hw, hy - r * 9);
      s += line(d, 0.7, 0.45);
      s += path(K.q(hx + 38, hy - 22, hx + 56, hy), P.dark, 1.3) + line(seg(hx + 38, hy - 16, hx + 56, hy - 16) + seg(hx + 38, hy - 6, hx + 56, hy - 6), 1.4, 1, P.iron);
      s += path(K.q(hx + 10, hy - 32, hx + 20, hy - 28), '#2e241a', 0.8) + path(K.q(hx + 72, hy - 32, hx + 82, hy - 28), '#2e241a', 0.8);
      s += C.roofGable(hx - 6, hx + hw + 6, hy - 34, hy - 60, 10, P.tile, P.red, 5);
      // 雕刻作坊敞棚
      s += K.shed(ctx, 124, D - 34, 62, 26, 20, { open: true, roof: P.slate, roof2: P.slate2 });
      s += C.block(130, D - 36, 50, 6, 4, P.wood, P.timber, 1.1);
      s += tusk(134, D - 45, 22, false) + ell(164, D - 45, 3, 2.4, P.ivory, 0.9) + path(poly([[171, D - 42], [173, D - 50], [176, D - 42]]), P.ivory, 0.9);
      // 前左：收购秤 + 牙料摞 + 木箱
      s += scale(40, D - 8) + tuskStack(70, D - 8, 4);
      s += C.block(122, D - 6, 16, 8, 10, P.wood, P.timber, 1.2) + C.block(140, D - 6, 14, 8, 8, P.wood, P.timber, 1.2);
      return s + C.tuft(ctx, 6, D - 4, 5, 3) + C.tuft(ctx, W - 6, D - 4, 5, 3);
    }
  });
  C.def({
    idKind: 'prop-ivory-stack', name: '牙料摞', cat: 'prop', resource: 'ivory', w: 1, d: 1, up: 18, tags: ['raw_ivory', 'stack'],
    draw: function (ctx, W, D) { return tuskStack(4, D - 8, 5); }
  });
  C.def({
    idKind: 'prop-ivory-scale', name: '收购秤', cat: 'prop', resource: 'ivory', w: 1, d: 1, up: 22, tags: ['scale', 'trade'],
    draw: function (ctx, W, D) { return C.shadowEll(26, D - 7, 16, 3) + scale(24, D - 6); }
  });
  C.def({
    idKind: 'prop-ivory-crate', name: '牙雕成品箱', cat: 'prop', resource: 'ivory', w: 1, d: 1, up: 10, tags: ['crate', 'carvings'],
    draw: function (ctx, W, D) {
      var s = shade(K.q(10, D - 9, 44, D - 5)) + C.block(8, D - 6, 32, 10, 12, P.wood, P.timber, 1.3);
      s += path(K.q(11, D - 27, 37, D - 19), P.straw, 0.6);
      return s + ell(16, D - 24, 2.6, 2, P.ivory, 0.8) + ell(24, D - 25, 2.2, 2.6, P.ivory, 0.8) + path(poly([[29, D - 21], [31, D - 29], [34, D - 21]]), P.ivory, 0.8);
    }
  });

  /** 一束茜草根（红褐色，挂在杆上下垂） */
  function madderBundle(x, y) {
    var d = ''; for (var i = 0; i < 5; i++) d += 'M' + f(x - 2 + i) + ' ' + f(y) + 'q' + f(i - 2) + ' 5 ' + f((i - 2) * 0.6) + ' ' + f(9 + (i % 2) * 2);
    return line(d, 1.3, 1, P.madder) + line(seg(x - 3, y + 1, x + 3, y + 1), 1.4, 1, P.dark);
  }
  /** 一匹晾布（从横杆垂下的长条，下沿微波） */
  function cloth(x, y, w, h, fill) {
    return path('M' + f(x) + ' ' + f(y) + 'L' + f(x + w) + ' ' + f(y) + 'L' + f(x + w) + ' ' + f(y + h) + 'Q' + f(x + w * 0.75) + ' ' + f(y + h + 2) + ' ' + f(x + w * 0.5) + ' ' + f(y + h) +
      'Q' + f(x + w * 0.25) + ' ' + f(y + h - 2) + ' ' + f(x) + ' ' + f(y + h) + 'Z', fill, 1.1) + line(seg(x + w * 0.5, y + 2, x + w * 0.5, y + h - 3), 0.6, 0.4);
  }
  /* 染料场：后左菘蓝发酵池（两格石池，蓝色液面 + 泡沫）、后右茜草根晾架、前排染布晾杆（蓝、红、本色）+ 染缸 */
  C.def({
    idKind: 'site-dye-works', name: '染料场', cat: 'site', resource: 'dye', subtype: 'woad_madder', facility: null,
    w: 4, d: 3, up: 56, tags: ['woad_vat', 'madder_rack', 'cloth_poles', 'dye_vat'],
    note: '菘蓝发酵池 + 茜草根晾架 + 染布晾杆；无对应 FacilityKind（最近似 tannery，但不是制革）',
    draw: function (ctx, W, D) {
      var s = path(K.q(6, D - 138, W - 6, D - 4), P.yard, 0, 0.75);
      // 菘蓝发酵池（两格）
      s += K.basin(12, D - 92, 40, 22, P.woad) + K.basin(56, D - 92, 40, 22, P.woad2);
      for (var i = 0; i < 6; i++) s += ell(18 + ctx.rnd(0, 72), D - 104 + ctx.rnd(-3, 3), 1.6, 0.9, P.woad2, 0.4);
      // 池边一堆菘蓝叶
      s += path(C.blob(ctx, 34, D - 72, 14, 5, 6, 0.15), P.leaf, 1.1) + path(C.blob(ctx, 30, D - 74, 7, 2.5, 5, 0.15), P.leaf2, 0);
      // 茜草根晾架（两层）
      var rk = K.rack(116, D - 74, 66, 40, 2); s += rk.svg;
      rk.bars.forEach(function (y) { for (var k = 0; k < 7; k++) s += madderBundle(122 + k * 9, y); });
      // 前排晾布杆
      s += C.post(10, D - 8, 42, 3) + C.post(150, D - 8, 42, 3) + line(seg(8, D - 48, 152, D - 48), 1.8, 1, P.dark);
      var cols = [P.woad, P.woad2, P.madder, P.madder2, P.plaster, P.woad];
      for (i = 0; i < 6; i++) s += cloth(16 + i * 22, D - 48, 18, 30 - (i % 2) * 4, cols[i]);
      // 染缸（前右）
      s += K.barrel(170, D - 6, 11, P.clay2, 16) + ell(170, D - 22, 8.5, 2.6, P.madder, 0);
      s += K.barrel(W - 10, D - 6, 8, P.clay2, 12) + ell(W - 10, D - 18, 6, 2, P.woad, 0);
      return s + C.tuft(ctx, 6, D - 4, 5, 3);
    }
  });
  C.def({
    idKind: 'prop-dye-vat', name: '染缸', cat: 'prop', resource: 'dye', w: 1, d: 1, up: 12, tags: ['vat', 'woad'],
    draw: function (ctx, W, D) {
      var s = K.barrel(24, D - 8, 14, P.clay2, 18) + ell(24, D - 26, 11, 3.6, P.woad, 0);
      return s + line(seg(30, D - 26, 40, D - 44), 1.6, 1, P.timber);
    }
  });
  C.def({
    idKind: 'prop-dye-madderrack', name: '茜草根晾架', cat: 'prop', resource: 'dye', w: 1, d: 1, up: 24, tags: ['rack', 'madder_root'],
    draw: function (ctx, W, D) {
      var rk = K.rack(8, D - 6, 32, 34, 2), s = C.shadowEll(26, D - 6, 18, 3) + rk.svg;
      rk.bars.forEach(function (y) { for (var k = 0; k < 4; k++) s += madderBundle(12 + k * 8, y); });
      return s;
    }
  });
  C.def({
    idKind: 'prop-dye-clothpole', name: '染布晾杆', cat: 'prop', resource: 'dye', w: 1, d: 1, up: 30, tags: ['cloth', 'drying'],
    draw: function (ctx, W, D) {
      var s = C.post(6, D - 6, 40, 2.6) + C.post(42, D - 6, 40, 2.6) + line(seg(4, D - 44, 44, D - 44), 1.6, 1, P.dark);
      return s + cloth(9, D - 44, 14, 28, P.woad) + cloth(25, D - 44, 14, 24, P.madder);
    }
  });
  C.groundSet({
    idKind: 'ground-dyeyard', name: '染坊泼染地', resource: 'dye', base: '#d2bf95',
    scatter: function (ctx, v) { return C.scatter(ctx, 3, 'b').concat(C.scatter(ctx, 2, 'r'), C.scatter(ctx, 5, 'p')); },
    item: function (sub, it, x, y) {
      if (it.t === 'p') return ell(x, y, 1.2, 0.7, P.yard2, 0);
      return path(C.blob(sub, x, y, sub.rnd(3, 5), sub.rnd(1.4, 2.2), 5, 0.25), it.t === 'b' ? P.woad2 : P.madder2, 0, 0.55);
    }
  });
})(typeof window !== 'undefined' ? window : this);
