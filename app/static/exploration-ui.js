/* Two scales, one session location. Travel always settles through the server. */
(() => {
  'use strict';
  let scale = 'town', sessionId = null, pending = null, busy = false;
  const panel = document.createElement('section');
  panel.id = 'exploration-panel';
  panel.hidden = true;
  panel.setAttribute('aria-label', '城镇与旅行');
  const townMap = document.createElement('div');
  townMap.id = 'exploration-town-map';
  townMap.hidden = true;
  const dialog = document.createElement('dialog');
  dialog.id = 'travel-confirm';
  dialog.innerHTML = '<h2>确认出发</h2><p id="travel-summary"></p><div class="toolbar"><button id="travel-cancel" type="button">再想想</button><button id="travel-go" class="primary" type="button">出发</button></div>';
  document.body.append(dialog);
  const node = (tag, text) => { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; return e; };
  const svgNode = (tag, attrs) => { const e = document.createElementNS('http://www.w3.org/2000/svg', tag); for (const [k,v] of Object.entries(attrs)) e.setAttribute(k,v); return e; };
  function choose(destination) {
    if (busy || !destination.can_move) return;
    pending = {session: current.id, version: current.exploration.state_version, destination};
    document.getElementById('travel-summary').textContent = '前往' + destination.name + '，预计经过 ' + destination.hours + ' 小时。';
    dialog.showModal();
  }
  window.addEventListener('td-travel-select', event => {
    const destination = current?.exploration?.destinations.find(d => d.id === event.detail);
    if (destination) choose(destination);
  });
  document.getElementById('travel-cancel').onclick = () => { pending = null; dialog.close(); };
  dialog.addEventListener('cancel', () => { pending = null; });
  document.getElementById('travel-go').onclick = async () => {
    if (!pending || busy) return;
    const trip = pending;
    if (current?.id !== trip.session) { dialog.close(); pending = null; return; }
    busy = true;
    document.getElementById('travel-go').disabled = true;
    try {
      const next = await api('/sessions/' + trip.session + '/move', 'POST', {
        location_id: trip.destination.id, expected_version: trip.version});
      dialog.close(); pending = null;
      if (current?.id === trip.session) { current = next; render(); notice('已到达' + next.location); }
    } catch (error) { document.getElementById('travel-summary').textContent = error.message; }
    finally { busy = false; document.getElementById('travel-go').disabled = false; draw(); }
  };
  function draw() {
    const state = current?.exploration;
    panel.hidden = !state;
    townMap.hidden = !state || scale !== 'town' || !state.town;
    if (!state) return;
    if (sessionId !== current.id) { sessionId = current.id; scale = 'town'; }
    townMap.hidden = scale !== 'town' || !state.town;
    panel.replaceChildren(node('strong', current.location));
    const toggles = node('div'); toggles.className = 'toolbar';
    for (const [id, label] of [['world','世界道路'],['town','城镇街区']]) {
      const button = node('button', label); button.type = 'button';
      button.disabled = id === 'town' && !state.town;
      button.setAttribute('aria-pressed', String(scale === id));
      button.onclick = () => { scale = id; draw(); };
      toggles.append(button);
    }
    panel.append(toggles, node('p', state.description));
    const list = node('div'); list.className = 'exploration-destinations';
    for (const destination of state.destinations) {
      const button = node('button', destination.name + ' · ' + destination.hours + '小时');
      button.type = 'button'; button.dataset.destination = destination.id;
      button.disabled = !destination.can_move || busy;
      button.onclick = () => choose(destination); list.append(button);
    }
    panel.append(node('small', current.event ? '先完成当前事件，再出发。' : '选择相邻地点，确认后移动。'), list);
    if (!state.town) return;
    const svg = svgNode('svg', {viewBox:'0 0 600 430', role:'img', 'aria-label':state.town.name + '街区图'});
    const nodes = new Map(state.town.nodes.map(n => [n.id,n]));
    for (const [a,b] of state.town.streets) {
      const [x1,y1] = nodes.get(a).position, [x2,y2] = nodes.get(b).position;
      svg.append(svgNode('line', {x1,y1,x2,y2,stroke:'#b7ad93','stroke-width':12,'stroke-linecap':'round'}));
    }
    for (const place of state.town.nodes) {
      const [x,y] = place.position;
      const here = place.id === state.location_id;
      const destination = state.destinations.find(d => d.id === place.id && d.can_move);
      const group = svgNode('g', {class:here?'town-node current':'town-node',role:'button',tabindex:destination?0:-1,
        'aria-label':place.name + (here?'，你在这里':destination?'，可前往':'，需沿街道前往'),
        'aria-disabled':String(!destination)});
      group.append(svgNode('rect',{x:x-54,y:y-27,width:108,height:54,rx:4,fill:here?'#25483e':'#fbfaf5',stroke:'#7c8975','stroke-width':2}));
      const label = svgNode('text',{x,y:y+5,'text-anchor':'middle',fill:here?'#fff':'#263730','font-size':15});
      label.textContent = place.name; group.append(label);
      if (destination) { group.onclick = () => choose(destination); group.onkeydown = e => { if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(destination);} }; }
      if(here){const marker=svgNode('text',{x,y:y-36,'text-anchor':'middle',fill:'#8c5c32','font-size':16});marker.textContent='▼ 你在这里';group.append(marker);}
      svg.append(group);
    }
    townMap.replaceChildren(svg, node('p','街区示意图 · 根据城址生成公共设施；城内探索按1小时行动刻度结算。'));
  }
  window.addEventListener('DOMContentLoaded', () => {
    document.getElementById('player-map-host').append(townMap, panel);
    const original = render;
    render = function () { const result = original.apply(this, arguments); draw(); return result; };
    draw();
  });
})();
