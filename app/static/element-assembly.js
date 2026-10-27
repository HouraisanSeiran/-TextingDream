'use strict';
// 元素装配页。所有值都用 textContent（el()）写入，作者文本不会变成标记。
// 页面只和 /api/inner/elements/* 通信：不传文件路径，也不相信浏览器提交的 payload——
// 服务端按选中的 namespace/element_id/version 自己从只读库里读。
const elementPanel=el('section',undefined,'page');elementPanel.id='elements';elementPanel.hidden=true;
elementPanel.innerHTML=`<div class="intro"><h2>元素装配</h2><p>从本地候选库挑条目、逐条确认并固定版本，形成这个世界的元素清单。清单在开局前锁定；旅程只读故事包里的快照，运行期不再查库。库里的条目都是待审候选，采纳不会把它们标成已核实。</p></div>
<div class="card"><h3>本地百科库</h3><div id="ea-library" class="muted">读取中…</div></div>
<div class="two-col"><div>
<form id="ea-search" class="card"><h3>检索</h3>
<label>名称或别名<input id="ea-text" maxlength="200" placeholder="例如 小麦、steel"></label>
<label>标签（任一命中，逗号分隔）<input id="ea-tag" maxlength="200" placeholder="cereal, metal"></label>
<label>命名空间<select id="ea-namespace"><option value="">全部</option></select></label>
<div class="toolbar"><button class="primary" type="submit">搜索</button><button id="ea-prev" type="button">上一页</button><button id="ea-next" type="button">下一页</button></div>
<p id="ea-page" class="muted"></p></form>
<div class="card"><h3>检索结果</h3><div id="ea-results"></div></div>
<div class="card"><h3 id="ea-detail-title">条目详情</h3><div id="ea-detail" class="muted">选择一条结果查看完整内容与固定来源版本。</div></div>
</div><div>
<form id="ea-add" class="card"><h3>加入清单</h3>
<p id="ea-target" class="muted">先在上方结果里点“加入清单”。</p>
<label>固定版本<input id="ea-version" type="number" min="1" value="1"></label>
<label>状态<select id="ea-state"></select></label>
<label>公开说明（作者定稿，玩家可见）<textarea id="ea-public" rows="3" maxlength="600" placeholder="用一两句话写这个元素在本世界的样子"></textarea></label>
<div id="ea-fields"></div>
<label>限定地点<select id="ea-location"><option value="">不限地点</option></select></label>
<label>解锁标记 reveal_flag<input id="ea-flag" maxlength="60" placeholder="例如 met_guild"></label>
<div id="ea-known"></div>
<label class="inline"><input id="ea-reveal-potential" type="checkbox"> 潜在元素也允许透露其存在</label>
<label class="inline"><input id="ea-ack" type="checkbox"> 我已确认这是待审候选资料（采纳不改变审核状态）</label>
<div class="toolbar"><button class="primary" type="submit">加入清单</button><button id="ea-cancel-edit" type="button">取消</button></div>
<p class="muted">服务端会用仓库里的原始 payload 重新组装，浏览器提交的内容不被当作事实来源。</p></form>
<div class="card"><h3>选择清单 <small id="ea-count"></small></h3><div id="ea-selected"></div>
<div class="toolbar"><button id="ea-save">保存草稿</button><button id="ea-preview">校验并试算</button><button id="ea-commit" class="primary">锁定到故事包</button></div>
<p id="ea-status" class="muted" role="status"></p><div id="ea-warnings"></div></div>
<div class="card"><h3>显式 typed 规则</h3>
<div class="toolbar"><select id="ea-rule-kind"><option value="requires">依赖 requires</option><option value="conflicts">互斥 conflicts</option></select><select id="ea-rule-from"></select><input id="ea-rule-to" maxlength="120" placeholder="namespace/element_id"><button id="ea-rule-add" type="button">添加</button></div>
<div id="ea-rules"></div>
<p class="muted">只有这里列出的规则会被机器校验（缺引用、环、互斥都会报错）。条目里的 requires / excludes 是自然语言条件，本版本不当依赖，只在警告里逐条标出。</p></div>
<div class="card"><h3>故事包清单</h3>
<div class="toolbar"><button id="ea-manifest">读取作者视图</button><button id="ea-drafts">草稿列表</button><button id="ea-recover">恢复中断的提交</button></div>
<div id="ea-drafts"></div><div id="ea-manifest-box"></div></div>
</div></div>`;
document.querySelector('main').append(elementPanel);

const elementNav=el('button');
elementNav.dataset.page='elements';
elementNav.append(el('span','◆ 元素装配'),el('small','作者'));
elementNav.onclick=()=>safe(()=>showPage('elements'));
document.querySelector('nav').insertBefore(elementNav,document.querySelector('nav button[data-page="traces"]'));

const elementShowPage=showPage;
showPage=async function(id){await elementShowPage(id);if(id!=='elements')return;
 $('page-title').textContent='元素装配';$('breadcrumb').textContent='工作空间 / 元素装配';
 await eaLoadLibrary();await eaLoadPackage();await eaListDrafts()};

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
 box.append(el('p',`${eaInfo.path} · schema ${eaInfo.schema_version} · 组 ${eaInfo.totals.groups} · 元素 ${eaInfo.totals.elements} · 来源 ${eaInfo.totals.sources}（只读）`),
  el('p',eaInfo.candidate,'muted'));
 const select=$('ea-namespace');
 select.replaceChildren(new Option('全部',''));
 for(const group of eaInfo.groups)select.append(new Option(`${group.namespace}（${group.elements}）`,group.namespace));
 const states=$('ea-state');states.replaceChildren(...eaInfo.states.map(s=>new Option(s.label,s.id)));
 const fields=$('ea-fields');fields.replaceChildren(el('p','公开字段（白名单，留空则只公开上面的说明）','muted'));
 for(const name of eaInfo.public_fields){
  const line=el('label','inline');const box=el('input');box.type='checkbox';box.classList.add('ea-field');box.dataset.field=name;
  line.append(box,el('span',name));fields.append(line);
 }
}

async function eaLoadPackage(){
 eaPackageInfo=await api('/inner/package');
 const places=$('ea-location');places.replaceChildren(new Option('不限地点',''));
 for(const place of eaPackageInfo.story.locations||[])places.append(new Option(place.name,place.id));
 const box=$('ea-known');box.replaceChildren(el('p','谁可以看到（known_by，留空=谁都看不到）','muted'));
 for(const who of ['player'].concat((eaPackageInfo.characters.characters||[]).map(c=>c.id))){
  const line=el('label','inline');const box2=el('input');box2.type='checkbox';box2.classList.add('ea-known');box2.dataset.who=who;
  line.append(box2,el('span',who==='player'?'玩家':who));box.append(line);
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
  $('ea-page').textContent=`命中 ${page.total} 条，本页 ${page.returned} 条（offset ${page.offset}）`;
  box.replaceChildren();
  if(!page.items.length)box.append(el('p','没有命中。换个名称、别名或标签试试。','muted'));
  for(const item of page.items){
   const card=el('article',undefined,'card');
   card.append(el('h3',item.name),el('p',`${item.namespace}/${item.element_id} v${item.version} · ${item.review_status} / ${item.detail_status}`,'muted'));
   if(item.aliases&&item.aliases.length)card.append(el('p','别名：'+item.aliases.join(' / '),'muted'));
   if(item.tags&&item.tags.length)card.append(el('p','标签：'+item.tags.join(', '),'muted'));
   card.append(el('p',item.summary||'（无摘要）','prose'));
   card.append(button('查看详情',()=>eaDetail(item.namespace,item.element_id,item.version)),
               button('加入清单',()=>eaPick(item),'primary'));
   box.append(card);
  }
 }catch(error){box.replaceChildren(el('p',error.message))}
}

async function eaDetail(namespace,elementId,version){
 const box=$('ea-detail');box.replaceChildren(el('p','读取中…'));
 const item=await api(`/inner/elements/item/${encodeURIComponent(namespace)}/${encodeURIComponent(elementId)}${version?'?version='+version:''}`);
 $('ea-detail-title').textContent=`${item.name} · ${item.namespace}/${item.element_id} v${item.version}`;
 box.replaceChildren();
 box.append(el('p',`当前版本 v${item.current_version}${item.is_current?'':'（这是历史版本）'} · 内容哈希 ${String(item.content_hash).slice(0,12)} · ${item.review_status} / ${item.detail_status}`,'muted'));
 const facts=el('div');box.append(facts);
 formatReader(facts,{七节:item.details,额外分节:item.details_extra,适配映射:item.details_map,标签:item.tags,别名:item.aliases});
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
 $('ea-reveal-potential').checked=existing?!!existing.disclosure.reveal_potential:false;
 for(const box of document.querySelectorAll('.ea-field'))box.checked=!!(existing&&existing.disclosure.public_fields.includes(box.dataset.field));
 for(const box of document.querySelectorAll('.ea-known'))box.checked=!!(existing&&existing.disclosure.known_by.includes(box.dataset.who));
 $('ea-add').scrollIntoView({block:'nearest'});
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
  const card=el('div');
  card.append(el('p',`${ref} v${entry.version} · ${entry.state==='existing'?'已存在':'潜在'}${entry.acknowledge_candidate?' · 已确认候选':' · 尚未确认候选'}`),
   el('p',entry.disclosure.public_description||'（未写公开说明：玩家看不到）','prose'),
   el('p',`公开字段：${entry.disclosure.public_fields.join(', ')||'无'} · 地点 ${entry.disclosure.location_id||'不限'} · 受众 ${entry.disclosure.known_by.join('/')||'无'}${entry.disclosure.reveal_flag?' · 标记 '+entry.disclosure.reveal_flag:''}`,undefined,'muted'));
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

$('ea-search').onsubmit=event=>{event.preventDefault();safe(()=>eaSearch(0))};
$('ea-prev').onclick=()=>safe(()=>eaSearch(Math.max(0,eaPageState.offset-eaPageState.limit)));
$('ea-next').onclick=()=>safe(()=>eaSearch(eaPageState.offset+eaPageState.limit));
$('ea-cancel-edit').onclick=()=>{eaTarget=null;$('ea-target').textContent='先在上方结果里点“加入清单”。'};

$('ea-add').onsubmit=event=>{event.preventDefault();safe(async()=>{
 const entry=eaEntryFromForm();
 eaElements=eaElements.filter(item=>!(item.namespace===entry.namespace&&item.element_id===entry.element_id));
 eaElements.push(entry);
 eaTarget=null;$('ea-target').textContent='已加入清单；可以继续选择下一条。';
 eaDrawSelected();
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
$('ea-drafts').onclick=()=>safe(eaListDrafts);
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
