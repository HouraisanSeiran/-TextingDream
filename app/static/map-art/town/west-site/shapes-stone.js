/*
 * 织梦 · 西式资源点 —— 采石场 stone、大理石场 marble
 * draw(ctx, W, D) 在“地面坐标”里画：占地 x∈[0,W]、y∈[0,D]，y=D 是前沿；高度画成负 y。
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWS_core;
  var P = C.P, f = C.f, path = C.path, line = C.line, ell = C.ell, poly = C.poly, seg = C.seg, shade = C.shade;

  /** 阶梯采面：后高前低 n 级台阶，每级 = 顶面(亮) + 立面(暗、带凿痕) */
  function steps(ctx, W, D, n, top, face, crack) {
    var s = '', i, x0 = 6, x1 = W - 6, stepH = 22, stepD = 16;
    // 背后山体（崖壁顶上的草皮与岩体）
    var yTop = D - 12 - n * (stepH + stepD);
    s += path('M' + f(x0 - 4) + ' ' + f(yTop + 10) + 'Q' + f(W * 0.3) + ' ' + f(yTop - 22) + ' ' + f(W * 0.55) + ' ' + f(yTop - 14) +
      'Q' + f(W * 0.8) + ' ' + f(yTop - 26) + ' ' + f(x1 + 4) + ' ' + f(yTop + 6) + 'L' + f(x1 + 4) + ' ' + f(yTop + 16) + 'L' + f(x0 - 4) + ' ' + f(yTop + 16) + 'Z',
      P.leaf2, 1.6);
    s += line(seg(x0 + 10, yTop - 2, x0 + 16, yTop - 6) + seg(W * 0.6, yTop - 12, W * 0.6 + 6, yTop - 16), 0.9, 0.7, P.leaf3);
    for (i = 0; i < n; i++) {
      var inset = (n - 1 - i) * 10, xa = x0 + inset * 0.6, xb = x1 - inset * 0.4;
      var yf = yTop + 14 + i * (stepH + stepD), yt = yf - 2;      // 立面顶
      if (i > 0) s += path(poly([[xa, yt - stepD + 2], [xb, yt - stepD + 2], [xb, yt], [xa, yt]]), top, 1.2);
      s += path(poly([[xa, yt], [xb, yt], [xb, yt + stepH], [xa, yt + stepH]]), face, 1.4);
      var cr = '';
      for (var k = 0; k < 7; k++) { var cx = ctx.rnd(xa + 6, xb - 6), cy = ctx.rnd(yt + 4, yt + stepH - 4); cr += seg(cx, cy, cx + ctx.rnd(-3, 3), cy + ctx.rnd(3, 6)); }
      for (k = 1; k < 4; k++) { var bx = xa + k * (xb - xa) / 4 + ctx.rnd(-6, 6); cr += seg(bx, yt + 1, bx, yt + stepH - 1); }
      s += line(cr, 0.8, 0.55, crack);
      s += line(seg(xa + 2, yt + stepH * 0.5, xb - 2, yt + stepH * 0.5), 0.6, 0.4, crack);
    }
    // 最前一级脚下的采场底（碎屑平地）
    var yb = yTop + 14 + n * (stepH + stepD) - 2;
    s += path(poly([[x0, yb - stepD + 2], [x1, yb - stepD + 2], [x1, D - 2], [x0, D - 2]]), top, 1.2);
    return { s: s, yb: yb };
  }
  /** 木吊杆（中世纪人力踏轮吊简化为三脚立柱 + 斜挑杆 + 吊绳石块） */
  function crane(ctx, x, yb, h, load) {
    var s = shade(poly([[x - 8, yb], [x + 22, yb], [x + 26, yb + 4], [x - 4, yb + 4]]));
    s += line(seg(x - 10, yb, x, yb - h) + seg(x + 10, yb, x, yb - h), 2.4, 1, P.dark);
    s += C.post(x, yb, h, 4);
    s += line(seg(x - 4, yb - h * 0.25, x + 46, yb - h - 18), 3.2, 1, P.dark) + line(seg(x - 4, yb - h * 0.25, x + 46, yb - h - 18), 1.4, 1, P.timber);
    s += line(seg(x, yb - h, x + 46, yb - h - 18), 0.8, 0.8);
    s += line(seg(x + 44, yb - h - 16, x + 44, yb - h * 0.35), 0.9, 1);
    s += C.block(x + 36, yb - h * 0.35 + 12, 16, 5, 12, load[0], load[1], 1.2);
    s += C.wheel(x - 2, yb - 12, 8);      // 绞盘
    return s;
  }

  C.def({
    idKind: 'site-quarry', name: '阶梯采石面', cat: 'site', resource: 'stone', facility: null,
    w: 4, d: 3, up: 70, roof: 'none', tags: ['terraced_face', 'crane', 'open_pit'],
    note: '露天阶梯采面 + 木吊杆；FacilityKind 无采石场，facility 为 null',
    draw: function (ctx, W, D) {
      var r = steps(ctx, W, D, 3, P.stone, P.stone3, P.dark);
      var s = r.s;
      s += crane(ctx, W - 66, D - 8, 54, [P.stone, P.stone2]);
      s += C.rock(ctx, 24, D - 6, 7) + C.rock(ctx, 40, D - 4, 5) + C.rock(ctx, 70, D - 22, 6);
      // 凿石匠的楔子和锤（台阶上）
      s += line(seg(110, D - 52, 118, D - 60), 1.6, 1, P.timber) + path(poly([[116, D - 63], [122, D - 60], [120, D - 57], [114, D - 60]]), P.iron, 0.8);
      return s;
    }
  });

  C.def({
    idKind: 'site-marblequarry', name: '大理石采面', cat: 'site', resource: 'marble', facility: null,
    w: 4, d: 3, up: 70, roof: 'none', tags: ['terraced_face', 'white_stone', 'sawn_blocks'],
    note: '白色阶梯采面，立面是锯切留下的平直方格切缝（区别于普通采石的乱凿痕）；facility 为 null',
    draw: function (ctx, W, D) {
      var r = steps(ctx, W, D, 3, P.marble, P.marble2, P.stone3);
      var s = r.s, i, yb = D - 8;
      // 平直切缝方格（覆盖在各级立面上）
      var g = '';
      for (i = 0; i < 3; i++) {
        var yt = D - 12 - 3 * 38 + 12 + i * 38;
        for (var k = 0; k < 7; k++) g += seg(14 + k * 26 - (2 - i) * 4, yt + 1, 14 + k * 26 - (2 - i) * 4, yt + 21);
      }
      s += line(g, 0.9, 0.8, P.stone3);
      // 灰色云纹（大理石脉）
      s += line('M30 ' + f(D - 104) + 'q14 -4 24 4t26 0M120 ' + f(D - 66) + 'q10 6 22 0t20 4', 0.8, 0.55, P.slate);
      // 前景：撬棍 + 滚木上的方块
      s += C.logSide(30, 74, yb - 2, 3) + C.block(30, yb - 5, 40, 10, 16, P.marble, P.marble2, 1.4);
      s += line(seg(80, yb, 96, yb - 30), 2, 1, P.iron);
      s += crane(ctx, W - 64, yb, 54, [P.marble, P.marble2]);
      return s;
    }
  });

  /* 石块垛：粗方石错缝码成两层 */
  C.def({
    idKind: 'prop-stonestack', name: '石块垛', cat: 'prop', resource: 'stone', w: 1, d: 1, up: 4, tags: ['stack'],
    draw: function (ctx, W, D) {
      var s = shade(poly([[6, D - 4], [46, D - 4], [48, D + 3], [8, D + 3]]));
      s += C.block(5, D - 4, 18, 8, 12, P.stone, P.stone2) + C.block(24, D - 4, 18, 8, 12, P.stone, P.stone3);
      s += C.block(9, D - 24, 14, 6, 11, P.stone, P.stone2) + C.block(24, D - 24, 15, 6, 11, P.stone, P.stone2);
      s += C.block(15, D - 41, 16, 6, 10, P.stone, P.stone3);
      return s + line(seg(10, D - 10, 14, D - 8) + seg(30, D - 12, 34, D - 9), 0.7, 0.5);
    }
  });
  /* 碎石堆：灰土丘 + 碎块 + 一把丁字镐 */
  C.def({
    idKind: 'prop-rubble', name: '碎石堆', cat: 'prop', resource: 'stone', w: 1, d: 1, up: 0, tags: ['heap', 'pick'],
    draw: function (ctx, W, D) {
      var s = C.heap(ctx, 22, D - 6, 18, 20, P.stone2, P.stone, P.stone3, 12);
      s += line(seg(34, D - 4, 44, D - 26), 1.8, 1, P.timber) + line('M38 ' + f(D - 27) + 'Q44 ' + f(D - 30) + ' 50 ' + f(D - 24), 2, 1, P.iron);
      return s;
    }
  });
  /* 精切石块（大理石）：锯得四方的白石放在木垫上，带编号刻痕 */
  C.def({
    idKind: 'prop-marbleblock', name: '精切大理石块', cat: 'prop', resource: 'marble', w: 1, d: 1, up: 6, tags: ['ashlar', 'white_stone'],
    draw: function (ctx, W, D) {
      var s = shade(poly([[6, D - 4], [46, D - 4], [48, D + 3], [8, D + 3]]));
      s += line(seg(6, D - 4, 42, D - 4) + seg(8, D - 8, 44, D - 8), 2.2, 1, P.timber);
      s += C.block(6, D - 8, 36, 12, 18, P.marble, P.marble2, 1.5);
      s += C.block(12, D - 38, 22, 8, 12, P.marble, P.marble2, 1.4);
      s += line('M10 ' + f(D - 20) + 'q8 -3 14 2t14 -1', 0.7, 0.5, P.slate);
      return s + line(seg(36, D - 18, 38, D - 14) + seg(38, D - 18, 36, D - 14), 0.8, 0.8, P.red);   // 匠人记号
    }
  });

  /* 岩板缝：左右边都在 y=16、上下边都在 x=18 与 x=38 出入，平铺时缝线首尾相接 */
  var CRACK = 'M0 16L14 18L22 30L34 23.5L48 16M14 18L18 0M22 30L18 48M34 23.5L38 0M34 23.5L38 48';
  /* 裸岩地面：岩板缝 + 碎石子，平铺 4 变体 */
  C.groundSet({
    idKind: 'ground-bedrock', name: '采石场裸岩', resource: 'stone', base: P.stone2, tags: ['quarry_floor'],
    under: function (ctx, v, W, D) {
      // 岩板缝只在格内画并且贴着上下左右边对称出入，保证拼接时缝线续得上
      return line(CRACK, 0.8, 0.45, P.stone3);
    },
    scatter: function (ctx, v) { return C.scatter(ctx, 7 + v, 'chip'); },
    item: function (sub, it, x, y) {
      return it.k < 0.25 ? C.rock(sub, x, y, 3, P.stone, P.stone3, 0.9) : C.rect(x, y, 2, 1.6, it.k < 0.6 ? P.stone : P.stone3, 0, 0.9);
    }
  });
  /* 大理石碎屑地：白屑 + 浅灰石粉 */
  C.groundSet({
    idKind: 'ground-marblechips', name: '大理石碎屑地', resource: 'marble', base: P.marble2, tags: ['quarry_floor'],
    under: function () { return line(CRACK, 0.7, 0.3, P.stone3); },
    scatter: function (ctx, v) { return C.scatter(ctx, 9 + v, 'chip'); },
    item: function (sub, it, x, y) {
      return it.k < 0.2 ? C.rock(sub, x, y, 2.6, P.marble, P.marble2, 0.8) : C.rect(x, y, 2.2, 1.4, P.marble, 0, 0.95);
    }
  });
})(typeof window !== 'undefined' ? window : this);
