/*
 * 织梦 · 城镇西式精灵族民居 01–04 + 组合工具（美术样板，尚未接入游戏）
 * 局部坐标：y = 0 为占地前沿，向上为负。每种 3 个变体，变体之间改轮廓（不只是翻转换色）。
 * 浏览器挂 window.TownArtWE_housesA；Node 用 module.exports。依赖 core.js、parts.js、forms.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWE_core;
  var Q = isNode ? require('./parts.js') : root.TownArtWE_parts;
  var F = isNode ? require('./forms.js') : root.TownArtWE_forms;
  var P = C.P, f = C.f, line = C.line, path = C.path, rect = C.rect;

  // ---------------- 组合工具 ----------------
  /** 树干一段（无根）：cx，底 yb 半宽 wb，顶 yt 半宽 wt */
  function column(ctx, cx, yb, wb, wt, yt) {
    var h = yb - yt;
    var d = 'M' + f(cx - wb) + ' ' + f(yb) + 'C' + f(cx - wb) + ' ' + f(yb - h * 0.4) + ' ' + f(cx - wt) + ' ' + f(yt + h * 0.4) + ' ' + f(cx - wt) + ' ' + f(yt) +
      'L' + f(cx + wt) + ' ' + f(yt) + 'C' + f(cx + wt) + ' ' + f(yt + h * 0.4) + ' ' + f(cx + wb) + ' ' + f(yb - h * 0.4) + ' ' + f(cx + wb) + ' ' + f(yb) + 'Z';
    var t = '';
    for (var u = -0.75; u < 0.8; u += ctx.rnd(0.28, 0.4))
      t += 'M' + f(cx + u * wb) + ' ' + f(yb) + 'Q' + f(cx + u * (wb + wt) / 2 + ctx.rnd(-1.5, 1.5)) + ' ' + f(yb - h / 2) + ' ' + f(cx + u * wt) + ' ' + f(yt);
    var tex = line(t, 0.8, 0.5) + rect(cx + wt * 0.3, yt, wb * 1.2, h, P.shadow, 0, 0.2) + C.hatch(cx + wt * 0.5, yt + h * 0.3, wb * 0.6, h * 0.4, 3.4, 0.3);
    ctx.top(yt);
    return C.face(ctx, d, P.bark2, tex, 1.7);
  }
  /** 绳梯：x 左绳，yt 顶，yb 底，w 宽 */
  function ladder(x, yt, yb, w) {
    w = w || 4;
    var my = (yt + yb) / 2;
    var r = 'M' + f(x) + ' ' + f(yt) + 'Q' + f(x - 0.8) + ' ' + f(my) + ' ' + f(x) + ' ' + f(yb) +
      'M' + f(x + w) + ' ' + f(yt) + 'Q' + f(x + w - 0.8) + ' ' + f(my) + ' ' + f(x + w) + ' ' + f(yb);
    var g = '';
    for (var y = yt + 4; y < yb - 1; y += 5) g += 'M' + f(x - 0.3) + ' ' + f(y) + 'h' + f(w + 0.6);
    return line(g, 2, 1) + line(g, 0.9, 1, P.silver) + line(r, 1.1, 1, P.bark);
  }
  /** 悬空台阶：pts 从下到上的踏板中心；画时从上往下（下面的踏板在前） */
  function steps(pts, w) {
    var s = '', rl = [], d = '';
    for (var k = pts.length - 1; k >= 0; k--) s += rect(pts[k][0] - w / 2, pts[k][1] - 2.4, w, 2.6, P.silver2, 0.9);
    pts.forEach(function (p, k) {
      rl.push([p[0] + w / 2 - 0.5, p[1] - 8]);
      if (k % 2 === 0) d += 'M' + f(p[0] + w / 2 - 0.5) + ' ' + f(p[1] - 2.4) + 'V' + f(p[1] - 8);
    });
    var r = C.smooth(rl);
    return s + line(d, 1.2, 1) + line(r, 2.2, 1) + line(r, 1, 1, P.silver);
  }
  /** 小屋：银白木墙 + 叶尖山墙 / 叶舟顶 + 尖拱门窗 */
  function hut(ctx, x0, x1, yb, h, o) {
    o = o || {};
    var s = '', w = x1 - x0, xc = (x0 + x1) / 2, R = o.R || w * 0.5, r;
    s += F.wall(ctx, x0, x1, yb, h, { mat: o.mat || 'silver', sill: o.sill });
    var dw = o.dw || Math.min(8, w * 0.32), dh = Math.min(h - 3, dw * 1.6);
    if (o.door !== false) s += Q.door(ctx, o.doorX != null ? o.doorX : xc - dw / 2, yb, dw, dh, { step: o.step });
    (o.wins || []).forEach(function (wx) { s += Q.win(ctx, wx, yb - h * 0.3, 4, Math.min(8, h * 0.45), { lit: o.lit }); });
    if (o.roof === 'leaf') {
      r = F.roofLeaf(ctx, { x0: x0, x1: x1, yE: yb - h, D: o.D || 14, R: R, mat: o.rmat || 'leaf', curl: o.curl, ov: o.ov });
      s += r.svg;
    } else {
      r = F.roofGable(ctx, { x0: x0, x1: x1, yE: yb - h, D: o.D || 12, R: R, mat: o.rmat || 'leaf', ov: o.ov });
      s += r.svg;
      if (o.gwin !== false) s += Q.roundWin(ctx, xc, yb - h - R * 0.38, Math.max(1.8, Math.min(3.4, w * 0.1)), { lit: o.lit });
    }
    return s;
  }
  /** 圆屋：圆身 + 花瓣穹顶 / 尖塔顶。o.wins 窗位置（-1..1 的横向比例） */
  function pod(ctx, cx, yF, r, H, o) {
    o = o || {};
    var c = F.cyl(ctx, cx, yF, r, H, { mat: o.mat || 'silver' }), s = c.svg;
    if (o.door !== false) { var dw = Math.min(7, r * 0.7); s += Q.door(ctx, cx - dw / 2 + (o.dOff || 0), yF - 0.6, dw, Math.min(H - 2, dw * 1.6)); }
    (o.wins || []).forEach(function (u) { s += Q.win(ctx, cx + u * r - 1.6, c.yc - H * 0.38, 3.2, Math.min(7, H * 0.4), { lit: o.lit }); });
    s += F.cap(ctx, cx, c.yt, r, o.R || r * 1.6, { shape: o.shape || 'dome', mat: o.rmat || 'petal', finial: o.finial, ov: o.ov }).svg;
    return s;
  }
  /** 月光蘑菇：x 中心，yb 地面 */
  function mush(x, yb, s) {
    s = s || 1;
    return rect(x - 0.8 * s, yb - 3.5 * s, 1.6 * s, 3.5 * s, P.silver, 0.6) +
      path('M' + f(x - 3 * s) + ' ' + f(yb - 3 * s) + 'Q' + f(x) + ' ' + f(yb - 8 * s) + ' ' + f(x + 3 * s) + ' ' + f(yb - 3 * s) + 'Z', P.moon, 0.8) +
      C.circle(x - 0.8 * s, yb - 4.8 * s, 0.5 * s, P.silver, 0);
  }

  // ---------------- 01 巨树树屋（1×1） ----------------
  function treeHouse(ctx, v) {
    var i = v.i, s = C.groundShadow(10, 40, -6, -26);
    var dk = i === 3 ? -54 : -70, top = i === 3 ? -150 : -128;
    s += F.trunk(ctx, 24, -8, 8, 6.5, -8 - dk, { roots: 5 }).svg;
    var R1 = F.ring(ctx, 24, dk, i === 3 ? 22 : 20, 4, { railH: 5 });
    s += R1.back + R1.deck + column(ctx, 24, dk, 6.5, 5, top);
    if (i === 1) s += hut(ctx, 13, 35, dk + 5, 15, { R: 12, D: 12, wins: [28.5], doorX: 16 });
    else if (i === 2) s += pod(ctx, 24, dk + 7, 10, 15, { wins: [-0.62, 0.62], R: 18 });
    else s += pod(ctx, 24, dk + 7, 9, 12, { wins: [0.62], R: 12, finial: false, rmat: 'moss' });
    s += R1.front;
    if (i === 3) {
      var R2 = F.ring(ctx, 24, -106, 14, 3, { railH: 4 });
      s += R2.back + R2.deck + hut(ctx, 16, 32, -102, 10, { roof: 'leaf', R: 7, D: 10, dw: 5.5 }) + R2.front;
      s += ladder(9, -96, -47, 4);
    }
    s += ladder(i === 2 ? 8 : 35, dk + 12, -1, 4);
    if (i === 1) s += Q.lamp(ctx, 7, -3, 16, 1);
    else s += mush(42, -2) + mush(38, -1, 0.7);
    var cy = i === 3 ? -160 : -136;
    s += F.canopy(ctx, i === 2 ? 26 : 24, cy, i === 3 ? 22 : 24, 16, { gems: 3 });
    return s;
  }

  // ---------------- 02 树根洞屋 ----------------
  function rootHouse(ctx, v) {
    var i = v.i, s = '';
    if (i === 1) { // 活树根部掏洞，门开在根间
      s += C.groundShadow(6, 44, -6, -30);
      s += F.trunk(ctx, 24, -6, 15, 9, 62, { roots: 7 }).svg;
      s += Q.door(ctx, 18, -6, 12, 18, { fill: P.bark, frame: P.moss, step: true });
      s += Q.roundWin(ctx, 15, -38, 2.8) + Q.roundWin(ctx, 32.5, -31, 2.4, { lit: true });
      s += Q.vine(ctx, [[10, -8], [12, -24], [10, -42], [14, -60]], { step: 5, flowers: true });
      s += Q.lamp(ctx, 41, -3, 14, -1) + mush(6, -2, 0.8);
      s += column(ctx, 24, -67, 9, 7, -96);
      s += F.canopy(ctx, 24, -100, 26, 18, { gems: 2 });
    } else if (i === 2) { // 截断的老树桩，桩顶盖苔瓣圆顶
      s += C.groundShadow(4, 44, -6, -30);
      var tr = F.trunk(ctx, 24, -6, 17, 15, 40, { roots: 8 });
      s += tr.svg;
      var yt = tr.yt, rings = '';
      for (var k = 1; k < 4; k++) rings += C.ellD(24, yt, 15 * k / 4, 6 * k / 4);
      s += C.ellipse(24, yt, 15, 6, P.silver2, 1.4) + line(rings, 0.6, 0.45);
      s += F.cap(ctx, 24, yt - 1, 13, 26, { mat: 'moss', ov: 3 }).svg;
      s += Q.door(ctx, 19, -6, 10, 16, { fill: P.bark, step: true });
      s += Q.win(ctx, 33, -24, 3.6, 7, { lit: true }) + Q.roundWin(ctx, 13, -27, 2.4);
      s += line('M37 ' + f(yt + 2) + 'v-12', 2.4) + line('M37 ' + f(yt + 2) + 'v-12', 1, 1, P.silver) + C.circle(37, yt - 12, 1.8, P.moon, 0.8);
      s += mush(43, -2) + mush(5, -3, 0.7);
    } else { // 2×1：大树根拱下的长洞屋，左边接叶尖山墙门廊
      s += C.groundShadow(4, 92, -6, -36);
      s += F.trunk(ctx, 60, -6, 17, 10, 74, { roots: 10 }).svg;
      s += Q.door(ctx, 54, -6, 12, 18, { fill: P.bark, frame: P.moss });
      s += Q.roundWin(ctx, 70.5, -34, 2.6, { lit: true });
      s += hut(ctx, 8, 38, -6, 15, { R: 12, D: 12, wins: [28], doorX: 12, step: true });
      s += line('M38 -10Q42 -14 44 -8M38 -18Q43 -22 44 -14', 2.6, 1) + line('M38 -10Q42 -14 44 -8M38 -18Q43 -22 44 -14', 1.2, 1, P.bark2);
      s += Q.vine(ctx, [[84, -6], [80, -26], [76, -48], [70, -66]], { step: 5, flowers: true });
      s += mush(88, -2) + mush(84, -1, 0.7) + Q.lamp(ctx, 46, -2, 14, -1);
      s += column(ctx, 60, -79, 10, 8, -108);
      s += F.canopy(ctx, 60, -114, 34, 20, { n: 8, gems: 3 });
    }
    return s;
  }

  // ---------------- 03 环形平台屋 ----------------
  function stilts(ctx, cx, y, rx, us, yb) {
    var ry = rx * 0.5, d = '';
    us.forEach(function (u) { var x = cx + u * rx; d += 'M' + f(x) + ' ' + f(y + Math.sqrt(1 - u * u) * ry + 3) + 'V' + f(yb); });
    return line(d, 3.6, 1) + line(d, 2, 1, P.silver2);
  }
  function ringHouse(ctx, v) {
    var i = v.i, s = '', R;
    if (i === 1) { // 2×2 低台：高脚环台，左山墙屋 + 右圆舱
      s += C.groundShadow(8, 90, -4, -60);
      s += F.trunk(ctx, 48, -6, 11, 9, 40, { roots: 7 }).svg;
      s += stilts(ctx, 48, -44, 40, [-0.8, -0.4, 0.4, 0.8], -4);
      R = F.ring(ctx, 48, -44, 40, 4, { railH: 6 });
      s += R.back + R.deck + column(ctx, 48, -46, 9, 7, -120);
      s += hut(ctx, 12, 36, -34, 14, { R: 11, D: 12, wins: [28], doorX: 15 });
      s += pod(ctx, 70, -32, 10, 13, { wins: [0.6], R: 16 });
      s += R.front + steps([[86, -5], [84, -11], [82, -17], [80, -23], [78, -29]], 7);
      s += F.canopy(ctx, 48, -128, 40, 22, { n: 9, gems: 3 });
    } else if (i === 2) { // 2×2 高台：托梁挑出，台前一座叶舟顶长屋，绳梯落地
      s += C.groundShadow(14, 84, -4, -60);
      s += F.trunk(ctx, 48, -6, 12, 9, 56, { roots: 8 }).svg;
      R = F.ring(ctx, 48, -60, 38, 4, { railH: 6 });
      s += R.back + R.deck + column(ctx, 48, -62, 9, 7, -128);
      s += hut(ctx, 26, 70, -46, 15, { roof: 'leaf', R: 9, D: 16, wins: [31, 61], doorX: 44, rmat: 'leaf' });
      s += R.front + ladder(18, -42, -2, 4);
      s += F.canopy(ctx, 48, -136, 38, 20, { n: 9, gems: 2 });
    } else { // 2×1 地面环台：一圈矮台围着树，台上两座小圆舱
      s += C.groundShadow(10, 88, -4, -40);
      R = F.ring(ctx, 48, -24, 36, 3, { railH: 5 });
      s += R.back + R.deck + F.trunk(ctx, 48, -22, 10, 8, 72, { roots: 6 }).svg;
      s += pod(ctx, 24, -14, 8, 12, { wins: [0.6], R: 14, rmat: 'moss' });
      s += pod(ctx, 72, -14, 8, 11, { wins: [-0.6], R: 16, shape: 'spire' });
      s += R.front + Q.lamp(ctx, 8, -6, 14, 1);
      s += F.canopy(ctx, 48, -108, 34, 20, { n: 8, gems: 2 });
    }
    return s;
  }

  // ---------------- 04 藤拱小屋 ----------------
  /** 藤拱：两根藤从地面拱起、在顶上交成尖弧，挂叶与银白小花 */
  function vineArch(ctx, x0, x1, yb, h) {
    var xc = (x0 + x1) / 2, s = '';
    [[x0, 1], [x1, -1]].forEach(function (p) {
      var x = p[0], k = p[1], hw = Math.abs(xc - x);
      var pts = [[x, yb], [x - k, yb - h * 0.35], [x + k * hw * 0.12, yb - h * 0.7], [xc - k * hw * 0.45, yb - h * 0.93], [xc, yb - h]];
      s += line(C.smooth(pts), 4, 1) + Q.vine(ctx, pts, { sw: 2.4, color: P.bark2, step: 4.5, flowers: true });
    });
    ctx.top(yb - h - 4);
    return s;
  }
  function vineHouse(ctx, v) {
    var i = v.i, s = '';
    if (i === 1) {
      s += C.groundShadow(8, 42, -6, -32);
      s += hut(ctx, 8, 40, -6, 16, { R: 13, D: 14, rmat: 'moss', wins: [31], doorX: 13, step: true });
      s += vineArch(ctx, 9, 25, -3, 26) + Q.vine(ctx, [[40, -6], [42, -18], [38, -30], [32, -36]], { step: 4.5 });
    } else if (i === 2) { // 大藤拱整个罩住小屋，叶舟顶
      s += C.groundShadow(4, 44, -4, -34);
      s += hut(ctx, 11, 37, -8, 14, { roof: 'leaf', R: 8, D: 14, wins: [29], doorX: 15, rmat: 'leaf' });
      s += vineArch(ctx, 4, 44, -3, 48);
      s += Q.lamp(ctx, 42, -3, 12, -1);
    } else { // 2×1：两座小屋之间一道藤拱门廊
      s += C.groundShadow(4, 92, -6, -34);
      s += hut(ctx, 4, 34, -8, 15, { R: 12, D: 12, wins: [25], doorX: 8 });
      s += pod(ctx, 76, -8, 12, 14, { wins: [-0.6, 0.6], R: 18, rmat: 'moss' });
      s += vineArch(ctx, 38, 58, -4, 34) + Q.lamp(ctx, 37, -3, 13, -1);
      s += Q.rail(ctx, 60, 64, -5, 5);
    }
    return s;
  }

  var T = [
    { n: 1, kind: 'house_elf_treehouse', name: '巨树树屋', fp: [1, 1], roof: 'gable_tile', vname: ['叶尖山墙屋', '花瓣圆舱', '双层台'],
      tags: ['treehouse', 'raised', 'ring_platform', 'rope_ladder'], draw: treeHouse,
      note: '树干上一圈环形木台，台上小屋，绳梯落地；叶形屋顶无对应 RoofId，取最近的 gable_tile' },
    { n: 2, kind: 'house_elf_root', name: '树根洞屋', fps: [[1, 1], [1, 1], [2, 1]], roof: 'gable_tile', vname: ['活树根洞', '树桩苔顶', '根拱长洞'],
      tags: ['burrow', 'tree_root', 'ground_level'], draw: rootHouse,
      note: '门开在巨树根间；变体 2 是截断树桩上盖苔瓣圆顶；叶形/穹顶无对应 RoofId，取 gable_tile' },
    { n: 3, kind: 'house_elf_ring', name: '环形平台屋', fps: [[2, 2], [2, 2], [2, 1]], roof: 'gable_tile', vname: ['高脚环台', '挑梁高台', '地面环台'],
      tags: ['ring_platform', 'raised', 'tree_trunk'], draw: ringHouse,
      note: '绕巨树主干的一圈椭圆木台，台上有屋；变体 3 是贴地矮台' },
    { n: 4, kind: 'house_elf_vinearch', name: '藤拱小屋', fps: [[1, 1], [1, 1], [2, 1]], roof: 'gable_tile', vname: ['门前藤拱', '藤拱罩屋', '藤拱连廊'],
      tags: ['vine_arch', 'ground_level'], draw: vineHouse,
      note: '活藤拱成尖弧门廊，挂银白小花' }
  ];

  var API = { T: T, column: column, ladder: ladder, steps: steps, hut: hut, pod: pod, mush: mush };
  root.TownArtWE_housesA = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
