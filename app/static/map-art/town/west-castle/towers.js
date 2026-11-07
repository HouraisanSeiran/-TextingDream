/*
 * 织梦 · 西式城堡 —— 塔楼（幕墙叠加件）、城门楼（gate-h / gate-v）、吊桥（放下 / 收起）。尚未接入游戏。
 * 返回格式同 keep.js；内部 clipPath id 用 "__ID__" 占位。
 *
 * 放置约定（与 preview.js 的示范城堡一致）：
 *   塔楼占地 3×3，中格对准幕墙拐角 / 端点那一格；
 *   gate-h 占地 3×2，中列对准东西向墙段的门洞格，第 1 行是墙格，第 2 行是墙外护坡；
 *   gate-v 占地 2×3，中行对准南北向墙段的门洞格，第 1 列是墙格，城门朝东（第 2 列一侧）；
 *   吊桥 ns 占地 1×2（跨南北两格宽的护城河），ew 占地 2×1。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWC.core;
  var KP = isNode ? require('./keep.js') : root.TownArtWC.keep;
  var PAL = C.PAL, rect = C.rect, path = C.path, seg = C.seg, lines = C.lines, poly = C.poly, f = C.f, P = C.P;

  function rec(id, kind, facility, variant, fp, up, tags, roof, note, body) {
    return { id: id, category: 'castle', kind: kind, facility: facility, variant: variant, footprint: fp, up: up, tags: tags, roof: roof, note: note, body: body };
  }

  /** 圆塔身：勒脚 + 塔身 + 托臂突堞 + 腰线 + 箭窗 + 塔顶女墙。返回 { svg, yt, ry }（yt = 女墙顶椭圆中心）。 */
  function roundBody(up, cx, cg, r, h, ph, slits) {
    var ry = r * C.K, o = '';
    var pl = C.cylinder(up, cx, cg, r + 3, 0, 9, PAL.st3, false);
    o += pl.svg + C.ell(cx, pl.yt, r + 3, (r + 3) * C.K, PAL.st3, 1.1);
    var cyl = C.cylinder(up, cx, cg, r, 6, h + ph, PAL.st2);
    o += cyl.svg;
    var mb = '', y0 = cyl.yt + ph;
    for (var a = 0.1; a < Math.PI; a += 0.24) {
      var x = cx - r * Math.cos(a), y = y0 + ry * Math.sin(a), w = 3.8 * Math.max(0.35, Math.sin(a));
      mb += C.rectD(x - w / 2, y, w, 5);
    }
    var band = 'M' + P(cx - r, y0) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 0 ' + P(cx + r, y0) +
      'L' + P(cx + r, y0 + 5) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 1 ' + P(cx - r, y0 + 5) + 'Z';
    o += path(band, PAL.hole, 1) + path(mb, PAL.st1, 0.6);
    var ys = cyl.yt + Math.round(h * 0.5);
    o += path('M' + P(cx - r, ys) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 0 ' + P(cx + r, ys), 'none', 1.2);
    (slits || [[-0.45, 16, true], [0.3, 16, true], [-0.05, h * 0.5 + 10, false]]).forEach(function (s) {
      var xx = cx + r * s[0], yy = cyl.yt + ry * Math.sqrt(1 - s[0] * s[0]) + s[1];
      o += C.arrowSlit(xx, yy, s[2] ? 14 : 12, s[2]);
    });
    o += C.roundTop(cx, cyl.yt, r, ph, PAL.plaster);
    return { svg: o, yt: cyl.yt, ry: ry };
  }

  /** 坐在女墙内圈上的锥顶：裁掉前沿女墙顶线以下的部分，让前面一圈垛口挡住锥顶脚。 */
  function roofCone(cx, yt, r, ph, hh, tag, pennant) {
    var ry = r * C.K, cb = yt + ph - 1;
    var cd = 'M' + P(cx - r - 8, yt - 220) + 'L' + P(cx - r - 8, yt) + 'L' + P(cx - r, yt) +
      'A' + f(r) + ' ' + f(ry) + ' 0 0 0 ' + P(cx + r, yt) + 'L' + P(cx + r + 8, yt) + 'L' + P(cx + r + 8, yt - 220) + 'Z';
    var o = C.clip('__ID__cone' + tag, cd, C.cone(cx, cb, r - 4, hh, PAL.sl1));
    if (pennant) o += C.flag(cx, cb - hh + 1, pennant[0], pennant[1], pennant[2]);
    else o += C.ell(cx, cb - hh, 1.6, 1.6, PAL.wash, 0.8);
    return o;
  }

  /** 圆塔：3×3，塔身直径 1.4 格；托臂突堞、箭窗、垛口女墙、青石板锥顶 + 旗。 */
  function roundTower() {
    var up = 104, cx = 72, cg = 72, r = 34, h = 96, ph = 8, o = '';
    o += C.shadow(C.ellD(cx + 6, up + cg + 3, r + 5, (r + 5) * C.K));
    var t = roundBody(up, cx, cg, r, h, ph);
    o += t.svg + roofCone(cx, t.yt, r, ph, 44, 'a', [22, 1, 0.9]);
    return rec('west-common-tower-round-01', 'tower_round', 'watchtower', 1, [3, 3], up,
      ['tower', 'round', 'wall_overlay', 'corner', 'crenellated', 'conical_roof', 'flag'], 'steep_slate',
      '幕墙拐角 / 端点叠加件：塔心对准占地中格（即墙格中心）；锥顶青石板', o);
  }

  /** 方塔：3×3，方台 1.5 格；转角隅石、托臂突堞、十字箭窗、勒脚、屋顶楼梯小塔 + 旗。 */
  function squareTower() {
    var up = 100, x0 = 36, x1 = 108, g0 = 36, g1 = 108, h = 94, ph = 8, o = '';
    var yb = up + g1;
    o += C.dropShadow(x0, x1, up + g0 - h - ph, yb, 144, up + 144);
    var k = C.crenBox(up, x0, x1, g0, g1, 0, h, { ph: ph, e: 6, cut: 5, shade: 0.22, deck: { seed: 17, hatch: [62, 86], plinth: [84, up + 76 - h] } });
    o += k.svg;
    var fy = k.front + ph;
    o += KP.corbelBand(x0, x1, fy, 5, 8);
    // 转角隅石：长短交替
    for (var y = fy + 6, n = 0; y < yb - 12; y += 8, n++) {
      var w = n % 2 ? 10 : 6;
      o += rect(x0, y, w, 8, PAL.st1, 0.7, 0.8) + rect(x1 - w, y, w, 8, PAL.st1, 0.7, 0.8);
    }
    var s1 = fy + 36;
    o += path(seg(x0, s1, x1, s1), 'none', 1.3);
    [56, 88].forEach(function (x) { o += C.arrowSlit(x, fy + 12, 15, true); });
    o += C.arrowSlit(72, s1 + 10, 14, false);
    o += poly([[x0 - 4, yb], [x1 + 4, yb], [x1 + 1, yb - 10], [x0 - 1, yb - 10]], PAL.st3, 1.3);
    o += lines(C.hatchD(x0, x1, yb - 9.5, yb - 0.5, 12), 0.8, 0.4);
    // 屋顶：后左楼梯小塔 + 中央旗杆
    o += C.crenBox(up, x0, x0 + 22, g0, g0 + 22, h, h + 14, { ph: 6, e: 3, cut: 3.5, shade: 0.3 }).svg;
    o += C.flag(84, up + 76 - h, 36, 1, 1);
    return rec('west-common-tower-square-01', 'tower_square', 'watchtower', 1, [3, 3], up,
      ['tower', 'square', 'wall_overlay', 'corner', 'crenellated', 'flag'], 'none',
      '幕墙拐角 / 端点叠加件：方台中心对准占地中格；平顶垛口，无对应 RoofId 填 none', o);
  }

  // ======================= 城门楼 =======================
  /**
   * D 形塔：后半是方台（gBack..cg），前半是圆柱（中心 cg，半径 r），顶部 D 形女墙 + 凹下平台。
   * 用于城门楼两侧夹门的塔。tag 用来区分 clipPath id。
   */
  function dTower(up, cx, cg, r, gBack, H, ph, tag, slits) {
    var ry = r * C.K, x0 = cx - r, x1 = cx + r, o = '';
    var cyl = C.cylinder(up, cx, cg, r, 0, H, PAL.st2);
    o += cyl.svg;
    // 托臂突堞带 + 腰线 + 箭窗
    var y0 = cyl.yt + ph, mb = '';
    for (var a = 0.12; a < Math.PI; a += 0.3) {
      var x = cx - r * Math.cos(a), y = y0 + ry * Math.sin(a), w = 3.6 * Math.max(0.35, Math.sin(a));
      mb += C.rectD(x - w / 2, y, w, 5);
    }
    o += path('M' + P(x0, y0) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 0 ' + P(x1, y0) + 'L' + P(x1, y0 + 5) +
      'A' + f(r) + ' ' + f(ry) + ' 0 0 1 ' + P(x0, y0 + 5) + 'Z', PAL.hole, 1) + path(mb, PAL.st1, 0.6);
    var ys = cyl.yt + Math.round(H * 0.55);
    o += path('M' + P(x0, ys) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 0 ' + P(x1, ys), 'none', 1.2);
    (slits || [[0, 18, true], [0, H * 0.55 + 10, false]]).forEach(function (s) {
      var xx = cx + r * s[0], yy = cyl.yt + ry * Math.sqrt(1 - s[0] * s[0]) + s[1];
      o += C.arrowSlit(xx, yy, s[2] ? 14 : 12, s[2]);
    });
    // D 形顶
    var yt0 = up + gBack - H, yE = cyl.yt, e = 4.5, ri = r - e, ryi = ri * C.K;
    var topD = 'M' + P(x0, yt0) + 'L' + P(x1, yt0) + 'L' + P(x1, yE) + 'A' + f(r) + ' ' + f(ry) + ' 0 0 1 ' + P(x0, yE) + 'Z';
    var inD = 'M' + P(x0 + e, yt0 + e) + 'L' + P(x1 - e, yt0 + e) + 'L' + P(x1 - e, yE) + 'A' + f(ri) + ' ' + f(ryi) + ' 0 0 1 ' + P(x0 + e, yE) + 'Z';
    o += path(topD, PAL.st1, 1.3) + path(inD, PAL.st3, 0.9);
    // 台面：错缝石板 + 女墙阴影（左塔加一个楼梯口），整体下移 ph 露出女墙内侧
    var deckIn = C.deck(x0 + e, x1 - e, yt0 + e, yE + ryi, 41 + tag.charCodeAt(0), tag === 'l' ? { hatch: [cx - 6, yt0 + e + 16] } : {});
    o += C.clip('__ID__dt' + tag, inD, '<g transform="translate(0 ' + ph + ')">' + deckIn + path(inD, 'none', 0.8) + '</g>');
    o += C.crenelNotches(x0 + e, x1 - e, yt0 - 0.2, 2.2, 12, 7, PAL.st3);
    for (var yy2 = yt0 + e + 6; yy2 < yE - 3; yy2 += 12) o += rect(x0 + 0.6, yy2, e - 1.2, 5, PAL.st3, 0.6, 0.7) + rect(x1 - e + 0.6, yy2, e - 1.2, 5, PAL.st3, 0.6, 0.7);
    var n = 7;
    for (var i = 0; i < n; i += 2) {
      var aa = Math.PI * (i + 0.5) / n, xf = cx - r * Math.cos(aa), wd = Math.max(1.6, 4.2 * Math.sin(aa));
      o += rect(xf - wd / 2, yE + ry * Math.sin(aa) - 0.6, wd, 4.2, PAL.plaster, 0.8);
    }
    return { svg: o, yt0: yt0, yE: yE };
  }

  /** 门洞：石券框 + 券石放射缝 + 深色门洞 + 半升起的吊闸 + 门洞里的地面。 */
  function gateArch(x, gy, w, h, tag) {
    var o = path(C.archD(x - 3, gy - h - 3, w + 6, h + 3), PAL.st1, 1.1), r = w / 2 + 1.5, cx = x + w / 2, cy = gy - h + w / 2, vd = '';
    for (var a = 0.2; a < Math.PI - 0.1; a += 0.42) vd += seg(cx - r * Math.cos(a), cy - r * Math.sin(a), cx - (r + 3) * Math.cos(a), cy - (r + 3) * Math.sin(a));
    o += lines(vd, 0.8, 0.6);
    var hd = C.archD(x, gy - h, w, h);
    o += path(hd, PAL.hole, 1.2);
    o += C.clip('__ID__ga' + tag, hd, rect(x, gy - 9, w, 9, PAL.st3, 0) + lines(seg(x, gy - 5, x + w, gy - 5), 0.7, 0.4) +
      C.portcullis(x + 2, x + w - 2, gy - h - 2, gy - 15, 5));
    return o;
  }

  /** 城门楼（东西向墙段）：3×2。中间门楼带吊闸门洞、突堞箱、吊桥链孔；两侧 D 形塔；门前石板坡道。 */
  function gatehouseH() {
    var up = 124, o = '', gy = up + 58;
    o += C.dropShadow(4, 140, up - 100, up + 92, 144, up + 96);
    // 门前坡道（地面）
    o += rect(46, up + 56, 52, 40, PAL.st1, 1) + lines(C.ashlarD(46, up + 56, 52, 40, 10, 13, 0, 0), 0.8, 0.45);
    var k = C.crenBox(up, 34, 110, 0, 58, 0, 84, { ph: 8, e: 5, cut: 5, deck: { seed: 23, plinth: [72, up + 29 - 84] } });
    o += k.svg;
    o += gateArch(57, gy, 30, 48, 'h');
    // 突堞箱（门洞正上方，往门外投石）+ 两个吊桥链孔
    o += KP.corbelBand(58, 86, gy - 66, 5, 7) + rect(56, gy - 78, 32, 12, PAL.st1, 1) + C.crenelNotches(56, 88, gy - 78, 3, 8, 4, PAL.st3);
    o += C.ell(58, gy - 56, 2, 2, PAL.hole, 0.8) + C.ell(86, gy - 56, 2, 2, PAL.hole, 0.8);
    o += C.flag(72, up + 29 - 84, 40, 1, 1.1);
    o += dTower(up, 24, 66, 24, 0, 104, 8, 'l').svg + dTower(up, 120, 66, 24, 0, 104, 8, 'r').svg;
    o += C.shield(72, gy - 90, 4.5, PAL.red, 'cross');
    return rec('west-common-gatehouse-h', 'gatehouse', 'gate', 1, [3, 2], up,
      ['gatehouse', 'gate-h', 'wall_overlay', 'portcullis', 'machicolation', 'twin_towers', 'flag'], 'none',
      '东西向幕墙的城门楼：占地 3×2，第 1 行压在墙格上（中列为门洞格），第 2 行是墙外护坡；吊闸半升；链孔与 drawbridge-ns 对齐', o);
  }

  /**
   * 城门楼（南北向墙段，门朝东）：2×3。北塔、门楼、南塔；斜俯视下朝东的门面本应看不见，
   * 这里按规范「侧面只露一窄条」画一条 10 px 宽的东立面，里面是窄拱门洞与吊闸横档。
   */
  /** 侧立面窄条顶上的女墙垛：沿右沿每 12 px 一个凸垛（俯看侧面的垛口）。 */
  function crenStrip(x0, x1, yTop) {
    var o = rect(x0, yTop, x1 - x0, 8, PAL.st1, 1);
    for (var y = yTop + 10; y < yTop + 100; y += 12) o += rect(x1 - 5, y, 5, 6, PAL.st1, 0.8) + rect(x1 - 5, y + 6, 5, 6, PAL.st3, 0.6, 0.7);
    return o;
  }

  function gatehouseV() {
    var up = 130, o = '';
    o += C.dropShadow(2, 80, up - 96, up + 136, 96, up + 144);
    // 门前石板坡道：从东立面一直铺到占地东沿（护城河岸），宽度 = 门洞格
    o += rect(74, up + 50, 22, 46, PAL.st1, 1) + lines(C.ashlarD(74, up + 50, 22, 46, 9, 11, 0, 0), 0.8, 0.45);
    o += lines(seg(74, up + 50, 96, up + 50), 1.2, 0.8);
    // 北塔（在主体后面，先画，塔顶高出主体）
    var nt = roundBody(up, 30, 22, 22, 100, 8, [[-0.35, 16, true], [0.3, 50, false]]);
    o += nt.svg;
    // 门楼主体（压在墙格上），台面铺石板 + 旗杆座
    var k = C.crenBox(up, 2, 58, 18, 126, 0, 80, { ph: 8, e: 5, cut: 5, deck: { seed: 29, hatch: [12, up - 44], plinth: [36, up - 22] } });
    o += k.svg + C.flag(36, up - 22, 36, 1, 1.05);
    // ---- 东立面（规范：侧面只露一窄条，这里放宽到 18 px 好放门洞）
    var sx0 = 58, sx1 = 76, sy0 = up + 18 - 88, sy1 = up + 126;
    o += rect(sx0, sy0, sx1 - sx0, sy1 - sy0, PAL.st3, 1.2) + lines(C.rowsD(sx0, sx1, sy0, sy1, 8, 9, 5), 0.7, 0.4);
    o += lines(C.hatchD(sx0 + 12, sx1, sy0 + 2, sy1 - 2, 3), 0.6, 0.3);
    o += crenStrip(sx0, sx1, sy0);
    // 突堞箱（门洞正上方，向东挑出）
    var mY = up + 4;
    o += rect(sx0 - 1, mY, sx1 - sx0 + 6, 13, PAL.st1, 1.1) + C.crenelNotches(sx0 - 1, sx1 + 5, mY, 3, 7, 4, PAL.st3);
    for (var cy = mY + 13, cx2 = sx0 + 2; cx2 < sx1 + 4; cx2 += 5) o += path('M' + P(cx2, cy) + 'L' + P(cx2 + 3, cy) + 'L' + P(cx2 + 1.5, cy + 4) + 'Z', PAL.st1, 0.7);
    // 门洞：券石框 → 外层暗口 → 侧壁（左亮右暗的两条内壁）→ 最深处暗洞 → 洞内地面 → 半升吊闸
    var ax0 = sx0 + 1, ax1 = sx1 - 1, aTop = up + 30, aBot = up + 96, aw = ax1 - ax0;
    o += path(C.archD(ax0 - 1.5, aTop - 2, aw + 3, aBot - aTop + 2), PAL.st1, 1.1);
    var hole = C.archD(ax0 + 1, aTop, aw - 2, aBot - aTop);
    o += path(hole, PAL.hole, 1.3);
    var inner = '';
    inner += rect(ax0 + 1, aTop, 3.5, aBot - aTop, PAL.st2, 0) + lines(C.rowsD(ax0 + 1, ax0 + 4.5, aTop, aBot, 6, 0, 2), 0.6, 0.5);
    inner += rect(ax1 - 4.5, aTop, 3.5, aBot - aTop, PAL.grain, 0).replace('/>', ' fill-opacity="0.55"/>');
    inner += path(C.archD(ax0 + 4.5, aTop + 9, aw - 9, aBot - aTop - 9), '#2f241a', 0.8);
    inner += rect(ax0 + 1, aBot - 10, aw - 2, 10, PAL.st3, 0) + lines(seg(ax0 + 1, aBot - 6, ax1 - 1, aBot - 6), 0.6, 0.5);
    inner += C.portcullis(ax0 + 1.5, ax1 - 1.5, aTop - 2, aTop + 30, 3);
    o += C.clip('__ID__gvm', hole, inner) + path(hole, 'none', 1.3);
    // 吊桥链孔 + 链（与 drawbridge-ew 西端 h=60 处接上）
    [0, 24].forEach(function (dy) {
      o += C.ell(sx1 - 3, up + dy - 6, 1.7, 1.7, PAL.hole, 0.7) +
        path('M' + P(sx1 - 3, up + dy - 6) + 'Q' + P(88, up + dy) + ' ' + P(96, up + dy), 'none', 1.3, 0.9, ' stroke-dasharray="2.2 1.2"');
    });
    o += C.shield(sx0 + 9, up - 12, 4, PAL.red, 'cross');
    // 南塔（最前，后画）
    var stl = roundBody(up, 30, 120, 22, 100, 8, [[-0.4, 16, true], [0.3, 16, true], [0, 50, false]]);
    o += stl.svg;
    return rec('west-common-gatehouse-v', 'gatehouse', 'gate', 2, [2, 3], up,
      ['gatehouse', 'gate-v', 'wall_overlay', 'portcullis', 'twin_towers', 'flag'], 'none',
      '南北向幕墙的城门楼（门朝东）：占地 2×3，第 1 列压在墙格上（中行为门洞格），第 2 列是墙外护坡；东立面按规范只露一窄条；链在东沿 h=60 处与 drawbridge-ew 接上', o);
  }

  // ======================= 吊桥 =======================
  function chain(x1, y1, x2, y2, sag) {
    return path('M' + P(x1, y1) + 'Q' + P((x1 + x2) / 2, (y1 + y2) / 2 + (sag || 3)) + ' ' + P(x2, y2), 'none', 1.3, 0.9, ' stroke-dasharray="2.2 1.2"');
  }
  /** 南北向吊桥（跨 2 格宽护城河）：1×2。down=放下（桥面 + 铁箍 + 两条链拉向城门楼链孔），否则收起（桥板竖起挡住门洞）。 */
  function bridgeNS(down) {
    var up = 100, o = '', x0 = 9, x1 = 39;
    o += rect(x0 - 2, up - 4, x1 - x0 + 4, 5, PAL.st1, 1);   // 门槛石
    if (down) {
      o += C.shadow(C.rectD(x1, up + 4, 6, 90));
      o += rect(x0, up + 90, x1 - x0, 4, PAL.dark, 1.1);
      o += rect(x0, up - 4, x1 - x0, 94, PAL.wood, 1.3);
      o += lines(C.rowsD(x0, x1, up - 4, up + 90, 4.5, 0, 1), 0.7, 0.45);
      o += rect(x0, up - 4, 3, 94, PAL.grain, 0.8) + rect(x1 - 3, up - 4, 3, 94, PAL.grain, 0.8);
      for (var y = up + 14; y < up + 90; y += 24) o += path(seg(x0, y, x1, y), 'none', 1.6, 0.85);
      o += chain(x0 + 2, up + 86, x0 + 1, up - 94, 2) + chain(x1 - 2, up + 86, x1 - 1, up - 94, 2);
    } else {
      o += rect(x0, up - 99, x1 - x0, 4, PAL.wood, 1);
      o += rect(x0, up - 96, x1 - x0, 94, PAL.wood, 1.3);
      o += rect(x0, up - 96, 3, 94, PAL.grain, 0.8) + rect(x1 - 3, up - 96, 3, 94, PAL.grain, 0.8);
      o += lines(C.hatchD(x0 + 3, x1 - 3, up - 95, up - 3, 4.5), 0.7, 0.4);
      for (var y2 = up - 84; y2 < up - 4; y2 += 18) o += path(seg(x0, y2, x1, y2), 'none', 1.8, 0.85);
      o += rect(x0 - 1, up - 6, x1 - x0 + 2, 4, PAL.dark, 1);
      o += C.ell(x0 + 3, up - 97, 1.4, 1.4, PAL.hole, 0.6) + C.ell(x1 - 3, up - 97, 1.4, 1.4, PAL.hole, 0.6);
    }
    return rec('west-common-drawbridge-ns-' + (down ? 'down' : 'up'), 'drawbridge', 'bridge', down ? 1 : 2, [1, 2], up,
      ['drawbridge', 'ns', down ? 'lowered' : 'raised', 'moat_overlay'], 'none',
      '南北向吊桥：放在 2 格宽护城河上，北端对准 gatehouse-h 的门洞；' + (down ? '放下状态，两条链拉向门楼链孔' : '收起状态，桥板竖起挡住门洞，下面露出水面'), o);
  }
  /** 东西向吊桥：2×1。西端对准 gatehouse-v 门洞；链在西沿 h=60 处接城门楼的链。 */
  function bridgeEW(down) {
    var up = 56, o = '', g0 = 10, g1 = 38;
    o += rect(0, up + g0 - 2, 5, g1 - g0 + 4, PAL.st1, 1);
    if (down) {
      o += C.shadow(C.rectD(4, up + g1 + 2, 90, 5));
      o += rect(2, up + g1 - 2, 92, 4, PAL.dark, 1.1);
      o += rect(2, up + g0 - 2, 92, g1 - g0, PAL.wood, 1.3);
      o += lines(C.hatchD(2, 94, up + g0 - 2, up + g1 - 2, 4.5), 0.7, 0.45);
      o += rect(2, up + g0 - 2, 92, 3, PAL.grain, 0.8) + rect(2, up + g1 - 5, 92, 3, PAL.grain, 0.8);
      for (var x = 20; x < 94; x += 24) o += path(seg(x, up + g0 - 2, x, up + g1 - 2), 'none', 1.6, 0.85);
      o += chain(90, up + g0, 0, up + g0 + 2 - 60, 4) + chain(90, up + g1 - 4, 0, up + g1 - 2 - 60 + 2, 4);
    } else {
      o += C.shadow(C.rectD(9, up + g0, 5, g1 - g0 + 4));
      o += rect(1, up + g0 - 96, 8, g1 - g0, PAL.wash, 1);              // 竖起桥板的顶端
      o += rect(1, up + g1 - 96, 8, 96, PAL.wood, 1.3);                 // 朝南的板端
      for (var y = up + g1 - 84; y < up + g1; y += 18) o += path(seg(1, y, 9, y), 'none', 1.6, 0.85);
      o += chain(5, up + g0 - 94, 0, up + g0 + 2 - 60, 1) + chain(5, up + g1 - 94, 0, up + g1 - 60, 1);
    }
    return rec('west-common-drawbridge-ew-' + (down ? 'down' : 'up'), 'drawbridge', 'bridge', down ? 3 : 4, [2, 1], up,
      ['drawbridge', 'ew', down ? 'lowered' : 'raised', 'moat_overlay'], 'none',
      '东西向吊桥：放在 2 格宽护城河上，西端对准 gatehouse-v 的门洞；' + (down ? '放下状态' : '收起状态（桥板侧对镜头，只见窄条与顶端）'), o);
  }

  function list() {
    return [roundTower, squareTower, gatehouseH, gatehouseV,
      function () { return bridgeNS(true); }, function () { return bridgeNS(false); },
      function () { return bridgeEW(true); }, function () { return bridgeEW(false); }];
  }

  var API = { roundBody: roundBody, dTower: dTower, gateArch: gateArch, roundTower: roundTower, squareTower: squareTower,
    gatehouseH: gatehouseH, gatehouseV: gatehouseV, bridgeNS: bridgeNS, bridgeEW: bridgeEW, list: list };
  if (isNode) module.exports = API;
  else { root.TownArtWC = root.TownArtWC || {}; root.TownArtWC.towers = API; }
})(this);
