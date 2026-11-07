/*
 * 织梦 · race-fort-2 生成脚本：node build.js → sprite.svg + meta.json，并做第 6 节自检
 * 自检：symbol id 唯一、内部 id 带 symbol 前缀且全文件唯一、meta 与 symbol 一一对应、facility 在 28 种之内、
 * 与 app/static/map-art/town/ 下其他目录（含 race-fort）的 symbol id 不撞名、上伸不超上限、XML 标签配对。有错以退出码 1 结束。
 */
'use strict';
var fs = require('fs'), pathM = require('path');
var RF = require('./race-fort-2.js');
var dir = __dirname, errs = [];
var list = RF.symbols();
var svg = RF.spriteSVG(list);
var metas = list.map(function (s) { return s.meta; });
fs.writeFileSync(pathM.join(dir, 'sprite.svg'), svg);
fs.writeFileSync(pathM.join(dir, 'meta.json'), JSON.stringify(metas, null, 1));

var seen = {};
list.forEach(function (s) {
  if (seen[s.id]) errs.push('重复 id ' + s.id); seen[s.id] = 1;
  var m = s.meta;
  if (m.facility && RF.FACILITIES.indexOf(m.facility) < 0) errs.push('facility 不在 28 种内 ' + s.id + ' ' + m.facility);
  if (s.over) errs.push('上伸超限（已截断）' + s.id);
  if (m.category === 'landmark' && !m.culture) errs.push('地标缺 culture ' + s.id);
  var re = /id="([^"]+)"/g, r;
  while ((r = re.exec(s.body))) if (r[1].indexOf(s.id + '-') !== 0) errs.push('内部 id 未带前缀 ' + s.id + ' ' + r[1]);
});
// meta 与 symbol 一一对应（从产物文件回读）
var symIds = [], re1 = /<symbol id="([^"]+)"/g, r1;
while ((r1 = re1.exec(svg))) symIds.push(r1[1]);
var metaIds = JSON.parse(fs.readFileSync(pathM.join(dir, 'meta.json'), 'utf8')).map(function (m) { return m.id; });
if (symIds.join(',') !== metaIds.join(',')) errs.push('meta 与 symbol 不一一对应');
// 全文件 id 唯一
var all = {}, re2 = /id="([^"]+)"/g, r2;
while ((r2 = re2.exec(svg))) { if (all[r2[1]]) errs.push('文件内 id 重复 ' + r2[1]); all[r2[1]] = 1; }
// 与其他目录撞名
var town = pathM.join(dir, '..'), checked = 0;
fs.readdirSync(town).forEach(function (d) {
  var p = pathM.join(town, d, 'sprite.svg');
  if (d === 'race-fort-2' || !fs.existsSync(p)) return;
  checked++;
  var t = fs.readFileSync(p, 'utf8'), re3 = /<symbol id="([^"]+)"/g, r3;
  while ((r3 = re3.exec(t))) if (seen[r3[1]]) errs.push('与 ' + d + ' 撞名 ' + r3[1]);
});
// 粗查 XML：标签配对
var stack = [], re4 = /<(\/?)([a-zA-Z]+)[^>]*?(\/?)>/g, r4;
while ((r4 = re4.exec(svg))) {
  if (r4[3]) continue;
  if (!r4[1]) stack.push(r4[2]);
  else if (stack.pop() !== r4[2]) { errs.push('XML 标签不配对 @' + r4.index); break; }
}
if (stack.length) errs.push('XML 有未闭合标签 ' + stack.join(','));

metas.forEach(function (m) { console.log(m.id, m.footprint.join('x'), 'up=' + m.height_px, m.category, m.facility); });
console.log('symbols=' + list.length + ' 比对目录=' + checked + ' sprite=' + Math.round(svg.length / 1024) + 'KB');
if (errs.length) { console.error(errs.join('\n')); process.exit(1); }
console.log('自检通过');
