/*
 * 织梦 · race-fort 生成脚本：node build.js → sprite.svg + meta.json，并做第 6 节自检
 * 自检：symbol id 唯一、内部 id 带 symbol 前缀、meta 与 symbol 一一对应、facility 在 28 种之内、
 * 与 app/static/map-art/town/ 下其他目录的 symbol id 不撞名、上伸不超上限。有错就以退出码 1 结束。
 */
'use strict';
var fs = require('fs'), pathM = require('path');
var RF = require('./race-fort.js');
var dir = __dirname, errs = [];
var list = RF.symbols();
var svg = RF.spriteSVG(list);
fs.writeFileSync(pathM.join(dir, 'sprite.svg'), svg);
fs.writeFileSync(pathM.join(dir, 'meta.json'), JSON.stringify(list.map(function (s) { return s.meta; }), null, 1));

var seen = {};
list.forEach(function (s) {
  if (seen[s.id]) errs.push('重复 id ' + s.id); seen[s.id] = 1;
  var m = s.meta;
  if (m.facility && RF.FACILITIES.indexOf(m.facility) < 0) errs.push('facility 不在 28 种内 ' + s.id + ' ' + m.facility);
  var lim = m.category === 'landmark' || /fortress/.test(m.id) ? 240 : 144;
  if (m.height_px > lim) errs.push('上伸超限 ' + s.id + ' ' + m.height_px);
  var re = /id="([^"]+)"/g, r;
  while ((r = re.exec(s.body))) if (r[1].indexOf(s.id + '-') !== 0) errs.push('内部 id 未带前缀 ' + s.id + ' ' + r[1]);
});
// 全文件内部 id 唯一
var all = {}, re2 = /id="([^"]+)"/g, r2;
while ((r2 = re2.exec(svg))) { if (all[r2[1]]) errs.push('文件内 id 重复 ' + r2[1]); all[r2[1]] = 1; }
// 与其他目录撞名
var town = pathM.join(dir, '..');
fs.readdirSync(town).forEach(function (d) {
  var p = pathM.join(town, d, 'sprite.svg');
  if (d === 'race-fort' || !fs.existsSync(p)) return;
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
if (stack.length) errs.push('XML 未闭合 ' + stack.join(','));
// 预览用：从三族目录的 sprite.svg 只读摘出已有城门 symbol，写成 preview-refs.js（file:// 下可直接 <script src>）
var REF = { 'west-elf': ['west-elf-wall-gate-h', 'west-elf-wall-gate-v'], 'west-dwarf': ['west-dwarf-wall-gate-h', 'west-dwarf-wall-gate-v'], 'west-orc': ['west-orc-gate-h', 'west-orc-gate-v'] };
var refs = {};
Object.keys(REF).forEach(function (d) {
  var p = pathM.join(town, d, 'sprite.svg');
  if (!fs.existsSync(p)) { errs.push('缺参考 ' + p); return; }
  var t = fs.readFileSync(p, 'utf8');
  REF[d].forEach(function (id) {
    var m = new RegExp('<symbol id="' + id + '"[^>]*viewBox="([^"]+)"[\\s\\S]*?</symbol>').exec(t);
    if (!m) { errs.push('参考 symbol 缺失 ' + id); return; }
    refs[id] = { svg: m[0], viewBox: m[1].split(/\s+/).map(Number) };
  });
});
fs.writeFileSync(pathM.join(dir, 'preview-refs.js'), '/* 生成产物：build.js 从 west-elf / west-dwarf / west-orc 的 sprite.svg 只读摘出的城门 symbol，仅供 preview.html 拼接验证 */\nwindow.RF_REFS = ' + JSON.stringify(refs) + ';\n');
console.log('symbols=' + list.length + ' bytes=' + svg.length);
list.forEach(function (s) { var m = s.meta; console.log(m.id, m.footprint.join('x'), 'up=' + m.height_px, m.facility); });
if (errs.length) { console.error(errs.join('\n')); process.exit(1); }
console.log('自检通过');
