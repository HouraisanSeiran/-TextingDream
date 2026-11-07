/*
 * 织梦 · 西式特殊建筑：共用画笔（3/4 斜俯视，木刻线描 + 羊皮纸淡彩；美术样板，尚未接入游戏）
 *
 * 投影约定（与 docs/town-art-spec.md 一致）：地面格是 48 px 正方形，地面进深不压缩；
 * 立面直接向上画；屋顶顶面按"地面进深 + 屋脊抬升"计算：
 *   坡屋顶（屋脊平行正面）：前檐 yE，后檐 yE - dg，屋脊 yE - dg/2 - rise。
 *   山墙朝前：屋脊从 (cx, yE - rise) 向后延伸 dg。
 * 光从左上来：左坡偏亮、右坡偏暗，投影落在右下方。
 * 浏览器挂 window.TownArtWS_prims；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var CELL = 48;
  var C = {
    ink: '#4a3826', paper: '#efdfb2', plaster: '#e9dcc0', wash: '#e3c47a', wood: '#c9a46a',
    stone: '#cfc0a2', stone2: '#bfb093', stone3: '#b1a287', beam: '#8a6a44', dark: '#6b4f32',
    tile: '#b5654a', red: '#9a3b2a', slate: '#7d8790', slate2: '#5f6870',
    thatch: '#d2b46c', thatch2: '#b8954e', grass: '#c9c79a', shadow: '#3a2c1e',
    // 规范色表外的两个补色（菜蔬、水面），在 README 里说明
    leaf: '#8f9a5c', water: '#a9b8ad'   // 水色同 special-infra 西式码头 / west-ground 水面瓦片
  };
  var MAT = {
    tile: { fill: C.tile, back: '#a0553d', row: 5, ink: 0.42, kind: 'tile' },
    slate: { fill: C.slate, back: C.slate2, row: 4, ink: 0.45, kind: 'slate' },
    thatch: { fill: C.thatch, back: C.thatch2, row: 6, ink: 0.38, kind: 'thatch' },
    shingle: { fill: C.wood, back: C.beam, row: 5, ink: 0.42, kind: 'tile' },
    canvas: { fill: C.paper, back: C.stone, row: 0, ink: 0.3, kind: 'none' }
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
    return 'fill="' + fill + '" stroke="' + C.ink + '" stroke-width="' + f(sw == null ? 1.6 : sw) +
      '" stroke-linejoin="round" stroke-linecap="round"' + (extra ? ' ' + extra : '');
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
  /** 细线（不填充）：d 路径，sw 线宽，op 不透明度，color 默认墨色 */
  function ln(d, sw, op, color) {
    if (!d) return '';
    return '<path d="' + d + '" fill="none" stroke="' + (color || C.ink) + '" stroke-width="' + f(sw || 0.8) +
      '" stroke-linecap="round" stroke-linejoin="round"' + (op != null && op < 1 ? ' stroke-opacity="' + f(op) + '"' : '') + '/>';
  }
  function flat(pts, fill, op) {
    return '<path d="' + pd(pts) + '" fill="' + fill + '"' + (op != null && op < 1 ? ' fill-opacity="' + f(op) + '"' : '') + '/>';
  }
  /** 投影：半透明暗色平涂 */
  function shade(pts, op) { return flat(pts, C.shadow, op == null ? 0.18 : op); }
  /** 方盒投影：盒体地面范围 x0..x1、后沿 yb、前沿 yf；向右伸 s（不超出 W），向下 2–4 px（不超出 H） */
  function boxShadow(x0, x1, yb, yf, s, W, H) {
    var dn = Math.min(4, H - yf), sx = Math.max(0, Math.min(s, W - x1 - 0.5));
    return shade([[x0 + 4, yf], [x0 + 4 + dn, yf + dn], [x1 + sx, yf + dn], [x1 + sx, yb + sx * 0.7], [x1, yb]]);
  }

  /**
   * 一块坡面：A→B 为檐口，D→C 为屋脊一侧（A 对 D、B 对 C）。
   * 平涂 + 平行于檐口的瓦行线 + 行间错缝短线；茅草用随机短排线。
   */
  function slope(A, B, C2, D, mat, dark, rnd) {
    var m = MAT[mat] || MAT.tile, s = poly([A, B, C2, D], dark ? m.back : m.fill, 1.4);
    if (!m.row) return s;
    var len = Math.hypot(D[0] - A[0], D[1] - A[1]), n = Math.max(2, Math.round(len / m.row)), d = '', tk = '';
    var w = Math.hypot(B[0] - A[0], B[1] - A[1]);
    for (var i = 1; i < n; i++) {
      var t = i / n, P = lerp(A, D, t), Q = lerp(B, C2, t);
      if (m.kind === 'thatch') {
        d += seg(P[0], P[1], Q[0], Q[1]);
      } else d += seg(P[0], P[1], Q[0], Q[1]);
      var t0 = (i - 1) / n, P0 = lerp(A, D, t0), Q0 = lerp(B, C2, t0);
      var step = m.kind === 'thatch' ? 3.2 : 7, k = Math.max(1, Math.round(w / step));
      for (var j = 0; j < k; j++) {
        var u = (j + (m.kind === 'thatch' ? (rnd ? rnd() : 0.5) : (i % 2 ? 0.25 : 0.75))) / k;
        if (m.kind === 'thatch' && rnd && rnd() < 0.35) continue;
        var a = lerp(P0, Q0, u), b = lerp(P, Q, u);
        tk += seg(a[0], a[1], m.kind === 'thatch' ? (a[0] * 0.3 + b[0] * 0.7) : b[0], m.kind === 'thatch' ? (a[1] * 0.3 + b[1] * 0.7) : b[1]);
      }
    }
    return s + ln(d, 0.8, m.ink) + ln(tk, m.kind === 'thatch' ? 0.7 : 0.7, m.kind === 'thatch' ? 0.45 : m.ink * 0.85, m.kind === 'thatch' ? C.dark : null);
  }

  // ——————————————————— 墙面 ———————————————————
  /** 石砌 / 砖砌层缝：每层高 ch，竖缝间距约 bw，逐层错缝 */
  function courses(x0, x1, yt, yb, ch, rnd, bw) {
    var d = '', v = '', row = 0, y;
    for (y = yb - ch; y > yt + 1.5; y -= ch) d += seg(x0 + 0.8, y, x1 - 0.8, y);
    for (y = yb; y > yt + 0.5; y -= ch, row++) {
      var top = Math.max(yt, y - ch), x = x0 + (row % 2 ? bw * 0.5 : bw * 0.95) + (rnd() - 0.5) * 2;
      for (; x < x1 - 2.5; x += bw * (0.8 + rnd() * 0.45)) v += seg(x, top + 0.5, x, y - 0.5);
    }
    return ln(d, 0.8, 0.5) + ln(v, 0.7, 0.42);
  }
  /** 木筋墙：竖柱 n 间、楼层梁、两端开间各一对斜撑（中间开间留给窗） */
  function timberFrame(x0, x1, yt, yb, n, floors) {
    var d = '', w = (x1 - x0) / n, fh = (yb - yt) / (floors || 1), i, k;
    for (k = 1; k < (floors || 1); k++) d += seg(x0, yt + fh * k, x1, yt + fh * k);
    for (i = 1; i < n; i++) d += seg(x0 + w * i, yt, x0 + w * i, yb);
    for (k = 0; k < (floors || 1); k++) {
      var a = yt + fh * k, b = a + fh;
      d += seg(x0 + 1, b - 1, x0 + w - 1, a + 1) + seg(x1 - 1, b - 1, x1 - w + 1, a + 1);
    }
    return ln(d, 2.4, 1, C.beam) + ln(seg(x0, yt + 1, x1, yt + 1), 2.6, 1, C.beam);
  }
  /** 正立面墙。kind: plaster | timber | stone | ashlar | brick | plank */
  function wall(x0, x1, yt, yb, kind, rnd, opt) {
    opt = opt || {};
    var fills = { plaster: C.plaster, timber: C.plaster, stone: C.stone, ashlar: C.stone, brick: C.stone2, plank: C.wood };
    var o = rect(x0, yt, x1 - x0, yb - yt, opt.fill || fills[kind] || C.plaster, 1.8);
    if (kind === 'stone') o += courses(x0, x1, yt, yb, opt.ch || 6, rnd, 9);
    if (kind === 'ashlar') o += courses(x0, x1, yt, yb, opt.ch || 7, rnd, 15);
    if (kind === 'brick') o += courses(x0, x1, yt, yb, opt.ch || 4, rnd, 7);
    if (kind === 'plank') {
      var d = '';
      for (var x = x0 + 5; x < x1 - 1; x += 5) d += seg(x, yt + 1, x, yb - 1);
      o += ln(d, 0.8, 0.5);
    }
    if (kind === 'timber') o += timberFrame(x0, x1, yt, yb, opt.bays || 3, opt.floors || 1);
    if (opt.plinth) o += rect(x0, yb - opt.plinth, x1 - x0, opt.plinth, C.stone2, 1.4) + courses(x0, x1, yb - opt.plinth, yb, opt.plinth, rnd, 10);
    // 檐下阴影带 + 右端转角阴面（光从左上来）
    o += flat([[x0 + 1, yt + 0.8], [x1 - 1, yt + 0.8], [x1 - 1, yt + 4.5], [x0 + 1, yt + 3.5]], C.shadow, 0.16);
    o += flat([[x1 - 3.5, yt + 1], [x1 - 1, yt + 1], [x1 - 1, yb - 1], [x1 - 3.5, yb - 1]], C.shadow, 0.12);
    return o;
  }

  // ——————————————————— 门窗 ———————————————————
  function archPath(x, y, w, h) { // y = 顶点，半圆拱
    var r = w / 2;
    return 'M' + f(x) + ' ' + f(y + h) + 'L' + f(x) + ' ' + f(y + r) + 'A' + f(r) + ' ' + f(r) + ' 0 0 1 ' + f(x + w) + ' ' + f(y + r) + 'L' + f(x + w) + ' ' + f(y + h) + 'Z';
  }
  function pointPath(x, y, w, h) { // 尖拱（哥特）
    var m = x + w / 2, s = Math.min(h * 0.45, w * 0.9);
    return 'M' + f(x) + ' ' + f(y + h) + 'L' + f(x) + ' ' + f(y + s) + 'Q' + f(x) + ' ' + f(y + s * 0.25) + ' ' + f(m) + ' ' + f(y) +
      'Q' + f(x + w) + ' ' + f(y + s * 0.25) + ' ' + f(x + w) + ' ' + f(y + s) + 'L' + f(x + w) + ' ' + f(y + h) + 'Z';
  }
  /** 窗：x,y 左上；shape: rect | arch | point；panes 是否画窗棂十字；shutters 百叶 */
  function win(x, y, w, h, opt) {
    opt = opt || {};
    var o = '', d = opt.shape === 'arch' ? archPath(x, y, w, h) : opt.shape === 'point' ? pointPath(x, y, w, h) : pd([[x, y], [x + w, y], [x + w, y + h], [x, y + h]]);
    if (opt.shutters) o += rect(x - w * 0.42, y, w * 0.42, h, C.beam, 1) + rect(x + w, y, w * 0.42, h, C.beam, 1);
    o += path(d, opt.glass || C.dark, 1.3);
    var top = opt.shape ? y + w * 0.5 : y + 1;
    if (opt.panes !== false) o += ln(seg(x + w / 2, y + 1.2, x + w / 2, y + h - 0.8) + (h > 8 ? seg(x + 0.8, top + (y + h - top) * 0.42, x + w - 0.8, top + (y + h - top) * 0.42) : ''), 0.9, 0.85, C.wash);
    o += ln(seg(x - 1.2, y + h + 0.6, x + w + 1.2, y + h + 0.6), 1.4, 1);
    return o;
  }
  /** 门：cx 中线，yb 门槛；arch 半圆拱 / point 尖拱 / 方门；open 时画成黑洞 */
  function door(cx, yb, w, h, opt) {
    opt = opt || {};
    var x = cx - w / 2, y = yb - h;
    var d = opt.shape === 'arch' ? archPath(x, y, w, h) : opt.shape === 'point' ? pointPath(x, y, w, h) : pd([[x, y], [x + w, y], [x + w, yb], [x, yb]]);
    var o = '';
    if (opt.frame) o += path(opt.shape === 'arch' ? archPath(x - 2, y - 2, w + 4, h + 2) : opt.shape === 'point' ? pointPath(x - 2, y - 2, w + 4, h + 2) : pd([[x - 2, y - 2], [x + w + 2, y - 2], [x + w + 2, yb], [x - 2, yb]]), opt.frame, 1.3);
    o += path(d, opt.open ? C.dark : (opt.fill || C.beam), 1.5);
    if (!opt.open) {
      var v = '';
      for (var i = 1; i < 4; i++) v += seg(x + w * i / 4, y + (opt.shape ? w * 0.25 : 1), x + w * i / 4, yb - 0.5);
      o += ln(v, 0.8, 0.55) + ln(seg(x + 1, yb - h * 0.3, x + w - 1, yb - h * 0.3) + seg(x + 1, yb - h * 0.72, x + w - 1, yb - h * 0.72), 1.1, 0.7, C.dark);
    }
    return o;
  }

  // ——————————————————— 屋顶 ———————————————————
  /** 檐口封檐板：一条深木色窄带 */
  function fascia(a, b, y, t) { return rect(a, y, b - a, t || 2.4, C.dark, 1.1); }
  /**
   * 坡屋顶，屋脊平行正面。x0..x1 墙宽，yE 前檐（=正墙顶），dg 地面进深，rise 屋脊抬升。
   * 屋脊比后檐高时后坡被挡住，只画前坡。
   */
  function gableRoof(x0, x1, yE, dg, rise, mat, rnd, opt) {
    opt = opt || {};
    var ov = opt.ov == null ? 3 : opt.ov, yR = yE - dg / 2 - rise, yB = yE - dg - 1;
    var a = x0 - ov, b = x1 + ov, o = '';
    if (yB < yR - 0.5) o += slope([a, yB], [b, yB], [b, yR], [a, yR], mat, true, rnd);
    o += slope([a, yE + 1], [b, yE + 1], [b, yR], [a, yR], mat, false, rnd);
    o += fascia(a, b, yE + 0.5, 2.2) + ln(seg(a, yR, b, yR), 2.2, 1);
    return o;
  }
  /** 山墙朝前的坡屋顶：屋脊垂直正面。返回 { roof, gable }，gable 是正面山尖三角（要盖在墙之上画）。 */
  function gableFront(x0, x1, yE, dg, rise, mat, rnd, opt) {
    opt = opt || {};
    var ov = opt.ov == null ? 3 : opt.ov, cx = (x0 + x1) / 2, yA = yE - rise;
    var roof = slope([x0 - ov, yE + ov * 0.6], [x0 - ov, yE - dg + ov * 0.6], [cx, yA - dg], [cx, yA], mat, false, rnd) +
      slope([x1 + ov, yE + ov * 0.6], [x1 + ov, yE - dg + ov * 0.6], [cx, yA - dg], [cx, yA], mat, true, rnd) +
      ln(seg(cx, yA, cx, yA - dg), 2, 1);
    var gable = poly([[x0, yE], [cx, yA + 1], [x1, yE]], opt.fill || C.plaster, 1.6);
    if (opt.timber) {
      gable += ln(seg(cx, yA + 2, cx, yE) + seg(x0 + 4, yE - 1, cx, yA + rise * 0.45) + seg(x1 - 4, yE - 1, cx, yA + rise * 0.45) +
        seg(x0 + (cx - x0) * 0.35, yE - rise * 0.33, x1 - (x1 - cx) * 0.35, yE - rise * 0.33), 2.2, 1, C.beam);
    }
    if (opt.vent) gable += win(cx - 3, yA + rise * 0.45, 6, 7, { shape: 'arch', panes: false });
    gable += ln(seg(x0 - ov, yE + ov * 0.6, cx, yA - 0.6) + seg(cx, yA - 0.6, x1 + ov, yE + ov * 0.6), 3, 1, C.dark) +
      ln(seg(x0 - ov, yE + ov * 0.6, cx, yA - 0.6) + seg(cx, yA - 0.6, x1 + ov, yE + ov * 0.6), 1, 0.8, C.ink);
    return { roof: roof, gable: gable };
  }
  /** 四坡顶：hip 为两端斜脊内收量 */
  function hipRoof(x0, x1, yE, dg, rise, mat, rnd, opt) {
    opt = opt || {};
    var ov = opt.ov == null ? 3 : opt.ov, a = x0 - ov, b = x1 + ov, yR = yE - dg / 2 - rise, yB = yE - dg - 1;
    var hp = opt.hip == null ? Math.min(dg * 0.5, (x1 - x0) * 0.32) : opt.hip, o = '';
    var L = [a + hp, yR], R = [b - hp, yR];
    if (yB < yR - 0.5) o += slope([a, yB], [b, yB], R, L, mat, true, rnd);
    o += slope([a, yE + 1], [a, yB], L, L, mat, false, rnd) + slope([b, yE + 1], [b, yB], R, R, mat, true, rnd);
    o += slope([a, yE + 1], [b, yE + 1], R, L, mat, false, rnd);
    o += fascia(a, b, yE + 0.5, 2.2) + ln(seg(L[0], L[1], R[0], R[1]), 2.2, 1);
    return o;
  }
  /** 四角攒尖（塔尖）：底为塔顶面 x0..x1 × (yE-dg .. yE)，尖高 h（自顶面中心起） */
  function pyramid(x0, x1, yE, dg, h, mat, rnd, opt) {
    opt = opt || {};
    var ov = opt.ov == null ? 2 : opt.ov, a = x0 - ov, b = x1 + ov, cx = (x0 + x1) / 2, ap = [cx, yE - dg / 2 - h];
    var o = slope([a, yE + 1], [a, yE - dg], ap, ap, mat, false, rnd) + slope([b, yE + 1], [b, yE - dg], ap, ap, mat, true, rnd) +
      slope([a, yE + 1], [b, yE + 1], ap, ap, mat, false, rnd);
    if (opt.finial !== false) o += ln(seg(ap[0], ap[1], ap[0], ap[1] - 6), 1.4, 1) + circle(ap[0], ap[1] - 6.5, 1.4, C.wash, 0.9);
    return o;
  }
  /** 圆锥顶：底为椭圆（半径 r，扁度 0.5），尖高 h */
  function cone(cx, yb, r, h, mat, opt) {
    opt = opt || {};
    var m = MAT[mat] || MAT.slate, ry = r * 0.5, ap = cx + ' ' + f(yb - h), o = '';
    o += path('M' + f(cx - r) + ' ' + f(yb) + 'L' + ap + 'L' + f(cx + r) + ' ' + f(yb) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 1 ' + f(cx - r) + ' ' + f(yb) + 'Z', m.fill, 1.6);
    o += flat([[cx + r * 0.25, yb + ry * 0.95], [cx, yb - h], [cx + r, yb]], m.back, 1);
    var d = '';
    for (var i = 1; i < 6; i++) {
      var t = i / 6, y = yb - h * (1 - t);
      d += 'M' + f(cx - r * t) + ' ' + f(y) + 'A' + f(r * t) + ' ' + f(ry * t) + ' 0 0 0 ' + f(cx + r * t) + ' ' + f(y);
    }
    o += ln(d, 0.8, m.ink) + ln('M' + f(cx - r) + ' ' + f(yb) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + r) + ' ' + f(yb), 1.6, 1);
    if (opt.finial !== false) o += ln(seg(cx, yb - h, cx, yb - h - 6), 1.4, 1) + circle(cx, yb - h - 6.5, 1.4, C.wash, 0.9);
    return o;
  }
  /** 圆柱体（圆塔、水桶、酒桶立放）：前面 + 顶椭圆。kind: stone | plank | plain */
  function cylinder(cx, yb, r, h, fill, kind, rnd, opt) {
    opt = opt || {};
    var ry = r * (opt.flat || 0.5), yt = yb - h, x0 = cx - r, x1 = cx + r, o = '';
    o += path('M' + f(x0) + ' ' + f(yt) + 'L' + f(x0) + ' ' + f(yb) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 0 ' + f(x1) + ' ' + f(yb) + 'L' + f(x1) + ' ' + f(yt) + 'Z', fill, 1.6);
    o += flat([[cx + r * 0.55, yt], [x1, yt], [x1, yb], [cx + r * 0.55, yb + ry * 0.83]], C.shadow, 0.14);
    if (kind === 'stone' && rnd) {
      var d = '', v = '', row = 0;
      for (var y = yb - 6; y > yt + 2; y -= 6, row++) {
        d += 'M' + f(x0) + ' ' + f(y) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 0 ' + f(x1) + ' ' + f(y);
        for (var k = -2; k <= 2; k++) {
          var u = (k + (row % 2 ? 0.5 : 0)) / 3.2; if (Math.abs(u) > 0.9) continue;
          var vx = cx + u * r, dy = ry * Math.sqrt(1 - u * u);
          v += seg(vx, y + dy + 0.5, vx, y + dy + 5.5);
        }
      }
      o += ln(d, 0.8, 0.5) + ln(v, 0.7, 0.42);
    }
    if (kind === 'plank') {
      var pv = '';
      for (var j = -3; j <= 3; j++) { var px = cx + j * r / 4, py = ry * Math.sqrt(Math.max(0, 1 - Math.pow(j / 4, 2))); pv += seg(px, yt + py, px, yb + py); }
      o += ln(pv, 0.7, 0.45);
    }
    if (opt.top !== false) o += ellipse(cx, yt, r, ry, opt.topFill || fill, 1.5);
    return o;
  }
  /** 方盒（箱子、台子、小屋体）：正面 x0..x1 × (yf-h..yf)，顶面向后 dg */
  function box(x0, x1, yf, dg, h, front, top, sw) {
    return poly([[x0, yf - h], [x1, yf - h], [x1, yf - h - dg], [x0, yf - h - dg]], top || front, sw || 1.4) +
      rect(x0, yf - h, x1 - x0, h, front, sw || 1.4);
  }

  // ——————————————————— 小部件 ———————————————————
  /** 烟囱：石砌方柱，正面 x0..x0+w，底 yb，高 h；顶部帽沿 */
  function chimney(x0, yb, w, h, rnd, opt) {
    opt = opt || {};
    var o = rect(x0, yb - h, w, h, opt.fill || C.stone2, 1.5) + courses(x0, x0 + w, yb - h, yb, 5, rnd, 6);
    o += rect(x0 - 1.5, yb - h - 3, w + 3, 3.5, C.stone3, 1.3) + rect(x0 + 1, yb - h - 4.8, w - 2, 2, C.dark, 0.8);
    return o;
  }
  /** 炊烟：几团木刻式卷云，从 (x,y) 往右上飘；n 团 */
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
  /** 横放酒桶：正面看到圆形桶底，cx,cy 中心，r 半径 */
  function barrelEnd(cx, cy, r) {
    return circle(cx, cy, r, C.wood, 1.4) + circle(cx, cy, r * 0.62, 'none', 0.8, 'stroke-opacity="0.6"') +
      ln(seg(cx - r * 0.8, cy, cx + r * 0.8, cy), 0.7, 0.5) + ring(cx, cy, r - 0.6, 1.6, 1, C.dark);
  }
  /** 只描边的圆（不重复 stroke 属性） */
  function ring(cx, cy, r, sw, op, color) {
    return '<circle cx="' + f(cx) + '" cy="' + f(cy) + '" r="' + f(r) + '" fill="none" stroke="' + (color || C.ink) + '" stroke-width="' + f(sw || 1) + '"' +
      (op != null && op < 1 ? ' stroke-opacity="' + f(op) + '"' : '') + '/>';
  }
  /** 立放木桶：cx, yb 底，r, h */
  function barrel(cx, yb, r, h, water) {
    var o = cylinder(cx, yb, r, h, C.wood, 'plank', null, { topFill: water ? C.water : C.wood });
    o += ln('M' + f(cx - r) + ' ' + f(yb - h * 0.25) + 'A' + f(r) + ' ' + f(r * 0.5) + ' 0 0 0 ' + f(cx + r) + ' ' + f(yb - h * 0.25) +
      'M' + f(cx - r) + ' ' + f(yb - h * 0.75) + 'A' + f(r) + ' ' + f(r * 0.5) + ' 0 0 0 ' + f(cx + r) + ' ' + f(yb - h * 0.75), 1.4, 1, C.dark);
    return o;
  }
  /** 木箱：正面 x0..x0+w，底 yb */
  function crate(x0, yb, w, h, dg) {
    var o = box(x0, x0 + w, yb, dg == null ? w * 0.45 : dg, h, C.wood, '#d8b77e', 1.3);
    o += ln(seg(x0 + 1, yb - h + 1, x0 + w - 1, yb - 1) + seg(x0 + 1, yb - 1, x0 + w - 1, yb - h + 1), 1, 0.6);
    return o;
  }
  /** 铁砧：底座木墩 + 铁砧，cx 中线，yb 地面 */
  function anvil(cx, yb, sc) {
    sc = sc || 1;
    var s = function (v) { return v * sc; };
    var o = rect(cx - s(4), yb - s(7), s(8), s(7), C.beam, 1.3) + ellipse(cx, yb - s(7), s(4), s(1.6), C.wood, 1);
    o += path('M' + f(cx - s(9)) + ' ' + f(yb - s(12)) + 'L' + f(cx + s(6)) + ' ' + f(yb - s(12)) + 'L' + f(cx + s(7)) + ' ' + f(yb - s(10.5)) +
      'L' + f(cx + s(3)) + ' ' + f(yb - s(10)) + 'L' + f(cx + s(2.5)) + ' ' + f(yb - s(8)) + 'L' + f(cx - s(3)) + ' ' + f(yb - s(8)) +
      'L' + f(cx - s(3.5)) + ' ' + f(yb - s(10)) + 'Q' + f(cx - s(7)) + ' ' + f(yb - s(10)) + ' ' + f(cx - s(9)) + ' ' + f(yb - s(12)) + 'Z', C.slate2, 1.4);
    o += ln(seg(cx - s(7), yb - s(11.6), cx + s(5), yb - s(11.6)), 0.8, 0.7, '#a9b1b6');
    return o;
  }
  /** 旗：杆底 (x,yb)，杆高 h，旗宽 w；color 旗色 */
  function flag(x, yb, h, w, color) {
    var t = yb - h, o = ln(seg(x, yb, x, t - 2), 1.4, 1);
    o += path('M' + f(x) + ' ' + f(t) + 'Q' + f(x + w * 0.5) + ' ' + f(t - 2) + ' ' + f(x + w) + ' ' + f(t + 1) + 'L' + f(x + w * 0.82) + ' ' + f(t + 4) +
      'L' + f(x + w) + ' ' + f(t + 7) + 'Q' + f(x + w * 0.5) + ' ' + f(t + 5) + ' ' + f(x) + ' ' + f(t + 7) + 'Z', color || C.red, 1.1);
    return o + circle(x, t - 2.5, 1.1, C.wash, 0.8);
  }
  /** 挑出的招牌：墙上铁臂 + 悬挂木牌；x 墙面挂点，y 高度，dir 1 向右挑；icon(cx,cy) 返回牌面图案 */
  function hangSign(x, y, dir, w, h, icon) {
    var ex = x + dir * (w + 5), o = ln(seg(x, y, ex, y) + seg(x, y + 5, x + dir * 6, y), 1.3, 1);
    var sx = Math.min(x + dir * 4, ex) + (dir < 0 ? 1 : 0) , cx = (x + dir * 4 + ex) / 2;
    o += ln(seg(cx - w / 2 + 1, y, cx - w / 2 + 1, y + 2) + seg(cx + w / 2 - 1, y, cx + w / 2 - 1, y + 2), 0.8, 1);
    o += rect(cx - w / 2, y + 2, w, h, C.wash, 1.2);
    void sx;
    return o + (icon ? icon(cx, y + 2 + h / 2) : '');
  }
  /** 马蹄铁图案 */
  function horseshoe(cx, cy, r) {
    return '<path d="M' + f(cx - r) + ' ' + f(cy + r) + 'L' + f(cx - r) + ' ' + f(cy) + 'A' + f(r) + ' ' + f(r) + ' 0 0 1 ' + f(cx + r) + ' ' + f(cy) +
      'L' + f(cx + r) + ' ' + f(cy + r) + '" fill="none" stroke="' + C.slate2 + '" stroke-width="' + f(r * 0.6) + '" stroke-linecap="butt"/>';
  }
  /** 石板地坪（院落 / 台基）：x0..x1 × y0..y1，格 s */
  function paving(x0, y0, x1, y1, s, rnd, fill) {
    var o = rect(x0, y0, x1 - x0, y1 - y0, fill || C.stone, 1.2), d = '', row = 0;
    for (var y = y0 + s; y < y1 - 0.5; y += s) d += seg(x0 + 0.6, y, x1 - 0.6, y);
    for (var yy = y0; yy < y1 - 0.5; yy += s, row++) {
      for (var x = x0 + (row % 2 ? s * 0.5 : s) + (rnd() - 0.5); x < x1 - 1; x += s) d += seg(x, yy + 0.5, x, Math.min(y1, yy + s) - 0.5);
    }
    return o + ln(d, 0.7, 0.4);
  }
  /** 灌木 / 小树丛：一团叶子 */
  function bush(cx, yb, r, rnd) {
    var d = '', n = 7;
    for (var i = 0; i <= n; i++) {
      var a = Math.PI + Math.PI * i / n, rr = r * (0.85 + rnd() * 0.3);
      var px = cx + Math.cos(a) * rr, py = yb - r * 0.8 + Math.sin(a) * rr * 0.9;
      d += (i ? 'Q' + f(cx + Math.cos(a - Math.PI / n / 2) * rr * 1.25) + ' ' + f(yb - r * 0.8 + Math.sin(a - Math.PI / n / 2) * rr * 1.1) + ' ' : 'M') + f(px) + ' ' + f(py);
    }
    d += 'Q' + f(cx) + ' ' + f(yb + 1) + ' ' + f(cx - r) + ' ' + f(yb - r * 0.8) + 'Z';
    return path(d, C.leaf, 1.3) + ln('M' + f(cx - r * 0.4) + ' ' + f(yb - r * 0.9) + 'q' + f(r * 0.2) + ' -2 ' + f(r * 0.4) + ' 0', 0.8, 0.5);
  }

  var api = {
    CELL: CELL, C: C, MAT: MAT, f: f, rng: rng, lerp: lerp, pd: pd, seg: seg, at: at, poly: poly, path: path, rect: rect,
    circle: circle, ellipse: ellipse, ln: ln, flat: flat, shade: shade, boxShadow: boxShadow, slope: slope, courses: courses,
    timberFrame: timberFrame, wall: wall, archPath: archPath, pointPath: pointPath, win: win, door: door, fascia: fascia,
    gableRoof: gableRoof, gableFront: gableFront, hipRoof: hipRoof, pyramid: pyramid, cone: cone, cylinder: cylinder, box: box,
    chimney: chimney, smoke: smoke, barrelEnd: barrelEnd, barrel: barrel, crate: crate, anvil: anvil, flag: flag,
    hangSign: hangSign, horseshoe: horseshoe, paving: paving, bush: bush, ring: ring
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.TownArtWS_prims = api;
})(typeof window !== 'undefined' ? window : this);
