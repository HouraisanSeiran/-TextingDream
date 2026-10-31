/* Author-only NPC cards. Journey inspection always uses its pinned revision. */
(function () {
  'use strict';
  const labels = {
    identity: '身份与职业', experiences: '过往经历', values: '价值观',
    goal: '当前目标', pressure: '压力与顾虑', boundaries: '行为底线',
    bargaining: '可商谈的条件', social_context: '阶层、阵营与当地习俗',
    emotion: '初始情绪', failure_response: '交涉失败时的回应方式'
  };
  const kinds = {observation: '亲身观察', rumor: '传闻', interpretation: '个人推测', misunderstanding: '误解（作者标记）'};
  const pageNode = el('section', undefined, 'page');
  pageNode.id = 'npc-cards'; pageNode.hidden = true;
  pageNode.append(el('h2', 'NPC 角色卡'), el('p', '让人物带着目标、经历和立场回应。公开内容用于现场对话；私密内容仅用于本人视角和作者评估。'));
  const toolbar = el('div', undefined, 'toolbar');
  const select = el('select'); select.setAttribute('aria-label', '选择 NPC');
  const mode = el('p', '', 'muted');
  const form = el('form', undefined, 'card');
  form.hidden = true;
  const fields = el('div', undefined, 'two-col');
  const controls = {};
  for (const [key, title] of Object.entries(labels)) {
    const box = el('div');
    const label = el('label', title), input = el('textarea');
    input.rows = 2; input.maxLength = 400; input.name = key;
    label.append(input);
    const publicLabel = el('label'), publicInput = el('input');
    publicInput.type = 'checkbox';
    publicLabel.append(publicInput, document.createTextNode(' 可用于公开对话'));
    box.append(label, publicLabel); fields.append(box);
    controls[key] = {input, publicInput};
  }
  const knowledge = el('div');
  const add = button('＋ 添加所知或误解', () => addKnowledge()); add.type = 'button';
  const save = el('button', '保存角色卡为新版本', 'primary'); save.type = 'submit';
  const state = el('div');
  form.append(fields, el('h3', '所知、传闻与误解'),
    el('p', '每条说法保留来源。确信程度只是人物的把握，不代表事情是真的。私密消息不会自动公开。', 'muted'),
    knowledge, add, el('p', '保存后，新旅程使用新版；已有旅程保留原角色卡。', 'muted'), save);
  toolbar.append(button('读取最新角色卡', () => load(false)), button('查看当前旅程角色与记忆', () => load(true)), select);
  pageNode.append(toolbar, mode, form, state);
  document.querySelector('main').append(pageNode);
  const nav = button('NPC 角色卡', () => TDNav.show('npc-cards'), 'workspace-link');
  nav.id = 'workspace-npc-cards'; $('workspace-elements').after(nav);
  const legacyNav = button('NPC 角色卡', () => TDNav.show('npc-cards'));
  legacyNav.dataset.page = 'npc-cards';
  document.querySelector('#legacy nav').append(legacyNav);

  let data = null, selected = null, readOnly = false;
  let knowledgeControls = [];
  const drafts = new Map();

  function addKnowledge(entry = {}) {
    if (knowledgeControls.length >= 16) throw Error('每张角色卡最多 16 条所知');
    const row = el('div', undefined, 'card');
    const inputs = {};
    for (const [key, title] of [['text', '说法'], ['source', '来源']]) {
      const label = el('label', title), input = el('input');
      input.value = entry[key] || ''; input.maxLength = 400; input.required = true;
      label.append(input); row.append(label); inputs[key] = input;
    }
    const kindLabel = el('label', '性质'), kind = el('select');
    kind.setAttribute('aria-label', '性质');
    for (const [value, title] of Object.entries(kinds)) {
      const option = el('option', title); option.value = value; kind.append(option);
    }
    kind.value = entry.kind || 'rumor'; kindLabel.append(kind);
    const confidenceLabel = el('label', '确信程度（0–1）'), confidence = el('input');
    confidence.type = 'number'; confidence.min = '0'; confidence.max = '1'; confidence.step = '.05';
    confidence.required = true; confidence.value = entry.confidence ?? .5; confidenceLabel.append(confidence);
    const visibleLabel = el('label'), visible = el('input'); visible.type = 'checkbox';
    visible.checked = entry.visibility === 'public'; visibleLabel.append(visible, document.createTextNode(' 可用于公开对话'));
    const item = {row, ...inputs, kind, confidence, visible};
    const remove = button('移除此条', () => {
      knowledgeControls = knowledgeControls.filter(x => x !== item); row.remove();
    }); remove.type = 'button';
    row.append(kindLabel, confidenceLabel, visibleLabel, remove);
    knowledgeControls.push(item); knowledge.append(row);
  }

  function collect() {
    const card = {version: 1};
    for (const [key, {input, publicInput}] of Object.entries(controls)) {
      card[key] = {text: input.value, visibility: publicInput.checked ? 'public' : 'private'};
    }
    card.knowledge = knowledgeControls.map(x => ({text: x.text.value, source: x.source.value,
      kind: x.kind.value, confidence: Number(x.confidence.value), visibility: x.visible.checked ? 'public' : 'private'}));
    return card;
  }

  function draw() {
    const actor = data.characters.find(c => c.id === select.value);
    selected = actor?.id || null; form.hidden = !actor; state.replaceChildren();
    if (!actor) return;
    const card = drafts.get(actor.id) || actor.card;
    for (const [key, {input, publicInput}] of Object.entries(controls)) {
      input.value = card[key].text; publicInput.checked = card[key].visibility === 'public';
    }
    knowledge.replaceChildren(); knowledgeControls = [];
    card.knowledge.forEach(addKnowledge);
    form.querySelectorAll('input, textarea, select, button').forEach(x => { x.disabled = readOnly; });
    state.append(el('h3', '现有属性与性格'), el('p', actor.traits.join('、') || '尚未填写性格标签'));
    const abilities = el('div', undefined, 'chips');
    for (const [key, value] of Object.entries(actor.attributes)) abilities.append(el('span', key + '：' + value));
    state.append(abilities);
    if (readOnly) {
      state.append(el('h3', '本旅程的关系与记忆'));
      const snapshot = actor.state;
      if (!snapshot) { state.append(el('p', '本旅程使用的版本尚未配置角色卡。')); return; }
      const relationships = snapshot.relationships || {};
      for (const [target, values] of Object.entries(relationships)) {
        state.append(el('p', target + ' · ' + Object.entries(values).map(([k, v]) => (k === 'trust' ? '信任' : k) + '：' + v).join(' / ')));
      }
      if (!snapshot.memories.length) state.append(el('p', '暂无已记录经历。'));
      for (const memory of snapshot.memories) {
        state.append(el('p', memory.text), el('small', '来源：' + (memory.source || '未注明') + ' · ' +
          (memory.kind === 'npc_event' ? '亲眼目睹的行动结果' : memory.kind === 'statement' ? '听到的说法' : '人物所闻')));
      }
    }
  }

  async function load(journey) {
    if (journey && !current) throw Error('请先选择一个旅程');
    const wasHidden = form.hidden; form.hidden = true;
    toolbar.querySelectorAll('button, select').forEach(x => { x.disabled = true; });
    try {
      const result = await api('/inner/npc-cards' + (journey ? '?session_id=' + encodeURIComponent(current.id) : ''));
      data = result; readOnly = journey; drafts.clear();
      select.replaceChildren(...data.characters.map(c => { const option = el('option', c.name); option.value = c.id; return option; }));
      mode.textContent = !data.characters.length ? '当前没有 NPC，请先在里层创作中建立人物。' :
        journey ? '正在查看当前旅程，角色卡只读；下方显示该旅程的关系和最近经历。' : '正在编辑最新角色包。';
      draw();
    } catch (error) {
      form.hidden = wasHidden; throw error;
    } finally {
      toolbar.querySelectorAll('button, select').forEach(x => { x.disabled = false; });
    }
  }
  select.addEventListener('change', () => {
    if (selected && !readOnly) drafts.set(selected, collect());
    draw();
  });
  form.addEventListener('submit', event => {
    event.preventDefault();
    safe(async () => {
      if (readOnly || !selected) return;
      const cid = selected, card = collect();
      pageNode.querySelectorAll('input, textarea, select, button').forEach(x => { x.disabled = true; });
      try {
        const result = await api('/inner/npc-cards/' + encodeURIComponent(cid), 'PUT', {revision: data.revision, card});
        data.revision = result.revision;
        data.characters.find(c => c.id === cid).card = card; drafts.delete(cid);
        notice('角色卡已保存，新建旅程即可使用。');
      } finally {
        pageNode.querySelectorAll('input, textarea, select, button').forEach(x => { x.disabled = false; });
      }
    });
  });
  TDNav.register('npc-cards', {title: 'NPC 角色卡', enter: () => safe(() => load(false))});
})();
