// node build.js → sprite.svg + meta.json（纯程序化，不读外部图片）
'use strict';
const fs = require('fs');
const path = require('path');
const A = require('./east-fort.js');
const FAC = 'town_hall lord_hall market_hall granary cistern well mill forge smelter kiln tannery barracks watchtower city_wall gate temple academy infirmary inn caravanserai stable dock warehouse mine_head boiler_house ward_tower cemetery bridge'.split(' ');
const list = A.items();
const ids = new Set();
let bad = 0;
for (const it of list) {
  if (ids.has(it.id)) { console.error('重复 id', it.id); bad++; }
  ids.add(it.id);
  if (it.meta.facility !== null && FAC.indexOf(it.meta.facility) < 0) { console.error('facility 不在 28 种内', it.id, it.meta.facility); bad++; }
  const lim = it.meta.category === 'landmark' ? 240 : 144;
  if (it.meta.height_px > lim) { console.error('上伸超限', it.id, it.meta.height_px); bad++; }
}
fs.writeFileSync(path.join(__dirname, 'sprite.svg'), A.spriteSvg(list));
fs.writeFileSync(path.join(__dirname, 'meta.json'), JSON.stringify(list.map(it => it.meta), null, 1));
console.log('symbols', list.length, 'errors', bad);
for (const it of list) console.log(it.id, it.meta.footprint.join('x'), 'up', it.meta.height_px, it.meta.facility);
process.exitCode = bad ? 1 : 0;
