/*
 * 织梦 · 阿拉伯风格（人族）特殊建筑与文化地标 —— 汇总入口（美术样板，尚未接入游戏）
 * 浏览器：先按顺序 <script> 引 core/parts/mass/towers/ground/b-*.js，再引本文件，挂 window.TownArt_arabSpecial。
 * Node：module.exports，同接口。
 * 接口：list() → defs；symbol(def) → '<symbol …>'；meta(def) → 元数据；sprite() → 整个 <svg>；metaAll()。
 */
(function (root) {
  'use strict';
  var N = typeof module !== 'undefined' && module.exports;
  var K = N ? require('./core.js') : root.TownArtAS_core;
  var MODS = ['b-religious.js', 'b-trade.js', 'b-civic.js', 'b-craft.js', 'b-infra.js', 'b-landmark.js'];
  var defs = [];
  if (N) {
    var fs = require('fs'), pth = require('path');
    MODS.forEach(function (m) {
      if (fs.existsSync(pth.join(__dirname, m))) defs = defs.concat(require('./' + m));
    });
  } else defs = (root.TownArtAS_defs || []).slice();

  function dims(d) {
    var W = d.fp[0] * K.CELL, D = d.fp[1] * K.CELL, up = d.up;
    return { W: W, D: D, up: up, H: D + up, gy: up };
  }
  function symbol(d) {
    var g = dims(d), ctx = { W: g.W, H: g.H, D: g.D, up: g.up, gy: g.gy, id: d.id, K: K };
    return '<symbol id="' + d.id + '" viewBox="0 0 ' + g.W + ' ' + g.H + '">' + d.draw(ctx) + '</symbol>';
  }
  function meta(d) {
    var g = dims(d);
    var m = {
      id: d.id, name: d.name, style: 'arab', race: 'common', category: d.category || 'special', kind: d.kind,
      facility: d.facility == null ? null : d.facility, variant: d.variant || 1,
      footprint: [d.fp[0], d.fp[1]], height_px: g.up, anchor: [g.W / 2, g.H], viewBox: [0, 0, g.W, g.H],
      tags: d.tags || [], roof: d.roof || 'flat_mud'
    };
    if (d.culture) m.culture = d.culture;
    if (d.note) m.note = d.note;
    return m;
  }
  function sprite() {
    return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0">\n' + defs.map(symbol).join('\n') + '\n</svg>\n';
  }
  var API = {
    list: function () { return defs; }, dims: dims, symbol: symbol, meta: meta, sprite: sprite,
    metaAll: function () { return defs.map(meta); }
  };
  if (N) module.exports = API; else root.TownArt_arabSpecial = API;
})(this);
