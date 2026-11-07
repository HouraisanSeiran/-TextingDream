/*
 * 织梦 · 东方特殊建筑 · 公共设施：水井、蓄水池、书院、医馆、营房、鼓楼 / 望楼（美术素材，尚未接入游戏）
 * def 格式同 civic.js。
 */
(function (root) {
  'use strict';
  var K = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtEastSpecialCore;
  var C = K.C, TILE = K.TILE, G = K.G, GL = K.GL, f = K.f, P = K.P, R = K.R, E = K.E, L = K.L;
  var SHF = ' fill-opacity="0.2"', BAMBOO = '#d8c27a', WATER = '#4f8a9a';
  var POOL = C.tealLt, POOL_DK = K.mix(C.tealLt, C.teal, 0.55);   // 露天水面（池塘），同 east-ground 水面瓦片
  var defs = [];

  // ====================== 水井 ======================
  /** 井栏：石砌圆井圈。(cx, gy) = 井圈底面中心；r 半径；h 井圈高。 */
  function curb(cx, gy, r, h) {
    var k = 0.45, s = E(cx + r * 0.45, gy + 1, r * 1.1, r * k * 0.8, K.SH, null, 0, SHF);
    s += P('M' + f(cx - r) + ' ' + f(gy - h) + 'V' + f(gy) + 'A' + f(r) + ' ' + f(r * k) + ' 0 0 0 ' + f(cx + r) + ' ' + f(gy) + 'V' + f(gy - h) + 'Z', C.stone, G, 1);
    var d = 'M' + f(cx - r) + ' ' + f(gy - h / 2) + 'A' + f(r) + ' ' + f(r * k) + ' 0 0 0 ' + f(cx + r) + ' ' + f(gy - h / 2);
    for (var i = -2; i <= 2; i++) {
      var x = cx + i * r * 0.4, dy = r * k * Math.sqrt(Math.max(0, 1 - Math.pow((x - cx) / r, 2)));
      d += 'M' + f(x) + ' ' + f(gy - h + dy) + 'V' + f(gy - h / 2 + dy);
      var x2 = x + r * 0.2; if (x2 < cx + r) { var dy2 = r * k * Math.sqrt(Math.max(0, 1 - Math.pow((x2 - cx) / r, 2))); d += 'M' + f(x2) + ' ' + f(gy - h / 2 + dy2) + 'V' + f(gy + dy2); }
    }
    s += L(d, C.stoneDk, 0.6, 0.8);
    s += E(cx, gy - h, r, r * k, C.stoneLt, G, 1) + E(cx, gy - h, r * 0.66, r * k * 0.66, C.dark, G, 0.7) +
      E(cx, gy - h + r * k * 0.18, r * 0.46, r * k * 0.36, WATER) + E(cx - r * 0.12, gy - h + r * k * 0.12, r * 0.18, r * k * 0.1, C.tealLt);
    return s;
  }
  /** 木桶：(x, y) = 桶底中点。 */
  function pail(x, y, r, water) {
    var s = E(x + 1.2, y + 0.4, r * 1.1, r * 0.32, K.SH, null, 0, SHF) +
      P('M' + f(x - r) + ' ' + f(y - r * 1.4) + 'L' + f(x - r * 0.82) + ' ' + f(y) + 'H' + f(x + r * 0.82) + 'L' + f(x + r) + ' ' + f(y - r * 1.4) + 'Z', C.umberLt, G, 0.7) +
      L('M' + f(x - r * 0.95) + ' ' + f(y - r * 1.05) + 'H' + f(x + r * 0.95) + 'M' + f(x - r * 0.86) + ' ' + f(y - r * 0.35) + 'H' + f(x + r * 0.86), C.dark, 0.7) +
      E(x, y - r * 1.4, r, r * 0.32, water ? WATER : C.dark, G, 0.6);
    return s + L('M' + f(x - r) + ' ' + f(y - r * 1.4) + 'Q' + f(x) + ' ' + f(y - r * 2.6) + ' ' + f(x + r) + ' ' + f(y - r * 1.4), C.umber, 0.7);
  }
  /** 辘轳：井圈左右两根木架，横轴上一只缠绳的木辘轳，右侧摇把；绳垂进井口，吊一只小桶。 */
  function windlass(cx, gy, r, h, ph) {
    var top = gy - h - ph, xl = cx - r * 0.8, xr = cx + r * 0.8;
    var posts = 'M' + f(xl) + ' ' + f(gy - h + 1.5) + 'V' + f(top) + 'M' + f(xr) + ' ' + f(gy - h + 1.5) + 'V' + f(top);
    var s = L(posts, G, 3.2) + L(posts, C.umber, 2.1);
    s += L('M' + f(xl - 1) + ' ' + f(top + 2) + 'H' + f(xr + 1), C.umber, 1.6);
    s += R(cx - 4.5, top - 0.6, 9, 5.2, C.umberLt, GL, 0.6) + L('M' + f(cx - 4) + ' ' + f(top + 1) + 'h8M' + f(cx - 4) + ' ' + f(top + 2.6) + 'h8', C.ochreLt, 0.6);
    s += L('M' + f(xr) + ' ' + f(top + 2) + 'h4.5v5.5h2.6', C.dark, 1.2);
    s += L('M' + f(cx + 2) + ' ' + f(top + 4.6) + 'V' + f(gy - h - 1), C.ochreLt, 0.7);
    s += P('M' + f(cx - 0.6) + ' ' + f(gy - h - 4.6) + 'H' + f(cx + 4.6) + 'L' + f(cx + 4) + ' ' + f(gy - h - 0.6) + 'H' + f(cx) + 'Z', C.umberLt, G, 0.5);
    return s;
  }

  defs.push({
    kind: 'well', variant: 1, name: '辘轳井', facility: 'well', category: 'prop', fp: [1, 1], up: 40,
    tags: ['water', 'scatter', 'windlass'], roof: 'none',
    note: '1×1 露天水井：青石井台、石砌圆井圈、木架辘轳（缠绳、摇把、吊桶）；井旁一只盛水木桶。可散放在街口、院中。',
    draw: function (K, W, U, D) {
      var s = '', cx = W / 2, gy = U + 28;
      s += K.pave(4, U + 8, W - 4, U + D - 2, 10, C.stoneLt);
      s += P('M4 ' + f(U + D - 2) + 'H' + f(W - 4) + 'V' + f(U + D) + 'H4Z', C.stone, G, 0.5);
      s += curb(cx, gy, 12, 8) + windlass(cx, gy, 12, 8, 16);
      s += pail(W - 9, U + D - 6, 4, true) + L('M7 ' + f(U + D - 5) + 'q4 -2 8 0', WATER, 1.2, 0.8);
      return s;
    }
  });

  defs.push({
    kind: 'well', variant: 2, name: '井亭', facility: 'well', category: 'special', fp: [2, 2], up: 80,
    tags: ['water', 'pavilion', 'windlass'], roof: 'hip_tile',
    note: '四柱攒尖井亭罩着石井：亭下井圈 + 辘轳，前檐挂小匾；青石井台、排水石槽，井旁木桶两只、洗衣石台，亭后一棵树。攒尖顶在 RoofId 里没有，记最近的 hip_tile。',
    draw: function (K, W, U, D) {
      var s = '', cx = W / 2;
      s += K.shadow(20, 76, U + 24, U + 68, 8);
      s += K.pave(6, U + 12, W - 6, U + D - 2, 11, C.stoneLt);
      s += K.tree(W - 16, U + 34, 10, 17, { col: C.teal });
      s += K.platform(16, 80, U + 20, U + 72, 4);
      var inner = curb(cx, U + 52, 13, 7) + windlass(cx, U + 52, 13, 7, 8);
      s += K.pavilion(22, 74, U + 26, U + 66, 36, { post: C.red, pw: 3, roof: { type: 'spire', tile: TILE.grey, ov: 7, up: 8, hr: 22, finial: 8 } }, inner).svg;
      s += K.plaque(cx, U + 66 - 36 + 7, 20, 6, { chars: 2 });
      // 井台前：排水石槽、木桶、洗衣石台
      s += R(20, U + 80, 56, 4, C.stoneDk, G, 0.6) + L('M22 ' + f(U + 82) + 'H74', WATER, 1.4, 0.9);
      s += pail(14, U + 90, 4.2, true) + pail(84, U + 90, 4.2, false);
      s += K.box(30, 50, U + 88, U + 93, 4, C.stoneLt, C.stone, G, 0.6) + P('M33 ' + f(U + 84) + 'h8v2h-8z', C.tealLt, G, 0.4);
      return s;
    }
  });

  // ====================== 蓄水池 ======================
  /** 荷叶 + 荷花。 */
  function lotusLeaf(x, y, r) {
    return P('M' + f(x) + ' ' + f(y) + 'L' + f(x + r * 0.9) + ' ' + f(y - r * 0.18) + 'A' + f(r) + ' ' + f(r * 0.45) + ' 0 1 1 ' + f(x + r * 0.9) + ' ' + f(y + r * 0.2) + 'Z', C.teal, G, 0.6) +
      L('M' + f(x) + ' ' + f(y) + 'l' + f(-r * 0.6) + ' ' + f(-r * 0.2) + 'M' + f(x) + ' ' + f(y) + 'l' + f(-r * 0.5) + ' ' + f(r * 0.25), C.tealLt, 0.5);
  }
  function lotus(x, y, s) {
    s = s || 1;
    var o = L('M' + f(x) + ' ' + f(y) + 'V' + f(y - 6 * s), C.teal, 0.9);
    [-1, 0, 1].forEach(function (k) {
      o += P('M' + f(x) + ' ' + f(y - 6 * s) + 'Q' + f(x + k * 4 * s - 1.5 * s) + ' ' + f(y - 9 * s) + ' ' + f(x + k * 2.6 * s) + ' ' + f(y - 12 * s + Math.abs(k) * 1.5 * s) +
        'Q' + f(x + k * 4 * s + 1.5 * s) + ' ' + f(y - 9 * s) + ' ' + f(x) + ' ' + f(y - 6 * s) + 'Z', k ? '#e98aa0' : '#f6c2cc', G, 0.5);
    });
    return o;
  }
  /** 水面：深浅两圈叠晕 + 几道水纹。水色 POOL = #6cc1b3（同 east-ground / 东方码头），池壁暗圈 POOL_DK 同 east-ground 岸壁暗色。 */
  function waterSurface(x0, y0, x1, y1, seed) {
    var r = K.rng(seed || 5), s = R(x0, y0, x1 - x0, y1 - y0, POOL_DK) + R(x0 + 3, y0 + 3, x1 - x0 - 6, y1 - y0 - 5, POOL), d = '';
    for (var i = 0; i < 6; i++) {
      var x = x0 + 8 + r() * (x1 - x0 - 22), y = y0 + 6 + r() * (y1 - y0 - 10);
      d += 'M' + f(x) + ' ' + f(y) + 'q3 -1.6 6 0t6 0';
    }
    return s + L(d, C.wallLt, 0.7, 0.75);
  }

  defs.push({
    kind: 'cistern', variant: 1, name: '荷花池', facility: 'cistern', category: 'special', fp: [3, 2], up: 30,
    tags: ['water', 'pond', 'lotus', 'fire_pool'], roof: 'none',
    note: '青石驳岸的方荷塘（兼作防火蓄水池）：水面叠晕、荷叶荷花、红鲤；岸上红栏杆、汲水石阶；角上一座小方亭。蓄水池用途靠石阶与水桶表达。',
    draw: function (K, W, U, D) {
      var s = '', px0 = 10, px1 = W - 10, py0 = U + 18, py1 = U + D - 10;
      s += K.pave(2, U + 4, W - 2, U + D - 1, 12, C.stoneLt);
      // 驳岸：池沿石条顶面 + 内壁（北侧内壁可见）
      s += R(px0 - 5, py0 - 5, px1 - px0 + 10, py1 - py0 + 10, C.stone, G, 1);
      s += R(px0, py0, px1 - px0, py1 - py0, C.stoneDk, G, 0.8);
      s += waterSurface(px0, py0 + 5, px1, py1, 33);
      s += K.bricks(px0, py0, px1, py0 + 5, C.dark, 8, 2.5);
      var rr = K.rng(77);
      for (var i = 0; i < 7; i++) s += lotusLeaf(px0 + 14 + rr() * (px1 - px0 - 40), py0 + 12 + rr() * (py1 - py0 - 20), 5 + rr() * 2);
      s += lotus(px0 + 30, py0 + 22, 1) + lotus(px0 + 70, py0 + 30, 1.1) + lotus(px1 - 30, py0 + 18, 0.9);
      s += P('M' + f(px0 + 50) + ' ' + f(py1 - 12) + 'q4 -3 8 0q-4 3 -8 0zM' + f(px0 + 58) + ' ' + f(py1 - 12) + 'l3 -2v4z', C.orange, G, 0.4);
      // 汲水石阶（前沿正中，伸进池里）
      for (var k = 0; k < 3; k++) s += R(W / 2 - 10 + k, py1 + 3 - k * 3.4, 20 - 2 * k, 3.4, k % 2 ? C.stone : C.stoneLt, G, 0.6);
      // 前沿栏杆（留出石阶口）
      s += K.railing(px0 - 4, W / 2 - 12, py1 + 5, 4, C.red) + K.railing(W / 2 + 12, px1 + 4, py1 + 5, 4, C.red);
      // 左后角小方亭
      s += K.pavilion(4, 28, U - 2, U + 18, 18, { post: C.red, roof: { type: 'spire', tile: TILE.teal, ov: 4, up: 5, hr: 12, finial: 5 } }, '').svg;
      s += pail(W - 12, U + D - 2, 3.6, true);
      return s;
    }
  });

  defs.push({
    kind: 'cistern', variant: 2, name: '石砌蓄水池（太平缸）', facility: 'cistern', category: 'special', fp: [2, 2], up: 40,
    tags: ['water', 'reservoir', 'fire_pool'], roof: 'none',
    note: '条石砌的方形蓄水池：高出地面的石池壁、池里满水，侧壁一只铜龙头出水口，池前四只铜太平缸（防火储水）、两只木桶；池后一个引水竹笕。',
    draw: function (K, W, U, D) {
      var s = '', x0 = 10, x1 = W - 10, yb = U + 6, yf = U + 64, h = 12;
      s += K.shadow(x0, x1, yb, yf, 7);
      s += K.pave(2, U + 2, W - 2, U + D - 1, 12, C.stoneLt);
      // 引水竹笕：从后方伸来的半剖竹槽，架在竹架上
      s += L('M' + f(W - 4) + ' ' + f(U - 30) + 'L' + f(W / 2 + 6) + ' ' + f(yb - h + 2), G, 4) + L('M' + f(W - 4) + ' ' + f(U - 30) + 'L' + f(W / 2 + 6) + ' ' + f(yb - h + 2), BAMBOO, 2.6) +
        L('M' + f(W - 12) + ' ' + f(U - 22) + 'l-3 22M' + f(W - 12) + ' ' + f(U - 22) + 'l3 22', C.umber, 1) + L('M' + f(W / 2 + 6) + ' ' + f(yb - h + 2) + 'v6', WATER, 1.6, 0.9);
      // 池：顶面（池沿 + 水面）+ 正面石壁
      s += R(x0, yb - h, x1 - x0, yf - yb, C.stone, G, 1.1);
      s += waterSurface(x0 + 5, yb - h + 4, x1 - 5, yf - h - 3, 61);
      s += R(x0 + 5, yb - h + 4, x1 - x0 - 10, 3, C.stoneDk);
      s += R(x0, yf - h, x1 - x0, h, C.stoneLt, G, 1.1) + K.bricks(x0, yf - h, x1, yf, C.dark, 12, 4);
      // 铜龙头出水口
      s += E(W / 2, yf - h / 2 - 1, 3.4, 3, C.bronze, GL, 0.7) + K.dots([[W / 2 - 1.2, yf - h / 2 - 2], [W / 2 + 1.2, yf - h / 2 - 2]], C.dark, 0.9) +
        L('M' + f(W / 2) + ' ' + f(yf - h / 2 + 1.6) + 'V' + f(yf + 2), WATER, 1.4, 0.9);
      // 太平缸
      [16, 34, W - 34, W - 16].forEach(function (x, i) {
        var y = U + D - 3;
        s += E(x + 2, y + 0.5, 7, 1.8, K.SH, null, 0, SHF) +
          P('M' + f(x - 6.5) + ' ' + f(y - 10) + 'Q' + f(x - 7.5) + ' ' + f(y - 1) + ' ' + f(x - 3.5) + ' ' + f(y) + 'H' + f(x + 3.5) + 'Q' + f(x + 7.5) + ' ' + f(y - 1) + ' ' + f(x + 6.5) + ' ' + f(y - 10) + 'Z', C.bronze, GL, 0.8) +
          L('M' + f(x - 6.6) + ' ' + f(y - 7.5) + 'H' + f(x + 6.6), GL, 0.6) + E(x - 6.8, y - 6, 1.2, 1.4, null, GL, 0.6) + E(x + 6.8, y - 6, 1.2, 1.4, null, GL, 0.6) +
          E(x, y - 10, 6.5, 2, C.dark, GL, 0.6) + E(x, y - 9.6, 5, 1.3, WATER);
      });
      s += pail(W / 2 - 8, U + D - 3, 3.4, true) + pail(W / 2 + 8, U + D - 3, 3.4, false);
      return s;
    }
  });

  // ====================== 书院 ======================
  /** 一摞线装书。 */
  function books(x, y, n) {
    var s = '', cols = [C.navy, C.teal, C.ochre, C.red];
    for (var i = 0; i < n; i++) s += R(x + (i % 2) * 0.8, y - 2.2 * (i + 1), 10, 2.2, cols[i % 4], GL, 0.4);
    return s;
  }
  /** 碑亭里的石碑（龟趺碑简化为须弥座碑）。(x, y) = 碑座底中点。 */
  function stele(x, y, s) {
    s = s || 1;
    return E(x + 2 * s, y + 0.4, 6 * s, 1.5 * s, K.SH, null, 0, SHF) +
      K.box(x - 5 * s, x + 5 * s, y - 3 * s, y, 3 * s, C.stoneLt, C.stone, G, 0.6) +
      R(x - 3.5 * s, y - 18 * s, 7 * s, 15 * s, C.greyLt, G, 0.8) +
      P('M' + f(x - 4 * s) + ' ' + f(y - 18 * s) + 'Q' + f(x) + ' ' + f(y - 23 * s) + ' ' + f(x + 4 * s) + ' ' + f(y - 18 * s) + 'Z', C.grey, G, 0.7) +
      L('M' + f(x - 1.5 * s) + ' ' + f(y - 15 * s) + 'V' + f(y - 5 * s) + 'M' + f(x + 1.5 * s) + ' ' + f(y - 15 * s) + 'V' + f(y - 6 * s), C.wallLt, 0.6, 0.8);
  }

  defs.push({
    kind: 'academy', variant: 1, name: '书院', facility: 'academy', category: 'special', fp: [3, 3], up: 80,
    tags: ['compound', 'courtyard', 'scholar', 'library'], roof: 'hip_tile',
    note: '书院：后为两层藏书楼（重檐歇山、楼上格扇、正中匾额），院中泮池（半月形水池 + 小石桥）、碑亭石碑、松树；前为白墙门屋，门前两摞书箱。泮池是书院、文庙的标志部件。',
    draw: function (K, W, U, D) {
      var s = '', cx = W / 2;
      s += K.shadow(6, W - 6, U + 6, U + 136, 9);
      s += K.pave(4, U + 6, W - 4, U + 140, 12);
      // 藏书楼
      s += K.platform(16, W - 16, U + 8, U + 62, 5);
      s += K.steps(cx, U + 62, 18, 3);
      s += K.hall(20, W - 20, U + 8, U + 57, { double: true, h1: 22, h2: 18, inset: 6, skirt: 6,
        fac: { bays: 5, doors: [2], col: C.umber, beam: C.navyLt },
        upFac: { bays: 5, doors: [], win: 'lattice', sill: false, col: C.umber, beam: C.navyLt },
        roof: { type: 'hip', tile: TILE.navy, ov: 6, up: 8, hr: 14, ridge: 'chiwen', hipK: 0.5 } }).svg;
      s += K.railing(26, W - 26, U + 57 - 5 - 22 + 1, 3.6, C.umber);
      s += K.plaque(cx, U + 57 - 5 - 22 - 18 + 8, 30, 7.5, { chars: 4, bg: C.navy });
      // 泮池：半月形水池（直边在北），中间一座小拱桥
      var py = U + 82, pr = 30;
      s += P('M' + f(cx - pr - 3) + ' ' + f(py - 2) + 'H' + f(cx + pr + 3) + 'A' + f(pr + 3) + ' ' + f((pr + 3) * 0.42) + ' 0 0 1 ' + f(cx - pr - 3) + ' ' + f(py - 2) + 'Z', C.stone, G, 0.9);
      s += P('M' + f(cx - pr) + ' ' + f(py) + 'H' + f(cx + pr) + 'A' + f(pr) + ' ' + f(pr * 0.42) + ' 0 0 1 ' + f(cx - pr) + ' ' + f(py) + 'Z', POOL, G, 0.7);
      s += L('M' + f(cx - 20) + ' ' + f(py + 5) + 'q3 -1.5 6 0t6 0M' + f(cx + 10) + ' ' + f(py + 7) + 'q3 -1.5 6 0', C.wallLt, 0.7, 0.75);
      s += P('M' + f(cx - 6) + ' ' + f(py - 3) + 'H' + f(cx + 6) + 'V' + f(py + 13) + 'H' + f(cx - 6) + 'Z', C.stoneLt, G, 0.7) +
        K.railing(cx - 6, cx - 6.01, py + 12, 3, C.stoneLt) + L('M' + f(cx - 6) + ' ' + f(py - 3) + 'V' + f(py + 13) + 'M' + f(cx + 6) + ' ' + f(py - 3) + 'V' + f(py + 13), C.stoneDk, 1.2);
      // 碑亭 + 松
      s += K.pavilion(10, 36, U + 76, U + 100, 18, { post: C.red, roof: { type: 'spire', tile: TILE.grey, ov: 4, up: 5, hr: 11, finial: 5 } }, stele(23, U + 99, 0.85)).svg;
      s += K.tree(W - 22, U + 108, 10, 51, { col: C.navyLt, lite: C.teal });
      // 院墙 + 门屋
      s += K.sideWall(6, U + 22, U + 132, 16) + K.sideWall(W - 6, U + 22, U + 132, 16);
      s += K.yardWall(5, 48, U + 134, 16) + K.yardWall(W - 48, W - 5, U + 134, 16);
      s += gateLodge(48, W - 48, U + 114, U + 136, 22);
      s += books(14, U + D - 3, 4) + books(W - 26, U + D - 3, 3);
      return s;
    }
  });
  /** 白墙门屋（书院、医馆用）：一间门，黑漆门、门楣小匾，悬山灰瓦。 */
  function gateLodge(x0, x1, yb, yf, h, o) {
    o = o || {};
    var cx = (x0 + x1) / 2, w = x1 - x0, s = '';
    s += K.platform(x0 - 2, x1 + 2, yb, yf + 2, 2);
    s += R(x0, yf - h, w, h, C.wallLt, G, 1) + R(x0, yf - 3, w, 3, C.stone, G, 0.6);
    var dw = w * 0.4, dh = h * 0.72;
    s += R(cx - dw / 2 - 2, yf - dh - 2, dw + 4, dh + 2, C.stone, G, 0.7) + K.door(cx - dw / 2, yf - dh, dw, dh - 0.5, { col: o.doorCol || C.navy });
    s += R(x0, yf - h, w, 2.6, o.beam || C.navyLt, GL, 0.5);
    s += K.roof(x0, x1, yb, yf, h, { type: 'gable', tile: o.tile || TILE.grey, ov: 4, up: 5, hr: 8, ridge: 'swallow' }).svg;
    s += K.plaque(cx, yf - dh - 5, Math.min(w * 0.5, 22), 6, { chars: 2, bg: o.plaqueBg || C.navy });
    return s;
  }

  // ====================== 医馆 ======================
  /** 药葫芦招幌：“悬壶”——檐下挑出一只大葫芦，系红绸。 */
  function hangGourd(x, y, s) {
    s = s || 1;
    return L('M' + f(x) + ' ' + f(y) + 'v' + f(3 * s), C.dark, 0.7) +
      E(x, y + 6 * s, 3 * s, 3.2 * s, C.ochre, G, 0.8) + E(x, y + 14 * s, 5 * s, 5.4 * s, C.ochre, G, 0.9) +
      E(x - 1.5 * s, y + 13 * s, 1.8 * s, 2.4 * s, C.ochreLt) + L('M' + f(x - 2.6 * s) + ' ' + f(y + 9 * s) + 'H' + f(x + 2.6 * s), C.red, 1.4 * s) +
      L('M' + f(x + 2 * s) + ' ' + f(y + 9 * s) + 'q2 3 0.5 6', C.red, 0.9 * s);
  }
  /** 晒药竹匾：大圆竹匾放在木架上，匾里药材（几种颜色的小点）。 */
  function herbTray(cx, y, r, seed) {
    var rr = K.rng(seed || 9), s = L('M' + f(cx - r * 0.7) + ' ' + f(y) + 'L' + f(cx - r * 0.5) + ' ' + f(y - 6) + 'M' + f(cx + r * 0.7) + ' ' + f(y) + 'L' + f(cx + r * 0.5) + ' ' + f(y - 6), C.umber, 1.1);
    s += E(cx, y - 7, r, r * 0.38, C.ochre, G, 0.8) + E(cx, y - 7.3, r * 0.82, r * 0.3, BAMBOO);
    var pts = [], cols = [C.umber, C.teal, C.red];
    for (var i = 0; i < 14; i++) { var a = rr() * Math.PI * 2, d = Math.sqrt(rr()) * r * 0.7; pts.push([cx + Math.cos(a) * d, y - 7.3 + Math.sin(a) * d * 0.36]); }
    cols.forEach(function (c, k) { s += K.dots(pts.filter(function (p, j) { return j % 3 === k; }), c, 1.6); });
    return s;
  }

  /** 药柜：一排百子柜小抽屉。 */
  function medCabinet(x, y, w, h) {
    var s = R(x, y - h, w, h, C.umber, GL, 0.6), d = '', cw = w / 5, ch = h / 4;
    for (var i = 1; i < 5; i++) d += 'M' + f(x + cw * i) + ' ' + f(y - h) + 'V' + f(y);
    for (var j = 1; j < 4; j++) d += 'M' + f(x) + ' ' + f(y - ch * j) + 'H' + f(x + w);
    var knobs = [];
    for (var a = 0; a < 5; a++) for (var b = 0; b < 4; b++) knobs.push([x + cw * (a + 0.5), y - ch * (b + 0.5)]);
    return s + L(d, C.ochre, 0.5, 0.8) + K.dots(knobs, C.ochreLt, 0.9);
  }

  defs.push({
    kind: 'infirmary', variant: 1, name: '医馆（药铺）', facility: 'infirmary', category: 'special', fp: [3, 2], up: 72,
    tags: ['shop', 'medicine', 'gourd_sign'], roof: 'gable_tile',
    note: '临街药铺医馆：三间铺面，中间敞门露出百子药柜与柜台，左右格扇；檐下挑一只大药葫芦（悬壶济世），门侧竖幌；门前木架竹匾晒药材、药碾子、煎药小炉冒热气。',
    draw: function (K, W, U, D) {
      var s = '', x0 = 10, x1 = W - 10, yb = U + 10, yf = U + 64, h = 30;
      s += K.shadow(x0, x1, yb, yf, 9);
      s += K.pave(2, yf - 2, W - 2, U + D - 1, 12);
      s += K.facade(x0, x1, yf, h, { bays: 3, doors: [1], open: true, col: C.umber, beam: C.teal, doorW: 36, doorH: 24, win: 'lattice' });
      var cx = W / 2;
      s += medCabinet(cx - 15, yf - 7, 30, 15) + K.box(cx - 13, cx + 13, yf - 6, yf - 3.5, 5, C.umberLt, C.umber, GL, 0.5);
      s += K.roof(x0, x1, yb, yf, h, { type: 'gable', tile: TILE.grey, ov: 5, up: 5, hr: 12, ridge: 'swallow' }).svg;
      s += K.plaque(cx, yf - h + 8.5, 34, 8, { chars: 3, bg: C.umber });
      s += L('M' + f(x0 + 10) + ' ' + f(yf - h + 2) + 'h-10', C.umber, 1.4) + hangGourd(x0 + 1, yf - h + 2, 1);
      s += K.banner(x1 - 6, yf - h + 4, 7, 20, { col: C.wallLt, mark: true, ink: C.red });
      // 门前：晒药竹匾、药碾子、煎药炉
      var gy = U + D - 3;
      s += herbTray(22, gy, 11, 13) + herbTray(48, gy - 1, 10, 17);
      s += P('M' + f(76) + ' ' + f(gy) + 'L' + f(78) + ' ' + f(gy - 4) + 'H' + f(96) + 'L' + f(98) + ' ' + f(gy) + 'Z', C.stone, G, 0.7) +
        E(87, gy - 5.5, 4, 3, C.grey, G, 0.7) + L('M79 ' + f(gy - 5.5) + 'H95', C.umber, 1.2);
      s += K.box(108, 120, gy - 3, gy, 6, C.brick, C.umberLt, G, 0.6) + K.fire(114, gy - 1, 2) + K.jar(114, gy - 8.5, 3.6, C.umber) + K.smoke(114, gy - 18, 4.5, 61);
      s += K.jar(W - 10, gy, 4.4, C.ochre);
      return s;
    }
  });

  // ====================== 营房 ======================
  /** 兵器架（刀枪戟）。(x0..x1, y) = 架脚。 */
  function weaponRack(x0, x1, y, h) {
    var s = L('M' + f(x0) + ' ' + f(y) + 'V' + f(y - h) + 'M' + f(x1) + ' ' + f(y) + 'V' + f(y - h), C.umber, 1.6) +
      L('M' + f(x0 - 1) + ' ' + f(y - h + 2) + 'H' + f(x1 + 1) + 'M' + f(x0 - 1) + ' ' + f(y - 4) + 'H' + f(x1 + 1), C.umber, 1.3), n = Math.floor((x1 - x0) / 5);
    for (var i = 1; i < n; i++) {
      var x = x0 + (x1 - x0) * i / n, t = y - h - 4;
      s += L('M' + f(x) + ' ' + f(y - 1) + 'V' + f(t + 3), C.umberLt, 0.9);
      if (i % 2) s += P('M' + f(x - 1.4) + ' ' + f(t + 4) + 'L' + f(x) + ' ' + f(t - 1) + 'L' + f(x + 1.4) + ' ' + f(t + 4) + 'Z', C.greyLt, GL, 0.4) + L('M' + f(x - 1.6) + ' ' + f(t + 5) + 'h3.2', C.red, 1.2);
      else s += P('M' + f(x) + ' ' + f(t + 3) + 'Q' + f(x + 3.4) + ' ' + f(t + 1) + ' ' + f(x + 2) + ' ' + f(t - 2) + 'L' + f(x) + ' ' + f(t + 0.5) + 'Z', C.greyLt, GL, 0.4);
    }
    return s;
  }
  /** 帅旗：三角牙旗，旗心一个圆。 */
  function warFlag(x, yBase, top, col) {
    var s = L('M' + f(x) + ' ' + f(yBase) + 'V' + f(top), G, 2.8) + L('M' + f(x) + ' ' + f(yBase) + 'V' + f(top), C.umber, 1.8) +
      P('M' + f(x - 2) + ' ' + f(top - 2) + 'L' + f(x) + ' ' + f(top - 6) + 'L' + f(x + 2) + ' ' + f(top - 2) + 'Z', C.greyLt, GL, 0.4) +
      R(x - 3, yBase - 3, 6, 3, C.stone, G, 0.5);
    var d = 'M' + f(x + 1) + ' ' + f(top) + 'L' + f(x + 20) + ' ' + f(top + 3) + 'L' + f(x + 15) + ' ' + f(top + 7) + 'L' + f(x + 20) + ' ' + f(top + 11) + 'L' + f(x + 1) + ' ' + f(top + 15) + 'Z';
    s += P(d, col || C.red, GL, 0.8) + L('M' + f(x + 1) + ' ' + f(top + 1) + 'V' + f(top + 15), C.ochre, 1.4);
    return s + E(x + 9, top + 7.5, 3, 3, C.ochreLt, GL, 0.5);
  }
  /** 箭靶：草靶架。 */
  function target(x, y) {
    return L('M' + f(x - 4) + ' ' + f(y) + 'L' + f(x - 1) + ' ' + f(y - 12) + 'M' + f(x + 4) + ' ' + f(y) + 'L' + f(x + 1) + ' ' + f(y - 12) + 'M' + f(x) + ' ' + f(y - 6) + 'L' + f(x + 2) + ' ' + f(y), C.umber, 1) +
      E(x, y - 14, 6, 6, TILE.thatch.fill, G, 0.8) + E(x, y - 14, 4, 4, C.wallLt) + E(x, y - 14, 2.2, 2.2, C.red) + L('M' + f(x + 1) + ' ' + f(y - 14.5) + 'l6 -3', C.umber, 0.7);
  }

  defs.push({
    kind: 'barracks', variant: 1, name: '营房（兵营）', facility: 'barracks', category: 'special', fp: [4, 3], up: 72,
    tags: ['compound', 'military', 'drill_yard'], roof: 'gable_tile',
    note: '营房：后排一长溜七间硬山营房（灰瓦、直棂窗、多门）；前为夯土校场，左右兵器架、箭靶，中间点将台插红牙旗；前沿木栅栏 + 辕门（两柱横梁挂牌）。',
    draw: function (K, W, U, D) {
      var s = '', x0 = 10, x1 = W - 10, yb = U + 8, yf = U + 52, h = 24;
      s += K.shadow(x0, x1, yb, yf, 8);
      s += R(4, yf - 2, W - 8, U + D - yf, '#cdb784', G, 0.6);
      s += L('M14 ' + f(yf + 16) + 'h20M60 ' + f(yf + 34) + 'h24M130 ' + f(yf + 22) + 'h30', '#b39c6a', 0.8, 0.8);
      s += K.facade(x0, x1, yf, h, { bays: 7, doors: [1, 3, 5], col: C.umber, beam: C.navyLt, win: 'straight', doorCol: C.umber });
      s += K.roof(x0, x1, yb, yf, h, { type: 'gable', tile: TILE.grey, ov: 5, up: 4, hr: 12, ridge: 'plain' }).svg;
      s += K.plaque(W / 2, yf - h + 7.5, 26, 7, { chars: 2, bg: C.red });
      // 点将台
      var cx = W / 2, ty = U + 106;
      s += K.platform(cx - 18, cx + 18, ty - 14, ty, 7) + K.steps(cx, ty, 10, 2, 2) + warFlag(cx - 12, ty - 9, ty - 52, C.red);
      s += K.box(cx - 3, cx + 9, ty - 13, ty - 9, 5, C.umberLt, C.umber, GL, 0.5);
      // 兵器架、箭靶
      s += weaponRack(16, 46, U + 98, 16) + weaponRack(W - 46, W - 16, U + 98, 16);
      s += target(30, U + 128) + target(W - 30, U + 128);
      // 木栅栏 + 辕门
      var fy = U + D - 2, fence = '';
      for (var x = 6; x < W - 4; x += 4.5) if (Math.abs(x - cx) > 15) fence += 'M' + f(x) + ' ' + f(fy) + 'V' + f(fy - 11);
      s += L(fence, G, 2.6) + L(fence, C.umberLt, 1.6) + L('M6 ' + f(fy - 8) + 'H' + f(cx - 15) + 'M' + f(cx + 15) + ' ' + f(fy - 8) + 'H' + f(W - 6), C.umber, 1.2);
      s += L('M' + f(cx - 14) + ' ' + f(fy) + 'V' + f(fy - 34) + 'M' + f(cx + 14) + ' ' + f(fy) + 'V' + f(fy - 34), G, 3.6) + L('M' + f(cx - 14) + ' ' + f(fy) + 'V' + f(fy - 34) + 'M' + f(cx + 14) + ' ' + f(fy) + 'V' + f(fy - 34), C.red, 2.4);
      s += R(cx - 18, fy - 36, 36, 3, C.umber, GL, 0.6) + K.plaque(cx, fy - 29, 16, 6, { chars: 2, bg: C.navy });
      return s;
    }
  });

  // ====================== 鼓楼 / 望楼 ======================
  defs.push({
    kind: 'watchtower', variant: 1, name: '鼓楼', facility: 'watchtower', category: 'special', fp: [2, 2], up: 128,
    tags: ['landmark', 'drum_tower', 'time_keeping'], roof: 'hip_tile',
    note: '城中报时与警讯的鼓楼：青砖墩台开券洞、台上两层重檐楼阁，二层敞开悬一面大鼓（鼓面朝前）、四周平座栏杆。facility 记 watchtower（东方城镇以钟鼓楼报时、示警，兼瞭望）；钟楼可换鼓为钟。',
    draw: function (K, W, U, D) {
      var s = '', x0 = 8, x1 = W - 8, yb = U + 18, yf = U + 88, hb = 34, cx = W / 2;
      s += K.shadow(x0, x1, yb, yf, 9);
      s += K.pave(2, U + 10, W - 2, U + D - 1, 12);
      s += K.box(x0, x1, yb, yf, hb, C.stoneLt, C.stone, G, 1.1) + K.bricks(x0, yf - hb, x1, yf, C.dark, 7, 3.6);
      var aw = 20, ah = 24, ad = 'M' + f(cx - aw / 2) + ' ' + f(yf) + 'V' + f(yf - ah + aw / 2) + 'A' + f(aw / 2) + ' ' + f(aw / 2) + ' 0 0 1 ' + f(cx + aw / 2) + ' ' + f(yf - ah + aw / 2) + 'V' + f(yf) + 'Z';
      s += P(ad, C.dark, C.stoneLt, 3) + L(ad, G, 0.8);
      var tf = yf - hb, tb = yb - hb;
      // 一层：敞间，正中挂大鼓
      var x2 = x0 + 6, x3 = x1 - 6, h1 = 26;
      s += R(x2, tf - h1, x3 - x2, h1, '#6a3d27', G, 1);
      var dy = tf - h1 * 0.5;
      s += L('M' + f(cx - 11) + ' ' + f(tf - 1) + 'L' + f(cx - 7) + ' ' + f(dy + 4) + 'M' + f(cx + 11) + ' ' + f(tf - 1) + 'L' + f(cx + 7) + ' ' + f(dy + 4), C.umber, 1.6);
      s += E(cx + 2, dy, 9.5, 9.5, C.red, GL, 0.8) + E(cx, dy, 9.5, 9.5, C.ochre, G, 1) + E(cx, dy, 6.6, 6.6, C.ochreLt) + E(cx, dy, 3.5, 3.5, C.wallLt);
      var st = [];
      for (var i = 0; i < 14; i++) { var a = i / 14 * Math.PI * 2; st.push([cx + Math.cos(a) * 8.3, dy + Math.sin(a) * 8.3]); }
      s += K.dots(st, C.umber, 1);
      [x2, (x2 + cx) / 2 - 6, (x3 + cx) / 2 + 6, x3].forEach(function (px) { s += R(px - 1.5, tf - h1, 3, h1, C.red, GL, 0.6); });
      s += R(x2, tf - h1, x3 - x2, 3, C.teal, GL, 0.6);
      s += K.railing(x2 - 3, x3 + 3, tf, 4, C.red);
      // 腰檐 + 二层 + 顶
      var h2 = 16;
      s += K.facade(x2 + 5, x3 - 5, tf - 5 - h1, h2 + 2, { bays: 3, doors: [], win: 'lattice', sill: false, col: C.red, beam: C.teal });
      s += K.roof(x2, x3, tf - 14 + 12, tf, h1, { type: 'hip', tile: TILE.grey, ov: 6, up: 6, hr: 6, inset: 7, noBack: true }).svg;
      s += K.plaque(cx, tf - 5 - h1 - h2 + 7, 18, 6, { chars: 2, bg: C.navy });
      s += K.roof(x2 + 5, x3 - 5, tb + 6, tf - 5, h1 + h2, { type: 'hip', tile: TILE.grey, ov: 6, up: 8, hr: 13, ridge: 'chiwen', hipK: 0.55 }).svg;
      s += K.lantern(x2 - 1, tf - h1 + 2, 2.4) + K.lantern(x3 + 1, tf - h1 + 2, 2.4);
      return s;
    }
  });

  defs.push({
    kind: 'watchtower', variant: 2, name: '木望楼（更楼）', facility: 'watchtower', category: 'special', fp: [2, 2], up: 136,
    tags: ['lookout', 'timber', 'gong'], roof: 'hip_tile',
    note: '四柱木构望楼：四根高柱斜撑、中间剪刀撑，柱间一架木梯直上；顶上瞭望台围栏、挂铜锣和灯笼，攒尖小顶；脚下一圈石础、一只水缸。用于街坊巡更、火警瞭望。',
    draw: function (K, W, U, D) {
      var s = '', cx = W / 2, gy = U + 82, ty = U - 4;
      s += K.pave(2, U + 30, W - 2, U + D - 1, 12);
      s += E(cx + 14, gy + 2, 30, 6, K.SH, null, 0, SHF);
      var bl = 18, br = W - 18, tl = 26, tr = W - 26, back = 'M' + f(tl + 6) + ' ' + f(ty) + 'L' + f(bl + 10) + ' ' + f(gy - 26) + 'M' + f(tr - 6) + ' ' + f(ty) + 'L' + f(br - 10) + ' ' + f(gy - 26);
      s += L(back, G, 3) + L(back, C.umber, 2);
      var cross = 'M' + f(bl + 3) + ' ' + f(gy - 6) + 'L' + f(tr - 2) + ' ' + f(ty + 30) + 'M' + f(br - 3) + ' ' + f(gy - 6) + 'L' + f(tl + 2) + ' ' + f(ty + 30) +
        'M' + f(tl + 1) + ' ' + f(ty + 28) + 'L' + f(tr - 1) + ' ' + f(ty + 28) + 'M' + f(bl + 4) + ' ' + f(gy - 30) + 'H' + f(br - 4);
      s += L(cross, C.umber, 1.4);
      // 梯子
      var rung = '';
      for (var y = gy - 4; y > ty + 6; y -= 5) rung += 'M' + f(cx - 4) + ' ' + f(y) + 'h8';
      s += L('M' + f(cx - 5) + ' ' + f(gy) + 'L' + f(cx - 4) + ' ' + f(ty + 4) + 'M' + f(cx + 5) + ' ' + f(gy) + 'L' + f(cx + 4) + ' ' + f(ty + 4) + rung, C.umberLt, 1.1);
      var legs = 'M' + f(bl) + ' ' + f(gy) + 'L' + f(tl) + ' ' + f(ty) + 'M' + f(br) + ' ' + f(gy) + 'L' + f(tr) + ' ' + f(ty);
      s += L(legs, G, 4) + L(legs, C.red, 2.8);
      s += E(bl, gy, 4, 1.8, C.stone, G, 0.6) + E(br, gy, 4, 1.8, C.stone, G, 0.6);
      // 瞭望台
      s += K.box(tl - 6, tr + 6, ty - 14, ty, 4, C.umberLt, C.umber, GL, 0.8);
      s += K.railing(tl - 5, tr + 5, ty - 4, 7, C.red);
      // 铜锣
      s += L('M' + f(tr + 3) + ' ' + f(ty - 14) + 'v-4h6', C.umber, 1) + E(tr + 9, ty - 11, 4, 4, C.bronze, GL, 0.8) + E(tr + 9, ty - 11, 1.6, 1.6, C.ochreLt);
      var rf = K.pavilion(tl - 2, tr + 2, ty - 18, ty - 4, 16, { post: C.red, pw: 2.2, roof: { type: 'spire', tile: TILE.grey, ov: 5, up: 6, hr: 15, finial: 7 } }, '');
      s += rf.svg + K.lantern(tl - 1, ty - 19, 2.4);
      s += K.jar(W - 10, U + D - 3, 5, C.umberLt);
      return s;
    }
  });

  // —— 导出 ——
  var API = { defs: defs, curb: curb, pail: pail, windlass: windlass, gateLodge: gateLodge, hangGourd: hangGourd, warFlag: warFlag };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.TownArtEastSpecialService = API;
})(typeof window !== 'undefined' ? window : this);
