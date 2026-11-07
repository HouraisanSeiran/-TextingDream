/*
 * 织梦 · east-ground · 摆件画笔（树冠、树干、缸、筐、箱体、湖石、车轮）
 *
 * 摆件局部坐标：x∈[0,48]，y=0 是锚点所在的地面线（格子前沿），向上为负；占地格是 y∈[-48,0]。
 * 3/4 俯视：地面上的圆压成扁椭圆（ry = r·0.42）；立面不压缩。投影一律藏青 0.2 平涂在右下。
 * 浏览器挂 window.TownArtEG_kit，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'));
  else root.TownArtEG_kit = factory(root.TownArtEG_core);
})(this, function (K) {
  'use strict';
  var C = K.C, f = K.f, mix = K.mix, G = C.gold, G2 = C.gold2, KF = 0.42;

  /** 地面投影：以 (cx, y) 为脚底，向右下偏。 */
  function shade(cx, y, rx) { return K.shadow(cx + rx * 0.22, y + 0.6, rx, Math.max(1.4, rx * 0.32)); }
  /** 直筒：底面中心 (cx, y)，半径 r，高 h。 */
  function cyl(cx, y, r, h, fill, top, lw) {
    var ry = r * KF;
    return K.path('M' + f(cx - r) + ' ' + f(y - h) + 'V' + f(y) + 'Q' + f(cx) + ' ' + f(y + ry * 2) + ' ' + f(cx + r) + ' ' + f(y) + 'V' + f(y - h) + 'Z', fill, G, lw || 0.8) +
      K.ell(cx, y - h, r, ry, top || fill, G, lw || 0.8);
  }
  /** 鼓腹缸：口径 rt、腹径 rb、高 h；inner 为口内颜色（水 / 暗色）。 */
  function jar(cx, y, rt, rb, h, fill, inner, band) {
    var s = shade(cx, y, rb * 1.1);
    s += K.path('M' + f(cx - rt) + ' ' + f(y - h) + 'C' + f(cx - rb * 1.25) + ' ' + f(y - h * 0.62) + ' ' + f(cx - rb * 0.95) + ' ' + f(y) + ' ' + f(cx - rb * 0.55) + ' ' + f(y) +
      'H' + f(cx + rb * 0.55) + 'C' + f(cx + rb * 0.95) + ' ' + f(y) + ' ' + f(cx + rb * 1.25) + ' ' + f(y - h * 0.62) + ' ' + f(cx + rt) + ' ' + f(y - h) + 'Z', fill, G, 0.8);
    s += K.path('M' + f(cx + rb * 0.25) + ' ' + f(y - h * 0.8) + 'Q' + f(cx + rb * 0.75) + ' ' + f(y - h * 0.5) + ' ' + f(cx + rb * 0.5) + ' ' + f(y - h * 0.08), null, mix(fill, C.navy, 0.35), 1.4, K.sop(0.5));
    if (band) s += K.line('M' + f(cx - rb * 1.02) + ' ' + f(y - h * 0.55) + 'Q' + f(cx) + ' ' + f(y - h * 0.4) + ' ' + f(cx + rb * 1.02) + ' ' + f(y - h * 0.55), band, 1.1);
    s += K.ell(cx, y - h, rt + 0.9, (rt + 0.9) * KF, mix(fill, C.creamL, 0.25), G, 0.8) + K.ell(cx, y - h + 0.2, rt - 0.4, (rt - 0.4) * KF, inner || C.umber);
    if (inner === C.water) s += K.line('M' + f(cx - rt * 0.5) + ' ' + f(y - h + 0.3) + 'q' + f(rt * 0.25) + ' -0.7 ' + f(rt * 0.5) + ' 0', C.creamL, 0.6, K.sop(0.8));
    return s;
  }
  /** 竹编筐：上口 rt、下底 rb、高 h；woven 横编线。 */
  function basket(cx, y, rt, rb, h, fill, load) {
    var s = shade(cx, y, rt), ry = rt * KF, d = 'M' + f(cx - rt) + ' ' + f(y - h) + 'L' + f(cx - rb) + ' ' + f(y) + 'Q' + f(cx) + ' ' + f(y + rb * KF * 2) + ' ' + f(cx + rb) + ' ' + f(y) + 'L' + f(cx + rt) + ' ' + f(y - h) + 'Z', w = '';
    s += K.path(d, fill, G, 0.8);
    for (var k = 1; k < 4; k++) { var yy = y - h * k / 4, rr = rb + (rt - rb) * k / 4; w += 'M' + f(cx - rr) + ' ' + f(yy) + 'Q' + f(cx) + ' ' + f(yy + rr * KF * 1.6) + ' ' + f(cx + rr) + ' ' + f(yy); }
    for (var j = -2; j <= 2; j++) w += 'M' + f(cx + j * rt * 0.36) + ' ' + f(y - h + ry * 0.8) + 'L' + f(cx + j * rb * 0.36) + ' ' + f(y + rb * KF * 0.8);
    s += K.line(w, C.umber, 0.55, K.sop(0.55));
    s += K.ell(cx, y - h, rt, ry, mix(fill, C.umber, 0.25), G, 0.8);
    if (load) s += load(cx, y - h, rt);
    return s;
  }
  /** 3/4 箱体：前脸 x0..x1、y-h..y，顶面向北深 dp。 */
  function box(x0, x1, y, h, dp, front, top, lw) {
    return K.rect(x0, y - h - dp, x1 - x0, dp, top || mix(front, C.creamL, 0.3), G, lw || 0.8) + K.rect(x0, y - h, x1 - x0, h, front, G, lw || 0.8);
  }
  /** 树干：从 (x, y) 向上 h，底宽 w，顶端偏 lean。 */
  function trunk(x, y, h, w, lean, col) {
    var tx = x + (lean || 0), ty = y - h;
    return K.path('M' + f(x - w / 2) + ' ' + f(y) + 'Q' + f(x - w * 0.35 + (lean || 0) * 0.3) + ' ' + f(y - h * 0.5) + ' ' + f(tx - w * 0.22) + ' ' + f(ty) +
      'L' + f(tx + w * 0.22) + ' ' + f(ty) + 'Q' + f(x + w * 0.3 + (lean || 0) * 0.3) + ' ' + f(y - h * 0.5) + ' ' + f(x + w / 2) + ' ' + f(y) + 'Z', col || C.umber, G, 0.8);
  }
  /** 树冠：若干重叠圆（金线外圈 + 本色 + 左上叠晕）。 */
  function canopy(cx, cy, R, r, col, lite, n, flat) {
    var a = [], i;
    n = n || 6;
    for (i = 0; i < n; i++) { var t = i / n * Math.PI * 2 + r() * 0.6, dd = R * (0.42 + r() * 0.22); a.push([cx + Math.cos(t) * dd, cy + Math.sin(t) * dd * (flat || 0.72), R * (0.42 + r() * 0.16)]); }
    a.push([cx, cy, R * 0.62]);
    var s = '';
    a.forEach(function (c) { s += K.circ(c[0], c[1], c[2] + 1, G); });
    a.forEach(function (c) { s += K.circ(c[0], c[1], c[2], col); });
    a.forEach(function (c) { if (c[1] <= cy + 0.5 && c[0] <= cx + R * 0.3) s += K.circ(c[0] - c[2] * 0.18, c[1] - c[2] * 0.22, c[2] * 0.55, lite); });
    return s;
  }
  /** 湖石：瘦漏透的竖石块，(cx, y) 脚底，宽 w 高 h，带几个孔洞。 */
  function rock(cx, y, w, h, r, holes) {
    var pts = [], n = 11, i;
    for (i = 0; i < n; i++) {
      var t = i / n, a = Math.PI + t * Math.PI * 2, ex = Math.cos(a), ey = Math.sin(a);
      var rx = w / 2 * (0.8 + r() * 0.35) * (ey < 0 ? 0.85 + 0.25 * Math.sin(t * 9) : 1);
      pts.push([cx + ex * rx, y - h / 2 + ey * h / 2 * (0.9 + r() * 0.15)]);
    }
    pts = pts.map(function (p) { return [p[0], Math.min(y, p[1])]; });
    var d = 'M' + K.pt(pts[0]);
    for (i = 0; i < n; i++) { var p = pts[i], q = pts[(i + 1) % n]; d += 'Q' + K.pt([p[0] + (q[0] - p[0]) * 0.5 + (r() - 0.5) * 3, p[1] + (q[1] - p[1]) * 0.5 + (r() - 0.5) * 3]) + ' ' + K.pt(q); }
    var s = shade(cx, y, w * 0.55) + K.path(d + 'Z', C.rock, G, 0.9);
    s += K.path('M' + f(cx + w * 0.08) + ' ' + f(y - h * 0.9) + 'Q' + f(cx + w * 0.42) + ' ' + f(y - h * 0.5) + ' ' + f(cx + w * 0.22) + ' ' + f(y - 1), null, C.rockD, 2.2, K.sop(0.45));
    s += K.path('M' + f(cx - w * 0.3) + ' ' + f(y - h * 0.75) + 'q' + f(w * 0.1) + ' ' + f(-h * 0.12) + ' ' + f(w * 0.3) + ' ' + f(-h * 0.1), null, C.rockL, 1.2, K.sop(0.8));
    for (i = 0; i < (holes || 0); i++) {
      var hx = cx + (r() - 0.55) * w * 0.5, hy = y - h * (0.3 + 0.45 * i / Math.max(1, holes - 1)) - r() * 2, hr = 1.3 + r() * 1.2;
      s += K.ell(hx, hy, hr, hr * 1.3, mix(C.gray, C.navy, 0.3), C.gold, 0.4);
    }
    return s;
  }
  /** 车轮：(cx, cy) 圆心，r 半径，侧视（略压扁成椭圆 ex）。 */
  function wheel(cx, cy, r, ex) {
    var s = K.ell(cx, cy, r * (ex || 1), r, C.wood, G, 0.9) + K.ell(cx, cy, r * (ex || 1) - 1.6, r - 1.6, 'none', C.umber, 0.8), d = '';
    for (var k = 0; k < 4; k++) { var a = k * Math.PI / 4; d += 'M' + f(cx - Math.cos(a) * r * (ex || 1) * 0.8) + ' ' + f(cy - Math.sin(a) * r * 0.8) + 'L' + f(cx + Math.cos(a) * r * (ex || 1) * 0.8) + ' ' + f(cy + Math.sin(a) * r * 0.8); }
    return s + K.line(d, C.umber, 0.8) + K.circ(cx, cy, 1.3, C.umber, G, 0.4);
  }
  /** 小叶片（竹叶、柳叶）：从 (x, y) 指向角度 a、长 L。 */
  function leaf(x, y, a, L, col, w) {
    var tx = x + Math.cos(a) * L, ty = y + Math.sin(a) * L, nx = -Math.sin(a) * (w || L * 0.22), ny = Math.cos(a) * (w || L * 0.22);
    return K.path('M' + f(x) + ' ' + f(y) + 'Q' + f((x + tx) / 2 + nx) + ' ' + f((y + ty) / 2 + ny) + ' ' + f(tx) + ' ' + f(ty) + 'Q' + f((x + tx) / 2 - nx * 0.4) + ' ' + f((y + ty) / 2 - ny * 0.4) + ' ' + f(x) + ' ' + f(y) + 'Z', col, G, 0.25);
  }

  return { KF: KF, G: G, G2: G2, shade: shade, cyl: cyl, jar: jar, basket: basket, box: box, trunk: trunk, canopy: canopy, rock: rock, wheel: wheel, leaf: leaf };
});
