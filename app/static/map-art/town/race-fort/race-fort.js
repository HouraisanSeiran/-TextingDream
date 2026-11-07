/*
 * 织梦 · race-fort 入口：精灵 / 矮人 / 兽人三族辐条城墙、节点塔、防御工事（美术样板，尚未接入游戏）
 * 浏览器挂 window.TownArt_raceFort；Node 用 module.exports。
 * 依赖 core.js、spoke.js 与各族模块（elf.js / dwarf.js / orc.js，缺哪个就跳过哪个）。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  function req(n, g) { if (isNode) { try { return require(n); } catch (e) { if (e.code === 'MODULE_NOT_FOUND' && e.message.indexOf(n) >= 0) return null; throw e; } } return root[g] || null; }
  var C = req('./core.js', 'TownArtRF_core'), K = req('./spoke.js', 'TownArtRF_spoke');
  var RACES = { elf: req('./elf.js', 'TownArtRF_elf'), dwarf: req('./dwarf.js', 'TownArtRF_dwarf'), orc: req('./orc.js', 'TownArtRF_orc') };
  var CELL = 48, MAX_UP = 144, MAX_UP_LANDMARK = 240;
  var FACILITIES = ['town_hall', 'lord_hall', 'market_hall', 'granary', 'cistern', 'well', 'mill', 'forge', 'smelter', 'kiln', 'tannery',
    'barracks', 'watchtower', 'city_wall', 'gate', 'temple', 'academy', 'infirmary', 'inn', 'caravanserai', 'stable', 'dock', 'warehouse',
    'mine_head', 'boiler_house', 'ward_tower', 'cemetery', 'bridge'];

  /** 通用：每族的辐条 8 张 + 节点；族模块用 M.types() 追加自己的塔与工事 */
  function wallTypes(race, M) {
    var out = [];
    K.DIRS.forEach(function (d) {
      out.push({ id: 'west-' + race + '-wallspoke-' + d, race: race, category: 'wall', kind: 'wall_spoke', facility: 'city_wall', fp: [1, 1],
        tags: ['spoke', 'dir_' + d, 'order_' + K.ORDER[d]], roof: 'none', sort: K.ORDER[d],
        note: '辐条半段墙：格中心 → ' + (d.length === 1 ? '格边中点' : '格角') + '；同格排序键 = 前沿 y + ' + K.ORDER[d],
        draw: function (ctx) { return M.spoke(ctx, d); } });
    });
    (M.NODES || [1, 2]).forEach(function (v) {
      out.push({ id: 'west-' + race + '-wallnode-' + ('0' + v).slice(-2), race: race, category: 'wall', kind: 'wall_node', facility: 'city_wall', fp: [1, 1],
        tags: ['node', 'order_0.2'], roof: 'none', sort: 0.2, variant: v, note: (M.NODE_NOTES || {})[v] || '墙节点墩子',
        draw: function (ctx) { return M.node(ctx, v); } });
    });
    return out;
  }
  function types() {
    var out = [];
    ['elf', 'dwarf', 'orc'].forEach(function (r) {
      var M = RACES[r];
      if (!M) return;
      out = out.concat(wallTypes(r, M), M.types ? M.types() : []);
    });
    return out;
  }
  function wrap(T) {
    var ctx = new C.Ctx(T.id), body = T.draw(ctx), w = T.fp[0], d = T.fp[1];
    var lim = T.category === 'landmark' || T.landmark ? MAX_UP_LANDMARK : MAX_UP;
    var up = Math.max(0, Math.ceil(-ctx.minY - d * CELL + 2));
    if (up > lim) up = lim;
    var Hh = d * CELL + up;
    var m = { id: T.id, style: 'west', race: T.race, category: T.category, kind: T.kind, facility: T.facility || null, variant: T.variant || 1,
      footprint: [w, d], height_px: up, anchor: [w * 24, Hh], viewBox: [0, 0, w * CELL, Hh], tags: T.tags || [], roof: T.roof || 'none', note: T.note || '' };
    if (T.culture) m.culture = T.culture;
    if (T.sort != null) m.sort_offset = T.sort;
    return { id: T.id, meta: m, viewBox: m.viewBox, body: '<g transform="translate(0 ' + Hh + ')">' + body + '</g>' };
  }
  function symbols() { return types().map(wrap); }
  function symbolSVG(s) { return '<symbol id="' + s.id + '" viewBox="' + s.viewBox.join(' ') + '" overflow="visible">' + s.body + '</symbol>'; }
  function spriteSVG(list) {
    list = list || symbols();
    // 不能用 display:none：display:none 容器里的 clipPath 失效
    return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute;overflow:hidden">' + list.map(symbolSVG).join('\n') + '</svg>';
  }
  var API = { CELL: CELL, MAX_UP: MAX_UP, FACILITIES: FACILITIES, core: C, spoke: K, races: RACES, types: types, wrap: wrap, symbols: symbols, symbolSVG: symbolSVG, spriteSVG: spriteSVG };
  root.TownArt_raceFort = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
