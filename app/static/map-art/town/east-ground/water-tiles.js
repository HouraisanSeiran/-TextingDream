/*
 * 织梦 · east-ground · 水面瓦片：自然河岸 bank-XXXX、条石驳岸 quay-XXXX（各 16），驳岸石阶叠加件 quay-steps-s / -n
 *
 * mask 里 1 = 该角是水。瓦片的陆地一侧透明（下面铺什么地面都行），只在岸线附近画湿土带、卵石、芦苇。
 * 所有沿岸线的描边都在两端沿切向外延 6 px，并且岸线在边中点处垂直于瓦片边，所以相邻瓦片的笔触首尾相接。
 * 驳岸压顶石的石缝从每条岸线的两端各按 12 px 量起，直岸线正好落在世界 x / y 的 12 倍数上。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./grid.js'), require('./water.js'));
  else root.TownArtEG_waterTiles = factory(root.TownArtEG_core, root.TownArtEG_grid, root.TownArtEG_water);
})(this, function (K, GR, W) {
  'use strict';
  var C = K.C, f = K.f, mix = K.mix;
  function ext(P) { return GR.polyD(W.extend(P, 6)); }

  /** 沿岸线两端各按 step 量出接缝点：返回 [{ p, n }]（n 指向水面）。 */
  function joints(P, step) {
    var N = W.norms(P), cum = [0], i, out = [];
    for (i = 1; i < P.length; i++) cum.push(cum[i - 1] + Math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]));
    var L = cum[cum.length - 1];
    function pick(s) {
      for (var k = 1; k < P.length; k++) if (cum[k] >= s - 1e-6) {
        var t = (s - cum[k - 1]) / ((cum[k] - cum[k - 1]) || 1);
        return { p: [P[k - 1][0] + (P[k][0] - P[k - 1][0]) * t, P[k - 1][1] + (P[k][1] - P[k - 1][1]) * t], n: N[t < 0.5 ? k - 1 : k] };
      }
      return { p: P[P.length - 1], n: N[N.length - 1] };
    }
    for (var s = 0; s < L / 2 + 0.5; s += step) { out.push(pick(s)); if (L - s > L / 2 + 0.5) out.push(pick(L - s)); }
    return out;
  }
  function inTile(x, y, m) { return x > m && x < 48 - m && y > m && y < 48 - m; }

  function bankTile(mask) {
    var id = 'east-common-water-bank-' + K.bits(mask), ctx = new K.Ctx(id, 1), b = '';
    var rg = GR.region(mask, { mode: 'round', amp: 2.2, ph: 0.9 });
    if (rg) {
      var band = '', land = '', face = '', gold = '', deco = '', r = W.hashMask(mask, 1);
      rg.edges.forEach(function (e) {
        var P = e.pts;
        band += K.line(ext(P), W.FOAM, 7, K.sop(0.6)) + K.line(ext(W.offset(P, 6.5)), C.creamL, 0.7, K.sop(0.5));
        land += K.line(ext(P), C.damp, 9, K.sop(0.55)) + K.line(ext(P), C.mud, 3, K.sop(0.35));
        var N = W.norms(P), lo = P.map(function (p, i) { return [p[0], p[1] + 3.2 * Math.max(0, N[i][1])]; });
        face += K.path(W.facePoly(P, 3.2), C.mud) + K.line(GR.polyD(lo), C.creamL, 0.8, K.sop(0.7));
        gold += K.line(ext(P), C.gold, 1);
        for (var k = 0; k < 3; k++) {
          var a = GR.at(e, 0.22 + 0.28 * k + (r() - 0.5) * 0.1), x = a.p[0] - a.nx * 2.5, y = a.p[1] - a.ny * 2.5, kind = r();
          if (kind < 0.4 && inTile(x, y - 12, 6) && inTile(x, y, 6)) deco += W.reeds(x, y, r);
          else if (kind < 0.65 && inTile(x, y - 10, 6) && inTile(x, y, 6)) deco += W.calamus(x, y, r);
          else if (inTile(a.p[0], a.p[1], 4)) deco += W.pebble(a.p[0] + (r() - 0.5) * 2, a.p[1] + 0.6, 0.9 + r() * 0.5) + W.pebble(a.p[0] + 3.2, a.p[1] - 1.2, 0.6);
        }
      });
      b += K.clip(ctx, GR.outside(rg), land, true);
      b += K.clip(ctx, rg.fill, W.waterTex() + band + face) + gold + deco;
    }
    return item(id, b, 'water_bank', '自然河岸', mask, ['dual_grid', 'natural_bank', 'reeds', 'pebbles']);
  }

  function quayTile(mask) {
    var id = 'east-common-water-quay-' + K.bits(mask), ctx = new K.Ctx(id, 1), b = '';
    var rg = GR.region(mask, { mode: 'square', rr: 5 });
    if (rg) {
      var wet = '', cope = '', face = '', gold = '', deco = '', H = 8;
      rg.edges.forEach(function (e) {
        var P = e.pts, N = W.norms(P);
        wet += K.line(ext(P), W.DARK, 5, K.sop(0.35));
        var lo = P.map(function (p, i) { return [p[0], p[1] + H * Math.max(0, N[i][1])]; });
        var mid = P.map(function (p, i) { return [p[0], p[1] + H * 0.5 * Math.max(0, N[i][1])]; });
        var jf = '', jc = '';
        joints(P, 12).forEach(function (j) {
          var h = H * Math.max(0, j.n[1]);
          if (h > 0.5) jf += 'M' + f(j.p[0]) + ' ' + f(j.p[1]) + 'v' + f(h * 0.5) + 'M' + f(j.p[0] + 6 * Math.abs(j.n[1])) + ' ' + f(j.p[1] + h * 0.5) + 'v' + f(h * 0.5);
          jc += 'M' + K.pt(j.p) + 'L' + K.pt([j.p[0] - j.n[0] * 7, j.p[1] - j.n[1] * 7]);
        });
        face += K.path(W.facePoly(P, H), C.stone2) + K.line(GR.polyD(mid), C.umber, 0.6, K.sop(0.45)) + K.line(jf, C.umber, 0.6, K.sop(0.5)) +
          K.line(GR.polyD(lo), C.creamL, 0.9, K.sop(0.75));
        cope += K.line(ext(P), C.stone, 14) + K.line(ext(W.offset(P, -1.6)), C.rockL, 1.2, K.sop(0.6)) + K.line(jc, C.stone2, 0.8);
        gold += K.line(ext(P), C.gold, 1.1) + K.clip(ctx, GR.outside(rg), K.line(ext(W.offset(P, -7)), C.gold, 0.7, K.sop(0.75)), true);
        if (e.kind === 'straight') { var a = GR.at(e, 0.5); deco += W.bollard(a.p[0] - a.nx * 3.5 + 6, a.p[1] - a.ny * 3.5 + 1); }
      });
      b += K.clip(ctx, GR.outside(rg), cope, true);
      b += K.clip(ctx, rg.fill, W.waterTex() + wet + face) + gold + deco;
    }
    return item(id, b, 'water_quay', '条石驳岸', mask, ['dual_grid', 'stone_quay', 'coping', 'bollard']);
  }

  /** 驳岸石阶叠加件：dir = 's'（水在南，盖在 quay-0011 上）或 'n'（水在北，盖在 quay-1100 上）。 */
  function stepsOverlay(dir) {
    var id = 'east-common-water-quay-steps-' + dir, s = '', x0 = 15, x1 = 33, i;
    if (dir === 's') {
      s += K.rect(x0 - 3, 17, x1 - x0 + 6, 16, C.stone2, C.gold, 0.6);
      for (i = 0; i < 5; i++) { var yt = 18 + i * 4.4; s += K.rect(x0, yt, x1 - x0, 2.6, C.creamL, C.gold, 0.5) + K.rect(x0, yt + 2.6, x1 - x0, 1.8, C.stone2); }
      s += K.rect(x0, 40, x1 - x0, 2.2, C.stone2, C.gold, 0.4) + K.ell(24, 43.4, 11, 1.4, 'none', C.creamL, 0.8, K.sop(0.8));
      s += K.rect(x0 - 3, 17, 3, 22, C.stone, C.gold, 0.6) + K.rect(x1, 17, 3, 22, C.stone, C.gold, 0.6);
    } else {
      s += K.rect(x0 - 3, 14, x1 - x0 + 6, 18, C.stone2, C.gold, 0.6);
      for (i = 0; i < 5; i++) { var yb = 31 - i * 3.6; s += K.rect(x0, yb - 3.2, x1 - x0, 3.2, i % 2 ? C.stone : C.creamL, C.gold, 0.5); }
      s += K.rect(x0, 9, x1 - x0, 4, mix(C.water, C.teal, 0.3)) + K.line('M' + f(x0) + ' 13H' + f(x1), C.creamL, 0.8);
      s += K.rect(x0 - 3, 12, 3, 20, C.stone, C.gold, 0.6) + K.rect(x1, 12, 3, 20, C.stone, C.gold, 0.6);
    }
    var sym = K.tileSym(id, s);
    return { id: id, svg: sym.svg, name: '驳岸石阶', meta: {
      id: id, style: 'east', race: 'common', category: 'water', kind: 'water_quay_steps', facility: null, variant: dir === 's' ? 1 : 2,
      footprint: [1, 1], height_px: 0, anchor: sym.anchor, viewBox: sym.viewBox, tags: ['overlay', 'stone_steps', 'water_' + (dir === 's' ? 'south' : 'north')],
      roof: 'none', note: '叠加件：盖在 east-common-water-quay-' + (dir === 's' ? '0011（北岸南水）' : '1100（南岸北水）') + ' 上，石阶从压顶石一级级下到水面', name_zh: '驳岸石阶'
    } };
  }

  function item(id, body, kind, name, mask, tags) {
    var sym = K.tileSym(id, body);
    return { id: id, svg: sym.svg, name: name + ' ' + K.bits(mask), meta: {
      id: id, style: 'east', race: 'common', category: 'water', kind: kind, facility: null, variant: mask,
      footprint: [1, 1], height_px: 0, anchor: sym.anchor, viewBox: sym.viewBox,
      tags: tags.concat(['mask_' + K.bits(mask)], mask === 0 ? ['empty'] : []), roof: 'none',
      note: name + '水面双网格瓦片，四角 NW NE SW SE = ' + K.bits(mask) + '（1 = 水）' + (mask === 0 ? '，空瓦片透明占位' : '') + '；陆地一侧透明，水色 #6cc1b3 与码头一致',
      name_zh: name, mask: mask
    } };
  }

  function all() {
    var out = [], m;
    for (m = 0; m < 16; m++) out.push(bankTile(m));
    for (m = 0; m < 16; m++) out.push(quayTile(m));
    return out.concat([stepsOverlay('s'), stepsOverlay('n')]);
  }
  return { all: all, bankTile: bankTile, quayTile: quayTile, joints: joints };
});
