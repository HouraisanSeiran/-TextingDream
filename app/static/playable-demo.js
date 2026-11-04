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
    const anchor = byId('story-text') || byId('play-left');
    if (!anchor) return;
    const scroller = byId('surface') || anchor;
    const rect = scroller.getBoundingClientRect();
    const width = Math.min(380, Math.max(240, rect.width - 24), innerWidth - 24);
    const left = Math.max(12, Math.min(rect.left + rect.width / 2 - width / 2, innerWidth - width - 12));
    const composer = byId('chat-form');
    const inputTop = composer && !composer.hidden ? composer.getBoundingClientRect().top : innerHeight;
    const desiredTop = Math.max(12, rect.top + 12);
    const top = Math.min(desiredTop, Math.max(12, innerHeight - 220));
    checkOverlay.style.width = width + 'px';
    checkOverlay.style.left = left + 'px';
    checkOverlay.style.top = top + 'px';
    checkOverlay.style.maxHeight = Math.max(160, Math.min(innerHeight - top - 12,
      inputTop > top + 160 ? inputTop - top - 8 : innerHeight - top - 100)) + 'px';
    checkOverlay.dataset.anchor = 'surface';
  }

  function closeCheckOverlay() {
    if (!checkOverlay) return;
    const host = checkOverlay.querySelector('.dice-overlay-result');
    if (host && window.TDDice) window.TDDice.stop(host);
    if (checkOverlay.open) checkOverlay.close();
  }

  function showCheckOverlay(check) {
    // Never cover an unsubmitted author/player confirmation dialog.
    if (document.querySelector('dialog[open]:not(#demo-dice-overlay)')) return;
    if (!checkOverlay) {
      checkOverlay = el('dialog', undefined, 'dice-overlay');
      checkOverlay.id = 'demo-dice-overlay';
      checkOverlay.setAttribute('aria-labelledby', 'demo-dice-overlay-title');
      const head = el('div', undefined, 'dice-overlay-head');
      const title = el('strong', '判定结果');
      title.id = 'demo-dice-overlay-title';
      const close = el('button', '×', 'dice-overlay-close');
      close.type = 'button'; close.title = '关闭判定结果';
      close.setAttribute('aria-label', '关闭判定结果');
      close.addEventListener('click', closeCheckOverlay);
      head.append(title, close);
      checkOverlay.append(head, el('div', undefined, 'dice-overlay-result'));
      checkOverlay.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') { event.preventDefault(); closeCheckOverlay(); }
      });
      checkOverlay.addEventListener('close', () => {
        if (checkOverlay.open) return;
        window.TDDice.stop(checkOverlay.querySelector('.dice-overlay-result'));
        if (overlayFocus && overlayFocus.isConnected) overlayFocus.focus({ preventScroll: true });
      });
      document.body.append(checkOverlay);
      const anchor = byId('surface') || byId('play-left');
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
    positionCheckOverlay();
    window.TDDice.roll(checkOverlay.querySelector('.dice-overlay-result'), check, { mode: 'spin' });
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
    if (!surface) { closeCheckOverlay(); return; }
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
      expectCheck = false;
      return;
    }
    if (!host) host = panel('demo-last-check', 'check-result', 'story');
    if (!host) return;
    // A reload/session switch only shows the stored result statically. The
    // request-local flag is set after a successful confirmed check response;
    // changed fingerprints alone never reopen the floating view.
    const key = JSON.stringify(check);
    const animate = !fresh && expectCheck;
    expectCheck = false;
    if (animate || fresh || key !== lastCheck || !host.firstChild) {
      lastCheck = key;
      window.TDDice.roll(host, check, { animate: false });
      if (animate) showCheckOverlay(check);
    }
  }

  // --------------------------------------------------------------- 装到已有界面上
  function install() {
    if (!byId('new-form') || !byId('actions')) return;
    ensureConfirmDialog();
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
      return originalAuthorMode.apply(this, arguments);
    };
    const originalRender = render;
    render = function () {
      originalRender.apply(this, arguments);
      decorateActions();
      drawDemoPanels();
    };

    drawProfiles();
    if (current) { decorateActions(); drawDemoPanels(); }
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
