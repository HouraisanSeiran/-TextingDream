/*
 * 织梦 · 西式工业与基础设施（木刻线描 + 羊皮纸淡彩，3/4 斜俯视，尚未接入游戏）
 *
 * 每个定义：{ kind, idKind, facility, variant, w, d, up, tags, roof, note, draw(W, D, r) }
 * draw 在“地面坐标”里画：占地 x∈[0,W]、y∈[0,D]，y=D 是前沿；高度画成负 y。
 * 组装（special-infra.js）时整体下移 up 像素。
 *
 * 浏览器挂 window.TownArtInfraWest；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./infra-core.js') : root.TownArtInfraCore;
  var S = C.WEST, f = C.f, poly = C.poly, pl = C.pl, path = C.path, rect = C.rect, ell = C.ell, circ = C.circ;
  var ln = C.ln, lines = C.lines, fop = C.fop;
  var I = S.ink, LW = S.lw, LD = S.lwd;
  var defs = [];
  function def(o) { o.style = 'west'; defs.push(o); }

  /** 夯土场地垫（只在占地内）。 */
  function pad(x0, y0, x1, y1) { return poly([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], S.stone, null, 0, fop(0.45)); }

  /** 木刻式车轮/水轮：轮面平行于正面，圆心 (cx, cy)，半径 R。 */
  function wheel(cx, cy, R, n, paddles) {
    var o = circ(cx, cy, R, S.wood, I, LW) + circ(cx, cy, R - 3.5, 'none', I, LD);
    var s = [];
    for (var i = 0; i < n; i++) {
      var a = i / n * Math.PI * 2, c = Math.cos(a), sn = Math.sin(a);
      s.push([cx + c * 2.5, cy + sn * 2.5, cx + c * (R - 3.5), cy + sn * (R - 3.5)]);
      if (paddles) s.push([cx + c * (R - 1), cy + sn * (R - 1), cx + c * (R + 2.5), cy + sn * (R + 2.5)]);
    }
    return o + lines(s, I, 1.2) + circ(cx, cy, 2.8, S.dark, I, 0.9);
  }

  // ================= 冶炼厂（高炉 + 水力鼓风棚 + 矿渣堆） =================
  def({
    kind: 'smelter_blast', idKind: 'smelter', facility: 'smelter', variant: 1, w: 3, d: 2, up: 100,
    tags: ['blast_furnace', 'water_bellows', 'slag_heap', 'smoke'], roof: 'gable_thatch',
    note: '石砌高炉（上窄下宽、顶部装料口冒火）、左侧木构装料坡道、右侧水轮带动皮风箱的鼓风棚、前方出铁口与砂床、左前矿渣堆。水槽沿前沿东西向，紧邻水渠摆放更自然。',
    draw: function (W, D, r) {
      var o = '';
      // 投影
      o += C.shadow(28, 26, 80, 70, 12, S) + C.shadow(88, 34, 140, 74, 6, S, 3);
      o += pad(4, 18, 142, 94);
      // —— 高炉：四棱台石砌 ——
      var bx0 = 28, bx1 = 80, tx0 = 37, tx1 = 71, yb = 70, yk = 26, H = 92, yt = 62 - H, ytb = 34 - H;
      o += poly([[tx0, ytb], [tx1, ytb], [tx1, yt], [tx0, yt]], S.stone3, I, LW);                 // 顶面
      o += poly([[bx0, yk], [tx0, ytb], [tx0, yt], [bx0, yb]], S.stone, I, LW);                   // 左侧（受光）
      o += poly([[bx1, yk], [tx1, ytb], [tx1, yt], [bx1, yb]], S.stone3, I, LW);                  // 右侧（背光）
      var front = [[bx0, yb], [bx1, yb], [tx1, yt], [tx0, yt]];
      o += poly(front, S.stone2, I, LW);
      o += C.clip('west-common-smelter-01-cf', poly(front, '#000'), C.rubble(bx0, yt, bx1, yb, r, I, 0.45));
      // 箍铁两道
      [0.35, 0.68].forEach(function (k) {
        var y = yb + (yt - yb) * k, xl = bx0 + (tx0 - bx0) * k, xr = bx1 + (tx1 - bx1) * k;
        o += ln(xl, y, xr, y, S.iron, 2.2) + ln(xl, y - 1.6, xr, y - 1.6, I, 0.7, 0.6);
      });
      // 装料口：顶面里的火口
      o += ell(54, (ytb + yt) / 2, 11, 6, S.dark, I, LD) + ell(54, (ytb + yt) / 2 + 0.8, 7.5, 3.6, S.fire, null, 0) +
        path('M48 ' + f(yt - 12) + 'q2 -9 5 -12q-1 6 3 8q1 -5 4 -7q0 7 -3 11z', S.glow, I, 0.9);
      o += C.smoke(52, yt - 22, S, 4, 11);
      // 出铁口：正面底部拱洞
      o += path(C.archD(54, yb, 15, 6), S.dark, I, LW) + path(C.archD(54, yb, 9, 3), S.fire, null, 0);
      // 风口管：从鼓风棚伸进高炉右侧
      o += ln(76, 52, 90, 52, S.iron, 3.2) + ln(76, 52, 90, 52, I, 0.8, 0.6);
      // —— 装料坡道：木构斜桥，搭到炉顶 ——
      var g0 = [3, 36], g1 = [38, -40];
      [8, 17, 26].forEach(function (x) {
        var t = (x - g0[0]) / (g1[0] - g0[0]), y = g0[1] + (g1[1] - g0[1]) * t;
        o += ln(x, y + 3, x, 48, S.dark, 1.8) + ln(x, y + 3, x, 48, I, 0.6, 0.5);
      });
      o += poly([[g0[0], g0[1]], [g1[0], g1[1]], [g1[0], g1[1] + 5], [g0[0], g0[1] + 5]], S.wood, I, 1.3);
      var cl = [];
      for (var k = 1; k < 9; k++) {
        var t = k / 9, x = g0[0] + (g1[0] - g0[0]) * t, y = g0[1] + (g1[1] - g0[1]) * t;
        cl.push([x - 1, y + 0.4, x + 2, y - 0.6]);
      }
      o += lines(cl, I, 0.9, 0.7) + ln(g0[0], g0[1] - 7, g1[0], g1[1] - 7, I, 1, 0.8) +
        ln(g1[0], g1[1] - 7, g1[0], g1[1], I, 1, 0.8) + ln(g0[0], g0[1] - 7, g0[0], g0[1], I, 1, 0.8);
      // —— 鼓风棚：茅草两坡顶，前墙开大洞露出皮风箱 ——
      var hs = C.gableEW(88, 34, 140, 74, 26, 16, { wall: S.plaster, roof: S.thatch, back: S.thatch2, ink: I, lw: LW, ov: 3 });
      o += hs.s + C.tileRows(hs.x0, hs.ry, hs.x1, hs.ey, 4, S.thatch2, 0.9, r);
      o += rect(93, 54, 20, 20, S.dark, I, 1.2);
      o += ln(93, 54, 93, 74, S.grain, 2.4) + ln(113, 54, 113, 74, S.grain, 2.4);
      o += poly([[96, 64], [102, 59], [111, 57], [111, 71], [102, 69]], S.wash, I, 1) +
        lines([[103, 59.5, 103, 68.5], [106, 58.6, 106, 69.6], [109, 57.8, 109, 70.5]], I, 0.8, 0.7) +
        ln(96, 64, 94, 64, S.iron, 2) + ln(102, 56, 111, 55, S.grain, 1.6);
      o += C.planks(114, 48, 140, 74, 6, true, S.grain, 0.45);
      // —— 前沿水槽 + 水轮 ——
      o += rect(104, 79, 40, 13, S.water, I, 1) + lines([[108, 84, 114, 84], [124, 88, 131, 88], [134, 82, 140, 82]], I, 0.8, 0.4);
      o += wheel(127, 68, 15, 8, true);
      // —— 出铁砂床 ——
      o += poly([[38, 76], [70, 76], [72, 90], [36, 90]], S.paper, I, 1) +
        lines([[54, 70, 54, 88], [42, 80, 66, 80], [42, 85, 66, 85]], S.fire, 1.4) +
        lines([[44, 78, 44, 88], [50, 78, 50, 88], [58, 78, 58, 88], [64, 78, 64, 88]], S.red, 1, 0.7);
      // —— 矿渣堆 ——
      o += C.shadowEll(18, 89, 15, 4, 6, S) + C.dome(18, 90, 16, 4, 15, S.slate2, I, LW);
      var lumps = [];
      for (var q = 0; q < 9; q++) { var lx = 7 + r() * 22, ly = 80 + r() * 9; lumps.push([lx, ly, lx + 2 + r() * 2, ly - 1]); }
      o += lines(lumps, '#2f3438', 1.4, 0.7) + C.dome(32, 91, 5, 2, 5, S.slate, I, 1);
      return o;
    }
  });

  /** 小划船：船舷椭圆 (cx, cy, rx, ry)，船身朝前鼓出。 */
  function rowboat(cx, cy, rx, ry, dark) {
    var o = C.shadowEll(cx, cy + ry + 3, rx, 3, 5, S);
    o += path('M' + f(cx - rx) + ' ' + f(cy) + 'C' + f(cx - rx + 4) + ' ' + f(cy + ry + 9) + ' ' + f(cx + rx - 4) + ' ' + f(cy + ry + 9) + ' ' +
      f(cx + rx) + ' ' + f(cy) + 'Z', S.wood, I, LW);
    o += lines([[cx - rx + 3, cy + 4, cx + rx - 3, cy + 4], [cx - rx + 7, cy + 8, cx + rx - 7, cy + 8]], S.grain, 0.8, 0.7);
    o += ell(cx, cy, rx, ry, dark || S.dark, I, LW) + ell(cx, cy + 1, rx - 3, ry - 2, S.grain, null, 0);
    o += lines([[cx - rx * 0.35, cy - ry + 1.5, cx - rx * 0.35, cy + ry - 1.5], [cx + rx * 0.3, cy - ry + 1.5, cx + rx * 0.3, cy + ry - 1.5]], S.wood, 2.2);
    return o;
  }
  /** 系缆柱：铁或木的短桩。 */
  function bollard(x, y) { return C.cyl(x, y, 3, 1.6, 6, S.iron, '#7a776f', I, 1) + ell(x, y - 6, 4, 2, 'none', I, 0.8); }
  function crate(x, y, s) {
    return C.box(x, y - s * 0.6, x + s, y, s * 0.9, S.wash, S.wood, I, 1) +
      lines([[x, y - s * 0.9, x + s, y], [x + s, y - s * 0.9, x, y]], S.grain, 0.8, 0.7);
  }
  function barrel(x, y) {
    return C.cyl(x, y, 4.5, 2.2, 10, S.wood, S.wash, I, 1) +
      lines([[x - 4.5, y - 2.5, x + 4.5, y - 2.5], [x - 4.5, y - 7.5, x + 4.5, y - 7.5]], S.iron, 1.1);
  }

  // ================= 码头（木栈桥 + 吊杆 + 系缆柱 + 小船） =================
  def({
    kind: 'dock_pier', idKind: 'dock', facility: 'dock', variant: 1, w: 3, d: 2, up: 74,
    tags: ['waterside_south', 'pier', 'crane', 'bollard', 'boat'], roof: 'none',
    note: '临水边朝南：占地后部约 0.6 格是石砌岸壁与货场，其余是水面，木栈桥向南伸进水里。放置时让地块前沿（南）贴河道或海岸，后沿接陆地道路。',
    draw: function (W, D, r) {
      var o = '';
      // 水面（岸壁以南全部是水）
      o += C.water(0, 30, W, D, S, 21);
      // 岸上货场 + 岸壁正面
      o += rect(0, 0, W, 26, S.stone, null, 0) + C.rubble(0, 0, W, 26, r, I, 0.25);
      o += rect(0, 26, W, 8, S.stone2, I, LW) + C.rubble(0, 26, W, 34, r, I, 0.5);
      o += C.shadow(0, 26, W, 34, 0, S, 3).replace(/points="[^"]*"/, 'points="0,34 ' + W + ',34 ' + W + ',37 0,37"');
      // 栈桥：桥墩先画（在水里），再画桥面
      var px0 = 58, px1 = 88, py1 = 86, dh = 5;
      for (var y = 46; y <= py1; y += 20) {
        o += C.cyl(px0 + 2, y + 2, 2.4, 1.2, 0, null, null) +
          ln(px0 + 2, y - dh, px0 + 2, y + 5, S.dark, 3.4) + ln(px1 - 2, y - dh, px1 - 2, y + 5, S.dark, 3.4) +
          ell(px0 + 2, y + 5, 3.5, 1.2, 'none', '#f3ead2', 0.8) + ell(px1 - 2, y + 5, 3.5, 1.2, 'none', '#f3ead2', 0.8);
      }
      o += poly([[px1, 26 - dh], [px1 + 7, 29 - dh], [px1 + 7, py1 + 3], [px0 + 4, py1 + 3]], S.shadow, null, 0, fop(S.sop));
      o += C.box(px0, 26, px1, py1, dh, S.wood, S.grain, I, LW);
      o += C.planks(px0, 26 - dh, px1, py1 - dh, 4.5, false, S.grain, 0.55);
      o += lines([[px0 + 6, 30 - dh, px0 + 6, py1 - dh], [px1 - 6, 30 - dh, px1 - 6, py1 - dh]], S.dark, 0.8, 0.5);
      // 桥头系缆柱 + 岸上系缆柱
      o += bollard(px0 + 4, py1 - dh - 2) + bollard(px1 - 4, py1 - dh - 2);
      o += bollard(18, 25) + bollard(128, 25);
      // 小船系在栈桥右边，缆绳拴到桥头柱
      o += rowboat(114, 62, 19, 6);
      o += path('M' + f(px1 - 4) + ' ' + f(py1 - dh - 8) + 'Q102 ' + f(py1 - 8) + ' 98 64', null, S.dark, 0.9);
      // 左侧水里再泊一条小舢板（被岸壁挡住一点）
      o += rowboat(26, 52, 15, 5, S.grain);
      // 吊杆：岸上立柱 + 斜撑 + 挑臂，吊着一只货箱悬在栈桥上
      var mx = 42, my = 20, mh = 58;
      o += C.shadow(mx - 2, my - 2, mx + 2, my, 8, S, 2);
      o += ln(mx, my, mx, my - mh, S.dark, 4) + ln(mx, my, mx, my - mh, I, 1, 0.6);
      o += ln(mx - 10, my, mx, my - 22, S.wood, 2.4) + ln(mx + 10, my, mx, my - 22, S.wood, 2.4);
      o += ln(mx, my - mh + 6, 74, my - mh - 6, S.wood, 3.4) + ln(mx, my - mh + 6, 74, my - mh - 6, I, 0.9, 0.7);
      o += ln(mx, my - mh, 74, my - mh - 6, I, 0.8);
      o += ln(74, my - mh - 6, 74, 26, I, 0.9);
      o += circ(mx - 3, my - 14, 4.2, S.wood, I, 1) + circ(mx - 3, my - 14, 1.4, S.dark, null, 0);
      o += crate(68, 30, 12);
      // 岸上货物
      o += crate(100, 20, 13) + crate(112, 22, 10) + barrel(8, 22) + barrel(16, 15) + barrel(134, 15);
      o += C.logPile(118, 10, 3, 2, S);
      return o;
    }
  });

  // ================= 砖窑（圆顶蜂窝窑 + 柴堆 + 晾坯架） =================
  def({
    kind: 'kiln_beehive', idKind: 'kiln', facility: 'kiln', variant: 1, w: 2, d: 2, up: 62,
    tags: ['beehive_kiln', 'brick', 'woodpile', 'smoke'], roof: 'none',
    note: '砖砌圆顶窑（蜂窝窑），前方拱形火门吐火，顶上一截短烟道；右侧柴堆，左前码着刚出窑的砖垛。窑本身没有屋顶，roof 记 none。',
    draw: function (W, D, r, id) {
      var o = '', cx = 46, cy = 64, rx = 32, ry = 13, hh = 56;
      o += C.shadowEll(cx, cy, rx, ry, 14, S);
      o += pad(2, 22, 94, 94);
      o += C.dome(cx, cy, rx, ry, hh, S.tile, I, LW);
      o += C.clip(id + '-d', path(C.domeD(cx, cy, rx, ry, hh), '#000'),
        C.brick(cx - rx, cy - hh, cx + rx, cy + ry, 5.5, 9, I, 0.4) +
        path(C.domeD(cx - 9, cy + 4, rx * 0.55, ry, hh * 0.92), '#c87a5b', null, 0, fop(0.75)));
      o += path(C.domeD(cx, cy, rx, ry, hh), null, I, LW);
      // 加固铁箍
      o += path('M' + f(cx - rx + 3) + ' ' + f(cy - 14) + 'Q' + f(cx) + ' ' + f(cy - 2) + ' ' + f(cx + rx - 3) + ' ' + f(cy - 14), null, S.iron, 2);
      // 烟道 + 烟
      o += C.cyl(cx + 4, cy - hh + 4, 6, 2.6, 12, S.red, S.dark, I, LD) + C.smoke(cx + 2, cy - hh - 12, S, 3, 3);
      // 火门
      o += path(C.archD(cx, cy + 10, 18, 7), S.stone2, I, LW) + path(C.archD(cx, cy + 10, 12, 5), S.dark, I, LD) +
        path('M' + f(cx - 5) + ' ' + f(cy + 10) + 'q2 -8 5 -10q0 5 3 6q1 -3 2 -4q1 5 -1 8z', S.fire, null, 0);
      // 柴堆（右侧）
      o += C.shadow(72, 64, 92, 84, 5, S, 2) + C.logPile(70, 86, 4, 3, S);
      // 砖垛（左前）
      for (var j = 0; j < 3; j++) o += C.box(6, 78 - j * 0, 24, 88, 6 + j * 4, j === 2 ? S.tile : S.red, S.tile, I, LD);
      o += lines([[6, 84 - 14, 24, 84 - 14], [15, 88 - 14, 15, 88]], I, 0.7, 0.5);
      return o;
    }
  });

  // ================= 陶窑（英式瓶形窑 + 坯棚） =================
  def({
    kind: 'kiln_bottle', idKind: 'kiln', facility: 'kiln', variant: 2, w: 2, d: 2, up: 112,
    tags: ['bottle_kiln', 'pottery', 'smoke', 'drying_shed'], roof: 'monopitch',
    note: '瓶形陶窑：红砖砌的瓶身（下鼓上收、顶口冒烟），底部火门；左侧一间单坡坯棚，棚前晾着陶罐坯。roof 记的是坯棚的单坡顶。',
    draw: function (W, D, r, id) {
      var o = '', cx = 56, by = 74;
      o += C.shadowEll(cx, by, 26, 9, 16, S);
      o += pad(2, 24, 94, 94);
      // 坯棚（左后）
      o += rect(4, 32, 26, 34, S.plaster, I, LW) + C.planks(4, 32, 30, 66, 6.5, true, S.grain, 0.45);
      o += poly([[1, 26], [34, 18], [34, 34], [1, 40]], S.thatch, I, LW) + C.tileRows(1, 20, 34, 40, 4, S.thatch2, 0.7);
      // 瓶身
      var d = 'M' + f(cx - 30) + ' ' + f(by) + 'C' + f(cx - 34) + ' ' + f(by - 40) + ' ' + f(cx - 14) + ' ' + f(by - 82) + ' ' + f(cx - 9) + ' ' + f(by - 140) +
        'L' + f(cx + 9) + ' ' + f(by - 140) + 'C' + f(cx + 14) + ' ' + f(by - 82) + ' ' + f(cx + 34) + ' ' + f(by - 40) + ' ' + f(cx + 30) + ' ' + f(by) +
        'A30 10 0 0 1 ' + f(cx - 30) + ' ' + f(by) + 'Z';
      o += path(d, S.tile, I, LW);
      o += C.clip(id + '-b', path(d, '#000'), C.brick(cx - 36, by - 142, cx + 36, by + 12, 5, 9, I, 0.35) +
        path('M' + f(cx + 4) + ' ' + f(by - 140) + 'C' + f(cx + 10) + ' ' + f(by - 80) + ' ' + f(cx + 30) + ' ' + f(by - 40) + ' ' + f(cx + 30) + ' ' + f(by + 12) +
          'L' + f(cx + 40) + ' ' + f(by + 12) + 'L' + f(cx + 40) + ' ' + f(by - 140) + 'Z', S.red, null, 0, fop(0.45)));
      o += path(d, null, I, LW);
      [by - 30, by - 66].forEach(function (y, k) {
        var hw = k ? 18 : 29;
        o += path('M' + f(cx - hw) + ' ' + f(y) + 'Q' + f(cx) + ' ' + f(y + 6) + ' ' + f(cx + hw) + ' ' + f(y), null, S.iron, 2);
      });
      o += ell(cx, by - 140, 9, 3, S.dark, I, LD) + C.smoke(cx - 2, by - 148, S, 3, 9);
      o += path(C.archD(cx, by + 8, 14, 9), S.dark, I, LW) + path('M' + f(cx - 4) + ' ' + f(by + 8) + 'q2 -7 4 -8q1 4 3 5q1 -2 1 -3q1 4 -1 6z', S.fire, null, 0);
      // 晾着的陶罐坯
      [[10, 84], [20, 86], [30, 88]].forEach(function (p) {
        o += path('M' + f(p[0] - 3) + ' ' + f(p[1]) + 'Q' + f(p[0] - 6) + ' ' + f(p[1] - 6) + ' ' + f(p[0] - 2) + ' ' + f(p[1] - 10) + 'L' + f(p[0] + 2) + ' ' + f(p[1] - 10) +
          'Q' + f(p[0] + 6) + ' ' + f(p[1] - 6) + ' ' + f(p[0] + 3) + ' ' + f(p[1]) + 'Z', S.wash, I, 1);
      });
      o += C.logPile(78, 92, 2, 2, S);
      return o;
    }
  });

  /** 一张撑开的生皮。 */
  function hide(cx, top, w, h, col) {
    var x0 = cx - w / 2, x1 = cx + w / 2, b = top + h;
    var d = 'M' + f(x0) + ' ' + f(top) + 'L' + f(x1) + ' ' + f(top) + 'L' + f(x1 + 2) + ' ' + f(top + h * 0.25) + 'L' + f(x1 - 1) + ' ' + f(top + h * 0.45) +
      'L' + f(x1 + 1.5) + ' ' + f(b - 2) + 'L' + f(cx + w * 0.15) + ' ' + f(b) + 'L' + f(cx - w * 0.15) + ' ' + f(b) + 'L' + f(x0 - 1.5) + ' ' + f(b - 2) +
      'L' + f(x0 + 1) + ' ' + f(top + h * 0.45) + 'L' + f(x0 - 2) + ' ' + f(top + h * 0.25) + 'Z';
    return path(d, col, I, 1) + ln(cx, top + 2, cx, b - 3, S.grain, 0.7, 0.5);
  }

  // ================= 制革坊（鞣池 + 晾皮架 + 木筋工棚） =================
  def({
    kind: 'tannery_yard', idKind: 'tannery', facility: 'tannery', variant: 1, w: 3, d: 2, up: 56,
    tags: ['tanning_pits', 'hide_rack', 'workshop', 'smelly'], roof: 'gable_thatch',
    note: '左后木筋灰泥工棚（茅草顶），前方一排六口砌在地里的鞣池（树皮液深浅不同），右侧木架上撑着几张生皮，旁边码着树皮捆与木桶。',
    draw: function (W, D, r, id) {
      var o = '';
      o += C.shadow(4, 20, 64, 54, 8, S, 3);
      o += pad(2, 12, 144, 96);
      // 工棚
      var g = C.gableEW(4, 20, 64, 54, 24, 14, { wall: S.plaster, roof: S.thatch, back: S.thatch2, ink: I, lw: LW });
      o += g.s;
      o += C.clip(id + '-r', poly([[g.x0, g.ry], [g.x1, g.ry], [g.x1, g.ey], [g.x0, g.ey]], '#000'), C.tileRows(g.x0, g.ry, g.x1, g.ey, 3.6, S.thatch2, 0.8, r));
      o += lines([[4, 30, 64, 30], [22, 30, 22, 54], [46, 30, 46, 54], [4, 54, 22, 32], [46, 32, 64, 54]], S.dark, 1.4);
      o += rect(28, 38, 12, 16, S.dark, I, LD);
      // 鞣池：2 排 × 3 口，嵌在地面
      var cols = ['#8a5a32', '#a87a45', '#6b4f32', '#9a6a3a', '#b58b55', '#7d5530'];
      for (var i = 0; i < 6; i++) {
        var px = 10 + (i % 3) * 22, py = 64 + Math.floor(i / 3) * 15;
        o += rect(px - 1.5, py - 1.5, 21, 13, S.stone2, I, LD) + rect(px + 1, py + 1, 16, 8, cols[i], I, 0.8) +
          ln(px + 3, py + 4, px + 9, py + 4, S.paper, 0.8, 0.5);
      }
      // 晾皮架：两根立柱 + 横杆，挂四张皮
      o += C.shadow(80, 44, 140, 48, 6, S, 3);
      o += ln(80, 48, 80, 2, S.dark, 3) + ln(140, 48, 140, 2, S.dark, 3) + ln(76, 6, 144, 6, S.wood, 3.2) + ln(76, 6, 144, 6, I, 0.8, 0.6);
      o += ln(80, 30, 140, 30, S.wood, 2.2);
      [[90, 8, 16, 22, '#d9b383'], [108, 8, 15, 20, '#c69a62'], [126, 8, 16, 22, '#e2c49a'], [99, 32, 14, 14, '#b88a58'], [123, 32, 14, 13, '#d4ac7a']].forEach(function (h) {
        o += hide(h[0], h[1], h[2], h[3], h[4]);
      });
      o += lines([[80, 48, 74, 54], [140, 48, 146, 54]], S.dark, 1.6);
      // 树皮捆 + 桶
      o += barrel(84, 80) + barrel(96, 84) + C.logPile(110, 92, 4, 2, S);
      return o;
    }
  });

  // ================= 矿井口（木构井架 + 天轮 + 绞车 + 矿车轨） =================
  def({
    kind: 'mine_headframe', idKind: 'mine_head', facility: 'mine_head', variant: 1, w: 2, d: 2, up: 72,
    tags: ['headframe', 'sheave_wheel', 'winch', 'mine_cart', 'rails', 'spoil_heap'], roof: 'none',
    note: '方形木框井口上立四柱收分的木井架，顶部天轮；钢缆一头吊着罐笼，另一头斜拉到右侧绞车滚筒。井口前一段矿车轨通向前沿，轨上停一辆装满矿石的矿车，左前是废石堆。',
    draw: function (W, D, r, id) {
      var o = '';
      o += C.shadow(22, 32, 60, 58, 14, S, 3);
      o += pad(2, 14, 94, 94);
      // 废石堆
      o += C.shadowEll(14, 86, 13, 5, 6, S) + C.dome(14, 86, 13, 5, 16, S.stone3, I, LW);
      for (var k = 0; k < 9; k++) o += circ(5 + r() * 18, 76 + r() * 9, 1 + r() * 1.2, S.stone2, I, 0.6);
      // 井口木框 + 井筒
      o += poly([[22, 32], [60, 32], [60, 58], [22, 58]], S.wood, I, LW);
      o += C.planks(22, 32, 60, 58, 6.5, true, S.grain, 0.5);
      o += poly([[28, 37], [54, 37], [54, 53], [28, 53]], '#2e2418', I, LD);
      // 后柱
      o += ln(27, 35, 37, -44, S.dark, 3) + ln(55, 35, 45, -44, S.dark, 3);
      // 罐笼与吊缆
      o += ln(36, -50, 36, 30, I, 0.9);
      o += rect(31, 30, 11, 13, S.iron, I, LD) + lines([[31, 36, 42, 36], [36.5, 30, 36.5, 43]], S.paper, 0.6, 0.5);
      // 前柱 + 横撑 + 剪刀撑
      var FL = function (t) { return [24 + (35 - 24) * t, 57 + (-36 - 57) * t]; }, FR = function (t) { return [58 + (47 - 58) * t, 57 + (-36 - 57) * t]; };
      o += ln(24, 57, 35, -36, S.wood, 4) + ln(24, 57, 35, -36, I, 0.9, 0.7) + ln(58, 57, 47, -36, S.wood, 4) + ln(58, 57, 47, -36, I, 0.9, 0.7);
      [0.3, 0.62].forEach(function (t) { var a = FL(t), b = FR(t); o += ln(a[0], a[1], b[0], b[1], S.wood, 2.6) + ln(a[0], a[1], b[0], b[1], I, 0.7, 0.6); });
      [[0, 0.3], [0.3, 0.62], [0.62, 0.9]].forEach(function (p) {
        var a = FL(p[0]), b = FR(p[1]), c = FR(p[0]), d = FL(p[1]);
        o += lines([[a[0], a[1], b[0], b[1]], [c[0], c[1], d[0], d[1]]], S.dark, 1.3);
      });
      // 顶台 + 天轮
      o += C.box(33, -38, 49, -32, 4, S.wash, S.wood, I, LD);
      o += ln(38, -40, 41, -54, S.dark, 2) + ln(46, -40, 43, -54, S.dark, 2);
      o += wheel(42, -56, 10, 8, false);
      // 去绞车的斜缆
      o += ln(51, -60, 78, 26, I, 0.9);
      // 绞车：A 字支架 + 横卧滚筒 + 摇把
      o += C.shadow(68, 24, 92, 44, 6, S, 2);
      o += lines([[68, 46, 72, 22], [76, 46, 72, 22], [84, 46, 88, 22], [92, 46, 88, 22]], S.dark, 2.2);
      o += rect(70, 20, 20, 12, S.wood, I, LW) + ell(90, 26, 3, 6, S.wash, I, LD) + C.planks(70, 20, 90, 32, 3, false, S.grain, 0.6);
      o += lines([[73, 21, 73, 31], [87, 21, 87, 31]], S.iron, 1.6);
      o += ln(90, 26, 94, 34, S.iron, 1.8) + ln(94, 34, 94, 38, S.dark, 2.4);
      // 矿车轨 + 枕木
      var sl = [];
      for (var y = 61; y < 94; y += 6) sl.push([29, y, 53, y]);
      o += lines(sl, S.dark, 2.4) + lines([[33, 58, 33, 94], [49, 58, 49, 94]], S.iron, 1.8);
      // 矿车
      o += C.shadow(31, 68, 51, 84, 4, S, 2);
      o += poly([[30, 72], [52, 72], [49, 84], [33, 84]], S.iron, I, LW) + poly([[30, 72], [52, 72], [51, 67], [31, 67]], '#7a776f', I, LD);
      for (var m = 0; m < 6; m++) o += circ(33 + m * 3.2, 67 - (m % 2) * 1.6, 2.2, S.stone3, I, 0.6);
      o += lines([[32, 76, 50, 76]], '#7a776f', 0.8, 0.8);
      o += circ(35, 85, 2.6, S.dark, I, 0.8) + circ(47, 85, 2.6, S.dark, I, 0.8);
      return o;
    }
  });

  // ================= 锅炉房（砖房 + 高烟囱 + 铆钉铁锅炉，蒸汽奇幻） =================
  def({
    kind: 'boiler_steam', idKind: 'boiler_house', facility: 'boiler_house', variant: 1, w: 3, d: 2, up: 136,
    tags: ['steam_boiler', 'brick_chimney', 'riveted_iron', 'pipes', 'coal', 'steam_fantasy'], roof: 'steep_slate',
    note: '红砖机房（青石板瓦两坡顶，窗里透出炉光）、右后一座方形砖烟囱带铁箍；左边砖砌炉座上横卧一具铆钉铁锅炉，顶上黄铜汽包与安全阀冒白汽，蒸汽管弯进机房；前方炉门透火、煤堆。',
    draw: function (W, D, r, id) {
      var o = '', BR = '#c47f60';
      o += C.shadow(40, 26, 120, 64, 10, S, 3) + C.shadow(122, 14, 136, 26, 16, S, 2) + C.shadow(4, 56, 46, 82, 6, S, 3);
      o += pad(2, 10, 142, 94);
      // 烟囱（后排先画）
      o += C.box(122, 14, 136, 26, 122, S.red, BR, I, LW);
      o += C.clip(id + '-ch', rect(122, 26 - 122, 14, 122, '#000'), C.brick(122, 26 - 122, 136, 26, 5, 7, I, 0.35));
      o += poly([[124, 14 - 122 + 2], [134, 14 - 122 + 2], [134, 26 - 122 - 2], [124, 26 - 122 - 2]], '#2e2418', null, 0);
      [-20, -60].forEach(function (y) { o += rect(121, y, 16, 2.4, S.iron, I, 0.7); });
      o += C.smoke(127, -108, S, 3, 17);
      // 机房
      var g = C.gableEW(40, 26, 120, 64, 32, 18, { wall: BR, roof: S.slate, back: S.slate2, ink: I, lw: LW });
      o += g.s;
      o += C.clip(id + '-w', rect(40, 32, 80, 32, '#000'), C.brick(40, 32, 120, 64, 5, 10, I, 0.35));
      o += C.clip(id + '-r', poly([[g.x0, g.ry], [g.x1, g.ry], [g.x1, g.ey], [g.x0, g.ey]], '#000'), C.tileRows(g.x0, g.ry, g.x1, g.ey, 4, S.slate2, 0.8, r));
      o += lines([[g.x0, g.ry, g.x1, g.ry]], I, 2.2);
      // 屋顶通风气楼
      o += C.box(70, g.ry - 2, 90, g.ry + 4, 6, S.slate2, S.dark, I, LD);
      [52, 104].forEach(function (x) {
        o += path(C.archD(x, 56, 12, 9), S.glow, I, LD) + lines([[x, 43, x, 56], [x - 6, 50, x + 6, 50]], I, 0.9);
      });
      o += path(C.archD(80, 64, 16, 14), S.dark, I, LW) + ln(80, 52, 80, 64, S.grain, 0.8);
      // 炉座 + 锅炉
      o += C.box(4, 56, 46, 82, 12, S.stone3, BR, I, LW) + C.clip(id + '-s', rect(4, 70, 42, 12, '#000'), C.brick(4, 70, 46, 82, 4, 8, I, 0.4));
      o += path(C.archD(26, 82, 11, 5), S.dark, I, LD) + path(C.archD(26, 82, 7, 3), S.fire, null, 0);
      o += rect(8, 36, 36, 22, S.iron, I, LW) + ell(8, 47, 4.5, 11, '#7a776f', I, LW) + ell(8, 47, 2, 5, S.wash, I, 0.7);
      o += rect(8, 36, 36, 5, '#7a776f', null, 0, fop(0.8)) + lines([[8, 36, 44, 36]], I, LW);
      var rv = [];
      [19, 31].forEach(function (x) { rv.push([x, 36.5, x, 57.5]); });
      o += lines(rv, I, 0.8, 0.6);
      for (var x = 11; x < 44; x += 3) o += circ(x, 39.5, 0.6, S.paper, null, 0) + circ(x, 54.5, 0.6, S.paper, null, 0);
      // 黄铜汽包、安全阀、压力表
      o += C.cyl(30, 37, 5, 2, 9, S.wash, '#f0d58c', I, LD) + ell(30, 28, 3, 1.2, S.wood, I, 0.7);
      o += ln(16, 36, 16, 29, S.dark, 2) + circ(16, 28, 2, S.wash, I, 0.8);
      o += circ(14, 22, 3.5, '#f3ead2', I, 0.8, 'stroke-opacity="0.5"') + circ(11, 15, 5, '#f3ead2', I, 0.8, 'stroke-opacity="0.45"') + circ(15, 8, 4, '#f3ead2', I, 0.8, 'stroke-opacity="0.4"');
      o += circ(40, 44, 3.4, '#f3ead2', I, 0.9) + ln(40, 44, 41.6, 42.4, S.red, 0.9);
      // 蒸汽管：汽包 → 机房
      var pd = 'M30 28L30 20Q30 16 34 16L48 16Q52 16 52 20L52 30';
      o += path(pd, null, I, 4.6) + path(pd, null, S.wash, 2.8);
      o += rect(48.5, 21, 7, 2.4, S.wood, I, 0.7);
      // 阀轮
      o += circ(38, 16, 3.6, 'none', S.red, 1.4) + lines([[34.4, 16, 41.6, 16], [38, 12.4, 38, 19.6]], S.red, 0.9);
      // 煤堆 + 煤铲
      o += C.dome(64, 88, 13, 4.5, 9, '#3f3a34', I, LW);
      for (var c = 0; c < 8; c++) o += circ(54 + r() * 20, 82 + r() * 5, 0.8, '#7a776f', null, 0);
      o += ln(76, 92, 84, 78, S.dark, 1.4) + poly([[82, 76], [87, 74], [86, 79]], S.iron, I, 0.7);
      o += crate(100, 90, 11) + barrel(122, 88) + barrel(132, 84);
      return o;
    }
  });

  // ================= 结界塔（圆形法师塔 + 顶部发光符文水晶） =================
  def({
    kind: 'ward_mage_tower', idKind: 'ward_tower', facility: 'ward_tower', variant: 1, w: 2, d: 2, up: 100,
    tags: ['mage_tower', 'rune_crystal', 'glow', 'ward', 'round_tower'], roof: 'steep_slate',
    note: '毛石圆塔（三段收分、箭窗透光、拱门）、塔顶青石板尖锥被换成一圈石爪托着的悬浮符文水晶，水晶外绕两道淡金结界环；塔脚四块刻符立石围成一圈。发光只用浅金平涂与淡色圈，不用渐变或模糊。',
    draw: function (W, D, r, id) {
      var o = '', cx = 48, cy = 66;
      o += C.shadowEll(cx, cy, 22, 8, 18, S);
      o += pad(4, 24, 92, 94);
      // 结界立石（后两块先画）
      var stones = [[14, 44], [82, 44], [12, 84], [84, 84]];
      function menhir(p) {
        var x = p[0], y = p[1];
        return C.shadow(x - 3, y - 2, x + 3, y, 4, S, 2) + poly([[x - 4, y], [x - 3, y - 14], [x, y - 17], [x + 3, y - 14], [x + 4, y]], S.stone2, I, LD) +
          path('M' + f(x - 1.5) + ' ' + f(y - 10) + 'l1.5 -3l1.5 3l-1.5 3z', S.glow, I, 0.7);
      }
      o += menhir(stones[0]) + menhir(stones[1]);
      // 塔身三段
      var segs = [[22, 48], [19, 30], [16, 24]], base = cy, yy = base;
      segs.forEach(function (sg, k) {
        var rx0 = sg[0], h = sg[1], ry = rx0 * 0.36;
        o += C.cyl(cx, yy, rx0, ry, h, k % 2 ? S.stone : S.stone2, null, I, LW);
        var dd = 'M' + f(cx - rx0) + ' ' + f(yy - h) + 'L' + f(cx - rx0) + ' ' + f(yy) + 'A' + f(rx0) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + rx0) + ' ' + f(yy) + 'L' + f(cx + rx0) + ' ' + f(yy - h) + 'Z';
        o += C.clip(id + '-t' + k, path(dd, '#000'), C.rubble(cx - rx0, yy - h - 2, cx + rx0, yy + ry, r, I, 0.4) +
          rect(cx + rx0 * 0.35, yy - h - 4, rx0, h + ry + 6, S.stone3, null, 0, fop(0.7)));
        o += path(dd, null, I, LW);
        // 束带（挑出的一圈石檐）
        var ny = yy - h, nrx = rx0 + 2, nry = nrx * 0.36;
        o += path('M' + f(cx - nrx) + ' ' + f(ny) + 'A' + f(nrx) + ' ' + f(nry) + ' 0 0 0 ' + f(cx + nrx) + ' ' + f(ny) + 'L' + f(cx + nrx) + ' ' + f(ny - 3) +
          'A' + f(nrx) + ' ' + f(nry) + ' 0 0 1 ' + f(cx - nrx) + ' ' + f(ny - 3) + 'Z', S.stone3, I, LD);
        yy = ny - 3;
      });
      var topY = yy;
      // 拱门 + 箭窗（透出金光）
      o += path(C.archD(cx, base + 7, 13, 9), S.dark, I, LW) + lines([[cx, base - 7, cx, base + 7]], S.grain, 0.8);
      [[cx - 7, base - 22], [cx + 6, base - 58], [cx - 4, base - 86]].forEach(function (p) {
        o += path(C.archD(p[0], p[1], 4.5, 7), S.glow, I, 0.9);
      });
      // 塔顶平台 + 石爪
      o += ell(cx, topY, 18, 6.4, S.stone3, I, LW) + ell(cx, topY, 12, 4.2, S.stone2, I, LD);
      [-14, -6, 6, 14].forEach(function (dx, k) {
        var bx = cx + dx, by = topY + (Math.abs(dx) > 10 ? 1.5 : 3.5);
        o += path('M' + f(bx - 2) + ' ' + f(by) + 'Q' + f(bx - dx * 0.15) + ' ' + f(by - 10) + ' ' + f(cx + dx * 0.45) + ' ' + f(by - 16) + 'L' + f(cx + dx * 0.4 + 1) + ' ' + f(by - 13) +
          'Q' + f(bx + 1) + ' ' + f(by - 7) + ' ' + f(bx + 2) + ' ' + f(by) + 'Z', k % 2 ? S.stone : S.stone2, I, LD);
      });
      // 水晶：竖长八面体，左亮右暗，悬浮
      var qy = topY - 30, qh = 20;
      o += ell(cx, qy, 26, 9, 'none', S.wash, 1.6, 'stroke-opacity="0.7"') + ell(cx, qy - 2, 34, 12, 'none', S.wash, 1, 'stroke-opacity="0.45" stroke-dasharray="3 4"');
      o += circ(cx, qy, 15, S.glow, null, 0, fop(0.35));
      o += poly([[cx, qy - qh], [cx - 8, qy], [cx, qy + qh * 0.7]], '#cfe6e0', I, LW) + poly([[cx, qy - qh], [cx + 8, qy], [cx, qy + qh * 0.7]], '#8fb6b0', I, LW);
      o += lines([[cx, qy - qh, cx, qy + qh * 0.7], [cx - 8, qy, cx + 8, qy]], I, 0.8, 0.6);
      o += path('M' + f(cx - 3) + ' ' + f(qy - 8) + 'l2 -3l2 3l-2 3zM' + f(cx + 3) + ' ' + f(qy + 4) + 'l-1.5 -2.5l1.5 -2.5l1.5 2.5z', S.paper, I, 0.6);
      // 前环（压在水晶前的那半圈）
      o += path('M' + f(cx - 26) + ' ' + f(qy) + 'A26 9 0 0 0 ' + f(cx + 26) + ' ' + f(qy), null, '#d9a640', 1.8);
      [[-22, 4], [0, 9], [22, 4]].forEach(function (p) { o += circ(cx + p[0], qy + p[1], 1.6, S.paper, I, 0.6); });
      o += menhir(stones[2]) + menhir(stones[3]);
      return o;
    }
  });

  /** 麻袋：一只鼓起的袋子。 */
  function sack(x, y, s) {
    return path('M' + f(x - s * 0.5) + ' ' + f(y) + 'Q' + f(x - s * 0.62) + ' ' + f(y - s * 0.8) + ' ' + f(x - s * 0.18) + ' ' + f(y - s * 1.05) +
      'L' + f(x + s * 0.18) + ' ' + f(y - s * 1.05) + 'Q' + f(x + s * 0.62) + ' ' + f(y - s * 0.8) + ' ' + f(x + s * 0.5) + ' ' + f(y) + 'Z', S.paper, I, 1) +
      ln(x - s * 0.2, y - s * 0.95, x + s * 0.2, y - s * 0.95, S.grain, 1);
  }

  // ================= 仓库一（山墙朝街的木筋大仓 + 吊货口 + 双开大木门） =================
  def({
    kind: 'warehouse_gable_hoist', idKind: 'warehouse', facility: 'warehouse', variant: 1, w: 3, d: 2, up: 86,
    tags: ['gable_front', 'hoist_beam', 'loft_door', 'double_door', 'timber_frame'], roof: 'gable_tile',
    note: '山墙朝前（南）的三层木筋灰泥大仓：底层双开大木门（斜撑门板），二、三层正中各一扇阁楼货门，山尖挑出吊货梁挂滑轮与吊绳；门前码着木箱、麻袋。',
    draw: function (W, D, r, id) {
      var o = '', x0 = 22, x1 = 122, y0 = 14, y1 = 78, h = 64, rh = 34;
      o += C.shadow(x0, y0, x1, y1, 12, S, 3);
      o += pad(4, 8, 142, 94);
      var g = C.gableNS(x0, y0, x1, y1, h, rh, { wall: S.plaster, roofL: S.tile, roofR: '#9d563f', ink: I, lw: LW, ov: 4 });
      o += g.s;
      // 瓦行：两坡各自裁剪
      o += C.clip(id + '-rl', poly(g.L, '#000'), C.tileRows(x0 - 8, y0 - h - rh, (x0 + x1) / 2, y1 + 2 - h + 4, 4, S.red, 0.55, r));
      o += C.clip(id + '-rr', poly(g.R, '#000'), C.tileRows((x0 + x1) / 2, y0 - h - rh, x1 + 8, y1 + 2 - h + 4, 4, '#6e3626', 0.5, r));
      // 木筋：楼层梁、立柱、斜撑
      var xm = (x0 + x1) / 2, F1 = y1 - 26, F2 = y1 - 48, wy = y1 - h;
      var fr = [[x0, F1, x1, F1], [x0, F2, x1, F2], [x0 + 2, y1, x0 + 2, wy], [x1 - 2, y1, x1 - 2, wy], [x0 + 26, F1, x0 + 26, wy], [x1 - 26, F1, x1 - 26, wy],
        [x0 + 2, F1, x0 + 26, F2], [x1 - 2, F1, x1 - 26, F2], [x0 + 26, F2, x0 + 8, wy], [x1 - 26, F2, x1 - 8, wy]];
      o += lines(fr, S.dark, 2.2);
      o += lines([[x0 + 6, wy, xm, wy - rh + 6], [x1 - 6, wy, xm, wy - rh + 6]], S.dark, 2);
      // 底层大门（双开、斜撑）
      var dx0 = xm - 18, dx1 = xm + 18;
      o += rect(dx0 - 2, y1 - 25, 40, 25, S.dark, I, LW);
      o += rect(dx0, y1 - 23, 17.5, 23, S.wood, I, LD) + rect(xm + 0.5, y1 - 23, 17.5, 23, S.wood, I, LD);
      o += C.planks(dx0, y1 - 23, dx1, y1, 4.4, true, S.grain, 0.55) + lines([[dx0, y1 - 2, xm, y1 - 21], [dx1, y1 - 2, xm, y1 - 21]], S.dark, 1.3);
      o += circ(xm - 2.5, y1 - 11, 1.2, S.iron, null, 0) + circ(xm + 2.5, y1 - 11, 1.2, S.iron, null, 0);
      // 侧边小窗
      [x0 + 12, x1 - 12].forEach(function (x) { o += rect(x - 4, y1 - 20, 8, 9, S.dark, I, LD) + ln(x, y1 - 20, x, y1 - 11, S.wood, 1); });
      // 阁楼货门两层
      o += rect(xm - 8, F1 - 20, 16, 19, S.wood, I, LD) + C.planks(xm - 8, F1 - 20, xm + 8, F1 - 1, 4, true, S.grain, 0.5);
      o += rect(xm - 7, F2 - 16, 14, 14, S.dark, I, LD) + rect(xm - 5, F2 - 9, 10, 7, S.wash, I, 0.7);
      // 吊货梁 + 滑轮 + 吊绳 + 货箱
      var by = wy - rh + 14;
      o += C.box(xm - 3, by - 3, xm + 3, by + 3, 4, S.wood, S.dark, I, LD);
      o += lines([[xm, by - 1, xm, by + 16]], S.dark, 3) ;
      o += rect(xm - 3, by - 6, 6, 4, S.dark, I, 0.7) + circ(xm, by + 14, 3, S.wood, I, 0.9) + circ(xm, by + 14, 1, S.dark, null, 0);
      o += ln(xm - 2, by + 15, xm - 2, F1 - 30, I, 0.9) + ln(xm + 2.6, by + 15, xm + 10, F1 - 8, I, 0.8, 0.7);
      o += crate(xm - 7, F1 - 22, 10);
      // 门前货物
      o += crate(6, 90, 12) + crate(16, 84, 10) + sack(30, 92, 9) + sack(38, 90, 8) + barrel(128, 92) + barrel(137, 86) + crate(110, 92, 10);
      return o;
    }
  });

  // ================= 仓库二（石砌长仓 + 屋面吊货老虎窗 + 装卸台） =================
  def({
    kind: 'warehouse_stone_dock', idKind: 'warehouse', facility: 'warehouse', variant: 2, w: 3, d: 2, up: 66,
    tags: ['stone_wall', 'hoist_dormer', 'loading_platform', 'double_door', 'sacks'], roof: 'steep_slate',
    note: '毛石砌的长条仓库，青石板陡坡顶，屋面正中开一个吊货老虎窗（挑出吊臂与滑轮）；两扇拱形大木门，门前一段木装卸台高出地面，台上麻袋、木箱，一架手推车。',
    draw: function (W, D, r, id) {
      var o = '', x0 = 8, x1 = 138, y0 = 18, y1 = 66, h = 30, rh = 26;
      o += C.shadow(x0, y0, x1, y1, 10, S, 3);
      o += pad(2, 10, 144, 94);
      var g = C.gableEW(x0, y0, x1, y1, h, rh, { wall: S.stone2, roof: S.slate, back: S.slate2, ink: I, lw: LW, ov: 3 });
      o += g.s;
      o += C.clip(id + '-w', rect(x0, y1 - h, x1 - x0, h, '#000'), C.rubble(x0, y1 - h, x1, y1, r, I, 0.45));
      o += C.clip(id + '-r', poly([[g.x0, g.ry], [g.x1, g.ry], [g.x1, g.ey], [g.x0, g.ey]], '#000'), C.tileRows(g.x0, g.ry, g.x1, g.ey, 4, S.slate2, 0.75, r));
      o += lines([[g.x0, g.ry, g.x1, g.ry]], I, 2.2);
      // 墙角隅石
      [x0, x1 - 7].forEach(function (x) { for (var k = 0; k < 5; k++) o += rect(x + (k % 2 ? 0 : 1), y1 - 6 - k * 6, k % 2 ? 7 : 5, 6, S.stone, I, 0.7); });
      // 老虎窗：小山墙 + 货门 + 吊臂
      var dxm = 73, dy = g.ey - 2;
      o += poly([[dxm - 12, dy], [dxm - 12, dy - 16], [dxm, dy - 26], [dxm + 12, dy - 16], [dxm + 12, dy]], S.plaster, I, LW);
      o += poly([[dxm - 15, dy - 14], [dxm, dy - 28], [dxm, dy - 24], [dxm - 13, dy - 12]], S.slate, I, LD) + poly([[dxm + 15, dy - 14], [dxm, dy - 28], [dxm, dy - 24], [dxm + 13, dy - 12]], S.slate2, I, LD);
      o += rect(dxm - 6, dy - 15, 12, 15, S.dark, I, LD);
      o += ln(dxm, dy - 26, dxm, dy - 36, S.dark, 2.6) + ln(dxm, dy - 36, dxm + 2, dy - 36, S.dark, 2.6) + circ(dxm, dy - 33, 2.2, S.wood, I, 0.7);
      o += ln(dxm + 1.8, dy - 33, dxm + 1.8, y1 + 6, I, 0.8) + sack(dxm + 2, dy + 14, 8);
      // 拱形大门两扇
      [36, 110].forEach(function (x) {
        o += path(C.archD(x, y1, 22, 12), S.stone, I, LW) + path(C.archD(x, y1, 17, 10), S.wood, I, LD);
        o += C.clip(id + '-d' + x, path(C.archD(x, y1, 17, 10), '#000'), C.planks(x - 9, y1 - 20, x + 9, y1, 4.2, true, S.grain, 0.55));
        o += lines([[x - 8.5, y1 - 7, x + 8.5, y1 - 7], [x - 8.5, y1 - 14, x + 8.5, y1 - 14]], S.iron, 1.2);
      });
      // 装卸台
      o += C.shadow(20, 66, 126, 78, 4, S, 2);
      o += C.box(20, 66, 126, 78, 6, S.wood, S.grain, I, LW) + C.planks(20, 60, 126, 72, 4, false, S.grain, 0.45);
      [26, 50, 96, 120].forEach(function (x) { o += ln(x, 72, x, 78, S.dark, 1.6); });
      o += sack(48, 70, 9) + sack(56, 71, 8) + sack(52, 64, 8) + crate(88, 72, 11) + crate(98, 70, 9);
      // 手推车
      o += poly([[128, 80], [142, 78], [143, 86], [130, 88]], S.wood, I, LD) + circ(133, 89, 3.4, S.dark, I, 0.8) + ln(130, 82, 124, 90, S.dark, 1.4);
      return o;
    }
  });

  // ================= 墓地（铁栅 + 十字墓碑 + 小停尸房 + 紫杉） =================
  function cross(x, y, s, col) {
    return C.shadow(x - 1, y - 2, x + 1, y, 3, S, 2) +
      poly([[x - 1.6 * s, y], [x - 1.6 * s, y - 6 * s], [x - 4 * s, y - 6 * s], [x - 4 * s, y - 9 * s], [x - 1.6 * s, y - 9 * s], [x - 1.6 * s, y - 12 * s],
        [x + 1.6 * s, y - 12 * s], [x + 1.6 * s, y - 9 * s], [x + 4 * s, y - 9 * s], [x + 4 * s, y - 6 * s], [x + 1.6 * s, y - 6 * s], [x + 1.6 * s, y]], col || S.stone2, I, 1);
  }
  function slab(x, y, col) {
    return C.shadow(x - 4, y - 2, x + 4, y, 3, S, 2) + path('M' + f(x - 4) + ' ' + f(y) + 'L' + f(x - 4) + ' ' + f(y - 7) + 'A4 4 0 0 1 ' + f(x + 4) + ' ' + f(y - 7) + 'L' + f(x + 4) + ' ' + f(y) + 'Z', col || S.stone, I, 1) +
      ln(x - 2, y - 6, x + 2, y - 6, I, 0.6, 0.5);
  }
  function fence(x0, y, x1, h) {
    var s = [];
    for (var x = x0; x <= x1 + 0.1; x += 4) s.push([x, y, x, y - h]);
    return lines(s, '#3f3a34', 1.1) + lines([[x0, y - h + 2, x1, y - h + 2], [x0, y - 2, x1, y - 2]], '#3f3a34', 1.2) +
      lines(s.map(function (q) { return [q[0], q[3] - 1.8, q[0], q[3]]; }), '#3f3a34', 2);
  }
  def({
    kind: 'cemetery_churchyard', idKind: 'cemetery', facility: 'cemetery', variant: 1, w: 3, d: 2, up: 54,
    tags: ['iron_fence', 'cross_graves', 'mortuary_chapel', 'yew', 'gate'], roof: 'steep_slate',
    note: '铁栅围起的墓园：右后一间毛石小停尸房（山墙朝前、青石板陡顶、山尖立十字），园中三排十字碑与圆头碑、几处新坟土堆，左后一棵紫杉，前沿正中铁门。roof 记停尸房的屋顶。',
    draw: function (W, D, r, id) {
      var o = '';
      o += poly([[4, 8], [142, 8], [142, 92], [4, 92]], '#b9b98a', null, 0, fop(0.6));
      // 后栅
      o += fence(4, 10, 142, 11);
      // 紫杉（左后）
      o += C.shadowEll(22, 32, 12, 4, 10, S) + ln(22, 32, 22, 22, S.dark, 3);
      o += path('M22 -26C10 -14 6 6 10 26Q22 32 34 26C38 6 34 -14 22 -26Z', '#6f7a52', I, LW) +
        path('M22 -20C14 -10 12 6 14 22Q18 25 22 25Z', '#879166', null, 0) + lines([[16, 4, 21, -2], [26, 12, 31, 6], [15, 18, 20, 13]], I, 0.7, 0.5);
      // 停尸房（右后）
      var x0 = 96, x1 = 136, y0 = 14, y1 = 44;
      o += C.shadow(x0, y0, x1, y1, 8, S, 3);
      var g = C.gableNS(x0, y0, x1, y1, 22, 18, { wall: S.stone, roofL: S.slate, roofR: S.slate2, ink: I, lw: LW, ov: 3 });
      o += g.s + C.clip(id + '-w', rect(x0, y1 - 22, x1 - x0, 22, '#000'), C.rubble(x0, y1 - 40, x1, y1, r, I, 0.4));
      o += path(C.archD(116, y1, 10, 9), S.red, I, LD) + path(C.archD(116, y1 - 24, 5, 4), S.dark, I, 0.8);
      o += lines([[116, g.apex[1] - 1, 116, g.apex[1] - 12], [112, g.apex[1] - 8, 120, g.apex[1] - 8]], S.dark, 2);
      // 墓碑三排（后排先画）
      var rows = [[30, [44, 60, 76]], [52, [34, 52, 70, 88, 104, 122]], [72, [22, 40, 58, 92, 110, 128]]];
      rows.forEach(function (rw, k) {
        rw[1].forEach(function (x, i) {
          var t = (i + k) % 3, xx = x + (r() - 0.5) * 3;
          if (k > 0 && i % 2) o += C.dome(xx, rw[0] + 6, 6, 2.4, 3.5, S.stone3, I, 0.8);
          o += t === 0 ? cross(xx, rw[0], 1, S.stone2) : t === 1 ? slab(xx, rw[0], S.stone) : cross(xx, rw[0], 0.8, S.wood);
        });
      });
      // 侧栅（短截）+ 前栅 + 铁门
      o += lines([[4, 10, 4, 92], [142, 10, 142, 92]], '#3f3a34', 1.4);
      o += fence(4, 94, 62, 12) + fence(84, 94, 142, 12);
      o += rect(61, 78, 3.5, 16, S.stone2, I, LD) + rect(82.5, 78, 3.5, 16, S.stone2, I, LD);
      o += path('M64 92L64 84Q73 78 82 84L82 92', null, '#3f3a34', 1.4) + lines([[68, 92, 68, 82], [73, 92, 73, 80.5], [78, 92, 78, 82]], '#3f3a34', 1.1);
      return o;
    }
  });

  // ================= 桥（两座：石拱桥东西向、木栈桥南北向） =================
  /** 东西向拱桥：桥面东西走、跨南北流的河，正面看到拱券。W 宽、D 进深。 */
  function archBridge(W, D, id, pal) {
    var o = '', N = 24, Fy = D - 8, By = 12, crown = 30;
    function h(x) { return 8 + crown * Math.pow(Math.sin(Math.PI * x / W), 0.8); }
    function curve(y0, dy, rev) {
      var a = [];
      for (var i = 0; i <= N; i++) { var x = W * i / N; a.push([x, y0 - h(x) + dy]); }
      return rev ? a.reverse() : a;
    }
    o += poly([[W * 0.3, D - 2], [W * 0.75, D - 2], [W * 0.7, D + 4], [W * 0.35, D + 4]], S.shadow, null, 0, fop(S.sop));
    // 后栏
    o += poly(curve(By, -6).concat(curve(By, 0, true)), pal.side, I, LW);
    // 桥面
    var deck = curve(By, 0).concat(curve(Fy, 0, true));
    o += poly(deck, pal.top, I, LW);
    var s = [];
    for (var i = 1; i < 12; i++) { var x = W * i / 12; s.push([x, By - h(x), x, Fy - h(x)]); }
    o += lines(s, I, 0.8, 0.4);
    // 正面（拱券挖空）：半径 R，拱脚在 D
    var R = W * 0.22, cx = W / 2, top = curve(Fy, -6);
    var fd = 'M0 ' + f(D) + top.map(function (p) { return 'L' + f(p[0]) + ' ' + f(p[1]); }).join('') + 'L' + f(W) + ' ' + f(D) + 'L' + f(cx + R) + ' ' + f(D) +
      'A' + f(R) + ' ' + f(R * 0.95) + ' 0 0 0 ' + f(cx - R) + ' ' + f(D) + 'Z';
    var arch = 'M' + f(cx - R) + ' ' + f(D) + 'A' + f(R) + ' ' + f(R * 0.95) + ' 0 0 1 ' + f(cx + R) + ' ' + f(D) + 'Z';
    o += path(arch, pal.water, null, 0) + C.clip(id + '-a', path(arch, '#000'),
      path('M' + f(cx - R) + ' ' + f(D - R * 0.95 - 2) + 'L' + f(cx + R) + ' ' + f(D - R * 0.95 - 2) + 'L' + f(cx + R) + ' ' + f(D - R * 0.45) + 'L' + f(cx - R) + ' ' + f(D - R * 0.45) + 'Z', pal.dark, null, 0, fop(0.75)) +
      lines([[cx - R * 0.6, D - 5, cx - R * 0.1, D - 5], [cx + R * 0.1, D - 9, cx + R * 0.5, D - 9]], pal.wline, 0.9, 0.8));
    o += path(fd, pal.side, I, LW);
    o += C.clip(id + '-f', path(fd, '#000'), pal.west ? C.rubble(0, -40, W, D, C.rng(9), I, 0.4) : C.brick(0, -40, W, D, 4.5, 12, pal.joint, 0.5));
    // 拱券石（放射状券石线）
    var vs = [];
    for (var k = 0; k <= 12; k++) {
      var a = Math.PI * k / 12, c = Math.cos(a), sn = Math.sin(a);
      vs.push([cx - c * R, D - sn * R * 0.95, cx - c * (R + 7), D - sn * (R * 0.95 + 7)]);
    }
    o += lines(vs, I, 0.9, 0.7) + path('M' + f(cx - R - 7) + ' ' + f(D) + 'A' + f(R + 7) + ' ' + f(R * 0.95 + 7) + ' 0 0 1 ' + f(cx + R + 7) + ' ' + f(D), null, I, 1.1);
    o += path(fd, null, I, LW);
    // 栏顶压条
    o += pl(top, I, 1.2) + pl(curve(Fy, -4.5), pal.cap, 1.6);
    return o;
  }
  def({
    kind: 'bridge_stone_arch', idKind: 'bridge', facility: 'bridge', variant: 1, w: 3, d: 1, up: 40,
    tags: ['stone_arch', 'deck_ew', 'river_ns', 'span_1'], roof: 'none',
    note: '单孔毛石拱桥。桥面东西走向、跨南北流向的河：放在河道瓦片上时，中间一格是水、东西两端搭在两岸。正面（南）看到拱券与券石；拱洞里画了一点水色。',
    draw: function (W, D, r, id) {
      return archBridge(W, D, id, { west: true, top: S.stone, side: S.stone2, water: S.water, dark: S.water2, wline: '#f3ead2', cap: S.stone3, joint: I });
    }
  });
  def({
    kind: 'bridge_timber_trestle', idKind: 'bridge', facility: 'bridge', variant: 2, w: 1, d: 3, up: 18,
    tags: ['timber', 'trestle', 'deck_ns', 'river_ew', 'railing'], roof: 'none',
    note: '木栈桥。桥面南北走向、跨东西流向的河：放在河道瓦片上时，中间一格是水、南北两端落在两岸。斜俯视下只看得到桥面与左侧一窄条桥身，桥墩木桩露在中间一格的水里。',
    draw: function (W, D, r, id) {
      var o = '', x0 = 12, x1 = 38, lift = 13;
      // 中段（南北第二格，水面）抬高 lift，两端各用约 0.7 格的坡道落到岸上
      function hy(y) { return y >= 44 && y <= 100 ? lift : y < 44 ? lift * Math.max(0, (y - 10) / 34) : lift * Math.max(0, (134 - y) / 34); }
      o += poly([[x1, 44 - lift], [x1 + 9, 48 - lift], [x1 + 9, 104], [x1, 100]], S.shadow, null, 0, fop(S.sop));
      // 左侧桥身：栈架侧面（立桩 + 剪刀撑），中段露出到水面
      var side = [], bot = [];
      for (var y0 = 0; y0 <= D; y0 += 4) { side.push([x0, y0 - hy(y0)]); bot.push([x0 - 5, Math.min(D, y0 - hy(y0) + 3)]); }
      o += poly(side.concat(bot.reverse()), S.dark, I, LD);
      var bents = [];
      for (var yb = 48; yb <= 96; yb += 12) bents.push([x0 - 2.5, yb - lift + 2, x0 - 2.5, yb + 5]);
      o += lines(bents, S.dark, 3.2) + lines(bents, I, 0.8, 0.6);
      var xb = [];
      for (var yc = 48; yc < 96; yc += 12) xb.push([x0 - 2.5, yc - lift + 4, x0 - 1, yc + 12 + 3], [x0 - 2.5, yc + 4, x0 - 1, yc + 12 - lift + 4]);
      o += lines(xb, S.grain, 1.1, 0.9);
      for (var yr = 48; yr <= 96; yr += 12) o += ell(x0 - 2.5, yr + 5.5, 4, 1.3, 'none', '#f3ead2', 0.9);
      // 桥面（两端坡道，中段抬高）
      var L = [], R = [];
      for (var y = 0; y <= D; y += 4) { L.push([x0, y - hy(y)]); R.push([x1, y - hy(y)]); }
      o += poly(L.concat(R.reverse()), S.wood, I, LW);
      // 桥面前端（南端）露出的一截厚度
      o += poly([[x0, D], [x1, D], [x1, D - 2.5], [x0, D - 2.5]], S.grain, I, LD);
      var s = [];
      for (var yy = 4; yy < D; yy += 4.5) s.push([x0 + 0.5, yy - hy(yy), x1 - 0.5, yy - hy(yy)]);
      o += lines(s, S.grain, 0.8, 0.55);
      // 栏杆：立柱 + 扶手
      [x0 + 1.5, x1 - 1.5].forEach(function (x) {
        var posts = [], rail = [];
        for (var y = 6; y <= D - 4; y += 12) { posts.push([x, y - hy(y), x, y - hy(y) - 10]); rail.push([x, y - hy(y) - 10]); }
        o += lines(posts, S.dark, 2) + pl(rail, S.wood, 2.4) + pl(rail, I, 0.8, 'stroke-opacity="0.6"');
      });
      return o;
    }
  });

  var api = { defs: defs, style: S };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.TownArtInfraWest = api;
})(typeof window !== 'undefined' ? window : this);
