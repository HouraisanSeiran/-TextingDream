/*
 * 织梦 · 阿拉伯风格 8 向辐条夯土墙（规范第 11 节）：wallspoke-{n,ne,e,se,s,sw,w,nw} + wallnode（2 变体）（美术样板，尚未接入游戏）
 * 格内坐标：x 0..48，y = 0 为本格前沿、-48 为后沿，格中心 (24, -24)。
 * 墙厚 24（半宽 HW = 12，斜段同厚），墙高与双网格城墙一致（WALL_H = 38）；节点墩 28×28（半宽 NH = 14），比墙高 NB。
 * 先画的辐条（n / ne / nw，排序 +0.1）从格中心起画、被节点墩盖住；后画的（e / w / s / se / sw）从墩子边界起画。
 * 斜段从格中心画到格角，端头垂直于墙向收口，两格在格角处端面重合；端头会伸出本格最多 8.5 px（README 已知问题）。
 * 垛口与脚手架孔按「离端头的距离」排节奏（端头对称），两格在对接处连续。
 * 浏览器挂 window.TownArtAB_spoke；Node 用 module.exports。依赖 core.js、parts2.js、tiles-wall.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  function dep(file, name) { return isNode ? require(file) : root[name]; }
  var C = dep('./core.js', 'TownArtAB_core'), Q2 = dep('./parts2.js', 'TownArtAB_parts2'), W = dep('./tiles-wall.js', 'TownArtAB_wall');
  var P = C.PAL, f = C.f, HW = 12, NH = 14, NB = 7, H = W.WALL_H, R2 = Math.SQRT2, R1 = Math.SQRT1_2;
  var DIRS = ['n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw'];
  var ORDER = { n: 0.1, ne: 0.1, nw: 0.1, node: 0.2, e: 0.3, w: 0.3, s: 0.4, se: 0.4, sw: 0.4 };
  var EARLY = { n: 1, ne: 1, nw: 1 };
  /** 方向 → 单位向量 u（沿墙向外）；v = u 顺时针转 90°（屏幕坐标 y 向下） */
  var U = { e: [1, 0], w: [-1, 0], s: [0, 1], n: [0, -1], se: [R1, R1], ne: [R1, -R1], sw: [-R1, R1], nw: [-R1, -R1] };
  function frame(dir) {
    var u = U[dir], diag = dir.length === 2, v = [-u[1], u[0]];
    var a0 = EARLY[dir] ? 0 : (diag ? NH * R2 - HW : NH), a1 = diag ? 24 * R2 : 24;
    return { dir: dir, diag: diag, u: u, v: v, a0: a0, a1: a1, early: !!EARLY[dir] };
  }
  function at(fr, a, b) { return [24 + fr.u[0] * a + fr.v[0] * b, -24 + fr.u[1] * a + fr.v[1] * b]; }
  /** 辐条地面多边形与边类型（side = 墙侧面，start / cap = 起点 / 端头，不画立面） */
  function geom(dir) {
    var fr = frame(dir);
    if (!fr.diag || fr.early) {
      return { fr: fr, pts: [at(fr, fr.a0, -HW), at(fr, fr.a1, -HW), at(fr, fr.a1, HW), at(fr, fr.a0, HW)], kinds: ['side', 'cap', 'side', 'start'] };
    }
    // 后画的斜段：起点贴着方墩的角（两条墩边），保证墩与墙之间不露缝
    var sx = fr.u[0] > 0 ? 1 : -1, sy = fr.u[1] > 0 ? 1 : -1, c = [24 + sx * NH, -24 + sy * NH], k = HW * R2;
    var pA = [c[0] - sx * k, c[1]], pB = [c[0], c[1] - sy * k], e1 = at(fr, fr.a1, -HW), e2 = at(fr, fr.a1, HW);
    // 按多边形顺序：pA → c → pB → 端头两点，按 v 侧排列
    var side = function (p) { return (p[0] - 24) * fr.v[0] + (p[1] + 24) * fr.v[1]; };
    var first = side(pA) < side(pB) ? [pA, c, pB] : [pB, c, pA];
    return { fr: fr, pts: [first[2], first[1], first[0], e1, e2], kinds: ['start', 'start', 'side', 'cap', 'side'] };
  }
  function edgesOf(pts, kinds) {
    var n = pts.length, a2 = 0, i, out = [];
    for (i = 0; i < n; i++) { var p = pts[i], q = pts[(i + 1) % n]; a2 += p[0] * q[1] - q[0] * p[1]; }
    for (i = 0; i < n; i++) {
      var A = pts[i], B = pts[(i + 1) % n], ex = B[0] - A[0], ey = B[1] - A[1], L = Math.hypot(ex, ey) || 1;
      out.push({ A: A, B: B, nx: (a2 > 0 ? ey : -ey) / L, ny: (a2 > 0 ? -ex : ex) / L, kind: kinds[i] });
    }
    return out;
  }
  /** 夯土立面纹理（平直坐标：底 y = 0，顶 y = -h）：8 px 一道夯层线，脚手架孔按格内 x ≡ 6 (mod 12) 错行排 */
  function mudTex(x0, x1, h) {
    var d = '', s = '', y, x, row = 0;
    for (y = -8; y > -h + 3; y -= 8) d += 'M' + f(x0) + ' ' + f(y) + 'H' + f(x1);
    for (y = -17; y > -h + 6; y -= 16, row++) for (x = 6 + (row % 2) * 12; x < 48; x += 24) if (x > x0 + 1 && x < x1 - 2) s += C.rect(x, y, 2, 2, P.hole, 0);
    return C.rect(x0 - 1, -4, x1 - x0 + 2, 4, P.mud2, 0) + C.line(d + 'M' + f(x0) + ' -4H' + f(x1), 0.7, 0.45) + s + C.rect(x0 - 1, -h, x1 - x0 + 2, 2.5, P.mud3, 0, 0.5);
  }
  /** 立面：地面边 A→B 向上拉高 h，纹理在平直坐标里画再错切到斜边上 */
  function face(ctx, A, B, h, fill) {
    if (A[0] > B[0]) { var t = A; A = B; B = t; }
    var k = (B[1] - A[1]) / (B[0] - A[0]), c = A[1] - k * A[0];
    var quad = C.poly([A, B, [B[0], B[1] - h], [A[0], A[1] - h]]);
    return C.path(quad, fill, 0) + C.clipped(ctx, quad, '<g transform="matrix(1 ' + f(k) + ' 0 1 0 ' + f(c) + ')">' + mudTex(A[0], B[0], h) + '</g>') +
      C.line('M' + f(A[0]) + ' ' + f(A[1]) + 'L' + f(B[0]) + ' ' + f(B[1]), 1.6);
  }
  /** 棱柱：画朝屏幕下方（ny > 0）的 side 立面 + 顶面；返回 { svg, top:顶面点, es } */
  function prism(ctx, pts, kinds, h, fill, topFill) {
    var es = edgesOf(pts, kinds), s = '', ol = '', n = es.length, i;
    function vis(e) { return e.ny > 0.02 && e.kind === 'side' && Math.abs(e.B[0] - e.A[0]) > 0.05; }
    for (i = 0; i < n; i++) {
      var e = es[i];
      if (!vis(e)) continue;
      s += face(ctx, e.A, e.B, h, fill);
      var pv = es[(i + n - 1) % n], nx = es[(i + 1) % n];
      if (pv.kind === 'side' && !vis(pv)) ol += 'M' + f(e.A[0]) + ' ' + f(e.A[1]) + 'v' + f(-h);
      if (nx.kind === 'side' && !vis(nx)) ol += 'M' + f(e.B[0]) + ' ' + f(e.B[1]) + 'v' + f(-h);
    }
    var top = pts.map(function (p) { return [p[0], p[1] - h]; });
    s += C.path(C.poly(top), topFill, 0);
    for (i = 0; i < n; i++) if (es[i].kind === 'side') ol += 'M' + f(top[i][0]) + ' ' + f(top[i][1]) + 'L' + f(top[(i + 1) % n][0]) + ' ' + f(top[(i + 1) % n][1]);
    ctx.top(Math.min.apply(null, top.map(function (p) { return p[1]; })));
    return { svg: s, ol: ol, top: top, es: es };
  }
  /** 端头对称的节奏点：a1 - step/2, a1 - 3step/2, …（两格在端头处节奏一致） */
  function beats(fr, step, margin) {
    var out = [];
    for (var a = fr.a1 - step / 2; a - margin >= fr.a0 - 0.01; a -= step) out.push(a);
    return out.reverse();
  }
  function lift(p, h) { return [p[0], p[1] - h]; }
  /** 墙顶两侧的阶梯雉堞：后侧（屏幕上方）小、前侧大；南北向墙两侧只画压顶条（与双网格城墙一致） */
  function crest(ctx, fr) {
    var s = '', back = '', front = '', walk = '';
    if (fr.dir === 'n' || fr.dir === 's') {
      var y0 = Math.min(at(fr, fr.a0, 0)[1], at(fr, fr.a1, 0)[1]) - H, y1 = Math.max(at(fr, fr.a0, 0)[1], at(fr, fr.a1, 0)[1]) - H;
      return C.rect(24 - HW, y0, 3, y1 - y0, P.lime2, 0.8) + C.rect(24 + HW - 3, y0, 3, y1 - y0, P.mud3, 0.8) + C.line('M24 ' + f(y0) + 'V' + f(y1), 0.6, 0.3);
    }
    var step = fr.diag ? 24 * R2 / 4 : 12, bs = beats(fr, step, fr.early ? 2 : 3);
    var bSide = at(fr, 0, -HW)[1] < at(fr, 0, HW)[1] ? -1 : 1;
    bs.forEach(function (a) {
      var pb = lift(at(fr, a, bSide * (HW - 1.6)), H), pf = lift(at(fr, a, -bSide * (HW - 1.6)), H);
      back += W.merlon(pb[0], pb[1] + 1, fr.diag ? 5.5 : 7, 6, P.mud2, 0.8);
      front += W.merlon(pf[0], pf[1] + 1.5, fr.diag ? 6 : 8, fr.diag ? 8 : 9, P.mud, 1);
    });
    var w0 = lift(at(fr, fr.a0, 0), H), w1 = lift(at(fr, fr.a1, 0), H);
    walk = C.line('M' + f(w0[0]) + ' ' + f(w0[1]) + 'L' + f(w1[0]) + ' ' + f(w1[1]), 0.6, 0.3);
    s += back + walk + front;
    ctx.top(Math.min(w0[1], w1[1]) - 11);
    return s;
  }
  function spoke(ctx, dir) {
    var g = geom(dir), fr = g.fr, s = '';
    s += C.shadow(C.poly(g.pts.map(function (p) { return [p[0] + 5, p[1] + 3]; })));
    var pr = prism(ctx, g.pts, g.kinds, H, P.mud, W.WALK);
    // 南北向墙：后画的 s 段起点处画一道立面接缝（被墩子盖住的 n 段不需要）
    return s + pr.svg + crest(ctx, fr) + C.line(pr.ol, 1.4);
  }
  /**
   * 节点墩：v1 东西直段平齐墩（与墙同高同厚，垛口节奏与 e / w 段一致：x = 18、30）；
   * v2 拐点凸起八角墩带绿松石瓷砖带 + 小旗；v3 南北 / 斜向直段平齐墩（无垛口，两侧压顶条，与 n / s 段一致）。
   */
  function node(ctx, v) {
    if (v !== 2) return flushNode(ctx, v);
    var hh = H + NB, pts, kinds, s = '';
    { var c = NH * 0.42; pts = [[24 - NH + c, -24 - NH], [24 + NH - c, -24 - NH], [24 + NH, -24 - NH + c], [24 + NH, -24 + NH - c], [24 + NH - c, -24 + NH], [24 - NH + c, -24 + NH], [24 - NH, -24 + NH - c], [24 - NH, -24 - NH + c]]; }
    kinds = pts.map(function () { return 'side'; });
    s += C.shadow(C.poly(pts.map(function (p) { return [p[0] + 5, p[1] + 3]; })));
    var pr = prism(ctx, pts, kinds, hh, P.mud, W.WALK);
    s += pr.svg;
    var yb = -24 + NH, top = yb - hh;
    if (v === 2) s += Q2.tileBand(ctx, 24 - NH * 0.58, 24 + NH * 0.58, top + 6, 3.2, 'star', P.turq, P.lime) + Q2.win(22.5, yb - 22, 3, 8, 'slit');
    // 墩顶：后排小雉堞 → 前排大雉堞
    var back = '', front = '', xs = v === 1 ? [13, 20.3, 27.7, 35] : [17, 24, 31];
    xs.forEach(function (x) { back += W.merlon(x, top - 2 * NH + 2, 6, 6, P.mud2, 0.8); front += W.merlon(x, top + 1.5, 6.5, 9, P.mud, 1); });
    s += back + C.line(pr.ol, 1.4) + front;
    if (v === 2) { s += C.line('M24 ' + f(top - NH) + 'v-16', 1.2) + C.path('M24 ' + f(top - NH - 16) + 'l9 2.6l-9 2.8Z', P.ochre, 0.7); ctx.top(top - NH - 18); }
    ctx.top(top - 2 * NH - 6);
    return s;
  }
  function flushNode(ctx, v) {
    var ew = v === 1, hx = ew ? NH : HW, hy = ew ? HW : NH, x0 = 24 - hx, x1 = 24 + hx, y0 = -24 - hy - H, y1 = -24 + hy - H, s = '';
    var pts = [[x0, -24 - hy], [x1, -24 - hy], [x1, -24 + hy], [x0, -24 + hy]];
    s += C.shadow(C.poly(pts.map(function (p) { return [p[0] + 5, p[1] + 3]; })));
    s += face(ctx, [x0, -24 + hy], [x1, -24 + hy], H, P.mud) + C.rect(x0, y0, 2 * hx, 2 * hy, W.WALK, 0);
    if (ew) {
      var yb = -24 - HW + 1.6 - H, yf = -24 + HW - 1.6 - H, b = '', fr = '';
      [18, 30].forEach(function (x) { b += W.merlon(x, yb + 1, 7, 6, P.mud2, 0.8); fr += W.merlon(x, yf + 1.5, 8, 9, P.mud, 1); });
      s += b + C.line('M' + f(x0) + ' ' + f(-24 - H) + 'H' + f(x1), 0.6, 0.3) + C.line('M' + f(x0) + ' ' + f(y0) + 'H' + f(x1) + 'M' + f(x0) + ' ' + f(y1) + 'H' + f(x1), 1.4) + fr;
    } else {
      s += C.rect(x0, y0, 3, 2 * hy, P.lime2, 0.8) + C.rect(x1 - 3, y0, 3, 2 * hy, P.mud3, 0.8) + C.line('M24 ' + f(y0) + 'V' + f(y1), 0.6, 0.3);
    }
    ctx.top(y0 - 10);
    return s;
  }
  function all(wrap) {
    var out = [];
    DIRS.forEach(function (dir) {
      var id = 'arab-common-wallspoke-' + dir, ctx = new C.Ctx(id), body = spoke(ctx, dir);
      out.push(wrap(id, [1, 1], body, Math.min(ctx.minY, -48), {
        id: id, style: 'arab', race: 'common', category: 'wall', kind: 'wall_spoke', facility: 'city_wall', variant: 1, dir: dir, sort_offset: ORDER[dir],
        name: '辐条夯土墙 ' + dir.toUpperCase(), tags: ['spoke', 'dir_' + dir, 'rammed_earth', 'stepped_merlons'], roof: 'none',
        note: '半段墙：格中心 → ' + (dir.length === 2 ? '格角' : '格边中点') + '；排序键 = 本格前沿 y + ' + ORDER[dir] + (dir.length === 2 ? '；端头伸出本格 ≤ 8.5 px' : '')
      }));
    });
    [1, 2, 3].forEach(function (v) {
      var id = 'arab-common-wallnode-' + C.pad2(v), ctx = new C.Ctx(id), body = node(ctx, v);
      out.push(wrap(id, [1, 1], body, ctx.minY, {
        id: id, style: 'arab', race: 'common', category: 'wall', kind: 'wall_node', facility: 'city_wall', variant: v, sort_offset: ORDER.node,
        name: ['', '辐条墙节点 东西直段平齐墩', '辐条墙节点 拐点八角墩', '辐条墙节点 南北 / 斜向直段平齐墩'][v], tags: ['spoke', 'node', 'rammed_earth', ['', 'straight_ew', 'corner', 'straight_ns_diag'][v]], roof: 'none',
        note: '墙格中心的墩子 / 拐点，排序键 = 本格前沿 y + 0.2；可用 arab-common-wall-tower 替代'
      }));
    });
    return out;
  }
  var API = { HW: HW, NH: NH, DIRS: DIRS, ORDER: ORDER, geom: geom, spoke: spoke, node: node, all: all };
  root.TownArtAB_spoke = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
