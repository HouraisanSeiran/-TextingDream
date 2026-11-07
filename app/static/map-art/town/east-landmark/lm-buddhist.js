/*
 * 织梦 · 东方文化地标（east-landmark）· 佛教：大型佛寺、楼阁式木塔、密檐砖塔、喇嘛白塔（美术素材，尚未接入游戏）
 * def 格式同 lm-taoist.js。浏览器挂 window.TownArtEastLandmarkBuddhist；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var node = typeof module !== 'undefined' && module.exports;
  var K = node ? require('./lm-core.js') : root.TownArtEastLandmarkCore;
  var PT = node ? require('./lm-parts.js') : root.TownArtEastLandmarkParts;
  var X = node ? require('./lm-extra.js') : root.TownArtEastLandmarkExtra;
  var C = K.C, TILE = K.TILE, G = K.G, GL = K.GL, f = K.f, P = K.P, R = K.R, E = K.E, L = K.L;
  var defs = [];

  defs.push({
    kind: 'buddhist_temple', variant: 1, name: '大型佛寺（丛林）', facility: 'temple', culture: 'buddhist', category: 'landmark',
    fp: [6, 6], up: 32, tags: ['compound', 'courtyard', 'axial', 'multi_court', 'bell_tower', 'drum_tower', 'pond', 'sutra_library'], roof: 'hip_tile',
    note: '中轴多进佛寺：红墙三洞山门与石狮 → 放生池（荷花、汉白玉拱桥）→ 天王殿（单檐歇山灰瓦）→ 左钟楼右鼓楼、铜鼎香炉、经幢长幡 → ' +
      '汉白玉须弥座上的重檐庑殿黄琉璃大雄宝殿（七开间、斗拱、宝珠、御路台阶）→ 后院两层藏经阁（平座回廊）。黄墙院。',
    draw: function (K, W, U, D) {
      var s = '', cx = W / 2, B = U + D;
      s += K.shadow(6, W - 6, U + 10, B - 3, 10);
      s += K.pave(4, U + 8, W - 4, B - 2, 12);
      s += K.pave(cx - 10, U + 150, cx + 10, B - 26, 10, C.stoneLt);
      // 后墙、侧墙
      s += PT.templeWall(6, W - 6, U + 14, 18);
      s += K.sideWall(6, U + 14, B - 4, 18, { col: C.ochre }) + K.sideWall(W - 6, U + 14, B - 4, 18, { col: C.ochre });
      // 藏经阁：两层楼阁，下层七间、上层平座回廊
      s += K.platform(64, W - 64, U + 22, U + 58, 4);
      s += X.tower(cx, U + 54, 26, [
        { w: 150, h: 20, bays: 7, doors: [3], dg: 3.6, ov: 6, tile: TILE.grey },
        { w: 136, h: 16, bays: 7, balcony: true, dg: 3.6, ov: 6, tile: TILE.grey, roof: 'hip', hr: 14, up: 9 }
      ]).svg;
      s += X.cypress(36, U + 62, 1.1) + X.cypress(W - 36, U + 62, 1.1);
      // 大雄宝殿：须弥座 + 重檐庑殿黄琉璃
      var tp = 13, tf = U + 152;
      s += X.terrace(46, W - 46, U + 86, tf, tp, { gap: [cx - 16, cx + 16] });
      var hl = X.grandHall(64, W - 64, U + 100, tf - tp - 6, { double: true, h1: 30, h2: 20, inset: 15, skirt: 8, dg: 5,
        fac: { bays: 7, doors: [2, 3, 4], col: C.red, beam: C.teal, doorCol: C.red },
        roof: { type: 'hip', tile: TILE.gold, ov: 9, up: 12, hr: 18, ridge: 'chiwen', hipK: 0.8, pearl: true, ridgeH: 4 } });
      s += hl.svg;
      s += K.plaque(cx, hl.top + 12, 30, 8, { chars: 4, bg: C.navy });
      s += X.stair(cx, tf - tp, tf + 4, 26, { yulu: true });
      s += PT.censer(cx - 44, tf + 16, 0.8, 51) + PT.censer(cx + 44, tf + 16, 0.8, 53);
      // 钟楼（左）鼓楼（右）
      s += PT.bellTower(14, 52, U + 158, U + 190, { kind: 'bell', hb: 20, hp: 17, spire: false, tile: TILE.grey });
      s += PT.bellTower(W - 52, W - 14, U + 158, U + 190, { kind: 'drum', hb: 20, hp: 17, spire: false, tile: TILE.grey });
      s += PT.pennant(64, U + 206, U + 140, 6, 32, C.ochre) + PT.pennant(W - 70, U + 206, U + 140, 6, 32, C.ochre);
      // 天王殿
      var tb = U + 196, tfr = U + 222;
      s += K.platform(78, W - 78, tb, tfr + 4, 5);
      s += K.steps(cx, tfr + 4, 20, 2);
      s += X.grandHall(84, W - 84, tb - 5, tfr - 5, { h: 22, dg: 4, fac: { bays: 5, doors: [1, 2, 3], col: C.red, beam: C.teal },
        roof: { type: 'hip', tile: TILE.grey, ov: 6, up: 9, hr: 13, ridge: 'chiwen', hipK: 0.55 } }).svg;
      s += K.plaque(cx, tfr - 5 - 22 + 6, 22, 6, { chars: 3, bg: C.navy });
      s += K.tree(30, U + 236, 9, 61, { col: C.teal }) + K.tree(W - 30, U + 236, 9, 67, { col: C.teal });
      // 放生池 + 汉白玉拱桥
      s += X.pond(56, U + 232, W - 56, U + 250, { seed: 9, lotus: 7 });
      s += X.archBridge(cx, U + 249, 26, { h: 6 });
      // 山门 + 前院黄墙 + 石狮
      s += PT.templeWall(6, cx - 42, B - 4, 18) + PT.templeWall(cx + 42, W - 6, B - 4, 18);
      s += PT.shanmen(cx - 42, cx + 42, B - 30, B - 5, 28, { arches: 3, chars: 3, tile: TILE.grey });
      s += X.lion(cx - 52, B - 2, 0.95, 1) + X.lion(cx + 52, B - 2, 0.95, -1);
      return s;
    }
  });

  /** 八角塔身一段：正面 + 左右两道斜面（左受光、右背光）。返回 svg。wT/wB = 顶 / 底宽，k = 斜面占比。 */
  function octBody(cx, yT, yB, wT, wB, k, col, colR) {
    var a = wT / 2, b = wB / 2, sa = wT * k, sb = wB * k;
    return P(K.pts([[cx - a, yT + 1.2], [cx - a + sa, yT], [cx - b + sb, yB], [cx - b, yB - 1.2]]), col, G, 0.7) +
      P(K.pts([[cx + a - sa, yT], [cx + a, yT + 1.2], [cx + b, yB - 1.2], [cx + b - sb, yB]]), colR, G, 0.7) +
      P(K.pts([[cx - a + sa, yT], [cx + a - sa, yT], [cx + b - sb, yB], [cx - b + sb, yB]]), col, G, 0.8);
  }

  defs.push({
    kind: 'pagoda', variant: 1, name: '楼阁式木塔', facility: 'temple', culture: 'buddhist', category: 'landmark',
    fp: [3, 3], up: 132, tags: ['pagoda', 'wooden', 'octagonal', 'multi_storey', 'balcony'], roof: 'hip_tile',
    note: '八角五层楼阁式木塔（应县木塔的气质）：两级青石台基 + 汉白玉栏杆，底层副阶周匝（一圈腰檐）；上四层每层平座回廊、斗拱、' +
      '层层出檐、逐层收分；第三层挂竖匾；顶为八角攒尖 + 铁刹相轮。roof 用 hip_tile（实为攒尖），见 note。',
    draw: function (K, W, U, D) {
      var s = '', cx = W / 2, B = U + D;
      s += K.shadow(cx - 56, cx + 56, U + 40, B - 6, 10);
      s += K.pave(6, U + 30, W - 6, B - 2, 12);
      s += K.platform(10, W - 10, U + 40, B - 8, 6);
      s += X.terrace(22, W - 22, U + 46, B - 18, 9, { gap: [cx - 12, cx + 12] });
      s += K.steps(cx, B - 18, 22, 4, 2.4);
      var yf = B - 30;
      // 副阶周匝：底层外一圈低檐
      s += K.facade(cx - 52, cx + 52, yf, 14, { bays: 7, doors: [3], win: 'straight', col: C.red, beam: C.teal });
      s += K.roof(cx - 52, cx + 52, yf - 20, yf, 15, { type: 'hip', tile: TILE.grey, ov: 6, up: 8, hr: 6, inset: 30, ridge: 'plain', ridgeH: 1.5 }).svg;
      var LV = [
        { w: 86, h: 26, bays: 3, doors: [1], oct: 0.18, dg: 4, ov: 7, tile: TILE.grey, hr: 5, ridgeW: 10 },
        { w: 80, h: 24, bays: 3, doors: [], oct: 0.18, balcony: true, dg: 4, ov: 7, tile: TILE.grey, hr: 5, ridgeW: 10 },
        { w: 74, h: 23, bays: 3, doors: [], oct: 0.18, balcony: true, dg: 4, ov: 7, tile: TILE.grey, hr: 5, ridgeW: 9 },
        { w: 68, h: 22, bays: 3, doors: [], oct: 0.18, balcony: true, dg: 4, ov: 7, tile: TILE.grey, hr: 5, ridgeW: 8 },
        { w: 62, h: 22, bays: 3, doors: [], oct: 0.18, balcony: true, dg: 4, ov: 8, tile: TILE.grey, roof: 'spire', hr: 26, up: 11, finial: 0 }
      ];
      var tw = X.tower(cx, yf - 15, 22, LV);
      s += tw.svg + PT.tasha(cx, tw.roof.ridgeY + 2, 1.8);
      // 第三层竖匾：按层高算出第三层墙面中点
      var y3 = yf - 15 - (LV[0].h + 6) - (LV[1].h + 6), py = y3 - LV[2].h / 2 - 8;
      s += R(cx - 5, py, 10, 15, GL) + R(cx - 4, py + 1, 8, 13, C.navy, G, 0.5) +
        L('M' + f(cx - 2) + ' ' + f(py + 4) + 'h4M' + f(cx - 2) + ' ' + f(py + 7.5) + 'h4M' + f(cx - 2) + ' ' + f(py + 11) + 'h4', GL, 0.8);
      s += PT.censer(cx - 34, B - 6, 0.7, 71) + PT.censer(cx + 34, B - 6, 0.7, 73);
      return s;
    }
  });

  defs.push({
    kind: 'pagoda', variant: 2, name: '密檐砖塔', facility: 'temple', culture: 'buddhist', category: 'landmark',
    fp: [2, 2], up: 160, tags: ['pagoda', 'brick', 'octagonal', 'dense_eave'], roof: 'hip_tile',
    note: '八角十三级密檐砖塔（辽金密檐塔的气质）：须弥座 + 仰莲平座，高大的第一层塔身开券门、两侧直棂假窗、转角倚柱，上承斗拱；' +
      '其上十三道密檐层层相叠，轮廓微鼓（卷杀）再收；顶为攒尖 + 塔刹。',
    draw: function (K, W, U, D) {
      var s = '', cx = W / 2, B = U + D;
      s += K.shadow(cx - 34, cx + 34, U + 40, B - 6, 8);
      s += K.pave(4, U + 34, W - 4, B - 2, 12);
      s += K.platform(12, W - 12, U + 44, B - 8, 5);
      // 须弥座（八角）+ 仰莲
      var y = B - 13;
      s += octBody(cx, y - 12, y, 58, 62, 0.2, C.stoneLt, C.stone);
      s += L('M' + f(cx - 30) + ' ' + f(y - 6) + 'H' + f(cx + 30), C.stoneDk, 0.7, 0.8);
      var lt = '';
      for (var i = 0; i < 9; i++) { var lx = cx - 26 + i * 6.5; lt += 'M' + f(lx - 3) + ' ' + f(y - 12) + 'Q' + f(lx) + ' ' + f(y - 17) + ' ' + f(lx + 3) + ' ' + f(y - 12); }
      s += R(cx - 28, y - 16, 56, 4, C.wallLt, G, 0.6) + L(lt, G, 0.8);
      // 第一层塔身
      y -= 16;
      var h1 = 44;
      s += octBody(cx, y - h1, y, 40, 40, 0.2, C.stoneLt, C.stone);
      s += K.bricks(cx - 12, y - h1, cx + 12, y, C.stoneDk, 6, 3.4);
      s += P('M' + f(cx - 5) + ' ' + f(y) + 'V' + f(y - 17) + 'A5 5 0 0 1 ' + f(cx + 5) + ' ' + f(y - 17) + 'V' + f(y) + 'Z', C.dark, C.wallLt, 1.6) + K.door(cx - 4, y - 14, 8, 14, { col: C.red, studs: false });
      s += K.lattice(cx - 18.5, y - 26, 5, 12, { straight: true, step: 1.6 }) + K.lattice(cx + 13.5, y - 26, 5, 12, { straight: true, step: 1.6, bg: '#6a2e1a' });
      s += R(cx - 20.5, y - h1, 2, h1, C.red, GL, 0.4) + R(cx + 18.5, y - h1, 2, h1, K.mix(C.red, '#000000', 0.2), GL, 0.4);
      s += X.dougong(cx - 21, cx + 21, y - h1 - 6, y - h1 + 0.5, { sp: 6 });
      s += K.roof(cx - 21, cx + 21, y - h1 - 8, y - h1, 6, { type: 'hip', tile: TILE.grey, ov: 6, up: 6, hr: 3, inset: 16, ridge: 'plain', ridgeH: 1.2 }).svg;
      // 十三道密檐
      y = y - h1 - 8;
      var N = 13, sp = 10, band = 4.6, rf;
      for (var j = 0; j < N; j++) {
        var t = j / (N - 1), w = 40 + 4 * Math.sin(Math.PI * t) - 20 * t * t, bw = w * 0.8;
        s += octBody(cx, y - band, y, bw, bw, 0.2, C.stoneLt, C.stone);
        if (j % 3 === 1) s += E(cx, y - band / 2, 1.1, 1.2, C.dark);
        var last = j === N - 1;
        rf = K.roof(cx - w / 2, cx + w / 2, y - 6, y, band, last
          ? { type: 'spire', tile: TILE.grey, ov: 4, up: 5, hr: 14, finial: 0 }
          : { type: 'hip', tile: TILE.grey, ov: 4, up: 3.5, hr: 2, inset: w / 2 - 4, ridge: 'plain', ridgeH: 1 });
        s += rf.svg;
        y -= sp;
      }
      s += PT.tasha(cx, rf.ridgeY + 2, 1.15);
      return s;
    }
  });

  defs.push({
    kind: 'pagoda', variant: 3, name: '喇嘛白塔（覆钵式）', facility: 'temple', culture: 'buddhist', category: 'landmark',
    fp: [3, 3], up: 94, tags: ['pagoda', 'stupa', 'lama', 'white'], roof: 'none',
    note: '覆钵式喇嘛塔（妙应寺白塔的气质）：方台 + 两层亚字形须弥座（折角、束腰金线）→ 莲座 → 白色覆钵（塔肚子）正面开眼光门（佛龛）→ ' +
      '塔脖子 → 十三天相轮（白色锥体 + 十三道金环）→ 铜华盖垂流苏 → 鎏金宝顶。塔前铜鼎香炉、两侧经幢长幡。',
    draw: function (K, W, U, D) {
      var s = '', cx = W / 2, B = U + D, WH = '#fbf6ea', WS = '#e3d8bf';
      s += K.shadow(cx - 56, cx + 56, U + 30, B - 6, 10);
      s += K.pave(6, U + 30, W - 6, B - 2, 12);
      s += K.platform(12, W - 12, U + 36, B - 10, 6);
      s += K.steps(cx, B - 10, 24, 3);
      // 亚字形须弥座两层：每层正面中段凸出、两端折角缩进
      var y = B - 16;
      [[100, 22, 16], [80, 18, 14]].forEach(function (lv) {
        var w = lv[0], h = lv[2], k = 10, x0 = cx - w / 2, x1 = cx + w / 2;
        s += R(x0, y - h - lv[1], w, lv[1], WS, G, 0.8);
        s += R(x0, y - h, k, h, WS, G, 0.8) + R(x1 - k, y - h, k, h, '#d3c6a8', G, 0.8) + R(x0 + k - 2, y - h + 1.5, w - 2 * k + 4, h - 1.5, WH, G, 0.9);
        s += R(x0 + k, y - h * 0.62, w - 2 * k, h * 0.3, C.stoneLt, G, 0.5) + L('M' + f(x0 + k) + ' ' + f(y - h * 0.47) + 'H' + f(x1 - k), GL, 0.8);
        s += R(x0 - 1, y - h - 1.6, w + 2, 2, WH, G, 0.6);
        y = y - h - lv[1] * 0.45;
      });
      // 莲座
      var lt = '';
      for (var i = 0; i < 11; i++) { var lx = cx - 30 + i * 6; lt += 'M' + f(lx - 3) + ' ' + f(y) + 'Q' + f(lx) + ' ' + f(y - 6) + ' ' + f(lx + 3) + ' ' + f(y); }
      s += P('M' + f(cx - 34) + ' ' + f(y + 1) + 'Q' + f(cx) + ' ' + f(y - 10) + ' ' + f(cx + 34) + ' ' + f(y + 1) + 'Z', WS, G, 0.8) + L(lt, G, 0.8);
      y -= 6;
      // 覆钵：左亮右暗两块平涂
      var bw = 34, bh = 50, by = y;
      var bowl = 'M' + f(cx - bw * 0.9) + ' ' + f(by) + 'C' + f(cx - bw * 1.15) + ' ' + f(by - bh * 0.55) + ' ' + f(cx - bw * 0.7) + ' ' + f(by - bh) + ' ' + f(cx - bw * 0.42) + ' ' + f(by - bh) +
        'H' + f(cx + bw * 0.42) + 'C' + f(cx + bw * 0.7) + ' ' + f(by - bh) + ' ' + f(cx + bw * 1.15) + ' ' + f(by - bh * 0.55) + ' ' + f(cx + bw * 0.9) + ' ' + f(by) + 'Z';
      s += P(bowl, WH, G, 1.2);
      s += P('M' + f(cx + bw * 0.3) + ' ' + f(by - bh + 1) + 'C' + f(cx + bw * 0.75) + ' ' + f(by - bh * 0.9) + ' ' + f(cx + bw * 1.05) + ' ' + f(by - bh * 0.5) + ' ' + f(cx + bw * 0.86) + ' ' + f(by - 0.6) +
        'H' + f(cx + bw * 0.55) + 'C' + f(cx + bw * 0.7) + ' ' + f(by - bh * 0.45) + ' ' + f(cx + bw * 0.55) + ' ' + f(by - bh * 0.85) + ' ' + f(cx + bw * 0.3) + ' ' + f(by - bh + 1) + 'Z', WS);
      s += L('M' + f(cx - bw * 0.86) + ' ' + f(by - bh * 0.18) + 'Q' + f(cx) + ' ' + f(by - bh * 0.1) + ' ' + f(cx + bw * 0.86) + ' ' + f(by - bh * 0.18), GL, 0.9);
      // 眼光门：火焰形佛龛
      var ny = by - bh * 0.2;
      s += P('M' + f(cx - 7) + ' ' + f(ny) + 'V' + f(ny - 12) + 'Q' + f(cx - 7) + ' ' + f(ny - 19) + ' ' + f(cx) + ' ' + f(ny - 24) + 'Q' + f(cx + 7) + ' ' + f(ny - 19) + ' ' + f(cx + 7) + ' ' + f(ny - 12) + 'V' + f(ny) + 'Z', C.ochre, G, 0.8);
      s += P('M' + f(cx - 4.6) + ' ' + f(ny) + 'V' + f(ny - 11) + 'Q' + f(cx - 4.6) + ' ' + f(ny - 16) + ' ' + f(cx) + ' ' + f(ny - 19.5) + 'Q' + f(cx + 4.6) + ' ' + f(ny - 16) + ' ' + f(cx + 4.6) + ' ' + f(ny - 11) + 'V' + f(ny) + 'Z', C.red, GL, 0.6);
      s += E(cx, ny - 9, 2, 2.2, C.ochreLt, G, 0.5) + E(cx, ny - 4, 3, 2.4, C.ochreLt, G, 0.5);
      // 塔脖子（方形折角座）
      y = by - bh;
      s += R(cx - 18, y - 5, 36, 5, WS, G, 0.8) + R(cx - 13, y - 10, 26, 5, WH, G, 0.8) + L('M' + f(cx - 13) + ' ' + f(y - 7.5) + 'H' + f(cx + 13), GL, 0.7);
      y -= 10;
      // 十三天：白色锥体 + 十三道金环
      var ch = 72, w0 = 24, w1 = 10;
      s += P(K.pts([[cx - w0 / 2, y], [cx - w1 / 2, y - ch], [cx + w1 / 2, y - ch], [cx + w0 / 2, y]]), WH, G, 1);
      s += P(K.pts([[cx + w0 * 0.2, y], [cx + w1 * 0.2, y - ch], [cx + w1 / 2, y - ch], [cx + w0 / 2, y]]), WS);
      var rg = '';
      for (var j = 1; j <= 13; j++) { var yy = y - ch * j / 14, ww = (w0 + (w1 - w0) * j / 14) / 2; rg += 'M' + f(cx - ww) + ' ' + f(yy) + 'H' + f(cx + ww); }
      s += L(rg, G, 1.1) + L(rg, C.ochreLt, 0.5);
      y -= ch;
      // 华盖 + 流苏 + 宝顶
      s += E(cx, y - 1, 15, 3.6, C.bronze, GL, 0.9) + P('M' + f(cx - 15) + ' ' + f(y - 1) + 'Q' + f(cx) + ' ' + f(y - 9) + ' ' + f(cx + 15) + ' ' + f(y - 1) + 'Z', C.bronze, GL, 0.9);
      var ts = '';
      for (var t = -12; t <= 12; t += 4) ts += 'M' + f(cx + t) + ' ' + f(y + 1.5) + 'v' + f(5 - Math.abs(t) * 0.15);
      s += L(ts, C.ochre, 0.9);
      s += R(cx - 3, y - 12, 6, 4, C.ochre, G, 0.6) + E(cx, y - 17, 4.6, 5.2, C.ochre, G, 0.9) + E(cx - 1.4, y - 18.4, 1.6, 2, C.ochreLt) +
        E(cx, y - 25, 2.4, 2.8, C.ochre, G, 0.8) + L('M' + f(cx) + ' ' + f(y - 27.5) + 'v-3', C.umber, 1);
      // 塔前香炉、两侧长幡
      s += PT.censer(cx, B - 4, 0.75, 81);
      s += PT.pennant(18, B - 12, U + 60, 6, 34, C.ochre) + PT.pennant(W - 24, B - 12, U + 60, 6, 34, C.red);
      return s;
    }
  });

  var API = { defs: defs, octBody: octBody };
  if (node) module.exports = API;
  else root.TownArtEastLandmarkBuddhist = API;
})(typeof window !== 'undefined' ? window : this);
