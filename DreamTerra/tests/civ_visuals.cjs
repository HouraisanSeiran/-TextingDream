const { chromium } = require(require.resolve('playwright', {
  paths: [require('node:path').resolve(__dirname, '../../external/civ-atlas')],
}));
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const output = path.resolve(__dirname, '../evidence/civ-visuals');
const base = process.env.DREAM_MAP_URL || 'http://127.0.0.1:8000';
const edge = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const report = { base, views: {}, requests: [], errors: [], blockedWrites: [] };
fs.mkdirSync(output, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true, ...(fs.existsSync(edge) ? { executablePath: edge } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  let phase = 'load';
  page.on('pageerror', error => report.errors.push(error.message));
  page.on('request', request => {
    const url = new URL(request.url());
    if (url.pathname.startsWith('/api/')) {
      report.requests.push({ phase, method: request.method(), path: url.pathname });
    }
  });
  await page.route('**/*', route => {
    const request = route.request();
    if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method())) {
      report.blockedWrites.push({ phase, method: request.method(), url: request.url() });
      return route.abort();
    }
    return route.continue();
  });
  const detail = page.locator('.dream-world-detail');
  const read = () => detail.evaluate(canvas => ({
    ...canvas.dataset, width: canvas.width, height: canvas.height,
    cssWidth: canvas.getBoundingClientRect().width,
  }));
  const settle = () => page.evaluate(() => new Promise(resolve =>
    requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const capture = async name => {
    await settle();
    const view = await read();
    assert.ok(view.source, `${name}: missing world source`);
    assert.ok(Number.isFinite(Number(view.drawMs)) && view.drawMs !== '', `${name}: missing draw time`);
    assert.ok(view.width > 0 && view.height > 0, `${name}: empty canvas`);
    if (report.source) assert.equal(view.source, report.source, `${name}: world source changed`);
    report.views[name] = view;
    await page.screenshot({ path: path.join(output, `${name}.png`) });
    return view;
  };
  try {
    await page.goto(base, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => {
      const canvas = document.querySelector('.dream-world-detail');
      return canvas && canvas.dataset.k === '1' && canvas.dataset.source && canvas.dataset.drawMs;
    }, undefined, { timeout: 90000 });
    const overview = await capture('overview');
    report.source = overview.source;
    assert.ok(Number(overview.eligible) <= 12, 'overview has too many eligible labels');
    assert.equal(await page.locator('.dreamterra-engine-selector:visible').count(), 0,
      'independent DreamTerra entry is visible');
    phase = 'interaction';
    const layers = page.locator('.dream-atlas-layers');
    assert.equal(await layers.getByRole('button').count(), 4);
    const layer = name => layers.getByRole('button', { name, exact: true });
    assert.equal(await layer('山川').getAttribute('aria-pressed'), 'true');
    const political = layer('疆域');
    await political.click();
    assert.equal(await political.getAttribute('aria-pressed'), 'true');
    await capture('territory');
    await layer('山川').click();
    for (const name of ['道路', '地名']) {
      const button = layer(name);
      const before = await button.getAttribute('aria-pressed');
      assert.ok(['true', 'false'].includes(before), `${name}: missing toggle state`);
      await button.click();
      assert.notEqual(await button.getAttribute('aria-pressed'), before, `${name}: did not toggle`);
      await button.click();
      assert.equal(await button.getAttribute('aria-pressed'), before, `${name}: did not restore`);
    }
    const journey = page.locator('.dream-atlas-journey');
    await journey.locator('summary').click();
    assert.equal(await journey.getByLabel('探索起点城镇').count(), 1);
    await journey.locator('summary').click();
    const zoomIn = page.getByRole('button', { name: '放大地图', exact: true });
    for (let i = 0; i < 4; i++) await zoomIn.click();
    await page.waitForFunction(() => Number(document.querySelector('.dream-world-detail')?.dataset.k) > 3.2);
    const regional = await capture('regional');
    assert.ok(Number(regional.eligible) > Number(overview.eligible), 'regional labels did not increase');
    for (let i = 0; i < 2; i++) await zoomIn.click();
    await page.waitForFunction(() => Number(document.querySelector('.dream-world-detail')?.dataset.k) > 6);
    const local = await capture('local');
    assert.ok(Number(local.eligible) >= Number(regional.eligible), 'local labels decreased');
    await page.getByRole('button', { name: '缩小地图', exact: true }).click();
    await page.getByRole('button', { name: '复位', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('.dream-world-detail')?.dataset.k === '1');
    assert.equal((await read()).eligible, overview.eligible);
    await journey.locator('summary').click();
    await journey.getByRole('button', { name: '定位城镇', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('.dream-world-detail')?.dataset.k === '4');
    const inspector = page.getByRole('region', { name: '地理详情' });
    assert.ok((await inspector.innerText()).includes('海拔'));
    await journey.locator('summary').click();
    await capture('town');
    await page.getByRole('button', { name: '关闭地理详情' }).click();
    const bounds = await detail.boundingBox();
    await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);
    await page.mouse.down();
    await page.mouse.move(bounds.x + bounds.width / 2 + 80, bounds.y + bounds.height / 2 + 30, { steps: 8 });
    await page.mouse.up();
    await settle();
    assert.equal((await read()).source, report.source);
    await page.getByRole('button', { name: '复位', exact: true }).click();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForFunction(() => {
      const canvas = document.querySelector('.dream-world-detail');
      return canvas && Math.abs(canvas.width - canvas.getBoundingClientRect().width * devicePixelRatio) < 2;
    });
    await capture('narrow');
    const authorRequests = report.requests.filter(r => r.path.startsWith('/api/inner/native-worlds'));
    report.authorRequests = authorRequests;
    assert.ok(authorRequests.length <= 4, `too many world requests: ${authorRequests.length}`);
    assert.equal(authorRequests.filter(r => r.phase === 'interaction').length, 0, 'zoom requested world data again');
    phase = 'player';
    await page.evaluate(() => window.setNativeMode('player'));
    await page.waitForFunction(() => window.__tdNativeMode === 'player' && !document.querySelector('#native-map-host .dream-world-detail'));
    await page.waitForTimeout(1500);
    report.player = await page.evaluate(() => ({
      mode: window.__tdNativeMode,
      hostHidden: document.getElementById('native-map-host')?.hidden,
      playerText: document.getElementById('player-map-host')?.innerText || '',
    }));
    assert.ok(report.player.hostHidden, 'author map remains visible in player mode');
    assert.equal(report.requests.filter(r => r.phase === 'player' && r.path.startsWith('/api/inner/native-worlds')).length, 0,
      'player mode requested author world data');
    assert.deepEqual(report.blockedWrites, [], 'page attempted a write');
    assert.deepEqual(report.errors, [], 'page errors occurred');
    report.result = 'passed';
  } catch (error) {
    report.result = 'failed';
    report.failure = error.stack || String(error);
    await page.screenshot({ path: path.join(output, 'failure.png') }).catch(() => {});
    process.exitCode = 1;
  } finally {
    fs.writeFileSync(path.join(output, 'browser.json'), JSON.stringify(report, null, 2));
    await browser.close();
    console.log(JSON.stringify({ result: report.result, source: report.source, failure: report.failure, output }));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
