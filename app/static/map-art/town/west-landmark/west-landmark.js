/*
 * 织梦 · 西式（人族）文化地标汇总（3/4 斜俯视，category=landmark；美术样板，尚未接入游戏）
 * 依赖 core.js 与各地标模块（sacred.js、castles.js、roman.js、extra.js）。
 * 浏览器：按顺序 <script src> 引 core.js、各模块、west-landmark.js，之后用 window.TownArt_westLandmark；
 * Node：require('./west-landmark.js')。
 *   list()        → 全部 def
 *   idOf(def)     → symbol id
 *   symbol(def)   → '<symbol id=... viewBox=...>...</symbol>'
 *   meta(def)     → meta.json 的一项
 *   svg(def, k)   → 独立 <svg>（预览用）
 *   spriteSVG()   → 包含全部 symbol 的隐藏 <svg>
 * def 字段：kind, variant, (id 可覆盖), name, fp:[w,d], up, seed, facility, culture, roof, tags, note, draw(c)
 * draw(c) 的 c = { rnd, W, H, up, id }：占地区 y = up..H，锚点 (W/2, H)；建筑前沿一般放在 H-5，给投影留位。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  function mod(file, name) {
    if (isNode) { try { return require(file); } catch (e) { if (e.code === 'MODULE_NOT_FOUND' && e.message.indexOf(file.slice(2)) >= 0) return null; throw e; } }
    return root[name] || null;
  }
  var P = mod('./core.js', 'TownArtWL_core');
  var MODS = [
    mod('./sacred.js', 'TownArtWL_sacred'),
    mod('./castles.js', 'TownArtWL_castles'),
    mod('./roman.js', 'TownArtWL_roman'),
    mod('./extra.js', 'TownArtWL_extra')
  ];
  var CELL = 48, MAX_UP = 240, MAX_FP = 6;
  var FACILITY = ['town_hall', 'lord_hall', 'market_hall', 'granary', 'cistern', 'well', 'mill', 'forge', 'smelter', 'kiln', 'tannery',
    'barracks', 'watchtower', 'city_wall', 'gate', 'temple', 'academy', 'infirmary', 'inn', 'caravanserai', 'stable', 'dock',
    'warehouse', 'mine_head', 'boiler_house', 'ward_tower', 'cemetery', 'bridge'];

  function pad(n) { return n < 10 ? '0' + n : String(n); }
  function idOf(d) { return 'west-common-' + (d.id || (d.kind.replace(/_/g, '-') + '-' + pad(d.variant))); }
  function dims(d) { return { W: d.fp[0] * CELL, H: d.fp[1] * CELL + d.up }; }
  function list() {
    var all = [];
    MODS.forEach(function (m) { if (m) all = all.concat(m); });
    return all;
  }
  function body(d) {
    var s = dims(d);
    return d.draw({ rnd: P.rng(d.seed), W: s.W, H: s.H, up: d.up, id: idOf(d) });
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
      id: idOf(d), style: 'west', race: 'common', category: 'landmark', kind: d.kind, facility: d.facility == null ? null : d.facility,
      culture: d.culture, variant: d.variant, footprint: d.fp.slice(), height_px: d.up, anchor: [s.W / 2, s.H],
      viewBox: [0, 0, s.W, s.H], tags: (d.tags || []).slice(), roof: d.roof || 'none', name_zh: d.name
    };
    if (d.note) m.note = d.note;
    return m;
  }
  function spriteSVG(defs) {
    // 不用 display:none：Chrome 下 display:none 容器里的 clipPath 会失效
    return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute;overflow:hidden">' +
      (defs || list()).map(symbol).join('\n') + '</svg>';
  }
  var api = {
    CELL: CELL, MAX_UP: MAX_UP, MAX_FP: MAX_FP, FACILITY: FACILITY, P: P,
    list: list, idOf: idOf, dims: dims, symbol: symbol, svg: svg, meta: meta, spriteSVG: spriteSVG
  };
  root.TownArt_westLandmark = api;
  if (isNode) module.exports = api;
})(typeof window !== 'undefined' ? window : this);
