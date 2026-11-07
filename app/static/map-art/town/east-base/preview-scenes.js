/*
 * east-base 预览页的场景部分：瓦片表、双网格拼接验证、街巷示意。只给 preview.html 用。
 * 双网格：渲染瓦片 (i, j) 的左上角在世界坐标 (i*48-24, j*48-24)，四角 = 逻辑格 (j-1,i-1) (j-1,i) (j,i-1) (j,i)。
 * 叠加件（城门楼、角楼、民居）按逻辑格放：锚点 = 占地前沿中点。全部按锚点 y（同 y 按 x）排序后画。
 */
(function (root) {
  'use strict';
  var NS = 'http://www.w3.org/2000/svg', GRASS = '#d9c58f';

  root.EastPreviewScenes = function (res, useSvg) {
    var byId = {};
    res.items.forEach(function (it) { byId[it.id] = it; });
    function meta(id) { if (!byId[id]) throw new Error('缺 symbol: ' + id); return byId[id].meta; }
    function bits(m) { return ('000' + m.toString(2)).slice(-4); }
    // 把 symbol 的占地左前角放到世界 (x, yFront)
    function put(id, x, yFront) {
      var m = meta(id), W = m.viewBox[2], H = m.viewBox[3];
      return '<use href="#' + id + '" x="' + x + '" y="' + (yFront - H) + '" width="' + W + '" height="' + H + '"/>';
    }
    function cellOn(grid, r, c) { return r >= 0 && r < grid.length && c >= 0 && c < grid[0].length && grid[r][c] === 1; }
    // 双网格展开：返回 [{key, kx, svg}]
    function dual(grid, prefix, ox, oy) {
      var out = [], rows = grid.length, cols = grid[0].length;
      for (var j = 0; j <= rows; j++) for (var i = 0; i <= cols; i++) {
        var m = (cellOn(grid, j - 1, i - 1) ? 8 : 0) + (cellOn(grid, j - 1, i) ? 4 : 0) + (cellOn(grid, j, i - 1) ? 2 : 0) + (cellOn(grid, j, i) ? 1 : 0);
        if (!m) continue;
        var x = ox + i * 48 - 24, y = oy + j * 48 - 24;
        out.push({ key: y + 48, kx: x, svg: put(prefix + bits(m), x, y + 48) });
      }
      return out;
    }
    function grid(rows, cols, fn) {
      var g = [];
      for (var r = 0; r < rows; r++) { g.push([]); for (var c = 0; c < cols; c++) g[r].push(fn(r, c) ? 1 : 0); }
      return g;
    }
    function sortDraw(list) {
      return list.sort(function (a, b) { return a.key - b.key || a.kx - b.kx; }).map(function (o) { return o.svg; }).join('');
    }
    function cellLines(rows, cols, ox, oy) {
      var d = '';
      for (var r = 0; r <= rows; r++) d += 'M' + ox + ' ' + (oy + r * 48) + 'h' + cols * 48;
      for (var c = 0; c <= cols; c++) d += 'M' + (ox + c * 48) + ' ' + oy + 'v' + rows * 48;
      return '<path d="' + d + '" fill="none" stroke="#8c3d22" stroke-width="0.4" stroke-opacity="0.35" stroke-dasharray="2 3"/>';
    }
    function scene(w, h, body, scale) {
      scale = scale || 1;
      return '<svg xmlns="' + NS + '" width="' + w * scale + '" height="' + h * scale + '" viewBox="0 0 ' + w + ' ' + h + '"><rect width="' + w + '" height="' + h + '" fill="' + GRASS + '"/>' + body + '</svg>';
    }

    var host = document.getElementById('tile-sections'), html = '';

    // ---------- 1. 瓦片表 ----------
    function tileRow(title, prefix, sc) {
      var s = '<h2>' + title + '（16 张，后缀 = NW NE SW SE）</h2><div class="tiles">';
      for (var m = 0; m < 16; m++) {
        var id = prefix + bits(m), mt = meta(id), W = mt.viewBox[2], H = mt.viewBox[3], up = H - 48;
        var dots = [[0, 0, 8], [48, 0, 4], [0, 48, 2], [48, 48, 1]].map(function (q) {
          return '<circle cx="' + q[0] + '" cy="' + (q[1] + up) + '" r="2.4" fill="' + (m & q[2] ? '#cd5030' : '#fbf0d4') + '" stroke="#8c3d22" stroke-width="0.6"/>';
        }).join('');
        s += '<div class="t"><svg xmlns="' + NS + '" width="' + (W + 8) * sc + '" height="' + (H + 8) * sc + '" viewBox="-4 -4 ' + (W + 8) + ' ' + (H + 8) + '">' +
          '<rect x="0" y="' + up + '" width="48" height="48" fill="' + GRASS + '" stroke="#8c3d22" stroke-width="0.5" stroke-dasharray="2 2"/>' +
          '<use href="#' + id + '" x="0" y="0" width="' + W + '" height="' + H + '"/>' + dots + '</svg><div>' + bits(m) + '</div></div>';
      }
      return s + '</div>';
    }
    html += tileRow('黄土路 dirt', 'east-common-road-dirt-', 1.3);
    html += tileRow('青石板路 stone', 'east-common-road-stone-', 1.3);
    html += tileRow('官道 highway', 'east-common-road-highway-', 1.3);
    html += tileRow('城墙 wall', 'east-common-wall-', 1.3);

    // 叠加件
    html += '<h2>城墙叠加件（城门楼、角楼）</h2><div class="grid">';
    res.items.filter(function (it) { return it.meta.category === 'wall' && !/wall-\d{4}$/.test(it.id); }).forEach(function (it) {
      html += '<div class="card">' + useSvg(it.meta, 2) + '<div class="zh">' + it.name + '（' + it.meta.footprint.join('×') + '，facility ' + it.meta.facility + '）</div><div class="id">' + it.id + '</div></div>';
    });
    html += '</div>';

    // ---------- 2. 拼接验证 ----------
    html += '<h2>拼接验证（逻辑格数组 → 双网格实时拼出；细虚线 = 逻辑格边界）</h2><div class="note">每档道路各拼一个 L 形 + 一个十字路口；下面是带城门楼与角楼的方形城墙，南墙正中 gate-h、东墙 gate-v、四角角楼。</div>';
    var roads = ['dirt', 'stone', 'highway'], parts = '', OX = 24, OY = 24;
    var Lg = grid(5, 5, function (r, c) { return (c === 1 && r <= 3) || (r === 3 && c >= 1); });
    var Xg = grid(5, 5, function (r, c) { return r === 2 || c === 2; });
    var Wg = grid(5, 5, function (r, c) { return (r === 1 || r === 2) && c >= 1 && c <= 3 || r === 3 && c === 2; }); // 两格宽的路 + 丁字
    roads.forEach(function (k) {
      [Lg, Xg, Wg].forEach(function (g) {
        var b = sortDraw(dual(g, 'east-common-road-' + k + '-', OX, OY)) + cellLines(5, 5, OX, OY);
        parts += '<div class="scene">' + scene(5 * 48 + 48, 5 * 48 + 48, b, 1) + '</div> ';
      });
    });
    html += '<div style="margin:0 18px;display:flex;flex-wrap:wrap;gap:8px">' + parts + '</div>';

    // 方形城墙：9 × 8 逻辑格，墙在边上；城外一条官道穿过南门进城，城内一条青石板路通东门
    var R = 8, Cn = 9, ox = 48, oy = 140, wallG = grid(R, Cn, function (r, c) { return (r === 1 || r === R - 2) && c >= 1 && c <= Cn - 2 || (c === 1 || c === Cn - 2) && r >= 1 && r <= R - 2; });
    var hiG = grid(R, Cn, function (r, c) { return c === 4 && r >= 4; }), stG = grid(R, Cn, function (r, c) { return r === 4 && c >= 4; });
    var L = [];
    var flat = sortDraw(dual(hiG, 'east-common-road-highway-', ox, oy)) + sortDraw(dual(stG, 'east-common-road-stone-', ox, oy));
    L = L.concat(dual(wallG, 'east-common-wall-', ox, oy));
    // 叠加件按逻辑格放：锚点 y = 前沿；排序键放到同一行墙瓦片之后（+24.5），让它压住底下那行墙瓦片
    function overlay(id, c0, r, w) { var yF = oy + (r + 1) * 48; L.push({ key: yF + 24.5, kx: ox + c0 * 48, svg: put(id, ox + c0 * 48, yF) }); }
    overlay('east-common-wall-gate-h', 3, R - 2, 3);
    overlay('east-common-wall-gate-v', Cn - 2, 4, 1);
    overlay('east-common-wall-tower', 1, 1, 1); overlay('east-common-wall-tower-xieshan', Cn - 2, 1, 1);
    overlay('east-common-wall-tower-xieshan', 1, R - 2, 1); overlay('east-common-wall-tower', Cn - 2, R - 2, 1);
    var wb = flat + sortDraw(L) + cellLines(R, Cn, ox, oy);
    html += '<div class="scene" style="margin-top:8px">' + scene(Cn * 48 + 96, R * 48 + 170, wb, 1.4) + '</div>';

    // ---------- 3. 街巷示意 ----------
    html += '<h2>街巷示意（民居按锚点 y 排序，沿青石板路排开）</h2>';
    var SR = 9, SC = 14, sx = 24, syy = 96;
    var streetG = grid(SR, SC, function (r, c) { return r === 3 || r === 7 || c === 9 && r >= 3; });
    var lane = grid(SR, SC, function (r, c) { return c === 4 && r >= 3 && r <= 7; });
    var ls = [];
    var placeH = function (id, c, r) { var m = meta(id), yF = syy + (r + m.footprint[1]) * 48; ls.push({ key: yF, kx: sx + c * 48, svg: put(id, sx + c * 48, yF) }); };
    // 北排：前沿贴着第 3 行石板路
    placeH('east-common-house-huipai-01', 0, 2); placeH('east-common-house-puwu-01', 2, 2); placeH('east-common-house-yingshan-01', 5, 2);
    placeH('east-common-house-puwu-03', 6, 2); placeH('east-common-house-diaolou-01', 7, 2); placeH('east-common-house-xieshan-02', 10, 1);
    placeH('east-common-house-siheyuan-01', 12, 1);
    // 中排：在两条路之间
    placeH('east-common-house-yuanlin-01', 0, 5); placeH('east-common-house-sanheyuan-01', 2, 6); placeH('east-common-house-juanpeng-01', 5, 6);
    placeH('east-common-house-huipai-02', 6, 6); placeH('east-common-house-xuanshan-01', 7, 6); placeH('east-common-house-tulou-01', 10, 5);
    placeH('east-common-house-yingshan-02', 12, 6); placeH('east-common-house-maoshe-01', 13, 6);
    placeH('east-common-house-diaojiaolou-01', 5, 4); placeH('east-common-house-puwu-02', 6, 4); placeH('east-common-house-zhulou-01', 8, 5);
    var sb = sortDraw(dual(streetG, 'east-common-road-stone-', sx, syy)) + sortDraw(dual(lane, 'east-common-road-dirt-', sx, syy)) + sortDraw(ls);
    html += '<div class="scene">' + scene(SC * 48 + 48, SR * 48 + 120, sb, 1.4) + '</div>';

    host.innerHTML = html;
  };
})(this);
