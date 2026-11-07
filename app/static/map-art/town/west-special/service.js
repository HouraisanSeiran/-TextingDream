/*
 * 织梦 · 西式特殊建筑：服务与防务（水井、蓄水池、磨坊、学院、医馆、兵营、瞭望塔）
 * 浏览器挂 window.TownArtWS_service；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var P = (typeof module !== 'undefined' && module.exports) ? require('./prims.js') : root.TownArtWS_prims;
  var C = P.C, f = P.f, seg = P.seg, ln = P.ln, rect = P.rect, poly = P.poly, path = P.path, flat = P.flat;
  var defs = [];
  function def(o) { defs.push(o); }
  function sack(cx, yb, w, h, fill) {
    return path('M' + f(cx - w * 0.2) + ' ' + f(yb - h) + 'Q' + f(cx - w * 0.62) + ' ' + f(yb - h * 0.55) + ' ' + f(cx - w * 0.5) + ' ' + f(yb - 1) +
      'Q' + f(cx) + ' ' + f(yb + 1.5) + ' ' + f(cx + w * 0.5) + ' ' + f(yb - 1) + 'Q' + f(cx + w * 0.62) + ' ' + f(yb - h * 0.55) + ' ' + f(cx + w * 0.2) + ' ' + f(yb - h) + 'Z', fill || C.paper, 1.2) +
      ln(seg(cx - w * 0.22, yb - h + 1.2, cx + w * 0.22, yb - h + 1.2), 1.2, 1, C.beam);
  }
  /** 水面波纹：x0..x1 × y0..y1 里几道短弧 */
  function ripples(x0, y0, x1, y1, rnd, n) {
    var d = '';
    for (var i = 0; i < (n || 8); i++) {
      var x = x0 + 4 + rnd() * (x1 - x0 - 12), y = y0 + 2 + rnd() * (y1 - y0 - 4);
      d += 'M' + f(x) + ' ' + f(y) + 'q2 -1.6 4 0t4 0';
    }
    return ln(d, 0.8, 0.55, C.paper);
  }

  // ——————————————————— 水井：石井栏 + 木亭顶 + 辘轳 ———————————————————
  def({
    kind: 'well', facility: 'well', variant: 1, name: '水井·辘轳亭', fp: [2, 2], up: 46, seed: 3101,
    roof: 'gable_tile', tags: ['water', 'windlass', 'plaza'],
    note: '公共水井：圆形石砌井栏，两根立柱撑起木瓦小坡顶，横担辘轳带摇把，绳上挂水桶；井台铺石板，旁边放一只满水的木桶。屋面为木瓦（shingle），roof 写最近的 gable_tile',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 6, o = '', cx = 48;
      o += P.paving(8, H - 46, 88, H - 2, 9, r, C.stone);
      o += P.shade([[cx + 4, yf - 4], [cx + 30, yf - 6], [cx + 34, yf - 16], [cx + 20, yf - 22]], 0.18);
      // 立柱（落在井栏左右两侧、进深中段）
      o += rect(21, yf - 72, 4.5, 58, C.beam, 1.3) + rect(70.5, yf - 72, 4.5, 58, C.beam, 1.3);
      o += ln(seg(25.5, yf - 58, 32, yf - 66) + seg(70.5, yf - 58, 64, yf - 66), 1.8, 1, C.beam);
      // 井栏
      o += P.cylinder(cx, yf - 12, 21, 16, C.stone, 'stone', r, { topFill: C.stone3 });
      o += P.ellipse(cx, yf - 28, 15, 6.6, C.dark, 1.2) + ripples(cx - 12, yf - 31, cx + 12, yf - 26, r, 2);
      // 辘轳 + 摇把 + 绳与桶
      o += rect(24, yf - 56, 48, 6, C.wood, 1.3) + ln(seg(30, yf - 55, 30, yf - 51) + seg(38, yf - 55, 38, yf - 51) + seg(56, yf - 55, 56, yf - 51), 0.8, 0.6, C.dark);
      o += ln(seg(75, yf - 53, 82, yf - 53) + seg(82, yf - 53, 82, yf - 45), 1.6, 1, C.dark) + rect(80.5, yf - 46, 3, 5, C.wood, 0.9);
      o += ln(seg(46, yf - 50, 46, yf - 40), 1, 1, C.dark) + P.barrel(46, yf - 31, 4.5, 7, true) + ln('M41.5 ' + f(yf - 38) + 'Q46 ' + f(yf - 44) + ' 50.5 ' + f(yf - 38), 0.9, 1);
      // 小坡顶
      o += P.gableRoof(14, 82, yf - 70, 26, 13, 'shingle', r, { ov: 3 });
      o += P.barrel(78, H - 3, 6, 10, true);
      return o;
    }
  });

  // ——————————————————— 蓄水池：石砌水槽 + 狮头出水口 + 手压泵 ———————————————————
  def({
    kind: 'cistern', facility: 'cistern', variant: 1, name: '蓄水池·狮口水槽', fp: [3, 2], up: 30, seed: 3201,
    roof: 'none', tags: ['water', 'reservoir', 'public_fountain'],
    note: '露天公共蓄水池：方整石砌池壁、压顶石沿与扶墙，池面可见水波；正面两只狮头出水口向小石盆放水，正中一台铁手压泵与石刻铭牌',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '', yt = yf - 22;
      o += P.boxShadow(10, 134, yt - 62, yf, 5, W, H);
      o += poly([[10, yt], [134, yt], [134, yt - 62], [10, yt - 62]], C.stone3, 1.6);
      o += poly([[16, yt - 3], [128, yt - 3], [128, yt - 57], [16, yt - 57]], C.water, 1.2) + ripples(18, yt - 54, 126, yt - 6, r, 12);
      o += flat([[16, yt - 57], [128, yt - 57], [128, yt - 52], [16, yt - 52]], C.shadow, 0.2);
      o += P.wall(10, 134, yt, yf, 'ashlar', r, { plinth: 4 });
      o += rect(8, yt - 3, 128, 4.5, C.stone2, 1.4);
      [10, 128].forEach(function (x) { o += poly([[x - 2, yf], [x - 2, yt + 2], [x + 8, yt + 2], [x + 8, yf]], C.stone2, 1.2); });
      [42, 102].forEach(function (x) {
        o += P.circle(x, yt + 7, 4.2, C.stone2, 1.2) + P.circle(x - 1.4, yt + 6, 0.7, C.ink, 0) + P.circle(x + 1.4, yt + 6, 0.7, C.ink, 0) + P.circle(x, yt + 9, 1.2, C.dark, 0.6);
        o += ln(seg(x, yt + 10, x + 0.5, yf - 6), 2.2, 1, C.water) + ln(seg(x - 1, yt + 11, x - 0.6, yf - 7), 0.7, 0.8, C.paper);
        o += P.box(x - 9, x + 9, yf, 4, 6, C.stone2, C.water, 1.2);
      });
      // 铭牌 + 手压泵
      o += rect(62, yt + 4, 20, 8, C.paper, 1.1) + ln(seg(65, yt + 7, 79, yt + 7) + seg(65, yt + 9.5, 75, yt + 9.5), 0.7, 0.6);
      o += rect(69, yt - 20, 6, 20, C.slate2, 1.3) + P.ellipse(72, yt - 20, 3.4, 1.4, C.slate, 1) + ln(seg(75, yt - 17, 88, yt - 23), 1.8, 1, C.slate2);
      o += ln(seg(69, yt - 12, 63, yt - 12) + seg(63, yt - 12, 63, yt - 8), 2, 1, C.slate2) + P.barrel(63, yt - 0.5, 3.6, 5, true);
      return o;
    }
  });

  /** 水车（侧立面看到的轮子）：cx,cy 轴心，R 半径，n 叶板 */
  function waterWheel(cx, cy, R, n) {
    var o = P.ring(cx, cy, R, 4, 1, C.ink) + P.ring(cx, cy, R, 2.2, 1, C.beam) + P.ring(cx, cy, R * 0.72, 1.6, 1, C.beam), d = '', pd2 = '';
    for (var i = 0; i < n; i++) {
      var a = i * Math.PI * 2 / n, ca = Math.cos(a), sa = Math.sin(a);
      d += seg(cx + ca * 2, cy + sa * 2, cx + ca * R * 0.72, cy + sa * R * 0.72);
      // 叶板：沿径向伸出轮缘的小方板
      var x1 = cx + ca * R * 0.7, y1 = cy + sa * R * 0.7, x2 = cx + ca * (R + 4), y2 = cy + sa * (R + 4);
      pd2 += seg(x1, y1, x2, y2);
    }
    o += ln(d, 1.4, 1, C.beam) + ln(pd2, 3.6, 1, C.ink) + ln(pd2, 2, 1, C.wood);
    return o + P.circle(cx, cy, 3.2, C.dark, 1.2);
  }

  // ——————————————————— 磨坊 1：水磨（溪边石磨坊 + 下射式水车） ———————————————————
  def({
    kind: 'watermill', facility: 'mill', variant: 1, name: '水磨坊', fp: [3, 2], up: 70, seed: 3301,
    roof: 'gable_tile', tags: ['watermill', 'water_wheel', 'millrace', 'waterside'],
    note: '石砌磨坊：右侧山墙外挂大木水车，木槽引水（导水槽）从后方落到轮顶，轮下是溪水；门口粮食麻袋与一块备用磨盘。水车属于 mill',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '', yE = yf - 38;
      o += P.boxShadow(6, 96, yf - 52, yf, 4, W, H);
      // 溪水：从后往前流过右侧
      o += poly([[98, 70], [142, 70], [142, H - 1], [96, H - 1]], C.water, 1.2) + ripples(100, 74, 140, H - 4, r, 9);
      o += ln(seg(98, 70, 96, H - 1), 1.4, 1, C.stone3);
      // 主屋
      o += P.gableRoof(6, 96, yE, 52, 22, 'tile', r, { ov: 3 });
      o += P.chimney(20, yE - 20, 9, 22, r) + P.smoke(24, yE - 46, 3, r);
      o += P.wall(6, 96, yE, yf, 'stone', r, { plinth: 5 });
      o += P.door(30, yf, 14, 22, { shape: 'arch', frame: C.stone3 }) + P.win(52, yE + 9, 9, 11, { shutters: true }) + P.win(74, yE + 9, 9, 11, { shutters: true });
      // 导水槽：从后方架上轮顶
      o += P.box(104, 132, 74, 3, 5, C.wood, C.water, 1.2) + rect(106, 74, 3, 14, C.beam, 1) + rect(128, 74, 3, 14, C.beam, 1);
      o += ln(seg(122, 74, 122, 86), 3, 0.8, C.water);
      // 水车（贴右墙）
      o += waterWheel(116, yf - 26, 23, 12);
      o += ln('M100 ' + f(yf - 2) + 'q4 -3 8 0t8 0t8 0t8 0', 1.2, 0.9, C.paper);
      // 门前：麻袋 + 立放的备用磨盘
      o += sack(12, H - 2, 9, 10) + sack(20, H - 2, 8, 9, C.stone) + sack(48, H - 2, 9, 10);
      o += P.ellipse(70, H - 12, 9, 9, C.stone2, 1.4) + P.circle(70, H - 12, 2, C.dark, 0.8) + ln(seg(64, H - 16, 69, H - 13) + seg(76, H - 8, 71, H - 11), 0.7, 0.5);
      return o;
    }
  });

  // ——————————————————— 磨坊 2：风车（塔式风车 + 四片格栅帆翼） ———————————————————
  def({
    kind: 'windmill', facility: 'mill', variant: 2, name: '风车磨坊', fp: [2, 2], up: 144, seed: 3302,
    roof: 'none', tags: ['windmill', 'sails', 'tower_mill'],
    note: '塔式风车：石砌圆塔、木瓦帽顶朝前，四片格栅木帆翼（两片蒙帆布）呈 X 形；塔脚一圈木平台与栏杆，门口麻袋。风车属于 mill；帽顶是圆锥，roof 写 none',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 6, o = '', cx = 48, hub = [48, 64];
      o += P.shade([[cx + 4, yf + 2], [cx + 30, yf], [cx + 38, yf - 14], [cx + 22, yf - 22]], 0.18);
      // 塔身（上窄下宽，用梯形近似）
      var tb = yf - 4, tt = 76;
      o += path('M' + f(cx - 22) + ' ' + f(tb) + 'L' + f(cx - 15) + ' ' + f(tt) + 'L' + f(cx + 15) + ' ' + f(tt) + 'L' + f(cx + 22) + ' ' + f(tb) +
        'A22 9 0 0 1 ' + f(cx - 22) + ' ' + f(tb) + 'Z', C.plaster, 1.8);
      var rows = '';
      for (var y = tb - 8; y > tt + 2; y -= 8) { var k = (y - tt) / (tb - tt), hw = 15 + 7 * k; rows += 'M' + f(cx - hw) + ' ' + f(y) + 'A' + f(hw) + ' ' + f(hw * 0.4) + ' 0 0 0 ' + f(cx + hw) + ' ' + f(y); }
      o += ln(rows, 0.7, 0.35) + flat([[cx + 7, tt + 1], [cx + 15, tt + 1], [cx + 22, tb], [cx + 10, tb + 8]], C.shadow, 0.14);
      o += P.win(cx - 3, tt + 22, 6, 9, { shape: 'arch', panes: false }) + P.win(cx - 3, tt + 48, 6, 9, { shape: 'arch', panes: false });
      // 木平台 + 栏杆
      o += P.box(cx - 30, cx + 30, yf - 22, 6, 3, C.wood, C.wood, 1.2);
      var rl = seg(cx - 30, yf - 32, cx + 30, yf - 32);
      [-30, -18, -6, 6, 18, 30].forEach(function (x) { rl += seg(cx + x, yf - 32, cx + x, yf - 25); });
      [-26, 26].forEach(function (x) { rl += seg(cx + x, yf - 22, cx + x * 1.04, yf - 2); });
      o += ln(rl, 1.3, 1, C.beam);
      o += P.door(cx, yf - 1, 12, 18, { shape: 'arch' }) + sack(cx - 18, H - 2, 8, 9) + sack(cx + 18, H - 2, 9, 10, C.stone);
      // 帽顶
      o += path('M' + f(cx - 19) + ' ' + f(tt + 2) + 'Q' + f(cx - 18) + ' ' + f(tt - 22) + ' ' + f(cx) + ' ' + f(tt - 26) + 'Q' + f(cx + 18) + ' ' + f(tt - 22) + ' ' + f(cx + 19) + ' ' + f(tt + 2) + 'Z', C.wood, 1.6);
      o += ln('M' + f(cx - 15) + ' ' + f(tt - 10) + 'Q' + f(cx) + ' ' + f(tt - 14) + ' ' + f(cx + 15) + ' ' + f(tt - 10) + 'M' + f(cx - 18) + ' ' + f(tt - 2) + 'Q' + f(cx) + ' ' + f(tt - 6) + ' ' + f(cx + 18) + ' ' + f(tt - 2), 0.8, 0.5);
      o += flat([[cx + 6, tt - 25], [cx + 18, tt - 20], [cx + 19, tt + 1], [cx + 8, tt + 1]], C.shadow, 0.14);
      // 帆翼：四臂 X 形
      var L = 56, ang = [-Math.PI * 0.27, Math.PI * 0.23, Math.PI * 0.73, Math.PI * 1.23];
      ang.forEach(function (a, i) {
        var ca = Math.cos(a), sa = Math.sin(a), nx = -sa, ny = ca, w = 9, s0 = 9;
        var A = [hub[0] + ca * s0, hub[1] + sa * s0], B = [hub[0] + ca * L, hub[1] + sa * L];
        var A2 = [A[0] + nx * w, A[1] + ny * w], B2 = [B[0] + nx * w, B[1] + ny * w];
        o += poly([A, B, B2, A2], i % 2 ? C.paper : 'none', 1.2, i % 2 ? '' : 'fill-opacity="0"');
        var g = '';
        for (var t = 0.12; t < 1; t += 0.11) { var p = P.lerp(A, B, t), q = P.lerp(A2, B2, t); g += seg(p[0], p[1], q[0], q[1]); }
        var m1 = P.lerp(A, A2, 0.5), m2 = P.lerp(B, B2, 0.5);
        g += seg(m1[0], m1[1], m2[0], m2[1]);
        o += ln(g, 0.9, 0.85, C.beam);
        o += ln(seg(hub[0], hub[1], B[0], B[1]), 3.4, 1, C.ink) + ln(seg(hub[0], hub[1], B[0], B[1]), 1.8, 1, C.wood);
      });
      o += P.circle(hub[0], hub[1], 4, C.dark, 1.3);
      return o;
    }
  });

  /** 垛口一列 */
  function merlons(x0, x1, y, mw, gap, fill) {
    var o = '', n = Math.max(2, Math.round((x1 - x0 + gap) / (mw + gap))), st = (x1 - x0 - mw) / (n - 1);
    for (var i = 0; i < n; i++) o += P.box(x0 + i * st, x0 + i * st + mw, y, 2.5, 5, fill || C.stone, C.stone3, 1.2);
    return o;
  }
  /** 打开的书（浮雕 / 牌面）：cx,cy 中心，s 缩放 */
  function book(cx, cy, s) {
    var o = '', d = '';
    [-1, 1].forEach(function (k) {
      o += path('M' + f(cx) + ' ' + f(cy - 4 * s) + 'Q' + f(cx + k * 5 * s) + ' ' + f(cy - 6 * s) + ' ' + f(cx + k * 9 * s) + ' ' + f(cy - 4.5 * s) +
        'L' + f(cx + k * 9 * s) + ' ' + f(cy + 4 * s) + 'Q' + f(cx + k * 5 * s) + ' ' + f(cy + 2.5 * s) + ' ' + f(cx) + ' ' + f(cy + 4.5 * s) + 'Z', C.paper, 1.1);
      for (var i = 0; i < 3; i++) d += seg(cx + k * 2 * s, cy - (2 - i * 2) * s, cx + k * 7.5 * s, cy - (2.6 - i * 2) * s);
    });
    return o + ln(d, 0.7, 0.55) + ln(seg(cx, cy - 4 * s, cx, cy + 4.5 * s), 1.1, 1);
  }
  /** 药臼与杵 */
  function mortar(cx, cy) {
    return ln(seg(cx + 1, cy - 1, cx + 6, cy - 8), 1.8, 1, C.beam) +
      path('M' + f(cx - 5.5) + ' ' + f(cy - 1.5) + 'L' + f(cx + 5.5) + ' ' + f(cy - 1.5) + 'Q' + f(cx + 5) + ' ' + f(cy + 4.5) + ' ' + f(cx) + ' ' + f(cy + 4.5) + 'Q' + f(cx - 5) + ' ' + f(cy + 4.5) + ' ' + f(cx - 5.5) + ' ' + f(cy - 1.5) + 'Z', C.stone2, 1.1);
  }
  /** 药圃：矮木框苗床 + 一行行草药 */
  function herbBed(x0, x1, yb, rnd) {
    var o = P.box(x0, x1, yb, 12, 4, C.beam, C.dark, 1.2), y, x;
    for (y = yb - 14; y < yb - 4; y += 4.5) {
      for (x = x0 + 4; x < x1 - 2; x += 5 + rnd() * 1.5) {
        var big = rnd() < 0.5;
        o += P.circle(x, y, big ? 2.4 : 1.8, big ? C.leaf : '#a3ac6c', 0.7);
        if (rnd() < 0.18) o += P.circle(x + 1, y - 1.5, 0.9, rnd() < 0.5 ? C.paper : C.tile, 0);
      }
    }
    return o;
  }

  // ——————————————————— 学院：石砌学堂 + 门楼 + 观星塔 ———————————————————
  def({
    kind: 'academy', facility: 'academy', variant: 1, name: '学院·观星塔', fp: [3, 2], up: 96, seed: 3401,
    roof: 'steep_slate', tags: ['college', 'library', 'observatory', 'gothic'],
    note: '两层石砌学堂：一排高尖拱窗，正中带垛口的门楼刻打开的书；右侧屋顶上一座圆形观星小塔，穹顶开缝伸出铜望远镜；两侧蓝色学院旗幅',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '', yE = yf - 50;
      o += P.boxShadow(6, 138, yf - 50, yf, 5, W, H);
      o += P.gableRoof(6, 138, yE, 50, 22, 'slate', r, { ov: 3 });
      o += P.chimney(22, yE - 20, 8, 20, r);
      // 观星塔：骑在右侧屋面上
      var ox = 116, ob = yE - 16;
      o += P.cylinder(ox, ob, 11, 18, C.stone, 'stone', r, { top: false });
      o += P.win(ox - 2.5, ob - 13, 5, 8, { shape: 'arch', panes: false });
      o += path('M' + f(ox - 12.5) + ' ' + f(ob - 17) + 'A12.5 12.5 0 0 1 ' + f(ox + 12.5) + ' ' + f(ob - 17) + 'Z', C.slate, 1.5) +
        flat([[ox + 4, ob - 28], [ox + 12, ob - 18], [ox + 4, ob - 17.5]], C.slate2) + rect(ox - 2, ob - 29, 4, 12, C.dark, 1);
      o += ln(seg(ox, ob - 23, ox + 15, ob - 36), 4, 1, C.ink) + ln(seg(ox, ob - 23, ox + 15, ob - 36), 2.2, 1, C.wash);
      // 主体两层
      o += P.wall(6, 138, yE, yf, 'ashlar', r, { plinth: 5 });
      o += ln(seg(6, yE + 25, 138, yE + 25), 1.6, 0.8) + rect(6, yE + 24, 132, 2.5, C.stone2, 1);
      [12, 30, 106, 124].forEach(function (x) { o += P.win(x, yE + 4, 8, 17, { shape: 'point' }) + P.win(x, yE + 30, 8, 13, { shape: 'point' }); });
      // 门楼
      var yt = yf - 90;
      o += poly([[54, yt], [90, yt], [90, yt - 12], [54, yt - 12]], C.stone3, 1.4) + merlons(54, 90, yt - 9.5, 4, 3.5, C.stone2);
      o += P.wall(54, 90, yt, yf, 'ashlar', r, { plinth: 6 }) + merlons(53, 91, yt, 4.5, 3.5, C.stone);
      o += P.win(66, yt + 9, 12, 20, { shape: 'point' });
      o += rect(61, yt + 36, 22, 14, C.slate2, 1.3) + book(72, yt + 43, 1);
      o += P.door(72, yf, 16, 25, { shape: 'point', frame: C.stone3 });
      o += sBanner(46, yE + 3) + sBanner(98, yE + 3);
      return o;
    }
  });
  function sBanner(cx, yt) {
    return ln(seg(cx - 5, yt, cx + 5, yt), 1.4, 1, C.dark) +
      path('M' + f(cx - 4) + ' ' + f(yt) + 'L' + f(cx + 4) + ' ' + f(yt) + 'L' + f(cx + 4) + ' ' + f(yt + 16) + 'L' + f(cx) + ' ' + f(yt + 12.5) + 'L' + f(cx - 4) + ' ' + f(yt + 16) + 'Z', C.slate, 1.1) +
      P.circle(cx, yt + 6, 2, C.wash, 0.8);
  }

  // ——————————————————— 医馆：木筋病坊 + 药圃 + 药臼招牌 ———————————————————
  def({
    kind: 'infirmary', facility: 'infirmary', variant: 1, name: '医馆·药圃', fp: [3, 2], up: 70, seed: 3501,
    roof: 'gable_tile', tags: ['healer', 'herb_garden', 'apothecary'],
    note: '两层木筋病坊：门上蛇杖石牌，铁臂挑出药臼招牌，檐下倒挂一排晾干的草药束；门前两块木框药圃，中间石板小径；门边长凳',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yb = H - 26, o = '', yE = yb - 46;
      o += P.boxShadow(6, 138, yb - 44, yb, 5, W, H);
      o += P.gableRoof(6, 138, yE, 44, 20, 'tile', r, { ov: 3 });
      o += P.chimney(112, yE - 18, 9, 20, r) + P.smoke(116, yE - 44, 3, r);
      var g = P.gableFront(54, 90, yE + 1, 16, 16, 'tile', r, { ov: 2.5, timber: true });
      o += g.roof;
      o += P.wall(6, 138, yE, yb - 22, 'timber', r, { bays: 6 });
      o += P.wall(6, 138, yb - 22, yb, 'plaster', r, { plinth: 4 });
      o += g.gable + P.circle(72, yE - 6, 3.5, C.dark, 1.1);
      [14, 34, 102, 122].forEach(function (x) { o += P.win(x, yE + 6, 8, 11, { glass: C.paper }) + P.win(x, yb - 17, 8, 10, { shutters: true }); });
      o += P.win(66, yE + 6, 12, 11, {});
      // 草药束
      var hb = '';
      [12, 20, 28, 40, 48, 100, 108, 120, 128].forEach(function (x, i) {
        hb += ln(seg(x, yE + 0.5, x, yE + 3), 0.7, 1) + poly([[x - 2, yE + 3], [x + 2, yE + 3], [x + 0.8, yE + 9], [x - 0.8, yE + 9]], i % 3 ? C.leaf : C.thatch2, 0.8);
      });
      o += hb;
      // 门 + 蛇杖牌 + 药臼招牌
      o += P.door(72, yb, 14, 20, { shape: 'arch', frame: C.stone3 });
      o += rect(64, yb - 33, 16, 10, C.paper, 1.2) + ln(seg(72, yb - 32, 72, yb - 24), 1.3, 1, C.beam) +
        ln('M70 ' + f(yb - 31) + 'q4 1.2 0 2.4t0 2.4t0 2.4', 1.1, 1, '#5f7a4a');
      o += P.hangSign(88, yb - 30, 1, 14, 12, mortar);
      o += rect(44, yb - 7, 14, 2.2, C.wood, 1) + ln(seg(46, yb - 5, 46, yb) + seg(56, yb - 5, 56, yb), 1.3, 1, C.beam);
      // 药圃 + 小径
      o += P.paving(64, yb, 80, H - 1, 8, r, C.stone);
      o += herbBed(10, 60, H - 3, r) + herbBed(84, 134, H - 3, r);
      return o;
    }
  });

  /** 武器架：横杆上斜靠几支长矛 + 一面圆盾 */
  function weaponRack(x0, yb) {
    var o = rect(x0, yb - 14, 2.4, 14, C.beam, 1) + rect(x0 + 22, yb - 14, 2.4, 14, C.beam, 1) + rect(x0 - 1, yb - 12, 27, 2.2, C.wood, 1);
    var d = '', tips = '';
    for (var i = 0; i < 4; i++) {
      var x = x0 + 4 + i * 5;
      d += seg(x, yb, x + 2, yb - 26);
      tips += 'M' + f(x + 2) + ' ' + f(yb - 31) + 'L' + f(x + 3.4) + ' ' + f(yb - 26) + 'L' + f(x + 0.6) + ' ' + f(yb - 26) + 'Z';
    }
    return o + ln(d, 1.3, 1, C.beam) + path(tips, C.slate, 0.8);
  }
  /** 圆盾：红底 + 黄十字 + 铁边 */
  function shield(cx, cy, r) {
    return P.circle(cx, cy, r, C.red, 1.3) + ln(seg(cx, cy - r + 1, cx, cy + r - 1) + seg(cx - r + 1, cy, cx + r - 1, cy), 1.4, 1, C.wash) +
      P.circle(cx, cy, 1.4, C.slate2, 0.7);
  }
  /** 稻草靶人 */
  function dummy(cx, yb) {
    return ln(seg(cx, yb, cx, yb - 18) + seg(cx - 7, yb - 14, cx + 7, yb - 14), 1.6, 1, C.beam) +
      P.ellipse(cx, yb - 12, 4.5, 6, C.thatch, 1.1) + P.circle(cx, yb - 20.5, 3.4, C.thatch, 1.1) +
      P.ring(cx, yb - 12, 2.2, 0.9, 1, C.red);
  }

  // ——————————————————— 兵营：带垛口的石砌营房 + 操练场 ———————————————————
  def({
    kind: 'barracks', facility: 'barracks', variant: 1, name: '兵营·操练场', fp: [4, 2], up: 70, seed: 3601,
    roof: 'gable_tile', tags: ['garrison', 'crenellated', 'drill_yard', 'armory'],
    note: '长条石砌营房：檐口一圈垛口胸墙后是红瓦坡顶，窄长射击窗、包铁双扇门，门上挂盾徽；门前土操练场：长矛武器架、稻草靶人、军旗',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yb = H - 22, o = '', yE = yb - 40;
      o += P.boxShadow(6, 186, yb - 46, yb, 5, W, H);
      o += poly([[4, yb - 2], [188, yb - 2], [190, H - 2], [2, H - 2]], '#c7b48d', 1, 'stroke-opacity="0.5"');
      o += P.gableRoof(10, 182, yE - 4, 46, 16, 'tile', r, { ov: 0 });
      o += P.chimney(30, yE - 26, 9, 18, r) + P.smoke(34, yE - 50, 3, r) + P.chimney(156, yE - 26, 9, 18, r);
      o += P.wall(6, 186, yE, yb, 'stone', r, { plinth: 5 });
      o += rect(4, yE - 3, 184, 4.5, C.stone2, 1.4) + merlons(4, 184, yE - 3, 5, 4, C.stone);
      [16, 34, 52, 130, 148, 166].forEach(function (x) { o += rect(x, yE + 8, 3.5, 16, C.dark, 1) + ln(seg(x - 2, yE + 15, x + 5.5, yE + 15), 1, 0.9, C.stone3); });
      // 门：包铁双扇门 + 门头盾徽
      o += P.door(96, yb, 22, 26, { shape: 'arch', frame: C.stone3, fill: C.dark });
      o += ln(seg(85.5, yb - 8, 106.5, yb - 8) + seg(85.5, yb - 18, 106.5, yb - 18), 1.6, 1, C.slate2);
      o += path('M88 ' + f(yE + 2) + 'L104 ' + f(yE + 2) + 'L104 ' + f(yE + 9) + 'Q104 ' + f(yE + 15) + ' 96 ' + f(yE + 17) + 'Q88 ' + f(yE + 15) + ' 88 ' + f(yE + 9) + 'Z', C.slate, 1.2) +
        ln(seg(96, yE + 3, 96, yE + 15) + seg(89, yE + 8, 103, yE + 8), 1.5, 1, C.wash);
      o += shield(70, yb - 18, 5) + shield(122, yb - 18, 5);
      // 操练场
      o += weaponRack(14, H - 3) + dummy(56, H - 3) + dummy(140, H - 3) + weaponRack(156, H - 4);
      o += P.flag(116, H - 3, 40, 14, C.red);
      return o;
    }
  });

  // ——————————————————— 瞭望塔：高石塔 + 木制望台 + 烽火盆 ———————————————————
  def({
    kind: 'watchtower', facility: 'watchtower', variant: 1, name: '瞭望塔·烽火', fp: [2, 2], up: 144, seed: 3701,
    roof: 'monopitch', tags: ['lookout', 'beacon', 'defense'],
    note: '方形石塔，越往上越窄；顶层挑出木制望台（托梁 + 栏杆），上方四坡木瓦小顶与号角旗；台角一只烽火铁盆。底层包铁小门、墙上一列箭窗，塔脚堆柴。roof 最近 monopitch，实为四坡小顶',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '', cx = 48;
      o += P.boxShadow(24, 72, yf - 26, yf, 5, W, H);
      // 塔身：梯形
      var tb = yf, tt = 70, b0 = 24, b1 = 72, t0 = 30, t1 = 66;
      o += poly([[b0, tb], [t0, tt], [t1, tt], [b1, tb]], C.stone, 1.8);
      var d = '', v = '', row = 0;
      for (var y = tb - 7; y > tt + 2; y -= 7, row++) {
        var k = (tb - y) / (tb - tt), l = b0 + (t0 - b0) * k, rr = b1 + (t1 - b1) * k;
        d += seg(l + 0.8, y, rr - 0.8, y);
        for (var x = l + (row % 2 ? 6 : 11); x < rr - 3; x += 11) v += seg(x, y - 6.5, x, y - 0.5);
      }
      o += ln(d, 0.8, 0.5) + ln(v, 0.7, 0.42) + flat([[b1 - 6, tb - 1], [t1 - 4, tt + 1], [t1 - 1, tt + 1], [b1 - 1, tb - 1]], C.shadow, 0.13);
      [96, 124, 152].forEach(function (y) { o += rect(cx - 1.8, y, 3.6, 12, C.dark, 1); });
      o += P.door(cx, tb, 12, 18, { shape: 'arch', frame: C.stone3, fill: C.dark });
      // 望台：托梁 + 台面 + 栏杆
      var py = tt;
      o += ln(seg(t0 + 1, py + 14, t0 - 9, py + 1) + seg(t1 - 1, py + 14, t1 + 9, py + 1), 2.2, 1, C.beam);
      o += P.box(t0 - 12, t1 + 12, py + 2, 12, 4, C.beam, C.wood, 1.3);
      o += rect(t0 - 9, py - 40, 3, 40, C.beam, 1.1) + rect(t1 + 6, py - 40, 3, 40, C.beam, 1.1);
      var rail = seg(t0 - 12, py - 12, t1 + 12, py - 12);
      for (var px = t0 - 10; px <= t1 + 10; px += 6) rail += seg(px, py - 12, px, py - 2);
      o += ln(rail, 1.3, 1, C.beam);
      // 烽火盆（左角）
      o += ln(seg(t0 - 4, py - 13, t0 - 2, py - 22) + seg(t0 + 4, py - 13, t0 + 2, py - 22), 1.2, 1, C.slate2);
      o += path('M' + f(t0 - 6) + ' ' + f(py - 25) + 'L' + f(t0 + 6) + ' ' + f(py - 25) + 'L' + f(t0 + 3) + ' ' + f(py - 20) + 'L' + f(t0 - 3) + ' ' + f(py - 20) + 'Z', C.slate2, 1.1);
      o += path('M' + f(t0 - 5) + ' ' + f(py - 25) + 'Q' + f(t0 - 4) + ' ' + f(py - 31) + ' ' + f(t0 - 1) + ' ' + f(py - 30) + 'Q' + f(t0) + ' ' + f(py - 36) + ' ' + f(t0 + 2) + ' ' + f(py - 33) +
        'Q' + f(t0 + 5) + ' ' + f(py - 31) + ' ' + f(t0 + 5) + ' ' + f(py - 25) + 'Z', C.tile, 0.9) + path('M' + f(t0 - 2) + ' ' + f(py - 25) + 'Q' + f(t0) + ' ' + f(py - 31) + ' ' + f(t0 + 2.5) + ' ' + f(py - 25) + 'Z', C.wash, 0);
      // 小四坡顶 + 旗
      o += P.hipRoof(t0 - 12, t1 + 12, py - 40, 14, 14, 'shingle', r, { ov: 2 });
      o += P.flag(cx, py - 48, 14, 13, C.red);
      // 塔脚柴堆
      var fw = '';
      for (var i = 0; i < 4; i++) fw += seg(76, H - 3 - i * 2.4, 92, H - 4 - i * 2.4);
      o += ln(fw, 2.2, 1, C.ink) + ln(fw, 1.2, 1, C.wood);
      return o;
    }
  });

  if (typeof module !== 'undefined' && module.exports) module.exports = defs;
  else root.TownArtWS_service = defs;
})(typeof window !== 'undefined' ? window : this);
