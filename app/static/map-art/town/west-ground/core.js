/*
 * 织梦 · 城镇西式水面与地面素材 —— 公共画笔（3/4 斜俯视；美术样板，尚未接入游戏）
 * 木刻线描 + 羊皮纸淡彩：不透明平涂 + 墨线 #4a3826 勾边 + 少量短排线；不用渐变、高光、模糊。
 * 浏览器挂 window.TownArtWG_core；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var INK = '#4a3826';
  var P = {
    ink: INK, paper: '#efdfb2', plaster: '#e9dcc0', wash: '#e3c47a', wood: '#c9a46a',
    stone: '#cfc0a2', stone2: '#bfb093', stone3: '#b1a287', timber: '#8a6a44', dark: '#6b4f32',
    tile: '#b5654a', red: '#9a3b2a', slate: '#7d8790', slate2: '#5f6870', thatch: '#d2b46c', thatch2: '#b8954e',
    grass: '#c9c79a', shadow: '#3a2c1e', soil: '#a98a5e', soil2: '#93764d',
    leaf: '#8e8f58', leaf2: '#a6a46a', leaf3: '#76784a',
    // 水色：与 special-infra 的西式码头、石拱桥一致（infra-core.js WEST.water / water2）
    water: '#a9b8ad', water2: '#8fa49a',
    mud: '#c2ab7f', yard: '#d8c49a', yard2: '#c6ae80', iron: '#5c5a55', fire: '#d9853f', glow: '#f2d98a'
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
  function hashStr(s) {
    var h = 2166136261;
    for (var i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
    return h >>> 0;
  }

  /** 绘制上下文：symbol id 前缀（内部 clipPath id 用）+ 种子随机 */
  function Ctx(id, seed) { this.id = id; this.n = 0; this.r = rng(seed == null ? hashStr(id) : seed); }
  Ctx.prototype.uid = function () { return this.id + '-k' + (++this.n); };
  Ctx.prototype.rnd = function (a, b) { return a + (b - a) * this.r(); };
  Ctx.prototype.int = function (a, b) { return Math.min(b, Math.floor(a + (b - a + 1) * this.r())); };
  Ctx.prototype.pick = function (arr) { return arr[Math.floor(this.r() * arr.length) % arr.length]; };
  Ctx.prototype.chance = function (p) { return this.r() < p; };

  function st(sw, op, color, cap) {
    return ' stroke="' + (color || INK) + '" stroke-width="' + f(sw) + '" stroke-linejoin="round" stroke-linecap="' + (cap || 'round') + '"' +
      (op != null && op < 1 ? ' stroke-opacity="' + f(op) + '"' : '');
  }
  function fo(fop) { return fop != null && fop < 1 ? ' fill-opacity="' + f(fop) + '"' : ''; }
  function rect(x, y, w, h, fill, sw, fop, rx) {
    return '<rect x="' + f(x) + '" y="' + f(y) + '" width="' + f(w) + '" height="' + f(h) + '"' + (rx ? ' rx="' + f(rx) + '"' : '') +
      ' fill="' + (fill || 'none') + '"' + fo(fop) + (sw ? st(sw) : '') + '/>';
  }
  function path(d, fill, sw, fop, extra) {
    if (!d) return '';
    return '<path d="' + d + '" fill="' + (fill || 'none') + '"' + fo(fop) + (sw ? st(sw) : '') + (extra || '') + '/>';
  }
  function line(d, sw, op, color, extra) {
    if (!d) return '';
    return '<path d="' + d + '" fill="none"' + st(sw, op, color) + (extra || '') + '/>';
  }
  function ell(cx, cy, rx, ry, fill, sw, fop) {
    return '<ellipse cx="' + f(cx) + '" cy="' + f(cy) + '" rx="' + f(rx) + '" ry="' + f(ry) + '" fill="' + (fill || 'none') + '"' +
      fo(fop) + (sw ? st(sw) : '') + '/>';
  }
  function poly(pts, open) {
    return 'M' + pts.map(function (p) { return f(p[0]) + ' ' + f(p[1]); }).join('L') + (open ? '' : 'Z');
  }
  function seg(x1, y1, x2, y2) { return 'M' + f(x1) + ' ' + f(y1) + 'L' + f(x2) + ' ' + f(y2); }
  /** 把 inner 裁切在路径 d 里；tf 可给 clipPath 里的路径加 transform */
  function clip(ctx, d, rule, inner, tf) {
    if (!inner || !d) return '';
    var id = ctx.uid();
    return '<defs><clipPath id="' + id + '"><path d="' + d + '" clip-rule="' + (rule || 'nonzero') + '"' +
      (tf ? ' transform="' + tf + '"' : '') + '/></clipPath></defs><g clip-path="url(#' + id + ')">' + inner + '</g>';
  }
  /** 平涂投影（西式 #3a2c1e / 0.18） */
  function shade(d) { return path(d, P.shadow, 0, 0.18); }
  function shadowEll(cx, cy, rx, ry) { return ell(cx, cy, rx, ry, P.shadow, 0, 0.18); }

  /** 不规则圆团（树冠、灌木、草堆）：n 个外凸弧围成；返回 d */
  function blob(ctx, cx, cy, rx, ry, n, jit) {
    var pts = [], i, a0 = ctx.rnd(0, Math.PI * 2);
    for (i = 0; i < n; i++) {
      var a = a0 + i * Math.PI * 2 / n, k = 1 + ctx.rnd(-jit, jit);
      pts.push([cx + Math.cos(a) * rx * k, cy + Math.sin(a) * ry * k]);
    }
    var d = 'M' + f(pts[0][0]) + ' ' + f(pts[0][1]);
    for (i = 0; i < n; i++) {
      var p = pts[i], q = pts[(i + 1) % n], mx = (p[0] + q[0]) / 2, my = (p[1] + q[1]) / 2;
      var ox = mx - cx, oy = my - cy, L = Math.hypot(ox, oy) || 1, bump = Math.hypot(q[0] - p[0], q[1] - p[1]) * 0.42;
      d += 'Q' + f(mx + ox / L * bump) + ' ' + f(my + oy / L * bump) + ' ' + f(q[0]) + ' ' + f(q[1]);
    }
    return d + 'Z';
  }
  /** 一簇草：从 (x, y) 向上 n 根短笔触 */
  function tuft(ctx, x, y, h, n, color, sw) {
    var d = '';
    for (var i = 0; i < n; i++) {
      var dx = (i - (n - 1) / 2) * 1.6, lean = dx * 0.7 + ctx.rnd(-0.8, 0.8), hh = h * ctx.rnd(0.6, 1);
      d += 'M' + f(x + dx * 0.5) + ' ' + f(y) + 'Q' + f(x + dx * 0.6) + ' ' + f(y - hh * 0.6) + ' ' + f(x + dx * 0.5 + lean) + ' ' + f(y - hh);
    }
    return line(d, sw || 0.9, 1, color || P.leaf3);
  }

  var api = {
    INK: INK, P: P, f: f, rng: rng, hashStr: hashStr, Ctx: Ctx, st: st, rect: rect, path: path, line: line, ell: ell,
    poly: poly, seg: seg, clip: clip, shade: shade, shadowEll: shadowEll, blob: blob, tuft: tuft
  };
  root.TownArtWG_core = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : this);
