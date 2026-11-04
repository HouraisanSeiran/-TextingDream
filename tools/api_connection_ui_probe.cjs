const { chromium } = require(require.resolve('playwright', { paths: [require('path').resolve('external/civ-atlas')] }));
const assert = require('node:assert/strict');
const fs = require('node:fs');

(async () => {
  const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [], calls = [];
  page.on('pageerror', error => errors.push(error.stack));
  try {
    let savedConfig = null;
    await page.route('**/api/bootstrap', async route => {
      const response = await route.fetch();
      const boot = await response.json();
      await route.fulfill({ json: { ...boot, ...(savedConfig ? { api: savedConfig } : {}) } });
    });
    await page.route('**/api/settings/api', route => savedConfig ? route.fulfill({ json: savedConfig }) : route.continue());
    await page.goto(process.env.API_UI_TEST_URL || 'http://127.0.0.1:8984/');
    await page.getByRole('button', { name: '连接设置', exact: true }).click();
    const form = page.locator('#api-form');
    await form.waitFor({ state: 'visible' });
    await page.waitForFunction(() => document.querySelector('#api-url').value.length > 0);
    const fields = await form.locator('input,select,textarea').evaluateAll(nodes => nodes.map(node => node.id));
    assert.deepEqual(fields, ['api-url', 'api-key', 'api-protocol', 'api-model']);
    let failModels = false;
    await page.route('**/api/settings/connection/models', route => {
      calls.push({ kind: 'models', body: route.request().postDataJSON() });
      return failModels ? route.fulfill({ status: 400, json: { detail: '模型列表暂不可用，配置未更改' } })
        : route.fulfill({ json: { models: ['test-first', 'test-selected'], selected_model: 'test-first' } });
    });
    await page.route('**/api/settings/connection', route => {
      calls.push({ kind: 'save', body: route.request().postDataJSON() });
      savedConfig = { base_url: 'https://test.example/v1', protocol: 'anthropic', model: route.request().postDataJSON().model, has_key: true, offline: false };
      return route.fulfill({ json: savedConfig });
    });
    await page.route('**/api/settings/api/test', route => {
      calls.push({ kind: 'test' });
      return route.fulfill({ json: { message: '连接成功' } });
    });
    await page.getByLabel('请求地址', { exact: true }).fill('https://test.example/v1');
    await form.locator('#api-key').fill('test-ui-key');
    await form.locator('#api-protocol').selectOption('anthropic');
    const topBefore = await page.locator('#conn-state').innerText();
    await form.locator('#request-models').click();
    await page.waitForFunction(() => document.querySelector('#api-model').options.length === 2);
    assert.equal(await page.locator('#conn-state').innerText(), topBefore);
    await form.locator('#api-model').selectOption('test-selected');
    await page.getByRole('button', { name: '测试连接', exact: true }).click();
    await page.waitForFunction(() => !document.querySelector('#test-api').disabled);
    assert.deepEqual(calls.map(call => call.kind), ['models', 'save', 'test']);
    assert.deepEqual(calls[0].body, { base_url: 'https://test.example/v1', protocol: 'anthropic', api_key: 'test-ui-key' });
    assert.equal(calls[1].body.model, 'test-selected');
    assert.match(await page.locator('#conn-state').innerText(), /^test-selected · 密钥已配置$/);
    assert.equal(await form.locator('#api-key').inputValue(), '');
    failModels = true;
    await form.locator('#request-models').click();
    await page.waitForFunction(() => document.querySelector('#models-status').textContent.includes('暂不可用'));
    assert.match(await page.locator('#conn-state').innerText(), /^test-selected/);
    assert.equal(await form.locator('#api-model').inputValue(), 'test-selected');
    fs.mkdirSync('artifacts/api-connection', { recursive: true });
    await page.screenshot({ path: 'artifacts/api-connection/desktop.png' });
    await page.keyboard.press('Escape');
    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator('#workspace-api').click();
    await form.waitFor({ state: 'visible' });
    assert.equal(await form.locator('input:visible,select:visible').count(), 4);
    const bounds = await form.boundingBox();
    assert(bounds.x >= 0 && bounds.x + bounds.width <= 391);
    await page.screenshot({ path: 'artifacts/api-connection/mobile.png' });
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ fields, modelDiscovery: true, selectedModelInHeader: true, failurePreservesSelection: true, desktopAndMobile: true, errors }));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
