/*
 * 织梦 · race-fort-2 棱垒 / 棱堡公共几何（美术样板，尚未接入游戏）
 * 棱堡「替换」一段直墙：占地 N×N，墙格（attach）沿占地的一条边（正交朝向）或一条对角线（斜向朝向）穿过，
 * 堡体 = 与辐条墙同厚（24）、两端切在格边中点 / 格角（与相邻辐条端头完全重合）的墙带 + 朝外的五边形尖角堡身。
 * 放置时跳过 attach 墙格的全部辐条与节点，由棱堡自己画这一段墙。
 * 局部坐标同 race-fort：x 0..N*48，y = 0 为占地前沿、-N*48 为后沿。
 * 浏览器挂 window.TownArtRF2_bastion；Node 用 module.exports。只读引用 ../race-fort/core.js、spoke.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('../race-fort/core.js') : root.TownArtRF_core;
  var K = isNode ? require('../race-fort/spoke.js') : root.TownArtRF_spoke;
  var f = C.f, S2 = Math.SQRT1_2, HW = 12;
  var U = { n: [0, -1], ne: [S2, -S2], e: [1, 0], se: [S2, S2], s: [0, 1], sw: [-S2, S2], w: [-1, 0], nw: [-S2, -S2] };
  /** 穿过 attach 墙格的辐条方向对 */
  var THRU = { n: ['w', 'e'], s: ['w', 'e'], e: ['n', 's'], w: ['n', 's'], ne: ['nw', 'se'], sw: ['nw', 'se'], se: ['ne', 'sw'], nw: ['ne', 'sw'] };
  function origin(dir, N) {
    var W = N * 48, c = W / 2;
    return { n: [c, -24], s: [c, -W + 24], e: [24, -c], w: [W - 24, -c] }[dir] || [c, -c];
  }
  /** attach 墙格：占地内 [列, 行]，行 0 = 最北 */
  function attachCells(dir, N) {
    var out = [];
    for (var i = 0; i < N; i++) out.push({ n: [i, N - 1], s: [i, 0], e: [0, i], w: [N - 1, i], ne: [i, i], sw: [i, i], se: [i, N - 1 - i], nw: [i, N - 1 - i] }[dir]);
    return out;
  }
  /**
   * 外形：sh = { root, sh: [u, v], tip }（u 沿尖角向外，v 沿墙）。
   * 边序：0 切口 1 外侧短幕墙 2 侧翼 3 棱面 4 棱面 5 侧翼 6 外侧短幕墙 7 切口 8 城内侧墙面（gorge）
   */
  function outline(dir, N, sh) {
    var u = U[dir], v = [-u[1], u[0]], O = origin(dir, N), L = dir.length === 2 ? N * 24 * Math.SQRT2 : N * 24;
    function P(a, b) { return [O[0] + u[0] * a + v[0] * b, O[1] + u[1] * a + v[1] * b]; }
    var uv = [[-HW, -L], [HW, -L], [HW, -sh.root], [sh.sh[0], -sh.sh[1]], [sh.tip, 0], [sh.sh[0], sh.sh[1]], [HW, sh.root], [HW, L], [-HW, L]];
    var role = ['cut', 'curtain', 'flank', 'face', 'face', 'flank', 'curtain', 'cut', 'gorge'];
    var pts = uv.map(function (q) { return P(q[0], q[1]); });
    return { dir: dir, N: N, O: O, u: u, v: v, L: L, P: P, uv: uv, pts: pts, role: role,
      kinds: role.map(function (r) { return r === 'cut' ? 'start' : 'side'; }), body: pts.slice(2, 7) };
  }
  function ends(e) { return e.A[0] <= e.B[0] ? [e.A, e.B] : [e.B, e.A]; }
  /** 在立面坐标里画：x 为局部 x，y 以墙脚为 0、向上为负；z0 = 墙脚抬高。竖直边（俯视看不到）返回空 */
  function onFace(e, z0, body) {
    var ab = ends(e), A = ab[0], B = ab[1], dx = B[0] - A[0];
    if (Math.abs(dx) < 0.05) return '';
    var k = (B[1] - A[1]) / dx, c = A[1] - k * A[0] - (z0 || 0);
    return '<g transform="matrix(1 ' + f(k) + ' 0 1 0 ' + f(c) + ')">' + body + '</g>';
  }
  function lerp(A, B, t) { return [A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t]; }
  function centroid(pts) { var x = 0, y = 0; pts.forEach(function (p) { x += p[0]; y += p[1]; }); return [x / pts.length, y / pts.length]; }
  function inPoly(pts, x, y) {
    var c = false;
    for (var i = 0, j = pts.length - 1; i < pts.length; j = i++) {
      var a = pts[i], b = pts[j];
      if ((a[1] > y) !== (b[1] > y) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) c = !c;
    }
    return c;
  }
  function distSeg(p, A, B) {
    var dx = B[0] - A[0], dy = B[1] - A[1], L2 = dx * dx + dy * dy || 1, t = Math.max(0, Math.min(1, ((p[0] - A[0]) * dx + (p[1] - A[1]) * dy) / L2));
    var x = A[0] + dx * t - p[0], y = A[1] + dy * t - p[1];
    return Math.sqrt(x * x + y * y);
  }
  /** 多边形内取 n 个点（离边至少 margin），种子随机 */
  function scatter(ctx, pts, n, margin) {
    var x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity, out = [], tries = 0;
    pts.forEach(function (p) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); y0 = Math.min(y0, p[1]); y1 = Math.max(y1, p[1]); });
    while (out.length < n && tries++ < n * 40) {
      var p = [ctx.rnd(x0, x1), ctx.rnd(y0, y1)], ok = inPoly(pts, p[0], p[1]);
      for (var i = 0; ok && i < pts.length; i++) if (distSeg(p, pts[i], pts[(i + 1) % pts.length]) < (margin || 0)) ok = false;
      if (ok) out.push(p);
    }
    return out;
  }
  function lift(pts, z) { return pts.map(function (p) { return [p[0], p[1] - z]; }); }
  function shadow(pts, dx, dy, op) { return C.shadow(C.poly(pts.map(function (p) { return [p[0] + (dx || 6), p[1] + (dy || 4)]; })), op == null ? 0.16 : op); }
  /** 沿边放小块：返回 [{ pts, c, e }]，位置从边起点 offset 开始每 step 一个，块沿边长 la、横向 lb，向内缩 inset */
  function edgeBlocks(e, offset, step, la, lb, inset, endMargin) {
    var out = [], dx = (e.B[0] - e.A[0]) / e.len, dy = (e.B[1] - e.A[1]) / e.len;
    for (var a = offset; a <= e.len - (endMargin == null ? la / 2 : endMargin) + 0.01; a += step) {
      var c = [e.A[0] + dx * a - e.nx * inset, e.A[1] + dy * a - e.ny * inset];
      out.push({ c: c, e: e, pts: [[c[0] - dx * la / 2 - e.nx * lb / 2, c[1] - dy * la / 2 - e.ny * lb / 2], [c[0] + dx * la / 2 - e.nx * lb / 2, c[1] + dy * la / 2 - e.ny * lb / 2],
        [c[0] + dx * la / 2 + e.nx * lb / 2, c[1] + dy * la / 2 + e.ny * lb / 2], [c[0] - dx * la / 2 + e.nx * lb / 2, c[1] - dy * la / 2 + e.ny * lb / 2]] });
    }
    return out;
  }
  /** 边的起点：切口之后的 curtain / gorge 从格边（切口端）起算，保证与相邻墙格的节奏一致 */
  function fromCut(g, es, i) {
    var e = es[i], cutEnd = g.role[(i + es.length - 1) % es.length] === 'cut';
    return cutEnd ? e : { A: e.B, B: e.A, nx: e.nx, ny: e.ny, len: e.len, kind: e.kind };
  }

  /**
   * 凹多边形实体（棱堡外形是凹的）：可见立面按地面深度由远到近排序后画，再画整块顶面与顶面轮廓线。
   * o = { face, top, tex(x0, x1, h, e, i), sw, topTex(top, es) }；kinds 里 'start' 的边（切口）不画立面也不描线。
   */
  function solid(ctx, pts, kinds, z0, h, o) {
    o = o || {};
    var es = K.edgesOf(pts, kinds), n = es.length, s = '', ol = '', i;
    function vis(e) { return e.kind === 'side' && e.ny > 0.02; }
    var idx = [];
    for (i = 0; i < n; i++) if (vis(es[i]) && Math.abs(es[i].B[0] - es[i].A[0]) >= 0.05) idx.push(i);
    idx.sort(function (a, b) { return (es[a].A[1] + es[a].B[1]) - (es[b].A[1] + es[b].B[1]); });
    idx.forEach(function (j) {
      var e = es[j], A = [e.A[0], e.A[1] - z0], B = [e.B[0], e.B[1] - z0];
      s += K.face(ctx, A, B, h, o.face, o.tex ? function (x0, x1, hh) { return o.tex(x0, x1, hh, e, j); } : null, o.sw);
      var pv = es[(j + n - 1) % n], nx = es[(j + 1) % n];
      if (pv.kind === 'side' && !vis(pv)) ol += 'M' + f(A[0]) + ' ' + f(A[1]) + 'v' + f(-h);
      if (nx.kind === 'side' && !vis(nx)) ol += 'M' + f(B[0]) + ' ' + f(B[1]) + 'v' + f(-h);
    });
    var top = lift(pts, z0 + h);
    s += C.path(C.poly(top), o.top, 0);
    if (o.topTex) s += o.topTex(top, es);
    for (i = 0; i < n; i++) if (es[i].kind === 'side') ol += 'M' + f(top[i][0]) + ' ' + f(top[i][1]) + 'L' + f(top[(i + 1) % n][0]) + ' ' + f(top[(i + 1) % n][1]);
    ctx.top(Math.min.apply(null, top.map(function (p) { return p[1]; })));
    return s + C.line(ol, o.sw || 1.6);
  }

  var API = { HW: HW, U: U, THRU: THRU, origin: origin, attachCells: attachCells, outline: outline, onFace: onFace, ends: ends, lerp: lerp, solid: solid,
    centroid: centroid, inPoly: inPoly, distSeg: distSeg, scatter: scatter, lift: lift, shadow: shadow, edgeBlocks: edgeBlocks, fromCut: fromCut };
  root.TownArtRF2_bastion = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
