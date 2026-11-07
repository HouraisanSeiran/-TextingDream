/*
 * 织梦 · 三族不规则城墙与防御工事（race-fort）公共画笔（美术样板，尚未接入游戏）
 * 色板逐项取自 west-elf / west-dwarf / west-orc 的 core.js，保证与已有城墙一致。
 * 浏览器挂 window.TownArtRF_core；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var INK = '#4a3826';
  var P = {
    ink: INK, paper: '#efdfb2', wash: '#e3c47a', wood: '#c9a46a', stone: '#cfc0a2', stone2: '#bfb093', stone3: '#b1a287',
    timber: '#8a6a44', dark: '#6b4f32', red: '#9a3b2a', shadow: '#3a2c1e', hole: '#3b2d1f', grass: '#c9c79a',
    silver: '#e8e4d4', silver2: '#d8d3c0', silver3: '#c2bca5', moss: '#a7b48a', leaf: '#7f9a5c', leaf2: '#677f4a',
    bark: '#6b5a44', bark2: '#86735a', moon: '#cfd8d6', moon2: '#aebbb8',
    granite: '#9a958c', granite2: '#aba69c', granite3: '#b6b1a6', deep: '#6f6a62', deep2: '#5c5852', walk: '#a8a397',
    copper: '#b8763a', copper2: '#9c6230', verd: '#5f8f7e', verd2: '#7aa494', fire: '#e07a2f', ember: '#f0b04e', iron: '#4f4b46',
    soil: '#a98a5e', soil2: '#93764d', hide: '#9b7550', hide2: '#6e4e33', hide3: '#b48f66', bone: '#e6dcc2', bone2: '#cbbf9f',
    rust: '#8f3a26', omoss: '#6f7a4a', oiron: '#6a6660', rope: '#c8a86a'
  };
  function f(n) { return String(Math.round(n * 100) / 100); }
  function rng(seed) { return function () { seed |= 0; seed = seed + 0x6D2B79F5 | 0; var t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  function hashStr(s) { var h = 2166136261; for (var i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619); return h >>> 0; }
  function Ctx(id) { this.id = id; this.n = 0; this.r = rng(hashStr(id)); this.minY = 0; }
  Ctx.prototype.uid = function () { return this.id + '-k' + (++this.n); };
  Ctx.prototype.rnd = function (a, b) { return a + (b - a) * this.r(); };
  Ctx.prototype.top = function (y) { if (y < this.minY) this.minY = y; };
  function stroke(sw, op, c) { return ' stroke="' + (c || INK) + '" stroke-width="' + f(sw) + '" stroke-linejoin="round" stroke-linecap="round"' + (op != null && op < 1 ? ' stroke-opacity="' + f(op) + '"' : ''); }
  function fillA(c, op) { return ' fill="' + (c || 'none') + '"' + (op != null && op < 1 ? ' fill-opacity="' + f(op) + '"' : ''); }
  function path(d, c, sw, op) { return d ? '<path d="' + d + '"' + fillA(c, op) + (sw ? stroke(sw) : '') + '/>' : ''; }
  function line(d, sw, op, c) { return d ? '<path d="' + d + '" fill="none"' + stroke(sw, op, c) + '/>' : ''; }
  function rect(x, y, w, h, c, sw, op) { return path('M' + f(x) + ' ' + f(y) + 'h' + f(w) + 'v' + f(h) + 'h' + f(-w) + 'Z', c, sw, op); }
  function ell(cx, cy, rx, ry, c, sw, op) { return '<ellipse cx="' + f(cx) + '" cy="' + f(cy) + '" rx="' + f(rx) + '" ry="' + f(ry) + '"' + fillA(c, op) + (sw ? stroke(sw) : '') + '/>'; }
  function poly(pts) { return pts.length ? 'M' + pts.map(function (p) { return f(p[0]) + ' ' + f(p[1]); }).join('L') + 'Z' : ''; }
  function pl(pts) { return 'M' + pts.map(function (p) { return f(p[0]) + ' ' + f(p[1]); }).join('L'); }
  function shadow(d, op) { return path(d, P.shadow, 0, op == null ? 0.18 : op); }
  var API = { INK: INK, P: P, f: f, rng: rng, hashStr: hashStr, Ctx: Ctx, stroke: stroke, path: path, line: line, rect: rect, ell: ell, poly: poly, pl: pl, shadow: shadow };
  root.TownArtRF_core = API;
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
