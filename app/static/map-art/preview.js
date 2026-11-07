/* 地图美术资产预览：读 manifest.json + 内嵌 map-art.svg，画图标墙与一张示意地图。
 * 示意地图是随机噪声地形，只为检验美术搭配；不读任何世界数据、不调用后端 API。 */
(function () {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const $ = (id) => document.getElementById(id);
  const svgEl = (tag, attrs) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); return n; };
  const use = (id, attrs) => { const u = svgEl('use', attrs || {}); u.setAttribute('href', '#' + id); return u; };
  const iconSvg = (id, vb) => { const s = svgEl('svg', { viewBox: '0 0 ' + vb[0] + ' ' + vb[1], 'aria-hidden': 'true' }); s.append(use(id, { width: vb[0], height: vb[1] })); return s; };
  function cell(id, vb, title, code) {
    const d = document.createElement('div'); d.className = 'ma-cell';
    d.append(iconSvg(id, vb));
    const b = document.createElement('b'); b.textContent = title; d.append(b);
    const c = document.createElement('code'); c.textContent = code || id; d.append(c);
    return d;
  }

  Promise.all([
    fetch('/static/map-art/manifest.json').then((r) => r.json()),
    fetch('/static/map-art/map-art.svg').then((r) => r.text()),
  ]).then(([m, sprite]) => {
    // 不能 display:none：部分浏览器不渲染隐藏子树里被 <use> 引用的符号。sprite 自身是 0×0 绝对定位。
    const holder = document.createElement('div'); holder.innerHTML = sprite;
    document.body.prepend(holder);
    const A = m.anchors;

    // 群系
    const bio = $('ma-biomes');
    m.biomes.palette.forEach((b, i) => {
      const d = document.createElement('div'); d.className = 'ma-cell';
      const sw = document.createElement('div'); sw.className = 'ma-swatch';
      sw.style.background = 'linear-gradient(135deg,' + b.fill + ' 0 62%,' + b.shade + ' 62% 100%)';
      const t = document.createElement('b'); t.textContent = b.name;
      const c = document.createElement('code'); c.textContent = i + ' · ' + b.fill;
      d.append(sw, t, c); bio.append(d);
    });
    // 城镇表
    const tt = $('ma-towns');
    tt.append(Object.assign(document.createElement('div'), { className: 'ma-th' }));
    m.towns.tiers.forEach((t) => tt.append(Object.assign(document.createElement('div'), { className: 'ma-th', textContent: t.name })));
    for (const [race, info] of Object.entries(m.towns.races)) {
      const r = document.createElement('div'); r.className = 'ma-race'; r.textContent = info.name;
      const s = document.createElement('small'); s.textContent = info.motif; r.append(s); tt.append(r);
      m.towns.tiers.forEach((t) => { const id = 'town-' + race + '-' + t.id; const c = cell(id, A.town.viewBox, '', id); c.querySelector('b').remove(); tt.append(c); });
    }
    for (const [k, n] of Object.entries(m.resources.kinds)) $('ma-res').append(cell('res-' + k, A.resource.viewBox, n));
    for (const [k, n] of Object.entries(m.resources.trade_kinds || {})) if (k !== 'note') { const c = cell('res-' + k, A.resource.viewBox, n); c.style.borderStyle = 'dashed'; $('ma-res').append(c); }
    for (const [k, d] of Object.entries(m.decorations || {})) if (k !== 'note') $('ma-deco').append(cell(d.symbol, d.viewBox, d.name));
    const catNames = { 'cat-food': '饮食', 'cat-produce': '蔬果作物', 'cat-herb': '草药', 'cat-alchemy': '炼金', 'cat-formula': '方剂公式',
      'cat-biology': '生物', 'cat-race': '种族', 'cat-character': '人物属性', 'cat-trait': '特质', 'cat-material': '材料', 'cat-tool': '工具工艺',
      'cat-society': '社会制度', 'cat-culture': '文学文化', 'cat-name': '人名', 'cat-eastern': '东方玄幻', 'cat-western': '西方魔幻', 'cat-physical': '物理',
      'cat-steam': '蒸汽朋克', 'cat-horror': '民俗恐怖', 'cat-generic': '其他' };
    for (const [id, n] of Object.entries(catNames)) $('ma-cats').append(cell(id, [24, 24], n));
    for (const [k, n] of Object.entries(m.trees.species)) $('ma-trees').append(cell('tree-' + k, A.tree.viewBox, n));
    for (const [k, n] of Object.entries(m.trees.fantasy_species || {})) if (k !== 'note') { const c = cell('tree-' + k, A.tree.viewBox, n); c.style.borderStyle = 'dashed'; $('ma-trees').append(c); }
    for (const [k, n] of Object.entries(m.marks)) $('ma-marks').append(cell('mark-' + k, A.mark.viewBox, n));
    for (const [k, n] of Object.entries(m.terrain)) $('ma-marks').append(cell('terrain-' + k, A.terrain.viewBox, n));
    // 道路
    for (const [k, r] of Object.entries(m.routes.kinds)) {
      const row = document.createElement('div'); row.className = 'ma-route';
      const name = document.createElement('b'); name.textContent = r.name;
      const s = svgEl('svg', { viewBox: '0 0 400 22', preserveAspectRatio: 'none' });
      s.append(svgEl('rect', { width: 400, height: 22, fill: '#d6cd92' }));
      const d = 'M0 11 C80 2 140 20 200 11 S320 2 400 11';
      if (r.casing) s.append(svgEl('path', { d, fill: 'none', stroke: r.casing, 'stroke-width': r.casing_width * 1.6, 'stroke-linecap': 'round' }));
      s.append(svgEl('path', { d, fill: 'none', stroke: r.stroke, 'stroke-width': r.width * 1.6, 'stroke-linecap': 'round', 'stroke-dasharray': (r.dash || []).map((x) => x * 1.6).join(' ') }));
      const c = document.createElement('code'); c.textContent = k;
      row.append(name, s, c); $('ma-routes').append(row);
    }

    // ---------- 示意地图 ----------
    const W = 960, H = 540, G = 8;  // 栅格步长（像素）
    const cols = W / G, rows = H / G;
    const biomeIndex = Object.fromEntries(m.biomes.palette.map((b, i) => [b.name, i]));
    function rng(seed) { let s = seed >>> 0; return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
    function noiseField(rand, scale) {
      const gw = Math.ceil(cols / scale) + 2, gh = Math.ceil(rows / scale) + 2, g = [];
      for (let i = 0; i < gw * gh; i++) g.push(rand());
      const sm = (t) => t * t * (3 - 2 * t);
      return (x, y) => { const fx = x / scale, fy = y / scale, ix = Math.floor(fx), iy = Math.floor(fy), tx = sm(fx - ix), ty = sm(fy - iy);
        const a = g[iy * gw + ix], b = g[iy * gw + ix + 1], c = g[(iy + 1) * gw + ix], d = g[(iy + 1) * gw + ix + 1];
        return a + (b - a) * tx + (c - a) * ty + (a - b - c + d) * tx * ty; };
    }
    function draw(seed) {
      $('ma-seed').textContent = 'seed ' + seed;
      const rand = rng(seed);
      const n1 = noiseField(rand, 22), n2 = noiseField(rand, 9), n3 = noiseField(rand, 4), nt = noiseField(rand, 30), np = noiseField(rand, 18);
      const elev = [], biome = [];
      for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) {
        const dx = (x / cols - .5) * 2, dy = (y / rows - .5) * 2;
        const e = n1(x, y) * .6 + n2(x, y) * .3 + n3(x, y) * .1 - (dx * dx * .55 + dy * dy * .75) * .55;
        elev.push(e);
        const lat = Math.abs(y / rows - .5) * 2;
        const temp = 1 - lat * .9 - Math.max(0, e - .45) * 1.4 + (nt(x, y) - .5) * .25;
        const prec = np(x, y) * .9 + .1;
        let b;
        if (e < .32) b = temp < .12 ? '海冰' : '海洋';
        else if (temp < .1) b = '冰原';
        else if (temp < .22) b = prec < .3 ? '寒漠' : '苔原';
        else if (temp < .4) b = prec < .35 ? '寒漠' : '针叶林';
        else if (temp < .68) b = prec < .25 ? '温带荒漠' : prec < .45 ? '草原' : prec < .85 ? '温带森林' : '温带雨林';
        else b = prec < .25 ? '热带荒漠' : prec < .45 ? '稀树草原' : prec < .7 ? '热带季雨林' : '热带雨林';
        if (b !== '海洋' && b !== '海冰' && e < .35 && prec > .55 && temp > .4) b = '湿地';
        biome.push(b);
      }
      const at = (x, y) => (x < 0 || y < 0 || x >= cols || y >= rows) ? -1 : y * cols + x;
      const land = (i) => i >= 0 && elev[i] >= .32;
      const map = $('ma-map'); map.replaceChildren();
      const pal = m.biomes.palette;
      // 1 群系色块（按行合并相同群系的连续格子以减少节点）
      const gBio = svgEl('g', { 'shape-rendering': 'crispEdges' });
      for (let y = 0; y < rows; y++) { let x0 = 0; for (let x = 1; x <= cols; x++) { if (x === cols || biome[at(x, y)] !== biome[at(x0, y)]) {
        gBio.append(svgEl('rect', { x: x0 * G, y: y * G, width: (x - x0) * G + .5, height: G + .5, fill: pal[biomeIndex[biome[at(x0, y)]]].fill })); x0 = x; } } }
      map.append(gBio);
      // 2 海岸线描边 + 浅水晕
      const coast = [], shallow = [];
      for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) { const i = at(x, y); if (!land(i)) continue;
        if (!land(at(x, y - 1))) coast.push('M' + x * G + ' ' + y * G + 'h' + G);
        if (!land(at(x, y + 1))) coast.push('M' + x * G + ' ' + (y + 1) * G + 'h' + G);
        if (!land(at(x - 1, y))) coast.push('M' + x * G + ' ' + y * G + 'v' + G);
        if (!land(at(x + 1, y))) coast.push('M' + (x + 1) * G + ' ' + y * G + 'v' + G); }
      for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) { const i = at(x, y); if (land(i)) continue;
        if (land(at(x + 1, y)) || land(at(x - 1, y)) || land(at(x, y + 1)) || land(at(x, y - 1))) shallow.push('M' + (x * G + G / 2) + ' ' + (y * G + G / 2) + 'h.1'); }
      map.append(svgEl('path', { d: shallow.join(''), stroke: '#c9dad2', 'stroke-width': 18, 'stroke-linecap': 'round', fill: 'none', opacity: .55 }));
      map.insertBefore(map.lastChild, gBio.nextSibling);
      map.append(svgEl('path', { d: coast.join(''), stroke: '#3b2a1e', 'stroke-width': 1.6, fill: 'none', 'stroke-linecap': 'round' }));
      // 3 山峰（只取高处）
      const gMtn = svgEl('g');
      for (let y = 1; y < rows - 1; y += 2) for (let x = 1; x < cols - 1; x += 2) { const i = at(x, y); if (!land(i)) continue; const e = elev[i];
        if (e > .58 && rand() < .7) gMtn.append(use(e > .7 ? 'terrain-snowpeak' : 'terrain-mountain', { x: x * G - 12, y: y * G - 16, width: 24, height: 18 }));
        else if (e > .5 && rand() < .25) gMtn.append(use('terrain-hill', { x: x * G - 12, y: y * G - 10, width: 24, height: 12 })); }
      // 4 森林（按群系配比挑树种，沿海热带改红树）
      const gTree = svgEl('g', { id: 'ma-layer-trees' });
      const pick = (weights) => { let r = rand(), acc = 0; for (const [k, w] of Object.entries(weights)) { acc += w; if (r <= acc) return k; } return Object.keys(weights)[0]; };
      const trees = [];
      for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) { const i = at(x, y); if (!land(i) || elev[i] > .58) continue; const b = biome[i];
        const dens = m.trees.density[b] || 0; if (!dens || rand() > dens * .55) continue;
        const coastal = !land(at(x + 1, y)) || !land(at(x - 1, y)) || !land(at(x, y + 1)) || !land(at(x, y - 1));
        const sp = coastal && m.trees.coastal_override[b] ? m.trees.coastal_override[b] : pick(m.trees.by_biome[b]);
        if (b === '湿地' && rand() < .4) { gMtn.append(use('terrain-marsh', { x: x * G - 8, y: y * G - 2, width: 16, height: 8 })); continue; }
        trees.push([y * G + rand() * G, x * G + rand() * G, sp]); }
      trees.sort((a, b) => a[0] - b[0]);
      for (const [ty, tx, sp] of trees) gTree.append(use('tree-' + sp, { x: tx - 5, y: ty - 12, width: 10, height: 12.5 }));
      // 5 城镇：在陆地上挑分散的点，种族按群系挑（演示用）
      const raceOf = (b, e) => e > .52 ? 'dwarf' : (b === '温带森林' || b === '温带雨林' || b === '热带雨林') ? 'elf' : (b === '草原' || b === '稀树草原' || b.indexOf('荒漠') >= 0 || b === '寒漠') ? 'orc' : b === '湿地' ? 'halfling' : 'human';
      const towns = [];
      for (let tries = 0; tries < 2000 && towns.length < 16; tries++) {
        const x = 2 + Math.floor(rand() * (cols - 4)), y = 2 + Math.floor(rand() * (rows - 4)), i = at(x, y);
        if (!land(i) || elev[i] > .66 || biome[i] === '冰原') continue;
        if (towns.some((t) => Math.hypot(t.x - x, t.y - y) < 13)) continue;
        towns.push({ x, y, race: raceOf(biome[i], elev[i]), biome: biome[i] });
      }
      const tiers = ['capital', 'city', 'city', 'town', 'town', 'town'];
      towns.forEach((t, k) => { t.tier = tiers[k] || (rand() < .5 ? 'town' : 'hamlet'); });
      // 6 道路：最近邻连接（王道连首都与城市，其余大路/小径）
      const gRoad = svgEl('g', { id: 'ma-layer-roads', fill: 'none', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' });
      const R = m.routes.kinds, linked = new Set();
      const roadPath = (a, b) => { const ax = a.x * G, ay = a.y * G, bx = b.x * G, by = b.y * G, mx = (ax + bx) / 2 + (rand() - .5) * 40, my = (ay + by) / 2 + (rand() - .5) * 40; return 'M' + ax + ' ' + ay + ' Q' + mx + ' ' + my + ' ' + bx + ' ' + by; };
      const lineOk = (a, b) => { for (let s = 1; s < 12; s++) { const x = Math.round(a.x + (b.x - a.x) * s / 12), y = Math.round(a.y + (b.y - a.y) * s / 12); if (!land(at(x, y))) return false; } return true; };
      const casingG = svgEl('g'), strokeG = svgEl('g');
      towns.forEach((a, ai) => {
        const near = towns.map((b, bi) => [Math.hypot(a.x - b.x, a.y - b.y), bi]).filter(([d, bi]) => bi !== ai && d < 40).sort((p, q) => p[0] - q[0]).slice(0, 2);
        for (const [d, bi] of near) { const key = Math.min(ai, bi) + '-' + Math.max(ai, bi); if (linked.has(key)) continue; linked.add(key);
          const b = towns[bi], big = (a.tier === 'capital' || a.tier === 'city') && (b.tier === 'capital' || b.tier === 'city');
          const kind = !lineOk(a, b) ? R.sea_route : big ? R.royal_road : d < 20 ? R.road : R.track;
          const p = roadPath(a, b);
          if (kind.casing) casingG.append(svgEl('path', { d: p, stroke: kind.casing, 'stroke-width': kind.casing_width }));
          strokeG.append(svgEl('path', { d: p, stroke: kind.stroke, 'stroke-width': kind.width, 'stroke-dasharray': kind.dash.join(' ') })); }
      });
      gRoad.append(casingG, strokeG);
      // 7 资源：按地形挑（演示用）
      const gRes = svgEl('g', { id: 'ma-layer-res' });
      const resFor = (b, e, coastal) => coastal ? (rand() < .5 ? 'fish' : 'salt') : e > .55 ? ['iron', 'coal', 'copper', 'tin', 'gold', 'rare_metals', 'stone'][Math.floor(rand() * 7)]
        : b.indexOf('森林') >= 0 || b.indexOf('雨林') >= 0 || b === '针叶林' ? (rand() < .6 ? 'timber' : 'herb') : b === '湿地' ? (rand() < .5 ? 'reed' : 'clay') : b === '草原' || b === '稀树草原' ? (rand() < .5 ? 'livestock' : 'wool') : 'grain';
      let placed = 0;
      for (let tries = 0; tries < 3000 && placed < 22; tries++) { const x = 2 + Math.floor(rand() * (cols - 4)), y = 2 + Math.floor(rand() * (rows - 4)), i = at(x, y);
        if (!land(i) || towns.some((t) => Math.hypot(t.x - x, t.y - y) < 4)) continue;
        const coastal = !land(at(x + 1, y)) || !land(at(x - 1, y)) || !land(at(x, y + 1)) || !land(at(x, y - 1));
        const unsurveyed = rand() < .3;
        const g = svgEl('g', { opacity: unsurveyed ? .5 : 1 });
        if (unsurveyed) g.append(svgEl('circle', { cx: x * G, cy: y * G, r: 10, fill: 'none', stroke: '#3b2a1e', 'stroke-width': 1, 'stroke-dasharray': '2 2' }));
        g.append(use('res-' + resFor(biome[i], elev[i], coastal), { x: x * G - 8, y: y * G - 8, width: 16, height: 16 }));
        gRes.append(g); placed++; }
      // 8 城镇图标 + 名字
      const gTown = svgEl('g');
      const sizes = Object.fromEntries(m.towns.tiers.map((t) => [t.id, t.size_px]));
      const names = ['灰港', '铁门', '松涛镇', '青风寨', '金波城', '鹰巢堡', '雾林', '石砧', '芦湾', '狼牙营', '白桦村', '琥珀渡', '星塔', '赤岩', '暮光城', '银溪'];
      towns.forEach((t, k) => { const s = sizes[t.tier] * 1.3; const px = t.x * G, py = t.y * G;
        gTown.append(use('town-' + t.race + '-' + t.tier, { x: px - s / 2, y: py - s * 28 / 32, width: s, height: s }));
        const label = svgEl('text', { x: px, y: py + 13, 'text-anchor': 'middle', 'font-size': t.tier === 'capital' ? 15 : t.tier === 'city' ? 13 : 11,
          'font-family': "'STKaiti','KaiTi','Songti SC','SimSun',serif", fill: '#2e1d12', stroke: '#f3e6c4', 'stroke-width': 3, 'paint-order': 'stroke', 'font-weight': t.tier === 'capital' ? 700 : 400 });
        label.textContent = (t.tier === 'capital' ? '★ ' : '') + names[k % names.length]; gTown.append(label); });
      // 9 罗盘 + 外框
      const frame = svgEl('g');
      frame.append(svgEl('rect', { x: 6, y: 6, width: W - 12, height: H - 12, fill: 'none', stroke: '#2e1d12', 'stroke-width': 2 }));
      frame.append(svgEl('rect', { x: 11, y: 11, width: W - 22, height: H - 22, fill: 'none', stroke: '#c9a14a', 'stroke-width': 1 }));
      const cx = W - 62, cy = 62, rose = svgEl('g', { stroke: '#2e1d12', 'stroke-width': 1 });
      rose.append(svgEl('circle', { cx, cy, r: 30, fill: '#f3e6c4', opacity: .85 }), svgEl('circle', { cx, cy, r: 24, fill: 'none', stroke: '#c9a14a' }));
      rose.append(svgEl('path', { d: `M${cx} ${cy - 28} L${cx + 6} ${cy} L${cx} ${cy + 28} L${cx - 6} ${cy} Z`, fill: '#7a1f22' }));
      rose.append(svgEl('path', { d: `M${cx - 28} ${cy} L${cx} ${cy - 6} L${cx + 28} ${cy} L${cx} ${cy + 6} Z`, fill: '#e9d9b4' }));
      const nlab = svgEl('text', { x: cx, y: cy - 33, 'text-anchor': 'middle', 'font-size': 12, fill: '#2e1d12', 'font-family': 'serif', stroke: 'none' }); nlab.textContent = 'N'; rose.append(nlab);
      frame.append(rose);
      // 标题卷轴 + 比例尺 + 海上装饰（只放在海面的空白处）
      frame.append(use('deco-cartouche', { x: 24, y: 20, width: 220, height: 66 }));
      const title = svgEl('text', { x: 134, y: 60, 'text-anchor': 'middle', 'font-size': 20, fill: '#2e1d12', 'font-family': "'STKaiti','KaiTi','Songti SC',serif", 'letter-spacing': 4 });
      title.textContent = '山川志异'; frame.append(title);
      frame.append(use('deco-scale', { x: 30, y: H - 40, width: 150, height: 20 }));
      const sc = svgEl('text', { x: 105, y: H - 44, 'text-anchor': 'middle', 'font-size': 11, fill: '#2e1d12', 'font-family': 'serif' }); sc.textContent = '五百里'; frame.append(sc);
      const seaSpots = [];
      for (let tries = 0; tries < 800 && seaSpots.length < 3; tries++) {
        const x = 6 + Math.floor(rand() * (cols - 12)), y = 12 + Math.floor(rand() * (rows - 20));
        let open = true;
        for (let dy = -4; dy <= 4 && open; dy++) for (let dx = -6; dx <= 6; dx++) if (land(at(x + dx, y + dy))) { open = false; break; }
        if (open && !seaSpots.some((p) => Math.hypot(p[0] - x, p[1] - y) < 25)) seaSpots.push([x, y]);
      }
      seaSpots.forEach(([x, y], k) => frame.append(k === 0 ? use('deco-seaserpent', { x: x * G - 32, y: y * G - 16, width: 64, height: 32 })
        : use(k === 1 ? 'deco-ship-west' : 'deco-ship-east', { x: x * G - 24, y: y * G - 20, width: 48, height: 40 })));
      map.append(gMtn, gTree, gRoad, gRes, gTown, frame);
      // 10 迷雾演示：这里只演示「传闻线索圈」的画法。雾本身不再用合成样张——
      // 真正的雾是浏览器按真实揭示几何画的（/static/map-art/fog-preview.html），
      // 两套算法并存只会展示过时效果，所以这张示意地图不画雾。
      const gFog = svgEl('g', { id: 'ma-layer-fog' });
      const hidden = towns[towns.length - 1] || { x: cols * .7, y: rows * .6 };
      const ang = rand() * Math.PI * 2, r = 90, off = r * (0.25 + 0.55 * rand());
      const qx = hidden.x * G + Math.cos(ang) * off, qy = hidden.y * G + Math.sin(ang) * off;
      gFog.append(svgEl('circle', { cx: qx, cy: qy, r, fill: 'rgba(201,161,74,.10)', stroke: '#c9a14a', 'stroke-width': 2, 'stroke-dasharray': '9 6' }));
      gFog.append(svgEl('circle', { cx: qx, cy: qy, r: 11, fill: '#2e1d12', stroke: '#c9a14a', 'stroke-width': 1.6 }));
      const qm = svgEl('text', { x: qx, y: qy + 5.5, 'text-anchor': 'middle', fill: '#f0d58a', 'font-size': 15, 'font-weight': 700 }); qm.textContent = '?'; gFog.append(qm);
      const ql = svgEl('text', { x: qx, y: qy - 17, 'text-anchor': 'middle', fill: '#f0e3c2', 'font-size': 14, 'font-style': 'italic', stroke: '#2a1d14', 'stroke-width': 3, 'paint-order': 'stroke' }); ql.textContent = '传闻中的沉船藏宝地'; gFog.append(ql);
      map.append(gFog);
      gFog.style.display = $('ma-show-fog').checked ? '' : 'none';
      gTree.style.display = $('ma-show-trees').checked ? '' : 'none';
      gRoad.style.display = $('ma-show-roads').checked ? '' : 'none';
      gRes.style.display = $('ma-show-res').checked ? '' : 'none';
    }
    let seed = 20261101;
    draw(seed);
    $('ma-reroll').onclick = () => { seed = Math.floor(Math.random() * 1e8); draw(seed); };
    for (const [box, layer] of [['ma-show-trees', 'ma-layer-trees'], ['ma-show-roads', 'ma-layer-roads'], ['ma-show-res', 'ma-layer-res'], ['ma-show-fog', 'ma-layer-fog']])
      $(box).onchange = () => { const l = $(layer); if (l) l.style.display = $(box).checked ? '' : 'none'; };
  }).catch((error) => {
    document.querySelector('main').prepend(Object.assign(document.createElement('p'), { textContent: '资产读取失败：' + error.message }));
  });
})();
