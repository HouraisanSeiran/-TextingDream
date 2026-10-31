const {chromium} = require(require.resolve('playwright', {paths: [require('path').resolve('external/civ-atlas')]}));
const assert = require('node:assert/strict');
const fs = require('node:fs');

(async () => {
  const browser = await chromium.launch({executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true});
  const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  fs.mkdirSync('artifacts/npc-cards', {recursive: true});
  try {
    await page.goto(process.env.NPC_CARD_TEST_URL || 'http://127.0.0.1:18765');
    await page.waitForFunction(() => Boolean(window.__textileDreamToken));
    await page.locator('#workspace-npc-cards').click();
    const panel = page.locator('#npc-cards');
    const goal = panel.getByLabel('当前目标', {exact: true});
    await goal.fill('保住酒馆生意，先核实旅人的来意');
    await panel.getByLabel('选择 NPC').selectOption('ferryman');
    await panel.getByLabel('选择 NPC').selectOption('bess');
    assert.equal(await goal.inputValue(), '保住酒馆生意，先核实旅人的来意');
    await panel.getByRole('button', {name: '＋ 添加所知或误解', exact: true}).click();
    await panel.getByLabel('说法', {exact: true}).fill('渡船工可能拿走了账本');
    await panel.getByLabel('来源', {exact: true}).fill('听常客猜测');
    await panel.getByLabel('性质', {exact: true}).selectOption('rumor');
    await panel.getByRole('button', {name: '保存角色卡为新版本', exact: true}).click();
    await page.waitForFunction(() => document.getElementById('notice').textContent.includes('角色卡已保存'));
    await panel.getByRole('button', {name: '读取最新角色卡', exact: true}).click();
    await page.waitForFunction(() => document.querySelector('#npc-cards textarea[name="goal"]').value.includes('保住酒馆'));
    assert.equal(await panel.getByLabel('说法', {exact: true}).inputValue(), '渡船工可能拿走了账本');
    assert.equal(await panel.getByLabel('可用于公开对话', {exact: true}).last().isChecked(), false);
    await page.screenshot({path: 'artifacts/npc-cards/desktop.png', fullPage: true});
    await page.evaluate(async () => {
      const bootstrap = await api('/bootstrap');
      await loadSession(bootstrap.sessions[0].id);
      await TDNav.show('npc-cards');
    });
    await panel.getByRole('button', {name: '查看当前旅程角色与记忆', exact: true}).click();
    await page.waitForFunction(() => document.querySelector('#npc-cards textarea[name="goal"]').disabled);
    assert.equal(await goal.inputValue(), ''); // the journey pins the old package
    await page.setViewportSize({width: 390, height: 844});
    await panel.getByRole('button', {name: '读取最新角色卡', exact: true}).click();
    await page.waitForFunction(() => !document.querySelector('#npc-cards textarea[name="goal"]').disabled);
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    await page.screenshot({path: 'artifacts/npc-cards/mobile.png', fullPage: true});
    assert.deepEqual(errors, []);
    console.log('PASS: edit, switch drafts, save/reload, private knowledge, pinned read-only journey, mobile layout, no page errors');
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
