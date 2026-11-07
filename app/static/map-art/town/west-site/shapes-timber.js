/*
 * 织梦 · 西式资源点 —— 伐木场 timber
 * draw(ctx, W, D) 在“地面坐标”里画：占地 x∈[0,W]、y∈[0,D]，y=D 是前沿；高度画成负 y，组装时整体下移 up。
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWS_core;
  var P = C.P, f = C.f, path = C.path, line = C.line, ell = C.ell, poly = C.poly, seg = C.seg, shade = C.shade;

  /* 锯木棚：开敞木构棚 + 茅草双坡顶 + 棚下锯台、架锯 + 一侧原木 */
  C.def({
    idKind: 'site-sawshed', name: '锯木棚', cat: 'site', resource: 'timber', facility: null,
    w: 3, d: 2, up: 52, roof: 'gable_thatch', tags: ['open_shed', 'saw_pit'],
    note: 'FacilityKind 无锯木坊，facility 为 null',
    draw: function (ctx, W, D) {
      var s = '', x0 = 10, x1 = W - 16, yb = D - 10, yeave = yb - 46, yr = yeave - 38;
      s += shade(poly([[x0 + 8, yb], [x1 + 14, yb], [x1 + 14, yb + 5], [x0 + 8, yb + 5]]));
      s += shade(poly([[x1, yb], [x1 + 14, yb - 6], [x1 + 14, yeave + 4], [x1, yeave]]));
      // 地坪（踩实的土+锯末）
      s += path(poly([[x0 - 2, yb + 2], [x1 + 2, yb + 2], [x1 - 4, yb - 30], [x0 + 4, yb - 30]]), P.yard, 1);
      var dust = '';
      for (var i = 0; i < 14; i++) { var u = ctx.rnd(x0 + 6, x1 - 6), v = ctx.rnd(yb - 26, yb - 2); dust += seg(u, v, u + 1.6, v - 0.3); }
      s += line(dust, 0.8, 0.5, P.wash);
      // 后排柱
      for (i = 0; i < 4; i++) s += C.post(x0 + 6 + i * (x1 - x0 - 12) / 3, yb - 28, 40, 3.2);
      // 架锯（双人立锯）：锯架 + 一根架在上面的原木
      var sx = x0 + 30, sy = yb - 12;
      s += line(seg(sx, sy, sx + 10, sy - 20) + seg(sx + 20, sy, sx + 10, sy - 20) + seg(sx + 46, sy, sx + 56, sy - 20) + seg(sx + 66, sy, sx + 56, sy - 20), 2, 1, P.dark);
      s += C.logSide(sx + 2, sx + 66, sy - 22, 5);
      s += path(poly([[sx + 32, sy - 40], [sx + 35, sy - 40], [sx + 35, sy - 2], [sx + 32, sy - 2]]), P.iron, 0.8);
      s += line(seg(sx + 26, sy - 40, sx + 42, sy - 40) + seg(sx + 27, sy - 2, sx + 40, sy - 2), 2, 1, P.timber);
      // 锯好的板材斜靠在右侧
      for (i = 0; i < 4; i++) {
        var bx = x1 - 34 + i * 6;
        s += path(poly([[bx, yb - 2], [bx + 4, yb - 2], [bx + 10, yb - 36], [bx + 6, yb - 36]]), i % 2 ? P.wood : P.wash, 0.9);
      }
      // 前排柱
      for (i = 0; i < 4; i++) s += C.post(x0 + 2 + i * (x1 - x0 - 4) / 3, yb, 46, 4);
      s += line(seg(x0 - 4, yeave + 2, x1 + 4, yeave + 2), 3, 1, P.dark);
      // 茅草屋顶
      s += C.roofGable(x0 - 10, x1 + 10, yeave + 4, yr, 14, P.thatch, P.thatch2, 5);
      var th = '';
      for (i = 0; i < 22; i++) { var tx = x0 - 6 + i * (x1 - x0 + 12) / 21; th += seg(tx, yeave + 4, tx + ctx.rnd(-1, 1), yeave - 3); }
      s += line(th, 0.8, 0.7, P.thatch2);
      s += line(seg(x0 + 4, yr, x1 - 4, yr), 3, 1, P.thatch2) + line(seg(x0 + 4, yr, x1 - 4, yr), 1.2);
      // 棚右外侧的原木
      s += C.logEnd(x1 + 9, yb - 6, 6) + C.logEnd(x1 + 4, yb - 17, 5.5) + C.logEnd(x1 + 14, yb - 17, 5);
      return s;
    }
  });

  /* 水力锯：引水木槽 + 立式水轮 + 带锯架的木屋 */
  C.def({
    idKind: 'site-watersaw', name: '水力锯坊', cat: 'site', resource: 'timber', facility: null,
    w: 3, d: 3, up: 60, roof: 'gable_tile', tags: ['water_wheel', 'sash_saw'],
    note: '中世纪水力往复锯（框锯）；需临水。FacilityKind 的 mill 指磨坊，故 facility 为 null',
    draw: function (ctx, W, D) {
      var s = '', hx0 = 52, hx1 = W - 8, yb = D - 8, yeave = yb - 50, yr = yeave - 40;
      // 左侧水渠（贴地，向前流出）
      s += path(poly([[0, D - 2], [34, D - 2], [34, 18], [0, 18]]), P.water, 1.2);
      s += line(seg(6, 40, 14, 40) + seg(18, 70, 28, 70) + seg(8, 100, 18, 100) + seg(16, 124, 26, 124), 0.9, 0.6, P.water2);
      s += line(seg(34, 18, 34, D - 2), 1.6);
      // 房体投影与墙
      s += shade(poly([[hx1, yb], [hx1 + 8, yb - 4], [hx1 + 8, yeave + 4], [hx1, yeave]]));
      s += path(poly([[hx0, yb - 40], [hx1, yb - 40], [hx1, yb], [hx0, yb]]), P.wood, 1.6);
      s += path(poly([[hx0, yb - 40], [hx1, yb - 40], [hx1, yeave], [hx0, yeave]]), P.wood, 1.6);
      var pl = '';
      for (var i = 1; i < 9; i++) { var px = hx0 + i * (hx1 - hx0) / 9; pl += seg(px, yeave + 1, px, yb - 1); }
      s += line(pl, 0.8, 0.55);
      // 大门敞开，露出锯框与原木
      var dx0 = hx0 + 26, dx1 = hx1 - 12, dy = yb - 34;
      s += path(poly([[dx0, dy], [dx1, dy], [dx1, yb], [dx0, yb]]), P.dark, 1.2);
      s += C.logSide(dx0 + 2, dx1 - 2, yb - 12, 5);
      s += path(poly([[dx0 + 22, dy + 2], [dx0 + 34, dy + 2], [dx0 + 34, yb - 4], [dx0 + 22, yb - 4]]), 'none', 1.6);
      s += line(seg(dx0 + 28, dy + 2, dx0 + 28, yb - 4), 1, 1, P.tin);
      // 瓦顶
      s += C.roofGable(hx0 - 6, hx1 + 6, yeave + 3, yr, 12, P.tile, P.red, 6);
      // 引水木槽（从后方架到轮顶）+ 立式水轮（下半浸在渠里）
      var wx = 26, wy = yb - 34, wr = 26;
      s += path(poly([[18, wy - wr - 10], [30, wy - wr - 10], [30, 2], [18, 2]]), P.timber, 1.2);
      s += line(seg(20, 4, 20, wy - wr - 10), 0.7, 0.6, P.water2);
      s += C.wheel(wx, wy, wr);
      var pad = '';
      for (i = 0; i < 12; i++) {
        var a = i * Math.PI / 6, c = Math.cos(a), sn = Math.sin(a);
        pad += seg(wx + c * wr, wy + sn * wr, wx + c * (wr + 5), wy + sn * (wr + 5));
      }
      s += line(pad, 2.4, 1, P.dark);
      s += line(seg(wx, wy, hx0, wy), 3, 1, P.iron);
      s += path(poly([[2, wy + wr - 6], [44, wy + wr - 6], [44, wy + wr + 6], [2, wy + wr + 6]]), P.water, 0, 0.85);
      s += line(seg(6, wy + wr - 2, 14, wy + wr - 2) + seg(26, wy + wr + 2, 38, wy + wr + 2), 0.9, 0.7, P.water2);
      return s;
    }
  });

  /* 原木垛：金字塔式横堆 + 两侧楔桩 */
  C.def({
    idKind: 'prop-logpile', name: '原木垛', cat: 'prop', resource: 'timber', w: 1, d: 1, up: 14, tags: ['stack'],
    draw: function (ctx, W, D) {
      var s = shade(poly([[6, D - 4], [46, D - 4], [48, D + 3], [8, D + 3]]));
      var rows = [[0, 4], [1, 3], [2, 2]], r = 5.2, i, j;
      s += C.post(5, D - 4, 16, 2.6) + C.post(43, D - 4, 16, 2.6);
      for (i = 0; i < rows.length; i++) {
        var n = rows[i][1], y = D - 9 - i * 9, x0 = 24 - (n - 1) * r * 1.05;
        for (j = 0; j < n; j++) s += C.logEnd(x0 + j * r * 2.1, y, r, j % 2 ? P.wash : P.wood);
      }
      return s + line(seg(8, D - 30, 40, D - 30), 0.7, 0.4);
    }
  });

  /* 运木车：两轮牛车 + 绑着的长原木 */
  C.def({
    idKind: 'prop-logcart', name: '运木车', cat: 'prop', resource: 'timber', w: 1, d: 1, up: 12, tags: ['cart'],
    draw: function (ctx, W, D) {
      var s = shade(poly([[4, D - 6], [46, D - 6], [47, D + 2], [5, D + 2]]));
      s += line(seg(2, D - 16, 14, D - 20), 2.2, 1, P.dark);                       // 车辕
      s += path(poly([[10, D - 22], [42, D - 22], [42, D - 17], [10, D - 17]]), P.wood, 1.2);
      s += C.logSide(6, 44, D - 27, 4.5) + C.logSide(9, 46, D - 35, 4);
      s += line(seg(18, D - 40, 18, D - 18) + seg(36, D - 40, 36, D - 18), 1.2, 1, P.dark);   // 捆绳
      s += C.wheel(26, D - 11, 9);
      return s;
    }
  });

  /* 劈柴墩：树墩 + 斧头 + 劈好的柴 */
  C.def({
    idKind: 'prop-chopblock', name: '劈柴墩', cat: 'prop', resource: 'timber', w: 1, d: 1, up: 6, tags: ['axe'],
    draw: function (ctx, W, D) {
      var s = C.stump(ctx, 18, D - 12, 8);
      s += line(seg(20, D - 20, 30, D - 36), 2, 1, P.timber) + path(poly([[16, D - 23], [22, D - 26], [23, D - 19], [18, D - 18]]), P.iron, 0.9);
      for (var i = 0; i < 5; i++) {
        var x = 30 + (i % 3) * 5, y = D - 6 - Math.floor(i / 3) * 5;
        s += path(poly([[x, y], [x + 5, y - 1], [x + 4, y - 5], [x - 1, y - 4]]), i % 2 ? P.wash : P.wood, 0.8);
      }
      return s;
    }
  });

  /* 树桩地：可平铺 48×48 底纹，4 变体（草地 + 树桩 + 木屑 + 枝丫） */
  for (var gv = 1; gv <= 4; gv++) (function (v) {
    C.def({
      idKind: 'ground-stumpfield', name: '树桩地', cat: 'ground', resource: 'timber', variant: v, w: 1, d: 1, up: 0,
      tags: ['tile', 'seamless'], note: '平铺底纹；元素按 ±48 平移复制后裁切，任意排列无缝',
      draw: function (ctx, W, D) {
        var s = C.rect(0, 0, W, D, P.grass, 0), items = [], i;
        for (i = 0; i < 5; i++) items.push({ t: 'chip', x: ctx.rnd(0, 48), y: ctx.rnd(0, 48) });
        for (i = 0; i < 4; i++) items.push({ t: 'tuft', x: ctx.rnd(0, 48), y: ctx.rnd(0, 48) });
        if (v !== 2) items.push({ t: 'stump', x: ctx.rnd(10, 38), y: ctx.rnd(16, 40), r: ctx.rnd(4.5, 6.5) });
        if (v === 3) items.push({ t: 'stump', x: ctx.rnd(4, 44), y: ctx.rnd(8, 44), r: 4 });
        if (v !== 1) items.push({ t: 'twig', x: ctx.rnd(0, 48), y: ctx.rnd(0, 48) });
        var sub = new C.Ctx(ctx.id + '-w');
        s += C.tileWrap(ctx, W, D, function (ox, oy) {
          var o = '';
          items.forEach(function (it) {
            var x = it.x + ox, y = it.y + oy;
            if (it.t === 'chip') o += C.rect(x, y, 2.2, 1, P.wash, 0, 0.9);
            else if (it.t === 'tuft') o += C.tuft(sub, x, y, 4, 3);
            else if (it.t === 'stump') { sub.r = C.rng(Math.round(it.x * 100)); o += C.stump(sub, x, y, it.r); }
            else o += line(seg(x, y, x + 9, y - 2) + seg(x + 5, y - 1, x + 7, y - 4), 1, 0.8, P.timber);
          });
          return o;
        });
        return s;
      }
    });
  })(gv);
})(typeof window !== 'undefined' ? window : this);
