/*
 * 织梦 · 东方斜向护城河辐条：moatspoke-{8 向} + moatnode（水面层），moatbank-{8 向} + moatbank-node（岸层）。
 * 地面层，不上伸（斜段过格角时带子会伸出本格约 12.7 px，同城墙辐条）。水色 = east-ground 的 C.water #6cc1b3，
 *   水纹米白 FOAM = mix(water, creamL, 0.32)，岸壁暗色 DARK = mix(water, teal, 0.55)，与 east-ground/water.js 一致。
 * 两遍绘制（meta.draw_pass）：先画全部 moatbank（pass 0：青石岸 + 暗色岸壁），再画全部 moatspoke / moatnode（pass 1：水面）。
 *   这样任意方向组合在节点处都不会出现岸线横穿水面；节点只有一种，不需要按方向组合选变体。
 * 宽度：岸带半宽 18（= 半墙厚），岸壁半宽 15.5，水面半宽 14 且向南错 2 px，于是北岸露出一条约 3.5 px 的岸壁（斜俯视看到北岸朝南的那面）。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'));
  else root.TownArtFort_moat = factory(root.TownArtFort_core);
})(this, function (F) {
  'use strict';
  var E = F.E, C = F.C, f = F.f, mix = F.mix, add = F.add, R2 = F.R2;
  var WATER = C.tealL, DARK = mix(WATER, C.teal, 0.55), FOAM = mix(WATER, C.creamL, 0.32);
  var DIRS = { n: [0, -1], ne: [R2, -R2], e: [1, 0], se: [R2, R2], s: [0, 1], sw: [-R2, R2], w: [-1, 0], nw: [-R2, -R2] };
  var ORDER = ['n', 'ne', 'e', 'se', 's', 'sw', 'w', 'nw'], CEN = [24, -24];

  function band(dir, hw, dy) {
    var d = DIRS[dir], L = dir.length === 2 ? 24 * Math.SQRT2 : 24, n = [-d[1], d[0]], c = add(CEN, [0, dy || 0]), e = add(c, d, L);
    return E.poly([add(c, n, hw), add(e, n, hw), add(e, n, -hw), add(c, n, -hw)]);
  }
  function oct(r, dy) {
    var t = r * Math.tan(Math.PI / 8), x = 24, g = -24 + (dy || 0);
    return E.poly([[x - t, g - r], [x + t, g - r], [x + r, g - t], [x + r, g + t], [x + t, g + r], [x - t, g + r], [x - r, g + t], [x - r, g - t]]);
  }
  function bankSpoke(dir) { return E.path(band(dir, 18), C.stone) + E.path(band(dir, 15.5), DARK); }
  function bankNode() { return E.path(oct(18), C.stone) + E.path(oct(15.5), DARK); }
  // 水纹：沿轴向两道短波线，位置按方向固定（同向辐条处处一致）
  function ripples(dir) {
    var d = DIRS[dir], n = [-d[1], d[0]], c = add(CEN, [0, 2]), s = '';
    [[11, -5], [24, 4]].forEach(function (q) {
      var p = add(add(c, d, q[0]), n, q[1]), a = add(p, d, -3.5), b = add(p, d, 3.5), m = add(p, [0, -1.6]);
      s += 'M' + E.pt(a) + 'Q' + E.pt(m) + ' ' + E.pt(b);
    });
    return E.line(s, FOAM, 0.9, ' stroke-opacity="0.85"');
  }
  function waterSpoke(dir) { return E.path(band(dir, 14, 2), WATER) + ripples(dir); }
  function waterNode() { return E.path(oct(14, 2), WATER) + E.line('M20 -21Q24 -23 28 -21', FOAM, 0.9, ' stroke-opacity="0.85"'); }

  function item(id, seed, draw, kind, pass, tags, note, extra) {
    var sym = E.symbol(id, seed, 1, 1, draw), m = { id: id, style: 'east', race: 'common', category: 'water', kind: kind, facility: null, variant: seed % 100,
      footprint: [1, 1], height_px: sym.up, anchor: sym.anchor, viewBox: sym.viewBox, tags: ['moat', 'spoke_water', 'pass_' + pass].concat(tags), roof: 'none',
      draw_pass: pass, note: note, name_zh: pass ? '护城河' : '护城河岸' };
    for (var k in extra || {}) m[k] = extra[k];
    return { id: id, svg: sym.svg, name: m.name_zh + ' ' + (extra && extra.dir || 'node'), meta: m };
  }
  function items() {
    var out = [];
    ORDER.forEach(function (dir, i) {
      out.push(item('east-common-moatbank-' + dir, 9600 + i, function () { return bankSpoke(dir); }, 'moat_bank_spoke', 0, ['dir_' + dir],
        '护城河岸辐条（青石岸 + 岸壁暗色），第一遍画；facility 无对应填 null', { dir: dir }));
    });
    out.push(item('east-common-moatbank-node', 9610, bankNode, 'moat_bank_node', 0, ['node'], '护城河岸节点（八角），第一遍画，每个河格一张', {}));
    ORDER.forEach(function (dir, i) {
      out.push(item('east-common-moatspoke-' + dir, 9620 + i, function () { return waterSpoke(dir); }, 'moat_spoke', 1, ['dir_' + dir],
        '护城河水面辐条，第二遍画（全部岸层之后）；水色同 east-ground', { dir: dir }));
    });
    out.push(item('east-common-moatnode', 9630, waterNode, 'moat_node', 1, ['node'], '护城河水面节点（八角），第二遍画，每个河格一张', {}));
    return out;
  }
  return { items: items, WATER: WATER };
});
