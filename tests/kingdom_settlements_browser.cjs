/* Real author UI against an isolated synthetic background; no model or formal data. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const net=require('node:net');
const {spawn}=require('node:child_process');

const root=path.resolve(__dirname,'..');
function playwrightModule(){
  if(process.env.TEXTILEDREAM_PLAYWRIGHT_MODULE)return require(process.env.TEXTILEDREAM_PLAYWRIGHT_MODULE);
  try{return require('playwright')}catch(error){
    if(error.code!=='MODULE_NOT_FOUND')throw error;
    return require(require.resolve('playwright',{paths:[path.join(root,'external/civ-atlas')]}));
  }
}

async function freePort(){
  return new Promise((resolve,reject)=>{
    const socket=net.createServer();socket.on('error',reject);
    socket.listen(0,'127.0.0.1',()=>{const port=socket.address().port;socket.close(()=>resolve(port))});
  });
}

async function run(){
  const {chromium}=playwrightModule();
  const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'textiledream-kingdom-browser-'));
  const port=await freePort(),base='http://127.0.0.1:'+port;
  const python=`
import json, os
from pathlib import Path
import uvicorn
from fastapi.testclient import TestClient
from app import towns
from app.service import Service
import app.web as web
from tests.test_background_http import Registry
from tests.test_kingdom_settlements_http import background
from tests.test_world_package_pipeline import build_library

temporary=Path(os.environ['KINGDOM_BROWSER_TEMP'])
database=temporary/'encyclopedia.sqlite3'
build_library(database)
os.environ['TEXTILEDREAM_ENCYCLOPEDIA_DB']=str(database)
os.environ['TEXTILEDREAM_ENCYCLOPEDIA_ROOTS']=str(temporary)
os.environ['TEXTILE_CIV_ATLAS']='0'
# Keep static files at the repository root while all author writes use the temporary root.
web.Service=lambda store, ignored_root: Service(store, temporary)
app=web.create_app(temporary/'runtime.sqlite3')
service=app.state.service
service.provider.configure({'offline':True})
service.world_package.backgrounds.registry=Registry()
with TestClient(app) as client:
    headers={'X-TextileDream-Token':client.get('/api/bootstrap').json()['token']}
    document=background(client,headers)
fixture={'version_id':document['version_id'],
         'polity_id':document['simulation']['kingdoms'][0]['id'],
         'author_input':towns.preset_entry('wet_valley','browser-author-declaration').model_dump(mode='json')}
(temporary/'fixture.json').write_text(json.dumps(fixture,ensure_ascii=False),encoding='utf-8')
assert service.runtime.root.resolve()==temporary.resolve()
assert service.store.get('pointer','package') is None
uvicorn.run(app,host='127.0.0.1',port=${port},log_level='warning',access_log=False)
`;
  const server=spawn(path.join(root,'.venv/Scripts/python.exe'),['-X','utf8','-u','-c',python],{
    cwd:root,env:{...process.env,KINGDOM_BROWSER_TEMP:temporary},windowsHide:true
  });
  let logs='',browser,page;
  server.stdout.on('data',chunk=>logs+=chunk);server.stderr.on('data',chunk=>logs+=chunk);
  const errors=[],csp=[];
  try{
    let ready=false;
    for(let attempt=0;attempt<160;attempt++){
      if(server.exitCode!==null)throw Error('Fixture server exited: '+logs);
      try{if((await fetch(base+'/api/bootstrap')).ok){ready=true;break}}catch{}
      await new Promise(resolve=>setTimeout(resolve,150));
    }
    assert(ready,'Fixture server did not start: '+logs);
    const fixture=JSON.parse(fs.readFileSync(path.join(temporary,'fixture.json'),'utf8'));
    browser=await chromium.launch({channel:process.env.TEXTILEDREAM_BROWSER_CHANNEL||'msedge',headless:true});
    page=await browser.newPage({viewport:{width:1440,height:1000}});
    page.on('pageerror',error=>errors.push(error.message));
    await page.addInitScript(()=>document.addEventListener('securitypolicyviolation',event=>{
      (window.__kingdomCsp||(window.__kingdomCsp=[])).push(event.violatedDirective+':'+event.blockedURI);
    }));
    const idle=()=>page.waitForFunction(()=>window.TDKingdoms&&!window.TDKingdoms.state.busy);
    await page.goto(base+'/');
    await page.waitForFunction(()=>window.TDKingdoms&&window.__textileDreamToken);
    await page.evaluate(()=>{document.querySelectorAll('dialog[open]').forEach(dialog=>dialog.close());TDNav.show('background-page')});
    await page.getByRole('button',{name:'王国城镇与道路',exact:true}).click();
    await page.waitForFunction(version=>document.querySelector('#kingdom-background').value===version&&!window.TDKingdoms.state.busy,fixture.version_id);
    assert.equal(await page.locator('#kingdom-polity').inputValue(),fixture.polity_id);
    await page.locator('#kingdom-count').fill('3');
    await page.locator('#kingdom-seed').fill('browser-kingdom');
    await page.locator('#kingdom-generate').click();await idle();
    let plan=await page.evaluate(()=>window.TDKingdoms.state.plan);
    assert(plan,await page.locator('#kingdom-status').textContent());
    assert.equal(plan.background_version_id,fixture.version_id);assert.equal(plan.sites.length,3);
    assert(plan.roads.length>0,'The fixture must exercise an actual planned land route');
    assert.equal(await page.locator('#kingdom-map svg circle').count(),3);
    assert.equal(await page.locator('#kingdom-map svg polyline').count(),plan.roads.length);
    const planId=plan.id,siteIds=plan.sites.map(site=>site.id);
    for(const siteId of siteIds){
      const siteIndex=plan.sites.findIndex(site=>site.id===siteId);
      await page.locator('#kingdom-sites button').nth(siteIndex).click();await idle();
      const template=JSON.parse(await page.locator('#kingdom-input').inputValue());
      assert.equal(template.background.site_id,siteId);
      assert.equal(template.terrain.soil_fertility,null);
      assert.match(await page.locator('#kingdom-required').textContent(),/soil_fertility/);
      const declared=structuredClone(fixture.author_input);
      for(const key of ['story_revision','seed','site','site_location_id','region','map','background','founded_period'])declared[key]=structuredClone(template[key]);
      for(const [key,value] of Object.entries(template.terrain))if(value!==null||key==='coordinates')declared.terrain[key]=value;
      declared.bindings=[];
      declared.notes='Explicit browser-test author assumptions for missing water, soil and society; not measured map facts.';
      await page.locator('#kingdom-input').fill(JSON.stringify(declared,null,2));
      await page.locator('#kingdom-create-town').click();await idle();
      plan=await page.evaluate(()=>window.TDKingdoms.state.plan);
      assert(plan.towns[siteId],await page.locator('#kingdom-status').textContent());
      const draftId=plan.towns[siteId].draft_id;
      if(siteId===siteIds[0]){
        await page.locator('#kingdom-layout').click();await idle();
        const layout=JSON.parse(await page.locator('#kingdom-town').textContent());
        assert.equal(layout.source.id,draftId);
        // The new bridge must open the existing single-town editor with the real draft.
        await page.locator('#kingdom-edit-town').click();
        await page.waitForFunction(()=>!document.querySelector('#towns').hidden&&document.querySelector('#town-json').value.length>2);
        assert.equal(await page.evaluate(()=>activeTown.id),draftId);
        assert.equal(await page.locator('#town-heading').textContent(),declared.site_name);
        await page.evaluate(()=>TDNav.show('kingdom-page'));await idle();
        await page.locator('#kingdom-records button').filter({hasText:planId}).click();await idle();
        await page.locator('#kingdom-sites button').nth(siteIndex).click();await idle();
      }
      await page.locator('#kingdom-publish-town').click();await idle();
      const town=JSON.parse(await page.locator('#kingdom-town').textContent());
      assert.equal(town.snapshot.input.background.version_id,fixture.version_id);
      assert.equal(town.snapshot.input.background.site_id,siteId);
    }
    await page.locator('#kingdom-publish').click();await idle();
    const published=JSON.parse(await page.locator('#kingdom-town').textContent());
    assert.equal(published.background_version_id,fixture.version_id);
    assert.equal(published.town_versions.length,3);
    assert.equal(published.can_start,false);
    assert(published.plan.roads.every(road=>road.status==='planned'));
    assert.equal(await page.locator('#kingdom-publish').isDisabled(),true);
    assert.equal(await page.locator('#kingdom-versions button').count(),1);
    csp.push(...await page.evaluate(()=>window.__kingdomCsp||[]));
    await page.reload();
    await page.waitForFunction(()=>window.TDKingdoms&&window.__textileDreamToken);
    await page.evaluate(()=>{document.querySelectorAll('dialog[open]').forEach(dialog=>dialog.close());TDNav.show('kingdom-page')});await idle();
    await page.locator('#kingdom-versions button').filter({hasText:published.id}).click();await idle();
    const reopened=JSON.parse(await page.locator('#kingdom-town').textContent());
    assert.deepEqual(reopened,published);
    csp.push(...await page.evaluate(()=>window.__kingdomCsp||[]));
    assert.deepEqual(errors,[]);assert.deepEqual(csp,[]);
    console.log(JSON.stringify({result:'passed',browser:process.env.TEXTILEDREAM_BROWSER_CHANNEL||'msedge',
      background_version:fixture.version_id,kingdom_version:published.id,sites:siteIds.length,
      roads:published.plan.roads.length,published_towns:published.town_versions.length,
      same_version_after_reload:true,page_errors:errors,csp_violations:csp,formal_data_modified:false},null,2));
  }catch(error){
    if(page)console.error(await page.evaluate(()=>({status:document.querySelector('#kingdom-status')?.textContent,
      plan:window.TDKingdoms?.state.plan?.id,site:window.TDKingdoms?.state.site?.id})));
    console.error(logs);throw error;
  }finally{
    if(browser)await browser.close();
    if(server.exitCode===null){server.kill();await new Promise(resolve=>server.once('exit',resolve))}
    const tempRoot=path.resolve(os.tmpdir())+path.sep;
    assert(path.resolve(temporary).startsWith(tempRoot),'Refuse cleanup outside temporary root');
    fs.rmSync(temporary,{recursive:true,force:true});
  }
}

run().catch(error=>{console.error(error);process.exitCode=1});
