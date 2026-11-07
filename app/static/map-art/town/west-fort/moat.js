/*
 * 织梦 · 西式防御工事 —— 斜向护城河辐条 moatspoke-<dir> + moatnode（地面层，不上伸）
 * 水带宽 32（半宽 16），水色 #a9b8ad 同 west-ground；岸线只画在外边（wall 边），北岸内侧一条暗水带表示岸壁阴影，
 * 南岸外侧向下 3 px 的岸壁（属于投影范围）。拼接与城墙辐条相同；地面层应先于所有墙体画。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWF.core;
  var G = isNode ? require('./geom.js') : root.TownArtWF.geom;
  var SP = isNode ? require('./spoke.js') : root.TownArtWF.spoke;
  var PAL = C.PAL, T = 16, WATER = '#a9b8ad', DEEP = '#93a394';
  var SHAPE = SP.makeShapes(T), PASS = SP.makePass(T);
  var DNAME = { n: '北', ne: '东北', e: '东', se: '东南', s: '南', sw: '西南', w: '西', nw: '西北' };
  function water(poly, kinds) {
    var E = G.edges(poly), bank = '', lip = '', dark = '';
    E.forEach(function (e, i) {
      if (kinds[i] !== 'wall') return;
      bank += C.seg(e.a, e.b);
      if (e.n[1] < -0.3) dark += C.pts([e.a, e.b, [e.b[0], e.b[1] + 4], [e.a[0], e.a[1] + 4]]);
      if (e.n[1] > 0.3) lip += C.pts([e.a, e.b, [e.b[0], e.b[1] + 3], [e.a[0], e.a[1] + 3]]);
    });
    var b = G.bbox(poly), rip = '';
    for (var y = Math.floor(b[1] / 12) * 12 + 6; y < b[3]; y += 12) for (var x = Math.floor(b[0] / 16) * 16 + ((y / 12) % 2 ? 4 : 12); x < b[2]; x += 16) rip += 'M' + C.f(x - 3) + ' ' + C.f(y) + 'h6';
    return C.poly(poly, WATER, 0) + C.path(dark, DEEP, 0) + C.path(lip, PAL.soil, 0) +
      '<clipPath id="' + this.uid() + '"><path d="' + C.pts(poly) + '"/></clipPath>' +
      '<g clip-path="url(#' + this.id + '-c' + (this.n - 1) + ')">' + C.lines(rip, 0.8, 0.35) + '</g>' + C.path(bank, 'none', 1.3);
  }
  function spoke(ctx, dir) { var sh = SHAPE[dir]; return water.call(ctx, sh[0], sh[1]); }
  function node(ctx) { return water.call(ctx, [[24 - T, -24 + T], [24 - T, -24 - T], [24 + T, -24 - T], [24 + T, -24 + T]], ['open', 'open', 'open', 'open']); }
  function pass(ctx, k) { var p = PASS[k]; return water.call(ctx, p[0], p[1]); }
  function nodeFor(dirs) {
    var k = Object.keys(dirs).sort().join(',');
    return { 'e,w': 'west-common-moatnode-pass-h', 'n,s': 'west-common-moatnode-pass-v', 'nw,se': 'west-common-moatnode-pass-se', 'ne,sw': 'west-common-moatnode-pass-ne' }[k] || 'west-common-moatnode';
  }
  function items() {
    var out = SP.DIRS.map(function (dir, k) {
      return { id: 'west-common-moatspoke-' + dir, fp: [1, 1], pad: SHAPE[dir][3], ground: true, draw: function (ctx) { return spoke(ctx, dir); },
        meta: { category: 'water', kind: 'moat_spoke', facility: null, variant: k + 1, dir: dir, layer: 'ground', name: '护城河半段（' + DNAME[dir] + '）',
          tags: ['spoke', 'moat', 'dir_' + dir, 'ground_layer'], note: '地面层护城河辐条：水宽 32 px，水色 #a9b8ad（同 west-ground），不上伸；先于墙体画。方向与拼接同城墙辐条' } };
    });
    out.push({ id: 'west-common-moatnode', fp: [1, 1], ground: true, draw: node,
      meta: { category: 'water', kind: 'moat_node', facility: null, variant: 1, layer: 'ground', name: '护城河节点', tags: ['spoke_node', 'moat', 'ground_layer'], note: '格中心 32×32 水面，无岸线（岸线由辐条画）' } });
    [['se', '西北–东南', 2], ['ne', '西南–东北', 3], ['h', '东西', 4], ['v', '南北', 5]].forEach(function (p) {
      out.push({ id: 'west-common-moatnode-pass-' + p[0], fp: [1, 1], ground: true, draw: function (ctx) { return pass(ctx, p[0]); },
        meta: { category: 'water', kind: 'moat_node_pass', facility: null, variant: p[2], layer: 'ground', name: '护城河节点（' + p[1] + '直通）', tags: ['spoke_node', 'moat', 'pass_through', 'ground_layer'], note: '直通时代替 moatnode：岸线连续，斜向时还避免方块角伸出水带' } });
    });
    return out;
  }
  var API = { T: T, SHAPE: SHAPE, spoke: spoke, node: node, nodeFor: nodeFor, items: items };
  if (isNode) module.exports = API;
  else root.TownArtWF.moat = API;
})(this);
