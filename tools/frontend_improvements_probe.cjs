const {chromium}=require(require.resolve('playwright',{paths:[require('path').resolve('external/civ-atlas')]}));
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
  fs.mkdirSync('artifacts/frontend-improvements',{recursive:true});
  const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[],checks=[];
  page.on('pageerror',e=>errors.push(e.message));
  let listFailed=false;
  await page.route('**/api/inner/native-worlds',route=>{
    if(!listFailed){listFailed=true;return route.fulfill({status:503,json:{detail:'测试：世界清单暂不可用'}});}
    return route.continue();
  });
  const ready=()=>page.waitForFunction(()=>!!document.querySelector('.dream-world-detail')?.dataset.k,{},{timeout:90000});
  const zoom=()=>page.locator('.dream-world-detail').getAttribute('data-k');
  try {
    await page.goto('http://127.0.0.1:8000/');
    await page.getByRole('button',{name:'重新读取世界',exact:true}).click({timeout:60000});
    await ready();checks.push('list failure and retry');
    assert.equal(await page.locator('.dream-atlas-heading').evaluate(e=>getComputedStyle(e).display),'flex');
    checks.push('atlas stylesheet loaded from the main application');
    const stage=page.locator('.dream-host-stage');
    await stage.focus();await page.keyboard.press('+');
    await page.waitForFunction(()=>Number(document.querySelector('.dream-world-detail').dataset.k)>1);
    const before=await stage.locator(':scope > div').first().getAttribute('style');
    await page.keyboard.press('ArrowRight');
    await page.waitForFunction(old=>document.querySelector('.dream-host-stage > div')?.getAttribute('style')!==old,before);
    await page.keyboard.press('0');
    await page.waitForFunction(()=>document.querySelector('.dream-world-detail').dataset.k==='1');
    checks.push('keyboard zoom, pan, reset');
    await page.evaluate(()=>{
      const original=CanvasRenderingContext2D.prototype.rect;
      CanvasRenderingContext2D.prototype.rect=function(...args){
        if(this.canvas.classList?.contains('dream-world-detail')){
          CanvasRenderingContext2D.prototype.rect=original;
          throw new Error('TEST_RENDER_FAILURE');
        }
        return original.apply(this,args);
      };
    });
    const selected=await page.getByLabel('选择原件',{exact:true}).inputValue();
    await page.getByRole('button',{name:'放大地图',exact:true}).click();
    await page.getByRole('button',{name:'重新绘制地图',exact:true}).click();
    await ready();assert.equal(await page.getByLabel('选择原件',{exact:true}).inputValue(),selected);
    checks.push('animation-frame render failure and isolated retry');
    await page.locator('.dream-atlas-actions').getByRole('button',{name:'复位',exact:true}).click();
    await page.screenshot({path:'artifacts/frontend-improvements/desktop.png'});
    // Open the existing tool panel; never submit a real world generation request.
    await page.locator('#workspace-map-tools').click();
    await page.getByRole('button',{name:'生成一个新世界',exact:false}).click();
    const form=page.locator('.dream-create');
    const cells=form.getByLabel('地块数',{exact:true});
    await cells.fill('17000');
    await form.getByRole('button',{name:'随机种子',exact:true}).click();
    assert.equal(await cells.inputValue(),'17000');
    await cells.fill('');
    assert.equal(await form.evaluate(f=>f.checkValidity()),false);
    await cells.fill('17000');
    assert.equal(await form.evaluate(f=>f.checkValidity()),true);
    const k=await zoom();await cells.press('ArrowUp');assert.equal(await zoom(),k);
    checks.push('random seed preserves other parameters; empty form blocked; inputs keep own keys');
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:'artifacts/frontend-improvements/mobile.png'});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    checks.push('390px layout');
    assert.deepEqual(errors.filter(e=>!e.includes('TEST_RENDER_FAILURE')),[]);
    fs.writeFileSync('artifacts/frontend-improvements/browser.json',JSON.stringify({checks,errors},null,2));
    console.log(JSON.stringify({checks,errors}));
  } catch(error){
    await page.screenshot({path:'artifacts/frontend-improvements/failure.png'});
    console.error('Buttons:',await page.locator('button').allTextContents());throw error;
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
