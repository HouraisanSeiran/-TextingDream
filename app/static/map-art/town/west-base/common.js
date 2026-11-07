/*
 * 织梦 · 城镇西式基础素材 —— 公共绘图函数（美术样板，尚未接入游戏）
 * 木刻线描 + 羊皮纸淡彩：不透明平涂 + 墨线勾边 + 少量短排线；不用渐变、高光、模糊。
 * 浏览器里挂 window.TownArtWB_common；Node 里 module.exports。
 * 局部坐标约定（民居）：x 从 0 到 w*48；y = 0 是占地前沿，向上为负，占地后沿 y = -d*48。
 */
(function (root) {
  'use strict';
  var INK = '#4a3826';
  var PAL = {
    ink: INK, paper: '#efdfb2', plaster: '#e9dcc0', wash: '#e3c47a', wood: '#c9a46a',
    stone: '#cfc0a2', stone2: '#bfb093', stone3: '#b1a287', timber: '#8a6a44', dark: '#6b4f32',
    tile: '#b5654a', tile2: '#9e5540', red: '#9a3b2a', slate: '#7d8790', slate2: '#5f6870',
    thatch: '#d2b46c', thatch2: '#b8954e', grass: '#c9c79a', shadow: '#3a2c1e', glass: '#4f3f2c',
    soil: '#a98a5e', leaf: '#8e8f58', leaf2: '#a6a46a'
  };
  // 屋面材质：a 受光面 / b 背光面；step 瓦行间距；tick 瓦缝间距
  var ROOF = {
    tile: { a: PAL.tile, b: PAL.tile2, step: 5, tick: 6, op: 0.5, ridge: PAL.red },
    slate: { a: PAL.slate, b: PAL.slate2, step: 4, tick: 7, op: 0.55, ridge: PAL.slate2 },
    thatch: { a: PAL.thatch, b: PAL.thatch2, step: 7, tick: 3, op: 0.5, ridge: PAL.thatch2 },
    shingle: { a: PAL.wood, b: '#ad8a5c', step: 4, tick: 5, op: 0.5, ridge: PAL.timber }
  };
  var ROOF_ID = { tile: 'gable_tile', slate: 'steep_slate', thatch: 'gable_thatch', shingle: 'gable_tile' };

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
  function poly(pts) {
    return 'M' + pts.map(function (p) { return f(p[0]) + ' ' + f(p[1]); }).join('L') + 'Z';
  }
  function rectD(x, y, w, h) { return poly([[x, y], [x + w, y], [x + w, y + h], [x, y + h]]); }
  function clipped(ctx, d, inner) {
    if (!inner) return '';
    var id = ctx.uid();
    return '<defs><clipPath id="' + id + '"><path d="' + d + '"/></clipPath></defs><g clip-path="url(#' + id + ')">' + inner + '</g>';
  }
  /** 平涂面 + 裁切在面内的纹理 + 墨线外轮廓 */
  function face(ctx, d, fill, tex, sw) {
    return path(d, fill, 0) + clipped(ctx, d, tex) + path(d, 'none', sw == null ? 1.6 : sw);
  }
  function shadowD(d) { return path(d, PAL.shadow, 0, 0.18); }

  // ---------------- 墙面材质（在矩形 x,y,w,h 内画纹理，由调用方裁切） ----------------
  var WALL_FILL = { plaster: PAL.plaster, timber: PAL.plaster, rubble: PAL.stone, ashlar: PAL.stone2, plank: PAL.wood, plankh: PAL.wood };

  function texRubble(ctx, x, y, w, h) {
    var o = '', fills = [PAL.stone, PAL.stone2, '#c7b897', PAL.stone3];
    for (var yy = y + h; yy > y - 6; ) {
      var rh = ctx.rnd(4.5, 7), xx = x - ctx.rnd(0, 6);
      while (xx < x + w) {
        var sw = ctx.rnd(6, 11), j = function () { return ctx.rnd(-0.8, 0.8); };
        var d = poly([[xx + 0.8 + j(), yy - 0.6], [xx + sw - 0.8 + j(), yy - 0.6 + j()], [xx + sw - 0.3, yy - rh * 0.55 + j()],
          [xx + sw - 1.2 + j(), yy - rh + 0.5], [xx + 1 + j(), yy - rh + 0.6 + j()], [xx + 0.2, yy - rh * 0.45]]);
        o += '<path d="' + d + '" fill="' + ctx.pick(fills) + '"' + stroke(0.8, 0.6) + '/>';
        xx += sw;
      }
      yy -= rh;
    }
    return o;
  }
  function texAshlar(ctx, x, y, w, h, course, joint) {
    course = course || 6; joint = joint || 13;
    var d = '', row = 0;
    for (var yy = y + h - course; yy > y; yy -= course, row++) d += 'M' + f(x) + ' ' + f(yy) + 'H' + f(x + w);
    row = 0;
    for (var yb = y + h; yb > y; yb -= course, row++) {
      var off = (row % 2) * joint / 2;
      for (var xx = x + off + joint * 0.7; xx < x + w - 2; xx += joint) d += 'M' + f(xx) + ' ' + f(yb) + 'V' + f(Math.max(y, yb - course));
    }
    return line(d, 0.8, 0.55);
  }
  function texPlank(ctx, x, y, w, h, horiz) {
    var d = '';
    if (horiz) {
      for (var yy = y + h - 4; yy > y; yy -= 4) d += 'M' + f(x) + ' ' + f(yy) + 'H' + f(x + w);
    } else {
      for (var xx = x + 4; xx < x + w; xx += 4 + ctx.rnd(-0.5, 0.8)) d += 'M' + f(xx) + ' ' + f(y) + 'V' + f(y + h);
    }
    var k = '';
    for (var i = 0; i < Math.max(1, Math.round(w * h / 500)); i++) {
      var kx = x + ctx.rnd(2, w - 2), ky = y + ctx.rnd(2, h - 2);
      k += 'M' + f(kx - 1) + ' ' + f(ky) + 'Q' + f(kx) + ' ' + f(ky - 1.4) + ' ' + f(kx + 1) + ' ' + f(ky);
    }
    return line(d, 0.8, 0.45) + line(k, 0.8, 0.5);
  }
  /** 木筋：柱、上下梁、中腰梁、斜撑。spacing 柱距；pattern 'x'|'k'|'v' */
  function texTimber(ctx, x, y, w, h, spacing, pattern) {
    spacing = spacing || 13; pattern = pattern || 'k';
    var n = Math.max(1, Math.round(w / spacing)), sp = w / n, o = '', tw = 2.2, rail = y + h * ctx.rnd(0.42, 0.55);
    function beam(d) { o += '<path d="' + d + '" fill="none" stroke="' + PAL.timber + '" stroke-width="' + tw + '" stroke-linecap="butt"/>'; }
    var d = 'M' + f(x) + ' ' + f(y + 1.1) + 'H' + f(x + w) + 'M' + f(x) + ' ' + f(y + h - 1.1) + 'H' + f(x + w) +
      'M' + f(x) + ' ' + f(rail) + 'H' + f(x + w);
    for (var i = 0; i <= n; i++) {
      var px = Math.min(x + w - 1.1, Math.max(x + 1.1, x + i * sp));
      d += 'M' + f(px) + ' ' + f(y) + 'V' + f(y + h);
    }
    beam(d);
    var b = '';
    for (var k = 0; k < n; k++) {
      var a = x + k * sp, c = a + sp, edge = (k === 0 || k === n - 1);
      if (pattern === 'x' && (k % 2 === 0)) b += 'M' + f(a) + ' ' + f(y) + 'L' + f(c) + ' ' + f(rail) + 'M' + f(c) + ' ' + f(y) + 'L' + f(a) + ' ' + f(rail);
      else if (pattern === 'v') b += 'M' + f(a) + ' ' + f(rail) + 'L' + f((a + c) / 2) + ' ' + f(y + h) + 'L' + f(c) + ' ' + f(rail);
      else if (edge) {
        if (k === 0) b += 'M' + f(a) + ' ' + f(rail) + 'L' + f(c) + ' ' + f(y); else b += 'M' + f(c) + ' ' + f(rail) + 'L' + f(a) + ' ' + f(y);
        if (k === 0) b += 'M' + f(a) + ' ' + f(rail) + 'L' + f(c) + ' ' + f(y + h); else b += 'M' + f(c) + ' ' + f(rail) + 'L' + f(a) + ' ' + f(y + h);
      }
    }
    if (b) beam(b);
    // 木料墨线：沿梁中心再压一道细墨线，模拟木刻勾边
    o += line(d + b, 0.5, 0.45);
    return o;
  }
  function wallTex(ctx, mat, x, y, w, h, opt) {
    opt = opt || {};
    if (mat === 'rubble') return texRubble(ctx, x, y, w, h);
    if (mat === 'ashlar') return texAshlar(ctx, x, y, w, h, opt.course, opt.joint);
    if (mat === 'plank') return texPlank(ctx, x, y, w, h, false);
    if (mat === 'plankh') return texPlank(ctx, x, y, w, h, true);
    if (mat === 'timber') return texTimber(ctx, x, y, w, h, opt.spacing, opt.pattern);
    // 灰泥：几道淡淡的抹灰刷痕
    var d = '';
    for (var i = 0; i < Math.round(w / 16); i++) {
      var sx = x + ctx.rnd(3, w - 6), sy = y + ctx.rnd(3, h - 3);
      d += 'M' + f(sx) + ' ' + f(sy) + 'l' + f(ctx.rnd(2, 4)) + ' ' + f(ctx.rnd(-0.6, 0.6));
    }
    return line(d, 0.8, 0.35);
  }

  /**
   * 立面一层：x0..x1，底边 yb（向上为负），高 h。返回 { svg, top }。
   * opt.fill 覆盖底色；opt.tex 传给 wallTex；opt.band 画底部挑梁（外挑层）。
   */
  function facade(ctx, x0, x1, yb, h, mat, opt) {
    opt = opt || {};
    var d = rectD(x0, yb - h, x1 - x0, h);
    var fill = opt.fill || WALL_FILL[mat] || PAL.plaster;
    var tex = wallTex(ctx, mat, x0, yb - h, x1 - x0, h, opt.tex);
    // 左侧受光、右侧一窄条背光
    tex += rect(x1 - 3, yb - h, 3, h, PAL.shadow, 0, 0.12);
    var o = face(ctx, d, fill, tex, 1.6);
    if (opt.band) o += rect(x0 - 0.5, yb - 2.6, x1 - x0 + 1, 2.6, PAL.dark, 1, 1);
    ctx.top(yb - h);
    return o;
  }
  /** 外挑楼层底部的投影条（画在下层墙面顶端） */
  function jettyShade(x0, x1, y) { return rect(x0, y, x1 - x0, 3, PAL.shadow, 0, 0.22); }

  // ---------------- 屋面 ----------------
  /** 屋面纹理：dir 'h' = 瓦行水平（檐口水平），'v' = 瓦行竖直（檐口沿进深方向，即正山墙两坡） */
  function roofTex(ctx, mat, x, y, w, h, dir) {
    var m = ROOF[mat], d = '', t = '', xx, yy, row;
    var th = mat === 'thatch';
    if (dir === 'v') {
      for (xx = x + m.step, row = 0; xx < x + w + m.step; xx += m.step, row++) {
        d += 'M' + f(xx) + ' ' + f(y) + 'V' + f(y + h);
        for (yy = y + (row % 2) * m.tick / 2; yy < y + h; yy += m.tick * (th ? ctx.rnd(0.7, 1.4) : 1))
          t += 'M' + f(xx - (th ? m.step * ctx.rnd(0.4, 0.7) : m.step)) + ' ' + f(yy) + 'H' + f(xx);
      }
    } else {
      for (yy = y + h - m.step, row = 0; yy > y - m.step; yy -= m.step, row++) {
        d += th ? 'M' + f(x) + ' ' + f(yy) + 'q' + f(w / 4) + ' ' + f(ctx.rnd(-1, 1)) + ' ' + f(w / 2) + ' 0t' + f(w / 2) + ' 0'
          : 'M' + f(x) + ' ' + f(yy) + 'H' + f(x + w);
        for (xx = x + (row % 2) * m.tick / 2; xx < x + w; xx += m.tick * (th ? ctx.rnd(0.7, 1.5) : 1))
          t += 'M' + f(xx) + ' ' + f(yy) + 'v' + f(th ? m.step * ctx.rnd(0.4, 0.75) : m.step);
      }
    }
    return line(d, th ? 0.9 : 0.8, m.op) + line(t, 0.7, m.op * (th ? 0.9 : 0.75));
  }
  /** 背光面上的短排线（木刻阴影） */
  function hatch(ctx, x, y, w, h, gap) {
    var d = '', g = gap || 3.2;
    for (var k = -h; k < w; k += g) d += 'M' + f(x + k) + ' ' + f(y + h) + 'l' + f(Math.min(h, 7)) + ' ' + f(-Math.min(h, 7));
    return line(d, 0.6, 0.4);
  }
  function colors(o) { var m = ROOF[o.mat]; return { a: o.fa || m.a, b: o.fb || m.b, m: m }; }

  /**
   * 侧坡屋面（屋脊平行于正面）。o: x0 x1 墙宽；yE 檐口（正立面墙顶）；D 进深（屏幕像素）；R 屋脊升高；
   * mat；ov 两侧出檐；hip 0..1（0 双坡，1 四坡）或 hx 直接给收山量。返回 { svg, yR, yB, x0, x1, hx }
   */
  function roofSide(ctx, o) {
    var c = colors(o), ov = o.ov == null ? 3 : o.ov, x0 = o.x0 - ov, x1 = o.x1 + ov, yE = o.yE + 2;
    var yR = o.yE - o.D / 2 - o.R, yB = o.yE - o.D;
    var hx = Math.min((x1 - x0) / 2, o.hx != null ? o.hx : (o.hip || 0) * o.D / 2), s = '';
    s += rect(o.x0, o.yE + 2, o.x1 - o.x0, 3.5, PAL.shadow, 0, 0.25);
    s += face(ctx, poly([[x0 + hx, yR], [x1 - hx, yR], [x1, yB], [x0, yB]]), c.b, '', 1.4);
    if (hx > 0) {
      var lt = poly([[x0, yE], [x0 + hx, yR], [x0, yB]]), rt = poly([[x1, yE], [x1 - hx, yR], [x1, yB]]);
      s += face(ctx, lt, c.a, roofTex(ctx, o.mat, x0, Math.min(yR, yB), hx, yE - Math.min(yR, yB), 'v'), 1.6);
      s += face(ctx, rt, c.b, roofTex(ctx, o.mat, x1 - hx, Math.min(yR, yB), hx, yE - Math.min(yR, yB), 'v') +
        hatch(ctx, x1 - hx, Math.min(yR, yB), hx, yE - Math.min(yR, yB)), 1.6);
    }
    var fr = poly([[x0, yE], [x1, yE], [x1 - hx, yR], [x0 + hx, yR]]);
    s += face(ctx, fr, c.a, roofTex(ctx, o.mat, x0, yR, x1 - x0, yE - yR, 'h'), 1.6);
    if (hx === 0) {
      s += rect(x0 - 0.6, yR, 2.6, yE - yR, PAL.dark, 1) + rect(x1 - 2, yR, 2.6, yE - yR, PAL.dark, 1);
    }
    if (hx < (x1 - x0) / 2 - 1) s += line('M' + f(x0 + hx) + ' ' + f(yR) + 'H' + f(x1 - hx), 2.4, 1, c.m.ridge) +
      line('M' + f(x0 + hx) + ' ' + f(yR - 1.2) + 'H' + f(x1 - hx), 0.9, 0.8);
    s += line('M' + f(x0) + ' ' + f(yE) + 'H' + f(x1), 1.8);
    ctx.top(Math.min(yR, yB) - 2);
    return { svg: s, yR: yR, yB: yB, x0: x0, x1: x1, hx: hx };
  }
  /**
   * 正山墙屋面（屋脊垂直于正面，山墙朝街）。o: x0 x1 yE D R mat ov；gmat/gfill/gtex 山花墙面；
   * jerkin 半歇山截顶比例（0..0.4）。返回 { svg, apex }
   */
  function roofFront(ctx, o) {
    var c = colors(o), ov = o.ov == null ? 3 : o.ov, x0 = o.x0, x1 = o.x1, xc = (x0 + x1) / 2, yE = o.yE, R = o.R, D = o.D;
    var k = R / ((x1 - x0) / 2), s = '';
    var L = [x0 - ov, yE + ov * k], Rr = [x1 + ov, yE + ov * k], A = [xc, yE - R - 1.5];
    var left = poly([L, A, [A[0], A[1] - D], [L[0], L[1] - D]]), right = poly([Rr, A, [A[0], A[1] - D], [Rr[0], Rr[1] - D]]);
    s += face(ctx, right, c.b, roofTex(ctx, o.mat, xc, A[1] - D, Rr[0] - xc, Rr[1] - A[1] + D, 'v') +
      hatch(ctx, xc, A[1] - D, Rr[0] - xc, Rr[1] - A[1] + D, 4), 1.6);
    s += face(ctx, left, c.a, roofTex(ctx, o.mat, L[0], A[1] - D, xc - L[0], L[1] - A[1] + D, 'v'), 1.6);
    var gm = o.gmat || 'plaster';
    var tri = poly([[x0, yE], [x1, yE], [xc, yE - R]]);
    s += face(ctx, tri, o.gfill || WALL_FILL[gm] || PAL.plaster, wallTex(ctx, gm, x0, yE - R, x1 - x0, R, o.gtex), 1.4);
    var bd = 'M' + f(L[0]) + ' ' + f(L[1]) + 'L' + f(A[0]) + ' ' + f(A[1]) + 'L' + f(Rr[0]) + ' ' + f(Rr[1]);
    s += line(bd, 4.4, 1) + line(bd, 2.4, 1, o.board || PAL.timber);
    s += line('M' + f(A[0]) + ' ' + f(A[1]) + 'V' + f(A[1] - D), 1.8);
    if (o.finial) s += line('M' + f(xc) + ' ' + f(A[1]) + 'V' + f(A[1] - 6), 1.6) + '<circle cx="' + f(xc) + '" cy="' + f(A[1] - 6.5) + '" r="1.6" fill="' + PAL.dark + '"' + stroke(0.8) + '/>';
    ctx.top(A[1] - D - (o.finial ? 9 : 2));
    return { svg: s, apex: A, k: k };
  }
  /** 单坡屋面：前低后高。o: x0 x1 yE D R mat ov */
  function roofMono(ctx, o) {
    var c = colors(o), ov = o.ov == null ? 3 : o.ov, x0 = o.x0 - ov, x1 = o.x1 + ov, yE = o.yE + 2, yT = o.yE - o.D - o.R, s = '';
    s += rect(o.x0, o.yE + 2, o.x1 - o.x0, 3.5, PAL.shadow, 0, 0.25);
    var d = rectD(x0, yT, x1 - x0, yE - yT);
    s += face(ctx, d, c.a, roofTex(ctx, o.mat, x0, yT, x1 - x0, yE - yT, 'h'), 1.6);
    s += rect(x0 - 0.6, yT, 2.6, yE - yT, PAL.dark, 1) + rect(x1 - 2, yT, 2.6, yE - yT, PAL.dark, 1);
    s += line('M' + f(x0) + ' ' + f(yE) + 'H' + f(x1), 1.8);
    ctx.top(yT - 2);
    return { svg: s, yT: yT };
  }
  /** 圆塔：中心 cx，前沿地面 yF，半径 r，墙高 H，锥顶高 R。椭圆率 0.55 表示俯角下的圆。 */
  function roundTower(ctx, cx, yF, r, H, R, o) {
    o = o || {};
    var ry = r * 0.55, yc = yF - ry, yt = yc - H, s = '';
    var body = 'M' + f(cx - r) + ' ' + f(yt) + 'V' + f(yc) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + r) + ' ' + f(yc) + 'V' + f(yt) + 'Z';
    var tex = wallTex(ctx, o.mat || 'ashlar', cx - r, yt - ry, 2 * r, H + 2 * ry, o.tex) +
      rect(cx + r * 0.45, yt - ry, r * 0.55, H + 2 * ry, PAL.shadow, 0, 0.16) + rect(cx - r, yt - ry, r * 0.25, H + 2 * ry, PAL.paper, 0, 0.18);
    s += face(ctx, body, o.fill || PAL.stone, tex, 1.6);
    if (R > 0) {
      var ov = o.ov == null ? 3 : o.ov, rr = r + ov, cone = 'M' + f(cx - rr) + ' ' + f(yt + 1) + 'L' + f(cx) + ' ' + f(yt - R) + 'L' + f(cx + rr) + ' ' + f(yt + 1) +
        'A' + f(rr) + ' ' + f(rr * 0.55) + ' 0 0 1 ' + f(cx - rr) + ' ' + f(yt + 1) + 'Z';
      var m = ROOF[o.roof || 'slate'], t = '';
      for (var i = 1; i < 6; i++) {
        var q = i / 6, yy = yt - R + (R + rr * 0.5) * q, hw = rr * q;
        t += 'M' + f(cx - hw) + ' ' + f(yy - rr * 0.25 * q) + 'Q' + f(cx) + ' ' + f(yy + rr * 0.55 * q) + ' ' + f(cx + hw) + ' ' + f(yy - rr * 0.25 * q);
      }
      for (var j = -3; j <= 3; j++) t += 'M' + f(cx) + ' ' + f(yt - R) + 'L' + f(cx + j * rr / 3.2) + ' ' + f(yt + rr * 0.5 * Math.cos(j / 3.4));
      s += rect(cx - r, yt + 1, 2 * r, 4, PAL.shadow, 0, 0.25);
      s += face(ctx, cone, o.fa || m.a, line(t, 0.8, m.op) +
        path('M' + f(cx) + ' ' + f(yt - R) + 'L' + f(cx + rr) + ' ' + f(yt + 1) + 'A' + f(rr) + ' ' + f(rr * 0.55) + ' 0 0 1 ' + f(cx + rr * 0.3) + ' ' + f(yt + rr * 0.53) + 'Z', o.fb || m.b, 0, 0.7), 1.6);
      if (o.finial !== false) s += line('M' + f(cx) + ' ' + f(yt - R) + 'v-7', 1.4) + '<path d="M' + f(cx) + ' ' + f(yt - R - 7) + 'l6 1.6l-6 1.8Z" fill="' + PAL.red + '"' + stroke(0.7) + '/>';
      ctx.top(yt - R - 9);
    } else {
      s += '<ellipse cx="' + f(cx) + '" cy="' + f(yt) + '" rx="' + f(r) + '" ry="' + f(ry) + '" fill="' + PAL.stone2 + '"' + stroke(1.4) + '/>';
      ctx.top(yt - ry);
    }
    return { svg: s, yt: yt, yc: yc, ry: ry };
  }

  // ---------------- 门窗与附件 ----------------
  /** 窗：x,y 左上；kind 'shutter'(带百叶) 'lead'(铅条菱格) 'slit'(窄窗) 'arch'(拱窗) 'plain' */
  function win(ctx, x, y, w, h, kind, opt) {
    opt = opt || {};
    var s = '', g = PAL.glass;
    if (kind === 'arch') {
      var d = 'M' + f(x) + ' ' + f(y + h) + 'V' + f(y + w / 2) + 'A' + f(w / 2) + ' ' + f(w / 2) + ' 0 0 1 ' + f(x + w) + ' ' + f(y + w / 2) + 'V' + f(y + h) + 'Z';
      s += path(d, g, 1.2) + line('M' + f(x + w / 2) + ' ' + f(y + 1) + 'V' + f(y + h) + 'M' + f(x) + ' ' + f(y + h * 0.55) + 'H' + f(x + w), 0.8, 0.8, PAL.wash);
      s += rect(x - 1.5, y + h, w + 3, 2, PAL.stone2, 0.9);
      return s;
    }
    if (kind === 'slit') return rect(x, y, w, h, g, 1) + rect(x - 1.2, y + h, w + 2.4, 1.6, PAL.stone2, 0.8);
    s += rect(x - 1.2, y - 1.2, w + 2.4, h + 2.4, opt.frame || PAL.timber, 1);
    s += rect(x, y, w, h, g, 0);
    if (kind === 'lead') {
      var dd = '';
      for (var k = -h; k < w; k += 3) dd += 'M' + f(x + k) + ' ' + f(y + h) + 'l' + f(h) + ' ' + f(-h) + 'M' + f(x + k + h) + ' ' + f(y + h) + 'l' + f(-h) + ' ' + f(-h);
      s += clipped(ctx, rectD(x, y, w, h), line(dd, 0.6, 0.7, PAL.wash));
    } else {
      s += line('M' + f(x + w / 2) + ' ' + f(y) + 'V' + f(y + h) + 'M' + f(x) + ' ' + f(y + h / 2) + 'H' + f(x + w), 1, 1, opt.frame || PAL.timber);
    }
    if (kind === 'shutter') {
      var sc = opt.shutter || PAL.dark, sw = Math.max(2.4, w * 0.45);
      s += rect(x - 1.4 - sw, y - 0.6, sw, h + 1.2, sc, 0.9) + rect(x + w + 1.4, y - 0.6, sw, h + 1.2, sc, 0.9);
      s += line('M' + f(x - 1.4 - sw) + ' ' + f(y + h / 2) + 'h' + f(sw) + 'M' + f(x + w + 1.4) + ' ' + f(y + h / 2) + 'h' + f(sw), 0.6, 0.6);
    }
    if (opt.box) s += rect(x - 1.5, y + h + 1, w + 3, 2.6, PAL.dark, 0.8) + line('M' + f(x) + ' ' + f(y + h + 1) + 'q1.5 -2.5 3 0q1.5 -2.5 3 0q1.5 -2.5 3 0', 1.4, 1, opt.flower || PAL.red);
    s += line('M' + f(x - 1.2) + ' ' + f(y - 1.2) + 'H' + f(x + w + 1.2), 0.9);
    return s;
  }
  /** 门：x 左，yb 门槛（地面），w,h；kind 'plank' 'arch' 'dutch'(上下分扇) 'wide'(双开大门) */
  function door(ctx, x, yb, w, h, kind, opt) {
    opt = opt || {};
    var y = yb - h, s = '', fill = opt.fill || PAL.timber;
    var d = kind === 'arch' || kind === 'wide'
      ? 'M' + f(x) + ' ' + f(yb) + 'V' + f(y + w / 2) + 'A' + f(w / 2) + ' ' + f(Math.min(w / 2, h * 0.4)) + ' 0 0 1 ' + f(x + w) + ' ' + f(y + w / 2) + 'V' + f(yb) + 'Z'
      : rectD(x, y, w, h);
    if (opt.surround) s += path(kind === 'arch' || kind === 'wide'
      ? 'M' + f(x - 2.4) + ' ' + f(yb) + 'V' + f(y + w / 2) + 'A' + f(w / 2 + 2.4) + ' ' + f(Math.min(w / 2, h * 0.4) + 2.4) + ' 0 0 1 ' + f(x + w + 2.4) + ' ' + f(y + w / 2) + 'V' + f(yb) + 'Z'
      : rectD(x - 2.2, y - 2.2, w + 4.4, h + 2.2), PAL.stone2, 1.2);
    var t = '';
    for (var xx = x + 2.6; xx < x + w - 1; xx += 2.8) t += 'M' + f(xx) + ' ' + f(y - 4) + 'V' + f(yb);
    if (kind === 'wide') t += 'M' + f(x + w / 2) + ' ' + f(y - 4) + 'V' + f(yb);
    var hg = 'M' + f(x + 0.5) + ' ' + f(y + h * 0.3) + 'h' + f(w * 0.55) + 'M' + f(x + 0.5) + ' ' + f(y + h * 0.75) + 'h' + f(w * 0.55);
    if (kind === 'dutch') hg += 'M' + f(x) + ' ' + f(y + h * 0.5) + 'H' + f(x + w);
    s += path(d, fill, 0) + clipped(ctx, d, line(t, 0.6, 0.55) + line(hg, 1.1, 0.85)) + path(d, 'none', 1.3);
    s += '<circle cx="' + f(x + w * (kind === 'wide' ? 0.42 : 0.8)) + '" cy="' + f(yb - h * 0.45) + '" r="0.8" fill="' + INK + '"/>';
    if (opt.step) s += rect(x - 2, yb - 1.6, w + 4, 2.2, PAL.stone2, 0.9);
    return s;
  }
  /** 烟囱：x 左，yb 根部（被屋面盖住的位置），yt 顶，w 宽；mat 'stone'|'brick' */
  function chimney(ctx, x, yb, yt, w, mat) {
    var d = rectD(x, yt, w, yb - yt), s = '';
    var tex = mat === 'brick' ? texAshlar(ctx, x, yt, w, yb - yt, 3.2, 5) : texRubble(ctx, x, yt, w, yb - yt);
    s += face(ctx, d, mat === 'brick' ? '#c08a62' : PAL.stone, tex + rect(x + w - 2.4, yt, 2.4, yb - yt, PAL.shadow, 0, 0.18), 1.4);
    s += rect(x - 1.5, yt - 2.6, w + 3, 3, PAL.stone2, 1.2);
    s += '<ellipse cx="' + f(x + w / 2) + '" cy="' + f(yt - 1.4) + '" rx="' + f(w / 2 - 1) + '" ry="0.9" fill="' + INK + '"/>';
    ctx.top(yt - 4);
    return s;
  }
  /** 一缕炊烟（木刻卷线），不填充 */
  function smoke(ctx, x, y) {
    var d = 'M' + f(x) + ' ' + f(y) + 'c-3 -4 3 -6 0 -10c-3 -4 4 -6 1 -10';
    ctx.top(y - 21);
    return line(d, 1, 0.45);
  }
  /** 老虎窗：坐在侧坡屋面上；cx 中心，yb 底（坡面上的位置），w 宽，h 立面高，mat 屋面材质 */
  function dormer(ctx, cx, yb, w, h, mat) {
    var x0 = cx - w / 2, x1 = cx + w / 2, s = '';
    s += face(ctx, rectD(x0, yb - h, w, h), PAL.plaster, '', 1.2);
    s += win(ctx, x0 + w * 0.25, yb - h + 2.2, w * 0.5, h - 4, 'plain');
    var r = roofFront(ctx, { x0: x0, x1: x1, yE: yb - h, D: 5, R: w * 0.42, mat: mat, ov: 1.6, gmat: 'plaster' });
    return s + r.svg;
  }
  /** 挂招牌：铁臂伸出墙面，木牌；icon 'mug'|'loaf'|'key'|'boot' */
  function sign(ctx, x, y, icon) {
    var s = line('M' + f(x) + ' ' + f(y) + 'h12M' + f(x) + ' ' + f(y + 4) + 'l5 -4', 1.2);
    s += line('M' + f(x + 4) + ' ' + f(y) + 'v2.5M' + f(x + 11) + ' ' + f(y) + 'v2.5', 0.7);
    s += rect(x + 2, y + 2.5, 11, 8, PAL.wash, 1.1, 1, 0.8);
    var c = x + 7.5, m = y + 6.5;
    if (icon === 'mug') s += rect(c - 2.5, m - 2.5, 4, 5, PAL.dark, 0) + line('M' + f(c + 1.5) + ' ' + f(m - 1.5) + 'h1.5v3h-1.5', 0.8);
    else if (icon === 'loaf') s += '<ellipse cx="' + f(c) + '" cy="' + f(m) + '" rx="3.6" ry="2" fill="' + PAL.timber + '"/>';
    else if (icon === 'key') s += line('M' + f(c - 3) + ' ' + f(m) + 'h6m0 0v1.6m-1.6 -1.6v1.2', 1) + '<circle cx="' + f(c - 3.4) + '" cy="' + f(m) + '" r="1.2" fill="none"' + stroke(0.9) + '/>';
    else s += path('M' + f(c - 2) + ' ' + f(m - 3) + 'h2v3.6h2.6v1.6h-4.6Z', PAL.dark, 0);
    return s;
  }
  /** 篱笆（沿 y 水平一排），x0..x1，yb 地面，h 高 */
  function fence(ctx, x0, x1, yb, h, kind) {
    var d = '', s = '';
    if (kind === 'wall') {
      var dd = rectD(x0, yb - h, x1 - x0, h);
      return face(ctx, dd, PAL.stone, texRubble(ctx, x0, yb - h, x1 - x0, h), 1.3) + rect(x0 - 0.5, yb - h - 1.6, x1 - x0 + 1, 2.2, PAL.stone2, 1);
    }
    for (var x = x0 + 1; x <= x1 - 0.5; x += 4) d += 'M' + f(x) + ' ' + f(yb) + 'V' + f(yb - h + ctx.rnd(-0.6, 0.6));
    s += line(d, 2, 1, PAL.wood) + line(d, 0.6, 0.6);
    s += line('M' + f(x0) + ' ' + f(yb - h * 0.35) + 'H' + f(x1) + 'M' + f(x0) + ' ' + f(yb - h * 0.75) + 'H' + f(x1), 1.1);
    return s;
  }
  /** 菜畦：x,y 左上，w,h；几垄带叶子的作物 */
  function garden(ctx, x, y, w, h) {
    var s = rect(x, y, w, h, PAL.soil, 1, 1, 1.5), d = '', lv = '';
    for (var yy = y + 3; yy < y + h - 1; yy += 4.5) {
      d += 'M' + f(x + 1.5) + ' ' + f(yy + 1) + 'H' + f(x + w - 1.5);
      for (var xx = x + 3 + ctx.rnd(0, 1.5); xx < x + w - 2; xx += ctx.rnd(3.2, 4.4))
        lv += 'M' + f(xx - 1.4) + ' ' + f(yy + 0.8) + 'q1.4 -3 2.8 0';
    }
    return s + line(d, 0.7, 0.5) + '<path d="' + lv + '" fill="' + PAL.leaf + '"' + stroke(0.6, 0.8) + '/>';
  }
  /** 外楼梯：沿立面斜上，x0 底端 x，yb 地面，x1 顶端 x，yt 平台高；带扶手 */
  function stairs(ctx, xa, yb, xb, yt) {
    var n = Math.max(3, Math.round((yb - yt) / 4)), s = '', dir = xb > xa ? 1 : -1, sw = 5;
    var d = 'M' + f(xa) + ' ' + f(yb) + 'L' + f(xb) + ' ' + f(yt) + 'L' + f(xb) + ' ' + f(yt + sw) + 'L' + f(xa + dir * sw * 0.8) + ' ' + f(yb) + 'Z';
    var t = '';
    for (var i = 1; i < n; i++) { var q = i / n, px = xa + (xb - xa) * q, py = yb + (yt - yb) * q; t += 'M' + f(px) + ' ' + f(py) + 'v' + f(sw); }
    s += face(ctx, d, PAL.wood, line(t, 0.8, 0.8), 1.2);
    s += line('M' + f(xa) + ' ' + f(yb - 7) + 'L' + f(xb) + ' ' + f(yt - 7) + 'M' + f(xa) + ' ' + f(yb) + 'v-7M' + f((xa + xb) / 2) + ' ' + f((yb + yt) / 2) + 'v-7', 1);
    return s;
  }
  /** 地面投影：占地前沿下方 4 px + 右侧一条 */
  function groundShadow(x0, x1, yb, back) {
    return path(poly([[x0 + 4, yb], [x1, yb], [x1 + 4, yb + 4], [x0 + 6, yb + 4]]), PAL.shadow, 0, 0.18) +
      (back != null ? path(poly([[x1, yb], [x1 + 4, yb + 4], [x1 + 4, back + 6], [x1, back]]), PAL.shadow, 0, 0.18) : '');
  }
  /** 一棵小果树（院子里） */
  function shrub(ctx, cx, yb, r) {
    var s = line('M' + f(cx) + ' ' + f(yb) + 'v' + f(-r), 2, 1, PAL.dark), d = '';
    var n = 7;
    for (var i = 0; i <= n; i++) {
      var a = Math.PI * (1 - i / n) * 1.0 + Math.PI * 0.0, rr = r * ctx.rnd(0.85, 1.1);
      var px = cx + Math.cos(Math.PI + a) * rr * 0 + Math.cos(Math.PI * i / n + Math.PI) * rr, py = yb - r - Math.sin(Math.PI * i / n) * rr * 0.9;
      d += (i ? 'L' : 'M') + f(px) + ' ' + f(py);
    }
    d += 'Q' + f(cx) + ' ' + f(yb - r * 0.3) + ' ' + f(cx - r) + ' ' + f(yb - r) + 'Z';
    s += path(d, PAL.leaf2, 1.3) + line('M' + f(cx - r * 0.4) + ' ' + f(yb - r * 1.3) + 'q2 -1 3 1M' + f(cx + r * 0.1) + ' ' + f(yb - r * 1.6) + 'q2 -1 3 1', 0.7, 0.6);
    ctx.top(yb - r * 2);
    return s;
  }

  var API = {
    PAL: PAL, ROOF: ROOF, ROOF_ID: ROOF_ID, INK: INK, WALL_FILL: WALL_FILL,
    f: f, rng: rng, hashStr: hashStr, Ctx: Ctx, stroke: stroke, rect: rect, path: path, line: line, poly: poly, rectD: rectD,
    clipped: clipped, face: face, shadowD: shadowD, wallTex: wallTex, texRubble: texRubble, texAshlar: texAshlar, texPlank: texPlank,
    texTimber: texTimber, hatch: hatch, facade: facade, jettyShade: jettyShade, roofTex: roofTex, roofSide: roofSide, roofFront: roofFront,
    roofMono: roofMono, roundTower: roundTower, win: win, door: door, chimney: chimney, smoke: smoke, dormer: dormer, sign: sign,
    fence: fence, garden: garden, stairs: stairs, groundShadow: groundShadow, shrub: shrub
  };
  root.TownArtWB_common = API;
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
