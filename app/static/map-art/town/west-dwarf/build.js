#!/usr/bin/env node
/* 生成 sprite.svg 与 meta.json，并做规范第 6 节的静态自检：node build.js */
'use strict';
var fs = require('fs'), path = require('path');
var WD = require('./west-dwarf.js');

var list = WD.symbols();
var ids = {}, bad = 0;
function err(m) { console.error(m); bad++; }
list.forEach(function (s) {
  if (!/^west-dwarf-[a-z0-9-]+$/.test(s.id)) err('bad id ' + s.id);
  if (ids[s.id]) err('duplicate symbol id ' + s.id);
  ids[s.id] = 1;
  if (s.over) err('too tall (' + s.up + ' px > ' + WD.MAX_UP + '): ' + s.id);
  var fa = s.meta.facility;
  if (fa !== null && WD.FACILITY.indexOf(fa) < 0) err('facility not in FacilityKind: ' + fa + ' (' + s.id + ')');
  if (/NaN|undefined/.test(s.body)) err('NaN/undefined in body: ' + s.id);
  if (/(width|height|r|rx|ry)="-/.test(s.body)) err('negative size in body: ' + s.id);
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
});
var svg = '<?xml version="1.0" encoding="UTF-8"?>\n' + WD.spriteSVG(list).replace(' width="0" height="0" style="position:absolute;overflow:hidden"', '') + '\n';
var meta = list.map(function (s) { return s.meta; });
// meta 与 symbol 一一对应
var symIds = (svg.match(/<symbol id="[^"]+"/g) || []).map(function (t) { return t.slice(12, -1); });
if (symIds.length !== meta.length) err('symbol count ' + symIds.length + ' != meta ' + meta.length);
meta.forEach(function (m, i) { if (symIds[i] !== m.id) err('meta/symbol mismatch at ' + i + ': ' + m.id); });
fs.writeFileSync(path.join(__dirname, 'sprite.svg'), svg);
fs.writeFileSync(path.join(__dirname, 'meta.json'), JSON.stringify(meta, null, 1) + '\n');
var cat = {}, fac = {};
list.forEach(function (s) {
  cat[s.meta.category] = (cat[s.meta.category] || 0) + 1;
  if (s.meta.facility) fac[s.meta.facility] = 1;
});
console.log('symbols: ' + list.length + ' ' + JSON.stringify(cat) + ', house types: ' + WD.HOUSE_TYPES.length +
  ', facilities: ' + Object.keys(fac).join(',') + ', max up ' + Math.max.apply(null, list.map(function (s) { return s.up; })) +
  ' px, sprite ' + Math.round(svg.length / 1024) + ' KB');
if (bad) { console.error(bad + ' problem(s)'); process.exit(1); }
