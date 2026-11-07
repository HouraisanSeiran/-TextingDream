/*
 * 织梦 · race-fort 辐条城墙几何（规范第 11 节）+ 通用棱柱绘制（3/4 斜俯视：墙顶上移 H，朝南的边画立面）
 * 格内坐标：x 0..48，y = 0 为本格前沿、-48 为后沿，格中心 (24, -24)。
 * 墙厚 24（半宽 HW = 12），斜段同厚；节点墩子是 28×28 方墩（半宽 NH = 14），比墙高 NB。
 * 先画的辐条（n / ne / nw，排序 +0.1）从格中心起画，后面会被节点墩子盖住；
 * 后画的辐条（e / w / s / se / sw）从墩子边界起画，不压墩子。
 * 斜段从格中心画到格角，端头按垂直于墙向的切线收口，两格在格角处切线完全重合；
 * 代价是端头会伸出本格最多 8.5 px（写在 README 已知问题）。
 * 浏览器挂 window.TownArtRF_spoke；Node 用 module.exports。依赖 core.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtRF_core;
  var f = C.f, HW = 12, NH = 14, D = HW * Math.SQRT2;
  var DIRS = ['n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw'];
  var ORDER = { n: 0.1, ne: 0.1, nw: 0.1, node: 0.2, e: 0.3, w: 0.3, s: 0.4, se: 0.4, sw: 0.4 };
  var EARLY = { n: 1, ne: 1, nw: 1 };
  var MAP = {
    e: function (a, b) { return [a, b]; }, w: function (a, b) { return [-a, b]; },
    s: function (a, b) { return [b, a]; }, n: function (a, b) { return [b, -a]; },
    se: function (a, b) { return [a, b]; }, ne: function (a, b) { return [a, -b]; },
    sw: function (a, b) { return [-a, b]; }, nw: function (a, b) { return [-a, -b]; }
  };
  /** 模板：沿 +a 前进（正交 = 东，斜向 = 东南），返回相对格中心的点与每条边的类型 */
  function template(dir) {
    var early = !!EARLY[dir], a0 = early ? 0 : NH;
    if (dir.length === 1) return { pts: [[a0, -HW], [24, -HW], [24, HW], [a0, HW]], kinds: ['side', 'cap', 'side', 'start'] };
    var e2 = [(48 + D) / 2, (48 - D) / 2], e1 = [(48 - D) / 2, (48 + D) / 2];
    if (early) return { pts: [[-D / 2, D / 2], [D / 2, -D / 2], e2, e1], kinds: ['start', 'side', 'cap', 'side'] };
    return { pts: [[NH - D, NH], [NH, NH], [NH, NH - D], e2, e1], kinds: ['start', 'start', 'side', 'cap', 'side'] };
  }
  /** 辐条地面多边形（格内坐标） */
  function spokeGeom(dir) {
    var t = template(dir), m = MAP[dir];
    return { pts: t.pts.map(function (p) { var q = m(p[0], p[1]); return [24 + q[0], -24 + q[1]]; }), kinds: t.kinds };
  }
  function nodeGeom(nh) { nh = nh || NH; return { pts: [[24 - nh, -24 - nh], [24 + nh, -24 - nh], [24 + nh, -24 + nh], [24 - nh, -24 + nh]], kinds: ['side', 'side', 'side', 'side'] }; }

  function edgesOf(pts, kinds) {
    var n = pts.length, a2 = 0, i, out = [];
    for (i = 0; i < n; i++) { var p = pts[i], q = pts[(i + 1) % n]; a2 += p[0] * q[1] - q[0] * p[1]; }
    for (i = 0; i < n; i++) {
      var A = pts[i], B = pts[(i + 1) % n], ex = B[0] - A[0], ey = B[1] - A[1], L = Math.sqrt(ex * ex + ey * ey) || 1;
      out.push({ A: A, B: B, nx: (a2 > 0 ? ey : -ey) / L, ny: (a2 > 0 ? -ex : ex) / L, kind: kinds ? kinds[i] : 'side', len: L });
    }
    return out;
  }
  function up(p, h) { return [p[0], p[1] - h]; }
  /** 立面：地面边 A→B 向上拉高 h；纹理 tex(x0, x1, h) 在「底 y=0、顶 y=-h、x 为格内坐标」的平直坐标系里画，再错切到斜边上 */
  function face(ctx, A, B, h, fill, tex, sw) {
    if (A[0] > B[0]) { var t = A; A = B; B = t; }
    var k = (B[1] - A[1]) / (B[0] - A[0]), c = A[1] - k * A[0], id = ctx.uid();
    var quad = C.poly([A, B, up(B, h), up(A, h)]);
    var s = '<clipPath id="' + id + '"><path d="' + quad + '"/></clipPath>' + C.path(quad, fill, 0);
    if (tex) s += '<g clip-path="url(#' + id + ')"><g transform="matrix(1 ' + f(k) + ' 0 1 0 ' + f(c) + ')">' + tex(A[0], B[0], h) + '</g></g>';
    return s + C.line('M' + f(A[0]) + ' ' + f(A[1]) + 'L' + f(B[0]) + ' ' + f(B[1]), sw || 1.6);
  }
  /** 斜边上 x 处的地面 y */
  function yAt(e, x) { var A = e.A, B = e.B; return Math.abs(B[0] - A[0]) < 0.01 ? A[1] : A[1] + (B[1] - A[1]) * (x - A[0]) / (B[0] - A[0]); }

  /**
   * 棱柱：地面多边形 pts（格内坐标），底面抬高 z0，高 h。只画朝屏幕下方（法线 ny > 0）且 kind 为 side 的立面，再画顶面。
   * o = { face, top, tex(x0,x1,h,e), topTex(ptsTop) 返回串, sw, edge(eTop) 返回墙顶外缘装饰, noTopLine }
   */
  function prism(ctx, pts, z0, h, o, kinds) {
    o = o || {};
    var es = edgesOf(pts, kinds), s = '', ol = '', i, n = es.length;
    var lift = function (p) { return [p[0], p[1] - z0]; };
    function vis(e) { return e.ny > 0.02 && e.kind === 'side'; }
    for (i = 0; i < n; i++) {
      var e = es[i];
      if (!vis(e) || Math.abs(e.B[0] - e.A[0]) < 0.05) continue;
      var A = lift(e.A), B = lift(e.B);
      s += face(ctx, A, B, h, o.face, o.tex ? function (x0, x1, hh) { return o.tex(x0, x1, hh, e); } : null, o.sw);
      var pv = es[(i + n - 1) % n], nx = es[(i + 1) % n];
      if (pv.kind === 'side' && !vis(pv)) ol += 'M' + f(A[0]) + ' ' + f(A[1]) + 'v' + f(-h);
      if (nx.kind === 'side' && !vis(nx)) ol += 'M' + f(B[0]) + ' ' + f(B[1]) + 'v' + f(-h);
    }
    var top = pts.map(function (p) { return [p[0], p[1] - z0 - h]; });
    s += C.path(C.poly(top), o.top, 0);
    if (o.topTex) s += o.topTex(top, es);
    if (!o.noTopLine) for (i = 0; i < n; i++) if (es[i].kind === 'side') {
      ol += 'M' + f(top[i][0]) + ' ' + f(top[i][1]) + 'L' + f(top[(i + 1) % n][0]) + ' ' + f(top[(i + 1) % n][1]);
    }
    ctx.top(Math.min.apply(null, top.map(function (p) { return p[1]; })));
    return s + C.line(ol, o.sw || 1.6);
  }
  /** 辐条的沿墙坐标系：u 沿墙向外，v 垂直；a0 = 两侧外缘起点，a1 = 端头（格边中点 / 格角） */
  function frame(dir) {
    var m = MAP[dir], diag = dir.length === 2, k = diag ? Math.SQRT1_2 : 1;
    var u = m(diag ? k : 1, diag ? k : 0), v = m(diag ? k : 0, diag ? -k : 1);
    var a0 = EARLY[dir] ? 0 : (diag ? (2 * NH - D) * Math.SQRT1_2 : NH);
    return { dir: dir, diag: diag, u: u, v: v, a0: a0, a1: diag ? 24 * Math.SQRT2 : 24, early: !!EARLY[dir] };
  }
  function at(fr, a, b) { return [24 + fr.u[0] * a + fr.v[0] * b, -24 + fr.u[1] * a + fr.v[1] * b]; }
  /** 端头对称的节奏点：a1 - step/2, a1 - 3step/2, …（两格在端头处节奏一致） */
  function beats(fr, step, margin) {
    var out = [];
    for (var a = fr.a1 - step / 2; a - (margin || 0) >= fr.a0 - 0.01; a -= step) out.push(a);
    return out.reverse();
  }
  /** 沿墙放的小块（垛口、桩基）：中心 a、侧偏 b，沿墙长 la、横向 lb，返回地面多边形 */
  function block(fr, a, b, la, lb) {
    return [at(fr, a - la / 2, b - lb / 2), at(fr, a + la / 2, b - lb / 2), at(fr, a + la / 2, b + lb / 2), at(fr, a - la / 2, b + lb / 2)];
  }
  /** 八边形地面多边形：中心 (cx, cy)，半宽 r，切角比 k */
  function octo(cx, cy, r, k) {
    var c = r * (k == null ? 0.42 : k);
    return [[cx - r + c, cy - r], [cx + r - c, cy - r], [cx + r, cy - r + c], [cx + r, cy + r - c], [cx + r - c, cy + r], [cx - r + c, cy + r], [cx - r, cy + r - c], [cx - r, cy - r + c]];
  }
  /** n 边近似圆：中心、半径 rx/ry、起始角 */
  function ring(cx, cy, rx, ry, n, a0) {
    var out = [];
    for (var i = 0; i < n; i++) { var t = (a0 || 0) + i * Math.PI * 2 / n; out.push([cx + rx * Math.cos(t), cy + ry * Math.sin(t)]); }
    return out;
  }
  /** 墙段投影：地面多边形向右下平移 */
  function shadowOf(pts, dx, dy) { return C.shadow(C.poly(pts.map(function (p) { return [p[0] + (dx || 5), p[1] + (dy || 3)]; }))); }

  var API = {
    HW: HW, NH: NH, D: D, DIRS: DIRS, ORDER: ORDER, EARLY: EARLY, spokeGeom: spokeGeom, nodeGeom: nodeGeom, edgesOf: edgesOf,
    face: face, yAt: yAt, prism: prism, frame: frame, at: at, beats: beats, block: block, octo: octo, ring: ring, shadowOf: shadowOf
  };
  root.TownArtRF_spoke = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
