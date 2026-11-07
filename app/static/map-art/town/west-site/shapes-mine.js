/*
 * 织梦 · 西式资源点 —— 矿山主体（铁、铜、锡、金、银、煤）
 * 两种形制：井架绞盘（竖井）与山腹矿道口（平硐）；各矿种另有专属配套部件，不只换矿石色。
 * draw(ctx, W, D) 在“地面坐标”里画：占地 x∈[0,W]、y∈[0,D]，y=D 是前沿；高度画成负 y。
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWS_core;
  var P = C.P, f = C.f, path = C.path, line = C.line, ell = C.ell, poly = C.poly, seg = C.seg, shade = C.shade;
  var HOLE = '#2e241a';

  /** 竖井井口：木框 + 黑洞 */
  function collar(cx, yb, w) {
    var h = w * 0.5;
    return path(poly([[cx - w / 2, yb - h], [cx + w / 2, yb - h], [cx + w / 2, yb], [cx - w / 2, yb]]), P.timber, 1.4) +
      path(poly([[cx - w / 2 + 4, yb - h + 3], [cx + w / 2 - 4, yb - h + 3], [cx + w / 2 - 4, yb - 3], [cx - w / 2 + 4, yb - 3]]), HOLE, 1);
  }
  /** 井架：A 字木架 + 横撑 + 顶上天轮 + 吊绳 */
  function headframe(ctx, cx, yb, h, w, tall) {
    var s = shade(poly([[cx + w / 2, yb], [cx + w / 2 + 16, yb - 4], [cx + 18, yb - h * 0.6], [cx + 4, yb - h]]));
    var top = yb - h, L = cx - w / 2, R = cx + w / 2;
    s += line(seg(L, yb, cx - 5, top) + seg(R, yb, cx + 5, top), 3.4, 1, P.dark) + line(seg(L, yb, cx - 5, top) + seg(R, yb, cx + 5, top), 1.4, 1, P.timber);
    var br = '';
    for (var i = 1; i <= (tall ? 3 : 2); i++) {
      var t = i / ((tall ? 3 : 2) + 0.6), y = yb - h * t, xa = L + (cx - 5 - L) * t, xb = R - (R - cx - 5) * t;
      br += seg(xa, y, xb, y);
      if (i === 1) br += seg(xa, y, R - (R - cx - 5) * (t * 0.3), yb - h * t * 0.3);
    }
    s += line(br, 2, 1, P.dark);
    s += C.block(cx - 10, top + 2, 20, 4, 3, P.wood, P.timber, 1.2);
    s += C.wheel(cx, top - 8, 9);
    s += line(seg(cx - 6, top - 6, cx - 6, yb - 20), 0.9, 1);
    return s + collar(cx, yb, Math.max(22, w * 0.45));
  }
  /** 山体（平硐所在的山坡）：左亮右暗 + 岩层线；返回 d 与 svg */
  function hill(ctx, x0, x1, yb, top, fill, fill2) {
    var mid = (x0 + x1) / 2;
    // 起伏山脊：左缓坡 → 肩 → 主峰 → 右肩 → 落到地面（不是对称圆顶）
    var hh = yb - top;
    var d = 'M' + f(x0) + ' ' + f(yb) + 'Q' + f(x0 + 14) + ' ' + f(top + hh * 0.55) + ' ' + f(x0 + 40) + ' ' + f(top + hh * 0.35) +
      'Q' + f(mid - 30) + ' ' + f(top + hh * 0.12) + ' ' + f(mid - 6) + ' ' + f(top) +
      'Q' + f(mid + 18) + ' ' + f(top + hh * 0.08) + ' ' + f(mid + 34) + ' ' + f(top + hh * 0.3) +
      'Q' + f(x1 - 30) + ' ' + f(top + hh * 0.36) + ' ' + f(x1 - 16) + ' ' + f(top + hh * 0.6) +
      'Q' + f(x1 - 4) + ' ' + f(top + hh * 0.8) + ' ' + f(x1) + ' ' + f(yb) + 'Z';
    var s = path(d, fill, 1.8);
    s += C.clip(ctx, d, path(poly([[mid + 6, top - 4], [x1 + 4, top - 4], [x1 + 4, yb], [mid + 30, yb]]), fill2, 0));
    var st = '';
    for (var i = 0; i < 6; i++) { var y = ctx.rnd(top + 14, yb - 10), x = ctx.rnd(x0 + 16, x1 - 40); st += seg(x, y, x + ctx.rnd(10, 22), y + ctx.rnd(-2, 2)); }
    s += C.clip(ctx, d, line(st, 0.8, 0.5));
    s += C.clip(ctx, d, path('M' + f(x0) + ' ' + f(top + 4) + 'Q' + f(mid) + ' ' + f(top - 8) + ' ' + f(x1) + ' ' + f(top + 4) + 'L' + f(x1) + ' ' + f(top - 20) + 'L' + f(x0) + ' ' + f(top - 20) + 'Z', P.leaf2, 0));
    return { d: d, s: s };
  }
  /** 平硐口：黑洞 + 两柱一梁的木支护 */
  function portal(cx, yb, w, h) {
    var s = path(poly([[cx - w / 2, yb], [cx - w / 2 + 2, yb - h], [cx + w / 2 - 2, yb - h], [cx + w / 2, yb]]), HOLE, 1.2);
    s += C.post(cx - w / 2 + 1, yb, h + 2, 5) + C.post(cx + w / 2 - 1, yb, h + 2, 5);
    s += path(poly([[cx - w / 2 - 5, yb - h - 7], [cx + w / 2 + 5, yb - h - 7], [cx + w / 2 + 5, yb - h], [cx - w / 2 - 5, yb - h]]), P.timber, 1.4);
    return s + line(seg(cx - w / 2 - 2, yb - h - 3.5, cx + w / 2 + 2, yb - h - 3.5), 0.6, 0.5);
  }
  /** 矿车轨道（朝观者延伸，近大远小） */
  function rails(cx, ytop, yb, nearHalf) {
    var farHalf = nearHalf * 0.6, sl = '', n = Math.max(2, Math.round((yb - ytop) / 7));
    for (var i = 0; i <= n; i++) {
      var t = i / n, y = ytop + (yb - ytop) * t, hw = farHalf + (nearHalf - farHalf) * t + 3;
      sl += seg(cx - hw, y, cx + hw, y);
    }
    return line(sl, 2, 1, P.timber) +
      line(seg(cx - farHalf, ytop, cx - nearHalf, yb) + seg(cx + farHalf, ytop, cx + nearHalf, yb), 1.6, 1, P.iron);
  }
  /** 矿车：木斗 + 铁箍 + 小轮 + 斗里的矿石 */
  function minecart(ctx, cx, yb, ore, ore2) {
    var s = C.shadowEll(cx + 3, yb, 15, 3);
    s += ell(cx - 8, yb - 4, 3.5, 3.5, P.iron, 1) + ell(cx + 8, yb - 4, 3.5, 3.5, P.iron, 1);
    for (var i = 0; i < 6; i++) {
      var x = cx - 10 + i * 4, y = yb - 19 - ctx.rnd(0, 3);
      s += path(poly([[x - 3, y + 3], [x - 1, y - 1], [x + 3, y - 2], [x + 4, y + 3]]), i % 2 ? ore : (ore2 || ore), 0.8);
    }
    s += path(poly([[cx - 13, yb - 18], [cx + 13, yb - 18], [cx + 10, yb - 6], [cx - 10, yb - 6]]), P.timber, 1.4);
    return s + line(seg(cx - 6, yb - 18, cx - 5, yb - 6) + seg(cx + 6, yb - 18, cx + 5, yb - 6), 1.4, 1, P.iron);
  }
  /** 矿石堆（按矿种上色） */
  function oreHeap(ctx, cx, yb, rx, ry, base, a, b, n) { return C.heap(ctx, cx, yb, rx, ry, base, a, b, n); }

  C.mine = { HOLE: HOLE, collar: collar, headframe: headframe, hill: hill, portal: portal, rails: rails, minecart: minecart, oreHeap: oreHeap };

  /* 矿种：矿石主色/副色/堆底色，形制 shaft=井架 adit=平硐，hillTint=山体染色（铜矿绿锈、煤层黑带） */
  var ORES = {
    iron: { zh: '铁矿', a: P.ironore, b: '#6f4535', base: P.soil2, type: 'shaft' },
    copper: { zh: '铜矿', a: P.copper, b: P.copper2, base: P.stone3, type: 'adit', tint: P.copper },
    tin: { zh: '锡矿', a: P.tin, b: '#7f817c', base: P.stone2, type: 'adit' },
    gold: { zh: '金矿', a: P.gold, b: '#b48d34', base: P.soil, type: 'adit' },
    silver: { zh: '银矿', a: P.silver, b: '#8e9599', base: P.stone3, type: 'shaft' },
    coal: { zh: '煤矿', a: P.coal, b: P.coal2, base: '#4e4943', type: 'adit', tint: P.coal }
  };
  C.ORES = ORES;

  /** 绞车房：小木棚 + 卷筒（井架矿用） */
  function winchHouse(ctx, x, yb) {
    var s = shade(poly([[x + 44, yb], [x + 52, yb - 4], [x + 52, yb - 30], [x + 44, yb - 34]]));
    s += path(poly([[x, yb - 30], [x + 44, yb - 30], [x + 44, yb], [x, yb]]), P.wood, 1.5);
    s += line(seg(x + 11, yb - 29, x + 11, yb - 1) + seg(x + 22, yb - 29, x + 22, yb - 1) + seg(x + 33, yb - 29, x + 33, yb - 1), 0.8, 0.5);
    s += path(poly([[x + 14, yb - 22], [x + 30, yb - 22], [x + 30, yb], [x + 14, yb]]), HOLE, 1);
    s += ell(x + 22, yb - 10, 6, 5, P.timber, 1) + line(seg(x + 16, yb - 10, x + 28, yb - 10), 0.8, 0.8);
    return s + C.roofGable(x - 5, x + 49, yb - 28, yb - 48, 8, P.thatch, P.thatch2, 3);
  }
  /** 马拉绞盘（银矿）：立轴 + 横杆 + 一匹拉磨的马（简化轮廓） */
  function horseWhim(ctx, cx, yb) {
    var s = C.shadowEll(cx + 4, yb - 6, 34, 9);
    s += ell(cx, yb - 8, 32, 9, P.yard2, 1, 0.9);
    s += C.post(cx, yb - 8, 34, 5) + ell(cx, yb - 42, 8, 3, P.timber, 1.2);
    s += line(seg(cx, yb - 30, cx + 28, yb - 16), 2.6, 1, P.dark);
    var hx = cx + 30, hy = yb - 6;            // 马
    s += path('M' + f(hx - 12) + ' ' + f(hy - 16) + 'Q' + f(hx) + ' ' + f(hy - 22) + ' ' + f(hx + 10) + ' ' + f(hy - 17) + 'L' + f(hx + 16) + ' ' + f(hy - 26) +
      'L' + f(hx + 20) + ' ' + f(hy - 22) + 'L' + f(hx + 13) + ' ' + f(hy - 11) + 'L' + f(hx - 12) + ' ' + f(hy - 9) + 'Z', P.timber, 1.2);
    s += line(seg(hx - 9, hy - 10, hx - 10, hy) + seg(hx - 4, hy - 10, hx - 3, hy) + seg(hx + 5, hy - 11, hx + 6, hy) + seg(hx + 10, hy - 11, hx + 12, hy), 1.8, 1, P.dark);
    return s;
  }

  function mineSite(kind) {
    var O = ORES[kind];
    C.def({
      idKind: 'site-mine-' + kind, name: O.zh + (O.type === 'shaft' ? '井架' : '矿道口'), cat: 'site', resource: kind, facility: 'mine_head',
      w: 4, d: 3, up: O.type === 'shaft' ? 96 : 64, roof: 'none',
      tags: O.type === 'shaft' ? ['headframe', 'shaft', 'winch'] : ['adit', 'hillside', 'timbered_portal'],
      note: (O.type === 'shaft' ? '竖井：A 字木井架 + 天轮 + 绞车房' : '平硐：山腹矿道口 + 木支护') + '，矿车轨道通向矿石堆；' + (O.note || ''),
      draw: function (ctx, W, D) {
        var s = path(poly([[4, D - 2], [W - 4, D - 2], [W - 10, D - 60], [10, D - 60]]), P.yard2, 1, 0.9);
        var cx, ytop;
        if (O.type === 'shaft') {
          cx = 66; ytop = D - 34;
          if (kind === 'silver') s += horseWhim(ctx, 150, D - 30);
          else s += winchHouse(ctx, 128, D - 52);
          s += C.mine.headframe(ctx, cx, ytop, 116, 64, true);
          s += line(seg(cx + 6, ytop - 124, 140, D - 70), 0.8, 0.8);
        } else {
          var h = C.mine.hill(ctx, 2, W - 2, D - 44, -58, P.stone2, P.stone3);
          s += h.s;
          if (O.tint) s += C.clip(ctx, h.d, line('M8 ' + f(D - 70) + 'Q60 ' + f(D - 80) + ' 120 ' + f(D - 72) + 'T' + f(W) + ' ' + f(D - 78), kind === 'coal' ? 6 : 3, kind === 'coal' ? 0.9 : 0.6, O.tint));
          cx = 74; ytop = D - 44;
          s += C.mine.portal(cx, ytop, 30, 30);
        }
        s += C.mine.rails(cx, ytop, D - 3, 9);
        s += C.mine.minecart(ctx, cx, D - 10, O.a, O.b);
        s += C.mine.oreHeap(ctx, W - 40, D - 6, 28, 20, O.base, O.a, O.b, 14);
        if (O.extra) s += O.extra(ctx, W, D);
        return s;
      }
    });
  }
  // 各矿种在主体上的专属部件
  ORES.copper.extra = function (ctx, W, D) {          // 铜矿：坡上一道绿色氧化铜渍
    return path('M110 ' + f(D - 98) + 'q6 14 2 30q8 -10 12 -26z', P.copper, 0.9, 0.85);
  };
  ORES.gold.extra = function (ctx, W, D) {            // 金矿：矿道口旁的小溪
    return path('M' + f(W - 76) + ' ' + f(D - 2) + 'Q' + f(W - 90) + ' ' + f(D - 30) + ' ' + f(W - 70) + ' ' + f(D - 46) + 'L' + f(W - 60) + ' ' + f(D - 44) +
      'Q' + f(W - 78) + ' ' + f(D - 28) + ' ' + f(W - 64) + ' ' + f(D - 2) + 'Z', P.water, 1.2);
  };
  ORES.coal.extra = function (ctx, W, D) {            // 煤矿：洞口上方熏黑
    return path('M62 ' + f(D - 80) + 'q12 -10 24 0l-4 6h-16z', P.coal, 0, 0.5);
  };
  ORES.gold.note = '旁有溪流，配套淘金槽'; ORES.coal.note = '山体露出黑色煤层'; ORES.copper.note = '山坡带绿色铜锈'; ORES.silver.note = '马拉绞盘提升';
  Object.keys(ORES).forEach(mineSite);

  /* ---------- 矿山配套摆件：每矿种一个矿石堆 + 一辆满载矿车（轨道一段） ---------- */
  Object.keys(ORES).forEach(function (kind) {
    var O = ORES[kind];
    C.def({
      idKind: 'prop-ore-' + kind, name: O.zh + '矿石堆', cat: 'prop', resource: kind, w: 1, d: 1, up: 0, tags: ['ore', 'heap'],
      draw: function (ctx, W, D) {
        var s = C.heap(ctx, 24, D - 6, 20, kind === 'coal' ? 24 : 19, O.base, O.a, O.b, kind === 'coal' ? 16 : 12);
        if (kind === 'coal') s += line(seg(12, D - 14, 18, D - 22) + seg(28, D - 26, 34, D - 18), 0.7, 0.5, P.slate);   // 煤块反光的棱
        return s;
      }
    });
    C.def({
      idKind: 'prop-minecart-' + kind, name: O.zh + '矿车', cat: 'prop', resource: kind, w: 1, d: 1, up: 0, tags: ['minecart', 'rails'],
      draw: function (ctx, W, D) { return C.mine.rails(24, 4, D - 2, 9) + C.mine.minecart(ctx, 24, D - 12, O.a, O.b); }
    });
  });

  /* ---------- 各矿种专属配套 ---------- */
  C.def({   // 金：淘金槽（斜架木槽 + 横格挡 + 流水 + 淘盘）
    idKind: 'prop-sluice', name: '淘金槽', cat: 'prop', resource: 'gold', w: 1, d: 1, up: 10, tags: ['sluice', 'placer'],
    draw: function (ctx, W, D) {
      var s = shade(poly([[6, D - 4], [46, D - 4], [47, D + 2], [7, D + 2]]));
      s += C.post(8, D - 4, 24, 3) + C.post(40, D - 4, 10, 3);
      s += path(poly([[2, D - 34], [10, D - 38], [46, D - 14], [40, D - 8]]), P.wood, 1.3);
      s += path(poly([[5, D - 34], [10, D - 36], [42, D - 14], [39, D - 11]]), P.water, 0.6);
      var r = '';
      for (var i = 1; i < 6; i++) { var t = i / 6; r += seg(5 + 34 * t, D - 34 + 22 * t, 10 + 32 * t, D - 36 + 22 * t); }
      s += line(r, 1.2, 1, P.timber);
      s += ell(16, D - 6, 9, 3.5, P.iron, 1.2) + ell(16, D - 6.5, 5, 1.8, P.gold, 0);
      return s;
    }
  });
  C.def({   // 铁：焙烧堆（矿石与木柴层叠、冒烟）
    idKind: 'prop-roastclamp', name: '焙烧矿堆', cat: 'prop', resource: 'iron', w: 1, d: 1, up: 20, tags: ['roasting', 'smoke'],
    draw: function (ctx, W, D) {
      var s = C.heap(ctx, 24, D - 6, 20, 16, P.soil2, P.ironore, '#6f4535', 10);
      s += line(seg(8, D - 10, 40, D - 10) + seg(12, D - 16, 36, D - 16), 1.6, 1, P.dark);
      s += path('M18 ' + f(D - 12) + 'q3 -5 6 0q2 -6 5 0z', P.fire, 0.8);
      s += path('M22 ' + f(D - 24) + 'q-6 -8 2 -14q-4 -8 4 -14q6 4 2 10q8 4 2 12z', P.stone, 1, 0.75);
      return s;
    }
  });
  C.def({   // 锡：圆形洗矿池（buddle）+ 转耙
    idKind: 'prop-buddle', name: '洗矿圆池', cat: 'prop', resource: 'tin', w: 1, d: 1, up: 4, tags: ['ore_dressing', 'water'],
    draw: function (ctx, W, D) {
      var s = C.shadowEll(26, D - 12, 22, 9);
      s += ell(24, D - 14, 21, 9, P.stone2, 1.5) + ell(24, D - 15, 16, 6.5, P.water, 1);
      s += ell(24, D - 15, 9, 3.6, P.tin, 0.6, 0.8);
      s += C.post(24, D - 14, 18, 3) + line(seg(10, D - 22, 38, D - 30), 1.8, 1, P.dark);
      return s;
    }
  });
  C.def({   // 铜：淋滤池（绿色胆水木槽）
    idKind: 'prop-leachpit', name: '淋铜池', cat: 'prop', resource: 'copper', w: 1, d: 1, up: 0, tags: ['leaching', 'water'],
    draw: function (ctx, W, D) {
      var s = shade(poly([[6, D - 4], [46, D - 4], [47, D + 2], [7, D + 2]]));
      s += C.block(4, D - 4, 40, 18, 8, P.copper, P.timber, 1.4);
      s += line(seg(8, D - 18, 40, D - 18) + seg(10, D - 22, 38, D - 22), 0.7, 0.5, '#3f6f5f');
      s += line(seg(24, D - 30, 24, D - 4), 1.2, 1, P.timber);
      s += C.heap(ctx, 38, D - 30, 9, 8, P.stone3, P.copper2, P.copper, 5);
      return s;
    }
  });
  C.def({   // 银：灰吹炉（小石炉 + 风箱）
    idKind: 'prop-cupel', name: '灰吹炉', cat: 'prop', resource: 'silver', w: 1, d: 1, up: 18, tags: ['cupellation', 'furnace'],
    draw: function (ctx, W, D) {
      var s = shade(poly([[10, D - 4], [44, D - 4], [46, D + 2], [12, D + 2]]));
      s += C.block(10, D - 4, 22, 8, 20, P.stone, P.stone3, 1.4);
      s += path(poly([[16, D - 6], [26, D - 6], [26, D - 16], [16, D - 16]]), '#2e241a', 1) + path('M17 ' + f(D - 7) + 'q4 -6 8 0z', P.fire, 0);
      s += C.block(16, D - 32, 10, 4, 18, P.stone2, P.stone3, 1.2);
      s += path(poly([[34, D - 8], [46, D - 14], [46, D - 4], [34, D - 4]]), P.timber, 1.1);
      return s + ell(20, D - 8, 2, 1, P.silver, 0);
    }
  });
  C.def({   // 煤：筐装煤（背篓 + 黑煤块）
    idKind: 'prop-coalbaskets', name: '煤筐', cat: 'prop', resource: 'coal', w: 1, d: 1, up: 0, tags: ['basket'],
    draw: function (ctx, W, D) {
      var s = '';
      [[14, D - 6], [32, D - 8]].forEach(function (b, k) {
        s += C.shadowEll(b[0] + 2, b[1] + 1, 10, 3);
        s += path(poly([[b[0] - 9, b[1] - 18], [b[0] + 9, b[1] - 18], [b[0] + 7, b[1]], [b[0] - 7, b[1]]]), P.thatch2, 1.3);
        s += line(seg(b[0] - 8, b[1] - 12, b[0] + 8, b[1] - 12) + seg(b[0] - 7, b[1] - 6, b[0] + 7, b[1] - 6), 0.7, 0.6);
        s += C.heap(new C.Ctx('coalb' + k), b[0], b[1] - 17, 8, 6, P.coal, P.coal2, P.coal, 5);
      });
      return s;
    }
  });

  /* ---------- 矿区地面 ---------- */
  C.groundSet({
    idKind: 'ground-slag', name: '矿渣地', resource: 'iron', base: P.soil2, tags: ['mine_floor'],
    note: '平铺底纹；铁/铜/锡/金/银矿共用（resource 记 iron）；元素按 ±48 平移复制后裁切，任意排列无缝',
    scatter: function (ctx, v) { return C.scatter(ctx, 10 + v, 'chip'); },
    item: function (sub, it, x, y) {
      return it.k < 0.2 ? C.rock(sub, x, y, 2.8, P.stone3, P.dark, 0.8) : C.rect(x, y, 2.4, 1.6, it.k < 0.55 ? P.dark : P.soil, 0, 0.9);
    }
  });
  C.groundSet({
    idKind: 'ground-coaldust', name: '煤尘地', resource: 'coal', base: '#6e665a', tags: ['mine_floor'],
    scatter: function (ctx, v) { return C.scatter(ctx, 12 + v, 'chip'); },
    item: function (sub, it, x, y) { return C.rect(x, y, it.k < 0.3 ? 3 : 2, 1.6, it.k < 0.6 ? P.coal : P.coal2, 0, 0.95); }
  });
})(typeof window !== 'undefined' ? window : this);
