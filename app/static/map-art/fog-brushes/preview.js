/* 织梦 · 迷雾卷云笔刷预览（美术样板，尚未接入游戏） */
(function () {
  'use strict';
  var FB = window.FogBrushes;
  var NS = 'http://www.w3.org/2000/svg';
  var MAP = '../../../../assets/maps/world-hypsometric.png'; // 2160×1080，等经纬，6 px/度（只读示意）

  function rng(seed) { // mulberry32
    return function () {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      var t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  var byId = {}; FB.BRUSHES.forEach(function (b) { byId[b.id] = b; });

  // ---------- 图册 ----------
  var grid = document.getElementById('atlas-grid');
  FB.BRUSHES.forEach(function (b) {
    var base = 'brush-' + b.id + '-' + b.key + '-';
    var card = document.createElement('div'); card.className = 'card';
    card.innerHTML = '<div class="meta"><b>' + b.id.toUpperCase() + ' · ' + b.name + '</b><span>' + b.note +
      '</span><br><span>' + b.w + '×' + b.h + '</span></div>' +
      fig(base + 'mid.svg', b.w, b.h, '原尺寸 · 羊皮纸') +
      fig(base + 'light.svg', b.w, b.h, '原尺寸 · 浅羊皮纸') +
      fig(base + 'mid.svg', b.w * 2, b.h * 2, '放大 ×2');
    grid.appendChild(card);
  });
  function fig(src, w, h, cap) {
    return '<figure><img src="' + src + '" width="' + w + '" height="' + h + '" alt="' + cap + '"><figcaption>' + cap + '</figcaption></figure>';
  }
  var tones = document.getElementById('tones');
  FB.TONE_ORDER.forEach(function (k) {
    var t = FB.TONES[k];
    tones.insertAdjacentHTML('beforeend', '<div class="tone"><i style="background:linear-gradient(' + t.top + ',' + t.body + ',' + t.shade +
      ');border-top:2px solid ' + t.ink + '"></i>' + t.name + '</div>');
  });

  // ---------- 共用笔刷定义（每个 笔刷×色调 只定义一次，场景里全部用 <use>） ----------
  var defsMarkup = '';
  FB.BRUSHES.forEach(function (b) {
    FB.TONE_ORDER.forEach(function (tone) {
      var r = FB.render(b, tone, 'pv-' + b.id + '-' + tone);
      defsMarkup += r.defs + '<g id="use-' + b.id + '-' + tone + '">' + r.body + '</g>';
    });
  });
  var shared = document.createElementNS(NS, 'svg');
  shared.setAttribute('width', '0'); shared.setAttribute('height', '0');
  shared.setAttribute('style', 'position:absolute');
  shared.innerHTML = '<defs>' + defsMarkup + '</defs>';
  document.body.insertBefore(shared, document.body.firstChild);

  // 方案 B：一排排平行于边界、由内向外像屋瓦一样叠放。先画内排，外排的云头压在内排的下身上，
  // 所以每排只露出带墨线的云头；笔刷是不透明平涂，排与排之间没有半透明过渡。
  // 排数按场景需要一直铺到画面边缘，未知区不留空白底色。
  var TONE_STEPS = ['light', 'mid', 'mid', 'dark', 'dark', 'dusk', 'dusk', 'coal'];
  var POOLS = ['aecab', 'cbdea', 'bcdea', 'bdcfe', 'fbdcf'];
  function rowsFor(maxD) {
    var rows = [], d = 0.15, i = 0;
    while (d < maxD) {
      rows.push({ tone: TONE_STEPS[Math.min(i, TONE_STEPS.length - 1)], d: d,
        s: Math.min(1.3, 0.6 + 0.12 * i), gap: 0.6, pool: POOLS[Math.min(4, Math.floor(i * 0.6))],
        skip: i === 0 ? 0.18 : 0 });
      d += 0.8 + 0.14 * i; i++;
    }
    return rows;
  }

  // ---------- 东方玄幻：祥云 + 海水纹（fog-xiangyun.js） ----------
  var XY = window.FogXiangyun, CE = window.FogCelestial;
  // 每排从几种色里随机取：内缘米白、赭黄为主，往外混入橘红、朱红、青绿，最外赭褐、藏青。
  var EAST_ROWS = [['cream'], ['cream', 'ochre'], ['ochre', 'cream', 'orange'], ['orange', 'ochre', 'teal'],
    ['vermil', 'orange', 'ochre', 'teal'], ['teal', 'vermil', 'ochre'], ['umber', 'teal', 'orange'], ['navy', 'umber', 'teal']];
  function eastWall(curve, length, U, seed, closed, maxD, spread) {
    var R = rng(seed), out = [], d = 0.25, i = 0, pending = [];
    while (d < maxD) {
      var k = spread ? spread(d * U) : 1, rs = U * (i < 2 ? 0.72 : 0.46 + 0.07 * i), pals = EAST_ROWS[Math.min(i, EAST_ROWS.length - 1)];
      var s = (closed ? 0 : -60) + R() * rs * 2, end = closed ? length : length + 60, items = [], heroes = [];
      while (s < end) {
        var c = curve(closed ? s % length : s);
        // 云团大小与形状拉开：贴地图两排用长云带（不碎成气泡）；往外大小簇混排，偶尔一团高耸的主角云
        var form, mul, q = R();
        if (i === 0) { form = q < 0.55 ? 'mound' : 'bank'; mul = 0.9 + R() * 0.6; }
        else if (i === 1 && q < 0.12) { form = 'tower'; mul = 1.6 + R() * 0.5; }
        else if (i === 1) { form = q < 0.6 ? 'mound' : 'bank'; mul = 0.9 + R() * 0.5; }
        else if (q < 0.22) { form = 'tower'; mul = 2.0 + R() * 0.9; }
        else if (q < 0.45) { form = 'tuft'; mul = 0.5 + R() * 0.25; }
        else if (q < 0.6) { form = 'bank'; mul = 0.8 + R() * 0.3; }
        else { form = 'mound'; mul = 0.85 + R() * 0.55; }
        var Rr = rs * mul;
        var dd = (d + (R() - 0.5) * 0.3) * U;
        if (i === 0 && R() < 0.2) dd -= 0.3 * U;           // 偶尔一团伸进地图边缘
        if (form === 'tower') dd += Rr * 0.35;              // 主角云底座退后一点，云顶往地图方向高高耸起
        var x = c.x - c.nx * dd, y = c.y - c.ny * dd;
        var phi = Math.atan2(c.nx, -c.ny) * 180 / Math.PI + (R() - 0.5) * 10;
        var pal = XY.PAL[pals[Math.floor(R() * pals.length)]];
        var g = '<g transform="translate(' + x.toFixed(1) + ' ' + y.toFixed(1) + ') rotate(' + phi.toFixed(1) + ') scale(' + (R() < 0.5 ? -1 : 1) + ' 1)">' +
          XY.cluster(Rr, pal, Math.floor(R() * 1e9), form) + '</g>';
        (form === 'tower' ? heroes : items).push(g);
        var span = form === 'bank' ? 3.4 : form === 'tuft' ? 1.4 : form === 'tower' ? 1.2 : 2.3;
        s += Rr * span * k * (0.55 + R() * 0.3);
      }
      for (var a = items.length - 1; a > 0; a--) { var b = Math.floor(R() * (a + 1)); var t = items[a]; items[a] = items[b]; items[b] = t; }
      out.push('<g>' + items.join('') + '</g>');
      // 主角云晚一排再画，压在下一排的云头上，才显得高耸
      out.push(pending.join('')); pending = heroes;
      d += 0.44 + 0.07 * i; i++;
    }
    out.push(pending.join(''));
    return out.join('');
  }
  // 角上的螺旋日轮，下半身被两团云挡住
  function eastSun(cx, cy, r, seed) {
    var R = rng(seed);
    return CE.redSun(cx, cy, r) +
      '<g transform="translate(' + (cx - r * 0.6).toFixed(1) + ' ' + (cy + r * 0.55).toFixed(1) + ')">' + XY.cluster(r * 0.55, XY.PAL.ochre, Math.floor(R() * 1e9)) + '</g>' +
      '<g transform="translate(' + (cx + r * 0.7).toFixed(1) + ' ' + (cy + r * 0.75).toFixed(1) + ') scale(-1 1)">' + XY.cluster(r * 0.5, XY.PAL.cream, Math.floor(R() * 1e9)) + '</g>';
  }
  // 西方：右上木刻太阳、左上月牙配几颗八芒星。下半身各被两三团云挡住；
  // 云用与角落云墙同一色调（暖灰褐），平涂色和墙连成一片，只露出带墨线的云头，不再像一片药片。
  function westCorners(seed) {
    var R = rng(seed + 9);
    function cloud(id, x, y, sc, fl, tone) {
      var b = byId[id];
      return '<use href="#use-' + id + '-' + (tone || 'dusk') + '" transform="translate(' + x + ' ' + y + ') scale(' + (sc * fl) + ' ' + sc + ') translate(' + (-b.w / 2) + ' ' + (-b.headY) + ')"/>';
    }
    return CE.westSun(972, 110, 66) + cloud('b', 1000, 196, 0.62, -1, 'coal') + cloud('e', 925, 182, 0.6, 1) + cloud('e', 1050, 178, 0.5, -1) +
      CE.westMoon(122, 114, 70) + cloud('b', 110, 206, 0.58, 1, 'coal') + cloud('e', 168, 192, 0.5, -1) +
      [[228, 58, 10], [258, 128, 6], [52, 226, 7], [212, 222, 5]].map(function (s) { return CE.westStar(s[0] + (R() - 0.5) * 6, s[1], s[2]); }).join('');
  }
  function eastCloudlets(list) {
    return list.map(function (c, i) {
      return '<g transform="translate(' + c[0] + ' ' + c[1] + ')">' + XY.cloudlet(c[2], XY.PAL[c[3] || 'ochre'], 100 + i) + '</g>';
    }).join('');
  }

  /**
   * 沿一条边界铺云墙。curve(s) → {x, y, nx, ny}：s 为弧长，n 为指向“地图（清晰区）”的单位法线。
   * 云头朝向地图；每排沿法线反方向外推。maxD = 铺到离边界多远（U 的倍数）；
   * spread(dd) = 外推 dd 后同一段边界弧长被拉长的倍数的倒数（圆形围合用，直段为 1）。
   */
  function wall(curve, length, U, seed, closed, maxD, spread) {
    var R = rng(seed), out = [];
    rowsFor(maxD).forEach(function (row, ri) {
      var k = spread ? spread(row.d * U) : 1;
      var s = (closed ? 0 : -60) + R() * 40, prev = '';
      var end = closed ? length : length + 60;
      var items = [];
      while (s < end) {
        var id;
        do { id = row.pool[Math.floor(R() * row.pool.length)]; } while (id === prev && row.pool.length > 1);
        prev = id;
        var b = byId[id];
        var sc = row.s * (U / 60) * (0.9 + R() * 0.2);
        var c = curve(closed ? s % length : s);
        var dd = (row.d + (R() - 0.5) * 0.22) * U;
        // 最内一排偶尔断开、偶尔有一团伸进地图，内缘不是一道干净的圆孔
        if (row.skip && R() < row.skip) { s += b.w * sc * 0.7 * k; continue; }
        // 只让圆润的小簇云（e）稍稍伸进地图，长条笔刷伸进去会露出平直的底边
        if (ri === 0 && id === 'e' && R() < 0.35) dd -= 0.28 * U;
        var x = c.x - c.nx * dd, y = c.y - c.ny * dd;
        var phi = Math.atan2(c.nx, -c.ny) * 180 / Math.PI + (R() - 0.5) * 4;
        var flip = R() < 0.45 ? -1 : 1;
        items.push('<use href="#use-' + id + '-' + row.tone + '" transform="translate(' + x.toFixed(1) + ' ' + y.toFixed(1) +
          ') rotate(' + phi.toFixed(1) + ') scale(' + (sc * flip).toFixed(3) + ' ' + sc.toFixed(3) + ') translate(' +
          (-b.w / 2) + ' ' + (-b.headY) + ')"/>');
        s += b.w * sc * row.gap * (0.85 + R() * 0.3) * k;
      }
      // 同层内也打乱前后，免得一排整齐压边
      for (var i = items.length - 1; i > 0; i--) { var j = Math.floor(R() * (i + 1)); var t = items[i]; items[i] = items[j]; items[j] = t; }
      out.push('<g class="row-' + ri + '">' + items.join('') + '</g>');
    });
    return out.join('');
  }

  function skyGradient(id, attrs, style) {
    // 云后的底色：与最外排同色系（基本被云盖满，只在缝里露一点）。西方旧纸灰褐，东方靛紫。
    var c = style === 'east' ? ['#d99a45', '#9c4a2a'] : ['#c2b294', '#ab9b7f'];
    return '<radialGradient id="' + id + '" ' + attrs + '><stop offset="0" stop-color="' + c[0] + '"/>' +
      '<stop offset="1" stop-color="' + c[1] + '"/></radialGradient>';
  }
  function mapImage(W, H, lon0, lat0, lon1, lat1, clip) {
    // 把经纬范围映射进场景矩形
    var px = W / ((lon1 - lon0) * 6), py = H / ((lat0 - lat1) * 6);
    var ox = -(lon0 + 180) * 6 * px, oy = -(90 - lat0) * 6 * py;
    return '<image href="' + MAP + '" x="' + ox.toFixed(1) + '" y="' + oy.toFixed(1) + '" width="' + (2160 * px).toFixed(1) +
      '" height="' + (1080 * py).toFixed(1) + '" preserveAspectRatio="none"' + (clip ? ' clip-path="url(#' + clip + ')"' : '') + '/>';
  }
  function label(W, H, text) {
    return '<g font-family="Microsoft YaHei, sans-serif" font-size="13"><rect x="10" y="' + (H - 32) + '" width="' + (text.length * 13 + 16) +
      '" height="22" rx="3" fill="#1d1f22" fill-opacity="0.78"/><text x="18" y="' + (H - 16) + '" fill="#e7c48a">' + text + '</text></g>';
  }
  function mount(id, W, H, inner) {
    document.getElementById(id).innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + W + ' ' + H + '" width="' + W + '" height="' + H + '">' + inner + '</svg>';
  }

  // ---------- 直段 ----------
  (function () {
    var W = 1000, H = 400, y0 = 170, U = 54;
    var curve = function (s) { return { x: s, y: y0, nx: 0, ny: -1 }; };
    mount('scene-straight', W, H,
      '<defs>' + skyGradient('sky-st', 'gradientUnits="userSpaceOnUse" cx="500" cy="' + y0 + '" r="360" fx="500" fy="' + y0 + '"') +
      '<clipPath id="clip-st"><rect width="' + W + '" height="' + H + '"/></clipPath></defs>' +
      mapImage(W, H, 4, 54, 22, 47.5) +
      '<g clip-path="url(#clip-st)"><rect x="0" y="' + (y0 + U * 1.0) + '" width="' + W + '" height="' + H + '" fill="url(#sky-st)"/>' +
      wall(curve, W, U, 11, false, (H - y0) / U + 0.6) + '</g>' + label(W, H, '直段云墙 · 示意底图'));
  })();

  // ---------- 弯段（S 形起伏的边界） ----------
  function curveScene(id, style, seed, text) {
    var W = 1000, H = 440, U = 54;
    function yAt(x) { return 190 + 60 * Math.sin(x / 170) + 25 * Math.sin(x / 61 + 1); }
    // 按弧长取样
    var table = [], acc = 0, px = -80, py = yAt(-80);
    for (var x = -80; x <= W + 80; x += 2) { var y = yAt(x); acc += Math.hypot(x - px, y - py); table.push([acc, x]); px = x; py = y; }
    var curve = function (s) {
      var i = 0; while (i < table.length - 1 && table[i][0] < s + 0) i++;
      var xx = table[i][1], dy = (yAt(xx + 1) - yAt(xx - 1)) / 2, l = Math.hypot(1, dy);
      return { x: xx, y: yAt(xx), nx: dy / l, ny: -1 / l };
    };
    var sky = 'M-10 ' + (H + 10);
    for (var k = -10; k <= W + 10; k += 10) sky += 'L' + k + ' ' + (yAt(k) + U * 1.0).toFixed(1);
    sky += 'L' + (W + 10) + ' ' + (H + 10) + 'Z';
    mount(id, W, H,
      '<defs>' + skyGradient('sky-' + id, 'gradientUnits="userSpaceOnUse" cx="500" cy="190" r="380"', style) + '</defs>' +
      mapImage(W, H, 8, 50, 26, 43) +
      '<path d="' + sky + '" fill="url(#sky-' + id + ')"/>' +
      '<g transform="translate(80 0)">' + (style === 'east' ? eastWall : wall)(function (s) { var c = curve(s); c.x -= 80; return c; }, acc - 60, U, seed, false, (H - 100) / U + 0.6) + '</g>' +
      (style === 'east' ? XY.waves(W, 350, H, seed + 5, 3) : CE.westWaves(W, 352, H, seed + 5, 3)) +
      label(W, H, text));
  }
  curveScene('scene-curve', 'west', 23, '弯段云墙 · 示意底图');
  curveScene('scene-east-curve', 'east', 41, '东方祥云 · 弯段 · 示意底图');

  // ---------- 近圆形围合 ----------
  function ringScene(id, style, seed, text) {
    var W = 1100, H = 820, cx = 560, cy = 400, R0 = 238, U = 48;
    function rad(t) { return R0 * (1 + 0.07 * Math.sin(2 * t + 0.6) + 0.04 * Math.sin(3 * t + 2.1) + 0.025 * Math.sin(5 * t + 4)); }
    var table = [], acc = 0, N = 720, prev = null;
    for (var i = 0; i <= N; i++) {
      var t = i / N * Math.PI * 2, r = rad(t), p = [cx + Math.cos(t) * r, cy + Math.sin(t) * r];
      if (prev) acc += Math.hypot(p[0] - prev[0], p[1] - prev[1]);
      table.push([acc, t]); prev = p;
    }
    var curve = function (s) {
      var i = 0; while (i < table.length - 1 && table[i][0] < s) i++;
      var t = table[i][1], r = rad(t), x = cx + Math.cos(t) * r, y = cy + Math.sin(t) * r;
      // 指向中心的法线（用切线求，再保证朝内）
      var e = 0.002, x2 = cx + Math.cos(t + e) * rad(t + e), y2 = cy + Math.sin(t + e) * rad(t + e);
      var tx = x2 - x, ty = y2 - y, l = Math.hypot(tx, ty), nx = -ty / l, ny = tx / l;
      if (nx * (cx - x) + ny * (cy - y) < 0) { nx = -nx; ny = -ny; }
      return { x: x, y: y, nx: nx, ny: ny };
    };
    var hole = '';
    for (var k = 0; k <= 180; k++) {
      var tt = k / 180 * Math.PI * 2, rr = rad(tt) + U * 1.0; // 暗天空底藏在中层云下，内缘断口里透出的是地图
      hole += (k ? 'L' : 'M') + (cx + Math.cos(tt) * rr).toFixed(1) + ' ' + (cy + Math.sin(tt) * rr).toFixed(1);
    }
    mount(id, W, H,
      '<defs>' + skyGradient('sky-' + id, 'gradientUnits="userSpaceOnUse" cx="' + cx + '" cy="' + cy + '" r="640"', style) + '</defs>' +
      mapImage(W, H, 6, 54, 24, 44) +
      '<path d="M0 0H' + W + 'V' + H + 'H0Z' + hole + 'Z" fill="url(#sky-' + id + ')" fill-rule="evenodd"/>' +
      (style === 'east' ? eastWall : wall)(curve, acc, U, seed, true, Math.hypot(cx, H - cy) / U - R0 / U * 0.85 + 0.8, function (dd) { return R0 / (R0 + dd); }) +
      (style === 'east'
        ? eastSun(985, 105, 70, seed) + CE.eastMoon(118, 108, 58) +
          eastCloudlets([[205, 168, 20, 'ochre'], [70, 190, 14, 'cream'], [760, 52, 18, 'ochre']]) +
          XY.waves(W, 700, H, seed + 5, 3)
        : westCorners(seed) + CE.westWaves(W, 702, H, seed + 5, 3)) +
      '<g font-family="Microsoft YaHei, sans-serif"><circle cx="' + (cx - 30) + '" cy="' + (cy + 10) + '" r="7" fill="#efe6d2" stroke="#2b2a29" stroke-width="2.5"/>' +
      '<text x="' + (cx - 16) + '" y="' + (cy + 16) + '" font-size="16" fill="#2b2a29" stroke="#efe6d2" stroke-width="3" paint-order="stroke">示意地点</text></g>' +
      label(W, H, text));
  }
  ringScene('scene-ring', 'west', 37, '近圆形围合 · 示意底图，非正式玩家地图');
  ringScene('scene-east-ring', 'east', 53, '东方祥云 · 近圆形围合 · 示意底图');

  // ---------- 西方船型参考：吃水线以下用一道纸色水面盖住 ----------
  (function () {
    var W = 1000, H = 330, wl = 270;
    var sea = '<path d="M0 ' + wl + 'Q125 ' + (wl - 6) + ' 250 ' + wl + 'T500 ' + wl + 'T750 ' + wl + 'T1000 ' + wl + 'V' + H + 'H0Z" fill="#cdc1a1" stroke="#4a3826" stroke-width="1.6"/>';
    mount('scene-ships', W, H, '<rect width="' + W + '" height="' + H + '" fill="#e9dcc0"/>' +
      CE.cog(170, wl, 1.7, 1) + CE.carrack(480, wl, 1.75, 1) + CE.galleon(810, wl, 1.45, 1) + sea +
      '<g font-family="Microsoft YaHei, sans-serif" font-size="14" fill="#4a3826" text-anchor="middle">' +
      '<text x="170" y="312">柯克船</text><text x="480" y="312">卡拉克船（雾效使用）</text><text x="810" y="312">战列舰 / 盖伦船</text></g>');
  })();
})();
