/*
 * 织梦 · west-base 预览：瓦片表 + 双网格拼接演示（仅预览页使用）
 * 双网格：逻辑格 (x,y) 记录布尔值；渲染瓦片 (i,j) 左上角像素 = (i*48-24, j*48-24)，四角 = 逻辑格 (i-1,j-1)(i,j-1)(i-1,j)(i,j) 的中心。
 * 深度：地面（道路）先画；其余按锚点 y（底边）从小到大、同 y 按 x。叠加件（城门、塔楼）对齐逻辑格，
 *       排序键取逻辑格底边 + 24.1，保证盖在它所在墙段的渲染瓦片之上。
 */
(function (root) {
  'use strict';
  var S = 48, NS = 'http://www.w3.org/2000/svg';
  function bin(m) { return ('000' + m.toString(2)).slice(-4); }
  function byId(list) { var m = {}; list.forEach(function (s) { m[s.id] = s; }); return m; }

  /** 按逻辑格算出全部渲染瓦片 */
  function dual(rows, pred, prefix, out) {
    var H = rows.length, W = rows[0].length;
    function at(x, y) { return x >= 0 && y >= 0 && x < W && y < H && pred(rows[y].charAt(x)) ? 1 : 0; }
    for (var j = 0; j <= H; j++) for (var i = 0; i <= W; i++) {
      var m = at(i - 1, j - 1) * 8 + at(i, j - 1) * 4 + at(i - 1, j) * 2 + at(i, j);
      if (m) out.push({ id: prefix + bin(m), x: i * S - S / 2, bottom: j * S + S / 2, key: j * S + S / 2 });
    }
    return out;
  }
  function useAt(sym, x, bottom) {
    var W = sym.viewBox[2], H = sym.viewBox[3];
    return '<use href="#' + sym.id + '" x="' + x + '" y="' + (bottom - H) + '" width="' + W + '" height="' + H + '"/>';
  }
  function draw(M, ground, items) {
    var s = '';
    ground.forEach(function (it) { if (M[it.id]) s += useAt(M[it.id], it.x, it.bottom); });
    items.sort(function (a, b) { return a.key - b.key || a.x - b.x; });
    items.forEach(function (it) { if (M[it.id]) s += useAt(M[it.id], it.x, it.bottom); });
    return s;
  }
  function gridLines(W, H) {
    var d = '';
    for (var x = 0; x <= W; x++) d += 'M' + x * S + ' 0V' + H * S;
    for (var y = 0; y <= H; y++) d += 'M0 ' + y * S + 'H' + W * S;
    return '<path d="' + d + '" fill="none" stroke="#4a3826" stroke-opacity="0.12" stroke-dasharray="2 3"/>';
  }
  function scene(W, H, up, sc, inner, title) {
    var vb = [-24, -up, W * S + 48, H * S + up + 30];
    return '<div class="card" style="text-align:left"><div class="lab"><b>' + title + '</b></div>' +
      '<svg xmlns="' + NS + '" width="' + Math.round(vb[2] * sc) + '" height="' + Math.round(vb[3] * sc) + '" viewBox="' + vb.join(' ') + '">' +
      '<rect x="' + vb[0] + '" y="' + vb[1] + '" width="' + vb[2] + '" height="' + vb[3] + '" fill="#c9c79a"/>' + gridLines(W, H) + inner + '</svg></div>';
  }

  // 道路：L 形 + 十字路口 + T 形 + 对角相邻（不应连通）+ 2×2 实心块
  var ROAD_ROWS = [
    '...........',
    '.#.....#...',
    '.#.....#...',
    '.#..#######',
    '.####..#...',
    '.......#...',
    '..##...#.#.',
    '..##......#'];

  // 城墙小镇：T 塔楼、G 东西向墙上的城门、V 南北向墙上的城门、w 墙、= 石板路
  var TOWN_ROWS = [
    '....=.......',
    '.TwwGwwwwT..',
    '.w..=....w..',
    '.w..=....w..',
    '.w=======V==',
    '.w....=..w..',
    '.w....=..w..',
    '.TwwwwGwwT..',
    '......=.....',
    '......=.....'];
  var TOWN_HOUSES = [ // [type, variant, x, y]（x,y = 占地左上逻辑格）
    [1, 1, 2, 2], [3, 2, 5, 2], [5, 1, 7, 2], [2, 3, 8, 2],
    [11, 1, 2, 3], [6, 1, 5, 3], [12, 2, 7, 3],
    [9, 1, 2, 5], [7, 1, 4, 5], [15, 2, 5, 5], [10, 1, 7, 5],
    [14, 1, 0, 8], [4, 2, 7, 8], [13, 1, 10, 6], [8, 1, 3, 8]];

  function houseItem(WB, h) {
    var id = WB.houseId(h[0], h[1]), T = null;
    WB.HOUSE_TYPES.forEach(function (t) { if (t.n === h[0]) T = t; });
    return { id: id, x: h[2] * S, bottom: (h[3] + T.fp[1]) * S, key: (h[3] + T.fp[1]) * S };
  }

  function render(WB, useSVG) {
    var all = root.__WB_SYMBOLS || WB.symbols(), M = byId(all), html = '', mats = ['dirt', 'stone', 'highway'], k;
    // ---------- 瓦片表 ----------
    html += '<h2>双网格瓦片表（mask = NW·8 + NE·4 + SW·2 + SE·1；虚线 = 逻辑格边界，圆点 = 四角状态）</h2>';
    function tileCard(id, mask) {
      var s = M[id]; if (!s) return '';
      var H = s.viewBox[3], up = H - 48, sc = 1.4, m = 6;
      var o = '<svg xmlns="' + NS + '" width="' + Math.round((48 + 2 * m) * sc) + '" height="' + Math.round((H + 2 * m) * sc) + '" viewBox="' + (-m) + ' ' + (-up - m) + ' ' + (48 + 2 * m) + ' ' + (H + 2 * m) + '">';
      o += '<rect x="0" y="0" width="48" height="48" fill="#b9b78a" fill-opacity="0.5"/>';
      o += useAt(s, 0, 48);
      o += '<path d="M24 0V48M0 24H48" stroke="#4a3826" stroke-opacity="0.3" stroke-dasharray="2 2"/><rect x="0" y="0" width="48" height="48" fill="none" stroke="#4a3826" stroke-opacity="0.35"/>';
      if (mask != null) [[0, 0, 8], [48, 0, 4], [0, 48, 2], [48, 48, 1]].forEach(function (c) {
        o += '<circle cx="' + c[0] + '" cy="' + c[1] + '" r="2.4" fill="' + (mask & c[2] ? '#9a3b2a' : '#efdfb2') + '" stroke="#4a3826" stroke-width="0.8"/>';
      });
      return '<div class="card">' + o + '</svg><div class="lab">' + id.replace('west-common-', '') + '</div></div>';
    }
    mats.forEach(function (mat) {
      html += '<div class="note">道路 · ' + mat + '</div><div class="grid">';
      for (k = 0; k < 16; k++) html += tileCard('west-common-road-' + mat + '-' + bin(k), k);
      html += '</div>';
    });
    html += '<div class="note">城墙 · 16 张 + 叠加件</div><div class="grid">';
    for (k = 0; k < 16; k++) html += tileCard('west-common-wall-' + bin(k), k);
    ['gate-h', 'gate-v', 'tower-round', 'tower-square'].forEach(function (n) { html += tileCard('west-common-wall-' + n, null); });
    html += '</div>';
    document.getElementById('tiles-sec').innerHTML = html;

    // ---------- 拼接演示 ----------
    html = '<h2>拼接验证（按逻辑格数组实时用双网格算法拼出；虚线 = 逻辑格）</h2><div class="grid">';
    mats.forEach(function (mat) {
      var g = dual(ROAD_ROWS, function (c) { return c === '#'; }, 'west-common-road-' + mat + '-', []);
      html += scene(ROAD_ROWS[0].length, ROAD_ROWS.length, 10, 0.78, draw(M, g, []), '道路 ' + mat + '：L 形、十字、T 形、对角相邻（不连通）、2×2 实心');
    });
    html += '</div><div class="grid">';
    var ground = dual(TOWN_ROWS, function (c) { return c === '=' || c === 'G' || c === 'V'; }, 'west-common-road-stone-', []);
    var items = dual(TOWN_ROWS, function (c) { return 'wTGV'.indexOf(c) >= 0; }, 'west-common-wall-', []);
    var tw = 0;
    TOWN_ROWS.forEach(function (row, y) {
      for (var x = 0; x < row.length; x++) {
        var c = row.charAt(x), id = c === 'G' ? 'gate-h' : c === 'V' ? 'gate-v' : c === 'T' ? (tw++ % 2 ? 'tower-square' : 'tower-round') : null;
        if (id) items.push({ id: 'west-common-wall-' + id, x: x * S, bottom: (y + 1) * S, key: (y + 1) * S + 24.1 });
      }
    });
    TOWN_HOUSES.forEach(function (h) { items.push(houseItem(WB, h)); });
    html += scene(TOWN_ROWS[0].length, TOWN_ROWS.length, 150, 1.15, draw(M, ground, items), '城墙小镇：方形城墙 + 三座城门（北、南 gate-h，东 gate-v）+ 四角塔楼 + 石板路 + 民居（按锚点 y 排序）');
    html += '</div>';
    document.getElementById('demo-sec').innerHTML = html;
  }

  root.TownArtWB_demo = { render: render, dual: dual, ROAD_ROWS: ROAD_ROWS, TOWN_ROWS: TOWN_ROWS };
})(typeof window !== 'undefined' ? window : this);
