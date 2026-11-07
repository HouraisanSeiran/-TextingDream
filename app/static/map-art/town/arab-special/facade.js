/*
 * 阿拉伯风格立面画笔：拱廊 arcade、门楼 pishtaq（尖拱大门龛）、木门 door、小窗排 windows、布棚 awning。
 * 浏览器挂 window.TownArtAS_facade；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var N = typeof module !== 'undefined' && module.exports;
  var K = N ? require('./core.js') : root.TownArtAS_core;
  var P = N ? require('./parts.js') : root.TownArtAS_parts;
  var C = K.C, f = K.f;

  /** 一排尖拱（立面上）：x0..x1，底 yb，拱高 hh，n 个；hole 洞色；pier 是否画柱头线 */
  function arcade(x0, x1, yb, hh, n, hole, frame) {
    var st = (x1 - x0) / n, s = '', w = st * 0.66;
    for (var i = 0; i < n; i++) {
      var ax = x0 + st * i + (st - w) / 2;
      s += frame ? P.archFramed(ax, yb, w, hh, frame, hole) : P.arch(ax, yb, w, hh, hole || C.hole, 0.9);
    }
    return s;
  }
  /** 门楼 pishtaq：x0..x1 宽，底 yb，顶 yt；拱洞内带木门；瓷砖边框 */
  function pishtaq(x0, x1, yb, yt, o) {
    o = o || {};
    var w = x1 - x0, s = '';
    s += K.rect(x0, yt, w, yb - yt, o.wall || C.lime, 1.6);
    s += K.flat([[x1 - w * 0.12, yt + 1], [x1 - 0.8, yt + 1], [x1 - 0.8, yb - 0.8], [x1 - w * 0.12, yb - 0.8]], C.adobe3, 0.22);
    var b = Math.max(3, w * 0.09);
    // 瓷砖边框（上 + 两侧）
    s += P.tileBand(x0 + 1.5, x1 - 1.5, yt + 2, b, o.alt);
    s += K.rect(x0 + 1.5, yt + 2 + b, b, yb - yt - 2 - b, o.alt ? C.turq : C.cobalt, 0.8);
    s += K.rect(x1 - 1.5 - b, yt + 2 + b, b, yb - yt - 2 - b, o.alt ? C.turq : C.cobalt, 0.8);
    var ax0 = x0 + b + 4, aw = w - 2 * b - 8, ah = (yb - yt) - b - 7;
    s += P.arch(ax0 - 1.5, yb, aw + 3, ah + 1.5, C.turq2, 1);
    s += P.arch(ax0, yb, aw, ah, o.hole || C.cobalt, 1);
    // 钟乳拱（muqarnas）暗示：拱顶下三层小弧
    var my = yb - ah + aw * 0.5, d = '';
    for (var r = 0; r < 3; r++) {
      var nn = 2 + r, sw = aw * (0.5 + r * 0.17) / nn, xs = ax0 + aw / 2 - sw * nn / 2, yy = my + r * aw * 0.14;
      for (var k = 0; k < nn; k++) d += 'M' + f(xs + sw * k) + ' ' + f(yy) + 'q' + f(sw / 2) + ' ' + f(-sw * 0.6) + ' ' + f(sw) + ' 0';
    }
    s += K.ln(d, 0.6, 0.8, C.lime);
    // 内门
    if (o.door !== false) s += door(ax0 + aw / 2, yb, Math.min(aw * 0.55, 18), Math.min(ah * 0.55, 30));
    if (o.star !== false && w > 30) s += P.star8(x0 + w / 2, yt + 2 + b / 2, b * 0.9, C.gold, 0.6);
    return s;
  }
  /** 木门：中心 cx，底 yb，宽 w 高 h；尖拱头，双扇，钉点 */
  function door(cx, yb, w, h, fill) {
    var s = K.path(P.archD(cx - w / 2, yb, w, h), fill || C.ochre, 1.1);
    s += K.ln(K.seg(cx, yb - h + w * 0.3, cx, yb), 0.7, 0.7);
    var d = '';
    for (var i = 1; i < 4; i++) { var yy = yb - h * 0.62 * i / 3; d += 'M' + f(cx - w * 0.3) + ' ' + f(yy) + 'h0.1M' + f(cx + w * 0.3) + ' ' + f(yy) + 'h0.1'; }
    s += K.ln(d, 1.2, 0.8, C.gold);
    return s;
  }
  /** 一排小方窗（带尖拱头），可选木格 */
  function windows(x0, x1, y, w, h, n, lattice) {
    var st = (x1 - x0) / n, s = '';
    for (var i = 0; i < n; i++) {
      var x = x0 + st * (i + 0.5) - w / 2;
      s += lattice ? P.mashrabiya(x, y, w, h) : P.arch(x, y + h, w, h, C.hole, 0.8);
    }
    return s;
  }
  /** 布棚：x0..x1，挂点 y，下垂 dy，条纹色 a/b */
  function awning(x0, x1, y, dy, a, b) {
    var w = x1 - x0, n = Math.max(2, Math.round(w / 7)), st = w / n, s = '';
    for (var i = 0; i < n; i++) {
      var xa = x0 + st * i, xb = xa + st;
      s += K.poly([[xa, y], [xb, y], [xb + 0.6, y + dy], [xa + 0.6, y + dy]], i % 2 ? (b || C.lime) : (a || C.ochre2), 0.7);
    }
    var d = 'M' + f(x0 + 0.6) + ' ' + f(y + dy);
    for (var j = 0; j < n; j++) d += 'q' + f(st / 2) + ' 2.4 ' + f(st) + ' 0';
    s += K.path(d + 'V' + f(y + dy) + 'Z', a || C.ochre2, 0.7);
    return s + K.ln(K.seg(x0, y, x1, y), 1.2, 1);
  }

  var F = { arcade: arcade, pishtaq: pishtaq, door: door, windows: windows, awning: awning };
  if (N) module.exports = F; else root.TownArtAS_facade = F;
})(this);
