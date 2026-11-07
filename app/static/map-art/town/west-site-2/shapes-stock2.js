/*
 * 织梦 · 西式资源点第二批 —— 牲畜（二）：livestock/goat_farm 山羊场、livestock/poultry_farm 鸡鸭场、livestock/apiary 养蜂场、
 * wool/sheep_station 羊场、horses/horse_stud 种马场
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWS2_core;
  var P = C.P, K = C.K, f = C.f, path = C.path, line = C.line, ell = C.ell, poly = C.poly, seg = C.seg, shade = C.shade;

  /** 山羊（瘦身、翘尾、后弯角、小胡子） */
  function goat(ctx, x, yb, flip) {
    var k = flip ? -1 : 1, X = function (d) { return x + k * d; };
    var s = C.shadowEll(x + 2, yb, 9, 2.2);
    s += line(seg(X(-6), yb - 7, X(-6), yb) + seg(X(-3), yb - 7, X(-3), yb) + seg(X(4), yb - 7, X(4), yb) + seg(X(7), yb - 7, X(7), yb), 1.3, 1, P.dark);
    s += path(poly([[X(-8), yb - 14], [X(7), yb - 14], [X(8), yb - 7], [X(-8), yb - 7]]), P.goat, 1.1);
    s += path(poly([[X(7), yb - 16], [X(12), yb - 15], [X(12), yb - 11], [X(8), yb - 11]]), P.goat, 1);
    s += line(seg(X(9), yb - 16, X(6), yb - 21) + seg(X(11), yb - 11, X(11), yb - 8), 1.1, 1, P.dark);
    return s + line(seg(X(-8), yb - 14, X(-10), yb - 17), 1.1, 1, P.dark);
  }
  /** 鸡（侧身小团 + 红冠） */
  function hen(ctx, x, yb, flip) {
    var k = flip ? -1 : 1;
    return C.shadowEll(x + 1, yb, 4, 1.2) + line(seg(x - 1, yb - 3, x - 1, yb) + seg(x + 1, yb - 3, x + 1, yb), 0.8, 1, P.amber) +
      ell(x, yb - 5, 4, 3, P.hen, 0.9) + ell(x + k * 3.5, yb - 8, 1.8, 1.7, P.hen, 0.8) +
      ell(x + k * 3.6, yb - 10, 1, 0.8, P.comb, 0) + path(poly([[x - k * 4, yb - 6], [x - k * 6, yb - 9], [x - k * 3, yb - 7]]), P.hen, 0.7);
  }
  /** 鸭（浮水，扁身 + 黄喙） */
  function duck(x, y, flip) {
    var k = flip ? -1 : 1;
    return ell(x, y, 5, 2.4, P.duck, 0.9) + ell(x + k * 4, y - 3, 2, 1.8, P.duck, 0.8) +
      path(poly([[x + k * 5.6, y - 3.4], [x + k * 8, y - 2.8], [x + k * 5.6, y - 2.2]]), P.amber, 0.5) + line(seg(x - 4, y + 2, x + 4, y + 2), 0.6, 0.6, P.water2);
  }
  C.goat = goat; C.hen = hen; C.duck = duck;

  /* 山羊场：坡地石墙围场（石砌矮墙）+ 后排石头羊舍 + 山羊群 + 站在岩块上的山羊 + 草料架 */
  C.def({
    idKind: 'site-goat-farm', name: '山羊场', cat: 'site', resource: 'livestock', subtype: 'goat_farm', facility: 'stable',
    w: 4, d: 3, up: 40, roof: 'gable_tile', tags: ['goats', 'drystone_wall', 'rocks', 'hay_rack'],
    note: '石墙围场 + 羊舍；牲畜棚最近 FacilityKind 为 stable',
    draw: function (ctx, W, D) {
      var s = path(K.q(6, D - 120, W - 6, D - 6), P.leaf2, 0, 0.3);
      s += K.shed(ctx, 20, D - 104, 80, 24, 20, { wall: P.stone, roof: P.tile, roof2: P.red, door: 'open', win: 2 });
      // 干砌石墙一圈（前沿、两侧）
      var d = '', i;
      [[6, D - 8, W - 6, D - 8, 22], [6, D - 112, 6, D - 8, 9], [W - 6, D - 112, W - 6, D - 8, 9]].forEach(function (w) {
        for (i = 0; i < w[4]; i++) { var t = i / w[4]; s += C.rock(ctx, w[0] + (w[2] - w[0]) * t + 4, w[1] + (w[3] - w[1]) * t, 4.5, P.stone, P.stone2, 0.9); }
      });
      // 岩块 + 站在上面的山羊
      s += C.rock(ctx, 150, D - 74, 18, P.stone, P.stone2, 1.4) + goat(ctx, 150, D - 90, true);
      s += C.rock(ctx, 120, D - 40, 11, P.stone2, P.stone3, 1.3);
      [[40, 64, 0], [70, 50, 1], [96, 70, 0], [56, 28, 0], [170, 34, 1], [110, 22, 1]].forEach(function (p) { s += goat(ctx, p[0], D - p[1], p[2]); });
      // 草料架
      s += C.post(162, D - 104, 18, 2.4) + C.post(190, D - 104, 18, 2.4) + K.stack(ctx, 176, D - 104, 10, P.straw, P.thatch2);
      return s + line(d, 0.5, 0.5);
    }
  });
  C.def({
    idKind: 'prop-goat-goats', name: '山羊', cat: 'prop', resource: 'livestock', subtype: 'goat_farm', w: 1, d: 1, up: 0, tags: ['animal', 'goat'],
    draw: function (ctx, W, D) { return goat(ctx, 16, D - 20, false) + goat(ctx, 30, D - 6, true); }
  });
  C.def({
    idKind: 'prop-goat-rock', name: '山羊与岩块', cat: 'prop', resource: 'livestock', subtype: 'goat_farm', w: 1, d: 1, up: 20, tags: ['rock', 'goat'],
    draw: function (ctx, W, D) { return C.rock(ctx, 24, D - 8, 16, P.stone, P.stone2, 1.3) + goat(ctx, 24, D - 22, false); }
  });
  C.def({
    idKind: 'prop-goat-milkstool', name: '挤羊奶凳与奶桶', cat: 'prop', resource: 'livestock', subtype: 'goat_farm', w: 1, d: 1, up: 2, tags: ['stool', 'pail'],
    draw: function (ctx, W, D) {
      return C.shadowEll(26, D - 8, 16, 3) + C.post(12, D - 8, 8, 1.6) + C.post(20, D - 8, 8, 1.6) + ell(16, D - 16, 7, 2.2, P.wood, 1) +
        K.barrel(34, D - 8, 6, P.wood, 10) + ell(34, D - 18, 4.4, 1.4, P.silkw, 0);
    }
  });

  /** 鸡舍：高脚小木屋 + 斜跳板 */
  function coop(ctx, x, yb, w) {
    var s = C.post(x + 3, yb, 12, 2.4) + C.post(x + w - 3, yb, 12, 2.4);
    s += K.shed(ctx, x, yb - 10, w, 18, 14, { wall: P.wood, roof: P.thatch, roof2: P.thatch2, door: 'open' });
    return s + line(seg(x + w / 2 - 3, yb - 10, x + w / 2 + 10, yb + 0), 2, 1, P.timber);
  }
  /* 鸡鸭场：后左高脚鸡舍 + 编栏鸡场 + 散鸡；右侧鸭塘与鸭群；前排食槽、蛋筐 */
  C.def({
    idKind: 'site-poultry-yard', name: '鸡鸭场', cat: 'site', resource: 'livestock', subtype: 'poultry_farm', facility: null,
    w: 4, d: 3, up: 40, roof: 'gable_thatch', tags: ['hen_house', 'duck_pond', 'hens', 'ducks'],
    note: '鸡舍 + 鸭塘；无对应 FacilityKind（禽舍不算 stable）',
    draw: function (ctx, W, D) {
      var s = path(K.q(6, D - 128, 110, D - 10), P.yard, 0, 0.8);
      s += coop(ctx, 14, D - 98, 54) + coop(ctx, 74, D - 104, 30);
      s += K.pond(ctx, 150, D - 68, 34, 22);
      [[136, D - 76, 0], [158, D - 62, 1], [168, D - 78, 1], [142, D - 56, 0]].forEach(function (p) { s += duck(p[0], p[1], p[2]); });
      s += duck(118, D - 44, 0);
      for (var i = 0; i < 9; i++) s += hen(ctx, 18 + ctx.rnd(0, 84), D - 70 + ctx.rnd(0, 52), i % 2);
      s += C.block(30, D - 20, 34, 6, 5, P.wood, P.timber, 1.1) + path(K.q(33, D - 30, 61, D - 27), P.wheat, 0.6);
      s += C.fence(6, D - 128, 110, D - 128, 8, 12) + C.fence(110, D - 128, 110, D - 10, 6, 12) + C.fence(6, D - 10, 110, D - 10, 8, 12);
      s += C.basket(ctx, 140, D - 8, 18, 9, function (x, y) { var t = ''; for (var k = 0; k < 5; k++) t += ell(x + 3 + k * 3, y - (k % 2), 1.6, 2, P.hen, 0.6); return t; });
      return s + C.tuft(ctx, W - 8, D - 4, 5, 3);
    }
  });
  C.def({
    idKind: 'prop-poultry-coop', name: '高脚鸡舍', cat: 'prop', resource: 'livestock', subtype: 'poultry_farm', w: 1, d: 1, up: 30, tags: ['hen_house'],
    draw: function (ctx, W, D) { return C.shadowEll(28, D - 8, 18, 3) + coop(ctx, 6, D - 8, 32) + hen(ctx, 40, D - 4, true); }
  });
  C.def({
    idKind: 'prop-poultry-hens', name: '鸡群', cat: 'prop', resource: 'livestock', subtype: 'poultry_farm', w: 1, d: 1, up: 0, tags: ['animal', 'hen'],
    draw: function (ctx, W, D) { return hen(ctx, 12, D - 26, 0) + hen(ctx, 32, D - 22, 1) + hen(ctx, 20, D - 12, 1) + hen(ctx, 38, D - 6, 0); }
  });
  C.def({
    idKind: 'prop-poultry-duckpond', name: '小鸭塘', cat: 'prop', resource: 'livestock', subtype: 'poultry_farm', w: 1, d: 1, up: 0, tags: ['pond', 'duck'],
    draw: function (ctx, W, D) { return K.pond(ctx, 24, D - 20, 19, 12) + duck(18, D - 22, 0) + duck(30, D - 16, 1); }
  });

  /** 草编蜂箱（skep）：钟形 + 横向草圈 + 入口 */
  function skep(x, yb, r) {
    var s = C.shadowEll(x + 2, yb, r * 1.1, r * 0.3);
    s += path('M' + f(x - r) + ' ' + f(yb) + 'Q' + f(x - r * 1.05) + ' ' + f(yb - r * 1.6) + ' ' + f(x) + ' ' + f(yb - r * 1.7) +
      'Q' + f(x + r * 1.05) + ' ' + f(yb - r * 1.6) + ' ' + f(x + r) + ' ' + f(yb) + 'Z', P.straw, 1.2);
    var d = ''; for (var i = 1; i < 4; i++) { var y = yb - r * 0.42 * i, hw = r * (1 - i * i * 0.06); d += seg(x - hw, y, x + hw, y); }
    return s + line(d, 0.8, 0.7, P.thatch2) + ell(x, yb - 2, 1.8, 1.4, '#2e241a', 0);
  }
  /** 蜂箱台：长条木台 + 一排 skep */
  function skepBench(x, yb, n) {
    var s = C.post(x + 2, yb, 6, 2.4) + C.post(x + n * 14 - 2, yb, 6, 2.4) + C.block(x - 2, yb - 5, n * 14 + 4, 4, 2, P.wood, P.timber, 1);
    for (var i = 0; i < n; i++) s += skep(x + 7 + i * 14, yb - 9, 6);
    return s;
  }
  C.skep = skep;
  /* 养蜂场：花草地里两排蜂箱台（草编蜂箱）+ 右后取蜜棚（敞棚内蜜桶、摇蜜架）+ 蜂群小点 */
  C.def({
    idKind: 'site-apiary', name: '养蜂场', cat: 'site', resource: 'livestock', subtype: 'apiary', facility: null,
    w: 4, d: 3, up: 40, roof: 'gable_thatch', tags: ['skeps', 'honey_shed', 'wildflowers', 'bees'],
    note: '草编蜂箱 + 取蜜棚；无对应 FacilityKind；按规范 16.2 归 livestock',
    draw: function (ctx, W, D) {
      // 野花草甸（浅绿底 + 一丛丛花）+ 编枝矮篱
      var s = path(C.blob(ctx, W * 0.5, D - 70, W * 0.47, 64, 10, 0.06), P.leaf2, 0, 0.45), i;
      for (i = 0; i < 26; i++) {
        var fx = ctx.rnd(10, W - 10), fy = ctx.rnd(D - 132, D - 8), col = ctx.pick([P.saffron2, P.wash, P.plaster, P.madder2, P.flax]);
        s += C.tuft(ctx, fx, fy, 5, 3, P.leaf3, 0.8) + ell(fx - 1.5, fy - 5, 1.5, 1.2, col, 0) + ell(fx + 1.6, fy - 4, 1.3, 1.1, col, 0);
      }
      s += C.fence(6, D - 132, W - 6, D - 132, 12, 10);
      s += skepBench(14, D - 92, 6) + skepBench(26, D - 48, 6);
      // 取蜜棚
      s += K.shed(ctx, 128, D - 64, 58, 28, 22, { open: true, roof: P.thatch, roof2: P.thatch2 });
      s += K.barrel(142, D - 66, 6, P.wood, 11) + ell(142, D - 77, 4.4, 1.4, P.honey, 0);
      s += C.block(154, D - 66, 24, 5, 10, P.wood, P.timber, 1.1);
      for (i = 0; i < 4; i++) s += path(K.q(156 + i * 5.5, D - 82, 160 + i * 5.5, D - 76), P.honey, 0.6);
      // 前右蜜罐
      s += K.barrel(140, D - 10, 7, P.clay, 12) + K.barrel(158, D - 8, 6, P.clay2, 10) + ell(158, D - 18, 4.4, 1.4, P.honey, 0);
      // 蜂群（小点）
      var d = ''; for (i = 0; i < 18; i++) { var x = ctx.rnd(20, 120), y = ctx.rnd(D - 120, D - 60); d += seg(x, y, x + 0.6, y); }
      s += line(d, 1.6, 0.85, P.dark);
      return s + C.tuft(ctx, 6, D - 4, 5, 3) + C.tuft(ctx, W - 8, D - 4, 5, 3);
    }
  });
  C.def({
    idKind: 'prop-apiary-skeps', name: '草编蜂箱台', cat: 'prop', resource: 'livestock', subtype: 'apiary', w: 1, d: 1, up: 4, tags: ['skep'],
    draw: function (ctx, W, D) { return shade(K.q(6, D - 9, 44, D - 6)) + skepBench(4, D - 8, 3); }
  });
  C.def({
    idKind: 'prop-apiary-honeypots', name: '蜜罐', cat: 'prop', resource: 'livestock', subtype: 'apiary', w: 1, d: 1, up: 2, tags: ['honey', 'jar'],
    draw: function (ctx, W, D) { return K.barrel(14, D - 12, 7, P.clay, 12) + K.barrel(32, D - 14, 7, P.clay2, 14) + ell(32, D - 28, 5, 1.6, P.honey, 0) + K.barrel(23, D - 4, 6, P.clay, 10); }
  });

  /** 羊（羊毛团 + 黑脸；剪过毛的 shorn=true 身子瘦小、偏米色） */
  function sheep(ctx, x, yb, flip, shorn) {
    var k = flip ? -1 : 1;
    var s = C.shadowEll(x + 2, yb, 9, 2.4);
    s += line(seg(x - 5, yb - 6, x - 5, yb) + seg(x - 1, yb - 6, x - 1, yb) + seg(x + 3, yb - 6, x + 3, yb) + seg(x + 6, yb - 6, x + 6, yb), 1.4, 1, P.coal);
    s += shorn ? ell(x, yb - 9, 7, 4, P.bone2, 1.1) : path(C.blob(ctx, x, yb - 9, 9, 5.5, 7, 0.12), P.wool, 1.1);
    return s + ell(x + k * (shorn ? 8 : 10), yb - 11, 3.2, 2.6, P.coal, 0.8);
  }
  C.sheepW = sheep;
  /* 羊场：后排长条剪毛棚（敞面，棚内剪毛台 + 剪过的羊）+ 前半羊群围栏 + 羊毛捆 */
  C.def({
    idKind: 'site-sheep-station', name: '羊场', cat: 'site', resource: 'wool', subtype: 'sheep_station', facility: 'stable',
    w: 5, d: 3, up: 46, roof: 'gable_thatch', tags: ['shearing_shed', 'sheep_pen', 'wool_bales', 'sheep'],
    note: '剪毛棚 + 羊群围栏；牲畜棚最近 FacilityKind 为 stable',
    draw: function (ctx, W, D) {
      var s = path(K.q(8, D - 70, W - 8, D - 6), P.leaf2, 0, 0.35);
      // 剪毛棚
      s += K.shed(ctx, 16, D - 82, 150, 30, 24, { open: true, roof: P.thatch, roof2: P.thatch2 });
      s += C.block(40, D - 84, 40, 5, 6, P.wood, P.timber, 1.1) + C.block(96, D - 84, 40, 5, 6, P.wood, P.timber, 1.1);
      s += sheep(ctx, 60, D - 92, false, true) + sheep(ctx, 116, D - 92, true, false);
      // 羊毛捆（方包）
      for (var i = 0; i < 4; i++) s += C.block(180 + (i % 2) * 22, D - 84 + Math.floor(i / 2) * 2 - Math.floor(i / 2) * 14, 20, 6, 12, P.wool, P.bone2, 1.2);
      // 前半围栏 + 羊群
      s += C.fence(8, D - 70, W - 8, D - 70, 16, 12) + C.fence(8, D - 70, 8, D - 6, 3, 12) + C.fence(W - 8, D - 70, W - 8, D - 6, 3, 12);
      [[30, 50, 0], [52, 40, 1], [76, 54, 0], [100, 34, 1], [124, 50, 0], [150, 30, 1], [176, 48, 0], [200, 36, 1], [222, 54, 0], [64, 20, 1], [140, 16, 0], [196, 14, 1]]
        .forEach(function (p, j) { s += sheep(ctx, p[0], D - p[1], p[2], j % 5 === 4); });
      s += C.fence(8, D - 6, 100, D - 6, 6, 12) + C.fence(140, D - 6, W - 8, D - 6, 6, 12);
      return s;
    }
  });
  C.def({
    idKind: 'prop-wool-bales', name: '羊毛捆', cat: 'prop', resource: 'wool', subtype: 'sheep_station', w: 1, d: 1, up: 10, tags: ['wool', 'bale'],
    draw: function (ctx, W, D) {
      return shade(K.q(8, D - 9, 46, D - 5)) + C.block(4, D - 6, 20, 6, 12, P.wool, P.bone2, 1.2) + C.block(24, D - 8, 20, 6, 12, P.wool, P.bone2, 1.2) +
        C.block(13, D - 24, 20, 6, 10, P.wool, P.bone2, 1.2);
    }
  });
  C.def({
    idKind: 'prop-wool-flock', name: '羊群', cat: 'prop', resource: 'wool', subtype: 'sheep_station', w: 1, d: 1, up: 0, tags: ['animal', 'sheep'],
    draw: function (ctx, W, D) { return sheep(ctx, 16, D - 24, false) + sheep(ctx, 32, D - 16, true) + sheep(ctx, 18, D - 6, false, true); }
  });
  C.def({
    idKind: 'prop-wool-shearstand', name: '剪毛台', cat: 'prop', resource: 'wool', subtype: 'sheep_station', w: 1, d: 1, up: 8, tags: ['shearing'],
    draw: function (ctx, W, D) {
      var s = shade(K.q(8, D - 9, 44, D - 6)) + C.block(6, D - 6, 36, 6, 8, P.wood, P.timber, 1.2);
      return s + sheep(ctx, 22, D - 20, false, true) + path(C.blob(ctx, 38, D - 22, 6, 3, 6, 0.15), P.wool, 0.9);
    }
  });

  /** 马（侧身简化轮廓） */
  function horse(ctx, x, yb, fill, flip) {
    var k = flip ? -1 : 1, X = function (dx) { return f(x + k * dx); };
    var s = C.shadowEll(x + 2, yb, 14, 3);
    s += line('M' + X(-9) + ' ' + f(yb - 12) + 'L' + X(-10) + ' ' + f(yb) + 'M' + X(-5) + ' ' + f(yb - 12) + 'L' + X(-4) + ' ' + f(yb) +
      'M' + X(6) + ' ' + f(yb - 12) + 'L' + X(7) + ' ' + f(yb) + 'M' + X(10) + ' ' + f(yb - 12) + 'L' + X(11) + ' ' + f(yb), 2, 1, P.dark);
    s += path('M' + X(-12) + ' ' + f(yb - 20) + 'Q' + X(0) + ' ' + f(yb - 24) + ' ' + X(10) + ' ' + f(yb - 20) + 'L' + X(15) + ' ' + f(yb - 30) +
      'L' + X(20) + ' ' + f(yb - 27) + 'L' + X(14) + ' ' + f(yb - 14) + 'Q' + X(0) + ' ' + f(yb - 10) + ' ' + X(-12) + ' ' + f(yb - 13) + 'Z', fill, 1.2);
    s += line('M' + X(-12) + ' ' + f(yb - 19) + 'q' + f(-k * 5) + ' 3 ' + f(-k * 4) + ' 10', 1.6, 1, P.dark);
    return s + line('M' + X(11) + ' ' + f(yb - 22) + 'L' + X(15) + ' ' + f(yb - 30), 1.6, 1, P.dark);
  }
  C.horseW = horse;
  /* 种马场：后排长马厩（木筋墙、多扇半截门、马探头）+ 前右圆形训练圈（沙地 + 圈栏 + 中心桩与马）+ 前左饮水槽 */
  C.def({
    idKind: 'site-horse-stud', name: '种马场', cat: 'site', resource: 'horses', subtype: 'horse_stud', facility: 'stable',
    w: 5, d: 3, up: 56, roof: 'gable_tile', tags: ['stable_block', 'lunging_ring', 'stud', 'water_trough'],
    note: '马厩 + 训练圈，facility 为 stable',
    draw: function (ctx, W, D) {
      var hx = 12, hy = D - 92, hw = 140;
      var s = K.shed(ctx, hx, hy, hw, 30, 26, { wall: P.plaster, timber: true, roof: P.tile, roof2: P.red, door: 'none', rows: 5 });
      for (var i = 0; i < 5; i++) {
        var dx = hx + 8 + i * 27;
        s += path(K.q(dx, hy - 22, dx + 16, hy), P.dark, 1.1) + path(K.q(dx, hy - 22, dx + 16, hy - 12), '#2e241a', 0.9);
        s += path(poly([[dx + 3, hy - 12], [dx + 6, hy - 20], [dx + 11, hy - 19], [dx + 12, hy - 12]]), i % 2 ? P.dark : P.wood, 0.8);
      }
      // 训练圈
      var rx = 186, ry = D - 46;
      s += ell(rx, ry, 50, 34, P.yard, 1.2) + ell(rx, ry, 42, 27, '#dcc79c', 0.6, 0.8);
      s += C.post(rx, ry, 18, 3) + line(seg(rx, ry - 14, rx - 24, ry + 6), 0.7, 0.9);
      s += horse(ctx, rx - 26, ry + 10, P.wood, false);
      var d = '';
      for (i = 0; i < 16; i++) { var a = Math.PI + i * Math.PI / 15; d += seg(rx + Math.cos(a) * 50, ry + Math.sin(a) * 34 * -1 + 0, rx + Math.cos(a) * 50, ry + Math.sin(a) * -34 - 10); }
      s += line(d, 1.6, 1, P.timber) + line(C.ellD(rx, ry - 8, 50, 34), 1.4, 1, P.dark);
      // 前左：饮水槽 + 拴马桩上的马
      s += C.block(20, D - 12, 40, 7, 7, P.wood, P.timber, 1.2) + path(K.q(23, D - 23, 57, D - 20), P.water, 0.8);
      s += horse(ctx, 92, D - 14, P.cow2, true) + horse(ctx, 120, D - 40, P.goat, false) + C.post(70, D - 10, 16, 3);
      return s;
    }
  });
  C.def({
    idKind: 'prop-horse-mare', name: '母马与小马', cat: 'prop', resource: 'horses', subtype: 'horse_stud', w: 1, d: 1, up: 4, tags: ['animal', 'horse', 'foal'],
    draw: function (ctx, W, D) {
      var s = horse(ctx, 20, D - 12, P.wood, false);
      return s + '<g transform="translate(34 ' + (D - 4) + ') scale(0.6) translate(-34 ' + (-(D - 4)) + ')">' + horse(ctx, 34, D - 4, P.goat, true) + '</g>';
    }
  });
  C.def({
    idKind: 'prop-horse-saddlerack', name: '马鞍架', cat: 'prop', resource: 'horses', subtype: 'horse_stud', w: 1, d: 1, up: 8, tags: ['saddle', 'tack'],
    draw: function (ctx, W, D) {
      var s = shade(K.q(8, D - 9, 44, D - 6)) + C.post(10, D - 6, 20, 2.6) + C.post(38, D - 6, 20, 2.6) + line(seg(8, D - 26, 40, D - 26), 2.2, 1, P.dark);
      s += path('M12 ' + (D - 26) + 'Q14 ' + (D - 34) + ' 22 ' + (D - 32) + 'Q30 ' + (D - 30) + ' 32 ' + (D - 26) + 'L30 ' + (D - 14) + 'L14 ' + (D - 14) + 'Z', P.red, 1.2);
      return s + line(seg(22, D - 26, 22, D - 10) + 'M20 ' + (D - 10) + 'h4', 0.9, 1, P.iron);
    }
  });
  C.def({
    idKind: 'prop-horse-haynet', name: '草料栏', cat: 'prop', resource: 'horses', subtype: 'horse_stud', w: 1, d: 1, up: 14, tags: ['hay', 'rack'],
    draw: function (ctx, W, D) {
      var s = C.post(8, D - 6, 24, 2.6) + C.post(40, D - 6, 24, 2.6) + K.stack(ctx, 24, D - 12, 13, P.straw, P.thatch2);
      var d = ''; for (var i = 0; i < 6; i++) d += seg(10 + i * 5.6, D - 30, 10 + i * 5.6, D - 12);
      return s + line(d + seg(8, D - 30, 40, D - 30), 1.2, 1, P.timber);
    }
  });
})(typeof window !== 'undefined' ? window : this);
