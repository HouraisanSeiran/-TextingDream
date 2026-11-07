/*
 * 织梦 · 东方城防工事 A：马面（墙外墩台）、敌楼、箭楼、十字脊角楼。
 * 马面 mamian-{n,s,e,w}：1×1，放在墙格外侧相邻格；块体向墙一侧多画 6 px 贴住墙身（只向北 / 向东西伸，不越过前沿）。
 * 敌楼 / 箭楼 / 角楼：1×1 叠加件，立在墙墩（wallnode）顶上，墙墩照常画；同格排序偏移 0.45（在 s / se / sw 辐条之后）。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('../east-base/houses-a.js'));
  else root.TownArtFort_forts = factory(root.TownArtFort_core, root.TownArtEast_housesA);
})(this, function (F, HA) {
  'use strict';
  var E = F.E, C = F.C, T = F.T, K = F.K, f = F.f, sy = F.sy, WH = F.WH, PH = F.PH, PW = F.PW, WC = F.WC;

  // 马面：o = 平面范围 [x0,x1,gb,gf]，side = 贴墙那一侧（不画垛口）
  var MM = {
    n: { r: [8, 40, -88, -36], tie: 's', fp: [1, 2] },  // 1×2：前排那格就是墙格，块体南端压在墙顶北沿上（不画南立面）
    s: { r: [8, 40, -54, -6], tie: 'n' },    // 墙在北边一格：北端伸进墙脚
    e: { r: [-6, 34, -40, -8], tie: 'w' },
    w: { r: [14, 54, -40, -8], tie: 'e' }
  };
  function mamian(ctx, dir) {
    var m = MM[dir], x0 = m.r[0], x1 = m.r[1], gb = m.r[2], gf = Math.min(0, m.r[3]), z = WH, s = '', gv = m.tie === 's' ? -42 : gf;
    if (m.tie !== 's') s += E.shadow(x0, x1, gb, gf, z, 5);
    s += F.topPoly(ctx, [[x0, gb], [x1, gb], [x1, gf], [x0, gf]], z);
    if (m.tie !== 'n') s += F.merlonsH(x0, x1, gb + PW, PW, z, z + PH, false);
    if (m.tie !== 'w') s += F.merlonsV(x0, gb + (m.tie === 'n' ? 0 : PW), gv, z, z + PH);
    if (m.tie !== 'e') s += F.merlonsV(x1 - PW, gb + (m.tie === 'n' ? 0 : PW), gv, z, z + PH);
    if (m.tie === 's') return s;
    s += F.wallFace(ctx, x0, x1, gf, z, [m.tie !== 'w', m.tie !== 'e']);
    if (m.tie !== 's') s += F.merlonsH(x0, x1, gf, PW, z, z + PH, false);
    // 墩台正面一道石砌腰线 + 两个射孔
    s += E.rect(x0, sy(gf, z * 0.55), x1 - x0, 1.4, WC.base, C.gold, 0.4);
    s += F.arrowWin((x0 + x1) / 2 - 7, gf, z * 0.62, 2.4, 5) + F.arrowWin((x0 + x1) / 2 + 4.6, gf, z * 0.62, 2.4, 5);
    return s;
  }

  // 墙顶楼身：砖面 + 箭窗行列（rows × cols），x0..x1，前脸 g，z0..z1
  function brickBody(ctx, x0, x1, gb, g, z0, z1, rows, cols, ww) {
    var s = F.topPoly(ctx, [[x0, gb], [x1, gb], [x1, g], [x0, g]], z1);
    s += F.brickFace(ctx, x0, x1, sy(g, z1), sy(g, z0));
    s += E.line('M' + f(x0) + ' ' + f(sy(g, z1)) + 'H' + f(x1) + 'V' + f(sy(g, z0)) + 'M' + f(x0) + ' ' + f(sy(g, z1)) + 'V' + f(sy(g, z0)), C.gold, 0.8);
    var bw = (x1 - x0) / cols, hz = (z1 - z0) / rows;
    for (var r = 0; r < rows; r++) for (var c = 0; c < cols; c++)
      s += F.arrowWin(x0 + bw * (c + 0.5) - ww / 2, g, z0 + hz * (r + 0.28), ww, hz * 0.5);
    return s;
  }

  // 木构一层：墙面 + 窗 + 朱柱 + 额枋
  function storey(x0, x1, g, z0, z1, n, wall, winKind) {
    var s = E.face(x0, x1, g, z0, z1, wall || C.cream), bw = (x1 - x0) / n, k;
    for (k = 0; k < n; k++) s += E.win(x0 + k * bw + bw * 0.2, g, z0 + (z1 - z0) * 0.28, bw * 0.6, (z1 - z0) * 0.44, winKind || 'lattice');
    for (k = 0; k <= n; k++) s += E.col(x0 + k * bw, g, z0, z1, C.vermil);
    return s + E.face(x0 - 0.5, x1 + 0.5, g, z1 - 2, z1, C.teal, C.gold2, 0.5);
  }
  var Z = WH, TG = T.gray;
  // 敌楼（空心敌台）：砖砌楼身两层箭窗，顶上一圈垛口，台顶一座小楼橹（攒尖）
  function dilou(ctx) {
    var s = E.shadow(8, 40, -42, -8, 40, 5), z1 = Z + 20;
    s += brickBody(ctx, 8, 40, -42, -8, Z, z1, 2, 3, 3.2);
    s += E.rect(8, sy(-8, z1) - 0.2, 32, 1.6, WC.faceD);
    s += F.ringCrenels(8, 40, -42, -8, z1, {});
    s += E.shadow(15, 33, -34, -18, 12, 3).replace('fill-opacity="0.2"', 'fill-opacity="0.12"');
    s += storey(15, 33, -18, z1, z1 + 9, 2, C.cream, 'lattice');
    s += E.roofPyr(ctx, { x0: 15, x1: 33, gb: -34, gf: -18, h: z1 + 9, rh: 10, t: TG, ov: 4, lift: 4 });
    return s;
  }
  // 箭楼：砖砌重檐楼，正面密排箭窗（4 行 × 4 列），下层腰檐 + 上层歇山
  function jianlou(ctx) {
    var s = E.shadow(5, 43, -42, -8, 50, 6), z1 = Z + 16, z2 = Z + 30;
    s += brickBody(ctx, 5, 43, -42, -8, Z, z1, 2, 4, 2.6);
    s += HA.H.shed(ctx, 4, 44, -10, z1 - 1, TG, 5, 3);
    s += brickBody(ctx, 7, 41, -40, -12, z1 + 1, z2, 2, 4, 2.6);
    s += E.roofEW(ctx, { x0: 7, x1: 41, gb: -40, gf: -12, h: z2, rh: 13, type: 'xie', t: TG, ov: 5, os: 4, lift: 6, ridge: 'curl', ridgeW: 3 });
    return s;
  }
  // 十字脊角楼：砖台 + 一层木构楼 + 平座栏杆 + 十字脊歇山顶（东西向、南北向两条正脊相交，四面出山花）
  function cornerTower(ctx) {
    var s = E.shadow(7, 41, -41, -7, 56, 6), z1 = Z + 6, z2 = z1 + 14;
    s += brickBody(ctx, 7, 41, -41, -7, Z, z1, 1, 3, 3);
    s += F.ringCrenels(7, 41, -41, -7, z1, { south: false });
    s += storey(11, 37, -11, z1, z2, 3, C.vermil, 'hex');
    s += HA.H.railing(9, 39, -8, z1, z1 + 3.5, C.vermil, 2.6);
    s += E.roofEW(ctx, { x0: 11, x1: 37, gb: -37, gf: -11, h: z2, rh: 12, type: 'xie', t: T.teal, ov: 5, os: 4, lift: 6, ridge: 'curl', ridgeW: 2.6 });
    s += E.roofNS(ctx, { x0: 17, x1: 31, gb: -38, gf: -10, h: z2 + 2, rh: 10, t: T.teal, ov: 3, os: 4, lift: 2 });
    // 十字交点宝顶
    var A = E.P(24, -24, z2 + 13);
    s += E.circle(A[0], A[1] - 3, 2.4, C.ochre, C.gold, 0.8);
    return s;
  }

  function meta(sym, o) {
    var m = { id: sym.id, style: 'east', race: 'common', category: o.category || 'fort', kind: o.kind, facility: o.facility, variant: o.variant || 1,
      footprint: o.fp || [1, 1], height_px: sym.up, anchor: sym.anchor, viewBox: sym.viewBox, tags: o.tags, roof: o.roof || 'none', note: o.note };
    for (var k in o.extra || {}) m[k] = o.extra[k];
    return m;
  }
  function item(id, seed, w, d, draw, o) {
    var sym = E.symbol(id, seed, w, d, draw);
    return { id: id, svg: sym.svg, name: o.name, meta: meta(sym, o) };
  }
  function items() {
    var out = [], NAME = { n: '北', s: '南', e: '东', w: '西' };
    ['n', 's', 'e', 'w'].forEach(function (d, i) {
      var fp = MM[d].fp || [1, 1];
      out.push(item('east-common-mamian-' + d, 9300 + i, fp[0], fp[1], function (c) { return mamian(c, d); }, { name: '马面 ' + d, kind: 'mamian', facility: 'watchtower', variant: i + 1, fp: fp,
        tags: ['mamian', 'dir_' + d, 'crenellated', 'brick_faced'], extra: { name_zh: '马面', dir: d },
        note: '马面（墙外凸出的砖砌墩台），朝' + NAME[d] + '凸出；放在墙格' + NAME[d] + '侧相邻的一格，贴墙一侧不画垛口，伸出约 6 px 与墙身贴合' }));
    });
    out.push(item('east-common-dilou-01', 9310, 1, 1, dilou, { name: '敌楼', kind: 'dilou', facility: 'watchtower', roof: 'hip_tile',
      tags: ['dilou', 'on_node', 'arrow_windows', 'crenellated'], extra: { name_zh: '敌楼', sort_offset: 0.45 },
      note: '空心敌楼：砖砌楼身两层箭窗、顶上垛口与攒尖小楼橹；放在墙节点上（墙墩照常画，本件排序偏移 0.45）。roof 为攒尖顶，取最近的 hip_tile' }));
    out.push(item('east-common-jianlou-01', 9311, 1, 1, jianlou, { name: '箭楼', kind: 'jianlou', facility: 'watchtower', roof: 'hip_tile',
      tags: ['jianlou', 'on_node', 'arrow_windows', 'double_eave'], extra: { name_zh: '箭楼', sort_offset: 0.45 },
      note: '箭楼：砖砌重檐，下层腰檐、上层歇山，正面两层各密排 2 行 × 4 列箭窗；放在墙节点上。roof 歇山取最近的 hip_tile' }));
    out.push(item('east-common-cornertower-01', 9312, 1, 1, cornerTower, { name: '十字脊角楼', kind: 'corner_tower', facility: 'watchtower', roof: 'hip_tile',
      tags: ['corner_tower', 'cross_ridge', 'on_node', 'teal_glazed'], extra: { name_zh: '十字脊角楼', sort_offset: 0.45 },
      note: '十字脊角楼：砖台 + 一层木构楼 + 平座栏杆 + 青绿琉璃十字脊歇山顶；放在墙节点或拐角。roof 歇山取最近的 hip_tile' }));
    return out;
  }
  return { items: items, mamian: mamian, dilou: dilou, jianlou: jianlou, cornerTower: cornerTower, brickBody: brickBody, storey: storey, item: item };
});
