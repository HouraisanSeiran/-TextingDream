/* 可试玩 Demo 的表层适配层。
 *
 * 它不重写引擎，只做三件事：
 *   1. 新建旅程时让玩家选起点（/api/start-profiles）；没有起点配置时整段隐藏。
 *   2. 把「候选行动 → 看成本 → 确认」这条链子接到已有 /chat 上（confirm 凭据）。
 *   3. 展示起点回执、玩家已知的预警与已记录结局。
 *
 * app.js 用的是脚本级 const/let（api / current / token 等不在 window 上），
 * 所以这里直接引用那些全局词法绑定，而不是 window.xxx。
 * 旧界面不存在时全部静默跳过，行为不变。
 */
(function () {
  'use strict';
  const byId = (id) => document.getElementById(id);
  let startConfig = { configured: false, profiles: [] };
  let pendingIntent = '';
  let pending = null;
  let confirmRequest = 0;
  let lastCheck = null;
  let lastCheckSession = null;
  // 「会话 id:check_seq」。服务端给每条新检定一个单调递增序号，有序号时只看它。
  let lastCheckSeq = null;
  // Set only while a confirmed action that carries a v2 check is in flight, so a
  // new roll that happens to equal the previous one still animates once.
  let expectCheck = false;
  let actionBusy = false;
  let sessionEpoch = 0;
  let checkOverlay = null;
  let overlayFocus = null;
  let overlayResize = null;

  function positionCheckOverlay() {
    if (!checkOverlay || !checkOverlay.open) return;
    const anchor = byId('play-left-head');
    const drawer = byId('play-left');
    if (!anchor || !drawer || drawer.classList.contains('is-collapsed') || !current) {
      closeCheckOverlay();
      return;
    }
    const rect = anchor.getBoundingClientRect();
    const width = Math.min(380, Math.max(240, rect.width - 24), innerWidth - 24);
    const left = Math.max(12, Math.min(rect.left + 12, innerWidth - width - 12));
    const composer = byId('chat-form');
    const inputTop = composer && !composer.hidden ? composer.getBoundingClientRect().top : innerHeight;
    const desiredTop = Math.max(12, rect.bottom + 8);
    const top = Math.min(desiredTop, Math.max(12, innerHeight - 220));
    checkOverlay.style.width = width + 'px';
    checkOverlay.style.left = left + 'px';
    checkOverlay.style.top = top + 'px';
    checkOverlay.style.maxHeight = Math.max(160, Math.min(innerHeight - top - 12,
      inputTop > top + 160 ? inputTop - top - 8 : innerHeight - top - 100)) + 'px';
    checkOverlay.dataset.anchor = 'play-left-head';
  }

  function closeCheckOverlay() {
    byId('dice-toggle')?.setAttribute('aria-expanded', 'false');
    if (!checkOverlay) return;
    const host = checkOverlay.querySelector('.dice-overlay-result');
    if (host && window.TDDice) window.TDDice.stop(host);
    if (checkOverlay.open) checkOverlay.close();
  }

  function currentCheck() {
    return current && (current.last_check || current.check_public
      || (current.result && (current.result.last_check || current.result.check_public)));
  }

  function syncDiceButton() {
    const button = byId('dice-toggle');
    if (!button) return;
    button.disabled = !current;
    button.setAttribute('aria-expanded', String(Boolean(checkOverlay && checkOverlay.open)));
    if (!current) closeCheckOverlay();
  }

  function showCheckOverlay(check, animate = false) {
    if (!current || byId('play-left')?.classList.contains('is-collapsed')) return;
    // Never cover an unsubmitted author/player confirmation dialog.
    if (document.querySelector('dialog[open]:not(#demo-dice-overlay)')) return;
    closeFoldPanel();
    if (!checkOverlay) {
      checkOverlay = el('dialog', undefined, 'dice-overlay');
      checkOverlay.id = 'demo-dice-overlay';
      checkOverlay.setAttribute('aria-labelledby', 'demo-dice-overlay-title');
      const head = el('div', undefined, 'dice-overlay-head');
      const title = el('strong', '骰子');
      title.id = 'demo-dice-overlay-title';
      const close = el('button', '×', 'dice-overlay-close');
      close.type = 'button'; close.title = '关闭判定结果';
      close.setAttribute('aria-label', '关闭判定结果');
      close.addEventListener('click', closeCheckOverlay);
      head.append(title, close);
      const footer = el('div', undefined, 'dice-panel-tools');
      const replay = el('button', '重放动画');
      replay.id = 'dice-replay'; replay.type = 'button';
      replay.addEventListener('click', () => {
        const latest = currentCheck();
        if (latest) showCheckOverlay(latest, true);
      });
      const sandbox = el('a', '自由沙盘（试投不影响剧情）');
      sandbox.href = '/static/dice-physics-demo.html';
      sandbox.target = '_blank'; sandbox.rel = 'noopener';
      // Material: browser-local view preference, never sent to the server.
      const matLabel = el('label', undefined, 'dice-material');
      const matSelect = el('select');
      matSelect.id = 'dice-material';
      matSelect.setAttribute('aria-label', '骰子材质');
      const core = window.TDDiceCore;
      Object.entries((core && core.MATERIALS) || {}).forEach(([id, row]) => {
        const option = el('option', row.label);
        option.value = id;
        matSelect.append(option);
      });
      if (core) matSelect.value = core.material();
      matSelect.addEventListener('change', () => {
        if (core) core.setMaterial(matSelect.value);
        const latest = currentCheck();
        if (latest) showCheckOverlay(latest, false);
      });
      matLabel.append(document.createTextNode('材质 '), matSelect);
      footer.append(replay, matLabel, sandbox);
      checkOverlay.append(head, el('div', undefined, 'dice-overlay-result'), footer);
      checkOverlay.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') { event.preventDefault(); closeCheckOverlay(); }
      });
      checkOverlay.addEventListener('close', () => {
        if (checkOverlay.open) return;
        byId('dice-toggle')?.setAttribute('aria-expanded', 'false');
        window.TDDice.stop(checkOverlay.querySelector('.dice-overlay-result'));
        if (overlayFocus && overlayFocus.isConnected) overlayFocus.focus({ preventScroll: true });
      });
      document.body.append(checkOverlay);
      const anchor = byId('play-left-head');
      if (anchor && window.ResizeObserver) {
        overlayResize = new ResizeObserver(positionCheckOverlay);
        overlayResize.observe(anchor);
      }
      document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && checkOverlay.open && !document.querySelector('dialog:modal')) {
          event.preventDefault(); closeCheckOverlay();
        }
      });
      window.addEventListener('resize', positionCheckOverlay);
      window.addEventListener('scroll', positionCheckOverlay, true);
    }
    if (!checkOverlay.open) {
      overlayFocus = document.activeElement;
      checkOverlay.show();
    }
    const host = checkOverlay.querySelector('.dice-overlay-result');
    window.TDDice.stop(host);
    if (check) window.TDDice.roll(host, check, { mode: 'spin', animate });
    else {
      host.className = 'dice-overlay-result';
      host.replaceChildren(el('p', '尚无检定。完成一次检定后，可在这里查看结果。', 'muted'));
    }
    byId('dice-replay').disabled = !check || check.rolled !== true;
    syncDiceButton();
    positionCheckOverlay();
    checkOverlay.querySelector('button').focus({ preventScroll: true });
  }

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
    say.timer = setTimeout(() => { box.hidden = true; }, 8000);
  }

  // ------------------------------------------------------------------ 起点选择
  function profileSection() {
    let box = byId('start-profile-box');
    if (box) return box;
    const form = byId('new-form');
    if (!form) return null;
    box = el('div', undefined, 'start-profiles');
    box.id = 'start-profile-box';
    form.insertBefore(box, form.querySelector('.toolbar'));
    return box;
  }

  function drawProfiles() {
    const box = profileSection();
    if (!box) return;
    box.replaceChildren();
    if (!startConfig.configured || !startConfig.profiles.length) {
      box.hidden = true;
      return;
    }
    box.hidden = false;
    box.append(el('p', '选一个起点。身份、落脚处、随身东西、认识的人与开局已知的信息不同，入口事件也不同。', 'muted'));
    startConfig.profiles.forEach((profile, index) => {
      const label = el('label', undefined, 'start-profile');
      const radio = el('input');
      radio.type = 'radio';
      radio.name = 'start-profile';
      radio.value = profile.id;
      radio.checked = index === 0;
      label.append(radio, el('strong', profile.title), el('small', profile.summary || ''));
      const facts = [];
      if (profile.identity) facts.push('身份：' + profile.identity);
      if (profile.goal) facts.push('目标：' + profile.goal);
      if (profile.known && profile.known.length) facts.push('开局已知：' + profile.known.join('；'));
      if (facts.length) label.append(el('span', facts.join(' · '), 'start-facts'));
      box.append(label);
    });
  }

  function chosenProfile() {
    const checked = document.querySelector('input[name="start-profile"]:checked');
    return checked ? checked.value : null;
  }

  // ------------------------------------------------------- 行动候选 + 成本确认
  function ensureConfirmDialog() {
    let dialog = byId('demo-confirm');
    if (dialog) return dialog;
    dialog = el('dialog');
    dialog.id = 'demo-confirm';
    dialog.innerHTML = '<form method="dialog"><h2>确认这一步</h2><div id="demo-confirm-body"></div>' +
      '<div class="toolbar"><button type="button" id="demo-confirm-cancel">再想想</button>' +
      '<button type="button" id="demo-confirm-run" class="primary">确认执行</button></div></form>';
    document.body.append(dialog);
    byId('demo-confirm-cancel').onclick = () => { dialog.close(); pending = null; confirmRequest += 1; };
    dialog.addEventListener('cancel', () => { pending = null; confirmRequest += 1; });
    byId('demo-confirm-run').onclick = () => runPending(dialog);
    return dialog;
  }

  function costText(costs) {
    return (costs || []).map((row) => row.name + ' × ' + row.amount).join('，');
  }

  function detailLines(action) {
    const lines = [];
    if (action.risk_notice) lines.push('可能的后果：' + action.risk_notice);
    lines.push(action.costs && action.costs.length ? '成本：' + costText(action.costs) : '成本：不花资源');
    if (action.duration_hours) lines.push('时长：' + action.duration_hours + ' 小时');
    if (action.check && action.check.attribute && !action.check.v2) {
      lines.push('检定：' + action.check.attribute + ' · 难度 ' + action.check.difficulty);
    }
    if (action.ends_event) lines.push('这一步会结束当前事件');
    return lines;
  }

  function drawConfirm(action) {
    const body = byId('demo-confirm-body');
    body.replaceChildren(el('p', action.label, 'confirm-title'));
    detailLines(action).forEach((line) => body.append(el('p', line, 'confirm-line')));
    const v2 = action.check && action.check.v2;
    byId('demo-confirm').classList.toggle('has-check-v2', Boolean(v2));
    if (v2 && window.TDDice) {
      window.TDDice.preview(body, v2, { push: action.selectedPush, onPush: refreshPush });
    }
    const run = byId('demo-confirm-run');
    if (!action.confirm) {
      body.append(el('p', '没有拿到确认凭据，请重新获取候选（可能状态已经变了）。', 'muted'));
      run.disabled = true;
    } else {
      run.disabled = Boolean(v2 && (v2.refused || v2.blocked));
    }
  }

  function openConfirm(action) {
    const dialog = ensureConfirmDialog();
    confirmRequest += 1;
    pending = action;
    drawConfirm(action);
    if (!dialog.open) dialog.showModal();
  }

  async function refreshPush(push) {
    if (!pending || !current) return;
    const request = ++confirmRequest;
    const sessionId = current.id;
    const action = pending;
    byId('demo-confirm-run').disabled = true;
    const body = byId('demo-confirm-body');
    let status = body.querySelector('.check-refresh-status');
    if (!status) { status = el('p', '', 'check-refresh-status muted'); status.setAttribute('role', 'status'); body.append(status); }
    status.textContent = '正在更新加码与确认凭据…';
    try {
      const next = await api('/sessions/' + encodeURIComponent(sessionId) + '/confirm/'
        + encodeURIComponent(action.action_id || action.id) + (push ? '?push=' + encodeURIComponent(push) : ''));
      if (request !== confirmRequest || pending !== action || !current || current.id !== sessionId) return;
      pending = Object.assign({}, next, { selectedPush: push || null });
      drawConfirm(pending);
    } catch (error) {
      if (request !== confirmRequest || pending !== action) return;
      // The old token cannot be used with the newly selected push.
      status.textContent = '加码确认未更新：' + error.message + '。请重新选择加码或重新打开动作。';
    }
  }

  async function runPending(dialog) {
    if (!pending || typeof current === 'undefined' || !current || actionBusy || byId('demo-confirm-run').disabled) return;
    const v2 = pending.check && pending.check.v2;
    if (v2 && (v2.refused || v2.blocked)) return;
    confirmRequest += 1;
    const action = pending;
    dialog.close();
    if (action.kind === 'move') {
      pendingIntent = '';
      await runMove();
      pending = null;
      return;
    }
    const message = pendingIntent || action.label;
    pending = null;
    pendingIntent = '';
    const sessionId = current.id;
    const epoch = sessionEpoch;
    actionBusy = true;
    try {
      const response = await api('/sessions/' + sessionId + '/chat', 'POST', {
        message,
        action_id: action.action_id,
        channel: 'action',
        confirm: action.confirm || undefined,
        ...(action.check && action.check.v2 ? { push: action.selectedPush || null } : {}),
      });
      if (sessionEpoch !== epoch || !current || current.id !== sessionId) return;
      expectCheck = Boolean(action.check && action.check.v2);
      // 确保这份响应被当作「本页刚提交的结果」（api 包装失败时也成立）。
      freshResponses.add(response);
      current = response;
      const intent = byId('demo-intent-text');
      if (intent) intent.value = '';
      // 无事件时服务端不会产生模型正文。这里只展示**服务端已确认**的结果：
      // 动作公开标签 + 时长/资源前后。没有 local_result 就不造任何话。
      showLocalResult(current && current.local_result);
      render();
    } catch (error) {
      expectCheck = false;
      if (sessionEpoch === epoch) say(error.message);
    } finally {
      if (sessionEpoch === epoch) actionBusy = false;
    }
  }

  function showLocalResult(result) {
    if (!result) return;
    const parts = [result.label || result.action_id];
    if (result.hours) parts.push('用时 ' + result.hours + ' 小时');
    (result.resources || []).forEach((row) => {
      if (row.before === row.after) return;
      parts.push(row.id + ' ' + row.before + ' → ' + row.after);
    });
    say('已执行：' + parts.join('；'));
  }

  // ----------------------------------------- 旅行：既有 POST /move（无新 token）
  // 服务端已经验过路线可见性/条件/同世界/费用；这里只把**同一个**确认框拿来
  // 展示目的地与时长，避免不确认就直接跳走。不传任何客户端计算的时长。
  function openMoveConfirm(row) {
    const dialog = ensureConfirmDialog();
    dialog.classList.remove('has-check-v2');
    const body = byId('demo-confirm-body');
    body.replaceChildren(el('p', '前往 ' + (row.target && row.target.name
      ? row.target.name : row.label), 'confirm-title'));
    body.append(el('p', '时长：' + row.duration_hours + ' 小时（'
      + (row.duration_source === 'route' ? '按已声明路线'
        : row.duration_source === 'local.travel_hours' ? '默认路程时长' : '作者声明')
      + '）', 'confirm-line'));
    const costs = (row.travel && row.travel.costs) || {};
    const names = Object.keys(costs);
    if (names.length) {
      body.append(el('p', '路费：' + names.map((key) => key + ' × ' + costs[key]).join('，')
        + '（不足则整次不动）', 'confirm-line'));
    } else {
      body.append(el('p', '路费：不花资源', 'confirm-line'));
    }
    if (row.travel && row.travel.position_source === 'unrecorded') {
      body.append(el('p', '这个地点没有记录坐标，时长来自声明而不是距离推算。', 'muted'));
    }
    const run = byId('demo-confirm-run');
    run.disabled = false;
    pending = { kind: 'move', destination: row.travel.destination, label: row.label };
    dialog.showModal();
  }

  async function runMove() {
    if (!pending || !pending.destination || !current) return;
    const destination = pending.destination;
    try {
      current = await api('/sessions/' + current.id + '/move', 'POST',
        { location_id: destination });
      const clock = (current.local_state && current.local_state.clock) || {};
      say('已到达 ' + (current.location || destination)
        + (clock.elapsed_hours !== undefined ? '（累计 ' + clock.elapsed_hours + ' 小时）' : ''));
      render();
    } catch (error) {
      say(error.message);
    }
  }

  async function confirmAction(actionId) {
    if (!current) return;
    try {
      openConfirm(await api('/sessions/' + current.id + '/confirm/' + encodeURIComponent(actionId)));
    } catch (error) {
      say(error.message);
    }
  }

  // -------------------------------------------- 运行时动作（surface.adventure）
  // 只读服务端已经算好的 public 摘要：不在这里猜成功/失败、不拼未公开文本。
  // 三条规则：
  //   execution === 'action' 且有 confirm → 按钮 → 既有 POST /chat
  //   execution === 'move'   → 按钮 → 既有 POST /move（先弹同一个确认框）
  //   execution === 'blocked_active_event' / 'unsupported' / 无 confirm → **不渲染**
  function actionMeta(row) {
    const meta = [];
    if (row.costs && row.costs.length) meta.push(costText(row.costs));
    else meta.push('不花资源');
    if (row.duration_hours) meta.push(row.duration_hours + ' 小时');
    if (row.duration_source === 'route') meta.push('按已声明路线');
    if (row.duration_source === 'local.travel_hours') meta.push('默认路程时长');
    if (row.check && row.check.attribute) meta.push('检定 ' + row.check.attribute);
    return meta.join(' · ');
  }

  function adventureRows() {
    const block = current && current.adventure;
    if (!block || !block.plans) return [];
    // 只有服务端真的允许本次执行的两种才会出按钮：
    //   action = 走既有 /chat（已带 confirm）；move = 走既有 /move（仅在无事件时）。
    // blocked_active_event / unsupported 即便 supported=true 也不渲染。
    return block.plans.filter((row) => row.supported
      && (row.execution === 'action' && row.confirm || row.execution === 'move'));
  }

  function drawAdventure(box, known) {
    const rows = adventureRows().filter((row) => !known.has(row.action_id));
    if (!rows.length) return 0;
    box.append(el('p', '就地能做的事', 'actions-label'));
    rows.forEach((row) => {
      const button = el('button');
      button.type = 'button';
      button.dataset.adventureId = row.action_id;
      button.dataset.execution = row.execution;
      const label = row.target && row.target.name
        ? row.label : row.label;
      button.append(el('span', label));
      button.append(el('small', actionMeta(row)));
      button.onclick = () => (row.execution === 'move'
        ? openMoveConfirm(row) : openConfirm(row));
      box.append(button);
    });
    return rows.length;
  }

  function decorateActions() {
    const box = byId('actions');
    if (!box || box.hidden || !current) return;
    const actions = current.actions || [];
    box.replaceChildren();
    const shown = new Set();
    actions.forEach((action) => {
      const button = el('button');
      button.type = 'button';
      button.dataset.actionId = action.id;
      button.append(el('span', action.label));
      const meta = [];
      if (action.costs && action.costs.length) meta.push(costText(action.costs));
      else meta.push('不花资源');
      if (action.duration_hours) meta.push(action.duration_hours + ' 小时');
      if (action.check && action.check.attribute) meta.push('检定 ' + action.check.attribute);
      button.append(el('small', meta.join(' · ')));
      button.onclick = () => confirmAction(action.id);
      box.append(button);
      shown.add(action.id);
    });
    const extra = drawAdventure(box, shown);
    // 没有可执行动作时不占正文位置：输入栏的提示已经说明可以直接说话。
    box.hidden = !actions.length && !extra;
  }

  // ------------------------------------------------------- 自由意图 -> 有界候选
  // 输入栏上方的浮层（#composer-pop），由工具按钮 #tool-intent 开关。
  function ensureIntentBox() {
    let box = byId('demo-intent');
    if (box) return box;
    const host = byId('composer-pop');
    if (!host) return null;
    box = el('div', undefined, 'demo-intent pop-card');
    box.id = 'demo-intent';
    box.hidden = true;
    box.innerHTML = '<div class="pop-head"><strong>想做别的事</strong><span class="muted">引擎只会从已声明的动作里挑候选，一句话不会直接改状态。</span>' +
      '<button type="button" class="pop-close" data-pop-close aria-label="关闭">×</button></div>' +
      '<div class="pop-row"><input id="demo-intent-text" maxlength="500" placeholder="例如：我想把沙袋压上闸板" aria-label="想做的事">' +
      '<button type="button" id="demo-intent-run" class="primary">看看能做什么</button></div><div id="demo-intent-result" class="intent-result"></div>';
    host.append(box);
    byId('demo-intent-run').onclick = () => askIntent();
    byId('demo-intent-text').addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); askIntent(); }
    });
    box.addEventListener('td-pop-open', () => byId('demo-intent-text').focus());
    return box;
  }

  async function askIntent() {
    if (!current) { say('请先新建或选择旅程'); return; }
    const result = byId('demo-intent-result');
    const text = byId('demo-intent-text').value.trim();
    if (!text) { say('先写一句你想做什么'); return; }
    try {
      const data = await api('/sessions/' + current.id + '/intent', 'POST', { text });
      result.replaceChildren();
      if (!data.matched || !data.matched.length) {
        result.append(el('p', data.note || '没有匹配到已配置的动作；这句话只作为台词或描述。', 'muted'));
        return;
      }
      data.matched.forEach((row) => {
        const item = el('button', undefined, 'candidate');
        item.type = 'button';
        item.append(el('span', row.label), el('small', detailLines(row).join(' · ')));
        item.onclick = () => { pendingIntent = text; openConfirm(row); };
        result.append(item);
      });
      if (data.ambiguous) result.append(el('p', '有多个同分候选，请自己挑一个。', 'muted'));
    } catch (error) {
      say(error.message);
    }
  }

  // -------------------------------------------------- 起点回执 / 预警 / 结局
  // 开局、场景卡、预警进右侧信息栏（#info-scene）；结局与判定结果紧跟正文（#story-after）。
  function panel(id, cls, where) {
    let node = byId(id);
    if (node) return node;
    const host = byId(where === 'story' ? 'story-after' : 'info-scene');
    if (!host) return null;
    node = el('div', undefined, cls);
    node.id = id;
    host.append(node);
    return node;
  }

  function drawDemoPanels() {
    const surface = current;
    syncDiceButton();
    foldCards = new Map();
    if (!surface) { closeCheckOverlay(); syncFoldUi(); return; }
    if (byId('close-event')) byId('close-event').hidden = Boolean(surface.short_scene);
    const scene = panel('short-scene', 'demo-card');
    if (scene) {
      scene.hidden = !surface.short_scene;
      scene.replaceChildren();
      if (surface.short_scene) {
        scene.append(el('strong', surface.location), el('p', surface.short_scene.description));
        const resources = (surface.local_state && surface.local_state.resources) || [];
        const purse = resources.find((r) => r.id === 'pence');
        if (purse) {
          const p = purse.amount;
          scene.append(el('p', '旅费：' + Math.floor(p / 240) + '镑 ' + Math.floor(p % 240 / 12) + '先令 ' + p % 12 + '便士（共' + p + '便士）', 'muted'));
        }
        resources.filter((r) => r.id !== 'pence' && r.amount > 0).forEach((r) =>
          scene.append(el('p', r.name + '：' + r.amount + r.unit, 'muted')));
        if (!surface.event && !surface.ending) {
          scene.append(el('p', '这一幕已经结束，选择下一处地点：', 'muted'));
          surface.places.filter((p) => p.can_move).forEach((p) => {
            const button = el('button', '前往' + p.name);
            button.type = 'button';
            button.dataset.shortDestination = p.id;
            button.onclick = () => openMoveConfirm({target: {name: p.name},
              duration_hours: surface.short_scene.travel_hours, duration_source: 'local.travel_hours',
              travel: {destination: p.id, costs: {}}});
            scene.append(button);
          });
        }
      }
    }
    drawQuests(surface);
    if (window.TDDice) drawChecks(surface);
    const opening = panel('demo-opening', 'demo-card');
    if (opening) {
      opening.replaceChildren();
      if (surface.opening) {
        opening.hidden = false;
        opening.append(el('strong', surface.opening.title || surface.opening.profile_id || '起点'));
        if (surface.opening.identity) opening.append(el('p', '身份：' + surface.opening.identity, 'muted'));
        if (surface.opening.goal) opening.append(el('p', '目标：' + surface.opening.goal, 'muted'));
        if (surface.opening.known && surface.opening.known.length) {
          const list = el('ul', undefined, 'opening-known');
          surface.opening.known.forEach((row) => list.append(el('li', row.text)));
          opening.append(list);
        }
      } else {
        opening.hidden = true;
      }
    }

    const warnings = panel('demo-warnings', 'demo-warnings');
    if (warnings) {
      warnings.replaceChildren();
      if (surface.warnings && surface.warnings.length) {
        warnings.hidden = false;
        warnings.append(el('strong', '已经传到你耳朵里的消息'));
        surface.warnings.forEach((text) => warnings.append(el('p', text)));
      } else {
        warnings.hidden = true;
      }
    }

    const ending = panel('demo-ending', 'demo-card demo-ending', 'story');
    if (ending) {
      ending.replaceChildren();
      if (surface.ending) {
        ending.hidden = false;
        ending.append(el('strong', '阶段结局 · ' + (surface.ending.title || surface.ending.id)));
        ending.append(el('p', surface.ending.summary || ''));
        const recap = el('details', undefined, 'journey-recap');
        recap.append(el('summary', '回顾'));
        const body = el('div');
        recap.append(body);
        let loaded = false;
        recap.addEventListener('toggle', async () => {
          if (!recap.open || loaded) return;
          loaded = true;
          body.textContent = '正在读取…';
          try {
            const data = await api('/sessions/' + surface.id + '/recap');
            body.replaceChildren(el('h3', '关键选择'));
            const list = el('ol');
            data.timeline.forEach((row) => {
              const range = row.time_range || {};
              const time = row.time == null ? range.from + '–' + range.to : row.time;
              const check = row.check ? ' · ' + row.check.attribute + ' · '
                + (row.check.success ? '成功' : '失败') : '';
              list.append(el('li', row.label + '（游戏时刻 ' + time + '）' + check));
            });
            body.append(list, el('h3', '谁记住了你'));
            if (!data.remembered.length) body.append(el('p', '暂无已知记录', 'muted'));
            data.remembered.forEach((row) => body.append(el('p', row.name + '：' + row.text)));
            body.append(el('h3', '开局 → 现在'));
            const before = data.holdings.opening;
            const now = data.holdings.now;
            ['wallet', 'resources'].forEach((key) => {
              const previous = new Map(before[key].map((row) => [row.id, row.amount]));
              now[key].forEach((row) => body.append(el('p', row.name + '：'
                + (previous.get(row.id) || 0) + ' → ' + row.amount + (row.unit || ''))));
            });
            new Set([...Object.keys(before.items), ...Object.keys(now.items)]).forEach((name) =>
              body.append(el('p', name + '：' + (before.items[name] || 0) + ' → ' + (now.items[name] || 0))));
            body.append(el('p', '还有 ' + data.unseen_endings + ' 种结局未见', 'muted'));
          } catch (error) {
            loaded = false;
            body.textContent = error.message;
          }
        });
        ending.append(recap);
        ending.append(el('p', surface.ending.kind === 'lost'
          ? '这一段没有保住，但存档继续：还可以走动、说话、接着收拾。'
          : '这一段已经定下，不会被后面的叙述改写。', 'muted'));
      } else {
        ending.hidden = true;
      }
    }
    syncFoldUi();
  }

  function drawChecks(surface) {
    const scene = byId('short-scene');
    let clockHost = byId('demo-clocks');
    if (surface.clocks && surface.clocks.length) {
      if (!clockHost) { clockHost = el('div'); clockHost.id = 'demo-clocks'; }
      // Reattach after the scene card is redrawn; older packages get no new UI.
      if (scene) {
        if (!surface.short_scene) scene.append(el('strong', surface.location || '当前场景'));
        scene.hidden = false;
        scene.append(clockHost);
      } else {
        const anchor = byId('info-scene');
        if (anchor) anchor.append(clockHost);
      }
      clockHost.hidden = false;
      window.TDDice.clocks(clockHost, surface.clocks);
      decorateClocks(clockHost, surface.clocks);
    } else if (clockHost) clockHost.remove();
    const check = surface.last_check || surface.check_public
      || (surface.result && (surface.result.last_check || surface.result.check_public));
    let host = byId('demo-last-check');
    const fresh = surface.id !== lastCheckSession;
    if (fresh) closeCheckOverlay();
    lastCheckSession = surface.id;
    if (!check) {
      if (host) host.remove();
      lastCheck = null;
      lastCheckSeq = null;
      expectCheck = false;
      return;
    }
    if (!host) host = panel('demo-last-check', 'check-result', 'story');
    if (!host) return;
    // 有 check_seq（服务端为每条新检定盖的单调序号）：序号变了才算新检定，并且只有
    // 本页成功提交的 chat/move 响应才播动画；刷新、读档、切会话得到的 surface 只静态
    // 展示。内容相同的两次检定序号不同，所以会播；没产生新检定的确认序号不变，不播。
    const seq = Number.isInteger(check.check_seq) && check.check_seq > 0 ? check.check_seq : null;
    if (seq !== null) {
      const seqKey = surface.id + ':' + seq;
      const isNew = seqKey !== lastCheckSeq;
      const animateSeq = !fresh && isNew && freshResponses.has(surface);
      expectCheck = false;
      lastCheckSeq = seqKey;
      if (animateSeq || fresh || isNew || !host.firstChild) {
        lastCheck = JSON.stringify(check);
        window.TDDice.roll(host, check, { animate: false });
        if (animateSeq) showCheckOverlay(check, true);
        else if (checkOverlay && checkOverlay.open) showCheckOverlay(check, false);
      }
      return;
    }
    // 旧存档（没有 check_seq）：保留原来的回退逻辑。
    lastCheckSeq = null;
    // A reload/session switch only shows the stored result statically. The
    // request-local flag is set after a successful confirmed check response;
    // changed fingerprints alone never reopen the floating view.
    const key = JSON.stringify(check);
    const animate = !fresh && expectCheck;
    expectCheck = false;
    if (animate || fresh || key !== lastCheck || !host.firstChild) {
      lastCheck = key;
      window.TDDice.roll(host, check, { animate: false });
      if (animate) showCheckOverlay(check, true);
      else if (checkOverlay && checkOverlay.open) showCheckOverlay(check, false);
    }
  }

  // ------------------------------------------------ 局势变化提示（钟阶段 / 揭示 / 开启 / 任务）
  // 只对**本页成功提交**后的新响应显示：api 包装层把 POST /chat、/move 的响应对象记进
  // freshResponses；读档（GET）、刷新页面得到的 surface 不在其中，所以不会重复弹出。
  // 文本全部来自服务端的公开字段，前端不推断、不拼接未公开内容。
  const freshResponses = new WeakSet();
  let noticeOwner = null;
  let noticeItems = [];

  function collectNotices(surface) {
    const rows = [];
    (Array.isArray(surface.clock_notices) ? surface.clock_notices : []).forEach((row) => {
      if (!row || typeof row.text !== 'string' || !row.text.trim()) return;
      const kind = ['stage', 'reveal', 'enable'].includes(row.kind) ? row.kind : 'stage';
      const label = typeof row.clock_label === 'string' ? row.clock_label.trim() : '';
      rows.push({ kind, head: label || '局势', text: row.text.trim() });
    });
    (Array.isArray(surface.quest_notices) ? surface.quest_notices : []).forEach((row) => {
      if (!row || typeof row.title !== 'string' || !row.title.trim()) return;
      rows.push({ kind: 'quest', head: '新的局势', text: row.title.trim(),
        summary: typeof row.summary === 'string' ? row.summary.trim() : '' });
    });
    return rows;
  }

  function drawSituation() {
    const surface = current;
    if (!surface || typeof surface !== 'object') return;
    if (surface !== noticeOwner) {
      noticeOwner = surface;
      noticeItems = freshResponses.has(surface) ? collectNotices(surface) : [];
    }
    let host = byId('demo-situation');
    if (!noticeItems.length) { if (host) host.remove(); return; }
    if (!host) {
      const story = byId('story-text');
      if (!story || !story.parentNode) return;
      host = el('div', undefined, 'situation-notice');
      host.id = 'demo-situation';
      host.setAttribute('role', 'status');
      story.parentNode.insertBefore(host, story);
    }
    host.replaceChildren();
    noticeItems.forEach((row) => {
      const line = el('p', undefined, 'situation-line is-' + row.kind);
      line.append(el('strong', '局势变化 · ' + row.head + '：'), document.createTextNode(row.text));
      if (row.summary) line.append(el('small', row.summary, 'situation-summary'));
      host.append(line);
    });
    const close = el('button', '知道了', 'situation-dismiss');
    close.type = 'button';
    close.onclick = () => { noticeItems = []; host.remove(); };
    host.append(close);
  }

  function trackFreshResponses() {
    try {
      if (typeof api !== 'function' || api.tdTracksFresh) return;
      const originalApi = api;
      api = async function (path, method) {
        const result = await originalApi.apply(this, arguments);
        // 回滚成功：check_seq 随快照回退，回滚后第一次新检定的序号可能等于回滚前页面上记着的那条。
        // 清掉前端记的「上一条检定」，使回滚后的下一次真实检定一定按新检定处理（回滚响应本身
        // 不在 freshResponses 里，所以回滚不会播动画；读档/刷新/切会话路径不经过这里）。
        if (String(method || '').toUpperCase() === 'POST'
          && /^\/sessions\/[^/?]+\/rollback\/[^/?]+(\?|$)/.test(String(path))
          && result && typeof result === 'object') {
          lastCheckSeq = null;
          lastCheck = null;
          expectCheck = false;
        }
        if (String(method || '').toUpperCase() === 'POST'
          && /^\/sessions\/[^/?]+\/(chat|move)(\?|$)/.test(String(path))
          && result && typeof result === 'object') freshResponses.add(result);
        return result;
      };
      api.tdTracksFresh = true;
    } catch (error) { /* 无法包装时只是不显示提示，不影响玩法 */ }
  }

  // ------------------------------------------------ 信息栏卡片收起（钟 / 任务）
  // 纯显示偏好：只写浏览器 localStorage，不写存档、不发请求。按旅程 id 分桶，桶内按卡片 key
  // （clock:<钟 id> / quest:<任务 id>）记录；被收起的卡片放进聊天栏顶栏的「隐藏」区。
  const FOLD_KEY = 'td-folded-cards-v1';
  let foldStore = null;
  let foldCards = new Map();
  let foldPanelSession = null;

  function foldData() {
    if (foldStore) return foldStore;
    foldStore = {};
    try {
      const raw = JSON.parse(localStorage.getItem(FOLD_KEY) || '{}');
      if (raw && typeof raw === 'object' && !Array.isArray(raw)) foldStore = raw;
    } catch (error) { /* 存储不可用或内容损坏：当作没有收起过 */ }
    return foldStore;
  }
  function foldSave() {
    try { localStorage.setItem(FOLD_KEY, JSON.stringify(foldData())); } catch (error) { /* 只是记不住，不影响玩法 */ }
  }
  function foldBucket(create) {
    const sid = current && current.id;
    if (!sid) return null;
    const data = foldData();
    let bucket = data[sid];
    if (!bucket || typeof bucket !== 'object' || Array.isArray(bucket)) {
      if (!create) return null;
      bucket = data[sid] = {};
    }
    return bucket;
  }
  function foldEntry(key) {
    const bucket = foldBucket(false);
    const entry = bucket && bucket[key];
    return entry && typeof entry === 'object' ? entry : null;
  }
  const foldIsFolded = (key) => Boolean(foldEntry(key));
  function foldRegister(card) { foldCards.set(card.key, card); }
  function foldFolded() { return [...foldCards.values()].filter((card) => foldIsFolded(card.key)); }

  // 钟的变化签名：进度格数 + 已到达阶段数 + 当前阶段名（全部来自服务端公开字段）。
  function clockSig(row) {
    const reached = Array.isArray(row.stages) ? row.stages.filter((s) => s && s.reached === true).length : 0;
    return [row.filled, reached, typeof row.stage_label === 'string' ? row.stage_label : ''].join('|');
  }
  // 被收起的卡片有新变化：只打标记，不自动弹回。
  function foldNote(key, sig) {
    const entry = foldEntry(key);
    if (!entry || typeof sig !== 'string' || sig === '' || entry.sig === sig) return;
    entry.sig = sig;
    entry.changed = true;
    foldSave();
  }
  function foldHide(key, sig) {
    const bucket = foldBucket(true);
    if (!bucket) return;
    bucket[key] = { sig: sig || '', changed: false };
    foldSave();
    drawDemoPanels();
    const toggle = byId('hide-toggle');
    if (toggle && !toggle.disabled) toggle.focus({ preventScroll: true });
  }
  function foldRestore(keys) {
    const bucket = foldBucket(false);
    if (!bucket) return;
    keys.forEach((key) => { delete bucket[key]; });
    if (!Object.keys(bucket).length) delete foldData()[current.id];
    foldSave();
    drawDemoPanels();
  }
  function foldButton(key, title, sig) {
    const button = el('button', '收起', 'fold-btn');
    button.type = 'button';
    button.title = '收起「' + title + '」，放进顶栏的「隐藏」';
    button.setAttribute('aria-label', '收起 ' + title);
    button.addEventListener('click', () => foldHide(key, sig));
    return button;
  }

  // 钟：dice.js 把整组钟画进 #demo-clocks，这里只在结果上按序号加标记 / 按钮 / 隐藏。
  function decorateClocks(host, rows) {
    const nodes = Array.from(host.children);
    let shown = 0;
    rows.forEach((row, index) => {
      const node = nodes[index];
      if (!node || !row || row.id == null) { if (node) shown += 1; return; }
      const key = 'clock:' + row.id;
      const title = String(row.label || '钟');
      const sig = clockSig(row);
      foldRegister({ key, type: 'clock', title });
      node.dataset.cardKey = key;
      node.dataset.clockId = String(row.id);
      if (foldIsFolded(key)) {
        foldNote(key, sig);
        node.hidden = true;
        return;
      }
      shown += 1;
      node.append(foldButton(key, title, sig));
    });
    host.hidden = shown === 0;
  }

  // 任务：surface.quests 是 quests.public_view 的玩家投影 {quests:[{quest_id,title,summary,state,due,missing}]}。
  const QUEST_STATE = { proposed: '可接', accepted: '已接下', active: '进行中' };
  function questRows(surface) {
    const block = surface.quests;
    const rows = Array.isArray(block) ? block : (block && Array.isArray(block.quests) ? block.quests : []);
    return rows.filter((row) => row && typeof row === 'object' && typeof row.quest_id === 'string'
      && typeof row.title === 'string' && row.title.trim());
  }
  function drawQuests(surface) {
    const rows = questRows(surface);
    const host = rows.length ? panel('demo-quests', 'quest-list') : byId('demo-quests');
    if (!host) return;
    host.replaceChildren();
    let shown = 0;
    rows.forEach((row) => {
      const key = 'quest:' + row.quest_id;
      const title = row.title.trim();
      foldRegister({ key, type: 'quest', title });
      if (foldIsFolded(key)) return;
      shown += 1;
      const card = el('section', undefined, 'quest-card');
      card.dataset.cardKey = key;
      card.dataset.questId = row.quest_id;
      const head = el('div', undefined, 'quest-head');
      const name = el('strong', title);
      head.append(name, foldButton(key, title, ''));
      card.append(head);
      const state = QUEST_STATE[row.state];
      if (state) card.append(el('small', '任务 · ' + state, 'quest-state'));
      if (typeof row.summary === 'string' && row.summary.trim()) card.append(el('p', row.summary.trim()));
      if (typeof row.due === 'number' && Number.isFinite(row.due)) card.append(el('p', '期限：游戏时刻 ' + row.due, 'muted'));
      if (Array.isArray(row.missing) && row.missing.length) {
        const list = el('ul', undefined, 'quest-missing');
        row.missing.filter((text) => typeof text === 'string' && text).forEach((text) => list.append(el('li', text)));
        card.append(list);
      }
      host.append(card);
    });
    host.hidden = shown === 0;
  }

  // 顶栏「隐藏」区
  const isFoldPanelOpen = () => { const p = byId('hidden-cards-panel'); return Boolean(p && !p.hidden); };
  function closeFoldPanel(focusBack) {
    const panelNode = byId('hidden-cards-panel');
    const toggle = byId('hide-toggle');
    foldPanelSession = null;
    if (toggle) toggle.setAttribute('aria-expanded', 'false');
    if (!panelNode || panelNode.hidden) return;
    panelNode.hidden = true;
    if (focusBack && toggle && !toggle.disabled) toggle.focus({ preventScroll: true });
  }
  function openFoldPanel() {
    const panelNode = byId('hidden-cards-panel');
    const toggle = byId('hide-toggle');
    if (!panelNode || !toggle || toggle.disabled || !current) return;
    if (byId('play-left')?.classList.contains('is-collapsed')) return;
    closeCheckOverlay();
    panelNode.hidden = false;
    toggle.setAttribute('aria-expanded', 'true');
    foldPanelSession = current.id;
    syncFoldUi();
  }
  function renderFoldList(list) {
    const ul = byId('hidden-cards-list');
    if (!ul) return;
    ul.replaceChildren();
    list.forEach((card) => {
      const entry = foldEntry(card.key) || {};
      const item = el('li', undefined, 'hidden-card-row');
      item.dataset.cardKey = card.key;
      item.append(el('span', card.type === 'quest' ? '任务' : '钟', 'hidden-card-kind'),
        el('span', card.title, 'hidden-card-title'));
      if (entry.changed) item.append(el('span', '有变化', 'hidden-card-new'));
      const restore = el('button', '恢复', 'hidden-card-restore');
      restore.type = 'button';
      restore.setAttribute('aria-label', '恢复 ' + card.title + ' 到右侧');
      restore.addEventListener('click', () => {
        foldRestore([card.key]);
        const next = byId('hidden-cards-list')?.querySelector('button');
        (next || byId('hide-toggle'))?.focus({ preventScroll: true });
      });
      item.append(restore);
      ul.append(item);
    });
  }
  function syncFoldUi() {
    const toggle = byId('hide-toggle');
    if (!toggle) return;
    const list = current ? foldFolded() : [];
    if (!list.length || !current || (foldPanelSession && foldPanelSession !== current.id)) closeFoldPanel();
    if (isFoldPanelOpen()) {
      renderFoldList(list);
      // 面板正开着就等于看过了：清掉「有变化」标记，下面的提示点随之消失。
      let cleared = false;
      list.forEach((card) => {
        const entry = foldEntry(card.key);
        if (entry && entry.changed) { entry.changed = false; cleared = true; }
      });
      if (cleared) foldSave();
    }
    const changed = list.some((card) => (foldEntry(card.key) || {}).changed);
    const count = byId('hide-count');
    if (count) count.textContent = String(list.length);
    const dot = byId('hide-dot');
    if (dot) dot.hidden = !changed;
    toggle.disabled = list.length === 0;
    toggle.setAttribute('aria-label', '隐藏区，' + (list.length
      ? '已收起 ' + list.length + ' 张卡片' + (changed ? '，有新的变化' : '') : '没有收起的卡片'));
    toggle.dataset.changed = changed ? 'true' : 'false';
  }
  function installFoldArea() {
    const toggle = byId('hide-toggle');
    if (!toggle) return;
    toggle.addEventListener('click', () => { if (isFoldPanelOpen()) closeFoldPanel(true); else openFoldPanel(); });
    byId('hidden-restore-all')?.addEventListener('click', () => {
      foldRestore(foldFolded().map((card) => card.key));
      byId('hide-toggle')?.focus({ preventScroll: true });
    });
    // 先于 play-ui 的 Esc（收起整个聊天栏）处理：面板开着时 Esc 只关面板。
    document.addEventListener('keydown', (event) => {
      if (event.key !== 'Escape' || !isFoldPanelOpen()) return;
      event.preventDefault();
      event.stopPropagation();
      closeFoldPanel(true);
    }, true);
    // 用 pointerdown：点「恢复」后行会被重绘，click 时目标已脱离面板，会被误判成点在外面。
    document.addEventListener('pointerdown', (event) => {
      if (!isFoldPanelOpen()) return;
      const target = event.target;
      if (target instanceof Node && (byId('hidden-cards-panel').contains(target) || toggle.contains(target))) return;
      closeFoldPanel(false);
    }, true);
    syncFoldUi();
  }

  // --------------------------------------------------------------- 装到已有界面上
  function install() {
    if (!byId('new-form') || !byId('actions')) return;
    ensureConfirmDialog();
    byId('dice-toggle')?.addEventListener('click', () => {
      if (checkOverlay && checkOverlay.open) closeCheckOverlay();
      else showCheckOverlay(currentCheck(), false);
    });
    syncDiceButton();
    installFoldArea();
    const drawer = byId('play-left');
    if (drawer) new MutationObserver(() => {
      if (drawer.classList.contains('is-collapsed')) { closeCheckOverlay(); closeFoldPanel(); }
      else positionCheckOverlay();
    }).observe(drawer, { attributes: true, attributeFilter: ['class'] });
    ensureIntentBox();
    const inner = byId('inner');
    if (inner && !byId('unmatched-intents')) {
      const log = el('details', undefined, 'unmatched-intents');
      log.id = 'unmatched-intents';
      log.append(el('summary', '未匹配意图'));
      const rows = el('div');
      log.append(rows);
      log.addEventListener('toggle', async () => {
        if (!log.open) return;
        rows.textContent = '正在读取…';
        try {
          const data = await api('/inner/unmatched-intents?limit=100');
          rows.replaceChildren();
          if (!data.items.length) rows.append(el('p', '暂无记录', 'muted'));
          data.items.forEach((row) => {
            const item = el('div', undefined, 'unmatched-intent-row');
            item.append(el('p', row.text), el('small', row.package_id + ' · ' + row.revision
              + ' · ' + row.location_id + (row.event_id ? ' / ' + row.event_id : '') + ' · ' + row.created));
            rows.append(item);
          });
        } catch (error) { rows.textContent = error.message; }
      });
      inner.prepend(log);
    }

    const form = byId('new-form');
    form.onsubmit = (event) => {
      event.preventDefault();
      sessionEpoch += 1; actionBusy = false; expectCheck = false; closeCheckOverlay();
      (async () => {
        try {
          const body = { title: byId('session-title').value, mode: byId('session-mode').value };
          const profile = chosenProfile();
          if (profile) body.profile = profile;
          current = await api('/sessions', 'POST', body);
          byId('new-dialog').close();
          await loadSession(current.id);
        } catch (error) {
          say(error.message);
        }
      })();
    };

    const originalLoadSession = loadSession;
    loadSession = async function () {
      sessionEpoch += 1;
      actionBusy = false;
      expectCheck = false;
      closeCheckOverlay();
      return originalLoadSession.apply(this, arguments);
    };
    window.loadSession = loadSession;
    const originalAuthorMode = window.TDEnterAuthorMode;
    if (originalAuthorMode) window.TDEnterAuthorMode = function () {
      sessionEpoch += 1; actionBusy = false; expectCheck = false; closeCheckOverlay();
      const result = originalAuthorMode.apply(this, arguments);
      syncDiceButton();
      return result;
    };
    trackFreshResponses();
    const originalRender = render;
    render = function () {
      originalRender.apply(this, arguments);
      decorateActions();
      drawDemoPanels();
      drawSituation();
    };

    drawProfiles();
    if (current) { decorateActions(); drawDemoPanels(); drawSituation(); }
  }

  async function loadProfiles() {
    try {
      startConfig = await api('/start-profiles');
    } catch (error) {
      startConfig = { configured: false, profiles: [] };
    }
    drawProfiles();
  }

  window.addEventListener('DOMContentLoaded', () => {
    try {
      install();
      loadProfiles();
    } catch (error) {
      say('Demo 界面未能挂载：' + error.message);
    }
  });
})();
