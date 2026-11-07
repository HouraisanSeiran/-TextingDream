/*
 * 织梦 · race-fort 兽人族：尖木栅墙辐条 + 角柱节点 + 图腾瞭望塔 + 尖桩土垒（美术样板，尚未接入游戏）
 * 照 west-orc/tiles.js：桩高 33 + DH 起伏（周期 12 根）、桩宽 4.8（南北向正视 6.6）、桩距 4、两道绳扎（离地 12 / 24.5）、
 * 墙段中挂头骨、土垄底色 soil2 × 0.42、角柱宽 7 高 40 + 绳结 + 一对短角。
 * 桩按「本格内 x、y」取序号，周期 48 整除，所以相邻格对接处节奏一致。
 * 辐条的格边 / 格角那根桩只归正方向一侧（e / s / se / sw）画，另一侧不画，避免重桩。
 * 浏览器挂 window.TownArtRF_orc；Node 用 module.exports。依赖 core.js、spoke.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtRF_core;
  var K = isNode ? require('./spoke.js') : root.TownArtRF_spoke;
  var P = C.P, f = C.f, line = C.line, path = C.path, rect = C.rect, H = 33, STEP = 4, SW_ = 4.8;
  var DH = [0, 2, -1, 1, 3, -2, 1, 0, 2, -1, 3, 0];
  var TONE = [P.wood, '#bf9a60', '#b48e58', P.wood, '#b48e58', '#c4a068'];
  var OWN_END = { e: 1, s: 1, se: 1, sw: 1 };

  function stake(x, yb, w, h, fill, sw) {
    var d = 'M' + f(x) + ' ' + f(yb) + 'V' + f(yb - h) + 'L' + f(x + w * 0.5) + ' ' + f(yb - h - w * 1.1) + 'L' + f(x + w) + ' ' + f(yb - h) + 'V' + f(yb) + 'Z';
    return path(d, fill || P.wood, sw == null ? 1 : sw) + line('M' + f(x + w * 0.62) + ' ' + f(yb - 2) + 'V' + f(yb - h * 0.7), 0.6, 0.45);
  }
  function knot(x, y, w, n) {
    var d = '';
    for (var i = 0; i < (n || 3); i++) d += 'M' + f(x - w / 2 - 0.3) + ' ' + f(y + i * 1.7) + 'l' + f(w + 0.6) + ' -1.3';
    return line(d, 1.7, 1) + line(d, 0.8, 1, P.rope);
  }
  function rope(d) { return line(d, 1.6, 1) + line(d, 0.7, 1, P.rope); }
  function skull(x, y, s) {
    s = s || 1;
    var d = 'M' + f(x - 4 * s) + ' ' + f(y + s) + 'C' + f(x - 4.2 * s) + ' ' + f(y - 4.6 * s) + ' ' + f(x + 4.2 * s) + ' ' + f(y - 4.6 * s) + ' ' + f(x + 4 * s) + ' ' + f(y + s) +
      'L' + f(x + 3 * s) + ' ' + f(y + 3.2 * s) + 'L' + f(x + 2.2 * s) + ' ' + f(y + 5.4 * s) + 'L' + f(x - 2.2 * s) + ' ' + f(y + 5.4 * s) + 'L' + f(x - 3 * s) + ' ' + f(y + 3.2 * s) + 'Z';
    return path(d, P.bone, 0.9) + C.ell(x - 1.6 * s, y + 1.3 * s, 1.15 * s, 1.25 * s, P.hole, 0) + C.ell(x + 1.6 * s, y + 1.3 * s, 1.15 * s, 1.25 * s, P.hole, 0) +
      path('M' + f(x) + ' ' + f(y + 2.6 * s) + 'l' + f(-0.6 * s) + ' ' + f(1.2 * s) + 'h' + f(1.2 * s) + 'Z', P.hole, 0);
  }
  function horn(x, y, len, dir) {
    var tx = x + dir * len, ty = y - len * 0.7;
    return path('M' + f(x) + ' ' + f(y - 1.6) + 'Q' + f(x + dir * len * 0.85) + ' ' + f(y - 1) + ' ' + f(tx) + ' ' + f(ty) +
      'Q' + f(x + dir * len * 0.7) + ' ' + f(y + 2.2) + ' ' + f(x) + ' ' + f(y + 1.8) + 'Z', P.bone2, 0.9);
  }
  function hornSkull(x, y, s, len) { return horn(x - 3 * s, y - 0.5 * s, len, -1) + horn(x + 3 * s, y - 0.5 * s, len, 1) + skull(x, y, s); }
  function seq(x, y) { return (((Math.round(x / STEP) + Math.round(y / STEP) * 5) % 12) + 12) % 12; }
  /** 一根墙桩：底中心 (x, yb)；vert = 南北向正视（更宽、左亮右暗） */
  function wallStake(x, yb, vert) {
    var k = seq(x, yb), h = H + DH[k], w = vert ? 6.6 : SW_;
    var s = stake(x - w / 2, yb, w, h, TONE[k % TONE.length], 1);
    if (vert) s += path(C.poly([[x + 0.3, yb - 0.6], [x + 0.3, yb - h], [x + w * 0.42, yb - h + 0.4], [x + w * 0.42, yb - 0.6]]), P.dark, 0, 0.3);
    else s += rect(x + w * 0.18, yb - h + 0.6, w * 0.32 - 0.4, h - 1.2, P.dark, 0, 0.22);
    return s;
  }
  /** 角柱（墙节点）：更粗更高，绳扎 + 一对短角；v=2 顶上插长角兽头骨 */
  function cornerPost(ctx, x, yb, v) {
    var w = 7, h = H + 7, s = stake(x - w / 2, yb, w, h, P.timber, 1.3);
    s += rect(x + 0.6, yb - h + 0.6, w / 2 - 1, h - 1.2, P.dark, 0, 0.25) + knot(x, yb - h * 0.62, w, 3) + knot(x, yb - 9, w, 2);
    if (v === 2) { s += hornSkull(x, yb - h - w * 1.1 - 2, 0.62, 8); ctx.top(yb - h - w * 1.1 - 14); }
    else { s += horn(x - 2, yb - h + 2, 5, -1) + horn(x + 2, yb - h + 2, 5, 1); ctx.top(yb - h - w * 1.1 - 5); }
    return s;
  }

  // ---------- 辐条 / 节点 ----------
  var VEC = { n: [0, -1], ne: [1, -1], e: [1, 0], se: [1, 1], s: [0, 1], sw: [-1, 1], w: [-1, 0], nw: [-1, -1] };
  /** 辐条上的桩位：从格中心外 4 px 起每 4 px 一根，到端头；端头那根只归 OWN_END 方向 */
  function stakePts(dir) {
    var v = VEC[dir], out = [], last = OWN_END[dir] ? 24 : 20;
    for (var t = 4; t <= last; t += STEP) out.push([24 + v[0] * t, -24 + v[1] * t]);
    return out;
  }
  function spoke(ctx, dir) {
    var g = K.spokeGeom(dir), v = VEC[dir], pts = stakePts(dir), vert = v[0] === 0, s = '';
    var a = [24 + v[0] * 2, -24 + v[1] * 2], b = [24 + v[0] * 24, -24 + v[1] * 24];
    // 地面：土垄（同 west-orc 的 soil2 × 0.42）+ 几块石头
    s += path(C.poly(g.pts), P.soil2, 0, 0.42);
    [8, 17].forEach(function (t, i) { var q = [24 + v[0] * t + (vert ? 6 : 0), -24 + v[1] * t + (vert ? 0 : 7) - i]; s += C.ell(q[0], q[1], 1.6, 1.1, P.stone2, 0.6); });
    // 投影：桩列右下方一窄条
    var o1 = vert ? [2.4, 0] : (v[1] === 0 ? [2, 0] : [2.4, 0]), o2 = vert ? [7.9, 0] : (v[1] === 0 ? [2, 4.5] : [7, 3.5]);
    s += C.shadow(C.poly([[a[0] + o1[0], a[1] + o1[1]], [b[0] + o1[0], b[1] + o1[1]], [b[0] + o2[0], b[1] + o2[1]], [a[0] + o2[0], a[1] + o2[1]]]));
    pts.sort(function (p, q) { return p[1] - q[1] || p[0] - q[0]; });
    pts.forEach(function (p) {
      s += wallStake(p[0], p[1], vert);
      if (vert && seq(p[0], p[1]) % 3 === 0) s += knot(p[0], p[1] - 14, 6.6, 1);
    });
    if (!vert) { // 两道绳扎，沿桩列（斜段随桩脚斜下）
      var p0 = pts[0], p1 = pts[pts.length - 1], ext = OWN_END[dir] ? 1 : 2;
      [12, 24.5].forEach(function (z) {
        s += rope('M' + f(p0[0] - v[0] * 2) + ' ' + f(p0[1] - v[1] * 2 - z) + 'L' + f(p1[0] + v[0] * ext) + ' ' + f(p1[1] + v[1] * ext - z));
      });
      if (OWN_END[dir]) { var sk = [24 + v[0] * 16, -24 + v[1] * 16]; s += skull(sk[0], sk[1] - 21.5, 0.6); }
    }
    ctx.top(Math.min.apply(null, pts.map(function (p) { return p[1]; })) - H - 3 - SW_ * 1.1 - 1);
    return s;
  }
  /** 墙节点：夯土小墩 + 角柱；v=1 一对短角，v=2 长角兽头骨 + 一圈碎骨 */
  function node(ctx, v) {
    var s = C.ell(24, -24, 13, 9, P.soil2, 0, 0.42) + C.ell(24, -23, 9, 6, P.soil, 1, 0.9) + C.shadow('M27 -24l8 1l2 4l-8 0Z');
    if (v === 2) s += C.ell(17, -19, 2.2, 1.2, P.bone2, 0.6) + C.ell(31, -20, 1.8, 1, P.bone, 0.6) + line('M14 -22l3 1M32 -26l3 -1', 1.4, 1, P.bone2);
    return s + cornerPost(ctx, 24, -23, v);
  }
  var NODE_NOTES = { 1: '角柱：粗原木 + 绳扎 + 一对短角（同 west-orc 瓦片 SW 角柱）', 2: '骨柱：角柱顶插长角兽头骨，脚下散碎骨' };

  /** 战旗：杆底 (x, yb)，高 h，红兽皮旗 + 骨纹 + 杆顶小头骨 */
  function banner(x, yb, h, dir) {
    dir = dir || 1;
    var ty = yb - h, bw = 9, bh = 15, s = line('M' + f(x) + ' ' + f(yb) + 'V' + f(ty), 1.6) + line('M' + f(x - 0.4) + ' ' + f(yb) + 'V' + f(ty), 0.8, 1, P.timber);
    s += line('M' + f(x - 3) + ' ' + f(ty + 2) + 'H' + f(x + dir * (bw + 2)), 1.4);
    s += path('M' + f(x) + ' ' + f(ty + 2) + 'H' + f(x + dir * bw) + 'V' + f(ty + 2 + bh) + 'L' + f(x + dir * bw / 2) + ' ' + f(ty + bh - 2) + 'L' + f(x) + ' ' + f(ty + 2 + bh) + 'Z', P.rust, 1.1);
    var cx = x + dir * bw / 2;
    s += line('M' + f(cx - 2) + ' ' + f(ty + 6) + 'l0.8 5M' + f(cx) + ' ' + f(ty + 5.5) + 'v5.6M' + f(cx + 2) + ' ' + f(ty + 6) + 'l-0.8 5', 1, 1, P.bone);
    return s + skull(x, ty - 1.5, 0.45);
  }
  /** 图腾瞭望塔（替代 wallnode）：四根斜撑原木 + 刻面图腾柱 + 兽皮顶瞭望台 + 长角头骨 */
  function totemTower(ctx) {
    var s = C.ell(24, -24, 14, 9, P.soil2, 0, 0.42) + C.shadow('M30 -22l14 3l3 -8l-12 -3Z', 0.16), Z = 64;
    // 后两根撑木
    s += line('M13 -34L19 ' + f(-24 - Z), 4.2) + line('M13 -34L19 ' + f(-24 - Z), 2.6, 1, P.timber);
    s += line('M35 -34L29 ' + f(-24 - Z), 4.2) + line('M35 -34L29 ' + f(-24 - Z), 2.6, 1, P.timber);
    // 图腾柱：三段刻面兽首
    var cols = [P.wood, '#b48e58', P.hide3];
    for (var i = 0; i < 4; i++) {
      var y1 = -20 - i * 15, y0 = y1 - 15;
      s += rect(19, y0, 10, 15, cols[i % 3], 1.2) + rect(25, y0 + 0.6, 3.4, 13.8, P.dark, 0, 0.25);
      s += C.ell(21.8, y0 + 5, 1.3, 1.1, P.hole, 0) + C.ell(26.2, y0 + 5, 1.3, 1.1, P.hole, 0) +
        path('M20.5 ' + f(y0 + 9) + 'h7l-1 3h-5Z', P.hole, 0.6) + path('M21.5 ' + f(y0 + 9) + 'l0.7 2l0.7 -2M25 ' + f(y0 + 9) + 'l0.7 2l0.7 -2', P.bone, 0.4) +
        line('M19 ' + f(y0 + 2.5) + 'h10', 0.8, 0.55);
    }
    // 前两根撑木 + 绳扎横档
    s += line('M8 -16L18 ' + f(-24 - Z + 4), 4.6) + line('M8 -16L18 ' + f(-24 - Z + 4), 3, 1, P.wood);
    s += line('M40 -16L30 ' + f(-24 - Z + 4), 4.6) + line('M40 -16L30 ' + f(-24 - Z + 4), 3, 1, '#b48e58');
    s += rope('M12 -42H36') + knot(12, -43, 3, 2) + knot(36, -43, 3, 2);
    // 瞭望台：圆木台 + 一圈小尖桩 + 兽皮斜顶
    var ty = -24 - Z;
    s += K.prism(ctx, K.octo(24, -24, 17, 0.4), Z - 4, 4, { face: P.timber, top: P.wood, sw: 1.4 });
    for (var x = 9; x <= 39; x += 4) s += stake(x - 1.6, ty + 9 - Math.abs(x - 24) * 0.12, 3.2, 9 + DH[(x / 4 | 0) % 12] * 0.5, TONE[(x / 4 | 0) % TONE.length], 0.8);
    s += line('M12 ' + f(ty + 4) + 'V' + f(ty - 16) + 'M36 ' + f(ty + 4) + 'V' + f(ty - 16), 1.8);
    s += path('M5 ' + f(ty - 12) + 'L24 ' + f(ty - 30) + 'L43 ' + f(ty - 12) + 'L38 ' + f(ty - 9) + 'L30 ' + f(ty - 13) + 'L22 ' + f(ty - 9) + 'L14 ' + f(ty - 13) + 'Z', P.hide, 1.5);
    s += path('M24 ' + f(ty - 30) + 'L43 ' + f(ty - 12) + 'L38 ' + f(ty - 9) + 'L30 ' + f(ty - 13) + 'Z', P.hide2, 0, 0.45) + line('M15 ' + f(ty - 17) + 'l4 -3M28 ' + f(ty - 22) + 'l4 3', 0.8, 0.6);
    s += hornSkull(24, ty - 31, 0.7, 9);
    ctx.top(ty - 42);
    return s;
  }

  /** 尖角工事通用外形（2×2，格内坐标 0..96 / -96..0）：沿 dir 指向的五边形，底边朝城内接幕墙 */
  var U = { n: [0, -1], ne: [Math.SQRT1_2, -Math.SQRT1_2], e: [1, 0], se: [Math.SQRT1_2, Math.SQRT1_2], s: [0, 1], sw: [-Math.SQRT1_2, Math.SQRT1_2], w: [-1, 0], nw: [-Math.SQRT1_2, -Math.SQRT1_2] };
  function pent(dir, cx, cy, tip, sh, bw, back) {
    var u = U[dir], v = [-u[1], u[0]];
    var P2 = function (a, b) { return [Math.max(1, Math.min(cx * 2 - 1, cx + u[0] * a + v[0] * b)), Math.max(-cx * 2 + 1, Math.min(-1, cy + u[1] * a + v[1] * b))]; };
    return [P2(tip, 0), P2(sh, bw), P2(-back, bw * 0.8), P2(-back, -bw * 0.8), P2(sh, -bw)];
  }
  function shrink(pts, k) {
    var cx = 0, cy = 0; pts.forEach(function (p) { cx += p[0] / pts.length; cy += p[1] / pts.length; });
    return pts.map(function (p) { return [cx + (p[0] - cx) * k, cy + (p[1] - cy) * k]; });
  }
  /** 尖桩土垒（fort，2×2）：夯土坡两层 + 外缘一圈外斜尖桩 + 桩头头骨 + 中央战旗；底边（kinds=start）不插桩，接幕墙 */
  function earthwork(ctx, dir) {
    var pts = pent(dir, 48, -48, 44, 8, 38, 26), kinds = ['side', 'side', 'start', 'side', 'side'], s = '';
    s += C.shadow(C.poly(pts.map(function (p) { return [p[0] + 6, p[1] + 4]; })), 0.16);
    var Z1 = 9, es = K.edgesOf(pts, kinds), front = [], back = [];
    s += K.prism(ctx, pts, 0, Z1, { face: P.soil2, top: P.soil, sw: 1.6, tex: function (x0, x1, h) {
      var d = ''; for (var x = Math.floor(x0 / 7) * 7; x < x1; x += 7) d += 'M' + f(x) + ' -2l3 ' + f(-h + 4); return line(d, 0.7, 0.45);
    } }, kinds);
    es.forEach(function (e, ei) {
      if (e.kind !== 'side') return;
      var n = Math.max(2, Math.round(e.len / 7));
      for (var i = 0; i <= n; i++) {
        if (i === n && es[(ei + 1) % es.length].kind === 'side') continue; // 角上那根归下一条边
        var t = i / n, p = [e.A[0] + (e.B[0] - e.A[0]) * t - e.nx * 3, e.A[1] + (e.B[1] - e.A[1]) * t - e.ny * 3 - Z1];
        (e.ny > 0.05 ? front : back).push({ p: p, nx: e.nx, ny: e.ny, k: ei * 7 + i });
      }
    });
    function draw(st) {
      var p = st.p, len = 17 + DH[st.k % 12], q = [p[0] + st.nx * 9, p[1] + st.ny * 5 - len];
      var d = 'M' + f(p[0]) + ' ' + f(p[1]) + 'L' + f(q[0]) + ' ' + f(q[1]);
      var r = line(d, 4.6) + line(d, 2.9, 1, TONE[st.k % TONE.length]) + line('M' + f(q[0]) + ' ' + f(q[1]) + 'l' + f(-st.nx) + ' 2', 1.2, 1, '#f0e2bf');
      if (st.k % 5 === 2) r += skull(q[0], q[1] - 3, 0.55);
      ctx.top(q[1] - 7);
      return r;
    }
    back.sort(function (a, b) { return a.p[1] - b.p[1]; }); front.sort(function (a, b) { return a.p[1] - b.p[1]; });
    back.forEach(function (st) { s += draw(st); });
    var inner = shrink(pts, 0.62);
    s += K.prism(ctx, inner, Z1, 8, { face: P.soil2, top: P.soil, sw: 1.4 });
    var c = shrink(pts, 0.05)[0], cx = 0, cy = 0; pts.forEach(function (p) { cx += p[0] / 5; cy += p[1] / 5; });
    s += C.ell(cx - 6, cy - Z1 - 8 + 3, 2.4, 1.4, P.bone2, 0.6) + line('M' + f(cx + 4) + ' ' + f(cy - Z1 - 4) + 'l5 -1', 1.4, 1, P.bone2);
    s += banner(cx, cy - Z1 - 8, 40, U[dir][0] >= 0 ? 1 : -1);
    ctx.top(cy - Z1 - 8 - 46);
    front.forEach(function (st) { s += draw(st); });
    return s;
  }
  function types() {
    var out = [{ id: 'west-orc-walltower-01', race: 'orc', category: 'wall', kind: 'wall_tower_totem', facility: 'watchtower', fp: [1, 1], roof: 'monopitch',
      tags: ['node_tower', 'replaces_wallnode', 'totem', 'order_0.2'], sort: 0.2, note: '图腾瞭望塔：放在墙节点上替代 wallnode；四撑原木 + 刻面兽首图腾柱 + 尖桩围栏瞭望台 + 兽皮斜顶 + 长角头骨', draw: totemTower }];
    K.DIRS.forEach(function (d) {
      out.push({ id: 'west-orc-earthwork-' + d, race: 'orc', category: 'fort', kind: 'earthwork', facility: 'barracks', fp: [2, 2], roof: 'none',
        tags: ['earthwork', 'point_' + d, 'stakes', 'skull', 'banner'], note: '尖桩土垒：尖角朝 ' + d + '，夯土两层坡 + 外斜尖桩 + 头骨 + 战旗；底边朝城内接幕墙辐条。facility 无土垒专项，取 barracks', draw: function (ctx) { return earthwork(ctx, d); } });
    });
    return out;
  }
  var API = { H: H, NODE_NOTES: NODE_NOTES, types: types, spoke: spoke, node: node, totemTower: totemTower, earthwork: earthwork, pent: pent, shrink: shrink,
    stake: stake, skull: skull, hornSkull: hornSkull, banner: banner, rope: rope, knot: knot, wallStake: wallStake, cornerPost: cornerPost };
  root.TownArtRF_orc = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
