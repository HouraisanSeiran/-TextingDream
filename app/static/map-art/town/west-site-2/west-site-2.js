/*
 * 织梦 · 西式资源点素材第二批 —— 组装（3/4 斜俯视；美术样板，尚未接入游戏）
 * 形状拆在 shapes-*.js 小模块里，各自 C.def({...}) 登记；这里统一生成 symbol 与 meta。
 * 浏览器：先按顺序 <script> 引 core.js、shapes-*.js，再引本文件 → window.TownArt_westSite2。
 * Node：require('./west-site-2.js') 自动加载全部模块。
 */
(function (root) {
  'use strict';
  var MODULES = ['kit.js', 'shapes-mine.js', 'shapes-mine2.js', 'shapes-trade.js', 'shapes-craft.js', 'shapes-coast.js', 'shapes-crop.js', 'shapes-tree.js',
    'shapes-stock.js', 'shapes-stock2.js'];
  var isNode = typeof module !== 'undefined' && module.exports;
  var C;
  if (isNode) {
    C = require('./core.js');
    var fs = require('fs'), pth = require('path');
    MODULES.forEach(function (m) { if (fs.existsSync(pth.join(__dirname, m))) require('./' + m); });
  } else C = root.TownArtWS2_core;
  var CELL = 48;

  function pad2(n) { return n < 10 ? '0' + n : String(n); }
  function idOf(o) { return 'west-common-' + o.idKind + '-' + pad2(o.variant); }

  function build() {
    var out = [], seen = {};
    C.defs.forEach(function (o) {
      var id = idOf(o);
      if (seen[id]) throw new Error('重复 id ' + id);
      seen[id] = 1;
      var W = o.w * CELL, D = o.d * CELL, H = D + o.up;
      var ctx = new C.Ctx(id);
      var body = o.draw(ctx, W, D);
      var svg = '<symbol id="' + id + '" viewBox="0 0 ' + W + ' ' + H + '" overflow="visible">' +
        '<g transform="translate(0 ' + o.up + ')">' + body + '</g></symbol>';
      var meta = {
        id: id, style: 'west', race: 'common', category: o.cat, kind: o.idKind.replace(/^(site|prop|ground)-/, ''),
        name: o.name, resource: o.resource, subtype: o.subtype || null, facility: o.facility, variant: o.variant,
        footprint: [o.w, o.d], height_px: o.up, anchor: [W / 2, H], viewBox: [0, 0, W, H], tags: o.tags, roof: o.roof,
        note: o.note || (o.facility === null && o.cat !== 'site' ? '配套摆件/地面，无对应 FacilityKind' : '')
      };
      out.push({ id: id, svg: svg, meta: meta });
    });
    return out;
  }
  function sprite(items) {
    return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute;width:0;height:0;overflow:hidden">' +
      items.map(function (i) { return i.svg; }).join('\n') + '</svg>';
  }

  var api = { build: build, sprite: sprite, idOf: idOf, CELL: CELL, core: C, MODULES: MODULES };
  if (isNode) module.exports = api;
  else root.TownArt_westSite2 = api;
})(typeof window !== 'undefined' ? window : this);
