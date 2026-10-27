'use strict';
// Loaded after existing deferred scripts; surface data contains no hidden NPC attributes.
window.addEventListener('DOMContentLoaded',()=>{
 const card=el('details');card.id='world-systems';card.className='card';
 card.append(el('summary','我的属性与当地环境'));
 const body=el('div');card.append(body);$('surface-journeys').after(card);
 const names={talent:'天赋',strength:'力量',agility:'敏捷',wisdom:'智慧',social:'社交',resilience:'韧性'};
 // Public holdings only: labels and balances the engine already disclosed. Everything is
 // written with textContent (el()), never innerHTML, so author-supplied names cannot
 // inject markup. Unidentified items show only what the engine disclosed about them.
 function drawRewards(){
  const r=current.rewards;if(!r)return; // 未配置奖励的故事包不显示这一段
  if(r.wallet.length)body.append(el('p','钱货：'+r.wallet.map(w=>`${w.name} ${w.amount}${w.unit||''}`).join(' · ')));
  if(r.items.length){
   const list=el('details');list.open=true;list.append(el('summary',`随身物品（${r.items.length}）`));
   for(const item of r.items){
    const row=el('div');const hidden=item.identified===false;
    // Public figures are a visible estimate, not a settled value: label them so nobody
    // reads "伤害/价值" as the item's complete adjudicated numbers.
    const bits=[item.label,hidden?'未鉴定':'',hidden?'':item.material,hidden?'':item.quality,
                `重 ${item.weight}`,hidden?'':`已知耐久 ${item.durability}`,
                hidden?'':`已知伤害 ${item.damage}`,hidden?'':`估值 ${item.value}`];
    row.append(el('p',bits.filter(Boolean).join(' · ')));
    if(!hidden&&item.figures==='visible_estimate')row.append(el('small','以上为可见估值，不含未披露的效果；不是最终裁定值'));
    if(item.enchantments&&item.enchantments.length)row.append(el('small','附魔：'+item.enchantments.map(e=>`${e.name} ${e.level}级`).join('、')));
    if(item.mana&&item.mana.capacity)row.append(el('small',`魔力 ${item.mana.charge}/${item.mana.capacity}`));
    list.append(row);
   }
   body.append(list);
  }
  if(r.abilities.length)body.append(el('p','已掌握：'+r.abilities.map(x=>x.name).join(' · ')));
 }
 function draw(){body.replaceChildren();if(!current){body.append(el('p','选择旅程后显示。'));return}
  const a=current.abilities;if(a){body.append(el('p',Object.entries(a.values).map(([k,v])=>`${names[k]||k} ${v}`).join(' · ')),el('p',`血量 ${a.health.current}/${a.health.maximum}`))}
  drawRewards();
  const g=current.geography;if(g){if(g.coordinates)body.append(el('p','经度、纬度：'+g.coordinates.join(', ')));if(g.environment)body.append(el('p',`海拔 ${g.environment.elevation_m}m · 流域 ${g.environment.basin||'未设定'} · 自然沃土 ${g.estimates.fertile_soil_km2}km² · 区域承载 ${g.estimates.population_capacity}人（估计）`));if(g.sun){const s=g.sun,f=v=>v?`${v.time}${v.day_offset?'（相对日期'+(v.day_offset>0?'+':'')+v.day_offset+'天）':''}`:'—';body.append(el('p',s.polar==='polar_day'?'极昼':s.polar==='polar_night'?'极夜':`日出 ${f(s.sunrise)} · 日落 ${f(s.sunset)} · 日长 ${s.daylight_hours}小时`),el('small',s.basis))}}
 }
 const previous=render;render=function(){previous();draw()};draw();
 const panel=el('details');panel.id='world-pipeline-panel';panel.open=true;
 panel.innerHTML=`<summary>分阶段生成故事包</summary><p>粗地形 → 细化地形 → 自然资源与沃土 → 地缘政治实体。每次只生成下一阶段；修改上游会清除下游草稿。</p><label>世界名称<input id="pipeline-title" value="我的架空世界" maxlength="80"></label><label>自然区域数<input id="pipeline-count" type="number" min="2" max="5" value="3"></label><label>设定要求<textarea id="pipeline-instruction" rows="3" maxlength="4000" placeholder="大陆形状、气候、时代或必须保留的设定"></textarea></label><div class="toolbar"><button id="pipeline-create">建立分阶段草稿</button><button id="pipeline-load">读取草稿列表</button><select id="pipeline-list" aria-label="分阶段草稿"></select></div><p id="pipeline-status" role="status"></p><div class="toolbar"><button id="pipeline-next" disabled>生成下一阶段</button><button id="pipeline-save" disabled>保存为故事包</button></div><select id="pipeline-stage" aria-label="查看生成阶段"></select><textarea id="pipeline-json" rows="18" spellcheck="false"></textarea><button id="pipeline-edit" disabled>保存阶段编辑（清除下游）</button><div id="pipeline-map"></div>`;
 $('world-creation-form').before(panel);
 const atlas=atlasViewer($('pipeline-map'));let selected=null;
 async function display(p){selected=p;$('pipeline-status').textContent=p.status==='saved'?'已保存到StoryPackage':`已完成 ${p.stages.length}/4 阶段`;$('pipeline-next').disabled=p.stages.length>=4||p.status==='saved';$('pipeline-save').disabled=p.stages.length!==4||p.status==='saved';$('pipeline-edit').disabled=!p.stages.length||p.status==='saved';$('pipeline-stage').replaceChildren(...p.stages.map((s,i)=>new Option(`${i+1}. ${s.name}`,i)));$('pipeline-stage').value=String(Math.max(0,p.stages.length-1));stage();atlas.update(await api('/inner/world-pipelines/'+p.id+'/atlas'))}
 function stage(){$('pipeline-json').value=selected?.stages[$('pipeline-stage').value]?JSON.stringify(selected.stages[$('pipeline-stage').value].data,null,2):''}
 $('pipeline-stage').onchange=stage;
 async function refresh(){const ps=await api('/inner/world-pipelines');$('pipeline-list').replaceChildren(...ps.map(p=>new Option(p.request.title+' · '+p.stages.length+'/4',p.id)));return ps}
 $('pipeline-load').onclick=()=>safe(async()=>{const ps=await refresh();if(ps.length)await display(ps[ps.length-1])});
 $('pipeline-list').onchange=()=>safe(async()=>{const id=$('pipeline-list').value,ps=await api('/inner/world-pipelines');await display(ps.find(p=>p.id===id))});
 $('pipeline-create').onclick=()=>safe(async()=>{const p=await api('/inner/world-pipelines','POST',{title:$('pipeline-title').value,instruction:$('pipeline-instruction').value,regions:Number($('pipeline-count').value)});await refresh();$('pipeline-list').value=p.id;await display(p)});
 $('pipeline-next').onclick=()=>safe(async()=>{if(!selected)return;$('pipeline-next').disabled=true;$('pipeline-status').textContent='正在生成下一阶段…';try{await display(await api('/inner/world-pipelines/'+selected.id+'/next','POST'))}finally{$('pipeline-next').disabled=selected.stages.length>=4||selected.status==='saved'}});
 $('pipeline-edit').onclick=()=>safe(async()=>{await display(await api('/inner/world-pipelines/'+selected.id,'PUT',{index:Number($('pipeline-stage').value),data:JSON.parse($('pipeline-json').value)}))});
 $('pipeline-save').onclick=()=>safe(async()=>{const r=await api('/inner/world-pipelines/'+selected.id+'/save','POST');selected.status='saved';await display(selected);$('pipeline-status').textContent='已保存：StoryPackage/'+r.folder;await refreshGenerators()});
});
