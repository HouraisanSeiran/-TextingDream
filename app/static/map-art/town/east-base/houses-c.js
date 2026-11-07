/*
 * 织梦 · 东方民居（三）：园林宅院、歇山大宅、渔家棚屋、悬山农舍、卷棚小筑
 * 坐标与画法约定同 houses-a.js（原点 = 占地左前角，g 向南，z 向上，屏幕 y = g - z*K）。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./east-core.js'), require('./houses-a.js'), require('./houses-b.js'));
  else root.TownArtEast_housesC = factory(root.TownArtEast_core, root.TownArtEast_housesA, root.TownArtEast_housesB);
})(this, function (E, HA, HB) {
  'use strict';
  var C = E.C, T = E.TILE, f = E.f, sy = E.sy, K = E.K, H = HA.H, HOUSES = [];

  function seg(x0, y0, x1, y1) { return 'M' + f(x0) + ' ' + f(y0) + 'L' + f(x1) + ' ' + f(y1); }
  function mid(a, b) { return [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]; }
  // 不规则闭合曲线（池塘、湖石）：n 个半径抖动的点，用中点二次曲线连成光滑轮廓
  function blob(cx, cy, rx, ry, r, n, jit) {
    var pts = [], i;
    n = n || 9; jit = jit == null ? 0.3 : jit;
    for (i = 0; i < n; i++) {
      var a = i / n * Math.PI * 2, k = 1 - jit / 2 + r() * jit;
      pts.push([cx + Math.cos(a) * rx * k, cy + Math.sin(a) * ry * k]);
    }
    var d = 'M' + E.pt(mid(pts[n - 1], pts[0]));
    for (i = 0; i < n; i++) d += 'Q' + E.pt(pts[i]) + ' ' + E.pt(mid(pts[i], pts[(i + 1) % n]));
    return d + 'Z';
  }
  // 太湖石：竖向不规则石峰，金线勾边，内缩一圈浅色叠晕，几个深色孔洞
  function rock(ctx, cx, g, w, hh) {
    var r = ctx.r, cy = g - hh / 2, s = '';
    E.track(g - hh - 2);
    s += E.shadow(cx - w / 2, cx + w / 2, g - 3, g, 6, 3);
    s += E.path(blob(cx, cy, w / 2, hh / 2, r, 8, 0.4), C.stone, C.gold, 0.9);
    s += E.path(blob(cx - w * 0.08, cy - hh * 0.08, w * 0.3, hh * 0.3, r, 7, 0.4), C.stoneL);
    for (var i = 0; i < 3; i++) s += E.circle(cx + (r() - 0.5) * w * 0.5, cy + (r() - 0.4) * hh * 0.6, 0.8 + r() * 1.1, C.gray);
    return s;
  }
  // 池塘：水面 + 金线岸 + 两道浅色水纹 + 几片荷叶
  function pond(ctx, cx, cy, rx, ry, lotus) {
    var r = ctx.r, d = blob(cx, cy, rx, ry, r, 10, 0.22), s = '';
    s += E.path(blob(cx, cy, rx + 2, ry + 1.6, r, 10, 0.2), C.stone, C.gold, 0.7);
    s += E.path(d, C.tealL, C.gold, 0.8); // 水色 #6cc1b3，同 east-ground / 东方码头
    var w = '';
    for (var i = 0; i < 3; i++) { var wx = cx + (r() - 0.5) * rx, wy = cy + (r() - 0.5) * ry; w += 'M' + f(wx - 4) + ' ' + f(wy) + 'q2 -1.4 4 0t4 0'; }
    s += E.clip(ctx, d, E.line(w, C.creamL, 0.7, ' stroke-opacity="0.75"'));
    for (var j = 0; j < (lotus || 0); j++) {
      var lx = cx + (r() - 0.5) * rx * 1.2, ly = cy + (r() - 0.3) * ry * 0.9;
      s += '<ellipse cx="' + f(lx) + '" cy="' + f(ly) + '" rx="2.6" ry="1.6" fill="' + C.leaf + '" stroke="' + C.gold2 + '" stroke-width="0.4"/>';
      if (j % 2 === 0) s += E.circle(lx + 1.2, ly - 1.4, 0.9, C.orange);
    }
    return s;
  }
  // 方亭：四柱 + 美人靠 + 攒尖
  function pavilion(ctx, x0, x1, gb, gf, h, t) {
    var s = E.shadow(x0, x1, gb, gf, h + 10, 5) + E.plinth(x0 - 1.5, x1 + 1.5, gf + 1.5, 2);
    s += E.rect(x0, sy(gf, 2), x1 - x0, 0, C.stoneL);
    [x0 + 1.4, x1 - 1.4].forEach(function (x) { s += E.col(x, gb + 2, 2, h, C.vermil); });
    s += H.railing(x0 + 1, x1 - 1, gf, 3, 7, C.vermil, 2.4);
    [x0 + 1.4, x1 - 1.4].forEach(function (x) { s += E.col(x, gf, 2, h, C.vermil); });
    s += E.face(x0, x1, gf, h - 2.2, h, C.teal, C.gold2, 0.5);
    s += E.roofPyr(ctx, { x0: x0, x1: x1, gb: gb, gf: gf, h: h, rh: 13, t: t, ov: 5, lift: 6 });
    return s;
  }

  // 11. 园林宅院 2×2：后面卷棚花厅，中间池塘、曲桥、湖石、方亭，前面白粉墙开月洞门、墙上漏窗
  HOUSES.push({
    kind: 'yuanlin', name: '园林宅院', fp: [2, 2], roof: 'gable_tile', tags: ['garden', 'courtyard', 'pond', 'moon_gate'],
    note: '江南宅园：花厅卷棚顶（RoofId 取 gable_tile），园中凿池、架曲桥、立湖石与方亭，白粉墙月洞门',
    variants: [{ t: 'gray', pt: 'teal', plant: 'bamboo' }, { t: 'navy', pt: 'gray', plant: 'tree' }],
    draw: function (ctx, v) {
      var t = T[v.t], s = '';
      s += H.paving(4, 92, -76, -8, 0, E.mix(C.grass, C.leafL, 0.25));
      s += H.hall(ctx, { x0: 12, x1: 68, gb: -94, gf: -76, h: 21, rh: 8, type: 'juan', t: t, ph: 3, ov: 4,
        deco: function (ph) { return H.bays(12, 68, -76, ph, 21, 4, { doors: [1, 2], win: 'hex', dh: 13, wh: 8 }); } });
      s += H.sideWall(4, 8, -74, -10, 15, T.gray, C.creamL) + H.sideWall(88, 92, -74, -10, 15, T.gray, C.creamL);
      s += rock(ctx, 18, -60, 10, 18);
      s += pavilion(ctx, 66, 84, -64, -48, 17, T[v.pt]);
      s += pond(ctx, 40, -42, 21, 9, 4);
      // 曲桥：三折石板桥跨过池塘
      var br = 'M19 -36L32 -36L38 -44L50 -44L56 -38L64 -38';
      s += E.line(br, C.gold, 4.4) + E.line(br, C.stoneL, 3) + E.line(br, C.grayL, 0.5, ' stroke-dasharray="1.6 1.6"');
      s += rock(ctx, 62, -24, 7, 10);
      if (v.plant === 'bamboo') s += E.bamboo(ctx, 16, -16, 30, 5);
      else s += E.tree(ctx, 18, -16, 22, 9);
      s += E.tree(ctx, 80, -18, 18, 7, 'pine');
      // 前院墙：白粉墙 + 灰瓦压顶，正中月洞门，两侧漏窗
      s += H.lowWall(ctx, 4, 92, -6, 19, T.gray, C.creamL);
      s += E.door(41, -6, 0, 14, 0, 'moon');
      s += E.win(16, -6, 8, 9, 7, 'hex') + E.win(71, -6, 8, 9, 7, 'hex');
      return s;
    }
  });

  // 12. 歇山大宅 2×2：高台基、五开间正厅，重檐（下层腰檐 + 上层歇山）、青绿彩画、前出月台和石阶，两侧石狮
  HOUSES.push({
    kind: 'xieshan', name: '歇山大宅', fp: [2, 2], roof: 'hip_tile', tags: ['manor', 'wealthy', 'double_eave', 'terrace'],
    note: '富户正厅：歇山顶（RoofId 无歇山，取 hip_tile），重檐、高台基、月台石阶；变体 1 青绿琉璃，变体 2 灰瓦单檐带前院照壁',
    variants: [{ t: 'teal', dbl: true }, { t: 'gray', dbl: false, screen: true }],
    draw: function (ctx, v) {
      var t = T[v.t], s = '', x0 = 10, x1 = 86, gb = -86, gf = -50, ph = 7, h = v.dbl ? 40 : 30;
      s += E.shadow(x0, x1, gb, gf, h + 20, 7);
      // 前院方砖地
      s += H.paving(4, 92, -44, -3, 8, C.stoneL);
      // 高台基 + 月台
      s += E.plinth(x0 - 4, x1 + 4, gf + 3, ph);
      s += E.rect(30, sy(-40, 5), 36, sy(gf + 3, 5) - sy(-40, 5), C.stoneL, C.gold, 0.7) + E.face(30, 66, -40, 0, 5, C.stone, C.gold, 0.8);
      // 石阶：一级级横纹
      var st = '';
      for (var i = 1; i < 5; i++) st += seg(41, sy(-40, i), 55, sy(-40, i));
      s += E.rect(41, sy(-40, 5), 14, 5 * K, C.stoneL, C.gold, 0.6) + E.line(st, C.grayL, 0.6);
      s += E.face(x0, x1, gf, ph, h, C.cream);
      s += H.bays(x0, x1, gf, ph, v.dbl ? 26 : h, 5, { doors: [1, 2, 3], door: 'double', dh: 15, wh: 9, beamC: C.teal });
      if (v.dbl) { // 上层：退进一点的二层墙身 + 腰檐
        s += E.face(x0 + 6, x1 - 6, gf - 4, 26, h, C.vermil, C.gold2, 0.7);
        for (var k = 0; k < 5; k++) s += E.win(x0 + 8 + k * (x1 - x0 - 12) / 5 + 2, gf - 4, 29, (x1 - x0 - 12) / 5 - 4, 7, 'lattice');
        s += E.face(x0 + 5, x1 - 5, gf - 4, h - 2.4, h, C.teal, C.gold2, 0.5);
        s += H.shed(ctx, x0 - 2, x1 + 2, gf, 25, t, 7, 4);
      }
      s += E.roofEW(ctx, { x0: v.dbl ? x0 + 4 : x0, x1: v.dbl ? x1 - 4 : x1, gb: gb, gf: v.dbl ? gf - 4 : gf, h: h, rh: 18, type: 'xie', t: t, ov: 7, os: 5, lift: 8, ridge: 'curl', ridgeW: 3.6 });
      // 石狮一对：圆身 + 卷鬃
      [24, 72].forEach(function (x) {
        s += E.rect(x - 3.5, sy(-38, 3), 7, 3 * K, C.stone, C.gold, 0.6);
        s += E.circle(x, sy(-38, 6.5), 3.2, C.stoneL, C.gold, 0.7) + E.circle(x, sy(-38, 10.5), 2.4, C.stoneL, C.gold, 0.7) + E.circle(x - 0.8, sy(-38, 11), 0.6, C.umber);
      });
      if (v.screen) { // 前院照壁
        s += E.shadow(30, 66, -12, -8, 18, 3);
        s += E.face(30, 66, -8, 0, 16, C.vermil, C.gold, 0.9);
        s += E.rect(40, sy(-8, 13), 16, 9 * K, C.stone, C.gold, 0.7) + E.circle(48, sy(-8, 8.5), 2.6, C.tealL, C.gold, 0.6);
        s += E.roofEW(ctx, { x0: 30, x1: 66, gb: -11, gf: -8, h: 16, rh: 4, type: 'hard', t: T.gray, ov: 1.6, os: 2, lift: 1.5, dots: false, ridgeW: 2, ridge: 'curl' });
      } else {
        s += E.tree(ctx, 12, -10, 24, 9, 'pine') + E.tree(ctx, 84, -10, 20, 8);
      }
      return s;
    }
  });

  // 渔网：挂在竹竿间的一片菱形网格
  function net(ctx, x0, x1, yT, yB) {
    var d = 'M' + f(x0) + ' ' + f(yT) + 'Q' + f((x0 + x1) / 2) + ' ' + f(yT + 3) + ' ' + f(x1) + ' ' + f(yT) + 'L' + f(x1 - 2) + ' ' + f(yB) + 'Q' + f((x0 + x1) / 2) + ' ' + f(yB + 2) + ' ' + f(x0 + 2) + ' ' + f(yB) + 'Z', g = '';
    for (var x = x0 - 20; x < x1 + 20; x += 2.6) g += seg(x, yT, x + 14, yB + 3) + seg(x + 14, yT, x, yB + 3);
    return E.path(d, C.umber, null, 0, ' fill-opacity="0.12"') + E.clip(ctx, d, E.line(g, C.umber, 0.4, ' stroke-opacity="0.75"')) + E.path(d, 'none', C.umberL, 0.6);
  }

  // 13. 渔家棚屋 2×1：前半伸进水里，木桩架起，茅草 / 灰瓦单坡加悬山棚顶，挂渔网，泊一条小舢板
  HOUSES.push({
    kind: 'yupeng', name: '渔家棚屋', fp: [2, 1], roof: 'gable_thatch', tags: ['waterside', 'stilts', 'fishing'],
    note: '水边棚屋：前沿木桩站在水里，悬山茅草顶，侧挂渔网，前泊舢板；变体 2 为灰瓦并带晒鱼架',
    variants: [{ t: 'thatch', boat: true }, { t: 'gray', rack: true, roof: 'gable_tile' }],
    draw: function (ctx, v) {
      var t = T[v.t], s = '', x0 = 10, x1 = 62, gb = -42, gf = -22, fz = 7, h = 22, r = ctx.r;
      // 水面：占地南半边是水，北半边是河岸
      s += E.rect(0, -48, 96, 26, E.mix(C.earthL, C.grass, 0.4), null);
      var wd = 'M0 -22Q24 -24 48 -22T96 -22V0H0Z';
      s += E.path(wd, C.tealL) + E.line('M0 -22Q24 -24 48 -22T96 -22', C.gold, 0.9); // 水色 #6cc1b3，同东方码头
      var wv = '';
      for (var i = 0; i < 7; i++) { var wx = 4 + r() * 84, wy = -18 + r() * 14; wv += 'M' + f(wx) + ' ' + f(wy) + 'q2.5 -1.6 5 0t5 0'; }
      s += E.line(wv, C.creamL, 0.7, ' stroke-opacity="0.75"');
      s += E.shadow(x0, x1, gb, gf, h + 10, 6);
      // 木桩 + 平台
      s += E.rect(x0 - 2, sy(gf + 6, fz), x1 - x0 + 4, sy(gf, fz) - sy(gf + 6, fz) + 0.1, C.umberL, C.gold, 0.5);
      s += E.rowsV(x0 - 2, x1 + 2, sy(gf, fz), sy(gf + 6, fz), 3, C.umber, 0.5, 0.6);
      s += E.face(x0 - 2, x1 + 2, gf + 6, fz - 1.4, fz, C.umber, C.gold, 0.5);
      for (var p = 0; p <= 5; p++) { var px = x0 + p * (x1 - x0) / 5; s += E.rect(px - 1, sy(gf + 6, fz - 1.4), 2, (fz - 1.4) * K + 1.5, C.umber, C.gold2, 0.3); }
      // 木板墙
      s += E.face(x0, x1, gf, fz, h, C.umberL) + H.planks(x0, x1, gf, fz, h, 3);
      s += E.door(x0 + 20, gf, fz, 10, 12, 'plank') + E.win(x0 + 5, gf, fz + 5, 8, 6, 'lattice') + E.win(x1 - 13, gf, fz + 5, 8, 6, 'lattice');
      s += E.roofEW(ctx, { x0: x0, x1: x1, gb: gb, gf: gf, h: h, rh: 13, type: 'hang', t: t, ov: 5, os: 5, lift: v.t === 'thatch' ? 0.6 : 2,
        dots: v.t !== 'thatch', step: v.t === 'thatch' ? 2.2 : 3.4, ridge: v.t === 'thatch' ? 'plain' : 'horn' });
      // 晾网竹竿 + 渔网
      var yT = sy(-30, 26), yB = sy(-30, 9);
      s += E.line(seg(68, -30, 68, yT - 2) + seg(90, -28, 90, yT - 1), C.umber, 1.3) + E.line(seg(66, yT, 92, yT + 1), C.umberL, 1);
      E.track(yT - 4);
      if (v.rack) { // 晒鱼架：横竿上挂一串小鱼
        s += net(ctx, 69, 89, yT + 1, yT + 6);
        for (var q = 0; q < 6; q++) {
          var fx = 70 + q * 3.4, fy = yT + 10;
          s += E.line(seg(fx, yT + 6, fx, fy - 2), C.umber, 0.4) + '<ellipse cx="' + f(fx) + '" cy="' + f(fy) + '" rx="1.1" ry="2.4" fill="' + C.grayL + '" stroke="' + C.gold + '" stroke-width="0.3"/>';
        }
      } else s += net(ctx, 69, 89, yT + 1, yB);
      if (v.boat) { // 舢板：船身弧线 + 一支桨
        var bd = 'M58 -7Q66 -2 82 -4Q90 -5 94 -10L56 -10Z';
        s += E.path(bd, C.umber, C.gold2, 0.8) + E.line('M57 -10L94 -10', C.umberL, 1.2) + E.line(seg(70, -13, 86, -2), C.umberL, 1);
      }
      return s;
    }
  });

  // 14. 悬山农舍 2×1：长条三间，悬山顶两山挑出、博风板，檐下挂玉米辣椒，前院鸡笼 + 柴堆 + 石碾
  HOUSES.push({
    kind: 'xuanshan', name: '悬山农舍', fp: [2, 1], roof: 'gable_tile', tags: ['farm', 'rural', 'yard'],
    note: '悬山顶：屋面出际挑过两山，山面挂博风板；一侧接矮披屋作灶间；变体 2 为藏青瓦并带石碾',
    variants: [{ t: 'gray', side: 'right' }, { t: 'navy', side: 'left', mill: true }],
    draw: function (ctx, v) {
      var t = T[v.t], s = '', L = v.side === 'left', x0 = L ? 30 : 8, x1 = L ? 88 : 66, gb = -42, gf = -20, h = 19;
      s += H.paving(2, 94, -20, -2, 0, C.earthL);
      // 灶间披屋（单坡）
      var px0 = L ? 6 : 66, px1 = L ? 30 : 90;
      s += E.shadow(px0, px1, -38, -22, 16);
      s += E.face(px0, px1, -22, 0, 13, C.earth) + E.door(px0 + 7, -22, 0, 8, 10, 'plank');
      s += E.rect(L ? px0 + 3 : px1 - 7, sy(-34, 24), 4, 12 * K, C.stone, C.gold, 0.6) + E.line(seg(L ? px0 + 5 : px1 - 5, sy(-34, 24), L ? px0 + 5 : px1 - 5, sy(-34, 24) - 1.5), C.gray, 1); // 烟囱
      E.track(sy(-34, 24) - 3);
      s += H.shed(ctx, px0, px1, -36, 13, t, 15, 0.6);
      // 正屋
      s += E.shadow(x0, x1, gb, gf, h + 12);
      s += E.plinth(x0 - 1.5, x1 + 1.5, gf + 1.5, 2);
      s += E.face(x0, x1, gf, 2, h, C.cream);
      s += H.bays(x0, x1, gf, 2, h, 3, { doors: [1], door: 'plank', dh: 13, wh: 6, sill: 5, beam: false, colC: C.umber });
      s += E.roofEW(ctx, { x0: x0, x1: x1, gb: gb, gf: gf, h: h, rh: 12, type: 'hang', t: t, os: 7, ov: 4, lift: 1.8 });
      // 博风板 + 悬鱼（两山出际处）
      [x0 - 7, x1 + 7].forEach(function (x, i) {
        var yR = sy((gb + gf) / 2, h + 12), yE = sy(gf + 4, h), d = 'M' + f(x) + ' ' + f(yR) + 'L' + f(x) + ' ' + f(yE);
        s += E.line(d, C.gold2, 2.6) + E.line(d, C.umber, 1.4) + E.path('M' + f(x) + ' ' + f(yR + 2) + 'l1.8 3l-1.8 2.4l-1.8 -2.4Z', C.gold2);
      });
      // 檐下挂玉米串、辣椒串
      [x0 + 6, x1 - 6].forEach(function (x, i) {
        var y = sy(gf + 3, h - 1);
        for (var q = 0; q < 4; q++) s += '<ellipse cx="' + f(x + (q % 2) * 1.6) + '" cy="' + f(y + 2 + q * 2.4) + '" rx="1.2" ry="1.5" fill="' + (i ? C.vermil : C.ochre) + '" stroke="' + C.gold + '" stroke-width="0.3"/>';
      });
      // 柴堆 / 鸡笼
      var cx = L ? 14 : 80;
      s += E.rect(cx - 7, -9, 14, 5, C.umberL, C.gold, 0.5) + E.rowsV(cx - 7, cx + 7, -9, -4, 2, C.umber, 0.6, 0.8);
      for (var q2 = 0; q2 < 5; q2++) s += E.circle(cx - 6 + q2 * 3, -10, 1.3, C.umberL, C.umber, 0.4);
      var hx = L ? 74 : 26;
      s += E.path('M' + f(hx - 5) + ' -4Q' + f(hx) + ' -14 ' + f(hx + 5) + ' -4Z', T.bamboo.fill, C.umber, 0.6) + E.line('M' + f(hx - 3) + ' -5Q' + f(hx) + ' -12 ' + f(hx + 3) + ' -5M' + f(hx) + ' -4V-11', C.umber, 0.4);
      E.track(-15);
      if (v.mill) s += E.circle(48, -9, 5, C.stone, C.gold, 0.7) + E.circle(48, -9, 2.4, C.stoneL, C.gold, 0.5) + E.line(seg(48, -9, 56, -13), C.umber, 1.1);
      return s;
    }
  });

  // 15. 卷棚小筑 1×1：读书小斋，卷棚顶（屋脊圆弧无正脊）、前出廊、竹丛与湖石
  HOUSES.push({
    kind: 'juanpeng', name: '卷棚小筑', fp: [1, 1], roof: 'gable_tile', tags: ['study', 'garden', 'veranda'],
    note: '卷棚顶（圆脊无正脊，RoofId 取 gable_tile），前出廊带栏杆，门边竹丛 / 湖石；变体 2 为青绿瓦',
    variants: [{ t: 'gray', plant: 'bamboo' }, { t: 'teal', plant: 'rock' }],
    draw: function (ctx, v) {
      var t = T[v.t], s = '', x0 = 7, x1 = 41, gb = -36, gf = -14, h = 20;
      s += E.shadow(x0, x1, gb, gf - 6, h + 10);
      s += E.plinth(x0 - 2, x1 + 2, gf + 2, 2.5);
      // 退进的墙身（廊后）
      s += E.face(x0 + 1, x1 - 1, gf - 6, 2.5, h, C.creamL);
      s += E.door(x0 + 12, gf - 6, 2.5, 10, 13, 'double') + E.win(x0 + 3, gf - 6, 7, 6, 7, 'hex') + E.win(x1 - 9, gf - 6, 7, 6, 7, 'hex');
      // 廊柱 + 栏杆 + 挂落
      s += H.railing(x0 + 1, x0 + 10, gf, 3, 7, C.vermil, 2.2) + H.railing(x1 - 10, x1 - 1, gf, 3, 7, C.vermil, 2.2);
      [x0 + 1, x0 + 12, x1 - 12, x1 - 1].forEach(function (x) { s += E.col(x, gf, 2.5, h, C.vermil); });
      s += E.face(x0, x1, gf, h - 3, h, C.teal, C.gold2, 0.5);
      s += E.roofEW(ctx, { x0: x0, x1: x1, gb: gb, gf: gf, h: h, rh: 10, type: 'juan', t: t, ov: 4, os: 2.5, lift: 2 });
      if (v.plant === 'bamboo') s += E.bamboo(ctx, 44, -2, 30, 3);
      else s += HC_rock(ctx, 43, -2, 6, 12);
      return s;
    }
  });
  function HC_rock(ctx, cx, g, w, hh) { return rock(ctx, cx, g, w, hh); }

  return { HOUSES: HOUSES, blob: blob, rock: rock, pond: pond, pavilion: pavilion, net: net };
});
