/*
 * 织梦 · 阿拉伯风格（人族）城镇基础素材汇总：民居、道路三档、城墙 + 城门 + 塔楼、辐条墙、绿洲水面、摆件（美术样板，尚未接入游戏）
 * 浏览器：按顺序 <script src> 引 core.js、parts.js、parts2.js、kit.js、houses-*.js、tiles-*.js、spoke.js、water.js、props.js、arab-base.js，
 *         之后用 window.TownArt_arabBase。Node：require('./arab-base.js')。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  function mod(file, name) {
    if (isNode) { try { return require(file); } catch (e) { if (e.code === 'MODULE_NOT_FOUND' && e.message.indexOf(file.slice(2)) >= 0) return null; throw e; } }
    return root[name] || null;
  }
  var C = mod('./core.js', 'TownArtAB_core');
  var HOUSE_MODS = [mod('./houses-a.js', 'TownArtAB_housesA'), mod('./houses-b.js', 'TownArtAB_housesB'), mod('./houses-c.js', 'TownArtAB_housesC'), mod('./houses-d.js', 'TownArtAB_housesD'), mod('./houses-e.js', 'TownArtAB_housesE')];
  var EXTRA = [mod('./tiles-road.js', 'TownArtAB_road'), mod('./tiles-wall.js', 'TownArtAB_wall'), mod('./spoke.js', 'TownArtAB_spoke'), mod('./water.js', 'TownArtAB_water'), mod('./props.js', 'TownArtAB_props')];
  var CELL = C.CELL, MAX_UP = C.MAX_UP;

  var HOUSE_TYPES = [];
  HOUSE_MODS.forEach(function (m) { if (m) HOUSE_TYPES = HOUSE_TYPES.concat(m.T); });
  HOUSE_TYPES.sort(function (a, b) { return a.n - b.n; });

  /** 局部坐标（y = 0 为占地前沿、向上为负）片段包成 symbol 记录 { id, viewBox, body, up, over, meta } */
  function wrap(id, fp, body, minY, meta) {
    var W = fp[0] * CELL, D = fp[1] * CELL;
    var up = Math.max(0, Math.ceil(-minY - D - 0.01));
    var H = D + up;
    meta.footprint = fp; meta.height_px = up; meta.anchor = [W / 2, H]; meta.viewBox = [0, 0, W, H];
    return { id: id, viewBox: [0, 0, W, H], up: up, over: up > (meta.maxUp || MAX_UP),
      body: '<g transform="translate(0 ' + H + ')">' + body + '</g>', meta: meta };
  }
  function houses() {
    var out = [];
    HOUSE_TYPES.forEach(function (T) {
      T.fps.forEach(function (fp, k) {
        var v = k + 1, id = 'arab-common-house-' + T.kind + '-' + C.pad2(v), ctx = new C.Ctx(id);
        var body = T.draw(ctx, v, fp);
        out.push(wrap(id, fp, body, ctx.minY, {
          id: id, style: 'arab', race: 'common', category: 'house', kind: 'house_' + T.kind, facility: null, variant: v,
          name: T.name + ' ' + v, tags: T.tags.slice(), roof: T.roof, note: (T.vnote && T.vnote[k]) || T.note || ''
        }));
      });
    });
    return out;
  }
  function symbols() {
    var list = houses();
    EXTRA.forEach(function (m) { if (m) list = list.concat(m.all(wrap)); });
    return list;
  }
  function symbolSVG(s) {
    return '<symbol id="' + s.id + '" viewBox="' + s.viewBox.join(' ') + '" overflow="visible">' + s.body + '</symbol>';
  }
  function spriteSVG(list) {
    return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute;overflow:hidden">' + list.map(symbolSVG).join('') + '</svg>';
  }
  var API = { CELL: CELL, MAX_UP: MAX_UP, HOUSE_TYPES: HOUSE_TYPES, wrap: wrap, houses: houses, symbols: symbols, symbolSVG: symbolSVG, spriteSVG: spriteSVG, core: C };
  root.TownArt_arabBase = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
