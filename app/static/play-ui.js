/* 地图主画面 + 故事手记。作者原件与服务端已掩膜的旅程地图分容器挂载；
 * 故事手记收起时是地图底部的一条，展开后占满整块地图区（三栏：旅程存档 / 正文 / 信息栏）。
 * 玩家地图只读当前 session 的 play-map 路由，永不读取作者原件。地点文字用 textContent。
 */
(function () {
  'use strict';
  const byId = (id) => document.getElementById(id);
  if (!byId('play') || !byId('surface')) return;          // 旧界面不在：静默跳过

  const LAYOUT_KEY = 'textiledream-chat-layout';
  // 玩家地图节点存在时才安装缩放、服务端掩膜图与位置标记；作者地图另有宿主。
  const hasPlayerMap = Boolean(byId('play-map-img'));
  const narrow = () => window.matchMedia('(max-width: 1100px)').matches;

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

  // ------------------------------------------------------- 故事手记：展开 = 占满地图区
  function setDrawerOpen(open) {
    const drawer = byId('play-left'), handle = byId('conversation-handle');
    if (!drawer) return;
    if (!open && drawer.contains(document.activeElement)) handle?.focus();
    if (!open) closePop();
    drawer.classList.toggle('is-expanded', open);
    drawer.classList.toggle('is-collapsed', !open);
    if (handle) handle.setAttribute('aria-expanded', String(open));
    const content = byId('conversation-content');
    if (content) { content.inert = !open; content.setAttribute('aria-hidden', String(!open)); }
    // 展开时地图被完全盖住：不让它继续接键盘焦点。
    const map = byId('play-right');
    if (map) { map.inert = open; map.setAttribute('aria-hidden', String(open)); }
    if (open) { syncSidePanels(); scrollStory(false); }
    else if (hasPlayerMap) requestAnimationFrame(applyTransform);
  }

  // 正文滚到底：加载旅程与发送后。force=false 时只在玩家本来就在底部附近时跟随。
  function scrollStory(force) {
    const box = byId('surface');
    if (!box) return;
    const near = box.scrollHeight - box.scrollTop - box.clientHeight < 160;
    if (force || near || !scrollStory.done) {
      requestAnimationFrame(() => { box.scrollTop = box.scrollHeight; });
      scrollStory.done = true;
    }
  }
  window.TDScrollStory = scrollStory;

  // ------------------------------------------------------- 左栏（存档）与右栏（信息）的开关
  // 宽屏时三栏并排、开关写进本地；窄屏时两侧变成覆盖在正文上的抽屉，默认收起。
  let layout = { rail: true, info: true };
  try { Object.assign(layout, JSON.parse(localStorage.getItem(LAYOUT_KEY) || '{}')); } catch (error) { /* 忽略 */ }
  let narrowOpen = { rail: false, info: false };
  function syncSidePanels() {
    const drawer = byId('play-left');
    if (!drawer) return;
    const small = narrow();
    const rail = small ? narrowOpen.rail : layout.rail;
    const info = small ? narrowOpen.info : layout.info;
    drawer.classList.toggle('rail-off', !rail);
    drawer.classList.toggle('info-off', !info);
    drawer.classList.toggle('is-narrow', small);
    byId('rail-toggle')?.setAttribute('aria-expanded', String(rail));
    byId('info-toggle')?.setAttribute('aria-expanded', String(info));
  }
  function toggleSide(which) {
    if (narrow()) {
      narrowOpen = { rail: false, info: false, [which]: !narrowOpen[which] };
    } else {
      layout[which] = !layout[which];
      try { localStorage.setItem(LAYOUT_KEY, JSON.stringify(layout)); } catch (error) { /* 忽略 */ }
    }
    syncSidePanels();
  }
  function closeNarrowSides() {
    if (!narrow() || (!narrowOpen.rail && !narrowOpen.info)) return false;
    narrowOpen = { rail: false, info: false };
    syncSidePanels();
    return true;
  }

  // ------------------------------------------------------- 输入栏浮层（AI 起草 / 想做别的事）
  const POP_TOOLS = { 'reply-direction-panel': 'tool-draft', 'demo-intent': 'tool-intent' };
  let openPop = null;
  function closePop() {
    if (!openPop) return;
    const card = byId(openPop);
    if (card) card.hidden = true;
    byId(POP_TOOLS[openPop])?.setAttribute('aria-expanded', 'false');
    byId(POP_TOOLS[openPop])?.classList.remove('on');
    byId('chat-form')?.classList.remove('has-pop');
    openPop = null;
  }
  function showPop(id) {
    const card = byId(id);
    if (!card) return;
    if (openPop === id) { closePop(); return; }
    closePop();
    card.hidden = false;
    openPop = id;
    byId(POP_TOOLS[id])?.setAttribute('aria-expanded', 'true');
    byId(POP_TOOLS[id])?.classList.add('on');
    byId('chat-form')?.classList.add('has-pop');
    card.dispatchEvent(new Event('td-pop-open'));
  }
  window.TDComposerPop = { open: showPop, close: closePop };

  function installComposer() {
    for (const [pop, tool] of Object.entries(POP_TOOLS)) {
      const button = byId(tool);
      if (button) button.onclick = () => showPop(pop);
    }
    byId('composer-pop')?.addEventListener('click', (event) => {
      if (event.target.closest('[data-pop-close]')) closePop();
    });
    document.addEventListener('pointerdown', (event) => {
      if (!openPop) return;
      if (event.target.closest('#composer-pop, .composer-tools, dialog')) return;
      closePop();
    });
    // 输入框随内容增高（1–8 行），不再一开始就占两行。
    const message = byId('message');
    if (message) {
      const fit = () => {
        message.style.height = 'auto';
        message.style.height = Math.min(message.scrollHeight + 2, 200) + 'px';
      };
      message.addEventListener('input', fit);
      fit();
    }
  }

  // ------------------------------------------------------- 信息栏顶部的地图缩略图
  // 只复用已经拿到的服务端掩膜底图（同一张 data: 图），不额外请求任何地图。
  function drawMiniMap(payload, dataUrl) {
    const img = byId('mini-map-img'), dot = byId('mini-map-dot'), empty = byId('mini-map-empty');
    const label = byId('mini-map-label');
    if (!img || !dot || !empty) return;
    if (dataUrl !== undefined) {
      if (dataUrl) img.src = dataUrl; else img.removeAttribute('src');
      img.hidden = !dataUrl;
    }
    empty.hidden = !img.hidden;
    empty.textContent = current ? '暂无地图' : '世界地图';
    const box = payload && payload.basemap && payload.basemap.bbox;
    const player = payload && payload.player;
    if (!img.hidden && box && player && player.lon !== null && player.lat !== null) {
      const [lonMin, lonMax, latMin, latMax] = box;
      dot.style.left = (100 * (player.lon - lonMin) / ((lonMax - lonMin) || 1)) + '%';
      dot.style.top = (100 * (latMax - player.lat) / ((latMax - latMin) || 1)) + '%';
      dot.hidden = false;
    } else dot.hidden = true;
    if (label) label.textContent = current ? (current.location || '旅程地图') : '地图';
    // 只有服务端明确回了「没有可用底图」才提示关联；加载中不闪。
    setMiniNote(!!current && !!payload && !(payload.status === 'ok' && payload.basemap && payload.basemap.available), payload && payload.reason);
  }

  // 信息栏缩略图下方的「关联地图」说明行。按钮不放进 #mini-map（它本身是 button）。
  function setMiniNote(show, reason) {
    const note = byId('mini-map-note');
    if (!note) return;
    note.hidden = !show;
    note.title = show && reason ? String(reason) : '';
  }
  // 与旅程地图空态里的「去世界地图工具关联」是同一个跳转，只写这一处。
  function openMapToolsForLink() {
    setDrawerOpen(false);
    return safe(() => showPage('map-tools'));
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
    wrap.append(host);
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
      scheduleFog(null);
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
    scheduleFog({ left, top, width, height });
  }

  // 绘制雾（static/map-fog.js）：铺满整个视口的 canvas，按屏幕分辨率画。只是装饰：
  // 底图 PNG 里揭示圈外已经是服务端画好的纯色，这层雾的透明区只会更小。
  // 拖动/缩放时先用 CSS 变换跟随上一帧，停下后再重画。
  let fogPainted = null, fogTimer = 0;
  function scheduleFog(rect) {
    const canvas = byId('play-map-fog'), wrap = byId('play-map-wrap'), img = byId('play-map-img');
    const payload = mapState.payload;
    const ok = canvas && wrap && img && !img.hidden && rect && window.TDMapFog && payload
      && payload.basemap && payload.basemap.bbox && payload.fog && Array.isArray(payload.fog.reveal);
    if (!ok) { if (canvas) canvas.hidden = true; fogPainted = null; return; }
    if (fogPainted && fogPainted.cw === wrap.clientWidth && fogPainted.ch === wrap.clientHeight) {
      const k = rect.width / fogPainted.rect.width;
      canvas.style.transformOrigin = '0 0';
      canvas.style.transform = 'translate(' + (rect.left - fogPainted.rect.left * k) + 'px,'
        + (rect.top - fogPainted.rect.top * k) + 'px) scale(' + k + ')';
    }
    clearTimeout(fogTimer);
    fogTimer = setTimeout(() => paintFog(rect), fogPainted ? 140 : 0);
  }
  function paintFog(rect) {
    const canvas = byId('play-map-fog'), wrap = byId('play-map-wrap');
    const payload = mapState.payload;
    if (!canvas || !wrap || !payload || !payload.fog) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const cw = wrap.clientWidth, ch = wrap.clientHeight;
    canvas.width = Math.round(cw * dpr); canvas.height = Math.round(ch * dpr);
    canvas.style.width = cw + 'px'; canvas.style.height = ch + 'px';
    canvas.style.transform = '';
    window.TDMapFog.paint(canvas, { box: payload.basemap.bbox, reveal: payload.fog.reveal,
      cloudDeg: payload.fog.cloud_deg, rect, scale: dpr });
    canvas.hidden = false;
    fogPainted = { rect, cw, ch };
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
    // 大致位置线索：服务端给的是偏移后的圆心（真实地点一定在圈内，但不在圆心）。
    // 圈内仍是雾：只画虚线圈与问号，不揭示地形。
    const kmToPx = (lat, km) => {
      const deg = km / 111.195;
      return { rx: deg / Math.max(0.02, Math.cos(lat * Math.PI / 180)) / spanLon * W, ry: deg / spanLat * H };
    };
    for (const clue of payload.clues || []) {
      const [x, y] = at(clue.lon, clue.lat);
      const { rx, ry } = kmToPx(clue.lat, clue.radius_km);
      const group = svgEl('g', { class: 'map-clue' });
      group.append(svgEl('ellipse', { cx: x, cy: y, rx, ry, fill: 'rgba(201,161,74,.10)',
        stroke: '#c9a14a', 'stroke-width': 2.5, 'stroke-dasharray': '10 7' }));
      group.append(svgEl('circle', { cx: x, cy: y, r: 14, fill: '#2e1d12', stroke: '#c9a14a', 'stroke-width': 2 }));
      const mark = svgEl('text', { x, y: y + 7, 'text-anchor': 'middle', fill: '#f0d58a', 'font-size': 20, 'font-weight': 700 });
      mark.textContent = '?';
      group.append(mark);
      const label = svgEl('text', { x, y: y - 22, 'text-anchor': 'middle', fill: '#f0e3c2', 'font-size': 20,
        stroke: '#0d1418', 'stroke-width': 4, 'paint-order': 'stroke', 'font-style': 'italic' });
      label.textContent = clue.label;
      group.append(label);
      const tip = svgEl('title', {});
      tip.textContent = clue.label + '：大致在这一带（约 ' + Math.round(clue.radius_km) + ' km 范围内）'
        + (clue.text ? '\n' + clue.text : '') + '\n到达后线索自动消失。';
      group.append(tip);
      overlay.append(group);
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
      go.onclick = () => openMapToolsForLink();
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
    if ((payload.clues || []).length) add('legend-clue', '传闻中的大致位置');
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
    if (byId('play-map-fog')) byId('play-map-fog').hidden = true;
    byId('play-map-empty').hidden = true;
    mapState = { status: 'loading', payload: null };
    drawLegend(null); drawMapNote(null); setMiniNote(false);
    try {
      const payload = await apiBase('/sessions/' + sessionId + '/play-map');
      if (current?.id !== sessionId || window.__tdNativeMode !== 'player' || seq !== imageSeq) return;
      mapState = { status: payload.status, payload };
      drawLegend(payload);
      drawMapNote(payload);
      const img = byId('play-map-img');
      drawMiniMap(payload, null);
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
          img.onload = () => { if (seq !== imageSeq || current?.id !== sessionId || window.__tdNativeMode !== 'player') return; img.hidden = false; byId('play-map-empty').hidden = true; applyTransform(); drawMiniMap(payload, dataUrl); };
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
      setMiniNote(true, '地图读取失败：' + error.message);
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
        if (byId('play-map-fog')) byId('play-map-fog').hidden = true;
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
        if (byId('play-map-fog')) byId('play-map-fog').hidden = true;
        byId('play-map-empty').hidden = true;
        drawLegend(null); drawMapNote(null);
        drawMiniMap(null, null);
      }
    });
  }

  // --------------------------------------------------------------- 接线
  function installPlayChrome() {
    const drawer = byId('play-left');
    const handle = byId('conversation-handle');
    // 对话层默认收起，留出完整地图；点击手记、存档或新建对话才展开。
    setDrawerOpen(false);
    if (handle) handle.onclick = () => setDrawerOpen(!drawer.classList.contains('is-expanded'));
    for (const id of ['drawer-collapse', 'mini-map']) {
      const button = byId(id);
      if (button) button.onclick = () => setDrawerOpen(false);
    }
    byId('rail-toggle')?.addEventListener('click', () => toggleSide('rail'));
    byId('info-toggle')?.addEventListener('click', () => toggleSide('info'));
    window.addEventListener('resize', syncSidePanels);
    document.addEventListener('keydown', (event) => {
      if (event.key !== 'Escape' || !drawer?.classList.contains('is-expanded')) return;
      if (document.querySelector('dialog[open]') || !byId('api-pop')?.hidden) return;
      if (openPop) { closePop(); return; }
      if (closeNarrowSides()) return;
      setDrawerOpen(false);
    });
    // 新建对话只有对话栏里这一个入口（存档栏顶部 + 空态卡片）。
    const openNew = () => { setDrawerOpen(true); openNewDialog(); };
    for (const id of ['journey-new', 'journey-empty-new']) {
      const button = byId(id);
      if (button) button.onclick = openNew;
    }
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
      mapTools.title = '在作者地图中查看和编辑圈地草稿';
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
    if (workspaceApi) workspaceApi.onclick = () => byId('api-toggle')?.click();
    const back = byId('back-to-play');
    if (back) back.onclick = () => safe(() => showPage('surface'));
    byId('message')?.addEventListener('focus', () => setDrawerOpen(true));
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
        ['settings', '设置'],
      ];
      for (const [target, title] of menuEntries) {
        const item = el('button', title, 'workspace-sub-link');
        item.type = 'button';
        item.onclick = () => safe(() => showPage(target));
        otherMenu.append(item);
      }
      // 地图美术资产预览是独立页面（新标签打开），不进旧功能层的页面路由。
      const artLink = el('button', '地图美术资产', 'workspace-sub-link');
      artLink.type = 'button';
      artLink.onclick = () => window.open('/static/map-art/index.html', '_blank', 'noopener');
      otherMenu.append(artLink);
      otherButton.onclick = () => {
        otherMenu.hidden = !otherMenu.hidden;
        otherButton.setAttribute('aria-expanded', String(!otherMenu.hidden));
      };
    }
    // 旅程存档列表（对话栏左栏）。标题由服务端给出，一律 textContent。
    window.TDWorkspaceSync = (sessions, api) => {
      const box = byId('journey-list');
      if (box) {
        box.replaceChildren(...(sessions || []).map((session) => {
          const title = session.title || '未命名旅程';
          const item = el('button', undefined, 'journey-item');
          item.type = 'button';
          item.title = title;
          item.dataset.sessionId = session.id;
          item.append(el('span', title, 'journey-title'));
          item.classList.toggle('selected', !!current && session.id === current.id);
          if (current && session.id === current.id) item.setAttribute('aria-current', 'true');
          item.onclick = () => safe(async () => {
            authorMap?.classList.remove('selected');
            closeNarrowSides();
            await loadSession(session.id);
            scrollStory(true);
          });
          return item;
        }));
        if (!(sessions || []).length) box.append(el('p', '还没有旅程。', 'muted rail-empty'));
      }
      const hint = byId('workspace-api-hint');
      if (hint && api) hint.textContent = api.offline ? '离线模式' : api.has_key ? '已连接' : '待配置';
      const mode = byId('workspace-mode');
      if (mode && api) mode.textContent = api.offline ? '离线测试' : '已连接 · ' + (api.model || '模型');
    };
    window.TDWorkspaceSyncCurrent = (session) => {
      byId('journey-list')?.querySelectorAll('button').forEach((button) => {
        const on = button.dataset.sessionId === session?.id;
        button.classList.toggle('selected', on);
        if (on) button.setAttribute('aria-current', 'true'); else button.removeAttribute('aria-current');
      });
      const worldLabel = byId('world-label');
      if (worldLabel && session) worldLabel.textContent = session.world || '织梦';
      const summary = byId('conversation-summary');
      if (summary && session) summary.textContent = [session.current_scene || session.event?.title, session.location].filter(Boolean).join(' · ') || '继续这段旅程';
    };
    document.querySelectorAll('#legacy nav button[data-page="surface"]').forEach((b) => {
      b.onclick = () => safe(() => showPage('surface'));
    });
  }

  function installRenderHooks() {
    const base = render;
    render = function () {
      base.apply(this, arguments);
      if (current) {
        byId('play-badge').textContent = current.title || current.world || '故事手记';
        byId('play-place').textContent = [current.location, current.daytime].filter(Boolean).join(' · ');
      }
      scrollStory(false);
      safe(() => loadMap(false));
      return undefined;
    };
  }

  // ------------------------------------------------- 信息栏「阅读」与侧栏分组
  const READING_KEY = 'textiledream-reading';
  const AUTHOR_GROUP_KEY = 'textiledream-author-group';
  const store = {
    get(key) { try { return JSON.parse(localStorage.getItem(key) || 'null'); } catch (e) { return null; } },
    set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* 存不了就只对本次生效 */ } },
    del(key) { try { localStorage.removeItem(key); } catch (e) { /* 同上 */ } },
  };
  function installReading() {
    const card = byId('info-reading'), story = byId('story-text');
    if (!card || !story) return;
    const allowed = { size: ['15', '17', '19'], leading: ['1.6', '1.9', '2.2'] };
    let prefs = store.get(READING_KEY) || {};
    const apply = () => {
      if (allowed.size.includes(String(prefs.size))) story.style.setProperty('--read-size', prefs.size + 'px');
      else story.style.removeProperty('--read-size');
      if (allowed.leading.includes(String(prefs.leading))) story.style.setProperty('--read-leading', String(prefs.leading));
      else story.style.removeProperty('--read-leading');
      card.querySelectorAll('.read-group').forEach((group) => {
        const picked = String(prefs[group.dataset.read] ?? '');
        group.querySelectorAll('button').forEach((button) => {
          const on = button.dataset.value === picked;
          button.classList.toggle('selected', on);
          button.setAttribute('aria-pressed', String(on));
        });
      });
    };
    card.querySelectorAll('.read-group button').forEach((button) => {
      button.onclick = () => {
        const key = button.closest('.read-group').dataset.read;
        prefs = { ...prefs, [key]: button.dataset.value };
        store.set(READING_KEY, prefs);
        apply();
      };
    });
    const reset = byId('read-reset');
    if (reset) reset.onclick = () => { prefs = {}; store.del(READING_KEY); apply(); };
    apply();
  }
  function installSidebarGroups() {
    const toggle = byId('workspace-author-toggle'), body = byId('workspace-author-group');
    if (toggle && body) {
      const isOpen = () => toggle.getAttribute('aria-expanded') === 'true';
      const set = (open) => {
        toggle.setAttribute('aria-expanded', String(open));
        toggle.parentElement?.classList.toggle('is-collapsed', !open);
      };
      set(store.get(AUTHOR_GROUP_KEY) !== 'closed');
      toggle.onclick = () => {
        const open = !isOpen();
        set(open);
        store.set(AUTHOR_GROUP_KEY, open ? 'open' : 'closed');
      };
    }
    const link = byId('mini-map-link');
    if (link) link.onclick = () => openMapToolsForLink();
  }

  window.addEventListener('DOMContentLoaded', () => {
    try {
      installReading();
      installSidebarGroups();
      installPlayChrome();
      installComposer();
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
      syncSidePanels();
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

  // 供其它脚本用的最小接口。
  window.PlayUI = {
    resetView,
    refreshMap: () => loadMap(true),
  };
})();
