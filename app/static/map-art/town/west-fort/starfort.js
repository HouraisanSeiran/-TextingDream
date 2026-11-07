/*
 * 织梦 · 西式防御工事 —— 整体小星堡地标 starfort-01（6×6，category = landmark）
 * 方形主体 + 四角尖棱堡（尖角朝 ne / se / sw / nw），实心土石台面高 40；外绕一圈护城河（地面层，水色同 west-ground）。
 * 内院：在台面开口里先铺内墙立面色，再把地面层内院平移 40 px 画进去，露出的部分就是北侧内墙面（斜俯视正确）。
 * 内院中央方塔 + 青石板四坡顶 + 旗；南面城门洞；四个尖角哨亭、棱面炮位。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWF.core;
  var G = isNode ? require('./geom.js') : root.TownArtWF.geom;
  var B = isNode ? require('./bastion.js') : root.TownArtWF.bastion;
  var PAL = C.PAL, f = C.f, CX = 144, CY = -144, A = 74, IN = 54, H = 40, WATER = '#a9b8ad';
  function outline(sc) {
    var q = [[A - 30, -A], [A - 30, -A - 22], [A + 40, -A - 40], [A + 22, -A + 30], [A, -A + 30]], out = [];
    for (var k = 0; k < 4; k++) q.forEach(function (p) { var r = B.rot(p, k); out.push([CX + r[0] * sc, CY + r[1] * sc]); });
    return out;
  }
  function sq(r, cx, cy) { return [[cx - r, cy + r], [cx - r, cy - r], [cx + r, cy - r], [cx + r, cy + r]]; }
  function draw(ctx) {
    var s = '', star = outline(1), moat = outline(1.17);
    // 护城河（地面层）
    s += C.poly(moat, WATER, 1.3) + C.poly(outline(1.06), '#c9c79a', 0) + C.lines(C.pts(outline(1.06)), 0.9, 0.6);
    var rip = '';
    for (var i = 0; i < 14; i++) { var p = moat[(i * 3) % moat.length], q = star[(i * 3) % star.length], m = [(p[0] * 2 + q[0]) / 3, (p[1] * 2 + q[1]) / 3]; rip += C.seg([m[0] - 3, m[1]], [m[0] + 3, m[1]]); }
    s += C.lines(rip, 0.8, 0.4);
    // 主体台面
    s += G.prism(ctx, star, H, star.map(function () { return 'wall'; }), { mode: 'ortho' });
    // 南面城门洞 + 吊桥
    var gy = CY + A, gx = CX;
    s += C.poly([[gx - 8, gy + 2], [gx + 8, gy + 2], [gx + 8, gy + 20], [gx - 8, gy + 20]], PAL.wood, 1.1) + C.lines(C.seg([gx - 8, gy + 8], [gx + 8, gy + 8]) + C.seg([gx - 8, gy + 14], [gx + 8, gy + 14]), 0.7, 0.5);
    s += C.path('M' + f(gx - 7) + ' ' + f(gy) + 'V' + f(gy - 16) + 'A7 7 0 0 1 ' + f(gx + 7) + ' ' + f(gy - 16) + 'V' + f(gy) + 'Z', PAL.hole, 1.4);
    // 内院开口
    var hole = G.lift(sq(IN, CX, CY), H), yard = sq(IN, CX, CY);
    s += G.clip(ctx, hole, C.poly(hole, PAL.stone2, 0) + C.lines(courses(hole), 0.8, 0.5) + C.poly(yard, '#d4c39a', 0) + C.lines(C.pts(yard), 1, 0.6));
    s += C.poly(hole, 'none', 1.4);
    // 炮位与哨亭
    var E = G.edges(star);
    E.forEach(function (e, i) {
      if (i % 5 === 1 || i % 5 === 2) { var t = 0.5, pt = [e.a[0] + (e.b[0] - e.a[0]) * t - e.n[0] * 9, e.a[1] + (e.b[1] - e.a[1]) * t - e.n[1] * 9]; s += B.cannon(pt, e.n, H); }
    });
    [2, 7, 12, 17].forEach(function (k) { var tp = star[k], v = [CX - tp[0], CY - tp[1]], L = Math.hypot(v[0], v[1]); s += B.guerite(ctx, tp[0] + v[0] / L * 10, tp[1] + v[1] / L * 10, H); });
    return s + keep(ctx);
  }
  function courses(hole) { var b = G.bbox(hole), d = ''; for (var y = b[1] + 8; y < b[3]; y += 8) d += 'M' + f(b[0]) + ' ' + f(y) + 'H' + f(b[2]); return d; }
  /** 内院中央方塔：24×24（半边 14），高 74，四面垛口，四坡青石板顶 */
  function keep(ctx) {
    var r = 14, cy = CY - 4, s = G.prism(ctx, sq(r, CX, cy), 74, ['wall', 'wall', 'wall', 'wall'], { mode: 'ortho' });
    s += C.poly([[CX - 1.2, cy + r - 30], [CX - 1.2, cy + r - 40], [CX + 1.2, cy + r - 40], [CX + 1.2, cy + r - 30]], PAL.hole, 0);
    var z = 74 + 9, L = CX - r + 3, R = CX + r - 3, T = cy - r + 3 - z, Bt = cy + r - 3 - z, ap = [CX, cy - z - 34];
    s += C.poly([[L, T], [R, T], ap], PAL.slate2, 1.1) + C.poly([[L, T], [L, Bt], ap], PAL.slate, 1.1) + C.poly([[R, T], [R, Bt], ap], PAL.slate2, 1.1) + C.poly([[L, Bt], [R, Bt], ap], PAL.slate, 1.3);
    s += C.lines(C.seg([L + 6, Bt], [CX - 2, ap[1] + 10]) + C.seg([R - 6, Bt], [CX + 2, ap[1] + 10]) + C.seg([CX, Bt], [CX, ap[1] + 4]), 0.8, 0.5);
    ctx.top(ap[1] - 18);
    return s + C.path(C.seg(ap, [ap[0], ap[1] - 16]), 'none', 1.3) + C.path('M' + f(ap[0]) + ' ' + f(ap[1] - 16) + 'q6 1 11 3.5q-6 0.8 -11 3.5Z', PAL.red, 0.7);
  }
  function items() {
    return [{ id: 'west-common-starfort-01', fp: [6, 6], draw: draw,
      meta: { category: 'landmark', kind: 'star_fort', facility: 'watchtower', culture: 'renaissance', variant: 1, name: '小星堡',
        tags: ['star_fort', 'bastion', 'moat', 'keep', 'cannon', 'guerite'],
        note: '整体小星堡地标：方形主体 + 四角尖棱堡（尖角朝 ne/se/sw/nw），台面高 40，外绕护城河（水色 #a9b8ad），南门带吊桥，内院中央方塔。facility 取最近的 watchtower' } }];
  }
  var API = { draw: draw, items: items };
  if (isNode) module.exports = API;
  else root.TownArtWF.starfort = API;
})(this);
