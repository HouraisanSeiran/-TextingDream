/* 地图主画面：作者原件与服务端已掩膜的旅程地图分容器挂载；底部对话栏覆盖地图。
 * 玩家地图只读当前 session 的 play-map 路由，永不读取作者原件。地点文字用 textContent。
 */
(function () {
  'use strict';
  const byId = (id) => document.getElementById(id);
  if (!byId('play') || !byId('surface')) return;          // 旧界面不在：静默跳过

  const TAB_KEY = 'textiledream-play-tab';
  const TABS = ['chat', 'history', 'items', 'other'];
  // 玩家地图节点存在时才安装缩放、服务端掩膜图与位置标记；作者地图另有宿主。
  const hasPlayerMap = Boolean(byId('play-map-img'));

  function el(tag, text, cls) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  }
  function say(text) {
    const box = byId('notice');
    if (!box) return;
    box.textContent = text;
    box.hidden = false;
    clearTimeout(say.timer);
    say.timer = setTimeout(() => { box.hidden = true; }, 9000);
  }
  const apiBase = (path, method, body) => api(path, method, body);

  // --------------------------------------------------------------- 底部对话层及页签
  function setDrawerOpen(open) {
    const drawer = byId('play-left'), handle = byId('conversation-handle');
    if (!drawer) return;
    if (!open && drawer.contains(document.activeElement) && document.activeElement !== handle) handle?.focus();
    drawer.classList.toggle('is-expanded', open);
    drawer.classList.toggle('is-collapsed', !open);
    if (handle) handle.setAttribute('aria-expanded', String(open));
    const content = byId('conversation-content');
    if (content) { content.inert = !open; content.setAttribute('aria-hidden', String(!open)); }
  }
  function showTab(name, persist) {
    const tab = TABS.includes(name) ? name : 'chat';
    setDrawerOpen(true);
    document.querySelectorAll('#play-tabs button').forEach((b) => {
      const on = b.dataset.tab === tab;
      b.classList.toggle('on', on);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    byId('surface').hidden = tab !== 'chat';
    for (const other of ['history', 'items', 'other']) {
      const panel = byId('panel-' + other);
      if (panel) panel.hidden = other !== tab;
    }
    if (persist) { try { localStorage.setItem(TAB_KEY, tab); } catch (error) { /* 忽略 */ } }
    if (tab === 'history') drawHistory();
    if (tab === 'items') drawItems();
    if (tab === 'other') drawOther();
  }

  function drawHistory() {
    const box = byId('panel-history');
    if (!box) return;
    // 历史面板里就放旧侧栏的存档 + 章节列表（app.js 已把 #surface-journeys 搬到这里），
    // 也由 render() 持续重画；这里只在页签打开时确保章节列表存在。
    if (!byId('conversations') && current) render();
  }

  // ------------------------------------------------------------------- 物品栏
  function drawItems() {
    const box = byId('panel-items');
    if (!box) return;
    box.replaceChildren();
    const head = el('div', undefined, 'panel-head');
    head.append(el('h3', '随身物品'));
    box.append(head);
    if (!current) {
      box.append(el('p', '选择或新建一段旅程后显示。', 'muted'));
      return;
    }
    const rewards = current.rewards;
    const names = current.inventory || [];
    if (rewards && rewards.wallet && rewards.wallet.length) {
      box.append(el('p', '钱货：' + rewards.wallet.map((w) => w.name + ' ' + w.amount + (w.unit || '')).join(' · '), 'muted'));
    }
    if (rewards && rewards.items && rewards.items.length) {
      for (const item of rewards.items) {
        const card = el('div', undefined, 'item-row');
        const hidden = item.identified === false;
        // 名称单独一段（可省略号 + title 全文），材质/品质/重量另起一段：
        // 长名只在短列表里收起，数量与状态永远完整可见。
        const name = el('strong', String(item.label || ''), 'item-name');
        name.title = [
          item.label,
          hidden ? '未鉴定' : item.material,
          hidden ? '' : item.quality,
          '重 ' + item.weight,
        ].filter(Boolean).join(' · ');
        card.append(name);
        const meta = [hidden ? '未鉴定' : '', hidden ? '' : item.material,
                      hidden ? '' : item.quality, '重 ' + item.weight];
        card.append(el('span', meta.filter(Boolean).join(' · '), 'item-meta'));
        if (!hidden && item.figures === 'visible_estimate') {
          card.append(el('small', '以上为可见估值，不含未披露的效果；不是最终裁定值'));
        }
        if (item.enchantments && item.enchantments.length) {
          card.append(el('small', '附魔：' + item.enchantments.map((e) => e.name + ' ' + e.level + '级').join('、')));
        }
        box.append(card);
      }
    } else if (names.length) {
      const list = el('ul', undefined, 'item-list');
      names.forEach((name) => list.append(el('li', name)));
      box.append(list);
    } else {
      box.append(el('p', '身上没有记下物品。', 'muted'));
    }
    const facts = el('details');
    facts.append(el('summary', '属性与当地环境'));
    const body = el('div');
    facts.append(body);
    const abilities = current.abilities;
    if (abilities) {
      const namesMap = { talent: '天赋', strength: '力量', agility: '敏捷', wisdom: '智慧', social: '社交', resilience: '韧性' };
      body.append(el('p', Object.entries(abilities.values).map(([k, v]) => (namesMap[k] || k) + ' ' + v).join(' · '), 'muted'));
      body.append(el('p', '血量 ' + abilities.health.current + '/' + abilities.health.maximum, 'muted'));
    }
    const geo = current.geography;
    if (geo && geo.coordinates) body.append(el('p', '经度、纬度：' + geo.coordinates.join(', '), 'muted'));
    if (geo && geo.environment) {
      body.append(el('p', '海拔 ' + geo.environment.elevation_m + 'm · 流域 ' + (geo.environment.basin || '未设定'), 'muted'));
    }
    box.append(facts);
  }

  // ------------------------------------------------------------------- 其他
  const OTHER_ENTRIES = [
    ['notebook', '知识点记录簿', '旅途里记下的条录，只列已公开的内容'],
    ['map', '旅程地图 · 旧图册', '旧设定里的示意坐标与图册（不是游玩地图）'],
    ['world-workshop', '世界创作', '世界观、地理、文明与故事包'],
    ['map-tools', '世界地图工具', '导入 civ-atlas 世界、选点、建城镇'],
    ['towns', '城镇创作', '四阶段城镇草稿与发布'],
    ['elements', '元素装配', '从本地百科库挑条目固定到故事包'],
    ['inner', '里层创作', '生成候选、审核、包版本与审计'],
    ['traces', '模型输入输出', '实际请求与响应（含隐藏设定）'],
    ['api', 'API 配置', '连接模型、密钥与并发'],
    ['settings', '设置', '阅读、上下文预算与通用语料'],
  ];
  function drawOther() {
    const box = byId('panel-other');
    if (!box) return;
    box.replaceChildren();
    const head = el('div', undefined, 'panel-head');
    head.append(el('h3', '其他'));
    box.append(head);
    const guide = el('details', undefined, 'other-help');
    guide.append(el('summary', '玩法与地图帮助'));
    guide.append(el('p', '作者地图显示世界原件；进入旅程后，右侧只请求服务器已遮罩的玩家地图。未关联地图时会明确提示，不显示作者全图。', 'muted'));
    guide.append(el('p', '作者地图可用滚轮缩放、拖动平移；需要圈地时，展开左侧「地图与圈地工具」。', 'muted'));
    guide.append(el('p', '关键动作由引擎给候选与成本，说一句话不会直接改状态；只说话的回合只会影响对话。', 'muted'));
    box.append(guide);
    const list = el('div', undefined, 'other-list');
    for (const [page, title, hint] of OTHER_ENTRIES) {
      const row = el('button', undefined, 'other-row');
      row.type = 'button';
      row.append(el('span', title), el('small', hint));
      row.onclick = () => safe(() => showPage(page));
      list.append(row);
    }
    box.append(list);
  }

  // ------------------------------------------------------------- 顶部 API 弹层
  // 表单本体始终只有一份（#api-form）。弹层打开时把它接到弹层里，关掉时**搬回**
  // 「其他 → API 配置」页，所以那一页不会变成只剩标题的空壳。
  function installApiPopover() {
    const pop = byId('api-pop'), form = byId('api-form'), toggle = byId('api-toggle');
    if (!pop || !form || !toggle) return;
    const page = byId('api');
    const home = form.parentElement;          // 旧页 #api 里原本的位置
    const wrap = el('div', undefined, 'api-pop-inner');
    wrap.append(el('p', '连接模型。密钥只存在本地服务内存：不回填、不进地址栏、不进日志。', 'muted'));
    const host = el('div');
    host.id = 'api-pop-host';          // 给个可识别的落点，便于对账表单去哪了
    wrap.append(host, el('p', '更多作者选项（并发、推理强度、超时）在左侧「其他 → API 配置」。', 'muted'));
    pop.append(wrap);
    if (page && !byId('api-moved-note')) {
      // 弹层开着的时候这一页仍然可用（表单被搬进弹层）；给一行说明，避免看着像坏了。
      const note = el('p', '配置表单可能在顶部弹层里：点顶部「⌁ API 配置」打开，关闭后会回到这里。密钥不回填、不显示，只保存在本次服务内存。', 'muted');
      note.id = 'api-moved-note';
      page.querySelector('.intro').append(note);
    }
    const setOpen = (open) => {
      pop.hidden = !open;
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (open) {
        if (form.parentElement !== host) {
          host.append(form);
          form.classList.add('api-form-compact');
        }
        if (typeof apiConfig === 'object' && apiConfig) safe(async () => { apiConfig = await api('/settings/api'); fillApi(); });
      } else if (home && form.parentElement === host) {
        // 关掉就搬回旧页：两个入口看到的是同一份表单，不是一个空壳加一份副本。
        home.append(form);
        form.classList.remove('api-form-compact');
      }
    };
    toggle.onclick = () => setOpen(pop.hidden);
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && !pop.hidden) setOpen(false);
    });
    document.addEventListener('pointerdown', (event) => {
      if (pop.hidden) return;
      if (pop.contains(event.target) || toggle.contains(event.target)) return;
      setOpen(false);
    });
    // 从「其他 → API 配置」这一页进来时同样把表单搬回页里，免得和弹层抢同一份 DOM。
    window.__closeApiPopover = () => setOpen(false);
  }

  function drawConnState(api) {
    const box = byId('conn-state');
    if (!box) return;
    const keyState = api.has_key ? '密钥已配置' : '未配置密钥';
    box.textContent = (api.offline ? '离线模式' : api.model) + ' · ' + keyState;
    box.classList.toggle('warn', !api.has_key && !api.offline);
    box.title = api.offline ? '离线模式：不调用远程 API' : ('模型 ' + api.model + ' · ' + keyState);
  }

  // ------------------------------------------------------------------- 右图
  // 视图（zoom/pan）与数据（每回合刷新）分开：回合推进只重画标记，resetView 才会复位。
  const view = { zoom: 1, x: 0.5, y: 0.5, fitted: false };
  let mapState = { status: 'loading', payload: null };
  let imageSeq = 0, mapLoading = false, pendingMap = false;

  function resetView() {
    if (!hasPlayerMap) return;
    view.zoom = 1; view.x = 0.5; view.y = 0.5; view.fitted = false;
    // 重置缩放、中心与已解码尺寸；图片和标记共用同一布局。
    applyTransform();
  }
  // 底图与覆盖层必须共用同一比例和位移：按 PNG 解码后的真实宽高等比放入视口；
  // bbox 只用于地点经纬度到图内坐标的映射，未解码时不猜测图像比例。
  function applyMapAspect() {
    const img = byId('play-map-img');
    const overlay = byId('play-map-overlay');
    if (!img) return false;
    const nw = img.naturalWidth, nh = img.naturalHeight;
    if (!nw || !nh) return false;
    const shape = nw + ' / ' + nh;
    if (img.style.aspectRatio !== shape) img.style.aspectRatio = shape;
    if (overlay) overlay.style.aspectRatio = shape;
    return true;
  }

  // contain 基准框：图片按真实宽高比等比居中；未解码时返回 null。
  function fitRect() {
    const wrap = byId('play-map-wrap'), img = byId('play-map-img');
    if (!wrap || !img) return null;
    const nw = img.naturalWidth, nh = img.naturalHeight;
    const cw = wrap.clientWidth, ch = wrap.clientHeight;
    if (!nw || !nh || !cw || !ch) return null;
    const scale = Math.min(cw / nw, ch / nh);
    const width = nw * scale, height = nh * scale;
    return { left: (cw - width) / 2, top: (ch - height) / 2, width, height };
  }

  function applyTransform() {
    if (!hasPlayerMap) return;
    const img = byId('play-map-img'), overlay = byId('play-map-overlay');
    applyMapAspect();
    const fit = fitRect();
    if (!img || !fit) {
      // 没有可用的真实比例：维持整块铺满，不猜比例。
      const size = 100 * view.zoom;
      for (const node of [img, overlay]) {
        if (!node) continue;
        node.style.width = size + '%'; node.style.height = size + '%';
        node.style.left = (50 - 0.5 * size) + '%';
        node.style.top = (50 - 0.5 * size) + '%';
      }
      drawOverlay();
      return;
    }
    // 在 contain 基准框上做 zoom/pan：zoom 缩放尺寸，view.x/y 是视口中心落在图内的比例。
    const width = fit.width * view.zoom, height = fit.height * view.zoom;
    const centerX = fit.left + fit.width / 2, centerY = fit.top + fit.height / 2;
    const left = centerX - view.x * width;
    const top = centerY - view.y * height;
    for (const node of [img, overlay]) {
      if (!node) continue;
      node.style.width = width + 'px';
      node.style.height = height + 'px';
      node.style.left = left + 'px';
      node.style.top = top + 'px';
    }
    drawOverlay();
  }

  function drawOverlay() {
    if (!hasPlayerMap) return;
    const overlay = byId('play-map-overlay');
    const img = byId('play-map-img');
    if (!overlay) return;
    // 安全边界：整张服务器掩膜底图已经在图像内；远端原件不会因前端缩放而下载。
    const W = (img && img.clientWidth) || 1000;
    const H = (img && img.clientHeight) || 1000;
    overlay.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    overlay.replaceChildren();
    if (!img || img.hidden || !img.naturalWidth || !img.naturalHeight) { overlay.hidden = true; return; }
    overlay.hidden = false;
    const payload = mapState.payload;
    if (!payload) return;
    const box = payload.basemap && payload.basemap.bbox;
    if (!box) return;
    const [lonMin, lonMax, latMin, latMax] = box;
    const spanLon = lonMax - lonMin || 1, spanLat = latMax - latMin || 1;
    const at = (lon, lat) => [((lon - lonMin) / spanLon) * W, ((latMax - lat) / spanLat) * H];
    const svgEl = (tag, attrs) => {
      const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
      Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
      return node;
    };
    for (const road of current?.exploration?.roads || []) {
      if (road.source !== 'civ_routes') continue;
      let segment = [];
      const draw = () => { if(segment.length > 1) overlay.append(svgEl('polyline', {
        points:segment.map(p => at(p[0],p[1]).join(',')).join(' '), fill:'none',
        stroke:road.kind.includes('sea')?'#779fb1':'#b58a57', 'stroke-width':3,
        'stroke-dasharray':road.kind.includes('sea')?'7 5':'none'})); };
      for(const point of road.points){
        if(segment.length && Math.abs(point[0]-segment.at(-1)[0])>180){draw();segment=[];}
        segment.push(point);
      }
      draw();
    }
    for (const place of payload.places || []) {
      if (place.town_id && place.id !== place.town_id) continue;
      if (place.lon === null || place.lat === null) continue;   // 不伪造位置
      const [x, y] = at(place.lon, place.lat);
      const state = place.state;
      if (state === 'current') continue;                        // 当前位置用倒三角画
      const node = svgEl('circle', {
        cx: x, cy: y, r: (state === 'explored' ? 9 : 7),
        fill: state === 'explored' ? '#dfe6ec' : 'none',
        stroke: state === 'explored' ? '#0d1418' : '#9fb0bd',
        'stroke-width': 2,
        'stroke-dasharray': state === 'known' ? '4 4' : 'none',
        opacity: state === 'explored' ? 0.92 : 0.8,
      });
      const title = svgEl('title', {});
      title.textContent = state === 'explored' ? place.name + '（已探索）' : place.name + '（已知未到）';
      node.append(title);
      const destination = current?.exploration?.destinations.find(d => d.id === place.id && d.can_move);
      if (destination) {
        node.setAttribute('role', 'button'); node.setAttribute('tabindex', '0');
        node.setAttribute('aria-label', '前往' + place.name); node.style.cursor = 'pointer';
        node.onclick = () => window.dispatchEvent(new CustomEvent('td-travel-select', {detail:place.id}));
        node.onkeydown = event => { if(event.key==='Enter'||event.key===' '){event.preventDefault();node.onclick();} };
      }
      overlay.append(node);
      if (state === 'known') {
        const label = svgEl('text', { x: x + 13, y: y + 5, fill: '#cfd8e0',
                                      'font-size': 22, stroke: '#0d1418',
                                      'stroke-width': 4, 'paint-order': 'stroke' });
        label.textContent = place.name;
        overlay.append(label);
      }
    }
    const player = payload.player;
    if (player && player.lon !== null && player.lat !== null) {
      const [x, y] = at(player.lon, player.lat);
      // 倒三角：底边在上、尖朝下。尖必须**落在**坐标点上：底边 y-28、尖 y，
      // 高度固定 28，这样尖端与 locationAt 算出的像素同一个点（不偏移 8px）。
      const marker = svgEl('path', {
        d: 'M ' + (x - 13) + ' ' + (y - 28) + ' L ' + (x + 13) + ' ' + (y - 28)
           + ' L ' + x + ' ' + y + ' Z',
        fill: '#b56f3f', stroke: '#fffaf0', 'stroke-width': 2.5,
      });
      const markerTitle = svgEl('title', {});
      markerTitle.textContent = '你在这里：' + player.name;
      marker.append(markerTitle);
      overlay.append(marker);
      // 标签不顶边被裁：默认在三角右上方；靠近画布上沿时翻到下方，靠近右沿时改左对齐。
      const labelW = 26 * String(player.name).length;
      const labelH = 30;
      const flipDown = y - labelH < 4;
      const flipLeft = x + 18 + labelW > W - 4;
      const label = svgEl('text', {
        x: flipLeft ? Math.max(4, x - 18 - labelW) : x + 18,
        y: flipDown ? y + 22 : y - 22,
        fill: '#f0e3c2', 'font-size': 26, stroke: '#0d1418',
        'stroke-width': 5, 'paint-order': 'stroke' });
      label.textContent = player.name;
      overlay.append(label);
    }
  }

  function setMapEmpty(text, canAuthor) {
    const box = byId('play-map-empty');
    if (!box) return;
    box.replaceChildren();
    box.hidden = false;
    box.append(el('p', text));
    if (canAuthor) {
      const go = el('button', '去世界地图工具关联 civ-atlas 数据', 'tb-btn');
      go.type = 'button';
      go.onclick = () => safe(() => showPage('map-tools'));
      box.append(go);
    }
  }

  function drawLegend(payload) {
    const legend = byId('play-map-legend');
    if (!legend) return;
    legend.replaceChildren();
    if (!payload || payload.status !== 'ok') return;
    const add = (cls, text) => {
      const span = el('span', undefined, 'legend-item');
      span.append(el('i', undefined, cls), el('span', text));
      legend.append(span);
    };
    add('legend-tri', '当前位置');
    add('legend-explored', '已探索');
    add('legend-known', '已知未到');
  }

  function drawMapNote(payload) {
    const note = byId('play-map-note');
    if (!note) return;
    // 主画面只保简洁状态；雾的算法口径/限制移到 tooltip 与「其他 → 帮助」，
    // 不让玩家每看一眼地图就读一段免责说明。
    const bits = [];
    if (payload && payload.status === 'ok') {
      bits.push('已探索 ' + Math.round(payload.fog.reveal_radius_km) + ' km');
      const extra = (payload.notes || []).length;
      if (extra) bits.push(extra + ' 条提示');
    }
    note.textContent = bits.join(' · ');
    note.title = payload && payload.status === 'ok'
      ? ['可见范围是按玩法设定算的可达距离，不是真实视线，也不含地形遮蔽。',
         '范围外的格子由服务器直接画成雾色，客户端没有那里的地形。',
         ...(payload.notes || [])].join('\n')
      : '';
  }

  async function loadMap(force) {
    if (!hasPlayerMap || window.__tdNativeMode !== 'player') return;
    if (!current) {
      if (mapLoading) pendingMap = true;
      return;
    }
    if (mapLoading) { pendingMap = true; return; }
    const sessionId = current.id;
    mapLoading = true;
    const seq = ++imageSeq;
    byId('play-map-img').hidden = true;
    byId('play-map-img').removeAttribute('src');
    byId('play-map-overlay').replaceChildren();
    byId('play-map-overlay').hidden = true;
    byId('play-map-empty').hidden = true;
    mapState = { status: 'loading', payload: null };
    drawLegend(null); drawMapNote(null);
    try {
      const payload = await apiBase('/sessions/' + sessionId + '/play-map');
      if (current?.id !== sessionId || window.__tdNativeMode !== 'player' || seq !== imageSeq) return;
      mapState = { status: payload.status, payload };
      drawLegend(payload);
      drawMapNote(payload);
      const img = byId('play-map-img');
      if (payload.status === 'ok' && payload.basemap.available) {
        // 页面 CSP 是 `img-src 'self' data:`：blob: 不在白名单里，直接 createObjectURL
        // 会让图片静默失败（naturalWidth 一直 0）。token 又不能进 URL。
        // 所以先自己 fetch（走 connect-src 'self'，头里带 token），再转 data: 给 img。
        const res = await fetch(payload.basemap.url, { headers: { 'X-TextileDream-Token': token } });
        if (seq !== imageSeq || current?.id !== sessionId || window.__tdNativeMode !== 'player') return;
        if (!res.ok) {
          img.hidden = true;
          drawOverlay();
          setMapEmpty('底图暂时取不到（' + res.status + '）。游玩与地点列表不受影响。', true);
        } else {
          const blob = await res.blob();
          if (seq !== imageSeq || current?.id !== sessionId || window.__tdNativeMode !== 'player') return;
          const dataUrl = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = () => reject(new Error('底图读取失败'));
            reader.readAsDataURL(blob);
          });
          if (seq !== imageSeq || current?.id !== sessionId || window.__tdNativeMode !== 'player') return;
          img.onload = () => { if (seq !== imageSeq || current?.id !== sessionId || window.__tdNativeMode !== 'player') return; img.hidden = false; byId('play-map-empty').hidden = true; applyTransform(); };
          img.onerror = () => { if (seq !== imageSeq || current?.id !== sessionId || window.__tdNativeMode !== 'player') return; img.hidden = true; drawOverlay(); setMapEmpty('底图无法显示（格式或 CSP 问题）', true); };
          img.src = dataUrl;
          if (!view.fitted) { view.fitted = true; }
        }
      } else {
        img.hidden = true;
        img.removeAttribute('src');
        const reason = payload.reason || '这张地图暂时不可用';
        setMapEmpty(reason, payload.status !== 'ok');
      }
      applyTransform();
    } catch (error) {
      if (current?.id !== sessionId || window.__tdNativeMode !== 'player' || seq !== imageSeq) return;
      mapState = { status: 'error', payload: null };
      byId('play-map-img').hidden = true;
      byId('play-map-img').removeAttribute('src');
      setMapEmpty('地图读取失败：' + error.message, true);
      drawOverlay();
    } finally {
      mapLoading = false;
      if (pendingMap) { pendingMap = false; void loadMap(true); }
    }
  }

  function installMapControls() {
    if (!hasPlayerMap) return;
    const byIdSafe = (id) => document.getElementById(id);
    const zoomBy = (factor) => {
      view.zoom = Math.min(8, Math.max(1, view.zoom * factor));
      if (view.zoom === 1) { view.x = 0.5; view.y = 0.5; }
      applyTransform();
    };
    const zoomIn = byIdSafe('play-map-zoom-in'), zoomOut = byIdSafe('play-map-zoom-out'), reset = byIdSafe('play-map-reset');
    if (zoomIn) zoomIn.onclick = () => zoomBy(1.25);
    if (zoomOut) zoomOut.onclick = () => zoomBy(0.8);
    if (reset) reset.onclick = () => { resetView(); };
    const wrap = byIdSafe('play-map-wrap');
    if (!wrap) return;
    wrap.addEventListener('wheel', (event) => {
      if (!mapState.payload || mapState.status !== 'ok') return;
      event.preventDefault();
      const box = wrap.getBoundingClientRect();
      const fx = (event.clientX - box.left) / Math.max(1, box.width);
      const fy = (event.clientY - box.top) / Math.max(1, box.height);
      const before = view.zoom;
      view.zoom = Math.min(8, Math.max(1, view.zoom * (event.deltaY > 0 ? 0.88 : 1.14)));
      if (view.zoom !== before) {
        // 缩放到鼠标位置：视口中心的经纬点保持不动。
        view.x = Math.min(1, Math.max(0, view.x + (fx - 0.5) * (1 - before / view.zoom)));
        view.y = Math.min(1, Math.max(0, view.y + (fy - 0.5) * (1 - before / view.zoom)));
        if (view.zoom === 1) { view.x = 0.5; view.y = 0.5; }
      }
      applyTransform();
    }, { passive: false });
    let drag = null;
    wrap.addEventListener('pointerdown', (event) => {
      if (view.zoom <= 1) return;
      drag = { x: event.clientX, y: event.clientY, vx: view.x, vy: view.y };
      try { wrap.setPointerCapture(event.pointerId); } catch (error) { /* 忽略 */ }
    });
    wrap.addEventListener('pointermove', (event) => {
      if (!drag) return;
      const box = wrap.getBoundingClientRect();
      if (!box.width || !box.height) return;
      view.x = Math.min(1, Math.max(0, drag.vx - (event.clientX - drag.x) / (box.width * view.zoom)));
      view.y = Math.min(1, Math.max(0, drag.vy - (event.clientY - drag.y) / (box.height * view.zoom)));
      applyTransform();
    });
    const stop = () => { drag = null; };
    wrap.addEventListener('pointerup', stop);
    wrap.addEventListener('pointercancel', stop);
    window.addEventListener('resize', () => { applyTransform(); });
    // 从 author -> player 时，地图视角从默认值开始，不沿用上一段旅程的 pan/zoom。
    window.addEventListener('td-native-mode', (event) => {
      imageSeq++;
      if (event.detail?.mode === 'player') {
        mapState = { status: 'loading', payload: null };
        const img = byId('play-map-img');
        if (img) { img.hidden = true; img.removeAttribute('src'); }
        byId('play-map-overlay')?.replaceChildren();
        byId('play-map-overlay').hidden = true;
        byId('play-map-empty').hidden = true;
        drawLegend(null); drawMapNote(null);
        resetView();
      }
      if (event.detail?.mode === 'author') {
        mapState = { status: 'no-session', payload: null };
        const img = byId('play-map-img');
        if (img) { img.hidden = true; img.removeAttribute('src'); }
        byId('play-map-overlay')?.replaceChildren();
        byId('play-map-overlay').hidden = true;
        byId('play-map-empty').hidden = true;
        drawLegend(null); drawMapNote(null);
      }
    });
  }

  // --------------------------------------------------------------- 接线旧逻辑
  function installPlayChrome() {
    const drawer = byId('play-left');
    const handle = byId('conversation-handle');
    const newButton = byId('play-new');
    const newSession = byId('new-session');
    // 对话层默认收起，留出完整地图；显式点击手记、页签或输入框才展开。
    setDrawerOpen(false);
    if (handle) handle.onclick = () => setDrawerOpen(!drawer.classList.contains('is-expanded'));
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && drawer?.classList.contains('is-expanded')
          && !byId('new-dialog')?.open && byId('api-pop')?.hidden) setDrawerOpen(false);
    });
    if (newButton && newSession) newButton.onclick = () => { newSession.click(); };
    const left = byId('workspace-new-chat');
    if (left && newSession) left.onclick = () => { newSession.click(); };
    const newWorld = byId('workspace-new-world');
    if (newWorld) newWorld.onclick = () => safe(async () => {
      if (window.__tdNativeMode !== 'author') await window.TDEnterAuthorMode();
      if (typeof window.TDOpenMapTools === 'function') window.TDOpenMapTools();
      const toolbox = byId('native-map-toolbox');
      // 宿主异步挂载，等其门户到位再展开参数；没有就保留工具打开态。
      const expand = () => {
        const toggle = toolbox?.querySelector('.dream-create-toggle');
        if (toggle && toggle.getAttribute('aria-expanded') !== 'true') toggle.click();
        return !!toggle;
      };
      if (!expand() && toolbox) {
        const observer = new MutationObserver(() => { if (expand()) observer.disconnect(); });
        observer.observe(toolbox, { childList: true, subtree: true });
        setTimeout(() => observer.disconnect(), 8000);
      }
    });
    const mapTools = byId('workspace-map-tools');
    const toolbox = byId('native-map-toolbox');
    if (mapTools && toolbox) {
      const tooltip = '在作者地图中查看和编辑圈地草稿';
      mapTools.title = tooltip;
      const setToolsOpen = (open) => {
        toolbox.hidden = !open;
        mapTools.setAttribute('aria-expanded', String(open));
        mapTools.classList.toggle('selected', open);
      };
      mapTools.onclick = () => {
        if (window.__tdNativeMode !== 'author') {
          void safe(async () => { await window.TDEnterAuthorMode(); setToolsOpen(true); });
        } else setToolsOpen(toolbox.hidden);
      };
      window.TDOpenMapTools = () => setToolsOpen(true);
    }
    const workspaceApi = byId('workspace-api');
    if (workspaceApi) workspaceApi.onclick = () => {
      const toggle = byId('api-toggle');
      if (toggle) toggle.click();
    };
    const back = byId('back-to-play');
    if (back) back.onclick = () => safe(() => showPage('surface'));
    const tabs = byId('play-tabs');
    if (tabs) {
      tabs.addEventListener('click', (event) => {
        const button = event.target.closest('button[data-tab]');
        if (button) { showTab(button.dataset.tab, true); }
      });
    }
    const form = byId('chat-form');
    if (form) form.addEventListener('focusin', () => setDrawerOpen(true));
    const message = byId('message');
    if (message) message.addEventListener('focus', () => setDrawerOpen(true));
    const elements = byId('workspace-elements');
    if (elements) elements.onclick = () => safe(async () => { await showPage('elements'); });
    const authorMap = byId('workspace-author-map');
    if (authorMap) authorMap.onclick = () => safe(async () => { await window.TDEnterAuthorMode(); authorMap.classList.add('selected'); });
    window.TDConversationDrawer = { open: () => setDrawerOpen(true), close: () => setDrawerOpen(false), toggle: () => setDrawerOpen(!drawer?.classList.contains('is-expanded')) };
    const otherButton = byId('workspace-other'), otherMenu = byId('workspace-other-menu');
    if (otherButton && otherMenu) {
      const menuEntries = [
        ['world-workshop', '世界创作'], ['notebook', '知识点记录簿'],
        ['towns', '城镇创作'], ['map-tools', '世界地图工具'],
        ['inner', '里层创作'], ['traces', '模型输入输出'],
        ['settings', '设置'], ['map', '旅程地图 · 旧图册'],
      ];
      for (const [target, title] of menuEntries) {
        const item = el('button', title, 'workspace-sub-link');
        item.type = 'button';
        item.onclick = () => safe(() => showPage(target));
        otherMenu.append(item);
      }
      otherButton.onclick = () => {
        otherMenu.hidden = !otherMenu.hidden;
        otherButton.setAttribute('aria-expanded', String(!otherMenu.hidden));
      };
    }
    window.TDWorkspaceSync = (sessions, api) => {
      const box = byId('workspace-sessions');
      if (box) {
        box.replaceChildren(...(sessions || []).map((session) => {
          const item = el('button', session.title || '未命名旅程');
          item.type = 'button';
          item.title = session.title || '未命名旅程';
          item.dataset.sessionId = session.id;
          item.classList.toggle('selected', !!current && session.id === current.id);
          item.onclick = () => safe(async () => { authorMap?.classList.remove('selected'); await loadSession(session.id); });
          return item;
        }));
        if (!(sessions || []).length) box.append(el('p', '还没有旅程。', 'muted'));
      }
      const hint = byId('workspace-api-hint');
      if (hint && api) hint.textContent = api.offline ? '离线模式' : api.has_key ? '已连接' : '待配置';
      const mode = byId('workspace-mode');
      if (mode && api) mode.textContent = api.offline ? '离线测试' : '已连接 · ' + (api.model || '模型');
    };
    window.TDWorkspaceSyncCurrent = (session) => {
      const box = byId('workspace-sessions');
      if (box) box.querySelectorAll('button').forEach((button) => button.classList.toggle('selected', button.dataset.sessionId === session?.id));
      const worldLabel = byId('world-label');
      if (worldLabel && session) worldLabel.textContent = session.world || '织梦';
      const badge = byId('play-badge');
      if (badge && session) badge.textContent = session.world || '织梦';
      const mapLegend = document.querySelector('.map-player-legend');
      if (mapLegend) mapLegend.hidden = !!session;
      const place = byId('play-place');
      if (place && session) place.textContent = [session.location, session.daytime].filter(Boolean).join(' · ');
      const summary = byId('conversation-summary');
      if (summary && session) summary.textContent = [session.current_scene || session.event?.title, session.location].filter(Boolean).join(' · ') || '继续这段旅程';
    };
    // 旧版把页签存在浏览器里；地图优先的新壳每次进入先显示对话页签。
    document.querySelectorAll('#legacy nav button[data-page="surface"]').forEach((b) => {
      b.onclick = () => safe(() => showPage('surface'));
    });
  }

  function installRenderHooks() {
    const base = render;
    render = function () {
      base.apply(this, arguments);
      const badge = byId('play-badge');
      if (badge && current) badge.textContent = current.world || 'TextingDream';
      const place = byId('play-place');
      if (place) {
        place.textContent = current ? '· ' + current.location + ' · ' + current.daytime : '';
      }
      if (byId('panel-items') && !byId('panel-items').hidden) drawItems();
      if (byId('panel-other') && !byId('panel-other').hidden) drawOther();
      if (byId('panel-history') && !byId('panel-history').hidden) drawHistory();
      safe(() => loadMap(false));
      return undefined;
    };
  }

  window.addEventListener('DOMContentLoaded', () => {
    try {
      installPlayChrome();
      installApiPopover();
      // 从「其他 → API 配置」进来时先关掉弹层，让表单又回到旧页里（同一份 DOM）。
      TDNav.register('api', {
        title: 'API 配置',
        enter: async () => {
          if (typeof window.__closeApiPopover === 'function') window.__closeApiPopover();
          apiConfig = await api('/settings/api');
          fillApi();
        },
      });
      installMapControls();
      installRenderHooks();
      showTab('chat', false);
      setDrawerOpen(false);
      // 顶栏连接状态：只显示状态值，不显示密钥。
      const baseBootstrap = bootstrap;
      bootstrap = async function () {
        const info = await baseBootstrap.apply(this, arguments);
        drawConnState(info.api);
        return info;
      };
      safe(async () => {
        const info = await api('/bootstrap');
        drawConnState(info.api);
      });
      safe(() => loadMap(false));
    } catch (error) {
      say('游玩界面未能挂载：' + error.message);
    }
  });

  // 供其它脚本（历史列表）用的最小接口。
  window.PlayUI = {
    showTab,
    resetView,
    refreshMap: () => loadMap(true),
    otherEntries: OTHER_ENTRIES.map((row) => row[0]),
  };
})();
