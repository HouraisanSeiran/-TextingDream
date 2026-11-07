/*
 * 织梦 · 西式资源点素材 —— 公共画笔（3/4 斜俯视；美术样板，尚未接入游戏）
 * 木刻线描 + 羊皮纸淡彩：不透明平涂 + 墨线 #4a3826 勾边 + 少量短排线；不用渐变、高光、模糊。
 * 配色与 west-ground/core.js 一致（只是照抄色值，不在运行时依赖它）。
 * 定义登记：各形状模块调用 C.def({...})，west-site.js 统一组装。
 * 浏览器挂 window.TownArtWS_core；Node 用 module.exports。
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
    water: '#a9b8ad', water2: '#8fa49a',
    mud: '#c2ab7f', yard: '#d8c49a', yard2: '#c6ae80', iron: '#5c5a55', fire: '#d9853f', glow: '#f2d98a',
    // 资源点专用（矿石、晶体等），仍取低饱和、偏羊皮纸的色
    marble: '#f3eee0', marble2: '#ddd6c4', coal: '#3d3a36', coal2: '#55514a',
    ironore: '#8c5a44', copper: '#5f9a84', copper2: '#b9744a', tin: '#a7a9a4', gold: '#d9b24a', silver: '#c9cdd0',
    sulfur: '#d8c24e', sulfur2: '#b9a33a', clay: '#b9734f', clay2: '#9c5d40', salt: '#f4f0e4',
    gem: '#7f6aa0', gem2: '#5f8f9a', amber: '#d48f3a', mana: '#8fb6c9', mana2: '#6d8fb8', bone: '#ece2c8', bone2: '#cdbf9c',
    grape: '#6e4a62', wheat: '#e0c472', wheat2: '#c9a955', herb: '#9aa064', wool: '#f1ead6'
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
  /** 绘制上下文：symbol id 前缀（clipPath id 用）+ 种子随机 */
  function Ctx(id, seed) { this.id = id; this.n = 0; this.r = rng(seed == null ? hashStr(id) : seed); }
  Ctx.prototype.uid = function () { return this.id + '-k' + (++this.n); };
  Ctx.prototype.rnd = function (a, b) { return a + (b - a) * this.r(); };
  Ctx.prototype.int = function (a, b) { return Math.min(b, Math.floor(a + (b - a + 1) * this.r())); };
  Ctx.prototype.pick = function (arr) { return arr[Math.floor(this.r() * arr.length) % arr.length]; };
  Ctx.prototype.chance = function (p) { return this.r() < p; };

  function st(sw, op, color) {
    return ' stroke="' + (color || INK) + '" stroke-width="' + f(sw) + '" stroke-linejoin="round" stroke-linecap="round"' +
      (op != null && op < 1 ? ' stroke-opacity="' + f(op) + '"' : '');
  }
  function fo(fop) { return fop != null && fop < 1 ? ' fill-opacity="' + f(fop) + '"' : ''; }
  function rect(x, y, w, h, fill, sw, fop) {
    return '<rect x="' + f(x) + '" y="' + f(y) + '" width="' + f(w) + '" height="' + f(h) + '" fill="' + (fill || 'none') + '"' +
      fo(fop) + (sw ? st(sw) : '') + '/>';
  }
  function path(d, fill, sw, fop) {
    if (!d) return '';
    return '<path d="' + d + '" fill="' + (fill || 'none') + '"' + fo(fop) + (sw ? st(sw) : '') + '/>';
  }
  function line(d, sw, op, color) {
    if (!d) return '';
    return '<path d="' + d + '" fill="none"' + st(sw, op, color) + '/>';
  }
  function ell(cx, cy, rx, ry, fill, sw, fop) {
    return '<ellipse cx="' + f(cx) + '" cy="' + f(cy) + '" rx="' + f(rx) + '" ry="' + f(ry) + '" fill="' + (fill || 'none') + '"' +
      fo(fop) + (sw ? st(sw) : '') + '/>';
  }
  function poly(pts, open) {
    return 'M' + pts.map(function (p) { return f(p[0]) + ' ' + f(p[1]); }).join('L') + (open ? '' : 'Z');
  }
  function seg(x1, y1, x2, y2) { return 'M' + f(x1) + ' ' + f(y1) + 'L' + f(x2) + ' ' + f(y2); }
  function clip(ctx, d, inner) {
    if (!inner || !d) return '';
    var id = ctx.uid();
    return '<defs><clipPath id="' + id + '"><path d="' + d + '"/></clipPath></defs><g clip-path="url(#' + id + ')">' + inner + '</g>';
  }
  function shade(d) { return path(d, P.shadow, 0, 0.18); }
  function shadowEll(cx, cy, rx, ry) { return ell(cx, cy, rx, ry, P.shadow, 0, 0.18); }

  /** 不规则圆团（树冠、草堆、土堆）：n 个外凸弧围成；返回 d */
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
      var dx = (i - (n - 1) / 2) * 1.6, hh = h * ctx.rnd(0.6, 1);
      d += 'M' + f(x + dx * 0.5) + ' ' + f(y) + 'Q' + f(x + dx) + ' ' + f(y - hh * 0.6) + ' ' + f(x + dx * 1.6 + ctx.rnd(-0.8, 0.8)) + ' ' + f(y - hh);
    }
    return line(d, sw || 0.9, 0.75, color || P.leaf3);
  }
  /** 平顶方块（3/4 视角）：前沿地面线 yb，宽 w，进深（俯视压缩后）dp，高 hp */
  function block(x, yb, w, dp, hp, top, front, sw) {
    return path(poly([[x, yb - hp - dp], [x + w, yb - hp - dp], [x + w, yb - hp], [x, yb - hp]]), top, sw || 1.4) +
      path(poly([[x, yb - hp], [x + w, yb - hp], [x + w, yb], [x, yb]]), front, sw || 1.4);
  }
  /** 棱角石块：中心 (cx, cy) 为底中点；r 宽半径；返回顶面亮、正面暗两块 */
  function rock(ctx, cx, cy, r, fill, fill2, sw) {
    var h = r * ctx.rnd(0.7, 1.05), t = r * ctx.rnd(0.35, 0.55);
    var a = [cx - r, cy - h * 0.35], b = [cx - r * ctx.rnd(0.5, 0.8), cy - h], c = [cx + r * ctx.rnd(0.3, 0.7), cy - h - t * 0.3],
      d = [cx + r, cy - h * 0.45], e = [cx + r * 0.85, cy], g = [cx - r * 0.85, cy];
    var m = [cx + ctx.rnd(-r * 0.2, r * 0.2), cy - h * 0.5];
    return path(poly([a, b, c, d, e, g]), fill2 || P.stone2, sw || 1.2) +
      path(poly([a, b, c, d, m]), fill || P.stone, 0) +
      line(poly([a, m, d], true), 0.8, 0.6);
  }
  /** 一堆碎块（矿石、碎石、煤）：底部土丘 + 若干小块 */
  function heap(ctx, cx, cy, rx, ry, base, chunk, chunk2, n) {
    var s = shadowEll(cx + 3, cy + 1, rx * 1.05, ry * 0.45);
    s += path('M' + f(cx - rx) + ' ' + f(cy) + 'Q' + f(cx - rx * 0.6) + ' ' + f(cy - ry * 1.1) + ' ' + f(cx) + ' ' + f(cy - ry) +
      'Q' + f(cx + rx * 0.6) + ' ' + f(cy - ry * 1.1) + ' ' + f(cx + rx) + ' ' + f(cy) + 'Z', base, 1.4);
    var k = n || 9;
    for (var i = 0; i < k; i++) {
      var u = ctx.rnd(-0.8, 0.8), v = ctx.rnd(0.1, 0.9) * (1 - Math.abs(u) * 0.6);
      var x = cx + u * rx * 0.85, y = cy - v * ry * 0.95 + 1, r = ctx.rnd(1.8, 3.4);
      s += path(poly([[x - r, y], [x - r * 0.6, y - r * 0.9], [x + r * 0.5, y - r], [x + r, y - r * 0.2], [x + r * 0.4, y + r * 0.3]]),
        ctx.chance(0.5) ? chunk : (chunk2 || chunk), 0.8);
    }
    return s;
  }
  /** 原木端面（朝向观者）：同心年轮 */
  function logEnd(cx, cy, r, fill) {
    return ell(cx, cy, r, r * 0.92, fill || P.wash, 1.2) + ell(cx, cy, r * 0.55, r * 0.5, 'none', 0.6) +
      ell(cx, cy, r * 0.18, r * 0.16, P.timber, 0);
  }
  /** 横躺原木（沿 x）：x1→x2，中心线 y，半径 r */
  function logSide(x1, x2, y, r) {
    return path('M' + f(x1) + ' ' + f(y - r) + 'L' + f(x2) + ' ' + f(y - r) + 'A' + f(r * 0.45) + ' ' + f(r) + ' 0 0 1 ' + f(x2) + ' ' + f(y + r) +
      'L' + f(x1) + ' ' + f(y + r) + 'Z', P.timber, 1.2) +
      line(seg(x1 + 3, y - r * 0.3, x2 - 4, y - r * 0.35) + seg(x1 + 6, y + r * 0.35, x2 - 8, y + r * 0.3), 0.6, 0.5) +
      ell(x1, y, r * 0.45, r, P.wash, 1.2) + ell(x1, y, r * 0.18, r * 0.4, 'none', 0.5);
  }
  /** 栅栏：从 (x1,y1) 到 (x2,y2)，n 段，桩高 h */
  function fence(x1, y1, x2, y2, n, h) {
    var s = '', i, dx = (x2 - x1) / n, dy = (y2 - y1) / n;
    s += line(seg(x1, y1 - h * 0.75, x2, y2 - h * 0.75) + seg(x1, y1 - h * 0.35, x2, y2 - h * 0.35), 1.6, 1, P.dark);
    s += line(seg(x1, y1 - h * 0.75, x2, y2 - h * 0.75), 0.8, 1, P.wood);
    for (i = 0; i <= n; i++) s += path(poly([[x1 + dx * i - 1.2, y1 + dy * i - h], [x1 + dx * i + 1.2, y1 + dy * i - h],
      [x1 + dx * i + 1.2, y1 + dy * i], [x1 + dx * i - 1.2, y1 + dy * i]]), P.timber, 0.9);
    return s;
  }
  /** 树桩 */
  function stump(ctx, cx, cy, r) {
    var h = r * ctx.rnd(0.6, 1);
    return shadowEll(cx + 2, cy + 0.5, r * 1.3, r * 0.45) +
      path('M' + f(cx - r) + ' ' + f(cy - h) + 'L' + f(cx - r * 1.1) + ' ' + f(cy) + 'Q' + f(cx) + ' ' + f(cy + r * 0.4) + ' ' + f(cx + r * 1.1) + ' ' + f(cy) +
        'L' + f(cx + r) + ' ' + f(cy - h) + 'Z', P.timber, 1.1) +
      ell(cx, cy - h, r, r * 0.45, P.wash, 1.1) + ell(cx, cy - h, r * 0.45, r * 0.2, 'none', 0.5);
  }
  /** 双坡屋顶（正面看到檐口三角山墙在左右侧不露）：屋面四边形 x0..x1，檐口 ye，屋脊 yr，屋脊内收 inset */
  function roofGable(x0, x1, ye, yr, inset, fill, fill2, rows) {
    var s = path(poly([[x0, ye], [x0 + inset, yr], [x1 - inset, yr], [x1, ye]]), fill, 1.6);
    var n = rows || 4, i, d = '';
    for (i = 1; i < n; i++) {
      var t = i / n, y = yr + (ye - yr) * t, xa = x0 + inset * (1 - t), xb = x1 - inset * (1 - t);
      d += seg(xa + 1, y, xb - 1, y);
    }
    s += line(d, 0.8, 0.5);
    if (fill2) s += path(poly([[x1 - inset, yr], [x1, ye], [x1 - inset * 0.4, ye]]), fill2, 0, 0.9);
    return s;
  }
  /** 木桩柱 */
  function post(x, yb, h, w) {
    w = w || 3;
    return path(poly([[x - w / 2, yb - h], [x + w / 2, yb - h], [x + w / 2, yb], [x - w / 2, yb]]), P.timber, 1);
  }
  /** 车轮（侧面略扁） */
  function wheel(cx, cy, r) {
    var s = ell(cx, cy, r, r, P.wood, 1.3) + ell(cx, cy, r * 0.25, r * 0.25, P.dark, 0.8), d = '';
    for (var i = 0; i < 6; i++) { var a = i * Math.PI / 3; d += seg(cx, cy, cx + Math.cos(a) * r * 0.9, cy + Math.sin(a) * r * 0.9); }
    return s + line(d, 0.8, 0.8);
  }
  /** 在 48×48 平铺格里把元素按 ±48 平移复制后裁切，保证无缝 */
  function tileWrap(ctx, W, H, drawAt) {
    var inner = '', ox, oy;
    for (ox = -W; ox <= W; ox += W) for (oy = -H; oy <= H; oy += H) inner += drawAt(ox, oy);
    return clip(ctx, poly([[0, 0], [W, 0], [W, H], [0, H]]), inner);
  }

  /* ---------- 定义登记 ---------- */
  var defs = [];
  /** 平铺地面一套 4 变体：o = { idKind, name, resource, base, note, scatter(ctx, v) → [{x,y,...}], item(sub, it, x, y) → svg } */
  function groundSet(o) {
    for (var v = 1; v <= 4; v++) (function (v) {
      def({
        idKind: o.idKind, name: o.name, cat: 'ground', resource: o.resource, variant: v, w: 1, d: 1, up: 0,
        tags: ['tile', 'seamless'].concat(o.tags || []), note: o.note || '平铺底纹；元素按 ±48 平移复制后裁切，任意排列无缝',
        draw: function (ctx, W, D) {
          var items = o.scatter(ctx, v), sub = new Ctx(ctx.id + '-w');
          var s = rect(0, 0, W, D, o.base, 0);
          if (o.under) s += o.under(ctx, v, W, D);
          return s + tileWrap(ctx, W, D, function (ox, oy) {
            var t = '';
            items.forEach(function (it, k) { sub.r = rng(k * 7919 + v * 31 + 1); t += o.item(sub, it, it.x + ox, it.y + oy); });
            return t;
          });
        }
      });
    })(v);
  }
  /** 随机散点 n 个（ctx 决定，平铺无缝用） */
  function scatter(ctx, n, t) {
    var a = [];
    for (var i = 0; i < n; i++) a.push({ t: t, x: ctx.rnd(0, 48), y: ctx.rnd(0, 48), k: ctx.r() });
    return a;
  }
  /** o: { idKind, name, cat:'site'|'prop'|'ground', resource, facility, variant, w, d, up, tags, roof, note, draw(ctx, W, D) } */
  function def(o) {
    o.variant = o.variant || 1; o.up = o.up || 0; o.tags = o.tags || []; o.roof = o.roof || 'none';
    o.facility = o.facility === undefined ? null : o.facility;
    defs.push(o); return o;
  }

  var api = {
    P: P, INK: INK, f: f, rng: rng, hashStr: hashStr, Ctx: Ctx, st: st, rect: rect, path: path, line: line, ell: ell,
    poly: poly, seg: seg, clip: clip, shade: shade, shadowEll: shadowEll, blob: blob, tuft: tuft, block: block, rock: rock,
    heap: heap, logEnd: logEnd, logSide: logSide, fence: fence, stump: stump, roofGable: roofGable, post: post, wheel: wheel,
    tileWrap: tileWrap, defs: defs, def: def, groundSet: groundSet, scatter: scatter
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.TownArtWS_core = api;
})(typeof window !== 'undefined' ? window : this);
