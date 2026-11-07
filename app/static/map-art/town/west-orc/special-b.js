/*
 * 织梦 · 兽人族特殊建筑 B 组（美术样板，尚未接入游戏）：战士营帐 barracks、木架哨塔 watchtower、萨满祭坛 temple、座狼圈 stable。
 * 局部坐标：x 0..w*48，y = 0 为占地前沿，向上为负。每项 draw(ctx) 返回 svg 片段。
 * 浏览器挂 window.TownArtWO_specialB；Node 用 module.exports。依赖 core.js、parts.js、forms.js、houses-a.js、houses-b.js、special-a.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWO_core;
  var K = isNode ? require('./parts.js') : root.TownArtWO_parts;
  var F = isNode ? require('./forms.js') : root.TownArtWO_forms;
  var HA = isNode ? require('./houses-a.js') : root.TownArtWO_housesA;
  var HB = isNode ? require('./houses-b.js') : root.TownArtWO_housesB;
  var SA = isNode ? require('./special-a.js') : root.TownArtWO_specialA;
  var P = C.PAL, f = C.f;
  var S = [];

  /** 草靶：木桩上绑一捆草人，胸口插一支矛 */
  function dummy(ctx, cx, yb) {
    var s = C.shadowD(C.ellD(cx + 3, yb - 1, 6, 2)) + K.pole(cx, yb, 20, 2.4);
    s += C.line('M' + f(cx - 8) + ' ' + f(yb - 15) + 'H' + f(cx + 8), 2.6) + C.line('M' + f(cx - 8) + ' ' + f(yb - 15) + 'H' + f(cx + 8), 1.1, 1, P.wood);
    s += C.path(C.wob(ctx, [[cx - 4, yb - 6], [cx + 4, yb - 6], [cx + 5, yb - 18], [cx - 5, yb - 18]], 0.6), P.thatch, 1.1) + K.texThatch(ctx, 0, 0, 0, 0);
    s += C.ell(cx, yb - 21, 3.6, 3.4, P.thatch2, 1.1) + K.knot(cx, yb - 12, 9, 1);
    s += C.line('M' + f(cx - 10) + ' ' + f(yb - 4) + 'L' + f(cx + 1) + ' ' + f(yb - 14), 1.4, 1, P.timber) + C.path('M' + f(cx + 1) + ' ' + f(yb - 14) + 'l3 -3.6l-0.6 2.4l1.6 0.6Z', P.iron2, 0.7);
    ctx.top(yb - 25);
    return s;
  }
  /** 地上一圈练武场边界：插在地上的短桩 */
  function ring(ctx, cx, cy, rx, ry) {
    var s = C.path(C.ellD(cx, cy, rx, ry), P.soil, 0, 0.5) + C.path(C.ellD(cx, cy, rx, ry), 'none', 0.9);
    for (var a = 0; a < Math.PI * 2; a += Math.PI / 7) {
      if (Math.sin(a) < -0.2) continue; // 只画前半圈的桩，后半圈被场地遮挡也说得通
      s += K.stake(cx + Math.cos(a) * rx - 1.4, cy + Math.sin(a) * ry, 2.8, 4, P.wood, 0.7);
    }
    return s;
  }

  // 兵营：3×2 战士营帐——后排一座长条兽皮大帐，旁立战旗；前排是一圈练武场，场里草靶与兵器架
  S.push({
    id: 'west-orc-barracks-01', name: '战士营帐', kind: 'orc_barracks', facility: 'barracks', fp: [3, 2], roof: 'gable_thatch',
    tags: ['military', 'hide', 'training_yard', 'banner'], note: '兽皮 A 字长帐 + 露天练武场，屋面是兽皮，最接近 gable',
    draw: function (ctx) {
      var s = '';
      // 后排长帐
      s += C.groundShadow(14, 118, -54, -92);
      s += F.facade(ctx, 14, 118, -54, 8, 'vlogs');
      var r = F.roofLong(ctx, { x0: 14, x1: 118, yE: -62, Dp: 30, R: 14, mat: 'hide2', ov: 3, hip: 0 });
      s += r.svg;
      [r.L, r.Rt].forEach(function (p) {
        s += C.line('M' + f(p[0] - 5) + ' ' + f(p[1] - 7) + 'L' + f(p[0] + 3) + ' ' + f(p[1] + 3) + 'M' + f(p[0] + 5) + ' ' + f(p[1] - 7) + 'L' + f(p[0] - 3) + ' ' + f(p[1] + 3), 2.2) + K.knot(p[0], p[1] - 1, 3, 2);
      });
      s += K.hornSkull(66, r.yR - 4, 0.8, 11);
      s += HA.tentDoor(ctx, 42, -54, 11, 13, 'skull') + HA.tentDoor(ctx, 90, -54, 11, 13, 'tusk');
      s += K.boneString(ctx, 20, -68, 34, -66, 3) + K.boneString(ctx, 100, -66, 114, -68, 3);
      // 右侧战旗、左侧兵器架
      s += K.banner(ctx, 132, -46, 58, P.rust, -1) + K.banner(ctx, 8, -46, 50, P.moss, 1);
      // 前排练武场
      s += ring(ctx, 72, -24, 52, 15);
      s += dummy(ctx, 46, -20) + dummy(ctx, 98, -22);
      s += SA.weaponRack(ctx, 62, 82, -12, 20, ['axe', 'club', 'cleaver']);
      s += K.firepit(ctx, 128, -12, 6, true);
      ctx.top(-118);
      return s;
    }
  });

  // 瞭望塔：1×1 木架哨塔——四根原木交叉绑扎，顶上尖桩护栏小台 + 兽皮小顶，挂号角与战旗
  S.push({
    id: 'west-orc-watchtower-01', name: '木架哨塔', kind: 'orc_watchtower', facility: 'watchtower', fp: [1, 1], roof: 'gable_thatch',
    tags: ['military', 'logs', 'lookout', 'horn'], note: '兽皮小坡顶，最接近 gable',
    draw: function (ctx) {
      var s = C.shadowD(C.poly([[10, -6], [44, -6], [48, -10], [46, -30], [38, -30]]));
      // 后两柱（细、暗）
      s += K.pole(15, -30, 70, 2.6, P.dark) + K.pole(33, -30, 70, 2.6, P.dark);
      // 前两柱（略外撇）
      s += C.path(C.poly([[8, -4], [12, -4], [17, -98], [14, -98]]), P.timber, 1.1) + C.path(C.poly([[36, -4], [40, -4], [34, -98], [31, -98]]), P.timber, 1.1);
      // 交叉斜撑 + 绳扎
      var x = 'M11 -10L35 -48M37 -10L13 -48M14 -52L33 -86M34 -52L15 -86';
      s += C.line(x, 2.6) + C.line(x, 1.1, 1, P.wood);
      s += K.knot(12, -50, 4, 2) + K.knot(36, -50, 4, 2) + K.knot(15, -88, 4, 2) + K.knot(33, -88, 4, 2);
      s += C.line('M10 -50H38', 2.4) + C.line('M10 -50H38', 1, 1, P.wood);
      // 爬梯（右侧外挂）
      var lad = 'M40 -4L36 -96M45 -4L41 -96', rungs = '';
      for (var y = -10; y > -94; y -= 7) rungs += 'M' + f(40 + (y + 4) / 23) + ' ' + f(y) + 'h5';
      s += C.line(lad + rungs, 1.4) + C.line(lad, 0.6, 1, P.wood);
      // 平台：地板 + 尖桩护栏
      s += C.path(C.wob(ctx, [[5, -96], [43, -96], [44, -103], [6, -103]], 0.4), P.timber, 1.4);
      for (var k = 0; k < 9; k++) s += K.stake(5 + k * 4.4, -96, 4, 9 + (k % 3), k % 2 ? P.wood : '#b48e58', 0.8);
      s += C.line('M5 -101H44', 1.4, 1, P.dark);
      // 兽皮小顶
      s += K.pole(9, -105, 12, 2) + K.pole(39, -105, 12, 2);
      s += F.roofFront(ctx, { x0: 6, x1: 42, yE: -116, R: 10, Dp: 8, mat: 'hide', ov: 2 }).svg;
      // 挂号角（牛角号）+ 顶旗
      s += K.horn(8, -108, 7, -1, 0.4, P.bone);
      s += K.banner(ctx, 24, -134, 8, P.rust, 1);
      return s;
    }
  });

  /** 立石：一块略歪的粗石，刻一道锈红符纹 */
  function menhir(ctx, cx, yb, w, h) {
    var d = C.wob(ctx, [[cx - w / 2, yb], [cx + w / 2, yb], [cx + w * 0.4, yb - h * 0.8], [cx + w * 0.1, yb - h], [cx - w * 0.4, yb - h * 0.85]], 0.6);
    var s = C.shadowD(C.poly([[cx, yb], [cx + w / 2 + 6, yb + 2], [cx + w / 2 + 4, yb - 4]]));
    s += C.face(ctx, d, P.stone2, C.rect(cx + w * 0.15, yb - h - 2, w, h + 4, P.shadow, 0, 0.2), 1.4);
    s += C.line('M' + f(cx - w * 0.15) + ' ' + f(yb - h * 0.75) + 'l' + f(w * 0.25) + ' ' + f(h * 0.12) + 'l' + f(-w * 0.25) + ' ' + f(h * 0.12) + 'l' + f(w * 0.25) + ' ' + f(h * 0.12), 1.3, 1, P.rust);
    ctx.top(yb - h);
    return s;
  }

  // 神殿：2×2 萨满祭坛——后立三块刻纹立石，中央粗石祭台上一颗大长角兽头骨与火盆，两侧图腾柱，前设骨串拱门
  S.push({
    id: 'west-orc-temple-01', name: '萨满祭坛', kind: 'orc_shaman_altar', facility: 'temple', fp: [2, 2], roof: 'none',
    tags: ['open_air', 'shaman', 'totem', 'standing_stone', 'bone'], note: '露天祭坛，无屋顶',
    draw: function (ctx) {
      var s = SA.yard(ctx, 48, -44, 44, 38);
      s += C.path(C.ellD(48, -48, 30, 18), P.stone3, 0, 0.45) + C.path(C.ellD(48, -48, 30, 18), 'none', 0.8, 0.6);
      // 后排立石
      s += menhir(ctx, 22, -66, 11, 34) + menhir(ctx, 48, -74, 13, 46) + menhir(ctx, 74, -66, 11, 32);
      // 祭台
      s += SA.box(ctx, 32, 62, -40, 12, 8, 5);
      s += K.hornSkull(47, -66, 1.3, 17);
      s += C.ell(38, -61, 4, 1.6, P.hole, 0.9) + SA.flame(38, -61, 0.6);
      s += SA.pot(57, -60, 2.6, P.rust);
      ctx.top(-86);
      // 两侧图腾柱
      s += K.totem(ctx, 9, -24, 9, 56, 'wings') + K.totem(ctx, 79, -24, 9, 56, 'skull');
      // 前方骨串拱门
      var arch = 'M28 -4Q48 -48 68 -4';
      s += C.line(arch, 4) + C.line(arch, 2.4, 1, P.bone);
      s += K.boneString(ctx, 32, -16, 64, -16, 5);
      s += K.tusk(26, -3, 9, -1) + K.tusk(70, -3, 9, 1);
      return s;
    }
  });

  /** 座狼：蹲坐侧影（朝左），灰褐毛，竖耳 */
  function wolf(cx, yb, k, dir) {
    k = k || 1; dir = dir || -1;
    function X(v) { return f(cx + dir * v * k); }
    function Y(v) { return f(yb - v * k); }
    var d = 'M' + X(-6) + ' ' + Y(0) + 'Q' + X(-8) + ' ' + Y(6) + ' ' + X(-4) + ' ' + Y(9) + 'L' + X(2) + ' ' + Y(10) + 'L' + X(5) + ' ' + Y(15) +
      'L' + X(6) + ' ' + Y(18) + 'L' + X(7.5) + ' ' + Y(15.5) + 'L' + X(11) + ' ' + Y(14) + 'L' + X(10.5) + ' ' + Y(12) + 'L' + X(6) + ' ' + Y(11) +
      'L' + X(5) + ' ' + Y(4) + 'L' + X(6) + ' ' + Y(0) + 'Z';
    var tail = 'M' + X(-6) + ' ' + Y(1) + 'Q' + X(-11) + ' ' + Y(2) + ' ' + X(-12) + ' ' + Y(6);
    return C.line(tail, 3, 1) + C.line(tail, 1.6, 1, '#7d7468') + C.path(d, '#7d7468', 1) +
      C.circ(cx + dir * 7.5 * k, yb - 13.6 * k, 0.6 * k, P.fire2, 0) +
      C.line('M' + X(-2) + ' ' + Y(8) + 'l' + f(dir * 1.5) + ' -1.6M' + X(0) + ' ' + Y(8.5) + 'l' + f(dir * 1.5) + ' -1.6', 0.7, 0.7);
  }

  // 马厩：3×2 座狼圈——尖桩围栏圈出狼圈，后排一座半敞的原木狼棚（兽皮顶），圈内两头蹲坐的座狼，骨头食槽
  S.push({
    id: 'west-orc-stable-01', name: '座狼圈', kind: 'orc_wolf_pen', facility: 'stable', fp: [3, 2], roof: 'monopitch',
    tags: ['animal_pen', 'logs', 'hide', 'warg'], note: '兽人骑座狼，对应 stable；狼棚是单坡兽皮顶',
    draw: function (ctx) {
      var s = SA.yard(ctx, 72, -42, 66, 38);
      // 后排狼棚：原木后墙 + 单坡兽皮顶 + 前柱
      s += F.facade(ctx, 10, 96, -64, 20, 'vlogs');
      s += C.rect(12, -82, 82, 16, P.hole, 0, 0.55);
      s += K.pole(12, -54, 30, 2.6) + K.pole(94, -54, 30, 2.6);
      s += SA.sheet(ctx, [[6, -82], [100, -84], [98, -100], [10, -98]], true);
      s += K.knot(12, -82, 2.6, 2) + K.knot(94, -83, 2.6, 2) + K.hornSkull(53, -96, 0.75, 10);
      ctx.top(-106);
      // 一捆干草 + 拴狼的木桩
      s += C.path(C.wob(ctx, [[106, -60], [130, -60], [128, -70], [108, -70]], 0.6), P.thatch, 1.1) + K.texThatch(ctx, 0, 0, 0, 0);
      s += C.line('M110 -65h16', 0.8, 0.6) + K.knot(118, -64, 22, 1);
      // 圈内
      s += wolf(36, -40, 1.1, 1) + wolf(84, -34, 1.2, -1);
      s += C.path(C.poly([[56, -24], [72, -24], [74, -29], [54, -29]]), P.timber, 1.1);
      s += C.line('M58 -28l4 -2M63 -27.5l5 -1.5M66 -29l3 1', 1.6, 1, P.bone);
      // 围栏：后侧左右两段侧栏 + 前排一长段（中间留栅门）
      s += HB.fenceSide(ctx, 4, -10, 50, 12) + HB.fenceSide(ctx, 140, -10, 50, 12);
      s += HB.fenceRow(ctx, 4, 58, -6, 13) + HB.fenceRow(ctx, 86, 142, -6, 13);
      s += K.pole(58, -6, 18, 3.4, P.dark) + K.pole(86, -6, 18, 3.4, P.dark) + K.skull(58, -27, 0.6) + K.skull(86, -27, 0.6);
      var gate = 'M60 -8L70 -16M60 -16L70 -8M60 -12H70';
      s += C.line(gate, 2.2) + C.line(gate, 0.9, 1, P.wood);
      return s;
    }
  });

  var API = { S: S, dummy: dummy, ring: ring, menhir: menhir, wolf: wolf };
  root.TownArtWO_specialB = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
