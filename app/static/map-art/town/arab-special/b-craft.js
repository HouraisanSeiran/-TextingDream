/*
 * 工坊与仓储类：铁匠铺、冶炼炉、陶窑、制革染坊、粮仓、马厩骆驼栏、兵营、瞭望塔、货栈。
 * 浏览器追加到 window.TownArtAS_defs；Node 用 module.exports 导出数组。
 */
(function (root) {
  'use strict';
  var N = typeof module !== 'undefined' && module.exports;
  var K = N ? require('./core.js') : root.TownArtAS_core;
  var P = N ? require('./parts.js') : root.TownArtAS_parts;
  var Ms = N ? require('./mass.js') : root.TownArtAS_mass;
  var F = N ? require('./facade.js') : root.TownArtAS_facade;
  var C = K.C, f = K.f;
  var defs = [];

  /** 蜂窝窑 / 土丘：无金尖 */
  function hive(cx, by, r, hh, fill) {
    var s = K.path('M' + f(cx - r) + ' ' + f(by) + 'C' + f(cx - r) + ' ' + f(by - hh * 1.3) + ' ' + f(cx + r) + ' ' + f(by - hh * 1.3) + ' ' + f(cx + r) + ' ' + f(by) + 'Z', fill || C.adobe2, 1.5);
    s += K.flatD('M' + f(cx + r * 0.3) + ' ' + f(by - hh * 0.95) + 'Q' + f(cx + r * 0.95) + ' ' + f(by - hh * 0.75) + ' ' + f(cx + r - 0.8) + ' ' + f(by - 0.7) +
      'L' + f(cx + r * 0.5) + ' ' + f(by - 0.7) + 'Q' + f(cx + r * 0.6) + ' ' + f(by - hh * 0.6) + ' ' + f(cx + r * 0.3) + ' ' + f(by - hh * 0.95) + 'Z', C.adobe3, 0.5);
    var d = '';
    for (var k = 1; k < 4; k++) { var y = by - hh * k / 4, w = r * Math.sqrt(1 - Math.pow(k / 4.4, 2)); d += 'M' + f(cx - w) + ' ' + f(y) + 'Q' + f(cx) + ' ' + f(y + 2.5) + ' ' + f(cx + w) + ' ' + f(y); }
    return s + K.ln(d, 0.6, 0.4);
  }
  function flame(cx, by, w, h) {
    return K.path('M' + f(cx - w / 2) + ' ' + f(by) + 'Q' + f(cx - w * 0.4) + ' ' + f(by - h * 0.7) + ' ' + f(cx - w * 0.1) + ' ' + f(by - h * 0.45) +
      'Q' + f(cx) + ' ' + f(by - h) + ' ' + f(cx + w * 0.15) + ' ' + f(by - h * 0.5) + 'Q' + f(cx + w * 0.45) + ' ' + f(by - h * 0.7) + ' ' + f(cx + w / 2) + ' ' + f(by) + 'Z', C.ochre2, 0.7) +
      K.ellipse(cx, by - 1.5, w * 0.25, h * 0.18, C.gold, 0.4);
  }
  function smoke(x, y) { return K.ln('M' + f(x) + ' ' + f(y) + 'q-4 -6 1 -11q5 -5 0 -11', 0.9, 0.4); }
  function mound(cx, by, r, hh, fill) {
    return K.path('M' + f(cx - r) + ' ' + f(by) + 'Q' + f(cx - r * 0.4) + ' ' + f(by - hh * 1.4) + ' ' + f(cx + r * 0.2) + ' ' + f(by - hh) + 'Q' + f(cx + r * 0.8) + ' ' + f(by - hh * 0.6) + ' ' + f(cx + r) + ' ' + f(by) + 'Z', fill, 1);
  }

  defs.push({
    id: 'arab-common-forge-01', name: '铁匠铺', fp: [2, 2], up: 60, kind: 'smithy', facility: 'forge',
    tags: ['open_front', 'chimney', 'anvil'], roof: 'flat_mud',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, s = '', yf = H - 22, h = 44, ty = gy + 6 - h;
      s += Ms.block({ x0: 8, x1: W - 8, yb: gy + 6, yf: yf, h: h, lip: 2, wall: C.adobe, top: C.adobe2, W: W, H: H });
      s += K.rect(W - 26, ty - 14, 10, 24, C.adobe2, 1.2) + K.rect(W - 27.5, ty - 16, 13, 2.5, C.adobe3, 0.8) + smoke(W - 21, ty - 18);
      s += P.arch(14, yf - 0.5, 36, 34, C.hole, 1.2) + flame(32, yf - 2, 18, 16);
      s += F.awning(10, 54, yf - 38, 6, C.ochre, C.adobe);
      s += F.windows(60, W - 12, yf - 28, 5, 8, 2);
      // 院前：铁砧、淬火桶、柴堆
      var ax = 58, ay = H - 7;
      s += K.shade([[ax - 6, ay], [ax + 12, ay], [ax + 14, ay + 3], [ax - 4, ay + 3]]);
      s += K.rect(ax - 2.5, ay - 6, 5, 6, C.wood, 0.8);
      s += K.path('M' + f(ax - 7) + ' ' + f(ay - 6) + 'V' + f(ay - 10) + 'H' + f(ax + 6) + 'L' + f(ax + 11) + ' ' + f(ay - 12) + 'L' + f(ax + 9) + ' ' + f(ay - 8.5) + 'L' + f(ax + 4) + ' ' + f(ay - 6) + 'Z', C.iron, 1);
      s += K.rect(W - 22, H - 16, 13, 11, C.wood, 1) + K.ellipse(W - 15.5, H - 16, 6.5, 2.2, C.water, 0.8);
      var d = ''; for (var i = 0; i < 5; i++) d += K.seg(10 + i * 2, H - 5, 22 + i * 2, H - 13);
      s += K.ln(d, 1.6, 1, C.wood);
      return s;
    }
  });

  defs.push({
    id: 'arab-common-smelter-01', name: '冶炼炉（土竖炉）', fp: [2, 2], up: 96, kind: 'shaft_furnace', facility: 'smelter',
    tags: ['furnace', 'bellows', 'slag'], roof: 'none',
    draw: function (c) {
      var W = c.W, H = c.H, s = '', cx = W / 2 - 2, by = H - 14, th = 84;
      s += K.boxShadow(cx - 20, cx + 20, by - 24, by, 12, W, H);
      s += mound(W - 16, H - 4, 12, 9, C.hole) + mound(14, H - 4, 11, 8, C.ochre);
      s += K.poly([[cx - 20, by], [cx - 11, by - th], [cx + 11, by - th], [cx + 20, by]], C.adobe2, 1.7);
      s += K.flat([[cx + 5, by - th + 1], [cx + 10.4, by - th + 1], [cx + 19, by - 1], [cx + 9, by - 1]], C.adobe3, 0.45);
      var d = ''; for (var k = 1; k < 4; k++) { var y = by - th * k / 4, hw = 20 - 9 * k / 4; d += K.seg(cx - hw, y, cx + hw, y); }
      s += K.ln(d, 0.9, 0.6);
      s += K.ellipse(cx, by - th, 11, 3, C.adobe3, 1.2) + K.ellipse(cx, by - th, 7, 1.7, C.ochre2, 0.6) + smoke(cx, by - th - 3);
      s += P.arch(cx - 6, by, 12, 15, C.hole, 1) + flame(cx, by - 1, 9, 11);
      // 风箱（左）
      s += K.ln(K.seg(cx - 26, by - 9, cx - 16, by - 7), 1.6, 1, C.wood);
      s += K.ellipse(cx - 30, by - 7, 7, 4, C.ochre, 0.9) + K.ellipse(cx - 30, by - 1, 7, 3, C.ochre2, 0.9);
      return s;
    }
  });

  defs.push({
    id: 'arab-common-kiln-01', name: '陶窑（蜂窝窑）', fp: [2, 2], up: 58, kind: 'pottery_kiln', facility: 'kiln',
    tags: ['beehive_kiln', 'pottery', 'drying_rack'], roof: 'none', note: '穹形窑体，无屋面，roof=none',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, s = '';
      s += K.boxShadow(14, 70, gy + 20, H - 12, 10, W, H);
      s += hive(42, H - 12, 28, 46, C.adobe2);
      s += K.ellipse(42, H - 12 - 58, 6, 2.2, C.adobe3, 1) + smoke(42, H - 72);
      s += P.arch(34, H - 12, 16, 16, C.hole, 1.1) + flame(42, H - 13, 9, 9);
      // 晾坯架 + 成品罐
      s += K.rect(68, H - 30, 2, 26, C.wood, 0.7) + K.rect(W - 4, H - 30, 2, 26, C.wood, 0.7);
      s += K.rect(66, H - 30, W - 68, 2, C.wood, 0.7) + K.rect(66, H - 18, W - 68, 2, C.wood, 0.7);
      [[73, H - 30], [80, H - 30], [87, H - 30], [76, H - 18], [84, H - 18]].forEach(function (p, i) {
        s += K.path('M' + f(p[0] - 2.5) + ' ' + f(p[1]) + 'q-1 -4 1 -5.5h3q2 1.5 1 5.5Z', i % 2 ? C.ochre2 : C.sand, 0.6);
      });
      s += K.rect(8, H - 10, 16, 6, C.wood, 0.8);
      var d = ''; for (var i = 0; i < 3; i++) d += K.seg(10 + i * 5, H - 10, 12 + i * 5, H - 4);
      return s + K.ln(d, 0.6, 0.6);
    }
  });

  defs.push({
    id: 'arab-common-tannery-01', name: '制革染坊（彩色染池）', fp: [3, 2], up: 52, kind: 'tannery_dyeworks', facility: 'tannery',
    tags: ['dye_vats', 'open_air', 'drying_hides'], roof: 'flat_mud',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, s = '';
      // 后排：工棚（平顶块）+ 晾皮架
      s += Ms.block({ x0: 8, x1: W - 8, yb: gy + 4, yf: gy + 34, h: 30, lip: 2, wall: C.adobe, top: C.adobe2, W: W, H: H });
      s += F.arcade(12, W - 12, gy + 33, 18, 6, C.hole);
      var hy = gy - 26, d = '';
      for (var k = 0; k < 4; k++) { var x = 18 + k * 30; s += K.rect(x, hy, 18, 12, [C.ochre2, C.gold, C.cobalt2, C.ochre][k], 0.8); }
      s += K.ln(K.seg(12, hy, W - 12, hy), 1.1, 1, C.wood);
      // 前院：彩色染池格（石沿蜂窝格）
      var cols = [C.ochre, C.gold, C.turq, C.lime2, C.cobalt2, C.ochre2, C.palm2, C.adobe2, C.gold, C.turq2, C.ochre, C.lime2];
      s += K.rect(6, gy + 36, W - 12, H - 4 - gy - 36, C.lime2, 1.4);
      var nx = 6, ny = 2, cw = (W - 16) / nx, ch = (H - 8 - gy - 38) / ny;
      for (var j = 0; j < ny; j++) for (var i = 0; i < nx; i++) {
        var x0 = 8 + i * cw, y0 = gy + 38 + j * ch;
        s += K.ellipse(x0 + cw / 2, y0 + ch / 2, cw * 0.4, ch * 0.36, cols[(i + j * nx) % cols.length], 1);
        d += 'M' + f(x0 + cw / 2 - cw * 0.18) + ' ' + f(y0 + ch / 2 - 1) + 'q2 -1.2 4 0';
      }
      s += K.ln(d, 0.6, 0.5, C.lime);
      return s;
    }
  });

  defs.push({
    id: 'arab-common-granary-01', name: '粮仓（筑垒粮仓 agadir）', fp: [2, 2], up: 90, kind: 'fortified_granary', facility: 'granary',
    tags: ['fortified', 'cells', 'crenellated'], roof: 'flat_mud',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, s = '', yf = H - 6, h = 76;
      s += Ms.block({ x0: 8, x1: W - 8, yb: gy + 8, yf: yf, h: h, lip: 0, wall: C.adobe, top: C.adobe2, W: W, H: H });
      s += P.merlons(8, W - 8, yf - h, 6, C.adobe);
      // 多层储粮小格门（木门 + 托木）
      for (var r = 0; r < 4; r++) for (var i = 0; i < 4; i++) {
        var x = 16 + i * 18, y = yf - h + 10 + r * 16;
        s += K.rect(x, y, 8, 9, C.wood, 0.8) + K.ln(K.seg(x - 3, y + 11, x + 11, y + 11), 1, 0.8, C.adobe3);
      }
      s += P.arch(W / 2 - 7, yf, 14, 14, C.hole, 1);
      s += K.rect(12, yf - 6, 14, 6, C.sand, 0.7) + K.rect(W - 26, yf - 6, 14, 6, C.sand, 0.7);
      return s;
    }
  });

  defs.push({
    id: 'arab-common-stable-01', name: '马厩骆驼栏', fp: [3, 2], up: 44, kind: 'stable_camel', facility: 'stable',
    tags: ['open_shed', 'trough', 'fenced_yard'], roof: 'flat_mud', note: '只画饲槽与草料，未画骆驼（骆驼摆件属 arab-base）',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, s = '';
      s += Ms.block({ x0: 6, x1: W - 6, yb: gy + 4, yf: gy + 40, h: 34, lip: 2, wall: C.adobe, top: C.adobe2, W: W, H: H });
      s += F.arcade(10, W - 10, gy + 39, 26, 5, C.hole);
      s += K.rect(6, gy + 40, W - 12, H - 4 - gy - 40, C.sand, 1);
      // 栅栏
      var d = ''; for (var x = 6; x <= W - 6; x += 9) d += K.seg(x, H - 4, x, H - 14);
      s += K.ln(d + K.seg(6, H - 12, W - 6, H - 12) + K.seg(6, H - 7, W - 6, H - 7), 1.2, 1, C.wood);
      // 饲槽与草料堆
      s += K.rect(14, gy + 44, 40, 6, C.adobe3, 0.9) + K.rect(16, gy + 45, 36, 3, C.palm2, 0.5);
      s += mound(W - 30, gy + 58, 16, 12, C.gold) + mound(W - 50, gy + 60, 10, 8, C.sand);
      return s;
    }
  });

  defs.push({
    id: 'arab-common-barracks-01', name: '兵营（里巴特式营房）', fp: [3, 2], up: 70, kind: 'barracks', facility: 'barracks',
    tags: ['crenellated', 'corner_towers', 'arrow_slits', 'weapon_rack'], roof: 'flat_mud',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, cx = W / 2, s = '', yf = H - 4, h = 40;
      s += Ms.block({ x0: 12, x1: W - 12, yb: gy + 8, yf: yf, h: h, lip: 0, wall: C.adobe, top: C.adobe2, W: W, H: H });
      s += P.merlons(12, W - 12, yf - h, 5, C.adobe);
      var d = ''; for (var x = 24; x < W - 20; x += 14) if (Math.abs(x - cx) > 14) d += K.seg(x, yf - h + 10, x, yf - h + 20);
      s += K.ln(d, 1.6, 1, C.hole);
      [[2, 20], [W - 20, W - 2]].forEach(function (t) {
        var yt = yf - h - 18;
        s += K.rect(t[0], yt, t[1] - t[0], yf - yt, C.adobe, 1.5);
        s += K.flat([[t[1] - 6, yt + 1], [t[1] - 0.8, yt + 1], [t[1] - 0.8, yf - 0.8], [t[1] - 6, yf - 0.8]], C.adobe3, 0.35);
        s += K.ln(K.seg((t[0] + t[1]) / 2, yt + 10, (t[0] + t[1]) / 2, yt + 20), 1.6, 1, C.hole);
        s += K.rect(t[0] - 1.5, yt - 3, t[1] - t[0] + 3, 3, C.adobe, 1) + P.merlons(t[0] - 1, t[1] + 1, yt - 3, 5, C.adobe, 1.2);
      });
      s += P.arch(cx - 10, yf, 20, 26, C.hole, 1.2) + K.rect(cx - 13, yf - 30, 26, 3, C.ochre, 0.8);
      // 门旁兵器架
      s += K.rect(cx + 16, yf - 14, 18, 2, C.wood, 0.7);
      var sp = ''; for (var k = 0; k < 4; k++) sp += K.seg(cx + 18 + k * 4.5, yf - 2, cx + 18 + k * 4.5, yf - 22);
      s += K.ln(sp, 0.9, 1, C.wood);
      for (var j = 0; j < 4; j++) s += K.poly([[cx + 16.8 + j * 4.5, yf - 22], [cx + 18 + j * 4.5, yf - 26], [cx + 19.2 + j * 4.5, yf - 22]], C.iron, 0.5);
      return s;
    }
  });

  defs.push({
    id: 'arab-common-watchtower-01', name: '瞭望塔（夯土方塔）', fp: [1, 1], up: 120, kind: 'watchtower', facility: 'watchtower',
    tags: ['tower', 'crenellated', 'machicolation'], roof: 'flat_mud',
    draw: function (c) {
      var W = c.W, H = c.H, s = '', x0 = 9, x1 = W - 9, yf = H - 6, yt = 16;
      s += K.boxShadow(x0, x1, yf - 20, yf, 8, W, H);
      s += K.poly([[x0 - 3, yf], [x0, yt], [x1, yt], [x1 + 3, yf]], C.adobe, 1.6);
      s += K.flat([[x1 - 8, yt + 1], [x1 - 0.8, yt + 1], [x1 + 2.2, yf - 0.8], [x1 - 7, yf - 0.8]], C.adobe3, 0.35);
      var d = ''; for (var y = yt + 22; y < yf - 4; y += 22) d += K.seg(x0, y, x1, y);
      s += K.ln(d, 0.6, 0.4);
      s += K.ln(K.seg(W / 2, yt + 34, W / 2, yt + 46) + K.seg(W / 2, yt + 70, W / 2, yt + 82), 1.8, 1, C.hole);
      s += P.arch(W / 2 - 5, yf, 10, 16, C.ochre, 1);
      // 顶部外挑箭楼（mashrabiya 式木罩）+ 垛
      s += K.rect(x0 - 3, yt - 2, x1 - x0 + 6, 3, C.adobe2, 1);
      s += P.mashrabiya(W / 2 - 6, yt + 6, 12, 9);
      s += P.merlons(x0 - 3, x1 + 3, yt - 2, 6, C.adobe, 1.5);
      return s;
    }
  });

  defs.push({
    id: 'arab-common-warehouse-01', name: '货栈（瓦卡拉仓房）', fp: [3, 2], up: 66, kind: 'wakala_storehouse', facility: 'warehouse',
    tags: ['storage', 'loading_door', 'bales', 'mashrabiya'], roof: 'flat_mud',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, cx = W / 2, s = '', yf = H - 12, h = 52;
      s += Ms.block({ x0: 8, x1: W - 8, yb: gy + 6, yf: yf, h: h, lip: 3, wall: C.adobe, top: C.adobe2, W: W, H: H });
      // 屋顶滑轮吊杆
      var ty = gy + 6 - h;
      s += K.ln(K.seg(cx + 30, ty + 20, cx + 30, ty - 6) + K.seg(cx + 30, ty - 6, cx + 46, ty - 2), 1.6, 1, C.wood);
      s += K.circle(cx + 44, ty - 2, 2, C.iron, 0.6) + K.ln(K.seg(cx + 44, ty, cx + 44, yf - h + 18), 0.6, 0.8);
      s += K.rect(cx + 40, yf - h + 18, 8, 6, C.sand, 0.7);
      s += P.tileBand(10, W - 10, yf - h + 4, 3.5, true);
      s += F.windows(16, W - 16, yf - h + 12, 9, 10, 4, true);
      // 三扇大木门
      [cx - 44, cx, cx + 44].forEach(function (x) { s += F.door(x, yf, 20, 26, C.wood); });
      // 门前货包与木箱
      s += K.rect(14, H - 10, 14, 7, C.sand, 0.8) + K.rect(17, H - 15, 10, 6, C.ochre2, 0.8);
      s += K.rect(W - 30, H - 11, 12, 8, C.wood, 0.9) + K.ln(K.seg(W - 30, H - 11, W - 18, H - 3) + K.seg(W - 18, H - 11, W - 30, H - 3), 0.6, 0.6);
      s += K.rect(cx - 22, H - 9, 10, 6, C.gold, 0.7) + K.rect(cx + 14, H - 9, 10, 6, C.adobe2, 0.7);
      return s;
    }
  });

  if (N) module.exports = defs;
  else root.TownArtAS_defs = (root.TownArtAS_defs || []).concat(defs);
})(this);
