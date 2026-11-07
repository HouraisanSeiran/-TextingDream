/*
 * 织梦 · 东方工业与基础设施（国潮平涂 + 金线勾边，3/4 斜俯视，尚未接入游戏）
 *
 * 定义格式与 west-infra.js 相同：{ kind, idKind, facility, variant, w, d, up, tags, roof, note, draw(W, D, r, id) }
 * draw 在“地面坐标”里画：占地 x∈[0,W]、y∈[0,D]，y=D 是前沿；高度画成负 y。
 *
 * 浏览器挂 window.TownArtInfraEast；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./infra-core.js') : root.TownArtInfraCore;
  var S = C.EAST, f = C.f, poly = C.poly, pl = C.pl, path = C.path, rect = C.rect, ell = C.ell, circ = C.circ;
  var ln = C.ln, lines = C.lines, fop = C.fop;
  var G = S.ink, G2 = S.ink2, LW = S.lw, LD = S.lwd;
  var defs = [];
  function def(o) { o.style = 'east'; defs.push(o); }

  /** 场地：夯土 / 青石铺地（只在占地内）。 */
  function pad(x0, y0, x1, y1, col) { return poly([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], col || S.stone, null, 0, fop(0.55)); }

  /**
   * 东方坡屋顶（屋脊东西向，看到前坡）：x0..x1 墙宽，ry 屋脊，ey 檐口，ov 出檐，lift 檐角起翘。
   * by（可选）< ry 时在屋脊后画一窄条后坡。返回 SVG 字符串。
   */
  function eaveRoof(id, x0, x1, ry, ey, ov, fill, lite, lift, by) {
    var L = x0 - ov, R = x1 + ov, k = lift == null ? 5 : lift;
    var o = '';
    if (by != null && by < ry) o += poly([[L + 6, by], [R - 6, by], [R - 3, ry], [L + 3, ry]], S.gray, G, LD);
    var d = 'M' + f(L + 3) + ' ' + f(ry) + 'L' + f(R - 3) + ' ' + f(ry) +
      'L' + f(R) + ' ' + f(ey - k) + 'Q' + f(R - 5) + ' ' + f(ey) + ' ' + f(R - 13) + ' ' + f(ey) +
      'L' + f(L + 13) + ' ' + f(ey) + 'Q' + f(L + 5) + ' ' + f(ey) + ' ' + f(L) + ' ' + f(ey - k) + 'Z';
    o += path(d, fill, G, LW);
    o += C.clip(id, path(d, '#000'), C.tileRidges(L, ry, R, ey + 1, 4.5, lite, 0.85));
    // 檐口一道瓦当线
    o += path('M' + f(L + 1.5) + ' ' + f(ey - k + 0.5) + 'Q' + f(L + 5) + ' ' + f(ey - 1.6) + ' ' + f(L + 13) + ' ' + f(ey - 1.6) +
      'L' + f(R - 13) + ' ' + f(ey - 1.6) + 'Q' + f(R - 5) + ' ' + f(ey - 1.6) + ' ' + f(R - 1.5) + ' ' + f(ey - k + 0.5), null, G2, 1.3);
    // 屋脊与两端翘起的脊吻
    var rd = 'M' + f(L + 1) + ' ' + f(ry - 5) + 'Q' + f(L + 4) + ' ' + f(ry) + ' ' + f(L + 10) + ' ' + f(ry) +
      'L' + f(R - 10) + ' ' + f(ry) + 'Q' + f(R - 4) + ' ' + f(ry) + ' ' + f(R - 1) + ' ' + f(ry - 5);
    o += path(rd, null, G, 4.2) + path(rd, null, S.navy, 2.2);
    return o;
  }
  /** 朱红圆柱（立面上的竖柱）。 */
  function pillar(x, yTop, yBot, w) {
    w = w || 3.4;
    return rect(x - w / 2, yTop, w, yBot - yTop, S.vermil, G, 1) + rect(x - w / 2 - 1, yBot - 2, w + 2, 2, S.stone2, G, 0.8);
  }
  /** 叠晕：同一多边形缩一圈填浅色。 */
  function band(a, col) { return poly(a, col, null, 0); }

  // ================= 冶炉（土高炉 + 木风箱棚 + 炭堆） =================
  def({
    kind: 'smelter_earthen', idKind: 'smelter', facility: 'smelter', variant: 1, w: 3, d: 2, up: 100,
    tags: ['earthen_furnace', 'bellows_shed', 'charcoal', 'smoke'], roof: 'gable_tile',
    note: '夯土高炉（上收下放、竹篾箍、炉口吐火）、右侧灰瓦风箱棚里一具推拉木风箱用陶管通进炉腹、前方出铁口接砂模铁锭、左前炭堆与矿石筐。',
    draw: function (W, D, r, id) {
      var o = '';
      o += C.shadowEll(51, 62, 23, 8, 16, S) + C.shadow(86, 26, 140, 72, 6, S, 3);
      o += pad(4, 16, 142, 94);
      // —— 风箱棚（后段先画：后坡、背墙下部、风箱） ——
      var sx0 = 88, sx1 = 140, sy0 = 28, sy1 = 72, sh = 30;
      o += rect(sx0, sy0 - sh + 8, sx1 - sx0, sh - 8 + (sy1 - sy0) - 26, S.cream, G, LD);       // 棚内背墙（被屋顶挡掉上半）
      o += C.planks(sx0, sy0 - sh + 8, sx1, sy0 + 18, 6, true, S.stone2, 0.6);
      // 风箱：长方木箱，左端伸出推拉杆
      var bx0 = 100, bx1 = 130, by0 = 50, by1 = 62, bh = 15;
      o += C.box(bx0, by0, bx1, by1, bh, S.umber2, S.umber, G, LD);
      o += rect(bx0 + 3, by1 - bh + 3, bx1 - bx0 - 6, bh - 6, 'none', G2, 0.9);
      o += ln(bx0, by1 - bh * 0.55, bx0 - 12, by1 - bh * 0.55, S.umber, 2.4) + ln(bx0 - 12, by1 - bh * 0.55 - 5, bx0 - 12, by1 - bh * 0.55 + 5, S.umber, 2.8);
      // 陶风管：风箱 → 炉腹
      o += path('M' + f(bx0 + 4) + ' ' + f(by0 - bh + 6) + 'Q86 ' + f(by0 - 18) + ' 70 40', null, G, 5.2) +
        path('M' + f(bx0 + 4) + ' ' + f(by0 - bh + 6) + 'Q86 ' + f(by0 - 18) + ' 70 40', null, S.umber2, 3.2);
      // 棚柱 + 屋顶
      o += pillar(sx0 + 2, sy1 - sh - 2, sy1) + pillar(sx1 - 2, sy1 - sh - 2, sy1);
      o += eaveRoof(id + '-r1', sx0, sx1, (sy0 + sy1) / 2 - sh - 12, sy1 - sh + 4, 4, S.gray, S.gray2, 5, sy0 - sh);
      // —— 土高炉：圆台 ——
      var cx = 51, cy = 60, H = 80;
      o += C.frustum(cx, cy, 23, 8, 13, 5, H, S.umber2, null, G, LW);
      // 受光的左侧叠晕
      o += C.clip(id + '-k', path('M' + f(cx - 23) + ' ' + f(cy) + 'L' + f(cx - 13) + ' ' + f(cy - H) + 'L' + f(cx + 13) + ' ' + f(cy - H) + 'L' + f(cx + 23) + ' ' + f(cy) + 'Z', '#000'),
        poly([[cx - 26, cy + 9], [cx - 15, cy - H], [cx - 4, cy - H], [cx - 9, cy + 9]], '#c97a4c', null, 0));
      // 竹篾箍
      [0.18, 0.42, 0.66, 0.88].forEach(function (k) {
        var y = cy - H * k, rx = 23 - 10 * k, ry = 8 - 3 * k;
        o += path('M' + f(cx - rx) + ' ' + f(y) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + rx) + ' ' + f(y), null, G2, 1.8);
      });
      // 炉口：火与烟
      o += ell(cx, cy - H, 13, 5, S.umber, G, LW) + ell(cx, cy - H + 0.6, 9, 3, S.orange, null, 0);
      o += path('M' + f(cx - 7) + ' ' + f(cy - H - 1) + 'q1 -10 6 -15q-1 7 3 9q2 -6 5 -8q1 8 -3 14z', S.ochre, G, 1);
      o += C.smoke(cx - 2, cy - H - 20, S, 4, 5);
      // 出铁口 + 流槽 + 砂模铁锭
      o += path(C.archD(cx, cy + 7, 12, 5), S.navy, G2, 1.2) + path(C.archD(cx, cy + 7, 7, 2.5), S.orange, null, 0);
      o += poly([[cx - 3, cy + 7], [cx + 3, cy + 7], [cx + 5, 80], [cx - 1, 80]], S.umber, G, LD);
      o += rect(cx - 16, 80, 40, 10, S.stone2, G, LD);
      for (var i = 0; i < 4; i++) o += rect(cx - 13 + i * 9.5, 82.5, 7, 3.4, i === 0 ? S.orange : S.gray, G2, 0.7);
      // 炭堆（左前）+ 矿石筐
      o += C.dome(16, 86, 14, 5, 13, S.navy, G, LW);
      for (var j = 0; j < 7; j++) o += circ(8 + r() * 16, 80 - r() * 8, 0.9, G2, null, 0);
      o += C.frustum(30, 90, 6, 2.4, 7.5, 3, 9, S.ochre, S.stone2, G, LD) +
        lines([[23, 85, 37, 85], [23.5, 88, 36.5, 88]], S.umber, 0.8, 0.8);
      o += circ(28, 81, 2, S.gray2, G, 0.7) + circ(32, 80.5, 1.8, S.gray, G, 0.7);
      return o;
    }
  });

  /** 乌篷船：船身侧面朝前，中间一段竹篷（藏青半筒），cx 船中，wy 水线，L 半长。 */
  function wupeng(cx, wy, L, flip) {
    var s = flip ? -1 : 1, o = '';
    o += ell(cx + 4, wy + 2, L + 2, 3, S.shadow, null, 0, fop(S.sop));
    // 船身：两头上翘
    var hull = 'M' + f(cx - L * s) + ' ' + f(wy - 9) + 'Q' + f(cx - L * 0.7 * s) + ' ' + f(wy + 1) + ' ' + f(cx - L * 0.35 * s) + ' ' + f(wy + 1) +
      'L' + f(cx + L * 0.4 * s) + ' ' + f(wy + 1) + 'Q' + f(cx + L * 0.8 * s) + ' ' + f(wy + 1) + ' ' + f(cx + L * s) + ' ' + f(wy - 7) +
      'L' + f(cx + L * 0.8 * s) + ' ' + f(wy - 5) + 'L' + f(cx - L * 0.8 * s) + ' ' + f(wy - 5) + 'Z';
    o += path(hull, S.navy, G2, 1.3);
    o += path('M' + f(cx - L * 0.85 * s) + ' ' + f(wy - 6.5) + 'L' + f(cx + L * 0.82 * s) + ' ' + f(wy - 6), null, S.vermil, 1.4);
    // 船舷内侧（俯视看到一窄条甲板）
    o += poly([[cx - L * 0.8 * s, wy - 5], [cx + L * 0.8 * s, wy - 5], [cx + L * 0.7 * s, wy - 8], [cx - L * 0.7 * s, wy - 8]], S.umber2, G, 0.8);
    // 竹篷：两段半筒
    [[-0.32, 0.12], [0.16, 0.5]].forEach(function (seg, k) {
      var a = cx + seg[0] * L * s, b = cx + seg[1] * L * s, x0 = Math.min(a, b), x1 = Math.max(a, b);
      var d = 'M' + f(x0) + ' ' + f(wy - 6) + 'L' + f(x0) + ' ' + f(wy - 11) + 'Q' + f((x0 + x1) / 2) + ' ' + f(wy - 20 + k * 2) + ' ' + f(x1) + ' ' + f(wy - 11) +
        'L' + f(x1) + ' ' + f(wy - 6) + 'Z';
      o += path(d, k ? S.navy2 : S.navy, G2, 1.1);
      for (var x = x0 + 3; x < x1 - 1; x += 3.2) o += ln(x, wy - 7, x, wy - 13 - (1 - Math.abs((x - (x0 + x1) / 2) / ((x1 - x0) / 2))) * 4, G, 0.7, 0.8);
    });
    // 船尾橹
    o += ln(cx + L * 0.9 * s, wy - 8, cx + (L + 9) * s, wy + 3, S.umber, 1.8);
    return o;
  }
  function stoneBollard(x, y) { return C.cyl(x, y, 2.8, 1.5, 7, S.stone2, S.stone, G, 1); }

  // ================= 码头（石阶埠头 + 乌篷船） =================
  def({
    kind: 'dock_steps', idKind: 'dock', facility: 'dock', variant: 1, w: 3, d: 2, up: 30,
    tags: ['waterside_south', 'stone_steps', 'wupeng_boat', 'bollard'], roof: 'none',
    note: '临水边朝南：后部约 0.7 格是青石驳岸与埠头平台，中间一段石阶一级级下到水面，两旁系船石桩，前部是水面泊两条乌篷船。放置时地块前沿（南）贴河道，后沿接街巷。',
    draw: function (W, D, r, id) {
      var o = '';
      o += C.water(0, 40, W, D, S, 31);
      // 驳岸平台（青石板）
      o += rect(0, 0, W, 30, S.stone, null, 0);
      var s = [];
      for (var x = 12; x < W; x += 16) s.push([x, 0, x, 30]);
      s.push([0, 15, W, 15]);
      o += lines(s, S.stone2, 0.9, 0.9);
      // 驳岸正面（条石砌）
      o += rect(0, 30, W, 12, S.stone2, G, LW) + C.brick(0, 30, W, 42, 4, 14, S.umber, 0.45);
      o += rect(0, 42, W, 2.5, S.navy, null, 0, fop(0.35));
      // 石阶：从平台切进驳岸一级级下到水
      var x0 = 52, x1 = 94, n = 5;
      o += poly([[x0, 20], [x1, 20], [x1, 30], [x0, 30]], S.stone2, null, 0);
      for (var i = 0; i < n; i++) {
        var yt = 20 + i * 5.2, yf = yt + 3;
        o += rect(x0, yt, x1 - x0, 3, S.cream, G, LD) + rect(x0, yf, x1 - x0, 2.6, S.stone2, G, 0.8);
      }
      o += rect(x0 - 4, 18, 4, 28, S.stone, G, LD) + rect(x1, 18, 4, 28, S.stone, G, LD);
      o += ell((x0 + x1) / 2, 47, 24, 2, 'none', S.cream2, 1, 'stroke-opacity="0.8"');
      // 系船石桩 + 缆绳
      o += stoneBollard(20, 28) + stoneBollard(126, 28);
      // 乌篷船两条（一条靠阶，一条稍远）
      o += wupeng(118, 72, 24, false);
      o += path('M126 22Q136 50 128 64', null, S.umber, 0.9);
      o += wupeng(30, 86, 21, true);
      o += path('M20 22Q14 60 24 78', null, S.umber, 0.9);
      // 平台上的货物：竹篓、酒坛
      [[12, 14], [22, 10], [118, 12]].forEach(function (p, k) {
        o += C.frustum(p[0], p[1], 5, 2.2, 6, 2.6, 9, k === 2 ? S.umber2 : S.ochre, S.stone2, G, LD) +
          (k === 2 ? '' : lines([[p[0] - 5.4, p[1] - 3, p[0] + 5.4, p[1] - 3], [p[0] - 5.7, p[1] - 6, p[0] + 5.7, p[1] - 6]], S.umber, 0.8, 0.8));
      });
      o += C.cyl(132, 16, 4, 2, 8, S.umber, S.umber2, G, LD) + rect(130, 6, 4, 3, S.vermil, G, 0.8);
      // 埠头小旗杆 + 幌子
      o += ln(104, 18, 104, -22, S.umber, 2.2) + poly([[104, -20], [114, -18], [114, 0], [104, -2]], S.vermil, G, 1) +
        rect(106, -15, 6, 10, 'none', G2, 0.8);
      return o;
    }
  });

  // ================= 龙窑（依坡长条窑 + 窑头火膛 + 投柴孔 + 窑尾烟囱） =================
  def({
    kind: 'kiln_dragon', idKind: 'kiln', facility: 'kiln', variant: 1, w: 3, d: 2, up: 56,
    tags: ['dragon_kiln', 'slope', 'firing_holes', 'woodpile', 'smoke', 'slope_rises_east'], roof: 'none',
    note: '龙窑：依坡砌的长条拱顶窑，窑头在西（左）低处、窑尾在东（右）高处，中段最高最宽。窑头砖砌火膛朝南开火口，窑身分节（目），节上一排投柴孔，前侧两道窑门，窑尾一截矮烟囱。放置时让地块东侧接山坡或高地更自然。',
    draw: function (W, D, r, id) {
      var o = '', N = 30, xa = 22, xb = 134;
      function g(x) { return Math.max(0, (x - 8) * 0.25); }
      function vh(x) { var t = (x - xa) / (xb - xa); return 10 + 8 * Math.sin(Math.PI * Math.min(1, Math.max(0, t * 1.15))); }
      function samp(fn, a0, a1) { var a = []; for (var i = 0; i <= N; i++) { var x = a0 + (a1 - a0) * i / N; a.push([x, fn(x)]); } return a; }
      // 山坡土台：前立面 + 顶面
      o += poly([[140, 44 - g(140)], [146, 46 - g(140)], [146, 83], [140, 83]], S.shadow, null, 0, fop(S.sop));
      var topF = samp(function (x) { return 80 - g(x); }, 4, 140), topB = samp(function (x) { return 38 - g(x); }, 4, 140).reverse();
      o += poly(topF.concat(topB), S.stone, G, LD);
      o += poly([[4, 80]].concat(topF).concat([[140, 80]]), S.stone2, G, LW);
      o += C.clip(id + '-bk', poly([[4, 80]].concat(topF).concat([[140, 80]]), '#000'), C.rubble(4, 40, 140, 80, r, S.umber, 0.35));
      // 窑身：前下沿与顶轮廓
      var bot = samp(function (x) { return 68 - g(x); }, xa, xb), crest = samp(function (x) { return 50 - g(x) - vh(x); }, xa, xb);
      var lit = samp(function (x) { return 57 - g(x) - vh(x) * 0.55; }, xa, xb);
      o += poly(bot.map(function (p) { return [p[0] + 7, p[1] + 3]; }).concat(crest.map(function (p) { return [p[0] + 7, p[1] + 6]; }).reverse()), S.shadow, null, 0, fop(S.sop));
      var body = bot.concat(crest.slice().reverse());
      o += poly(body, S.umber2, G, LW);
      o += C.clip(id + '-v', poly(body, '#000'), poly(crest.concat(lit.slice().reverse()), '#c97a4c', null, 0) +
        C.brick(xa, -10, xb, 70, 4, 9, S.umber, 0.4));
      // 分节（目）：每节一道拱箍线 + 一枚投柴孔
      var ribs = [];
      for (var x = xa + 10; x < xb - 4; x += 10) {
        ribs.push([x, 68 - g(x), x + 2, 50 - g(x) - vh(x)]);
        var hx = x + 5, hy = 55 - g(hx) - vh(hx) * 0.55;
        o += ell(hx, hy, 2.2, 1.5, S.navy, G2, 0.7);
        if (((x - xa) / 10) % 3 === 1) o += ell(hx, hy + 0.3, 1.1, 0.7, S.orange, null, 0);
      }
      o += lines(ribs, G2, 1.2, 0.85);
      o += pl(crest, G2, 1.1);
      // 窑门两道（封着的砖门，一道半开）
      [[58, false], [100, true]].forEach(function (d) {
        var x = d[0], y = 68 - g(x);
        o += path(C.archD(x, y, 9, 7), d[1] ? S.navy : S.umber, G2, 1) + (d[1] ? '' : C.brick(x - 4.5, y - 11, x + 4.5, y, 3, 4, S.ochre, 0.6));
      });
      // 窑头火膛（左端，砖砌，火口朝南）
      o += C.shadow(8, 50, 28, 70, 5, S, 3);
      o += C.box(8, 52, 28, 70, 16, S.umber, S.umber2, G, LW);
      o += path(C.archD(18, 70, 10, 5), S.navy, G2, 1.2) + path('M14 70q2 -7 4 -9q0 4 2 5q1 -2 2 -3q1 4 -1 7z', S.orange, null, 0);
      o += C.smoke(14, 32, S, 2, 13);
      // 窑尾烟囱（右端高处）
      var cxs = 132, cg = g(cxs);
      o += C.box(126, 50 - cg, 138, 58 - cg, 22, S.umber, S.umber2, G, LW) + rect(128, 37 - cg - 22 + 13, 8, 2, S.navy, null, 0);
      o += C.smoke(130, 36 - cg - 22, S, 3, 23);
      // 坡下柴垛与待烧的坛罐
      o += C.shadow(30, 84, 74, 92, 4, S, 2) + C.logPile(30, 94, 7, 3, S);
      [[96, 92], [107, 93], [118, 92], [102, 85], [113, 85]].forEach(function (p, k) {
        o += C.frustum(p[0], p[1], 3.6, 1.6, 4.6, 2, 8, k % 2 ? S.teal : S.umber2, S.navy, G, 0.8);
      });
      o += rect(126, 82, 14, 12, S.ochre, G, LD) + C.planks(126, 82, 140, 94, 3.5, true, S.umber, 0.5);
      return o;
    }
  });

  // ================= 染坊（高晾布架挂彩布 + 染缸 + 作坊） =================
  function cloth(x, top, bot, w, col, pat) {
    var d = 'M' + f(x) + ' ' + f(top) + 'L' + f(x + w) + ' ' + f(top) + 'L' + f(x + w + 0.8) + ' ' + f(bot - 2) +
      'Q' + f(x + w * 0.5) + ' ' + f(bot + 2) + ' ' + f(x + 0.4) + ' ' + f(bot) + 'Z';
    var o = path(d, col, G, 1);
    o += ln(x + w * 0.62, top + 2, x + w * 0.7, bot - 2, '#000', 0.8, 0.12);
    if (pat === 'dots') for (var y = top + 5; y < bot - 3; y += 6) o += circ(x + w * 0.3, y, 0.9, S.cream2, null, 0) + circ(x + w * 0.72, y + 3, 0.9, S.cream2, null, 0);
    if (pat === 'band') o += rect(x, top + (bot - top) * 0.6, w, 4, S.ochre2, null, 0);
    return o;
  }
  def({
    kind: 'dyehouse_cloth', idKind: 'tannery', facility: 'tannery', variant: 1, w: 3, d: 2, up: 108,
    tags: ['dye_house', 'cloth_rack', 'dye_vats', 'workshop', 'indigo'], roof: 'gable_tile',
    note: '染坊（FacilityKind 没有染坊，按同类“浸泡加工作坊”归入 tannery）：右侧三根高杆搭起两层晾布架，挂着靛蓝、蓝印花、青绿、朱红、赭黄的长布；左后灰瓦作坊；前方一排染缸，缸面是不同染液。',
    draw: function (W, D, r, id) {
      var o = '';
      o += C.shadow(6, 22, 52, 60, 8, S, 3) + poly([[140, 40], [146, 42], [146, 47], [62, 47], [62, 44], [140, 44]], S.shadow, null, 0, fop(S.sop));
      o += pad(2, 12, 144, 96);
      // 作坊（左后）
      var x0 = 6, x1 = 52, y0 = 22, y1 = 60, h = 26;
      o += rect(x0, y1 - h, x1 - x0, h, S.cream, G, LW);
      o += rect(x0 + 16, y1 - 18, 14, 18, S.umber, G, LD) + rect(x0 + 4, y1 - 19, 8, 9, S.navy, G2, 0.8) +
        lines([[x0 + 8, y1 - 19, x0 + 8, y1 - 10], [x0 + 4, y1 - 14.5, x0 + 12, y1 - 14.5]], G2, 0.6);
      o += rect(x1 - 13, y1 - 19, 8, 9, S.navy, G2, 0.8) + lines([[x1 - 9, y1 - 19, x1 - 9, y1 - 10], [x1 - 13, y1 - 14.5, x1 - 5, y1 - 14.5]], G2, 0.6);
      o += pillar(x0 + 1.5, y1 - h, y1) + pillar(x1 - 1.5, y1 - h, y1);
      o += eaveRoof(id + '-r', x0, x1, (y0 + y1) / 2 - h - 12, y1 - h + 4, 4, S.gray, S.gray2, 5, y0 - h);
      // 门前长凳 + 叠好的布匹
      o += rect(8, 66, 40, 3, S.umber2, G, 0.8) + lines([[11, 69, 11, 74], [45, 69, 45, 74]], S.umber, 1.4);
      [[12, S.navy], [21, S.teal], [30, S.vermil], [39, S.navy2]].forEach(function (b) { o += C.box(b[0], 62, b[0] + 7, 66, 4, b[1], b[1], G, 0.7); });
      // 晾布架：三根高杆、两道横杆
      var poles = [62, 101, 140], tb = -96, mb = -40;
      poles.forEach(function (x) { o += ln(x, 44, x, tb - 4, S.umber, 2.6) + ln(x - 6, 44, x, 30, S.umber, 1.4); });
      var cols = [[S.navy, 'dots'], [S.navy2, null], [S.teal, 'band'], [S.vermil, null], [S.navy, null], [S.ochre, 'band'], [S.teal2, null], [S.navy, 'dots'], [S.orange, null]];
      cols.forEach(function (c, i) {
        var x = 64 + i * 8.5, long = i % 3 !== 1;
        o += cloth(x, tb + 1, long ? 24 - (i % 2) * 6 : mb - 4, 7, c[0], c[1]);
      });
      // 中横杆上搭的短布（压在长布前）
      [[70, S.vermil], [96, S.ochre], [116, S.cream]].forEach(function (c) { o += cloth(c[0], mb + 1, mb + 26, 11, c[1], c[1] === S.cream ? 'dots' : null); });
      o += ln(58, tb, 144, tb, S.umber, 3) + ln(58, tb, 144, tb, G, 0.8, 0.8) + ln(60, mb, 142, mb, S.umber, 2.2);
      // 染缸一排（前沿），缸面染液
      [[70, S.navy], [86, S.navy2], [102, S.teal], [118, S.vermil], [134, S.ochre]].forEach(function (v, k) {
        o += C.shadowEll(v[0], 88, 7, 2.6, 5, S) + C.frustum(v[0], 88, 5.5, 2.4, 7.5, 3, 12, S.umber2, v[1], G, LD) +
          ell(v[0], 76, 7.5, 3, 'none', G2, 0.9);
        if (k === 1) o += ln(v[0] - 2, 76, v[0] + 5, 62, S.ochre, 1.6);
      });
      o += C.frustum(18, 90, 5, 2, 6, 2.4, 9, S.ochre, S.stone2, G, LD);
      return o;
    }
  });

  /** 矿篓：竹编背篓，装着矿石。 */
  function basket(x, y, s, ore) {
    var o = C.shadowEll(x, y, 5 * s, 2 * s, 4, S) + C.frustum(x, y, 4.2 * s, 1.8 * s, 5.6 * s, 2.3 * s, 10 * s, S.ochre, S.umber2, G, LD);
    o += lines([[x - 4.6 * s, y - 3 * s, x + 4.6 * s, y - 3 * s], [x - 5.1 * s, y - 6.5 * s, x + 5.1 * s, y - 6.5 * s]], S.umber, 0.8, 0.8);
    o += lines([[x - 2 * s, y, x - 2.6 * s, y - 10 * s], [x + 2 * s, y, x + 2.6 * s, y - 10 * s]], S.umber, 0.6, 0.6);
    if (ore) for (var i = 0; i < 4; i++) o += circ(x - 3 * s + i * 2 * s, y - 10.5 * s - (i % 2), 1.6 * s, i % 2 ? S.gray2 : S.gray, G, 0.5);
    return o;
  }

  // ================= 矿洞口（山壁 + 木撑洞口 + 矿篓 + 灯笼） =================
  def({
    kind: 'mine_adit', idKind: 'mine_head', facility: 'mine_head', variant: 1, w: 2, d: 2, up: 88,
    tags: ['adit', 'cliff', 'timber_props', 'ore_baskets', 'lantern', 'spoil_heap', 'cliff_north'], roof: 'none',
    note: '平硐式矿洞：后半格起是青绿山水式的山壁（青绿峰顶、赭石山脚、金线皴纹），正中洞口用木柱 + 横梁 + 人字撑支护，梁下挂红灯笼；洞口铺木板道出来，旁边几只装矿石的竹矿篓和一根扁担，右前废石堆，左侧小木牌。山壁朝南，放置时地块北侧接山地更自然。',
    draw: function (W, D, r, id) {
      var o = '';
      // 山壁：后层青绿峰、前层赭石崖
      var back = [[0, 30], [4, -20], [16, -44], [28, -34], [40, -66], [54, -50], [64, -58], [78, -30], [90, -36], [96, -10], [96, 30]];
      o += poly(back, S.teal, G, LW);
      o += C.clip(id + '-pk', poly(back, '#000'), poly([[0, -2], [14, -36], [28, -24], [40, -56], [50, -42], [64, -48], [80, -20], [96, -6], [96, 30], [0, 30]], S.teal2, null, 0, fop(0.55)));
      var cliff = [[0, 62], [0, 18], [10, 4], [22, 10], [34, -6], [48, 0], [60, -10], [74, 6], [86, 2], [96, 14], [96, 60]];
      o += poly(cliff, S.ochre, G, LW);
      o += C.clip(id + '-cl', poly(cliff, '#000'),
        poly([[60, -10], [74, 6], [86, 2], [96, 14], [96, 62], [62, 62]], S.umber2, null, 0, fop(0.55)) +
        lines([[8, 14, 4, 30], [20, 14, 14, 36], [30, 4, 24, 22], [70, 10, 76, 30], [84, 8, 90, 34], [12, 40, 8, 54], [82, 40, 88, 56]], G, 1, 0.8));
      // 峰顶小松
      [[40, -66], [16, -44]].forEach(function (p, k) {
        o += ln(p[0], p[1], p[0], p[1] - 9, S.umber, 1.4) + poly([[p[0] - 6, p[1] - 5], [p[0], p[1] - 14], [p[0] + 6, p[1] - 5]], S.navy2, G, 0.9) +
          poly([[p[0] - 4.5, p[1] - 10], [p[0], p[1] - 18], [p[0] + 4.5, p[1] - 10]], S.navy2, G, 0.9);
      });
      // 洞口：深色拱洞 + 两层暗晕
      var cx = 46, by = 62;
      o += path(C.archD(cx, by, 34, 20), S.navy, G, LW) + path(C.archD(cx, by, 24, 14), '#142a40', null, 0) + path(C.archD(cx, by, 12, 8), '#0c1c2c', null, 0);
      // 木撑：两柱 + 横梁 + 人字撑
      o += rect(29, 34, 4, 28, S.umber2, G, LD) + rect(59, 34, 4, 28, S.umber2, G, LD);
      o += rect(25, 30, 42, 5, S.umber, G, LD) + lines([[31, 44, 46, 31], [61, 44, 46, 31]], S.umber, 2.2);
      o += lines([[27, 32.5, 65, 32.5]], G2, 0.6, 0.8);
      // 红灯笼
      o += ln(54, 35, 54, 39, G, 0.8) + ell(54, 43, 3.6, 4.4, S.vermil, G, 0.9) + rect(52.5, 38.5, 3, 1.2, S.ochre, null, 0) + rect(52.5, 47, 3, 1.2, S.ochre, null, 0);
      // 木板道
      var pk = [];
      for (var y = 64; y < 94; y += 4) pk.push([36, y, 56, y]);
      o += poly([[34, 62], [58, 62], [60, 94], [32, 94]], S.ochre2, G, LD) + lines(pk, S.umber, 0.8, 0.6);
      // 矿篓、扁担
      o += basket(20, 82, 1, true) + basket(70, 78, 0.9, true) + basket(80, 90, 1, false);
      o += ln(10, 92, 30, 86, S.umber, 2) + ln(10, 92, 30, 86, G, 0.6, 0.7);
      // 废石堆（右前）
      o += C.shadowEll(84, 70, 10, 4, 6, S) + C.dome(84, 70, 10, 4, 12, S.gray2, G, LD);
      for (var k = 0; k < 7; k++) o += circ(77 + r() * 14, 63 + r() * 6, 1 + r(), S.gray, G, 0.5);
      // 左侧木牌
      o += ln(10, 70, 10, 56, S.umber, 1.8) + rect(4, 48, 12, 9, S.vermil, G, 1) + rect(6, 50, 8, 5, 'none', G2, 0.7);
      return o;
    }
  });

  // ================= 锅炉房（铜炉房：三足铜鼎锅炉 + 瓦屋机房 + 铜烟囱，带一点奇幻） =================
  def({
    kind: 'boiler_bronze', idKind: 'boiler_house', facility: 'boiler_house', variant: 1, w: 3, d: 2, up: 104,
    tags: ['bronze_cauldron', 'copper_chimney', 'steam', 'talisman', 'eave_roof', 'steam_fantasy'], roof: 'gable_tile',
    note: '东方化的锅炉房：左前一只三足铜鼎当锅炉（鼎腹回纹带、双耳、盖上铜钮，鼎腹贴一道符纸，足间柴火），鼎盖引一根铜管进右侧灰瓦机房；左后一座分节铜烟囱，顶上仰莲形帽冒云头状白汽。奇幻成分只有符纸和鼎腹一圈青玉纹。',
    draw: function (W, D, r, id) {
      var o = '', CU = '#d08a4a', CU2 = '#a5602e', CU3 = '#e9b07a';
      o += C.shadow(58, 24, 140, 66, 8, S, 3) + C.shadow(16, 8, 30, 20, 14, S, 2) + C.shadowEll(36, 84, 22, 6, 12, S);
      o += pad(4, 6, 142, 94);
      // 铜烟囱（左后）：分节圆筒
      var hx = 23, hy = 18;
      o += C.cyl(hx, hy, 7, 2.6, 80, CU2, null, G, LW);
      o += C.clip(id + '-ch', path('M' + f(hx - 7) + ' ' + f(hy - 80) + 'L' + f(hx - 7) + ' ' + f(hy) + 'L' + f(hx - 1) + ' ' + f(hy) + 'L' + f(hx - 1) + ' ' + f(hy - 80) + 'Z', '#000'), rect(hx - 7, hy - 80, 6, 82, CU, null, 0));
      [10, 30, 50, 70].forEach(function (dy) { o += path('M' + f(hx - 8) + ' ' + f(hy - dy) + 'A8 3 0 0 0 ' + f(hx + 8) + ' ' + f(hy - dy), null, G2, 2.2); });
      // 仰莲帽
      var ty = hy - 80;
      o += path('M' + f(hx - 7) + ' ' + f(ty) + 'Q' + f(hx - 13) + ' ' + f(ty - 4) + ' ' + f(hx - 12) + ' ' + f(ty - 9) + 'Q' + f(hx - 7) + ' ' + f(ty - 6) + ' ' + f(hx - 5) + ' ' + f(ty - 9) +
        'Q' + f(hx) + ' ' + f(ty - 5) + ' ' + f(hx + 5) + ' ' + f(ty - 9) + 'Q' + f(hx + 7) + ' ' + f(ty - 6) + ' ' + f(hx + 12) + ' ' + f(ty - 9) + 'Q' + f(hx + 13) + ' ' + f(ty - 4) + ' ' + f(hx + 7) + ' ' + f(ty) + 'Z', CU3, G, LD);
      o += ell(hx, ty - 8, 8, 2.4, '#3a2a20', G, 0.8) + C.smoke(hx - 2, ty - 14, S, 2, 41);
      // 机房：灰瓦坡顶、朱柱、格窗、板门
      var x0 = 58, x1 = 140, y0 = 24, y1 = 66, h = 30;
      o += rect(x0, y1 - h, x1 - x0, h, S.cream, G, LW);
      o += rect(x0, y1 - 6, x1 - x0, 6, S.stone2, G, LD);
      // 格窗（透出炉光）
      [76, 122].forEach(function (x) {
        o += rect(x - 8, y1 - 24, 16, 12, S.ochre2, G, LD);
        var s = [];
        for (var k = 1; k < 4; k++) s.push([x - 8 + k * 4, y1 - 24, x - 8 + k * 4, y1 - 12]);
        s.push([x - 8, y1 - 18, x + 8, y1 - 18]);
        o += lines(s, S.umber, 0.9);
      });
      o += rect(92, y1 - 26, 16, 26, S.umber, G, LD) + ln(100, y1 - 26, 100, y1, G2, 0.8) + circ(98, y1 - 13, 0.9, G2, null, 0) + circ(102, y1 - 13, 0.9, G2, null, 0);
      o += pillar(x0 + 2, y1 - h, y1) + pillar(x1 - 2, y1 - h, y1) + pillar(88, y1 - h, y1) + pillar(112, y1 - h, y1);
      o += eaveRoof(id + '-r', x0, x1, (y0 + y1) / 2 - h - 14, y1 - h + 5, 5, S.gray, S.gray2, 5, y0 - h);
      // 屋脊中央的铜火珠
      var rdy = (y0 + y1) / 2 - h - 14;
      o += circ(99, rdy - 5, 3.6, CU3, G, 1) + path('M99 ' + f(rdy - 12) + 'q2 3 0 5q-2 -2 0 -5z', S.orange, G, 0.6);
      // 铜鼎锅炉：三足、鼎腹、双耳、盖、钮
      var cx = 36, gy = 84, bh = 22, rx = 20, ry = 6.5, yb = gy - 8;
      // 足间柴火
      o += C.logPile(cx - 12, gy, 4, 1, S) + path('M' + f(cx - 6) + ' ' + f(gy - 6) + 'q2 -8 5 -10q0 5 2 6q2 -4 3 -5q2 6 -1 9z', S.orange, G, 0.7);
      [[-14, 0], [0, 2.5], [14, 0]].forEach(function (lg) { o += rect(cx + lg[0] - 2, yb + lg[1] - 2, 4, 10 - lg[1] * 0.4, CU2, G, LD); });
      o += C.cyl(cx, yb, rx, ry, bh, CU, null, G, LW);
      o += C.clip(id + '-dp', path('M' + f(cx + rx * 0.3) + ' ' + f(yb - bh) + 'L' + f(cx + rx) + ' ' + f(yb - bh) + 'L' + f(cx + rx) + ' ' + f(yb + ry) + 'L' + f(cx + rx * 0.3) + ' ' + f(yb + ry) + 'Z', '#000'),
        C.cyl(cx, yb, rx, ry, bh, CU2, null, null, 0));
      o += C.cyl(cx, yb, rx, ry, bh, 'none', null, G, LW);
      // 回纹带 + 青玉纹
      var my = yb - bh * 0.55;
      o += path('M' + f(cx - rx) + ' ' + f(my - 3) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + rx) + ' ' + f(my - 3), null, G2, 1.4) +
        path('M' + f(cx - rx) + ' ' + f(my + 4) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + rx) + ' ' + f(my + 4), null, G2, 1.4);
      for (var q = -15; q <= 12; q += 6) {
        var qy = my + 0.5 + ry * Math.sqrt(Math.max(0, 1 - (q / rx) * (q / rx)));
        o += path('M' + f(cx + q) + ' ' + f(qy + 1.5) + 'h3v-3h-2v1.5', null, S.jade, 0.9);
      }
      // 双耳
      o += path('M' + f(cx - rx - 1) + ' ' + f(yb - bh + 2) + 'q-6 0 -6 -5q0 -4 4 -4', null, CU2, 2.4) + path('M' + f(cx + rx + 1) + ' ' + f(yb - bh + 2) + 'q6 0 6 -5q0 -4 -4 -4', null, CU2, 2.4);
      // 鼎盖 + 钮
      o += ell(cx, yb - bh, rx, ry, CU3, G, LW) + C.dome(cx, yb - bh - 1, rx * 0.72, ry * 0.7, 8, CU, G, LD) + circ(cx, yb - bh - 10, 2.6, CU3, G, 0.9);
      // 符纸
      o += rect(cx - 4, yb - bh + 5, 7, 15, '#f3e09a', G, 0.7) + lines([[cx - 0.5, yb - bh + 7, cx - 0.5, yb - bh + 18], [cx - 2.5, yb - bh + 10, cx + 1.5, yb - bh + 10]], S.vermil, 0.9);
      // 铜管：鼎盖 → 机房
      var pd = 'M' + f(cx + 8) + ' ' + f(yb - bh - 4) + 'L' + f(cx + 8) + ' ' + f(yb - bh - 12) + 'Q' + f(cx + 8) + ' ' + f(yb - bh - 16) + ' ' + f(cx + 12) + ' ' + f(yb - bh - 16) + 'L' + f(x0 + 2) + ' ' + f(yb - bh - 16);
      o += path(pd, null, G, 4.8) + path(pd, null, CU3, 2.8);
      o += rect(cx + 18, yb - bh - 18.5, 3, 5, CU2, G, 0.6);
      // 泄汽云头
      o += C.smoke(cx - 10, yb - bh - 12, S, 2, 47);
      // 前方：水桶、炭篓
      o += C.cyl(76, 90, 5, 2, 8, S.umber2, S.teal2, G, LD) + lines([[71, 87, 81, 87]], G2, 0.8) + basket(120, 90, 1, false) + basket(132, 86, 0.9, false);
      return o;
    }
  });

  // ================= 结界塔（镇妖塔：八角密檐小塔 + 塔顶符阵 + 符箓） =================
  def({
    kind: 'ward_pagoda', idKind: 'ward_tower', facility: 'ward_tower', variant: 1, w: 2, d: 2, up: 112,
    tags: ['pagoda', 'talisman', 'seal_array', 'glow', 'ward', 'stone_base'], roof: 'hip_tile',
    note: '镇妖塔：须弥座石台基上立三层收分的塔身（朱柱米墙、每层青绿檐翘角、檐角挂铃），底层拱门贴交叉封条符纸；塔刹换成一枚悬空的金色八卦符阵（两圈金环 + 八道卦线 + 中心太极），四周飘四张黄符。roof 记 hip_tile（攒尖/庑殿类最近项）。',
    draw: function (W, D, r, id) {
      var o = '', cx = 48, base = 78;
      o += C.shadow(16, 46, 80, 82, 14, S, 3);
      o += pad(4, 30, 92, 94, S.stone2);
      // 须弥座台基（两级）
      o += C.box(12, 56, 84, 86, 6, S.stone, S.stone2, G, LW) + C.box(18, 52, 78, 80, 6, S.cream2, S.stone, G, LD);
      o += lines([[18, 77, 78, 77]], S.umber, 0.8, 0.5);
      // 台阶
      for (var i = 0; i < 3; i++) o += rect(38 - i * 1.5, 80 + i * 2, 20 + i * 3, 2, S.cream, G, 0.7);
      // 三层塔身：每层 墙 + 檐
      var y = base - 6, levels = [[28, 24, 36], [23, 18, 30], [18, 14, 24]];
      levels.forEach(function (lv, k) {
        var hw = lv[0], h = lv[1], ehw = lv[2], wy = y - h;
        o += rect(cx - hw, wy, hw * 2, h, S.cream, G, LW);
        o += rect(cx + hw * 0.35, wy, hw * 0.65, h, S.ochre2, null, 0, fop(0.55));
        o += pillar(cx - hw + 2, wy, y, 3) + pillar(cx + hw - 2, wy, y, 3);
        if (k === 0) {
          // 拱门 + 交叉封条
          o += path(C.archD(cx, y, 14, 10), S.umber, G2, 1.1) + lines([[cx - 7, y - 3, cx + 7, y - 14], [cx + 7, y - 3, cx - 7, y - 14]], '#f3e09a', 2.4) +
            lines([[cx - 7, y - 3, cx + 7, y - 14], [cx + 7, y - 3, cx - 7, y - 14]], S.vermil, 0.6);
        } else {
          o += path(C.archD(cx, y - 3, 7, 5 - k), S.ochre, G, 0.9);
        }
        // 檐：青绿瓦、翘角、挂铃
        var ey = wy + 2, ry = wy - 10;
        o += eaveRoof(id + '-e' + k, cx - hw, cx + hw, ry, ey, ehw - hw, S.teal, S.teal2, 6);
        [cx - ehw, cx + ehw].forEach(function (x) { o += ln(x, ey - 6, x, ey - 2, G, 0.8) + circ(x, ey - 1, 1.6, S.ochre, G, 0.6); });
        y = ry + 2;
      });
      // 塔顶宝珠座
      o += C.frustum(cx, y, 6, 2, 3, 1.2, 6, S.ochre, S.ochre2, G, LD);
      // 符阵：悬空八卦
      var qy = y - 26, R = 15;
      o += circ(cx, qy, R + 6, S.ochre2, null, 0, fop(0.35));
      o += circ(cx, qy, R + 3, 'none', S.ink2, 1.6) + circ(cx, qy, R - 3, S.navy, G2, 1.4);
      for (var t = 0; t < 8; t++) {
        var a = t / 8 * Math.PI * 2, c = Math.cos(a), s = Math.sin(a), mx = cx + c * (R + 0.2), my = qy + s * (R + 0.2);
        var px = -s * 3.2, py = c * 3.2;
        o += ln(mx - px, my - py, mx + px, my + py, S.ink2, 1.4) + ln(mx - px + c * 2.4, my - py + s * 2.4, mx + px + c * 2.4, my + py + s * 2.4, S.ink2, t % 2 ? 0.7 : 1.4, t % 2 ? 0.6 : 1);
      }
      // 太极
      var tr = 6;
      o += circ(cx, qy, tr, S.cream2, G2, 0.9) +
        path('M' + f(cx) + ' ' + f(qy - tr) + 'A' + f(tr) + ' ' + f(tr) + ' 0 0 1 ' + f(cx) + ' ' + f(qy + tr) + 'A' + f(tr / 2) + ' ' + f(tr / 2) + ' 0 0 1 ' + f(cx) + ' ' + f(qy) +
          'A' + f(tr / 2) + ' ' + f(tr / 2) + ' 0 0 0 ' + f(cx) + ' ' + f(qy - tr) + 'Z', S.vermil, null, 0) +
        circ(cx, qy - tr / 2, 1.1, S.vermil, null, 0) + circ(cx, qy + tr / 2, 1.1, S.cream2, null, 0);
      o += ln(cx, y - 6, cx, qy + R + 3, S.ink2, 0.8, 0.6);
      // 飘符四张
      [[cx - 34, qy + 6, -12], [cx + 30, qy - 2, 10], [cx - 26, qy - 22, 8], [cx + 26, qy + 22, -6]].forEach(function (p) {
        o += '<g transform="rotate(' + f(p[2]) + ' ' + f(p[0]) + ' ' + f(p[1]) + ')">' + rect(p[0] - 3, p[1] - 7, 6, 14, '#f3e09a', G, 0.7) +
          lines([[p[0], p[1] - 5, p[0], p[1] + 5], [p[0] - 1.8, p[1] - 2, p[0] + 1.8, p[1] - 2]], S.vermil, 0.8) + '</g>';
      });
      // 台前两尊镇石（石狮墩简化成圆墩+火焰）
      [[16, 90], [80, 90]].forEach(function (p) {
        o += C.cyl(p[0], p[1], 4, 1.8, 6, S.stone2, S.stone, G, LD) + path('M' + f(p[0] - 2) + ' ' + f(p[1] - 7) + 'q1 -5 2 -6q1 3 2 6z', S.orange, G, 0.6);
      });
      return o;
    }
  });

  /** 幌子：挂在挑杆上的长条布幌，写一道字纹。 */
  function banner(x, y, len, col) {
    return ln(x, y, x + 10, y, S.umber, 1.6) + rect(x + 4, y + 1, 6, len, col || S.vermil, G, 0.9) +
      lines([[x + 7, y + 4, x + 7, y + len - 3], [x + 5.5, y + 7, x + 8.5, y + 7]], S.cream2, 0.8) +
      path('M' + f(x + 4) + ' ' + f(y + len + 1) + 'l1.5 3l1.5 -3l1.5 3l1.5 -3', null, G, 0.7);
  }

  // ================= 货栈一（两层木构货栈 + 挑出吊货檐 + 挂幌） =================
  def({
    kind: 'depot_two_storey', idKind: 'warehouse', facility: 'warehouse', variant: 1, w: 3, d: 2, up: 76,
    tags: ['two_storey', 'banner', 'hoist', 'shutters', 'eave_roof'], roof: 'gable_tile',
    note: '两层货栈：底层敞开的排门板（一半卸下露出码放的货包），二层出挑的木栏走廊与支摘窗，二层正中开吊货口、檐下挑木挂滑轮；灰瓦坡顶，左檐挑杆挂朱红长幌、右檐挂青幌；门前石板阶前堆着麻包、坛子。',
    draw: function (W, D, r, id) {
      var o = '', x0 = 12, x1 = 134, y0 = 18, y1 = 74;
      o += C.shadow(x0, y0, x1, y1, 10, S, 3);
      o += pad(4, 10, 142, 94, S.stone2);
      // 底层
      o += rect(x0, y1 - 26, x1 - x0, 26, S.umber2, G, LW);
      // 排门板（左半合着、右半卸下露货）
      o += C.planks(x0, y1 - 26, 72, y1, 6, true, S.umber, 0.7);
      o += rect(74, y1 - 24, 56, 24, S.navy, G, LD);
      [[78, 68, 10], [90, 70, 12], [104, 68, 10], [84, 60, 9], [98, 61, 10], [116, 70, 11]].forEach(function (b) {
        o += C.box(b[0], b[1] - 4, b[0] + b[2], b[1], 6, S.cream, S.ochre, G, 0.8);
      });
      // 一层檐（腰檐）
      o += eaveRoof(id + '-w', x0, x1, y1 - 32, y1 - 24, 4, S.gray, S.gray2, 3);
      // 二层：退进一点
      var u0 = x0 + 4, u1 = x1 - 4, uy = y1 - 34, uh = 26;
      o += rect(u0, uy - uh, u1 - u0, uh, S.cream, G, LW);
      // 支摘窗
      [24, 44, 102, 122].forEach(function (x) {
        o += rect(x - 7, uy - 22, 14, 12, S.vermil, G, LD) + rect(x - 5, uy - 20, 10, 8, S.ochre2, G2, 0.6) +
          lines([[x, uy - 20, x, uy - 12], [x - 5, uy - 16, x + 5, uy - 16]], S.umber, 0.7);
      });
      // 吊货口 + 货包
      o += rect(64, uy - 24, 18, 22, S.navy, G, LD) + C.box(67, uy - 8, 79, uy - 2, 7, S.ochre, S.umber2, G, 0.8);
      // 二层木栏
      var bs = [];
      for (var x = u0 + 4; x < u1; x += 5) bs.push([x, uy - 8, x, uy]);
      o += lines(bs, S.umber, 1.2) + lines([[u0, uy - 8, u1, uy - 8]], S.vermil, 2);
      o += pillar(u0 + 2, uy - uh, uy, 3) + pillar(u1 - 2, uy - uh, uy, 3);
      // 屋顶
      var ry = y0 - 8 - uh - 6;
      o += eaveRoof(id + '-r', u0, u1, ry + 6, uy - uh + 4, 5, S.gray, S.gray2, 6, ry - 6);
      // 吊货挑木 + 滑轮 + 绳
      o += ln(73, uy - uh + 2, 73, uy - uh - 8, S.umber, 2.4) + rect(70, uy - uh - 10, 6, 3, S.umber, G, 0.7);
      o += circ(73, uy - uh + 5, 2.4, S.ochre, G, 0.8) + ln(72, uy - uh + 7, 72, uy - 9, S.umber, 0.8);
      // 幌子
      o += banner(u0 - 6, uy - uh + 6, 24, S.vermil) + banner(u1 - 4, uy - uh + 6, 20, S.teal);
      // 门前
      o += rect(x0, y1, x1 - x0, 3, S.stone, G, 0.7);
      [[20, 90], [30, 92], [25, 84]].forEach(function (p) {
        o += path('M' + f(p[0] - 6) + ' ' + f(p[1]) + 'Q' + f(p[0] - 7) + ' ' + f(p[1] - 7) + ' ' + f(p[0]) + ' ' + f(p[1] - 7) + 'Q' + f(p[0] + 7) + ' ' + f(p[1] - 7) + ' ' + f(p[0] + 6) + ' ' + f(p[1]) + 'Z', S.cream, G, 0.9);
      });
      [[118, 90], [128, 88]].forEach(function (p) { o += C.frustum(p[0], p[1], 4, 1.6, 3, 1.2, 9, S.umber2, S.umber, G, LD) + rect(p[0] - 2, p[1] - 12, 4, 3, S.vermil, G, 0.6); });
      return o;
    }
  });

  // ================= 义冢（土坟 + 石碑 + 松柏 + 矮围墙） =================
  function stele(x, y, w, h, big) {
    var o = C.shadow(x - w / 2, y - 2, x + w / 2, y, 4, S, 2);
    if (big) o += C.box(x - w / 2 - 4, y - 6, x + w / 2 + 4, y, 5, S.stone, S.stone2, G, LD);
    var by = big ? y - 5 : y;
    o += path('M' + f(x - w / 2) + ' ' + f(by) + 'L' + f(x - w / 2) + ' ' + f(by - h + w * 0.35) + 'Q' + f(x) + ' ' + f(by - h - w * 0.15) + ' ' + f(x + w / 2) + ' ' + f(by - h + w * 0.35) +
      'L' + f(x + w / 2) + ' ' + f(by) + 'Z', S.cream, G, big ? LW : LD);
    o += rect(x + w * 0.15, by - h + w * 0.3, w * 0.35, h - w * 0.3, S.stone, null, 0, fop(0.5));
    var s = [];
    for (var k = 0; k < (big ? 2 : 1); k++) {
      var lx = x + (big ? (k ? -2 : 2) : 0);
      s.push([lx, by - h + w * 0.55, lx, by - 3]);
      if (big) for (var j = 0; j < 4; j++) s.push([lx - 1.4, by - h + w * 0.6 + j * 4.5, lx + 1.4, by - h + w * 0.6 + j * 4.5]);
    }
    return o + lines(s, S.vermil, big ? 1.1 : 0.9);
  }
  function mound(x, y, rx) {
    return C.shadowEll(x, y, rx, rx * 0.4, 6, S) + ell(x, y, rx + 2, rx * 0.4 + 1, S.stone2, G, LD) +
      C.dome(x, y - 1, rx, rx * 0.38, rx * 0.75, S.ochre, G, LW) +
      path('M' + f(x - rx * 0.7) + ' ' + f(y - rx * 0.35) + 'Q' + f(x - rx * 0.4) + ' ' + f(y - rx * 0.78) + ' ' + f(x + rx * 0.05) + ' ' + f(y - rx * 0.72), null, S.ochre2, 1.6) +
      lines([[x - 2, y - rx * 0.7, x - 3, y - rx * 0.95], [x + 1, y - rx * 0.72, x + 2, y - rx], [x + 4, y - rx * 0.66, x + 5, y - rx * 0.88]], S.teal, 0.9);
  }
  function pine(x, y, s) {
    var o = C.shadowEll(x + 4, y, 14 * s, 4 * s, 8, S);
    o += path('M' + f(x) + ' ' + f(y) + 'Q' + f(x - 5 * s) + ' ' + f(y - 18 * s) + ' ' + f(x + 2 * s) + ' ' + f(y - 34 * s), null, G, 5.2 * s) +
      path('M' + f(x) + ' ' + f(y) + 'Q' + f(x - 5 * s) + ' ' + f(y - 18 * s) + ' ' + f(x + 2 * s) + ' ' + f(y - 34 * s), null, S.umber, 3.4 * s);
    [[-9, -24, 14, 0], [8, -32, 13, 1], [-3, -44, 12, 0], [12, -18, 10, 1]].forEach(function (c) {
      var cx = x + c[0] * s, cy = y + c[1] * s, rx = c[2] * s;
      o += ell(cx, cy, rx, rx * 0.42, c[3] ? S.navy2 : S.teal, G, LD) + ell(cx - rx * 0.15, cy - rx * 0.08, rx * 0.62, rx * 0.22, c[3] ? S.teal : S.teal2, null, 0);
    });
    return o;
  }
  function cypress(x, y, h) {
    var d = 'M' + f(x) + ' ' + f(y - h) + 'C' + f(x - 13) + ' ' + f(y - h * 0.6) + ' ' + f(x - 11) + ' ' + f(y - 6) + ' ' + f(x) + ' ' + f(y - 3) +
      'C' + f(x + 11) + ' ' + f(y - 6) + ' ' + f(x + 13) + ' ' + f(y - h * 0.6) + ' ' + f(x) + ' ' + f(y - h) + 'Z';
    return C.shadowEll(x + 3, y, 10, 3.5, 8, S) + ln(x, y, x, y - 6, S.umber, 2.6) + path(d, S.navy2, G, LW) +
      path('M' + f(x - 1) + ' ' + f(y - h + 4) + 'C' + f(x - 9) + ' ' + f(y - h * 0.6) + ' ' + f(x - 7) + ' ' + f(y - 10) + ' ' + f(x - 1) + ' ' + f(y - 7) + 'Z', S.teal, null, 0) +
      lines([[x - 5, y - h * 0.7, x + 1, y - h * 0.62], [x - 6, y - h * 0.45, x + 2, y - h * 0.38], [x - 5, y - h * 0.22, x + 3, y - h * 0.16]], G2, 0.8, 0.7);
  }
  def({
    kind: 'graveyard_charity', idKind: 'cemetery', facility: 'cemetery', variant: 1, w: 3, d: 2, up: 56,
    tags: ['earth_mounds', 'stele', 'pine', 'cypress', 'incense_burner', 'low_wall'], roof: 'none',
    note: '义冢：三面灰瓦压顶的矮石墙围出一片坟地，正中一通螭首大碑（台座上刻竖行朱字）、碑前三足香炉冒香烟；碑两侧与前方五座带石圈的土坟，各立一方小碑；左后古松、右后侧柏。前沿敞开不设门，散落几枚纸钱。',
    draw: function (W, D, r, id) {
      var o = '';
      o += pad(2, 6, 142, 94, '#cdb57c');
      // 后墙 + 两侧墙（矮，灰瓦压顶）
      o += C.box(4, 6, 140, 12, 9, S.gray, S.stone, G, LD) + C.brick(4, 3, 140, 12, 3, 10, S.umber, 0.4);
      o += lines([[4, -3, 140, -3]], S.gray2, 1.6);
      // 松柏（后排）
      o += pine(22, 30, 1) + cypress(126, 30, 40);
      // 大碑 + 香炉
      o += stele(72, 34, 16, 30, true);
      o += C.frustum(72, 44, 4.5, 1.8, 6, 2.4, 5, S.ochre, S.umber2, G, LD) + lines([[68, 44, 67, 47], [76, 44, 77, 47], [72, 45, 72, 48]], S.umber, 1.2) +
        lines([[70, 38, 70, 33], [72, 38, 72, 31], [74, 38, 74, 33]], S.umber, 0.7);
      o += path('M72 30q-3 -5 0 -9q3 -4 0 -9', null, S.cream2, 1.2, 'stroke-opacity="0.9"');
      // 土坟：后两座、前三座
      [[44, 46, 12], [102, 46, 12], [24, 74, 13], [72, 78, 14], [120, 74, 13]].forEach(function (m, k) {
        o += stele(m[0], m[1] - m[2] * 0.42, 6, 10, false);
        o += mound(m[0], m[1] + 4, m[2]);
      });
      // 侧墙前段（压在坟前，短截）
      o += C.box(2, 12, 6, 60, 8, S.gray2, S.stone, G, LD) + C.box(138, 12, 142, 60, 8, S.gray2, S.stone, G, LD);
      // 纸钱
      [[50, 90], [92, 92], [60, 66], [100, 64]].forEach(function (p) { o += circ(p[0], p[1], 2, S.cream2, G, 0.6) + rect(p[0] - 0.6, p[1] - 0.6, 1.2, 1.2, S.umber, null, 0); });
      return o;
    }
  });

  // ================= 桥一：石拱桥（驼峰单孔，桥面东西向） =================
  def({
    kind: 'bridge_hump_arch', idKind: 'bridge', facility: 'bridge', variant: 1, w: 3, d: 1, up: 46,
    tags: ['stone_arch', 'hump', 'steps', 'deck_ew', 'river_ns', 'span_1'], roof: 'none',
    note: '驼峰式单孔石拱桥。桥面东西走向、跨南北流向的河：放在河道瓦片上时，中间一格是水、东西两格搭在两岸。正面（南）看到近半圆的拱券、券脸石与倒影线，桥面是一级级石阶，两侧石栏带望柱，桥头抱鼓石。',
    draw: function (W, D, r, id) {
      var o = '', N = 32, By = 8, Fy = D - 6;
      function h(x) { return 5 + 30 * Math.pow(Math.sin(Math.PI * x / W), 1.3); }
      function curve(y0, dy, rev) { var a = []; for (var i = 0; i <= N; i++) { var x = W * i / N; a.push([x, y0 - h(x) + dy]); } return rev ? a.reverse() : a; }
      o += poly([[W * 0.28, D - 2], [W * 0.78, D - 2], [W * 0.74, D + 4], [W * 0.32, D + 4]], S.shadow, null, 0, fop(S.sop));
      // 后栏
      o += poly(curve(By, -7).concat(curve(By, 0, true)), S.stone2, G, LD);
      // 桥面 + 石阶
      o += poly(curve(By, 0).concat(curve(Fy, 0, true)), S.cream, G, LW);
      var st = [];
      for (var x = 6; x < W - 4; x += 6) { if (Math.abs(x - W / 2) < 10) continue; st.push([x, By - h(x), x, Fy - h(x)]); }
      o += lines(st, S.stone2, 1, 0.9);
      // 正面：拱券挖空
      var R = W * 0.25, cx = W / 2, RY = R * 0.98, top = curve(Fy, -7);
      var fd = 'M0 ' + f(D) + top.map(function (p) { return 'L' + f(p[0]) + ' ' + f(p[1]); }).join('') + 'L' + f(W) + ' ' + f(D) + 'L' + f(cx + R) + ' ' + f(D) +
        'A' + f(R) + ' ' + f(RY) + ' 0 0 0 ' + f(cx - R) + ' ' + f(D) + 'Z';
      var arch = 'M' + f(cx - R) + ' ' + f(D) + 'A' + f(R) + ' ' + f(RY) + ' 0 0 1 ' + f(cx + R) + ' ' + f(D) + 'Z';
      o += path(arch, S.water, null, 0) + C.clip(id + '-a', path(arch, '#000'),
        rect(cx - R, D - RY - 2, R * 2, RY * 0.5, S.navy2, null, 0, fop(0.8)) +
        lines([[cx - R * 0.6, D - 4, cx - R * 0.1, D - 4], [cx + R * 0.15, D - 8, cx + R * 0.55, D - 8], [cx - R * 0.3, D - 12, cx + R * 0.2, D - 12]], S.cream2, 1, 0.9));
      o += path(fd, S.stone, G, LW);
      o += C.clip(id + '-f', path(fd, '#000'), C.brick(0, -40, W, D, 4.5, 12, S.umber, 0.4) +
        poly([[W * 0.62, -40], [W, -40], [W, D], [W * 0.75, D]], S.stone2, null, 0, fop(0.5)));
      // 券脸石：放射缝 + 外圈
      var vs = [];
      for (var k = 0; k <= 14; k++) {
        var a = Math.PI * k / 14, c = Math.cos(a), sn = Math.sin(a);
        vs.push([cx - c * R, D - sn * RY, cx - c * (R + 7), D - sn * (RY + 7)]);
      }
      o += lines(vs, G, 1, 0.9) + path('M' + f(cx - R - 7) + ' ' + f(D) + 'A' + f(R + 7) + ' ' + f(RY + 7) + ' 0 0 1 ' + f(cx + R + 7) + ' ' + f(D), null, G, 1.3);
      o += path(arch, null, G, LW) + path(fd, null, G, LW);
      // 拱顶龙门石
      o += rect(cx - 4, D - RY - 8, 8, 9, S.cream2, G, LD);
      // 前栏：栏板 + 望柱
      o += poly(curve(Fy, -7).concat(curve(Fy, -1, true)), S.cream2, G, LD);
      for (var px = 12; px < W - 6; px += 15) {
        var py = Fy - h(px);
        o += rect(px - 1.6, py - 11, 3.2, 10, S.cream, G, 0.9) + circ(px, py - 11.5, 2, S.cream2, G, 0.8);
      }
      // 抱鼓石
      [[4, 1], [W - 4, -1]].forEach(function (p) { var y = Fy - h(p[0]) - 3; o += circ(p[0], y, 4, S.stone, G, LD) + circ(p[0], y, 1.6, 'none', G, 0.7); });
      return o;
    }
  });

  // ================= 桥二：廊桥（桥面南北向，长廊瓦顶 + 中亭） =================
  def({
    kind: 'bridge_covered', idKind: 'bridge', facility: 'bridge', variant: 2, w: 1, d: 3, up: 66,
    tags: ['covered_bridge', 'gallery', 'pavilion', 'deck_ns', 'river_ew'], roof: 'gable_tile',
    note: '廊桥。桥面南北走向、跨东西流向的河：放在河道瓦片上时，中间一格是水、南北两格落在两岸。斜俯视下看到一条南北向的长廊灰瓦顶，中段横架一座青绿歇山小亭（宝葫芦顶），南端廊口朱柱、匾额与下岸石阶；廊身投影落在右侧水面上。',
    draw: function (W, D, r, id) {
      var o = '', x0 = 9, x1 = 39, y0 = 4, y1 = 132, h = 24, rh = 12;
      // 投影（压在右侧水面上）
      o += poly([[x1, y0], [x1 + 8, y0 + 4], [x1 + 8, y1 + 4], [x0 + 4, y1 + 4], [x0 + 4, y1]], S.shadow, null, 0, fop(S.sop));
      // 南端石阶（廊口下岸）
      o += rect(x0 + 2, y1, x1 - x0 - 4, 12, S.stone, G, LD);
      for (var i = 0; i < 3; i++) o += ln(x0 + 3, y1 + 3 + i * 3.4, x1 - 3, y1 + 3 + i * 3.4, S.stone2, 1);
      // 长廊屋顶（两坡，屋脊南北向）
      var g = C.gableNS(x0, y0, x1, y1, h, rh, { wall: S.cream, roofL: S.gray2, roofR: S.gray, ink: G, lw: LW, ov: 4 });
      o += g.s;
      o += C.clip(id + '-rl', poly(g.L, '#000'), C.planks(x0 - 6, y0 - h - rh, (x0 + x1) / 2, y1, 4.5, false, S.cream2, 0.55));
      o += C.clip(id + '-rr', poly(g.R, '#000'), C.planks((x0 + x1) / 2, y0 - h - rh, x1 + 6, y1, 4.5, false, S.gray2, 0.7));
      o += ln(g.apex[0], y0 - h - rh, g.apex[0], g.apex[1], S.navy, 2.6);
      // 廊口：深色门洞里看到桥面纵深，朱柱、匾额
      var wy = y1 - h;
      o += rect(x0 + 3, wy + 4, x1 - x0 - 6, h - 4, S.navy, G, LD) + poly([[x0 + 9, y1], [x1 - 9, y1], [(x0 + x1) / 2 + 2, wy + 8], [(x0 + x1) / 2 - 2, wy + 8]], S.navy2, null, 0);
      o += lines([[x0 + 3, y1 - 6, x1 - 3, y1 - 6]], S.vermil, 1.6);
      o += pillar(x0 + 2, wy, y1, 3) + pillar(x1 - 2, wy, y1, 3);
      o += rect((x0 + x1) / 2 - 7, wy - 6, 14, 6, S.navy, G2, 0.9) + lines([[(x0 + x1) / 2 - 4, wy - 3, (x0 + x1) / 2 + 4, wy - 3]], G2, 0.8);
      o += lines([[x0, wy, (x0 + x1) / 2, g.gableApex[1] + 2], [x1, wy, (x0 + x1) / 2, g.gableApex[1] + 2]], S.umber, 1.2, 0.7);
      // 中亭：横跨长廊的青绿歇山小顶，坐在中间一格（水面）上
      var ty = 92;
      o += C.box(x0 - 2, ty - 26, x1 + 2, ty - 20, 14, S.cream2, S.cream, G, LD);
      o += pillar(x0, ty - 34, ty - 20, 2.6) + pillar(x1, ty - 34, ty - 20, 2.6);
      o += eaveRoof(id + '-p', x0 - 2, x1 + 2, ty - 58, ty - 32, 6, S.teal, S.teal2, 6);
      o += C.frustum((x0 + x1) / 2, ty - 60, 2.6, 1, 1.4, 0.6, 3, S.ochre, null, G, 0.8) + circ((x0 + x1) / 2, ty - 66, 3, S.ochre, G, 0.9) + circ((x0 + x1) / 2, ty - 71, 2, S.ochre, G, 0.8);
      return o;
    }
  });

  var api = { defs: defs, style: S, eaveRoof: eaveRoof, pillar: pillar };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.TownArtInfraEast = api;
})(typeof window !== 'undefined' ? window : this);
