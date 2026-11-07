/*
 * 织梦 · 阿拉伯民居 E：绿洲棕榈茅屋（barasti）、山坡退台屋、带鸽塔的农舍（美术样板，尚未接入游戏）
 * 浏览器挂 window.TownArtAB_housesE；Node 用 module.exports。依赖 core.js、parts.js、parts2.js、kit.js、houses-d.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  function dep(file, name) { return isNode ? require(file) : root[name]; }
  var C = dep('./core.js', 'TownArtAB_core'), Q = dep('./parts.js', 'TownArtAB_parts');
  var Q2 = dep('./parts2.js', 'TownArtAB_parts2'), K = dep('./kit.js', 'TownArtAB_kit'), HD = dep('./houses-d.js', 'TownArtAB_housesD');
  var P = C.PAL, f = C.f, FR = HD.FROND, FR2 = HD.FROND2;

  /** 棕榈叶编墙：竖向叶柄排线 + 两道横向绑扎 */
  function frondWall(x0, x1, yb, h) {
    var s = C.rect(x0, yb - h, x1 - x0, h, FR, 0), d = '';
    for (var x = x0 + 2; x < x1 - 0.5; x += 2.2) d += 'M' + f(x) + ' ' + f(yb - 0.5) + 'V' + f(yb - h + 0.5);
    s += C.line(d, 0.6, 0.5, FR2) + C.line('M' + f(x0) + ' ' + f(yb - h * 0.33) + 'H' + f(x1) + 'M' + f(x0) + ' ' + f(yb - h * 0.72) + 'H' + f(x1), 1, 0.9, P.wood);
    return s + C.rect(x0, yb - h, x1 - x0, h, 'none', 1.5);
  }
  /** 双坡棕榈叶屋顶（屋脊东西向）：檐口 ye，进深 dp，屋脊抬高 rise */
  function frondRoof(ctx, x0, x1, ye, dp, rise) {
    var yr = ye - dp * 0.6 - rise, yk = ye - dp - rise * 0.4, s = '', d = '';
    s += C.path('M' + f(x0 - 1) + ' ' + f(yr) + 'L' + f(x0 + 1) + ' ' + f(yk) + 'H' + f(x1 - 1) + 'L' + f(x1 + 1) + ' ' + f(yr) + 'Z', FR2, 1.2);
    s += C.path('M' + f(x0 - 2.5) + ' ' + f(ye + 1) + 'L' + f(x0 - 1) + ' ' + f(yr) + 'H' + f(x1 + 1) + 'L' + f(x1 + 2.5) + ' ' + f(ye + 1) + 'Z', FR, 1.5);
    for (var y = yr + 3.5; y < ye; y += 3.5) d += 'M' + f(x0 - 1) + ' ' + f(y) + 'q' + f((x1 - x0) / 4) + ' 1.2 ' + f((x1 - x0) / 2 + 1) + ' 0t' + f((x1 - x0) / 2 + 1) + ' 0';
    s += C.line(d, 0.6, 0.55, FR2) + C.line('M' + f(x0 - 1) + ' ' + f(yr) + 'H' + f(x1 + 1), 1.6, 1, P.wood);
    // 檐口垂下的叶尖
    var t = 'M' + f(x0 - 2.5) + ' ' + f(ye + 1);
    for (var x = x0 - 2.5; x < x1 + 2; x += 3) t += 'l1.5 2l1.5 -2';
    s += C.line(t, 0.7, 0.7, FR2);
    ctx.top(yk - 2);
    return s;
  }
  /** 棕榈茅屋：v1 1×1 单屋；v2 2×1 屋 + 棕榈叶平顶凉棚（arish）+ 椰枣树；v3 1×1 屋 + 棕榈叶风塔 */
  function barasti(ctx, v, fp) {
    var W = fp[0] * 48, s = '', yf = -4, x0 = 7, x1 = v === 2 ? 50 : 41, h = 18, dp = 28;
    s += C.groundShadow(x0, v === 2 ? W - 4 : x1, yf, yf - dp);
    if (v === 3) {
      // 后部风塔：四根木柱 + 棕榈叶围帘 + 布导风帆
      var tx0 = 26, tx1 = 40, tb = yf - 24, th = 46;
      s += C.line('M' + tx0 + ' ' + tb + 'V' + (tb - th) + 'M' + tx1 + ' ' + tb + 'V' + (tb - th), 1.4, 1, P.wood);
      s += frondWall(tx0, tx1, tb - 20, th - 22) + C.path('M' + f(tx0 - 1) + ' ' + f(tb - th) + 'h' + f(tx1 - tx0 + 2) + 'l-1 4h' + f(-(tx1 - tx0)) + 'Z', P.lime2, 1);
      s += C.path('M' + f(tx0 + 2) + ' ' + f(tb - 22) + 'L' + f(tx1 - 2) + ' ' + f(tb - 22) + 'L' + f((tx0 + tx1) / 2) + ' ' + f(tb - 34) + 'Z', P.lime, 0.8);
      ctx.top(tb - th - 2);
    }
    s += frondWall(x0, x1, yf, h) + frondRoof(ctx, x0, x1, yf - h, dp - 6, 10);
    s += C.rect((x0 + x1) / 2 - 5, yf - 14, 10, 14, P.dark, 1.1) + C.line('M' + f((x0 + x1) / 2 - 5) + ' ' + f(yf - 14) + 'q5 4 10 0', 0.8, 0.8, FR);
    if (v === 2) {
      var ax0 = 54, ax1 = W - 5, ay = yf - 20;
      s += Q2.palm(ctx, W - 10, yf - 22, 44, -4, { dates: true });
      s += C.line('M' + (ax0 + 1) + ' ' + yf + 'V' + ay + 'M' + (ax1 - 1) + ' ' + yf + 'V' + ay, 1.4, 1, P.wood);
      s += C.path('M' + f(ax0) + ' ' + f(ay) + 'H' + f(ax1) + 'L' + f(ax1 - 1) + ' ' + f(ay - 18) + 'H' + f(ax0 + 1) + 'Z', FR, 1.2) + C.line('M' + (ax0 + 2) + ' ' + (ay - 6) + 'H' + (ax1 - 2) + 'M' + (ax0 + 2) + ' ' + (ay - 12) + 'H' + (ax1 - 2), 0.6, 0.6, FR2);
      s += C.rect(ax0 + 6, yf - 3, ax1 - ax0 - 12, 3, P.ochre, 0.7) + K.jar(ctx, ax1 - 6, yf, 6);
    }
    return s;
  }
  /** 山坡退台屋：后排层层抬高，石砌挡土墙托起每一台；levels = [[x0,x1,前沿y,进深,墙高,台高], …] 从后往前 */
  function hillside(ctx, v, fp) {
    var W = fp[0] * 48, s = '', L;
    if (v === 1) L = [[8, 40, -60, 30, 20, 26], [5, 43, -4, 30, 22, 0]];
    else if (v === 2) L = [[50, W - 6, -66, 26, 18, 30], [6, 58, -52, 28, 22, 18], [4, W - 4, -4, 32, 20, 0]];
    else L = [[10, 44, -30, 14, 18, 20], [6, 52, -4, 20, 18, 0], [56, W - 6, -14, 20, 16, 8]];
    s += C.groundShadow(4, W - 4, -4, -fp[1] * 48 + 6);
    L.forEach(function (l, i) {
      var x0 = l[0], x1 = l[1], yf = l[2], dp = l[3], h = l[4], z = l[5], yb = yf - z;
      if (z) s += Q.facade(ctx, x0 - 2, x1 + 2, yf, z, 'stone', { noPlinth: true }) + C.rect(x0 - 2, yb - 1.5, x1 - x0 + 4, 3, P.stone2, 0.8);
      s += Q.box(ctx, x0, x1, yb, dp - 2, h, { mat: i % 2 ? 'mud' : 'lime', roof: { p: 3, wall: i % 2 ? P.mud : P.lime2, spouts: i === L.length - 1 } });
      var dx = x0 + (x1 - x0) * (i % 2 ? 0.25 : 0.55);
      s += Q.door(ctx, dx, yb, 8, 13, { kind: i ? 'pointed' : 'round', col: i % 2 ? P.ochre : P.cob2, frame: P.lime2 });
      for (var wx = x0 + 6; wx < x1 - 6; wx += 14) if (Math.abs(wx - dx - 4) > 8) s += Q2.win(wx, yb - 10, 3.5, 4.5, 'square');
    });
    if (v === 2) s += K.stair(ctx, 60, -4 - 20 - 32, 10, 12, P.stone2) + K.laundry(ctx, 10, 30, -52 - 18 - 22 - 12, [P.turq2, P.ochre2]);
    if (v === 3) s += Q2.palm(ctx, 60, -16 - 8 - 16 - 10, 26, 3, {});
    return s;
  }
  /** 鸽塔：上细下粗的圆柱土塔，表面布满陶罐口鸽孔，顶部白色小尖顶 */
  function dovecote(ctx, cx, yb, w, h) {
    var r0 = w / 2, r1 = w * 0.36, top = yb - h;
    var d = 'M' + f(cx - r0) + ' ' + f(yb) + 'L' + f(cx - r1) + ' ' + f(top) + 'H' + f(cx + r1) + 'L' + f(cx + r0) + ' ' + f(yb) + 'Z';
    var holes = '';
    for (var y = yb - 6, row = 0; y > top + 4; y -= 5, row++) {
      var t = (yb - y) / h, rr = r0 + (r1 - r0) * t;
      for (var x = cx - rr + 3 + (row % 2) * 2; x < cx + rr - 2; x += 4) holes += C.ell(x, y, 0.9, 0.9, P.hole, 0);
    }
    var inner = holes + C.rect(cx + r1 * 0.35, top - 1, r0, h + 2, P.mud3, 0, 0.4);
    var s = C.path(d, P.mud, 0) + C.clipped(ctx, d, inner) + C.path(d, 'none', 1.5);
    // 两道白色石膏环（防蛇）+ 顶部小尖顶
    s += C.rect(cx - r0 * 0.9, yb - h * 0.38, r0 * 1.8, 2.4, P.lime, 0.8) + C.rect(cx - r1 - 0.8, top + 2, r1 * 2 + 1.6, 2.4, P.lime, 0.8);
    s += C.path('M' + f(cx - r1 - 1) + ' ' + f(top) + 'Q' + f(cx - r1 * 0.3) + ' ' + f(top - 4) + ' ' + f(cx) + ' ' + f(top - 10) + 'Q' + f(cx + r1 * 0.3) + ' ' + f(top - 4) + ' ' + f(cx + r1 + 1) + ' ' + f(top) + 'Z', P.lime, 1.2);
    s += C.ell(cx - 3, top - 3, 1.6, 1, P.lime2, 0.5) + C.ell(cx + 5, top + 6, 1.6, 1, '#9a9a9a', 0.5);
    ctx.top(top - 12);
    return s;
  }
  /** 鸽塔农舍：v1 1×1 小屋 + 侧鸽塔；v2 2×1 农舍 + 院墙 + 双鸽塔；v3 2×2 院落农舍 + 大鸽塔 + 椰枣 */
  function dovefarm(ctx, v, fp) {
    var W = fp[0] * 48, s = '', yf = -4;
    if (v === 1) {
      s += C.groundShadow(4, 44, yf, -38);
      s += dovecote(ctx, 33, -14, 18, 58);
      s += Q.box(ctx, 4, 30, yf, 30, 18, { roof: { p: 3 } }) + Q.door(ctx, 10, yf, 9, 13, { col: P.wood });
      s += K.jar(ctx, 40, yf, 6);
    } else if (v === 2) {
      s += C.groundShadow(4, W - 4, yf, -40);
      s += dovecote(ctx, 62, -26, 18, 54) + dovecote(ctx, 84, -24, 14, 44);
      s += Q.box(ctx, 4, 50, yf, 34, 22, { roof: { p: 3, spouts: true } });
      s += Q.door(ctx, 14, yf, 10, 15, { kind: 'pointed', col: P.ochre, frame: P.lime2 }) + Q2.win(36, yf - 12, 4, 5, 'square');
      s += Q.facade(ctx, 50, W - 4, yf, 10, 'mud', { noPlinth: true }) + C.rect(50, yf - 12.6, W - 54, 2.6, P.lime2, 1) + Q.door(ctx, 70, yf, 9, 10, { col: P.wood2 });
    } else {
      s += C.groundShadow(4, W - 4, yf, -88);
      s += dovecote(ctx, 72, -54, 26, 76);
      s += Q.box(ctx, 6, 54, -50, 38, 22, { roof: { p: 3 } }) + Q.door(ctx, 26, -50, 9, 13, { col: P.wood });
      s += K.yard(ctx, 6, W - 6, -50, -14, '#e2cf9e');
      s += Q2.palm(ctx, 18, -22, 42, 3, { dates: true }) + K.jar(ctx, 60, -24, 7) + K.jar(ctx, 68, -22, 6, P.mud2);
      s += C.rect(4, -62, 2.6, 50, P.lime2, 0.9) + C.rect(W - 6.6, -62, 2.6, 50, P.mud3, 0.9);
      s += Q.facade(ctx, 4, W - 4, yf, 10, 'mud', { noPlinth: true }) + C.rect(3.5, yf - 12.6, W - 7, 2.6, P.lime2, 1);
      s += Q.door(ctx, 42, yf, 12, 12, { kind: 'pointed', col: P.ochre, frame: P.lime2, studs: true });
    }
    return s;
  }

  var T = [
    { n: 10, kind: 'barasti', name: '绿洲棕榈茅屋', roof: 'gable_thatch', tags: ['palm_frond', 'oasis', 'barasti'], fps: [[1, 1], [2, 1], [1, 1]], draw: barasti,
      note: '棕榈叶编墙与双坡棕榈叶顶，roof 取最近的 gable_thatch', vnote: ['单屋', '屋 + 棕榈叶凉棚 + 椰枣树', '屋 + 棕榈叶风塔'] },
    { n: 11, kind: 'hillside', name: '山坡退台屋', roof: 'flat_mud', tags: ['terraced', 'hillside', 'retaining_wall'], fps: [[1, 2], [2, 2], [2, 1]], draw: hillside,
      vnote: ['两台', '三台错落 + 梯道', '前后两台 + 侧台'] },
    { n: 12, kind: 'dovecote', name: '鸽塔农舍', roof: 'flat_mud', tags: ['farm', 'dovecote', 'pigeon_tower'], fps: [[1, 1], [2, 1], [2, 2]], draw: dovefarm,
      vnote: ['小屋 + 侧鸽塔', '农舍 + 院墙 + 双鸽塔', '院落农舍 + 大鸽塔'] }
  ];
  var API = { T: T, frondWall: frondWall, frondRoof: frondRoof, dovecote: dovecote };
  root.TownArtAB_housesE = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
