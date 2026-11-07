/*
 * 织梦 · east-ground · 地面：底纹 earth-01..04（任意排列无缝）、青砖院坪双网格 paving-XXXX × 16
 *
 * 底纹：四张同一底色 #d9c58f（规范东方预览地面色），所有斑块、草丛、碎石都离瓦片边 ≥ 4 px，
 *       所以任意两张怎么拼，边上都是同一种纯色，一定无缝；四张的点缀位置、疏密各不相同，混铺时看不出重复格。
 * 院坪：mask 里 1 = 铺地。方砖 12×12 按周期 48 摆放（世界对齐），砖缝正好落在逻辑格边界 x/y = 24 上；
 *       分界走直角（square 模式），沿边一圈压边条砖，砖缝从岸线两端各按 12 px 量起，相邻瓦片对得上。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./grid.js'), require('./water.js'), require('./water-tiles.js'));
  else root.TownArtEG_ground = factory(root.TownArtEG_core, root.TownArtEG_grid, root.TownArtEG_water, root.TownArtEG_waterTiles);
})(this, function (K, GR, W, WT) {
  'use strict';
  var C = K.C, f = K.f, mix = K.mix;
  var LITE = mix(C.grass, C.creamL, 0.38), DUSK = mix(C.grass, C.umberL, 0.2), MOSS = mix(C.grass, C.leaf, 0.22);

  // ---------- 底纹 ----------
  /** 不规则软斑：几个重叠椭圆，统一半透明。 */
  function blob(x, y, w, h, col, o, r) {
    var s = '';
    for (var i = 0; i < 3; i++) s += K.ell(x + (r() - 0.5) * w * 0.6, y + (r() - 0.5) * h * 0.5, w * (0.35 + r() * 0.2), h * (0.35 + r() * 0.2), col);
    return '<g' + K.op(o) + '>' + s + '</g>';
  }
  function tuft(x, y, r, sc) {
    var d = '';
    for (var k = 0; k < 5; k++) { var a = -Math.PI / 2 + (k - 2) * 0.42 + (r() - 0.5) * 0.2, L = (3.4 + r() * 1.8) * sc; d += 'M' + f(x + (k - 2) * 0.6) + ' ' + f(y) + 'q' + f(Math.cos(a) * L * 0.3) + ' ' + f(Math.sin(a) * L * 0.6) + ' ' + f(Math.cos(a) * L) + ' ' + f(Math.sin(a) * L); }
    return K.line(d, C.leaf, 0.75, K.sop(0.75)) + K.line('M' + f(x - 1.2 * sc) + ' ' + f(y - 2 * sc) + 'l' + f(1.2 * sc) + ' ' + f(-1.6 * sc), C.leafL, 0.6, K.sop(0.8));
  }
  function gravel(x, y, r) {
    var s = '';
    for (var k = 0; k < 3; k++) { var rx = 0.8 + r() * 0.7; s += K.ell(x + (r() - 0.5) * 5, y + (r() - 0.5) * 3, rx * 1.3, rx, k ? C.rock : C.rockL, C.gold, 0.3); }
    return s;
  }
  function inner(r, m) { return m + r() * (48 - 2 * m); }
  // 每张底纹的疏密配方：[亮斑, 暗斑, 苔斑, 草丛, 碎石, 土粒]
  // 斑块小而淡（0.22–0.32），位置各不相同；土粒铺满到离边 1.5 px，边上不再是一圈空白，避免排成格子
  // 草丛只放在一张里且缩小：两张都有草丛时，草丛在格内同一位置，大片铺开会排成网格
  var EARTH = [[2, 1, 0, 0, 0, 22], [1, 0, 1, 0, 1, 26], [0, 2, 0, 1, 0, 30], [1, 1, 1, 0, 1, 20]];
  var SEEDS = [5311, 5422, 5537, 5649];
  function earthTile(v) {
    var id = 'east-common-ground-earth-' + K.pad2(v + 1), r = K.rng(SEEDS[v]), q = EARTH[v], s = K.rect(-0.5, -0.5, 49, 49, C.grass), i;
    for (i = 0; i < q[0]; i++) s += blob(inner(r, 11), inner(r, 9), 9 + r() * 6, 4 + r() * 2, LITE, 0.32, r);
    for (i = 0; i < q[1]; i++) s += blob(inner(r, 10), inner(r, 9), 8 + r() * 5, 4 + r() * 1.5, DUSK, 0.22, r);
    for (i = 0; i < q[2]; i++) s += blob(inner(r, 10), inner(r, 9), 8 + r() * 4, 4, MOSS, 0.3, r);
    for (i = 0; i < q[5]; i++) s += K.circ(inner(r, 1.5), inner(r, 1.5), 0.35 + r() * 0.45, r() < 0.6 ? C.umberL : C.strawD, null, 0, K.op(0.35));
    for (i = 0; i < q[4]; i++) s += gravel(inner(r, 9), inner(r, 9), r);
    for (i = 0; i < q[3]; i++) s += tuft(inner(r, 9), inner(r, 10) + 3, r, 0.7 + r() * 0.2);
    var sym = K.tileSym(id, s);
    return { id: id, svg: sym.svg, name: '黄土地面 ' + (v + 1), meta: {
      id: id, style: 'east', race: 'common', category: 'ground', kind: 'ground_earth', facility: null, variant: v + 1,
      footprint: [1, 1], height_px: 0, anchor: sym.anchor, viewBox: sym.viewBox, tags: ['tileable', 'base_ground', 'any_order'], roof: 'none',
      note: '地面底纹，底色 #d9c58f，四张任意排列无缝（点缀离边 ≥ 4 px）', name_zh: '黄土地面'
    } };
  }

  // ---------- 青砖院坪 ----------
  // 砖色往米白、石色上靠一些，砖缝用浅一档的灰，院坪不压过建筑
  var BRK = mix(C.brick, C.stone, 0.3), BRL = mix(C.brickL, C.creamL, 0.25), GROUT = mix(C.brick, C.brickD, 0.55);
  var BR = [BRK, BRL, mix(BRK, BRL, 0.5), mix(BRK, C.tealL, 0.1), mix(BRK, C.stone, 0.35)];
  function pavingTex() {
    var r = K.rng(6101), s = K.rect(-1, -1, 50, 50, GROUT), hi = '';
    for (var j = 0; j < 4; j++) for (var i = 0; i < 4; i++) {
      var x = i * 12, y = j * 12, c = BR[Math.floor(r() * BR.length)];
      s += K.rect(x + 0.45, y + 0.45, 11.1, 11.1, c);
      hi += 'M' + f(x + 1.4) + ' ' + f(y + 1.3) + 'H' + f(x + 10.4);
      if (r() < 0.14) s += K.line('M' + f(x + 3 + r() * 3) + ' ' + f(y + 0.8) + 'l' + f(1.5 + r() * 2) + ' ' + f(4 + r() * 2) + 'l' + f(2.4) + ' ' + f(2), GROUT, 0.5, K.sop(0.7));
      if (r() < 0.04) s += tuft(x + 6, y + 11.6, r, 0.45);
    }
    return s + K.line(hi, C.creamL, 0.6, K.sop(0.4));
  }
  function pavingTile(mask) {
    var id = 'east-common-ground-paving-' + K.bits(mask), ctx = new K.Ctx(id, 1), b = '';
    var rg = GR.region(mask, { mode: 'square', rr: 3 });
    if (rg) {
      var band = '', gold = '', edge = '';
      rg.edges.forEach(function (e) {
        var P = e.pts, D = GR.polyD(W.extend(P, 6)), jd = '';
        WT.joints(P, 12).forEach(function (j) { jd += 'M' + K.pt(j.p) + 'L' + K.pt([j.p[0] + j.n[0] * 5, j.p[1] + j.n[1] * 5]); });
        band += K.line(D, GROUT, 11.6) + K.line(D, mix(C.brickL, C.cream, 0.4), 9.6) + K.line(jd, GROUT, 0.7);
        edge += K.line(D, C.umber, 3, K.sop(0.18));
        gold += K.line(D, C.gold, 1);
      });
      b += K.clip(ctx, GR.outside(rg), edge, true);
      b += K.clip(ctx, rg.fill, pavingTex() + band) + gold;
    }
    var sym = K.tileSym(id, b);
    return { id: id, svg: sym.svg, name: '青砖院坪 ' + K.bits(mask), meta: {
      id: id, style: 'east', race: 'common', category: 'ground', kind: 'ground_paving', facility: null, variant: mask,
      footprint: [1, 1], height_px: 0, anchor: sym.anchor, viewBox: sym.viewBox,
      tags: ['dual_grid', 'brick_paving', 'courtyard', 'plaza', 'mask_' + K.bits(mask)].concat(mask === 0 ? ['empty'] : []), roof: 'none',
      note: '青砖方砖铺地双网格（衙前广场、寺前、市集），四角 NW NE SW SE = ' + K.bits(mask) + '（1 = 铺地）' + (mask === 0 ? '，空瓦片透明占位' : '') + '；非铺地一侧透明',
      name_zh: '青砖院坪', mask: mask
    } };
  }

  function all() {
    var out = [], i;
    for (i = 0; i < 4; i++) out.push(earthTile(i));
    for (i = 0; i < 16; i++) out.push(pavingTile(i));
    return out;
  }
  return { all: all, tuft: tuft, gravel: gravel };
});
