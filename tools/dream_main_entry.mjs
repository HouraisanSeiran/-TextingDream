// 主入口真浏览器验收的浏览器侧：打开 `/`，看原生地图是否真的挂上、作者生成是否真的跑通。
//
// 不看源码、不看假数据：它等真像素、真请求、真导入记录。
//
// 注意：**所有页内脚本都传函数，不传字符串**。这个页面带着 `script-src 'self'` 的 CSP，
// 字符串 evaluate / waitForFunction 会走页内 eval 被拦下（实测 EvalError）。传函数由
// Playwright 通过调试协议注入，不触发 CSP。
//
// 每一步都往 stderr 打一行 `[step] …`（带毫秒）：卡在哪一步能一眼看出，不用等到超时。
//
// 用法： node tools/dream_main_entry.mjs <baseUrl> [cells]  → stdout 一行 JSON
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const UPSTREAM = join(HERE, '..', 'external', 'civ-atlas');
// playwright 装在上游树里（本仓根没有 node_modules，也不该为这件事引一份）
const upstreamRequire = createRequire(join(UPSTREAM, 'package.json'));
const { chromium } = upstreamRequire('playwright');
const read = (p) => { try { return readFileSync(p); } catch { return null; } };
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

const BASE = (process.argv[2] || '').replace(/\/$/, '');
if (!BASE) {
  console.error('用法：dream_main_entry.mjs <baseUrl> [cells]');
  process.exit(2);
}
const CELLS = Number(process.argv[3] || 6000);

const T0 = Date.now();
const step = (text) => process.stderr.write(`[step +${((Date.now() - T0) / 1000).toFixed(1)}s] ${text}\n`);

/** 量一次页面：原生挂载点、画布、作者控件、错误。 */
function measure() {
  const host = document.getElementById('native-map-host');
  const canvas = document.querySelector('#native-map-host .dream-host-stage canvas');
  const first = host ? host.firstElementChild : null;
  const out = {
    hasHost: !!host,
    hostText: (host ? host.innerText : '').slice(0, 400),
    hostState: first && first.dataset ? first.dataset.state || null : null,
    hasCanvas: !!canvas,
    importSelect: !!document.querySelector('#native-map-host select[aria-label="选择原件"]'),
    createButton: !![...document.querySelectorAll('#native-map-host button')]
      .find((b) => (b.textContent || '').includes('新建世界')),
    errors: (window.__probeErrors || []).slice(0, 8),
  };
  if (canvas) {
    out.canvasBitmap = [canvas.width, canvas.height];
    if (canvas.width > 0 && canvas.height > 0) {
      const ctx = canvas.getContext('2d');
      const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
      const colors = new Set();
      let opaque = 0;
      let sampled = 0;
      const stride = Math.max(1, Math.floor(Math.min(canvas.width, canvas.height) / 120));
      for (let y = 0; y < canvas.height; y += stride) {
        for (let x = 0; x < canvas.width; x += stride) {
          const at = (y * canvas.width + x) * 4;
          colors.add((data[at] << 16) | (data[at + 1] << 8) | data[at + 2]);
          if (data[at + 3] === 255) opaque += 1;
          sampled += 1;
        }
      }
      out.distinctColors = colors.size;
      out.opaqueRatio = sampled ? opaque / sampled : 0;
    }
  }
  return out;
}

const report = { base: BASE, cells: CELLS };
let browser;
let watcher = null;
try {
  browser = await chromium.launch(read(EDGE) ? { executablePath: EDGE } : {});
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const requests = [];
  const consoleErrors = [];
  page.on('request', (r) => {
    const url = new URL(r.url());
    if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/native-map/')) {
      requests.push(r.method() + ' ' + url.pathname);
    }
  });
  page.on('console', (m) => {
    if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 300));
  });
  page.on('pageerror', (e) => consoleErrors.push('pageerror: ' + String(e).slice(0, 300)));

  step('打开 ' + BASE + '/');
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => {
    window.__probeErrors = [];
    window.addEventListener('error', (e) => window.__probeErrors.push(String(e.message)));
    window.addEventListener('unhandledrejection', (e) => window.__probeErrors.push(String(e.reason)));
  });

  step('等原生宿主挂上');
  await page.waitForFunction(() => !!document.querySelector('#native-map-host .dream-host'),
    undefined, { timeout: 120000, polling: 250 });
  report.mounted = await page.evaluate(measure);
  step('已挂上：' + JSON.stringify({ canvas: report.mounted.canvasBitmap || null,
    state: report.mounted.hostState }));

  report.emptyState = await page.evaluate(() => ({
    form: !!document.querySelector('#native-map-host .dream-create'),
    hint: (document.querySelector('#native-map-host .dream-host-stage') || {}).innerText || '',
    optionCount: document.querySelectorAll('#native-map-host select[aria-label="选择原件"] option').length,
  }));
  step('空态：' + JSON.stringify(report.emptyState).slice(0, 240));

  // ---------------------------------------------------------------- 作者生成
  await page.evaluate((cells) => {
    const form = document.querySelector('#native-map-host .dream-create');
    if (!form) return;
    const setVal = (node, v) => {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      setter.call(node, String(v));
      node.dispatchEvent(new Event('input', { bubbles: true }));
    };
    for (const label of form.querySelectorAll('label')) {
      if ((label.textContent || '').trim() === '地块数') setVal(label.querySelector('input'), cells);
    }
  }, CELLS);

  const worldsCount = () => page.evaluate(async () => {
    const response = await fetch('/api/inner/native-worlds',
      { headers: { 'X-TextileDream-Token': window.__textileDreamToken || '' } });
    if (!response.ok) return -1;
    const rows = await response.json();
    return Array.isArray(rows) ? rows.length : -1;
  });

  report.worldsBefore = await worldsCount();
  step('已登记世界数（前）：' + report.worldsBefore);

  step('点「生成并登记」');
  await page.evaluate(() => {
    const form = document.querySelector('#native-map-host .dream-create');
    const submit = [...form.querySelectorAll('button')]
      .find((b) => (b.textContent || '').includes('生成并登记'));
    submit.click();
  });

  // 每 8 秒记一行当前阶段，卡住能看出停在哪
  watcher = setInterval(async () => {
    try {
      const now = await page.evaluate(() => {
        const bar = document.querySelector('#native-map-host .dream-host-bar');
        const status = bar ? (bar.querySelector('[role=status]') || {}).textContent || '' : '';
        const alert = document.querySelector('#native-map-host [role=alert]');
        const notice = document.querySelector('#native-map-host .dream-host > p');
        const c = document.querySelector('#native-map-host .dream-host-stage canvas');
        return {
          status: status.trim(),
          alert: alert ? (alert.textContent || '').trim().slice(0, 200) : null,
          stageText: (document.querySelector('#native-map-host .dream-host-stage') || {}).innerText || '',
          foot: (document.querySelector('#native-map-host .dream-host-foot') || {}).innerText || '',
          notice: notice ? (notice.textContent || '').trim().slice(0, 160) : null,
          canvas: c ? [c.width, c.height] : null,
        };
      });
      step('进度：' + JSON.stringify(now));
    } catch (error) { /* 页面在导航：下轮再看 */ }
  }, 8000);

  step('等画布出像素（上限 10 分钟）');
  await page.waitForFunction(() => {
    const c = document.querySelector('#native-map-host .dream-host-stage canvas');
    return !!c && c.width > 0 && c.height > 0;
  }, undefined, { timeout: 600000, polling: 500 });
  clearInterval(watcher);
  watcher = null;
  report.generateMs = Date.now() - T0;
  report.afterCreate = await page.evaluate(measure);
  report.worldsAfter = await worldsCount();
  report.footText = await page.evaluate(() =>
    (document.querySelector('#native-map-host .dream-host-foot') || {}).innerText || '');
  step('已出图，颜色数 ' + report.afterCreate.distinctColors + '，世界数 ' + report.worldsAfter);
  report.requests = requests.slice();
  report.consoleErrors = consoleErrors.slice(0, 10);

  step('刷新验证世界是否被服务端记住');
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => {
    const c = document.querySelector('#native-map-host .dream-host-stage canvas');
    return !!c && c.width > 0;
  }, undefined, { timeout: 180000, polling: 500 });
  report.afterReload = await page.evaluate(measure);
  step('刷新后：' + JSON.stringify(report.afterReload.canvasBitmap || null)
    + ' 颜色数 ' + report.afterReload.distinctColors);

  // ------------------------------------------------ 进入旅程：作者原件必须 0 请求
  // 走的是**应用自己的入口**：`window.loadSession()` 第一行就是 setNativeMode('player')，
  // 再拉 /api/sessions/{id}。空世界、没有故事包时后端会拒建旅程（400），
  // 但“切到玩家模式”这一步真实的发生了 —— 这正是要验的那条代码路径，
  // 而不是另起一个独立的 player 挂载来冒充。
  const madeSession = await page.evaluate(async () => {
    const token = window.__textileDreamToken || '';
    const response = await fetch('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-TextileDream-Token': token },
      body: JSON.stringify({ title: '验收旅程', mode: 'protagonist' }),
    });
    return { status: response.status, body: (await response.text()).slice(0, 200) };
  });
  report.session = madeSession;
  step('新建旅程：' + JSON.stringify(madeSession));

  // 无论旅程能不能建（没有故事包时 400），都走一遍应用切换成玩家的真实入口
  requests.length = 0;
  const switched = await page.evaluate(async () => {
    const before = window.__tdNativeMode || null;
    // 用不存在的 id：目的只看“切模式”这一步（它在读会话之前就发生），不在拿到会话内容
    try { await window.loadSession('sc_' + '0'.repeat(12), false); } catch (error) { /* 没这段旅程，预期内 */ }
    return { before, after: window.__tdNativeMode || null };
  });
  report.modeSwitch = switched;
  await page.waitForFunction(() => !document.querySelector('#native-map-host .dream-host'),
    undefined, { timeout: 60000, polling: 250 });
  // 再等一小会儿：确认没有“晚到的”作者原件请求洩回来
  await new Promise((resolve) => setTimeout(resolve, 1500));
  report.afterSession = await page.evaluate(measure);
  report.sessionAuthorRequests = requests.filter((r) => r.includes('/api/inner/native-worlds'));
  step('切到玩家：' + JSON.stringify(switched) + '，宿主已卸下='
    + !report.afterSession.hasCanvas + '，作者原件请求数=' + report.sessionAuthorRequests.length);

  await page.close();

  const drawn = report.afterCreate || {};
  report.ok = Boolean(
    // 空态：还没生成世界 → 没有像素（canvas 元素在但位图 0×0）、没有已登记世界、新建面板自动展开
    report.mounted?.canvasBitmap?.[0] === 0
    && report.emptyState?.optionCount === 0
    && report.emptyState?.form === true
    // 生成闭环：真出像素 + 服务端真多了一条登记 + 刷新后仍在
    && drawn.distinctColors > 30
    && (report.worldsAfter || 0) > (report.worldsBefore ?? 0)
    && (report.afterReload?.distinctColors || 0) > 30
    // 作者/玩家分离：切到玩家后作者宿主真卸下、作者原件 0 请求
    && report.modeSwitch?.after === 'player'
    && report.sessionAuthorRequests
    && report.sessionAuthorRequests.length === 0
    && report.afterSession
    && report.afterSession.hasCanvas === false
    && report.afterSession.hostState === 'not_ready',
  );
} catch (error) {
  report.ok = false;
  report.error = String(error && error.message ? error.message : error).slice(0, 2000);
  step('失败：' + report.error);
} finally {
  if (watcher) clearInterval(watcher);
  await browser?.close();
}

console.log(JSON.stringify(report));
process.exit(report.ok ? 0 : 1);
