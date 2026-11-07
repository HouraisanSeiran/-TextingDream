/*
 * 织梦 · 城镇内部地图 · 东方玄幻地面层（east-ground）汇总入口（美术素材，尚未接入游戏）
 *
 * 模块：core.js（画笔、色板）→ grid.js（双网格几何）→ water.js / water-tiles.js（水面）→ ground.js（底纹、院坪）
 *       → prop-kit.js → props-plants / props-stone / props-farm / props-yard → props.js → 本文件。
 * 浏览器按上面顺序 <script src> 引入后挂 window.TownArt_eastGround；Node 里 require 本文件即可。
 * buildAll() 返回 { items: [{ id, svg, meta, name }], spriteSvg() }，build.js 与 preview.html 都用它。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = factory(require('./core.js'), require('./grid.js'), require('./water-tiles.js'), require('./ground.js'), require('./props.js'));
  } else {
    root.TownArt_eastGround = factory(root.TownArtEG_core, root.TownArtEG_grid, root.TownArtEG_waterTiles, root.TownArtEG_ground, root.TownArtEG_props);
  }
})(this, function (K, GR, WT, GD, PR) {
  'use strict';

  function buildAll() {
    var items = WT.all().concat(GD.all(), PR.all());
    return {
      items: items,
      spriteSvg: function () {
        // 不用 display:none：Chromium 下 display:none 的 svg 里的 clipPath 会失效，水面裁不出岸线
        return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute;width:0;height:0;overflow:hidden">\n' +
          items.map(function (it) { return it.svg; }).join('\n') + '\n</svg>\n';
      }
    };
  }

  /** 双网格选瓦片：grid[y][x] 为逻辑格布尔，渲染格 (i, j) 的四角是逻辑格 (i-1..i, j-1..j)，越界当 false。 */
  function maskAt(grid, i, j) {
    function g(x, y) { return !!(grid[y] && grid[y][x]); }
    return (g(i - 1, j - 1) ? 8 : 0) + (g(i, j - 1) ? 4 : 0) + (g(i - 1, j) ? 2 : 0) + (g(i, j) ? 1 : 0);
  }

  return { CELL: K.CELL, core: K, grid: GR, buildAll: buildAll, maskAt: maskAt, bits: K.bits };
});
