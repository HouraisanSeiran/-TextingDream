/*
 * 织梦 · 西式双网格瓦片：道路三档（dirt / stone / highway）× 16、城墙 × 16 + 城门 gate-h / gate-v + 塔楼（美术样板，尚未接入游戏）
 * 四角编码 mask = NW*8 + NE*4 + SW*2 + SE*1。瓦片内部坐标 0..48（y 向下），四角 = 四个逻辑格中心。
 * 道路：路面 = 是路的角所在的象限（逻辑格边界即 x=24 / y=24 两条中线）；分界线过边中点且垂直于边，中心处圆角。
 *       纹理周期都整除 48，按世界坐标对齐。
 * 城墙：墙沿逻辑格中心线走，墙厚 24 px（每块瓦片里占 12 px 宽的带）；高 H，墙顶有垛口。按 12 px 小格计算。
 * 浏览器挂 window.TownArtWB_tiles；Node 用 module.exports。依赖 common.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./common.js') : root.TownArtWB_common;
  var P = C.PAL, f = C.f, S = 48, M = 24, RAD = 10, WALL_H = 40;
  var BITS = [8, 4, 2, 1]; // 象限 q = qy*2+qx：NW NE SW SE
  function on(mask, qx, qy) { return !!(mask & BITS[qy * 2 + qx]); }
  function bin(m) { return ('000' + m.toString(2)).slice(-4); }

  /** a→b 的手绘线段：两端切线沿线段方向（保证在瓦片边上垂直于边），中点偏 w */
  function curve(a, b, w) {
    var dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1, nx = -dy / L, ny = dx / L;
    var m = [(a[0] + b[0]) / 2 + nx * w, (a[1] + b[1]) / 2 + ny * w];
    return 'C' + f(a[0] + dx * 0.25) + ' ' + f(a[1] + dy * 0.25) + ' ' + f(m[0] - dx * 0.18) + ' ' + f(m[1] - dy * 0.18) + ' ' + f(m[0]) + ' ' + f(m[1]) +
      'S' + f(b[0] - dx * 0.25) + ' ' + f(b[1] - dy * 0.25) + ' ' + f(b[0]) + ' ' + f(b[1]);
  }
  /** 象限的内侧边界：从瓦片边中点 A 进到中心圆角，再出到另一条边中点 B（不带 M 以外的闭合） */
  function inner(qx, qy, r, w1, w2) {
    var ox = qx * S, oy = qy * S, sx = qx ? 1 : -1, sy = qy ? 1 : -1;
    var A = [M, oy], E1 = [M, M + sy * r], E2 = [M + sx * r, M], B = [ox, M];
    return 'M' + f(A[0]) + ' ' + f(A[1]) + curve(A, E1, w1) + 'Q' + M + ' ' + M + ' ' + f(E2[0]) + ' ' + f(E2[1]) + curve(E2, B, w2);
  }
  function quadFill(qx, qy, r, w1, w2) { return inner(qx, qy, r, w1, w2) + 'L' + qx * S + ' ' + qy * S + 'Z'; }

  /** 路面形状：{ fill, rule, outline } */
  function roadShape(ctx, mask) {
    var k = 0, i, qs = [];
    for (i = 0; i < 4; i++) { var qx = i % 2, qy = i >> 1; if (on(mask, qx, qy)) { k++; qs.push([qx, qy]); } }
    var w = function () { return ctx.rnd(-1.6, 1.6); };
    if (k === 0) return null;
    if (k === 4) return { fill: C.rectD(0, 0, S, S), rule: 'nonzero', outline: '' };
    if (k === 3) {
      for (i = 0; i < 4; i++) if (!on(mask, i % 2, i >> 1)) break;
      var a = w(), b = w(), q = inner(i % 2, i >> 1, RAD, a, b);
      return { fill: C.rectD(0, 0, S, S) + quadFill(i % 2, i >> 1, RAD, a, b), rule: 'evenodd', outline: q };
    }
    if (k === 2 && mask !== 9 && mask !== 6) {
      var c = w(), seg;
      if (mask === 12) seg = ['M0 0L48 0L48 24', [48, 24], [0, 24]];
      else if (mask === 3) seg = ['M0 48L48 48L48 24', [48, 24], [0, 24]];
      else if (mask === 10) seg = ['M0 0L0 48L24 48', [24, 48], [24, 0]];
      else seg = ['M48 0L48 48L24 48', [24, 48], [24, 0]];
      var cv = curve(seg[1], seg[2], c);
      return { fill: seg[0] + cv + 'Z', rule: 'nonzero', outline: 'M' + seg[1].join(' ') + cv };
    }
    var fl = '', ol = '';
    qs.forEach(function (p) { var a1 = w(), b1 = w(); fl += quadFill(p[0], p[1], RAD, a1, b1); ol += inner(p[0], p[1], RAD, a1, b1); });
    return { fill: fl, rule: 'nonzero', outline: ol };
  }
  function clipRule(ctx, d, rule, innerSvg) {
    if (!innerSvg) return '';
    var id = ctx.uid();
    return '<defs><clipPath id="' + id + '"><path d="' + d + '" clip-rule="' + rule + '"/></clipPath></defs><g clip-path="url(#' + id + ')">' + innerSvg + '</g>';
  }
  function band(d, w, color, op) {
    return d ? '<path d="' + d + '" fill="none" stroke="' + color + '" stroke-width="' + f(w) + '"' + (op != null ? ' stroke-opacity="' + f(op) + '"' : '') + ' stroke-linejoin="round"/>' : '';
  }
  function dash(d, w, color, op, da) {
    return d ? '<path d="' + d + '" fill="none" stroke="' + color + '" stroke-width="' + f(w) + '" stroke-opacity="' + f(op) + '" stroke-dasharray="' + da + '"/>' : '';
  }

  // ---------- 三档路面纹理 ----------
  function slabs(rowH, slabW, off, tones, sw, op) {
    var o = '';
    for (var j = 0; j * rowH < S; j++) {
      var y = j * rowH, ox = (j % 2) * off;
      for (var k = -1; ox + k * slabW < S; k++) {
        var x = ox + k * slabW, ci = (((k % tones.length) + tones.length) + j) % tones.length;
        o += '<rect x="' + f(x) + '" y="' + f(y) + '" width="' + f(slabW) + '" height="' + f(rowH) + '" fill="' + tones[ci] + '"' + C.stroke(sw, op) + '/>';
      }
    }
    return o;
  }
  /** 土路车辙：象限的同行邻象限是路 → 横辙；同列邻象限是路 → 竖辙。辙距逻辑格中心线 7 px */
  function ruts(mask) {
    var d = '';
    for (var i = 0; i < 4; i++) {
      var qx = i % 2, qy = i >> 1;
      if (!on(mask, qx, qy)) continue;
      var ox = qx * S, oy = qy * S;
      if (on(mask, 1 - qx, qy)) { var y = oy + (qy ? -7 : 7); d += 'M' + ox + ' ' + f(y) + 'L' + M + ' ' + f(y); }
      if (on(mask, qx, 1 - qy)) { var x = ox + (qx ? -7 : 7); d += 'M' + f(x) + ' ' + oy + 'L' + f(x) + ' ' + M; }
    }
    return d;
  }
  var ROAD = {
    dirt: { name: '土路', base: '#d6bd8a', verge: '#c4a673' },
    stone: { name: '石板路', base: '#cdbf9f', verge: P.stone3 },
    highway: { name: '官道', base: '#c9c2aa', verge: '#a99a7e' }
  };
  function roadTex(ctx, mat, mask, outline) {
    var o = '';
    if (mat === 'dirt') {
      o += band(ruts(mask), 3.2, '#bf9f6c', 0.9) + band(ruts(mask), 0.8, P.ink, 0.35);
      for (var i = 0; i < 9; i++) {
        var px = ctx.rnd(4, 44), py = ctx.rnd(4, 44);
        o += '<ellipse cx="' + f(px) + '" cy="' + f(py) + '" rx="' + f(ctx.rnd(0.9, 1.8)) + '" ry="' + f(ctx.rnd(0.7, 1.2)) + '" fill="' + ctx.pick([P.stone, P.stone2, '#b9a47c']) + '"' + C.stroke(0.5, 0.6) + '/>';
      }
      for (i = 0; i < 5; i++) {
        var qx = ctx.rnd(4, 42), qy = ctx.rnd(4, 44);
        o += C.line('M' + f(qx) + ' ' + f(qy) + 'q1.5 -0.8 3 0', 0.6, 0.35);
      }
      o += band(outline, 7, ROAD.dirt.verge, 1);
    } else if (mat === 'stone') {
      o += slabs(12, 16, 8, ['#cdbf9f', '#c4b593', '#d3c6a7'], 0.8, 0.5);
      o += band(outline, 8, ROAD.stone.verge, 1) + dash(outline, 8, P.ink, 0.45, '1 5');
    } else {
      o += slabs(16, 24, 12, ['#c9c2aa', '#bfb79e', '#d1cab3'], 1, 0.55);
      o += band(outline, 13, P.ink, 0.85) + band(outline, 11, '#b8ab8e', 1) + dash(outline, 11, P.ink, 0.55, '1.2 6.8');
    }
    return o;
  }
  function roadTile(ctx, mat, mask) {
    var sh = roadShape(ctx, mask);
    if (!sh) return '';
    var R = ROAD[mat];
    var s = '<path d="' + sh.fill + '" fill="' + R.base + '" fill-rule="' + sh.rule + '"/>';
    s += clipRule(ctx, sh.fill, sh.rule, roadTex(ctx, mat, mask, sh.outline));
    s += sh.outline ? C.line(sh.outline, 1.4, 0.9) : '';
    return s;
  }

  // ---------- 城墙（瓦片坐标 0..48，y 向下；按 12 px 小格） ----------
  var G = 12, WALK = '#c3b494';
  /** 4×4 小格占用：四角是墙 → 角上一格；相邻两角都是墙 → 连成边带；四角全是 → 填满 */
  function wallCells(mask) {
    var g = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]];
    var nw = mask & 8, ne = mask & 4, sw = mask & 2, se = mask & 1;
    if (nw) g[0][0] = 1; if (ne) g[0][3] = 1; if (sw) g[3][0] = 1; if (se) g[3][3] = 1;
    if (nw && ne) g[0][1] = g[0][2] = 1;
    if (sw && se) g[3][1] = g[3][2] = 1;
    if (nw && sw) g[1][0] = g[2][0] = 1;
    if (ne && se) g[1][3] = g[2][3] = 1;
    if (mask === 15) g[1][1] = g[1][2] = g[2][1] = g[2][2] = 1;
    return g;
  }
  /** 墙正面：方石按瓦片坐标对齐（层高 8、块长 16、错缝 8，周期都整除 48），只在真接缝处画缝 */
  function stoneFace(x0, x1, yb, h, endL, endR) {
    var s = '', tones = [P.stone, '#c7b897', P.stone2, '#d4c6a8'], joints = '', courses = '', r = 0, course = 8;
    for (var y = yb; y > yb - h + 0.1; y -= course, r++) {
      var y0 = Math.max(yb - h, y - course), off = (r % 2) * 8;
      for (var k = Math.floor((x0 - off) / 16); off + k * 16 < x1; k++) {
        var bx0 = Math.max(x0, off + k * 16), bx1 = Math.min(x1, off + (k + 1) * 16);
        s += '<rect x="' + f(bx0) + '" y="' + f(y0) + '" width="' + f(bx1 - bx0) + '" height="' + f(y - y0) + '" fill="' + tones[((((k % 3) + 3) % 3) + r) % 4] + '"/>';
        if (off + k * 16 > x0 && off + k * 16 < x1) joints += 'M' + f(off + k * 16) + ' ' + f(y) + 'V' + f(y0);
      }
      if (y0 > yb - h + 0.1) courses += 'M' + f(x0) + ' ' + f(y0) + 'H' + f(x1);
    }
    s += C.line(courses + joints, 0.8, 0.55);
    // 勒脚与墙顶压檐
    s += C.rect(x0, yb - 5, x1 - x0, 5, P.stone3, 0) + C.line('M' + f(x0) + ' ' + f(yb - 5) + 'H' + f(x1), 0.9, 0.7);
    s += C.rect(x0, yb - h, x1 - x0, 2.5, P.shadow, 0, 0.14);
    var ol = 'M' + f(x0) + ' ' + f(yb) + 'H' + f(x1);
    if (endL) ol += 'M' + f(x0) + ' ' + f(yb) + 'V' + f(yb - h);
    if (endR) ol += 'M' + f(x1) + ' ' + f(yb) + 'V' + f(yb - h);
    return s + C.line(ol, 1.6);
  }
  function wallTile(ctx, mask) {
    if (!mask) return '';
    var g = wallCells(mask), H = WALL_H, s = '', cx, cy;
    function at(x, y) { return x >= 0 && x < 4 && y >= 0 && y < 4 ? g[y][x] : 2; }
    var shade = '', faces = '', tops = '', grid = '', edge = '', back = '', front = '';
    for (cy = 0; cy < 4; cy++) for (cx = 0; cx < 4; cx++) {
      if (!g[cy][cx]) continue;
      var x = cx * G, y = cy * G, ty = y - H;
      // 地面投影：东侧、南侧
      if (at(cx + 1, cy) === 0) shade += C.rect(x + G, y + 2, 5, G, P.shadow, 0, 0.18);
      if (at(cx, cy + 1) === 0) shade += C.rect(x + 3, y + G, G, 4, P.shadow, 0, 0.18);
      tops += C.rect(x, ty, G, G, WALK, 0);
      grid += 'M' + f(x + 6) + ' ' + f(ty) + 'v' + G + 'M' + f(x) + ' ' + f(ty + 6) + 'h' + G;
      if (at(cx, cy - 1) === 0) {
        edge += 'M' + f(x) + ' ' + f(ty) + 'h' + G;
        back += C.rect(x, ty, G, 3, P.stone2, 0) + C.rect(x + 2.5, ty - 5, 7, 7, P.stone, 0.9);
      }
      if (at(cx - 1, cy) === 0) {
        edge += 'M' + f(x) + ' ' + f(ty) + 'v' + G;
        back += C.rect(x, ty, 3.5, G, P.stone2, 0) + C.rect(x, ty + 1, 3.5, 9, P.stone, 0.9) + C.line('M' + f(x) + ' ' + f(ty + 5) + 'h3.5', 0.7, 0.6);
      }
      if (at(cx + 1, cy) === 0) {
        edge += 'M' + f(x + G) + ' ' + f(ty) + 'v' + G;
        back += C.rect(x + G - 3.5, ty, 3.5, G, P.stone2, 0) + C.rect(x + G - 3.5, ty + 1, 3.5, 9, P.stone3, 0.9) + C.line('M' + f(x + G - 3.5) + ' ' + f(ty + 5) + 'h3.5', 0.7, 0.6);
      }
      if (at(cx, cy + 1) === 0) {
        var e = ty + G;
        edge += 'M' + f(x) + ' ' + f(e) + 'h' + G;
        front += C.rect(x, e - 3.5, G, 3.5, P.stone, 0) + C.rect(x + 2.5, e - 10, 7, 10, P.stone, 1) + C.line('M' + f(x + 2.5) + ' ' + f(e - 7.5) + 'h7', 0.7, 0.6);
      }
    }
    // 正面：每行连续的一段
    for (cy = 0; cy < 3; cy++) {
      cx = 0;
      while (cx < 4) {
        if (g[cy][cx] && g[cy + 1][cx] === 0) {
          var a = cx;
          while (cx < 4 && g[cy][cx] && g[cy + 1][cx] === 0) cx++;
          var x0 = a * G, x1 = cx * G;
          faces += stoneFace(x0, x1, (cy + 1) * G, H, x0 > 0, x1 < S);
        } else cx++;
      }
    }
    s += shade + faces + tops + C.line(grid, 0.6, 0.3) + back + front + C.line(edge, 1.4);
    ctx.top(-H - 6);
    return s;
  }

  // ---------- 叠加件（对齐逻辑格；局部坐标 y = 0 为逻辑格前沿，墙带在 y -36..-12） ----------
  function passage(ctx, x, yb, w, h) {
    var r = w / 2, d = 'M' + f(x) + ' ' + f(yb) + 'V' + f(yb - h + r) + 'A' + f(r) + ' ' + f(r) + ' 0 0 1 ' + f(x + w) + ' ' + f(yb - h + r) + 'V' + f(yb) + 'Z';
    var ring = 'M' + f(x - 3.5) + ' ' + f(yb) + 'V' + f(yb - h + r) + 'A' + f(r + 3.5) + ' ' + f(r + 3.5) + ' 0 0 1 ' + f(x + w + 3.5) + ' ' + f(yb - h + r) + 'V' + f(yb) + 'Z';
    var s = C.path(ring, P.stone2, 1.3), vs = '';
    for (var i = 1; i < 8; i++) {
      var a = Math.PI * i / 8, cx = x + r, cy = yb - h + r;
      vs += 'M' + f(cx - Math.cos(a) * r) + ' ' + f(cy - Math.sin(a) * r) + 'L' + f(cx - Math.cos(a) * (r + 3.5)) + ' ' + f(cy - Math.sin(a) * (r + 3.5));
    }
    s += C.line(vs, 0.8, 0.7) + C.path(d, '#3b2d1f', 0);
    // 吊闸：升起一半，下缘齿尖
    var py = yb - h * 0.45, grid = '', teeth = '';
    for (var gx = x + 3; gx < x + w - 1; gx += 3.5) { grid += 'M' + f(gx) + ' ' + f(yb - h) + 'V' + f(py); teeth += 'M' + f(gx - 1) + ' ' + f(py) + 'l1 2.6l1 -2.6Z'; }
    for (var gy = py - 4; gy > yb - h; gy -= 4.5) grid += 'M' + f(x) + ' ' + f(gy) + 'H' + f(x + w);
    s += C.clipped(ctx, d, C.line(grid, 1.3, 1, P.dark) + C.line(grid, 0.4, 0.6) + C.path(teeth, P.dark, 0));
    return s + C.path(d, 'none', 1.4);
  }
  /** 门楼顶下的一排托石（突堞） */
  function corbels(x0, x1, y) {
    var s = C.rect(x0 - 1.5, y - 4, x1 - x0 + 3, 4, P.stone, 1.1), t = '';
    for (var x = x0 + 1; x < x1 - 2; x += 5) t += C.path('M' + f(x) + ' ' + f(y) + 'h3v2.6l-1.5 1.4l-1.5 -1.4Z', P.stone2, 0.7);
    return s + t;
  }
  function pennant(ctx, x, y, color) {
    ctx.top(y - 14);
    return C.line('M' + f(x) + ' ' + f(y) + 'v-14', 1.3) + C.path('M' + f(x) + ' ' + f(y - 14) + 'q5 1 9 3q-5 0.6 -9 3Z', color || P.red, 0.7);
  }
  function gateH(ctx) {
    var s = '', H = WALL_H, x0 = 3, x1 = 45, yb = -8, gh = H + 16;
    s += C.groundShadow(x0, x1, yb, -40);
    s += C.facade(ctx, x0, x1, yb, gh, 'ashlar', { tex: { course: 6, joint: 12 } });
    s += C.rect(x0, yb - 5, x1 - x0, 5, P.stone3, 1);
    s += passage(ctx, 15, yb, 18, 28);
    s += C.win(ctx, 8.5, yb - 40, 3, 8, 'slit') + C.win(ctx, 36.5, yb - 40, 3, 8, 'slit');
    // 门上纹章盾
    s += C.path('M20 ' + f(yb - 46) + 'h8v5q0 4 -4 6q-4 -2 -4 -6Z', P.red, 1) + C.line('M24 ' + f(yb - 45) + 'v9M21 ' + f(yb - 42) + 'h6', 1, 1, P.wash);
    s += corbels(x0, x1, yb - gh + 6);
    var r = C.roofSide(ctx, { x0: x0, x1: x1, yE: yb - gh + 2, D: 28, R: 12, mat: 'tile', ov: 2.5, hip: 0.7 });
    s += r.svg + pennant(ctx, 24, r.yR, P.red);
    return s;
  }
  function gateV(ctx) {
    var s = '', H = WALL_H, x0 = 8, x1 = 40, yb = -4, gh = H + 14;
    s += C.groundShadow(x0, x1, yb, -44);
    // 东西两侧敞开的门扇（门洞朝东西，正视只露门扇）
    [[2, 8], [40, 46]].forEach(function (p) {
      s += C.face(ctx, C.rectD(p[0], yb - 22, p[1] - p[0], 22), P.timber, C.line('M' + f(p[0]) + ' ' + f(yb - 16) + 'H' + f(p[1]) + 'M' + f(p[0]) + ' ' + f(yb - 6) + 'H' + f(p[1]), 1.2, 1, P.ink), 1.2);
    });
    s += C.facade(ctx, x0, x1, yb, gh, 'ashlar', { tex: { course: 6, joint: 12 } });
    s += C.rect(x0, yb - 5, x1 - x0, 5, P.stone3, 1);
    s += C.win(ctx, 22.5, yb - 24, 3, 9, 'slit') + C.win(ctx, 22.5, yb - 44, 3, 8, 'slit');
    s += C.path('M20 ' + f(yb - 36) + 'h8v5q0 4 -4 6q-4 -2 -4 -6Z', P.red, 1) + C.line('M24 ' + f(yb - 35) + 'v9M21 ' + f(yb - 32) + 'h6', 1, 1, P.wash);
    s += corbels(x0, x1, yb - gh + 6);
    var r = C.roofFront(ctx, { x0: x0 - 1.5, x1: x1 + 1.5, yE: yb - gh + 2, D: 34, R: 15, mat: 'tile', ov: 2, gmat: 'ashlar', gtex: { course: 5, joint: 10 } });
    s += r.svg + pennant(ctx, 24, r.apex[1] - 34, P.red);
    return s;
  }
  function towerRound(ctx) {
    var s = '', H = WALL_H, r = 19;
    s += C.groundShadow(5, 43, -2, -38);
    var T = C.roundTower(ctx, 24, -2, r, H + 24, 30, { mat: 'ashlar', roof: 'slate', ov: 3, tex: { course: 6, joint: 11 } });
    s += T.svg;
    s += C.win(ctx, 22.5, T.yt + 10, 3, 9, 'slit') + C.win(ctx, 13, T.yt + 30, 3, 8, 'slit') + C.win(ctx, 32, T.yt + 30, 3, 8, 'slit');
    s += C.line('M5 ' + f(T.yc - 6) + 'q19 ' + f(r * 0.55 * 2) + ' 38 0', 0.9, 0.6);
    return s;
  }
  function towerSquare(ctx) {
    var s = '', H = WALL_H, x0 = 6, x1 = 42, yb = -6, th = H + 18, dpt = 34, yE = yb - th;
    s += C.groundShadow(x0, x1, yb, -40);
    s += C.facade(ctx, x0, x1, yb, th, 'ashlar', { tex: { course: 6, joint: 12 } });
    var q = '';
    for (var y = yb; y > yE + 4; y -= 6) { var lw = ((Math.round((yb - y) / 6)) % 2) ? 4 : 7; q += C.rect(x0, y - 6, lw, 6, P.paper, 0.8) + C.rect(x1 - lw, y - 6, lw, 6, P.stone, 0.8); }
    s += q + C.rect(x0, yb - 5, x1 - x0, 5, P.stone3, 1);
    s += C.win(ctx, 22.5, yb - 26, 3, 9, 'slit') + C.win(ctx, 22.5, yb - 48, 3, 9, 'slit');
    s += corbels(x0, x1, yE + 6);
    // 塔顶平台与四面垛口
    var tx0 = x0 - 1.5, tx1 = x1 + 1.5, ty1 = yE - 4, ty0 = ty1 - dpt;
    s += C.rect(tx0, ty0, tx1 - tx0, dpt, WALK, 1.4);
    var m = '';
    for (var x = tx0 + 2; x < tx1 - 6; x += 9) m += C.rect(x, ty0 - 5, 6, 7, P.stone, 0.9);
    for (var yy = ty0 + 4; yy < ty1 - 6; yy += 9) m += C.rect(tx0, yy, 3.5, 7, P.stone, 0.9) + C.rect(tx1 - 3.5, yy, 3.5, 7, P.stone3, 0.9);
    s += m + pennant(ctx, 24, ty0 + dpt / 2, P.red);
    for (x = tx0 + 2; x < tx1 - 6; x += 9) s += C.rect(x, ty1 - 9, 6, 9, P.stone, 1) + C.line('M' + f(x) + ' ' + f(ty1 - 6.5) + 'h6', 0.7, 0.6);
    s += C.rect(tx0, ty1 - 3, tx1 - tx0, 3, P.stone, 1.2) + C.rect(tx0, ty1, tx1 - tx0, 2.5, P.stone2, 1);
    ctx.top(ty0 - 6);
    return s;
  }

  // ---------- 汇总 ----------
  var ROAD_KEYS = ['dirt', 'stone', 'highway'];
  function all(wrap) {
    var out = [], m;
    ROAD_KEYS.forEach(function (mat) {
      for (m = 0; m < 16; m++) {
        var id = 'west-common-road-' + mat + '-' + bin(m), ctx = new C.Ctx(id);
        var body = '<g transform="translate(0 -48)">' + roadTile(ctx, mat, m) + '</g>';
        out.push(wrap(id, [1, 1], body, -48, {
          id: id, style: 'west', race: 'common', category: 'road', kind: 'road_' + mat, facility: null, variant: m, mask: m,
          name: ROAD[mat].name + ' ' + bin(m), tags: ['dual_grid', 'mask_' + bin(m)], roof: 'none',
          note: m === 0 ? '空瓦片（透明占位）' : '双网格渲染瓦片：四角落在逻辑格中心'
        }));
      }
    });
    for (m = 0; m < 16; m++) {
      var wid = 'west-common-wall-' + bin(m), wctx = new C.Ctx(wid);
      var wb = '<g transform="translate(0 -48)">' + wallTile(wctx, m) + '</g>';
      out.push(wrap(wid, [1, 1], wb, m ? -48 - WALL_H - 7 : -48, {
        id: wid, style: 'west', race: 'common', category: 'wall', kind: 'wall_stone', facility: 'city_wall', variant: m, mask: m,
        name: '城墙 ' + bin(m), tags: ['dual_grid', 'mask_' + bin(m), 'crenellated'], roof: 'none',
        note: m === 0 ? '空瓦片（透明占位）' : '墙厚 24 px、高 ' + WALL_H + ' px，墙顶垛口'
      }));
    }
    var OV = [
      ['gate-h', gateH, 'gate', 'wall_gate_h', '城门（东西向墙段）', ['overlay', 'logical_cell', 'portcullis', 'gatehouse'], 'gable_tile', '放在东西向直墙的逻辑格上；门洞朝南北，带吊闸、突堞与四坡红瓦门楼'],
      ['gate-v', gateV, 'gate', 'wall_gate_v', '城门（南北向墙段）', ['overlay', 'logical_cell', 'gatehouse'], 'gable_tile', '放在南北向直墙的逻辑格上；门洞朝东西，正视只露两侧敞开的门扇'],
      ['tower-round', towerRound, 'watchtower', 'wall_tower_round', '圆塔楼', ['overlay', 'logical_cell', 'round_tower', 'cone_roof'], 'steep_slate', '放在墙的拐角或端点；锥形青石板顶'],
      ['tower-square', towerSquare, 'watchtower', 'wall_tower_square', '方塔楼', ['overlay', 'logical_cell', 'square_tower', 'crenellated'], 'none', '放在墙的拐角或端点；平顶垛口']
    ];
    OV.forEach(function (o, k) {
      var id = 'west-common-wall-' + o[0], ctx = new C.Ctx(id);
      var body = o[1](ctx);
      out.push(wrap(id, [1, 1], body, ctx.minY, {
        id: id, style: 'west', race: 'common', category: 'wall', kind: o[3], facility: o[2], variant: k + 1,
        name: o[4], tags: o[5], roof: o[6], note: o[7] + '。叠加件对齐逻辑格（不是渲染格），锚点 = 逻辑格前沿中点'
      }));
    });
    return out;
  }

  var API = {
    WALL_H: WALL_H, ROAD: ROAD, ROAD_KEYS: ROAD_KEYS, bin: bin, roadShape: roadShape, roadTile: roadTile,
    wallCells: wallCells, wallTile: wallTile, gateH: gateH, gateV: gateV, towerRound: towerRound, towerSquare: towerSquare, all: all
  };
  root.TownArtWB_tiles = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
