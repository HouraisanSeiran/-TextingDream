/*
 * 织梦 · 东方城防工事（east-fort）汇总入口。美术素材，尚未接入游戏。
 * 浏览器：依次 <script> 引 ../east-base/east-core.js、../east-base/houses-a.js、core.js、spoke.js、forts.js（可选）、本文件，
 *         之后 window.TownArt_eastFort.items() 返回全部 symbol；Node：require('./east-fort.js')。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    var opt = function (p) { try { return require(p); } catch (e) { if (e.code === 'MODULE_NOT_FOUND' && String(e.message).indexOf(p.slice(2)) >= 0) return null; throw e; } };
    module.exports = factory(require('./core.js'), require('./spoke.js'), opt('./forts.js'), opt('./forts-b.js'), opt('./moat.js'), opt('./passfort.js'));
  } else root.TownArt_eastFort = factory(root.TownArtFort_core, root.TownArtFort_spoke, root.TownArtFort_forts || null, root.TownArtFort_fortsB || null, root.TownArtFort_moat || null, root.TownArtFort_pass || null);
})(this, function (F, S, A, B2, M, PF) {
  'use strict';
  function items() {
    var out = S.items();
    [A, B2, M, PF].forEach(function (mod) { if (mod) out = out.concat(mod.items()); });
    return out;
  }
  function spriteSvg(list) {
    list = list || items();
    return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute;width:0;height:0;overflow:hidden">' +
      list.map(function (it) { return it.svg; }).join('') + '</svg>';
  }
  return { items: items, spriteSvg: spriteSvg, SORT: S.SORT, DIRS: S.DIRS, core: F };
});
