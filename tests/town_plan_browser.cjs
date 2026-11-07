/* Real HTTP + production CSP + isolated database; never touches saves or calls a model. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawn} = require('node:child_process');
const root = path.resolve(__dirname, '..');
const {chromium} = require(require.resolve('playwright',{paths:[path.join(root,'external/civ-atlas')]}));
const output = path.join(root,'artifacts/town-plan');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(),'textiledream-town-plan-'));
const port = Number(process.env.TOWN_PLAN_TEST_PORT || 8766);
const base = 'http://127.0.0.1:'+port;
fs.mkdirSync(output,{recursive:true});
const server = spawn(path.join(root,'.venv/Scripts/python.exe'),['-X','utf8','-u','-c',`
import os
import uvicorn
from pathlib import Path
from tests.fixtures_world import world_app
app=world_app(Path(os.environ['TOWN_PLAN_TEST_DB']))
app.state.service.provider.configure({'offline':True})
uvicorn.run(app,host='127.0.0.1',port=${port},log_level='warning')
`],{cwd:root,env:{...process.env,TOWN_PLAN_TEST_DB:path.join(tmp,'test.sqlite3')},windowsHide:true});
let logs=''; server.stdout.on('data',b=>logs+=b);server.stderr.on('data',b=>logs+=b);
(async()=>{
  let browser;
  const errors=[], responses=[];
  try {
    let ready=false;
    for(let i=0;i<120;i++){
      if(server.exitCode!==null)throw Error('Test server exited: '+logs);
      try{const r=await fetch(base+'/api/bootstrap');if(r.ok){ready=true;break;}}catch{}
      await new Promise(r=>setTimeout(r,250));
    }
    assert(ready,'Test server failed: '+logs);
    browser=await chromium.launch({channel:'msedge',headless:true});
    const page=await browser.newPage({viewport:{width:1600,height:1100},deviceScaleFactor:1.5});
    page.on('pageerror',e=>errors.push(e.message));
    page.on('response',async response=>{
      if(response.url().endsWith('/layout')&&response.ok()){
        try{responses.push(await response.json());}catch{/* Browser may close after a failed assertion. */}
      }
    });
    await page.addInitScript(()=>document.addEventListener('securitypolicyviolation',e=>{
      (window.__townCsp||(window.__townCsp=[])).push(e.violatedDirective+':'+e.blockedURI);
    }));
    await page.goto(base+'/');
    await page.waitForFunction(()=>window.__textileDreamToken&&window.TownPlanUI);
    await page.evaluate(()=>document.querySelectorAll('dialog[open]').forEach(d=>d.close()));
    await page.waitForFunction(()=>window.__nativeMapRoot||document.querySelector('#native-map-host [data-state="failed"]'));
    const nativeClose=page.getByRole('button',{name:'关闭生成新世界',exact:true});
    if(await nativeClose.count())await nativeClose.click();
    await page.evaluate(()=>showPage('towns'));
    async function waitPlan(){
      await page.waitForFunction(()=>document.querySelector('#town-plan-scene svg use')&&
        !document.getElementById('town-plan-generate').disabled,{},{timeout:30000});
    }
    async function changePlan(action){
      const pending=page.waitForResponse(r=>r.url().endsWith('/layout')&&r.ok(),{timeout:30000});
      await action();
      const data=await (await pending).json();
      await waitPlan();
      await page.waitForFunction(name=>document.getElementById('town-plan-status').textContent.startsWith(name),data.name);
      return data;
    }
    const report={cases:[],errors,base};
    for(const preset of ['wet_valley','cold_mountain_mine','arid_oasis_route']){
      await page.selectOption('#town-preset',preset);
      await page.fill('#town-seed','browser_'+preset);
      await page.fill('#town-site','浏览器验收_'+preset);
      const data=await changePlan(()=>page.locator('#town-create-form button[type=submit]').click());
      const rendered=await page.evaluate(()=>({status:document.getElementById('town-plan-status').textContent,
        uses:document.querySelectorAll('#town-plan-scene use').length,
        missing:[...document.querySelectorAll('#town-plan-scene use')].filter(n=>!document.getElementById(n.getAttribute('href').slice(1))).length,
        named:document.querySelectorAll('#town-plan-scene [data-town-source]').length,
        sites:document.getElementById('town-plan-site').options.length,
        sceneWidth:document.querySelector('#town-plan-scene svg').getBoundingClientRect().width}));
      assert(rendered.uses>50);assert.equal(rendered.missing,0);assert(rendered.named>0);assert(rendered.sites>0);
      assert(rendered.sceneWidth>500);
      await page.locator('.town-plan').screenshot({path:path.join(output,preset+'.png')});
      report.cases.push({preset,...rendered,summary:data.summary});
    }
    assert.equal(responses.at(-1).resolved.style,'arab');
    assert(!responses.at(-1).resource_sites.some(s=>s.resource==='iron'));
    assert(responses.at(-1).resource_sites.every(s=>s.diagnostics.some(d=>d.reason==='style_fallback')));
    await changePlan(()=>page.selectOption('#town-plan-style','east'));
    const fallback=await changePlan(()=>page.selectOption('#town-plan-race','elf'));
    assert.equal(fallback.resolved.race,'common');
    assert(fallback.diagnostics.some(d=>d.reason==='culture_fallback'));
    await page.locator('#town-plan-facilities').evaluate(n=>n.closest('details').open=true);
    await page.locator('#town-plan-facilities button:not([disabled])').first().click();
    assert.equal(await page.locator('[data-town-highlight]').count(),1);
    await page.selectOption('#town-plan-zoom','200');
    const zoom=await page.evaluate(()=>({scene:document.getElementById('town-plan-scene').getBoundingClientRect().width,
      view:document.getElementById('town-plan-viewport').clientWidth}));
    assert(zoom.scene>zoom.view*1.8);
    await page.locator('#town-plan-export').scrollIntoViewIfNeeded();
    const downloadPromise=page.waitForEvent('download');await page.click('#town-plan-export');
    const download=await downloadPromise;await download.saveAs(path.join(output,'town-map.json'));
    const exported=JSON.parse(fs.readFileSync(path.join(output,'town-map.json'),'utf8'));
    assert.equal(exported.resolved.style,'east');
    await changePlan(()=>page.click('#town-publish'));
    await page.locator('#town-versions details').first().evaluate(n=>n.open=true);
    const versionResponse=page.waitForResponse(r=>r.url().includes('/town-versions/')&&r.url().endsWith('/layout')&&r.ok());
    await page.getByRole('button',{name:'查看此版本的城镇地图'}).first().click();
    assert.equal((await (await versionResponse).json()).source.kind,'version');
    await waitPlan();
    assert((await page.locator('#town-plan-status').textContent()).includes('已发布版本'));
    const stale=await page.evaluate(async()=>{
      const draft=await api('/inner/towns/'+activeTown.id);
      await api('/inner/towns/'+draft.id+'/stages','PUT',{stage:'skeleton',data:draft.stages[0].data,expected_revision:draft.revision});
      await selectTown(draft.id);
      return {uses:document.querySelectorAll('#town-plan-scene use').length,status:document.getElementById('town-plan-status').textContent};
    });
    assert.equal(stale.uses,0);assert(stale.status.includes('失效'));
    report.stale=stale;report.csp=await page.evaluate(()=>window.__townCsp||[]);
    report.requests=responses.map(r=>({source:r.source,summary:r.summary,resolved:r.resolved}));
    assert.deepEqual(report.csp,[]);assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(output,'browser-report.json'),JSON.stringify(report,null,2));
    console.log(JSON.stringify(report,null,2));
  }finally{
    if(browser)await browser.close();
    server.kill();
    await new Promise(resolve=>server.exitCode!==null?resolve():server.once('exit',resolve));
    assert(path.resolve(tmp).startsWith(path.resolve(os.tmpdir())+path.sep));
    assert(path.basename(tmp).startsWith('textiledream-town-plan-'));
    fs.rmSync(tmp,{recursive:true,force:true});
  }
})().catch(error=>{console.error(error.stack,logs);process.exitCode=1;});
