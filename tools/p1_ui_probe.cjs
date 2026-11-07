/* P1 桌面布局验收探针：用 external/civ-atlas 里已有的 playwright + 本机 Edge。
 *
 * 只做浏览器里的观察与断言，不碰数据库、不造服务：服务与 fixture 由
 * tools/p1_ui_check.py 用临时 DB 起好传进来。结果以一行 JSON 打到 stdout。
 *
 * 每一项断言的是行为，不是"元素存在"：
 *   - 分隔条拖完左栏真的变宽，并且存进 localStorage；
 *   - 正文/历史真的能滚，输入框不压住内容；
 *   - 倒三角屏幕位置与服务器给的经纬度同一投影一致；
 *   - 底图裁切框角像素是雾色（把 PNG 读回像素比，不信 CSS）；
 *   - 未关联地图：无 img，给作者入口；
 *   - 任何响应体/header 里都没有假 key。
 */
const path = require('path');
const fs = require('fs');

const PLAYWRIGHT_ROOT = path.resolve(__dirname, '..', 'external', 'civ-atlas');
const { chromium } = require(require.resolve('playwright', { paths: [PLAYWRIGHT_ROOT] }));

const BASE = process.env.TD_BASE;
const FIXTURE = JSON.parse(process.env.TD_FIXTURE || '{}');
const SHOTS = process.env.TD_SHOTS;
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const VIEWPORTS = [['1440x900', 1440, 900], ['1366x768', 1366, 768]];
const SECRET = 'sk-P1TESTSECRET';
// 会改数据的检查（存档重命名/删除）只在显式允许、且目标不是用户正在用的 8000 端口时运行。
const ALLOW_MUTATE = process.env.TD_ALLOW_MUTATE === '1';
const { runNewFeatureChecks } = require('./p1_ui_features.cjs');
const skipped = [];

const checks = [];
function check(name, ok, detail) {
  checks.push({ check: name, ok: !!ok, detail: detail === undefined ? '' : String(detail).slice(0, 500) });
  console.log((ok ? 'PASS  ' : 'FAIL  ') + name + (detail !== undefined && detail !== '' ? '  — ' + String(detail).slice(0, 220) : ''));
  return !!ok;
}

const VIEW = () => {
  const box = (id) => {
    const e = document.getElementById(id);
    if (!e) return null;
    const r = e.getBoundingClientRect();
    return { w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.left),
             y: Math.round(r.top), bottom: Math.round(r.bottom), right: Math.round(r.right) };
  };
  const img = document.getElementById('play-map-img');
  const empty = document.getElementById('play-map-empty');
  const drawer = document.getElementById('play-left');
  const tri = document.querySelector('#play-map-overlay path');
  return {
    viewport: { w: innerWidth, h: innerHeight },
    docScrollW: document.documentElement.scrollWidth,
    left: box('play-left'), right: box('play-right'), main: box('play-main'), topbar: box('topbar'),
    rail: box('journey-rail'), info: box('info-panel'), surface: box('surface'),
    mapWrap: box('play-map-wrap'), mapImg: box('play-map-img'),
    composer: box('chat-form'),
    mapVisible: !!img && !img.hidden,
    emptyText: empty && !empty.hidden ? empty.textContent.trim().slice(0, 240) : null,
    expanded: !!drawer && drawer.classList.contains('is-expanded'),
    railOff: !!drawer && drawer.classList.contains('rail-off'),
    infoOff: !!drawer && drawer.classList.contains('info-off'),
    storedLayout: (() => { try { return localStorage.getItem('textiledream-chat-layout'); } catch (e) { return 'ERR'; } })(),
    connText: (document.getElementById('conn-state') || {}).textContent || null,
    apiFormParent: (() => { const f = document.getElementById('api-form'); return f && f.parentElement ? (f.parentElement.id || f.parentElement.className) : null; })(),
    keyType: (() => { const k = document.getElementById('api-key'); return k ? k.type : null; })(),
    keyValue: (() => { const k = document.getElementById('api-key'); return k ? k.value : null; })(),
    triD: tri ? tri.getAttribute('d') : null,
    circles: document.querySelectorAll('#play-map-overlay circle').length,
    legend: [...document.querySelectorAll('#play-map-legend .legend-item')].map((n) => n.textContent.trim()),
    mapNote: ((document.getElementById('play-map-note') || {}).textContent || '').slice(0, 400),
    otherRows: [...document.querySelectorAll('#workspace-other-menu button')].map((n) => n.textContent),
    overflowX: document.documentElement.scrollWidth > innerWidth + 1,
  };
};

async function shot(page, name) {
  const file = path.join(SHOTS, name);
  await page.screenshot({ path: file, animations: 'disabled' });
  return file;
}

async function waitFor(page, fnBody, timeoutMs) {
  // 页面带着严格的 CSP（script-src 'self'），所以不能用 page.waitForFunction：
  // 它会把自己序列化成字符串去 eval，直接被 CSP 拒。page.evaluate 走 CDP 的
  // Runtime.evaluate，不受页面 CSP 限制，所以这里自己轮询。
  const deadline = Date.now() + (timeoutMs || 20000);
  while (Date.now() < deadline) {
    try {
      if (await page.evaluate(fnBody) === true) return true;
    } catch (e) { /* 页面还在导航/未就绪 */ }
    await page.waitForTimeout(120);
  }
  return false;
}

async function waitApp(page) {
  // 新版启动停在作者模式空态（不自动打开旅程），所以只等 token。
  const ok = await waitFor(page, () => typeof token === 'string' && token.length > 8 &&
    typeof window.loadSession === 'function' && !!window.TDConversationDrawer, 30000);
  if (!ok) throw new Error('应用未在 30s 内完成引导（token / loadSession 未就位）');
}

// 故事手记展开时盖住整块地图；测地图交互前要先收起，测对话前再展开。
async function setDrawer(page, open) {
  await page.evaluate((o) => (o ? window.TDConversationDrawer.open() : window.TDConversationDrawer.close()), open);
  await page.waitForTimeout(380);
}

/* 跑一步，崩溃就**记成一条失败项**再继续——不是把失败变成功。
   它只是为了不让某一页的异常把整轮其余页面（以及它们的截图）都拖死。 */
async function guard(page, label, step, fn) {
  try {
    return await fn();
  } catch (error) {
    const message = String((error && error.message) || error).slice(0, 400);
    check(label + ' ' + step + ' 未抛异常', false, message);
    return null;
  }
}

async function runViewport(browser, label, width, height) {
  // 默认布局必须在**全新的 context**里量：上一个视口拖过分隔条，会把比例写进
  // localStorage；如果在同一个 context 里量“默认 40%”，量到的是上次的偏好，
  // 而不是默认值。（存偏好另有一段单独验：fresh context —— 拖 —— 重开 context）
  const context = await browser.newContext({
    viewport: { width, height }, deviceScaleFactor: 1, isMobile: false,
    locale: 'zh-CN',
  });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push('pageerror: ' + String(e.message).slice(0, 200)));
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console.error: ' + m.text().slice(0, 200)); });
  const responses = [];
  const requests = [];   // 每个 /api 请求的 method + path，用来断言「没有发出不该发的请求」
  page.on('request', (r) => {
    try {
      const u = new URL(r.url());
      if (u.pathname.startsWith('/api/')) requests.push({ method: r.method(), path: u.pathname });
    } catch (e) { /* 非常规 URL 忽略 */ }
  });
  page.on('response', async (r) => {
    try {
      const url = r.url();
      if (!url.includes('/api/')) return;
      const text = await r.text().catch(() => '');
      const headers = JSON.stringify(r.headers());
      responses.push({ url: url.replace(BASE, ''), status: r.status(),
                       leaked: text.includes(SECRET) || headers.includes(SECRET) });
    } catch (e) { /* 预检/中止的响应忽略 */ }
  });

  console.log('\n=== ' + label + ' ===');
  await page.goto(BASE + '?p1=1', { waitUntil: 'domcontentloaded' });
  await waitApp(page);
  // 新 context：没有残留布局偏好；首屏是完整地图 + 底部一条收起的故事手记。
  const v0 = await page.evaluate(VIEW);
  check(label + ' 新 context 里没有残留对话栏布局偏好', v0.storedLayout === null, String(v0.storedLayout));
  check(label + ' 首屏故事手记默认收起（只占底部一条，地图可见）',
    !v0.expanded && !!v0.left && v0.left.h <= 60 && !!v0.right && v0.right.h > v0.left.h * 4,
    'expanded=' + v0.expanded + ' left.h=' + (v0.left && v0.left.h) + ' right.h=' + (v0.right && v0.right.h));
  const sidebarSessions = await page.evaluate(() => ({
    inDrawer: !!document.querySelector('#play-left #journey-list'),
    inSidebar: document.querySelectorAll('#workspace-sidebar #journey-list, #workspace-sidebar .journey-item, #workspace-sessions').length,
    newInDrawer: !!document.querySelector('#play-left #journey-new'),
    newElsewhere: document.querySelectorAll('#play-new, #workspace-new-chat, #new-session').length,
  }));
  check(label + ' 旅程存档与新建对话只在对话栏里（侧栏/顶栏没有）',
    sidebarSessions.inDrawer && sidebarSessions.inSidebar === 0 && sidebarSessions.newInDrawer && sidebarSessions.newElsewhere === 0,
    JSON.stringify(sidebarSessions));
  await page.evaluate((id) => loadSession(id), FIXTURE.linked);
  const mapReady = await waitFor(page, () => {
    const img = document.getElementById('play-map-img');
    return !!img && !img.hidden && img.naturalWidth > 0;
  }, 25000);
  // 底图加载失败时把真实网络响应打出来（状态/内容），不要只说“没加载”。
  const mapNet = await page.evaluate(async () => {
    const r1 = await fetch('/api/sessions/' + current.id + '/play-map',
      { headers: { 'X-TextileDream-Token': token } });
    const body = await r1.json();
    const url = body.basemap && body.basemap.url;
    let png = null;
    if (url) {
      const r2 = await fetch(url, { headers: { 'X-TextileDream-Token': token } });
      png = { status: r2.status, type: r2.headers.get('content-type'),
              bytes: (await r2.blob()).size };
    }
    return { jsonStatus: r1.status, status: body.status,
             available: body.basemap && body.basemap.available, url, png,
             player: body.player, bbox: body.basemap && body.basemap.bbox };
  });
  check(label + ' play-map 真实响应是 ok 且有 bbox/player',
    mapNet.jsonStatus === 200 && mapNet.status === 'ok' && !!mapNet.bbox && !!mapNet.player,
    JSON.stringify(mapNet).slice(0, 300));
  check(label + ' basemap.png 真实响应 200 且是 PNG 字节',
    !!mapNet.png && mapNet.png.status === 200 && mapNet.png.bytes > 100 &&
    String(mapNet.png.type).includes('png'), JSON.stringify(mapNet.png));
  check(label + ' 已关联地图的底图在 25s 内加载完成', mapReady,
    'img.naturalWidth>0 = ' + mapReady);
  await page.waitForTimeout(400);
  const vc = await page.evaluate(VIEW);
  await shot(page, 'chat-' + label + '.png');
  check(label + ' 打开旅程后故事手记展开并占满地图区',
    vc.expanded && !!vc.main && Math.abs(vc.left.w - vc.main.w) <= 2 && Math.abs(vc.left.h - vc.main.h) <= 2,
    'left=' + vc.left.w + 'x' + vc.left.h + ' main=' + (vc.main && vc.main.w + 'x' + vc.main.h));
  check(label + ' 展开时三栏并排（存档 | 正文 | 信息）',
    !vc.railOff && !vc.infoOff && vc.rail.w > 120 && vc.info.w > 160 && vc.surface.w > vc.rail.w &&
    vc.rail.right <= vc.surface.x + 2 && vc.surface.right <= vc.info.x + 2,
    'rail=' + vc.rail.w + ' surface=' + vc.surface.w + ' info=' + vc.info.w);
  check(label + ' 输入框在正文栏内且底边不越界',
    vc.composer.bottom <= vc.left.bottom + 1 && vc.composer.x >= vc.surface.x - 1 && vc.composer.right <= vc.surface.right + 1,
    'composer.bottom=' + vc.composer.bottom + ' left.bottom=' + vc.left.bottom);
  const mini = await page.evaluate(() => {
    const img = document.getElementById('mini-map-img');
    return { inInfo: !!document.querySelector('#info-panel #mini-map'), img: !!img && !img.hidden && img.naturalWidth > 0,
             dot: !document.getElementById('mini-map-dot').hidden };
  });
  check(label + ' 信息栏有地图缩略图（已加载、标出当前位置）', mini.inInfo && mini.img && mini.dot, JSON.stringify(mini));

  // 点缩略图回到地图：对话栏收起，地图重新可见、可交互。
  await page.click('#mini-map');
  await page.waitForTimeout(420);
  const v = await page.evaluate(VIEW);
  check(label + ' 点缩略图收起对话栏回到地图', !v.expanded && v.left.h <= 60, 'expanded=' + v.expanded + ' h=' + v.left.h);

  check(label + ' 无横向溢出', !v.overflowX, 'scrollW=' + v.docScrollW + ' viewport=' + v.viewport.w);
  check(label + ' 地图主画面占满地图区（唯一一张底图已加载）', v.mapVisible && v.mapWrap.w >= v.right.w - 2,
    'mapWrap=' + v.mapWrap.w + 'x' + v.mapWrap.h + ' right=' + v.right.w);
  check(label + ' 倒三角（当前位置）已画出', !!v.triD, String(v.triD).slice(0, 70));
  check(label + ' 图例含「当前位置」', (v.legend || []).some((t) => t.includes('当前位置')), JSON.stringify(v.legend));
  // 主画面只保简洁状态；技术口径在 tooltip 里（玩家不该每看一眼地图就读一段免责）。
  check(label + ' 地图状态栏简洁（不把算法免责写成正文）',
    v.mapNote.includes('已探索') && v.mapNote.length < 60,
    v.mapNote.slice(0, 120));
  const fogTitle = await page.evaluate(() => (document.getElementById('play-map-note') || {}).title || '');
  check(label + ' 雾的说明移到 tooltip（可查但不占画面）',
    fogTitle.includes('不是真实视线') && fogTitle.includes('服务器'), fogTitle.slice(0, 120));
  check(label + ' 顶部连接状态只给状态值、不含密钥',
    !!v.connText && !v.connText.includes(SECRET) && v.connText.includes('密钥'), v.connText);

  // 倒三角尖端必须落在服务器经纬度对应的**屏幕**位置上：<=1 屏幕像素。
  // 只比 SVG 用户单位会被缩放骗过（放大 8 倍时 1 单位就是 8 像素），所以一律换算到
  // getBoundingClientRect 的屏幕坐标再比，并在默认、放大、平移三种视图下各验一次。
  const anchorNow = () => page.evaluate(async () => {
    const r = await fetch('/api/sessions/' + current.id + '/play-map',
      { headers: { 'X-TextileDream-Token': token } });
    const p = await r.json();
    const bbox = p.basemap && p.basemap.bbox;
    const path = document.querySelector('#play-map-overlay path');
    const svg = document.getElementById('play-map-overlay');
    if (!bbox || !path || !svg) return { skip: true };
    const [lonMin, lonMax, latMin, latMax] = bbox;
    const fx = (p.player.lon - lonMin) / (lonMax - lonMin);
    const fy = (latMax - p.player.lat) / (latMax - latMin);
    const rect = svg.getBoundingClientRect();
    const d = path.getAttribute('d') || '';
    const nums = (d.match(/-?[\d.]+/g) || []).map(Number);
    // d = 'M x0 y0 L x1 y1 L tipX tipY Z'：第三个点是尖端（朝下）。
    const tipX = nums[4], tipY = nums[5];
    // viewBox 不再固定为 1000×1000（现为底图像素尺寸），按实际 viewBox 换算。
    const vb = (svg.getAttribute('viewBox') || '0 0 1000 1000').split(/[\s,]+/).map(Number);
    const toScreenX = (vx) => rect.left + ((vx - vb[0]) / (vb[2] || 1000)) * rect.width;
    const toScreenY = (vy) => rect.top + ((vy - vb[1]) / (vb[3] || 1000)) * rect.height;
    return {
      bbox, player: { lon: p.player.lon, lat: p.player.lat },
      rect: { x: rect.left, y: rect.top, w: rect.width, h: rect.height },
      viewBox: svg.getAttribute('viewBox'),
      tipSvg: { x: tipX, y: tipY },
      want: { x: rect.left + fx * rect.width, y: rect.top + fy * rect.height },
      got: { x: toScreenX(tipX), y: toScreenY(tipY) },
      note: p.fog && p.fog.note,
      radius: p.fog && p.fog.reveal_radius_km,
      placeStates: (p.places || []).map((row) => row.state),
    };
  });
  const anchorCheck = (name, row) => {
    const dx = row && row.got ? row.got.x - row.want.x : NaN;
    const dy = row && row.got ? row.got.y - row.want.y : NaN;
    check(label + ' ' + name, !!row && !row.skip && Math.abs(dx) <= 1 && Math.abs(dy) <= 1,
      row && row.skip ? 'no bbox/player'
        : 'dx=' + dx.toFixed(2) + ' dy=' + dy.toFixed(2) +
          ' want=' + row.want.x.toFixed(1) + ',' + row.want.y.toFixed(1) +
          ' got=' + row.got.x.toFixed(1) + ',' + row.got.y.toFixed(1) +
          ' overlay=' + Math.round(row.rect.w) + 'x' + Math.round(row.rect.h));
    return row;
  };
  const a0 = anchorCheck('倒三角尖端落在经纬度屏幕位置（默认视图，<=1px）', await anchorNow());
  check(label + ' 地点状态属于 current/explored/known',
    (a0.placeStates || []).length > 0 && a0.placeStates.every((s) => ['current', 'explored', 'known'].includes(s)),
    JSON.stringify(a0.placeStates));
  check(label + ' 可见半径写明是玩法距离', a0.radius > 0 && String(a0.note || '').includes('玩法'),
    'radius=' + a0.radius);

  // 探索面板默认是「城镇街区」，街区图会盖住整张底图、吃掉指针事件；
  // 测世界底图的缩放/平移/点外部前，先切到「世界道路」。
  const worldScale = page.locator('#exploration-panel button:has-text("世界道路")');
  if (await worldScale.count()) { await worldScale.first().click(); await page.waitForTimeout(250); }
  // 缩放后仍 <=1 屏幕像素（这一条是用户明确要的：锚点按屏幕算，不按 viewBox 算）
  await page.click('#play-map-zoom-in');
  await page.click('#play-map-zoom-in');
  await page.waitForTimeout(260);
  const a1 = anchorCheck('放大后尖端仍落在屏幕位置（<=1px）', await anchorNow());
  check(label + ' 放大真的改变了底图尺寸', !!a1 && !!a0 && a1.rect.w > a0.rect.w * 1.3,
    'before=' + (a0 && Math.round(a0.rect.w)) + ' after=' + (a1 && Math.round(a1.rect.w)));

  // 真实鼠标平移（pointerdown/move/up 走真实指针，才真正压到 setPointerCapture 路径）
  const mid = await page.evaluate(() => {
    const r = document.getElementById('play-map-wrap').getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  });
  await page.mouse.move(mid.x, mid.y);
  await page.mouse.down();
  await page.mouse.move(mid.x + 90, mid.y + 40, { steps: 10 });
  await page.mouse.up();
  await page.waitForTimeout(260);
  const a2 = anchorCheck('平移后尖端仍落在屏幕位置（<=1px）', await anchorNow());
  check(label + ' 真实鼠标拖动真的平移了地图', !!a1 && !!a2 && Math.abs(a2.rect.x - a1.rect.x) > 5,
    'x ' + (a1 && Math.round(a1.rect.x)) + ' -> ' + (a2 && Math.round(a2.rect.x)));
  check(label + ' 平移只在放大后生效（默认视图不越界）', !!a0 && a0.rect.x >= -1,
    'x0=' + (a0 && Math.round(a0.rect.x)));
  await page.click('#play-map-reset');
  await page.waitForTimeout(260);
  const a3 = anchorCheck('复位后尖端仍落在屏幕位置（<=1px）', await anchorNow());
  check(label + ' 「复位」回到整张探索区域',
    !!a0 && !!a3 && Math.abs(a3.rect.w - a0.rect.w) <= 2 && Math.abs(a3.rect.x - a0.rect.x) <= 2,
    'w ' + (a0 && Math.round(a0.rect.w)) + ' -> ' + (a3 && Math.round(a3.rect.w)));

  // 底图裁切框角落必须是雾色（读回像素，不信 CSS）
  const fog = await page.evaluate(async () => {
    const r = await fetch('/api/sessions/' + current.id + '/play-map',
      { headers: { 'X-TextileDream-Token': token } });
    const p = await r.json();
    const img = document.getElementById('play-map-img');
    const c = document.createElement('canvas');
    c.width = img.naturalWidth; c.height = img.naturalHeight;
    const ctx = c.getContext('2d');
    ctx.drawImage(img, 0, 0);
    const px = (x, y) => [...ctx.getImageData(x, y, 1, 1).data].slice(0, 3);
    return {
      w: c.width, h: c.height, bbox: p.basemap.bbox, url: p.basemap.url,
      cornerTL: px(1, 1), cornerBR: px(c.width - 2, c.height - 2),
      playerPx: (() => {
        const [lonMin, lonMax, latMin, latMax] = p.basemap.bbox;
        const x = Math.round((p.player.lon - lonMin) / (lonMax - lonMin) * (c.width - 1));
        const y = Math.round((latMax - p.player.lat) / (latMax - latMin) * (c.height - 1));
        return { x, y, rgb: px(Math.min(c.width - 1, Math.max(0, x)), Math.min(c.height - 1, Math.max(0, y))) };
      })(),
    };
  });
  // 雾色取自 app/fog_art.py 的 FOG_RGB（现为纸色 198,186,160）。
  const FOG = [198, 186, 160];
  const isFog = (rgb) => rgb && rgb[0] === FOG[0] && rgb[1] === FOG[1] && rgb[2] === FOG[2];
  // 先断言图片真的解码成功、坐标落在图内；否则 ((-1,-1,[0,0,0])) 这种
  // 抽不到的像素会让 "当前位置不是雾" 假阳性通过。
  check(label + ' 底图已解码（canvas 尺寸 > 0）', fog.w > 0 && fog.h > 0,
    'w=' + fog.w + ' h=' + fog.h);
  const inBounds = fog.playerPx && fog.playerPx.x >= 0 && fog.playerPx.y >= 0 &&
    fog.playerPx.x < fog.w && fog.playerPx.y < fog.h;
  check(label + ' 当前位置像素坐标在图内（不靠越界值碰巧通过）', inBounds,
    JSON.stringify(fog.playerPx));
  check(label + ' 底图角落像素是雾色（不是地形）',
    fog.w > 0 && fog.h > 0 && isFog(fog.cornerTL) && isFog(fog.cornerBR),
    'tl=' + fog.cornerTL + ' br=' + fog.cornerBR + ' size=' + fog.w + 'x' + fog.h);
  check(label + ' 当前位置像素不是雾（已探索真地形）', inBounds && !isFog(fog.playerPx.rgb),
    JSON.stringify(fog.playerPx));

  // 正文独立滚动 + 输入框不压住内容（滚动容器是 #surface）
  await setDrawer(page, true);
  const scroll = await page.evaluate(() => {
    const reading = document.getElementById('surface');
    const composer = document.getElementById('chat-form');
    const long = document.getElementById('story-text');
    if (!reading) return { skip: true };
    // 为了真的量到滚动，塞一段长文本（只在浏览器里，不写库）。
    const probe = document.createElement('div');
    probe.id = 'p1-scroll-probe';
    probe.style.whiteSpace = 'pre-wrap';
    probe.textContent = Array.from({ length: 60 }, (_, i) => '滚动检查行 ' + i + '：'.repeat(1) + '内容'.repeat(20)).join('\n');
    long.append(probe);
    const canScroll = reading.scrollHeight > reading.clientHeight + 1;
    reading.scrollTop = reading.scrollHeight;
    const a = composer.getBoundingClientRect();
    const b = probe.getBoundingClientRect();
    const out = { canScroll, scrollTop: Math.round(reading.scrollTop),
                  scrollH: reading.scrollHeight, clientH: reading.clientHeight,
                  probeBottom: Math.round(b.bottom), composerTop: Math.round(a.top),
                  composerBottom: Math.round(a.bottom),
                  leftBottom: Math.round(document.getElementById('play-left').getBoundingClientRect().bottom) };
    probe.remove();
    return out;
  });
  check(label + ' 正文区独立滚动（长内容可滚）', scroll.canScroll === true,
    'scrollH=' + scroll.scrollH + ' clientH=' + scroll.clientH + ' scrollTop=' + scroll.scrollTop);
  check(label + ' 滚到底时输入框不压住正文', scroll.probeBottom <= scroll.composerTop + 2,
    'probeBottom=' + scroll.probeBottom + ' composerTop=' + scroll.composerTop);
  check(label + ' 输入框底边不越出对话栏', scroll.composerBottom <= scroll.leftBottom + 1,
    'composerBottom=' + scroll.composerBottom + ' leftBottom=' + scroll.leftBottom);

  // 存档栏 / 信息栏开关：真实点击，宽屏下写进 localStorage（textiledream-chat-layout）。
  const sides = await guard(page, label, '存档/信息栏开关', async () => {
    const before = await page.evaluate(VIEW);
    await page.click('#rail-toggle');
    await page.click('#info-toggle');
    await page.waitForTimeout(350);
    const off = await page.evaluate(VIEW);
    await page.click('#rail-toggle');
    await page.click('#info-toggle');
    await page.waitForTimeout(350);
    const on = await page.evaluate(VIEW);
    return { before, off, on };
  });
  check(label + ' 收起存档栏与信息栏后正文变宽',
    !!sides && sides.off.railOff && sides.off.infoOff && sides.off.surface.w > sides.before.surface.w + 200,
    sides && ('surface ' + sides.before.surface.w + ' -> ' + sides.off.surface.w));
  check(label + ' 两栏开关状态写入 localStorage',
    !!sides && /"rail":false/.test(String(sides.off.storedLayout)) && /"info":false/.test(String(sides.off.storedLayout)),
    sides && sides.off.storedLayout);
  check(label + ' 再点一次两栏恢复', !!sides && !sides.on.railOff && !sides.on.infoOff,
    sides && JSON.stringify({ railOff: sides.on.railOff, infoOff: sides.on.infoOff }));
  await shot(page, 'layout-' + label + '.png');

  // 存档栏（原「历史」页签）：存档与章节都在对话栏左栏里
  const hist = await page.evaluate(() => ({
    journeys: document.querySelectorAll('#journey-rail #journey-list .journey-item').length,
    selected: document.querySelectorAll('#journey-list .journey-item.selected').length,
    chapters: document.querySelectorAll('#journey-rail #conversations button').length,
  }));
  check(label + ' 存档栏列出旅程且标出当前旅程', hist.journeys >= 2 && hist.selected === 1, JSON.stringify(hist));

  // 信息栏卡片（原「物品 / 其他」页签的内容）
  const info = await page.evaluate(() => {
    const t = (id) => ((document.getElementById(id) || {}).textContent || '').trim();
    return {
      local: t('local-state').slice(0, 120), journey: !!document.querySelector('#info-panel #info-journey #export-story'),
      systems: !!document.querySelector('#info-panel #world-systems'), systemsText: t('world-systems').slice(0, 160),
    };
  });
  check(label + ' 信息栏有资源与时间卡片且不是空白', info.local.length > 4, info.local);
  check(label + ' 信息栏有「属性、物品与当地环境」卡片', info.systems && info.systemsText.length > 4, info.systemsText);
  check(label + ' 信息栏有「本段旅程」（导出、归档）', info.journey, String(info.journey));
  await shot(page, 'info-' + label + '.png');

  // 「其他」菜单收全部旧功能入口（旧图册已删除，不再要求）
  await page.click('#workspace-other');
  await page.waitForTimeout(250);
  const other = await page.evaluate(VIEW);
  const wanted = ['知识点记录簿', '世界创作', '世界地图工具', '城镇创作', '里层创作', '模型输入输出', '设置'];
  const missing = wanted.filter((w) => !(other.otherRows || []).some((t) => t.includes(w)));
  check(label + ' 「其他」收全部旧功能入口', missing.length === 0, 'missing=' + JSON.stringify(missing));
  check(label + ' 「旅程地图 · 旧图册」已不在入口里', !(other.otherRows || []).some((t) => t.includes('旧图册')),
    JSON.stringify(other.otherRows));
  await shot(page, 'other-' + label + '.png');

  // 旧功能没丢：城镇创作 → 内容在 → 回到游玩
  const town = await guard(page, label, '旧「城镇创作」页', async () => {
    await page.click('#workspace-other-menu button:has-text("城镇创作")');
    await page.waitForTimeout(900);
    return await page.evaluate(() => ({
      legacyHidden: document.getElementById('legacy').hidden,
      playHidden: document.getElementById('play').hidden,
      title: document.getElementById('page-title').textContent,
      townVisible: !document.getElementById('towns').hidden,
      townText: document.getElementById('towns').textContent.length,
    }));
  });
  check(label + ' 旧「城镇创作」页可打开且内容在',
    !!town && town.legacyHidden === false && town.townVisible && town.townText > 200,
    JSON.stringify(town));
  await shot(page, 'legacy-towns-' + label + '.png');
  // 元素装配也要在
  const el2 = await guard(page, label, '旧「元素装配」页', async () => {
    await page.evaluate(() => showPage('elements'));
    await page.waitForTimeout(700);
    return await page.evaluate(() => ({
      visible: !document.getElementById('elements').hidden,
      text: document.getElementById('elements').textContent.length,
    }));
  });
  check(label + ' 旧「元素装配」页可打开且内容在', !!el2 && el2.visible && el2.text > 200,
    JSON.stringify(el2));
  await shot(page, 'legacy-elements-' + label + '.png');
  const back = await guard(page, label, '回到游玩', async () => {
    await page.click('#back-to-play');
    await page.waitForTimeout(500);
    return await page.evaluate(() => ({
      play: !document.getElementById('play').hidden,
      legacy: document.getElementById('legacy').hidden,
      mainW: Math.round(document.getElementById('play-main').getBoundingClientRect().width),
      leftW: Math.round(document.getElementById('play-left').getBoundingClientRect().width),
    }));
  });
  check(label + ' 「回到游玩」回到游玩壳（地图区 + 故事手记）',
    !!back && back.play === true && back.legacy === true && back.mainW > 400 && back.leftW > 0,
    JSON.stringify(back));

  // 「其他 → 旧页 → 返回」不能丢掉 current（也不能换会话）
  const curAfter = await page.evaluate(() => current && current.id);
  check(label + ' 进出旧页后 current 不丢、不换会话', curAfter === FIXTURE.linked,
    'current=' + curAfter + ' expect=' + FIXTURE.linked);

  // API 弹层：打开 → 弹层真的可见、表单真的在弹层里、密钥框可用；
  // 关闭（再点一次 / Escape / 点外部）→ 表单**搬回** #api 页，不留空壳。
  await page.click('#api-toggle');
  await page.waitForTimeout(450);
  const opened = await page.evaluate(() => {
    const pop = document.getElementById('api-pop');
    const form = document.getElementById('api-form');
    const key = document.getElementById('api-key');
    const r = pop.getBoundingClientRect();
    const kr = key ? key.getBoundingClientRect() : null;
    return {
      popHidden: pop.hidden, popW: Math.round(r.width), popH: Math.round(r.height),
      popOnScreen: r.width > 100 && r.height > 40 && r.top >= 0 && r.left >= 0 &&
                   r.right <= innerWidth + 1 && r.bottom <= innerHeight + 1,
      parent: form && form.parentElement ? (form.parentElement.id || form.parentElement.className) : null,
      formVisible: !!form && form.getBoundingClientRect().height > 20,
      inputs: pop.querySelectorAll('input,select,button').length,
      keyType: key ? key.type : null, keyValue: key ? key.value : null,
      keyVisible: !!kr && kr.width > 20 && kr.height > 10,
      expanded: document.getElementById('api-toggle').getAttribute('aria-expanded'),
    };
  });
  check(label + ' 顶部 API 弹层真的打开了（不隐藏、在屏内、有尺寸）',
    opened.popHidden === false && opened.popOnScreen && opened.expanded === 'true',
    JSON.stringify({ hidden: opened.popHidden, w: opened.popW, h: opened.popH, expanded: opened.expanded }));
  check(label + ' 弹层里的表单可见且可操作（不是空壳）',
    opened.formVisible && opened.inputs >= 5 && opened.keyVisible,
    JSON.stringify({ formVisible: opened.formVisible, inputs: opened.inputs, keyVisible: opened.keyVisible }));
  check(label + ' 顶部弹层里的表单就是那一份（落在 api-pop-host）',
    opened.parent === 'api-pop-host', '表单落点=' + opened.parent);
  check(label + ' 密钥框 type=password 且值为空（不回填）',
    opened.keyType === 'password' && !opened.keyValue,
    'type=' + opened.keyType + ' value=' + JSON.stringify(opened.keyValue));
  await shot(page, 'api-pop-' + label + '.png');

  // 关闭方式一：再点一次顶部入口
  await page.click('#api-toggle');
  await page.waitForTimeout(350);
  const closed1 = await page.evaluate(() => ({
    hidden: document.getElementById('api-pop').hidden,
    expanded: document.getElementById('api-toggle').getAttribute('aria-expanded'),
    parent: (() => { const f = document.getElementById('api-form');
      return f && f.parentElement ? (f.parentElement.id || f.parentElement.className) : null; })(),
  }));
  check(label + ' 再点入口能关闭弹层并把表单搬回 #api',
    closed1.hidden === true && closed1.expanded === 'false' && closed1.parent === 'api',
    JSON.stringify(closed1));

  // 关闭方式二：Escape
  await page.click('#api-toggle');
  await page.waitForTimeout(300);
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
  const closed2 = await page.evaluate(() => document.getElementById('api-pop').hidden);
  check(label + ' Escape 能关闭弹层', closed2 === true, 'hidden=' + closed2);

  // 关闭方式三：点弹层外部
  await page.click('#api-toggle');
  await page.waitForTimeout(300);
  // 弹层盖在右上角：点击位置必须真的在弹层矩形之外（取主区左下角）。
  const outside = await page.evaluate(() => {
    const r = document.getElementById('play-main').getBoundingClientRect();
    const p = document.getElementById('api-pop').getBoundingClientRect();
    const pt = { x: r.left + 40, y: r.bottom - 80 };
    const inPop = pt.x >= p.left && pt.x <= p.right && pt.y >= p.top && pt.y <= p.bottom;
    return inPop ? { x: r.left + 20, y: r.bottom - 20 } : pt;
  });
  await page.mouse.click(outside.x, outside.y);
  await page.waitForTimeout(300);
  const closed3 = await page.evaluate(() => document.getElementById('api-pop').hidden);
  check(label + ' 点弹层外部能关闭它', closed3 === true, 'hidden=' + closed3);

  await page.evaluate(() => showPage('api'));
  await page.waitForTimeout(600);
  const apiPage = await page.evaluate(() => ({
    parent: (() => { const f = document.getElementById('api-form');
      return f && f.parentElement ? (f.parentElement.id || f.parentElement.className) : null; })(),
    visible: !document.getElementById('api').hidden,
    text: document.getElementById('api').textContent.length,
    fields: document.querySelectorAll('#api input, #api select').length,
    keyValue: (document.getElementById('api-key') || {}).value,
    formVisible: document.getElementById('api-form').getBoundingClientRect().height > 40,
  }));
  check(label + ' API 旧页不再是空壳（表单搬回 #api 且可见）',
    apiPage.visible && apiPage.parent === 'api' && apiPage.fields >= 3 && apiPage.formVisible,
    JSON.stringify(apiPage));
  check(label + ' API 旧页里的密钥框仍为空（不回填）', !apiPage.keyValue, JSON.stringify(apiPage.keyValue));
  await shot(page, 'api-page-' + label + '.png');
  await page.click('#back-to-play');
  await page.waitForTimeout(500);

  // 未关联地图的旅程：无 img + 作者入口
  await page.evaluate((id) => loadSession(id), FIXTURE.plain);
  await page.waitForTimeout(1500);
  const plain = await page.evaluate(VIEW);
  check(label + ' 未关联地图时不显示任何底图', !plain.mapVisible, 'mapVisible=' + plain.mapVisible);
  check(label + ' 未关联时给明确未关联文案 + 作者入口按钮',
    !!plain.emptyText && plain.emptyText.includes('没有关联') && plain.emptyText.includes('世界地图工具'),
    plain.emptyText);
  await shot(page, 'unlinked-' + label + '.png');

  // ---------------------------------------------------------- 保存偏好 vs 首次默认
  // 首次默认（两栏都开）已在全新 context 验过；这里验「收起过存档栏，重载后读回偏好」。
  await page.evaluate(() => localStorage.setItem('textiledream-chat-layout', JSON.stringify({ rail: false, info: true })));
  await page.reload({ waitUntil: 'domcontentloaded' });
  await waitApp(page);
  await page.evaluate((id) => loadSession(id), FIXTURE.linked);
  await page.waitForTimeout(900);
  const restored = await page.evaluate(VIEW);
  check(label + ' 重载后读回保存的两栏偏好（存档栏仍收起、信息栏仍打开）',
    restored.expanded && restored.railOff === true && restored.infoOff === false,
    JSON.stringify({ expanded: restored.expanded, railOff: restored.railOff, infoOff: restored.infoOff, stored: restored.storedLayout }));
  // 清回默认，免得后续截图带着偏好
  await page.evaluate(() => localStorage.removeItem('textiledream-chat-layout'));

  // ---------------------------------------------------------- 会话切换不串源
  // 关联 → 未关联 → 关联：底图/标记/空态都要跟着当前会话刷新，不能拿上一段的结果顶着。
  const sessionSwitch = await guard(page, label, '会话切换', async () => {
    await page.evaluate((ids) => { window.__fx = ids; }, FIXTURE);
    await page.evaluate((id) => loadSession(id), FIXTURE.linked);
    const backToLinked = await waitFor(page, () => {
      const img = document.getElementById('play-map-img');
      return !!img && !img.hidden && img.naturalWidth > 0 &&
        !!document.querySelector('#play-map-overlay path');
    }, 20000);
    const per = await page.evaluate(async () => {
      const get = async (id) => (await (await fetch('/api/sessions/' + id + '/play-map',
        { headers: { 'X-TextileDream-Token': token } })).json());
      const linked = await get(window.__fx.linked);
      const plain = await get(window.__fx.plain);
      const img = document.getElementById('play-map-img');
      return {
        linkedStatus: linked.status, plainStatus: plain.status,
        linkedHasBbox: !!(linked.basemap && linked.basemap.bbox),
        plainHasBbox: !!(plain.basemap && plain.basemap.bbox),
        plainSource: plain.source || null,
        srcPrefix: String(img.src || '').slice(0, 22),
        overlayPaths: document.querySelectorAll('#play-map-overlay path').length,
        currentId: current && current.id,
      };
    });
    return { backToLinked, per };
  });
  check(label + ' 切回已关联会话后底图与标记都在',
    !!sessionSwitch && sessionSwitch.backToLinked === true,
    JSON.stringify(sessionSwitch && sessionSwitch.backToLinked));
  check(label + ' 两段会话的地图来源不串（一段 ok+bbox、一段 not_linked 无 bbox）',
    !!sessionSwitch && sessionSwitch.per.linkedHasBbox === true &&
    sessionSwitch.per.plainHasBbox === false && sessionSwitch.per.linkedStatus === 'ok' &&
    sessionSwitch.per.plainStatus === 'not_linked' && sessionSwitch.per.plainSource === null,
    JSON.stringify(sessionSwitch && sessionSwitch.per));
  check(label + ' 已关联会话的底图以 data: 显示（CSP 下不用 blob）',
    !!sessionSwitch && sessionSwitch.per.srcPrefix.startsWith('data:image/png'),
    sessionSwitch && sessionSwitch.per.srcPrefix);

  // 主动再切一轮会话：关联 → 未关联（旧图必须收起）→ 关联（图必须回来）
  const flip = await guard(page, label, '会话来回切换', async () => {
    await page.evaluate((id) => loadSession(id), FIXTURE.plain);
    await page.waitForTimeout(1200);
    const mid = await page.evaluate(() => {
      const img = document.getElementById('play-map-img');
      const empty = document.getElementById('play-map-empty');
      return { imgHidden: img.hidden, src: String(img.src || '').slice(0, 12),
               overlay: document.querySelectorAll('#play-map-overlay path').length,
               emptyShown: !!empty && !empty.hidden,
               currentId: current && current.id };
    });
    await page.evaluate((id) => loadSession(id), FIXTURE.linked);
    const backOk = await waitFor(page, () => {
      const img = document.getElementById('play-map-img');
      return !!img && !img.hidden && img.naturalWidth > 0;
    }, 20000);
    const after = await page.evaluate(() => ({
      currentId: current && current.id,
      overlay: document.querySelectorAll('#play-map-overlay path').length,
    }));
    return { mid, backOk, after };
  });
  check(label + ' 切到未关联会话：旧底图被收起、不再画倒三角',
    !!flip && flip.mid.imgHidden === true && flip.mid.overlay === 0 && flip.mid.emptyShown === true,
    JSON.stringify(flip && flip.mid));
  check(label + ' 再切回已关联会话：底图与倒三角重新出现',
    !!flip && flip.backOk === true && flip.after.overlay === 1,
    JSON.stringify(flip && { backOk: flip.backOk, after: flip.after }));

  // ---------------------------------------------------------- 最近几轮新增的界面功能
  // 阅读设置 / 侧栏分组 / 无地图引导 / chat-polish.css / 存档管理 / 世界设定卡片
  await runNewFeatureChecks({
    page, label, check, shot, waitApp, waitFor, guard, fixture: FIXTURE, requests,
    allowMutate: ALLOW_MUTATE, skipped, viewport: { w: width, h: height },
  });

  // 品牌文案：产品名是 TextingDream，旧名只允许留在内部 id / header 里。
  const brand = await page.evaluate(() => ({
    title: document.title,
    brand: (document.querySelector('#topbar .tb-title') || {}).textContent || '',
    legacyBrand: (document.querySelector('#legacy .brand') || {}).textContent || '',
    visibleText: (document.body.innerText || '').includes('TextileDream'),
  }));
  check(label + ' 可见品牌文案是 TextingDream（不出现旧名 TextileDream）',
    brand.title.includes('TextingDream') && brand.brand.includes('TextingDream') &&
    brand.legacyBrand.includes('TextingDream') && brand.visibleText === false,
    JSON.stringify(brand));

  // 网络/接口不泄密钥：假 key 已写进 provider，检查所有 /api 响应
  const leaked = responses.filter((r) => r.leaked);
  check(label + ' 所有 /api 响应与 header 都不回显密钥', leaked.length === 0,
    JSON.stringify(leaked.map((r) => r.url)).slice(0, 300));
  check(label + ' 采到的 /api 响应数 > 3（截图前的真请求）', responses.length > 3, responses.length);

  const realErrors = errors.filter((e) => !/favicon|Failed to load resource/i.test(e));
  check(label + ' 无未捕获脚本异常', realErrors.length === 0, JSON.stringify(realErrors).slice(0, 400));

  await context.close();
  return label;
}

(async () => {
  if (!BASE || /:8000(\/|$)/.test(BASE)) {
    console.error('拒绝运行：TD_BASE 未设置，或指向 8000 端口（用户正在使用的服务）：' + BASE);
    process.exit(2);
  }
  fs.mkdirSync(SHOTS, { recursive: true });
  const browser = await chromium.launch({
    executablePath: fs.existsSync(EDGE) ? EDGE : undefined,
    headless: true,
    args: ['--no-first-run', '--no-default-browser-check'],
  });
  let exitCode = 0;
  try {
    for (const [label, w, h] of VIEWPORTS) await runViewport(browser, label, w, h);
  } catch (error) {
    check('探针未抛异常', false, String(error && error.stack || error).slice(0, 600));
    exitCode = 1;
  } finally {
    await browser.close();
  }
  const passed = checks.filter((c) => c.ok).length;
  const failed = checks.length - passed;
  const report = {
    viewports: VIEWPORTS.map((v) => v[0]),
    // 截图里的底图是验收脚本现画的 fixture 高度图，不是用户世界，也不是最终 civ-atlas 画风。
    // 这些图只用于验布局、锚点与不串源，不能当美术验收稿。
    basemapNote: '底图是 fixture 16 位高度图经服务器掩膜的矩形色块，非最终 civ-atlas 画风，仅供布局/锚点验收',
    fixture: FIXTURE.note || '',
    generatedAt: new Date().toISOString(),
    skipped, mutateAllowed: ALLOW_MUTATE,
    checks, passed, failed,
  };
  fs.writeFileSync(path.join(SHOTS, 'p1-ui-report.json'), JSON.stringify(report, null, 2));
  console.log('\n' + passed + ' PASS / ' + failed + ' FAIL');
  for (const row of checks) if (!row.ok) console.log('FAILED: ' + row.check + ' | ' + row.detail);
  process.exit(failed === 0 ? 0 : 1);
})();
