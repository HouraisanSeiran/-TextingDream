/*
 * 织梦 · 西式防御工事（west-fort）—— 公共画笔（尚未接入游戏）
 * 局部坐标：x 0..w*48；y = 0 是占地前沿，向上为负，占地后沿 y = -d*48。
 * 斜俯视投影：地面点 (x, y) 在高度 h 处画到 (x, y - h)。
 * 浏览器挂 window.TownArtWF.core；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var PAL = {
    ink: '#4a3826', paper: '#efdfb2', plaster: '#e9dcc0', wash: '#e3c47a', wood: '#c9a46a',
    stone: '#cfc0a2', stone2: '#bfb093', stone3: '#b1a287', walk: '#c3b494', timber: '#8a6a44', dark: '#6b4f32',
    tile: '#b5654a', red: '#9a3b2a', slate: '#7d8790', slate2: '#5f6870', grass: '#c9c79a', shadow: '#3a2c1e',
    hole: '#3b2d1f', water: '#a9b7a6', water2: '#93a394', water3: '#7c8d80', soil: '#a98a5e'
  };
  function f(n) { return String(Math.round(n * 100) / 100); }
  function P(x, y) { return f(x) + ' ' + f(y); }
  function rng(seed) { return function () { seed |= 0; seed = seed + 0x6D2B79F5 | 0; var t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  function seedOf(s) { var h = 2166136261 >>> 0; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
  function stroke(sw, op, col) { return sw ? ' stroke="' + (col || PAL.ink) + '" stroke-width="' + f(sw) + '" stroke-linejoin="round" stroke-linecap="round"' + (op != null && op < 1 ? ' stroke-opacity="' + f(op) + '"' : '') : ''; }
  function path(d, fill, sw, op, extra) { return d ? '<path d="' + d + '" fill="' + (fill || 'none') + '"' + stroke(sw, op) + (extra || '') + '/>' : ''; }
  function pts(a) { return 'M' + a.map(function (p) { return P(p[0], p[1]); }).join('L') + 'Z'; }
  function poly(a, fill, sw, op) { return path(pts(a), fill, sw, op); }
  function seg(a, b) { return 'M' + P(a[0], a[1]) + 'L' + P(b[0], b[1]); }
  function lines(d, sw, op) { return d ? path(d, 'none', sw || 0.8, op == null ? 0.5 : op) : ''; }
  function shadow(d) { return d ? '<path d="' + d + '" fill="' + PAL.shadow + '" fill-opacity="0.18"/>' : ''; }
  /** 每个 symbol 一个上下文：种子随机 + 内部 id + 记录最高点 */
  function Ctx(id) { this.id = id; this.r = rng(seedOf(id)); this.n = 0; this.minY = 0; }
  Ctx.prototype.rnd = function (a, b) { return a + (b - a) * this.r(); };
  Ctx.prototype.uid = function () { return this.id + '-c' + (this.n++); };
  Ctx.prototype.top = function (y) { if (y < this.minY) this.minY = y; };
  var API = { PAL: PAL, CELL: 48, f: f, P: P, rng: rng, seedOf: seedOf, stroke: stroke, path: path, pts: pts, poly: poly, seg: seg, lines: lines, shadow: shadow, Ctx: Ctx };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else { root.TownArtWF = root.TownArtWF || {}; root.TownArtWF.core = API; }
})(this);
