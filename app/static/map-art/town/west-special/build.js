#!/usr/bin/env node
/*
 * 生成 sprite.svg 与 meta.json：node build.js
 * 纯程序化路径，不读外部图片。生成后做基本自检：id 唯一、facility 合法、footprint 在规范范围内。
 */
'use strict';
var fs = require('fs'), path = require('path');
var WS = require('./west-special.js');
var defs = WS.list(), seen = {}, errs = [];
var syms = [], metas = [];
defs.forEach(function (d) {
  var id = WS.idOf(d);
  if (seen[id]) errs.push('重复 id ' + id);
  seen[id] = 1;
  if (WS.FACILITY.indexOf(d.facility) < 0) errs.push(id + ' facility 非法: ' + d.facility);
  if (d.up > 144) errs.push(id + ' 上伸超过 144 px');
  var cat = d.category || 'special';
  if (cat === 'special' && (d.fp[0] < 2 || d.fp[1] < 2 || d.fp[0] > 4 || d.fp[1] > 3)) errs.push(id + ' 占地不在 2×2..4×3');
  syms.push(WS.symbol(d));
  metas.push(WS.meta(d));
});
// symbol 内部 id（clipPath 等）必须带 symbol 前缀
syms.forEach(function (s, i) {
  var own = WS.idOf(defs[i]), re = /\sid="([^"]+)"/g, m;
  while ((m = re.exec(s))) if (m[1] !== own && m[1].indexOf(own + '-') !== 0) errs.push(own + ' 内部 id 未带前缀: ' + m[1]);
});
var out = '<svg xmlns="http://www.w3.org/2000/svg" style="display:none">\n' + syms.join('\n') + '\n</svg>\n';
fs.writeFileSync(path.join(__dirname, 'sprite.svg'), out);
fs.writeFileSync(path.join(__dirname, 'meta.json'), JSON.stringify(metas, null, 2) + '\n');
console.log('symbols:', syms.length, ' bytes:', out.length);
if (errs.length) { console.error(errs.join('\n')); process.exit(1); }
