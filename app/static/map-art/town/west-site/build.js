// node build.js —— 生成 sprite.svg 与 meta.json（纯程序化，不读外部图片），并做基础自检
'use strict';
var fs = require('fs'), path = require('path');
var WS = require('./west-site.js');
var items = WS.build();
var svg = '<?xml version="1.0" encoding="UTF-8"?>\n' + WS.sprite(items) + '\n';
fs.writeFileSync(path.join(__dirname, 'sprite.svg'), svg);
fs.writeFileSync(path.join(__dirname, 'meta.json'), JSON.stringify(items.map(function (i) { return i.meta; }), null, 2) + '\n');

var FAC = 'town_hall lord_hall market_hall granary cistern well mill forge smelter kiln tannery barracks watchtower city_wall gate temple academy infirmary inn caravanserai stable dock warehouse mine_head boiler_house ward_tower cemetery bridge'.split(' ');
var RES = 'grain timber stone clay iron copper tin coal salt livestock fish herb wool gold rare_metals reed silver gems marble sulfur spices silk horses ivory amber pearls wine dye mana dragonbone'.split(' ');
var bad = [];
items.forEach(function (i) {
  var m = i.meta;
  if (m.facility !== null && FAC.indexOf(m.facility) < 0) bad.push(m.id + ' facility=' + m.facility);
  if (RES.indexOf(m.resource) < 0) bad.push(m.id + ' resource=' + m.resource);
  if (m.category === 'site' && (m.footprint[0] < 2 || m.footprint[1] < 2 || m.height_px > 144)) bad.push(m.id + ' site 占地/上伸越界');
  if (m.category === 'prop' && (m.footprint[0] !== 1 || m.footprint[1] !== 1 || m.height_px > 48)) bad.push(m.id + ' prop 占地/上伸越界');
});
// 内部 id 唯一
var ids = {}, re = /\sid="([^"]+)"/g, mm;
while ((mm = re.exec(svg))) { if (ids[mm[1]]) bad.push('重复内部 id ' + mm[1]); ids[mm[1]] = 1; }
var cats = {};
items.forEach(function (i) { cats[i.meta.category] = (cats[i.meta.category] || 0) + 1; });
console.log('symbols', items.length, JSON.stringify(cats), 'svg bytes', svg.length);
if (bad.length) { console.error(bad.join('\n')); process.exit(1); }
