/*
 * 织梦 · 东方文化地标（east-landmark）· 道教：大型道观、山顶仙山宫观（美术素材，尚未接入游戏）
 * def：{ kind, variant, name, facility, culture, fp:[w,d], up, tags, roof, note, draw(K, W, U, D) }，
 * draw 在 viewBox 坐标里画，占地矩形 x 0..W、y U..U+D。
 * 浏览器挂 window.TownArtEastLandmarkTaoist；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var node = typeof module !== 'undefined' && module.exports;
  var K = node ? require('./lm-core.js') : root.TownArtEastLandmarkCore;
  var PT = node ? require('./lm-parts.js') : root.TownArtEastLandmarkParts;
  var X = node ? require('./lm-extra.js') : root.TownArtEastLandmarkExtra;
  var C = K.C, TILE = K.TILE, G = K.G, GL = K.GL, f = K.f, P = K.P, R = K.R, E = K.E, L = K.L;
  var defs = [];

  /** 神道：中轴一条浅色石板路。 */
  function axisPath(cx, y0, y1, w) { return K.pave(cx - w / 2, y0, cx + w / 2, y1, 10, C.stoneLt); }

  defs.push({
    kind: 'taoist_temple', variant: 1, name: '大型道观（三清宫）', facility: 'temple', culture: 'taoist', category: 'landmark',
    fp: [5, 6], up: 56, tags: ['compound', 'courtyard', 'axial', 'multi_court', 'bagua', 'bell_tower', 'drum_tower'], roof: 'hip_tile',
    note: '中轴对称三进道观：红墙三洞山门与石狮 → 前院左钟楼右鼓楼、香炉 → 灵官殿（单檐歇山灰瓦）→ 中院八卦坛（太极）与古松 → ' +
      '汉白玉须弥座上的重檐歇山青绿琉璃三清殿（斗拱、宝葫芦、太极门额、御路台阶）。',
    draw: function (K, W, U, D) {
      var s = '', cx = W / 2, B = U + D;
      s += K.shadow(6, W - 6, U + 10, B - 3, 10);
      s += K.pave(4, U + 10, W - 4, B - 2, 12);
      s += axisPath(cx, U + 108, B - 28, 18);
      // 后墙与左右院墙
      s += K.yardWall(6, W - 6, U + 14, 16);
      s += K.sideWall(6, U + 14, B - 4, 16) + K.sideWall(W - 6, U + 14, B - 4, 16);
      // 后殿两侧古柏
      s += X.cypress(26, U + 60, 1.2) + X.cypress(W - 26, U + 60, 1.2);
      // 三清殿：须弥座 + 重檐歇山
      var tp = 12, tf = U + 104;
      s += X.terrace(36, W - 36, U + 22, tf, tp, { gap: [cx - 14, cx + 14] });
      var hl = X.grandHall(54, W - 54, U + 22 - tp + 4, tf - tp - 6, { double: true, h1: 28, h2: 18, inset: 12, skirt: 7, dg: 5,
        fac: { bays: 7, doors: [2, 3, 4], col: C.red, beam: C.teal, doorCol: C.red },
        roof: { type: 'hip', tile: TILE.teal, ov: 8, up: 11, hr: 18, ridge: 'chiwen', hipK: 0.5 } });
      s += hl.svg + PT.gourd(cx, hl.roof.ridgeY - 3, 1.25);
      s += PT.taiji(cx, hl.top + 11, 5.5);
      s += K.plaque(cx, tf - tp - 6 - 28 + 6, 26, 7, { chars: 3, bg: C.navy });
      s += X.stair(cx, tf - tp, tf + 4, 22, { yulu: true });
      // 殿前月台两只铜鼎
      s += PT.censer(cx - 30, tf + 12, 0.7, 41) + PT.censer(cx + 30, tf + 12, 0.7, 43);
      // 中院：八卦坛 + 迎客松
      s += X.pine(34, U + 150, 1.15, 1) + X.pine(W - 34, U + 150, 1.15, -1);
      s += PT.bagua(cx, U + 133, 26, 0.42, 5);
      // 灵官殿
      var lb = U + 184, lf = U + 208;
      s += K.platform(66, W - 66, lb, lf + 4, 5);
      s += K.steps(cx, lf + 4, 18, 3);
      s += X.grandHall(72, W - 72, lb - 5, lf - 5, { h: 20, dg: 4, fac: { bays: 5, doors: [2], col: C.red, beam: C.teal },
        roof: { type: 'hip', tile: TILE.grey, ov: 6, up: 9, hr: 13, ridge: 'chiwen', hipK: 0.55, pearl: true } }).svg;
      s += K.plaque(cx, lf - 5 - 20 + 6, 20, 6, { chars: 3, bg: C.navy });
      // 前院：钟楼（左）鼓楼（右）、香炉、长幡
      s += PT.bellTower(16, 50, U + 210, U + 240, { kind: 'bell', hb: 18, hp: 16, spire: true });
      s += PT.bellTower(W - 50, W - 16, U + 210, U + 240, { kind: 'drum', hb: 18, hp: 16, spire: true });
      s += PT.pennant(60, U + 262, U + 200, 6, 30, C.ochre) + PT.pennant(W - 66, U + 262, U + 200, 6, 30, C.ochre);
      s += PT.censer(cx, U + 240, 1.1, 47);
      // 山门 + 前院墙 + 石狮
      s += K.yardWall(6, cx - 34, B - 4, 16) + K.yardWall(cx + 34, W - 6, B - 4, 16);
      s += PT.shanmen(cx - 34, cx + 34, B - 30, B - 5, 26, { arches: 3, chars: 3, tile: TILE.grey });
      s += X.lion(cx - 44, B - 2, 0.9, 1) + X.lion(cx + 44, B - 2, 0.9, -1);
      return s;
    }
  });

  /** 一段山崖台地的立面多边形：顶边平直（台地前沿 yT），左右与底边用种子抖动。 */
  function crag(x0, x1, yT, yB, seed, jit) {
    jit = jit || 8;
    var r = K.rng(seed), p = [[x0, yT], [x1, yT]], i;
    for (i = 1; i <= 3; i++) p.push([x1 - r() * jit * 0.8 + jit * 0.3, yT + (yB - yT) * i / 3 - (i === 3 ? r() * jit * 0.5 : 0)]);
    for (i = 1; i <= 5; i++) p.push([x1 - (x1 - x0) * i / 6, yB - r() * jit * 0.6]);
    for (i = 2; i >= 1; i--) p.push([x0 + r() * jit * 0.8 - jit * 0.3, yT + (yB - yT) * i / 3]);
    return p;
  }
  /** 仙鹤：白身、黑翅尖、丹顶，展翅飞。k = 1 朝右、-1 朝左。 */
  function crane(x, y, s, k) {
    s = s || 1; k = k || 1;
    function q(a, b, c, d, e2, g) { return 'Q' + f(x + k * a * s) + ' ' + f(y + b * s) + ' ' + f(x + k * c * s) + ' ' + f(y + d * s); }
    var o = P('M' + f(x) + ' ' + f(y) + q(-3, -9, -10, -12) + q(-5, -5, 2, 0.5) + 'Z', C.smoke, G, 0.6);
    o += L('M' + f(x - k * 7 * s) + ' ' + f(y - 10 * s) + 'L' + f(x - k * 10 * s) + ' ' + f(y - 12 * s), C.dark, 1.2);
    o += E(x, y + 1 * s, 5.5 * s, 1.9 * s, '#ffffff', G, 0.6);
    o += P('M' + f(x + k * 1 * s) + ' ' + f(y + 0.5 * s) + q(4, -6, 12, -5) + q(5, -1, 1, 2) + 'Z', '#ffffff', G, 0.6);
    o += L('M' + f(x + k * 9 * s) + ' ' + f(y - 4.6 * s) + 'L' + f(x + k * 12 * s) + ' ' + f(y - 5 * s), C.dark, 1.2);
    var nk = 'M' + f(x + k * 4.5 * s) + ' ' + f(y + 0.4 * s) + 'L' + f(x + k * 11 * s) + ' ' + f(y - 1.6 * s);
    o += L(nk, G, 1.7) + L(nk, '#ffffff', 0.9) + K.dots([[x + k * 11.2 * s, y - 1.8 * s]], C.red, 1.6);
    o += L('M' + f(x + k * 11.8 * s) + ' ' + f(y - 1.6 * s) + 'l' + f(k * 2.4 * s) + ' ' + f(0.6 * s), C.ochre, 0.7);
    o += L('M' + f(x - k * 4.5 * s) + ' ' + f(y + 1.6 * s) + 'L' + f(x - k * 11 * s) + ' ' + f(y + 3 * s), C.dark, 0.7);
    return o;
  }

  defs.push({
    kind: 'taoist_temple', variant: 2, name: '山顶道观（仙山宫观）', facility: 'temple', culture: 'taoist', category: 'landmark',
    fp: [5, 5], up: 240, tags: ['mountain', 'terraced', 'fantasy', 'clouds', 'cranes', 'waterfall'], roof: 'hip_tile',
    note: '依山三层台地的仙山宫观：山脚汉白玉台阶与石狮 → 第一层台地单洞山门、杏黄长幡 → 御路台阶 → 第二层灵官殿（藏青琉璃）与八角攒尖亭 → ' +
      '侧面一跑石阶 → 山顶重檐歇山青绿琉璃主殿（斗拱、宝葫芦、太极）。背后两座青绿石笋，左峰顶一座小亭，右峰挂瀑布，祥云缭绕、仙鹤飞过。',
    draw: function (K, W, U, D) {
      var s = '', cx = W / 2, B = U + D;
      s += K.shadow(12, W - 12, U + 200, B - 3, 8);
      // 背后石笋两座、左峰顶小亭、右峰瀑布与松
      s += X.rock([[14, 330], [22, 180], [34, 96], [44, 50], [62, 50], [66, 120], [78, 200], [86, 330]], { seed: 3, k: 0.35 });
      s += K.pavilion(43, 63, 44, 50, 12, { post: C.red, roof: { type: 'spire', tile: TILE.teal, ov: 3, up: 5, hr: 10, finial: 5 } }).svg;
      s += X.rock([[160, 330], [170, 220], [182, 120], [194, 74], [204, 66], [214, 84], [222, 150], [230, 240], [234, 330]], { seed: 5, k: 0.35 });
      s += P('M194 98Q189 200 197 330L206 330Q198 200 201 96Z', '#cfe8e2', G, 0.6) + L('M196.5 104Q193 200 200 326M199.5 104Q197 200 203 326', C.tealLt, 0.7, 0.9);
      s += X.pine(207, 72, 0.8, -1);
      s += X.cloud(108, 74, 62) + X.cloud(150, 44, 42, { flip: true });
      // 第三层（山顶）：台地 + 重檐主殿
      s += X.rock(crag(36, 204, 200, 300, 11), { seed: 11, k: 0.22, side: C.stoneDk });
      s += K.pave(40, 150, 200, 200, 12) + X.cypress(52, 196, 0.9);
      var hl = X.grandHall(70, 170, 162, 192, { double: true, h1: 22, h2: 14, inset: 10, skirt: 6, dg: 4.5,
        fac: { bays: 5, doors: [1, 2, 3], col: C.red, beam: C.teal },
        roof: { type: 'hip', tile: TILE.teal, ov: 7, up: 11, hr: 16, ridge: 'chiwen', hipK: 0.5 } });
      s += hl.svg + PT.gourd(cx, hl.roof.ridgeY - 3, 1.15) + PT.taiji(cx, hl.top + 10, 4.6);
      s += K.plaque(cx, 192 - 22 + 6, 22, 6, { chars: 3, bg: C.navy });
      s += X.marbleRail(42, 176, 200, 5);
      s += X.stair(187, 200, 268, 16, {});
      // 第二层：台地 + 灵官殿 + 八角亭
      s += X.rock(crag(18, 222, 318, 420, 13), { seed: 13, k: 0.22, side: C.stoneDk });
      s += X.pine(40, 352, 0.7, 1) + X.pine(150, 372, 0.6, -1);
      s += K.pave(22, 262, 218, 318, 12);
      s += K.platform(28, 62, 288, 312, 3);
      s += K.pavilion(30, 60, 286, 308, 16, { post: C.red, roof: { type: 'spire', tile: TILE.teal, ov: 4, up: 7, hr: 14, finial: 6 } }).svg;
      s += X.grandHall(80, 160, 272, 306, { h: 20, dg: 4, fac: { bays: 5, doors: [2], col: C.red, beam: C.teal },
        roof: { type: 'hip', tile: TILE.navy, ov: 6, up: 9, hr: 13, ridge: 'chiwen', hipK: 0.55, pearl: true } }).svg;
      s += K.plaque(cx, 306 - 20 + 6, 20, 6, { chars: 3, bg: C.navy });
      s += X.pine(206, 314, 0.9, -1);
      s += X.marbleRail(22, cx - 13, 318, 5) + X.marbleRail(cx + 13, 218, 318, 5);
      s += X.stair(cx, 318, 400, 20, { yulu: true });
      // 第一层：台地 + 山门 + 长幡
      s += X.rock(crag(6, 234, 446, 474, 17, 4), { seed: 17, k: 0.3, side: C.stoneDk });
      s += K.pave(8, 392, 232, 446, 12);
      s += X.cypress(30, 440, 1) + X.cypress(W - 30, 440, 1);
      s += PT.pennant(70, 442, 384, 5, 26, C.ochre) + PT.pennant(W - 70, 442, 384, 5, 26, C.ochre);
      s += K.yardWall(10, 84, 444, 12) + K.yardWall(156, W - 10, 444, 12);
      s += PT.shanmen(84, 156, 420, 444, 24, { arches: 1, chars: 2, tile: TILE.teal });
      // 山脚：石阶 + 石狮
      s += K.pave(20, 472, W - 20, B - 1, 12);
      s += X.stair(cx, 447, B - 2, 24, { rail: true });
      s += X.lion(cx - 25, B - 2, 0.8, 1) + X.lion(cx + 25, B - 2, 0.8, -1);
      // 前景祥云（遮住崖脚接缝）与仙鹤
      s += X.cloud(30, 334, 50) + X.cloud(212, 300, 44, { flip: true }) + X.cloud(26, 428, 40) + X.cloud(216, 420, 40, { flip: true });
      s += X.cloud(120, 22, 52, { op: 0.9 });
      s += crane(140, 62, 1, -1) + crane(172, 88, 0.8, -1);
      return s;
    }
  });

  var API = { defs: defs, axisPath: axisPath, crag: crag, crane: crane };
  if (node) module.exports = API;
  else root.TownArtEastLandmarkTaoist = API;
})(typeof window !== 'undefined' ? window : this);
