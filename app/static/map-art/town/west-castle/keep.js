/*
 * 织梦 · 西式城堡 —— 主楼（keep / donjon）：方形诺曼式、圆形塔式。尚未接入游戏。
 * 每个函数返回 { id, category, kind, facility, variant, footprint, up, tags, roof, note, body }，
 * body 是 symbol 内部的 SVG；内部 clipPath id 用 "__ID__" 占位，build 时换成 symbol id 前缀。
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWC.core;
  var PAL = C.PAL, rect = C.rect, path = C.path, seg = C.seg, lines = C.lines, poly = C.poly, f = C.f, P = C.P;

  /** 前立面的一排托臂（叠涩），下面是一道暗色突堞孔：x0..x1，在 y 处，高 hh。 */
  function corbelBand(x0, x1, y, hh, step) {
    step = step || 8;
    var o = rect(x0, y, x1 - x0, hh, PAL.hole, 1);
    for (var x = x0 + step / 2; x < x1 - 2; x += step) {
      o += path('M' + P(x - 2.4, y) + 'L' + P(x + 2.4, y) + 'L' + P(x + 2.4, y + hh - 2) + 'Q' + P(x, y + hh + 1) + ' ' + P(x - 2.4, y + hh - 2) + 'Z', PAL.st1, 0.8);
    }
    return o;
  }

  /** 方形主楼（诺曼式）：3×3。扶壁、腰线、多层箭窗与双联拱窗、二层入口木梯、四角小塔、中央旗杆。 */
  function squareKeep() {
    var up = 144, x0 = 18, x1 = 126, g0 = 22, g1 = 130, h = 94, ph = 9, o = '';
    var yb = up + g1;
    o += C.dropShadow(x0, x1, up + g0 - h - ph, yb, 144, up + 144);
    var k = C.crenBox(up, x0, x1, g0, g1, 0, h, { ph: ph, e: 7, cut: 5, shade: 0.2, floor: PAL.plaster, deck: { seed: 11, hatch: [88, 142], plinth: [72, up + 76 - h] } });
    o += k.svg;
    var fy = k.front + ph; // 前脸上女墙底
    // 突堞托臂一排（女墙之下）
    o += corbelBand(x0, x1, fy, 6, 9);
    // 腰线
    var s1 = fy + 30, s2 = fy + 62;
    o += path(seg(x0, s1, x1, s1) + seg(x0, s2, x1, s2), 'none', 1.4);
    // 扶壁（角部与中线，浅色凸起的竖条）
    [[x0, x0 + 9], [68, 76], [x1 - 9, x1]].forEach(function (b) {
      o += rect(b[0], fy + 6, b[1] - b[0], yb - fy - 18, PAL.st1, 1) + C.ashlar(b[0], fy + 6, b[1] - b[0], yb - fy - 18, 8, 9, 0, 0, 0.4);
    });
    // 顶层：双联半圆拱窗；中层：十字箭窗；底层：直缝箭窗
    [36, 96].forEach(function (x) { o += C.windowA(x - 7, fy + 12, 14, 15, false, true); });
    [40, 104].forEach(function (x) { o += C.arrowSlit(x, s1 + 8, 16, true); });
    [44, 100].forEach(function (x) { o += C.arrowSlit(x, s2 + 10, 14, false); });
    // 二层入口：中线扶壁右侧的拱门 + 斜木梯
    o += C.doorA(80, s2 - 2, 13, 20, false);
    var st = 'M' + P(78, s2 - 1) + 'L' + P(93, s2 - 1) + 'L' + P(118, yb - 12) + 'L' + P(104, yb - 12) + 'Z';
    o += path(st, PAL.wood, 1.2);
    var rungs = '';
    for (var t = 1; t < 7; t++) { var u = t / 7; rungs += seg(78 + 26 * u, s2 - 1 + (yb - 12 - s2 + 1) * u, 93 + 25 * u, s2 - 1 + (yb - 12 - s2 + 1) * u); }
    o += lines(rungs, 0.8, 0.6);
    o += path(seg(93, s2 - 12, 93, s2 - 1) + seg(93, s2 - 12, 118, yb - 22) + seg(118, yb - 22, 118, yb - 12), 'none', 1.2);
    // 外扩的勒脚（墙脚斜面）
    o += poly([[x0 - 4, yb], [x1 + 4, yb], [x1 + 1, yb - 12], [x0 - 1, yb - 12]], PAL.st3, 1.3);
    o += lines(seg(x0 - 2.5, yb - 6, x1 + 2.5, yb - 6) + C.hatchD(x0, x1, yb - 11.5, yb - 6.5, 16), 0.8, 0.45);
    // 屋顶：后两角小塔 → 中央旗杆 → 前两角小塔
    function turret(tx0, tg0) {
      return C.crenBox(up, tx0, tx0 + 22, tg0, tg0 + 22, h, h + 15, { ph: 7, e: 3.5, cut: 4, shade: 0.3 }).svg;
    }
    o += turret(x0, g0) + turret(x1 - 22, g0);
    o += C.flag(72, up + 76 - h, 44, 1, 1.15);
    o += turret(x0, g1 - 22) + turret(x1 - 22, g1 - 22);
    return {
      id: 'west-common-keep-01', category: 'castle', kind: 'keep_square', facility: 'lord_hall', variant: 1,
      footprint: [3, 3], up: up, tags: ['keep', 'donjon', 'square', 'crenellated', 'flag'], roof: 'none',
      note: '方形诺曼式主楼：平顶带垛口，四角小塔；无对应 RoofId，填 none（平屋顶石台）', body: o
    };
  }

  /** 圆形主楼（塔式 donjon）：3×3。斜勒脚、托臂突堞一圈、箭窗、底层拱门、屋顶楼梯小塔 + 锥顶 + 旗。 */
  function roundKeep() {
    var up = 144, cx = 72, cg = 80, r = 50, h = 92, ph = 9, o = '';
    var ry = r * C.K;
    // 投影：落在右下方的半椭圆带
    o += C.shadow(C.ellD(cx + 7, up + cg + 4, r + 4, (r + 4) * C.K));
    // 斜勒脚
    var pl = C.cylinder(up, cx, cg, r + 5, 0, 14, PAL.st3, false);
    o += pl.svg + C.ell(cx, pl.yt, r + 5, (r + 5) * C.K, PAL.st3, 1.2);
    var cyl = C.cylinder(up, cx, cg, r, 10, h + ph, PAL.st2);
    o += cyl.svg;
    // 托臂突堞：沿前半圆一圈
    var mb = '', mc = '';
    for (var a = 0.08; a < Math.PI; a += 0.19) {
      var x = cx - r * Math.cos(a), y = cyl.yt + ry * Math.sin(a) + ph, w = 4.4 * Math.max(0.35, Math.sin(a));
      mb += C.rectD(x - w / 2, y, w, 6);
      mc += 'M' + P(x - w * 0.35, y + 6) + 'L' + P(x + w * 0.35, y + 6);
    }
    var bandD = 'M' + P(cx - r, cyl.yt + ph) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 0 ' + P(cx + r, cyl.yt + ph) +
      'L' + P(cx + r, cyl.yt + ph + 6) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 1 ' + P(cx - r, cyl.yt + ph + 6) + 'Z';
    o += path(bandD, PAL.hole, 1.1) + path(mb, PAL.st1, 0.7) + lines(mc, 0.8, 0.6);
    // 腰线
    var ys = cyl.yt + 46;
    o += path('M' + P(cx - r, ys) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 0 ' + P(cx + r, ys), 'none', 1.3);
    // 箭窗：上层三个十字窗，下层两个直缝
    [[-0.55, 22, true], [0, 22, true], [0.55, 22, true], [-0.35, 56, false], [0.4, 56, false]].forEach(function (s) {
      var xx = cx + r * s[0], yy = cyl.yt + ry * Math.sqrt(1 - s[0] * s[0]) + s[1];
      o += C.arrowSlit(xx, yy, s[2] ? 16 : 13, s[2]);
    });
    // 底层拱门 + 门前台阶
    var gy = up + cg + ry - 6;
    o += C.doorA(cx - 8, gy, 16, 24, false);
    o += rect(cx - 12, gy, 24, 4, PAL.st1, 1) + rect(cx - 15, gy + 4, 30, 3, PAL.st3, 1);
    o += C.shield(cx, gy - 34, 5, PAL.red, 'chevron');
    // 塔顶
    o += C.roundTop(cx, cyl.yt, r, ph, PAL.plaster);
    // 楼梯小塔（屋顶后左）+ 锥顶 + 旗
    var tx = cx - 20, tg = cg - 14;
    var tc = C.cylinder(up, tx, tg, 11, h, h + 30, PAL.st1);
    o += tc.svg + C.arrowSlit(tx - 2, tc.yt + 10, 9, false);
    o += C.cone(tx, tc.yt, 14, 26, PAL.sl1);
    o += C.flag(tx, tc.yt - 25, 18, 1, 0.85);
    return {
      id: 'west-common-keep-02', category: 'castle', kind: 'keep_round', facility: 'lord_hall', variant: 2,
      footprint: [3, 3], up: up, tags: ['keep', 'donjon', 'round', 'crenellated', 'machicolation', 'flag'], roof: 'steep_slate',
      note: '圆形塔式主楼：塔顶平台带垛口与突堞，屋顶楼梯小塔为青石板锥顶', body: o
    };
  }

  var API = { corbelBand: corbelBand, squareKeep: squareKeep, roundKeep: roundKeep };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else { root.TownArtWC = root.TownArtWC || {}; root.TownArtWC.keep = API; }
})(this);
