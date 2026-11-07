/*
 * 织梦 · 阿拉伯风格部件 2：小窗、木格窗（mashrabiya）、几何纹瓷砖带、穹顶、椰枣树、布棚、风塔（barjeel）（美术样板，尚未接入游戏）
 * 浏览器挂 window.TownArtAB_parts2；Node 用 module.exports。依赖 core.js、parts.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtAB_core;
  var Q = isNode ? require('./parts.js') : root.TownArtAB_parts;
  var P = C.PAL, f = C.f;

  /** 小窗：kind = slit / square / pointed / round */
  function win(x, yb, w, h, kind) {
    if (kind === 'pointed') return C.path(Q.pointedD(x, yb, w, h - w * 0.6, w * 0.6), P.hole, 1);
    if (kind === 'round') return C.path('M' + f(x) + ' ' + f(yb) + 'V' + f(yb - h + w / 2) + 'A' + f(w / 2) + ' ' + f(w / 2) + ' 0 0 1 ' + f(x + w) + ' ' + f(yb - h + w / 2) + 'V' + f(yb) + 'Z', P.hole, 1);
    return C.rect(x, yb - h, w, h, P.hole, 1) + (kind === 'square' ? C.rect(x - 1, yb, w + 2, 1.4, P.lime2, 0.7) : '');
  }
  /** 木格窗：外挑木箱，正面细密方格，顶有小檐 */
  function mashrabiya(ctx, x, yb, w, h, col) {
    col = col || P.wood;
    var s = C.rect(x - 1, yb, w + 2, 2.4, P.wood2, 0.9) + C.rect(x, yb - h, w, h, col, 1.3), g = '';
    for (var gx = x + 2.2; gx < x + w - 1; gx += 2.4) g += 'M' + f(gx) + ' ' + f(yb - h + 1.5) + 'V' + f(yb - 1);
    for (var gy = yb - h + 2.5; gy < yb - 1; gy += 2.4) g += 'M' + f(x + 1) + ' ' + f(gy) + 'H' + f(x + w - 1);
    s += C.line(g, 0.6, 0.75, P.wood2);
    s += C.path('M' + f(x - 1.8) + ' ' + f(yb - h) + 'h' + f(w + 3.6) + 'l-1.6 -2.4h' + f(-(w + 0.4)) + 'Z', P.wood2, 1);
    return s;
  }
  /** 几何纹瓷砖带：x0..x1，中线 y，高 h；pat = star / zig / chev；底 bg */
  function tileBand(ctx, x0, x1, y, h, pat, bg, fg) {
    bg = bg || P.cob; fg = fg || P.turq2;
    var s = C.rect(x0, y - h / 2, x1 - x0, h, bg, 0.9), d = '', u = h, x;
    if (pat === 'zig') {
      d = 'M' + f(x0) + ' ' + f(y + h * 0.25);
      for (x = x0; x < x1 - 0.1; x += u / 2) d += 'L' + f(Math.min(x1, x + u / 4)) + ' ' + f(y - h * 0.25) + 'L' + f(Math.min(x1, x + u / 2)) + ' ' + f(y + h * 0.25);
      return s + C.line(d, 0.9, 1, fg);
    }
    for (x = x0 + u / 2; x < x1 - u / 3; x += u) {
      var r = h * 0.34;
      if (pat === 'chev') d += 'M' + f(x - r) + ' ' + f(y + r * 0.6) + 'L' + f(x) + ' ' + f(y - r * 0.6) + 'L' + f(x + r) + ' ' + f(y + r * 0.6);
      else d += 'M' + f(x) + ' ' + f(y - r) + 'L' + f(x + r) + ' ' + f(y) + 'L' + f(x) + ' ' + f(y + r) + 'L' + f(x - r) + ' ' + f(y) + 'Z';
    }
    return s + (pat === 'chev' ? C.line(d, 0.9, 1, fg) : C.path(d, fg, 0) + C.line(d, 0.5, 0.8, P.lime));
  }
  /** 穹顶：底宽 w 中心 cx，鼓座底 yb，鼓座高 dh，穹高 ht；col 穹面色；finial 金尖 */
  function dome(ctx, cx, yb, w, dh, ht, o) {
    o = o || {};
    var r = w / 2, col = o.col || P.lime, s = '';
    if (dh > 0) s += C.rect(cx - r - 1, yb - dh, w + 2, dh, o.drum || P.lime2, 1.3) + (o.band ? tileBand(ctx, cx - r - 1, cx + r + 1, yb - dh / 2, Math.min(dh - 1, 4), 'star') : '');
    var y0 = yb - dh, k = o.onion ? 1.1 : 1;
    var d = 'M' + f(cx - r) + ' ' + f(y0) + 'C' + f(cx - r * k) + ' ' + f(y0 - ht * 0.62) + ' ' + f(cx - r * 0.35) + ' ' + f(y0 - ht * 0.9) + ' ' + f(cx) + ' ' + f(y0 - ht) +
      'C' + f(cx + r * 0.35) + ' ' + f(y0 - ht * 0.9) + ' ' + f(cx + r * k) + ' ' + f(y0 - ht * 0.62) + ' ' + f(cx + r) + ' ' + f(y0) + 'Z';
    s += C.path(d, col, 1.6);
    // 阴面：右侧一片平涂（光从左上来）
    s += C.clipped(ctx, d, C.path('M' + f(cx + r * 0.25) + ' ' + f(y0 - ht - 2) + 'C' + f(cx + r * 0.7) + ' ' + f(y0 - ht * 0.6) + ' ' + f(cx + r * 0.6) + ' ' + f(y0 - ht * 0.2) + ' ' + f(cx + r * 0.5) + ' ' + f(y0 + 1) + 'H' + f(cx + r + 2) + 'V' + f(y0 - ht - 2) + 'Z', o.shade || P.lime2, 0));
    if (o.ribs) {
      var rb = '';
      for (var i = 1; i < o.ribs; i++) { var t = -1 + 2 * i / o.ribs; rb += 'M' + f(cx + t * r * 0.95) + ' ' + f(y0) + 'Q' + f(cx + t * r * 0.7) + ' ' + f(y0 - ht * 0.75) + ' ' + f(cx) + ' ' + f(y0 - ht); }
      s += C.line(rb, 0.7, 0.5);
    }
    s += C.path(d, 'none', 1.6);
    var top = y0 - ht;
    if (o.finial !== false) { s += C.line('M' + f(cx) + ' ' + f(top) + 'v-6', 1.1, 1, P.gold) + C.ell(cx, top - 3, 1.4, 1.4, P.gold, 0.6); top -= 7; if (o.crescent) { s += C.path('M' + f(cx - 2) + ' ' + f(top - 1) + 'a2.4 2.4 0 1 0 4 0a1.8 1.8 0 1 1 -4 0Z', P.gold, 0.5); top -= 4; } }
    ctx.top(top);
    return s;
  }
  /** 椰枣树：根部 (x, yb)，高 h，lean 弯曲；dates 是否挂果 */
  function palm(ctx, x, yb, h, lean, o) {
    o = o || {};
    var tx = x + lean, ty = yb - h, s = '';
    s += C.ell(x + 4, yb + 1, 6, 2, P.ink, 0, 0.18);
    var trunk = 'M' + f(x - 1.8) + ' ' + f(yb) + 'Q' + f(x + lean * 0.2 - 1.4) + ' ' + f(yb - h * 0.55) + ' ' + f(tx - 1) + ' ' + f(ty) + 'L' + f(tx + 1) + ' ' + f(ty) + 'Q' + f(x + lean * 0.2 + 1.6) + ' ' + f(yb - h * 0.55) + ' ' + f(x + 1.8) + ' ' + f(yb) + 'Z';
    s += C.path(trunk, P.wood2, 1.1);
    var rings = '';
    for (var i = 1; i < 8; i++) { var t = i / 8, yy = yb - h * t, xx = x + lean * t * t * 0.9; rings += 'M' + f(xx - 1.6) + ' ' + f(yy + 0.6) + 'l3.2 -1.2'; }
    s += C.line(rings, 0.6, 0.6);
    var n = o.fronds || 8, fr = '', fr2 = '';
    for (i = 0; i < n; i++) {
      var a = Math.PI * (1.05 + i * 0.9 / (n - 1)) + ctx.rnd(-0.08, 0.08), L = ctx.rnd(9, 13) * (o.sc || 1);
      var ex = tx + Math.cos(a) * L * 1.2, ey = ty + Math.sin(a) * L * 0.75 + L * 0.55, mx = tx + Math.cos(a) * L * 0.6, my = ty + Math.sin(a) * L * 0.6 - 1.5;
      var d = 'M' + f(tx) + ' ' + f(ty) + 'Q' + f(mx - 1.6) + ' ' + f(my - 2) + ' ' + f(ex) + ' ' + f(ey) + 'Q' + f(mx + 1.2) + ' ' + f(my + 1.6) + ' ' + f(tx) + ' ' + f(ty) + 'Z';
      if (i % 2) fr += C.path(d, P.palm, 0.8); else fr2 += C.path(d, P.palm2, 0.8);
      ctx.top(Math.min(ey, my - 2));
    }
    s += fr + fr2;
    if (o.dates) s += C.ell(tx - 1.5, ty + 2.5, 1.6, 2.2, P.ochre2, 0.6) + C.ell(tx + 2, ty + 2.8, 1.5, 2, P.ochre, 0.6);
    ctx.top(ty - 6);
    return s;
  }
  /** 布棚：x0..x1，挂在 y 处，前伸 dp，col 主色，stripe 条纹色；poles 前沿立杆落地 yb */
  function awning(ctx, x0, x1, y, dp, col, stripe, yb) {
    var s = '';
    if (yb != null) s += C.line('M' + f(x0 + 1) + ' ' + f(y + dp) + 'V' + f(yb) + 'M' + f(x1 - 1) + ' ' + f(y + dp) + 'V' + f(yb), 1.2, 1, P.wood);
    s += C.path('M' + f(x0) + ' ' + f(y) + 'H' + f(x1) + 'L' + f(x1 + 1) + ' ' + f(y + dp) + 'H' + f(x0 - 1) + 'Z', col, 1.2);
    var st = '';
    for (var x = x0 + 3; x < x1 - 1; x += 6) st += C.path('M' + f(x) + ' ' + f(y) + 'h2.6l0.4 ' + f(dp) + 'h-3.4Z', stripe, 0);
    s += st;
    var sc = 'M' + f(x0 - 1) + ' ' + f(y + dp);
    for (x = x0 - 1; x < x1 + 0.5; x += 4) sc += 'q2 2.6 4 0';
    s += C.path(sc + 'V' + f(y + dp) + 'Z', col, 1);
    return s;
  }
  /** 风塔（barjeel）：方塔 cx 中心，底 yb，宽 w，高 h；四面开竖向通风槽，顶部十字木撑 */
  function windTower(ctx, cx, yb, w, h, o) {
    o = o || {};
    var x0 = cx - w / 2, s = Q.facade(ctx, x0, x0 + w, yb, h, o.mat || 'mud', { noPlinth: true });
    var top = yb - h, sl = '', n = Math.max(2, Math.floor(w / 4.2));
    for (var i = 0; i < n; i++) { var x = x0 + 2 + i * (w - 4) / n; sl += C.rect(x + 0.5, top + 3, (w - 4) / n - 1.2, h * 0.42, P.hole, 0.6); }
    s += sl + C.rect(x0 - 1, top + 3 + h * 0.42, w + 2, 1.8, P.lime2, 0.8);
    // 顶面与伸出的木撑
    s += C.rect(x0 - 1, top - 4, w + 2, 4, o.cap || P.lime2, 1.2);
    s += C.line('M' + f(x0 - 3) + ' ' + f(top + 1.5) + 'h' + f(w + 6) + 'M' + f(x0 - 3) + ' ' + f(top + 7) + 'h' + f(w + 6), 1.1, 1, P.wood);
    ctx.top(top - 5);
    return s;
  }
  var API = { win: win, mashrabiya: mashrabiya, tileBand: tileBand, dome: dome, palm: palm, awning: awning, windTower: windTower };
  root.TownArtAB_parts2 = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
