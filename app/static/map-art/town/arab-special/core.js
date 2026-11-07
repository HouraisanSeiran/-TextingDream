/*
 * 织梦 · 阿拉伯风格特殊建筑：基础画笔（3/4 斜俯视，细墨线 + 不透明平涂；美术样板，尚未接入游戏）
 *
 * 投影约定（docs/town-art-spec.md 第 1、15 节）：地面格 48 px 正方形，地面进深不压缩；
 * 立面向上直画；平顶顶面 = 地面范围整体上移墙高 h。光从左上来，右侧/阴面用暗一档色，投影在右下。
 * 浏览器挂 window.TownArtAS_core；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var CELL = 48;
  var C = {
    ink: '#4a3020', lime: '#f2ead8', lime2: '#e8dcc2',
    adobe: '#d9b98a', adobe2: '#c79d66', adobe3: '#a97f4c', sand: '#e6cf9e',
    turq: '#3a9fa8', turq2: '#7cc6c2', cobalt: '#24467a', cobalt2: '#3d64a0',
    gold: '#c9a046', ochre: '#a8502e', ochre2: '#c86b3c', palm: '#5f7a3a', palm2: '#86a052',
    ground: '#e3cf9f', water: '#a9b8ad', shadow: '#4a3020',
    // 色板外补色（README 说明）：门窗洞深色、深木（木格窗/木轮）
    hole: '#5c3d27', wood: '#7a5233', iron: '#6b6560'
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
  function hash(s) { var h = 2166136261; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
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
  /** 细线（不填充） */
  function ln(d, sw, op, color) {
    if (!d) return '';
    return '<path d="' + d + '" fill="none" stroke="' + (color || C.ink) + '" stroke-width="' + f(sw || 0.8) +
      '" stroke-linecap="round" stroke-linejoin="round"' + (op != null && op < 1 ? ' stroke-opacity="' + f(op) + '"' : '') + '/>';
  }
  /** 无描边平涂 */
  function flat(pts, fill, op) {
    return '<path d="' + pd(pts) + '" fill="' + fill + '"' + (op != null && op < 1 ? ' fill-opacity="' + f(op) + '"' : '') + '/>';
  }
  function flatD(d, fill, op) {
    return '<path d="' + d + '" fill="' + fill + '"' + (op != null && op < 1 ? ' fill-opacity="' + f(op) + '"' : '') + '/>';
  }
  /** 投影：#4a3020 不透明度 0.18 */
  function shade(pts, op) { return flat(pts, C.shadow, op == null ? 0.18 : op); }
  /** 方盒投影：地面 x0..x1，后沿 yb，前沿 yf；向右伸 s（不出 W），向下 ≤4 px（不出 H） */
  function boxShadow(x0, x1, yb, yf, s, W, H) {
    var dn = Math.max(0, Math.min(4, H - yf)), sx = Math.max(0, Math.min(s, W - x1 - 0.5));
    return shade([[x0 + 4, yf], [x0 + 4 + dn, yf + dn], [x1 + sx, yf + dn], [x1 + sx, yb + sx * 0.7], [x1, yb]]);
  }

  var M = {
    CELL: CELL, C: C, f: f, rng: rng, hash: hash, pd: pd, seg: seg, at: at, poly: poly, path: path,
    rect: rect, circle: circle, ellipse: ellipse, ln: ln, flat: flat, flatD: flatD, shade: shade, boxShadow: boxShadow
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = M;
  else root.TownArtAS_core = M;
})(this);
