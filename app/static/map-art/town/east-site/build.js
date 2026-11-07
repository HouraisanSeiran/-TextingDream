// node build.js —— 生成 sprite.svg 与 meta.json，并做基本自检（id 唯一、facility 合法、resource 合法、占地与上伸范围）。
'use strict';
const fs = require('fs');
const path = require('path');
const ES = require('./east-site.js');

const FAC = 'town_hall lord_hall market_hall granary cistern well mill forge smelter kiln tannery barracks watchtower city_wall gate temple academy infirmary inn caravanserai stable dock warehouse mine_head boiler_house ward_tower cemetery bridge'.split(' ');
const RES = 'grain timber stone clay iron copper tin coal salt livestock fish herb wool gold rare_metals reed silver gems marble sulfur spices silk horses ivory amber pearls wine dye mana dragonbone'.split(' ');

const out = ES.buildAll();
const errs = [];
const seen = new Set();
for (const it of out.items) {
  const m = it.meta;
  if (seen.has(m.id)) errs.push('重复 id ' + m.id);
  seen.add(m.id);
  if (m.facility !== null && !FAC.includes(m.facility)) errs.push(m.id + ' facility 非法 ' + m.facility);
  if (!RES.includes(m.resource)) errs.push(m.id + ' resource 非法 ' + m.resource);
  if (!/^east-common-(site|prop|ground)-[a-z0-9-]+$/.test(m.id)) errs.push(m.id + ' id 格式');
  if (m.category === 'site' && (m.height_px > 144 || m.footprint[0] < 2 || m.footprint[1] < 2)) errs.push(m.id + ' site 尺寸越界');
  if (m.category === 'prop' && (m.height_px > 48 || m.footprint[0] !== 1 || m.footprint[1] !== 1)) errs.push(m.id + ' prop 尺寸越界');
  // symbol 内部 id 必须带 symbol 前缀
  const inner = [...it.svg.matchAll(/ id="([^"]+)"/g)].map(x => x[1]);
  for (const iid of inner) {
    if (iid !== m.id && !iid.startsWith(m.id + '-')) errs.push(m.id + ' 内部 id 无前缀 ' + iid);
    if (iid !== m.id) { if (seen.has(iid)) errs.push('内部 id 重复 ' + iid); seen.add(iid); }
  }
}
fs.writeFileSync(path.join(__dirname, 'sprite.svg'), out.spriteSvg());
fs.writeFileSync(path.join(__dirname, 'meta.json'), JSON.stringify(out.items.map(i => i.meta), null, 1) + '\n');
const cnt = {};
out.items.forEach(i => { cnt[i.meta.category] = (cnt[i.meta.category] || 0) + 1; });
console.log('symbols', out.items.length, JSON.stringify(cnt));
if (errs.length) { console.error(errs.join('\n')); process.exit(1); }
