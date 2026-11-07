/*
 * 织梦 · 西式文化地标：古罗马建筑（斗兽场、神庙、引水渠段落、公共浴场、凯旋门、广场柱廊）
 * draw(c) 的 c = { rnd, W, H, up, id }：占地区 y = up..H；锚点 (W/2, H)。
 * 浏览器挂 window.TownArtWL_roman；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var P = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWL_core;
  var C = P.C, f = P.f, seg = P.seg, ln = P.ln, rect = P.rect, poly = P.poly, path = P.path, flat = P.flat;
  var defs = [];
  function def(o) { defs.push(o); }
  var MARBLE = C.paper, TRAV = '#e6d6ae'; // 大理石、石灰华（纸色系）

  /** 前半椭圆弧（从左到右，经过前沿）：中心 cx,cy，半轴 rx,ry */
  function frontArc(cx, cy, rx, ry) { return 'M' + f(cx - rx) + ' ' + f(cy) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + rx) + ' ' + f(cy); }

  // ——————————————————— 圆形剧场 / 斗兽场 ———————————————————
  def({
    kind: 'amphitheatre', variant: 1, name: '圆形斗兽场', fp: [6, 5], up: 112, seed: 4101,
    facility: null, culture: 'roman', roof: 'none',
    tags: ['amphitheatre', 'arena', 'arcade', 'ellipse', 'four_storeys', 'velarium', 'roman', 'important'],
    note: '椭圆形四层外墙：下三层是连续拱券（每层拱间立半壁柱、层间檐口），第四层是开小方窗的实墙阁楼，檐上一圈遮阳篷桅杆；' +
      '从上方能看到内部一圈圈下降的看台与中央沙地竞技场，正中一道大拱门。FacilityKind 里没有剧场 / 竞技场，填 null',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, U = c.up, o = '';
      var cx = 144, rx = 138, ry = 106, cyB = U + 117, hh = 94, cyT = cyB - hh, tiers = [26, 24, 22], attic = hh - 72;
      // 投影
      o += flat([[cx - rx + 12, cyB + ry * 0.5], [cx + rx + 4, cyB - ry * 0.2], [cx + rx + 4, cyB + 8], [cx + 40, H - 1], [cx - 80, H - 2]], C.shadow, 0.18);
      // 顶面：外缘椭圆（墙顶）+ 内部看台环（向内逐级下降）+ 竞技场沙地
      o += P.ellipse(cx, cyT, rx, ry, TRAV, 1.8);
      var nRing = 7;
      for (var i = 0; i < nRing; i++) {
        var k = i + 1, rxi = rx - 7 - k * 10.5, ryi = ry - 7 - k * 7.8, cyi = cyT + k * 6.2;
        o += P.ellipse(cx, cyi, rxi, ryi, i % 2 ? C.stone : C.stone2, 1);
        // 看台座排：每环内再两道细弧线
        o += ln(frontArc(cx, cyi - 1.5, rxi - 4, ryi - 3) + 'M' + f(cx - rxi + 4) + ' ' + f(cyi - 1.5) + 'A' + f(rxi - 4) + ' ' + f(ryi - 3) + ' 0 0 1 ' + f(cx + rxi - 4) + ' ' + f(cyi - 1.5), 0.6, 0.4);
        // 走道竖线（vomitoria 方向）
        var vd = '';
        for (var a = 0; a < 12; a++) {
          var t = (a + 0.5) / 12 * Math.PI * 2, ca = Math.cos(t), sa = Math.sin(t);
          vd += seg(cx + ca * (rxi - 1), cyi + sa * (ryi - 1), cx + ca * (rxi - 9), cyi + sa * (ryi - 7));
        }
        if (i < nRing - 1) o += ln(vd, 0.7, 0.5);
      }
      var arx = rx - 7 - (nRing + 1) * 10.5, ary = ry - 7 - (nRing + 1) * 7.8, acy = cyT + (nRing + 1) * 6.2;
      o += P.ellipse(cx, acy, arx + 4, ary + 3, C.stone3, 1.3) + P.ellipse(cx, acy + 3, arx, ary, C.sand, 1.2);
      o += ln(seg(cx - arx * 0.5, acy + 3, cx + arx * 0.5, acy + 3) + seg(cx, acy + 3 - ary * 0.5, cx, acy + 3 + ary * 0.5), 0.8, 0.35);
      // 外墙内侧（后半圈露出的内壁）阴影带
      o += '<path d="M' + f(cx - rx + 5) + ' ' + f(cyT) + 'A' + f(rx - 5) + ' ' + f(ry - 5) + ' 0 0 1 ' + f(cx + rx - 5) + ' ' + f(cyT) +
        'A' + f(rx - 14) + ' ' + f(ry - 12) + ' 0 0 0 ' + f(cx - rx + 5) + ' ' + f(cyT) + 'Z" fill="' + C.shadow + '" fill-opacity="0.12"/>';
      // 外墙前半圈立面
      var band = 'M' + f(cx - rx) + ' ' + f(cyT) + 'L' + f(cx - rx) + ' ' + f(cyB) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + rx) + ' ' + f(cyB) +
        'L' + f(cx + rx) + ' ' + f(cyT) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 1 ' + f(cx - rx) + ' ' + f(cyT) + 'Z';
      o += path(band, TRAV, 1.9);
      // 各层：拱券 + 半壁柱 + 层间檐口
      var n = 22, base = 0, cl = '';
      tiers.forEach(function (th, k) {
        for (var j = 0; j < n; j++) {
          var t = Math.PI * (j + 0.5) / n, s = Math.sin(t), x = cx - rx * Math.cos(t), yb = cyB - base + ry * s;
          var w = Math.PI * rx / n * s * 0.6, ah = th - 6;
          if (w < 1.6) continue;
          var big = k === 0 && j === n / 2 - 0.5 ? 1 : 0;
          if (k === 0 && (j === 10 || j === 11)) { // 正门：两个拱位合成一道大拱
            if (j === 10) { var gx = cx, gw = w * 1.7; o += path(P.archPath(gx - gw / 2, yb - th + 1.5 + 2, gw, th - 2), C.dark, 1.3); }
            continue;
          }
          o += path(P.archPath(x - w / 2, yb - ah - 2, w, ah), k === 2 ? C.dark : '#5b442d', s > 0.35 ? 1.1 : 0.8);
          void big;
          // 拱间半壁柱（在拱与下一拱之间）
          var t2 = Math.PI * (j + 1) / n, x2 = cx - rx * Math.cos(t2), s2 = Math.sin(t2), yb2 = cyB - base + ry * s2;
          if (j < n - 1 && s2 > 0.2) cl += seg(x2, yb2 - 1, x2, yb2 - th + 2.5);
        }
        base += th;
        o += path(frontArc(cx, cyB - base, rx, ry) + 'L' + f(cx + rx) + ' ' + f(cyB - base + 2.6) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 1 ' + f(cx - rx) + ' ' + f(cyB - base + 2.6) + 'Z', C.stone, 1);
      });
      o += ln(cl, 1.6, 0.55);
      // 阁楼层：小方窗 + 托架
      var wd = '', md = '';
      for (var j2 = 0; j2 < 36; j2++) {
        var t3 = Math.PI * (j2 + 0.5) / 36, s3 = Math.sin(t3), x3 = cx - rx * Math.cos(t3), yb3 = cyB - base + ry * s3;
        if (s3 < 0.25) continue;
        if (j2 % 3 === 1) o += rect(x3 - 2.2 * s3, yb3 - attic * 0.62, 4.4 * s3, 6, C.dark, 0.8);
        md += seg(x3, yb3 - attic + 3, x3, yb3 - attic + 6);
      }
      o += ln(md, 1.1, 0.6) + ln(wd, 0.8, 0.5);
      // 外墙右侧阴面 + 顶缘线
      o += '<path d="M' + f(cx + rx * 0.55) + ' ' + f(cyT + ry * 0.835) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + rx) + ' ' + f(cyT) + 'L' + f(cx + rx) + ' ' + f(cyB) +
        'A' + f(rx) + ' ' + f(ry) + ' 0 0 1 ' + f(cx + rx * 0.55) + ' ' + f(cyB + ry * 0.835) + 'Z" fill="' + C.shadow + '" fill-opacity="0.13"/>';
      o += ln(frontArc(cx, cyT, rx, ry), 2, 1);
      // 遮阳篷桅杆
      var mast = '';
      for (var m = 0; m < 28; m++) {
        var tm = Math.PI * 2 * (m + 0.5) / 28, mx = cx - rx * Math.cos(tm) * 0.985, my = cyT + ry * Math.sin(tm) * 0.985;
        mast += seg(mx, my, mx, my - 9);
      }
      o += ln(mast, 1.3, 0.9, C.beam);
      // 正门前台阶
      o += rect(cx - 22, cyB + ry - 1, 44, 2.6, C.stone2, 1) + rect(cx - 26, cyB + ry + 1.6, 52, 2.6, C.stone3, 1);
      return o;
    }
  });

  /** 科林斯柱头：在 column() 之上加两层卷叶短线 */
  function corinth(cx, yt, r) {
    return ln(seg(cx - r * 1.2, yt + 2.2, cx - r * 0.5, yt + 5.5) + seg(cx + r * 1.2, yt + 2.2, cx + r * 0.5, yt + 5.5) + seg(cx, yt + 2.5, cx, yt + 5.5), 0.8, 0.6);
  }
  /** 铭文带：一排短竖划（拉丁大写字母的意思） */
  function inscription(x0, x1, y, h) {
    var d = '';
    for (var x = x0; x < x1; x += 2.6) if (((x * 7) | 0) % 5 !== 0) d += seg(x, y, x, y + h);
    return ln(d, 0.9, 0.6);
  }

  // ——————————————————— 罗马神庙：高台基、六柱前廊、三角山花 ———————————————————
  def({
    kind: 'roman_temple', variant: 1, name: '罗马神庙', fp: [3, 3], up: 104, seed: 4201,
    facility: 'temple', culture: 'roman', roof: 'gable_tile',
    tags: ['podium', 'hexastyle', 'portico', 'pediment', 'corinthian', 'inscription', 'roman', 'important'],
    note: '前廊式罗马神庙：高台基正面一道通宽台阶，两侧挡墙上各一座祭坛；六根科林斯柱撑起刻铭文的额枋与带浮雕的三角山花，' +
      '山花顶与两角立雕像；柱廊后是内殿墙与青铜大门，红瓦两坡顶顺进深伸向后方',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '';
      var px0 = 12, px1 = 132, ph = 24, yp = yf - ph, ch = 58, yE = yp - ch - 10, rise = 28, dg = 100;
      o += P.boxShadow(px0, px1, yf - 130, yf, 8, W, H);
      var g = P.gableFront(16, 128, yE, dg, rise, 'tile', { ov: 2, fill: MARBLE });
      o += g.roof;
      // 前廊地坪 + 内殿墙 + 大门
      o += rect(16, yp - 26, 112, 26, C.stone, 1.2);
      o += P.wall(30, 114, yE, yp - 24, 'ashlar', r, { fill: TRAV, ch: 7 });
      o += P.door(72, yp - 24, 22, 34, { shape: 'rect', frame: C.stone3, fill: C.beam });
      o += ln(seg(72, yp - 58, 72, yp - 25), 1, 0.7, C.dark);
      // 六柱
      for (var i = 0; i < 6; i++) { var x = 22 + i * 20; o += P.column(x, yp, ch, 4.4, { fill: MARBLE, ionic: true }) + corinth(x, yp - ch, 4.4); }
      // 额枋 + 铭文 + 山花
      o += rect(14, yE, 116, 10, MARBLE, 1.5) + ln(seg(15, yE + 3.4, 129, yE + 3.4), 0.8, 0.6) + inscription(36, 108, yE + 5, 3.4);
      o += P.pediment(16, 128, yE, rise, r, { relief: true, fill: MARBLE });
      // 雕像：山花顶 + 两角
      [[72, yE - rise - 1, 10], [17, yE - 2, 8], [127, yE - 2, 8]].forEach(function (s) {
        o += rect(s[0] - 2.6, s[1] - 3, 5.2, 3, C.stone2, 0.9) + path('M' + f(s[0] - 2) + ' ' + f(s[1] - 3) + 'L' + f(s[0] - 1.3) + ' ' + f(s[1] - s[2] + 2) +
          'Q' + f(s[0]) + ' ' + f(s[1] - s[2] - 1) + ' ' + f(s[0] + 1.3) + ' ' + f(s[1] - s[2] + 2) + 'L' + f(s[0] + 2) + ' ' + f(s[1] - 3) + 'Z', C.stone, 0.9);
      });
      // 台基正面 + 台阶 + 挡墙祭坛
      o += P.wall(px0, px1, yp, yf, 'ashlar', r, { fill: TRAV, ch: 6 }) + rect(px0 - 2, yp - 1, px1 - px0 + 4, 3.4, C.stone, 1.2);
      for (var k = 0; k < 6; k++) { var sy = yp + 2 + k * (ph - 2) / 6; o += rect(34, sy, 76, (ph - 2) / 6 + 0.4, k % 2 ? C.stone : C.stone2, 0.9); }
      [[px0, 34], [110, px1]].forEach(function (a) {
        o += rect(a[0], yp, a[1] - a[0], ph, C.stone2, 1.3) + P.box(a[0] + 4, a[1] - 4, yp, 5, 8, MARBLE, C.stone, 1) + P.circle((a[0] + a[1]) / 2, yp - 9.5, 1.6, C.tile, 0.6);
      });
      return o;
    }
  });

  // ——————————————————— 引水渠：可沿直线拼接的段落（1×1）与端头 ———————————————————
  // 统一尺寸（所有段落共用，拼接处高度对齐）：上伸 124；E-W 段正立面在格内进深 g=30，墙厚 10；
  // 三层拱：底层大拱（顶高 50）、中层拱（顶高 88）、顶层三联小拱（顶高 112），渠顶盖板 118。
  // 每格宽 48 = 一跨，拱墩中心在格的左右边上，石缝按 12 px 周期对齐，所以任意多格拼起来无缝。
  var AQ_UP = 124, AQ_G = 30, AQ_T = 10, AQ_CAP = 118;
  var AQ_O1 = [[6, 42]], AQ_O2 = [[7, 41]], AQ_O3 = [[3, 13], [19, 29], [35, 45]];
  function openArch(x0, x1, yTop, yBot) { // 不封底的半圆拱轮廓
    var r = (x1 - x0) / 2;
    return 'M' + f(x0) + ' ' + f(yBot) + 'L' + f(x0) + ' ' + f(yTop + r) + 'A' + f(r) + ' ' + f(r) + ' 0 0 1 ' + f(x1) + ' ' + f(yTop + r) + 'L' + f(x1) + ' ' + f(yBot);
  }
  /** E-W 走向的一段：结构横向 xa..xb；o1/o2/o3 三层拱洞 [x0,x1]；edgeL/edgeR 端头描边 */
  function aqEW(c, xa, xb, o1, o2, o3, edgeL, edgeR) {
    var U = c.up, yb = U + AQ_G, yT = U + AQ_G - AQ_T - AQ_CAP, yC = yb - AQ_CAP, o = '', holes = '', outl = '', vs = '';
    function Y(h) { return yb - h; }
    o += flat([[xa + (edgeL ? 4 : 0), yb], [xb, yb], [xb, yb + 5], [xa + (edgeL ? 8 : 0), yb + 5]], C.shadow, 0.18);
    // 渠顶盖板（顶面）+ 盖板缝
    o += rect(xa, yT, xb - xa, yC - yT, C.stone, 0);
    var sj = '';
    for (var x = Math.ceil(xa / 8) * 8; x < xb; x += 8) if (x > xa + 0.5) sj += seg(x, yT + 0.6, x, yC - 0.6);
    o += ln(sj, 0.7, 0.45) + ln(seg(xa, yT, xb, yT), 1.6, 1);
    // 三层拱洞（透空）
    [[o1, 46, 0], [o2, 85, 52], [o3, 109, 90]].forEach(function (t) {
      t[0].forEach(function (a) {
        holes += P.archPath(a[0], Y(t[1]), a[1] - a[0], t[1] - t[2]);
        outl += openArch(a[0], a[1], Y(t[1]), Y(t[2]));
        if (a[1] - a[0] > 20) { // 拱券石
          var rr = (a[1] - a[0]) / 2, cx = a[0] + rr, cy = Y(t[1]) + rr;
          for (var k = 1; k < 8; k++) { var an = Math.PI + Math.PI * k / 8; vs += seg(cx + Math.cos(an) * rr, cy + Math.sin(an) * rr, cx + Math.cos(an) * (rr + 3.6), cy + Math.sin(an) * (rr + 3.6)); }
        }
      });
    });
    var face = P.pd([[xa, yC], [xb, yC], [xb, yb], [xa, yb]]) + holes, cid = c.id + '-face';
    o += '<path d="' + face + '" fill="' + TRAV + '" fill-rule="evenodd"/>';
    // 石缝：12 px 周期，按格内绝对 x 对齐（拼接无缝），裁在立面内
    var cd = '', row = 0;
    for (var y = yb - 6; y > yC + 0.5; y -= 6, row++) cd += seg(xa, y, xb, y);
    var vd = '';
    for (y = yb, row = 0; y > yC + 0.5; y -= 6, row++) for (x = (row % 2) * 6; x < 48; x += 12) if (x > xa + 0.5 && x < xb - 0.5) vd += seg(x, y - 0.6, x, Math.max(yC, y - 6) + 0.6);
    o += '<defs><clipPath id="' + cid + '"><path d="' + face + '" clip-rule="evenodd"/></clipPath></defs>';
    o += '<g clip-path="url(#' + cid + ')">' + ln(cd, 0.7, 0.42) + ln(vd, 0.6, 0.36) + '</g>';
    // 层间檐口
    [50, 88, 112].forEach(function (h) { o += rect(xa, Y(h) - 1.4, xb - xa, 2.8, C.stone, 0) + ln(seg(xa, Y(h) - 1.4, xb, Y(h) - 1.4) + seg(xa, Y(h) + 1.4, xb, Y(h) + 1.4), 0.9, 0.85); });
    o += ln(outl, 1.3, 1) + ln(vs, 0.7, 0.55) + ln(seg(xa, yC, xb, yC), 1.7, 1);
    // 地面线只画在拱墩下
    var gl = '', px = xa;
    o1.forEach(function (a) { if (a[0] > px) gl += seg(px, yb, a[0], yb); px = a[1]; });
    if (xb > px) gl += seg(px, yb, xb, yb);
    o += ln(gl, 1.8, 1);
    if (edgeL) o += ln(seg(xa, yT, xa, yb), 1.8, 1);
    if (edgeR) o += ln(seg(xb, yT, xb, yb), 1.8, 1);
    return o;
  }
  /** 端头外侧的土坡（引水渠接入山坡）：x0..x1，dir=1 坡面朝右 */
  function bank(c, x0, x1, dir) {
    var yb = c.up + AQ_G, yC = yb - AQ_CAP + 8, xi = dir > 0 ? x1 : x0, xo = dir > 0 ? x0 : x1;
    var pts = [[xo, yb + 8], [xo, yC - 6], [xi - dir * 3, yC - 4], [xi, yC + 20], [xi + dir * 2, yb - 30], [xi + dir * 6, yb + 8]];
    return P.crag(pts, c.rnd, { strata: 5 }) + P.bush(xo + dir * 6, yC - 2, 6, c.rnd) + P.bush(xi + dir * 3, yb + 4, 5, c.rnd);
  }

  def({
    kind: 'aqueduct', id: 'aqueduct-ew-01', variant: 1, name: '引水渠·东西段', fp: [1, 1], up: AQ_UP, seed: 4301,
    facility: null, culture: 'roman', roof: 'none', tags: ['aqueduct', 'tileable', 'axis_ew', 'three_tier_arcade', 'roman'],
    note: '东西走向的一跨（48 px），三层拱券（底层大拱、中层拱、顶层三联小拱）+ 渠顶盖板；拱墩中心落在格的左右边，石缝 12 px 周期，任意多格沿一行拼接无缝。' +
      'FacilityKind 没有引水渠（cistern 是蓄水池），填 null',
    draw: function (c) { return aqEW(c, 0, 48, AQ_O1, AQ_O2, AQ_O3, false, false); }
  });
  def({
    kind: 'aqueduct', id: 'aqueduct-end-w-01', variant: 2, name: '引水渠·西端头', fp: [1, 1], up: AQ_UP, seed: 4302,
    facility: null, culture: 'roman', roof: 'none', tags: ['aqueduct', 'end', 'end_w', 'roman'],
    note: '东西段的西端：渠身接进左侧山坡（土石坡），右边与 aqueduct-ew-01 拼接。FacilityKind 没有对应项，填 null',
    draw: function (c) { return bank(c, 0, 16, 1) + aqEW(c, 14, 48, [[24, 42]], [[24.5, 41]], [[35, 45], [22, 29]], true, false); }
  });
  def({
    kind: 'aqueduct', id: 'aqueduct-end-e-01', variant: 3, name: '引水渠·东端头', fp: [1, 1], up: AQ_UP, seed: 4303,
    facility: null, culture: 'roman', roof: 'none', tags: ['aqueduct', 'end', 'end_e', 'roman'],
    note: '东西段的东端：渠身接进右侧山坡，左边与 aqueduct-ew-01 拼接。FacilityKind 没有对应项，填 null',
    draw: function (c) { return bank(c, 32, 48, -1) + aqEW(c, 0, 34, [[6, 24]], [[7, 23.5]], [[3, 13], [19, 26]], false, true); }
  });

  // —— 南北走向：斜俯视下东西两侧面几乎侧对视线，只看到渠顶（带水槽）、一窄条受光西侧面与南端拱墩面 ——
  // 渠身在格中线 x 19..29（厚 10，与东西段同厚）；地面进深 g 处、高 h 画到 y = up + g - h。
  var NS_X0 = 19, NS_X1 = 29;
  /** g0..g1 为本格内渠身覆盖的进深范围；south 画南端面（端头或末格）；north 北端面描边 */
  function aqNS(c, g0, g1, south, north) {
    // 渠顶在高度 AQ_CAP：y = up + g - AQ_CAP（与东西段盖板同一高度）
    var U = c.up, o = '', yTop0 = U + g0 - AQ_CAP, yTop1 = U + g1 - AQ_CAP, x0 = NS_X0, x1 = NS_X1;
    // 地面投影（东侧），拱洞处透光留空
    var sh = '';
    for (var g = g0; g < g1; g += 48) {
      var gs = Math.max(g0, 0), ge = Math.min(g1, 48);
      sh += P.pd([[x1, U + gs], [x1 + 9, U + gs + 3], [x1 + 9, U + ge + 3], [x1, U + ge]]);
    }
    o += P.flatD(sh, C.shadow, 0.18);
    [[6, 42]].forEach(function (a) { if (a[0] >= g0 && a[1] <= g1) o += flat([[x1 + 1, U + a[0] + 8], [x1 + 8, U + a[0] + 10], [x1 + 8, U + a[1] - 2], [x1 + 1, U + a[1] - 4]], C.grass, 0.55); });
    // 受光西侧面（窄条，假透视 4 px）+ 顶层小拱缝
    o += poly([[x0 - 4, yTop0 + 3], [x0, yTop0 + 1], [x0, yTop1 + 40], [x0 - 4, yTop1 + 40]], TRAV, 1.2);
    var sl = '';
    [[3, 13], [19, 29], [35, 45]].forEach(function (a) { if (a[0] >= g0 && a[1] <= g1) sl += seg(x0 - 2, U + a[0] - 104, x0 - 2, U + a[1] - 98); });
    [[7, 41]].forEach(function (a) { if (a[0] >= g0 && a[1] <= g1) sl += seg(x0 - 2, U + a[0] - 60, x0 - 2, U + a[1] - 70); });
    o += ln(sl, 2.2, 0.8, C.dark);
    // 渠顶盖板 + 中央水槽 + 两侧护边
    o += rect(x0, yTop0, x1 - x0, yTop1 - yTop0, C.stone, 1.4);
    o += rect(x0 + 3, yTop0 + (north ? 2 : 0), x1 - x0 - 6, yTop1 - yTop0 - (north ? 2 : 0) - (south ? 3 : 0), C.water, 0.8);
    var jd = '';
    for (var y = Math.ceil((yTop0 + 1) / 8) * 8; y < yTop1 - 1; y += 8) jd += seg(x0 + 0.6, y, x0 + 3, y) + seg(x1 - 3, y, x1 - 0.6, y);
    o += ln(jd, 0.7, 0.5) + ln(seg(x0 + 4.5, yTop0 + 6, x0 + 4.5, yTop0 + 14) + seg(x1 - 5, yTop0 + 26, x1 - 5, yTop0 + 32), 0.7, 0.55, '#eef0e4');
    if (south) { // 南端拱墩面：通高实墙 + 三道檐口
      var yb = U + g1, yC = yb - AQ_CAP;
      o += P.wall(x0, x1, yC, yb, 'ashlar', c.rnd, { fill: TRAV, ch: 6, sw: 1.5 });
      [50, 88, 112].forEach(function (h) { o += rect(x0 - 1.2, yb - h - 1.4, x1 - x0 + 2.4, 2.8, C.stone, 0.9); });
      o += rect(x0 - 2.5, yb - 4, x1 - x0 + 5, 4, C.stone2, 1.1);
    }
    return o;
  }
  def({
    kind: 'aqueduct', id: 'aqueduct-ns-01', variant: 4, name: '引水渠·南北段', fp: [1, 1], up: AQ_UP, seed: 4304,
    facility: null, culture: 'roman', roof: 'none', tags: ['aqueduct', 'tileable', 'axis_ns', 'roman'],
    note: '南北走向的一格：渠身在格中线（x 19..29，与东西段同厚同高）。斜俯视下侧面几乎侧对视线，只露渠顶水槽、受光西侧窄条（顶层、中层拱缝）与东侧地面上被拱洞打断的投影；' +
      '南边一格后画，会盖住本格的南端面，所以一列格子自然连成一道。最南一格请用 aqueduct-end-s-01 收出拱墩面。FacilityKind 没有对应项，填 null',
    draw: function (c) { return aqNS(c, 0, 48, true, false); }
  });
  def({
    kind: 'aqueduct', id: 'aqueduct-end-n-01', variant: 5, name: '引水渠·北端头', fp: [1, 1], up: AQ_UP, seed: 4305,
    facility: null, culture: 'roman', roof: 'none', tags: ['aqueduct', 'end', 'end_n', 'roman'],
    note: '南北段的北端：渠身从后方山坡（土石坡 + 灌木）里伸出，南边接 aqueduct-ns-01。FacilityKind 没有对应项，填 null',
    draw: function (c) {
      var U = c.up, pts = [[1, U + 24], [2, U - 30], [8, U - 66], [18, U - 84], [32, U - 86], [42, U - 68], [47, U - 32], [47, U + 22]];
      return P.crag(pts, c.rnd, { strata: 8 }) + P.bush(8, U + 18, 6, c.rnd) + P.bush(42, U + 16, 6, c.rnd) + aqNS(c, 14, 48, true, true);
    }
  });
  def({
    kind: 'aqueduct', id: 'aqueduct-end-s-01', variant: 6, name: '引水渠·南端头', fp: [1, 1], up: AQ_UP, seed: 4306,
    facility: null, culture: 'roman', roof: 'none', tags: ['aqueduct', 'end', 'end_s', 'castellum', 'roman'],
    note: '南北段的南端：渠身止于一座方形分水塔（castellum），塔身拱门、顶上四角坡顶，北边接 aqueduct-ns-01。FacilityKind 没有对应项，填 null',
    draw: function (c) {
      var U = c.up, yb = U + 44, o = aqNS(c, 0, 28, false, false);
      o += P.boxShadow(8, 40, yb - 26, yb, 6, 48, c.H);
      o += P.hipRoof(8, 40, yb - 112, 24, 8, 'tile', { ov: 2 });
      o += P.wall(8, 40, yb - 112, yb, 'ashlar', c.rnd, { fill: TRAV, ch: 6 });
      [50, 88].forEach(function (h) { o += rect(7, yb - h - 1.4, 34, 2.8, C.stone, 0.9); });
      o += P.win(20, yb - 84, 8, 14, { shape: 'arch', panes: false }) + P.door(24, yb, 14, 26, { shape: 'arch', frame: C.stone3 });
      o += P.ellipse(24, yb - 40, 5, 2.4, C.water, 0.8) + ln(seg(24, yb - 38, 24, yb - 30), 1.6, 0.9, C.water);
      return o;
    }
  });

  /** 半球穹顶：鼓座顶面中心 (cx, yt)，半径 r；肋线 + 顶部采光亭 */
  function dome(cx, yt, r, mat) {
    var m = P.MAT[mat] || P.MAT.lead, hr = r * 0.92, o = '';
    o += path('M' + f(cx - r) + ' ' + f(yt) + 'A' + f(r) + ' ' + f(hr) + ' 0 0 1 ' + f(cx + r) + ' ' + f(yt) + 'A' + f(r) + ' ' + f(r * 0.5) + ' 0 0 1 ' + f(cx - r) + ' ' + f(yt) + 'Z', m.fill, 1.6);
    o += path('M' + f(cx + r * 0.25) + ' ' + f(yt - hr * 0.97) + 'A' + f(r) + ' ' + f(hr) + ' 0 0 1 ' + f(cx + r) + ' ' + f(yt) + 'A' + f(r) + ' ' + f(r * 0.5) + ' 0 0 1 ' + f(cx + r * 0.4) + ' ' + f(yt + r * 0.46) + 'Z', m.back, 0);
    var d = '';
    for (var k = 1; k < 8; k++) { var u = -1 + k / 4, x = cx + u * r; d += 'M' + f(cx) + ' ' + f(yt - hr) + 'Q' + f(cx + u * r * 1.05) + ' ' + f(yt - hr * 0.7) + ' ' + f(x) + ' ' + f(yt + r * 0.5 * Math.sqrt(1 - u * u)); }
    [0.35, 0.68].forEach(function (t) { var rr = r * Math.sqrt(1 - t * t); d += 'M' + f(cx - rr) + ' ' + f(yt - hr * t) + 'A' + f(rr) + ' ' + f(rr * 0.5) + ' 0 0 0 ' + f(cx + rr) + ' ' + f(yt - hr * t); });
    o += ln(d, 0.8, m.ink);
    o += P.cylinder(cx, yt - hr + 2, r * 0.14, 6, MARBLE, 'plain', null) + P.ellipse(cx, yt - hr - 4, r * 0.17, r * 0.07, m.fill, 1);
    return o;
  }
  /** 半圆浴场窗（thermae window）：底边 x0..x1、底线 yb；两根竖棂 */
  function thermalWin(x0, x1, yb) {
    var r = (x1 - x0) / 2, cx = x0 + r;
    return path('M' + f(x0) + ' ' + f(yb) + 'A' + f(r) + ' ' + f(r) + ' 0 0 1 ' + f(x1) + ' ' + f(yb) + 'Z', C.dark, 1.3) +
      ln(seg(cx - r / 3, yb, cx - r / 3, yb - r * 0.94) + seg(cx + r / 3, yb, cx + r / 3, yb - r * 0.94), 2, 1, TRAV) +
      path('M' + f(x0 - 3) + ' ' + f(yb) + 'A' + f(r + 3) + ' ' + f(r + 3) + ' 0 0 1 ' + f(x1 + 3) + ' ' + f(yb), 'none', 1.2);
  }

  // ——————————————————— 公共浴场：穹顶热水厅 + 拱顶大厅 + 两翼 + 露天泳池 ———————————————————
  def({
    kind: 'thermae', variant: 1, name: '公共浴场', fp: [4, 3], up: 110, seed: 4401,
    facility: 'cistern', culture: 'roman', roof: 'hip_tile',
    tags: ['bath', 'dome', 'thermal_window', 'natatio', 'hypocaust', 'roman', 'important'],
    note: '罗马公共浴场：后排是铅皮半球穹顶的热水厅（鼓座开拱窗，顶部采光亭），中间是长边朝前的温水 / 冷水大厅（三扇半圆浴场窗、下层拱廊），' +
      '两端四坡顶的更衣翼；前院石板地中一方露天泳池（natatio）带台阶；后面锅炉房冒烟（地暖 hypocaust）。' +
      'FacilityKind 无浴场，取最接近的 cistern（蓄水用水设施）',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, U = c.up, yf = H - 5, o = '';
      o += P.boxShadow(6, 186, U + 30, yf, 6, W, H);
      // 锅炉房烟囱与烟（最后排）
      o += P.chimney(150, U + 44, 8, 40, r) + P.smoke(152, U - 6, 3, r);
      // 热水厅：鼓座 + 穹顶
      o += P.cylinder(96, U + 60, 38, 56, TRAV, 'ashlar', r, { top: false });
      [-0.62, -0.2, 0.2, 0.62].forEach(function (u) { o += P.win(96 + u * 38 - 4, U + 14 + 19 * Math.sqrt(1 - u * u) - 8, 8, 14, { shape: 'arch', panes: false }); });
      o += rect(57, U + 2, 78, 3, C.stone, 0) + ln('M58 ' + f(U + 4) + 'A38 19 0 0 0 134 ' + f(U + 4), 1.4, 1);
      o += dome(96, U + 4, 40, 'lead');
      // 大厅：低坡红瓦顶 + 正墙
      var yE = U + 104 - 54;
      o += P.gableRoof(28, 164, yE, 40, 12, 'tile', { ov: 3 });
      o += P.wall(28, 164, yE, U + 104, 'ashlar', r, { fill: TRAV, ch: 7 });
      [[44, 72], [82, 110], [120, 148]].forEach(function (a) { o += thermalWin(a[0], a[1], yE + 22); });
      o += rect(28, yE + 24, 136, 3, C.stone, 1.1);
      o += P.arcade(28, 164, U + 104 - 16, U + 104, 7, 5, { fill: C.dark, voussoir: true });
      // 两翼更衣室（四坡顶，比大厅前凸）
      [[6, 46], [146, 186]].forEach(function (a) {
        var wy = U + 118 - 40;
        o += P.hipRoof(a[0], a[1], wy, 30, 12, 'tile', { ov: 2 });
        o += P.wall(a[0], a[1], wy, U + 118, 'ashlar', r, { fill: TRAV, ch: 7 });
        o += P.win(a[0] + 9, wy + 8, 7, 12, { shape: 'arch' }) + P.win(a[1] - 16, wy + 8, 7, 12, { shape: 'arch' }) + P.door((a[0] + a[1]) / 2, U + 118, 10, 18, { shape: 'arch', frame: C.stone3 });
      });
      // 前院：石板地 + 泳池（池壁、水面、台阶）+ 池角雕像
      o += P.paving(48, U + 106, 144, yf, 8, r, C.stone);
      o += rect(58, U + 112, 76, 22, C.stone3, 1.3) + rect(62, U + 116, 68, 16, C.water, 1);
      var wd = '';
      for (var k = 0; k < 4; k++) wd += seg(68 + k * 15, U + 121 + (k % 2) * 4, 76 + k * 15, U + 121 + (k % 2) * 4);
      o += ln(wd, 0.8, 0.6, '#eef0e4');
      for (var s = 0; s < 3; s++) o += rect(84 + s * 3, U + 116 + s * 2.6, 24 - s * 6, 2.6, C.stone2, 0.7);
      [54, 138].forEach(function (x) { o += rect(x - 3, U + 134, 6, 4, C.stone2, 0.9) + P.column(x, U + 134, 12, 1.6, { fill: MARBLE }); });
      return o;
    }
  });

  // ——————————————————— 凯旋门：三拱门、四根附柱、铭文阁楼、青铜四马战车 ———————————————————
  def({
    kind: 'triumphal_arch', variant: 1, name: '凯旋门', fp: [3, 1], up: 120, seed: 4501,
    facility: null, culture: 'roman', roof: 'none',
    tags: ['arch', 'triple_arch', 'attic', 'inscription', 'quadriga', 'relief', 'roman', 'gate_like'],
    note: '三拱凯旋门：中间大拱、两侧小拱，四根附墙科林斯柱立在高柱础上，小拱上方嵌浮雕圆盘；顶部铭文阁楼，阁楼上青铜四马战车。' +
      '可横跨在道路上（道路从大拱穿过），但不是城门，FacilityKind 无对应，填 null',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '', x0 = 14, x1 = 130, cx = 72, dg = 22, yt = yf - 104, ya = yt + 30;
      o += P.boxShadow(x0, x1, yf - dg, yf, 6, W, H);
      o += poly([[x0, yt], [x1, yt], [x1, yt - dg], [x0, yt - dg]], C.stone3, 1.4);
      // 四马战车（青铜，用深木色平涂）
      var q = '', bz = C.dark;
      o += rect(cx - 30, yt - dg + 4, 60, 7, C.stone2, 1.1);
      [-18, -6, 6, 18].forEach(function (dx, i) {
        var hx = cx + dx, hy = yt - dg + 4;
        q += 'M' + f(hx - 5) + ' ' + f(hy) + 'L' + f(hx - 4) + ' ' + f(hy - 9) + 'Q' + f(hx - 1) + ' ' + f(hy - 13) + ' ' + f(hx + (i < 2 ? -3 : 3)) + ' ' + f(hy - 20) +
          'L' + f(hx + (i < 2 ? -6 : 6)) + ' ' + f(hy - 17) + 'L' + f(hx + (i < 2 ? -2 : 2)) + ' ' + f(hy - 11) + 'L' + f(hx + 5) + ' ' + f(hy - 10) + 'L' + f(hx + 4) + ' ' + f(hy) + 'Z';
      });
      o += path(q, bz, 1);
      o += path('M' + f(cx - 7) + ' ' + f(yt - dg + 4) + 'L' + f(cx - 6) + ' ' + f(yt - dg - 10) + 'L' + f(cx + 6) + ' ' + f(yt - dg - 10) + 'L' + f(cx + 7) + ' ' + f(yt - dg + 4) + 'Z', bz, 1) +
        path('M' + f(cx - 2) + ' ' + f(yt - dg - 10) + 'L' + f(cx - 1.5) + ' ' + f(yt - dg - 22) + 'Q' + f(cx) + ' ' + f(yt - dg - 26) + ' ' + f(cx + 1.5) + ' ' + f(yt - dg - 22) + 'L' + f(cx + 2) + ' ' + f(yt - dg - 10) + 'Z', bz, 0.9) +
        ln(seg(cx + 2, yt - dg - 20, cx + 7, yt - dg - 27), 1.2, 1, bz);
      // 阁楼 + 铭文
      o += P.wall(x0, x1, yt, ya, 'ashlar', r, { fill: TRAV, ch: 10 });
      o += rect(cx - 34, yt + 5, 68, 20, C.paper, 1.2) + inscription(cx - 30, cx + 30, yt + 8, 4) + inscription(cx - 26, cx + 26, yt + 16, 4);
      o += rect(x0 - 3, ya - 1, x1 - x0 + 6, 4, C.stone, 1.3);
      // 主体
      o += P.wall(x0, x1, ya + 3, yf, 'ashlar', r, { fill: TRAV, ch: 8 });
      o += path(P.archPath(cx - 17, yf - 66, 34, 66), C.dark, 1.6) + path('M' + f(cx - 20) + ' ' + f(yf - 49) + 'A20 20 0 0 1 ' + f(cx + 20) + ' ' + f(yf - 49), 'none', 1.2);
      o += rect(cx - 4, yf - 74, 8, 9, C.stone, 1) ; // 拱心石
      [[31, 17], [113, 17]].forEach(function (a) {
        o += path(P.archPath(a[0] - 8, yf - 40, 16, 40), C.dark, 1.4);
        o += P.circle(a[0], yf - 56, 7, C.stone, 1.1) + P.circle(a[0], yf - 56, 4, C.stone2, 0.7);
        o += rect(a[0] - 12, yf - 74, 24, 8, C.stone2, 0.9) + ln(seg(a[0] - 9, yf - 70, a[0] + 9, yf - 70), 0.8, 0.5);
      });
      [18, 46, 98, 126].forEach(function (x) { o += rect(x - 5.5, yf - 18, 11, 18, C.stone, 1.2) + P.column(x, yf - 18, yf - 18 - ya - 3, 3.6, { fill: MARBLE }) + corinth(x, ya + 3, 3.6); });
      return o;
    }
  });

  // ——————————————————— 广场柱廊（forum）：三面柱廊围合石板广场 + 后排会堂 + 纪功柱 + 讲坛 ———————————————————
  def({
    kind: 'forum', variant: 1, name: '广场柱廊', fp: [5, 4], up: 96, seed: 4601,
    facility: 'market_hall', culture: 'roman', roof: 'gable_tile',
    tags: ['forum', 'colonnade', 'basilica', 'honorary_column', 'rostra', 'plaza', 'shops', 'roman', 'important'],
    note: '罗马广场：后排长边朝前的会堂（basilica，高侧窗 + 下层拱廊），左右两翼单坡顶柱廊（柱后是一间间店铺门洞），' +
      '中间大石板广场，正中一根带螺旋浮雕的纪功柱（柱顶雕像），前方演讲台（rostra）与两座骑马像底座；前沿敞开。FacilityKind 取 market_hall（广场兼集市）',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, U = c.up, yf = H - 5, o = '';
      o += P.boxShadow(6, 234, U + 20, yf, 6, W, H);
      // 广场地坪
      o += P.paving(6, U + 60, 234, yf, 10, r, C.stone);
      // 后排会堂
      var yE = U + 62 - 62;
      o += P.gableRoof(30, 210, yE, 50, 16, 'tile', { ov: 3 });
      o += P.wall(30, 210, yE, U + 62, 'ashlar', r, { fill: TRAV, ch: 7 });
      for (var i = 0; i < 9; i++) o += P.win(40 + i * 19, yE + 6, 8, 14, { shape: 'arch' });
      o += rect(30, yE + 25, 180, 3, C.stone, 1.1);
      o += P.arcade(30, 210, U + 62 - 18, U + 62, 9, 6, { fill: C.dark, voussoir: true });
      o += P.pediment(100, 140, yE, 12, r, { fill: MARBLE });
      // 两翼柱廊（顺进深）：单坡顶 + 后墙店铺 + 前排柱子
      [[6, 50, false], [190, 234, true]].forEach(function (s) {
        var xo = s[2] ? s[1] : s[0], xi = s[2] ? s[0] : s[1], gb = 66, gf2 = 176, h0 = 44, h1 = 36;
        o += P.slope([xo, U + gf2 - h0], [xo, U + gb - h0], [xi, U + gb - h1], [xi, U + gf2 - h1], 'tile', s[2]);
        // 柱廊前端面（朝南的山墙端）
        var x0 = s[0], x1 = s[1], yb = U + gf2;
        o += P.wall(x0, x1, yb - 40, yb, 'ashlar', r, { fill: TRAV, ch: 7 });
        o += path(P.archPath(x0 + 10, yb - 30, x1 - x0 - 20, 30), C.dark, 1.3);
        // 朝广场一侧的柱廊：檐下一窄条柱廊立面（暗色廊内 + 一根根柱子，按进深错开 2 px 做出透视节奏）
        var dir = s[2] ? -1 : 1, ex = xi, cd = '', cl = '';
        o += poly([[ex, U + gb - h1], [ex + dir * 7, U + gb - h1 + 3], [ex + dir * 7, U + gf2 - 40], [ex, U + gf2 - 40]], C.dark, 1.1);
        for (var g = gb + 6; g < gf2 - 40; g += 10) {
          var t = (g - gb) / (gf2 - gb), cx2 = ex + dir * (1.6 + t * 3.6), yt = U + g - h1 + 1;
          cd += P.pd([[cx2 - 1.2, yt], [cx2 + 1.2, yt], [cx2 + 1.2, yt + 10], [cx2 - 1.2, yt + 10]]);
          cl += seg(cx2 - 2, yt, cx2 + 2, yt);
        }
        o += '<path d="' + cd + '" fill="' + MARBLE + '" stroke="' + C.ink + '" stroke-width="0.6"/>' + ln(cl, 1, 0.8);
      });
      // 纪功柱：方座 + 螺旋浮雕柱身 + 雕像
      var kx = 120, ky = U + 126, kh = 104;
      o += P.box(110, 130, ky, 8, 14, C.stone2, C.stone, 1.3);
      o += rect(kx - 6, ky - 14 - kh, 12, kh, MARBLE, 1.5);
      var sp = '';
      for (var y = ky - 18; y > ky - 10 - kh; y -= 8) sp += seg(kx - 6, y, kx + 6, y - 5);
      o += ln(sp, 0.9, 0.6) + flat([[kx + 2, ky - 14 - kh], [kx + 6, ky - 14 - kh], [kx + 6, ky - 14], [kx + 2, ky - 14]], C.shadow, 0.13);
      o += rect(kx - 8, ky - 17 - kh, 16, 3.5, C.stone, 1.1);
      o += path('M' + f(kx - 3) + ' ' + f(ky - 17 - kh) + 'L' + f(kx - 2) + ' ' + f(ky - 30 - kh) + 'Q' + f(kx) + ' ' + f(ky - 35 - kh) + ' ' + f(kx + 2) + ' ' + f(ky - 30 - kh) + 'L' + f(kx + 3) + ' ' + f(ky - 17 - kh) + 'Z', C.dark, 0.9);
      // 骑马像底座两座
      [[66, U + 150], [174, U + 150]].forEach(function (p) {
        o += P.box(p[0] - 9, p[0] + 9, p[1], 7, 12, C.stone2, C.stone, 1.2);
        o += path('M' + f(p[0] - 7) + ' ' + f(p[1] - 15) + 'L' + f(p[0] - 6) + ' ' + f(p[1] - 22) + 'L' + f(p[0] + 4) + ' ' + f(p[1] - 23) + 'L' + f(p[0] + 7) + ' ' + f(p[1] - 29) + 'L' + f(p[0] + 8) + ' ' + f(p[1] - 22) + 'L' + f(p[0] + 7) + ' ' + f(p[1] - 15) + 'Z', C.dark, 0.9) +
          path('M' + f(p[0] - 1) + ' ' + f(p[1] - 23) + 'L' + f(p[0] - 1) + ' ' + f(p[1] - 31) + 'Q' + f(p[0] + 1) + ' ' + f(p[1] - 34) + ' ' + f(p[0] + 2) + ' ' + f(p[1] - 30) + 'L' + f(p[0] + 2) + ' ' + f(p[1] - 23) + 'Z', C.dark, 0.8);
      });
      // 前方演讲台 rostra：矮台 + 船首装饰 + 栏杆
      o += P.box(92, 148, yf - 2, 12, 14, TRAV, C.stone, 1.4);
      [102, 116, 130, 142].forEach(function (x) { o += path('M' + f(x - 3) + ' ' + f(yf - 12) + 'L' + f(x + 3) + ' ' + f(yf - 12) + 'L' + f(x) + ' ' + f(yf - 5) + 'Z', C.dark, 0.8); });
      o += ln(seg(93, yf - 22, 147, yf - 22) + seg(100, yf - 22, 100, yf - 16) + seg(120, yf - 22, 120, yf - 16) + seg(140, yf - 22, 140, yf - 16), 1, 0.8);
      return o;
    }
  });

  if (typeof module !== 'undefined' && module.exports) module.exports = defs;
  else root.TownArtWL_roman = defs;
})(typeof window !== 'undefined' ? window : this);
