// node build.js —— 生成 sprite.svg 与 meta.json，并自检：id 唯一（含与 town/ 下其他目录）、facility / resource / subtype 合法、尺寸范围、内部 id 前缀、场景引用。
'use strict';
const fs = require('fs');
const path = require('path');
const ES = require('./east-site-2.js');

const FAC = 'town_hall lord_hall market_hall granary cistern well mill forge smelter kiln tannery barracks watchtower city_wall gate temple academy infirmary inn caravanserai stable dock warehouse mine_head boiler_house ward_tower cemetery bridge'.split(' ');
const RES = 'grain timber stone clay iron copper tin coal salt livestock fish herb wool gold rare_metals reed silver gems marble sulfur spices silk horses ivory amber pearls wine dye mana dragonbone lapis'.split(' ');
const SUB = {
  grain: 'wheat_farm rice_paddy millet_farm vegetable_farm orchard olive_grove flax_farm cotton_farm'.split(' '),
  livestock: 'cattle_ranch dairy_farm pig_farm goat_farm poultry_farm apiary'.split(' '),
  wool: ['sheep_station'], horses: ['horse_stud']
};

const out = ES.buildAll();
const errs = [];
const seen = new Set();
// 其他目录已有的 id
const townDir = path.join(__dirname, '..');
const foreign = new Map();
for (const d of fs.readdirSync(townDir)) {
  const fp = path.join(townDir, d);
  if (d === path.basename(__dirname) || !fs.statSync(fp).isDirectory()) continue;
  for (const fn of ['sprite.svg', 'meta.json']) {
    const p2 = path.join(fp, fn);
    if (!fs.existsSync(p2)) continue;
    const txt = fs.readFileSync(p2, 'utf8');
    for (const m of txt.matchAll(/(?:<symbol id=|"id":\s*)"([^"]+)"/g)) foreign.set(m[1], d);
  }
}
for (const it of out.items) {
  const m = it.meta;
  if (seen.has(m.id)) errs.push('重复 id ' + m.id);
  seen.add(m.id);
  if (foreign.has(m.id)) errs.push(m.id + ' 与 ' + foreign.get(m.id) + '/ 撞名');
  if (m.facility !== null && !FAC.includes(m.facility)) errs.push(m.id + ' facility 非法 ' + m.facility);
  if (m.facility === null && m.category === 'site' && !m.note) errs.push(m.id + ' facility=null 但无 note');
  if (!RES.includes(m.resource)) errs.push(m.id + ' resource 非法 ' + m.resource);
  if (SUB[m.resource] && m.category === 'site' && !SUB[m.resource].includes(m.subtype)) errs.push(m.id + ' subtype 缺失或非法 ' + m.subtype);
  if (m.subtype != null && !/^[a-z_]+$/.test(m.subtype)) errs.push(m.id + ' subtype 格式');
  if (!/^east-common-(site|prop|ground)-[a-z0-9-]+$/.test(m.id)) errs.push(m.id + ' id 格式');
  if (m.category === 'site' && (m.height_px > 144 || m.footprint[0] < 2 || m.footprint[1] < 2 || m.footprint[0] > 5 || m.footprint[1] > 4)) errs.push(m.id + ' site 尺寸越界');
  if (m.category === 'prop' && (m.height_px > 48 || m.footprint[0] !== 1 || m.footprint[1] !== 1)) errs.push(m.id + ' prop 尺寸越界');
  if (m.category === 'ground' && (m.height_px !== 0 || m.footprint[0] !== 1 || m.footprint[1] !== 1)) errs.push(m.id + ' ground 尺寸');
  const inner = [...it.svg.matchAll(/ id="([^"]+)"/g)].map(x => x[1]);
  for (const iid of inner) if (iid !== m.id && !iid.startsWith(m.id + '-')) errs.push(m.id + ' 内部 id 未带前缀 ' + iid);
}
// 场景引用的 id 都存在
for (const sc of out.scenes) {
  const refs = [sc.site[0]].concat(sc.props.map(p => p[0]), sc.ground ? sc.ground.map(g => g[0]) : []);
  for (const r of refs) if (!seen.has(r)) errs.push('场景 ' + sc.key + ' 引用不存在的 ' + r);
}
const sprite = out.spriteSvg();
fs.writeFileSync(path.join(__dirname, 'sprite.svg'), sprite);
fs.writeFileSync(path.join(__dirname, 'meta.json'), JSON.stringify(out.items.map(i => i.meta), null, 2) + '\n');
const nSym = (sprite.match(/<symbol /g) || []).length;
if (nSym !== out.items.length) errs.push('symbol 数 ' + nSym + ' ≠ meta 数 ' + out.items.length);
const cnt = {};
out.items.forEach(i => { cnt[i.meta.category] = (cnt[i.meta.category] || 0) + 1; });
console.log('items', out.items.length, JSON.stringify(cnt), 'scenes', out.scenes.length, 'foreign ids', foreign.size);
if (errs.length) { console.error(errs.join('\n')); process.exit(1); }
console.log('OK');
