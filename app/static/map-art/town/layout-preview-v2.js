/* layout-preview-v2: unpacks TOWN_LAYOUT_SAMPLES_V2 and draws it with TownRender. */
(function () {
  'use strict';
  const DATA = window.TOWN_LAYOUT_SAMPLES_V2, CAT = window.TOWN_CATALOG;
  const $ = id => document.getElementById(id);
  const RACE_ZH = { common: '人族', elf: '精灵', dwarf: '矮人', orc: '兽人' };
  const FORT_ZH = { none: '无', light: '轻', normal: '中', heavy: '重' };
  function unpack(packed) {
    const out = Object.assign({}, packed);
    ['underlay', 'ground', 'items'].forEach(layer => {
      out[layer] = (packed[layer] || []).map(r => {
        const id = DATA.ids[r[0]];
        const it = { id: id, x: r[1], bottom: r[2], key: r.length > 3 ? r[3] : r[2] };
        if (layer === 'underlay' && /-water-/.test(id)) it.layer = 'water';
        return it;
      });
    });
    return out;
  }
  function fill(sel, pairs) {
    sel.replaceChildren(...pairs.map(([v, t]) => Object.assign(document.createElement('option'), { value: v, textContent: t })));
  }
  const samples = [];
  DATA.towns.forEach(t => { if (!samples.some(s => s[0] === t.sample)) samples.push([t.sample, t.name]); });
  fill($('sample'), samples);
  fill($('seed'), [...new Set(DATA.towns.map(t => t.seed))].map(s => [s, String(s)]));
  function count(list, key) {
    const c = {};
    (list || []).forEach(x => { c[x[key]] = (c[x[key]] || 0) + 1; });
    return Object.entries(c).map(([k, v]) => k + '×' + v).join('、') || '无';
  }
  function drawTown() {
    const style = $('style').value;
    $('race').disabled = style !== 'west';
    const race = style === 'west' ? $('race').value : 'common';
    const pick = DATA.towns.find(t => t.sample === $('sample').value && t.style === style &&
      t.race === race && t.shape === $('shape').value && String(t.seed) === $('seed').value);
    if (!pick) { $('scene').textContent = '没有这个组合的样例'; return; }
    const lay = unpack(pick.layout);
    TownRender.render($('scene'), lay, CAT);
    const facs = lay.buildings.filter(b => b.facility).length;
    $('stats').innerHTML = [
      ['网格', lay.grid.w + '×' + lay.grid.h], ['种族', RACE_ZH[lay.race]],
      ['工事等级', FORT_ZH[lay.fortification]], ['城门', lay.grid.gates.length],
      ['设施', facs], ['民居', lay.buildings.length - facs], ['摆件', (lay.props || []).length],
      ['工事', count(lay.forts.filter(f => f.kind !== 'node_tower'), 'kind')],
      ['地标', (lay.landmarks || []).map(l => l.id.replace(/^\w+-\w+-/, '')).join('、') || '无'],
      ['水面', lay.terrain.water_kind || '无']
    ].map(([k, v]) => '<span>' + k + ' <b>' + v + '</b></span>').join('');
    $('missing').replaceChildren(...lay.missing.map(m => {
      const li = document.createElement('li');
      li.textContent = [m.reason, m.facility, m.id, m.note].filter(Boolean).join(' · ');
      return li;
    }));
  }
  function drawSite() {
    const style = $('site-style').value;
    const list = DATA.sites.filter(s => s.style === style);
    if ($('site').dataset.style !== style) {
      fill($('site'), list.map((s, i) => [i, s.resource + (s.subtype ? ' / ' + s.subtype : '')]));
      $('site').dataset.style = style;
    }
    const s = list[+$('site').value || 0];
    if (!s) return;
    const lay = unpack(s.layout);
    TownRender.render($('site-scene'), lay, CAT);
    const econ = (lay.buildings[0] || {}).economy;
    $('site-info').textContent = s.main + (econ ? ' · 经营档案 ' + econ : '') +
      (lay.missing.length ? ' · ' + lay.missing.map(m => m.reason).join('、') : '');
  }
  ['sample', 'style', 'race', 'shape', 'seed'].forEach(id => $(id).addEventListener('change', drawTown));
  ['site-style', 'site'].forEach(id => $(id).addEventListener('change', drawSite));
  const q = new URLSearchParams(location.search);
  ['sample', 'style', 'race', 'shape', 'seed', 'site-style'].forEach(id => { if (q.get(id)) $(id).value = q.get(id); });
  drawTown();
  drawSite();
  if (q.get('site')) { $('site').value = q.get('site'); drawSite(); }
})();
