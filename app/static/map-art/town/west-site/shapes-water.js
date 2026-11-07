/*
 * 织梦 · 西式资源点 —— 渔场 fish、芦苇荡 reed（水色 #a9b8ad，与码头统一）
 * draw(ctx, W, D) 在“地面坐标”里画：占地 x∈[0,W]、y∈[0,D]，y=D 是前沿；高度画成负 y。
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWS_core;
  var P = C.P, f = C.f, path = C.path, line = C.line, ell = C.ell, poly = C.poly, seg = C.seg, shade = C.shade;

  /** 芦苇一丛：细茎 + 顶端穗 */
  function reeds(ctx, x, yb, n, h) {
    var st = '', hd = '';
    for (var i = 0; i < n; i++) {
      var dx = (i - n / 2) * 2.2 + ctx.rnd(-1, 1), hh = h * ctx.rnd(0.7, 1), lean = ctx.rnd(-3, 3);
      st += 'M' + f(x + dx) + ' ' + f(yb) + 'Q' + f(x + dx + lean * 0.3) + ' ' + f(yb - hh * 0.6) + ' ' + f(x + dx + lean) + ' ' + f(yb - hh);
      if (ctx.chance(0.6)) hd += C.ell(x + dx + lean, yb - hh - 2.5, 1.3, 3.2, P.thatch2, 0.6);
    }
    return line(st, 0.9, 0.9, P.leaf3) + hd;
  }
  C.reeds = reeds;

  /* 渔村栈桥：木栈桥伸进水里 + 系着的小渔船 + 岸上小渔屋 */
  C.def({
    idKind: 'site-fishjetty', name: '渔村栈桥', cat: 'site', resource: 'fish', facility: 'dock',
    w: 4, d: 3, up: 48, roof: 'gable_thatch', tags: ['jetty', 'fishing_boat', 'hut'],
    note: '岸在后、水在前：栈桥朝屏幕下方伸进水面；小码头对 dock',
    draw: function (ctx, W, D) {
      // 岸线落在格边界（第 2 行与第 3 行之间），左右两端水平，与相邻水面瓦片接得上
      var s = '', i, shore = D - 48;
      s += path(poly([[0, shore], [W, shore], [W, D], [0, D]]), P.water, 0);
      s += line('M0 ' + f(shore) + 'Q' + f(W * 0.3) + ' ' + f(shore + 3) + ' ' + f(W * 0.5) + ' ' + f(shore) + 'T' + f(W) + ' ' + f(shore), 1.6);
      var rp = '';
      for (i = 0; i < 9; i++) { var x = ctx.rnd(8, W - 20), y = ctx.rnd(shore + 14, D - 6); rp += seg(x, y, x + ctx.rnd(6, 12), y); }
      s += line(rp, 0.9, 0.7, P.water2);
      // 岸上渔屋（后方）
      var hx = 14, hy = shore - 4;
      s += shade(poly([[hx + 56, hy], [hx + 64, hy - 4], [hx + 64, hy - 30], [hx + 56, hy - 34]]));
      s += path(poly([[hx, hy - 34], [hx + 56, hy - 34], [hx + 56, hy], [hx, hy]]), P.plaster, 1.5);
      s += line(seg(hx, hy - 17, hx + 56, hy - 17) + seg(hx + 18, hy - 34, hx + 18, hy) + seg(hx + 38, hy - 34, hx + 38, hy), 1.6, 1, P.timber);
      s += path(poly([[hx + 22, hy - 14], [hx + 34, hy - 14], [hx + 34, hy], [hx + 22, hy]]), P.dark, 1);
      s += C.roofGable(hx - 6, hx + 62, hy - 32, hy - 58, 10, P.thatch, P.thatch2, 4);
      // 栈桥：桩 + 板面，从岸伸到前沿
      var jx = W / 2 + 18, jw = 22;
      for (i = 0; i < 4; i++) { var py = shore + 8 + i * 20; s += C.post(jx + 2, py + 6, 12, 3) + C.post(jx + jw - 2, py + 6, 12, 3); }
      s += path(poly([[jx, shore - 6], [jx + jw, shore - 6], [jx + jw, D - 10], [jx, D - 10]]), P.wood, 1.4);
      var pl = '';
      for (i = 1; i < 14; i++) pl += seg(jx + 1, shore - 6 + i * 6.4, jx + jw - 1, shore - 6 + i * 6.4);
      s += line(pl, 0.7, 0.55);
      s += path(poly([[jx, D - 10], [jx + jw, D - 10], [jx + jw, D - 6], [jx, D - 6]]), P.timber, 1);
      // 系在栈桥左侧的小渔船（船头朝后）
      var bx = jx - 30, by = D - 24;
      s += path('M' + f(bx - 12) + ' ' + f(by - 6) + 'Q' + f(bx) + ' ' + f(by + 6) + ' ' + f(bx + 12) + ' ' + f(by - 6) + 'L' + f(bx + 6) + ' ' + f(by - 40) +
        'Q' + f(bx) + ' ' + f(by - 48) + ' ' + f(bx - 6) + ' ' + f(by - 40) + 'Z', P.timber, 1.4);
      s += path('M' + f(bx - 8) + ' ' + f(by - 8) + 'Q' + f(bx) + ' ' + f(by - 2) + ' ' + f(bx + 8) + ' ' + f(by - 8) + 'L' + f(bx + 4) + ' ' + f(by - 36) + 'L' + f(bx - 4) + ' ' + f(by - 36) + 'Z', P.wood, 0.9);
      s += line(seg(bx - 7, by - 20, bx + 7, by - 20), 1.4, 1, P.dark) + line(seg(bx + 8, by - 30, jx, by - 34), 0.8, 0.9);
      // 栈桥上的鱼篓与一卷网
      s += path(poly([[jx + 4, D - 30], [jx + 12, D - 30], [jx + 11, D - 20], [jx + 5, D - 20]]), P.thatch2, 1);
      s += ell(jx + 16, D - 46, 5, 3, P.stone2, 0.9);
      return s;
    }
  });
  /* 晒网架：两根立柱 + 横杆 + 垂挂的渔网（菱形网眼） */
  C.def({
    idKind: 'prop-netrack', name: '晒网架', cat: 'prop', resource: 'fish', w: 1, d: 1, up: 12, tags: ['net', 'drying'],
    draw: function (ctx, W, D) {
      var s = shade(poly([[6, D - 4], [46, D - 4], [47, D + 2], [7, D + 2]]));
      s += C.post(6, D - 4, 52, 3) + C.post(42, D - 4, 52, 3) + line(seg(3, D - 54, 45, D - 54), 2.2, 1, P.dark);
      var net = 'M8 ' + f(D - 54) + 'Q24 ' + f(D - 12) + ' 40 ' + f(D - 54);
      s += path(net + 'Z', P.stone, 1, 0.55);
      var g = '';
      for (var i = 0; i < 6; i++) { var x = 10 + i * 5.6; g += seg(x, D - 53, x + 8, D - 30) + seg(x + 8, D - 53, x, D - 30); }
      s += C.clip(ctx, net + 'Z', line(g, 0.6, 0.8));
      return s + line(net, 1.1, 1) + ell(24, D - 32, 2.4, 1.6, P.cork || P.wood, 0.6);
    }
  });
  /* 鱼篓：两只柳编篓 + 一条鱼 */
  C.def({
    idKind: 'prop-fishbasket', name: '鱼篓', cat: 'prop', resource: 'fish', w: 1, d: 1, up: 0, tags: ['basket', 'catch'],
    draw: function (ctx, W, D) {
      var s = C.shadowEll(27, D - 5, 20, 4);
      [[16, D - 4, 9, 18], [33, D - 6, 8, 15]].forEach(function (b) {
        s += path(poly([[b[0] - b[2], b[1] - b[3]], [b[0] + b[2], b[1] - b[3]], [b[0] + b[2] - 2, b[1]], [b[0] - b[2] + 2, b[1]]]), P.thatch2, 1.2);
        var w = '';
        for (var k = 1; k < 4; k++) w += seg(b[0] - b[2] + k * 0.5, b[1] - b[3] + k * b[3] / 4, b[0] + b[2] - k * 0.5, b[1] - b[3] + k * b[3] / 4);
        s += line(w, 0.7, 0.6) + ell(b[0], b[1] - b[3], b[2], 2.4, P.thatch, 1);
      });
      s += path('M8 ' + f(D - 23) + 'q8 -6 14 0l4 -3l0 6l-4 -3q-6 6 -14 0z', P.silver, 0.9);
      return s;
    }
  });

  /* ---------- 芦苇荡 reed ---------- */
  /* 芦苇割场：浅水边的芦苇丛 + 割出的空地 + 镰刀 + 平底小船 */
  C.def({
    idKind: 'site-reedcut', name: '芦苇割场', cat: 'site', resource: 'reed', facility: null,
    w: 4, d: 2, up: 30, tags: ['marsh', 'reed_bed', 'punt'], note: '沼泽浅水边割苇；facility 为 null',
    draw: function (ctx, W, D) {
      var s = '', i;
      // 后方浅水 + 前方泥滩
      // 水面不勾外框（与场景里的水面瓦片相接），只勾岸线；泥滩边缘做成圆缓的不规则形
      s += path('M0 ' + f(D - 60) + 'Q' + f(W * 0.4) + ' ' + f(D - 50) + ' ' + f(W) + ' ' + f(D - 62) + 'L' + f(W) + ' ' + f(D - 96) + 'L0 ' + f(D - 96) + 'Z', P.water, 0);
      s += path('M0 ' + f(D - 60) + 'Q' + f(W * 0.4) + ' ' + f(D - 50) + ' ' + f(W) + ' ' + f(D - 62) + 'Q' + f(W - 4) + ' ' + f(D - 22) + ' ' + f(W - 44) + ' ' + f(D - 8) +
        'Q' + f(W * 0.5) + ' ' + f(D - 2) + ' 40 ' + f(D - 8) + 'Q4 ' + f(D - 22) + ' 0 ' + f(D - 60) + 'Z', P.mud, 0);
      s += line('M0 ' + f(D - 60) + 'Q' + f(W * 0.4) + ' ' + f(D - 50) + ' ' + f(W) + ' ' + f(D - 62), 1.4);
      s += line(seg(20, D - 80, 32, D - 80) + seg(120, D - 76, 134, D - 76), 0.9, 0.7, P.water2);
      // 后排高芦苇丛（左右两片，中间是割开的豁口）
      for (i = 0; i < 9; i++) s += reeds(ctx, 6 + i * 9, D - 54 + (i % 2) * 4, 7, 44);
      for (i = 0; i < 6; i++) s += reeds(ctx, W - 62 + i * 10, D - 54 + (i % 2) * 4, 7, 44);
      // 割后留下的短茬
      var stub = '';
      for (i = 0; i < 18; i++) { var x = ctx.rnd(92, W - 70), y = ctx.rnd(D - 50, D - 24); stub += seg(x, y, x + 0.5, y - 3); }
      s += line(stub, 1, 0.8, P.thatch2);
      // 平底小船停在水边，船里一捆苇
      var bx = 120, by = D - 62;
      s += path('M' + f(bx - 26) + ' ' + f(by - 6) + 'L' + f(bx + 26) + ' ' + f(by - 6) + 'L' + f(bx + 20) + ' ' + f(by + 2) + 'L' + f(bx - 20) + ' ' + f(by + 2) + 'Z', P.timber, 1.3);
      s += path(poly([[bx - 18, by - 12], [bx + 14, by - 12], [bx + 16, by - 6], [bx - 20, by - 6]]), P.thatch, 1);
      s += line(seg(bx + 22, by - 4, bx + 40, by - 34), 1.4, 1, P.timber);
      // 前景：镰刀 + 一小捆
      s += line(seg(30, D - 8, 40, D - 20), 1.6, 1, P.timber) + line('M40 ' + f(D - 20) + 'q8 -2 8 6', 1.6, 1, P.iron);
      s += path(poly([[56, D - 8], [92, D - 14], [94, D - 8], [58, D - 3]]), P.thatch, 1.1) + line(seg(72, D - 13, 74, D - 5), 1.4, 1, P.dark);
      return s;
    }
  });
  /* 捆苇垛：立着靠成圆锥的苇捆 */
  C.def({
    idKind: 'prop-reedstook', name: '捆苇垛', cat: 'prop', resource: 'reed', w: 1, d: 1, up: 20, tags: ['bundle', 'stook'],
    draw: function (ctx, W, D) {
      var s = C.shadowEll(28, D - 5, 18, 4), i, cx = 24;
      for (i = -3; i <= 3; i++) {
        var bx = cx + i * 4.4;
        s += path(poly([[bx - 3.5, D - 4], [bx + 3.5, D - 4], [cx + i * 1.2 + 2, D - 62], [cx + i * 1.2 - 2, D - 62]]), Math.abs(i) % 2 ? P.thatch2 : P.thatch, 0.9);
      }
      s += line(seg(cx - 13, D - 22, cx + 13, D - 22), 1.6, 1, P.dark);
      return s + C.ell(cx, D - 64, 4, 3, P.thatch2, 0.8);
    }
  });
  /* 芦苇丛（单丛摆件，铺在水边） */
  C.def({
    idKind: 'prop-reedclump', name: '芦苇丛', cat: 'prop', resource: 'reed', w: 1, d: 1, up: 12, tags: ['marsh'],
    draw: function (ctx, W, D) {
      var s = ell(24, D - 6, 20, 5, P.water, 1, 0.9);
      return s + reeds(ctx, 16, D - 6, 8, 46) + reeds(ctx, 32, D - 5, 7, 40);
    }
  });
})(typeof window !== 'undefined' ? window : this);
