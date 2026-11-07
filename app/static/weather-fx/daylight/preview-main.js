/*
 * 日光预览主循环：控件 → 天气状态 → layer.update / draw；角落显示 fps 与时钟。
 * URL 参数（截图用）：?hour=19&moon=0.5&kind=clear&cloud=0.15&sunrise=5.9&sunset=18.4&dpr=1&play=1&speed=600
 * 调试接口：window.__daylight = { set(obj), fps(), layer, state() }
 */
(function () {
  'use strict';
  var W = 1400, H = 900, $ = function (id) { return document.getElementById(id); };
  var Q = new URLSearchParams(location.search);
  var dpr = Math.min(2, +Q.get('dpr') || window.devicePixelRatio || 1);
  var fx = $('fx'); fx.width = W * dpr; fx.height = H * dpr;
  var ctx = fx.getContext('2d');
  var ids = { hour: 'hour', sunrise: 'sunrise', sunset: 'sunset', moon: 'moon', cloud: 'cloud', intensity: 'intensity', wind: 'wind', aurS: 'aurS', aurH: 'aurH' };
  Object.keys(ids).forEach(function (k) { if (Q.get(k) != null) $(ids[k]).value = Q.get(k); });
  if (Q.get('kind')) $('kind').value = Q.get('kind');
  if (Q.get('speed')) $('speed').value = Q.get('speed');
  if (Q.get('aurora') === '1') $('aurora').checked = true;
  if (Q.get('town')) $('town').value = Q.get('town');
  $('town').addEventListener('change', function () { var u = new URL(location.href); u.searchParams.set('town', $('town').value); location.href = u.href; });
  var playing = Q.get('play') === '1';

  function fmt(h) { h = ((h % 24) + 24) % 24; var m = Math.floor(h * 60 + 1e-6); return ('0' + Math.floor(m / 60)).slice(-2) + ':' + ('0' + (m % 60)).slice(-2); }
  function outs() {
    document.querySelectorAll('header input[type=range]').forEach(function (el) {
      var o = el.nextElementSibling; if (!o || o.tagName !== 'OUTPUT') return;
      o.textContent = /hour|sunrise|sunset/.test(el.id) ? fmt(+el.value) : (+el.value).toFixed(2);
    });
    $('play').textContent = playing ? '❚❚ 暂停' : '▶ 自动播放';
  }
  document.querySelectorAll('header input,header select').forEach(function (el) { el.addEventListener('input', outs); });
  $('play').addEventListener('click', function () { playing = !playing; outs(); });
  // 天气联动：选降水类天气时云量自动拉高（仍可手动改）
  $('kind').addEventListener('change', function () {
    var k = $('kind').value, c = { clear: 0.1, cloudy: 0.5, overcast: 0.95, fog: 0.7, drizzle: 0.8, rain: 0.9, storm: 1, snow: 0.85, blizzard: 1, sleet: 0.9, sandstorm: 0.6 }[k];
    if (c != null) $('cloud').value = c; outs();
  });
  outs();

  function state() {
    var k = $('kind').value, it = +$('intensity').value;
    var pt = { drizzle: 'rain', rain: 'rain', storm: 'rain', snow: 'snow', blizzard: 'snow', sleet: 'sleet' }[k] || 'none';
    return {
      seed: 12345, kind: k, intensity: it, cloud_cover: +$('cloud').value, fog: k === 'fog' ? 0.6 : 0,
      time: { hour: +$('hour').value, day_of_year: 160, sunrise: +$('sunrise').value, sunset: +$('sunset').value, moon_phase: +$('moon').value },
      precipitation: { type: pt, rate: pt === 'none' ? 0 : it },
      wind: { dir_deg: 100, speed: +$('wind').value, gust: 0.2 }, lightning: 0, temperature_c: /snow|blizzard/.test(k) ? -3 : 16,
      humidity: 0.6, visibility: 0.8, ground: { wetness: 0, puddles: 0, snow_cover: 0 }, season: 'summer', climate: 'temperate',
      aurora: { strength: $('aurora').checked ? +$('aurS').value : 0, hue: +$('aurH').value }
    };
  }

  var layer = null, town = null, fpsLog = [], frames = 0, acc = 0, last = performance.now(), hourF = +$('hour').value;
  window.__daylight = {
    set: function (o) { Object.keys(o).forEach(function (k) { if (k === 'kind') $('kind').value = o.kind; else if (k === 'play') playing = !!o.play; else if (k === 'aurora') $('aurora').checked = !!o.aurora; else if (ids[k]) $(ids[k]).value = o[k]; if (k === 'hour') hourF = +o.hour; }); outs(); },
    fps: function () { return fpsLog.slice(); }, state: state, ready: false, get layer() { return layer; },
    work: function () { return workLog.slice(); }
  };
  function onTown(t) {
    if (!t) { window.DaylightTown.build(dpr, onTown); return; } // 港口样例缺失时退回自拼河镇
    town = t;
    layer = window.WeatherFX_daylight.create({ seed: 12345, noise: window.WeatherNoise });
    layer.resize(W, H, dpr); layer.setScene(t.scene);
    window.__daylight.ready = true;
    requestAnimationFrame(frame);
  }
  if ($('town').value === 'river' || !window.DaylightPort) window.DaylightTown.build(dpr, onTown);
  else window.DaylightPort.build($('town').value, dpr, onTown);

  var workLog = [];
  function frame(now) {
    var w0 = performance.now();
    var dt = Math.min(0.1, (now - last) / 1000); last = now;
    frames++; acc += dt;
    if (acc >= 0.5) { var f = frames / acc; fpsLog.push(f); if (fpsLog.length > 240) fpsLog.shift(); $('fps').textContent = f.toFixed(1) + ' fps · dpr ' + dpr; frames = 0; acc = 0; }
    if (Math.abs(+$('hour').value - hourF) > 0.006) hourF = +$('hour').value; // 用户拖了滑杆
    if (playing) {
      hourF = (((hourF + dt * (+$('speed').value) / 3600) % 24) + 24) % 24; $('hour').value = hourF;
      $('hourOut').textContent = fmt(hourF);
    }
    $('clock').textContent = fmt(hourF) + ' · ' + $('kind').value;
    var st = state(); st.time.hour = hourF;
    layer.update(st, dt);
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1;
    ctx.fillStyle = '#000'; ctx.fillRect(0, 0, fx.width, fx.height);
    if (town.ground) ctx.drawImage(town.ground, 0, 0);
    layer.draw(ctx, 'ground');
    layer.draw(ctx, 'reflect');
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    if (town.objects) ctx.drawImage(town.objects, 0, 0);
    layer.draw(ctx, 'light');
    workLog.push(performance.now() - w0); if (workLog.length > 600) workLog.shift();
    requestAnimationFrame(frame);
  }
})();
