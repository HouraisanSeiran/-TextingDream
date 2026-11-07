/*
 * 织梦 · 西式文化地标：宗教建筑（哥特大教堂、修道院、山顶岛式修道院）
 * 每项 def 由 west-landmark.js 汇总成 symbol。draw(c) 的 c = { rnd, W, H, up, id }：
 *   W × H 为 viewBox，占地区 y = up..H；锚点 (W/2, H)。建筑前沿一般放在 H-5，给右下投影留位。
 * 浏览器挂 window.TownArtWL_sacred；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var P = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWL_core;
  var C = P.C, f = P.f, seg = P.seg, ln = P.ln, rect = P.rect, poly = P.poly, path = P.path, flat = P.flat;
  var defs = [];
  function def(o) { defs.push(o); }

  /** 带卷叶饰（crocket）的石尖塔：四角攒尖 + 两条外棱上的短钩 + 两道镂空横带 + 顶饰 */
  function spire(x0, x1, yE, dg, h, mat) {
    var o = P.pyramid(x0, x1, yE, dg, h, mat || 'stone', { finial: false, ov: 1 });
    var cx = (x0 + x1) / 2, ap = [cx, yE - dg / 2 - h], L = [x0 - 1, yE + 1], R = [x1 + 1, yE + 1], d = '', band = '';
    for (var t = 0.1; t < 0.93; t += 0.09) {
      var a = P.lerp(L, ap, t), b = P.lerp(R, ap, t);
      d += seg(a[0], a[1], a[0] - 2.6, a[1] - 1.8) + seg(b[0], b[1], b[0] + 2.6, b[1] - 1.8);
    }
    [0.3, 0.58].forEach(function (t) { var a = P.lerp(L, ap, t), b = P.lerp(R, ap, t); band += seg(a[0], a[1], b[0], b[1]); });
    // 镂空的小窗洞（尖塔前面中线两侧）
    var hole = '';
    [0.16, 0.42, 0.68].forEach(function (t) {
      var a = P.lerp(L, ap, t), b = P.lerp(R, ap, t), w = (b[0] - a[0]) * 0.18;
      hole += path(P.pointPath(cx - w / 2, a[1] - w * 2.4, w, w * 2.2), C.dark, 0.7);
    });
    return o + hole + ln(d, 1.1, 0.9) + ln(band, 1.5, 0.85) + P.finial(ap[0], ap[1], 8);
  }
  /** 镂空栏杆：x0..x1，顶 y，高 h；一排小四叶孔 */
  function balustrade(x0, x1, y, h) {
    var o = rect(x0, y, x1 - x0, h, C.stone, 1.2), n = Math.max(2, Math.round((x1 - x0) / 6));
    for (var i = 0; i < n; i++) o += P.circle(x0 + (i + 0.5) * (x1 - x0) / n, y + h / 2, Math.min(1.6, h * 0.28), C.dark, 0);
    return o;
  }
  /** 尖拱山花（wimperg）：底 x0..x1、底线 yb、尖顶 ya；中间一个三叶圆 */
  function wimperg(x0, x1, yb, ya) {
    var cx = (x0 + x1) / 2;
    return poly([[x0, yb], [cx, ya], [x1, yb]], C.stone, 1.3) + ln(P.pd([[x0 + 4, yb - 1], [cx, ya + 5], [x1 - 4, yb - 1]], true), 0.8, 0.55) +
      P.circle(cx, ya + (yb - ya) * 0.48, (x1 - x0) * 0.08, C.dark, 0.8) + P.finial(cx, ya, 4);
  }
  /** 退进式尖拱大门：cx 中线，yf 地坪，w 门洞宽，h 门洞高；层层拱环 + 门楣浮雕 + 门侧立像 */
  function portal(cx, yf, w, h, rings) {
    var o = '', k = rings || 3;
    for (var i = k; i >= 1; i--) {
      var ww = w + i * 7, hh = h + i * 6;
      o += path(P.pointPath(cx - ww / 2, yf - hh, ww, hh), i % 2 ? C.stone3 : C.stone2, 1.2);
      // 拱环上的小雕像（短竖线）
      var d = '';
      for (var t = 0.15; t < 0.9; t += 0.18) d += seg(cx - ww / 2 + 1.8, yf - hh * t, cx - ww / 2 + 1.8, yf - hh * t - 3) + seg(cx + ww / 2 - 1.8, yf - hh * t, cx + ww / 2 - 1.8, yf - hh * t - 3);
      o += ln(d, 1.2, 0.55);
    }
    // 门楣（tympanum）+ 浮雕椭圆
    var dh = h * 0.58;
    o += path(P.pointPath(cx - w / 2, yf - h, w, h - dh + 2), C.stone, 1.2) + P.ellipse(cx, yf - h + (h - dh) * 0.55, w * 0.14, (h - dh) * 0.28, C.stone2, 0.8);
    o += P.door(cx, yf, w, dh, { shape: 'rect', fill: C.beam }) + rect(cx - 1.3, yf - dh, 2.6, dh, C.stone2, 0.9);
    return o;
  }
  /** 哥特西立面塔：x0..x1，前沿 yf，塔身高 h，尖塔高 sh；三段（门 / 长窗 / 钟室）+ 栏杆 + 角尖塔 + 卷叶石尖塔 */
  function westTower(x0, x1, yf, h, sh, r) {
    var w = x1 - x0, cx = (x0 + x1) / 2, yt = yf - h, dg = 32, o = '';
    var s1 = yf - h * 0.34, s2 = yf - h * 0.67;
    o += poly([[x0, yt], [x1, yt], [x1, yt - dg], [x0, yt - dg]], C.stone3, 1.4);
    o += P.pinnacle(x0 + 4, yt - dg + 6, 22, 5) + P.pinnacle(x1 - 4, yt - dg + 6, 22, 5);
    o += spire(x0 + 7, x1 - 7, yt - 3, dg - 8, sh, 'stone');
    o += P.wall(x0, x1, yt, yf, 'ashlar', r, { plinth: 6, ch: 8 });
    // 角扶壁：通高窄条，每段收一次
    [[x0 - 1, 1], [x1 - 6, -1]].forEach(function (b) {
      o += rect(b[0], yt + 2, 7, h - 2, C.stone2, 1.2);
      [s1, s2].forEach(function (s) { o += poly([[b[0] - 0.5, s + 2], [b[0] + 7.5, s + 2], [b[0] + 7.5, s - 3], [b[0] + 3.5, s - 6], [b[0] - 0.5, s - 3]], C.stone3, 1); });
    });
    // 腰线
    [s1, s2].forEach(function (s) { o += rect(x0 + 5, s - 1.5, w - 10, 3, C.stone3, 1); });
    // 第一段：侧门
    o += portal(cx, yf, 14, 38, 2);
    // 第二段：一对长尖窗（彩窗）+ 罩线 + 小圆窗
    o += ln(P.pointPath(cx - 13, s2 + 7, 26, s1 - s2 - 12), 1.2, 0.7);
    o += P.win(cx - 10, s2 + 20, 7, s1 - s2 - 27, { shape: 'point', stain: true }) + P.win(cx + 3, s2 + 20, 7, s1 - s2 - 27, { shape: 'point', stain: true });
    o += P.circle(cx, s2 + 15, 3.4, C.dark, 1) + P.circle(cx, s2 + 15, 1.2, C.red, 0);
    // 第三段：钟室，两道高拱口 + 百叶 + 小山花
    var bt = yt + 16, bh = s2 - bt - 6;
    [cx - 12, cx + 3].forEach(function (x) {
      o += path(P.pointPath(x, bt, 9, bh), C.dark, 1.2);
      var lv = '';
      for (var y = bt + 11; y < bt + bh - 2; y += 4) lv += seg(x + 1.2, y, x + 7.8, y + 1.2);
      o += ln(lv, 1, 0.75, C.wood) + wimperg(x - 1.5, x + 10.5, bt + 2, bt - 10);
    });
    // 顶：镂空栏杆 + 前角小尖塔
    o += balustrade(x0 - 1, x1 + 1, yt - 6, 6);
    o += P.pinnacle(x0 + 2.5, yt - 4, 26, 6) + P.pinnacle(x1 - 2.5, yt - 4, 26, 6);
    return o;
  }
  /** 飞扶壁一组：外墩 px（墩宽 7，dir=1 在左侧向右跨），地面行 yg，跨到 nx；墩高 ph，扶壁落点高 nh */
  function flyer(px, dir, yg, nx, ph, nh, r) {
    var x0 = dir > 0 ? px : px - 7, x1 = x0 + 7, ex = dir > 0 ? x1 : x0, o = '';
    o += rect(x0, yg - ph, 7, ph, C.stone2, 1.3) + P.courses(x0, x1, yg - ph, yg, 7, r, 30);
    var d = 'M' + f(ex) + ' ' + f(yg - ph + 6) + 'L' + f(nx) + ' ' + f(yg - nh - 10) + 'L' + f(nx) + ' ' + f(yg - nh) +
      'Q' + f(ex + dir * 10) + ' ' + f(yg - nh + 2) + ' ' + f(ex) + ' ' + f(yg - ph + 22) + 'Z';
    o += path(d, C.stone, 1.3);
    o += P.pinnacle((x0 + x1) / 2, yg - ph + 1, 18, 7);
    return o;
  }

  /** 单坡侧廊屋顶的一段：外檐 xo（高 ho）、内侧 xi（高 hi），地面进深 g0..g1；up 为 viewBox 上伸 */
  function aisleRoof(xo, xi, ho, hi, g0, g1, up, dark) {
    return P.slope([xo, up + g1 - ho], [xo, up + g0 - ho], [xi, up + g0 - hi], [xi, up + g1 - hi], 'slate', dark);
  }

  // ——————————————————— 哥特大教堂：双塔西立面、玫瑰窗、飞扶壁、十字形平面 ———————————————————
  def({
    kind: 'cathedral', variant: 1, name: '哥特大教堂', fp: [5, 5], up: 240, seed: 2101,
    facility: 'temple', culture: 'gothic', roof: 'steep_slate',
    tags: ['twin_towers', 'rose_window', 'flying_buttress', 'spire', 'transept', 'gothic', 'important'],
    note: '西立面朝前：两座三段式方塔顶着带卷叶饰与镂空的石尖塔，中间山墙下是退进三层的尖拱大门、尖顶山花与大玫瑰窗；' +
      '中殿高耸，两侧侧廊单坡顶上跨着三对飞扶壁；十字交叉部骑一座铅皮小尖塔（flèche），后端半圆后殿带一圈小尖塔',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, U = c.up, yf = H - 5, gf = H - 5 - U, o = '';
      // 平面：双侧廊 x 6..84 / 156..234，中殿 84..156，西立面塔 28..84 / 156..212（塔比侧廊窄，外侧露出飞扶壁）
      var nx0 = 84, nx1 = 156, cx = 120, nh = 110, rise = 44, ng0 = 40, yE = yf - nh, ax0 = 6, ax1 = 234, tw0 = 28, tw1 = 212;
      o += P.boxShadow(8, 232, U + 40, yf, 6, W, H);
      // 后殿：多边形折面半锥顶（7 面），檐口一圈小尖塔
      var ay = U + ng0 - nh, top = [cx, ay - rise * 0.75], N = 7, R = 38, vs = [];
      for (var k = 0; k <= N; k++) { var a = Math.PI + Math.PI * k / N; vs.push([cx + Math.cos(a) * R, ay + Math.sin(a) * R * 0.9]); }
      for (k = 0; k < N; k++) o += P.slope(vs[k], vs[k + 1], top, top, 'slate', k >= N / 2);
      [1, 2, 5, 6].forEach(function (i) { o += P.pinnacle(vs[i][0], vs[i][1] + 3, 22, 5); });
      // 侧廊后段（十字翼之后）
      o += aisleRoof(ax0, nx0, 46, 85, ng0, 90, U, false) + aisleRoof(ax1, nx1, 46, 85, ng0, 90, U, true);
      o += flyer(8, 1, U + 72, nx0, 70, 100, r) + flyer(232, -1, U + 72, nx1, 70, 100, r);
      // 十字翼：屋脊与中殿等高，比侧廊再宽出一点；外端露出的墙面各一扇长尖窗
      o += P.gableRoof(1, 239, U + 130 - nh, 40, rise, 'slate', { ov: 1 });
      o += P.wall(1, 239, U + 130 - nh, U + 130, 'ashlar', r, { ch: 8 });
      o += P.win(9, U + 130 - nh + 12, 7, 30, { shape: 'point', stain: true }) + P.win(224, U + 130 - nh + 12, 7, 30, { shape: 'point', stain: true });
      // 侧廊前段（一直到立面）
      o += aisleRoof(ax0, nx0, 46, 85, 130, gf, U, false) + aisleRoof(ax1, nx1, 46, 85, 130, gf, U, true);
      // 中殿屋顶（山墙朝前），屋脊铸铁饰带 + 屋面两排小老虎窗
      var g = P.gableFront(nx0, nx1, yE, gf - ng0, rise, 'slate', { ov: 2, fill: C.stone });
      o += g.roof;
      var cr = '';
      for (var y = yE - rise - 8; y > yE - rise - (gf - ng0) + 4; y -= 9) cr += seg(cx, y, cx, y - 3.5);
      o += ln(cr, 1.4, 0.8, C.slate2);
      [70, 120].forEach(function (gg) {
        [[cx - 22, false], [cx + 22, true]].forEach(function (s) {
          var dy = U + gg - nh - rise * 0.5;
          o += poly([[s[0] - 5, dy + 6], [s[0] - 5, dy], [s[0], dy - 6], [s[0] + 5, dy], [s[0] + 5, dy + 6]], s[1] ? C.stone2 : C.stone, 1.1) +
            P.win(s[0] - 2, dy - 1, 4, 6, { shape: 'point', panes: false, sill: false });
        });
      });
      // 交叉部铅皮小尖塔
      var ry = yE - rise - (gf - 110);
      o += rect(cx - 9, ry - 26, 18, 28, C.slate, 1.4) + P.win(cx - 6, ry - 22, 4, 14, { shape: 'point', panes: false }) + P.win(cx + 2, ry - 22, 4, 14, { shape: 'point', panes: false });
      o += P.pyramid(cx - 10, cx + 10, ry - 26, 8, 62, 'lead', { finial: false }) + P.cross(cx, ry - 26 - 4 - 62 - 11, 11);
      [cx - 13, cx + 13].forEach(function (x) { o += P.pinnacle(x, ry + 2, 22, 4); });
      // 前排飞扶壁（由后往前）
      [150, 192].forEach(function (gg) { o += flyer(8, 1, U + gg, nx0, 70, 100, r) + flyer(232, -1, U + gg, nx1, 70, 100, r); });
      // 侧廊前墙（塔外侧露出的部分）：斜顶随侧廊屋面，尖窗 + 扶壁
      var hAt = function (x, side) { return 46 + (side ? (ax1 - x) / (ax1 - nx1) : (x - ax0) / (nx0 - ax0)) * 39; };
      o += poly([[ax0, yf - 46], [tw0 + 1, yf - hAt(tw0 + 1, 0)], [tw0 + 1, yf], [ax0, yf]], C.stone, 1.6) + P.courses(ax0, tw0 + 1, yf - 50, yf, 8, r, 15);
      o += poly([[tw1 - 1, yf - hAt(tw1 - 1, 1)], [ax1, yf - 46], [ax1, yf], [tw1 - 1, yf]], C.stone, 1.6) + P.courses(tw1 - 1, ax1, yf - 50, yf, 8, r, 15);
      o += flat([[ax1 - 4, yf - 45], [ax1 - 1, yf - 45], [ax1 - 1, yf - 1], [ax1 - 4, yf - 1]], C.shadow, 0.12);
      o += P.win(13, yf - 38, 7, 24, { shape: 'point', stain: true }) + P.win(220, yf - 38, 7, 24, { shape: 'point', stain: true });
      // 中央立面：山墙 + 墙体 + 玫瑰窗 + 山墙壁龛 + 大门 + 尖顶山花 + 台阶
      o += g.gable + P.wall(nx0, nx1, yE, yf, 'ashlar', r, { plinth: 6, ch: 8 });
      o += P.arcade(103, 137, yE - 18, yE - 6, 4, 2, { fill: C.stone3 });
      o += P.roseWindow(cx, yE + 3, 18, 12);
      o += P.win(89, yE + 30, 6, 30, { shape: 'point', stain: true }) + P.win(145, yE + 30, 6, 30, { shape: 'point', stain: true });
      o += portal(cx, yf, 26, 46, 3);
      o += wimperg(95, 145, yf - 63, yf - 85);
      o += rect(92, yf, 56, 2.4, C.stone2, 1) + rect(88, yf + 2.4, 64, 2.4, C.stone3, 1);
      // 西立面双塔
      o += westTower(tw0, nx0, yf, 150, 196, r) + westTower(nx1, tw1, yf, 150, 196, r);
      return o;
    }
  });

  /** 伦巴第小拱带：x0..x1，y 为拱脚，step 拱宽 */
  function lombard(x0, x1, y, step) {
    var d = '';
    for (var x = x0; x < x1 - step + 0.5; x += step) d += 'M' + f(x) + ' ' + f(y) + 'A' + f(step / 2) + ' ' + f(step / 2) + ' 0 0 1 ' + f(x + step) + ' ' + f(y);
    return ln(d, 0.9, 0.7);
  }
  /** 双联拱窗（钟室）：x 左，y 拱顶，w 总宽，h 高；中间小柱 */
  function biforate(x, y, w, h) {
    var a = (w - 3) / 2;
    return path(P.archPath(x - 2, y - 2, w + 4, h + 2), C.stone3, 1.2) + path(P.archPath(x, y, a, h), C.dark, 1.1) +
      path(P.archPath(x + a + 3, y, a, h), C.dark, 1.1) + rect(x + a + 0.6, y + a * 0.5, 1.8, h - a * 0.5, C.stone, 0.7);
  }
  /** 小民居（山城、修道院附属）：x 左，yb 地面，w 宽，h 墙高；side=1 屋脊平行正面，否则山墙朝前 */
  function miniHouse(x, yb, w, h, kind, mat, side, r) {
    var o = '', yE = yb - h;
    if (side) o += P.gableRoof(x, x + w, yE, 10, 5 + w * 0.12, mat, { ov: 1.5 });
    else { var g = P.gableFront(x, x + w, yE, 10, w * 0.5, mat, { ov: 1.5, fill: kind === 'stone' ? C.stone : C.plaster }); o += g.roof + g.gable; }
    o += P.wall(x, x + w, yE, yb, kind, r, { sw: 1.3, ch: 5 });
    var n = Math.max(1, Math.floor(w / 8));
    for (var i = 0; i < n; i++) o += P.win(x + (i + 0.5) * w / n - 1.5, yE + 2.5, 3, 4, { panes: false, sill: false, sw: 0.8 });
    if (h >= 12 && r() < 0.65) o += rect(x + w * (0.3 + r() * 0.4) - 1.8, yb - 5.5, 3.6, 5.5, C.beam, 0.8);
    return o;
  }

  // ——————————————————— 罗曼式修道院（平地）：教堂 + 钟楼 + 回廊庭院 + 修士宿舍 + 食堂 + 菜园 ———————————————————
  def({
    kind: 'abbey', variant: 1, name: '罗曼式修道院', fp: [6, 5], up: 170, seed: 2201,
    facility: 'temple', culture: 'romanesque', roof: 'gable_tile',
    tags: ['cloister', 'bell_tower', 'apse', 'dormitory', 'refectory', 'kitchen_garden', 'orchard', 'romanesque', 'important'],
    note: '平地修道院：后排是长边朝前的罗曼式教堂（壁柱、半圆拱窗、伦巴第小拱带、东端半圆后殿、交叉部八角小塔），' +
      '西端高大方钟楼带双联拱钟室；教堂南侧方形回廊庭院（拱廊、中央泉亭），左翼两层修士宿舍，右翼食堂与厨房烟囱；前排菜园、果树与碎石前院',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, U = c.up, o = '';
      function Y(g, h) { return U + g - (h || 0); }
      o += P.boxShadow(10, 280, Y(30), H - 5, 6, W, H);
      // 前院碎石地
      o += rect(84, Y(200), 148, 34, C.sand, 1, 'stroke-opacity="0.4"');
      // 东端半圆后殿（教堂右端之后）
      o += P.cylinder(250, Y(54), 24, 40, C.stone, 'stone', r) + P.cone(250, Y(54, 40), 24, 22, 'tile', { finial: false });
      o += P.win(256, Y(54, 30), 5, 12, { shape: 'arch', panes: false }) + P.win(266, Y(54, 28), 4, 11, { shape: 'arch', panes: false });
      // 教堂：长边朝前，x 64..252，前墙 g=82，墙高 58
      var yE = Y(82, 58), x0 = 64, x1 = 252;
      o += P.gableRoof(x0, x1, yE, 56, 26, 'tile', { ov: 3 });
      // 交叉部八角小塔（骑在屋脊上）
      o += rect(198, yE - 66, 26, 42, C.stone, 1.5) + P.courses(198, 224, yE - 66, yE - 24, 6, r, 8);
      o += ln(seg(204.5, yE - 66, 204.5, yE - 25) + seg(217.5, yE - 66, 217.5, yE - 25), 0.9, 0.6);
      o += biforate(205.5, yE - 60, 11, 14) + lombard(199, 223, yE - 64, 4);
      o += P.pyramid(198, 224, yE - 66, 14, 26, 'tile', { finial: false }) + P.cross(211, yE - 66 - 7 - 26 - 11, 11);
      o += P.wall(x0, x1, yE, Y(82), 'stone', r, { plinth: 5 });
      o += lombard(x0 + 2, x1 - 2, yE + 6, 6);
      [92, 124, 156, 188, 220].forEach(function (x) { o += rect(x, yE + 7, 4, 51, C.stone2, 1.1); });
      [74, 104, 136, 168, 200, 232].forEach(function (x) { o += P.win(x, yE + 11, 8, 15, { shape: 'arch', stain: true }); });
      // 回廊：地坪 + 庭院草地 + 十字甬道 + 泉亭
      o += P.paving(84, Y(84), 226, Y(200), 7, r, C.stone2);
      o += rect(98, Y(98), 114, 88, '#b3b47c', 1.2);
      o += rect(151, Y(98), 8, 88, C.stone, 0.8) + rect(98, Y(138), 114, 8, C.stone, 0.8);
      [[110, Y(124)], [198, Y(124)], [110, Y(178)], [198, Y(178)]].forEach(function (p) { o += P.bush(p[0], p[1], 6, r); });
      o += P.ellipse(155, Y(142), 15, 7.5, C.stone3, 1.4) + P.ellipse(155, Y(142, 2), 12, 6, C.water, 1);
      o += P.cylinder(155, Y(142, 2), 3, 14, C.stone, 'plain') + P.ellipse(155, Y(142, 16), 7, 3.5, C.stone2, 1) + P.finial(155, Y(142, 17), 5);
      // 北廊：靠教堂的单坡顶 + 朝庭院的拱廊立面
      o += P.slope([84, Y(98, 16)], [226, Y(98, 16)], [226, Y(84, 26)], [84, Y(84, 26)], 'tile', false);
      o += rect(98, Y(98, 16), 114, 16, C.stone, 1.3) + P.arcade(98, 212, Y(98, 7), Y(98), 9, 3, { fill: C.dark });
      // 东西两廊屋面（单坡，外高内低）
      o += P.slope([98, Y(186, 16)], [98, Y(98, 16)], [84, Y(98, 24)], [84, Y(186, 24)], 'tile', false);
      o += P.slope([212, Y(186, 16)], [212, Y(98, 16)], [226, Y(98, 24)], [226, Y(186, 24)], 'tile', true);
      // 钟楼：x 18..66，前沿 g=92，高 150
      var tx0 = 18, tx1 = 66, tcx = 42, tyf = Y(92), tyt = Y(92, 150);
      o += P.pyramid(tx0, tx1, tyt, 30, 44, 'tile', { finial: false }) + P.cross(tcx, tyt - 15 - 44 - 13, 13);
      o += P.wall(tx0, tx1, tyt, tyf, 'ashlar', r, { plinth: 6, ch: 8 });
      [0.32, 0.6, 0.82].forEach(function (t) { var y = tyf - 150 * t; o += rect(tx0 - 1.5, y - 1.5, tx1 - tx0 + 3, 3, C.stone3, 1.1) + lombard(tx0 + 1, tx1 - 1, y + 7, 6); });
      o += rect(tx0 - 1.5, tyt - 2, tx1 - tx0 + 3, 3.5, C.stone3, 1.2);
      o += biforate(22, tyt + 6, 17, 18) + biforate(45, tyt + 6, 17, 18);
      o += biforate(31, tyf - 84, 22, 20) + P.win(38, tyf - 40, 8, 14, { shape: 'arch', stain: true });
      o += P.door(tcx, tyf, 15, 24, { shape: 'arch', frame: C.stone3 });
      // 修士宿舍（左翼，山墙朝前，两层：底层石砌，上层灰泥）
      var dyE = Y(206, 50), dg = P.gableFront(26, 84, dyE, 106, 28, 'tile', { ov: 2, fill: C.plaster });
      o += dg.roof + dg.gable + P.wall(26, 84, dyE, Y(206, 24), 'plaster', r) + P.wall(26, 84, Y(206, 24), Y(206), 'stone', r, { plinth: 4 });
      o += ln(seg(26, Y(206, 24), 84, Y(206, 24)), 2.2, 1, C.beam);
      [33, 47, 61, 75].forEach(function (x) { o += P.win(x - 3, dyE + 6, 6, 9, { shutters: false }); });
      o += P.win(52, dyE - 14, 6, 8, { shape: 'arch', panes: false });
      o += P.win(34, Y(206, 18), 6, 10, { shape: 'arch' }) + P.win(70, Y(206, 18), 6, 10, { shape: 'arch' }) + P.door(55, Y(206), 11, 17, { shape: 'arch' });
      // 食堂（右翼，石砌山墙朝前，高拱窗，屋面上厨房烟囱）
      var ryE = Y(196, 40), rg = P.gableFront(226, 282, ryE, 100, 26, 'tile', { ov: 2, fill: C.stone });
      o += rg.roof + P.chimney(262, ryE - 34, 9, 26, r) + rg.gable + P.wall(226, 282, ryE, Y(196), 'stone', r, { plinth: 4 });
      o += P.circle(254, ryE - 10, 4.5, C.dark, 1.2) + P.circle(254, ryE - 10, 1.6, C.red, 0);
      o += P.win(236, ryE + 7, 8, 24, { shape: 'arch', stain: true }) + P.win(264, ryE + 7, 8, 24, { shape: 'arch', stain: true }) + P.door(254, Y(196), 11, 18, { shape: 'arch' });
      o += P.smoke(266, ryE - 64, 3, r);
      // 南廊外墙 + 单坡顶 + 回廊门
      o += P.slope([84, Y(200, 22)], [226, Y(200, 22)], [226, Y(186, 16)], [84, Y(186, 16)], 'tile', true);
      o += P.wall(84, 226, Y(200, 22), Y(200), 'stone', r, { plinth: 3 });
      [96, 112, 128, 176, 192, 208].forEach(function (x) { o += P.win(x, Y(200, 17), 5, 9, { shape: 'arch', panes: false }); });
      o += P.door(155, Y(200), 12, 17, { shape: 'arch', frame: C.stone3 });
      // 菜园（左前）+ 篱笆；果树（右前）；前院石十字
      o += P.beds(10, Y(212), 80, Y(232), 4, r);
      var fe = '';
      for (var x = 10; x <= 80; x += 5) fe += seg(x, Y(234), x, Y(234, 6));
      o += ln(fe + seg(9, Y(234, 4), 81, Y(234, 4)), 1, 0.85, C.beam);
      o += P.tree(244, Y(230), 10, r) + P.tree(266, Y(222), 9, r) + P.tree(282, Y(233), 8, r);
      o += rect(182, Y(226, 3), 8, 3, C.stone2, 1) + P.cross(186, Y(226, 20), 17);
      return o;
    }
  });

  /** 一排山城民居：沿 yb 行，从 xa 到 xb，落脚点都要在岩体 rock 内；返回 svg */
  function houseRow(rock, yb, xa, xb, r) {
    var o = '', x = xa;
    while (x < xb - 10) {
      var w = 12 + Math.floor(r() * 9), h = 9 + Math.floor(r() * 7);
      if (x + w > xb) break;
      if (P.inside(rock, x - 1, yb + 3) && P.inside(rock, x + w + 1, yb + 3)) {
        if (r() < 0.14) o += P.bush(x + w / 2, yb + 1, 6, r);
        else o += miniHouse(x, yb, w, h, r() < 0.55 ? 'plaster' : 'stone', r() < 0.6 ? 'slate' : 'tile', r() < 0.5, r);
      }
      x += w + 1 + Math.floor(r() * 3);
    }
    return o;
  }

  // ——————————————————— 山顶岛式修道院：岩石山体 + 层叠民居 + 环岛城墙 + 山顶哥特修道院与尖塔 ———————————————————
  def({
    kind: 'abbey', variant: 2, name: '山顶岛式修道院', fp: [6, 6], up: 240, seed: 2202,
    facility: 'temple', culture: 'gothic', roof: 'steep_slate',
    tags: ['island', 'hilltop', 'crag', 'spire', 'ramparts', 'village', 'pilgrimage', 'tidal_flat', 'gothic', 'important'],
    note: '潮间沙洲上的岩石孤山：山脚一圈带圆塔与门楼的城墙，墙内民居沿山坡层层叠起，左坡有一座带小尖塔的教区小教堂；' +
      '山顶是筑在高大基台上的哥特修道院教堂，右侧悬崖上贴着一座带扶壁的高楼（修院主楼），交叉部方塔顶着铅皮尖塔与金色天使像。' +
      '整座占地即岛体，民居是画在 symbol 里的，不另占格',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '';
      o += P.boxShadow(14, 274, 300, yf, 6, W, H);
      // 潮间沙洲 + 几汪积水
      o += P.ellipse(144, yf - 16, 142, 19, C.sand, 1.2);
      [[40, yf - 6, 18], [236, yf - 4, 22], [150, yf - 2, 12]].forEach(function (p) { o += P.ellipse(p[0], p[1], p[2], p[2] * 0.22, C.water, 0.9); });
      // 岩石山体
      var rock = [[10, 500], [22, 452], [44, 410], [62, 372], [84, 336], [100, 300], [112, 272], [130, 262], [196, 258], [214, 276],
        [230, 310], [246, 352], [262, 400], [274, 450], [280, 500]];
      o += P.crag(rock, r, { strata: 30 });
      // 山顶基台（筑在岩上的墙，带扶壁）
      o += P.wall(104, 236, 288, 334, 'ashlar', r, { ch: 8 });
      [112, 140, 168, 196, 224].forEach(function (x) { o += P.buttress(x, 334, 292, 6); });
      // 修道院教堂：长边朝前，x 108..232，墙 250..290
      o += P.gableRoof(108, 232, 250, 40, 22, 'slate', { ov: 2 });
      // 交叉部方塔 + 铅皮尖塔 + 金天使
      o += rect(156, 150, 28, 60, C.stone, 1.5) + P.courses(156, 184, 150, 210, 7, r, 10);
      o += path(P.pointPath(160, 158, 8, 26), C.dark, 1.1) + path(P.pointPath(172, 158, 8, 26), C.dark, 1.1);
      o += balustrade(154, 186, 146, 5) + P.pinnacle(156, 148, 20, 5) + P.pinnacle(184, 148, 20, 5);
      o += spire(158, 182, 146, 10, 96, 'lead');
      o += path('M170 37l-2.4 5.5h1.5l-1 6h3.8l-1-6h1.5Z', C.wash, 0.8) + ln(seg(166, 39, 174, 37), 1, 0.9, C.wash);
      // 教堂正墙：尖窗 + 扶壁 + 墙顶小尖塔
      o += P.wall(108, 232, 250, 290, 'ashlar', r, { ch: 8 });
      [116, 134, 152, 188, 206, 222].forEach(function (x) { o += P.win(x - 3, 258, 6, 22, { shape: 'point', stain: true }); });
      [125, 143, 170, 197, 214].forEach(function (x) { o += rect(x - 2, 256, 4, 34, C.stone2, 1); o += P.pinnacle(x, 254, 16, 4); });
      o += P.roseWindow(170, 270, 9, 8);
      // 左侧修院附楼（山墙朝前）
      var lg = P.gableFront(92, 124, 282, 30, 20, 'slate', { ov: 2, fill: C.stone });
      o += lg.roof + lg.gable + P.wall(92, 124, 282, 322, 'stone', r, { plinth: 4 });
      o += P.win(100, 290, 5, 10, { shape: 'point' }) + P.win(111, 290, 5, 10, { shape: 'point' }) + P.win(105, 304, 6, 10, { shape: 'arch' });
      // 右侧悬崖高楼（修院主楼）：高墙、长窄窗、通高扶壁
      o += P.gableRoof(194, 250, 300, 18, 8, 'slate', { ov: 2 });
      o += P.wall(194, 250, 300, 378, 'ashlar', r, { ch: 8 });
      [200, 216, 232].forEach(function (x) { o += P.win(x + 1, 308, 5, 26, { shape: 'point' }) + P.win(x + 2, 346, 4, 14, { shape: 'point', panes: false }); });
      [196, 212, 228, 244].forEach(function (x) { o += rect(x - 2.5, 304, 5, 74, C.stone2, 1.1) + poly([[x - 3, 304], [x + 3, 304], [x, 296]], C.stone3, 1); });
      // 登山石阶（左坡折线）
      o += ln('M60 470L96 452L70 432L104 412L84 392L112 372L100 352L120 336', 2.6, 0.6, C.stone3);
      // 层叠民居（后排先画）
      o += houseRow(rock, 360, 84, 190, r);
      o += houseRow(rock, 388, 66, 196, r);
      // 教区小教堂（左坡）：山墙朝前 + 小尖塔
      var cg = P.gableFront(52, 74, 412, 20, 14, 'slate', { ov: 1.5, fill: C.stone });
      o += cg.roof + rect(59, 376, 8, 22, C.stone, 1.2) + P.pyramid(58, 68, 376, 5, 22, 'slate', { finial: false }) + P.cross(63, 336, 7);
      o += cg.gable + P.wall(52, 74, 412, 434, 'stone', r, { ch: 5 }) + P.door(63, 434, 7, 11, { shape: 'point' });
      o += houseRow(rock, 416, 78, 258, r);
      o += houseRow(rock, 444, 30, 266, r);
      o += houseRow(rock, 472, 22, 272, r);
      [[40, 446], [250, 418], [232, 388], [262, 470]].forEach(function (p) { if (P.inside(rock, p[0], p[1])) o += P.tree(p[0], p[1], 8, r); });
      // 环岛城墙：墙段 + 垛口 + 圆塔 + 中央门楼
      o += P.wall(14, 274, 482, 504, 'stone', r, { ch: 6 }) + P.merlons(14, 274, 482, 4, 3.5, C.stone);
      [[86, 10, 30], [204, 10, 30]].forEach(function (t) { o += P.cylinder(t[0], 508, t[1], t[2], C.stone, 'stone', r) + P.ringMerlons(t[0], 508 - t[2], t[1], 5); });
      [[26, 13, 38], [262, 13, 38]].forEach(function (t) {
        o += P.cylinder(t[0], 508, t[1], t[2], C.stone, 'stone', r, { top: false }) + P.cone(t[0], 508 - t[2], t[1], 22, 'slate', { finial: false });
      });
      o += rect(128, 466, 32, 42, C.stone, 1.6) + P.courses(128, 160, 466, 508, 6, r, 9) + P.merlons(127, 161, 466, 4.5, 3.5, C.stone);
      o += path(P.archPath(136, 486, 16, 22), C.dark, 1.4);
      var pc = '';
      for (var x = 139; x < 152; x += 4) pc += seg(x, 490, x, 506);
      o += ln(pc + seg(137, 496, 151, 496) + seg(137, 502, 151, 502), 1, 1, C.slate2) + P.flag(144, 466, 18, 12, C.red);
      return o;
    }
  });

  if (typeof module !== 'undefined' && module.exports) module.exports = defs;
  else root.TownArtWL_sacred = defs;
})(typeof window !== 'undefined' ? window : this);
