/*
 * 织梦 · 兽人族体块库（美术样板，尚未接入游戏）：圆顶帐、圆锥顶、圆筒墙、矩形立面、坡顶（脊沿 x / 山墙朝前）、门洞。
 * 局部坐标：y 向下；y = 0 为占地前沿。浏览器挂 window.TownArtWO_forms；Node 用 module.exports。依赖 core.js、parts.js。
 * 投影关系：地面进深与高度都按 1:1 直接向上叠（与 west-base 一致）。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWO_core;
  var K = isNode ? require('./parts.js') : root.TownArtWO_parts;
  var P = C.PAL, f = C.f;

  // 屋面材质：a 受光 / b 背光
  var MAT = {
    thatch: { a: P.thatch, b: P.thatch2, tex: function (ctx, x, y, w, h) { return K.texThatch(ctx, x, y, w, h, 6); } },
    hide: { a: P.hide, b: P.hide2, tex: function (ctx, x, y, w, h) { return K.texHide(ctx, x, y, w, h, K.HIDE_L); },
      texB: function (ctx, x, y, w, h) { return K.texHide(ctx, x, y, w, h, K.HIDE_D); } },
    hide2: { a: P.hide2, b: '#583e28', tex: function (ctx, x, y, w, h) { return K.texHide(ctx, x, y, w, h, [P.hide2, '#7c5a3a', '#86643f']); } },
    turf: { a: P.moss2, b: P.moss, tex: function (ctx, x, y, w, h) { return K.texThatch(ctx, x, y, w, h, 5); } },
    plank: { a: P.wood, b: P.timber, tex: function (ctx, x, y, w, h) { return K.texLogsH(ctx, x, y, w, h, 5); } }
  };
  function tex(ctx, m, back, x, y, w, h) { var M = MAT[m]; return back && M.texB ? M.texB(ctx, x, y, w, h) : M.tex(ctx, x, y, w, h); }

  /** 圆顶帐：底面椭圆中心 (cx, yc)，半径 rx/ry，高 h。opt.mat、opt.ribs 肋数、opt.bands 绳箍数、opt.smoke 顶孔 */
  function dome(ctx, cx, yc, rx, ry, h, opt) {
    opt = opt || {};
    var m = opt.mat || 'hide', M = MAT[m];
    var d = 'M' + f(cx - rx) + ' ' + f(yc) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + rx) + ' ' + f(yc) + 'A' + f(rx) + ' ' + f(h) + ' 0 0 0 ' + f(cx - rx) + ' ' + f(yc) + 'Z';
    var inner = tex(ctx, m, false, cx - rx, yc - h, rx * 2, h + ry);
    // 背光：右侧月牙
    var sh = [], e, a;
    for (e = 0; e <= 90; e += 10) sh.push(C.domePt(cx, yc, rx, ry, h, Math.PI / 2, e * Math.PI / 180));
    for (e = 90; e >= 0; e -= 10) sh.push(C.domePt(cx, yc, rx, ry, h, 0.62, e * Math.PI / 180));
    inner += C.path(C.pl(sh) + 'Z', P.hide2, 0, 0.42);
    var ribs = '', bands = '', nr = opt.ribs || 5, nb = opt.bands == null ? 2 : opt.bands;
    for (var i = 1; i < nr; i++) {
      a = -Math.PI / 2 + Math.PI * i / nr; var pts = [];
      for (e = 0; e <= 90; e += 10) pts.push(C.domePt(cx, yc, rx, ry, h, a, e * Math.PI / 180));
      ribs += C.pl(pts);
    }
    for (var b = 1; b <= nb; b++) {
      var eb = Math.PI / 2 * b / (nb + 1.3), pb = [];
      for (a = -90; a <= 90; a += 12) pb.push(C.domePt(cx, yc, rx, ry, h, a * Math.PI / 180, eb));
      bands += C.pl(pb);
    }
    inner += C.line(ribs, 1, 0.55) + K.rope(bands);
    var s = C.ellShadow(cx, yc, rx, ry) + C.path(d, M.a, 0) + C.clipped(ctx, d, inner) + C.path(d, 'none', 1.7);
    if (opt.smoke !== false) {
      var ty = yc - h;
      s += C.ell(cx, ty + 2.5, rx * 0.2, 2.2, P.hole, 1) + C.line('M' + f(cx - rx * 0.12) + ' ' + f(ty + 2) + 'l-2 -5M' + f(cx + rx * 0.12) + ' ' + f(ty + 2) + 'l2 -5M' + f(cx) + ' ' + f(ty + 1) + 'v-6', 1.6, 1, P.dark);
      ctx.top(ty - 6);
    }
    ctx.top(yc - h);
    return s;
  }
  /** 圆筒墙（粗石圆屋）：底面中心 (cx, yc)，rx/ry，墙高 h，mat = rubble | hide | logs */
  function cylinder(ctx, cx, yc, rx, ry, h, mat) {
    var t = yc - h;
    var d = 'M' + f(cx - rx) + ' ' + f(yc) + 'V' + f(t) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + rx) + ' ' + f(t) + 'V' + f(yc) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 1 ' + f(cx - rx) + ' ' + f(yc) + 'Z';
    var inner = mat === 'rubble' ? K.texRubble(ctx, cx - rx, t - ry, rx * 2, h + ry * 2, true) : mat === 'logs' ? vlogs(ctx, cx - rx, t - ry, rx * 2, h + ry * 2) : K.texHide(ctx, cx - rx, t, rx * 2, h + ry);
    inner += C.path(C.rectD(cx + rx * 0.45, t - ry, rx * 0.6, h + ry * 2), P.shadow, 0, 0.2);
    return C.ellShadow(cx, yc, rx, ry) + C.path(d, P.stone, 0) + C.clipped(ctx, d, inner) + C.path(d, 'none', 1.7);
  }
  /** 竖立原木排（栅墙、原木屋墙） */
  function vlogs(ctx, x, y, w, h) {
    var o = '', d = '';
    for (var xx = x; xx < x + w; ) {
      var lw = ctx.rnd(4.5, 6.5);
      o += C.rect(xx, y, lw, h, ctx.pick([P.wood, '#bf9a60', '#b48e58']), 0);
      d += 'M' + f(xx) + ' ' + f(y) + 'V' + f(y + h);
      d += 'M' + f(xx + lw * 0.6) + ' ' + f(y + h * ctx.rnd(0.2, 0.6)) + 'v' + f(ctx.rnd(3, 6));
      xx += lw;
    }
    return o + C.line(d, 0.85, 0.7);
  }
  /** 圆锥顶：檐口椭圆中心 (cx, ye)，半径 rx/ry，尖顶高出檐口 h（屏幕） */
  function cone(ctx, cx, ye, rx, ry, h, m, lean) {
    m = m || 'thatch'; lean = lean || 0;
    var M = MAT[m], ax = cx + lean, ay = ye - h;
    var d = 'M' + f(cx - rx) + ' ' + f(ye) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + rx) + ' ' + f(ye) + 'L' + f(ax) + ' ' + f(ay) + 'Z';
    var inner = tex(ctx, m, false, cx - rx, ay, rx * 2, h + ry);
    inner += C.path(C.poly([[ax, ay], [cx + rx * 0.25, ye + ry], [cx + rx + 2, ye + ry], [cx + rx + 2, ay]]), M.b, 0, 0.65);
    // 檐口毛边
    var hem = 'M' + f(cx - rx) + ' ' + f(ye), n = Math.round(rx / 2.5);
    for (var i = 1; i <= n; i++) {
      var a = Math.PI - Math.PI * i / n, x = cx + rx * Math.cos(a), y = ye + ry * Math.sin(a);
      hem += 'L' + f(x - (rx / n) * 0.5) + ' ' + f(y + 2.2) + 'L' + f(x) + ' ' + f(y);
    }
    ctx.top(ay);
    return C.path(d, M.a, 0) + C.clipped(ctx, d, inner) + C.line(hem, 0.9, 0.8) + C.path(d, 'none', 1.7);
  }
  /** 矩形立面：x0..x1，底 yb，高 h，mat = rubble | logs | vlogs | hide | plank */
  function facade(ctx, x0, x1, yb, h, mat) {
    var d = C.rectD(x0, yb - h, x1 - x0, h), w = x1 - x0, inner;
    if (mat === 'rubble') inner = K.texRubble(ctx, x0, yb - h, w, h, true);
    else if (mat === 'logs') inner = K.texLogsH(ctx, x0, yb - h, w, h, 6);
    else if (mat === 'vlogs') inner = vlogs(ctx, x0, yb - h, w, h);
    else if (mat === 'plank') inner = K.texLogsH(ctx, x0, yb - h, w, h, 4.5);
    else inner = K.texHide(ctx, x0, yb - h, w, h);
    inner += C.rect(x0, yb - h, w, 3, P.shadow, 0, 0.16); // 檐下阴影
    return C.face(ctx, d, P.stone, inner, 1.6);
  }
  /** 侧墙窄条（右侧背光，向上后退 dp）：x，底 yb，高 h */
  function sideStrip(ctx, x, yb, h, dp, wdt, mat) {
    var d = C.poly([[x, yb], [x + wdt, yb - dp], [x + wdt, yb - dp - h], [x, yb - h]]);
    return C.face(ctx, d, P.stone3, mat === 'hide' ? K.texHide(ctx, x, yb - dp - h, wdt, h + dp, K.HIDE_D) : C.rect(x, yb - dp - h, wdt, h + dp, P.shadow, 0, 0.22), 1.4);
  }
  /**
   * 坡顶，脊沿 x（长边朝前）：檐口 yE，x0..x1，进深 Dp（屏幕），脊高 R，ov 出檐，hip 两端收山比例 0..1，lean 歪斜。
   * 返回 { svg, yR }
   */
  function roofLong(ctx, o) {
    var M = MAT[o.mat || 'thatch'], ov = o.ov == null ? 3 : o.ov, hip = o.hip || 0, lean = o.lean || 0;
    var yE = o.yE, yR = yE - o.Dp / 2 - o.R, inset = (o.x1 - o.x0) * 0.5 * hip * 0.6;
    var a = [o.x0 - ov, yE + ov], b = [o.x1 + ov, yE + ov], c = [o.x1 - inset + lean, yR + ctx.j(1)], dd = [o.x0 + inset + lean, yR + ctx.j(1)];
    var d = C.poly([a, b, c, dd]), s = '';
    var inner = tex(ctx, o.mat || 'thatch', false, a[0], yR - 2, b[0] - a[0], yE - yR + ov + 4);
    // 右端收山面背光
    if (hip > 0) inner += C.path(C.poly([[o.x1 - inset * 0.2 + lean, yE + ov], [b[0], b[1]], c]), M.b, 0, 0.7);
    else inner += C.path(C.rectD(o.x1 - 7, yR - 2, 12, yE - yR + ov + 4), M.b, 0, 0.45);
    s += C.path(d, M.a, 0) + C.clipped(ctx, d, inner) + C.path(d, 'none', 1.7);
    // 脊上压一根原木
    s += C.line('M' + f(dd[0] - 1) + ' ' + f(dd[1]) + 'L' + f(c[0] + 1) + ' ' + f(c[1]), 3.4) + C.line('M' + f(dd[0] - 0.6) + ' ' + f(dd[1] - 0.3) + 'L' + f(c[0] + 0.6) + ' ' + f(c[1] - 0.3), 1.6, 1, P.wood);
    ctx.top(Math.min(c[1], dd[1]) - 2);
    return { svg: s, yR: Math.min(c[1], dd[1]), L: dd, Rt: c };
  }
  /**
   * 山墙朝前的坡顶（脊沿 y）：前山墙 x0..x1，檐 yE，脊高 R，进深 Dp，ov 出檐，wallMat 山墙面材质（null 表示屋面一直拖到前沿，A 字帐）。
   * 返回 { svg, apex: [x, y] }
   */
  function roofFront(ctx, o) {
    var M = MAT[o.mat || 'thatch'], ov = o.ov == null ? 3 : o.ov, xm = (o.x0 + o.x1) / 2 + (o.lean || 0);
    var yE = o.yE, ap = [xm, yE - o.R], bk = [xm, yE - o.R - o.Dp], s = '';
    var L = C.poly([[o.x0 - ov, yE + ov * 0.6], ap, bk, [o.x0 - ov, yE - o.Dp + ov * 0.6]]);
    var Rr = C.poly([[o.x1 + ov, yE + ov * 0.6], ap, bk, [o.x1 + ov, yE - o.Dp + ov * 0.6]]);
    var hb = yE - o.R - o.Dp - 2, hh = o.R + o.Dp + ov + 4;
    s += C.face(ctx, L, M.a, tex(ctx, o.mat || 'thatch', false, o.x0 - ov, hb, xm - o.x0 + ov, hh), 1.6);
    s += C.face(ctx, Rr, M.b, tex(ctx, o.mat || 'thatch', true, xm, hb, o.x1 - xm + ov, hh) + C.rect(xm, hb, o.x1 - xm + ov + 2, hh, P.shadow, 0, 0.18), 1.6);
    if (o.wallMat) {
      var g = C.poly([[o.x0, yE], ap, [o.x1, yE]]);
      s += C.face(ctx, g, P.stone, o.wallMat === 'vlogs' ? vlogs(ctx, o.x0, ap[1], o.x1 - o.x0, o.R) : K.texHide(ctx, o.x0, ap[1], o.x1 - o.x0, o.R), 1.4);
    }
    // 交叉脊杆（伸出山尖）
    s += C.line('M' + f(xm - 6) + ' ' + f(ap[1] - 6) + 'L' + f(xm + 2) + ' ' + f(ap[1] + 2) + 'M' + f(xm + 6) + ' ' + f(ap[1] - 6) + 'L' + f(xm - 2) + ' ' + f(ap[1] + 2), 2.4) +
      C.line('M' + f(xm - 6) + ' ' + f(ap[1] - 6) + 'L' + f(xm + 2) + ' ' + f(ap[1] + 2) + 'M' + f(xm + 6) + ' ' + f(ap[1] - 6) + 'L' + f(xm - 2) + ' ' + f(ap[1] + 2), 1, 1, P.wood);
    ctx.top(Math.min(bk[1], ap[1] - 6) - 1);
    return { svg: s, apex: ap, back: bk };
  }
  /** 门洞：底中心 (cx, yb)，宽 w 高 h；shape = rect | arch | tri；flap 兽皮门帘卷起；返回 svg */
  function door(ctx, cx, yb, w, h, shape, flap) {
    var x0 = cx - w / 2, x1 = cx + w / 2, d;
    if (shape === 'arch') d = 'M' + f(x0) + ' ' + f(yb) + 'V' + f(yb - h + w / 2) + 'A' + f(w / 2) + ' ' + f(w / 2) + ' 0 0 1 ' + f(x1) + ' ' + f(yb - h + w / 2) + 'V' + f(yb) + 'Z';
    else if (shape === 'tri') d = C.poly([[x0, yb], [cx, yb - h], [x1, yb]]);
    else d = C.poly([[x0, yb], [x0 + 0.6, yb - h], [x1 - 0.4, yb - h + 0.6], [x1, yb]]);
    var s = C.path(d, P.hole, 1.3);
    if (flap) {
      // 一侧门帘系起，斜挂在门框边
      var fx = shape === 'tri' ? cx : x1, fy = shape === 'tri' ? yb - h : yb - h;
      s += C.path(C.poly([[cx - 0.5, fy + (shape === 'tri' ? 0 : 0.5)], [fx, fy], [x1 + 1.2, yb - 0.5], [x1 - w * 0.28, yb - h * 0.42]]), P.hide2, 1) +
        K.knot(x1 - w * 0.18, yb - h * 0.45, 3, 2);
    }
    return s;
  }

  var API = { MAT: MAT, tex: tex, dome: dome, cylinder: cylinder, vlogs: vlogs, cone: cone, facade: facade, sideStrip: sideStrip,
    roofLong: roofLong, roofFront: roofFront, door: door };
  root.TownArtWO_forms = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
