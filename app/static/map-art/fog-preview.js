// 玩家地图迷雾的独立预览：模拟 play-ui.js 的「底图 + 雾 canvas + SVG 叠层」三层结构。
(function () {
  'use strict';
  const params = new URLSearchParams(location.search);
  const W = Number(params.get('w')) || 620, H = Number(params.get('h')) || 420;
  const base = '/static/map-art/fog-fixtures/';
  const svgEl = (tag, attrs) => {
    const n = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v));
    return n;
  };
  function render(card, region, zoom, showFog) {
    const wrap = card.querySelector('.wrap');
    const img = wrap.querySelector('img'), canvas = wrap.querySelector('canvas'), svg = wrap.querySelector('svg');
    const nw = region.basemap.width, nh = region.basemap.height;
    const s = Math.min(W / nw, H / nh) * zoom;
    const rect = { width: nw * s, height: nh * s, left: (W - nw * s) / 2, top: (H - nh * s) / 2 };
    for (const n of [img, svg]) {
      n.style.left = rect.left + 'px'; n.style.top = rect.top + 'px';
      n.style.width = rect.width + 'px'; n.style.height = rect.height + 'px';
    }
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    canvas.hidden = !showFog;
    const t0 = performance.now();
    if (showFog) window.TDMapFog.paint(canvas, { box: region.basemap.bbox, reveal: region.fog.reveal,
      cloudDeg: region.fog.cloud_deg, rect, scale: dpr });
    card.querySelector('.ms').textContent = Math.round(performance.now() - t0) + ' ms';
    // 叠层：与 play-ui.js 相同的坐标映射
    const [lonMin, lonMax, latMin, latMax] = region.basemap.bbox;
    const sw = rect.width, sh = rect.height;
    svg.setAttribute('viewBox', '0 0 ' + sw + ' ' + sh);
    svg.replaceChildren();
    const at = (lon, lat) => [(lon - lonMin) / (lonMax - lonMin) * sw, (latMax - lat) / (latMax - latMin) * sh];
    for (const p of region.places) {
      if (p.state === 'current') continue;
      const [x, y] = at(p.lon, p.lat);
      svg.append(svgEl('circle', { cx: x, cy: y, r: p.state === 'explored' ? 6 : 5,
        fill: p.state === 'explored' ? '#dfe6ec' : 'none', stroke: p.state === 'explored' ? '#0d1418' : '#3a2a1c',
        'stroke-width': 2, 'stroke-dasharray': p.state === 'known' ? '4 4' : 'none' }));
      const t = svgEl('text', { x: x + 9, y: y + 4, fill: '#2b1e12', 'font-size': 13, stroke: '#f3ead6',
        'stroke-width': 3, 'paint-order': 'stroke' });
      t.textContent = p.name; svg.append(t);
    }
    for (const c of region.clues) {
      const [x, y] = at(c.lon, c.lat);
      const deg = c.radius_km / 111.195;
      const rx = deg / Math.max(0.02, Math.cos(c.lat * Math.PI / 180)) / (lonMax - lonMin) * sw;
      const ry = deg / (latMax - latMin) * sh;
      svg.append(svgEl('ellipse', { cx: x, cy: y, rx, ry, fill: 'rgba(201,161,74,.10)', stroke: '#c9a14a',
        'stroke-width': 2.5, 'stroke-dasharray': '10 7' }));
      svg.append(svgEl('circle', { cx: x, cy: y, r: 11, fill: '#2e1d12', stroke: '#c9a14a', 'stroke-width': 2 }));
      const q = svgEl('text', { x, y: y + 5.5, 'text-anchor': 'middle', fill: '#f0d58a', 'font-size': 15, 'font-weight': 700 });
      q.textContent = '?'; svg.append(q);
      const l = svgEl('text', { x, y: y - 17, 'text-anchor': 'middle', fill: '#f0e3c2', 'font-size': 13,
        stroke: '#2a1d14', 'stroke-width': 3, 'paint-order': 'stroke', 'font-style': 'italic' });
      l.textContent = c.label; svg.append(l);
    }
    const [px, py] = at(region.player.lon, region.player.lat);
    svg.append(svgEl('path', { d: `M ${px - 9} ${py - 20} L ${px + 9} ${py - 20} L ${px} ${py} Z`,
      fill: '#b56f3f', stroke: '#fffaf0', 'stroke-width': 2 }));
  }
  fetch(base + 'regions.json').then((r) => r.json()).then((regions) => {
    const grid = document.getElementById('grid');
    const cards = regions.map((region) => {
      const card = document.createElement('div');
      card.className = 'card';
      card.innerHTML = '<h2></h2><div class="wrap"><img alt=""><canvas></canvas><svg></svg></div>';
      card.querySelector('h2').innerHTML = region.title + ' · 半径 ' + region.fog.reveal_radius_km + ' km <span class="ms"></span>';
      const wrap = card.querySelector('.wrap');
      wrap.style.setProperty('--w', W + 'px'); wrap.style.setProperty('--h', H + 'px');
      card.querySelector('img').src = base + region.image;
      grid.append(card);
      return [card, region];
    });
    const draw = () => {
      const z = Number(document.getElementById('zoom').value), f = document.getElementById('show-fog').checked;
      cards.forEach(([c, r]) => render(c, r, z, f));
      document.body.dataset.ready = '1';
    };
    document.getElementById('zoom').oninput = draw;
    document.getElementById('show-fog').onchange = draw;
    Promise.all(cards.map(([c]) => c.querySelector('img').decode().catch(() => {}))).then(draw);
  });
})();
