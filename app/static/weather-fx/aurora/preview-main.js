/*
 * 极光预览主循环：控件 → 天气状态 → daylight + aurora 的 update / draw；角落显示 fps。
 * pass 顺序：town.ground → daylight ground/reflect → town.objects → daylight light → aurora → (flash)
 * URL 参数（截图用）：?town=port&style=west&strength=0.9&hue=0&cloud=0.1&hour=23&dpr=1&pause=1&daylight=1&t=12
 *   t = 预推进的动画秒数（暂停截图时得到固定画面）
 * 调试接口：window.__aurora = { ready, set(obj), fps(), work(), layer, day }
 */
(function () {
  'use strict';
  var W = 1400, H = 900, $ = function (id) { return document.getElementById(id); };
  var Q = new URLSearchParams(location.search);
  var dpr = Math.min(2, +Q.get('dpr') || window.devicePixelRatio || 1);
  var fx = $('fx'); fx.width = W * dpr; fx.height = H * dpr;
  var ctx = fx.getContext('2d');
  ['strength', 'hue', 'cloud', 'hour'].forEach(function (k) { if (Q.get(k) != null) $(k).value = Q.get(k); });
  if (Q.get('town')) $('town').value = Q.get('town');
  if (Q.get('style')) $('style').value = Q.get('style');
  if (Q.get('daylight') === '0') $('daylight').checked = false;
  var paused = Q.get('pause') === '1';
  function reload() { var u = new URL(location.href); u.searchParams.set('town', $('town').value); u.searchParams.set('style', $('style').value); location.href = u.href; }
  $('town').addEventListener('change', reload); $('style').addEventListener('change', reload);
  function fmt(h) { h = ((h % 24) + 24) % 24; var m = Math.floor(h * 60 + 1e-6); return ('0' + Math.floor(m / 60)).slice(-2) + ':' + ('0' + (m % 60)).slice(-2); }
  function outs() {
    document.querySelectorAll('header input[type=range]').forEach(function (el) {
      var o = el.nextElementSibling; if (o && o.tagName === 'OUTPUT') o.textContent = el.id === 'hour' ? fmt(+el.value) : (+el.value).toFixed(2);
    });
    $('pause').textContent = paused ? '▶ 继续' : '❚❚ 暂停';
  }
  document.querySelectorAll('header input').forEach(function (el) { el.addEventListener('input', outs); });
  $('pause').addEventListener('click', function () { paused = !paused; outs(); });
  outs();

  function state() {
    var cc = +$('cloud').value;
    return {
      seed: 12345, kind: cc > 0.6 ? 'cloudy' : 'clear', intensity: 0.5, cloud_cover: cc, fog: 0,
      time: { hour: +$('hour').value, day_of_year: 20, sunrise: 8.6, sunset: 15.6, moon_phase: 0.1 },
      precipitation: { type: 'none', rate: 0 }, wind: { dir_deg: 100, speed: 0.3, gust: 0.2 }, lightning: 0,
      temperature_c: -14, humidity: 0.5, visibility: 0.9, ground: { wetness: 0, puddles: 0, snow_cover: 0 },
      season: 'winter', climate: 'polar', aurora: { strength: +$('strength').value, hue: +$('hue').value }
    };
  }

  var layer = null, day = null, town = null, fpsLog = [], workLog = [], frames = 0, acc = 0, last = performance.now();
  window.__aurora = {
    ready: false, state: state,
    set: function (o) { Object.keys(o).forEach(function (k) { if (k === 'pause') paused = !!o.pause; else if (k === 'daylight') $('daylight').checked = !!o.daylight; else if ($(k)) $(k).value = o[k]; }); outs(); },
    fps: function () { return fpsLog.slice(); }, work: function () { return workLog.slice(); },
    get layer() { return layer; }, get day() { return day; }
  };
  function onTown(t) {
    town = t || { ground: null, objects: null, scene: null };
    layer = window.WeatherFX_aurora.create({ seed: 12345, noise: window.WeatherNoise });
    layer.resize(W, H, dpr); layer.setScene(town.scene);
    day = window.WeatherFX_daylight.create({ seed: 12345, noise: window.WeatherNoise });
    day.resize(W, H, dpr); day.setScene(town.scene);
    var pre = +Q.get('t') || 0, st = state();   // 预推进动画
    for (var i = 0; i < pre * 20; i++) { layer.update(st, 0.05); day.update(st, 0.05); }
    window.__aurora.ready = true;
    requestAnimationFrame(frame);
  }
  window.AuroraTown.build($('town').value, $('style').value, dpr, onTown);

  function frame(now) {
    var w0 = performance.now();
    var dt = Math.min(0.1, (now - last) / 1000); last = now;
    frames++; acc += dt;
    if (acc >= 0.5) { var f = frames / acc; fpsLog.push(f); if (fpsLog.length > 240) fpsLog.shift(); $('fps').textContent = f.toFixed(1) + ' fps · dpr ' + dpr; frames = 0; acc = 0; }
    var st = state(), ad = paused ? 0 : dt, info;
    layer.update(st, ad); day.update(st, ad);
    info = layer.info();
    $('clock').textContent = fmt(st.time.hour) + ' · 极光 ' + info.s.toFixed(2) + ' · 可见 ' + info.vis.toFixed(2);
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1;
    ctx.fillStyle = '#000'; ctx.fillRect(0, 0, fx.width, fx.height);
    var useDay = $('daylight').checked;
    if (town.ground) ctx.drawImage(town.ground, 0, 0);
    if (useDay) { day.draw(ctx, 'ground'); day.draw(ctx, 'reflect'); }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    if (town.objects) ctx.drawImage(town.objects, 0, 0);
    if (useDay) day.draw(ctx, 'light');
    layer.draw(ctx, 'aurora');
    workLog.push(performance.now() - w0); if (workLog.length > 600) workLog.shift();
    requestAnimationFrame(frame);
  }
})();
