/*
 * 织梦 · 城镇矮人族素材 —— 公共画笔（3/4 斜俯视，西式木刻线描 + 羊皮纸淡彩的矮人变种；美术样板，尚未接入游戏）
 * 不透明平涂 + 墨线 #4a3826 勾边 + 少量短排线；不用渐变、高光、模糊。
 * 局部坐标：x 0..w*48；y = 0 为占地前沿，向上为负，占地后沿 y = -d*48。
 * 投影：立面直接向上画；平顶/屋面按"地面进深不压缩"画（顶面高度 = 进深）。光从左上，投影落右下。
 * 浏览器挂 window.TownArtWD_core；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var INK = '#4a3826', CELL = 48;
  var PAL = {
    ink: INK, paper: '#efdfb2', plaster: '#e9dcc0', wash: '#e3c47a', wood: '#c9a46a',
    stone: '#cfc0a2', stone2: '#bfb093', stone3: '#b1a287', timber: '#8a6a44', dark: '#6b4f32',
    tile: '#b5654a', red: '#9a3b2a', slate: '#7d8790', slate2: '#5f6870', grass: '#c9c79a',
    shadow: '#3a2c1e', glass: '#4f3f2c', moss: '#8e8f58', moss2: '#a6a46a',
    // 矮人色
    granite: '#9a958c', granite2: '#aba69c', granite3: '#b6b1a6', deep: '#6f6a62', deep2: '#5c5852',
    copper: '#b8763a', copper2: '#9c6230', verd: '#5f8f7e', verd2: '#7aa494', fire: '#e07a2f', ember: '#f0b04e',
    iron: '#4f4b46', soot: '#3e3a36', hole: '#3b2d1f'
  };
  var GT = [PAL.granite2, PAL.granite, '#a29d93', PAL.granite3];

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
  /** 绘制上下文：symbol id 前缀、种子随机、记录最高点 */
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
  function rect(x, y, w, h, fill, sw, fop, rx) {
    return '<rect x="' + f(x) + '" y="' + f(y) + '" width="' + f(w) + '" height="' + f(h) + '"' + (rx ? ' rx="' + f(rx) + '"' : '') +
      ' fill="' + (fill || 'none') + '"' + (fop != null && fop < 1 ? ' fill-opacity="' + f(fop) + '"' : '') + (sw ? stroke(sw) : '') + '/>';
  }
  function path(d, fill, sw, fop) {
    return '<path d="' + d + '" fill="' + (fill || 'none') + '"' + (fop != null && fop < 1 ? ' fill-opacity="' + f(fop) + '"' : '') +
      (sw ? stroke(sw) : '') + '/>';
  }
  function line(d, sw, op, color) {
    if (!d) return '';
    return '<path d="' + d + '" fill="none"' + stroke(sw, op, color) + '/>';
  }
  function circle(cx, cy, r, fill, sw, op) {
    return '<circle cx="' + f(cx) + '" cy="' + f(cy) + '" r="' + f(r) + '" fill="' + (fill || 'none') + '"' + (sw ? stroke(sw, op) : '') + '/>';
  }
  function ellipse(cx, cy, rx, ry, fill, sw) {
    return '<ellipse cx="' + f(cx) + '" cy="' + f(cy) + '" rx="' + f(rx) + '" ry="' + f(ry) + '" fill="' + (fill || 'none') + '"' + (sw ? stroke(sw) : '') + '/>';
  }
  function poly(pts) { return 'M' + pts.map(function (p) { return f(p[0]) + ' ' + f(p[1]); }).join('L') + 'Z'; }
  function rectD(x, y, w, h) { return poly([[x, y], [x + w, y], [x + w, y + h], [x, y + h]]); }
  function clipped(ctx, d, inner) {
    if (!inner) return '';
    var id = ctx.uid();
    return '<defs><clipPath id="' + id + '"><path d="' + d + '"/></clipPath></defs><g clip-path="url(#' + id + ')">' + inner + '</g>';
  }
  /** 平涂面 + 裁切在面内的纹理 + 墨线外轮廓 */
  function face(ctx, d, fill, tex, sw) { return path(d, fill, 0) + clipped(ctx, d, tex) + path(d, 'none', sw == null ? 1.7 : sw); }
  function shade(d, op) { return path(d, PAL.shadow, 0, op == null ? 0.18 : op); }
  /** 地面投影：建筑右侧一条 + 前沿下 3 px（不超过 xr 与前沿下 6 px） */
  function groundShadow(x0, x1, yb, yBack, xr) {
    xr = Math.min(xr == null ? x1 + 6 : xr, x1 + 7);
    var yl = Math.min(yb + 3, 3);
    return shade(poly([[x1 - 2, yBack + 3], [xr, yBack + 8], [xr, yl], [x0 + 5, yl], [x0 + 3, yb], [x1 - 2, yb]]));
  }

  /**
   * 方整巨石立面：x0..x1，底 yb，高 h。opt.course 层高（默认 8–11 随机），minW/maxW 块长，tones 色，outline 是否勾外框。
   * 每块下沿一窄条暗色，显出石块的厚重感；块间墨线缝；少量斜排线表示凿痕。
   */
  function blocks(ctx, x0, x1, yb, h, opt) {
    opt = opt || {};
    var tones = opt.tones || GT, s = '', jd = '', cd = '', hd = '', y = yb, r = 0, yt = yb - h;
    while (y > yt + 0.5) {
      var ch = opt.course || ctx.rnd(8, 11);
      if (y - ch - yt < 4) ch = y - yt;
      var y0 = y - ch, x = x0 - (r % 2 ? ctx.rnd(5, 11) : ctx.rnd(0, 3));
      while (x < x1 - 0.1) {
        var bw = ctx.rnd(opt.minW || 13, opt.maxW || 24), bx0 = Math.max(x0, x), bx1 = Math.min(x1, x + bw);
        if (bx1 - bx0 < 2) { x += bw; continue; } // 行首错缝块整个落在 x0 左侧：跳过
        if (x1 - bx1 < Math.min(6, (x1 - x0) * 0.3)) bx1 = x1;
        s += rect(bx0, y0, bx1 - bx0, ch, ctx.pick(tones), 0) + rect(bx0, y - 1.6, bx1 - bx0, 1.6, PAL.shadow, 0, 0.12);
        if (bx1 < x1) jd += 'M' + f(bx1) + ' ' + f(y) + 'V' + f(y0);
        if (ctx.chance(0.3) && bx1 - bx0 > 8) {
          var hx = bx1 - ctx.rnd(3, 6), hy = y - 2;
          hd += 'M' + f(hx) + ' ' + f(hy) + 'l1.6 -2.4M' + f(hx + 1.8) + ' ' + f(hy) + 'l1.6 -2.4';
        }
        x = bx1;
      }
      if (y0 > yt + 0.1) cd += 'M' + f(x0) + ' ' + f(y0) + 'H' + f(x1);
      y = y0; r++;
    }
    s += line(cd + jd, 0.9, 0.62) + line(hd, 0.7, 0.4);
    if (opt.shadeR !== false) s += rect(x1 - 3.5, yt, 3.5, h, PAL.shadow, 0, 0.13);
    if (opt.outline !== false) s += path(rectD(x0, yt, x1 - x0, h), 'none', 1.8);
    ctx.top(yt);
    return s;
  }
  /** 平顶：顶面 x0..x1，前沿 yt，进深 dg。opt.parapet 女儿墙宽（0 = 无）、opt.fill 顶面色 */
  function slabTop(ctx, x0, x1, yt, dg, opt) {
    opt = opt || {};
    var p = opt.parapet == null ? 3 : opt.parapet, yb = yt - dg, s = '', d = '', r = 0;
    var D = rectD(x0, yb, x1 - x0, dg);
    s += path(D, opt.fill || PAL.granite3, 0);
    var ix0 = x0 + p, ix1 = x1 - p, iy0 = yb + p, iy1 = yt - p;
    if (p > 0) {
      s += rect(ix0, iy0, ix1 - ix0, iy1 - iy0, opt.floor || '#a8a397', 0.9);
      // 女儿墙在内侧左、后两边投下阴影
      s += shade(poly([[ix0, iy0], [ix1, iy0], [ix1 - 0, iy0 + 2.5], [ix0 + 2.5, iy0 + 2.5], [ix0 + 2.5, iy1], [ix0, iy1]]), 0.2);
    }
    for (var y = iy1 - 8; y > iy0 + 1; y -= 8, r++) d += 'M' + f(ix0) + ' ' + f(y) + 'H' + f(ix1);
    for (var yy = iy1, k = 0; yy > iy0 + 1; yy -= 8, k++)
      for (var x = ix0 + 6 + (k % 2) * 7; x < ix1 - 2; x += 14) d += 'M' + f(x) + ' ' + f(yy) + 'V' + f(Math.max(iy0, yy - 8));
    s += line(d, 0.7, 0.4);
    s += path(D, 'none', 1.7);
    ctx.top(yb);
    return s;
  }

  /**
   * 岩坡：建筑后半截埋进山体。底边 yb（通常在占地中部），x0..x1，最高 h（向上）。
   * 轮廓为折线山脊，块面左亮右暗，加裂隙与几簇苔。返回 svg；ctx.top 记录最高点。
   */
  function rockSlope(ctx, x0, x1, yb, h, opt) {
    opt = opt || {};
    var n = Math.max(4, Math.round((x1 - x0) / 9)), pts = [[x0, yb]], i, s = '', cr = '';
    var lo = opt.lo == null ? 0.45 : opt.lo;
    for (i = 0; i <= n; i++) {
      var t = i / n, edge = Math.pow(Math.sin(Math.PI * t), 0.6);
      var hh = h * (lo + (1 - lo) * edge) * (i % 2 ? ctx.rnd(0.86, 1) : ctx.rnd(0.66, 0.84));
      if (i === 0 || i === n) hh = h * lo * ctx.rnd(0.5, 0.8);
      pts.push([x0 + (x1 - x0) * t + (i && i < n ? ctx.rnd(-3, 3) : 0), yb - hh]);
    }
    pts.push([x1, yb]);
    var D = poly(pts), tex = '';
    // 块面：每段山脊往下拉一条楔面，左半受光、右半背光
    for (i = 1; i < pts.length - 2; i++) {
      var a = pts[i], b = pts[i + 1], mx = (a[0] + b[0]) / 2 + ctx.rnd(-3, 3), my = Math.max(a[1], b[1]) + ctx.rnd(8, 16);
      var light = (a[0] + b[0]) / 2 < (x0 + x1) / 2;
      tex += path(poly([a, b, [mx + 4, my], [mx - 4, my + 2]]), light ? PAL.granite2 : PAL.deep, 0);
      cr += 'M' + f(b[0]) + ' ' + f(b[1]) + 'L' + f(mx + 4) + ' ' + f(my) + 'l' + f(ctx.rnd(-3, 3)) + ' ' + f(ctx.rnd(5, 9));
    }
    tex += rect(x0, yb - 6, x1 - x0, 6, PAL.deep, 0, 0.55);
    for (i = 0; i < Math.round((x1 - x0) / 18); i++) {
      var hx = ctx.rnd(x0 + 4, x1 - 6), hy = ctx.rnd(yb - h * 0.6, yb - 4);
      cr += 'M' + f(hx) + ' ' + f(hy) + 'l3 -1.2M' + f(hx + 1) + ' ' + f(hy + 2) + 'l3 -1.2';
    }
    s += face(ctx, D, opt.fill || PAL.granite, tex + line(cr, 0.8, 0.55), 1.7);
    // 苔丛
    for (i = 0; i < (opt.moss == null ? 2 : opt.moss); i++) {
      var k = 1 + Math.floor(ctx.r() * (pts.length - 3)), p = pts[k], mx = Math.max(x0 + 4.5, Math.min(x1 - 4.5, p[0]));
      s += path('M' + f(mx - 4) + ' ' + f(p[1] + 2) + 'q2 -4 4 -1q2 -3 4 1q-4 2 -8 0Z', PAL.moss, 0.8);
    }
    ctx.top(Math.min.apply(null, pts.map(function (q) { return q[1]; })));
    return s;
  }
  /** 一排铆钉 */
  function rivets(x0, x1, y, step, r) {
    var s = '';
    step = step || 4; r = r || 0.75;
    for (var x = x0; x <= x1 + 0.01; x += step) s += '<circle cx="' + f(x) + '" cy="' + f(y) + '" r="' + f(r) + '" fill="' + INK + '" fill-opacity="0.8"/>';
    return s;
  }
  /**
   * 矮人门：cx 中心，yb 门槛，w×h。kind 'lintel'(巨石过梁) 'arch'(半圆拱) 'trap'(梯形收口) 'round'(圆门)。
   * opt.fill 门板色（默认铜）；门板上横铜箍 + 铆钉；石框厚 opt.frame（默认 4）。
   */
  function door(ctx, cx, yb, w, h, kind, opt) {
    opt = opt || {};
    var x = cx - w / 2, y = yb - h, fr = opt.frame == null ? 4 : opt.frame, s = '', d, ring;
    var fill = opt.fill || PAL.copper;
    if (kind === 'arch') {
      d = 'M' + f(x) + ' ' + f(yb) + 'V' + f(y + w / 2) + 'A' + f(w / 2) + ' ' + f(w / 2) + ' 0 0 1 ' + f(x + w) + ' ' + f(y + w / 2) + 'V' + f(yb) + 'Z';
      ring = 'M' + f(x - fr) + ' ' + f(yb) + 'V' + f(y + w / 2) + 'A' + f(w / 2 + fr) + ' ' + f(w / 2 + fr) + ' 0 0 1 ' + f(x + w + fr) + ' ' + f(y + w / 2) + 'V' + f(yb) + 'Z';
    } else if (kind === 'trap') {
      d = poly([[x, yb], [x + w * 0.16, y], [x + w * 0.84, y], [x + w, yb]]);
      ring = poly([[x - fr, yb], [x + w * 0.16 - fr * 0.7, y - fr], [x + w * 0.84 + fr * 0.7, y - fr], [x + w + fr, yb]]);
    } else if (kind === 'round') {
      var r = w / 2, cy = yb - r;
      d = 'M' + f(x) + ' ' + f(yb) + 'A' + f(r) + ' ' + f(r) + ' 0 1 1 ' + f(x + w) + ' ' + f(yb) + 'Z';
      ring = 'M' + f(x - fr) + ' ' + f(yb) + 'A' + f(r + fr) + ' ' + f(r + fr) + ' 0 1 1 ' + f(x + w + fr) + ' ' + f(yb) + 'Z';
      y = cy - r;
    } else {
      d = rectD(x, y, w, h);
      ring = rectD(x - fr, y - fr, w + 2 * fr, h + fr);
    }
    s += path(ring, opt.ring || PAL.granite3, 1.3);
    if (kind === 'lintel') s += rect(x - fr - 3, y - fr - 5, w + 2 * fr + 6, 6, PAL.granite2, 1.4) + rivets(x - fr, x + w + fr, y - fr - 2, 5);
    if (kind === 'arch') { // 拱石
      var vs = '';
      for (var i = 1; i < 6; i++) {
        var an = Math.PI * i / 6, ax = cx - Math.cos(an) * w / 2, ay = y + w / 2 - Math.sin(an) * w / 2;
        vs += 'M' + f(ax) + ' ' + f(ay) + 'L' + f(cx - Math.cos(an) * (w / 2 + fr)) + ' ' + f(y + w / 2 - Math.sin(an) * (w / 2 + fr));
      }
      s += line(vs, 0.8, 0.7);
    }
    var t = '', bands = opt.bands || 2;
    for (var b = 1; b <= bands; b++) {
      var by = yb - (yb - y) * b / (bands + 1);
      t += rect(x - 1, by - 1.4, w + 2, 2.8, opt.band || PAL.iron, 0) + rivets(x + 1.5, x + w - 1.5, by, 3.2, 0.6);
    }
    if (opt.split !== false) t += line('M' + f(cx) + ' ' + f(y) + 'V' + f(yb), 1, 0.7);
    t += rect(x + w - 2.5, y, 2.5, h + 4, PAL.shadow, 0, 0.2);
    s += path(d, fill, 0) + clipped(ctx, d, t) + path(d, 'none', 1.4);
    s += circle(cx + (opt.split !== false ? -1.8 : w * 0.3), yb - h * 0.42, 1, PAL.ember, 0.6);
    if (opt.step !== false) s += rect(x - fr - 1.5, yb - 2.2, w + 2 * fr + 3, 2.2, PAL.granite2, 1);
    ctx.top(y - fr - 6);
    return s;
  }
  /** 窗：'slit' 窄窗、'square' 方窗带厚过梁、'port' 圆窗铜圈、'fire' 熔火映窗（橙色）。x,y 左上 */
  function win(ctx, x, y, w, h, kind) {
    var s = '';
    if (kind === 'port') {
      var r = w / 2;
      return circle(x + r, y + r, r + 1.8, PAL.copper, 1.1) + circle(x + r, y + r, r, PAL.glass, 0.8) +
        line('M' + f(x + 1) + ' ' + f(y + r) + 'h' + f(w - 2) + 'M' + f(x + r) + ' ' + f(y + 1) + 'v' + f(w - 2), 0.7, 0.8, PAL.copper);
    }
    var g = kind === 'fire' ? PAL.fire : PAL.glass;
    s += rect(x - 1.4, y - 1.4, w + 2.8, h + 2.8, PAL.deep, 0.9);
    s += rect(x, y, w, h, g, 0);
    if (kind === 'fire') s += rect(x, y + h * 0.55, w, h * 0.45, PAL.ember, 0) + rect(x, y, w, 1.6, PAL.shadow, 0, 0.3);
    else if (kind !== 'slit') s += line('M' + f(x + w / 2) + ' ' + f(y) + 'V' + f(y + h), 1.1, 1, PAL.iron);
    s += rect(x - 3, y - 4.2, w + 6, 3.6, PAL.granite2, 1.1) + rect(x - 2, y + h + 1, w + 4, 2, PAL.granite3, 0.9);
    return s;
  }
  /** 符文带：x0..x1，中线 y，高 h。字形由 ctx 种子派生：竖杆 + 1–2 道斜枝 */
  function runes(ctx, x0, x1, y, h, opt) {
    opt = opt || {};
    var s = rect(x0, y - h / 2, x1 - x0, h, opt.fill || PAL.granite3, 1.1), d = '', x = x0 + 4;
    var gh = h * 0.62, top = y - gh / 2;
    while (x < x1 - 4) {
      var k = ctx.int(0, 4);
      d += 'M' + f(x) + ' ' + f(top) + 'v' + f(gh);
      if (k === 0) d += 'M' + f(x) + ' ' + f(top) + 'l2.6 ' + f(gh * 0.35) + 'l-2.6 ' + f(gh * 0.3);
      else if (k === 1) d += 'M' + f(x - 2) + ' ' + f(top) + 'l4 ' + f(gh * 0.5) + 'M' + f(x + 2) + ' ' + f(top) + 'l-4 ' + f(gh * 0.5);
      else if (k === 2) d += 'M' + f(x) + ' ' + f(top + gh * 0.2) + 'l2.6 -' + f(gh * 0.2) + 'M' + f(x) + ' ' + f(top + gh * 0.55) + 'l2.6 -' + f(gh * 0.2);
      else if (k === 3) d += 'M' + f(x - 2.4) + ' ' + f(top + gh * 0.4) + 'h4.8';
      else d += 'M' + f(x) + ' ' + f(top + gh) + 'l2.6 -' + f(gh * 0.45) + 'M' + f(x) + ' ' + f(top) + 'l-2.4 ' + f(gh * 0.35);
      x += ctx.rnd(5.5, 7.5);
    }
    return s + line(d, 0.9, 0.85, opt.color || INK);
  }

  var API = {
    INK: INK, CELL: CELL, PAL: PAL, GT: GT, f: f, rng: rng, hashStr: hashStr, Ctx: Ctx,
    rockSlope: rockSlope, rivets: rivets, door: door, win: win, runes: runes,
    stroke: stroke, rect: rect, path: path, line: line, circle: circle, ellipse: ellipse, poly: poly, rectD: rectD,
    clipped: clipped, face: face, shade: shade, groundShadow: groundShadow, blocks: blocks, slabTop: slabTop
  };
  root.TownArtWD_core = API;
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
