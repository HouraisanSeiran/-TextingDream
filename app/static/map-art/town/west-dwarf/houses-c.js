/*
 * 织梦 · 矮人民居 C 组（07–09）：石门洞宅、双层厚墙宅、齿轮磨坊宅（美术样板，尚未接入游戏）
 * 局部坐标同 houses-a.js。浏览器挂 window.TownArtWD_housesC；Node 用 module.exports。依赖 core.js、parts.js、houses-a.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWD_core;
  var K = isNode ? require('./parts.js') : root.TownArtWD_parts;
  var HA = isNode ? require('./houses-a.js') : root.TownArtWD_housesA;
  var P = C.PAL, f = C.f;

  /** 扶壁：外侧斜面的厚石墩，x 贴墙一侧，side -1 向左伸 / 1 向右伸 */
  function buttress(ctx, x, yb, h, side) {
    var w = 7, xo = x + side * w, top = yb - h;
    var d = C.poly([[x, yb], [xo, yb], [xo, yb - h * 0.45], [x + side * 2.5, top], [x, top]]);
    var tex = C.line('M' + f(Math.min(x, xo)) + ' ' + f(yb - h * 0.25) + 'H' + f(Math.max(x, xo)) +
      'M' + f(Math.min(x, xo)) + ' ' + f(yb - h * 0.5) + 'H' + f(Math.max(x, xo)), 0.8, 0.55) +
      (side > 0 ? C.rect(Math.min(x, xo), top, w, h, P.shadow, 0, 0.16) : '');
    return C.face(ctx, d, side < 0 ? P.granite3 : P.granite, tex, 1.5);
  }
  /** 凿入岩面的洞口框：梯形深色洞 + 外凿边 */
  function carved(ctx, cx, yb, w, h) {
    var x0 = cx - w / 2, x1 = cx + w / 2, y = yb - h;
    var outer = C.poly([[x0 - 4, yb], [x0 - 1, y - 4], [x1 + 1, y - 4], [x1 + 4, yb]]);
    var inner = C.poly([[x0, yb], [x0 + 2, y], [x1 - 2, y], [x1, yb]]);
    return C.path(outer, P.granite3, 1.4) + C.path(inner, P.deep2, 1.1) +
      C.line('M' + f(x0 - 2.5) + ' ' + f(y + 3) + 'l3 -2M' + f(x1 + 2.5) + ' ' + f(y + 3) + 'l-3 -2', 0.8, 0.6);
  }

  var T = [];

  // 07 石门洞宅：整面岩壁里凿出来的住宅，只看到凿边门洞、窗洞和门前石台
  T.push({
    n: 7, kind: 'house_rockcut', name: '石门洞宅', fps: [[1, 1], [2, 1], [1, 1]], roof: 'none',
    tags: ['one_storey', 'rock_cut', 'embedded'], note: '凿进岩壁的穴居，屋顶即山体，roof 记 none',
    draw: function (ctx, v) {
      var W = v.fp[0] * 48, s = '';
      s += C.groundShadow(2, W - 2, 0, -30);
      s += C.rockSlope(ctx, 0, W, -4, v.i === 2 ? 66 : 58, { lo: 0.62, moss: 3 });
      // 门前石台（凿平的台面 + 两级台阶）
      s += C.rect(3, -6, W - 6, 6, P.granite3, 1.3) + C.line('M6 -3H' + f(W - 6), 0.7, 0.5);
      if (v.i === 2) {
        s += carved(ctx, 30, -6, 20, 30) + C.door(ctx, 30, -6, 13, 20, 'trap', { fill: v.door, band: v.band, step: false, frame: 2 });
        s += carved(ctx, 64, -6, 14, 22) + C.door(ctx, 64, -6, 9, 15, 'lintel', { fill: P.timber, band: v.band, step: false, frame: 2 });
        s += C.win(ctx, 44, -34, 7, 6, 'square') + C.win(ctx, 80, -30, 6, 6, 'slit');
        s += C.runes(ctx, 18, 42, -44, 5) + K.chimney(ctx, 82, -50, 6, 10, { cap: 'ring', smoke: 2 });
        s += C.rect(46, -18, 10, 4, P.copper, 0.9) + C.line('M47 -14v6M55 -14v6', 1, 1, P.iron);
      } else if (v.i === 3) {
        // 圆门：铜圈圆门 + 两侧小窗洞
        s += C.door(ctx, 24, -6, 18, 18, 'round', { fill: P.verd, band: P.copper, split: false, step: false, frame: 3, ring: P.copper });
        s += C.win(ctx, 6, -22, 5, 5, 'port') + C.win(ctx, 37, -22, 5, 5, 'port');
        s += K.chimney(ctx, 34, -46, 5, 9, { smoke: 2 });
      } else {
        s += carved(ctx, 20, -6, 16, 26) + C.door(ctx, 20, -6, 11, 17, 'trap', { fill: v.door, band: v.band, step: false, frame: 2 });
        s += C.win(ctx, 33, -26, 6, 6, 'square') + C.runes(ctx, 8, 32, -38, 4.5);
      }
      return s;
    }
  });

  // 08 双层厚墙宅：两层巨石墙、两端斜扶壁、二层略收进，低坡石板顶；v3 为 2×2 带前院矮墙
  T.push({
    n: 8, kind: 'house_fortified', name: '双层厚墙宅', fps: [[1, 1], [2, 1], [2, 2]], roof: 'gable_tile',
    tags: ['two_storey', 'thick_wall', 'buttress'], note: '低坡石板顶，最近 RoofId 为 gable_tile（石板代瓦）',
    draw: function (ctx, v) {
      var W = v.fp[0] * 48, s = '', deep = v.fp[1] === 2;
      var x0 = 9, x1 = W - 9, yb = deep ? -34 : 0, h1 = 22, h2 = 20, dg = deep ? 40 : 24;
      s += C.groundShadow(x0 - 6, x1 + 6, 0, yb - dg - 6);
      s += C.blocks(ctx, x0, x1, yb, h1, { minW: 14, maxW: 24 });
      s += C.rect(x0 - 1.5, yb - h1 - 3, x1 - x0 + 3, 3.5, P.granite2, 1.2);
      s += C.blocks(ctx, x0 + 3, x1 - 3, yb - h1 - 3, h2, { minW: 12, maxW: 20 });
      var R = K.slabRoof(ctx, x0 + 3, x1 - 3, yb - h1 - 3 - h2, dg, v.i === 1 ? 6 : 8, { ov: 3, rivet: v.i === 3 });
      s += R.svg;
      s += buttress(ctx, x0, yb, h1 + 10, -1) + buttress(ctx, x1, yb, h1 + 10, 1);
      s += K.chimney(ctx, x1 - 9, R.yR + 3, 6, 12, { cap: v.i === 2 ? 'copper' : 'plain', smoke: 2 });
      if (v.i !== 1) s += K.chimney(ctx, x0 + 12, R.yR + 3, 6, 10, { smoke: 1 });
      var dc = v.i === 1 ? 24 : 48;
      s += C.door(ctx, dc, yb, 12, 16, 'lintel', { fill: v.door, band: v.band });
      var y2 = yb - h1 - 3 - 15;
      if (v.i === 1) s += C.win(ctx, 21, y2, 6, 7, 'slit') + C.win(ctx, 32, yb - 13, 4, 6, 'slit');
      else {
        [20, 32, 64, 76].forEach(function (x) { s += C.win(ctx, x - 3, y2, 6, 7, 'square'); });
        s += C.win(ctx, 22, yb - 14, 6, 6, 'slit') + C.win(ctx, 72, yb - 14, 6, 6, 'slit');
        s += C.rect(42, y2 - 1, 12, 9, P.red, 1) + C.line('M48 ' + f(y2 + 1) + 'v5M45 ' + f(y2 + 3.5) + 'h6', 0.9, 1, P.wash);
      }
      if (deep) { // 前院：矮石墙 + 院门两墩 + 一块磨刀石
        s += C.blocks(ctx, 2, 36, 0, 9, { course: 4.5, minW: 8, maxW: 14 }) + C.blocks(ctx, 60, 94, 0, 9, { course: 4.5, minW: 8, maxW: 14 });
        s += C.rect(34, -13, 5, 13, P.granite2, 1.2) + C.rect(57, -13, 5, 13, P.granite2, 1.2);
        s += C.rect(1, -10.5, 36, 2.5, P.granite3, 1) + C.rect(59, -10.5, 36, 2.5, P.granite3, 1);
        s += C.circle(84, -22, 4, P.granite3, 1.1) + C.rect(81, -18, 6, 3, P.timber, 0.8);
      }
      return s;
    }
  });

  // 09 齿轮磨坊宅：石屋正面嵌一组大小咬合的铜齿轮，侧面立水槽/传动轴，屋顶带风斗
  T.push({
    n: 9, kind: 'house_gearworks', name: '齿轮磨坊宅', fps: [[1, 1], [2, 1], [2, 1]], roof: 'flat_mud',
    tags: ['one_storey', 'gears', 'workshop'], note: '石板平顶 + 外露齿轮传动，最近 RoofId 为 flat_mud',
    draw: function (ctx, v) {
      var W = v.fp[0] * 48, s = '', x0 = 4, x1 = W - 4, h = v.i === 1 ? 28 : 26, dg = 22;
      s += C.groundShadow(x0, x1, 0, -h - dg);
      s += C.blocks(ctx, x0, x1, 0, h) + C.slabTop(ctx, x0, x1, -h, dg);
      s += HA.cornice(x0, x1, -h, v.fp[0] * 3);
      if (v.i === 1) {
        s += K.gear(ctx, 32, -h - 6, 9, 10, { rot: 0.1 }) + K.gear(ctx, 18, -h - 1, 5, 7, { rot: 0.4, fill: P.verd2 });
        s += C.door(ctx, 15, 0, 10, 15, 'lintel', { fill: v.door, band: v.band }) + C.win(ctx, 29, -15, 7, 6, 'square');
        return s;
      }
      // 正面大齿轮组（v2 左侧，v3 右侧并加水槽）
      var gx = v.i === 2 ? 26 : 66;
      s += C.circle(gx, -15, 13.5, P.deep2, 1.2);
      s += K.gear(ctx, gx, -15, 10.5, 12, { rot: 0.05 }) + K.gear(ctx, gx + (v.i === 2 ? 15 : -15), -26, 5.5, 8, { rot: 0.3, fill: P.verd2 });
      s += C.line('M' + f(gx) + ' -15L' + f(gx + (v.i === 2 ? 15 : -15)) + ' -26', 1.4, 1, P.iron);
      var dc = v.i === 2 ? 62 : 26;
      s += C.door(ctx, dc, 0, 12, 16, 'arch', { fill: v.door, band: v.band });
      s += C.win(ctx, v.i === 2 ? 76 : 8, -16, 7, 6, 'fire');
      if (v.i === 3) { // 侧墙引水木槽 + 小水轮
        s += C.rect(x1 - 1, -h - 8, 4, 4, P.timber, 1) + C.rect(x1 - 30, -h - 9, 30, 3, P.wood, 1);
        s += K.gear(ctx, 86, -h - 14, 4, 6, { fill: P.timber, inner: P.dark });
      }
      // 屋顶风斗
      s += C.rect(v.i === 2 ? 70 : 20, -h - dg + 2, 8, 10, P.copper, 1.1) + C.path(C.poly([[v.i === 2 ? 68 : 18, -h - dg + 2], [v.i === 2 ? 74 : 24, -h - dg - 4], [v.i === 2 ? 80 : 30, -h - dg + 2]]), P.verd, 1);
      ctx.top(-h - dg - 4);
      return s;
    }
  });

  var API = { T: T, buttress: buttress, carved: carved };
  root.TownArtWD_housesC = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
