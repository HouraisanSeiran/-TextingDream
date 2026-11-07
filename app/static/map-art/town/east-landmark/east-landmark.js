/*
 * 织梦 · 东方玄幻（人族）文化地标（east-landmark，3/4 斜俯视）汇总入口 —— 美术素材，尚未接入游戏
 *
 * 模块顺序：lm-core.js（公共画法，= east-special/core.js 的副本）→ lm-parts.js（宗教部件）→ lm-extra.js（地标部件）
 *   → lm-taoist.js / lm-buddhist.js / lm-civic.js / lm-fantasy.js（各类地标定义）→ 本文件。
 * 浏览器：按上面顺序 <script src>，得到 window.TownArt_eastLandmark；Node：require('./east-landmark.js')。
 *
 * API：list() 元数据数组（同 meta.json）；symbol(id) → { id, viewBox, anchor, body }；symbolSvg(id)；spriteSvg()
 */
(function (root) {
  'use strict';
  var node = typeof module !== 'undefined' && module.exports;
  var K = node ? require('./lm-core.js') : root.TownArtEastLandmarkCore;
  var NAMES = ['taoist', 'buddhist', 'civic', 'fantasy'];
  var GLOB = { taoist: 'TownArtEastLandmarkTaoist', buddhist: 'TownArtEastLandmarkBuddhist', civic: 'TownArtEastLandmarkCivic', fantasy: 'TownArtEastLandmarkFantasy' };
  var mods = NAMES.map(function (n) {
    if (!node) return root[GLOB[n]] || null;
    var p = './lm-' + n + '.js';
    try { return require(p); } catch (e) { if (e.code === 'MODULE_NOT_FOUND' && e.message.indexOf('lm-' + n + '.js') >= 0) return null; throw e; }
  });
  var STYLE = 'east', RACE = 'common';
  var defs = [];
  mods.forEach(function (m) { if (m && m.defs) defs = defs.concat(m.defs); });

  var cache = {};
  function idOf(d) { return STYLE + '-' + RACE + '-' + d.kind.replace(/_/g, '-') + '-' + (d.variant < 10 ? '0' : '') + d.variant; }
  function symbol(id) {
    if (cache[id]) return cache[id];
    var d = defs.filter(function (x) { return idOf(x) === id; })[0];
    if (!d) return null;
    return (cache[id] = K.symbolOf(d, STYLE, RACE));
  }
  function metaOf(d) {
    var s = symbol(idOf(d));
    var m = {
      id: s.id, style: STYLE, race: RACE, category: 'landmark', kind: d.kind,
      facility: d.facility === undefined ? null : d.facility, culture: d.culture || null, variant: d.variant,
      footprint: d.fp.slice(), height_px: d.up, anchor: s.anchor, viewBox: s.viewBox,
      tags: (d.tags || []).slice(), roof: d.roof || 'none', name_zh: d.name
    };
    if (d.note) m.note = d.note;
    return m;
  }
  function list() { return defs.map(metaOf); }
  function symbolSvg(id) {
    var s = symbol(id);
    return '<symbol id="' + s.id + '" viewBox="' + s.viewBox.join(' ') + '">' + s.body + '</symbol>';
  }
  function spriteSvg() {
    return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute;width:0;height:0;overflow:hidden" aria-hidden="true">\n' +
      defs.map(function (d) { return symbolSvg(idOf(d)); }).join('\n') + '\n</svg>\n';
  }

  var API = { core: K, defs: defs, idOf: idOf, list: list, symbol: symbol, symbolSvg: symbolSvg, spriteSvg: spriteSvg };
  if (node) module.exports = API;
  else root.TownArt_eastLandmark = API;
})(typeof window !== 'undefined' ? window : this);
