/*
 * 织梦 · east-site-2 预览页脚本：生成 sprite、图册与每种资源点的 10×8 格示意小地图。
 * 场景格式（各 s-*.js 导出的 scenes）：{ key, title, ground: [[id, gx, gy, w, h]], road: [[gx, gy], ...]（相邻格连成土路，须通到地图边），
 *   site: [id, gx, gy], props: [[id, gx, gy]] }；gx, gy 是占地左上角所在格。主体与摆件按锚点 y（同 y 按 x）排序绘制。
 */
(function () {
  'use strict';
  var CELL = 48, GW = 10, GH = 8, SC = 0.75;
  var ES = window.TownArt_eastSite2.buildAll();
  var EG = window.TownArt_eastGround ? window.TownArt_eastGround.buildAll() : null;
  document.getElementById('sprites').innerHTML = (EG ? EG.spriteSvg() : '') + ES.spriteSvg();
  var meta = {}; ES.items.forEach(function (it) { meta[it.id] = it.meta; });
  var hasEarth = EG && EG.items.some(function (it) { return it.id === 'east-common-ground-earth-01'; });
  function useAt(id, x, y, w, h) { return '<use href="#' + id + '" x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '"/>'; }

  function render1(sc) {
    var o = '', x, y, seed = 7, miss = [];
    for (y = 0; y < GH; y++) for (x = 0; x < GW; x++) {
      seed = (seed * 1103515245 + 12345) & 0x7fffffff;
      o += hasEarth ? useAt('east-common-ground-earth-0' + (1 + seed % 4), x * CELL, y * CELL, CELL, CELL) : '<rect x="' + x * CELL + '" y="' + y * CELL + '" width="48" height="48" fill="#d9c58f"/>';
    }
    (sc.ground || []).forEach(function (g) {
      if (!meta[g[0]]) { miss.push(g[0]); return; }
      for (var yy = g[2]; yy < g[2] + g[4]; yy++) for (var xx = g[1]; xx < g[1] + g[3]; xx++) o += useAt(g[0], xx * CELL, yy * CELL, CELL, CELL);
    });
    var set = {};
    (sc.road || []).forEach(function (c) { set[c[0] + ',' + c[1]] = 1; });
    (sc.road || []).forEach(function (c) {
      var X = c[0] * CELL, Y = c[1] * CELL;
      var l = set[(c[0] - 1) + ',' + c[1]] || c[0] === 0 ? 0 : 9, r = set[(c[0] + 1) + ',' + c[1]] || c[0] === GW - 1 ? 0 : 9;
      var t = set[c[0] + ',' + (c[1] - 1)] || c[1] === 0 ? 0 : 9, b = set[c[0] + ',' + (c[1] + 1)] || c[1] === GH - 1 ? 0 : 9;
      o += '<rect x="' + (X + l) + '" y="' + (Y + t) + '" width="' + (CELL - l - r) + '" height="' + (CELL - t - b) + '" fill="#ecd7a2"/>';
      var E = 'stroke="#b08048" stroke-width="1.4" opacity="0.75"';
      if (l) o += '<line x1="' + (X + l) + '" y1="' + (Y + t) + '" x2="' + (X + l) + '" y2="' + (Y + CELL - b) + '" ' + E + '/>';
      if (r) o += '<line x1="' + (X + CELL - r) + '" y1="' + (Y + t) + '" x2="' + (X + CELL - r) + '" y2="' + (Y + CELL - b) + '" ' + E + '/>';
      if (t) o += '<line x1="' + (X + l) + '" y1="' + (Y + t) + '" x2="' + (X + CELL - r) + '" y2="' + (Y + t) + '" ' + E + '/>';
      if (b) o += '<line x1="' + (X + l) + '" y1="' + (Y + CELL - b) + '" x2="' + (X + CELL - r) + '" y2="' + (Y + CELL - b) + '" ' + E + '/>';
      o += '<circle cx="' + (X + 14 + (c[0] * 13 + c[1] * 7) % 20) + '" cy="' + (Y + 18 + (c[0] * 5 + c[1] * 11) % 14) + '" r="1.6" fill="#c79c5c" opacity="0.6"/>';
    });
    var list = [];
    [sc.site].concat(sc.props || []).forEach(function (it) {
      var m = meta[it[0]]; if (!m) { miss.push(it[0]); return; }
      var W = m.viewBox[2], H = m.viewBox[3], ax = it[1] * CELL + W / 2, ay = (it[2] + m.footprint[1]) * CELL;
      list.push({ ay: ay, ax: ax, s: useAt(m.id, ax - W / 2, ay - H, W, H) });
    });
    list.sort(function (a, b) { return a.ay - b.ay || a.ax - b.ax; });
    o += list.map(function (e) { return e.s; }).join('');
    var W0 = GW * CELL, H0 = GH * CELL;
    return '<div class="scene" data-key="' + sc.key + '"><h3>' + sc.title + (miss.length ? ' <small style="color:#c00">缺 ' + miss.join(', ') + '</small>' : '') + '</h3>' +
      '<svg width="' + W0 * SC + '" height="' + H0 * SC + '" viewBox="0 0 ' + W0 + ' ' + H0 + '">' + o + '</svg></div>';
  }
  document.getElementById('scenes').innerHTML = ES.scenes.map(render1).join('');

  var groups = {}, order = [];
  ES.items.forEach(function (it) { var k = it.meta.resource + (it.meta.subtype ? ' / ' + it.meta.subtype : ''); if (!groups[k]) { groups[k] = []; order.push(k); } groups[k].push(it.meta); });
  var html = '';
  order.forEach(function (k) {
    html += '<h3>' + k + '</h3><div class="atlas">';
    groups[k].forEach(function (m) {
      var vb = m.viewBox, sc = m.category === 'site' ? 1 : 1.5;
      html += '<div class="card"><svg width="' + vb[2] * sc + '" height="' + vb[3] * sc + '" viewBox="' + vb.join(' ') + '" style="overflow:visible"><use href="#' + m.id + '"/></svg>' +
        m.name + '<br><code>' + m.id + '</code><br>' + m.footprint.join('×') + ' · ' + (m.facility || '—') + '</div>';
    });
    html += '</div>';
  });
  document.getElementById('atlas').innerHTML = html;
  window.ES2_META = meta;
})();
