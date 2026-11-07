/*
 * 日光预览 · 港口样例底图（规范第 6 节）：layout-samples.js 的 port 样例 + town-render.js 渲染。
 * TownRender.render 画进隐藏容器 → 改 viewBox 裁出 1400×900 窗口 → 分「地面+水」「建筑」两张序列化栅格化，
 * 倒影 pass 夹在两张之间。scene 从布局算：水面格、建筑/城墙包围盒、民居与特殊建筑窗灯、路灯、城门火把。
 */
(function (root) {
  'use strict';
  var W = 1400, H = 900, NS = 'http://www.w3.org/2000/svg';
  function pick(name) {
    var S = root.TOWN_LAYOUT_SAMPLES || [], st = name === 'port-east' ? 'east' : 'west';
    for (var i = 0; i < S.length; i++) if (S[i].sample === 'port' && S[i].style === st && S[i].race === 'common') return S[i];
    return null;
  }
  function build(name, dpr, done) {
    var smp = pick(name), cat = root.TOWN_CATALOG, DT = root.DaylightTown;
    if (!smp || !root.TownRender || !cat) { done(null); return; }
    var L = smp.layout, g = L.grid, C = g.cell, meta = {};
    cat.meta.forEach(function (m) { meta[m.id] = m; });
    var wy = (g.water || []).reduce(function (a, p) { return Math.max(a, p[1]); }, 0);
    var ox = Math.round((g.w * C - W) / 2), oy = Math.max(-C, Math.min((g.h + 0.5) * C - H, (wy + 0.5) * C - H * 0.62));
    // ---- 渲染
    var host = document.createElement('div');
    host.style.cssText = 'position:absolute;left:0;top:0;width:0;height:0;overflow:hidden';
    document.body.appendChild(host);
    function svgText(layout, strip) {
      var svg = root.TownRender.render(host, layout, cat);
      svg.setAttribute('viewBox', [ox, oy, W, H].join(' ')); svg.setAttribute('width', W); svg.setAttribute('height', H);
      svg.setAttribute('xmlns', NS); svg.removeAttribute('style');
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
    // ---- scene
    var scene = { width: W, height: H, cell: C, water: [], buildings: [], lights: [], ground: [], town: smp.name + ' · ' + smp.style };
    (g.water || []).forEach(function (p) { scene.water.push([p[0] * C - ox, p[1] * C - oy, C, C]); });
    (g.roads || []).forEach(function (p) { scene.ground.push([p[0] * C - ox, p[1] * C - oy, C, C]); });
    var R = root.WeatherNoise.rng((smp.seed | 0) * 31 + 7);
    L.items.forEach(function (it) {
      var m = meta[it.id]; if (!m) return;
      var x = it.x - ox, y = it.bottom - m.anchor[1] - oy, w = m.viewBox[2], h = m.viewBox[3], bottom = it.bottom - oy;
      if (x + w < -80 || x > W + 80 || y > H + 40 || bottom < -40) return;
      var hp = m.height_px || 40;
      scene.buildings.push({ x: x, y: y, w: w, h: h, roofY: y, depth: Math.max(10, h - hp), wall: m.category === 'wall' });
      if ((m.category !== 'house' && m.category !== 'special') || /dock|bridge|well|carry-pole/.test(it.id)) return;
      var n = Math.max(1, Math.round(w / (m.category === 'special' ? 34 : 44)) + (R() < 0.3 ? 1 : 0));
      for (var i = 0; i < n; i++) scene.lights.push({ x: x + w * (i + 0.5 + (R() - 0.5) * 0.25) / n, y: bottom - Math.min(26, hp * 0.42) - 4, kind: 'window' });
      if (hp > 50 && R() < 0.6) scene.lights.push({ x: x + w * (0.3 + R() * 0.4), y: bottom - hp * 0.78, kind: 'window' });
    });
    // 路灯：主街每 5 格一盏 + 水边空地；城门两侧火把
    var occ = {}; L.buildings.forEach(function (b) {
      for (var yy = 0; yy < b.footprint[1]; yy++) for (var xx = 0; xx < b.footprint[0]; xx++) occ[(b.cell[0] + xx) + ',' + (b.cell[1] + yy)] = 1;
    });
    var water = {}; (g.water || []).forEach(function (p) { water[p[0] + ',' + p[1]] = 1; });
    var lamps = [], fires = [];
    (g.roads || []).forEach(function (p) { if (p[1] === 11 && p[0] % 5 === 3) lamps.push([p[0] * C + 10 - ox, p[1] * C + 12 - oy]); });
    for (var cx = 0; cx < g.w; cx++) for (var cy = 0; cy < g.h; cy++) {
      if (water[cx + ',' + (cy + 1)] && !water[cx + ',' + cy] && !occ[cx + ',' + cy] && (cx % 2)) lamps.push([cx * C + 24 - ox, cy * C + 44 - oy]);
    }
    (L.infrastructure || []).forEach(function (f) {
      if (f.facility !== 'gate') return;
      fires.push([f.cell[0] * C + 6 - ox, f.cell[1] * C + 8 - oy], [(f.cell[0] + 1) * C - 6 - ox, f.cell[1] * C + 8 - oy]);
    });
    // 被城墙挡住的窗灯（墙脚民居）去掉，否则夜里墙头会冒出一排灯
    var walls = scene.buildings.filter(function (b) { return b.wall; });
    scene.lights = scene.lights.filter(function (l) {
      return !walls.some(function (b) { return l.x >= b.x && l.x <= b.x + b.w && l.y >= b.y + 4 && l.y <= b.y + b.h; });
    });
    lamps.forEach(function (l) { scene.lights.push({ x: l[0], y: l[1] - 30, kind: 'lamp' }); });
    fires.forEach(function (f) { scene.lights.push({ x: f[0], y: f[1], kind: 'fire' }); });
    DT.raster(gText, dpr, function (gc) {
      DT.raster(oText, dpr, function (oc) {
        var c = document.createElement('canvas'); c.width = W * dpr; c.height = H * dpr;
        DT.drawProps(c, dpr, lamps, []);           // 路灯画在建筑之下：南侧房子能挡住它
        var cg = c.getContext('2d'); cg.setTransform(1, 0, 0, 1, 0, 0); if (oc) cg.drawImage(oc, 0, 0);
        scene.objectsImage = c; scene.objectsScale = dpr;
        done({ ground: gc, objects: c, scene: scene });
      });
    });
  }
  root.DaylightPort = { build: build };
})(this);
