/*
 * 织梦 · 城镇西式精灵族特殊建筑（一）：铁匠铺 forge（月光熔炉、银砧）、市场 market_hall（藤棚摊位）+ 摊位 prop、
 * 行政厅 town_hall（议事古树殿）（美术样板，尚未接入游戏）
 * 局部坐标：y = 0 为占地前沿，向上为负。
 * 浏览器挂 window.TownArtWE_specialA；Node 用 module.exports。依赖 core.js、parts.js、forms.js、houses-a.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWE_core;
  var Q = isNode ? require('./parts.js') : root.TownArtWE_parts;
  var F = isNode ? require('./forms.js') : root.TownArtWE_forms;
  var HA = isNode ? require('./houses-a.js') : root.TownArtWE_housesA;
  var P = C.P, f = C.f, line = C.line, path = C.path, rect = C.rect;
  var EMBER = '#3b2d1f';

  // ---------------- 共用小件 ----------------
  /** 银白木立柱（带叶形柱头）：x，底 yb，顶 yt */
  function post(x, yb, yt, w) {
    w = w || 2.6;
    var d = 'M' + f(x) + ' ' + f(yb) + 'V' + f(yt);
    return line(d, w + 1.4, 1) + line(d, w, 1, P.silver) + Q.leaf(x, yt + 1, 4, -Math.PI / 2 - 0.8, P.leaf, 0.5) + Q.leaf(x, yt + 1, 4, -Math.PI / 2 + 0.8, P.moss, 0.5);
  }
  /** 挂旗：叶形长幡，x 中心，y 顶，h 长；月牙徽 */
  function banner(x, y, h, color) {
    var w = 4.2, d = 'M' + f(x - w) + ' ' + f(y) + 'H' + f(x + w) + 'V' + f(y + h * 0.75) + 'Q' + f(x + w * 0.4) + ' ' + f(y + h * 0.8) + ' ' + f(x) + ' ' + f(y + h) +
      'Q' + f(x - w * 0.4) + ' ' + f(y + h * 0.8) + ' ' + f(x - w) + ' ' + f(y + h * 0.75) + 'Z';
    var cy = y + h * 0.38;
    return line('M' + f(x - w - 1.5) + ' ' + f(y) + 'H' + f(x + w + 1.5), 1.6) + path(d, color || P.leaf, 1) +
      path('M' + f(x + 1.4) + ' ' + f(cy - 2.6) + 'A2.6 2.6 0 1 0 ' + f(x + 1.4) + ' ' + f(cy + 2.6) + 'A2 2 0 1 1 ' + f(x + 1.4) + ' ' + f(cy - 2.6) + 'Z', P.silver, 0.5);
  }
  /** 一缕银烟（木刻卷线） */
  function smoke(ctx, x, y) {
    var d = 'M' + f(x) + ' ' + f(y) + 'c-3 -4 3 -6 0 -10c-3 -4 4 -6 1 -10c-2 -3 2 -5 0 -7';
    ctx.top(y - 28);
    return line(d, 2.4, 0.35) + line(d, 1.2, 1, P.silver);
  }

  // ---------------- 铁匠铺：月光熔炉 + 银砧 ----------------
  /** 月光石穹顶熔炉：cx，地面 yb，半宽 r，高 h；炉口淡银火苗 */
  function furnace(ctx, cx, yb, r, h) {
    var d = 'M' + f(cx - r) + ' ' + f(yb) + 'C' + f(cx - r) + ' ' + f(yb - h * 0.78) + ' ' + f(cx - r * 0.55) + ' ' + f(yb - h) + ' ' + f(cx) + ' ' + f(yb - h) +
      'C' + f(cx + r * 0.55) + ' ' + f(yb - h) + ' ' + f(cx + r) + ' ' + f(yb - h * 0.78) + ' ' + f(cx + r) + ' ' + f(yb) + 'Z';
    var s = C.ellShadow(cx + 4, yb - 1, r + 2, 3);
    // 炉顶烟道（先画，炉身压住根部）
    s += C.face(ctx, C.rectD(cx - 3.5, yb - h - 9, 7, 12), P.moon2, '', 1.3) + C.ellipse(cx, yb - h - 9, 3.5, 1.4, EMBER, 1);
    var tex = F.wallTex(ctx, 'stone', cx - r, yb - h, 2 * r, h) + path('M' + f(cx + r * 0.35) + ' ' + f(yb - h - 2) + 'H' + f(cx + r + 2) + 'V' + f(yb + 2) + 'H' + f(cx + r * 0.35) + 'Z', P.shadow, 0, 0.16);
    s += C.face(ctx, d, P.moon, tex, 1.8);
    // 银箍
    s += line('M' + f(cx - r + 0.6) + ' ' + f(yb - h * 0.3) + 'Q' + f(cx) + ' ' + f(yb - h * 0.3 + 3) + ' ' + f(cx + r - 0.6) + ' ' + f(yb - h * 0.3), 3, 1) +
      line('M' + f(cx - r + 0.6) + ' ' + f(yb - h * 0.3) + 'Q' + f(cx) + ' ' + f(yb - h * 0.3 + 3) + ' ' + f(cx + r - 0.6) + ' ' + f(yb - h * 0.3), 1.6, 1, P.silver);
    // 炉口：暗洞 + 炭火 + 月白火苗
    var mw = r * 0.8, mo = Q.archD(cx - mw / 2, yb - 1, mw, h * 0.52, 0.7);
    s += path(Q.archD(cx - mw / 2 - 2, yb - 1, mw + 4, h * 0.52 + 2.4, 0.7), P.moon2, 1.2) + path(mo, EMBER, 1.2);
    var fire = rect(cx - mw / 2, yb - 4.5, mw, 3.5, P.wash, 0) +
      path('M' + f(cx - mw * 0.35) + ' ' + f(yb - 4) + 'q' + f(mw * 0.1) + ' -7 ' + f(mw * 0.2) + ' -9q' + f(mw * 0.1) + ' 4 ' + f(mw * 0.15) + ' 3q' + f(mw * 0.08) + ' -5 ' + f(mw * 0.18) + ' -8q' + f(mw * 0.12) + ' 6 ' + f(mw * 0.17) + ' 14Z', P.moon, 0.7) +
      path('M' + f(cx - mw * 0.12) + ' ' + f(yb - 4) + 'q' + f(mw * 0.06) + ' -4 ' + f(mw * 0.12) + ' -5q' + f(mw * 0.08) + ' 3 ' + f(mw * 0.1) + ' 5Z', P.silver, 0);
    s += C.clipped(ctx, mo, fire);
    ctx.top(yb - h - 11);
    return s;
  }
  /** 银砧：立在树桩上，ax 中心，yb 地面 */
  function anvil(ctx, ax, yb) {
    var s = C.ellShadow(ax + 2, yb - 1, 8, 2.5);
    var st = F.cyl(ctx, ax, yb, 5.5, 5, { mat: 'bark', sill: false });
    s += st.svg + C.ellipse(ax, st.yt, 5.5, 3, P.bark2, 1) + line(C.ellD(ax, st.yt, 3, 1.6), 0.5, 0.5);
    var t = st.yt - 1;
    var d = 'M' + f(ax - 11) + ' ' + f(t - 6.5) + 'Q' + f(ax - 7) + ' ' + f(t - 4) + ' ' + f(ax - 5) + ' ' + f(t - 3.5) + 'L' + f(ax - 3.5) + ' ' + f(t) +
      'L' + f(ax + 3.5) + ' ' + f(t) + 'L' + f(ax + 4.5) + ' ' + f(t - 3.5) + 'L' + f(ax + 8) + ' ' + f(t - 3.5) + 'L' + f(ax + 8) + ' ' + f(t - 7) + 'L' + f(ax - 5) + ' ' + f(t - 7) + 'Q' + f(ax - 8) + ' ' + f(t - 7) + ' ' + f(ax - 11) + ' ' + f(t - 6.5) + 'Z';
    s += C.face(ctx, d, P.silver, rect(ax + 2, t - 7, 7, 7, P.shadow, 0, 0.18) + line('M' + f(ax - 6) + ' ' + f(t - 6.2) + 'H' + f(ax + 7), 0.8, 0.5), 1.3);
    // 斜靠的锤子
    s += line('M' + f(ax + 9) + ' ' + f(yb - 1) + 'L' + f(ax + 12) + ' ' + f(yb - 12), 1.8, 1, P.timber) + rect(ax + 9.6, yb - 15, 5, 3.4, P.moon2, 0.9);
    ctx.top(t - 8);
    return s;
  }
  /** 淬火槽：x 左，yb 地面，w 宽 */
  function trough(ctx, x, yb, w) {
    var s = C.shadow(C.rectD(x + 3, yb - 3, w, 4.5));
    s += rect(x, yb - 13, w, 5, P.water, 1.2) + line('M' + f(x + 3) + ' ' + f(yb - 11) + 'h' + f(w * 0.3) + 'M' + f(x + w * 0.55) + ' ' + f(yb - 10) + 'h' + f(w * 0.25), 0.6, 0.6);
    s += C.face(ctx, C.rectD(x, yb - 8, w, 8), P.silver2, F.wallTex(ctx, 'silver', x, yb - 8, w, 8) + rect(x + w - 3, yb - 8, 3, 8, P.shadow, 0, 0.15), 1.3);
    return s;
  }
  function forge(ctx) {
    var s = C.groundShadow(8, 90, -6, -80);
    // 后排：月光石烟塔（右后）
    var ch = F.cyl(ctx, 80, -44, 8, 58, { mat: 'stone' });
    s += ch.svg + C.ellipse(80, ch.yt, 8, 4.4, P.moon2, 1.3) + C.ellipse(80, ch.yt, 5, 2.6, EMBER, 0.8);
    s += Q.vine(ctx, [[86, -48], [87, -66], [85, -84], [86, -96]], { step: 5 });
    s += smoke(ctx, 80, ch.yt - 3);
    // 后排：银白木作坊，敞口拱门，叶舟顶
    s += F.wall(ctx, 8, 68, -46, 24);
    s += Q.door(ctx, 30, -46, 16, 19, { open: true, step: true });
    s += Q.win(ctx, 14, -54, 4, 9, { lit: true }) + Q.win(ctx, 56, -54, 4, 9);
    // 墙上挂钳与锤
    s += line('M50 -66v8M53 -66l-1 9M48 -66h7', 1.2) + rect(50.6, -61, 4, 2.6, P.moon2, 0.8);
    s += F.roofLeaf(ctx, { x0: 8, x1: 68, yE: -70, D: 26, R: 10, mat: 'leaf', curl: 5 }).svg;
    // 前院：熔炉、风箱、银砧、淬火槽、灯
    s += furnace(ctx, 28, -16, 15, 26);
    s += path('M44 -18L52 -22L52 -14Z', P.bark2, 1.1) + line('M45 -18H51M52 -18h4', 0.8, 0.8) + line('M52 -22l4 -1.5', 1.2);
    s += anvil(ctx, 63, -10) + trough(ctx, 74, -4, 18);
    s += Q.lamp(ctx, 6, -3, 15, 1);
    return s;
  }

  // ---------------- 市场：藤棚摊位 ----------------
  var GOODS = ['fruit', 'cloth', 'jars', 'herbs'];
  /** 货摊：x 左，yb 地面，w 宽；台高 10，台面进深 6；kind 货物 */
  function stall(ctx, x, yb, w, kind) {
    var s = C.shadow(C.rectD(x + 3, yb - 2, w, 4)), top = yb - 10, g = '', k;
    s += C.face(ctx, C.rectD(x, top - 6, w, 6), P.silver2, line('M' + f(x) + ' ' + f(top - 3) + 'H' + f(x + w), 0.6, 0.4), 1.2);
    if (kind === 'fruit') for (k = x + 3; k < x + w - 2; k += 3.4) g += C.circle(k, top - 3 - ctx.rnd(0, 1.5), 1.7, ctx.pick([P.tile, P.wash, P.moss]), 0.6);
    else if (kind === 'cloth') for (k = x + 2; k < x + w - 5; k += 6) g += rect(k, top - 7, 5, 4, ctx.pick([P.leaf, P.moon, P.silver, '#b7a3c4']), 0.8, 1, 1.2);
    else if (kind === 'jars') for (k = x + 3.5; k < x + w - 2; k += 5) g += path('M' + f(k - 2) + ' ' + f(top - 2) + 'q-1 -4 1 -6h2q2 2 1 6Z', ctx.pick([P.moon, P.moon2, P.silver]), 0.8);
    else for (k = x + 3; k < x + w - 2; k += 4) g += Q.leaf(k, top - 2, 6, -Math.PI / 2 + ctx.rnd(-0.4, 0.4), ctx.pick([P.leaf, P.moss]), 0.6);
    s += g;
    s += C.face(ctx, C.rectD(x, top, w, 10), P.silver, F.wallTex(ctx, 'silver', x, top, w, 10) + rect(x + w - 3, top, 3, 10, P.shadow, 0, 0.15), 1.4);
    s += Q.leaf(x + w / 2 - 3, top + 4, 5, 0, P.leaf, 0.6) + Q.leaf(x + w / 2 + 3, top + 4, 5, Math.PI, P.leaf, 0.6);
    ctx.top(top - 10);
    return s;
  }

  /** 藤棚：前排柱 yF、后排柱 yB（地面），柱高 h；x0..x1；n 开间。返回 { back, top } 后排柱 / 顶部藤架（前排柱由调用方在最后画） */
  function trellis(ctx, x0, x1, yF, yB, h, n) {
    var back = '', top = '', k, xs = [];
    for (k = 0; k <= n; k++) xs.push(x0 + (x1 - x0) * k / n);
    xs.forEach(function (x) { back += post(x, yB, yB - h, 2.2); });
    var tF = yF - h, tB = yB - h, d = '';
    // 纵梁（前后）+ 横梁（前、后）+ 椽子
    xs.forEach(function (x) { d += 'M' + f(x) + ' ' + f(tF) + 'L' + f(x) + ' ' + f(tB); });
    d += 'M' + f(x0 - 3) + ' ' + f(tF) + 'H' + f(x1 + 3) + 'M' + f(x0 - 3) + ' ' + f(tB) + 'H' + f(x1 + 3);
    for (var y = tF - 23; y > tB + 6; y -= 23) d += 'M' + f(x0) + ' ' + f(y) + 'H' + f(x1);
    top += line(d, 3.2, 1) + line(d, 1.6, 1, P.silver);
    // 藤蔓沿横梁爬，偶有垂下的藤条与花
    for (y = tF; y >= tB - 0.1; y -= (tF - tB)) {
      var pts = [];
      for (var x = x0 - 2; x <= x1 + 2; x += 9) pts.push([x, y + ctx.rnd(-1.2, 1.2)]);
      top += Q.vine(ctx, pts, { step: 3.6, sw: 1.6, flowers: true, len: 5 });
    }
    for (k = 0; k < n * 2; k++) {
      var hx = x0 + ctx.rnd(4, x1 - x0 - 4), hl = ctx.rnd(6, 12);
      top += Q.vine(ctx, [[hx, tF], [hx + 1, tF + hl * 0.5], [hx - 0.5, tF + hl]], { step: 3.5, sw: 1, len: 3.6 });
    }
    ctx.top(tB - 6);
    return { back: back, top: top, xs: xs };
  }
  function market(ctx) {
    var s = '', i;
    // 月光石铺地
    var pave = '';
    for (var y = -6; y > -92; y -= 9) for (var x = 6 + ((y / 9) & 1) * 6; x < 138; x += 12) pave += C.ellipse(x, y, 5, 2.4, ((x + y) & 3) ? P.moon : P.moon2, 0.6, 1);
    s += C.clipped(ctx, C.rectD(2, -94, 140, 92), pave);
    var T = trellis(ctx, 10, 134, -10, -80, 36, 4);
    s += C.groundShadow(10, 134, -10, -116) + T.back;
    // 后排摊位
    s += stall(ctx, 16, -62, 26, 'cloth') + stall(ctx, 59, -62, 26, 'jars') + stall(ctx, 102, -62, 26, 'herbs');
    // 中央月光石泉
    s += C.ellipse(72, -34, 14, 6, P.moon2, 1.3) + C.ellipse(72, -35.5, 11, 4.6, P.water, 0.9) + line('M64 -36h5M75 -34h4', 0.6, 0.6);
    s += rect(70, -50, 4, 15, P.moon, 1) + C.ellipse(72, -50, 6, 2.6, P.moon, 1) + path('M72 -60q3 4 0 8q-3 -4 0 -8Z', P.moon, 0.8) + line('M68 -50q-3 6 -4 13M76 -50q3 6 4 13', 0.8, 0.6, P.water);
    // 前排摊位
    s += stall(ctx, 18, -18, 30, 'fruit') + stall(ctx, 96, -18, 30, 'herbs');
    s += Q.lamp(ctx, 4, -3, 15, 1) + Q.lamp(ctx, 140, -3, 15, -1);
    // 前排柱 + 顶棚
    T.xs.forEach(function (x) { s += post(x, -10, -46, 2.4); });
    s += T.top;
    s += banner(72, -46, 16, P.leaf);
    return s;
  }
  function stallProp(ctx) {
    var s = C.groundShadow(6, 42, -12, -30);
    s += post(7, -14, -36, 2.2) + post(41, -14, -36, 2.2);
    s += stall(ctx, 9, -12, 30, ctx.pick(GOODS));
    s += F.roofLeaf(ctx, { x0: 6, x1: 42, yE: -36, D: 10, R: 4, mat: 'moss', curl: 3, ov: 2 }).svg;
    s += C.ellipse(37, -4, 4, 2, P.wood, 0.9) + C.circle(36, -6, 1.5, P.tile, 0.6) + C.circle(38.4, -6.2, 1.5, P.wash, 0.6);
    return s;
  }

  // ---------------- 行政厅：议事古树殿 ----------------
  function townHall(ctx) {
    var s = C.groundShadow(10, 138, -8, -132), k;
    // 古树：粗干 + 高处环台 + 大冠
    s += F.trunk(ctx, 72, -66, 22, 15, 110, { roots: 12 }).svg;
    s += F.branch(ctx, 60, -168, 22, -188, 7) + F.branch(ctx, 84, -172, 124, -196, 7);
    var R = F.ring(ctx, 72, -150, 42, 4, { railH: 6 });
    s += R.back + R.deck + HA.column(ctx, 72, -152, 15, 12, -206) + R.front;
    for (k = 0; k < 3; k++) s += banner(48 + k * 24, -148, 12, k === 1 ? P.moss : P.leaf);
    s += F.canopy(ctx, 72, -228, 64, 34, { n: 11, gems: 5 });
    // 两侧月光石细塔
    s += HA.pod(ctx, 13, -40, 8, 46, { mat: 'stone', door: false, wins: [0], R: 28, shape: 'spire', rmat: 'leaf' });
    s += HA.pod(ctx, 131, -40, 8, 46, { mat: 'stone', door: false, wins: [0], R: 28, shape: 'spire', rmat: 'leaf' });
    // 主殿：银白木长廊，尖拱柱廊
    s += F.wall(ctx, 22, 122, -12, 30);
    for (k = 0; k < 6; k++) {
      var ax = 27 + k * 16 + (k > 2 ? 6 : 0);
      if (k === 3 || k === 2) continue;
      s += path(Q.archD(ax, -12, 10, 22, 0.8), P.glass, 1.1) + Q.leaf(ax + 5, -36, 5, -Math.PI / 2, P.leaf, 0.6);
    }
    s += F.roofLeaf(ctx, { x0: 22, x1: 122, yE: -42, D: 30, R: 12, mat: 'leaf', curl: 6 }).svg;
    // 正中门廊：叶尖山墙 + 双开尖拱大门 + 台阶
    s += F.wall(ctx, 52, 92, -4, 38, { mat: 'stone' });
    s += Q.door(ctx, 62, -4, 20, 28, { fill: P.bark, step: true });
    s += line('M72 -6v-24', 1);
    s += F.roofGable(ctx, { x0: 50, x1: 94, yE: -42, D: 22, R: 24, mat: 'moss' }).svg;
    s += Q.roundWin(ctx, 72, -52, 4.4, { lit: true });
    s += banner(56, -40, 18, P.leaf) + banner(88, -40, 18, P.leaf);
    s += rect(56, -3, 32, 3, P.moon2, 1);
    s += Q.lamp(ctx, 44, -2, 18, -1) + Q.lamp(ctx, 100, -2, 18, 1);
    return s;
  }

  var T = [
    { key: 'forge', suffix: true, kind: 'forge_elf_moon', name: '铁匠铺（月光熔炉）', facility: 'forge', fp: [2, 2], roof: 'gable_tile',
      tags: ['workshop', 'moonstone_furnace', 'silver_anvil', 'chimney'], draw: forge,
      note: '前院月光石穹顶熔炉 + 树桩银砧 + 淬火槽，后排叶舟顶作坊与月光石烟塔；叶顶取最近的 gable_tile' },
    { key: 'market', suffix: true, kind: 'market_elf_trellis', name: '藤棚市场', facility: 'market_hall', fp: [3, 2], roof: 'none',
      tags: ['trellis', 'open_air', 'stalls', 'fountain'], draw: market,
      note: '银白木藤棚架（顶部只有梁与藤，可透见下面摊位），五个货摊 + 中央月光石泉；无屋面' },
    { key: 'stall', suffix: true, kind: 'market_stall_elf', name: '叶篷摊位', facility: 'market_hall', category: 'prop', fp: [1, 1], roof: 'gable_thatch',
      tags: ['open_air', 'stall'], draw: stallProp, note: '露天单摊位（按规范 facility=market_hall + open_air）；苔叶篷取最近的 gable_thatch' },
    { key: 'townhall', suffix: true, kind: 'town_hall_elf_tree', name: '议事古树殿', facility: 'town_hall', fp: [3, 3], roof: 'gable_tile',
      tags: ['council', 'great_tree', 'ring_platform', 'colonnade', 'banner'], draw: townHall,
      note: '古树主干绕着建尖拱柱廊长殿，正中叶尖山墙门廊，树上议事环台挂叶幡，两侧月光石细塔；叶顶取最近的 gable_tile' }
  ];

  var API = { T: T, post: post, banner: banner, smoke: smoke, furnace: furnace, anvil: anvil, stall: stall, trellis: trellis };
  root.TownArtWE_specialA = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
