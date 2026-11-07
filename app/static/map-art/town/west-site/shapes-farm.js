/*
 * 织梦 · 西式资源点 —— 牧场 livestock / wool、马场 horses、农庄 grain、药圃 herb、葡萄园 wine
 * draw(ctx, W, D) 在“地面坐标”里画：占地 x∈[0,W]、y∈[0,D]，y=D 是前沿；高度画成负 y。
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWS_core;
  var P = C.P, f = C.f, path = C.path, line = C.line, ell = C.ell, poly = C.poly, seg = C.seg, shade = C.shade;

  /** 一只羊（侧身，羊毛团 + 黑脸黑腿） */
  function sheep(ctx, x, yb, flip) {
    var k = flip ? -1 : 1;
    var s = C.shadowEll(x + 2, yb, 9, 2.4);
    s += line(seg(x - 5, yb - 6, x - 5, yb) + seg(x - 1, yb - 6, x - 1, yb) + seg(x + 3, yb - 6, x + 3, yb) + seg(x + 6, yb - 6, x + 6, yb), 1.4, 1, P.coal);
    s += path(C.blob(ctx, x, yb - 9, 9, 5.5, 7, 0.12), P.wool, 1.1);
    s += ell(x + k * 10, yb - 11, 3.2, 2.6, P.coal, 0.8);
    return s;
  }
  /** 一匹马（侧身简化轮廓） */
  function horse(ctx, x, yb, fill, flip) {
    var k = flip ? -1 : 1, X = function (dx) { return f(x + k * dx); };
    var s = C.shadowEll(x + 2, yb, 14, 3);
    s += line('M' + X(-9) + ' ' + f(yb - 12) + 'L' + X(-10) + ' ' + f(yb) + 'M' + X(-5) + ' ' + f(yb - 12) + 'L' + X(-4) + ' ' + f(yb) +
      'M' + X(6) + ' ' + f(yb - 12) + 'L' + X(7) + ' ' + f(yb) + 'M' + X(10) + ' ' + f(yb - 12) + 'L' + X(11) + ' ' + f(yb), 2, 1, P.dark);
    s += path('M' + X(-12) + ' ' + f(yb - 20) + 'Q' + X(0) + ' ' + f(yb - 24) + ' ' + X(10) + ' ' + f(yb - 20) + 'L' + X(15) + ' ' + f(yb - 30) +
      'L' + X(20) + ' ' + f(yb - 27) + 'L' + X(14) + ' ' + f(yb - 14) + 'Q' + X(0) + ' ' + f(yb - 10) + ' ' + X(-12) + ' ' + f(yb - 13) + 'Z', fill, 1.2);
    s += line('M' + X(-12) + ' ' + f(yb - 19) + 'q' + f(-k * 5) + ' 3 ' + f(-k * 4) + ' 10', 1.6, 1, P.dark);   // 尾
    s += line('M' + X(11) + ' ' + f(yb - 22) + 'L' + X(15) + ' ' + f(yb - 30), 1.6, 1, P.dark);                 // 鬃
    return s;
  }
  C.sheep = sheep; C.horse = horse;

  /* 羊圈：枝条编栏围成的圈 + 草顶羊棚 + 几只羊 */
  C.def({
    idKind: 'site-sheepfold', name: '羊圈', cat: 'site', resource: 'livestock', facility: 'stable',
    w: 4, d: 3, up: 40, roof: 'gable_thatch', tags: ['pen', 'wattle_fence', 'sheep'],
    note: '牲畜棚圈，最近 FacilityKind 为 stable',
    draw: function (ctx, W, D) {
      var s = path(poly([[8, D - 4], [W - 8, D - 4], [W - 14, D - 104], [14, D - 104]]), P.yard, 1, 0.8);
      // 后栏
      s += C.fence(14, D - 104, W - 14, D - 104, 8, 16);
      // 后方羊棚
      var hx = 24, hy = D - 100;
      s += shade(poly([[hx + 70, hy], [hx + 78, hy - 4], [hx + 78, hy - 22], [hx + 70, hy - 26]]));
      s += path(poly([[hx, hy - 26], [hx + 70, hy - 26], [hx + 70, hy], [hx, hy]]), P.wood, 1.4);
      s += path(poly([[hx + 8, hy - 18], [hx + 62, hy - 18], [hx + 62, hy], [hx + 8, hy]]), '#2e241a', 1);
      s += C.roofGable(hx - 6, hx + 76, hy - 24, hy - 50, 10, P.thatch, P.thatch2, 4);
      // 羊
      var pos = [[110, D - 70], [140, D - 60], [60, D - 50], [96, D - 36], [150, D - 28], [40, D - 24]];
      pos.forEach(function (p, i) { s += sheep(ctx, p[0], p[1], i % 2); });
      // 水槽
      s += C.block(120, D - 82, 30, 6, 6, P.water, P.timber, 1.1);
      // 侧栏与前栏（带一扇栅门）
      s += C.fence(14, D - 104, 8, D - 4, 5, 16) + C.fence(W - 14, D - 104, W - 8, D - 4, 5, 16);
      s += C.fence(8, D - 4, W / 2 - 18, D - 4, 4, 16) + C.fence(W / 2 + 18, D - 4, W - 8, D - 4, 4, 16);
      s += line(seg(W / 2 - 18, D - 16, W / 2 + 2, D - 30) + seg(W / 2 - 18, D - 8, W / 2 + 2, D - 22), 1.6, 1, P.timber);
      return s;
    }
  });
  /* 剪毛棚：开敞草顶棚 + 剪毛凳 + 羊毛捆 */
  C.def({
    idKind: 'site-shearshed', name: '剪毛棚', cat: 'site', resource: 'wool', facility: null,
    w: 3, d: 2, up: 46, roof: 'gable_thatch', tags: ['open_shed', 'shearing', 'fleece'],
    note: '剪羊毛的开敞棚；对不上 FacilityKind，facility 为 null',
    draw: function (ctx, W, D) {
      var s = '', x0 = 12, x1 = W - 14, yb = D - 8, ye = yb - 40, yr = ye - 32, i;
      s += shade(poly([[x1, yb], [x1 + 12, yb - 4], [x1 + 12, ye + 4], [x1, ye]]));
      s += path(poly([[x0 - 2, yb + 2], [x1 + 2, yb + 2], [x1 - 4, yb - 30], [x0 + 4, yb - 30]]), P.yard, 1);
      for (i = 0; i < 4; i++) s += C.post(x0 + 6 + i * (x1 - x0 - 12) / 3, yb - 28, 34, 3);
      // 剪毛凳 + 正在剪的羊 + 剪刀
      s += C.block(x0 + 20, yb - 8, 36, 6, 8, P.wood, P.timber, 1.2);
      s += sheep(ctx, x0 + 38, yb - 16, false);
      s += line('M' + f(x0 + 56) + ' ' + f(yb - 30) + 'l6 6m-6 0l6 -6', 1.2, 1, P.iron);
      // 羊毛捆（卷起的白毛团）
      for (i = 0; i < 4; i++) s += path(C.blob(ctx, x1 - 40 + (i % 2) * 14, yb - 6 - Math.floor(i / 2) * 10, 7, 5, 6, 0.1), P.wool, 1);
      for (i = 0; i < 4; i++) s += C.post(x0 + 2 + i * (x1 - x0 - 4) / 3, yb, 40, 4);
      s += C.roofGable(x0 - 10, x1 + 10, ye + 4, yr, 14, P.thatch, P.thatch2, 5);
      return s;
    }
  });
  /* 干草架：三角木架上搭晒的干草 */
  C.def({
    idKind: 'prop-hayrack', name: '干草架', cat: 'prop', resource: 'livestock', w: 1, d: 1, up: 16, tags: ['hay', 'fodder'],
    draw: function (ctx, W, D) {
      var s = C.shadowEll(27, D - 4, 20, 4);
      s += line(seg(6, D - 4, 14, D - 56) + seg(42, D - 4, 34, D - 56) + seg(14, D - 56, 34, D - 56), 2, 1, P.dark);
      s += path('M8 ' + f(D - 20) + 'Q10 ' + f(D - 50) + ' 24 ' + f(D - 58) + 'Q38 ' + f(D - 50) + ' 40 ' + f(D - 20) + 'Q24 ' + f(D - 14) + ' 8 ' + f(D - 20) + 'Z', P.thatch, 1.3);
      var h = '';
      for (var i = 0; i < 7; i++) h += seg(12 + i * 4.5, D - 22, 14 + i * 3.5, D - 48);
      return s + line(h, 0.7, 0.6, P.thatch2);
    }
  });
  /* 马场：圆形驯马圈（围栏）+ 中间系缰的柱 + 马 + 一侧马棚 */
  C.def({
    idKind: 'site-horsecorral', name: '驯马场', cat: 'site', resource: 'horses', facility: 'stable',
    w: 4, d: 3, up: 44, roof: 'gable_tile', tags: ['round_pen', 'paddock', 'horses'],
    note: '圆形驯马圈 + 小马棚；facility 为 stable',
    draw: function (ctx, W, D) {
      var cx = 76, cy = D - 52, rx = 64, ry = 40, s = '', i;
      s += ell(cx, cy, rx, ry, P.yard2, 1, 0.9);
      // 马棚（右后）
      var hx = 132, hy = D - 70;
      s += shade(poly([[hx + 54, hy], [hx + 60, hy - 4], [hx + 60, hy - 28], [hx + 54, hy - 32]]));
      s += path(poly([[hx, hy - 32], [hx + 54, hy - 32], [hx + 54, hy], [hx, hy]]), P.wood, 1.4);
      for (i = 0; i < 3; i++) s += path(poly([[hx + 4 + i * 17, hy - 22], [hx + 16 + i * 17, hy - 22], [hx + 16 + i * 17, hy], [hx + 4 + i * 17, hy]]), i === 1 ? '#2e241a' : P.timber, 1);
      s += C.roofGable(hx - 6, hx + 60, hy - 30, hy - 56, 10, P.tile, P.red, 4);
      // 后半圈围栏
      var fence = function (a0, a1) {
        var o = '', n = 8;
        for (var k = 0; k < n; k++) {
          var a = a0 + (a1 - a0) * k / n, b = a0 + (a1 - a0) * (k + 1) / n;
          o += C.fence(cx + Math.cos(a) * rx, cy + Math.sin(a) * ry, cx + Math.cos(b) * rx, cy + Math.sin(b) * ry, 1, 14);
        }
        return o;
      };
      s += fence(Math.PI, Math.PI * 2);
      s += C.post(cx, cy + 4, 24, 4) + line(seg(cx, cy - 16, cx + 24, cy - 6), 0.8, 0.9);
      s += horse(ctx, cx + 30, cy + 8, P.timber, false) + horse(ctx, cx - 30, cy - 6, P.wash, true);
      s += fence(0, Math.PI);
      s += horse(ctx, W - 30, D - 6, P.dark, true);
      return s;
    }
  });

  /* ---------- 农庄 grain ---------- */
  /* 谷仓：高大的木构草顶谷仓 + 双开大门 + 门前堆的麦捆 */
  C.def({
    idKind: 'site-barn', name: '谷仓', cat: 'site', resource: 'grain', facility: 'granary',
    w: 3, d: 2, up: 80, roof: 'gable_thatch', tags: ['barn', 'threshing_door'],
    note: '中世纪什一税谷仓式；facility 为 granary',
    draw: function (ctx, W, D) {
      var x0 = 14, x1 = W - 14, yb = D - 6, ye = yb - 56, yr = ye - 54, s = '', i;
      s += shade(poly([[x1, yb], [x1 + 12, yb - 4], [x1 + 12, ye + 6], [x1, ye]]));
      s += path(poly([[x0, ye], [x1, ye], [x1, yb], [x0, yb]]), P.plaster, 1.6);
      var tb = seg(x0, ye + 20, x1, ye + 20);
      for (i = 1; i < 6; i++) tb += seg(x0 + i * (x1 - x0) / 6, ye, x0 + i * (x1 - x0) / 6, yb);
      tb += seg(x0, ye + 20, x0 + (x1 - x0) / 6, ye) + seg(x1, ye + 20, x1 - (x1 - x0) / 6, ye);
      s += line(tb, 2, 1, P.timber);
      var dx = W / 2;
      s += path(poly([[dx - 20, yb - 40], [dx + 20, yb - 40], [dx + 20, yb], [dx - 20, yb]]), P.wood, 1.4);
      s += path(poly([[dx - 16, yb - 36], [dx + 6, yb - 36], [dx + 6, yb], [dx - 16, yb]]), '#2e241a', 1);
      s += line(seg(dx + 8, yb - 38, dx + 8, yb) + seg(dx + 10, yb - 20, dx + 18, yb - 30), 1, 0.8);
      s += C.roofGable(x0 - 10, x1 + 10, ye + 4, yr, 22, P.thatch, P.thatch2, 6);
      s += line(seg(x0 + 14, yr, x1 - 14, yr), 3, 1, P.thatch2);
      // 门前麦捆
      for (i = 0; i < 3; i++) s += sheaf(x0 + 6 + i * 9, yb + 2, 12);
      return s;
    }
  });
  /** 一个麦捆（立着，中间扎腰） */
  function sheaf(x, yb, h) {
    var s = path(poly([[x - 4, yb], [x + 4, yb], [x + 2, yb - h * 0.5], [x + 4, yb - h], [x - 4, yb - h], [x - 2, yb - h * 0.5]]), P.wheat, 1);
    return s + line(seg(x - 2.5, yb - h * 0.5, x + 2.5, yb - h * 0.5), 1.2, 1, P.wheat2);
  }
  C.sheaf = sheaf;
  /* 打谷场：踩实的圆场 + 连枷 + 摊开的麦秸 + 麦捆垛 */
  C.def({
    idKind: 'prop-threshfloor', name: '打谷场', cat: 'prop', resource: 'grain', w: 1, d: 1, up: 4, tags: ['threshing', 'flail'],
    draw: function (ctx, W, D) {
      var s = ell(24, D - 18, 23, 14, P.yard2, 1.2);
      var st = '';
      for (var i = 0; i < 14; i++) { var x = ctx.rnd(8, 40), y = ctx.rnd(D - 28, D - 10); st += seg(x, y, x + ctx.rnd(-4, 4), y + ctx.rnd(-1.5, 1.5)); }
      s += line(st, 1, 0.9, P.wheat);
      s += line(seg(8, D - 8, 30, D - 36), 1.6, 1, P.timber) + line(seg(30, D - 36, 40, D - 26), 2.4, 1, P.wood);
      s += sheaf(38, D - 4, 14) + sheaf(44, D - 6, 12);
      return s;
    }
  });
  /* 麦田格：成熟麦垄，平铺 4 变体（垄线横贯瓦片，两端对齐） */
  C.groundSet({
    idKind: 'ground-wheatfield', name: '麦田格', resource: 'grain', base: P.wheat, tags: ['crop_rows', 'field'],
    note: '平铺底纹：每 8 px 一道横垄，左右边对齐；变体 4 为收割后的麦茬',
    under: function (ctx, v) {
      var d = '', k = '';
      for (var y = 4; y < 48; y += 8) { d += seg(0, y, 48, y); k += seg(0, y + 3, 48, y + 3); }
      return line(d, 1, 0.55, P.wheat2) + line(k, 0.6, 0.35, P.soil);
    },
    scatter: function (ctx, v) { return C.scatter(ctx, v === 4 ? 14 : 22, v === 4 ? 'stub' : 'ear'); },
    item: function (sub, it, x, y) {
      var yy = Math.round((y - 4) / 8) * 8 + 4;
      if (it.t === 'stub') return line(seg(x, yy, x + 0.4, yy - 2.4), 0.9, 0.8, P.soil2);
      return line(seg(x, yy, x + 0.8, yy - 5) + seg(x + 0.8, yy - 5, x + 1.4, yy - 7.5), 0.8, 0.8, P.wheat2) + C.ell(x + 1.1, yy - 6.4, 0.8, 1.6, P.wheat2, 0);
    }
  });

  /* ---------- 药圃 herb ---------- */
  /** 一垄药草（小灌丛排成一行） */
  function herbRow(ctx, x0, x1, y, fill) {
    var s = path(poly([[x0, y + 2], [x1, y + 2], [x1 - 2, y - 3], [x0 + 2, y - 3]]), P.soil2, 0.9), n = Math.floor((x1 - x0) / 9);
    for (var i = 0; i < n; i++) s += path(C.blob(ctx, x0 + 5 + i * 9, y - 4, 4.2, 3.2, 6, 0.2), i % 3 === 1 ? P.leaf : fill, 0.9);
    return s;
  }
  C.def({
    idKind: 'site-herbgarden', name: '药草田', cat: 'site', resource: 'herb', facility: null,
    w: 3, d: 2, up: 30, tags: ['raised_beds', 'wattle_fence', 'well'],
    note: '修道院式药圃：编篱围着的几畦药草 + 小井；对不上 FacilityKind（infirmary 是城镇医馆），facility 为 null',
    draw: function (ctx, W, D) {
      var s = path(poly([[6, D - 4], [W - 6, D - 4], [W - 10, D - 84], [10, D - 84]]), P.yard, 1, 0.8);
      s += C.fence(10, D - 84, W - 10, D - 84, 7, 14);
      var fills = [P.herb, P.leaf2, '#a58fa8', P.herb, P.leaf2];
      for (var r = 0; r < 5; r++) s += herbRow(ctx, 16 + r * 1.2, 100 - r * 1.2, D - 72 + r * 14, fills[r]);
      // 右侧小井
      var wx = 120, wy = D - 34;
      s += C.block(wx - 12, wy, 24, 6, 10, P.stone, P.stone2, 1.3) + ell(wx, wy - 13, 8, 2.4, P.water, 0.8);
      s += C.post(wx - 12, wy - 6, 26, 2.6) + C.post(wx + 12, wy - 6, 26, 2.6) + line(seg(wx - 14, wy - 32, wx + 14, wy - 32), 2, 1, P.dark);
      s += C.fence(6, D - 4, W / 2 - 12, D - 4, 4, 14) + C.fence(W / 2 + 12, D - 4, W - 6, D - 4, 4, 14);
      return s;
    }
  });
  /* 晒药架：三层竹木架上摊的药草束 */
  C.def({
    idKind: 'prop-herbrack', name: '晒药架', cat: 'prop', resource: 'herb', w: 1, d: 1, up: 14, tags: ['drying'],
    draw: function (ctx, W, D) {
      var s = shade(poly([[6, D - 4], [46, D - 4], [47, D + 2], [7, D + 2]]));
      s += C.post(6, D - 4, 56, 3) + C.post(42, D - 4, 56, 3);
      for (var k = 0; k < 3; k++) {
        var y = D - 54 + k * 18;
        s += line(seg(4, y, 44, y), 1.8, 1, P.dark);
        for (var i = 0; i < 5; i++) {
          var x = 9 + i * 7.5;
          s += path('M' + f(x - 2) + ' ' + f(y) + 'L' + f(x + 2) + ' ' + f(y) + 'L' + f(x + 3) + ' ' + f(y + 10) + 'L' + f(x - 3) + ' ' + f(y + 10) + 'Z', (i + k) % 2 ? P.herb : P.leaf2, 0.8);
        }
      }
      return s;
    }
  });

  /* ---------- 葡萄园 wine ---------- */
  /* 葡萄架行列（专用地面）：每张瓦片一行木桩 + 铁丝 + 藤叶，左右边对齐成连续行 */
  C.groundSet({
    idKind: 'ground-vinerows', name: '葡萄架行列', resource: 'wine', base: P.soil, tags: ['trellis', 'crop_rows'],
    note: '平铺底纹：每格两行葡萄架（y=16、y=40），桩距 24 px，左右拼接连续；藤高 ≤ 10 px，不出格',
    under: function (ctx, v) {
      var s = '';
      [16, 40].forEach(function (y) {
        s += C.rect(0, y + 1, 48, 3, P.soil2, 0, 0.6);
        s += line(seg(0, y - 8, 48, y - 8), 0.6, 0.7, P.iron);
      });
      return s;
    },
    scatter: function (ctx, v) {
      var a = [];
      [16, 40].forEach(function (y) { for (var x = 0; x < 48; x += 6) a.push({ t: x % 24 === 0 ? 'post' : 'leaf', x: x + 3, y: y, k: ctx.r() }); });
      return a;
    },
    item: function (sub, it, x, y) {
      if (it.t === 'post') return C.post(x, y, 11, 2) ;
      var s = path(C.blob(sub, x, y - 6, 4, 3.4, 6, 0.2), it.k < 0.5 ? P.leaf : P.leaf2, 0.8);
      if (it.k < 0.3) s += C.ell(x + 1, y - 2.5, 1.6, 2.2, P.grape, 0.5);
      return s;
    }
  });
  /* 压榨坊：石墙木顶小屋 + 门前巨大的螺杆压榨机 */
  C.def({
    idKind: 'site-winepress', name: '压榨坊', cat: 'site', resource: 'wine', facility: null,
    w: 3, d: 2, up: 60, roof: 'gable_tile', tags: ['screw_press', 'cellar'],
    note: '中世纪梁式/螺杆葡萄压榨机放在开敞门廊下；FacilityKind 无酿酒坊，facility 为 null',
    draw: function (ctx, W, D) {
      var x0 = 10, x1 = W - 12, yb = D - 6, ye = yb - 46, yr = ye - 36, s = '', i;
      s += shade(poly([[x1, yb], [x1 + 10, yb - 4], [x1 + 10, ye + 4], [x1, ye]]));
      s += path(poly([[x0, ye], [x1, ye], [x1, yb], [x0, yb]]), P.stone, 1.6);
      var st = '';
      for (i = 0; i < 4; i++) st += seg(x0, ye + 10 + i * 10, x1, ye + 10 + i * 10);
      s += line(st, 0.7, 0.45);
      s += path(poly([[x0 + 8, yb - 30], [x0 + 26, yb - 30], [x0 + 26, yb], [x0 + 8, yb]]), '#2e241a', 1.2);
      s += C.roofGable(x0 - 8, x1 + 8, ye + 4, yr, 12, P.tile, P.red, 5);
      // 螺杆压榨机：两立柱 + 横梁 + 中间螺杆 + 压板 + 榨槽
      var px = W / 2 + 18;
      s += C.block(px - 26, yb - 2, 52, 8, 8, P.wood, P.timber, 1.3);
      s += ell(px, yb - 14, 22, 4, P.grape, 0.8);
      s += C.post(px - 20, yb - 10, 40, 5) + C.post(px + 20, yb - 10, 40, 5);
      s += path(poly([[px - 26, yb - 54], [px + 26, yb - 54], [px + 26, yb - 46], [px - 26, yb - 46]]), P.timber, 1.4);
      s += line(seg(px, yb - 46, px, yb - 20), 4, 1, P.dark) + line('M' + f(px - 2) + ' ' + f(yb - 44) + 'l4 3l-4 3l4 3l-4 3l4 3l-4 3', 0.8, 0.7, P.wood);
      s += path(poly([[px - 16, yb - 22], [px + 16, yb - 22], [px + 16, yb - 17], [px - 16, yb - 17]]), P.wood, 1.2);
      s += line(seg(px - 20, yb - 36, px + 20, yb - 36), 2, 1, P.dark);
      return s;
    }
  });
  /* 酒桶：两只卧桶在木架上 + 一只立桶 */
  C.def({
    idKind: 'prop-winebarrels', name: '酒桶', cat: 'prop', resource: 'wine', w: 1, d: 1, up: 2, tags: ['barrel', 'cask'],
    draw: function (ctx, W, D) {
      var s = shade(poly([[4, D - 4], [46, D - 4], [47, D + 2], [5, D + 2]]));
      s += line(seg(2, D - 4, 30, D - 4), 2, 1, P.dark);
      [[10, D - 14], [24, D - 14], [17, D - 32]].forEach(function (b) {
        s += ell(b[0], b[1], 8, 9, P.wood, 1.3) + ell(b[0], b[1], 5, 6, 'none', 0.7) + ell(b[0], b[1], 1.6, 1.6, P.dark, 0);
      });
      s += path('M34 ' + f(D - 30) + 'L46 ' + f(D - 30) + 'Q48 ' + f(D - 17) + ' 46 ' + f(D - 4) + 'L34 ' + f(D - 4) + 'Q32 ' + f(D - 17) + ' 34 ' + f(D - 30) + 'Z', P.wood, 1.3);
      s += ell(40, D - 30, 6, 2, P.timber, 1) + line(seg(33, D - 22, 47, D - 22) + seg(33, D - 11, 47, D - 11), 1.2, 1, P.iron);
      return s;
    }
  });
  /* 葡萄筐（采摘筐） */
  C.def({
    idKind: 'prop-grapebasket', name: '葡萄采摘筐', cat: 'prop', resource: 'wine', w: 1, d: 1, up: 0, tags: ['harvest'],
    draw: function (ctx, W, D) {
      var s = '';
      [[16, D - 6], [32, D - 8]].forEach(function (b) {
        s += C.shadowEll(b[0] + 2, b[1], 10, 2.5);
        s += path(poly([[b[0] - 9, b[1] - 16], [b[0] + 9, b[1] - 16], [b[0] + 7, b[1]], [b[0] - 7, b[1]]]), P.thatch2, 1.2);
        for (var i = 0; i < 5; i++) s += C.ell(b[0] - 6 + i * 3, b[1] - 17 - (i % 2) * 2, 2.2, 2.2, P.grape, 0.6);
        s += line(seg(b[0] - 8, b[1] - 9, b[0] + 8, b[1] - 9), 0.6, 0.5);
      });
      return s;
    }
  });

  /* ---------- 农牧小摆件补充 ---------- */
  C.def({   // 羊群（放牧中的三只羊）
    idKind: 'prop-sheep', name: '羊群', cat: 'prop', resource: 'livestock', w: 1, d: 1, up: 0, tags: ['animal', 'sheep'],
    draw: function (ctx, W, D) { return sheep(ctx, 14, D - 26, false) + sheep(ctx, 34, D - 18, true) + sheep(ctx, 18, D - 6, false); }
  });
  C.def({   // 羊毛捆（布包着的毛捆 + 秤）
    idKind: 'prop-woolbales', name: '羊毛捆', cat: 'prop', resource: 'wool', w: 1, d: 1, up: 4, tags: ['fleece', 'sack'],
    draw: function (ctx, W, D) {
      var s = shade(poly([[6, D - 4], [46, D - 4], [47, D + 2], [7, D + 2]]));
      [[13, D - 4, 11], [33, D - 4, 11], [23, D - 24, 10]].forEach(function (b) {
        s += path(C.blob(ctx, b[0], b[1] - b[2] * 0.9, b[2], b[2] * 0.85, 7, 0.08), P.wool, 1.3);
        s += line(seg(b[0] - b[2] * 0.8, b[1] - b[2], b[0] + b[2] * 0.8, b[1] - b[2] * 0.95), 1.1, 0.8, P.timber);
      });
      return s;
    }
  });
  C.def({   // 拴马桩 + 饮马槽
    idKind: 'prop-hitchtrough', name: '拴马桩与饮马槽', cat: 'prop', resource: 'horses', w: 1, d: 1, up: 6, tags: ['trough', 'hitching_rail'],
    draw: function (ctx, W, D) {
      var s = shade(poly([[4, D - 4], [46, D - 4], [47, D + 2], [5, D + 2]]));
      s += C.post(6, D - 18, 30, 3) + C.post(42, D - 18, 30, 3) + line(seg(4, D - 44, 44, D - 44), 2.4, 1, P.dark);
      s += C.block(6, D - 4, 36, 8, 10, P.water, P.timber, 1.3);
      s += line(seg(24, D - 44, 26, D - 32), 0.8, 0.9);
      return s;
    }
  });
  C.def({   // 麦捆垛（田间立起的麦捆）
    idKind: 'prop-sheafstook', name: '麦捆垛', cat: 'prop', resource: 'grain', w: 1, d: 1, up: 0, tags: ['sheaf', 'harvest'],
    draw: function (ctx, W, D) {
      var s = C.shadowEll(26, D - 6, 18, 4);
      return s + sheaf(14, D - 10, 22) + sheaf(34, D - 10, 22) + sheaf(20, D - 4, 24) + sheaf(29, D - 4, 24);
    }
  });
  C.def({   // 药篮（装满药草的柳条篮 + 小锄）
    idKind: 'prop-herbbasket', name: '药草篮', cat: 'prop', resource: 'herb', w: 1, d: 1, up: 0, tags: ['harvest', 'basket'],
    draw: function (ctx, W, D) {
      var s = C.shadowEll(24, D - 5, 16, 3.5);
      s += path(C.blob(ctx, 20, D - 20, 9, 6, 6, 0.2), P.herb, 0.9) + path(C.blob(ctx, 28, D - 19, 7, 5, 6, 0.2), '#a58fa8', 0.9);
      s += path(poly([[8, D - 18], [36, D - 18], [32, D - 4], [12, D - 4]]), P.thatch2, 1.3);
      s += line(seg(10, D - 13, 34, D - 13) + seg(11, D - 8, 33, D - 8), 0.6, 0.5);
      return s + line(seg(36, D - 4, 46, D - 24), 1.4, 1, P.timber) + path(poly([[34, D - 4], [40, D - 2], [38, D + 1], [32, D - 2]]), P.iron, 0.7);
    }
  });
})(typeof window !== 'undefined' ? window : this);
