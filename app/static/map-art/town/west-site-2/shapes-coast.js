/*
 * 织梦 · 西式资源点第二批 —— 采珠 pearls：蚝床浅滩、采珠小艇、开蚌台
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWS2_core;
  var P = C.P, K = C.K, f = C.f, path = C.path, line = C.line, ell = C.ell, poly = C.poly, seg = C.seg, shade = C.shade;

  /** 一只蚝 / 珠母贝（扁椭圆 + 纹） */
  function oyster(ctx, x, y, r, open) {
    var s = ell(x, y, r, r * 0.55, P.shell, 0.9) + line(seg(x - r * 0.6, y - r * 0.1, x + r * 0.5, y - r * 0.25), 0.5, 0.6);
    if (open) s += ell(x + r * 0.2, y - r * 0.55, r * 0.8, r * 0.4, P.pearl, 0.7) + ell(x + r * 0.2, y - r * 0.55, r * 0.22, r * 0.2, '#ffffff', 0.4);
    return s;
  }
  C.oyster = oyster;
  /** 小艇（侧视，船头朝右）：船身 + 坐板 + 桨 */
  function skiff(ctx, x, y, L, flip) {
    var k = flip ? -1 : 1, X = function (d) { return f(x + k * d); };
    var s = ell(x, y + 1, L * 0.55, 2.2, P.water2, 0);
    s += path('M' + X(-L / 2) + ' ' + f(y - 7) + 'L' + X(L / 2 + 2) + ' ' + f(y - 9) + 'Q' + X(L / 2 - 3) + ' ' + f(y + 1) + ' ' + X(L / 2 - 10) + ' ' + f(y + 1) +
      'L' + X(-L / 2 + 5) + ' ' + f(y + 1) + 'Q' + X(-L / 2) + ' ' + f(y - 2) + ' ' + X(-L / 2) + ' ' + f(y - 7) + 'Z', P.wood, 1.4);
    s += line('M' + X(-L / 2 + 1) + ' ' + f(y - 4) + 'L' + X(L / 2 - 2) + ' ' + f(y - 5), 0.8, 0.6);
    s += path('M' + X(-L / 2 + 2) + ' ' + f(y - 7) + 'L' + X(L / 2) + ' ' + f(y - 8.6) + 'L' + X(L / 2 - 2) + ' ' + f(y - 6.4) + 'L' + X(-L / 2 + 3) + ' ' + f(y - 5.4) + 'Z', P.dark, 0.8);
    s += line(seg(x - k * 4, y - 9, x + k * 10, y + 4), 1.4, 1, P.timber);
    return s;
  }
  C.skiff = skiff;
  /** 蚝床桩：浅水里一排木桩 + 绳 */
  function stakes(x0, x1, y, n) {
    var s = '', dx = (x1 - x0) / n;
    s += line(seg(x0, y - 7, x1, y - 7), 0.8, 0.8, P.dark);
    for (var i = 0; i <= n; i++) s += C.post(x0 + dx * i, y, 10, 2.2) + line(seg(x0 + dx * i - 3, y + 0.5, x0 + dx * i + 3, y + 0.5), 0.7, 0.7, P.water2);
    return s;
  }

  /* 采珠场：后半是浅滩水面（蚝床桩 + 两条小艇），前半是沙岸（开蚌台、草棚、贝壳堆） */
  C.def({
    idKind: 'site-pearl-oysterbed', name: '采珠场', cat: 'site', resource: 'pearls', subtype: 'oyster_bed', facility: 'dock',
    w: 4, d: 3, up: 40, roof: 'gable_thatch', tags: ['oyster_bed', 'shallows', 'skiff', 'shucking_table', 'jetty'],
    note: '浅滩蚝床 + 采珠小艇 + 开蚌台；小栈桥按 dock 记',
    draw: function (ctx, W, D) {
      // 浅滩水面（占地后 2/3），岸线手绘起伏
      var shore = 'M0 ' + f(D - 58) + 'Q' + f(W * 0.25) + ' ' + f(D - 50) + ' ' + f(W * 0.5) + ' ' + f(D - 60) + 'Q' + f(W * 0.75) + ' ' + f(D - 68) + ' ' + f(W) + ' ' + f(D - 56);
      var s = path('M0 0L' + W + ' 0L' + W + ' ' + f(D - 56) + 'Q' + f(W * 0.75) + ' ' + f(D - 68) + ' ' + f(W * 0.5) + ' ' + f(D - 60) + 'Q' + f(W * 0.25) + ' ' + f(D - 50) + ' 0 ' + f(D - 58) + 'Z', P.water, 0);
      // 沙岸
      s += path(shore + 'L' + W + ' ' + D + 'L0 ' + D + 'Z', '#ddcda2', 0);
      s += line(shore, 1.6, 1);
      // 水纹
      var d = ''; for (var i = 0; i < 9; i++) { var x = ctx.rnd(10, W - 30), y = ctx.rnd(-30, D - 80); d += seg(x, y, x + ctx.rnd(8, 16), y); }
      s += line(d, 0.8, 0.7, P.water2);
      // 蚝床：浅水下的贝壳团 + 两排桩
      for (i = 0; i < 14; i++) s += oyster(ctx, ctx.rnd(20, W - 80), ctx.rnd(-20, D - 78), ctx.rnd(2, 3), false);
      s += stakes(16, W - 90, D - 98, 6) + stakes(30, W - 70, D - 72, 7);
      // 两条采珠小艇
      s += skiff(ctx, W - 50, D - 104, 40, true) + skiff(ctx, W - 40, D - 76, 34, false);
      // 小栈桥（从沙岸伸进水里）
      s += path(K.q(W - 70, D - 88, W - 58, D - 50), P.wood, 1.3);
      d = ''; for (i = 1; i < 8; i++) d += seg(W - 70, D - 88 + i * 5, W - 58, D - 88 + i * 5); s += line(d, 0.7, 0.6);
      s += C.post(W - 71, D - 84, 8, 2.2) + C.post(W - 57, D - 84, 8, 2.2);
      // 沙岸前：开蚌台（条凳 + 木盆 + 开口蚌）
      s += C.post(20, D - 10, 12, 2.4) + C.post(70, D - 10, 12, 2.4);
      s += C.block(14, D - 20, 62, 7, 3, P.wood, P.timber, 1.2);
      for (i = 0; i < 5; i++) s += oyster(ctx, 22 + i * 10, D - 29, 3.2, i % 2 === 0);
      s += K.barrel(88, D - 8, 8, P.wood, 10) + ell(88, D - 18, 6, 2, P.water, 0);
      // 小草棚（存贝）
      s += K.shed(ctx, 112, D - 10, 44, 20, 18, { open: true, roof: P.thatch, roof2: P.thatch2 });
      for (i = 0; i < 3; i++) s += C.heap(ctx, 122 + i * 12, D - 11, 6, 4, P.shell, P.pearl, P.shell, 4);
      // 贝壳废堆
      s += C.heap(ctx, W - 22, D - 8, 18, 10, '#d3c6a6', P.shell, P.pearl, 10);
      return s;
    }
  });
  C.def({
    idKind: 'prop-pearl-skiff', name: '采珠小艇', cat: 'prop', resource: 'pearls', w: 1, d: 1, up: 4, tags: ['boat', 'on_water'],
    note: '放在水面格上；无对应 FacilityKind',
    draw: function (ctx, W, D) { return skiff(ctx, 24, D - 14, 40, false); }
  });
  C.def({
    idKind: 'prop-pearl-shucktable', name: '开蚌台', cat: 'prop', resource: 'pearls', w: 1, d: 1, up: 12, tags: ['table', 'oyster'],
    draw: function (ctx, W, D) {
      var s = shade(K.q(8, D - 9, 44, D - 6));
      s += C.post(10, D - 6, 12, 2.4) + C.post(38, D - 6, 12, 2.4) + C.block(5, D - 16, 38, 6, 3, P.wood, P.timber, 1.2);
      for (var i = 0; i < 4; i++) s += oyster(ctx, 11 + i * 9, D - 25, 3.4, i % 2 === 0);
      return s;
    }
  });
  C.def({
    idKind: 'prop-pearl-shellheap', name: '蚌壳堆', cat: 'prop', resource: 'pearls', w: 1, d: 1, up: 10, tags: ['shell', 'heap'],
    draw: function (ctx, W, D) {
      var s = C.heap(ctx, 24, D - 8, 19, 13, '#d3c6a6', P.shell, P.pearl, 12);
      return s + oyster(ctx, 34, D - 6, 3, true);
    }
  });
  C.def({
    idKind: 'prop-pearl-net', name: '采珠网兜与篮', cat: 'prop', resource: 'pearls', w: 1, d: 1, up: 22, tags: ['net', 'basket'],
    draw: function (ctx, W, D) {
      var s = C.post(12, D - 6, 30, 2.6) + C.post(38, D - 6, 30, 2.6) + line(seg(10, D - 34, 40, D - 34), 1.4, 1, P.dark);
      var d = ''; for (var i = 0; i < 6; i++) d += seg(14 + i * 4.5, D - 34, 16 + i * 4, D - 18);
      s += line(d + 'M14 ' + (D - 26) + 'Q25 ' + (D - 22) + ' 37 ' + (D - 26), 0.7, 0.8);
      return s + C.basket(ctx, 16, D - 4, 18, 9, function (x, y) { var t = ''; for (var k = 0; k < 4; k++) t += oyster(ctx, x + 3 + k * 4, y, 2.4, false); return t; });
    }
  });
  /* 地面：湿沙滩（贝屑 + 水痕） */
  C.groundSet({
    idKind: 'ground-pearlsand', name: '采珠湿沙滩', resource: 'pearls', base: '#d8c8a0',
    scatter: function (ctx, v) { return C.scatter(ctx, 7, 's').concat(C.scatter(ctx, 3, 'w')); },
    item: function (sub, it, x, y) {
      if (it.t === 'w') return line(seg(x - 6, y, x + 6, y + 0.5), 0.8, 0.5, P.water2);
      return ell(x, y, sub.rnd(1, 1.8), sub.rnd(0.6, 1), it.k < 0.5 ? P.shell : P.pearl, 0.5);
    }
  });
})(typeof window !== 'undefined' ? window : this);
