/*
 * 生成 sprite.svg 与 meta.json：node build.js（在本目录或任意目录运行均可）。
 * 纯程序化路径，不读任何外部图片。
 */
'use strict';
var fs = require('fs'), path = require('path');
var WC = require('./west-castle.js');

var list = WC.entries();
var ids = {};
list.forEach(function (e) {
  if (ids[e.id]) throw new Error('重复的 symbol id: ' + e.id);
  ids[e.id] = 1;
});
var svg = WC.sprite(list), meta = WC.meta(list);
fs.writeFileSync(path.join(__dirname, 'sprite.svg'), svg);
fs.writeFileSync(path.join(__dirname, 'meta.json'), JSON.stringify(meta, null, 1) + '\n');
console.log('symbols: ' + list.length + '  sprite.svg ' + (svg.length / 1024).toFixed(1) + ' KB  meta.json ' + meta.length + ' 项');
