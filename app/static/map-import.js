'use strict';
// 地图工具（作者侧）：把 civ-atlas 生成的世界数据接进织梦的城镇管线。
// 约定：
//  · 预览图是作者侧受保护路由（`/api/inner/...`），必须带 token 头取 blob 再转 ObjectURL；
//    绝不把 token 拼进 URL，也不为了显示图片放宽作者路由。
//  · 图层是服务端按真实数组渲染的不同图（高程/气温/降水/群系/海陆），不是同一张灰度图换标签。
//  · 选点只发经纬度；地形与气候数字由服务端重算，客户端传来的样本永不被信任。
//  · 「生成器数据」不等于现实测量：这里是 civ-atlas 生成世界的逐格数值，不是地球观测数据。
const MAP_PAGE=el('section',undefined,'page');MAP_PAGE.id='map-tools';MAP_PAGE.hidden=true;
MAP_PAGE.innerHTML=`<div class="map-tools" id="map-tools-root">
 <div class="map-stage">
  <div class="map-stage-head">
   <div><h2 class="map-title">地图</h2><p id="map-sub" class="map-sub">选择一个已导入的世界，或先导入。</p></div>
   <div class="map-actions">
    <button id="map-open-civ-top" class="map-btn primary" type="button">打开地图生成器</button>
    <label class="map-btn">导入文件<input id="map-file" type="file" accept=".civsnap,.png"></label>
    <button id="map-reload" class="map-btn" type="button">刷新</button>
   </div>
  </div>
  <div class="map-canvas-wrap" id="map-canvas-wrap">
   <img id="map-preview" alt="导入世界的图层预览" hidden>
   <div id="map-empty" class="map-empty">还没有导入的地图。<br><small>推荐用 civ-atlas 的 .civsnap（含高程、海陆、气温、降水、群系）。</small></div>
   <div id="map-pin" class="map-pin" hidden></div>
  </div>
  <div class="map-legend" id="map-legend" hidden></div>
  <p id="map-status" class="map-status" role="status"></p>
 </div>
 <div class="map-side">
  <div class="map-block">
   <label class="map-field">已导入<select id="map-imports"></select></label>
   <p id="map-meta" class="map-meta"></p>
  </div>
  <div class="map-block" id="map-layer-block">
   <h3 class="map-h3">图层</h3>
   <div id="map-layers" class="map-layers"></div>
  </div>
  <div class="map-block">
   <h3 class="map-h3">选点</h3>
   <div class="map-coord">
    <label>经度<input id="map-lon" type="number" step="0.01" min="-180" max="180" value="10"></label>
    <label>纬度<input id="map-lat" type="number" step="0.01" min="-89.5" max="89.5" value="35"></label>
   </div>
   <label class="map-field">窗格<select id="map-window"><option>3</option><option>5</option><option>7</option><option>9</option><option>11</option><option>13</option><option>15</option></select></label>
   <div class="map-actions"><button id="map-sample" class="map-btn primary" type="button">取样</button><button id="map-clear-pin" class="map-btn" type="button">清除标记</button></div>
   <div id="map-sample-out" class="map-sample"></div>
  </div>
  <div class="map-block" id="map-town-block" hidden>
   <h3 class="map-h3">创建城镇草稿</h3>
   <label class="map-field">地点名<input id="map-site" maxlength="80" placeholder="例如 观雨城"></label>
    <label class="map-field">所属区域<input id="map-region" maxlength="80" placeholder="例如 河谷上游"></label>
   <label class="map-check"><input id="map-confirm-template" type="checkbox"> 用模板占位先出一版草稿（水源/通路/材料会标成模板默认值，不是地图事实）</label>
   <label class="map-field">气温与降水<select id="map-climate"><option value="measured">用该世界生成的数值</option><option value="author">我来填</option></select></label>
   <div id="map-author-climate" hidden>
    <div class="map-coord"><label>年均温 ℃<input id="map-temp" type="number" step="0.1" min="-55" max="55"></label><label>年降水 mm<input id="map-precip" type="number" step="1" min="0" max="6000"></label></div>
   </div>
   <div class="map-actions"><button id="map-make-town" class="map-btn primary" type="button">创建草稿</button></div>
   <p id="map-town-out" class="map-status"></p>
  </div>
  <details class="map-block map-advanced"><summary>导出工具 · 来源与限制</summary>
   <div id="map-steps" class="map-steps">
    <p class="map-step-t">还没有原件？按这三步做：</p>
    <p>1. 打开 civ-atlas（本机 <code>http://127.0.0.1:5188/</code>），新建一个世界。</p>
    <p>2. <strong>先点「保存地图」把它存进「我的世界」</strong>——草稿状态下的世界不会写原件，也就导不出来。</p>
    <p>3. 回到这页之前，在 civ-atlas 右下角点「导出给织梦」，下载 <code>.civsnap</code>；也可以直接在这里导入。</p>
    <p class="map-note">不想用按钮也可以：拿下面的导出脚本到 civ-atlas 的控制台里粘着跑。脚本只读 IndexedDB，不联网、不写库、不读 API Key。</p>
   </div>
   <div class="map-actions"><button id="map-get-tool" class="map-btn" type="button">下载导出脚本</button><button id="map-open-civ" class="map-btn" type="button">打开 civ-atlas</button></div>
   <pre id="map-tool-note" class="map-pre"></pre>
   <div id="map-units" class="map-note"></div>
  </details>
  <!-- 历史采纳：独立组件自己渲染、自己取数据；这里只给一块容器，不改上面任何控件。 -->
  <div class="map-block" id="map-history-block">
   <world-history-panel id="map-history"></world-history-panel>
  </div>
 </div>
</div>`;
document.querySelector('main').append(MAP_PAGE);
const mapNav=el('button');mapNav.dataset.page='map-tools';
mapNav.append(el('span','◈ 世界地图工具'),el('small','导入·选点'));
mapNav.onclick=()=>safe(()=>showPage('map-tools'));
// 插到「地图与世界」那组导航的最后（不依赖某条具体按钮在哪个 nav 里）
document.querySelector('nav button[data-page="world-workshop"]').closest('nav').append(mapNav);

if(!document.getElementById('map-towns-style')){
 const link=document.createElement('link');link.rel='stylesheet';link.href='/static/map-tools.css';link.id='map-towns-style';
 document.head.append(link);
}

let mapImports=[],mapActive=null,mapSample=null,mapLayer='',mapPreviewUrl='',mapPreviewSeq=0,mapLayers=[];

// 图层能力由服务端给出的真实数组决定。高度图只有高程与海陆，所以这里不会凭空列出气温层。
function mapLayerOptions(){
 const s=(mapActive&&mapActive.stats)||{};
 if(!mapActive)return [];
 if(!mapActive.format.includes('snapshot'))return [['elevation','高程'],['water','海陆']];
 const out=[['elevation','高程'],['water','海陆']];
 if(s.has_temperature)out.push(['temperature','气温']);
 if(s.has_precipitation)out.push(['precipitation','降水']);
 if(s.has_biome)out.push(['biome','群系']);
 return out;
}

function mapSetLayer(name){
 mapLayer=name;
 for(const b of $('map-layers').querySelectorAll('button'))b.classList.toggle('on',b.dataset.layer===name);
 drawMapLegend();
 loadMapPreview();
}

function drawMapLegend(){
 const box=$('map-legend');box.replaceChildren();
 if(!mapActive){box.hidden=true;return}
 box.hidden=false;
 const table={
  elevation:[['#77ad78','低于 0 m'],['#b3ce7c','0–500 m'],['#e1db91','500–1500 m'],['#dfbb78','1500–3000 m'],['#c99260','3000–4500 m'],['#f3eee5','≥4500 m']],
  water:[['#1d2b34','海'],['#3f6f8a','湖'],['#9fb3a8','陆']],
  temperature:[['#5c7f8c','≤ −10 ℃'],['#9fb8a6','−10…5 ℃'],['#d8cfa6','5…20 ℃'],['#c98f6a','20…30 ℃'],['#a85c47','≥30 ℃']],
  precipitation:[['#8a7a52','≤ 200 mm'],['#7f9a6a','200…600'],['#5f9a8a','600…1200'],['#4a7fa8','1200…2500'],['#3a5f9a','≥2500 mm']],
  biome:[['#4a7fa8','海洋/湖泊'],['#f3eee5','冰原'],['#b9b3a0','苔原'],['#4f6f4a','针叶林'],['#8fa06a','草原'],['#c9b072','荒漠'],['#3f7a52','林地']]
 }[mapLayer]||[];
 for(const [color,label]of table){const span=el('span',label);span.style.borderLeft='11px solid '+color;box.append(span)}
 const note=el('span',(mapLayer==='temperature'||mapLayer==='precipitation'||mapLayer==='biome')
   ?'该世界生成器算出的逐格数值，不是现实观测':'由该世界的高程与海陆数组渲染','map-legend-note');
 box.append(note);
}

async function loadMapPreview(){
 if(!mapActive)return;
 const seq=++mapPreviewSeq;
 const img=$('map-preview');
 // token 走请求头：作者路由不放宽，URL 里不带 token。
 const res=await fetch('/api/inner/map-imports/'+encodeURIComponent(mapActive.id)+'/preview.png?layer='+encodeURIComponent(mapLayer),
  {headers:{'X-TextileDream-Token':token}});
 if(seq!==mapPreviewSeq)return;            // 旧响应晚到：丢弃，避免覆盖新图层
 if(!res.ok){
  img.hidden=true;
  if(mapPreviewUrl){URL.revokeObjectURL(mapPreviewUrl);mapPreviewUrl=''}
  const empty=$('map-empty');empty.hidden=false;empty.textContent='预览图加载失败（'+res.status+'）；导入记录仍在，选点与创建城镇不受影响。';
  return;
 }
 const blob=await res.blob();
 if(seq!==mapPreviewSeq)return;
 const url=URL.createObjectURL(blob);
 const old=mapPreviewUrl;mapPreviewUrl=url;
 img.onload=()=>{if(old)URL.revokeObjectURL(old)};
 img.src=url;img.hidden=false;
 const empty=$('map-empty');empty.hidden=true;
}

function mapMessage(text){$('map-status').textContent=text||''}
function mapPct(v){return (v*100).toFixed(0)+'%'}
function mapNum(v,fixed){return (v===null||v===undefined||Number.isNaN(Number(v)))?'—':Number(v).toFixed(fixed)}

async function mapRefresh(){
 mapImports=await api('/inner/map-imports');
 const history=$('map-history');
 if(history&&!history.previewId)await history.loadImports();
 const sel=$('map-imports');
 sel.replaceChildren(...(mapImports.length
   ? mapImports.slice().reverse().map(r=>new Option(`${r.format.includes('snapshot')?'世界':'高度图'} · ${r.id} · ${r.width}×${r.height}`,r.id))
   : [new Option('（没有导入）','')]));
 if(!mapImports.length){mapActive=null;mapSample=null;mapDraw();return}
 const keep=(mapActive&&mapImports.some(r=>r.id===mapActive.id))?mapActive.id:mapImports.at(-1).id;
 await mapSelect(keep);
}

async function mapSelect(id){
 mapActive=await api('/inner/map-imports/'+encodeURIComponent(id));
 mapSample=null;
 $('map-sample-out').replaceChildren();
 $('map-town-block').hidden=true;
 $('map-imports').value=id;
 mapLayers=mapLayerOptions();
 const box=$('map-layers');box.replaceChildren();
 for(const [name,label]of mapLayers){
  const b=el('button',label,'map-layer-btn');b.type='button';b.dataset.layer=name;
  b.onclick=()=>safe(()=>mapSetLayer(name));
  box.append(b);
 }
 mapLayer=mapLayers.some(([n])=>n===mapLayer)?mapLayer:mapLayers[0][0];
 mapDraw();
 await loadMapPreview();
}

function mapDraw(){
 const img=$('map-preview'),empty=$('map-empty'),pin=$('map-pin');
 if(!mapActive){
  img.hidden=true;empty.hidden=false;pin.hidden=true;$('map-legend').hidden=true;
  $('map-meta').textContent='';$('map-sub').textContent='选择一个已导入的世界，或先导入。';
  $('map-layer-block').hidden=true;return;
 }
 empty.hidden=true;$('map-layer-block').hidden=false;
 const s=mapActive.stats||{};
 $('map-sub').textContent=mapActive.format.includes('snapshot')
  ?`civ-atlas 生成的世界 · ${mapActive.width} 个地块 · 生成器 g${(mapActive.source||{}).generator_version??'?'}`
  :`16 位高度图 · ${mapActive.width}×${mapActive.height} · 海拔 ${mapNum(mapActive.lo_m,0)}…${mapNum(mapActive.hi_m,0)} 米`;
 const rows=[['编号',mapActive.id],['内容哈希',(mapActive.sha256||'').slice(0,16)],['格 / 像素',`${mapActive.width} × ${mapActive.height}`]];
 if(mapActive.format.includes('snapshot')){
  rows.push(['海 / 湖地块',`${s.sea_cells??'—'} / ${s.lake_cells??'—'}`]);
  rows.push(['气温 / 降水',`${s.has_temperature?'有':'无'} / ${s.has_precipitation?'有':'无'}`]);
 }else{
  rows.push(['海面占比',mapPct(s.sea_fraction||0)]);
 }
 $('map-meta').replaceChildren(...rows.flatMap(([k,v])=>[el('span',k,'map-meta-k'),el('span',v,'map-meta-v')]));
 const units=$('map-units');units.replaceChildren();
 const u=mapActive.units||{};
 const unitRows=[['高程',u.elevation||'—'],['海陆',u.water||u.sea_land||'—'],
  ['气温',u.temperature||'这份数据不含气温'],['降水',u.precipitation||'这份数据不含降水'],
  ['面积',u.area||'按声明星体半径折算']];
 for(const [k,v]of unitRows)units.append(el('p',`${k}：${v}`));
 if((mapActive.warnings||[]).length){
  const w=el('div','','map-warn');
  for(const line of mapActive.warnings)w.append(el('p',line));
  units.append(w);
 }
  drawMapLegend();
 if(window.__spatialDraw)window.__spatialDraw();   // 空间圈选页重画自己的覆盖层与草稿列表
}

function mapPinAt(lon,lat){
 const wrap=$('map-canvas-wrap'),img=$('map-preview'),pin=$('map-pin');
 if(!mapActive||img.hidden){pin.hidden=true;return}
 const rect=img.getBoundingClientRect(),box=wrap.getBoundingClientRect();
 if(!rect.width){pin.hidden=true;return}
 pin.hidden=false;
 pin.style.left=(rect.left-box.left+(lon+180)/360*rect.width)+'px';
 pin.style.top=(rect.top-box.top+(90-lat)/180*rect.height)+'px';
}

async function mapSampleAt(lon,lat){
 if(!mapActive)throw Error('先选择一个导入');
 $('map-lon').value=lon;$('map-lat').value=lat;
 mapPinAt(lon,lat);
 const out=$('map-sample-out');out.replaceChildren(el('p','取样中…','map-muted'));
 let s;
 try{
  s=await api('/inner/map-imports/'+encodeURIComponent(mapActive.id)+'/sample','POST',
   {lon,lat,window_px:Number($('map-window').value)});
 }catch(error){
  out.replaceChildren(el('p',error.message,'map-err'));
  $('map-town-block').hidden=true;
  throw error;
 }
 mapSample=s;out.replaceChildren();drawMapSample(s);$('map-town-block').hidden=false;
}

function drawMapSample(s){
 const out=$('map-sample-out');out.replaceChildren();
 const grid=el('div','','map-kv');
 const rows=[['经度 / 纬度',`${mapNum(s.lon,2)}° / ${mapNum(s.lat,2)}°`],
  ['海拔（窗内）',`${mapNum(s.elevation_m.min,0)}…${mapNum(s.elevation_m.max,0)}，均 ${mapNum(s.elevation_m.mean,0)} 米`],
  ['海面占比',mapPct(s.sea_fraction)],
  ['窗内面积',`${mapNum(s.area_km2,1)} km²（陆 ${mapNum(s.land_km2,1)}）`],
  ['跨度',`南北 ${mapNum(s.span_km.north_south,0)} × 东西 ${mapNum(s.span_km.east_west,0)} km`],
  ['区域坡度 p50 / max',`${mapNum(s.slope_deg.p50,2)}° / ${mapNum(s.slope_deg.max,2)}°`]];
 if(s.climate&&s.climate.measured){
  rows.push(['气温 / 降水',`${mapNum(s.climate.temperature_c,1)} ℃ · ${mapNum(s.climate.precipitation_mm,0)} mm/年${s.climate.biome_name?' · '+s.climate.biome_name:''}`]);
 }else{
  rows.push(['气温 / 降水','这份数据不含，需你填']);
 }
 for(const [k,v]of rows)grid.append(el('span',k,'map-kv-k'),el('span',v,'map-kv-v'));
 out.append(grid);
 if(s.vertical_m)out.append(el('p',`高程换算误差约 ±${mapNum(s.vertical_m,1)} 米（高度图量化 + 取整）`,'map-muted'));
 const missing=(s.missing||[]).length?s.missing:(s.blocked||[]);
 if(missing.length)out.append(el('p','这份数据不含：'+missing.join('、'),'map-muted'));
 for(const line of s.warnings||[])out.append(el('p',line,'map-warn-line'));
 if(s.area_km2>0)out.append(el('p',`面积按球面均分近似，不是精确地块面积`,'map-muted'));
 $('map-climate').value=(s.climate&&s.climate.measured)?'measured':'author';
 mapClimateMode();
}

function mapClimateMode(){
 const author=$('map-climate').value==='author';
 $('map-author-climate').hidden=!author;
 if(author&&mapSample&&mapSample.climate&&mapSample.climate.measured){
  if(!$('map-temp').value)$('map-temp').value=mapSample.climate.temperature_c;
  if(!$('map-precip').value)$('map-precip').value=Math.round(mapSample.climate.precipitation_mm);
 }
}
$('map-climate').onchange=mapClimateMode;

async function mapMakeTown(){
 if(!mapActive||!mapSample)throw Error('先取样再创建');
 const site=$('map-site').value.trim(),region=$('map-region').value.trim();
 if(!site||!region)throw Error('请填写地点名与所属区域');
 const source=$('map-climate').value;
 const author={climate_source:source,site_name:site,region,
  selection:{lon:mapSample.lon,lat:mapSample.lat}};
 if(source==='author'){
  author.temperature_c=Number($('map-temp').value);
  author.precipitation_mm=Number($('map-precip').value);
 }
 if($('map-confirm-template').checked)author.confirm_template=true;
 const out=$('map-town-out');out.textContent='正在按这份地形生成…';
 const r=await api('/inner/map-imports/'+encodeURIComponent(mapActive.id)+'/town-input','POST',
  {lon:mapSample.lon,lat:mapSample.lat,window_px:Number($('map-window').value),author});
 const draft=await api('/inner/towns','POST',{input:r.input});
  out.replaceChildren(
   el('p',`已创建草稿 ${draft.id}｜${r.input.site_name} · ${r.input.region}`,'map-ok'),
   el('p','四阶段生成、校验与发布在「城镇创作」页完成；不修改故事包，也不移动已有旅程的版本。','map-muted'));
  const go=el('button','去城镇创作 ›','map-btn');go.type='button';
  go.onclick=()=>safe(async()=>{
   window.__mapTownDraft=draft.id;
   await showPage('towns');
   // 城镇页自己会拉列表；这里再把下拉选中那次草稿，不依赖它是不是已经刷新完。
   const pick=$('town-list');
   if(pick&&!pick.querySelector('.selected')){
    const btn=[...pick.querySelectorAll('button')].find(b=>b.textContent.includes(draft.id));
    if(btn)btn.click();
   }
  });
  out.append(go);
  notice('城镇草稿已创建：'+draft.id);
  window.__mapTownDraft=draft.id;
}

$('map-imports').onchange=()=>safe(()=>mapSelect($('map-imports').value));
$('map-reload').onclick=()=>safe(async()=>{await mapRefresh();notice('已刷新导入列表')});
$('map-sample').onclick=()=>safe(()=>mapSampleAt(Number($('map-lon').value),Number($('map-lat').value)));
$('map-clear-pin').onclick=()=>{
 $('map-pin').hidden=true;
 $('map-sample-out').replaceChildren();
 $('map-town-block').hidden=true;
 mapSample=null;
};
$('map-make-town').onclick=()=>safe(mapMakeTown);
$('map-open-civ').onclick=()=>openGenerator();
$('map-open-civ-top').onclick=()=>openGenerator();
$('map-get-tool').onclick=()=>safe(async()=>{
 const r=await api('/inner/civ-atlas/export-tool');
 const url=URL.createObjectURL(new Blob([r.source],{type:'text/javascript'}));
 const a=el('a');a.href=url;a.download='civ-atlas-export.js';a.click();
 setTimeout(()=>URL.revokeObjectURL(url),1000);
 $('map-tool-note').textContent='已下载 '+r.path+'。在 civ-atlas 页面控制台整段粘贴后运行 __civAtlasExport.list()。';
});
$('map-file').onchange=e=>safe(async()=>{
 const file=e.target.files[0];if(!file)return;
 e.target.value='';
 mapMessage('正在导入 '+file.name+'（'+(file.size/1048576).toFixed(1)+' MB）…');
 const buf=await file.arrayBuffer();
 const res=await fetch('/api/inner/map-imports',{method:'POST',
  headers:{'Content-Type':'application/octet-stream','X-TextileDream-Token':token},
  body:buf});
 const j=await res.json();
 if(!res.ok)throw Error(typeof j.detail==='string'?j.detail:JSON.stringify(j.detail));
 mapMessage('已导入 '+j.id);
 await mapRefresh();
 await mapSelect(j.id);
});
$('map-canvas-wrap').onclick=e=>safe(async()=>{
 if(!mapActive)return;
 const img=$('map-preview');if(img.hidden)return;
 const rect=img.getBoundingClientRect();if(!rect.width)return;
 const x=(e.clientX-rect.left)/rect.width,y=(e.clientY-rect.top)/rect.height;
 if(x<0||x>1||y<0||y>1)return;
 await mapSampleAt(Number((-180+360*x).toFixed(2)),Number((90-180*y).toFixed(2)));
});

TDNav.register('map-tools',{title:'世界地图工具',enter:async()=>{mapMessage('');await mapRefresh()}});

// 空间圈选页（spatial-planner.js）复用这一页的底图与导入记录：这里只开放只读入口，
// 不让它另造底图或自己算经纬度映射。
window.mapActiveId=()=>(mapActive?mapActive.id:'');
window.mapActiveRecord=()=>mapActive;
window.mapSelectForSpatial=async id=>{await mapSelect(id)};
