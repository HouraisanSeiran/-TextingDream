/*
 * 织梦 · 西式文化地标：童话式山顶城堡（gothic / romantic；参考新天鹅堡、霍亨索伦城堡的形制，原创程序化路径）
 * draw(c) 的 c = { rnd, W, H, up, id }：占地区 y = up..H；锚点 (W/2, H)。
 * 浏览器挂 window.TownArtWL_castles；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var P = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWL_core;
  var C = P.C, f = P.f, seg = P.seg, ln = P.ln, rect = P.rect, poly = P.poly, path = P.path;
  var defs = [];
  function def(o) { defs.push(o); }

  /** 双联拱窗：x 左，y 拱顶，w 总宽，h 高 */
  function winPair(x, y, w, h, glass) {
    var a = (w - 2.4) / 2;
    return P.win(x, y, a, h, { shape: 'arch', panes: false, sill: false, glass: glass, sw: 1 }) +
      P.win(x + a + 2.4, y, a, h, { shape: 'arch', panes: false, sill: false, glass: glass, sw: 1 }) +
      ln(seg(x - 1, y + h + 0.6, x + w + 1, y + h + 0.6), 1.2, 1);
  }
  /** 挑檐托石一圈（圆塔顶廊下方）：沿前半椭圆排小方块 */
  function corbels(cx, y, rr, n) {
    var o = '';
    for (var i = 0; i < n; i++) {
      var u = -0.9 + 1.8 * i / (n - 1), x = cx + u * rr, dy = rr * 0.5 * Math.sqrt(1 - u * u);
      o += rect(x - 1.1, y + dy, 2.2, 3.4, C.stone3, 0.7);
    }
    return o;
  }
  /**
   * 高瘦圆塔：cx 中线，yb 塔脚，r 半径，h 塔身高，ch 锥顶高；
   * opt.fill 墙色，opt.kind 'plain'|'ashlar'，opt.gallery 顶部挑出的一圈廊（带托石与窗），opt.flag 旗色，opt.wins 窗的高度比例
   */
  function roundTower(cx, yb, r, h, ch, rnd, opt) {
    opt = opt || {};
    var fill = opt.fill || C.plaster, yt = yb - h, o = '';
    o += P.cylinder(cx, yb, r, h, fill, opt.kind || 'plain', rnd, { top: false });
    (opt.wins || [0.3, 0.55]).forEach(function (t) { o += P.win(cx - r * 0.28, yb - h * t - 8, r * 0.56, 9, { shape: 'arch', panes: false, sw: 1 }); });
    if (opt.gallery) {
      var gr = r + 2.5, gh = 12;
      o += corbels(cx, yt - 1, gr - 1, Math.max(5, Math.round(r * 0.8)));
      o += P.cylinder(cx, yt + 2, gr, gh, fill, 'plain', rnd, { top: false });
      o += winPair(cx - gr * 0.5, yt - gh + 4, gr, 6) ;
      yt = yt + 2 - gh; r = gr;
    }
    o += P.cone(cx, yt, r, ch, opt.mat || 'slate', { finial: opt.flag ? false : true, flag: opt.flag, ov: 1.5 });
    return o;
  }
  /** 方塔：x0..x1，yb 塔脚，h 高，dg 顶面进深；攒尖顶 sh（0 = 垛口平顶）；四角小圆塔可选 */
  function squareTower(x0, x1, yb, h, dg, sh, rnd, opt) {
    opt = opt || {};
    var yt = yb - h, cx = (x0 + x1) / 2, o = '';
    if (sh) {
      o += P.pyramid(x0, x1, yt, dg, sh, opt.mat || 'slate', { ov: 2 });
    } else {
      o += poly([[x0, yt], [x1, yt], [x1, yt - dg], [x0, yt - dg]], C.stone3, 1.3) + P.merlons(x0, x1, yt - dg + 2.5, 4, 3.5, C.stone2);
    }
    o += P.wall(x0, x1, yt, yb, opt.kind || 'ashlar', rnd, { fill: opt.fill, ch: 7 });
    if (!sh) o += P.merlons(x0 - 1, x1 + 1, yt, 4.5, 3.5, opt.fill || C.stone);
    (opt.wins || [0.25, 0.5, 0.75]).forEach(function (t) { o += winPair(cx - 5, yb - h * t - 6, 10, 9); });
    if (opt.turrets) [x0, x1].forEach(function (x) { o += turret(x, yt + 14, 4.5, 16, 18, rnd, opt.fill); });
    return o;
  }
  /** 挑出的角楼（悬挑小圆塔）：cx，yb 塔身底，r，h 塔身，ch 锥高；下方倒锥托座 */
  function turret(cx, yb, r, h, ch, rnd, fill) {
    var o = path('M' + f(cx - r) + ' ' + f(yb) + 'L' + f(cx) + ' ' + f(yb + r * 2.2) + 'L' + f(cx + r) + ' ' + f(yb) + 'Z', C.stone3, 1.1);
    o += P.cylinder(cx, yb, r, h, fill || C.plaster, 'plain', rnd, { top: false });
    o += P.win(cx - 1.2, yb - h * 0.7, 2.4, 5, { shape: 'arch', panes: false, sill: false, sw: 0.7 });
    return o + P.cone(cx, yb - h, r, ch, 'slate', { ov: 1 });
  }
  /** 阶梯山墙（朝前）：底 x0..x1、底线 yb、高 h、n 阶 */
  function steppedGable(x0, x1, yb, h, n, fill) {
    var cx = (x0 + x1) / 2, st = (x1 - x0) / 2 / (n + 0.5), L = [[x0, yb]], i, y;
    for (i = 0; i < n; i++) { y = yb - h * (i + 1) / (n + 1); L.push([x0 + st * i, y]); L.push([x0 + st * (i + 1), y]); }
    L.push([x0 + st * n, yb - h]);
    var R = L.map(function (p) { return [2 * cx - p[0], p[1]]; }).reverse();
    return poly(L.concat(R), fill || C.plaster, 1.5);
  }
  /** 城堡主楼（宫殿体）：长边朝前，x0..x1，前沿 yb，墙高 h，n 层；陡坡屋顶 + 老虎窗 */
  function palas(x0, x1, yb, h, dg, rise, floors, rnd, opt) {
    opt = opt || {};
    var yE = yb - h, o = P.gableRoof(x0, x1, yE, dg, rise, opt.mat || 'slate', { ov: 3 });
    var nd = Math.max(1, Math.round((x1 - x0) / 34));
    for (var i = 0; i < nd; i++) {
      var dx = x0 + (i + 0.5) * (x1 - x0) / nd, dy = yE - dg * 0.25 - rise * 0.5;
      o += poly([[dx - 6, dy + 10], [dx - 6, dy], [dx, dy - 8], [dx + 6, dy], [dx + 6, dy + 10]], opt.fill || C.plaster, 1.1) +
        P.win(dx - 2.5, dy, 5, 8, { shape: 'arch', panes: false, sill: false, sw: 0.9 });
    }
    o += P.wall(x0, x1, yE, yb, opt.kind || 'plaster', rnd, { fill: opt.fill, ch: 7 });
    var fh = h / floors, nw = Math.max(2, Math.round((x1 - x0) / 20));
    for (var k = 0; k < floors; k++) {
      var wy = yE + fh * k + fh * 0.2;
      if (k) o += ln(seg(x0 + 1, yE + fh * k, x1 - 1, yE + fh * k), 1, 0.6);
      for (var j = 0; j < nw; j++) {
        var wx = x0 + (j + 0.5) * (x1 - x0) / nw;
        o += k === floors - 1 && opt.doorAt != null && Math.abs(wx - opt.doorAt) < 10 ? '' : winPair(wx - 5, wy, 10, fh * 0.5);
      }
    }
    return o;
  }
  /** 挡土台墙（台地）：x0..x1，yt..yb，墙顶垛口；扶壁间距 bs */
  function terrace(x0, x1, yt, yb, rnd, bs, merl, fill) {
    var o = P.wall(x0, x1, yt, yb, 'stone', rnd, { ch: 6, fill: fill || C.stone2, noShade: true });
    if (bs) for (var x = x0 + bs / 2; x < x1 - 4; x += bs) o += rect(x - 3, yt + 4, 6, yb - yt - 4, C.stone3, 1.1) + poly([[x - 3, yt + 4], [x + 3, yt + 4], [x, yt - 1]], C.stone3, 1);
    if (merl) o += P.merlons(x0, x1, yt, 4, 3.5, fill || C.stone2);
    return o;
  }
  /** 岩体上的林木：在 rock 内随机撒 n 棵树（避开 avoid(x,y) 为真的位置） */
  function forest(rock, n, y0, y1, rnd, avoid) {
    var o = '', pts = [];
    for (var i = 0; i < n * 3 && pts.length < n; i++) {
      var x = 14 + rnd() * 260, y = y0 + rnd() * (y1 - y0);
      if (!P.inside(rock, x - 8, y + 2) || !P.inside(rock, x + 8, y + 2)) continue;
      if (avoid && avoid(x, y)) continue;
      pts.push([x, y]);
    }
    pts.sort(function (a, b) { return a[1] - b[1]; });
    pts.forEach(function (p) { o += rnd() < 0.3 ? P.cypress(p[0], p[1], 20 + rnd() * 8) : P.tree(p[0], p[1], 7 + rnd() * 4, rnd); });
    return o;
  }
  /** 盘山步道：一条之字形折线（细墨线 + 浅沙色） */
  function trail(pts) {
    var d = P.pd(pts, true);
    return ln(d, 4.2, 0.55) + ln(d, 2.8, 1, C.sand);
  }

  // ——————————————————— 童话城堡 1：白墙蓝顶、高瘦塔楼（新天鹅堡气质） ———————————————————
  def({
    kind: 'castle_hill', variant: 1, name: '白墙童话城堡', fp: [6, 6], up: 240, seed: 3101,
    facility: 'lord_hall', culture: 'romantic', roof: 'steep_slate',
    tags: ['hilltop', 'crag', 'fairytale', 'white_walls', 'slender_towers', 'cone_spires', 'gatehouse', 'terrace', 'important'],
    note: '岩石山顶的浪漫主义城堡：白灰泥墙、青石板陡顶；四层主楼正中一座凸出的阶梯山墙翼与阳台，楼后一高一矮两座细圆塔（顶部挑廊 + 尖锥 + 旗），' +
      '左前高瘦圆塔、右前方形主塔（四角悬挑小角楼 + 尖顶）；山顶一圈带垛口的胸墙，下层台地上是暖石门楼与两座小圆塔，之字形步道下山',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '';
      o += P.boxShadow(14, 274, 340, yf, 6, W, H);
      var rock = [[8, 522], [14, 482], [26, 446], [36, 408], [44, 378], [56, 356], [100, 348], [210, 346], [244, 352], [256, 372],
        [264, 404], [272, 444], [278, 484], [282, 522]];
      o += P.crag(rock, r, { strata: 26 });
      // 楼后两座细圆塔（后排先画）
      o += roundTower(112, 252, 9, 150, 62, r, { gallery: true, flag: C.red, wins: [0.35, 0.6, 0.82] });
      o += squareTower(166, 190, 254, 110, 14, 40, r, { fill: C.plaster, kind: 'plaster', wins: [0.55, 0.8] });
      // 主楼：四层，正中凸出阶梯山墙翼
      o += palas(58, 198, 346, 118, 44, 36, 4, r, { fill: C.plaster });
      o += turret(58, 248, 5.5, 22, 24, r) + turret(198, 248, 5.5, 22, 24, r);
      o += P.wall(104, 150, 214, 346, 'plaster', r, {}) + steppedGable(104, 150, 214, 40, 4, C.plaster);
      o += P.win(122, 190, 6, 10, { shape: 'arch', panes: false });
      o += winPair(112, 224, 26, 26, null) + winPair(114, 260, 22, 18) + winPair(114, 290, 22, 18);
      o += rect(108, 314, 38, 3, C.stone3, 1.1) + ln(seg(108, 308, 146, 308) + seg(112, 308, 112, 314) + seg(120, 308, 120, 314) + seg(128, 308, 128, 314) + seg(136, 308, 136, 314) + seg(144, 308, 144, 314), 1, 0.85);
      o += P.door(127, 346, 12, 20, { shape: 'arch', frame: C.stone2 });
      // 左前高瘦圆塔
      o += roundTower(44, 362, 12, 176, 58, r, { gallery: true, flag: C.slate, wins: [0.2, 0.42, 0.64, 0.84] });
      // 右前方形主塔：四角悬挑角楼 + 尖顶
      o += squareTower(206, 236, 364, 190, 16, 56, r, { fill: C.plaster, kind: 'plaster', wins: [0.2, 0.38, 0.56, 0.74], turrets: true });
      o += P.flag(221, 364 - 190 - 8 - 56 - 8, 14, 10, C.red);
      // 山顶胸墙
      o += P.wall(26, 264, 352, 368, 'stone', r, { ch: 6, fill: C.stone }) + P.merlons(26, 264, 352, 4, 3.5, C.stone);
      // 盘山步道（门楼往下）
      o += trail([[150, 440], [196, 462], [118, 486], [168, 520]]);
      // 下层台地：挡土墙 + 暖石门楼 + 两座小圆塔
      o += terrace(64, 230, 410, 442, r, 26, false);
      o += P.gableRoof(94, 204, 372, 20, 12, 'slate', { ov: 2 });
      o += P.wall(94, 204, 372, 412, 'ashlar', r, { fill: C.wash, ch: 6 });
      [104, 124, 168, 188].forEach(function (x) { o += winPair(x - 5, 380, 10, 10); });
      o += path(P.archPath(140, 384, 20, 28), C.dark, 1.5) + P.flag(150, 372 - 22, 14, 10, C.red);
      [[86, 12], [212, 12]].forEach(function (t) {
        o += P.cylinder(t[0], 418, t[1], 52, C.wash, 'ashlar', r, { top: false }) + P.cone(t[0], 366, t[1], 30, 'slate', {});
        o += P.win(t[0] - 2, 384, 4, 8, { shape: 'arch', panes: false });
      });
      // 岩上林木
      o += forest(rock, 22, 420, 512, r, function (x, y) { return y < 445 && x > 60 && x < 236; });
      return o;
    }
  });

  /** 半圆棱台（台地外凸的圆形炮台）：cx，yb 底，r，h；顶一圈垛口 */
  function roundBastion(cx, yb, r, h, rnd) {
    return P.cylinder(cx, yb, r, h, C.stone2, 'stone', rnd, { topFill: C.stone3 }) + P.ringMerlons(cx, yb - h, r, Math.max(5, Math.round(r / 3)), C.stone2);
  }

  // ——————————————————— 童话城堡 2：暖石多塔、层层台地（霍亨索伦城堡气质） ———————————————————
  def({
    kind: 'castle_hill', variant: 2, name: '暖石多塔山城', fp: [6, 6], up: 240, seed: 3102,
    facility: 'lord_hall', culture: 'gothic', roof: 'steep_slate',
    tags: ['hilltop', 'crag', 'fairytale', 'warm_stone', 'many_spires', 'terraces', 'bastions', 'chapel', 'gatehouse', 'important'],
    note: '山脊上的哥特复兴式城堡：暖黄砂岩墙、青石板尖顶；山坡上三道带垛口的台地城墙层层退进，最外一道有两座圆炮台与门楼；' +
      '山顶主楼两翼高低错落，后排一座最高的八角主塔（尖顶 + 旗），左侧方塔四角小尖塔，右侧城堡礼拜堂（尖拱长窗 + 玫瑰窗 + 小尖塔），' +
      '另有三座细圆塔顶着尖锥',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '', ws = C.wash;
      o += P.boxShadow(14, 274, 330, yf, 6, W, H);
      var rock = [[6, 522], [16, 488], [30, 456], [48, 426], [70, 398], [96, 382], [190, 380], [222, 394], [246, 420],
        [262, 452], [276, 488], [284, 522]];
      o += P.crag(rock, r, { strata: 24, fill: C.stone2 });
      // —— 后排：最高主塔（八角感：两条棱线 + 尖顶） ——
      var kx0 = 128, kx1 = 160;
      o += P.pyramid(kx0, kx1, 196, 14, 66, 'slate', { ov: 3, finial: false }) + P.flag(144, 196 - 7 - 66 - 1, 16, 11, C.red);
      o += P.wall(kx0, kx1, 196, 300, 'ashlar', r, { fill: ws, ch: 7 });
      o += ln(seg(kx0 + 8, 197, kx0 + 8, 299) + seg(kx1 - 8, 197, kx1 - 8, 299), 1, 0.6);
      o += P.merlons(kx0 - 2, kx1 + 2, 196, 4, 3, ws);
      [210, 236, 262].forEach(function (y) { o += winPair(139, y, 10, 12); });
      // 后排细圆塔两座
      o += roundTower(92, 300, 8, 96, 44, r, { fill: ws, kind: 'ashlar', mat: 'slate', wins: [0.45, 0.75] });
      o += roundTower(196, 296, 8, 104, 48, r, { fill: ws, kind: 'ashlar', mat: 'slate', wins: [0.45, 0.75], flag: C.slate });
      // —— 山顶主楼：左翼高、右翼低 ——
      o += palas(56, 140, 372, 92, 40, 34, 3, r, { fill: ws, kind: 'ashlar' });
      o += palas(140, 206, 372, 74, 36, 28, 2, r, { fill: ws, kind: 'ashlar', doorAt: 173 });
      o += P.door(173, 372, 12, 20, { shape: 'arch', frame: C.stone3 });
      // 左侧方塔：四角小尖塔 + 中央尖顶
      o += squareTower(26, 58, 384, 150, 16, 50, r, { fill: ws, wins: [0.2, 0.42, 0.64, 0.84] });
      [28, 56].forEach(function (x) { o += P.pinnacle(x, 234, 24, 6); });
      // 右侧礼拜堂：山墙朝前，尖拱长窗、玫瑰窗，屋脊小尖塔
      var cg = P.gableFront(206, 254, 300, 60, 34, 'slate', { ov: 2, fill: ws });
      o += cg.roof + rect(226, 236, 8, 18, ws, 1.1) + P.pyramid(224, 236, 236, 6, 30, 'slate', { finial: false }) + P.cross(230, 188, 9);
      o += cg.gable + P.wall(206, 254, 300, 380, 'ashlar', r, { fill: ws, ch: 7 });
      o += P.roseWindow(230, 286, 7, 8);
      [212, 236].forEach(function (x) { o += P.win(x, 314, 7, 30, { shape: 'point', stain: true }); });
      [204, 256].forEach(function (x) { o += P.buttress(x - 3.5, 380, 304, 7); });
      // 前排细圆塔（主楼左前角）
      o += roundTower(70, 392, 10, 124, 50, r, { fill: ws, kind: 'ashlar', gallery: true, flag: C.red, wins: [0.3, 0.55, 0.8] });
      // —— 台地 1（山顶胸墙）——
      o += terrace(40, 262, 384, 404, r, 0, true, C.stone);
      // —— 台地 2 ——
      o += terrace(34, 254, 420, 446, r, 32, true);
      // —— 台地 3（最外）：墙 + 两座圆炮台 + 门楼 ——
      o += trail([[148, 446], [104, 462], [176, 478]]);
      o += terrace(22, 266, 470, 500, r, 0, true);
      o += roundBastion(44, 506, 20, 40, r) + roundBastion(244, 506, 20, 40, r);
      o += rect(130, 458, 36, 48, ws, 1.6) + P.courses(130, 166, 458, 506, 6, r, 9) + P.merlons(129, 167, 458, 4.5, 3.5, ws);
      [131, 165].forEach(function (x) { o += turret(x, 470, 4, 12, 16, r, ws); });
      o += path(P.archPath(140, 478, 16, 28), C.dark, 1.4) + P.flag(148, 458, 18, 12, C.red);
      o += trail([[148, 506], [148, 522]]);
      o += forest(rock, 10, 448, 470, r, function (x) { return x > 120 && x < 176; });
      o += forest(rock, 8, 506, 520, r, function (x) { return x > 20 && x < 268; });
      return o;
    }
  });

  if (typeof module !== 'undefined' && module.exports) module.exports = defs;
  else root.TownArtWL_castles = defs;
})(typeof window !== 'undefined' ? window : this);
