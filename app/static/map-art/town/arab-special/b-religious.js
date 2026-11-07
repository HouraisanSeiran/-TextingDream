/*
 * 宗教类：清真寺 ×2、宣礼塔单塔。def: {id,name,fp,up,kind,facility,tags,roof,note,draw(ctx)}
 * 浏览器追加到 window.TownArtAS_defs；Node 用 module.exports 导出数组。
 */
(function (root) {
  'use strict';
  var N = typeof module !== 'undefined' && module.exports;
  var K = N ? require('./core.js') : root.TownArtAS_core;
  var P = N ? require('./parts.js') : root.TownArtAS_parts;
  var Ms = N ? require('./mass.js') : root.TownArtAS_mass;
  var T = N ? require('./towers.js') : root.TownArtAS_towers;
  var G = N ? require('./ground.js') : root.TownArtAS_ground;
  var F = N ? require('./facade.js') : root.TownArtAS_facade;
  var C = K.C;
  var defs = [];

  /** 清真寺通用：o.dome 穹顶色，o.minL/minR 宣礼塔，o.kind 穹顶形 */
  function mosque(c, o) {
    var W = c.W, H = c.H, gy = c.gy, s = '';
    var cx = W / 2;
    if (o.minR) s += T.minaret(W - 18, gy + 40, 6, 138, { kind: o.minKind, tiers: 2, capFill: o.dome });
    if (o.minL) s += T.minaret(18, gy + 40, 6, 138, { kind: o.minKind, tiers: 2, capFill: o.dome });
    // 礼拜殿
    s += Ms.block({ x0: 22, x1: W - 22, yb: gy + 4, yf: gy + 60, h: 52, band: 4, W: W, H: H });
    s += F.windows(30, cx - 24, gy + 18, 5, 8, 3) + F.windows(cx + 24, W - 30, gy + 18, 5, 8, 3);
    // 穹顶（鼓座 + 穹顶），坐在顶面中央
    var dy = gy - 18;
    if (o.side) { s += Ms.drum(42, dy + 6, 11, 6, C.lime, 2) + Ms.dome(42, dy, 12, 18, o.dome, 'pointed'); s += Ms.drum(W - 42, dy + 6, 11, 6, C.lime, 2) + Ms.dome(W - 42, dy, 12, 18, o.dome, 'pointed'); }
    s += Ms.drum(cx, dy, 30, 13, C.lime);
    s += P.tileBand(cx - 30, cx + 30, dy - 13, 3.5, true);
    s += Ms.dome(cx, dy - 13, 32, o.dh || 56, o.dome, o.kind);
    // 礼拜殿门楼
    s += F.pishtaq(cx - 24, cx + 24, gy + 32, gy - 14, { door: false, alt: o.alt });
    // 前院（内拱廊 + 八角净池）
    s += Ms.court({
      x0: 6, x1: W - 6, yb: gy + 56, yf: H - 3, h: 24, t: 10, riwaq: true, lip: 2, W: W, H: H,
      content: function (q) { return G.pool(q.cx, q.cy - 3, 16, 9) + G.palm(q.ix0 + 12, q.iyB - 2, 26, 5) + G.palm(q.ix1 - 12, q.iyB - 2, 26, 9); }
    });
    s += F.arcade(12, cx - 22, H - 6, 14, 3, C.lime2) + F.arcade(cx + 22, W - 12, H - 6, 14, 3, C.lime2);
    s += F.pishtaq(cx - 17, cx + 17, H - 3, H - 38, { alt: !o.alt });
    return s;
  }

  defs.push({
    id: 'arab-common-mosque-01', name: '清真寺（绿松石穹顶）', fp: [4, 3], up: 140, kind: 'mosque', facility: 'temple',
    tags: ['dome', 'minaret', 'courtyard', 'ablution_pool'], roof: 'flat_mud',
    note: '穹顶无对应 RoofId，按平顶 flat_mud 记',
    draw: function (c) { return mosque(c, { dome: C.turq, minR: true, kind: 'pointed' }); }
  });

  defs.push({
    id: 'arab-common-mosque-02', name: '清真寺（双塔钴蓝穹顶）', fp: [4, 3], up: 140, kind: 'mosque', facility: 'temple', variant: 2,
    tags: ['dome', 'minaret', 'twin_minaret', 'courtyard', 'ablution_pool'], roof: 'flat_mud',
    note: '穹顶无对应 RoofId，按平顶 flat_mud 记；方形马格里布式宣礼塔',
    draw: function (c) { return mosque(c, { dome: C.cobalt2, minL: true, minR: true, minKind: 'square', kind: 'onion', side: true, alt: true, dh: 50 }); }
  });
  defs.push({
    id: 'arab-common-minaret-01', name: '宣礼塔（单塔）', fp: [1, 1], up: 144, kind: 'minaret', facility: 'temple',
    tags: ['minaret', 'tower'], roof: 'none', note: '独立宣礼塔，可配小礼拜点',
    draw: function (c) {
      var s = K.boxShadow(8, 40, c.H - 22, c.H - 4, 8, c.W, c.H);
      s += K.rect(5, c.H - 16, 38, 13, C.lime2, 1.3) + P.tileBand(6, 42, c.H - 13, 4, true);
      return s + T.minaret(24, c.H - 14, 7, 132, { kind: 'round', tiers: 2, capFill: C.turq });
    }
  });

  if (N) module.exports = defs;
  else root.TownArtAS_defs = (root.TownArtAS_defs || []).concat(defs);
})(this);
