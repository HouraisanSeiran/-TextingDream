$('surface-thinking').parentElement.lastChild.textContent=' 启用模型推理（服务支持时生效）';
const recallOptions=el('div');
recallOptions.innerHTML='<label><input id="recall-enabled" type="checkbox" checked> 按需检索旧对话</label><label>记忆相关性阈值<input id="recall-threshold" type="number" min="0.05" max="0.9" step="0.01" value="0.12"></label><small>本地 TF-IDF 文本向量，无额外 API 消耗。近期上下文照常保留，旧原文只在相关时召回；不是通用语义嵌入。</small>';
$('settings-form').prepend(recallOptions);
const stageOptions=el('div');
stageOptions.innerHTML='<label>历史发送方式<select id="history-strategy"><option value="staged">阶段内追加（推荐）</option><option value="sliding">仅最近几轮</option></select></label><label>每阶段最多轮数<input id="stage-turns" type="number" min="6" max="40" value="16"></label><label>每阶段历史字符上限<input id="stage-chars" type="number" min="1200" max="16000" value="6000"></label><small>达到轮数或字符上限时建立新阶段，保留短原文摘录；完整聊天仍保存在本地。阶段历史最多使用总上下文预算的三分之一。上方“保留轮数”仅用于最近几轮模式。缓存由服务端决定，不承诺每次命中。</small>';
$('settings-form').prepend(stageOptions);
function fillStageSettings(p){$('history-strategy').value=p.history_strategy||'staged';$('stage-turns').value=p.stage_turns||16;$('stage-chars').value=p.stage_chars||6000;}
function stageSettings(){return {history_strategy:$('history-strategy').value,stage_turns:Number($('stage-turns').value),stage_chars:Number($('stage-chars').value)};}
const cacheSummary=el('div',undefined,'card');cacheSummary.id='cache-summary';
$('traces').querySelector('.toolbar').after(cacheSummary);
function showCacheSummary(records){
 const remote=records.filter(t=>t.status!=='offline'&&t.status!=='blocked');const known=remote.filter(t=>t.cache?.reported);
 const sum=k=>known.reduce((n,t)=>n+(t.cache[k]||0),0);const input=sum('input_tokens');
 cacheSummary.textContent=`当前筛选 / 最近保留记录：${remote.length} 次远程调用；已报告缓存 ${known.length} 次，未知 ${remote.length-known.length} 次。输入 ${input.toLocaleString()}；命中 ${sum('hit_tokens').toLocaleString()}；未命中 ${sum('miss_tokens').toLocaleString()}；加权命中率 ${input?(100*sum('hit_tokens')/input).toFixed(2)+'%':'—'}；这些调用的输出 ${sum('output_tokens').toLocaleString()}。不是账户全量账单。`;
}
const batch=el('div',undefined,'card');
batch.innerHTML='<h3>并发创作</h3><p>同时生成背景知识和道具，各自保存为候选；等待时也可前往表层对话。</p><textarea id="batch-instruction" rows="3" maxlength="3500" placeholder="例如：为边城集市补充商贸背景和一件当地器物"></textarea><button id="batch-generate">生成背景 + 道具</button><pre id="batch-result"></pre>';
$('generate-form').after(batch);
$('batch-generate').onclick=()=>safe(async()=>{const instruction=$('batch-instruction').value.trim();if(!instruction)throw Error('请填写创作要求');$('batch-generate').disabled=true;try{const r=await api('/inner/generate-batch','POST',{tasks:[{kind:'fact',instruction:'生成背景知识，区分事实和传闻：'+instruction},{kind:'item',instruction:'生成完整道具及可见性：'+instruction}]});$('batch-result').textContent=r.results.map(x=>x.error?x.kind+'：失败，'+x.error:x.kind+'：候选已保存 '+x.draft.id).join('\n');await refreshInner()}finally{$('batch-generate').disabled=false}});
const recallPanel=el('div',undefined,'card');
recallPanel.innerHTML='<h3>聊天记忆检索 · 里层查看</h3><input id="recall-query" maxlength="3000" placeholder="第一次做的炒肉和白粥好不好吃"><button id="recall-search">查找当前旅程原文</button><pre id="recall-result"></pre>';
batch.after(recallPanel);
$('recall-search').onclick=()=>safe(async()=>{if(!current)throw Error('请先打开一个旅程');const r=await api('/inner/sessions/'+current.id+'/recall?query='+encodeURIComponent($('recall-query').value));$('recall-result').textContent=JSON.stringify(r,null,2)});
// 输入方式（#input-channel）与「资源与时间」（#local-state）已在 index.html 的对话栏里；这里只管渲染。
function drawLocalState(state){
 const box=$('local-state');box.replaceChildren();
 if(!state){box.append(el('p','当前故事包没有定义资源与日程。','muted'));return}
 const c=state.clock||{};
 if(c.day!==undefined)box.append(el('p','第 '+c.day+' 天 · '+String(c.hour).padStart(2,'0')+':00'+(c.elapsed_hours!==undefined?' · 已过 '+c.elapsed_hours+' 小时':''),'ls-clock'));
 for(const r of state.resources||[]){
  const row=el('div',undefined,'ls-row');row.append(el('span',r.name),el('strong',r.amount+(r.unit||'')+(r.maximum?' / '+r.maximum:'')));
  if(r.maximum){const bar=el('i',undefined,'ls-bar');bar.style.setProperty('--fill',Math.max(0,Math.min(100,100*r.amount/r.maximum))+'%');row.append(bar)}
  box.append(row);
 }
 if((state.upcoming||[]).length){box.append(el('p','即将发生','rail-label'));for(const t of state.upcoming.slice(0,4))box.append(el('p',t.title+' · '+t.in_hours+' 小时后','ls-line'))}
 if((state.notices||[]).length){box.append(el('p','最近消息','rail-label'));for(const n of state.notices.slice(-3))box.append(el('p',n.text,'ls-line'))}
}
const renderBeforeLocal=render;
render=function(){renderBeforeLocal();if(!current)return;drawLocalState(current.local_state);$('wait-local').disabled=!!current.event;$('wait-hint').hidden=!current.event;};
$('wait-local').onclick=()=>safe(async()=>{if(!current)throw Error('请先打开旅程');current=await api('/sessions/'+current.id+'/wait','POST',{hours:Number($('wait-hours').value)});render();notice('时间已由本地推进，未调用模型')});
const rulesEditor=el('details');rulesEditor.innerHTML='<summary>本地资源与日程规则 · 作者配置</summary><p>不调用AI。保存为故事包新版本；新旅程使用新规则，已有旅程保持原版本。跨午夜日程需拆为两段，资源数量为整数。</p><button id="load-local-rules">读取规则</button><button id="example-local-rules">填入测试示例（未保存）</button><textarea id="local-rules-json" rows="16" spellcheck="false"></textarea><button id="save-local-rules">校验并保存新版本</button>';
$('inner').append(rulesEditor);
$('load-local-rules').onclick=()=>safe(async()=>{$('local-rules-json').value=JSON.stringify((await api('/inner/local-rules')).rules,null,2)});
$('example-local-rules').onclick=()=>{$('local-rules-json').value=JSON.stringify({resources:[{id:'supplies',name:'测试补给',unit:'份',initial:24,maximum:100,per_hour:-1}],schedules:[{id:'notice',title:'测试驿站通知',at:12,every:24,public:true,effects:[{op:'notice',text:'驿站发出例行报时。',visible:true}]}],routines:[],turn_hours:1,travel_hours:4,memory_limit:200},null,2)};
$('save-local-rules').onclick=()=>safe(async()=>{const r=await api('/inner/local-rules','PUT',JSON.parse($('local-rules-json').value));notice('规则已保存，新旅程使用版本 '+r.revision);await refreshInner()});
