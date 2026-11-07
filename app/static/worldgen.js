/* Author-only world generation page: parameters -> background job (skeleton -> fast layer -> optional TD on GPU -> atlas) -> preview.
 * API: /api/inner/worldgen/* (token header via api()). Previews are fetched with the token and shown as blob: URLs. */
(function () {
  'use strict';
  const STATUS = {queued: '排队中', running: '运行中', succeeded: '已完成', failed: '失败', cancelled: '已取消', interrupted: '已中断', pending: '等待', skipped: '未运行'};
  const BASIS = {measured: '实测', extrapolated: '推算'};
  const pageNode = el('section', undefined, 'page worldgen');
  pageNode.id = 'worldgen'; pageNode.hidden = true;
  pageNode.append(el('h2', '世界生成'),
    el('p', '调参数后在后台依次生成：板块骨架（造山带）→ 快速世界层 2 km（CPU，不规则网格汇流，无 D8）→（勾选显卡时）TD 粗模型山脉走向与对比 → 成图。产物写入新的 web-<任务号> 目录，不覆盖已有产物。', 'muted'));

  const form = el('form', undefined, 'card worldgen-form');
  const typeSel = el('select'), sizeSel = el('select');
  const ocean = el('input'), oceanOut = el('output');
  const mount = el('input'), mountOut = el('output');
  const seed = el('input');
  const gpu = el('input'), gpuNote = el('p', '正在检测显卡…', 'muted worldgen-gpu-note');
  ocean.type = 'range'; ocean.step = '0.01';
  mount.type = 'range'; mount.step = '0.01';
  seed.type = 'number'; seed.min = '0'; seed.step = '1'; seed.required = true;
  gpu.type = 'checkbox'; gpu.disabled = true;
  function field(label, ...nodes) { const l = el('label', label); l.append(...nodes); return l; }
  const gpuLabel = el('label', undefined, 'worldgen-check'); gpuLabel.append(gpu, document.createTextNode(' 使用显卡（只用于 TD 粗模型山脉走向验证 / 对比）'));
  const estimateBox = el('div', undefined, 'worldgen-estimate');
  const submit = el('button', '开始生成', 'primary'); submit.type = 'submit';
  const refreshGpu = button('重新检测显卡', () => loadOptions(true)); refreshGpu.type = 'button';
  form.append(field('世界类型', typeSel), field('世界大小', sizeSel), field('海洋比例 ', oceanOut, ocean),
    field('山地覆盖（占陆地） ', mountOut, mount), field('种子', seed), gpuLabel, gpuNote, refreshGpu, estimateBox, submit);

  const jobBox = el('div', undefined, 'card worldgen-job'); jobBox.hidden = true;
  const historyBox = el('div', undefined, 'worldgen-history');
  pageNode.append(form, jobBox, el('h3', '最近的任务'), historyBox);
  document.querySelector('main').append(pageNode);

  const anchor = $('workspace-ai-drafts') || $('workspace-npc-cards') || $('workspace-elements');
  const nav = button('世界生成', () => TDNav.show('worldgen'), 'workspace-link');
  nav.id = 'workspace-worldgen';
  if (anchor) anchor.after(nav);
  const legacy = document.querySelector('#legacy nav');
  if (legacy) { const b = button('世界生成', () => TDNav.show('worldgen')); b.dataset.page = 'worldgen'; legacy.append(b); }

  let opts = null, timer = null, shownJob = null, blobs = [];

  const pct = v => (v === null || v === undefined) ? '—' : (100 * v).toFixed(1) + '%';
  const num = (v, d = 1) => (v === null || v === undefined) ? '—' : Number(v).toFixed(d);
  function dur(s) {
    if (s === null || s === undefined) return '—';
    s = Math.round(s);
    if (s < 120) return s + ' 秒';
    if (s < 7200) return (s / 60).toFixed(s < 600 ? 1 : 0) + ' 分钟';
    return (s / 3600).toFixed(1) + ' 小时';
  }
  const range = a => (Math.abs(a[0] - a[1]) < 1) ? dur(a[0]) : dur(a[0]) + ' – ' + dur(a[1]);

  function fill(o) {
    opts = o;
    if (!typeSel.options.length) {
      for (const t of o.world_types) { const x = el('option', t.label); x.value = t.id; typeSel.append(x); }
      for (const s of o.sizes) { const x = el('option', s.label); x.value = String(s.km); sizeSel.append(x); }
      const d = o.defaults;
      typeSel.value = d.world_type; sizeSel.value = String(d.size_km);
      ocean.min = o.ranges.ocean_fraction[0]; ocean.max = o.ranges.ocean_fraction[1]; ocean.value = d.ocean_fraction;
      mount.min = o.ranges.mountain_area[0]; mount.max = o.ranges.mountain_area[1]; mount.value = d.mountain_area;
      seed.value = d.seed;
    }
    const g = o.gpu;
    gpu.disabled = !g.usable;
    if (!g.usable) gpu.checked = false;
    gpuLabel.classList.toggle('disabled', !g.usable);
    const info = g.info || {};
    gpuNote.textContent = g.usable
      ? `检测到 ${info.name || 'CUDA 显卡'}：空闲 ${info.cuda_free_mib} / ${info.cuda_total_mib} MiB（需要 ≥ ${g.min_free_mib} MiB）。${g.used_for}。检测于 ${g.checked_at}`
      : `不能使用显卡：${g.reason}。检测于 ${g.checked_at}`;
    renderEstimate();
  }

  function renderEstimate() {
    if (!opts) return;
    oceanOut.textContent = pct(Number(ocean.value)); mountOut.textContent = pct(Number(mount.value));
    const size = sizeSel.value, e = opts.estimates[size][gpu.checked ? 'gpu' : 'cpu'];
    const rows = e.stages.map(s => { const r = el('tr');
      r.append(el('td', s.label), el('td', range(s.seconds)), el('td', s.peak_mb ? Math.round(s.peak_mb) + ' MB' : ''), el('td', BASIS[s.basis] || s.basis, s.basis === 'measured' ? 'ok' : 'warn'));
      return r; });
    const t = el('table'); const head = el('tr');
    head.append(el('th', '阶段'), el('th', '预计耗时'), el('th', '内存峰值'), el('th', '依据'));
    t.append(head, ...rows);
    const avail = opts.memory.available_bytes, need = opts.memory.min_free_bytes[size];
    const memLine = el('p', `合计约 ${range(e.total_seconds)}；内存峰值约 ${Math.round(e.peak_mb)} MB。启动门槛：可用内存 ≥ ${(need / 2 ** 30).toFixed(1)} GiB，当前可用 ${avail ? (avail / 2 ** 30).toFixed(2) + ' GiB' : '未知'}。`,
      avail !== null && avail < need ? 'warn' : 'muted');
    const extra = [];
    if (size === '10000') extra.push(el('p', '万公里世界需要显卡且很慢：骨架与快速层的时间、内存都是从 1600 / 5000 km 实测推算的，可能超出本机内存。', 'warn'));
    if (!gpu.checked && opts.estimates[size].gpu) {
      const td = opts.estimates[size].gpu.stages.find(s => s.stage === 'td');
      if (td) extra.push(el('p', `勾选显卡会多跑一步 TD 粗模型（推算 ${range(td.seconds)}，约 ${td.tiles[0] === td.tiles[1] ? td.tiles[0] : td.tiles.join('–')} 块，跳过离陆地 ${opts.td.skip_ocean_km} km 外深海、${opts.td.steps} 步）。`, 'muted'));
    }
    estimateBox.replaceChildren(el('h3', '提交前估算'), t, memLine, ...extra,
      el('p', '“实测”来自本机已跑过的同尺寸任务；“推算”按块数 × 每块耗时或尺寸外推，未在本机实测。', 'muted'));
  }
  for (const x of [ocean, mount, sizeSel, gpu, typeSel]) x.addEventListener('input', renderEstimate);

  async function loadOptions(refresh) {
    fill(await api('/inner/worldgen/options' + (refresh ? '?refresh_gpu=1' : '')));
    if (opts.active_job) watch(opts.active_job);
    await loadHistory();
  }

  async function loadHistory() {
    const jobs = await api('/inner/worldgen/jobs');
    historyBox.replaceChildren(...(jobs.length ? jobs.slice(0, 12).map(j => {
      const p = j.params;
      return button(`${j.id} · ${STATUS[j.status] || j.status} · ${p.size_km} km ${p.world_type}${p.use_gpu ? ' · 显卡' : ''}${j.seconds_total ? ' · ' + dur(j.seconds_total) : ''}`, () => watch(j.id), 'worldgen-history-item');
    }) : [el('p', '还没有生成任务。', 'muted')]));
  }

  form.addEventListener('submit', ev => {
    ev.preventDefault();
    safe(async () => {
      const body = {world_type: typeSel.value, size_km: Number(sizeSel.value), ocean_fraction: Number(ocean.value),
        mountain_area: Number(mount.value), seed: Number(seed.value), use_gpu: gpu.checked};
      if (!Number.isSafeInteger(body.seed) || body.seed < 0) throw Error('种子必须是非负整数');
      submit.disabled = true;
      try { const j = await api('/inner/worldgen/jobs', 'POST', body); notice('已开始生成：' + j.id); watch(j.id); await loadHistory(); }
      finally { submit.disabled = false; }
    });
  });

  function watch(id) {
    clearTimeout(timer);
    const tick = () => safe(async () => {
      const j = await api('/inner/worldgen/jobs/' + encodeURIComponent(id));
      await renderJob(j);
      if (!['succeeded', 'failed', 'cancelled', 'interrupted'].includes(j.status) && page === 'worldgen') timer = setTimeout(tick, 2000);
      else if (shownJob === id) loadHistory();
    });
    tick();
  }

  async function previewImg(id, name, alt) {
    const r = await fetch(`/api/inner/worldgen/jobs/${encodeURIComponent(id)}/preview/${name}`, {headers: {'X-TextileDream-Token': token}});
    if (!r.ok) return el('p', alt + '：读取失败', 'warn');
    const url = URL.createObjectURL(await r.blob()); blobs.push(url);
    const fig = el('figure'), img = el('img'); img.src = url; img.alt = alt; img.loading = 'lazy';
    const a = el('a'); a.href = url; a.target = '_blank'; a.append(img);
    fig.append(a, el('figcaption', alt)); return fig;
  }

  function kv(pairs) {
    const dl = el('dl', undefined, 'worldgen-kv');
    for (const [k, v] of pairs) dl.append(el('dt', k), el('dd', v === null || v === undefined || v === '' ? '—' : String(v)));
    return dl;
  }

  async function renderJob(j) {
    const fresh = shownJob !== j.id || jobBox.dataset.status !== j.status;
    shownJob = j.id; jobBox.hidden = false;
    const done = ['succeeded', 'failed', 'cancelled', 'interrupted'].includes(j.status);
    const p = j.params;
    const head = el('div', undefined, 'toolbar');
    head.append(el('strong', `任务 ${j.id}`), el('span', STATUS[j.status] || j.status, 'worldgen-status ' + j.status),
      el('span', `${p.size_km} km · ${p.world_type} · 海洋 ${pct(p.ocean_fraction)} · 山地 ${pct(p.mountain_area)} · 种子 ${p.seed}${p.use_gpu ? ' · 显卡' : ''}`, 'muted'));
    if (!done) head.append(button('取消任务', async () => { await api(`/inner/worldgen/jobs/${encodeURIComponent(j.id)}/cancel`, 'POST'); notice('已请求取消'); }));
    const stages = el('ol', undefined, 'worldgen-stages');
    for (const s of j.stages || []) {
      const mon = s.gpu_monitor ? ` · 显存峰值 ${s.gpu_monitor.peak_mib} MiB（整卡）` : '';
      stages.append(el('li', `${s.label}：${STATUS[s.status] || s.status}${s.seconds !== undefined ? ' · ' + dur(s.seconds) : ''}${mon}${s.error ? ' · ' + s.error : ''}`, s.status));
    }
    const log = el('pre', (j.log_tail || []).join('\n'), 'worldgen-log');
    const parts = [head, stages];
    if (j.error) parts.push(el('p', j.error, 'warn'));
    if (!fresh && done) return;              // finished job already rendered with previews
    jobBox.dataset.status = j.status;
    if (j.result) parts.push(...resultView(j));
    parts.push(el('h4', '日志尾部'), log);
    if (done && j.previews && j.previews.length) {
      for (const u of blobs) URL.revokeObjectURL(u); blobs = [];
      const names = {overview: '总览图', relief: '纯地形图', td: 'TD 粗模型走向'};
      const figs = el('div', undefined, 'worldgen-previews');
      for (const n of j.previews) figs.append(await previewImg(j.id, n, names[n] || n));
      parts.splice(2, 0, figs);
    }
    jobBox.replaceChildren(...parts);
  }

  function resultView(j) {
    const r = j.result, sk = r.skeleton || {}, f = r.fast || {}, ms = f.map_source || {}, out = [el('h4', '产品与关键数字')];
    out.push(kv([
      ['快速层产品身份', f.identity], ['算法', f.algorithm_version + ' · ' + (f.routing || '')],
      ['map_source 读取', ms.kind ? `${ms.kind} / ${ms.schema}，身份${ms.identity_matches ? '一致' : '不一致'}，${(ms.shape_zx || []).join('×')} 格 × ${ms.spacing_m} m` : '—'],
      ['骨架', `${sk.algorithm || ''} · ${sk.identity ? sk.identity.slice(0, 16) + '…' : ''}`],
      ['实际海洋比例', `${pct(f.ocean_fraction)}（骨架 ${pct(sk.ocean_fraction)}，目标 ${pct(sk.ocean_target)}）`],
      ['山地占陆地', `${pct(sk.mountain_area_land_fraction)}（目标 ${pct(sk.mountain_area_target)}，区间 ${(sk.mountain_area_band || []).map(pct).join('–')}${sk.mountain_area_within_band ? '，达标' : sk.mountain_area_within_band === false ? '，未达标' : ''}）`],
      ['>1500 m 高山占陆地', pct(f.high_mountain_land_fraction_gt1500m)],
      ['最高海拔', num(f.max_elevation_m, 0) + ' m'], ['河段 / 湖泊', `${f.river_segments ?? '—'} / ${f.kept_lakes ?? '—'}`],
      ['快速层耗时 / 内存峰值', `${dur(f.seconds)} / ${num(f.peak_working_set_mb, 0)} MB`],
      ['总耗时', dur(j.seconds_total)], ['产物目录', `${j.paths_relative.world_dir} ； ${j.paths_relative.fast_dir}`]]));
    if (r.td) {
      const t = r.td, c = t.compare_with_fast || {};
      out.push(el('h4', 'TD 粗模型（显卡）'), kv([
        ['设备', `${t.device}${t.device_name ? ' · ' + t.device_name : ''}`], ['身份', t.identity],
        ['块数', `${t.tiles} 计算 / ${t.tiles_total} 总计（跳过 ${t.tiles_skipped}）`],
        ['耗时', `模型加载 ${dur(t.model_load_seconds)}，生成 ${dur(t.generate_seconds)}（${num(t.seconds_per_tile, 2)} 秒/块）`],
        ['显存峰值', `torch 分配 ${num(t.torch_cuda_max_allocated_mib, 0)} MiB / 保留 ${num(t.torch_cuda_max_reserved_mib, 0)} MiB；整卡 ${t.nvidia_smi ? t.nvidia_smi.peak_mib + ' MiB（起始 ' + t.nvidia_smi.baseline_mib + '）' : '—'}`],
        ['与快速层对比', c.cells_compared ? `山地 IoU ${num(c.mountain_iou, 3)}，海陆一致 ${pct(c.land_agreement)}，主脊方向偏差中位数 ${num(c.ridge_axis_deviation_deg_median, 1)}°（20° 内 ${pct(c.within_20deg)}，随机期望 45°）` : '—']]));
    }
    return out;
  }

  TDNav.register('worldgen', {title: '世界生成', enter: () => safe(() => loadOptions(false))});

  // Deep link: /#worldgen or /#worldgen=<job id> opens this page (and that job) once bootstrap has the token.
  const deep = /^#worldgen(?:=([0-9a-f-]{20}))?$/.exec(location.hash);
  if (deep) {
    let tries = 0;
    const open = () => {
      if (!token) { if (++tries < 100) setTimeout(open, 100); return; }
      safe(async () => { await TDNav.show('worldgen'); if (deep[1]) watch(deep[1]); });
    };
    window.addEventListener('DOMContentLoaded', () => setTimeout(open, 0));
  }
})();
