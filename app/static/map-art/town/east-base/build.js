#!/usr/bin/env node
/*
 * 生成 sprite.svg 与 meta.json：node build.js
 * 纯程序化手写路径，不读任何外部图片。
 */
'use strict';
var fs = require('fs'), path = require('path');
var EB = require('./east-base.js');

var res = EB.buildAll(), dir = __dirname;
var sprite = res.spriteSvg();
var meta = res.items.map(function (it) { return it.meta; });

// 自检：id 唯一、内部 id 都带 symbol 前缀、meta 与 symbol 一一对应、上伸不超 144
var symIds = [], m, re = /<symbol id="([^"]+)"/g;
while ((m = re.exec(sprite))) symIds.push(m[1]);
var bad = [];
var seen = {};
symIds.forEach(function (s) { if (seen[s]) bad.push('symbol 重复: ' + s); seen[s] = 1; });
meta.forEach(function (x) { if (!seen[x.id]) bad.push('meta 无对应 symbol: ' + x.id); });
if (symIds.length !== meta.length) bad.push('symbol 数 ' + symIds.length + ' ≠ meta 数 ' + meta.length);
res.items.forEach(function (it) {
  var r2 = /\bid="([^"]+)"/g, k;
  while ((k = r2.exec(it.svg))) if (k[1] !== it.id && k[1].indexOf(it.id + '-') !== 0) bad.push(it.id + ' 内部 id 未带前缀: ' + k[1]);
  if (it.over) bad.push(it.id + ' 上伸超过 144 px');
});
var allIds = {}, r3 = /\bid="([^"]+)"/g, q;
while ((q = r3.exec(sprite))) { if (allIds[q[1]]) bad.push('全目录 id 重复: ' + q[1]); allIds[q[1]] = 1; }

fs.writeFileSync(path.join(dir, 'sprite.svg'), '<?xml version="1.0" encoding="UTF-8"?>\n<!-- 织梦 · 东方城镇基础素材（east-base），由 build.js 生成，勿手改 -->\n' + sprite);
fs.writeFileSync(path.join(dir, 'meta.json'), JSON.stringify(meta, null, 1) + '\n');

var cats = {};
meta.forEach(function (x) { cats[x.category] = (cats[x.category] || 0) + 1; });
console.log('symbols:', symIds.length, JSON.stringify(cats), 'sprite bytes:', Buffer.byteLength(sprite));
if (bad.length) { console.error(bad.join('\n')); process.exit(1); }
console.log('OK');
