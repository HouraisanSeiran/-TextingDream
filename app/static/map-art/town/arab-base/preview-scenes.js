/*
 * 织梦 · arab-base 预览：拼接验证场景的通用部分（双网格铺瓦、辐条环、按锚点 y 排序）。依赖 arab-base.js 及其模块。
 * 场景坐标：逻辑格 (cx, cy) 占 x cx*48..(cx+1)*48、y cy*48..(cy+1)*48；1×1 件的锚点 = (cx*48+24, (cy+1)*48)。
 */
(function (root) {
  'use strict';
  var C = root.TownArtAB_core, S = 48, IDX = {};
  function index(list) { list.forEach(function (s) { IDX[s.id] = s; }); }
  /** 把 symbol 的锚点放到 (ax, ay) */
  function useAt(id, ax, ay) {
    var s = IDX[id];
    if (!s) { console.error('preview: missing symbol ' + id); return ''; }
    var vb = s.viewBox;
    return '<use href="#' + id + '" x="' + (ax - s.meta.anchor[0]) + '" y="' + (ay - s.meta.anchor[1]) + '" width="' + vb[2] + '" height="' + vb[3] + '"/>';
  }
  function grid(rows) { return rows.map(function (r) { return r.split('').map(function (c) { return c === '#' ? 1 : 0; }); }); }
  function cellAt(L, x, y) { return y >= 0 && y < L.length && x >= 0 && x < L[0].length && L[y][x] ? 1 : 0; }
  /** 双网格：渲染格 (i, j) 的四角 = 逻辑格 (i-1,j-1) (i,j-1) (i-1,j) (i,j) 的中心 */
  function dual(L, prefix, out) {
    for (var j = 0; j <= L.length; j++) for (var i = 0; i <= L[0].length; i++) {
      var m = cellAt(L, i - 1, j - 1) * 8 + cellAt(L, i, j - 1) * 4 + cellAt(L, i - 1, j) * 2 + cellAt(L, i, j);
      if (m) out.push({ k: (j + 0.5) * S, x: i * S, svg: useAt(prefix + C.bin(m), i * S, (j + 0.5) * S) });
    }
  }
  /** 1×1 件放在逻辑格上；dk = 排序偏移 */
  function cell(id, cx, cy, out, dk) { out.push({ k: (cy + 1) * S + (dk || 0), x: cx * S + 24, svg: useAt(id, cx * S + 24, (cy + 1) * S) }); }
  /** 多格建筑：左上逻辑格 (cx, cy) */
  function bld(id, cx, cy, out) {
    var s = IDX[id]; if (!s) { console.error('preview: missing symbol ' + id); return; }
    var fp = s.meta.footprint, ax = (cx + fp[0] / 2) * S, ay = (cy + fp[1]) * S;
    out.push({ k: ay, x: ax, svg: useAt(id, ax, ay) });
  }
  var DIR = { '0,-1': 'n', '1,-1': 'ne', '1,0': 'e', '1,1': 'se', '0,1': 's', '-1,1': 'sw', '-1,0': 'w', '-1,-1': 'nw' };
  /** 折线顶点（逻辑格坐标）栅格化成墙格序列；每段必须正交或正好 45° */
  function trace(verts) {
    var cells = [], i;
    for (i = 0; i < verts.length - 1; i++) {
      var a = verts[i], b = verts[i + 1], dx = Math.sign(b[0] - a[0]), dy = Math.sign(b[1] - a[1]);
      var n = Math.max(Math.abs(b[0] - a[0]), Math.abs(b[1] - a[1]));
      if (dx && dy && Math.abs(b[0] - a[0]) !== Math.abs(b[1] - a[1])) console.error('preview: segment not 45°');
      for (var t = 0; t < n; t++) cells.push([a[0] + dx * t, a[1] + dy * t]);
    }
    return cells;
  }
  /** 闭合辐条环：每格朝前后两个邻格各画半段墙 + 节点；verts 首尾相同；towers = 用塔楼替代节点的顶点下标 */
  function spokeRing(verts, out, towerAt) {
    var cells = trace(verts), n = cells.length, ORD = root.TownArtAB_spoke.ORDER, isV = {};
    verts.forEach(function (v) { isV[v.join(',')] = 1; });
    cells.forEach(function (c, i) {
      var p = cells[(i + n - 1) % n], q = cells[(i + 1) % n];
      [p, q].forEach(function (o) { var d = DIR[(o[0] - c[0]) + ',' + (o[1] - c[1])]; cell('arab-common-wallspoke-' + d, c[0], c[1], out, ORD[d]); });
      // 节点：拐点或斜段 → 02 八角墩；东西直段 → 01；南北直段 → 03
      var key = c.join(','), ew = p[1] === c[1] && q[1] === c[1], ns = p[0] === c[0] && q[0] === c[0];
      if (towerAt && towerAt[key]) cell('arab-common-wall-tower', c[0], c[1], out, ORD.node);
      else cell('arab-common-wallnode-' + (isV[key] || !(ew || ns) ? '02' : ew ? '01' : '03'), c[0], c[1], out, ORD.node);
    });
  }
  function sortSvg(items) {
    return items.slice().sort(function (a, b) { return a.k - b.k || a.x - b.x; }).map(function (it) { return it.svg; }).join('');
  }
  /** 一个场景：cols × rows 逻辑格；build(ground[], objs[]) 往两层里放东西 */
  function scene(host, title, cols, rows, build) {
    var ground = [], objs = [], up = 120, W = cols * S + 48, H = rows * S + up + 24;
    build(ground, objs);
    var svg = '<svg width="' + W + '" height="' + H + '" viewBox="-24 ' + (-up) + ' ' + W + ' ' + H + '">' +
      '<rect x="-24" y="' + (-up) + '" width="' + W + '" height="' + H + '" fill="#e3cf9f"/>' +
      '<rect x="0" y="0" width="' + cols * S + '" height="' + rows * S + '" fill="none" stroke="#c79d66" stroke-width="0.5" stroke-dasharray="2 4"/>' +
      sortSvg(ground) + sortSvg(objs) + '</svg>';
    var d = document.createElement('div');
    d.className = 'scene';
    d.innerHTML = '<div class="scap">' + title + '</div>' + svg;
    host.appendChild(d);
  }
  root.ABScenesKit = { index: index, useAt: useAt, grid: grid, dual: dual, cell: cell, bld: bld, trace: trace, spokeRing: spokeRing, scene: scene, S: S };
})(window);
