/*
 * 织梦 · 东方城墙辐条（规范第 11 节）：wallspoke-{n,ne,e,se,s,sw,w,nw} + wallnode（8 个变体）。
 * 墙走在逻辑格中心连成的折线上，墙厚 36（中线两侧各 18），墙高 WH=26，砖缝 / 垛口 / 女墙 / 海墁与 east-base 城墙一致。
 * 节点 = 正八角墩，内切半径 18（= 半墙厚）：东西两边在 x=6 / 42，南北两边在 g=-42 / -6，与正交墙身齐平。
 * 每根辐条 = 一条 36 宽的带子，从八角墩的弦（距格心 B = 18·tan22.5° = 7.46）伸到格边中点（正交）或格角（斜向）；
 *   带子两条边正好过八角墩的两个顶点，所以墙顶、垛口、女墙在节点处首尾相接。
 * 斜段：朝南那一侧（NE-SW 墙的东南面、NW-SE 墙的西南面）画砖立面 + 垛口，背侧画女墙；不是旋转，是按平面投影。
 * 排序（规范第 11 节）：n/ne/nw 在节点前画，节点盖住它们的根部；e/w/s/se/sw 在节点后画，盖住节点相应的边。
 * 所以节点只需知道本格有没有朝北的辐条：变体按 north mask = nw*4 + n*2 + ne 选，
 *   wallnode = 000，wallnode-02 … wallnode-08 = mask 1 … 7（id 后缀 = mask + 1）。
 * 斜段带子在格角两侧各伸出本格约 12.7 px（满厚 45° 带子过格角，几何上无法完全留在格内），见 README。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'));
  else root.TownArtFort_spoke = factory(root.TownArtFort_core);
})(this, function (F) {
  'use strict';
  var E = F.E, WH = F.WH, PH = F.PH, PW = F.PW, R2 = F.R2, add = F.add;
  var CX = 24, CG = -24, HW = 18, B = 18 * Math.tan(Math.PI / 8);
  var DIRS = { n: [0, -1], ne: [R2, -R2], e: [1, 0], se: [R2, R2], s: [0, 1], sw: [-R2, R2], w: [-1, 0], nw: [-R2, -R2] };
  var ORDER = ['n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw'];
  var SORT = { n: 0.1, ne: 0.1, nw: 0.1, node: 0.2, e: 0.3, w: 0.3, s: 0.4, se: 0.4, sw: 0.4 };
  // 八角墩顶点（顺时针，从北边西端起）
  var OCT = [[CX - B, -42], [CX + B, -42], [42, CG - B], [42, CG + B], [CX + B, -6], [CX - B, -6], [6, CG + B], [6, CG - B]];

  function orthSpoke(ctx, dir) {
    var s = '';
    if (dir === 'e' || dir === 'w') {
      var x0 = dir === 'e' ? CX + B : 0, x1 = dir === 'e' ? 48 : CX - B;
      s += F.topPoly(ctx, [[x0, -42], [x1, -42], [x1, -6], [x0, -6]], WH);
      s += F.merlonsH(x0, x1, -42 + PW, PW, WH, WH + 3.5, true);          // 北沿女墙
      return s + F.wallFace(ctx, x0, x1, -6, WH, [false, false]) + F.merlonsH(x0, x1, -6, PW, WH, WH + PH, false);
    }
    var g0 = dir === 'n' ? -48 : CG + B, g1 = dir === 'n' ? CG - B : 0;
    s += F.topPoly(ctx, [[6, g0], [42, g0], [42, g1], [6, g1]], WH);
    return s + F.merlonsV(6, g0, g1, WH, WH + PH) + F.merlonsV(42 - PW, g0, g1, WH, WH + PH);
  }
  function diagSpoke(ctx, dir) {
    var d = DIRS[dir], c = add([CX, CG], d, B), e = add([CX, CG], d, 24 * Math.SQRT2), n1 = [-d[1], d[0]], n2 = [d[1], -d[0]];
    var nf = n1[1] > 0 ? n1 : n2, nb = n1[1] > 0 ? n2 : n1, fill = F.shadeOf(nf);
    var f0 = add(c, nf, HW), f1 = add(e, nf, HW), b0 = add(c, nb, HW), b1 = add(e, nb, HW), s = '';
    s += F.topPoly(ctx, [f0, f1, b1, b0], WH);
    s += F.diagPar(b0, b1, nf, false);                                     // 背侧女墙
    return s + F.diagFace(ctx, f0, f1, WH, fill, [false, false]) + F.diagPar(f0, f1, nb, true, fill);
  }
  // 节点：open = 八角墩 8 条边里没被辐条盖住的边（bit i 对应 ORDER[i] 方向的边）。
  // 每根辐条盖住自己方向的边和左右相邻的两条边，所以边 i 露出 ⇔ 方向 i-1、i、i+1 都没有辐条。
  // 露出的边画垛墙 / 立面；被盖住的不画（盖它的辐条在排序上都画在节点之后，或者在节点之前但只盖北侧低处）。
  var EO = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 0]];   // ORDER[i] 方向的边 = OCT[EO[i][0]]-OCT[EO[i][1]]
  function openEdges(spokes) {
    var m = 0;
    for (var i = 0; i < 8; i++) {
      var hit = [ORDER[(i + 7) % 8], ORDER[i], ORDER[(i + 1) % 8]].some(function (d) { return spokes.indexOf(d) >= 0; });
      if (!hit) m |= 1 << i;
    }
    return m;
  }
  function node(ctx, open) {
    var O = OCT, on = function (d) { return !!(open & (1 << ORDER.indexOf(d))); }, s = F.topPoly(ctx, O, WH);
    var fl = F.shadeOf([-1, 1]), fr = F.shadeOf([1, 1]);
    if (on('nw')) s += F.diagPar(O[7], O[0], [R2, R2], false);
    if (on('n')) s += F.merlonsH(O[0][0], O[1][0], -42 + PW, PW, WH, WH + 3.5, true);
    if (on('ne')) s += F.diagPar(O[1], O[2], [-R2, R2], false);
    if (on('w')) s += F.merlonsV(6, O[7][1], O[6][1], WH, WH + PH);
    if (on('e')) s += F.merlonsV(42 - PW, O[2][1], O[3][1], WH, WH + PH);
    // 立面端头竖线只画在真正的折角上（相邻那条边也露出）；与相邻辐条共线时不画
    if (on('sw')) s += F.diagFace(ctx, O[6], O[5], WH, fl, [on('w'), on('s')]);
    if (on('s')) s += F.wallFace(ctx, O[5][0], O[4][0], -6, WH, [on('sw'), on('se')]);
    if (on('se')) s += F.diagFace(ctx, O[4], O[3], WH, fr, [on('s'), on('e')]);
    if (on('sw')) s += F.diagPar(O[6], O[5], [R2, -R2], true, fl);
    if (on('s')) s += F.merlonsH(O[5][0], O[4][0], -6, PW, WH, WH + PH, false);
    if (on('se')) s += F.diagPar(O[4], O[3], [-R2, -R2], true, fr);
    return s;
  }
  // 所有可能出现的 open 组合（至少一根辐条）：共 45 种，按数值升序编号；open = 0 → wallnode，其余 → wallnode-02 …
  var OPEN_LIST = (function () {
    var seen = {}, l = [];
    for (var m = 1; m < 256; m++) {
      var sp = ORDER.filter(function (d, i) { return m & (1 << i); }), o = openEdges(sp);
      if (!seen[o]) { seen[o] = 1; l.push(o); }
    }
    return l.sort(function (a, b) { return a - b; });
  })();
  function nodeIdByOpen(o) { var k = OPEN_LIST.indexOf(o); return 'east-common-wallnode' + (k > 0 ? '-' + (k + 1 < 10 ? '0' : '') + (k + 1) : ''); }
  function nodeId(spokes) { return nodeIdByOpen(openEdges(spokes)); }
  function openBits(o) { return ORDER.filter(function (d, i) { return o & (1 << i); }); }
  function nodeMask(spokes) { return (spokes.indexOf('nw') >= 0 ? 4 : 0) + (spokes.indexOf('n') >= 0 ? 2 : 0) + (spokes.indexOf('ne') >= 0 ? 1 : 0); }

  function meta(sym, kind, variant, tags, note, extra) {
    var m = { id: sym.id, style: 'east', race: 'common', category: 'wall', kind: kind, facility: 'city_wall', variant: variant,
      footprint: [1, 1], height_px: sym.up, anchor: sym.anchor, viewBox: sym.viewBox, tags: ['spoke_wall', 'crenellated', 'brick_faced'].concat(tags),
      roof: 'none', note: note };
    for (var k in extra) m[k] = extra[k];
    return m;
  }
  function items() {
    var out = [];
    ORDER.forEach(function (dir, i) {
      var id = 'east-common-wallspoke-' + dir, diag = dir.length === 2;
      var sym = E.symbol(id, 9100 + i, 1, 1, function (ctx) { return diag ? diagSpoke(ctx, dir) : orthSpoke(ctx, dir); });
      out.push({ id: id, svg: sym.svg, name: '城墙辐条 ' + dir, meta: meta(sym, 'wall_spoke', i + 1, ['dir_' + dir, diag ? 'diagonal' : 'orthogonal'],
        '夯土包砖城墙半段，从八角墩的弦画到' + (diag ? '格角（满厚 45° 带子，格角两侧各伸出本格约 12.7 px）' : '格边中点') + '；墙厚 36、墙高 ' + WH + '，与 east-base 城墙一致',
        { name_zh: '城墙辐条', dir: dir, sort_offset: SORT[dir] }) });
    });
    OPEN_LIST.forEach(function (o, k) {
      var id = nodeIdByOpen(o), ob = openBits(o);
      var sym = E.symbol(id, 9200 + o, 1, 1, function (ctx) { return node(ctx, o); });
      out.push({ id: id, svg: sym.svg, name: '墙墩 露边 ' + (ob.join('+') || '无'), meta: meta(sym, 'wall_node', k + 1, ['node', 'octagon', 'open_' + o],
        '八角墙墩（八条边与正交、斜向墙身两侧齐平）。露出的边 = ' + (ob.join(' ') || '无') + '。选法：边 i 露出 ⇔ 方向 i-1、i、i+1 都没有辐条（方向顺序 n ne e se s sw w nw）；用 nodeId(本格辐条方向数组) 取 id',
        { name_zh: '墙墩', open_edges: ob, open_mask: o, sort_offset: SORT.node }) });
    });
    return out;
  }
  return { items: items, DIRS: DIRS, ORDER: ORDER, SORT: SORT, OCT: OCT, B: B, orthSpoke: orthSpoke, diagSpoke: diagSpoke, node: node, nodeId: nodeId, nodeIdByOpen: nodeIdByOpen, openEdges: openEdges, OPEN_LIST: OPEN_LIST, nodeMask: nodeMask };
});
