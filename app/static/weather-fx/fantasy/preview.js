/*
 * 奇幻天气预览页：用 town-render.js 画 layout-samples.js 里的城镇样例做底图（docs/weather-spec.md 第 6 节），
 * 从布局算出 3.2 节的 scene，把 WeatherFX_fantasy 叠上去。只为预览：简单昼夜暗化 + 窗灯，正式光照由 daylight 模块负责。
 */
(function () {
  'use strict';
  var W = 1400, H = 900, $ = function (id) { return document.getElementById(id); };
  var cat = window.TOWN_CATALOG, SAMPLES = window.TOWN_LAYOUT_SAMPLES || [];
  var meta = new Map(cat.meta.map(function (m) { return [m.id, m]; }));
  var U = window.WeatherFX_fantasy.util;
  // ---------------------------------------------------------------- 城镇样例
  var WEST = SAMPLES.findIndex(function (s) { return s.sample === 'town' && s.style === 'west' && s.race === 'common'; });
  var EAST = SAMPLES.findIndex(function (s) { return s.sample === 'town' && s.style === 'east'; });
  SAMPLES.forEach(function (s, i) {
    var o = document.createElement('option'); o.value = i; o.textContent = i + ' ' + s.sample + ' / ' + s.style + ' / ' + s.race; $('sample').appendChild(o);
  });
  $('sample').value = Math.max(0, WEST);
  var scene = null, curSample = -1;
  function buildTown(idx) {
    if (idx === curSample) return; curSample = idx;
    var L = SAMPLES[idx].layout, svg = window.TownRender.render($('town'), L, cat);
    svg.setAttribute('preserveAspectRatio', 'xMidYMid slice');
    var vb = svg.viewBox.baseVal, k = Math.max(W / vb.width, H / vb.height);
    var ox = (W - vb.width * k) / 2 - vb.x * k, oy = (H - vb.height * k) / 2 - vb.y * k, c = L.grid.cell;
    function R(x, y, w, h) { return [ox + x * k, oy + y * k, w * k, h * k]; }
    scene = { width: W, height: H, cell: c * k, water: [], buildings: [], lights: [], ground: [] };
    (L.grid.roads || []).forEach(function (p) { scene.ground.push(R(p[0] * c, p[1] * c, c, c)); });
    (L.grid.water || []).forEach(function (p) { scene.water.push(R(p[0] * c, p[1] * c, c, c)); });
    var hr = window.WeatherNoise.rng(SAMPLES[idx].seed * 31 + idx);
    L.items.forEach(function (it) {
      var m = meta.get(it.id); if (!m || (m.category !== 'house' && m.category !== 'special')) return;
      var top = it.bottom - m.anchor[1], b = R(it.x, top, m.viewBox[2], m.viewBox[3]);
      scene.buildings.push({ x: b[0], y: b[1], w: b[2], h: b[3], roofY: b[1] + 2 * k });
      if (hr() < 0.75) scene.lights.push({ x: b[0] + b[2] * (0.3 + hr() * 0.4), y: oy + (it.bottom - 14) * k, kind: 'window' });
    });
    window.__scene = scene;
    if (layer) layer.setScene(scene);
  }
  // ---------------------------------------------------------------- 叠层
  var fx = $('fx'), dpr = Math.min(2, +(new URLSearchParams(location.search).get('dpr')) || window.devicePixelRatio || 1);
  fx.width = W * dpr; fx.height = H * dpr;
  var ctx = fx.getContext('2d'), layer = window.WeatherFX_fantasy.create({ seed: 2024, noise: window.WeatherNoise });
  layer.resize(W, H, dpr);
  buildTown(+$('sample').value);
  var PASSES = ['ground', 'reflect', 'precip', 'fog', 'light', 'flash'];
  // ---------------------------------------------------------------- 控件
  var ids = ['intensity', 'strength', 'hue', 'pulse', 'hour', 'dir', 'speed', 'gust', 'cover'];
  function val(id) { return +$(id).value; }
  function show() { ids.forEach(function (id) { $(id).nextElementSibling.textContent = $(id).value; }); }
  function link() {
    var k = $('kind').value, it = val('intensity');
    if ($('autoSample').checked) { $('sample').value = k === 'spirit_mist' ? Math.max(0, EAST) : Math.max(0, WEST); buildTown(+$('sample').value); }
    if (!$('link').checked) return;
    $('strength').value = (0.3 + 0.7 * it).toFixed(2);
    $('cover').value = (k === 'ashfall' ? Math.min(1, 0.08 + 0.92 * it) : k === 'mana_storm' ? Math.min(1, it * 1.05) : 0).toFixed(2);
  }
  ids.forEach(function (id) { $(id).addEventListener('input', function () { if (id === 'intensity') link(); show(); }); });
  $('kind').addEventListener('change', function () { link(); show(); });
  $('sample').addEventListener('change', function () { $('autoSample').checked = false; buildTown(+$('sample').value); });
  var paused = false, stepOnce = false;
  $('pause').onclick = function () { paused = !paused; this.textContent = paused ? '继续' : '暂停'; };
  $('step').onclick = function () { stepOnce = true; };
  function state() {
    var k = $('kind').value, g = {};
    if (k === 'mana_storm') g.mana_residue = val('cover'); else if (k === 'ashfall') g.ash_cover = val('cover');
    var I = val('intensity');
    return { seed: 2024, time: { hour: val('hour'), day_of_year: 120, sunrise: 6, sunset: 18.5, moon_phase: 0.5 }, kind: k, intensity: I,
      precipitation: { type: k === 'ashfall' ? 'ash' : 'none', rate: k === 'ashfall' ? I : 0 }, cloud_cover: 0.6 + 0.4 * I,
      fog: k === 'spirit_mist' || k === 'miasma' ? I : 0.1 * I, wind: { dir_deg: val('dir'), speed: val('speed'), gust: val('gust') },
      lightning: 0, temperature_c: 16, humidity: 0.7, visibility: Math.max(0.05, 1 - 0.85 * I),
      magic: { strength: val('strength'), hue: val('hue'), pulse: val('pulse') }, ground: g, season: 'autumn', climate: 'temperate' };
  }
  // 预览用昼夜：夜间叠一层半透明深蓝（fx 画布在城镇 SVG 之上、本身透明，不能用 multiply），窗灯在模块 light 之前补上
  function dayNight(st) {
    var n = U.night(st); if (n <= 0.01) return;
    ctx.globalCompositeOperation = 'source-over';
    ctx.fillStyle = 'rgba(8,12,34,' + (0.66 * n).toFixed(3) + ')';
    ctx.fillRect(0, 0, W, H);
    ctx.globalCompositeOperation = 'lighter';
    var sp = U.glow([255, 190, 110], 14);
    ctx.globalAlpha = 0.5 * n;
    scene.lights.forEach(function (l) { ctx.drawImage(sp, l.x - 14, l.y - 14, 28, 28); });
    ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
  }
  // ---------------------------------------------------------------- 主循环
  var last = performance.now(), fpsLog = [], acc = 0, frames = 0;
  function frame(now) {
    var dt = Math.min(0.1, (now - last) / 1000); last = now;
    acc += dt; frames++;
    if (acc >= 0.5) { var f = frames / acc; fpsLog.push(f); if (fpsLog.length > 60) fpsLog.shift(); $('fps').textContent = f.toFixed(1) + ' fps'; acc = 0; frames = 0; }
    if (!paused || stepOnce) {
      var st = state(), d = stepOnce && paused ? 1 / 60 : dt; stepOnce = false;
      layer.update(st, d);
      ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, fx.width, fx.height); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      PASSES.forEach(function (p) { if (p === 'light') { ctx.save(); dayNight(st); ctx.restore(); } layer.draw(ctx, p); });
    }
    requestAnimationFrame(frame);
  }
  // 供自动化测试
  window.__preview = {
    set: function (o) {
      if (o.kind) $('kind').value = o.kind;
      if (o.intensity != null) $('intensity').value = o.intensity;
      if (o.kind || o.intensity != null) link();
      Object.keys(o).forEach(function (k) { if (k !== 'kind' && k !== 'intensity' && $(k)) $(k).value = o[k]; });
      if (o.sample != null) buildTown(+o.sample);
      show();
    },
    fps: function () { var a = fpsLog.slice(-6); return a.reduce(function (s, x) { return s + x; }, 0) / Math.max(1, a.length); },
    resetFps: function () { fpsLog = []; }
  };
  link(); show();
  requestAnimationFrame(frame);
})();
