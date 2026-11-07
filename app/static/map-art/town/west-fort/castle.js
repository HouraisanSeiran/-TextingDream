/*
 * 织梦 · 西式防御工事 —— 城堡幕墙辐条 castlespoke-<dir> 与 castlenode（配合 west-castle 幕墙：墙高 60）
 * 比城镇墙更高更厚：墙厚 30（半厚 15）、高 60；节点墩子 30×30、高 66，四面垛口 + 顶上小旗。
 * 画法、拼接、同格排序与城镇墙辐条相同（第 11 节），斜段同样只按本行裁剪，viewBox 带 pad_x = 24。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWF.core;
  var G = isNode ? require('./geom.js') : root.TownArtWF.geom;
  var SP = isNode ? require('./spoke.js') : root.TownArtWF.spoke;
  var PAL = C.PAL, f = C.f, T = 15, H = 60, PH = 66;
  var SHAPE = SP.makeShapes(T), PASS = SP.makePass(T);
  var DNAME = { n: '北', ne: '东北', e: '东', se: '东南', s: '南', sw: '西南', w: '西', nw: '西北' };
  function spoke(ctx, dir) { var sh = SHAPE[dir]; return G.prism(ctx, sh[0], H, sh[1], { mode: sh[2] }); }
  function node(ctx) {
    var q = [[24 - T, -24 + T], [24 - T, -24 - T], [24 + T, -24 - T], [24 + T, -24 + T]];
    var s = G.prism(ctx, q, PH, ['wall', 'wall', 'wall', 'wall'], { mode: 'ortho' });
    // 正面一道箭缝
    s += C.poly([[23, -9 - 20], [23, -9 - 30], [25, -9 - 30], [25, -9 - 20]], PAL.hole, 0);
    var top = -24 - PH;
    ctx.top(top - 20);
    return s + C.path(C.seg([24, top], [24, top - 18]), 'none', 1.3) + C.path('M24 ' + f(top - 18) + 'q6 1 11 3.5q-6 0.8 -11 3.5Z', PAL.red, 0.7);
  }
  function pass(ctx, k) { var p = PASS[k]; return G.prism(ctx, p[0], H, p[1], { mode: p[2] }); }
  function nodeFor(dirs) {
    var k = Object.keys(dirs).sort().join(',');
    return { 'e,w': 'west-common-castlenode-pass-h', 'n,s': 'west-common-castlenode-pass-v', 'nw,se': 'west-common-castlenode-pass-se', 'ne,sw': 'west-common-castlenode-pass-ne' }[k] || 'west-common-castlenode';
  }
  function items() {
    var out = SP.DIRS.map(function (dir, k) {
      var diag = dir.length === 2;
      return {
        id: 'west-common-castlespoke-' + dir, fp: [1, 1], pad: SHAPE[dir][3], draw: function (ctx) { return spoke(ctx, dir); },
        meta: { category: 'castle', kind: 'castle_spoke', facility: 'city_wall', variant: k + 1, dir: dir, sort_offset: SP.ORDER[dir],
          name: '城堡幕墙半段（' + DNAME[dir] + '）', tags: ['spoke', 'dir_' + dir, 'crenellated', 'curtain_wall', diag ? 'diagonal' : 'orthogonal'],
          note: '城堡幕墙辐条：墙厚 30 px、高 60 px（与 west-castle 幕墙同高），从格中心画到' + (diag ? '格角（只按本行裁剪，pad_x = 24）' : '格边中点') + '。同格排序 +' + SP.ORDER[dir] }
      };
    });
    out.push({ id: 'west-common-castlenode', fp: [1, 1], draw: node,
      meta: { category: 'castle', kind: 'castle_node', facility: 'city_wall', variant: 1, sort_offset: SP.ORDER.node, name: '城堡幕墙节点',
        tags: ['spoke_node', 'crenellated', 'curtain_wall'], note: '30×30 墩子，高 66 px（高出幕墙 6 px），四面垛口、箭缝、小旗；同格排序 +0.2' } });
    var PN = { h: ['东西', 2], v: ['南北', 3], se: ['西北–东南', 4], ne: ['西南–东北', 5] };
    Object.keys(PN).forEach(function (k) {
      out.push({ id: 'west-common-castlenode-pass-' + k, fp: [1, 1], draw: function (ctx) { return pass(ctx, k); },
        meta: { category: 'castle', kind: 'castle_node_pass', facility: 'city_wall', variant: PN[k][1], sort_offset: SP.ORDER.node, name: '城堡幕墙节点（' + PN[k][0] + '直通）',
          tags: ['spoke_node', 'pass_through', 'curtain_wall'], note: '只有一对相对辐条（' + PASS[k][3] + '）时代替 castlenode，走道不断' } });
    });
    return out;
  }
  var API = { T: T, H: H, SHAPE: SHAPE, spoke: spoke, node: node, nodeFor: nodeFor, items: items };
  if (isNode) module.exports = API;
  else root.TownArtWF.castle = API;
})(this);
