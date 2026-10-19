'use strict';
function atlasViewer(host){
 const names={terrain:'地形',elevation:'海拔',water:'水系',resources:'矿产',fertile_soil:'沃土',farmland:'旧版耕地',population:'人口承载',states:'政区',cultures:'文化',routes:'商路',markers:'地点'},colors={terrain:'#b29a6a',elevation:'#c99470',resources:'#d5a8e5',fertile_soil:'#8ccc78',farmland:'#92aa65',population:'#f3aa7b',water:'#6dc8e8',states:'#c4a7ef',cultures:'#e6b480',routes:'#edc985',markers:'#f3e7c5'};
 const bar=el('div',undefined,'toolbar atlas-controls'),search=el('input');search.placeholder='查找地点或区域';search.setAttribute('aria-label','地图搜索');
 const canvas=svg('svg',{viewBox:'0 0 1440 720',class:'atlas-svg','aria-label':'分层世界图册'}),info=el('div',undefined,'atlas-info'),note=el('p',undefined,'muted'),wrap=el('div',undefined,'atlas-layout');wrap.append(canvas,info);
 const elevationBands=[[-Infinity,'低于0','#77ad78'],[0,'0–200','#79b76c'],[200,'200–500','#b3ce7c'],[500,'500–1000','#e1db91'],[1000,'1000–2000','#dfbb78'],[2000,'2000–3000','#c99260'],[3000,'3000–4000','#ab7558'],[4000,'4000–5000','#8f695b'],[5000,'5000–6000','#d1c3b6'],[6000,'≥6000','#f3eee5']];
 const elevationColor=value=>elevationBands.filter(b=>value>=b[0]).at(-1)[2];
 const mode=el('select');mode.setAttribute('aria-label','地图样式');mode.append(new Option('分层设色地形图','terrain'),new Option('综合图','all'));mode.value='terrain';
 const legend=el('div',undefined,'terrain-legend');legend.append(el('strong','陆地海拔（米）'));
 for(const [,label,color]of elevationBands){const entry=el('span',label);entry.style.borderLeft='12px solid '+color;legend.append(entry)}
 legend.append(el('strong','海洋水深（米）'));for(const [label,color]of [['0–200','#aad9e5'],['200–2000','#7eb8d6'],['2000–4000','#5997c2'],['4000–6000','#427aae'],['≥6000','#315d98']]){const entry=el('span',label);entry.style.borderLeft='12px solid '+color;legend.append(entry)}
 const caption=el('p','同一海拔区间使用同一颜色。现实高程测试底图：GMT Earth Relief / SRTM15+V2.7，10角分；架空区域有海拔时按同一色阶覆盖，仅有地点高度时显示色点，未知高度只画边界。底图不改变故事设定。','muted');
 let data={features:[]},places=[],box=[0,0,1440,720],drag=null,moved=false;const enabled=new Set(['terrain','elevation','water','routes','markers']),checks={};
 const project=([x,y])=>[(x+180)*4,(90-y)*4],view=()=>canvas.setAttribute('viewBox',box.join(' '));
 function focus(points){const xy=points.map(project),xs=xy.map(p=>p[0]),ys=xy.map(p=>p[1]),w=Math.max(65,Math.max(...xs)-Math.min(...xs)+40),h=Math.max(40,Math.max(...ys)-Math.min(...ys)+30);box=[Math.min(...xs)-20,Math.min(...ys)-15,Math.max(w,h*2),Math.max(h,w/2)];view()}
 function scale(f){const w=Math.max(24,Math.min(1440,box[2]*f)),h=w/2;box=[box[0]+(box[2]-w)/2,box[1]+(box[3]-h)/2,w,h];view()}
 function details(f){info.replaceChildren(el('h3',f.name),el('p',(names[f.layer]||'地点')+(f.visibility==='author'?' · 作者可见':''),'muted'),el('p',f.description||'暂无说明','prose'),button('放大此区域',()=>focus(f.coordinates)));
  info.append(el('p','经纬度：'+f.coordinates.map(p=>p.map(n=>Number(n).toFixed(2)).join(', ')).slice(0,3).join(' / ')));
  if(f.environment){const e=f.environment,s=f.estimates||{};info.append(el('p',`海拔 ${e.elevation_m}m · 坡度 ${e.slope_deg}° · 年降雨 ${e.precipitation_mm}mm · 年均温 ${e.temperature_c}℃`),el('p',`流域：${e.basin||'未设定'} · 区域 ${e.area_km2}km² · 自然沃土 ${s.fertile_soil_km2??'待算'}km² · 承载人口 ${s.population_capacity??'待算'}`));if(e.deposits?.length)info.append(el('p','资源：'+e.deposits.map(d=>({iron:'铁',coal:'煤',copper:'铜',tin:'锡',gold:'金',rare_metals:'稀有金属'}[d.kind])+`（丰度${d.abundance}，可达${d.accessibility}，技术${d.technology}）`).join('；')));info.append(el('p',(s.dependencies||[]).join(' · '),'muted'))}
  for(const a of f.articles||[]){const d=el('details');d.open=true;d.append(el('summary',a.title),el('p',a.content,'prose'),el('small',a.status||'设定'));info.append(d)}}
 function draw(){canvas.replaceChildren();const topo=mode.value==='terrain';canvas.append(svg('image',{href:topo?'/maps/world-hypsometric.png':'/maps/world-detailed.svg',x:0,y:0,width:1440,height:720,preserveAspectRatio:'none',class:'atlas-basemap'}));legend.hidden=!topo;caption.hidden=!topo;
  for(const lon of [-120,-60,0,60,120])canvas.append(svg('path',{d:`M ${(lon+180)*4} 0 V 720`,stroke:'#81989a','stroke-opacity':.15,'stroke-width':.5}));
  for(const lat of [-60,-30,0,30,60]){canvas.append(svg('path',{d:`M 0 ${(90-lat)*4} H 1440`,stroke:'#81989a','stroke-opacity':.2,'stroke-width':.5}));const label=svg('text',{x:4,y:(90-lat)*4-2,'font-size':6,fill:'#aabbbb'});label.textContent=lat+'°';canvas.append(label)}
  const all=[...data.features,...places.map(p=>({id:'play_'+p.id,name:p.name,layer:'markers',geometry:'point',coordinates:[p.coordinates],description:p.current?'当前位置':p.explored?'已探索地点':'已知相邻地点',current:p.current}))].sort((a,b)=>['terrain','elevation','fertile_soil','farmland','states','cultures','water','routes','resources','population','markers'].indexOf(a.layer)-['terrain','elevation','fertile_soil','farmland','states','cultures','water','routes','resources','population','markers'].indexOf(b.layer)),q=search.value.trim().toLowerCase();
  for(const f of all){if(!enabled.has(f.layer)||(q&&!(f.name+' '+f.description).toLowerCase().includes(q)))continue;const xy=f.coordinates.map(project),g=svg('g',{tabindex:0,role:'button','aria-label':f.name,class:'atlas-feature','data-terrain':f.terrain_kind||'unspecified'}),height=f.environment?.elevation_m,relief=['terrain','elevation'].includes(f.layer),known=Number.isFinite(height),color=relief?(known?elevationColor(height):'#79796c'):colors[f.layer];
   if(relief){g.setAttribute('data-elevation',known?height:'unknown');g.setAttribute('data-band-color',known?color:'none')}
   if(f.geometry==='point')g.append(svg('circle',{cx:xy[0][0],cy:xy[0][1],r:f.current?4:2.7,fill:color,stroke:'#152a32','stroke-width':.8}));
   else g.append(svg('path',{d:xy.map((p,i)=>(i?'L ':'M ')+p.join(' ')).join(' ')+(f.geometry==='polygon'?' Z':''),fill:f.geometry==='polygon'&&(!relief||known)?color:'none','fill-opacity':relief?1:.16,stroke:color,'stroke-width':relief?.8:1.6,'stroke-dasharray':f.layer==='routes'||relief&&!known?'4 3':'none','vector-effect':'non-scaling-stroke'}));
   const t=svg('text',{x:xy[0][0]+5,y:xy[0][1]-4,'font-size':4.5,fill:topo?'#243528':color,stroke:topo?'#ffffff':'#10242d','stroke-width':1,'paint-order':'stroke'});t.textContent=f.name+(relief&&known?' · '+height+'m':'');g.append(t);g.onclick=()=>{if(!moved)details(f)};g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();details(f)}};canvas.append(g);
  }note.textContent=topo?'矿产、沃土、人口、水系、政区等作为独立图层叠加；参考底图不用于计算旅行时间。':data.note||'架空示意地图';view();
 }
 bar.append(mode);mode.onchange=draw;
 for(const [key,name]of Object.entries(names)){const l=el('label'),c=el('input');checks[key]=c;c.type='checkbox';c.checked=enabled.has(key);c.onchange=()=>{c.checked?enabled.add(key):enabled.delete(key);draw()};l.append(c,document.createTextNode(name));bar.append(l)}
 bar.append(search,button('定位',()=>{const q=search.value.trim().toLowerCase(),f=data.features.find(x=>(x.name+' '+x.description).toLowerCase().includes(q));if(f){focus(f.coordinates);details(f)}}),button('＋',()=>scale(.7)),button('−',()=>scale(1.4)),button('全图',()=>{box=[0,0,1440,720];view()}),button('旅途区域',()=>{const coords=places.length?places.map(p=>p.coordinates):data.features.flatMap(f=>f.coordinates);if(coords.length)focus(coords)}));
 search.oninput=draw;canvas.addEventListener('wheel',e=>{e.preventDefault();scale(e.deltaY>0?1.15:.87)},{passive:false});
 canvas.onpointerdown=e=>{drag={x:e.clientX,y:e.clientY,box:[...box]};moved=false};canvas.onpointermove=e=>{if(!drag)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.abs(dx)+Math.abs(dy)>4)moved=true;const r=canvas.getBoundingClientRect();box=[drag.box[0]-dx/r.width*drag.box[2],drag.box[1]-dy/r.height*drag.box[3],...drag.box.slice(2)];view()};canvas.onpointerup=canvas.onpointerleave=canvas.onpointercancel=()=>{drag=null};
 host.append(bar,legend,wrap,caption,note);
 let signature='';
 return {update(atlas,locations=[]){data=atlas||{features:[]};places=locations;const next=JSON.stringify([data.title,data.features.map(f=>[f.id,f.coordinates]),places.map(p=>[p.id,p.current])]);if(next!==signature){signature=next;search.value='';const coords=places.length?places.map(p=>p.coordinates):data.features.flatMap(f=>f.coordinates);if(coords.length)focus(coords);else{box=[0,0,1440,720];view()}}info.replaceChildren(el('p','点击标记、道路或区域，阅读关联资料。','muted'));draw()},focus};
}
const mapHost=el('div');mapHost.id='layered-player-map';$('map').querySelector('.map-viewport').hidden=true;$('map').querySelector('.toolbar').hidden=true;$('map').querySelector('.map-viewport').after(mapHost);
const playerAtlas=atlasViewer(mapHost),oldDrawMap=drawMap;
drawMap=function(){oldDrawMap();playerAtlas.update(current?.atlas,current?.places||[])};
$('map').querySelector('.intro p').textContent='地形、水系、政区、文化、商路与地点 · 点击标记阅读资料';

const surfaceMapPanel=el('div');surfaceMapPanel.id='surface-map-panel';
const surfaceMapToggle=el('input');surfaceMapToggle.type='checkbox';surfaceMapToggle.id='show-current-map';
surfaceMapToggle.checked=localStorage.getItem('textiledream-show-map')==='true';
const mapLabel=el('label');mapLabel.append(surfaceMapToggle,document.createTextNode('显示当前地图'));
const surfaceMapBody=el('div');surfaceMapBody.id='surface-current-map';surfaceMapBody.hidden=!surfaceMapToggle.checked;
const surfaceMapTitle=el('p',undefined,'muted'),surfaceMapView=el('div');surfaceMapBody.append(surfaceMapTitle,surfaceMapView);surfaceMapPanel.append(mapLabel,surfaceMapBody);
$('surface-journeys').after(surfaceMapPanel);const conversationAtlas=atlasViewer(surfaceMapView);
function updateConversationMap(){surfaceMapTitle.textContent=current?current.world+' · 当前位置：'+current.location+' · 旅程版本 '+current.revision:'请先选择旅程';if(surfaceMapToggle.checked)conversationAtlas.update(current?.atlas,current?.places||[])}
surfaceMapToggle.onchange=()=>{localStorage.setItem('textiledream-show-map',String(surfaceMapToggle.checked));surfaceMapBody.hidden=!surfaceMapToggle.checked;updateConversationMap()};
const renderBeforeMap=render;render=function(){renderBeforeMap();updateConversationMap()};
