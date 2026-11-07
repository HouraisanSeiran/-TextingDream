/*
 * 文化地标（category=landmark，占地到 6×6，上伸到 240 px）：大清真寺、宫殿园林四分园、卡斯巴城堡、岩凿神殿、天文台。
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

  /** 收分夯土塔：x0..x1 为底宽，yf 地面前沿，yt 塔顶；收分 k px；带雉堞与三角砖纹 */
  function taper(x0, x1, yf, yt, k, fill) {
    var s = K.poly([[x0, yf], [x0 + k, yt], [x1 - k, yt], [x1, yf]], fill || C.adobe, 1.6);
    s += K.flat([[x1 - k - (x1 - x0) * 0.25, yt + 1], [x1 - k - 0.8, yt + 1], [x1 - 0.8, yf - 0.8], [x1 - (x1 - x0) * 0.3, yf - 0.8]], C.adobe3, 0.35);
    var w = x1 - x0 - 2 * k, n = Math.max(2, Math.round(w / 7)), st = w / n, d = '';
    for (var i = 0; i < n; i++) { var a = x0 + k + st * i; d += 'M' + f(a + 1) + ' ' + f(yt + 13) + 'L' + f(a + st / 2) + ' ' + f(yt + 7) + 'L' + f(a + st - 1) + ' ' + f(yt + 13); }
    s += K.ln(d, 0.8, 0.7, C.adobe3);
    s += K.rect(x0 + k - 2, yt - 3, w + 4, 3, fill || C.adobe, 1) + P.merlons(x0 + k - 1, x1 - k + 1, yt - 3, 6, fill || C.adobe, 1.4);
    return s;
  }

  /** 平屋顶杂物：石缝 + 上人口小亭 + 晾晒地毯（让大屋面不空） */
  function roofClutter(x0, x1, y0, y1, seed, fill) {
    var r = K.rng(seed), s = G.pavers(x0, y0, x1, y1, 14, seed, 0.25), w = x1 - x0;
    var hx = x0 + w * (0.15 + r() * 0.15), hy = y0 + (y1 - y0) * 0.3;
    s += K.rect(hx, hy, 16, 9, fill || C.adobe, 1) + K.rect(hx + 5, hy + 3, 6, 6, C.hole, 0.7) + K.rect(hx - 1, hy - 2, 18, 2, C.adobe3, 0.7);
    var cx = x0 + w * (0.62 + r() * 0.12), cy = y0 + (y1 - y0) * 0.45;
    s += K.ln(K.seg(cx - 14, cy, cx + 14, cy), 0.8, 0.8, C.wood);
    s += K.rect(cx - 12, cy, 10, 8, C.ochre2, 0.6) + K.rect(cx + 1, cy, 10, 7, C.cobalt2, 0.6);
    return s;
  }

  defs.push({
    id: 'arab-common-landmark-greatmosque-01', name: '大清真寺（四塔大穹顶）', fp: [6, 5], up: 236, category: 'landmark', culture: 'islamic',
    kind: 'great_mosque', facility: 'temple', tags: ['dome', 'four_minarets', 'grand_courtyard', 'iwan', 'ablution_pool'], roof: 'flat_mud',
    note: '穹顶无对应 RoofId，按 flat_mud 记',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, cx = W / 2, s = '';
      // 后排两座高宣礼塔
      s += T.minaret(22, gy + 34, 7, 214, { kind: 'square', tiers: 3, capFill: C.turq });
      s += T.minaret(W - 22, gy + 34, 7, 214, { kind: 'square', tiers: 3, capFill: C.turq });
      // 礼拜大殿
      s += Ms.block({ x0: 38, x1: W - 38, yb: gy + 2, yf: gy + 80, h: 70, band: 5, W: W, H: H });
      s += F.windows(46, cx - 40, gy + 18, 6, 10, 4) + F.windows(cx + 40, W - 46, gy + 18, 6, 10, 4);
      var dy = gy - 28;
      [70, W - 70].forEach(function (x) { s += Ms.drum(x, dy + 4, 15, 8, C.lime, 2) + Ms.dome(x, dy - 4, 16, 24, C.turq, 'pointed'); });
      s += Ms.drum(cx, dy, 46, 20, C.lime, 9);
      s += P.tileBand(cx - 46, cx + 46, dy - 20, 5, true);
      s += Ms.dome(cx, dy - 20, 48, 88, C.turq, 'pointed');
      s += F.pishtaq(cx - 34, cx + 34, gy + 44, gy - 28, { door: false });
      s += P.merlons(cx - 34, cx + 34, gy - 28, 6, C.lime);
      // 大内院
      s += Ms.court({
        x0: 6, x1: W - 6, yb: gy + 74, yf: H - 3, h: 30, t: 14, riwaq: true, lip: 2, W: W, H: H,
        content: function (q) {
          var t = G.pavers(q.ix0, q.fy, q.ix1, q.iyB, 16, 33, 0.22);
          t += G.basin(q.cx - 70, q.cy - 6, 40, 12, 2.5) + G.basin(q.cx + 30, q.cy - 6, 40, 12, 2.5);
          t += G.pool(q.cx, q.cy - 2, 22, 12);
          t += G.palm(q.ix0 + 16, q.iyB - 2, 30, 5) + G.palm(q.ix1 - 16, q.iyB - 2, 30, 9);
          t += G.palm(q.ix0 + 44, q.iyB - 4, 26, 13) + G.palm(q.ix1 - 44, q.iyB - 4, 26, 17);
          return t;
        }
      });
      s += F.arcade(22, cx - 32, H - 6, 18, 5, C.lime2) + F.arcade(cx + 32, W - 22, H - 6, 18, 5, C.lime2);
      // 前排两座较矮宣礼塔（院角）
      s += T.minaret(14, H - 6, 6, 150, { kind: 'round', tiers: 2, capFill: C.turq });
      s += T.minaret(W - 14, H - 6, 6, 150, { kind: 'round', tiers: 2, capFill: C.turq });
      s += F.pishtaq(cx - 28, cx + 28, H - 3, H - 66, { alt: true });
      s += P.merlons(cx - 28, cx + 28, H - 66, 6, C.lime);
      return s;
    }
  });

  defs.push({
    id: 'arab-common-landmark-charbagh-01', name: '宫殿园林（四分园）', fp: [6, 5], up: 150, category: 'landmark', culture: 'persian',
    kind: 'palace_garden', facility: 'lord_hall', tags: ['charbagh', 'water_channels', 'pavilion', 'arcade', 'cypress', 'fountain'], roof: 'flat_mud',
    note: '波斯 / 安达卢斯四分园：十字水渠分四块花圃；后殿伊旺 + 穹顶亭，归 lord_hall',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, cx = W / 2, s = '';
      // 后殿：长拱廊 + 中央伊旺 + 穹顶亭
      s += Ms.block({ x0: 20, x1: W - 20, yb: gy + 2, yf: gy + 60, h: 64, lip: 3, band: 5, bandAlt: true, W: W, H: H });
      var ty = gy + 2 - 64;
      s += Ms.drum(cx, ty + 14, 22, 10, C.lime) + Ms.dome(cx, ty + 4, 24, 40, C.palm2, 'onion', C.palm);
      [60, W - 60].forEach(function (x) {
        s += K.rect(x - 12, ty + 2, 24, 16, C.lime, 1.1) + F.arcade(x - 10, x + 10, ty + 18, 10, 2, C.hole);
        s += K.rect(x - 14, ty - 1, 28, 3, C.lime2, 0.9) + Ms.dome(x, ty - 1, 11, 14, C.turq, 'pointed');
      });
      s += F.windows(30, cx - 40, gy + 6, 12, 15, 3, true) + F.windows(cx + 40, W - 30, gy + 6, 12, 15, 3, true);
      s += F.arcade(26, cx - 36, gy + 59, 22, 5, C.hole, C.lime2) + F.arcade(cx + 36, W - 26, gy + 59, 22, 5, C.hole, C.lime2);
      s += F.pishtaq(cx - 32, cx + 32, gy + 60, gy - 24, { door: false, alt: true });
      // 园地（低围墙内）
      var gx0 = 10, gx1 = W - 10, gyb = gy + 62, gyf = H - 12;
      s += K.rect(gx0, gyb, gx1 - gx0, gyf - gyb, C.sand, 1.2);
      var mx = cx, my = (gyb + gyf) / 2;
      // 十字水渠
      s += G.basin(gx0 + 6, my - 5, gx1 - gx0 - 12, 10, 2) + G.basin(mx - 5, gyb + 4, 10, gyf - gyb - 8, 2);
      // 四块花圃 + 柏树
      [[gx0 + 10, gyb + 8, mx - 12], [mx + 12, gyb + 8, gx1 - 10]].forEach(function (b, i) {
        s += G.bed(b[0], b[1], b[2] - b[0], my - 8 - b[1], 61 + i) + G.bed(b[0], my + 8, b[2] - b[0], gyf - 8 - my - 8, 71 + i);
      });
      s += G.pool(mx, my, 20, 11);
      [gx0 + 18, mx - 26, mx + 26, gx1 - 18].forEach(function (x, i) {
        s += G.cypress(x, my - 10, 30) + (i % 3 === 0 ? G.cypress(x, gyf - 10, 28) : '');
      });
      // 前沿：矮墙 + 门
      s += K.rect(gx0 - 4, H - 14, cx - 20 - gx0 + 4, 10, C.lime, 1.2) + K.rect(cx + 20, H - 14, gx1 + 4 - cx - 20, 10, C.lime, 1.2);
      s += P.tileBand(gx0 - 3, cx - 21, H - 12, 3.5) + P.tileBand(cx + 21, gx1 + 3, H - 12, 3.5);
      s += P.archFramed(cx - 11, H - 4, 22, 24, C.turq2, C.hole);
      return s;
    }
  });

  defs.push({
    id: 'arab-common-landmark-kasbah-01', name: '卡斯巴卫城（层叠夯土塔堡）', fp: [5, 5], up: 210, category: 'landmark', culture: 'maghrebi',
    kind: 'kasbah', facility: 'barracks', tags: ['citadel', 'tapered_towers', 'crenellated', 'rammed_earth', 'gatehouse'], roof: 'flat_mud',
    note: '马格里布夯土卫城；驻军与治所合一，facility 取 barracks',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, cx = W / 2, s = '';
      // 后排：最高主塔（主楼）
      s += Ms.block({ x0: 70, x1: W - 70, yb: gy + 6, yf: gy + 70, h: 150, lip: 0, wall: C.adobe, top: C.adobe2, W: W, H: H });
      s += taper(70, W - 70, gy + 70, gy - 80, 6, C.adobe);
      s += F.windows(82, W - 82, gy - 40, 7, 10, 4, true) + F.windows(82, W - 82, gy + 2, 5, 8, 4);
      s += roofClutter(76, W - 76, gy - 140, gy - 86, 53, C.adobe);
      // 中排：两侧塔 + 连墙
      s += Ms.block({ x0: 24, x1: W - 24, yb: gy + 60, yf: gy + 150, h: 90, lip: 0, wall: C.adobe2, top: C.adobe3, W: W, H: H });
      s += roofClutter(68, W - 68, gy - 28, gy + 58, 31, C.adobe2);
      s += P.merlons(24, W - 24, gy + 60, 6, C.adobe2);
      s += taper(14, 66, gy + 150, gy + 20, 5, C.adobe) + taper(W - 66, W - 14, gy + 150, gy + 20, 5, C.adobe);
      s += P.mashrabiya(32, gy + 50, 14, 14) + P.mashrabiya(W - 46, gy + 50, 14, 14);
      s += F.windows(80, W - 80, gy + 96, 5, 8, 5);
      // 前排：外墙 + 角塔 + 门楼
      var yf = H - 4, h = 54;
      s += Ms.block({ x0: 8, x1: W - 8, yb: gy + 150, yf: yf, h: h, lip: 0, wall: C.adobe, top: C.adobe2, W: W, H: H });
      s += roofClutter(40, W - 40, gy + 98, yf - h - 2, 43, C.adobe);
      s += P.merlons(8, W - 8, yf - h, 6, C.adobe);
      var d = ''; for (var x = 30; x < W - 26; x += 18) if (Math.abs(x - cx) > 30) d += K.seg(x, yf - h + 14, x, yf - h + 24);
      s += K.ln(d, 1.6, 1, C.hole);
      s += taper(2, 34, yf, yf - h - 26, 3, C.adobe) + taper(W - 34, W - 2, yf, yf - h - 26, 3, C.adobe);
      s += taper(cx - 32, cx + 32, yf, yf - h - 22, 3, C.adobe2);
      s += P.arch(cx - 13, yf, 26, 38, C.hole, 1.4) + F.door(cx, yf, 18, 28, C.ochre);
      s += P.tileBand(cx - 22, cx + 22, yf - 50, 4);
      return s;
    }
  });

  defs.push({
    id: 'arab-common-landmark-rocktemple-01', name: '岩凿神殿（佩特拉式崖面）', fp: [5, 4], up: 200, category: 'landmark', culture: 'nabataean',
    kind: 'rock_cut_temple', facility: 'temple', tags: ['rock_cut', 'cliff_face', 'tholos', 'columns', 'pediment'], roof: 'none',
    note: '纳巴泰岩凿立面：崖面凿出双层柱廊、断山花与圆亭；立面后是山体，roof=none',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, cx = W / 2, s = '';
      var rose = '#c9876a', rose2 = '#b06e55', rose3 = '#8f5644';
      // 崖体：不规则顶线
      var r = K.rng(97), top = [[0, H - 40]];
      for (var x = 0; x <= W; x += 24) top.push([x, 10 + r() * 26 + Math.abs(x - cx) * 0.12]);
      top.push([W, H - 40]);
      s += K.poly(top.concat([[W, H - 40]]), rose2, 1.8);
      var cliff = [[0, H - 40]].concat(top.slice(1, -1)).concat([[W, H - 40], [W, H - 4], [0, H - 4]]);
      s += K.poly(cliff, rose, 1.8);
      // 岩层纹
      var d = ''; for (var y = 40; y < H - 10; y += 14) { var o = r() * 20; d += 'M' + f(4 + o) + ' ' + f(y) + 'q30 ' + f(r() * 6 - 3) + ' 60 0'; d += 'M' + f(W - 70 - o) + ' ' + f(y + 5) + 'q30 ' + f(r() * 6 - 3) + ' 60 0'; }
      s += K.ln(d, 0.8, 0.45, rose3);
      s += K.flat([[W - 40, 30], [W - 4, 50], [W - 4, H - 6], [W - 40, H - 6]], rose3, 0.25);
      // 两侧崖面小墓立面（纳巴泰阶梯冠）
      [[10, 120], [W - 52, 132]].forEach(function (t, i) {
        var tx = t[0], tyb = t[1] + 46, tw = 40;
        s += K.rect(tx, t[1], tw, 46, rose2, 1);
        for (var k = 0; k < 2; k++) {
          var sx = tx + 4 + k * 20;
          s += K.poly([[sx, t[1]], [sx, t[1] - 4], [sx + 3, t[1] - 4], [sx + 3, t[1] - 8], [sx + 9, t[1] - 8], [sx + 9, t[1] - 4], [sx + 12, t[1] - 4], [sx + 12, t[1]]], rose2, 0.8);
        }
        s += K.rect(tx + 2, t[1] + 6, tw - 4, 3, rose, 0.7) + K.rect(tx + 14, tyb - 22, 12, 22, C.hole, 0.9);
        s += K.ln(K.seg(tx + 5, t[1] + 12, tx + 5, tyb) + K.seg(tx + tw - 5, t[1] + 12, tx + tw - 5, tyb), 1.6, 1, rose3);
      });
      // 凿出的立面龛
      var fx0 = cx - 72, fx1 = cx + 72, fy1 = H - 10, fy0 = 46;
      s += K.rect(fx0, fy0, fx1 - fx0, fy1 - fy0, rose2, 1.2);
      // 上层：断山花 + 圆亭
      var uy = fy0 + 74;
      s += K.rect(fx0 + 6, uy, fx1 - fx0 - 12, 5, rose, 1);
      s += K.poly([[fx0 + 6, uy], [fx0 + 34, uy - 16], [fx0 + 40, uy - 16], [fx0 + 40, uy]], rose, 1);
      s += K.poly([[fx1 - 6, uy], [fx1 - 34, uy - 16], [fx1 - 40, uy - 16], [fx1 - 40, uy]], rose, 1);
      s += K.rect(cx - 20, fy0 + 26, 40, uy - fy0 - 26, rose, 1.1);
      s += K.path('M' + f(cx - 22) + ' ' + f(fy0 + 26) + 'L' + f(cx) + ' ' + f(fy0 + 4) + 'L' + f(cx + 22) + ' ' + f(fy0 + 26) + 'Z', rose, 1.1);
      s += K.ellipse(cx, fy0 + 2, 5, 3, rose, 0.9);
      var cd = '';
      for (var i = 0; i < 4; i++) { var x1 = cx - 15 + i * 10; cd += K.seg(x1, fy0 + 28, x1, uy - 1); }
      [fx0 + 12, fx0 + 24, fx1 - 12, fx1 - 24].forEach(function (x2) { cd += K.seg(x2, uy - 12, x2, uy - 1); });
      s += K.ln(cd, 2.2, 1, rose3) + K.ln(cd, 0.6, 0.6);
      // 下层：六柱门廊 + 山花
      var ly = uy + 5, lb = fy1 - 4;
      s += K.poly([[fx0 + 6, ly + 20], [cx, ly + 2], [fx1 - 6, ly + 20]], rose, 1.2);
      s += K.rect(fx0 + 6, ly + 20, fx1 - fx0 - 12, 5, rose, 1);
      s += K.rect(fx0 + 10, ly + 25, fx1 - fx0 - 20, lb - ly - 25, rose3, 1);
      for (var j = 0; j < 6; j++) {
        var px = fx0 + 16 + j * ((fx1 - fx0 - 32) / 5);
        s += K.rect(px - 3.5, ly + 25, 7, lb - ly - 25, rose, 1) + K.rect(px - 5, ly + 25, 10, 3, rose2, 0.7);
      }
      s += K.rect(cx - 9, lb - 34, 18, 34, C.hole, 1.1);
      s += K.rect(fx0, lb, fx1 - fx0, 4, rose2, 1) + K.rect(fx0 + 10, lb + 4, fx1 - fx0 - 20, H - 4 - lb - 4, rose, 0.8);
      return s;
    }
  });

  defs.push({
    id: 'arab-common-landmark-observatory-01', name: '天文台（大六分仪与观星塔）', fp: [5, 4], up: 170, category: 'landmark', culture: 'persian',
    kind: 'observatory', facility: 'academy', tags: ['observatory', 'sextant', 'astrolabe', 'dome', 'library'], roof: 'flat_mud',
    note: '撒马尔罕 / 马拉盖式天文台：大弧形子午仪槽 + 观星穹顶塔 + 学舍，归 academy',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, cx = W / 2, s = '';
      // 后排：圆柱主楼（三层退台）
      var tx0 = cx - 60, tx1 = cx + 60;
      s += Ms.block({ x0: tx0, x1: tx1, yb: gy + 6, yf: gy + 96, h: 110, lip: 3, band: 5, W: W, H: H });
      s += F.arcade(tx0 + 6, tx1 - 6, gy - 30, 18, 6, C.hole, C.lime2) + F.arcade(tx0 + 6, tx1 - 6, gy + 18, 20, 6, C.hole, C.lime2);
      s += P.tileBand(tx0 + 1, tx1 - 1, gy - 6, 4, true);
      // 屋顶：观星穹顶 + 浑仪
      var ty = gy + 6 - 110;
      s += Ms.drum(cx - 22, ty + 18, 18, 10, C.lime) + Ms.dome(cx - 22, ty + 8, 20, 30, C.cobalt2, 'pointed');
      s += K.ln(K.seg(cx - 22, ty - 8, cx - 22, ty - 8), 1, 1);
      var ax = cx + 30, ay = ty + 14, ad = '';
      ad += 'M' + f(ax - 13) + ' ' + f(ay) + 'A13 13 0 1 1 ' + f(ax + 13) + ' ' + f(ay) + 'A13 13 0 1 1 ' + f(ax - 13) + ' ' + f(ay);
      ad += 'M' + f(ax - 13) + ' ' + f(ay) + 'A13 5 0 1 0 ' + f(ax + 13) + ' ' + f(ay);
      ad += 'M' + f(ax) + ' ' + f(ay - 13) + 'A5 13 0 1 0 ' + f(ax) + ' ' + f(ay + 13);
      s += K.ln(ad, 1.6, 1, C.gold) + K.ln(ad, 0.5, 0.6);
      s += K.rect(ax - 3, ay + 13, 6, 6, C.wood, 0.8);
      // 前排：巨型子午仪弧槽（台阶 + 弧形轨道）
      var gx0 = 18, gx1 = W - 18, gyb = gy + 100, yf = H - 6;
      s += Ms.block({ x0: gx0, x1: gx1, yb: gyb, yf: yf, h: 30, lip: 2, wall: C.lime, top: C.lime2, W: W, H: H });
      var ry = yf - 30, rx0 = cx - 70, rx1 = cx + 70;
      s += K.path('M' + f(rx0) + ' ' + f(gyb - 30 + 6) + 'Q' + f(cx) + ' ' + f(ry + 10) + ' ' + f(rx1) + ' ' + f(gyb - 30 + 6) + 'L' + f(rx1 - 12) + ' ' + f(gyb - 30 + 6) + 'Q' + f(cx) + ' ' + f(ry - 4) + ' ' + f(rx0 + 12) + ' ' + f(gyb - 30 + 6) + 'Z', C.adobe2, 1.2);
      var tick = '';
      for (var k = 1; k < 12; k++) {
        var t = k / 12, bx = (1 - t) * (1 - t) * rx0 + 2 * t * (1 - t) * cx + t * t * rx1, by = (1 - t) * (1 - t) * (gyb - 24) + 2 * t * (1 - t) * (ry + 10) + t * t * (gyb - 24);
        tick += K.seg(bx, by, bx, by - 9);
      }
      s += K.ln(tick, 0.9, 0.7);
      // 弧槽两侧台阶 + 日晷盘
      var st = ''; for (var q = 0; q < 6; q++) st += K.seg(rx0 - 4 - q * 3, gyb - 24 + q * 4, rx0 + 4 - q * 3, gyb - 24 + q * 4) + K.seg(rx1 + 4 + q * 3, gyb - 24 + q * 4, rx1 - 4 + q * 3, gyb - 24 + q * 4);
      s += K.ln(st, 0.8, 0.6);
      [gx0 + 22, gx1 - 22].forEach(function (x) {
        s += K.ellipse(x, gyb - 6, 13, 6, C.lime, 1) + K.ln(K.seg(x - 10, gyb - 6, x + 10, gyb - 6) + K.seg(x, gyb - 11, x, gyb - 1), 0.6, 0.6);
        s += K.poly([[x, gyb - 6], [x, gyb - 18], [x + 6, gyb - 6]], C.gold, 0.8);
      });
      s += F.pishtaq(cx - 20, cx + 20, yf, yf - 50, { alt: true });
      s += F.windows(gx0 + 10, cx - 26, yf - 22, 5, 8, 4) + F.windows(cx + 26, gx1 - 10, yf - 22, 5, 8, 4);
      return s;
    }
  });

  if (N) module.exports = defs;
  else root.TownArtAS_defs = (root.TownArtAS_defs || []).concat(defs);
})(this);
