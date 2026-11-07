#!/usr/bin/env node
/* 生成 sprite.svg 与 meta.json：node build.js（顺带检查 id 唯一、内部 id 前缀、与 town/ 下其他目录不重名） */
'use strict';
var fs = require('fs'), path = require('path');
var WG = require('./west-ground.js');

var list = WG.symbols();
var ids = {}, bad = 0;
list.forEach(function (s) {
  if (!/^west-(common|elf|dwarf|orc)-[a-z0-9-]+$/.test(s.id)) { console.error('bad id ' + s.id); bad++; }
  if (ids[s.id]) { console.error('duplicate symbol id ' + s.id); bad++; }
  ids[s.id] = 1;
  if (s.over) { console.error('too tall (' + s.up + ' px > ' + WG.MAX_UP + '): ' + s.id); bad++; }
});
var all = {};
list.forEach(function (s) {
  var re = /\bid="([^"]+)"/g, m;
  while ((m = re.exec(s.body))) {
    if (m[1].indexOf(s.id + '-') !== 0) { console.error('inner id without prefix: ' + m[1]); bad++; }
    if (all[m[1]] || ids[m[1]]) { console.error('inner id clash: ' + m[1]); bad++; }
    all[m[1]] = 1;
  }
});
// 与 town/ 下其他目录的 meta 不重名
var townDir = path.join(__dirname, '..');
fs.readdirSync(townDir).forEach(function (d) {
  var mp = path.join(townDir, d, 'meta.json');
  if (d === path.basename(__dirname) || !fs.existsSync(mp)) return;
  JSON.parse(fs.readFileSync(mp, 'utf8')).forEach(function (m) {
    if (ids[m.id]) { console.error('id clash with ' + d + ': ' + m.id); bad++; }
  });
});
var svg = '<?xml version="1.0" encoding="UTF-8"?>\n' + WG.spriteSVG(list).replace(' width="0" height="0" style="position:absolute;overflow:hidden"', '') + '\n';
fs.writeFileSync(path.join(__dirname, 'sprite.svg'), svg);
fs.writeFileSync(path.join(__dirname, 'meta.json'), JSON.stringify(list.map(function (s) { return s.meta; }), null, 1) + '\n');
var cat = {}, race = {};
list.forEach(function (s) {
  cat[s.meta.category] = (cat[s.meta.category] || 0) + 1;
  if (s.meta.category === 'prop') race[s.meta.race] = (race[s.meta.race] || 0) + 1;
});
console.log('symbols: ' + list.length + ' ' + JSON.stringify(cat) + ', props by race ' + JSON.stringify(race) +
  ', sprite ' + Math.round(svg.length / 1024) + ' KB');
if (bad) { console.error(bad + ' problem(s)'); process.exit(1); }
