/*
 * 织梦 · 西式防御工事（west-fort）—— 通用棱柱墙体：任意多边形地面轮廓 → 正面方石立面 + 墙顶走道 + 垛口
 * 局部坐标：y = 0 为占地前沿，向上为负；地面点 (x, y) 在高 h 处画到 (x, y - h)。
 * 画序（同一高度的棱柱）：立面 → 墙顶 → 垛口；可证同屏重叠时总是后画者在前。
 * 浏览器挂 window.TownArtWF.geom；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWF.core;
  var PAL = C.PAL, f = C.f;
  var TONES_A = [PAL.stone, '#c7b897', PAL.stone2, '#d4c6a8'];   // 朝南 / 朝西南（受光）
  var TONES_B = [PAL.stone2, '#b9aa8c', PAL.stone3, '#c3b496'];  // 朝东南（背光）
  function area(a) {
    var s = 0;
    for (var i = 0; i < a.length; i++) { var p = a[i], q = a[(i + 1) % a.length]; s += p[0] * q[1] - q[0] * p[1]; }
    return s / 2;
  }
  function lift(a, h) { return a.map(function (p) { return [p[0], p[1] - h]; }); }
  function add(p, v, k) { return [p[0] + v[0] * k, p[1] + v[1] * k]; }
  /** 每条边：a、b、外法线 n（y 向下的坐标里）、单位方向 d、长度 */
  function edges(poly) {
    var sg = area(poly) > 0 ? 1 : -1, out = [];
    for (var i = 0; i < poly.length; i++) {
      var a = poly[i], b = poly[(i + 1) % poly.length], dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1;
      out.push({ i: i, a: a, b: b, d: [dx / L, dy / L], n: [sg * dy / L, -sg * dx / L], L: L, my: (a[1] + b[1]) / 2 });
    }
    return out;
  }
  function clip(ctx, shape, inner) {
    var id = ctx.uid();
    return '<clipPath id="' + id + '"><path d="' + C.pts(shape) + '"/></clipPath><g clip-path="url(#' + id + ')">' + inner + '</g>';
  }
  /** 一面方石立面：地面边 a→b（不能是竖直边），高 h。层高 8；块长按 x 周期对齐世界坐标 */
  function stoneFace(ctx, a, b, h, o) {
    o = o || {};
    var eA = o.endA, eB = o.endB;
    if (a[0] > b[0]) { var t = a; a = b; b = t; eA = o.endB; eB = o.endA; }
    var k = (b[1] - a[1]) / (b[0] - a[0]);
    function yb(x) { return a[1] + k * (x - a[0]); }
    var per = o.per || (Math.abs(k) > 0.3 ? 12 : 16), tones = o.dark ? TONES_B : TONES_A;
    var quad = [a, b, [b[0], b[1] - h], [a[0], a[1] - h]], blocks = '', d = '', r = 0;
    for (var z = 0; z < h - 0.1; z += 8, r++) {
      var z1 = Math.min(h, z + 8), off = (r % 2) * per / 2;
      for (var j = Math.floor((a[0] - off) / per); off + j * per < b[0]; j++) {
        var x0 = off + j * per, x1 = x0 + per;
        blocks += C.poly([[x0, yb(x0) - z], [x1, yb(x1) - z], [x1, yb(x1) - z1], [x0, yb(x0) - z1]], tones[(((j % 3) + 3) % 3 + r) % 4], 0);
        if (x0 > a[0] + 0.5) d += C.seg([x0, yb(x0) - z], [x0, yb(x0) - z1]);
      }
      if (z1 < h - 0.1) d += C.seg([a[0], a[1] - z1], [b[0], b[1] - z1]);
    }
    var s = blocks + C.lines(d, 0.8, 0.55);
    s += C.poly([a, b, [b[0], b[1] - 5], [a[0], a[1] - 5]], PAL.stone3, 0) + C.lines(C.seg([a[0], a[1] - 5], [b[0], b[1] - 5]), 0.9, 0.7);
    s += '<path d="' + C.pts([[a[0], a[1] - h], [b[0], b[1] - h], [b[0], b[1] - h + 2.5], [a[0], a[1] - h + 2.5]]) + '" fill="' + PAL.shadow + '" fill-opacity="0.14"/>';
    var ol = C.seg(a, b);
    if (eA) ol += C.seg(a, [a[0], a[1] - h]);
    if (eB) ol += C.seg(b, [b[0], b[1] - h]);
    return clip(ctx, quad, s) + C.path(ol, 'none', 1.6);
  }
  // —— 后续：walkTop / parapet / prism 追加在下面 ——
  /** 墙顶走道：平涂 + 世界坐标对齐的石板缝（mode: 'ortho' 横竖；'se' / 'ne' 沿斜向） */
  function walkTop(ctx, top, mode, fill) {
    var b = bbox(top), d = '', v;
    if (mode === 'diag') {  // 两族斜缝 x + y = c 与 x - y = c，c 取 12 的倍数（随 48 格平移不变）
      var lo = Math.floor((b[0] + b[1]) / 12) * 12, hi = b[2] + b[3], lo2 = Math.floor((b[0] - b[3]) / 12) * 12, hi2 = b[2] - b[1];
      for (v = lo; v <= hi; v += 12) d += C.seg([v - b[1], b[1]], [v - b[3], b[3]]);
      for (v = lo2; v <= hi2; v += 12) d += C.seg([v + b[1], b[1]], [v + b[3], b[3]]);
    } else {
      for (v = Math.floor(b[0] / 12) * 12 + 6; v < b[2]; v += 12) d += 'M' + f(v) + ' ' + f(b[1]) + 'V' + f(b[3]);
    }
    for (v = Math.floor(b[1] / 12) * 12 + 6; v < b[3]; v += 12) if (mode === 'ortho' || !mode) d += 'M' + f(b[0]) + ' ' + f(v) + 'H' + f(b[2]);
    return C.poly(top, fill || PAL.walk, 0) + clip(ctx, top, C.lines(d, 0.6, 0.3));
  }
  function bbox(a) {
    var b = [1e9, 1e9, -1e9, -1e9];
    a.forEach(function (p) { b[0] = Math.min(b[0], p[0]); b[1] = Math.min(b[1], p[1]); b[2] = Math.max(b[2], p[0]); b[3] = Math.max(b[3], p[1]); });
    return b;
  }
  /** 小棱柱（垛口、胸墙）：地面四边形 q，底高 z0、顶高 z1 */
  function block(q, z0, z1, fill) {
    var s = '', E = edges(q);
    E.forEach(function (e) {
      if (e.n[1] < 0.05) return;
      s += C.poly([[e.a[0], e.a[1] - z0], [e.b[0], e.b[1] - z0], [e.b[0], e.b[1] - z1], [e.a[0], e.a[1] - z1]], e.n[0] > 0.35 ? PAL.stone3 : (fill || PAL.stone), 0.8);
    });
    return s + C.poly(lift(q, z1), e2top(fill), 0.8);
  }
  function e2top(fill) { return fill === PAL.stone2 ? PAL.stone : '#d8cbae'; }
  /** 沿一条墙边放胸墙 + 垛口：内法线方向退 3 px；垛口按世界 x（或竖边的 y）周期对齐 */
  function parapet(e, h, list) {
    var inw = [-e.n[0], -e.n[1]], vertical = Math.abs(e.d[0]) < 0.2, per = vertical ? 12 : (Math.abs(e.d[1]) > 0.2 ? 8 : 12);
    var a = e.a, b = e.b, ax = vertical ? 1 : 0, lo = Math.min(a[ax], b[ax]), hi = Math.max(a[ax], b[ax]);
    function at(u) { var t = (u - a[ax]) / (b[ax] - a[ax]); return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]; }
    list.push({ y: (a[1] + b[1]) / 2 + inw[1] * 1.5, s: block([a, b, add(b, inw, 3), add(a, inw, 3)], h, h + 3, PAL.stone2) });
    var mw = per === 8 ? 4 : 6.5, o0 = per === 8 ? 2 : 2.75;
    for (var u = Math.floor(lo / per) * per + o0; u < hi; u += per) {
      var u0 = Math.max(lo, u), u1 = Math.min(hi, u + mw);
      if (u1 - u0 < 1.5) continue;
      var p0 = at(u0), p1 = at(u1);
      list.push({ y: (p0[1] + p1[1]) / 2 + inw[1] * 1.5 + 0.01, s: block([p0, p1, add(p1, inw, 3.2), add(p0, inw, 3.2)], h, h + 9) });
    }
  }
  /**
   * 一块墙体棱柱。poly：地面多边形；h：高；kinds[i] 对应第 i 条边：
   *   'wall' 外墙面（朝下的画立面、墙顶勾边、上垛口）；'open' 与邻格相接的切口（全不画）；
   *   'pier' 贴着墙墩（不画立面、不上垛口、墙顶细勾）；'plain' 有立面与勾边但不上垛口。
   * o.mode 走道缝方向；o.top 走道色；o.noShadow。
   */
  /** 立面端线：接切口不画；正交立面贴墩子（同一平面延续）不画，斜立面贴墩子画（内折角） */
  function endOk(k) { return k !== 'open' && k !== 'pier'; }
  function prism(ctx, poly, h, kinds, o) {
    o = o || {};
    var E = edges(poly), s = '', faces = [], ol = '', ol2 = '', pars = [];
    // 投影：只沿外墙边（wall / plain）向右下拉一条带，不越过切口落到邻件立面上
    if (!o.noShadow) { var sd = ''; E.forEach(function (e, i) { var k = kinds[i] || 'wall'; if ((k === 'wall' || k === 'plain') && (e.n[0] > 0.05 || e.n[1] > 0.05)) sd += C.pts([e.a, e.b, [e.b[0] + 5, e.b[1] + 4], [e.a[0] + 5, e.a[1] + 4]]); }); s += C.shadow(sd); }
    E.forEach(function (e, i) {
      var k = kinds[i] || 'wall', prev = kinds[(i + E.length - 1) % E.length] || 'wall', next = kinds[(i + 1) % E.length] || 'wall';
      if (k === 'open') return;
      if (k !== 'pier' && e.n[1] > 0.05 && Math.abs(e.b[0] - e.a[0]) > 0.3)
        faces.push({ y: e.my, s: stoneFace(ctx, e.a, e.b, h, { dark: e.n[0] > 0.35, endA: endOk(prev), endB: endOk(next) }) });
      if (k !== 'pier') ol += C.seg([e.a[0], e.a[1] - h], [e.b[0], e.b[1] - h]);
      if (k === 'wall') parapet(e, h, pars);
    });
    faces.sort(function (p, q) { return p.y - q.y; });
    s += faces.map(function (x) { return x.s; }).join('');
    s += walkTop(ctx, lift(poly, h), o.mode, o.top) + C.path(ol, 'none', 1.4) + C.lines(ol2, 1, 0.6);
    pars.sort(function (p, q) { return p.y - q.y; });
    s += pars.map(function (x) { return x.s; }).join('');
    ctx.top(bbox(poly)[1] - h - 10);
    return s;
  }
  var API = { area: area, lift: lift, add: add, edges: edges, bbox: bbox, clip: clip, stoneFace: stoneFace, walkTop: walkTop, block: block, parapet: parapet, prism: prism };
  if (isNode) module.exports = API;
  else root.TownArtWF.geom = API;
})(this);
