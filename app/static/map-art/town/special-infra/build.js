#!/usr/bin/env node
/*
 * 生成 sprite.svg 与 meta.json（纯程序化，不读外部图片）。
 * 用法：node build.js
 */
'use strict';
var fs = require('fs'), path = require('path');
var A = require('./special-infra.js');
var dir = __dirname;

var sprite = A.sprite(), meta = A.metaAll();

// 自检：symbol id 唯一、内部 id 都带所在 symbol 前缀、meta 每项有 symbol
var ids = {}, errs = [];
meta.forEach(function (m) {
  if (ids[m.id]) errs.push('重复 symbol id: ' + m.id);
  ids[m.id] = 1;
  if (sprite.indexOf('<symbol id="' + m.id + '"') < 0) errs.push('meta 没有对应 symbol: ' + m.id);
});
var re = /<symbol id="([^"]+)"[\s\S]*?<\/symbol>/g, mm, inner = {};
while ((mm = re.exec(sprite))) {
  var sid = mm[1], body = mm[0].slice(mm[0].indexOf('>') + 1), r2 = /\sid="([^"]+)"/g, k;
  while ((k = r2.exec(body))) {
    if (k[1].indexOf(sid + '-') !== 0) errs.push(sid + ' 内部 id 未带前缀: ' + k[1]);
    if (inner[k[1]]) errs.push('内部 id 重复: ' + k[1]);
    inner[k[1]] = 1;
  }
}
if (errs.length) { console.error(errs.join('\n')); process.exit(1); }

fs.writeFileSync(path.join(dir, 'sprite.svg'), sprite);
fs.writeFileSync(path.join(dir, 'meta.json'), JSON.stringify(meta, null, 2) + '\n');
console.log('symbols=' + meta.length + ' sprite=' + sprite.length + 'B');
meta.forEach(function (m) { console.log('  ' + m.id + '  ' + m.footprint.join('x') + '  ' + m.facility); });
