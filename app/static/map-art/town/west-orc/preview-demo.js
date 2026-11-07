/*
 * 织梦 · 兽人营地示意（预览页用，尚未接入游戏）
 * 逻辑格 14×10，外圈一周尖木栅墙（双网格瓦片），北、南各一座 gate-h，东侧一座 gate-v。
 * 所有东西按锚点 y 从小到大（同 y 按 x）绘制。浏览器挂 window.TownArtWO_demo。
 */
(function (root) {
  'use strict';
  var S = 48, GW = 14, GH = 10, TOP = 150, PAD = 40;
  // 建筑：[id, 左上逻辑格 x, y]
  var BUILD = [
    ['west-orc-town-hall-01', 5, 1],
    ['west-orc-house-01-1', 1, 1], ['west-orc-house-01-3', 2, 1], ['west-orc-house-03-1', 3, 1], ['west-orc-house-06-1', 4, 3],
    ['west-orc-house-02-1', 1, 3], ['west-orc-house-05-1', 9, 1], ['west-orc-house-07-1', 12, 1], ['west-orc-house-09-1', 9, 3],
    ['west-orc-house-04-1', 11, 3], ['west-orc-house-08-1', 3, 5], ['west-orc-house-10-1', 6, 6], ['west-orc-house-01-2', 12, 6],
    ['west-orc-forge-01', 1, 5], ['west-orc-forge-02', 3, 8], ['west-orc-market-01', 8, 6],
    ['west-orc-stall-01', 11, 7], ['west-orc-stall-02', 11, 6], ['west-orc-house-03-2', 1, 8]
  ];
  // 栅门替换瓦片：渲染瓦片 (i, j) → id
  // 北墙在逻辑行 0：底边是它的渲染瓦片在 j=-1；南墙在逻辑行 9：底边是它的瓦片在 j=8（mask 0011）
  var GATES = { '6,-1': 'west-orc-gate-h', '6,8': 'west-orc-gate-h', '13,4': 'west-orc-gate-v' };
  function isWall(x, y) { return (x === 0 || x === GW - 1 || y === 0 || y === GH - 1) && x >= 0 && x < GW && y >= 0 && y < GH; }
  function bin(m) { return ('000' + m.toString(2)).slice(-4); }

  function render(WO, el) {
    var list = root.__WO_SYMBOLS || WO.symbols(), by = {};
    list.forEach(function (s) { by[s.id] = s; });
    var items = [], i, j;
    for (j = -1; j < GH; j++) for (i = -1; i < GW; i++) {
      var m = (isWall(i, j) ? 8 : 0) + (isWall(i + 1, j) ? 4 : 0) + (isWall(i, j + 1) ? 2 : 0) + (isWall(i + 1, j + 1) ? 1 : 0);
      if (!m) continue;
      var id = GATES[i + ',' + j] || ('west-orc-wall-' + bin(m)), s = by[id];
      if (!s) continue;
      // 渲染瓦片左上角 = 逻辑格 (i, j) 中心；锚点 = 瓦片底边中点
      items.push({ s: s, ax: i * S + S, ay: (j + 1) * S + S / 2 });
    }
    BUILD.forEach(function (b) {
      var s = by[b[0]];
      if (!s) return;
      var fp = s.meta.footprint;
      items.push({ s: s, ax: (b[1] + fp[0] / 2) * S, ay: (b[2] + fp[1]) * S });
    });
    items.sort(function (a, b) { return a.ay - b.ay || a.ax - b.ax; });
    var W = GW * S + 2 * PAD, H = GH * S + TOP + PAD, ox = PAD, oy = TOP;
    var o = '<svg xmlns="http://www.w3.org/2000/svg" width="' + Math.round(W * 1.25) + '" height="' + Math.round(H * 1.25) + '" viewBox="0 0 ' + W + ' ' + H + '">';
    o += '<rect width="' + W + '" height="' + H + '" fill="#c9c79a"/><g transform="translate(' + ox + ' ' + oy + ')">';
    // 踩出的土路：南门 → 酋长大帐 → 北门，东门 → 场心
    o += '<path d="M318 ' + (GH * S + 20) + 'L320 300L314 150L322 -30L346 -30L338 150L344 300L346 ' + (GH * S + 20) + 'Z" fill="#a98a5e" fill-opacity="0.45"/>';
    o += '<path d="M330 220L' + (GW * S + 20) + ' 212L' + (GW * S + 20) + ' 238L330 248Z" fill="#a98a5e" fill-opacity="0.45"/>';
    items.forEach(function (it) {
      var vb = it.s.viewBox;
      o += '<use href="#' + it.s.id + '" x="' + (it.ax - vb[2] / 2) + '" y="' + (it.ay - vb[3]) + '" width="' + vb[2] + '" height="' + vb[3] + '"/>';
    });
    o += '</g></svg>';
    el.innerHTML = o;
  }
  root.TownArtWO_demo = { render: render };
})(typeof window !== 'undefined' ? window : this);
