/*
 * 织梦 · 西式资源点第二批 —— 矿：青金石露天坑 lapis、露天煤坑 coal/open_pit、烧炭窑 coal/charcoal_kiln、稀有金属平硐 rare_metals
 * draw(ctx, W, D) 在“地面坐标”里画：占地 x∈[0,W]、y∈[0,D]，y=D 是前沿；高度画成负 y。
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWS2_core;
  var P = C.P, f = C.f, path = C.path, line = C.line, ell = C.ell, poly = C.poly, seg = C.seg, shade = C.shade;

  function ellD(cx, cy, rx, ry) {
    return 'M' + f(cx - rx) + ' ' + f(cy) + 'A' + f(rx) + ' ' + f(ry) + ' 0 1 0 ' + f(cx + rx) + ' ' + f(cy) +
      'A' + f(rx) + ' ' + f(ry) + ' 0 1 0 ' + f(cx - rx) + ' ' + f(cy) + 'Z';
  }
  C.ellD = ellD;
  /** 露天采坑：每级 = 台面椭圆 + 下一级上移 h 的“岩壁椭圆”（只露出后壁月牙）+ 下一级台面；
   *  vein(cx, yTop, rx, h) 回调在岩壁上画矿脉（已裁切到岩壁） */
  function pit(ctx, cx, cy, rx, ry, steps, rim, wall, floor, vein, h) {
    h = h || 13;
    var s = C.shadowEll(cx + 4, cy + 3, rx * 1.03, ry * 1.03);
    s += path(ellD(cx, cy, rx, ry), rim, 1.8);
    for (var i = 1; i <= steps; i++) {
      var k = 1 - i * 0.2, cyi = cy + i * ry * 0.12, rxi = rx * k, ryi = ry * k;
      var wd = ellD(cx, cyi - h, rxi, ryi);
      var inner = path(wd, wall, 0);
      // 岩层竖向短排线
      var d = '';
      for (var j = 0; j < 9; j++) {
        var x = cx - rxi * 0.85 + j * rxi * 0.21;
        d += seg(x, cyi - h - ryi * 0.95 + ctx.rnd(0, 3), x + ctx.rnd(-1, 1), cyi - h - ryi * 0.95 + h * ctx.rnd(0.5, 0.9));
      }
      inner += line(d, 0.7, 0.45);
      if (vein) inner += vein(cx, cyi - h - ryi, rxi, h);
      s += C.clip(ctx, wd, inner) + path(wd, 'none', 1.2);
      s += path(ellD(cx, cyi, rxi, ryi), i === steps ? floor : rim, 1.3);
    }
    return s;
  }
  C.pit = pit;
  /** 一块蓝色青金石（带金点） */
  function lapisChunk(ctx, x, y, r) {
    var s = path(poly([[x - r, y], [x - r * 0.6, y - r], [x + r * 0.5, y - r * 1.05], [x + r, y - r * 0.2], [x + r * 0.4, y + r * 0.3]]), P.lapis, 0.9);
    s += path(poly([[x - r * 0.6, y - r], [x + r * 0.5, y - r * 1.05], [x + r * 0.2, y - r * 0.4]]), P.lapis2, 0);
    s += ell(x + ctx.rnd(-r * 0.4, r * 0.4), y - r * ctx.rnd(0.2, 0.7), 0.7, 0.6, P.pyrite, 0);
    return s;
  }
  C.lapisChunk = lapisChunk;
  /** 后壁岩面上的深蓝矿脉 + 黄铁矿金点 */
  function lapisVein(ctx) {
    return function (cx, yTop, rx, h) {
      var s = '', n = 3;
      for (var i = 0; i < n; i++) {
        var x = cx - rx * 0.62 + i * rx * 0.42 + ctx.rnd(-4, 4), y = yTop + h * ctx.rnd(0.35, 0.7), L = ctx.rnd(14, 24);
        s += line('M' + f(x) + ' ' + f(y) + 'q' + f(L * 0.4) + ' ' + f(ctx.rnd(-4, 4)) + ' ' + f(L) + ' ' + f(ctx.rnd(-3, 3)), 3.2, 1, P.lapis);
        s += line('M' + f(x + 2) + ' ' + f(y - 0.6) + 'q' + f(L * 0.3) + ' -1 ' + f(L * 0.6) + ' 0', 1, 1, P.lapis2);
        s += ell(x + L * 0.3, y + 0.4, 1, 0.8, P.pyrite, 0) + ell(x + L * 0.75, y - 0.3, 0.9, 0.7, P.pyrite, 0) +
          ell(x + L * 0.5, y + h * 0.25, 0.7, 0.6, P.pyrite, 0);
      }
      return s;
    };
  }
  /** 选矿台：木板台面 + 腿 + 台上一堆矿块 */
  function sortTable(ctx, x, yb, w, chunk) {
    var s = shade(poly([[x + 4, yb], [x + w + 6, yb], [x + w + 6, yb - 3], [x + 4, yb - 3]]));
    s += C.post(x + 3, yb, 12, 2.4) + C.post(x + w - 3, yb, 12, 2.4);
    s += C.block(x - 2, yb - 10, w + 4, 8, 3, P.wood, P.timber, 1.2);
    for (var i = 0; i < 6; i++) s += chunk(ctx, x + 4 + i * (w - 8) / 5 + ctx.rnd(-1, 1), yb - 15 - ctx.rnd(0, 2), ctx.rnd(2, 3.2));
    return s;
  }
  C.sortTable = sortTable;

  /* 青金石露天采坑：三级台阶坑，后壁岩面带深蓝矿脉和金色黄铁矿点；前右侧选矿台堆蓝矿块；左后吊杆 */
  C.def({
    idKind: 'site-lapispit', name: '青金石露天矿', cat: 'site', resource: 'lapis', subtype: 'open_pit', facility: 'mine_head',
    w: 4, d: 3, up: 46, tags: ['open_pit', 'terraced', 'sorting_table', 'derrick'],
    note: '露天采坑，最近 FacilityKind 为 mine_head',
    draw: function (ctx, W, D) {
      var s = C.pit(ctx, W * 0.46, D - 74, 76, 50, 3, P.stone, P.stone3, P.stone2, lapisVein(ctx));
      // 坑底几块散落矿石
      for (var i = 0; i < 5; i++) s += lapisChunk(ctx, W * 0.46 + ctx.rnd(-22, 22), D - 54 - ctx.rnd(0, 6), ctx.rnd(2, 3));
      // 坑沿到底的木梯
      s += line(seg(W * 0.46 + 30, D - 30, W * 0.46 + 18, D - 60) + seg(W * 0.46 + 36, D - 30, W * 0.46 + 24, D - 60), 1.4, 1, P.dark);
      for (i = 1; i < 6; i++) s += line(seg(W * 0.46 + 30 - i * 2, D - 30 - i * 5, W * 0.46 + 36 - i * 2, D - 30 - i * 5), 1, 1, P.dark);
      // 左后吊杆（三脚木架 + 吊篮）
      var gx = 26, gy = D - 112;
      s += line(seg(gx - 12, gy, gx, gy - 40) + seg(gx + 12, gy, gx, gy - 40) + seg(gx, gy - 40, gx + 34, gy - 26), 2, 1, P.timber);
      s += line(seg(gx + 34, gy - 26, gx + 34, gy - 4), 0.9, 1);
      s += path(poly([[gx + 30, gy - 4], [gx + 38, gy - 4], [gx + 37, gy + 3], [gx + 31, gy + 3]]), P.wood, 1);
      // 前右选矿台
      s += sortTable(ctx, W - 64, D - 6, 52, lapisChunk);
      s += C.tuft(ctx, 10, D - 6, 6, 4) + C.tuft(ctx, W - 10, D - 60, 5, 3);
      return s;
    }
  });
  /* 摆件：蓝矿块筐、碎岩废料堆、矿石背篓 */
  C.def({
    idKind: 'prop-lapis-basket', name: '青金石矿筐', cat: 'prop', resource: 'lapis', w: 1, d: 1, up: 12, tags: ['ore', 'basket'],
    draw: function (ctx, W, D) {
      var s = C.shadowEll(27, D - 8, 15, 4);
      s += path('M10 ' + (D - 22) + 'L38 ' + (D - 22) + 'L35 ' + (D - 8) + 'L13 ' + (D - 8) + 'Z', P.thatch2, 1.4);
      s += line(seg(12, D - 17, 36, D - 17) + seg(13, D - 12, 35, D - 12), 0.7, 0.6);
      for (var i = 0; i < 6; i++) s += lapisChunk(ctx, 14 + i * 4 + ctx.rnd(-1, 1), D - 22 - ctx.rnd(0, 3), ctx.rnd(2.4, 3.4));
      return s;
    }
  });
  C.def({
    idKind: 'prop-lapis-spoil', name: '废石堆', cat: 'prop', resource: 'lapis', w: 1, d: 1, up: 10, tags: ['spoil'],
    draw: function (ctx, W, D) { return C.heap(ctx, 24, D - 10, 20, 16, P.stone2, P.stone, P.stone3, 10) + lapisChunk(ctx, 30, D - 16, 2); }
  });
  C.def({
    idKind: 'prop-lapis-cart', name: '青金石手推车', cat: 'prop', resource: 'lapis', w: 1, d: 1, up: 14, tags: ['wheelbarrow'],
    draw: function (ctx, W, D) {
      var s = C.shadowEll(26, D - 8, 17, 4);
      s += line(seg(30, D - 20, 44, D - 14), 1.8, 1, P.dark);
      s += path(poly([[6, D - 26], [32, D - 26], [28, D - 14], [10, D - 14]]), P.wood, 1.4);
      for (var i = 0; i < 4; i++) s += lapisChunk(ctx, 11 + i * 5.5, D - 26, ctx.rnd(2.4, 3.2));
      return s + C.wheel(12, D - 11, 5);
    }
  });
  /* 地面：灰白碎岩地，偶见蓝屑 */
  C.groundSet({
    idKind: 'ground-lapisrubble', name: '青金石碎岩地', resource: 'lapis', base: '#cbbd9f',
    scatter: function (ctx, v) { return C.scatter(ctx, 9, 'r').concat(C.scatter(ctx, 2, 'b')); },
    item: function (sub, it, x, y) {
      if (it.t === 'b') return ell(x, y, 1.6, 1.1, P.lapis, 0.5);
      var r = sub.rnd(1.4, 3);
      return path(poly([[x - r, y], [x - r * 0.4, y - r * 0.8], [x + r, y - r * 0.3], [x + r * 0.5, y + r * 0.4]]), it.k < 0.5 ? P.stone2 : P.stone3, 0.7);
    }
  });
})(typeof window !== 'undefined' ? window : this);
