/*
 * 织梦 · 阿拉伯风格部件：体块、平顶女儿墙、阶梯雉堞、尖拱 / 马蹄拱、木格窗、瓷砖带、穹顶、椰枣树、布棚（美术样板，尚未接入游戏）
 * 局部坐标：y = 0 为占地前沿，向上为负；体块顶面 = 地面矩形整体上移 h（3/4 斜俯视，侧面不露）。
 * 浏览器挂 window.TownArtAB_parts；Node 用 module.exports。依赖 core.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtAB_core;
  var P = C.PAL, f = C.f;

  /** 墙面纹理：土坯抹灰的稀疏裂纹与斑点（种子随机） */
  function plaster(ctx, x0, x1, y0, y1, dens, col) {
    var s = '', n = Math.round((x1 - x0) * (y1 - y0) / 260 * (dens == null ? 1 : dens));
    for (var i = 0; i < n; i++) {
      var x = ctx.rnd(x0 + 2, x1 - 4), y = ctx.rnd(y0 + 2, y1 - 2);
      if (ctx.r() < 0.55) s += 'M' + f(x) + ' ' + f(y) + 'h' + f(ctx.rnd(1.5, 3.5));
      else s += 'M' + f(x) + ' ' + f(y) + 'l' + f(ctx.rnd(-1, 1)) + ' ' + f(ctx.rnd(1.5, 3)) + 'l' + f(ctx.rnd(0.5, 1.5)) + ' 1.2';
    }
    return C.line(s, 0.7, 0.4, col);
  }
  /** 立面：x0..x1，底 yb，高 h；mat = mud / lime / stone */
  function facade(ctx, x0, x1, yb, h, mat, o) {
    o = o || {};
    var fill = mat === 'lime' ? P.lime : mat === 'stone' ? P.stone : (o.fill || P.mud);
    var s = C.rect(x0, yb - h, x1 - x0, h, fill, 0);
    if (mat === 'stone') {
      var d = '';
      for (var y = yb - 7; y > yb - h + 2; y -= 7) d += 'M' + f(x0) + ' ' + f(y) + 'H' + f(x1);
      s += C.line(d, 0.6, 0.35);
    } else s += plaster(ctx, x0, x1, yb - h, yb, mat === 'lime' ? 0.45 : 1);
    // 勒脚
    if (!o.noPlinth) s += C.rect(x0, yb - 3.5, x1 - x0, 3.5, mat === 'lime' ? P.lime2 : P.mud2, 0) + C.line('M' + f(x0) + ' ' + f(yb - 3.5) + 'H' + f(x1), 0.7, 0.5);
    return s + C.rect(x0, yb - h, x1 - x0, h, 'none', 1.7);
  }
  /** 平顶屋面（可上人）+ 女儿墙：前沿 yt，进深 dp；p = 前女儿墙高；step = 是否阶梯雉堞 */
  function flatRoof(ctx, x0, x1, yt, dp, o) {
    o = o || {};
    var p = o.p == null ? 4 : o.p, roof = o.roof || P.sand, wall = o.wall || P.mud, wt = 2.6;
    var s = C.rect(x0, yt - dp, x1 - x0, dp, roof, 1.4);
    // 屋面排水与踩痕
    s += C.line('M' + f(x0 + 5) + ' ' + f(yt - dp * 0.55) + 'h' + f((x1 - x0) * 0.3) + 'M' + f(x1 - (x1 - x0) * 0.45) + ' ' + f(yt - dp * 0.3) + 'h' + f((x1 - x0) * 0.25), 0.7, 0.35);
    if (p > 0) {
      // 后、左、右女儿墙顶（窄带）
      s += C.rect(x0, yt - dp - p, x1 - x0, p, wall, 1) + C.rect(x0, yt - dp, wt, dp, P.lime2, 0.9) + C.rect(x1 - wt, yt - dp, wt, dp, P.mud3, 0.9);
      s += C.rect(x0, yt - dp - p - 1.6, x1 - x0, 2.2, P.lime2, 0.9);
      // 前女儿墙立面
      s += C.rect(x0, yt - p, x1 - x0, p, wall, 1.3) + C.rect(x0 - 0.6, yt - p - 1.6, x1 - x0 + 1.2, 2.2, P.lime2, 1);
      ctx.top(yt - dp - p - 2);
    } else ctx.top(yt - dp);
    if (o.step) s += merlons(x0, x1, yt - p - 1.6, o.step === true ? 6 : o.step, o.mcol || wall) + merlons(x0, x1, yt - dp - p - 1.6, o.step === true ? 6 : o.step, o.mcol || wall, 0.8);
    if (o.spouts) s += spout(x0 + 4, yt - p + 2) + spout(x1 - 7, yt - p + 2);
    return s;
  }
  /** 木质排水口 */
  function spout(x, y) { return C.rect(x, y - 1, 3, 2.2, P.wood, 0.7); }
  /** 阶梯雉堞：一排两级台阶形的垛 */
  function merlons(x0, x1, y, w, col, sc) {
    sc = sc || 1;
    var s = '', h = 5 * sc, n = Math.max(1, Math.floor((x1 - x0) / (w * 1.5))), gap = ((x1 - x0) - n * w) / n;
    for (var i = 0; i < n; i++) {
      var x = x0 + gap / 2 + i * (w + gap), q = w / 4;
      s += C.path('M' + f(x) + ' ' + f(y) + 'v' + f(-h * 0.5) + 'h' + f(q) + 'v' + f(-h * 0.5) + 'h' + f(w - 2 * q) + 'v' + f(h * 0.5) + 'h' + f(q) + 'v' + f(h * 0.5) + 'Z', col, 0.9);
    }
    return s;
  }
  /** 尖拱轮廓（开口 w，起拱点高 hs，尖顶高 ha 以上） */
  function pointedD(x, yb, w, hs, ha) {
    var ys = yb - hs, k = ha == null ? w * 0.62 : ha;
    return 'M' + f(x) + ' ' + f(yb) + 'V' + f(ys) + 'Q' + f(x) + ' ' + f(ys - k * 0.78) + ' ' + f(x + w / 2) + ' ' + f(ys - k) +
      'Q' + f(x + w) + ' ' + f(ys - k * 0.78) + ' ' + f(x + w) + ' ' + f(ys) + 'V' + f(yb) + 'Z';
  }
  /** 马蹄拱轮廓：弧半径略大于半宽、大弧 */
  function horseshoeD(x, yb, w, hs) {
    var r = w * 0.58, ys = yb - hs;
    return 'M' + f(x) + ' ' + f(yb) + 'V' + f(ys) + 'A' + f(r) + ' ' + f(r) + ' 0 1 1 ' + f(x + w) + ' ' + f(ys) + 'V' + f(yb) + 'Z';
  }
  /** 门：kind = pointed / horseshoe；col 门板色；studs 门钉；frame 拱框色 */
  function door(ctx, x, yb, w, h, o) {
    o = o || {};
    var hs = h - w * 0.62, d = o.kind === 'horseshoe' ? horseshoeD(x, yb, w, h - w * 0.75) : pointedD(x, yb, w, hs);
    var s = '';
    if (o.frame) {
      var fr = o.kind === 'horseshoe' ? horseshoeD(x - 2.2, yb, w + 4.4, h - w * 0.75) : pointedD(x - 2.2, yb, w + 4.4, hs, (w + 4.4) * 0.64);
      s += C.path(fr, o.frame, 1.1);
    }
    s += C.path(d, o.col || P.wood, 1.3);
    if (o.open) s += C.path(d, P.dark, 0, null, 0.85);
    else {
      s += C.line('M' + f(x + w / 2) + ' ' + f(yb) + 'V' + f(yb - hs - 1), 0.8, 0.7);
      if (o.studs) {
        var st = '';
        for (var yy = yb - 3; yy > yb - hs + 1; yy -= 3.5) st += 'M' + f(x + w * 0.25) + ' ' + f(yy) + 'h0.01M' + f(x + w * 0.75) + ' ' + f(yy) + 'h0.01';
        s += C.line(st, 1.3, 0.9, P.gold);
      }
    }
    return s;
  }
  /** 平顶体块：地面 x0..x1、前沿 yf、进深 dp、墙高 h；o.mat 墙料，o.roof 传给 flatRoof */
  function box(ctx, x0, x1, yf, dp, h, o) {
    o = o || {};
    return facade(ctx, x0, x1, yf, h, o.mat || 'mud', o) + flatRoof(ctx, x0, x1, yf - h, dp, o.roof || {});
  }
  var API = { plaster: plaster, facade: facade, flatRoof: flatRoof, merlons: merlons, pointedD: pointedD, horseshoeD: horseshoeD, door: door, spout: spout, box: box };
  root.TownArtAB_parts = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
