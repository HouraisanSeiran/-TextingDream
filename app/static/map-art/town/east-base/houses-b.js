/*
 * 织梦 · 东方民居（二）：两层铺面、茅舍、硬山小宅、竹楼、窑洞、碉楼、园林宅院、歇山大宅、渔家棚屋、悬山农舍
 * 坐标与画法约定同 houses-a.js（原点 = 占地左前角，g 向南，z 向上，屏幕 y = g - z*K）。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./east-core.js'), require('./houses-a.js'));
  else root.TownArtEast_housesB = factory(root.TownArtEast_core, root.TownArtEast_housesA);
})(this, function (E, HA) {
  'use strict';
  var C = E.C, T = E.TILE, f = E.f, sy = E.sy, K = E.K, H = HA.H, HOUSES = [];

  function seg(x0, y0, x1, y1) { return 'M' + f(x0) + ' ' + f(y0) + 'L' + f(x1) + ' ' + f(y1); }
  // 幌子：立杆 + 横挑 + 一面燕尾布招（布面上一枚米白圆章）
  function banner(x, g, ztop, c) {
    var yt = sy(g, ztop), s = '';
    E.track(yt - 2);
    s += E.line(seg(x, g, x, yt), C.umber, 1.4) + E.line(seg(x - 1, yt + 1, x + 10, yt + 1), C.umber, 1.1);
    var bx = x + 2.5, by = yt + 2, bw = 6.5, bh = 17;
    s += E.path('M' + f(bx) + ' ' + f(by) + 'h' + f(bw) + 'v' + f(bh) + 'l' + f(-bw / 2) + ' -3.2l' + f(-bw / 2) + ' 3.2Z', c || C.vermil, C.gold2, 0.6);
    s += E.circle(bx + bw / 2, by + 5, 2.3, C.creamL, C.gold, 0.4) + E.line(seg(bx + bw / 2 - 1.2, by + 5, bx + bw / 2 + 1.2, by + 5) + seg(bx + bw / 2, by + 3.8, bx + bw / 2, by + 6.2), C.umber, 0.6);
    return s;
  }
  // 篱笆：一排竖枝 + 两道横条，gap = [xa, xb] 留出门口
  function fence(x0, x1, g, hz, gap) {
    var d = '', yT = sy(g, hz);
    for (var x = x0; x <= x1 + 0.01; x += 2.4) if (!gap || x < gap[0] || x > gap[1]) d += seg(x, g, x + 0.3, yT - 0.8);
    var rail = function (z) {
      var y = sy(g, z);
      return gap ? seg(x0 - 0.5, y, gap[0], y) + seg(gap[1], y, x1 + 0.5, y) : seg(x0 - 0.5, y, x1 + 0.5, y);
    };
    return E.line(d, C.umber, 0.8) + E.line(rail(hz * 0.35) + rail(hz * 0.8), C.umberL, 1.1);
  }
  // 草垛：馒头形，竖向草纹
  function haystack(ctx, cx, g, r) {
    var yt = g - r * 1.5, d = 'M' + f(cx - r) + ' ' + f(g) + 'Q' + f(cx - r) + ' ' + f(yt) + ' ' + f(cx) + ' ' + f(yt) + 'Q' + f(cx + r) + ' ' + f(yt) + ' ' + f(cx + r) + ' ' + f(g) + 'Z';
    E.track(yt - 3);
    return E.shadow(cx - r, cx + r, g - 4, g, 6, 3) + E.path(d, T.thatch.lite) + E.clip(ctx, d, E.rowsV(cx - r, cx + r, yt, g, 1.8, T.thatch.dark, 0.6, 0.6)) +
      E.path(d, 'none', C.umber, 0.8) + E.line(seg(cx, yt, cx, yt - 3), C.umber, 0.9);
  }

  // 6. 两层铺面：下店上宅，底层排门板，腰檐，二层格窗，门前立幌子
  HOUSES.push({
    kind: 'puwu', name: '两层铺面', fp: [2, 1], roof: 'gable_tile', tags: ['two_storey', 'shop', 'banner'],
    note: '下店上宅，悬山顶带燕尾脊，一道腰檐；门前立杆挂燕尾幌子',
    variants: [{ w: 2, t: 'gray' }, { w: 2, t: 'teal', flag: 'navy' }, { w: 1, t: 'navy' }],
    draw: function (ctx, v) {
      var W = v.w * 48, t = T[v.t], s = '', x0 = 5, x1 = W - 5, gf = -7, gb = -38, z1 = 20, h = 38, n = v.w * 2, bw = (x1 - x0) / n, k;
      s += E.shadow(x0, x1, gb, gf, h + 12);
      s += E.plinth(x0 - 1.5, x1 + 1.5, gf + 1.5, 2);
      s += E.face(x0, x1, gf, 2, z1, C.umberL);
      for (k = 0; k < n; k++) {
        var bx = x0 + k * bw, shop = v.w === 1 ? k === 0 : (k === 1 || k === 2);
        if (shop) s += E.door(bx + 1.5, gf, 2, bw - 3, 14.5, 'shop');
        else s += E.win(bx + 3, gf, 7, bw - 6, 8, 'lattice') + E.rect(bx + 2, sy(gf, 6), bw - 4, 1.4, C.umber); // 柜台窗
      }
      for (k = 0; k <= n; k++) s += E.col(x0 + k * bw, gf, 2, z1, C.umber);
      // 二层：略收进，一排格窗 + 窗下栏杆
      s += E.face(x0 + 1, x1 - 1, gf - 3, z1, h, C.cream);
      for (k = 0; k < n; k++) s += E.win(x0 + 1 + k * bw + 3, gf - 3, z1 + 5, bw - 6, 9, k % 2 ? 'hex' : 'lattice');
      s += H.railing(x0 + 2, x1 - 2, gf - 3, z1 + 1, z1 + 5, C.vermil, 2.6);
      for (k = 0; k <= n; k++) s += E.col(x0 + 1 + k * (x1 - x0 - 2) / n, gf - 3, z1, h, C.vermil);
      s += E.face(x0, x1, gf - 3, h - 2.4, h, C.teal, C.gold2, 0.5);
      // 腰檐压住上下层交界
      s += H.shed(ctx, x0, x1, gf - 3, z1 - 1, t, 5, 1.5);
      // 招牌匾
      s += E.rect((x0 + x1) / 2 - 9, sy(gf - 3, z1 + 16.5), 18, 4.5, C.navy, C.gold2, 0.6) + E.line(seg((x0 + x1) / 2 - 6, sy(gf - 3, z1 + 14.3), (x0 + x1) / 2 + 6, sy(gf - 3, z1 + 14.3)), C.gold2, 0.8, ' stroke-dasharray="2 1.4"');
      s += E.roofEW(ctx, { x0: x0, x1: x1, gb: gb, gf: gf - 3, h: h, rh: 12, type: 'hang', t: t, ridge: 'horn', ov: 4 });
      s += E.lantern(x0 + bw, sy(gf + 2, z1 - 4), 2) + E.lantern(x1 - bw, sy(gf + 2, z1 - 4), 2);
      s += banner(x0 - 2, -1, h + 2, v.flag ? C[v.flag] : C.vermil);
      return s;
    }
  });

  // 7. 茅舍：夯土墙、茅草悬山顶、柴门篱笆
  HOUSES.push({
    kind: 'maoshe', name: '茅舍', fp: [1, 1], roof: 'gable_thatch', tags: ['thatch', 'poor', 'fence'],
    note: '夯土墙，茅草悬山顶，屋脊压一道草绳；前面柴门篱笆（变体 2 带草垛）',
    variants: [{ fenceOn: true }, { stack: true }],
    draw: function (ctx, v) {
      var t = T.thatch, s = '', x0 = v.stack ? 4 : 8, x1 = v.stack ? 31 : 40, gf = -12, gb = -34, h = 16;
      s += E.shadow(x0, x1, gb, gf, h + 10);
      s += E.face(x0, x1, gf, 0, h, C.earth);
      var dd = '';
      for (var z = 3; z < h - 1; z += 3.2) dd += seg(x0 + 1, sy(gf, z), x1 - 1, sy(gf, z));
      s += E.line(dd, C.umber, 0.5, ' stroke-opacity="0.35"');
      var dx = v.stack ? x0 + 4 : x0 + 12;
      s += E.door(dx, gf, 0, 8, 12, 'plank');
      s += E.win(v.stack ? x1 - 11 : x0 + 3, gf, 6, 6, 5, 'lattice');
      if (!v.stack) s += E.win(x1 - 9, gf, 6, 6, 5, 'lattice');
      s += E.roofEW(ctx, { x0: x0, x1: x1, gb: gb, gf: gf, h: h, rh: 14, type: 'hang', t: t, ov: 5, os: 4, lift: 0.6, dots: false, step: 2.2, ridgeW: 3.4 });
      // 压脊草绳
      var yr = sy((gb + gf) / 2, h + 14), dr = '';
      for (var x = x0 - 2; x < x1 + 2; x += 5) dr += seg(x, yr - 2, x + 1.5, yr + 2);
      s += E.line(dr, C.umber, 0.9);
      if (v.fenceOn) s += fence(3, 45, -3, 7, [dx - 1, dx + 9]);
      if (v.stack) s += haystack(ctx, 40, -9, 6.5) + E.circle(21, -4, 2.6, C.umberL, C.gold, 0.5) + E.circle(21, -5, 1.6, C.water);
      return s;
    }
  });

  // 8. 硬山小宅：两山砖墙齐屋面，墀头挑出；三开间，一明两暗
  HOUSES.push({
    kind: 'yingshan', name: '硬山小宅', fp: [1, 1], roof: 'gable_tile', tags: ['brick_gable', 'small'],
    note: '硬山顶，山墙与屋面齐平，檐下两端砖雕墀头；变体 2 圆窗、燕尾脊',
    variants: [{ t: 'gray', ridge: 'plain' }, { t: 'navy', ridge: 'horn', round: true }],
    draw: function (ctx, v) {
      var t = T[v.t], s = '', x0 = 6, x1 = 42, gf = -8, gb = -34, h = 22, ph = 2;
      s += E.shadow(x0, x1, gb, gf, h + 12);
      s += E.plinth(x0 - 2, x1 + 2, gf + 1.5, ph);
      s += E.face(x0, x1, gf, ph, h, C.cream);
      s += E.face(x0, x1, gf, ph, ph + 4, C.grayL, C.gold, 0.6);
      s += E.door(x0 + 13, gf, ph, 10, 14, 'double');
      if (v.round) s += E.win(x0 + 3, gf, ph + 6, 7, 7, 'round') + E.win(x1 - 10, gf, ph + 6, 7, 7, 'round');
      else s += E.win(x0 + 3, gf, ph + 6, 8, 7, 'lattice') + E.win(x1 - 11, gf, ph + 6, 8, 7, 'lattice');
      // 两端砖砌山墙垛
      [x0 - 2, x1 - 2].forEach(function (x) {
        s += E.face(x, x + 4, gf + 0.5, 0, h, C.grayL, C.gold, 0.7);
        var dd = '';
        for (var z = 3; z < h; z += 2.6) dd += seg(x, sy(gf + 0.5, z), x + 4, sy(gf + 0.5, z));
        s += E.line(dd, C.gray, 0.4, ' stroke-opacity="0.6"');
      });
      s += E.roofEW(ctx, { x0: x0, x1: x1, gb: gb, gf: gf, h: h, rh: 12, type: 'hard', t: t, ridge: v.ridge, os: 2 });
      // 墀头：檐下两端挑出的砖雕
      [x0 - 3, x1 - 3].forEach(function (x) {
        var y = sy(gf + 4, h) + 0.5;
        s += E.path('M' + f(x) + ' ' + f(y) + 'h6v2.4h-1v2.6h-4v-2.6h-1Z', C.stone, C.gold, 0.6) + E.circle(x + 3, y + 3.4, 0.8, C.teal);
      });
      return s;
    }
  });

  // 竹篾编壁的纹理：横篾密、竖篾疏
  function weave(x0, x1, g, z0, z1) {
    var y0 = sy(g, z1), y1 = sy(g, z0);
    return E.clipRaw(x0, y0, x1 - x0, y1 - y0, E.rowsH(x0, x1, y0, y1, 2, T.bamboo.dark, 0.5, 0.55) +
      E.rowsV(x0, x1, y0, y1, 4.2, T.bamboo.dark, 0.6, 0.35));
  }
  // 拱形轮廓：x..x+w，底边 yb，总高 hh（屏幕像素）
  function archD(x, yb, w, hh) {
    var r = w / 2;
    return 'M' + f(x) + ' ' + f(yb) + 'V' + f(yb - hh + r) + 'A' + f(r) + ' ' + f(r) + ' 0 0 1 ' + f(x + w) + ' ' + f(yb - hh + r) + 'V' + f(yb) + 'Z';
  }

  // 9. 竹楼：傣家干栏式，竹柱架空，竹篾编壁，陡峭的大歇山顶几乎罩住整栋楼，前面一架木梯
  HOUSES.push({
    kind: 'zhulou', name: '竹楼', fp: [1, 1], roof: 'hip_tile', tags: ['stilts', 'bamboo', 'tropical'],
    note: '干栏式竹楼，陡坡歇山顶（茅草 / 灰瓦），RoofId 取 hip_tile；楼下架空，木梯上楼',
    variants: [{ w: 1, t: 'thatch' }, { w: 2, t: 'gray', fp: [2, 1] }],
    draw: function (ctx, v) {
      var W = v.w * 48, t = T[v.t], s = '', x0 = 6, x1 = W - 6, gf = -12, gb = -40, fz = 13, h = 27, n = v.w + 1, bw = (x1 - x0) / n, k;
      s += E.shadow(x0, x1, gb, gf, h + 18, 6);
      // 楼下暗处 + 竹柱
      s += E.rect(x0, sy(gf, fz), x1 - x0, fz * K, C.navy, null).replace('/>', ' fill-opacity="0.35"/>');
      for (k = 0; k <= n; k++) s += E.rect(x0 + k * bw - 1.1, sy(gf + 2, fz), 2.2, fz * K, T.bamboo.fill, C.umber, 0.4) +
        E.line('M' + f(x0 + k * bw - 1.1) + ' ' + f(sy(gf + 2, fz * 0.5)) + 'h2.2', C.umber, 0.5);
      // 楼面梁 + 竹篾壁
      s += E.face(x0, x1, gf, fz + 1, h, T.bamboo.lite) + weave(x0, x1, gf, fz + 1, h);
      s += E.face(x0 - 2, x1 + 2, gf + 2, fz - 1, fz + 1.4, C.umber, C.gold, 0.5);
      var dx = x0 + bw * Math.floor(n / 2) + (bw - 9) / 2;
      s += E.door(dx, gf, fz + 1.4, 9, 11, 'plank');
      for (k = 0; k < n; k++) if (k !== Math.floor(n / 2)) s += E.win(x0 + k * bw + bw / 2 - 3, gf, fz + 5, 6, 5, 'lattice');
      // 木梯：从地面斜到门口
      var ly0 = -1, ly1 = sy(gf + 2, fz), lx = dx + 1.5, dl = '';
      dl += 'M' + f(lx - 2) + ' ' + f(ly0) + 'L' + f(lx) + ' ' + f(ly1) + 'M' + f(lx + 8) + ' ' + f(ly0) + 'L' + f(lx + 6) + ' ' + f(ly1);
      for (var q = 1; q < 5; q++) { var yy = ly0 + (ly1 - ly0) * q / 5, dx2 = 2 * (1 - q / 5); dl += 'M' + f(lx - dx2) + ' ' + f(yy) + 'H' + f(lx + 6 + dx2); }
      s += E.line(dl, C.gold, 2.2) + E.line(dl, C.umber, 1.2);
      s += E.roofEW(ctx, { x0: x0, x1: x1, gb: gb, gf: gf, h: h, rh: 24, type: 'xie', t: t, ov: 7, os: 7, lift: v.t === 'thatch' ? 1.5 : 4,
        ridge: v.t === 'thatch' ? 'plain' : 'horn', dots: v.t !== 'thatch', step: v.t === 'thatch' ? 2.2 : 3.4 });
      if (v.w > 1) s += E.bamboo(ctx, W - 4, -2, 34, 3);
      return s;
    }
  });

  // 10. 窑洞式靠山屋：背靠黄土崖，崖面掏出拱形窑洞，窑脸砖砌，上半格子窗糊纸，崖顶女儿墙 + 烟囱
  HOUSES.push({
    kind: 'yaodong', name: '窑洞', fp: [2, 1], roof: 'flat_mud', tags: ['cave', 'loess', 'hillside'],
    note: '靠崖窑：背后黄土崖，拱形窑脸，崖顶即屋顶（flat_mud）；变体 1 挂辣椒串和碾盘，变体 2 两孔窑带土院墙和枣树',
    variants: [{ n: 3, chili: true }, { n: 2, yard: true }],
    draw: function (ctx, v) {
      var s = '', gC = -30, zC = 30, yTop = sy(gC, zC), yBack = sy(-50, zC), r = ctx.r;
      // 崖顶台地
      E.track(yBack - 6);
      var ed = 'M0 ' + f(yTop), dd = '';
      for (var x = 0; x <= 96; x += 8) ed += 'L' + f(x) + ' ' + f(yTop - 1 - r() * 2.5);
      s += E.path(E.poly([[0, yBack], [96, yBack], [96, yTop], [0, yTop]]), E.mix(C.earthL, C.grass, 0.4), C.gold, 0.7);
      for (var i = 0; i < 9; i++) { var gx = 4 + r() * 88, gy = yBack + 3 + r() * (yTop - yBack - 6); dd += 'M' + f(gx) + ' ' + f(gy) + 'l1 -2.6M' + f(gx + 2) + ' ' + f(gy) + 'l-0.4 -3M' + f(gx + 3.6) + ' ' + f(gy) + 'l-1.2 -2.2'; }
      s += E.line(dd, C.leaf, 0.8);
      // 崖面
      s += E.face(0, 96, gC, 0, zC, C.earth);
      var cr = '';
      for (var z = 4; z < zC - 1; z += 3.6) cr += 'M' + f(r() * 6) + ' ' + f(sy(gC, z)) + 'H' + f(96 - r() * 6);
      s += E.line(cr, C.umber, 0.5, ' stroke-opacity="0.3"');
      // 崖顶女儿墙 + 烟囱
      s += E.face(2, 94, gC + 0.5, zC, zC + 3, C.earthL, C.gold, 0.6) + E.face(1, 95, gC + 0.5, zC + 3, zC + 4.2, T.gray.fill, T.gray.line, 0.5);
      var chx = v.n === 3 ? 74 : 60;
      s += E.face(chx, chx + 5, -40, zC, zC + 10, C.earthL, C.gold, 0.6) + E.rect(chx - 0.6, sy(-40, zC + 10) - 1.2, 6.2, 1.6, C.umber);
      // 前院地面
      s += E.rect(0, gC, 96, -1 - gC, E.mix(C.earthL, C.cream, 0.3), null);
      // 窑洞：窑脸（砖拱）→ 内部窗与门
      var aw = 22, gap = (96 - v.n * aw) / (v.n + 1);
      for (var k = 0; k < v.n; k++) {
        var ax = gap + k * (aw + gap), yb = gC, hh = 24 * K + aw / 2 * 0.5;
        s += E.path(archD(ax - 2.5, yb, aw + 5, hh + 2.5), C.stone, C.gold, 0.8);
        var inD = archD(ax, yb, aw, hh), mid = yb - hh * 0.5;
        var inner = E.rect(ax, yb - hh - 2, aw, hh + 2, C.creamL) +
          E.rowsV(ax, ax + aw, yb - hh - 2, mid, 2.8, C.umber, 0.6, 0.8) + E.rowsH(ax, ax + aw, yb - hh - 2, mid, 2.8, C.umber, 0.6, 0.8) +
          E.rect(ax, mid, aw, yb - mid, C.umberL) + E.rect(ax + aw / 2 - 4, mid, 8, yb - mid, C.vermil, C.gold2, 0.5) +
          E.line('M' + f(ax + aw / 2) + ' ' + f(mid) + 'V' + f(yb), C.umber, 0.6) +
          E.rect(ax + 2, mid + 2.5, 5, 4, C.creamL, C.umber, 0.5) + E.rect(ax + aw - 7, mid + 2.5, 5, 4, C.creamL, C.umber, 0.5) +
          E.line('M' + f(ax) + ' ' + f(mid) + 'H' + f(ax + aw), C.umber, 1.2);
        s += E.clip(ctx, inD, inner) + E.path(inD, 'none', C.umber, 1);
        s += E.circle(ax + aw / 2, yb - hh * 0.72, 2.2, C.vermil, C.gold2, 0.5); // 窗花
        if (v.chili) { // 辣椒串、玉米串
          var cx0 = ax + aw + gap / 2, ds = '';
          for (var c = 0; c < 6; c++) ds += E.circle(cx0 + (c % 2 ? 0.8 : -0.8), yb - hh * 0.8 + c * 2.2, 1.2, k % 2 ? C.ochre : C.vermil);
          if (k < v.n - 1) s += E.line('M' + f(cx0) + ' ' + f(yb - hh * 0.85) + 'v14', C.umber, 0.5) + ds;
        }
      }
      if (v.chili) s += E.circle(14, -9, 6.5, C.stone, C.gold, 0.8) + E.circle(14, -9, 2.4, C.stoneL, C.gold, 0.5) + E.rect(13, -16, 2, 5, C.umber); // 碾盘
      if (v.yard) {
        s += E.tree(ctx, 86, -10, 18, 8);
        s += E.face(0, 30, -2, 0, 9, C.earthL, C.gold, 0.7) + E.face(66, 96, -2, 0, 9, C.earthL, C.gold, 0.7) +
          E.face(-0.5, 30.5, -2, 9, 10.5, T.gray.fill, T.gray.line, 0.5) + E.face(65.5, 96.5, -2, 9, 10.5, T.gray.fill, T.gray.line, 0.5);
      }
      return s;
    }
  });

  // 11. 碉楼：窄高的多层防御楼，墙基石砌，每层小窗带铁栅，顶层挑出一圈燕子窝挑台，攒尖顶
  HOUSES.push({
    kind: 'diaolou', name: '碉楼', fp: [1, 1], roof: 'hip_tile', tags: ['tower', 'fortified', 'multi_storey'],
    note: '四层碉楼，顶层挑台（燕子窝）+ 四角攒尖顶（RoofId 取 hip_tile）；变体 2 为毛石碉楼、灰瓦',
    variants: [{ t: 'teal', wall: 'cream' }, { t: 'gray', wall: 'stone' }],
    draw: function (ctx, v) {
      var t = T[v.t], s = '', x0 = 13, x1 = 35, gf = -13, gb = -35, h = 74, k;
      var wall = v.wall === 'stone' ? E.mix(C.stone, C.earth, 0.3) : C.creamL;
      s += E.shadow(x0, x1, gb, gf, 40, 7);
      s += E.face(x0, x1, gf, 0, h, wall);
      s += E.rect(x1 - 4, sy(gf, h), 4, h * K, C.navy, null).replace('/>', ' fill-opacity="0.13"/>'); // 右侧背光
      s += E.face(x0 - 1, x1 + 1, gf + 0.5, 0, 9, C.stone, C.gold, 0.8);
      var dd = '';
      if (v.wall === 'stone') for (var z = 12; z < h; z += 4) for (var xx = x0 + ((z / 4) % 2) * 3; xx < x1 - 2; xx += 6) dd += 'M' + f(xx) + ' ' + f(sy(gf, z)) + 'h' + f(4 + ctx.r() * 1.5);
      else for (var z2 = 26; z2 < h; z2 += 18) dd += 'M' + f(x0) + ' ' + f(sy(gf, z2)) + 'H' + f(x1);
      s += E.line(dd, v.wall === 'stone' ? C.gray : C.gold, 0.6, ' stroke-opacity="0.6"');
      s += E.door(x0 + 7, gf, 0, 8, 13, 'arch');
      [30, 48, 64].forEach(function (z) {
        [x0 + 4, x1 - 8].forEach(function (wx) {
          s += E.win(wx, gf, z, 4, 6, 'slit') + E.line('M' + f(wx + 1.3) + ' ' + f(sy(gf, z + 6)) + 'V' + f(sy(gf, z)) + 'M' + f(wx + 2.7) + ' ' + f(sy(gf, z + 6)) + 'V' + f(sy(gf, z)), C.gray, 0.5);
        });
      });
      s += E.circle((x0 + x1) / 2, sy(gf, 40), 1.6, C.navy, C.gold, 0.4) + E.circle((x0 + x1) / 2, sy(gf, 56), 1.6, C.navy, C.gold, 0.4); // 枪眼
      // 挑台：一排托拱 + 挑出的台面 + 栏杆
      var zb = h, cx0 = x0 - 4, cx1 = x1 + 4;
      for (k = 0; k < 6; k++) {
        var px = x0 + 1 + k * (x1 - x0 - 2) / 5;
        s += E.path('M' + f(px - 1.6) + ' ' + f(sy(gf, zb)) + 'L' + f(px + 1.6) + ' ' + f(sy(gf, zb)) + 'L' + f(px) + ' ' + f(sy(gf, zb - 6)) + 'Z', C.stone, C.gold, 0.5);
      }
      s += E.rect(cx0, sy(gf + 4, zb + 1.5), cx1 - cx0, sy(gf - 26, zb + 1.5) - sy(gf + 4, zb + 1.5) + 0, C.stoneL, C.gold, 0.6).replace(/d="[^"]*"/, function () {
        return 'd="' + E.poly([[cx0, sy(gb - 4, zb + 1.5)], [cx1, sy(gb - 4, zb + 1.5)], [cx1, sy(gf + 4, zb + 1.5)], [cx0, sy(gf + 4, zb + 1.5)]]) + '"';
      });
      s += E.face(cx0, cx1, gf + 4, zb - 1, zb + 1.5, C.stone, C.gold, 0.6);
      // 顶层：退进的小屋 + 圆窗
      s += E.face(x0 + 1, x1 - 1, gf - 2, zb + 1.5, zb + 14, wall);
      s += E.win(x0 + 4, gf - 2, zb + 4, 5, 5, 'round') + E.win(x1 - 9, gf - 2, zb + 4, 5, 5, 'round');
      s += H.railing(cx0 + 1, cx1 - 1, gf + 4, zb + 1.5, zb + 5.5, C.vermil, 2.6);
      s += E.roofPyr(ctx, { x0: x0 + 1, x1: x1 - 1, gb: gb + 2, gf: gf - 2, h: zb + 14, rh: 14, t: t, ov: 5, lift: 4 });
      return s;
    }
  });

  return { HOUSES: HOUSES, banner: banner, fence: fence, haystack: haystack, weave: weave, archD: archD };
});
