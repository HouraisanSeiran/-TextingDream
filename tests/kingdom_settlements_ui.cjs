/* Author workflow regression; no real map, model or persistent save. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const ids={},requests=[];
class Element{
  constructor(tag,text){this.tagName=tag;this.children=[];this.style={};this.dataset={};this.attributes={};this._text=text||'';this._value='';}
  set id(v){this._id=v;ids[v]=this}get id(){return this._id}
  set textContent(v){this._text=String(v??'');this.children=[]}get textContent(){return this._text+this.children.map(c=>c.textContent).join('')}
  set value(v){this._value=String(v)}get value(){return this._value||(this.tagName==='select'?this.children[0]?.value||'':'')}
  append(...xs){for(const x of xs){this.children.push(x);x.parentElement=this}}
  replaceChildren(...xs){this._text='';this.children=[];this.append(...xs)}
  after(n){this.parentElement?.append(n)}
  setAttribute(k,v){this.attributes[k]=String(v)}
}
const main=new Element('main'),aside=new Element('aside'),anchor=new Element('button');anchor.id='workspace-background';aside.append(anchor);
const pages={},site={id:'site-1',name:'测试聚落',role:'capital',x_m:1000,z_m:2000};
let plan={id:'kp1',revision:0,status:'draft',background_version_id:'bgv1',polity_id:'kingdom-1',background_year:10,sites:[site],roads:[],disconnected:[],towns:{}},fail=false;
const api=async(p,method='GET',body)=>{
  requests.push({p,method,body});if(fail&&p.endsWith('/town'))throw Error('invalid water input');
  if(p.endsWith('/backgrounds'))return [{version_id:'bgv1',title:'世界背景'}];
  if(p.endsWith('/backgrounds/bgv1'))return {simulation:{kingdoms:[{id:'kingdom-1',name:'国家'}]}};
  if(p.endsWith('/bgv1/settlements')&&method==='GET')return [plan];
  if(p.includes('/bgv1/settlements?')&&method==='POST')return plan;
  if(p.endsWith('/bgv1/kingdom-versions'))return [];
  if(p.endsWith('/sites/site-1/town-input'))return {template:{water:{daily_capacity_l:null}},required_fields:['water.daily_capacity_l'],observations:{elevation_m:40},background_context:{version_id:'bgv1'}};
  if(p.endsWith('/sites/site-1/town')){plan={...plan,revision:1,towns:{'site-1':{draft_id:'td1'}}};return {plan,draft:{id:'td1'}}}
  if(p.endsWith('/towns/td1'))return {revision:0};
  if(p.endsWith('/towns/td1/publish'))return {version:{id:'tv1'}};
  if(p.endsWith('/towns/td1/layout'))return {source:'layout'};
  if(p.endsWith('/settlement-plans/kp1/publish')){plan={...plan,revision:2,status:'published'};return {plan,version:{id:'ksv1'}}}
  if(p.endsWith('/settlement-plans/kp1'))return plan;
  throw Error('Unexpected '+method+' '+p);
};
const context=vm.createContext({window:{},document:{querySelector:()=>main,createElementNS:(ns,t)=>new Element(t)},el:(t,text)=>new Element(t,text),$:id=>ids[id],api,console,JSON,encodeURIComponent,TDNav:{register:(id,spec)=>pages[id]=spec,show:()=>{}}});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../app/static/kingdom-settlements.js'),'utf8'),context);
async function click(id){await ids['kingdom-'+id].onclick()}
async function run(){
  await pages['kingdom-page'].enter();assert.equal(ids['kingdom-background'].value,'bgv1');
  await click('generate');assert.equal(context.window.TDKingdoms.state.plan.id,'kp1');
  await ids['kingdom-sites'].children[0].onclick();assert.match(ids['kingdom-required'].textContent,/water.daily_capacity_l/);
  ids['kingdom-input'].value='{"water":{"daily_capacity_l":90000}}';fail=true;await click('create-town');assert.match(ids['kingdom-status'].textContent,/保留/);assert.match(ids['kingdom-input'].value,/90000/);assert.equal(plan.revision,0);
  fail=false;await click('create-town');assert.equal(plan.revision,1);assert.equal(ids['kingdom-publish-town'].disabled,false);
  await click('publish-town');assert.match(ids['kingdom-town'].textContent,/tv1/);
  await click('layout');assert.match(ids['kingdom-town'].textContent,/layout/);
  await click('publish');assert.equal(plan.status,'published');assert.equal(ids['kingdom-publish'].disabled,true);
  assert(requests.some(r=>r.method==='POST'&&r.p.includes('/settlements?polity_id=kingdom-1')&&r.body.count===3));
  assert.equal(requests.some(r=>r.p.includes('/activate')),false);
  console.log('kingdom UI: fixed background, sites, missing inputs, failure preservation, town and kingdom publication passed');
}
run().catch(error=>{console.error(error);process.exitCode=1});
