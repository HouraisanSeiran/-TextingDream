/*
 * 织梦 · 阿拉伯风格绿洲水面双网格 × 16：水色 #a9b8ad（与 west-ground 对齐），沙岸带 + 湿沙线 + 芦苇丛（美术样板，尚未接入游戏）
 * 规则同道路（规范第 4、9 节）：水岸分界线过瓦片边中点并垂直于边；水面是地面层，不向上伸出。
 * 波纹按世界坐标对齐（周期 24），芦苇只放在离瓦片边 ≥ 6 px 处，不跨瓦片。
 * 浏览器挂 window.TownArtAB_water；Node 用 module.exports。依赖 core.js、tiles-road.js（复用分界线形状）。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  function dep(file, name) { return isNode ? require(file) : root[name]; }
  var C = dep('./core.js', 'TownArtAB_core'), R = dep('./tiles-road.js', 'TownArtAB_road');
  var P = C.PAL, f = C.f, WATER = '#a9b8ad', DEEP = '#97a89c', RIP = '#c6d1c6', BANK = '#ead7a8', WET = '#c9b78e';

  function band(d, w, col, op) { return d ? '<path d="' + d + '" fill="none" stroke="' + col + '" stroke-width="' + f(w) + '"' + (op != null ? ' stroke-opacity="' + f(op) + '"' : '') + ' stroke-linejoin="round"/>' : ''; }
  /** 芦苇丛：根部 (x, y)，几根弯秆 + 两三个香蒲穗 */
  function reeds(ctx, x, y, n) {
    var d = '', s = '', i;
    for (i = 0; i < n; i++) {
      var bx = x + (i - (n - 1) / 2) * 1.6, lean = ctx.rnd(-2.5, 2.5), h = ctx.rnd(6, 9.5);
      d += 'M' + f(bx) + ' ' + f(y) + 'q' + f(lean * 0.3) + ' ' + f(-h * 0.6) + ' ' + f(lean) + ' ' + f(-h);
      if (i % 2 === 0) s += C.ell(bx + lean * 0.85, y - h * 0.82, 0.9, 1.8, P.wood, 0.4);
    }
    return C.ell(x + 1, y + 0.5, n * 0.9 + 1, 1, P.ink, 0, 0.15) + C.line(d, 0.9, 1, P.palm) + C.line(d, 0.4, 0.6, P.palm2) + s;
  }
  /** 世界对齐的波纹：每 24 px 一组两道短弧 */
  function ripples() {
    var d = '';
    for (var y = 6; y < 48; y += 12) for (var x = ((y / 6) % 4 === 1 ? 4 : 16); x < 48; x += 24) d += 'M' + x + ' ' + y + 'q3 -1.6 6 0q3 1.6 6 0';
    return C.line(d, 0.8, 0.9, RIP);
  }
  /** 芦苇位置：瓦片边中点上分界线穿过时，在离边 12 px、向陆地一侧偏 6 px 处 */
  function reedSpots(mask) {
    var on = function (qx, qy) { return R.on(mask, qx, qy); }, out = [];
    if (on(0, 0) !== on(1, 0)) out.push([on(0, 0) ? 30 : 18, 12]);
    if (on(0, 1) !== on(1, 1)) out.push([on(0, 1) ? 30 : 18, 40]);
    if (on(0, 0) !== on(0, 1)) out.push([12, on(0, 0) ? 30 : 18]);
    if (on(1, 0) !== on(1, 1)) out.push([38, on(1, 0) ? 30 : 18]);
    return out;
  }
  function waterTile(ctx, mask) {
    var sh = R.shape(ctx, mask, 1.8);
    if (!sh) return '';
    var tile = C.rectD(0, 0, 48, 48), s = '';
    // 沙岸带（中心落在分界线上，外半在陆地、内半被水盖住）
    if (sh.outline) s += C.clipped(ctx, tile, band(sh.outline, 14, BANK, 1) + band(sh.outline, 7, WET, 1));
    s += '<path d="' + sh.fill + '" fill="' + WATER + '" fill-rule="' + sh.rule + '"/>';
    var inner = ripples();
    s += C.clipped(ctx, sh.fill, inner + (sh.outline ? band(sh.outline, 4, RIP, 0.9) : ''), sh.rule);
    if (sh.outline) s += C.line(sh.outline, 1.2, 0.8);
    reedSpots(mask).forEach(function (p, i) { if ((i + mask) % 2 === 0 || mask === 1 || mask === 14) s += reeds(ctx, p[0], p[1], 4 + (i % 2)); });
    return s;
  }
  function all(wrap) {
    var out = [];
    for (var m = 0; m < 16; m++) {
      var id = 'arab-common-water-oasis-' + C.bin(m), ctx = new C.Ctx(id);
      out.push(wrap(id, [1, 1], '<g transform="translate(0 -48)">' + waterTile(ctx, m) + '</g>', -48, {
        id: id, style: 'arab', race: 'common', category: 'water', kind: 'water_oasis', facility: null, variant: m, mask: m,
        name: '绿洲水面 ' + C.bin(m), tags: ['dual_grid', 'mask_' + C.bin(m), 'oasis', 'sand_bank', 'reeds'], roof: 'none', water_color: WATER,
        note: m === 0 ? '空瓦片（透明占位）' : '双网格渲染瓦片：1 = 该角是水；水色 ' + WATER + ' 与 west-ground 对齐；椰枣树用 prop 摆在岸上'
      }));
    }
    return out;
  }
  var API = { WATER: WATER, waterTile: waterTile, reeds: reeds, all: all };
  root.TownArtAB_water = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
