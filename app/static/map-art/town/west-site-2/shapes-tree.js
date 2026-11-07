/*
 * 织梦 · 西式资源点第二批 —— 果木：grain/orchard 苹果园、grain/olive_grove 橄榄园（含榨油石磨）
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWS2_core;
  var P = C.P, K = C.K, f = C.f, path = C.path, line = C.line, ell = C.ell, poly = C.poly, seg = C.seg, shade = C.shade;

  function appleTree(ctx, x, yb, r) { return K.tree(ctx, x, yb, r, P.leaf, P.apple, 7, P.leaf2); }
  /** 橄榄树：扭曲双干 + 灰绿碎冠 */
  function oliveTree(ctx, x, yb, r) {
    var s = C.shadowEll(x + r * 0.5, yb, r * 0.9, r * 0.3);
    s += path('M' + f(x - 3) + ' ' + f(yb) + 'Q' + f(x - 5) + ' ' + f(yb - r * 0.5) + ' ' + f(x - 2) + ' ' + f(yb - r * 0.9) + 'L' + f(x + 1) + ' ' + f(yb - r * 0.9) +
      'Q' + f(x + 4) + ' ' + f(yb - r * 0.4) + ' ' + f(x + 3) + ' ' + f(yb) + 'Z', P.dark, 1);
    s += line(seg(x - 1, yb - r * 0.4, x - r * 0.4, yb - r * 0.95), 1.6, 1, P.dark);
    s += path(C.blob(ctx, x - r * 0.35, yb - r * 1.35, r * 0.6, r * 0.45, 6, 0.2), P.olive, 1.1) +
      path(C.blob(ctx, x + r * 0.35, yb - r * 1.45, r * 0.62, r * 0.5, 6, 0.2), P.olive, 1.1) +
      path(C.blob(ctx, x, yb - r * 1.7, r * 0.45, r * 0.3, 5, 0.2), P.olive2, 0.9);
    for (var i = 0; i < 5; i++) s += ell(x + ctx.rnd(-r * 0.7, r * 0.7), yb - r * 1.45 + ctx.rnd(-r * 0.3, r * 0.3), 0.9, 0.7, P.grape, 0);
    return s;
  }
  C.appleTree = appleTree; C.oliveTree = oliveTree;
  /** 梯子（靠树） */
  function ladder(x, yb, h) {
    var s = line(seg(x, yb, x + 6, yb - h) + seg(x + 6, yb, x + 12, yb - h), 1.2, 1, P.timber), d = '';
    for (var i = 1; i < 5; i++) d += seg(x + 6 * i / 5 + 0.5, yb - h * i / 5, x + 6 + 6 * i / 5 - 0.5, yb - h * i / 5);
    return s + line(d, 1, 1, P.timber);
  }
  /** 苹果筐 */
  function appleCrate(ctx, x, yb) {
    var s = C.block(x, yb, 18, 5, 9, P.wood, P.timber, 1.1);
    for (var i = 0; i < 6; i++) s += ell(x + 3 + i * 2.5, yb - 14 + (i % 2), 1.6, 1.4, P.apple, 0.5);
    return s;
  }
  /* 苹果园：成行苹果树（下层草地）+ 前右小果棚（敞棚内苹果筐）+ 梯子 + 苹果酒桶 */
  C.def({
    idKind: 'site-apple-orchard', name: '苹果园', cat: 'site', resource: 'grain', subtype: 'orchard', facility: null,
    w: 4, d: 3, up: 46, roof: 'gable_thatch', tags: ['apple_trees', 'fruit_shed', 'ladder', 'cider_barrels'],
    note: '果园 + 果棚；无对应 FacilityKind（按规范 16.2 归 grain）',
    draw: function (ctx, W, D) {
      var s = '';
      for (var r = 0; r < 3; r++) for (var i = 0; i < 5 - (r === 2 ? 2 : 0); i++) {
        var x = 20 + i * 38 + (r % 2) * 18, y = D - 104 + r * 36;
        s += appleTree(ctx, x, y, 12);
        for (var k = 0; k < 2; k++) s += ell(x + ctx.rnd(-10, 10), y + ctx.rnd(1, 4), 1.4, 1.1, P.apple, 0.4);
      }
      s += ladder(64, D - 32, 22);
      s += K.shed(ctx, 128, D - 8, 58, 24, 18, { open: true, roof: P.thatch, roof2: P.thatch2 });
      s += appleCrate(ctx, 134, D - 9) + appleCrate(ctx, 156, D - 9);
      s += K.barrel(W - 8, D - 6, 6, P.wood, 12);
      return s + C.tuft(ctx, 6, D - 4, 5, 3);
    }
  });
  C.def({
    idKind: 'prop-orchard-appletree', name: '苹果树', cat: 'prop', resource: 'grain', subtype: 'orchard', w: 1, d: 1, up: 24, tags: ['tree'],
    draw: function (ctx, W, D) { return appleTree(ctx, 24, D - 8, 15); }
  });
  C.def({
    idKind: 'prop-orchard-crates', name: '苹果筐', cat: 'prop', resource: 'grain', subtype: 'orchard', w: 1, d: 1, up: 6, tags: ['crate'],
    draw: function (ctx, W, D) { return shade(K.q(6, D - 10, 44, D - 6)) + appleCrate(ctx, 4, D - 8) + appleCrate(ctx, 24, D - 10) + appleCrate(ctx, 14, D - 22); }
  });
  C.def({
    idKind: 'prop-orchard-ladder', name: '果梯与果篮', cat: 'prop', resource: 'grain', subtype: 'orchard', w: 1, d: 1, up: 4, tags: ['ladder', 'basket'],
    draw: function (ctx, W, D) {
      return ladder(6, D - 6, 34) + C.basket(ctx, 24, D - 6, 16, 9, function (x, y) { var t = ''; for (var i = 0; i < 5; i++) t += ell(x + 3 + i * 2.6, y - (i % 2), 1.7, 1.5, P.apple, 0.5); return t; });
    }
  });

  /** 榨油石磨（立轮碾）：圆形石槽 + 立式石轮 + 中轴 + 推杆 */
  function olivePress(ctx, cx, yb, r) {
    var s = C.shadowEll(cx + 4, yb, r * 1.15, r * 0.4);
    s += path('M' + f(cx - r) + ' ' + f(yb - 8) + 'L' + f(cx - r) + ' ' + f(yb - 2) + 'A' + f(r) + ' ' + f(r * 0.38) + ' 0 0 0 ' + f(cx + r) + ' ' + f(yb - 2) +
      'L' + f(cx + r) + ' ' + f(yb - 8) + 'Z', P.stone2, 1.4);
    s += ell(cx, yb - 8, r, r * 0.38, P.stone, 1.4) + ell(cx, yb - 8, r * 0.78, r * 0.28, P.olive, 0.9);
    for (var i = 0; i < 8; i++) s += ell(cx + ctx.rnd(-r * 0.6, r * 0.6), yb - 8 + ctx.rnd(-r * 0.15, r * 0.15), 0.9, 0.7, P.grape, 0);
    // 中轴
    s += path(K.q(cx - 2, yb - 34, cx + 2, yb - 8), P.timber, 1);
    // 立式石轮（侧面看是竖椭圆）
    s += path(C.ellD(cx + r * 0.38, yb - 17, r * 0.24, r * 0.42), P.stone3, 1.4) + path(C.ellD(cx + r * 0.33, yb - 17, r * 0.2, r * 0.38), P.stone, 1.1);
    s += ell(cx + r * 0.33, yb - 17, 1.6, 1.6, P.dark, 0);
    // 推杆
    s += line(seg(cx, yb - 22, cx - r * 1.2, yb - 18), 2.2, 1, P.timber);
    return s;
  }
  C.olivePress = olivePress;
  /** 油罐（双耳陶罐） */
  function amphora(x, yb, h) {
    return C.shadowEll(x + 2, yb, 5, 1.6) + path('M' + f(x - 3) + ' ' + f(yb) + 'Q' + f(x - 7) + ' ' + f(yb - h * 0.55) + ' ' + f(x - 2) + ' ' + f(yb - h) + 'L' + f(x + 2) + ' ' + f(yb - h) +
      'Q' + f(x + 7) + ' ' + f(yb - h * 0.55) + ' ' + f(x + 3) + ' ' + f(yb) + 'Z', P.clay, 1.1) +
      line('M' + f(x - 2) + ' ' + f(yb - h * 0.85) + 'q-4 1 -3 5M' + f(x + 2) + ' ' + f(yb - h * 0.85) + 'q4 1 3 5', 0.9, 1);
  }
  /* 橄榄园：成行橄榄树（干土地）+ 前右敞棚下的榨油石磨 + 油罐 + 橄榄筐 */
  C.def({
    idKind: 'site-olive-grove', name: '橄榄园', cat: 'site', resource: 'grain', subtype: 'olive_grove', facility: 'mill',
    w: 4, d: 3, up: 50, roof: 'gable_tile', tags: ['olive_trees', 'olive_press', 'edge_runner', 'amphorae'],
    note: '橄榄树林 + 立轮榨油石磨（按 mill 记）；按规范 16.2 归 grain',
    draw: function (ctx, W, D) {
      var s = path(K.q(4, D - 140, W - 4, D - 4), '#d6c393', 0, 0.7);
      for (var r = 0; r < 3; r++) for (var i = 0; i < 5 - r; i++) {
        var x = 18 + i * 36 + (r % 2) * 16, y = D - 106 + r * 34;
        s += oliveTree(ctx, x, y, 13);
      }
      // 榨油棚：瓦顶敞棚 + 石磨
      s += K.shed(ctx, 112, D - 8, 74, 30, 20, { open: true, roof: P.tile, roof2: P.red, rows: 3 });
      s += olivePress(ctx, 146, D - 10, 22);
      s += amphora(122, D - 8, 14) + amphora(178, D - 8, 13);
      s += C.basket(ctx, 88, D - 6, 16, 9, function (x, y) { var t = ''; for (var k = 0; k < 6; k++) t += ell(x + 3 + k * 2, y - (k % 2), 1.2, 1, k % 2 ? P.olive : P.grape, 0.4); return t; });
      return s + C.tuft(ctx, 6, D - 4, 5, 3);
    }
  });
  C.def({
    idKind: 'prop-olive-tree', name: '橄榄树', cat: 'prop', resource: 'grain', subtype: 'olive_grove', w: 1, d: 1, up: 24, tags: ['tree'],
    draw: function (ctx, W, D) { return oliveTree(ctx, 24, D - 8, 16); }
  });
  C.def({
    idKind: 'prop-olive-press', name: '榨油石磨', cat: 'prop', resource: 'grain', subtype: 'olive_grove', facility: 'mill', w: 1, d: 1, up: 4, tags: ['olive_press'],
    note: '小型立轮碾，按 mill 记',
    draw: function (ctx, W, D) { return olivePress(ctx, 26, D - 6, 18); }
  });
  C.def({
    idKind: 'prop-olive-amphorae', name: '橄榄油罐', cat: 'prop', resource: 'grain', subtype: 'olive_grove', w: 1, d: 1, up: 4, tags: ['amphora'],
    draw: function (ctx, W, D) { return amphora(14, D - 12, 18) + amphora(30, D - 14, 20) + amphora(24, D - 4, 17); }
  });
})(typeof window !== 'undefined' ? window : this);
