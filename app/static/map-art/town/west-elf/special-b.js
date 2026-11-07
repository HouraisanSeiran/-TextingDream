/*
 * 织梦 · 城镇西式精灵族特殊建筑（二）：神殿 temple（月神祠）、客栈 inn（树荫客栈）（美术样板，尚未接入游戏）
 * 局部坐标：y = 0 为占地前沿，向上为负。
 * 浏览器挂 window.TownArtWE_specialB；Node 用 module.exports。依赖 core.js、parts.js、forms.js、houses-a.js、houses-b.js、special-a.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWE_core;
  var Q = isNode ? require('./parts.js') : root.TownArtWE_parts;
  var F = isNode ? require('./forms.js') : root.TownArtWE_forms;
  var HA = isNode ? require('./houses-a.js') : root.TownArtWE_housesA;
  var HB = isNode ? require('./houses-b.js') : root.TownArtWE_housesB;
  var SA = isNode ? require('./special-a.js') : root.TownArtWE_specialA;
  var P = C.P, f = C.f, line = C.line, path = C.path, rect = C.rect;

  /** 月牙：中心 cx,cy，半径 r */
  function crescent(cx, cy, r, fill) {
    return path('M' + f(cx + r * 0.4) + ' ' + f(cy - r) + 'A' + f(r) + ' ' + f(r) + ' 0 1 0 ' + f(cx + r * 0.4) + ' ' + f(cy + r) +
      'A' + f(r * 0.78) + ' ' + f(r * 0.78) + ' 0 1 1 ' + f(cx + r * 0.4) + ' ' + f(cy - r) + 'Z', fill || P.silver, 0.9);
  }
  /** 一圈银白立柱（环形柱廊），part 'back' 后半 / 'front' 前半 */
  function colonnade(cx, yc, rx, ry, yt, part) {
    var s = '', n = 10;
    for (var k = 0; k < n; k++) {
      var a = Math.PI * 2 * (k + 0.5) / n, sn = Math.sin(a);
      if ((part === 'back') !== (sn < 0)) continue;
      var x = cx + Math.cos(a) * rx, y = yc + sn * ry, d = 'M' + f(x) + ' ' + f(y) + 'V' + f(yt + sn * ry);
      s += line(d, 4, 1) + line(d, 2.4, 1, sn < 0 ? P.silver2 : P.silver);
    }
    return s;
  }

  // ---------------- 神殿：月神祠 ----------------
  function temple(ctx) {
    var s = C.ellShadow(52, -14, 44, 9), cx = 48;
    // 月光石圆台（两级）
    s += C.ellipse(cx, -18, 44, 15, P.moon2, 1.4) + C.ellipse(cx, -21, 44, 15, P.moon, 1.4);
    s += C.ellipse(cx, -26, 36, 12, P.moon2, 1.2) + C.ellipse(cx, -29, 36, 12, P.silver2, 1.2);
    var rx = 32, ry = 10.5, yc = -29, yt = -76;
    // 环廊顶圈（后半） + 后排柱
    s += colonnade(cx, yc, rx, ry, yt, 'back');
    // 中央圣坛：细高月光石圆身 + 尖顶 + 月牙
    var c = F.cyl(ctx, cx, yc + 6, 13, 52, { mat: 'stone', sill: false });
    s += c.svg + Q.door(ctx, cx - 4.5, yc + 5.4, 9, 15, { fill: P.moon2, frame: P.silver }) + Q.roundWin(ctx, cx, c.yt + 12, 3.6, { lit: true });
    s += F.cap(ctx, cx, c.yt, 13, 46, { shape: 'spire', mat: 'petal', finial: false, ov: 2.5 }).svg;
    var tip = c.yt - 46;
    s += line('M' + f(cx) + ' ' + f(tip + 1) + 'V' + f(tip - 6), 2.4) + line('M' + f(cx) + ' ' + f(tip + 1) + 'V' + f(tip - 6), 1, 1, P.silver);
    s += crescent(cx, tip - 11, 5.5, P.silver);
    ctx.top(tip - 18);
    // 环廊檐圈（前半，压在柱头上）+ 前排柱
    s += colonnade(cx, yc, rx, ry, yt, 'front');
    var ring = 'M' + f(cx - rx - 3) + ' ' + f(yt) + 'A' + f(rx + 3) + ' ' + f(ry + 1.5) + ' 0 0 0 ' + f(cx + rx + 3) + ' ' + f(yt) + 'v4A' + f(rx + 3) + ' ' + f(ry + 1.5) + ' 0 0 1 ' + f(cx - rx - 3) + ' ' + f(yt + 4) + 'Z';
    s += path(ring, P.silver2, 1.3) + Q.vine(ctx, (function () {
      var pts = []; for (var a = 0.15; a < Math.PI - 0.1; a += 0.3) pts.push([cx + Math.cos(a) * (rx + 2), yt + 3 + Math.sin(a) * (ry + 1)]); return pts;
    })(), { step: 4, sw: 1.2, flowers: true, len: 3.6 });
    // 前方月池 + 两盏灯 + 台阶
    s += rect(cx - 10, -9, 20, 5, P.moon2, 1) + rect(cx - 8, -5, 16, 4, P.moon, 1);
    s += C.ellipse(16, -10, 9, 3.6, P.moon2, 1) + C.ellipse(16, -10.5, 7, 2.6, P.water, 0.8) + crescent(15, -10.5, 1.6, P.silver);
    s += Q.lamp(ctx, 82, -4, 18, -1) + Q.lamp(ctx, 4, -3, 14, 1);
    return s;
  }

  // ---------------- 客栈：树荫客栈 ----------------
  function inn(ctx) {
    var s = C.groundShadow(6, 92, -6, -88);
    // 后面一棵老树撑起二层露台
    s += F.trunk(ctx, 70, -50, 10, 8, 40, { roots: 6 }).svg;
    var R = F.ring(ctx, 70, -92, 22, 3, { railH: 5 });
    s += R.back + R.deck + HA.column(ctx, 70, -93, 8, 6, -122);
    s += line('M58 -92v-8M82 -92v-8', 0.8, 0.7) + rect(63, -98, 14, 2.4, P.wood, 0.8);
    s += R.front + F.canopy(ctx, 70, -128, 28, 14, { n: 7, gems: 3 });
    // 主楼：两层（月光石底层 + 银白木上层），叶尖山墙
    var t = HB.twoStorey(ctx, 10, 54, -6, 18, 16, { lit: true, R: 16 });
    s += t.svg;
    // 招牌：叶形木牌 + 酒杯
    s += line('M54 -22h10M54 -18l4 -4', 1.2) + path(Q.leafD(58, -15, 12, 0, 3), P.wash, 1) +
      rect(61, -18.5, 3.4, 4, P.dark, 0) + line('M64.4 -17.5h1.2v2h-1.2', 0.7);
    // 侧翼马厩披屋（单坡苔顶）+ 酒桶
    s += F.wall(ctx, 56, 90, -6, 13, { mat: 'bark' }) + Q.door(ctx, 70, -6, 12, 11, { open: true });
    s += path('M54 -19L92 -19L92 -27L56 -31Z', P.moss, 1.4) + line('M58 -23.5H90M60 -27H90', 0.7, 0.45);
    s += C.ellipse(87, -8, 3.6, 4.8, P.timber, 1) + line('M83.6 -9h7', 0.8, 0.7);
    s += Q.lamp(ctx, 6, -3, 16, 1) + HB.flowerBed(ctx, 12, -5, 10, 4);
    return s;
  }

  var T = [
    { key: 'temple', suffix: true, kind: 'temple_elf_moon', name: '月神祠', facility: 'temple', fp: [2, 2], roof: 'steep_slate',
      tags: ['shrine', 'moon', 'colonnade', 'spire', 'pool'], draw: temple,
      note: '两级月光石圆台，环形银白柱廊绕着月光石圣坛，内凹花瓣尖顶顶上月牙；尖顶取最近的 steep_slate' },
    { key: 'inn', suffix: true, kind: 'inn_elf_tree', name: '树荫客栈', facility: 'inn', fp: [2, 2], roof: 'gable_tile',
      tags: ['two_storey', 'sign', 'stable_shed', 'ring_platform'], draw: inn,
      note: '两层客栈挂叶形酒杯招牌，侧翼马厩披屋，后面老树上的环形露台；叶形顶取最近的 gable_tile' }
  ];

  var API = { T: T, crescent: crescent, colonnade: colonnade };
  root.TownArtWE_specialB = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
