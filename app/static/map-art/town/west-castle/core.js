/*
 * 织梦 · 城镇建筑美术 · 西式中世纪城堡 —— 公共画笔（core.js，尚未接入游戏）
 *
 * 3/4 斜俯视约定（docs/town-art-spec.md）：
 *   symbol 的占地矩形在 viewBox 底部；地面点 (x, g) 在高度 h 处画到屏幕 (x, up + g - h)。
 *   g 是占地内的进深坐标（0 = 占地后沿，d*48 = 前沿），up 是向上伸出的像素。
 * 画风：木刻线描 + 羊皮纸淡彩，不透明平涂 + 墨线，不用渐变 / 模糊。
 * 浏览器挂 window.TownArtWC.core；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var CELL = 48;
  var PAL = {
    ink: '#4a3826', paper: '#efdfb2', plaster: '#e9dcc0', wash: '#e3c47a', wood: '#c9a46a',
    st1: '#cfc0a2', st2: '#bfb093', st3: '#b1a287', grain: '#8a6a44', dark: '#6b4f32',
    tile: '#b5654a', red: '#9a3b2a', sl1: '#7d8790', sl2: '#5f6870', th1: '#d2b46c', th2: '#b8954e',
    grass: '#c9c79a', shadow: '#3a2c1e',
    // 规范表外的补充色（水面、洞口、炉火），都取自同一组暖灰 / 赭黄的邻近色
    water: '#a9b7a6', water2: '#93a394', water3: '#7c8d80', hole: '#4f3c29', glow: '#e39a4a'
  };

  function f(n) { return String(Math.round(n * 100) / 100); }
  function P(x, y) { return f(x) + ' ' + f(y); }
  function rng(seed) { // mulberry32
    return function () {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      var t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  function seedOf(s) { // FNV-1a，把 symbol id 变成种子
    var h = 2166136261 >>> 0;
    for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }
  function stroke(sw, op) {
    if (!sw) return '';
    return ' stroke="' + PAL.ink + '" stroke-width="' + f(sw) + '" stroke-linejoin="round" stroke-linecap="round"' +
      (op != null && op < 1 ? ' stroke-opacity="' + f(op) + '"' : '');
  }
  function path(d, fill, sw, op, extra) {
    return '<path d="' + d + '" fill="' + (fill || 'none') + '"' + stroke(sw, op) + (extra || '') + '/>';
  }
  function pts(a) { return 'M' + a.map(function (p) { return P(p[0], p[1]); }).join('L') + 'Z'; }
  function poly(a, fill, sw, op) { return path(pts(a), fill, sw, op); }
  function rectD(x, y, w, h) { return pts([[x, y], [x + w, y], [x + w, y + h], [x, y + h]]); }
  function rect(x, y, w, h, fill, sw, op) { return path(rectD(x, y, w, h), fill, sw, op); }
  function seg(x1, y1, x2, y2) { return 'M' + P(x1, y1) + 'L' + P(x2, y2); }
  function lines(d, sw, op) { return d ? path(d, 'none', sw || 0.8, op == null ? 0.5 : op) : ''; }
  function ellD(cx, cy, rx, ry) {
    return 'M' + P(cx - rx, cy) + 'A' + f(rx) + ' ' + f(ry) + ' 0 1 0 ' + P(cx + rx, cy) +
      'A' + f(rx) + ' ' + f(ry) + ' 0 1 0 ' + P(cx - rx, cy) + 'Z';
  }
  function ell(cx, cy, rx, ry, fill, sw, op) { return path(ellD(cx, cy, rx, ry), fill, sw, op); }
  function shadow(d) { return '<path d="' + d + '" fill="' + PAL.shadow + '" fill-opacity="0.18"/>'; }
  function clip(id, d, inner) {
    return '<defs><clipPath id="' + id + '"><path d="' + d + '"/></clipPath></defs><g clip-path="url(#' + id + ')">' + inner + '</g>';
  }
  function g(inner, tr) { return '<g' + (tr ? ' transform="' + tr + '"' : '') + '>' + inner + '</g>'; }

  /**
   * 方整石砌缝：矩形 (x,y,w,h) 内横缝每 ch 一道、竖缝每 cw 一道且逐层错半块。
   * (ox, oy) 是该矩形所在的世界偏移，用来让相邻瓦片 / 部件的石缝对齐。
   */
  function ashlarD(x, y, w, h, ch, cw, ox, oy) {
    ox = ox || 0; oy = oy || 0;
    var d = '', k0 = Math.floor((y + oy) / ch);
    for (var k = k0; k * ch - oy < y + h - 0.5; k++) {
      var top = Math.max(y, k * ch - oy), bot = Math.min(y + h, (k + 1) * ch - oy);
      if (k * ch - oy > y + 0.5) d += seg(x, k * ch - oy, x + w, k * ch - oy);
      if (bot - top < 1.5) continue;
      var off = (((k % 2) + 2) % 2) ? cw / 2 : 0;
      var xs = Math.ceil((x + ox - off) / cw) * cw - ox + off;
      for (var xx = xs; xx < x + w - 0.5; xx += cw) if (xx > x + 0.5) d += seg(xx, top + 0.6, xx, bot - 0.6);
    }
    return d;
  }
  function ashlar(x, y, w, h, ch, cw, ox, oy, op) { return lines(ashlarD(x, y, w, h, ch, cw, ox, oy), 0.8, op == null ? 0.45 : op); }
  /** 竖排线（阴面、木纹） */
  function hatchD(x0, x1, y0, y1, step) {
    var d = '';
    for (var x = x0 + step / 2; x < x1; x += step) d += seg(x, y0, x, y1);
    return d;
  }
  /** 横排线（瓦行、板缝） */
  function rowsD(x0, x1, y0, y1, step, tick, seed) {
    var d = '', r = rng(seed || 1), k = 0;
    for (var y = y0 + step; y < y1 - 0.5; y += step, k++) {
      d += seg(x0, y, x1, y);
      if (tick) for (var x = x0 + (k % 2 ? tick / 2 : 0) + r() * 2; x < x1 - 1; x += tick) d += seg(x, y, x, y - step + 0.8);
    }
    return d;
  }

  /** 立方体两面：平面 x0..x1 × g0..g1，高度 h0..h1。 */
  function boxFaces(up, x0, x1, g0, g1, h0, h1) {
    var yt0 = up + g0 - h1, yt1 = up + g1 - h1, yb = up + g1 - h0;
    return {
      top: [[x0, yt0], [x1, yt0], [x1, yt1], [x0, yt1]],
      front: [[x0, yt1], [x1, yt1], [x1, yb], [x0, yb]],
      yt0: yt0, yt1: yt1, yb: yb
    };
  }
  function box(up, x0, x1, g0, g1, h0, h1, topFill, frontFill, sw) {
    var b = boxFaces(up, x0, x1, g0, g1, h0, h1);
    return poly(b.front, frontFill || PAL.st2, sw == null ? 1 : sw) + poly(b.top, topFill || PAL.plaster, sw == null ? 1 : sw);
  }

  // ---------------- 石面、垛口、箭窗 ----------------
  var CH = 8, CW = 16; // 石块：层高 8、块长 16（能整除 48，相邻瓦片石缝对齐）
  /** 竖直石面：x0..x1，屏幕 yTop..yBot；石层从 yBot（地面线）往上数。 */
  function stoneFace(x0, x1, yTop, yBot, fill, op) {
    return rect(x0, yTop, x1 - x0, yBot - yTop, fill || PAL.st2, 1.2) +
      ashlar(x0, yTop, x1 - x0, yBot - yTop, CH, CW, 0, -yBot + Math.ceil(yBot / CH) * CH, op);
  }
  /** 垛口前脸的折线：墙顶在 yBase，垛高 ph，垛口凹 cut，周期 per，垛宽 m；ox 让相邻件对齐。 */
  function battleD(x0, x1, yBase, ph, cut, per, m, ox) {
    ox = ox || 0;
    var d = 'M' + P(x0, yBase), xs = [x0];
    var k0 = Math.floor((x0 + ox) / per) - 1;
    for (var k = k0; k * per - ox < x1 + per; k++) {
      var a = k * per - ox, b = a + m;
      if (a > x0 && a < x1) xs.push(a);
      if (b > x0 && b < x1) xs.push(b);
    }
    xs.push(x1);
    function hi(x) { var u = (((x + ox) % per) + per) % per; return u < m - 0.01; }
    for (var i = 0; i < xs.length - 1; i++) {
      var mid = (xs[i] + xs[i + 1]) / 2, y = yBase - ph + (hi(mid) ? 0 : cut);
      d += 'L' + P(xs[i], y) + 'L' + P(xs[i + 1], y);
    }
    return d + 'L' + P(x1, yBase) + 'Z';
  }
  function battle(x0, x1, yBase, ph, cut, fill, ox, per, m) {
    return path(battleD(x0, x1, yBase, ph, cut, per || 12, m || 7, ox), fill || PAL.st2, 1.2);
  }
  /** 箭窗：浅色石框 + 深色窄缝；cross = 十字形箭窗。 */
  function arrowSlit(x, yTop, h, cross) {
    var o = rect(x - 2.6, yTop - 1.5, 5.2, h + 3, PAL.st1, 0.8, 0.8);
    o += path(seg(x, yTop, x, yTop + h), 'none', 1.8);
    if (cross) o += path(seg(x - 2.4, yTop + h * 0.42, x + 2.4, yTop + h * 0.42), 'none', 1.4);
    return o;
  }
  /** 尖拱（哥特尖券）窗 / 门洞的路径 */
  function lancetD(x, y, w, h) {
    var sy = y + w * 0.87;
    return 'M' + P(x, y + h) + 'L' + P(x, sy) + 'A' + f(w) + ' ' + f(w) + ' 0 0 1 ' + P(x + w / 2, y) +
      'A' + f(w) + ' ' + f(w) + ' 0 0 1 ' + P(x + w, sy) + 'L' + P(x + w, y + h) + 'Z';
  }
  /** 半圆拱（罗曼式）路径 */
  function archD(x, y, w, h) {
    var r = w / 2;
    return 'M' + P(x, y + h) + 'L' + P(x, y + r) + 'A' + f(r) + ' ' + f(r) + ' 0 0 1 ' + P(x + w, y + r) + 'L' + P(x + w, y + h) + 'Z';
  }
  /** 窗：石框 + 深色窗洞 + 竖棂；pointed 选尖拱 */
  function windowA(x, y, w, h, pointed, mullion) {
    var dd = pointed ? lancetD : archD;
    var o = path(dd(x - 1.6, y - 1.6, w + 3.2, h + 2.4), PAL.st1, 0.9);
    o += path(dd(x, y, w, h), PAL.hole, 1);
    if (mullion) o += path(seg(x + w / 2, y + w * 0.5, x + w / 2, y + h), 'none', 1, 0.8) + path(seg(x, y + h * 0.62, x + w, y + h * 0.62), 'none', 0.7, 0.6);
    return o;
  }
  /** 木门（拱顶）：竖板缝 + 两道铁条 + 门环 */
  function doorA(x, yGround, w, h, pointed) {
    var y = yGround - h, dd = pointed ? lancetD : archD;
    var o = path(dd(x - 2, y - 2, w + 4, h + 2), PAL.st1, 1);
    o += path(dd(x, y, w, h), PAL.dark, 1.2);
    o += lines(hatchD(x, x + w, y + w * 0.35, yGround, w / 4), 0.7, 0.5);
    o += path(seg(x + 1, y + h * 0.45, x + w - 1, y + h * 0.45) + seg(x + 1, y + h * 0.8, x + w - 1, y + h * 0.8), 'none', 1.1, 0.85);
    return o + ell(x + w * 0.72, y + h * 0.62, 1.1, 1.1, PAL.wash, 0.6);
  }
  /** 吊闸：铁格栅（竖杆带尖 + 横杆），从 yTop 垂到 yBot。 */
  function portcullis(x0, x1, yTop, yBot, n) {
    var o = '', d = '', step = (x1 - x0) / n;
    for (var i = 0; i <= n; i++) {
      var x = x0 + i * step;
      d += seg(x, yTop, x, yBot - 2) + 'M' + P(x - 1.2, yBot - 2) + 'L' + P(x, yBot + 1) + 'L' + P(x + 1.2, yBot - 2);
    }
    for (var y = yTop + 5; y < yBot - 3; y += 6) d += seg(x0 - 0.5, y, x1 + 0.5, y);
    o += path(d, 'none', 1.3);
    return o;
  }
  /** 旗：旗杆 + 燕尾旗（红底、浅色斜带）；dir = 1 向右飘 */
  function flag(px, yBase, poleH, dir, size) {
    dir = dir || 1; size = size || 1;
    var top = yBase - poleH, L = 20 * size, Hh = 9 * size;
    var o = path(seg(px, yBase, px, top), 'none', 1.5);
    var d = 'M' + P(px, top + 1) + 'Q' + P(px + dir * L * 0.5, top - 2) + ' ' + P(px + dir * L, top + 1) +
      'L' + P(px + dir * L * 0.72, top + 1 + Hh * 0.5) + 'L' + P(px + dir * L, top + 1 + Hh) +
      'Q' + P(px + dir * L * 0.5, top + Hh + 3) + ' ' + P(px, top + 1 + Hh) + 'Z';
    o += path(d, PAL.red, 1.1);
    o += path(seg(px + dir * 2, top + 2 + Hh * 0.2, px + dir * L * 0.55, top + 1 + Hh * 0.8), 'none', 2.2 * size, 1, ' stroke="' + PAL.paper + '"').replace(' stroke="' + PAL.ink + '"', '');
    return o + ell(px, top - 1, 1.6, 1.6, PAL.wash, 0.8);
  }
  /** 盾形纹章：底色 + 一道十字或山形 */
  function shield(cx, cy, s, fill, charge) {
    var d = 'M' + P(cx - s, cy - s) + 'L' + P(cx + s, cy - s) + 'L' + P(cx + s, cy) + 'Q' + P(cx + s, cy + s * 0.9) + ' ' + P(cx, cy + s * 1.35) +
      'Q' + P(cx - s, cy + s * 0.9) + ' ' + P(cx - s, cy) + 'Z';
    var o = path(d, fill || PAL.red, 1);
    if (charge === 'chevron') o += path('M' + P(cx - s * 0.75, cy + s * 0.35) + 'L' + P(cx, cy - s * 0.45) + 'L' + P(cx + s * 0.75, cy + s * 0.35), 'none', 0, 1, ' stroke="' + PAL.wash + '" stroke-width="' + f(s * 0.4) + '"');
    else o += path(seg(cx, cy - s * 0.8, cx, cy + s * 1.05) + seg(cx - s * 0.8, cy - s * 0.15, cx + s * 0.8, cy - s * 0.15), 'none', 0, 1, ' stroke="' + PAL.wash + '" stroke-width="' + f(s * 0.32) + '"');
    return o + path(d, 'none', 1);
  }

  // ---------------- 体块：带垛口的方台、圆柱、锥顶、坡顶 ----------------
  var K = 0.6; // 圆形部件的椭圆压扁比（只用于圆塔 / 锥顶，让圆形读得出是圆柱）

  /** 前立面上的垛口缺口：在前脸顶边 yTop 处每 per 一个缺口（宽 per-m，深 cut）。 */
  function crenelNotches(x0, x1, yTop, cut, per, m, fill, ox) {
    var o = '';
    per = per || 12; m = m || 7; ox = ox || 0;
    var k0 = Math.floor((x0 + ox) / per);
    for (var k = k0; k * per - ox < x1; k++) {
      var a = k * per - ox + m, b = a + per - m;
      a = Math.max(a, x0 + 2); b = Math.min(b, x1 - 2);
      if (b - a < 2.5) continue;
      o += rect(a, yTop - 0.4, b - a, cut + 0.4, fill || PAL.st3, 0.9);
    }
    return o;
  }

  /**
   * 带垛口的方台（塔、主楼、墙体都用它）：x0..x1 × g0..g1，墙身 h0 → 走道 h，女墙再高 ph。
   * 画：前脸石砌 + 前脸垛口缺口 + 顶边石沿 + 凹下去的走道地面 + 背面女墙内侧 + 两侧女墙上的缺口。
   */
  function crenBox(up, x0, x1, g0, g1, h0, h, opt) {
    opt = opt || {};
    var ph = opt.ph || 8, e = opt.e || 4, cut = opt.cut || 4, ox = opt.ox || 0;
    var front = opt.front || PAL.st2, rim = opt.rim || PAL.st1, floor = opt.floor || PAL.plaster;
    var b = boxFaces(up, x0, x1, g0, g1, h0, h + ph), o = '';
    o += stoneFace(x0, x1, b.yt1, b.yb, front);
    if (opt.shade) o += rect(x1 - (x1 - x0) * opt.shade, b.yt1, (x1 - x0) * opt.shade, b.yb - b.yt1, PAL.st3, 0) +
      lines(hatchD(x1 - (x1 - x0) * opt.shade, x1, b.yt1 + 2, b.yb - 2, 3), 0.6, 0.35) + rect(x0, b.yt1, x1 - x0, b.yb - b.yt1, 'none', 1.2);
    o += poly(b.top, rim, 1.2);
    var iy0 = b.yt0 + e, iy1 = b.yt1 - e;
    if (iy1 - iy0 > 2) {
      o += rect(x0 + e, iy0, x1 - x0 - 2 * e, iy1 - iy0, PAL.st3, 0.9);
      var fy0 = iy0 + ph;
      if (iy1 - fy0 > 1) {
        if (opt.deck) o += deck(x0 + e, x1 - e, fy0, iy1, opt.deck.seed, opt.deck);
        else {
          o += rect(x0 + e, fy0, x1 - x0 - 2 * e, iy1 - fy0, floor, 0.8);
          if (opt.planks) o += lines(rowsD(x0 + e, x1 - e, fy0, iy1, 4, 0, 3), 0.6, 0.35);
        }
      }
      // 两侧女墙上的缺口（俯看是一格格的小缺）
      for (var y = iy0 + 6; y < iy1 - 3; y += 12) {
        o += rect(x0 + 0.6, y, e - 1.2, 5, PAL.st3, 0.6, 0.7) + rect(x1 - e + 0.6, y, e - 1.2, 5, PAL.st3, 0.6, 0.7);
      }
      // 背面女墙顶上的缺口
      o += crenelNotches(x0 + e, x1 - e, b.yt0 - 0.2, 2.2, 12, 7, PAL.st3, ox);
    }
    o += crenelNotches(x0, x1, b.yt1, cut, 12, 7, floor, ox);
    return { svg: o, top: b.yt0, front: b.yt1, base: b.yb, floorY: iy0 + ph };
  }

  /**
   * 石板平台：矩形 x0..x1 × y0..y1 内铺错缝石板（层高 6、块长 8–15，由种子派生），
   * 北沿、西沿女墙在台面上投一条阴影（光从左上）。
   * opt.hatch = [x, y] 画楼梯口；opt.plinth = [x, y] 画旗杆座（旗杆底落在 y）。
   */
  function deck(x0, x1, y0, y1, seed, opt) {
    opt = opt || {};
    var r = rng(seed || 7), o = rect(x0, y0, x1 - x0, y1 - y0, PAL.plaster, 0.8), d = '';
    for (var y = y0; y < y1 - 0.5; y += 6) {
      var yb = Math.min(y1, y + 6);
      if (y > y0) d += seg(x0, y, x1, y);
      var x = x0 - r() * 8;
      for (;;) { x += 8 + r() * 7; if (x >= x1 - 2) break; if (x > x0 + 2) d += seg(x, y + 0.5, x, yb - 0.5); }
    }
    o += lines(d, 0.8, 0.42);
    var sw = Math.min(4, (x1 - x0) / 4);
    o += shadow(pts([[x0, y0], [x1, y0], [x1, y0 + 3.5], [x0 + sw, y0 + 3.5], [x0 + sw, y1], [x0, y1]]));
    if (opt.hatch) o += stairHatch(opt.hatch[0], opt.hatch[1]);
    if (opt.plinth) o += plinth(opt.plinth[0], opt.plinth[1]);
    return o;
  }
  /** 楼梯口：石框 + 暗口 + 两级下行石阶 + 掀起立在北沿的木盖板（两道铁条）。(x, y) 为洞口左上。 */
  function stairHatch(x, y) {
    var w = 12, h = 9, o = '';
    o += rect(x - 1.5, y - 1.5, w + 3, h + 3, PAL.st1, 1);
    o += rect(x, y, w, h, PAL.hole, 0.9);
    o += rect(x, y + h - 3, w, 3, PAL.st2, 0.6) + rect(x, y + h - 6, w * 0.7, 3, PAL.st3, 0.6);
    o += poly([[x, y - 1.5], [x + w, y - 1.5], [x + w - 1, y - 9], [x + 1, y - 9]], PAL.wood, 1);
    o += lines(seg(x + 4, y - 2, x + 4, y - 8.5) + seg(x + 8, y - 2, x + 8, y - 8.5), 0.9, 0.75);
    return o;
  }
  /** 旗杆座：两级方石墩，旗杆底落在 (px, py)。 */
  function plinth(px, py) {
    return rect(px - 6, py - 2.5, 12, 5, PAL.st1, 1) + rect(px - 3.5, py - 5, 7, 2.8, PAL.st2, 0.9);
  }

  /** 圆柱身（前半）：中心 (cx, cg)，半径 r，高度 h0..h1。返回 svg 和顶椭圆中心 y。 */
  function cylinder(up, cx, cg, r, h0, h1, fill, shade) {
    var ry = r * K, yb = up + cg - h0, yt = up + cg - h1;
    var d = 'M' + P(cx - r, yt) + 'L' + P(cx - r, yb) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 0 ' + P(cx + r, yb) + 'L' + P(cx + r, yt) + 'Z';
    var o = path(d, fill || PAL.st2, 1.4);
    var id = 'cyl' + (++uidN);
    var inner = '';
    // 石层：一圈圈下弧
    for (var y = yb - CH; y > yt + 2; y -= CH) inner += 'M' + P(cx - r, y) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 0 ' + P(cx + r, y);
    var s = '<path d="' + inner + '" fill="none"' + stroke(0.8, 0.42) + '/>';
    // 竖缝：按角度错落
    var vd = '', layer = 0;
    for (var y2 = yb; y2 > yt + 4; y2 -= CH, layer++) {
      for (var a = (layer % 2 ? 0.22 : 0.05); a < Math.PI; a += 0.36) {
        var xx = cx - r * Math.cos(a), yy = y2 + ry * Math.sin(a);
        vd += seg(xx, yy - 1, xx, yy - CH + 1);
      }
    }
    s += '<path d="' + vd + '" fill="none"' + stroke(0.7, 0.35) + '/>';
    if (shade !== false) s += rect(cx + r * 0.42, yt - 2, r * 0.6, yb - yt + ry + 4, PAL.st3, 0, 1).replace('/>', ' fill-opacity="0.75"/>') +
      lines(hatchD(cx + r * 0.42, cx + r, yt, yb + ry, 3), 0.6, 0.35);
    o += '<defs><clipPath id="__ID__' + id + '"><path d="' + d + '"/></clipPath></defs><g clip-path="url(#__ID__' + id + ')">' + s + '</g>';
    o += path(d, 'none', 1.5);
    return { svg: o, yt: yt, yb: yb, ry: ry };
  }
  var uidN = 0;
  function resetUid() { uidN = 0; }

  /** 圆塔顶：女墙一圈 + 凹下去的平台 + 前沿垛口缺口。cyl 已画到 h1（含女墙高度 ph）。 */
  function roundTop(cx, yt, r, ph, floor) {
    var ry = r * K, o = '';
    o += ell(cx, yt, r, ry, PAL.st1, 1.3);
    var ri = r - 4.5, ryi = ri * K;
    o += ell(cx, yt, ri, ryi, PAL.st3, 0.9);
    var id = 'rt' + (++uidN);
    o += '<defs><clipPath id="__ID__' + id + '"><path d="' + ellD(cx, yt, ri, ryi) + '"/></clipPath></defs>' +
      '<g clip-path="url(#__ID__' + id + ')">' + ell(cx, yt + ph, ri, ryi, floor || PAL.plaster, 0.8) + '</g>';
    // 后沿缺口（在背面女墙顶）与前沿缺口（前脸上缘）
    var n = Math.max(6, Math.round(Math.PI * r / 12));
    for (var i = 0; i < n; i++) {
      var a = Math.PI * (i + 0.5) / n, x = cx - r * Math.cos(a);
      var wdt = Math.max(1.6, 4.2 * Math.sin(a));
      if (i % 2 === 0) {
        var yf = yt + ry * Math.sin(a);
        o += rect(x - wdt / 2, yf - 0.6, wdt, 4.2, floor || PAL.plaster, 0.8);
        var yk = yt - ri * K * Math.sin(a);
        o += rect(x - wdt / 2 * 0.9, yk - 0.4, wdt * 0.9, 2.2, PAL.st3, 0.6, 0.8);
      }
    }
    return o;
  }

  /** 锥顶（前半轮廓）：底椭圆中心 (cx, yb)，半径 r，尖高 hh。tile=true 画鱼鳞瓦。 */
  function cone(cx, yb, r, hh, fill, scale) {
    var ry = r * K, ax = cx, ay = yb - hh;
    var d = 'M' + P(cx - r, yb) + 'L' + P(ax, ay) + 'L' + P(cx + r, yb) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 1 ' + P(cx - r, yb) + 'Z';
    var o = path(d, fill || PAL.sl1, 1.4);
    var id = 'cn' + (++uidN), s = '';
    // 右侧阴面
    s += path('M' + P(ax, ay) + 'L' + P(cx + r, yb) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 1 ' + P(cx + r * 0.3, yb + ry * 0.95) + 'Z', PAL.sl2, 0).replace('/>', ' fill-opacity="0.7"/>');
    // 瓦行：随高度缩小的下弧
    var rows = Math.max(3, Math.round(hh / 7));
    for (var i = 1; i < rows; i++) {
      var t = i / rows, rr = r * t, yy = ay + hh * t;
      s += path('M' + P(ax - rr, yy) + 'A' + f(rr) + ' ' + f(rr * K) + ' 0 0 0 ' + P(ax + rr, yy), 'none', 0.8, 0.5);
      if (scale !== false) {
        var nn = Math.max(2, Math.round(rr / 4));
        for (var j = 0; j <= nn; j++) {
          var a = Math.PI * j / nn, x = ax - rr * Math.cos(a), y = yy + rr * K * Math.sin(a);
          s += path(seg(x, y, x + (ax - x) * 0.12, y - hh / rows * 0.85), 'none', 0.6, 0.35);
        }
      }
    }
    o += '<defs><clipPath id="__ID__' + id + '"><path d="' + d + '"/></clipPath></defs><g clip-path="url(#__ID__' + id + ')">' + s + '</g>';
    return o + path(d, 'none', 1.5);
  }

  /** 在多边形 d 里画平行瓦行（斜线由 (ax,ay)->(bx,by) 方向给出，按 step 平移）。 */
  function roofRows(d, x0, y0, x1, y1, step, vertical, op) {
    var id = 'rr' + (++uidN), s = '';
    if (vertical) for (var x = x0 + step; x < x1; x += step) s += seg(x, y0 - 2, x, y1 + 2);
    else for (var y = y0 + step; y < y1; y += step) s += seg(x0 - 2, y, x1 + 2, y);
    return '<defs><clipPath id="__ID__' + id + '"><path d="' + d + '"/></clipPath></defs><g clip-path="url(#__ID__' + id + ')">' +
      path(s, 'none', 0.8, op == null ? 0.5 : op) + '</g>';
  }

  /**
   * 东西向屋脊的双坡顶（长厅用）：前坡整片可见，屋脊在进深中线；后坡在屋脊不够高时露一窄条。
   * 墙高 hw，脊高 rh（在墙顶之上），ov 为两端挑出。
   */
  function gableX(up, x0, x1, g0, g1, hw, rh, fill, dark, ov) {
    ov = ov == null ? 3 : ov;
    var yE = up + g1 - hw + 3, yR = up + (g0 + g1) / 2 - hw - rh, yB = up + g0 - hw, o = '';
    if (yB < yR - 1) {
      var bd = pts([[x0 - ov, yB], [x1 + ov, yB], [x1 + ov, yR], [x0 - ov, yR]]);
      o += path(bd, dark || PAL.sl2, 1.3) + roofRows(bd, x0 - ov, yB, x1 + ov, yR, 4, false, 0.4);
    }
    var fd = pts([[x0 - ov, yR], [x1 + ov, yR], [x1 + ov, yE], [x0 - ov, yE]]);
    o += path(fd, fill || PAL.sl1, 1.4);
    o += roofRows(fd, x0 - ov, yR, x1 + ov, yE, 5, false, 0.5);
    // 竖向错缝的短瓦缝
    var id = 'rs' + (++uidN), s = '', k = 0;
    for (var y = yR + 5; y < yE; y += 5, k++) for (var x = x0 - ov + (k % 2 ? 3 : 6); x < x1 + ov; x += 6) s += seg(x, y - 5, x, y);
    o += '<defs><clipPath id="__ID__' + id + '"><path d="' + fd + '"/></clipPath></defs><g clip-path="url(#__ID__' + id + ')">' + path(s, 'none', 0.6, 0.3) + '</g>';
    o += path(seg(x0 - ov - 1, yR, x1 + ov + 1, yR), 'none', 2.2);
    return { svg: o, ridge: yR, eave: yE };
  }

  /**
   * 南北向屋脊的双坡顶（山墙朝前，礼拜堂、附属小屋用）：左坡亮、右坡暗，前山墙三角另画。
   * 返回 apex（前山尖屏幕坐标）与 base（山墙底 y）。
   */
  function gableG(up, x0, x1, g0, g1, hw, rh, fill, dark, ov) {
    ov = ov == null ? 3 : ov;
    var xm = (x0 + x1) / 2, yb0 = up + g0 - hw, yb1 = up + g1 - hw, o = '';
    var L = pts([[x0 - ov, yb0 + 2], [xm, yb0 - rh], [xm, yb1 - rh], [x0 - ov, yb1 + 2]]);
    var R = pts([[xm, yb0 - rh], [x1 + ov, yb0 + 2], [x1 + ov, yb1 + 2], [xm, yb1 - rh]]);
    o += path(L, fill || PAL.sl1, 1.3) + roofRows(L, x0 - ov, yb0 - rh, xm, yb1 + 2, 4, true, 0.45);
    o += path(R, dark || PAL.sl2, 1.3) + roofRows(R, xm, yb0 - rh, x1 + ov, yb1 + 2, 4, true, 0.4);
    o += path(seg(xm, yb0 - rh - 0.5, xm, yb1 - rh), 'none', 2);
    return { svg: o, apex: [xm, yb1 - rh], base: yb1, eaveL: [x0 - ov, yb1 + 2], eaveR: [x1 + ov, yb1 + 2] };
  }

  /** 前山墙三角（墙面色 + 石缝），配合 gableG；返回 svg。 */
  function gableFront(gr, x0, x1, fill, stone) {
    var d = pts([[x0, gr.base], [gr.apex[0], gr.apex[1] + 3], [x1, gr.base]]);
    var o = path(d, fill || PAL.st2, 1.3);
    if (stone !== false) {
      var id = 'gf' + (++uidN);
      o += '<defs><clipPath id="__ID__' + id + '"><path d="' + d + '"/></clipPath></defs><g clip-path="url(#__ID__' + id + ')">' +
        ashlar(x0, gr.apex[1], x1 - x0, gr.base - gr.apex[1], CH, CW, 0, 0) + '</g>';
    }
    // 山墙外沿的封檐板
    o += path('M' + P(gr.eaveL[0], gr.eaveL[1]) + 'L' + P(gr.apex[0], gr.apex[1]) + 'L' + P(gr.eaveR[0], gr.eaveR[1]), 'none', 2.2);
    return o;
  }

  /** 木板 / 夯土立面：用于附属小屋。woodFrame=true 画木筋（半木结构）。 */
  function timberFace(x0, x1, yTop, yBot, woodFrame) {
    var o = rect(x0, yTop, x1 - x0, yBot - yTop, woodFrame ? PAL.plaster : PAL.wood, 1.3);
    if (woodFrame) {
      var d = seg(x0 + 1, yTop + 2, x1 - 1, yTop + 2) + seg(x0 + 1, yBot - 2, x1 - 1, yBot - 2);
      var n = Math.max(2, Math.round((x1 - x0) / 14));
      for (var i = 0; i <= n; i++) { var x = x0 + 1.5 + (x1 - x0 - 3) * i / n; d += seg(x, yTop + 2, x, yBot - 2); }
      for (var j = 0; j < n; j += 2) {
        var xa = x0 + 1.5 + (x1 - x0 - 3) * j / n, xb = x0 + 1.5 + (x1 - x0 - 3) * (j + 1) / n;
        d += seg(xa, yBot - 2, xb, yTop + 2);
      }
      o += '<path d="' + d + '" fill="none" stroke="' + PAL.grain + '" stroke-width="2.2" stroke-linecap="square"/>';
    } else {
      o += lines(hatchD(x0, x1, yTop + 1, yBot - 1, 4), 0.7, 0.45);
    }
    return o + rect(x0, yTop, x1 - x0, yBot - yTop, 'none', 1.3);
  }

  /** 墙脚投影：建筑右侧和下方一条半透明暗带（最多下伸 6 px，不超出 viewBox）。 */
  function dropShadow(x0, x1, yTopRight, yBase, wMax, hMax) {
    var dx = 6, dy = Math.min(5, hMax - yBase);
    return shadow(pts([[x1, yTopRight + 4], [Math.min(wMax, x1 + dx), yTopRight + 8], [Math.min(wMax, x1 + dx), yBase + dy], [x0 + 4, yBase + dy], [x0 + 4, yBase], [x1, yBase]]));
  }

  var API = {
    CELL: CELL, PAL: PAL, K: K, CH: CH, CW: CW, f: f, P: P, rng: rng, seedOf: seedOf, stroke: stroke, path: path, pts: pts, poly: poly,
    rectD: rectD, rect: rect, seg: seg, lines: lines, ellD: ellD, ell: ell, shadow: shadow, clip: clip, g: g,
    ashlarD: ashlarD, ashlar: ashlar, hatchD: hatchD, rowsD: rowsD, boxFaces: boxFaces, box: box,
    stoneFace: stoneFace, battleD: battleD, battle: battle, arrowSlit: arrowSlit, lancetD: lancetD, archD: archD,
    windowA: windowA, doorA: doorA, portcullis: portcullis, flag: flag, shield: shield,
    crenelNotches: crenelNotches, crenBox: crenBox, deck: deck, stairHatch: stairHatch, plinth: plinth, cylinder: cylinder, roundTop: roundTop, cone: cone, resetUid: resetUid,
    roofRows: roofRows, gableX: gableX, gableG: gableG, gableFront: gableFront, timberFace: timberFace, dropShadow: dropShadow
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else { root.TownArtWC = root.TownArtWC || {}; root.TownArtWC.core = API; }
})(this);
