/* p1_ui_probe.cjs 的「最近几轮新增界面功能」检查段，拆成单独文件只为不让主探针继续膨胀。
 *
 * 覆盖：阅读设置、侧栏分组（可折叠、存 localStorage）、无地图引导、chat-polish.css 已加载、
 *       存档管理（⋯ 菜单 / 重命名对话框 / 删除确认）、元素数据库页的世界设定卡片。
 *
 * 约束：
 *   - 存档管理会真的 PATCH / DELETE /api/sessions/{id}，只在 TD_ALLOW_MUTATE=1 时运行，
 *     并且只动本段自己新建、标题以「UI探针」开头的存档；主探针另外保证 TD_BASE 不是 8000 端口。
 *   - 世界设定只验证渲染与「查看大类元素」；不点保存、不点生成、不点推荐，
 *     并用请求记录断言整段没有发出 PUT /inner/world-setting 与 /worldview/generate。
 *   - chat-polish.css 只断言样式表已加载、伪元素文案存在，不做像素比对。
 */
'use strict';

const TEST_PREFIX = 'UI探针';

async function waitArg(page, fn, arg, ms) {
  // 页面 CSP 禁止 eval，所以不用 page.waitForFunction，自己轮询 page.evaluate。
  const end = Date.now() + (ms || 10000);
  while (Date.now() < end) {
    try { if ((await page.evaluate(fn, arg)) === true) return true; } catch (e) { /* 导航中 */ }
    await page.waitForTimeout(120);
  }
  return false;
}

const js = (v) => JSON.stringify(v);

async function openDrawer(page) {
  await page.evaluate(() => window.TDConversationDrawer.open());
  await page.waitForTimeout(380);
}

const drawerExpanded = (page) =>
  page.evaluate(() => document.getElementById('play-left').classList.contains('is-expanded'));

const bootstrapSessions = (page) => page.evaluate(async () => {
  const r = await fetch('/api/bootstrap', { headers: { 'X-TextileDream-Token': token } });
  return (await r.json()).sessions.map((s) => ({ id: s.id, title: s.title }));
});

const readState = (page) => page.evaluate(() => {
  const s = document.getElementById('story-text');
  const cs = getComputedStyle(s);
  const pressed = (k) => {
    const b = document.querySelector('#info-reading .read-group[data-read="' + k + '"] button[aria-pressed="true"]');
    return b ? b.dataset.value : null;
  };
  let stored = null;
  try { stored = localStorage.getItem('textiledream-reading'); } catch (e) { stored = 'ERR'; }
  return {
    sizeVar: s.style.getPropertyValue('--read-size'), leadVar: s.style.getPropertyValue('--read-leading'),
    fontSize: cs.fontSize, lineHeight: cs.lineHeight,
    pressedSize: pressed('size'), pressedLead: pressed('leading'), stored,
  };
});

const authorState = (page) => page.evaluate(() => {
  const t = document.getElementById('workspace-author-toggle');
  const body = document.getElementById('workspace-author-group');
  let stored = null;
  try { stored = localStorage.getItem('textiledream-author-group'); } catch (e) { stored = 'ERR'; }
  return {
    expanded: t ? t.getAttribute('aria-expanded') : null,
    bodyDisplay: body ? getComputedStyle(body).display : null,
    collapsedClass: !!(t && t.parentElement.classList.contains('is-collapsed')),
    bodyVisible: !!body && body.getBoundingClientRect().height > 20,
    stored,
  };
});

/* ------------------------------------------------------------------ 阅读设置 + 侧栏分组 */
async function readingAndSidebar(c) {
  const { page, label, check, shot, waitApp, waitFor, fixture } = c;
  await page.evaluate(() => { localStorage.removeItem('textiledream-reading'); localStorage.removeItem('textiledream-author-group'); });
  await page.evaluate((id) => loadSession(id), fixture.linked);
  await waitFor(page, () => !!current && !!document.getElementById('story-text'), 15000);
  await openDrawer(page);

  // ---- 侧栏分组结构
  const g = await page.evaluate(() => {
    const play = document.getElementById('workspace-group-play');
    const author = document.getElementById('workspace-group-author');
    const sb = document.getElementById('workspace-sidebar').getBoundingClientRect();
    const labelOf = (n) => (n ? (n.querySelector('.workspace-label') || n).textContent.replace(/\s+/g, ' ').trim() : null);
    return {
      sidebarW: Math.round(sb.width),
      playLabel: labelOf(play), authorLabel: labelOf(author),
      playHasMap: !!play && !!play.querySelector('#workspace-author-map'),
      authorHas: ['workspace-new-world', 'workspace-elements', 'workspace-map-tools', 'workspace-other']
        .filter((id) => author && author.querySelector('#' + id)),
      authorOwnsToggle: !!author && !!author.querySelector('#workspace-author-toggle'),
    };
  });
  check(label + ' 侧栏有「游玩」「作者工具」两组，入口各归其组',
    g.sidebarW > 100 && /^游玩/.test(g.playLabel || '') && /^作者工具/.test(g.authorLabel || '') &&
    g.playHasMap && g.authorHas.length === 4 && g.authorOwnsToggle,
    '侧栏分组结构不对：' + JSON.stringify(g));
  const a0 = await authorState(page);
  check(label + ' 作者工具组默认展开且内容可见（没有偏好时）',
    a0.expanded === 'true' && a0.bodyVisible && a0.bodyDisplay !== 'none' && !a0.collapsedClass && a0.stored === null,
    '作者组默认状态应为展开：' + JSON.stringify(a0));

  // ---- 折叠 + 存偏好
  await page.click('#workspace-author-toggle');
  await page.waitForTimeout(250);
  const a1 = await authorState(page);
  check(label + ' 点「作者工具」后折叠（内容 display:none）并写入 textiledream-author-group=closed',
    a1.expanded === 'false' && a1.bodyDisplay === 'none' && a1.collapsedClass && a1.stored === '"closed"',
    '折叠后状态不对：' + JSON.stringify(a1));
  await shot(page, 'sidebar-author-collapsed-' + label + '.png');

  // ---- 阅读设置：选档位
  const r0 = await readState(page);
  const inInfo = await page.evaluate(() => !!document.querySelector('#info-panel #info-reading'));
  check(label + ' 阅读设置卡片在信息栏里，默认折叠且无偏好', inInfo && r0.stored === null && r0.sizeVar === '' && r0.leadVar === '',
    '阅读卡片应位于 #info-panel 且初始没有偏好：' + JSON.stringify({ inInfo, r0 }));
  await page.click('#info-reading > summary');
  await page.waitForTimeout(200);
  const opened = await page.evaluate(() => document.getElementById('info-reading').open);
  check(label + ' 点「阅读」摘要能展开卡片', opened === true, 'open=' + opened);
  await page.click('#info-reading .read-group[data-read="size"] button[data-value="15"]');
  const r15 = await readState(page);
  check(label + ' 字号选「小(15)」：--read-size=15px，正文实际字号 15px',
    r15.sizeVar === '15px' && r15.fontSize === '15px' && r15.pressedSize === '15',
    '字号 15 未生效：' + JSON.stringify(r15));
  await page.click('#info-reading .read-group[data-read="size"] button[data-value="19"]');
  await page.click('#info-reading .read-group[data-read="leading"] button[data-value="2.2"]');
  await page.waitForTimeout(150);
  const r19 = await readState(page);
  const lh = parseFloat(r19.lineHeight);
  check(label + ' 字号选「大(19)」+ 行距选「宽松(2.2)」：变量、实际字号、实际行高(≈41.8px)都生效',
    r19.sizeVar === '19px' && r19.leadVar === '2.2' && r19.fontSize === '19px' &&
    Math.abs(lh - 19 * 2.2) < 0.6 && r19.pressedSize === '19' && r19.pressedLead === '2.2',
    '阅读设置未作用到 #story-text：' + JSON.stringify(r19));
  let storedObj = null;
  try { storedObj = JSON.parse(r19.stored); } catch (e) { /* 留空 */ }
  check(label + ' 偏好存进 localStorage textiledream-reading',
    !!storedObj && storedObj.size === '19' && storedObj.leading === '2.2', 'stored=' + r19.stored);
  await shot(page, 'reading-big-' + label + '.png');

  // ---- 刷新保持（阅读 + 作者组折叠一并验）
  await page.reload({ waitUntil: 'domcontentloaded' });
  await waitApp(page);
  const r1 = await readState(page);
  const a2 = await authorState(page);
  check(label + ' 刷新后阅读设置保持（19px / 2.2，按钮选中态恢复）',
    r1.sizeVar === '19px' && r1.leadVar === '2.2' && r1.fontSize === '19px' && r1.pressedSize === '19' && r1.pressedLead === '2.2',
    '刷新后阅读偏好丢失：' + JSON.stringify(r1));
  check(label + ' 刷新后作者工具组仍折叠', a2.expanded === 'false' && a2.bodyDisplay === 'none',
    '刷新后作者组状态不对：' + JSON.stringify(a2));

  // ---- 再展开 + 存偏好；恢复默认
  await page.click('#workspace-author-toggle');
  await page.waitForTimeout(250);
  const a3 = await authorState(page);
  check(label + ' 再点一次展开，并写入 textiledream-author-group=open',
    a3.expanded === 'true' && a3.bodyVisible && a3.stored === '"open"', '展开后状态不对：' + JSON.stringify(a3));
  // 刷新后没有打开的旅程，信息栏卡片（除缩略图外）按 CSS 隐藏；先打开旅程再点「恢复默认」。
  await page.evaluate((id) => loadSession(id), fixture.linked);
  await waitFor(page, () => !!current && document.getElementById('read-reset').getBoundingClientRect().width > 0, 15000);
  await openDrawer(page);
  await page.evaluate(() => { document.getElementById('info-reading').open = true; });
  await page.click('#read-reset');
  await page.waitForTimeout(150);
  const r2 = await readState(page);
  check(label + ' 「恢复默认」清掉变量、选中态与 localStorage',
    r2.sizeVar === '' && r2.leadVar === '' && r2.pressedSize === null && r2.pressedLead === null && r2.stored === null,
    '恢复默认后仍有残留：' + JSON.stringify(r2));

  // ---- 非法存储值不能被当成样式
  await page.evaluate(() => localStorage.setItem('textiledream-reading', JSON.stringify({ size: '99', leading: 'abc' })));
  await page.reload({ waitUntil: 'domcontentloaded' });
  await waitApp(page);
  const r3 = await readState(page);
  check(label + ' localStorage 里的非法档位（99 / abc）被忽略，不写进样式',
    r3.sizeVar === '' && r3.leadVar === '' && r3.pressedSize === null,
    '非法偏好不应生效：' + JSON.stringify(r3));
  await page.evaluate(() => { localStorage.removeItem('textiledream-reading'); localStorage.removeItem('textiledream-author-group'); });
}

/* ------------------------------------------------------------------ 无地图引导 + chat-polish.css */
async function mapNoteAndCss(c) {
  const { page, label, check, shot, waitFor, waitApp, fixture } = c;
  await page.evaluate((id) => loadSession(id), fixture.plain);
  const shown = await waitFor(page, () => {
    const n = document.getElementById('mini-map-note');
    return !!n && !n.hidden;
  }, 12000);
  await openDrawer(page);
  const n1 = await page.evaluate(() => {
    const n = document.getElementById('mini-map-note');
    const mm = document.getElementById('mini-map');
    const r = n.getBoundingClientRect();
    const b = document.getElementById('mini-map-link');
    return {
      hidden: n.hidden, text: n.textContent.replace(/\s+/g, ' ').trim(),
      afterMiniMap: mm.nextElementSibling === n, visibleBox: r.width > 80 && r.height > 14,
      btn: b ? b.textContent.trim() : null, btnInNote: !!b && n.contains(b), btnIsMiniMapChild: !!b && mm.contains(b),
    };
  });
  check(label + ' 未关联地图的旅程：缩略图后出现引导条，含「还没有关联地图」与「关联地图」按钮',
    shown && !n1.hidden && n1.afterMiniMap && n1.visibleBox && n1.text.includes('还没有关联地图') &&
    n1.btn === '关联地图' && n1.btnInNote && !n1.btnIsMiniMapChild,
    '无地图引导条不对：' + JSON.stringify({ shown, n1 }));
  await shot(page, 'mini-map-note-' + label + '.png');

  // chat-polish.css：样式表已加载 + 两处关键伪元素文案（不做像素比对）
  const css = await page.evaluate(() => {
    const sheet = [...document.styleSheets].find((s) => (s.href || '').includes('chat-polish.css'));
    let rules = -1;
    try { rules = sheet ? sheet.cssRules.length : -1; } catch (e) { rules = -2; }
    const head = document.querySelector('#play-left .scene-head');
    const story = document.getElementById('story-text');
    return {
      linkTag: !!document.querySelector('link[rel="stylesheet"][href*="chat-polish.css"]'),
      found: !!sheet, rules,
      eyebrow: head ? getComputedStyle(head, '::before').content : null,
      storyEmpty: !!story && story.children.length === 0 && story.textContent.trim() === '',
      emptyHint: story ? getComputedStyle(story, '::before').content : null,
    };
  });
  check(label + ' chat-polish.css 已加载（link 存在、样式表有规则）',
    css.linkTag && css.found && css.rules > 20, 'chat-polish.css 未正常加载：' + JSON.stringify(css));
  check(label + ' 场景标题有「当前场景」眉标（chat-polish.css 生效）',
    String(css.eyebrow).includes('当前场景'), '眉标伪元素 content=' + css.eyebrow);
  check(label + ' 空正文显示提示卡「故事还没有开始」（新旅程无回合时）',
    css.storyEmpty && String(css.emptyHint).includes('故事还没有开始'),
    '空正文提示不对：storyEmpty=' + css.storyEmpty + ' content=' + css.emptyHint);

  // 已关联的旅程不显示引导条
  await page.evaluate((id) => loadSession(id), fixture.linked);
  const linkedOk = await waitFor(page, () => {
    const img = document.getElementById('mini-map-img');
    return !!img && !img.hidden && img.naturalWidth > 0;
  }, 20000);
  const n2 = await page.evaluate(() => document.getElementById('mini-map-note').hidden);
  check(label + ' 已关联地图的旅程不显示引导条', linkedOk && n2 === true, 'thumbLoaded=' + linkedOk + ' noteHidden=' + n2);

  // 点「关联地图」→ 收起抽屉并进入 map-tools 页
  await page.evaluate((id) => loadSession(id), fixture.plain);
  await waitFor(page, () => !document.getElementById('mini-map-note').hidden, 12000);
  await openDrawer(page);
  const before = await drawerExpanded(page);
  await page.click('#mini-map-link');
  await page.waitForTimeout(900);
  const nav = await page.evaluate(() => ({
    expanded: document.getElementById('play-left').classList.contains('is-expanded'),
    legacyHidden: document.getElementById('legacy').hidden,
    playHidden: document.getElementById('play').hidden,
    title: document.getElementById('page-title').textContent.trim(),
  }));
  check(label + ' 点「关联地图」：收起对话抽屉并进入「世界地图工具」页',
    before === true && nav.expanded === false && nav.legacyHidden === false && nav.title === '世界地图工具',
    '关联地图跳转不对：before=' + before + ' ' + JSON.stringify(nav));
  await shot(page, 'mini-map-link-target-' + label + '.png');
  await page.click('#back-to-play');
  await page.waitForTimeout(500);
  await page.evaluate((id) => loadSession(id), fixture.linked);
  await waitFor(page, () => {
    const img = document.getElementById('play-map-img');
    return !!img && !img.hidden && img.naturalWidth > 0;
  }, 20000);
}

/* ------------------------------------------------------------------ 存档管理（会改数据） */
async function journeyManagement(c) {
  const { page, label, check, shot, waitFor, fixture, requests, viewport } = c;
  const T_RENAME = TEST_PREFIX + '·改名用', T_DELETE = TEST_PREFIX + '·删除用', T_CURRENT = TEST_PREFIX + '·删当前';
  const NEWNAME = TEST_PREFIX + ' <i>改名</i> & "引号"';
  const created = [];
  const mk = async (title) => {
    const id = await page.evaluate(async (t) => (await api('/sessions', 'POST', { title: t, mode: 'protagonist' })).id, title);
    created.push(id);
    return id;
  };
  const moreSel = (id) => '#journey-list .journey-row:has(> button[data-session-id="' + id + '"]) > button.journey-more';
  const moreInfo = (id) => page.evaluate((i) => {
    const it = document.querySelector('#journey-list button.journey-item[data-session-id="' + i + '"]');
    const row = it && it.parentElement;
    const m = row && row.querySelector(':scope > button.journey-more');
    const t = it && it.querySelector('.journey-title');
    return {
      opacity: m ? getComputedStyle(m).opacity : null, label: m ? m.getAttribute('aria-label') : null,
      haspopup: m ? m.getAttribute('aria-haspopup') : null, expanded: m ? m.getAttribute('aria-expanded') : null,
      focused: !!m && document.activeElement === m, title: t ? t.textContent : null, titleChildren: t ? t.children.length : null,
    };
  }, id);
  const menuState = () => page.evaluate(() => {
    const m = document.querySelector('.journey-menu');
    if (!m) return null;
    const r = m.getBoundingClientRect();
    const items = [...m.querySelectorAll('button')];
    return {
      count: document.querySelectorAll('.journey-menu').length, parent: m.parentElement.id,
      items: items.map((b) => b.textContent), roles: items.map((b) => b.getAttribute('role')),
      danger: !!items[1] && items[1].classList.contains('danger'),
      inView: r.top >= 0 && r.left >= 0 && r.bottom <= innerHeight + 1 && r.right <= innerWidth + 1,
      focus: document.activeElement ? document.activeElement.textContent : null,
    };
  });
  const itemExists = (id) => page.evaluate((i) => !!document.querySelector('#journey-list button.journey-item[data-session-id="' + i + '"]'), id);
  const serverStatus = (id) => page.evaluate(async (i) => (await fetch('/api/sessions/' + i, { headers: { 'X-TextileDream-Token': token } })).status, id);
  const methodCount = (method) => requests.filter((r) => r.method === method && /^\/api\/sessions\/[^/]+$/.test(r.path)).length;
  const openMenuFor = async (id) => { await page.click(moreSel(id)); await page.waitForTimeout(200); };

  try {
    const idRename = await mk(T_RENAME);
    const idDelete = await mk(T_DELETE);
    const idCurrent = await mk(T_CURRENT);
    await page.evaluate(() => bootstrap());
    await page.waitForTimeout(500);
    await openDrawer(page);

    // ---- 结构
    const server = await bootstrapSessions(page);
    const st = await page.evaluate(() => {
      const kids = [...document.getElementById('journey-list').children];
      const rows = kids.filter((k) => k.classList.contains('journey-row'));
      return {
        kids: kids.length, rows: rows.length, bare: kids.filter((k) => k.tagName === 'BUTTON').length,
        ok: rows.filter((r) => r.querySelector(':scope > button.journey-item[data-session-id]') &&
                               r.querySelector(':scope > button.journey-more')).length,
      };
    });
    check(label + ' 每条存档都被包进 .journey-row，右侧有「⋯」按钮，且没有裸的存档按钮',
      st.rows === server.length && st.ok === st.rows && st.bare === 0,
      '存档行结构不对：dom=' + js(st) + ' 服务端存档数=' + server.length);
    const mi = await moreInfo(idRename);
    check(label + ' 「⋯」按钮有 aria-haspopup=menu、收起态 aria-expanded=false、aria-label 带存档名',
      mi.haspopup === 'menu' && mi.expanded === 'false' && String(mi.label).includes(T_RENAME), js(mi));

    // ---- 悬停才显示
    await page.evaluate(() => document.activeElement && document.activeElement.blur());
    await page.mouse.move(Math.round(viewport.w / 2), 4);
    await page.waitForTimeout(350);
    const op0 = (await moreInfo(idRename)).opacity;
    await page.hover('#journey-list button.journey-item[data-session-id="' + idRename + '"]');
    await page.waitForTimeout(350);
    const op1 = (await moreInfo(idRename)).opacity;
    check(label + ' 「⋯」平时隐藏、鼠标悬停该行时显示', op0 === '0' && op1 === '1', 'opacity 平时=' + op0 + ' 悬停=' + op1);

    // ---- 菜单
    const curBefore = await page.evaluate(() => current && current.id);
    await openMenuFor(idRename);
    const m1 = await menuState();
    const curAfter = await page.evaluate(() => current && current.id);
    const mi2 = await moreInfo(idRename);
    check(label + ' 点「⋯」弹出菜单：只有「重命名」「删除」，删除为危险样式，在屏内，焦点落在第一项，并且不会切换会话',
      !!m1 && m1.count === 1 && m1.items.join('|') === '重命名|删除' && m1.roles.join('|') === 'menuitem|menuitem' &&
      m1.danger && m1.inView && m1.focus === '重命名' && mi2.expanded === 'true' && curBefore === curAfter,
      '存档菜单不对：' + js({ m1, expanded: mi2.expanded, curBefore, curAfter }));
    await shot(page, 'journey-menu-' + label + '.png');
    await page.keyboard.press('ArrowDown');
    const m2 = await menuState();
    check(label + ' 菜单里按 ↓ 焦点移到「删除」', !!m2 && m2.focus === '删除', 'focus=' + (m2 && m2.focus));

    // ---- Esc 只关菜单，不收起抽屉
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    const afterEsc = { menu: await menuState(), drawer: await drawerExpanded(page), more: await moreInfo(idRename) };
    check(label + ' 菜单开着时按 Esc：只关菜单，对话抽屉仍展开，焦点回到「⋯」，aria-expanded 复位',
      afterEsc.menu === null && afterEsc.drawer === true && afterEsc.more.focused && afterEsc.more.expanded === 'false',
      'Esc 行为不对：' + js(afterEsc));
    // 对照：没有菜单时同一个 Esc 应当收起抽屉（证明上一条不是因为 Esc 根本无效）
    await page.keyboard.press('Escape');
    await page.waitForTimeout(400);
    const ctrl = await drawerExpanded(page);
    check(label + ' 对照：没有菜单/弹窗时按 Esc 会收起抽屉', ctrl === false, 'drawer 仍展开=' + ctrl);
    await openDrawer(page);

    // ---- 点外部关闭
    await openMenuFor(idRename);
    const sBox = await page.evaluate(() => { const r = document.getElementById('surface').getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + 40 }; });
    await page.mouse.click(sBox.x, sBox.y);
    await page.waitForTimeout(250);
    const outClose = { menu: await menuState(), drawer: await drawerExpanded(page) };
    check(label + ' 点菜单外部关闭菜单（抽屉不受影响）', outClose.menu === null && outClose.drawer === true, js(outClose));

    // ---- 重命名对话框
    const titlesBefore = await bootstrapSessions(page);
    await openMenuFor(idRename);
    await page.click('.journey-menu button:has-text("重命名")');
    await page.waitForTimeout(300);
    const d1 = await page.evaluate(() => {
      const d = document.getElementById('rename-dialog');
      const i = d && d.querySelector('input');
      return {
        exists: !!d, open: !!d && d.open, h2: d ? d.querySelector('h2').textContent : null,
        value: i ? i.value : null, focused: !!i && document.activeElement === i,
        buttons: d ? [...d.querySelectorAll('button')].map((b) => b.textContent) : [], menuGone: !document.querySelector('.journey-menu'),
      };
    });
    check(label + ' 点「重命名」：弹出 #rename-dialog（模态），预填原名并聚焦输入框，菜单已收起',
      d1.exists && d1.open && d1.h2 === '重命名存档' && d1.value === T_RENAME && d1.focused &&
      d1.buttons.join('|') === '取消|保存' && d1.menuGone, '重命名对话框不对：' + js(d1));
    await shot(page, 'rename-dialog-' + label + '.png');

    const patchBefore = methodCount('PATCH');
    await page.fill('#rename-dialog input', '');
    await page.click('#rename-dialog button[type="submit"]');
    await page.waitForTimeout(300);
    const dEmpty = await page.evaluate(() => document.getElementById('rename-dialog').open);
    check(label + ' 名称留空点保存：被拦下（对话框仍开，没有发出 PATCH）',
      dEmpty === true && methodCount('PATCH') === patchBefore, 'open=' + dEmpty + ' PATCH 增量=' + (methodCount('PATCH') - patchBefore));
    await page.fill('#rename-dialog input', '    ');
    await page.click('#rename-dialog button[type="submit"]');
    await page.waitForTimeout(300);
    const dBlank = await page.evaluate(() => ({
      open: document.getElementById('rename-dialog').open,
      err: (document.querySelector('#rename-dialog [role="alert"]') || {}).textContent || '',
    }));
    check(label + ' 名称只有空格点保存：对话框内提示「名称需要 1 到 80 个字」且不发 PATCH',
      dBlank.open && dBlank.err.includes('1 到 80') && methodCount('PATCH') === patchBefore, js(dBlank));
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    const dEsc = { open: await page.evaluate(() => document.getElementById('rename-dialog').open), drawer: await drawerExpanded(page) };
    const unchanged = await moreInfo(idRename);
    check(label + ' 对话框里按 Esc：只关对话框（抽屉仍展开），存档名不变',
      dEsc.open === false && dEsc.drawer === true && unchanged.title === T_RENAME, js({ dEsc, title: unchanged.title }));

    await openMenuFor(idRename);
    await page.click('.journey-menu button:has-text("重命名")');
    await page.waitForTimeout(250);
    await page.fill('#rename-dialog input', NEWNAME);
    await page.click('#rename-dialog button[type="submit"]');
    const closed = await waitArg(page, () => !document.getElementById('rename-dialog').open, null, 8000);
    await page.waitForTimeout(500);
    const ren = await moreInfo(idRename);
    const titlesAfter = await bootstrapSessions(page);
    const mapOf = (arr) => Object.fromEntries(arr.map((s) => [s.id, s.title]));
    const tb = mapOf(titlesBefore), ta = mapOf(titlesAfter);
    const diff = Object.keys({ ...tb, ...ta }).filter((k) => tb[k] !== ta[k]);
    const noticeText = await page.evaluate(() => document.getElementById('notice').textContent);
    check(label + ' 重命名成功：对话框关闭，列表和服务端都是新名，标题按纯文本显示（不解析 HTML）',
      closed && ren.title === NEWNAME && ren.titleChildren === 0 && ta[idRename] === NEWNAME,
      '重命名结果不对：' + js({ closed, ren, server: ta[idRename] }));
    check(label + ' 重命名只改了目标存档，其它存档名不变，并提示「已重命名」',
      diff.length === 1 && diff[0] === idRename && String(noticeText).includes('已重命名'),
      '被改动的存档=' + js(diff) + ' notice=' + noticeText);
    check(label + ' 重命名后「⋯」的 aria-label 同步为新名', String(ren.label).includes(NEWNAME), 'aria-label=' + ren.label);

    // ---- 删除：取消 → 确认
    let msg = null;
    c.page.once('dialog', (d) => { msg = d.message(); d.dismiss(); });
    const delBefore = methodCount('DELETE');
    await openMenuFor(idDelete);
    await page.click('.journey-menu button:has-text("删除")');
    await page.waitForTimeout(500);
    check(label + ' 点「删除」弹确认框（带存档名、说明永久删除）；取消后存档仍在、未发出 DELETE',
      !!msg && msg.includes(T_DELETE) && msg.includes('永久删除') && (await itemExists(idDelete)) &&
      methodCount('DELETE') === delBefore && (await serverStatus(idDelete)) === 200,
      '删除确认/取消行为不对：msg=' + msg);
    c.page.once('dialog', (d) => d.accept());
    await openMenuFor(idDelete);
    await page.click('.journey-menu button:has-text("删除")');
    const gone = await waitArg(page, (i) => !document.querySelector('#journey-list button.journey-item[data-session-id="' + i + '"]'), idDelete, 8000);
    const st404 = await serverStatus(idDelete);
    const stillCur = await page.evaluate(() => current && current.id);
    const after = await bootstrapSessions(page);
    check(label + ' 确认删除：存档从列表和服务端消失，其它存档与当前会话不受影响',
      gone && st404 !== 200 && !after.some((s) => s.id === idDelete) && after.some((s) => s.id === fixture.linked) &&
      after.some((s) => s.id === fixture.plain) && stillCur === fixture.linked,
      '删除结果不对：' + js({ gone, st404, stillCur }));

    // ---- 删除「当前」存档：回到作者模式、清掉记住的会话
    await page.evaluate((i) => loadSession(i), idCurrent);
    await page.waitForTimeout(800);
    await openDrawer(page);
    const memo = await page.evaluate(() => localStorage.getItem('textiledream-session'));
    c.page.once('dialog', (d) => d.accept());
    await openMenuFor(idCurrent);
    await page.click('.journey-menu button:has-text("删除")');
    // 模式先切到 author，列表随后由 bootstrap() 重绘；两个条件都满足才算完成。
    const authorMode = await waitArg(page, (i) => window.__tdNativeMode === 'author' &&
      !document.querySelector('#journey-list button[data-session-id="' + i + '"]'), idCurrent, 10000);
    await page.waitForTimeout(300);
    const fin = await page.evaluate((i) => ({
      mode: window.__tdNativeMode, listed: !!document.querySelector('#journey-list button[data-session-id="' + i + '"]'),
      remembered: localStorage.getItem('textiledream-session'),
    }), idCurrent);
    check(label + ' 删除当前打开的存档：回到作者模式、列表不再有它、不再记住该会话',
      authorMode && fin.mode === 'author' && !fin.listed && fin.remembered !== idCurrent && memo === idCurrent,
      '删除当前存档后状态不对：' + js({ memo, fin }));
  } finally {
    // 清理本段创建的临时存档（只删 created 里的 id，且这些都是探针自己新建的）
    for (const id of created) {
      try { await page.evaluate((i) => api('/sessions/' + i, 'DELETE'), id); } catch (e) { /* 已删 */ }
    }
    try { await page.evaluate(() => bootstrap()); } catch (e) { /* ignore */ }
  }
}

/* ------------------------------------------------------------------ 世界设定卡片 */
async function worldSetting(c) {
  const { page, label, check, shot, waitFor, requests } = c;
  const reqStart = requests.length;
  await page.evaluate(() => showPage('elements'));
  const ready = await waitFor(page, () => {
    const cats = document.getElementById('ws-cats');
    return !!cats && cats.querySelectorAll('button').length > 0 &&
      document.querySelectorAll('#ws-tech button').length > 1;
  }, 20000);
  const card = await page.evaluate(() => {
    const el = document.getElementById('world-setting');
    const r = el ? el.getBoundingClientRect() : null;
    const hero = document.querySelector('#elements .ea-hero');
    const vis = (id) => { const b = document.getElementById(id); return !!b && b.getBoundingClientRect().width > 20; };
    return {
      exists: !!el, tag: el ? el.tagName : null, open: el ? el.open : null,
      inElements: !!el && !!document.getElementById('elements').contains(el),
      afterHero: !!el && !!hero && hero.nextElementSibling === el,
      visible: !!r && r.width > 200 && r.height > 100,
      btns: ['ws-cat-preview', 'ws-recommend', 'ws-generate', 'ws-save'].map((id) => id + ':' + vis(id)),
      cats: document.querySelectorAll('#ws-cats button').length,
      tech: document.querySelectorAll('#ws-tech button').length,
      magic: document.querySelectorAll('#ws-magic button').length,
      saveDisabled: (document.getElementById('ws-save') || {}).disabled,
      status: (document.getElementById('ws-status') || {}).textContent || '',
    };
  });
  check(label + ' 元素数据库页顶部有「世界设定」卡片（details，默认展开，紧跟页头，可见）',
    ready && card.exists && card.tag === 'DETAILS' && card.open === true && card.inElements && card.afterHero && card.visible,
    '世界设定卡片不对：' + js(card));
  check(label + ' 卡片里渲染了大类、科技档位、魔法档位和四个按钮',
    card.cats >= 2 && card.tech >= 3 && card.magic >= 3 && card.btns.every((b) => b.endsWith(':true')),
    '大类/档位/按钮渲染不完整：' + js({ cats: card.cats, tech: card.tech, magic: card.magic, btns: card.btns }));
  await shot(page, 'world-setting-' + label + '.png');

  const pressed = (id) => page.evaluate((i) => [...document.querySelectorAll('#' + i + ' button')]
    .map((b) => ({ on: b.classList.contains('on'), p: b.getAttribute('aria-pressed') })), id);
  const catsBefore = await pressed('ws-cats');
  await page.click('#ws-cats button >> nth=0');
  await page.waitForTimeout(150);
  const catsAfter = await pressed('ws-cats');
  check(label + ' 点第一个大类：它变为选中（aria-pressed=true，高亮）',
    catsBefore[0].p === 'false' && catsAfter[0].p === 'true' && catsAfter[0].on === true,
    '大类选中态不对：' + js({ before: catsBefore[0], after: catsAfter[0] }));
  const techBefore = await pressed('ws-tech');
  await page.click('#ws-tech button >> nth=1');
  await page.waitForTimeout(150);
  const techAfter = await pressed('ws-tech');
  check(label + ' 科技档位：默认「不限」高亮；点第一档后该档选中、「不限」取消',
    techBefore[0].on === true && techAfter[1].on === true && techAfter[1].p === 'true' && techAfter[0].on === false,
    '科技档位选中态不对：' + js({ before: techBefore.slice(0, 2), after: techAfter.slice(0, 2) }));
  await page.click('#ws-magic button >> nth=1');
  await page.waitForTimeout(150);
  const magicAfter = await pressed('ws-magic');
  check(label + ' 魔法档位：点第一档后该档选中、「不限」取消',
    magicAfter[1].on === true && magicAfter[1].p === 'true' && magicAfter[0].on === false, js(magicAfter.slice(0, 2)));

  await page.click('#ws-cat-preview');
  const reco = await waitFor(page, () => {
    const box = document.getElementById('ws-reco');
    return !!box && !box.hidden && box.querySelectorAll('.ws-group').length > 0;
  }, 20000);
  const recoInfo = await page.evaluate(() => {
    const box = document.getElementById('ws-reco');
    return {
      hidden: box.hidden, groups: box.querySelectorAll('.ws-group').length,
      head: box.textContent.slice(0, 80), titles: [...box.querySelectorAll('.ws-group h4')].map((h) => h.textContent.slice(0, 20)).slice(0, 6),
    };
  });
  check(label + ' 点「查看大类元素」：#ws-reco 出现分组，并有「共纳入 N 条元素」说明',
    reco && !recoInfo.hidden && recoInfo.groups >= 1 && recoInfo.head.includes('共纳入'),
    '大类元素预览不对：' + js(recoInfo));
  await shot(page, 'world-setting-reco-' + label + '.png');

  const made = requests.slice(reqStart);
  const risky = made.filter((r) => (r.method === 'PUT' && r.path.includes('/inner/world-setting')) ||
    r.path.includes('/worldview/generate') || r.path.includes('/worldview/drafts'));
  check(label + ' 探针没有触发世界设定保存或世界观生成（无 PUT /inner/world-setting、无 generate 请求）',
    risky.length === 0, '不该发出的请求：' + js(risky));
  await page.click('#back-to-play');
  await page.waitForTimeout(500);
}

async function runNewFeatureChecks(ctx) {
  const { page, label, guard, fixture, waitFor } = ctx;
  await guard(page, label, '阅读设置与侧栏分组', () => readingAndSidebar(ctx));
  await guard(page, label, '无地图引导与 chat-polish.css', () => mapNoteAndCss(ctx));
  if (ctx.allowMutate) {
    await guard(page, label, '存档管理', () => journeyManagement(ctx));
  } else {
    console.log('SKIP  ' + label + ' 存档管理（重命名/删除）：未设 TD_ALLOW_MUTATE=1，不在当前服务上改数据');
    ctx.skipped.push(label + ' 存档管理');
  }
  await guard(page, label, '世界设定卡片', () => worldSetting(ctx));
  // 收尾：回到已关联旅程 + 展开抽屉，让后面的检查看到和以前一样的状态
  await guard(page, label, '新功能检查收尾', async () => {
    await page.evaluate((id) => loadSession(id), fixture.linked);
    await waitFor(page, () => {
      const img = document.getElementById('play-map-img');
      return !!img && !img.hidden && img.naturalWidth > 0;
    }, 20000);
  });
}

module.exports = { runNewFeatureChecks };
