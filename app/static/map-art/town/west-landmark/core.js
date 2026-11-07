/*
 * 织梦 · 西式文化地标：共用画笔 core.js（3/4 斜俯视，木刻线描 + 羊皮纸淡彩；美术样板，尚未接入游戏）
 *
 * 投影约定与 docs/town-art-spec.md、west-special/prims.js 一致：地面格 48 px 正方形，地面进深不压缩，
 * 地面点 (x, g) 在高度 h 处画到屏幕 (x, up + g - h)。
 *   坡屋顶（屋脊平行正面）：前檐 yE，后檐 yE - dg，屋脊 yE - dg/2 - rise。
 *   山墙朝前：屋脊从 (cx, yE - rise) 向后延伸 dg。
 * 光从左上来：左面 / 左坡偏亮，右侧偏暗，投影落右下。
 * 浏览器挂 window.TownArtWL_core；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var CELL = 48;
  var C = {
    ink: '#4a3826', paper: '#efdfb2', plaster: '#e9dcc0', wash: '#e3c47a', wood: '#c9a46a',
    stone: '#cfc0a2', stone2: '#bfb093', stone3: '#b1a287', beam: '#8a6a44', dark: '#6b4f32',
    tile: '#b5654a', red: '#9a3b2a', slate: '#7d8790', slate2: '#5f6870',
    thatch: '#d2b46c', thatch2: '#b8954e', grass: '#c9c79a', shadow: '#3a2c1e',
    // 规范色表外的补色（README 说明）：岩石暗面、植物、水面（同 special-infra 西式水色）、沙
    rock: '#a49678', leaf: '#8f9a5c', leaf2: '#76814b', water: '#a9b8ad', water2: '#8fa49a', sand: '#dccb9c'
  };
  var MAT = {
    tile: { fill: C.tile, back: '#a0553d', row: 5, ink: 0.42 },
    slate: { fill: C.slate, back: C.slate2, row: 4, ink: 0.45 },
    lead: { fill: '#8f989c', back: '#6f787d', row: 6, ink: 0.4 },
    shingle: { fill: C.wood, back: C.beam, row: 5, ink: 0.42 },
    stone: { fill: C.stone, back: C.stone3, row: 6, ink: 0.4 }
  };

  function f(n) { return String(Math.round(n * 100) / 100); }
  function rng(seed) { // mulberry32
    return function () {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      var t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  function lerp(a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]; }
  function pd(pts, open) {
    var s = '';
    for (var i = 0; i < pts.length; i++) s += (i ? 'L' : 'M') + f(pts[i][0]) + ' ' + f(pts[i][1]);
    return open ? s : s + 'Z';
  }
  function seg(x1, y1, x2, y2) { return 'M' + f(x1) + ' ' + f(y1) + 'L' + f(x2) + ' ' + f(y2); }
  function at(fill, sw, extra) {
    return 'fill="' + fill + '"' + (sw === 0 ? '' : ' stroke="' + C.ink + '" stroke-width="' + f(sw == null ? 1.6 : sw) +
      '" stroke-linejoin="round" stroke-linecap="round"') + (extra ? ' ' + extra : '');
  }
  function poly(pts, fill, sw, extra) { return '<path d="' + pd(pts) + '" ' + at(fill, sw, extra) + '/>'; }
  function path(d, fill, sw, extra) { return '<path d="' + d + '" ' + at(fill, sw, extra) + '/>'; }
  function rect(x, y, w, h, fill, sw, extra) { return poly([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], fill, sw, extra); }
  function circle(cx, cy, r, fill, sw, extra) {
    return '<circle cx="' + f(cx) + '" cy="' + f(cy) + '" r="' + f(r) + '" ' + at(fill, sw, extra) + '/>';
  }
  function ellipse(cx, cy, rx, ry, fill, sw, extra) {
    return '<ellipse cx="' + f(cx) + '" cy="' + f(cy) + '" rx="' + f(rx) + '" ry="' + f(ry) + '" ' + at(fill, sw, extra) + '/>';
  }
  /** 细线（不填充） */
  function ln(d, sw, op, color) {
    if (!d) return '';
    return '<path d="' + d + '" fill="none" stroke="' + (color || C.ink) + '" stroke-width="' + f(sw || 0.8) +
      '" stroke-linecap="round" stroke-linejoin="round"' + (op != null && op < 1 ? ' stroke-opacity="' + f(op) + '"' : '') + '/>';
  }
  function flat(pts, fill, op) {
    return '<path d="' + pd(pts) + '" fill="' + fill + '"' + (op != null && op < 1 ? ' fill-opacity="' + f(op) + '"' : '') + '/>';
  }
  function flatD(d, fill, op) {
    return '<path d="' + d + '" fill="' + fill + '"' + (op != null && op < 1 ? ' fill-opacity="' + f(op) + '"' : '') + '/>';
  }
  /** 投影：半透明暗色平涂（西式 #3a2c1e / 0.18） */
  function shade(pts, op) { return flat(pts, C.shadow, op == null ? 0.18 : op); }
  /** 方盒投影：地面范围 x0..x1、后沿 yb、前沿 yf；向右伸 s，向下最多 4 px（不超出 H） */
  function boxShadow(x0, x1, yb, yf, s, W, H) {
    var dn = Math.min(4, H - yf), sx = Math.max(0, Math.min(s, W - x1 - 0.5));
    return shade([[x0 + 4, yf], [x0 + 4 + dn, yf + dn], [x1 + sx, yf + dn], [x1 + sx, yb + sx * 0.7], [x1, yb]]);
  }

  /** 一块坡面：A→B 檐口，D→C 屋脊一侧。平涂 + 平行檐口的瓦行线 + 错缝短线 */
  function slope(A, B, C2, D, mat, dark) {
    var m = MAT[mat] || MAT.tile, s = poly([A, B, C2, D], dark ? m.back : m.fill, 1.4);
    var len = Math.hypot(D[0] - A[0], D[1] - A[1]), n = Math.max(2, Math.round(len / m.row)), d = '', tk = '';
    var w = Math.hypot(B[0] - A[0], B[1] - A[1]);
    for (var i = 1; i < n; i++) {
      var t = i / n, P = lerp(A, D, t), Q = lerp(B, C2, t);
      d += seg(P[0], P[1], Q[0], Q[1]);
      var P0 = lerp(A, D, (i - 1) / n), Q0 = lerp(B, C2, (i - 1) / n), k = Math.max(1, Math.round(w * (1 - t * 0.5) / 7));
      for (var j = 0; j < k; j++) {
        var u = (j + (i % 2 ? 0.25 : 0.75)) / k, a = lerp(P0, Q0, u), b = lerp(P, Q, u);
        tk += seg(a[0], a[1], b[0], b[1]);
      }
    }
    return s + ln(d, 0.8, m.ink) + ln(tk, 0.7, m.ink * 0.85);
  }

  /** 石砌 / 砖砌层缝：层高 ch，竖缝间距约 bw，逐层错缝 */
  function courses(x0, x1, yt, yb, ch, rnd, bw) {
    var d = '', v = '', row = 0, y;
    for (y = yb - ch; y > yt + 1.5; y -= ch) d += seg(x0 + 0.8, y, x1 - 0.8, y);
    for (y = yb; y > yt + 0.5; y -= ch, row++) {
      var top = Math.max(yt, y - ch), x = x0 + (row % 2 ? bw * 0.5 : bw * 0.95) + (rnd() - 0.5) * 2;
      for (; x < x1 - 2.5; x += bw * (0.8 + rnd() * 0.45)) v += seg(x, top + 0.5, x, y - 0.5);
    }
    return ln(d, 0.8, 0.5) + ln(v, 0.7, 0.42);
  }
  /** 正立面墙。kind: plaster | stone | ashlar | brick | timber；opt.fill / plinth / ch / noShade */
  function wall(x0, x1, yt, yb, kind, rnd, opt) {
    opt = opt || {};
    var fills = { plaster: C.plaster, timber: C.plaster, stone: C.stone, ashlar: C.stone, brick: C.stone2 };
    var o = rect(x0, yt, x1 - x0, yb - yt, opt.fill || fills[kind] || C.plaster, opt.sw || 1.8);
    if (kind === 'stone') o += courses(x0, x1, yt, yb, opt.ch || 6, rnd, 9);
    if (kind === 'ashlar') o += courses(x0, x1, yt, yb, opt.ch || 7, rnd, 15);
    if (kind === 'brick') o += courses(x0, x1, yt, yb, opt.ch || 4, rnd, 7);
    if (kind === 'timber') {
      var td = '', n = opt.bays || 3, bw = (x1 - x0) / n;
      for (var i = 1; i < n; i++) td += seg(x0 + bw * i, yt, x0 + bw * i, yb);
      td += seg(x0 + 1, yb - 1, x0 + bw - 1, yt + 1) + seg(x1 - 1, yb - 1, x1 - bw + 1, yt + 1);
      o += ln(td, 2.2, 1, C.beam);
    }
    if (opt.plinth) o += rect(x0, yb - opt.plinth, x1 - x0, opt.plinth, C.stone2, 1.4) + courses(x0, x1, yb - opt.plinth, yb, opt.plinth, rnd, 10);
    if (!opt.noShade) {
      o += flat([[x0 + 1, yt + 0.8], [x1 - 1, yt + 0.8], [x1 - 1, yt + 4.5], [x0 + 1, yt + 3.5]], C.shadow, 0.16);
      o += flat([[x1 - 3.5, yt + 1], [x1 - 1, yt + 1], [x1 - 1, yb - 1], [x1 - 3.5, yb - 1]], C.shadow, 0.12);
    }
    return o;
  }

  // ——————————————————— 门窗 / 拱 ———————————————————
  function archPath(x, y, w, h) { // y = 拱顶，半圆拱
    var r = w / 2;
    return 'M' + f(x) + ' ' + f(y + h) + 'L' + f(x) + ' ' + f(y + r) + 'A' + f(r) + ' ' + f(r) + ' 0 0 1 ' + f(x + w) + ' ' + f(y + r) + 'L' + f(x + w) + ' ' + f(y + h) + 'Z';
  }
  function pointPath(x, y, w, h) { // 尖拱（哥特）
    var m = x + w / 2, s = Math.min(h * 0.45, w * 0.9);
    return 'M' + f(x) + ' ' + f(y + h) + 'L' + f(x) + ' ' + f(y + s) + 'Q' + f(x) + ' ' + f(y + s * 0.25) + ' ' + f(m) + ' ' + f(y) +
      'Q' + f(x + w) + ' ' + f(y + s * 0.25) + ' ' + f(x + w) + ' ' + f(y + s) + 'L' + f(x + w) + ' ' + f(y + h) + 'Z';
  }
  /** 窗：x,y 左上；shape rect | arch | point；panes 窗棂；glass 玻璃色；stain 彩窗（红/蓝小块） */
  function win(x, y, w, h, opt) {
    opt = opt || {};
    var o = '', d = opt.shape === 'arch' ? archPath(x, y, w, h) : opt.shape === 'point' ? pointPath(x, y, w, h) : pd([[x, y], [x + w, y], [x + w, y + h], [x, y + h]]);
    o += path(d, opt.glass || C.dark, opt.sw || 1.3);
    if (opt.stain && w >= 5 && h >= 10) {
      var ky = y + w * 0.6, kh = (y + h - ky - 1) / 3;
      for (var i = 0; i < 3; i++) o += rect(x + w * 0.22, ky + i * kh + 0.6, w * 0.56, kh - 1.2, i % 2 ? C.slate : C.red, 0, 'fill-opacity="0.85"');
    }
    var top = opt.shape ? y + w * 0.5 : y + 1;
    if (opt.panes !== false) o += ln(seg(x + w / 2, y + 1.2, x + w / 2, y + h - 0.8) + (h > 8 ? seg(x + 0.8, top + (y + h - top) * 0.42, x + w - 0.8, top + (y + h - top) * 0.42) : ''), 0.8, 0.85, C.wash);
    if (opt.sill !== false) o += ln(seg(x - 1.2, y + h + 0.6, x + w + 1.2, y + h + 0.6), 1.3, 1);
    return o;
  }
  /** 门：cx 中线，yb 门槛；shape arch / point / rect；open 画成黑洞；frame 门框色 */
  function door(cx, yb, w, h, opt) {
    opt = opt || {};
    var x = cx - w / 2, y = yb - h, o = '';
    var d = opt.shape === 'arch' ? archPath(x, y, w, h) : opt.shape === 'point' ? pointPath(x, y, w, h) : pd([[x, y], [x + w, y], [x + w, yb], [x, yb]]);
    if (opt.frame) o += path(opt.shape === 'arch' ? archPath(x - 2, y - 2, w + 4, h + 2) : opt.shape === 'point' ? pointPath(x - 2, y - 2, w + 4, h + 2) : pd([[x - 2, y - 2], [x + w + 2, y - 2], [x + w + 2, yb], [x - 2, yb]]), opt.frame, 1.3);
    o += path(d, opt.open ? C.dark : (opt.fill || C.beam), 1.5);
    if (!opt.open) {
      var v = '';
      for (var i = 1; i < 4; i++) v += seg(x + w * i / 4, y + (opt.shape ? w * 0.25 : 1), x + w * i / 4, yb - 0.5);
      o += ln(v, 0.8, 0.55) + ln(seg(x + 1, yb - h * 0.3, x + w - 1, yb - h * 0.3) + seg(x + 1, yb - h * 0.72, x + w - 1, yb - h * 0.72), 1.1, 0.7, C.dark);
    }
    return o;
  }
  /** 一排连续拱券（拱廊 / 引水渠 / 斗兽场层）：x0..x1 内 n 个拱，拱墩宽 pw，拱脚 ys，地坪 yb；arch 半圆或 point */
  function arcade(x0, x1, ys, yb, n, pw, opt) {
    opt = opt || {};
    var o = '', sp = (x1 - x0 - pw) / n, aw = sp - pw;
    for (var i = 0; i < n; i++) {
      var ax = x0 + pw + i * sp, ay = ys - aw / 2;
      var d = opt.shape === 'point' ? pointPath(ax, ys - aw * 0.8, aw, yb - ys + aw * 0.8) : archPath(ax, ay, aw, yb - ay);
      o += path(d, opt.fill || C.dark, opt.sw || 1.2);
      if (opt.voussoir) { // 拱券石：放射短线
        var r = aw / 2, cx = ax + r, dv = '';
        for (var k = 1; k < 6; k++) { var a = Math.PI + Math.PI * k / 6; dv += seg(cx + Math.cos(a) * r, ys + Math.sin(a) * r, cx + Math.cos(a) * (r + 3.2), ys + Math.sin(a) * (r + 3.2)); }
        o += ln(dv, 0.7, 0.55);
      }
      if (opt.inner) o += opt.inner(ax, ys, aw, yb);
    }
    return o;
  }
  /** 圆柱（古典）：cx 中线，yb 柱础底，h 高，r 半径；带柱础、柱头、凹槽线 */
  function column(cx, yb, h, r, opt) {
    opt = opt || {};
    var yt = yb - h, o = '';
    o += rect(cx - r * 1.45, yb - 2.6, r * 2.9, 2.6, C.stone2, 1);
    o += rect(cx - r, yt + 2.8, r * 2, h - 5.4, opt.fill || C.paper, 1.2);
    var fl = '';
    for (var k = -1; k <= 1; k++) if (k) fl += seg(cx + k * r * 0.45, yt + 4, cx + k * r * 0.45, yb - 3.5);
    o += ln(fl, 0.6, 0.45);
    o += flat([[cx + r * 0.35, yt + 3], [cx + r - 0.4, yt + 3], [cx + r - 0.4, yb - 3], [cx + r * 0.35, yb - 3]], C.shadow, 0.13);
    o += rect(cx - r * 1.5, yt, r * 3, 2.8, C.stone, 1);
    if (opt.ionic) o += circle(cx - r * 1.3, yt + 2, 1.1, C.stone2, 0.6) + circle(cx + r * 1.3, yt + 2, 1.1, C.stone2, 0.6);
    return o;
  }
  /** 古典山花（三角楣）：x0..x1 底，yb 底线，h 高；内含檐口与一道山花内框 */
  function pediment(x0, x1, yb, h, rnd, opt) {
    opt = opt || {};
    var cx = (x0 + x1) / 2, o = poly([[x0, yb], [cx, yb - h], [x1, yb]], opt.fill || C.paper, 1.6);
    o += ln(pd([[x0 + 6, yb - 2.2], [cx, yb - h + 3.6], [x1 - 6, yb - 2.2]], true), 0.9, 0.6);
    if (opt.relief) o += circle(cx, yb - h * 0.36, h * 0.15, C.stone2, 0.9) + ln(seg(cx - h * 0.55, yb - 4, cx - h * 0.25, yb - h * 0.3) + seg(cx + h * 0.55, yb - 4, cx + h * 0.25, yb - h * 0.3), 0.8, 0.6);
    o += rect(x0 - 2, yb, x1 - x0 + 4, 3.4, C.stone, 1.3);
    return o;
  }
  /** 十字：竖杆顶 (x,yt) 起 h 高 */
  function cross(x, yt, h) {
    var d = seg(x, yt, x, yt + h) + seg(x - h * 0.32, yt + h * 0.32, x + h * 0.32, yt + h * 0.32);
    return ln(d, 2.8, 1, C.ink) + ln(d, 1.2, 1, C.wash);
  }
  /** 尖顶小饰（finial）：杆 + 金球 */
  function finial(x, y, h) { return ln(seg(x, y, x, y - (h || 6)), 1.4, 1) + circle(x, y - (h || 6) - 0.5, 1.4, C.wash, 0.9); }
  /** 旗：杆底 (x,yb)，杆高 h，旗宽 w */
  function flag(x, yb, h, w, color) {
    var t = yb - h, o = ln(seg(x, yb, x, t - 2), 1.3, 1);
    o += path('M' + f(x) + ' ' + f(t) + 'Q' + f(x + w * 0.5) + ' ' + f(t - 2) + ' ' + f(x + w) + ' ' + f(t + 1) + 'L' + f(x + w * 0.82) + ' ' + f(t + 3.5) +
      'L' + f(x + w) + ' ' + f(t + 6) + 'Q' + f(x + w * 0.5) + ' ' + f(t + 4.5) + ' ' + f(x) + ' ' + f(t + 6) + 'Z', color || C.red, 1);
    return o + circle(x, t - 2.5, 1.1, C.wash, 0.8);
  }
  /** 玫瑰窗：石框 + 深色玻璃 + 彩色花瓣 + 放射窗棂 */
  function roseWindow(cx, cy, R, petals) {
    var n = petals || 8, o = circle(cx, cy, R + 3, C.stone3, 1.5) + circle(cx, cy, R, C.dark, 1.2), d = '';
    for (var i = 0; i < n; i++) {
      var a = i * 2 * Math.PI / n - Math.PI / 2, ca = Math.cos(a), sa = Math.sin(a);
      o += circle(cx + ca * R * 0.64, cy + sa * R * 0.64, R * (n > 8 ? 0.2 : 0.25), i % 2 ? C.red : C.slate, 0.7);
      d += seg(cx + ca * R * 0.24, cy + sa * R * 0.24, cx + ca * R * 0.96, cy + sa * R * 0.96);
    }
    return o + ln(d, 1, 0.9, C.wash) + circle(cx, cy, R * 0.24, C.wash, 0.9) + ring(cx, cy, R, 1.4, 1);
  }
  function ring(cx, cy, r, sw, op, color) {
    return '<circle cx="' + f(cx) + '" cy="' + f(cy) + '" r="' + f(r) + '" fill="none" stroke="' + (color || C.ink) + '" stroke-width="' + f(sw || 1) + '"' +
      (op != null && op < 1 ? ' stroke-opacity="' + f(op) + '"' : '') + '/>';
  }

  // ——————————————————— 屋顶 ———————————————————
  function fascia(a, b, y, t) { return rect(a, y, b - a, t || 2.4, C.dark, 1.1); }
  /** 坡屋顶，屋脊平行正面：x0..x1 墙宽，yE 前檐，dg 地面进深，rise 屋脊抬升 */
  function gableRoof(x0, x1, yE, dg, rise, mat, opt) {
    opt = opt || {};
    var ov = opt.ov == null ? 3 : opt.ov, yR = yE - dg / 2 - rise, yB = yE - dg - 1, a = x0 - ov, b = x1 + ov, o = '';
    if (yB < yR - 0.5) o += slope([a, yB], [b, yB], [b, yR], [a, yR], mat, true);
    o += slope([a, yE + 1], [b, yE + 1], [b, yR], [a, yR], mat, false);
    o += fascia(a, b, yE + 0.5, 2.2) + ln(seg(a, yR, b, yR), 2.2, 1);
    return o;
  }
  /** 山墙朝前：返回 { roof, gable }，gable 盖在墙之上画 */
  function gableFront(x0, x1, yE, dg, rise, mat, opt) {
    opt = opt || {};
    var ov = opt.ov == null ? 3 : opt.ov, cx = (x0 + x1) / 2, yA = yE - rise;
    var roof = slope([x0 - ov, yE + ov * 0.6], [x0 - ov, yE - dg + ov * 0.6], [cx, yA - dg], [cx, yA], mat, false) +
      slope([x1 + ov, yE + ov * 0.6], [x1 + ov, yE - dg + ov * 0.6], [cx, yA - dg], [cx, yA], mat, true) +
      ln(seg(cx, yA, cx, yA - dg), 2, 1);
    var gable = poly([[x0, yE], [cx, yA + 1], [x1, yE]], opt.fill || C.plaster, 1.6);
    gable += ln(seg(x0 - ov, yE + ov * 0.6, cx, yA - 0.6) + seg(cx, yA - 0.6, x1 + ov, yE + ov * 0.6), 3, 1, C.dark) +
      ln(seg(x0 - ov, yE + ov * 0.6, cx, yA - 0.6) + seg(cx, yA - 0.6, x1 + ov, yE + ov * 0.6), 1, 0.8, C.ink);
    return { roof: roof, gable: gable };
  }
  /** 四坡顶 */
  function hipRoof(x0, x1, yE, dg, rise, mat, opt) {
    opt = opt || {};
    var ov = opt.ov == null ? 3 : opt.ov, a = x0 - ov, b = x1 + ov, yR = yE - dg / 2 - rise, yB = yE - dg - 1;
    var hp = opt.hip == null ? Math.min(dg * 0.5, (x1 - x0) * 0.32) : opt.hip, o = '', L = [a + hp, yR], R = [b - hp, yR];
    if (yB < yR - 0.5) o += slope([a, yB], [b, yB], R, L, mat, true);
    o += slope([a, yE + 1], [a, yB], L, L, mat, false) + slope([b, yE + 1], [b, yB], R, R, mat, true);
    o += slope([a, yE + 1], [b, yE + 1], R, L, mat, false);
    return o + fascia(a, b, yE + 0.5, 2.2) + ln(seg(L[0], L[1], R[0], R[1]), 2.2, 1);
  }
  /** 四角攒尖（方塔尖顶）：塔顶面 x0..x1 × (yE-dg..yE)，尖高 h */
  function pyramid(x0, x1, yE, dg, h, mat, opt) {
    opt = opt || {};
    var ov = opt.ov == null ? 2 : opt.ov, a = x0 - ov, b = x1 + ov, cx = (x0 + x1) / 2, ap = [cx, yE - dg / 2 - h];
    var o = slope([a, yE + 1], [a, yE - dg], ap, ap, mat, false) + slope([b, yE + 1], [b, yE - dg], ap, ap, mat, true) +
      slope([a, yE + 1], [b, yE + 1], [cx + (b - cx) * 0.02, ap[1]], ap, mat, false);
    o += flat([[cx, yE + 1], [b, yE + 1], ap], C.shadow, 0.14);
    if (opt.finial !== false) o += finial(ap[0], ap[1], 6);
    return o;
  }
  /** 圆锥顶：底椭圆半径 r（扁度 0.5），尖高 h；mat 取 MAT 色 */
  function cone(cx, yb, r, h, mat, opt) {
    opt = opt || {};
    var m = MAT[mat] || MAT.slate, ry = r * 0.5, ap = f(cx) + ' ' + f(yb - h), o = '', ov = opt.ov == null ? 1.5 : opt.ov, R = r + ov;
    o += path('M' + f(cx - R) + ' ' + f(yb) + 'L' + ap + 'L' + f(cx + R) + ' ' + f(yb) + 'A' + f(R) + ' ' + f(ry) + ' 0 0 1 ' + f(cx - R) + ' ' + f(yb) + 'Z', m.fill, 1.5);
    o += flat([[cx + R * 0.22, yb + ry * 0.97], [cx, yb - h], [cx + R, yb]], m.back, 1);
    var d = '', n = Math.max(4, Math.round(h / 7));
    for (var i = 1; i < n; i++) {
      var t = i / n, y = yb - h * (1 - t);
      d += 'M' + f(cx - R * t) + ' ' + f(y) + 'A' + f(R * t) + ' ' + f(ry * t) + ' 0 0 0 ' + f(cx + R * t) + ' ' + f(y);
    }
    o += ln(d, 0.75, m.ink) + ln('M' + f(cx - R) + ' ' + f(yb) + 'A' + f(R) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + R) + ' ' + f(yb), 1.6, 1);
    if (opt.finial !== false) o += finial(cx, yb - h, opt.fh || 6);
    if (opt.flag) o += flag(cx, yb - h - 2, 12, 9, opt.flag);
    return o;
  }
  /** 圆柱（圆塔）：前面 + 顶椭圆。kind: stone | ashlar | plain；opt.top 顶面 false 不画 */
  function cylinder(cx, yb, r, h, fill, kind, rnd, opt) {
    opt = opt || {};
    var ry = r * 0.5, yt = yb - h, x0 = cx - r, x1 = cx + r, o = '';
    o += path('M' + f(x0) + ' ' + f(yt) + 'L' + f(x0) + ' ' + f(yb) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 0 ' + f(x1) + ' ' + f(yb) + 'L' + f(x1) + ' ' + f(yt) + 'Z', fill, 1.6);
    o += flat([[cx + r * 0.5, yt], [x1, yt], [x1, yb], [cx + r * 0.5, yb + ry * 0.86]], C.shadow, 0.14);
    if (kind !== 'plain' && rnd) {
      var ch = kind === 'ashlar' ? 7 : 6, d = '', v = '', row = 0;
      for (var y = yb - ch; y > yt + 2; y -= ch, row++) {
        d += 'M' + f(x0) + ' ' + f(y) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 0 ' + f(x1) + ' ' + f(y);
        for (var k = -3; k <= 3; k++) {
          var u = (k + (row % 2 ? 0.5 : 0)) / (kind === 'ashlar' ? 3 : 3.6); if (Math.abs(u) > 0.92) continue;
          var vx = cx + u * r, dy = ry * Math.sqrt(1 - u * u);
          v += seg(vx, y + dy + 0.5, vx, y + dy + ch - 0.5);
        }
      }
      o += ln(d, 0.75, 0.48) + ln(v, 0.65, 0.4);
    }
    if (opt.top !== false) o += ellipse(cx, yt, r, ry, opt.topFill || fill, 1.4);
    return o;
  }
  /** 方盒：正面 x0..x1 × (yf-h..yf)，顶面向后 dg */
  function box(x0, x1, yf, dg, h, front, top, sw) {
    return poly([[x0, yf - h], [x1, yf - h], [x1, yf - h - dg], [x0, yf - h - dg]], top || front, sw || 1.4) +
      rect(x0, yf - h, x1 - x0, h, front, sw || 1.4);
  }
  /** 垛口一排：x0..x1，墙顶 y，齿宽 mw，间隔 gap */
  function merlons(x0, x1, y, mw, gap, fill) {
    var o = '', n = Math.max(2, Math.round((x1 - x0 + gap) / (mw + gap))), st = (x1 - x0 - mw) / (n - 1);
    for (var i = 0; i < n; i++) o += box(x0 + i * st, x0 + i * st + mw, y, 2.5, 5, fill || C.stone, C.stone3, 1.1);
    return o;
  }
  /** 圆塔顶一圈垛口（沿前半椭圆排） */
  function ringMerlons(cx, y, r, n, fill) {
    var o = '';
    for (var i = 0; i < n; i++) {
      var u = -0.86 + 1.72 * i / (n - 1), x = cx + u * r, dy = r * 0.5 * Math.sqrt(1 - u * u);
      o += box(x - 2.2, x + 2.2, y + dy, 2, 5, fill || C.stone, C.stone3, 1);
    }
    return o;
  }
  /** 扶壁：x 左缘，宽 w，yb 地面，yt 顶 */
  function buttress(x, yb, yt, w) {
    w = w || 7;
    return rect(x, yt + 8, w, yb - yt - 8, C.stone2, 1.3) + poly([[x - 0.5, yt + 8], [x + w + 0.5, yt + 8], [x + w / 2, yt]], C.stone3, 1.2) +
      rect(x - 1.5, yb - 24, w + 3, 24, C.stone2, 1.3) + poly([[x - 1.5, yb - 24], [x + w + 1.5, yb - 24], [x + w, yb - 29], [x, yb - 29]], C.stone3, 1.2);
  }
  /** 小尖塔（pinnacle）：x 中线，yb 底，h 高 */
  function pinnacle(x, yb, h, w) {
    w = w || 5;
    return rect(x - w / 2, yb - h * 0.45, w, h * 0.45, C.stone, 1.1) + poly([[x - w / 2 - 0.5, yb - h * 0.45], [x + w / 2 + 0.5, yb - h * 0.45], [x, yb - h]], C.stone3, 1) +
      ln(seg(x - w * 0.25, yb - h * 0.62, x - w * 0.6, yb - h * 0.66) + seg(x + w * 0.25, yb - h * 0.78, x + w * 0.6, yb - h * 0.82), 0.8, 0.7);
  }

  // ——————————————————— 地形与植物 ———————————————————
  /**
   * 岩石山体：pts 为外轮廓（顺时针，大致凸），平涂暖灰 + 右侧面暗块 + 裂隙排线 + 层理短线。
   * 光从左上：轮廓顶点在质心右侧的面压暗一档。
   */
  function crag(pts, rnd, opt) {
    opt = opt || {};
    var cx = 0, cy = 0, n = pts.length, o = poly(pts, opt.fill || C.stone2, 1.8), d = '', s = '';
    pts.forEach(function (p) { cx += p[0] / n; cy += p[1] / n; });
    for (var i = 0; i < n; i++) {
      var a = pts[i], b = pts[(i + 1) % n], mx = (a[0] + b[0]) / 2;
      var k = 0.42 + rnd() * 0.2, c = [a[0] + (cx - a[0]) * k * 0.6 + (b[0] - a[0]) * 0.3, a[1] + (cy - a[1]) * k];
      if (mx > cx + 4) o += flat([a, b, c], C.rock, 0.95);
      else if (mx < cx - 6 && rnd() < 0.5) o += flat([a, b, c], C.stone, 0.9);
      d += seg(a[0], a[1], c[0], c[1]);
      // 裂隙：从轮廓点往下的折线
      var x = a[0] + (cx - a[0]) * 0.15, y = a[1] + 2, L = 6 + rnd() * 12;
      s += 'M' + f(x) + ' ' + f(y) + 'l' + f((rnd() - 0.5) * 4) + ' ' + f(L * 0.5) + 'l' + f((rnd() - 0.5) * 4) + ' ' + f(L * 0.5);
    }
    // 层理：水平短排线
    var minY = Math.min.apply(null, pts.map(function (p) { return p[1]; })), maxY = Math.max.apply(null, pts.map(function (p) { return p[1]; }));
    var minX = Math.min.apply(null, pts.map(function (p) { return p[0]; })), maxX = Math.max.apply(null, pts.map(function (p) { return p[0]; }));
    var h = '';
    for (var t = 0; t < (opt.strata || 14); t++) {
      var yy = minY + 6 + rnd() * (maxY - minY - 10), xx = minX + 6 + rnd() * (maxX - minX - 12);
      if (inside(pts, xx, yy) && inside(pts, xx + 8, yy)) h += seg(xx, yy, xx + 4 + rnd() * 6, yy + (rnd() - 0.5));
    }
    return o + ln(d, 0.9, 0.55) + ln(s, 0.8, 0.5) + ln(h, 0.7, 0.45);
  }
  function inside(pts, x, y) { // 射线法
    var c = false;
    for (var i = 0, j = pts.length - 1; i < pts.length; j = i++) {
      var a = pts[i], b = pts[j];
      if ((a[1] > y) !== (b[1] > y) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) c = !c;
    }
    return c;
  }
  /** 石板地坪 */
  function paving(x0, y0, x1, y1, s, rnd, fill) {
    var o = rect(x0, y0, x1 - x0, y1 - y0, fill || C.stone, 1.2), d = '', row = 0;
    for (var y = y0 + s; y < y1 - 0.5; y += s) d += seg(x0 + 0.6, y, x1 - 0.6, y);
    for (var yy = y0; yy < y1 - 0.5; yy += s, row++) {
      for (var x = x0 + (row % 2 ? s * 0.5 : s) + (rnd() - 0.5); x < x1 - 1; x += s) d += seg(x, yy + 0.5, x, Math.min(y1, yy + s) - 0.5);
    }
    return o + ln(d, 0.7, 0.4);
  }
  /** 灌木丛 */
  function bush(cx, yb, r, rnd, fill) {
    var d = '', n = 7;
    for (var i = 0; i <= n; i++) {
      var a = Math.PI + Math.PI * i / n, rr = r * (0.85 + rnd() * 0.3);
      var px = cx + Math.cos(a) * rr, py = yb - r * 0.8 + Math.sin(a) * rr * 0.9;
      d += (i ? 'Q' + f(cx + Math.cos(a - Math.PI / n / 2) * rr * 1.25) + ' ' + f(yb - r * 0.8 + Math.sin(a - Math.PI / n / 2) * rr * 1.1) + ' ' : 'M') + f(px) + ' ' + f(py);
    }
    d += 'Q' + f(cx) + ' ' + f(yb + 1) + ' ' + f(cx - r) + ' ' + f(yb - r * 0.8) + 'Z';
    return path(d, fill || C.leaf, 1.3) + ln('M' + f(cx - r * 0.4) + ' ' + f(yb - r * 0.9) + 'q' + f(r * 0.2) + ' -2 ' + f(r * 0.4) + ' 0', 0.8, 0.5);
  }
  /** 阔叶树：树干 + 两团树冠 */
  function tree(cx, yb, r, rnd) {
    var o = rect(cx - 1.6, yb - r * 0.9, 3.2, r * 0.9, C.beam, 1.1);
    o += bush(cx, yb - r * 0.55, r, rnd, C.leaf2) + bush(cx - r * 0.25, yb - r * 0.75, r * 0.7, rnd, C.leaf);
    return o;
  }
  /** 柏树 / 针叶树：细长尖冠 */
  function cypress(cx, yb, h, w) {
    w = w || h * 0.22;
    var d = 'M' + f(cx) + ' ' + f(yb - h) + 'Q' + f(cx + w * 0.9) + ' ' + f(yb - h * 0.55) + ' ' + f(cx + w * 0.55) + ' ' + f(yb - 2) +
      'L' + f(cx - w * 0.55) + ' ' + f(yb - 2) + 'Q' + f(cx - w * 0.9) + ' ' + f(yb - h * 0.55) + ' ' + f(cx) + ' ' + f(yb - h) + 'Z';
    return rect(cx - 1, yb - 3, 2, 3, C.beam, 0.9) + path(d, C.leaf2, 1.2) +
      ln(seg(cx - w * 0.2, yb - h * 0.7, cx + w * 0.1, yb - h * 0.6) + seg(cx - w * 0.3, yb - h * 0.4, cx + w * 0.15, yb - h * 0.3), 0.7, 0.5);
  }
  /** 菜畦：x0..x1 × y0..y1 的田块，n 垄 */
  function beds(x0, y0, x1, y1, n, rnd) {
    var o = rect(x0, y0, x1 - x0, y1 - y0, '#b9a479', 1.1), d = '', h = (y1 - y0) / n;
    for (var i = 0; i < n; i++) {
      var y = y0 + h * (i + 0.5);
      for (var x = x0 + 3; x < x1 - 2; x += 4 + rnd() * 1.5) o += circle(x, y, 1.3 + rnd() * 0.5, i % 2 ? C.leaf : C.leaf2, 0);
      if (i) d += seg(x0 + 1, y0 + h * i, x1 - 1, y0 + h * i);
    }
    return o + ln(d, 0.7, 0.45);
  }

  /** 烟囱：石砌方柱，正面 x0..x0+w，底 yb，高 h，顶部帽沿 */
  function chimney(x0, yb, w, h, rnd) {
    return rect(x0, yb - h, w, h, C.stone2, 1.5) + courses(x0, x0 + w, yb - h, yb, 5, rnd, 6) +
      rect(x0 - 1.5, yb - h - 3, w + 3, 3.5, C.stone3, 1.3) + rect(x0 + 1, yb - h - 4.8, w - 2, 2, C.dark, 0.8);
  }
  /** 炊烟：几团木刻式卷云，从 (x,y) 往右上飘 */
  function smoke(x, y, n, rnd, sc) {
    sc = sc || 1;
    var o = '', cx = x, cy = y;
    for (var i = 0; i < n; i++) {
      var r = (3 + i * 1.3) * sc;
      cy -= r * 1.5; cx += r * 0.7 + (rnd() - 0.3) * 2;
      var d = 'M' + f(cx - r) + ' ' + f(cy + r * 0.3) + 'Q' + f(cx - r * 1.1) + ' ' + f(cy - r * 0.8) + ' ' + f(cx) + ' ' + f(cy - r * 0.7) +
        'Q' + f(cx + r * 1.2) + ' ' + f(cy - r * 0.9) + ' ' + f(cx + r) + ' ' + f(cy + r * 0.2) + 'Q' + f(cx) + ' ' + f(cy + r * 0.9) + ' ' + f(cx - r) + ' ' + f(cy + r * 0.3) + 'Z';
      o += path(d, '#e6dccb', 1.1, 'stroke-opacity="0.75"') +
        ln('M' + f(cx - r * 0.3) + ' ' + f(cy) + 'q' + f(r * 0.4) + ' ' + f(-r * 0.4) + ' ' + f(r * 0.6) + ' 0', 0.8, 0.5);
    }
    return o;
  }

  var api = {
    chimney: chimney, smoke: smoke,
    CELL: CELL, C: C, MAT: MAT, f: f, rng: rng, lerp: lerp, pd: pd, seg: seg, at: at, poly: poly, path: path, rect: rect,
    circle: circle, ellipse: ellipse, ln: ln, flat: flat, flatD: flatD, shade: shade, boxShadow: boxShadow, slope: slope,
    courses: courses, wall: wall, archPath: archPath, pointPath: pointPath, win: win, door: door, arcade: arcade,
    column: column, pediment: pediment, cross: cross, finial: finial, flag: flag, roseWindow: roseWindow, ring: ring,
    fascia: fascia, gableRoof: gableRoof, gableFront: gableFront, hipRoof: hipRoof, pyramid: pyramid, cone: cone,
    cylinder: cylinder, box: box, merlons: merlons, ringMerlons: ringMerlons, buttress: buttress, pinnacle: pinnacle,
    crag: crag, inside: inside, paving: paving, bush: bush, tree: tree, cypress: cypress, beds: beds
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.TownArtWL_core = api;
})(typeof window !== 'undefined' ? window : this);
