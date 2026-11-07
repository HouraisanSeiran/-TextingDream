'use strict';
/* 世界设定：类型配比 + 科技 / 魔法档位 + 国家 / 种族 / 势力短表，以及「按设定推荐元素」。
 * 挂在「元素数据库」页顶部。保存 = 故事包新版本（PUT /inner/world-setting）。
 * 推荐结果的「加入清单」复用 element-assembly.js 的 eaPick，走原有锁定流程。
 * 所有作者文本都用 textContent 写入。 */
(function(){
 const page=document.getElementById('elements');if(!page)return;
 let options=null,setting=null,loaded=false;
 const card=el('details',undefined,'ws-card');card.id='world-setting';card.open=true;
 card.innerHTML='<summary><strong>世界设定</strong><span class="muted">类型配比、科技与魔法档位、国家 / 种族 / 势力。按它推荐元素。</span></summary>'+
  '<div class="ws-body"><div class="ws-row"><p class="ws-label">大类 <small>选中大类 = 纳入该类元素；技术元素不跟大类走，只按科技档位纳入</small></p><div id="ws-cats" class="ws-cats"></div></div>'+
  '<div class="ws-row"><p class="ws-label">类型配比 <small>只影响推荐排序：3 = 主体，1 = 点缀</small></p><div id="ws-genres" class="ws-genres"></div></div>'+
  '<div class="ws-two"><div><p class="ws-label">科技档位 <small>止于二战前</small></p><div id="ws-tech" class="ws-tiers"></div><p class="ws-label ws-markers-label">代表性科技 <small>勾选世界里已出现的；下方档位按「该档及以下代表科技齐全」自动推断，也可直接点选档位（直接点选优先）</small></p><div id="ws-markers" class="ws-markers"></div></div>'+
  '<div><p class="ws-label">魔法档位</p><div id="ws-magic" class="ws-tiers"></div></div></div>'+
  '<div id="ws-lists" class="ws-lists"></div>'+
  '<label class="ws-note">补充说明<textarea id="ws-note" rows="2" maxlength="1200" placeholder="例如：魔法被教会垄断，蒸汽机只在南方港口使用"></textarea></label>'+
  '<div class="ws-actions"><span id="ws-status" class="muted" role="status"></span><button id="ws-cat-preview" type="button">查看大类元素</button><button id="ws-recommend" type="button">按设定推荐元素</button><button id="ws-generate" type="button">生成世界观</button><button id="ws-save" type="button" class="primary">保存设定</button></div>'+
  '<div id="ws-draft" class="ws-draft" hidden></div><div id="ws-reco" class="ws-reco" hidden></div></div>';
 page.querySelector('.ea-hero').after(card);
 const $$=id=>document.getElementById(id);
 const blank=()=>({genres:[],categories:[],tech:null,tech_markers:[],magic:null,note:'',polities:[],races:[],factions:[]});
 // 代表性科技 → 推断档位：该档及以下所有档的代表科技都已出现的最高档（与后端 tier_from_markers 同规则）。
 let directTech=false;
 function inferTier(present){let best=null;for(const t of options.tech){if(t.markers.length&&t.markers.every(m=>present.includes(m)))best=t.id;else break}return best}
 function syncDirect(){const inf=inferTier(setting.tech_markers||[]);directTech=!!setting.tech&&(!(setting.tech_markers||[]).length||inf!==setting.tech)}
 const slug=()=>('x'+Date.now().toString(36)+Math.random().toString(36).slice(2,5));

 function drawGenres(){
  const box=$$('ws-genres');box.replaceChildren();
  for(const g of options.genres){
   const on=setting.genres.find(x=>x.tag===g.id);
   const chip=el('span',undefined,'ws-chip'+(on?' on':''));
   const toggle=button(g.label,()=>{if(on)setting.genres=setting.genres.filter(x=>x.tag!==g.id);else setting.genres.push({tag:g.id,weight:2});drawGenres()});
   toggle.setAttribute('aria-pressed',String(!!on));chip.append(toggle);
   if(on){const w=el('select');w.setAttribute('aria-label',g.label+'权重');for(const n of [3,2,1])w.append(new Option(['','点缀','次要','主体'][n],n));w.value=String(on.weight);w.onchange=()=>{on.weight=Number(w.value)};chip.append(w)}
   box.append(chip);
  }
 }
 function drawTiers(id,key,list){
  const box=$$(id);box.replaceChildren();
  const tech=key==='tech';
  const none=button('不限',()=>{setting[key]=null;if(tech)directTech=false;drawTiers(id,key,list);if(tech)drawMarkers()},'ws-tier'+(setting[key]?'':' on'));box.append(none);
  for(const t of list){const b=button('',()=>{setting[key]=t.id;if(tech){directTech=true;drawMarkers()}drawTiers(id,key,list)},'ws-tier'+(setting[key]===t.id?' on':'')+(tech&&!directTech&&setting[key]===t.id&&(setting.tech_markers||[]).length?' inferred':''));b.append(el('strong',t.label),el('small',t.description));b.setAttribute('aria-pressed',String(setting[key]===t.id));box.append(b)}
 }
 function drawMarkers(){
  const box=$$('ws-markers');box.replaceChildren();
  const have=setting.tech_markers||[];const inf=inferTier(have);
  for(const t of options.tech){
   const row=el('div',undefined,'ws-marker-tier'+(inf===t.id?' on':''));
   row.append(el('strong',t.label));
   for(const m of t.markers){
    const lab=el('label',undefined,'ws-marker');const cb=document.createElement('input');cb.type='checkbox';cb.checked=have.includes(m);cb.dataset.marker=m;
    cb.onchange=()=>{const set=new Set(setting.tech_markers||[]);if(cb.checked)set.add(m);else set.delete(m);setting.tech_markers=options.tech.flatMap(x=>x.markers).filter(x=>set.has(x));
     if(!directTech)setting.tech=inferTier(setting.tech_markers);drawTiers('ws-tech','tech',options.tech);drawMarkers()};
    lab.append(cb,el('span',m));row.append(lab);
   }
   box.append(row);
  }
  box.append(el('p',inf?'按代表科技推断：'+options.tech.find(x=>x.id===inf).label+(directTech?'（当前档位为直接点选，优先于推断）':''):'还没有凑齐任何一档的代表科技。','muted ws-hint'));
 }
 function drawLists(){
  const box=$$('ws-lists');box.replaceChildren();
  for(const l of options.lists){
   const col=el('div',undefined,'ws-list');const head=el('div',undefined,'ws-list-head');
   head.append(el('p',l.label+'（'+setting[l.id].length+'）','ws-label'),button('＋ 手写一项',()=>{setting[l.id].push({id:slug(),name:'',summary:'',tags:[],element_ref:null});drawLists()}));
   col.append(head);
   if(!setting[l.id].length)col.append(el('p','还没有。可以手写，或从下方推荐里「设为'+l.label+'」。','muted ws-empty'));
   for(const row of setting[l.id]){
    const r=el('div',undefined,'ws-item');
    const name=el('input');name.value=row.name;name.maxLength=40;name.placeholder=l.label+'名称';name.oninput=()=>{row.name=name.value};
    const sum=el('input');sum.value=row.summary;sum.maxLength=400;sum.placeholder='一句话说明';sum.oninput=()=>{row.summary=sum.value};
    const tags=el('input');tags.value=row.tags.join(', ');tags.placeholder=l.id==='polities'?'标签，逗号分隔：polity:monarchy, tech:steam':'标签，逗号分隔（可自定义）';
    tags.oninput=()=>{row.tags=tags.value.split(/[,，]/).map(s=>s.trim()).filter(Boolean)};
    const del=button('×',()=>{setting[l.id]=setting[l.id].filter(x=>x!==row);drawLists()},'ws-del');del.title='删除';del.setAttribute('aria-label','删除'+(row.name||l.label));
    r.append(name,del,sum,tags);
    if(row.element_ref)r.append(el('small','引用元素库：'+row.element_ref,'muted'));
    col.append(r);
   }
   if(l.id==='polities'){const hint=el('p',undefined,'ws-hint muted');hint.textContent='政体标签：'+options.polity_tags.map(t=>t.id.replace('polity:','')+' '+t.label).join(' · ');col.append(hint)}
   box.append(col);
  }
 }
 function drawCats(){
  const box=$$('ws-cats');box.replaceChildren();
  for(const c of options.categories){
   const on=setting.categories.includes(c.id);
   const b=button('',()=>{setting.categories=on?setting.categories.filter(x=>x!==c.id):[...setting.categories,c.id];drawCats()},'ws-tier'+(on?' on':''));
   b.append(el('strong',c.label),el('small',c.description));b.setAttribute('aria-pressed',String(on));box.append(b);
  }
 }
 function draw(){drawCats();drawGenres();setting.tech_markers=setting.tech_markers||[];syncDirect();drawTiers('ws-tech','tech',options.tech);drawMarkers();drawTiers('ws-magic','magic',options.magic);drawLists();$$('ws-note').value=setting.note||''}
 // 手写了但没填名称的空行不提交（否则整份设定校验失败）。
 function payload(){setting.note=$$('ws-note').value;const out=Object.assign({},setting);for(const l of options.lists)out[l.id]=setting[l.id].filter(r=>r.name.trim());return out}

 async function load(){
  const r=await api('/inner/world-setting');options=r.options;setting=Object.assign(blank(),r.setting||{});
  $$('ws-status').textContent=r.revision?'':'还没有世界：设定可以先填，保存需要先新建或导入故事包。';
  $$('ws-save').disabled=!r.revision;loaded=true;draw();
 }
 $$('ws-save').onclick=()=>safe(async()=>{const r=await api('/inner/world-setting','PUT',{setting:payload()});setting=Object.assign(blank(),r.setting);draw();$$('ws-status').textContent='已保存为故事包新版本 '+r.revision+(r.category_elements?' · 锁定大类元素 '+r.category_elements+' 条':'');notice('世界设定已保存；新旅程使用新设定，已有旅程不变')});
 $$('ws-recommend').onclick=()=>safe(async()=>{
  const box=$$('ws-reco');box.hidden=false;box.replaceChildren(el('p','推荐中…','muted'));
  const r=await api('/inner/world-setting/recommend','POST',{setting:payload()});box.replaceChildren();
  for(const g of r.groups){
   const sec=el('section',undefined,'ws-group');
   const meta=[g.items.length?'':'没有匹配的条目',g.more?'另有 '+g.more+' 条':'',g.skipped_by_tier?g.skipped_by_tier+' 条越档未列出':''].filter(Boolean).join(' · ');
   const h=el('h4',g.title);if(meta)h.append(el('small',' '+meta,'muted'));sec.append(h);
   const grid=el('div',undefined,'ws-reco-grid');
   for(const it of g.items){
    const c=el('article',undefined,'ws-reco-item'+(it.adopted?' adopted':''));
    c.append(el('strong',it.name||it.element_id),el('p',it.summary||'（无摘要）','muted'));
    const tags=el('div',undefined,'ws-reco-tags');for(const t of it.tags.slice(0,4))tags.append(el('span',t));c.append(tags);
    const acts=el('div',undefined,'ws-reco-acts');
    acts.append(button(it.adopted?'已在清单 · 编辑':'加入清单',()=>window.eaPick?.({namespace:it.namespace,element_id:it.element_id,version:it.version,name:it.name}),it.adopted?'':'primary'));
    const target={polities:'polities',races:'races',factions:'factions'}[g.id];
    if(target&&!setting[target].some(x=>x.element_ref===it.ref))acts.append(button('设为'+options.lists.find(l=>l.id===target).label,()=>{setting[target].push({id:slug(),name:(it.name||'').slice(0,40),summary:(it.summary||'').slice(0,400),tags:it.tags.filter(t=>/^(genre|tech|magic|polity):/.test(t)),element_ref:it.ref});drawLists();notice('已加入设定，记得保存')}));
    c.append(acts);grid.append(c);
   }
   sec.append(grid);box.append(sec);
  }
 });
 // 大类 → 纳入的元素（只读预览）。
 $$('ws-cat-preview').onclick=()=>safe(async()=>{
  const box=$$('ws-reco');box.hidden=false;box.replaceChildren(el('p','读取中…','muted'));
  const r=await api('/inner/world-setting/categories','POST',{setting:payload()});box.replaceChildren();
  box.append(el('p','共纳入 '+r.unique+' 条元素（同一条只算一次）。保存设定后，这些元素随世界设定生效；单条细调仍走下方「加入清单」。','muted'));
  if(!r.setting.categories.length)box.append(el('p','还没选大类。','muted'));
  for(const g of r.groups){
   if(g.id==='technology'&&!r.setting.tech){box.append(el('p','科技：未设科技档位，不纳入技术元素。','muted'));continue}
   const sec=el('section',undefined,'ws-group');
   const h=el('h4',g.title+'（'+g.items.length+'）');if(g.skipped_by_tier)h.append(el('small',' '+g.skipped_by_tier+' 条越档未纳入','muted'));sec.append(h);
   const list=el('p',g.items.filter(i=>!i.duplicate).map(i=>i.name).join('、')||'没有匹配的条目','ws-cat-names');sec.append(list);box.append(sec);
  }
 });
 // 世界观生成 agent：生成草稿 → 作者审阅 → 采纳为故事包新版本。
 function drawDraft(d){
  const box=$$('ws-draft');box.hidden=false;box.replaceChildren();
  const r=d.result;box.append(el('h4','世界观草稿'),el('p',r.premise,'prose'));
  const sec=(title,rows)=>{if(!rows||!rows.length)return;box.append(el('p',title,'ws-label'));const ul=el('ul');for(const x of rows)ul.append(el('li',typeof x==='string'?x:(x.era||x.name)+'：'+x.summary));box.append(ul)};
  sec('世界规则',r.laws);sec('年表',r.chronology);if(r.geography.overview)box.append(el('p','地理：'+r.geography.overview));sec('地区',r.geography.regions);sec('文化',r.cultures);sec('国家',r.polities);sec('种族',r.races);sec('势力',r.factions);
  box.append(el('p','取材 '+r.used_elements.length+' 条元素 · 可用 '+d.element_count+' 条','muted'));
  for(const w of d.warnings||[])box.append(el('p','⚠ '+w,'muted'));
  const acts=el('div',undefined,'ws-actions');
  const adopt=button('采纳为世界观',async()=>{if(!confirm('用这份草稿替换当前世界观正文？世界设定保留，已有旅程不变。'))return;const res=await api('/inner/worldview/drafts/'+d.id+'/adopt','POST');adopt.disabled=true;notice('已采纳，故事包新版本 '+res.revision)},'primary');
  acts.append(button('重新生成',()=>$$('ws-generate').click()),adopt);box.append(acts);
 }
 $$('ws-generate').onclick=()=>safe(async()=>{
  const b=$$('ws-generate');b.disabled=true;const box=$$('ws-draft');box.hidden=false;box.replaceChildren(el('p','生成中…（调用模型）','muted'));
  try{drawDraft(await api('/inner/worldview/generate','POST',{setting:payload()}))}catch(e){box.replaceChildren(el('p',e.message,'muted'));throw e}finally{b.disabled=false}
 });
 // 进入元素数据库页时读取一次（之后保留未保存的编辑）。
 new MutationObserver(()=>{if(!page.hidden&&!loaded)safe(load)}).observe(page,{attributes:true,attributeFilter:['hidden']});
 if(!page.hidden)safe(load);
})();
