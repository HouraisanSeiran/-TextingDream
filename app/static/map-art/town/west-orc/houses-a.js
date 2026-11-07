/*
 * 织梦 · 兽人族民居 A 组（01–05）（美术样板，尚未接入游戏）
 * 局部坐标：x 0..w*48，y = 0 为占地前沿，向上为负。每种 draw(ctx, v) 返回 svg 片段，v.i = 变体 1..3。
 * 浏览器挂 window.TownArtWO_housesA；Node 用 module.exports。依赖 core.js、parts.js、forms.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWO_core;
  var K = isNode ? require('./parts.js') : root.TownArtWO_parts;
  var F = isNode ? require('./forms.js') : root.TownArtWO_forms;
  var P = C.PAL, f = C.f;

  /** 拉索：从 (x0,y0) 到地桩 (x1,y1) */
  function guy(x0, y0, x1, y1) {
    return C.line('M' + f(x0) + ' ' + f(y0) + 'L' + f(x1) + ' ' + f(y1), 0.8, 0.8) + C.path(C.rectD(x1 - 1, y1 - 3, 2, 3.6), P.timber, 0.7);
  }
  /** 帐门：拱门 + 卷起门帘 + 门楣獠牙 */
  function tentDoor(ctx, cx, yb, w, h, deco) {
    var s = F.door(ctx, cx, yb, w, h, 'arch', true);
    if (deco === 'tusk') s += K.tuskArch(cx, yb - h + 1, w * 0.5);
    else if (deco === 'skull') s += K.skull(cx, yb - h - 2.5, 0.6);
    else if (deco === 'horn') s += K.hornSkull(cx, yb - h - 2.5, 0.55, 7);
    return s;
  }

  var T = [];

  // 01 圆顶兽皮帐：拼缝兽皮蒙在弯木骨上，绳箍压皮，顶开烟孔
  T.push({
    n: 1, kind: 'house_yurt', name: '圆顶兽皮帐', fp: [1, 1], roof: 'none',
    tags: ['one_storey', 'hide', 'tent', 'dome'], note: '圆顶兽皮帐，RoofId 无对应，写 none',
    draw: function (ctx, v) {
      var s = '';
      if (v.i === 3) { // 双顶：后侧小帐 + 前侧主帐
        s += F.dome(ctx, 37, -30, 9, 7, 17, { mat: 'hide2', ribs: 3, bands: 1, smoke: false });
        s += F.dome(ctx, 20, -21, 16, 12, 28, { mat: 'hide', ribs: 4 });
        s += tentDoor(ctx, 20, -9, 9, 13, 'tusk');
        s += guy(6, -22, 3, -5) + guy(35, -18, 44, -4);
        return s;
      }
      var tall = v.i === 2, h = tall ? 38 : 30, rx = tall ? 17 : 19;
      s += F.dome(ctx, 24, -22, rx, 14, h, { mat: tall ? 'hide2' : 'hide', ribs: tall ? 4 : 5, bands: tall ? 3 : 2 });
      s += tentDoor(ctx, 24, -8, 10, 14, tall ? 'horn' : 'tusk');
      s += guy(24 - rx + 1, -24, 3, -5) + guy(24 + rx - 1, -24, 45, -5);
      if (tall) s += K.banner(ctx, 42, -6, 40, P.rust, -1);
      else s += K.boneString(ctx, 9, -30, 22, -45, 3);
      return s;
    }
  });

  // 02 长条兽皮帐：A 字形长帐，皮面拖到地，两端交叉撑杆
  T.push({
    n: 2, kind: 'house_longtent', name: '长条兽皮帐', fp: [2, 1], roof: 'gable_thatch',
    tags: ['one_storey', 'hide', 'tent'], note: '兽皮 A 字长帐，最接近 gable，屋面是兽皮不是茅草',
    draw: function (ctx, v) {
      var s = '', x0 = 8, x1 = 88, yb = -6, wall = v.i === 3 ? 10 : 0;
      s += C.groundShadow(x0, x1, yb, -42);
      if (wall) s += F.facade(ctx, x0, x1, yb, wall, 'vlogs');
      var r = F.roofLong(ctx, { x0: x0, x1: x1, yE: yb - wall, Dp: 32, R: v.i === 3 ? 12 : 15, mat: 'hide', ov: 2, hip: v.i === 2 ? 0.9 : 0, lean: v.i === 2 ? 2 : 0 });
      s += r.svg;
      // 两端交叉撑杆（伸出脊线）
      [r.L, r.Rt].forEach(function (p) {
        s += C.line('M' + f(p[0] - 5) + ' ' + f(p[1] - 7) + 'L' + f(p[0] + 3) + ' ' + f(p[1] + 3) + 'M' + f(p[0] + 5) + ' ' + f(p[1] - 7) + 'L' + f(p[0] - 3) + ' ' + f(p[1] + 3), 2.2) +
          K.knot(p[0], p[1] - 1, 3, 2);
      });
      ctx.top(r.yR - 8);
      // 前坡上开门：三角门洞（墙高时开在墙上）
      if (wall) s += tentDoor(ctx, 48, yb, 11, wall + 4, 'skull');
      else s += F.door(ctx, 48, yb, 13, 15, 'tri', true) + K.skull(48, yb - 19, 0.55);
      s += K.boneString(ctx, 16, yb - wall - 8, 38, yb - wall - 6, 4) + K.boneString(ctx, 58, yb - wall - 6, 80, yb - wall - 8, 4);
      if (v.i === 2) s += F.dome(ctx, 76, yb - 22, 6, 4, 6, { mat: 'hide2', ribs: 2, bands: 0, smoke: false }) + C.line('M76 ' + f(yb - 28) + 'v-6', 1.6, 1, P.dark);
      else s += K.weapon('spear', 4, -30, 26);
      return s;
    }
  });

  // 03 粗石圆屋：粗石垒圆墙 + 圆锥顶，顶尖挂长角兽头骨
  T.push({
    n: 3, kind: 'house_roundstone', name: '粗石圆屋', fp: [1, 1], roof: 'gable_thatch',
    tags: ['one_storey', 'rubble', 'round'], note: '圆锥茅草/兽皮顶，最接近 gable_thatch',
    draw: function (ctx, v) {
      var s = '', cx = 24, yc = -22;
      if (v.i === 3) { // 矮宽圆墙 + 草皮圆顶 + 石烟囱
        s += F.cylinder(ctx, cx, yc, 19, 14, 12, 'rubble');
        s += F.dome(ctx, cx, yc - 12, 20, 14, 18, { mat: 'turf', ribs: 0, bands: 0, smoke: false });
        s += C.face(ctx, C.wob(ctx, [[30, -40], [37, -40], [36, -55], [31, -55]], 0.6), P.stone2, K.texRubble(ctx, 29, -56, 9, 17), 1.3);
        ctx.top(-56);
        s += F.door(ctx, cx - 3, -8, 9, 11, 'rect', false) + C.line('M' + f(cx - 8.5) + ' -19.5h11', 2.4, 1, P.dark);
        return s + K.horn(cx + 8, -14, 6, 1, 0.6) + K.horn(cx + 8, -14, 6, -1, 0.6);
      }
      s += F.cylinder(ctx, cx, yc, 17, 13, 16, 'rubble');
      s += F.door(ctx, cx, -9, 9, 12, 'rect', false) + C.line('M' + f(cx - 6) + ' -21h12', 2.4, 1, P.dark);
      if (v.i === 2) { // 两层：兽皮大锥 + 茅草小尖
        s += F.cone(ctx, cx, yc - 16, 21, 15, 18, 'hide', -1);
        s += F.cone(ctx, cx - 1, yc - 30, 10, 7, 16, 'thatch', 1);
        s += K.knot(cx - 1, yc - 32, 6, 2);
        s += K.banner(ctx, cx, yc - 46, 12, P.moss, 1);
      } else {
        s += F.cone(ctx, cx, yc - 16, 21, 15, 28, 'thatch', 1.5);
        s += K.hornSkull(cx + 1.5, yc - 46, 0.7, 9);
        ctx.top(yc - 54);
      }
      return s;
    }
  });

  /** 兽皮补丁（缝在茅草顶上），中心 (cx, cy) */
  function patch(ctx, cx, cy, w, h, tone) {
    var x0 = cx - w / 2, y0 = cy - h / 2, st = '';
    var d = C.wob(ctx, [[x0, y0], [x0 + w, y0], [x0 + w, y0 + h], [x0, y0 + h]], 0.7);
    for (var x = x0 + 1.5; x < x0 + w - 1; x += 2.6) st += 'M' + f(x) + ' ' + f(y0 + 0.4) + 'v1.4M' + f(x) + ' ' + f(y0 + h - 1.8) + 'v1.4';
    return C.path(d, tone || P.hide, 1) + C.line(st, 0.6, 0.8, P.bone2);
  }
  /** 晾皮架：两根杆 + 横杆 + 绷开的兽皮；左下 (x, yb) */
  function rack(ctx, x, yb, w, h) {
    var s = K.pole(x + 1, yb, h, 2) + K.pole(x + w - 1, yb, h, 2) + C.line('M' + f(x - 1) + ' ' + f(yb - h + 1.5) + 'H' + f(x + w + 1), 1.8, 1, P.timber);
    var hx0 = x + 3, hx1 = x + w - 3, ht = yb - h + 4, hb = yb - h * 0.3;
    var d = 'M' + f(hx0) + ' ' + f(ht) + 'Q' + f((hx0 + hx1) / 2) + ' ' + f(ht - 2) + ' ' + f(hx1) + ' ' + f(ht) + 'L' + f(hx1 - 1) + ' ' + f(hb) +
      'Q' + f((hx0 + hx1) / 2) + ' ' + f(hb + 3) + ' ' + f(hx0 + 1) + ' ' + f(hb) + 'Z';
    s += C.path(d, P.hide3, 1.1) + C.line('M' + f(hx0) + ' ' + f(ht) + 'L' + f(x + 1) + ' ' + f(ht - 1) + 'M' + f(hx1) + ' ' + f(ht) + 'L' + f(x + w - 1) + ' ' + f(ht - 1) +
      'M' + f(hx0 + 1) + ' ' + f(hb) + 'L' + f(x + 1) + ' ' + f(hb + 1) + 'M' + f(hx1 - 1) + ' ' + f(hb) + 'L' + f(x + w - 1) + ' ' + f(hb + 1), 0.7, 0.9);
    ctx.top(yb - h - 1);
    return s;
  }
  /** 三角下沉入口：底 yb，中心 cx，宽 w，高 h，内画三级台阶 */
  function pitDoor(cx, yb, w, h) {
    var s = C.path(C.poly([[cx - w / 2, yb], [cx, yb - h], [cx + w / 2, yb]]), P.hole, 1.3), st = '';
    for (var i = 1; i <= 3; i++) { var y = yb - h * i * 0.2, ww = w / 2 * (1 - i * 0.2) - 1.2; st += 'M' + f(cx - ww) + ' ' + f(y) + 'H' + f(cx + ww); }
    return s + C.line(st, 1.1, 0.85, P.soil);
  }
  /** 一圈压边石（椭圆前半圈） */
  function rimStones(ctx, cx, yc, rx, ry) {
    var s = '';
    for (var a = 0.15; a < Math.PI - 0.1; a += 0.32) s += C.ell(cx + Math.cos(a) * rx, yc + Math.sin(a) * ry - 1.6, 2.6, 1.6, ctx.pick([P.stone, P.stone2, P.stone3]), 0.8);
    return s;
  }

  // 04 半地穴屋：屋身半埋在土里，草皮土丘围着一圈压边石，低矮的皮顶 / 草皮顶，三角下沉门
  T.push({
    n: 4, kind: 'house_pit', name: '半地穴屋', fp: [1, 1], roof: 'none',
    tags: ['one_storey', 'sunken', 'turf', 'hide'], note: '半地穴，土丘上盖兽皮锥顶或草皮顶，RoofId 无对应写 none',
    draw: function (ctx, v) {
      var s = '';
      s += F.dome(ctx, 24, -21, 21, 14, v.i === 2 ? 9 : 6, { mat: 'turf', ribs: 0, bands: 0, smoke: false });
      if (v.i === 1) {
        s += F.cone(ctx, 24, -25, 15, 10, 19, 'hide', 1);
        s += K.knot(25, -40, 4, 2);
      } else if (v.i === 2) { // 平缓草皮顶 + 一根兽皮裹的烟道，顶插长角
        s += F.dome(ctx, 24, -27, 16, 10, 10, { mat: 'turf', ribs: 0, bands: 0, smoke: false });
        s += C.face(ctx, C.wob(ctx, [[30, -36], [35, -36], [35, -50], [30, -50]], 0.5), P.hide2, K.texHide(ctx, 29, -51, 7, 16, K.HIDE_D), 1.2);
        s += K.knot(32.5, -44, 5, 2) + K.horn(32.5, -50, 6, -1, 1) + K.horn(32.5, -50, 6, 1, 1);
        ctx.top(-56);
      } else { // 撑杆帐从坑里立起：杆头伸出锥顶，挂头骨
        s += F.cone(ctx, 24, -25, 14, 9, 30, 'hide2', -1);
        s += C.line('M17 -63L24 -53M31 -63L24 -53M24 -65V-53', 1.8) + C.line('M17 -63L24 -53M31 -63L24 -53M24 -65V-53', 0.7, 1, P.wood);
        s += K.knot(24, -54, 6, 2) + K.skull(31, -43, 0.55);
        ctx.top(-66);
      }
      s += rimStones(ctx, 24, -21, 21, 14);
      s += F.roofFront(ctx, { x0: 17, x1: 31, yE: -5, R: 11, Dp: 9, mat: 'turf', ov: 1.5 }).svg;
      s += pitDoor(24, -5, 11, 10);
      return s;
    }
  });

  // 05 原木长屋：横叠原木墙，茅草顶缝兽皮补丁，脊端交叉木刻兽角
  T.push({
    n: 5, kind: 'house_longhouse', name: '原木长屋', fp: [2, 1], roof: 'gable_thatch',
    tags: ['one_storey', 'logs', 'thatch', 'hide'], note: '茅草与兽皮混搭的长坡顶',
    draw: function (ctx, v) {
      var s = '', x0 = v.i === 3 ? 18 : 10, x1 = 83, yb = -5, wh = 15;
      s += C.groundShadow(x0, x1 + 5, yb, -40);
      if (v.i === 3) {
        s += F.facade(ctx, x0, x1, yb, 6, 'rubble') + F.facade(ctx, x0, x1, yb - 6, wh - 4, 'vlogs');
        s += rack(ctx, 2, -3, 14, 22);
      } else s += F.facade(ctx, x0, x1, yb, wh, 'logs');
      s += F.sideStrip(ctx, x1, yb, v.i === 3 ? wh + 2 : wh, 6, 5);
      var yE = yb - (v.i === 3 ? wh + 2 : wh);
      var r = F.roofLong(ctx, { x0: x0, x1: x1 + 4, yE: yE, Dp: 26, R: 12, mat: v.i === 3 ? 'hide' : 'thatch', ov: 3, hip: v.i === 3 ? 0.7 : 0, lean: v.i === 1 ? -1.5 : 0 });
      s += r.svg;
      if (v.i !== 3) {
        s += patch(ctx, x0 + 20, yE - 9, 11, 7) + patch(ctx, x0 + 52, yE - 15, 9, 6, P.hide2) + patch(ctx, x0 + 66, yE - 6, 8, 6);
        s += K.hornSkull(r.L[0] + 2, r.L[1] - 3, 0.6, 7);
        s += C.line('M' + f(r.Rt[0] - 4) + ' ' + f(r.Rt[1] - 7) + 'L' + f(r.Rt[0] + 3) + ' ' + f(r.Rt[1] + 2) + 'M' + f(r.Rt[0] + 4) + ' ' + f(r.Rt[1] - 7) + 'L' + f(r.Rt[0] - 3) + ' ' + f(r.Rt[1] + 2), 2.2);
        ctx.top(r.yR - 9);
      } else {
        s += C.rect(36, yE - 15, 6, 4, P.hole, 1) + C.rect(62, yE - 15, 6, 4, P.hole, 1);
      }
      var dx = v.i === 3 ? 52 : 30;
      s += F.door(ctx, dx, yb, 10, 12, 'rect', true) + K.tuskArch(dx, yb - 12, 5);
      s += C.rect(dx + 22, yb - 11, 7, 5, P.hole, 1.1) + C.path(C.poly([[dx + 21.5, yb - 11.5], [dx + 29.5, yb - 11.5], [dx + 28, yb - 8.5], [dx + 22.5, yb - 8]]), P.hide2, 0.8);
      if (v.i === 2) { // 正中加一座山墙朝前的门廊
        s += K.pole(39, -3, 14, 2.4) + K.pole(57, -3, 14, 2.4);
        s += F.roofFront(ctx, { x0: 37, x1: 59, yE: -17, R: 9, Dp: 12, mat: 'hide', ov: 2 }).svg;
        s += K.banner(ctx, 91, -2, 38, P.rust, -1);
      } else if (v.i === 1) s += K.weapon('axe', 72, yb - 13, 10);
      return s;
    }
  });

  var API = { T: T, guy: guy, tentDoor: tentDoor, patch: patch, rack: rack, pitDoor: pitDoor, rimStones: rimStones };
  root.TownArtWO_housesA = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
