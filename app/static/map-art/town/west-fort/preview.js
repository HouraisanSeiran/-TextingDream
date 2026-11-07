/*
 * 织梦 · west-fort 预览页脚本：图册 + 场景（按第 11 节同格排序偏移拼接）。
 * 只读引用 ../west-base/ 的 common.js、tiles.js（城门、塔楼）。
 */
(function (root) {
  'use strict';
  var WF = root.TownArt_westFort, WT = root.TownArtWB_tiles, S = 48;
  var META = {}, SYM = [];
  WF.all().forEach(function (x) { META[x.id] = x.meta; SYM.push(x.svg); });
  // west-base 叠加件（城门、塔楼）现场生成成 symbol
  WT.all(function (id, fp, body, top, meta) {
    if (!/wall-(gate|tower)/.test(id)) return null;
    var H = Math.ceil(-top) + 2;
    META[id] = { id: id, footprint: fp, viewBox: [0, 0, 48, H], anchor: [24, H] };
    SYM.push('<symbol id="' + id + '" viewBox="0 0 48 ' + H + '" overflow="visible"><g transform="translate(0 ' + H + ')">' + body + '</g></symbol>');
    return null;
  });
  var DIRV = { n: [0, -1], ne: [1, -1], e: [1, 0], se: [1, 1], s: [0, 1], sw: [-1, 1], w: [-1, 0], nw: [-1, -1] };
  var OPP = { n: 's', ne: 'sw', e: 'w', se: 'nw', s: 'n', sw: 'ne', w: 'e', nw: 'se' };
  function dirOf(dx, dy) { for (var k in DIRV) if (DIRV[k][0] === dx && DIRV[k][1] === dy) return k; }
  /** 闭合折线（格坐标顶点）→ 墙格表 { "x,y": {x,y,dirs:{}} } */
  function trace(verts, cells) {
    cells = cells || {};
    function cell(x, y) { var k = x + ',' + y; return cells[k] || (cells[k] = { x: x, y: y, dirs: {} }); }
    for (var i = 0; i < verts.length; i++) {
      var a = verts[i], b = verts[(i + 1) % verts.length];
      var dx = Math.sign(b[0] - a[0]), dy = Math.sign(b[1] - a[1]), x = a[0], y = a[1];
      while (x !== b[0] || y !== b[1]) {
        var d = dirOf(dx, dy);
        cell(x, y).dirs[d] = 1; x += dx; y += dy; cell(x, y).dirs[OPP[d]] = 1;
      }
    }
    return cells;
  }
  /** 一个放置件：格 (gx, gy)，排序偏移 off */
  function item(id, gx, gy, off) { return { id: id, gx: gx, gy: gy, key: (gy + 1) * S + off, x: gx }; }
  /** 墙格 → 放置件；over：{ "x,y": 叠加件 id } 替代节点或盖在直段上 */
  function wallItems(cells, over) {
    var out = [];
    Object.keys(cells).forEach(function (k) {
      var c = cells[k], o = over && over[k];
      Object.keys(c.dirs).forEach(function (d) { out.push(item('west-common-wallspoke-' + d, c.x, c.y, WF.ORDER[d])); });
      var gate = o && /gate/.test(o);
      if (!o || gate) out.push(item(root.TownArtWF.spoke.nodeFor(c.dirs), c.x, c.y, WF.ORDER.node));
      if (o) out.push(item(o, c.x, c.y, gate ? 0.45 : WF.ORDER.node));
    });
    return out;
  }
  function use(it) {
    // gx = 占地最左一列，gy = 占地最前一行；局部 x = 0 对齐 gx*S（viewBox 左侧余量 vb[0] 为负）
    var m = META[it.id], vb = m.viewBox, y = (it.gy + 1) * S - m.anchor[1];
    return '<use href="#' + it.id + '" x="' + (it.gx * S + vb[0]) + '" y="' + y + '" width="' + vb[2] + '" height="' + vb[3] + '"/>';
  }
  function scene(w, h, list, zoom, view, title) {
    list.sort(function (a, b) { return a.key - b.key || a.x - b.x; });
    var v = view || [0, -96, w * S, h * S + 96], z = zoom || 1;
    var grid = '';
    for (var i = 1; i < w; i++) grid += 'M' + i * S + ' 0V' + h * S;
    for (var j = 1; j < h; j++) grid += 'M0 ' + j * S + 'H' + w * S;
    return '<figure><figcaption>' + title + '</figcaption><svg width="' + v[2] * z + '" height="' + v[3] * z + '" viewBox="' + v.join(' ') + '">' +
      '<rect x="' + v[0] + '" y="' + v[1] + '" width="' + v[2] + '" height="' + v[3] + '" fill="#c9c79a"/>' +
      '<path d="' + grid + '" stroke="#4a3826" stroke-opacity="0.08" fill="none"/>' + list.map(use).join('') + '</svg></figure>';
  }
  root.WFPreview = { META: META, SYM: SYM, trace: trace, item: item, wallItems: wallItems, scene: scene, use: use };
})(this);
