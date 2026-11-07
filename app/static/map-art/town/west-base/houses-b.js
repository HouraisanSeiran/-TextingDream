/*
 * 织梦 · 西式民居 B 组（06–10）（美术样板，尚未接入游戏）
 * 浏览器挂 window.TownArtWB_housesB；Node 用 module.exports。依赖 common.js、houses-a.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./common.js') : root.TownArtWB_common;
  var HA = isNode ? require('./houses-a.js') : root.TownArtWB_housesA;
  var P = C.PAL, f = C.f, floors = HA.floors, centers = HA.centers, wrow = HA.wrow;
  var T = [];

  // 06 方石商住楼：2×1，两层方石，底层店面（大拱窗 + 门 + 挂招牌 + 布篷），四坡红瓦，两座烟囱
  T.push({
    n: 6, kind: 'house_shop', name: '方石商住楼', fp: [2, 1], roof: 'hip_tile',
    tags: ['two_storey', 'ashlar', 'shop', 'sign', 'awning', 'hip', 'chimney'], note: '',
    draw: function (ctx, v) {
      var p = v.pal, s = '', x0 = 4, x1 = 92, fl = v.flip;
      s += C.groundShadow(x0, x1, 0, -42);
      var B = floors(ctx, x0, x1, [
        { h: 22, mat: 'ashlar', tex: { course: 5.5, joint: 12 } },
        { h: 19, mat: 'ashlar', band: true, tex: { course: 5.5, joint: 12 } }]);
      s += B.svg;
      // 店面：两扇拱窗 + 门；上方条纹布篷
      var dx = fl ? 66 : 20, wx = fl ? [16, 38] : [52, 74];
      s += C.door(ctx, dx - 5, 0, 10, 17, 'arch', { fill: p.door, surround: true, step: true });
      wx.forEach(function (cx) { s += C.win(ctx, cx - 6, -17, 12, 12, 'arch'); });
      var ax0 = wx[0] - 9, ax1 = wx[1] + 9, ay = -21.5, aw = '', stripe = v.i === 3 ? P.slate : P.red;
      s += C.path(C.poly([[ax0, ay], [ax1, ay], [ax1 + 2, ay + 6], [ax0 - 2, ay + 6]]), P.paper, 1.2);
      for (var x = ax0; x < ax1; x += 6) aw += 'M' + f(x + 1) + ' ' + f(ay) + 'l' + f(-0.3) + ' 6h3l0.3 -6Z';
      s += C.clipped(ctx, C.poly([[ax0, ay], [ax1, ay], [ax1 + 2, ay + 6], [ax0 - 2, ay + 6]]), C.path(aw, stripe, 0));
      var sc = '';
      for (x = ax0 - 2; x < ax1 + 2; x += 3) sc += 'q1.5 2.4 3 0';
      s += C.line('M' + f(ax0 - 2) + ' ' + f(ay + 6) + sc, 1);
      s += wrow(ctx, B.F[1], centers(x0 + 4, x1 - 4, 4), 'shutter', 7, 9, { shutter: p.shut, box: v.i !== 3 });
      s += C.sign(ctx, fl ? 82 : 2, -30, v.i === 2 ? 'mug' : 'loaf');
      var r = C.roofSide(ctx, { x0: x0, x1: x1, yE: B.yE, D: 44, R: 13, mat: 'tile', ov: 3, hip: 0.8 });
      s += r.svg;
      if (v.i === 3) {
        // 变体 3：正中一座山墙老虎窗，只留一座端部烟囱
        s += C.dormer(ctx, 48, B.yE - 6, 16, 12, 'tile');
        s += C.chimney(ctx, 80, r.yR + 6, r.yR - 11, 7, 'brick') + C.smoke(ctx, 83.5, r.yR - 15);
      } else [fl ? 30 : 26, fl ? 66 : 62].forEach(function (cx, k) {
        s += C.chimney(ctx, cx, r.yR + 6, r.yR - 9 - k * 2, 6, 'brick');
        if (k === v.i % 2) s += C.smoke(ctx, cx + 3, r.yR - 13 - k * 2);
      });
      return s;
    }
  });

  // 07 外楼梯石屋：1×2 进深，底层毛石（畜圈 / 储藏），上层竖板木屋，外楼梯沿正面通二楼门；青石板山墙朝街
  T.push({
    n: 7, kind: 'house_stair', name: '外楼梯石屋', fp: [1, 2], roof: 'steep_slate',
    tags: ['two_storey', 'rubble', 'plank', 'outside_stair', 'gable_front'], note: '下石上木，外楼梯',
    draw: function (ctx, v) {
      var p = v.pal, s = '', x0 = 5, x1 = 43, fl = v.flip;
      s += C.groundShadow(x0, x1, 0, -90);
      var FL = [
        { h: 20, mat: 'rubble' },
        { h: 17, mat: 'plank', fill: v.i === 3 ? '#b8956a' : P.wood, band: true }];
      // 变体 3：再加一层矮阁楼（竖板）
      if (v.i === 3) FL.push({ h: 13, mat: 'plank', fill: P.wood, band: true });
      var B = floors(ctx, x0, x1, FL);
      s += B.svg;
      if (B.F[2]) s += wrow(ctx, B.F[2], [fl ? 15 : 33], 'plain', 6, 5, {});
      // 底层低矮拱门（畜圈）
      s += C.door(ctx, fl ? 8 : 30, 0, 10, 13, 'arch', { fill: P.dark });
      // 外楼梯：从底层一侧斜上到二层门前平台
      var dX = fl ? 10 : 30;
      s += C.door(ctx, dX, -20, 8, 14, 'plank', { fill: p.door });
      s += C.rect(fl ? 6 : 28, -21.5, 14, 2.6, P.wood, 1);
      s += C.stairs(ctx, fl ? 42 : 6, 0, fl ? 20 : 28, -20);
      s += wrow(ctx, B.F[1], [fl ? 32 : 15], 'shutter', 6, 7, { shutter: p.shut });
      // 屋脊沿进深，但斜俯视下 96 px 进深只占约 55 px 屋面
      var r = C.roofFront(ctx, { x0: B.x0, x1: B.x1, yE: B.yE, D: 54, R: 20, mat: 'slate', ov: 3,
        gmat: 'plank', gfill: P.wood });
      s += r.svg;
      s += C.win(ctx, 21, B.yE - 11, 6, 6, 'plain');
      // 后坡上一座石烟囱
      var cx = fl ? 12 : 31;
      s += C.chimney(ctx, cx, B.yE - 44, B.yE - 62, 6, 'stone') + C.smoke(ctx, cx + 3, B.yE - 66);
      return s;
    }
  });

  // 08 塔式小楼：1×1，三层毛石圆塔（锥形青石板顶 + 风向旗），塔脚贴一间单坡木板小披屋
  T.push({
    n: 8, kind: 'house_tower', name: '塔式小楼', fp: [1, 1], roof: 'steep_slate',
    tags: ['three_storey', 'round_tower', 'rubble', 'lean_to', 'cone_roof'], note: '锥顶，RoofId 取最近的 steep_slate',
    draw: function (ctx, v) {
      var p = v.pal, s = '', fl = v.flip, cx = fl ? 30 : 18, r = 13;
      s += C.groundShadow(4, 44, 0, -40);
      // 披屋在塔后侧，先画
      var lx0 = fl ? 4 : 28, lx1 = fl ? 20 : 45;
      s += C.facade(ctx, lx0, lx1, -2, 13, 'plank');
      s += C.door(ctx, lx0 + 4, -2, 7, 11, 'plank', { fill: p.door });
      s += C.roofMono(ctx, { x0: lx0, x1: lx1, yE: -15, D: 26, R: 6, mat: v.i === 3 ? 'thatch' : 'shingle', ov: 2 }).svg;
      var v3 = v.i === 3, T2 = C.roundTower(ctx, cx, 0, r, v3 ? 62 : 54, v3 ? 0 : 26, { mat: 'rubble', roof: 'slate', ov: 3 });
      s += T2.svg;
      if (v3) {
        // 变体 3：更高的平顶塔，顶上一圈垛口
        for (var k = -2; k <= 2; k++) {
          var mx = cx + k * 5.2, my = T2.yt + T2.ry * Math.sqrt(Math.max(0, 1 - Math.pow(k * 5.2 / r, 2)));
          s += C.rect(mx - 2, my - 5, 4, 5, P.stone, 0.9);
        }
        ctx.top(T2.yt - 6);
      }
      // 塔身门窗
      s += C.door(ctx, cx - 4, -7, 8, 13, 'arch', { fill: p.door, step: true });
      s += C.win(ctx, cx - 3, -32, 6, 8, 'shutter', { shutter: p.shut });
      s += C.win(ctx, cx - 2, -50, 4, 7, 'slit');
      s += C.line('M' + f(cx - r) + ' ' + f(-7 - 21) + 'q' + f(r) + ' ' + f(r * 0.5) + ' ' + f(2 * r) + ' 0', 1, 0.6);
      return s;
    }
  });

  /** 在局部坐标里整体后移 dy（负数 = 往后/上）画一段，minY 同步换算 */
  function shifted(ctx, dy, fn) {
    var m = ctx.minY; ctx.minY = 0;
    var svg = fn();
    ctx.minY = Math.min(m, ctx.minY + dy);
    return '<g transform="translate(0 ' + f(dy) + ')">' + svg + '</g>';
  }

  // 09 院落农家：2×2，主屋退在后半格（一层竖木筋 + 木瓦顶），前院有矮石院墙、院门、两块菜畦、果树、碎石小径
  T.push({
    n: 9, kind: 'house_farmyard', name: '院落农家', fp: [2, 2], roof: 'gable_tile',
    tags: ['one_storey', 'timber_frame', 'yard', 'yard_wall', 'garden', 'shingle'], note: '木瓦屋面，RoofId 取最近的 gable_tile',
    draw: function (ctx, v) {
      var p = v.pal, s = '', fl = v.flip, back = -46;
      s += C.groundShadow(8, 88, back, -94);
      s += shifted(ctx, back, function () {
        var o = '', B = floors(ctx, 8, 88, [{ h: 20, mat: 'timber', fill: p.plaster, tex: { pattern: 'v', spacing: 12 } }]);
        o += B.svg;
        o += C.door(ctx, 43, 0, 10, 16, 'dutch', { fill: p.door, step: true });
        o += wrow(ctx, B.F[0], fl ? [20, 32, 70] : [24, 66, 78], 'shutter', 6, 7, { shutter: p.shut, box: v.i === 1 });
        var r = C.roofSide(ctx, { x0: 8, x1: 88, yE: B.yE, D: 40, R: 12, mat: 'shingle', ov: 3 });
        o += r.svg;
        if (v.i === 3) [26, 70].forEach(function (dx) { o += C.dormer(ctx, dx, B.yE - 5, 10, 8, 'shingle'); });
        var cx = v.i === 3 ? 46 : (fl ? 18 : 72);
        o += C.chimney(ctx, cx, r.yR + 6, r.yR - 8, 6, 'stone') + C.smoke(ctx, cx + 3, r.yR - 12);
        return o;
      });
      // 院子地面：碎石小径
      s += C.path(C.poly([[44, back], [52, back], [54, -1], [42, -1]]), '#d8c99f', 0);
      var pv = '';
      for (var i = 0; i < 9; i++) pv += 'M' + f(ctx.rnd(43, 52)) + ' ' + f(ctx.rnd(back + 2, -3)) + 'h1.6';
      s += C.line(pv, 1, 0.5);
      // 菜畦与果树
      s += C.garden(ctx, fl ? 58 : 10, -38, 28, 15) + C.garden(ctx, fl ? 58 : 10, -19, 28, 11);
      s += C.shrub(ctx, fl ? 22 : 74, -16, 8);
      if (v.i !== 2) s += HA.barrel(ctx, fl ? 34 : 60, -26);
      // 两侧院墙（只露墙顶）与前院墙
      var wall = v.i === 3 ? 'fence' : 'wall';
      [4, 88.5].forEach(function (x) {
        s += C.face(ctx, C.rectD(x, back + 2, 3.5, -back - 9), wall === 'wall' ? P.stone2 : P.wood, '', 1);
      });
      s += C.fence(ctx, 3, 40, 0, 7, wall) + C.fence(ctx, 56, 93, 0, 7, wall);
      s += C.rect(39, -11, 3.5, 11, P.stone2, 1.1) + C.rect(53.5, -11, 3.5, 11, P.stone2, 1.1);
      return s;
    }
  });

  // 10 半石半木大宅：2×2，底层方石、二层木筋外挑，半歇山红瓦大屋顶 + 两座老虎窗 + 两端砖烟囱，石框拱门
  T.push({
    n: 10, kind: 'house_manor', name: '半石半木大宅', fp: [2, 2], roof: 'hip_tile',
    tags: ['two_storey', 'ashlar', 'timber_frame', 'jetty', 'half_hip', 'dormer', 'chimney'], note: '半歇山（端部截角），RoofId 取 hip_tile',
    draw: function (ctx, v) {
      var p = v.pal, s = '', fl = v.flip, x0 = 6, x1 = 90;
      s += C.groundShadow(x0, x1, 0, -92);
      var B = floors(ctx, x0, x1, [
        { h: 23, mat: v.i === 3 ? 'rubble' : 'ashlar', tex: { course: 6, joint: 14 } },
        { h: 21, mat: 'timber', fill: p.plaster, jet: 3, tex: { pattern: v.i === 2 ? 'x' : 'k', spacing: 12 } }]);
      s += B.svg;
      s += C.door(ctx, 43, 0, 11, 18, 'arch', { fill: p.door, surround: true, step: true });
      s += wrow(ctx, B.F[0], fl ? [16, 30, 66, 80] : [16, 30, 66, 80], 'lead', 7, 9, {});
      s += wrow(ctx, B.F[1], centers(B.x0 + 4, B.x1 - 4, 5), 'lead', 7, 9, { box: v.i === 1 });
      var r = C.roofSide(ctx, { x0: B.x0, x1: B.x1, yE: B.yE, D: 86, R: 10, mat: 'tile', ov: 3, hx: 14 });
      s += r.svg;
      if (v.i === 3) {
        // 变体 3：正面中段一座木筋交叉山墙，代替两座老虎窗
        s += C.roofFront(ctx, { x0: 34, x1: 62, yE: B.yE, D: 30, R: 20, mat: 'tile', ov: 2.5,
          gmat: 'timber', gfill: p.plaster, gtex: { pattern: 'v', spacing: 9 } }).svg;
        s += C.win(ctx, 44, B.yE - 12, 8, 8, 'lead');
      } else [34, 62].forEach(function (cx) { s += C.dormer(ctx, cx, B.yE - 9, 12, 10, 'tile'); });
      s += C.chimney(ctx, B.x0 + 16, r.yR + 6, r.yR - 10, 7, 'brick') + C.chimney(ctx, B.x1 - 23, r.yR + 6, r.yR - 10, 7, 'brick');
      s += C.smoke(ctx, fl ? B.x0 + 19.5 : B.x1 - 19.5, r.yR - 14);
      return s;
    }
  });

  var API = { T: T, shifted: shifted };
  root.TownArtWB_housesB = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
