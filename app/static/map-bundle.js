/* Terragenesis layers inside the existing author world map. No player/full-map fallback. */
(function () {
  'use strict';
  const ROOT = '/inner/map-bundles';
  const WORLD = 'terragenesis-world-20261111';
  const GROUP_LABELS = { terrain: '地形 · 10 km', environment: '环境 / 雪冰', climate: '月气候 · 40 km', hydrology: '水文', ocean: '海洋 / 洋流 · 40 km', surface_water: '月湖 / 实际地表水（有限年）' };
  const PREVIEW_LABELS = {
    atlas: '自然总览', relief: '纯地形', 'climate-topics': '气候专题',
    'water-snow-topics': '水文雪冰', 'glacier-year-comparison': '冰川变化',
    'ocean-composite': '洋流叠图', 'ocean-theme': '洋流专题', 'ocean-overlay': '洋流透明层'
  };
  const FIELD_LABELS = {
    lake_stage_m: '本月实际水位', lake_volume_m3: '本月湖水库存', wet_mask: '月末实际湿湖',
    soil_mm: '月末陆地土壤水', runoff_mm: '月陆地产流', land_actual_et_mm: '月陆地实际蒸散',
    lake_actual_et_m3: '月湖蒸发（连通池需求归属）', terminal_overflow_m3: '月终端排出量',
    hillslope_discharge_m3_s: '坡面 Q（不含湖内部 / 溢流）', hillslope_q_support: '坡面 Q 有效支持',
    flow_wet_support: '月内曾淹没范围（裁河线）', direct_lake_liquid_m3: '月湖面液态直入',
    elevation_m: '海拔', bed_m: '基底海拔', surface_m: '路由地表高程', status: '陆海 / 地形状态码',
    temperature_c: '年均气温', precipitation_mm_yr: '年降水', biome: '潜在原生群系', biome_id: '潜在原生群系 ID',
    discharge_m3_s: '年均径流 Q', lake_id: '潜在填洼湖 ID（未验证）', lake_depth_m: '潜在填洼深度（非永久水深）',
    snow_swe_mm: '雪水当量', soil_water_mm: '土壤水', year_end_ice_swe_mm: '年末冰水当量',
    monthly_temperature_c: '月均气温', monthly_precipitation_mm: '月降水', monthly_wind_u_m_s: '月风 X 分量（东正）',
    monthly_wind_v_m_s: '月风 Z 分量（南正）', monthly_sst_c: '月海表温度 SST',
    monthly_u_m_s: '洋流 X 分量（东正）', monthly_v_m_s: '洋流 Z 分量（南正）', monthly_speed_m_s: '月流速',
    monthly_current_type: '月洋流类型码', ocean_mask: '海洋母网格掩膜',
    hydro_bed_m: '水文基底海拔', routing_surface_m: '冻结路由面（非当年冰面）', water_surface_m: '潜在水面（非永久水面）',
    drainage_area_m2: '汇水面积', receiver: '冻结路由接收格 ID', registered_lagoon: '登记潟湖标记',
    glacier_coverage_fraction: '冰川覆盖比例', glacier_simulated_fraction: '动力模拟范围比例',
    glacier_ice_surface_m: '年末选区冰面海拔', glacier_ice_thickness_m: '年末选区冰厚', glacier_ice_volume_m3: '年末选区冰体积',
    monthly_wind_x_m_s: '月风 X 分量（东正）', monthly_wind_z_m_s: '月风 Z 分量（南正）',
    monthly_discharge_m3_s: '月均径流 Q', monthly_runoff_mm: '月径流量', monthly_soil_water_mm: '月末土壤水',
    monthly_snow_swe_mm: '月末雪水当量', monthly_ice_swe_mm: '月末冰水当量', monthly_liquid_input_mm: '月液态水输入',
    monthly_sublimation_mm: '月升华量', monthly_actual_et_mm: '月实际蒸散', monthly_pet_mm: '月潜在蒸散',
    monthly_routed_volume_m3: '月路由体积', dynamic_glacier_mask: '冰川动力范围',
    final_ice_swe_mm: '年末冰水当量', final_snow_swe_mm: '年末雪水当量', final_soil_water_mm: '年末土壤水',
    initial_ice_swe_mm: '年初冰水当量', initial_snow_swe_mm: '年初雪水当量', initial_soil_water_mm: '年初土壤水',
    monthly_current_x_m_s: '洋流 X 分量（东正）', monthly_current_z_m_s: '洋流 Z 分量（南正）',
    monthly_sea_temperature_c: '月海表温度 SST', monthly_reference_sst_c: '参考海表温度', monthly_sst_anomaly_c: 'SST 距平（暖冷判据）',
    latitude_deg: '模型诊断纬度（非现实坐标）', longitude_deg: '模型诊断经度（非现实坐标）',
    biome_override_reason: '群系覆写原因码', wet_area_fraction: '海洋湿格面积比例', basin_id: '洋盆 ID'

  };
  const LIMITS = [
    '极干：61.2% 陆地年降水 < 1 mm；这是当前模拟产物，不是现实气候。',
    '湖泊仅是潜在填洼湖（filled，未验证），并非确认常年湖；地表水不代表永久水面。',
    '冰区以外未做冰川动力模拟；首年洋流尚未长期收敛，1 月包含初始化影响。',
    '地形约 10 km，气候与洋流母网格约 40 km；米制平面 X 向东、Z 向南，不是现实经纬度。',
    '月份 1–12 用于数值点检；洋流存图只有 1 / 7 月，其他月不补绘、不替代。缺值表示“未提供”，不是 0。'
  ];
  function node(tag, text, cls) {
    const e = document.createElement(tag);
    if (text !== undefined) e.textContent = text;
    if (cls) e.className = cls;
    return e;
  }
  function available(layer, month) {
    return !!layer && (!layer.months || !layer.months.length || layer.months.includes(Number(month)));
  }
  // rect is in natural image pixels; extent is planar X/Z metres. Never uses old lon/lat SVG.
  function imagePoint(image, frame, clientX, clientY, panel) {
    if (panel || !frame || !image.naturalWidth || !image.naturalHeight) return null;
    const box = image.getBoundingClientRect();
    if (!box.width || !box.height) return null;
    const px = (clientX - box.left) * image.naturalWidth / box.width;
    const py = (clientY - box.top) * image.naturalHeight / box.height;
    const r = frame.rect, w = frame.extent;
    if (!r || !w || !(r.width > 0 && r.height > 0)) return null;
    const u = (px - r.x) / r.width, v = (py - r.y) / r.height;
    if (u < 0 || u > 1 || v < 0 || v > 1) return null;
    return { x_m: w.x_min + u * (w.x_max - w.x_min), z_m: w.z_min + v * (w.z_max - w.z_min) };
  }
  function display(value, unit) {
    if (value === null || value === undefined || (typeof value === 'number' && !Number.isFinite(value))) return '未提供';
    if (typeof value === 'boolean') return value ? '是' : '否';
    let text;
    if (typeof value === 'number') {
      const magnitude = Math.abs(value);
      text = value === 0 ? '0' : magnitude < 0.001 || magnitude >= 1e6
        ? value.toExponential(3).replace(/\.?0+e/, 'e') : String(Number(value.toPrecision(4)));
    } else text = typeof value === 'object' ? JSON.stringify(value) : String(value);
    return text + (unit ? ' ' + unit : '');
  }
  function mount(host) {
    let disposed = false, detail = null, layers = [], imageEpoch = 0, pointEpoch = 0, loadEpoch = 0, imageController = null;
    let zoom = 1, lastPoint = null;
    const urls = new Set();
    const active = () => !disposed && window.__tdNativeMode === 'author';
    const shell = node('section', undefined, 'map-bundle');
    shell.setAttribute('aria-label', '世界地图');
    const bar = node('div', undefined, 'map-bundle-bar');
    bar.append(node('strong', '世界地图'));
    const layerSelect = node('select');
    layerSelect.setAttribute('aria-label', '地图图层');
    const layerLabel = node('label', '图层'); layerLabel.append(layerSelect);
    const month = node('select'); month.setAttribute('aria-label', '月份');
    for (let m = 1; m <= 12; m++) { const o = node('option', m + ' 月'); o.value = String(m); month.append(o); }
    month.value = '1';
    const monthLabel = node('label', '月份'); monthLabel.append(month);
    bar.append(layerLabel, monthLabel);
    const overlays = node('div', undefined, 'map-bundle-overlays');
    const overlayChecks = new Map();
    const minus = node('button', '−'), plus = node('button', '＋'), reset = node('button', '复位');
    minus.setAttribute('aria-label', '缩小世界地图'); plus.setAttribute('aria-label', '放大世界地图');
    for (const b of [minus, plus, reset]) b.type = 'button';
    bar.append(minus, plus, reset, overlays);
    const body = node('div', undefined, 'map-bundle-body');
    const viewport = node('div', undefined, 'map-bundle-viewport');
    const plane = node('div', undefined, 'map-bundle-plane');
    const image = node('img', undefined, 'map-bundle-base'); image.hidden = true; image.draggable = false;
    const overlayImages = node('div'); plane.append(image, overlayImages); viewport.append(plane);
    const inspector = node('aside', undefined, 'map-bundle-inspector'); inspector.setAttribute('aria-label', '地点环境点检');
    const inspectTitle = node('h3', '地点点检');
    const inspectBody = node('div', '点击地图有效区域查看米制坐标与当前月环境；专题拼图不支持定位。');
    inspector.append(inspectTitle, inspectBody); body.append(viewport, inspector);
    const info = node('details', undefined, 'map-bundle-info');
    info.append(node('summary', '来源、图层与工程限制'));
    const limits = node('ul', undefined, 'map-bundle-warnings');
    LIMITS.forEach(text => limits.append(node('li', text))); info.append(limits);
    const metadata = node('div'); info.append(metadata);
    const status = node('div', '正在读取世界地图…', 'map-bundle-status'); status.setAttribute('role', 'status');
    shell.append(bar, body, status, info);
    function tell(text, error) { if (!active()) return; status.textContent = text; status.dataset.error = String(!!error); }
    function revoke() { for (const url of urls) URL.revokeObjectURL(url); urls.clear(); }
    function clearImages() {
      image.hidden = true; image.removeAttribute('src'); image.onload = null; image.onerror = null;
      overlayImages.replaceChildren(); revoke();
    }
    function renderPoint(data) {
      inspectBody.replaceChildren();
      const coords = node('p', 'X ' + Math.round(lastPoint.x_m) + ' m · Z ' + Math.round(lastPoint.z_m) + ' m · ' + month.value + ' 月');
      inspectBody.append(coords);
      for (const name of Object.keys(GROUP_LABELS)) {
        const group = data.groups && data.groups[name];
        if (name === 'surface_water' && !group) continue;
        inspectBody.append(node('h4', GROUP_LABELS[name]));
        if (name === 'surface_water') inspectBody.append(node('small', '本年供水而非永久河槽认证；坡面 Q 不含湖内部，溢流为独立净转移示意。'));
        if (name === 'hydrology' && data.groups?.surface_water) inspectBody.append(node('small', '历史无湖诊断，非含湖最终总流量。'));
        if (group) inspectBody.append(node('small', '最近存储格；数值未插值。时间口径见字段提示及来源详情。'));
        if (!group || !group.values || !Object.keys(group.values).length) { inspectBody.append(node('p', '未提供')); continue; }
        const dl = node('dl');
        for (const [key, value] of Object.entries(group.values)) {
          const field = detail?.groups?.[name]?.fields?.[key];
          const contextual = name === 'surface_water' ? { lake_depth_m: '本月实际湖水深', receiver: '真实床坡面接收格', basin_id: '真实床湖盆 ID' } : {};
          const label = node('dt', contextual[key] || FIELD_LABELS[key] || group.labels?.[key] || key);
          label.title = key + (field?.time_semantics ? ' · ' + field.time_semantics : '') + (group.sampling ? ' · ' + group.sampling : '');
          let shown = display(value, group.units?.[key]);
          if (value !== null && value !== undefined && key === 'status') {
            const statuses = ['未准备', '界外', '未知', '海洋', '封闭低于海平面（非确认湖）', '陆地'];
            shown = statuses[value] === undefined ? shown : statuses[value] + '（' + value + '）';
          }
          if (value !== null && value !== undefined && (key === 'biome' || key === 'biome_id')) {
            const biome = detail?.stable_biome_ids?.[value];
            if (biome) shown = biome + '（' + value + '；潜在群系）';
          }
          const output = node('dd', shown);
          output.title = (value === null || value === undefined ? '未提供' : typeof value === 'object' ? JSON.stringify(value) : String(value)) + (group.units?.[key] ? ' ' + group.units[key] : '');
          dl.append(label, output);
        }
        inspectBody.append(dl);
      }
      if (data.warnings?.length) {
        const warnings = node('ul', undefined, 'map-bundle-warnings');
        data.warnings.forEach(w => warnings.append(node('li', typeof w === 'string' ? w : JSON.stringify(w))));
        inspectBody.append(warnings);
      }
    }
    async function queryPoint(point) {
      if (!active()) return;
      lastPoint = point;
      const seq = ++pointEpoch;
      inspectBody.textContent = '正在读取地点环境…';
      try {
        const data = await api(ROOT + '/' + encodeURIComponent(WORLD) + '/point', 'POST', { ...point, month: Number(month.value) });
        if (active() && seq === pointEpoch) renderPoint(data);
      } catch (error) { if (active() && seq === pointEpoch) inspectBody.textContent = '点检失败：' + error.message; }
    }
    // Metadata adapter is kept separate from DOM / mode ownership.
    function configure(data) {
      detail = data;
      layers = previewLayers(data);
      layerSelect.replaceChildren(); overlays.replaceChildren(); overlayChecks.clear();
      for (const layer of layers) {
        if (!layer.overlay) {
          const option = node('option', layer.title); option.value = layer.key; layerSelect.append(option);
        } else {
          const label = node('label'); const check = node('input'); check.type = 'checkbox';
          label.append(check, node('span', layer.title)); overlays.append(label); overlayChecks.set(layer.key, check);
          check.onchange = () => { void refresh(); };
        }
      }
      layerSelect.value = layers.find(l => !l.overlay)?.key || '';
      metadata.replaceChildren();
      if (data.groups?.surface_water) {
        limits.replaceChildren();
        [LIMITS[0], '实际月湖是空库存有限首年月水账，非长期常年认证；旧潜在湖图层仅历史参考。', LIMITS[2], LIMITS[3],
          '新月湖图仅显式存图月份可用；其他月仅数值点检，不补绘、不替代。坡面 Q 不含湖内，溢流为净转移示意。']
          .forEach(text => limits.append(node('li', text)));
      }
      metadata.append(node('p', 'Terragenesis · ' + (data.title || data.id || WORLD)));
      metadata.append(node('p', data.groups?.surface_water
        ? '时间口径：有限无闰首年；新月湖河基于真实床面和空库存月水账。坡面 Q 不含湖内部，溢流为独立净转移示意；旧水文 / 潜在湖 / 洋流合成图仅历史参考，不是永久水道认证。'
        : '时间口径：有限无闰 365 天诊断首年；月气候为月均或月累计，雪/冰/土壤水为月末存量，年均 Q 为全年路由体积 / 365 天。底图/水系保留冻结拓扑，不用当年冰面重路由；非真实日期天气。'));
      const list = node('ul');
      for (const layer of layers) list.append(node('li', layer.title + (layer.panel ? ' · 专题拼图，不可点检' : ' · 米制地图') + (layer.months?.length ? ' · 存图月份 ' + layer.months.join('/') : ' · 静态图')));
      metadata.append(list);
      const provenance = node('pre', JSON.stringify({ producer: data.producer, coordinate_system: data.coordinate_system, grid: data.grid, groups: data.groups, limits: data.limits, history: data.history }, null, 2));
      if (data.warnings?.length) {
        const notes = node('ul', undefined, 'map-bundle-warnings');
        data.warnings.forEach(w => notes.append(node('li', typeof w === 'string' ? w : JSON.stringify(w))));
        metadata.append(notes);
      }
      metadata.append(provenance);
      void refresh();
    }
    function updateAvailability() {
      for (const option of layerSelect.children) {
        const layer = layers.find(l => l.key === option.value); option.disabled = !available(layer, month.value);
      }
      for (const layer of layers.filter(l => l.overlay)) {
        const check = overlayChecks.get(layer.key); check.disabled = !available(layer, month.value);
        const selected = layers.find(l => l.key === layerSelect.value);
        check.disabled = check.disabled || !!selected?.panel;
        check.parentElement.title = check.disabled ? '此月未提供存图，或当前为专题拼图；不会用其他月份代替' : '';
      }
    }
    async function blobImage(layer, seq, target) {
      const res = await fetch(previewUrl(layer, Number(month.value)), {
        headers: { 'X-TextileDream-Token': window.__textileDreamToken || '' }, signal: imageController.signal
      });
      if (!res.ok) throw new Error(layer.title + ' HTTP ' + res.status);
      const blob = await res.blob();
      if (!active() || seq !== imageEpoch) return false;
      const url = URL.createObjectURL(blob); urls.add(url);
      target.src = url;
      return true;
    }
    async function refresh() {
      const seq = ++imageEpoch; ++pointEpoch;
      if (imageController) imageController.abort();
      imageController = new AbortController(); clearImages(); updateAvailability();
      if (!active()) return;
      const layer = layers.find(l => l.key === layerSelect.value);
      if (!layer) { tell('此世界没有可显示的地图存图。', true); return; }
      if (!available(layer, month.value)) {
        tell('此图层未提供 ' + month.value + ' 月存图；洋流仅 1 / 7 月。请选择其他图层或月份。'); return;
      }
      image.alt = layer.title; image.dataset.panel = String(layer.panel);
      image.onload = () => { if (active() && seq === imageEpoch) image.hidden = false; };
      image.onerror = () => { if (active() && seq === imageEpoch) { image.hidden = true; tell('图层无法显示（格式或 CSP），请检查服务配置后重试。', true); } };
      tell('正在读取 ' + layer.title + '…');
      try {
        if (!await blobImage(layer, seq, image)) return;
        let overlayCount = 0;
        if (!layer.panel) for (const overlay of layers.filter(l => l.overlay)) {
          const check = overlayChecks.get(overlay.key);
          if (!check.checked || !available(overlay, month.value)) continue;
          const img = node('img', undefined, 'map-bundle-overlay'); img.alt = overlay.title;
          // Stored transparent art can have a different title/margin; align its map rect, not full PNG edges.
          const b = layer.frame?.rect, o = overlay.frame?.rect;
          if (!b || !o || !layer.size || !overlay.size) continue;
          const sx = b.width / o.width, sy = b.height / o.height;
          img.style.left = ((b.x - o.x * sx) / layer.size[0] * 100) + '%';
          img.style.top = ((b.y - o.y * sy) / layer.size[1] * 100) + '%';
          img.style.width = (overlay.size[0] * sx / layer.size[0] * 100) + '%';
          img.style.height = (overlay.size[1] * sy / layer.size[1] * 100) + '%';
          if (await blobImage(overlay, seq, img)) { overlayImages.append(img); overlayCount++; }
          else return;
        }
        if (!active() || seq !== imageEpoch) return;
        tell(layer.title + ' · ' + (layer.months?.length ? month.value + ' 月存图' : '静态图；数值点检 ' + month.value + ' 月') + (layer.panel ? ' · 专题拼图，禁用坐标点检与透明层' : ' · X 东 / Z 南（m），点击点检') + (overlayCount ? ' · 透明层 ' + overlayCount : ''));
      } catch (error) { if (active() && seq === imageEpoch && error.name !== 'AbortError') tell('图层读取失败：' + error.message, true); }
    }
    function setZoom(next) { zoom = Math.max(1, Math.min(5, next)); plane.style.width = (zoom * 100) + '%'; }
    minus.onclick = () => setZoom(zoom / 1.25); plus.onclick = () => setZoom(zoom * 1.25);
    reset.onclick = () => { setZoom(1); viewport.scrollLeft = 0; viewport.scrollTop = 0; };
    layerSelect.onchange = () => { void refresh(); };
    month.onchange = () => { void refresh(); if (lastPoint) void queryPoint(lastPoint); };
    image.onclick = event => {
      if (!active() || image.hidden) return;
      const layer = layers.find(l => l.key === layerSelect.value);
      const point = imagePoint(image, layer?.frame, event.clientX, event.clientY, layer?.panel);
      if (point) void queryPoint(point);
      else tell(layer?.panel ? '专题拼图不可坐标点检；请选择地理底图。' : '请点击地图框内，边距、标题与图例不属于世界坐标。');
    };
    const retry = node('button', '重新读取地图'); retry.type = 'button'; retry.onclick = () => { void start(); }; bar.append(retry);
    async function start() {
      if (!active()) return;
      const seq = ++loadEpoch;
      tell('正在读取世界地图…');
      try { const data = await api(ROOT + '/' + encodeURIComponent(WORLD)); if (active() && seq === loadEpoch) configure(data); }
      catch (error) { if (seq === loadEpoch) tell('世界地图不可用：' + error.message, true); }
    }
    if (active()) { host.replaceChildren(shell); void start(); }
    return { unmount() {
      if (disposed) return; disposed = true; ++imageEpoch; ++pointEpoch;
      if (imageController) imageController.abort(); clearImages();
      image.onclick = null; host.replaceChildren();
    } };
  }
  // Exact backend metadata conversion lives here (not a second map projection).
  function previewLayers(data) {
    return (data.previews || []).map(preview => {
      const extent = preview.world_extent_m || data.world_extent_m;
      const rect = preview.map_rect;
      return {
        key: preview.key, title: preview.status === 'history-reference-only' || preview.surface_water_identity
          ? (preview.title || preview.key) : (PREVIEW_LABELS[preview.key] || preview.title || preview.key), months: preview.months,
        panel: !preview.georeferenced, overlay: preview.key === 'ocean-overlay', size: preview.image_size,
        frame: preview.georeferenced && rect && extent ? {
          rect, extent: { x_min: extent[0], z_min: extent[1], x_max: extent[2], z_max: extent[3] }
        } : null
      };
    });
  }
  function previewUrl(layer, month) { return '/api' + ROOT + '/' + encodeURIComponent(WORLD) + '/preview/' + encodeURIComponent(layer.key) + '?month=' + month; }
  window.TDMapBundle = Object.freeze({ mount, imagePoint, available, display });
})();
