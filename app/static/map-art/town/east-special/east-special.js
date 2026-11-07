/*
 * 织梦 · 城镇特殊建筑（东方玄幻，3/4 斜俯视）汇总入口 —— 美术素材，尚未接入游戏
 *
 * 依赖同目录 core.js（公共画法）与各分类模块（civic.js、religion.js、trade.js、service.js）。
 * 浏览器：按顺序 <script src> 引 core.js、各模块、east-special.js，得到 window.TownArt_eastSpecial；
 * Node：require('./east-special.js')。
 *
 * API：
 *   list()            全部建筑定义的元数据数组（与 meta.json 同格式）
 *   symbol(id)        某个 symbol 的 { id, viewBox, anchor, body }
 *   symbolSvg(id)     <symbol id=… viewBox=…>…</symbol> 字符串
 *   spriteSvg()       整个 sprite.svg 文本
 */
(function (root) {
  'use strict';
  var node = typeof module !== 'undefined' && module.exports;
  var K = node ? require('./core.js') : root.TownArtEastSpecialCore;
  var mods = node
    ? ['./civic.js', './religion.js', './trade.js', './service.js'].map(function (p) { try { return require(p); } catch (e) { if (e.code === 'MODULE_NOT_FOUND' && e.message.indexOf(p.slice(2)) >= 0) return null; throw e; } })
    : [root.TownArtEastSpecialCivic, root.TownArtEastSpecialReligion, root.TownArtEastSpecialTrade, root.TownArtEastSpecialService];
  var STYLE = 'east', RACE = 'common';
  var defs = [];
  mods.forEach(function (m) { if (m && m.defs) defs = defs.concat(m.defs); });

  var cache = {};
  // id 只用小写字母、数字、连字符：kind 里的下划线换成连字符（town_hall → town-hall），meta 的 kind 字段保留原值
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
      id: s.id, style: STYLE, race: RACE, category: d.category || 'special', kind: d.kind,
      facility: d.facility === undefined ? null : d.facility, variant: d.variant,
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
    return '<svg xmlns="http://www.w3.org/2000/svg" style="display:none">\n' +
      defs.map(function (d) { return symbolSvg(idOf(d)); }).join('\n') + '\n</svg>\n';
  }

  var API = { core: K, defs: defs, idOf: idOf, list: list, symbol: symbol, symbolSvg: symbolSvg, spriteSvg: spriteSvg };
  if (node) module.exports = API;
  else root.TownArt_eastSpecial = API;
})(typeof window !== 'undefined' ? window : this);
