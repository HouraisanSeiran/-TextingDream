/*
 * 织梦 · 城镇建筑美术 · 西式中世纪城堡（west-castle）—— 汇总导出（尚未接入游戏）
 *
 * 依赖同目录的 core.js / walls.js / keep.js / towers.js / annex.js（浏览器里先用 <script> 依次引入）。
 * 浏览器挂 window.TownArt_westCastle；Node 用 module.exports。
 *
 *   entries()      全部部件（含 body），顺序即图册顺序
 *   symbol(e)      一个 <symbol> 字符串（内部 clipPath id 已加 symbol id 前缀）
 *   sprite()       整个 sprite.svg 文本
 *   meta()         meta.json 数组
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  function mod(name) {
    if (isNode) { try { return require('./' + name + '.js'); } catch (e) { if (e.code === 'MODULE_NOT_FOUND') return null; throw e; } }
    return (root.TownArtWC || {})[name] || null;
  }
  var C = mod('core'), W = mod('walls'), KP = mod('keep'), TW = mod('towers'), AX = mod('annex');
  var CELL = C.CELL;

  /** 每个生成函数都在 resetUid 之后调用，保证同一部件每次生成完全一样。 */
  function run(fn, arg) { C.resetUid(); return fn(arg); }

  function entries() {
    var out = [], m;
    if (KP) { out.push(run(KP.squareKeep)); out.push(run(KP.roundKeep)); }
    if (AX && AX.list) AX.list().forEach(function (fn) { out.push(run(fn)); });
    if (TW && TW.list) TW.list().forEach(function (fn) { out.push(run(fn)); });
    if (W) {
      for (m = 0; m < 16; m++) out.push(run(W.wallTile, m));
      for (m = 0; m < 16; m++) out.push(run(tileEntry('moat'), m));
      for (m = 0; m < 16; m++) out.push(run(tileEntry('yard'), m));
    }
    return out.map(normalize);
  }

  // 护城河 / 内院瓦片：walls.js 只返回图形，这里补齐 meta 字段
  function tileEntry(kind) {
    return function (mask) {
      var t = kind === 'moat' ? W.moatTile(mask) : W.yardTile(mask), b = W.bin4(mask);
      var isMoat = kind === 'moat';
      return {
        id: 'west-common-' + (isMoat ? 'moat' : 'yard') + '-' + b, category: isMoat ? 'castle' : 'road',
        kind: isMoat ? 'moat' : 'yard_flagstone', facility: null, variant: mask, footprint: [1, 1], up: t.up,
        tags: ['dual_grid', 'mask_' + b].concat(isMoat ? ['water'] : ['courtyard']), roof: 'none',
        note: mask ? (isMoat ? '护城河双网格瓦片：水面低于地面，北岸露石砌驳岸立面，岸顶压顶条石' : '内院石板地双网格瓦片，边缘一道路缘石')
          : '空瓦片（透明占位）',
        body: t.body
      };
    };
  }

  function normalize(e) {
    var w = e.footprint[0] * CELL, d = e.footprint[1] * CELL, up = e.up || 0;
    e.style = 'west'; e.race = 'common';
    e.viewBox = [0, 0, w, d + up];
    e.anchor = [w / 2, d + up];
    e.height_px = up;
    return e;
  }

  function symbol(e) {
    var body = String(e.body || '').split('__ID__').join(e.id + '-');
    return '<symbol id="' + e.id + '" viewBox="' + e.viewBox.join(' ') + '">' + body + '</symbol>';
  }

  function sprite(list) {
    list = list || entries();
    // 不用 display:none：Chrome 下 display:none 容器里的 clipPath 会失效
    return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute;overflow:hidden">\n' +
      '<!-- 织梦 · 西式中世纪城堡 town art（程序生成，勿手改；改 west-castle/*.js 后运行 node build.js） -->\n' +
      list.map(symbol).join('\n') + '\n</svg>\n';
  }

  var FIELDS = ['id', 'style', 'race', 'category', 'kind', 'facility', 'variant', 'footprint', 'height_px', 'anchor', 'viewBox', 'tags', 'roof', 'note'];
  function meta(list) {
    list = list || entries();
    return list.map(function (e) {
      var o = {};
      FIELDS.forEach(function (k) { o[k] = e[k] === undefined ? null : e[k]; });
      if (e.extra) Object.keys(e.extra).forEach(function (k) { o[k] = e.extra[k]; });
      return o;
    });
  }

  var API = { CELL: CELL, core: C, walls: W, keep: KP, towers: TW, annex: AX, entries: entries, symbol: symbol, sprite: sprite, meta: meta };
  if (isNode) module.exports = API;
  else root.TownArt_westCastle = API;
})(this);
