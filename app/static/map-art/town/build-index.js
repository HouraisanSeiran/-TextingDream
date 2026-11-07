// 用法：node app/static/map-art/town/build-index.js
// 自动合并各子目录的 sprite.svg 与 meta.json，供图册与在线城镇布局共用。
'use strict';
var fs = require('fs'), path = require('path');
// 自动扫描：凡是带 meta.json 和 sprite.svg 的子目录都并入（新增素材目录无需改这里）
var DIRS = fs.readdirSync(__dirname).filter(function (d) {
  return fs.existsSync(path.join(__dirname, d, 'meta.json')) && fs.existsSync(path.join(__dirname, d, 'sprite.svg'));
}).sort();
var root = __dirname, meta = [], parts = [], seen = {};
DIRS.forEach(function (d) {
  var m = JSON.parse(fs.readFileSync(path.join(root, d, 'meta.json'), 'utf8'));
  m.forEach(function (it) {
    if (seen[it.id]) throw new Error('重复 id ' + it.id + '（' + seen[it.id] + ' / ' + d + '）');
    seen[it.id] = d; it.dir = d; meta.push(it);
  });
  var s = fs.readFileSync(path.join(root, d, 'sprite.svg'), 'utf8');
  s = s.replace(/<\?xml[^>]*\?>/, '').replace(/<!--[\s\S]*?-->/g, '');
  var a = s.indexOf('>', s.indexOf('<svg')) + 1, b = s.lastIndexOf('</svg>');
  parts.push(s.slice(a, b));
});
var out = '/* 由 build-index.js 生成，勿手改 */\nwindow.TOWN_CATALOG = ' +
  JSON.stringify({ dirs: DIRS, meta: meta, sprite: parts.join('\n') }) + ';\n';
fs.writeFileSync(path.join(root, 'town-catalog.js'), out, 'utf8');
console.log('symbols=' + meta.length + ' bytes=' + out.length);
