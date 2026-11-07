/*
 * 织梦 · 城镇西式基础素材汇总（美术样板，尚未接入游戏）
 * 汇总 common.js / houses-*.js / tiles.js，生成 symbol 与 meta。
 * 浏览器：按顺序 <script src> 引 common.js、houses-a.js、houses-b.js、houses-c.js、tiles.js、west-base.js，
 *         之后用 window.TownArt_westBase。Node：require('./west-base.js')。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  function mod(file, name) {
    if (isNode) { try { return require(file); } catch (e) { if (e.code === 'MODULE_NOT_FOUND') return null; throw e; } }
    return root[name] || null;
  }
  var C = mod('./common.js', 'TownArtWB_common');
  var HA = mod('./houses-a.js', 'TownArtWB_housesA');
  var HB = mod('./houses-b.js', 'TownArtWB_housesB');
  var HC = mod('./houses-c.js', 'TownArtWB_housesC');
  var TL = mod('./tiles.js', 'TownArtWB_tiles');
  var CELL = 48, MAX_UP = 144, VARIANTS = 3;

  var HOUSE_TYPES = [].concat(HA ? HA.T : [], HB ? HB.T : [], HC ? HC.T : []);
  HOUSE_TYPES.sort(function (a, b) { return a.n - b.n; });

  function pad2(n) { return (n < 10 ? '0' : '') + n; }
  function houseId(n, i) { return 'west-common-house-' + pad2(n) + '-' + i; }

  /**
   * 把局部坐标（y=0 为占地前沿、向上为负）的片段包成 symbol 记录。
   * 返回 { id, viewBox:[0,0,W,H], body, up, meta }
   */
  function wrap(id, fp, body, minY, meta) {
    var W = fp[0] * CELL, D = fp[1] * CELL;
    var up = Math.max(0, Math.ceil(-minY - D - 0.01));
    var H = D + up;
    meta.footprint = fp; meta.height_px = up; meta.anchor = [W / 2, H]; meta.viewBox = [0, 0, W, H];
    return { id: id, viewBox: [0, 0, W, H], up: up, over: up > MAX_UP,
      body: '<g transform="translate(0 ' + H + ')">' + body + '</g>', meta: meta };
  }

  /** 一种民居的一个变体。i = 1..VARIANTS */
  function house(n, i) {
    var T = null;
    HOUSE_TYPES.forEach(function (t) { if (t.n === n) T = t; });
    if (!T) throw new Error('no house type ' + n);
    var id = houseId(n, i), ctx = new C.Ctx(id);
    var v = { i: i, flip: i === 2, pal: HA.pal(ctx) };
    var body = T.draw(ctx, v);
    return wrap(id, T.fp, body, ctx.minY, {
      id: id, style: 'west', race: 'common', category: 'house', kind: T.kind, facility: null,
      variant: i, type: n, name: T.name, tags: T.tags.slice(), roof: T.roof, note: T.note || ''
    });
  }
  function houses() {
    var out = [];
    HOUSE_TYPES.forEach(function (t) { for (var i = 1; i <= VARIANTS; i++) out.push(house(t.n, i)); });
    return out;
  }
  function tiles() { return TL ? TL.all(wrap) : []; }
  function symbols() { return houses().concat(tiles()); }

  function symbolSVG(s) {
    return '<symbol id="' + s.id + '" viewBox="' + s.viewBox.join(' ') + '" overflow="visible">' + s.body + '</symbol>';
  }
  function spriteSVG(list) {
    list = list || symbols();
    // 不能用 display:none：Chrome 下 display:none 容器里的 clipPath 失效，纹理会溢出面外
    return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute;overflow:hidden">' + list.map(symbolSVG).join('\n') + '</svg>';
  }

  var API = {
    CELL: CELL, MAX_UP: MAX_UP, VARIANTS: VARIANTS, common: C, HOUSE_TYPES: HOUSE_TYPES,
    houseId: houseId, house: house, houses: houses, tiles: tiles, symbols: symbols,
    symbolSVG: symbolSVG, spriteSVG: spriteSVG, wrap: wrap, tileMod: TL
  };
  root.TownArt_westBase = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
