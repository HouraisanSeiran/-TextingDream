/*
 * 织梦 · 西式城堡预览：图册 + 示范城堡拼装（只供 preview.html 用，尚未接入游戏）。
 * 示范城堡用双网格规则真实拼接：逻辑格布尔场 → 每个渲染瓦片按四角编码选 symbol。
 * 深度排序：地面瓦片（内院、护城河、道路）先画；其余（幕墙瓦片、建筑、叠加件）按锚点 y、再按 x 排序。
 */
(function (root) {
  'use strict';
  var NS = 'http://www.w3.org/2000/svg', CELL = 48;

  function el(tag, attrs, parent) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function use(parent, id, x, y, w, h) {
    return el('use', { href: '#' + id, x: x, y: y, width: w, height: h }, parent);
  }

  // ---------------- 示范城堡布局（逻辑格） ----------------
  var GW = 25, GH = 29;
  var W0 = 5, W1 = 19;             // 幕墙一圈：x 或 y 等于 5 / 19
  var M0 = 2, M1 = 22;             // 护城河外沿；护城河宽 2 格，与幕墙之间隔 1 格护坡
  function isWallCell(x, y) {
    if (x < W0 || x > W1 || y < W0 || y > W1) return false;
    if (!(x === W0 || x === W1 || y === W0 || y === W1)) return false;
    if (y === W1 && x >= 11 && x <= 13) return false;   // 南门楼 gate-h
    if (x === W1 && y >= 11 && y <= 13) return false;   // 东门楼 gate-v
    return true;
  }
  function isMoatCell(x, y) {
    if (x < M0 || x > M1 || y < M0 || y > M1) return false;
    return x <= M0 + 1 || x >= M1 - 1 || y <= M0 + 1 || y >= M1 - 1;
  }
  function isYardCell(x, y) {
    if (x > W0 && x < W1 && y > W0 && y < W1) return true;
    return (x === 12 && y === W1) || (y === 12 && x === W1);  // 门洞下的地面
  }
  function isRoadCell(x, y) { // 城外土路（west-base 存在时才画）
    return (x === 12 && y >= 23) || (y === 25 && x >= 3 && x <= 22) || (y === 12 && x >= 23);  // 东门外一段土路
  }

  // 建筑 / 叠加件：[symbol id, x, y]（占地左上逻辑格）
  var PLACE = [
    // 马厩、铁匠棚是单坡披屋：后沿贴北墙内侧（第 6 行），朝南开口；南墙内侧会被幕墙挡住，不放披屋
    ['west-common-keep-01', 6, 6], ['west-common-castlestable-01', 9, 6], ['west-common-castleforge-01', 12, 6], ['west-common-keep-02', 15, 6],
    ['west-common-greathall-01', 9, 10], ['west-common-castlekitchen-01', 13, 10],
    ['west-common-chapel-01', 6, 11], ['west-common-castlebarracks-01', 15, 12],
    ['west-common-castlewell-01', 12, 14], ['west-common-castlegranary-01', 16, 15],
    // 塔楼 3×3、塔心在中格：左上角 = 墙角格 - 1
    ['west-common-tower-round-01', 4, 4], ['west-common-tower-square-01', 18, 4],
    ['west-common-tower-square-01', 4, 18], ['west-common-tower-round-01', 18, 18],
    ['west-common-gatehouse-h', 11, 19], ['west-common-gatehouse-v', 19, 11],
    ['west-common-drawbridge-ns-down', 12, 21], ['west-common-drawbridge-ew-down', 21, 12]
  ];
  // 城外民居（复用 west-base）
  var HOUSES = [
    ['west-common-house-03-1', 3, 23], ['west-common-house-01-2', 6, 23], ['west-common-house-09-1', 8, 23],
    ['west-common-house-06-1', 13, 23], ['west-common-house-05-1', 16, 23], ['west-common-house-12-2', 18, 23],
    ['west-common-house-04-1', 3, 26], ['west-common-house-10-1', 6, 26], ['west-common-house-02-1', 9, 26],
    ['west-common-house-14-1', 13, 26], ['west-common-house-16-1', 16, 26], ['west-common-house-11-3', 19, 26]
  ];

  function maskAt(fn, i, j) { // 渲染瓦片 (i, j) 的四角 = 逻辑格 (i,j) (i+1,j) (i,j+1) (i+1,j+1)
    return (fn(i, j) ? 8 : 0) + (fn(i + 1, j) ? 4 : 0) + (fn(i, j + 1) ? 2 : 0) + (fn(i + 1, j + 1) ? 1 : 0);
  }
  function bin4(m) { return ('000' + m.toString(2)).slice(-4); }

  /**
   * metaById：symbol id → meta（含 viewBox、footprint）。返回 { svg, missing, counts }。
   */
  function renderCastle(host, metaById) {
    var W = GW * CELL, H = GH * CELL, TOP = 150;
    var svg = el('svg', { viewBox: '0 ' + (-TOP) + ' ' + W + ' ' + (H + TOP), width: W, height: H + TOP }, host);
    el('rect', { x: 0, y: -TOP, width: W, height: H + TOP, fill: '#c9c79a' }, svg);
    var missing = {}, counts = { ground: 0, sorted: 0 }, items = [];
    function has(id) { if (metaById[id]) return true; missing[id] = 1; return false; }
    function tile(prefix, fn, ground) {
      for (var j = -1; j < GH; j++) for (var i = -1; i < GW; i++) {
        var m = maskAt(fn, i, j);
        if (!m) continue;
        var id = prefix + bin4(m);
        if (!has(id)) continue;
        var vb = metaById[id].viewBox, x = i * CELL + 24, yb = j * CELL + 72;
        var it = { id: id, x: x, y: yb - vb[3], w: vb[2], h: vb[3], ay: yb, ax: x + 24 };
        if (ground) { use(svg, it.id, it.x, it.y, it.w, it.h); counts.ground++; } else items.push(it);
      }
    }
    var hasRoad = !!metaById['west-common-road-dirt-1111'];
    if (hasRoad) tile('west-common-road-dirt-', isRoadCell, true);
    tile('west-common-yard-', isYardCell, true);
    tile('west-common-moat-', isMoatCell, true);
    tile('west-common-castlewall-', isWallCell, false);
    var all = PLACE.concat(metaById['west-common-house-01-1'] ? HOUSES : []);
    all.forEach(function (p) {
      if (!has(p[0])) return;
      var m = metaById[p[0]], fw = m.footprint[0], fd = m.footprint[1], vb = m.viewBox;
      var ay = (p[2] + fd) * CELL;
      items.push({ id: p[0], x: p[1] * CELL, y: ay - vb[3], w: vb[2], h: vb[3], ay: ay, ax: (p[1] + fw / 2) * CELL });
    });
    items.sort(function (a, b) { return a.ay - b.ay || a.ax - b.ax; });
    items.forEach(function (it) { use(svg, it.id, it.x, it.y, it.w, it.h); counts.sorted++; });
    return { svg: svg, missing: Object.keys(missing), counts: counts, hasHouses: !!metaById['west-common-house-01-1'] };
  }

  /** 图册：每个 symbol 一格卡片，画上占地网格与锚点。 */
  function renderAtlas(host, list, scale) {
    scale = scale || 1;
    list.forEach(function (m) {
      var card = document.createElement('div'); card.className = 'card';
      var vb = m.viewBox, up = m.height_px, fw = m.footprint[0], fd = m.footprint[1];
      var s = el('svg', { width: vb[2] * scale + 12, height: vb[3] * scale + 12, viewBox: (-6) + ' ' + (-6) + ' ' + (vb[2] + 12) + ' ' + (vb[3] + 12) }, card);
      el('rect', { x: -6, y: -6, width: vb[2] + 12, height: vb[3] + 12, fill: '#c9c79a' }, s);
      var grid = '';
      for (var i = 0; i <= fw; i++) grid += 'M' + i * CELL + ' ' + up + 'V' + (up + fd * CELL);
      for (var j = 0; j <= fd; j++) grid += 'M0 ' + (up + j * CELL) + 'H' + fw * CELL;
      el('path', { d: grid, fill: 'none', stroke: '#7a6a4a', 'stroke-opacity': 0.35, 'stroke-dasharray': '3 3' }, s);
      use(s, m.id, 0, 0, vb[2], vb[3]);
      el('circle', { cx: m.anchor[0], cy: m.anchor[1], r: 2.5, fill: '#9a3b2a' }, s);
      var cap = document.createElement('div'); cap.className = 'cap';
      cap.textContent = m.id + ' · ' + fw + '×' + fd + (m.facility ? ' · ' + m.facility : '');
      card.appendChild(cap);
      host.appendChild(card);
    });
  }

  root.TownArtWC_preview = { renderCastle: renderCastle, renderAtlas: renderAtlas, GW: GW, GH: GH };
})(typeof window !== 'undefined' ? window : this);
