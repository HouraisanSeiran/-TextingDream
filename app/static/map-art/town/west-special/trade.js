/*
 * 织梦 · 西式特殊建筑：商贸（菜市场摊位、市集厅、酒馆客栈、商队驿站、粮仓、马厩）
 * 浏览器挂 window.TownArtWS_trade；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var P = (typeof module !== 'undefined' && module.exports) ? require('./prims.js') : root.TownArtWS_prims;
  var C = P.C, f = P.f, seg = P.seg, ln = P.ln, rect = P.rect, poly = P.poly, path = P.path, flat = P.flat;
  var defs = [];
  function def(o) { defs.push(o); }

  /** 条纹帆布篷：前沿 yF、后沿 yB（篷面朝上可见），n 条竖纹；前沿垂一排扇贝边 */
  function awning(x0, x1, yF, yB, n, c1, c2, sag) {
    var w = (x1 - x0) / n, o = '', d = '', i, s = sag || 6;
    for (i = 0; i < n; i++) o += flat([[x0 + i * w, yB], [x0 + (i + 1) * w, yB], [x0 + (i + 1) * w, yF], [x0 + i * w, yF]], i % 2 ? c2 : c1);
    o += flat([[x0 + (x1 - x0) * 0.62, yB], [x1, yB], [x1, yF], [x0 + (x1 - x0) * 0.62, yF]], C.shadow, 0.1);
    for (i = 1; i < 3; i++) d += seg(x0 + 1, yB + (yF - yB) * i / 3, x1 - 1, yB + (yF - yB) * i / 3);
    o += ln(d, 0.7, 0.3) + poly([[x0, yB], [x1, yB], [x1, yF], [x0, yF]], 'none', 1.5);
    for (i = 0; i < n; i++) {
      var a = x0 + i * w, b = a + w;
      o += path('M' + f(a) + ' ' + f(yF) + 'L' + f(b) + ' ' + f(yF) + 'L' + f(b) + ' ' + f(yF + 2) + 'Q' + f((a + b) / 2) + ' ' + f(yF + s) + ' ' + f(a) + ' ' + f(yF + 2) + 'Z', i % 2 ? c2 : c1, 1.1);
    }
    return o;
  }
  /** 一堆圆形货品（菜、果）：cx,cy 中心，宽 w，n 个，cols 颜色轮换，rr 单个半径；从后往前画 */
  function pile(cx, cy, w, n, cols, rnd, rr) {
    var pts = [], o = '';
    for (var i = 0; i < n; i++) pts.push([cx + (rnd() - 0.5) * w, cy - rnd() * rr * 1.6, cols[i % cols.length]]);
    pts.sort(function (a, b) { return a[1] - b[1]; });
    pts.forEach(function (p) {
      o += P.circle(p[0], p[1], rr, p[2], 0.9) + ln(seg(p[0] - rr * 0.35, p[1] - rr * 0.35, p[0] - rr * 0.05, p[1] - rr * 0.55), 0.7, 0.5);
    });
    return o;
  }
  /** 卷心菜：叶团 + 两道叶脉 */
  function cabbage(cx, cy, r) {
    return P.circle(cx, cy, r, C.leaf, 1.1) + ln('M' + f(cx - r * 0.6) + ' ' + f(cy) + 'Q' + f(cx) + ' ' + f(cy - r * 0.9) + ' ' + f(cx + r * 0.6) + ' ' + f(cy) +
      'M' + f(cx) + ' ' + f(cy - r * 0.2) + 'L' + f(cx) + ' ' + f(cy + r * 0.7), 0.8, 0.6);
  }
  /** 胡萝卜一束：几根橘红细三角 + 绿缨 */
  function carrots(x, y, n) {
    var o = '';
    for (var i = 0; i < n; i++) {
      var bx = x + i * 3;
      o += poly([[bx, y], [bx + 2.6, y], [bx + 5.5, y + 7]], C.tile, 0.8) + ln(seg(bx + 1.2, y, bx, y - 3) + seg(bx + 1.4, y, bx + 2.6, y - 3), 0.9, 1, C.leaf);
    }
    return o;
  }
  /** 柳条筐：cx 中线，yb 底；goods 在筐口堆一层 */
  function basket(cx, yb, w, h, goods, rnd) {
    var x0 = cx - w / 2, x1 = cx + w / 2, yt = yb - h;
    var o = (goods ? pile(cx, yt + 0.5, w * 0.75, 5, goods, rnd, w * 0.16) : '');
    o += path('M' + f(x0) + ' ' + f(yt) + 'L' + f(x1) + ' ' + f(yt) + 'L' + f(x1 - w * 0.12) + ' ' + f(yb - 1.5) + 'Q' + f(cx) + ' ' + f(yb + 1) + ' ' + f(x0 + w * 0.12) + ' ' + f(yb - 1.5) + 'Z', C.wood, 1.3);
    var d = '';
    for (var y = yt + 2.5; y < yb - 1; y += 2.5) d += seg(x0 + 1.5, y, x1 - 1.5, y);
    for (var x = x0 + 3; x < x1 - 1; x += 3.2) d += seg(x, yt + 0.5, x + (x < cx ? 0.6 : -0.6), yb - 1.5);
    return o + ln(d, 0.6, 0.45) + ln(seg(x0 - 0.5, yt, x1 + 0.5, yt), 1.6, 1, C.beam);
  }
  /** 麻袋：圆鼓鼓、顶部扎口 */
  function sack(cx, yb, w, h, fill) {
    var o = path('M' + f(cx - w * 0.2) + ' ' + f(yb - h) + 'Q' + f(cx - w * 0.62) + ' ' + f(yb - h * 0.55) + ' ' + f(cx - w * 0.5) + ' ' + f(yb - 1) +
      'Q' + f(cx) + ' ' + f(yb + 1.5) + ' ' + f(cx + w * 0.5) + ' ' + f(yb - 1) + 'Q' + f(cx + w * 0.62) + ' ' + f(yb - h * 0.55) + ' ' + f(cx + w * 0.2) + ' ' + f(yb - h) + 'Z', fill || C.paper, 1.2);
    return o + ln(seg(cx - w * 0.22, yb - h + 1.2, cx + w * 0.22, yb - h + 1.2), 1.2, 1, C.beam) + ln(seg(cx - w * 0.1, yb - h * 0.55, cx - w * 0.2, yb - h * 0.2), 0.7, 0.45);
  }
  /** 摊台：木桌（正面 + 桌面），四柱 */
  function table(x0, x1, yf, h, dg) {
    var o = P.box(x0, x1, yf, dg, h, C.wood, '#d8b77e', 1.4), d = '';
    for (var x = x0 + 5; x < x1 - 2; x += 5) d += seg(x, yf - h + 1, x, yf - 1);
    return o + ln(d, 0.7, 0.45) + ln(seg(x0, yf - h + 0.5, x1, yf - h + 0.5), 1.6, 1, C.beam);
  }
  function stallShadow(yf, x1) { return P.shade([[6, yf], [8, yf + 3], [x1 + 2, yf + 3], [x1 + 2, yf - 20], [x1 - 2, yf - 22]]); }
  var STALL = { category: 'prop', facility: 'market_hall', fp: [1, 1], up: 34, roof: 'none' };
  function stall(o) { for (var k in STALL) if (!(k in o)) o[k] = STALL[k]; def(o); }

  // ——————————————————— 露天摊位 1：红白条纹篷 · 菜摊 ———————————————————
  stall({
    kind: 'stall', variant: 1, name: '菜摊·红白篷', seed: 2101, tags: ['open_air', 'stall', 'vegetables', 'scatter'],
    note: '露天菜市场单个摊位（可散放）：红白条纹帆布篷、木摊台上卷心菜与胡萝卜，台前一筐洋葱',
    draw: function (c) {
      var r = c.rnd, H = c.H, yf = H - 5, o = stallShadow(yf, 44);
      o += rect(7, yf - 60, 2.5, 36, C.beam, 1) + rect(38.5, yf - 60, 2.5, 36, C.beam, 1);
      o += table(4, 44, yf, 12, 12);
      o += cabbage(11, yf - 18, 3.6) + cabbage(17, yf - 20, 3.6) + cabbage(14, yf - 15, 3.8) + carrots(22, yf - 20, 4) + cabbage(37, yf - 18, 3.4);
      o += rect(4.5, yf - 30, 2.6, 30, C.beam, 1.1) + rect(40.9, yf - 30, 2.6, 30, C.beam, 1.1);
      o += awning(1, 47, yf - 30, yf - 60, 6, C.red, C.paper, 6);
      o += basket(36, H - 1, 12, 8, [C.wash, '#d8b77e'], r) + basket(12, H - 1, 10, 6, [C.leaf], r);
      return o;
    }
  });

  // ——————————————————— 露天摊位 2：青白条纹篷 · 果摊 + 木箱 ———————————————————
  stall({
    kind: 'stall', variant: 2, name: '果摊·青白篷', seed: 2102, tags: ['open_air', 'stall', 'fruit', 'scatter'],
    note: '青白条纹篷果摊：摊台上苹果与梨，右侧叠放两只装果木箱',
    draw: function (c) {
      var r = c.rnd, H = c.H, yf = H - 5, o = stallShadow(yf, 44);
      o += rect(6, yf - 58, 2.5, 34, C.beam, 1) + rect(30, yf - 58, 2.5, 34, C.beam, 1);
      o += table(3, 34, yf, 12, 12);
      o += pile(11, yf - 16, 10, 8, [C.red, C.tile], r, 2.6) + pile(25, yf - 16, 10, 7, [C.wash, '#d8b77e'], r, 2.6);
      o += rect(3.5, yf - 28, 2.6, 28, C.beam, 1.1) + rect(31, yf - 28, 2.6, 28, C.beam, 1.1);
      o += awning(0, 37, yf - 28, yf - 58, 5, C.slate, C.paper, 6);
      o += P.crate(34, yf - 1, 12, 10, 5) + pile(40, yf - 17, 8, 4, [C.red], r, 2.3) + P.crate(35, H - 1, 12, 10, 5);
      o += basket(19, H - 1, 11, 7, [C.red, C.tile], r);
      return o;
    }
  });

  // ——————————————————— 露天摊位 3：本色帆布尖帐 · 粮面摊 ———————————————————
  stall({
    kind: 'stall', variant: 3, name: '粮面摊·帆布帐', seed: 2103, tags: ['open_air', 'stall', 'grain', 'bread', 'scatter'],
    note: '本色帆布两坡小帐：摊台上面包与圆面饼，台前几只粮食麻袋、一只敞口粮袋',
    draw: function (c) {
      var r = c.rnd, H = c.H, yf = H - 5, o = stallShadow(yf, 44);
      // 帐篷屋脊平行正面：后坡（暗）、前坡（亮）
      o += rect(22.8, yf - 64, 2.4, 40, C.beam, 1);
      o += table(4, 44, yf, 11, 12);
      o += pile(13, yf - 15, 12, 6, [C.wash, '#d8b77e'], r, 3) + P.ellipse(30, yf - 13, 6, 2.6, '#d8b77e', 1) + P.ellipse(37, yf - 14, 5, 2.2, C.wash, 1);
      o += rect(3.5, yf - 26, 2.6, 26, C.beam, 1.1) + rect(41.9, yf - 26, 2.6, 26, C.beam, 1.1);
      o += P.slope([1, yf - 26], [47, yf - 26], [44, yf - 58], [4, yf - 58], 'canvas', false, r);
      o += ln(seg(12, yf - 27, 13, yf - 57) + seg(24, yf - 27, 24, yf - 57) + seg(36, yf - 27, 35, yf - 57), 0.7, 0.35);
      o += flat([[30, yf - 57], [44, yf - 57], [47, yf - 26.5], [30, yf - 26.5]], C.shadow, 0.08);
      o += ln(seg(4, yf - 58, 44, yf - 58), 1.8, 1, C.beam) + ln(seg(1, yf - 26, 47, yf - 26), 1.8, 1, C.dark);
      o += sack(8, H - 1, 9, 10) + sack(16, H - 1, 9, 11, C.stone) + sack(40, H - 1, 10, 10);
      o += P.ellipse(40, H - 11, 3.4, 1.4, C.wash, 0.8);
      return o;
    }
  });

  /** 拱廊：x0..x1 墙段里开 n 个半圆券洞，券洞内能看到深色廊内与后墙下沿 */
  function arcade(x0, x1, yt, yb, n, r, opt) {
    opt = opt || {};
    var o = P.wall(x0, x1, yt, yb, opt.kind || 'ashlar', r), w = (x1 - x0) / n;
    for (var i = 0; i < n; i++) {
      var ax = x0 + i * w + w * 0.14, aw = w * 0.72;
      o += path(P.archPath(ax, yt + (yb - yt) * 0.16, aw, (yb - yt) * 0.84), C.dark, 1.4);
      o += flat([[ax + 1, yb - 1], [ax + aw - 1, yb - 1], [ax + aw - 1, yb - 4], [ax + 1, yb - 4]], C.stone2);
      if (opt.goods) o += opt.goods(ax + aw / 2, yb - 1, aw, i);
    }
    return o;
  }

  // ——————————————————— 市集厅 1：石拱廊底层 + 木筋上层（廊下有摊） ———————————————————
  def({
    kind: 'market_hall', facility: 'market_hall', variant: 1, name: '市集厅·拱廊', fp: [3, 2], up: 70, seed: 2201,
    roof: 'hip_tile', tags: ['arcade', 'covered_market', 'important'],
    note: '中世纪有顶市场：底层开敞的石拱廊，廊下看得见菜筐、麻袋与秤；上层木筋储货/行会厅，红瓦四坡顶，正中挂铜秤招牌',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '', y1 = yf - 30, y2 = yf - 56;
      o += P.boxShadow(6, 138, yf - 66, yf, 5, W, H);
      o += P.hipRoof(6, 138, y2, 66, 22, 'tile', r, { ov: 4 });
      o += P.wall(6, 138, y2, y1, 'timber', r, { bays: 6 });
      [18, 40, 62, 84, 106, 126].forEach(function (x) { o += P.win(x - 4, y2 + 7, 8, 11, { shutters: false }); });
      o += rect(4, y1 - 2, 136, 3.5, C.dark, 1.2);
      o += arcade(6, 138, y1, yf, 5, r, { goods: function (cx, yb, aw, i) {
        if (i === 2) return '';
        if (i % 2) return sack(cx - 4, yb, 8, 9) + sack(cx + 4, yb, 8, 10, C.stone);
        return basket(cx - 4, yb, 9, 6, [C.leaf], r) + basket(cx + 5, yb, 9, 6, [C.red, C.tile], r);
      } });
      // 正中廊下：秤台
      o += ln(seg(64, yf - 18, 80, yf - 18) + seg(72, yf - 22, 72, yf - 18) + seg(64, yf - 18, 64, yf - 13) + seg(80, yf - 18, 80, yf - 13), 1.1, 1, C.wash);
      o += path('M60 ' + f(yf - 13) + 'L68 ' + f(yf - 13) + 'Q64 ' + f(yf - 9) + ' 60 ' + f(yf - 13) + 'Z', C.wash, 0.9) + path('M76 ' + f(yf - 13) + 'L84 ' + f(yf - 13) + 'Q80 ' + f(yf - 9) + ' 76 ' + f(yf - 13) + 'Z', C.wash, 0.9);
      // 二层正中：铜秤招牌
      o += rect(60, y2 - 2, 24, 15, C.wash, 1.3) + ln(seg(72, y2 + 1, 72, y2 + 6) + seg(64, y2 + 6, 80, y2 + 6) + seg(65, y2 + 6, 63, y2 + 10) + seg(65, y2 + 6, 67, y2 + 10) + seg(79, y2 + 6, 77, y2 + 10) + seg(79, y2 + 6, 81, y2 + 10), 1, 1) +
        ln(seg(62, y2 + 10, 68, y2 + 10) + seg(76, y2 + 10, 82, y2 + 10), 1.4, 1);
      o += P.flag(72, y2 - 54, 16, 12, C.red);
      return o;
    }
  });

  // ——————————————————— 市集厅 2：木柱敞厅（四面开敞的大屋顶） ———————————————————
  def({
    kind: 'market_hall', facility: 'market_hall', variant: 2, name: '市集厅·木柱敞厅', fp: [3, 2], up: 58, seed: 2202,
    roof: 'hip_tile', tags: ['open_hall', 'covered_market', 'timber_posts', 'important'],
    note: '乡镇常见的木构市集敞厅：石础上一排粗木柱撑起大红瓦四坡顶，四面开敞，厅下摆着长摊台、菜筐与木箱；屋顶正中小气窗',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '', yE = yf - 34;
      o += P.boxShadow(6, 138, yf - 70, yf, 5, W, H);
      // 厅内地坪 + 后排柱
      o += P.paving(8, yf - 22, 136, yf, 9, r, C.stone2);
      [14, 44, 74, 104, 132].forEach(function (x) { o += rect(x - 2, yE + 6, 4, 22, C.dark, 1); });
      // 厅内摊台与货
      o += table(18, 62, yf - 6, 9, 8) + table(82, 126, yf - 6, 9, 8);
      o += cabbage(24, yf - 17, 3.3) + cabbage(30, yf - 18, 3.3) + carrots(36, yf - 19, 4) + pile(54, yf - 16, 10, 6, [C.red, C.tile], r, 2.4);
      o += pile(92, yf - 16, 12, 7, [C.wash, '#d8b77e'], r, 2.6) + P.ellipse(114, yf - 15, 6, 2.4, '#d8b77e', 1);
      o += basket(70, yf, 10, 7, [C.leaf], r) + P.crate(130, yf, 10, 9, 4) + sack(10, yf, 8, 9);
      // 前排柱（石础 + 木柱 + 斜撑）
      [6, 40, 72, 104, 138].forEach(function (x, i) {
        var px = Math.min(Math.max(x, 8), 136);
        o += rect(px - 4, yf - 4, 8, 4, C.stone3, 1.1) + rect(px - 2.6, yE + 2, 5.2, 30, C.beam, 1.3);
        if (i > 0) o += ln(seg(px - 2.6, yE + 9, px - 9, yE + 2.5), 2, 1, C.beam);
        if (i < 4) o += ln(seg(px + 2.6, yE + 9, px + 9, yE + 2.5), 2, 1, C.beam);
      });
      o += rect(4, yE, 136, 3.5, C.beam, 1.3);
      // 大屋顶 + 正中老虎窗
      o += P.hipRoof(8, 136, yE + 1, 70, 20, 'tile', r, { ov: 5 });
      var g = P.gableFront(62, 82, yE - 18, 14, 9, 'tile', r, { ov: 1.5, fill: C.wood });
      o += g.roof + g.gable + P.win(68, yE - 16, 8, 7, { panes: true });
      return o;
    }
  });

  /** 横躺酒桶侧面：cx,cy 中心，长 w，高 h */
  function barrelSide(cx, cy, w, h) {
    var x0 = cx - w / 2, x1 = cx + w / 2, e = h * 0.38;
    var d = 'M' + f(x0) + ' ' + f(cy - e) + 'Q' + f(cx) + ' ' + f(cy - h * 0.72) + ' ' + f(x1) + ' ' + f(cy - e) +
      'L' + f(x1) + ' ' + f(cy + e) + 'Q' + f(cx) + ' ' + f(cy + h * 0.72) + ' ' + f(x0) + ' ' + f(cy + e) + 'Z';
    var o = path(d, C.wood, 1.4), hp = '';
    [0.2, 0.8].forEach(function (t) {
      var x = x0 + w * t;
      hp += 'M' + f(x) + ' ' + f(cy - h * 0.48) + 'Q' + f(x + (t < 0.5 ? -1.5 : 1.5)) + ' ' + f(cy) + ' ' + f(x) + ' ' + f(cy + h * 0.48);
    });
    o += ln(hp, 1.6, 1, C.dark) + ln(seg(x0 + 1, cy - h * 0.15, x1 - 1, cy - h * 0.15) + seg(x0 + 1, cy + h * 0.18, x1 - 1, cy + h * 0.18), 0.7, 0.45);
    return o + P.ellipse(x0, cy, 1.6, e, C.beam, 1);
  }
  /** 拴马桩：两根桩 + 横杆 + 铁环 */
  function hitchRail(x0, x1, yb) {
    return rect(x0, yb - 13, 3, 13, C.beam, 1.1) + rect(x1 - 3, yb - 13, 3, 13, C.beam, 1.1) +
      rect(x0 - 1, yb - 12, x1 - x0 + 2, 2.6, C.wood, 1.1) + P.ring((x0 + x1) / 2, yb - 8.2, 1.8, 0.9, 1, C.slate2);
  }
  /** 木槽（饮马槽 / 料槽）：顶面盛水 */
  function trough(x0, x1, yb, fill) {
    return P.box(x0, x1, yb, 4, 6, C.wood, fill || C.water, 1.2) + ln(seg(x0 + 1, yb - 3, x1 - 1, yb - 3), 0.7, 0.5);
  }
  /** 啤酒杯图案：杯身 + 把手 + 泡沫 */
  function tankard(cx, cy, s) {
    s = s || 1;
    return path('M' + f(cx + 3 * s) + ' ' + f(cy - 2 * s) + 'Q' + f(cx + 7 * s) + ' ' + f(cy - 2 * s) + ' ' + f(cx + 6 * s) + ' ' + f(cy + 2 * s) + 'Q' + f(cx + 5 * s) + ' ' + f(cy + 4 * s) + ' ' + f(cx + 3 * s) + ' ' + f(cy + 3.5 * s), 'none', 1.2) +
      rect(cx - 4 * s, cy - 3 * s, 7.5 * s, 8.5 * s, C.wood, 1.1) + ln(seg(cx - 1.5 * s, cy - 2 * s, cx - 1.5 * s, cy + 4.5 * s), 0.7, 0.5) +
      path('M' + f(cx - 4.6 * s) + ' ' + f(cy - 3 * s) + 'Q' + f(cx - 3 * s) + ' ' + f(cy - 6.2 * s) + ' ' + f(cx) + ' ' + f(cy - 5 * s) + 'Q' + f(cx + 3 * s) + ' ' + f(cy - 6.4 * s) + ' ' + f(cx + 4.2 * s) + ' ' + f(cy - 3 * s) + 'Z', C.paper, 0.9);
  }

  // ——————————————————— 酒馆客栈 1：三层出挑木筋客栈 + 酒桶招牌 ———————————————————
  def({
    kind: 'inn', facility: 'inn', variant: 1, name: '客栈·酒桶招牌', fp: [3, 2], up: 92, seed: 2301,
    roof: 'gable_tile', tags: ['tavern', 'lodging', 'jettied', 'hitching_post', 'important'],
    note: '三层客栈：底层石砌酒堂，上两层木筋逐层外挑，红瓦坡顶两座老虎窗；门旁铁臂挂一只横躺酒桶作招牌，门前拴马桩与饮马槽，墙边堆酒桶',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '', y1 = yf - 26, y2 = yf - 48, y3 = yf - 70;
      o += P.boxShadow(8, 136, yf - 60, yf, 5, W, H);
      o += P.gableRoof(3, 141, y3, 60, 24, 'tile', r, { ov: 2 });
      o += P.chimney(22, y3 - 22, 9, 22, r) + P.smoke(26, y3 - 48, 3, r) + P.chimney(116, y3 - 24, 9, 20, r);
      [52, 92].forEach(function (x) {
        var yb = y3 - 6, g = P.gableFront(x - 8, x + 8, yb - 11, 9, 8, 'tile', r, { ov: 1.5 });
        o += g.roof + rect(x - 8, yb - 11, 16, 11, C.plaster, 1.3) + P.win(x - 3.5, yb - 9, 7, 7, {}) + g.gable;
      });
      o += P.wall(3, 141, y3, y2, 'timber', r, { bays: 6 });
      [12, 34, 56, 81, 103, 125].forEach(function (x) { o += P.win(x, y3 + 6, 7, 10, {}); });
      o += rect(3, y2 - 1, 138, 3, C.dark, 1.1);
      o += P.wall(6, 138, y2 + 2, y1, 'timber', r, { bays: 5 });
      [14, 40, 94, 120].forEach(function (x) { o += P.win(x, y2 + 7, 9, 10, { shutters: true }); });
      o += rect(6, y1 - 1, 132, 3, C.dark, 1.1);
      o += P.wall(9, 135, y1 + 2, yf, 'stone', r, { plinth: 4 });
      o += P.door(72, yf, 16, 21, { shape: 'arch', frame: C.stone3 });
      o += P.win(18, y1 + 8, 16, 10, {}) + P.win(42, y1 + 8, 12, 10, {}) + P.win(112, y1 + 8, 14, 10, {});
      [12, 38, 64, 80, 106, 132].forEach(function (x) { o += ln(seg(x, y1 + 2, x + 3, y1 + 7), 2, 1, C.dark); });
      // 酒桶招牌
      o += ln(seg(83, y1 + 4, 106, y1 + 4) + seg(83, y1 + 10, 89, y1 + 4), 1.4, 1) + ln(seg(91, y1 + 4, 91, y1 + 10) + seg(103, y1 + 4, 103, y1 + 10), 0.8, 1);
      o += barrelSide(97, y1 + 14, 17, 10);
      // 门前：饮马槽 + 拴马桩；右侧墙边酒桶堆
      o += hitchRail(12, 40, H - 3) + trough(16, 36, H - 0.5);
      o += P.barrelEnd(118, H - 6, 5) + P.barrelEnd(129, H - 6, 5) + P.barrelEnd(123.5, H - 15, 5);
      return o;
    }
  });

  // ——————————————————— 酒馆客栈 2：茅草顶驿道酒馆 + 马车拱门 ———————————————————
  def({
    kind: 'inn', facility: 'inn', variant: 2, name: '酒馆·茅草驿道店', fp: [3, 2], up: 84, seed: 2302,
    roof: 'gable_thatch', tags: ['tavern', 'coaching_inn', 'carriage_arch', 'signpost', 'important'],
    note: '驿道旁茅草顶酒馆：两层（下石上木筋），右翼山墙朝前、开马车拱门通后院；门前立柱挂啤酒杯招牌，门边长凳、酒桶当桌，挂一盏提灯',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '', y1 = yf - 26, y2 = yf - 50;
      o += P.boxShadow(6, 140, yf - 58, yf, 5, W, H);
      // 右翼：山墙朝前，木瓦，马车拱门
      var g = P.gableFront(92, 140, yf - 40, 56, 22, 'shingle', r, { ov: 2, fill: C.stone });
      o += g.roof + g.gable + P.wall(92, 140, yf - 40, yf, 'stone', r, { plinth: 4 });
      o += P.win(112, yf - 54, 8, 9, { shape: 'arch', panes: false });
      o += path(P.archPath(101, yf - 33, 30, 33), C.stone3, 1.4) + path(P.archPath(104, yf - 30, 24, 30), C.dark, 1.4);
      o += P.ring(118, yf - 8, 7, 1.6, 1, C.wood) + ln(seg(118, yf - 15, 118, yf - 1) + seg(111, yf - 8, 125, yf - 8), 0.9, 0.9, C.wood);
      // 主楼：茅草顶
      o += P.gableRoof(6, 92, y2, 56, 24, 'thatch', r, { ov: 5 });
      o += P.chimney(12, y2 - 14, 10, 30, r) + P.smoke(17, y2 - 48, 3, r);
      o += P.wall(6, 92, y2, y1, 'timber', r, { bays: 4 });
      [17, 40, 62, 82].forEach(function (x) { o += P.win(x - 3.5, y2 + 6, 7, 10, {}); });
      o += P.wall(6, 92, y1, yf, 'stone', r, { plinth: 4 });
      o += P.door(52, yf, 14, 20, { frame: C.beam }) + P.win(18, y1 + 7, 14, 10, {}) + P.win(70, y1 + 7, 12, 10, {});
      // 提灯
      o += ln(seg(62, y1 + 3, 66, y1 + 3) + seg(66, y1 + 3, 66, y1 + 6), 1, 1) + rect(64, y1 + 6, 4, 5, C.wash, 0.9);
      // 长凳 + 酒桶桌
      o += rect(16, yf - 7, 22, 2.4, C.wood, 1.1) + ln(seg(18, yf - 4.6, 18, yf) + seg(36, yf - 4.6, 36, yf), 1.4, 1, C.beam);
      o += P.barrel(76, H - 3.5, 5, 9) + tankard(74, H - 15.5, 0.55) + tankard(79, H - 15, 0.55);
      // 立柱招牌
      o += rect(41, H - 46, 3, 46, C.beam, 1.2) + ln(seg(44, H - 43, 62, H - 43) + seg(44, H - 36, 51, H - 43), 1.6, 1, C.beam);
      o += ln(seg(48, H - 43, 48, H - 40) + seg(60, H - 43, 60, H - 40), 0.8, 1) + rect(46, H - 40, 16, 14, C.wash, 1.3) + tankard(53.5, H - 32.5, 0.8);
      return o;
    }
  });

  /** 篷布马车：x 车尾左端，yb 地面，dir 1 车辕朝右 */
  function wagon(x, yb, cover) {
    var o = '', d = '';
    o += ln(seg(x + 28, yb - 7, x + 40, yb - 3), 1.6, 1, C.beam);
    o += rect(x, yb - 13, 30, 6, C.wood, 1.3) + ln(seg(x + 1, yb - 10, x + 29, yb - 10), 0.7, 0.5);
    o += path('M' + f(x + 2) + ' ' + f(yb - 13) + 'L' + f(x + 2) + ' ' + f(yb - 20) + 'Q' + f(x + 15) + ' ' + f(yb - 34) + ' ' + f(x + 28) + ' ' + f(yb - 20) + 'L' + f(x + 28) + ' ' + f(yb - 13) + 'Z', cover || C.paper, 1.4);
    [9, 15, 21].forEach(function (k) { d += 'M' + f(x + k) + ' ' + f(yb - 13) + 'L' + f(x + k) + ' ' + f(yb - 27 + Math.abs(k - 15) * 0.35); });
    o += ln(d, 0.8, 0.45) + flat([[x + 19, yb - 13.5], [x + 27.5, yb - 13.5], [x + 27.5, yb - 20], [x + 19, yb - 27]], C.shadow, 0.1);
    [x + 7, x + 23].forEach(function (cx) {
      var sp = '';
      for (var i = 0; i < 4; i++) { var a = i * Math.PI / 4; sp += seg(cx - Math.cos(a) * 4.6, yb - 5 - Math.sin(a) * 4.6, cx + Math.cos(a) * 4.6, yb - 5 + Math.sin(a) * 4.6); }
      o += P.circle(cx, yb - 5, 5, C.wood, 1.3) + ln(sp, 0.8, 0.8) + P.circle(cx, yb - 5, 1.3, C.dark, 0.6);
    });
    return o;
  }

  // ——————————————————— 商队驿站：四合围院 + 门楼 ———————————————————
  def({
    kind: 'caravanserai', facility: 'caravanserai', variant: 1, name: '商队驿站·围院', fp: [4, 3], up: 62, seed: 2401,
    roof: 'gable_tile', tags: ['courtyard', 'enclosed', 'gatehouse', 'wagons'],
    note: '围合院落：后排两层木筋客房，两侧单坡顶货廊向院内落水，前排石砌矮屋正中门楼（大券门可过马车）；院里篷布马车、货箱麻袋、饮马槽',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '', yb = 104, yc = 168;
      o += P.boxShadow(6, 186, 64, yf, 5, W, H);
      o += P.paving(30, yb - 2, 162, yc + 4, 10, r, C.stone);
      // 后排客房
      o += P.gableRoof(6, 186, yb - 34, 34, 14, 'tile', r, { ov: 2 });
      o += P.chimney(40, yb - 66, 9, 20, r) + P.smoke(44, yb - 86, 2, r) + P.chimney(146, yb - 66, 9, 20, r);
      o += P.wall(6, 186, yb - 34, yb, 'timber', r, { bays: 8, floors: 2 });
      [18, 40, 62, 120, 142, 164].forEach(function (x) { o += P.win(x, yb - 31, 7, 9, {}) + P.door(x + 3.5, yb, 9, 14, {}); });
      o += rect(84, yb - 30, 24, 14, C.wash, 1.3) + ln(seg(88, yb - 23, 104, yb - 23), 1.2, 1) + P.door(96, yb, 14, 15, { open: true });
      // 院内：马车、货物、饮马槽
      o += wagon(46, 140, C.paper) + wagon(112, 158, '#e3d3a8');
      o += P.crate(96, 132, 10, 9, 4) + P.crate(100, 124, 9, 8, 4) + sack(84, 134, 9, 10) + sack(152, 136, 9, 10, C.stone);
      o += trough(54, 78, 160) + P.barrel(146, 162, 5, 9);
      // 两侧货廊：单坡顶向院内落水
      // 檐口高 14、外墙高 22：坡度缓、整体压低，后排客房底层仍露在上方
      o += P.slope([32, yc - 14], [32, yb - 14], [6, yb - 22], [6, yc - 22], 'tile', true, r);
      o += P.slope([160, yc - 14], [160, yb - 14], [186, yb - 22], [186, yc - 22], 'tile', false, r);
      o += ln(seg(32, yb - 14, 32, yc - 14), 2.2, 1, C.dark) + ln(seg(160, yb - 14, 160, yc - 14), 2.2, 1, C.dark);
      // 货廊檐下：廊柱（柱脚落在院内地面 = 檐口 y + 14），柱后投一条暗带，读作有顶回廊
      o += flat([[32, yb - 12], [38, yb - 10], [38, yc + 2], [32, yc]], C.shadow, 0.18) + flat([[160, yb - 12], [154, yb - 10], [154, yc + 2], [160, yc]], C.shadow, 0.18);
      [yb - 2, yb + 18, yb + 38].forEach(function (y) {
        o += rect(30.5, y - 14, 3, 14, C.beam, 1.1) + rect(158.5, y - 14, 3, 14, C.beam, 1.1);
        o += sack(41, y + 1, 7, 8, C.stone) + P.crate(146, y + 1, 8, 7, 3);
      });
      // 前排矮屋
      o += P.gableRoof(6, 186, yf - 26, 30, 10, 'tile', r, { ov: 2 });
      o += P.wall(6, 186, yf - 26, yf, 'stone', r, { plinth: 4 });
      [16, 38, 140, 162].forEach(function (x) { o += P.win(x, yf - 20, 8, 9, { shutters: true }); });
      // 门楼：大券门
      o += P.wall(72, 120, yf - 58, yf, 'ashlar', r, { plinth: 5 });
      o += P.pyramid(72, 120, yf - 58, 26, 22, 'tile', r);
      o += path(P.archPath(80, yf - 40, 32, 40), C.stone3, 1.5) + path(P.archPath(83, yf - 37, 26, 37), C.dark, 1.4);
      o += flat([[84, yf - 1], [108, yf - 1], [108, yf - 7], [84, yf - 7]], C.stone2);
      o += P.win(92, yf - 54, 8, 9, { shape: 'arch' }) + banner(78, yf - 54) + banner(114, yf - 54);
      return o;
    }
  });
  /** 蘑菇石（防鼠垫石）：石柱 + 圆帽 */
  function staddle(cx, yb) {
    return rect(cx - 2.5, yb - 9, 5, 9, C.stone2, 1.1) + P.ellipse(cx, yb - 9.5, 5.5, 2, C.stone, 1.1);
  }
  /** 草垛方捆 */
  function hayBale(x0, yb, w, h) {
    var o = P.box(x0, x0 + w, yb, 4, h, C.thatch, '#dcc283', 1.2), d = '';
    for (var x = x0 + 2.5; x < x0 + w - 1; x += 2.6) d += seg(x, yb - h + 1, x + 0.6, yb - 1);
    return o + ln(d, 0.6, 0.45, C.dark) + ln(seg(x0 + w * 0.3, yb - h, x0 + w * 0.3, yb) + seg(x0 + w * 0.7, yb - h, x0 + w * 0.7, yb), 1, 1, C.beam);
  }
  /** 马头（正脸，从半截门探出，下巴搭在门板上）：cx 门中线，yt 半门顶，col 毛色，blaze 是否有白鼻梁 */
  function horseHead(cx, yt, col, blaze) {
    var o = '';
    o += poly([[cx - 4.6, yt - 12], [cx - 4.4, yt - 18.5], [cx - 1.6, yt - 13.6]], col, 1.1) + poly([[cx + 4.6, yt - 12], [cx + 4.4, yt - 18.5], [cx + 1.6, yt - 13.6]], col, 1.1);
    o += path('M' + f(cx - 5) + ' ' + f(yt - 12) + 'Q' + f(cx - 5.4) + ' ' + f(yt - 5) + ' ' + f(cx - 3.2) + ' ' + f(yt + 1.5) + 'Q' + f(cx) + ' ' + f(yt + 4.5) + ' ' + f(cx + 3.2) + ' ' + f(yt + 1.5) +
      'Q' + f(cx + 5.4) + ' ' + f(yt - 5) + ' ' + f(cx + 5) + ' ' + f(yt - 12) + 'Q' + f(cx) + ' ' + f(yt - 16) + ' ' + f(cx - 5) + ' ' + f(yt - 12) + 'Z', col, 1.3);
    if (blaze) o += path('M' + f(cx - 1.2) + ' ' + f(yt - 13) + 'L' + f(cx + 1.2) + ' ' + f(yt - 13) + 'L' + f(cx + 0.9) + ' ' + f(yt - 1) + 'L' + f(cx - 0.9) + ' ' + f(yt - 1) + 'Z', C.paper, 0);
    o += P.ellipse(cx, yt + 0.6, 3.2, 2, C.stone2, 0.9) + P.circle(cx - 1.4, yt + 0.6, 0.6, C.ink, 0) + P.circle(cx + 1.4, yt + 0.6, 0.6, C.ink, 0);
    o += P.circle(cx - 3.4, yt - 8.5, 0.9, C.ink, 0) + P.circle(cx + 3.4, yt - 8.5, 0.9, C.ink, 0);
    o += path('M' + f(cx - 2.2) + ' ' + f(yt - 14.2) + 'Q' + f(cx) + ' ' + f(yt - 11) + ' ' + f(cx + 2.2) + ' ' + f(yt - 14.2) + 'Q' + f(cx) + ' ' + f(yt - 15.8) + ' ' + f(cx - 2.2) + ' ' + f(yt - 14.2) + 'Z', C.dark, 0.8);
    return o;
  }

  // ——————————————————— 粮仓 1：垫石架高的木构粮仓 ———————————————————
  def({
    kind: 'granary', facility: 'granary', variant: 1, name: '粮仓·垫石木仓', fp: [2, 2], up: 58, seed: 2501,
    roof: 'gable_thatch', tags: ['raised', 'staddle_stones', 'storage'],
    note: '英式架高粮仓：九块蘑菇石垫起木板仓身防鼠防潮，厚茅草坡顶，仓门前搭木梯；门口麻袋与一辆独轮车',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '', yb = yf - 12;
      o += P.boxShadow(10, 84, yf - 52, yf, 4, W, H);
      [16, 47, 78].forEach(function (x) { o += staddle(x, yf - 30); });
      o += P.gableRoof(10, 84, yb - 32, 48, 18, 'thatch', r, { ov: 6 });
      o += P.wall(12, 82, yb - 32, yb, 'plank', r);
      o += ln(seg(12, yb - 16, 82, yb - 16) + seg(30, yb - 32, 30, yb) + seg(64, yb - 32, 64, yb), 2.2, 1, C.beam);
      o += P.door(47, yb - 3, 14, 22, { fill: C.beam }) + rect(12, yb - 2, 70, 4, C.dark, 1.1);
      [16, 47, 78].forEach(function (x) { o += staddle(x, yf); });
      // 木梯
      var d = seg(41, yf + 1, 43, yb - 3) + seg(53, yf + 1, 51, yb - 3);
      for (var y = yf - 3; y > yb - 2; y -= 4) d += seg(41.5 + (yf - y) * 0.13, y, 52.5 - (yf - y) * 0.13, y);
      o += ln(d, 1.4, 1, C.beam);
      o += sack(24, H - 2, 9, 10) + sack(32, H - 2, 8, 9, C.stone) + sack(70, H - 2, 9, 10);
      o += P.ellipse(84, H - 6, 3.6, 3.6, C.wood, 1.1) + poly([[78, H - 13], [92, H - 13], [90, H - 7], [80, H - 7]], C.wood, 1.2) + ln(seg(78, H - 13, 70, H - 8), 1.4, 1, C.beam);
      return o;
    }
  });

  // ——————————————————— 粮仓 2：石砌什一税大谷仓 ———————————————————
  def({
    kind: 'granary', facility: 'granary', variant: 2, name: '粮仓·什一税谷仓', fp: [3, 2], up: 60, seed: 2502,
    roof: 'gable_tile', tags: ['tithe_barn', 'storage', 'large'],
    note: '石砌长谷仓：正中凸出的山墙门廊开双扇大车门，墙上一排窄通风缝与扶墙，红瓦长坡顶；门前草垛和麻袋',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '', yE = yf - 30;
      o += P.boxShadow(6, 138, yf - 60, yf, 5, W, H);
      o += P.gableRoof(6, 138, yE, 60, 22, 'tile', r, { ov: 3 });
      o += P.wall(6, 138, yE, yf, 'stone', r, { plinth: 5 });
      [14, 34, 104, 124].forEach(function (x) { o += rect(x, yE + 6, 3, 13, C.dark, 1); });
      [24, 44, 96, 116].forEach(function (x) { o += poly([[x, yf], [x, yE + 6], [x + 4, yE + 4], [x + 6, yf]], C.stone2, 1.1); });
      // 门廊
      var g = P.gableFront(52, 92, yE + 2, 22, 18, 'tile', r, { ov: 2, fill: C.stone });
      o += g.roof + P.wall(52, 92, yE + 2, yf, 'stone', r) + g.gable + P.win(69, yE - 10, 6, 7, { shape: 'arch', panes: false });
      o += P.door(72, yf, 28, 28, { shape: 'arch', frame: C.stone3 }) + ln(seg(72, yf - 28, 72, yf), 1.4, 1, C.dark);
      o += hayBale(8, H - 1, 16, 9) + hayBale(12, H - 10, 12, 8) + sack(110, H - 1, 9, 10) + sack(119, H - 1, 9, 9, C.stone) + sack(128, H - 1, 9, 10);
      return o;
    }
  });

  // ——————————————————— 马厩：长厩房 + 半截门 + 草料阁 ———————————————————
  def({
    kind: 'stable', facility: 'stable', variant: 1, name: '马厩', fp: [3, 2], up: 56, seed: 2601,
    roof: 'gable_thatch', tags: ['horses', 'hayloft', 'dutch_doors'],
    note: '木筋长厩：一排上下分开的半截门，马头从门里探出；正中山墙草料阁门挑出吊货梁与绳钩；门前饮水槽、草垛、马鞍架',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '', yE = yf - 30;
      o += P.boxShadow(6, 138, yf - 50, yf, 5, W, H);
      o += P.gableRoof(6, 138, yE, 50, 18, 'thatch', r, { ov: 5 });
      o += P.wall(6, 138, yE, yf, 'timber', r, { bays: 5, plinth: 4 });
      var g = P.gableFront(56, 88, yE + 2, 20, 18, 'thatch', r, { ov: 3, timber: false });
      o += g.roof + g.gable + rect(65, yE - 13, 14, 12, C.dark, 1.2);
      o += rect(70.5, yE - 21, 3, 7, C.beam, 1) + rect(70, yE - 20, 16, 3, C.beam, 1.1) + ln(seg(84, yE - 17, 84, yE - 4), 0.9, 1) + ln('M82 ' + f(yE - 4) + 'q2 3 4 0', 1, 1, C.slate2);
      var cols = ['#a37b4f', C.wood, C.plaster, '#a37b4f'];
      [20, 44, 100, 124].forEach(function (x, i) {
        o += rect(x - 8, yf - 26, 16, 26, C.dark, 1.3) + horseHead(x, yf - 12, cols[i], i !== 2) + rect(x - 8, yf - 12, 16, 12, C.wood, 1.3) +
          ln(seg(x - 7, yf - 1, x + 7, yf - 11) + seg(x - 4, yf - 12, x - 4, yf), 1, 0.7, C.beam) + P.ellipse(x, yf - 11.4, 3.2, 1.8, cols[i], 0.9) + P.circle(x - 1.4, yf - 11.4, 0.6, C.ink, 0) + P.circle(x + 1.4, yf - 11.4, 0.6, C.ink, 0);
      });
      o += P.door(72, yf, 16, 22, { fill: C.beam });
      o += trough(10, 34, H - 1) + hayBale(106, H - 1, 16, 9) + hayBale(110, H - 10, 11, 7);
      o += rect(56, H - 9, 2.4, 9, C.beam, 1) + poly([[52, H - 10], [62, H - 10], [61, H - 14], [53, H - 14]], C.red, 1.1);
      return o;
    }
  });

  function banner(cx, yt) {
    return path('M' + f(cx - 3) + ' ' + f(yt) + 'L' + f(cx + 3) + ' ' + f(yt) + 'L' + f(cx + 3) + ' ' + f(yt + 12) + 'L' + f(cx) + ' ' + f(yt + 9) + 'L' + f(cx - 3) + ' ' + f(yt + 12) + 'Z', C.red, 1) +
      ln(seg(cx, yt + 1, cx, yt + 8), 1.2, 1, C.wash);
  }

  if (typeof module !== 'undefined' && module.exports) module.exports = defs;
  else root.TownArtWS_trade = defs;
})(typeof window !== 'undefined' ? window : this);
