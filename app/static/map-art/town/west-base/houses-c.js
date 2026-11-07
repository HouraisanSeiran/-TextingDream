/*
 * 织梦 · 西式民居 C 组（11–16）（美术样板，尚未接入游戏）
 * 浏览器挂 window.TownArtWB_housesC；Node 用 module.exports。依赖 common.js、houses-a.js、houses-b.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./common.js') : root.TownArtWB_common;
  var HA = isNode ? require('./houses-a.js') : root.TownArtWB_housesA;
  var HB = isNode ? require('./houses-b.js') : root.TownArtWB_housesB;
  var P = C.PAL, f = C.f, floors = HA.floors, centers = HA.centers, wrow = HA.wrow, shifted = HB.shifted;
  var T = [];

  /** 阶梯山墙（佛兰德式跌级山墙）：盖在正山墙之上，n 级 */
  function crowStep(ctx, x0, x1, yE, R, n) {
    var xc = (x0 + x1) / 2, sw = (xc - x0) / (n + 0.5), rise = R / n, L = [[x0 - 1.5, yE]], i;
    for (i = 0; i < n; i++) { L.push([x0 - 1.5 + i * sw, yE - (i + 1) * rise]); L.push([x0 - 1.5 + (i + 1) * sw, yE - (i + 1) * rise]); }
    L.push([xc - sw / 2, yE - R - rise]);
    var Rt = L.map(function (p) { return [2 * xc - p[0], p[1]]; }).reverse();
    var pts = L.concat([[xc + sw / 2, yE - R - rise]]).concat(Rt.slice(1));
    pts.splice(L.length + 1, 0);
    var d = C.poly(pts), s = C.face(ctx, d, P.stone, C.texAshlar(ctx, x0 - 2, yE - R - rise, x1 - x0 + 4, R + rise, 5, 10) +
      C.rect(xc, yE - R - rise, xc - x0 + 2, R + rise, P.shadow, 0, 0.1), 1.6);
    var cap = '';
    for (i = 0; i < n; i++) {
      var yy = yE - (i + 1) * rise;
      cap += C.rect(x0 - 2.5 + i * sw, yy - 1.6, sw + 1, 2.2, P.stone2, 0.9) + C.rect(2 * xc - (x0 - 1.5 + (i + 1) * sw) - 1, yy - 1.6, sw + 1, 2.2, P.stone2, 0.9);
    }
    cap += C.rect(xc - sw / 2 - 1, yE - R - rise - 1.6, sw + 2, 2.2, P.stone2, 0.9);
    ctx.top(yE - R - rise - 3);
    return s + cap;
  }
  /** 草垛 */
  function haystack(ctx, cx, yb, r) {
    var d = 'M' + f(cx - r) + ' ' + f(yb) + 'Q' + f(cx - r) + ' ' + f(yb - r * 1.5) + ' ' + f(cx) + ' ' + f(yb - r * 1.6) + 'Q' + f(cx + r) + ' ' + f(yb - r * 1.5) + ' ' + f(cx + r) + ' ' + f(yb) + 'Z';
    var t = '';
    for (var i = 0; i < 6; i++) { var x = cx - r * 0.8 + i * r * 0.32; t += 'M' + f(x) + ' ' + f(yb - 1) + 'q' + f(r * 0.1) + ' ' + f(-r * 0.6) + ' ' + f(r * 0.05) + ' ' + f(-r * 1.1); }
    ctx.top(yb - r * 1.7);
    return C.face(ctx, d, P.thatch, C.line(t, 0.7, 0.55) + C.rect(cx + r * 0.2, yb - r * 2, r, r * 2, P.shadow, 0, 0.12), 1.4);
  }

  // 11 单坡木板屋：1×1，竖木板墙，单坡屋面（后高前低），铁皮烟管，门边长凳与雨水桶
  T.push({
    n: 11, kind: 'house_shack', name: '单坡木板屋', fp: [1, 1], roof: 'monopitch',
    tags: ['one_storey', 'plank', 'monopitch', 'stovepipe', 'rain_barrel'], note: '',
    draw: function (ctx, v) {
      var p = v.pal, s = '', fl = v.flip, x0 = 6, x1 = 42;
      s += C.groundShadow(x0, x1, 0, -40);
      var B = floors(ctx, x0, x1, [{ h: 19, mat: 'plank', fill: v.i === 3 ? '#b8956a' : P.wood }]);
      s += B.svg;
      s += C.door(ctx, fl ? 27 : 11, 0, 9, 15, 'plank', { fill: p.door });
      s += wrow(ctx, B.F[0], [fl ? 15 : 33], 'plain', 7, 6, {});
      var r = C.roofMono(ctx, { x0: x0, x1: x1, yE: B.yE, D: 40, R: 9, mat: v.i === 3 ? 'thatch' : 'shingle', ov: 3 });
      s += r.svg;
      if (v.i === 3) {
        // 变体 3：门前一架木柱小雨棚
        var dx0 = (fl ? 27 : 11) - 4, dx1 = dx0 + 17;
        s += C.line('M' + f(dx0 + 1) + ' 0V-17M' + f(dx1 - 1) + ' 0V-17', 2, 1, P.timber) + C.line('M' + f(dx0 + 1) + ' 0V-17M' + f(dx1 - 1) + ' 0V-17', 0.6, 0.6);
        s += C.face(ctx, C.poly([[dx0 - 1, -16], [dx1 + 1, -16], [dx1 + 1, -22], [dx0 - 1, -22]]), P.thatch, C.roofTex(ctx, 'thatch', dx0 - 1, -22, dx1 - dx0 + 2, 6, 'h'), 1.3);
      }
      // 铁烟管 + 小斗笠帽
      var px = fl ? 12 : 34;
      s += C.rect(px, r.yT - 8, 3, 18, P.slate2, 1) + C.path('M' + f(px - 2.5) + ' ' + f(r.yT - 8) + 'l4 -3l4 3Z', P.slate2, 1) + C.smoke(ctx, px + 1.5, r.yT - 12);
      // 长凳 + 雨水桶
      var bx = fl ? 8 : 24;
      s += C.rect(bx, -5, 11, 2, P.timber, 0.9) + C.line('M' + f(bx + 1.5) + ' -3V0M' + f(bx + 9.5) + ' -3V0', 1.2);
      s += HA.barrel(ctx, fl ? 37 : 3, 0);
      return s;
    }
  });

  // 12 双山墙联排：2×1，两户并肩、各自山墙朝街；左户红瓦木筋，右户青石板灰泥，高低错开
  T.push({
    n: 12, kind: 'house_row', name: '双山墙联排', fp: [2, 1], roof: 'gable_tile',
    tags: ['two_storey', 'gable_front', 'row_house', 'timber_frame', 'plaster', 'jetty'], note: '两户分别为红瓦与青石板',
    draw: function (ctx, v) {
      var p = v.pal, s = '', fl = v.flip;
      s += C.groundShadow(4, 92, 0, -42);
      var units = [
        { x0: 4, x1: 48, mat: 'timber', roof: 'tile', h: [21, 18], R: 20 },
        { x0: 48, x1: 92, mat: 'plaster', roof: 'slate', h: [20, 16], R: 24 }];
      if (fl) units.reverse(), units[0].x0 = 4, units[0].x1 = 48, units[1].x0 = 48, units[1].x1 = 92;
      units.forEach(function (u, k) {
        var B = floors(ctx, u.x0, u.x1, [
          { h: u.h[0], mat: u.mat === 'timber' ? 'ashlar' : 'plaster', fill: u.mat === 'timber' ? null : p.plaster, tex: { course: 5, joint: 10 } },
          { h: u.h[1], mat: u.mat, fill: p.plaster, jet: u.mat === 'timber' ? 2 : 0, band: true, tex: { pattern: k ? 'x' : 'v', spacing: 10 } }]
          // 变体 3：右户多一层
          .concat(v.i === 3 && k === 1 ? [{ h: 14, mat: u.mat, fill: p.plaster, band: true, tex: { pattern: 'k', spacing: 10 } }] : []));
        s += B.svg;
        if (B.F[2]) s += wrow(ctx, B.F[2], centers(B.x0 + 2, B.x1 - 2, 2), 'shutter', 6, 6, { shutter: p.shut });
        var mid = (u.x0 + u.x1) / 2;
        s += C.door(ctx, mid - (k ? 14 : -5), 0, 9, 15, k ? 'plank' : 'arch', { fill: k ? p.door : '#6e3b2c', step: true });
        s += C.win(ctx, mid + (k ? 3 : -15), -15, 9, 9, k ? 'shutter' : 'lead', { shutter: p.shut });
        s += wrow(ctx, B.F[1], centers(B.x0 + 2, B.x1 - 2, 2), u.mat === 'timber' ? 'lead' : 'shutter', 7, 8, { shutter: p.shut, box: v.i === k + 1 });
        var r = C.roofFront(ctx, { x0: B.x0, x1: B.x1, yE: B.yE, D: 40, R: u.R, mat: u.roof, ov: 2,
          gmat: u.mat, gfill: p.plaster, gtex: { pattern: 'k', spacing: 9 } });
        s += r.svg + C.win(ctx, mid - 3, B.yE - u.R * 0.55, 6, 6, 'plain');
      });
      s += C.rect(46.5, -38, 3, 38, P.stone2, 1);
      return s;
    }
  });

  // 13 跌级山墙石楼：1×2，三层方石城宅，正面佛兰德式阶梯山墙，青石板陡顶；底层石框拱门、上层十字窗
  T.push({
    n: 13, kind: 'house_stepgable', name: '跌级山墙石楼', fp: [1, 2], roof: 'steep_slate',
    tags: ['three_storey', 'ashlar', 'crow_step_gable', 'gable_front'], note: '阶梯山墙',
    draw: function (ctx, v) {
      var p = v.pal, s = '', x0 = 4, x1 = 44, v3 = v.i === 3;
      s += C.groundShadow(x0, x1, 0, -90);
      var stone = v3 ? '#d8c9a6' : null;
      var FL = [
        { h: 21, mat: 'ashlar', fill: stone, tex: { course: 6, joint: 12 } },
        { h: 18, mat: 'ashlar', fill: stone, band: true, tex: { course: 6, joint: 12 } }];
      // 变体 3：只有两层（矮一截）
      if (!v3) FL.push({ h: 16, mat: 'ashlar', fill: stone, band: true, tex: { course: 6, joint: 12 } });
      var B = floors(ctx, x0, x1, FL);
      s += B.svg;
      s += C.door(ctx, v.flip ? 26 : 12, 0, 10, 17, 'arch', { fill: p.door, surround: true, step: true });
      s += C.win(ctx, v.flip ? 11 : 29, -16, 7, 10, 'lead');
      s += wrow(ctx, B.F[1], [15, 33], 'lead', 7, 10, { frame: P.stone2, box: v.i === 2 });
      if (B.F[2]) s += wrow(ctx, B.F[2], [15, 33], 'lead', 6, 8, { frame: P.stone2 });
      // 屋脊沿进深，斜俯视下 96 px 进深压成约 54 px 屋面
      var r = C.roofFront(ctx, { x0: x0, x1: x1, yE: B.yE, D: 54, R: 30, mat: 'slate', ov: 1, gmat: 'ashlar' });
      s += r.svg + crowStep(ctx, x0, x1, B.yE, 30, 5);
      s += C.win(ctx, 21, B.yE - 18, 6, 8, 'slit') + C.win(ctx, 13, B.yE - 8, 5, 5, 'slit') + C.win(ctx, 30, B.yE - 8, 5, 5, 'slit');
      s += C.chimney(ctx, v.flip ? 9 : 32, B.yE - 50, B.yE - 66, 7, 'stone');
      return s;
    }
  });

  // 14 谷仓农屋：2×1，山墙朝街的大茅草谷仓式屋，木筋 + 竖板山花，山花上开草料门与吊杆，门前草垛
  T.push({
    n: 14, kind: 'house_barn', name: '谷仓农屋', fp: [2, 1], roof: 'gable_thatch',
    tags: ['one_storey', 'loft', 'gable_front', 'timber_frame', 'thatch', 'hay_door', 'haystack'], note: '山墙朝街，草料阁楼',
    draw: function (ctx, v) {
      var p = v.pal, s = '', fl = v.flip, x0 = fl ? 34 : 4, x1 = fl ? 92 : 62;
      s += C.groundShadow(x0, x1, 0, -42);
      var B = floors(ctx, x0, x1, [{ h: 22, mat: 'timber', fill: p.plaster, tex: { pattern: 'x', spacing: 14 } }]);
      s += B.svg;
      var mid = (x0 + x1) / 2;
      s += C.door(ctx, mid - 9, 0, 18, 18, 'wide', { fill: p.door });
      s += C.win(ctx, x0 + 5, -15, 6, 6, 'plain') + C.win(ctx, x1 - 11, -15, 6, 6, 'plain');
      var r = C.roofFront(ctx, { x0: x0, x1: x1, yE: B.yE, D: 40, R: 30, mat: 'thatch', ov: 4, gmat: 'plank', gfill: P.wood });
      s += r.svg;
      // 草料门 + 吊杆滑轮
      s += C.door(ctx, mid - 5, B.yE - 3, 10, 12, 'plank', { fill: P.dark });
      s += C.line('M' + f(mid) + ' ' + f(B.yE - 17) + 'v-5h9', 1.8, 1, P.dark) + C.line('M' + f(mid + 8) + ' ' + f(B.yE - 22) + 'v9', 0.8) +
        '<circle cx="' + f(mid + 8) + '" cy="' + f(B.yE - 21) + '" r="1.3" fill="' + P.timber + '"' + C.stroke(0.7) + '/>';
      var hx = fl ? 16 : 78;
      if (v.i === 3) {
        // 变体 3：谷仓侧面接一间敞口单坡车棚（木柱 + 茅草），草垛挪到棚外
        var sx0 = fl ? 12 : 62, sx1 = fl ? 34 : 84;
        s += C.rect(sx0, -16, sx1 - sx0, 16, P.shadow, 0, 0.28);
        s += C.line('M' + f(sx0 + 2) + ' 0V-16M' + f(sx1 - 2) + ' 0V-16', 2.2, 1, P.timber) + C.line('M' + f(sx0 + 2) + ' 0V-16M' + f(sx1 - 2) + ' 0V-16', 0.6, 0.6);
        s += C.path('M' + f(sx0 + 5) + ' -1h7l2 -3h-7Z', P.wood, 0.8);
        s += C.roofMono(ctx, { x0: sx0, x1: sx1, yE: -16, D: 30, R: 4, mat: 'thatch', ov: 1.5 }).svg;
        hx = fl ? 6 : 89;
        s += haystack(ctx, hx, 0, 5);
      } else s += haystack(ctx, hx, 0, 10);
      if (v.i !== 3) s += haystack(ctx, hx + (fl ? 10 : -6) * 0 + (fl ? 10 : 8), -18, 6);
      if (v.i === 2) s += C.fence(ctx, fl ? 4 : 66, fl ? 30 : 92, 0, 6);
      return s;
    }
  });

  // 15 方石塔宅：1×1，三层方塔（墙角隅石、底层无窗只开石框门、顶层射孔窗），金字塔形青石板顶 + 风向标
  T.push({
    n: 15, kind: 'house_towerhouse', name: '方石塔宅', fp: [1, 1], roof: 'hip_tile',
    tags: ['three_storey', 'square_tower', 'ashlar', 'quoins', 'pyramid_roof'], note: '金字塔四坡青石板顶，RoofId 取 hip_tile（材质为青石板）',
    draw: function (ctx, v) {
      var p = v.pal, s = '', x0 = 9, x1 = 39;
      s += C.groundShadow(x0, x1, 0, -36);
      var v3 = v.i === 3, FL = [
        { h: 22, mat: v3 ? 'rubble' : 'ashlar', tex: { course: 5.5, joint: 10 } },
        { h: 19, mat: v3 ? 'rubble' : 'ashlar', tex: { course: 5.5, joint: 10 } }];
      // 变体 3：顶层换成外挑的木筋阁楼，屋顶改红瓦
      FL.push(v3 ? { h: 15, mat: 'timber', fill: p.plaster, jet: 3, tex: { pattern: 'x', spacing: 9 } }
        : { h: 17, mat: 'ashlar', band: true, tex: { course: 5.5, joint: 10 } });
      var B = floors(ctx, x0, x1, FL);
      s += B.svg;
      // 隅石：两角交替长短石块
      var q = '';
      for (var y = 0; y > (v3 ? B.F[1].yt : B.yE) + 4; y -= 6) {
        var lw = ((-y / 6) % 2) ? 4 : 7;
        q += C.rect(x0, y - 6, lw, 6, P.paper, 0.8) + C.rect(x1 - lw, y - 6, lw, 6, P.stone, 0.8);
      }
      s += q;
      s += C.door(ctx, 19, 0, 10, 16, 'arch', { fill: p.door, surround: true, step: true });
      s += C.win(ctx, 20, -36, 8, 10, 'lead', { frame: P.stone2, box: v.i === 1 });
      if (v3) s += wrow(ctx, B.F[2], [17, 31], 'lead', 5, 6, {});
      else s += C.win(ctx, 16, -54, 3, 7, 'slit') + C.win(ctx, 29, -54, 3, 7, 'slit');
      var r = C.roofSide(ctx, { x0: B.x0, x1: B.x1, yE: B.yE, D: 30, R: v3 ? 14 : 20, mat: v3 ? 'tile' : 'slate', ov: 3, hip: 1 });
      s += r.svg;
      var ax = (x0 + x1) / 2, ay = r.yR;
      s += C.line('M' + f(ax) + ' ' + f(ay) + 'v-10', 1.4) + C.path('M' + f(ax) + ' ' + f(ay - 10) + 'l7 1.8l-7 2Z', P.red, 0.7);
      ctx.top(ay - 12);
      return s;
    }
  });

  // 16 L 形侧翼宅：2×2，后排横向主屋（灰泥 + 侧坡红瓦），一侧向前伸出带山墙的木筋侧翼，拐角处小院与井
  T.push({
    n: 16, kind: 'house_lplan', name: 'L 形侧翼宅', fp: [2, 2], roof: 'gable_tile',
    tags: ['two_storey', 'l_plan', 'plaster', 'timber_frame', 'wing', 'yard', 'well'], note: '主屋侧坡 + 侧翼正山墙',
    draw: function (ctx, v) {
      var p = v.pal, s = '', fl = v.flip, back = -44, mat = v.i === 3 ? 'slate' : 'tile';
      var wx0 = fl ? 6 : 52, wx1 = fl ? 44 : 90;
      s += C.groundShadow(6, 90, back, -94) + C.groundShadow(wx0, wx1, 0, back);
      // 主屋（退在后半格）
      s += shifted(ctx, back, function () {
        var o = '', B = floors(ctx, 6, 90, [{ h: 20, mat: 'plaster', fill: p.plaster }, { h: 16, mat: 'plaster', fill: p.plaster, band: true }]);
        o += B.svg;
        var dx = fl ? 60 : 22;
        o += C.door(ctx, dx, 0, 9, 15, 'arch', { fill: p.door, step: true });
        o += wrow(ctx, B.F[0], fl ? [52, 80] : [14, 40], 'shutter', 6, 7, { shutter: p.shut });
        o += wrow(ctx, B.F[1], centers(8, 88, 5), 'shutter', 6, 7, { shutter: p.shut, box: v.i === 2 });
        var r = C.roofSide(ctx, { x0: 6, x1: 90, yE: B.yE, D: 42, R: 12, mat: mat, ov: 3 });
        o += r.svg + C.chimney(ctx, fl ? 76 : 14, r.yR + 6, r.yR - 9, 6, 'brick') + C.smoke(ctx, fl ? 79 : 17, r.yR - 13);
        // 变体 3：主屋屋面加两座老虎窗
        if (v.i === 3) [30, 46].forEach(function (dx) { o += C.dormer(ctx, dx, B.yE - 6, 10, 8, mat); });
        return o;
      });
      // 院中水井
      var ux = fl ? 66 : 30;
      s += '<ellipse cx="' + f(ux) + '" cy="-18" rx="7" ry="3.6" fill="' + P.stone2 + '"' + C.stroke(1.2) + '/>' +
        C.face(ctx, 'M' + f(ux - 7) + ' -18V-12A7 3.6 0 0 0 ' + f(ux + 7) + ' -12V-18Z', P.stone, C.texRubble(ctx, ux - 7, -20, 14, 10), 1.2) +
        '<ellipse cx="' + f(ux) + '" cy="-18" rx="4.6" ry="2.2" fill="' + P.glass + '"/>' +
        C.line('M' + f(ux - 6) + ' -18v-12M' + f(ux + 6) + ' -18v-12M' + f(ux - 7.5) + ' -30h15', 1.4, 1, P.dark);
      ctx.top(-31);
      // 前伸侧翼：木筋 + 正山墙
      var W = floors(ctx, wx0, wx1, [{ h: 20, mat: 'ashlar', tex: { course: 5, joint: 11 } },
        { h: 16, mat: 'timber', fill: p.plaster, jet: 2, tex: { pattern: 'k', spacing: 10 } }]);
      s += W.svg;
      var wm = (wx0 + wx1) / 2;
      s += C.win(ctx, wm - 6, -16, 12, 9, 'lead') + wrow(ctx, W.F[1], centers(W.x0 + 2, W.x1 - 2, 2), 'lead', 6, 7, {});
      s += C.roofFront(ctx, { x0: W.x0, x1: W.x1, yE: W.yE, D: 46, R: 20, mat: mat, ov: 2, gmat: 'timber', gfill: p.plaster, gtex: { pattern: 'v', spacing: 8 } }).svg;
      return s;
    }
  });

  var API = { T: T, crowStep: crowStep, haystack: haystack };
  root.TownArtWB_housesC = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
