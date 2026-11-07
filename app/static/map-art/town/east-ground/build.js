#!/usr/bin/env node
/*
 * 生成 sprite.svg 与 meta.json：node build.js
 * 纯程序化手写路径，不读任何外部图片。
 * 自检：symbol id 唯一、内部 id 带 symbol 前缀、meta 与 symbol 一一对应、摆件上伸 ≤ 48、
 *       id 不与 app/static/map-art/town/ 下其他目录的 sprite.svg 重复。
 */
'use strict';
var fs = require('fs'), path = require('path');
var EG = require('./east-ground.js');

var res = EG.buildAll(), dir = __dirname;
var sprite = res.spriteSvg();
var meta = res.items.map(function (it) { return it.meta; });

var symIds = [], m, re = /<symbol id="([^"]+)"/g, bad = [], seen = {};
while ((m = re.exec(sprite))) symIds.push(m[1]);
symIds.forEach(function (s) { if (seen[s]) bad.push('symbol 重复: ' + s); seen[s] = 1; });
meta.forEach(function (x) { if (!seen[x.id]) bad.push('meta 无对应 symbol: ' + x.id); });
if (symIds.length !== meta.length) bad.push('symbol 数 ' + symIds.length + ' ≠ meta 数 ' + meta.length);
res.items.forEach(function (it) {
  var r2 = /\bid="([^"]+)"/g, k;
  while ((k = r2.exec(it.svg))) if (k[1] !== it.id && k[1].indexOf(it.id + '-') !== 0) bad.push(it.id + ' 内部 id 未带前缀: ' + k[1]);
  if (it.over) bad.push(it.id + ' 上伸超过 48 px');
});
var allIds = {}, r3 = /\bid="([^"]+)"/g, q;
while ((q = r3.exec(sprite))) { if (allIds[q[1]]) bad.push('全目录 id 重复: ' + q[1]); allIds[q[1]] = 1; }

// 与 town/ 下其他目录对比
var townDir = path.join(dir, '..'), clash = 0;
fs.readdirSync(townDir).forEach(function (d) {
  var p = path.join(townDir, d, 'sprite.svg');
  if (d === path.basename(dir) || !fs.existsSync(p)) return;
  var txt = fs.readFileSync(p, 'utf8'), r4 = /\bid="([^"]+)"/g, z;
  while ((z = r4.exec(txt))) if (allIds[z[1]]) { bad.push('与 ' + d + ' 重复 id: ' + z[1]); clash++; }
});

if (bad.length) { console.error(bad.join('\n')); process.exit(1); }
fs.writeFileSync(path.join(dir, 'sprite.svg'), sprite);
fs.writeFileSync(path.join(dir, 'meta.json'), JSON.stringify(meta, null, 2) + '\n');
var cnt = {};
meta.forEach(function (x) { cnt[x.category] = (cnt[x.category] || 0) + 1; });
console.log('写出 ' + meta.length + ' 个 symbol：' + Object.keys(cnt).map(function (k) { return k + ' ' + cnt[k]; }).join('，') +
  '；sprite ' + Math.round(sprite.length / 1024) + ' KB；与其他目录 id 冲突 ' + clash);
