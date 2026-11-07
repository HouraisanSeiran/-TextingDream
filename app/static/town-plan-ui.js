/* Live authoring preview; only same-origin scripts, compatible with script-src 'self'. */
(function () {
  'use strict';
  const card = el('section', undefined, 'card town-plan');
  card.setAttribute('aria-label', '城镇地图生成');
  card.innerHTML = `<h3>城镇地图</h3>
<p class="muted">从当前草稿或已发布版本生成，复用现有建筑、道路、城防与资源点素材。选择设施可定位；滚动查看放大后的地图。</p>
<div class="toolbar">
<label>建筑风格<select id="town-plan-style"><option value="auto">按屋面自动选择</option><option value="west">西式</option><option value="east">东方</option><option value="arab">阿拉伯</option></select></label>
<label>种族素材<select id="town-plan-race"><option value="common">通用 / 人族</option><option value="elf">精灵</option><option value="dwarf">矮人</option><option value="orc">兽人</option></select></label>
<label>墙形<select id="town-plan-shape"><option value="irregular">不规则</option><option value="square">方形</option></select></label>
<label>工事<select id="town-plan-fort"><option value="auto">按聚落自动选择</option><option value="none">无附加工事</option><option value="light">轻型</option><option value="normal">中型</option><option value="heavy">重型</option></select></label>
<label>地标<select id="town-plan-landmarks"><option value="">自动</option><option value="0">无</option><option value="1">1 处</option><option value="2">2 处</option></select></label>
<label>布局种子<input id="town-plan-seed" maxlength="64" placeholder="留空沿用城镇种子"></label>
<button id="town-plan-generate" disabled>生成 / 刷新布局</button>
<button id="town-plan-export" disabled>导出地图 JSON</button>
<label>显示大小<select id="town-plan-zoom"><option value="100">适应宽度</option><option value="150">150%</option><option value="200">200%</option></select></label>
</div>
<p id="town-plan-status" role="status" aria-live="polite">选择或新建一份城镇草稿后查看地图。</p>
<div id="town-plan-viewport" class="town-plan-viewport"><div id="town-plan-scene"></div></div>
<p id="town-plan-info" class="muted"></p>
<details id="town-plan-issues"><summary>布局提示</summary><ul id="town-plan-diagnostics"></ul></details>
<details><summary>设施放置清单</summary><div id="town-plan-facilities" class="town-plan-facilities"></div></details>
<details id="town-plan-sites"><summary>周边资源点</summary><p class="muted">仅显示已勘探且满足技术、燃料条件的本地资源；每张为独立地块示意。</p>
<label>资源点<select id="town-plan-site"></select></label><p id="town-plan-site-info" class="muted"></p><div id="town-plan-site-scene"></div></details>`;
  townPanel.querySelector('.two-col').before(card);
  const css = document.createElement('link');
  css.rel = 'stylesheet'; css.href = '/static/town-plan.css'; document.head.append(css);
  let source = null, generation = 0, result = null, assets = null;
  const kinds = {draft:'草稿',version:'已发布版本'};
  const styles = {west:'西式',east:'东方',arab:'阿拉伯'};
  const races = {common:'通用 / 人族',elf:'精灵',dwarf:'矮人',orc:'兽人'};
  function script(src) {
    return new Promise((resolve, reject) => {
      const node = document.createElement('script'); node.src = src;
      node.onload = resolve;
      node.onerror = () => { node.remove(); reject(Error('城镇素材加载失败：'+src)); };
      document.head.append(node);
    });
  }
  function loadAssets() {
    if (!assets) assets = Promise.all([
      window.TOWN_CATALOG ? Promise.resolve() : script('/static/map-art/town/town-catalog.js'),
      window.TownRender ? Promise.resolve() : script('/static/town-render.js')
    ]).catch(error => {assets=null; throw error;});
    return assets;
  }
  function clear() {
    result = null;
    ['scene','facilities','diagnostics','site','site-scene'].forEach(id => $('town-plan-'+id).replaceChildren());
    ['info','site-info'].forEach(id => $('town-plan-'+id).textContent='');
    $('town-plan-export').disabled = true;
    $('town-plan-issues').open = false;
    $('town-plan-sites').hidden = true;
  }
  function options() {
    return {style:$('town-plan-style').value,race:$('town-plan-race').value,
      wall_shape:$('town-plan-shape').value,fortification:$('town-plan-fort').value,
      seed:$('town-plan-seed').value.trim()||null,
      landmarks:$('town-plan-landmarks').value===''?null:Number($('town-plan-landmarks').value)};
  }
  function focusFacility(row) {
    const svg = $('town-plan-scene').querySelector('svg');
    svg.querySelector('[data-town-highlight]')?.remove();
    if (!row.cell) return;
    const cell = result.layout.grid.cell, rect = document.createElementNS('http://www.w3.org/2000/svg','rect');
    const [x,y] = row.cell, [w,h] = row.footprint;
    for (const [key,value] of Object.entries({x:x*cell,y:y*cell,width:w*cell,height:h*cell,
      fill:'#ffd76d',stroke:'#9b3900','stroke-width':3,'fill-opacity':.22,'data-town-highlight':row.source})) rect.setAttribute(key,value);
    svg.append(rect);
    rect.scrollIntoView({block:'nearest',inline:'nearest'});
    $('town-plan-status').textContent = row.name+' · '+row.art_id;
  }
  function drawSite() {
    const site = result?.resource_sites[Number($('town-plan-site').value)];
    if (!site) return;
    TownRender.render($('town-plan-site-scene'),site.layout,TOWN_CATALOG);
    $('town-plan-site-info').textContent = site.name+' · '+styles[site.layout.style]+
      (site.diagnostics.length?' · '+site.diagnostics.map(d=>d.message).join('；'):'');
  }
  async function generate() {
    if (!source) return;
    const current = ++generation, selected = {...source}, requested = options();
    clear(); $('town-plan-status').textContent='正在生成 '+kinds[selected.kind]+' 的实际布局…';
    $('town-plan-generate').disabled=true;
    try {
      const [data] = await Promise.all([
        api('/inner/'+(selected.kind==='draft'?'towns/':'town-versions/')+encodeURIComponent(selected.id)+'/layout','POST',requested),
        loadAssets()
      ]);
      if (current !== generation) return;
      result=data;
      TownRender.render($('town-plan-scene'),data.layout,TOWN_CATALOG);
      const s=data.summary, g=data.layout.grid;
      $('town-plan-status').textContent=`${data.name} · ${kinds[selected.kind]} · ${styles[data.resolved.style]} / ${races[data.resolved.race]} · ${g.w}×${g.h} 格 · 设施 ${s.placed}/${s.facilities} · 示意民居 ${s.houses} · 资源点 ${s.resource_sites}`;
      $('town-plan-info').textContent=`${data.note} 规则住房数：${s.reference_houses} 户。布局种子：${data.resolved.seed}。`;
      const names = Object.fromEntries(data.facilities.map(row=>[row.source,row.name]));
      for (const d of data.diagnostics) $('town-plan-diagnostics').append(el('li',
        [names[d.source||d.for_source],d.message,d.note,d.id].filter(Boolean).join(' · ')));
      if (!data.diagnostics.length) $('town-plan-diagnostics').append(el('li','设施与素材检查未发现缺项。'));
      $('town-plan-issues').open=data.diagnostics.length>0;
      for (const row of data.facilities) {
        const line=el('p'), b=button(row.name,()=>focusFacility(row));
        b.disabled=row.status!=='placed'||!row.cell;
        line.append(b,el('span',row.status==='placed'?'已放置 · '+row.art_id:'未放置 · '+
          (data.diagnostics.find(d=>d.source===row.source)?.message||row.reason)));
        $('town-plan-facilities').append(line);
      }
      $('town-plan-site').replaceChildren(...data.resource_sites.map((site,i)=>new Option(site.name,i)));
      $('town-plan-sites').hidden=!data.resource_sites.length;
      drawSite(); $('town-plan-export').disabled=false;
    } catch(error) {
      if (current === generation) {clear(); $('town-plan-status').textContent='布局未生成：'+error.message;}
    } finally {
      if (current === generation) $('town-plan-generate').disabled=!source;
    }
  }
  function select(kind,id,ready=true) {
    generation++; clear(); source=ready?{kind,id}:null;
    $('town-plan-generate').disabled=!source;
    if (source) generate();
    else $('town-plan-status').textContent='草稿存在失效或未完成阶段，请先重新生成阶段，再查看地图。';
  }
  window.addEventListener('td-town-selected',event=>select('draft',event.detail.id,event.detail.ready));
  window.TownPlanUI={showVersion(id){select('version',id);card.scrollIntoView({block:'start'});}};
  $('town-plan-generate').onclick=generate;
  ['style','race','shape','fort','landmarks'].forEach(id=>$('town-plan-'+id).onchange=generate);
  $('town-plan-seed').onchange=generate;
  $('town-plan-site').onchange=drawSite;
  $('town-plan-export').onclick=()=>{if(result)jsonDownload(result,'town-map-'+result.town_id+'.json');};
  $('town-plan-zoom').onchange=()=>{$('town-plan-scene').style.width=$('town-plan-zoom').value+'%';};
})();
