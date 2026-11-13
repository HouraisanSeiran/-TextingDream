/* Published background -> kingdom sites -> existing town drafts -> versioned content. */
(function () {
  'use strict';
  const state={plan:null,site:null,busy:false,background:null};
  const root='/inner/world-package/backgrounds', plans='/inner/settlement-plans';
  const nodes={};
  function node(tag,id,text){const n=el(tag,text);if(id){n.id='kingdom-'+id;nodes[id]=n}return n}
  function field(label,n){const p=el('label',label);p.append(n);return p}
  function control(id,label,fn){const n=node('button',id,label);n.type='button';n.onclick=()=>run(fn);return n}
  const page=node('section','page');page.className='page';page.hidden=true;
  page.append(el('h2','王国城镇与道路'),el('p','依据已发布背景选择聚落位置，补充城镇所需条件，再审核发布。道路为规划候选，不自动写成历史事实。'));
  const form=el('div',undefined,'card'),background=node('select','background'),polity=node('select','polity');
  const seed=node('input','seed');seed.value='kingdom-1';seed.maxLength=64;
  const count=node('input','count');count.type='number';count.min='1';count.max='24';count.value='3';
  const distance=node('input','distance');distance.type='number';distance.min='0';distance.value='1000';
  form.append(field('背景版本',background),field('所属国家',polity),field('规划种子',seed),field('聚落数量',count),field('聚落最小间距（米）',distance),control('generate','生成聚落与道路规划',generate),control('refresh','刷新记录',refresh));
  const status=node('p','status');status.setAttribute('role','status');
  const records=node('div','records'),summary=node('div','summary'),map=node('div','map'),sites=node('div','sites');
  const edit=el('div',undefined,'card'),editor=node('textarea','input');editor.rows=22;editor.spellcheck=false;
  edit.append(node('h3','site-heading','选择一个聚落'),node('p','required'),field('城镇条件（JSON，缺项请依据地图或作者设定填写）',editor),control('create-town','生成该聚落的城镇草稿',createTown),control('edit-town','编辑城镇阶段与查看布局',editTown),control('publish-town','发布该城镇',publishTown),control('layout','查看该城镇布局数据',layout),node('pre','town'));
  const versions=node('div','versions');page.append(form,status,records,summary,map,sites,edit,control('publish','审核并发布王国城镇版本',publish),el('h3','已发布王国城镇'),versions);
  document.querySelector('main').append(page);
  const nav=el('button','王国城镇','workspace-link');nav.id='workspace-kingdoms';nav.dataset.nav='kingdom-page';nav.onclick=()=>TDNav.show('kingdom-page');const anchor=$('workspace-background');if(anchor)anchor.after(nav);
  TDNav.register('kingdom-page',{title:'王国城镇与道路',enter:()=>run(refresh)});
  async function run(fn){if(state.busy)return;state.busy=true;buttons();try{await fn()}catch(error){status.textContent=error.message+'；已填写内容保留。'}finally{state.busy=false;buttons()}}
  function buttons(){for(const key of ['generate','refresh','create-town','edit-town','publish-town','layout','publish'])if(nodes[key])nodes[key].disabled=state.busy||(['create-town'].includes(key)&&(!state.site||state.plan?.status==='published'))||(['edit-town','publish-town','layout'].includes(key)&&!state.plan?.towns?.[state.site?.id]?.draft_id)||(key==='publish'&&(!state.plan||state.plan.status==='published'))}
  async function refresh(){
    const previous=background.value;const rows=await api(root);background.replaceChildren();
    for(const row of rows){const o=el('option',(row.title||row.id)+' · '+row.version_id);o.value=row.version_id;background.append(o)}
    if(rows.some(r=>r.version_id===previous))background.value=previous;
    if(background.value)await loadBackground();else status.textContent='请先在世界背景页审核发布一个背景版本。';
  }
  async function loadBackground(){
    const wanted=polity.value;state.background=await api(root+'/'+encodeURIComponent(background.value));polity.replaceChildren();
    for(const k of state.background.simulation?.kingdoms||[]){const o=el('option',k.name||k.id);o.value=String(k.id);polity.append(o)}
    if((state.background.simulation?.kingdoms||[]).some(k=>String(k.id)===wanted))polity.value=wanted;
    state.plan=null;state.site=null;summary.replaceChildren();sites.replaceChildren();map.replaceChildren();editor.value='';nodes.town.textContent='';await refreshRecords();buttons();
  }
  background.onchange=()=>run(loadBackground);
  async function refreshRecords(){
    const id=encodeURIComponent(background.value);const drafts=await api(root+'/'+id+'/settlements');records.replaceChildren();
    for(const row of drafts){const b=el('button',(row.polity_id||'国家')+' · '+row.id+' · '+row.status);b.type='button';b.onclick=()=>run(async()=>show(await api(plans+'/'+encodeURIComponent(row.id))));records.append(b)}
    const published=await api(root+'/'+id+'/kingdom-versions');versions.replaceChildren();
    for(const row of published){const b=el('button',row.id+' · '+(row.polity_id||''));b.type='button';b.onclick=()=>run(async()=>{nodes.town.textContent=JSON.stringify(await api('/inner/kingdom-versions/'+encodeURIComponent(row.id)),null,2)});versions.append(b)}
  }
  async function generate(){if(!background.value||!polity.value)throw Error('请先选择有国家的背景版本');show(await api(root+'/'+encodeURIComponent(background.value)+'/settlements?polity_id='+encodeURIComponent(polity.value),'POST',{seed:seed.value,count:Number(count.value),min_distance_m:Number(distance.value)}));await refreshRecords();status.textContent='规划已生成，请逐镇填写缺失条件并审核。'}
  function show(plan){state.plan=plan;state.site=null;summary.replaceChildren(el('h3','规划 '+plan.id),el('p','背景 '+plan.background_version_id+' · 年份 '+plan.background_year+' · 修订 '+plan.revision),el('p','道路 '+(plan.roads?.length||0)+' 条；未连通分组 '+(plan.disconnected?.length||0)));sites.replaceChildren();editor.value='';nodes.town.textContent='';nodes.required.textContent='';for(const site of plan.sites||[]){const b=el('button',(site.name||site.id)+' · '+site.role+' · '+site.x_m+', '+site.z_m+' 米'+(plan.towns?.[site.id]?' · 已有草稿':''));b.type='button';b.onclick=()=>run(()=>selectSite(site));sites.append(b)}draw(plan);buttons()}
  function draw(plan){map.replaceChildren();if(!plan.sites?.length)return;const points=plan.sites.map(s=>[s.x_m,s.z_m]);for(const road of plan.roads||[])points.push(...(road.points_xz_m||[]));const xs=points.map(p=>p[0]),zs=points.map(p=>p[1]),x0=Math.min(...xs),z0=Math.min(...zs),width=Math.max(1,Math.max(...xs)-x0),height=Math.max(1,Math.max(...zs)-z0),pad=Math.max(width,height)*.08;function svg(tag,attrs){const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v]of Object.entries(attrs))n.setAttribute(k,String(v));return n}const canvas=svg('svg',{viewBox:[x0-pad,z0-pad,width+2*pad,height+2*pad].join(' '),role:'img','aria-label':'聚落与陆地道路规划'});canvas.style.maxHeight='420px';canvas.style.width='100%';for(const road of plan.roads||[])if(road.points_xz_m?.length)canvas.append(svg('polyline',{points:road.points_xz_m.map(p=>p.join(',')).join(' '),fill:'none',stroke:'#98724c','stroke-width':Math.max(width,height)/180}));for(const site of plan.sites){const p=svg('circle',{cx:site.x_m,cy:site.z_m,r:Math.max(width,height)/65,fill:'#35666a'}),t=svg('title',{});t.textContent=site.name||site.id;p.append(t);canvas.append(p)}map.append(canvas,el('p','坐标单位为米；连线表示沿陆地格求得的待审核路径。'))}
  async function selectSite(site){const data=await api(plans+'/'+encodeURIComponent(state.plan.id)+'/sites/'+encodeURIComponent(site.id)+'/town-input');state.site=site;editor.value=JSON.stringify(data.template,null,2);nodes['site-heading'].textContent=site.name||site.id;nodes.required.textContent='待填写／核对：'+JSON.stringify(data.required_fields||[]);nodes.town.textContent=JSON.stringify({observations:data.observations,background_context:data.background_context},null,2);buttons()}
  async function createTown(){const site=state.site;const response=await api(plans+'/'+encodeURIComponent(state.plan.id)+'/sites/'+encodeURIComponent(site.id)+'/town','POST',{expected_revision:state.plan.revision,input:JSON.parse(editor.value)});const inputText=editor.value;show(response.plan);state.site=site;editor.value=inputText;nodes.town.textContent=JSON.stringify(response.draft,null,2);status.textContent='城镇草稿已生成；核对人口、生计、建筑和背景条件后发布。';buttons()}
  async function publishTown(){const id=state.plan.towns[state.site.id].draft_id;const draft=await api('/inner/towns/'+encodeURIComponent(id));const result=await api('/inner/towns/'+encodeURIComponent(id)+'/publish','POST',{expected_revision:draft.revision});nodes.town.textContent=JSON.stringify(result.version,null,2);status.textContent='该城镇已发布；全部聚落完成后可发布王国城镇版本。'}
  async function layout(){const id=state.plan.towns[state.site.id].draft_id;nodes.town.textContent=JSON.stringify(await api('/inner/towns/'+encodeURIComponent(id)+'/layout','POST',{}),null,2)}
  async function editTown(){const id=state.plan.towns[state.site.id].draft_id;await window.TDTowns.openDraft(id)}
  async function publish(){const result=await api(plans+'/'+encodeURIComponent(state.plan.id)+'/publish','POST',{expected_revision:state.plan.revision});show(result.plan);nodes.town.textContent=JSON.stringify(result.version,null,2);await refreshRecords();status.textContent='王国城镇版本已发布，绑定原背景及城镇快照。'}
  window.TDKingdoms={state,refresh,show,open:async function(version){await refresh();background.value=version;await loadBackground();TDNav.show('kingdom-page')}};
  buttons();
})();
