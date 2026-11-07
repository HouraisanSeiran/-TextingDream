/*
 * 织梦 · 东方文化地标（east-landmark）· 礼制与城市：文庙、名楼、王府大殿（美术素材，尚未接入游戏）
 * def 格式同 lm-taoist.js。浏览器挂 window.TownArtEastLandmarkCivic；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var node = typeof module !== 'undefined' && module.exports;
  var K = node ? require('./lm-core.js') : root.TownArtEastLandmarkCore;
  var PT = node ? require('./lm-parts.js') : root.TownArtEastLandmarkParts;
  var X = node ? require('./lm-extra.js') : root.TownArtEastLandmarkExtra;
  var C = K.C, TILE = K.TILE, G = K.G, GL = K.GL, f = K.f, P = K.P, R = K.R, E = K.E, L = K.L;
  var defs = [];

  /** 红墙（宫墙 / 庙墙）：朱红墙身 + 黄琉璃墙帽。 */
  function redWall(x0, x1, y, h) { return K.yardWall(x0, x1, y, h, { col: C.red, tile: TILE.gold, t: 3.4 }); }
  function redSide(x, y0, y1, h) { return K.sideWall(x, y0, y1, h, { col: C.red, tile: TILE.gold }); }

  /** 棂星门：石柱冲天、柱顶云冠，柱间额枋 + 朱红棂格门扇。xs = 柱 x 列表，y = 地面，h = 柱高。 */
  function lingxing(xs, y, h) {
    var s = P(K.pts([[xs[0] - 6, y - 2], [xs[xs.length - 1] + 6, y - 2], [xs[xs.length - 1] + 10, y + 3], [xs[0] - 2, y + 3]]), K.SH, null, 0, ' fill-opacity="0.2"');
    for (var i = 0; i < xs.length - 1; i++) {
      var a = xs[i] + 3, b = xs[i + 1] - 3, mid = i === Math.floor((xs.length - 1) / 2);
      var top = y - h * (mid ? 0.72 : 0.62);
      s += R(a, top, b - a, 3, X.MARB, G, 0.6) + R(a, top + 4.5, b - a, 2.4, C.teal, GL, 0.4);
      s += K.lattice(a + 1, top + 8, b - a - 2, y - top - 10, { bg: C.red, fg: C.ochreLt, step: 3 });
      s += L('M' + f((a + b) / 2) + ' ' + f(top + 8) + 'V' + f(y - 2), GL, 0.7);
      s += R(a, y - 2.4, b - a, 2.4, C.stone, G, 0.5);
    }
    xs.forEach(function (x) {
      s += R(x - 2.8, y - h, 5.6, h, X.MARB, G, 0.8) + R(x + 0.8, y - h, 2, h, X.MARB2);
      // 云冠：一朵小如意云压柱顶
      s += P('M' + f(x - 5) + ' ' + f(y - h) + 'Q' + f(x - 6) + ' ' + f(y - h - 5) + ' ' + f(x - 2) + ' ' + f(y - h - 5) + 'Q' + f(x) + ' ' + f(y - h - 9) + ' ' + f(x + 2.5) + ' ' + f(y - h - 5) +
        'Q' + f(x + 6) + ' ' + f(y - h - 5) + ' ' + f(x + 5) + ' ' + f(y - h) + 'Z', X.MARB, G, 0.7);
      s += E(x, y - h - 9.5, 1.6, 1.8, C.ochre, G, 0.5);
      s += PT.guShi(x, y + 1, 0.55);
    });
    return s;
  }
  /** 泮池：北边平直、南边半圆的石岸水池，中间一座拱桥（状元桥）。 */
  function panchi(cx, yN, rx, ry) {
    var d = 'M' + f(cx - rx) + ' ' + f(yN) + 'H' + f(cx + rx) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 1 ' + f(cx - rx) + ' ' + f(yN) + 'Z';
    var d2 = 'M' + f(cx - rx + 3) + ' ' + f(yN + 1.5) + 'H' + f(cx + rx - 3) + 'A' + f(rx - 3) + ' ' + f(ry - 3) + ' 0 0 1 ' + f(cx - rx + 3) + ' ' + f(yN + 1.5) + 'Z';
    var s = P(d, C.stone, G, 1) + P(d2, X.WATER, G, 0.6) + R(cx - rx + 3, yN + 1.5, 2 * rx - 6, 2.2, '#30697f');
    s += L('M' + f(cx - rx * 0.6) + ' ' + f(yN + ry * 0.45) + 'q3 -1.4 6 0t6 0M' + f(cx + rx * 0.3) + ' ' + f(yN + ry * 0.3) + 'q3 -1.4 6 0t6 0', C.tealLt, 0.7, 0.85);
    // 池岸石栏（只画南侧弧上一串望柱）
    var dots = [];
    for (var i = 0; i <= 14; i++) { var a = Math.PI * i / 14; dots.push([cx + Math.cos(a) * rx, yN + Math.sin(a) * ry - 2]); }
    s += K.dots(dots, G, 3) + K.dots(dots, X.MARB, 1.8);
    s += X.archBridge(cx, yN + ry * 0.62, 18, { h: 5 });
    return s;
  }

  defs.push({
    kind: 'confucian_temple', variant: 1, name: '文庙（孔庙）', facility: 'academy', culture: 'confucian', category: 'landmark',
    fp: [5, 6], up: 24, tags: ['compound', 'courtyard', 'axial', 'multi_court', 'stele_pavilion', 'pond', 'cypress'], roof: 'hip_tile',
    note: '中轴礼制建筑群：万仞宫墙（红墙黄瓦照壁）→ 汉白玉棂星门（冲天柱、云冠、朱红棂格）→ 半月泮池与状元桥 → 大成门（单檐歇山）→ ' +
      '左右黄琉璃碑亭（亭中驮碑赑屃）→ 汉白玉月台上的重檐歇山黄琉璃大成殿（九开间、斗拱、竖匾、御路）。院中古柏成行。书院 / 学宫通用。',
    draw: function (K, W, U, D) {
      var s = '', cx = W / 2, B = U + D;
      s += K.shadow(6, W - 6, U + 10, B - 3, 10);
      s += K.pave(4, U + 10, W - 4, B - 2, 12);
      s += K.pave(cx - 9, U + 120, cx + 9, B - 30, 10, C.stoneLt);
      s += redWall(6, W - 6, U + 14, 18);
      s += redSide(6, U + 14, B - 4, 18) + redSide(W - 6, U + 14, B - 4, 18);
      s += X.cypress(22, U + 70, 1.1) + X.cypress(W - 22, U + 70, 1.1);
      // 大成殿：月台 + 重檐歇山黄琉璃
      var tp = 12, tf = U + 112;
      s += X.terrace(28, W - 28, U + 40, tf, tp, { gap: [cx - 14, cx + 14] });
      var hl = X.grandHall(44, W - 44, U + 44, tf - tp - 8, { double: true, h1: 28, h2: 18, inset: 13, skirt: 7, dg: 5,
        fac: { bays: 9, doors: [3, 4, 5], col: C.red, beam: C.teal, doorCol: C.red },
        roof: { type: 'hip', tile: TILE.gold, ov: 8, up: 11, hr: 17, ridge: 'chiwen', hipK: 0.55, ridgeH: 3.5 } });
      s += hl.svg;
      // 竖匾（大成殿）
      var py = hl.top + 4;
      s += R(cx - 5.5, py, 11, 15, GL) + R(cx - 4.5, py + 1, 9, 13, C.navy, G, 0.5) + L('M' + f(cx - 2) + ' ' + f(py + 4) + 'h4M' + f(cx - 2) + ' ' + f(py + 7.5) + 'h4M' + f(cx - 2) + ' ' + f(py + 11) + 'h4', GL, 0.8);
      s += X.stair(cx, tf - tp, tf + 4, 22, { yulu: true });
      s += PT.censer(cx, tf + 20, 0.85, 81);
      // 碑亭（左右）
      s += X.stelePavilion(16, 50, U + 136, U + 160, { h: 22 }) + X.stelePavilion(W - 50, W - 16, U + 136, U + 160, { h: 22 });
      s += X.cypress(64, U + 166, 0.9) + X.cypress(W - 64, U + 166, 0.9);
      // 大成门
      var gb = U + 172, gf = U + 196;
      s += K.platform(64, W - 64, gb, gf + 4, 5) + K.steps(cx, gf + 4, 18, 2);
      s += X.grandHall(70, W - 70, gb - 5, gf - 5, { h: 20, dg: 4, fac: { bays: 5, doors: [1, 2, 3], col: C.red, beam: C.teal },
        roof: { type: 'hip', tile: TILE.gold, ov: 6, up: 9, hr: 12, ridge: 'chiwen', hipK: 0.55 } }).svg;
      s += K.plaque(cx, gf - 5 - 20 + 6, 20, 6, { chars: 3, bg: C.navy });
      // 泮池 + 状元桥
      s += panchi(cx, U + 212, 52, 20);
      s += X.cypress(22, U + 230, 0.9) + X.cypress(W - 22, U + 230, 0.9);
      // 棂星门
      s += lingxing([cx - 54, cx - 20, cx + 20, cx + 54], B - 12, 38);
      return s;
    }
  });

  /** 砖城台：青砖台体 + 中间券洞 + 顶面垛墙（名楼、城楼用）。返回 svg。 */
  function brickPodium(x0, x1, yb, yf, h, o) {
    o = o || {};
    var cx = (x0 + x1) / 2, s = K.box(x0, x1, yb, yf, h, C.stoneLt, C.greyLt, G, 1.1);
    s += K.bricks(x0, yf - h, x1, yf, '#3d454e', 8, 3.6);
    s += R(x0, yf - h, x1 - x0, 3, C.stone, G, 0.6) + R(x0, yf - 4, x1 - x0, 4, C.stone, G, 0.6);
    if (o.arch !== false) {
      var aw = o.aw || 16, ah = h * 0.66;
      var d = 'M' + f(cx - aw / 2) + ' ' + f(yf) + 'V' + f(yf - ah + aw / 2) + 'A' + f(aw / 2) + ' ' + f(aw / 2) + ' 0 0 1 ' + f(cx + aw / 2) + ' ' + f(yf - ah + aw / 2) + 'V' + f(yf) + 'Z';
      s += P(d, C.dark, C.stoneLt, 3) + L(d, G, 0.7);
      s += K.plaque(cx, yf - ah - 5, aw + 6, 6, { chars: 2, bg: C.stoneLt, ink: C.dark });
    }
    // 顶面女墙：一道矮墙 + 垛口
    var top = yf - h, d2 = '';
    s += R(x0, top - 4, x1 - x0, 4, C.grey, G, 0.7);
    for (var x = x0 + 2; x < x1 - 4; x += 8) d2 += 'M' + f(x) + ' ' + f(top - 4) + 'h4v-2.4h-4Z';
    s += P(d2, C.grey, G, 0.6);
    return s;
  }

  defs.push({
    kind: 'famous_tower', variant: 1, name: '名楼（临江高阁）', facility: 'watchtower', culture: 'chinese_classical', category: 'landmark',
    fp: [4, 4], up: 84, tags: ['tower', 'multi_storey', 'balcony', 'scenic', 'riverside', 'brick_podium'], roof: 'hip_tile',
    note: '黄鹤楼、滕王阁气质的名楼：青砖高城台（券门、门额、垛墙）→ 汉白玉须弥座 → 四层楼阁，每层平座回廊与斗拱、层层出檐（明三暗五的重檐）、' +
      '八角折面；第二层挂横匾；顶层重檐歇山黄琉璃配宝珠。楼前一对石狮、两旁灯笼柱。FacilityKind 无"名楼"，按登高望远归 watchtower；' +
      '实际游戏中更像文化景观，接入时可只作地标不承担军事瞭望。',
    draw: function (K, W, U, D) {
      var s = '', cx = W / 2, B = U + D;
      s += K.shadow(14, W - 14, U + 30, B - 4, 10);
      s += K.pave(4, U + 26, W - 4, B - 2, 12);
      // 城台
      var pf = B - 14;
      s += brickPodium(18, W - 18, U + 40, pf, 46, { aw: 20 });
      s += K.steps(cx, pf, 28, 5, 2.4);
      // 城台上：须弥座 + 楼阁
      var tf = pf - 46 - 4;
      s += X.terrace(36, W - 36, tf - 34, tf, 7, { gap: [cx - 9, cx + 9] });
      var tw = X.tower(cx, tf - 9, 24, [
        { w: 114, h: 30, bays: 5, doors: [1, 2, 3], oct: 0.12, dg: 4.5, ov: 9, up: 11, hr: 6, tile: TILE.gold, ridgeW: 20 },
        { w: 104, h: 26, bays: 5, doors: [], oct: 0.12, balcony: true, dg: 4.5, ov: 9, up: 11, hr: 6, tile: TILE.gold, ridgeW: 18, plaque: 4 },
        { w: 94, h: 24, bays: 5, doors: [], oct: 0.12, balcony: true, dg: 4, ov: 9, up: 11, hr: 6, tile: TILE.gold, ridgeW: 16 },
        { w: 84, h: 22, bays: 5, doors: [], oct: 0.12, balcony: true, dg: 4, ov: 8, up: 10, hr: 6, tile: TILE.gold, ridgeW: 14 },
        { w: 70, h: 22, bays: 3, doors: [], oct: 0.14, balcony: true, dg: 4, ov: 10, up: 13, hr: 22, tile: TILE.gold, roof: 'hip', pearl: true }
      ]);
      s += tw.svg;
      // 两旁灯笼柱 + 楼前石狮
      [26, W - 26].forEach(function (x) {
        s += L('M' + f(x) + ' ' + f(B - 4) + 'V' + f(B - 40), G, 3) + L('M' + f(x) + ' ' + f(B - 4) + 'V' + f(B - 40), C.red, 1.8) +
          L('M' + f(x - 5) + ' ' + f(B - 38) + 'H' + f(x + 5), C.umber, 1.4) + K.lantern(x - 4, B - 38, 2.6) + K.lantern(x + 4, B - 38, 2.6);
      });
      s += X.lion(cx - 22, B - 2, 0.85, 1) + X.lion(cx + 22, B - 2, 0.85, -1);
      return s;
    }
  });

  /** 铜鹤 / 铜龟：殿前陈设，(x, y) 着地点。 */
  function bronzeCrane(x, y, s) {
    s = s || 1;
    var o = E(x + 2 * s, y + 0.3, 5 * s, 1.4 * s, K.SH, null, 0, ' fill-opacity="0.2"') + R(x - 3 * s, y - 3 * s, 6 * s, 3 * s, C.stone, G, 0.5);
    o += P('M' + f(x - 3.5 * s) + ' ' + f(y - 9 * s) + 'Q' + f(x) + ' ' + f(y - 13 * s) + ' ' + f(x + 3.5 * s) + ' ' + f(y - 9 * s) + 'Q' + f(x) + ' ' + f(y - 5 * s) + ' ' + f(x - 3.5 * s) + ' ' + f(y - 9 * s) + 'Z', C.bronze, GL, 0.6);
    o += L('M' + f(x - 1 * s) + ' ' + f(y - 6 * s) + 'V' + f(y - 3 * s) + 'M' + f(x + 1 * s) + ' ' + f(y - 6 * s) + 'V' + f(y - 3 * s), C.bronze, 0.8);
    var nk = 'M' + f(x + 1.5 * s) + ' ' + f(y - 11 * s) + 'Q' + f(x + 2 * s) + ' ' + f(y - 18 * s) + ' ' + f(x + 0.5 * s) + ' ' + f(y - 20 * s);
    o += L(nk, GL, 1.8 * s) + L(nk, C.bronze, 1.1 * s) + L('M' + f(x + 0.5 * s) + ' ' + f(y - 20 * s) + 'l' + f(-2.6 * s) + ' ' + f(0.6 * s), C.bronze, 0.9);
    return o;
  }
  /** 日晷：斜置石盘 + 晷针，放在石座上。 */
  function sundial(x, y, s) {
    s = s || 1;
    return R(x - 2.6 * s, y - 7 * s, 5.2 * s, 7 * s, X.MARB, G, 0.5) + E(x, y - 10 * s, 4.6 * s, 3.6 * s, X.MARB, G, 0.6) + E(x, y - 10 * s, 3.2 * s, 2.4 * s, null, C.stoneDk, 0.4) +
      L('M' + f(x) + ' ' + f(y - 10 * s) + 'l' + f(2.6 * s) + ' ' + f(-2.6 * s), C.bronze, 0.9);
  }

  defs.push({
    kind: 'palace_hall', variant: 1, name: '宫城正殿（王府大殿）', facility: 'lord_hall', culture: 'chinese_imperial', category: 'landmark',
    fp: [6, 5], up: 44, tags: ['palace', 'imperial', 'three_tier_terrace', 'yulu', 'red_wall', 'gold_tile'], roof: 'hip_tile',
    note: '皇城 / 宫城一角的正殿（太和殿气质的缩小版）：三层汉白玉须弥座（层层栏杆、龙头螭首排水），中轴三跑御路台阶；' +
      '九开间重檐庑殿黄琉璃大殿（斗拱、鸱吻、竖匾）；月台左日晷、右嘉量位，两侧铜鹤与鼎炉；殿前广场、朱红宫墙黄琉璃墙帽。可作王府大殿。',
    draw: function (K, W, U, D) {
      var s = '', cx = W / 2, B = U + D;
      s += K.shadow(6, W - 6, U + 10, B - 3, 10);
      s += K.pave(4, U + 10, W - 4, B - 2, 14, '#d9cdb0');
      s += redWall(6, W - 6, U + 12, 22);
      s += redSide(6, U + 12, B - 4, 22) + redSide(W - 6, U + 12, B - 4, 22);
      // 三台：由下往上逐层收进
      var tiers = [[20, W - 20, U + 30, U + 150, 10], [34, W - 34, U + 30, U + 136, 10], [48, W - 48, U + 30, U + 122, 10]];
      tiers.forEach(function (t, i) {
        s += X.terrace(t[0], t[1], t[2], t[3] - i * 10, t[4], { gap: [cx - 18, cx + 18], railH: 5 });
        // 螭首：台角伸出的龙头排水
        var d = '';
        for (var x = t[0] + 10; x < t[1] - 6; x += 18) { if (Math.abs(x - cx) < 22) continue; d += 'M' + f(x) + ' ' + f(t[3] - i * 10 - t[4] + 1) + 'l0 2.8'; }
        s += L(d, G, 2.6) + L(d, X.MARB, 1.5);
      });
      // 大殿：落在第三层台面上
      var hf = U + 122 - 20 - 10 - 6;
      var hl = X.grandHall(62, W - 62, U + 26, hf, { double: true, h1: 30, h2: 20, inset: 15, skirt: 8, dg: 5.5,
        fac: { bays: 9, doors: [2, 3, 4, 5, 6], col: C.red, beam: C.teal, doorCol: C.red },
        roof: { type: 'hip', tile: TILE.gold, ov: 10, up: 12, hr: 20, ridge: 'chiwen', hipK: 0.9, ridgeH: 4 } });
      s += hl.svg;
      var py = hl.top + 4;
      s += R(cx - 6.5, py, 13, 17, GL) + R(cx - 5.5, py + 1, 11, 15, C.navy, G, 0.5) + L('M' + f(cx - 2.4) + ' ' + f(py + 5) + 'h4.8M' + f(cx - 2.4) + ' ' + f(py + 9) + 'h4.8M' + f(cx - 2.4) + ' ' + f(py + 13) + 'h4.8', GL, 0.8);
      // 三跑御路台阶
      s += X.stair(cx, hf + 6 - 10 + 6, U + 112 + 2, 30, { yulu: true });
      s += X.stair(cx, U + 116, U + 126 + 2, 30, { yulu: true });
      s += X.stair(cx, U + 130, U + 152, 30, { yulu: true });
      // 月台陈设
      s += sundial(cx - 50, U + 102, 0.9) + PT.censer(cx + 50, U + 104, 0.6, 91);
      s += bronzeCrane(cx - 72, U + 116, 0.9) + bronzeCrane(cx + 72, U + 116, 0.9);
      s += PT.censer(cx - 90, U + 132, 0.75, 93) + PT.censer(cx + 90, U + 132, 0.75, 95);
      // 殿前广场：一对铜狮 + 前宫墙（中间留门口）
      s += X.lion(cx - 34, B - 26, 1.1, 1) + X.lion(cx + 34, B - 26, 1.1, -1);
      s += redWall(6, cx - 40, B - 4, 20) + redWall(cx + 40, W - 6, B - 4, 20);
      return s;
    }
  });

  var API = { defs: defs, redWall: redWall, redSide: redSide, lingxing: lingxing, panchi: panchi, brickPodium: brickPodium, bronzeCrane: bronzeCrane, sundial: sundial };
  if (node) module.exports = API;
  else root.TownArtEastLandmarkCivic = API;
})(typeof window !== 'undefined' ? window : this);
