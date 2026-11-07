#!/usr/bin/env node
/* 生成 sprite.svg 与 meta.json：node build.js（检查 id 唯一、内部 id 前缀、上伸 ≤ 144 px、facility 合法、meta↔symbol 一一对应） */
'use strict';
var fs = require('fs'), path = require('path');
var WE = require('./west-elf.js');

var list = WE.symbols();
var ids = {}, bad = 0;
function err(m) { console.error(m); bad++; }
list.forEach(function (s) {
  if (ids[s.id]) err('duplicate symbol id ' + s.id);
  ids[s.id] = 1;
  if (!/^west-elf-[a-z0-9-]+$/.test(s.id)) err('bad id ' + s.id);
  if (s.over) err('too tall (' + s.up + ' px > ' + WE.MAX_UP + '): ' + s.id);
  var fac = s.meta.facility;
  if (fac !== null && WE.FACILITIES.indexOf(fac) < 0) err('unknown facility ' + fac + ' in ' + s.id);
  if (s.meta.category === 'house' && fac !== null) err('house with facility: ' + s.id);
  if (s.meta.id !== s.id) err('meta id mismatch ' + s.id);
});
// 内部 id 必须带 symbol id 前缀且全目录唯一
var all = {};
list.forEach(function (s) {
  var re = /\bid="([^"]+)"/g, m;
  while ((m = re.exec(s.body))) {
    if (m[1].indexOf(s.id + '-') !== 0) err('inner id without prefix: ' + m[1]);
    if (all[m[1]] || ids[m[1]]) err('inner id clash: ' + m[1]);
    all[m[1]] = 1;
  }
  if (/NaN|undefined|Infinity/.test(s.body)) err('NaN/undefined in ' + s.id);
});
var svg = '<?xml version="1.0" encoding="UTF-8"?>\n' + WE.spriteSVG(list).replace(' width="0" height="0" style="position:absolute;overflow:hidden"', '') + '\n';
fs.writeFileSync(path.join(__dirname, 'sprite.svg'), svg);
var meta = list.map(function (s) { return s.meta; });
fs.writeFileSync(path.join(__dirname, 'meta.json'), JSON.stringify(meta, null, 1) + '\n');
// 回读：sprite 里的 symbol 与 meta 一一对应
var sym = {}, re2 = /<symbol id="([^"]+)"/g, mm, nsym = 0;
while ((mm = re2.exec(svg))) { sym[mm[1]] = 1; nsym++; }
if (nsym !== meta.length) err('symbol count ' + nsym + ' != meta ' + meta.length);
meta.forEach(function (m) { if (!sym[m.id]) err('meta without symbol ' + m.id); });
var cat = {}, fac = {};
list.forEach(function (s) {
  cat[s.meta.category] = (cat[s.meta.category] || 0) + 1;
  if (s.meta.facility) fac[s.meta.facility] = (fac[s.meta.facility] || 0) + 1;
});
var maxUp = list.reduce(function (a, s) { return Math.max(a, s.up); }, 0);
console.log('symbols: ' + list.length + ' ' + JSON.stringify(cat) + ', house types: ' + WE.HOUSE_TYPES.length +
  ', max up ' + maxUp + ' px, sprite ' + Math.round(svg.length / 1024) + ' KB');
console.log('facilities: ' + JSON.stringify(fac));
if (bad) { console.error(bad + ' problem(s)'); process.exit(1); }
