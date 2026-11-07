/*
 * 织梦 · 东方城镇地面（east-ground）共用画笔（美术素材，尚未接入游戏）
 *
 * 国潮不透明平涂 + 金线勾边，色板与规范第 2 节东方表、fog-xiangyun.js 的 PAL 一致。
 * 水色 C.water = #6cc1b3，与 special-infra 的东方码头、拱桥水面（EAST.water）完全相同，拼在一起看不出两种水。
 * 浏览器挂 window.TownArtEG_core，Node 用 module.exports。全部是原创程序化路径，不读外部图片。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory();
  else root.TownArtEG_core = factory();
})(this, function () {
  'use strict';
  var CELL = 48;

  function rng(seed) { // mulberry32
    return function () {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      var t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  function f(n) { return String(Math.round(n * 100) / 100); }
  function hx(c) { return [1, 3, 5].map(function (i) { return parseInt(c.slice(i, i + 2), 16); }); }
  function mix(a, b, t) {
    var A = hx(a), B = hx(b);
    return '#' + A.map(function (v, i) { var x = Math.round(v + (B[i] - v) * t); return (x < 16 ? '0' : '') + x.toString(16); }).join('');
  }

  var C = {
    gold: '#c98f3c', gold2: '#f3c46a', cream: '#f1dcae', creamL: '#fbf0d4', ochre: '#eeb24f', ochreL: '#f8d78e',
    orange: '#e47c36', vermil: '#cd5030', vermilL: '#e7864f', umber: '#8c3d22', umberL: '#b5623a',
    teal: '#2e938d', tealL: '#6cc1b3', navy: '#1f3c5b', navyL: '#30697f', gray: '#5d6670', grayL: '#7b8590',
    grass: '#d9c58f', shadow: '#1f3c5b',
    water: '#6cc1b3', stone: '#c9b48a', stone2: '#b39b6f'      // 与 special-infra EAST.water / stone / stone2 相同
  };
  C.leaf = mix(C.teal, '#5f7d3a', 0.45); C.leafL = mix(C.tealL, '#a9c46a', 0.4); C.leafD = mix(C.leaf, C.navy, 0.35);
  C.rock = mix(C.grayL, C.cream, 0.45); C.rockL = mix(C.grayL, C.creamL, 0.68); C.rockD = mix(C.gray, C.grayL, 0.4);
  C.mud = mix(C.umber, C.ochre, 0.42);           // 岸壁（湿土）
  C.damp = mix(C.grass, C.umberL, 0.32);         // 岸边湿土带
  C.straw = mix(C.ochre, C.cream, 0.3); C.strawD = mix(C.ochre, C.umber, 0.35);
  C.wood = mix(C.umberL, C.ochre, 0.25); C.woodD = C.umber;
  C.bamboo = mix(C.ochre, '#7d8a3a', 0.35); C.bambooD = mix(C.teal, '#6f8a2c', 0.4);
  C.brick = mix(C.grayL, C.cream, 0.32); C.brickL = mix(C.grayL, C.creamL, 0.5); C.brickD = mix(C.gray, C.grayL, 0.55);

  function op(o) { return ' fill-opacity="' + o + '"'; }
  function sop(o) { return ' stroke-opacity="' + o + '"'; }
  function pt(p) { return f(p[0]) + ' ' + f(p[1]); }
  function poly(pts, open) { return pts.map(function (p, i) { return (i ? 'L' : 'M') + pt(p); }).join('') + (open ? '' : 'Z'); }
  function path(d, fill, ln, lw, extra) {
    return '<path d="' + d + '" fill="' + (fill || 'none') + '"' +
      (ln ? ' stroke="' + ln + '" stroke-width="' + f(lw || 1) + '" stroke-linejoin="round" stroke-linecap="round"' : '') + (extra || '') + '/>';
  }
  function line(d, color, lw, extra) { return path(d, 'none', color, lw, extra); }
  function rect(x, y, w, h, fill, ln, lw, extra) { return path('M' + f(x) + ' ' + f(y) + 'H' + f(x + w) + 'V' + f(y + h) + 'H' + f(x) + 'Z', fill, ln, lw, extra); }
  function ell(cx, cy, rx, ry, fill, ln, lw, extra) {
    return '<ellipse cx="' + f(cx) + '" cy="' + f(cy) + '" rx="' + f(rx) + '" ry="' + f(ry) + '" fill="' + (fill || 'none') + '"' +
      (ln ? ' stroke="' + ln + '" stroke-width="' + f(lw || 1) + '"' : '') + (extra || '') + '/>';
  }
  function circ(cx, cy, r, fill, ln, lw, extra) { return ell(cx, cy, r, r, fill, ln, lw, extra); }
  /** 投影：东方藏青 0.2 平涂，落在右下。 */
  function shadow(cx, cy, rx, ry) { return ell(cx, cy, rx, ry, C.shadow, null, 0, op(0.2)); }

  // 每个 symbol 一个 ctx：内部 clipPath id 都带 symbol id 前缀
  function Ctx(id, seed) { this.id = id; this.n = 0; this.r = rng(seed || 1); }
  Ctx.prototype.uid = function (s) { return this.id + '-' + (s || 'k') + (this.n++); };
  /** 裁剪：d 为裁剪路径，evenodd 时按奇偶规则（用来取「瓦片减去水面」），tf 是裁剪路径自己的 transform。 */
  function clip(ctx, d, inner, evenodd, tf) {
    var id = ctx.uid('clip');
    return '<clipPath id="' + id + '"><path d="' + d + '"' + (evenodd ? ' clip-rule="evenodd"' : '') + (tf ? ' transform="' + tf + '"' : '') +
      '/></clipPath><g clip-path="url(#' + id + ')">' + inner + '</g>';
  }
  // 周期 48 的环绕：元素 bbox 越过瓦片边时，在对边再画一份
  function wrap(x, y, w, h, draw) {
    var s = '';
    [-48, 0, 48].forEach(function (ox) {
      [-48, 0, 48].forEach(function (oy) {
        if (x + ox < 48 && x + ox + w > 0 && y + oy < 48 && y + oy + h > 0) s += draw(x + ox, y + oy);
      });
    });
    return s;
  }
  function bits(m) { return ('000' + m.toString(2)).slice(-4); }
  function pad2(n) { return (n < 10 ? '0' : '') + n; }

  /** 地面层瓦片：48×48，无上伸，锚点 = 底边中点。 */
  function tileSym(id, body) {
    return { id: id, viewBox: [0, 0, 48, 48], anchor: [24, 48], up: 0,
      svg: '<symbol id="' + id + '" viewBox="0 0 48 48" overflow="visible">' + body + '</symbol>' };
  }
  /** 摆件：局部原点在格子前沿中点左移 24（x∈[0,48]），y=0 是锚点所在的地面线，向上为负。 */
  function propSym(id, up, body) {
    var H = 48 + up;
    return { id: id, viewBox: [0, 0, 48, H], anchor: [24, H], up: up,
      svg: '<symbol id="' + id + '" viewBox="0 0 48 ' + H + '" overflow="visible"><g transform="translate(0 ' + H + ')">' + body + '</g></symbol>' };
  }
  /** 粗扫 SVG 文本里的绝对 y（M/L/Q/C/T/V 与圆、椭圆、矩形），用来核对摆件有没有画出声明的上伸。 */
  function scanTop(svg) {
    var top = 0, m, re = /\bd="([^"]*)"/g;
    while ((m = re.exec(svg))) {
      var tok = m[1].match(/[A-Za-z]|-?\d*\.?\d+(?:e-?\d+)?/g) || [], cmd = '', nums = [];
      var flush = function () {
        var per = { M: 2, L: 2, T: 2, Q: 4, C: 6, V: 1 }[cmd];
        if (!per) return;
        for (var i = 0; i + per <= nums.length; i += per) {
          if (cmd === 'V') { top = Math.min(top, nums[i]); continue; }
          for (var k = 1; k < per; k += 2) top = Math.min(top, nums[i + k]);
        }
      };
      tok.forEach(function (t) { if (/[A-Za-z]/.test(t)) { flush(); cmd = t; nums = []; } else nums.push(parseFloat(t)); });
      flush();
    }
    var rc = /<ellipse\b[^>]*?\bcy="([-\d.]+)"[^>]*?\bry="([-\d.]+)"/g;
    while ((m = rc.exec(svg))) top = Math.min(top, parseFloat(m[1]) - parseFloat(m[2]));
    return top;
  }

  return {
    CELL: CELL, C: C, rng: rng, f: f, mix: mix, op: op, sop: sop, pt: pt, poly: poly, path: path, line: line, rect: rect,
    ell: ell, circ: circ, shadow: shadow, Ctx: Ctx, clip: clip, wrap: wrap, bits: bits, pad2: pad2,
    tileSym: tileSym, propSym: propSym, scanTop: scanTop
  };
});
