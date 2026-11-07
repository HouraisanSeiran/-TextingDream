/*
 * 极光预览底图：layout-samples.js 的五种样例（village / town / city / port / fortress）+ town-render.js 渲染。
 * 做法同 daylight/preview-port.js：TownRender.render 画进屏幕外容器（不用 display:none，否则 <use> 不出图）→
 * 改 viewBox 裁出窗口（小样例放大铺满）→ 分「地面+水」「建筑/树」两张栅格化。建筑那张同时当 scene.occluder。
 * 依赖 daylight/preview-town.js 提供的 DaylightTown.raster / symbolText（只调用，不改它）。
 */
(function (root) {
  'use strict';
  var W = 1400, H = 900, NS = 'http://www.w3.org/2000/svg';
  function pick(name, style) {
    var S = root.TOWN_LAYOUT_SAMPLES || [];
    for (var i = 0; i < S.length; i++) if (S[i].sample === name && S[i].style === style && S[i].race === 'common') return S[i];
    for (i = 0; i < S.length; i++) if (S[i].sample === name) return S[i];
    return S[0] || null;
  }
  function build(name, style, dpr, done) {
    var smp = pick(name, style), cat = root.TOWN_CATALOG, DT = root.DaylightTown;
    if (!smp || !root.TownRender || !cat || !DT) { done(null); return; }
    var L = smp.layout, g = L.grid, C = g.cell, meta = {};
    cat.meta.forEach(function (m) { meta[m.id] = m; });
    // 视窗：样例比画布小就放大铺满，大就居中裁切；港口把水道放在画面下部
    var gw = g.w * C, gh = g.h * C, k = Math.max(1, W / gw, H / (gh + C)), vw = W / k, vh = H / k;
    var ox = Math.round((gw - vw) / 2), oy = Math.round((gh - vh) / 2);
    var wy = (g.water || []).reduce(function (a, p) { return Math.max(a, p[1]); }, -1);
    if (wy >= 0) oy = Math.max(-C, Math.min((g.h + 0.5) * C - vh, (wy + 0.5) * C - vh * 0.62));
    function X(x) { return (x - ox) * k; } function Y(y) { return (y - oy) * k; }
    var host = document.createElement('div');
    host.style.cssText = 'position:absolute;left:0;top:0;width:0;height:0;overflow:hidden';
    document.body.appendChild(host);
    function svgText(layout, strip) {
      var svg = root.TownRender.render(host, layout, cat);
      svg.setAttribute('viewBox', [ox, oy, vw, vh].join(' ')); svg.setAttribute('width', W); svg.setAttribute('height', H);
      svg.setAttribute('preserveAspectRatio', 'none'); svg.setAttribute('xmlns', NS); svg.removeAttribute('style');
      if (strip) { var r = svg.querySelector('rect'); if (r) r.remove(); }
      svg.querySelectorAll('title').forEach(function (t) { t.remove(); });
      var txt = new XMLSerializer().serializeToString(svg), used = {};
      txt.replace(/href="#([^"]+)"/g, function (_, id) { used[id] = 1; });
      var defs = Object.keys(used).map(DT.symbolText).join('');
      return txt.replace(/^<svg[^>]*>/, function (m) { return m + '<defs>' + defs + '</defs>'; });
    }
    var gText = svgText(Object.assign({}, L, { items: [] }), false);
    var oText = svgText(Object.assign({}, L, { ground: [], grid: Object.assign({}, g, { water: [] }) }), true);
    host.remove();
    var scene = { width: W, height: H, cell: C * k, water: [], buildings: [], lights: [], ground: [], town: smp.name + ' · ' + smp.style };
    (g.water || []).forEach(function (p) { scene.water.push([X(p[0] * C), Y(p[1] * C), C * k, C * k]); });
    (g.roads || []).forEach(function (p) { scene.ground.push([X(p[0] * C), Y(p[1] * C), C * k, C * k]); });
    var R = root.WeatherNoise.rng((smp.seed | 0) * 31 + 7);
    L.items.forEach(function (it) {
      var m = meta[it.id]; if (!m) return;
      var x = X(it.x), y = Y(it.bottom - m.anchor[1]), w = m.viewBox[2] * k, h = m.viewBox[3] * k, bottom = Y(it.bottom);
      if (x + w < -80 || x > W + 80 || y > H + 40 || bottom < -40) return;
      var hp = (m.height_px || 40) * k;
      scene.buildings.push({ x: x, y: y, w: w, h: h, roofY: y, depth: Math.max(10, h - hp), wall: m.category === 'wall' });
      if ((m.category !== 'house' && m.category !== 'special') || /dock|bridge|well|carry-pole/.test(it.id)) return;
      var n = Math.max(1, Math.round(w / (44 * k)) + (R() < 0.3 ? 1 : 0));
      for (var i = 0; i < n; i++) scene.lights.push({ x: x + w * (i + 0.5 + (R() - 0.5) * 0.25) / n, y: bottom - Math.min(26 * k, hp * 0.42) - 4, kind: 'window' });
    });
    var walls = scene.buildings.filter(function (b) { return b.wall; });
    scene.lights = scene.lights.filter(function (l) {
      return !walls.some(function (b) { return l.x >= b.x && l.x <= b.x + b.w && l.y >= b.y + 4 && l.y <= b.y + b.h; });
    });
    (L.infrastructure || []).forEach(function (f) {
      if (f.facility !== 'gate' || !f.cell) return;   // 城市样例有的城门没有 cell
      scene.lights.push({ x: X(f.cell[0] * C + 6), y: Y(f.cell[1] * C + 8), kind: 'fire' }, { x: X((f.cell[0] + 1) * C - 6), y: Y(f.cell[1] * C + 8), kind: 'fire' });
    });
    DT.raster(gText, dpr, function (gc) {
      DT.raster(oText, dpr, function (oc) {
        // occluder：CSS 尺寸的前景剪影（规范第 7 节）
        var occ = document.createElement('canvas'); occ.width = W; occ.height = H;
        if (oc) occ.getContext('2d').drawImage(oc, 0, 0, W, H);
        scene.occluder = occ; scene.objectsImage = oc; scene.objectsScale = dpr;
        done({ ground: gc, objects: oc, scene: scene });
      });
    });
  }
  root.AuroraTown = { build: build };
})(this);
