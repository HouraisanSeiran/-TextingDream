/*
 * 织梦 · 东方民居（一）：共用部件 + 四合院、徽派马头墙民居、吊脚楼
 * 局部坐标见 east-core.js：原点 = 占地左前角，x 向右，g 向南（占地 g∈[-d*48, 0]），z 向上，屏幕 y = g - z*K。
 * 画的顺序就是遮挡顺序：同一个 symbol 里先画靠北的、再画靠南的。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./east-core.js'));
  else root.TownArtEast_housesA = factory(root.TownArtEast_core);
})(this, function (E) {
  'use strict';
  var C = E.C, T = E.TILE, f = E.f, sy = E.sy, K = E.K;

  // 一栋单体：投影 → 台基 → 正立面 → 立面装饰 → 屋顶
  function hall(ctx, o) {
    var s = '', ph = o.ph == null ? 3 : o.ph;
    if (o.shadow !== false) s += E.shadow(o.x0, o.x1, o.gb, o.gf, o.h + (o.rh || 0));
    if (ph) s += E.plinth(o.x0 - 1.5, o.x1 + 1.5, o.gf + 1.5, ph);
    s += E.face(o.x0, o.x1, o.gf, ph, o.h, o.wall || C.cream);
    if (o.band) s += E.face(o.x0, o.x1, o.gf, ph, ph + o.band, o.bandC || C.stone, C.gold, 0.7);
    if (o.deco) s += o.deco(ph);
    if (o.roof === 'ns') s += E.roofNS(ctx, o);
    else if (o.roof === 'pyr') s += E.roofPyr(ctx, o);
    else if (o.roof !== 'none') s += E.roofEW(ctx, o);
    return s;
  }

  // 开间：n 间，柱子、门、窗、檐下青绿彩画额枋
  function bays(x0, x1, g, ph, h, n, o) {
    o = o || {};
    var s = '', bw = (x1 - x0) / n, mid = Math.floor(n / 2), doors = o.doors || [mid];
    for (var i = 0; i < n; i++) {
      var bx = x0 + i * bw, pad = bw * (o.pad || 0.16);
      if (doors.indexOf(i) >= 0) s += E.door(bx + pad, g, ph, bw - pad * 2, Math.min(h - ph - 3, o.dh || 14), o.door || 'double');
      else if (o.win !== 'none') {
        var sill = o.sill || 4;
        s += E.win(bx + pad, g, ph + sill, bw - pad * 2, Math.min(h - ph - sill - 4, o.wh || 8), o.win || 'lattice');
      }
    }
    if (o.cols !== false) for (var k = 0; k <= n; k++) s += E.col(x0 + k * bw, g, ph, h, o.colC);
    if (o.beam !== false) s += E.face(x0 - 1, x1 + 1, g, h - 2.6, h, o.beamC || C.teal, C.gold2, 0.6);
    return s;
  }

  // 地面铺装：方砖（院子）/ 夯土（农家院）。地面 z=0，所以屏幕 y 就是 g
  function paving(x0, x1, g0, g1, step, fill, ln) {
    var s = E.rect(x0, g0, x1 - x0, g1 - g0, fill || C.stoneL, C.gold, 0.7), d = '';
    if (step) {
      for (var x = x0 + step; x < x1 - 0.5; x += step) d += 'M' + f(x) + ' ' + f(g0) + 'V' + f(g1);
      for (var y = g0 + step; y < g1 - 0.5; y += step) d += 'M' + f(x0) + ' ' + f(y) + 'H' + f(x1);
      s += E.line(d, ln || C.grayL, 0.5, ' stroke-opacity="0.45"');
    }
    return s;
  }

  // 院墙：一段东西向矮墙（正面 + 墙顶瓦帽）
  function lowWall(ctx, x0, x1, g, h, t, wall) {
    return E.shadow(x0, x1, g - 3, g, h, 3) + E.face(x0, x1, g, 0, h, wall || C.cream) +
      E.roofEW(ctx, { x0: x0, x1: x1, gb: g - 3, gf: g, h: h, rh: 2.5, type: 'hard', t: t || T.gray, ov: 1.2, os: 0.6, lift: 0, dots: false, ridgeW: 1.6, step: 3 });
  }
  // 南北向院墙：只露墙顶一条（墙帽）和南端头
  function sideWall(x0, x1, gb, gf, h, t, wall) {
    var yT0 = sy(gb, h), yT1 = sy(gf, h), s = '';
    E.track(yT0 - 3);
    s += E.rect(x0, yT0, x1 - x0, gf - yT0, wall || C.cream, C.gold, 0.8);
    s += E.rect(x0 - 1, sy(gb, h + 2), x1 - x0 + 2, yT1 - yT0 + 2 * K, (t || T.gray).fill, (t || T.gray).line, 0.7);
    return s;
  }

  /**
   * 马头墙（徽派封火山墙）：x0..x1 一道南北向山墙，从屋脊处向南北两头各跌落 n 阶。
   * 背面往前一段一段画，前面的墙段自然压住后面墙段的下半截；前半坡每阶前端起"马头"。
   */
  function mtq(x0, x1, gb, gf, zLo, zHi, n, wall, t) {
    var s = '', m = 2 * n - 1, L = (gf - gb) / m;
    for (var j = 0; j < m; j++) {
      var lvl = n - 1 - Math.abs(j - (n - 1)), z = n > 1 ? zLo + (zHi - zLo) * lvl / (n - 1) : zHi;
      var gs = gb + j * L, ge = gs + L, yT0 = sy(gs, z), yT1 = sy(ge, z);
      E.track(yT0 - 8);
      s += E.rect(x0, yT0, x1 - x0, ge - yT0, wall, C.gold, 0.8);
      s += E.line('M' + f(x0) + ' ' + f(yT1) + 'H' + f(x1), C.gold, 0.6, ' stroke-opacity="0.7"');
      var zc = z + 2.6, yc0 = sy(gs - 0.6, zc), yc1 = sy(ge + 0.6, zc), cx0 = x0 - 1.8, cx1 = x1 + 1.8;
      s += E.rect(cx0, yc0, cx1 - cx0, yc1 - yc0 + 2.6 * K, t.fill, t.line, 0.7);
      s += E.line('M' + f(cx0 + 0.6) + ' ' + f(yc1) + 'H' + f(cx1 - 0.6), t.lite, 0.6);
      if (j >= n - 1) { // 马头：前端翘起的一块"座头"
        var hy = yc1;
        s += E.path('M' + f(cx0 - 0.6) + ' ' + f(hy + 1) + 'L' + f(cx1 + 0.6) + ' ' + f(hy + 1) + 'L' + f(cx1 + 1.4) + ' ' + f(hy - 3.4) +
          'Q' + f((cx0 + cx1) / 2) + ' ' + f(hy - 1.6) + ' ' + f(cx0 - 1.4) + ' ' + f(hy - 3.4) + 'Z', t.dark, t.line, 0.7);
      }
    }
    return s;
  }

  // 栏杆：沿 x0..x1 在 g 处高 z0..z1 的一排望柱 + 扶手
  function railing(x0, x1, g, z0, z1, c, step) {
    var d = '', yT = sy(g, z1), yB = sy(g, z0);
    for (var x = x0; x <= x1 + 0.01; x += step || 3) d += 'M' + f(x) + ' ' + f(yB) + 'V' + f(yT);
    return E.line(d, c || C.vermil, 0.8) + E.line('M' + f(x0 - 0.5) + ' ' + f(yT) + 'H' + f(x1 + 0.5), C.gold2, 1.6) +
      E.line('M' + f(x0 - 0.5) + ' ' + f(yT) + 'H' + f(x1 + 0.5), c || C.vermil, 0.9);
  }

  // 木板墙的竖缝
  function planks(x0, x1, g, z0, z1, step, c) {
    var d = '';
    for (var x = x0 + step; x < x1 - 0.5; x += step) d += 'M' + f(x) + ' ' + f(sy(g, z1)) + 'V' + f(sy(g, z0));
    return d ? E.line(d, c || C.umber, 0.6, ' stroke-opacity="0.55"') : '';
  }

  var H = { hall: hall, bays: bays, paving: paving, lowWall: lowWall, sideWall: sideWall, mtq: mtq, railing: railing, planks: planks };
  var HOUSES = [];

  // 单坡披檐（腰檐、门罩）：上沿贴在墙面 g 处 z+4，下沿出挑 ov 到 z
  function shed(ctx, x0, x1, g, z, t, ov, lift) {
    ov = ov == null ? 4 : ov; lift = lift == null ? 1.5 : lift;
    var top = sy(g, z + 4), F = E.eavePts(x0 - 2, x1 + 2, sy(g + ov, z), lift, 16);
    E.track(top - 1);
    var d = E.poly([[x0 - 0.5, top], [x1 + 0.5, top]].concat(F.slice().reverse()));
    return E.path(d, t.fill) + E.clip(ctx, d, E.rowsV(x0 - 3, x1 + 3, top - 1, F[0][1] + 1, 3, t.dark)) + E.path(d, 'none', t.line, 0.9) +
      E.line(E.poly(F, true), t.dark, 1.8) + E.line(E.poly(F, true), t.line, 0.7);
  }
  H.shed = shed;

  // 1. 四合院 2×2：正房 + 东西厢房 + 院墙，东南角宅门，东厢南山墙做座山影壁
  HOUSES.push({
    kind: 'siheyuan', name: '四合院', fp: [2, 2], roof: 'gable_tile', tags: ['courtyard', 'screen_wall', 'enclosed'],
    note: '北方合院：正房与厢房硬山顶，东南角开宅门，进门正对东厢南山墙上的座山影壁',
    variants: [{ t: 'gray', ridge: 'curl' }, { t: 'navy', ridge: 'curl', tree: true }],
    draw: function (ctx, v) {
      var t = T[v.t], s = '';
      s += paving(8, 88, -72, -5, 8, C.stoneL);
      s += hall(ctx, { x0: 14, x1: 82, gb: -94, gf: -72, h: 24, rh: 13, type: 'hard', t: t, ridge: v.ridge, ph: 4,
        deco: function (ph) { return bays(14, 82, -72, ph, 24, 5, { doors: [2], dh: 15, wh: 9 }); } });
      s += sideWall(5, 9, -40, -5, 12, t) + sideWall(87, 91, -40, -5, 12, t);
      [[6, 26], [70, 90]].forEach(function (q, i) {
        s += hall(ctx, { x0: q[0], x1: q[1], gb: -68, gf: -26, h: 18, rh: 9, roof: 'ns', gable: 'wall', t: t, ph: 2,
          deco: function (ph) {
            if (i === 0) return E.win(q[0] + 6, -26, ph + 5, 8, 7, 'round');
            // 座山影壁：方框 + 中心花 + 四角岔角
            var cx = (q[0] + q[1]) / 2, cy = sy(-26, 10);
            return E.rect(q[0] + 3, sy(-26, 16), 14, 12 * K, C.stone, C.gold, 0.8) +
              E.path('M' + f(cx) + ' ' + f(cy - 3.6) + 'L' + f(cx + 3.6) + ' ' + f(cy) + 'L' + f(cx) + ' ' + f(cy + 3.6) + 'L' + f(cx - 3.6) + ' ' + f(cy) + 'Z', C.tealL, C.gold, 0.7) +
              E.circle(cx, cy, 1.1, C.vermil);
          } });
      });
      if (v.tree) s += E.tree(ctx, 40, -40, 20, 9);
      else s += E.rect(44, -46, 8, 6, C.stone, C.gold, 0.6) + E.circle(48, -45, 2.2, C.water, C.gold, 0.5); // 院中鱼缸
      s += lowWall(ctx, 5, 91, -4, 13, t);
      // 宅门：小门楼，硬山，朱门 + 门簪 + 抱鼓石
      s += hall(ctx, { x0: 68, x1: 86, gb: -10, gf: -2, h: 19, rh: 7, type: 'hard', t: t, ph: 2, ov: 3, os: 2, ridge: 'curl',
        deco: function (ph) {
          return E.door(72, -2, ph, 10, 13, 'double') + E.circle(75, sy(-2, 16.2), 0.8, C.gold2) + E.circle(79, sy(-2, 16.2), 0.8, C.gold2) +
            E.circle(70.6, sy(-2, ph + 2), 1.6, C.stone, C.gold, 0.5) + E.circle(83.4, sy(-2, ph + 2), 1.6, C.stone, C.gold, 0.5) +
            E.face(68, 86, -2, 16.5, 19, C.teal, C.gold2, 0.5);
        } });
      return s;
    }
  });

  // 2. 三合院 2×1：南方三合院，正身 + 两护龙，前面一片晒谷禾埕，燕尾脊
  HOUSES.push({
    kind: 'sanheyuan', name: '三合院', fp: [2, 1], roof: 'gable_tile', tags: ['courtyard', 'open_front', 'swallowtail_ridge'],
    note: '一正两厢、前面敞开；正身悬山，屋脊两端燕尾起翘；厢房山面朝南',
    variants: [{ t: 'gray', wall: 'brick' }, { t: 'teal', wall: 'cream', fence: true }],
    draw: function (ctx, v) {
      var t = T[v.t], s = '', wall = v.wall === 'brick' ? E.mix(C.vermilL, C.cream, 0.25) : C.cream;
      s += paving(22, 74, -32, -3, 0, C.earthL);
      for (var i = 0; i < 3; i++) s += E.rect(30 + i * 13, -20 + (i % 2) * 4, 10, 6, C.ochreL, C.gold, 0.5) + E.rowsH(30 + i * 13, 40 + i * 13, -20 + (i % 2) * 4, -14 + (i % 2) * 4, 1.6, C.ochre, 0.5, 0.8);
      s += hall(ctx, { x0: 24, x1: 72, gb: -46, gf: -32, h: 19, rh: 10, type: 'hang', t: t, wall: wall, ridge: 'horn', ph: 3,
        deco: function (ph) { return bays(24, 72, -32, ph, 19, 3, { doors: [1], dh: 12, wh: 7 }); } });
      [[3, 22], [74, 93]].forEach(function (q) {
        s += hall(ctx, { x0: q[0], x1: q[1], gb: -42, gf: -8, h: 15, rh: 8, roof: 'ns', gable: 'wall', wall: wall, t: t, ph: 2,
          deco: function (ph) { return E.door(q[0] + 6, -8, ph, 7, 10, 'plank') + E.win(q[0] + 14, -8, ph + 5, 3, 4, 'slit'); } });
      });
      if (v.fence) {
        var d = '';
        for (var x = 23; x < 74; x += 3) d += 'M' + f(x) + ' ' + f(-2) + 'V' + f(-8);
        s += E.line(d, C.umber, 0.9) + E.line('M22 -6.5H74M22 -4H74', C.umberL, 0.8);
      }
      return s;
    }
  });

  // 3. 徽派民居：白墙黛瓦，两山马头墙层层跌落，高窗小、门上砖雕门罩
  HOUSES.push({
    kind: 'huipai', name: '徽派马头墙民居', fp: [2, 1], roof: 'gable_tile', tags: ['two_storey', 'firewall', 'white_wall'],
    note: '硬山顶被两侧三阶马头墙夹住；正面白墙高窗、门罩披檐；1×1 小变体为两阶',
    variants: [{ w: 2, n: 3 }, { w: 1, n: 2 }, { w: 2, n: 3, flip: true }],
    draw: function (ctx, v) {
      var W = v.w * 48, t = T.gray, s = '', x0 = 6, x1 = W - 6, h = v.w > 1 ? 34 : 31, gf = -8, gb = -42;
      s += hall(ctx, { x0: x0, x1: x1, gb: gb, gf: gf, h: h, rh: 10, type: 'hard', t: t, wall: C.creamL, ph: 2, band: 3, ov: 3, os: 0,
        deco: function (ph) {
          var o = '', dx = v.flip ? x1 - 22 : (x0 + x1) / 2 - 6, dw = 12;
          // 雨水在白墙上留下的淡灰水迹
          var dd = '';
          for (var k = 0; k < 7; k++) { var xx = x0 + 4 + ctx.r() * (x1 - x0 - 8); dd += 'M' + f(xx) + ' ' + f(sy(gf, h - 1)) + 'v' + f(4 + ctx.r() * 7); }
          o += E.line(dd, C.grayL, 0.8, ' stroke-opacity="0.35"');
          o += E.rect(dx - 1.5, sy(gf, 20), dw + 3, (20 - ph) * K, C.stone, C.gold, 0.7) + E.door(dx, gf, ph, dw, 16, 'plank');
          o += shed(ctx, dx - 2, dx + dw + 2, gf, 21, t, 3, 1.5);
          var wx = v.w > 1 ? [x0 + 8, x1 - 15] : [x0 + 4];
          if (v.flip) wx = [x0 + 8, x0 + 26];
          wx.forEach(function (x) { o += E.win(x, gf, 22, 7, 6, 'lattice'); });
          if (v.w > 1) o += E.win(v.flip ? x0 + 14 : x0 + 12, gf, 9, 4, 6, 'slit');
          return o;
        } });
      var zLo = h + 1, zHi = h + 12;
      s += mtq(x0 - 3, x0 + 2, gb - 2, gf + 2, zLo, zHi, v.n, C.creamL, t) + mtq(x1 - 2, x1 + 3, gb - 2, gf + 2, zLo, zHi, v.n, C.creamL, t);
      return s;
    }
  });

  // 4. 吊脚楼 1×2 / 2×2：后半坐在石砌台地上，前半由木柱架空，二层挑出美人靠回廊，歇山顶檐角高翘
  HOUSES.push({
    kind: 'diaojiaolou', name: '吊脚楼', fp: [1, 2], roof: 'hip_tile', tags: ['stilts', 'hillside', 'balcony'],
    note: '实际为小青瓦歇山顶（RoofId 无歇山，取 hip_tile）；前檐木柱落在坡下，柱脚垫石',
    variants: [{ w: 1, t: 'gray' }, { w: 2, t: 'navy', bays: 3 }],
    draw: function (ctx, v) {
      // 1×2 单开间：楼身只进深 24、矮一些，屋顶整体压低（上伸约 80 px），后半露出台地；两开间保持原样
      var one = v.w === 1;
      var W = v.w * 48, t = T[v.t], s = '', x0 = 5, x1 = W - 5, fz = one ? 13 : 14, h = one ? 28 : 36, gf = one ? -22 : -20, gb = one ? -46 : -70, bal = -11;
      s += E.shadow(x0, x1, gb, bal, 30, 6);
      // 台地：顶面夯土 + 前沿毛石挡土墙
      s += E.rect(1, sy(-94, fz), W - 2, sy(-44, fz) - sy(-94, fz), C.earthL, C.gold, 0.7);
      s += E.face(1, W - 1, -44, 0, fz, C.stone, C.gold, 0.8);
      var dd = '';
      for (var r0 = 0; r0 < 3; r0++) for (var c0 = 0; c0 < v.w * 5; c0++) {
        var xx = 1 + (c0 + (r0 % 2) * 0.5) * 9.4, yy = sy(-44, 3 + r0 * 4);
        if (xx + 7 < W) dd += 'M' + f(xx) + ' ' + f(yy) + 'h' + f(7 + ctx.r() * 1.5);
      }
      s += E.line(dd, C.grayL, 0.7, ' stroke-opacity="0.7"');
      // 坡下地面
      s += E.rect(1, -44, W - 2, 43, E.mix(C.earthL, C.grass, 0.5), null);
      // 架空层：后排柱、楼面下的暗处
      var nb = v.bays || 2, bw = (x1 - x0) / nb, k;
      s += E.rect(x0, sy(gf, fz), x1 - x0, fz * K, E.mix(C.navy, C.umber, 0.5), null);
      for (k = 0; k <= nb; k++) s += E.rect(x0 + k * bw - 1, sy(gf, fz), 2, fz * K, C.umber);
      // 二层主体：木板壁，中间一樘格扇门，两侧花窗
      s += E.face(x0, x1, gf, fz, h, C.umberL);
      s += H.planks(x0, x1, gf, fz, h, 3.2);
      for (k = 0; k < nb; k++) {
        var bx = x0 + k * bw;
        if (k === Math.floor(nb / 2)) s += E.door(bx + 3, gf, fz + 1.5, bw - 6, one ? 11.5 : 15, 'double');
        else s += E.win(bx + 3, gf, fz + 6, bw - 6, one ? 7 : 9, 'hex');
      }
      for (k = 0; k <= nb; k++) s += E.col(x0 + k * bw, gf, fz, h, C.umber);
      s += E.face(x0 - 1, x1 + 1, gf, h - 2.4, h, C.vermil, C.gold2, 0.5);
      // 挑廊：楼面板 + 前排吊脚柱（柱脚垫石）+ 美人靠
      s += E.rect(x0 - 2, sy(bal, fz + 1.6), x1 - x0 + 4, sy(gf, fz + 1.6) - sy(bal, fz + 1.6), C.umberL, C.gold, 0.6);
      s += E.rowsV(x0 - 2, x1 + 2, sy(gf, fz + 1.6), sy(bal, fz + 1.6), 3, C.umber, 0.5, 0.5);
      s += E.face(x0 - 2, x1 + 2, bal, fz - 0.6, fz + 1.6, C.umber, C.gold, 0.5);
      for (k = 0; k <= nb; k++) {
        var px = x0 + k * bw;
        s += E.rect(px - 1.3, sy(bal, fz), 2.6, fz * K, C.umber, C.gold2, 0.4) + E.rect(px - 2.2, bal - 1.6, 4.4, 1.6, C.stone, C.gold, 0.4);
      }
      // 美人靠：向外弯出的靠背
      var yb = sy(bal, fz + 1.6), yt = sy(bal + 1.5, fz + 8), dk = '';
      for (var x = x0; x <= x1 + 0.1; x += 2.6) dk += 'M' + f(x) + ' ' + f(yb) + 'Q' + f(x) + ' ' + f(yt + 2) + ' ' + f(x) + ' ' + f(yt);
      s += E.line(dk, C.vermil, 0.8) + E.line('M' + f(x0 - 1) + ' ' + f(yt) + 'H' + f(x1 + 1), C.gold2, 1.8) + E.line('M' + f(x0 - 1) + ' ' + f(yt) + 'H' + f(x1 + 1), C.vermil, 1);
      if (v.w > 1) s += E.lantern(x0 + bw, sy(bal, 30), 2.2) + E.lantern(x0 + bw * 2, sy(bal, 30), 2.2);
      else s += E.lantern((x0 + x1) / 2, sy(bal, 23), 2.2);
      // 窄而深的单开间吊脚楼：屋脊南北向、悬山山面朝南（博风板 + 悬鱼）；两开间的才用歇山
      if (v.w > 1) s += E.roofEW(ctx, { x0: x0, x1: x1, gb: gb, gf: gf, h: h, rh: 15, type: 'xie', t: t, ov: 9, os: 4, lift: 7, ridge: 'horn' });
      else s += E.roofNS(ctx, { x0: x0, x1: x1, gb: gb, gf: gf, h: h, rh: 8, t: t, ov: 5, os: 5, gable: 'board', lift: 2 });
      return s;
    }
  });

  // 土楼的圆 / 方轮廓（地面平面里就是圆和方，斜俯视下不压扁）
  function ring(shape, cx, cy, r) {
    if (shape === 'round') return 'M' + f(cx - r) + ' ' + f(cy) + 'a' + f(r) + ' ' + f(r) + ' 0 1 0 ' + f(2 * r) + ' 0a' + f(r) + ' ' + f(r) + ' 0 1 0 ' + f(-2 * r) + ' 0Z';
    return E.poly([[cx - r, cy - r], [cx + r, cy - r], [cx + r, cy + r], [cx - r, cy + r]]);
  }
  function backArc(shape, cx, cy, r) { // 只取北半边（内圈回廊线）
    if (shape === 'round') return 'M' + f(cx - r) + ' ' + f(cy) + 'A' + f(r) + ' ' + f(r) + ' 0 0 1 ' + f(cx + r) + ' ' + f(cy);
    return 'M' + f(cx - r) + ' ' + f(cy + r) + 'V' + f(cy - r) + 'H' + f(cx + r) + 'V' + f(cy + r);
  }

  // 5. 客家土楼 2×2：圆楼 / 方楼。外墙夯土厚实、底层不开窗、上层一圈小窗；屋顶一圈环形瓦面，中间露出天井和内圈木回廊
  HOUSES.push({
    kind: 'tulou', name: '客家土楼', fp: [2, 2], roof: 'hip_tile', tags: ['earthen', 'fortified', 'courtyard', 'multi_storey'],
    note: '环形（或回字形）双坡瓦顶，RoofId 取 hip_tile；外墙夯土，底层无窗，正门一处',
    variants: [{ shape: 'round', t: 'gray' }, { shape: 'square', t: 'navy' }],
    draw: function (ctx, v) {
      var t = T[v.t], s = '', sh = v.shape, cx = 48, cy = -48, r = 43, h = 34, ov = 4, rm = 36, ri = 24, rh = 6;
      var yT = cy - h * K, yR = cy - (h + rh) * K, yB = cy, sh2 = sh === 'round';
      E.track(yR - rm - 4);
      // 投影
      s += E.path(ring(sh, cx + 5, cy + 2, r), C.shadow, null, 0, ' fill-opacity="0.2"');
      // 外墙：圆楼是一条前半圆柱带，方楼是一面南墙
      var band = sh2 ? 'M' + f(cx - r) + ' ' + f(yT) + 'L' + f(cx - r) + ' ' + f(yB) + 'A' + f(r) + ' ' + f(r) + ' 0 0 0 ' + f(cx + r) + ' ' + f(yB) +
        'L' + f(cx + r) + ' ' + f(yT) + 'A' + f(r) + ' ' + f(r) + ' 0 0 1 ' + f(cx - r) + ' ' + f(yT) + 'Z'
        : E.poly([[cx - r, yT + r], [cx + r, yT + r], [cx + r, yB + r], [cx - r, yB + r]]);
      var foot = 'M' + f(cx - r) + ' ' + f(yB - 5 * K) + (sh2 ? 'A' + f(r) + ' ' + f(r) + ' 0 0 0 ' + f(cx + r) + ' ' + f(yB - 5 * K) : 'L' + f(cx + r) + ' ' + f(yB - 5 * K));
      var inner = E.rect(cx - r - 2, yB + r - 5 * K - (sh2 ? 0 : 0), 2 * r + 4, 12, C.stone) + // 毛石墙基
        E.rect(cx + r * 0.35, yT - 4, r, h * K + r + 8, E.mix(C.earth, C.umber, 0.35), null).replace('/>', ' fill-opacity="0.45"/>') + // 右侧背光
        E.rect(cx - r - 1, yT - 4, r * 0.35, h * K + r + 8, C.earthL, null).replace('/>', ' fill-opacity="0.5"/>');
      if (sh2) inner = inner.replace(E.rect(cx - r - 2, yB + r - 5 * K, 2 * r + 4, 12, C.stone), '') +
        E.path('M' + f(cx - r) + ' ' + f(yB - 5 * K) + 'L' + f(cx - r) + ' ' + f(yB) + 'A' + f(r) + ' ' + f(r) + ' 0 0 0 ' + f(cx + r) + ' ' + f(yB) +
          'L' + f(cx + r) + ' ' + f(yB - 5 * K) + 'A' + f(r) + ' ' + f(r) + ' 0 0 1 ' + f(cx - r) + ' ' + f(yB - 5 * K) + 'Z', C.stone);
      s += E.path(band, C.earth) + E.clip(ctx, band, inner) + E.path(band, 'none', C.gold, 1.1);
      s += E.line(foot, C.gold, 0.6, ' stroke-opacity="0.7"');
      // 上层小窗：圆楼按柱面角度排布（越靠两边越窄），方楼均匀一排
      var wz = [20, 27], wd = '';
      wz.forEach(function (z) {
        for (var i = 0; i < 9; i++) {
          if (sh2) {
            var th = Math.PI * (0.12 + 0.76 * i / 8), sn = Math.sin(th), wx = cx - r * Math.cos(th), wy = cy + r * sn - z * K;
            if (Math.abs(i - 4) < 1) continue;
            wd += E.rect(wx - (0.5 + 1.1 * sn), wy - 3.4, 1 + 2.2 * sn, 3.4, C.navy, C.gold, 0.4);
          } else {
            var sx = cx - r + 8 + i * (2 * r - 16) / 8;
            if (i === 4) continue;
            wd += E.rect(sx - 1.4, sy(cy + r, z) - 3.4, 2.8, 3.4, C.navy, C.gold, 0.4);
          }
        }
      });
      s += wd;
      // 正门：石框拱门 + 门罩披檐 + 门楣匾
      var gy = cy + r;
      s += E.rect(cx - 7, sy(gy, 15), 14, 15 * K, C.stone, C.gold, 0.7) + E.door(cx - 4.5, gy, 0, 9, 12.5, 'arch');
      s += E.rect(cx - 5, sy(gy, 18.6), 10, 2.6, C.navy, C.gold2, 0.5);
      s += H.shed(ctx, cx - 8, cx + 8, gy, 20, t, 3, 2);
      // 屋顶：外坡（落到外檐）→ 内坡（脊到天井）→ 天井
      var outer = ring(sh, cx, yT, r + ov), ridge = ring(sh, cx, yR, rm), hole = ring(sh, cx, yT, ri), rad = '';
      for (var a = 0; a < 72; a++) {
        var an = a / 72 * Math.PI * 2;
        rad += 'M' + f(cx + Math.cos(an) * ri) + ' ' + f(yT + Math.sin(an) * ri) + 'L' + f(cx + Math.cos(an) * (r + ov + 6)) + ' ' + f(yT + Math.sin(an) * (r + ov + 6));
      }
      // 瓦垄：圆楼放射状；方楼按四个坡面分区（南北坡竖垄、东西坡横垄，西坡亮、东坡暗）。做成函数，每次调用生成新的 clip id
      var Ro = r + ov + 6, cyy = (yT + yR) / 2;
      var TL = [cx - Ro, yT - Ro], TR = [cx + Ro, yT - Ro], BR = [cx + Ro, yT + Ro], BL = [cx - Ro, yT + Ro];
      var tri = function (a, b) { return E.poly([[cx, cyy], a, b]); };
      var mkRad = function () {
        if (sh2) return E.line(rad, t.dark, 0.6, ' stroke-opacity="0.55"');
        return E.path(tri(TL, BL), t.lite, null, 0, ' fill-opacity="0.55"') + E.path(tri(TR, BR), t.dark, null, 0, ' fill-opacity="0.55"') +
          E.clip(ctx, tri(TL, TR) + tri(BL, BR), E.rowsV(cx - Ro, cx + Ro, yT - Ro, yT + Ro, 3.2, t.dark)) +
          E.clip(ctx, tri(TL, BL) + tri(TR, BR), E.rowsH(cx - Ro, cx + Ro, yT - Ro, yT + Ro, 3.2, t.dark));
      };
      s += E.path(outer, t.fill) + E.clip(ctx, outer, mkRad()) + E.path(outer, 'none', t.line, 1.2);
      s += E.path(ridge, t.lite) + E.clip(ctx, ridge, mkRad()) + E.path(ridge, 'none', t.dark, 2.6) + E.path(ridge, 'none', t.line, 0.9);
      if (!sh2) [[-1, -1], [1, -1], [1, 1], [-1, 1]].forEach(function (q) { // 方楼四条戗脊：外檐角 → 屋脊角 → 天井角
        var d = 'M' + f(cx + q[0] * (r + ov)) + ' ' + f(yT + q[1] * (r + ov)) + 'L' + f(cx + q[0] * rm) + ' ' + f(yR + q[1] * rm) + 'L' + f(cx + q[0] * ri) + ' ' + f(yT + q[1] * ri);
        s += E.line(d, t.line, 2.4) + E.line(d, t.dark, 1.3);
      });
      // 天井：先填内圈木回廊（背面内墙），再把地面（压低 h 的同形）裁进去
      var gal = '';
      [9, 18, 27].forEach(function (z) { gal += E.line(backArc(sh, cx, cy - z * K, ri), C.vermil, 1.3) + E.line(backArc(sh, cx, cy - z * K - 1.4, ri), C.gold2, 0.5); });
      var floor = ring(sh, cx, cy, ri) ;
      var cour = E.rect(cx - ri - 2, yT - ri - 2, 2 * ri + 4, 2 * ri + 4 + h, C.umberL) + gal +
        E.path(floor, E.mix(C.stoneL, C.earthL, 0.4), C.gold, 0.7) +
        E.circle(cx, cy - ri * 0.25, 3.2, C.stone, C.gold, 0.6) + E.circle(cx, cy - ri * 0.25, 1.8, C.water); // 天井水井
      s += E.path(hole, C.umberL) + E.clip(ctx, hole, cour) + E.path(hole, 'none', t.line, 1.2) + E.path(hole, 'none', t.dark, 0.5);
      return s;
    }
  });

  return { H: H, HOUSES: HOUSES };
});
