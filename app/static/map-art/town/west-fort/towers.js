/*
 * 织梦 · 西式防御工事 —— 节点角楼 nodetower-round / nodetower-octagon（放在墙节点上，替代 wallnode）
 * 局部坐标同 core.js；塔心在格中心 (24,-24)。投影：地面圆在高 z 处仍是圆，平移到 y - z。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWF.core;
  var G = isNode ? require('./geom.js') : root.TownArtWF.geom;
  var PAL = C.PAL, f = C.f, CX = 24, CY = -24;
  function circ(cx, cy, r) { return 'M' + f(cx - r) + ' ' + f(cy) + 'A' + f(r) + ' ' + f(r) + ' 0 1 0 ' + f(cx + r) + ' ' + f(cy) + 'A' + f(r) + ' ' + f(r) + ' 0 1 0 ' + f(cx - r) + ' ' + f(cy) + 'Z'; }
  function front(cx, cy, r, z) { return 'M' + f(cx - r) + ' ' + f(cy - z) + 'A' + f(r) + ' ' + f(r) + ' 0 0 0 ' + f(cx + r) + ' ' + f(cy - z); }
  /** 圆柱塔身：方石层 + 竖缝（按角度错缝），右侧背光 */
  function drum(ctx, cx, cy, r, z0, z1) {
    var body = 'M' + f(cx - r) + ' ' + f(cy - z1) + 'V' + f(cy - z0) + 'A' + f(r) + ' ' + f(r) + ' 0 0 0 ' + f(cx + r) + ' ' + f(cy - z0) + 'V' + f(cy - z1) + 'Z';
    var s = C.path(body, PAL.stone, 0), d = '', row = 0;
    s += G.clip(ctx, [[cx + r * 0.35, cy - z1 - r], [cx + r + 1, cy - z1 - r], [cx + r + 1, cy - z0 + r + 1], [cx + r * 0.35, cy - z0 + r + 1]], C.path(body, PAL.stone2, 0));
    for (var z = z0 + 8; z < z1 - 0.1; z += 8, row++) d += front(cx, cy, r, z);
    row = 0;
    for (z = z0; z < z1 - 0.1; z += 8, row++) for (var a = (row % 2) * 0.25 + 0.2; a < Math.PI; a += 0.5) {
      var x = cx - r * Math.cos(a), y = cy + r * Math.sin(a);
      d += C.seg([x, y - z], [x, y - Math.min(z1, z + 8)]);
    }
    s += C.lines(d, 0.8, 0.55) + C.path(front(cx, cy, r, z0 + 5), 'none', 0.9, 0.7);
    return s + C.path('M' + f(cx - r) + ' ' + f(cy - z1) + 'V' + f(cy - z0) + 'A' + f(r) + ' ' + f(r) + ' 0 0 0 ' + f(cx + r) + ' ' + f(cy - z0) + 'V' + f(cy - z1), 'none', 1.6);
  }
  /** 一圈垛口：沿圆周放小方块，后半圈先画 */
  function ring(cx, cy, r, z, n) {
    var list = [];
    for (var i = 0; i < n; i++) {
      var a = (i + 0.5) * 2 * Math.PI / n, a0 = a - 0.16, a1 = a + 0.16, ri = r - 3;
      var q = [[cx + r * Math.cos(a0), cy + r * Math.sin(a0)], [cx + r * Math.cos(a1), cy + r * Math.sin(a1)], [cx + ri * Math.cos(a1), cy + ri * Math.sin(a1)], [cx + ri * Math.cos(a0), cy + ri * Math.sin(a0)]];
      list.push({ y: Math.sin(a), s: G.block(q, z, z + 9) });
    }
    list.sort(function (p, q) { return p.y - q.y; });
    return list.map(function (x) { return x.s; }).join('');
  }
  function slit(x, y) { return C.poly([[x - 1, y], [x - 1, y - 7], [x + 1, y - 7], [x + 1, y]], PAL.hole, 0); }
  function flag(ctx, x, y) { ctx.top(y - 16); return C.path(C.seg([x, y], [x, y - 16]), 'none', 1.3) + C.path('M' + f(x) + ' ' + f(y - 16) + 'q5 1 9 3q-5 0.6 -9 3Z', PAL.red, 0.7); }
  /** 圆角楼：半径 17，塔身高 56，托石挑檐 + 一圈垛口 + 青石板锥顶 */
  function round(ctx) {
    var r = 17, z1 = 56, s = '';
    s += C.shadow(circ(CX + 5, CY + 4, r));
    s += drum(ctx, CX, CY, r, 0, z1);
    s += slit(CX - 6, CY + r - 18) + slit(CX + 5, CY + r - 36);
    // 托石挑檐：外扩 2 px 的一圈
    var R = r + 2, zc = z1;
    s += C.path(front(CX, CY, R, zc) + 'L' + f(CX + R) + ' ' + f(CY - zc - 5) + 'A' + f(R) + ' ' + f(R) + ' 0 0 1 ' + f(CX - R) + ' ' + f(CY - zc - 5) + 'Z', PAL.stone2, 1.2);
    var t = '';
    for (var a = 0.25; a < Math.PI; a += 0.35) { var x = CX - R * Math.cos(a), y = CY + R * Math.sin(a) - zc; t += C.seg([x, y], [x, y + 3]); }
    s += C.lines(t, 0.9, 0.7);
    s += C.path(circ(CX, CY - zc - 5, R), PAL.walk, 1.3);
    s += ring(CX, CY - 0, R, zc + 5, 12);
    // 锥顶
    var Rr = R - 2, zb = zc + 12, apex = [CX, CY - zb - 46];
    var cone = 'M' + f(CX - Rr) + ' ' + f(CY - zb) + 'A' + f(Rr) + ' ' + f(Rr * 0.45) + ' 0 0 0 ' + f(CX + Rr) + ' ' + f(CY - zb) + 'L' + C.P(apex[0], apex[1]) + 'Z';
    s += C.path(cone, PAL.slate, 0);
    s += C.path('M' + f(CX + 3) + ' ' + f(CY - zb + Rr * 0.45 - 0.5) + 'A' + f(Rr) + ' ' + f(Rr * 0.45) + ' 0 0 0 ' + f(CX + Rr) + ' ' + f(CY - zb) + 'L' + C.P(apex[0], apex[1]) + 'Z', PAL.slate2, 0);
    var rl = '';
    for (var k = 1; k < 5; k++) { var tt = k / 5, rr = Rr * (1 - tt), yy = CY - zb - 46 * tt; rl += 'M' + f(CX - rr) + ' ' + f(yy) + 'A' + f(rr) + ' ' + f(rr * 0.45) + ' 0 0 0 ' + f(CX + rr) + ' ' + f(yy); }
    s += C.lines(rl, 0.8, 0.5) + C.path(cone, 'none', 1.5);
    s += flag(ctx, apex[0], apex[1]);
    return s;
  }
  /** 八角楼：八边形棱柱高 60，四面垛口 + 顶上一座八角小望亭（青石板八角攒尖） */
  function octagon(ctx) {
    var r = 18, oct = [], i;
    for (i = 0; i < 8; i++) { var a = Math.PI / 8 + i * Math.PI / 4; oct.push([CX + r * Math.cos(a), CY + r * Math.sin(a)]); }
    var s = G.prism(ctx, oct, 60, oct.map(function () { return 'wall'; }), { mode: 'ortho' });
    s += slit(CX - 4, CY + 16 - 20) + slit(CX + 9, CY + 12 - 30);
    // 小望亭：八边形半径 9，高 14，攒尖顶
    var r2 = 9, oc2 = [];
    for (i = 0; i < 8; i++) { var b = Math.PI / 8 + i * Math.PI / 4; oc2.push([CX + r2 * Math.cos(b), CY - 2 + r2 * Math.sin(b)]); }
    // 望亭身只画 z 60..74：高 14 的棱柱整体上移 60
    s += '<g transform="translate(0 -60)">' + G.prism(ctx, oc2, 14, oc2.map(function () { return 'plain'; }), { mode: 'ortho', noShadow: true }) + '</g>';
    var top = G.lift(oc2, 74), ap = [CX, CY - 2 - 74 - 26], roof = '';
    top.forEach(function (p, j) {
      var q = top[(j + 1) % 8];
      if ((p[1] + q[1]) / 2 > CY - 2 - 74 - 0.5) { var fl = (p[0] + q[0]) / 2 > CX + 1 ? PAL.slate2 : PAL.slate; roof += C.poly([p, q, ap], fl, 1.2); }
    });
    s += C.poly([[CX - r2 - 1, CY - 2 - 74], [CX + r2 + 1, CY - 2 - 74], ap], PAL.slate, 0) + roof;
    s += flag(ctx, ap[0], ap[1]);
    return s;
  }
  function items() {
    return [
      { id: 'west-common-nodetower-round', fp: [1, 1], draw: round,
        meta: { category: 'wall', kind: 'node_tower_round', facility: 'watchtower', variant: 1, sort_offset: 0.2, roof: 'steep_slate', name: '节点圆角楼',
          tags: ['spoke_node', 'round_tower', 'cone_roof', 'machicolation'], note: '放在辐条墙节点上替代 wallnode（同格排序 +0.2）；直径 34 px 盖住墙带交叉方块，塔身 56 px，青石板锥顶' } },
      { id: 'west-common-nodetower-octagon', fp: [1, 1], draw: octagon,
        meta: { category: 'wall', kind: 'node_tower_octagon', facility: 'watchtower', variant: 2, sort_offset: 0.2, roof: 'steep_slate', name: '节点八角楼',
          tags: ['spoke_node', 'octagonal_tower', 'crenellated'], note: '八角形塔身 60 px 带垛口，顶上八角小望亭 + 青石板攒尖；适合斜段拐点' } }
    ];
  }
  var API = { circ: circ, front: front, drum: drum, ring: ring, flag: flag, round: round, octagon: octagon, items: items };
  if (isNode) module.exports = API;
  else root.TownArtWF.towers = API;
})(this);
