/*
 * 织梦 · 东方文化地标（east-landmark）· 地标专用部件（美术素材，尚未接入游戏）
 * 斗拱带、带斗拱的殿堂（单檐 / 重檐）、汉白玉须弥座与栏杆、御路台阶、石狮、碑与碑亭、水池与荷花、
 * 祥云、青绿山石、松柏、多层楼阁。全部是原创程序化路径；画法与色板沿用 lm-core.js（= east-special/core.js）。
 * 浏览器挂 window.TownArtEastLandmarkExtra；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var K = (typeof module !== 'undefined' && module.exports) ? require('./lm-core.js') : root.TownArtEastLandmarkCore;
  var C = K.C, TILE = K.TILE, G = K.G, GL = K.GL, f = K.f, P = K.P, R = K.R, E = K.E, L = K.L;
  var SHF = ' fill-opacity="0.2"';
  // 汉白玉（米白 #fbf0d4 为面、青石浅色为阴面）；水色与 east-special 的井、荷花池一致
  var MARB = C.wallLt, MARB2 = C.stoneLt, WATER = '#4f8a9a';

  /** 斗拱带：额枋之上一排斗拱（青绿拱臂 + 赭黄斗），下压一道朱红平板枋。y0..y1 = 带的上下沿。 */
  function dougong(x0, x1, y0, y1, o) {
    o = o || {};
    var h = y1 - y0, sp = o.sp || 7, s = R(x0, y0, x1 - x0, h, o.bg || C.navy, G, 0.7), d = '';
    var n = Math.max(2, Math.round((x1 - x0) / sp)), st = (x1 - x0) / n;
    for (var i = 0; i <= n; i++) {
      var x = x0 + i * st, aw = Math.min(st * 0.42, 3.4);
      s += R(x - aw, y0 + h * 0.42, aw * 2, Math.max(1, h * 0.2), C.teal, null) +
        R(x - aw * 0.55, y0 + h * 0.18, aw * 1.1, Math.max(0.9, h * 0.18), C.tealLt, null) +
        R(x - 1.1, y0 + h * 0.66, 2.2, h * 0.34, C.ochre, null) + R(x - 0.8, y0, 1.6, h * 0.2, C.ochre, null);
      d += 'M' + f(x - aw) + ' ' + f(y0 + h * 0.62) + 'Q' + f(x) + ' ' + f(y0 + h * 0.3) + ' ' + f(x + aw) + ' ' + f(y0 + h * 0.62);
    }
    s += L(d, GL, 0.5, 0.9);
    return s + R(x0, y1 - 1.4, x1 - x0, 1.6, C.red, GL, 0.4);
  }

  /**
   * 带斗拱的殿堂。与 K.hall 同参数，额外 o.dg = 斗拱带高（默认 4.5）。
   * 单檐：立面 h → 斗拱带 → 屋顶；重檐：下层立面 h1 + 下斗拱 → 上层立面 h2 + 上斗拱 → 腰檐 → 上檐。
   * 返回 { svg, roof, top }（top = 上层墙顶屏幕 y）。
   */
  function grandHall(x0, x1, yb, yf, o) {
    o = o || {};
    var ro = o.roof || {}, dg = o.dg != null ? o.dg : 4.5, ov = ro.ov != null ? ro.ov : 5, s = '', r;
    if (!o.double) {
      var h = o.h || 28;
      s += K.facade(x0, x1, yf, h, o.fac || {});
      s += dougong(x0 + 0.5, x1 - 0.5, yf - h - dg - ov * 0.6, yf - h + 0.5, o.dgo);
      r = K.roof(x0, x1, yb, yf, h + dg, ro);
      return { svg: s + r.svg, roof: r, top: yf - h };
    }
    var h1 = o.h1 || 24, h2 = o.h2 || 16, ins = o.inset || 8, sk = o.skirt || 7, H1 = h1 + dg;
    var ub = yb + 3, uf = yf - 5, fac = o.fac || {};
    s += K.facade(x0, x1, yf, h1, fac);
    s += dougong(x0 + 0.5, x1 - 0.5, yf - h1 - dg - (ov + 1) * 0.6, yf - h1 + 0.5, o.dgo);
    var uo = o.upFac || { bays: fac.bays || 3, doors: [], win: 'lattice', sill: false, col: fac.col, beam: fac.beam };
    s += K.facade(x0 + ins, x1 - ins, uf - H1, h2 + 2, uo);
    var utop = uf - H1 - h2 - 2;
    s += dougong(x0 + ins + 0.5, x1 - ins - 0.5, utop - dg - ov * 0.6, utop + 0.5, o.dgo);
    s += K.roof(x0, x1, yf - 14 + 2 * sk, yf, H1, { type: 'hip', tile: ro.tile, ov: ov + 1, up: ro.up != null ? ro.up : 5, hr: sk, inset: ins + 2, noBack: true }).svg;
    r = K.roof(x0 + ins, x1 - ins, ub, uf, H1 + h2 + 2 + dg, ro);
    return { svg: s + r.svg, roof: r, top: utop };
  }

  /** 汉白玉栏杆：地栿 + 望柱（圆头）+ 寻杖 + 华板。y = 栏杆脚（台面前沿）。 */
  function marbleRail(x0, x1, y, h, o) {
    o = o || {};
    var sp = o.sp || 6, n = Math.max(1, Math.round((x1 - x0) / sp)), st = (x1 - x0) / n, s = '', d = '';
    s += R(x0, y - h * 0.62, x1 - x0, h * 0.5, MARB2, G, 0.5);
    for (var i = 0; i < n; i++) {
      var a = x0 + i * st + 1.3, b = a + st - 2.6;
      if (b - a > 1.6) d += 'M' + f(a) + ' ' + f(y - h * 0.38) + 'Q' + f((a + b) / 2) + ' ' + f(y - h * 0.62) + ' ' + f(b) + ' ' + f(y - h * 0.38);
    }
    s += L(d, C.stoneDk, 0.6, 0.8);
    s += R(x0, y - h * 0.82, x1 - x0, 1.3, MARB, G, 0.5) + R(x0, y - 1.6, x1 - x0, 1.6, MARB, G, 0.5);
    for (var j = 0; j <= n; j++) {
      var x = x0 + j * st;
      s += R(x - 0.9, y - h, 1.8, h, MARB, G, 0.5) + E(x, y - h - 0.8, 1.2, 1.2, MARB, G, 0.5);
    }
    return s;
  }
  /** 侧栏杆：台面左右两边纵向的一段，只露一排望柱头。 */
  function sideRail(x, y0, y1, h) {
    var s = L('M' + f(x) + ' ' + f(y0 - h * 0.8) + 'V' + f(y1 - h * 0.8), G, 2) + L('M' + f(x) + ' ' + f(y0 - h * 0.8) + 'V' + f(y1 - h * 0.8), MARB, 1.1), list = [];
    for (var y = y0; y <= y1 + 0.1; y += 6) s += E(x, y - h - 0.6, 1.2, 1.2, MARB, G, 0.5);
    return s;
  }
  /**
   * 须弥座台基（汉白玉）：顶面 + 正面三段线脚（上枭、束腰、下枭）+ 前沿栏杆。
   * x0..x1 × yb..yf 是台基地面范围，p = 台高。o.rail=false 不画栏杆；o.gap=[a,b] 栏杆在中间留口（接台阶）。
   */
  function terrace(x0, x1, yb, yf, p, o) {
    o = o || {};
    var s = R(x0, yb - p, x1 - x0, yf - yb, o.top || C.stoneLt, G, 1);
    s += K.pave(x0 + 2, yb - p + 2, x1 - 2, yf - p - 1, 14, o.top || C.stoneLt);
    s += R(x0, yf - p, x1 - x0, p, MARB, G, 1);
    if (p >= 6) {
      var t1 = yf - p + p * 0.22, t2 = yf - p * 0.3;
      s += R(x0 + 2, t1, x1 - x0 - 4, t2 - t1, MARB2, G, 0.6);
      var d = '';
      for (var x = x0 + 8; x < x1 - 4; x += 12) d += 'M' + f(x) + ' ' + f(t1 + 0.8) + 'V' + f(t2 - 0.8);
      s += L(d, C.stoneDk, 0.6, 0.6);
    }
    if (o.rail !== false) {
      var rh = o.railH || 5, y = yf - p;
      if (o.gap) s += marbleRail(x0 + 1, o.gap[0], y, rh) + marbleRail(o.gap[1], x1 - 1, y, rh);
      else s += marbleRail(x0 + 1, x1 - 1, y, rh);
      s += sideRail(x0 + 1.5, yb - p + 3, yf - p, rh) + sideRail(x1 - 1.5, yb - p + 3, yf - p, rh);
    }
    return s;
  }
  /**
   * 一跑台阶：从台面前沿 yTop 下到地面 yBot，宽 w；o.yulu = 中间一道御路浮雕石（皇家、大殿用）；
   * 两侧垂带石（o.rail 时带汉白玉栏杆）。
   */
  function stair(cx, yTop, yBot, w, o) {
    o = o || {};
    var n = o.n || Math.max(3, Math.round((yBot - yTop) / 2.6)), sh = (yBot - yTop) / n, s = '';
    for (var i = 0; i < n; i++) s += R(cx - w / 2, yTop + i * sh, w, sh + 0.15, i % 2 ? C.stone : C.stoneLt, null);
    var d = '';
    for (var j = 1; j < n; j++) d += 'M' + f(cx - w / 2) + ' ' + f(yTop + j * sh) + 'H' + f(cx + w / 2);
    s += L(d, C.stoneDk, 0.5, 0.7);
    if (o.yulu) {
      var yw = w * 0.3;
      s += R(cx - yw / 2, yTop, yw, yBot - yTop, MARB, G, 0.6);
      var c = '';
      for (var k = 0; k < 3; k++) { var yy = yTop + (yBot - yTop) * (0.22 + k * 0.28); c += 'M' + f(cx - yw * 0.3) + ' ' + f(yy) + 'q' + f(yw * 0.3) + ' -3 ' + f(yw * 0.6) + ' 0'; }
      s += L(c, G, 0.7, 0.9);
    }
    var bw = o.cheek || 2.6;
    s += R(cx - w / 2 - bw, yTop, bw, yBot - yTop, MARB, G, 0.6) + R(cx + w / 2, yTop, bw, yBot - yTop, MARB, G, 0.6);
    if (o.rail) {
      [cx - w / 2 - bw / 2, cx + w / 2 + bw / 2].forEach(function (x) {
        s += L('M' + f(x) + ' ' + f(yTop - 4) + 'L' + f(x) + ' ' + f(yBot - 3), G, 2) + L('M' + f(x) + ' ' + f(yTop - 4) + 'L' + f(x) + ' ' + f(yBot - 3), MARB, 1.1);
        for (var y = yTop; y <= yBot - 2; y += Math.max(4, (yBot - yTop) / 3)) s += E(x, y - 4.6, 1.2, 1.2, MARB, G, 0.5);
      });
    }
    return s;
  }

  /** 石狮：须弥座上蹲坐的狮子，卷鬣、前爪按绣球（dir=-1 朝右看、1 朝左看只影响鬣毛卷向）。(x, y) = 座底中点。 */
  function lion(x, y, s, dir) {
    s = s || 1; dir = dir || 1;
    var o = E(x + 3 * s, y + 0.4, 6 * s, 1.6 * s, K.SH, null, 0, SHF);
    o += R(x - 4.5 * s, y - 4 * s, 9 * s, 4 * s, C.stone, G, 0.6) + R(x - 5.2 * s, y - 5 * s, 10.4 * s, 1.4 * s, C.stoneLt, G, 0.5);
    var body = 'M' + f(x - 3.6 * s) + ' ' + f(y - 5 * s) + 'Q' + f(x - 4.2 * s) + ' ' + f(y - 10 * s) + ' ' + f(x - 2.6 * s) + ' ' + f(y - 13 * s) +
      'L' + f(x + 2.6 * s) + ' ' + f(y - 13 * s) + 'Q' + f(x + 4.2 * s) + ' ' + f(y - 10 * s) + ' ' + f(x + 3.6 * s) + ' ' + f(y - 5 * s) + 'Z';
    o += P(body, C.stoneLt, G, 0.7);
    o += L('M' + f(x - 1.2 * s) + ' ' + f(y - 5 * s) + 'V' + f(y - 9 * s) + 'M' + f(x + 1.2 * s) + ' ' + f(y - 5 * s) + 'V' + f(y - 9 * s), C.stoneDk, 0.6 * s);
    o += E(x, y - 15 * s, 3.4 * s, 3 * s, C.stone, G, 0.7);
    var m = '';
    for (var i = 0; i < 5; i++) { var a = Math.PI * (0.9 + i * 0.3); m += 'M' + f(x + Math.cos(a) * 2.6 * s) + ' ' + f(y - 15 * s + Math.sin(a) * 2.4 * s) + 'q' + f(dir * 0.8 * s) + ' ' + f(-0.6 * s) + ' ' + f(dir * 0.4 * s) + ' ' + f(0.8 * s); }
    o += L(m, C.stoneDk, 0.6, 0.9);
    o += E(x, y - 14.2 * s, 1.6 * s, 1.2 * s, C.stoneLt, G, 0.4) + K.dots([[x - 1.1 * s, y - 15.8 * s], [x + 1.1 * s, y - 15.8 * s]], C.dark, 0.9);
    o += E(x - dir * 2.8 * s, y - 6.4 * s, 1.5 * s, 1.5 * s, C.ochre, G, 0.5);
    return o;
  }
  /** 石碑：赑屃（驮碑龟）底座 + 碑身 + 螭首碑额。(x, y) = 底座前沿中点。 */
  function stele(x, y, s, o) {
    s = s || 1; o = o || {};
    var r = E(x + 3 * s, y + 0.3, 7 * s, 1.6 * s, K.SH, null, 0, SHF);
    if (o.turtle !== false) {
      r += P('M' + f(x - 6 * s) + ' ' + f(y) + 'Q' + f(x - 6.5 * s) + ' ' + f(y - 5 * s) + ' ' + f(x) + ' ' + f(y - 5.5 * s) + 'Q' + f(x + 6.5 * s) + ' ' + f(y - 5 * s) + ' ' + f(x + 6 * s) + ' ' + f(y) + 'Z', C.stoneDk, G, 0.6);
      r += E(x, y - 1.4 * s, 2 * s, 1.6 * s, C.stone, G, 0.5);
    } else r += R(x - 5 * s, y - 3.5 * s, 10 * s, 3.5 * s, C.stone, G, 0.6);
    var t = y - (o.turtle !== false ? 4.5 : 3.5) * s, h = (o.h || 20) * s, w = 6.4 * s;
    r += R(x - w / 2, t - h, w, h, o.col || C.stoneLt, G, 0.7) + R(x + w / 2 - 1.2 * s, t - h, 1.2 * s, h, C.stone);
    r += P('M' + f(x - w / 2 - 0.6 * s) + ' ' + f(t - h) + 'Q' + f(x - w / 2) + ' ' + f(t - h - 5 * s) + ' ' + f(x) + ' ' + f(t - h - 5.4 * s) + 'Q' + f(x + w / 2) + ' ' + f(t - h - 5 * s) + ' ' + f(x + w / 2 + 0.6 * s) + ' ' + f(t - h) + 'Z', C.stone, G, 0.6);
    var d = '';
    for (var c = 0; c < 2; c++) for (var k = 0; k < 4; k++) d += 'M' + f(x - 1.4 * s + c * 2.6 * s) + ' ' + f(t - h + 3 * s + k * h * 0.2) + 'v' + f(h * 0.12);
    return r + L(d, C.dark, 0.6, 0.6);
  }
  /** 碑亭：方台 + 四柱敞亭（重檐攒尖可选），亭中立碑。x0..x1 × yb..yf。 */
  function stelePavilion(x0, x1, yb, yf, o) {
    o = o || {};
    var cx = (x0 + x1) / 2, h = o.h || 20, s = K.platform(x0 - 2, x1 + 2, yb, yf + 2, 3);
    var inner = stele(cx, yf - 4, Math.min(1, (x1 - x0) / 26), { h: h * 0.62 });
    s += K.pavilion(x0, x1, yb - 3, yf - 3, h, { post: C.red, roof: { type: o.spire ? 'spire' : 'hip', tile: o.tile || TILE.gold, ov: 5, up: 7, hr: o.spire ? 13 : 9, ridge: 'chiwen', finial: 6, hipK: 0.5 } }, inner).svg;
    return s;
  }
  /** 一片水面：圆角矩形（或椭圆）水池，石岸 + 两道波纹 + 荷叶荷花。 */
  function pond(x0, y0, x1, y1, o) {
    o = o || {};
    var rr = K.rng(o.seed || 5), cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, rx = (x1 - x0) / 2, ry = (y1 - y0) / 2, s = '';
    if (o.ellipse) s += E(cx, cy, rx + 2, ry + 2, C.stone, G, 1) + E(cx, cy + 0.6, rx, ry, WATER, G, 0.6) + E(cx, cy + 1.6, rx - 2, ry - 2, '#30697f', null, 0, ' fill-opacity="0.35"');
    else s += R(x0 - 2, y0 - 2, x1 - x0 + 4, y1 - y0 + 4, C.stone, G, 1) + R(x0, y0 + 1, x1 - x0, y1 - y0 - 1, WATER, G, 0.6) + R(x0, y0 + 1, x1 - x0, 2, '#30697f');
    var d = '';
    for (var i = 0; i < Math.max(2, (x1 - x0) / 14); i++) {
      var wx = x0 + 4 + rr() * (x1 - x0 - 12), wy = y0 + 4 + rr() * (y1 - y0 - 7);
      d += 'M' + f(wx) + ' ' + f(wy) + 'q2 -1.4 4 0t4 0';
    }
    s += L(d, C.tealLt, 0.7, 0.85);
    var nl = o.lotus != null ? o.lotus : Math.round((x1 - x0) * (y1 - y0) / 260);
    for (var j = 0; j < nl; j++) {
      var lx = x0 + 3 + rr() * (x1 - x0 - 6), ly = y0 + 3 + rr() * (y1 - y0 - 5), lr = 2 + rr() * 1.4;
      s += E(lx, ly, lr, lr * 0.55, C.teal, GL, 0.4) + L('M' + f(lx) + ' ' + f(ly) + 'l' + f(lr * 0.8) + ' ' + f(-lr * 0.2), '#195853', 0.5);
      if (rr() < 0.4) s += E(lx + 0.6, ly - 1.6, 1.2, 1.4, '#f3a0a0', C.red, 0.4) + E(lx + 0.6, ly - 1.4, 0.5, 0.6, C.ochreLt);
    }
    return s;
  }
  /** 拱桥（放在池上）：半圆拱 + 桥面 + 两侧栏杆。cx 中心，y = 桥脚水面线，w 跨长。 */
  function archBridge(cx, y, w, o) {
    o = o || {};
    var hgt = o.h || w * 0.28, s = '';
    var deck = 'M' + f(cx - w / 2 - 3) + ' ' + f(y) + 'Q' + f(cx) + ' ' + f(y - hgt * 2) + ' ' + f(cx + w / 2 + 3) + ' ' + f(y) + 'Z';
    s += P(deck, MARB, G, 0.9);
    s += P('M' + f(cx - w * 0.28) + ' ' + f(y) + 'A' + f(w * 0.28) + ' ' + f(hgt * 0.9) + ' 0 0 1 ' + f(cx + w * 0.28) + ' ' + f(y) + 'Z', WATER, G, 0.6);
    var rail = 'M' + f(cx - w / 2 - 2) + ' ' + f(y - 3) + 'Q' + f(cx) + ' ' + f(y - hgt * 2 - 3.5) + ' ' + f(cx + w / 2 + 2) + ' ' + f(y - 3);
    s += L(rail, G, 2) + L(rail, MARB, 1.1);
    var d = '';
    for (var i = 0; i <= 6; i++) {
      var t = i / 6, bx = (1 - t) * (1 - t) * (cx - w / 2 - 2) + 2 * t * (1 - t) * cx + t * t * (cx + w / 2 + 2);
      var by = (1 - t) * (1 - t) * (y - 3) + 2 * t * (1 - t) * (y - hgt * 2 - 3.5) + t * t * (y - 3);
      d += 'M' + f(bx) + ' ' + f(by + 2.6) + 'V' + f(by - 0.6);
    }
    return s + L(d, G, 1.8) + L(d, MARB, 0.9);
  }
  /**
   * 祥云：一朵横向的如意云（几颗圆头 + 卷尾），金线勾边 + 叠晕；(cx, cy) 中心，w 宽。
   * o.col 云色（默认米白），o.flip 卷尾朝左。
   */
  function cloud(cx, cy, w, o) {
    o = o || {};
    var col = o.col || C.smokeLt, lite = o.lite || '#ffffff', k = o.flip ? -1 : 1, r = w / 6, s = '';
    var Cs = [[cx - w * 0.3, cy, r * 0.9], [cx - w * 0.1, cy - r * 0.6, r * 1.15], [cx + w * 0.12, cy - r * 0.35, r], [cx + w * 0.32, cy + r * 0.05, r * 0.75]];
    if (k < 0) Cs = Cs.map(function (c) { return [2 * cx - c[0], c[1], c[2]]; });
    function disc(pad, fill, dy) { return '<g fill="' + fill + '">' + Cs.map(function (c) { return '<circle cx="' + f(c[0]) + '" cy="' + f(c[1] + dy) + '" r="' + f(c[2] + pad) + '"/>'; }).join('') + '</g>'; }
    s += disc(1.1, G, 0) + R(cx - w * 0.38, cy, w * 0.76, r * 0.7, G) + disc(0, col, 0) + R(cx - w * 0.38 + 1, cy, w * 0.76 - 2, r * 0.7 - 1.1, col);
    s += disc(-r * 0.4, lite, -r * 0.18);
    var tx = cx + k * w * 0.42, ty = cy + r * 0.3;
    s += L('M' + f(tx - k * r * 0.4) + ' ' + f(ty) + 'q' + f(k * r * 0.9) + ' ' + f(-r * 0.2) + ' ' + f(k * r * 0.7) + ' ' + f(-r * 0.9) + 'q' + f(-k * r * 0.25) + ' ' + f(-r * 0.4) + ' ' + f(-k * r * 0.55) + ' ' + f(-r * 0.05), G, 1.1);
    var cl = '';
    Cs.slice(0, 3).forEach(function (c) { cl += 'M' + f(c[0] - c[2] * 0.45) + ' ' + f(c[1] + c[2] * 0.1) + 'a' + f(c[2] * 0.45) + ' ' + f(c[2] * 0.45) + ' 0 1 1 ' + f(c[2] * 0.6) + ' ' + f(c[2] * 0.3); });
    return '<g opacity="' + (o.op || 0.96) + '">' + s + L(cl, G, 0.7, 0.8) + '</g>';
  }
  /**
   * 青绿山石：一座立面山崖（多边形），顶部石青、下部赭褐，横向皴纹。poly 是屏幕坐标多边形（顺时针）。
   * o.top 山顶色，o.side 山体色。
   */
  function rock(poly, o) {
    o = o || {};
    var s = P(K.pts(poly), o.side || C.umberLt, G, 1.1);
    var ys = poly.map(function (p) { return p[1]; }), y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys), d = '', d2 = '';
    // 上半截压青绿（叠晕两层）
    var cut = y0 + (y1 - y0) * (o.k || 0.45), up = [];
    for (var yy = y0 + 2; yy < y1 - 1; yy += 3.2) {
      var a = K.scan(poly, yy); if (!a) continue;
      var w = a[1] - a[0]; if (w < 3) continue;
      var rr = K.rng(Math.round(yy * 13 + (o.seed || 1)));
      var sx = a[0] + w * (0.05 + rr() * 0.25), ex = a[1] - w * (0.05 + rr() * 0.25);
      if (yy < cut) up.push([yy, a]);
      if (ex - sx > 3) {
        var seg = 'M' + f(sx) + ' ' + f(yy) + 'q' + f((ex - sx) / 2) + ' ' + f(-1.2) + ' ' + f(ex - sx) + ' 0';
        if (yy < cut) d2 += seg; else d += seg;
      }
    }
    if (up.length > 1) {
      var lt = up.map(function (u) { return [u[1][0] + 0.8, u[0]]; }), rt = up.map(function (u) { return [u[1][1] - 0.8, u[0]]; }).reverse();
      s += P(K.pts(lt.concat(rt)), o.top || C.teal, null, 0);
      var lt2 = up.slice(0, Math.max(2, Math.floor(up.length * 0.6))).map(function (u) { return [u[1][0] + (u[1][1] - u[1][0]) * 0.18, u[0]]; });
      var rt2 = up.slice(0, lt2.length).map(function (u) { return [u[1][1] - (u[1][1] - u[1][0]) * 0.32, u[0]]; }).reverse();
      s += P(K.pts(lt2.concat(rt2)), o.topLt || C.tealLt, null, 0, ' fill-opacity="0.7"');
    }
    s += L(d, C.umber, 0.7, 0.7) + L(d2, '#195853', 0.7, 0.6);
    return s + P(K.pts(poly), null, G, 1.1);
  }
  /** 松：一棵层层平展的迎客松（三四层扁冠），(x, y) 树根，s 缩放，k 朝向。 */
  function pine(x, y, s, k) {
    s = s || 1; k = k || 1;
    var o = E(x + 4 * s, y + 0.4, 6 * s, 1.6 * s, K.SH, null, 0, SHF);
    var tr = 'M' + f(x) + ' ' + f(y) + 'Q' + f(x + k * 2 * s) + ' ' + f(y - 8 * s) + ' ' + f(x - k * 1 * s) + ' ' + f(y - 16 * s) + 'Q' + f(x - k * 3 * s) + ' ' + f(y - 20 * s) + ' ' + f(x + k * 1 * s) + ' ' + f(y - 24 * s);
    o += L(tr, G, 3.6 * s) + L(tr, C.umber, 2.2 * s);
    [[0, -24, 9, 2.6], [k * 4, -17, 8, 2.4], [-k * 5, -11, 7, 2.2], [k * 2, -29, 6, 2]].forEach(function (c) {
      var cx = x + c[0] * s, cy = y + c[1] * s, rx = c[2] * s, ry = c[3] * s;
      o += E(cx, cy, rx + 1, ry + 1, G) + E(cx, cy, rx, ry, '#21706b') + E(cx - rx * 0.15, cy - ry * 0.35, rx * 0.7, ry * 0.5, C.teal);
    });
    return o;
  }
  /** 柏：窄高的塔形柏树（文庙、祠堂、陵前常见），(x, y) 树根。 */
  function cypress(x, y, s) {
    s = s || 1;
    var o = E(x + 3 * s, y + 0.4, 5 * s, 1.4 * s, K.SH, null, 0, SHF) + R(x - 1.2 * s, y - 6 * s, 2.4 * s, 6 * s, C.umber, GL, 0.4);
    var body = 'M' + f(x) + ' ' + f(y - 30 * s) + 'Q' + f(x + 6.5 * s) + ' ' + f(y - 18 * s) + ' ' + f(x + 5 * s) + ' ' + f(y - 6 * s) + 'Q' + f(x) + ' ' + f(y - 3.5 * s) + ' ' + f(x - 5 * s) + ' ' + f(y - 6 * s) + 'Q' + f(x - 6.5 * s) + ' ' + f(y - 18 * s) + ' ' + f(x) + ' ' + f(y - 30 * s) + 'Z';
    o += P(body, '#21706b', G, 0.9);
    o += P('M' + f(x - 0.5 * s) + ' ' + f(y - 27 * s) + 'Q' + f(x - 4.5 * s) + ' ' + f(y - 18 * s) + ' ' + f(x - 3 * s) + ' ' + f(y - 8 * s) + 'Q' + f(x - 1 * s) + ' ' + f(y - 16 * s) + ' ' + f(x - 0.5 * s) + ' ' + f(y - 27 * s) + 'Z', C.teal);
    var d = '';
    for (var i = 0; i < 4; i++) d += 'M' + f(x - 3 * s) + ' ' + f(y - 9 * s - i * 5 * s) + 'q' + f(3 * s) + ' ' + f(1.4 * s) + ' ' + f(6 * s) + ' 0';
    return o + L(d, '#195853', 0.6, 0.7);
  }
  /** 平座回廊：楼阁层与层之间一圈挑出的平台 + 栏杆。x0..x1 宽，y = 平台面前沿，dep 平台露出的顶面深。 */
  function balcony(x0, x1, y, dep, o) {
    o = o || {};
    var s = R(x0, y - dep, x1 - x0, dep, C.umberLt, G, 0.7) + R(x0, y, x1 - x0, 2.2, C.red, GL, 0.5);
    s += dougong(x0 + 1, x1 - 1, y + 2.2, y + 5.4, { sp: 6 });
    s += K.railing(x0 + 0.5, x1 - 0.5, y, o.rh || 3.4, o.col || C.red);
    return s;
  }
  /**
   * 多层楼阁（名楼、藏经阁、楼阁式塔通用）。从地面层往上一层层叠：
   * levels = [{ w, h, bays, doors?, roof?: 'hip'|'spire'|'gable', tile?, balcony?: true, win? }...]，
   * 每层宽 w（以 cx 居中），墙高 h；每层上盖一圈腰檐，最后一层盖整顶。dep = 每层进深（屏幕 y 量）。
   * 返回 { svg, topY, roof }。
   */
  function tower(cx, yf, dep, levels, o) {
    o = o || {};
    var s = '', y = yf, last = null;
    levels.forEach(function (lv, i) {
      var w = lv.w, x0 = cx - w / 2, x1 = cx + w / 2, h = lv.h, top = y - h, isLast = i === levels.length - 1;
      if (lv.balcony && i > 0) { s += balcony(x0 - 3, x1 + 3, y, Math.min(5, dep * 0.25), { col: lv.railCol }); }
      // lv.oct：八角楼阁，两侧各露一面斜面（左受光、右背光），sw = 斜面宽
      var sw = lv.oct ? w * lv.oct : 0, pc = lv.col || C.red;
      if (sw) {
        s += P(K.pts([[x0, top + 2], [x0 + sw, top], [x0 + sw, y], [x0, y - 1.5]]), lv.wall || C.wall, G, 0.8) +
          P(K.pts([[x1 - sw, top], [x1, top + 2], [x1, y - 1.5], [x1 - sw, y]]), C.stone, G, 0.8);
        s += K.lattice(x0 + sw * 0.22, top + h * 0.3, sw * 0.56, Math.min(h * 0.42, 10), {}) + K.lattice(x1 - sw * 0.78, top + h * 0.3, sw * 0.56, Math.min(h * 0.42, 10), { bg: '#6a2e1a' });
        s += R(x0 - 0.6, top + 2, 2.2, h - 3.5, pc, GL, 0.5) + R(x1 - 1.6, top + 2, 2.2, h - 3.5, K.mix(pc, '#000000', 0.2), GL, 0.5);
      }
      s += K.facade(x0 + sw, x1 - sw, y, h, { bays: lv.bays || 3, doors: lv.doors || (i === 0 ? [Math.floor((lv.bays || 3) / 2)] : []), win: lv.win || 'lattice', sill: false, col: pc, beam: C.teal, wall: lv.wall });
      var dg = lv.dg != null ? lv.dg : 3.6, ov = lv.ov != null ? lv.ov : 6;
      if (dg > 0) s += dougong(x0 + 0.5, x1 - 0.5, top - dg - ov * 0.6, top + 0.5, { sp: 6 });
      var ro = isLast
        ? { type: lv.roof || 'hip', tile: lv.tile || o.tile || TILE.gold, ov: ov, up: lv.up || 9, hr: lv.hr || 14, ridge: 'chiwen', hipK: 0.5, finial: lv.finial, pearl: lv.pearl }
        : { type: 'hip', tile: lv.tile || o.tile || TILE.gold, ov: ov, up: lv.up || 8, hr: lv.hr || 5, inset: w / 2 - (lv.ridgeW || 8), ridge: 'plain', ridgeH: 1.5 };
      last = K.roof(x0, x1, y - dep, y, h + dg, ro);
      s += last.svg;
      if (lv.plaque) s += K.plaque(cx, top + h * 0.28, Math.min(w * 0.4, 24), 6.5, { chars: lv.plaque, bg: C.navy });
      y = top - dg - (lv.gap != null ? lv.gap : 2);
    });
    return { svg: s, topY: y, roof: last };
  }

  var API = {
    MARB: MARB, MARB2: MARB2, WATER: WATER,
    dougong: dougong, grandHall: grandHall, marbleRail: marbleRail, sideRail: sideRail, terrace: terrace, stair: stair,
    lion: lion, stele: stele, stelePavilion: stelePavilion, pond: pond, archBridge: archBridge, cloud: cloud,
    rock: rock, pine: pine, cypress: cypress, balcony: balcony, tower: tower
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.TownArtEastLandmarkExtra = API;
})(typeof window !== 'undefined' ? window : this);
