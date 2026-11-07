/*
 * 织梦 · race-fort 矮人族：巨石城墙辐条 + 墙节点 + 矮堡塔 + 嵌山石堡 + 石棱堡（美术样板，尚未接入游戏）
 * 墙高 44、墙厚 24、巨石层高 11 / 块长 24 / 错缝 12、深岩勒脚、走道色 #a8a397、
 * 北沿矮垛（9×7）、南沿厚方垛（9×12 + 压顶石），全部照 west-dwarf/tiles.js。
 * 浏览器挂 window.TownArtRF_dwarf；Node 用 module.exports。依赖 core.js、spoke.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtRF_core;
  var K = isNode ? require('./spoke.js') : root.TownArtRF_spoke;
  var P = C.P, f = C.f, line = C.line, path = C.path, rect = C.rect, H = 44;
  var TONES = [P.granite2, P.granite, '#a29d93', P.granite3];

  /** 巨石立面（平直坐标：底 y = 0，顶 y = -h），块缝按格内 x 对齐（周期 24 整除 48） */
  function stones(x0, x1, h, plinth) {
    var s = '', joints = '', courses = '', r = 0, course = 11;
    for (var y = 0; y > -h + 0.1; y -= course, r++) {
      var y0 = Math.max(-h, y - course), off = (r % 2) * 12;
      for (var k = Math.floor((x0 - off) / 24) - 1; off + k * 24 < x1; k++) {
        var bx0 = Math.max(x0, off + k * 24), bx1 = Math.min(x1, off + (k + 1) * 24);
        if (bx1 - bx0 < 0.3) continue;
        var tone = r === 0 && plinth !== false ? P.deep : TONES[((k * 3 + r) % 4 + 4) % 4];
        s += rect(bx0, y0, bx1 - bx0, y - y0, tone, 0) + rect(bx0, y - 1.8, bx1 - bx0, 1.8, P.shadow, 0, 0.14);
        var jx = off + k * 24;
        if (jx > x0 + 0.1 && jx < x1 - 0.1) joints += 'M' + f(jx) + ' ' + f(y) + 'V' + f(y0);
        var hx = off + (k + 1) * 24 - 6;
        if (r > 0 && hx > x0 + 1 && hx < x1 - 3) courses += 'M' + f(hx) + ' ' + f(y - 2.5) + 'l1.8 -2.6M' + f(hx + 2) + ' ' + f(y - 2.5) + 'l1.8 -2.6';
      }
      if (y0 > -h + 0.1) courses += 'M' + f(x0) + ' ' + f(y0) + 'H' + f(x1);
    }
    return s + line(courses + joints, 0.9, 0.6) + rect(x0, -h, x1 - x0, 3, P.shadow, 0, 0.16);
  }
  /** 一块垛（棱柱）：地面多边形 pts 抬到 z0，高 h */
  function merlon(ctx, pts, z0, h, front) {
    return K.prism(ctx, pts, z0, h, { face: front ? P.granite2 : P.granite2, top: P.granite3, sw: front ? 1.2 : 1.1 });
  }
  /** 沿辐条两侧放垛：b = ±12 一侧朝屏幕下方的是南沿厚垛，另一侧是北沿矮垛；正交南北向墙两侧都是窄侧垛 */
  function battlements(ctx, fr, a0) {
    var pA = K.at(fr, 10, 12), pB = K.at(fr, 10, -12), frontB = pA[1] > pB[1] || (pA[1] === pB[1] && pA[0] < pB[0]) ? 12 : -12;
    var ns = !fr.diag && (fr.dir === 'n' || fr.dir === 's');
    var back = [], front = [];
    K.beats(fr, 12, 0).forEach(function (a) {
      if (a < a0 - 1) return;
      if (ns) {
        back.push(K.block(fr, a, -10, 9, 4)); back.push(K.block(fr, a, 10, 9, 4));
      } else {
        back.push(K.block(fr, a, -frontB * 0.84, 9, 4));
        front.push(K.block(fr, a, frontB * 0.88, 9, 3));
      }
    });
    var key = function (pts) { return pts.reduce(function (m, p) { return m + p[1]; }, 0); };
    back.sort(function (a, b) { return key(a) - key(b); }); front.sort(function (a, b) { return key(a) - key(b); });
    var s = '';
    back.forEach(function (p) { s += merlon(ctx, p, H, ns ? 5 : 6, false); });
    front.forEach(function (p) { s += merlon(ctx, p, H, 10, true) + merlon(ctx, scale(p, 1.12), H + 10, 2.4, true); });
    return s;
  }
  function scale(pts, k) {
    var cx = 0, cy = 0; pts.forEach(function (p) { cx += p[0] / pts.length; cy += p[1] / pts.length; });
    return pts.map(function (p) { return [cx + (p[0] - cx) * k, cy + (p[1] - cy) * k]; });
  }
  /** 走道石板缝 */
  function walkway(fr, a0) {
    var d = '';
    K.beats(fr, 12, 0).forEach(function (a) {
      if (a < a0) return;
      var p = K.at(fr, a + 6, -12), q = K.at(fr, a + 6, 12);
      d += 'M' + f(p[0]) + ' ' + f(p[1] - H) + 'L' + f(q[0]) + ' ' + f(q[1] - H);
    });
    return line(d, 0.6, 0.35);
  }

  // ---------- 辐条 / 节点 / 矮堡塔 ----------
  function spoke(ctx, dir) {
    var g = K.spokeGeom(dir), fr = K.frame(dir), s = '';
    s += K.shadowOf(g.pts, 6, 3.5);
    s += K.prism(ctx, g.pts, 0, H, { face: P.granite, top: P.walk, sw: 1.8, tex: function (x0, x1, h) { return stones(x0, x1, h); } }, g.kinds);
    s += walkway(fr, fr.a0) + battlements(ctx, fr, fr.a0);
    ctx.top(-24 - 12 - H - 14);
    return s;
  }
  /** 墙内侧 → 箭缝（画在立面上，x 为格内坐标，底 yb） */
  function slit(x, yb, h) { return rect(x - 1.5, yb - h, 3, h, P.hole, 1) + rect(x - 3.5, yb - h - 3, 7, 3, P.granite3, 0.9); }
  /** 方墩四角垛 + 前沿两垛 */
  function corners(ctx, cx, cy, r, z) {
    var bs = [[cx - r, cy - r], [cx + r - 9, cy - r], [cx - r, cy + r - 6], [cx + r - 9, cy + r - 6]], s = '';
    bs.forEach(function (b, i) { var p = [[b[0], b[1]], [b[0] + 9, b[1]], [b[0] + 9, b[1] + 6], [b[0], b[1] + 6]]; s += merlon(ctx, p, z, i < 2 ? 7 : 11, i >= 2); });
    return s;
  }
  /** 墙节点：v=1 方墩（四角厚垛 + 箭缝）；v=2 符文墩（铜帽界石 + 青绿符文） */
  function node(ctx, v) {
    var g = K.nodeGeom(), hh = H + 6, s = '';
    s += K.shadowOf(g.pts, 6, 4);
    s += K.prism(ctx, g.pts, 0, hh, { face: P.granite, top: P.walk, sw: 1.8, tex: function (x0, x1, h) { return stones(x0, x1, h); } }, g.kinds);
    s += line('M10 ' + f(-38 - hh) + 'H38M10 ' + f(-24 - hh) + 'H38M24 ' + f(-38 - hh) + 'V' + f(-10 - hh), 0.6, 0.35);
    if (v === 2) {
      s += slit(24, -14, 14);
      // 界石：铜帽方柱 + 一枚符文
      s += K.prism(ctx, K.octo(24, -24, 5, 0.3), hh, 14, { face: P.granite3, top: P.granite2, sw: 1.2 });
      s += path('M18 ' + f(-24 - hh - 14) + 'L24 ' + f(-24 - hh - 22) + 'L30 ' + f(-24 - hh - 14) + 'Z', P.copper, 1.1);
      s += rune(24, -24 - hh - 4, 3.2, P.verd);
      s += corners(ctx, 24, -24, 14, hh);
      ctx.top(-24 - hh - 24);
    } else {
      s += slit(17, -14, 13) + slit(31, -14, 13);
      s += corners(ctx, 24, -24, 14, hh);
      ctx.top(-24 - hh - 14);
    }
    return s;
  }
  /** 矮人符文：中心 (x, y)，尺寸 r，颜色 c（直线刻痕，按尺寸组合） */
  function rune(x, y, r, c, k) {
    var R = [
      'M' + f(x) + ' ' + f(y - r) + 'V' + f(y + r) + 'M' + f(x) + ' ' + f(y - r * 0.4) + 'L' + f(x + r * 0.7) + ' ' + f(y - r) + 'M' + f(x) + ' ' + f(y) + 'L' + f(x - r * 0.7) + ' ' + f(y - r * 0.6),
      'M' + f(x - r * 0.6) + ' ' + f(y + r) + 'L' + f(x) + ' ' + f(y - r) + 'L' + f(x + r * 0.6) + ' ' + f(y + r) + 'M' + f(x - r * 0.35) + ' ' + f(y + r * 0.2) + 'H' + f(x + r * 0.35),
      'M' + f(x - r * 0.6) + ' ' + f(y - r) + 'V' + f(y + r) + 'M' + f(x + r * 0.6) + ' ' + f(y - r) + 'V' + f(y + r) + 'M' + f(x - r * 0.6) + ' ' + f(y - r * 0.6) + 'L' + f(x + r * 0.6) + ' ' + f(y + r * 0.6),
      'M' + f(x) + ' ' + f(y - r) + 'L' + f(x + r * 0.7) + ' ' + f(y) + 'L' + f(x) + ' ' + f(y + r) + 'L' + f(x - r * 0.7) + ' ' + f(y) + 'Z'
    ];
    var d = R[(k || 0) % R.length];
    return line(d, 1.7, 1, P.deep2) + line(d, 0.9, 1, c || P.verd2);
  }
  /** 矮堡塔（替代 wallnode）：八角厚塔，比墙高 26，铜铆箍带 + 符文 + 箭缝 + 一圈厚垛 + 铜顶小旗 */
  function tower(ctx) {
    var r = 19, base = K.octo(24, -24, r, 0.38), Ht = H + 26, s = '';
    s += K.shadowOf(base, 7, 4);
    s += K.prism(ctx, K.octo(24, -24, r + 2, 0.38), 0, 6, { face: P.deep, top: P.granite, sw: 1.6 });
    s += K.prism(ctx, base, 6, Ht - 6, { face: P.granite, top: P.walk, sw: 1.8, tex: function (x0, x1, h) {
      return stones(x0, x1, h, false) + rect(x0, -h * 0.62, x1 - x0, 4, P.copper2, 0) + line('M' + f(x0) + ' ' + f(-h * 0.62) + 'H' + f(x1) + 'M' + f(x0) + ' ' + f(-h * 0.62 + 4) + 'H' + f(x1), 0.8, 0.7);
    } });
    for (var x = 12; x <= 36; x += 6) s += C.ell(x, -5 - 6 - (Ht - 6) * 0.62 + 2, 0.8, 0.8, P.ember, 0.4);
    s += slit(24, -10, 15) + rune(14, -40, 3.4, P.verd2, 1) + rune(34, -40, 3.4, P.verd2, 2);
    // 塔顶一圈垛：后半圈矮、前半圈厚（按 y 排序）
    var ring = K.ring(24, -24, r - 3.5, r - 3.5, 8, Math.PI / 8).sort(function (a, b) { return a[1] - b[1]; });
    ring.forEach(function (p) {
      var fr2 = p[1] > -24, bx = [[p[0] - 4, p[1] - 2.5], [p[0] + 4, p[1] - 2.5], [p[0] + 4, p[1] + 2.5], [p[0] - 4, p[1] + 2.5]];
      s += merlon(ctx, bx, Ht, fr2 ? 10 : 7, fr2);
    });
    var ty = -24 - Ht;
    s += line('M24 ' + f(ty) + 'V' + f(ty - 30), 1.8) + path('M24 ' + f(ty - 30) + 'h14l-3 5l3 5h-14Z', P.red, 1.1) + rune(30, ty - 25, 2.4, P.ember, 3);
    ctx.top(ty - 32);
    return s;
  }

  /** 铜门：中心 cx、底 yb、宽 w、高 h（拱顶），两扇铜板 + 铁箍 + 铆钉 */
  function copperDoor(cx, yb, w, h) {
    var x0 = cx - w / 2, x1 = cx + w / 2, sp = yb - h + w / 2, s = '';
    var arch = function (a, b, y, e) { return 'M' + f(a) + ' ' + f(yb) + 'V' + f(y) + 'Q' + f(cx) + ' ' + f(y - e) + ' ' + f(b) + ' ' + f(y) + 'V' + f(yb) + 'Z'; };
    s += path(arch(x0 - 6, x1 + 6, sp, w * 0.75), P.granite3, 1.5) + path(arch(x0, x1, sp, w * 0.6), P.copper, 1.4);
    s += path('M' + f(cx) + ' ' + f(yb) + 'V' + f(sp - w * 0.3) + 'L' + f(x1) + ' ' + f(sp) + 'V' + f(yb) + 'Z', P.copper2, 0, 0.6);
    var bands = '', rv = '';
    [0.25, 0.55, 0.82].forEach(function (t) {
      var y = yb - (yb - sp) * t; bands += 'M' + f(x0) + ' ' + f(y) + 'H' + f(x1);
      for (var x = x0 + 2.5; x < x1 - 1; x += 4) rv += C.ell(x, y, 0.8, 0.8, P.ember, 0.3);
    });
    s += line(bands, 2.4, 1, P.iron) + rv + line('M' + f(cx) + ' ' + f(yb) + 'V' + f(sp - w * 0.3), 1.2);
    s += C.ell(cx - 2.5, yb - h * 0.45, 1.6, 1.6, P.iron, 0.8) + C.ell(cx + 2.5, yb - h * 0.45, 1.6, 1.6, P.iron, 0.8);
    return s;
  }
  /** 炮眼：石圈 + 黑洞 + 伸出的铁炮口 */
  function gunport(x, y, r) {
    return C.ell(x, y, r + 3, r + 2.4, P.granite3, 1.2) + C.ell(x, y, r, r * 0.85, P.hole, 1) +
      C.ell(x + 0.6, y + 0.6, r * 0.62, r * 0.55, P.iron, 1) + C.ell(x + 0.6, y + 0.6, r * 0.3, r * 0.26, P.soot || '#3e3a36', 0);
  }
  /** 嵌山石堡（fort，3×3）：后方岩坡吞没堡身两肩，前凸门楼开铜门，门楣符文，两侧炮眼 */
  function mountainFort(ctx) {
    var s = '';
    s += C.shadow('M30 -8L150 -8L150 -60L128 -100Z', 0.15);
    // 岩坡：亮左坡、暗右坡，几道裂隙
    s += path('M0 -18L4 -84L20 -132L44 -166L66 -190L90 -178L108 -160L124 -138L140 -96L144 -24Z', P.granite3, 1.8);
    s += path('M66 -190L90 -178L108 -160L124 -138L140 -96L144 -24L104 -60L84 -120Z', P.granite, 0);
    s += line('M66 -190L84 -120L104 -60M44 -166L52 -120M20 -132L30 -100M108 -160L100 -118M124 -138L118 -104', 0.9, 0.55);
    s += line('M66 -190L90 -178L108 -160L124 -138L140 -96L144 -24', 1.8);
    s += path('M58 -168l6 -6l6 4l-4 6ZM32 -140l5 -3l3 4l-5 2Z', P.moss || '#a7b48a', 0.8);
    // 堡身（嵌在岩坡里）
    var body = [[20, -98], [124, -98], [124, -14], [20, -14]];
    s += K.prism(ctx, body, 0, 54, { face: P.granite, top: P.walk, sw: 1.8, tex: function (x0, x1, h) { return stones(x0, x1, h); } });
    s += gunport(36, -48, 4.5) + gunport(108, -48, 4.5);
    // 前凸门楼
    var gh = [[48, -36], [96, -36], [96, -4], [48, -4]];
    s += K.prism(ctx, gh, 0, 66, { face: P.granite2, top: P.walk, sw: 1.8, tex: function (x0, x1, h) { return stones(x0, x1, h); } });
    s += copperDoor(72, -4, 22, 36);
    s += rect(56, -60, 32, 9, P.deep, 1.2);
    for (var i = 0; i < 4; i++) s += rune(61 + i * 7.5, -55.5, 3, P.verd2, i);
    s += gunport(56, -44, 3) + gunport(88, -44, 3);
    // 垛：堡身后沿矮、前沿厚；门楼前沿厚垛
    for (var x = 22; x < 122; x += 12) {
      s += merlon(ctx, [[x, -98], [x + 9, -98], [x + 9, -94], [x, -94]], 54, 6, false);
      if (x < 46 || x > 90) s += merlon(ctx, [[x, -18], [x + 9, -18], [x + 9, -14], [x, -14]], 54, 10, true);
    }
    for (x = 50; x < 94; x += 11) s += merlon(ctx, [[x, -8], [x + 8, -8], [x + 8, -4], [x, -4]], 66, 11, true);
    // 岩肩压住堡身两端（嵌山）
    s += path('M0 -18L2 -60L12 -104L24 -122L30 -96L26 -60L22 -30L14 -18Z', P.granite3, 1.6) + line('M8 -70l8 -20M14 -40l6 -18', 0.8, 0.5);
    s += path('M144 -24L142 -70L134 -110L124 -128L118 -100L122 -62L126 -30L134 -22Z', P.granite, 1.6) + line('M136 -60l-6 -24', 0.8, 0.5);
    // 门楼顶铜炉烟囱 + 小旗
    s += K.prism(ctx, K.octo(84, -26, 4, 0.3), 66, 12, { face: P.copper, top: P.copper2, sw: 1.2 });
    s += line('M60 -98V-128', 1.8) + path('M60 -128h16l-3 5l3 5h-16Z', P.red, 1.1) + rune(67, -123, 2.4, P.ember, 3);
    ctx.top(-192);
    return s;
  }

  var NODE_NOTES = { 1: '方墩：四角厚垛 + 两道箭缝', 2: '符文墩：铜帽界石 + 青绿符文 + 箭缝' };
  var EXTRA = [];
  function types() {
    return [
      { id: 'west-dwarf-walltower-01', race: 'dwarf', category: 'wall', kind: 'wall_tower_keep', facility: 'watchtower', fp: [1, 1], roof: 'none',
        tags: ['node_tower', 'replaces_wallnode', 'order_0.2'], sort: 0.2, note: '矮堡塔：八角厚塔，铜箍带、符文、箭缝、一圈厚垛，放在墙节点上替代 wallnode', draw: tower },
      { id: 'west-dwarf-mountainfort-01', race: 'dwarf', category: 'fort', kind: 'mountain_keep', facility: 'barracks', fp: [3, 3], roof: 'none',
        tags: ['embedded_rock', 'copper_gate', 'runes', 'gunports'], note: '嵌山石堡：半嵌入岩坡，前凸门楼开铜门，门楣符文，炮眼；按驻军堡填 barracks', draw: mountainFort }
    ].concat(EXTRA);
  }
  var API = { NODE_NOTES: NODE_NOTES, EXTRA: EXTRA, types: types, H: H, stones: stones, merlon: merlon, rune: rune, slit: slit, copperDoor: copperDoor, gunport: gunport, spoke: spoke, node: node, tower: tower, mountainFort: mountainFort };
  root.TownArtRF_dwarf = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
