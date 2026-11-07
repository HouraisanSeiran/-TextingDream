/*
 * 织梦 · 西式特殊建筑汇总（3/4 斜俯视；美术样板，尚未接入游戏）
 * 依赖 prims.js 与各建筑模块（civic.js、trade.js、service.js）。浏览器里按顺序 <script src> 引入后挂 window.TownArt_westSpecial；
 * Node 用 module.exports。
 *   list()          → 全部 def（含 meta 字段）
 *   symbol(def)     → '<symbol id=... viewBox=...>...</symbol>'
 *   meta(def)       → meta.json 的一项
 *   svg(def)        → 独立 <svg>（预览用）
 */
(function (root) {
  'use strict';
  var node = typeof module !== 'undefined' && module.exports;
  var P = node ? require('./prims.js') : root.TownArtWS_prims;
  var mods = node ? [require('./civic.js'), require('./trade.js'), require('./service.js')]
    : [root.TownArtWS_civic, root.TownArtWS_trade, root.TownArtWS_service];
  var CELL = P.CELL;
  var FACILITY = ['town_hall', 'lord_hall', 'market_hall', 'granary', 'cistern', 'well', 'mill', 'forge', 'smelter', 'kiln', 'tannery',
    'barracks', 'watchtower', 'city_wall', 'gate', 'temple', 'academy', 'infirmary', 'inn', 'caravanserai', 'stable', 'dock',
    'warehouse', 'mine_head', 'boiler_house', 'ward_tower', 'cemetery', 'bridge'];

  function pad(n) { return n < 10 ? '0' + n : String(n); }
  function idOf(d) { return 'west-common-' + d.kind.replace(/_/g, '-') + '-' + pad(d.variant); }
  function dims(d) { var W = d.fp[0] * CELL, H = d.fp[1] * CELL + d.up; return { W: W, H: H }; }
  function list() {
    var all = [];
    mods.forEach(function (m) { if (m) all = all.concat(m); });
    return all;
  }
  function body(d) {
    var s = dims(d), id = idOf(d);
    return d.draw({ rnd: P.rng(d.seed), W: s.W, H: s.H, up: d.up, id: id });
  }
  function symbol(d) {
    var s = dims(d);
    return '<symbol id="' + idOf(d) + '" viewBox="0 0 ' + s.W + ' ' + s.H + '">' + body(d) + '</symbol>';
  }
  function svg(d, scale) {
    var s = dims(d), k = scale || 1;
    return '<svg xmlns="http://www.w3.org/2000/svg" width="' + s.W * k + '" height="' + s.H * k + '" viewBox="0 0 ' + s.W + ' ' + s.H + '">' + body(d) + '</svg>';
  }
  function meta(d) {
    var s = dims(d);
    var m = {
      id: idOf(d), style: 'west', race: 'common', category: d.category || 'special', kind: d.kind, facility: d.facility,
      variant: d.variant, footprint: d.fp.slice(), height_px: d.up, anchor: [s.W / 2, s.H], viewBox: [0, 0, s.W, s.H],
      tags: (d.tags || []).slice(), roof: d.roof || 'none', name_zh: d.name
    };
    if (d.note) m.note = d.note;
    return m;
  }
  var api = { list: list, symbol: symbol, svg: svg, meta: meta, idOf: idOf, dims: dims, FACILITY: FACILITY, P: P };
  if (node) module.exports = api;
  else root.TownArt_westSpecial = api;
})(typeof window !== 'undefined' ? window : this);
