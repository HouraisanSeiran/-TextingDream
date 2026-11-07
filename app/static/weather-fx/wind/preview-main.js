/* 织梦 · 强风预览主循环：WeatherFX_daylight + WeatherFX_rain + WeatherFX_wind 按 3.3 / 8.4 节 pass 顺序合成在同一张 canvas 上
 * 雨层吃 WeatherFX_wind.rainState(state)，昼夜层吃 WeatherFX_wind.daylightState(state)，风层吃原始 state。
 * 调色统一由 daylight 负责，所以 rain 用 tint:false（与总预览 index.js 一致）。
 * 测试钩子：window.__wind = { set(obj), warm(sec), fps(ms) → Promise<{fps,frames}>, stats() } */
(function () {
  'use strict';
  var T = window.WIND_TOWN, W = T.W, H = T.H, N = window.WeatherNoise, SEED = 20261105;
  var $ = function (id) { return document.getElementById(id); };
  var Q = new URLSearchParams(location.search);
  var dpr = Math.min(2, +Q.get('dpr') || window.devicePixelRatio || 1);
  var fx = $('fx'); fx.width = W * dpr; fx.height = H * dpr;
  var ctx = fx.getContext('2d');
  var dl = window.WeatherFX_daylight.create({ seed: SEED, noise: N });
  var rain = window.WeatherFX_rain.create({ seed: SEED + 1, noise: N, tint: false });
  var wind = window.WeatherFX_wind.create({ seed: SEED + 10, noise: N });
  var mods = [dl, rain, wind];
  mods.forEach(function (l) { l.resize(W, H, dpr); });
  var PASSES = ['ground', 'reflect', 'precip', 'fog', 'light', 'flash'];

  T.fillSelect($('townSel'));
  var townImg = null;
  function onScene(sc) { townImg = sc.townImage || null; mods.forEach(function (l) { l.setScene(sc); }); }
  T.load(Q.get('town') || 'port/west/common/1', onScene, dpr);
  $('townSel').addEventListener('change', function () { townImg = null; T.load(this.value, onScene, dpr); });

  // ---------------------------------------------------------------- 控件 → 天气状态
  var ids = ['intensity', 'cat', 'vortex', 'dir', 'speed', 'gust', 'hour'];
  function val(id) { return +$(id).value; }
  function show() { ids.forEach(function (id) { $(id).nextElementSibling.textContent = $(id).value; }); }
  function buildState() {
    var k = $('kind').value, I = val('intensity'), ty = k === 'typhoon', to = k === 'tornado', ph = $('phase').value;
    var sp = val('speed'); if (ty) sp = Math.max(0.7, sp);          // 8.2：台风 wind.speed 至少 0.7
    var wet = ty ? (ph === 'eye' ? 0.85 : 0.6 + 0.4 * I) : to ? 0.5 + 0.4 * I : 0.1;
    return {
      seed: SEED, time: { hour: val('hour'), day_of_year: 230, sunrise: 5.8, sunset: 18.6, moon_phase: 0.4 },
      kind: k, intensity: I,
      precipitation: { type: ty || to ? 'rain' : 'none', rate: ty || to ? I : 0 },
      cloud_cover: ty ? (ph === 'eye' ? 0.35 : 1) : to ? 1 : 0.1, fog: 0,
      wind: { dir_deg: val('dir'), speed: sp, gust: val('gust') },
      lightning: to ? 0.5 + 0.4 * I : ty ? 0.15 : 0, temperature_c: 27, humidity: 0.9,
      visibility: ty ? (ph === 'eyewall' ? 0.15 : ph === 'eye' ? 0.8 : 0.5 - 0.3 * I) : to ? 0.5 : 1,
      ground: { wetness: wet, puddles: wet * 0.6, snow_cover: 0 },
      cyclone: ty ? { category: val('cat'), phase: ph } : null,
      vortex: to ? (val('vortex') > 0 ? val('vortex') : I) : 0,
      season: 'summer', climate: ty ? 'tropical' : 'continental'
    };
  }
  var state = buildState();
  function refresh() { show(); state = buildState(); }
  ids.forEach(function (id) { $(id).addEventListener('input', refresh); });
  ['kind', 'phase'].forEach(function (id) { $(id).addEventListener('change', refresh); });
  ['rainOn', 'dayOn'].forEach(function (id) { $(id).addEventListener('change', refresh); });
  refresh();

  // ---------------------------------------------------------------- 主循环
  var paused = false, stepOnce = false, last = 0, fpsT = 0, fpsN = 0, fpsV = 0, frames = 0;
  function tick(dt) {
    var rs = window.WeatherFX_wind.rainState(state), ds = window.WeatherFX_wind.daylightState(state);
    if (!$('rainOn').checked) { rs = Object.assign({}, rs, { kind: 'clear' }); }
    if (!$('dayOn').checked) { ds = Object.assign({}, ds, { time: { hour: 12, sunrise: 6, sunset: 18 }, kind: 'clear', cloud_cover: 0 }); }
    dl.update(ds, dt); rain.update(rs, dt); wind.update(state, dt);
  }
  function render() {
    // 城镇栅格先画进同一张 canvas：daylight 的 multiply / soft-light 要作用在城镇像素上（透明画布上会变整片乘色）
    reset(); ctx.clearRect(0, 0, fx.width, fx.height);
    if (townImg) ctx.drawImage(townImg, 0, 0, fx.width, fx.height);
    var useDay = $('dayOn').checked;
    for (var i = 0; i < PASSES.length; i++) {
      var ps = PASSES[i];
      if (useDay) { dl.draw(ctx, ps); reset(); }
      rain.draw(ctx, ps); reset(); wind.draw(ctx, ps); reset();
    }
  }
  function reset() { ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1; }
  function loop(now) {
    var dt = last ? (now - last) / 1000 : 0.016; last = now;
    if (!paused || stepOnce) { tick(stepOnce ? 1 / 60 : dt); stepOnce = false; }
    render(); frames++;
    fpsN++; fpsT += dt;
    if (fpsT >= 0.5) {
      fpsV = fpsN / fpsT; fpsN = 0; fpsT = 0;
      var s = wind.stats();
      $('fps').textContent = fpsV.toFixed(0) + ' fps · dpr ' + dpr + '\n碎屑 ' + s.debris + ' 环绕 ' + s.orbit + ' 浪尖 ' + s.crests + ' 阵风 ' + s.gust;
    }
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
  $('pause').addEventListener('click', function () { paused = !paused; this.textContent = paused ? '继续' : '暂停'; });
  $('step').addEventListener('click', function () { stepOnce = true; });

  // ---------------------------------------------------------------- 测试钩子
  window.__wind = {
    set: function (o) {
      Object.keys(o).forEach(function (k) { var el = $(k); if (!el) return; if (el.type === 'checkbox') el.checked = !!o[k]; else el.value = o[k]; });
      refresh();
    },
    warm: function (sec) { for (var t = 0; t < sec; t += 1 / 60) tick(1 / 60); render(); },
    pause: function (v) { paused = v !== false; },
    stats: function () { return { wind: wind.stats(), rain: rain.stats(), fps: fpsV }; },
    /** 每个模块 update + 全部 pass draw 的平均毫秒（n 帧） */
    profile: function (n) {
      n = n || 60; var out = {}, names = ['daylight', 'rain', 'wind'], rs = window.WeatherFX_wind.rainState(state), ds = window.WeatherFX_wind.daylightState(state);
      var sts = [ds, rs, state];
      mods.forEach(function (m, k) {
        var tu = 0, td = 0;
        for (var f = 0; f < n; f++) {
          var t0 = performance.now(); m.update(sts[k], 1 / 60); var t1 = performance.now();
          for (var i = 0; i < PASSES.length; i++) { m.draw(ctx, PASSES[i]); reset(); }
          ctx.getImageData(0, 0, 1, 1); td += performance.now() - t1; tu += t1 - t0;
        }
        out[names[k]] = { update: +(tu / n).toFixed(2), draw: +(td / n).toFixed(2) };
      });
      var pp = {};             // 风层逐 pass
      PASSES.forEach(function (ps) {
        var t0 = performance.now();
        for (var f = 0; f < n; f++) { wind.draw(ctx, ps); reset(); }
        ctx.getImageData(0, 0, 1, 1); pp[ps] = +((performance.now() - t0) / n).toFixed(2);
      });
      out.windPass = pp;
      return out;
    },
    fps: function (ms) {
      return new Promise(function (res) {
        var f0 = frames, t0 = performance.now();
        setTimeout(function () { res({ fps: (frames - f0) * 1000 / (performance.now() - t0), frames: frames - f0 }); }, ms || 3000);
      });
    }
  };
})();
