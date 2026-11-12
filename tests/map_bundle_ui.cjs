/* No browser, dependencies, server, or production data. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
class Element {
  constructor(tag) { this.tagName = tag; this.children = []; this.dataset = {}; this.style = {}; this.attributes = {}; this._text = ''; this._value = ''; this.hidden = false; this.naturalWidth = 1200; this.naturalHeight = 900; }
  set textContent(v) { this._text = String(v); this.children = []; }
  get textContent() { return this._text + this.children.map(x => x.textContent).join(''); }
  append(...nodes) { for (const n of nodes) { this.children.push(n); n.parentElement = this; } }
  replaceChildren(...nodes) { this.children = []; this._text = ''; this.append(...nodes); }
  setAttribute(k, v) { this.attributes[k] = String(v); }
  removeAttribute(k) { delete this[k]; delete this.attributes[k]; }
  set value(v) { this._value = String(v); }
  get value() { return this._value || (this.tagName === 'select' ? this.children[0]?.value || '' : ''); }
  getBoundingClientRect() { return this.rect || { left: 10, top: 20, width: 600, height: 450 }; }
}
function descendants(e) { return [e, ...e.children.flatMap(descendants)]; }
function find(e, pred) { return descendants(e).find(pred); }
const tick = () => new Promise(resolve => setImmediate(resolve));
function setup(mode = 'author') {
  const author = new Element('div'), player = new Element('div'), listeners = {}, calls = [], fetched = [], revoked = [], created = [];
  const window = { __tdNativeMode: mode, __textileDreamToken: 'secret', __tdMapPolicy: { civ_atlas_enabled: false }, addEventListener(name, cb) { listeners[name] = cb; }, PlayUI: { refreshMap() { calls.push('player-map'); } } };
  const document = { createElement: tag => new Element(tag), getElementById: id => id === 'native-map-host' ? author : id === 'player-map-host' ? player : null, querySelector: () => null, head: new Element('head') };
  const geo = { georeferenced: true, image_size: [1200, 900], map_rect: { x: 100, y: 50, width: 1000, height: 800 }, world_extent_m: [-200, -400, 800, 400] };
  const response = { id: 'terragenesis-world-20261111', title: 'fixture', previews: [
    { ...geo, key: 'atlas', title: 'Year-1 environment atlas', months: [] },
    { key: 'climate-topics', title: '气候专题', months: [], georeferenced: false },
    { ...geo, key: 'ocean-composite', title: '洋流路线', months: [1, 7] },
    { ...geo, key: 'ocean-overlay', title: 'ocean-overlay', months: [1, 7] }
  ] };
  const context = vm.createContext({ window, document, console, AbortController,
    URL: { createObjectURL(blob) { const u = 'blob:fixture-' + created.length; created.push(u); return u; }, revokeObjectURL(u) { revoked.push(u); } },
    async api(p, method, body) { calls.push({ p, method, body }); return p.endsWith('/point') ? { groups: { terrain: { values: { elevation_m: 0, lake: null, glacier_ice_thickness_m: 12.34567890123456 }, units: { elevation_m: 'm' } }, surface_water: { values: { lake_stage_m: 15, lake_depth_m: 2, hillslope_discharge_m3_s: null }, units: { lake_stage_m: 'm', lake_depth_m: 'm' } } }, warnings: ['潜在湖未验证'] } : response; },
    async fetch(p, options) { fetched.push({ p, options }); return { ok: true, blob: async () => ({}) }; }
  });
  const root = path.resolve(__dirname, '../app/static');
  vm.runInContext(fs.readFileSync(path.join(root, 'map-bundle.js'), 'utf8'), context);
  function native() { vm.runInContext(fs.readFileSync(path.join(root, 'native-map.js'), 'utf8'), context); }
  function switchMode(next) { window.__tdNativeMode = next; listeners['td-native-mode']({ detail: { mode: next } }); }
  return { window, context, author, player, calls, fetched, revoked, created, response, native, switchMode };
}
async function run() {
  const env = setup();
  const ui = env.window.TDMapBundle;
  const image = new Element('img');
  const frame = { rect: { x: 100, y: 50, width: 1000, height: 800 }, extent: { x_min: -200, x_max: 800, z_min: -400, z_max: 400 } };
  let point = ui.imagePoint(image, frame, 310, 245, false);
  assert.equal(point.x_m, 300); assert.equal(point.z_m, 0);
  image.rect = { left: -700, top: -200, width: 2400, height: 1800 };
  point = ui.imagePoint(image, frame, 500, 700, false);
  assert.equal(point.x_m, 300); assert.equal(point.z_m, 0); // zoom + pan uses current bounding rect
  assert.equal(ui.imagePoint(image, frame, -700, -200, false), null); // margins
  assert.equal(ui.imagePoint(image, frame, 500, 700, true), null); // panel never maps
  assert.equal(ui.imagePoint(image, null, 500, 700, false), null);
  assert.equal(ui.available({ months: [1, 7] }, 2), false);
  assert.equal(ui.available({ months: [1, 7] }, 7), true);
  assert.equal(ui.available({ months: [] }, 12), true);
  assert.equal(ui.display(null, 'mm'), '未提供'); assert.equal(ui.display(0, 'mm'), '0 mm');
  assert.equal(ui.display(12.34567890123456, 'm'), '12.35 m');
  assert.equal(ui.display(0.000012345678, 'm/s'), '1.235e-5 m/s');
  assert.equal(ui.display(1200000, 'm3'), '1.2e+6 m3');
  assert.equal(ui.display(-0.0001, 'm/s'), '-1e-4 m/s');
  const six = setup();
  six.response.groups = { surface_water: { fields: {} } };
  six.response.previews[0].surface_water_identity = 'surface-fixture';
  six.response.previews[0].title = '实际月湖河'; six.response.previews[0].months = [1, 7, 12];
  six.native(); await tick(); await tick();
  assert.match(six.author.textContent, /实际月湖是空库存有限首年/);
  assert.match(six.author.textContent, /实际月湖河/);
  six.switchMode('player');
  const player = setup('player'); player.native(); await tick();
  assert.equal(player.calls.length, 1); assert.equal(player.calls[0], 'player-map');
  assert.equal(player.fetched.length, 0); assert.equal(player.author.hidden, true);
  const mountPlayer = player.window.TDMapBundle.mount(player.author); await tick();
  assert.equal(player.calls.length, 1); mountPlayer.unmount();
  // Async detail arriving after player transition must not fetch an author image.
  const late = setup(); let finishDetail;
  late.context.api = () => new Promise(resolve => { finishDetail = resolve; });
  late.native(); late.switchMode('player'); finishDetail(late.response); await tick();
  assert.equal(late.fetched.length, 0); assert.equal(late.author.children.length, 0);
  // Blob read finishing after dispose must not create or leak an ObjectURL.
  const lateBlob = setup(); let finishBlob;
  lateBlob.context.fetch = async () => ({ ok: true, blob: () => new Promise(resolve => { finishBlob = resolve; }) });
  lateBlob.native(); await tick(); lateBlob.switchMode('player'); finishBlob({}); await tick();
  assert.equal(lateBlob.created.length, 0); assert.equal(lateBlob.author.children.length, 0);
  console.log('map-bundle core/initial player and stale response isolation OK');
  return env;
}
run().then(async env => {
  env.native(); await tick(); await tick();
  assert.equal(env.calls.filter(c => c.p?.includes('/inner/map-bundles/')).length, 1);
  assert.equal(env.fetched.some(c => c.p.includes('/native-map/')), false); // civ opt-in is off
  assert.equal(env.fetched.length, 1);
  assert.equal(env.fetched[0].options.headers['X-TextileDream-Token'], 'secret');
  assert.match(env.fetched[0].p, /preview\/atlas\?month=1$/);
  const select = find(env.author, e => e.attributes['aria-label'] === '地图图层');
  const month = find(env.author, e => e.attributes['aria-label'] === '月份');
  const image = find(env.author, e => e.className === 'map-bundle-base');
  const overlay = find(env.author, e => e.tagName === 'input');
  assert.equal(select.children.find(o => o.value === 'atlas').textContent, '自然总览');
  assert.equal(image.alt, '自然总览'); assert.match(overlay.parentElement.textContent, /洋流透明层/);
  image.onload();
  await image.onclick({ clientX: 310, clientY: 245 }); await tick();
  let point = env.calls.find(c => c.p?.endsWith('/point'));
  assert.equal(point.body.x_m, 300); assert.equal(point.body.z_m, 0); assert.equal(point.body.month, 1);
  assert.match(env.author.textContent, /海拔0 m/); assert.match(env.author.textContent, /未提供/);
   assert.match(env.author.textContent, /年末选区冰厚12.35/);
   assert.match(env.author.textContent, /月湖 \/ 实际地表水/);
   assert.match(env.author.textContent, /本月实际水位15 m/);
   assert.match(env.author.textContent, /坡面 Q（不含湖内部 \/ 溢流）未提供/);
  assert.equal(find(env.author, e => e.tagName === 'dd' && e.textContent === '12.35').title, '12.34567890123456');
  const firstUrl = env.created[0];
  overlay.checked = true; overlay.onchange(); await tick(); await tick();
  assert.ok(env.revoked.includes(firstUrl));
  assert.ok(env.fetched.some(c => c.p.includes('preview/ocean-overlay')));
  assert.equal(find(env.author, e => e.className === 'map-bundle-overlay').style.width, '100%');
  select.value = 'climate-topics'; select.onchange(); await tick(); await tick(); image.onload();
  const beforePanel = env.calls.length;
  image.onclick({ clientX: 310, clientY: 245 }); await tick();
  assert.equal(env.calls.length, beforePanel); assert.equal(overlay.disabled, true);
  select.value = 'ocean-composite'; select.onchange(); await tick(); await tick();
  const fetchedBefore = env.fetched.length;
  month.value = '2'; month.onchange(); await tick(); await tick();
  assert.equal(env.fetched.length, fetchedBefore); // does not silently substitute Jan or July
  assert.equal(image.hidden, true); assert.equal(overlay.disabled, true);
  assert.equal(select.children.find(o => o.value === 'ocean-composite').disabled, true);
  assert.match(env.author.textContent, /未提供 2 月存图/);
  month.value = '7'; month.onchange(); await tick(); await tick();
  assert.equal(overlay.disabled, false); assert.ok(env.fetched.some(c => c.p.endsWith('?month=7')));
  const count = env.fetched.length;
  env.switchMode('player'); await tick();
  assert.equal(env.author.children.length, 0); assert.equal(env.author.hidden, true); assert.equal(env.player.hidden, false);
  assert.equal(env.created.length, env.revoked.length); // every author ObjectURL released
  assert.equal(env.fetched.length, count);
  console.log('map-bundle DOM mount/unmount, token/blob/revoke, panel, point, month availability OK');
}).catch(error => { console.error(error); process.exitCode = 1; });
