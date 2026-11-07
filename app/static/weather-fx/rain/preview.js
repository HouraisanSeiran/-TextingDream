/* 织梦 · 雨天与风暴预览页：用 TOWN_CATALOG 拼一块西式小城镇做底图，上面叠 WeatherFX_rain 画布 */
(function () {
  'use strict';
  var C = window.TOWN_CATALOG, S = 48, NS = 'http://www.w3.org/2000/svg';
  var M = {}; C.meta.forEach(function (m) { M[m.id] = m; });
  var GW = 30, GH = 19, SEED = 20261105;
  var Q0 = new URLSearchParams(location.search), townArg = Q0.get('town');

  // 默认底图：规范第 6 节——town_layout.py 导出的布局样例 + town-render.js；?town=grid 用旧的手拼小镇
  var SAMPLES = window.TOWN_LAYOUT_SAMPLES;
  if (SAMPLES && window.TownRender && townArg !== 'grid') {
    var idx = townArg != null && townArg !== '' ? +townArg : -1;
    if (!(idx >= 0 && idx < SAMPLES.length)) idx = Math.max(0, SAMPLES.findIndex(function (s) { return s.sample === 'port' && s.style === 'west' && s.race === 'common'; }));
    var smp = SAMPLES[idx], lay = smp.layout, cell = lay.grid.cell;
    var svg = window.TownRender.render(document.getElementById('town'), lay, C);
    var vb = svg.viewBox.baseVal;
    svg.style.width = vb.width + 'px'; svg.style.height = vb.height + 'px';   // 1 布局像素 = 1 CSS 像素
    // 视口：让港口水面落在画面里（水在南侧时整体上移）
    var stH = document.getElementById('stage').clientHeight || 900;
    var wys = (lay.grid.water || []).map(function (c) { return (c[1] + 1) * cell - vb.y; });
    var oy = wys.length ? Math.max(0, Math.min(vb.height - stH, Math.max.apply(null, wys) + cell * 2 - stH)) : 0;
    var ox = 0, tx = -vb.x - ox, ty = -vb.y - oy;
    var town = document.getElementById('town'); town.style.left = -ox + 'px'; town.style.top = -oy + 'px';
    var bld = [];
    lay.items.forEach(function (it) {
      var m = M[it.id]; if (!m || (m.category !== 'house' && m.category !== 'special')) return;
      var top = it.bottom - m.anchor[1];
      bld.push({ x: it.x + tx, y: top + ty, w: m.viewBox[2], h: m.anchor[1], roofY: top + ty,
        eaveY: it.bottom + ty - (m.height_px || 30) * 0.9 });
    });
    var isW = {}; (lay.grid.water || []).forEach(function (c) { isW[c[0] + ',' + c[1]] = 1; });
    var wat = (lay.grid.water || []).map(function (c) {
      var l = isW[(c[0] - 1) + ',' + c[1]] ? 0 : 2, r = isW[(c[0] + 1) + ',' + c[1]] ? 0 : 2;
      return [c[0] * cell + tx + l, c[1] * cell + ty + 2, cell - l - r, cell - 4];
    });
    window.RAIN_PREVIEW_SCENE = { width: Math.round(vb.width - ox), height: Math.round(vb.height - oy), cell: cell, water: wat, buildings: bld,
      lights: bld.map(function (b) { return { x: b.x + b.w / 2, y: b.y + b.h - 14, kind: 'window' }; }),
      ground: [[0, 0, Math.round(vb.width), Math.round(vb.height)]] };
    window.RAIN_PREVIEW_SAMPLE = { index: idx, label: smp.sample + ' · ' + smp.style + ' · ' + smp.race + ' · seed ' + smp.seed };
    window.__rainPreviewTownReady = true;
    return;
  }

  // 雪碧图只插一次：0×0 绝对定位（display:none 会让 clipPath 失效）
  var holder = document.createElement('div');
  holder.innerHTML = '<svg xmlns="' + NS + '" width="0" height="0" style="position:absolute;width:0;height:0;overflow:hidden">' + C.sprite + '</svg>';
  document.body.insertBefore(holder.firstChild, document.body.firstChild);

  function bin(m) { return ('000' + m.toString(2)).slice(-4); }
  function use(id, x, bottom) {
    var m = M[id]; if (!m) return '';
    return '<use href="#' + id + '" x="' + x.toFixed(1) + '" y="' + (bottom - m.viewBox[3]).toFixed(1) + '" width="' + m.viewBox[2] + '" height="' + m.viewBox[3] + '"/>';
  }
  var R = WeatherNoise.rng(SEED);

  // 逻辑格：'=' 路，'~' 水，'.' 草地
  var g = [], occ = [], RX = 12, RY = 9;
  for (var y = 0; y < GH; y++) { g.push([]); occ.push([]); for (var x = 0; x < GW; x++) {
    var dx = (x - 22.5) / 4.6, dy = (y - 14) / 2.9, water = dx * dx + dy * dy < 1;
    var road = (x === RX && y < GH) || (y === RY && x < GW);
    g[y].push(water ? '~' : road ? '=' : '.'); occ[y].push(water || road);
  } }
  function dual(fn, prefix) {
    var out = [];
    for (var j = 0; j <= GH; j++) for (var i = 0; i <= GW; i++) {
      var at = function (xx, yy) { return xx >= 0 && yy >= 0 && xx < GW && yy < GH && fn(g[yy][xx]) ? 1 : 0; };
      var m = at(i - 1, j - 1) * 8 + at(i, j - 1) * 4 + at(i - 1, j) * 2 + at(i, j);
      if (m) out.push({ id: prefix + bin(m), x: i * S - S / 2, bottom: j * S + S / 2 });
    }
    return out;
  }
  // 草地是可平铺的单格底纹（grass-01..04），不是双网格
  var ground = [];
  for (y = 0; y < GH; y++) for (x = 0; x < GW; x++) ground.push({ id: 'west-common-ground-grass-0' + (1 + Math.floor(R() * 4)), x: x * S, bottom: (y + 1) * S });
  ground = ground.concat(dual(function (c) { return c === '='; }, 'west-common-road-stone-'))
    .concat(dual(function (c) { return c === '~'; }, 'west-common-water-bank-'));

  // 民居：贴路优先，占地须空闲且离水一格
  var houses = C.meta.filter(function (m) { return m.dir === 'west-base' && m.category === 'house'; }).map(function (m) { return m.id; });
  var props = ['west-common-prop-tree-oak-01', 'west-common-prop-tree-oak-02', 'west-common-prop-tree-pine-01', 'west-common-prop-bush-01',
    'west-common-prop-bush-02', 'west-common-prop-barrel-stack-01', 'west-common-prop-crate-01', 'west-common-prop-hay-bale-01'].filter(function (id) { return M[id]; });
  var items = [], buildings = [];
  function fits(x, y, w, d) {
    if (x < 0 || y < 1 || x + w > GW || y + d > GH) return false;
    for (var yy = y - 1; yy <= y + d; yy++) for (var xx = x; xx < x + w; xx++) {
      if (yy >= y && yy < y + d && occ[yy][xx]) return false;
      if (yy >= 0 && yy < GH && g[yy][xx] === '~') return false;
    }
    return true;
  }
  function nearRoad(x, y, w, d) {
    for (var xx = x; xx < x + w; xx++) if (g[y + d] && g[y + d][xx] === '=') return true;
    for (var yy = y; yy < y + d; yy++) if (g[yy][x - 1] === '=' || g[yy][x + w] === '=') return true;
    return false;
  }
  function place(id, needRoad, isHouse) {
    var m = M[id], w = m.footprint[0], d = m.footprint[1], spots = [];
    for (var y = 1; y < GH; y++) for (var x = 0; x < GW; x++) if (fits(x, y, w, d) && (!needRoad || nearRoad(x, y, w, d))) spots.push([x, y]);
    if (!spots.length) return false;
    var p = spots[Math.floor(R() * spots.length)];
    for (var yy = p[1]; yy < p[1] + d; yy++) for (var xx = p[0]; xx < p[0] + w; xx++) occ[yy][xx] = true;
    var bx = p[0] * S, bottom = (p[1] + d) * S, H = m.viewBox[3];
    items.push({ id: id, x: bx, bottom: bottom });
    if (isHouse) buildings.push({ x: bx, y: bottom - H, w: m.viewBox[2], h: H, roofY: bottom - H, eaveY: bottom - (m.height_px || 30) * 0.9 });
    return true;
  }
  for (var n = 0; n < 26; n++) place(houses[Math.floor(R() * houses.length)], true, true);
  for (n = 0; n < 8; n++) place(houses[Math.floor(R() * houses.length)], false, true);
  for (n = 0; n < 16 && props.length; n++) place(props[Math.floor(R() * props.length)], false, false);
  items.sort(function (a, b) { return a.bottom - b.bottom || a.x - b.x; });
  var TW = GW * S, TH = GH * S;
  document.getElementById('town').innerHTML = '<svg xmlns="' + NS + '" width="' + TW + '" height="' + TH + '" viewBox="0 0 ' + TW + ' ' + TH + '">' +
    ground.map(function (it) { return use(it.id, it.x, it.bottom); }).join('') + items.map(function (it) { return use(it.id, it.x, it.bottom); }).join('') + '</svg>';

  // 场景描述（CSS 像素，与 SVG 1:1）
  var water = [];
  // 双网格水岸会把外侧半格画成岸：临岸一侧内缩，避免涟漪 / 水面效果露出方角
  function isW(xx, yy) { return xx >= 0 && yy >= 0 && xx < GW && yy < GH && g[yy][xx] === '~'; }
  for (y = 0; y < GH; y++) for (x = 0; x < GW; x++) if (g[y][x] === '~') {
    var l = isW(x - 1, y) ? 0 : 18, r = isW(x + 1, y) ? 0 : 18, t = isW(x, y - 1) ? 0 : 18, b = isW(x, y + 1) ? 0 : 18;
    water.push([x * S + l, y * S + t, S - l - r, S - t - b]);
  }
  var scene = { width: TW, height: TH, cell: S, water: water, buildings: buildings,
    lights: buildings.map(function (b) { return { x: b.x + b.w / 2, y: b.y + b.h - 14, kind: 'window' }; }),
    ground: [[0, 0, TW, TH]] };
  window.RAIN_PREVIEW_SCENE = scene;
  window.__rainPreviewTownReady = true;
})();

/* 驱动：控件 → 天气状态 → layer.update / draw；URL 参数 ?kind=rain&i=0.5&dir=110&speed=0.3&lightning=0.5&wet=0.7&puddles=0.4&hour=13&dpr=2&paused=1 */
(function () {
  'use strict';
  var scene = window.RAIN_PREVIEW_SCENE, cv = document.getElementById('fx'), ctx = cv.getContext('2d');
  var Q = new URLSearchParams(location.search);
  var dpr = +Q.get('dpr') || window.devicePixelRatio || 1;
  var layer = WeatherFX_rain.create({ seed: 20261105, noise: window.WeatherNoise });
  var ids = ['kind', 'ptype', 'intensity', 'dir', 'speed', 'gust', 'lightning', 'wetness', 'puddles', 'hail_cover', 'hour'];
  var alias = { i: 'intensity', wet: 'wetness', hail: 'hail_cover' };
  // 城镇样例下拉：切换时带着当前 URL 参数重载
  (function () {
    var sel = document.getElementById('townSel'), S0 = window.TOWN_LAYOUT_SAMPLES || [], cur = window.RAIN_PREVIEW_SAMPLE;
    S0.forEach(function (s, i) { var o = document.createElement('option'); o.value = i; o.textContent = i + ' ' + s.sample + ' · ' + s.style + ' · ' + s.race + ' · ' + s.seed; sel.appendChild(o); });
    var g = document.createElement('option'); g.value = 'grid'; g.textContent = '手拼小镇（旧）'; sel.appendChild(g);
    sel.value = cur ? String(cur.index) : 'grid';
    sel.onchange = function () { var u = new URLSearchParams(location.search); u.set('town', sel.value); location.search = u.toString(); };
  })();
  Q.forEach(function (v, k) { var id = alias[k] || k; var el = document.getElementById(id); if (el && ids.indexOf(id) >= 0) el.value = v; });
  if (Q.get('wet') || Q.get('wetness') || Q.get('puddles') || Q.get('hail')) document.getElementById('auto').checked = false;
  if (Q.get('auto') === '0') document.getElementById('auto').checked = false;
  function el(id) { return document.getElementById(id); }
  function num(id) { return +el(id).value; }

  // 自动湿度：只给预览用的粗略默认值（真实 ground 由生成系统按前几小时累积给出）
  function autoGround() {
    if (!el('auto').checked) return;
    var k = el('kind').value, I = num('intensity');
    var e = k === 'drizzle' ? 0.1 + 0.2 * I : k === 'clear' ? 0 : k === 'sleet' ? 0.7 * I : k === 'hail' ? 0.35 * I : I;
    var hailOn = k === 'hail' || (k === 'storm' && el('ptype').value === 'hail');
    el('hail_cover').value = (hailOn ? Math.min(1, 0.04 + 0.55 * I) : 0).toFixed(2);
    el('wetness').value = (k === 'clear' ? 0 : Math.min(1, 0.2 + 0.85 * e)).toFixed(2);
    el('puddles').value = (k === 'clear' || k === 'drizzle' ? 0 : Math.min(1, Math.max(0, (e - 0.2) * 1.2))).toFixed(2);
  }
  function syncOut() { ids.forEach(function (id) { var o = el(id).parentNode.querySelector('output'); if (o) o.textContent = el(id).value; }); }
  ids.forEach(function (id) { el(id).addEventListener('input', function () { if (id === 'kind' || id === 'intensity' || id === 'ptype') autoGround(); syncOut(); }); });
  el('auto').addEventListener('change', function () { autoGround(); syncOut(); });
  if (el('auto').checked) autoGround();
  syncOut();

  function state() {
    var k = el('kind').value, I = num('intensity');
    return { seed: 20261105, time: { hour: num('hour'), day_of_year: 120, sunrise: 6, sunset: 18.4, moon_phase: 0.4 },
      kind: k, intensity: I, precipitation: { type: k === 'clear' ? 'none' : (k === 'hail' || (k === 'storm' && el('ptype').value === 'hail')) ? 'hail' : 'rain', rate: I },
      cloud_cover: k === 'clear' ? 0.1 : k === 'drizzle' ? 0.8 : 0.9 + 0.1 * I, fog: 0,
      wind: { dir_deg: num('dir'), speed: num('speed'), gust: num('gust') },
      lightning: k === 'storm' ? num('lightning') : 0, temperature_c: k === 'sleet' ? 1 : 14, humidity: 0.9,
      visibility: Math.max(0.2, 1 - 0.7 * I * (k === 'drizzle' ? 0.3 : 1)),
      ground: { wetness: num('wetness'), puddles: num('puddles'), snow_cover: 0, hail_cover: num('hail_cover') }, season: 'spring', climate: 'temperate' };
  }

  var W = 0, H = 0;
  function fit() {
    var st = document.getElementById('stage');
    W = Math.min(st.clientWidth, scene.width); H = Math.min(st.clientHeight, scene.height);
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); cv.style.width = W + 'px'; cv.style.height = H + 'px';
    layer.resize(W, H, dpr); layer.setScene(scene);
  }
  window.addEventListener('resize', fit);
  fit();

  var paused = Q.get('paused') === '1', stepOnce = false, last = performance.now(), frames = [], fpsAcc = { n: 0, t: 0 };
  el('pause').textContent = paused ? '继续' : '暂停';
  el('pause').onclick = function () { paused = !paused; this.textContent = paused ? '继续' : '暂停'; };
  el('step').onclick = function () { paused = true; el('pause').textContent = '继续'; stepOnce = true; };
  el('strike').onclick = function () { layer.triggerLightning(); if (paused) stepOnce = true; };

  var PASSES = ['ground', 'reflect', 'precip', 'fog', 'flash'];
  function render(dt) {
    layer.update(state(), dt);
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, cv.width, cv.height);
    for (var i = 0; i < PASSES.length; i++) layer.draw(ctx, PASSES[i]);
  }
  function loop(now) {
    var dt = Math.min(0.05, (now - last) / 1000); last = now;
    if (!paused || stepOnce) { render(stepOnce && paused ? 1 / 60 : dt); stepOnce = false; }
    frames.push(now); while (frames.length && now - frames[0] > 1000) frames.shift();
    fpsAcc.n++; fpsAcc.t += dt;
    if (fpsAcc.n % 15 === 0) {
      el('fps').textContent = 'fps ' + frames.length + ' · dpr ' + dpr + ' · ' + W + '×' + H;
      var s = layer.stats(); el('stats').textContent = '雨丝 ' + s.drops + ' · 溅点 ' + s.sparks + ' · 涟漪 ' + s.rings + ' · 檐滴 ' + s.drips;
    }
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);

  // 测试钩子：设参数、推进 n 帧、打闪电、量 fps
  window.rainPreview = {
    layer: layer,
    set: function (o) { Object.keys(o).forEach(function (k) { var id = alias[k] || k; if (el(id)) { if (el(id).type === 'checkbox') el(id).checked = !!o[k]; else el(id).value = o[k]; } }); autoGround(); syncOut(); },
    advance: function (n, dt) { for (var i = 0; i < (n || 1); i++) render(dt || 1 / 60); },
    strike: function () { layer.triggerLightning(); },
    pause: function (v) { paused = v !== false; el('pause').textContent = paused ? '继续' : '暂停'; },
    fps: function () { return frames.length; }
  };
})();
