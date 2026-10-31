// 历史采纳作者页组件（独立文件，不挂 index 脚本、不改共享 static）。
//
// 挂载：在作者页自己加一行 <script type="module" src="/static/world-history.js"></script>
// 和一个 <div id="world-history"></div>；本文件只碰自己那个容器。
//
// 它在页面里只做一件事：把服务端**已经算好的**回放草稿逐页展示，让作者按 ref 挑选、
// 标公开范围、确认采纳。它不自己算历史、不猜年份、不改地图。
//
// 服务端接口（作者侧，全部 `/api/inner/history/...`，全部要 token）：
//   GET  /api/inner/history/imports                    → 可回放的导入
//   POST /api/inner/history/previews                   → 回放草稿（只收 import_id + 年 + 分支）
//   GET  /api/inner/history/previews/{id}              → 草稿
//   GET  /api/inner/history/previews/{id}/page         → {items,total,pages,page,size}
//   POST /api/inner/history/previews/{id}/review       → 审阅（带 expected_revision）
//   POST /api/inner/history/previews/{id}/commit       → 固定快照
//   GET  /api/inner/history/snapshots/{id}             → 作者视图
//   POST /api/inner/history/snapshots/{id}/adopt       → 采纳（带 expected_story_revision）
//
// 失败一律原样显示服务端的中文拒收原因：这里不编默认值、不重试、不掩盖。

// Keep helper names private: this classic script shares the page with app.js.
(() => {
const API = '/api/inner/history';
const PAGE_SIZE = 20;

// 作者令牌由 app.js 维护（顶层 `let token`）。作者页内取它；URL、localStorage
// 与静态资源都不得携带或记录它。
function authorToken() {
  try {
    if (typeof token === 'string' && token) return token;   // app.js 的顶层变量
  } catch { /* not in scope yet */ }
  return window.__textileDreamToken || '';
}

const CATEGORIES = [
  ['annals', '事件'],
  ['polities', '国家'],
  ['settlements', '城镇'],
  ['people', '人物'],
];

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === 'class') node.className = value;
    else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else if (value !== null && value !== undefined) node.setAttribute(key, value);
  }
  for (const child of children) {
    if (child === null || child === undefined) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

async function request(path, options = {}) {
  const response = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json',
               'X-TextileDream-Token': authorToken() },
    ...options,
  });
  const text = await response.text();
  let body = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = null; }
  if (!response.ok) {
    const detail = (body && (body.detail || body.message)) || text || response.statusText;
    throw new Error(detail);
  }
  return body;
}

class WorldHistoryPanel extends HTMLElement {
  constructor() {
    super();
    this.previewId = null;
    this.draft = null;
    this.category = 'annals';
    this.page = 0;
    this.selected = new Map();   // ref → {ref, category, summary}
    this.publicRefs = new Set();
    this.links = {};             // ref → location_id
    this.busy = false;
    this.message = '';
    this.error = '';
  }

  // --------------------------------------------------------------- lifecycle
  connectedCallback() {
    // The panel needs a full-width row of its own. Inside the map sidebar it was 336px
    // wide, so a stable ref (a long casnap:… string) wrapped badly and the main area was
    // left empty. Spanning the existing grid row is a local change: no global CSS, no
    // index.html edit, and the map controls above keep their own geometry.
    this.style.gridColumn = '1 / -1';
    this.style.minWidth = '0';
    this.style.display = 'block';
    const id = this.getAttribute('preview-id');
    if (id) this.load(id);
    else if (authorToken()) this.loadImports();
    else this.render(); // The host loads imports when entering the map page after bootstrap.
  }

  async load(previewId) {
    this.previewId = previewId;
    await this.guard(async () => {
      this.draft = await request(`/previews/${encodeURIComponent(previewId)}`);
      this.page = 0;
    });
  }

  async loadImports() {
    await this.guard(async () => {
      const body = await request('/imports');
      this.imports = body.imports || [];
      // The server tells us which package revision is current; adopt/link must send the
      // revision the author is actually looking at, not one re-read at submit time.
      this.storyRevision = body.story_revision || this.storyRevision;
      if (!this.importId && this.imports.length) {
        this.importId = this.imports[0].import_id;
      }
    });
  }

  async startPreview() {
    await this.guard(async () => {
      const year = Number(this.yearInput);
      if (this.yearInput === '' || !Number.isFinite(year)) {
        throw new Error('基准年必须是一个数字（可含小数）');
      }
      const body = await request('/previews', { method: 'POST', body: JSON.stringify({
        import_id: this.importId,
        base_year: year,
        branch: this.branchInput || null,
      }) });
      this.draft = body.preview;
      this.previewId = body.preview.id;
      this.selected.clear();
      this.publicRefs.clear();
      this.links = {};
      this.slice = null;
      this.snapshot = null;
      this.storyRevision = null;
      this.page = 0;
      this.message = body.reused ? '这份回放已经做过，沿用原草稿。' : '已回放，逐项挑要用的部分。';
      await this.goPage(0);
    });
  }

  async linkStartMap() {
    await this.guard(async () => {
      if (!this.importId) throw new Error('先选一份已导入的地图');
      // The story revision the author is looking at: taken from the draft's frozen base
      // (a preview is pinned to it) or, before any preview, from the snapshot they fixed.
      const base = this.storyRevision
        || (this.draft && this.draft.base_story_revision)
        || (this.snapshot && (this.snapshot.story || {}).base_story_revision);
      if (!base) throw new Error('这份回放没有记录故事包版本；请重新回放一次');
      const body = await request('/map-link', { method: 'POST', body: JSON.stringify({
        import_id: this.importId,
        expected_story_revision: base,
        fog_radius_km: 300,
      }) });
      this.message = body.reused
        ? '这份地图已经是当前故事包的开局地图。'
        : `已把 ${body.link.import_id} 关联为开局地图（版本 ${body.revision}）`;
      // Linking the map commits a NEW story revision. Any preview taken before that still
      // carries the old base revision, and adopting it will (correctly) be refused. Say so
      // instead of silently rebasing the author's earlier decision.
      if (!body.reused && this.draft && this.draft.base_story_revision
          && this.draft.base_story_revision !== body.revision) {
        this.stalePreview = true;
        this.message += '；这份地图关联新建了故事包版本，之前的回放基于旧版本，'
          + '采纳会被拒收——请在新版本上重新回放一次（不会自动改基）。';
      }
    });
  }

  async guard(work) {
    if (this.busy) return;
    this.busy = true;
    this.error = '';
    try {
      await work();
    } catch (error) {
      this.error = error.message;
    } finally {
      this.busy = false;
      this.render();
    }
  }

  // ------------------------------------------------------------------ actions
  async goPage(page) {
    await this.guard(async () => {
      const query = new URLSearchParams({ category: this.category,
                                         page: String(page), size: String(PAGE_SIZE) });
      this.slice = await request(`/previews/${encodeURIComponent(this.previewId)}/page?${query}`);
      this.page = page;
    });
  }

  toggleSelect(item) {
    if (this.selected.has(item.ref)) this.selected.delete(item.ref);
    else this.selected.set(item.ref, { ref: item.ref, category: item.category || this.category });
    this.render();
  }

  togglePublic(ref) {
    if (this.publicRefs.has(ref)) this.publicRefs.delete(ref);
    else this.publicRefs.add(ref);
    this.render();
  }

  setSummary(ref, text) {
    const entry = this.selected.get(ref);
    if (entry) entry.summary = text.trim() || undefined;
  }

  setLink(ref, locationId) {
    const value = locationId.trim();
    if (value) this.links[ref] = value;
    else delete this.links[ref];
  }

  async review() {
    await this.guard(async () => {
      const entries = [...this.selected.values()];
      const summaries = {};
      for (const entry of entries) {
        if (entry.summary) summaries[entry.ref] = entry.summary;
      }
      this.draft = await request(
        `/previews/${encodeURIComponent(this.previewId)}/review`,
        { method: 'POST', body: JSON.stringify({
            entries,
            disclosure: { public_refs: [...this.publicRefs], summaries },
            local_links: this.links,
            expected_revision: this.draft.revision,
          }) });
      this.message = '已审阅，还没有固定在故事包里。';
    });
  }

  async commit() {
    await this.guard(async () => {
      const result = await request(
        `/previews/${encodeURIComponent(this.previewId)}/commit`,
        { method: 'POST', body: JSON.stringify({ expected_revision: this.draft.revision }) });
      this.snapshot = result.snapshot;
      // Remember the story revision the author actually reviewed against. Adopt must send
      // this same value back: reading "the current revision" at submit time would throw
      // away the CAS and let a stale decision land on a newer world.
      this.storyRevision = (result.snapshot.story || {}).base_story_revision;
      this.message = `已固定成历史快照 ${result.snapshot.id}`
        + (result.reused ? '（同内容已存在，未重复写入）' : '');
    });
  }

  async adopt() {
    await this.guard(async () => {
      if (!this.storyRevision) {
        throw new Error('这份快照没有记录审阅时的故事包版本，不能采纳；请重新回放一次');
      }
      const result = await request(
        `/snapshots/${encodeURIComponent(this.snapshot.id)}/adopt`,
        { method: 'POST', body: JSON.stringify({
            expected_story_revision: this.storyRevision,
            note: this.note || '',
          }) });
      this.message = result.reused
        ? `已在该故事包中（版本 ${result.revision}），本次只补齐索引`
        : `已采纳进故事包版本 ${result.revision}`;
    });
  }

  // ------------------------------------------------------------------- render
  render() {
    if (!this.firstChild) this.append(el('div', { class: 'wh-root' }));
    const root = this.firstChild;
    root.replaceChildren();
    root.append(this.renderHeader());
    if (this.error) {
      root.append(el('p', { class: 'wh-error', role: 'alert' }, this.error));
    }
    if (this.message) {
      root.append(el('p', { class: 'wh-message', role: 'status' }, this.message));
    }
    if (!this.draft) {
      root.append(this.renderStart());
      return;
    }
    root.append(this.renderFacts());
    root.append(this.renderCategories());
    root.append(this.renderPage());
    root.append(this.renderDecision());
  }

  renderHeader() {
    const title = this.draft
      ? `历史回放：第 ${this.draft.base_year} 年（分支 ${this.draft.branch || '未标注'}）`
      : '历史回放';
    return el('header', { class: 'wh-header' }, el('h2', {}, title));
  }

  renderStart() {
    const box = el('section', { class: 'wh-start' });
    box.append(el('p', { class: 'wh-hint' },
      '选一份已导入的世界与一个基准年，回放成作者侧草稿。回放不会改故事包、不会改会话。'));
    const imports = this.imports || [];
    if (!imports.length) {
      box.append(el('p', {}, '还没有导入过世界。先到地图页导入一份 .civsnap。'));
      return box;
    }
    const select = el('select', { class: 'wh-import',
      onchange: (event) => { this.importId = event.target.value; } });
    for (const item of imports) {
      const label = `${item.import_id} · 世界 ${item.world_id || '未记录'}`
        + ` · ${(item.parts || []).join('/') || '无分块'}`;
      select.append(el('option', { value: item.import_id,
                                   selected: item.import_id === this.importId ? 'selected' : null },
                       label));
    }
    if (!this.importId) this.importId = imports[0].import_id;
    const year = el('input', { type: 'number', step: 'any', class: 'wh-year-input',
                              placeholder: '基准年（可含小数）',
                              onchange: (event) => { this.yearInput = event.target.value; } });
    const branch = el('input', { type: 'text', class: 'wh-branch',
                                placeholder: '分支标签（可空，脚本不猜）',
                                onchange: (event) => { this.branchInput = event.target.value; } });
    box.append(el('label', { class: 'wh-field' }, '已导入世界', select),
               el('label', { class: 'wh-field' }, '基准年', year),
               el('label', { class: 'wh-field' }, '分支', branch),
               el('button', { type: 'button', class: 'wh-go',
                             onclick: () => this.startPreview() }, '回放这一年'));
    // The button is enabled only once a concrete import is chosen: a click with no
    // selection used to be a silent no-op, which looks like "linking worked".
    box.append(el('button', { type: 'button', class: 'wh-link-map',
                             disabled: this.importId ? null : 'disabled',
                             onclick: () => this.linkStartMap() }, '把这份导入关联为开局地图'));
    box.append(el('p', { class: 'wh-hint' },
      '关联地图是独立动作：回放/采纳历史都不会自己改地图。包里已有来自另一份导入的历史时'
      + '会被拒收，需先对这份地图重新回放。'));
    box.append(el('p', { class: 'wh-hint' },
      '只接受导入编号与年份：源文件、路径、URL 与客户端 civ 数据都不从浏览器接收。'));
    return box;
  }

  renderFacts() {
    const terrain = (this.draft.document && this.draft.document.terrain) || this.draft.terrain || {};
    const facts = el('dl', { class: 'wh-facts' });
    facts.append(el('dt', {}, '地形关联'),
                 el('dd', { class: terrain.state === 'unmatched' ? 'wh-warn' : '' },
                    terrain.note || terrain.state || '未记录'));
    facts.append(el('dt', {}, '草稿状态'), el('dd', {},
      `${this.draft.status}（版本 ${this.draft.revision}）`));
    const status = (this.draft.document && this.draft.document.field_status) || {};
    const unknown = Object.entries(status)
      .filter(([, row]) => (row && row.status) === 'unknown').map(([field]) => field);
    if (unknown.length) {
      facts.append(el('dt', {}, '没有据的字段'),
                   el('dd', { class: 'wh-warn' }, unknown.join('、')));
    }
    return facts;
  }

  renderCategories() {
    const bar = el('nav', { class: 'wh-tabs' });
    for (const [key, label] of CATEGORIES) {
      bar.append(el('button', {
        type: 'button',
        class: key === this.category ? 'wh-tab wh-tab-active' : 'wh-tab',
        onclick: () => { this.category = key; this.page = 0; this.slice = null; this.goPage(0); },
      }, label));
    }
    return bar;
  }

  renderPage() {
    const slice = this.slice;
    const list = el('ul', { class: 'wh-items' });
    if (!slice) {
      list.append(el('li', { class: 'wh-hint' }, '选一个类别后载入这一页。'));
      return el('section', {}, list);
    }
    if (!slice.items.length) {
      list.append(el('li', { class: 'wh-hint' }, '这一类在本次回放里没有条目。'));
    }
    for (const item of slice.items) {
      const picked = this.selected.has(item.ref);
      const row = el('li', { class: picked ? 'wh-item wh-item-picked' : 'wh-item' });
      // The readable identity comes first; the stable ref is the audit detail, not the
      // headline — a 60-character casnap hash is not what an author scans for.
      row.append(el('label', { class: 'wh-pick' },
        el('input', { type: 'checkbox', checked: picked ? 'checked' : null,
                      onchange: () => this.toggleSelect(item) }),
        el('span', { class: 'wh-label' },
          item.display_name || item.kind || item.role || '(无题名)')));
      if (item.year !== undefined) row.append(el('span', { class: 'wh-year' }, String(item.year)));
      const detail = el('details', { class: 'wh-refbox' },
        el('summary', {}, '稳定引用'));
      const refLine = el('code', { class: 'wh-ref', title: item.ref }, item.ref);
      refLine.style.overflowWrap = 'anywhere';
      detail.append(refLine);
      row.append(detail);
      if (picked) {
        const publicToggle = el('input', {
          type: 'checkbox',
          checked: this.publicRefs.has(item.ref) ? 'checked' : null,
          onchange: () => this.togglePublic(item.ref),
        });
        row.append(el('label', { class: 'wh-public' }, publicToggle, '对玩家公开'));
        row.append(el('input', {
          type: 'text', class: 'wh-summary', placeholder: '公开摘要（可留空）',
          value: (this.selected.get(item.ref) || {}).summary || '',
          onchange: (event) => this.setSummary(item.ref, event.target.value),
        }));
        row.append(el('input', {
          type: 'text', class: 'wh-link', placeholder: '关联本地地点 id（可留空）',
          value: this.links[item.ref] || '',
          onchange: (event) => this.setLink(item.ref, event.target.value),
        }));
      }
      list.append(row);
    }
    const nav = el('div', { class: 'wh-pager' },
      el('button', { type: 'button', disabled: slice.page <= 0 ? 'disabled' : null,
                     onclick: () => this.goPage(slice.page - 1) }, '上一页'),
      el('span', {}, `第 ${slice.page + 1} / ${slice.pages} 页 · 共 ${slice.total} 条`),
      el('button', { type: 'button', disabled: slice.page + 1 >= slice.pages ? 'disabled' : null,
                     onclick: () => this.goPage(slice.page + 1) }, '下一页'));
    if (slice.truncated_by_page) {
      nav.append(el('p', { class: 'wh-hint' },
        '这一类超过一页，逐页选；总数是精确的，没有静默截断。'));
    }
    return el('section', {}, list, nav);
  }

  renderDecision() {
    const box = el('section', { class: 'wh-decision' });
    box.append(el('h3', {}, '作者决定'),
               el('p', { class: 'wh-hint' },
                  `已选 ${this.selected.size} 条，其中对玩家公开 ${this.publicRefs.size} 条。`
                  + '未公开的条目不会进玩家侧；摘要在审阅后可以改，但要重新固定快照。'));
    const reviewed = this.draft.status === 'reviewed';
    box.append(el('div', { class: 'wh-actions' },
      el('button', { type: 'button', disabled: this.selected.size ? null : 'disabled',
                     onclick: () => this.review() }, '1 · 审阅'),
      el('button', { type: 'button',
                     disabled: (!reviewed || this.snapshot) ? 'disabled' : null,
                     onclick: () => this.commit() }, '2 · 固定成快照')));
    if (this.snapshot) {
      box.append(el('p', {}, `快照 ${this.snapshot.id} · 第 ${this.snapshot.base_year} 年`));
      box.append(el('input', { type: 'text', class: 'wh-note',
                               placeholder: '采纳备注（可留空）',
                               onchange: (event) => { this.note = event.target.value; } }));
      box.append(el('button', { type: 'button', onclick: () => this.adopt() },
        '3 · 采纳进当前故事包'));
      box.append(el('p', { class: 'wh-hint' },
        '采纳会新建一个故事包版本，地图来源与已经跑着的旅程都不改。'));
    }
    return box;
  }
}

if (!customElements.get('world-history-panel')) {
  customElements.define('world-history-panel', WorldHistoryPanel);
}

// Classic script (loaded with `defer`, like the other author pages): no ES module export,
// so `index.html` can include it without changing any existing script into a module.
})();
