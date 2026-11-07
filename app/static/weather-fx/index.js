/*
 * 织梦 · 天气系统总预览（docs/weather-spec.md 第 6、7 节）。尚未接入游戏，只供检查效果。
 * 底图：layout-samples.js + town-render.js，裁出 1400×900 窗口，分「地面+水」「建筑/城墙/摆件」两张栅格；
 *       另把建筑、城墙、树的 symbol 栅格化成 scene.occluder（雪模块用）。
 * 每帧：地面栅格 → daylight.reflect（倒影须在岸上实物之下）→ 实物栅格 →
 *       其余 pass 按第 8 节顺序 ground → reflect → precip → fog → light → bow → aurora → flash 依次 draw。
 *       六个已有模块只收原六个 pass；可选叠层 aurora / ice / wind / sky 存在时才加载，收全部 pass。
 * 调试接口 window.__wx：set / preset / mode / play / speed / state / fps / ready / strike。
 */
(function () {
  'use strict';
  var W = 1400, H = 900, NS = 'http://www.w3.org/2000/svg';
  var $ = function (id) { return document.getElementById(id); };
  var Q = new URLSearchParams(location.search);
  var dpr = Math.max(1, Math.min(2, +Q.get('dpr') || window.devicePixelRatio || 1));
  var cat = window.TOWN_CATALOG, META = {}, SAMPLES = window.TOWN_LAYOUT_SAMPLES || [];
  cat.meta.forEach(function (m) { META[m.id] = m; });
  var BLD = { house: 1, special: 1, castle: 1, landmark: 1, fort: 1, site: 1 };

  // ---------------------------------------------------------------- 城镇栅格化
  function symbolText(id) {
    var s = cat.sprite, i = s.indexOf('<symbol id="' + id + '"');
    return i < 0 ? '' : s.slice(i, s.indexOf('</symbol>', i) + 9);
  }
  /** 把 svg 文本里 href="#id" 引用的 symbol（含 symbol 内部再引用的）拼成 <defs> 插进去 */
  function withDefs(txt) {
    var used = {}, queue = [], defs = '';
    function scan(t) { t.replace(/href="#([^"]+)"/g, function (_, id) { if (!used[id]) { used[id] = 1; queue.push(id); } }); }
    scan(txt);
    while (queue.length) { var d = symbolText(queue.shift()); if (d) { defs += d; scan(d); } }
    return txt.replace(/^<svg[^>]*>/, function (m) { return m + '<defs>' + defs + '</defs>'; });
  }
  function svgText(layout, win, strip) {
    var svg = window.TownRender.render($('host'), layout, cat);
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
  /** 路灯杆（白天看得到实物，夜里由 daylight 点亮）；坐标 CSS 像素，y = 地面 */
  function drawLampPosts(c, k, lamps) {
    var g = c.getContext('2d'); g.setTransform(k, 0, 0, k, 0, 0);
    lamps.forEach(function (l) {
      var x = l[0], y = l[1];
      g.fillStyle = 'rgba(58,44,30,0.22)'; g.beginPath(); g.ellipse(x + 3, y, 6, 2, 0, 0, Math.PI * 2); g.fill();
      g.fillStyle = '#3a3330'; g.fillRect(x - 1.3, y - 38, 2.6, 38); g.fillRect(x - 3, y - 3, 6, 3);
      g.fillStyle = '#4a3f36'; g.fillRect(x - 1, y - 38, 8, 1.6);
      g.fillStyle = '#d9c48a'; g.fillRect(x + 4.2, y - 35, 4.6, 6.5);
      g.strokeStyle = '#2e2724'; g.lineWidth = 1; g.strokeRect(x + 4.2, y - 35, 4.6, 6.5);
    });
    g.setTransform(1, 0, 0, 1, 0, 0);
  }

  /** 从布局算窗口与 scene，异步栅格化，done({ground, objects, scene, label}) */
  function buildTown(idx, done) {
    var smp = SAMPLES[idx], L = smp.layout, g = L.grid, C = g.cell;
    var vb0 = window.TownRender.render($('host'), L, cat).viewBox.baseVal;
    var vbx = vb0.x, vby = vb0.y, vbw = vb0.width, vbh = vb0.height;
    var s = Math.max(1, W / vbw, H / vbh), ww = W / s, wh = H / s;   // 小镇放大铺满，大城按 1:1 裁窗
    var vx = vbx + (vbw - ww) / 2, vy = vby + (vbh - wh) / 2;
    if ((g.water || []).length) {                                     // 有水面：让水落在画面下部
      var wy = g.water.reduce(function (a, p) { return Math.max(a, p[1]); }, 0);
      vy = Math.max(vby, Math.min(vby + vbh - wh, (wy + 0.5) * C - wh * 0.62));
    }
    var win = [vx, vy, ww, wh];
    function R(x, y, w, h) { return [(x - vx) * s, (y - vy) * s, w * s, h * s]; }
    var scene = { width: W, height: H, cell: C * s, water: [], buildings: [], lights: [], ground: [] };
    (g.roads || []).forEach(function (p) { scene.ground.push(R(p[0] * C, p[1] * C, C, C)); });
    (g.water || []).forEach(function (p) { scene.water.push(R(p[0] * C, p[1] * C, C, C)); });
    var rng = window.WeatherNoise.rng((smp.seed | 0) * 31 + idx * 7 + 3), walls = [], occItems = [];
    L.items.forEach(function (it) {
      var m = META[it.id]; if (!m) return;
      var top = it.bottom - m.anchor[1], b = R(it.x, top, m.viewBox[2], m.viewBox[3]), hp = m.height_px || 40;
      if (BLD[m.category] || m.category === 'wall' || /tree|bush/.test(it.id)) occItems.push(it);
      if (b[0] + b[2] < -80 || b[0] > W + 80 || b[1] > H + 40 || b[1] + b[3] < -40) return;
      var bottom = (it.bottom - vy) * s;
      if (m.category === 'wall') { walls.push({ x: b[0], y: b[1], w: b[2], h: b[3], roofY: b[1], depth: Math.max(10, m.viewBox[3] - hp) * s, wall: true }); return; }
      if (/campfire|brazier|torch/.test(it.id)) { scene.lights.push({ x: b[0] + b[2] / 2, y: bottom - 14 * s, kind: 'fire' }); return; }
      if (!BLD[m.category]) return;
      scene.buildings.push({ x: b[0], y: b[1], w: b[2], h: b[3], roofY: b[1] + 2 * s,
        eaveY: bottom - hp * 0.9 * s, depth: Math.max(10, m.viewBox[3] - hp) * s });
      if ((m.category !== 'house' && m.category !== 'special') || /dock|bridge|well|carry-pole/.test(it.id)) return;
      var n = Math.max(1, Math.round(b[2] / (m.category === 'special' ? 34 : 44)) + (rng() < 0.3 ? 1 : 0));
      for (var i = 0; i < n; i++) scene.lights.push({ x: b[0] + b[2] * (i + 0.5 + (rng() - 0.5) * 0.25) / n, y: bottom - Math.min(26, hp * 0.42) * s - 4, kind: 'window' });
      if (hp > 50 && rng() < 0.6) scene.lights.push({ x: b[0] + b[2] * (0.3 + rng() * 0.4), y: bottom - hp * 0.78 * s, kind: 'window' });
    });
    // 被城墙挡住的窗灯去掉
    scene.lights = scene.lights.filter(function (l) {
      return !walls.some(function (b) { return l.x >= b.x && l.x <= b.x + b.w && l.y >= b.y + 4 && l.y <= b.y + b.h; });
    });
    // 路灯：道路格按哈希稀疏放置；城门两侧火把
    var lamps = [];
    (g.roads || []).forEach(function (p) {
      if (window.WeatherNoise.hash32(p[0] * 73856093 ^ p[1] * 19349663) % 9 !== 0) return;
      var q = R(p[0] * C + C * 0.3, p[1] * C + C * 0.85, 0, 0);
      if (q[0] < -20 || q[0] > W + 20 || q[1] < 0 || q[1] > H + 40) return;
      lamps.push([q[0], q[1]]); scene.lights.push({ x: q[0] + 6, y: q[1] - 32, kind: 'lamp' });
    });
    (L.infrastructure || []).forEach(function (f) {
      if (f.facility !== 'gate') return;
      var a = R(f.cell[0] * C + 6, f.cell[1] * C + 8, 0, 0), b = R((f.cell[0] + 1) * C - 6, f.cell[1] * C + 8, 0, 0);
      scene.lights.push({ x: a[0], y: a[1], kind: 'fire' }, { x: b[0], y: b[1], kind: 'fire' });
    });
    scene.buildingsWithWalls = scene.buildings.concat(walls);
    var gText = svgText(Object.assign({}, L, { items: [] }), win, false);
    var oText = svgText(Object.assign({}, L, { ground: [], grid: Object.assign({}, g, { water: [] }) }), win, true);
    var cText = svgText(Object.assign({}, L, { ground: [], items: occItems, grid: Object.assign({}, g, { water: [] }) }), win, true);
    $('host').replaceChildren();
    var base = L.style === 'east' ? '#ced6aa' : '#bfcba9';
    raster(gText, dpr, function (gc) {
      raster(oText, dpr, function (oc) {
        raster(cText, 1, function (cc) {
          var bg = document.createElement('canvas'); bg.width = W * dpr; bg.height = H * dpr;
          var bx = bg.getContext('2d'); bx.fillStyle = base; bx.fillRect(0, 0, bg.width, bg.height);
          if (gc) bx.drawImage(gc, 0, 0);
          var ob = document.createElement('canvas'); ob.width = W * dpr; ob.height = H * dpr;
          drawLampPosts(ob, dpr, lamps);
          if (oc) ob.getContext('2d').drawImage(oc, 0, 0);
          scene.objectsImage = ob; scene.objectsScale = dpr; if (cc) scene.occluder = cc;
          done({ ground: bg, objects: ob, scene: scene, label: smp.sample + '/' + smp.style + '/' + smp.race + '/' + smp.seed, ok: !!(gc && oc) });
        });
      });
    });
  }

  // ---------------------------------------------------------------- 叠层模块
  var fx = $('fx'); fx.width = W * dpr; fx.height = H * dpr;
  var ctx = fx.getContext('2d'), N = window.WeatherNoise, SEED = 20261105;
  // 调色统一由 daylight 负责：rain / snow 关掉自带 tint，避免两次压暗 / 提亮
  var dl = window.WeatherFX_daylight.create({ seed: SEED, noise: N });
  var rain = window.WeatherFX_rain.create({ seed: SEED + 1, noise: N, tint: false });
  var snow = window.WeatherFX_snow.create({ seed: SEED + 2, noise: N, tint: false });
  var fog = window.WeatherFX_fog.create({ seed: SEED + 3, noise: N });
  var sand = window.WeatherFX_sand.create({ seed: SEED + 4, noise: N });
  var fan = window.WeatherFX_fantasy.create({ seed: SEED + 5, noise: N });
  // daylight 放第一个：light pass 里它的夜色 multiply 先压暗，奇幻辉光再 lighter 加亮，不被夜色吃掉
  var MODS = [dl, rain, snow, fog, sand, fan], NAMES = ['daylight', 'rain', 'snow', 'fog', 'sand', 'fantasy'];
  var BASE_N = MODS.length;   // 前六个是已有模块：只收原 3.3 的六个 pass，读「代理状态」（第 8 节新 kind 换成它所处的基础天气）
  // 第 8 节最终顺序；bow / aurora 只发给可选叠层（aurora / ice / wind / sky），它们存在时才加载
  var PASSES = ['ground', 'reflect', 'precip', 'fog', 'light', 'bow', 'aurora', 'flash'];
  var BASE_PASS = { ground: 1, reflect: 1, precip: 1, fog: 1, light: 1, flash: 1 };
  MODS.forEach(function (m) { m.resize(W, H, dpr); });
  var ON = MODS.map(function () { return true; });   // 模块开关（排查哪个模块画了什么）
  function addModToggle(n, i) {
    var l = document.createElement('label'), c = document.createElement('input');
    c.type = 'checkbox'; c.checked = true; c.id = 'mod_' + n;
    c.addEventListener('change', function () { ON[i] = c.checked; });
    l.appendChild(c); l.appendChild(document.createTextNode(n)); $('modRow').appendChild(l);
  }
  NAMES.forEach(addModToggle);
  // 可选叠层用同源外部 script 加载，遵守服务端 script-src 'self'。
  var OPT = [
    { name: 'aurora', src: 'aurora/aurora.js', glob: 'WeatherFX_aurora', kinds: [], status: '加载中' },
    { name: 'ice', src: 'ice/ice.js', glob: 'WeatherFX_ice', kinds: ['freezing_rain', 'graupel', 'frost', 'rime'], status: '加载中' },
    { name: 'wind', src: 'wind/wind.js', glob: 'WeatherFX_wind', kinds: ['typhoon', 'tornado'], status: '加载中' },
    { name: 'sky', src: 'sky/sky.js', glob: 'WeatherFX_sky', kinds: ['haze', 'dust', 'blowing_sand', 'heatwave', 'sunshower'], status: '加载中' }
  ];
  var aur = null, aurGroundK = 0.45;
  function loadOptional(d, i) {
    function done() { showModStatus(); refreshKindLabels(); }
    function attach() {
      var A = window[d.glob];
      if (!A || typeof A.create !== 'function') { d.status = '没挂 ' + d.glob; return done(); }
      try {
        var m = A.create({ seed: SEED + 6 + i, noise: N }); m.resize(W, H, dpr);
        if (town) m.setScene(town.scene);
        MODS.push(m); NAMES.push(d.name); ON.push(true); addModToggle(d.name, MODS.length - 1);
        d.layer = m; d.status = 'ok';
        if (d.name === 'aurora') { aur = m; tuneAurora(m); }
      } catch (e) { d.status = '创建失败：' + e.message; }
      done();
    }
    if (window[d.glob]) { attach(); return; }
    var sc = document.createElement('script'); sc.src = d.src;
    sc.onload = attach;
    sc.onerror = function () { d.status = '加载失败：' + d.src; done(); };
    document.body.appendChild(sc);
  }
  /** 极光 0.9 档整体偏绿：只在本页把 WeatherFX_aurora 的地面染色（柔光淡染、自上而下渐变、屋顶加亮）乘 aurGroundK，
   *  帘幕与光弧不动。做法是在实例上包一层 drawGround，不改 aurora.js。 */
  function tuneAurora(m) {
    var base = m.drawGround;
    if (typeof base !== 'function') return;
    m.drawGround = function (ctx, A, c0, aa) { if (aurGroundK > 0.001) base.call(this, ctx, A, c0, aa * aurGroundK); };
  }
  function showModStatus() {
    var el = $('optStatus'); if (!el) { el = document.createElement('span'); el.id = 'optStatus'; el.style.color = '#c9a76a'; $('modRow').appendChild(el); }
    el.textContent = OPT.filter(function (d) { return d.status !== 'ok'; }).map(function (d) { return d.name + '：' + d.status + '（已跳过）'; }).join('  ');
  }
  var town = null, townIdx = -1, building = false;
  function applyScene(sc) {
    // daylight 的投影 / 倒影要带城墙；rain 的湿地按整幅地面算（同 rain/preview.js），其余用道路格当 ground
    dl.setScene(Object.assign({}, sc, { buildings: sc.buildingsWithWalls }));
    rain.setScene(Object.assign({}, sc, { ground: [[0, 0, W, H]] }));
    [snow, fog, sand, fan].forEach(function (m) { m.setScene(sc); });
    OPT.forEach(function (d) { if (d.layer) d.layer.setScene(sc); });
  }
  function loadTown(idx) {
    if (building) return; building = true; $('loading').style.display = 'block';
    buildTown(idx, function (t) {
      building = false; $('loading').style.display = 'none';
      town = t; townIdx = idx; applyScene(t.scene); window.__scene = t.scene;
      if (!t.ok) showErr('城镇栅格化失败');
    });
  }

  // ---------------------------------------------------------------- 控件
  var G = window.WeatherGen;
  var KIND_ZH = { clear: '晴', cloudy: '多云', overcast: '阴', fog: '雾', drizzle: '毛毛雨', rain: '雨', storm: '雷暴',
    snow: '雪', blizzard: '暴风雪', sleet: '雨夹雪', sandstorm: '沙暴', hail: '冰雹', aurora: '极光',
    mana_storm: '魔力风暴', spirit_mist: '灵雾', miasma: '瘴气', ashfall: '灰烬雨',
    freezing_rain: '冻雨', graupel: '霰', frost: '霜', rime: '雾凇', haze: '霾', dust: '浮尘', blowing_sand: '扬沙',
    typhoon: '台风', tornado: '龙卷风', heatwave: '热浪', sunshower: '太阳雨' };
  // 第 8.1 节新 kind。生成器还不认识时，用「基础天气」调 weatherAt 再补字段（代理状态）；
  // 六个已有模块始终收到 kind 换成基础天气的状态（它们不认识新 kind），可选叠层收到完整状态。
  var KINDS8 = ['freezing_rain', 'graupel', 'frost', 'rime', 'haze', 'dust', 'blowing_sand', 'typhoon', 'tornado', 'heatwave', 'sunshower'];
  var BASE_OF = { freezing_rain: 'rain', graupel: 'overcast', frost: 'clear', rime: 'fog', haze: 'cloudy', dust: 'cloudy',
    blowing_sand: 'cloudy', typhoon: 'storm', tornado: 'storm', heatwave: 'clear', sunshower: 'rain' };
  var PTYPE8 = { freezing_rain: 'freezing_rain', graupel: 'graupel', typhoon: 'rain', tornado: 'rain', sunshower: 'rain' };
  var GROUND8 = ['glaze', 'frost', 'rime', 'dust_cover'];
  var CLIMATE_ZH = { temperate: '温带', continental: '大陆性', maritime: '海洋性', mediterranean: '地中海',
    subtropical_monsoon: '亚热带季风', tropical: '热带', arid: '干旱', highland: '高原', polar: '寒带' };
  var SEASON_ZH = { spring: '春', summer: '夏', autumn: '秋', winter: '冬' };
  var GROUND = G.GROUND_NAMES;                                  // 生成器认识的累积量（可当 overrides）
  var GROUND_ALL = GROUND.concat(GROUND8.filter(function (k) { return GROUND.indexOf(k) < 0; }));
  SAMPLES.forEach(function (s, i) {
    var o = document.createElement('option'); o.value = i;
    o.textContent = s.sample + ' · ' + s.style + ' · ' + s.race + ' · seed ' + s.seed; $('town').appendChild(o);
  });
  var KIND_LIST = G.KINDS.concat(KINDS8.filter(function (k) { return G.KINDS.indexOf(k) < 0; }));
  KIND_LIST.forEach(function (k) { var o = document.createElement('option'); o.value = k; $('kind').appendChild(o); });
  /** 新 kind 的选项文字：对应叠层没加载时标「（未就绪）」，生成器不认识时标「代理」 */
  function refreshKindLabels() {
    Array.prototype.forEach.call($('kind').options, function (o) {
      var k = o.value, t = k + ' ' + (KIND_ZH[k] || k), d = OPT.filter(function (x) { return x.kinds.indexOf(k) >= 0; })[0];
      if (d && d.status !== 'ok') t += '（未就绪）';
      if (G.KINDS.indexOf(k) < 0) t += ' · 代理';
      o.textContent = t;
    });
  }
  refreshKindLabels();
  var CLIMATE_LIST = Array.isArray(G.CLIMATES) ? G.CLIMATES.slice() : Object.keys(G.CLIMATES);   // weather-gen 导出的是名字数组
  CLIMATE_LIST.forEach(function (k) { var o = document.createElement('option'); o.value = k; o.textContent = (CLIMATE_ZH[k] || k) + ' ' + k; $('climate').appendChild(o); });
  function outFor(el) { var o = el.parentNode.querySelector('output'); if (o) o.textContent = (+el.value).toFixed(el.step && +el.step >= 1 ? 0 : 2); }
  document.querySelectorAll('header input[type=range]').forEach(function (el) {
    outFor(el); el.addEventListener('input', function () { outFor(el); dirty = true; });
  });
  ['kind', 'hailMix', 'climate', 'season', 'lat', 'seed', 'fantasy', 'day', 'gAuto'].forEach(function (id) {
    $(id).addEventListener('change', function () { dirty = true; if (id === 'day') dayN = clampDay(+$('day').value); });
  });
  var mode = 'manual', playing = false, hourF = +$('hour').value, dayN = +$('day').value, dirty = true;
  function setMode(m) {
    mode = m === 'gen' ? 'gen' : 'manual'; dirty = true;
    document.body.classList.toggle('gen', mode === 'gen'); document.body.classList.toggle('manual', mode === 'manual');
    $('modeSeg').querySelectorAll('button').forEach(function (b) { b.classList.toggle('on', b.dataset.mode === mode); });
  }
  $('modeSeg').addEventListener('click', function (e) { if (e.target.dataset.mode) setMode(e.target.dataset.mode); });
  function setPlay(p) { playing = !!p; $('play').textContent = playing ? '⏸ 暂停' : '▶ 播放'; }
  $('play').addEventListener('click', function () { setPlay(!playing); });
  $('hour').addEventListener('input', function () { hourF = +$('hour').value; dirty = true; });
  $('town').addEventListener('change', function () { loadTown(+$('town').value); });
  $('strike').addEventListener('click', function () { rain.triggerLightning(); });
  $('random').addEventListener('click', function () {
    $('seed').value = (Math.random() * 1e6) | 0; dayN = 1 + ((Math.random() * 365) | 0); $('day').value = dayN; dirty = true;
  });
  function clampDay(d) { d = Math.round(d) || 1; return ((d - 1) % 365 + 365) % 365 + 1; }
  function showErr(t) { $('err').textContent = t || ''; }
  function fmtH(h) { var m = Math.floor(h * 60 + 1e-6); return ('0' + Math.floor(m / 60) % 24).slice(-2) + ':' + ('0' + m % 60).slice(-2); }

  // ---------------------------------------------------------------- 天气状态
  /** 手动参数 → overrides → weatherAt 补全。kind 不允许的取值按生成器报的范围夹紧后重试，并在页面上提示 */
  var notes = [];
  function genWithClamp(seed, day, hour, climate, opts) {
    notes = [];
    for (var tries = 0; tries < 12; tries++) {
      try { return G.weatherAt(seed, day, hour, climate, opts); } catch (e) {
        var m = /要求 (\S+) 在 \[([-\d.e]+), ([-\d.e]+)\]/.exec(e.message), ov = opts.overrides;
        if (!m || !ov) throw e;
        var path = m[1].split('.'), lo = +m[2], hi = +m[3], o = ov;
        for (var i = 0; i < path.length - 1; i++) o = o[path[i]] = Object.assign({}, o[path[i]] || {});
        var k = path[path.length - 1];
        if (o[k] == null) throw e;
        o[k] = Math.min(hi, Math.max(lo, o[k])); notes.push(m[1] + '→' + (+o[k].toFixed(2)));
      }
    }
    throw new Error('覆盖字段无法自洽');
  }
  var manualGround = {}; GROUND_ALL.forEach(function (k) { manualGround[k] = +$('g_' + k).value; });
  /** 生成器还不认识这个 kind 吗（第 8 节新 kind 在 weather-gen 更新前走代理） */
  function isProxy(kind) { return KINDS8.indexOf(kind) >= 0 && G.KINDS.indexOf(kind) < 0; }
  function manualOverrides() {
    var kind = $('kind').value, gk = isProxy(kind) ? BASE_OF[kind] : kind, ov = {
      kind: gk, intensity: +$('intensity').value, cloud_cover: +$('cloud').value, fog: +$('fogv').value,
      wind: { dir_deg: +$('dir').value, speed: +$('wspeed').value, gust: +$('gust').value }, ground: {}
    };
    if (kind === 'typhoon') {
      ov.cyclone = { category: +$('cyCat').value, phase: $('cyPhase').value };
      if (ov.cyclone.phase !== 'eye') ov.wind.speed = Math.max(0.7, ov.wind.speed);
    }
    if (kind === 'sunshower') ov.cloud_cover = Math.min(0.49, ov.cloud_cover);
    GROUND.forEach(function (k) { ov.ground[k] = manualGround[k]; });
    if (kind === 'storm' && $('hailMix').checked) ov.precipitation = { type: 'hail' };
    // 叠加极光：生成器只允许 clear / cloudy / aurora 带极光（其余 kind 的 aurora.strength 固定为 0）
    var auS = +$('auS').value;
    if (kind === 'aurora' || ((kind === 'clear' || kind === 'cloudy') && auS > 0)) ov.aurora = { strength: auS, hue: +$('auH').value };
    return ov;
  }
  function envOpts() {
    var o = { lat: Math.max(-90, Math.min(90, +$('lat').value || 0)) };
    if ($('season').value) o.season = $('season').value;
    if ($('fantasy').checked) o.fantasy = G.FANTASY.slice();
    return o;
  }
  function computeState() {
    var seed = (+$('seed').value) | 0, climate = $('climate').value, opts = envOpts(), h = Math.min(23.999, hourF);
    if (mode === 'manual') opts.overrides = manualOverrides();
    var st = genWithClamp(seed, dayN, h, climate, opts);
    return mode === 'manual' ? complete8(st, $('kind').value) : complete8(st, st.kind);
  }
  /** 补第 8.2 节字段。kind 是代理时把 kind / 强度 / 降水类型改回用户选的新 kind；
   *  手动模式下 rainbow / heat / cyclone / 新累积量取滑杆值；生成器已给出的字段不覆盖 */
  function complete8(st, kind) {
    var s = JSON.parse(JSON.stringify(st)), man = mode === 'manual', I = man ? +$('intensity').value : s.intensity;
    if (isProxy(kind)) {
      s.kind = kind; s.intensity = I;
      if (PTYPE8[kind]) s.precipitation = { type: PTYPE8[kind], rate: Math.max(0.05, s.precipitation.rate || 0.2 + 0.6 * I) };
      else s.precipitation = { type: 'none', rate: 0 };
      if (kind === 'frost' || kind === 'rime' || kind === 'freezing_rain') s.temperature_c = Math.min(s.temperature_c, kind === 'rime' ? -3 : kind === 'frost' ? -1 : -1.5);
      if (kind === 'graupel') s.temperature_c = Math.max(-2, Math.min(3, s.temperature_c));
      if (kind === 'heatwave') s.temperature_c = Math.max(s.temperature_c, 36 + 6 * I);
    }
    var AER = { haze: 'haze', dust: 'dust', blowing_sand: 'sand', sandstorm: 'sand' };
    if (!s.aerosol) s.aerosol = AER[kind] ? { type: AER[kind], density: kind === 'sandstorm' ? Math.max(0.7, I) : I } : { type: 'none', density: 0 };
    var rb = man ? +$('rainbow').value : 0, ht = man ? +$('heat').value : 0;
    if (kind === 'sunshower') rb = Math.max(rb, 0.6 * I);
    if (kind === 'heatwave') ht = Math.max(ht, I);
    if (s.rainbow == null || man) s.rainbow = rb;
    if (s.heat == null || man) s.heat = ht;
    if (kind === 'typhoon') { if (!s.cyclone || man) s.cyclone = { category: +$('cyCat').value, phase: $('cyPhase').value }; }
    else if (!s.cyclone) s.cyclone = { category: 0, phase: 'outer' };
    if (s.vortex == null || (man && kind === 'tornado')) s.vortex = kind === 'tornado' ? I : 0;
    GROUND8.forEach(function (k) { if (s.ground[k] == null || man) s.ground[k] = man ? manualGround[k] : 0; });
    return s;
  }
  /** 给六个已有模块的状态：它们不认识第 8 节新 kind，换成基础天气、降水类型换成它们认识的 */
  function baseStateOf(s) {
    if (!s || KINDS8.indexOf(s.kind) < 0) return s;
    var b = Object.assign({}, s, { kind: BASE_OF[s.kind] });
    var pt = s.precipitation.type;
    if (pt === 'freezing_rain') b.precipitation = { type: 'rain', rate: s.precipitation.rate };
    else if (pt === 'graupel') b.precipitation = { type: 'none', rate: 0 };
    return b;
  }
  GROUND8.forEach(function (k) {
    $('g_' + k).addEventListener('input', function () { manualGround[k] = +$('g_' + k).value; });
  });
  ['cyCat', 'cyPhase'].forEach(function (id) { $(id).addEventListener('change', function () { dirty = true; }); });
  $('aurGround').addEventListener('input', function () { aurGroundK = +$('aurGround').value; });
  GROUND.forEach(function (k) {
    $('g_' + k).addEventListener('input', function () { manualGround[k] = +$('g_' + k).value; });
  });
  /** 手动模式「自动」：按当前天气每游戏小时累积 / 消退（只为预览，规则近似 weather.py 的累积模型） */
  function accumulate(st, dtH) {
    if (!st || dtH <= 0) return;
    var k = st.kind, p = st.precipitation || {}, rate = p.rate || 0, T = st.temperature_c, gnd = manualGround, i = st.intensity;
    var wetIn = (p.type === 'rain' || p.type === 'sleet' || p.type === 'hail') ? rate : 0;
    var melt = (p.type === 'snow' ? 0 : Math.max(0, T) * 0.012 + (T > 0 ? 0.01 : 0));
    gnd.wetness += wetIn > 0 ? wetIn * 0.6 * dtH : -(0.06 + Math.max(0, T) * 0.004) * dtH;
    gnd.wetness += Math.min(gnd.snow_cover, melt * dtH) * 0.4;
    gnd.puddles += wetIn > 0 ? Math.max(0, gnd.wetness - 0.35) * wetIn * 0.6 * dtH : -0.1 * dtH;
    gnd.puddles = Math.min(gnd.puddles, gnd.wetness);
    if (p.type === 'snow' || p.type === 'sleet') gnd.snow_cover += (T <= 0.5 ? rate * (p.type === 'snow' ? 0.3 : 0.08) : 0) * dtH;
    else gnd.snow_cover -= melt * dtH;
    if (p.type === 'hail') gnd.hail_cover += rate * 0.35 * dtH; else gnd.hail_cover -= (0.02 + 0.004 * Math.max(0, T)) * dtH;
    if (p.type === 'graupel') gnd.graupel += rate * 0.15 * dtH; else gnd.graupel -= (0.005 + 0.012 * Math.max(0, T)) * dtH;
    if (k === 'ashfall') gnd.ash_cover += i * 0.15 * dtH; else gnd.ash_cover -= (wetIn > 0 ? 0.08 : 0.01) * dtH;
    if (k === 'mana_storm') gnd.mana_residue += i * 0.2 * dtH; else gnd.mana_residue -= 0.04 * dtH;
    // 第 8 节累积量（预览近似）：冻雨结冰壳、霜 / 雾凇在冰点下长、日照或升温后消退；浮尘积灰雨水冲掉
    var warm = T > 0 ? 0.03 + T * 0.01 : 0;
    if (k === 'freezing_rain') gnd.glaze += rate * 0.3 * dtH; else gnd.glaze -= (warm + 0.005) * dtH;
    if (k === 'frost') gnd.frost += (0.1 + 0.2 * i) * dtH; else gnd.frost -= (warm + 0.15) * dtH;
    if (k === 'rime') gnd.rime += (0.08 + 0.2 * i) * dtH; else gnd.rime -= (warm + 0.01) * dtH;
    if (k === 'dust' || k === 'blowing_sand' || k === 'sandstorm') gnd.dust_cover += i * 0.1 * dtH; else gnd.dust_cover -= (wetIn > 0 ? 0.1 : 0.005) * dtH;
    GROUND_ALL.forEach(function (n) {
      gnd[n] = Math.max(0, Math.min(1, gnd[n]));
      var el = $('g_' + n); el.value = gnd[n]; outFor(el);
    });
  }
  /** 把一份状态写回手动控件（从生成器切回手动时保持连续） */
  function syncControls(st) {
    if (!st) return;
    $('kind').value = st.kind; $('intensity').value = st.intensity; $('cloud').value = st.cloud_cover; $('fogv').value = st.fog;
    $('dir').value = Math.round(st.wind.dir_deg) % 360; $('wspeed').value = st.wind.speed; $('gust').value = st.wind.gust;
    $('hailMix').checked = st.kind === 'storm' && st.precipitation.type === 'hail';
    if (st.aurora) { $('auS').value = st.aurora.strength; $('auH').value = st.aurora.hue; }
    GROUND_ALL.forEach(function (k) { manualGround[k] = st.ground[k] || 0; $('g_' + k).value = manualGround[k]; });
    document.querySelectorAll('header input[type=range]').forEach(outFor);
  }
  var _setMode = setMode;
  setMode = function (m) { if (m !== 'gen' && mode === 'gen') syncControls(state); _setMode(m); };

  // ---------------------------------------------------------------- 预设（手动模式）
  var Z = { wetness: 0, puddles: 0, snow_cover: 0, hail_cover: 0, ash_cover: 0, mana_residue: 0, glaze: 0, frost: 0, rime: 0, dust_cover: 0, graupel: 0 };
  var PRESETS = [
    ['clear-noon', '晴正午', { kind: 'clear', intensity: 0.1, hour: 12.5, cloud: 0.1, fogv: 0, dir: 110, wspeed: 0.2, gust: 0.2 }],
    ['dusk', '黄昏', { kind: 'clear', intensity: 0.15, hour: 17.85, cloud: 0.2, fogv: 0, dir: 110, wspeed: 0.15, gust: 0.1 }],
    ['night', '夜晚', { kind: 'clear', intensity: 0.1, hour: 22.5, cloud: 0.05, fogv: 0, dir: 110, wspeed: 0.1, gust: 0.1 }],
    ['drizzle', '毛毛雨', { kind: 'drizzle', intensity: 0.25, hour: 10, cloud: 0.8, fogv: 0.1, dir: 200, wspeed: 0.2, gust: 0.2, g: { wetness: 0.35, puddles: 0.05 } }],
    ['heavy-rain', '大雨', { kind: 'rain', intensity: 0.9, hour: 14, cloud: 0.95, fogv: 0.15, dir: 250, wspeed: 0.5, gust: 0.4, g: { wetness: 0.9, puddles: 0.7 } }],
    ['storm', '雷暴', { kind: 'storm', intensity: 0.85, hour: 16, cloud: 1, fogv: 0.1, dir: 240, wspeed: 0.75, gust: 0.6, g: { wetness: 0.9, puddles: 0.6 } }],
    ['hail', '冰雹', { kind: 'hail', intensity: 0.85, hour: 15, cloud: 0.95, fogv: 0, dir: 230, wspeed: 0.5, gust: 0.4, g: { wetness: 0.5, puddles: 0.2, hail_cover: 0.5 } }],
    ['light-snow', '小雪', { kind: 'snow', intensity: 0.2, hour: 11, cloud: 0.75, fogv: 0.05, dir: 120, wspeed: 0.15, gust: 0.1, g: { snow_cover: 0.25 } }],
    ['blizzard', '暴风雪', { kind: 'blizzard', intensity: 0.92, hour: 13, cloud: 1, fogv: 0.2, dir: 80, wspeed: 0.85, gust: 0.7, g: { snow_cover: 0.85 } }],
    ['dense-fog', '浓雾', { kind: 'fog', intensity: 0.85, hour: 7.5, cloud: 0.04, fogv: 0.9, dir: 90, wspeed: 0.1, gust: 0.05, g: { wetness: 0.2 } }],
    ['sandstorm', '沙暴', { kind: 'sandstorm', intensity: 0.8, hour: 14, cloud: 0.04, fogv: 0.1, dir: 70, wspeed: 0.8, gust: 0.6 }],
    ['aurora-night', '极光夜', { kind: 'aurora', intensity: 0.85, hour: 23, cloud: 0.1, fogv: 0, dir: 260, wspeed: 0.2, gust: 0.1, auS: 0.85, auH: 0.45, climate: 'polar', g: { snow_cover: 0.4 } }],
    ['mana-storm', '魔力风暴', { kind: 'mana_storm', intensity: 0.8, hour: 20, cloud: 0.9, fogv: 0, dir: 300, wspeed: 0.6, gust: 0.5, g: { mana_residue: 0.6 } }],
    ['spirit-mist', '灵雾', { kind: 'spirit_mist', intensity: 0.6, hour: 9, cloud: 0.04, fogv: 0.65, dir: 100, wspeed: 0.15, gust: 0.1 }],
    ['miasma', '瘴气', { kind: 'miasma', intensity: 0.7, hour: 18.6, cloud: 0.7, fogv: 0.7, dir: 120, wspeed: 0.1, gust: 0.05, g: { wetness: 0.2 } }],
    ['ashfall', '灰烬雨', { kind: 'ashfall', intensity: 0.75, hour: 15, cloud: 0.9, fogv: 0.1, dir: 110, wspeed: 0.3, gust: 0.3, g: { ash_cover: 0.55 } }]
  ];
  var PRESET_MAP = {};
  PRESETS.forEach(function (p) {
    PRESET_MAP[p[0]] = p;
    var b = document.createElement('button'); b.textContent = p[1]; b.dataset.preset = p[0]; $('presets').appendChild(b);
  });
  $('presets').addEventListener('click', function (e) { if (e.target.dataset.preset) applyPreset(e.target.dataset.preset); });
  function applyPreset(name) {
    var p = PRESET_MAP[name]; if (!p) return false;
    var v = p[2];
    _setMode('manual');
    ['kind', 'intensity', 'cloud', 'fogv', 'dir', 'wspeed', 'gust'].forEach(function (id) { $(id).value = v[id]; });
    $('auS').value = v.auS || 0; $('auH').value = v.auH == null ? 0.3 : v.auH;
    $('hailMix').checked = false;
    $('climate').value = v.climate || 'temperate';
    var g = Object.assign({}, Z, v.g || {});
    GROUND_ALL.forEach(function (k) { manualGround[k] = g[k]; $('g_' + k).value = g[k]; });
    $('rainbow').value = v.rainbow || 0; $('heat').value = v.heat || 0;
    hourF = v.hour; $('hour').value = v.hour;
    document.querySelectorAll('header input[type=range]').forEach(outFor);
    $('presets').querySelectorAll('button').forEach(function (b) { b.classList.toggle('on', b.dataset.preset === name); });
    rain.triggerLightning && v.kind === 'storm' && rain.triggerLightning();
    dirty = true; return true;
  }

  // ---------------------------------------------------------------- 状态刷新、摘要、预报条
  var state = null, lastKey = '', fcKey = '', jsonT = 0;
  function refreshState() {
    try {
      var st = computeState(); state = st; showErr(notes.length ? '已按 kind 夹紧：' + notes.join('，') : '');
    } catch (e) { showErr(e.message); return; }
    document.body.classList.toggle('storm', $('kind').value === 'storm');
    var s = state, p = s.precipitation;
    $('summary').textContent = [
      fmtH(s.time.hour) + ' 第' + s.time.day_of_year + '天', SEASON_ZH[s.season] + ' · ' + (CLIMATE_ZH[s.climate] || s.climate),
      s.kind + ' ' + KIND_ZH[s.kind] + ' ' + s.intensity.toFixed(2), '降水 ' + p.type + ' ' + p.rate.toFixed(2),
      '气温 ' + s.temperature_c.toFixed(1) + '℃', '云 ' + s.cloud_cover.toFixed(2), '雾 ' + s.fog.toFixed(2),
      '能见 ' + s.visibility.toFixed(2), '风 ' + Math.round(s.wind.dir_deg) + '° ' + s.wind.speed.toFixed(2) + '/' + s.wind.gust.toFixed(2),
      '雷 ' + s.lightning.toFixed(2), '日出 ' + fmtH(s.time.sunrise) + ' 日落 ' + fmtH(s.time.sunset % 24),
      '地面 湿' + s.ground.wetness.toFixed(2) + ' 洼' + s.ground.puddles.toFixed(2) + ' 雪' + s.ground.snow_cover.toFixed(2) +
        ' 冰' + s.ground.hail_cover.toFixed(2) + ' 灰' + s.ground.ash_cover.toFixed(2) + ' 晶' + s.ground.mana_residue.toFixed(2)
    ].join('  |  ');
    if (mode === 'gen') {
      $('hourOut').textContent = fmtH(hourF);
      var key = [$('seed').value, $('climate').value, $('season').value, $('lat').value, $('fantasy').checked, dayN, Math.floor(hourF)].join();
      if (key !== fcKey) {
        fcKey = key;
        try {
          var o = envOpts(), fc = G.forecast((+$('seed').value) | 0, dayN, Math.floor(hourF), 24, $('climate').value, o);
          $('forecast').innerHTML = '<b>未来 24 小时</b>' + fc.map(function (f, i) {
            return '<span' + (i === 0 ? ' class="now"' : '') + ' title="' + f.kind + ' ' + f.intensity.toFixed(2) + ' ' +
              f.temperature_c.toFixed(1) + '℃">' + ('0' + Math.floor(f.time.hour)).slice(-2) + ' ' + KIND_ZH[f.kind] + '</span>';
          }).join('');
        } catch (e) { $('forecast').textContent = '预报失败：' + e.message; }
      }
    }
  }
  function updateJson(force) {
    if (!state || (!force && !$('jsonBox').open)) return;
    $('json').textContent = JSON.stringify(state, function (k, v) { return typeof v === 'number' ? +v.toFixed(4) : v; }, 2);
  }
  $('jsonBox').addEventListener('toggle', function () { updateJson(true); });

  // ---------------------------------------------------------------- 主循环
  var last = performance.now(), frames = 0, acc = 0, fpsNow = 0, fpsLog = [], lastHourKey = -1;
  function advanceTime(dt) {
    if (!playing) return 0;
    var gh = dt * (+$('speedMul').value) / 3600;   // 游戏小时
    hourF += gh;
    while (hourF >= 24) { hourF -= 24; dayN = clampDay(dayN + 1); $('day').value = dayN; }
    $('hour').value = Math.min(23.99, hourF);
    return gh;
  }
  function frame(now) {
    var dt = Math.min(0.1, Math.max(0, (now - last) / 1000)); last = now;
    frames++; acc += dt;
    if (acc >= 0.5) { fpsNow = frames / acc; fpsLog.push(fpsNow); if (fpsLog.length > 240) fpsLog.shift(); $('fps').textContent = fpsNow.toFixed(1) + ' fps · dpr ' + dpr; frames = 0; acc = 0; }
    var gh = advanceTime(dt);
    if (gh > 0 && mode === 'manual' && $('gAuto').checked) accumulate(state, gh);
    var hk = Math.round(hourF * 60);                 // 每游戏分钟重算一次状态（weatherAt 约 0.3 ms）
    if (dirty || hk !== lastHourKey || (gh > 0 && mode === 'manual' && $('gAuto').checked)) { dirty = false; lastHourKey = hk; refreshState(); }
    $('hourOut').textContent = fmtH(hourF); $('dayOut').textContent = '';
    jsonT += dt; if (jsonT > 0.5) { jsonT = 0; updateJson(false); }
    var st = state;
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1;
    ctx.fillStyle = '#111'; ctx.fillRect(0, 0, fx.width, fx.height);
    if (st) { var bst = baseStateOf(st); MODS.forEach(function (m, i) { m.update(i < BASE_N ? bst : st, dt); }); }
    if (town && st) {
      // 底图地面+水 → daylight 倒影（必须在岸上实物之下）→ 实物；之后按 3.3 顺序逐 pass 调全部模块
      ctx.drawImage(town.ground, 0, 0);
      if (ON[0]) drawLayer(dl, 'reflect');
      ctx.drawImage(town.objects, 0, 0);
      for (var pi = 0; pi < PASSES.length; pi++) {
        var pass = PASSES[pi];
        for (var mi = 0; mi < MODS.length; mi++) {
          if (!ON[mi] || (MODS[mi] === dl && pass === 'reflect')) continue;   // 关掉的模块 / 已在实物之下画过的倒影
          if (mi < BASE_N && !BASE_PASS[pass]) continue;                       // bow / aurora 只发给可选叠层
          drawLayer(MODS[mi], pass);
        }
      }
    }
    requestAnimationFrame(frame);
  }
  // 底图缓冲按设备像素绘制；天气和 scene 按 CSS 像素绘制。
  // 某些模块自行 setTransform(dpr)，其余继承这里的变换；绝不能累乘 scale(dpr)。
  function drawLayer(layer, pass) {
    ctx.save();
    try {
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1; ctx.filter = 'none';
      ctx.beginPath();
      layer.draw(ctx, pass);
    } finally {
      ctx.restore(); ctx.beginPath();
    }
  }

  // ---------------------------------------------------------------- 初始化、URL 参数、调试接口
  // ?town=45&preset=storm&mode=gen&play=1&speed=3600&climate=polar&day=20&seed=7&fantasy=1&hour=13&dpr=2
  var defIdx = SAMPLES.findIndex(function (s) { return s.sample === 'port' && s.style === 'west' && s.race === 'common' && s.seed === 1; });
  if (defIdx < 0) defIdx = 0;
  var tq = Q.get('town'), tIdx = tq != null && tq !== '' && +tq >= 0 && +tq < SAMPLES.length ? +tq : defIdx;
  $('town').value = tIdx;
  $('climate').value = CLIMATE_LIST.indexOf(Q.get('climate')) >= 0 ? Q.get('climate') : 'temperate';
  if (Q.get('seed')) $('seed').value = Q.get('seed') | 0;
  if (Q.get('day')) { dayN = clampDay(+Q.get('day')); $('day').value = dayN; }
  if (Q.get('fantasy') === '1') $('fantasy').checked = true;
  if (Q.get('season')) $('season').value = Q.get('season');
  if (Q.get('speed')) $('speedMul').value = Q.get('speed');
  _setMode(Q.get('mode') === 'gen' ? 'gen' : 'manual');
  if (Q.get('preset')) applyPreset(Q.get('preset'));
  if (Q.get('hour') != null) { hourF = Math.max(0, Math.min(23.99, +Q.get('hour'))); $('hour').value = hourF; }
  setPlay(Q.get('play') === '1');
  loadTown(tIdx);
  OPT.forEach(loadOptional);

  window.__wx = {
    /** 直接改控件：{ kind, intensity, cloud, fogv, dir, wspeed, gust, hour, climate, seed, day, g:{wetness,...} } */
    set: function (o) {
      Object.keys(o || {}).forEach(function (k) {
        if (k === 'g') { Object.keys(o.g).forEach(function (n) { manualGround[n] = o.g[n]; $('g_' + n).value = o.g[n]; }); }
        else if (k === 'hour') { hourF = o.hour; $('hour').value = o.hour; }
        else if (k === 'day') { dayN = clampDay(o.day); $('day').value = dayN; }
        else if ($(k)) { if ($(k).type === 'checkbox') $(k).checked = !!o[k]; else $(k).value = o[k]; }
      });
      document.querySelectorAll('header input[type=range]').forEach(outFor); dirty = true;
    },
    preset: applyPreset,
    presets: function () { return PRESETS.map(function (p) { return p[0]; }); },
    mode: function (m) { setMode(m); },
    play: function (p) { setPlay(p); },
    speed: function (v) { $('speedMul').value = String(v); },
    town: function (i) { loadTown(i); $('town').value = i; },
    ready: function () { return !!town && !building && !!state; },
    state: function () { return state; },
    fps: function () { return fpsLog.length ? fpsLog.reduce(function (a, b) { return a + b; }, 0) / fpsLog.length : 0; },
    resetFps: function () { fpsLog.length = 0; },
    strike: function () { rain.triggerLightning(); },
    /** 模块开关：enable({ fog:false }) */
    enable: function (o) { NAMES.forEach(function (n, i) { if (o && n in o) { ON[i] = !!o[n]; $('mod_' + n).checked = ON[i]; } }); },
    modules: NAMES,
    aurora: function () { return { loaded: !!aur, status: OPT[0].status }; },
    optional: function () { return OPT.map(function (d) { return { name: d.name, status: d.status }; }); },
    aurGround: function (k) { aurGroundK = +k; $('aurGround').value = k; outFor($('aurGround')); }
  };
  requestAnimationFrame(function (t) { last = t; frame(t); });
})();
