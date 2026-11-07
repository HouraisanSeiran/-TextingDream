/*
 * 织梦 · 城镇工业与基础设施素材：公共绘图原语（3/4 斜俯视，尚未接入游戏）
 *
 * 坐标约定（所有 draw 函数共用）：地面坐标，占地矩形是 x∈[0,W]、y∈[0,D]，
 * y=0 是后沿（北），y=D 是前沿（南，锚点所在）。高度向上画成负 y：
 * 地面点 (x, y) 抬高 h 后画在 (x, y - h)。symbol 组装时整体下移上伸像素 U。
 *
 * 浏览器挂 window.TownArtInfraCore；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var CELL = 48;
  function f(n) { return String(Math.round(n * 100) / 100); }
  function rng(seed) { // mulberry32
    return function () {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      var t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  function hashStr(s) {
    var h = 2166136261;
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }
  function pts(a) { return a.map(function (p) { return f(p[0]) + ',' + f(p[1]); }).join(' '); }
  function at(fill, ink, w, extra) {
    return ' fill="' + (fill || 'none') + '"' +
      (ink ? ' stroke="' + ink + '" stroke-width="' + f(w || 1) + '" stroke-linejoin="round" stroke-linecap="round"' : '') +
      (extra ? ' ' + extra : '');
  }
  function poly(a, fill, ink, w, extra) { return '<polygon points="' + pts(a) + '"' + at(fill, ink, w, extra) + '/>'; }
  function pl(a, ink, w, extra) { return '<polyline points="' + pts(a) + '"' + at(null, ink, w, extra) + '/>'; }
  function path(d, fill, ink, w, extra) { return '<path d="' + d + '"' + at(fill, ink, w, extra) + '/>'; }
  function rect(x, y, w, h, fill, ink, lw, extra) {
    return '<rect x="' + f(x) + '" y="' + f(y) + '" width="' + f(w) + '" height="' + f(h) + '"' + at(fill, ink, lw, extra) + '/>';
  }
  function ell(cx, cy, rx, ry, fill, ink, lw, extra) {
    return '<ellipse cx="' + f(cx) + '" cy="' + f(cy) + '" rx="' + f(rx) + '" ry="' + f(ry) + '"' + at(fill, ink, lw, extra) + '/>';
  }
  function circ(cx, cy, r, fill, ink, lw, extra) { return ell(cx, cy, r, r, fill, ink, lw, extra); }
  function ln(x1, y1, x2, y2, ink, w, o) {
    return '<line x1="' + f(x1) + '" y1="' + f(y1) + '" x2="' + f(x2) + '" y2="' + f(y2) + '" stroke="' + ink +
      '" stroke-width="' + f(w || 1) + '" stroke-linecap="round"' + (o != null && o < 1 ? ' stroke-opacity="' + f(o) + '"' : '') + '/>';
  }
  /** 一组线段合成一条 path：segs = [[x1,y1,x2,y2], ...] */
  function lines(segs, ink, w, o) {
    if (!segs.length) return '';
    var d = segs.map(function (s) { return 'M' + f(s[0]) + ' ' + f(s[1]) + 'L' + f(s[2]) + ' ' + f(s[3]); }).join('');
    return '<path d="' + d + '" fill="none" stroke="' + ink + '" stroke-width="' + f(w || 1) + '" stroke-linecap="round"' +
      (o != null && o < 1 ? ' stroke-opacity="' + f(o) + '"' : '') + '/>';
  }
  function op(o) { return 'opacity="' + f(o) + '"'; }
  function fop(o) { return 'fill-opacity="' + f(o) + '"'; }
  /** clipPath：shape 是一段形状标记（不带样式也可），inner 被裁在里面 */
  function clip(id, shape, inner) {
    return '<defs><clipPath id="' + id + '">' + shape + '</clipPath></defs><g clip-path="url(#' + id + ')">' + inner + '</g>';
  }

  // ---------- 投影形体 ----------
  /** 立方体：地面矩形 x0..x1 × y0..y1，高 h。顶面 + 正面（南立面）。 */
  function box(x0, y0, x1, y1, h, top, front, ink, lw) {
    return poly([[x0, y0 - h], [x1, y0 - h], [x1, y1 - h], [x0, y1 - h]], top, ink, lw) +
      poly([[x0, y1 - h], [x1, y1 - h], [x1, y1], [x0, y1]], front, ink, lw);
  }
  /** 矩形体的投影：落在右下，最多下伸 dy（≤5）。 */
  function shadow(x0, y0, x1, y1, s, st, dy) {
    var d = dy == null ? Math.min(4, s * 0.3) : dy;
    return poly([[x1, y0], [x1 + s, y0 + s * 0.45], [x1 + s, y1 + d], [x0 + s * 0.45, y1 + d], [x0 + s * 0.45, y1], [x1, y1]],
      st.shadow, null, 0, fop(st.sop));
  }
  /** 圆形物的投影：一枚偏右下的椭圆。 */
  function shadowEll(cx, cy, rx, ry, s, st) {
    return ell(cx + s * 0.6, cy + Math.min(3, s * 0.15), rx + s * 0.4, ry, st.shadow, null, 0, fop(st.sop));
  }
  /** 东西向屋脊两坡顶（屋脊平行于前沿）：墙高 h，脊高 rh，出檐 ov。o = {wall, roof, back, ink, lw, ov} */
  function gableEW(x0, y0, x1, y1, h, rh, o) {
    var ym = (y0 + y1) / 2, ov = o.ov == null ? 3 : o.ov, ry = ym - h - rh, ey = y1 - h + ov;
    var s = poly([[x0, y1 - h], [x1, y1 - h], [x1, y1], [x0, y1]], o.wall, o.ink, o.lw);
    s += poly([[x0 - ov, y0 - h], [x1 + ov, y0 - h], [x1 + ov, ry], [x0 - ov, ry]], o.back || o.roof, o.ink, o.lw);
    s += poly([[x0 - ov, ry], [x1 + ov, ry], [x1 + ov, ey], [x0 - ov, ey]], o.roof, o.ink, o.lw);
    return { s: s, ry: ry, ey: ey, x0: x0 - ov, x1: x1 + ov };
  }
  /** 南北向屋脊两坡顶（山墙朝前）：左坡受光、右坡背光。o = {wall, roofL, roofR, ink, lw, ov} */
  function gableNS(x0, y0, x1, y1, h, rh, o) {
    var xm = (x0 + x1) / 2, ov = o.ov == null ? 3 : o.ov, fy = y1 + 2;
    var s = poly([[x0, y1], [x0, y1 - h], [xm, y1 - h - rh], [x1, y1 - h], [x1, y1]], o.wall, o.ink, o.lw);
    var L = [[x0 - ov, y0 - h + ov], [xm, y0 - h - rh], [xm, fy - h - rh], [x0 - ov, fy - h + ov]];
    var R = [[x1 + ov, y0 - h + ov], [xm, y0 - h - rh], [xm, fy - h - rh], [x1 + ov, fy - h + ov]];
    s += poly(R, o.roofR, o.ink, o.lw) + poly(L, o.roofL, o.ink, o.lw);
    return { s: s, L: L, R: R, apex: [xm, fy - h - rh], gableApex: [xm, y1 - h - rh] };
  }
  /** 立着的圆柱：地面圆心 (cx,cy)，椭圆半轴 rx/ry，高 h。 */
  function cyl(cx, cy, rx, ry, h, side, top, ink, lw) {
    var d = 'M' + f(cx - rx) + ' ' + f(cy - h) + 'L' + f(cx - rx) + ' ' + f(cy) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 0 ' +
      f(cx + rx) + ' ' + f(cy) + 'L' + f(cx + rx) + ' ' + f(cy - h) + 'Z';
    return path(d, side, ink, lw) + (top ? ell(cx, cy - h, rx, ry, top, ink, lw) : '');
  }
  /** 圆台：底半轴 (ax, ay)，顶半轴 (bx, by)，高 h。 */
  function frustum(cx, cy, ax, ay, bx, by, h, side, top, ink, lw) {
    var d = 'M' + f(cx - bx) + ' ' + f(cy - h) + 'L' + f(cx - ax) + ' ' + f(cy) + 'A' + f(ax) + ' ' + f(ay) + ' 0 0 0 ' +
      f(cx + ax) + ' ' + f(cy) + 'L' + f(cx + bx) + ' ' + f(cy - h) + 'Z';
    return path(d, side, ink, lw) + (top ? ell(cx, cy - h, bx, by, top, ink, lw) : '');
  }
  /** 穹顶（蜂窝窑、坟包）：底椭圆 rx/ry，顶高 hh。 */
  function dome(cx, cy, rx, ry, hh, fill, ink, lw) {
    var d = 'M' + f(cx - rx) + ' ' + f(cy) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + rx) + ' ' + f(cy) +
      'A' + f(rx) + ' ' + f(hh) + ' 0 0 0 ' + f(cx - rx) + ' ' + f(cy) + 'Z';
    return path(d, fill, ink, lw);
  }
  function domeD(cx, cy, rx, ry, hh) {
    return 'M' + f(cx - rx) + ' ' + f(cy) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + rx) + ' ' + f(cy) +
      'A' + f(rx) + ' ' + f(hh) + ' 0 0 0 ' + f(cx - rx) + ' ' + f(cy) + 'Z';
  }
  /** 拱门路径（半圆顶）：底边中点 (cx, by)，宽 w，竖边高 h。 */
  function archD(cx, by, w, h) {
    var r = w / 2;
    return 'M' + f(cx - r) + ' ' + f(by) + 'L' + f(cx - r) + ' ' + f(by - h) + 'A' + f(r) + ' ' + f(r) + ' 0 0 1 ' +
      f(cx + r) + ' ' + f(by - h) + 'L' + f(cx + r) + ' ' + f(by) + 'Z';
  }

  // ---------- 色板 ----------
  var WEST = {
    style: 'west', ink: '#4a3826', lw: 1.7, lwd: 1, shadow: '#3a2c1e', sop: 0.18,
    paper: '#efdfb2', plaster: '#e9dcc0', wash: '#e3c47a', wood: '#c9a46a',
    stone: '#cfc0a2', stone2: '#bfb093', stone3: '#b1a287', grain: '#8a6a44', dark: '#6b4f32',
    tile: '#b5654a', red: '#9a3b2a', slate: '#7d8790', slate2: '#5f6870', thatch: '#d2b46c', thatch2: '#b8954e',
    water: '#a9b8ad', water2: '#8fa49a', glow: '#f2d98a', iron: '#5c5a55', fire: '#d9853f', grass: '#c9c79a'
  };
  var EAST = {
    style: 'east', ink: '#c98f3c', ink2: '#f3c46a', lw: 1.6, lwd: 1, shadow: '#1f3c5b', sop: 0.2,
    cream: '#f1dcae', cream2: '#fbf0d4', ochre: '#eeb24f', ochre2: '#f8d78e', orange: '#e47c36', vermil: '#cd5030',
    umber: '#8c3d22', umber2: '#b5623a', teal: '#2e938d', teal2: '#6cc1b3', navy: '#1f3c5b', navy2: '#30697f',
    gray: '#5d6670', gray2: '#7b8590', stone: '#c9b48a', stone2: '#b39b6f', water: '#6cc1b3', water2: '#2e938d',
    fire: '#e47c36', grass: '#d9c58f', jade: '#8fd3c0'
  };

  // ---------- 纹理（都是按区域生成的线段，由调用方 clip 或自行限界） ----------
  /** 砖缝：x0..x1 × y0..y1，层高 rh，砖长 bw，交错。 */
  function brick(x0, y0, x1, y1, rh, bw, ink, o) {
    var s = [], row = 0;
    for (var y = y1 - rh; y > y0 + 0.5; y -= rh, row++) {
      s.push([x0, y, x1, y]);
    }
    row = 0;
    for (var yy = y1; yy > y0 + 0.5; yy -= rh, row++) {
      var top = Math.max(y0, yy - rh);
      for (var x = x0 + (row % 2 ? bw / 2 : bw); x < x1 - 1; x += bw) s.push([x, top, x, yy]);
    }
    return lines(s, ink, 0.8, o == null ? 0.5 : o);
  }
  /** 毛石墙：随机长短的石块缝。 */
  function rubble(x0, y0, x1, y1, rnd, ink, o) {
    var s = [], rh = 6;
    for (var yy = y1; yy > y0 + 1; yy -= rh) {
      var top = Math.max(y0, yy - rh);
      if (yy < y1) s.push([x0, yy, x1, yy]);
      var x = x0 + rnd() * 6;
      while (x < x1 - 3) { s.push([x, top, x, yy]); x += 6 + rnd() * 9; }
    }
    return lines(s, ink, 0.8, o == null ? 0.45 : o);
  }
  /** 木板：竖向（vertical=true）或横向的平行缝。 */
  function planks(x0, y0, x1, y1, step, vertical, ink, o) {
    var s = [];
    if (vertical) for (var x = x0 + step; x < x1 - 0.5; x += step) s.push([x, y0, x, y1]);
    else for (var y = y0 + step; y < y1 - 0.5; y += step) s.push([x0, y, x1, y]);
    return lines(s, ink, 0.8, o == null ? 0.5 : o);
  }
  /** 屋面瓦行（横向短排线，东西向屋顶）：在 x0..x1、y0..y1 的屋面上。 */
  function tileRows(x0, y0, x1, y1, step, ink, o, rnd) {
    var s = [];
    for (var y = y0 + step; y < y1 - 1; y += step) {
      s.push([x0 + 1, y, x1 - 1, y]);
      if (rnd) for (var x = x0 + 3 + rnd() * 4; x < x1 - 2; x += 5 + rnd() * 4) s.push([x, y, x, y - step * 0.6]);
    }
    return lines(s, ink, 0.8, o == null ? 0.5 : o);
  }
  /** 东方瓦垄：竖向平行线（东西向屋脊的前坡），间距 step。 */
  function tileRidges(x0, y0, x1, y1, step, ink, o) {
    var s = [];
    for (var x = x0 + step / 2; x < x1; x += step) s.push([x, y0, x, y1]);
    return lines(s, ink, 1, o == null ? 0.7 : o);
  }
  /** 一缕烟：西式淡墨圈，东方卷云头。从 (x, y) 往上。 */
  function smoke(x, y, st, n, seed) {
    var r = rng(seed || 7), o = '';
    for (var i = 0; i < (n || 3); i++) {
      var cx = x + i * 3 + r() * 3, cy = y - i * 8 - 3, rr = 3 + i * 1.3;
      if (st.style === 'west') o += circ(cx, cy, rr, '#e8dcc0', st.ink, 0.9, 'fill-opacity="0.85" stroke-opacity="0.55"');
      else o += circ(cx, cy, rr, '#fbf0d4', st.ink, 1, 'fill-opacity="0.9"') +
        path('M' + f(cx - rr * 0.4) + ' ' + f(cy + rr * 0.1) + 'a' + f(rr * 0.4) + ' ' + f(rr * 0.4) + ' 0 1 1 ' + f(rr * 0.5) + ' ' + f(-rr * 0.3), null, st.ink, 0.9);
    }
    return o;
  }
  /** 水面条带（码头、桥下）：x0..x1 × y0..y1，带几道波纹。 */
  function water(x0, y0, x1, y1, st, seed) {
    var r = rng(seed || 3), o = rect(x0, y0, x1 - x0, y1 - y0, st.water, null, 0), s = [];
    for (var y = y0 + 5; y < y1 - 2; y += 7) {
      for (var x = x0 + r() * 10; x < x1 - 6; x += 14 + r() * 10) s.push([x, y, x + 5 + r() * 4, y]);
    }
    return o + lines(s, st.style === 'west' ? st.ink : '#fbf0d4', 0.9, st.style === 'west' ? 0.35 : 0.75);
  }
  /** 柴堆：一摞横放的圆木截面。 */
  function logPile(x, y, n, rows, st) {
    var o = '', r = 3;
    for (var j = 0; j < rows; j++) {
      for (var i = 0; i < n - j; i++) {
        var cx = x + i * r * 2 + j * r + r, cy = y - r - j * r * 1.7;
        o += circ(cx, cy, r, st.style === 'west' ? st.wood : st.ochre, st.ink, 0.9) +
          circ(cx, cy, 1, st.style === 'west' ? st.grain : st.umber, null, 0);
      }
    }
    return o;
  }

  var api = {
    CELL: CELL, f: f, rng: rng, hashStr: hashStr, pts: pts,
    poly: poly, pl: pl, path: path, rect: rect, ell: ell, circ: circ, ln: ln, lines: lines, op: op, fop: fop, clip: clip,
    box: box, shadow: shadow, shadowEll: shadowEll, gableEW: gableEW, gableNS: gableNS, cyl: cyl, frustum: frustum,
    dome: dome, domeD: domeD, archD: archD,
    brick: brick, rubble: rubble, planks: planks, tileRows: tileRows, tileRidges: tileRidges, smoke: smoke, water: water, logPile: logPile,
    WEST: WEST, EAST: EAST
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.TownArtInfraCore = api;
})(typeof window !== 'undefined' ? window : this);
