/* 织梦 · 城镇建筑美术总览页（仅预览用；正式的城镇内部生成系统另做） */
(function () {
  'use strict';
  var C = window.TOWN_CATALOG, S = 48, NS = 'http://www.w3.org/2000/svg';
  var M = {}; C.meta.forEach(function (m) { M[m.id] = m; });

  // 雪碧图只插一次：0×0 绝对定位（display:none 会让 clipPath 失效）
  var holder = document.createElement('div');
  holder.innerHTML = '<svg xmlns="' + NS + '" width="0" height="0" style="position:absolute;width:0;height:0;overflow:hidden">' + C.sprite + '</svg>';
  document.body.insertBefore(holder.firstChild, document.body.firstChild);

  function rng(seed) { return function () { seed |= 0; seed = seed + 0x6D2B79F5 | 0; var t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  function bin(m) { return ('000' + m.toString(2)).slice(-4); }
  function use(id, x, bottom) {
    var m = M[id]; if (!m) return '';
    var W = m.viewBox[2], H = m.viewBox[3];
    return '<use href="#' + id + '" x="' + x.toFixed(1) + '" y="' + (bottom - H).toFixed(1) + '" width="' + W + '" height="' + H + '"/>';
  }
  function pick(dirs, cat, style) {
    return C.meta.filter(function (m) { return dirs.indexOf(m.dir) >= 0 && m.category === cat && (!style || m.style === style); }).map(function (m) { return m.id; });
  }

  // 各风格的素材组合
  var SETS = {
    west:  { houses: pick(['west-base'], 'house'), specials: pick(['west-special'], 'special').concat(pick(['special-infra'], 'special', 'west').filter(noWater)),
             props: pick(['west-special'], 'prop'), wall: 'west-common-wall-', road: 'west-common-road-stone-', gate: 'west-common-wall-gate-h', tower: 'west-common-wall-tower-round' },
    east:  { houses: pick(['east-base'], 'house').filter(noWater), specials: pick(['east-special'], 'special').concat(pick(['special-infra'], 'special', 'east').filter(noWater)),
             props: pick(['east-special'], 'prop'), wall: 'east-common-wall-', road: 'east-common-road-stone-', gate: 'east-common-wall-gate-h', tower: 'east-common-wall-tower' },
    elf:   { houses: pick(['west-elf'], 'house'), specials: pick(['west-elf'], 'special'), props: pick(['west-elf'], 'prop'),
             wall: 'west-elf-wall-', road: 'west-common-road-dirt-', gate: 'west-elf-wall-gate-h', tower: 'west-elf-wall-tower' },
    dwarf: { houses: pick(['west-dwarf'], 'house'), specials: pick(['west-dwarf'], 'special'), props: pick(['west-dwarf'], 'prop'),
             wall: 'west-dwarf-wall-', road: 'west-common-road-stone-', gate: 'west-dwarf-wall-gate-h', tower: 'west-dwarf-wall-tower' },
    orc:   { houses: pick(['west-orc'], 'house'), specials: pick(['west-orc'], 'special'), props: pick(['west-orc'], 'prop'),
             wall: 'west-orc-wall-', road: 'west-common-road-dirt-', gate: 'west-orc-gate-h', gateReplace: true, tower: null },
    arab:  { houses: pick(['arab-base'], 'house').filter(function (id) { return !/tent/.test(id); }), specials: pick(['arab-special'], 'special').filter(noWater),
             props: pick(['arab-special'], 'prop').concat(pick(['arab-base'], 'prop')), wall: 'arab-common-wall-', road: 'arab-common-road-stone-', gate: 'arab-common-wall-gate-h', tower: 'arab-common-wall-tower' }
  };
  // 码头、桥、渔家棚屋等需要水面，示范城镇里没有河，先排除
  function noWater(id) { var t = (M[id].tags || []).join(' '); return !/waterside|river_|deck_|on_water|stilts_water/.test(t) && !/dock|bridge|yupeng|noria/.test(id); }

  function scene(setName, seed) {
    var S0 = SETS[setName], R = rng(seed), GW = 22, GH = 15, gx = 11;
    var g = [], occ = [];
    for (var y = 0; y < GH; y++) { g.push([]); occ.push([]); for (var x = 0; x < GW; x++) {
      var wall = y === 0 || y === GH - 1 || x === 0 || x === GW - 1;
      var road = (x === gx && y > 0) || (y === 7 && x > 0 && x < GW - 1);
      g[y].push(wall ? 'w' : road ? '=' : '.'); occ[y].push(wall || road);
    } }
    function at(fn, x, y) { return x >= 0 && y >= 0 && x < GW && y < GH && fn(g[y][x], x, y) ? 1 : 0; }
    function dual(fn, prefix) {
      var out = [];
      for (var j = 0; j <= GH; j++) for (var i = 0; i <= GW; i++) {
        var m = at(fn, i - 1, j - 1) * 8 + at(fn, i, j - 1) * 4 + at(fn, i - 1, j) * 2 + at(fn, i, j);
        if (m) out.push({ id: prefix + bin(m), i: i, j: j, x: i * S - S / 2, bottom: j * S + S / 2, key: j * S + S / 2 });
      }
      return out;
    }
    // 南墙正中是城门：门洞那格既是墙也是路，路一直通到城外
    var ground = dual(function (c, x, y) { return c === '=' || (x === gx && y === GH - 1); }, S0.road);
    var items = dual(function (c) { return c === 'w'; }, S0.wall);
    var gy = GH - 1;
    if (S0.gateReplace) {
      items.forEach(function (it) { if (it.i === gx + 1 && it.j === gy && /0011$/.test(it.id)) it.id = S0.gate; });
    } else {
      var gm = M[S0.gate];
      items.push({ id: S0.gate, x: gx * S + S / 2 - gm.viewBox[2] / 2, bottom: (gy + 1) * S, key: (gy + 1) * S + 24.5 });
    }
    if (S0.tower) [[0, 0], [GW - 1, 0], [0, GH - 1], [GW - 1, GH - 1]].forEach(function (c) {
      var tm = M[S0.tower];
      items.push({ id: S0.tower, x: c[0] * S + S / 2 - tm.viewBox[2] / 2, bottom: (c[1] + 1) * S, key: (c[1] + 1) * S + 24.5 });
    });

    // 建筑：先特殊建筑，后民居；占地必须完全空闲，第一遍要求贴着道路，第二遍填空
    function fits(x, y, w, d) {
      if (x < 1 || y < 1 || x + w > GW - 1 || y + d > GH - 1) return false;
      for (var yy = y; yy < y + d; yy++) for (var xx = x; xx < x + w; xx++) if (occ[yy][xx]) return false;
      return true;
    }
    function touchesRoad(x, y, w, d) {
      for (var xx = x; xx < x + w; xx++) if (g[y + d] && g[y + d][xx] === '=') return true;   // 正面朝路
      for (var yy = y; yy < y + d; yy++) if (g[yy][x - 1] === '=' || g[yy][x + w] === '=') return true;
      return false;
    }
    function place(id, needRoad) {
      var fp = M[id].footprint, w = fp[0], d = fp[1], spots = [];
      for (var y = 1; y < GH - 1; y++) for (var x = 1; x < GW - 1; x++) if (fits(x, y, w, d) && (!needRoad || touchesRoad(x, y, w, d))) spots.push([x, y]);
      if (!spots.length) return false;
      var p = spots[Math.floor(R() * spots.length)];
      for (var yy = p[1]; yy < p[1] + d; yy++) for (var xx = p[0]; xx < p[0] + w; xx++) occ[yy][xx] = true;
      items.push({ id: id, x: p[0] * S, bottom: (p[1] + d) * S, key: (p[1] + d) * S });
      return true;
    }
    var specials = S0.specials.slice(); shuffle(specials, R);
    specials.slice(0, 9).forEach(function (id) { place(id, true); });
    S0.props.slice(0, 4).forEach(function (id) { place(id, true); });
    var houses = S0.houses.slice(), last = '';
    for (var pass = 0; pass < 2; pass++) for (var n = 0; n < 60; n++) {
      shuffle(houses, R);
      var id = houses[0] === last && houses.length > 1 ? houses[1] : houses[0];
      if (place(id, pass === 0)) last = id;
    }

    items.sort(function (a, b) { return a.key - b.key || a.x - b.x; });
    var body = ground.map(function (it) { return use(it.id, it.x, it.bottom); }).join('') +
      items.map(function (it) { return use(it.id, it.x, it.bottom); }).join('');
    var up = 150, vb = [-36, -up, GW * S + 72, GH * S + up + 120];
    document.getElementById('scene').innerHTML = '<svg xmlns="' + NS + '" viewBox="' + vb.join(' ') + '" width="' + Math.round(vb[2] * 0.9) + '">' + body + '</svg>';
  }
  function shuffle(a, R) { for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(R() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } }

  function atlas() {
    var fs = val('fs'), fr = val('fr'), fc = val('fc');
    var fx = val('fx'), fq = val('fq').trim().toLowerCase();
    var list = C.meta.filter(function (m) {
      return (!fs || m.style === fs) && (!fr || m.race === fr) && (!fc || m.category === fc) && (!fx || m.resource === fx) &&
        (!fq || m.id.toLowerCase().indexOf(fq) >= 0 || String(m.name_zh || m.name || '').indexOf(fq) >= 0 || String(m.subtype || '').indexOf(fq) >= 0);
    });
    document.getElementById('count').textContent = '共 ' + list.length + ' / ' + C.meta.length + ' 个';
    document.getElementById('atlas').innerHTML = list.map(function (m) {
      var W = m.viewBox[2], H = m.viewBox[3];
      return '<div class="card" data-id="' + m.id + '" style="cursor:zoom-in"><svg xmlns="' + NS + '" width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" overflow="visible"><use href="#' + m.id + '"/></svg>' +
        '<b>' + (m.name_zh || m.name || m.kind || '') + '</b><span>' + m.footprint.join('×') + (m.facility ? ' · ' + m.facility : '') +
        (m.resource ? ' · ' + m.resource : '') + (m.subtype ? ' / ' + m.subtype : '') + '</span><code>' + m.id + '</code></div>';
    }).join('');
  }
  function val(id) { return document.getElementById(id).value; }

  // 资源下拉、目录预览入口、点击放大
  var resSet = {}; C.meta.forEach(function (m) { if (m.resource) resSet[m.resource] = 1; });
  Object.keys(resSet).sort().forEach(function (r) { document.getElementById('fx').insertAdjacentHTML('beforeend', '<option>' + r + '</option>'); });
  var cnt = {}; C.meta.forEach(function (m) { cnt[m.dir] = (cnt[m.dir] || 0) + 1; });
  document.getElementById('dirs').innerHTML = C.dirs.map(function (d) {
    return '<a href="' + d + '/preview.html" target="_blank" style="padding:4px 10px;background:#f3ead4;border:1px solid #c9b994;color:#3a2c1e;text-decoration:none">' + d + ' <small>(' + (cnt[d] || 0) + ')</small></a>';
  }).join('') + '<a href="layout-preview.html" target="_blank" style="padding:4px 10px;background:#e3c47a;border:1px solid #c9b994;color:#3a2c1e;text-decoration:none">城镇布局生成预览</a>';
  document.getElementById('atlas').addEventListener('click', function (e) {
    var card = e.target.closest('.card'); if (!card) return;
    var m = M[card.getAttribute('data-id')], W = m.viewBox[2], H = m.viewBox[3], k = Math.min(4, 760 / Math.max(W, H));
    document.getElementById('zbox').innerHTML = '<svg xmlns="' + NS + '" width="' + Math.round(W * k) + '" height="' + Math.round(H * k) + '" viewBox="0 0 ' + W + ' ' + H + '" overflow="visible" style="background:#c9c79a"><use href="#' + m.id + '"/></svg>' +
      '<pre style="font-size:12px;white-space:pre-wrap">' + JSON.stringify(m, null, 1).replace(/</g, '&lt;') + '</pre>';
    document.getElementById('zoom').style.display = 'flex';
  });
  document.getElementById('zoom').addEventListener('click', function (e) { if (e.target.id === 'zoom') this.style.display = 'none'; });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') document.getElementById('zoom').style.display = 'none'; });

  function redraw() { scene(val('set'), +val('seed') || 1); }
  ['set', 'seed'].forEach(function (id) { document.getElementById(id).addEventListener('change', redraw); });
  ['fs', 'fr', 'fc', 'fx'].forEach(function (id) { document.getElementById(id).addEventListener('change', atlas); });
  document.getElementById('fq').addEventListener('input', atlas);
  var q = new URLSearchParams(location.search);
  if (q.get('set')) document.getElementById('set').value = q.get('set');
  if (q.get('cat')) document.getElementById('fc').value = q.get('cat');
  redraw(); atlas();
})();
