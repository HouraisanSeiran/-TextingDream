/*
 * 织梦 · 西式资源点 —— 黏土 clay、盐 salt、硫磺 sulfur、宝石 gems、琥珀 amber
 * draw(ctx, W, D) 在“地面坐标”里画：占地 x∈[0,W]、y∈[0,D]，y=D 是前沿；高度画成负 y。
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWS_core;
  var P = C.P, f = C.f, path = C.path, line = C.line, ell = C.ell, poly = C.poly, seg = C.seg, shade = C.shade;

  /** 下挖的坑：外沿土唇 + 坑壁（前低后高，坑壁后侧可见）+ 坑底 */
  function pit(ctx, cx, cy, rx, ry, rim, wall, floor, depth) {
    var s = ell(cx, cy, rx, ry, rim, 1.6);
    s += ell(cx, cy + 2, rx - 8, ry - 6, wall, 1.2);
    s += ell(cx, cy + 2 + depth * 0.4, rx - 12, ry - 6 - depth * 0.4, floor, 1);
    var st = '';
    for (var i = 0; i < 9; i++) { var a = Math.PI * (1.05 + i * 0.1), x = cx + Math.cos(a) * (rx - 9), y = cy + 2 + Math.sin(a) * (ry - 7); st += seg(x, y, x, y + depth * 0.35); }
    return s + line(st, 0.7, 0.45);
  }
  C.pit = pit;

  /* 取土坑：挖开的红黏土坑 + 坑中积水 + 坑沿铁锹与独轮车 */
  C.def({
    idKind: 'site-claypit', name: '取土坑', cat: 'site', resource: 'clay', facility: null,
    w: 3, d: 2, up: 16, tags: ['pit', 'digging'], note: '露天黏土坑；砖窑可对 kiln，但取土坑本身对不上，facility 为 null',
    draw: function (ctx, W, D) {
      var s = C.shadowEll(W / 2 + 4, D - 30, 64, 26);
      s += pit(ctx, W / 2, D - 34, 64, 28, P.clay, P.clay2, P.clay, 16);
      s += ell(W / 2 + 14, D - 28, 18, 5, P.water, 1);
      s += line(seg(W / 2 + 6, D - 28, W / 2 + 14, D - 28), 0.8, 0.6, P.water2);
      // 坑底台阶状挖痕
      s += line('M' + f(W / 2 - 40) + ' ' + f(D - 36) + 'l10 -3l10 2l8 -3', 0.9, 0.6, P.clay2);
      // 铁锹插在土里
      s += line(seg(30, D - 12, 36, D - 44), 1.8, 1, P.timber) + path(poly([[26, D - 14], [33, D - 16], [34, D - 6], [28, D - 4]]), P.iron, 0.9);
      // 独轮车
      var bx = W - 42, by = D - 8;
      s += C.wheel(bx - 12, by - 6, 6);
      s += path(poly([[bx - 18, by - 20], [bx + 10, by - 20], [bx + 4, by - 10], [bx - 14, by - 10]]), P.wood, 1.3);
      s += C.heap(ctx, bx - 4, by - 19, 12, 7, P.clay, P.clay2, P.clay, 4);
      s += line(seg(bx + 4, by - 14, bx + 22, by - 4) + seg(bx - 2, by - 10, bx + 2, by), 1.6, 1, P.dark);
      return s;
    }
  });
  /* 晒坯场：木框模具 + 一排排摊在地上的湿砖坯 + 遮雨草帘 */
  C.def({
    idKind: 'site-brickyard', name: '晒坯场', cat: 'site', resource: 'clay', facility: null,
    w: 3, d: 2, up: 30, roof: 'monopitch', tags: ['drying_floor', 'brick_mould'], note: '晒砖坯的平地 + 单坡草棚；facility 为 null（烧砖窑属 kiln，另见 west-special）',
    draw: function (ctx, W, D) {
      var s = path(poly([[4, D - 2], [W - 4, D - 2], [W - 10, D - 70], [10, D - 70]]), P.yard, 1);
      var r, k;
      for (r = 0; r < 4; r++) for (k = 0; k < 8; k++) {
        var x = 16 + k * 10 + r * 1.5, y = D - 60 + r * 13;
        s += C.block(x, y, 7, 2.5, 3.5, P.clay, P.clay2, 0.8);
      }
      // 右侧单坡草棚，下面码着半干的坯
      var hx = W - 46;
      s += shade(poly([[hx + 40, D - 6], [hx + 46, D - 8], [hx + 46, D - 46], [hx + 40, D - 46]]));
      s += C.post(hx, D - 6, 38, 3) + C.post(hx + 38, D - 6, 30, 3);
      for (k = 0; k < 3; k++) s += C.block(hx + 6, D - 8 - k * 7, 26, 3, 4, P.clay, P.clay2, 0.9);
      s += path(poly([[hx - 6, D - 46], [hx + 44, D - 38], [hx + 44, D - 34], [hx - 6, D - 42]]), P.thatch, 1.4);
      s += path(poly([[hx - 4, D - 70], [hx + 42, D - 58], [hx + 44, D - 38], [hx - 6, D - 46]]), P.thatch, 1.4);
      var th = '';
      for (k = 0; k < 10; k++) th += seg(hx - 4 + k * 5, D - 68 + k * 1.2, hx - 5 + k * 5, D - 46 + k * 0.8);
      s += line(th, 0.7, 0.6, P.thatch2);
      // 木模具与水桶
      s += path(poly([[20, D - 10], [44, D - 10], [44, D - 4], [20, D - 4]]), 'none', 1.6) + line(seg(28, D - 10, 28, D - 4) + seg(36, D - 10, 36, D - 4), 1, 1);
      s += path(poly([[52, D - 16], [62, D - 16], [61, D - 4], [53, D - 4]]), P.wood, 1.2) + ell(57, D - 16, 5, 1.6, P.water, 0.8);
      return s;
    }
  });
  /* 砖坯垛：晾干的坯错缝立码，留通风缝 */
  C.def({
    idKind: 'prop-brickstack', name: '砖坯垛', cat: 'prop', resource: 'clay', w: 1, d: 1, up: 6, tags: ['stack', 'hack'],
    draw: function (ctx, W, D) {
      var s = shade(poly([[8, D - 4], [44, D - 4], [46, D + 3], [10, D + 3]]));
      for (var r = 0; r < 5; r++) for (var k = 0; k < 4; k++) {
        var x = 7 + k * 9 + (r % 2) * 3, y = D - 4 - r * 9;
        s += C.block(x, y, 7, 3, 6, r % 2 ? P.clay2 : P.clay, P.clay2, 0.8);
      }
      return s + path(poly([[5, D - 50], [43, D - 50], [45, D - 44], [5, D - 44]]), P.thatch, 1.1);
    }
  });

  /* ---------- 盐场 salt ---------- */
  /* 熬盐棚：开敞木棚 + 石灶 + 铁盐锅 + 蒸汽 + 一旁卤水桶 */
  C.def({
    idKind: 'site-saltboil', name: '熬盐棚', cat: 'site', resource: 'salt', facility: null,
    w: 3, d: 2, up: 56, roof: 'gable_tile', tags: ['salt_pan', 'brine', 'furnace'], note: '盐井卤水在铁锅里熬干成盐（盐井式盐场）；facility 为 null',
    draw: function (ctx, W, D) {
      var s = '', x0 = 12, x1 = W - 14, yb = D - 8, ye = yb - 44, yr = ye - 34, i;
      s += shade(poly([[x1, yb], [x1 + 12, yb - 4], [x1 + 12, ye + 4], [x1, ye]]));
      s += path(poly([[x0 - 2, yb + 2], [x1 + 2, yb + 2], [x1 - 4, yb - 30], [x0 + 4, yb - 30]]), P.yard2, 1);
      for (i = 0; i < 4; i++) s += C.post(x0 + 6 + i * (x1 - x0 - 12) / 3, yb - 28, 38, 3);
      // 石灶 + 宽口铁锅 + 盐霜
      var cx = W / 2 - 6;
      s += C.block(cx - 34, yb - 8, 68, 10, 16, P.stone, P.stone2, 1.4);
      s += path(poly([[cx - 6, yb - 8], [cx + 6, yb - 8], [cx + 6, yb - 16], [cx - 6, yb - 16]]), '#2e241a', 1) + path('M' + f(cx - 4) + ' ' + f(yb - 9) + 'q4 -6 8 0z', P.fire, 0.6);
      s += ell(cx, yb - 34, 30, 7, P.iron, 1.5) + ell(cx, yb - 35, 25, 5, P.salt, 0.8);
      s += path('M' + f(cx - 8) + ' ' + f(yb - 40) + 'q-6 -10 2 -16q-4 -8 4 -12q6 6 0 12q8 6 2 16z', P.paper, 1, 0.7);
      // 前排柱 + 瓦顶
      for (i = 0; i < 4; i++) s += C.post(x0 + 2 + i * (x1 - x0 - 4) / 3, yb, 44, 4);
      s += C.roofGable(x0 - 10, x1 + 10, ye + 4, yr, 14, P.tile, P.red, 5);
      // 卤水桶 + 盐袋
      s += path(poly([[x1 + 2, yb - 18], [x1 + 14, yb - 18], [x1 + 13, yb], [x1 + 3, yb]]), P.wood, 1.2) + ell(x1 + 8, yb - 18, 6, 2, P.water, 0.8);
      s += path('M' + f(x0 - 6) + ' ' + f(yb) + 'q-2 -14 6 -16q8 2 6 16z', P.wool, 1.2);
      return s;
    }
  });
  /* 盐堆（耙成尖堆的白盐 + 木耙） */
  C.def({
    idKind: 'prop-saltheap', name: '盐堆', cat: 'prop', resource: 'salt', w: 1, d: 1, up: 0, tags: ['heap'],
    draw: function (ctx, W, D) {
      var s = C.shadowEll(27, D - 5, 20, 5);
      s += path('M4 ' + f(D - 6) + 'Q16 ' + f(D - 34) + ' 22 ' + f(D - 34) + 'Q30 ' + f(D - 34) + ' 42 ' + f(D - 6) + 'Z', P.salt, 1.4);
      s += line('M14 ' + f(D - 14) + 'l6 -10M26 ' + f(D - 12) + 'l4 -10', 0.7, 0.4, P.stone3);
      return s + line(seg(36, D - 4, 46, D - 28), 1.6, 1, P.timber) + line(seg(40, D - 30, 50, D - 26), 2, 1, P.timber);
    }
  });
  /* 盐田格：海水蒸发池（土埂围成方格，格里浅水 + 盐花）；平铺，格埂正好落在瓦片边上 */
  C.groundSet({
    idKind: 'ground-saltpan', name: '盐田格', resource: 'salt', base: P.mud, tags: ['evaporation_pond', 'water'],
    note: '平铺底纹：每张瓦片一个蒸发池，四边土埂各占 3 px，拼起来成网格；水色 #a9b8ad',
    under: function (ctx, v) {
      var tone = [P.water, P.water, '#c4cdbf', '#dfe0d4'][v - 1];   // 结晶程度不同：清水 → 结盐
      var s = C.rect(3, 3, 42, 42, tone, 0) + line('M3 3H45V45H3Z', 0.8, 0.5);
      if (v >= 3) s += line('M10 14h6M28 22h9M16 33h7M32 38h5', 1.4, 0.8, P.salt);
      return s + line(seg(0, 0, 48, 0) + seg(0, 48, 48, 48), 0.6, 0.3);
    },
    scatter: function (ctx, v) { return v <= 2 ? C.scatter(ctx, 3, 'ripple') : C.scatter(ctx, 6, 'crystal'); },
    item: function (sub, it, x, y) {
      if (x < 6 || x > 40 || y < 6 || y > 42) return '';
      return it.t === 'ripple' ? line(seg(x, y, x + 7, y), 0.8, 0.6, P.water2) : C.rect(x, y, 2.4, 1.6, P.salt, 0);
    }
  });

  /* ---------- 硫磺坑 sulfur ---------- */
  C.def({
    idKind: 'site-sulfurpit', name: '硫磺喷气坑', cat: 'site', resource: 'sulfur', facility: null,
    w: 3, d: 2, up: 60, tags: ['fumarole', 'yellow_crust'], note: '火山喷气孔周围结黄色硫华，人工凿取；facility 为 null',
    draw: function (ctx, W, D) {
      var s = pit(ctx, W / 2, D - 34, 60, 26, P.sulfur, P.sulfur2, '#8f8240', 14), i;
      for (i = 0; i < 3; i++) {
        var vx = W / 2 - 30 + i * 30, vy = D - 30 - (i % 2) * 6;
        s += ell(vx, vy, 6, 2.4, '#2e241a', 1);
        s += path('M' + f(vx - 4) + ' ' + f(vy - 2) + 'q-8 -14 2 -22q-6 -12 4 -20q10 8 2 18q10 8 2 24z', P.paper, 1, 0.65);
      }
      s += line('M' + f(W / 2 - 56) + ' ' + f(D - 30) + 'l8 -6l6 4M' + f(W / 2 + 36) + ' ' + f(D - 40) + 'l10 4', 1, 0.7, P.sulfur2);
      // 坑沿凿取工具 + 装硫磺的筐
      s += line(seg(18, D - 6, 26, D - 30), 1.8, 1, P.timber) + path(poly([[22, D - 32], [32, D - 30], [30, D - 27]]), P.iron, 0.8);
      s += path(poly([[W - 34, D - 22], [W - 14, D - 22], [W - 17, D - 4], [W - 31, D - 4]]), P.wood, 1.2);
      return s + C.heap(ctx, W - 24, D - 21, 10, 6, P.sulfur2, P.sulfur, P.sulfur2, 4);
    }
  });
  C.def({
    idKind: 'prop-sulfurlumps', name: '硫磺块堆', cat: 'prop', resource: 'sulfur', w: 1, d: 1, up: 0, tags: ['heap'],
    draw: function (ctx, W, D) { return C.heap(ctx, 24, D - 6, 19, 17, P.sulfur2, P.sulfur, '#e6d478', 12); }
  });
  C.groundSet({
    idKind: 'ground-sulfurcrust', name: '硫华地', resource: 'sulfur', base: '#b8ad82', tags: ['volcanic'],
    scatter: function (ctx, v) { return C.scatter(ctx, 8 + v, 'crust'); },
    item: function (sub, it, x, y) {
      return it.k < 0.35 ? C.ell(x, y, 4, 1.8, P.sulfur, 0, 0.85) : C.rect(x, y, 2, 1.4, it.k < 0.7 ? P.sulfur2 : P.stone3, 0, 0.9);
    }
  });

  /* ---------- 宝石 gems / 琥珀 amber：小型手工矿坑 + 筛矿台 ---------- */
  /** 手工小坑：坑口木辘轳 + 梯子 + 篮子 */
  function handPit(ctx, W, D, ore, ore2, label) {
    var s = path(poly([[4, D - 2], [W - 4, D - 2], [W - 10, D - 66], [10, D - 66]]), P.yard2, 1, 0.9);
    s += pit(ctx, 56, D - 34, 40, 20, P.soil, P.soil2, '#5e4a33', 14);
    // 木辘轳：两根叉柱 + 横轴 + 摇把 + 吊绳篮
    s += line(seg(30, D - 22, 34, D - 58) + seg(82, D - 22, 78, D - 58), 2.6, 1, P.dark);
    s += C.logSide(32, 80, D - 56, 3.5) + line('M80 ' + f(D - 56) + 'l8 0l0 8', 1.6, 1, P.iron);
    s += line(seg(56, D - 53, 56, D - 34), 0.9, 1);
    s += path(poly([[50, D - 34], [62, D - 34], [60, D - 26], [52, D - 26]]), P.wood, 1);
    // 梯子伸出坑口
    s += line(seg(66, D - 30, 72, D - 50) + seg(72, D - 28, 78, D - 48), 1.4, 1, P.timber);
    s += line(seg(67.5, D - 35, 73.5, D - 33) + seg(69, D - 40, 75, D - 38) + seg(70.5, D - 45, 76.5, D - 43), 1, 1, P.timber);
    // 挖出的土堆，里面闪着矿物
    s += C.heap(ctx, W - 40, D - 8, 26, 16, P.soil, P.soil2, P.soil2, 8);
    for (var i = 0; i < 6; i++) {
      var x = W - 58 + i * 7, y = D - 12 - (i % 3) * 4;
      s += path(poly([[x, y], [x + 2.5, y - 4], [x + 5, y], [x + 2.5, y + 2]]), i % 2 ? ore : ore2, 0.7);
    }
    return s;
  }
  /** 筛矿台：木架 + 斜放的筛子 + 盆 */
  function sieveTable(ctx, W, D, ore, ore2, water) {
    var s = shade(poly([[6, D - 4], [46, D - 4], [47, D + 2], [7, D + 2]]));
    s += C.post(8, D - 4, 22, 3) + C.post(40, D - 4, 22, 3);
    s += path(poly([[4, D - 28], [44, D - 28], [44, D - 22], [4, D - 22]]), P.wood, 1.2);
    s += ell(24, D - 32, 14, 5, P.thatch2, 1.2) + ell(24, D - 32, 10, 3.2, P.soil, 0);
    var g = '';
    for (var i = -2; i <= 2; i++) g += seg(24 + i * 4, D - 35, 24 + i * 4, D - 29);
    s += line(g, 0.6, 0.6);
    s += path(poly([[20, D - 33], [22, D - 36], [24, D - 33], [22, D - 31]]), ore, 0.6) + path(poly([[27, D - 32], [29, D - 35], [31, D - 32], [29, D - 30]]), ore2, 0.6);
    if (water) s += ell(24, D - 8, 12, 4, P.iron, 1.2) + ell(24, D - 8.5, 8, 2.4, P.water, 0);
    return s;
  }
  C.def({
    idKind: 'site-gempit', name: '宝石手工矿坑', cat: 'site', resource: 'gems', facility: 'mine_head',
    w: 3, d: 2, up: 26, tags: ['hand_pit', 'windlass'], note: '冲积层里挖宝石的小竖坑 + 木辘轳；规模小，仍记 mine_head',
    draw: function (ctx, W, D) { return handPit(ctx, W, D, P.gem, P.gem2); }
  });
  C.def({
    idKind: 'prop-gemsieve', name: '宝石筛矿台', cat: 'prop', resource: 'gems', w: 1, d: 1, up: 0, tags: ['sieve', 'washing'],
    draw: function (ctx, W, D) { return sieveTable(ctx, W, D, P.gem, P.gem2, true); }
  });
  C.def({
    idKind: 'site-amberpit', name: '琥珀挖掘坑', cat: 'site', resource: 'amber', facility: null,
    w: 3, d: 2, up: 26, tags: ['hand_pit', 'resin'], note: '琥珀产于泥炭/砂层，人工挖掘；坑旁倒着一截古木（树脂来源），facility 为 null',
    draw: function (ctx, W, D) {
      var s = handPit(ctx, W, D, P.amber, '#b8742e');
      s += C.logSide(10, 40, D - 10, 5) + path('M28 ' + f(D - 15) + 'q3 -4 6 0q-3 3 -6 0z', P.amber, 0.7);
      return s;
    }
  });
  C.def({
    idKind: 'prop-ambersieve', name: '琥珀筛选台', cat: 'prop', resource: 'amber', w: 1, d: 1, up: 0, tags: ['sieve'],
    draw: function (ctx, W, D) {
      var s = sieveTable(ctx, W, D, P.amber, '#b8742e', false);
      return s + path('M12 ' + f(D - 4) + 'q-2 -8 6 -9q8 1 6 9z', P.amber, 1.1, 0.95) + path('M30 ' + f(D - 4) + 'q-1 -6 5 -6q6 0 5 6z', '#b8742e', 1);
    }
  });
})(typeof window !== 'undefined' ? window : this);
