/*
 * 织梦 · 西式特殊建筑：工坊与公共建筑（铁匠铺、行政厅、领主府、教堂）
 * 每项 def 由 west-special.js 汇总成 symbol。draw(c) 的 c = { rnd, W, H, up, id }：
 *   W × H 为 viewBox，占地区是 y = up .. H；锚点 (W/2, H)。建筑前沿一般放在 H-5，给右下投影留位。
 * 浏览器挂 window.TownArtWS_civic；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var P = (typeof module !== 'undefined' && module.exports) ? require('./prims.js') : root.TownArtWS_prims;
  var C = P.C, f = P.f, seg = P.seg, ln = P.ln, rect = P.rect, poly = P.poly, path = P.path, flat = P.flat;
  var defs = [];
  function def(o) { defs.push(o); }

  /** 炉火：炉口内一团火苗（橘红 + 淡黄平涂） */
  function fire(cx, yb, w) {
    var h = w * 0.9;
    var outer = 'M' + f(cx - w / 2) + ' ' + f(yb) + 'Q' + f(cx - w / 2) + ' ' + f(yb - h * 0.5) + ' ' + f(cx - w * 0.2) + ' ' + f(yb - h * 0.7) +
      'Q' + f(cx - w * 0.15) + ' ' + f(yb - h * 0.35) + ' ' + f(cx) + ' ' + f(yb - h) + 'Q' + f(cx + w * 0.2) + ' ' + f(yb - h * 0.45) + ' ' + f(cx + w * 0.3) + ' ' + f(yb - h * 0.7) +
      'Q' + f(cx + w / 2) + ' ' + f(yb - h * 0.4) + ' ' + f(cx + w / 2) + ' ' + f(yb) + 'Z';
    var inner = 'M' + f(cx - w * 0.25) + ' ' + f(yb) + 'Q' + f(cx - w * 0.2) + ' ' + f(yb - h * 0.4) + ' ' + f(cx) + ' ' + f(yb - h * 0.6) +
      'Q' + f(cx + w * 0.2) + ' ' + f(yb - h * 0.4) + ' ' + f(cx + w * 0.25) + ' ' + f(yb) + 'Z';
    return path(outer, C.tile, 0.9) + path(inner, C.wash, 0) ;
  }
  /** 风箱：两块木板夹一层皮革，嘴朝左；x 右端，yc 中线 */
  function bellows(x, yc, sc) {
    var s = sc || 1;
    var o = path('M' + f(x - 15 * s) + ' ' + f(yc) + 'L' + f(x) + ' ' + f(yc - 5 * s) + 'L' + f(x) + ' ' + f(yc + 5 * s) + 'Z', C.dark, 1.2);
    o += poly([[x - 15 * s, yc - 0.6], [x, yc - 6 * s], [x, yc - 3.8 * s]], C.wood, 1.1);
    o += ln(seg(x - 15 * s, yc, x - 20 * s, yc) , 1.8, 1, C.slate2) + ln(seg(x, yc - 5.5 * s, x + 4 * s, yc - 9 * s), 1.4, 1, C.beam);
    return o;
  }
  /** 磨刀砂轮：木架 + 石轮，cx 中线，yb 地面 */
  function grindstone(cx, yb) {
    return ln(seg(cx - 7, yb, cx - 4, yb - 9) + seg(cx + 7, yb, cx + 4, yb - 9), 1.6, 1, C.beam) +
      P.circle(cx, yb - 11, 6.5, C.stone2, 1.4) + P.circle(cx, yb - 11, 1.4, C.dark, 0.8) +
      ln(seg(cx + 1, yb - 11, cx + 9, yb - 14), 1.2, 1, C.dark);
  }
  /** 墙上挂的工具：火钳、锤子、马蹄铁 */
  function tools(x, y) {
    return ln(seg(x, y, x + 2, y + 12) + seg(x + 3, y, x + 2, y + 12), 0.9, 0.9, C.slate2) +
      ln(seg(x + 8, y, x + 8, y + 11), 1.3, 1, C.beam) + rect(x + 5.5, y - 1, 5, 2.6, C.slate2, 0.8) +
      P.horseshoe(x + 15, y + 3, 2.4) + P.horseshoe(x + 21, y + 6, 2.4);
  }

  // ——————————————————— 铁匠铺 1：石屋 + 开敞作坊棚 ———————————————————
  def({
    kind: 'forge', facility: 'forge', variant: 1, name: '铁匠铺·作坊棚', fp: [3, 2], up: 76, seed: 1101,
    roof: 'gable_tile', tags: ['workshop', 'open_shed', 'smoke', 'important'],
    note: '左侧石砌住屋，右侧开敞作坊棚：炉膛与烟囱、风箱、铁砧、淬火水桶、檐下马蹄铁招牌；棚顶为单坡木瓦（monopitch）',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '';
      o += P.boxShadow(6, 140, yf - 56, yf, 4, W, H);
      // 作坊棚内部：后墙下段、夯土地面
      o += rect(81, 118, 58, yf - 12 - 118, C.stone3, 1.2) + P.courses(81, 139, 118, yf - 12, 6, r, 9);
      o += poly([[80, yf - 12], [140, yf - 12], [141, yf], [79, yf]], C.stone2, 1.1);
      o += tools(116, 124);
      // 炉膛：砖砌台 + 拱形炉口 + 炉火；上方石砌烟罩
      o += poly([[84, yf - 34], [108, yf - 34], [103, 112], [89, 112]], C.stone2, 1.4) + P.courses(84, 108, 112, yf - 34, 5, r, 7);
      o += P.box(83, 109, yf - 6, 7, 18, C.stone2, C.stone3, 1.4) + P.courses(83, 109, yf - 24, yf - 6, 4, r, 7);
      o += path(P.archPath(90, yf - 22, 12, 13), C.dark, 1.2) + fire(96, yf - 10, 9);
      o += bellows(124, yf - 22, 1);
      // 左侧石屋
      o += P.gableRoof(6, 78, yf - 36, 56, 20, 'tile', r);
      o += P.wall(6, 78, yf - 36, yf, 'stone', r, { plinth: 5 });
      o += P.door(26, yf, 12, 21, { shape: 'arch', frame: C.stone3 }) + P.win(46, yf - 28, 9, 11, { shutters: true }) + P.win(64, yf - 28, 7, 11, {});
      // 作坊棚单坡顶（木瓦），前檐 yf-40
      o += P.slope([78, yf - 39], [143, yf - 39], [143, 74], [78, 74], 'shingle', false, r) + P.fascia(78, 143, yf - 39.5, 2.6);
      // 炉子烟囱穿出棚顶 + 烟
      o += P.chimney(90, 104, 12, 68, r) + P.smoke(96, 32, 3, r);
      // 立柱
      o += rect(80, yf - 37, 3.5, 37, C.beam, 1.3) + rect(137.5, yf - 37, 3.5, 37, C.beam, 1.3);
      o += ln(seg(83.5, yf - 30, 90, yf - 37) + seg(137.5, yf - 30, 131, yf - 37), 1.6, 1, C.beam);
      // 檐下吊着的马蹄铁招牌
      o += ln(seg(121, yf - 37, 121, yf - 33) + seg(133, yf - 37, 133, yf - 33), 0.9, 1);
      o += rect(118, yf - 33, 18, 12, C.wash, 1.3) + P.horseshoe(127, yf - 28.5, 3.4);
      // 铁砧、淬火水桶
      o += P.anvil(118, yf - 1, 1.15) + P.barrel(72, yf, 5.5, 10, true);
      return o;
    }
  });

  // ——————————————————— 铁匠铺 2：山墙朝前石作坊 + 外挂大烟囱 ———————————————————
  def({
    kind: 'forge', facility: 'forge', variant: 2, name: '铁匠铺·山墙作坊', fp: [2, 2], up: 70, seed: 1102,
    roof: 'gable_tile', tags: ['workshop', 'smoke', 'important'],
    note: '山墙朝前的石作坊，敞开的大拱门里看得见炉火；右侧外挂石烟囱，门前铁砧与磨刀砂轮，山尖钉马蹄铁',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 18, o = '';
      o += P.boxShadow(8, 84, yf - 48, yf, 4, W, H);
      o += poly([[4, yf - 2], [92, yf - 2], [94, H - 3], [2, H - 3]], C.stone2, 1, 'stroke-opacity="0.5"');
      var g = P.gableFront(8, 70, yf - 34, 48, 24, 'tile', r, { timber: false, fill: C.stone });
      o += g.roof + g.gable + P.courses(14, 64, yf - 50, yf - 34, 6, r, 10);
      o += P.wall(8, 70, yf - 34, yf, 'stone', r, { plinth: 4 });
      // 敞开的大拱门：门洞深色，里面炉火
      o += path(P.archPath(26, yf - 27, 26, 27), C.stone3, 1.4) + path(P.archPath(29, yf - 24, 20, 24), C.dark, 1.4);
      o += rect(31, yf - 9, 16, 9, C.stone3, 1) + fire(39, yf - 9, 10);
      // 山尖：钉一只大马蹄铁
      o += P.horseshoe(39, yf - 45, 5);
      o += P.win(12, yf - 24, 7, 10, {}) + P.win(58, yf - 24, 7, 10, {});
      // 右侧外挂烟囱（地面起到高出屋脊）
      o += P.chimney(70, yf, 14, yf - 38, r, { fill: C.stone2 }) + P.smoke(77, 32, 3, r);
      // 门前：铁砧、砂轮、水桶、一堆铁条
      o += P.anvil(17, H - 4, 1.05) + grindstone(62, H - 4) + P.barrel(88, H - 4, 4.5, 9, true);
      o += ln(seg(44, H - 6, 54, H - 9) + seg(45, H - 5, 55, H - 8) + seg(46, H - 4, 56, H - 7), 1.3, 1, C.slate2);
      return o;
    }
  });

  /** 钟面：白底罗马钟 */
  function clock(cx, cy, r) {
    var d = '';
    for (var i = 0; i < 12; i++) { var a = i * Math.PI / 6; d += seg(cx + Math.cos(a) * r * 0.72, cy + Math.sin(a) * r * 0.72, cx + Math.cos(a) * r * 0.9, cy + Math.sin(a) * r * 0.9); }
    return P.circle(cx, cy, r + 1.6, C.wash, 1.4) + P.circle(cx, cy, r, C.paper, 1.1) + ln(d, 0.8, 0.8) +
      ln(seg(cx, cy, cx, cy - r * 0.62) + seg(cx, cy, cx + r * 0.45, cy + r * 0.2), 1.2, 1);
  }
  /** 钟楼开口里的钟 */
  function bell(cx, yt, w) {
    return path('M' + f(cx - w * 0.3) + ' ' + f(yt + w * 0.9) + 'Q' + f(cx - w * 0.32) + ' ' + f(yt) + ' ' + f(cx) + ' ' + f(yt) + 'Q' + f(cx + w * 0.32) + ' ' + f(yt) + ' ' + f(cx + w * 0.3) + ' ' + f(yt + w * 0.9) +
      'L' + f(cx + w * 0.45) + ' ' + f(yt + w * 1.05) + 'L' + f(cx - w * 0.45) + ' ' + f(yt + w * 1.05) + 'Z', C.wash, 1.1);
  }
  /** 阶梯山墙（佛兰德式）：底 x0..x1 于 yb，顶 yt，n 阶 */
  function steppedGable(x0, x1, yb, yt, n, fill) {
    var cx = (x0 + x1) / 2, hw = (x1 - x0) / 2, pts = [[x0, yb]], h = (yb - yt) / (n + 0.6);
    for (var i = 0; i < n; i++) { var x = x0 + hw * i / (n + 0.3), y = yb - h * (i + 1); pts.push([x, y], [x0 + hw * (i + 1) / (n + 0.3), y]); }
    var L = pts.slice(), R = L.slice(1).reverse().map(function (p) { return [2 * cx - p[0], p[1]]; });
    var top = [[L[L.length - 1][0], yt], [R[0][0], yt]];
    return poly(L.concat(top, R, [[x1, yb]]), fill || C.stone, 1.6);
  }

  // ——————————————————— 行政厅 1：拱廊市政厅 + 正中钟楼 ———————————————————
  def({
    kind: 'town_hall', facility: 'town_hall', variant: 1, name: '市政厅·钟楼', fp: [3, 2], up: 120, seed: 1201,
    roof: 'gable_tile', tags: ['bell_tower', 'clock', 'arcade', 'important'],
    note: '底层石砌拱廊（可作集会/避雨），二层木筋议事厅，红瓦坡顶；正中凸出方形钟楼：钟面、钟口、青石板攒尖顶与城旗',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '', y1 = yf - 26, y2 = yf - 52;
      o += P.boxShadow(6, 138, yf - 54, yf, 5, W, H);
      o += P.gableRoof(6, 138, y2, 54, 20, 'tile', r);
      o += P.chimney(20, y2 - 14, 8, 16, r);
      o += P.wall(6, 138, y2, y1, 'timber', r, { bays: 6 });
      [14, 36, 98, 120].forEach(function (x) { o += P.win(x + 2, y2 + 7, 8, 12, {}); });
      o += P.wall(6, 138, y1, yf, 'ashlar', r);
      [10, 30, 96, 116].forEach(function (x) { o += path(P.archPath(x, y1 + 5, 16, 21), C.dark, 1.4) + ln(seg(x + 2, yf - 1, x + 14, yf - 1), 1, 0.6, C.stone); });
      o += ln(seg(6, y1, 138, y1), 2.4, 1);
      // 钟楼：前面 56..88，墙顶 78
      var tx0 = 55, tx1 = 89, yt = 80;
      o += P.wall(tx0, tx1, yt, yf, 'ashlar', r, { plinth: 6 });
      o += rect(tx0 - 2, yt - 3, tx1 - tx0 + 4, 5, C.stone3, 1.4);
      o += path(P.archPath(64, yt + 8, 16, 22), C.dark, 1.4) + bell(72, yt + 13, 12) + ln(seg(64, yt + 22, 80, yt + 22), 1.2, 1, C.beam);
      o += clock(72, yt + 45, 8.5);
      o += P.win(68, yt + 64, 8, 12, { shape: 'arch' });
      o += P.door(72, yf, 16, 24, { shape: 'arch', frame: C.stone3 });
      o += P.pyramid(tx0, tx1, yt - 2, 30, 42, 'slate', r) + P.flag(72, yt - 58, 18, 14, C.red);
      // 两侧墙上的城徽旗幅
      o += banner(50, y2 + 4) + banner(94, y2 + 4);
      return o;
    }
  });
  /** 墙上垂挂的旗幅：红底黄色竖条，燕尾 */
  function banner(cx, yt) {
    return ln(seg(cx - 5, yt, cx + 5, yt), 1.4, 1, C.dark) +
      path('M' + f(cx - 4) + ' ' + f(yt) + 'L' + f(cx + 4) + ' ' + f(yt) + 'L' + f(cx + 4) + ' ' + f(yt + 17) + 'L' + f(cx) + ' ' + f(yt + 13) + 'L' + f(cx - 4) + ' ' + f(yt + 17) + 'Z', C.red, 1.1) +
      ln(seg(cx, yt + 1, cx, yt + 12), 1.6, 1, C.wash);
  }

  // ——————————————————— 行政厅 2：阶梯山墙议事厅 + 侧边圆角塔 ———————————————————
  def({
    kind: 'town_hall', facility: 'town_hall', variant: 2, name: '议事厅·阶梯山墙', fp: [3, 2], up: 100, seed: 1202,
    roof: 'steep_slate', tags: ['stepped_gable', 'bell_turret', 'balcony', 'important'],
    note: '石砌行会议事厅：山墙朝前的阶梯山墙，正中宣告阳台与城旗；左侧圆形楼梯塔（锥顶挂钟），右翼两层木筋附楼',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '';
      o += P.boxShadow(8, 138, yf - 56, yf, 5, W, H);
      // 右翼附楼
      o += P.gableRoof(98, 138, yf - 40, 48, 14, 'tile', r, { ov: 2 });
      o += P.wall(98, 138, yf - 40, yf, 'timber', r, { bays: 2, floors: 2 });
      o += P.win(104, yf - 34, 7, 9, {}) + P.win(124, yf - 34, 7, 9, {}) + P.door(118, yf, 10, 16, {});
      // 主体：山墙朝前，青石板陡坡
      var x0 = 28, x1 = 100, yE = yf - 46;
      var g = P.gableFront(x0, x1, yE, 56, 46, 'slate', r, { ov: 2 });
      o += g.roof + steppedGable(x0, x1, yE + 0.5, yE - 52, 4, C.stone) + P.courses(x0 + 6, x1 - 6, yE - 30, yE, 6, r, 11);
      o += P.win(57, yE - 30, 14, 18, { shape: 'arch' }) + P.circle(64, yE - 40, 3, C.dark, 1);
      o += P.wall(x0, x1, yE, yf, 'ashlar', r, { plinth: 5 });
      o += P.win(36, yE + 6, 9, 14, { shape: 'arch' }) + P.win(83, yE + 6, 9, 14, { shape: 'arch' });
      o += P.door(64, yf, 18, 25, { shape: 'arch', frame: C.stone3 });
      // 阳台：石托 + 栏杆 + 两侧旗
      o += rect(50, yE + 15, 28, 3.5, C.stone3, 1.3) + ln(seg(51, yE + 8, 77, yE + 8) + seg(54, yE + 8, 54, yE + 15) + seg(60, yE + 8, 60, yE + 15) + seg(68, yE + 8, 68, yE + 15) + seg(74, yE + 8, 74, yE + 15), 1.2, 1);
      o += banner(43, yE + 2) + banner(85, yE + 2);
      // 左侧圆形楼梯塔
      o += P.cylinder(18, yf - 2.5, 13, 67.5, C.stone, 'stone', r, { top: false });
      o += P.win(15, yf - 50, 5, 9, { shape: 'arch', panes: false }) + P.win(15, yf - 26, 5, 9, { shape: 'arch', panes: false });
      o += path(P.archPath(12, yf - 66, 12, 12), C.dark, 1.2) + bell(18, yf - 62, 8);
      o += P.cone(18, yf - 70, 16, 40, 'slate');
      o += P.flag(18, yf - 116, 0.1, 12, C.red);
      return o;
    }
  });

  /** 垛口：沿 x0..x1 在 y（墙顶前沿）上排一列墙齿 */
  function merlons(x0, x1, y, mw, gap, fill) {
    var o = '', n = Math.max(2, Math.round((x1 - x0 + gap) / (mw + gap))), st = (x1 - x0 - mw) / (n - 1);
    for (var i = 0; i < n; i++) o += P.box(x0 + i * st, x0 + i * st + mw, y, 2.5, 5, fill || C.stone, C.stone3, 1.2);
    return o;
  }
  /** 方塔：正面 x0..x1，前沿 yb，高 h，顶面进深 dg，顶上垛口 */
  function squareTower(x0, x1, yb, h, dg, r, opt) {
    opt = opt || {};
    var yt = yb - h, o = '';
    o += poly([[x0, yt], [x1, yt], [x1, yt - dg], [x0, yt - dg]], C.stone3, 1.4);
    o += merlons(x0, x1, yt - dg + 2.5, 4, 3.5, C.stone2);
    o += P.wall(x0, x1, yt, yb, 'ashlar', r, { plinth: opt.plinth || 0 });
    o += merlons(x0 - 1, x1 + 1, yt, 4.5, 3.5, C.stone);
    return o;
  }

  // ——————————————————— 领主府：围墙前院 + 主楼 + 两角方塔 ———————————————————
  def({
    kind: 'lord_hall', facility: 'lord_hall', variant: 1, name: '领主府', fp: [4, 3], up: 100, seed: 1301,
    roof: 'hip_tile', tags: ['manor', 'courtyard', 'crenellated', 'heraldry'],
    note: '设防庄园：前院低矮围墙与带吊闸的门楼，石板前院；主楼两层（底层石砌、上层木筋），青石板四坡顶；两角方塔带垛口，悬挂家族纹章旗',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '', ym = yf - 52;
      o += P.boxShadow(6, 186, yf - 130, yf, 5, W, H);
      // 前院地坪
      o += P.paving(10, ym - 2, 182, yf - 4, 9, r, C.stone);
      // 主楼
      o += P.hipRoof(36, 156, ym - 52, 74, 26, 'slate', r, { ov: 3 });
      o += P.chimney(60, ym - 80, 9, 22, r) + P.chimney(124, ym - 82, 9, 22, r);
      o += P.wall(36, 156, ym - 52, ym - 26, 'timber', r, { bays: 6 });
      [44, 64, 120, 140].forEach(function (x) { o += P.win(x, ym - 47, 8, 13, { shutters: true }); });
      o += P.wall(36, 156, ym - 26, ym, 'ashlar', r, { plinth: 4 });
      [44, 64, 120, 140].forEach(function (x) { o += P.win(x, ym - 21, 8, 12, { shape: 'arch' }); });
      // 主楼正门 + 门上纹章盾
      o += P.door(96, ym, 18, 24, { shape: 'arch', frame: C.stone3 });
      o += path('M86 ' + f(ym - 50) + 'L106 ' + f(ym - 50) + 'L106 ' + f(ym - 40) + 'Q106 ' + f(ym - 31) + ' 96 ' + f(ym - 28) + 'Q86 ' + f(ym - 31) + ' 86 ' + f(ym - 40) + 'Z', C.red, 1.3) +
        ln(seg(96, ym - 49, 96, ym - 30) + seg(87, ym - 42, 105, ym - 42), 2, 1, C.wash);
      // 两角方塔
      o += squareTower(6, 38, yf - 34, 86, 26, r, { plinth: 5 }) + squareTower(154, 186, yf - 34, 86, 26, r, { plinth: 5 });
      [[22, yf - 100], [170, yf - 100]].forEach(function (p) { o += P.win(p[0] - 3, p[1], 6, 11, { shape: 'arch', panes: false }) + P.win(p[0] - 3, p[1] + 30, 6, 11, { shape: 'arch', panes: false }); });
      o += P.flag(22, yf - 125, 24, 15, C.red) + P.flag(170, yf - 125, 24, 15, C.slate);
      o += banner(22, yf - 70) + banner(170, yf - 70);
      // 前院围墙 + 门楼（吊闸）
      o += P.box(38, 154, yf, 4, 18, C.stone, C.stone3, 1.5) + P.courses(38, 154, yf - 18, yf, 6, r, 11);
      o += merlons(39, 153, yf - 18, 4, 4, C.stone);
      o += squareTower(78, 114, yf, 46, 14, r, {});
      o += path(P.archPath(86, yf - 30, 20, 30), C.dark, 1.5);
      var pc = '';
      for (var x = 90; x < 104; x += 4) pc += seg(x, yf - 26, x, yf - 3);
      for (var y = yf - 22; y < yf; y += 5) pc += seg(87, y, 105, y);
      o += ln(pc, 1.1, 1, C.slate2) + banner(96, yf - 44);
      return o;
    }
  });

  /** 玫瑰窗：石框 + 深色玻璃 + 八瓣彩色花窗 + 放射窗棂 */
  function roseWindow(cx, cy, R) {
    var o = P.circle(cx, cy, R + 3, C.stone3, 1.5) + P.circle(cx, cy, R, C.dark, 1.2), d = '';
    for (var i = 0; i < 8; i++) {
      var a = i * Math.PI / 4 - Math.PI / 2, ca = Math.cos(a), sa = Math.sin(a);
      o += P.circle(cx + ca * R * 0.62, cy + sa * R * 0.62, R * 0.25, i % 2 ? C.red : C.slate, 0.7);
      d += seg(cx + ca * R * 0.24, cy + sa * R * 0.24, cx + ca * R * 0.96, cy + sa * R * 0.96);
    }
    return o + ln(d, 1.1, 0.9, C.wash) + P.circle(cx, cy, R * 0.24, C.wash, 0.9) + P.ring(cx, cy, R, 1.4, 1, C.ink);
  }
  /** 扶壁：上窄下宽两段，带斜帽；x 左缘，yb 地面，yt 顶 */
  function buttress(x, yb, yt) {
    return rect(x, yt + 8, 7, yb - yt - 8, C.stone2, 1.3) + poly([[x - 0.5, yt + 8], [x + 7.5, yt + 8], [x + 3.5, yt]], C.stone3, 1.2) +
      rect(x - 1.5, yb - 26, 10, 26, C.stone2, 1.3) + poly([[x - 1.5, yb - 26], [x + 8.5, yb - 26], [x + 7, yb - 31], [x, yb - 31]], C.stone3, 1.2);
  }
  /** 十字：竖杆顶 (x,yt) 起 h 高 */
  function cross(x, yt, h) {
    var d = seg(x, yt, x, yt + h) + seg(x - h * 0.32, yt + h * 0.32, x + h * 0.32, yt + h * 0.32);
    return ln(d, 2.8, 1, C.ink) + ln(d, 1.2, 1, C.wash);
  }

  // ——————————————————— 教堂 1：哥特式大教堂（尖塔、玫瑰窗、飞扶壁） ———————————————————
  def({
    kind: 'temple', facility: 'temple', variant: 1, name: '大教堂·尖塔', fp: [3, 3], up: 144, seed: 1401,
    roof: 'steep_slate', tags: ['spire', 'rose_window', 'buttress', 'gothic', 'important'],
    note: '哥特式教堂：山墙朝前的正立面，玫瑰窗与层层退进的尖拱大门；两侧低矮侧廊，屋面上跨着飞扶壁；交叉部方塔上青石板高尖塔与十字',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '', nx0 = 36, nx1 = 108, cx = 72, yE = yf - 62, dg = 112, rise = 40;
      var ay = yf - 30, ai = yf - 46, adg = 104;
      o += P.boxShadow(6, 138, yf - dg, yf, 5, W, H);
      // 侧廊单坡顶（顺进深方向）
      o += P.slope([5, ay], [5, ay - adg], [nx0, ai - adg], [nx0, ai], 'slate', false, r);
      o += P.slope([139, ay], [139, ay - adg], [nx1, ai - adg], [nx1, ai], 'slate', true, r);
      // 飞扶壁：从侧廊外墙小尖塔跨到中厅墙（后排先画）
      [86, 54, 22].forEach(function (k) {
        [[8, nx0, 1], [136, nx1, -1]].forEach(function (s) {
          var px = s[0], d = 'M' + f(px) + ' ' + f(ay - k - 8) + 'Q' + f(px + s[2] * 14) + ' ' + f(ai - k - 22) + ' ' + f(s[1]) + ' ' + f(ai - k - 20);
          o += ln(d, 4, 1, C.ink) + ln(d, 2.2, 1, C.stone);
          o += rect(px - 3, ay - k - 12, 6, 13, C.stone, 1.1) + poly([[px - 3.5, ay - k - 12], [px + 3.5, ay - k - 12], [px, ay - k - 20]], C.stone3, 1);
        });
      });
      // 中厅屋顶
      var g = P.gableFront(nx0, nx1, yE, dg, rise, 'slate', r, { ov: 2, fill: C.stone });
      o += g.roof;
      // 交叉部方塔 + 尖塔（骑在屋脊上，进深约 58 处）
      var ty = yE - rise - 58;
      o += poly([[60, ty + 6], [72, ty - 2], [84, ty + 6]], C.slate2, 1.2);
      o += rect(63, ty - 26, 18, 30, C.stone, 1.5) + P.courses(63, 81, ty - 26, ty + 4, 6, r, 9) + P.win(69, ty - 22, 6, 14, { shape: 'point', panes: false });
      o += P.pyramid(62, 82, ty - 26, 8, 70, 'slate', r, { finial: false });
      o += cross(72, ty - 26 - 4 - 70 - 13, 13);
      // 正立面
      o += poly([[6, yf], [6, ay], [nx0 - 4, ai], [nx0 - 4, yf]], C.stone, 1.6) + P.courses(6, nx0 - 4, ay, yf, 6, r, 10);
      o += poly([[nx1 + 4, yf], [nx1 + 4, ai], [138, ay], [138, yf]], C.stone, 1.6) + P.courses(nx1 + 4, 138, ay, yf, 6, r, 10);
      o += flat([[nx1 + 4, yf - 1], [nx1 + 4, ai + 1], [137, ay + 1], [137, yf - 1]], C.shadow, 0.1);
      o += P.win(15, yf - 26, 8, 18, { shape: 'point' }) + P.win(121, yf - 26, 8, 18, { shape: 'point' });
      o += g.gable + P.wall(nx0, nx1, yE, yf, 'ashlar', r, { plinth: 6 });
      o += roseWindow(cx, yE - 5, 13);
      o += P.win(43, yE + 16, 7, 22, { shape: 'point' }) + P.win(94, yE + 16, 7, 22, { shape: 'point' });
      // 退进的尖拱大门
      o += path(P.pointPath(55, yf - 47, 34, 47), C.stone3, 1.5) + path(P.pointPath(59, yf - 42, 26, 42), C.stone2, 1.2) +
        P.door(cx, yf, 18, 36, { shape: 'point' }) + ln(seg(cx, yf - 36, cx, yf - 1), 1.2, 0.8, C.dark);
      o += buttress(nx0 - 5, yf, yE - 8) + buttress(nx1 - 2, yf, yE - 8);
      return o;
    }
  });

  // ——————————————————— 教堂 2：罗曼式教区教堂（侧立面 + 方钟塔） ———————————————————
  def({
    kind: 'temple', facility: 'temple', variant: 2, name: '教区教堂·钟塔', fp: [3, 2], up: 128, seed: 1402,
    roof: 'gable_tile', tags: ['bell_tower', 'romanesque', 'round_arch', 'important'],
    note: '罗曼式教区教堂：长边朝前的中厅，壁柱分间、半圆拱窗与檐下伦巴第小拱带；左端方形钟塔，双拱钟口里挂钟，青石板四角攒尖顶与十字',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '', yw = yf - 44;
      o += P.boxShadow(8, 138, yf - 60, yf, 5, W, H);
      o += P.gableRoof(44, 138, yw, 60, 22, 'tile', r, { ov: 3 });
      o += P.wall(44, 138, yw, yf, 'stone', r, { plinth: 5 });
      var arc = '';
      for (var x = 46; x < 136; x += 6) arc += 'M' + f(x) + ' ' + f(yw + 6) + 'A3 3 0 0 1 ' + f(x + 6) + ' ' + f(yw + 6);
      o += ln(arc, 0.9, 0.7);
      [70, 94, 118].forEach(function (x) { o += rect(x, yw + 7, 4, 37, C.stone2, 1.1); });
      [52, 78, 102, 124].forEach(function (x) { o += P.win(x, yw + 12, 8, 17, { shape: 'arch' }); });
      // 钟塔
      var x0 = 8, x1 = 46, yt = yf - 118;
      o += P.wall(x0, x1, yt, yf, 'ashlar', r, { plinth: 6 });
      o += rect(x0 - 2, yt - 3, x1 - x0 + 4, 4, C.stone3, 1.3) + rect(x0 - 1, yf - 74, x1 - x0 + 2, 3, C.stone3, 1.1);
      o += path(P.archPath(14, yt + 7, 11, 22), C.dark, 1.3) + path(P.archPath(29, yt + 7, 11, 22), C.dark, 1.3) +
        bell(19.5, yt + 13, 8) + bell(34.5, yt + 13, 8) + ln(seg(27, yt + 10, 27, yt + 29), 2.4, 1, C.stone2);
      o += roseWindow(27, yt + 48, 6);
      o += P.win(23.5, yf - 66, 7, 14, { shape: 'arch' });
      o += P.door(27, yf, 15, 25, { shape: 'arch', frame: C.stone3 });
      o += P.pyramid(x0, x1, yt - 1, 30, 36, 'slate', r, { finial: false }) + cross(27, yt - 1 - 15 - 36 - 13, 13);
      o += P.bush(134, yf + 3, 5, r);
      return o;
    }
  });

  // ——————————————————— 教堂 3：小礼拜堂（山墙钟架） ———————————————————
  def({
    kind: 'temple', facility: 'temple', variant: 3, name: '小礼拜堂', fp: [2, 2], up: 84, seed: 1403,
    roof: 'steep_slate', tags: ['chapel', 'bellcote', 'small'],
    note: '小礼拜堂：山墙朝前的单间石堂，山尖上一座小钟架，尖拱门与小玫瑰窗；门旁石十字与灌木',
    draw: function (c) {
      var r = c.rnd, W = c.W, H = c.H, yf = H - 5, o = '', x0 = 22, x1 = 74, cx = 48, yE = yf - 36;
      o += P.boxShadow(x0, x1, yf - 70, yf, 5, W, H);
      var g = P.gableFront(x0, x1, yE, 70, 30, 'slate', r, { ov: 2, fill: C.stone });
      o += g.roof + g.gable + P.wall(x0, x1, yE, yf, 'stone', r, { plinth: 4 });
      // 山尖钟架
      var ap = yE - 30;
      o += rect(cx - 6, ap - 15, 12, 17, C.stone, 1.3) + path(P.archPath(cx - 3.5, ap - 12, 7, 12), C.dark, 1) + bell(cx, ap - 9, 6) +
        poly([[cx - 8, ap - 15], [cx + 8, ap - 15], [cx, ap - 23]], C.slate, 1.2) + cross(cx, ap - 33, 10);
      o += roseWindow(cx, yE - 9, 5.5);
      o += P.door(cx, yf, 13, 22, { shape: 'point', frame: C.stone3 });
      o += P.win(29, yE + 8, 5, 14, { shape: 'point', panes: false }) + P.win(62, yE + 8, 5, 14, { shape: 'point', panes: false });
      o += buttress(x0 - 4, yf, yE - 4) + buttress(x1 - 3, yf, yE - 4);
      // 门旁石十字、灌木
      o += rect(84, yf - 6, 8, 6, C.stone2, 1.1) + ln(seg(88, yf - 6, 88, yf - 26) + seg(82, yf - 20, 94, yf - 20), 4, 1, C.ink) +
        ln(seg(88, yf - 6, 88, yf - 26) + seg(82, yf - 20, 94, yf - 20), 2.4, 1, C.stone);
      o += P.bush(10, yf, 7, r);
      return o;
    }
  });

  if (typeof module !== 'undefined' && module.exports) module.exports = defs;
  else root.TownArtWS_civic = defs;
})(typeof window !== 'undefined' ? window : this);
