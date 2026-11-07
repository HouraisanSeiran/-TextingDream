/*
 * 阿拉伯风格体块画笔：平顶块 block、内院 court、穹顶 dome、鼓座 drum、宣礼塔 minaret、风塔 windtower。
 * 坐标约定：x0..x1 地面左右，yb 后沿、yf 前沿（地面，未上移），h 墙高。平顶顶面 = 地面范围上移 h。
 * 浏览器挂 window.TownArtAS_mass；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var N = typeof module !== 'undefined' && module.exports;
  var K = N ? require('./core.js') : root.TownArtAS_core;
  var P = N ? require('./parts.js') : root.TownArtAS_parts;
  var C = K.C, f = K.f;

  /** 平顶块：返回 svg。o: {x0,x1,yb,yf,h,wall,top,lip(女儿墙高),band(瓷砖带),noShadow,W,H} */
  function block(o) {
    var s = '', h = o.h, lip = o.lip == null ? 3 : o.lip;
    if (!o.noShadow && o.W) s += K.boxShadow(o.x0, o.x1, o.yb - h * 0.3, o.yf, Math.min(10, h * 0.35), o.W, o.H);
    s += K.rect(o.x0, o.yf - h, o.x1 - o.x0, h, o.wall || C.lime, 1.6);
    // 墙脚暗带（阴面感）
    s += K.flat([[o.x1 - (o.x1 - o.x0) * 0.12, o.yf - h + 1], [o.x1 - 0.8, o.yf - h + 1], [o.x1 - 0.8, o.yf - 0.8], [o.x1 - (o.x1 - o.x0) * 0.12, o.yf - 0.8]], C.adobe3, 0.22);
    s += K.rect(o.x0, o.yb - h, o.x1 - o.x0, o.yf - o.yb, o.top || C.lime2, 1.6);
    if (lip > 0) {
      s += K.rect(o.x0, o.yf - h - lip, o.x1 - o.x0, lip, o.wall || C.lime, 1.1);
      s += K.ln(K.seg(o.x0 + 2, o.yb - h + 2, o.x1 - 2, o.yb - h + 2), 0.8, 0.5);
    }
    if (o.band) s += P.tileBand(o.x0 + 1, o.x1 - 1, o.yf - h + 3, o.band, o.bandAlt);
    return s;
  }

  /** 内院：外盒 + 空心顶环 + 院内（后墙内立面 + 地面）+ content 回调 + 前沿顶环 */
  function court(o) {
    var s = '', h = o.h, t = o.t || 8, wall = o.wall || C.lime, top = o.top || C.lime2;
    if (o.W) s += K.boxShadow(o.x0, o.x1, o.yb - h * 0.3, o.yf, Math.min(10, h * 0.35), o.W, o.H);
    s += K.rect(o.x0, o.yf - h, o.x1 - o.x0, h, wall, 1.6);
    var ix0 = o.x0 + t, ix1 = o.x1 - t, iyT = o.yb + t - h, iyB = o.yf - t - h;
    // 院内：后墙内立面
    var fy = Math.min(o.yb + t, iyB);
    s += K.rect(ix0, iyT, ix1 - ix0, fy - iyT, o.inner || C.lime2, 1);
    if (o.riwaq && fy - iyT > 10) { // 内拱廊
      var n = Math.max(2, Math.round((ix1 - ix0) / 13)), st = (ix1 - ix0) / n;
      for (var i = 0; i < n; i++) s += P.arch(ix0 + st * i + st * 0.18, fy, st * 0.64, Math.min(fy - iyT - 3, st * 1.3), C.hole, 0.8);
    }
    if (iyB > fy) s += K.rect(ix0, fy, ix1 - ix0, iyB - fy, o.floor || C.sand, 1);
    if (o.content) s += o.content({ ix0: ix0, ix1: ix1, fy: fy, iyB: iyB, cx: (ix0 + ix1) / 2, cy: (fy + iyB) / 2 });
    // 顶环（evenodd 挖空）
    var d = K.pd([[o.x0, o.yb - h], [o.x1, o.yb - h], [o.x1, o.yf - h], [o.x0, o.yf - h]]) + K.pd([[ix0, iyT], [ix0, iyB], [ix1, iyB], [ix1, iyT]]);
    s += K.path(d, top, 1.4, 'fill-rule="evenodd"');
    if (o.lip) s += K.rect(o.x0, o.yf - h - o.lip, o.x1 - o.x0, o.lip, wall, 1);
    if (o.band) s += P.tileBand(o.x0 + 1, o.x1 - 1, o.yf - h + 3, o.band, o.bandAlt);
    return s;
  }

  /** 鼓座：中心 cx，底 by，半宽 r，高 h；带小尖拱窗 */
  function drum(cx, by, r, h, fill, nwin) {
    var s = K.rect(cx - r, by - h, 2 * r, h, fill || C.lime, 1.3);
    s += K.flat([[cx + r * 0.45, by - h + 0.8], [cx + r - 0.7, by - h + 0.8], [cx + r - 0.7, by - 0.7], [cx + r * 0.45, by - 0.7]], C.adobe3, 0.2);
    var n = nwin == null ? Math.max(2, Math.round(r / 5)) : nwin;
    if (n > 0 && h > 6) {
      var st = 2 * r / n, ww = Math.min(st * 0.45, 4.5);
      for (var i = 0; i < n; i++) s += P.arch(cx - r + st * (i + 0.5) - ww / 2, by - 1.5, ww, Math.min(h - 3, ww * 2.1), C.hole, 0.7);
    }
    return s;
  }

  /** 穹顶：底 by，半宽 r，高 hh；kind: 'pointed'|'onion'|'flat'；fill 主色；右半暗面；金尖 */
  function dome(cx, by, r, hh, fill, kind, dark) {
    var d, top = by - hh, k = kind || 'pointed';
    if (k === 'onion') {
      d = 'M' + f(cx - r) + ' ' + f(by) + 'C' + f(cx - r * 1.25) + ' ' + f(by - hh * 0.5) + ' ' + f(cx - r * 0.35) + ' ' + f(by - hh * 0.75) + ' ' + f(cx) + ' ' + f(top) +
        'C' + f(cx + r * 0.35) + ' ' + f(by - hh * 0.75) + ' ' + f(cx + r * 1.25) + ' ' + f(by - hh * 0.5) + ' ' + f(cx + r) + ' ' + f(by) + 'Z';
    } else if (k === 'flat') {
      d = 'M' + f(cx - r) + ' ' + f(by) + 'C' + f(cx - r) + ' ' + f(by - hh * 1.3) + ' ' + f(cx + r) + ' ' + f(by - hh * 1.3) + ' ' + f(cx + r) + ' ' + f(by) + 'Z';
    } else {
      d = 'M' + f(cx - r) + ' ' + f(by) + 'C' + f(cx - r) + ' ' + f(by - hh * 0.62) + ' ' + f(cx - r * 0.3) + ' ' + f(by - hh * 0.9) + ' ' + f(cx) + ' ' + f(top) +
        'C' + f(cx + r * 0.3) + ' ' + f(by - hh * 0.9) + ' ' + f(cx + r) + ' ' + f(by - hh * 0.62) + ' ' + f(cx + r) + ' ' + f(by) + 'Z';
    }
    var s = K.path(d, fill || C.turq, 1.5);
    // 右侧暗面：一条从顶到底的月牙
    var dk = 'M' + f(cx + r * 0.1) + ' ' + f(top + hh * 0.08) + 'C' + f(cx + r * 0.62) + ' ' + f(by - hh * 0.62) + ' ' + f(cx + r * 0.6) + ' ' + f(by - hh * 0.2) + ' ' + f(cx + r * 0.5) + ' ' + f(by - 0.8) +
      'L' + f(cx + r * 0.92) + ' ' + f(by - 0.8) + 'C' + f(cx + r * 0.95) + ' ' + f(by - hh * 0.4) + ' ' + f(cx + r * 0.6) + ' ' + f(by - hh * 0.75) + ' ' + f(cx + r * 0.1) + ' ' + f(top + hh * 0.08) + 'Z';
    s += K.flatD(dk, dark || C.ink, dark ? 1 : 0.2);
    // 肋线
    if (r > 9) s += K.ln('M' + f(cx - r * 0.5) + ' ' + f(by - 0.5) + 'Q' + f(cx - r * 0.45) + ' ' + f(by - hh * 0.7) + ' ' + f(cx) + ' ' + f(top + 1) +
      'M' + f(cx) + ' ' + f(by - 0.5) + 'L' + f(cx) + ' ' + f(top + 1), 0.7, 0.45);
    // 金尖 + 新月
    var fh = Math.max(4, r * 0.45);
    s += K.ln(K.seg(cx, top, cx, top - fh), 1.1, 1, C.gold);
    s += K.circle(cx, top - fh * 0.45, Math.max(1, fh * 0.14), C.gold, 0.5);
    s += K.path('M' + f(cx - fh * 0.22) + ' ' + f(top - fh * 0.9) + 'A' + f(fh * 0.2) + ' ' + f(fh * 0.2) + ' 0 1 0 ' + f(cx + fh * 0.22) + ' ' + f(top - fh * 0.9) +
      'A' + f(fh * 0.15) + ' ' + f(fh * 0.13) + ' 0 1 1 ' + f(cx - fh * 0.22) + ' ' + f(top - fh * 0.9) + 'Z', C.gold, 0.5);
    return s;
  }

  var M = { block: block, court: court, drum: drum, dome: dome };
  if (N) module.exports = M; else root.TownArtAS_mass = M;
})(this);
