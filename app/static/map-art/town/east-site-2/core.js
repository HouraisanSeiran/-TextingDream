/*
 * 织梦 · 东方资源点（east-site-2，复制自 east-site）共用画笔与色板（美术素材，尚未接入游戏）
 * 国潮不透明平涂 + 金线勾边；色板同规范第 2 节东方表。水色 S.water = #6cc1b3，与 east-ground 驳岸水面一致。
 * 浏览器挂 window.TownArtES2_core，Node 用 module.exports。原创程序化路径，不读外部图片。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory();
  else root.TownArtES2_core = factory();
})(this, function () {
  'use strict';
  var CELL = 48;
  var S = {
    gold: '#c98f3c', gold2: '#f3c46a', cream: '#f1dcae', cream2: '#fbf0d4', ochre: '#eeb24f',
    orange: '#e47c36', vermil: '#cd5030', brown: '#8c3d22', brown2: '#a8593a', teal: '#2e938d', teal2: '#6cc1b3',
    navy: '#1f3c5b', navy2: '#30697f', gray: '#5d6670', gray2: '#7b8590', gray3: '#a3abb2',
    earth: '#d9b77a', earth2: '#c79c5c', earth3: '#b08048', grass: '#d9c58f', leaf: '#5f9a5a', leaf2: '#7fb36a', leaf3: '#3f7650',
    water: '#6cc1b3', water2: '#9fd8cb', waterDeep: '#3f9c93', wood: '#b9763f', wood2: '#d69a5c', wood3: '#8c4f2a',
    thatch: '#d8b25e', thatch2: '#b98d3e', coal: '#2e3036', coal2: '#4a4d55', salt: '#f7f4ea', shadow: '#1f3c5b',
    ink: '#c98f3c', ink2: '#f3c46a', lw: 1.6, lwd: 1
  };
  function f(n) { return Math.round(n * 10) / 10; }
  function rng(seed) { // mulberry32
    return function () {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      var t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  function hash(s) { var h = 2166136261; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
  function at(fill, stroke, sw, extra) {
    return ' fill="' + (fill || 'none') + '"' + (stroke ? ' stroke="' + stroke + '" stroke-width="' + (sw == null ? S.lw : sw) + '" stroke-linejoin="round" stroke-linecap="round"' : '') + (extra || '');
  }
  function fop(o) { return ' fill-opacity="' + o + '"'; }
  function op(o) { return ' opacity="' + o + '"'; }
  function pts(a) { return a.map(function (p) { return f(p[0]) + ',' + f(p[1]); }).join(' '); }
  function poly(a, fill, stroke, sw, extra) { return '<polygon points="' + pts(a) + '"' + at(fill, stroke, sw, extra) + '/>'; }
  function pl(a, stroke, sw, extra) { return '<polyline points="' + pts(a) + '"' + at(null, stroke, sw, extra) + '/>'; }
  function path(d, fill, stroke, sw, extra) { return '<path d="' + d + '"' + at(fill, stroke, sw, extra) + '/>'; }
  function rect(x, y, w, h, fill, stroke, sw, extra) {
    return '<rect x="' + f(x) + '" y="' + f(y) + '" width="' + f(w) + '" height="' + f(h) + '"' + at(fill, stroke, sw, extra) + '/>';
  }
  function ell(cx, cy, rx, ry, fill, stroke, sw, extra) {
    return '<ellipse cx="' + f(cx) + '" cy="' + f(cy) + '" rx="' + f(rx) + '" ry="' + f(ry) + '"' + at(fill, stroke, sw, extra) + '/>';
  }
  function circ(cx, cy, r, fill, stroke, sw, extra) { return ell(cx, cy, r, r, fill, stroke, sw, extra); }
  function ln(x1, y1, x2, y2, stroke, sw, extra) {
    return '<line x1="' + f(x1) + '" y1="' + f(y1) + '" x2="' + f(x2) + '" y2="' + f(y2) + '"' + at(null, stroke || S.ink, sw == null ? S.lwd : sw, extra) + '/>';
  }
  /** 投影：东方 #1f3c5b 不透明度 0.2，平涂。 */
  function shadow(a) { return poly(a, S.shadow, null, 0, fop(0.2)); }
  function shadowEll(cx, cy, rx, ry) { return ell(cx, cy, rx, ry, S.shadow, null, 0, fop(0.2)); }
  function clip(id, shape, body) { return '<clipPath id="' + id + '">' + shape + '</clipPath><g clip-path="url(#' + id + ')">' + body + '</g>'; }
  function g(tf, body, extra) { return '<g transform="' + tf + '"' + (extra || '') + '>' + body + '</g>'; }
  /** 组装 symbol 与 meta。def = { id, name, category, kind, resource, facility, w, d, up, tags, roof, note, draw(W, D, r, id) }。 */
  function make(def) {
    var W = def.w * CELL, D = def.d * CELL, up = def.up || 0, H = D + up;
    var r = rng(hash(def.id));
    var body = def.draw(W, D, r, def.id);
    var svg = '<symbol id="' + def.id + '" viewBox="0 0 ' + W + ' ' + H + '" overflow="visible"><g transform="translate(0,' + up + ')">' + body + '</g></symbol>';
    var meta = {
      id: def.id, style: 'east', race: 'common', category: def.category, kind: def.kind,
      resource: def.resource, subtype: def.subtype || null, facility: def.facility == null ? null : def.facility, variant: def.variant || 1,
      footprint: [def.w, def.d], height_px: up, anchor: [W / 2, H], viewBox: [0, 0, W, H],
      tags: def.tags || [], roof: def.roof || 'none', name: def.name
    };
    if (def.note) meta.note = def.note;
    return { id: def.id, name: def.name, svg: svg, meta: meta };
  }
  return { CELL: CELL, S: S, f: f, rng: rng, hash: hash, fop: fop, op: op, poly: poly, pl: pl, path: path, rect: rect,
    ell: ell, circ: circ, ln: ln, shadow: shadow, shadowEll: shadowEll, clip: clip, g: g, make: make };
});
