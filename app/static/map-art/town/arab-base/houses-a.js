/*
 * 织梦 · 阿拉伯民居 A：内院宅（courtyard）（美术样板，尚未接入游戏）
 * 每种民居 { kind, name, roof, tags, fps:[每个变体的占地], draw(ctx, v) }，局部坐标 y = 0 为占地前沿、向上为负。
 * 浏览器挂 window.TownArtAB_housesA；Node 用 module.exports。依赖 core.js、parts.js、parts2.js、kit.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  function dep(file, name) { return isNode ? require(file) : root[name]; }
  var C = dep('./core.js', 'TownArtAB_core'), Q = dep('./parts.js', 'TownArtAB_parts');
  var Q2 = dep('./parts2.js', 'TownArtAB_parts2'), K = dep('./kit.js', 'TownArtAB_kit');
  var P = C.PAL, f = C.f;

  /** 女儿墙一圈：外框 x0..x1 × y0..y1（已抬高到屋面），内框为天井开口（可空） */
  function parapetRing(x0, x1, y0, y1, hole, col) {
    var s = C.rect(x0, y0 - 2.6, x1 - x0, 2.6, col || P.lime2, 1) + C.rect(x0, y0, 2.4, y1 - y0, P.lime2, 0.8) + C.rect(x1 - 2.4, y0, 2.4, y1 - y0, P.mud3, 0.8);
    if (hole) s += C.rect(hole[0] - 1.2, hole[2] - 1.6, hole[1] - hole[0] + 2.4, 1.6, P.mud3, 0.7);
    return s;
  }
  /** 内院宅：四面围合，中庭水池 + 椰枣树。v1 方正平房；v2 后翼两层带木格窗；v3 前翼起高门楼（pishtaq） */
  function courtyard(ctx, v) {
    var x0 = 3, x1 = 93, yr = -93, yf = -3, t = v === 3 ? 24 : 21, h = 22, s = '';
    var hb = v === 2 ? 40 : h;
    s += C.groundShadow(x0, x1, yf, yr + hb * 0.3);
    // 天井地面（只看得到后半部）
    var yx0 = x0 + t, yx1 = x1 - t, yy0 = yr + t, yy1 = yf - t;
    s += K.yard(ctx, yx0, yx1, yy0, yy1);
    // 后翼：朝天井的内立面 + 屋面
    s += Q.facade(ctx, yx0, yx1, yy0, hb, v === 2 ? 'lime' : 'mud');
    if (v === 2) {
      s += Q2.mashrabiya(ctx, yx0 + 8, yy0 - 22, 10, 11) + Q2.mashrabiya(ctx, yx1 - 18, yy0 - 22, 10, 11);
      s += Q2.tileBand(ctx, yx0, yx1, yy0 - hb + 4, 3.4, 'zig');
    }
    s += K.arcade(ctx, yx0 + 2, yx1 - 2, yy0, 13, v === 1 ? 3 : 2, v === 3 ? 'horseshoe' : 'pointed', v === 2 ? P.turq : P.lime2);
    // 天井里：水池、椰枣树、陶罐
    var pcx = (yx0 + yx1) / 2, pcy = Math.min(yy1 - 4, yy0 + 14);
    s += K.pool(ctx, pcx - 9, pcx + 9, pcy - 5, pcy + 2, v !== 1);
    s += K.jar(ctx, yx1 - 5, yy0 + 9, 7) + (v === 3 ? K.jar(ctx, yx0 + 5, yy0 + 9, 6, P.mud2) : '');
    // 三翼屋面（后、左、右），按高度抬起
    var rL = yr - h, rB = yr - hb;
    s += C.rect(x0, rB, x1 - x0, t, P.sand, 1.3);
    if (hb > h) s += Q.facade(ctx, x0, yx0, yr + t - h, hb - h, 'lime', { noPlinth: true }) + Q.facade(ctx, yx1, x1, yr + t - h, hb - h, 'lime', { noPlinth: true });
    s += C.rect(x0, rL + t, t, yf - yr - t, P.sand, 1.3) + C.rect(x1 - t, rL + t, t, yf - yr - t, P.sand, 1.3);
    s += parapetRing(x0, x1, rB, rB + t, null, P.lime2);
    s += C.rect(x0, rL + t, 2.4, yf - yr - t, P.lime2, 0.8) + C.rect(x1 - 2.4, rL + t, 2.4, yf - yr - t, P.mud3, 0.8);
    // 椰枣树在天井角落，冠伸出屋面
    s += Q2.palm(ctx, yx0 + 6, yy0 + 12, v === 2 ? 52 : 44, 5, { dates: v !== 2, sc: 1.15 });
    // 前翼：完整体块（外立面朝街）
    s += Q.facade(ctx, x0, x1, yf, h, 'mud');
    s += C.rect(x0, yf - h - t, x1 - x0, t, P.sand, 1.3) + C.rect(x0, yf - h - 2.6, x1 - x0, 2.6, P.lime2, 1);
    s += C.rect(x0, yf - h - t, 2.4, t, P.lime2, 0.8) + C.rect(x1 - 2.4, yf - h - t, 2.4, t, P.mud3, 0.8);
    s += C.rect(yx0 - 1.2, yf - h - t - 1.6, yx1 - yx0 + 2.4, 1.6, P.mud3, 0.7);
    s += Q2.win(14, yf - 11, 4, 5, 'square') + Q2.win(x1 - 18, yf - 11, 4, 5, 'square') + Q.spout(x0 + 6, yf - h + 1) + Q.spout(x1 - 9, yf - h + 1);
    if (v === 3) {
      // 高门楼：比前翼高出一截，钴蓝瓷砖框 + 马蹄拱门
      var gx0 = 33, gx1 = 63, gh = 40;
      s += Q.facade(ctx, gx0, gx1, yf, gh, 'lime') + C.rect(gx0, yf - gh - 8, gx1 - gx0, 8, P.sand, 1.2) + Q.merlons(gx0, gx1, yf - gh, 5, P.lime2);
      s += C.rect(gx0 + 3, yf - 34, gx1 - gx0 - 6, 31, P.cob, 1) + Q2.tileBand(ctx, gx0 + 3, gx1 - 3, yf - 32.5, 3, 'star', P.cob2, P.turq2);
      s += Q.door(ctx, 41, yf, 14, 26, { kind: 'horseshoe', col: P.ochre, studs: true, frame: P.turq });
      ctx.top(yf - gh - 14);
    } else {
      s += Q.door(ctx, 42, yf, 12, 18, { kind: 'pointed', col: v === 2 ? P.cob2 : P.ochre, studs: true, frame: P.lime2 });
      if (v === 2) s += Q2.tileBand(ctx, x0, x1, yf - h + 4, 3, 'chev', P.turq, P.lime);
    }
    ctx.top(rB - 4);
    return s;
  }

  var T = [
    { n: 1, kind: 'courtyard', name: '内院宅', roof: 'flat_mud', tags: ['courtyard', 'pool', 'palm'], fps: [[2, 2], [2, 2], [2, 2]], draw: courtyard,
      vnote: ['方正平房，三拱回廊', '后翼两层石灰白楼带木格窗', '前翼起高门楼（pishtaq）马蹄拱门'] }
  ];
  var API = { T: T, parapetRing: parapetRing };
  root.TownArtAB_housesA = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
