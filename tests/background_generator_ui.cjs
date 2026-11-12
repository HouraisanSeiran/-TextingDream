/* Token-aware API seam and a small DOM; no server, browser, data files, or AI. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const clone=x=>JSON.parse(JSON.stringify(x));
function setup(){
  const ids={},requests=[],aliases={},pages={};
  class Element{
    constructor(tag){this.tagName=tag;this.children=[];this.attributes={};this.dataset={};this.style={};this.disabled=false;this.hidden=false;this._text='';this._value='';this.className='';}
    set id(v){this._id=v;ids[v]=this}get id(){return this._id}
    set textContent(v){this._text=String(v??'');this.children=[]}get textContent(){return this._text+this.children.map(x=>x.textContent).join('')}
    set value(v){this._value=String(v)}get value(){return this._value||(this.tagName==='select'?this.children[0]?.value||'':'')}
    append(...xs){for(const x of xs){this.children.push(x);x.parentElement=this}}
    replaceChildren(...xs){this._text='';this.children=[];this.append(...xs)}
    setAttribute(k,v){this.attributes[k]=String(v)}
    after(n){this.parentElement?.append(n)}
  }
  const main=new Element('main'),sidebar=new Element('aside'),anchor=new Element('button');anchor.id='workspace-elements';sidebar.append(anchor);
  const document={createElement:t=>new Element(t),createElementNS:(ns,t)=>new Element(t),querySelector:s=>s==='main'?main:null,getElementById:id=>ids[id]};
  const grid={shape_zx:[4,6],first_xz_m:[0,0],spacing_m:1000};
  const geo={landmasses:[{id:'landmass-1',name:'陆块',geometry:{grid,spans:[[0,0,6],[1,0,6]]}}],kingdoms:[{id:'kingdom-1',polity_id:1,name:'王国',land_cells:3,geometry:{grid,spans:[[0,1,4]]}}],background_year:120};
  let draft=null,fail='',versions=[];
  function advance(stage,more={}){draft={...draft,...more,stage,revision:draft.revision+1};return clone(draft)}
  async function api(p,method='GET',body){requests.push({p,method,body:clone(body??null)});if(fail&&p.endsWith(fail)){throw Error('fixture failure')}
    if(p.endsWith('/sources'))return {bundles:[{id:'tg-fixture',title:'TG 测试世界'}],defaults:{seed:42,start_year:0,end_year:120,max_polities:8,society:true},setting_options:{tech:[{id:'medieval',label:'中世纪'}],magic:[{id:'rare',label:'稀少'}]}};
    if(p=== '/inner/world-package/drafts'&&method==='GET')return draft?[clone(draft)]:[];
    if(p.endsWith('/backgrounds'))return clone(versions);
    if(p.endsWith('/propose')){draft={...body,id:'draft-1',target:'background',kind:'background',revision:1,stage:'proposed',approved_history_ids:[]};return clone(draft)}
    if(p.endsWith('/auto-select'))return advance('selected',{selection:{refs:['race/elf','power/magic']},polity_preferences:[{id:'test-profile',source:{kind:'ai_design_estimate'},weights:{river:1,coast:2,highland:3,distance:4}}]});
    if(p.endsWith('/select'))return advance('selected',{selection:{refs:body.refs},simulation:null,content:null});
    if(p.endsWith('/simulate'))return advance('simulated',{simulation:geo});
    if(p.endsWith('/generate'))return advance('generated',{content:{overview:'背景',continents:[],polities:[],history_sections:[],knowledge:[],major_history_proposals:[{id:'new-event',title:'新增史事',description:'须作者确认'}]}});
    if(p.endsWith('/configure'))return advance('selected',{config:body.config,year:body.year,polity_preferences:body.polity_preferences,simulation:null,content:null});
    if(p.endsWith('/confirm')){versions=[{id:'version-1',version_id:'version-1',title:draft.title}];return advance('published',{published:versions[0]})}
    if(p.endsWith('/revise'))return advance('generated',{status:'draft',published:null});
    if(p.includes('/town-context'))return {world_background:'version-1',polity_id:1};
    if(p.endsWith('/backgrounds/version-1'))return {simulation:geo};
    if(p.endsWith('/drafts/draft-1')&&method==='PUT')return advance('generated',{content:body.content,approved_history_ids:body.approved_history_ids});
    if(p.endsWith('/drafts/draft-1'))return clone(draft);
    throw Error('Unexpected request '+method+' '+p);
  }
  const context=vm.createContext({window:{},document,api,console,Set,JSON,encodeURIComponent,
    $:id=>ids[id],el:(tag,text,cls)=>{const n=new Element(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n},
    button:(text,fn,cls)=>{const n=new Element('button');n.textContent=text;n.onclick=fn;n.className=cls||'';return n},
    TDNav:{register:(id,spec)=>pages[id]=spec,alias:(id,fn)=>aliases[id]=fn,show:()=>{}}});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../app/static/background-generator.js'),'utf8'),context);
  return {ids,requests,aliases,pages,main,ui:context.window.TDBackgroundGenerator,setFail:v=>fail=v,get draft(){return draft}};
}
async function click(env,id){await env.ids['background-'+id].onclick()}
async function run(){
  const env=setup();assert.equal(env.aliases['generator-world']().page,'background-page');assert(env.pages['background-page']);
  await env.pages['background-page'].enter();
  assert.equal(env.ids['background-bundle'].value,'tg-fixture');
  await click(env,'all');
  assert.equal(env.draft.stage,'generated');assert.equal(env.ui.state.draft.revision,4);
  const calls=env.requests.filter(x=>x.method==='POST');assert.deepEqual(calls.map(x=>x.p.split('/').at(-1)),['propose','auto-select','simulate','generate']);
  assert.equal(calls[0].body.target,'background');assert.equal(calls[0].body.config.seed,42);assert.equal(calls[0].body.config.society,true);assert.deepEqual(calls[0].body.polity_preferences,[]);assert.equal(calls[0].body.setting.genres[0].tag,'western_fantasy');
  assert.deepEqual(calls.slice(1).map(x=>x.body.expected_revision),[1,2,3]);
  assert.equal(JSON.parse(env.ids['background-preferences'].value)[0].id,'test-profile');
  const svg=env.ids['background-map'].children[0];assert.equal(svg.attributes.viewBox,'0 0 6 4');assert(svg.children.some(g=>g.children.some(x=>x.tagName==='rect'&&x.attributes.width==='3')));
  assert.match(env.ids['background-revision'].textContent,/修订 4/);assert.match(env.ids['background-selection'].textContent,/race\/elf/);
  const editor=env.ids['background-editor'];const before=editor.value;editor.value='{invalid';await click(env,'save');assert.equal(editor.value,'{invalid');assert.equal(env.ui.state.draft.revision,4);assert.match(env.ids['background-status'].textContent,/保留/);editor.value=before;
  env.setFail('/generate');await click(env,'generate');assert.equal(env.ui.state.draft.revision,4);assert.equal(editor.value,before);assert.match(env.ids['background-status'].textContent,/fixture failure/);env.setFail('');
  const approval=env.ids['background-approvals'].children[1].children[0];approval.checked=true;approval.onchange();await click(env,'publish');
  const saved=env.requests.filter(x=>x.method==='PUT'&&x.p.endsWith('/drafts/draft-1')).at(-1);assert.deepEqual(saved.body.approved_history_ids,['new-event']);assert.equal(env.draft.stage,'published');assert.equal(env.ids['background-publish'].disabled,true);
  const row=env.ids['background-published'].children[0];await row.children.at(-1).onclick();assert.match(env.ids['background-town-context'].textContent,/world_background/);assert(env.requests.some(x=>x.p.endsWith('/town-context?polity_id=kingdom-1')));
  await row.children[2].onclick();assert.match(env.ids['background-town-context'].textContent,/simulation/);await row.children[3].onclick();assert.equal(env.ui.state.draft.stage,'generated');assert.equal(env.ids['background-publish'].disabled,false);
  assert.equal(env.requests.some(x=>x.p.includes('/activate')),false);
  const second=setup();await second.pages['background-page'].enter();await click(second,'all');second.ids['background-seed'].value='9';second.ids['background-year'].value='90';await click(second,'configure');assert.equal(second.draft.config.seed,9);assert.equal(second.draft.year,90);assert.equal(second.draft.simulation,null);assert.equal(second.ids['background-generate'].disabled,true);
  await click(second,'reset');assert.equal(second.ids['background-seed'].value,'42');assert.equal(second.ids['background-year'].value,'120');assert.equal(second.draft.config.seed,9);
  second.ids['background-refs'].value='race/elf';await click(second,'adopt');assert.equal(second.draft.selection.refs.join(','),'race/elf');assert.equal(second.draft.content,null);assert.equal(second.ids['background-generate'].disabled,true);
  second.ui.show({...second.draft,simulation:{...second.ui.state.draft.simulation,...{landmasses:[],kingdoms:[{id:'x',name:'<script>bad()</script>',geometry:{grid:{shape_zx:[1,1]},spans:[[0,0,1]]}}]}},revision:99});assert.match(second.ids['background-kingdoms'].textContent,/<script>bad/);assert.equal(second.ids['background-map'].children[0].children[0].children[0].tagName,'title');
  console.log('background generator: pipeline order, CAS, map, edit/failure preservation, history approvals, publish and town context OK');
}
async function browserRun(){
  const os=require('node:os'),net=require('node:net'),{spawn}=require('node:child_process');
  const root=path.resolve(__dirname,'..');
  let playwright;
  if(process.env.TEXTILEDREAM_PLAYWRIGHT_MODULE)playwright=require(process.env.TEXTILEDREAM_PLAYWRIGHT_MODULE);
  else {try{playwright=require('playwright')}catch(error){if(error.code!=='MODULE_NOT_FOUND')throw error;playwright=require(require.resolve('playwright',{paths:[path.join(root,'external/civ-atlas')]}))}}
  const {chromium}=playwright;
  const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'textiledream-background-ui-'));
  const port=await new Promise(resolve=>{const socket=net.createServer();socket.listen(0,'127.0.0.1',()=>{const value=socket.address().port;socket.close(()=>resolve(value))})});
  const source=`
import os
from pathlib import Path
import uvicorn
from tests.test_world_package_pipeline import build_library
from tests.test_background_http import Registry
from app.web import create_app
root=Path(os.environ['BACKGROUND_UI_TEMP'])
database=root/'encyclopedia.sqlite3'
build_library(database)
os.environ['TEXTILEDREAM_ENCYCLOPEDIA_DB']=str(database)
os.environ['TEXTILEDREAM_ENCYCLOPEDIA_ROOTS']=str(root)
os.environ['TEXTILE_CIV_ATLAS']='0'
app=create_app(root/'runtime.sqlite3')
app.state.service.provider.configure({'offline':True})
app.state.service.world_package.backgrounds.registry=Registry()
uvicorn.run(app,host='127.0.0.1',port=${port},log_level='warning')
`;
  const server=spawn(path.join(root,'.venv/Scripts/python.exe'),['-X','utf8','-u','-c',source],{cwd:root,env:{...process.env,BACKGROUND_UI_TEMP:tmp},windowsHide:true});
  let logs='',browser,activePage;server.stdout.on('data',x=>logs+=x);server.stderr.on('data',x=>logs+=x);
  const base='http://127.0.0.1:'+port,errors=[],csp=[];
  try{
    let ready=false;
    for(let i=0;i<100;i++){if(server.exitCode!==null)throw Error(logs);try{if((await fetch(base+'/api/bootstrap')).ok){ready=true;break}}catch{}await new Promise(r=>setTimeout(r,150))}
    assert(ready,'Background UI server did not become ready: '+logs);
    browser=await chromium.launch({channel:process.env.TEXTILEDREAM_BROWSER_CHANNEL||'msedge',headless:true});
    const page=await browser.newPage({viewport:{width:1440,height:1000}});activePage=page;
    page.on('pageerror',error=>errors.push(error.message));
    await page.addInitScript(()=>document.addEventListener('securitypolicyviolation',event=>(window.__backgroundCsp||(window.__backgroundCsp=[])).push(event.violatedDirective+':'+event.blockedURI)));
    await page.goto(base+'/');
    await page.waitForFunction(()=>window.TDBackgroundGenerator&&window.__textileDreamToken);
    await page.evaluate(()=>{document.querySelectorAll('dialog[open]').forEach(d=>d.close());return TDNav.show('world-workshop')});
    await page.waitForFunction(()=>document.querySelector('#background-bundle').value==='fixture-world');
    await page.locator('#background-title').fill('Browser background');
    await page.locator('#background-seed').fill('2');await page.locator('#background-end_year').fill('2');await page.locator('#background-year').fill('1');await page.locator('#background-max_polities').fill('2');
    await page.locator('#background-all').click();
    await page.waitForFunction(()=>window.TDBackgroundGenerator.state.draft?.stage==='generated'&&!window.TDBackgroundGenerator.state.busy,{},{timeout:30000});
    assert(await page.locator('#background-map svg rect').count()>0);
    const revision=await page.evaluate(()=>window.TDBackgroundGenerator.state.draft.revision);
    await page.locator('#background-editor').evaluate(n=>n.closest('details').open=true);
    const content=await page.locator('#background-editor').inputValue();
    await page.locator('#background-editor').fill('{bad');await page.locator('#background-save').click();
    await page.waitForFunction(()=>document.querySelector('#background-status').textContent.includes('保留'));
    assert.equal(await page.locator('#background-editor').inputValue(),'{bad');
    assert.equal(await page.evaluate(()=>window.TDBackgroundGenerator.state.draft.revision),revision);
    await page.locator('#background-editor').fill(content);await page.locator('#background-publish').click();
    await page.waitForFunction(()=>window.TDBackgroundGenerator.state.draft?.stage==='published'&&!window.TDBackgroundGenerator.state.busy);
    await page.getByRole('button',{name:'查看城镇生成输入',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('#background-town-context').textContent.includes('background_town_context_v1'));
    await page.getByRole('button',{name:'阅读完整背景',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('#background-town-context').textContent.includes('world_background_v1'));
    await page.getByRole('button',{name:'另存修订草稿',exact:true}).click();
    await page.waitForFunction(()=>window.TDBackgroundGenerator.state.draft?.status==='draft'&&window.TDBackgroundGenerator.state.draft?.parent_version);
    const invariant=await page.evaluate(async()=>{const r=await fetch('/api/inner/packages',{headers:{'X-TextileDream-Token':window.__textileDreamToken}});const entries=await r.json();return entries.every(p=>p.kind!=='background'||p.can_start===false)});
    assert(invariant);csp.push(...await page.evaluate(()=>window.__backgroundCsp||[]));assert.deepEqual(errors,[]);assert.deepEqual(csp,[]);
    console.log('background real HTTP/Edge/CSP: isolated synthetic world, create/select/simulate/generate/edit/publish/read/revise/town-context OK');
  }catch(error){if(activePage)console.error(await activePage.evaluate(()=>({status:document.querySelector('#background-status')?.textContent,stage:window.TDBackgroundGenerator?.state.draft?.stage,revision:window.TDBackgroundGenerator?.state.draft?.revision})));console.error(logs);throw error}
  finally{if(browser)await browser.close();server.kill();await new Promise(resolve=>{if(server.exitCode!==null)resolve();else server.once('exit',resolve)});fs.rmSync(tmp,{recursive:true,force:true})}
}
(process.argv.includes('--browser')?browserRun():run()).catch(error=>{console.error(error);process.exitCode=1});
