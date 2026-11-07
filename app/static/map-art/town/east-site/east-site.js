/*
 * 织梦 · 东方资源点（east-site）汇总入口（美术素材，尚未接入游戏）
 * 模块：core.js（画笔色板）→ kit.js（共用部件）→ sites-*.js（各类资源点）→ 本文件。
 * 浏览器按此顺序 <script src> 引入后挂 window.TownArt_eastSite；Node 里 require 本文件。
 * buildAll() 返回 { items: [{ id, name, svg, meta }], spriteSvg() }。
 */
(function (root, factory) {
  var MODS = ['wood', 'stone', 'mine', 'water', 'farm', 'rare'];
  if (typeof module !== 'undefined' && module.exports) {
    var fs = require('fs'), p = require('path');
    module.exports = factory(require('./core.js'), MODS.filter(function (m) { return fs.existsSync(p.join(__dirname, 'sites-' + m + '.js')); })
      .map(function (m) { return require('./sites-' + m + '.js'); }));
  } else {
    root.TownArt_eastSite = factory(root.TownArtES_core, MODS.map(function (m) { return root['TownArtES_' + m]; }).filter(Boolean));
  }
})(this, function (C, mods) {
  'use strict';
  function buildAll() {
    var items = [];
    mods.forEach(function (m) { items = items.concat(m.all()); });
    return {
      items: items,
      spriteSvg: function () {
        // 0×0 绝对定位，不用 display:none（否则 Chromium 里 clipPath 失效）
        return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute;width:0;height:0;overflow:hidden">\n' +
          items.map(function (it) { return it.svg; }).join('\n') + '\n</svg>\n';
      }
    };
  }
  return { CELL: C.CELL, core: C, buildAll: buildAll };
});
