/*
 * 基础设施类：水车 noria、风磨、码头（三角帆船 dhow）、墓园、石桥、矿井口、锅炉房、结界塔。
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

  /** 大木轮：中心 cx,cy，半径 r，辐条 n，水斗 */
  function wheel(cx, cy, r, n) {
    var ring = 'M' + f(cx - r) + ' ' + f(cy) + 'A' + f(r) + ' ' + f(r) + ' 0 1 0 ' + f(cx + r) + ' ' + f(cy) + 'A' + f(r) + ' ' + f(r) + ' 0 1 0 ' + f(cx - r) + ' ' + f(cy);
    var s = K.ln(ring, 3.4, 1, C.wood) + K.circle(cx, cy, r + 1.6, 'none', 0.9) + K.circle(cx, cy, r - 1.8, 'none', 0.8);
    var d = '';
    for (var i = 0; i < n; i++) { var a = Math.PI * 2 * i / n; d += K.seg(cx, cy, cx + Math.cos(a) * (r - 2), cy + Math.sin(a) * (r - 2)); }
    s += K.ln(d, 1.4, 1, C.wood) + K.ln(d, 0.5, 0.6);
    for (var j = 0; j < n * 2; j++) {
      var b = Math.PI * 2 * j / (n * 2), x = cx + Math.cos(b) * (r + 1.5), y = cy + Math.sin(b) * (r + 1.5);
      s += K.rect(x - 2, y - 1.6, 4, 3.2, C.ochre2, 0.6);
    }
    return s + K.circle(cx, cy, 4, C.wood, 1) + K.circle(cx, cy, 1.6, C.iron, 0.5);
  }

  defs.push({
    id: 'arab-common-noria-01', name: '水车（诺里亚大木轮）', fp: [3, 2], up: 96, kind: 'noria', facility: 'mill',
    tags: ['water_wheel', 'aqueduct', 'river'], roof: 'none', note: '提水水车，归 mill；需临河放置，水面为示意',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, s = '';
      // 水渠（前景河道）
      s += K.rect(0, H - 30, W, 26, C.water, 1);
      s += K.ln('M6 ' + (H - 20) + 'q4 -2 8 0M40 ' + (H - 12) + 'q4 -2 8 0M100 ' + (H - 22) + 'q4 -2 8 0', 0.7, 0.6, C.lime);
      // 引水渡槽：拱桥墩 + 顶槽
      s += Ms.block({ x0: W - 52, x1: W - 4, yb: gy + 4, yf: H - 30, h: 58, lip: 0, wall: C.adobe, top: C.adobe2, W: W, H: H });
      s += F.arcade(W - 50, W - 6, H - 31, 30, 2, C.hole);
      s += K.rect(W - 52, gy - 58, 48, 4, C.water, 0.9);
      // 石墩 + 大轮
      var cx = 54, cy = H - 52, r = 44;
      s += K.rect(cx - 6, cy, 12, H - 6 - cy, C.adobe2, 1.2);
      s += wheel(cx, cy, r, 12);
      s += K.ln('M' + f(cx + r - 2) + ' ' + f(cy - r + 12) + 'Q' + f(W - 56) + ' ' + f(gy - 58) + ' ' + f(W - 52) + ' ' + f(gy - 56), 1.4, 0.8, C.water);
      return s;
    }
  });

  defs.push({
    id: 'arab-common-windmill-01', name: '风磨（波斯立轴风车）', fp: [2, 2], up: 92, kind: 'asbad_windmill', facility: 'mill',
    tags: ['windmill', 'vertical_axis', 'reed_sails'], roof: 'flat_mud', note: '立轴风车（asbad），风帆在两道高墙间，归 mill',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, s = '', yf = H - 6;
      s += Ms.block({ x0: 6, x1: W - 6, yb: gy + 10, yf: yf, h: 30, lip: 0, wall: C.adobe, top: C.adobe2, W: W, H: H });
      s += P.arch(W / 2 - 8, yf, 16, 20, C.hole, 1);
      var by = gy + 10 - 30;
      // 两道高翼墙
      s += K.rect(8, by - 66, 14, 80, C.adobe, 1.4) + K.rect(W - 22, by - 66, 14, 80, C.adobe, 1.4);
      s += K.flat([[W - 13, by - 65], [W - 8.8, by - 65], [W - 8.8, by + 13], [W - 13, by + 13]], C.adobe3, 0.35);
      // 立轴风帆（苇帘）
      s += K.ln(K.seg(W / 2, by - 64, W / 2, by + 8), 2, 1, C.wood);
      // 四片苇帘：两片正对（宽）、两片侧转（窄），表示绕立轴转动
      s += K.rect(W / 2 - 22, by - 60, 21, 62, C.sand, 0.9) + K.rect(W / 2 + 1, by - 60, 8, 62, C.gold, 0.9);
      s += K.rect(W / 2 - 1, by - 60, 2, 62, C.wood, 0.5);
      var d = ''; for (var y = by - 54; y < by; y += 6) d += K.seg(W / 2 - 22, y, W / 2 + 22, y);
      s += K.ln(d, 0.5, 0.5);
      s += K.rect(6, by - 68, W - 12, 3, C.wood, 1);
      return s;
    }
  });

  /** 三角帆船 dhow：船底中 cx, 水线 wy, 长 L */
  function dhow(cx, wy, L) {
    var s = K.path('M' + f(cx - L / 2) + ' ' + f(wy - 9) + 'L' + f(cx + L / 2) + ' ' + f(wy - 13) + 'Q' + f(cx + L * 0.4) + ' ' + f(wy + 2) + ' ' + f(cx + L * 0.2) + ' ' + f(wy + 2) +
      'L' + f(cx - L * 0.36) + ' ' + f(wy + 2) + 'Q' + f(cx - L * 0.46) + ' ' + f(wy - 2) + ' ' + f(cx - L / 2) + ' ' + f(wy - 9) + 'Z', C.wood, 1.4);
    s += K.ln(K.seg(cx - L * 0.45, wy - 6, cx + L * 0.45, wy - 9), 0.7, 0.7, C.gold);
    s += K.ln(K.seg(cx, wy - 9, cx - 2, wy - 58), 1.6, 1, C.wood);
    s += K.poly([[cx - L * 0.45, wy - 16], [cx + L * 0.25, wy - 66], [cx + L * 0.2, wy - 16]], C.lime, 1.2);
    s += K.ln(K.seg(cx - L * 0.45, wy - 16, cx + L * 0.25, wy - 66), 1.4, 1, C.wood);
    s += K.ln(K.seg(cx - L * 0.1, wy - 16, cx + L * 0.06, wy - 44), 0.6, 0.4);
    return s;
  }

  defs.push({
    id: 'arab-common-dock-01', name: '码头（三角帆船 dhow）', fp: [3, 3], up: 70, kind: 'dhow_dock', facility: 'dock',
    tags: ['harbor', 'dhow', 'lateen_sail', 'jetty'], roof: 'none', note: '前两排为水面示意，后排为石砌码头',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, s = '';
      s += K.rect(0, gy + 36, W, H - gy - 36, C.water, 1);
      s += K.ln('M10 ' + (H - 20) + 'q5 -2 10 0M60 ' + (H - 10) + 'q5 -2 10 0M110 ' + (H - 28) + 'q5 -2 10 0', 0.7, 0.6, C.lime);
      s += K.rect(0, gy, W, 36, C.lime2, 1.4) + K.rect(0, gy + 30, W, 8, C.adobe2, 1.2);
      s += G.pavers(0, gy, W, gy + 30, 12, 31, 0.3);
      // 木栈桥伸入水中
      s += K.rect(W - 40, gy + 34, 18, H - gy - 40, C.wood, 1.1);
      var d = ''; for (var y = gy + 40; y < H - 6; y += 5) d += K.seg(W - 40, y, W - 22, y);
      s += K.ln(d, 0.5, 0.6);
      s += K.circle(W - 40, H - 8, 2, C.wood, 0.7) + K.circle(W - 22, H - 8, 2, C.wood, 0.7);
      // 系船桩 + 货包
      s += K.rect(14, gy + 22, 5, 8, C.iron, 0.8) + K.rect(26, gy + 8, 12, 9, C.sand, 0.8) + K.rect(42, gy + 10, 9, 7, C.ochre2, 0.8);
      s += dhow(58, H - 16, 76);
      return s;
    }
  });

  defs.push({
    id: 'arab-common-cemetery-01', name: '墓园（圣墓与墓碑）', fp: [3, 2], up: 62, kind: 'cemetery_qubba', facility: 'cemetery',
    tags: ['tombs', 'qubba', 'low_wall', 'cypress'], roof: 'none', note: '院墙低矮；圣墓小穹（qubba）',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, s = '';
      s += K.rect(4, gy + 4, W - 8, H - gy - 8, C.sand, 1.2);
      // 圣墓小穹（后中）
      s += Ms.block({ x0: 54, x1: 92, yb: gy + 6, yf: gy + 36, h: 22, lip: 0, W: W, H: H });
      s += P.arch(66, gy + 36, 14, 16, C.hole, 0.9) + Ms.dome(73, gy + 6 - 22 + 30, 17, 26, C.lime2, 'pointed', C.lime);
      s += G.cypress(20, gy + 30, 34) + G.cypress(W - 20, gy + 30, 34);
      // 墓碑（竖碑 + 低墓台）
      var r = K.rng(41);
      for (var j = 0; j < 2; j++) for (var i = 0; i < 6; i++) {
        var x = 14 + i * 21 + r() * 3, y = gy + 50 + j * 18;
        s += K.rect(x - 6, y - 2, 12, 4, C.lime2, 0.7);
        s += K.path('M' + f(x - 2) + ' ' + f(y) + 'V' + f(y - 7) + 'Q' + f(x) + ' ' + f(y - 10) + ' ' + f(x + 2) + ' ' + f(y - 7) + 'V' + f(y) + 'Z', C.lime, 0.7);
      }
      // 前沿矮墙 + 门口
      s += K.rect(4, H - 10, W / 2 - 14, 6, C.lime, 1) + K.rect(W / 2 + 10, H - 10, W / 2 - 14, 6, C.lime, 1);
      return s;
    }
  });

  defs.push({
    id: 'arab-common-bridge-01', name: '石桥（尖拱桥）', fp: [4, 2], up: 30, kind: 'pointed_arch_bridge', facility: 'bridge',
    tags: ['stone', 'pointed_arch', 'river'], roof: 'none', note: '东西向跨河；水面为示意',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, s = '';
      s += K.rect(0, gy + 8, W, H - gy - 12, C.water, 1);
      var deckB = gy + 6, deckF = H - 34, h = 26;
      s += K.rect(0, deckB - h + 18, W, deckF - deckB, C.lime2, 1.4);
      s += G.pavers(0, deckB - h + 18, W, deckF - h + 18, 12, 52, 0.3);
      s += K.rect(0, deckF - h + 18, W, h + 12, C.adobe, 1.6);
      // 三孔尖拱 + 分水尖
      [[22, 34], [78, 36], [140, 34]].forEach(function (a) { s += P.arch(a[0], H - 4, a[1], 30, C.water, 1.2); });
      s += K.rect(0, deckF - h + 14, W, 4, C.lime, 1) + P.tileBand(2, W - 2, deckF - h + 20, 3.5, true);
      s += K.ln('M30 ' + (H - 12) + 'q4 -2 8 0M90 ' + (H - 10) + 'q4 -2 8 0M150 ' + (H - 12) + 'q4 -2 8 0', 0.7, 0.6, C.lime);
      return s;
    }
  });

  defs.push({
    id: 'arab-common-minehead-01', name: '矿井口（滑轮绞架）', fp: [2, 2], up: 66, kind: 'mine_shaft', facility: 'mine_head',
    tags: ['shaft', 'windlass', 'ore_baskets'], roof: 'none',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, s = '', cx = W / 2;
      s += K.boxShadow(18, W - 18, gy + 30, H - 20, 8, W, H);
      s += K.rect(18, gy + 30, W - 36, H - gy - 50, C.adobe2, 1.4) + K.rect(26, gy + 36, W - 52, H - gy - 62, C.hole, 1);
      // 三角木架 + 滑轮 + 绳
      s += K.ln(K.seg(16, H - 22, cx, gy - 50) + K.seg(W - 16, H - 22, cx, gy - 50) + K.seg(cx, gy + 22, cx, gy - 50), 2.2, 1, C.wood);
      s += K.circle(cx, gy - 44, 5, C.wood, 1) + K.ln(K.seg(cx + 4, gy - 44, cx + 4, gy + 40), 0.7, 0.8);
      s += K.rect(cx + 1, gy + 40, 7, 6, C.wood, 0.7);
      // 矿石筐 + 矿渣堆
      s += K.ellipse(14, H - 10, 7, 5, C.wood, 0.9) + K.ellipse(14, H - 13, 5, 2, C.iron, 0.6);
      s += K.path('M' + f(W - 32) + ' ' + f(H - 5) + 'Q' + f(W - 20) + ' ' + f(H - 26) + ' ' + f(W - 6) + ' ' + f(H - 5) + 'Z', C.iron, 1);
      return s;
    }
  });

  defs.push({
    id: 'arab-common-boilerhouse-01', name: '锅炉房（浴室火房）', fp: [2, 2], up: 92, kind: 'furnace_house', facility: 'boiler_house',
    tags: ['chimney', 'fuel_stack', 'furnace'], roof: 'flat_mud', note: '借浴室火房（gulkhan）形制',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, s = '', yf = H - 6, h = 38, ty = gy + 8 - h;
      s += Ms.block({ x0: 8, x1: W - 8, yb: gy + 8, yf: yf, h: h, lip: 2, wall: C.adobe, top: C.adobe2, W: W, H: H });
      s += K.rect(W - 34, ty - 50, 14, 64, C.adobe2, 1.4) + K.rect(W - 36, ty - 53, 18, 3, C.adobe3, 0.9);
      s += K.ln('M' + f(W - 27) + ' ' + f(ty - 56) + 'q-5 -6 1 -11q5 -5 0 -11', 1, 0.45);
      s += P.arch(18, yf, 22, 22, C.hole, 1.1);
      s += K.path('M23 ' + f(yf - 1) + 'q3 -9 6 -4q2 -8 6 4Z', C.ochre2, 0.6);
      // 燃料垛（干草/粪饼）
      for (var i = 0; i < 3; i++) s += K.ellipse(58 + i * 9, yf - 3, 4.5, 3, C.adobe3, 0.7);
      s += K.ellipse(62, yf - 8, 4.5, 3, C.adobe3, 0.7) + K.ellipse(71, yf - 8, 4.5, 3, C.adobe3, 0.7);
      return s;
    }
  });

  defs.push({
    id: 'arab-common-wardtower-01', name: '结界塔（星形瓷砖塔）', fp: [1, 1], up: 136, kind: 'star_tile_tower', facility: 'ward_tower',
    tags: ['tower', 'star_tiles', 'arcane', 'lantern'], roof: 'none', note: '奇幻设施：塔身满铺八角星瓷砖，顶端金灯',
    draw: function (c) {
      var W = c.W, H = c.H, s = '', x0 = 12, x1 = W - 12, yf = H - 6, yt = 28;
      s += K.boxShadow(x0 - 4, x1 + 4, yf - 14, yf, 8, W, H);
      s += K.rect(x0 - 5, yf - 12, x1 - x0 + 10, 12, C.lime2, 1.3);
      s += T.starTiles(x0, yt, x1 - x0, yf - 12 - yt, 4.2);
      s += K.rect(x0 - 3, yt - 4, x1 - x0 + 6, 4, C.lime, 1);
      // 灯亭 + 尖顶 + 金球
      s += K.rect(x0 + 2, yt - 18, x1 - x0 - 4, 14, C.lime, 1.1) + P.arch(W / 2 - 3.5, yt - 4, 7, 11, C.gold, 0.7);
      s += K.poly([[x0 - 1, yt - 18], [W / 2, yt - 40], [x1 + 1, yt - 18]], C.cobalt2, 1.2);
      s += K.circle(W / 2, yt - 44, 3.2, C.gold, 0.7) + P.star8(W / 2, yt - 52, 4.2, C.gold, 0.6);
      return s;
    }
  });

  if (N) module.exports = defs;
  else root.TownArtAS_defs = (root.TownArtAS_defs || []).concat(defs);
})(this);
