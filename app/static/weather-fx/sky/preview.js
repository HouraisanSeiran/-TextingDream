/*
 * 天色天气预览：城镇底图（SkyTown）+ WeatherFX_daylight 调色 + WeatherFX_sky。
 * 每帧：地面栅格 → daylight.reflect → 实物栅格 → 按 ground → reflect → precip → fog → light → bow → aurora → flash
 *       依次发给 daylight 与 sky（daylight 只认 reflect / light）。
 * daylight 读「代理状态」：第 8 节新 kind 换成它认识的基础天气（霾/浮尘/扬沙/热浪 → clear，太阳雨 → cloudy），
 *       调色交给 sky 自己做，避免双重压暗。
 * 调试接口 window.__sky：set(o) / state() / fps() / ready / layer。
 */
(function () {
  'use strict';
  var W = 1400, H = 900, $ = function (id) { return document.getElementById(id); };
  var Q = new URLSearchParams(location.search), N = window.WeatherNoise;
  var dpr = Math.max(1, Math.min(2, +Q.get('dpr') || window.devicePixelRatio || 1));
  var SAMPLES = window.TOWN_LAYOUT_SAMPLES || [];
  SAMPLES.forEach(function (s, i) {
    var o = document.createElement('option'); o.value = i; o.textContent = window.SkyTown.label(s); $('townSel').appendChild(o);
  });
  function findIdx(key) {
    for (var i = 0; i < SAMPLES.length; i++) if (window.SkyTown.label(SAMPLES[i]) === key) return i;
    return 0;
  }
  // 预览默认样例：样例里没有阿拉伯风格，干旱类天气用西式城镇
  var DEFAULT_TOWN = { haze: 'city/west/common/1', dust: 'town/west/common/7', blowing_sand: 'town/west/common/7',
    heatwave: 'town/west/common/1', sunshower: 'port/west/common/1', rain: 'village/west/common/7' };

  var fx = $('fx'); fx.width = W * dpr; fx.height = H * dpr;
  var ctx = fx.getContext('2d');
  var dl = window.WeatherFX_daylight.create({ seed: 20261105, noise: N });
  var sky = window.WeatherFX_sky.create({ seed: 20261111, noise: N });
  dl.resize(W, H, dpr); sky.resize(W, H, dpr);
  var PASSES = ['ground', 'reflect', 'precip', 'fog', 'light', 'bow', 'aurora', 'flash'];

  var town = null, building = false, pendingIdx = -1;
  function loadTown(idx) {
    if (building) { pendingIdx = idx; return; }
    building = true; $('loading').style.display = 'block'; $('townSel').value = idx;
    if (window.__sky) window.__sky.ready = false;
    window.SkyTown.build($('host'), idx, dpr, function (t) {
      building = false; $('loading').style.display = 'none';
      if (t) {
        town = t; dl.setScene(t.scene); sky.setScene(t.scene); window.__scene = t.scene;
        $('stage').style.background = t.scene && SAMPLES[idx].style === 'east' ? '#ced6aa' : '#bfcba9';
      }
      if (pendingIdx >= 0) { var p = pendingIdx; pendingIdx = -1; loadTown(p); return; }
      if (window.__sky) window.__sky.ready = !!(t && t.ok);
    });
  }
  $('townSel').addEventListener('change', function () { loadTown(+this.value); });

  // ---------------------------------------------------------------- 控件
  var IDS = ['intensity', 'aeroDen', 'heat', 'rainbow', 'cover', 'cloud', 'dir', 'speed', 'gust', 'hour'];
  function val(id) { return +$(id).value; }
  function show() { IDS.forEach(function (id) { $(id).nextElementSibling.textContent = $(id).value; }); }
  function setv(id, v) { $(id).value = typeof v === 'number' ? +v.toFixed(2) : v; }
  /** 联动：切天气 / 拖强度时给出与之自洽的气溶胶、heat、rainbow、积灰、风、时刻（只为预览方便，模块本身只读 state） */
  function link() {
    if (!$('link').checked) return;
    var k = $('kind').value, it = val('intensity');
    var o = { aeroType: 'none', aeroDen: 0, heat: 0, rainbow: 0, cover: 0, cloud: 0.15, speed: 0.25 };
    if (k === 'haze') { o.aeroType = 'haze'; o.aeroDen = it; o.cloud = 0.08; o.speed = 0.05; }
    else if (k === 'dust') { o.aeroType = 'dust'; o.aeroDen = it; o.cover = 0.12 + 0.6 * it; o.speed = 0.3 + 0.15 * it; o.cloud = 0.1; }
    else if (k === 'blowing_sand') { o.aeroType = 'sand'; o.aeroDen = it; o.cover = 0.1 + 0.5 * it; o.speed = 0.5 + 0.35 * it; o.cloud = 0.1; }
    else if (k === 'heatwave') { o.heat = it; o.cloud = 0.05; o.speed = 0.08; }
    else if (k === 'sunshower') { o.rainbow = it; o.cloud = 0.2; o.speed = 0.2; o.hour = 17; }
    else if (k === 'rain') { o.rainbow = it; o.cloud = 0.3; o.hour = 8; }
    Object.keys(o).forEach(function (id) { setv(id, o[id]); });
  }
  $('kind').addEventListener('change', function () { link(); show(); });
  $('intensity').addEventListener('input', function () { link(); show(); });
  IDS.forEach(function (id) { $(id).addEventListener('input', show); });
  var TIME = { day_of_year: 172, sunrise: 5.8, sunset: 18.8, moon_phase: 0.3 };
  function state() {
    var k = $('kind').value, it = val('intensity');
    return { seed: 1234, kind: k, intensity: it,
      time: { hour: val('hour'), day_of_year: TIME.day_of_year, sunrise: TIME.sunrise, sunset: TIME.sunset, moon_phase: TIME.moon_phase },
      precipitation: { type: k === 'sunshower' ? 'rain' : 'none', rate: k === 'sunshower' ? it : 0 },
      cloud_cover: val('cloud'), fog: 0, wind: { dir_deg: val('dir'), speed: val('speed'), gust: val('gust') },
      lightning: 0, temperature_c: k === 'heatwave' ? 41 : k === 'haze' ? 6 : 28, humidity: k === 'haze' ? 0.6 : 0.3,
      visibility: 1 - 0.85 * val('aeroDen') * ($('aeroType').value === 'none' ? 0 : 1),
      aerosol: { type: $('aeroType').value, density: val('aeroDen') }, rainbow: val('rainbow'), heat: val('heat'),
      ground: { wetness: k === 'sunshower' ? 0.3 : k === 'rain' ? 0.6 : 0, puddles: 0, snow_cover: 0, dust_cover: val('cover') },
      season: 'summer', climate: 'arid' };
  }
  /** daylight 不认识第 8 节新 kind：换成基础天气，调色只用它的时刻光照（气溶胶色调由 sky 负责） */
  function proxy(st) {
    var p = Object.assign({}, st), k = st.kind;
    if (k === 'haze' || k === 'dust' || k === 'blowing_sand' || k === 'heatwave' || k === 'sunshower') p.kind = 'clear';
    else if (k === 'rain') { p.kind = 'cloudy'; }       // 预览里的 rain = 雨刚停，配彩虹
    // 气溶胶让阳光漫射：给 daylight 抬高云量，让建筑投影随密度变淡（daylight 的投影画在 light pass，盖在霾幕之上）
    var ad = st.aerosol && st.aerosol.type !== 'none' ? +st.aerosol.density || 0 : 0;
    if (ad > 0) p.cloud_cover = Math.max(p.cloud_cover || 0, Math.min(0.9, ad * 0.95));
    return p;
  }
  var paused = false, stepOnce = false;
  $('pause').onclick = function () { paused = !paused; this.textContent = paused ? '继续' : '暂停'; };
  $('step').onclick = function () { paused = true; $('pause').textContent = '继续'; stepOnce = true; };

  // ---------------------------------------------------------------- 循环 + fps
  var last = performance.now(), frames = 0, acc = 0, fpsLog = [], workLog = [];
  function reset() { ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1; ctx.filter = 'none'; }
  function frame(now) {
    var dt = Math.min(0.1, (now - last) / 1000); last = now;
    frames++; acc += dt;
    if (acc >= 0.5) { var f = frames / acc; fpsLog.push(f); if (fpsLog.length > 240) fpsLog.shift(); $('fps').textContent = f.toFixed(1) + ' fps · dpr ' + dpr; frames = 0; acc = 0; }
    if (town && (!paused || stepOnce)) {
      var w0 = performance.now(), st = state(), d = stepOnce ? 1 / 60 : dt, useDl = $('useDl').checked; stepOnce = false;
      if (useDl) dl.update(proxy(st), d);
      sky.update(st, d);
      reset(); ctx.fillStyle = '#000'; ctx.fillRect(0, 0, fx.width, fx.height);
      ctx.drawImage(town.ground, 0, 0);
      if (useDl) { dl.draw(ctx, 'reflect'); reset(); }
      if (town.objects) ctx.drawImage(town.objects, 0, 0);
      PASSES.forEach(function (p) {
        if (useDl && p !== 'reflect') { dl.draw(ctx, p); reset(); }
        sky.draw(ctx, p); reset();
      });
      workLog.push(performance.now() - w0); if (workLog.length > 240) workLog.shift();
    }
    requestAnimationFrame(frame);
  }
  // ---------------------------------------------------------------- 调试接口（自动化截图用）
  window.__sky = {
    ready: false, layer: sky, daylight: dl, state: state,
    fps: function () { return fpsLog.slice(); }, work: function () { return workLog.slice(); },
    resetFps: function () { fpsLog.length = 0; workLog.length = 0; },
    /** o：{ town:'city/west/common/1', kind, intensity, aeroType, aeroDen, heat, rainbow, cover, cloud, dir, speed, gust, hour, link } */
    set: function (o) {
      if (o.link != null) $('link').checked = !!o.link;
      if (o.kind) $('kind').value = o.kind;
      if (o.intensity != null) setv('intensity', o.intensity);
      if (o.kind || o.intensity != null) link();
      Object.keys(o).forEach(function (k) {
        if (k === 'kind' || k === 'intensity' || k === 'town' || k === 'link' || !$(k)) return;
        setv(k, o[k]);
      });
      show();
      if (o.town) loadTown(findIdx(o.town));
    }
  };
  var k0 = Q.get('kind') || 'haze';
  $('kind').value = k0; if (Q.get('intensity')) setv('intensity', +Q.get('intensity'));
  link(); show();
  loadTown(findIdx(Q.get('town') || DEFAULT_TOWN[k0] || 'town/west/common/1'));
  requestAnimationFrame(frame);
})();
