/*
 * 织梦 · 西式防御工事 —— 城墙辐条 wallspoke-<dir> 与墙节点 wallnode（第 11 节）
 * 局部坐标同 core.js：格 x 0..48，y -48..0；格中心 (24,-24)。墙厚 24（半厚 T = 12）、墙高 40，同 west-base。
 * 墙节点 = 格中心 28×28 墩子（高 46，比墙顶高 6，四面垛口）；半段墙从墩子边画到格边中点或格角。
 * 斜段在格角处的接法（保证墙带不在格角掐成一个点）：斜墙带只按「本行」裁剪（y 在 -48..0 之间），不按格左右裁。
 *   于是 se 半段终止在 y = 0 的一条横缝上（x 31..65），对角邻格的 nw 半段从同一条横缝开始，墙顶走道与垛口连续；
 *   格角旁边那个三角（属于正交邻格）由同一行的这半段补上，只向左右伸出 ≤ 17 px，不越过本行前沿，不破坏深度排序。
 *   斜段 symbol 因此左右各留 24 px 余量（padX），锚点仍是本格前沿中点。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWF.core;
  var G = isNode ? require('./geom.js') : root.TownArtWF.geom;
  var PAL = C.PAL, f = C.f;
  var T = 12, H = 40, PH = 44, Q = 12, S2 = T * Math.SQRT2;
  var X0 = 24 - Q, X1 = 24 + Q, Y0 = -24 - Q, Y1 = -24 + Q;   // 墩子 12..36 × -36..-12（= 墙带交叉方块）
  function mx(a) { return a.map(function (p) { return [48 - p[0], p[1]]; }).reverse(); }
  function mk(a) { var k = a.slice().reverse(); k.push(k.shift()); return k; }
  /** 方向 → [地面多边形, 每条边的类型, 走道缝模式, padX] */
  /** 按半厚 t（节点方块半边 = t）生成 8 向辐条轮廓；城堡幕墙、护城河辐条复用 */
  function makeShapes(t) {
    var x1 = 24 + t, y0 = -24 - t, y1 = -24 + t, s2 = t * Math.SQRT2, sh = {
      e: [[[x1, -24 - t], [48, -24 - t], [48, -24 + t], [x1, -24 + t]], ['wall', 'open', 'wall', 'pier'], 'ortho', 0],
      n: [[[24 - t, y0], [24 - t, -48], [24 + t, -48], [24 + t, y0]], ['wall', 'open', 'wall', 'pier'], 'ortho', 0],
      s: [[[24 - t, 0], [24 - t, y1], [24 + t, y1], [24 + t, 0]], ['wall', 'pier', 'wall', 'open'], 'ortho', 0],
      se: [[[48 - s2 + y1, y1], [48 - s2, 0], [48 + s2, 0], [x1, x1 - 48 - s2], [x1, y1]], ['wall', 'open', 'wall', 'pier', 'pier'], 'diag', 24],
      ne: [[[-s2 - y0, y0], [-s2 + 48, -48], [s2 + 48, -48], [x1, s2 - x1], [x1, y0]], ['wall', 'open', 'wall', 'pier', 'pier'], 'diag', 24]
    };
    sh.w = [mx(sh.e[0]), mk(sh.e[1]), 'ortho', 0];
    sh.sw = [mx(sh.se[0]), mk(sh.se[1]), 'diag', 24];
    sh.nw = [mx(sh.ne[0]), mk(sh.ne[1]), 'diag', 24];
    return sh;
  }
  function makePass(t) {
    var x0 = 24 - t, x1 = 24 + t, y0 = -24 - t, y1 = -24 + t, s2 = t * Math.SQRT2, p = {
      h: [[[x0, y0], [x1, y0], [x1, y1], [x0, y1]], ['wall', 'open', 'wall', 'open'], 'ortho', 'e-w'],
      v: [[[x0, y1], [x0, y0], [x1, y0], [x1, y1]], ['wall', 'open', 'wall', 'open'], 'ortho', 'n-s'],
      se: [[[x0, y0 + s2], [x0, y0], [x0 + s2, y0], [x1, y1 - s2], [x1, y1], [x1 - s2, y1]], ['open', 'open', 'wall', 'open', 'open', 'wall'], 'diag', 'nw-se']
    };
    p.ne = [mx(p.se[0]), mk(p.se[1]), 'diag', 'sw-ne'];
    return p;
  }
  var SHAPE = {
    e: [[[X1, -36], [48, -36], [48, -12], [X1, -12]], ['wall', 'open', 'wall', 'pier'], 'ortho', 0],
    n: [[[12, Y0], [12, -48], [36, -48], [36, Y0]], ['wall', 'open', 'wall', 'pier'], 'ortho', 0],
    s: [[[12, 0], [12, Y1], [36, Y1], [36, 0]], ['wall', 'pier', 'wall', 'open'], 'ortho', 0],
    // se：墙带 |x - y - 48| ≤ 12√2，裁到 y ≤ 0；内端贴墩子底边 / 右边
    se: [[[48 - S2 + Y1, Y1], [48 - S2, 0], [48 + S2, 0], [X1, X1 - 48 - S2], [X1, Y1]], ['wall', 'open', 'wall', 'pier', 'pier'], 'diag', 24],
    // ne：墙带 |x + y| ≤ 12√2，裁到 y ≥ -48；内端贴墩子顶边 / 右边
    ne: [[[-S2 - Y0, Y0], [-S2 + 48, -48], [S2 + 48, -48], [X1, S2 - X1], [X1, Y0]], ['wall', 'open', 'wall', 'pier', 'pier'], 'diag', 24]
  };
  SHAPE.w = [mx(SHAPE.e[0]), mk(SHAPE.e[1]), 'ortho', 0];
  SHAPE.sw = [mx(SHAPE.se[0]), mk(SHAPE.se[1]), 'diag', 24];
  SHAPE.nw = [mx(SHAPE.ne[0]), mk(SHAPE.ne[1]), 'diag', 24];
  var DIRS = ['n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw'];
  /** 同格排序偏移（第 11 节） */
  var ORDER = { n: 0.1, ne: 0.1, nw: 0.1, node: 0.2, e: 0.3, w: 0.3, s: 0.4, se: 0.4, sw: 0.4 };
  function spoke(ctx, dir, o) {
    o = o || {};
    var sh = SHAPE[dir];
    return G.prism(ctx, sh[0], o.h || H, sh[1], { mode: sh[2] });
  }
  function pier(ctx, o) {
    o = o || {};
    var q = [[X0, Y1], [X0, Y0], [X1, Y0], [X1, Y1]];
    return G.prism(ctx, q, o.h || PH, ['wall', 'wall', 'wall', 'wall'], { mode: 'ortho' });
  }
  /** 直通节点：墙格只有一对相对的辐条时用它代替墩子，墙顶走道与垛口连续不断 */
  var PASS = {
    h: [[[X0, Y0], [X1, Y0], [X1, Y1], [X0, Y1]], ['wall', 'open', 'wall', 'open'], 'ortho', 'e-w'],
    v: [[[X0, Y1], [X0, Y0], [X1, Y0], [X1, Y1]], ['wall', 'open', 'wall', 'open'], 'ortho', 'n-s']
  };
  // se 直通（nw–se）：方块 ∩ 墙带 |x - y - 48| ≤ 12√2；ne 直通（sw–ne）：方块 ∩ |x + y| ≤ 12√2
  PASS.se = [[[X0, Y0 + S2], [X0, Y0], [X0 + S2, Y0], [X1, Y1 - S2], [X1, Y1], [X1 - S2, Y1]], ['open', 'open', 'wall', 'open', 'open', 'wall'], 'diag', 'nw-se'];
  PASS.ne = [mx(PASS.se[0]), mk(PASS.se[1]), 'diag', 'sw-ne'];
  function pass(ctx, k) { var p = PASS[k]; return G.prism(ctx, p[0], H, p[1], { mode: p[2] }); }
  // —— 带小望台的节点：追加在下面 ——
  /** wallnode-02：墩子顶上一座木构小望台（四柱 + 栏杆 + 四坡红瓦小顶 + 小旗） */
  function lookout(ctx, o) {
    o = o || {};
    var h = o.h || PH, s = pier(ctx, o), z = h + 3, x0 = 14, x1 = 34, yb = -14, yt = -32, ph = 20;
    // 后排两柱
    s += C.path(C.seg([x0 + 1, yt - z], [x0 + 1, yt - z - ph]) + C.seg([x1 - 1, yt - z], [x1 - 1, yt - z - ph]), 'none', 2.2) ;
    // 木地板
    s += C.poly([[x0, yb - z], [x0, yt - z], [x1, yt - z], [x1, yb - z]], PAL.wood, 1.1) + C.lines(C.seg([x0, yb - z - 6], [x1, yb - z - 6]) + C.seg([x0, yb - z - 12], [x1, yb - z - 12]), 0.7, 0.5);
    s += C.poly([[x0, yb - z], [x1, yb - z], [x1, yb - z + 2.5], [x0, yb - z + 2.5]], PAL.timber, 0.9);
    // 前排两柱 + 栏杆
    s += C.path(C.seg([x0 + 1, yb - z], [x0 + 1, yb - z - ph]) + C.seg([x1 - 1, yb - z], [x1 - 1, yb - z - ph]), 'none', 2.2);
    s += C.path(C.seg([x0, yb - z - 7], [x1, yb - z - 7]), PAL.dark, 1.3) + C.lines(C.seg([19, yb - z], [19, yb - z - 7]) + C.seg([24, yb - z], [24, yb - z - 7]) + C.seg([29, yb - z], [29, yb - z - 7]), 0.9, 0.7);
    // 四坡小顶：屋脊在 (24, 中线)
    var ey = yb - z - ph, ry = yt - z - ph - 10, L = x0 - 4, R = x1 + 4;
    s += C.poly([[L, ey + 2], [24, ry + 6], [R, ey + 2]], PAL.tile, 1.5);
    s += C.poly([[24, ry + 6], [R, ey + 2], [R - 3, ey + 4]], '#9e5540', 0);
    s += C.lines(C.seg([L + 6, ey], [24, ry + 9]) + C.seg([L + 12, ey + 1], [24, ry + 11]) + C.seg([R - 6, ey], [24, ry + 9]) + C.seg([R - 12, ey + 1], [24, ry + 11]), 0.8, 0.5);
    s += C.path(C.seg([24, ry + 6], [24, ry - 8]), 'none', 1.2) + C.path('M24 ' + f(ry - 8) + 'q5 1 9 3q-5 0.6 -9 3Z', PAL.red, 0.7);
    ctx.top(ry - 10);
    return s;
  }
  var DNAME = { n: '北', ne: '东北', e: '东', se: '东南', s: '南', sw: '西南', w: '西', nw: '西北' };
  function items() {
    var out = DIRS.map(function (dir, k) {
      var diag = dir.length === 2;
      return {
        id: 'west-common-wallspoke-' + dir, fp: [1, 1], pad: SHAPE[dir][3],
        draw: function (ctx) { return spoke(ctx, dir); },
        meta: {
          category: 'wall', kind: 'wall_spoke', facility: 'city_wall', variant: k + 1, dir: dir, sort_offset: ORDER[dir],
          name: '城墙半段（' + DNAME[dir] + '）', tags: ['spoke', 'dir_' + dir, 'crenellated', diag ? 'diagonal' : 'orthogonal'],
          note: '辐条：从格中心墙节点画到' + (diag ? '格角（斜段只按本行裁剪，左右越出格边 ≤ 17 px，viewBox 带 pad_x = 24）' : '格边中点') +
            '。墙厚 24 px、高 40 px，同 west-base 城墙。同格排序键 = 本格前沿 y + ' + ORDER[dir]
        }
      };
    });
    out.push({
      id: 'west-common-wallnode', fp: [1, 1], draw: function (ctx) { return pier(ctx); },
      meta: { category: 'wall', kind: 'wall_node', facility: 'city_wall', variant: 1, sort_offset: ORDER.node, name: '墙节点（墩子）',
        tags: ['spoke_node', 'crenellated'], note: '墙格中心 28×28 墩子，高 46 px（高出墙顶 6 px），四面垛口；同格排序 +0.2' }
    });
    out.push({
      id: 'west-common-wallnode-02', fp: [1, 1], draw: function (ctx) { return lookout(ctx); },
      meta: { category: 'wall', kind: 'wall_node', facility: 'city_wall', variant: 2, sort_offset: ORDER.node, name: '墙节点（带小望台）',
        tags: ['spoke_node', 'lookout', 'timber'], roof: 'hip_tile', note: '墩子顶上木构四柱小望台，四坡红瓦小顶 + 小旗；可替代 wallnode' }
    });
    var PN = { h: ['东西', 3], v: ['南北', 4], se: ['西北–东南', 5], ne: ['西南–东北', 6] };
    Object.keys(PN).forEach(function (k) {
      out.push({
        id: 'west-common-wallnode-pass-' + k, fp: [1, 1], pad: 0, draw: function (ctx) { return pass(ctx, k); },
        meta: { category: 'wall', kind: 'wall_node_pass', facility: 'city_wall', variant: PN[k][1], sort_offset: ORDER.node, name: '墙节点（' + PN[k][0] + '直通）',
          tags: ['spoke_node', 'pass_through', 'crenellated'], note: '墙格只有一对相对辐条（' + PASS[k][3] + '）时代替 wallnode：与墙同高 40 px，只在两侧墙面上垛口，直段走道不被墩子打断' }
      });
    });
    return out;
  }
  /** 一个墙格该用哪个节点：dirs 为 { n:1, s:1 } 这样的表 */
  function nodeFor(dirs) {
    var k = Object.keys(dirs).sort().join(',');
    return { 'e,w': 'west-common-wallnode-pass-h', 'n,s': 'west-common-wallnode-pass-v', 'nw,se': 'west-common-wallnode-pass-se', 'ne,sw': 'west-common-wallnode-pass-ne' }[k] || 'west-common-wallnode';
  }
  var API = { makeShapes: makeShapes, makePass: makePass, T: T, H: H, PH: PH, Q: Q, SHAPE: SHAPE, PASS: PASS, DIRS: DIRS, ORDER: ORDER, spoke: spoke, pier: pier, pass: pass, lookout: lookout, nodeFor: nodeFor, items: items };
  if (isNode) module.exports = API;
  else root.TownArtWF.spoke = API;
})(this);
