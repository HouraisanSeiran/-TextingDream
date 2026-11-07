/*
 * 织梦 · 矮人民居 B 组（04–06）：圆石塔屋、矿工长屋、铜烟囱作坊宅（美术样板，尚未接入游戏）
 * 局部坐标同 houses-a.js。浏览器挂 window.TownArtWD_housesB；Node 用 module.exports。依赖 core.js、parts.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWD_core;
  var K = isNode ? require('./parts.js') : root.TownArtWD_parts;
  var P = C.PAL, f = C.f;

  /** 圆石鼓身：中心 cx，底椭圆中心 yc（前沿在 yc+ry），半轴 rx/ry，高 h。石层沿椭圆弧，错缝竖缝。返回 { svg, yt } */
  function drum(ctx, cx, yc, rx, ry, h) {
    var x0 = cx - rx, x1 = cx + rx, yt = yc - h, s = '', d = '', k;
    function bulge(x) { var t = (x - cx) / rx; return ry * Math.sqrt(Math.max(0, 1 - t * t)); }
    var D = 'M' + f(x0) + ' ' + f(yt) + 'V' + f(yc) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 0 ' + f(x1) + ' ' + f(yc) + 'V' + f(yt) +
      'A' + f(rx) + ' ' + f(ry) + ' 0 0 1 ' + f(x0) + ' ' + f(yt) + 'Z';
    for (k = 1; yc - k * 8 > yt + 2; k++) d += 'M' + f(x0) + ' ' + f(yc - k * 8) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 0 ' + f(x1) + ' ' + f(yc - k * 8);
    for (k = 0; yc - k * 8 > yt + 2; k++) {
      for (var a = -1.3 + (k % 2) * 0.32; a < 1.3; a += 0.64) {
        var x = cx + Math.sin(a) * rx, y = yc - k * 8 + bulge(x);
        d += 'M' + f(x) + ' ' + f(y) + 'v' + f(-Math.min(8, y - yt));
      }
    }
    var tex = C.line(d, 0.85, 0.6) + C.rect(cx + rx * 0.42, yt - ry, rx * 0.6, h + 2 * ry, P.shadow, 0, 0.16) +
      C.rect(x0, yc - 5, 2 * rx, 5 + ry, P.deep, 0, 0.35);
    s += C.face(ctx, D, P.granite2, tex, 1.8);
    ctx.top(yt - ry);
    return { svg: s, yt: yt, bulge: bulge };
  }
  /** 鼓身平顶 + 垛口 */
  function drumTop(ctx, cx, yt, rx, ry) {
    var s = '', i, back = '', front = '';
    for (i = -2; i <= 2; i++) {
      var x = cx + i * rx * 0.4, b = ry * Math.sqrt(Math.max(0, 1 - Math.pow(i * 0.4, 2)));
      back += C.rect(x - 2.6, yt - b - 5, 5.2, 5.5, P.granite3, 1);
      front += C.rect(x - 2.8, yt + b - 6, 5.6, 6.5, P.granite2, 1.1);
    }
    s += back + C.ellipse(cx, yt, rx, ry, P.granite3, 1.6) + C.ellipse(cx, yt + 0.6, rx - 3, ry - 1.8, '#a8a397', 0.9) + front;
    ctx.top(yt - ry - 5);
    return s;
  }
  /** 锥形石板顶：底椭圆 (cx, yt) 半轴 rx+ov / ry+1，尖 rise */
  function cone(ctx, cx, yt, rx, ry, rise, fill) {
    var a = rx + 3, b = ry + 1.5, ap = yt - rise, d = '', i;
    var D = 'M' + f(cx - a) + ' ' + f(yt) + 'A' + f(a) + ' ' + f(b) + ' 0 0 0 ' + f(cx + a) + ' ' + f(yt) + 'L' + f(cx) + ' ' + f(ap) + 'Z';
    for (i = -3; i <= 3; i++) { var t = i / 3.6; d += 'M' + f(cx) + ' ' + f(ap) + 'L' + f(cx + t * a) + ' ' + f(yt + b * Math.sqrt(1 - t * t)); }
    for (i = 1; i < 4; i++) {
      var k = i / 4, ra = a * (1 - k);
      d += 'M' + f(cx - ra) + ' ' + f(yt - rise * k) + 'A' + f(ra) + ' ' + f(b * (1 - k)) + ' 0 0 0 ' + f(cx + ra) + ' ' + f(yt - rise * k);
    }
    var tex = C.line(d, 0.8, 0.5) + C.path(C.poly([[cx, ap], [cx + a * 0.2, yt + b], [cx + a + 2, yt + b], [cx + a + 2, ap]]), P.shadow, 0, 0.17);
    var s = C.face(ctx, D, fill || P.slate, tex, 1.7);
    s += C.rect(cx - 1.2, ap - 8, 2.4, 8, P.copper, 0.8) + C.circle(cx, ap - 9, 2.2, P.verd, 0.9);
    ctx.top(ap - 11.5);
    return s;
  }
  /** 铜烟道：中心 cx，底 yb，宽 w，高 h；铜箍 + 铆钉 + 铜绿斑，顶上铜绿伞帽 */
  function flue(ctx, cx, yb, w, h, smoke) {
    var x0 = cx - w / 2, yt = yb - h, s = '', i;
    var tex = C.rect(cx + w * 0.15, yt, w * 0.35, h, P.copper2, 0) + C.rect(x0, yt, w, h, P.shadow, 0, 0.06);
    for (i = 0; i < 3; i++) tex += C.rect(x0 + ctx.rnd(0, w * 0.4), yt + ctx.rnd(4, h - 6), ctx.rnd(2, 3.5), ctx.rnd(2, 4), P.verd, 0, 0.75);
    s += C.face(ctx, C.rectD(x0, yt, w, h), P.copper, tex, 1.3);
    for (var y = yb - 6; y > yt + 4; y -= 11) s += C.rect(x0 - 1, y - 1.3, w + 2, 2.6, P.copper2, 0.9) + C.rivets(x0 + 1, x0 + w - 1, y, 2.5, 0.45);
    s += C.path(C.poly([[x0 - 3, yt - 2], [cx, yt - 7], [x0 + w + 3, yt - 2]]), P.verd, 1.1) + C.line('M' + f(cx) + ' ' + f(yt - 2) + 'V' + f(yt), 1.1);
    ctx.top(yt - 7);
    if (smoke) s += K.smoke(ctx, cx - 2, yt - 7, smoke);
    return s;
  }
  /** 矿坑式木框门洞：两立柱 + 过梁 + 斜撑，洞里黑 */
  function portal(ctx, cx, yb, w, h) {
    var x0 = cx - w / 2, x1 = cx + w / 2, y = yb - h, s = '';
    s += C.rect(x0, y, w, h, P.hole, 1.2);
    s += C.rect(x0 - 2.5, y, 3, h, P.timber, 1) + C.rect(x1 - 0.5, y, 3, h, P.timber, 1);
    s += C.rect(x0 - 4, y - 3.5, w + 8, 4, P.dark, 1.2);
    s += C.line('M' + f(x0 + 0.5) + ' ' + f(y + 4) + 'l4 -4M' + f(x1 - 0.5) + ' ' + f(y + 4) + 'l-4 -4', 1.6, 1, P.timber);
    s += C.circle(cx, y + 4, 1.4, P.ember, 0.6) + C.line('M' + f(cx) + ' ' + f(y) + 'v3', 0.7);
    ctx.top(y - 3.5);
    return s;
  }
  /** 矿石堆 */
  function ore(ctx, x, yb, n) {
    var s = '';
    for (var i = 0; i < n; i++) {
      var ox = x + i * 3.6 - (i > 2 ? 9 : 0), oy = yb - (i > 2 ? 3.4 : 0), w = ctx.rnd(4, 5.5);
      s += C.path(C.poly([[ox, oy], [ox + 0.8, oy - 3], [ox + w * 0.6, oy - 4], [ox + w, oy - 1.5], [ox + w, oy]]), i % 3 === 1 ? P.copper : P.deep, 0.8);
    }
    return s;
  }

  var T = [];

  // 04 圆石塔屋：圆鼓身石塔，锥形石板顶（v1）/ 垛口平顶 + 侧翼（v2）/ 矮胖铜绿锥顶（v3）
  T.push({
    n: 4, kind: 'house_tower', name: '圆石塔屋', fps: [[1, 1], [2, 1], [1, 1]], roof: 'steep_slate',
    tags: ['two_storey', 'round_tower', 'stone'], note: '圆鼓身石塔；v2 为垛口平顶',
    draw: function (ctx, v) {
      var s = '', D;
      if (v.i === 2) {
        s += C.groundShadow(6, 84, 0, -36);
        s += C.blocks(ctx, 6, 54, 0, 22) + K.slabRoof(ctx, 6, 54, -22, 26, 6, { ov: 2 }).svg;
        s += C.door(ctx, 24, 0, 11, 15, 'lintel', { fill: v.door, band: v.band }) + C.win(ctx, 39, -15, 6, 6, 'square');
        D = drum(ctx, 68, -7, 16, 6, 54);
        s += D.svg + drumTop(ctx, 68, D.yt, 16, 6) + K.chimney(ctx, 74, D.yt - 4, 5, 10, { cap: 'ring', smoke: 2 });
        s += C.win(ctx, 65, -30, 6, 8, 'slit') + C.win(ctx, 64, -48, 8, 8, 'port');
        return s;
      }
      var rx = v.i === 3 ? 19 : 15, ry = v.i === 3 ? 7 : 6, h = v.i === 3 ? 30 : 46;
      s += C.groundShadow(24 - rx, 24 + rx, 0, -24);
      D = drum(ctx, 24, -ry - 1, rx, ry, h);
      s += D.svg + cone(ctx, 24, D.yt, rx, ry, v.i === 3 ? 15 : 26, v.i === 3 ? P.verd : P.slate);
      s += C.door(ctx, 24, -1.5, 10, 14, 'arch', { fill: v.door, band: v.band, frame: 3 });
      if (v.i === 3) s += C.win(ctx, 6, -22, 6, 6, 'port') + C.win(ctx, 36, -22, 6, 6, 'port');
      else s += C.win(ctx, 22.5, -32, 3.5, 8, 'slit') + C.win(ctx, 21, -48, 6, 6, 'port');
      return s;
    }
  });

  // 05 矿工长屋：横向很长的低矮石屋，低坡石板顶，侧边矿坑门洞 + 轨道 + 矿车
  T.push({
    n: 5, kind: 'house_longhouse', name: '矿工长屋', fps: [[2, 1], [2, 2], [2, 1]], roof: 'gable_tile',
    tags: ['one_storey', 'longhouse', 'mine_track'], note: '低坡石板顶，最近 RoofId 为 gable_tile（石板代瓦）',
    draw: function (ctx, v) {
      var s = '', x0 = 3, x1 = 93, deep = v.fp[1] === 2, h = deep ? 22 : 19, dg = deep ? 60 : 28;
      s += C.groundShadow(x0, x1, 0, -dg - 8);
      if (v.i === 3) { // 一端埋进岩坡
        s += C.rockSlope(ctx, 58, 96, 0, 46, { lo: 0.6, moss: 2 });
        x1 = 70;
      }
      s += C.blocks(ctx, x0, x1, 0, h, { minW: 14, maxW: 26 });
      var R = K.slabRoof(ctx, x0, x1, -h, dg, deep ? 10 : 7, { ov: 3, rivet: v.i === 2 });
      s += R.svg;
      s += K.chimney(ctx, x0 + 14, R.yR + 4, 6, 11, { smoke: 2 });
      if (deep) s += K.chimney(ctx, x1 - 18, R.yR + 4, 6, 13, { cap: 'copper', smoke: 3 });
      var dx = v.i === 3 ? 22 : 30;
      s += C.door(ctx, dx, 0, 11, 15, 'lintel', { fill: v.door, band: v.band });
      var wx = v.i === 3 ? [42, 58] : [50, 66, 82];
      if (v.i !== 3) wx = deep ? [10, 50, 66, 82] : [50, 66, 82];
      wx.forEach(function (x) { if (Math.abs(x - dx) > 12) s += C.win(ctx, x - 3, -14, 6, 6, 'square'); });
      if (v.i === 3) {
        s += portal(ctx, 80, -2, 12, 16) + K.rails(62, 96, -3) + K.cart(ctx, 63, -1, 10);
      } else {
        s += ore(ctx, x0 + 1, -0.5, 4);
        s += K.rails(4, 22, -2);
      }
      return s;
    }
  });

  // 06 铜烟囱作坊宅：石屋 + 侧面粗铜烟道（铜箍、铜绿），熔火映窗，墙上齿轮
  T.push({
    n: 6, kind: 'house_workshop', name: '铜烟囱作坊宅', fps: [[1, 1], [2, 1], [2, 2]], roof: 'flat_mud',
    tags: ['two_storey', 'workshop', 'copper_flue', 'shop'], note: '石板平顶 + 铜烟道，最近 RoofId 为 flat_mud',
    draw: function (ctx, v) {
      var W = v.fp[0] * 48, s = '', deep = v.fp[1] === 2;
      if (v.i === 1) {
        s += C.groundShadow(4, 40, 0, -34);
        s += C.blocks(ctx, 4, 34, 0, 34) + C.slabTop(ctx, 4, 34, -34, 18);
        s += flue(ctx, 39, 0, 7, 60, 3);
        s += C.door(ctx, 16, 0, 10, 15, 'lintel', { fill: v.door, band: v.band });
        s += C.win(ctx, 24, -14, 6, 6, 'fire') + C.win(ctx, 10, -29, 6, 6, 'square') + C.win(ctx, 22, -29, 6, 6, 'square');
        s += K.gear(ctx, 37, -14, 4, 8);
        return s;
      }
      var x1 = W - 16, h = deep ? 40 : 30, dg = deep ? 56 : 24;
      s += C.groundShadow(4, W - 4, 0, -dg - 6);
      s += C.blocks(ctx, 4, x1, 0, h) + C.slabTop(ctx, 4, x1, -h, dg);
      if (deep) s += C.blocks(ctx, 12, 46, -h - 10, 14) + C.slabTop(ctx, 12, 46, -h - 24, 18);
      s += flue(ctx, W - 10, 0, 9, deep ? 92 : 66, 3) + flue(ctx, 30, -h - 8, 7, 18, 2);
      // 作坊大门：双开铜门 + 门楣铜牌
      s += C.door(ctx, 22, 0, 16, 18, 'trap', { fill: P.copper, band: P.iron, bands: 3 });
      s += C.rect(14, -26, 16, 5, P.verd, 1) + K.gear(ctx, 22, -23.5, 2.2, 6, { fill: P.ember });
      s += C.win(ctx, 40, -15, 8, 7, 'fire') + C.win(ctx, 56, -15, 8, 7, 'fire');
      if (deep) s += C.win(ctx, 40, -33, 7, 7, 'square') + C.win(ctx, 56, -33, 7, 7, 'square') + C.runes(ctx, 6, x1 - 2, -h + 4, 5);
      s += K.gear(ctx, x1 - 6, -h + 9, 5, 9, { rot: 0.2 }) + K.gear(ctx, x1 - 13, -h + 4, 3, 7, { rot: 0.5, fill: P.verd2 });
      return s;
    }
  });

  var API = { T: T, drum: drum, drumTop: drumTop, cone: cone, flue: flue, portal: portal, ore: ore };
  root.TownArtWD_housesB = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
