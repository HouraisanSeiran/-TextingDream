/*
 * 织梦 · 城镇西式精灵族素材 —— 小部件：叶片、藤蔓、尖弧拱门窗、月光石灯、藤编栏杆（美术样板，尚未接入游戏）
 * 局部坐标同 core.js（y = 0 为占地前沿，向上为负）。
 * 浏览器挂 window.TownArtWE_parts；Node 用 module.exports。依赖 core.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWE_core;
  var P = C.P, f = C.f, line = C.line, path = C.path, rect = C.rect;

  /** 长尖叶片：基点 (x,y)，长 len，方向角 ang（弧度，0 向右，-PI/2 向上），半宽 wid */
  function leafD(x, y, len, ang, wid) {
    var ca = Math.cos(ang), sa = Math.sin(ang), nx = -sa, ny = ca, w = (wid == null ? len * 0.3 : wid) * 1.6;
    var tx = x + ca * len, ty = y + sa * len, mx = x + ca * len * 0.45, my = y + sa * len * 0.45;
    return 'M' + f(x) + ' ' + f(y) + 'Q' + f(mx + nx * w) + ' ' + f(my + ny * w) + ' ' + f(tx) + ' ' + f(ty) +
      'Q' + f(mx - nx * w) + ' ' + f(my - ny * w) + ' ' + f(x) + ' ' + f(y) + 'Z';
  }
  function leaf(x, y, len, ang, fill, sw) { return path(leafD(x, y, len, ang), fill || P.leaf, sw == null ? 0.7 : sw); }

  /** 藤蔓：沿折线 pts 的平滑藤条，每隔 step 左右交替长一片叶 */
  function vine(ctx, pts, o) {
    o = o || {};
    var d = C.smooth(pts), s = line(d, o.sw || 1.4, 1, o.color || P.leaf2) + line(d, 0.5, 0.55);
    var step = o.step || 6, acc = 0, side = 1;
    for (var i = 0; i < pts.length - 1; i++) {
      var a = pts[i], b = pts[i + 1], dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1, ang = Math.atan2(dy, dx);
      var t = step - acc;
      if (t >= L) { acc += L; continue; }
      for (; t < L; t += step) {
        s += leaf(a[0] + dx * t / L, a[1] + dy * t / L, (o.len || 4.5) * ctx.rnd(0.8, 1.15), ang + side * ctx.rnd(0.7, 1.1),
          ctx.chance(0.7) ? P.leaf : P.moss, 0.5);
        side = -side;
      }
      acc = L - (t - step);
    }
    if (o.flowers) for (var k = 1; k < pts.length - 1; k += 2) s += C.circle(pts[k][0], pts[k][1], 1.3, P.silver, 0.6);
    return s;
  }

  /** 精灵尖弧拱（两段圆弧在顶上交成尖）：x 左，yb 底，w 宽，h 总高，k 拱高/宽 */
  function archD(x, yb, w, h, k) {
    k = k == null ? 0.62 : k;
    var rise = Math.min(h * 0.75, w * k), ys = yb - h + rise, xc = x + w / 2, r = w * 0.8;
    return 'M' + f(x) + ' ' + f(yb) + 'V' + f(ys) + 'A' + f(r) + ' ' + f(r) + ' 0 0 1 ' + f(xc) + ' ' + f(yb - h) +
      'A' + f(r) + ' ' + f(r) + ' 0 0 1 ' + f(x + w) + ' ' + f(ys) + 'V' + f(yb) + 'Z';
  }
  /** 尖弧拱窗：x 左，yb 窗台，w,h；o.lit 点灯（淡黄窗），o.frame 窗框色 */
  function win(ctx, x, yb, w, h, o) {
    o = o || {};
    var s = path(archD(x - 1.3, yb + 0.6, w + 2.6, h + 2.2), o.frame || P.silver2, 1);
    s += path(archD(x, yb, w, h), o.lit ? P.wash : P.glass, 0.8);
    s += line('M' + f(x + w / 2) + ' ' + f(yb - h + 1.2) + 'V' + f(yb) + (h > 9 ? 'M' + f(x) + ' ' + f(yb - h * 0.4) + 'H' + f(x + w) : ''),
      0.7, 0.9, o.lit ? P.dark : P.moon);
    s += rect(x - 1.8, yb, w + 3.6, 1.8, P.silver3, 0.8);
    return s;
  }
  /** 圆窗（月窗）：中心 cx,cy，半径 r，四瓣窗棂 */
  function roundWin(ctx, cx, cy, r, o) {
    o = o || {};
    var s = C.circle(cx, cy, r + 1.4, o.frame || P.silver2, 1) + C.circle(cx, cy, r, o.lit ? P.wash : P.glass, 0.8);
    s += path(leafD(cx, cy + r * 0.85, r * 1.7, -Math.PI / 2, r * 0.32), 'none', 0) +
      line(leafD(cx, cy + r * 0.85, r * 1.7, -Math.PI / 2, r * 0.32) + 'M' + f(cx - r) + ' ' + f(cy) + 'H' + f(cx + r), 0.7, 0.9, o.lit ? P.dark : P.moon);
    return s;
  }
  /** 尖弧拱门：x 左，yb 门槛，w,h；o.fill 门板色，o.surround 门套，o.step 台阶，o.open 敞开（只画暗门洞） */
  function door(ctx, x, yb, w, h, o) {
    o = o || {};
    var d = archD(x, yb, w, h, 0.72), s = '', t = '';
    if (o.surround !== false) s += path(archD(x - 2.2, yb, w + 4.4, h + 2.6, 0.72), o.frame || P.silver2, 1.2);
    if (o.open) return s + path(d, '#3b2d1f', 1.2) + (o.step ? rect(x - 2.5, yb - 1.6, w + 5, 2.2, P.stone2, 0.9) : '');
    for (var xx = x + 2.4; xx < x + w - 1; xx += 2.6) t += 'M' + f(xx) + ' ' + f(yb - h) + 'V' + f(yb);
    var hinge = path(leafD(x + 0.4, yb - h * 0.3, w * 0.55, 0, 1.1) + leafD(x + 0.4, yb - h * 0.72, w * 0.5, 0, 1.1), P.moss, 0.6);
    s += path(d, o.fill || P.bark, 0) + C.clipped(ctx, d, line(t, 0.6, 0.5) + hinge) + path(d, 'none', 1.3);
    s += C.circle(x + w * 0.8, yb - h * 0.42, 0.9, P.moon, 0.5);
    if (o.step) s += rect(x - 2.5, yb - 1.6, w + 5, 2.2, P.stone2, 0.9);
    return s;
  }

  /** 月光石灯柱：x 柱脚，yb 地面，h 柱高，side 灯钩朝向 ±1 */
  function lamp(ctx, x, yb, h, side) {
    side = side || 1;
    var yt = yb - h, s = C.ellShadow(x + 2, yb - 0.6, 3, 1.2), hx = x + side * 5.5;
    var d = 'M' + f(x) + ' ' + f(yb) + 'C' + f(x - 0.8) + ' ' + f(yb - h * 0.5) + ' ' + f(x + 0.8) + ' ' + f(yt + 6) + ' ' + f(x) + ' ' + f(yt + 2) +
      'C' + f(x) + ' ' + f(yt - 2.5) + ' ' + f(hx) + ' ' + f(yt - 2.5) + ' ' + f(hx) + ' ' + f(yt + 1);
    s += rect(x - 2, yb - 2, 4, 2, P.stone2, 0.8);
    s += line(d, 2.8, 1) + line(d, 1.4, 1, P.silver);
    s += leaf(x, yt + 4, 4, -Math.PI / 2 - side * 0.9, P.leaf, 0.5);
    var sy = yt + 2.5;
    s += path('M' + f(hx) + ' ' + f(sy) + 'q2.6 2.4 0 6.6q-2.6 -4.2 0 -6.6Z', P.moon, 0.9);
    s += line('M' + f(hx) + ' ' + f(sy + 1.2) + 'v4M' + f(hx - 3.6) + ' ' + f(sy + 3.4) + 'h-1.6M' + f(hx + 3.6) + ' ' + f(sy + 3.4) + 'h1.6', 0.6, 0.6);
    ctx.top(yt - 3);
    return s;
  }

  /** 藤编栏杆：沿立柱点列 pts（地面/台面上的点），高 h；横编两道藤、扶手为银白木，偶尔挂叶 */
  function railPts(ctx, pts, h, o) {
    o = o || {};
    var posts = '', weave = '', tops = [], s = '';
    pts.forEach(function (p) { posts += 'M' + f(p[0]) + ' ' + f(p[1]) + 'V' + f(p[1] - h); tops.push([p[0], p[1] - h]); });
    for (var i = 0; i < pts.length - 1; i++) {
      var a = pts[i], b = pts[i + 1], mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
      weave += 'M' + f(a[0]) + ' ' + f(a[1] - h * 0.25) + 'Q' + f(mx) + ' ' + f(my - h * 0.95) + ' ' + f(b[0]) + ' ' + f(b[1] - h * 0.25) +
        'M' + f(a[0]) + ' ' + f(a[1] - h * 0.75) + 'Q' + f(mx) + ' ' + f(my - h * 0.05) + ' ' + f(b[0]) + ' ' + f(b[1] - h * 0.75);
    }
    s += line(weave, 1.1, 1, P.bark2) + line(weave, 0.4, 0.5);
    s += line(posts, 2, 1) + line(posts, 0.9, 1, P.silver);
    var top = C.smooth(tops);
    s += line(top, 2.6, 1) + line(top, 1.3, 1, P.silver);
    if (o.leaves !== false) for (i = 0; i < pts.length - 1; i++) {
      if (!ctx.chance(o.leafP == null ? 0.45 : o.leafP)) continue;
      var q = ctx.rnd(0.25, 0.75), lx = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * q, ly = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * q - h + 0.6;
      s += leaf(lx, ly, 3.6, Math.PI / 2 + ctx.rnd(-0.6, 0.6), P.leaf, 0.5);
    }
    return s;
  }
  /** 直栏杆 x0..x1，地面 yb */
  function rail(ctx, x0, x1, yb, h, o) {
    var n = Math.max(1, Math.round((x1 - x0) / 8)), pts = [];
    for (var i = 0; i <= n; i++) pts.push([x0 + (x1 - x0) * i / n, yb]);
    return railPts(ctx, pts, h, o);
  }
  /** 椭圆弧栏杆：中心 cx,cy，半轴 rx,ry，角度 a0..a1（弧度，0 = 右，PI/2 = 前） */
  function railArc(ctx, cx, cy, rx, ry, a0, a1, h, o) {
    var n = Math.max(2, Math.round(Math.abs(a1 - a0) * (rx + ry) / 2 / 8)), pts = [];
    for (var i = 0; i <= n; i++) { var a = a0 + (a1 - a0) * i / n; pts.push([cx + Math.cos(a) * rx, cy + Math.sin(a) * ry]); }
    return railPts(ctx, pts, h, o);
  }

  var API = {
    leafD: leafD, leaf: leaf, vine: vine, archD: archD, win: win, roundWin: roundWin, door: door, lamp: lamp,
    railPts: railPts, rail: rail, railArc: railArc
  };
  root.TownArtWE_parts = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
