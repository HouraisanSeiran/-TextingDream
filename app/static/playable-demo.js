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
    byId('demo-confirm-cancel').onclick = () => { dialog.close(); pending = null; };
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
    if (action.check && action.check.attribute) {
      lines.push('检定：' + action.check.attribute + ' · 难度 ' + action.check.difficulty);
    }
    if (action.ends_event) lines.push('这一步会结束当前事件');
    return lines;
  }

  function openConfirm(action) {
    const dialog = ensureConfirmDialog();
    const body = byId('demo-confirm-body');
    body.replaceChildren(el('p', action.label, 'confirm-title'));
    detailLines(action).forEach((line) => body.append(el('p', line, 'confirm-line')));
    const run = byId('demo-confirm-run');
    if (!action.confirm) {
      body.append(el('p', '没有拿到确认凭据，请重新获取候选（可能状态已经变了）。', 'muted'));
      run.disabled = true;
    } else {
      run.disabled = false;
    }
    pending = action;
    dialog.showModal();
  }

  async function runPending(dialog) {
    if (!pending || typeof current === 'undefined' || !current) return;
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
    try {
      current = await api('/sessions/' + current.id + '/chat', 'POST', {
        message,
        action_id: action.action_id,
        channel: 'action',
        confirm: action.confirm || undefined,
      });
      const intent = byId('demo-intent-text');
      if (intent) intent.value = '';
      // 无事件时服务端不会产生模型正文。这里只展示**服务端已确认**的结果：
      // 动作公开标签 + 时长/资源前后。没有 local_result 就不造任何话。
      showLocalResult(current && current.local_result);
      render();
    } catch (error) {
      say(error.message);
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
      openConfirm(await api('/sessions/' + current.id + '/confirm/' + actionId));
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
    box.append(el('p', '就地能做的事（已做过的不会重复出现；缺执行器的不会列出）', 'muted'));
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
    if (!actions.length && !extra) {
      box.append(el('p', '此刻没有引擎能替你执行的动作。可以直接说话，或描述你想做什么。', 'muted'));
    }
  }

  // ------------------------------------------------------- 自由意图 -> 有界候选
  function ensureIntentBox() {
    let box = byId('demo-intent');
    if (box) return box;
    const form = byId('chat-form');
    if (!form || !form.parentNode) return null;
    box = el('div', undefined, 'demo-intent');
    box.id = 'demo-intent';
    box.innerHTML = '<label class="muted">想做但上面没列出的事：引擎只会从已声明的动作里挑候选，不会因为一句话就改状态。</label>' +
      '<div class="intent-row"><input id="demo-intent-text" maxlength="500" placeholder="例如：我想把沙袋压上闸板">' +
      '<button type="button" id="demo-intent-run">看看能做什么</button></div><div id="demo-intent-result"></div>';
    form.parentNode.insertBefore(box, form);
    byId('demo-intent-run').onclick = () => askIntent();
    byId('demo-intent-text').addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); askIntent(); }
    });
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
  function panel(id, cls) {
    let node = byId(id);
    if (node) return node;
    const anchor = byId('story-text');
    if (!anchor || !anchor.parentNode) return null;
    node = el('div', undefined, cls);
    node.id = id;
    anchor.parentNode.insertBefore(node, anchor);
    return node;
  }

  function drawDemoPanels() {
    const surface = current;
    if (!surface) return;
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

    const ending = panel('demo-ending', 'demo-card demo-ending');
    if (ending) {
      ending.replaceChildren();
      if (surface.ending) {
        ending.hidden = false;
        ending.append(el('strong', '阶段结局 · ' + (surface.ending.title || surface.ending.id)));
        ending.append(el('p', surface.ending.summary || ''));
        ending.append(el('p', surface.ending.kind === 'lost'
          ? '这一段没有保住，但存档继续：还可以走动、说话、接着收拾。'
          : '这一段已经定下，不会被后面的叙述改写。', 'muted'));
      } else {
        ending.hidden = true;
      }
    }
  }

  // --------------------------------------------------------------- 装到已有界面上
  function install() {
    if (!byId('new-form') || !byId('actions')) return;
    ensureConfirmDialog();
    ensureIntentBox();

    const form = byId('new-form');
    form.onsubmit = (event) => {
      event.preventDefault();
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
