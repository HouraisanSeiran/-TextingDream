/*
 * 织梦 · 兽人族民居 B 组（06–10）（美术样板，尚未接入游戏）
 * 局部坐标：x 0..w*48，y = 0 为占地前沿，向上为负。每种 draw(ctx, v) 返回 svg 片段，v.i = 变体 1..3。
 * 浏览器挂 window.TownArtWO_housesB；Node 用 module.exports。依赖 core.js、parts.js、forms.js、houses-a.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWO_core;
  var K = isNode ? require('./parts.js') : root.TownArtWO_parts;
  var F = isNode ? require('./forms.js') : root.TownArtWO_forms;
  var HA = isNode ? require('./houses-a.js') : root.TownArtWO_housesA;
  var P = C.PAL, f = C.f;

  /** 弯骨肋：从 (x, yb) 拱起到 (x2, yb)，顶高 h，骨白粗线 */
  function rib(x, yb, x2, h) {
    var d = 'M' + f(x) + ' ' + f(yb) + 'Q' + f((x + x2) / 2) + ' ' + f(yb - h * 1.9) + ' ' + f(x2) + ' ' + f(yb);
    return C.line(d, 2.8) + C.line(d, 1.3, 1, P.bone);
  }
  /** 一段尖桩矮栅（畜栏）：x0..x1，底 yb，桩高 h */
  function fenceRow(ctx, x0, x1, yb, h) {
    var s = '';
    for (var x = x0; x < x1 - 2; x += 4.4) s += K.stake(x, yb, 3.6, h + ctx.rnd(-1.5, 1.5), ctx.pick([P.wood, '#bf9a60', '#b48e58']), 0.8);
    return s + C.line('M' + f(x0) + ' ' + f(yb - h * 0.55) + 'H' + f(x1), 1.4, 1, P.timber) + C.line('M' + f(x0) + ' ' + f(yb - h * 0.55) + 'H' + f(x1), 0.5, 0.8);
  }
  /** 侧向矮栅（向上退的斜段）：底 (x, yb)，进深 dp */
  function fenceSide(ctx, x, yb, dp, h) {
    var s = '', n = Math.round(dp / 5);
    for (var i = n; i >= 0; i--) { var yy = yb - i * dp / n; s += K.stake(x - 1.6, yy, 3.2, h, P.timber, 0.8); }
    return s + C.line('M' + f(x) + ' ' + f(yb - h * 0.55) + 'L' + f(x) + ' ' + f(yb - dp - h * 0.55), 1.3, 1, P.dark);
  }
  /** 一头卧着的野猪（侧影，朝左） */
  function boar(cx, yb, s) {
    s = s || 1;
    var d = 'M' + f(cx - 7 * s) + ' ' + f(yb - 3 * s) + 'Q' + f(cx - 6 * s) + ' ' + f(yb - 8 * s) + ' ' + f(cx) + ' ' + f(yb - 8 * s) + 'Q' + f(cx + 6 * s) + ' ' + f(yb - 8 * s) + ' ' + f(cx + 6.5 * s) + ' ' + f(yb - 3 * s) +
      'L' + f(cx + 6 * s) + ' ' + f(yb) + 'H' + f(cx - 9 * s) + 'L' + f(cx - 10 * s) + ' ' + f(yb - 2.5 * s) + 'Z';
    return C.path(d, P.hide2, 1) + C.line('M' + f(cx - 3 * s) + ' ' + f(yb - 8 * s) + 'l1 -1.6l1 1.4l1 -1.6l1 1.6', 0.8, 0.9) +
      C.circ(cx - 6.5 * s, yb - 4.2 * s, 0.6 * s, P.hole, 0) + K.tusk(cx - 9 * s, yb - 1.4 * s, 2.6 * s, -1);
  }

  var T = [];

  // 06 骨架棚屋：巨兽肋骨拱成骨架，搭兽皮半蒙，门两侧立獠牙
  T.push({
    n: 6, kind: 'house_bonehut', name: '骨架棚屋', fp: [1, 1], roof: 'none',
    tags: ['one_storey', 'bone', 'hide', 'tent'], note: '巨兽骨架拱棚，RoofId 无对应写 none',
    draw: function (ctx, v) {
      var s = '', narrow = v.i === 2;
      var cx = 24, yc = -22, rx = narrow ? 14 : 18, ry = 13, h = narrow ? 34 : 26;
      s += F.dome(ctx, cx, yc, rx, ry, h, { mat: v.i === 3 ? 'hide2' : 'hide', ribs: 3, bands: 0, smoke: v.i !== 3 });
      // 外露的肋骨（前半圈，逐根由后往前）
      var n = 4;
      for (var i = 0; i < n; i++) {
        var t = (i + 0.5) / n, yy = yc - ry * 0.6 + ry * 1.3 * t, half = rx * Math.sqrt(1 - Math.pow(2 * t - 1, 2) * 0.6);
        s += rib(cx - half, yy, cx + half, h * (0.55 + 0.35 * Math.sin(Math.PI * t)) * 0.55);
      }
      if (v.i === 3) { // 头骨冠：最前一根肋上压一颗长角兽头骨
        s += K.hornSkull(cx, yc - h + 2, 0.9, 11);
        ctx.top(yc - h - 10);
      }
      s += F.door(ctx, cx, -8, 10, 13, 'arch', v.i !== 1);
      s += K.tusk(cx - 7, -6, 9, -1) + K.tusk(cx + 7, -6, 9, 1);
      if (v.i === 1) s += K.boneString(ctx, cx - rx + 2, yc - 4, cx - 4, -24, 3);
      return s;
    }
  });

  // 07 高脚瞭望屋：四根原木高脚撑起的小屋，绑扎斜撑，爬梯，顶插战旗
  T.push({
    n: 7, kind: 'house_stilt', name: '高脚瞭望屋', fp: [1, 1], roof: 'gable_thatch',
    tags: ['stilt', 'logs', 'thatch', 'lookout'], note: '高脚屋，顶为茅草或兽皮四坡',
    draw: function (ctx, v) {
      var s = '', x0 = 8, x1 = 40, legH = v.i === 2 ? 30 : 22, fy = -6 - legH, bh = 15;
      s += C.groundShadow(x0, x1, -6, -40);
      // 后排两根腿 + 前排两根腿 + 交叉斜撑
      s += K.pole(x0 + 5, -20, legH - 14, 3, P.dark) + K.pole(x1 - 5, -20, legH - 14, 3, P.dark);
      s += K.pole(x0 + 2, -4, legH - 2, 3.4) + K.pole(x1 - 2, -4, legH - 2, 3.4);
      s += C.line('M' + f(x0 + 2) + ' ' + f(-6) + 'L' + f(x1 - 2) + ' ' + f(fy + 4) + 'M' + f(x1 - 2) + ' ' + f(-6) + 'L' + f(x0 + 2) + ' ' + f(fy + 4), 1.8, 1, P.timber);
      s += K.knot(x0 + 2, fy + 3, 3.4, 2) + K.knot(x1 - 2, fy + 3, 3.4, 2);
      // 平台 + 屋身
      s += C.path(C.rectD(x0 - 3, fy - 3, x1 - x0 + 6, 4), P.timber, 1.2);
      var wallMat = v.i === 3 ? 'hide' : 'vlogs';
      s += F.facade(ctx, x0, x1, fy - 3, bh, wallMat);
      s += F.door(ctx, 24, fy - 3, 7, 10, 'rect', false) + K.skull(24, fy - 16.5, 0.5);
      // 爬梯（斜靠在右前方）
      var lx0 = 36, lx1 = 44;
      s += C.line('M' + f(lx0) + ' ' + f(fy) + 'L' + f(lx1 - 3) + ' -3M' + f(lx0 + 4) + ' ' + f(fy) + 'L' + f(lx1 + 1) + ' -3', 1.4, 1, P.dark);
      var rungs = '';
      for (var k = 1; k < 6; k++) { var t = k / 6, ya = fy + (-3 - fy) * t, xa = lx0 + (lx1 - 3 - lx0) * t; rungs += 'M' + f(xa) + ' ' + f(ya) + 'h4'; }
      s += C.line(rungs, 1.2, 1, P.timber);
      var yE = fy - 3 - bh;
      if (v.i === 3) { // 敞开的瞭望台：兽皮锥顶
        s += F.cone(ctx, 24, yE + 2, 21, 9, 18, 'hide', 1);
        s += K.horn(24, yE - 15, 6, -1, 1.2) + K.horn(24, yE - 15, 6, 1, 1.2);
        ctx.top(yE - 22);
      } else {
        var r = F.roofLong(ctx, { x0: x0, x1: x1, yE: yE, Dp: 18, R: 8, mat: 'thatch', ov: 3, hip: 0.85, lean: v.i === 1 ? 1.5 : -1 });
        s += r.svg + K.banner(ctx, (r.L[0] + r.Rt[0]) / 2, r.yR + 1, 18, v.i === 2 ? P.moss : P.rust, 1);
      }
      return s;
    }
  });

  // 08 带畜栏的帐屋：圆顶帐 + 前侧尖桩矮栅畜栏，栏里卧一头野猪
  T.push({
    n: 8, kind: 'house_tentpen', name: '带畜栏的帐屋', fp: [2, 2], roof: 'none',
    tags: ['one_storey', 'hide', 'tent', 'pen', 'livestock'], note: '圆顶兽皮帐 + 尖桩畜栏，RoofId 无对应写 none',
    draw: function (ctx, v) {
      var s = '', left = v.i !== 2; // 帐在左/右
      var tx = left ? 30 : 66, px0 = left ? 52 : 6, px1 = left ? 92 : 46;
      if (v.i === 3) s += F.cylinder(ctx, tx, -60, 20, 14, 10, 'logs') + F.cone(ctx, tx, -70, 23, 16, 30, 'thatch', 1.5);
      else s += F.dome(ctx, tx, -60, 22, 16, 36, { mat: 'hide', ribs: 5, bands: 2 });
      s += HA.tentDoor(ctx, tx, -45, 11, 14, 'horn');
      // 畜栏：后栅 → 侧栅 → 野猪 → 前栅
      s += fenceRow(ctx, px0, px1, -40, 9) + fenceSide(ctx, px0, -6, 34, 9) + fenceSide(ctx, px1, -6, 34, 9);
      s += boar(px0 + 18, -22, 1) + (v.i === 3 ? boar(px0 + 28, -14, 0.8) : '');
      s += C.path(C.ellD(px0 + 30, -30, 5, 2), P.thatch2, 0.8); // 草料
      s += fenceRow(ctx, px0, px0 + 14, -6, 10) + fenceRow(ctx, px0 + 24, px1, -6, 10);
      s += C.line('M' + f(px0 + 14) + ' -9L' + f(px0 + 22) + ' -15', 2, 1, P.timber); // 半开的栏门
      s += K.firepit(ctx, left ? 22 : 74, -18, 6, v.i !== 1);
      if (v.i === 1) s += HA.rack(ctx, 6, -6, 14, 20);
      else s += K.totem(ctx, left ? 8 : 86, -10, 6, 34, 'skull');
      return s;
    }
  });

  // 09 皮草混顶小屋：粗石矮墙 + 茅草与兽皮拼接的山墙朝前坡顶，门楣交叉獠牙
  T.push({
    n: 9, kind: 'house_mixhut', name: '皮草混顶小屋', fp: [1, 1], roof: 'gable_thatch',
    tags: ['one_storey', 'rubble', 'thatch', 'hide'], note: '山墙朝前，左坡茅草、右坡兽皮',
    draw: function (ctx, v) {
      var s = '', x0 = 7, x1 = 41, yb = -6, wh = v.i === 2 ? 16 : 13;
      s += C.groundShadow(x0, x1, yb, -38);
      s += F.facade(ctx, x0, x1, yb, wh, v.i === 3 ? 'vlogs' : 'rubble');
      var r = F.roofFront(ctx, { x0: x0, x1: x1, yE: yb - wh, R: v.i === 2 ? 20 : 16, Dp: 18, mat: 'thatch', ov: 3, wallMat: v.i === 3 ? 'hide' : 'vlogs', lean: v.i === 1 ? -1 : 1 });
      s += r.svg;
      // 右坡盖一大块兽皮
      var ap = r.apex;
      s += C.path(C.wob(ctx, [[ap[0] + 1, ap[1] - 3], [ap[0] + 1, ap[1] - 14], [x1 + 2, yb - wh - 13], [x1 + 3, yb - wh + 2]], 0.6), P.hide, 1.1);
      s += C.line('M' + f(ap[0] + 6) + ' ' + f(ap[1] - 6) + 'l2 1M' + f(ap[0] + 10) + ' ' + f(ap[1] - 3) + 'l2 1M' + f(ap[0] + 13) + ' ' + f(ap[1]) + 'l2 1', 0.7, 0.8, P.bone2);
      s += K.knot(x1 + 2, yb - wh - 3, 3, 2);
      s += F.door(ctx, 24, yb, 9, 11, 'rect', true) + K.tuskArch(24, yb - 11, 5);
      if (v.i === 2) s += K.hornSkull(ap[0], ap[1] + 6, 0.6, 7);
      else if (v.i === 3) s += K.weapon('club', 36, yb - 12, 10);
      else s += K.boneString(ctx, x0 + 1, yb - wh, 17, yb - wh + 1, 2);
      return s;
    }
  });

  // 10 图腾院落帐：方形兽皮帐 + 侧院图腾柱与篝火，两角挂战旗
  T.push({
    n: 10, kind: 'house_totemyard', name: '图腾院落帐', fp: [2, 1], roof: 'monopitch',
    tags: ['one_storey', 'hide', 'tent', 'totem', 'firepit'], note: '单坡兽皮帐，前檐用两根撑杆支起',
    draw: function (ctx, v) {
      var s = '', tl = v.i === 2 ? 50 : 6, tr = tl + 40, yb = -6, wh = 12;
      s += C.groundShadow(tl, tr, yb, -40);
      s += F.facade(ctx, tl, tr, yb, wh, 'hide');
      // 单坡：前檐高、后沿低（屏幕上为一块前低后高的平行四边形，撑杆外伸）
      var yE = yb - wh - 4, back = yE - 22;
      var d = C.wob(ctx, [[tl - 4, yE + 2], [tr + 4, yE + 2], [tr + 2, back], [tl - 2, back]], 0.8);
      s += C.face(ctx, d, P.hide, K.texHide(ctx, tl - 4, back - 2, tr - tl + 8, yE - back + 6) + C.rect(tr - 8, back, 14, 30, P.hide2, 0, 0.4), 1.7);
      s += K.pole(tl - 1, yb + 2, wh + 6, 2.4) + K.pole(tr + 1, yb + 2, wh + 6, 2.4);
      ctx.top(back - 2);
      s += F.door(ctx, (tl + tr) / 2, yb, 10, 11, 'rect', true) + K.skull((tl + tr) / 2, yb - 14, 0.55);
      // 侧院
      var yx = v.i === 2 ? 4 : 52, yx1 = yx + 40;
      s += K.firepit(ctx, yx + 22, -14, 7, true);
      s += K.totem(ctx, yx + 4, -24, 7, v.i === 3 ? 50 : 40, v.i === 3 ? 'wings' : 'skull');
      s += K.banner(ctx, yx1 - 4, -4, 34, v.i === 1 ? P.rust : P.moss, -1);
      if (v.i === 3) s += HA.rack(ctx, yx + 24, -26, 14, 18);
      return s;
    }
  });

  var API = { T: T, rib: rib, fenceRow: fenceRow, fenceSide: fenceSide, boar: boar };
  root.TownArtWO_housesB = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
