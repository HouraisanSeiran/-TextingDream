/*
 * 织梦 · 城镇兽人族素材 —— 公共绘图函数（美术样板，尚未接入游戏）
 * 西式木刻线描 + 羊皮纸淡彩的兽人变种：不透明平涂 + 墨线 #4a3826 勾边 + 少量短排线；不用渐变、高光、模糊。
 * 浏览器挂 window.TownArtWO_core；Node 用 module.exports。
 * 局部坐标：x 从 0 到 w*48；y = 0 是占地前沿，向上为负，占地后沿 y = -d*48。
 */
(function (root) {
  'use strict';
  var INK = '#4a3826';
  var PAL = {
    ink: INK, paper: '#efdfb2', plaster: '#e9dcc0', wash: '#e3c47a', wood: '#c9a46a',
    stone: '#cfc0a2', stone2: '#bfb093', stone3: '#b1a287', timber: '#8a6a44', dark: '#6b4f32',
    tile: '#b5654a', red: '#9a3b2a', thatch: '#d2b46c', thatch2: '#b8954e', grass: '#c9c79a',
    shadow: '#3a2c1e', hole: '#3b2d1f', soil: '#a98a5e', soil2: '#93764d',
    // 兽人追加色
    hide: '#9b7550', hide2: '#6e4e33', hide3: '#b48f66', bone: '#e6dcc2', bone2: '#cbbf9f',
    rust: '#8f3a26', moss: '#6f7a4a', moss2: '#8b9161', iron: '#6a6660', iron2: '#8d8a82',
    fire: '#d9893a', fire2: '#efc463'
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

  /** 绘制上下文：symbol id 前缀（内部 clipPath id 用）、种子随机、记录最高点 */
  function Ctx(id, seed) { this.id = id; this.n = 0; this.r = rng(seed == null ? hashStr(id) : seed); this.minY = 0; this.maxY = -999; }
  Ctx.prototype.uid = function () { return this.id + '-k' + (++this.n); };
  Ctx.prototype.rnd = function (a, b) { return a + (b - a) * this.r(); };
  Ctx.prototype.int = function (a, b) { return Math.min(b, Math.floor(a + (b - a + 1) * this.r())); };
  Ctx.prototype.pick = function (arr) { return arr[Math.floor(this.r() * arr.length) % arr.length]; };
  Ctx.prototype.chance = function (p) { return this.r() < p; };
  Ctx.prototype.j = function (a) { return (this.r() * 2 - 1) * (a == null ? 1 : a); };
  Ctx.prototype.top = function (y) { if (y < this.minY) this.minY = y; };

  function stroke(sw, op, color) {
    return ' stroke="' + (color || INK) + '" stroke-width="' + f(sw) + '" stroke-linejoin="round" stroke-linecap="round"' +
      (op != null && op < 1 ? ' stroke-opacity="' + f(op) + '"' : '');
  }
  function fillA(fill, fop) {
    return ' fill="' + (fill || 'none') + '"' + (fop != null && fop < 1 ? ' fill-opacity="' + f(fop) + '"' : '');
  }
  function rect(x, y, w, h, fill, sw, fop, rx) {
    return '<rect x="' + f(x) + '" y="' + f(y) + '" width="' + f(w) + '" height="' + f(h) + '"' + (rx ? ' rx="' + f(rx) + '"' : '') +
      fillA(fill, fop) + (sw ? stroke(sw) : '') + '/>';
  }
  function path(d, fill, sw, fop) { return '<path d="' + d + '"' + fillA(fill, fop) + (sw ? stroke(sw) : '') + '/>'; }
  function line(d, sw, op, color) { return d ? '<path d="' + d + '" fill="none"' + stroke(sw, op, color) + '/>' : ''; }
  function ell(cx, cy, rx, ry, fill, sw, fop) {
    return '<ellipse cx="' + f(cx) + '" cy="' + f(cy) + '" rx="' + f(rx) + '" ry="' + f(ry) + '"' + fillA(fill, fop) + (sw ? stroke(sw) : '') + '/>';
  }
  function poly(pts) { return 'M' + pts.map(function (p) { return f(p[0]) + ' ' + f(p[1]); }).join('L') + 'Z'; }
  function rectD(x, y, w, h) { return poly([[x, y], [x + w, y], [x + w, y + h], [x, y + h]]); }
  function ellD(cx, cy, rx, ry) {
    return 'M' + f(cx - rx) + ' ' + f(cy) + 'A' + f(rx) + ' ' + f(ry) + ' 0 1 0 ' + f(cx + rx) + ' ' + f(cy) +
      'A' + f(rx) + ' ' + f(ry) + ' 0 1 0 ' + f(cx - rx) + ' ' + f(cy) + 'Z';
  }
  /** 带手绘抖动的多边形（略歪斜） */
  function wob(ctx, pts, a) { return poly(pts.map(function (p) { return [p[0] + ctx.j(a), p[1] + ctx.j(a)]; })); }
  function clipped(ctx, d, inner) {
    if (!inner) return '';
    var id = ctx.uid();
    return '<defs><clipPath id="' + id + '"><path d="' + d + '"/></clipPath></defs><g clip-path="url(#' + id + ')">' + inner + '</g>';
  }
  /** 平涂面 + 裁切在面内的纹理 + 墨线外轮廓 */
  function face(ctx, d, fill, tex, sw) { return path(d, fill, 0) + clipped(ctx, d, tex) + path(d, 'none', sw == null ? 1.6 : sw); }
  // 投影统一带 class="sh"：自检脚本据此把投影排除在「不画出前沿以下」检查之外
  function shadowD(d) { return '<path class="sh" d="' + d + '" fill="' + PAL.shadow + '" fill-opacity="0.18"/>'; }
  /** 地面投影：占地前沿 yb 处向右下偏的平涂（最多下伸 5 px） */
  function groundShadow(x0, x1, yb, yt) {
    return shadowD(poly([[x0 + 4, yb], [x1, yb], [x1 + 6, yb - 3], [x1 + 6, yt + 6], [x1, yt]]) + 'M' + f(x0 + 4) + ' ' + f(yb) + 'L' + f(x1) + ' ' + f(yb) + 'L' + f(x1 - 2) + ' ' + f(Math.min(yb + 4, 4)) + 'L' + f(x0 + 6) + ' ' + f(Math.min(yb + 4, 4)) + 'Z');
  }
  function ellShadow(cx, cy, rx, ry) { return shadowD(ellD(cx + rx * 0.16, cy + Math.min(ry * 0.18, 3), rx * 1.02, ry)); }
  function circ(cx, cy, r, fill, sw) { return '<circle cx="' + f(cx) + '" cy="' + f(cy) + '" r="' + f(r) + '" fill="' + (fill || 'none') + '"' + (sw ? stroke(sw) : '') + '/>'; }
  /** 椭球点：方位 a（0 = 正前方，弧度）、仰角 e；底面中心 (cx, yc)，半径 rx / ry（底面透视）、高 h */
  function domePt(cx, yc, rx, ry, h, a, e) { return [cx + rx * Math.cos(e) * Math.sin(a), yc + ry * Math.cos(e) * Math.cos(a) - h * Math.sin(e)]; }
  function pl(pts) { return 'M' + pts.map(function (p) { return f(p[0]) + ' ' + f(p[1]); }).join('L'); }

  var API = {
    INK: INK, PAL: PAL, f: f, rng: rng, hashStr: hashStr, Ctx: Ctx, stroke: stroke, rect: rect, path: path, line: line, ell: ell,
    poly: poly, rectD: rectD, ellD: ellD, wob: wob, clipped: clipped, face: face, shadowD: shadowD, groundShadow: groundShadow, ellShadow: ellShadow,
    circ: circ, domePt: domePt, pl: pl
  };
  root.TownArtWO_core = API;
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
