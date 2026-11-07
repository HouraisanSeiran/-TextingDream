#!/usr/bin/env node
/* 生成 sprite.svg 与 meta.json：node build.js */
'use strict';
var fs = require('fs'), path = require('path');
var WO = require('./west-orc.js');

var FACILITY = ['town_hall', 'lord_hall', 'market_hall', 'granary', 'cistern', 'well', 'mill', 'forge', 'smelter', 'kiln', 'tannery',
  'barracks', 'watchtower', 'city_wall', 'gate', 'temple', 'academy', 'infirmary', 'inn', 'caravanserai', 'stable', 'dock',
  'warehouse', 'mine_head', 'boiler_house', 'ward_tower', 'cemetery', 'bridge'];
var list = WO.symbols();
var ids = {}, bad = 0;
list.forEach(function (s) {
  if (!/^west-orc-[a-z0-9-]+$/.test(s.id)) { console.error('bad id ' + s.id); bad++; }
  if (ids[s.id]) { console.error('duplicate symbol id ' + s.id); bad++; }
  ids[s.id] = 1;
  if (s.over) { console.error('too tall (' + s.up + ' px > ' + WO.MAX_UP + '): ' + s.id); bad++; }
  var fac = s.meta.facility;
  if (fac !== null && FACILITY.indexOf(fac) < 0) { console.error('unknown facility ' + fac + ': ' + s.id); bad++; }
  if (/NaN|undefined/.test(s.body)) { console.error('NaN/undefined in body: ' + s.id); bad++; }
});
// 内部 id 必须带 symbol id 前缀且全目录唯一
var all = {};
list.forEach(function (s) {
  var re = /\bid="([^"]+)"/g, m;
  while ((m = re.exec(s.body))) {
    if (m[1].indexOf(s.id + '-') !== 0) { console.error('inner id without prefix: ' + m[1]); bad++; }
    if (all[m[1]] || ids[m[1]]) { console.error('inner id clash: ' + m[1]); bad++; }
    all[m[1]] = 1;
  }
});
var svg = '<?xml version="1.0" encoding="UTF-8"?>\n' + WO.spriteSVG(list).replace(' width="0" height="0" style="position:absolute;overflow:hidden"', '') + '\n';
fs.writeFileSync(path.join(__dirname, 'sprite.svg'), svg);
fs.writeFileSync(path.join(__dirname, 'meta.json'), JSON.stringify(list.map(function (s) { return s.meta; }), null, 1) + '\n');
var cat = {};
list.forEach(function (s) { cat[s.meta.category] = (cat[s.meta.category] || 0) + 1; });
console.log('symbols: ' + list.length + ' ' + JSON.stringify(cat) + ', house types: ' + WO.HOUSE_TYPES.length +
  ', sprite ' + Math.round(svg.length / 1024) + ' KB');
if (bad) { console.error(bad + ' problem(s)'); process.exit(1); }
