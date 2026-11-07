#!/usr/bin/env node
/*
 * 生成 sprite.svg 与 meta.json：node build.js
 * 纯程序化，不读外部图片。生成后做基本自检：symbol id 唯一、内部 id 带 symbol 前缀、
 * facility 在 28 种 FacilityKind 之内或为 null、viewBox / 锚点与占地一致。
 */
'use strict';
var fs = require('fs'), path = require('path');
var A = require('./east-special.js');

var FACILITY = ['town_hall', 'lord_hall', 'market_hall', 'granary', 'cistern', 'well', 'mill', 'forge', 'smelter', 'kiln',
  'tannery', 'barracks', 'watchtower', 'city_wall', 'gate', 'temple', 'academy', 'infirmary', 'inn', 'caravanserai',
  'stable', 'dock', 'warehouse', 'mine_head', 'boiler_house', 'ward_tower', 'cemetery', 'bridge'];
var CATS = ['house', 'special', 'road', 'wall', 'castle', 'prop'];

var meta = A.list(), errs = [], seen = {};
meta.forEach(function (m) {
  if (seen[m.id]) errs.push('重复 id ' + m.id); seen[m.id] = 1;
  if (!/^[a-z0-9-]+$/.test(m.id)) errs.push('id 不合规 ' + m.id);
  if (m.facility !== null && FACILITY.indexOf(m.facility) < 0) errs.push('facility 不在 28 种内 ' + m.id + ' ' + m.facility);
  if (CATS.indexOf(m.category) < 0) errs.push('category 不合规 ' + m.id);
  var W = m.footprint[0] * 48, D = m.footprint[1] * 48;
  if (m.viewBox[2] !== W || m.viewBox[3] !== D + m.height_px) errs.push('viewBox 与占地不符 ' + m.id);
  if (m.anchor[0] !== W / 2 || m.anchor[1] !== D + m.height_px) errs.push('锚点不在前沿中点 ' + m.id);
  if (m.height_px > 144) errs.push('上伸超过 144 px ' + m.id);
  var body = A.symbol(m.id).body, re = /\bid="([^"]+)"/g, g;
  while ((g = re.exec(body))) {
    if (g[1].indexOf(m.id + '-') !== 0) errs.push('内部 id 未带前缀 ' + m.id + ' ' + g[1]);
    if (seen[g[1]]) errs.push('内部 id 重复 ' + g[1]); seen[g[1]] = 1;
  }
  if (/NaN|undefined/.test(body)) errs.push('图形里有 NaN/undefined ' + m.id);
});

fs.writeFileSync(path.join(__dirname, 'sprite.svg'), A.spriteSvg());
fs.writeFileSync(path.join(__dirname, 'meta.json'), JSON.stringify(meta, null, 2) + '\n');
console.log('symbols:', meta.length);
var fac = {};
meta.forEach(function (m) { if (m.facility) fac[m.facility] = (fac[m.facility] || 0) + 1; });
console.log('facility 覆盖:', Object.keys(fac).length + '/28', JSON.stringify(fac));
console.log('未覆盖:', FACILITY.filter(function (k) { return !fac[k]; }).join(', '));
if (errs.length) { console.error('自检失败:\n  ' + errs.join('\n  ')); process.exit(1); }
console.log('自检通过');
