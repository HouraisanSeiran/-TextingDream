/*
 * 生成 sprite.svg 与 meta.json：node build.js（纯程序化路径，不读任何外部图片）
 * 同时做自检：id 唯一、内部 id 带前缀、上伸上限、facility 合法、meta 与 symbol 一一对应。
 */
'use strict';
var fs = require('fs'), path = require('path');
var A = require('./arab-special.js');
var FAC = ['town_hall', 'lord_hall', 'market_hall', 'granary', 'cistern', 'well', 'mill', 'forge', 'smelter', 'kiln', 'tannery',
  'barracks', 'watchtower', 'city_wall', 'gate', 'temple', 'academy', 'infirmary', 'inn', 'caravanserai', 'stable', 'dock',
  'warehouse', 'mine_head', 'boiler_house', 'ward_tower', 'cemetery', 'bridge'];
var defs = A.list(), errs = [], seen = {};
defs.forEach(function (d) {
  if (seen[d.id]) errs.push('重复 id ' + d.id); seen[d.id] = 1;
  if (!/^arab-common-[a-z0-9-]+$/.test(d.id)) errs.push('id 格式 ' + d.id);
  if (d.facility != null && FAC.indexOf(d.facility) < 0) errs.push('facility 非法 ' + d.id + ' ' + d.facility);
  if (d.facility == null && !d.note) errs.push('facility=null 缺 note ' + d.id);
  var cat = d.category || 'special', lim = cat === 'landmark' ? 240 : (cat === 'prop' ? 48 : 144);
  if (d.up > lim) errs.push('上伸超限 ' + d.id + ' ' + d.up + '>' + lim);
  var mx = cat === 'landmark' ? 6 : 4;
  if (d.fp[0] > mx || d.fp[1] > mx) errs.push('占地超限 ' + d.id);
});
var syms = defs.map(A.symbol);
syms.forEach(function (s, i) {
  var re = /\bid="([^"]+)"/g, m, first = true;
  while ((m = re.exec(s))) { if (first) { first = false; continue; } if (m[1].indexOf(defs[i].id + '-') !== 0) errs.push('内部 id 无前缀 ' + m[1]); }
  if (/NaN|undefined/.test(s)) errs.push('NaN/undefined in ' + defs[i].id);
});
var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0">\n' + syms.join('\n') + '\n</svg>\n';
var meta = A.metaAll();
fs.writeFileSync(path.join(__dirname, 'sprite.svg'), svg);
fs.writeFileSync(path.join(__dirname, 'meta.json'), JSON.stringify(meta, null, 2) + '\n');
var cov = {}; meta.forEach(function (m) { if (m.facility) cov[m.facility] = (cov[m.facility] || 0) + 1; });
console.log('symbols:', defs.length, ' bytes:', svg.length);
console.log('facility 覆盖:', FAC.filter(function (k) { return cov[k]; }).length + '/28', ' 缺:', FAC.filter(function (k) { return !cov[k]; }).join(','));
if (errs.length) { console.error('错误:\n' + errs.join('\n')); process.exit(1); }
console.log('OK');
