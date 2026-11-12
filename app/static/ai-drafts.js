/* Author-only AI drafts: element and NPC card drafts. Nothing enters the library or a
 * package until the author confirms; running journeys keep their pinned revision. */
(function () {
  'use strict';
  const STATUS = {draft: '草稿（未确认）', confirmed: '已确认', rejected: '已拒绝'};
  const pageNode = el('section', undefined, 'page');
  pageNode.id = 'ai-drafts'; pageNode.hidden = true;
  pageNode.append(el('h2', 'AI 草稿'),
    el('p', '填名字、标签和大概方向，AI 补全成草稿。草稿是 AI 推演、未经来源核实；确认前不进百科库、不进任何故事包，也不影响正在进行的旅程。', 'muted'));

  function field(form, title, name, opts = {}) {
    const label = el('label', title);
    const input = el(opts.area ? 'textarea' : 'input');
    input.name = name; input.maxLength = opts.max || 80;
    if (opts.area) input.rows = 2;
    if (opts.required) input.required = true;
    if (opts.placeholder) input.placeholder = opts.placeholder;
    label.append(input); form.append(label);
    return input;
  }
  const splitTags = text => text.split(/[,，、\s]+/).map(x => x.trim()).filter(Boolean);

  // ---- 元素表单
  const elementForm = el('form', undefined, 'card');
  elementForm.append(el('h3', '生成元素草稿'));
  const eName = field(elementForm, '名字', 'name', {required: true});
  const eTags = field(elementForm, '标签（逗号或顿号分隔，可写中文）', 'tags', {max: 300});
  const eDir = field(elementForm, '大概方向', 'direction', {area: true, max: 500});
  const ePrimary = field(elementForm, '主标签提示（可空，如 beast、dish、race）', 'primary', {max: 64});
  const eTradition = field(elementForm, '传统（可空，小写英文，如 western、eastern）', 'tradition', {max: 40});
  const eSubmit = el('button', '生成元素草稿', 'primary'); eSubmit.type = 'submit';
  elementForm.append(eSubmit);

  // ---- NPC 表单
  const npcForm = el('form', undefined, 'card');
  npcForm.append(el('h3', '生成 NPC 角色卡草稿'));
  const nName = field(npcForm, '名字', 'name', {required: true});
  const nTags = field(npcForm, '标签', 'tags', {max: 300});
  const nDir = field(npcForm, '大概方向', 'direction', {area: true, max: 300});
  const nCharLabel = el('label', '挂到哪个 NPC（确认时用，可稍后再选）');
  const nChar = el('select'); nCharLabel.append(nChar); npcForm.append(nCharLabel);
  const nSubmit = el('button', '生成角色卡草稿', 'primary'); nSubmit.type = 'submit';
  npcForm.append(nSubmit);

  const forms = el('div', undefined, 'two-col');
  forms.append(elementForm, npcForm);
  const listBox = el('div');
  const preview = el('div', undefined, 'card'); preview.hidden = true;
  pageNode.append(forms, el('h3', '草稿列表'),
    el('div', undefined, 'toolbar'), listBox, preview);
  pageNode.querySelector('.toolbar').append(button('刷新列表', () => loadList()));
  document.querySelector('main').append(pageNode);

  const anchor = $('workspace-npc-cards') || $('workspace-elements');
  const nav = button('AI 草稿', () => TDNav.show('ai-drafts'), 'workspace-link');
  nav.id = 'workspace-ai-drafts';
  nav.dataset.nav = 'ai-drafts';
  if (anchor) anchor.after(nav);
  const legacy = document.querySelector('#legacy nav');
  if (legacy) {
    const legacyNav = button('AI 草稿', () => TDNav.show('ai-drafts'));
    legacyNav.dataset.page = 'ai-drafts'; legacy.append(legacyNav);
  }

  let cards = {revision: null, characters: []};

  async function loadCharacters() {
    cards = await api('/inner/npc-cards');
    nChar.replaceChildren(el('option', '（暂不指定）'));
    nChar.firstChild.value = '';
    for (const c of cards.characters) {
      const option = el('option', c.name); option.value = c.id; nChar.append(option);
    }
  }

  async function loadList() {
    const rows = await api('/inner/ai-drafts');
    listBox.replaceChildren();
    if (!rows.length) { listBox.append(el('p', '还没有草稿。', 'muted')); return; }
    for (const row of rows) {
      const line = el('div', undefined, 'card');
      line.append(el('strong', (row.type === 'element' ? '元素 · ' : 'NPC · ') + row.request.name),
        el('span', ' ' + (STATUS[row.status] || row.status) + (row.offline ? ' · 离线模板' : '')),
        button('查看', () => show(row.id)));
      listBox.append(line);
    }
  }

  async function show(id) {
    const draft = await api('/inner/ai-drafts/' + encodeURIComponent(id));
    preview.replaceChildren(); preview.hidden = false;
    preview.append(el('h3', (draft.type === 'element' ? '元素草稿：' : 'NPC 草稿：') + draft.request.name),
      el('p', draft.notice, 'muted'),
      el('p', '状态：' + (STATUS[draft.status] || draft.status) + ' · 修订 ' + draft.revision +
        (draft.offline ? ' · 离线模板（未调用模型）' : '')),
      el('p', '校验：' + (draft.validation.ok ? '通过' : '未通过 ' + draft.validation.errors.join('；'))));
    if (draft.type === 'element') {
      preview.append(el('p', '强制口径：evidence_grade=inferred，无来源，needs_review / needs_detail，入库命名空间 player-created。', 'muted'));
    }
    if (draft.confirmed) {
      preview.append(el('p', draft.type === 'element'
        ? '已入库：' + draft.confirmed.namespace + '/' + draft.confirmed.element_id + ' v' + draft.confirmed.version
        : '已保存为新故事包版本 ' + draft.confirmed.revision + '（已开始的旅程仍用旧卡）'));
    }
    const editor = el('textarea'); editor.rows = 18; editor.style.width = '100%';
    editor.value = JSON.stringify(draft.content, null, 2);
    editor.disabled = draft.status === 'rejected';
    preview.append(el('label', '内容（可改后保存，保存会重新校验）'), editor);
    const bar = el('div', undefined, 'toolbar');
    if (draft.status !== 'rejected') {
      bar.append(button('保存修改', async () => {
        let content;
        try { content = JSON.parse(editor.value); } catch (e) { throw Error('内容不是合法 JSON'); }
        await api('/inner/ai-drafts/' + encodeURIComponent(id), 'PUT', {revision: draft.revision, content});
        notice('修改已保存，需重新确认。'); await show(id); await loadList();
      }));
      bar.append(button('确认', async () => {
        const body = {revision: draft.revision};
        if (draft.type === 'npc') {
          await loadCharacters();
          body.character_id = nChar.value || draft.request.character_id || null;
          body.package_revision = cards.revision;
          if (!body.character_id) throw Error('请先在左侧“挂到哪个 NPC”里选择人物再确认');
        }
        await api('/inner/ai-drafts/' + encodeURIComponent(id) + '/confirm', 'POST', body);
        notice(draft.type === 'element' ? '已确认入库，可在元素装配页检索。' : '角色卡已保存为新版本，新旅程使用新卡。');
        await show(id); await loadList();
      }, 'primary'));
      if (draft.status === 'draft') {
        bar.append(button('拒绝', async () => {
          await api('/inner/ai-drafts/' + encodeURIComponent(id) + '/reject', 'POST', {revision: draft.revision});
          notice('草稿已拒绝。'); await show(id); await loadList();
        }));
      }
    }
    preview.append(bar);
  }

  async function submit(form, path, body) {
    form.querySelectorAll('input, textarea, select, button').forEach(x => { x.disabled = true; });
    try {
      const draft = await api(path, 'POST', body);
      notice('草稿已生成，请预览后确认或拒绝。');
      await loadList(); await show(draft.id);
    } finally {
      form.querySelectorAll('input, textarea, select, button').forEach(x => { x.disabled = false; });
    }
  }

  elementForm.addEventListener('submit', event => {
    event.preventDefault();
    safe(() => submit(elementForm, '/inner/ai-drafts/elements', {
      name: eName.value, tags: splitTags(eTags.value), direction: eDir.value,
      primary: ePrimary.value.trim() || null, tradition: eTradition.value.trim() || null}));
  });
  npcForm.addEventListener('submit', event => {
    event.preventDefault();
    safe(() => submit(npcForm, '/inner/ai-drafts/npcs', {
      name: nName.value, tags: splitTags(nTags.value), direction: nDir.value,
      character_id: nChar.value || null}));
  });

  TDNav.register('ai-drafts', {title: 'AI 草稿', enter: () => safe(async () => { await loadCharacters(); await loadList(); })});
})();
