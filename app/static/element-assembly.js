'use strict';
// 元素装配页。所有值都用 textContent（el()）写入，作者文本不会变成标记。
// 页面只和 /api/inner/elements/* 通信：不传文件路径，也不相信浏览器提交的 payload——
// 服务端按选中的 namespace/element_id/version 自己从只读库里读。
const elementPanel=el('section',undefined,'page');elementPanel.id='elements';elementPanel.hidden=true;
elementPanel.innerHTML=`<div class="ea-hero"><div class="ea-hero-text"><span class="ea-kicker">ELEMENT CODEX · 元素典籍</span><h2>元素数据库</h2><p>从本地候选库挑条目、固定版本，组成这个世界的元素清单。清单在开局前锁定，旅程只读故事包里的快照。库里都是待审候选，采纳不会把它们标成已核实。</p></div><div id="ea-library" class="ea-library muted">读取中…</div></div>
<div class="ea-catbar"><div id="ea-world" class="ea-world" role="group" aria-label="世界观"></div><div id="ea-cats" class="ea-cats" role="navigation" aria-label="按分组浏览"></div></div>
<div class="ea-layout"><div class="ea-main">
<form id="ea-search" class="ea-searchbar" role="search">
<input id="ea-text" maxlength="200" placeholder="名称或别名，例如 小麦、steel" aria-label="名称或别名">
<input id="ea-tag" maxlength="200" placeholder="标签，逗号分隔：cereal, metal" aria-label="标签（任一命中）">
<select id="ea-namespace" aria-label="命名空间"><option value="">全部分组</option></select>
<button class="primary" type="submit">搜索</button></form>
<div class="ea-pager"><span id="ea-page" class="muted"></span><span class="ea-pager-buttons"><button id="ea-prev" type="button">‹ 上一页</button><button id="ea-next" type="button">下一页 ›</button></span></div>
<div id="ea-results" class="ea-results"></div>
</div><aside class="ea-side">
<div class="card ea-detail-card"><h3 id="ea-detail-title">条目详情</h3><div id="ea-detail" class="muted">点一条结果的「查看详情」，在这里看完整内容与固定来源版本。</div></div>
<div class="card ea-basket"><h3>选择清单 <small id="ea-count"></small></h3><div id="ea-selected"></div>
<div class="toolbar"><button id="ea-save">保存草稿</button><button id="ea-preview">校验并试算</button><button id="ea-commit" class="primary">锁定到故事包</button></div>
<p id="ea-status" class="muted" role="status"></p><div id="ea-warnings"></div></div>
<details class="card ea-fold"><summary>显式 typed 规则</summary>
<div class="toolbar"><select id="ea-rule-kind"><option value="requires">依赖 requires</option><option value="conflicts">互斥 conflicts</option></select><select id="ea-rule-from"></select><input id="ea-rule-to" maxlength="120" placeholder="namespace/element_id"><button id="ea-rule-add" type="button">添加</button></div>
<div id="ea-rules"></div>
<p class="muted">只有这里列出的规则会被机器校验（缺引用、环、互斥都会报错）。条目里的 requires / excludes 是自然语言条件，本版本不当依赖，只在警告里逐条标出。</p></details>
<details class="card ea-fold"><summary>故事包清单与草稿</summary>
<div class="toolbar"><button id="ea-manifest">读取作者视图</button><button id="ea-drafts-refresh">刷新草稿列表</button><button id="ea-recover">恢复中断的提交</button></div>
<div id="ea-drafts" class="ea-drafts"></div><div id="ea-manifest-box"></div></details>
</aside></div>
<div id="ea-sheet-backdrop" class="ea-sheet-backdrop"></div>
<form id="ea-add" class="ea-sheet" aria-label="加入清单"><div class="ea-sheet-head"><h3>加入清单</h3><button id="ea-sheet-close" type="button" class="ea-sheet-close" aria-label="关闭">×</button></div>
<p id="ea-target" class="ea-target">先在结果里点「加入清单」。</p>
<label>固定版本<input id="ea-version" type="number" min="1" value="1"></label>
<label>状态<select id="ea-state"></select></label>
<label>公开说明（作者定稿，玩家可见）<textarea id="ea-public" rows="3" maxlength="600" placeholder="用一两句话写这个元素在本世界的样子"></textarea></label>
<div id="ea-fields"></div>
<label>限定地点<select id="ea-location"><option value="">不限地点</option></select></label>
<label>解锁标记 reveal_flag<input id="ea-flag" maxlength="60" placeholder="例如 met_guild"></label>
<div id="ea-known"></div>
<label class="inline"><input id="ea-reveal-potential" type="checkbox"> 潜在元素也允许透露其存在</label>
<label class="inline ea-ack"><input id="ea-ack" type="checkbox"> 我已确认这是待审候选资料（采纳不改变审核状态）</label>
<div class="toolbar ea-sheet-actions"><button id="ea-cancel-edit" type="button">取消</button><button class="primary" type="submit">加入清单</button></div>
<p class="muted ea-fine">服务端会用仓库里的原始 payload 重新组装，浏览器提交的内容不被当作事实来源。</p></form>`;
document.querySelector('main').append(elementPanel);

// ---------- 典籍外观：分组徽记、中文标签（只影响显示，不改任何请求） ----------
const EA_NS_LABEL={'animal-foods':'动物食材','character-attributes':'人物属性','character-traits':'性格特质','craft-supplement':'工艺补遗',
 'cuisine':'菜系','cuisine-british':'英式菜','cuisine-french':'法式菜','culture-literature':'文学','eastern':'玄幻设定','eastern-alchemy':'东方炼丹',
 'eastern-biology':'东方生物','fantasy-races':'奇幻种族','flavors':'风味','food-supplement':'食物补遗','materials':'材料','names-asian':'亚洲人名',
 'names-european':'欧洲人名','produce':'蔬果作物','reality-formulae':'方剂','reality-herbs-aerial':'草药·地上部','reality-herbs-other':'草药·其他',
 'reality-herbs-roots':'草药·根茎','reality-herbs-western':'西方草药','reality-human':'人体','reality-physical':'物理','society':'社会',
 'town-buildings':'城镇建筑',
 'staples':'主食','steam-horror':'蒸汽与恐怖（整组）','tools':'工具','western':'魔幻设定','western-alchemy':'西方炼金','western-biology':'西方生物'};
const EA_CAT_LABEL={'cat-food':'饮食','cat-produce':'作物','cat-herb':'草药','cat-alchemy':'炼金','cat-formula':'方剂','cat-biology':'生物','cat-race':'种族',
 'cat-character':'人物','cat-trait':'特质','cat-material':'材料','cat-tool':'工具工艺','cat-society':'社会','cat-culture':'文化','cat-name':'人名',
 'cat-eastern':'东方玄幻','cat-western':'西方魔幻','cat-steam':'蒸汽朋克','cat-horror':'民俗恐怖','cat-physical':'物理','cat-generic':'其他'};
const EA_FIELD_LABEL={definition:'定义',mechanism:'机制',conditions:'条件',exceptions:'例外',story_uses:'故事用法',historical_scope:'历史范围',
 evidence_and_uncertainty:'证据与不确定性',summary:'摘要',variants:'变体',story_roles:'故事角色',background:'背景',entry_modes:'进入方式',
 introduction_limits:'引入限制',genres:'题材',category:'类别'};
const EA_STATUS_LABEL={needs_review:'待审核',reviewed:'已审核',approved:'已通过',rejected:'已驳回',needs_detail:'待补细节',detailed:'细节完整',complete:'细节完整'};
let eaCatMap={},eaVirtual=[],eaWorldviews={},eaGroupTag='',eaVirtualCount={};
const EA_WORLD_KEY='textiledream-ea-worldview';
let eaWorld=(()=>{try{return localStorage.getItem(EA_WORLD_KEY)||'all'}catch(error){return 'all'}})();
const eaArt=(async()=>{
 try{
  const [sprite,manifest]=await Promise.all([fetch('/static/map-art/map-art.svg').then(r=>r.text()),fetch('/static/map-art/manifest.json').then(r=>r.json())]);
  if(!document.getElementById('ea-sprite')){const holder=document.createElement('div');holder.id='ea-sprite';holder.setAttribute('aria-hidden','true');holder.style.cssText='position:absolute;width:0;height:0;overflow:hidden';holder.innerHTML=sprite;document.body.prepend(holder)}
  const cats=manifest.element_categories||{};
  eaCatMap=cats.map||{};eaVirtual=(cats.virtual&&cats.virtual.groups)||[];eaWorldviews=cats.worldviews||{};
  if(!eaWorldviews[eaWorld])eaWorld='all';
 }catch(error){eaCatMap={}}
})();
function eaCat(namespace){return eaCatMap[namespace]||'cat-generic'}
function eaSvgIcon(id,cls){
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('aria-hidden','true');svg.classList.add(cls||'ea-icon');
 const use=document.createElementNS('http://www.w3.org/2000/svg','use');use.setAttribute('href','#'+id);svg.append(use);return svg;
}
// 条目的徽记：若它落在某个虚拟分组里（如蒸汽/民俗恐怖），用虚拟分组的徽记。
function eaItemIconId(namespace,tags){
 for(const g of eaVirtual)if(g.namespace===namespace&&(tags||[]).includes(g.tag))return g.icon;
 return eaCat(namespace);
}
function eaIcon(namespace,cls,tags){return eaSvgIcon(eaItemIconId(namespace,tags),cls)}
function eaBadge(text,kind){return el('span',EA_STATUS_LABEL[text]||text,'ea-badge'+(kind?' ea-badge-'+kind:''))}
function eaNsLabel(namespace,tags){
 for(const g of eaVirtual)if(tags&&g.namespace===namespace&&tags.includes(g.tag))return g.label;
 return EA_NS_LABEL[namespace]||namespace;
}
function eaOpenSheet(){elementPanel.classList.add('ea-sheet-open');setTimeout(()=>$('ea-public').focus({preventScroll:true}),60)}
function eaCloseSheet(){elementPanel.classList.remove('ea-sheet-open')}
function eaPickGroup(namespace,tag){
 $('ea-namespace').value=namespace;eaGroupTag=tag||'';
 $('ea-tag').value=tag||'';
 eaDrawCats();safe(()=>eaSearch(0));
}
function eaDrawWorld(){
 const box=$('ea-world');if(!box)return;box.replaceChildren();
 for(const [id,view] of Object.entries(eaWorldviews)){
  if(id==='note')continue;
  const b=el('button',undefined,'ea-world-btn'+(id===eaWorld?' is-on':''));b.type='button';b.setAttribute('aria-pressed',String(id===eaWorld));
  if(view.icon)b.append(eaSvgIcon(view.icon,'ea-world-icon'));
  b.append(el('span',view.label||id));
  b.onclick=()=>{eaWorld=id;try{localStorage.setItem(EA_WORLD_KEY,id)}catch(error){}
   const hide=(eaWorldviews[id]&&eaWorldviews[id].hide)||[];
   if(hide.includes($('ea-namespace').value)){$('ea-namespace').value='';eaGroupTag='';$('ea-tag').value='';safe(()=>eaSearch(0))}
   eaDrawWorld();eaDrawCats()};
  box.append(b);
 }
}
function eaDrawCats(){
 const box=$('ea-cats');if(!box||!eaInfo||!eaInfo.groups)return;
 box.replaceChildren();
 const hide=new Set((eaWorldviews[eaWorld]&&eaWorldviews[eaWorld].hide)||[]);
 const groups={};
 for(const g of eaInfo.groups){
  if(hide.has(g.namespace))continue;
  const split=eaVirtual.filter(v=>v.namespace===g.namespace);
  if(split.length){for(const v of split)(groups[v.icon]=groups[v.icon]||[]).push({namespace:g.namespace,tag:v.tag,label:v.label,count:null});continue}
  (groups[eaCat(g.namespace)]=groups[eaCat(g.namespace)]||[]).push({namespace:g.namespace,tag:'',label:eaNsLabel(g.namespace),count:g.elements});
 }
 const current=$('ea-namespace').value;
 const all=el('button',undefined,'ea-cat-chip ea-cat-all'+(current?'':' is-on'));all.type='button';all.append(el('span','全部'),el('small',String(eaInfo.totals.elements)));
 all.onclick=()=>eaPickGroup('','');box.append(all);
 for(const [cat,list] of Object.entries(groups).sort((a,b)=>(EA_CAT_LABEL[a[0]]||'').localeCompare(EA_CAT_LABEL[b[0]]||'','zh'))){
  const group=el('div',undefined,'ea-cat-group');
  const head=el('span',undefined,'ea-cat-head');head.append(eaSvgIcon(cat,'ea-cat-icon'),el('span',EA_CAT_LABEL[cat]||'其他'));group.append(head);
  const solo=list.length===1;
  for(const g of list){
   const on=g.namespace===current&&(g.tag||'')===eaGroupTag;
   const chip=el('button',undefined,'ea-cat-chip'+(on?' is-on':''));chip.type='button';chip.title=g.namespace+(g.tag?' · '+g.tag:'');
   // 只有一个子分组时，大类本身就是按钮，不再重复一遍名字。
   if(solo){group.classList.add('is-solo');head.remove();chip.classList.add('ea-cat-solo');chip.append(eaSvgIcon(cat,'ea-cat-icon'),el('span',EA_CAT_LABEL[cat]||g.label))}
   else chip.append(el('span',g.label));
   if(g.count!==null)chip.append(el('small',String(g.count)));
   else{const key=g.namespace+'|'+g.tag;const small=el('small',eaVirtualCount[key]===undefined?'…':String(eaVirtualCount[key]));chip.append(small);
    if(eaVirtualCount[key]===undefined)api('/inner/elements/search?'+new URLSearchParams({namespace:g.namespace,tag:g.tag,limit:'1',offset:'0'})).then(p=>{eaVirtualCount[key]=p.total;small.textContent=String(p.total)}).catch(()=>{small.textContent=''})}
   chip.onclick=()=>eaPickGroup(g.namespace,g.tag);
   group.append(chip);
  }
  box.append(group);
 }
}

const elementNav=el('button');
elementNav.dataset.page='elements';
elementNav.append(el('span','◆ 元素数据库'),el('small','作者'));
elementNav.onclick=()=>safe(()=>showPage('elements'));
document.querySelector('nav button[data-page="world-workshop"]').closest('nav').append(elementNav);

TDNav.register('elements',{title:'元素数据库',enter:async()=>{await eaLoadLibrary();await eaLoadPackage();await eaListDrafts();if(!$('ea-results').childElementCount)await eaSearch(0)}});

let eaInfo=null,eaPackageInfo=null,eaElements=[],eaRules=[],eaDraft=null,eaTarget=null;
let eaPageState={offset:0,limit:20,total:0};

async function eaLoadLibrary(){
 const box=$('ea-library');box.replaceChildren(el('p','读取中…'));
 try{eaInfo=await api('/inner/elements/library')}catch(error){box.replaceChildren(el('p',error.message));return}
 box.replaceChildren();
 if(!eaInfo.exists||!eaInfo.readable){
  box.append(el('p',eaInfo.error||'百科库不可用'),el('p','生成命令：'+eaInfo.build_command,'muted'));
  return;
 }
 const stats=el('div',undefined,'ea-stats');
 for(const [n,label] of [[eaInfo.totals.elements,'元素'],[eaInfo.totals.groups,'分组'],[eaInfo.totals.sources,'来源']]){const s=el('span',undefined,'ea-stat');s.append(el('b',String(n)),el('small',label));stats.append(s)}
 stats.title=`${eaInfo.path} · schema ${eaInfo.schema_version}（只读）`;
 box.append(stats,el('p',eaInfo.candidate,'muted ea-fine'));
 const select=$('ea-namespace');
 select.replaceChildren(new Option('全部分组',''));
 for(const group of eaInfo.groups)select.append(new Option(`${eaNsLabel(group.namespace)}（${group.elements}）`,group.namespace));
 await eaArt;eaDrawWorld();eaDrawCats();
 const states=$('ea-state');states.replaceChildren(...eaInfo.states.map(s=>new Option(s.label,s.id)));
 const fields=$('ea-fields');fields.replaceChildren(el('p','公开字段（白名单，留空则只公开上面的说明）','ea-group-label'));
 const chips=el('div',undefined,'ea-chips');fields.append(chips);
 for(const name of eaInfo.public_fields){
  const line=el('label',undefined,'ea-chip');line.title=name;const box=el('input');box.type='checkbox';box.classList.add('ea-field');box.dataset.field=name;
  line.append(box,el('span',EA_FIELD_LABEL[name]||name));chips.append(line);
 }
}

async function eaLoadPackage(){
 eaPackageInfo=await api('/inner/package');
 const places=$('ea-location');places.replaceChildren(new Option('不限地点',''));
 for(const place of eaPackageInfo.story.locations||[])places.append(new Option(place.name,place.id));
 const box=$('ea-known');box.replaceChildren(el('p','谁可以看到（known_by，留空=谁都看不到）','ea-group-label'));
 const chips=el('div',undefined,'ea-chips');box.append(chips);
 const names=Object.fromEntries((eaPackageInfo.characters.characters||[]).map(c=>[c.id,c.name||c.id]));
 for(const who of new Set(['player'].concat(Object.keys(names)))){
  const line=el('label',undefined,'ea-chip');line.title=who;const box2=el('input');box2.type='checkbox';box2.classList.add('ea-known');box2.dataset.who=who;
  line.append(box2,el('span',who==='player'?'玩家':names[who]));chips.append(line);
 }
 eaFillRuleFrom();
}

async function eaSearch(offset){
 eaPageState.offset=Math.max(0,offset||0);
 const box=$('ea-results');box.replaceChildren(el('p','检索中…'));
 try{
  const params=new URLSearchParams({text:$('ea-text').value.trim(),tag:$('ea-tag').value.trim(),namespace:$('ea-namespace').value,limit:String(eaPageState.limit),offset:String(eaPageState.offset)});
  const page=await api('/inner/elements/search?'+params.toString());
  eaPageState.total=page.total;
   const first=page.total?page.offset+1:0,last=page.offset+page.returned;
  $('ea-page').textContent=`共 ${page.total} 条 · 第 ${first}–${last} 条`;
  $('ea-prev').disabled=page.offset<=0;$('ea-next').disabled=last>=page.total;
  await eaArt;
  box.replaceChildren();
  if(!page.items.length)box.append(el('p','没有命中。换个名称、别名或标签试试。','muted ea-empty'));
  for(const item of page.items){
   const card=el('article',undefined,'ea-item');
   card.dataset.ref=item.namespace+'/'+item.element_id;
   if(eaElements.some(e=>e.namespace===item.namespace&&e.element_id===item.element_id))card.classList.add('in-basket');
   const head=el('div',undefined,'ea-item-head');
   const title=el('div',undefined,'ea-item-title');
   title.append(el('h3',item.name),el('small',`${eaNsLabel(item.namespace,item.tags)} · ${item.element_id} · v${item.version}`));
   head.append(eaIcon(item.namespace,undefined,item.tags),title);card.append(head);
   const badges=el('div',undefined,'ea-badges');
   badges.append(eaBadge(item.review_status,'review'),eaBadge(item.detail_status,'detail'));
   if(card.classList.contains('in-basket'))badges.append(eaBadge('已在清单','in'));
   card.append(badges);
   card.append(el('p',item.summary||'（无摘要）','ea-summary'));
   if(item.aliases&&item.aliases.length)card.append(el('p','别名 · '+item.aliases.join(' / '),'ea-aliases'));
   if(item.tags&&item.tags.length){const tags=el('div',undefined,'ea-tags');for(const t of item.tags.slice(0,5))tags.append(el('span',t,'ea-tag'));if(item.tags.length>5)tags.append(el('span','+'+(item.tags.length-5),'ea-tag'));card.append(tags)}
   const actions=el('div',undefined,'ea-item-actions');
   actions.append(button('查看详情',()=>{for(const c of box.querySelectorAll('.ea-item.is-active'))c.classList.remove('is-active');card.classList.add('is-active');return eaDetail(item.namespace,item.element_id,item.version)}),
               button(card.classList.contains('in-basket')?'编辑':'加入清单',()=>eaPick(item),'primary'));
   card.append(actions);
   box.append(card);
  }
 }catch(error){box.replaceChildren(el('p',error.message))}
}

async function eaDetail(namespace,elementId,version){
 const box=$('ea-detail');box.replaceChildren(el('p','读取中…'));
 const item=await api(`/inner/elements/item/${encodeURIComponent(namespace)}/${encodeURIComponent(elementId)}${version?'?version='+version:''}`);
 const titleBox=$('ea-detail-title');titleBox.replaceChildren(eaIcon(item.namespace,'ea-detail-icon',item.tags),el('span',item.name));
 box.replaceChildren();
 const meta=el('div',undefined,'ea-badges');
 meta.append(el('span',`${eaNsLabel(item.namespace,item.tags)} · ${item.element_id}`,'ea-ref'),el('span',`v${item.version}${item.is_current?'':' · 历史版本'}`,'ea-ref'),eaBadge(item.review_status,'review'),eaBadge(item.detail_status,'detail'));
 box.append(meta,el('p',`当前版本 v${item.current_version} · 内容哈希 ${String(item.content_hash).slice(0,12)}`,'muted ea-fine'));
 const facts=el('div',undefined,'ea-facts');box.append(facts);
 formatReader(facts,{七节:item.details,额外分节:item.details_extra,适配映射:item.details_map,标签:item.tags,别名:item.aliases});
 // 只翻译本页详情里的字段名；formatReader 是共享函数，不动它。
 for(const strong of facts.querySelectorAll('strong'))if(EA_FIELD_LABEL[strong.textContent])strong.textContent=EA_FIELD_LABEL[strong.textContent];
 const sources=el('details');sources.open=true;sources.append(el('summary',`来源证据（${item.sources.length}，版本已固定）`));
 for(const source of item.sources){
  sources.append(el('p',`${source.source_id} v${source.source_version}（${source.source_namespace}）${source.is_current_source_version?'':'· 来源之后有更新，证据版本不变'}`,undefined),
   el('p',`${source.title||''} | ${source.url||''} | ${source.access||''}`,'muted'));
  if(source.payload&&source.payload.supports)sources.append(el('p','支撑：'+source.payload.supports,'muted'));
  if(source.payload&&source.payload.rights_note)sources.append(el('p','权利说明：'+source.payload.rights_note,'muted'));
 }
 box.append(sources);
 const versions=await api(`/inner/elements/item/${encodeURIComponent(namespace)}/${encodeURIComponent(elementId)}/versions`);
 const list=el('details');list.append(el('summary',`版本历史（${versions.versions.length}）`));
 for(const row of versions.versions)list.append(el('p',`v${row.version}${row.is_current?' ←当前':''} · ${row.review_status}/${row.detail_status} · 批次 ${row.batch_id}`,'muted'));
 box.append(list);
}

function eaFillRuleFrom(){
 const select=$('ea-rule-from');if(!select)return;
 const current=select.value;
 const refs=eaElements.map(item=>item.namespace+'/'+item.element_id);
 select.replaceChildren(...refs.map(ref=>new Option(ref,ref)));
 if(refs.includes(current))select.value=current;
}

function eaPick(item){
 eaTarget={namespace:item.namespace,element_id:item.element_id,version:item.version,name:item.name};
 const existing=eaElements.find(entry=>entry.namespace===item.namespace&&entry.element_id===item.element_id);
 $('ea-target').textContent=`${item.name} · ${item.namespace}/${item.element_id}（库内当前版本 v${item.version}）`;
 $('ea-version').value=existing?existing.version:item.version;
 $('ea-state').value=existing?existing.state:'existing';
 $('ea-public').value=existing?existing.disclosure.public_description:'';
 $('ea-flag').value=existing&&existing.disclosure.reveal_flag||'';
 $('ea-location').value=existing&&existing.disclosure.location_id||'';
 $('ea-ack').checked=existing?existing.acknowledge_candidate:false;
 $('ea-target').replaceChildren(eaIcon(item.namespace,'ea-detail-icon'),el('b',item.name),el('small',`${eaNsLabel(item.namespace)} · ${item.element_id} · 库内当前 v${item.version}`));
 $('ea-reveal-potential').checked=existing?!!existing.disclosure.reveal_potential:false;
 for(const box of document.querySelectorAll('.ea-field'))box.checked=!!(existing&&existing.disclosure.public_fields.includes(box.dataset.field));
 for(const box of document.querySelectorAll('.ea-known'))box.checked=!!(existing&&existing.disclosure.known_by.includes(box.dataset.who));
 eaOpenSheet();
}

function eaEntryFromForm(){
 if(!eaTarget)throw Error('先选择要加入清单的条目');
 const version=Number($('ea-version').value);
 if(!Number.isInteger(version)||version<1)throw Error('版本必须是正整数');
 const publicFields=[...document.querySelectorAll('.ea-field')].filter(box=>box.checked).map(box=>box.dataset.field);
 const knownBy=[...document.querySelectorAll('.ea-known')].filter(box=>box.checked).map(box=>box.dataset.who);
 return {
  namespace:eaTarget.namespace,element_id:eaTarget.element_id,version,
  state:$('ea-state').value,
  acknowledge_candidate:!!$('ea-ack').checked,
  disclosure:{public_description:$('ea-public').value.trim(),public_fields:publicFields,
   location_id:$('ea-location').value||null,reveal_flag:$('ea-flag').value.trim()||null,
   known_by:knownBy,reveal_potential:!!$('ea-reveal-potential').checked},
  adaptation:{note:'',constraints:[]},
 };
}

function eaDrawSelected(){
 const box=$('ea-selected');box.replaceChildren();
 $('ea-count').textContent=eaElements.length?`${eaElements.length} 个`:'（空）';
 if(!eaElements.length){box.append(el('p','清单还是空的：从检索结果里加入条目。','muted'));eaFillRuleFrom();return}
 for(const entry of eaElements){
  const ref=`${entry.namespace}/${entry.element_id}`;
  const card=el('div',undefined,'ea-basket-row');
  const head=el('div',undefined,'ea-item-head');
  const title=el('div',undefined,'ea-item-title');title.append(el('b',entry.element_id),el('small',`${eaNsLabel(entry.namespace)} · v${entry.version}`));
  const badges=el('div',undefined,'ea-badges');badges.append(eaBadge(entry.state==='existing'?'已存在':'潜在',entry.state==='existing'?'in':'potential'),eaBadge(entry.acknowledge_candidate?'已确认候选':'未确认候选',entry.acknowledge_candidate?'review':'warn'));
  head.append(eaIcon(entry.namespace),title);
  card.append(head,badges,
   el('p',entry.disclosure.public_description||'（未写公开说明：玩家看不到）','ea-summary'),
   el('p',`公开字段 ${entry.disclosure.public_fields.map(f=>EA_FIELD_LABEL[f]||f).join('、')||'无'} · 地点 ${entry.disclosure.location_id||'不限'} · 受众 ${entry.disclosure.known_by.join('/')||'无'}${entry.disclosure.reveal_flag?' · 标记 '+entry.disclosure.reveal_flag:''}`,'ea-fine muted'));
  const toolbar=el('div',undefined,'toolbar');
  toolbar.append(button('编辑',()=>eaPick({namespace:entry.namespace,element_id:entry.element_id,version:entry.version,name:ref})),
   button('移除',()=>{eaElements=eaElements.filter(item=>item!==entry);eaDrawSelected();eaDrawRules()}));
  card.append(toolbar);
  box.append(card);
 }
 eaFillRuleFrom();eaDrawRules();
}

function eaDrawRules(){
 const box=$('ea-rules');box.replaceChildren();
 if(!eaRules.length){box.append(el('p','还没有 typed 规则。','muted'));return}
 for(const rule of eaRules){
  const line=el('div');
  line.append(el('p',`${rule.kind==='requires'?'依赖':'互斥'} ${rule.from} → ${rule.to}`),
   button('移除',()=>{eaRules=eaRules.filter(item=>item!==rule);eaDrawRules()}));
  box.append(line);
 }
}

$('ea-search').onsubmit=event=>{event.preventDefault();eaGroupTag=$('ea-tag').value.trim()===eaGroupTag?eaGroupTag:'';eaDrawCats();safe(()=>eaSearch(0))};
$('ea-namespace').onchange=()=>{eaGroupTag='';eaDrawCats()};
$('ea-prev').onclick=()=>safe(()=>eaSearch(Math.max(0,eaPageState.offset-eaPageState.limit)));
$('ea-next').onclick=()=>safe(()=>eaSearch(eaPageState.offset+eaPageState.limit));
$('ea-cancel-edit').onclick=()=>{eaTarget=null;$('ea-target').textContent='先在结果里点「加入清单」。';eaCloseSheet()};
$('ea-sheet-close').onclick=()=>$('ea-cancel-edit').click();
$('ea-sheet-backdrop').onclick=()=>$('ea-cancel-edit').click();
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&elementPanel.classList.contains('ea-sheet-open'))$('ea-cancel-edit').click()});

$('ea-add').onsubmit=event=>{event.preventDefault();safe(async()=>{
 const entry=eaEntryFromForm();
 eaElements=eaElements.filter(item=>!(item.namespace===entry.namespace&&item.element_id===entry.element_id));
 eaElements.push(entry);
 eaTarget=null;$('ea-target').textContent='已加入清单；可以继续选择下一条。';
 eaDrawSelected();eaCloseSheet();
 const card=document.querySelector(`#ea-results .ea-item[data-ref="${CSS.escape(entry.namespace+'/'+entry.element_id)}"]`);
 if(card&&!card.classList.contains('in-basket')){
  card.classList.add('in-basket');
  const pick=card.querySelector('.ea-item-actions .primary');if(pick)pick.textContent='编辑';
  const badges=card.querySelector('.ea-badges');if(badges)badges.append(eaBadge('已在清单','in'));
 }
})};

$('ea-rule-add').onclick=()=>safe(()=>{
 const from=$('ea-rule-from').value,to=$('ea-rule-to').value.trim();
 if(!from||!to)throw Error('规则需要 from 与 to（namespace/element_id）');
 eaRules.push({kind:$('ea-rule-kind').value,from,to,note:''});
 $('ea-rule-to').value='';eaDrawRules();
});

async function eaSaveDraft(){
 const body={elements:eaElements,rules:eaRules};
 // 已锁定的草稿不可改：下次保存自动开新草稿，旧版本与已提交的清单保持不可变。
 if(eaDraft&&eaDraft.status==='draft'){
  body.draft_id=eaDraft.id;
  body.expected_revision=eaDraft.revision;
 }
 eaDraft=await api('/inner/elements/drafts','POST',body);
 $('ea-status').textContent=`草稿已保存：${eaDraft.id} r${eaDraft.revision}`;
 await eaListDrafts();
 return eaDraft;
}

async function eaListDrafts(){
 const box=$('ea-drafts');box.replaceChildren();
 let rows=[];
 try{rows=await api('/inner/elements/drafts')}catch(error){box.append(el('p',error.message));return}
 if(!rows.length){box.append(el('p','还没有保存过的清单草稿。','muted'));return}
 for(const row of rows.slice().reverse()){
  const line=el('div');
  line.append(el('p',`${row.count} 个元素 · r${row.revision} · ${row.status==='committed'?'已锁定 '+String(row.committed_revision).slice(0,8):'草稿'}`,undefined),
   button('载入',async()=>{
    const draft=await api('/inner/elements/drafts/'+row.id);
    eaDraft=draft;eaElements=draft.elements;eaRules=(draft.rules&&draft.rules.items)||[];
    eaDrawSelected();$('ea-status').textContent=`已载入草稿 ${draft.id} r${draft.revision}`;
   }));
  box.append(line);
 }
}

$('ea-save').onclick=()=>safe(eaSaveDraft);
$('ea-drafts-refresh').onclick=()=>safe(eaListDrafts);
$('ea-recover').onclick=()=>safe(async()=>{
 const report=await api('/inner/elements/recover','POST');
 for(const note of report.errors||[])notice('恢复失败：'+note.reason);
 notice(`恢复：${report.recovered.length} 条回到草稿，${report.repaired.length} 条补齐索引，`
       +`${report.skipped.length} 条本进程正在提交（不处理）`);
 $('ea-status').textContent=JSON.stringify(report);
 await eaListDrafts();
});
$('ea-preview').onclick=()=>safe(async()=>{
 await eaSaveDraft();
 const result=await api('/inner/elements/drafts/'+eaDraft.id+'/preview','POST');
 const box=$('ea-warnings');box.replaceChildren();
 box.append(el('p',`试算通过：${result.count} 个元素，摘要 ${result.digest.slice(0,12)}（未写入故事包）`));
 for(const warning of result.warnings)box.append(el('p','提醒：'+warning,'muted'));
 for(const note of result.unsupported)box.append(el('p','未实现：'+note,'muted'));
 $('ea-status').textContent='校验完成；确认无误后再锁定。';
});

$('ea-commit').onclick=()=>safe(async()=>{
 if(!eaElements.length)throw Error('清单是空的');
 if(!confirm('把这份清单锁定进当前故事包（生成新版本）？已有旅程仍用原版本。'))return;
 await eaSaveDraft();
 const current=await api('/inner/package');
 const result=await api('/inner/elements/drafts/'+eaDraft.id+'/commit','POST',{expected_story_revision:current.id,expected_draft_revision:eaDraft.revision});
 notice(result.reused||result.indexed===false?result.note:('已锁定，故事包新版本 '+String(result.revision).slice(0,8)));
 const box=$('ea-warnings');box.replaceChildren();
 for(const warning of result.warnings||[])box.append(el('p','提醒：'+warning,'muted'));
 $('ea-status').textContent=`清单摘要 ${result.digest.slice(0,12)}`;
 // 已提交的草稿不可再改：清掉本地引用，下次保存自动开新草稿。
 eaDraft=null;
 await eaListDrafts();
});

$('ea-manifest').onclick=()=>safe(async()=>{
 const box=$('ea-manifest-box');box.replaceChildren(el('p','读取中…'));
 const view=await api('/inner/elements/manifest');
 if(!view){box.replaceChildren(el('p','当前故事包还没有元素清单（老包行为不变：提示词里不出现元素段）。','muted'));return}
 box.replaceChildren(el('p',`${view.count} 个元素 · 摘要 ${view.digest.slice(0,12)} · 锁定于 ${view.locked_at||'—'}`),
  el('p',view.candidate_notice,'muted'));
 for(const element of view.elements){
  const detail=el('details');
  detail.append(el('summary',`${element.name} · ${element.ref} v${element.version} · ${element.state==='existing'?'已存在':'潜在'}`),
   el('p',`审核状态（只记录原值）：${element.review_status} / ${element.detail_status}`,undefined,'muted'),
   el('p',`来源（固定版本）：${element.sources.map(s=>s.source_id+' v'+s.source_version).join('、')||'无'}`,undefined,'muted'),
   el('p',`公开字段：${element.disclosure.public_fields.join(', ')||'无'} · 地点 ${element.disclosure.location_id||'不限'} · 受众 ${element.disclosure.known_by.join('/')||'无'}`,undefined,'muted'));
  const body=el('div');formatReader(body,element.payload);detail.append(body);
  box.append(detail);
 }
 for(const warning of view.warnings)box.append(el('p','提醒：'+warning,'muted'));
 for(const note of view.unsupported)box.append(el('p','未实现：'+note,'muted'));
});

eaDrawSelected();eaDrawRules();
