/*
 * 织梦 · 东方城防工事（east-fort）共用画笔。美术素材，尚未接入游戏；全部是原创程序化路径。
 * 色板、投影、屋顶、门窗沿用 east-base/east-core.js（只读引用）；城墙的砖面 / 垛口 / 女墙 / 海墁函数
 * 按 east-base/tiles.js 原样重写（那边没导出），所以墙厚 36、墙高 WH=26、垛高 PH=6、垛墙厚 PW=3、
 * 砖缝（横 3.4 px、竖周期 8 错缝）、垛子（x 周期 8、宽 5）、海墁（6 × 12）与 east-base 城墙完全一致。
 * 斜向墙段用通用函数：平面边 a→b 投影成平行四边形立面，竖缝仍按世界 x 周期 8，跨格对得上。
 * 局部坐标同 east-core：原点 = 占地左前角，x 向右，g 向南（占地 g∈[-d*48,0]），z 向上，屏幕 y = g - z*K。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('../east-base/east-core.js'));
  else root.TownArtFort_core = factory(root.TownArtEast_core);
})(this, function (E) {
  'use strict';
  var C = E.C, T = E.TILE, f = E.f, K = E.K, mix = E.mix, sy = E.sy;
  var IN = 6, WH = 26, PH = 6, PW = 3, R2 = Math.SQRT1_2;
  var WC = {
    face: mix(C.grayL, C.cream, 0.32), faceD: mix(C.gray, C.grayL, 0.5), top: mix(C.stoneL, C.earthL, 0.35), base: C.stone,
    joint: mix(C.gray, C.navy, 0.2), par: mix(C.grayL, C.cream, 0.42)
  };

  function P(p, z) { return [p[0], p[1] - (z || 0) * K]; }
  function add(a, b, k) { k = k == null ? 1 : k; return [a[0] + b[0] * k, a[1] + b[1] * k]; }
  function lerp(a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]; }
  function seg(a, b, z) { return 'M' + E.pt(P(a, z)) + 'L' + E.pt(P(b, z)); }
  // 立面明暗按外法线：偏西迎光、偏东背光、正南原色
  function shadeOf(n, base) {
    base = base || WC.face;
    if (n[0] < -0.3) return mix(base, C.creamL, 0.22);
    if (n[0] > 0.3) return mix(base, WC.faceD, 0.4);
    return base;
  }

  /* ---------- 与 east-base/tiles.js 相同的正交墙体函数（g 即地面线） ---------- */
  function brickFace(ctx, x0, x1, yT, yB, fill) {
    var d = E.poly([[x0, yT], [x1, yT], [x1, yB], [x0, yB]]), j = '', row = 0, y;
    for (y = yB - 3.4; y > yT + 0.5; y -= 3.4) j += 'M' + f(x0) + ' ' + f(y) + 'H' + f(x1);
    for (y = yB; y > yT; y -= 3.4, row++) {
      var off = row % 2 ? 4 : 0, ya = Math.max(yT, y - 3.4);
      for (var x = Math.floor((x0 - off) / 8) * 8 + off; x < x1; x += 8) if (x > x0 + 0.3) j += 'M' + f(x) + ' ' + f(y) + 'V' + f(ya);
    }
    return E.path(d, fill || WC.face) + E.clip(ctx, d, E.line(j, WC.joint, 0.5, ' stroke-opacity="0.55"'));
  }
  function wallFace(ctx, x0, x1, yE, zTop, ends, fill) {
    var yT = yE - zTop * K, s = '';
    s += E.path(E.poly([[x0 + 3, yE], [x1 + 3, yE], [x1 + 3, yE + 3], [x0 + 2, yE + 3]]), C.shadow, null, 0, ' fill-opacity="0.2"');
    s += brickFace(ctx, x0, x1, yT, yE - 3 * K, fill);
    s += E.rect(x0, yE - 3 * K, x1 - x0, 3 * K, WC.base) + E.rect(x0, yT, x1 - x0, 1.6, WC.faceD);
    var d = 'M' + f(x0) + ' ' + f(yT) + 'H' + f(x1) + 'M' + f(x0) + ' ' + f(yE) + 'H' + f(x1) + 'M' + f(x0) + ' ' + f(yE - 3 * K) + 'H' + f(x1);
    if (ends && ends[0]) d += 'M' + f(x0) + ' ' + f(yT) + 'V' + f(yE);
    if (ends && ends[1]) d += 'M' + f(x1) + ' ' + f(yT) + 'V' + f(yE);
    return s + E.line(d, C.gold, 0.8);
  }
  function merlonsH(x0, x1, yF, depth, zb, zt, solid) {
    var s = '', zc = solid ? zt : zb + 2.4, tile = T.gray;
    s += E.rect(x0, yF - depth - zc * K, x1 - x0, depth, solid ? tile.fill : WC.par);
    s += E.rect(x0, yF - zc * K, x1 - x0, (zc - zb) * K, WC.face) + E.line('M' + f(x0) + ' ' + f(yF - zc * K) + 'H' + f(x1), solid ? tile.line : C.gold, 0.6);
    if (solid) return s + E.line('M' + f(x0) + ' ' + f(yF - depth - zc * K) + 'H' + f(x1), tile.lite, 0.6);
    for (var k = Math.floor(x0 / 8) - 1; k * 8 < x1; k++) {
      var xa = Math.max(x0, k * 8 + 1.5), xb = Math.min(x1, k * 8 + 6.5), w = xb - xa;
      if (w < 1) continue;
      s += E.rect(xa - 0.4, yF - depth - zt * K - 0.6, w + 0.8, depth + 0.6, tile.fill, tile.line, 0.4);
      s += E.rect(xa, yF - zt * K, w, (zt - zc) * K, WC.face, C.gold, 0.45);
      if (w > 4) s += E.rect(xa + w / 2 - 0.7, yF - (zc + (zt - zc) * 0.6) * K, 1.4, 1.4, C.navy);
    }
    return s;
  }
  // 沿 y 的垛口（南北向墙段东西两侧）：同 east-base
  function merlonsV(xa, y0, y1, zb, zt) {
    var s = '', zc = zb + 2.4, tile = T.gray;
    s += E.rect(xa, y0 - zc * K, PW, y1 - y0, WC.par) + E.line('M' + f(xa) + ' ' + f(y0 - zc * K) + 'V' + f(y1 - zc * K) + 'M' + f(xa + PW) + ' ' + f(y0 - zc * K) + 'V' + f(y1 - zc * K), C.gold, 0.4);
    for (var k = Math.floor(y0 / 8) - 1; k * 8 < y1; k++) {
      var ya = Math.max(y0, k * 8 + 1.5), yb = Math.min(y1, k * 8 + 6.5);
      if (yb - ya < 1) continue;
      s += E.rect(xa - 0.3, ya - zt * K, PW + 0.6, yb - ya, tile.fill, tile.line, 0.4);
      s += E.rect(xa, yb - zt * K, PW, (zt - zc) * K, WC.face, C.gold, 0.4);
    }
    return s;
  }
  // 墙顶海墁：横缝周期 6、竖缝周期 12 错缝（屏幕坐标，所有墙顶同高，所以跨格对得上）
  function walkTex(x0, x1, y0, y1) {
    var d = '', y;
    for (y = Math.ceil(y0 / 6) * 6; y < y1; y += 6) d += 'M' + f(x0) + ' ' + f(y) + 'H' + f(x1);
    for (y = Math.floor(y0 / 6) * 6; y < y1; y += 6) {
      var off = (Math.round(y / 6) % 2 + 2) % 2 ? 6 : 0;
      for (var x = Math.floor((x0 - off) / 12) * 12 + off; x < x1; x += 12) d += 'M' + f(x) + ' ' + f(Math.max(y0, y)) + 'V' + f(Math.min(y1, y + 6));
    }
    return E.line(d, WC.joint, 0.45, ' stroke-opacity="0.4"');
  }
  function polyZ(pts, z) { return E.poly(pts.map(function (p) { return P(p, z); })); }
  function topPoly(ctx, pts, z, fill) {
    z = z == null ? WH : z;
    var q = pts.map(function (p) { return P(p, z); }), d = E.poly(q);
    var xs = q.map(function (p) { return p[0]; }), ys = q.map(function (p) { return p[1]; });
    return E.path(d, fill || WC.top) + E.clip(ctx, d, walkTex(Math.min.apply(null, xs), Math.max.apply(null, xs), Math.min.apply(null, ys), Math.max.apply(null, ys)));
  }

  /* ---------- 斜向墙段：平面边 a→b（a.x < b.x）投成平行四边形立面 ---------- */
  function onEdge(a, b, x) { return lerp(a, b, (x - a[0]) / (b[0] - a[0])); }
  function quadZ(a, b, z0, z1) { return E.poly([P(a, z1), P(b, z1), P(b, z0), P(a, z0)]); }
  function vseg(p, z0, z1) { return 'M' + E.pt(P(p, z0)) + 'L' + E.pt(P(p, z1)); }
  function order(a, b) { return a[0] <= b[0] ? [a, b] : [b, a]; }
  // 斜立面：海墁同款砖缝——横缝按 z（底座 3 之上每 4 一皮，屏幕 3.4 px），竖缝按世界 x 周期 6 错缝
  function diagFace(ctx, a, b, zTop, fill, ends) {
    var o = order(a, b); a = o[0]; b = o[1];
    var s = E.path(E.poly([a, b, add(b, [3, 3]), add(a, [3, 3])]), C.shadow, null, 0, ' fill-opacity="0.2"');
    var d = quadZ(a, b, 3, zTop), j = '', r, z;
    s += E.path(d, fill || WC.face);
    for (r = 0, z = 3; z < zTop - 0.2; r++, z += 4) {
      var z2 = Math.min(zTop, z + 4);
      if (r) j += seg(a, b, z);
      for (var x = Math.floor(a[0] / 6) * 6 + (r % 2 ? 3 : 0) - 6; x < b[0]; x += 6) if (x > a[0] + 0.3) j += vseg(onEdge(a, b, x), z, z2);
    }
    s += E.clip(ctx, d, E.line(j, WC.joint, 0.5, ' stroke-opacity="0.55"'));
    s += E.path(quadZ(a, b, 0, 3), WC.base) + E.path(quadZ(a, b, zTop - 1.6 / K, zTop), WC.faceD);
    var l = seg(a, b, zTop) + seg(a, b, 0) + seg(a, b, 3);
    if (ends && ends[0]) l += vseg(a, 0, zTop);
    if (ends && ends[1]) l += vseg(b, 0, zTop);
    return s + E.line(l, C.gold, 0.8);
  }
  // 斜边上的垛墙：ni = 指向墙内的单位法线。crenel = 垛口（外边朝南、外脸可见），否则 = 女墙（外边朝北，看得到内脸）
  function diagPar(a, b, ni, crenel, fill) {
    var o = order(a, b); a = o[0]; b = o[1];
    var ai = add(a, ni, PW), bi = add(b, ni, PW), tile = T.gray, s = '';
    if (!crenel) {
      var zt = WH + 3.5;
      s += E.path(E.poly([P(a, zt), P(b, zt), P(bi, zt), P(ai, zt)]), tile.fill, tile.line, 0.5);
      return s + E.path(quadZ(ai, bi, WH, zt), WC.face) + E.line(seg(ai, bi, zt), tile.lite, 0.6);
    }
    var zc = WH + 2.4, zT = WH + PH;
    s += E.path(E.poly([P(a, zc), P(b, zc), P(bi, zc), P(ai, zc)]), WC.par);
    s += E.path(quadZ(a, b, WH, zc), fill || WC.face) + E.line(seg(a, b, zc), C.gold, 0.6);
    for (var k = Math.floor(a[0] / 6) - 1; k * 6 < b[0]; k++) {
      var xa = Math.max(a[0], k * 6 + 1), xb = Math.min(b[0], k * 6 + 5);
      if (xb - xa < 0.8) continue;
      var pa = onEdge(a, b, xa), pb = onEdge(a, b, xb), qa = add(pa, ni, PW), qb = add(pb, ni, PW);
      s += E.path(E.poly([P(pa, zT), P(pb, zT), P(qb, zT), P(qa, zT)]), tile.fill, tile.line, 0.4);
      s += E.path(quadZ(pa, pb, zc, zT), fill || WC.face, C.gold, 0.45);
      if (xb - xa > 3) { var m = P(lerp(pa, pb, 0.5), zc + (zT - zc) * 0.6); s += E.rect(m[0] - 0.6, m[1] - 0.6, 1.2, 1.2, C.navy); }
    }
    return s;
  }

  /* ---------- 通用块体：砖砌方墩（马面、墩台、城台），平面矩形 x0..x1 × gb..gf，顶高 zTop ---------- */
  function block(ctx, x0, x1, gb, gf, zTop, o) {
    o = o || {};
    var s = E.shadow(x0, x1, gb, gf, zTop, o.sx);
    s += topPoly(ctx, [[x0, gb], [x1, gb], [x1, gf], [x0, gf]], zTop, o.top);
    s += E.line(E.poly([P([x0, gf], zTop), P([x0, gb], zTop), P([x1, gb], zTop), P([x1, gf], zTop)], true), C.gold, 0.8);
    s += wallFace(ctx, x0, x1, gf, zTop, [true, true], o.face);
    return s;
  }
  // 一圈垛口（方台四沿）：北沿女墙 / 垛口、东西沿 merlonsV、南沿垛口
  function ringCrenels(x0, x1, gb, gf, z, o) {
    o = o || {};
    var s = '';
    s += o.northSolid === false ? merlonsH(x0, x1, gb + PW, PW, z, z + PH, false) : merlonsH(x0, x1, gb + PW, PW, z, z + 3.5, true);
    if (o.west !== false) s += merlonsV(x0, gb + PW, gf, z, z + PH);
    if (o.east !== false) s += merlonsV(x1 - PW, gb + PW, gf, z, z + PH);
    if (o.south !== false) s += merlonsH(x0, x1, gf, PW, z, z + PH, false);
    return s;
  }
  // 拱形门洞（石券 + 暗口）
  function archPath(x, yb, w, hh) {
    var r = w / 2;
    return 'M' + f(x) + ' ' + f(yb) + 'V' + f(yb - hh + r) + 'A' + f(r) + ' ' + f(r) + ' 0 0 1 ' + f(x + w) + ' ' + f(yb - hh + r) + 'V' + f(yb) + 'Z';
  }
  function gateArch(cx, g, w, hz) {
    var yb = g, hh = hz * K;
    return E.path(archPath(cx - w / 2 - 3, yb, w + 6, hh + 3), C.stone, C.gold, 0.9) + E.path(archPath(cx - w / 2, yb, w, hh), C.navy, C.gold, 1);
  }
  // 箭窗：竖长方小窗，深色洞口 + 金框
  function arrowWin(x, g, z, w, hz) {
    return E.rect(x, sy(g, z + hz), w, hz * K, C.navy, C.gold2, 0.45);
  }

  return {
    E: E, C: C, T: T, f: f, K: K, mix: mix, sy: sy, IN: IN, WH: WH, PH: PH, PW: PW, R2: R2, WC: WC,
    P: P, add: add, lerp: lerp, seg: seg, shadeOf: shadeOf,
    brickFace: brickFace, wallFace: wallFace, merlonsH: merlonsH, merlonsV: merlonsV, walkTex: walkTex,
    polyZ: polyZ, topPoly: topPoly, onEdge: onEdge, quadZ: quadZ, vseg: vseg, diagFace: diagFace, diagPar: diagPar,
    block: block, ringCrenels: ringCrenels, archPath: archPath, gateArch: gateArch, arrowWin: arrowWin
  };
});
