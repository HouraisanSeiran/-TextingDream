/*
 * west-landmark 预览页脚本：图册（0.6 倍缩略，点击放大）+ 城镇一角示意场景。
 * 场景只读引用 west-base（民居）与 west-special（特殊建筑）的 js 现场生成 symbol，按锚点 y 排序绘制。
 */
(function () {
  'use strict';
  var WL = window.TownArt_westLandmark, WB = window.TownArt_westBase, WS = window.TownArt_westSpecial, CELL = 48, K = 0.6;
  var defs = WL.list(), lm = {}, all = {};
  defs.forEach(function (d) { lm[WL.idOf(d)] = d; var s = WL.dims(d); all[WL.idOf(d)] = { W: s.W, H: s.H, up: d.up, fp: d.fp }; });

  // —— 共享 symbol：地标 + 民居 + 特殊建筑 ——
  var sp = WL.spriteSVG(defs);
  if (WB) {
    var hs = WB.houses();
    hs.forEach(function (h) { all[h.id] = { W: h.viewBox[2], H: h.viewBox[3], up: h.up, fp: h.meta.footprint }; });
    sp += WB.spriteSVG(hs);
  }
  if (WS) {
    var wd = WS.list();
    wd.forEach(function (d) { var s = WS.dims(d); all[WS.idOf(d)] = { W: s.W, H: s.H, up: d.up, fp: d.fp }; });
    sp += '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute;overflow:hidden">' + wd.map(WS.symbol).join('') + '</svg>';
  }
  document.getElementById('sprites').innerHTML = sp;

  // —— 图册 ——
  function card(d, k) {
    var s = WL.dims(d), id = WL.idOf(d), m = WL.meta(d), g = '';
    for (var x = CELL; x < s.W; x += CELL) g += '<line x1="' + x + '" y1="' + d.up + '" x2="' + x + '" y2="' + s.H + '" stroke="#4a3826" stroke-opacity="0.15"/>';
    for (var y = d.up + CELL; y < s.H; y += CELL) g += '<line x1="0" y1="' + y + '" x2="' + s.W + '" y2="' + y + '" stroke="#4a3826" stroke-opacity="0.15"/>';
    return '<svg xmlns="http://www.w3.org/2000/svg" width="' + s.W * k + '" height="' + s.H * k + '" viewBox="0 0 ' + s.W + ' ' + s.H + '">' +
      '<rect x="0" y="' + d.up + '" width="' + s.W + '" height="' + (s.H - d.up) + '" fill="#000" fill-opacity="0.05" stroke="#4a3826" stroke-opacity="0.25" stroke-dasharray="3 3"/>' +
      g + '<use href="#' + id + '"/><circle cx="' + m.anchor[0] + '" cy="' + m.anchor[1] + '" r="2.5" fill="#c0392b"/></svg>' +
      '<div class="zh">' + d.name + '</div><div class="id">' + id + '</div>' +
      '<div class="id">' + m.culture + ' · ' + m.facility + ' · ' + d.fp[0] + '×' + d.fp[1] + ' · 上伸 ' + d.up + '</div>';
  }
  var grid = document.getElementById('grid'), html = '';
  defs.forEach(function (d) { html += '<div class="cell" data-id="' + WL.idOf(d) + '">' + card(d, K) + '</div>'; });
  grid.innerHTML = html;
  var zoom = document.getElementById('zoom'), zb = document.getElementById('zoombox');
  grid.addEventListener('click', function (e) {
    var c = e.target.closest('.cell'); if (!c) return;
    zb.innerHTML = card(lm[c.getAttribute('data-id')], 1.5); zoom.classList.add('on');
  });
  zoom.addEventListener('click', function () { zoom.classList.remove('on'); });

  // —— 示意场景：城镇一角 ——
  // [id, 占地左列, 占地后行]；缺失的 id 跳过
  var COLS = 32, ROWS = 15, TOP = 250;
  var items = [
    ['west-common-castle-hill-01', 0, 0], ['west-common-cathedral-01', 7, 1], ['west-common-abbey-01', 13, 0],
    ['west-common-amphitheatre-01', 19, 0], ['west-common-roman-temple-01', 20, 7], ['west-common-forum-01', 14, 8],
    ['west-common-campanile-01', 12, 5], ['west-common-triumphal-arch-01', 9, 12],
    ['west-common-abbey-02', 26, 0], ['west-common-castle-hill-02', 26, 6], ['west-common-thermae-01', 27, 12],
    ['west-common-aqueduct-end-w-01', 0, 13], ['west-common-aqueduct-ew-01', 1, 13], ['west-common-aqueduct-ew-01', 2, 13],
    ['west-common-aqueduct-ew-01', 3, 13], ['west-common-aqueduct-end-e-01', 4, 13],
    ['west-common-temple-02', 0, 8], ['west-common-town-hall-01', 4, 8], ['west-common-market-hall-01', 9, 8],
    ['west-common-inn-01', 20, 12], ['west-common-well-01', 13, 13],
    ['west-common-house-01-1', 7, 7], ['west-common-house-03-2', 3, 11], ['west-common-house-05-1', 5, 11],
    ['west-common-house-02-1', 12, 12], ['west-common-house-04-3', 16, 13], ['west-common-house-06-1', 18, 13],
    ['west-common-house-07-2', 23, 12], ['west-common-house-08-1', 24, 13], ['west-common-house-02-3', 7, 13]
  ];
  var W = COLS * CELL, H = ROWS * CELL + TOP, o = '', g = '', list = [], miss = [];
  for (var x = 0; x <= W; x += CELL) g += 'M' + x + ' ' + TOP + 'V' + H;
  for (var y = TOP; y <= H; y += CELL) g += 'M0 ' + y + 'H' + W;
  o += '<rect width="' + W + '" height="' + H + '" fill="#c9c79a"/>';
  // 简单的土路与广场（只为示意，不是正式道路瓦片）
  o += '<path d="M0 ' + (TOP + 12 * CELL) + 'H' + W + 'V' + (TOP + 13 * CELL) + 'H0Z M' + (13 * CELL) + ' ' + (TOP + 7 * CELL) + 'h' + CELL + 'V' + (TOP + 12 * CELL) + 'h-' + CELL + 'Z" fill="#d8c49a"/>';
  o += '<path d="' + g + '" stroke="#4a3826" stroke-opacity="0.08" fill="none"/>';
  items.forEach(function (it) {
    var a = all[it[0]];
    if (!a) { miss.push(it[0]); return; }
    var fx = it[1] * CELL, fy = TOP + it[2] * CELL;
    list.push({ id: it[0], x: fx, y: fy - a.up, W: a.W, H: a.H, ay: fy + a.fp[1] * CELL, ax: fx + a.W / 2 });
  });
  list.sort(function (a, b) { return a.ay - b.ay || a.ax - b.ax; });
  list.forEach(function (it) { o += '<use href="#' + it.id + '" x="' + it.x + '" y="' + it.y + '" width="' + it.W + '" height="' + it.H + '"/>'; });
  document.getElementById('scene').innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '">' + o + '</svg>' +
    (miss.length ? '<div class="id">场景中尚未提供：' + miss.join('、') + '</div>' : '');

  // —— 引水渠拼接：同一套格子坐标，按锚点 y 排序 ——
  (function () {
    var JW = 9 * CELL, JT = 130, JH = JT + 7 * CELL, s = [], o = '', g = '';
    var row = ['aqueduct-end-w-01', 'aqueduct-ew-01', 'aqueduct-ew-01', 'aqueduct-ew-01', 'aqueduct-end-e-01'];
    row.forEach(function (id, i) { s.push(['west-common-' + id, i, 5]); });
    var col = ['aqueduct-end-n-01', 'aqueduct-ns-01', 'aqueduct-ns-01', 'aqueduct-ns-01', 'aqueduct-end-s-01'];
    col.forEach(function (id, i) { s.push(['west-common-' + id, 7, i + 1]); });
    for (var x = 0; x <= JW; x += CELL) g += 'M' + x + ' ' + JT + 'V' + JH;
    for (var y = JT; y <= JH; y += CELL) g += 'M0 ' + y + 'H' + JW;
    o += '<rect width="' + JW + '" height="' + JH + '" fill="#c9c79a"/><path d="' + g + '" stroke="#4a3826" stroke-opacity="0.12" fill="none"/>';
    var L = [];
    s.forEach(function (it) { var a = all[it[0]]; if (!a) return; var fx = it[1] * CELL, fy = JT + it[2] * CELL; L.push({ id: it[0], x: fx, y: fy - a.up, W: a.W, H: a.H, ay: fy + a.fp[1] * CELL, ax: fx }); });
    L.sort(function (a, b) { return a.ay - b.ay || a.ax - b.ax; });
    L.forEach(function (it) { o += '<use href="#' + it.id + '" x="' + it.x + '" y="' + it.y + '" width="' + it.W + '" height="' + it.H + '"/>'; });
    document.getElementById('joins').innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="' + JW * 2 + '" height="' + JH * 2 + '" viewBox="0 0 ' + JW + ' ' + JH + '" style="border:1px solid rgba(74,56,38,.4)">' + o + '</svg>';
  })();
})();
