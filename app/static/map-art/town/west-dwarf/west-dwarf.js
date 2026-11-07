/*
 * 织梦 · 城镇矮人族素材汇总（美术样板，尚未接入游戏）
 * 汇总 core.js / parts.js / houses-*.js / civic-*.js / tiles.js，生成 symbol 与 meta。
 * 浏览器：按顺序 <script src> 引 core.js、parts.js、houses-a.js、houses-b.js、houses-c.js、
 *         civic-a.js、civic-b.js、tiles.js、west-dwarf.js，之后用 window.TownArt_westDwarf。
 * Node：require('./west-dwarf.js')。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  function mod(file, name) {
    if (isNode) { try { return require(file); } catch (e) { if (e.code === 'MODULE_NOT_FOUND' && e.message.indexOf(file.slice(2)) >= 0) return null; throw e; } }
    return root[name] || null;
  }
  var C = mod('./core.js', 'TownArtWD_core');
  var HA = mod('./houses-a.js', 'TownArtWD_housesA');
  var HB = mod('./houses-b.js', 'TownArtWD_housesB');
  var HC = mod('./houses-c.js', 'TownArtWD_housesC');
  var SA = mod('./civic-a.js', 'TownArtWD_civicA');
  var SB = mod('./civic-b.js', 'TownArtWD_civicB');
  var TL = mod('./tiles.js', 'TownArtWD_tiles');
  var CELL = 48, MAX_UP = 144, VARIANTS = 3;
  var FACILITY = ['town_hall', 'lord_hall', 'market_hall', 'granary', 'cistern', 'well', 'mill', 'forge', 'smelter', 'kiln',
    'tannery', 'barracks', 'watchtower', 'city_wall', 'gate', 'temple', 'academy', 'infirmary', 'inn', 'caravanserai',
    'stable', 'dock', 'warehouse', 'mine_head', 'boiler_house', 'ward_tower', 'cemetery', 'bridge'];

  var HOUSE_TYPES = [].concat(HA ? HA.T : [], HB ? HB.T : [], HC ? HC.T : []);
  HOUSE_TYPES.sort(function (a, b) { return a.n - b.n; });
  var SPECIALS = [].concat(SA ? SA.S : [], SB ? SB.S : []);

  function pad2(n) { return (n < 10 ? '0' : '') + n; }
  function houseId(n, i) { return 'west-dwarf-house-' + pad2(n) + '-' + i; }

  /** 局部坐标（y=0 为占地前沿、向上为负）片段包成 symbol 记录 { id, viewBox, body, up, over, meta } */
  function wrap(id, fp, body, minY, meta) {
    var W = fp[0] * CELL, D = fp[1] * CELL;
    var up = Math.max(0, Math.ceil(-minY - D - 0.01));
    var H = D + up;
    meta.footprint = fp; meta.height_px = up; meta.anchor = [W / 2, H]; meta.viewBox = [0, 0, W, H];
    return { id: id, viewBox: [0, 0, W, H], up: up, over: up > MAX_UP,
      body: '<g transform="translate(0 ' + H + ')">' + body + '</g>', meta: meta };
  }
  function house(n, i) {
    var T = null;
    HOUSE_TYPES.forEach(function (t) { if (t.n === n) T = t; });
    if (!T) throw new Error('no house type ' + n);
    var id = houseId(n, i), ctx = new C.Ctx(id), fp = T.fps[i - 1];
    var v = { i: i, fp: fp, door: null, band: null }, p = HA.pal(ctx);
    v.door = p.door; v.band = p.band;
    var body = T.draw(ctx, v);
    return wrap(id, fp, body, ctx.minY, {
      id: id, style: 'west', race: 'dwarf', category: 'house', kind: T.kind, facility: null,
      variant: i, type: n, name: T.name + '·' + i, tags: T.tags.slice(), roof: T.roof, note: T.note || ''
    });
  }
  function houses() {
    var out = [];
    HOUSE_TYPES.forEach(function (t) { for (var i = 1; i <= t.fps.length; i++) out.push(house(t.n, i)); });
    return out;
  }
  /** 特殊建筑：每项 { id, name, facility, category?, kind, fp, roof, tags, note, draw(ctx) } */
  function specials() {
    return SPECIALS.map(function (S) {
      var ctx = new C.Ctx(S.id), body = S.draw(ctx);
      return wrap(S.id, S.fp, body, ctx.minY, {
        id: S.id, style: 'west', race: 'dwarf', category: S.category || 'special', kind: S.kind, facility: S.facility,
        variant: S.variant || 1, name: S.name, tags: (S.tags || []).slice(), roof: S.roof || 'none', note: S.note || ''
      });
    });
  }
  function tiles() { return TL ? TL.all(wrap) : []; }
  function symbols() { return houses().concat(specials(), tiles()); }

  function symbolSVG(s) {
    return '<symbol id="' + s.id + '" viewBox="' + s.viewBox.join(' ') + '" overflow="visible">' + s.body + '</symbol>';
  }
  function spriteSVG(list) {
    list = list || symbols();
    // 不能用 display:none：Chrome 下 display:none 容器里的 clipPath 失效
    return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute;overflow:hidden">' + list.map(symbolSVG).join('\n') + '</svg>';
  }

  var API = {
    CELL: CELL, MAX_UP: MAX_UP, VARIANTS: VARIANTS, FACILITY: FACILITY, core: C, HOUSE_TYPES: HOUSE_TYPES, SPECIALS: SPECIALS,
    houseId: houseId, house: house, houses: houses, specials: specials, tiles: tiles, symbols: symbols,
    symbolSVG: symbolSVG, spriteSVG: spriteSVG, wrap: wrap, tileMod: TL
  };
  root.TownArt_westDwarf = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
