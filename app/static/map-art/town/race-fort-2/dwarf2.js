/*
 * 织梦 · race-fort-2 矮人族：石棱堡（fort，3×3，8 向）+ 阶梯山城要塞地标（landmark，6×6）（美术样板，尚未接入游戏）
 * 墙高 44、巨石立面、深岩勒脚、走道色、北沿矮垛 / 南沿厚垛、铜门、符文、炮眼，全部沿用 ../race-fort/dwarf.js（只读 require）。
 * 浏览器挂 window.TownArtRF2_dwarf；Node 用 module.exports。依赖 race-fort 的 core.js、spoke.js、dwarf.js 与本目录 bastion.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('../race-fort/core.js') : root.TownArtRF_core;
  var K = isNode ? require('../race-fort/spoke.js') : root.TownArtRF_spoke;
  var D = isNode ? require('../race-fort/dwarf.js') : root.TownArtRF_dwarf;
  var B = isNode ? require('./bastion.js') : root.TownArtRF2_bastion;
  var P = C.P, f = C.f, line = C.line, path = C.path, rect = C.rect, H = D.H;
  var SHAPE = { o: { root: 28, sh: [66, 54], tip: 108 }, d: { root: 28, sh: [56, 38], tip: 92 } };
  function sh(dir) { return SHAPE[dir.length === 2 ? 'd' : 'o']; }

  function scale(pts, k) { var c = B.centroid(pts); return pts.map(function (p) { return [c[0] + (p[0] - c[0]) * k, c[1] + (p[1] - c[1]) * k]; }); }
  /** 铜铆炮门（平直坐标：底 y = 0）：石框 + 半开铜护板（铆钉 + 铁箍）+ 黑洞 + 炮口 */
  function gunDoor(x, yb, w, h) {
    var x0 = x - w / 2, y0 = yb - h, s = rect(x0 - 3, y0 - 3, w + 6, h + 5, P.granite3, 1.2) + rect(x0, y0, w, h, P.hole, 0.9);
    s += C.ell(x + 0.5, y0 + h * 0.58, w * 0.3, h * 0.26, P.iron, 0.9) + C.ell(x + 0.6, y0 + h * 0.6, w * 0.15, h * 0.13, '#3e3a36', 0);
    s += path('M' + f(x0 - 1) + ' ' + f(y0 - 1) + 'h' + f(w + 2) + 'l-2 ' + f(-h * 0.42) + 'h' + f(-w + 2) + 'Z', P.copper, 1.1);
    s += line('M' + f(x0 + 1) + ' ' + f(y0 - h * 0.21) + 'h' + f(w - 2), 1.6, 1, P.iron);
    for (var i = 0; i < 4; i++) s += C.ell(x0 + 1.5 + i * (w - 3) / 3, y0 - h * 0.21, 0.7, 0.7, P.ember, 0.3);
    return s + line('M' + f(x0 - 1) + ' ' + f(y0 - 1) + 'h' + f(w + 2), 1.2);
  }
  /** 立面纹理：巨石 + 侧翼 / 棱面开铜铆炮门、棱面刻符文带 */
  function faceTex(g) {
    return function (x0, x1, h, e, i) {
      var s = D.stones(x0, x1, h), role = g.role[i], w = x1 - x0;
      if ((role === 'flank' || role === 'face') && w > 16) s += gunDoor((x0 + x1) / 2, -14, 9, 10);
      if (role === 'face' && w > 30) {
        var a = x0 + w * 0.2, b = x1 - w * 0.2;
        s += rect(a, -h + 5, b - a, 7, P.deep, 1);
        for (var x = a + 4, k = 0; x < b - 2; x += 7, k++) s += D.rune(x, -h + 8.5, 2.4, P.verd2, k);
      }
      return s;
    };
  }
  /** 走道石板缝（裁在顶面内） */
  function slabs(ctx, top, step) {
    var id = ctx.uid(), x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity, d = '';
    top.forEach(function (p) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); y0 = Math.min(y0, p[1]); y1 = Math.max(y1, p[1]); });
    for (var y = Math.ceil(y0 / step) * step; y < y1; y += step) {
      d += 'M' + f(x0) + ' ' + f(y) + 'H' + f(x1);
      for (var x = Math.ceil(x0 / 16) * 16 + ((y / step) % 2 ? 8 : 0); x < x1; x += 16) d += 'M' + f(x) + ' ' + f(y) + 'v' + f(step);
    }
    return '<clipPath id="' + id + '"><path d="' + C.poly(top) + '"/></clipPath><g clip-path="url(#' + id + ')">' + line(d, 0.7, 0.35) + '</g>';
  }
  /** 沿外形各边排垛：切口两侧的幕墙从切口起算（与辐条节奏一致），城内侧墙面从两端各算一半 */
  function crenels(g, es) {
    var back = [], front = [];
    function put(e, offset, endMargin) {
      var fr = e.ny > 0.02, inset = fr ? 1.6 : 2;
      B.edgeBlocks(e, offset, 12, 9, fr ? 3 : 4, inset, endMargin).forEach(function (b) { (fr ? front : back).push({ pts: b.pts, vert: Math.abs(e.ny) <= 0.02 }); });
    }
    es.forEach(function (e, i) {
      var r = g.role[i];
      if (r === 'cut') return;
      if (r === 'curtain') return put(B.fromCut(g, es, i), 6, 4);
      if (r === 'gorge') {
        var half = e.len / 2;
        put({ A: e.A, B: B.lerp(e.A, e.B, 0.5), nx: e.nx, ny: e.ny, len: half }, 6, 4);
        put({ A: e.B, B: B.lerp(e.A, e.B, 0.5), nx: e.nx, ny: e.ny, len: half }, 6, 4);
        return;
      }
      put(e, ((e.len - 9) % 12) / 2 + 4.5, 6);
    });
    var key = function (b) { return b.pts.reduce(function (m, p) { return m + p[1]; }, 0); };
    back.sort(function (a, b) { return key(a) - key(b); }); front.sort(function (a, b) { return key(a) - key(b); });
    return { back: back, front: front };
  }

  /** 石棱堡（fort，3×3）：与巨石墙同高同厚的墙带 + 厚重五边形堡身（高出墙 10），侧翼 / 棱面开铜铆炮门，棱面刻符文带，尖角上铜顶哨亭 + 旗 */
  function bastion(ctx, dir) {
    var o = sh(dir), g = B.outline(dir, 3, o), es = K.edgesOf(g.pts, g.kinds), s = '', HB = H + 10;
    s += B.shadow(g.pts, 7, 5, 0.17);
    // 墙带（与辐条同高 H），堡身（HB）压在上面
    var band = [g.pts[0], g.pts[1], g.pts[2], g.pts[6], g.pts[7], g.pts[8]];
    s += B.solid(ctx, band, ['start', 'side', 'side', 'side', 'start', 'side'], 0, H, { face: P.granite, top: P.walk, sw: 1.8, tex: function (x0, x1, h) { return D.stones(x0, x1, h); } });
    var bodyPts = [g.pts[2], g.pts[3], g.pts[4], g.pts[5], g.pts[6], g.P(-B.HW, o.root), g.P(-B.HW, -o.root)];
    var bodyRole = ['flank', 'face', 'face', 'flank', 'curtain', 'gorge', 'curtain'];
    var gb = { role: bodyRole };
    s += B.solid(ctx, bodyPts, null, 0, HB, { face: P.granite, top: P.walk, sw: 1.9, tex: faceTex(gb), topTex: function (top) { return slabs(ctx, top, 9); } });
    // 墙带走道板缝
    s += slabs(ctx, B.lift(band, H), 9);
    // 垛：墙带两侧（走道高 H）+ 堡身外缘（走道高 HB）
    var cb = crenels(g, es), bes = K.edgesOf(bodyPts), cbody = crenels({ role: bodyRole }, bes);
    function onBody(b) { var c = B.centroid(b.pts); return B.inPoly(bodyPts, c[0], c[1]); }
    var back = cb.back.filter(function (b) { return !onBody(b); }), front = cb.front.filter(function (b) { return !onBody(b); });
    var bBack = cbody.back.filter(function (b, i) { return true; }), bFront = cbody.front;
    function mer(b, z, frontSide) { return frontSide ? D.merlon(ctx, b.pts, z, 10, true) + D.merlon(ctx, scale(b.pts, 1.12), z + 10, 2.4, true) : D.merlon(ctx, b.pts, z, b.vert ? 5 : 6, false); }
    back.forEach(function (b) { s += mer(b, H, false); });
    bBack.forEach(function (b) { s += mer(b, HB, false); });
    // 尖角铜顶哨亭（八角）+ 符文 + 矮人红旗
    var tc = g.P(o.tip - 30, 0), hut = K.octo(tc[0], tc[1], 11, 0.4);
    s += K.prism(ctx, hut, HB, 16, { face: P.granite2, top: P.granite3, sw: 1.4, tex: function (x0, x1, h) { return D.stones(x0, x1, h, false); } });
    var ty = tc[1] - HB - 16;
    s += path('M' + f(tc[0] - 14) + ' ' + f(ty + 2) + 'L' + f(tc[0]) + ' ' + f(ty - 14) + 'L' + f(tc[0] + 14) + ' ' + f(ty + 2) + 'Z', P.copper, 1.3) +
      path('M' + f(tc[0]) + ' ' + f(ty - 14) + 'L' + f(tc[0] + 14) + ' ' + f(ty + 2) + 'L' + f(tc[0] + 2) + ' ' + f(ty + 2) + 'Z', P.copper2, 0, 0.7) +
      line('M' + f(tc[0] - 9) + ' ' + f(ty - 2) + 'l5 -5M' + f(tc[0] - 4) + ' ' + f(ty + 1) + 'l7 -8', 0.7, 0.5) + D.rune(tc[0], tc[1] - HB - 8, 2.6, P.verd2, 1);
    s += D.slit(tc[0] - 5, tc[1] - HB - 2, 8) + D.slit(tc[0] + 5, tc[1] - HB - 2, 8);
    s += line('M' + f(tc[0]) + ' ' + f(ty - 14) + 'V' + f(ty - 34), 1.8) + path('M' + f(tc[0]) + ' ' + f(ty - 34) + 'h13l-3 4.5l3 4.5h-13Z', P.red, 1.1) + D.rune(tc[0] + 6, ty - 29.5, 2.2, P.ember, 3);
    ctx.top(ty - 36);
    // 堡身中央：一门架在铜座上的矮人炮（朝尖角）
    var cc = g.P(o.root + 14, 0), cz = cc[1] - HB, u = g.u;
    s += C.ell(cc[0], cz, 9, 5.5, P.copper2, 1.2) + C.ell(cc[0], cz - 1.5, 6, 3.6, P.copper, 0.9);
    var mz = [cc[0] + u[0] * 16, cz + u[1] * 9 - 4];
    s += line('M' + f(cc[0] - u[0] * 4) + ' ' + f(cz - 3 - u[1] * 2) + 'L' + f(mz[0]) + ' ' + f(mz[1]), 6, 1) + line('M' + f(cc[0] - u[0] * 4) + ' ' + f(cz - 3 - u[1] * 2) + 'L' + f(mz[0]) + ' ' + f(mz[1]), 4, 1, P.iron) +
      C.ell(mz[0], mz[1], 2.6, 2.2, '#3e3a36', 0.8);
    front.forEach(function (b) { s += mer(b, H, true); });
    bFront.forEach(function (b) { s += mer(b, HB, true); });
    return s;
  }

  // ---------- 阶梯山城（landmark，6×6） ----------
  /** 铜烟囱：底中心 (x, yb)，高 h，宽 w；铁箍 + 帽 + 三团烟 */
  function chimney(ctx, x, yb, h, w) {
    var x0 = x - w / 2, ty = yb - h, s = rect(x0, ty, w, h, P.copper, 1.4) + rect(x + w * 0.1, ty, w * 0.4, h, P.copper2, 0, 0.7);
    for (var y = yb - 8; y > ty + 4; y -= 11) s += rect(x0 - 1, y - 2, w + 2, 3, P.iron, 1);
    s += rect(x0 - 3, ty - 4, w + 6, 5, P.iron, 1.2) + rect(x0 - 1, ty - 7, w + 2, 3, P.copper2, 1);
    s += C.ell(x - 1, ty - 13, 6, 4.5, '#e9dcc0', 0.9) + C.ell(x + 5, ty - 22, 8, 5.5, '#e9dcc0', 0.9) + C.ell(x + 12, ty - 33, 10, 6.5, '#efdfb2', 0.8);
    s += line('M' + f(x - 3) + ' ' + f(ty - 13) + 'q2 -2 4 0M' + f(x + 3) + ' ' + f(ty - 23) + 'q3 -2 6 0', 0.7, 0.5);
    ctx.top(ty - 40);
    return s;
  }
  /** 立面台阶：x0..x1，底 yb，高 h，每级 5 px */
  function stair(x0, x1, yb, h) {
    var s = rect(x0 - 3, yb - h, x1 - x0 + 6, h, P.granite3, 1.3) + rect(x0, yb - h, x1 - x0, h, P.walk, 0), d = '', sd = '';
    for (var y = yb - 5; y > yb - h; y -= 5) { d += 'M' + f(x0) + ' ' + f(y) + 'H' + f(x1); sd += 'M' + f(x0) + ' ' + f(y + 1.6) + 'H' + f(x1); }
    return s + line(sd, 1.6, 0.18, P.shadow) + line(d, 0.9, 0.7) + line('M' + f(x0) + ' ' + f(yb) + 'V' + f(yb - h) + 'M' + f(x1) + ' ' + f(yb) + 'V' + f(yb - h), 1.1);
  }
  /** 前沿厚垛 / 后沿矮垛一排：x 从 a 到 b，地面 y，走道高 z */
  function merlonRow(ctx, a, b, y, z, front) {
    var s = '';
    for (var x = a; x + 9 <= b; x += 12) s += front ? D.merlon(ctx, [[x, y - 4], [x + 9, y - 4], [x + 9, y], [x, y]], z, 10, true) + D.merlon(ctx, scale([[x, y - 4], [x + 9, y - 4], [x + 9, y], [x, y]], 1.12), z + 10, 2.4, true)
      : D.merlon(ctx, [[x, y], [x + 9, y], [x + 9, y + 4], [x, y + 4]], z, 6, false);
    return s;
  }
  function tier(ctx, x0, x1, yb, yf, h) {
    var pts = [[x0, yb], [x1, yb], [x1, yf], [x0, yf]];
    return K.prism(ctx, pts, 0, h, { face: P.granite, top: P.walk, sw: 1.9, tex: function (a, b, hh) { return D.stones(a, b, hh); } }) + slabs(ctx, B.lift(pts, h), 10);
  }
  /** 阶梯石城：后方山体 + 三层凿山石台（逐层后退升高）+ 中轴大台阶 + 底层巨门（双铜扇、符文门楣、守门石像柱）+ 铜烟囱 + 顶层铜顶议事厅 */
  function fortress(ctx) {
    var s = '', T1 = 52, T2 = 104, T3 = 156;
    s += C.shadow('M30 -6L284 -6L284 -200L230 -260Z', 0.15);
    // 山体
    s += path('M0 -120L10 -260L40 -360L80 -430L120 -478L150 -500L180 -470L214 -440L248 -380L274 -300L288 -200L288 -110Z', P.granite3, 1.9);
    s += path('M150 -500L180 -470L214 -440L248 -380L274 -300L288 -200L288 -110L230 -240L190 -380Z', P.granite, 0);
    s += line('M150 -500L190 -380L230 -240M80 -430L96 -350M40 -360L60 -300M214 -440L204 -380M248 -380L236 -320', 1, 0.55);
    s += line('M150 -500L180 -470L214 -440L248 -380L274 -300L288 -200L288 -110', 1.9);
    s += path('M108 -462l8 -7l7 5l-5 6ZM60 -380l6 -4l4 5l-6 2ZM236 -350l5 -5l5 4l-4 4Z', P.moss, 0.8);
    s += path('M120 -478l8 -6l8 4l-4 -10l12 -10l14 8l6 -6l4 12l-14 4l-12 -2l-10 6Z', P.paper, 1.1);
    // 第三层（最后、最高）
    s += tier(ctx, 78, 210, -244, -184, T3);
    s += merlonRow(ctx, 82, 206, -244, T3, false);
    var hy = -184 - T3;
    for (var i = 0; i < 4; i++) s += D.slit(98 + i * 30, -184 - 112, 14);
    s += rect(100, -184 - T3 + 6, 88, 9, P.deep, 1.2);
    for (i = 0; i < 9; i++) s += D.rune(105 + i * 9.6, -184 - T3 + 10.5, 3, P.verd2, i);
    s += D.copperDoor(144, -184 - T2, 24, 34) + stair(184, 200, -184 - T2, T3 - T2);
    // 顶层议事厅：石墙 + 铜坡顶
    var hall = [[112, -238], [176, -238], [176, -204], [112, -204]];
    s += K.prism(ctx, hall, T3, 26, { face: P.granite2, top: P.granite3, sw: 1.6, tex: function (a, b, hh) { return D.stones(a, b, hh, false); } });
    var ry = -204 - T3 - 26;
    s += path('M106 ' + f(ry + 2) + 'L120 ' + f(ry - 40) + 'L168 ' + f(ry - 40) + 'L182 ' + f(ry + 2) + 'Z', P.copper, 1.6) +
      path('M144 ' + f(ry - 40) + 'L168 ' + f(ry - 40) + 'L182 ' + f(ry + 2) + 'L144 ' + f(ry + 2) + 'Z', P.copper2, 0, 0.55) +
      line('M118 ' + f(ry - 8) + 'H170M114 ' + f(ry - 20) + 'H173M117 ' + f(ry - 31) + 'H171', 0.8, 0.5, P.iron) + line('M120 ' + f(ry - 40) + 'H168', 2.4, 1, P.iron);
    s += path('M134 ' + f(ry + 26) + 'V' + f(ry + 12) + 'Q144 ' + f(ry + 4) + ' 154 ' + f(ry + 12) + 'V' + f(ry + 26) + 'Z', P.hole, 1) + D.rune(144, ry - 20, 4, P.ember, 2);
    s += chimney(ctx, 124, ry - 30, 30, 8) + chimney(ctx, 196, -230 - T3, 40, 10);
    s += line('M144 ' + f(ry - 40) + 'V' + f(ry - 64), 1.8) + path('M144 ' + f(ry - 64) + 'h16l-3 5l3 5h-16Z', P.red, 1.1);
    ctx.top(ry - 66);
    return s + fortressFront(ctx, T1, T2, T3);
  }

  /** 守门石像柱：底中心 (x, yb)：方柱 + 戴盔矮人头像 + 胡须 */
  function guardian(x, yb, h) {
    var ty = yb - h, s = rect(x - 7, ty, 14, h, P.granite2, 1.4) + rect(x + 1, ty, 6, h, P.granite, 0, 0.6) + rect(x - 9, yb - 6, 18, 6, P.deep, 1.2);
    s += path('M' + f(x - 8) + ' ' + f(ty) + 'Q' + f(x) + ' ' + f(ty - 16) + ' ' + f(x + 8) + ' ' + f(ty) + 'Z', P.copper, 1.2) + line('M' + f(x - 9) + ' ' + f(ty) + 'h18', 1.6, 1, P.iron);
    s += path('M' + f(x - 6) + ' ' + f(ty + 4) + 'L' + f(x) + ' ' + f(ty + 22) + 'L' + f(x + 6) + ' ' + f(ty + 4) + 'Z', P.granite3, 1) + line('M' + f(x - 3) + ' ' + f(ty + 6) + 'l3 12l3 -12', 0.7, 0.6);
    s += C.ell(x - 2.6, ty + 2.4, 1.1, 0.9, P.hole, 0) + C.ell(x + 2.6, ty + 2.4, 1.1, 0.9, P.hole, 0);
    return s + D.rune(x, yb - h * 0.35, 3, P.verd2, 2);
  }
  /** 巨门：中心 cx、底 yb：深拱 + 双铜扇（D.copperDoor 放大）+ 符文门楣 + 铁闸齿 */
  function greatGate(cx, yb) {
    var s = D.copperDoor(cx, yb, 40, 46);
    s += rect(cx - 30, yb - 58, 60, 10, P.deep, 1.3);
    for (var i = 0; i < 6; i++) s += D.rune(cx - 24 + i * 9.6, yb - 53, 3.2, P.ember, i);
    var d = '';
    for (var x = cx - 16; x <= cx + 16; x += 6.4) d += 'M' + f(x) + ' ' + f(yb - 44) + 'v5l1 2';
    return s + line(d, 1.6, 1, P.iron);
  }
  function fortressFront(ctx, T1, T2, T3) {
    var s = '';
    // 第二层
    s += tier(ctx, 46, 242, -184, -124, T2);
    s += merlonRow(ctx, 50, 76, -184, T2, false) + merlonRow(ctx, 212, 238, -184, T2, false);
    s += D.copperDoor(96, -176, 16, 26) + D.copperDoor(192, -176, 16, 26);
    for (var i = 0; i < 3; i++) s += D.gunport(64 + i * 80, -196, 4);
    s += chimney(ctx, 60, -176 - T2 + 8, 34, 9) + chimney(ctx, 228, -150 - T2, 28, 8);
    s += stair(132, 156, -124 - T2, T3 - T2 - 4);
    s += merlonRow(ctx, 50, 128, -124, T2, true) + merlonRow(ctx, 160, 238, -124, T2, true);
    // 第一层（最前）：巨门、石像柱、炮眼、厚垛
    s += tier(ctx, 14, 274, -124, -10, T1);
    s += stair(134, 154, -176, T2 - T1);
    s += greatGate(144, -10);
    s += guardian(102, -10, 44) + guardian(186, -10, 44);
    s += D.gunport(46, -32, 4.5) + D.gunport(242, -32, 4.5) + D.slit(74, -22, 14) + D.slit(214, -22, 14);
    s += rect(40, -10 - T1 + 4, 40, 7, P.deep, 1) + rect(208, -10 - T1 + 4, 40, 7, P.deep, 1);
    for (i = 0; i < 4; i++) s += D.rune(45 + i * 10, -10 - T1 + 7.5, 2.4, P.verd2, i) + D.rune(213 + i * 10, -10 - T1 + 7.5, 2.4, P.verd2, i + 2);
    // 第一轮截图：底层台面是一整块空灰板，补两座铜坡顶石屋（左为锻炉房带铜烟囱）+ 中轴石板道 + 铁砧
    s += terraceHouse(ctx, 30, 92, -116, -82, T1, true) + terraceHouse(ctx, 196, 258, -116, -82, T1, false);
    s += path('M132 ' + f(-124 - T1) + 'L156 ' + f(-124 - T1) + 'L158 ' + f(-14 - T1) + 'L130 ' + f(-14 - T1) + 'Z', P.granite3, 1, 0.9) + line('M131 ' + f(-50 - T1) + 'h26M131 ' + f(-80 - T1) + 'h26', 0.8, 0.5);
    s += anvil(110, -54 - T1) + anvil(178, -54 - T1);
    s += merlonRow(ctx, 18, 120, -10, T1, true) + merlonRow(ctx, 168, 270, -10, T1, true);
    return s;
  }
  /** 台面石屋：地面 x0..x1 × yb..yf，墙脚抬高 z；铜坡顶（屋脊东西向）+ 铜门；forge = 加铜烟囱与炉火窗 */
  function terraceHouse(ctx, x0, x1, yb, yf, z, forge) {
    var pts = [[x0, yb], [x1, yb], [x1, yf], [x0, yf]], h = 20, s = '';
    s += C.shadow(C.poly(B.lift(pts, z).map(function (p) { return [p[0] + 6, p[1] + 4]; })), 0.16);
    s += K.prism(ctx, pts, z, h, { face: P.granite2, top: P.granite3, sw: 1.5, tex: function (a, b, hh) { return D.stones(a, b, hh, false); } });
    var ey = yf - z - h, ry = (yb + yf) / 2 - z - h - 14;
    s += path('M' + f(x0 - 3) + ' ' + f(ey + 2) + 'L' + f(x0 + 2) + ' ' + f(ry) + 'L' + f(x1 - 2) + ' ' + f(ry) + 'L' + f(x1 + 3) + ' ' + f(ey + 2) + 'Z', P.copper, 1.4);
    s += path('M' + f(x0 + 2) + ' ' + f(ry) + 'L' + f(x1 - 2) + ' ' + f(ry) + 'L' + f(x1 - 2) + ' ' + f(yb - z - h) + 'L' + f(x0 + 2) + ' ' + f(yb - z - h) + 'Z', P.copper2, 1.1);
    var d = ''; for (var x = x0 + 6; x < x1 - 2; x += 7) d += 'M' + f(x) + ' ' + f(ey + 1) + 'L' + f(x + 1) + ' ' + f(ry + 2);
    s += line(d, 0.7, 0.5);
    s += D.copperDoor((x0 + x1) / 2, yf - z, 11, 15);
    if (forge) {
      s += rect(x0 + 6, yf - z - 14, 9, 7, P.fire, 1) + rect(x0 + 8, yf - z - 12, 5, 3, P.ember, 0);
      s += chimney(ctx, x1 - 12, ry + 4, 22, 7);
    } else s += D.slit(x0 + 10, yf - z - 6, 9) + D.slit(x1 - 10, yf - z - 6, 9);
    ctx.top(ry - 2);
    return s;
  }
  /** 铁砧：底中心 (x, y) */
  function anvil(x, y) {
    return rect(x - 4, y - 6, 8, 6, P.deep, 1) + path('M' + f(x - 9) + ' ' + f(y - 10) + 'h16l2 -2h-4v-2h-13l-2 2Z', P.iron, 1) + C.ell(x + 7, y - 2, 3, 1.6, P.granite3, 0.8);
  }

  function types() {
    var out = [];
    K.DIRS.forEach(function (d) {
      out.push({ id: 'west-dwarf-bastion-' + d, race: 'dwarf', category: 'fort', kind: 'stone_bastion', facility: 'watchtower', fp: [3, 3], roof: 'none',
        tags: ['bastion', 'point_' + d, 'replaces_wall_cells', 'gunport', 'rune', 'attach_' + B.THRU[d].join('_')],
        attach: B.attachCells(d, 3), thru: B.THRU[d],
        note: '石棱堡（3×3）：尖角朝 ' + d + '；巨石墙带与城墙同高同厚，两端切在' + (d.length === 1 ? '格边中点' : '格角') + '，接同族 wallspoke-' + B.THRU[d].join(' / ') +
          '；五边形堡身高出墙 10，侧翼与棱面开铜铆炮门、棱面符文带、尖角铜顶哨亭与红旗、堡内铜座矮人炮。放置时替掉 attach 墙格的辐条与节点。facility 无棱堡专项，取 watchtower',
        draw: function (ctx) { return bastion(ctx, d); } });
    });
    out.push({ id: 'west-dwarf-fortress-01', race: 'dwarf', category: 'landmark', kind: 'terraced_mountain_city', facility: 'lord_hall', fp: [6, 6], roof: 'gable_tile', culture: 'dwarf',
      tags: ['landmark', 'fortress', 'mountain', 'terraced', 'great_gate', 'copper_chimney', 'rune'],
      note: '阶梯山城（6×6）：后方山体 + 三层凿山石台逐层后退升高 + 中轴台阶 + 底层符文巨门与守门石像柱 + 铜烟囱 + 顶层铜坡顶议事厅。roof 为铜坡顶，取最近的 gable_tile；facility 取 lord_hall（领主议事厅）',
      draw: fortress });
    return out;
  }
  var API = { types: types, bastion: bastion, fortress: fortress, gunDoor: gunDoor, chimney: chimney, SHAPE: SHAPE };
  root.TownArtRF2_dwarf = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
