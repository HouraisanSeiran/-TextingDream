'use strict';
const growthCard=el('div',undefined,'card');
growthCard.innerHTML='<h3>当前旅程 · 角色发展</h3><p>依据角色经历生成候选，允许保持不变。批准只影响本旅程，因果合理性由作者审核；继续游玩后旧候选会过期。</p><div class="toolbar"><button id="growth-load">读取旅程角色</button><select id="growth-character"></select></div><textarea id="growth-instruction" rows="2" maxlength="2000" placeholder="希望重点评估哪些经历？不填写则评估是否需要变化。"></textarea><button id="growth-generate">评估角色发展</button><div id="growth-results"></div>';
$('inner').append(growthCard);
async function growthRefresh(){
 if(!current)throw Error('请先选择一个旅程');
 const data=await api('/inner/sessions/'+current.id+'/development');
 const box=$('growth-results');box.replaceChildren();
 const state=el('details');state.append(el('summary','本旅程已批准的发展'),el('pre',JSON.stringify(data.state,null,2)));box.append(state);
 for(const d of data.drafts.slice().reverse()){
  const item=el('details');item.append(el('summary',d.proposal.character_id+' · '+d.status),el('p',d.validation),el('pre',JSON.stringify({proposal:d.proposal,evidence:d.context.evidence},null,2)));
  if(d.status==='pending')for(const [a,label]of [['approve','批准并写入旅程'],['reject','拒绝']])item.append(button(label,async()=>{await api('/inner/development/'+d.id+'/'+a,'POST');await growthRefresh()}));
  box.append(item);
 }
}
$('growth-load').onclick=()=>safe(async()=>{if(!current)throw Error('请先选择一个旅程');const p=await api('/inner/package?revision='+current.revision);$('growth-character').replaceChildren(...p.characters.characters.map(c=>{const o=el('option',c.name);o.value=c.id;return o}));await growthRefresh()});
$('growth-generate').onclick=()=>safe(async()=>{if(!current||!$('growth-character').value)throw Error('请先读取旅程角色');const b=$('growth-generate');b.disabled=true;try{await api('/inner/sessions/'+current.id+'/development','POST',{character_id:$('growth-character').value,instruction:$('growth-instruction').value.trim()||'根据实际经历判断是否需要变化；允许保持不变。'});await growthRefresh()}finally{b.disabled=false}});
