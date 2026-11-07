// node build.js —— 生成 sprite.svg 与 meta.json（纯程序化，不读外部图片），并做自检
// 自检：facility / resource / subtype 合法、占地上伸、内部 id 唯一、与 town/ 下其他目录 symbol id 不撞名（只读扫描它们的 sprite.svg）
'use strict';
var fs = require('fs'), path = require('path');
var WS = require('./west-site-2.js');
var items = WS.build();
var svg = '<?xml version="1.0" encoding="UTF-8"?>\n' + WS.sprite(items) + '\n';
fs.writeFileSync(path.join(__dirname, 'sprite.svg'), svg);
fs.writeFileSync(path.join(__dirname, 'meta.json'), JSON.stringify(items.map(function (i) { return i.meta; }), null, 2) + '\n');

var FAC = 'town_hall lord_hall market_hall granary cistern well mill forge smelter kiln tannery barracks watchtower city_wall gate temple academy infirmary inn caravanserai stable dock warehouse mine_head boiler_house ward_tower cemetery bridge'.split(' ');
var RES = 'grain timber stone clay iron copper tin coal salt livestock fish herb wool gold rare_metals reed silver gems marble sulfur spices silk horses ivory amber pearls wine dye mana dragonbone lapis'.split(' ');
var SUB = {
  grain: 'wheat_farm rice_paddy millet_farm vegetable_farm orchard olive_grove flax_farm cotton_farm'.split(' '),
  livestock: 'cattle_ranch dairy_farm pig_farm goat_farm poultry_farm apiary'.split(' '),
  wool: ['sheep_station'], horses: ['horse_stud']
};
var bad = [];
items.forEach(function (i) {
  var m = i.meta;
  if (m.facility !== null && FAC.indexOf(m.facility) < 0) bad.push(m.id + ' facility=' + m.facility);
  if (m.facility === null && !m.note) bad.push(m.id + ' facility=null 但缺 note');
  if (RES.indexOf(m.resource) < 0) bad.push(m.id + ' resource=' + m.resource);
  if (SUB[m.resource]) {
    if (SUB[m.resource].indexOf(m.subtype) < 0) bad.push(m.id + ' 农牧 subtype 非法: ' + m.subtype);
  } else if (m.subtype !== null && !/^[a-z][a-z_]*$/.test(m.subtype)) bad.push(m.id + ' subtype 格式: ' + m.subtype);
  if (m.category === 'site' && (m.footprint[0] < 2 || m.footprint[1] < 2 || m.footprint[0] > 5 || m.footprint[1] > 4 || m.height_px > 144)) bad.push(m.id + ' site 占地/上伸越界');
  if (m.category === 'prop' && (m.footprint[0] !== 1 || m.footprint[1] !== 1 || m.height_px > 48)) bad.push(m.id + ' prop 占地/上伸越界');
  if (svg.indexOf('<symbol id="' + m.id + '"') < 0) bad.push(m.id + ' 缺 symbol');
});
// symbol 数与 meta 数一致
var nSym = (svg.match(/<symbol /g) || []).length;
if (nSym !== items.length) bad.push('symbol 数 ' + nSym + ' ≠ meta 数 ' + items.length);
// 内部 id 唯一
var ids = {}, re = /\sid="([^"]+)"/g, mm;
while ((mm = re.exec(svg))) { if (ids[mm[1]]) bad.push('重复内部 id ' + mm[1]); ids[mm[1]] = 1; }
// 与 town/ 下其他目录撞名（只读）
var town = path.join(__dirname, '..'), others = 0;
fs.readdirSync(town).forEach(function (d) {
  if (d === path.basename(__dirname)) return;
  var dir = path.join(town, d);
  if (!fs.statSync(dir).isDirectory()) return;
  ['sprite.svg', 'meta.json'].forEach(function (fn) {
    var p = path.join(dir, fn);
    if (!fs.existsSync(p)) return;
    var t = fs.readFileSync(p, 'utf8'), r2 = /"?id"?\s*[:=]\s*"([^"]+)"/g, m2;
    while ((m2 = r2.exec(t))) { others++; if (ids[m2[1]]) bad.push('与 ' + d + '/' + fn + ' 撞名 ' + m2[1]); }
  });
});
var cats = {};
items.forEach(function (i) { cats[i.meta.category] = (cats[i.meta.category] || 0) + 1; });
console.log('symbols', items.length, JSON.stringify(cats), 'svg bytes', svg.length, 'scanned other ids', others);
if (bad.length) { console.error(bad.join('\n')); process.exit(1); }
console.log('OK');
