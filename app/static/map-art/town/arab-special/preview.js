/* 预览页脚本：内联 sprite（0×0 绝对定位容器），图册 + 城镇广场示意（按锚点 y 排序绘制）。 */
(function () {
  'use strict';
  var A = window.TownArt_arabSpecial, K = window.TownArtAS_core, C = K.C, CELL = K.CELL;
  document.getElementById('sprite-host').innerHTML = A.sprite();
  var byId = {}; A.list().forEach(function (d) { byId[d.id] = d; });
  var SC = 1.5;
  // 图册
  var html = '';
  A.metaAll().forEach(function (m) {
    var w = m.viewBox[2], h = m.viewBox[3], up = m.height_px, s = m.footprint[0] * CELL, dd = m.footprint[1] * CELL;
    var grid = '';
    for (var i = 0; i <= m.footprint[0]; i++) grid += 'M' + i * CELL + ' ' + up + 'V' + h;
    for (var j = 0; j <= m.footprint[1]; j++) grid += 'M0 ' + (up + j * CELL) + 'H' + w;
    html += '<div class="card"><svg width="' + w * SC + '" height="' + (h + 6) * SC + '" viewBox="0 0 ' + w + ' ' + (h + 6) + '">' +
      '<path d="' + grid + '" stroke="#a97f4c" stroke-width="0.5" stroke-opacity="0.5" fill="none"/>' +
      '<use href="#' + m.id + '" width="' + w + '" height="' + h + '"/>' +
      '<circle cx="' + m.anchor[0] + '" cy="' + m.anchor[1] + '" r="2" fill="#a8502e"/></svg>' +
      '<div>' + m.name + ' · ' + s / CELL + '×' + dd / CELL + (m.culture ? ' · ' + m.culture : '') + '</div>' +
      '<div class="id">' + m.id + (m.facility ? ' · ' + m.facility : ' · null') + '</div></div>';
  });
  document.getElementById('atlas').innerHTML = html;
  // 广场示意：gx,gy 为占地左上格
  var GW = 17, GH = 12, TOP = 3;
  // 北排：清真寺 / 巴扎 / 商队客栈；广场中心水井，四周摊位；南排：浴室 / 旅舍
  var place = [
    ['arab-common-mosque-01', 1, 1], ['arab-common-bazaar-01', 6, 2], ['arab-common-caravanserai-01', 11, 1],
    ['arab-common-well-01', 8, 7], ['arab-common-stall-spice-01', 6, 5], ['arab-common-stall-rug-01', 10, 5],
    ['arab-common-stall-pottery-01', 6, 8], ['arab-common-stall-lamp-01', 10, 8], ['arab-common-stall-spice-01', 7, 9],
    ['arab-common-hammam-01', 1, 9], ['arab-common-inn-01', 13, 9], ['arab-common-minaret-01', 15, 6]
  ].filter(function (p) { return byId[p[0]]; });
  var W = GW * CELL, H = (GH + TOP) * CELL, g = '';
  g += '<rect width="' + W + '" height="' + H + '" fill="#e3cf9f"/>';
  var px0 = 0, py0 = (TOP + 4) * CELL, pw = GW * CELL, ph = 8 * CELL, d = '';
  g += '<rect x="' + px0 + '" y="' + py0 + '" width="' + pw + '" height="' + ph + '" fill="#e8dcc2" stroke="#4a3020" stroke-width="1"/>';
  for (var y = py0 + 16; y < py0 + ph; y += 16) d += 'M' + px0 + ' ' + y + 'H' + (px0 + pw);
  for (var r = 0, yy = py0; yy < py0 + ph; yy += 16, r++) for (var x = px0 + (r % 2) * 12 + 24; x < px0 + pw; x += 24) d += 'M' + x + ' ' + yy + 'v16';
  g += '<path d="' + d + '" stroke="#a97f4c" stroke-width="0.7" stroke-opacity="0.6" fill="none"/>';
  var items = place.map(function (p) {
    var m = A.meta(byId[p[0]]);
    var ax = (p[1] + m.footprint[0] / 2) * CELL, ay = (TOP + p[2] + m.footprint[1]) * CELL;
    return { m: m, ax: ax, ay: ay };
  });
  items.sort(function (a, b) { return a.ay - b.ay || a.ax - b.ax; });
  items.forEach(function (it) {
    var m = it.m;
    g += '<use href="#' + m.id + '" x="' + (it.ax - m.anchor[0]) + '" y="' + (it.ay - m.anchor[1]) + '" width="' + m.viewBox[2] + '" height="' + m.viewBox[3] + '"/>';
  });
  document.getElementById('plaza').innerHTML = '<svg width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '">' + g + '</svg>';
})();
