#!/usr/bin/env node
/*
 * 生成 sprite.svg 与 meta.json：node build.js
 * 纯程序化路径，不读外部图片。生成后自检：id 唯一、内部 id 带前缀、facility 合法或 null、culture 必填、
 * 占地 ≤ 6×6、上伸 ≤ 240 px、画面不越出 viewBox 底边以下 6 px（粗查 path 坐标）。
 */
'use strict';
var fs = require('fs'), path = require('path');
var WL = require('./west-landmark.js');
var defs = WL.list(), seen = {}, errs = [], warns = [];
var syms = [], metas = [];
defs.forEach(function (d) {
  var id = WL.idOf(d), s = WL.dims(d);
  if (!/^[a-z0-9-]+$/.test(id)) errs.push('id 不合规: ' + id);
  if (seen[id]) errs.push('重复 id ' + id);
  seen[id] = 1;
  if (d.facility != null && WL.FACILITY.indexOf(d.facility) < 0) errs.push(id + ' facility 非法: ' + d.facility);
  if (d.facility == null && !d.note) errs.push(id + ' facility 为 null 但缺 note');
  if (!d.culture) errs.push(id + ' 缺 culture');
  if (d.up > WL.MAX_UP) errs.push(id + ' 上伸超过 240 px: ' + d.up);
  if (d.fp[0] < 1 || d.fp[1] < 1 || d.fp[0] > WL.MAX_FP || d.fp[1] > WL.MAX_FP) errs.push(id + ' 占地超出 6×6: ' + d.fp.join('×'));
  var sym = WL.symbol(d);
  // 粗查：所有绝对坐标 y 不超过 H + 6（投影下伸上限）
  var re = /\b[MLQ]\s*(-?[\d.]+)\s+(-?[\d.]+)/g, m, maxY = -1e9, maxX = -1e9, minX = 1e9;
  while ((m = re.exec(sym))) { var x = +m[1], y = +m[2]; if (y > maxY) maxY = y; if (x > maxX) maxX = x; if (x < minX) minX = x; }
  if (maxY > s.H + 6.01) errs.push(id + ' 画到前沿以下 ' + (maxY - s.H).toFixed(1) + ' px');
  if (maxX > s.W + 0.5 || minX < -0.5) warns.push(id + ' 横向越出 viewBox：x ' + minX.toFixed(1) + '..' + maxX.toFixed(1) + ' / W ' + s.W);
  var ri = /\sid="([^"]+)"/g, mm;
  while ((mm = ri.exec(sym))) if (mm[1] !== id && mm[1].indexOf(id + '-') !== 0) errs.push(id + ' 内部 id 未带前缀: ' + mm[1]);
  syms.push(sym);
  metas.push(WL.meta(d));
});
var out = '<svg xmlns="http://www.w3.org/2000/svg" style="display:none">\n' + syms.join('\n') + '\n</svg>\n';
fs.writeFileSync(path.join(__dirname, 'sprite.svg'), out);
fs.writeFileSync(path.join(__dirname, 'meta.json'), JSON.stringify(metas, null, 2) + '\n');
console.log('symbols:', syms.length, ' bytes:', out.length);
metas.forEach(function (m) { console.log('  ' + m.id + '  ' + m.footprint.join('x') + ' up ' + m.height_px + '  ' + m.culture + '  ' + m.facility); });
if (warns.length) console.warn('警告:\n  ' + warns.join('\n  '));
if (errs.length) { console.error('错误:\n  ' + errs.join('\n  ')); process.exit(1); }
