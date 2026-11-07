/*
 * 织梦 · race-fort 精灵族：荆棘藤墙辐条 + 墙节点 + 树冠哨塔 + 藤木哨台 + 荆棘棱垒（美术样板，尚未接入游戏）
 * 墙高 34、墙厚 24、编藤纹理周期 12、银白木桩、叶面墙顶、北沿苔团 / 南沿垂叶，全部照 west-elf/tiles.js。
 * 浏览器挂 window.TownArtRF_elf；Node 用 module.exports。依赖 core.js、spoke.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtRF_core;
  var K = isNode ? require('./spoke.js') : root.TownArtRF_spoke;
  var P = C.P, f = C.f, line = C.line, path = C.path, rect = C.rect, H = 34;

  /** 正面编藤（平直坐标：底 y = 0，顶 y = -h），与 west-elf thornFace 同一套周期 */
  function weave(x0, x1, h) {
    var d1 = '', d2 = '', th = '', k, r;
    for (k = Math.floor(x0 / 12) * 12 - 12; k < x1 + 12; k += 12) {
      for (r = 0; r < 3 && 7 + r * 10 < h; r++) {
        var y0 = -7 - r * 10;
        d1 += 'M' + f(k) + ' ' + f(y0) + 'Q' + f(k + 6) + ' ' + f(y0 - 8) + ' ' + f(k + 12) + ' ' + f(y0);
        d2 += 'M' + f(k) + ' ' + f(y0 - 6) + 'Q' + f(k + 6) + ' ' + f(y0 + 2) + ' ' + f(k + 12) + ' ' + f(y0 - 6);
        th += 'M' + f(k + 5) + ' ' + f(y0 - 4) + 'l1 -2.8l1 2.8Z' + 'M' + f(k + 11) + ' ' + f(y0 - 3) + 'l1.6 1.6l-2 0.6Z';
      }
    }
    return line(d2, 2.6, 1, P.bark) + line(d1, 3, 1) + line(d1, 1.8, 1, P.leaf2) + line(d2, 0.5, 0.5) +
      path(th, P.silver2, 0.5) + rect(x0, -h, x1 - x0, 2.5, P.shadow, 0, 0.2) +
      rect(x0, -4, x1 - x0, 4, P.stone2, 0) + line('M' + f(x0) + ' -4H' + f(x1), 0.8, 0.6);
  }
  /** 沿线段 A→B 向法线 (nx, ny) 鼓出的一串叶团（闭合，可填色）；lobe = 每团长度 */
  function scallop(A, B, nx, ny, amp, lobe) {
    var dx = B[0] - A[0], dy = B[1] - A[1], L = Math.sqrt(dx * dx + dy * dy), n = Math.max(1, Math.round(L / lobe)), d = 'M' + f(A[0]) + ' ' + f(A[1]);
    for (var i = 0; i < n; i++) {
      var tm = (i + 0.5) / n, te = (i + 1) / n;
      d += 'Q' + f(A[0] + dx * tm + nx * amp) + ' ' + f(A[1] + dy * tm + ny * amp) + ' ' + f(A[0] + dx * te) + ' ' + f(A[1] + dy * te);
    }
    return d + 'Z';
  }
  /** 墙顶外缘：朝下的边垂叶（叶绿 + 银刺），朝上 / 朝西的边苔团，朝东的边暗叶 */
  function rims(es, z, onlyKinds) {
    var s = '';
    es.forEach(function (e) {
      if (e.kind !== 'side' && !(onlyKinds && onlyKinds[e.kind])) return;
      var A = [e.A[0], e.A[1] - z], B = [e.B[0], e.B[1] - z];
      if (e.ny > 0.02) {
        s += path(scallop(A, B, e.nx * 0.6, 1, 4.2, 6), P.leaf, 1.1);
        var mx = (A[0] + B[0]) / 2, my = (A[1] + B[1]) / 2;
        s += path('M' + f(mx - 3) + ' ' + f(my + 1) + 'l1 -3l1 3ZM' + f(mx + 2) + ' ' + f(my + 1) + 'l1 -3l1 3Z', P.silver2, 0.5);
      } else {
        s += path(scallop(A, B, e.nx, e.ny, 4.6, 6), e.nx > 0.5 ? P.leaf2 : P.moss, 1.1);
      }
    });
    return s;
  }
  /** 银白木桩：底 (x, yb)，高 h，尖头冒出 */
  function post(x, yb, h, w) {
    w = w || 4;
    return path('M' + f(x - w / 2) + ' ' + f(yb) + 'V' + f(yb - h) + 'L' + f(x) + ' ' + f(yb - h - w - 1) + 'L' + f(x + w / 2) + ' ' + f(yb - h) + 'V' + f(yb) + 'Z', P.silver, 1) +
      line('M' + f(x + w * 0.22) + ' ' + f(yb - 1) + 'V' + f(yb - h + 1), 0.8, 1, P.silver3);
  }
  /** 墙顶叶纹 + 银花点（沿墙节奏点） */
  function topLeaves(fr, a0, z) {
    var d = '', dots = '';
    K.beats(fr, fr.diag ? 11.31 : 12, 1).forEach(function (a, i) {
      if (a < a0) return;
      var p = K.at(fr, a, -4), q = K.at(fr, a - 3, 5);
      d += 'M' + f(p[0] - 2) + ' ' + f(p[1] - z) + 'q2 -2.6 4 0M' + f(q[0] - 2) + ' ' + f(q[1] - z) + 'q2 -2.6 4 0';
      if (i % 2 === 0) { var c = K.at(fr, a + 2, 1); dots += C.ell(c[0], c[1] - z, 1.1, 1.1, P.silver, 0.5); }
    });
    return line(d, 0.7, 0.45) + dots;
  }

  // ---------- 辐条 / 节点 ----------
  function spoke(ctx, dir) {
    var g = K.spokeGeom(dir), fr = K.frame(dir), es = K.edgesOf(g.pts, g.kinds), s = '';
    s += K.shadowOf(g.pts, 5, 3);
    s += K.prism(ctx, g.pts, 0, H, { face: P.bark2, top: P.leaf, tex: weave }, g.kinds);
    s += topLeaves(fr, fr.a0, H) + rims(es, H);
    if (fr.diag) K.beats(fr, 24).forEach(function (a) {
      if (a < fr.a0 + 2) return;
      var p = K.at(fr, a, 12), q = K.at(fr, a, -12), b = p[1] > q[1] ? p : q;
      s += post(b[0], b[1] - 0.5, H);
    });
    ctx.top(-24 - 12 - H - 6);
    return s;
  }
  /** 墙节点：28×28 方墩，比墙高 hh；v=1 荆棘根墩（四角银桩 + 顶上刺丛），v=2 苔石座（石基 + 月光灯柱） */
  function node(ctx, v) {
    var g = K.nodeGeom(), es = K.edgesOf(g.pts, g.kinds), hh = v === 2 ? H + 4 : H + 6, s = '';
    s += K.shadowOf(g.pts, 6, 4);
    if (v === 2) s += K.prism(ctx, g.pts, 0, 8, { face: P.stone2, top: P.stone3 }, g.kinds);
    s += K.prism(ctx, g.pts, v === 2 ? 8 : 0, v === 2 ? hh - 8 : hh, { face: P.bark2, top: P.leaf, tex: function (x0, x1, h) { return weave(x0, x1, h); } }, g.kinds);
    if (v === 2) s += line('M10 -10.5H38', 0.9, 0.6) + line('M17 -10v-8M30 -10v-8', 0.8, 0.5);
    s += rims(es, hh);
    var ty = -24 - hh;
    if (v === 2) { // 月光灯柱：银柱 + 月白灯罩 + 叶片小顶
      s += post(24, ty + 4, 16, 4.4) + path('M19.5 ' + f(ty - 13) + 'h9l-1.5 -8h-6Z', P.moon, 1.1) + C.ell(24, ty - 17, 2, 2.2, '#f3eccf', 0.6) +
        path('M18 ' + f(ty - 20.5) + 'Q24 ' + f(ty - 28) + ' 30 ' + f(ty - 20.5) + 'Z', P.leaf2, 1.1);
      ctx.top(ty - 29);
    } else { // 顶上一丛银刺与卷须
      s += path('M15 ' + f(ty + 2) + 'l3 -9l2 8l3 -11l2 11l3 -8l2 9Z', P.silver2, 0.9) + line('M27 ' + f(ty - 2) + 'q5 -6 1 -9q-3 -1 -1 2', 1.1, 1, P.leaf2);
      ctx.top(ty - 12);
    }
    s += post(12, -10.5, hh) + post(36, -10.5, hh);
    // 前沿根须（不越过本格前沿）
    s += line('M12 -10q-3 4 -7 5M36 -10q2 3 7 4M24 -10q1 3 -1 6', 1.4, 1, P.bark) + line('M12 -10q-3 4 -7 5M36 -10q2 3 7 4', 0.6, 0.6);
    return s;
  }
  /** 叶冠：一组叶团（中心 cx, cy，半宽 rx，半高 ry） */
  function crown(ctx, cx, cy, rx, ry) {
    var s = '', i, blobs = [];
    for (i = 0; i < 9; i++) {
      var t = i / 9 * Math.PI * 2;
      blobs.push([cx + Math.cos(t) * rx * 0.62, cy + Math.sin(t) * ry * 0.55, rx * 0.46, ry * 0.5, Math.sin(t) > 0.2 ? P.leaf2 : (Math.cos(t) < -0.2 ? P.moss : P.leaf)]);
    }
    blobs.sort(function (a, b) { return a[1] - b[1]; });
    s += C.ell(cx, cy, rx, ry, P.leaf2, 1.7);
    blobs.forEach(function (b) { s += C.ell(b[0], b[1], b[2], b[3], b[4], 1.1); });
    s += C.ell(cx - rx * 0.1, cy - ry * 0.15, rx * 0.5, ry * 0.42, P.leaf, 1);
    var d = '';
    for (i = 0; i < 7; i++) { var x = cx - rx * 0.6 + ctx.rnd(0, rx * 1.2), y = cy - ry * 0.5 + ctx.rnd(0, ry); d += 'M' + f(x) + ' ' + f(y) + 'q2.4 -3 4.8 0'; }
    s += line(d, 0.8, 0.5) + C.ell(cx - rx * 0.35, cy - ry * 0.35, 1.3, 1.3, P.silver, 0.5) + C.ell(cx + rx * 0.3, cy - ry * 0.1, 1.3, 1.3, P.silver, 0.5);
    ctx.top(cy - ry - 4);
    return s;
  }
  /** 一段活树干（立面）：底 (x, yb) 宽 w，向上 h，顶部向 lean 侧偏 */
  function trunk(x, yb, w, h, lean) {
    var t = yb - h, xl = x - w / 2, xr = x + w / 2, l = lean || 0;
    var d = 'M' + f(xl - 3) + ' ' + f(yb) + 'Q' + f(xl + 1) + ' ' + f(yb - h * 0.5) + ' ' + f(xl + l) + ' ' + f(t) + 'L' + f(xr + l) + ' ' + f(t) +
      'Q' + f(xr - 1) + ' ' + f(yb - h * 0.5) + ' ' + f(xr + 3) + ' ' + f(yb) + 'Z';
    var bark = 'M' + f(x - w * 0.15) + ' ' + f(yb - 3) + 'Q' + f(x - w * 0.2 + l * 0.5) + ' ' + f(yb - h * 0.5) + ' ' + f(x - w * 0.1 + l) + ' ' + f(t + 3) +
      'M' + f(x + w * 0.2) + ' ' + f(yb - 6) + 'q' + f(l * 0.3) + ' ' + f(-h * 0.3) + ' ' + f(l * 0.5) + ' ' + f(-h * 0.55);
    return path(d, P.bark2, 1.6) + path('M' + f(x + w * 0.18) + ' ' + f(yb) + 'Q' + f(xr - 1.5) + ' ' + f(yb - h * 0.5) + ' ' + f(xr + l - 1) + ' ' + f(t) + 'L' + f(xr + l) + ' ' + f(t) + 'Q' + f(xr - 1) + ' ' + f(yb - h * 0.5) + ' ' + f(xr + 3) + ' ' + f(yb) + 'Z', P.bark, 0, 0.55) +
      line(bark, 0.8, 0.55);
  }

  /** 藤梯：两根藤索 + 横档，从 (x, y0) 垂到 (x, y1) */
  function ladder(x, y0, y1, w) {
    var d = 'M' + f(x - w / 2) + ' ' + f(y0) + 'Q' + f(x - w / 2 - 1.5) + ' ' + f((y0 + y1) / 2) + ' ' + f(x - w / 2) + ' ' + f(y1) +
      'M' + f(x + w / 2) + ' ' + f(y0) + 'Q' + f(x + w / 2 + 1.5) + ' ' + f((y0 + y1) / 2) + ' ' + f(x + w / 2) + ' ' + f(y1), rungs = '';
    for (var y = y0 + 5; y < y1 - 2; y += 6) rungs += 'M' + f(x - w / 2) + ' ' + f(y) + 'h' + f(w);
    var lv = '';
    for (y = y0 + 9; y < y1 - 4; y += 13) lv += C.ell(x - w / 2 - 2, y, 2.2, 1.3, P.leaf, 0.6) + C.ell(x + w / 2 + 2, y + 6, 2.2, 1.3, P.leaf2, 0.6);
    return line(rungs, 2.4, 1) + line(rungs, 1.2, 1, P.wood) + line(d, 2.2, 1) + line(d, 1, 1, P.leaf2) + lv;
  }
  /** 环形木台：中心 (cx, cy) 地面投影椭圆 rx×ry，台面高 z，台缘厚 t，带藤栏 */
  function platform(ctx, cx, cy, rx, ry, z, t, rail) {
    var pts = K.ring(cx, cy, rx, ry, 20, 0), s = '';
    s += K.prism(ctx, pts, z - t, t, { face: P.timber, top: P.wood, sw: 1.5, tex: function (x0, x1, h) {
      var d = ''; for (var x = Math.floor(x0 / 6) * 6; x < x1; x += 6) d += 'M' + f(x) + ' 0v' + f(-h); return line(d, 0.7, 0.5);
    } });
    var ty = cy - z, d = '';
    for (var i = 0; i < 6; i++) d += 'M' + f(cx - rx + 4 + i * 4) + ' ' + f(ty - ry + 3 + i * 1.6) + 'l' + f(rx * 0.5) + ' -1.4';
    s += line(d, 0.7, 0.45);
    if (rail) { // 前半圈藤栏：银柱 + 两道藤索
      var top = '', bot = '', posts = '';
      for (i = 0; i <= 10; i++) {
        var a = Math.PI * i / 10, x = cx + rx * 0.94 * Math.cos(a), y = ty + ry * 0.94 * Math.sin(a);
        top += (i ? 'L' : 'M') + f(x) + ' ' + f(y - rail); bot += (i ? 'L' : 'M') + f(x) + ' ' + f(y - rail * 0.45);
        if (i % 2 === 0) posts += post(x, y, rail, 2.6);
      }
      s += line(bot, 2, 1) + line(bot, 0.9, 1, P.leaf2) + posts + line(top, 2.4, 1) + line(top, 1.2, 1, P.leaf);
    }
    return s;
  }
  /** 树冠哨塔（放在墙节点上，替代 wallnode）：荆棘墩 + 活树干 + 小环台 + 叶冠 */
  function tower(ctx) {
    var g = K.nodeGeom(), es = K.edgesOf(g.pts, g.kinds), s = '';
    s += K.shadowOf(g.pts, 6, 4) + C.shadow('M30 -6l14 2l4 -10l-12 -4Z', 0.16);
    s += K.prism(ctx, g.pts, 0, H, { face: P.bark2, top: P.leaf, tex: weave }, g.kinds) + rims(es, H);
    var by = -24 - H + 4;
    s += trunk(24, by, 10, 46, 1);
    s += line('M24 ' + f(by - 30) + 'q-9 -3 -14 -12M25 ' + f(by - 36) + 'q8 -2 13 -11', 3, 1) + line('M24 ' + f(by - 30) + 'q-9 -3 -14 -12M25 ' + f(by - 36) + 'q8 -2 13 -11', 1.6, 1, P.bark2);
    s += platform(ctx, 24, -24, 18, 11, 34 + 46 - 4, 4, 7);
    // 树干穿过环台继续向上托起叶冠（第一轮截图里叶冠悬空，补上）
    s += trunk(24, -24 - 76 + 3, 7, 24, 0) + line('M24 -116q-7 -2 -11 -8M25 -119q6 -1 10 -7', 2.4, 1) + line('M24 -116q-7 -2 -11 -8M25 -119q6 -1 10 -7', 1.2, 1, P.bark2);
    s += crown(ctx, 24, -24 - 34 - 46 - 26, 21, 15);
    s += post(12, -10.5, H) + post(36, -10.5, H);
    return s;
  }
  /** 藤木哨台（fort，2×2）：三株活树干托起环形高台，藤栏、垂下的藤梯、顶上叶冠 */
  function outpost(ctx) {
    var s = '', cx = 48, cy = -50, Z = 78;
    s += C.shadow(C.poly(K.ring(cx + 10, cy + 6, 40, 30, 16, 0)), 0.15);
    // 地面：苔石根盘
    s += C.ell(cx, cy + 4, 34, 22, P.moss, 1.2) + line('M20 -44q8 -6 16 0M60 -36q8 -5 15 1M38 -64q6 -4 12 0', 0.8, 0.5);
    // 后排树干先画，再前排
    s += trunk(cx + 20, cy - 8, 11, Z - 6, -6) + trunk(cx - 22, cy - 6, 12, Z - 6, 5);
    s += platform(ctx, cx, cy, 42, 24, Z - 8, 3, 0);
    s += trunk(cx, cy + 18, 14, Z + 8, 0);
    s += platform(ctx, cx, cy, 40, 23, Z, 5, 9);
    // 根须
    s += line('M41 -30q-6 6 -14 7M55 -30q5 5 13 6M48 -31q1 5 -2 9', 2, 1, P.bark) + line('M41 -30q-6 6 -14 7M55 -30q5 5 13 6', 0.7, 0.6);
    // 树干在台上继续向上，分叉托起叶冠
    var ty = cy - Z;
    s += trunk(cx, ty + 20, 9, 34, 0) + line('M48 ' + f(ty - 8) + 'q-14 -4 -22 -16M49 ' + f(ty - 12) + 'q14 -3 21 -15', 3.4, 1) +
      line('M48 ' + f(ty - 8) + 'q-14 -4 -22 -16M49 ' + f(ty - 12) + 'q14 -3 21 -15', 1.8, 1, P.bark2);
    s += crown(ctx, cx, ty - 40, 40, 24);
    // 藤梯：从台缘前方垂到地面
    s += ladder(cx + 22, cy + 20 - Z + 2, -6, 7);
    // 台上一面银叶小旗
    s += line('M78 ' + f(ty + 4) + 'V' + f(ty - 26), 1.6) + path('M78 ' + f(ty - 26) + 'h12l-4 5l4 5h-12Z', P.silver, 1) + path('M81 ' + f(ty - 23.5) + 'q3 -2 5 1q-3 2 -5 -1Z', P.leaf, 0.5);
    return s;
  }
  var NODE_NOTES = { 1: '荆棘根墩：四角银桩、顶上银刺丛、前沿根须', 2: '苔石座墩：石基 + 编藤墩身 + 月光灯柱' };
  var EXTRA = [];
  function types() {
    var out = [
      { id: 'west-elf-walltower-01', race: 'elf', category: 'wall', kind: 'wall_tower_canopy', facility: 'watchtower', fp: [1, 1], roof: 'none',
        tags: ['node_tower', 'replaces_wallnode', 'order_0.2'], sort: 0.2, note: '树冠哨塔：放在墙节点上替代 wallnode；荆棘墩 + 活树干 + 环台 + 叶冠', draw: tower },
      { id: 'west-elf-vineoutpost-01', race: 'elf', category: 'fort', kind: 'vine_outpost', facility: 'watchtower', fp: [2, 2], roof: 'none',
        tags: ['outpost', 'living_tree', 'ladder'], note: '藤木哨台：三株活树干托起环形高台，藤栏、藤梯、叶冠顶；roof 无对应，叶冠写 none', draw: outpost }
    ];
    return out.concat(EXTRA);
  }
  var API = { NODE_NOTES: NODE_NOTES, EXTRA: EXTRA, types: types, H: H, weave: weave, rims: rims, post: post, spoke: spoke, node: node, crown: crown, trunk: trunk, ladder: ladder, platform: platform, tower: tower, outpost: outpost, scallop: scallop };
  root.TownArtRF_elf = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
