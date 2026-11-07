/*
 * 商贸类：巴扎 ×2、露天摊位 ×4、商队客栈、旅舍茶馆。
 * 浏览器追加到 window.TownArtAS_defs；Node 用 module.exports 导出数组。
 */
(function (root) {
  'use strict';
  var N = typeof module !== 'undefined' && module.exports;
  var K = N ? require('./core.js') : root.TownArtAS_core;
  var P = N ? require('./parts.js') : root.TownArtAS_parts;
  var Ms = N ? require('./mass.js') : root.TownArtAS_mass;
  var T = N ? require('./towers.js') : root.TownArtAS_towers;
  var G = N ? require('./ground.js') : root.TownArtAS_ground;
  var F = N ? require('./facade.js') : root.TownArtAS_facade;
  var C = K.C, f = K.f;
  var defs = [];

  /** 砖拱顶 + 天窗（巴扎屋面单元） */
  function vault(cx, by, r, hh, fill) {
    var d = 'M' + f(cx - r) + ' ' + f(by) + 'C' + f(cx - r) + ' ' + f(by - hh * 1.3) + ' ' + f(cx + r) + ' ' + f(by - hh * 1.3) + ' ' + f(cx + r) + ' ' + f(by) + 'Z';
    var s = K.path(d, fill || C.adobe, 1.1);
    s += K.flatD('M' + f(cx + r * 0.35) + ' ' + f(by - hh * 0.93) + 'Q' + f(cx + r * 0.95) + ' ' + f(by - hh * 0.8) + ' ' + f(cx + r - 0.8) + ' ' + f(by - 0.6) +
      'L' + f(cx + r * 0.5) + ' ' + f(by - 0.6) + 'Q' + f(cx + r * 0.6) + ' ' + f(by - hh * 0.6) + ' ' + f(cx + r * 0.35) + ' ' + f(by - hh * 0.93) + 'Z', C.adobe3, 0.45);
    s += K.ln('M' + f(cx - r * 0.7) + ' ' + f(by - 0.5) + 'Q' + f(cx - r * 0.6) + ' ' + f(by - hh * 0.7) + ' ' + f(cx) + ' ' + f(by - hh * 0.9), 0.6, 0.4);
    s += K.ellipse(cx, by - hh * 0.8, r * 0.3, r * 0.16, C.hole, 0.7);
    return s;
  }
  /** 货物：麻袋堆 */
  function sacks(x, y, n, seed) {
    var r = K.rng(seed || 1), s = '', cols = [C.ochre2, C.gold, C.adobe2, C.palm2, C.ochre];
    for (var i = 0; i < n; i++) {
      var cx = x + i * 6.5, col = cols[Math.floor(r() * cols.length)];
      s += K.path('M' + f(cx - 3) + ' ' + f(y) + 'Q' + f(cx - 3.6) + ' ' + f(y - 5) + ' ' + f(cx) + ' ' + f(y - 6.5) + 'Q' + f(cx + 3.6) + ' ' + f(y - 5) + ' ' + f(cx + 3) + ' ' + f(y) + 'Z', C.sand, 0.8);
      s += K.ellipse(cx, y - 5.6, 2.4, 1.1, col, 0.5);
    }
    return s;
  }

  defs.push({
    id: 'arab-common-bazaar-01', name: '巴扎（拱顶长廊）', fp: [4, 2], up: 80, kind: 'bazaar', facility: 'market_hall',
    tags: ['covered', 'vaulted', 'skylight', 'shops'], roof: 'flat_mud', note: '砖拱顶屋面，按 flat_mud 记',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, cx = W / 2, s = '';
      s += Ms.block({ x0: 6, x1: W - 6, yb: gy + 12, yf: H - 6, h: 44, lip: 2, W: W, H: H });
      for (var row = 0; row < 2; row++) for (var i = 0; i < 6; i++) s += vault(21 + 30 * i, row ? gy + 40 : gy, 13, 16, row ? C.adobe : C.sand);
      s += P.tileBand(8, W - 8, H - 48, 4);
      var st = (W - 20) / 8;
      s += F.arcade(10, W - 10, H - 7, 27, 8, C.hole, C.lime2);
      [0, 1, 6, 7].forEach(function (k, j) { s += F.awning(10 + st * k + 1, 10 + st * (k + 1) - 1, H - 38, 7, j % 2 ? C.turq : C.ochre2, C.lime); });
      s += sacks(16, H - 7, 3, 4) + sacks(W - 34, H - 7, 3, 8) + sacks(52, H - 7, 2, 2) + sacks(W - 62, H - 7, 2, 6);
      s += F.pishtaq(cx - 22, cx + 22, H - 6, H - 82, { alt: true });
      s += P.merlons(cx - 22, cx + 22, H - 82, 5, C.lime);
      return s;
    }
  });

  defs.push({
    id: 'arab-common-bazaar-02', name: '巴扎（筒拱有顶街）', fp: [3, 2], up: 76, kind: 'bazaar', facility: 'market_hall', variant: 2,
    tags: ['covered', 'barrel_vault', 'skylight', 'shops', 'windtower'], roof: 'flat_mud', note: '筒拱屋面，按 flat_mud 记',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, s = '';
      s += Ms.block({ x0: 6, x1: W - 6, yb: gy + 10, yf: H - 6, h: 36, lip: 0, W: W, H: H });
      var yb = gy + 10 - 36, yf = H - 42, cr = (yb + yf) / 2 - 8;
      s += T.windtower(22, yb + 16, 13, 34, C.adobe);
      s += K.poly([[6, yb], [W - 6, yb], [W - 6, cr], [6, cr]], C.sand, 1.2);
      s += K.poly([[6, cr], [W - 6, cr], [W - 6, yf], [6, yf]], C.adobe, 1.4);
      var d = ''; for (var x = 18; x < W - 8; x += 12) d += K.seg(x, cr + 1, x, yf - 1);
      s += K.ln(d, 0.6, 0.4);
      for (var i = 0; i < 4; i++) s += vault(30 + i * 28, cr + 3, 7, 9, C.lime2);
      s += P.tileBand(8, W - 8, yf + 2, 4, true);
      s += F.arcade(10, W - 10, H - 7, 22, 6, C.hole);
      for (var k = 0; k < 6; k++) { var st = (W - 20) / 6; s += F.awning(10 + st * k + 1, 10 + st * (k + 1) - 1, H - 31, 6, k % 2 ? C.ochre2 : C.turq, C.lime); }
      s += sacks(14, H - 7, 2, 3) + sacks(W - 26, H - 7, 2, 5);
      s += P.archFramed(W / 2 - 9, H - 6, 18, 30, C.turq2, C.hole);
      return s;
    }
  });

  /** 陶罐：底中心 cx,by；半宽 r；高 h */
  function jar(cx, by, r, h, fill) {
    var d = 'M' + f(cx - r * 0.45) + ' ' + f(by) + 'C' + f(cx - r * 1.3) + ' ' + f(by - h * 0.35) + ' ' + f(cx - r * 1.1) + ' ' + f(by - h * 0.8) + ' ' + f(cx - r * 0.4) + ' ' + f(by - h * 0.85) +
      'L' + f(cx - r * 0.45) + ' ' + f(by - h) + 'L' + f(cx + r * 0.45) + ' ' + f(by - h) + 'L' + f(cx + r * 0.4) + ' ' + f(by - h * 0.85) +
      'C' + f(cx + r * 1.1) + ' ' + f(by - h * 0.8) + ' ' + f(cx + r * 1.3) + ' ' + f(by - h * 0.35) + ' ' + f(cx + r * 0.45) + ' ' + f(by) + 'Z';
    return K.path(d, fill || C.ochre2, 0.9) + K.ln(K.seg(cx - r * 0.85, by - h * 0.5, cx + r * 0.85, by - h * 0.5), 0.6, 0.6, C.lime);
  }
  /** 摊位通用：两杆 + 布棚 */
  function stallFrame(W, H, top, a, b) {
    var s = K.shade([[6, H - 3], [W - 2, H - 3], [W - 0.5, H - 8], [W - 0.5, top + 14], [W - 6, top + 12]]);
    s += K.rect(6, top + 6, 2, H - 4 - top - 6, C.wood, 0.7) + K.rect(W - 8, top + 6, 2, H - 4 - top - 6, C.wood, 0.7);
    s += K.poly([[3, top + 10], [W / 2, top], [W - 3, top + 10]], b || C.lime, 1.1);
    s += F.awning(3, W - 3, top + 10, 6, a || C.ochre2, b || C.lime);
    return s;
  }
  function stall(id, name, kind, tags, draw) {
    defs.push({ id: id, name: name, fp: [1, 1], up: 40, category: 'prop', kind: kind, facility: 'market_hall',
      tags: ['open_air', 'stall'].concat(tags), roof: 'none', note: '露天集市摊位（规范第 5 节：facility=market_hall + open_air）', draw: draw });
  }
  stall('arab-common-stall-spice-01', '香料摊', 'stall_spice', ['spice'], function (c) {
    var W = c.W, H = c.H, s = stallFrame(W, H, 44, C.ochre2, C.lime);
    s += K.rect(7, H - 22, 34, 16, C.wood, 1.1) + K.rect(7, H - 22, 34, 3, C.adobe2, 0.8);
    var cols = [C.ochre, C.gold, C.ochre2, C.palm2, C.adobe3];
    for (var i = 0; i < 5; i++) {
      var x = 11 + i * 6.5;
      s += K.path('M' + f(x - 3.2) + ' ' + f(H - 22) + 'L' + f(x - 3) + ' ' + f(H - 26) + 'Q' + f(x) + ' ' + f(H - 31) + ' ' + f(x + 3) + ' ' + f(H - 26) + 'L' + f(x + 3.2) + ' ' + f(H - 22) + 'Z', cols[i], 0.7);
    }
    return s + sacks(12, H - 4, 2, 7) + sacks(33, H - 4, 1, 9);
  });
  stall('arab-common-stall-rug-01', '地毯摊', 'stall_rug', ['carpet'], function (c) {
    var W = c.W, H = c.H, s = K.shade([[6, H - 3], [W - 2, H - 3], [W - 0.5, H - 8], [W - 0.5, 50], [W - 6, 48]]);
    s += K.rect(5, 44, 2, H - 48, C.wood, 0.7) + K.rect(W - 7, 44, 2, H - 48, C.wood, 0.7) + K.rect(3, 43, W - 6, 2.4, C.wood, 0.8);
    [[8, C.ochre, C.cobalt], [24, C.cobalt, C.ochre2]].forEach(function (r) {
      s += K.rect(r[0], 45.5, 15, 28, r[1], 1) + K.rect(r[0] + 2, 47.5, 11, 24, r[2], 0.6);
      s += K.rect(r[0] + 4, 50, 7, 19, r[1], 0.5) + P.star8(r[0] + 7.5, 59.5, 3, C.gold, 0.4);
      var d = ''; for (var k = 0; k < 5; k++) d += K.seg(r[0] + 1.5 + k * 3, 73.5, r[0] + 1.5 + k * 3, 76);
      s += K.ln(d, 0.6, 0.8);
    });
    s += K.rect(6, H - 9, 34, 5, C.ochre2, 0.9) + K.ellipse(40, H - 6.5, 2, 2.5, C.ochre, 0.8);
    s += K.rect(10, H - 14, 26, 5, C.turq, 0.9) + K.ellipse(36, H - 11.5, 2, 2.5, C.cobalt, 0.8);
    return s;
  });
  stall('arab-common-stall-pottery-01', '陶器摊', 'stall_pottery', ['pottery'], function (c) {
    var W = c.W, H = c.H, s = K.shade([[4, H - 3], [W - 2, H - 3], [W - 0.5, H - 7], [W - 0.5, H - 30], [W - 4, H - 32]]);
    s += K.poly([[3, H - 4], [W - 3, H - 4], [W - 6, H - 26], [6, H - 26]], C.ochre, 1);
    s += K.poly([[6, H - 7], [W - 6, H - 7], [W - 8.5, H - 23], [8.5, H - 23]], C.adobe2, 0.6);
    s += jar(14, H - 19, 5, 16, C.ochre2) + jar(30, H - 20, 6, 20, C.adobe) + jar(38, H - 14, 4, 11, C.turq);
    s += jar(10, H - 7, 4, 10, C.adobe2) + jar(22, H - 6, 5, 13, C.cobalt2);
    s += K.ellipse(35, H - 7, 5, 2, C.turq2, 0.8) + K.ellipse(35, H - 8, 3, 1, C.hole, 0.5);
    return s;
  });
  stall('arab-common-stall-lamp-01', '铜灯摊', 'stall_lamp', ['brass', 'lamp'], function (c) {
    var W = c.W, H = c.H, s = stallFrame(W, H, 42, C.turq, C.lime);
    s += K.rect(8, H - 18, 32, 13, C.wood, 1.1);
    for (var i = 0; i < 3; i++) {
      var x = 15 + i * 9;
      s += K.ln(K.seg(x, 58, x, 63), 0.6, 0.8);
      s += K.path('M' + f(x - 3) + ' 63L' + f(x) + ' 60L' + f(x + 3) + ' 63L' + f(x + 2.4) + ' 69L' + f(x - 2.4) + ' 69Z', C.gold, 0.7);
    }
    s += K.path('M14 ' + (H - 18) + 'q-1 -6 4 -6q5 0 4 6Z', C.gold, 0.8) + K.ellipse(30, H - 19, 6, 2, C.gold, 0.8);
    return s + K.rect(12, H - 13, 6, 6, C.adobe2, 0.7) + K.rect(26, H - 13, 8, 6, C.adobe2, 0.7);
  });

  /** 圆角塔（扶壁塔）：x0..x1，地面前沿 yf，顶 yt */
  function bastion(x0, x1, yf, yt, fill) {
    var w = x1 - x0, s = K.rect(x0, yt, w, yf - yt, fill || C.adobe, 1.5);
    s += K.flat([[x1 - w * 0.35, yt + 1], [x1 - 0.8, yt + 1], [x1 - 0.8, yf - 0.8], [x1 - w * 0.35, yf - 0.8]], C.adobe3, 0.35);
    s += K.ln(K.seg(x0 + w * 0.3, yt + 3, x0 + w * 0.3, yf - 2), 0.6, 0.35);
    s += K.rect(x0 - 1.5, yt - 3, w + 3, 3, fill || C.adobe, 1) + P.merlons(x0 - 1, x1 + 1, yt - 3, 5, fill || C.adobe, 1.2);
    return s;
  }

  defs.push({
    id: 'arab-common-caravanserai-01', name: '商队客栈（方院门楼）', fp: [4, 3], up: 96, kind: 'caravanserai', facility: 'caravanserai',
    tags: ['courtyard', 'two_storey_arcade', 'gatehouse', 'crenellated'], roof: 'flat_mud',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, cx = W / 2, s = '';
      var x0 = 8, x1 = W - 8, yf = H - 4, h = 46;
      s += Ms.court({
        x0: x0, x1: x1, yb: gy + 6, yf: yf, h: h, t: 14, wall: C.adobe, top: C.adobe2, inner: C.adobe, floor: C.sand, lip: 3, W: W, H: H,
        content: function (q) {
          var t = '', w = q.ix1 - q.ix0;
          t += F.arcade(q.ix0 + 2, q.ix1 - 2, q.fy, 17, 8, C.hole);
          t += K.rect(q.ix0, q.fy - 23, w, 2.2, C.adobe2, 0.8);
          t += F.arcade(q.ix0 + 2, q.ix1 - 2, q.fy - 24, 13, 8, C.hole);
          t += G.pavers(q.ix0, q.fy, q.ix1, q.iyB, 13, 21, 0.25);
          // 院内：饮水槽 + 货包
          t += G.basin(q.ix0 + 6, q.fy + 3, 26, 8, 2) + G.basin(q.ix1 - 32, q.fy + 3, 26, 8, 2);
          t += sacks(q.ix0 + 8, q.iyB - 2, 3, 12) + sacks(q.ix1 - 26, q.iyB - 2, 3, 14);
          return t;
        }
      });
      // 外立面：高窗、瓷砖带、雉堞
      s += F.windows(x0 + 18, cx - 30, yf - h + 10, 4, 6, 3) + F.windows(cx + 30, x1 - 18, yf - h + 10, 4, 6, 3);
      s += P.merlons(x0 + 14, cx - 28, yf - h - 3, 5, C.adobe) + P.merlons(cx + 28, x1 - 14, yf - h - 3, 5, C.adobe);
      s += bastion(x0 - 4, x0 + 12, yf, yf - h - 8) + bastion(x1 - 12, x1 + 4, yf, yf - h - 8);
      // 大门楼
      s += F.pishtaq(cx - 28, cx + 28, yf, yf - h - 34, { wall: C.lime });
      s += P.merlons(cx - 28, cx + 28, yf - h - 34, 6, C.lime);
      return s;
    }
  });

  defs.push({
    id: 'arab-common-inn-01', name: '旅舍茶馆（木格窗二层）', fp: [3, 2], up: 92, kind: 'inn_teahouse', facility: 'inn',
    tags: ['two_storey', 'mashrabiya', 'teahouse', 'roof_terrace', 'windtower'], roof: 'flat_mud',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, s = '';
      var x0 = 8, x1 = W - 8, yf = H - 14, h = 72;
      s += Ms.block({ x0: x0, x1: x1, yb: gy + 8, yf: yf, h: h, lip: 3, wall: C.lime, top: C.lime2, W: W, H: H });
      // 屋顶露台：布棚 + 风塔
      var ty = gy + 8 - h;
      s += T.windtower(x1 - 22, ty + 22, 14, 36, C.adobe);
      s += K.rect(x0 + 16, ty + 6, 2, 16, C.wood, 0.7) + K.rect(x0 + 54, ty + 6, 2, 16, C.wood, 0.7);
      s += F.awning(x0 + 12, x0 + 60, ty + 4, 6, C.turq, C.lime);
      s += K.rect(x0 + 20, ty + 16, 30, 5, C.ochre, 0.8);
      // 二层：木格窗外挑
      s += F.windows(x0 + 6, x1 - 6, yf - h + 12, 13, 17, 4, true);
      s += P.tileBand(x0 + 1, x1 - 1, yf - 37, 4, true);
      // 底层：拱廊 + 布棚 + 门
      s += F.arcade(x0 + 4, x1 - 4, yf - 1, 24, 5, C.hole, C.lime2);
      s += F.door(W / 2, yf - 1, 14, 24, C.ochre);
      s += F.awning(x0 + 2, W / 2 - 12, yf - 30, 6, C.ochre2, C.lime) + F.awning(W / 2 + 12, x1 - 2, yf - 30, 6, C.ochre2, C.lime);
      // 门前茶座：长凳 + 地毯 + 茶壶
      s += K.rect(x0 + 6, yf + 2, 40, 8, C.ochre, 0.9) + K.rect(x0 + 9, yf + 3.5, 34, 5, C.cobalt, 0.5);
      s += K.rect(x1 - 46, yf + 2, 40, 8, C.ochre, 0.9) + K.rect(x1 - 43, yf + 3.5, 34, 5, C.turq, 0.5);
      [x0 + 26, x1 - 26].forEach(function (x) {
        s += K.ellipse(x, yf + 4, 6, 2, C.gold, 0.7) + K.path('M' + f(x - 2.5) + ' ' + f(yf + 3) + 'q0 -5 2.5 -5q2.5 0 2.5 5Z', C.gold, 0.7);
      });
      return s;
    }
  });

  if (N) module.exports = defs;
  else root.TownArtAS_defs = (root.TownArtAS_defs || []).concat(defs);
})(this);
