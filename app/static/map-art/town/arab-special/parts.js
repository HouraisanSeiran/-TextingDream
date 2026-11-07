/*
 * 阿拉伯风格部件画笔：尖拱、瓷砖带、八角星、木格窗、雉堞、平顶块、内院、门楼。
 * 浏览器挂 window.TownArtAS_parts；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var K = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtAS_core;
  var C = K.C, f = K.f;

  /** 尖拱轮廓 d：左下角 x、底 yb、宽 w、总高 h（apex 在 yb-h） */
  function archD(x, yb, w, h) {
    var sp = yb - h + w * 0.62, ap = yb - h;
    if (sp > yb) sp = yb;
    return 'M' + f(x) + ' ' + f(yb) + 'L' + f(x) + ' ' + f(sp) +
      'Q' + f(x) + ' ' + f(ap + w * 0.22) + ' ' + f(x + w / 2) + ' ' + f(ap) +
      'Q' + f(x + w) + ' ' + f(ap + w * 0.22) + ' ' + f(x + w) + ' ' + f(sp) +
      'L' + f(x + w) + ' ' + f(yb) + 'Z';
  }
  function arch(x, yb, w, h, fill, sw) { return K.path(archD(x, yb, w, h), fill || C.hole, sw == null ? 1 : sw); }
  /** 带框尖拱：外框 + 内洞 */
  function archFramed(x, yb, w, h, frame, hole) {
    var t = Math.max(1.5, w * 0.16);
    return arch(x - t, yb, w + 2 * t, h + t, frame || C.lime2, 1) + arch(x, yb, w, h, hole || C.hole, 0.9);
  }
  /** 八角星（两个方块叠加） */
  function star8(cx, cy, r, fill, sw) {
    var p = [];
    for (var i = 0; i < 16; i++) {
      var a = Math.PI * i / 8 - Math.PI / 2, rr = i % 2 ? r * 0.58 : r;
      p.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr]);
    }
    return K.poly(p, fill || C.gold, sw == null ? 0.7 : sw);
  }
  /** 几何纹瓷砖带：钴蓝底 + 白菱 + 绿松石点 */
  function tileBand(x0, x1, y, hh, alt) {
    var s = K.rect(x0, y, x1 - x0, hh, alt ? C.turq : C.cobalt, 0.9);
    var step = Math.max(5, hh * 1.1), n = Math.max(1, Math.floor((x1 - x0) / step));
    step = (x1 - x0) / n;
    var cy = y + hh / 2, r = hh * 0.36, d = '';
    for (var i = 0; i < n; i++) {
      var cx = x0 + step * (i + 0.5);
      d += 'M' + f(cx) + ' ' + f(cy - r) + 'L' + f(cx + r) + ' ' + f(cy) + 'L' + f(cx) + ' ' + f(cy + r) + 'L' + f(cx - r) + ' ' + f(cy) + 'Z';
    }
    s += K.flatD(d, alt ? C.lime : C.turq2);
    if (hh >= 5) {
      var dd = '';
      for (var j = 0; j <= n; j++) {
        var x = x0 + step * j; if (x <= x0 + 0.5 || x >= x1 - 0.5) continue;
        dd += 'M' + f(x - 0.8) + ' ' + f(cy) + 'L' + f(x) + ' ' + f(cy - 0.8) + 'L' + f(x + 0.8) + ' ' + f(cy) + 'L' + f(x) + ' ' + f(cy + 0.8) + 'Z';
      }
      s += K.flatD(dd, C.gold);
    }
    return s;
  }
  /** 木格窗 mashrabiya：外挑木箱 + 斜格 */
  function mashrabiya(x, y, w, h) {
    var s = K.rect(x - 1.5, y + h, w + 3, 2.2, C.wood, 0.9) + K.rect(x, y, w, h, C.adobe3, 1.1);
    var d = '', st = 2.6;
    for (var k = -h; k < w; k += st) {
      var a0 = Math.max(0, k), a1 = Math.min(w, k + h);
      if (a1 > a0) d += K.seg(x + a0, y + (a0 - k), x + a1, y + (a1 - k));
      var b0 = Math.max(0, k), b1 = Math.min(w, k + h);
      if (b1 > b0) d += K.seg(x + b0, y + h - (b0 - k), x + b1, y + h - (b1 - k));
    }
    s += K.ln(d, 0.55, 0.85, C.wood);
    s += K.rect(x - 1, y - 2, w + 2, 2.2, C.wood, 0.8);
    return s;
  }
  /** 阶梯雉堞（沿 x0..x1，底在 y，齿高 hh） */
  function merlons(x0, x1, y, hh, fill, gap) {
    var mw = hh * 1.1, g = gap == null ? hh * 0.7 : gap, n = Math.max(1, Math.floor((x1 - x0 + g) / (mw + g)));
    var tot = n * mw + (n - 1) * g, st = x0 + (x1 - x0 - tot) / 2, s = '';
    for (var i = 0; i < n; i++) {
      var a = st + i * (mw + g), b = a + mw, q = mw * 0.25;
      s += K.poly([[a, y], [a, y - hh * 0.55], [a + q, y - hh * 0.55], [a + q, y - hh], [b - q, y - hh], [b - q, y - hh * 0.55],
        [b, y - hh * 0.55], [b, y]], fill || C.lime, 0.8);
    }
    return s;
  }

  var P = { archD: archD, arch: arch, archFramed: archFramed, star8: star8, tileBand: tileBand, mashrabiya: mashrabiya, merlons: merlons };
  if (typeof module !== 'undefined' && module.exports) module.exports = P;
  else root.TownArtAS_parts = P;
})(this);
