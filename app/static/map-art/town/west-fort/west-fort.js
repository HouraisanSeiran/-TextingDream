/*
 * 织梦 · 西式（人族）不规则城墙与防御工事 —— 汇总（美术样板，尚未接入游戏）
 * 浏览器：按顺序 <script src> 引 core.js、geom.js、spoke.js、[towers.js、bastion.js、castle.js、moat.js]、west-fort.js，
 *         之后用 window.TownArt_westFort。Node：require('./west-fort.js')。
 * symbol 约定：局部坐标 y = 0 为占地前沿；viewBox 允许左右余量 padX（斜辐条会越过格角最多 17 px），
 *   viewBox = [-padX, 0, w*48 + 2*padX, d*48 + 上伸]，因此锚点仍是 (w*24, 高度)。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  function mod(file, name) {
    if (isNode) { try { return require(file); } catch (e) { if (e.code === 'MODULE_NOT_FOUND' && e.message.indexOf(file.slice(2)) >= 0) return null; throw e; } }
    return (root.TownArtWF && root.TownArtWF[name]) || null;
  }
  var C = mod('./core.js', 'core');
  var parts = ['spoke', 'towers', 'bastion', 'castle', 'moat', 'starfort'].map(function (n) { return mod('./' + n + '.js', n); });
  var BASE = { style: 'west', race: 'common', roof: 'none' };
  /** 把一个条目画成 symbol：it = { id, fp:[w,d], pad, draw(ctx), meta:{...} } */
  function build(it) {
    var ctx = new C.Ctx(it.id), body = it.draw(ctx), w = it.fp[0], d = it.fp[1], pad = it.pad || 0;
    var up = Math.ceil(Math.max(0, -ctx.minY - d * 48)) + 2, H = d * 48 + up;
    if (it.ground) { up = 0; H = d * 48 + 6; }
    var vb = [-pad, 0, w * 48 + 2 * pad, H];
    var m = {}, k;
    for (k in BASE) m[k] = BASE[k];
    m.id = it.id;
    for (k in it.meta) m[k] = it.meta[k];
    m.footprint = [w, d]; m.height_px = up; m.anchor = [w * 24, it.ground ? d * 48 : H]; m.viewBox = vb;
    if (pad) m.pad_x = pad;
    var ty = it.ground ? d * 48 : H;
    var svg = '<symbol id="' + it.id + '" viewBox="' + vb.join(' ') + '" overflow="visible"><g transform="translate(0 ' + ty + ')">' + body + '</g></symbol>';
    return { id: it.id, svg: svg, meta: m };
  }
  function items() {
    var out = [];
    parts.forEach(function (p) { if (p && p.items) out = out.concat(p.items()); });
    return out;
  }
  function all() { return items().map(build); }
  function sprite(list) {
    list = list || all();
    return '<svg xmlns="http://www.w3.org/2000/svg" style="position:absolute;width:0;height:0;overflow:hidden">' + list.map(function (x) { return x.svg; }).join('') + '</svg>';
  }
  var API = { build: build, items: items, all: all, sprite: sprite, ORDER: parts[0] && parts[0].ORDER };
  if (isNode) module.exports = API;
  else root.TownArt_westFort = API;
})(this);
