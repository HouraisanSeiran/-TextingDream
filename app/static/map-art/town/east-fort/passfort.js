/*
 * 织梦 · 东方关城地标 passfort-01（6×4，category=landmark，上伸 ≤ 240）：两山夹一座城关。
 * 左右两座青绿山体（叠晕 + 金线 + 皴线）夹住谷口，谷中一道东西向关墙（墙厚 36、WH=26，砖缝 / 垛口同 east-base），
 * 正中城台开拱门，台上重檐歇山关楼（下层 5 间 + 腰檐 + 上层 3 间带平座栏杆）。关墙两端伸进山脚，被前山遮住。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('../east-base/houses-a.js'));
  else root.TownArtFort_pass = factory(root.TownArtFort_core, root.TownArtEast_housesA);
})(this, function (F, HA) {
  'use strict';
  var E = F.E, C = F.C, T = F.T, f = F.f, sy = F.sy, WH = F.WH, PH = F.PH, PW = F.PW, mix = F.mix;
  // 山：屏幕坐标轮廓（底在 y = yb），三层叠晕由外向内收
  function mountain(ctx, pts, yb, seed) {
    var r = E.rng(seed), d = E.poly(pts), s = '', top = Math.min.apply(null, pts.map(function (p) { return p[1]; }));
    E.track(top - 2);
    s += E.path(d, C.teal, C.gold, 1.4);
    var cx = pts.reduce(function (a, p) { return a + p[0]; }, 0) / pts.length;
    [[0.78, mix(C.teal, C.tealL, 0.45)], [0.52, C.tealL]].forEach(function (q) {
      var sc = q[0], inner = pts.map(function (p) { return [cx + (p[0] - cx) * sc, yb + (p[1] - yb) * (sc + (1 - sc) * 0.25)]; });
      s += E.path(E.poly(inner), q[1]);
    });
    var j = '';
    for (var k = 0; k < 14; k++) {
      var x = pts[0][0] + r() * (pts[pts.length - 1][0] - pts[0][0]), y = top + 30 + r() * (yb - top - 50);
      j += 'M' + f(x) + ' ' + f(y) + 'l' + f(-4 - r() * 4) + ' ' + f(5 + r() * 4);
    }
    s += E.clip(ctx, d, E.line(j, C.navy, 0.8, ' stroke-opacity="0.45"'));
    return s + E.path(d, 'none', C.gold, 1.4);
  }
  function storey(x0, x1, g, z0, z1, n, wall, kind) {
    var s = E.face(x0, x1, g, z0, z1, wall), bw = (x1 - x0) / n, k;
    for (k = 0; k < n; k++) s += E.win(x0 + k * bw + bw * 0.2, g, z0 + (z1 - z0) * 0.28, bw * 0.6, (z1 - z0) * 0.44, kind);
    for (k = 0; k <= n; k++) s += E.col(x0 + k * bw, g, z0, z1, C.vermil);
    return s + E.face(x0 - 0.5, x1 + 0.5, g, z1 - 2, z1, C.teal, C.gold2, 0.5);
  }
  function draw(ctx) {
    var s = '', Z = WH, gB = -112, gF = -76, TG = T.gray;
    // 后山（远处一抹淡山）
    s += E.path(E.poly([[40, -200], [100, -330], [150, -270], [200, -360], [250, -210]]), mix(C.tealL, C.creamL, 0.45), C.gold, 0.8);
    // 关墙：东西两段 + 正中城台（更宽更高一点）
    s += F.topPoly(ctx, [[40, gB], [248, gB], [248, gF], [40, gF]], Z);
    s += F.merlonsH(40, 248, gB + PW, PW, Z, Z + 3.5, true);
    s += F.wallFace(ctx, 40, 248, gF, Z, [false, false]) + F.merlonsH(40, 248, gF, PW, Z, Z + PH, false);
    var cz = Z + 6;
    s += F.block(ctx, 108, 180, gB - 6, gF + 10, cz);
    s += F.gateArch(144, gF + 10, 20, 22) + E.rect(134, sy(gF + 10, cz - 4), 20, 4.4, C.navy, C.gold2, 0.7);
    s += F.ringCrenels(108, 180, gB - 6, gF + 10, cz, { south: false });
    // 关楼：重檐歇山
    var z1 = cz + 17, z2 = z1 + 15;
    s += E.shadow(116, 172, gB, gF + 2, 40, 6);
    s += storey(116, 172, gF + 2, cz, z1, 5, C.cream, 'lattice');
    s += HA.H.shed(ctx, 113, 175, gF + 2, z1 - 2, TG, 6, 4);
    s += storey(124, 164, gF - 2, z1 + 2, z2, 3, C.vermil, 'hex');
    s += HA.H.railing(124, 164, gF, z1 + 2, z1 + 5.5, C.vermil, 2.6);
    s += E.roofEW(ctx, { x0: 124, x1: 164, gb: gB + 2, gf: gF - 2, h: z2, rh: 15, type: 'xie', t: TG, ov: 7, os: 6, lift: 8, ridge: 'curl', ridgeW: 3.4 });
    // 关前一条青石路面（地面层）
    s += E.path(E.poly([[132, gF + 10], [156, gF + 10], [166, 0], [122, 0]]), C.stone, C.gold, 0.6);
    // 两座前山压住关墙两端
    // 山体内沿陡收在 x≈56 / 232 附近，两段关墙（x 56..108、180..232）露出来，只把墙端头埋进山脚
    s += mountain(ctx, [[0, -2], [0, -200], [22, -300], [44, -262], [62, -340], [84, -236], [72, -150], [60, -66], [54, -2]], -2, 71);
    s += mountain(ctx, [[236, -2], [228, -66], [216, -150], [206, -236], [226, -340], [246, -272], [266, -312], [288, -190], [288, -2]], -2, 73);
    return s;
  }
  function items() {
    // E.symbol 把上伸钳在 144；地标上限 240，这里按同样的包法自己包一次（最高点 = 山尖 y=-360，加 8 px 余量）
    var id = 'east-common-passfort-01', ctx = new E.Ctx(id, 9700), body = draw(ctx), W = 288, D = 192, up = 360 + 8 - D, H = D + up;
    var sym = { id: id, up: up, viewBox: [0, 0, W, H], anchor: [W / 2, H],
      svg: '<symbol id="' + id + '" viewBox="0 0 ' + W + ' ' + H + '" overflow="visible"><g transform="translate(0 ' + H + ')">' + body + '</g></symbol>' };
    return [{ id: id, svg: sym.svg, name: '关城', meta: { id: id, style: 'east', race: 'common', category: 'landmark', kind: 'pass_fort', facility: 'gate',
      variant: 1, footprint: [6, 4], height_px: sym.up, anchor: sym.anchor, viewBox: sym.viewBox, culture: 'chinese_frontier',
      tags: ['landmark', 'pass', 'mountains', 'double_eave', 'gate_tower', 'crenellated'], roof: 'hip_tile', name_zh: '关城',
      note: '两山夹一座城关：谷中关墙 + 城台拱门 + 重檐歇山关楼；山体占满左右两侧，路从城台门洞穿过（南北向通行）。歇山顶 roof 按最近值写 hip_tile' } }];
  }
  return { items: items };
});
