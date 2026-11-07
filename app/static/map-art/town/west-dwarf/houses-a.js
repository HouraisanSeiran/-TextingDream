/*
 * 织梦 · 矮人民居 A 组（01–04）（美术样板，尚未接入游戏）
 * 局部坐标：x 0..w*48，y = 0 为占地前沿，向上为负。每种 { n, kind, name, fps[3], roof, tags, draw(ctx, v) }。
 * v = { i 变体 1..3, fp 本变体占地, door 门板色, band 门箍色 }。
 * 浏览器挂 window.TownArtWD_housesA；Node 用 module.exports。依赖 core.js、parts.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWD_core;
  var K = isNode ? require('./parts.js') : root.TownArtWD_parts;
  var P = C.PAL, f = C.f;
  var DOORS = [P.copper, P.timber, P.verd, '#7a4a32'];
  function pal(ctx) { return { door: ctx.pick(DOORS), band: ctx.pick([P.iron, P.copper2, P.iron]) }; }
  /** 墙顶压檐：一条厚石檐 + 下方托块 */
  function cornice(x0, x1, y, n) {
    var s = C.rect(x0 - 2, y - 4, x1 - x0 + 4, 4.5, P.granite2, 1.3), st = (x1 - x0) / (n || 4), t = '';
    for (var i = 0; i < (n || 4); i++) t += C.rect(x0 + st * (i + 0.5) - 1.8, y + 0.5, 3.6, 2.6, P.granite, 0.8);
    return s + t;
  }

  var T = [];

  // 01 嵌山石屋：后半截埋进岩坡，只露一面巨石正立面，过梁矮门
  T.push({
    n: 1, kind: 'house_embedded', name: '嵌山石屋', fps: [[1, 1], [2, 1], [1, 1]], roof: 'none',
    tags: ['one_storey', 'embedded', 'stone'], note: '后半截埋进岩坡，屋顶即山体，roof 记 none',
    draw: function (ctx, v) {
      var W = v.fp[0] * 48, s = '', x0 = v.i === 3 ? 10 : 5, x1 = W - (v.i === 3 ? 4 : 5), h = v.i === 2 ? 26 : 23;
      s += C.groundShadow(x0, x1, 0, -30);
      // 岩坡从地面起，两侧岩肩夹住正立面，后半截房子埋在山里
      s += C.rockSlope(ctx, 0, W, 0, h + (v.i === 2 ? 30 : 26), { moss: v.i === 2 ? 3 : 2, lo: 0.5 });
      s += C.path('M' + f(x0 - 1) + ' 0L' + f(x0 - 1) + ' ' + f(-h - 2) + 'L' + f(x1 + 1) + ' ' + f(-h - 2) + 'L' + f(x1 + 1) + ' 0Z', P.deep, 0, 0.5);
      if (v.i === 2) s += K.chimney(ctx, W * 0.72, -h - 14, 7, 14, { cap: 'ring', smoke: 3 });
      s += C.blocks(ctx, x0, x1, 0, h, { minW: 12, maxW: 22 });
      s += cornice(x0, x1, -h, v.i === 2 ? 6 : 3);
      if (v.i === 2) {
        s += C.door(ctx, 30, 0, 12, 17, 'lintel', { fill: v.door, band: v.band });
        s += C.win(ctx, 52, -17, 8, 7, 'square') + C.win(ctx, 70, -17, 8, 7, 'square');
        s += K.rails(44, W - 2, -2.5);
      } else {
        var dc = v.i === 3 ? 31 : 20;
        s += C.door(ctx, dc, 0, 11, 16, 'lintel', { fill: v.door, band: v.band });
        s += C.win(ctx, v.i === 3 ? 13 : 32, -16, 6, 6, v.i === 3 ? 'slit' : 'square');
      }
      if (v.i === 3) s += K.cart(ctx, 1, -1, 9, P.copper);
      return s;
    }
  });

  // 02 拱顶石穹屋：矮圆鼓墙 + 扁石穹，拱门
  T.push({
    n: 2, kind: 'house_dome', name: '拱顶石穹屋', fps: [[1, 1], [2, 1], [1, 1]], roof: 'none',
    tags: ['one_storey', 'dome', 'stone'], note: '石砌扁穹顶，RoofId 无对应，记 none',
    draw: function (ctx, v) {
      var W = v.fp[0] * 48, s = '';
      function unit(x0, x1, h, dh, cap) {
        var o = C.blocks(ctx, x0, x1, 0, h, { course: 7, minW: 9, maxW: 15 });
        o += K.dome(ctx, x0 - 1, x1 + 1, -h, dh, { cap: cap });
        return o;
      }
      if (v.i === 2) {
        s += C.groundShadow(6, 90, 0, -40);
        s += unit(56, 90, 14, 20, 'vent');
        s += unit(6, 58, 19, 30, 'copper');
        s += C.door(ctx, 32, 0, 12, 17, 'arch', { fill: v.door, band: v.band });
        s += C.win(ctx, 70, -12, 6, 6, 'port');
        s += K.gear(ctx, 46, -10, 3.6, 8);
      } else {
        var cap = v.i === 3 ? 'copper' : 'vent';
        s += C.groundShadow(5, 43, 0, -40);
        if (v.i === 3) s += K.chimney(ctx, 36, -26, 6, 16, { cap: 'copper', smoke: 2 });
        s += unit(5, 43, v.i === 3 ? 20 : 17, v.i === 3 ? 24 : 28, cap);
        s += C.door(ctx, v.i === 3 ? 18 : 24, 0, 11, 16, 'arch', { fill: v.door, band: v.band });
        if (v.i === 3) s += C.win(ctx, 30, -14, 6, 6, 'port');
      }
      return s;
    }
  });

  // 03 阶梯石屋：两三级退台，平顶女儿墙，台阶
  T.push({
    n: 3, kind: 'house_terrace', name: '阶梯石屋', fps: [[2, 1], [2, 1], [1, 1]], roof: 'flat_mud',
    tags: ['two_storey', 'terrace', 'flat_roof'], note: '石板平顶退台，最近 RoofId 为 flat_mud',
    draw: function (ctx, v) {
      var W = v.fp[0] * 48, s = '', x0 = 4, x1 = W - 4;
      s += C.groundShadow(x0, x1, 0, -36);
      if (v.i === 3) {
        s += C.blocks(ctx, x0, x1, 0, 18);
        s += C.slabTop(ctx, x0, x1, -18, 14);
        s += C.blocks(ctx, 12, 40, -24, 15) + C.slabTop(ctx, 12, 40, -39, 14);
        s += K.chimney(ctx, 34, -46, 6, 12, { smoke: 2 });
        s += C.door(ctx, 16, 0, 10, 14, 'lintel', { fill: v.door, band: v.band });
        s += C.win(ctx, 31, -14, 6, 6, 'square') + C.win(ctx, 22, -35, 6, 6, 'slit');
        return s;
      }
      // 第二级退向左（v1）或右（v2）
      var a = v.i === 2 ? 34 : 10, b = v.i === 2 ? 88 : 64;
      s += C.blocks(ctx, x0, x1, 0, 18);
      s += C.slabTop(ctx, x0, x1, -18, 14);
      s += C.blocks(ctx, a, b, -24, 16) + C.slabTop(ctx, a, b, -40, 12);
      var ta = v.i === 2 ? 58 : 18, tb = v.i === 2 ? 82 : 42;
      s += C.blocks(ctx, ta, tb, -45, 11) + C.slabTop(ctx, ta, tb, -56, 9);
      s += K.chimney(ctx, v.i === 2 ? 46 : 56, -48, 7, 12, { cap: 'copper', smoke: 3 });
      // 外挂石阶：从地面走上第一级屋顶
      var sx = v.i === 2 ? 8 : 72, st = '';
      for (var k = 0; k < 4; k++) st += C.rect(sx + k * 3, -4.5 * (k + 1), 14 - k * 3, 4.5, P.granite3, 1);
      s += st;
      s += C.door(ctx, v.i === 2 ? 64 : 34, 0, 12, 15, 'trap', { fill: v.door, band: v.band });
      s += C.door(ctx, (a + b) / 2, -24, 9, 11, 'lintel', { fill: v.door, band: v.band, step: false, frame: 3 });
      s += C.win(ctx, v.i === 2 ? 40 : 50, -14, 7, 6, 'square') + C.win(ctx, v.i === 2 ? 80 : 14, -14, 7, 6, 'square');
      s += C.runes(ctx, ta + 3, tb - 3, -50, 5);
      return s;
    }
  });

  var API = { T: T, pal: pal, cornice: cornice };
  root.TownArtWD_housesA = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
