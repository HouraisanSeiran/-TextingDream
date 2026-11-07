/*
 * 织梦 · 兽人族部件库（美术样板，尚未接入游戏）：骨饰、图腾、尖桩、战旗、篝火坑、绳结、兽皮纹理、圆顶帐等。
 * 局部坐标：y 向下；y = 0 为占地前沿。浏览器挂 window.TownArtWO_parts；Node 用 module.exports。依赖 core.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWO_core;
  var P = C.PAL, f = C.f;
  var HIDE_L = [P.hide, P.hide3, '#a8825a', '#b9946a'];   // 受光面兽皮
  var HIDE_D = ['#86643f', P.hide2, '#7c5a3a'];           // 背光面兽皮
  var ROPE = '#d6bd85';

  // ---------------- 纹理（在矩形内画，由调用方裁切） ----------------
  /** 拼缝兽皮：不规则拼块 + 缝线（短十字针脚） */
  function texHide(ctx, x, y, w, h, tones) {
    tones = tones || HIDE_L;
    var o = '', seams = '', st = '';
    var xs = [x - 2], ys = [y - 2];
    while (xs[xs.length - 1] < x + w) xs.push(xs[xs.length - 1] + ctx.rnd(9, 16));
    while (ys[ys.length - 1] < y + h) ys.push(ys[ys.length - 1] + ctx.rnd(7, 12));
    for (var r = 0; r < ys.length - 1; r++) {
      var off = r % 2 ? ctx.rnd(-5, 5) : 0;
      for (var c = 0; c < xs.length - 1; c++) {
        var a = xs[c] + off, b = xs[c + 1] + off, t = ys[r], u = ys[r + 1];
        o += C.path(C.wob(ctx, [[a, t], [b, t], [b, u], [a, u]], 0.8), ctx.pick(tones), 0);
        seams += 'M' + f(a) + ' ' + f(t) + 'L' + f(a + ctx.j(1)) + ' ' + f(u);
        for (var k = t + 2; k < u - 1; k += 3) st += 'M' + f(a - 1.2) + ' ' + f(k) + 'l2.4 1';
      }
      seams += 'M' + f(x - 2) + ' ' + f(ys[r + 1]) + 'H' + f(x + w + 2);
    }
    return o + C.line(seams, 0.8, 0.55) + C.line(st, 0.6, 0.45);
  }
  /** 茅草：一行行短竖线 + 行底毛边 */
  function texThatch(ctx, x, y, w, h, step) {
    step = step || 6;
    var d = '', hem = '';
    for (var yy = y + h; yy > y - step; yy -= step) {
      for (var xx = x + ctx.rnd(0, 3); xx < x + w; xx += ctx.rnd(2.2, 3.6)) d += 'M' + f(xx) + ' ' + f(yy) + 'l' + f(ctx.j(0.6)) + ' ' + f(-step * ctx.rnd(0.5, 0.85));
      hem += 'M' + f(x) + ' ' + f(yy) + 'H' + f(x + w);
    }
    return C.line(d, 0.7, 0.5) + C.line(hem, 0.9, 0.6);
  }
  /** 粗石垒墙：大小不一的不规则石块，偶尔长苔 */
  function texRubble(ctx, x, y, w, h, moss) {
    var o = '', fills = [P.stone, P.stone2, '#c7b897', P.stone3];
    for (var yy = y + h; yy > y - 8; ) {
      var rh = ctx.rnd(5.5, 9), xx = x - ctx.rnd(0, 7);
      while (xx < x + w) {
        var sw = ctx.rnd(7, 14), j = function () { return ctx.rnd(-1.2, 1.2); };
        var d = C.poly([[xx + 0.8 + j(), yy - 0.6], [xx + sw - 0.8 + j(), yy - 0.6 + j()], [xx + sw - 0.2, yy - rh * 0.55 + j()],
          [xx + sw - 1.4 + j(), yy - rh + 0.5], [xx + 1.2 + j(), yy - rh + 0.6 + j()], [xx + 0.2, yy - rh * 0.45]]);
        o += '<path d="' + d + '" fill="' + (moss && ctx.chance(0.14) ? P.moss2 : ctx.pick(fills)) + '"' + C.stroke(0.85, 0.65) + '/>';
        xx += sw;
      }
      yy -= rh;
    }
    return o;
  }
  /** 横放原木墙：每根圆木一条带 + 两端圆截面 */
  function texLogsH(ctx, x, y, w, h, dia) {
    dia = dia || 6;
    var o = '', d = '';
    for (var yy = y + h; yy > y; yy -= dia) {
      o += C.rect(x - 2, yy - dia, w + 4, dia, ctx.pick([P.wood, '#bf9a60', '#b48e58']), 0);
      d += 'M' + f(x - 2) + ' ' + f(yy) + 'H' + f(x + w + 2);
      var kx = x + ctx.rnd(4, w - 4);
      d += 'M' + f(kx) + ' ' + f(yy - dia * 0.5) + 'h' + f(ctx.rnd(3, 6));
    }
    return o + C.line(d, 0.9, 0.7);
  }

  // ---------------- 骨饰 ----------------
  /** 正面头骨（s=1 约宽 8 高 9），(x, y) 为颅顶中心偏下 */
  function skull(x, y, s) {
    s = s || 1;
    var d = 'M' + f(x - 4 * s) + ' ' + f(y + s) + 'C' + f(x - 4.2 * s) + ' ' + f(y - 4.6 * s) + ' ' + f(x + 4.2 * s) + ' ' + f(y - 4.6 * s) + ' ' + f(x + 4 * s) + ' ' + f(y + s) +
      'L' + f(x + 3 * s) + ' ' + f(y + 3.2 * s) + 'L' + f(x + 2.2 * s) + ' ' + f(y + 5.4 * s) + 'L' + f(x - 2.2 * s) + ' ' + f(y + 5.4 * s) + 'L' + f(x - 3 * s) + ' ' + f(y + 3.2 * s) + 'Z';
    return C.path(d, P.bone, 0.9) +
      C.ell(x - 1.6 * s, y + 1.3 * s, 1.15 * s, 1.25 * s, P.hole, 0) + C.ell(x + 1.6 * s, y + 1.3 * s, 1.15 * s, 1.25 * s, P.hole, 0) +
      C.path('M' + f(x) + ' ' + f(y + 2.6 * s) + 'l' + f(-0.6 * s) + ' ' + f(1.2 * s) + 'h' + f(1.2 * s) + 'Z', P.hole, 0) +
      C.line('M' + f(x - 1.4 * s) + ' ' + f(y + 4.6 * s) + 'v' + f(0.8 * s) + 'M' + f(x) + ' ' + f(y + 4.6 * s) + 'v' + f(0.8 * s) + 'M' + f(x + 1.4 * s) + ' ' + f(y + 4.6 * s) + 'v' + f(0.8 * s), 0.6, 0.7);
  }
  /** 一只角（新月形），dir = ±1 指向外侧，len 长度，up 上弯程度 */
  function horn(x, y, len, dir, up, fill) {
    up = up == null ? 1 : up;
    var tx = x + dir * len, ty = y - len * 0.7 * up;
    var d = 'M' + f(x) + ' ' + f(y - 1.6) + 'Q' + f(x + dir * len * 0.85) + ' ' + f(y - 1) + ' ' + f(tx) + ' ' + f(ty) +
      'Q' + f(x + dir * len * 0.7) + ' ' + f(y + 2.2) + ' ' + f(x) + ' ' + f(y + 1.8) + 'Z';
    return C.path(d, fill || P.bone2, 0.9) + C.line('M' + f(x + dir * len * 0.35) + ' ' + f(y - 1.2) + 'l' + f(dir * 0.6) + ' 2.4M' + f(x + dir * len * 0.6) + ' ' + f(y - 1.6 - len * 0.12 * up) + 'l' + f(dir * 0.8) + ' 2', 0.6, 0.6);
  }
  /** 长角兽头骨：头骨 + 一对长角 */
  function hornSkull(x, y, s, len) {
    s = s || 1; len = len || 9 * s;
    return horn(x - 3 * s, y - 0.5 * s, len, -1, 1) + horn(x + 3 * s, y - 0.5 * s, len, 1, 1) + skull(x, y, s);
  }
  /** 獠牙：从 (x, y) 起向 dir 侧上弯的长牙 */
  function tusk(x, y, len, dir) {
    var d = 'M' + f(x) + ' ' + f(y) + 'Q' + f(x + dir * len * 0.75) + ' ' + f(y + len * 0.12) + ' ' + f(x + dir * len) + ' ' + f(y - len * 0.6) +
      'Q' + f(x + dir * len * 0.5) + ' ' + f(y - len * 0.12) + ' ' + f(x) + ' ' + f(y - 2.6) + 'Z';
    return C.path(d, P.bone, 0.9);
  }
  /** 门楣上一对交叉獠牙（中心 cx，根部 y） */
  function tuskArch(cx, y, half) {
    return tusk(cx - half, y, half * 1.25, 1) + tusk(cx + half, y, half * 1.25, -1);
  }

  // ---------------- 木作 ----------------
  /** 尖头原木桩：(x, yb) 左下角，宽 w，桩身高 h（尖头再高 w*1.1） */
  function stake(x, yb, w, h, fill, sw) {
    var d = 'M' + f(x) + ' ' + f(yb) + 'V' + f(yb - h) + 'L' + f(x + w * 0.5) + ' ' + f(yb - h - w * 1.1) + 'L' + f(x + w) + ' ' + f(yb - h) + 'V' + f(yb) + 'Z';
    return C.path(d, fill || P.wood, sw == null ? 1 : sw) + C.line('M' + f(x + w * 0.62) + ' ' + f(yb - 2) + 'V' + f(yb - h * 0.7), 0.6, 0.45);
  }
  /** 绳结：在竖柱 (x, y) 处缠绕 n 圈，柱宽 w */
  function knot(x, y, w, n) {
    n = n || 3;
    var d = '';
    for (var i = 0; i < n; i++) d += 'M' + f(x - w / 2 - 0.3) + ' ' + f(y + i * 1.7) + 'l' + f(w + 0.6) + ' -1.3';
    return C.line(d, 1.7, 1) + C.line(d, 0.8, 1, ROPE);
  }
  /** 一段绳子（路径 d） */
  function rope(d) { return C.line(d, 1.6, 1) + C.line(d, 0.7, 1, ROPE); }
  /** 竖杆 */
  function pole(x, yb, h, w, fill) { return C.path(C.rectD(x - w / 2, yb - h, w, h), fill || P.timber, 0.9); }

  /** 图腾柱：底 (x, yb)，宽 w，高 h；自下而上叠刻面兽首，顶上一对展翼或长角 */
  function totem(ctx, x, yb, w, h, top) {
    var s = '', seg = Math.max(3, Math.round(h / 14)), sh = h / seg, cols = [P.wood, '#b48e58', P.hide3];
    s += C.shadowD(C.poly([[x + w / 2, yb], [x + w / 2 + 8, yb + 2], [x + w / 2 + 10, yb - 2], [x + w / 2 + 2, yb - 3]]));
    for (var i = 0; i < seg; i++) {
      var y1 = yb - i * sh, y0 = y1 - sh, xm = x + w / 2;
      s += C.path(C.rectD(x, y0, w, sh), ctx.pick(cols), 1.1);
      s += C.rect(x + w * 0.62, y0 + 0.6, w * 0.38 - 0.6, sh - 1.2, P.dark, 0, 0.22); // 右侧阴面
      // 刻面：眼、鼻、獠牙口
      var ey = y0 + sh * 0.32;
      s += C.path('M' + f(xm - w * 0.36) + ' ' + f(ey) + 'l' + f(w * 0.22) + ' ' + f(sh * 0.12) + 'l' + f(-w * 0.2) + ' ' + f(sh * 0.08) + 'Z', P.hole, 0) +
        C.path('M' + f(xm + w * 0.36) + ' ' + f(ey) + 'l' + f(-w * 0.22) + ' ' + f(sh * 0.12) + 'l' + f(w * 0.2) + ' ' + f(sh * 0.08) + 'Z', P.hole, 0);
      var my = y0 + sh * 0.72;
      s += C.path(C.rectD(xm - w * 0.3, my - sh * 0.1, w * 0.6, sh * 0.2), i % 2 ? P.rust : P.hole, 0.6);
      s += C.path('M' + f(xm - w * 0.22) + ' ' + f(my - sh * 0.1) + 'l1 ' + f(-sh * 0.16) + 'l1 ' + f(sh * 0.16) + 'ZM' + f(xm + w * 0.22 - 2) + ' ' + f(my - sh * 0.1) + 'l1 ' + f(-sh * 0.16) + 'l1 ' + f(sh * 0.16) + 'Z', P.bone, 0.4);
      if (i % 2 === 0) s += C.line('M' + f(x) + ' ' + f(y1 - 1.5) + 'H' + f(x + w), 1.4, 1, P.rust);
    }
    var ty = yb - h;
    if (top === 'wings') {
      s += C.path('M' + f(x + w / 2) + ' ' + f(ty + 3) + 'L' + f(x - w * 0.9) + ' ' + f(ty - 4) + 'l2 4l-3 1l3 3L' + f(x) + ' ' + f(ty + 5) + 'Z', P.wood, 1) +
        C.path('M' + f(x + w / 2) + ' ' + f(ty + 3) + 'L' + f(x + w * 1.9) + ' ' + f(ty - 4) + 'l-2 4l3 1l-3 3L' + f(x + w) + ' ' + f(ty + 5) + 'Z', '#b48e58', 1);
      ctx.top(ty - 6);
    } else if (top === 'skull') {
      s += hornSkull(x + w / 2, ty - 3, 0.8, w * 0.9); ctx.top(ty - 3 - w * 0.9);
    } else {
      s += C.path('M' + f(x - 1) + ' ' + f(ty) + 'L' + f(x + w / 2) + ' ' + f(ty - w * 0.8) + 'L' + f(x + w + 1) + ' ' + f(ty) + 'Z', P.timber, 1); ctx.top(ty - w);
    }
    return s;
  }
  /** 战旗：杆底 (x, yb)，杆高 h；竖幅兽皮旗，下缘燕尾，带锈红爪纹 */
  function banner(ctx, x, yb, h, color, dir) {
    dir = dir || 1;
    var bw = 9, bh = 15, ty = yb - h, s = '';
    s += C.line('M' + f(x) + ' ' + f(yb) + 'V' + f(ty), 1.6) + C.line('M' + f(x - 0.4) + ' ' + f(yb) + 'V' + f(ty), 0.8, 1, P.timber);
    s += C.line('M' + f(x - 3) + ' ' + f(ty + 2) + 'H' + f(x + dir * (bw + 2)), 1.4); // 横杆
    var x2 = x + dir * bw;
    s += C.path('M' + f(x) + ' ' + f(ty + 2) + 'H' + f(x2) + 'V' + f(ty + 2 + bh) + 'L' + f(x + dir * bw / 2) + ' ' + f(ty + bh - 2) + 'L' + f(x) + ' ' + f(ty + 2 + bh) + 'Z', color || P.rust, 1.1);
    var cx = x + dir * bw / 2;
    s += C.line('M' + f(cx - 2) + ' ' + f(ty + 6) + 'l0.8 5M' + f(cx) + ' ' + f(ty + 5.5) + 'v5.6M' + f(cx + 2) + ' ' + f(ty + 6) + 'l-0.8 5', 1, 1, P.bone);
    s += skull(x, ty - 1.5, 0.45);
    ctx.top(ty - 4);
    return s;
  }
  /** 篝火坑：中心 (cx, cy)，半径 r；石圈 + 柴堆 + 火焰（平涂，不发光） */
  function firepit(ctx, cx, cy, r, lit) {
    var s = C.ell(cx, cy, r, r * 0.55, P.hole, 1.1, 0.85), n = Math.max(7, Math.round(r * 1.1));
    for (var i = 0; i < n; i++) {
      var a = Math.PI * 2 * i / n, sx = cx + Math.cos(a) * r, sy = cy + Math.sin(a) * r * 0.55;
      s += C.ell(sx, sy - 0.8, 2.3, 1.7, ctx.pick([P.stone, P.stone2, P.stone3]), 0.8);
    }
    s += C.line('M' + f(cx - r * 0.6) + ' ' + f(cy + 1) + 'L' + f(cx + r * 0.5) + ' ' + f(cy - 2) + 'M' + f(cx + r * 0.6) + ' ' + f(cy + 1) + 'L' + f(cx - r * 0.5) + ' ' + f(cy - 2), 2.4, 1, P.dark);
    if (lit !== false) {
      var fh = r * 1.3;
      s += C.path('M' + f(cx - r * 0.45) + ' ' + f(cy) + 'Q' + f(cx - r * 0.5) + ' ' + f(cy - fh * 0.5) + ' ' + f(cx - r * 0.1) + ' ' + f(cy - fh) +
        'Q' + f(cx) + ' ' + f(cy - fh * 0.55) + ' ' + f(cx + r * 0.2) + ' ' + f(cy - fh * 0.8) + 'Q' + f(cx + r * 0.55) + ' ' + f(cy - fh * 0.4) + ' ' + f(cx + r * 0.45) + ' ' + f(cy) + 'Z', P.fire, 0.9);
      s += C.path('M' + f(cx - r * 0.2) + ' ' + f(cy) + 'Q' + f(cx - r * 0.2) + ' ' + f(cy - fh * 0.4) + ' ' + f(cx) + ' ' + f(cy - fh * 0.6) + 'Q' + f(cx + r * 0.25) + ' ' + f(cy - fh * 0.3) + ' ' + f(cx + r * 0.2) + ' ' + f(cy) + 'Z', P.fire2, 0);
      ctx.top(cy - fh);
    }
    return s;
  }
  /** 粗刀斧兵器：kind = axe | cleaver | spear | club；挂点 (x, y) 向下垂 */
  function weapon(kind, x, y, L) {
    L = L || 14;
    var s = C.line('M' + f(x) + ' ' + f(y) + 'V' + f(y + L), 1.8) + C.line('M' + f(x) + ' ' + f(y) + 'V' + f(y + L), 0.8, 1, P.wood);
    if (kind === 'axe') s += C.path('M' + f(x) + ' ' + f(y + 1) + 'Q' + f(x + 6) + ' ' + f(y - 1) + ' ' + f(x + 7) + ' ' + f(y + 3) + 'Q' + f(x + 7.5) + ' ' + f(y + 6.5) + ' ' + f(x + 5) + ' ' + f(y + 8) + 'Q' + f(x + 3) + ' ' + f(y + 5) + ' ' + f(x) + ' ' + f(y + 5.5) + 'Z', P.iron2, 0.9);
    else if (kind === 'cleaver') s += C.path(C.poly([[x - 0.8, y + 1], [x + 6.5, y], [x + 7.5, y + 9], [x - 0.8, y + 7]]), P.iron2, 0.9) + C.circ(x + 5, y + 2.4, 0.8, P.hole, 0);
    else if (kind === 'spear') s += C.path('M' + f(x) + ' ' + f(y - 6) + 'l2 5l-2 2l-2 -2Z', P.iron2, 0.8) + knot(x, y + 1, 2, 2);
    else s += C.path('M' + f(x - 2.2) + ' ' + f(y + L) + 'Q' + f(x - 3.4) + ' ' + f(y + L * 0.55) + ' ' + f(x) + ' ' + f(y + L * 0.4) + 'Q' + f(x + 3.4) + ' ' + f(y + L * 0.55) + ' ' + f(x + 2.2) + ' ' + f(y + L) + 'Z', P.timber, 0.9) +
      C.line('M' + f(x - 2) + ' ' + f(y + L * 0.7) + 'l-1.4 -0.6M' + f(x + 2.2) + ' ' + f(y + L * 0.8) + 'l1.4 -0.6', 1, 1, P.bone);
    return s;
  }
  /** 骨串：从 (x0,y0) 到 (x1,y1) 下垂的绳，挂 n 块小骨/牙 */
  function boneString(ctx, x0, y0, x1, y1, n) {
    var sag = 3 + Math.abs(x1 - x0) * 0.08, mx = (x0 + x1) / 2, my = (y0 + y1) / 2 + sag;
    var s = rope('M' + f(x0) + ' ' + f(y0) + 'Q' + f(mx) + ' ' + f(my + sag * 0.3) + ' ' + f(x1) + ' ' + f(y1));
    for (var i = 1; i <= n; i++) {
      var t = i / (n + 1), bx = (1 - t) * (1 - t) * x0 + 2 * t * (1 - t) * mx + t * t * x1, by = (1 - t) * (1 - t) * y0 + 2 * t * (1 - t) * (my + sag * 0.3) + t * t * y1;
      s += i % 3 === 0 ? skull(bx, by + 3, 0.38) : C.path('M' + f(bx - 0.9) + ' ' + f(by) + 'h1.8l-0.9 ' + f(ctx.rnd(3, 4.5)) + 'Z', P.bone, 0.6);
    }
    return s;
  }

  var API = { HIDE_L: HIDE_L, HIDE_D: HIDE_D, ROPE: ROPE, texHide: texHide, texThatch: texThatch, texRubble: texRubble, texLogsH: texLogsH,
    skull: skull, horn: horn, hornSkull: hornSkull, tusk: tusk, tuskArch: tuskArch, stake: stake, knot: knot, rope: rope, pole: pole,
    totem: totem, banner: banner, firepit: firepit, weapon: weapon, boneString: boneString };
  root.TownArtWO_parts = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
