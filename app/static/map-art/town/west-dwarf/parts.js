/*
 * 织梦 · 城镇矮人族素材 —— 部件：烟囱、烟团、齿轮、矿车轨道、石柱、石板顶、石穹顶（美术样板，尚未接入游戏）
 * 局部坐标同 core.js：y = 0 为占地前沿，向上为负。
 * 浏览器挂 window.TownArtWD_parts；Node 用 module.exports。依赖 core.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWD_core;
  var P = C.PAL, f = C.f;

  /** 烟团：木刻风的卷云团，纸灰色不透明平涂 + 淡墨勾边。n 团，自 (x,y) 向右上飘 */
  function smoke(ctx, x, y, n, sc) {
    var s = '', cx = x, cy = y; sc = sc || 1;
    for (var i = 0; i < n; i++) {
      var r = (2.6 + i * 1.1) * sc;
      cx += ctx.rnd(1.5, 3.5) * sc; cy -= r * 1.25;
      var d = 'M' + f(cx - r) + ' ' + f(cy + r * 0.3) + 'a' + f(r * 0.6) + ' ' + f(r * 0.6) + ' 0 0 1 ' + f(r * 0.5) + ' ' + f(-r * 0.9) +
        'a' + f(r * 0.7) + ' ' + f(r * 0.7) + ' 0 0 1 ' + f(r * 1.2) + ' ' + f(r * 0.1) +
        'a' + f(r * 0.55) + ' ' + f(r * 0.55) + ' 0 0 1 ' + f(r * 0.3) + ' ' + f(r * 0.95) + 'Z';
      s += C.path(d, i ? '#e2dccf' : '#d3ccbd', 0.9, 0.92) + C.line('M' + f(cx - r * 0.3) + ' ' + f(cy) + 'q' + f(r * 0.4) + ' ' + f(-r * 0.4) + ' ' + f(r * 0.8) + ' 0', 0.7, 0.45);
      ctx.top(cy - r * 0.75);
    }
    return s;
  }
  /** 石烟囱：中心 cx，底 yb，宽 w、高 h；opt.cap 'copper'(铜顶罩) | 'ring'(铜箍) | 'plain'；opt.fire 顶口熔火；opt.smoke 烟团数 */
  function chimney(ctx, cx, yb, w, h, opt) {
    opt = opt || {};
    var x0 = cx - w / 2, x1 = cx + w / 2, yt = yb - h, s = '';
    s += C.blocks(ctx, x0, x1, yb, h, { course: 6, minW: w * 0.4, maxW: w * 0.7 });
    if (opt.cap === 'copper') {
      s += C.rect(x0 - 2, yt - 3, w + 4, 3, P.copper, 1.1) + C.path(C.poly([[x0 - 1, yt - 3], [cx, yt - 8], [x1 + 1, yt - 3]]), P.verd, 1.1);
      s += C.rect(x0, yt - 2.4, w, 1.2, P.soot, 0);
      ctx.top(yt - 8);
    } else {
      s += C.rect(x0 - 1.8, yt - 3.4, w + 3.6, 3.4, P.granite3, 1.2) + C.rect(x0 + 1, yt - 4.6, w - 2, 1.4, opt.fire ? P.fire : P.soot, 0.7);
      if (opt.cap === 'ring') s += C.rect(x0 - 0.6, yb - h * 0.55, w + 1.2, 2.4, P.copper, 0.9) + C.rivets(x0 + 1.5, x1 - 1.5, yb - h * 0.55 + 1.2, 3, 0.5);
      ctx.top(yt - 5);
    }
    if (opt.smoke) s += smoke(ctx, cx - 2, yt - (opt.cap === 'copper' ? 7 : 4), opt.smoke, opt.smokeScale);
    return s;
  }
  /** 齿轮：圆心 cx,cy，半径 r，齿数 n；铜色平涂，轮毂铁色，辐条 */
  function gear(ctx, cx, cy, r, n, opt) {
    opt = opt || {};
    var pts = [], i, rt = r + Math.max(1.6, r * 0.22), rot = opt.rot || 0;
    for (i = 0; i < n * 4; i++) {
      var a = rot + Math.PI * 2 * i / (n * 4), rr = (i % 4 === 1 || i % 4 === 2) ? rt : r;
      pts.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr]);
    }
    var s = C.path(C.poly(pts), opt.fill || P.copper, 1.1), sp = '';
    s += C.circle(cx, cy, r * 0.72, opt.inner || P.copper2, 0.8);
    for (i = 0; i < 4; i++) {
      var b = rot + Math.PI * i / 2 + 0.4;
      sp += 'M' + f(cx) + ' ' + f(cy) + 'L' + f(cx + Math.cos(b) * r * 0.7) + ' ' + f(cy + Math.sin(b) * r * 0.7);
    }
    s += C.line(sp, Math.max(1, r * 0.18), 1, opt.fill || P.copper) + C.line(sp, 0.6, 0.6);
    s += C.circle(cx, cy, Math.max(1.2, r * 0.25), P.iron, 0.8);
    ctx.top(cy - rt);
    return s;
  }
  /** 矿车轨道（地面，横向）：x0..x1，轨道中线 y；枕木间距 6 */
  function rails(x0, x1, y) {
    var s = '', d = '';
    for (var x = x0 + 2; x < x1 - 1; x += 6) s += C.rect(x, y - 3.4, 3, 6.8, P.timber, 0.7);
    d += 'M' + f(x0) + ' ' + f(y - 2) + 'H' + f(x1) + 'M' + f(x0) + ' ' + f(y + 2) + 'H' + f(x1);
    return s + C.line(d, 1.3, 1, P.iron);
  }
  /** 矿车：x 左，yb 车轮底，w 宽；装矿石块（ore 色） */
  function cart(ctx, x, yb, w, ore) {
    var h = w * 0.55, y = yb - 3 - h, s = '';
    var lump = '';
    for (var i = 0; i < 4; i++) {
      var lx = x + 2 + i * (w - 4) / 4 + ctx.rnd(-0.5, 0.5);
      lump += C.path(C.poly([[lx, y + 1], [lx + 1, y - 2.6], [lx + 3.4, y - 3.2], [lx + 4.6, y + 1]]), ore || (i % 2 ? P.deep : P.granite), 0.7);
    }
    s += lump;
    s += C.path(C.poly([[x, y], [x + w, y], [x + w - 2, yb - 3], [x + 2, yb - 3]]), P.iron, 1.2);
    s += C.rect(x + 0.5, y + h * 0.35, w - 1, 1.6, P.copper, 0) + C.rivets(x + 2.5, x + w - 2.5, y + 1.5, 3.4, 0.5);
    s += C.circle(x + 4, yb - 2.2, 2.2, P.soot, 0.8) + C.circle(x + w - 4, yb - 2.2, 2.2, P.soot, 0.8);
    ctx.top(y - 3.2);
    return s;
  }
  /** 粗壮石柱：cx 中心，yb 底，宽 w、高 h；方柱 + 大柱础 + 柱头托块；opt.rune 柱身刻一道符文；opt.band 铜箍 */
  function pillar(ctx, cx, yb, w, h, opt) {
    opt = opt || {};
    var x0 = cx - w / 2, x1 = cx + w / 2, yt = yb - h, s = '';
    s += C.rect(x0 - 3, yb - 5, w + 6, 5, P.granite2, 1.3);
    s += C.face(ctx, C.rectD(x0, yt + 5, w, h - 10), P.granite3,
      C.rect(x1 - w * 0.3, yt + 5, w * 0.3, h - 10, P.shadow, 0, 0.18) +
      C.line('M' + f(x0) + ' ' + f(yb - h * 0.4) + 'H' + f(x1) + 'M' + f(x0) + ' ' + f(yb - h * 0.72) + 'H' + f(x1), 0.8, 0.55), 1.4);
    if (opt.rune) {
      var ry = yb - h * 0.56, d = 'M' + f(cx) + ' ' + f(ry - 4) + 'v8M' + f(cx - 2.2) + ' ' + f(ry - 3) + 'l2.2 2.2l2.2 -2.2';
      s += C.line(d, 0.9, 0.85);
    }
    if (opt.band) s += C.rect(x0 - 0.6, yb - h * 0.3, w + 1.2, 2.4, P.copper, 0.9);
    s += C.rect(x0 - 3, yt, w + 6, 5, P.granite2, 1.3) + C.rect(x0 - 1.5, yt + 5, w + 3, 2, P.granite, 0.9);
    ctx.top(yt);
    return s;
  }
  /**
   * 低坡石板顶（屋脊平行正面）：x0..x1，前檐 yE，地面进深 dg，抬升 rise，挑檐 ov。
   * 前坡受光（石板行水平排线），后坡露出一窄条；屋脊压一排脊石。opt.fill 覆盖前坡色。返回 { svg, yR }
   */
  function slabRoof(ctx, x0, x1, yE, dg, rise, opt) {
    opt = opt || {};
    var ov = opt.ov == null ? 3 : opt.ov, a = x0 - ov, b = x1 + ov, yB = yE - dg, yR = yE - dg / 2 - rise, s = '', d = '';
    if (yB < yR - 0.5) s += C.face(ctx, C.poly([[a + 2, yB], [b - 2, yB], [b, yR], [a, yR]]), P.deep, '', 1.5);
    var front = C.poly([[a, yR], [b, yR], [b, yE + 2], [a, yE + 2]]), k = 0;
    for (var y = yE + 2 - 6; y > yR + 1; y -= 6, k++) {
      d += 'M' + f(a) + ' ' + f(y) + 'H' + f(b);
      for (var x = a + 4 + (k % 2) * 6; x < b - 2; x += 12) d += 'M' + f(x) + ' ' + f(y) + 'v6';
    }
    var tex = C.line(d, 0.8, 0.55) + C.rect(b - 5, yR, 5, yE + 2 - yR, P.shadow, 0, 0.16) + C.rect(a, yE - 0.5, b - a, 2.5, P.shadow, 0, 0.2);
    s += C.face(ctx, front, opt.fill || P.slate, tex, 1.7);
    s += C.rect(a - 1, yR - 3, b - a + 2, 3.6, P.granite2, 1.3);
    if (opt.rivet) s += C.rivets(a + 3, b - 3, yR - 1.2, 6, 0.6);
    ctx.top(Math.min(yB, yR - 3));
    return { svg: s, yR: yR - 3 };
  }
  /**
   * 石穹顶：底边 x0..x1、底线 yb，高 h（扁半椭圆）。石层弧线 + 竖肋；opt.cap 'copper' 顶上铜宝珠 / 'vent' 烟口。
   */
  function dome(ctx, x0, x1, yb, h, opt) {
    opt = opt || {};
    var cx = (x0 + x1) / 2, rx = (x1 - x0) / 2, D = 'M' + f(x0) + ' ' + f(yb) + 'A' + f(rx) + ' ' + f(h) + ' 0 0 1 ' + f(x1) + ' ' + f(yb) + 'Z';
    var t = '', i;
    for (i = 1; i < 4; i++) {
      var k = i / 4;
      t += 'M' + f(cx - rx) + ' ' + f(yb - h * k) + 'Q' + f(cx) + ' ' + f(yb - h * k - h * 0.18) + ' ' + f(cx + rx) + ' ' + f(yb - h * k);
    }
    for (i = -2; i <= 2; i++) t += 'M' + f(cx + i * rx * 0.42) + ' ' + f(yb) + 'Q' + f(cx + i * rx * 0.3) + ' ' + f(yb - h * 0.7) + ' ' + f(cx) + ' ' + f(yb - h);
    var tex = C.line(t, 0.8, 0.5) + C.path('M' + f(cx + rx * 0.25) + ' ' + f(yb) + 'A' + f(rx * 0.75) + ' ' + f(h) + ' 0 0 0 ' + f(cx) + ' ' + f(yb - h) +
      'A' + f(rx) + ' ' + f(h) + ' 0 0 1 ' + f(x1) + ' ' + f(yb) + 'Z', P.shadow, 0, 0.17);
    var s = C.face(ctx, D, opt.fill || P.granite3, tex, 1.7);
    s += C.rect(x0 - 2, yb - 2, x1 - x0 + 4, 3.6, P.granite2, 1.2);
    if (opt.cap === 'copper') {
      s += C.rect(cx - 3, yb - h - 3, 6, 3.4, P.copper, 1) + C.circle(cx, yb - h - 6, 3, P.verd, 1);
      ctx.top(yb - h - 9);
    } else if (opt.cap === 'vent') {
      s += C.rect(cx - 4, yb - h - 5, 8, 6, P.granite2, 1.2) + C.rect(cx - 2.6, yb - h - 6, 5.2, 1.5, P.soot, 0.6);
      ctx.top(yb - h - 6);
    } else ctx.top(yb - h);
    return s;
  }
  var API = { smoke: smoke, chimney: chimney, gear: gear, rails: rails, cart: cart, pillar: pillar, slabRoof: slabRoof, dome: dome };
  root.TownArtWD_parts = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
