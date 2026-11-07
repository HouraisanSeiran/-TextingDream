'use strict';
const $=id=>document.getElementById(id);
let token='',current=null,draftId=null,page='surface',apiConfig={},drafts=[];
let selectedConversation=null, selectedTrace=null, traceRecord=null;

/* ---------------------------------------------------------------- 导航（唯一入口）
 * 旧脚本曾各自包一层 showPage，越包越容易互相吞掉。这里换成一个注册表：
 *   TDNav.register(id,{title,play,enter})  声明页面
 *   TDNav.alias(from, fn)                 旧 id 重定向
 *   TDNav.show(id)                        唯一的页面切换入口
 * showPage 保留为全局函数并转调 TDNav.show，所以还没改写的旧调用点行为不变。
 */
const TDNav=(function(){
 const pages=Object.create(null),aliases=Object.create(null);
 function register(id,spec){pages[id]={title:(spec&&spec.title)||id,play:!!(spec&&spec.play),enter:spec&&spec.enter};return pages[id]}
 function alias(from,resolve){aliases[from]=resolve}
 function resolve(id){const seen=new Set();let next=id,before=null;
  while(aliases[next]&&!seen.has(next)){seen.add(next);const r=aliases[next](next);next=r&&r.page?r.page:r;before=(r&&r.before)||before}
  return {id:next,before}}
 function show(id){
  const hit=resolve(id);
  if(hit.before)hit.before();
  const spec=pages[hit.id]||{title:hit.id,play:false};
  page=hit.id;
  const playBox=$('play'),legacy=$('legacy');
  if(spec.play){
   if(legacy)legacy.hidden=true;
   if(playBox)playBox.hidden=false;
   document.querySelectorAll('#play > .page, #play-body .page, #play-left .page').forEach(p=>p.hidden=p.id!==hit.id);
  }else{
   if(playBox)playBox.hidden=true;
   if(legacy)legacy.hidden=false;
   document.querySelectorAll('#legacy .page').forEach(p=>p.hidden=p.id!==hit.id);
  }
  document.querySelectorAll('#legacy nav button').forEach(b=>b.classList.toggle('selected',b.dataset.page===hit.id));
  const title=spec.title||'工作台';
  if($('page-title'))$('page-title').textContent=title;
  if($('breadcrumb'))$('breadcrumb').textContent='工作空间 / '+title;
  if(spec.enter)return spec.enter(hit.id);
 }
 return {register,alias,show,resolve,pages:()=>Object.keys(pages)};
})();
window.TDNav=TDNav;
const PAGE_TITLES={surface:'表层对话',inner:'里层创作',notebook:'知识点记录簿','map-tools':'世界地图工具','world-workshop':'世界创作',towns:'城镇创作',elements:'元素装配',api:'API 配置',settings:'设置',traces:'模型输入输出'};
for(const [id,title]of Object.entries(PAGE_TITLES))TDNav.register(id,{title,play:id==='surface'});
const tracePage=document.createElement('section');tracePage.id='traces';tracePage.className='page';tracePage.hidden=true;
tracePage.innerHTML=`<div class="intro"><h2>模型输入输出</h2><p>实际模型请求与响应正文（密钥已隐藏）。包含里层隐藏设定，仅供作者调试。调试正文保留最近 200 次调用，用量统计独立保留 90 天。</p></div><div class="toolbar"><button id="refresh-traces">刷新</button><label><input id="auto-traces" type="checkbox" checked>自动刷新</label><select id="trace-filter"><option value="all">全部调用</option><option value="surface">表层</option><option value="inner">里层</option><option value="connection_test">连接测试</option><option value="polish">润色</option></select><label>统计窗口<select id="usage-window"><option value="1">1 小时</option><option value="24" selected>24 小时</option><option value="168">7 天</option></select></label><button id="export-trace">导出当前记录</button><button id="clear-traces">清空调试记录</button></div><div id="token-usage-summary" class="card muted">读取 token 统计中…</div><div class="two-col"><div id="trace-list"></div><div><p id="trace-meta" class="muted">选择一次调用。旧调用无法追溯，更新后的调用将自动记录。</p><h3>源输入 · 请求 JSON</h3><pre id="trace-input" class="card"></pre><h3>源输出 · 响应正文</h3><pre id="trace-output" class="card"></pre><h3>用量 / 错误 / 前缀指纹</h3><pre id="trace-details" class="card"></pre></div></div>`;
document.querySelector('main').append(tracePage);
const packageReader=document.createElement('div');packageReader.className='card';packageReader.innerHTML=`<h3>故事包阅读器</h3><p>查看世界观、主要场景、地点、事件、物品与独立角色包。补充草案和待定项在来源说明中标记。</p><div class="toolbar"><button id="read-current-package">打开最新故事包</button><button id="read-session-package">打开当前旅程版本</button></div><div id="package-reading" hidden></div>`;$('inner').prepend(packageReader);
function notice(text){$('notice').textContent=text;$('notice').hidden=false;clearTimeout(notice.timer);notice.timer=setTimeout(()=>$('notice').hidden=true,8000)}
async function api(path,method='GET',body){const r=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json','X-TextileDream-Token':token},body:body===undefined?undefined:JSON.stringify(body)});const j=await r.json();if(!r.ok)throw Error(typeof j.detail==='string'?j.detail:JSON.stringify(j.detail));return j}
async function safe(fn){try{await fn()}catch(e){notice(e.message)}}
function el(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e}
function button(text,fn,cls){const b=el('button',text,cls);b.addEventListener('click',()=>safe(fn));return b}
function jsonDownload(data,name){const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=el('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
function textDownload(text,name){const url=URL.createObjectURL(new Blob([text],{type:'text/markdown;charset=utf-8'}));const a=el('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
const conversationOptions=el('div');conversationOptions.innerHTML='<label>对话分章<select id="conversation-mode"><option value="chapter">长篇连续（减少新建）</option><option value="scene">每个主要场景新建</option></select></label><label>至少多少轮后允许换场景分章<input id="chapter-turns" type="number" min="12" max="200" value="40"></label><label><input id="surface-thinking" type="checkbox"> 表层启用 DeepSeek 推理（默认开启，仍需检查生成质量）</label><small>默认延续当前对话，达到轮数后在下次换场景分章；后台发送最近历史和相关知识，完整原文保留。推理开关仅适用于官方 V4 / Flash。</small>';$('settings-form').prepend(conversationOptions);
function prefs(p){fillStageSettings(p);$('recall-enabled').checked=p.recall_enabled!==false;$('recall-threshold').value=p.recall_threshold??0.12;document.body.classList.toggle('light',p.theme==='light');document.documentElement.style.setProperty('--read-size',p.font_size+'px');for(const [id,key] of [['theme','theme'],['font-size','font_size'],['memory-k','memory_k'],['history-turns','history_turns'],['context-chars','context_chars']])$(id).value=p[key];$('conversation-mode').value=p.conversation_mode||'chapter';$('chapter-turns').value=p.chapter_turns||40;$('surface-thinking').checked=!!p.surface_thinking}
async function bootstrap(){const b=await api('/bootstrap');token=b.token;window.__textileDreamToken=token;apiConfig=b.api;prefs(b.preferences);$('mode-label').textContent=b.api.offline?'离线测试':'已选择 '+b.api.model;if(typeof window.TDWorkspaceSync==='function')window.TDWorkspaceSync(b.sessions,b.api);return b}
// 空态（没有选中旅程）与有旅程时的正文区互斥：空态不显示任何只对旅程有意义的按钮。
function syncJourneyState(){const has=!!current;$('play-left').classList.toggle('has-journey',has);$('journey-empty').hidden=has}
function openNewDialog(){$('new-dialog').showModal()}
/* 作者 / 玩家模式切换（唯一入口）。
 * 原生宿主只在**作者模式**挂载；一旦进入或切到一段旅程（session），
 * 右侧就必须卸下作者宿主、不再请求 /api/inner/native-worlds。
 * 这不是权限开关（token 本身不代表该看全图），而是“这幅图属于谁”的契约：
 *   空态（没有旅程）= 作者在准备世界 → author
 *   有旅程 = 玩家在看自己已探索的范围 → player（独立的服务端掩膜底图）
 * 用一个显式事件通知 native-map.js，不靠定时轮询、不靠两边各自 bootstrap。
 */
function setNativeMode(mode){
 window.__tdNativeMode=mode;
 try{window.dispatchEvent(new CustomEvent('td-native-mode',{detail:{mode}}))}catch(e){/* 老浏览器忽略 */}
}
async function loadSession(id,navigate=true){setNativeMode('player');let next;try{next=await api('/sessions/'+id)}catch(error){if(!current)setNativeMode('author');throw error}current=next;selectedConversation=null;$('workspace-author-map').classList.remove('selected');localStorage.setItem('textiledream-session',id);render();await bootstrap();if(navigate){window.TDConversationDrawer?.open();await showPage('surface')}}
// 供原生地图与验收脚本用（不靠内联 onclick 能否访问 loadSession）
window.loadSession=loadSession;
window.setNativeMode=setNativeMode;
window.TDEnterAuthorMode=async function(){
 current=null;selectedConversation=null;setNativeMode('author');renderNotesSync();syncJourneyState();
 $('world-label').textContent='织梦';$('play-badge').textContent='故事手记';$('play-place').textContent='';
 $('conversation-summary').textContent='选择或新建一段旅程';
 $('event-title').textContent='';
 $('event-goal').textContent='';
 $('status-line').replaceChildren();$('story-text').replaceChildren();$('actions').replaceChildren();$('archives').replaceChildren();
 if(window.PlayUI)window.PlayUI.resetView();
 $('chat-form').hidden=true;$('actions').hidden=false;$('close-event').hidden=false;
 $('workspace-author-map').classList.add('selected');
 $('journey-list').querySelectorAll('button').forEach(b=>b.classList.remove('selected'));
 $('conversations').replaceChildren();$('chapter-label').hidden=true;
 window.TDConversationDrawer?.close();
 try{localStorage.removeItem('textiledream-session')}catch(e){}
 await showPage('surface');
};
function renderNotesSync(){
 let box=$('notes-sync-notice');
 if(!box){box=el('div');box.id='notes-sync-notice';box.setAttribute('role','status');$('chat-form').prepend(box)}
 box.hidden=current?.notes_sync?.status!=='pending';
 if(box.hidden)return;
 const sessionId=current.id;
 const retry=button('重试同步笔记',async()=>{
  retry.disabled=true;
  try{
   const result=await api('/sessions/'+encodeURIComponent(sessionId)+'/notes-sync','POST');
   if(current?.id===sessionId){current.notes_sync=result.notes_sync;renderNotesSync()}
  }finally{retry.disabled=false}
 });
 retry.type='button';
 box.replaceChildren(el('span',current.notes_sync.message||'旅程已保存，笔记待同步'),retry);
}
function render(){if(!current)return;renderNotesSync();syncJourneyState();$('world-label').textContent=current.world;$('event-title').textContent=current.event?.title||'这一章已告一段落';$('event-goal').textContent=current.event?.goal||'可以查看归档，或打开地图继续前往其他地点。';$('status-line').replaceChildren(...[current.status].filter(Boolean).map(s=>el('span',s)));const turns=current.turns.length?current.turns:current.archives.at(-1)?.turns||[];$('story-text').replaceChildren(...turns.map(t=>{const d=el('article',undefined,'turn');d.append(el('div',t.input,'input'),el('div',t.reply,'prose'));return d}));$('actions').replaceChildren(...current.actions.map(a=>button(a.label,()=>send(a.label,a.id))));$('close-event').disabled=!current.event||!current.turns.length;$('archives').replaceChildren(...current.archives.map(a=>{const d=el('details');d.append(el('summary',a.title),el('div',a.turns.map(t=>t.reply).join('\n\n'),'prose'),button('回到本事件起点',async()=>{if(!confirm('恢复到该事件起点，并移除其后的进度？'))return;current=await api('/sessions/'+current.id+'/rollback/'+a.id,'POST');render();notice('已恢复事件起点')}));return d}));if(!current.archives.length)$('archives').append(el('p','还没有已归档的事件。','muted'));if(typeof window.TDWorkspaceSyncCurrent==='function')window.TDWorkspaceSyncCurrent(current)}
let sending=false;
async function send(message,action_id=null){if(!current)throw Error('请先新建或选择旅程');if(sending)return;sending=true;const buttons=[...document.querySelectorAll('#actions button,#chat-form button')];buttons.forEach(b=>b.disabled=true);$('play-left').classList.add('is-sending');try{current=await api('/sessions/'+current.id+'/chat','POST',{message,action_id,channel:action_id?'action':$('input-channel').value});$('message').value='';$('message').dispatchEvent(new Event('input'));render();window.TDScrollStory?.(true)}finally{sending=false;$('play-left').classList.remove('is-sending');buttons.forEach(b=>b.disabled=false)}}
async function showPage(id){
 const hit=TDNav.resolve(id);
 if(hit.id==='notebook')await refreshNotebook();
 if(hit.id==='inner')await refreshInner();
 if(hit.id==='traces')await refreshTraces();
 if(hit.id==='api'){apiConfig=await api('/settings/api');fillApi()}
 if(hit.id==='settings')$('corpus').value=(await api('/inner/corpus')).text;
 return TDNav.show(id);
}
function fillApi(){resetModelPicker(apiConfig.model);$('api-url').value=apiConfig.base_url;$('api-protocol').value=apiConfig.protocol||'openai';const key=$('api-key');key.value='';key.placeholder=apiConfig.has_key?'留空保留此服务的密钥':'填写 API Key';key.title='更换服务时请填写对应的密钥';$('key-status').textContent=apiConfig.has_key?'密钥已配置；留空保留此服务的密钥。':'尚未配置密钥，本地免密服务可留空。'}
async function refreshInner(){drafts=await api('/inner/drafts');$('drafts').replaceChildren(...drafts.slice().reverse().map(d=>{const b=button(d.instruction,()=>selectDraft(d.id),'draft');b.append(el('small',(d.usage.mode==='offline'?'离线示例 · ':'')+d.status));return b}));const p=await api('/inner/package');$('package-json').value=JSON.stringify({story:p.story,characters:p.characters},null,2);const versions=await api('/inner/versions');$('versions').replaceChildren(...versions.reverse().map(v=>{const d=el('div');d.append(el('span',v.created.slice(0,16)+' · '+v.note+' '),button('恢复为新版本',async()=>{if(confirm('后续新旅程将采用此版本，已有旅程保持不变。')){await api('/inner/versions/'+v.id+'/restore','POST');await refreshInner();notice('版本已恢复')}}));return d}));if(draftId&&drafts.some(d=>d.id===draftId))selectDraft(draftId)}
function selectDraft(id){const d=drafts.find(d=>d.id===id);draftId=id;$('draft-title').textContent=d.instruction;$('draft-json').value=JSON.stringify(d.element,null,2);for(const n of ['save-draft','approve-draft','reject-draft'])$(n).disabled=d.status!=='draft'}
function svg(tag,attributes){const e=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attributes).forEach(([k,v])=>e.setAttribute(k,v));return e}
document.querySelectorAll('#legacy nav button').forEach(b=>b.onclick=()=>safe(()=>showPage(b.dataset.page)));
const renderOriginal=render;
render=function(){renderOriginal();if(!current)return;const groups=current.conversations||[];const selected=groups.find(c=>c.id===selectedConversation)||groups.find(c=>c.id===current.conversation_id)||groups.at(-1);const old=selected&&selected.id!==current.conversation_id;if(selected){$('story-text').replaceChildren(...selected.turns.map(t=>{const d=el('article',undefined,'turn');d.append(el('div',t.input,'input'),el('div',t.reply,'prose'));return d}));$('event-title').textContent=old?selected.title:current.current_scene||selected.title;$('event-goal').textContent=old?'已归档场景 · 只读':current.event?.goal||'本场景已完成，可前往下一主要场景。'}$('conversations').replaceChildren(...groups.map(c=>button(c.title,async()=>{selectedConversation=c.id;render();await showPage('surface')},c.id===selected?.id?'selected':'')));$('chapter-label').hidden=groups.length<2;$('conversations').hidden=groups.length<2;$('chat-form').hidden=!!old;$('actions').hidden=!!old;$('close-event').hidden=!!old;};
async function readPackage(revision){const p=await api('/inner/package'+(revision?'?revision='+encodeURIComponent(revision):''));const box=$('package-reading');box.hidden=false;box.replaceChildren(el('h2',p.story.title),el('p','版本 '+p.id+' · '+p.note,'muted'));const sections=[['世界观总概',p.story.worldview],['主要场景',p.story.major_scenes],['地点',p.story.locations],['事件链',p.story.events],['物品与规则',{items:p.story.items,mechanics:p.story.mechanics}],['独立角色包',p.characters]];for(const [title,data] of sections){const d=el('details');d.append(el('summary',title));if(title==='世界观总概')d.open=true;const content=el('div');formatReader(content,data);d.append(content);box.append(d)}const search=el('input');search.placeholder='筛选知识点：标题、分类、关键词、内容';search.id='knowledge-search';const list=el('div');list.id='knowledge-list';const draw=()=>{const q=search.value.trim().toLowerCase();list.replaceChildren(...(p.story.knowledge||[]).filter(k=>JSON.stringify(k).toLowerCase().includes(q)).map(k=>{const d=el('details');d.append(el('summary',k.category+' · '+k.title),el('p',k.keywords.join(' / ')+' · '+k.visibility+' · '+k.status,'muted'),el('div',k.content,'prose'));return d}))};search.oninput=draw;box.append(el('h3','按需读取的知识点'),search,list);draw()}

packageReader.querySelector('.toolbar').append(button('从文件夹重新读取',async()=>{const r=await api('/inner/package/reload','POST');await refreshInner();await readPackage();notice('已读取 StoryPackage 文档 · '+r.revision+'；已有旅程保留原版')}),button('下载故事包文档',async()=>{const d=await api('/inner/package/document');textDownload(d.text,'玄陆_故事包.md')}));
let notebookRecords=[];
function drawNotebook(){const q=$('notebook-search').value.trim().toLowerCase();const notes=notebookRecords.filter(n=>JSON.stringify(n).toLowerCase().includes(q));$('notebook-list').replaceChildren(...notes.map(n=>{const d=el('article',undefined,'card');d.append(el('h3',n.title),el('p',n.summary,'prose'),el('p',n.status+' · '+n.source.event,'muted'));const evidence=el('details');evidence.append(el('summary','查看对话原文'),el('div',n.content,'prose'));d.append(evidence);if(n.source.conversation)d.append(button('回看所在场景',async()=>{selectedConversation=n.source.conversation;render();await showPage('surface')}));return d}));if(!notes.length)$('notebook-list').append(el('p',current?'暂无匹配记录；表层对话产生后会自动记录。':'请先选择旅程。','muted'))}
async function refreshNotebook(){notebookRecords=current?await api('/sessions/'+current.id+'/notebook'):[];drawNotebook()}
$('notebook-search').oninput=drawNotebook;$('refresh-notebook').onclick=()=>safe(refreshNotebook);
function formatReader(parent,value){if(value===undefined){parent.append(el('p','未设置','muted'));return}if(value===null||typeof value!=='object'){parent.append(el('p',String(value)));return}if(Array.isArray(value)){for(const entry of value){const d=el('div',undefined,'reader-entry');formatReader(d,entry);parent.append(d)}return}const labels={premise:'总纲',laws:'世界硬规则',source_notes:'来源、补充草案与待定项',confirmed:'原文确认',provisional:'补充草案',open_questions:'待定',geopolitics:'政治与文明',belief_systems:'架空信仰',energy_system:'能量体系',travel_and_language:'旅行与语言',information_protocol:'信息可靠性',public_lore:'公开常识',title:'名称',name:'名称',description:'说明',information_scope:'内容范围',expected_turns:'预计轮次',kind:'类型'};for(const [key,v] of Object.entries(value)){parent.append(el('strong',labels[key]||key));const block=el('div',undefined,'reader-value');formatReader(block,v);parent.append(block)}}
$('read-current-package').onclick=()=>safe(()=>readPackage());$('read-session-package').onclick=()=>safe(async()=>{if(!current)throw Error('先选择旅程');await readPackage(current.revision)});
async function refreshTraces(){const data=await api('/inner/traces');const filtered=data.filter(t=>$('trace-filter').value==='all'||t.scope===$('trace-filter').value);showCacheSummary(filtered);const usage=await api('/inner/token-usage?hours='+encodeURIComponent($('usage-window').value));const u=usage.overall;
 const coverage=usage.coverage;
 const text=[`统计窗口 ${usage.window_hours} 小时：${u.calls} 次模型调用；输入 ${u.input_tokens??'未知'} / 输出 ${u.output_tokens??'未知'} token。`,
  `输入计量覆盖 ${u.input_usage_calls}/${u.calls} 次，输出计量覆盖 ${u.output_usage_calls}/${u.calls} 次；离线 ${u.offline_traces} 次，未发送 ${u.blocked_traces} 次。`,
  `窗口平均 ${u.total_tokens_per_hour??'未知'} token/小时；缓存命中率 ${u.cache_hit_rate===null?'未知':(u.cache_hit_rate*100).toFixed(1)+'%'}。`];
 if(coverage&&!coverage.window_complete)text.push('此窗口历史记录不完整；连续记录起点：'+new Date(coverage.complete_since).toLocaleString()+'。');
 text.push(usage.note);
 $('token-usage-summary').textContent=text.join(' '); $('trace-list').replaceChildren(...filtered.map(t=>{const b=button(t.scope+' · '+t.status,()=>openTrace(t.id),'draft');b.append(el('small',new Date(t.created).toLocaleString()+' · '+t.elapsed_ms+'ms'+(t.cache?.reported?' · 命中 '+(100*(t.cache.hit_rate||0)).toFixed(1)+'% · 未命中 '+t.cache.miss_tokens:' · 缓存用量未知')));return b}));if(!filtered.length)$('trace-list').append(el('p','暂无记录。发起一次对话或连接测试后在此查看。','muted'));if(selectedTrace&&!data.some(t=>t.id===selectedTrace)){selectedTrace=null;traceRecord=null;for(const id of ['trace-input','trace-output','trace-details'])$(id).textContent=''}if(!selectedTrace&&filtered.length)await openTrace(filtered[0].id)}
async function openTrace(id){selectedTrace=id;traceRecord=await api('/inner/traces/'+id);$('trace-meta').textContent=traceRecord.scope+' · '+traceRecord.status+' · '+(traceRecord.endpoint||'本地模拟');$('trace-input').textContent=JSON.stringify(traceRecord.request,null,2);$('trace-output').textContent=typeof traceRecord.response==='string'?traceRecord.response:JSON.stringify(traceRecord.response,null,2);$('trace-details').textContent=JSON.stringify({usage:traceRecord.usage,cache:traceRecord.cache,context_stats:traceRecord.context_stats,http_status:traceRecord.http_status,error:traceRecord.error,elapsed_ms:traceRecord.elapsed_ms,prefix_sha256:traceRecord.prefix_sha256,note:traceRecord.note},null,2)}
$('refresh-traces').onclick=()=>safe(refreshTraces);$('trace-filter').onchange=()=>safe(refreshTraces);$('usage-window').onchange=()=>safe(refreshTraces);$('export-trace').onclick=()=>{if(traceRecord)jsonDownload(traceRecord,'TextileDream-trace.json')};$('clear-traces').onclick=()=>safe(async()=>{if(confirm('清空已记录的模型输入输出？用量统计和存档会保留。')){await api('/inner/traces','DELETE');await refreshTraces()}});
let traceRefreshing=false;setInterval(()=>{if(page==='traces'&&$('auto-traces').checked&&!traceRefreshing){traceRefreshing=true;safe(refreshTraces).finally(()=>traceRefreshing=false)}},2000);
$('cancel-new').onclick=()=>$('new-dialog').close();
$('new-form').onsubmit=e=>{e.preventDefault();safe(async()=>{current=await api('/sessions','POST',{title:$('session-title').value,mode:$('session-mode').value});$('new-dialog').close();await loadSession(current.id)})};
$('chat-form').onsubmit=e=>{e.preventDefault();if($('message').value.trim())safe(()=>send($('message').value.trim()))};
$('message').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();$('chat-form').requestSubmit()}};
$('close-event').onclick=()=>safe(async()=>{current=await api('/sessions/'+current.id+'/close','POST');render()});
$('export-story').onclick=()=>{if(current)location.href='/api/sessions/'+current.id+'/export'};
const polishButton=button('润色并导出',async()=>{if(!current)throw Error('先选择旅程');polishButton.disabled=true;try{const result=await api('/sessions/'+current.id+'/polish','POST');textDownload(result.text,'TextileDream-polished.md');notice('已导出，原始归档保持不变')}finally{polishButton.disabled=false}});$('export-story').after(polishButton);
$('generate-form').onsubmit=e=>{e.preventDefault();safe(async()=>{const b=e.target.querySelector('button');b.disabled=true;try{const d=await api('/inner/generate','POST',{instruction:$('instruction').value,kind:$('kind').value});draftId=d.id;await refreshInner();notice('候选已保存，检查完整内容和公开字段后批准')}finally{b.disabled=false}})};
$('save-draft').onclick=()=>safe(async()=>{if(!draftId)throw Error('先选择候选');await api('/inner/drafts/'+draftId,'PUT',JSON.parse($('draft-json').value));await refreshInner();notice('候选已保存')});
$('approve-draft').onclick=()=>safe(async()=>{if(!draftId)throw Error('先选择候选');await api('/inner/drafts/'+draftId,'PUT',JSON.parse($('draft-json').value));await api('/inner/drafts/'+draftId+'/approve','POST');await refreshInner();notice('已生成新故事包版本；新建旅程即可使用')});
$('reject-draft').onclick=()=>safe(async()=>{await api('/inner/drafts/'+draftId+'/reject','POST');await refreshInner()});
$('save-package').onclick=()=>safe(async()=>{await api('/inner/package','PUT',JSON.parse($('package-json').value));await refreshInner();notice('已保存新版本')});
$('export-package').onclick=()=>safe(async()=>{const p=await api('/inner/package/export');jsonDownload({story:p.story,characters:p.characters},'TextileDream-package.json')});
$('import-package').onchange=e=>safe(async()=>{const f=e.target.files[0];if(f){const data=JSON.parse(await f.text());$('package-json').value=JSON.stringify({story:data.story,characters:data.characters},null,2);notice('已读入编辑框，点击保存新版本完成导入')}});
$('inspect').onclick=()=>safe(async()=>{if(!current)throw Error('先选择旅程');$('audit').textContent=JSON.stringify(await api('/inner/sessions/'+current.id),null,2)});
function connectionFields(){return {base_url:$('api-url').value.trim(),protocol:$('api-protocol').value,api_key:$('api-key').value}}
function apiForm(){const fields=connectionFields();return {...fields,...($('api-model').value?{model:$('api-model').value}:{})}}
function resetModelPicker(model=''){
 const select=$('api-model');select.replaceChildren();
 const option=el('option',model||'请先请求模型');option.value=model;select.append(option);select.disabled=true;
 $('models-status').textContent=model?'当前模型：'+model+'。可请求列表重新选择。':'请求可用模型后选择，点击保存配置生效。';
}
let connecting=false;
function connectionBusy(busy){connecting=busy;$('api-form').querySelectorAll('button,input,select').forEach(node=>node.disabled=busy);if(!busy)$('api-model').disabled=$('api-model').options.length<2}
async function requestModels(){
 if(connecting||!$('api-form').reportValidity())return;
 const fields=connectionFields();const previous=$('api-model').value;
 connectionBusy(true);$('models-status').textContent='正在请求可用模型…';
 try{
  const result=await api('/settings/connection/models','POST',fields);
  const select=$('api-model');select.replaceChildren(...result.models.map(model=>{const option=el('option',model);option.value=model;return option}));
  select.value=result.models.includes(previous)?previous:result.selected_model;
  $('models-status').textContent='已获取 '+result.models.length+' 个模型，选择后点击保存配置生效。';
 }catch(error){$('models-status').textContent=error.message;throw error}
 finally{connectionBusy(false)}
}
async function saveConnection(test=false){if(connecting||!$('api-form').reportValidity())return;const fields=apiForm();connectionBusy(true);try{apiConfig=await api('/settings/connection','PUT',fields);fillApi();await bootstrap();notice(test?(await api('/settings/api/test','POST')).message:'配置已保存，使用模型：'+apiConfig.model)}finally{connectionBusy(false)}}
$('api-form').onsubmit=e=>{e.preventDefault();safe(()=>saveConnection())};
$('request-models').onclick=()=>safe(requestModels);
for(const id of ['api-url','api-protocol','api-key'])$(id).addEventListener('input',()=>resetModelPicker());
$('test-api').onclick=()=>safe(()=>saveConnection(true));
$('clear-key').onclick=()=>safe(async()=>{if(connecting)return;connectionBusy(true);try{apiConfig=await api('/settings/api','PUT',{api_key:'',clear_key:true});fillApi();await bootstrap();notice('密钥已清除')}finally{connectionBusy(false)}});
$('settings-form').onsubmit=e=>{e.preventDefault();safe(async()=>{const p=await api('/settings/preferences','PUT',{...stageSettings(),recall_enabled:$('recall-enabled').checked,recall_threshold:Number($('recall-threshold').value),theme:$('theme').value,font_size:Number($('font-size').value),memory_k:Number($('memory-k').value),history_turns:Number($('history-turns').value),context_chars:Number($('context-chars').value),conversation_mode:$('conversation-mode').value,chapter_turns:Number($('chapter-turns').value),surface_thinking:$('surface-thinking').checked});prefs(p);notice('设置已保存')})};
$('save-corpus').onclick=()=>safe(async()=>{await api('/inner/corpus','PUT',{text:$('corpus').value});notice('通用语料已保存')});
window.addEventListener('DOMContentLoaded',()=>safe(async()=>{await bootstrap();setNativeMode('author');syncJourneyState();$('workspace-author-map').classList.add('selected');$('chat-form').hidden=true;}));

/* ---- 旅程存档管理：每条存档右侧的「⋯」菜单（重命名 / 删除）----
 * 列表由 play-ui.js 的 TDWorkspaceSync 整体重绘；这里用 MutationObserver 在每次重绘后
 * 给每条存档补一个行容器和「⋯」按钮，不改动列表渲染代码。标题一律走 textContent。 */
(function(){
 const list=$('journey-list');if(!list)return;
 let menu=null,opener=null,dlg=null,dlgForm=null,dlgInput=null,dlgError=null,dlgOk=null,dlgId=null;
 const sessionUrl=id=>'/sessions/'+encodeURIComponent(id);
 function closeMenu(restoreFocus){
  if(!menu)return;menu.remove();menu=null;
  if(opener){opener.setAttribute('aria-expanded','false');if(restoreFocus)opener.focus();opener=null}
 }
 function openMenu(button,id,title){
  closeMenu(false);
  opener=button;button.setAttribute('aria-expanded','true');
  menu=el('div',undefined,'journey-menu');menu.setAttribute('role','menu');
  const rename=el('button','重命名');const remove=el('button','删除','danger');
  for(const b of [rename,remove]){b.type='button';b.setAttribute('role','menuitem')}
  rename.onclick=()=>{closeMenu(false);openRename(id,title)};
  remove.onclick=()=>{closeMenu(false);safe(()=>removeSession(id,title))};
  menu.append(rename,remove);
  menu.addEventListener('keydown',e=>{
   if(e.key==='Tab'){closeMenu(true);return}
   if(e.key!=='ArrowDown'&&e.key!=='ArrowUp')return;
   e.preventDefault();const items=[rename,remove];const i=items.indexOf(document.activeElement);
   items[(i+(e.key==='ArrowDown'?1:items.length-1))%items.length].focus();
  });
  ($('play-left')||document.body).append(menu);
  const r=button.getBoundingClientRect();
  menu.style.top=Math.min(r.bottom+4,window.innerHeight-menu.offsetHeight-8)+'px';
  menu.style.left=Math.max(8,Math.min(r.right-menu.offsetWidth,window.innerWidth-menu.offsetWidth-8))+'px';
  rename.focus();
 }
 document.addEventListener('mousedown',e=>{if(menu&&!menu.contains(e.target)&&e.target!==opener)closeMenu(false)});
 /* Esc 只关菜单：先于对话抽屉的 Esc 处理（play-ui.js 稍后注册）拦下，避免抽屉一并折叠。 */
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&menu){e.preventDefault();e.stopImmediatePropagation();closeMenu(true)}});
 window.addEventListener('resize',()=>closeMenu(false));
 window.addEventListener('scroll',()=>closeMenu(false),true);

 function ensureDialog(){
  if(dlg)return dlg;
  dlg=document.createElement('dialog');dlg.id='rename-dialog';
  dlgForm=document.createElement('form');
  const label=el('label','存档名称');dlgInput=document.createElement('input');dlgInput.type='text';dlgInput.maxLength=80;dlgInput.required=true;label.append(dlgInput);
  dlgError=el('p','','muted');dlgError.setAttribute('role','alert');
  const bar=el('div',undefined,'toolbar');
  const cancel=el('button','取消');cancel.type='button';cancel.onclick=()=>dlg.close();
  dlgOk=el('button','保存','primary');dlgOk.type='submit';
  bar.append(cancel,dlgOk);
  dlgForm.append(el('h2','重命名存档'),label,dlgError,bar);
  dlgForm.onsubmit=async e=>{
   e.preventDefault();const title=dlgInput.value.trim();
   if(!title||title.length>80){dlgError.textContent='名称需要 1 到 80 个字';return}
   dlgOk.disabled=true;dlgError.textContent='';
   try{await renameSession(dlgId,title);dlg.close()}
   catch(error){dlgError.textContent=error.message}
   finally{dlgOk.disabled=false}
  };
  dlg.append(dlgForm);document.body.append(dlg);return dlg;
 }
 function openRename(id,title){
  ensureDialog();dlgId=id;dlgInput.value=title;dlgError.textContent='';
  dlg.showModal();dlgInput.focus();dlgInput.select();
 }
 async function renameSession(id,title){
  await api(sessionUrl(id),'PATCH',{title});
  if(current&&current.id===id){current.title=title;const badge=$('play-badge');if(badge)badge.textContent=title}
  await bootstrap();notice('已重命名');
 }
 async function removeSession(id,title){
  if(!confirm('删除存档「'+title+'」？\n\n该存档的对话、进度与相关记忆将被永久删除，不可恢复。故事包本身不受影响。'))return;
  await api(sessionUrl(id),'DELETE');
  // 先把这一行从列表里拿掉，避免切回空态、等 bootstrap 重绘的那半秒里还看得到已删除的存档。
  for(const b of list.querySelectorAll('button[data-session-id]'))if(b.dataset.sessionId===id)(b.closest('.journey-row')||b).remove();
  if(current&&current.id===id)await window.TDEnterAuthorMode();
  try{if(localStorage.getItem('textiledream-session')===id)localStorage.removeItem('textiledream-session')}catch(e){}
  await bootstrap();notice('已删除存档');
 }

 function decorate(){
  for(const item of Array.from(list.children)){
   if(item.tagName!=='BUTTON'||!item.dataset.sessionId)continue;
   const id=item.dataset.sessionId;
   const title=item.querySelector('.journey-title')?.textContent||item.title||'未命名旅程';
   const row=el('div',undefined,'journey-row');
   list.replaceChild(row,item);row.append(item);
   const more=el('button','⋯','journey-more');more.type='button';
   more.setAttribute('aria-haspopup','menu');more.setAttribute('aria-expanded','false');
   more.setAttribute('aria-label','存档操作：'+title);more.title='重命名或删除';
   more.onclick=e=>{e.stopPropagation();if(menu&&opener===more)closeMenu(false);else openMenu(more,id,title)};
   row.append(more);
  }
 }
 new MutationObserver(decorate).observe(list,{childList:true});
 decorate();
})();
