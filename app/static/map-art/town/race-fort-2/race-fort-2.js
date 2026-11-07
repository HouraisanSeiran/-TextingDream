/*
 * 织梦 · race-fort-2 入口：精灵荆棘棱垒 / 矮人石棱堡（8 向）+ 三族整体要塞地标（美术样板，尚未接入游戏）
 * 浏览器挂 window.TownArt_raceFort2；Node 用 module.exports。
 * 依赖（只读引用）：../race-fort/core.js、spoke.js、elf.js、dwarf.js、orc.js；本目录 bastion.js、elf2.js、dwarf2.js、orc2.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('../race-fort/core.js') : root.TownArtRF_core;
  var MODS = isNode ? [require('./elf2.js'), require('./dwarf2.js'), require('./orc2.js')] : [root.TownArtRF2_elf, root.TownArtRF2_dwarf, root.TownArtRF2_orc];
  var CELL = 48, MAX_UP = 144, MAX_UP_LANDMARK = 240;
  var FACILITIES = ['town_hall', 'lord_hall', 'market_hall', 'granary', 'cistern', 'well', 'mill', 'forge', 'smelter', 'kiln', 'tannery',
    'barracks', 'watchtower', 'city_wall', 'gate', 'temple', 'academy', 'infirmary', 'inn', 'caravanserai', 'stable', 'dock', 'warehouse',
    'mine_head', 'boiler_house', 'ward_tower', 'cemetery', 'bridge'];

  function types() {
    var out = [];
    MODS.forEach(function (M) { if (M) out = out.concat(M.types()); });
    return out;
  }
  function wrap(T) {
    var ctx = new C.Ctx(T.id), body = T.draw(ctx), w = T.fp[0], d = T.fp[1];
    var lim = T.category === 'landmark' ? MAX_UP_LANDMARK : MAX_UP;
    var up = Math.max(0, Math.ceil(-ctx.minY - d * CELL + 2));
    var over = up > lim;
    if (over) up = lim;
    var Hh = d * CELL + up;
    var m = { id: T.id, style: 'west', race: T.race, category: T.category, kind: T.kind, facility: T.facility || null, variant: T.variant || 1,
      footprint: [w, d], height_px: up, anchor: [w * 24, Hh], viewBox: [0, 0, w * CELL, Hh], tags: T.tags || [], roof: T.roof || 'none', note: T.note || '' };
    if (T.culture) m.culture = T.culture;
    if (T.attach) { m.attach_cells = T.attach; m.joins_spokes = T.thru; }
    return { id: T.id, meta: m, viewBox: m.viewBox, over: over, body: '<g transform="translate(0 ' + Hh + ')">' + body + '</g>' };
  }
  function symbols() { return types().map(wrap); }
  function symbolSVG(s) { return '<symbol id="' + s.id + '" viewBox="' + s.viewBox.join(' ') + '" overflow="visible">' + s.body + '</symbol>'; }
  function spriteSVG(list) {
    list = list || symbols();
    // 不能用 display:none：display:none 容器里的 clipPath 失效
    return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute;overflow:hidden">' + list.map(symbolSVG).join('') + '</svg>';
  }
  var API = { CELL: CELL, MAX_UP: MAX_UP, MAX_UP_LANDMARK: MAX_UP_LANDMARK, FACILITIES: FACILITIES, types: types, wrap: wrap, symbols: symbols, symbolSVG: symbolSVG, spriteSVG: spriteSVG };
  root.TownArt_raceFort2 = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
