#!/usr/bin/env node
/* 生成 sprite.svg 与 meta.json：node build.js */
'use strict';
var fs = require('fs'), path = require('path');
var WB = require('./west-base.js');

var list = WB.symbols();
var ids = {}, bad = 0;
list.forEach(function (s) {
  if (ids[s.id]) { console.error('duplicate symbol id ' + s.id); bad++; }
  ids[s.id] = 1;
  if (s.over) { console.error('too tall (' + s.up + ' px > ' + WB.MAX_UP + '): ' + s.id); bad++; }
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
var svg = '<?xml version="1.0" encoding="UTF-8"?>\n' + WB.spriteSVG(list).replace(' width="0" height="0" style="position:absolute;overflow:hidden"', '') + '\n';
fs.writeFileSync(path.join(__dirname, 'sprite.svg'), svg);
fs.writeFileSync(path.join(__dirname, 'meta.json'), JSON.stringify(list.map(function (s) { return s.meta; }), null, 1) + '\n');
var cat = {};
list.forEach(function (s) { cat[s.meta.category] = (cat[s.meta.category] || 0) + 1; });
console.log('symbols: ' + list.length + ' ' + JSON.stringify(cat) + ', house types: ' + WB.HOUSE_TYPES.length +
  ', sprite ' + Math.round(svg.length / 1024) + ' KB');
if (bad) { console.error(bad + ' problem(s)'); process.exit(1); }
