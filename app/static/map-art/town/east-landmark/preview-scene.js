/*
 * east-landmark 预览页脚本：图册（0.6 倍缩略，点击 1.5 倍大图）+ 城镇一角示意场景。
 * 场景只读引用 east-base（民居）与 east-special（特殊建筑）的生成函数；按锚点 y 排序绘制，同 y 按 x。
 */
(function () {
  'use strict';
  var NS = 'http://www.w3.org/2000/svg', CELL = 48;
  var A = window.TownArt_eastLandmark;
  var metas = A.list(), byId = {};
  metas.forEach(function (m) { byId[m.id] = m; });

  // —— 把三套 sprite 都放进页面（不用 display:none：会让 symbol 内的 clipPath 失效）——
  function addSprite(txt) {
    var d = document.createElement('div');
    d.innerHTML = txt.replace('style="display:none"', 'width="0" height="0" style="position:absolute;width:0;height:0;overflow:hidden" aria-hidden="true"');
    document.body.insertBefore(d.firstElementChild, document.body.firstChild);
  }
  addSprite(A.spriteSvg());
  if (window.TownArt_eastBase) {
    var eb = window.TownArt_eastBase.buildAll();
    addSprite(eb.spriteSvg());
    eb.items.forEach(function (it) { if (!byId[it.id]) byId[it.id] = it.meta; });
  }
  if (window.TownArt_eastSpecial) {
    addSprite(window.TownArt_eastSpecial.spriteSvg());
    window.TownArt_eastSpecial.list().forEach(function (m) { if (!byId[m.id]) byId[m.id] = m; });
  }

  function useSvg(m, k, pad) {
    var w = m.viewBox[2], h = m.viewBox[3];
    return '<svg xmlns="' + NS + '" width="' + Math.round((w + pad * 2) * k) + '" height="' + Math.round((h + pad * 2) * k) + '" viewBox="' + (-pad) + ' ' + (-pad) + ' ' + (w + pad * 2) + ' ' + (h + pad * 2) + '">' +
      '<rect x="' + (-pad) + '" y="' + (-pad) + '" width="' + (w + pad * 2) + '" height="' + (h + pad * 2) + '" fill="#d9c58f"/>' +
      '<rect x="0" y="' + m.height_px + '" width="' + w + '" height="' + (h - m.height_px) + '" fill="none" stroke="#8c3d22" stroke-width="1" stroke-dasharray="4 3" opacity="0.6"/>' +
      '<use href="#' + m.id + '" x="0" y="0" width="' + w + '" height="' + h + '"/>' +
      '<circle cx="' + m.anchor[0] + '" cy="' + m.anchor[1] + '" r="3" fill="#e0322a"/></svg>';
  }

  // —— 图册 ——
  var grid = document.getElementById('grid'), zoom = document.getElementById('zoom'), zb = document.getElementById('zoomBox');
  metas.forEach(function (m) {
    var card = document.createElement('div'); card.className = 'card';
    card.innerHTML = useSvg(m, 0.6, 8) +
      '<div class="nm">' + m.name_zh + '</div><div class="id">' + m.id + '</div>' +
      '<div class="ft">占地 ' + m.footprint.join('×') + ' · 上伸 ' + m.height_px + ' px · ' + m.culture + ' · ' + (m.facility || 'null') + '</div>';
    card.onclick = function () {
      zb.innerHTML = useSvg(m, 1.5, 8) + '<div class="nm">' + m.name_zh + '　' + m.id + '</div><div class="ft" style="max-width:900px;margin:4px auto">' + (m.note || '') + '</div>';
      zoom.className = 'on';
    };
    grid.appendChild(card);
  });
  zoom.onclick = function () { zoom.className = ''; };

  // —— 城镇一角示意场景 ——
  // 地块：[id, 列, 行]（占地矩形左上角所在格）；不存在的 id 跳过（便于逐步加地标）
  // 南北街 = 第 11 列，东西街 = 第 7 行；地块互不重叠
  var COLS = 26, ROWS = 15, TOP = 250, ROAD_ROW = 7, ROAD_COL = 11;
  var PLACE = [
    ['east-common-taoist-temple-01', 0, 1], ['east-common-pagoda-02', 8, 1], ['east-common-famous-tower-01', 6, 3],
    ['east-common-house-xieshan-01', 6, 1],
    ['east-common-pagoda-01', 12, 2], ['east-common-house-puwu-01', 12, 6], ['east-common-house-huipai-02', 14, 6],
    ['east-common-buddhist-temple-01', 15, 1], ['east-common-taoist-temple-02', 21, 1],
    ['east-common-confucian-temple-01', 0, 8],
    ['east-common-house-siheyuan-01', 6, 8], ['east-common-house-huipai-01', 8, 8], ['east-common-house-huipai-02', 10, 8],
    ['east-common-paifang-01', 6, 10], ['east-common-temple-04', 9, 11], ['east-common-inn-01', 6, 12],
    ['east-common-pagoda-03', 12, 8], ['east-common-market-hall-01', 12, 12],
    ['east-common-palace-hall-01', 15, 8], ['east-common-house-yuanlin-01', 21, 8],
    ['east-common-house-siheyuan-02', 15, 13], ['east-common-house-puwu-02', 17, 13], ['east-common-house-huipai-03', 19, 13],
    ['east-common-house-sanheyuan-01', 0, 14], ['east-common-house-puwu-03', 2, 14], ['east-common-house-yingshan-01', 3, 14],
    ['east-common-house-zhulou-02', 4, 14], ['east-common-house-tulou-01', 21, 11], ['east-common-house-maoshe-01', 23, 11],
    ['east-common-floating-pavilion-01', 23, 8]
  ];
  var Wpx = COLS * CELL, Hpx = ROWS * CELL + TOP, g = '';
  g += '<rect width="' + Wpx + '" height="' + Hpx + '" fill="#d9c58f"/>';
  // 示意路面：一条东西大街 + 一条南北街
  g += '<rect x="0" y="' + (TOP + ROAD_ROW * CELL) + '" width="' + Wpx + '" height="' + CELL + '" fill="#cdbb91"/>';
  g += '<rect x="' + (ROAD_COL * CELL) + '" y="' + TOP + '" width="' + CELL + '" height="' + (ROWS * CELL) + '" fill="#cdbb91"/>';
  var d = '';
  for (var c = 0; c <= COLS; c++) d += 'M' + c * CELL + ' ' + TOP + 'V' + Hpx;
  for (var r = 0; r <= ROWS; r++) d += 'M0 ' + (TOP + r * CELL) + 'H' + Wpx;
  g += '<path d="' + d + '" stroke="#b8a170" stroke-width="0.5" opacity="0.5" fill="none"/>';
  var items = [], missing = [];
  PLACE.forEach(function (p) {
    var m = byId[p[0]]; if (!m) { missing.push(p[0]); return; }
    var ax = p[1] * CELL + m.footprint[0] * CELL / 2, ay = TOP + (p[2] + m.footprint[1]) * CELL;
    items.push({ m: m, ax: ax, ay: ay });
  });
  items.sort(function (a, b) { return a.ay - b.ay || a.ax - b.ax; });
  items.forEach(function (it) {
    var m = it.m;
    g += '<use href="#' + m.id + '" x="' + (it.ax - m.anchor[0]) + '" y="' + (it.ay - m.anchor[1]) + '" width="' + m.viewBox[2] + '" height="' + m.viewBox[3] + '"/>';
  });
  document.getElementById('scene').innerHTML = '<svg xmlns="' + NS + '" width="' + Wpx + '" height="' + Hpx + '" viewBox="0 0 ' + Wpx + ' ' + Hpx + '">' + g + '</svg>';
  window.__lmMissing = missing;
  window.__lmReady = true;
})();
