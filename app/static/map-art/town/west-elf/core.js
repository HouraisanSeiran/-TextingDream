/*
 * 织梦 · 城镇西式精灵族素材 —— 公共画笔（3/4 斜俯视，木刻线描 + 羊皮纸淡彩的精灵变种；美术样板，尚未接入游戏）
 * 不透明平涂 + 墨线 #4a3826 勾边 + 少量短排线；不用渐变、高光、模糊。
 * 局部坐标：x 从 0 到 w*48；y = 0 是占地前沿，向上为负，占地后沿 y = -d*48。
 * 浏览器挂 window.TownArtWE_core；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var INK = '#4a3826';
  var P = {
    ink: INK, paper: '#efdfb2', plaster: '#e9dcc0', wash: '#e3c47a', wood: '#c9a46a',
    stone: '#cfc0a2', stone2: '#bfb093', stone3: '#b1a287', timber: '#8a6a44', dark: '#6b4f32',
    red: '#9a3b2a', tile: '#b5654a', grass: '#c9c79a', shadow: '#3a2c1e', glass: '#4f3f2c',
    // 精灵补色（任务指定）
    silver: '#e8e4d4', moss: '#a7b48a', leaf: '#7f9a5c', moon: '#cfd8d6', bark: '#6b5a44',
    // 由补色派生的阴面色（README 说明）
    silver2: '#d8d3c0', silver3: '#c2bca5', leaf2: '#677f4a', bark2: '#86735a', moon2: '#aebbb8', water: '#a9b8b2'
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
  function Ctx(id, seed) { this.id = id; this.n = 0; this.r = rng(seed == null ? hashStr(id) : seed); this.minY = 0; }
  Ctx.prototype.uid = function () { return this.id + '-k' + (++this.n); };
  Ctx.prototype.rnd = function (a, b) { return a + (b - a) * this.r(); };
  Ctx.prototype.int = function (a, b) { return Math.min(b, Math.floor(a + (b - a + 1) * this.r())); };
  Ctx.prototype.pick = function (arr) { return arr[Math.floor(this.r() * arr.length) % arr.length]; };
  Ctx.prototype.chance = function (p) { return this.r() < p; };
  Ctx.prototype.top = function (y) { if (y < this.minY) this.minY = y; };

  function stroke(sw, op, color) {
    return ' stroke="' + (color || INK) + '" stroke-width="' + f(sw) + '" stroke-linejoin="round" stroke-linecap="round"' +
      (op != null && op < 1 ? ' stroke-opacity="' + f(op) + '"' : '');
  }
  function fillA(fill, fop) { return ' fill="' + (fill || 'none') + '"' + (fop != null && fop < 1 ? ' fill-opacity="' + f(fop) + '"' : ''); }
  function rect(x, y, w, h, fill, sw, fop, rx) {
    return '<rect x="' + f(x) + '" y="' + f(y) + '" width="' + f(w) + '" height="' + f(h) + '"' + (rx ? ' rx="' + f(rx) + '"' : '') +
      fillA(fill, fop) + (sw ? stroke(sw) : '') + '/>';
  }
  function path(d, fill, sw, fop) { return d ? '<path d="' + d + '"' + fillA(fill, fop) + (sw ? stroke(sw) : '') + '/>' : ''; }
  function line(d, sw, op, color) { return d ? '<path d="' + d + '" fill="none"' + stroke(sw, op, color) + '/>' : ''; }
  function circle(cx, cy, r, fill, sw, fop) {
    return '<circle cx="' + f(cx) + '" cy="' + f(cy) + '" r="' + f(r) + '"' + fillA(fill, fop) + (sw ? stroke(sw) : '') + '/>';
  }
  function ellipse(cx, cy, rx, ry, fill, sw, fop) {
    return '<ellipse cx="' + f(cx) + '" cy="' + f(cy) + '" rx="' + f(rx) + '" ry="' + f(ry) + '"' + fillA(fill, fop) + (sw ? stroke(sw) : '') + '/>';
  }
  function poly(pts) { return 'M' + pts.map(function (p) { return f(p[0]) + ' ' + f(p[1]); }).join('L') + 'Z'; }
  function rectD(x, y, w, h) { return poly([[x, y], [x + w, y], [x + w, y + h], [x, y + h]]); }
  function ellD(cx, cy, rx, ry) {
    return 'M' + f(cx - rx) + ' ' + f(cy) + 'A' + f(rx) + ' ' + f(ry) + ' 0 1 0 ' + f(cx + rx) + ' ' + f(cy) +
      'A' + f(rx) + ' ' + f(ry) + ' 0 1 0 ' + f(cx - rx) + ' ' + f(cy) + 'Z';
  }
  function clipped(ctx, d, inner) {
    if (!inner) return '';
    var id = ctx.uid();
    return '<defs><clipPath id="' + id + '"><path d="' + d + '"/></clipPath></defs><g clip-path="url(#' + id + ')">' + inner + '</g>';
  }
  /** 平涂面 + 裁切在面内的纹理 + 墨线外轮廓 */
  function face(ctx, d, fill, tex, sw) { return path(d, fill, 0) + clipped(ctx, d, tex) + path(d, 'none', sw == null ? 1.6 : sw); }
  /** 投影：半透明暗色平涂（西式 #3a2c1e 0.18） */
  function shadow(d, op) { return path(d, P.shadow, 0, op == null ? 0.18 : op); }
  /** 建筑脚下的投影：落在右下方，最多下伸 4 px */
  function groundShadow(x0, x1, yb, back) {
    var yl = Math.min(yb + 4, 4);
    return shadow(poly([[x0 + 5, yb], [x1, yb], [x1, back], [x1 + 6, back + 6], [x1 + 6, yl], [x0 + 8, yl]]));
  }
  function ellShadow(cx, cy, rx, ry) {
    var b = Math.min(cy + ry, 4.5) - cy;
    return shadow(ellD(cx + rx * 0.18, cy, rx, Math.max(1, Math.min(ry, b))));
  }
  /** 背光面短排线（木刻阴影） */
  function hatch(x, y, w, h, gap, op) {
    var d = '', g = gap || 3.2, k = Math.min(h, 7);
    for (var t = -h; t < w; t += g) d += 'M' + f(x + t) + ' ' + f(y + h) + 'l' + f(k) + ' ' + f(-k);
    return line(d, 0.6, op == null ? 0.4 : op);
  }
  /** 过若干点的平滑曲线（Catmull-Rom 转三次贝塞尔），open */
  function smooth(pts) {
    if (pts.length < 2) return '';
    var d = 'M' + f(pts[0][0]) + ' ' + f(pts[0][1]);
    for (var i = 0; i < pts.length - 1; i++) {
      var p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
      d += 'C' + f(p1[0] + (p2[0] - p0[0]) / 6) + ' ' + f(p1[1] + (p2[1] - p0[1]) / 6) + ' ' +
        f(p2[0] - (p3[0] - p1[0]) / 6) + ' ' + f(p2[1] - (p3[1] - p1[1]) / 6) + ' ' + f(p2[0]) + ' ' + f(p2[1]);
    }
    return d;
  }

  var API = {
    INK: INK, P: P, PAL: P, f: f, rng: rng, hashStr: hashStr, Ctx: Ctx, stroke: stroke, rect: rect, path: path, line: line,
    circle: circle, ellipse: ellipse, poly: poly, rectD: rectD, ellD: ellD, clipped: clipped, face: face, shadow: shadow,
    groundShadow: groundShadow, ellShadow: ellShadow, hatch: hatch, smooth: smooth
  };
  root.TownArtWE_core = API;
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
