/*
 * 织梦 · 东方资源点第二批（east-site-2）汇总入口（美术素材，尚未接入游戏）
 * 模块：core.js（画笔色板）→ kit.js / kit2.js（共用部件，复制自 east-site）→ kit3.js（本批新部件）→ s-*.js（各资源点）→ 本文件。
 * 浏览器按此顺序 <script src> 引入后挂 window.TownArt_eastSite2；Node 里 require 本文件。
 * buildAll() 返回 { items: [{ id, name, svg, meta, scene }], spriteSvg() }。
 */
(function (root, factory) {
  var MODS = ['wool', 'mine', 'stone', 'hot', 'craft', 'wine', 'coal', 'field', 'field2', 'herd', 'herd2'];
  if (typeof module !== 'undefined' && module.exports) {
    var fs = require('fs'), p = require('path');
    module.exports = factory(require('./core.js'), MODS.filter(function (m) { return fs.existsSync(p.join(__dirname, 's-' + m + '.js')); })
      .map(function (m) { return require('./s-' + m + '.js'); }));
  } else {
    root.TownArt_eastSite2 = factory(root.TownArtES2_core, MODS.map(function (m) { return root['TownArtES2_' + m]; }).filter(Boolean));
  }
})(this, function (C, mods) {
  'use strict';
  function buildAll() {
    var items = [], scenes = [];
    mods.forEach(function (m) { items = items.concat(m.all()); scenes = scenes.concat(m.scenes || []); });
    return {
      items: items,
      scenes: scenes,
      spriteSvg: function () {
        // 0×0 绝对定位，不用 display:none（否则 Chromium 里 clipPath 失效）
        return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute;width:0;height:0;overflow:hidden">\n' +
          items.map(function (it) { return it.svg; }).join('\n') + '\n</svg>\n';
      }
    };
  }
  return { CELL: C.CELL, core: C, buildAll: buildAll };
});
