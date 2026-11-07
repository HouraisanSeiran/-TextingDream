/*
 * 织梦 · 西式资源点第二批 —— 矿（续）：稀有金属平硐 rare_metals/adit、露天煤坑 coal/open_pit、烧炭窑场 coal/charcoal_kiln
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWS2_core;
  var P = C.P, K = C.K, f = C.f, path = C.path, line = C.line, ell = C.ell, poly = C.poly, seg = C.seg, shade = C.shade;

  /** 山腰：嶙峋岩坡（折线台阶轮廓，后高前低），返回 d */
  function hill(x0, x1, yb, top) {
    var w = x1 - x0, h = yb - top;
    var prof = [[0, 0], [0.04, 0.32], [0.1, 0.38], [0.16, 0.62], [0.24, 0.66], [0.3, 0.86], [0.38, 0.9], [0.44, 1], [0.52, 0.96],
      [0.58, 0.8], [0.66, 0.84], [0.72, 0.62], [0.8, 0.58], [0.86, 0.4], [0.93, 0.34], [1, 0]];
    return poly(prof.map(function (p) { return [x0 + w * p[0], yb - h * p[1]]; }));
  }
  C.hill = hill;
  function glint(ctx, x, y, col) { return ell(x, y, 1.2, 1, col, 0.5); }

  /* 稀有金属矿：山腰平硐口（木框支护）+ 出矿轨道 + 手选矿棚 + 小型洗矿槽 */
  C.def({
    idKind: 'site-raremetal-adit', name: '稀有金属矿', cat: 'site', resource: 'rare_metals', subtype: 'adit', facility: 'mine_head',
    w: 4, d: 3, up: 70, roof: 'monopitch', tags: ['adit', 'hand_sorting_shed', 'sluice', 'rails'],
    note: '山腰平硐 + 手选矿棚 + 洗矿槽；手选棚为单坡顶',
    draw: function (ctx, W, D) {
      var s = path(hill(-4, W + 4, D - 70, -66), P.stone2, 1.8);
      s += path(hill(10, W - 40, D - 78, -54), P.stone, 0);
      // 岩缝
      var d = '';
      for (var i = 0; i < 10; i++) { var x = ctx.rnd(16, W - 20), y = ctx.rnd(-50, D - 86); d += seg(x, y, x + ctx.rnd(4, 10), y + ctx.rnd(-2, 3)); }
      s += line(d, 0.8, 0.5);
      for (i = 0; i < 6; i++) s += glint(ctx, ctx.rnd(30, W - 40), ctx.rnd(-40, D - 90), i % 2 ? P.silver : P.copper);
      // 平硐口：木框支护
      var ax = 60, ay = D - 70;
      s += path('M' + f(ax - 16) + ' ' + f(ay) + 'L' + f(ax - 15) + ' ' + f(ay - 30) + 'Q' + f(ax) + ' ' + f(ay - 38) + ' ' + f(ax + 15) + ' ' + f(ay - 30) + 'L' + f(ax + 16) + ' ' + f(ay) + 'Z', '#2e241a', 1.6);
      s += C.post(ax - 15, ay, 30, 4) + C.post(ax + 15, ay, 30, 4);
      s += path(K.q(ax - 20, ay - 34, ax + 20, ay - 29), P.timber, 1.3);
      // 出矿轨道 + 矿车
      s += path(poly([[ax - 6, ay], [ax + 6, ay], [ax + 14, D - 6], [ax - 14, D - 6]]), P.yard2, 0, 0.9);
      s += line(seg(ax - 6, ay, ax - 13, D - 6) + seg(ax + 6, ay, ax + 13, D - 6), 1.4, 1, P.iron);
      d = ''; for (i = 1; i < 8; i++) { var t = i / 8, yy = ay + (D - 6 - ay) * t; d += seg(ax - 6 - 7 * t - 2, yy, ax + 6 + 7 * t + 2, yy); }
      s += line(d, 1.4, 1, P.dark);
      s += C.block(ax - 11, D - 34, 22, 6, 10, P.iron, '#6e6a62', 1.3) + C.heap(ctx, ax, D - 49, 10, 6, P.coal2, P.tin, P.silver, 5);
      // 手选矿棚（单坡顶敞棚，内有分拣台）
      var hx = 112, hy = D - 22;
      s += shade(poly([[hx + 64, hy], [hx + 72, hy - 4], [hx + 72, hy - 30], [hx + 64, hy - 30]]));
      s += path(K.q(hx, hy - 28, hx + 64, hy), '#2e241a', 1.2, 0.8);
      s += C.block(hx + 6, hy, 52, 5, 8, P.wood, P.timber, 1.2);
      for (i = 0; i < 7; i++) s += path(poly([[hx + 10 + i * 7, hy - 13], [hx + 13 + i * 7, hy - 16], [hx + 15 + i * 7, hy - 13]]), i % 3 ? P.tin : P.silver, 0.6);
      s += C.post(hx + 2, hy, 30, 3) + C.post(hx + 62, hy, 30, 3);
      s += path(poly([[hx - 4, hy - 26], [hx + 68, hy - 26], [hx + 66, hy - 46], [hx - 2, hy - 40]]), P.slate, 1.5);
      s += line(seg(hx, hy - 33, hx + 66, hy - 36), 0.8, 0.5);
      // 洗矿槽：斜木槽 + 水 + 下方小池
      s += line(seg(W - 20, D - 76, W - 20, D - 50), 2, 1, P.timber);
      s += path(poly([[W - 26, D - 78], [W - 14, D - 78], [W - 36, D - 46], [W - 46, D - 46]]), P.wood, 1.3);
      s += line(seg(W - 22, D - 76, W - 40, D - 48), 2.2, 1, P.water);
      s += K.basin(W - 56, D - 32, 30, 10, P.water);
      return s + C.tuft(ctx, 8, D - 4, 6, 4) + C.tuft(ctx, W - 8, D - 4, 5, 3);
    }
  });
  C.def({
    idKind: 'prop-raremetal-sluice', name: '洗矿木槽', cat: 'prop', resource: 'rare_metals', w: 1, d: 1, up: 16, tags: ['sluice', 'riffles'],
    draw: function (ctx, W, D) {
      var s = shade(poly([[8, D - 8], [44, D - 12], [44, D - 8], [10, D - 4]]));
      s += C.post(10, D - 6, 10, 2.4) + C.post(38, D - 10, 18, 2.4);
      s += path(poly([[4, D - 18], [42, D - 30], [44, D - 24], [6, D - 12]]), P.wood, 1.3);
      s += line(seg(8, D - 16, 41, D - 27), 2, 1, P.water);
      var d = ''; for (var i = 1; i < 6; i++) d += seg(6 + i * 6.5, D - 14 - i * 2.2, 7 + i * 6.5, D - 19 - i * 2.2);
      return s + line(d, 0.9, 0.8);
    }
  });
  C.def({
    idKind: 'prop-raremetal-panstack', name: '淘洗盘与矿样', cat: 'prop', resource: 'rare_metals', w: 1, d: 1, up: 8, tags: ['pan', 'ore_sample'],
    draw: function (ctx, W, D) {
      var s = C.shadowEll(26, D - 10, 16, 4);
      s += ell(18, D - 14, 11, 4.5, P.iron, 1.3) + ell(18, D - 15, 7, 2.6, P.water, 0.6) + ell(17, D - 15, 1.2, 0.8, P.silver, 0);
      s += C.heap(ctx, 34, D - 10, 9, 7, P.stone2, P.tin, P.silver, 6);
      return s;
    }
  });
  C.def({
    idKind: 'prop-raremetal-orebag', name: '矿样麻袋', cat: 'prop', resource: 'rare_metals', w: 1, d: 1, up: 14, tags: ['sack', 'ore'],
    draw: function (ctx, W, D) {
      var s = C.shadowEll(26, D - 8, 16, 4);
      [[16, 0], [31, 2]].forEach(function (p) {
        var x = p[0], y = D - 8 - p[1];
        s += path('M' + f(x - 8) + ' ' + f(y) + 'Q' + f(x - 10) + ' ' + f(y - 14) + ' ' + f(x - 3) + ' ' + f(y - 18) + 'L' + f(x + 3) + ' ' + f(y - 18) +
          'Q' + f(x + 10) + ' ' + f(y - 14) + ' ' + f(x + 8) + ' ' + f(y) + 'Z', P.wash, 1.2);
        s += line(seg(x - 3, y - 16, x + 3, y - 16), 1.2, 1, P.dark);
      });
      return s + ell(24, D - 6, 2, 1.4, P.silver, 0.6) + ell(28, D - 5, 1.6, 1.2, P.copper, 0.6);
    }
  });

  /* 露天煤坑：台阶坑，岩壁黑色煤层；坑边煤堆 + 运煤车 + 小绞车 */
  function coalVein(ctx) {
    return function (cx, yTop, rx, h) {
      return path('M' + f(cx - rx) + ' ' + f(yTop + h * 0.25) + 'L' + f(cx + rx) + ' ' + f(yTop + h * 0.25) + 'L' + f(cx + rx) + ' ' + f(yTop + h * 0.75) +
        'L' + f(cx - rx) + ' ' + f(yTop + h * 0.75) + 'Z', P.coal, 0) +
        line(seg(cx - rx, yTop + h * 0.5, cx + rx, yTop + h * 0.5 + ctx.rnd(-1, 1)), 0.6, 0.5, P.coal2);
    };
  }
  C.def({
    idKind: 'site-coal-openpit', name: '露天煤坑', cat: 'site', resource: 'coal', subtype: 'open_pit', facility: 'mine_head',
    w: 4, d: 3, up: 40, tags: ['open_pit', 'coal_seam', 'terraced', 'windlass'],
    note: '露天采煤坑，最近 FacilityKind 为 mine_head',
    draw: function (ctx, W, D) {
      var s = C.pit(ctx, W * 0.44, D - 72, 74, 48, 3, P.stone2, P.stone3, P.coal2, coalVein(ctx));
      for (var i = 0; i < 4; i++) s += C.heap(ctx, W * 0.44 + ctx.rnd(-18, 18), D - 54, 5, 3, P.coal2, P.coal, P.coal2, 3);
      // 坑沿斜坡道
      s += path(poly([[W * 0.44 + 40, D - 30], [W * 0.44 + 54, D - 32], [W * 0.44 + 34, D - 62], [W * 0.44 + 24, D - 60]]), P.yard2, 1.1);
      // 左后绞车
      var gx = 20, gy = D - 108;
      s += C.post(gx, gy, 22, 3) + C.post(gx + 26, gy, 22, 3) + path(K.q(gx - 2, gy - 24, gx + 28, gy - 20), P.timber, 1.2);
      s += ell(gx + 13, gy - 12, 5, 5, P.wood, 1.2) + line(seg(gx + 13, gy - 12, gx + 13, gy - 18) + seg(gx + 13, gy - 7, gx + 40, gy + 22), 0.9, 1);
      // 前右煤堆 + 运煤车
      s += C.heap(ctx, W - 36, D - 8, 28, 22, P.coal2, P.coal, '#2b2825', 14);
      s += C.block(W - 98, D - 10, 26, 7, 11, P.wood, P.timber, 1.3) + C.heap(ctx, W - 85, D - 27, 12, 6, P.coal2, P.coal, P.coal2, 5);
      s += C.wheel(W - 92, D - 7, 5) + C.wheel(W - 77, D - 7, 5);
      return s + C.tuft(ctx, 8, D - 4, 6, 4);
    }
  });
  C.def({
    idKind: 'prop-coal-heap', name: '露天煤堆', cat: 'prop', resource: 'coal', w: 1, d: 1, up: 14, tags: ['coal', 'heap'],
    draw: function (ctx, W, D) { return C.heap(ctx, 24, D - 8, 21, 20, P.coal2, P.coal, '#2b2825', 12); }
  });
  C.def({
    idKind: 'prop-coal-basket', name: '背煤筐', cat: 'prop', resource: 'coal', w: 1, d: 1, up: 18, tags: ['basket', 'coal'],
    draw: function (ctx, W, D) {
      var s = C.shadowEll(26, D - 8, 13, 3.5);
      s += path('M14 ' + (D - 28) + 'L34 ' + (D - 28) + 'L31 ' + (D - 8) + 'L17 ' + (D - 8) + 'Z', P.thatch2, 1.4);
      s += line(seg(15, D - 22, 33, D - 22) + seg(16, D - 15, 32, D - 15), 0.7, 0.6) + line('M16 ' + (D - 28) + 'Q24 ' + (D - 40) + ' 32 ' + (D - 28), 1.2, 1, P.dark);
      return s + C.heap(ctx, 24, D - 28, 9, 5, P.coal2, P.coal, P.coal2, 5);
    }
  });
  C.groundSet({
    idKind: 'ground-coalpitfloor', name: '煤坑煤屑地', resource: 'coal', base: '#9c8f78',
    scatter: function (ctx, v) { return C.scatter(ctx, 12, 'c'); },
    item: function (sub, it, x, y) {
      var r = sub.rnd(1, 2.6);
      return path(poly([[x - r, y], [x - r * 0.3, y - r * 0.8], [x + r, y - r * 0.2], [x + r * 0.4, y + r * 0.5]]), it.k < 0.6 ? P.coal : P.coal2, 0.5);
    }
  });

  /** 炭窑（土覆木垛 meiler）：圆丘 + 草皮块纹 + 顶部烟孔 + 烟 */
  function meiler(ctx, cx, yb, r, smoke) {
    var s = C.shadowEll(cx + r * 0.4, yb, r * 1.15, r * 0.32);
    var d = 'M' + f(cx - r) + ' ' + f(yb) + 'Q' + f(cx - r) + ' ' + f(yb - r * 1.2) + ' ' + f(cx) + ' ' + f(yb - r * 1.25) +
      'Q' + f(cx + r) + ' ' + f(yb - r * 1.2) + ' ' + f(cx + r) + ' ' + f(yb) + 'Z';
    s += path(d, P.soil, 1.6);
    s += path('M' + f(cx + r * 0.2) + ' ' + f(yb - r * 1.2) + 'Q' + f(cx + r) + ' ' + f(yb - r * 1.05) + ' ' + f(cx + r) + ' ' + f(yb) + 'L' + f(cx + r * 0.5) + ' ' + f(yb) + 'Z', P.soil2, 0, 0.8);
    var t = '';
    for (var i = 0; i < 9; i++) { var u = ctx.rnd(-0.75, 0.75), v = ctx.rnd(0.2, 1); t += seg(cx + u * r, yb - v * r, cx + u * r + 4, yb - v * r); }
    s += line(t, 0.8, 0.55);
    s += ell(cx - r * 0.5, yb - r * 0.25, 1.6, 1.2, P.ember, 0) + ell(cx + r * 0.35, yb - r * 0.5, 1.4, 1.1, P.ember, 0);
    s += ell(cx, yb - r * 1.22, 3, 1.3, '#2e241a', 0.8);
    if (smoke) {
      var sy = yb - r * 1.3;
      s += line('M' + f(cx) + ' ' + f(sy) + 'q-5 -8 1 -14 q6 -6 0 -14', 1.2, 0.6, P.stone3);
      s += path(C.blob(ctx, cx - 2, sy - 12, 5, 4, 5, 0.15), P.plaster, 0.9, 0.85) +
        path(C.blob(ctx, cx + 3, sy - 24, 7, 5, 6, 0.15), P.plaster, 0.9, 0.75) +
        path(C.blob(ctx, cx - 1, sy - 37, 9, 6, 6, 0.15), P.plaster, 0.9, 0.6);
    }
    return s;
  }
  C.meiler = meiler;
  /** 劈柴垛（端面朝观者的一堆小原木） */
  function woodpile(ctx, x, yb, cols, rows) {
    var s = shade(poly([[x, yb], [x + cols * 7 + 6, yb], [x + cols * 7 + 6, yb - 3], [x, yb - 3]]));
    for (var j = 0; j < rows; j++) for (var i = 0; i < cols - (j % 2); i++) s += C.logEnd(x + 4 + i * 7 + (j % 2) * 3.5, yb - 4 - j * 6.2, 3.4, P.wash);
    return s;
  }
  C.woodpile = woodpile;
  /* 烧炭窑场：两座土覆炭窑（一座冒烟）+ 劈柴垛 + 烧炭人草棚 */
  C.def({
    idKind: 'site-charcoal-kiln', name: '烧炭窑场', cat: 'site', resource: 'coal', subtype: 'charcoal_kiln', facility: 'kiln',
    w: 4, d: 3, up: 56, roof: 'gable_thatch', tags: ['charcoal', 'meiler', 'woodpile', 'collier_hut'],
    note: '林中土覆木垛烧炭，属 kiln；产物按 coal 记',
    draw: function (ctx, W, D) {
      var s = path(C.blob(ctx, W * 0.5, D - 70, W * 0.46, 56, 9, 0.06), '#b9a37c', 0, 0.85);
      // 后排：烧炭人锥形草棚 + 劈柴垛
      var hx = 30, hy = D - 100;
      s += shade(poly([[hx + 20, hy], [hx + 30, hy - 4], [hx, hy - 44]]));
      s += path(poly([[hx - 22, hy], [hx, hy - 46], [hx + 22, hy]]), P.thatch, 1.6);
      s += path(poly([[hx, hy - 46], [hx + 22, hy], [hx + 10, hy]]), P.thatch2, 0, 0.9);
      s += line(seg(hx - 11, hy - 23, hx + 11, hy - 23) + seg(hx - 16, hy - 12, hx + 16, hy - 12), 0.8, 0.5);
      s += path(poly([[hx - 5, hy], [hx, hy - 16], [hx + 5, hy]]), '#2e241a', 1);
      s += woodpile(ctx, 78, D - 102, 9, 4);
      // 中前：两座炭窑
      s += meiler(ctx, 70, D - 22, 34, false) + meiler(ctx, 140, D - 46, 30, true);
      // 冷却中的炭堆 + 耙子
      s += C.heap(ctx, W - 22, D - 10, 18, 12, P.charcoal, P.coal, P.coal2, 8);
      s += line(seg(W - 50, D - 6, W - 30, D - 34) + seg(W - 34, D - 36, W - 26, D - 32), 1.4, 1, P.dark);
      return s + C.tuft(ctx, 10, D - 4, 6, 4) + C.tuft(ctx, W - 8, D - 60, 5, 3);
    }
  });
  C.def({
    idKind: 'prop-charcoal-sacks', name: '木炭袋', cat: 'prop', resource: 'coal', w: 1, d: 1, up: 14, tags: ['charcoal', 'sack'],
    draw: function (ctx, W, D) {
      var s = C.shadowEll(26, D - 8, 16, 4);
      [[16, 0], [32, 2]].forEach(function (p) {
        var x = p[0], y = D - 8 - p[1];
        s += path('M' + f(x - 8) + ' ' + f(y) + 'Q' + f(x - 10) + ' ' + f(y - 14) + ' ' + f(x - 4) + ' ' + f(y - 17) + 'L' + f(x + 4) + ' ' + f(y - 17) +
          'Q' + f(x + 10) + ' ' + f(y - 14) + ' ' + f(x + 8) + ' ' + f(y) + 'Z', P.wood, 1.2);
        s += C.heap(ctx, x, y - 16, 4, 2.5, P.charcoal, P.coal, P.coal2, 3);
      });
      return s;
    }
  });
  C.def({
    idKind: 'prop-charcoal-woodpile', name: '烧炭劈柴垛', cat: 'prop', resource: 'coal', w: 1, d: 1, up: 20, tags: ['firewood'],
    draw: function (ctx, W, D) { return woodpile(ctx, 6, D - 6, 5, 5); }
  });
  C.def({
    idKind: 'prop-charcoal-meiler', name: '小炭窑', cat: 'prop', resource: 'coal', w: 1, d: 1, up: 44, tags: ['meiler', 'smoke'],
    draw: function (ctx, W, D) { return meiler(ctx, 24, D - 8, 17, true); }
  });
})(typeof window !== 'undefined' ? window : this);
