/*
 * 织梦 · west-elf 预览页专用：一小片精灵村落示意（仅预览，不进 sprite）
 * 逻辑格 16×11；南墙在第 10 行、西墙在第 0 列（第 3–10 行），西南角树冠哨台，南墙第 7 列藤拱城门。
 * 墙用双网格：渲染瓦片 (i,j) 的四角 = 逻辑格 (i,j)(i+1,j)(i,j+1)(i+1,j+1) 中心。
 * 所有物件按锚点 y 从小到大绘制（同 y 按 x）；城门/哨台叠加件排在同一行墙瓦片之后。
 */
(function (root) {
  'use strict';
  var S = 48, COLS = 16, ROWS = 11, TOP = 150;

  function scene(WE, all) {
    var by = {};
    all.forEach(function (s) { by[s.id] = s; });
    var wall = {};
    function setW(c, r) { wall[c + ',' + r] = 1; }
    function isW(c, r) { return !!wall[c + ',' + r]; }
    for (var c = 0; c < COLS; c++) setW(c, 10);
    for (var r = 3; r <= 10; r++) setW(0, r);
    var items = [];
    // 墙瓦片：渲染格左上 = 逻辑格中心
    for (var j = -1; j < ROWS; j++) for (var i = -1; i < COLS; i++) {
      var m = (isW(i, j) ? 8 : 0) + (isW(i + 1, j) ? 4 : 0) + (isW(i, j + 1) ? 2 : 0) + (isW(i + 1, j + 1) ? 1 : 0);
      if (!m) continue;
      var bin = ('000' + m.toString(2)).slice(-4);
      // 渲染格横跨逻辑格中心 (i,j)…(i+1,j+1)：中心 x = i*S+S，底边 y = j*S+1.5S
      items.push({ id: 'west-elf-wall-' + bin, ax: i * S + S, ay: j * S + 1.5 * S, key: j * S + 1.5 * S });
    }
    function put(id, col, row, extra) {
      var s = by[id];
      if (!s) return;
      var fp = s.meta.footprint, ax = (col + fp[0] / 2) * S, ay = (row + fp[1]) * S;
      items.push({ id: id, ax: ax, ay: ay, key: ay + (extra || 0) });
    }
    // 叠加件对齐逻辑格；排序键加 30，确保画在同行墙瓦片之后
    put('west-elf-wall-gate-h', 7, 10, 30);
    put('west-elf-wall-tower', 0, 10, 30);
    put('west-elf-townhall-01', 6, 1);
    put('west-elf-market-01', 10, 5);
    put('west-elf-forge-01', 2, 6);
    put('west-elf-house-01-1', 2, 2);
    put('west-elf-house-01-2', 4, 3);
    put('west-elf-house-03-1', 10, 1);
    put('west-elf-temple-01', 13, 1);
    put('west-elf-house-08-1', 14, 5);
    put('west-elf-house-05-1', 14, 8);
    put('west-elf-house-06-1', 11, 8);
    put('west-elf-house-02-3', 8, 8);
    put('west-elf-house-04-1', 5, 8);
    put('west-elf-house-07-2', 2, 9);
    put('west-elf-stall-01', 13, 7);
    items.sort(function (a, b) { return a.key - b.key || a.ax - b.ax; });
    var W = COLS * S, H = ROWS * S + S / 2, sc = 1;
    var o = '<svg xmlns="http://www.w3.org/2000/svg" width="' + W * sc + '" height="' + (H + TOP) * sc + '" viewBox="0 ' + (-TOP) + ' ' + W + ' ' + (H + TOP) + '">';
    o += '<rect x="0" y="' + (-TOP) + '" width="' + W + '" height="' + (H + TOP) + '" fill="#c9c79a"/>';
    // 网格淡线 + 城门到议事殿的土路
    var g = '';
    for (c = 0; c <= COLS; c++) g += 'M' + c * S + ' 0V' + ROWS * S;
    for (r = 0; r <= ROWS; r++) g += 'M0 ' + r * S + 'H' + W;
    o += '<path d="' + g + '" stroke="#4a3826" stroke-opacity="0.08" fill="none"/>';
    o += '<rect x="' + (7 * S + 8) + '" y="' + 4 * S + '" width="' + (S - 16) + '" height="' + 7.5 * S + '" fill="#d6bd8a" stroke="#4a3826" stroke-opacity="0.35"/>';
    items.forEach(function (it) {
      var s = by[it.id];
      if (!s) return;
      var vb = s.viewBox;
      o += '<use href="#' + it.id + '" x="' + (it.ax - vb[2] / 2) + '" y="' + (it.ay - vb[3]) + '" width="' + vb[2] + '" height="' + vb[3] + '"/>';
    });
    return o + '</svg>';
  }
  root.TownArtWE_scene = scene;
})(typeof window !== 'undefined' ? window : this);
