/* 预览页：图册 + 每种资源一张 10×8 格示意小地图（草地底纹只读引用 west-ground 现场生成） */
(function () {
  'use strict';
  var WS = window.TownArt_westSite, WG = window.TownArt_westGround, CELL = 48;
  var NS = 'http://www.w3.org/2000/svg';
  var items = WS.build(), byId = {};
  items.forEach(function (i) { byId[i.id] = i.meta; });
  var grass = [];
  var host = '';
  if (WG && WG.symbols) {
    WG.symbols().forEach(function (s) {
      if (/^west-common-ground-grass-0\d$/.test(s.id)) { grass.push(s.id); host += WG.symbolSVG(s); }
    });
  }
  // sprite 容器 0×0 绝对定位（不用 display:none，否则 clipPath 失效）
  document.getElementById('sprite-host').innerHTML =
    '<svg xmlns="' + NS + '" width="0" height="0" style="position:absolute;width:0;height:0;overflow:hidden">' + host +
    items.map(function (i) { return i.svg; }).join('') + '</svg>';

  function use(id, x, y, w, h) {
    return '<use href="#' + id + '" x="' + x + '" y="' + y + '" width="' + w + '" height="' + h + '"/>';
  }
  /* ---------- 图册 ---------- */
  var atlas = document.getElementById('atlas'), html = '';
  items.forEach(function (i) {
    var m = i.meta, W = m.viewBox[2], H = m.viewBox[3], sc = m.category === 'ground' ? 2 : 1;
    html += '<div class="card"><svg width="' + W * sc + '" height="' + H * sc + '" viewBox="0 0 ' + W + ' ' + H + '">' +
      use(i.id, 0, 0, W, H) + '</svg><b>' + m.name + '</b>' + m.id.replace('west-common-', '') + '<br>' +
      m.footprint.join('×') + ' · 上伸' + m.height_px + ' · ' + m.resource + (m.facility ? ' · ' + m.facility : '') + '</div>';
  });
  atlas.innerHTML = html;

  /* ---------- 示意小地图 ---------- */
  function rnd(seed) { return function () { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; }; }
  function scene(sc, k) {
    var GW = 10, GH = 8, W = GW * CELL, H = GH * CELL, r = rnd(k * 977 + 13), s = '', x, y;
    // 1) 草地底纹
    for (y = 0; y < GH; y++) for (x = 0; x < GW; x++) {
      if (grass.length) s += use(grass[Math.floor(r() * grass.length)], x * CELL, y * CELL, CELL, CELL);
      else s += '<rect x="' + x * CELL + '" y="' + y * CELL + '" width="48" height="48" fill="#c9c79a"/>';
    }
    // 2) 专用地面（ground 格）：[x, y, w, h] 区域按变体轮换铺
    (sc.ground || []).forEach(function (g) {
      var ids = items.filter(function (i) { return i.meta.category === 'ground' && i.meta.kind === g.kind; }).map(function (i) { return i.id; });
      if (!ids.length) return;
      for (var yy = g.y; yy < g.y + g.h; yy++) for (var xx = g.x; xx < g.x + g.w; xx++)
        s += use(ids[(xx * 7 + yy * 3) % ids.length], xx * CELL, yy * CELL, CELL, CELL);
    });
    // 2b) 水面区域（预览用平涂，水色与码头统一 #a9b8ad）：[x, y, w, h] 格
    (sc.water || []).forEach(function (q) {
      s += '<rect x="' + q[0] * CELL + '" y="' + q[1] * CELL + '" width="' + q[2] * CELL + '" height="' + q[3] * CELL + '" fill="#a9b8ad"/>' +
        '<path d="M' + q[0] * CELL + ' ' + q[1] * CELL + 'h' + q[2] * CELL + '" stroke="#4a3826" stroke-width="1.6" fill="none"/>';
    });
    // 3) 土路：一条从地图边缘通往主体前的路（预览用简单路面，不是正式瓦片）
    if (sc.road) {
      var pts = sc.road.map(function (p) { return (p[0] * CELL) + ' ' + (p[1] * CELL); }).join(' L');
      s += '<path d="M' + pts + '" fill="none" stroke="#93764d" stroke-width="30" stroke-linejoin="round" stroke-linecap="round"/>' +
        '<path d="M' + pts + '" fill="none" stroke="#c2ab7f" stroke-width="26" stroke-linejoin="round" stroke-linecap="round"/>' +
        '<path d="M' + pts + '" fill="none" stroke="#a98a5e" stroke-width="1" stroke-dasharray="6 9" stroke-opacity=".7" transform="translate(-6 0)"/>' +
        '<path d="M' + pts + '" fill="none" stroke="#a98a5e" stroke-width="1" stroke-dasharray="5 11" stroke-opacity=".7" transform="translate(6 0)"/>';
    }
    // 4) 主体与摆件：按锚点 y 排序（同 y 按 x）
    var objs = (sc.items || []).map(function (it) {
      var m = byId[it[0]];
      if (!m) return null;
      var bx = it[1] * CELL, by = (it[2] + m.footprint[1]) * CELL;     // 占地矩形前沿
      return { id: it[0], x: bx, y: by - m.viewBox[3], w: m.viewBox[2], h: m.viewBox[3], ay: by, ax: bx + m.anchor[0] };
    }).filter(Boolean);
    objs.sort(function (a, b) { return a.ay - b.ay || a.ax - b.ax; });
    objs.forEach(function (o) { s += use(o.id, o.x, o.y, o.w, o.h); });
    return '<div class="scene"><h3>' + sc.name + ' <small>' + sc.resource + '</small></h3><svg width="' + W + '" height="' + H +
      '" viewBox="0 0 ' + W + ' ' + H + '" style="overflow:hidden;display:block">' + s + '</svg></div>';
  }
  var SC = window.TownArtWS_scenes || [];
  document.getElementById('scenes').innerHTML = SC.map(scene).join('');
  window.__wsReady = true;
})();
