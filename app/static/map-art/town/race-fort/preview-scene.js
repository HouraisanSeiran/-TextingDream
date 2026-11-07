/*
 * 织梦 · race-fort 预览拼接引擎：不规则辐条城墙 + 城门 + 节点塔 + 外凸工事，按规范第 11 节排序真实拼接。
 * 逻辑格 (c, r) 占 x c*48..(c+1)*48、y r*48..(r+1)*48；锚点 = 前沿中点；排序键 = 前沿 y + 偏移。
 * 浏览器挂 window.RF_scene。依赖 race-fort.js（TownArt_raceFort）与 preview-refs.js（RF_REFS，已有城门）。
 */
(function (root) {
  'use strict';
  var S = 48, STEP = { n: [0, -1], ne: [1, -1], e: [1, 0], se: [1, 1], s: [0, 1], sw: [-1, 1], w: [-1, 0], nw: [-1, -1] };
  var OPP = { n: 's', s: 'n', e: 'w', w: 'e', ne: 'sw', sw: 'ne', nw: 'se', se: 'nw' };
  var ORDER = { n: 0.1, ne: 0.1, nw: 0.1, node: 0.2, e: 0.3, w: 0.3, s: 0.4, se: 0.4, sw: 0.4 };
  /** 由起点 + [方向, 步数] 段列表展开成闭合墙格环，返回 { 'c,r': {c, r, dirs:{}} } */
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
   * cfg = { race, start, segs, gates: [{c, r, kind:'h'|'v'}], gateMode:'overlay'|'replace', gateIds:{h, v},
   *         towers: {'c,r': id}, nodeVar: function(c, r) -> id, forts: [{id, c, r}] }
   */
  function build(cfg, lib) {
    var cells = trace(cfg.start, cfg.segs), items = [], skip = {}, race = cfg.race;
    function add(id, ax, ay, key) { items.push({ id: id, ax: ax, ay: ay, key: key }); }
    (cfg.gates || []).forEach(function (g) {
      var id = cfg.gateIds[g.kind], fy = (g.r + 1) * S;
      if (cfg.gateMode === 'replace') { // 兽人栅门是替换瓦片：门洞跨在两个墙格之间
        if (g.kind === 'h') { skip[g.c + ',' + g.r + ',e'] = skip[(g.c + 1) + ',' + g.r + ',w'] = 1; add(id, (g.c + 1) * S, (g.r + 0.5) * S, fy + 0.3); }
        else { skip[g.c + ',' + g.r + ',s'] = skip[g.c + ',' + (g.r + 1) + ',n'] = 1; add(id, (g.c + 1) * S, (g.r + 1.5) * S, fy + S + 0.15); }
      } else { skip[g.c + ',' + g.r + ',node'] = 1; add(id, (g.c + 0.5) * S, fy, fy + 0.5); }
    });
    Object.keys(cells).forEach(function (k) {
      var cl = cells[k], ax = (cl.c + 0.5) * S, fy = (cl.r + 1) * S;
      Object.keys(cl.dirs).forEach(function (d) { if (!skip[k + ',' + d]) add('west-' + race + '-wallspoke-' + d, ax, fy, fy + ORDER[d]); });
      if (skip[k + ',node']) return;
      var nid = (cfg.towers && cfg.towers[k]) || (cfg.nodeVar ? cfg.nodeVar(cl.c, cl.r) : 'west-' + race + '-wallnode-01');
      add(nid, ax, fy, fy + 0.2);
    });
    (cfg.forts || []).forEach(function (ft) {
      var m = lib[ft.id]; if (!m) return;
      var fp = m.footprint, fy = (ft.r + fp[1]) * S;
      add(ft.id, (ft.c + fp[0] / 2) * S, fy, fy + (ft.key || 0.5));
    });
    items.sort(function (a, b) { return a.key - b.key || a.ax - b.ax; });
    return { cells: cells, items: items };
  }
  /** 输出场景 svg；vb = [x, y, w, h]（世界坐标），scale = 显示倍数 */
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
  root.RF_scene = { S: S, trace: trace, build: build, render: render };
})(typeof window !== 'undefined' ? window : this);
