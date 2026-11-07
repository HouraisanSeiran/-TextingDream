/*
 * 织梦 · 城镇内部地图 · 东方玄幻基础素材（east-base）汇总入口（美术素材，尚未接入游戏）
 *
 * 模块：east-core.js（画笔）→ houses-a.js / houses-b.js（民居）→ tiles.js（道路、城墙瓦片与城门楼、角楼）→ 本文件。
 * 浏览器按上面顺序 <script src> 引入后挂 window.TownArt_eastBase；Node 里 require 本文件即可。
 * buildAll() 返回 { items: [{ id, svg, meta }], spriteSvg() }，build.js 与 preview.html 都用它。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    var opt = function (p) { try { return require(p); } catch (e) { if (e.code === 'MODULE_NOT_FOUND' && String(e.message).indexOf(p.slice(2)) >= 0) return null; throw e; } };
    module.exports = factory(require('./east-core.js'), require('./houses-a.js'), opt('./houses-b.js'), opt('./tiles.js'), opt('./houses-c.js'));
  } else {
    root.TownArt_eastBase = factory(root.TownArtEast_core, root.TownArtEast_housesA, root.TownArtEast_housesB || null, root.TownArtEast_tiles || null, root.TownArtEast_housesC || null);
  }
})(this, function (E, HA, HB, TL, HC) {
  'use strict';
  var CELL = E.CELL;

  function pad2(n) { return (n < 10 ? '0' : '') + n; }

  // 民居：每种 kind 按 variants 出若干张；id = east-common-house-<kind>-<两位变体号>
  function houseItems() {
    var list = HA.HOUSES.concat(HB ? HB.HOUSES : [], HC ? HC.HOUSES : []), out = [], seed = 7100;
    list.forEach(function (H, hi) {
      H.variants.forEach(function (v, vi) {
        var fp = v.fp || (v.w ? [v.w, H.fp[1]] : H.fp), id = 'east-common-house-' + H.kind.replace(/_/g, '') + '-' + pad2(vi + 1);
        var sym = E.symbol(id, seed + hi * 97 + vi * 13, fp[0], fp[1], function (ctx) { return H.draw(ctx, v, fp); });
        out.push({
          id: id, svg: sym.svg, over: sym.over, name: H.name,
          meta: {
            id: id, style: 'east', race: 'common', category: 'house', kind: 'house_' + H.kind, facility: null,
            variant: vi + 1, footprint: fp, height_px: sym.up, anchor: sym.anchor, viewBox: sym.viewBox,
            tags: (H.tags || []).concat(v.tags || []), roof: v.roof || H.roof,
            note: H.name + '：' + (v.note || H.note || ''), name_zh: H.name
          }
        });
      });
    });
    return out;
  }

  function buildAll() {
    var items = houseItems();
    if (TL) items = items.concat(TL.items(E));
    var ids = {};
    items.forEach(function (it) { if (ids[it.id]) throw new Error('重复 symbol id: ' + it.id); ids[it.id] = 1; });
    return {
      items: items,
      spriteSvg: function () {
        // 不能用 display:none：Chrome/Edge 里 display:none 的 svg 中 symbol 内部的 clipPath 会失效
        return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute;width:0;height:0;overflow:hidden" aria-hidden="true">\n' + items.map(function (it) { return it.svg; }).join('\n') + '\n</svg>\n';
      }
    };
  }

  return { CELL: CELL, core: E, housesA: HA, housesB: HB, tiles: TL, buildAll: buildAll };
});
