'use strict';
// 空间草稿（作者侧）：在地图工具页里圈建筑范围与用地，存成可继续编辑的草稿。
//
// 约定，和 map-import.js 保持一致：
//  · 底图就用那一页已经用受保护路由（带 token 头取 blob）画出来的 #map-preview，不另造底图，
//    也不把 token 拼进 URL。
//  · 圈点按**图像真实绘制矩形**换算经纬度：图是 max-width/max-height 等比缩放居中，
//    container 的 bounding box 四周有留白，用容器算会把 polygon 整体拉偏。
//  · 点地图取样 vs 画多边形是两种模式，互不误触：画的时候覆盖层接管点击并 stopPropagation。
//  · 客户端只发经纬度与用途；面积、冲突、供给、气候一律由服务端算，转换时服务端重采样。
//  · 切换地图或切换模式时，未保存的点/多边形会明确提示，绝不把 A 图的多边形存成 B 图的引用。
(function () {
  const KINDS = [['farmland', '农田（规划可用地）'], ['pasture', '牧场'],
                 ['mine', '矿山（仅意图）'], ['forest', '林地'],
                 ['wasteland', '荒地'], ['other', '其它']];
  const COLORS = {footprint: '#f0c46a', farmland: '#8fbf6a', pasture: '#b6cf7c',
                  mine: '#c08a6a', forest: '#4f8f6a', wasteland: '#9a9a8a',
                  other: '#8a9ab0'};

  // 与 map-import.js 共享的页面状态（那页是经典脚本，这些是全局绑定）
  const $ = (id) => document.getElementById(id);
  const el = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };
  const api = (path, method, body) => window.api(path, method, body);

  let drafts = [];          // 服务端空间草稿列表（summary）
  let current = null;       // 当前载入的草稿（含 footprint / land_use）
  let footprint = [];       // [[lon,lat], ...] 未保存或已载入
  let landUse = [];         // [{kind, vertices:[[lon,lat],...]}]
  let drawing = null;       // {target:'footprint'|'landUse', kind, points:[]}
  let mode = 'sample';      // sample | footprint | landUse
  let drawingMap = '';      // 暂存点所属的导入 id：换图就不许续画
  let lastSampling = null;  // {lon,lat,window_px} 作者在地图上选的点

  // 视图变换：世界上整幅图宽 = 360°，建筑范围只有几十 km²（< 0.01°），
  // 必须能放大到街区级别才画得出城镇边界。缩放/拖动同一个变换作用于图片与覆盖层，
  // 所以框选坐标自动跟随，不需要两套换算。
  let zoom = 1;
  let panX = 0, panY = 0;   // 相对“看全图”位置的像素偏移
  const MAX_ZOOM = 64;


  // ---------------------------------------------------------------- 页面骨架
  const block = el('div', undefined, 'map-block');
  block.id = 'spatial-block';
  // 高频圈选工具单独一栏，紧贴地图（见下方注入到 .map-stage）；面板里不再重复。
  const toolbar = el('div', undefined, 'sp-toolbar');
  toolbar.innerHTML = `
   <div class="sp-tool-group" role="group" aria-label="圈选模式">
    <button id="sp-mode-sample" class="map-btn" type="button">选点取样</button>
    <button id="sp-mode-footprint" class="map-btn" type="button">圈建筑范围</button>
    <button id="sp-mode-landuse" class="map-btn" type="button">圈用地</button>
   </div>
   <div class="sp-tool-group" role="group" aria-label="视图">
    <button id="sp-zoom-out" class="map-btn" type="button" aria-label="缩小">−</button>
    <button id="sp-zoom-fit" class="map-btn" type="button">全图</button>
    <button id="sp-zoom-in" class="map-btn" type="button" aria-label="放大">＋</button>
    <span id="sp-zoom-label" class="sp-zoom-label">全图</span>
   </div>
   <div class="sp-tool-group sp-draw-group" id="sp-draw-group" role="group" aria-label="当前一圈" hidden>
    <label class="sp-kind-field">用途<select id="sp-kind"></select></label>
    <button id="sp-finish" class="map-btn primary" type="button">结束</button>
    <button id="sp-undo" class="map-btn" type="button">撤销点</button>
    <button id="sp-clear-pts" class="map-btn" type="button">清除</button>
    <span id="sp-count" class="sp-zoom-label"></span>
   </div>`;
  block.innerHTML = `
   <h3 class="map-h3">空间草稿 · 建筑范围与用地</h3>
   <p class="map-muted">只圈建筑范围就能存；用地可选、稀疏，没画的区域算「未规划」。</p>
   <div class="map-block">
    <label class="map-field">已存空间草稿<select id="sp-drafts"></select></label>
    <div class="map-actions">
     <button id="sp-reload" class="map-btn" type="button">重新载入</button>
     <button id="sp-new" class="map-btn" type="button">清空并新建</button>
     <button id="sp-delete-footprint" class="map-btn" type="button">删除建筑范围</button>
    </div>
   </div>
   <label class="map-field">地点名<input id="sp-site" maxlength="80" placeholder="例如 观雨城"></label>
   <label class="map-field">所属区域<input id="sp-region" maxlength="80" placeholder="例如 河谷上游"></label>
   <div id="sp-geo" class="map-sample"></div>
   <div id="sp-landuse-list" class="map-sample"></div>
   <div class="map-actions">
    <button id="sp-save" class="map-btn primary" type="button">保存草稿</button>
    <button id="sp-convert" class="map-btn" type="button">转换成城镇草稿</button>
   </div>
   <p id="sp-status" class="map-status" role="status"></p>
   <details class="map-block" id="sp-author"><summary>作者声明：水源/材料/技术（默认用模板占位，不是地图事实）</summary>
    <p class="map-muted">地图不会告诉你这座城用什么水源、什么材料。下面这些要么是你写的，要么是导入模板的占位值；
     直接转换会标成模板默认值，不会当作地图事实。</p>
    <label class="map-check"><input id="sp-author-confirm" type="checkbox"> 我确认上面这些作者字段由我提供（不勾也可以先存草稿）</label>
    <label class="map-field">水源<select id="sp-water">
      <option value="river">河流</option><option value="lake">湖泊</option>
      <option value="spring">泉水</option><option value="well_field">井群</option>
      <option value="aqueduct">引水渠</option><option value="rain_cistern">雨窖</option></select></label>
    <label class="map-field">水源距离 km<input id="sp-water-km" type="number" step="0.1" min="0" max="200" value="1"></label>
    <label class="map-field">主要材料（逗号分隔）<input id="sp-materials" value="timber,stone"></label>
    <label class="map-field">技术（逗号分隔）<input id="sp-tech" value="timber_frame"></label>
   </details>
   <div id="sp-advanced">
    <details class="map-advanced"><summary>高级：作者显式腹地（可选，代替农田）</summary>
     <label class="map-field">腹地 km²<input id="sp-hinterland" type="number" step="1" min="0.5" max="20000"></label>
     <p class="map-muted">这等于直接把一块面积当粮食腹地，不经过农田规划；只在你有可靠依据时填。</p>
    </details>
   </div>`;
  // 圈选是高频率工具，必须贴着地图：把模式/缩放/结束这组按钮注入地图主区顶部，
  // 其余（草稿列表、地点名、地域、保存/转换、说明）留在下方面板。不遮地图、不进右玩家 UI。
  const stage = document.querySelector('#map-tools-root .map-stage');
  if (stage) {
    const head = stage.querySelector('.map-stage-head');
    if (head && head.parentNode) head.parentNode.insertBefore(toolbar, head.nextSibling);
    else stage.prepend(toolbar);
  }
  // 面板本体放到地图区下方（跨两列），保存/转换/草稿列表都在这边滚。
  const root = document.querySelector('#map-tools-root');
  if (root) root.append(block);
  const overlay = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  overlay.id = 'sp-overlay';
  overlay.setAttribute('preserveAspectRatio', 'none');
  overlay.setAttribute('aria-label', '建筑范围与用地');
  const wrap = $('map-canvas-wrap');
  wrap.append(overlay);

  const select = $('sp-kind');
  for (const [value, label] of KINDS) select.append(new Option(label, value));

  // ------------------------------------------------------------- 图像真实矩形
  // 图以 object-fit:contain 方式等比缩放居中，容器里会留白。画多边形必须用**图像实际
  // 占用的那个矩形**，否则经度/纬度整体偏移（尤其是容器很宽或很高的时候）。
  function imageRect() {
    const img = $('map-preview');
    if (!img || img.hidden || !img.naturalWidth) return null;
    const box = img.getBoundingClientRect();
    if (!box.width || !box.height) return null;
    const nw = img.naturalWidth, nh = img.naturalHeight;
    const style = window.getComputedStyle(img);
    const fit = style.objectFit;
    let width = box.width, height = box.height, left = box.left, top = box.top;
    if (fit === 'contain' || fit === 'scale-down') {
      const scale = Math.min(box.width / nw, box.height / nh);
      width = nw * scale;
      height = nh * scale;
      left = box.left + (box.width - width) / 2;
      top = box.top + (box.height - height) / 2;
    }
    // 再套一层视图变换：以图像中心为基准缩放，再加拖动偏移。图片与覆盖层共用它。
    const cx = left + width / 2, cy = top + height / 2;
    const w = width * zoom, h = height * zoom;
    return {left: cx - w / 2 + panX, top: cy - h / 2 + panY, width: w, height: h};
  }

  function toLonLat(event) {
    const rect = imageRect();
    if (!rect) return null;
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    if (x < -0.002 || x > 1.002 || y < -0.002 || y > 1.002) return null;
    const lon = -180 + 360 * Math.min(1, Math.max(0, x));
    const lat = 90 - 180 * Math.min(1, Math.max(0, y));
    return [Number(lon.toFixed(6)), Number(lat.toFixed(6))];
  }

  function toPixels(lon, lat) {
    const rect = imageRect();
    if (!rect) return null;
    return [rect.left + (lon + 180) / 360 * rect.width,
            rect.top + (90 - lat) / 180 * rect.height];
  }

  // 视图：图片按 zoom/pan 重新定位（覆盖层自己跟着算，所以框选不会偏）
  function applyView() {
    const img = $('map-preview');
    if (!img) return;
    if (zoom === 1 && !panX && !panY) {
      img.style.transform = '';
      img.style.transformOrigin = '';
    } else {
      img.style.transformOrigin = 'center center';
      img.style.transform = `translate(${panX}px, ${panY}px) scale(${zoom})`;
    }
    $('sp-zoom-label').textContent = zoom === 1 ? '全图'
      : `${zoom.toFixed(zoom < 4 ? 1 : 0)}×`;
    drawOverlay();
  }

  function setZoom(next, anchor) {
    const clamped = Math.min(MAX_ZOOM, Math.max(1, next));
    if (clamped === zoom) return;
    if (anchor) {
      // 以鼠标位置为中心缩放：让指针下的经纬度留在原地
      const before = toLonLat(anchor);
      const ratio = clamped / zoom;
      panX = (panX - 0) * ratio;
      panY = panY * ratio;
      zoom = clamped;
      const after = toLonLat(anchor);
      if (before && after) {
        const rect = imageRect();
        panX += (before[0] - after[0]) / 360 * rect.width;
        panY -= (before[1] - after[1]) / 180 * rect.height;
      }
    } else {
      const ratio = clamped / zoom;
      panX *= ratio; panY *= ratio;
      zoom = clamped;
    }
    if (zoom === 1) { panX = 0; panY = 0; }
    applyView();
  }

  // ------------------------------------------------------------------ 覆盖层绘制
  function drawOverlay() {
    overlay.replaceChildren();
    const img = $('map-preview');
    if (!img || img.hidden) return;
    const page = overlay.getBoundingClientRect();
    overlay.setAttribute('viewBox', `0 0 ${page.width || 1} ${page.height || 1}`);
    overlay.style.width = '100%';
    overlay.style.height = '100%';
    const poly = (vertices, color, dashed, close) => {
      if (!vertices || vertices.length < 2) return;
      const pts = vertices.map(([lon, lat]) => {
        const px = toPixels(lon, lat);
        return px ? `${(px[0] - page.left).toFixed(1)},${(px[1] - page.top).toFixed(1)}` : null;
      }).filter(Boolean);
      if (pts.length < 2) return;
      const node = document.createElementNS('http://www.w3.org/2000/svg', close ? 'polygon' : 'polyline');
      node.setAttribute('points', pts.join(' '));
      node.setAttribute('fill', close ? color + '33' : 'none');
      node.setAttribute('stroke', color);
      node.setAttribute('stroke-width', '2');
      if (dashed) node.setAttribute('stroke-dasharray', '5 4');
      overlay.append(node);
    };
    if (footprint.length) poly(footprint, COLORS.footprint, false, true);
    for (const entry of landUse) poly(entry.vertices, COLORS[entry.kind] || '#999', false, true);
    if (drawing) poly(drawing.points, drawing.target === 'footprint'
      ? COLORS.footprint : (COLORS[drawing.kind] || '#999'), true, false);
    for (const entry of landUse) {
      const first = toPixels(entry.vertices[0][0], entry.vertices[0][1]);
      if (!first) continue;
      const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      label.setAttribute('x', (first[0] - page.left + 4).toFixed(1));
      label.setAttribute('y', (first[1] - page.top + 12).toFixed(1));
      label.setAttribute('fill', COLORS[entry.kind] || '#999');
      label.setAttribute('font-size', '11');
      label.textContent = entry.kind;
      overlay.append(label);
    }
  }

  // ------------------------------------------------------------------- 模式切换
  function unsavedPoints() {
    return drawing ? drawing.points.length : 0;
  }

  function setMode(next) {
    if (next !== mode && unsavedPoints()) {
      const keep = window.confirm('当前这一圈还没结束（' + unsavedPoints()
        + ' 个点）。切换模式会丢弃它，继续吗？');
      if (!keep) return;
    }
    if (next !== mode) drawing = null;
    mode = next;
    for (const [id, value] of [['sp-mode-sample', 'sample'],
                               ['sp-mode-footprint', 'footprint'],
                               ['sp-mode-landuse', 'landUse']]) {
      $(id).classList.toggle('on', value === mode);
    }
    $('sp-draw-group').hidden = mode === 'sample';
    overlay.style.pointerEvents = mode === 'sample' ? 'none' : 'auto';
    wrap.classList.toggle('sp-drawing', mode !== 'sample');
    if (mode === 'landUse') drawing = {target: 'landUse', kind: select.value, points: []};
    if (mode === 'footprint') drawing = {target: 'footprint', kind: 'footprint', points: []};
    updateCount();
    drawOverlay();
  }

  function updateCount() {
    const n = unsavedPoints();
    $('sp-count').textContent = n ? n + ' 个点（需要至少 3 个）' : '';
  }

  // 覆盖层接管点击：画的时候取样 handler 收不到这次点击。
  overlay.addEventListener('click', (event) => {
    if (mode === 'sample') return;                 // pointer-events:none 时也不会到
    event.preventDefault();
    event.stopPropagation();
    const point = toLonLat(event);
    if (!point) return;
    if (!drawing) drawing = {target: mode === 'footprint' ? 'footprint' : 'landUse',
                             kind: mode === 'footprint' ? 'footprint' : select.value,
                             points: []};
    if (drawingMap && drawingMap !== (window.mapActiveId && window.mapActiveId())) {
      message('地图已换了一张：请先结束或清除这一圈，避免把上一个世界的点存到这张图。', true);
      return;
    }
    drawingMap = window.mapActiveId ? window.mapActiveId() : '';
    drawing.points.push(point);
    if (drawing.target === 'landUse') drawing.kind = select.value;
    updateCount();
    drawOverlay();
  }, true);

  function finishPolygon() {
    if (!drawing || drawing.points.length < 3) {
      message('至少点 3 个点才能形成一块范围。', true);
      return;
    }
    if (drawing.target === 'footprint') {
      if (footprint.length) {
        message('建筑范围只能有一块；要改请先「删除建筑范围」再重画。', true);
        return;
      }
      footprint = drawing.points.slice();
    } else {
      landUse.push({kind: drawing.kind, vertices: drawing.points.slice()});
    }
    drawing = null;
    setMode(mode === 'footprint' ? 'footprint' : mode);
    renderGeometry();
    drawOverlay();
    message('已加入这一块（还没保存到服务器）。');
  }

  // ---------------------------------------------------------------- 服务端交互
  function message(text, bad) {
    const out = $('sp-status');
    out.textContent = text || '';
    out.classList.toggle('map-warn-line', !!bad);
  }

  function currentImport() {
    return window.mapActiveId ? window.mapActiveId() : '';
  }

  function importRecord() {
    return window.mapActiveRecord ? window.mapActiveRecord() : null;
  }

  function draftBody() {
    const record = importRecord();
    if (!record) throw Error('先选一张已导入的地图');
    if (!footprint.length && !landUse.length) throw Error('至少要圈一块建筑范围或一块用地');
    const site = $('sp-site').value.trim();
    if (!site) throw Error('请填写地点名');
    const hint = Number($('sp-hinterland').value);
    const body = {
      site_name: site,
      footprint: footprint.length ? {vertices: footprint} : null,
      land_use: landUse.map((entry) => ({kind: entry.kind, vertices: entry.vertices})),
      environment_ref: {import_id: record.id, source_sha256: record.sha256},
      sampling: lastSampling
        ? {lon: lastSampling.lon, lat: lastSampling.lat,
           window_px: Number($('map-window').value)}
        : null,
    };
    if (hint > 0) body.hinterland_km2 = hint;
    return body;
  }

  async function refreshDrafts() {
    drafts = await api('/inner/spatial-drafts');
    const box = $('sp-drafts');
    const keep = current && drafts.some((row) => row.id === current.id) ? current.id : '';
    box.replaceChildren(new Option(drafts.length ? '（选择一份草稿）' : '（还没有空间草稿）', ''));
    for (const row of drafts) {
      const label = `${row.site_name} · ${row.supply.state === 'configured' ? '有供给' : '供给未配置'}`
        + ` · rev ${row.revision} · ${row.id}`;
      box.append(new Option(label, row.id));
    }
    box.value = keep;
  }

  async function loadDraft(id) {
    if (!id) return;
    if ((footprint.length || landUse.length || unsavedPoints())
        && current && current.id !== id
        && !window.confirm('当前未保存的图形会被替换，继续载入吗？')) return;
    const draft = await api('/inner/spatial-drafts/' + encodeURIComponent(id));
    current = draft;
    footprint = draft.footprint ? draft.footprint.vertices : [];
    landUse = (draft.land_use || []).map((entry) => ({kind: entry.kind,
                                                      vertices: entry.vertices}));
    drawing = null;
    drawingMap = '';
    $('sp-site').value = draft.site_name || '';
    if (draft.sampling) lastSampling = {lon: draft.sampling.lon, lat: draft.sampling.lat};
    // 载入草稿时把它自己声明的那张地图选出来：不拿当前图冒充草稿的来源。
    const ref = draft.environment_ref || {};
    if (ref.import_id && ref.import_id !== currentImport()) {
      await window.mapSelectForSpatial(ref.import_id);
    }
    renderGeometry();
    drawOverlay();
    message(`已载入 ${draft.id}（rev ${draft.revision}）。下次保存会带上这个版本号。`);
  }

  function renderGeometry() {
    const box = $('sp-geo');
    box.replaceChildren();
    const rows = [];
    rows.push(['建筑范围', footprint.length
      ? (current && current.footprint ? current.footprint.area_km2 + ' km²（已保存）'
        : '未保存（' + footprint.length + ' 个点）')
      : '未圈选（只圈建筑范围也能保存）']);
    const planned = landUse.reduce((sum, entry) => sum + (entry.area_km2 || 0), 0);
    rows.push(['用地块数', landUse.length + (planned ? `（约 ${planned.toFixed(2)} km²）` : '')]);
    const grid = el('div', '', 'map-kv');
    for (const [k, v] of rows) grid.append(el('span', k, 'map-kv-k'), el('span', v, 'map-kv-v'));
    box.append(grid);
    if (current && current.area_plan) {
      const plan = current.area_plan;
      box.append(el('p', plan.farmland_km2
        ? `已声明农田 ${plan.farmland_km2.toFixed(2)} km²：这是「规划可用地」的范围，不是已经产出的粮食。`
        : '还没有农田：草稿能存，但转换会缺「农田或腹地」。', 'map-muted'));
    }
    const list = $('sp-landuse-list');
    list.replaceChildren();
    landUse.forEach((entry, index) => {
      const row = el('div', '', 'map-actions');
      row.append(el('span', `${index + 1}. ${entry.kind}`
        + (entry.area_km2 ? ` · ${entry.area_km2} km²` : '（未保存）'), 'map-muted'));
      const drop = el('button', '删除', 'map-btn');
      drop.type = 'button';
      drop.onclick = () => { landUse.splice(index, 1); renderGeometry(); drawOverlay(); };
      const kind = new Option('改用途…', '');
      const change = document.createElement('select');
      change.append(kind);
      for (const [value, label] of KINDS) change.append(new Option(label, value));
      change.onchange = () => {
        if (!change.value) return;
        landUse[index].kind = change.value;
        renderGeometry();
        drawOverlay();
      };
      row.append(change, drop);
      list.append(row);
    });
    if (current && current.overlaps && current.overlaps.length) {
      list.append(el('p', '有范围重叠（服务端按顶点包含与边相交两路查得）：'
        + current.overlaps.map((c) => c.labels.join(' ↔ ')).join('；')
        + '。需要你重画，程序不会自动扣面积。', 'map-warn-line'));
    }
  }

  async function save() {
    let payload;
    try { payload = draftBody(); } catch (error) { message(error.message, true); return; }
    message('正在保存…');
    const result = current
      ? await api('/inner/spatial-drafts/' + encodeURIComponent(current.id), 'PUT',
        {expected_revision: current.revision, draft: payload})
      : await api('/inner/spatial-drafts', 'POST', {draft: payload});
    const draft = result.draft || result;
    current = draft;
    footprint = draft.footprint ? draft.footprint.vertices : footprint;
    landUse = (draft.land_use || []).map((entry) => ({kind: entry.kind,
                                                      vertices: entry.vertices,
                                                      area_km2: entry.area_km2}));
    await refreshDrafts();
    $('sp-drafts').value = draft.id;
    renderGeometry();
    drawOverlay();
    message(`已保存 ${draft.id}（rev ${draft.revision}）· `
      + (draft.supply.state === 'configured' ? '供给已配置' : '供给未配置：能存，转换会缺项'));
  }

  async function convert() {
    if (!current) { message('先保存草稿再转换。', true); return; }
    const report = await api('/inner/spatial-drafts/' + encodeURIComponent(current.id)
      + '/conversion');
    if (!report.ready) {
      const why = {
        farmland_or_hinterland: '还没有农田（或你显式填的腹地）',
        overlapping_farmland: '农田之间有重叠，需重画',
        footprint_overlaps_land_use: '建筑范围压到了用地范围，需重画',
        overlap_undetermined: '有范围太大，重叠检查没做完，需减少顶点后重画',
        sampling_point: '还没有在图上选取样点',
        story_base_revision_mismatch: '故事包已更新，请重新建草稿',
      };
      message('还不能转换：' + report.missing.map((m) => why[m] || m).join('；'), true);
      return;
    }
    const author = window.spatialAuthorFields ? window.spatialAuthorFields() : null;
    if (!author) { message('请先在下面填好水源/材料等作者字段。', true); return; }
    message('正在由服务端重新取样并转换…');
    const built = await api('/inner/spatial-drafts/' + encodeURIComponent(current.id)
      + '/town-input', 'POST', {expected_revision: current.revision, author});
    const town = await api('/inner/towns', 'POST', {input: built.input});
    current = await api('/inner/spatial-drafts/' + encodeURIComponent(current.id));
    renderGeometry();
    const out = $('sp-status');
    out.replaceChildren(
      el('p', `已转换并建城镇草稿 ${town.id}｜${built.input.site_name}`, 'map-ok'),
      el('p', '四阶段生成、校验、发布与绑定仍在「城镇创作」页完成；这里不发布、不移动故事包指针。',
        'map-muted'));
    const go = el('button', '去城镇创作 ›', 'map-btn');
    go.type = 'button';
    go.onclick = () => { window.__mapTownDraft = town.id; window.showPage('towns'); };
    out.append(go);
    window.__mapTownDraft = town.id;
  }

  // --------------------------------------------------------------------- 绑事件
  $('sp-mode-sample').onclick = () => setMode('sample');
  $('sp-mode-footprint').onclick = () => setMode('footprint');
  $('sp-mode-landuse').onclick = () => setMode('landUse');
  $('sp-finish').onclick = () => finishPolygon();
  $('sp-undo').onclick = () => {
    if (!drawing || !drawing.points.length) return;
    drawing.points.pop();
    updateCount();
    drawOverlay();
  };
  $('sp-clear-pts').onclick = () => {
    if (drawing) drawing.points = [];
    updateCount();
    drawOverlay();
  };
  $('sp-reload').onclick = () => window.safe(() => loadDraft($('sp-drafts').value));
  $('sp-drafts').onchange = () => window.safe(() => loadDraft($('sp-drafts').value));
  $('sp-new').onclick = () => {
    current = null; footprint = []; landUse = []; drawing = null; drawingMap = '';
    lastSampling = null;
    $('sp-site').value = ''; $('sp-hinterland').value = '';
    $('sp-drafts').value = '';
    renderGeometry(); setMode(mode); drawOverlay();
    message('已清空。画完记得保存成新草稿。');
  };
  $('sp-delete-footprint').onclick = () => {
    footprint = [];
    renderGeometry(); drawOverlay();
  };
  $('sp-save').onclick = () => window.safe(async () => {
    try { await save(); } catch (error) { message('保存失败：' + error.message, true); }
  });
  $('sp-convert').onclick = () => window.safe(async () => {
    try { await convert(); } catch (error) { message('转换失败：' + error.message, true); }
  });

  // 作者侧字段：地图不提供，所以默认是导入模板占位；作者确认后才当成作者声明。
  window.spatialAuthorFields = function () {
    const site = $('sp-site').value.trim();
    const region = $('sp-region').value.trim();
    if (!site || !region) { message('请填写地点名与所属区域。', true); return null; }
    const list = (id, fallback) => ($(id).value || '')
      .split(',').map((v) => v.trim()).filter(Boolean).slice(0, 8) || fallback;
    return {
      climate_source: 'measured', site_name: site, region,
      confirm_template: true,
      water: {source: $('sp-water').value, reliability: 0.8, daily_capacity_l: 200000,
              storage: 'none', distance_km: Number($('sp-water-km').value) || 1},
      transport: {road: 'track', water_route: false, portage: false,
                  seasonal_closed_days: 10, nearest_market_days: 2},
      materials: list('sp-materials', ['timber', 'stone']),
      technology: list('sp-tech', ['timber_frame']),
    };
  };

  // 地图页每次重画后回调（不在地图页里做别的事）
  window.__spatialDraw = function () {
    if (currentImport() !== drawingMap && unsavedPoints()) {
      drawing = null;
      message('地图换了，刚才没结束的那一圈已丢弃（不会把上一个世界的点存到这张图）。', true);
    }
    refreshDrafts().catch(() => {});
    renderGeometry();
    drawOverlay();
  };

  // 缩放与拖动：建筑范围只有几十 km²，不放大就画不出来。
  $('sp-zoom-in').onclick = () => setZoom(zoom * 2);
  $('sp-zoom-out').onclick = () => setZoom(zoom / 2);
  $('sp-zoom-fit').onclick = () => { zoom = 1; panX = 0; panY = 0; applyView(); };
  wrap.addEventListener('wheel', (event) => {
    if (event.target.closest && event.target.closest('#spatial-block')) return;
    if (!imageRect()) return;
    event.preventDefault();
    setZoom(zoom * (event.deltaY < 0 ? 1.25 : 0.8), event);
  }, { passive: false });

  let dragFrom = null;
  overlay.addEventListener('pointerdown', (event) => {
    if (event.button !== 0) return;
    dragFrom = { x: event.clientX, y: event.clientY, panX, panY };
  });
  wrap.addEventListener('pointermove', (event) => {
    if (!dragFrom) return;
    const dx = event.clientX - dragFrom.x, dy = event.clientY - dragFrom.y;
    if (Math.abs(dx) + Math.abs(dy) < 4) return;      // 小位移不算拖动，留给点击
    panX = dragFrom.panX + dx;
    panY = dragFrom.panY + dy;
    applyView();
  });
  wrap.addEventListener('pointerup', () => { dragFrom = null; });
  wrap.addEventListener('pointerleave', () => { dragFrom = null; });

  window.addEventListener('resize', () => applyView());
  setMode('sample');
  renderGeometry();
})();
