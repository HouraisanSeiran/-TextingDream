/*
 * 织梦 · 西式民居 A 组（01–05）+ 民居组合工具（美术样板，尚未接入游戏）
 * 局部坐标：x 0..w*48，y = 0 为占地前沿，向上为负。每种 draw(ctx, v) 返回 svg 片段。
 * 浏览器挂 window.TownArtWB_housesA；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./common.js') : root.TownArtWB_common;
  var P = C.PAL, f = C.f;

  var DOORS = [P.timber, '#7a4a32', '#5d6a52', '#6e3b2c'];
  var SHUT = [P.dark, '#5d6b58', '#7a3a2a', '#56606c'];
  var PLAST = [P.plaster, P.paper, '#e6d3a8', '#ece2c8'];
  function pal(ctx) { return { door: ctx.pick(DOORS), shut: ctx.pick(SHUT), plaster: ctx.pick(PLAST) }; }

  /** 叠层立面：list = [{h, mat, fill, tex, jet}]，上层 jet 为两侧外挑像素。返回 { svg, F, yE, x0, x1 } */
  function floors(ctx, x0, x1, list) {
    var y = 0, s = '', F = [], a = x0, b = x1, prev = null;
    for (var i = 0; i < list.length; i++) {
      var L = list[i], j = i ? (L.jet || 0) : 0;
      a -= j; b += j;
      s += C.facade(ctx, a, b, y, L.h, L.mat, { fill: L.fill, tex: L.tex, band: j > 0 || L.band });
      if (j > 0 && prev) {
        s += C.jettyShade(prev.x0, prev.x1, y);
        s += C.path(C.poly([[a + 0.4, y], [prev.x0 + 3.5, y], [prev.x0 + 0.4, y + 5]]), P.dark, 0.8) +
          C.path(C.poly([[b - 0.4, y], [prev.x1 - 3.5, y], [prev.x1 - 0.4, y + 5]]), P.dark, 0.8);
      }
      prev = { x0: a, x1: b, yb: y, yt: y - L.h, h: L.h };
      F.push(prev); y -= L.h;
    }
    return { svg: s, F: F, yE: y, x0: a, x1: b };
  }
  function centers(x0, x1, n) { var r = []; for (var i = 0; i < n; i++) r.push(x0 + (x1 - x0) * (i + 0.5) / n); return r; }
  /** 一排窗：fl 楼层，xs 窗中心 */
  function wrow(ctx, fl, xs, kind, w, h, opt) {
    var s = '', y = fl.yt + Math.max(2.5, (fl.h - h) * 0.42);
    xs.forEach(function (cx) { s += C.win(ctx, cx - w / 2, y, w, h, kind, opt); });
    return s;
  }
  /** 茅草檐口的毛边 */
  function thatchHem(x0, x1, y) {
    var n = Math.max(2, Math.round((x1 - x0) / 4)), st = (x1 - x0) / n, d = 'M' + f(x0) + ' ' + f(y);
    for (var i = 0; i < n; i++) d += 'q' + f(st / 2) + ' 2.8 ' + f(st) + ' 0';
    return C.path(d + 'V' + f(y - 2.5) + 'H' + f(x0) + 'Z', P.thatch2, 0) + C.line(d, 1.1);
  }
  /** 一堆劈柴（端面朝外的圆木） */
  function logs(ctx, x, yb, n) {
    var s = '', rows = [n, n - 1];
    for (var r = 0; r < rows.length; r++) for (var i = 0; i < rows[r]; i++) {
      var cx = x + 2.4 + i * 4.6 + r * 2.3, cy = yb - 2.2 - r * 4;
      s += '<circle cx="' + f(cx) + '" cy="' + f(cy) + '" r="2.2" fill="' + P.wood + '"' + C.stroke(0.8) + '/>' +
        '<circle cx="' + f(cx) + '" cy="' + f(cy) + '" r="0.8" fill="none"' + C.stroke(0.5, 0.6) + '/>';
    }
    return s;
  }
  /** 木桶 */
  function barrel(ctx, x, yb) {
    var d = 'M' + f(x) + ' ' + f(yb) + 'q-1 -4.5 0 -9h7q1 4.5 0 9Z';
    return C.path(d, P.wood, 1) + C.line('M' + f(x - 0.4) + ' ' + f(yb - 3) + 'h7.8M' + f(x - 0.4) + ' ' + f(yb - 6.3) + 'h7.8', 0.9, 1, P.dark) +
      '<ellipse cx="' + f(x + 3.5) + '" cy="' + f(yb - 9) + '" rx="3.5" ry="1.2" fill="' + P.timber + '"' + C.stroke(0.8) + '/>';
  }

  var T = [];

  // 01 茅草小屋：一层白灰泥墙，厚茅草四坡顶（收山），石烟囱，上下分扇门
  T.push({
    n: 1, kind: 'house_cottage', name: '茅草小屋', fp: [1, 1], roof: 'gable_thatch',
    tags: ['one_storey', 'plaster', 'thatch', 'chimney'], note: '茅草顶两端收山，近似半四坡',
    draw: function (ctx, v) {
      var p = v.pal, s = '', x0 = 6, x1 = 42;
      s += C.groundShadow(x0, x1, 0, -42);
      var B = floors(ctx, x0, x1, [{ h: 21, mat: 'plaster', fill: p.plaster }]);
      s += B.svg;
      s += C.door(ctx, v.flip ? 27 : 11, 0, 9, 16, 'dutch', { fill: p.door, step: true });
      s += wrow(ctx, B.F[0], [v.flip ? 16 : 32], 'shutter', 7, 7, { shutter: p.shut, box: v.i === 2 });
      var r = C.roofSide(ctx, { x0: x0, x1: x1, yE: B.yE, D: 46, R: 13, mat: 'thatch', ov: 4, hip: 0.3 });
      s += r.svg + thatchHem(r.x0, r.x1, B.yE + 2);
      if (v.i === 3) {
        // 变体 3：茅草眉窗 + 山墙端落地外烟囱
        s += C.dormer(ctx, 18, B.yE - 6, 10, 8, 'thatch');
        s += C.chimney(ctx, 40, 0, r.yR - 9, 7, 'stone') + C.smoke(ctx, 43.5, r.yR - 13);
      } else {
        var cx = v.flip ? 12 : 30;
        s += C.chimney(ctx, cx, r.yR + 8, r.yR - 9, 6, 'stone') + C.smoke(ctx, cx + 3, r.yR - 13);
      }
      return s;
    }
  });

  // 02 木筋两层屋：两层木筋灰泥，上层外挑，红瓦双坡，砖烟囱，铅条窗
  T.push({
    n: 2, kind: 'house_timber', name: '木筋两层屋', fp: [1, 1], roof: 'gable_tile',
    tags: ['two_storey', 'timber_frame', 'jetty', 'chimney'], note: '',
    draw: function (ctx, v) {
      var p = v.pal, s = '', x0 = 8, x1 = 40;
      s += C.groundShadow(x0, x1, 0, -42);
      var FL = [
        { h: 21, mat: 'timber', fill: p.plaster, tex: { pattern: 'k', spacing: 11 } },
        { h: 19, mat: 'timber', fill: p.plaster, jet: 3, tex: { pattern: v.i === 1 ? 'x' : 'v', spacing: 9.5 } }];
      // 变体 3：再加一层外挑三楼
      if (v.i === 3) FL.push({ h: 16, mat: 'timber', fill: p.plaster, jet: 2.5, tex: { pattern: 'k', spacing: 9 } });
      var B = floors(ctx, x0, x1, FL);
      s += B.svg;
      if (B.F[2]) s += wrow(ctx, B.F[2], [24], 'lead', 8, 7, {});
      s += C.door(ctx, v.flip ? 28 : 11, 0, 8, 16, 'plank', { fill: p.door, step: true });
      s += wrow(ctx, B.F[0], [v.flip ? 18 : 30], 'lead', 7, 8, {});
      s += wrow(ctx, B.F[1], centers(B.x0 + 2, B.x1 - 2, 2), 'lead', 7, 8, { box: v.i === 2 });
      var r = C.roofSide(ctx, { x0: B.x0, x1: B.x1, yE: B.yE, D: 44, R: 11, mat: 'tile' });
      s += r.svg;
      var cx = v.flip ? 10 : 31;
      s += C.chimney(ctx, cx, r.yR + 7, r.yR - 8, 5.5, 'brick') + (v.i === 1 ? C.smoke(ctx, cx + 2.7, r.yR - 12) : '');
      return s;
    }
  });

  // 03 毛石农舍：2×1，一层毛石墙 + 阁楼老虎窗，青石板陡坡顶，山墙端大石烟囱，门边一垛劈柴
  T.push({
    n: 3, kind: 'house_stone', name: '毛石农舍', fp: [2, 1], roof: 'steep_slate',
    tags: ['one_storey', 'attic', 'rubble', 'dormer', 'chimney', 'woodpile'], note: '',
    draw: function (ctx, v) {
      var p = v.pal, s = '', x0 = 5, fl = v.flip, v3 = v.i === 3, x1 = v3 ? 72 : 91;
      s += C.groundShadow(x0, v3 ? 92 : x1, 0, -42);
      if (v3) {
        // 变体 3：东端接一间矮竖板单坡披屋，主屋缩短
        s += C.facade(ctx, 72, 92, 0, 15, 'plank');
        s += C.door(ctx, 78, 0, 8, 12, 'plank', { fill: p.door });
        s += C.roofMono(ctx, { x0: 72, x1: 92, yE: -15, D: 38, R: 4, mat: 'shingle', ov: 1.5 }).svg;
      }
      var B = floors(ctx, x0, x1, [{ h: 23, mat: 'rubble' }]);
      s += B.svg;
      s += C.door(ctx, fl ? 58 : 30, 0, 10, 17, 'plank', { fill: p.door, surround: true });
      s += wrow(ctx, B.F[0], fl ? [20, 44, 78] : (v3 ? [17, 54] : [17, 52, 76]), 'shutter', 7, 7, { shutter: p.shut, box: v.i === 2 });
      var r = C.roofSide(ctx, { x0: x0, x1: x1, yE: B.yE, D: 44, R: 14, mat: 'slate', ov: 3 });
      s += r.svg;
      var dx = fl ? [34, 64] : (v3 ? [26, 52] : [32, 62]);
      if (v.i === 2) dx = [48];
      dx.forEach(function (cx) { s += C.dormer(ctx, cx, B.yE - 7, 11, 9, 'slate'); });
      var cx = (fl || v3) ? 8 : 81;
      s += C.chimney(ctx, cx, B.yE + 2, r.yR - 11, 8, 'stone') + C.smoke(ctx, cx + 4, r.yR - 15);
      s += logs(ctx, fl ? 72 : 12, 0, 3);
      return s;
    }
  });

  // 04 长屋：2×1，矮木板墙（横板），厚茅草全四坡长顶，一端畜栏双开大门，屋脊开排烟口
  T.push({
    n: 4, kind: 'house_longhouse', name: '长屋', fp: [2, 1], roof: 'gable_thatch',
    tags: ['one_storey', 'plank', 'thatch', 'byre', 'hip'], note: '四坡茅草顶，RoofId 取最近的 gable_thatch',
    draw: function (ctx, v) {
      var p = v.pal, s = '', x0 = 3, x1 = 93, fl = v.flip;
      s += C.groundShadow(x0, x1, 0, -42);
      var B = floors(ctx, x0, x1, [{ h: 17, mat: 'plankh' }]);
      s += B.svg;
      // 石砌勒脚
      s += C.face(ctx, C.rectD(x0, -4.5, x1 - x0, 4.5), P.stone2, C.texRubble(ctx, x0, -4.5, x1 - x0, 4.5), 1.2);
      s += C.door(ctx, fl ? 10 : 68, 0, 16, 15, 'wide', { fill: p.door });
      s += C.door(ctx, fl ? 62 : 26, 0, 8, 14, 'plank', { fill: p.door });
      s += wrow(ctx, B.F[0], fl ? [46, 80] : [14, 46], 'plain', 6, 5, {});
      // 变体 3：两端几乎不收山（近双坡）+ 端头石烟囱
      var r = C.roofSide(ctx, { x0: x0, x1: x1, yE: B.yE, D: 46, R: 17, mat: 'thatch', ov: 4, hip: v.i === 3 ? 0.15 : 0.75 });
      s += r.svg + thatchHem(r.x0, r.x1, B.yE + 2);
      if (v.i === 3) s += C.chimney(ctx, 82, r.yR + 6, r.yR - 10, 7, 'stone');
      // 屋脊排烟口
      var hx = fl ? 34 : 60;
      s += C.path('M' + f(hx - 5) + ' ' + f(r.yR + 1) + 'l2 -4h6l2 4Z', P.thatch2, 1.1) + C.smoke(ctx, hx, r.yR - 4);
      s += barrel(ctx, fl ? 86 : 3, 0);
      if (v.i === 2) s += barrel(ctx, fl ? 78 : 11, 0);
      return s;
    }
  });

  // 05 窄高街屋：1×1，山墙朝街，三层（底层方石、上两层木筋逐层外挑），红瓦陡山墙，挂招牌
  T.push({
    n: 5, kind: 'house_townhouse', name: '窄高街屋', fp: [1, 1], roof: 'gable_tile',
    tags: ['three_storey', 'gable_front', 'jetty', 'timber_frame', 'shop', 'sign'], note: '山墙朝街的商住街屋',
    draw: function (ctx, v) {
      var p = v.pal, s = '', x0 = 11, x1 = 37, fl = v.flip;
      s += C.groundShadow(x0, x1, 0, -42);
      var v3 = v.i === 3, FL = [
        { h: 20, mat: 'ashlar', tex: { course: 5, joint: 9 } },
        { h: 17, mat: 'timber', fill: p.plaster, jet: 2.5, tex: { pattern: 'x', spacing: 10 } }];
      if (!v3) FL.push({ h: 15, mat: 'timber', fill: p.plaster, jet: 2.5, tex: { pattern: 'k', spacing: 10 } });
      if (v3) {
        // 变体 3：只有两层，东侧贴一间单坡木板小铺（货摊披屋）
        s += C.facade(ctx, 35, 46, 0, 13, 'plank');
        s += C.rect(37, -9, 7, 5, P.glass, 0.8);
        s += C.roofMono(ctx, { x0: 35, x1: 46, yE: -13, D: 30, R: 5, mat: 'shingle', ov: 1 }).svg;
      }
      var B = floors(ctx, x0, x1, FL);
      s += B.svg;
      s += C.door(ctx, fl ? 25 : 14, 0, 9, 15, 'arch', { fill: p.door, step: true });
      s += C.win(ctx, fl ? 14 : 26, -15, 8, 9, 'lead');
      s += wrow(ctx, B.F[1], centers(B.F[1].x0 + 1, B.F[1].x1 - 1, 2), 'lead', 6, 8, { box: v.i === 1 });
      if (B.F[2]) s += wrow(ctx, B.F[2], [24], 'lead', 7, 8, {});
      var r = C.roofFront(ctx, { x0: B.x0, x1: B.x1, yE: B.yE, D: 38, R: 21, mat: 'tile', ov: 2.5,
        gmat: 'timber', gfill: p.plaster, gtex: { pattern: 'v', spacing: 8 }, finial: true });
      s += r.svg;
      s += C.win(ctx, 21.5, B.yE - 12, 5, 6, 'plain');
      if (!v3) s += C.sign(ctx, 35, -23, v.i === 1 ? 'key' : 'boot');
      else s += C.sign(ctx, 1, -24, 'loaf');
      return s;
    }
  });

  var API = { T: T, floors: floors, centers: centers, wrow: wrow, thatchHem: thatchHem, logs: logs, barrel: barrel, pal: pal };
  root.TownArtWB_housesA = API;
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
