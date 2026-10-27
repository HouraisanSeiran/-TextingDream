'use strict';
// Town authoring panel. Every value is written with textContent (el()), never innerHTML
// with data, so a town name from a package cannot inject markup. The JSON editor is the
// advanced path; the readable view is the default for reviewing a stage.
const townPanel=el('section',undefined,'page');townPanel.id='towns';townPanel.hidden=true;
townPanel.innerHTML=`<div class="intro"><h2>城镇创作</h2><p>单城镇四阶段：聚落骨架 → 社会经济 → 建筑与特殊地点 → 故事候选。生成由本地固定规则完成，不调用语言模型，同一世界版本、地形输入、社会档位与 seed 得到同一座城镇。</p></div>
<div class="two-col"><div>
<form id="town-create-form" class="card"><h3>从预置输入开始</h3>
<label>地形与社会样本<select id="town-preset"><option value="wet_valley">湿润河谷农业</option><option value="cold_mountain_mine">寒冷山地矿业</option><option value="arid_oasis_route">干旱商路绿洲</option></select></label>
<label>种子（可复现）<input id="town-seed" value="town_seed_01" maxlength="64"></label>
<label>显示名（留空用样本默认名）<input id="town-site" maxlength="80"></label>
<div class="toolbar"><button class="primary" type="submit">生成四阶段草稿</button><button id="town-reload" type="button">刷新草稿列表</button></div>
<p id="town-status" class="muted" role="status"></p></form>
<div class="card"><h3>草稿</h3><div id="town-list"></div></div>
<div class="card"><h3>已发布版本</h3><div id="town-versions"></div></div>
</div><div>
<h3 id="town-heading">选择或新建草稿</h3>
<div id="town-summary"></div>
<label>阶段<select id="town-stage"></select></label>
<div class="toolbar"><button id="town-advance" disabled>重新生成此阶段</button><button id="town-validate" disabled>校验</button><button id="town-publish" disabled>发布为不可变版本</button></div>
<details open><summary>阶段数据（高级编辑）</summary><p class="muted">保存上游阶段会把下游阶段标为失效，不会保留悬空引用；必须重新生成后才可发布。</p><textarea id="town-json" rows="20" spellcheck="false"></textarea><div class="toolbar"><button id="town-save-stage" disabled>保存阶段编辑（清除下游）</button><button id="town-export" disabled>导出此版本 JSON</button></div></details>
<p id="town-notice" class="muted"></p>
</div></div>`;
document.querySelector('main').append(townPanel);

// A nav button added after app.js bound its handlers needs its own binding.
const townNav=el('button');
townNav.dataset.page='towns';
townNav.append(el('span','▦ 城镇创作'),el('small','作者'));
townNav.onclick=()=>safe(()=>showPage('towns'));
document.querySelector('nav').insertBefore(townNav,document.querySelector('nav button[data-page="traces"]'));

const townShowPage=showPage;
showPage=async function(id){await townShowPage(id);if(id!=='towns')return;
 $('page-title').textContent='城镇创作';$('breadcrumb').textContent='工作空间 / 城镇创作';
 await refreshTowns();await refreshTownVersions()};

let townDrafts=[],townVersions=[],activeTown=null;

const TOWN_STAGE_LABEL={skeleton:'1. 聚落骨架',socioeconomy:'2. 社会经济',built:'3. 建筑与特殊地点',story:'4. 故事候选'};
const TOWN_LABEL={port:'港口',market_town:'集镇',caravan_stop:'商路驿站',mining_town:'矿业镇',farm_town:'农业镇',religious_center:'宗教中心',pass_fortress:'山口关城',village:'村落',hamlet:'小型聚落',town:'乡镇',city:'城市',
 small_town:'小镇',river:'河流',spring:'泉水',lake:'湖泊',well_field:'井群',aquifer:'引水渠',none:'无',
 gable_tile:'瓦屋面',steep_slate:'陡坡石板',flat_mud:'平土屋面',gable_thatch:'草顶',monopitch:'单坡',hip_tile:'庑殿瓦',
 open_gutter:'明沟',stone_channel:'石砌渠',soak_pit:'渗井',covered_sewer:'暗沟',
 guild_board:'行会理事会',company_board:'矿场董事会',temple_authority:'祠庙主事',military_governor:'军政守备',council:'推举议会',elder_council:'长老议事',assembly:'全体议事'};
const label=v=>TOWN_LABEL[v]||v;

function townLine(parent,text,cls){parent.append(el('p',text,cls))}

function drawTownSummary(){
 const box=$('town-summary');box.replaceChildren();
 if(!activeTown){townLine(box,'左侧新建或选择一个草稿。',"muted");return}
 const head=activeTown.preview;
 if(!head){townLine(box,'阶段尚未齐全，无法生成公开投影。请先推进失效的阶段。',"muted");return}
 const card=el('div',undefined,'card');
 card.append(el('h3',`${head.name} · ${head.type_label}`),
  el('p',`${head.region} · ${head.founded_period}｜建于：${head.founded_reason}`,'prose'),
  el('p',`社会档位：${head.social_mode==='realistic_reference'?'现实参考档（含证据等级与不确定性）':'艺术夸张档（现实原型＋创作归纳）'}`));
 card.append(el('p',`人口约 ${head.population.total} 人（规则估计，不是普查）`));
 card.append(el('p','组群：'+head.population.groups.map(g=>`${g.label} ${(g.share_permille/10).toFixed(1)}%`).join(' · ')));
 card.append(el('p',`治理：${head.governance.form} —— ${head.governance.authority}`));
 card.append(el('p',`水源：${head.water.source_label||label(head.water.source)} · ${head.water.storage}｜通路：`+head.roads.map(r=>`${r.name}（${r.destination}，${r.travel_days}天，年封${r.seasonal_closed_days}天）`).join('；')));
 if(head.chains.length)card.append(el('p','生产链：'+head.chains.map(c=>`${c.name} ${c.amount}${c.unit}/${c.period} → ${c.consumers}`).join('；')));
 if(head.trade.length)card.append(el('p','进出：'+head.trade.map(t=>`${t.direction==='import'?'进口':'外销'} ${t.name} ${t.amount}${t.unit}/${t.period}（${t.via}）`).join('；')));
 card.append(el('p',`建筑：${head.style.materials.join('、')}｜屋面 ${label(head.style.roof)}｜排水 ${label(head.style.drainage)}`));
 card.append(el('p',head.style.wall_note,'muted'));
 const causes=el('details');causes.append(el('summary','为什么是这样（因果解释）'));
 for(const c of head.style.explanations||[])causes.append(el('p',`${c.claim}：${c.because.join('；')}`,'prose'));
 card.append(causes);
 if(head.districts.length)card.append(el('p','街区：'+head.districts.map(d=>`${d.name}（${d.materials.join('/')}·${label(d.roof)}·${label(d.drainage)}·${d.storeys}层）`).join('；')));
 if(head.facilities.length)card.append(el('p','代表性设施：'+head.facilities.map(f=>f.name).join('、')));
 card.append(el('p',`住房：${head.housing.total_houses} 户（${head.housing.basis}）`,'muted'));
 if(head.special_sites.length)card.append(el('p','特殊地点（公开）：'+head.special_sites.map(s=>`${s.name}（${s.status}）`).join('、')));
 if(head.warnings.length){const w=el('details');w.append(el('summary',`提示（${head.warnings.length}）`));for(const x of head.warnings)w.append(el('p',x,'muted'));card.append(w)}
 card.append(el('p','玩家投影只含公开字段：秘密、隐藏目标与封闭地点不在这里，也不会进入模型上下文。','muted'));
 box.append(card);
}

function drawTownDrafts(){
 const box=$('town-list');box.replaceChildren();
 if(!townDrafts.length){townLine(box,'还没有城镇草稿。',"muted");return}
 for(const d of townDrafts.slice().reverse()){
  const b=button(d.site||d.id,()=>selectTown(d.id),'draft');
  const done=d.stages.filter(s=>!s.stale).length;
  b.append(el('small',`${done}/4 阶段 · 版本 r${d.revision}${d.published.length?' · 已发布 '+d.published.length:''}`));
  if(d.id===activeTown?.id)b.classList.add('selected');
  box.append(b);
 }
}

async function selectTown(id){
 const d=await api('/inner/towns/'+id);activeTown=d;
 let preview=null,previewError='';
 try{preview=await api('/inner/towns/'+id+'/preview?audience=public')}catch(error){previewError=error.message}
 activeTown.preview=preview;activeTown.previewError=previewError;
 $('town-heading').textContent=(d.input&&d.input.site_name)||id;
 const stage=$('town-stage');const current=stage.value;
 stage.replaceChildren(...d.stages.map(s=>new Option(`${TOWN_STAGE_LABEL[s.name]||s.name}${s.stale?' · 已失效':''}`,s.name)));
 if(current)stage.value=current;
 drawStage();drawTownSummary();drawTownDrafts();
 const published=d.published.length>0;
 for(const n of ['town-advance','town-validate','town-publish','town-save-stage','town-export'])
  $(n).disabled=n==='town-export'?!published:(!d.stages.length);
 $('town-advance').disabled=!d.stages.some(s=>s.stale);
 $('town-notice').textContent=published?`已发布 ${d.published.join('、')}；继续修改会形成新版本，旧版本与旧旅程不受影响。`:'尚未发布。';
}

function drawStage(){
 const name=$('town-stage').value;
 const row=activeTown?.stages?.find(s=>s.name===name);
 $('town-json').value=row&&row.data?JSON.stringify(row.data,null,2):'';
 $('town-save-stage').disabled=!row||row.stale;
}

$('town-stage').onchange=drawStage;

async function refreshTowns(){townDrafts=await api('/inner/towns');drawTownDrafts()}
async function refreshTownVersions(){
 townVersions=await api('/inner/town-versions');const box=$('town-versions');box.replaceChildren();
 if(!townVersions.length){townLine(box,'还没有已发布版本。',"muted");return}
 for(const v of townVersions.slice().reverse()){
  const d=el('details');d.append(el('summary',`${v.name} · ${v.id}`),
   el('p',`内容哈希 ${v.content_hash.slice(0,12)}｜seed ${v.seed}｜基础故事包 ${v.base_story_revision.slice(0,8)}｜绑定 ${v.bindings.length}`,'muted'));
  const sel=el('select');sel.setAttribute('aria-label','绑定到地点');
  sel.append(new Option('不绑定地点（仅作库里记录）',''));
  try{const current=await api('/inner/package');
   for(const place of current.story.locations||[])sel.append(new Option(place.name,place.id));
   const info=el('p',`当前故事包版本 ${current.id.slice(0,8)}`,'muted');
   d.append(info);
   d.append(button('把此版本采纳进当前故事包',async()=>{
    const r=await api('/inner/town-versions/'+v.id+'/adopt','POST',{version_id:v.id,expected_story_revision:current.id,location_id:sel.value||null});
    notice(r.reused?'该版本已在该故事包中，本次只补齐索引':'已采纳，生成故事包新版本 '+r.revision.slice(0,8));
    await refreshTownVersions();
   },'primary'));
  }catch(error){d.append(el('p',error.message,'muted'))}
  d.append(el('label','绑定地点'),sel);
  const preview=el('div');formatReader(preview,v);d.append(preview);
  box.append(d);
 }
}

$('town-create-form').onsubmit=e=>{e.preventDefault();safe(async()=>{
 const b=$('town-create-form').querySelector('button');
 b.disabled=true;$('town-status').textContent=' 正在按固定规则生成四阶段…';
 try{
  const preset=$('town-preset').value;
  const d=await api('/inner/towns/presets/'+preset,'POST',{preset,seed:$('town-seed').value,site_name:$('town-site').value});
  await refreshTowns();await selectTown(d.id);
  $('town-status').textContent=` 已生成 ${d.stages.length} 个阶段；提示 ${d.warnings.length} 条。`;
 }finally{b.disabled=false}
})};

$('town-reload').onclick=()=>safe(async()=>{await refreshTowns();await refreshTownVersions();notice('已刷新')});

$('town-advance').onclick=()=>safe(async()=>{
 if(!activeTown)return;
 $('town-advance').disabled=true;
 try{const d=await api('/inner/towns/'+activeTown.id+'/next','POST',{expected_revision:activeTown.revision});
  await refreshTowns();await selectTown(d.id);
  $('town-notice').textContent='已按当前输入重新生成所选阶段（一次只推进一个阶段）。';
 }finally{$('town-advance').disabled=false}
});

$('town-validate').onclick=()=>safe(async()=>{
 if(!activeTown)return;
 const preview=await api('/inner/towns/'+activeTown.id+'/preview?audience=public');
 activeTown.preview=preview;drawTownSummary();
 notice(`结构校验通过；提示 ${(preview.warnings||[]).length} 条`);
});

$('town-save-stage').onclick=()=>safe(async()=>{
 if(!activeTown)return;
 const name=$('town-stage').value;
 const d=await api('/inner/towns/'+activeTown.id+'/stages','PUT',{stage:name,expected_revision:activeTown.revision,data:JSON.parse($('town-json').value)});
 await refreshTowns();await selectTown(d.id);
 $('town-notice').textContent='已保存并清除下游阶段；请重新生成再发布。';
});

$('town-publish').onclick=()=>safe(async()=>{
 if(!activeTown)return;
 const r=await api('/inner/towns/'+activeTown.id+'/publish','POST',{expected_revision:activeTown.revision});
 notice(r.reused?'内容相同，复用已发布的不可变版本':'已发布新版本 '+r.version.id);
 await refreshTowns();await refreshTownVersions();await selectTown(activeTown.id);
});

$('town-export').onclick=()=>safe(async()=>{
 if(!activeTown||!activeTown.published.length)throw Error('请先发布版本');
 const v=await api('/inner/town-versions/'+activeTown.published.at(-1));
 jsonDownload(v,'town-'+v.id+'.json');
});

function townStageReady(){return !!(activeTown&&activeTown.stages.length)}
drawTownSummary();
