const {chromium}=require(require.resolve('playwright',{paths:[require('path').resolve('external/civ-atlas')]}));
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
  fs.mkdirSync('artifacts/world-detail',{recursive:true});
  const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  try {
    await page.goto('http://127.0.0.1:8000/');
    await page.waitForFunction(()=>document.querySelector('.dream-world-detail')?.dataset.k==='1',{},{timeout:90000});
    const read=()=>page.locator('.dream-world-detail').evaluate(c=>({...c.dataset,width:c.width,height:c.height}));
    const overview=await read();
    assert(Number(overview.eligible)<=12);
    await page.screenshot({path:'artifacts/world-detail/overview.png'});
    for(let i=0;i<4;i++) await page.getByRole('button',{name:'放大地图',exact:true}).click();
    await page.waitForFunction(()=>Number(document.querySelector('.dream-world-detail')?.dataset.k)>3.2);
    const regional=await read();assert(Number(regional.eligible)>Number(overview.eligible));
    // Fixed existing-world viewport: this point lies in open sea, well away from symbols.
    await page.mouse.click(850,730);
    const inspector=page.getByRole('region',{name:'地理详情'});
    await inspector.waitFor();
    assert.match(await inspector.innerText(),/海洋/);
    await page.getByRole('button',{name:'关闭地理详情',exact:true}).click();
    await page.screenshot({path:'artifacts/world-detail/regional.png'});
    for(let i=0;i<2;i++) await page.getByRole('button',{name:'放大地图',exact:true}).click();
    await page.waitForFunction(()=>Number(document.querySelector('.dream-world-detail')?.dataset.k)>6);
    const local=await read();assert(Number(local.eligible)>=Number(regional.eligible));
    await page.screenshot({path:'artifacts/world-detail/local.png'});
    await page.getByRole('button',{name:'复位',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('.dream-world-detail')?.dataset.k==='1');
    assert.equal((await read()).eligible,overview.eligible);
    await page.setViewportSize({width:390,height:844});
    await page.waitForFunction(()=>{const c=document.querySelector('.dream-world-detail');return c&&Math.abs(c.width-c.getBoundingClientRect().width*devicePixelRatio)<2;});
    assert.equal(errors.length,0,errors.join('\n'));
    fs.writeFileSync('artifacts/world-detail/browser.json',JSON.stringify({overview,regional,local,errors},null,2));
    console.log(JSON.stringify({overview,regional,local,errors}));
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
