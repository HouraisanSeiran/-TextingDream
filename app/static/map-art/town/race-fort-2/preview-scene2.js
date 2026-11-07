/*
 * 织梦 · race-fort-2 预览拼接引擎（照 ../race-fort/preview-scene.js 的规则复制改写，全局名 RF2_scene）：
 * 不规则辐条城墙按规范第 11 节排序拼接；棱堡 / 棱垒按 meta.attach_cells 替掉所在墙格的全部辐条与节点，自己画这一段墙。
 * 逻辑格 (c, r) 占 x c*48..(c+1)*48、y r*48..(r+1)*48；锚点 = 前沿中点；排序键 = 前沿 y + 偏移。
 */
(function (root) {
  'use strict';
  var S = 48, STEP = { n: [0, -1], ne: [1, -1], e: [1, 0], se: [1, 1], s: [0, 1], sw: [-1, 1], w: [-1, 0], nw: [-1, -1] };
  var OPP = { n: 's', s: 'n', e: 'w', w: 'e', ne: 'sw', sw: 'ne', nw: 'se', se: 'nw' };
  var ORDER = { n: 0.1, ne: 0.1, nw: 0.1, node: 0.2, e: 0.3, w: 0.3, s: 0.4, se: 0.4, sw: 0.4 };
  function trace(start, segs) {
    var cells = {}, c = start[0], r = start[1];
    function cell(c, r) { var k = c + ',' + r; return cells[k] || (cells[k] = { c: c, r: r, dirs: {} }); }
    cell(c, r);
    segs.forEach(function (sg) {
      for (var i = 0; i < sg[1]; i++) {
        var d = STEP[sg[0]], a = cell(c, r);
        c += d[0]; r += d[1];
        a.dirs[sg[0]] = 1; cell(c, r).dirs[OPP[sg[0]]] = 1;
      }
    });
    if (c !== start[0] || r !== start[1]) throw new Error('墙环未闭合，停在 ' + c + ',' + r);
    return cells;
  }
  /**
   * cfg = { race, start, segs, nodeVar(c, r) -> id, bastions: [{id, c, r}]（替换墙格）, forts: [{id, c, r}]（外挂，不替换）, landmark: {id, c, r} }
   * 校验：棱堡 attach 墙格必须在墙环上，且只含 joins_spokes 那一对方向（墙直着穿过）。
   */
  function build(cfg, lib) {
    var cells = trace(cfg.start, cfg.segs), items = [], skip = {}, race = cfg.race, warn = [];
    function add(id, ax, ay, key) { items.push({ id: id, ax: ax, ay: ay, key: key }); }
    function place(ft, key) {
      var m = lib[ft.id]; if (!m) { warn.push('缺 symbol ' + ft.id); return; }
      var fp = m.footprint, fy = (ft.r + fp[1]) * S;
      add(ft.id, (ft.c + fp[0] / 2) * S, fy, fy + key);
    }
    (cfg.bastions || []).forEach(function (b) {
      var m = lib[b.id]; if (!m) { warn.push('缺 symbol ' + b.id); return; }
      m.attach_cells.forEach(function (ac) {
        var k = (b.c + ac[0]) + ',' + (b.r + ac[1]), cl = cells[k];
        if (!cl) { warn.push(b.id + ' 的 attach 格 ' + k + ' 不在墙上'); return; }
        var ds = Object.keys(cl.dirs).sort().join(','), want = m.joins_spokes.slice().sort().join(',');
        if (ds !== want) warn.push(b.id + ' 的 attach 格 ' + k + ' 辐条 ' + ds + ' ≠ ' + want);
        skip[k] = 1;
      });
      place(b, 0.5);
    });
    Object.keys(cells).forEach(function (k) {
      if (skip[k]) return;
      var cl = cells[k], ax = (cl.c + 0.5) * S, fy = (cl.r + 1) * S;
      Object.keys(cl.dirs).forEach(function (d) { add('west-' + race + '-wallspoke-' + d, ax, fy, fy + ORDER[d]); });
      var nid = (cfg.towers && cfg.towers[k]) || (cfg.nodeVar ? cfg.nodeVar(cl.c, cl.r) : 'west-' + race + '-wallnode-01');
      add(nid, ax, fy, fy + 0.2);
    });
    (cfg.forts || []).forEach(function (ft) { place(ft, ft.key || 0.5); });
    if (cfg.landmark) place(cfg.landmark, 0.6);
    items.sort(function (a, b) { return a.key - b.key || a.ax - b.ax; });
    return { cells: cells, items: items, warn: warn };
  }
  function render(scene, lib, vb, scale, grid) {
    var o = '<svg xmlns="http://www.w3.org/2000/svg" width="' + vb[2] * scale + '" height="' + vb[3] * scale + '" viewBox="' + vb.join(' ') + '">';
    o += '<rect x="' + vb[0] + '" y="' + vb[1] + '" width="' + vb[2] + '" height="' + vb[3] + '" fill="#c9c79a"/>';
    if (grid) {
      var d = '';
      for (var x = Math.ceil(vb[0] / S) * S; x <= vb[0] + vb[2]; x += S) d += 'M' + x + ' ' + vb[1] + 'v' + vb[3];
      for (var y = Math.ceil(vb[1] / S) * S; y <= vb[1] + vb[3]; y += S) d += 'M' + vb[0] + ' ' + y + 'h' + vb[2];
      o += '<path d="' + d + '" stroke="#4a3826" stroke-opacity="0.12" stroke-width="' + (1 / scale) + '" fill="none"/>';
    }
    scene.items.forEach(function (it) {
      var m = lib[it.id]; if (!m) return;
      var w = m.viewBox[2], h = m.viewBox[3];
      o += '<use href="#' + it.id + '" x="' + (it.ax - w / 2) + '" y="' + (it.ay - h) + '" width="' + w + '" height="' + h + '"/>';
    });
    return o + '</svg>';
  }
  root.RF2_scene = { S: S, trace: trace, build: build, render: render };
})(typeof window !== 'undefined' ? window : this);
