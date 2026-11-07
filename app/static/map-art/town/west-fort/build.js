/*
 * 织梦 · 西式防御工事（west-fort）生成脚本：node build.js → sprite.svg + meta.json
 * 纯程序化手写路径，不读外部图片。
 */
'use strict';
var fs = require('fs'), path = require('path');
var WF = require('./west-fort.js');
var list = WF.all();
var seen = {};
list.forEach(function (x) {
  if (seen[x.id]) throw new Error('重复 id: ' + x.id);
  seen[x.id] = 1;
});
var svg = '<?xml version="1.0" encoding="UTF-8"?>\n' + WF.sprite(list).replace('<svg ', '<svg id="west-fort-sprite" ') + '\n';
fs.writeFileSync(path.join(__dirname, 'sprite.svg'), svg);
fs.writeFileSync(path.join(__dirname, 'meta.json'), JSON.stringify(list.map(function (x) { return x.meta; }), null, 1) + '\n');
console.log('west-fort: ' + list.length + ' symbols, sprite ' + Math.round(svg.length / 1024) + ' KB');
