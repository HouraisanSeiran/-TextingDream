/* 织梦 · 强风预览：城镇底图（layout-samples + town-render，规范第 6 节）→ scene（3.2 节）+ scene.occluder（第 7 节）
 * TownRender 自己建 sprite 容器（0×0 绝对定位）；SVG 被 CSS 固定成 1400×900、preserveAspectRatio=meet，
 * 布局坐标 → 舞台坐标 P = (p - vb.xy) * s + o。 */
(function () {
  'use strict';
  var W = 1400, H = 900, cat = window.TOWN_CATALOG, SAMPLES = window.TOWN_LAYOUT_SAMPLES || [];
  var meta = new Map(cat.meta.map(function (m) { return [m.id, m]; }));
  var BUILD_CAT = { house: 1, special: 1, castle: 1, wall: 1, fort: 1, landmark: 1, site: 1 };
  var tf = null, cur = null;
  function $(id) { return document.getElementById(id); }
  function keyOf(s) { return s.sample + '/' + s.style + '/' + s.race + '/' + s.seed; }
  function isOccluder(m, id) { return BUILD_CAT[m.category] || /tree|bush/.test(id); }
  function rectOf(x, y, w, h) { return [(x - tf.vx) * tf.s + tf.ox, (y - tf.vy) * tf.s + tf.oy, w * tf.s, h * tf.s]; }

  function fillSelect(sel) {
    SAMPLES.forEach(function (s) { var o = document.createElement('option'); o.value = o.textContent = keyOf(s); sel.appendChild(o); });
  }
  function occluderSvg(lay) {
    var used = {}, defs = '', body = '';
    lay.items.forEach(function (it) {
      var m = meta.get(it.id); if (!m || !isOccluder(m, it.id)) return;
      if (!used[it.id]) {
        var a = cat.sprite.indexOf('<symbol id="' + it.id + '"'), e = cat.sprite.indexOf('</symbol>', a);
        if (a >= 0 && e > a) defs += cat.sprite.slice(a, e + 9);
        used[it.id] = 1;
      }
      body += '<use href="#' + it.id + '" x="' + it.x + '" y="' + (it.bottom - m.anchor[1]) + '" width="' + m.viewBox[2] + '" height="' + m.viewBox[3] + '"/>';
    });
    return '<svg xmlns="http://www.w3.org/2000/svg" width="' + W + '" height="' + H + '" viewBox="' +
      [tf.vx, tf.vy, tf.vw, tf.vh].join(' ') + '" preserveAspectRatio="xMidYMid meet"><defs>' + defs + '</defs>' + body + '</svg>';
  }
  /** 城镇整图栅格化（daylight 的 multiply / soft-light 必须叠在同一张 canvas 的城镇像素上，透明画布上会变成整片乘色） */
  function withDefs(txt) {
    var used = {}, queue = [], defs = '';
    function sym(id) { var s = cat.sprite, i = s.indexOf('<symbol id="' + id + '"'); return i < 0 ? '' : s.slice(i, s.indexOf('</symbol>', i) + 9); }
    function scan(t) { t.replace(/href="#([^"]+)"/g, function (_, id) { if (!used[id]) { used[id] = 1; queue.push(id); } }); }
    scan(txt);
    while (queue.length) { var d = sym(queue.shift()); if (d) { defs += d; scan(d); } }
    return txt.replace(/^<svg[^>]*>/, function (m) { return m + '<defs>' + defs + '</defs>'; });
  }
  function rasterTown(svg, bg, scale, done) {
    var c0 = svg.cloneNode(true);
    c0.setAttribute('xmlns', 'http://www.w3.org/2000/svg'); c0.setAttribute('width', W); c0.setAttribute('height', H);
    c0.setAttribute('preserveAspectRatio', 'xMidYMid meet'); c0.removeAttribute('style');
    c0.querySelectorAll('title').forEach(function (t) { t.remove(); });
    var txt = withDefs(new XMLSerializer().serializeToString(c0));
    var img = new Image(), url = URL.createObjectURL(new Blob([txt], { type: 'image/svg+xml' }));
    img.onload = function () {
      var c = document.createElement('canvas'); c.width = W * scale; c.height = H * scale;
      var g = c.getContext('2d'); g.fillStyle = bg; g.fillRect(0, 0, c.width, c.height);
      g.drawImage(img, 0, 0, c.width, c.height); URL.revokeObjectURL(url); done(c);
    };
    img.onerror = function () { URL.revokeObjectURL(url); done(null); };
    img.src = url;
  }
  function buildOccluder(lay, done) {
    var img = new Image(), url = URL.createObjectURL(new Blob([occluderSvg(lay)], { type: 'image/svg+xml' }));
    img.onload = function () { var c = document.createElement('canvas'); c.width = W; c.height = H; c.getContext('2d').drawImage(img, 0, 0, W, H); URL.revokeObjectURL(url); done(c); };
    img.onerror = function () { URL.revokeObjectURL(url); done(null); };
    img.src = url;
  }
  /** 载入城镇；onScene(scene) 先回调一次（无 occluder），occluder 栅格化完成后再回调一次 */
  function load(key, onScene, scale) {
    var smp = SAMPLES.find(function (s) { return keyOf(s) === key; }) ||
      SAMPLES.find(function (s) { return s.sample === 'port' && s.style === 'west'; }) || SAMPLES[0];
    if (!smp) return null;
    $('townSel').value = keyOf(smp);
    var lay = cur = smp.layout, C0 = lay.grid.cell;
    var tsvg = TownRender.render($('townView'), lay, cat);
    var bgc = lay.style === 'east' ? '#ced6aa' : '#bfcba9';
    $('stage').style.background = bgc;
    var vb = tsvg.getAttribute('viewBox').split(/\s+/).map(Number), s = Math.min(W / vb[2], H / vb[3]);
    tf = { vx: vb[0], vy: vb[1], vw: vb[2], vh: vb[3], s: s, ox: (W - vb[2] * s) / 2, oy: (H - vb[3] * s) / 2 };
    var scene = { width: W, height: H, cell: C0 * s, water: [], buildings: [], lights: [], ground: [] };
    (lay.grid.roads || []).forEach(function (p) { scene.ground.push(rectOf(p[0] * C0, p[1] * C0, C0, C0)); });
    (lay.grid.water || []).forEach(function (p) { scene.water.push(rectOf(p[0] * C0, p[1] * C0, C0, C0)); });
    lay.items.forEach(function (it) {
      var m = meta.get(it.id); if (!m) return;
      var top = it.bottom - m.anchor[1];
      if (m.category === 'house' || m.category === 'special' || m.category === 'castle' || m.category === 'landmark') {
        var r = rectOf(it.x, top, m.viewBox[2], m.viewBox[3]);
        scene.buildings.push({ x: r[0], y: r[1], w: r[2], h: r[3], roofY: r[1] + 3 * s });
        var lp = rectOf(it.x + m.viewBox[2] * 0.5, it.bottom - 18, 0, 0); scene.lights.push({ x: lp[0], y: lp[1], kind: 'window' });
      } else if (/campfire|brazier|torch/.test(it.id)) {
        var fp = rectOf(it.x + 24, it.bottom - 16, 0, 0); scene.lights.push({ x: fp[0], y: fp[1], kind: 'fire' });
      }
    });
    (lay.grid.roads || []).forEach(function (p) {
      if (window.WeatherNoise.hash32(p[0] * 73856093 ^ p[1] * 19349663) % 9 !== 0) return;
      var q = rectOf(p[0] * C0 + C0 / 2, p[1] * C0 + C0 / 2, 0, 0); scene.lights.push({ x: q[0], y: q[1], kind: 'lamp' });
    });
    window.__scene = scene; window.__occluderReady = false;
    onScene(scene);
    var pend = 2;
    function fin() { if (--pend === 0) { onScene(scene); window.__occluderReady = true; } }
    rasterTown(tsvg, bgc, scale || 1, function (c) { if (lay !== cur) return; scene.townImage = c; fin(); });
    buildOccluder(lay, function (c) { if (lay !== cur) return; if (c) scene.occluder = c; fin(); });
    return scene;
  }
  window.WIND_TOWN = { W: W, H: H, load: load, fillSelect: fillSelect, keyOf: keyOf };
})();
