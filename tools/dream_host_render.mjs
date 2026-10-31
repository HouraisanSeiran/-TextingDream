// 宿主壳的**真浏览器**探针（给 tests/test_civ_native_contract.py 调）。
//
// 加载构建好的 `dist-dream/dream-host.js`（不是源码、不是模拟），由本地静态服务供应；
// 两个作者路由用 Playwright `page.route` 应答**真实形状**（`app/native_worlds.py` 的
// listing / detail / snapshot 字段），字节用真的 4.6 MB `.civsnap`。
//
// 测的是只靠类型/字符串断言不到的四件事：
//   1. 包在浏览器里能启动（没有 `process is not defined`，没有 crypto.subtle 崩）；
//   2. 地图真的画出了像素（颜色数、不透明比例）；
//   3. 非 2:1 舞台上地图框**居中**（与 `ui/mapWrap.ts` 的 boxLeft/boxTop 一致）；
//   4. 换原件时旧图被清掉、迟到的旧响应不会盖回新的；玩家模式一个作者路由都不请求。
//
// 用法： node tools/dream_host_render.mjs <real.civsnap> <dream-host.js>  → 一行 JSON
import { readFileSync } from 'node:fs';
import { createServer } from 'node:http';
import { dirname, join, resolve } from 'node:path';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';

const [, , SAMPLE, BUNDLE] = process.argv;
if (!SAMPLE || !BUNDLE) {
  console.error('用法：dream_host_render.mjs <real.civsnap> <dream-host.js>');
  process.exit(2);
}
const bundlePath = resolve(BUNDLE);
const outDir = dirname(bundlePath);
const container = readFileSync(SAMPLE);
const wholeSum = createHash('sha256').update(container).digest('hex');

// playwright 装在 upstream 里，从那里解析（脚本本身在仓库根 tools/）
const upstreamRequire = createRequire(join(outDir, '..', 'package.json'));
const { chromium } = upstreamRequire('playwright');
const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const exists = (p) => { try { return readFileSync(p) && true; } catch { return false; } };

const IMPORT_A = 'sn_aaaaaaaaaaaa';
const IMPORT_B = 'sn_bbbbbbbbbbbb';
const WORLD_ID = 'wmvrpuwi29m3yi';
const TOKEN = 'test-token';

const listing = [
  { import_id: IMPORT_A, created: '2026-01-01T00:00:00+00:00', sha256: wholeSum.slice(0, 16),
    bytes: container.length, world_id: WORLD_ID, snapshot_format: 1, generator_version: 45,
    parts: [] },
  { import_id: IMPORT_B, created: '2026-01-01T00:01:00+00:00', sha256: wholeSum.slice(0, 16),
    bytes: container.length, world_id: WORLD_ID, snapshot_format: 1, generator_version: 45,
    parts: [] },
];

function detailOf(importId) {
  return {
    identity: { import_id: importId, sha256: wholeSum, bytes: container.length,
                file: wholeSum.slice(0, 32) + '.civsnap', world_id: WORLD_ID,
                world_app: 'civ-atlas', snapshot_format: 1, generator_version: 45,
                exported_at: '2026-01-01T00:00:00+00:00', extractor: '织梦',
                spec_commit: '0939c5f', license: 'AGPL-3.0-only' },
    story_revision: null, story_id: null,
    parts: [], available: true,
  };
}

const PAGES = {
  '/author.html': `<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>dream host</title>
<link rel="stylesheet" href="/dream-host.css">
<style>html,body{margin:0}#host{width:900px;height:520px}</style>
</head><body><div id="host"></div>
<script type="module">
  window.__textileDreamToken = '${TOKEN}';
  window.__errors = [];
  window.addEventListener('error', (e) => window.__errors.push(String(e.message)));
  window.addEventListener('unhandledrejection', (e) => window.__errors.push(String(e.reason)));
  const originalError = console.error;
  console.error = (...args) => { window.__errors.push(args.map(String).join(' ')); originalError(...args); };
  import('/dream-host.js').then((mod) => {
    mod.mountDreamHost(document.getElementById('host'), { mode: 'author' });
    window.__booted = true;
  }).catch((e) => window.__errors.push('import 失败：' + e));
</script></body></html>`,
  '/player.html': `<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>dream host player</title>
<link rel="stylesheet" href="/dream-host.css">
<style>html,body{margin:0}#host{width:900px;height:520px}</style>
</head><body><div id="host"></div>
<script type="module">
  window.__textileDreamToken = '${TOKEN}';
  window.__errors = [];
  window.addEventListener('error', (e) => window.__errors.push(String(e.message)));
  window.addEventListener('unhandledrejection', (e) => window.__errors.push(String(e.reason)));
  import('/dream-host.js').then((mod) => {
    mod.mountDreamHost(document.getElementById('host'), { mode: 'player' });
    window.__booted = true;
  }).catch((e) => window.__errors.push('import 失败：' + e));
</script></body></html>`,
};

const server = createServer((request, response) => {
  const path = (request.url || '/').split('?')[0];
  if (PAGES[path]) {
    response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    response.end(PAGES[path]);
    return;
  }
  if (path === '/dream-host.js' || path === '/dream-host.css') {
    const type = path.endsWith('.css') ? 'text/css; charset=utf-8' : 'text/javascript; charset=utf-8';
    response.writeHead(200, { 'Content-Type': type });
    response.end(readFileSync(join(outDir, path.slice(1))));
    return;
  }
  response.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
  response.end('not found: ' + path);
});
await new Promise((done) => server.listen(0, '127.0.0.1', done));
const port = server.address().port;
const base = `http://127.0.0.1:${port}`;

/** 页面里量一次：画布像素、位置、舞台尺寸、错误。 */
const MEASURE = `(() => {
  const canvas = document.querySelector('.dream-host-stage canvas');
  const stage = document.querySelector('.dream-host-stage');
  if (!canvas || !stage) return { missing: true, text: document.body.innerText };
  const cr = canvas.getBoundingClientRect();
  const sr = stage.getBoundingClientRect();
  const ctx = canvas.getContext('2d');
  const frame = canvas.parentElement;
  const out = {
    stage: [Math.round(sr.width), Math.round(sr.height)],
    box: [Math.round(frame.offsetWidth), Math.round(frame.offsetHeight)],
    canvasBitmap: [canvas.width, canvas.height],
    canvasCss: [Math.round(cr.width), Math.round(cr.height)],
    boxLeft: cr.left - sr.left,
    boxTop: cr.top - sr.top,
    select: document.querySelector('select[aria-label="选择原件"]')?.value ?? null,
    error: (document.querySelector('[role="alert"]')?.textContent || '').trim(),
    foot: (document.querySelector('.dream-host-foot')?.textContent || '').trim(),
  };
  if (canvas.width > 0 && canvas.height > 0) {
    const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
    const colors = new Set();
    let opaque = 0;
    let sampled = 0;
    const step = 7;
    for (let y = 0; y < canvas.height; y += step) {
      for (let x = 0; x < canvas.width; x += step) {
        const at = (y * canvas.width + x) * 4;
        colors.add((data[at] << 16) | (data[at + 1] << 8) | data[at + 2]);
        if (data[at + 3] === 255) opaque += 1;
        sampled += 1;
      }
    }
    out.distinctColors = colors.size;
    out.opaqueRatio = sampled ? opaque / sampled : 0;
  }
  return out;
})()`;

async function waitCanvas(page, predicate, timeout = 120000) {
  try {
    await page.waitForFunction(predicate, undefined, { timeout, polling: 250 });
  } catch (error) {
    // 不静默超时：把页面此刻看到的东西一并抛出来，否则无法定位到是启动失败还是绘制失败
    const dump = await page.evaluate(`(() => ({
      errors: window.__errors || ['(没有 __errors)'],
      booted: !!window.__booted,
      text: document.body.innerText.slice(0, 800),
      html: document.getElementById('host')?.innerHTML.slice(0, 500) || '(空)',
      canvas: (() => { const c = document.querySelector('.dream-host-stage canvas');
                       return c ? [c.width, c.height] : null; })(),
    }))()`);
    throw new Error('等画布超时：' + JSON.stringify(dump) + ' / ' + String(error && error.message));
  }
}

const report = { sample: SAMPLE, bundle: bundlePath, bundleBytes: readFileSync(bundlePath).length };
const browser = await chromium.launch(exists(EDGE) ? { executablePath: EDGE } : {});
try {
  // ---------------------------------------------------------------- 作者模式
  const page = await browser.newPage();
  const authorRequests = [];
  let slowImport = null;      // 对这个 import 的 snapshot 故意延迟
  let corruptImport = null;   // 对这个 import 的 snapshot 返回坏字节
  // 用正则（不用 glob）：`**/x*` 里的 `*` 不跨 `/`，抓不到 `/snapshot` 子路径。
  await page.route(/\/api\/inner\/native-worlds/, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    authorRequests.push(url.pathname);
    if (request.headers()['x-textiledream-token'] !== TOKEN) {
      return route.fulfill({ status: 403, body: '禁止访问' });
    }
    if (url.pathname === '/api/inner/native-worlds') {
      return route.fulfill({ status: 200, contentType: 'application/json',
                             body: JSON.stringify(listing) });
    }
    const match = url.pathname.match(/^\/api\/inner\/native-worlds\/([^/]+)(\/snapshot)?$/);
    if (!match) return route.fulfill({ status: 404, body: 'no route' });
    const importId = decodeURIComponent(match[1]);
    if (!match[2]) {
      if (slowImport === importId) await new Promise((r) => setTimeout(r, 2500));
      return route.fulfill({ status: 200, contentType: 'application/json',
                             body: JSON.stringify(detailOf(importId)) });
    }
    if (corruptImport === importId) {
      // 截断的字节：如果这个响应真的被用上，解压会失败并报错
      return route.fulfill({ status: 200, contentType: 'application/octet-stream',
                             body: container.subarray(0, 4096) });
    }
    if (slowImport === importId) await new Promise((r) => setTimeout(r, 2500));
    return route.fulfill({ status: 200, contentType: 'application/octet-stream', body: container });
  });

  await page.goto(`${base}/author.html`);
  await waitCanvas(page, `(() => {
    const c = document.querySelector('.dream-host-stage canvas');
    return !!c && c.width > 0;
  })()`, 180000);
  report.boot = { errors: await page.evaluate('window.__errors') };
  const drawn = await page.evaluate(MEASURE);
  report.drawn = drawn;
  report.drawn.importId = listing[0].import_id;
  // 旧图可以清空或卸载；只核对加载期间没有留下旧画面。
  await page.evaluate(() => {
    window.__clears = 0;
    const stage = document.querySelector('.dream-host-stage');
    if (stage) {
      new MutationObserver(() => {
        const canvas = stage.querySelector('canvas');
        if (!canvas || canvas.width === 0 || canvas.height === 0) window.__clears += 1;
      }).observe(stage, { childList: true, subtree: true, attributeFilter: ['width', 'height'] });
    }
  });

  // ---------------------------------------------------------------- 切原件
  // 先把当前世界统一切成 A（默认选的是清单里最新那条 = B），
  // 否则“切到 B”可能根本没变值，也就不存在“换原件”这个动作。
  await page.selectOption('select[aria-label="选择原件"]', IMPORT_A);
  await waitCanvas(page, `(() => {
    const c = document.querySelector('.dream-host-stage canvas');
    return !!c && c.width > 0;
  })()`, 180000);
  await page.evaluate(() => { window.__clears = 0; });

  // B 先慢速（2.5 s）且返回坏字节：切过去的瞬间旧图必须被清掉；
  // 在它回来前切回 A（快），B 的迟到响应必须被丢弃——否则会报错并清空画布。
  slowImport = IMPORT_B;
  corruptImport = IMPORT_B;
  await page.selectOption('select[aria-label="选择原件"]', IMPORT_B);
  await page.waitForTimeout(400);
  const duringSwitch = await page.evaluate(`(() => {
    const c = document.querySelector('.dream-host-stage canvas');
    return { bitmap: c ? [c.width, c.height] : null,
             foot: document.body.innerText.includes('未选择原件') };
  })()`);
  const clearsDuringSwitch = await page.evaluate(() => window.__clears || 0);
  await page.selectOption('select[aria-label="选择原件"]', IMPORT_A);
  await waitCanvas(page, `(() => {
    const c = document.querySelector('.dream-host-stage canvas');
    return !!c && c.width > 0;
  })()`, 180000);
  await page.waitForTimeout(4000);       // 等 B 的迟到响应回来（若被用上就会清空画布 + 报错）
  const afterSwitch = await page.evaluate(MEASURE);
  report.switched = {
    clearedWhileLoading: clearsDuringSwitch > 0,
    duringSwitch,
    lateResponseDropped: afterSwitch.canvasBitmap?.[0] > 0 && !afterSwitch.error,
    finalImportId: afterSwitch.select,
    after: afterSwitch,
  };
  report.authorRequests = authorRequests.slice();
  await page.close();

  // ---------------------------------------------------------------- 玩家模式
  const playerPage = await browser.newPage();
  const playerAuthor = [];
  await playerPage.route(/\/api\//, async (route) => {
    playerAuthor.push(new URL(route.request().url()).pathname);
    return route.fulfill({ status: 500, body: '玩家模式不应请求作者路由' });
  });
  await playerPage.goto(`${base}/player.html`);
  await playerPage.waitForTimeout(2500);
  report.player = {
    authorRequests: playerAuthor.slice(),
    text: await playerPage.evaluate('document.body.innerText'),
    errors: await playerPage.evaluate('window.__errors'),
  };
  await playerPage.close();
} finally {
  await browser.close();
  server.close();
}

console.log(JSON.stringify({ ok: true, ...report }));
