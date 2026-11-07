/* 织梦 · east-fort 预览场景：按规范第 11 节同格排序偏移真实拼接辐条墙 */
(function () {
  'use strict';
  var EF = window.TownArt_eastFort, TB = window.TownArtEast_tiles, CELL = 48;
  var DN = { '0,-1': 'n', '1,-1': 'ne', '1,0': 'e', '1,1': 'se', '0,1': 's', '-1,1': 'sw', '-1,0': 'w', '-1,-1': 'nw' };
  var ALL = EF.items().concat(TB ? TB.items().filter(function (x) { return /gate|tower/.test(x.id); }) : []);
  var META = {};
  ALL.forEach(function (it) { META[it.id] = it.meta; });

  // 折线（逻辑格坐标）→ { "i,j": [dirs] }
  function wallCells(lines) {
    var cells = {};
    function add(i, j, d) { var k = i + ',' + j; (cells[k] = cells[k] || []); if (cells[k].indexOf(d) < 0) cells[k].push(d); }
    lines.forEach(function (pts) {
      for (var p = 0; p + 1 < pts.length; p++) {
        var a = pts[p], b = pts[p + 1], dx = Math.sign(b[0] - a[0]), dy = Math.sign(b[1] - a[1]), i = a[0], j = a[1];
        while (i !== b[0] || j !== b[1]) {
          add(i, j, DN[dx + ',' + dy]); add(i + dx, j + dy, DN[-dx + ',' + -dy]); i += dx; j += dy;
        }
      }
    });
    return cells;
  }
  // 墙格 → 放置列表；nodeOverride: { "i,j": symbolId } 用敌楼 / 角楼替换墙墩
  function wallPlaces(cells, nodeOverride) {
    var out = [];
    Object.keys(cells).forEach(function (k) {
      var ij = k.split(',').map(Number), ds = cells[k], ax = ij[0] * CELL + 24, ay = (ij[1] + 1) * CELL;
      ds.forEach(function (d) { out.push({ id: 'east-common-wallspoke-' + d, ax: ax, ay: ay, off: EF.SORT[d] }); });
      out.push({ id: window.TownArtFort_spoke.nodeId(ds), ax: ax, ay: ay, off: EF.SORT.node });
      // 敌楼 / 箭楼 / 角楼立在墙墩上：墙墩照画，塔楼排在本格所有辐条之后
      if (nodeOverride && nodeOverride[k]) out.push({ id: nodeOverride[k], ax: ax, ay: ay, off: 0.45 });
    });
    return out;
  }
  // 放一个多格 symbol：(i,j) = 占地左前角那一格，off = 同格排序偏移
  function placeAt(id, i, j, off) {
    var m = META[id], w = m.footprint[0];
    return { id: id, ax: i * CELL + w * 24, ay: (j + 1) * CELL, off: off == null ? 0.5 : off };
  }
  function render(svg, places, W, H, vb) {
    // 地面层（护城河）带 key，排在所有立体物之前；其余按规范第 11 节：前沿 y + 同格偏移
    var kk = function (p) { return p.key != null ? p.key : p.ay + p.off; };
    places.sort(function (a, b) { return kk(a) - kk(b) || a.ax - b.ax; });
    var s = '<rect x="-200" y="-200" width="' + (W + 400) + '" height="' + (H + 400) + '" fill="#d9c58f"/>';
    for (var x = 0; x <= W; x += CELL) s += '<path d="M' + x + ' 0V' + H + '" stroke="#b9a571" stroke-width="0.5" stroke-opacity="0.5"/>';
    for (var y = 0; y <= H; y += CELL) s += '<path d="M0 ' + y + 'H' + W + '" stroke="#b9a571" stroke-width="0.5" stroke-opacity="0.5"/>';
    places.forEach(function (p) {
      var m = META[p.id];
      if (!m) { console.warn('缺 symbol', p.id); return; }
      var vw = m.viewBox[2], vh = m.viewBox[3];
      s += '<use href="#' + p.id + '" x="' + (p.ax - vw / 2) + '" y="' + (p.ay - vh) + '" width="' + vw + '" height="' + vh + '"/>';
    });
    svg.setAttribute('viewBox', (vb || [-24, -96, W + 48, H + 120]).join(' '));
    svg.innerHTML = s;
  }

  // 场景 a：不规则城墙（正交 + 45° 斜段，(6,11)-(6,8)-(2,8) 处一个凹角）
  var LOOP = [[3, 2], [9, 2], [12, 5], [12, 9], [10, 11], [6, 11], [6, 8], [2, 8], [2, 5], [3, 4], [3, 2]];
  function sceneA() {
    var cells = wallCells([LOOP]), ov = {}, extra = [];
    if (META['east-common-dilou-01']) { ov['9,2'] = 'east-common-dilou-01'; ov['2,8'] = 'east-common-dilou-01'; }
    if (META['east-common-jianlou-01']) ov['12,9'] = 'east-common-jianlou-01';
    if (META['east-common-cornertower-01']) { ov['3,2'] = 'east-common-cornertower-01'; ov['6,8'] = 'east-common-cornertower-01'; }
    var pl = wallPlaces(cells, ov);
    if (META['east-common-wall-gate-h']) pl.push(placeAt('east-common-wall-gate-h', 7, 11, 0.5));
    if (META['east-common-wall-gate-v']) pl.push(placeAt('east-common-wall-gate-v', 12, 7, 0.5));
    if (META['east-common-mamian-n']) {
      extra.push(placeAt('east-common-mamian-n', 6, 2, 0.5), placeAt('east-common-mamian-w', 1, 6, 0.5));
      extra.push(placeAt('east-common-mamian-s', 4, 9, 0.5), placeAt('east-common-mamian-e', 13, 6, 0.5));
    }
    return moatPlaces([MOAT_A]).concat(pl, extra);
  }
  // 护城河：两遍——全部岸层（key -2e6）再全部水面（key -1e6）
  var MOAT_A = [[1, 0], [10, 0], [14, 4], [14, 11]];
  function moatPlaces(lines) {
    if (!META['east-common-moatnode']) return [];
    var cells = wallCells(lines), out = [];
    Object.keys(cells).forEach(function (k) {
      var ij = k.split(',').map(Number), ax = ij[0] * CELL + 24, ay = (ij[1] + 1) * CELL;
      out.push({ id: 'east-common-moatbank-node', ax: ax, ay: ay, key: -2e6 + ay });
      out.push({ id: 'east-common-moatnode', ax: ax, ay: ay, key: -1e6 + ay });
      cells[k].forEach(function (d) {
        out.push({ id: 'east-common-moatbank-' + d, ax: ax, ay: ay, key: -2e6 + ay });
        out.push({ id: 'east-common-moatspoke-' + d, ax: ax, ay: ay, key: -1e6 + ay });
      });
    });
    return out;
  }
  // 场景 b：东西向主墙两座城门（外接方瓮城 / 月城，朝南），东端拐向南的南北向墙上一座 gate-v 外接东向月城
  var LINE_B = [[0, 1], [13, 1], [13, 7]];
  function sceneB() {
    if (!META['east-common-wengcheng-square-s']) return null;
    var pl = wallPlaces(wallCells([LINE_B]), { '13,1': 'east-common-cornertower-01' });
    pl.push(placeAt('east-common-wall-gate-h', 2, 1, 0.5), placeAt('east-common-wall-gate-h', 8, 1, 0.5));
    pl.push(placeAt('east-common-wengcheng-square-s', 2, 3, 0.5), placeAt('east-common-wengcheng-moon-s', 8, 3, 0.5));
    pl.push(placeAt('east-common-wall-gate-v', 13, 4, 0.5), placeAt('east-common-wengcheng-moon-e', 14, 5, 0.5));
    return pl;
  }
  window.EastFortScenes = { wallCells: wallCells, wallPlaces: wallPlaces, placeAt: placeAt, render: render, sceneA: sceneA, sceneB: sceneB, META: META, ALL: ALL, LOOP: LOOP };
})();
