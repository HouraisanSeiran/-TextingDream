/*
 * 织梦 · 城镇西式精灵族民居 05–08：叶顶圆屋、双层吊桥连屋、花园亭屋、细塔屋（美术样板，尚未接入游戏）
 * 局部坐标：y = 0 为占地前沿，向上为负。每种 3 个变体，变体之间改轮廓。
 * 浏览器挂 window.TownArtWE_housesB；Node 用 module.exports。依赖 core.js、parts.js、forms.js、houses-a.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWE_core;
  var Q = isNode ? require('./parts.js') : root.TownArtWE_parts;
  var F = isNode ? require('./forms.js') : root.TownArtWE_forms;
  var HA = isNode ? require('./houses-a.js') : root.TownArtWE_housesA;
  var P = C.P, f = C.f, line = C.line, path = C.path, rect = C.rect;

  // ---------------- 组合工具 ----------------
  /** 叶冠顶：从顶点向檐口放射的一圈长尖叶（后排先画，前排后画），cx 中心，yt 檐口椭圆中心，r 屋身半径，R 顶高 */
  function leafCrown(ctx, cx, yt, r, R, o) {
    o = o || {};
    var rr = r + 3, ry = rr * 0.55, T = [cx, yt - R], n = o.n || Math.max(9, Math.round(rr * 0.9)), back = [], front = [], s = '';
    s += path('M' + f(cx - r) + ' ' + f(yt) + 'A' + f(r) + ' ' + f(r * 0.55) + ' 0 0 0 ' + f(cx + r) + ' ' + f(yt) + 'v4A' + f(r) + ' ' + f(r * 0.55) + ' 0 0 1 ' + f(cx - r) + ' ' + f(yt + 4) + 'Z', P.shadow, 0, 0.24);
    // 托底锥（叶缝里露出的深色）
    s += path('M' + f(cx - rr * 0.9) + ' ' + f(yt + 1) + 'Q' + f(cx - rr * 0.3) + ' ' + f(yt - R * 0.6) + ' ' + f(T[0]) + ' ' + f(T[1]) +
      'Q' + f(cx + rr * 0.3) + ' ' + f(yt - R * 0.6) + ' ' + f(cx + rr * 0.9) + ' ' + f(yt + 1) + 'Z', P.leaf2, 1.2);
    for (var j = 0; j < n; j++) {
      var b = Math.PI * 2 * (j + 0.5) / n, tip = [cx + Math.cos(b) * (rr + 2), yt + Math.sin(b) * ry + 3];
      var base = [cx + Math.cos(b) * rr * 0.12, T[1] + 2], dx = tip[0] - base[0], dy = tip[1] - base[1];
      var L = { b: b, base: base, len: Math.hypot(dx, dy), ang: Math.atan2(dy, dx), y: tip[1] };
      (Math.sin(b) < 0 ? back : front).push(L);
    }
    back.sort(function (a, c) { return a.y - c.y; });
    front.sort(function (a, c) { return Math.abs(Math.cos(c.b)) - Math.abs(Math.cos(a.b)); });
    back.concat(front).forEach(function (L) {
      var lit = Math.cos(L.b) < 0.15, w = rr * (o.wide || 0.2);
      var d = Q.leafD(L.base[0], L.base[1], L.len, L.ang, w / 1.6);
      s += path(d, lit ? (o.light || P.leaf) : P.leaf2, 1.1);
      s += line('M' + f(L.base[0]) + ' ' + f(L.base[1]) + 'L' + f(L.base[0] + Math.cos(L.ang) * L.len * 0.9) + ' ' + f(L.base[1] + Math.sin(L.ang) * L.len * 0.9), 0.6, 0.55);
    });
    // 顶上一颗卷芽
    s += path('M' + f(T[0] - 3) + ' ' + f(T[1] + 2) + 'Q' + f(T[0] - 3) + ' ' + f(T[1] - 6) + ' ' + f(T[0] + 1.5) + ' ' + f(T[1] - 8) +
      'Q' + f(T[0] + 3.5) + ' ' + f(T[1] - 3) + ' ' + f(T[0] + 3) + ' ' + f(T[1] + 2) + 'Z', P.moss, 1.1);
    ctx.top(T[1] - 9);
    return s;
  }
  /** 吊桥：a、b 两端桥面点，sag 中部下垂；木板 + 两道扶手绳 + 吊索 */
  function bridge(ctx, a, b, sag) {
    var m = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + sag], s = '', n = Math.max(4, Math.round(Math.abs(b[0] - a[0]) / 3.2));
    var deck = 'M' + f(a[0]) + ' ' + f(a[1]) + 'Q' + f(m[0]) + ' ' + f(m[1] + sag) + ' ' + f(b[0]) + ' ' + f(b[1]);
    s += line(deck, 4.6, 1) + line(deck, 3, 1, P.silver2);
    var pl = '', hang = '';
    for (var k = 1; k < n; k++) {
      var t = k / n, u = 1 - t, x = u * u * a[0] + 2 * u * t * m[0] + t * t * b[0], y = u * u * a[1] + 2 * u * t * (m[1] + sag) + t * t * b[1];
      pl += 'M' + f(x) + ' ' + f(y - 1.4) + 'v2.8';
      var yr = u * a[1] + t * b[1] - 9 + sag * 4 * t * u * 0.4;
      if (k % 2 === 0) hang += 'M' + f(x) + ' ' + f(y - 1) + 'L' + f(x) + ' ' + f(yr);
    }
    s += line(pl, 0.7, 0.7);
    var rope = 'M' + f(a[0]) + ' ' + f(a[1] - 9) + 'Q' + f(m[0]) + ' ' + f(m[1] - 9 + sag * 0.4) + ' ' + f(b[0]) + ' ' + f(b[1] - 9);
    s += line(hang, 0.6, 0.8) + line(rope, 1.3, 1, P.bark);
    // 两端系桩
    [a, b].forEach(function (p) { s += line('M' + f(p[0]) + ' ' + f(p[1]) + 'v-11', 2.6, 1) + line('M' + f(p[0]) + ' ' + f(p[1]) + 'v-11', 1.2, 1, P.silver); });
    return s;
  }
  /** 花畦：x,y 左上，w,h；小叶丛 + 银白/淡黄小花 */
  function flowerBed(ctx, x, y, w, h) {
    var s = rect(x, y, w, h, '#a98a5e', 1, 1, 3), lv = '', fl = '';
    for (var yy = y + 3; yy < y + h - 1; yy += 4)
      for (var xx = x + 3 + ctx.rnd(0, 1.5); xx < x + w - 2; xx += ctx.rnd(3.2, 4.4)) {
        lv += 'M' + f(xx - 1.6) + ' ' + f(yy + 1) + 'q1.6 -3.4 3.2 0';
        if (ctx.chance(0.4)) fl += C.circle(xx, yy - 1.4, 0.9, ctx.chance(0.6) ? P.silver : P.wash, 0.4);
      }
    return s + '<path d="' + lv + '" fill="' + P.leaf + '"' + C.stroke(0.6, 0.8) + '/>' + fl;
  }
  /** 小水池：椭圆，月光石沿 */
  function pond(ctx, cx, cy, rx, ry) {
    var s = C.ellipse(cx, cy, rx + 2, ry + 1.4, P.moon2, 1.2) + C.ellipse(cx, cy, rx, ry, P.water, 0.8);
    s += line('M' + f(cx - rx * 0.5) + ' ' + f(cy - ry * 0.2) + 'h' + f(rx * 0.4) + 'M' + f(cx + rx * 0.1) + ' ' + f(cy + ry * 0.3) + 'h' + f(rx * 0.35), 0.7, 0.55);
    s += Q.leaf(cx + rx * 0.35, cy - ry * 0.3, 4, 0.3, P.moss, 0.5) + C.circle(cx + rx * 0.4, cy - ry * 0.25, 0.9, P.silver, 0.4);
    return s;
  }

  // ---------------- 05 叶顶圆屋 ----------------
  function leafRound(ctx, v) {
    var i = v.i, s = '', c;
    if (i === 1) {
      s += C.ellShadow(26, -6, 18, 6);
      c = F.cyl(ctx, 24, -4, 14, 18);
      s += c.svg + Q.door(ctx, 20, -4.6, 8, 13, { step: true });
      s += Q.win(ctx, 11.5, c.yc - 8, 3.2, 7) + Q.win(ctx, 33.3, c.yc - 8, 3.2, 7, { lit: true });
      s += leafCrown(ctx, 24, c.yt, 14, 30) + Q.lamp(ctx, 42, -2, 13, -1);
    } else if (i === 2) { // 两层：下层宽圆身 + 苔瓣披檐，上层窄圆身 + 叶冠
      s += C.ellShadow(26, -6, 19, 6);
      c = F.cyl(ctx, 24, -4, 16, 13, { mat: 'stone' });
      s += c.svg + Q.door(ctx, 20, -4.6, 8, 11, { step: true }) + Q.roundWin(ctx, 12, c.yc - 7, 2.4) + Q.roundWin(ctx, 36, c.yc - 7, 2.4, { lit: true });
      var sk = F.cap(ctx, 24, c.yt, 16, 9, { mat: 'moss', finial: false, ov: 3 });
      s += sk.svg;
      var c2 = F.cyl(ctx, 24, c.yt - 5, 9, 12, { sill: false });
      s += c2.svg + Q.win(ctx, 22.4, c2.yc - 3, 3.2, 7, { lit: true });
      s += leafCrown(ctx, 24, c2.yt, 9, 24, { n: 9 });
    } else { // 2×1：两座圆屋 + 中间叶舟顶连廊
      s += C.groundShadow(8, 92, -6, -30);
      s += F.wall(ctx, 30, 68, -10, 12) + Q.door(ctx, 45, -10, 8, 10) + Q.win(ctx, 35, -14, 3.2, 6) + Q.win(ctx, 59, -14, 3.2, 6, { lit: true });
      s += F.roofLeaf(ctx, { x0: 30, x1: 68, yE: -22, D: 14, R: 6, mat: 'moss', curl: 3 }).svg;
      c = F.cyl(ctx, 22, -4, 13, 16);
      s += c.svg + Q.door(ctx, 18.5, -4.6, 7, 12, { step: true }) + Q.win(ctx, 11, c.yc - 8, 3.2, 7);
      s += leafCrown(ctx, 22, c.yt, 13, 28);
      var c3 = F.cyl(ctx, 76, -4, 11, 20, { mat: 'stone' });
      s += c3.svg + Q.win(ctx, 74.4, c3.yc - 11, 3.2, 8, { lit: true });
      s += leafCrown(ctx, 76, c3.yt, 11, 26, { light: P.moss });
      s += flowerBed(ctx, 52, -9, 12, 6);
    }
    return s;
  }

  // ---------------- 06 双层吊桥连屋 ----------------
  /** 两层屋：下层月光石、上层银白木外挑一点；返回 { svg, y2 }（y2 = 上层地板） */
  function twoStorey(ctx, x0, x1, yb, h1, h2, o) {
    o = o || {};
    var xc = (x0 + x1) / 2, s = F.wall(ctx, x0, x1, yb, h1, { mat: 'stone' }), y2 = yb - h1;
    s += Q.door(ctx, xc - 4 + (o.dx || 0), yb, 8, Math.min(h1 - 2, 12), { step: true });
    s += rect(x0 - 2, y2 - 1.5, x1 - x0 + 4, 3, P.bark, 1) + rect(x0, y2 + 1.5, x1 - x0, 2.5, P.shadow, 0, 0.22);
    s += F.wall(ctx, x0 - 2, x1 + 2, y2 - 1.5, h2, { sill: false });
    s += Q.win(ctx, x0 + 3.5, y2 - 4.5, 3.6, h2 - 8, { lit: o.lit }) + Q.win(ctx, x1 - 7.1, y2 - 4.5, 3.6, h2 - 8);
    var yE = y2 - 1.5 - h2;
    if (o.leafRoof) s += F.roofLeaf(ctx, { x0: x0 - 2, x1: x1 + 2, yE: yE, D: 12, R: 7, mat: o.rmat || 'leaf', curl: 4 }).svg;
    else {
      s += F.roofGable(ctx, { x0: x0 - 2, x1: x1 + 2, yE: yE, D: 12, R: o.R || 12, mat: o.rmat || 'leaf' }).svg;
      s += Q.roundWin(ctx, xc, yE - (o.R || 12) * 0.38, 2.6, { lit: true });
    }
    return { svg: s, y2: y2 };
  }
  function bridgeHouse(ctx, v) {
    var i = v.i, s = '', R;
    if (i === 1) { // 2×1：左两层屋，右高脚圆舱，上层之间吊桥
      s += C.groundShadow(6, 90, -6, -30);
      s += line('M66 -4V-30M82 -4V-30', 3.6, 1) + line('M66 -4V-30M82 -4V-30', 2, 1, P.silver2);
      R = F.ring(ctx, 74, -30, 15, 3, { railH: 4, floor: -1 });
      s += R.back + R.deck + HA.pod(ctx, 74, -27, 9, 12, { wins: [0.6], R: 16, rmat: 'moss' }) + R.front;
      s += HA.ladder(86, -27, -2, 4);
      s += twoStorey(ctx, 6, 38, -6, 14, 14, { lit: true }).svg;
      s += bridge(ctx, [40, -21], [60, -29], 3);
      s += HA.mush(46, -2) + HA.mush(52, -1, 0.7);
    } else if (i === 2) { // 2×1：两棵树上的环台，台间吊桥
      s += C.groundShadow(10, 90, -6, -30);
      s += F.trunk(ctx, 22, -8, 7.5, 6, 52, { roots: 5 }).svg + F.trunk(ctx, 74, -8, 7.5, 6, 36, { roots: 5 }).svg;
      R = F.ring(ctx, 22, -60, 16, 3, { railH: 4 });
      s += R.back + R.deck + HA.column(ctx, 22, -61, 6, 5, -104) + HA.hut(ctx, 13, 31, -56, 12, { R: 10, D: 10, dw: 6, wins: [], doorX: 19 }) + R.front;
      var R2 = F.ring(ctx, 74, -44, 16, 3, { railH: 4 });
      s += R2.back + R2.deck + HA.column(ctx, 74, -45, 6, 5, -96) + HA.pod(ctx, 74, -41, 8, 11, { wins: [-0.6], R: 14 }) + R2.front;
      s += bridge(ctx, [38, -60], [58, -45], 3) + HA.ladder(84, -40, -2, 4);
      s += F.canopy(ctx, 22, -108, 20, 13, { n: 6, gems: 2 }) + F.canopy(ctx, 74, -98, 20, 13, { n: 6, gems: 1 });
    } else { // 2×2：后排高树台屋，前排树根屋 + 中层圆舱，斜吊桥相连
      s += C.groundShadow(10, 38, -50, -70) + C.groundShadow(54, 92, -6, -40);
      s += F.trunk(ctx, 22, -50, 7.5, 6, 26, { roots: 5 }).svg;
      R = F.ring(ctx, 22, -78, 16, 3, { railH: 4 });
      s += R.back + R.deck + HA.column(ctx, 22, -79, 6, 5, -116) + HA.hut(ctx, 12, 32, -74, 13, { R: 10, D: 10, dw: 6, wins: [27], doorX: 15 }) + R.front;
      s += F.canopy(ctx, 22, -122, 20, 14, { n: 7, gems: 2 });
      s += bridge(ctx, [38, -78], [56, -66], 3);
      s += F.trunk(ctx, 72, -6, 11, 7, 58, { roots: 7 }).svg;
      s += Q.door(ctx, 67, -6, 10, 15, { fill: P.bark, frame: P.moss, step: true }) + Q.roundWin(ctx, 79, -34, 2.2, { lit: true });
      var R3 = F.ring(ctx, 72, -66, 16, 3, { railH: 4 });
      s += R3.back + R3.deck + HA.column(ctx, 72, -67, 6, 5, -104) + HA.pod(ctx, 72, -63, 8, 11, { wins: [0.6], R: 14, rmat: 'moss' }) + R3.front;
      s += F.canopy(ctx, 72, -110, 22, 14, { n: 7, gems: 2 });
      s += Q.lamp(ctx, 46, -4, 15, 1) + HA.mush(88, -2);
    }
    return s;
  }

  // ---------------- 07 花园亭屋 ----------------
  /** 圆亭：中心 cx，前沿地面 yF，半径 r，柱高 H；o.half 后半圈砌银白木墙（成为半敞的亭屋），o.R 顶高，o.rmat */
  function pavilion(ctx, cx, yF, r, H, o) {
    o = o || {};
    var ry = r * 0.55, yc = yF - ry - 2.2, yt = yc - H, s = '', k;
    s += C.ellShadow(cx + 3, yF - 1, r + 3, 3);
    s += C.ellipse(cx, yc + 0.6, r + 2.5, ry + 1.6, P.moon2, 1.2) + C.ellipse(cx, yc - 1, r + 2.5, ry + 1.6, P.moon, 1.2);
    var back = 'M' + f(cx - r) + ' ' + f(yc - 1) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 1 ' + f(cx + r) + ' ' + f(yc - 1) + 'V' + f(yt) + 'H' + f(cx - r) + 'Z';
    s += C.face(ctx, back, o.half ? P.silver2 : '#bdb79f', o.half ? F.wallTex(ctx, 'silver', cx - r, yt, 2 * r, yc - yt) : '', 1);
    s += rect(cx - r, yt, 2 * r, 4, P.shadow, 0, 0.25);
    if (o.half) s += Q.roundWin(ctx, cx, yt + H * 0.42, 3, { lit: true }) + Q.win(ctx, cx - r * 0.62 - 1.5, yc - ry * 0.7 - 2, 3, 7);
    function post(a) {
      var px = cx + Math.cos(a) * r, py = yc - 1 + Math.sin(a) * ry, d = 'M' + f(px) + ' ' + f(py) + 'V' + f(yt + Math.sin(a) * ry);
      return line(d, 2.8, 1) + line(d, 1.3, 1, P.silver);
    }
    [Math.PI * 4 / 3, Math.PI * 5 / 3].forEach(function (a) { s += post(a); });
    // 亭中长凳
    s += rect(cx - r * 0.5, yc - 6, r, 2.4, P.wood, 0.9) + line('M' + f(cx - r * 0.4) + ' ' + f(yc - 3.6) + 'v3M' + f(cx + r * 0.4) + ' ' + f(yc - 3.6) + 'v3', 1.2);
    s += Q.railArc(ctx, cx, yc - 1, r, ry, 0.15, 0.95, 5, { leafP: 0.6 }) + Q.railArc(ctx, cx, yc - 1, r, ry, Math.PI - 0.95, Math.PI - 0.15, 5, { leafP: 0.6 });
    [0, Math.PI / 3, Math.PI * 2 / 3, Math.PI].forEach(function (a) { s += post(a); });
    for (k = 0; k < 2; k++) {
      var a0 = k ? Math.PI * 2 / 3 : Math.PI / 3, px = cx + Math.cos(a0) * r, py = yc - 1 + Math.sin(a0) * ry;
      s += Q.vine(ctx, [[px, py], [px + 1.2, py - H * 0.4], [px - 0.8, py - H * 0.8], [px, yt + ry * 0.8]], { step: 4, sw: 1, flowers: true, len: 3.6 });
    }
    s += F.cap(ctx, cx, yt, r, o.R || r * 1.5, { mat: o.rmat || 'petal', shape: o.shape, ov: 3 }).svg;
    ctx.top(yt);
    return s;
  }
  function gardenHouse(ctx, v) {
    var i = v.i, s = '';
    if (i === 1) { // 1×1：半敞亭屋，后半圈是墙，门前花畦
      s += pavilion(ctx, 24, -8, 15, 17, { half: true, R: 20, rmat: 'moss' });
      s += flowerBed(ctx, 2, -9, 10, 7) + flowerBed(ctx, 36, -9, 10, 7);
    } else if (i === 2) { // 2×1：左山墙小屋 + 右敞亭，中间小水池
      s += C.groundShadow(4, 40, -10, -32);
      s += HA.hut(ctx, 4, 36, -10, 15, { R: 12, D: 12, wins: [27], doorX: 8, step: true, rmat: 'moss' });
      s += pond(ctx, 45, -6, 6, 3) + pavilion(ctx, 72, -6, 13, 15, { R: 18 });
      s += flowerBed(ctx, 4, -8, 14, 6);
    } else { // 2×2：后排叶舟顶长屋，前院亭子 + 池塘 + 花畦 + 藤篱
      s += C.groundShadow(10, 88, -54, -76);
      s += F.wall(ctx, 12, 84, -54, 16) + Q.door(ctx, 44, -54, 8, 13, { step: true });
      s += Q.win(ctx, 20, -60, 4, 8, { lit: true }) + Q.win(ctx, 31, -60, 4, 8) + Q.win(ctx, 61, -60, 4, 8) + Q.win(ctx, 72, -60, 4, 8, { lit: true });
      s += F.roofLeaf(ctx, { x0: 12, x1: 84, yE: -70, D: 18, R: 10, mat: 'leaf', curl: 5 }).svg;
      var st = '';
      [[48, -48], [46, -40], [49, -32], [47, -24]].forEach(function (p) { st += C.ellipse(p[0], p[1], 3.4, 1.8, P.moon, 0.8); });
      s += st + flowerBed(ctx, 58, -46, 28, 8) + flowerBed(ctx, 8, -46, 30, 7);
      s += pond(ctx, 70, -16, 13, 6) + pavilion(ctx, 26, -8, 14, 16, { R: 20 });
      s += Q.rail(ctx, 50, 92, -2, 5) + Q.lamp(ctx, 52, -4, 15, 1);
    }
    return s;
  }

  // ---------------- 08 细塔屋 ----------------
  /** 细高塔：中心 cx，地面 yF，半径 r，高 H；o.balc 阳台高度（从地面算），o.R 尖顶高 */
  function slimTower(ctx, cx, yF, r, H, o) {
    o = o || {};
    var c = F.cyl(ctx, cx, yF, r, H, { mat: o.mat || 'silver' }), s = c.svg;
    s += Q.door(ctx, cx - 3.5, yF - 0.6, 7, 11, { step: true });
    for (var y = c.yc - 22; y > c.yt + 12; y -= 18) s += Q.win(ctx, cx - 1.6 + (o.wx || 0), y, 3.2, 8, { lit: y < c.yt + 32 });
    // 腰箍：两道银白木环
    [0.38, 0.7].forEach(function (q) {
      var yy = c.yc - H * q;
      s += path('M' + f(cx - r - 0.6) + ' ' + f(yy - 1.6) + 'A' + f(r + 0.6) + ' ' + f(r * 0.55) + ' 0 0 0 ' + f(cx + r + 0.6) + ' ' + f(yy - 1.6) + 'v3A' + f(r + 0.6) + ' ' + f(r * 0.55) + ' 0 0 1 ' + f(cx - r - 0.6) + ' ' + f(yy + 1.4) + 'Z', P.silver2, 0.9);
    });
    if (o.vine) s += Q.vine(ctx, [[cx - r + 1, yF - 3], [cx - r + 3, yF - H * 0.3], [cx - r + 1, yF - H * 0.55], [cx - r + 4, yF - H * 0.75]], { step: 5, flowers: true });
    if (o.balc) {
      var R = F.ring(ctx, cx, yF - o.balc, r + 6, 2.5, { railH: 4 });
      s += R.back + R.deck + R.front;
    }
    s += F.cap(ctx, cx, c.yt, r, o.R || r * 3, { shape: 'spire', mat: o.rmat || 'leaf', ov: 2.5 }).svg;
    return s;
  }
  function towerHouse(ctx, v) {
    var i = v.i, s = '';
    if (i === 1) { // 1×1：单座细塔 + 门前月光石灯
      s += C.ellShadow(27, -5, 14, 5);
      s += slimTower(ctx, 24, -4, 9, 84, { R: 34, vine: true, rmat: 'leaf' });
      s += Q.lamp(ctx, 40, -2, 13, -1) + HA.mush(8, -2);
    } else if (i === 2) { // 1×1：细塔靠着一座矮山墙小屋，塔腰挑出环形阳台
      s += C.groundShadow(4, 46, -6, -32);
      s += HA.hut(ctx, 3, 27, -6, 13, { R: 10, D: 12, wins: [], doorX: 9.5, rmat: 'moss' });
      s += slimTower(ctx, 34, -4, 8, 76, { R: 30, balc: 54, wx: 0, rmat: 'petal' });
    } else { // 2×1：一高一矮两座细塔，塔腰吊桥相连
      s += C.groundShadow(8, 90, -6, -30);
      s += slimTower(ctx, 70, -6, 9, 60, { R: 28, rmat: 'moss' });
      s += slimTower(ctx, 26, -4, 10, 88, { R: 36, vine: true, rmat: 'leaf' });
      s += bridge(ctx, [36, -54], [61, -48], 2.5);
      s += Q.lamp(ctx, 48, -3, 14, 1);
    }
    return s;
  }

  var T = [
    { n: 5, kind: 'house_elf_leafround', name: '叶顶圆屋', fp: [1, 1], fps: [[1, 1], [1, 1], [2, 1]], roof: 'gable_thatch',
      vname: ['单层叶冠', '两层叶冠', '双圆屋连廊'], tags: ['round', 'leaf_crown'], draw: leafRound,
      note: '圆屋身顶上一圈放射长尖叶；无对应 RoofId，取最近的 gable_thatch（植物覆面）' },
    { n: 6, kind: 'house_elf_bridged', name: '双层吊桥连屋', fp: [2, 1], fps: [[2, 1], [2, 1], [2, 2]], roof: 'gable_tile',
      vname: ['屋台吊桥', '双树台吊桥', '前后错台'], tags: ['two_storey', 'rope_bridge', 'raised'], draw: bridgeHouse,
      note: '两处建筑的上层之间挂吊桥；叶形屋顶取最近的 gable_tile' },
    { n: 7, kind: 'house_elf_garden', name: '花园亭屋', fp: [1, 1], fps: [[1, 1], [2, 1], [2, 2]], roof: 'gable_tile',
      vname: ['半敞亭屋', '小屋带亭', '庭院长屋'], tags: ['garden', 'pavilion', 'pond'], draw: gardenHouse,
      note: '花瓣穹顶圆亭 + 花畦、水池；穹顶无对应 RoofId，取最近的 gable_tile' },
    { n: 8, kind: 'house_elf_tower', name: '细塔屋', fp: [1, 1], fps: [[1, 1], [1, 1], [2, 1]], roof: 'steep_slate',
      vname: ['单塔', '塔靠小屋', '双塔吊桥'], tags: ['tower', 'spire', 'tall'], draw: towerHouse,
      note: '细高圆塔、内凹尖叶顶；尖顶取最近的 steep_slate' }
  ];

  var API = { T: T, leafCrown: leafCrown, bridge: bridge, flowerBed: flowerBed, pond: pond, twoStorey: twoStorey, pavilion: pavilion, slimTower: slimTower };
  root.TownArtWE_housesB = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
