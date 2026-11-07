/* 织梦 · 冰冻天气预览页脚本：城镇底图（layout-samples + town-render）→ scene / occluder → ice + daylight 叠层 */
(function () {
  'use strict';
  var C = 48, W = 1400, H = 900;
  var cat = window.TOWN_CATALOG, meta = new Map(cat.meta.map(function (m) { return [m.id, m]; }));
  var $ = function (id) { return document.getElementById(id); };
  var SAMPLES = window.TOWN_LAYOUT_SAMPLES || [];
  var BUILD_CAT = { house: 1, special: 1, castle: 1, wall: 1, fort: 1, landmark: 1, site: 1 };
  var scene = null, tf = null, curLayout = null, mods = null, townC = null;
  var dpr = Math.min(2, +new URLSearchParams(location.search).get('dpr') || window.devicePixelRatio || 1);
  SAMPLES.forEach(function (s) {
    var o = document.createElement('option');
    o.value = s.sample + '/' + s.style + '/' + s.race + '/' + s.seed; o.textContent = o.value;
    $('townSel').appendChild(o);
  });
  // 前景剪影：建筑 + 树 / 灌木 / 栅栏（雾凇、霜挂在这些东西的上沿和边缘）
  function isOccluder(m, id) { return BUILD_CAT[m.category] || /tree|bush|pine|fence/.test(id); }
  function rectOf(x, y, w, h) { return [(x - tf.vx) * tf.s + tf.ox, (y - tf.vy) * tf.s + tf.oy, w * tf.s, h * tf.s]; }
  function loadTown(key) {
    var smp = SAMPLES.find(function (s) { return s.sample + '/' + s.style + '/' + s.race + '/' + s.seed === key; }) || SAMPLES[0];
    if (!smp) return;
    $('townSel').value = smp.sample + '/' + smp.style + '/' + smp.race + '/' + smp.seed;
    var lay = curLayout = smp.layout, C0 = lay.grid.cell;
    var tsvg = TownRender.render($('townView'), lay, cat);
    $('stage').style.background = lay.style === 'east' ? '#ced6aa' : '#bfcba9';
    var vb = tsvg.getAttribute('viewBox').split(/\s+/).map(Number), s = Math.min(W / vb[2], H / vb[3]);
    tf = { vx: vb[0], vy: vb[1], vw: vb[2], vh: vb[3], s: s, ox: (W - vb[2] * s) / 2, oy: (H - vb[3] * s) / 2 };
    scene = { width: W, height: H, cell: C0 * s, water: [], buildings: [], lights: [], ground: [] };
    (lay.grid.roads || []).forEach(function (p) { scene.ground.push(rectOf(p[0] * C0, p[1] * C0, C0, C0)); });
    (lay.grid.water || []).forEach(function (p) { scene.water.push(rectOf(p[0] * C0, p[1] * C0, C0, C0)); });
    lay.items.forEach(function (it) {
      var m = meta.get(it.id); if (!m) return;
      var top = it.bottom - m.anchor[1];
      if (m.category === 'house' || m.category === 'special' || m.category === 'castle' || m.category === 'landmark') {
        var r = rectOf(it.x, top, m.viewBox[2], m.viewBox[3]);
        scene.buildings.push({ x: r[0], y: r[1], w: r[2], h: r[3], roofY: r[1] + 3 * s });
        var lp = rectOf(it.x + m.viewBox[2] * 0.5, it.bottom - 18, 0, 0);
        scene.lights.push({ x: lp[0], y: lp[1], kind: 'window' });
      } else if (/campfire|brazier|torch/.test(it.id)) {
        var fp = rectOf(it.x + 24, it.bottom - 16, 0, 0); scene.lights.push({ x: fp[0], y: fp[1], kind: 'fire' });
      }
    });
    (lay.grid.roads || []).forEach(function (p) {
      if (window.WeatherNoise.hash32(p[0] * 73856093 ^ p[1] * 19349663) % 9 !== 0) return;
      var q = rectOf(p[0] * C0 + C0 / 2, p[1] * C0 + C0 / 2, 0, 0); scene.lights.push({ x: q[0], y: q[1], kind: 'lamp' });
    });
    window.__scene = scene; window.__occluderReady = false; townC = null;
    if (mods) mods.forEach(function (l) { l.setScene(scene); });
    // daylight 的 light pass 用正片叠底，必须和城镇画在同一张画布上：把渲染好的 SVG 栅格化成底图，每帧先画它
    var bgCol = $('stage').style.background;
    rasterSvg(townSvgText(tsvg), function (tc) {
      if (lay !== curLayout) return;
      var c = document.createElement('canvas'); c.width = W * dpr; c.height = H * dpr;
      var g = c.getContext('2d'); g.fillStyle = bgCol; g.fillRect(0, 0, c.width, c.height);
      if (tc) g.drawImage(tc, 0, 0, c.width, c.height);
      townC = c; tsvg.style.visibility = 'hidden';
      buildOccluder(lay, function (oc) {
        if (!oc || lay !== curLayout) return;
        scene.occluder = oc;
        if (mods) mods.forEach(function (l) { l.setScene(scene); });
        window.__occluderReady = true;
      });
    });
  }
  // 把 svg 里 href="#id" 引用的 symbol（含嵌套引用）拼进 <defs>，使其能脱离页面里的 sprite 容器单独栅格化
  function symbolText(id) { var s = cat.sprite, i = s.indexOf('<symbol id="' + id + '"'); return i < 0 ? '' : s.slice(i, s.indexOf('</symbol>', i) + 9); }
  function townSvgText(svg) {
    var c = svg.cloneNode(true);
    c.setAttribute('width', W); c.setAttribute('height', H); c.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    c.removeAttribute('style'); c.querySelectorAll('title').forEach(function (t) { t.remove(); });
    var txt = new XMLSerializer().serializeToString(c), used = {}, queue = [], defs = '';
    function scan(t) { t.replace(/href="#([^"]+)"/g, function (_, id) { if (!used[id]) { used[id] = 1; queue.push(id); } }); }
    scan(txt);
    while (queue.length) { var d = symbolText(queue.shift()); if (d) { defs += d; scan(d); } }
    return txt.replace(/^<svg[^>]*>/, function (m) { return m + '<defs>' + defs + '</defs>'; });
  }
  function rasterSvg(txt, done) {
    var img = new Image(), url = URL.createObjectURL(new Blob([txt], { type: 'image/svg+xml' }));
    img.onload = function () { URL.revokeObjectURL(url); done(img); };
    img.onerror = function () { URL.revokeObjectURL(url); done(null); };
    img.src = url;
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
      body += '<use href="#' + it.id + '" x="' + it.x + '" y="' + (it.bottom - m.anchor[1]) + '" width="' +
        m.viewBox[2] + '" height="' + m.viewBox[3] + '"/>';
    });
    return '<svg xmlns="http://www.w3.org/2000/svg" width="' + W + '" height="' + H + '" viewBox="' +
      [tf.vx, tf.vy, tf.vw, tf.vh].join(' ') + '" preserveAspectRatio="xMidYMid meet"><defs>' + defs + '</defs>' + body + '</svg>';
  }
  function buildOccluder(lay, done) {
    var img = new Image(), url = URL.createObjectURL(new Blob([occluderSvg(lay)], { type: 'image/svg+xml' }));
    img.onload = function () {
      var c = document.createElement('canvas'); c.width = W; c.height = H;
      c.getContext('2d').drawImage(img, 0, 0, W, H); URL.revokeObjectURL(url); done(c);
    };
    img.onerror = function () { URL.revokeObjectURL(url); done(null); };
    img.src = url;
  }
  var q0 = new URLSearchParams(location.search);
  loadTown(q0.get('town') || 'town/west/common/1');
  $('townSel').addEventListener('change', function () { loadTown(this.value); });
  // ---------------------------------------------------------------- 叠层
  var fx = $('fx');
  fx.width = W * dpr; fx.height = H * dpr;
  var ctx = fx.getContext('2d');
  var ice = window.WeatherFX_ice.create({ seed: 4321, noise: window.WeatherNoise });
  var day = window.WeatherFX_daylight.create({ seed: 4328, noise: window.WeatherNoise });
  mods = [ice, day];
  window.__ice = ice; window.__day = day;   // 供自动化测试 / 调试
  mods.forEach(function (l) { l.resize(W, H, dpr); l.setScene(scene); });
  var PASSES = ['ground', 'reflect', 'precip', 'fog', 'light', 'bow', 'aurora', 'flash'];
  // ---------------------------------------------------------------- 控件
  var ids = ['intensity', 'temp', 'hour', 'glaze', 'frost', 'rime', 'graupel', 'fog', 'dir', 'speed'];
  function val(id) { return +$(id).value; }
  function show() { ids.forEach(function (id) { $(id).nextElementSibling.textContent = $(id).value; }); }
  // 联动：切天气 / 拖强度时给出与之自洽的累积量、气温、雾（只为预览方便，模块本身只读 state）
  function link() {
    if (!$('link').checked) return;
    var k = $('kind').value, it = val('intensity'), set = function (id, v) { $(id).value = v; };
    var z = { glaze: 0, frost: 0, rime: 0, graupel: 0, fog: 0 };
    if (k === 'freezing_rain') { z.glaze = (0.08 + 0.92 * it).toFixed(2); set('temp', (-0.5 - 3 * it).toFixed(1)); set('hour', 10); }
    else if (k === 'graupel') { z.graupel = (0.05 + 0.95 * it).toFixed(2); set('temp', 1); set('hour', 14); }
    else if (k === 'frost') { z.frost = (0.08 + 0.92 * it).toFixed(2); set('temp', Math.round(-1 - 8 * it)); set('hour', 7.6); }
    else if (k === 'rime') { z.rime = (0.08 + 0.92 * it).toFixed(2); z.frost = (0.25 * it).toFixed(2); z.fog = (0.08 + 0.3 * it).toFixed(2); set('temp', Math.round(-3 - 10 * it)); set('hour', 9); }
    Object.keys(z).forEach(function (id) { set(id, z[id]); });
  }
  $('kind').addEventListener('change', function () { link(); show(); });
  $('intensity').addEventListener('input', function () { link(); show(); });
  ids.forEach(function (id) { $(id).addEventListener('input', show); });
  function state() {
    var k = $('kind').value, it = val('intensity');
    var ptype = k === 'freezing_rain' ? 'freezing_rain' : k === 'graupel' ? 'graupel' : 'none';
    return { seed: 4321, kind: k, intensity: it,
      time: { hour: val('hour'), day_of_year: 20, sunrise: 7.2, sunset: 17.1, moon_phase: 0.4 },
      precipitation: { type: ptype, rate: ptype === 'none' ? 0 : it },
      cloud_cover: k === 'frost' || k === 'clear' ? 0.1 : 0.85, fog: val('fog'),
      wind: { dir_deg: val('dir'), speed: val('speed'), gust: 0.2 }, lightning: 0, temperature_c: val('temp'),
      humidity: 0.85, visibility: Math.max(0.1, 1 - val('fog') * 0.8),
      ground: { wetness: k === 'freezing_rain' ? 0.6 : 0.1, puddles: 0, snow_cover: 0,
        glaze: val('glaze'), frost: val('frost'), rime: val('rime'), graupel: val('graupel') },
      season: 'winter', climate: 'continental' };
  }
  var paused = false, stepOnce = false;
  $('pause').onclick = function () { paused = !paused; this.textContent = paused ? '继续' : '暂停'; };
  $('step').onclick = function () { paused = true; $('pause').textContent = '继续'; stepOnce = true; };
  // ---------------------------------------------------------------- 循环 + fps
  var last = performance.now(), frames = 0, acc = 0, fpsLog = [];
  function frame(now) {
    var dt = Math.min(0.1, (now - last) / 1000); last = now;
    frames++; acc += dt;
    if (acc >= 0.5) { var f = frames / acc; fpsLog.push(f); $('fps').textContent = f.toFixed(1) + ' fps · dpr ' + dpr; frames = 0; acc = 0; }
    if (!paused || stepOnce) {
      var st = state(), d = stepOnce ? 1 / 60 : dt; stepOnce = false;
      ice.update(st, d); if ($('dl').checked) day.update(st, d);
      ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1;
      ctx.clearRect(0, 0, fx.width, fx.height);
      if (townC) ctx.drawImage(townC, 0, 0);   // 底图与叠层同画布，daylight 的正片叠底才作用在城镇上
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      PASSES.forEach(function (p) { ice.draw(ctx, p); if ($('dl').checked) day.draw(ctx, p); });
    }
    requestAnimationFrame(frame);
  }
  // 供自动化测试：设参数（先联动，再覆盖显式给出的字段）
  window.__preview = {
    set: function (o) {
      if (o.kind) $('kind').value = o.kind;
      if (o.intensity != null) $('intensity').value = o.intensity;
      if (o.kind || o.intensity != null) link();
      Object.keys(o).forEach(function (k) { if ($(k) && k !== 'kind' && k !== 'intensity') { if ($(k).type === 'checkbox') $(k).checked = !!o[k]; else $(k).value = o[k]; } });
      show();
    },
    fps: function () { var a = fpsLog.slice(-6); return a.reduce(function (s, x) { return s + x; }, 0) / Math.max(1, a.length); },
    resetFps: function () { fpsLog = []; },
    town: function (key) { loadTown(key); }
  };
  link(); show();
  requestAnimationFrame(frame);
})();
