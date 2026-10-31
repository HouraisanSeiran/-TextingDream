const {chromium} = require(require.resolve('playwright', {paths: [require('path').resolve('external/civ-atlas')]}));
const fs = require('fs');
const assert = require('assert');
(async () => {
  const browser = await chromium.launch({executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true});
  const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  try {
    await page.goto('http://127.0.0.1:8978/');
    await page.waitForFunction(() => typeof window.loadSession === 'function' && window.__textileDreamToken);
    await page.evaluate(id => window.loadSession(id), process.argv[2]);
    await page.locator('#short-scene').waitFor({state: 'visible'});
    assert((await page.locator('#short-scene').innerText()).includes('共18便士'));
    const act = async id => {
      await page.locator(`[data-action-id="${id}"]`).click();
      await page.locator('#demo-confirm').waitFor({state: 'visible'});
      const response = page.waitForResponse(r => r.url().endsWith('/chat') && r.request().method() === 'POST', {timeout:60000});
      await page.locator('#demo-confirm-run').click();
      const completed = await response;
      assert(completed.ok(), await completed.text());
      await page.locator('#demo-confirm').waitFor({state: 'hidden', timeout: 60000});
      await page.waitForTimeout(150);
    };
    await page.screenshot({path: 'artifacts/playable-scenes/frontend-start.png', fullPage: true});
    await act('buy_ale');
    await page.waitForFunction(() => document.querySelector('#short-scene').textContent.includes('共16便士'));
    await page.locator('#story-text .prose').first().waitFor();
    assert((await page.locator('#story-text .prose').first().innerText()).length > 10);
    assert((await page.locator('#story-text .input').first().innerText()).includes('麦酒'));
    await act('ask_job');
    await act('go_search');
    await page.locator('[data-short-destination="yard"]').click();
    await page.locator('#demo-confirm-run').click();
    await page.locator('[data-action-id="steal_linen"]').waitFor({state: 'visible'});
    await page.locator('[data-action-id="steal_linen"]').click();
    await page.locator('#demo-confirm').waitFor({state: 'visible'});
    const risk = await page.locator('#demo-confirm-body').innerText();
    assert(risk.includes('风险') || risk.includes('私物'));
    await page.screenshot({path: 'artifacts/playable-scenes/frontend-risk-confirm.png', fullPage: true});
    await page.locator('#demo-confirm-cancel').click();
    assert.equal(errors.length, 0, errors.join('\n'));
    fs.writeFileSync('artifacts/playable-scenes/browser-evaluation.json', JSON.stringify({passed:true,checks:['opening balance','paid action and live model reply','event progression','text travel','risk confirmation and cancellation'],pageErrors:errors}, null, 2));
    console.log('PASS: opening, payment, live dialogue, progression, travel, risk confirmation; no page errors.');
  } catch (error) {
    console.error('UI state:', await page.locator('#short-scene').innerText(), await page.locator('#notice').innerText(), errors);
    await page.screenshot({path: 'artifacts/playable-scenes/frontend-failure.png', fullPage: true});
    throw error;
  } finally { await browser.close(); }
})().catch(e => {console.error(e);process.exitCode = 1;});
