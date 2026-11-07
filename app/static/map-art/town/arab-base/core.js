/*
 * 织梦 · 阿拉伯风格（人族）城镇素材公共工具：色板、种子随机、SVG 小工具（美术样板，尚未接入游戏）
 * 坐标约定：symbol 局部坐标 x 0..w*48，y = 0 为占地前沿，向上为负。
 * 浏览器挂 window.TownArtAB_core；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var PAL = {
    ink: '#4a3020', lime: '#f2ead8', lime2: '#e8dcc2', mud: '#d9b98a', mud2: '#c79d66', mud3: '#a97f4c',
    sand: '#e6cf9e', turq: '#3a9fa8', turq2: '#7cc6c2', cob: '#24467a', cob2: '#3d64a0', gold: '#c9a046',
    ochre: '#a8502e', ochre2: '#c86b3c', palm: '#5f7a3a', palm2: '#86a052', water: '#a9b8ad', ground: '#e3cf9f',
    wood: '#8a5a34', wood2: '#b07a48', dark: '#3a2418', hole: '#5a3a24', felt: '#5e4636', felt2: '#7a5c44', stone: '#d8c8a6', stone2: '#c2b08b'
  };
  function f(n) { return String(Math.round(n * 100) / 100); }
  function stroke(w, op, col) {
    if (!w) return '';
    return ' stroke="' + (col || PAL.ink) + '" stroke-width="' + f(w) + '"' + (op != null && op < 1 ? ' stroke-opacity="' + f(op) + '"' : '') + ' stroke-linejoin="round" stroke-linecap="round"';
  }
  function path(d, fill, sw, op, fop) {
    return '<path d="' + d + '" fill="' + (fill || 'none') + '"' + (fop != null ? ' fill-opacity="' + f(fop) + '"' : '') + stroke(sw, op) + '/>';
  }
  function line(d, sw, op, col) { return d ? '<path d="' + d + '" fill="none"' + stroke(sw || 1, op, col) + '/>' : ''; }
  function rectD(x, y, w, h) { return 'M' + f(x) + ' ' + f(y) + 'h' + f(w) + 'v' + f(h) + 'h' + f(-w) + 'Z'; }
  function rect(x, y, w, h, fill, sw, fop) { return path(rectD(x, y, w, h), fill, sw, null, fop); }
  function poly(pts) { return 'M' + pts.map(function (p) { return f(p[0]) + ' ' + f(p[1]); }).join('L') + 'Z'; }
  function ell(cx, cy, rx, ry, fill, sw, fop) {
    return '<ellipse cx="' + f(cx) + '" cy="' + f(cy) + '" rx="' + f(rx) + '" ry="' + f(ry) + '" fill="' + (fill || 'none') + '"' + (fop != null ? ' fill-opacity="' + f(fop) + '"' : '') + stroke(sw) + '/>';
  }
  function shadow(d) { return '<path d="' + d + '" fill="' + PAL.ink + '" fill-opacity="0.18"/>'; }
  /** 建筑投影：占地 x0..x1、前沿 yb、后沿 yr；向右下偏 dx，下伸 ≤ 5 px */
  function groundShadow(x0, x1, yb, yr, dx) {
    dx = dx == null ? 7 : dx;
    return shadow('M' + f(x1) + ' ' + f(yr) + 'L' + f(x1 + dx) + ' ' + f(yr + 4) + 'L' + f(x1 + dx) + ' ' + f(yb + 4) + 'L' + f(x0 + 5) + ' ' + f(yb + 4) + 'L' + f(x0) + ' ' + f(yb) + 'Z');
  }
  function clipped(ctx, d, inner, rule) {
    if (!inner) return '';
    var id = ctx.uid();
    return '<clipPath id="' + id + '"><path d="' + d + '"' + (rule ? ' clip-rule="' + rule + '"' : '') + '/></clipPath><g clip-path="url(#' + id + ')">' + inner + '</g>';
  }
  function mulberry32(a) {
    return function () {
      a |= 0; a = a + 0x6D2B79F5 | 0;
      var t = Math.imul(a ^ a >>> 15, 1 | a);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  function hash(s) { var h = 2166136261; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
  function Ctx(id) {
    this.id = id; this.n = 0; this.minY = 0; this.r = mulberry32(hash(id));
  }
  Ctx.prototype.uid = function () { return this.id + '-c' + (this.n++); };
  Ctx.prototype.rnd = function (a, b) { return a + (b - a) * this.r(); };
  Ctx.prototype.pick = function (arr) { return arr[Math.floor(this.r() * arr.length)]; };
  Ctx.prototype.top = function (y) { if (y < this.minY) this.minY = y; };

  function pad2(n) { return (n < 10 ? '0' : '') + n; }
  function bin(m) { return ('000' + m.toString(2)).slice(-4); }
  var API = { PAL: PAL, f: f, stroke: stroke, path: path, line: line, rectD: rectD, rect: rect, poly: poly, ell: ell, shadow: shadow,
    groundShadow: groundShadow, clipped: clipped, mulberry32: mulberry32, hash: hash, Ctx: Ctx, pad2: pad2, bin: bin, CELL: 48, MAX_UP: 144 };
  root.TownArtAB_core = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
