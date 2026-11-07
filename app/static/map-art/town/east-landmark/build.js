#!/usr/bin/env node
/*
 * 生成 sprite.svg 与 meta.json：node build.js
 * 纯程序化，不读外部图片。自检：symbol id 唯一且合规、内部 id 带 symbol 前缀、facility 在 28 种之内或 null、
 * category = landmark、culture 非空、占地 ≤ 6×6、上伸 ≤ 240 px、viewBox / 锚点与占地一致、无 NaN/undefined、
 * 生成的 sprite.svg 能被 XML 解析（简单的标签配对检查）。
 */
'use strict';
var fs = require('fs'), path = require('path');
var A = require('./east-landmark.js');

var FACILITY = ['town_hall', 'lord_hall', 'market_hall', 'granary', 'cistern', 'well', 'mill', 'forge', 'smelter', 'kiln',
  'tannery', 'barracks', 'watchtower', 'city_wall', 'gate', 'temple', 'academy', 'infirmary', 'inn', 'caravanserai',
  'stable', 'dock', 'warehouse', 'mine_head', 'boiler_house', 'ward_tower', 'cemetery', 'bridge'];

var meta = A.list(), errs = [], seen = {};
meta.forEach(function (m) {
  if (seen[m.id]) errs.push('重复 id ' + m.id); seen[m.id] = 1;
  if (!/^[a-z0-9-]+$/.test(m.id)) errs.push('id 不合规 ' + m.id);
  if (m.style !== 'east' || m.race !== 'common') errs.push('style/race 不对 ' + m.id);
  if (m.facility !== null && FACILITY.indexOf(m.facility) < 0) errs.push('facility 不在 28 种内 ' + m.id + ' ' + m.facility);
  if (m.category !== 'landmark') errs.push('category 不是 landmark ' + m.id);
  if (!m.culture) errs.push('缺 culture ' + m.id);
  if (m.footprint[0] > 6 || m.footprint[1] > 6) errs.push('占地超过 6×6 ' + m.id);
  var W = m.footprint[0] * 48, D = m.footprint[1] * 48;
  if (m.viewBox[2] !== W || m.viewBox[3] !== D + m.height_px) errs.push('viewBox 与占地不符 ' + m.id);
  if (m.anchor[0] !== W / 2 || m.anchor[1] !== D + m.height_px) errs.push('锚点不在前沿中点 ' + m.id);
  if (m.height_px > 240) errs.push('上伸超过 240 px ' + m.id);
  var body = A.symbol(m.id).body, re = /\bid="([^"]+)"/g, g;
  while ((g = re.exec(body))) {
    if (g[1].indexOf(m.id + '-') !== 0) errs.push('内部 id 未带前缀 ' + m.id + ' ' + g[1]);
    if (seen[g[1]]) errs.push('内部 id 重复 ' + g[1]); seen[g[1]] = 1;
  }
  if (/NaN|undefined|Infinity/.test(body)) errs.push('图形里有 NaN/undefined ' + m.id);
});

// 简单 XML 良构检查：标签配对 + 属性引号
function xmlCheck(txt) {
  var stack = [], re = /<(\/?)([a-zA-Z][\w:-]*)((?:\s+[\w:-]+="[^"<]*")*)\s*(\/?)>/g, m, last = 0;
  while ((m = re.exec(txt))) {
    var between = txt.slice(last, m.index);
    if (/[<>]/.test(between)) return '标签之间有游离的 < 或 >：' + between.slice(0, 60);
    last = re.lastIndex;
    if (m[4]) continue;
    if (m[1]) { var top = stack.pop(); if (top !== m[2]) return '标签不配对 </' + m[2] + '> 期望 </' + top + '>'; }
    else stack.push(m[2]);
  }
  if (/[<>]/.test(txt.slice(last))) return '结尾有游离的 < 或 >';
  return stack.length ? '未闭合：' + stack.join(',') : null;
}
var sprite = A.spriteSvg(), xe = xmlCheck(sprite);
if (xe) errs.push('sprite.svg XML 检查失败：' + xe);

fs.writeFileSync(path.join(__dirname, 'sprite.svg'), sprite);
fs.writeFileSync(path.join(__dirname, 'meta.json'), JSON.stringify(meta, null, 2) + '\n');
console.log('symbols:', meta.length, ' sprite:', Math.round(sprite.length / 1024) + ' KB');
meta.forEach(function (m) { console.log('  ' + m.id + '  ' + m.name_zh + '  ' + m.culture + '  ' + m.footprint.join('×') + '  up ' + m.height_px + '  ' + m.facility); });
var symCount = (sprite.match(/<symbol /g) || []).length;
if (symCount !== meta.length) errs.push('symbol 数 ' + symCount + ' ≠ meta 数 ' + meta.length);
if (errs.length) { console.error('自检失败:\n  ' + errs.join('\n  ')); process.exit(1); }
console.log('自检通过');
