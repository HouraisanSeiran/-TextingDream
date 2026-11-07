// 用法：node app/static/map-art/fog-brushes/export-svg.js
// 从 fog-brushes.js 导出每枚笔刷的独立 SVG（中灰蓝 + 内缘浅灰蓝两个色调），并检查是否越出 viewBox。
'use strict';
var fs = require('fs');
var path = require('path');
var FB = require('./fog-brushes.js');

var dir = __dirname;
var written = [];
FB.BRUSHES.forEach(function (b) {
  ['mid', 'light'].forEach(function (tone) {
    var name = 'brush-' + b.id + '-' + b.key + '-' + tone + '.svg';
    fs.writeFileSync(path.join(dir, name), FB.standalone(b, tone), 'utf8');
    written.push(name);
  });
  // 粗查：云头顶（圆弧顶点及左右鼓出）不越出 viewBox
  b.clumps.forEach(function (cl) {
    for (var i = 0; i < cl.pts.length - 1; i++) {
      var p = cl.pts[i], q = cl.pts[i + 1];
      var c = Math.hypot(q[0] - p[0], q[1] - p[1]), s = cl.b[i] * c;
      var nx = (q[1] - p[1]) / c, ny = -(q[0] - p[0]) / c;
      var r = (c * c / 4 + s * s) / (2 * s);
      var cx = (p[0] + q[0]) / 2 + nx * (s - r), cy = (p[1] + q[1]) / 2 + ny * (s - r);
      for (var k = 0; k <= 64; k++) {
        var a = Math.atan2(p[1] - cy, p[0] - cx), a1 = Math.atan2(q[1] - cy, q[0] - cx);
        if (a1 < a) a1 += Math.PI * 2;
        var t = a + (a1 - a) * k / 64, x = cx + Math.cos(t) * r, y = cy + Math.sin(t) * r;
        if (x < 0 || x > b.w || y < 0 || y > b.h) {
          console.warn('越界', b.id, i, x.toFixed(1), y.toFixed(1));
          break;
        }
      }
    }
  });
});
console.log(written.join('\n'));
