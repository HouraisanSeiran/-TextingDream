/*
 * 织梦 · 矮人聚落示意（只用于 preview.html）：一段带城门与矮堡塔的巨石城墙（双网格）+ 民居 + 市场 + 铁匠铺 + 议事厅。
 * 逻辑格 (c, r) 占 x c*48..c*48+48、y r*48..r*48+48。渲染瓦片 (i, j) 的四角 = 逻辑格 (i,j)(i+1,j)(i,j+1)(i+1,j+1) 的中心。
 * 全部按锚点 y 从小到大绘制（同 y 按 x）。浏览器挂 window.TownArtWD_scene。
 */
(function (root) {
  'use strict';
  var COLS = 18, ROWS = 10, TOP = 150;
  // 城墙逻辑格：北面一道直墙 + 两端向南折（两个 L 形拐角）
  function isWall(c, r) {
    if (r === 1 && c >= 1 && c <= 16) return true;
    if ((c === 1 || c === 16) && r >= 1 && r <= 4) return true;
    return false;
  }
  // 建筑：[id, c, r]（c,r 为占地左上逻辑格）
  var BUILD = [
    ['west-dwarf-town-hall-01', 7, 3], ['west-dwarf-forge-01', 12, 3], ['west-dwarf-forge-02', 13, 6],
    ['west-dwarf-market-01', 2, 6], ['west-dwarf-stall-01', 5, 7], ['west-dwarf-stall-02', 6, 8],
    ['west-dwarf-house-07-2', 4, 2], ['west-dwarf-house-01-1', 2, 2], ['west-dwarf-house-04-1', 3, 4],
    ['west-dwarf-house-03-1', 4, 4], ['west-dwarf-house-02-2', 8, 7], ['west-dwarf-house-05-1', 10, 7],
    ['west-dwarf-house-06-2', 11, 9], ['west-dwarf-house-08-2', 14, 9], ['west-dwarf-house-09-2', 2, 9],
    ['west-dwarf-house-04-3', 16, 6], ['west-dwarf-house-01-2', 10, 2], ['west-dwarf-stall-01', 7, 9]
  ];
  function render(WD, host) {
    var all = window.__WD_SYMBOLS || WD.symbols(), by = {};
    all.forEach(function (s) { by[s.id] = s; });
    var items = [];
    function put(id, ax, ay, key) {
      var s = by[id];
      if (!s) return;
      var W = s.viewBox[2], H = s.viewBox[3];
      items.push({ ax: ax, ay: key == null ? ay : key, svg: '<use href="#' + id + '" x="' + (ax - W / 2) + '" y="' + (ay - H) + '" width="' + W + '" height="' + H + '"/>' });
    }
    var i, j, c, r;
    for (j = -1; j < ROWS; j++) for (i = -1; i < COLS; i++) {
      var m = (isWall(i, j) ? 8 : 0) + (isWall(i + 1, j) ? 4 : 0) + (isWall(i, j + 1) ? 2 : 0) + (isWall(i + 1, j + 1) ? 1 : 0);
      if (!m) continue;
      put('west-dwarf-wall-' + ('000' + m.toString(2)).slice(-4), i * 48 + 48, j * 48 + 72);
    }
    // 叠加件：城门放在直墙逻辑格上，塔放在两个拐角；锚点 = 逻辑格前沿中点。
    // 排序键取前沿 + 24.5：要压在覆盖同一逻辑格后半的那块墙瓦片（锚点 = 前沿 + 24）之上
    function over(id, c, r) { put(id, c * 48 + 24, (r + 1) * 48, (r + 1) * 48 + 24.5); }
    over('west-dwarf-wall-gate-h', 8, 1);
    over('west-dwarf-wall-tower', 1, 1);
    over('west-dwarf-wall-tower', 16, 1);
    over('west-dwarf-wall-gate-v', 16, 3);
    BUILD.forEach(function (b) {
      var s = by[b[0]];
      if (!s) return;
      var fp = s.meta.footprint;
      put(b[0], b[1] * 48 + fp[0] * 24, (b[2] + fp[1]) * 48);
    });
    items.sort(function (a, b) { return a.ay - b.ay || a.ax - b.ax; });
    // 地面：草地 + 城门进来的石板路 + 矿车轨道示意
    var g = '<rect x="0" y="0" width="' + COLS * 48 + '" height="' + ROWS * 48 + '" fill="#c9c79a"/>';
    g += '<rect x="' + (8 * 48 + 6) + '" y="96" width="36" height="48" fill="#bfb093" stroke="#4a3826" stroke-opacity="0.4"/>';
    g += '<rect x="' + (2 * 48) + '" y="' + (5 * 48 + 8) + '" width="' + (15 * 48) + '" height="32" fill="#bfb093" fill-opacity="0.7" stroke="#4a3826" stroke-opacity="0.35"/>';
    for (c = 0; c < COLS; c++) for (r = 0; r < ROWS; r++)
      g += '<rect x="' + c * 48 + '" y="' + r * 48 + '" width="48" height="48" fill="none" stroke="#4a3826" stroke-opacity="0.07"/>';
    var W = COLS * 48, H = ROWS * 48 + TOP;
    host.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="' + W * 1.25 + '" height="' + H * 1.25 + '" viewBox="0 ' + (-TOP) + ' ' + W + ' ' + H + '">' +
      g + items.map(function (t) { return t.svg; }).join('') + '</svg>';
  }
  root.TownArtWD_scene = { render: render, isWall: isWall };
})(typeof window !== 'undefined' ? window : this);
