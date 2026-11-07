/*
 * 织梦 · 矮人特殊建筑 A 组：铁匠铺 ×2、石拱市场 + 摊位、氏族议事厅（美术样板，尚未接入游戏）
 * 局部坐标：x 0..w*48，y = 0 为占地前沿，向上为负。每项 { id, name, facility, kind, fp, roof, tags, note, draw(ctx) }。
 * 浏览器挂 window.TownArtWD_civicA；Node 用 module.exports。依赖 core.js、parts.js、houses-a.js、houses-b.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWD_core;
  var K = isNode ? require('./parts.js') : root.TownArtWD_parts;
  var HA = isNode ? require('./houses-a.js') : root.TownArtWD_housesA;
  var HB = isNode ? require('./houses-b.js') : root.TownArtWD_housesB;
  var P = C.PAL, f = C.f, WATER = '#8fa7a8', WATER2 = '#b4c6c2', LEATHER = '#7a4a32';

  /** 铁砧：树桩墩 + 砧身（砧面、腰、砧角），sc 缩放 */
  function anvil(ctx, cx, yb, sc) {
    sc = sc || 1;
    var s = '', y = yb - 7 * sc;
    s += C.path(C.poly([[cx - 5 * sc, yb], [cx - 4 * sc, y], [cx + 4 * sc, y], [cx + 5 * sc, yb]]), P.timber, 1.1);
    s += C.line('M' + f(cx - 3 * sc) + ' ' + f(yb - 2.5 * sc) + 'h' + f(6 * sc) + 'M' + f(cx - 2 * sc) + ' ' + f(yb - 5 * sc) + 'h' + f(4 * sc), 0.6, 0.5);
    var d = C.poly([[cx - 3 * sc, y], [cx - 2 * sc, y - 3 * sc], [cx - 6 * sc, y - 4.5 * sc], [cx - 7 * sc, y - 7 * sc], [cx + 5 * sc, y - 7 * sc],
      [cx + 12 * sc, y - 6.2 * sc], [cx + 5 * sc, y - 4.2 * sc], [cx + 2.5 * sc, y - 3 * sc], [cx + 3.5 * sc, y]]);
    s += C.face(ctx, d, P.iron, C.rect(cx - 7 * sc, y - 7 * sc, 12 * sc, 1.4 * sc, '#8a857c', 0), 1.3);
    ctx.top(y - 7 * sc);
    return s;
  }
  /** 熔炉口：石拱圈 + 拱心石，洞内黑底上跳动的火舌（两层平涂） */
  function firemouth(ctx, cx, yb, w, h) {
    var x = cx - w / 2, r = w / 2, y = yb - h, fr = 5, i;
    function arch(a, rr) { return 'M' + f(cx - rr) + ' ' + f(yb) + 'V' + f(y + r) + 'A' + f(rr) + ' ' + f(rr) + ' 0 0 1 ' + f(cx + rr) + ' ' + f(y + r) + 'V' + f(yb) + 'Z'; }
    var d = arch(0, r), s = C.path(arch(0, r + fr), P.granite3, 1.4), vs = '';
    for (i = 1; i < 6; i++) {
      var an = Math.PI * i / 6;
      vs += 'M' + f(cx - Math.cos(an) * r) + ' ' + f(y + r - Math.sin(an) * r) + 'L' + f(cx - Math.cos(an) * (r + fr)) + ' ' + f(y + r - Math.sin(an) * (r + fr));
    }
    s += C.line(vs, 0.8, 0.7);
    function tongues(amp0, amp1) {
      var n = Math.max(3, Math.round(w / 4)), st = w / n, t = 'M' + f(x) + ' ' + f(yb);
      for (var k = 0; k < n; k++) t += 'L' + f(x + st * (k + 0.5)) + ' ' + f(yb - h * ctx.rnd(amp0, amp1)) + 'L' + f(x + st * (k + 1)) + ' ' + f(yb - h * amp0 * 0.5);
      return t + 'V' + f(yb) + 'Z';
    }
    var inner = C.path(tongues(0.4, 0.68), P.fire, 0) + C.path(tongues(0.18, 0.36), P.ember, 0) + C.rect(x, y, w, 2.5, P.shadow, 0, 0.3);
    s += C.path(d, P.hole, 0) + C.clipped(ctx, d, inner) + C.path(d, 'none', 1.5);
    s += C.rect(cx - 3, y - fr - 1, 6, fr + 3, P.granite2, 1.1);
    ctx.top(y - fr - 1);
    return s;
  }
  /** 皮风箱：底板 + 褶皱皮囊 + 上板 + 铜嘴（朝左） */
  function bellows(ctx, x, yb, w) {
    w = w || 14;
    var h = 9, s = '', z = 'M' + f(x + 2) + ' ' + f(yb - 3);
    for (var k = 1; k <= 5; k++) z += 'L' + f(x + 2 + (w - 2) * k / 5) + ' ' + f(yb - 3 - (k % 2 ? h - 4 : 0));
    var leather = C.poly([[x + 1, yb - 3], [x + w, yb - 3], [x + w, yb - h - 1], [x + 1, yb - h + 2]]);
    s += C.path(C.poly([[x, yb - 5], [x - 5, yb - 6.2], [x - 5, yb - 4.4], [x, yb - 3.4]]), P.copper, 0.8);
    s += C.rect(x, yb - 3, w, 3, P.wood, 1);
    s += C.face(ctx, leather, LEATHER, C.line(z, 0.8, 0.6), 1);
    s += C.path(C.poly([[x, yb - h + 1], [x + w, yb - h - 2.5], [x + w, yb - h - 0.5], [x, yb - h + 3]]), P.wood, 1);
    s += C.line('M' + f(x + w) + ' ' + f(yb - h - 1.5) + 'l5 -3', 1.6, 1, P.timber);
    ctx.top(yb - h - 5);
    return s;
  }
  /** 水轮：木轮辋 + 辐条 + 外挑叶板，铜轮毂 */
  function wheel(ctx, cx, cy, r, n) {
    n = n || 10;
    var s = '', sp = '', pd = '', i;
    for (i = 0; i < n; i++) {
      var a = Math.PI * 2 * i / n + 0.15, ca = Math.cos(a), sa = Math.sin(a), px = cx + ca * r, py = cy + sa * r, L = 4.5, Wd = 1.8;
      sp += 'M' + f(cx) + ' ' + f(cy) + 'L' + f(px) + ' ' + f(py);
      pd += C.path(C.poly([[px - sa * Wd, py + ca * Wd], [px + sa * Wd, py - ca * Wd], [px + sa * Wd + ca * L, py - ca * Wd + sa * L], [px - sa * Wd + ca * L, py + ca * Wd + sa * L]]), P.wood, 0.8);
    }
    s += pd + C.line(sp, 2, 1, P.timber) + C.line(sp, 0.5, 0.6);
    s += '<circle cx="' + f(cx) + '" cy="' + f(cy) + '" r="' + f(r) + '" fill="none" stroke="' + P.timber + '" stroke-width="3"/>';
    s += C.circle(cx, cy, r + 1.5, 'none', 1) + C.circle(cx, cy, r - 1.5, 'none', 0.8);
    s += C.circle(cx, cy, 3, P.copper, 1) + C.circle(cx, cy, 1, P.iron, 0);
    ctx.top(cy - r - 4.5);
    return s;
  }
  /** 淬火石槽：石槽 + 水面 */
  function trough(ctx, x0, x1, yb) {
    return C.rect(x0, yb - 6, x1 - x0, 6, P.granite2, 1.2) + C.rect(x0 + 1.5, yb - 6, x1 - x0 - 3, 2, WATER, 0.7) +
      C.line('M' + f(x0 + 3) + ' ' + f(yb - 5) + 'h3M' + f(x1 - 7) + ' ' + f(yb - 5) + 'h2', 0.6, 0.6, WATER2);
  }

  var S = [];

  /** 水力锻锤：A 字木架（立柱 px，底 yb，轴高 py）+ 锤杆 + 铁锤头（落在 hx,hy）+ 尾端凸轮 */
  function tripHammer(ctx, px, yb, py, hx, hy) {
    var s = '';
    s += C.path(C.poly([[px - 7, yb], [px - 1.5, py - 3], [px + 1.5, py - 3], [px + 7, yb], [px + 4, yb], [px, py + 4], [px - 4, yb]]), P.timber, 1.1);
    s += C.rect(px - 9, yb - 2.5, 18, 2.5, P.dark, 0.9);
    // 锤杆：从尾端（px+9）过轴到锤头
    s += C.line('M' + f(px + 9) + ' ' + f(py + 3) + 'L' + f(hx) + ' ' + f(hy - 2), 3.6, 1, P.dark) + C.line('M' + f(px + 9) + ' ' + f(py + 3) + 'L' + f(hx) + ' ' + f(hy - 2), 0.6, 0.6);
    s += C.path(C.poly([[hx - 5, hy - 5], [hx + 4, hy - 5], [hx + 5, hy + 4], [hx - 6, hy + 4]]), P.iron, 1.2) + C.rect(hx - 6, hy - 1.5, 11, 1.6, P.copper, 0);
    s += C.circle(px, py, 2.2, P.copper, 0.9) + C.circle(px + 9, py + 5, 2.6, P.iron, 0.8);
    ctx.top(py - 5);
    return s;
  }
  /** 木水槽：从 (x0,y0) 斜向 (x1,y1) 的木导水槽，槽口一道水落下到 yw */
  function flume(ctx, x0, y0, x1, y1, yw) {
    var s = C.path(C.poly([[x0, y0 - 3], [x1, y1 - 3], [x1, y1 + 2], [x0, y0 + 2]]), P.wood, 1.1);
    s += C.line('M' + f(x0) + ' ' + f(y0 - 1.5) + 'L' + f(x1) + ' ' + f(y1 - 1.5), 1.4, 1, WATER);
    s += C.line('M' + f((x0 * 3 + x1) / 4) + ' ' + f((y0 * 3 + y1) / 4 + 2) + 'v5M' + f((x0 + x1) / 2) + ' ' + f((y0 + y1) / 2 + 2) + 'v5', 1.6, 1, P.timber);
    s += C.path(C.poly([[x1 - 1, y1 + 2], [x1 + 3, y1 + 2], [x1 + 4, yw], [x1, yw]]), WATER, 0.7, 0.85) +
      C.line('M' + f(x1 + 1) + ' ' + f(y1 + 5) + 'v' + f(yw - y1 - 8), 0.6, 0.7, WATER2);
    ctx.top(Math.min(y0, y1) - 3);
    return s;
  }
  /** 敞棚：两根石柱 + 低坡石板顶（铁匠铺锻锤棚、市场摊位共用） */
  function shed(ctx, x0, x1, h, dg, rise) {
    var s = K.pillar(ctx, x0 + 4, 0, 7, h) + K.pillar(ctx, x1 - 4, 0, 7, h);
    return s + K.slabRoof(ctx, x0, x1, -h, dg, rise, { ov: 3 }).svg;
  }

  // forge-01：3×2 半嵌山熔炉坊。左半截埋进岩坡，石砌炉房 + 大拱炉口 + 三根烟囱；右侧敞棚里水轮带动锻锤打巨砧
  S.push({
    id: 'west-dwarf-forge-01', name: '矮人铁匠铺（嵌山熔炉坊）', facility: 'forge', kind: 'forge_mountain', fp: [3, 2], variant: 1,
    roof: 'flat_mud', tags: ['furnace', 'anvil', 'trip_hammer', 'water_wheel', 'embedded', 'smoke'],
    note: '炉房石板平顶（最近 RoofId flat_mud）；水轮经凸轮驱动锻锤',
    draw: function (ctx) {
      var s = '';
      s += C.groundShadow(6, 142, 0, -70);
      s += C.rockSlope(ctx, 0, 92, -30, 74, { lo: 0.55, moss: 3 });
      s += C.blocks(ctx, 6, 82, 0, 44, { minW: 16, maxW: 28 }) + C.slabTop(ctx, 6, 82, -44, 26);
      s += K.chimney(ctx, 22, -58, 13, 40, { fire: true, smoke: 4, smokeScale: 1.3 });
      s += K.chimney(ctx, 46, -58, 10, 30, { cap: 'ring', smoke: 3 });
      s += K.chimney(ctx, 68, -58, 8, 22, { cap: 'copper', smoke: 2 });
      s += C.runes(ctx, 12, 76, -38, 6);
      s += firemouth(ctx, 40, 0, 24, 28);
      s += bellows(ctx, 56, 0, 14) + C.win(ctx, 72, -26, 6, 7, 'fire') + C.win(ctx, 13, -26, 6, 7, 'fire');
      s += anvil(ctx, 18, 0, 1.1) + trough(ctx, 64, 80, 0);
      // 锻锤棚
      s += shed(ctx, 86, 140, 34, 30, 6);
      s += flume(ctx, 138, -66, 126, -54, -40);
      s += wheel(ctx, 128, -22, 15, 10);
      s += C.line('M128 -22H104', 2.2, 1, P.iron);
      s += anvil(ctx, 100, 0, 1.4) + tripHammer(ctx, 112, 0, -24, 101, -16);
      s += C.rect(118, -6, 22, 6, P.granite2, 1.1) + C.rect(119.5, -6, 19, 2, WATER, 0.7);
      return s;
    }
  });

  // forge-02：2×2 圆鼓高炉。花岗岩圆鼓炉身 + 收分石烟囱 + 铜箍；右侧小敞棚里锻锤，前角水轮
  S.push({
    id: 'west-dwarf-forge-02', name: '矮人铁匠铺（圆鼓高炉）', facility: 'forge', kind: 'forge_furnace_tower', fp: [2, 2], variant: 2,
    roof: 'none', tags: ['furnace', 'anvil', 'trip_hammer', 'water_wheel', 'round_tower', 'smoke'],
    note: '炉身为圆鼓石塔，顶为收分石烟囱，RoofId 无对应记 none；棚为石板低坡',
    draw: function (ctx) {
      var s = '', D, cx = 28, rx = 22, ry = 8;
      s += C.groundShadow(6, 94, 0, -70);
      s += C.blocks(ctx, 40, 92, -40, 22) + C.slabTop(ctx, 40, 92, -62, 22);
      D = HB.drum(ctx, cx, -ry - 1, rx, ry, 62);
      s += D.svg + C.ellipse(cx, D.yt, rx, ry, P.granite3, 1.5);
      // 收分烟囱
      var st = C.poly([[cx - 13, D.yt + 2], [cx - 7, D.yt - 40], [cx + 7, D.yt - 40], [cx + 13, D.yt + 2]]);
      s += C.face(ctx, st, P.granite2, C.line('M' + f(cx - 12) + ' ' + f(D.yt - 8) + 'H' + f(cx + 12) + 'M' + f(cx - 10) + ' ' + f(D.yt - 18) + 'H' + f(cx + 10) +
        'M' + f(cx - 9) + ' ' + f(D.yt - 28) + 'H' + f(cx + 9), 0.8, 0.55) + C.rect(cx + 3, D.yt - 40, 10, 44, P.shadow, 0, 0.16), 1.6);
      s += C.rect(cx - 9, D.yt - 44, 18, 4, P.granite3, 1.2) + C.rect(cx - 6, D.yt - 45.5, 12, 1.6, P.fire, 0.7);
      s += K.smoke(ctx, cx - 3, D.yt - 46, 4, 1.4);
      [-20, -44].forEach(function (y) { s += C.rect(cx - rx - 0.5, y - 1.4, 2 * rx + 1, 2.8, P.copper, 0.9) + C.rivets(cx - rx + 3, cx + rx - 3, y, 4, 0.55); });
      s += firemouth(ctx, cx, -3, 18, 22) + bellows(ctx, cx + 12, -1, 11);
      // 锻锤棚 + 水轮
      s += shed(ctx, 50, 92, 30, 20, 5);
      s += anvil(ctx, 62, 0, 1.25) + tripHammer(ctx, 74, 0, -21, 63, -14);
      s += wheel(ctx, 81, -17, 10.5, 9) + C.line('M81 -17H66', 2, 1, P.iron);
      s += flume(ctx, 90, -50, 84, -40, -30);
      s += trough(ctx, 4, 16, 0);
      return s;
    }
  });

  /** 半圆石拱（敞厅开间）：x0..x1，底 yb，拱脚高 hs；洞内暗色，拱石放射缝 */
  function bay(ctx, x0, x1, yb, hs, fill) {
    var w = x1 - x0, r = w / 2, cx = x0 + r, ys = yb - hs, vs = '';
    var d = 'M' + f(x0) + ' ' + f(yb) + 'V' + f(ys) + 'A' + f(r) + ' ' + f(r) + ' 0 0 1 ' + f(x1) + ' ' + f(ys) + 'V' + f(yb) + 'Z';
    for (var i = 1; i < 6; i++) {
      var an = Math.PI * i / 6;
      vs += 'M' + f(cx - Math.cos(an) * r) + ' ' + f(ys - Math.sin(an) * r) + 'L' + f(cx - Math.cos(an) * (r + 4)) + ' ' + f(ys - Math.sin(an) * (r + 4));
    }
    return C.path(d, fill || P.deep2, 1.4) + C.line(vs, 0.8, 0.65) + C.rect(cx - 2.5, ys - r - 4.5, 5, 5, P.granite3, 1);
  }
  /** 摊位货物：一排木箱 / 铜锅 / 矿石 / 酒桶 */
  function wares(ctx, x0, x1, yb) {
    var s = '', x = x0;
    while (x < x1 - 6) {
      var k = ctx.int(0, 3);
      if (k === 0) s += C.rect(x, yb - 6, 7, 6, P.wood, 0.9) + C.line('M' + f(x) + ' ' + f(yb - 3) + 'h7', 0.6, 0.6);
      else if (k === 1) s += C.path('M' + f(x) + ' ' + f(yb - 4) + 'q3.5 5 7 0Z', P.copper, 0.9) + C.line('M' + f(x + 1) + ' ' + f(yb - 4) + 'h5', 1, 1, P.copper2);
      else if (k === 2) s += C.path(C.poly([[x, yb], [x + 1, yb - 4], [x + 4, yb - 5], [x + 7, yb - 2], [x + 7, yb]]), ctx.pick([P.deep, P.verd, P.copper]), 0.8);
      else s += C.path('M' + f(x + 0.5) + ' ' + f(yb) + 'q-1 -3.5 0 -7h6q1 3.5 0 7Z', P.timber, 0.9) + C.line('M' + f(x) + ' ' + f(yb - 3.5) + 'h7', 0.8, 1, P.iron);
      x += 8.5;
    }
    return s;
  }

  // market_hall：3×2 石拱敞厅。三开间半圆拱 + 粗方柱，低坡石板顶，屋脊铜钟亭；拱下货摊
  S.push({
    id: 'west-dwarf-market-01', name: '矮人石拱市场厅', facility: 'market_hall', kind: 'market_arcade', fp: [3, 2], variant: 1,
    roof: 'gable_tile', tags: ['arcade', 'covered_market', 'bell'], note: '石板低坡顶，最近 RoofId 为 gable_tile（石板代瓦）',
    draw: function (ctx) {
      var s = '', x0 = 4, x1 = 140, h = 40;
      s += C.groundShadow(x0, x1, 0, -64);
      s += C.blocks(ctx, x0, x1, 0, h, { minW: 16, maxW: 30 });
      var bx = [10, 52, 94], bw = 40;
      bx.forEach(function (x) {
        s += bay(ctx, x + 3, x + bw - 3, 0, 18);
        s += C.rect(x + 5, -8, bw - 10, 8, P.wood, 1) + wares(ctx, x + 7, x + bw - 6, -8);
      });
      [8, 50, 92, 134].forEach(function (x) { s += K.pillar(ctx, x + 1, 0, 8, h); });
      s += C.runes(ctx, x0 + 4, x1 - 4, -h + 5, 5);
      var R = K.slabRoof(ctx, x0, x1, -h, 48, 10, { ov: 4, rivet: true });
      s += R.svg;
      // 屋脊钟亭：两根铜柱 + 小石板顶 + 铜钟
      var cx = 72, yr = R.yR;
      s += C.rect(cx - 9, yr - 18, 2.6, 18, P.copper, 0.9) + C.rect(cx + 6.4, yr - 18, 2.6, 18, P.copper, 0.9);
      s += C.path('M' + f(cx - 4.5) + ' ' + f(yr - 3) + 'q0 -10 4.5 -10q4.5 0 4.5 10Z', P.copper, 1.1) + C.circle(cx, yr - 2, 1.4, P.iron, 0.6);
      s += C.path(C.poly([[cx - 13, yr - 18], [cx, yr - 26], [cx + 13, yr - 18]]), P.verd, 1.3);
      ctx.top(yr - 26);
      s += K.chimney(ctx, 24, yr + 6, 6, 10, { smoke: 2 });
      return s;
    }
  });

  // 摊位：1×1 露天货摊。木台 + 两根木杆撑铜绿条纹布篷，台上货物
  [1, 2].forEach(function (n) {
    S.push({
      id: 'west-dwarf-stall-0' + n, name: '矮人露天货摊·' + n, facility: 'market_hall', category: 'prop', kind: 'market_stall', fp: [1, 1], variant: n,
      roof: 'monopitch', tags: ['open_air', 'stall'], note: '露天菜市场摊位：布篷单坡，最近 RoofId 为 monopitch',
      draw: function (ctx) {
        var s = '', awn = n === 1 ? P.verd : P.red, awn2 = n === 1 ? P.verd2 : P.wash;
        s += C.groundShadow(6, 42, 0, -22);
        s += C.line('M9 0V-26M39 0V-26', 2.2, 1, P.timber) + C.line('M9 -18V-30M39 -18V-30', 1.6, 1, P.dark);
        s += C.rect(5, -11, 38, 3.5, P.wood, 1.1) + C.rect(7, -7.5, 34, 7.5, P.timber, 1) + C.line('M7 -4h34', 0.6, 0.5);
        s += wares(ctx, 8, 42, -11);
        var d = C.poly([[3, -26], [45, -26], [42, -38], [6, -38]]), st = '';
        for (var x = 6; x < 46; x += 8) st += C.rect(x, -40, 4, 16, awn2, 0);
        s += C.face(ctx, d, awn, st, 1.4);
        var hem = 'M3 -26';
        for (var k = 0; k < 7; k++) hem += 'q3 3.5 6 0';
        s += C.path(hem + 'Z', awn, 1.1);
        if (n === 2) s += C.circle(24, -32, 3, P.copper, 1) + C.line('M22 -32h4', 0.8);
        ctx.top(-40);
        return s;
      }
    });
  });

  // town_hall：4×3 氏族议事厅。背靠山体，巨石阶梯基座，正中巨大石门（铜门板），两侧四根符文巨柱，山墙三角楣 + 氏族铜纹章
  S.push({
    id: 'west-dwarf-town-hall-01', name: '矮人氏族议事厅', facility: 'town_hall', kind: 'clan_hall', fp: [4, 3], variant: 1,
    roof: 'gable_tile', tags: ['clan_hall', 'great_gate', 'rune_pillars', 'embedded', 'steps'],
    note: '后半截嵌入岩坡；前为石板低坡顶 + 三角楣，最近 RoofId 为 gable_tile',
    draw: function (ctx) {
      var s = '', x0 = 10, x1 = 182, cx = 96, h = 58, base = 10;
      s += C.groundShadow(x0, x1, 0, -110);
      s += C.rockSlope(ctx, 0, 192, -60, 96, { lo: 0.55, moss: 4 });
      // 阶梯基座
      for (var k = 0; k < 3; k++) s += C.rect(x0 - 6 + k * 4, -(k + 1) * 3.4, x1 - x0 + 12 - k * 8, 3.4, k % 2 ? P.granite2 : P.granite3, 1.1);
      s += C.blocks(ctx, x0 + 6, x1 - 6, -base, h, { minW: 18, maxW: 32, course: 11 });
      s += C.runes(ctx, x0 + 10, x1 - 10, -base - h + 7, 7);
      // 巨大石门
      s += C.door(ctx, cx, -base, 34, 42, 'trap', { fill: P.copper, band: P.iron, bands: 3, frame: 7, ring: P.granite2, step: false });
      s += C.path('M' + f(cx - 6) + ' ' + f(-base - 30) + 'l6 -6l6 6l-6 6Z', P.verd, 1.1) + C.circle(cx, -base - 30, 1.6, P.ember, 0.6);
      // 符文巨柱：门两侧各两根
      [cx - 62, cx - 34, cx + 34, cx + 62].forEach(function (x) { s += K.pillar(ctx, x, -base, 12, h + 4, { rune: true, band: true }); });
      // 窄窗
      [cx - 48, cx + 48].forEach(function (x) { s += C.win(ctx, x - 3, -base - 40, 6, 14, 'slit') + C.win(ctx, x - 3.5, -base - 20, 7, 7, 'fire'); });
      // 三角楣 + 纹章
      var yt = -base - h - 4, R = K.slabRoof(ctx, x0, x1, yt, 64, 8, { ov: 4, rivet: true });
      s += R.svg;
      var ped = C.poly([[cx - 46, yt + 1], [cx, yt - 28], [cx + 46, yt + 1]]);
      s += C.face(ctx, ped, P.granite3, C.line('M' + f(cx - 38) + ' ' + f(yt - 4) + 'H' + f(cx + 38), 0.8, 0.5) +
        C.path(C.poly([[cx, yt - 28], [cx + 46, yt + 1], [cx + 30, yt + 1]]), P.shadow, 0, 0.14), 1.7);
      s += K.gear(ctx, cx, yt - 10, 7, 10, { fill: P.copper }) + C.path('M' + f(cx - 3) + ' ' + f(yt - 13) + 'l3 -3l3 3v4h-6Z', P.iron, 0.8);
      s += K.chimney(ctx, x0 + 22, R.yR + 6, 9, 18, { cap: 'ring', smoke: 3 }) + K.chimney(ctx, x1 - 22, R.yR + 6, 9, 18, { cap: 'ring', smoke: 3 });
      ctx.top(yt - 28);
      return s;
    }
  });

  var API = { S: S, anvil: anvil, firemouth: firemouth, bellows: bellows, wheel: wheel, trough: trough, shed: shed, bay: bay, wares: wares };
  root.TownArtWD_civicA = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
