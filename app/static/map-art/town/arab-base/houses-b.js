/*
 * 织梦 · 阿拉伯民居 B：平顶土坯小屋、风塔宅（barjeel）、木格窗两层白楼（mashrabiya）、屋顶露台布棚宅（美术样板，尚未接入游戏）
 * 浏览器挂 window.TownArtAB_housesB；Node 用 module.exports。依赖 core.js、parts.js、parts2.js、kit.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  function dep(file, name) { return isNode ? require(file) : root[name]; }
  var C = dep('./core.js', 'TownArtAB_core'), Q = dep('./parts.js', 'TownArtAB_parts');
  var Q2 = dep('./parts2.js', 'TownArtAB_parts2'), K = dep('./kit.js', 'TownArtAB_kit');
  var P = C.PAL;

  /** 平顶土坯小屋：v1 单方盒；v2 左侧矮披屋 + 主屋；v3 后置小屋 + 前院矮墙与椰枣 */
  function mudhut(ctx, v) {
    var s = '', yf = -4;
    if (v === 1) {
      s += C.groundShadow(8, 40, yf, -34);
      s += Q.box(ctx, 8, 40, yf, 30, 22, { roof: { p: 3, spouts: true } });
      s += Q.door(ctx, 13, yf, 9, 15, { col: P.wood }) + Q2.win(29, yf - 12, 4, 4, 'square');
    } else if (v === 2) {
      s += C.groundShadow(4, 43, yf, -36);
      s += Q.box(ctx, 4, 19, yf, 22, 14, { fill: P.mud2, roof: { p: 2.5 } }) + K.jar(ctx, 11, yf - 22, 6);
      s += Q.box(ctx, 17, 43, yf, 32, 25, { roof: { p: 4, spouts: true } });
      s += Q.door(ctx, 25, yf, 9, 16, { kind: 'pointed', col: P.ochre, frame: P.lime2 });
      s += Q2.win(8, yf - 8, 3.5, 4, 'square') + Q2.win(37, yf - 17, 3, 6, 'slit');
    } else {
      var yb = -22;
      s += C.groundShadow(4, 44, -3, -44);
      s += K.yard(ctx, 6, 42, yb, -12, '#e2cf9e');
      s += Q.box(ctx, 8, 40, yb, 22, 20, { roof: { p: 3 } }) + Q.door(ctx, 20, yb, 8, 13, { col: P.wood });
      s += Q2.palm(ctx, 36, -10, 36, -3, { dates: true });
      // 前院矮墙：两侧墙顶 + 正面墙
      s += C.rect(4, yb - 9, 2.6, -3 - yb, P.lime2, 0.9) + C.rect(41.4, yb - 9, 2.6, -3 - yb, P.mud3, 0.9);
      s += Q.facade(ctx, 4, 44, -3, 9, 'mud', { noPlinth: true }) + C.rect(3.5, -14.5, 41, 2.6, P.lime2, 1);
      s += Q.door(ctx, 9, -3, 7, 9, { col: P.ochre2 });
    }
    return s;
  }

  /** 风塔宅：v1 1×1 单风塔；v2 2×1 石灰白墙宽风塔带瓷砖；v3 2×2 前矮翼 + 后高楼双风塔 */
  function windtower(ctx, v, fp) {
    var W = fp[0] * 48, s = '', yf = -4, x0 = 6, x1 = W - 6;
    if (v === 3) {
      var yb = -46;
      s += C.groundShadow(x0, x1, yf, -92);
      s += Q.box(ctx, x0, x1, yb, 42, 30, { roof: { p: 4, step: 6 } });
      s += Q2.windTower(ctx, x0 + 18, yb - 30 - 20, 12, 34) + Q2.windTower(ctx, x1 - 20, yb - 30 - 14, 15, 42, { mat: 'lime' });
      s += Q2.mashrabiya(ctx, x1 - 30, yb - 12, 12, 10);
      s += K.yard(ctx, 52, x1, yb, yf - 9);
      s += Q2.palm(ctx, 74, yf - 12, 40, 4, { dates: true });
      s += Q.box(ctx, x0, 50, yf, 40, 18, { roof: { p: 3, spouts: true } });
      s += Q.door(ctx, 20, yf, 10, 15, { kind: 'pointed', col: P.ochre, studs: true, frame: P.lime2 }) + Q2.win(38, yf - 10, 4, 4, 'square');
      s += Q.facade(ctx, 50, x1, yf, 9, 'mud', { noPlinth: true }) + C.rect(50, yf - 11.6, x1 - 50, 2.6, P.lime2, 1);
      return s;
    }
    var dp = fp[1] * 48 - 10, h = 24, lime = v === 2;
    s += C.groundShadow(x0, x1, yf, yf - dp);
    s += Q.box(ctx, x0, x1, yf, dp, h, { mat: lime ? 'lime' : 'mud', roof: { p: 4, wall: lime ? P.lime2 : P.mud } });
    var rb = yf - h - dp * 0.45;
    if (v === 1) {
      s += Q2.windTower(ctx, x1 - 11, rb, 12, 30);
      s += Q.door(ctx, 11, yf, 9, 15, { col: P.wood }) + Q2.win(29, yf - 15, 3, 6, 'slit');
    } else {
      s += Q2.windTower(ctx, x0 + 26, rb, 17, 38, { mat: 'lime', cap: P.sand });
      s += Q2.tileBand(ctx, x0, x1, yf - h + 5, 3, 'star');
      s += Q.door(ctx, 54, yf, 11, 16, { kind: 'pointed', col: P.cob2, studs: true, frame: P.turq });
      s += Q2.win(16, yf - 11, 4, 5, 'pointed') + Q2.win(30, yf - 11, 4, 5, 'pointed') + Q2.win(76, yf - 11, 4, 5, 'pointed');
    }
    return s;
  }

  /** 木格窗白楼：v1 1×1 两层；v2 2×1 中央大挑窗；v3 1×2 三层窄高楼带屋顶梯间 */
  function mashra(ctx, v, fp) {
    var W = fp[0] * 48, s = '', yf = -4, x0 = v === 3 ? 8 : 5, x1 = W - x0, dp = fp[1] * 48 - 12, h = [0, 44, 48, 62][v];
    s += C.groundShadow(x0, x1, yf, yf - dp);
    s += Q.box(ctx, x0, x1, yf, dp, h, { mat: 'lime', roof: { p: 4, step: 5, wall: P.lime2, mcol: P.lime } });
    s += C.line('M' + x0 + ' ' + (yf - 21) + 'H' + x1, 1, 0.7);
    if (v === 1) {
      s += Q2.mashrabiya(ctx, 10, yf - 26, 10, 12) + Q2.mashrabiya(ctx, 28, yf - 26, 10, 12);
      s += Q.door(ctx, 18, yf, 10, 16, { kind: 'pointed', col: P.wood, frame: P.lime2 });
    } else if (v === 2) {
      s += Q2.mashrabiya(ctx, 33, yf - 25, 30, 16, P.wood) + Q2.mashrabiya(ctx, 10, yf - 27, 9, 11) + Q2.mashrabiya(ctx, 77, yf - 27, 9, 11);
      s += Q.door(ctx, 42, yf, 12, 17, { kind: 'pointed', col: P.ochre, studs: true, frame: P.mud2 });
      s += Q2.win(14, yf - 11, 4, 5, 'square') + Q2.win(78, yf - 11, 4, 5, 'square');
      s += K.laundry(ctx, 14, 40, yf - h - dp * 0.4, [P.ochre2, P.turq2, P.lime]);
    } else {
      s += C.line('M' + x0 + ' ' + (yf - 41) + 'H' + x1, 1, 0.7);
      s += Q2.mashrabiya(ctx, 13, yf - 26, 9, 11) + Q2.mashrabiya(ctx, 26, yf - 26, 9, 11) + Q2.mashrabiya(ctx, 15, yf - 46, 18, 13);
      s += Q.door(ctx, 18, yf, 11, 16, { kind: 'pointed', col: P.wood, frame: P.lime2 });
      var ry = yf - h - dp * 0.55;
      s += Q.box(ctx, 12, 30, ry, 18, 14, { mat: 'lime', roof: { p: 2 } }) + Q.door(ctx, 18, ry, 6, 10, { col: P.wood });
    }
    return s;
  }

  /** 屋顶露台：v1 1×1 条纹布棚；v2 2×1 退台二层 + 前露台布棚；v3 1×1 高屋顶棕榈叶凉棚 + 外挂楼梯 */
  function terrace(ctx, v, fp) {
    var W = fp[0] * 48, s = '', yf = -4;
    if (v === 1) {
      s += C.groundShadow(5, 43, yf, -36);
      s += Q.box(ctx, 5, 43, yf, 32, 22, { roof: { p: 4 } });
      s += Q2.awning(ctx, 9, 39, yf - 22 - 30, 10, P.ochre2, P.lime, yf - 22 - 6);
      s += Q.door(ctx, 12, yf, 9, 14, { col: P.wood }) + Q2.win(30, yf - 12, 4, 4, 'square');
    } else if (v === 2) {
      s += C.groundShadow(4, W - 4, yf, -42);
      s += Q.box(ctx, 4, W - 4, yf, 38, 20, { roof: { p: 4, spouts: true } });
      s += Q.box(ctx, 8, 52, yf - 20 - 14, 22, 18, { mat: 'lime', roof: { p: 3, step: 5, wall: P.lime2, mcol: P.lime } });
      s += Q.door(ctx, 24, yf - 34, 8, 12, { col: P.cob2 }) + Q2.win(40, yf - 44, 4, 4, 'square');
      s += Q2.awning(ctx, 58, 88, yf - 20 - 26, 12, P.cob2, P.lime, yf - 20 - 5);
      s += Q.door(ctx, 20, yf, 10, 14, { kind: 'pointed', col: P.ochre, frame: P.lime2 }) + Q2.win(66, yf - 11, 4, 5, 'square') + Q2.win(80, yf - 11, 4, 5, 'square');
    } else {
      s += C.groundShadow(4, 42, yf, -34);
      s += Q.box(ctx, 12, 42, yf, 28, 30, { roof: { p: 3 } });
      s += K.stair(ctx, 2, yf, 11, 28);
      var y = yf - 30 - 6;
      s += C.line('M15 ' + y + 'v-14M39 ' + y + 'v-14', 1.3, 1, P.wood);
      s += C.path('M13 ' + (y - 14) + 'h28l-2 -10h-24Z', P.palm2, 1.1) + C.line('M15 ' + (y - 16) + 'h24M16 ' + (y - 19) + 'h22M17 ' + (y - 22) + 'h20', 0.7, 0.6, P.palm);
      ctx.top(y - 26);
      s += Q.door(ctx, 26, yf, 9, 15, { col: P.wood });
    }
    return s;
  }

  var T = [
    { n: 2, kind: 'mudhut', name: '平顶土坯小屋', roof: 'flat_mud', tags: ['adobe', 'small'], fps: [[1, 1], [1, 1], [1, 1]], draw: mudhut,
      vnote: ['单方盒', '矮披屋 + 主屋', '后置小屋 + 前院矮墙与椰枣'] },
    { n: 3, kind: 'windtower', name: '风塔宅', roof: 'flat_mud', tags: ['barjeel', 'wind_tower'], fps: [[1, 1], [2, 1], [2, 2]], draw: windtower,
      vnote: ['单风塔', '石灰白墙宽风塔、瓷砖带', '前矮翼 + 后高楼双风塔'] },
    { n: 4, kind: 'mashrabiya', name: '木格窗白楼', roof: 'flat_mud', tags: ['two_storey', 'mashrabiya', 'lime'], fps: [[1, 1], [2, 1], [1, 2]], draw: mashra,
      vnote: ['两层', '中央大挑窗、屋顶晾布', '三层窄高楼带屋顶梯间'] },
    { n: 5, kind: 'terrace', name: '屋顶露台宅', roof: 'flat_mud', tags: ['roof_terrace', 'awning'], fps: [[1, 1], [2, 1], [1, 1]], draw: terrace,
      vnote: ['条纹布棚', '退台二层 + 前露台布棚', '棕榈叶凉棚 + 外挂楼梯'] }
  ];
  var API = { T: T };
  root.TownArtAB_housesB = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
