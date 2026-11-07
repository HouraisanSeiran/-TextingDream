/*
 * 织梦 · east-site 预览：每种资源一张约 10×8 格示意小地图。
 * 地面铺 east-ground 黄土底纹 earth-01..04（只读引用 ../east-ground/*.js 生成的 symbol），
 * 专用地面按格平铺，土路是一串格子，主体与摆件按锚点 y（同 y 按 x）排序绘制。
 * 场景项 [symbolId, gx, gy]：gx, gy 是占地左上角所在格。浏览器挂 window.ES_SCENES。
 */
(function (root) {
  'use strict';
  var CELL = 48, GW = 10, GH = 8, SC = 0.75;
  var SCENES = [];
  /** 新增一张场景。o = { title, ground: [[prefix, n, cells]], road: [[x,y],...], items: [[id, gx, gy]] } */
  function scene(o) { SCENES.push(o); }
  function rect(x0, y0, x1, y1) { var a = []; for (var y = y0; y <= y1; y++) for (var x = x0; x <= x1; x++) a.push([x, y]); return a; }
  /** 从 (x0,y0) 走到地图边的一条折线土路：pts 是拐点格序列。 */
  function road(pts) {
    var a = [];
    for (var i = 0; i + 1 < pts.length; i++) {
      var p = pts[i], q = pts[i + 1], dx = Math.sign(q[0] - p[0]), dy = Math.sign(q[1] - p[1]), x = p[0], y = p[1];
      a.push([x, y]); while (x !== q[0] || y !== q[1]) { x += dx; y += dy; a.push([x, y]); }
    }
    return a;
  }
  function useAt(id, x, y, w, h) { return '<use href="#' + id + '" x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '"/>'; }

  function render1(sc, meta) {
    var o = '', x, y, seed = 7, miss = [];
    for (y = 0; y < GH; y++) for (x = 0; x < GW; x++) { seed = (seed * 1103515245 + 12345) & 0x7fffffff; o += useAt('east-common-ground-earth-0' + (1 + seed % 4), x * CELL, y * CELL, CELL, CELL); }
    (sc.ground || []).forEach(function (g) {
      g[2].forEach(function (c, i) {
        // g[1] = 0：g[0] 就是完整 id（整块用同一变体）
        var id = g[1] === 0 ? g[0] : g[0] + (g[1] > 1 ? (1 + (c[0] * 7 + c[1] * 3 + i) % g[1]) : 1);
        if (!meta[id]) { miss.push(id); return; }
        o += useAt(id, c[0] * CELL, c[1] * CELL, CELL, CELL);
      });
    });
    // 土路：踩实的浅黄土，边缘略收
    var set = {};
    (sc.road || []).forEach(function (c) { set[c[0] + ',' + c[1]] = 1; });
    (sc.road || []).forEach(function (c) {
      var X = c[0] * CELL, Y = c[1] * CELL, l = set[(c[0] - 1) + ',' + c[1]] ? 0 : 9, r = set[(c[0] + 1) + ',' + c[1]] ? 0 : 9,
        t = set[c[0] + ',' + (c[1] - 1)] ? 0 : 9, b = set[c[0] + ',' + (c[1] + 1)] ? 0 : 9;
      o += '<rect x="' + (X + l) + '" y="' + (Y + t) + '" width="' + (CELL - l - r) + '" height="' + (CELL - t - b) + '" fill="#ecd7a2"/>';
      var E = 'stroke="#b08048" stroke-width="1.4" opacity="0.75"';
      if (l) o += '<line x1="' + (X + l) + '" y1="' + (Y + t) + '" x2="' + (X + l) + '" y2="' + (Y + CELL - b) + '" ' + E + '/>';
      if (r) o += '<line x1="' + (X + CELL - r) + '" y1="' + (Y + t) + '" x2="' + (X + CELL - r) + '" y2="' + (Y + CELL - b) + '" ' + E + '/>';
      if (t) o += '<line x1="' + (X + l) + '" y1="' + (Y + t) + '" x2="' + (X + CELL - r) + '" y2="' + (Y + t) + '" ' + E + '/>';
      if (b) o += '<line x1="' + (X + l) + '" y1="' + (Y + CELL - b) + '" x2="' + (X + CELL - r) + '" y2="' + (Y + CELL - b) + '" ' + E + '/>';
      o += '<circle cx="' + (X + 14 + (c[0] * 13 + c[1] * 7) % 20) + '" cy="' + (Y + 18 + (c[0] * 5 + c[1] * 11) % 14) + '" r="1.6" fill="#c79c5c" opacity="0.6"/>';
    });
    var list = [];
    (sc.items || []).forEach(function (it) {
      var m = meta[it[0]]; if (!m) { miss.push(it[0]); return; }
      var W = m.viewBox[2], H = m.viewBox[3], ax = it[1] * CELL + W / 2, ay = (it[2] + m.footprint[1]) * CELL;
      list.push({ ay: ay, ax: ax, s: useAt(m.id, ax - W / 2, ay - H, W, H) });
    });
    list.sort(function (a, b) { return a.ay - b.ay || a.ax - b.ax; });
    o += list.map(function (e) { return e.s; }).join('');
    var W0 = GW * CELL, H0 = GH * CELL;
    return '<div class="scene"><h3>' + sc.title + (miss.length ? ' <small style="color:#c00">缺 ' + miss.join(', ') + '</small>' : '') + '</h3>' +
      '<svg width="' + W0 * SC + '" height="' + H0 * SC + '" viewBox="0 0 ' + W0 + ' ' + H0 + '">' + o + '</svg></div>';
  }
  function render(meta) { return SCENES.map(function (s) { return render1(s, meta); }).join(''); }

  root.ES_SCENES = { render: render, scene: scene, rect: rect, road: road, list: SCENES };
})(this);
