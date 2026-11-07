'use strict';
// 信息栏交易卡：当前地点商人的开价 / 收购价、集市日，以及买 / 卖 / 以物易物 / 讨价还价入口。
// 数据只来自 current.trade（服务端 trade.surface，不含底价与商人账户余额）；所有作者文本一律
// 用 el()（textContent）写入，不用 innerHTML。点击入口走既有的「确认预览 → 带凭据执行」流程：
// GET /sessions/{id}/confirm/{action_id} 取预览与 confirm，再 POST /sessions/{id}/chat。
window.addEventListener('DOMContentLoaded',()=>{
 const card=el('details');card.id='trade-card';card.className='info-card trade-card';card.hidden=true;
 card.append(el('summary','集市与商人'));
 const body=el('div','',' trade-body');card.append(body);
 const anchor=$('world-systems')||$('info-local');anchor.after(card);
 let pending=null;      // {id, preview}：等待玩家确认的交易
 let lastOutcome='';    // 最近一次已结算交易的说明
 const MODE={buy:'购买',sell:'出售',barter:'以物易物',haggle:'讨价还价'};

 async function preview(id){
  const item=await api('/sessions/'+current.id+'/confirm/'+encodeURIComponent(id));
  pending={id,item};draw();
 }
 async function commit(){
  if(!pending)return;const {id,item}=pending;
  try{
   current=await api('/sessions/'+current.id+'/chat','POST',
    {message:item.label,action_id:id,channel:'action',confirm:item.confirm});
   const t=current.local_result&&current.local_result.trade;
   lastOutcome=t?t.outcome:'';
  }finally{pending=null}
  render();
 }
 function act(text,id,cls){
  const b=button(text,()=>preview(id),cls||'trade-act');
  if(current&&current.trade&&current.trade.busy)b.disabled=true;
  return b;
 }
 function row(text,note,btns){
  const r=el('div',undefined,'trade-row');
  const t=el('span',text,'trade-text');r.append(t);
  if(note)r.append(el('small',note,'trade-note'));
  const box=el('span',undefined,'trade-btns');btns.forEach(b=>b&&box.append(b));r.append(box);
  return r;
 }
 function drawPending(){
  const t=pending.item.trade||{};const box=el('div',undefined,'trade-confirm');
  box.append(el('strong',`${MODE[t.mode]||'交易'}：${pending.item.label}`));
  const lines=[];
  if(t.mode==='barter'&&t.give)lines.push(`付出 ${t.give.qty}${t.give.unit||''}${t.give.good}，换 1${t.unit||''}${t.good}`);
  else if(t.mode==='haggle')lines.push(`开价 ${t.unit_price} ${t.currency}；${t.note||''}`);
  else lines.push(`${t.qty}${t.unit||''}${t.good}，单价 ${t.unit_price}，合计 ${t.total} ${t.currency}`);
  if(t.notes&&t.notes.length)lines.push('价格因素：'+t.notes.join('、'));
  lines.push('口头谈妥不改变钱和货，以确认后的结算为准。');
  lines.forEach(x=>box.append(el('p',x)));
  const bar=el('div',undefined,'trade-btns');
  bar.append(button('确认',commit,'trade-ok'),button('取消',()=>{pending=null;draw()},'trade-cancel'));
  box.append(bar);body.append(box);
 }
 function draw(){
  body.replaceChildren();
  const t=current&&current.trade;
  card.hidden=!t;if(!t)return;
  const market=t.market_day_today?'今天是集市日':`下个集市日在 ${t.next_market_in} 天后`;
  body.append(el('p',`${t.regime} · ${t.season} · 第 ${t.day} 天 · ${market}`,'trade-head'));
  body.append(el('p',`随身钱：${t.wallet} ${t.currency}`));
  if(t.bag.length)body.append(el('p','货物袋：'+t.bag.map(b=>`${b.name} ×${b.qty}${b.unit||''}`).join('、')));
  if(lastOutcome)body.append(el('p',lastOutcome,'trade-outcome'));
  if(pending)drawPending();
  if(t.busy)body.append(el('small','正在处理事件，事件结束后才能交易。'));
  if(!t.merchants.length)body.append(el('small','这里没有商人。'));
  for(const m of t.merchants){
   const sec=el('div',undefined,'trade-merchant');
   sec.append(el('h4',m.name+(m.open_today?'':'（今天不营业）')));
   for(const g of m.sells){
    sec.append(row(`${g.name} 开价 ${g.ask}`,g.reason||g.notes.join('、'),
     [g.buy_action?act('买',g.buy_action):null,g.haggle_action?act('讨价还价',g.haggle_action):null]));
   }
   for(const g of m.buys){
    sec.append(row(`${g.name} 收购 ${g.bid}（你有 ${g.have}）`,g.available?g.notes.join('、'):'今天不收',
     [g.sell_action?act('卖',g.sell_action):null]));
   }
   for(const b of m.barter){
    sec.append(row(`用 ${b.need}${b.unit||''}${b.give} 换 ${b.get}`,`你有 ${b.have}`,
     [b.action?act('易货',b.action):null]));
   }
   body.append(sec);
  }
 }
 const previous=render;
 render=function(){previous();pending=pending&&current&&current.trade?pending:null;draw()};
 draw();
});
