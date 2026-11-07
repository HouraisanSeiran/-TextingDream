/*
 * 织梦 · 城镇西式精灵族素材 —— 大形体：银白木墙、圆屋身、叶形屋顶（叶舟顶 / 叶尖山墙 / 花瓣穹顶 / 尖塔顶）、
 * 巨树主干与树冠、环形平台（美术样板，尚未接入游戏）
 * 局部坐标同 core.js（y = 0 为占地前沿，向上为负）。光从左上：左亮右暗。
 * 浏览器挂 window.TownArtWE_forms；Node 用 module.exports。依赖 core.js、parts.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWE_core;
  var Q = isNode ? require('./parts.js') : root.TownArtWE_parts;
  var P = C.P, f = C.f, line = C.line, path = C.path, rect = C.rect, face = C.face;

  // 屋面材质：a 受光 / b 背光 / tex 'vein' 叶脉 | 'petal' 花瓣瓦 | 'shingle' 木瓦
  var ROOFM = {
    leaf: { a: P.leaf, b: P.leaf2, tex: 'vein', op: 0.5 },
    moss: { a: P.moss, b: '#8f9c72', tex: 'petal', op: 0.5 },
    petal: { a: P.silver, b: P.silver3, tex: 'petal', op: 0.5 },
    silver: { a: P.silver2, b: P.silver3, tex: 'shingle', op: 0.45 },
    bark: { a: P.bark2, b: P.bark, tex: 'shingle', op: 0.5 }
  };
  var WALLF = { silver: P.silver, bark: P.bark2, stone: P.moon, moss: P.moss, plaster: P.plaster };

  // ---------------- 墙面 ----------------
  function wallTex(ctx, mat, x, y, w, h) {
    var d = '', k = '', i;
    if (mat === 'stone') { // 月光石砌：圆角块错缝
      for (var yy = y + h, r = 0; yy > y; yy -= 6, r++)
        for (var xx = x - (r % 2) * 5; xx < x + w; xx += 10) k += C.rect(xx + 0.5, yy - 5.6, 9, 5.2, r % 3 ? P.moon : P.moon2, 0.6, 1, 2);
      return k;
    }
    if (mat === 'bark') {
      for (var bx = x + 3; bx < x + w; bx += ctx.rnd(3.5, 5.5)) d += 'M' + f(bx) + ' ' + f(y + h) + 'q' + f(ctx.rnd(-1.5, 1.5)) + ' ' + f(-h / 2) + ' 0 ' + f(-h);
      return line(d, 0.7, 0.5);
    }
    if (mat === 'moss') {
      for (i = 0; i < w * h / 60; i++) d += 'M' + f(x + ctx.rnd(1, w - 3)) + ' ' + f(y + ctx.rnd(2, h - 1)) + 'q1 -1.6 2 0';
      return line(d, 0.7, 0.45);
    }
    if (mat === 'plaster') return '';
    // 银白木：竖板 + 少量木节
    for (var px = x + 4; px < x + w - 1; px += 4 + ctx.rnd(-0.4, 0.8)) d += 'M' + f(px) + ' ' + f(y) + 'V' + f(y + h);
    for (i = 0; i < Math.max(1, Math.round(w * h / 420)); i++) {
      var kx = x + ctx.rnd(2, w - 3), ky = y + ctx.rnd(3, h - 3);
      k += 'M' + f(kx) + ' ' + f(ky) + 'q1 -1.4 2 0q-1 1.4 -2 0';
    }
    return line(d, 0.7, 0.4) + line(k, 0.6, 0.5);
  }
  /** 立面：x0..x1，底 yb，高 h。o.mat、o.fill、o.sill 底部苔石勒脚 */
  function wall(ctx, x0, x1, yb, h, o) {
    o = o || {};
    var mat = o.mat || 'silver', d = C.rectD(x0, yb - h, x1 - x0, h);
    var tex = wallTex(ctx, mat, x0, yb - h, x1 - x0, h) + rect(x1 - 3.2, yb - h, 3.2, h, P.shadow, 0, 0.13) + rect(x0, yb - h, 2, h, P.paper, 0, 0.25);
    if (o.sill !== false) tex += rect(x0, yb - 4, x1 - x0, 4, P.stone2, 0) + line('M' + f(x0) + ' ' + f(yb - 4) + 'H' + f(x1), 0.8, 0.6);
    ctx.top(yb - h);
    return face(ctx, d, o.fill || WALLF[mat], tex, 1.6);
  }
  /** 圆屋身：中心 cx，前沿地面 yF，半径 r，高 H。返回 { svg, yt, yc, ry } */
  function cyl(ctx, cx, yF, r, H, o) {
    o = o || {};
    var ry = r * 0.55, yc = yF - ry, yt = yc - H, mat = o.mat || 'silver';
    var d = 'M' + f(cx - r) + ' ' + f(yt) + 'V' + f(yc) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + r) + ' ' + f(yc) + 'V' + f(yt) + 'Z';
    var t = '';
    if (mat === 'silver' || mat === 'bark') {
      for (var a = -1.35; a < 1.4; a += 0.32) {
        var x = cx + Math.sin(a) * r, yy = yc + Math.cos(a) * ry;
        t += 'M' + f(x) + ' ' + f(yt + (yy - yc)) + 'V' + f(yy);
      }
      t = line(t, 0.7, 0.4);
    } else t = wallTex(ctx, mat, cx - r, yt - ry, 2 * r, H + 2 * ry);
    t += path('M' + f(cx + r * 0.42) + ' ' + f(yt - ry) + 'H' + f(cx + r) + 'V' + f(yF) + 'H' + f(cx + r * 0.42) + 'Z', P.shadow, 0, 0.15);
    t += rect(cx - r, yt - ry, r * 0.22, H + 2 * ry, P.paper, 0, 0.22);
    if (o.sill !== false) t += path('M' + f(cx - r) + ' ' + f(yc - 4) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + r) + ' ' + f(yc - 4) +
      'V' + f(yc) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 1 ' + f(cx - r) + ' ' + f(yc) + 'Z', P.stone2, 0.7);
    ctx.top(yt - ry);
    return { svg: face(ctx, d, o.fill || WALLF[mat], t, 1.6), yt: yt, yc: yc, ry: ry };
  }

  // ---------------- 屋面纹理 ----------------
  /** 花瓣瓦一行：沿点列画向下鼓的小弧 */
  function scallopRow(pts, dip) {
    var d = 'M' + f(pts[0][0]) + ' ' + f(pts[0][1]);
    for (var i = 1; i < pts.length; i++) {
      var a = pts[i - 1], b = pts[i];
      d += 'Q' + f((a[0] + b[0]) / 2) + ' ' + f((a[1] + b[1]) / 2 + dip) + ' ' + f(b[0]) + ' ' + f(b[1]);
    }
    return d;
  }
  function qb(a, c, b, t) { var u = 1 - t; return [u * u * a[0] + 2 * u * t * c[0] + t * t * b[0], u * u * a[1] + 2 * u * t * c[1] + t * t * b[1]]; }
  function lerp(a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]; }
  /** 两条二次曲线（下沿 lo、上沿 hi，各为 [起, 控, 终]）之间的屋面纹理 */
  function bandTex(lo, hi, mat, rows, cols) {
    var m = ROOFM[mat], d = '', v = '', r, i;
    if (m.tex === 'petal' || m.tex === 'shingle') {
      for (r = 1; r < rows; r++) {
        var q = r / rows, pts = [];
        for (i = 0; i <= cols; i++) { var t = i / cols; pts.push(lerp(qb(lo[0], lo[1], lo[2], t), qb(hi[0], hi[1], hi[2], t), q)); }
        d += m.tex === 'petal' ? scallopRow(pts, 2.2) : C.smooth(pts);
        if (m.tex === 'shingle') for (i = (r % 2); i < cols; i += 2) {
          var p0 = lerp(qb(lo[0], lo[1], lo[2], (i + 0.5) / cols), qb(hi[0], hi[1], hi[2], (i + 0.5) / cols), q);
          v += 'M' + f(p0[0]) + ' ' + f(p0[1]) + 'l0 ' + f(-3.5);
        }
      }
    } else { // 叶脉：一条主脉（上沿），侧脉从主脉斜向下沿、朝两端张开
      for (i = 1; i < cols; i++) {
        var tt = i / cols, top = qb(hi[0], hi[1], hi[2], tt), bot = qb(lo[0], lo[1], lo[2], Math.max(0, Math.min(1, tt + (tt < 0.5 ? -0.07 : 0.07))));
        v += 'M' + f(top[0]) + ' ' + f(top[1]) + 'Q' + f((top[0] + bot[0]) / 2) + ' ' + f((top[1] + bot[1]) / 2 - 1.5) + ' ' + f(bot[0]) + ' ' + f(bot[1]);
      }
    }
    return line(d, 0.8, m.op) + line(v, 0.7, m.op);
  }

  /**
   * 叶舟顶（屋脊平行正面，两端收成上翘的叶尖）。o: x0 x1 墙宽；yE 前檐；D 进深像素；R 屋脊升高；mat；ov 出檐；curl 叶尖上翘。
   * 返回 { svg, yR, tipL, tipR }
   */
  function roofLeaf(ctx, o) {
    var m = ROOFM[o.mat || 'leaf'], ov = o.ov == null ? 4 : o.ov, curl = o.curl == null ? 6 : o.curl, s = '';
    var xc = (o.x0 + o.x1) / 2, yE = o.yE + 2, yR = o.yE - o.D / 2 - o.R, yB = o.yE - o.D;
    var tipY = yE - (yE - yR) * 0.32 - curl * 0.5;
    var TL = [o.x0 - ov - 4, tipY], TR = [o.x1 + ov + 4, tipY];
    var eC = [xc, 2 * (yE + 1) - tipY], rC = [xc, 2 * yR - tipY], bC = [xc, 2 * Math.min(yB, yR - 3) - tipY];
    s += rect(o.x0, o.yE + 1, o.x1 - o.x0, 4, P.shadow, 0, 0.24);
    var back = 'M' + f(TL[0]) + ' ' + f(TL[1]) + 'Q' + f(rC[0]) + ' ' + f(rC[1]) + ' ' + f(TR[0]) + ' ' + f(TR[1]) + 'Q' + f(bC[0]) + ' ' + f(bC[1]) + ' ' + f(TL[0]) + ' ' + f(TL[1]) + 'Z';
    s += face(ctx, back, m.b, C.hatch(TL[0], Math.min(yB, yR) - 6, TR[0] - TL[0], 10, 4, 0.3), 1.4);
    var fr = 'M' + f(TL[0]) + ' ' + f(TL[1]) + 'Q' + f(eC[0]) + ' ' + f(eC[1]) + ' ' + f(TR[0]) + ' ' + f(TR[1]) + 'Q' + f(rC[0]) + ' ' + f(rC[1]) + ' ' + f(TL[0]) + ' ' + f(TL[1]) + 'Z';
    var tex = bandTex([TL, eC, TR], [TL, rC, TR], o.mat || 'leaf', Math.max(3, Math.round((yE - yR) / 6)), Math.max(6, Math.round((TR[0] - TL[0]) / 7)));
    tex += path('M' + f(xc + (TR[0] - xc) * 0.45) + ' ' + f(yR - 10) + 'L' + f(TR[0] + 2) + ' ' + f(tipY - 6) + 'L' + f(TR[0] + 2) + ' ' + f(yE + 6) + 'L' + f(xc + (TR[0] - xc) * 0.3) + ' ' + f(yE + 6) + 'Z', P.shadow, 0, 0.12);
    s += face(ctx, fr, m.a, tex, 1.7);
    s += line('M' + f(TL[0]) + ' ' + f(TL[1]) + 'Q' + f(rC[0]) + ' ' + f(rC[1]) + ' ' + f(TR[0]) + ' ' + f(TR[1]), 2.2, 1) +
      line('M' + f(TL[0] + 3) + ' ' + f(TL[1] - 0.8) + 'Q' + f(rC[0]) + ' ' + f(rC[1] - 0.6) + ' ' + f(TR[0] - 3) + ' ' + f(TR[1] - 0.8), 0.9, 1, P.silver);
    ctx.top(Math.min(yR, yB, bC[1] / 2 + tipY / 2) - 6);
    return { svg: s, yR: yR, tipL: TL, tipR: TR };
  }

  /** 坡面纹理（正山墙两坡，瓦行竖直）：dir -1 左坡、+1 右坡 */
  function slopeTex(x0, x1, yTop, yBot, mat, dir) {
    var m = ROOFM[mat], d = '', p = '', k = 0;
    for (var x = x0 + 4.5; x < x1; x += 4.5, k++) {
      d += 'M' + f(x) + ' ' + f(yTop) + 'V' + f(yBot);
      for (var y = yTop + (k % 2) * 2.5; y < yBot; y += 5)
        p += m.tex === 'vein' ? 'M' + f(x) + ' ' + f(y) + 'l' + f(-dir * 3) + ' -2.6' : 'M' + f(x) + ' ' + f(y) + 'q' + f(-dir * 2.4) + ' 2.5 0 5';
    }
    return line(d, 0.8, m.op) + line(p, 0.7, m.op);
  }
  /**
   * 叶尖山墙（屋脊垂直正面、山墙朝街；两坡内凹，顶端收成上翘的叶尖）。o: x0 x1 yE D R mat ov gfill
   * 返回 { svg, apex }；山花面由调用方再画窗。
   */
  function roofGable(ctx, o) {
    var m = ROOFM[o.mat || 'leaf'], ov = o.ov == null ? 3 : o.ov, x0 = o.x0, x1 = o.x1, xc = (x0 + x1) / 2, yE = o.yE, R = o.R, D = o.D, s = '';
    var L = [x0 - ov, yE + 2], Rr = [x1 + ov, yE + 2], A = [xc, yE - R - 2];
    function cp(B) { return [B[0] + (A[0] - B[0]) * 0.62, B[1] - (B[1] - A[1]) * 0.3]; }
    function slope(B) {
      var c = cp(B);
      return 'M' + f(B[0]) + ' ' + f(B[1]) + 'Q' + f(c[0]) + ' ' + f(c[1]) + ' ' + f(A[0]) + ' ' + f(A[1]) +
        'L' + f(A[0]) + ' ' + f(A[1] - D) + 'Q' + f(c[0]) + ' ' + f(c[1] - D) + ' ' + f(B[0]) + ' ' + f(B[1] - D) + 'Z';
    }
    s += rect(x0, yE, x1 - x0, 3.5, P.shadow, 0, 0.22);
    s += face(ctx, slope(Rr), m.b, slopeTex(xc, Rr[0], A[1] - D, Rr[1], o.mat || 'leaf', 1) + C.hatch(xc, A[1] - D, Rr[0] - xc, Rr[1] - A[1] + D, 4, 0.35), 1.6);
    s += face(ctx, slope(L), m.a, slopeTex(L[0], xc, A[1] - D, L[1], o.mat || 'leaf', -1), 1.6);
    var cl = cp([x0, yE]), cr = cp([x1, yE]);
    var tri = 'M' + f(x0) + ' ' + f(yE) + 'Q' + f(cl[0]) + ' ' + f(cl[1]) + ' ' + f(xc) + ' ' + f(yE - R) + 'Q' + f(cr[0]) + ' ' + f(cr[1]) + ' ' + f(x1) + ' ' + f(yE) + 'Z';
    s += face(ctx, tri, o.gfill || P.silver, wallTex(ctx, 'silver', x0, yE - R, x1 - x0, R) + rect(xc + (x1 - xc) * 0.5, yE - R, x1 - xc, R, P.shadow, 0, 0.1), 1.3);
    var cL = cp(L), cR = cp(Rr);
    var bd = 'M' + f(L[0]) + ' ' + f(L[1]) + 'Q' + f(cL[0]) + ' ' + f(cL[1]) + ' ' + f(A[0]) + ' ' + f(A[1]) + 'Q' + f(cR[0]) + ' ' + f(cR[1]) + ' ' + f(Rr[0]) + ' ' + f(Rr[1]);
    s += line(bd, 4.2, 1) + line(bd, 2.2, 1, P.silver);
    s += line('M' + f(A[0]) + ' ' + f(A[1]) + 'V' + f(A[1] - D), 1.6);
    // 叶尖顶饰：一片向上微卷的叶
    s += line('M' + f(A[0]) + ' ' + f(A[1]) + 'q0.5 -5 3.5 -8', 1.4) + Q.leaf(A[0] + 3.5, A[1] - 8, 7, -Math.PI / 2 + 0.5, P.leaf, 0.8);
    ctx.top(A[1] - D - 2);
    ctx.top(A[1] - 15);
    return { svg: s, apex: A };
  }

  /**
   * 圆顶：cx 中心，yt 檐口（屋身顶椭圆中心），r 屋身半径，R 顶高。
   * o.shape 'dome' 花瓣穹顶（外鼓）| 'spire' 尖塔顶（内凹细尖）；o.mat；o.ov；o.finial false 不画顶饰
   */
  function cap(ctx, cx, yt, r, R, o) {
    o = o || {};
    var mat = o.mat || 'petal', m = ROOFM[mat], ov = o.ov == null ? 3 : o.ov, rr = r + ov, ry = rr * 0.55, T = [cx, yt - R], s = '', d, i;
    var spire = o.shape === 'spire';
    if (spire) d = 'M' + f(cx - rr) + ' ' + f(yt) + 'Q' + f(cx - rr * 0.16) + ' ' + f(yt - R * 0.28) + ' ' + f(T[0]) + ' ' + f(T[1]) +
      'Q' + f(cx + rr * 0.16) + ' ' + f(yt - R * 0.28) + ' ' + f(cx + rr) + ' ' + f(yt);
    else d = 'M' + f(cx - rr) + ' ' + f(yt) + 'C' + f(cx - rr * 1.06) + ' ' + f(yt - R * 0.62) + ' ' + f(cx - rr * 0.22) + ' ' + f(yt - R * 0.74) + ' ' + f(T[0]) + ' ' + f(T[1]) +
      'C' + f(cx + rr * 0.22) + ' ' + f(yt - R * 0.74) + ' ' + f(cx + rr * 1.06) + ' ' + f(yt - R * 0.62) + ' ' + f(cx + rr) + ' ' + f(yt);
    d += 'A' + f(rr) + ' ' + f(ry) + ' 0 0 1 ' + f(cx - rr) + ' ' + f(yt) + 'Z';
    s += path('M' + f(cx - r) + ' ' + f(yt) + 'A' + f(r) + ' ' + f(r * 0.55) + ' 0 0 0 ' + f(cx + r) + ' ' + f(yt) + 'v4A' + f(r) + ' ' + f(r * 0.55) + ' 0 0 1 ' + f(cx - r) + ' ' + f(yt + 4) + 'Z', P.shadow, 0, 0.24);
    var t = '';
    for (i = -3; i <= 3; i++) { // 花瓣肋
      var a = i * 0.42, px = cx + rr * Math.sin(a), py = yt + ry * Math.cos(a);
      t += 'M' + f(T[0]) + ' ' + f(T[1]) + 'Q' + f(cx + rr * Math.sin(a) * (spire ? 0.45 : 1.2)) + ' ' + f(yt - R * (spire ? 0.3 : 0.5)) + ' ' + f(px) + ' ' + f(py);
    }
    var rows = '';
    for (var q = 0.22; q < 0.8; q += 0.2) {
      var hw = spire ? rr * Math.pow(1 - q, 1.7) : rr * Math.sqrt(1 - q * q), yc = yt - R * q, pts = [];
      if (hw < 3) continue;
      for (var k = 0; k <= 8; k++) { var b = 0.12 + (Math.PI - 0.24) * k / 8; pts.push([cx + Math.cos(b) * hw, yc + Math.sin(b) * hw * 0.55]); }
      rows += scallopRow(pts, 1.8);
    }
    var sh = C.poly([[T[0], T[1]], [cx + rr + 3, yt - R * 0.45], [cx + rr + 3, yt + ry + 3], [cx + rr * 0.3, yt + ry + 3], [cx + rr * 0.12, yt - R * 0.4]]);
    s += face(ctx, d, m.a, path(sh, m.b, 0, 0.8) + line(t, 0.8, m.op + 0.1) + line(rows, 0.7, m.op), 1.6);
    // 檐口一圈花瓣垂边
    var hem = '', n = Math.max(6, Math.round(rr / 2.6));
    for (i = 0; i < n; i++) {
      var b0 = Math.PI * i / n, b1 = Math.PI * (i + 1) / n, bm = (b0 + b1) / 2;
      var p0 = [cx + Math.cos(b0) * rr, yt + Math.sin(b0) * ry], p1 = [cx + Math.cos(b1) * rr, yt + Math.sin(b1) * ry];
      hem += 'M' + f(p0[0]) + ' ' + f(p0[1]) + 'Q' + f(cx + Math.cos(bm) * rr * 1.04) + ' ' + f(yt + Math.sin(bm) * ry + 4.2) + ' ' + f(p1[0]) + ' ' + f(p1[1]) + 'Z';
    }
    s += path(hem, m.b, 1);
    if (o.finial !== false) {
      s += line('M' + f(T[0]) + ' ' + f(T[1] + 1) + 'V' + f(T[1] - 6), 2.4) + line('M' + f(T[0]) + ' ' + f(T[1] + 1) + 'V' + f(T[1] - 6), 1, 1, P.silver) +
        C.circle(T[0], T[1] - 7.5, 2.1, P.moon, 0.9) +
        C.circle(T[0] - 0.6, T[1] - 8.2, 0.6, P.silver, 0);
      ctx.top(T[1] - 10);
    } else ctx.top(T[1] - 1);
    return { svg: s, tip: T, ry: ry };
  }

  // ---------------- 巨树 ----------------
  /**
   * 树干：中心 cx，地面 yb，根部半宽 wb，顶部半宽 wt，高 h（树干顶 y = yb - h）。
   * o.roots 根须外展量；o.hollow 根下开洞 {w,h}（返回洞口位置供画门）。
   */
  function trunk(ctx, cx, yb, wb, wt, h, o) {
    o = o || {};
    var rt = o.roots == null ? 6 : o.roots, yt = yb - h, s = '';
    var Lb = [cx - wb - rt, yb], Rb = [cx + wb + rt, yb];
    var d = 'M' + f(Lb[0]) + ' ' + f(yb) + 'Q' + f(cx - wb) + ' ' + f(yb - 2) + ' ' + f(cx - wb) + ' ' + f(yb - 10) +
      'C' + f(cx - wb * 0.9) + ' ' + f(yb - h * 0.45) + ' ' + f(cx - wt * 1.05) + ' ' + f(yt + h * 0.3) + ' ' + f(cx - wt) + ' ' + f(yt) +
      'L' + f(cx + wt) + ' ' + f(yt) +
      'C' + f(cx + wt * 1.05) + ' ' + f(yt + h * 0.3) + ' ' + f(cx + wb * 0.9) + ' ' + f(yb - h * 0.45) + ' ' + f(cx + wb) + ' ' + f(yb - 10) +
      'Q' + f(cx + wb) + ' ' + f(yb - 2) + ' ' + f(Rb[0]) + ' ' + f(yb) + 'Z';
    // 树皮纹：竖向波纹 + 右侧阴面
    var t = '';
    for (var x = cx - wb + 2.5; x < cx + wb; x += ctx.rnd(3.2, 4.6)) {
      var u = (x - cx) / wb;
      t += 'M' + f(x + ctx.rnd(-1, 1)) + ' ' + f(yb - 1) + 'C' + f(x + ctx.rnd(-2, 2)) + ' ' + f(yb - h * 0.35) + ' ' + f(cx + u * wt + ctx.rnd(-2, 2)) + ' ' + f(yt + h * 0.4) + ' ' + f(cx + u * wt) + ' ' + f(yt);
    }
    var tex = line(t, 0.8, 0.5) + path('M' + f(cx + wb * 0.35) + ' ' + f(yb + 2) + 'L' + f(cx + wt * 0.35) + ' ' + f(yt - 2) + 'L' + f(cx + wb + rt + 2) + ' ' + f(yt - 2) + 'L' + f(cx + wb + rt + 2) + ' ' + f(yb + 2) + 'Z', P.shadow, 0, 0.2);
    tex += C.hatch(cx + wb * 0.55, yb - h * 0.6, wb * 0.5, h * 0.55, 3.4, 0.35);
    tex += path('M' + f(cx - wb + 1) + ' ' + f(yb) + 'L' + f(cx - wt + 1) + ' ' + f(yt) + 'L' + f(cx - wt * 0.6) + ' ' + f(yt) + 'L' + f(cx - wb * 0.6) + ' ' + f(yb) + 'Z', P.silver, 0, 0.12);
    // 节疤
    for (var k = 0; k < Math.max(1, Math.round(h / 40)); k++) {
      var ky = yb - h * ctx.rnd(0.3, 0.8), kx = cx + ctx.rnd(-0.5, 0.2) * wt;
      tex += C.ellipse(kx, ky, 2.2, 3.2, P.bark, 0.7, 1);
    }
    s += C.face(ctx, d, o.fill || P.bark2, tex, 1.8);
    // 根须：从根部向两侧爬出的几条
    var rs = '';
    [-1, 1].forEach(function (sd) {
      var bx = cx + sd * wb;
      rs += 'M' + f(bx) + ' ' + f(yb - 8) + 'Q' + f(bx + sd * rt * 0.6) + ' ' + f(yb - 3) + ' ' + f(bx + sd * (rt + 3)) + ' ' + f(yb - 0.5);
      rs += 'M' + f(cx + sd * wb * 0.45) + ' ' + f(yb - 4) + 'q' + f(sd * 2) + ' 3 ' + f(sd * 4.5) + ' 3.5';
    });
    s += line(rs, 2.6, 1) + line(rs, 1.2, 1, P.bark2);
    var hole = null;
    if (o.hollow) {
      var hw = o.hollow.w, hh = o.hollow.h;
      hole = { x: cx - hw / 2, yb: yb, w: hw, h: hh };
    }
    ctx.top(yt);
    return { svg: s, yt: yt, hole: hole };
  }
  /** 一根横伸的枝：从 (x,y) 伸向 (x2,y2)，根部粗 w */
  function branch(ctx, x, y, x2, y2, w) {
    var mx = (x + x2) / 2, my = Math.min(y, y2) - Math.abs(x2 - x) * 0.15;
    var d = 'M' + f(x) + ' ' + f(y - w / 2) + 'Q' + f(mx) + ' ' + f(my - w * 0.3) + ' ' + f(x2) + ' ' + f(y2) + 'Q' + f(mx) + ' ' + f(my + w * 0.6) + ' ' + f(x) + ' ' + f(y + w / 2) + 'Z';
    return path(d, P.bark2, 1.3);
  }
  /**
   * 树冠：几团叶簇（椭圆朵）叠成。中心 cx,cy，半轴 rx,ry。光从左上：左上叶团用浅色。
   * o.n 叶团数；o.light 浅色；o.dark 深色
   */
  function canopy(ctx, cx, cy, rx, ry, o) {
    o = o || {};
    var n = o.n || 7, s = '', lumps = [], i;
    for (i = 0; i < n; i++) {
      var a = Math.PI * 2 * i / n + ctx.rnd(-0.3, 0.3), q = ctx.rnd(0.45, 0.62);
      lumps.push([cx + Math.cos(a) * rx * q, cy + Math.sin(a) * ry * q, rx * ctx.rnd(0.42, 0.55), ry * ctx.rnd(0.45, 0.6)]);
    }
    lumps.sort(function (a, b) { return a[1] - b[1]; });
    // 底下一层深色托底
    s += C.ellipse(cx + 2, cy + ry * 0.1, rx * 0.92, ry * 0.8, o.dark || P.leaf2, 1.6);
    lumps.forEach(function (L) {
      var lit = (L[0] - cx) / rx + (L[1] - cy) / ry < -0.1;
      var fill = lit ? (o.light || P.moss) : (o.mid || P.leaf);
      var d = C.ellD(L[0], L[1], L[2], L[3]);
      var tex = '';
      for (var k = 0; k < 6; k++) {
        var lx = L[0] + ctx.rnd(-0.7, 0.7) * L[2], ly = L[1] + ctx.rnd(-0.6, 0.7) * L[3];
        tex += 'M' + f(lx - 2) + ' ' + f(ly) + 'q2 -2.6 4 0';
      }
      var sh = lit ? '' : path(C.ellD(L[0] + L[2] * 0.35, L[1] + L[3] * 0.3, L[2] * 0.75, L[3] * 0.7), P.leaf2, 0, 0.55);
      s += C.face(ctx, d, fill, sh + line(tex, 0.8, 0.5), 1.4);
    });
    // 树冠上挂几颗月光石珠
    if (o.gems) for (i = 0; i < o.gems; i++) {
      var gx = cx + ctx.rnd(-0.6, 0.6) * rx, gy = cy + ctx.rnd(0.1, 0.6) * ry;
      s += line('M' + f(gx) + ' ' + f(gy - 4) + 'v4', 0.6, 0.7) + C.circle(gx, gy + 1.4, 1.5, P.moon, 0.7);
    }
    ctx.top(cy - ry - 2);
    return s;
  }
  /**
   * 环形平台（绕树干或柱的椭圆木台）：中心 cx，台面中心 y，半轴 rx（ry = rx*0.5），台厚 th。
   * 返回 { back, deck, front }：back 后半栏杆（在树干后），deck 台面（在树干后），front 前半栏杆与台沿（在树干前）。
   */
  function ring(ctx, cx, y, rx, th, o) {
    o = o || {};
    var ry = rx * 0.5, deck = '', front = '', back = '';
    var top = C.ellD(cx, y, rx, ry);
    var rim = 'M' + f(cx - rx) + ' ' + f(y) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + rx) + ' ' + f(y) + 'V' + f(y + th) +
      'A' + f(rx) + ' ' + f(ry) + ' 0 0 1 ' + f(cx - rx) + ' ' + f(y + th) + 'Z';
    var planks = '';
    for (var k = 1; k < 9; k++) planks += 'M' + f(cx - rx + 2 * rx * k / 9) + ' ' + f(y - ry) + 'V' + f(y + ry);
    deck += C.face(ctx, top, P.silver2, line(planks, 0.7, 0.4) + path(C.ellD(cx + rx * 0.3, y + ry * 0.15, rx * 0.6, ry * 0.7), P.shadow, 0, 0.08), 1.4);
    // 托梁：台沿下几根斜撑
    var br = '';
    [-0.65, -0.2, 0.25, 0.7].forEach(function (u) {
      var bx = cx + u * rx, by = y + Math.sqrt(1 - u * u) * ry + th;
      if (by + 12 > (o.floor == null ? -1 : o.floor)) return; // 托梁不许伸出占地前沿
      br += 'M' + f(bx) + ' ' + f(by) + 'Q' + f(bx + (cx - bx) * 0.2) + ' ' + f(by + 6) + ' ' + f(cx + (bx - cx) * 0.25) + ' ' + f(by + 12);
    });
    front += line(br, 2.4, 1) + line(br, 1.1, 1, P.bark2);
    front += C.face(ctx, rim, P.silver3, line('M' + f(cx - rx) + ' ' + f(y + th / 2) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + rx) + ' ' + f(y + th / 2), 0.6, 0.45) +
      rect(cx + rx * 0.4, y, rx, ry + th + 2, P.shadow, 0, 0.16), 1.4);
    if (o.rail !== false) {
      var h = o.railH || 6;
      back += Q.railArc(ctx, cx, y, rx - 1.5, ry - 1, Math.PI + 0.05, 2 * Math.PI - 0.05, h, { leafP: 0.3 });
      front += Q.railArc(ctx, cx, y, rx - 1.5, ry - 1, 0.05, Math.PI - 0.05, h, { leafP: 0.4 });
    }
    ctx.top(y - ry - (o.railH || 6));
    return { back: back, deck: deck, front: front, ry: ry };
  }

  var API = {
    ROOFM: ROOFM, WALLF: WALLF, wallTex: wallTex, wall: wall, cyl: cyl, bandTex: bandTex, roofLeaf: roofLeaf,
    roofGable: roofGable, cap: cap, scallopRow: scallopRow, trunk: trunk, branch: branch, canopy: canopy, ring: ring
  };
  root.TownArtWE_forms = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
