/*
 * 织梦 · 城镇工业与基础设施素材汇总（东西两套，尚未接入游戏）
 *
 * 依赖（浏览器里按顺序先引）：infra-core.js → west-infra.js → east-infra.js → special-infra.js
 * 浏览器挂 window.TownArt_specialInfra；Node 用 module.exports。
 *
 * API：
 *   list()            全部定义（含 id）
 *   symbol(def)       单个 <symbol> 字符串
 *   meta(def)         单项 meta 对象（规范第 3 节格式）
 *   sprite()          整份 sprite.svg 文本
 *   metaAll()         meta 数组
 */
(function (root) {
  'use strict';
  var node = typeof module !== 'undefined' && module.exports;
  var C = node ? require('./infra-core.js') : root.TownArtInfraCore;
  var Wm = node ? require('./west-infra.js') : root.TownArtInfraWest;
  var Em = node ? require('./east-infra.js') : root.TownArtInfraEast;
  var CELL = C.CELL;

  function pad2(n) { return (n < 10 ? '0' : '') + n; }
  function idOf(d) { return d.style + '-common-' + d.idKind + '-' + pad2(d.variant); }

  var all = Wm.defs.concat(Em.defs).map(function (d) { d.id = idOf(d); return d; });

  function dims(d) {
    var W = d.w * CELL, D = d.d * CELL;
    return { W: W, D: D, H: D + d.up };
  }
  function symbol(d) {
    var m = dims(d), r = C.rng(C.hashStr(d.id));
    var body = d.draw(m.W, m.D, r, d.id);
    return '<symbol id="' + d.id + '" viewBox="0 0 ' + m.W + ' ' + m.H + '" overflow="visible">' +
      '<g transform="translate(0 ' + d.up + ')">' + body + '</g></symbol>';
  }
  function meta(d) {
    var m = dims(d);
    return {
      id: d.id, style: d.style, race: 'common', category: 'special', kind: d.kind, facility: d.facility,
      variant: d.variant, footprint: [d.w, d.d], height_px: d.up, anchor: [m.W / 2, m.H], viewBox: [0, 0, m.W, m.H],
      tags: d.tags.slice(), roof: d.roof, note: d.note
    };
  }
  function sprite() {
    return '<svg xmlns="http://www.w3.org/2000/svg" style="display:none">\n' +
      all.map(symbol).join('\n') + '\n</svg>\n';
  }
  function metaAll() { return all.map(meta); }

  var api = { CELL: CELL, list: function () { return all; }, symbol: symbol, meta: meta, sprite: sprite, metaAll: metaAll, core: C };
  if (node) module.exports = api;
  else root.TownArt_specialInfra = api;
})(typeof window !== 'undefined' ? window : this);
