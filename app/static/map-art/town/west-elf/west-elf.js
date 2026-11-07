/*
 * 织梦 · 城镇西式精灵族素材汇总（美术样板，尚未接入游戏）
 * 汇总 core.js / parts.js / forms.js / houses-*.js / special-*.js / tiles.js，生成 symbol 与 meta。
 * 浏览器：按顺序 <script src> 引 core.js、parts.js、forms.js、houses-a.js、houses-b.js、special-a.js、special-b.js、tiles.js、west-elf.js，
 *         之后用 window.TownArt_westElf。Node：require('./west-elf.js')。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  function mod(file, name) {
    if (isNode) { try { return require(file); } catch (e) { if (e.code === 'MODULE_NOT_FOUND' && e.message.indexOf(file.slice(2)) >= 0) return null; throw e; } }
    return root[name] || null;
  }
  var C = mod('./core.js', 'TownArtWE_core');
  var HA = mod('./houses-a.js', 'TownArtWE_housesA');
  var HB = mod('./houses-b.js', 'TownArtWE_housesB');
  var SA = mod('./special-a.js', 'TownArtWE_specialA');
  var SB = mod('./special-b.js', 'TownArtWE_specialB');
  var TL = mod('./tiles.js', 'TownArtWE_tiles');
  var CELL = 48, MAX_UP = 144;
  var FACILITIES = ['town_hall', 'lord_hall', 'market_hall', 'granary', 'cistern', 'well', 'mill', 'forge', 'smelter', 'kiln', 'tannery',
    'barracks', 'watchtower', 'city_wall', 'gate', 'temple', 'academy', 'infirmary', 'inn', 'caravanserai', 'stable', 'dock', 'warehouse',
    'mine_head', 'boiler_house', 'ward_tower', 'cemetery', 'bridge'];

  var HOUSE_TYPES = [].concat(HA ? HA.T : [], HB ? HB.T : []);
  HOUSE_TYPES.sort(function (a, b) { return a.n - b.n; });
  var SPECIAL_TYPES = [].concat(SA ? SA.T : [], SB ? SB.T : []);

  function pad2(n) { return (n < 10 ? '0' : '') + n; }
  function houseId(n, i) { return 'west-elf-house-' + pad2(n) + '-' + i; }

  /** 局部坐标（y=0 为占地前沿、向上为负）片段 → symbol 记录 { id, viewBox, body, up, over, low, meta } */
  function wrap(id, fp, body, minY, meta) {
    var W = fp[0] * CELL, D = fp[1] * CELL;
    var up = Math.max(0, Math.ceil(-minY - D - 0.01));
    var H = D + up;
    meta.footprint = fp; meta.height_px = up; meta.anchor = [W / 2, H]; meta.viewBox = [0, 0, W, H];
    return { id: id, viewBox: [0, 0, W, H], up: up, over: up > MAX_UP,
      body: '<g transform="translate(0 ' + H + ')">' + body + '</g>', meta: meta };
  }
  function base(id, cat, T, i, facility) {
    return { id: id, style: 'west', race: 'elf', category: cat, kind: T.kind, facility: facility, variant: i,
      name: T.name + (T.vname && T.vname[i - 1] ? '（' + T.vname[i - 1] + '）' : ''), tags: T.tags.slice(), roof: T.roof, note: T.note || '' };
  }

  function house(n, i) {
    var T = null;
    HOUSE_TYPES.forEach(function (t) { if (t.n === n) T = t; });
    if (!T) throw new Error('no house type ' + n);
    var id = houseId(n, i), ctx = new C.Ctx(id);
    var fp = T.fps ? T.fps[i - 1] : T.fp;
    var body = T.draw(ctx, { i: i, fp: fp });
    var m = base(id, 'house', T, i, null);
    m.type = n;
    return wrap(id, fp, body, ctx.minY, m);
  }
  function houses() {
    var out = [];
    HOUSE_TYPES.forEach(function (t) { for (var i = 1; i <= (t.variants || 3); i++) out.push(house(t.n, i)); });
    return out;
  }
  /** 特殊建筑：T = { key, kind, name, facility, category, fp, roof, tags, note, variants?, draw(ctx, v) } */
  function specials() {
    var out = [];
    SPECIAL_TYPES.forEach(function (T) {
      var nv = T.variants || 1;
      for (var i = 1; i <= nv; i++) {
        var id = 'west-elf-' + T.key + (nv > 1 || T.suffix ? '-' + pad2(i) : ''), ctx = new C.Ctx(id);
        var fp = T.fps ? T.fps[i - 1] : T.fp;
        var body = T.draw(ctx, { i: i, fp: fp });
        out.push(wrap(id, fp, body, ctx.minY, base(id, T.category || 'special', T, i, T.facility)));
      }
    });
    return out;
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
    CELL: CELL, MAX_UP: MAX_UP, FACILITIES: FACILITIES, core: C, HOUSE_TYPES: HOUSE_TYPES, SPECIAL_TYPES: SPECIAL_TYPES,
    houseId: houseId, house: house, houses: houses, specials: specials, tiles: tiles, symbols: symbols,
    symbolSVG: symbolSVG, spriteSVG: spriteSVG, wrap: wrap, tileMod: TL
  };
  root.TownArt_westElf = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
