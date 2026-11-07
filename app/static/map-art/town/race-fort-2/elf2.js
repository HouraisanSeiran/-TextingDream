/*
 * 织梦 · race-fort-2 精灵族：荆棘棱垒（fort，2×2，8 向）+ 树冠要塞地标（landmark，6×6）（美术样板，尚未接入游戏）
 * 墙高 34、编藤立面、叶面墙顶、垂叶 / 苔团墙缘、银白木桩，全部沿用 ../race-fort/elf.js（只读 require，不复制）。
 * 浏览器挂 window.TownArtRF2_elf；Node 用 module.exports。依赖 race-fort 的 core.js、spoke.js、elf.js 与本目录 bastion.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('../race-fort/core.js') : root.TownArtRF_core;
  var K = isNode ? require('../race-fort/spoke.js') : root.TownArtRF_spoke;
  var E = isNode ? require('../race-fort/elf.js') : root.TownArtRF_elf;
  var B = isNode ? require('./bastion.js') : root.TownArtRF2_bastion;
  var P = C.P, f = C.f, line = C.line, path = C.path, H = E.H;
  var SHAPE = { o: { root: 20, sh: [40, 34], tip: 64 }, d: { root: 20, sh: [32, 26], tip: 58 } };

  /** 一根弯刺：根 p，朝 (nx, ny) 外伸并上挑，长 len、根宽 w；k 决定弯向与色调 */
  function thorn(p, nx, ny, len, w, k) {
    var t = [p[0] + nx * len, p[1] + ny * len * 0.55 - len * 0.5];
    var dx = t[0] - p[0], dy = t[1] - p[1], L = Math.sqrt(dx * dx + dy * dy) || 1, px = -dy / L * w / 2, py = dx / L * w / 2;
    var bend = (k % 2 ? 1 : -1) * len * 0.12, m = [p[0] + dx * 0.5 + px * bend / (w / 2), p[1] + dy * 0.5 + py * bend / (w / 2)];
    var d = 'M' + f(p[0] + px) + ' ' + f(p[1] + py) + 'Q' + f(m[0] + px * 0.45) + ' ' + f(m[1] + py * 0.45) + ' ' + f(t[0]) + ' ' + f(t[1]) +
      'Q' + f(m[0] - px * 0.45) + ' ' + f(m[1] - py * 0.45) + ' ' + f(p[0] - px) + ' ' + f(p[1] - py) + 'Z';
    var q = [p[0] + dx * 0.62, p[1] + dy * 0.62];
    return path(d, k % 3 ? P.bark : P.bark2, 0.9) + line('M' + f(q[0]) + ' ' + f(q[1]) + 'L' + f(t[0]) + ' ' + f(t[1]), 1.1, 1, P.silver2);
  }
  /** 沿边取刺位：只取 roles 里的边，每 step 一根，根点抬到墙顶下 3 px */
  function thornSpots(g, es, roles, step, z) {
    var out = [];
    es.forEach(function (e, i) {
      if (!roles[g.role[i]]) return;
      var n = Math.max(2, Math.round(e.len / step));
      for (var j = 0; j < n; j++) {
        var t = (j + 0.5) / n;
        out.push({ p: [e.A[0] + (e.B[0] - e.A[0]) * t + e.nx, e.A[1] + (e.B[1] - e.A[1]) * t + e.ny - z + 3], nx: e.nx, ny: e.ny, k: i * 13 + j });
      }
    });
    return out.sort(function (a, b) { return a.p[1] - b.p[1]; });
  }
  /** 叶面墙顶：散布的叶纹 + 银花点 */
  function leafTop(ctx, pts, n) {
    var d = '', dots = '';
    B.scatter(ctx, pts, n, 4).forEach(function (p, i) {
      d += 'M' + f(p[0] - 2) + ' ' + f(p[1]) + 'q2 -2.6 4 0';
      if (i % 3 === 0) dots += C.ell(p[0] + 3, p[1] + 1, 1.1, 1.1, P.silver, 0.5);
    });
    return line(d, 0.7, 0.45) + dots;
  }

  /** 荆棘棱垒（fort，2×2）：与藤墙同高同厚的墙带 + 朝外五边形垒身；侧翼与棱面外缘一圈外挑弯刺，垒顶荆棘丛与银桩小望台 */
  function thornBastion(ctx, dir) {
    var g = B.outline(dir, 2, SHAPE[dir.length === 2 ? 'd' : 'o']), es = K.edgesOf(g.pts, g.kinds), s = '';
    s += B.shadow(g.pts, 6, 4, 0.16);
    var th = thornSpots(g, es, { flank: 1, face: 1 }, 7, H);
    var draw = function (t) { return thorn(t.p, t.nx, t.ny, 12 + (t.k * 7) % 6, 4.6, t.k); };
    th.filter(function (t) { return t.ny <= 0.02; }).forEach(function (t) { s += draw(t); });
    s += B.solid(ctx, g.pts, g.kinds, 0, H, { face: P.bark2, top: P.leaf, tex: E.weave, topTex: function (top) { return leafTop(ctx, top, 16); } });
    s += E.rims(es, H);
    // 垒顶：尖角处一丛银刺、两肩荆棘丛、中央银桩小望台（叶顶）
    var tip = B.lift([g.pts[4]], H)[0], sl = B.lift([g.pts[3]], H)[0], sr = B.lift([g.pts[5]], H)[0];
    var tc = B.lift([g.P(sh(dir).tip - 14, 0)], H)[0], cc = g.P(sh(dir).root + 8, 0);
    s += path('M' + f(tc[0] - 8) + ' ' + f(tc[1] + 2) + 'l3 -10l2 8l3 -13l2 13l3 -9l2 11Z', P.silver2, 0.9);
    [sl, sr].forEach(function (q, i) {
      var c = [q[0] + (cc[0] - q[0]) * 0.3, q[1] + (cc[1] - H - q[1]) * 0.3];
      s += C.ell(c[0], c[1], 8, 5.4, P.leaf2, 1.1) + C.ell(c[0] - 1.5, c[1] - 1.5, 5, 3.2, P.moss, 0.8) +
        path('M' + f(c[0] - 5) + ' ' + f(c[1] - 2) + 'l2 -6l1.5 5l2 -7l1.5 7l2 -5l1 6Z', P.silver2, 0.7) + E.post(c[0] + (i ? -3 : 3), c[1] + 3, 7, 3);
    });
    s += E.post(cc[0], cc[1] - H + 2, 30, 4.2) + E.platform(ctx, cc[0], cc[1], 10, 6, H + 30, 3, 5);
    s += path('M' + f(cc[0] - 13) + ' ' + f(cc[1] - H - 36) + 'Q' + f(cc[0]) + ' ' + f(cc[1] - H - 52) + ' ' + f(cc[0] + 13) + ' ' + f(cc[1] - H - 36) +
      'Q' + f(cc[0]) + ' ' + f(cc[1] - H - 40) + ' ' + f(cc[0] - 13) + ' ' + f(cc[1] - H - 36) + 'Z', P.leaf2, 1.2) +
      line('M' + f(cc[0] - 7) + ' ' + f(cc[1] - H - 41) + 'q3 -3 6 -1M' + f(cc[0] + 1) + ' ' + f(cc[1] - H - 44) + 'q3 -2 5 1', 0.7, 0.5);
    ctx.top(cc[1] - H - 54);
    th.filter(function (t) { return t.ny > 0.02; }).forEach(function (t) { s += draw(t); });
    ctx.top(tip[1] - 20);
    return s;
  }
  function sh(dir) { return SHAPE[dir.length === 2 ? 'd' : 'o']; }

  // ---------- 树冠要塞（landmark，6×6） ----------
  /** 藤桥：A→B 下垂 sag，两道藤索 + 木板 + 叶片 */
  function vineBridge(A, B, sag) {
    var m = [(A[0] + B[0]) / 2, (A[1] + B[1]) / 2 + sag], d = 'M' + f(A[0]) + ' ' + f(A[1]) + 'Q' + f(m[0]) + ' ' + f(m[1]) + ' ' + f(B[0]) + ' ' + f(B[1]);
    var hi = 'M' + f(A[0]) + ' ' + f(A[1] - 7) + 'Q' + f(m[0]) + ' ' + f(m[1] - 7) + ' ' + f(B[0]) + ' ' + f(B[1] - 7), pl = '', lv = '', n = 12;
    for (var i = 1; i < n; i++) {
      var t = i / n, x = (1 - t) * (1 - t) * A[0] + 2 * t * (1 - t) * m[0] + t * t * B[0], y = (1 - t) * (1 - t) * A[1] + 2 * t * (1 - t) * m[1] + t * t * B[1];
      pl += 'M' + f(x - 0.6) + ' ' + f(y - 2) + 'l1.2 4';
      if (i % 3 === 1) lv += C.ell(x, y + 3, 2.4, 1.4, i % 2 ? P.leaf : P.leaf2, 0.6) + line('M' + f(x) + ' ' + f(y) + 'V' + f(y - 7), 0.7, 0.6);
    }
    return line(d, 4.2, 1) + line(d, 2.6, 1, P.wood) + line(pl, 1, 0.6) + line(hi, 1.6, 1) + line(hi, 0.8, 1, P.leaf2) + lv;
  }
  /** 树屋：底中心 (x, yb)，宽 w：银木墙 + 拱门 + 叶片圆顶 */
  function pod(x, yb, w) {
    var h = w * 0.55, s = path('M' + f(x - w / 2) + ' ' + f(yb) + 'V' + f(yb - h) + 'H' + f(x + w / 2) + 'V' + f(yb) + 'Z', P.silver, 1.2);
    s += rect2(x + w * 0.15, yb - h, w * 0.35, h, P.silver3, 0.5);
    s += path('M' + f(x - w * 0.14) + ' ' + f(yb) + 'V' + f(yb - h * 0.5) + 'Q' + f(x) + ' ' + f(yb - h * 0.85) + ' ' + f(x + w * 0.14) + ' ' + f(yb - h * 0.5) + 'V' + f(yb) + 'Z', P.hole, 0.8);
    s += path('M' + f(x - w * 0.62) + ' ' + f(yb - h + 2) + 'Q' + f(x - w * 0.5) + ' ' + f(yb - h - w * 0.75) + ' ' + f(x) + ' ' + f(yb - h - w * 0.82) +
      'Q' + f(x + w * 0.5) + ' ' + f(yb - h - w * 0.75) + ' ' + f(x + w * 0.62) + ' ' + f(yb - h + 2) + 'Q' + f(x) + ' ' + f(yb - h - 3) + ' ' + f(x - w * 0.62) + ' ' + f(yb - h + 2) + 'Z', P.leaf, 1.3);
    s += path('M' + f(x) + ' ' + f(yb - h - w * 0.82) + 'Q' + f(x + w * 0.5) + ' ' + f(yb - h - w * 0.75) + ' ' + f(x + w * 0.62) + ' ' + f(yb - h + 2) + 'Q' + f(x + w * 0.3) + ' ' + f(yb - h - 1) + ' ' + f(x + w * 0.1) + ' ' + f(yb - h - 2) + 'Z', P.leaf2, 0, 0.7);
    s += line('M' + f(x - w * 0.35) + ' ' + f(yb - h - w * 0.2) + 'q' + f(w * 0.2) + ' ' + f(-w * 0.2) + ' ' + f(w * 0.4) + ' 0M' + f(x - w * 0.15) + ' ' + f(yb - h - w * 0.5) + 'q' + f(w * 0.2) + ' ' + f(-w * 0.15) + ' ' + f(w * 0.35) + ' 0', 0.7, 0.5);
    return s + E.post(x, yb - h - w * 0.8, 4, 2.4);
  }
  function rect2(x, y, w, h, c, op) { return path('M' + f(x) + ' ' + f(y) + 'h' + f(w) + 'v' + f(h) + 'h' + f(-w) + 'Z', c, 0, op); }
  /** 粗根：从树干脚 (x, yb) 向 dir 侧伸出 */
  function roots(x, yb, w) {
    var d = '';
    [[-1, 0.9], [-0.5, 1.2], [0.4, 1.3], [1, 0.8]].forEach(function (r) {
      d += 'M' + f(x + r[0] * w * 0.35) + ' ' + f(yb - 6) + 'Q' + f(x + r[0] * w * 0.7) + ' ' + f(yb - 2) + ' ' + f(x + r[0] * w * (0.75 + r[1] * 0.3)) + ' ' + f(yb + 2 * r[1]);
    });
    return line(d, 6, 1) + line(d, 4, 1, P.bark2);
  }
  /** 一棵树的一段：树干 + 若干环台（由下往上画，树干穿过环台），返回串 */
  function tree(ctx, x, gy, z0, w, decks, topZ, lean) {
    var s = '', z = z0;
    decks.forEach(function (dk) {
      s += E.trunk(x, gy - z, w, dk.z - z, 0);
      s += E.platform(ctx, x, gy, dk.rx, dk.ry, dk.z, dk.t || 5, dk.rail == null ? 7 : dk.rail);
      (dk.pods || []).forEach(function (pd) { s += pod(x + pd[0], gy - dk.z + pd[1], pd[2]); });
      z = dk.z; w *= 0.82;
    });
    s += E.trunk(x, gy - z, w, topZ - z, lean || 0);
    return s;
  }
  /** 树冠要塞（landmark，6×6）：荆棘藤墙围起的八角台基 + 中央古树三层环台 + 左右两株卫树（各一层环台、树屋）+ 藤桥 + 前门楼 */
  function fortress(ctx) {
    var s = '', base = K.octo(144, -142, 128, 0.42), es = K.edgesOf(base), Z = 30;
    s += B.shadow(base, 8, 5, 0.16) + C.shadow('M200 -60L282 -40L282 -150L230 -170Z', 0.12);
    s += B.solid(ctx, base, null, 0, Z, { face: P.bark2, top: P.moss, tex: E.weave, topTex: function (top) { return leafTop(ctx, top, 46); } });
    s += E.rims(es, Z);
    // 台基顶上的根须与小径
    s += path('M126 ' + f(-14 - Z) + 'Q132 ' + f(-70 - Z) + ' 136 ' + f(-150 - Z) + 'L152 ' + f(-150 - Z) + 'Q156 ' + f(-70 - Z) + ' 162 ' + f(-14 - Z) + 'Z', P.stone2, 1, 0.9);
    s += line('M130 ' + f(-40 - Z) + 'h28M133 ' + f(-80 - Z) + 'h22M135 ' + f(-120 - Z) + 'h18', 0.8, 0.5);
    // 第一轮截图：台基前半是一片空苔地，补月光池（左）+ 银桩灌木丛（右）+ 几块苔石
    s += C.ell(68, -66 - Z, 26, 13, P.stone2, 1.4) + C.ell(68, -67 - Z, 21, 10, '#a9b8ad', 1) + line('M54 ' + f(-68 - Z) + 'q6 -2 12 0M70 ' + f(-63 - Z) + 'q6 -2 12 0', 0.8, 0.5) +
      C.ell(62, -69 - Z, 3, 1.4, P.moon, 0) + E.post(44, -62 - Z, 12, 3) + E.post(92, -62 - Z, 12, 3);
    s += E.crown(ctx, 222, -64 - Z, 18, 10) + E.post(208, -56 - Z, 10, 3) + E.post(236, -56 - Z, 10, 3);
    s += C.ell(100, -40 - Z, 4, 2.4, P.stone3, 0.9) + C.ell(190, -36 - Z, 5, 2.8, P.stone3, 0.9) + C.ell(240, -110 - Z, 4, 2.2, P.moss, 0.8);
    var MX = 144, MY = -168, LX = 52, RX = 236, SY = -150;
    // 中央古树
    s += roots(MX, MY - Z, 40);
    s += tree(ctx, MX, MY, Z, 36, [
      { z: 92, rx: 62, ry: 32, pods: [[-38, -6, 18], [36, -8, 16]] },
      { z: 146, rx: 46, ry: 25, pods: [[26, -4, 15]] },
      { z: 192, rx: 32, ry: 18, rail: 6 }], 226, 0);
    s += line('M144 ' + f(MY - 214) + 'q-26 -8 -40 -26M146 ' + f(MY - 220) + 'q24 -6 40 -24M144 ' + f(MY - 210) + 'q-8 -16 -6 -32', 5, 1) +
      line('M144 ' + f(MY - 214) + 'q-26 -8 -40 -26M146 ' + f(MY - 220) + 'q24 -6 40 -24M144 ' + f(MY - 210) + 'q-8 -16 -6 -32', 3, 1, P.bark2);
    s += E.crown(ctx, 104, MY - 246, 40, 24) + E.crown(ctx, 186, MY - 244, 40, 24) + E.crown(ctx, 144, MY - 262, 58, 32);
    // 两株卫树
    [[LX, -1], [RX, 1]].forEach(function (t) {
      s += roots(t[0], SY - Z, 22);
      s += tree(ctx, t[0], SY, Z, 20, [{ z: 104, rx: 30, ry: 17, pods: [[t[1] * -4, -4, 16]] }], 150, t[1] * 2);
      s += E.crown(ctx, t[0] + t[1] * 2, SY - 168, 34, 22);
    });
    // 藤桥：卫树环台 → 古树一层环台；古树二层 → 卫树树冠下
    s += vineBridge([LX + 28, SY - 104 - 2], [MX - 58, MY - 92 + 4], 14) + vineBridge([RX - 28, SY - 104 - 2], [MX + 58, MY - 92 + 4], 14);
    s += vineBridge([MX - 44, MY - 146 + 2], [LX + 16, SY - 150], 10) + vineBridge([MX + 44, MY - 146 + 2], [RX - 16, SY - 150], 10);
    s += E.ladder(MX + 22, MY - 92 + 6, MY - Z - 2, 7);
    // 前门楼：两座荆棘墩 + 活枝拱 + 银门
    s += gatehouse(ctx);
    return s;
  }
  function gatehouse(ctx) {
    var s = '', Z = 30;
    [[102, -40, 128, -10], [160, -40, 186, -10]].forEach(function (r) {
      var pts = [[r[0], r[1]], [r[2], r[1]], [r[2], r[3]], [r[0], r[3]]];
      s += K.prism(ctx, pts, 0, Z + 26, { face: P.bark2, top: P.leaf, tex: E.weave });
      s += E.rims(K.edgesOf(pts), Z + 26) + E.post(r[0] + 3, r[3] - 0.5, Z + 26) + E.post(r[2] - 3, r[3] - 0.5, Z + 26);
    });
    // 门洞（台基正面上）+ 银木门
    s += path('M130 -12V-40Q144 -58 158 -40V-12Z', P.hole, 1.4) + path('M133 -12V-39Q144 -53 155 -39V-12Z', P.silver2, 1.1);
    s += line('M144 -12V-50M134 -26H154M134 -36H154', 0.9, 0.7) + C.ell(140, -24, 1.2, 1.2, P.ink, 0) + C.ell(148, -24, 1.2, 1.2, P.ink, 0);
    // 活枝拱
    var arc = 'M114 -96Q114 -126 144 -130Q174 -126 174 -96';
    s += line(arc, 7, 1) + line(arc, 4.6, 1, P.bark2) + E.crown(ctx, 144, -130, 22, 12);
    s += path('M136 -112l2 -7l2 6l2 -9l2 9l2 -6l2 7Z', P.silver2, 0.7) + C.ell(144, -104, 3, 3.4, P.moon, 1) + C.ell(144, -104, 1.4, 1.6, '#f3eccf', 0);
    return s;
  }

  function types() {
    var out = [];
    K.DIRS.forEach(function (d) {
      out.push({ id: 'west-elf-thornbastion-' + d, race: 'elf', category: 'fort', kind: 'thorn_bastion', facility: 'watchtower', fp: [2, 2], roof: 'none',
        tags: ['bastion', 'point_' + d, 'replaces_wall_cells', 'thorns', 'attach_' + B.THRU[d].join('_')],
        attach: B.attachCells(d, 2), thru: B.THRU[d],
        note: '荆棘棱垒（2×2）：尖角朝 ' + d + '；编藤墙带与藤墙同高同厚，两端切在' + (d.length === 1 ? '格边中点' : '格角') + '，接同族 wallspoke-' + B.THRU[d].join(' / ') +
          '；垒身外缘一圈外挑银尖弯刺，顶上荆棘丛 + 银桩叶顶小望台。放置时替掉 attach 墙格的辐条与节点。facility 无棱堡专项，取 watchtower',
        draw: function (ctx) { return thornBastion(ctx, d); } });
    });
    out.push({ id: 'west-elf-fortress-01', race: 'elf', category: 'landmark', kind: 'canopy_fortress', facility: 'barracks', fp: [6, 6], roof: 'none', culture: 'elf',
      tags: ['landmark', 'fortress', 'tree', 'ring_decks', 'vine_bridge'],
      note: '树冠要塞（6×6）：荆棘藤墙八角台基 + 中央古树三层环台 + 左右卫树树屋 + 四道藤桥 + 活枝拱前门。facility 取最接近的 barracks（驻军要塞）',
      draw: fortress });
    return out;
  }
  var API = { types: types, thornBastion: thornBastion, fortress: fortress, thorn: thorn, vineBridge: vineBridge, pod: pod, SHAPE: SHAPE };
  root.TownArtRF2_elf = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
