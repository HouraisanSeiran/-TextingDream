/*
 * 织梦 · 城镇西式水面与地面素材汇总（美术样板，尚未接入游戏）
 * 浏览器：按顺序 <script src> 引 core.js、dual.js、water.js、ground.js、kit.js、props-a.js、props-b.js、props-c.js、
 *         props-race.js、props-orc.js、west-ground.js，之后用 window.TownArt_westGround。Node：require('./west-ground.js')。
 * API：symbols() 全部记录 { id, viewBox, body, meta }；symbolSVG(s)；spriteSVG(list)；byId()。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  function mod(file, name) { return isNode ? require(file) : root[name]; }
  var C = mod('./core.js', 'TownArtWG_core');
  var WA = mod('./water.js', 'TownArtWG_water');
  var GR = mod('./ground.js', 'TownArtWG_ground');
  var PROPS = [mod('./props-a.js', 'TownArtWG_propsA'), mod('./props-b.js', 'TownArtWG_propsB'), mod('./props-c.js', 'TownArtWG_propsC'),
    mod('./props-race.js', 'TownArtWG_propsRace'), mod('./props-orc.js', 'TownArtWG_propsOrc')];
  var CELL = 48, MAX_UP = 48;
  var TILE_NAME = { water_bank: '水面·自然河岸', water_quay: '水面·石砌码头岸', ground_dirt: '踩实土地/院坪' };

  function pad2(n) { return (n < 10 ? '0' : '') + n; }
  function base(id, cat, kind, race) {
    return { id: id, style: 'west', race: race || 'common', category: cat, kind: kind, facility: null };
  }
  /** 48×48 地面瓦片 */
  function tileRec(t, cat) {
    var m = base(t.id, cat, t.kind);
    m.variant = t.variant != null ? t.variant : t.mask;
    m.footprint = [1, 1]; m.height_px = 0; m.anchor = [24, 48]; m.viewBox = [0, 0, 48, 48];
    m.roof = 'none';
    if (t.mask != null) {
      m.mask = t.mask; m.name = TILE_NAME[t.kind] + ' ' + t.id.slice(-4);
      m.tags = ['dual_grid', 'mask_' + t.id.slice(-4)];
      if (cat === 'water') m.tags.push('waterside');
      m.note = '双网格瓦片：渲染格与逻辑格错开半格，四角 = 逻辑格中心，mask = NW*8+NE*4+SW*2+SE*1。' +
        (t.mask === 0 ? '0000 为透明占位。' : '') + (cat === 'water' ? '水色 #a9b8ad，与 special-infra 西式码头/石拱桥一致。' : '');
    } else {
      m.name = t.name; m.tags = ['tileable', 'seamless']; m.note = '可任意排列的草地底纹，四周 4 px 内无笔触。';
    }
    return { id: t.id, viewBox: m.viewBox, body: t.body, meta: m };
  }
  /** 地面摆件：1×1 占地，锚点 = 脚底中点 (24, H)，上伸 = top - 48 */
  function propRec(d, v) {
    var race = d.race || 'common';
    var id = 'west-' + race + '-prop-' + d.kind.replace(/_/g, '-') + '-' + pad2(v);
    var ctx = new C.Ctx(id), body = d.draw(ctx, v);
    var up = Math.max(0, Math.ceil(d.top - CELL)), H = CELL + up;
    var m = base(id, 'prop', d.kind, race);
    m.variant = v; m.name = d.name + (d.vars > 1 ? ' ' + v : ''); m.footprint = [1, 1]; m.height_px = up;
    m.anchor = [24, H]; m.viewBox = [0, 0, CELL, H]; m.tags = d.tags.slice(); m.roof = 'none';
    m.note = d.note || '地面摆件，锚点在脚底中点；按锚点 y 排序绘制。';
    return { id: id, viewBox: m.viewBox, up: up, over: up > MAX_UP,
      body: '<g transform="translate(0 ' + H + ')">' + body + '</g>', meta: m };
  }

  function symbols() {
    var out = [];
    WA.all().forEach(function (t) { out.push(tileRec(t, 'water')); });
    GR.all().forEach(function (t) { out.push(tileRec(t, 'ground')); });
    PROPS.forEach(function (P) {
      if (!P) return;
      P.defs.forEach(function (d) { for (var v = 1; v <= (d.vars || 1); v++) out.push(propRec(d, v)); });
    });
    return out;
  }
  function symbolSVG(s) {
    return '<symbol id="' + s.id + '" viewBox="' + s.viewBox.join(' ') + '" overflow="visible">' + s.body + '</symbol>';
  }
  function spriteSVG(list) {
    list = list || symbols();
    // 不能用 display:none：Chrome 下 display:none 容器里的 clipPath 失效
    return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute;overflow:hidden">' +
      list.map(symbolSVG).join('\n') + '</svg>';
  }
  function byId(list) { var m = {}; (list || symbols()).forEach(function (s) { m[s.id] = s; }); return m; }

  var API = { CELL: CELL, MAX_UP: MAX_UP, core: C, water: WA, ground: GR, symbols: symbols, symbolSVG: symbolSVG, spriteSVG: spriteSVG, byId: byId };
  root.TownArt_westGround = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
