/*
 * 天色天气预览 · 城镇底图（规范第 6 节）：layout-samples.js + town-render.js。
 * 照 weather-fx/index.js 的做法：裁出 1400×900 窗口，分「地面+水」「建筑/城墙/摆件」两张栅格，
 * 另栅格化建筑/城墙/树剪影作 scene.occluder；scene 从布局算（道路格、水面格、建筑包围盒、灯光点）。
 * 挂 window.SkyTown = { samples, build(idx, dpr, done) }，done({ ground, objects, scene, label, ok })。
 */
(function (root) {
  'use strict';
  var W = 1400, H = 900, NS = 'http://www.w3.org/2000/svg';
  var BLD = { house: 1, special: 1, castle: 1, landmark: 1, fort: 1, site: 1 };
  var META = null;
  function cat() { return root.TOWN_CATALOG; }
  function meta() {
    if (!META) { META = {}; cat().meta.forEach(function (m) { META[m.id] = m; }); }
    return META;
  }
  function symbolText(id) {
    var s = cat().sprite, i = s.indexOf('<symbol id="' + id + '"');
    return i < 0 ? '' : s.slice(i, s.indexOf('</symbol>', i) + 9);
  }
  function withDefs(txt) {
    var used = {}, queue = [], defs = '';
    function scan(t) { t.replace(/href="#([^"]+)"/g, function (_, id) { if (!used[id]) { used[id] = 1; queue.push(id); } }); }
    scan(txt);
    while (queue.length) { var d = symbolText(queue.shift()); if (d) { defs += d; scan(d); } }
    return txt.replace(/^<svg[^>]*>/, function (m) { return m + '<defs>' + defs + '</defs>'; });
  }
  function svgText(host, layout, win, strip) {
    var svg = root.TownRender.render(host, layout, cat());
    svg.setAttribute('viewBox', win.join(' ')); svg.setAttribute('width', W); svg.setAttribute('height', H);
    svg.setAttribute('preserveAspectRatio', 'none'); svg.setAttribute('xmlns', NS); svg.removeAttribute('style');
    if (strip) { var r = svg.querySelector('rect'); if (r) r.remove(); }
    svg.querySelectorAll('title').forEach(function (t) { t.remove(); });
    return withDefs(new XMLSerializer().serializeToString(svg));
  }
  function raster(txt, scale, cb) {
    var img = new Image(), url = URL.createObjectURL(new Blob([txt], { type: 'image/svg+xml' }));
    img.onload = function () {
      var c = document.createElement('canvas'); c.width = W * scale; c.height = H * scale;
      c.getContext('2d').drawImage(img, 0, 0, c.width, c.height); URL.revokeObjectURL(url); cb(c);
    };
    img.onerror = function () { URL.revokeObjectURL(url); cb(null); };
    img.src = url;
  }
  function build(host, idx, dpr, done) {
    var S = root.TOWN_LAYOUT_SAMPLES || [], smp = S[idx] || S[0], M = meta();
    if (!smp) { done(null); return; }
    var L = smp.layout, g = L.grid, C = g.cell;
    var vb0 = root.TownRender.render(host, L, cat()).viewBox.baseVal;
    var s = Math.max(1, W / vb0.width, H / vb0.height), ww = W / s, wh = H / s;
    var vx = vb0.x + (vb0.width - ww) / 2, vy = vb0.y + (vb0.height - wh) / 2;
    if ((g.water || []).length) {
      var wy = g.water.reduce(function (a, p) { return Math.max(a, p[1]); }, 0);
      vy = Math.max(vb0.y, Math.min(vb0.y + vb0.height - wh, (wy + 0.5) * C - wh * 0.62));
    }
    var win = [vx, vy, ww, wh];
    function R(x, y, w, h) { return [(x - vx) * s, (y - vy) * s, w * s, h * s]; }
    var scene = { width: W, height: H, cell: C * s, water: [], buildings: [], lights: [], ground: [] };
    (g.roads || []).forEach(function (p) { scene.ground.push(R(p[0] * C, p[1] * C, C, C)); });
    (g.water || []).forEach(function (p) { scene.water.push(R(p[0] * C, p[1] * C, C, C)); });
    var occItems = [];
    L.items.forEach(function (it) {
      var m = M[it.id]; if (!m) return;
      var top = it.bottom - m.anchor[1], b = R(it.x, top, m.viewBox[2], m.viewBox[3]), hp = m.height_px || 40;
      if (BLD[m.category] || m.category === 'wall' || /tree|bush/.test(it.id)) occItems.push(it);
      if (b[0] + b[2] < -80 || b[0] > W + 80 || b[1] > H + 40 || b[1] + b[3] < -40) return;
      var bottom = (it.bottom - vy) * s;
      if (/campfire|brazier|torch/.test(it.id)) { scene.lights.push({ x: b[0] + b[2] / 2, y: bottom - 14 * s, kind: 'fire' }); return; }
      if (!BLD[m.category]) return;
      scene.buildings.push({ x: b[0], y: b[1], w: b[2], h: b[3], roofY: b[1] + 2 * s });
      if (m.category === 'house' || m.category === 'special') scene.lights.push({ x: b[0] + b[2] / 2, y: bottom - Math.min(26, hp * 0.42) * s - 4, kind: 'window' });
    });
    (g.roads || []).forEach(function (p) {
      if (root.WeatherNoise.hash32(p[0] * 73856093 ^ p[1] * 19349663) % 9 !== 0) return;
      var q = R(p[0] * C + C * 0.3, p[1] * C + C * 0.85, 0, 0);
      if (q[0] > -20 && q[0] < W + 20 && q[1] > 0 && q[1] < H + 40) scene.lights.push({ x: q[0] + 6, y: q[1] - 32, kind: 'lamp' });
    });
    var gText = svgText(host, Object.assign({}, L, { items: [] }), win, false);
    var oText = svgText(host, Object.assign({}, L, { ground: [], grid: Object.assign({}, g, { water: [] }) }), win, true);
    var cText = svgText(host, Object.assign({}, L, { ground: [], items: occItems, grid: Object.assign({}, g, { water: [] }) }), win, true);
    host.replaceChildren();
    var base = L.style === 'east' ? '#ced6aa' : '#bfcba9';
    raster(gText, dpr, function (gc) {
      raster(oText, dpr, function (oc) {
        raster(cText, 1, function (cc) {
          var bg = document.createElement('canvas'); bg.width = W * dpr; bg.height = H * dpr;
          var bx = bg.getContext('2d'); bx.fillStyle = base; bx.fillRect(0, 0, bg.width, bg.height);
          if (gc) bx.drawImage(gc, 0, 0);
          if (cc) scene.occluder = cc;
          if (oc) { scene.objectsImage = oc; scene.objectsScale = dpr; }
          done({ ground: bg, objects: oc, scene: scene, ok: !!(gc && oc),
            label: smp.sample + '/' + smp.style + '/' + smp.race + '/' + smp.seed });
        });
      });
    });
  }
  root.SkyTown = { build: build, label: function (smp) { return smp.sample + '/' + smp.style + '/' + smp.race + '/' + smp.seed; } };
})(this);
