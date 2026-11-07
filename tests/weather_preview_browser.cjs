/* Actual HTTP preview regression: CSP module loading and CSS/device pixel composition. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const {chromium} = require(require.resolve('playwright', {paths:[path.join(root,'external/civ-atlas')]}));
const output = path.join(root,'artifacts/weather-preview-fix');
fs.mkdirSync(output,{recursive:true});
const instrumentation = `
(function () {
  window.__weatherDraws = {};
  ['daylight','rain','snow','fog','sand','fantasy','aurora','ice','wind','sky'].forEach(function(name) {
    var api = window['WeatherFX_'+name];
    if (!api) return;
    var create = api.create;
    api.create = function(opts) {
      var layer = create(opts), draw = layer.draw;
      layer.draw = function(ctx,pass) {
        var t = ctx.getTransform();
        window.__weatherDraws[name+':'+pass] = [t.a,t.d];
        return draw.call(layer,ctx,pass);
      };
      return layer;
    };
  });
})();
`;
(async () => {
  const browser=await chromium.launch({channel:'msedge',headless:true});
  const report=[];
  try {
    for (const dpr of (process.env.WEATHER_DPRS || '1,1.5,2').split(',').map(Number)) {
      const page=await browser.newPage({viewport:{width:1600,height:1200},deviceScaleFactor:dpr});
      const errors=[],violations=[];
      page.on('pageerror',e=>errors.push(e.message));
      await page.addInitScript(() => document.addEventListener('securitypolicyviolation',e => {
        (window.__cspViolations || (window.__cspViolations=[])).push(e.violatedDirective+':'+e.blockedURI);
      }));
      await page.route('**/weather-fx/index.js',async route=>{
        const response=await route.fetch();
        await route.fulfill({response,body:instrumentation+await response.text()});
      });
      const base=process.env.WEATHER_BASE || 'http://127.0.0.1:8000';
      await page.goto(base+'/static/weather-fx/index.html?dpr='+dpr+'&preset=ashfall');
      await page.waitForFunction(()=>window.__wx && __wx.ready() && __wx.optional().every(m=>m.status!=='加载中'));
      await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
      const state=await page.evaluate(()=>({modules:__wx.optional(),draws:__weatherDraws,
        violations:window.__cspViolations||[],error:document.getElementById('err').textContent,
        canvas:[document.getElementById('fx').width,document.getElementById('fx').height]}));
      violations.push(...state.violations);
      // Compare the actual ash renderer against the same town without effects at all four corners.
      // At DPR > 1 the old compositor left the right and bottom corners completely unchanged.
      await page.evaluate(()=>__wx.enable(Object.fromEntries(__wx.modules.map(n=>[n,false]))));
      const sample=async()=>{
        await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
        return page.evaluate(()=>{
          const c=document.getElementById('fx'),g=c.getContext('2d');
          return [[.02,.02],[.98,.02],[.02,.98],[.98,.98]].map(([x,y])=>
            Array.from(g.getImageData(Math.floor(c.width*x),Math.floor(c.height*y),1,1).data));
        });
      };
      const bare=await sample();
      await page.evaluate(()=>__wx.enable({fantasy:true}));
      const ash=await sample();
      state.cornerPixelChanges=ash.map((pixel,i)=>pixel.slice(0,3).reduce((sum,v,k)=>sum+Math.abs(v-bare[i][k]),0));
      await page.evaluate(()=>__wx.enable(Object.fromEntries(__wx.modules.map(n=>[n,true]))));
      await sample();
      await page.locator('#stage').screenshot({path:path.join(output,'ashfall-dpr'+dpr+'.png')});
      report.push({dpr,...state,errors});
      fs.writeFileSync(path.join(output,'browser-report.json'),JSON.stringify(report,null,2));
      const failures=[];
      if(state.cornerPixelChanges.some(delta=>delta<3)) failures.push('Ash does not cover every corner: '+state.cornerPixelChanges);
      if(state.modules.some(m=>m.status!=='ok')) failures.push('Optional modules failed: '+JSON.stringify(state.modules));
      for(const name of ['rain','snow','fog','sand','fantasy']) {
        const scale=state.draws[name+':light'];
        if(!scale || scale.some(s=>Math.abs(s-dpr)>1e-6)) failures.push(name+' draw scale '+scale+' expected '+dpr);
      }
      if(errors.length || violations.length) failures.push('Browser errors/CSP: '+JSON.stringify({errors,violations}));
      console.log(JSON.stringify({dpr,failures}));
      assert.deepEqual(failures,[]);
      await page.evaluate(()=>__wx.preset('blizzard'));
      await page.waitForFunction(()=>__wx.state().kind==='blizzard');
      await sample();
      await page.locator('#stage').screenshot({path:path.join(output,'snow-dpr'+dpr+'.png')});
      await page.evaluate(()=>{__wx.preset('light-snow');__wx.set({hour:23,g:{snow_cover:.85}});});
      await page.waitForFunction(()=>__wx.state().time.hour===23);
      await sample();
      await page.locator('#stage').screenshot({path:path.join(output,'snow-night-dpr'+dpr+'.png')});
      for(const kind of await page.evaluate(()=>WeatherGen.KINDS)) {
        await page.evaluate(k=>__wx.set({kind:k,intensity:.7}),kind);
        await page.waitForFunction(k=>__wx.state().kind===k,kind);
        await sample();
        const message=await page.locator('#err').textContent();
        assert.ok(!message || message.startsWith('已按 kind 夹紧：'),kind+': '+message);
      }
      for(const preset of await page.evaluate(()=>__wx.presets())) {
        await page.evaluate(p=>__wx.preset(p),preset);
        await sample();
        const result=await page.evaluate(()=>({finite:Object.values(__wx.state().ground).every(Number.isFinite),
          error:document.getElementById('err').textContent}));
        assert.ok(result.finite,preset+' ground');
        assert.ok(!result.error || result.error.startsWith('已按 kind 夹紧：'),preset+': '+result.error);
      }
      await page.evaluate(()=>{__wx.mode('gen');__wx.set({climate:'continental',day:12,hour:3});});
      await sample();
      await page.evaluate(()=>WeatherGen.validateState(__wx.state()));
      assert.deepEqual(errors,[]);
      assert.deepEqual(await page.evaluate(()=>window.__cspViolations||[]),[]);
      Object.assign(report[report.length-1],{manualKindsChecked:28,presetsChecked:16,generatorChecked:true});
      fs.writeFileSync(path.join(output,'browser-report.json'),JSON.stringify(report,null,2));
      console.log(JSON.stringify({dpr,manualKinds:28,presets:16,generator:true}));
      await page.close();
    }
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
