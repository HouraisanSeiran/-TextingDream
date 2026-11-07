/*
 * 织梦 · 东方特殊建筑 · 商贸与仓储：菜市摊棚、市楼、酒楼客栈、驿站、粮仓、马厩、水车磨坊（美术素材，尚未接入游戏）
 * def 格式同 civic.js。
 */
(function (root) {
  'use strict';
  var K = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtEastSpecialCore;
  var C = K.C, TILE = K.TILE, G = K.G, GL = K.GL, f = K.f, P = K.P, R = K.R, E = K.E, L = K.L;
  var SHF = ' fill-opacity="0.2"', BAMBOO = '#d8c27a';
  var defs = [];

  // ====================== 摊棚配件 ======================
  /** 竹竿：带竹节。 */
  function bamboo(x, y0, y1, w) {
    w = w || 1.6;
    var d = 'M' + f(x) + ' ' + f(y0) + 'V' + f(y1), n = '';
    for (var y = y0 - 6; y > y1 + 2; y -= 7) n += 'M' + f(x - w / 2 - 0.3) + ' ' + f(y) + 'h' + f(w + 0.6);
    return L(d, G, w + 1.2) + L(d, BAMBOO, w) + L(n, C.umber, 0.6, 0.8);
  }
  function lerp(p, q, t) { return [p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]; }
  /** 条纹布棚顶：后沿 yBack、前沿 yFront（斜俯视看到的棚面），前沿垂一道波浪边的布帘。 */
  function canopy(x0, x1, yBack, yFront, cols, o) {
    o = o || {};
    var A = [x0 - 2, yBack], B = [x1 + 2, yBack], Cc = [x1 + 4, yFront], Dd = [x0 - 4, yFront], n = o.n || 6, s = '';
    s += P(K.pts([A, B, Cc, Dd]), cols[0]);
    for (var i = 1; i < n; i += 2) s += P(K.pts([lerp(A, B, i / n), lerp(A, B, (i + 1) / n), lerp(Dd, Cc, (i + 1) / n), lerp(Dd, Cc, i / n)]), cols[1]);
    // 叠晕：棚面后半压一层浅色
    s += P(K.pts([A, B, lerp(B, Cc, 0.35), lerp(A, Dd, 0.35)]), '#ffffff', null, 0, ' fill-opacity="0.16"');
    s += P(K.pts([A, B, Cc, Dd]), null, G, 1.1);
    var vh = o.vh || 5, sc = (Cc[0] - Dd[0]) / n, d = 'M' + f(Dd[0]) + ' ' + f(yFront) + 'H' + f(Cc[0]) + 'V' + f(yFront + vh);
    for (var j = n; j > 0; j--) {
      var xa = Dd[0] + sc * j, xb = Dd[0] + sc * (j - 1);
      d += 'Q' + f((xa + xb) / 2) + ' ' + f(yFront + vh + 3.2) + ' ' + f(xb) + ' ' + f(yFront + vh);
    }
    s += P(d + 'Z', o.val || cols[0], G, 0.9) + L('M' + f(Dd[0] + 1) + ' ' + f(yFront + 1.8) + 'H' + f(Cc[0] - 1), GL, 0.7);
    return s;
  }
  function cabbage(x, y) {
    return E(x, y - 3, 4.4, 3.3, C.teal, G, 0.6) + E(x - 0.4, y - 3.6, 2.8, 2, C.tealLt) +
      L('M' + f(x - 2.5) + ' ' + f(y - 3) + 'Q' + f(x) + ' ' + f(y - 5) + ' ' + f(x + 2.5) + ' ' + f(y - 3), '#e8f3d6', 0.5);
  }
  function radish(x, y, dir) {
    dir = dir || 1;
    return P('M' + f(x) + ' ' + f(y - 4.6) + 'Q' + f(x + dir * 5) + ' ' + f(y - 3.6) + ' ' + f(x + dir * 9) + ' ' + f(y - 1.4) + 'Q' + f(x + dir * 4) + ' ' + f(y) + ' ' + f(x) + ' ' + f(y - 1.4) + 'Z', C.wallLt, G, 0.6) +
      L('M' + f(x) + ' ' + f(y - 3) + 'l' + f(-dir * 3) + ' -3M' + f(x) + ' ' + f(y - 3) + 'l' + f(-dir * 4) + ' -1M' + f(x) + ' ' + f(y - 3) + 'l' + f(-dir * 1.5) + ' -4', C.teal, 1.2);
  }
  /** 一堆圆果：底排 n 个、往上逐排少一个。 */
  function fruitPile(x, y, n, r, col, lite) {
    var s = '';
    for (var row = 0; row < n; row++)
      for (var i = 0; i < n - row; i++) {
        var cx = x + (i - (n - row - 1) / 2) * r * 1.9, cy = y - r - row * r * 1.5;
        s += E(cx, cy, r, r, col, G, 0.5) + E(cx - r * 0.3, cy - r * 0.3, r * 0.35, r * 0.35, lite);
      }
    return s;
  }
  function fish(x, y, len, dir, col) {
    dir = dir || 1; col = col || C.navyLt;
    var h = len * 0.32;
    return P('M' + f(x - dir * len / 2) + ' ' + f(y) + 'Q' + f(x) + ' ' + f(y - h) + ' ' + f(x + dir * len / 2) + ' ' + f(y) + 'Q' + f(x) + ' ' + f(y + h) + ' ' + f(x - dir * len / 2) + ' ' + f(y) + 'Z', col, G, 0.6) +
      P(K.pts([[x - dir * len / 2 + dir * 1, y], [x - dir * len / 2 - dir * 3, y - h * 0.9], [x - dir * len / 2 - dir * 3, y + h * 0.9]]), col, G, 0.5) +
      K.dots([[x + dir * len * 0.3, y - h * 0.15]], C.dark, 1.1) + L('M' + f(x - dir * len * 0.2) + ' ' + f(y - h * 0.2) + 'H' + f(x + dir * len * 0.15), C.tealLt, 0.6, 0.8);
  }
  /** 一卷布匹（横放）。 */
  function bolt(x, y, w, col) {
    return R(x, y - 4.4, w, 4.4, col, G, 0.6) + E(x + w, y - 2.2, 1.4, 2.2, K.mix(col, '#ffffff', 0.35), G, 0.5) +
      L('M' + f(x + 1) + ' ' + f(y - 3.2) + 'H' + f(x + w - 1), '#ffffff', 0.5, 0.45);
  }
  /** 竹蒸笼一摞 + 蒸汽。 */
  function steamer(x, y, n) {
    var s = '';
    for (var i = 0; i < n; i++) s += K.box(x - 6, x + 6, y - 2 - i * 3.6, y - i * 3.6, 3.6, C.ochreLt, C.ochre, G, 0.6) + L('M' + f(x - 6) + ' ' + f(y - i * 3.6 - 1.8) + 'h12', C.umberLt, 0.5, 0.8);
    var top = y - 2 - n * 3.6;
    return s + E(x, top - 0.6, 5, 1.6, C.ochreLt, G, 0.6) + K.smoke(x - 1, top - 6, 5, 41);
  }
  function bowl(x, y, col) {
    return P('M' + f(x - 2.8) + ' ' + f(y - 2.4) + 'Q' + f(x) + ' ' + f(y + 0.6) + ' ' + f(x + 2.8) + ' ' + f(y - 2.4) + 'Z', col || C.wallLt, G, 0.5) + L('M' + f(x - 2) + ' ' + f(y - 1.6) + 'H' + f(x + 2), C.teal, 0.5);
  }
  /** 扁担：一根弯木杆，两端绳子各挂一只箩筐。 */
  function carryPole(x0, x1, y, r, fills) {
    var s = K.basket(x0, y, r, fills[0]) + K.basket(x1, y, r, fills[1]);
    var top = y - r * 2.6;
    s += L('M' + f(x0 - r * 0.8) + ' ' + f(y - r * 0.9) + 'L' + f(x0) + ' ' + f(top) + 'L' + f(x0 + r * 0.8) + ' ' + f(y - r * 0.9) +
      'M' + f(x1 - r * 0.8) + ' ' + f(y - r * 0.9) + 'L' + f(x1) + ' ' + f(top) + 'L' + f(x1 + r * 0.8) + ' ' + f(y - r * 0.9), C.umber, 0.6, 0.9);
    var pd = 'M' + f(x0 - 3) + ' ' + f(top + 0.6) + 'Q' + f((x0 + x1) / 2) + ' ' + f(top - 2.4) + ' ' + f(x1 + 3) + ' ' + f(top + 0.6);
    return s + L(pd, G, 2.8) + L(pd, BAMBOO, 1.8);
  }

  /**
   * 一个 1×1 摊位：四根竹竿撑条纹布棚，棚下木案，案上货；案前地上放箩筐等。
   * goods(yTop) 画案面上的货，front(yGround) 画案前地面的东西。
   */
  function stall(K, W, U, D, o) {
    var s = '', yb = U + 14, yF = U + 38, ph = 30, x0 = 7, x1 = W - 7;
    s += K.shadow(x0, x1, yb, yF + 6, 6);
    s += P(K.pts([[3, U + 10], [W - 3, U + 10], [W - 3, U + D - 1], [3, U + D - 1]]), C.pave, null, 0, ' fill-opacity="0.55"');
    s += bamboo(x0 + 1, yb, yb - ph - 4) + bamboo(x1 - 1, yb, yb - ph - 4);
    // 木案
    s += K.box(x0 + 1, x1 - 1, yb + 8, yF - 2, 9, C.umberLt, C.umber, GL, 0.7) + L('M' + f(x0 + 2) + ' ' + f(yF - 6.5) + 'H' + f(x1 - 2), '#6a3d27', 0.6, 0.8);
    s += o.goods(yb + 8 - 9 + 9.5);
    s += bamboo(x0 - 1, yF + 1, yF - ph + 4) + bamboo(x1 + 1, yF + 1, yF - ph + 4);
    s += canopy(x0, x1, yb - ph - 4, yF - ph + 3, o.cols, { n: 6, vh: 5 });
    if (o.sign) s += o.sign;
    s += o.front(U + D - 3);
    return s;
  }
  var STALL = { category: 'prop', facility: 'market_hall', fp: [1, 1], up: 40, roof: 'none' };
  function stallDef(v, name, tags, note, o) {
    return { kind: 'stall', variant: v, name: name, facility: STALL.facility, category: STALL.category, fp: STALL.fp, up: STALL.up, roof: STALL.roof,
      tags: ['open_air', 'stall', 'scatter'].concat(tags), note: note + ' 1×1 散放摊位，可在空地上成片排布组成露天菜市（facility 按规范记 market_hall + open_air）；棚为布顶，roof 记 none。',
      draw: function (K, W, U, D) { return stall(K, W, U, D, o); } };
  }

  defs.push(stallDef(1, '菜摊', ['vegetable'], '青绿条纹布棚；案上白菜、萝卜；案前一副扁担箩筐。', {
    cols: [C.teal, C.wallLt],
    goods: function (y) { return cabbage(14, y) + cabbage(22, y + 0.5) + radish(27, y - 0.5, 1) + cabbage(36, y); },
    front: function (y) { return carryPole(11, 36, y, 4.2, [[C.teal, C.tealLt], [C.orange, C.ochre]]); }
  }));
  defs.push(stallDef(2, '果摊', ['fruit'], '橘红条纹布棚；案上橘子、桃子堆成垛；案前两只满筐。', {
    cols: [C.orange, C.wallLt],
    goods: function (y) { return fruitPile(16, y, 3, 2.2, C.orange, C.ochreLt) + fruitPile(32, y, 3, 2.2, '#e98a8a', '#f8d2c0'); },
    front: function (y) { return K.basket(14, y, 5, [C.orange, C.ochre]) + K.basket(34, y - 1, 5, ['#e98a8a', C.orange]); }
  }));
  defs.push(stallDef(3, '鱼摊', ['fish'], '藏青布棚；案上砧板摆两尾鱼，案头挂一条；案前木盆养活鱼。', {
    cols: [C.navy, C.wallLt],
    goods: function (y) { return R(11, y - 4.5, 24, 4, C.ochreLt, G, 0.5) + fish(17, y - 2.6, 10, 1) + fish(29, y - 2.4, 10, -1, C.greyLt); },
    front: function (y) {
      return E(31, y - 1, 10, 3.4, C.umberLt, G, 0.8) + E(31, y - 2.2, 8.6, 2.6, C.navyLt, G, 0.5) + fish(28, y - 2.2, 6, 1, C.orange) + fish(34, y - 2.6, 6, -1, C.greyLt) +
        K.basket(11, y, 4.5, null);
    }
  }));
  defs.push(stallDef(4, '布摊', ['cloth'], '朱红条纹布棚；案上一卷卷花布；棚边竹竿上搭一匹青布。', {
    cols: [C.red, C.ochreLt],
    goods: function (y) { return bolt(10, y, 10, C.teal) + bolt(21, y + 0.5, 10, C.ochre) + bolt(14, y - 4, 10, C.red) + bolt(30, y, 7, C.navyLt); },
    front: function (y) {
      return L('M6 ' + f(y - 18) + 'H22', C.umber, 1.2) + P('M8 ' + f(y - 18) + 'H20V' + f(y - 4) + 'Q14 ' + f(y - 2) + ' 8 ' + f(y - 4) + 'Z', C.navyLt, G, 0.6) +
        L('M6 ' + f(y) + 'V' + f(y - 19) + 'M22 ' + f(y) + 'V' + f(y - 19), C.umber, 1) + K.jar(36, y, 4, C.umberLt);
    }
  }));
  defs.push(stallDef(5, '点心摊', ['food', 'steam'], '赭黄布棚；案上竹蒸笼冒热气、一排小碗；案前小炉与条凳。', {
    cols: [C.ochre, C.wallLt],
    goods: function (y) { return steamer(16, y, 3) + bowl(28, y) + bowl(34, y) + bowl(31, y - 2.5, C.wallLt); },
    front: function (y) {
      return K.box(8, 20, y - 3, y, 4, C.brick, C.umberLt, G, 0.6) + K.fire(14, y - 6.5, 2.4) + K.box(26, 42, y - 3, y, 3.5, C.umberLt, C.umber, GL, 0.5);
    }
  }));

  // ====================== 市楼 ======================
  /** 货堆：几只麻袋 / 木箱。 */
  function sacks(x, y, n) {
    var s = '';
    for (var i = 0; i < n; i++) {
      var cx = x + i * 7, cy = y - (i % 2 ? 1 : 0);
      s += P('M' + f(cx - 3.4) + ' ' + f(cy) + 'Q' + f(cx - 4.2) + ' ' + f(cy - 5) + ' ' + f(cx - 1.6) + ' ' + f(cy - 7.4) + 'H' + f(cx + 1.6) + 'Q' + f(cx + 4.2) + ' ' + f(cy - 5) + ' ' + f(cx + 3.4) + ' ' + f(cy) + 'Z', C.ochreLt, G, 0.6) +
        L('M' + f(cx - 1.6) + ' ' + f(cy - 6.4) + 'H' + f(cx + 1.6), C.umber, 0.8);
    }
    return s;
  }
  function crate(x, y, w, h) {
    return K.box(x, x + w, y - w * 0.4, y, h, C.umberLt, C.ochre, G, 0.6) + L('M' + f(x) + ' ' + f(y - h) + 'L' + f(x + w) + ' ' + f(y) + 'M' + f(x + w) + ' ' + f(y - h) + 'L' + f(x) + ' ' + f(y), C.umber, 0.6, 0.8);
  }

  defs.push({
    kind: 'carry-pole', variant: 1, name: '扁担箩筐', facility: 'market_hall', category: 'prop', fp: [1, 1], up: 4, roof: 'none',
    tags: ['open_air', 'scatter', 'prop'], note: '散放小摆件：一副扁担挑两只满筐（青菜、萝卜），可撒在菜市空地、码头、城门口。',
    draw: function (K, W, U, D) { return carryPole(13, 35, U + D - 8, 5, [[C.teal, C.tealLt], [C.wallLt, C.orange]]) + K.basket(38, U + 20, 4, [C.ochre]) + K.basket(10, U + 22, 4, null); }
  });

  /** 竖招牌：一块立在地上的长条木招牌，两根小柱夹着。 */
  function signBoard(x, y, h, col) {
    return L('M' + f(x - 3.6) + ' ' + f(y) + 'V' + f(y - h - 2) + 'M' + f(x + 3.6) + ' ' + f(y) + 'V' + f(y - h - 2), C.umber, 1.2) +
      K.plaque(x, y - h / 2 - 2, 6, h - 2, { chars: 1, bg: col || C.navy }) +
      L('M' + f(x) + ' ' + f(y - h + 4) + 'V' + f(y - 6), GL, 0.7);
  }

  defs.push({
    kind: 'market_hall', variant: 1, name: '市楼（两层商楼）', facility: 'market_hall', category: 'special', fp: [3, 2], up: 80,
    tags: ['two_storey', 'covered_market', 'shop', 'plaque'], roof: 'hip_tile',
    note: '两层商楼：楼下四间全敞铺面，楼上格扇窗 + 平座栏杆，腰檐 + 歇山青绿瓦，二层正中挂大匾；檐下一排红灯笼；门前麻袋、木箱、箩筐与竖招牌。与 open_air 的摊棚区分。',
    draw: function (K, W, U, D) {
      var s = '', x0 = 8, x1 = W - 8, yb = U + 6, yf = U + 66, h1 = 26, h2 = 22;
      s += K.shadow(x0, x1, yb, yf, 9);
      s += K.pave(2, yf - 2, W - 2, U + D - 1, 12);
      var hl = K.hall(x0, x1, yb, yf, { double: true, h1: h1, h2: h2, inset: 3, skirt: 6,
        fac: { bays: 4, doors: [0, 1, 2, 3], open: true, col: C.red, beam: C.teal, doorW: 26, doorH: 21 },
        upFac: { bays: 4, doors: [], win: 'lattice', sill: false, col: C.red, beam: C.teal },
        roof: { type: 'hip', tile: TILE.teal, ov: 6, up: 8, hr: 14, ridge: 'chiwen', hipK: 0.5 } });
      s += hl.svg;
      // 铺内货架影子：敞开的铺面里露出几排货
      for (var i = 0; i < 4; i++) {
        var bx = x0 + (x1 - x0) / 4 * i + 6;
        s += R(bx, yf - 15, 20, 2, C.umberLt, GL, 0.4) + K.jar(bx + 5, yf - 15, 2.6, C.ochre) + K.jar(bx + 13, yf - 15, 2.6, C.teal);
      }
      var upBase = yf - 5 - h1;
      s += K.railing(x0 + 3, x1 - 3, upBase + 1, 4, C.red);
      s += K.plaque(W / 2, upBase - h2 + 9, 40, 9, { chars: 3, bg: C.navy });
      [x0 + 6, x0 + 40, x1 - 40, x1 - 6].forEach(function (x) { s += K.lantern(x, yf - h1 + 2, 2.6); });
      // 门前货
      var gy = U + D - 4;
      s += sacks(14, gy, 3) + crate(40, gy, 12, 9) + crate(44, gy - 9, 8, 6) + K.basket(68, gy, 5, [C.orange, C.ochre]) +
        K.basket(80, gy - 1, 5, [C.teal, C.tealLt]) + crate(96, gy, 12, 9) + sacks(116, gy, 2) + signBoard(W - 6, gy, 22, C.red);
      return s;
    }
  });

  defs.push({
    kind: 'market_hall', variant: 2, name: '跨街市楼（钟鼓市楼）', facility: 'market_hall', category: 'special', fp: [3, 2], up: 72,
    tags: ['two_storey', 'landmark', 'street_arch', 'drum', 'plaque'], roof: 'hip_tile',
    note: '跨街而立的市楼：青砖台基开一道券洞（街道从洞下穿过），台上两层重檐楼阁、四面平座栏杆；楼上悬鼓（击鼓开市、闭市），正中大匾；台下两侧摆箩筐扁担。参考平遥市楼一类形制，原创绘制。',
    draw: function (K, W, U, D) {
      var s = '', bx0 = 16, bx1 = W - 16, yb = U + 14, yf = U + 84, hb = 30;
      s += K.shadow(bx0, bx1, yb, yf, 10);
      s += K.pave(2, U + 4, W - 2, U + D - 1, 12);
      // 台基：顶面 + 正面青砖 + 券洞（洞里露出后面的石板街）
      s += K.box(bx0, bx1, yb, yf, hb, C.stoneLt, C.stone, G, 1.1) + K.bricks(bx0, yf - hb, bx1, yf, C.dark, 7, 3.6);
      var cx = W / 2, aw = 28, ah = 25;
      var ad = 'M' + f(cx - aw / 2) + ' ' + f(yf) + 'V' + f(yf - ah + aw / 2) + 'A' + f(aw / 2) + ' ' + f(aw / 2) + ' 0 0 1 ' + f(cx + aw / 2) + ' ' + f(yf - ah + aw / 2) + 'V' + f(yf) + 'Z';
      s += P(ad, C.pave, C.stoneLt, 3) + L(ad, G, 0.8);
      s += P('M' + f(cx - aw / 2 + 1.5) + ' ' + f(yf - ah + aw / 2) + 'A' + f(aw / 2 - 1.5) + ' ' + f(aw / 2 - 1.5) + ' 0 0 1 ' + f(cx + aw / 2 - 1.5) + ' ' + f(yf - ah + aw / 2) + 'V' + f(yf - 10) + 'H' + f(cx - aw / 2 + 1.5) + 'Z', '#4a2a1c', null, 0, ' fill-opacity="0.55"');
      s += L('M' + f(cx - aw / 2 + 2) + ' ' + f(yf - 6) + 'H' + f(cx + aw / 2 - 2) + 'M' + f(cx - aw / 2 + 2) + ' ' + f(yf - 2.5) + 'H' + f(cx + aw / 2 - 2), C.stoneDk, 0.6, 0.7);
      s += K.plaque(cx, yf - ah - 4.5, 18, 6, { chars: 2, bg: C.red });
      // 台上楼阁
      var tf = yf - hb, tb = yb - hb;
      var hl = K.hall(28, W - 28, tb + 8, tf - 6, { double: true, h1: 20, h2: 16, inset: 6, skirt: 6,
        fac: { bays: 3, doors: [1], open: true, col: C.red, beam: C.teal, doorW: 18, doorH: 15 },
        upFac: { bays: 3, doors: [], win: 'lattice', sill: false, col: C.red, beam: C.teal },
        roof: { type: 'hip', tile: TILE.grey, ov: 6, up: 8, hr: 13, ridge: 'chiwen', hipK: 0.55, pearl: true } });
      s += hl.svg;
      // 楼下敞间里一面大鼓
      var dy = tf - 6 - 9;
      s += E(cx + 1.2, dy, 6, 6, C.red, GL, 0.6) + E(cx, dy, 6, 6, C.ochre, G, 0.8) + E(cx, dy, 3.6, 3.6, C.ochreLt);
      s += K.railing(bx0 + 3, bx1 - 3, tf - 1, 4, C.red);
      s += K.plaque(cx, tf - 6 - 5 - 20 - 7, 26, 7, { chars: 2, bg: C.navy });
      s += K.lantern(30, tf - 6 - 20 + 2, 2.6) + K.lantern(W - 30, tf - 6 - 20 + 2, 2.6);
      // 台下两侧货摊
      var gy = U + D - 4;
      s += carryPole(4, 14, gy, 3.6, [[C.teal, C.tealLt], [C.orange, C.ochre]]) + K.basket(W - 10, gy, 4.5, [C.orange, C.ochre]) + sacks(W - 26, gy - 1, 1);
      return s;
    }
  });

  // ====================== 酒楼 / 客栈 ======================
  /** 酒旗：高杆 + 横挑 + 长条青布酒旗，旗上一个圆标（暗示“酒”字），下沿锯齿。 */
  function wineFlag(x, yBase, top, w, h) {
    var s = L('M' + f(x) + ' ' + f(yBase) + 'V' + f(top), G, 3) + L('M' + f(x) + ' ' + f(yBase) + 'V' + f(top), C.umber, 2) +
      R(x - 3, yBase - 4, 6, 4, C.stone, G, 0.6) + E(x, top - 1.5, 1.8, 1.8, C.ochre, G, 0.6) +
      L('M' + f(x) + ' ' + f(top + 2) + 'H' + f(x - w - 4), C.umber, 1.4);
    s += K.banner(x - w - 2.5, top + 3, w, h, { col: C.navy, mark: 'circle' });
    // 旗边一道红牙边
    s += L('M' + f(x - w - 2.5) + ' ' + f(top + 3) + 'V' + f(top + 3 + h - 2), C.red, 1.2);
    return s;
  }
  /** 檐下一串灯笼。 */
  function lanternRow(x0, x1, y, n, r) {
    var s = L('M' + f(x0) + ' ' + f(y) + 'H' + f(x1), C.dark, 0.5, 0.7);
    for (var i = 0; i < n; i++) s += K.lantern(x0 + (x1 - x0) * (n === 1 ? 0.5 : i / (n - 1)), y, r || 2.4);
    return s;
  }
  /** 一条长凳。 */
  function bench(x, y, w) {
    return K.box(x, x + w, y - 3, y - 1.5, 1.6, C.umberLt, C.umber, GL, 0.5) +
      L('M' + f(x + 1.5) + ' ' + f(y) + 'V' + f(y - 3) + 'M' + f(x + w - 1.5) + ' ' + f(y) + 'V' + f(y - 3), C.umber, 1);
  }
  /** 三层楼阁：每层退进 ins，层间腰檐；返回 { svg, roof }。 */
  function tower3(x0, x1, yb, yf, o) {
    var h1 = o.h1, h2 = o.h2, h3 = o.h3, i = o.inset || 4, sk = o.skirt || 6, ro = o.roof, s = '';
    var skirt = function (a0, a1, gf, hh, ins) {
      return K.roof(a0, a1, gf - 14 + 2 * sk, gf, hh, { type: 'hip', tile: ro.tile, ov: (ro.ov || 5) + 1, up: ro.up, hr: sk, inset: ins, noBack: true }).svg;
    };
    s += K.facade(x0, x1, yf, h1, o.fac1);
    s += K.facade(x0 + i, x1 - i, yf - 5 - h1, h2 + 2, o.fac2);
    s += skirt(x0, x1, yf, h1, i + 2);
    s += K.railing(x0 + i + 1, x1 - i - 1, yf - 5 - h1 + 0.5, 3.6, C.red);
    s += K.facade(x0 + 2 * i, x1 - 2 * i, yf - 10 - h1 - h2, h3 + 2, o.fac3);
    s += skirt(x0 + i, x1 - i, yf - 5, h1 + h2, i + 2);
    s += K.railing(x0 + 2 * i + 1, x1 - 2 * i - 1, yf - 10 - h1 - h2 + 0.5, 3.6, C.red);
    var r = K.roof(x0 + 2 * i, x1 - 2 * i, yb + 6, yf - 10, h1 + h2 + h3, ro);
    return { svg: s + r.svg, roof: r };
  }

  defs.push({
    kind: 'inn', variant: 1, name: '酒楼', facility: 'inn', category: 'special', fp: [3, 2], up: 88,
    tags: ['two_storey', 'tavern', 'wine_flag', 'lanterns'], roof: 'hip_tile',
    note: '两层临街酒楼：楼下三间敞门（柜台、酒坛），楼上格扇窗 + 平座栏杆，腰檐 + 歇山灰瓦；右侧高杆挑青布酒旗，檐下一串红灯笼；门前酒坛、长凳。',
    draw: function (K, W, U, D) {
      var s = '', x0 = 10, x1 = W - 22, yb = U + 8, yf = U + 66, h1 = 26, h2 = 22;
      s += K.shadow(x0, x1, yb, yf, 9);
      s += K.pave(2, yf - 2, W - 2, U + D - 1, 12);
      var hl = K.hall(x0, x1, yb, yf, { double: true, h1: h1, h2: h2, inset: 3, skirt: 6,
        fac: { bays: 3, doors: [0, 1, 2], open: true, col: C.red, beam: C.teal, doorW: 26, doorH: 21 },
        upFac: { bays: 3, doors: [], win: 'lattice', sill: false, col: C.red, beam: C.teal },
        roof: { type: 'hip', tile: TILE.grey, ov: 6, up: 8, hr: 14, ridge: 'chiwen', hipK: 0.5 } });
      s += hl.svg;
      // 铺里柜台与酒坛
      s += K.box(x0 + 6, x0 + 30, yf - 9, yf - 4, 8, C.umberLt, C.umber, GL, 0.6) + K.jar(x0 + 46, yf - 4, 4, C.umberLt) + K.jar(x0 + 56, yf - 4, 4, C.red) + K.jar(x0 + 80, yf - 4, 4.5, C.umberLt);
      var upBase = yf - 5 - h1;
      s += K.railing(x0 + 3, x1 - 3, upBase + 1, 4, C.red);
      s += K.plaque((x0 + x1) / 2, upBase - h2 + 9, 34, 8.5, { chars: 3, bg: C.navy });
      s += lanternRow(x0 + 4, x1 - 4, yf - h1 + 1.5, 4, 2.6);
      s += wineFlag(W - 7, U + D - 4, U - 6, 10, 34);
      var gy = U + D - 4;
      s += K.jar(12, gy, 5, C.umberLt) + K.jar(23, gy + 0.5, 5, C.red) + K.jar(17, gy - 6, 4, C.umberLt) + bench(48, gy, 30) + K.jar(92, gy, 4.5, C.umberLt);
      return s;
    }
  });

  defs.push({
    kind: 'inn', variant: 2, name: '三层客栈楼', facility: 'inn', category: 'special', fp: [3, 2], up: 128,
    tags: ['three_storey', 'lodging', 'tavern', 'wine_flag', 'lanterns', 'landmark'], roof: 'hip_tile',
    note: '三层客栈：底层敞门大堂，二三层客房格扇窗、层层腰檐与平座栏杆，青绿歇山顶；左侧酒旗杆，檐角挂灯笼，门前竖招牌与拴马桩。',
    draw: function (K, W, U, D) {
      var s = '', x0 = 22, x1 = W - 8, yb = U + 8, yf = U + 66;
      s += K.shadow(x0, x1, yb, yf, 10);
      s += K.pave(2, yf - 2, W - 2, U + D - 1, 12);
      var tw = tower3(x0, x1, yb, yf, { h1: 26, h2: 21, h3: 20, inset: 4, skirt: 6,
        fac1: { bays: 3, doors: [1], open: true, col: C.red, beam: C.teal, doorW: 26, doorH: 20, win: 'straight' },
        fac2: { bays: 3, doors: [], win: 'lattice', sill: false, col: C.red, beam: C.teal },
        fac3: { bays: 3, doors: [], win: 'lattice', sill: false, col: C.red, beam: C.teal },
        roof: { type: 'hip', tile: TILE.teal, ov: 6, up: 9, hr: 14, ridge: 'chiwen', hipK: 0.5 } });
      s += tw.svg;
      s += K.plaque((x0 + x1) / 2, yf - 26 + 8.5, 30, 7.5, { chars: 2, bg: C.navy });
      s += K.lantern(x0 - 2, yf - 26 - 2, 2.6) + K.lantern(x1 + 2, yf - 26 - 2, 2.6) + K.lantern(x0 + 2, yf - 58, 2.4) + K.lantern(x1 - 2, yf - 58, 2.4);
      // 左侧酒旗（旗挂在杆右侧）
      var px = 8;
      s += L('M' + f(px) + ' ' + f(U + D - 4) + 'V' + f(U - 30), G, 3) + L('M' + f(px) + ' ' + f(U + D - 4) + 'V' + f(U - 30), C.umber, 2) +
        E(px, U - 31.5, 1.8, 1.8, C.ochre, G, 0.6) + R(px - 3, U + D - 8, 6, 4, C.stone, G, 0.6) + L('M' + f(px) + ' ' + f(U - 28) + 'H' + f(px + 14), C.umber, 1.4) +
        K.banner(px + 2.5, U - 27, 9, 34, { col: C.red, mark: 'circle' });
      var gy = U + D - 4;
      s += signBoard(30, gy, 20, C.navy) + K.jar(52, gy, 4.5, C.umberLt) + K.jar(62, gy + 0.4, 4.5, C.umberLt) + bench(80, gy, 28) +
        L('M' + f(W - 12) + ' ' + f(gy) + 'V' + f(gy - 12), C.stoneDk, 3) + E(W - 12, gy - 12, 1.8, 1.2, C.stoneLt, G, 0.5);
      return s;
    }
  });

  // ====================== 马厩 / 驿站配件 ======================
  /** 一匹马（侧身，头朝 dir）。(x, y) = 两前后蹄之间的地面中点。 */
  function horse(x, y, s, dir, col) {
    s = s || 1; dir = dir || 1; col = col || C.umberLt;
    var dk = K.mix(col, '#000000', 0.3), o = E(x + 2 * s, y + 0.4, 9 * s, 1.8 * s, K.SH, null, 0, ' fill-opacity="0.2"');
    var legs = '';
    [-5.5, -3.5, 4, 6].forEach(function (lx) { legs += 'M' + f(x + dir * lx * s) + ' ' + f(y - 6 * s) + 'V' + f(y); });
    o += L(legs, G, 2.6 * s) + L(legs, dk, 1.6 * s);
    o += E(x, y - 8.5 * s, 8 * s, 3.8 * s, col, G, 0.8);                                                   // 躯干
    o += P('M' + f(x + dir * 5 * s) + ' ' + f(y - 10 * s) + 'L' + f(x + dir * 8.5 * s) + ' ' + f(y - 17 * s) + 'L' + f(x + dir * 12.5 * s) + ' ' + f(y - 15 * s) +
      'L' + f(x + dir * 12 * s) + ' ' + f(y - 13 * s) + 'L' + f(x + dir * 9 * s) + ' ' + f(y - 13 * s) + 'L' + f(x + dir * 8 * s) + ' ' + f(y - 8 * s) + 'Z', col, G, 0.8); // 颈与头
    o += L('M' + f(x + dir * 5.5 * s) + ' ' + f(y - 11 * s) + 'L' + f(x + dir * 8.6 * s) + ' ' + f(y - 17.4 * s), dk, 1.4 * s);            // 鬃
    o += L('M' + f(x - dir * 7.6 * s) + ' ' + f(y - 9.5 * s) + 'Q' + f(x - dir * 10.5 * s) + ' ' + f(y - 7 * s) + ' ' + f(x - dir * 9.6 * s) + ' ' + f(y - 3 * s), dk, 1.4 * s); // 尾
    o += K.dots([[x + dir * 10.4 * s, y - 15.3 * s]], C.dark, 1 * s);
    o += P('M' + f(x - 2.5 * s) + ' ' + f(y - 12 * s) + 'H' + f(x + 2.5 * s) + 'V' + f(y - 8 * s) + 'H' + f(x - 2.5 * s) + 'Z', C.red, GL, 0.4);   // 鞍褥
    return o;
  }
  /** 石马槽：长条石槽，槽里草料。 */
  function manger(x0, x1, y) {
    return K.box(x0, x1, y - 5, y, 5, C.stoneLt, C.stone, G, 0.7) + R(x0 + 1.5, y - 9.4, x1 - x0 - 3, 3, TILE.thatch.fill, G, 0.4) +
      L('M' + f(x0 + 3) + ' ' + f(y - 9) + 'l3 -2m4 2l2 -2.5m5 2.5l3 -2m4 2l2 -2', TILE.thatch.dark, 0.6);
  }
  /** 一垛草料（草垛）。 */
  function hay(cx, y, r) {
    return E(cx + 2, y + 0.5, r * 1.1, r * 0.3, K.SH, null, 0, ' fill-opacity="0.2"') +
      P('M' + f(cx - r) + ' ' + f(y) + 'Q' + f(cx - r) + ' ' + f(y - r * 1.4) + ' ' + f(cx) + ' ' + f(y - r * 1.5) + 'Q' + f(cx + r) + ' ' + f(y - r * 1.4) + ' ' + f(cx + r) + ' ' + f(y) + 'Z', TILE.thatch.fill, G, 0.7) +
      L('M' + f(cx - r * 0.7) + ' ' + f(y - r * 0.5) + 'Q' + f(cx) + ' ' + f(y - r * 0.3) + ' ' + f(cx + r * 0.7) + ' ' + f(y - r * 0.5) + 'M' + f(cx - r * 0.5) + ' ' + f(y - r * 1.05) + 'Q' + f(cx) + ' ' + f(y - r * 0.9) + ' ' + f(cx + r * 0.5) + ' ' + f(y - r * 1.05), TILE.thatch.line, 0.7);
  }
  /** 拴马桩：石柱顶一个小狮头。 */
  function hitch(x, y) {
    return R(x - 1.8, y - 14, 3.6, 14, C.stoneLt, G, 0.6) + E(x, y - 15, 2.4, 2, C.stone, G, 0.6) + L('M' + f(x - 1.8) + ' ' + f(y - 9) + 'H' + f(x + 1.8), C.stoneDk, 0.6);
  }

  defs.push({
    kind: 'stable', variant: 1, name: '马厩', facility: 'stable', category: 'special', fp: [3, 2], up: 56,
    tags: ['open_front', 'animals', 'hay'], roof: 'gable_tile',
    note: '五间敞棚马厩：木柱 + 横栏隔出马位，棚下两匹马对着石马槽；悬山灰瓦；右侧草垛，前院拴马桩、水桶。',
    draw: function (K, W, U, D) {
      var s = '', x0 = 6, x1 = W - 30, yb = U + 6, yF = U + 60, h = 26;
      s += K.shadow(x0, x1, yb, yF, 8);
      s += K.pave(2, yF - 2, W - 2, U + D - 1, 14, C.stoneLt);
      var inner = R(x0, yF - h, x1 - x0, h - 3, '#7a4a30') + R(x0, yF - 7, x1 - x0, 7, TILE.thatch.dark) + manger(x0 + 4, x1 - 4, yF - 15);
      inner += horse(x0 + 26, yF - 4, 1.05, -1, C.umberLt) + horse(x0 + 70, yF - 4, 1.05, -1, C.wallLt);
      var bays = 5, bw = (x1 - x0) / bays, rail = '';
      for (var i = 1; i < bays; i++) rail += 'M' + f(x0 + i * bw) + ' ' + f(yF) + 'V' + f(yF - h);
      inner += L(rail, C.umber, 2.2);
      inner += L('M' + f(x0) + ' ' + f(yF - 9) + 'H' + f(x1), C.umber, 1.6) + L('M' + f(x0) + ' ' + f(yF - 9) + 'H' + f(x1), C.umberLt, 0.7);
      s += K.pavilion(x0, x1, yb, yF, h, { post: C.umber, roof: { type: 'gable', tile: TILE.grey, ov: 5, up: 4, hr: 11, ridge: 'plain' } }, inner).svg;
      s += hay(W - 15, yF - 8, 11) + hay(W - 22, yF + 4, 8);
      var gy = U + D - 4;
      s += hitch(20, gy) + hitch(56, gy) + K.basket(80, gy, 4, null) + K.jar(98, gy, 4, C.navyLt);
      return s;
    }
  });

  defs.push({
    kind: 'caravanserai', variant: 1, name: '驿站', facility: 'caravanserai', category: 'special', fp: [4, 3], up: 72,
    tags: ['compound', 'courtyard', 'post_station', 'animals', 'lodging'], roof: 'gable_tile',
    note: '官驿院落：前为门屋（门上「驿」字匾、两侧灯笼、驿旗），白墙环院；院内左侧马棚与石马槽、两匹驿马，右侧草垛与货车，后为五间客房正屋。',
    draw: function (K, W, U, D) {
      var s = '', yf = U + D;
      s += K.shadow(6, W - 6, U + 6, U + 132, 10);
      s += K.pave(4, U + 6, W - 4, yf - 1, 14);
      // 后正屋
      s += K.platform(24, W - 24, U + 8, U + 56, 4);
      s += K.hall(28, W - 28, U + 8, U + 52, { h: 24, fac: { bays: 5, doors: [2], col: C.red, beam: C.teal, win: 'lattice' },
        roof: { type: 'gable', tile: TILE.grey, ov: 5, up: 5, hr: 12, ridge: 'swallow' } }).svg;
      // 左马棚（敞棚）
      var inner = R(10, U + 92 - 20, 58, 17, '#7a4a30') + manger(14, 64, U + 86) + horse(30, U + 91, 0.95, 1, C.umberLt) + horse(54, U + 91, 0.95, 1, C.wallLt);
      s += K.pavilion(10, 68, U + 66, U + 92, 20, { post: C.umber, roof: { type: 'gable', tile: TILE.grey, ov: 4, up: 4, hr: 8, ridge: 'plain' } }, inner).svg;
      // 右：草垛 + 板车
      s += hay(W - 30, U + 88, 11) + hay(W - 50, U + 92, 7);
      s += K.box(W - 82, W - 56, U + 98, U + 104, 6, C.umberLt, C.umber, GL, 0.6) + E(W - 76, U + 105, 5, 5, C.umber, GL, 0.7) + E(W - 76, U + 105, 1.4, 1.4, C.ochre) +
        L('M' + f(W - 56) + ' ' + f(U + 101) + 'L' + f(W - 44) + ' ' + f(U + 106), C.umber, 1.4) + sacks(W - 78, U + 98, 3);
      // 院墙 + 门屋
      s += K.sideWall(6, U + 20, U + 136, 15) + K.sideWall(W - 6, U + 20, U + 136, 15);
      s += K.yardWall(5, 68, U + 136, 15) + K.yardWall(W - 68, W - 5, U + 136, 15);
      var g0 = 68, g1 = W - 68, gF = U + 138, gh = 24;
      s += K.platform(g0 - 2, g1 + 2, gF - 22, gF + 3, 3);
      s += R(g0, gF - gh, g1 - g0, gh, C.wall, G, 1) + R(g0, gF - 3, g1 - g0, 3, C.stone, G, 0.6);
      s += K.door((g0 + g1) / 2 - 10, gF - 20, 20, 17.5, { open: true });
      s += R(g0, gF - gh, 2.6, gh - 3, C.red, GL, 0.5) + R(g1 - 2.6, gF - gh, 2.6, gh - 3, C.red, GL, 0.5) + R(g0, gF - gh, g1 - g0, 3, C.teal, GL, 0.6);
      s += K.roof(g0, g1, gF - 22, gF, gh, { type: 'gable', tile: TILE.grey, ov: 5, up: 5, hr: 9, ridge: 'swallow' }).svg;
      s += K.plaque((g0 + g1) / 2, gF - 22.5, 14, 6.5, { chars: 1, bg: C.navy });
      s += K.lantern(g0 + 4, gF - gh + 3, 2.6) + K.lantern(g1 - 4, gF - gh + 3, 2.6);
      s += L('M' + f(g1 + 14) + ' ' + f(yf - 3) + 'V' + f(U + 66), G, 3) + L('M' + f(g1 + 14) + ' ' + f(yf - 3) + 'V' + f(U + 66), C.umber, 2) +
        P('M' + f(g1 + 15) + ' ' + f(U + 67) + 'H' + f(g1 + 34) + 'L' + f(g1 + 29) + ' ' + f(U + 73) + 'L' + f(g1 + 34) + ' ' + f(U + 79) + 'H' + f(g1 + 15) + 'Z', C.ochre, G, 0.7) +
        L('M' + f(g1 + 19) + ' ' + f(U + 71) + 'h6M' + f(g1 + 22) + ' ' + f(U + 69.5) + 'v7', C.red, 0.9);
      s += hitch(g0 - 10, yf - 3) + hitch(20, yf - 3);
      return s;
    }
  });

  // ====================== 粮仓 ======================
  /** 圆仓：石台 + 圆筒仓身（夯土抹灰、竹篾箍）+ 圆锥草顶 + 顶尖葫芦；仓身正面一个小仓门与木梯。(cx, y) = 仓底前中点；r 半径，h 仓身高。 */
  function roundBin(cx, y, r, h, o) {
    o = o || {};
    var k = 0.42, s = '', T = o.tile || TILE.thatch;
    s += E(cx + r * 0.5, y + 1, r * 1.15, r * k * 0.8, K.SH, null, 0, ' fill-opacity="0.2"');
    // 石台
    s += P('M' + f(cx - r - 2) + ' ' + f(y - r * k) + 'V' + f(y - r * k + 4) + 'A' + f(r + 2) + ' ' + f((r + 2) * k) + ' 0 0 0 ' + f(cx + r + 2) + ' ' + f(y - r * k + 4) + 'V' + f(y - r * k) + 'Z', C.stone, G, 0.8);
    s += E(cx, y - r * k, r + 2, (r + 2) * k, C.stoneLt, G, 0.8);
    var by = y - r * k - 1;
    // 仓身
    s += P('M' + f(cx - r) + ' ' + f(by - h) + 'V' + f(by) + 'A' + f(r) + ' ' + f(r * k) + ' 0 0 0 ' + f(cx + r) + ' ' + f(by) + 'V' + f(by - h) + 'Z', o.wall || C.wall, G, 1);
    s += P('M' + f(cx + r * 0.35) + ' ' + f(by - h + r * k * 0.9) + 'V' + f(by + r * k * 0.9) + 'A' + f(r) + ' ' + f(r * k) + ' 0 0 0 ' + f(cx + r) + ' ' + f(by) + 'V' + f(by - h) + 'Z', C.stone, null, 0, ' fill-opacity="0.55"');
    var hoops = '';
    for (var i = 1; i <= 3; i++) { var yy = by - h * i / 4; hoops += 'M' + f(cx - r) + ' ' + f(yy) + 'A' + f(r) + ' ' + f(r * k) + ' 0 0 0 ' + f(cx + r) + ' ' + f(yy); }
    s += L(hoops, C.umberLt, 1, 0.85);
    // 仓门 + 梯
    var dw = r * 0.42, dy = by - h * 0.78 + r * k;
    s += R(cx - dw / 2, dy, dw, h * 0.26, C.umber, GL, 0.7) + L('M' + f(cx) + ' ' + f(dy) + 'v' + f(h * 0.26), GL, 0.5);
    var lx = cx - dw * 0.2, lb = y - 0.5, lt = dy + h * 0.26, rung = '';
    for (var j = lb - 3; j > lt + 1; j -= 3.4) rung += 'M' + f(lx - 3.2) + ' ' + f(j) + 'h6.4';
    s += L('M' + f(lx - 3.2) + ' ' + f(lb) + 'L' + f(lx - 2.6) + ' ' + f(lt) + 'M' + f(lx + 3.2) + ' ' + f(lb) + 'L' + f(lx + 2.6) + ' ' + f(lt) + rung, C.umber, 1);
    // 锥顶：底边是一段压扁的椭圆弧（前半），檐口出挑
    var rr = r + 4, ey = by - h + 1.5, apex = ey - (o.cone || r * 1.15);
    s += P('M' + f(cx - rr) + ' ' + f(ey) + 'A' + f(rr) + ' ' + f(rr * k) + ' 0 0 0 ' + f(cx + rr) + ' ' + f(ey) + 'L' + f(cx) + ' ' + f(apex) + 'Z', T.fill, G, 1.1);
    s += P('M' + f(cx - rr) + ' ' + f(ey) + 'L' + f(cx) + ' ' + f(apex) + 'L' + f(cx - rr * 0.25) + ' ' + f(ey + rr * k * 0.97) + 'A' + f(rr) + ' ' + f(rr * k) + ' 0 0 1 ' + f(cx - rr) + ' ' + f(ey) + 'Z', T.lite, null, 0);
    var st = '';
    for (var a = -0.9; a <= 0.91; a += 0.15) { var ex = cx + Math.sin(a * Math.PI / 2) * rr, eyy = ey + Math.cos(a * Math.PI / 2) * rr * k; st += 'M' + f(cx + (ex - cx) * 0.18) + ' ' + f(apex + (eyy - apex) * 0.18) + 'L' + f(ex) + ' ' + f(eyy - 0.8); }
    s += L(st, T.line, 0.6, 0.7);
    s += L('M' + f(cx - rr) + ' ' + f(ey) + 'A' + f(rr) + ' ' + f(rr * k) + ' 0 0 0 ' + f(cx + rr) + ' ' + f(ey), T.ridge, 2.2) + L('M' + f(cx - rr) + ' ' + f(ey) + 'A' + f(rr) + ' ' + f(rr * k) + ' 0 0 0 ' + f(cx + rr) + ' ' + f(ey), GL, 0.6);
    s += P('M' + f(cx - rr) + ' ' + f(ey) + 'A' + f(rr) + ' ' + f(rr * k) + ' 0 0 0 ' + f(cx + rr) + ' ' + f(ey) + 'L' + f(cx) + ' ' + f(apex) + 'Z', null, G, 1.1);
    // 顶尖：草扎宝顶
    s += E(cx, apex + 1, 2.6, 1.6, T.ridge, GL, 0.6) + E(cx, apex - 2.4, 2, 2.4, C.ochre, G, 0.6) + L('M' + f(cx) + ' ' + f(apex - 4.8) + 'v-3', C.umber, 1);
    return s;
  }

  defs.push({
    kind: 'granary', variant: 1, name: '圆仓粮囤', facility: 'granary', category: 'special', fp: [3, 2], up: 64,
    tags: ['storage', 'round_bin', 'thatch'], roof: 'gable_thatch',
    note: '三座石台圆仓（夯土抹灰仓身、竹篾箍、圆锥草顶 + 宝顶，正面小仓门搭木梯）一字排开；前院麻袋、斗、扫帚。圆锥草顶在 RoofId 里没有，记最近的 gable_thatch。',
    draw: function (K, W, U, D) {
      var s = '';
      s += K.pave(2, U + 20, W - 2, U + D - 1, 14, C.stoneLt);
      s += roundBin(30, U + 66, 18, 30, {}) + roundBin(W - 30, U + 66, 18, 30, {});
      s += roundBin(W / 2, U + 74, 21, 36, { cone: 26 });
      var gy = U + D - 4;
      s += sacks(10, gy, 3) + sacks(W - 30, gy, 3);
      // 量斗
      s += P(K.pts([[54, gy - 7], [66, gy - 7], [64, gy], [56, gy]]), C.umberLt, G, 0.7) + E(60, gy - 7, 6, 1.6, C.ochreLt, G, 0.5) + fruitPileGrain(60, gy - 7);
      return s;
    }
  });
  /** 斗里一小撮谷子。 */
  function fruitPileGrain(cx, y) { return P('M' + f(cx - 5) + ' ' + f(y) + 'Q' + f(cx) + ' ' + f(y - 4) + ' ' + f(cx + 5) + ' ' + f(y) + 'Z', C.ochre, G, 0.5); }

  defs.push({
    kind: 'granary', variant: 2, name: '官仓廒间', facility: 'granary', category: 'special', fp: [4, 2], up: 60,
    tags: ['storage', 'raised_floor', 'official'], roof: 'gable_tile',
    note: '官府廒间：长条五间仓房架在石墩上防潮（墩间露出暗空），墙上一排气窗，悬山灰瓦、屋脊开气楼；正中门上「仓」字匾，门前斛斗、麻袋垛与粮车。',
    draw: function (K, W, U, D) {
      var s = '', x0 = 10, x1 = W - 10, yb = U + 8, yf = U + 66, h = 30, pier = 7;
      s += K.shadow(x0, x1, yb, yf, 9);
      s += K.pave(2, yf - 3, W - 2, U + D - 1, 14);
      // 石墩层
      s += R(x0, yf - pier, x1 - x0, pier, '#4a2a1c');
      for (var px = x0; px <= x1 - 5; px += (x1 - x0 - 6) / 8) s += R(px, yf - pier, 6, pier, C.stone, G, 0.6);
      var wy = yf - pier;
      s += R(x0 - 1, wy - 2, x1 - x0 + 2, 2.4, C.umber, GL, 0.6);
      // 墙
      s += R(x0, wy - h, x1 - x0, h - 2, C.wall, G, 1.1);
      var bays = 5, bw = (x1 - x0) / bays;
      for (var i = 0; i < bays; i++) {
        var bx = x0 + i * bw;
        if (i === 2) s += K.door(bx + bw / 2 - 10, wy - 22, 20, 20, { col: C.red });
        else for (var v = 0; v < 2; v++) s += lat(bx + bw * (0.22 + v * 0.36), wy - h + 6);
      }
      for (var j = 0; j <= bays; j++) s += R(x0 + j * bw - 1.3, wy - h, 2.6, h - 2, C.umber, GL, 0.5);
      s += R(x0, wy - h, x1 - x0, 3, C.teal, GL, 0.6);
      var rf = K.roof(x0, x1, yb, wy, h, { type: 'gable', tile: TILE.grey, ov: 6, up: 5, hr: 13, ridge: 'swallow' });
      s += rf.svg;
      // 气楼：屋脊上一段小屋顶
      var qx0 = W / 2 - 26, qx1 = W / 2 + 26;
      s += R(qx0, rf.ridgeY - 7, qx1 - qx0, 5, C.dark, G, 0.6) + L('M' + f(qx0 + 3) + ' ' + f(rf.ridgeY - 4.5) + 'H' + f(qx1 - 3), C.stoneDk, 2.4, 0.8);
      s += K.roof(qx0, qx1, rf.ridgeY - 12, rf.ridgeY - 4, 4, { type: 'gable', tile: TILE.grey, ov: 3, up: 3, hr: 4, ridge: 'plain', ridgeH: 1.6 }).svg;
      s += K.plaque(W / 2, wy - h + 8.5, 14, 6.5, { chars: 1, bg: C.navy });
      var gy = U + D - 4;
      s += sacks(14, gy, 4) + sacks(18, gy - 7, 3) + crate(W - 60, gy, 12, 8);
      s += K.box(W - 42, W - 18, gy - 8, gy - 4, 5, C.umberLt, C.umber, GL, 0.6) + sacks(W - 38, gy - 9, 3) + E(W - 34, gy - 2, 4.4, 4.4, C.umber, GL, 0.7) + E(W - 34, gy - 2, 1.2, 1.2, C.ochre);
      return s;
    }
  });
  /** 气窗：一小方直棂窗。 */
  function lat(x, y) { return K.lattice(x - 5, y, 10, 7, { straight: true, step: 2.4 }); }

  // ====================== 水车磨坊 ======================
  /**
   * 筒车：大木轮，辐条 + 双圈轮辋，轮缘一圈竹筒（取水）；轮下半截浸在水渠里（水渠画在前面盖住）。
   * (cx, cy) 轮心；r 半径；n 辐条数。
   */
  function noria(cx, cy, r, n) {
    var s = '', i, sp = '', tubes = [];
    for (i = 0; i < n; i++) { var a = i / n * Math.PI * 2; sp += 'M' + f(cx) + ' ' + f(cy) + 'L' + f(cx + Math.cos(a) * r) + ' ' + f(cy + Math.sin(a) * r); }
    s += L(sp, G, 2.6) + L(sp, C.umber, 1.5);
    s += E(cx, cy, r, r, null, G, 3.4) + E(cx, cy, r, r, null, C.umberLt, 2.2) + E(cx, cy, r * 0.82, r * 0.82, null, C.umber, 1.4);
    for (i = 0; i < n * 2; i++) {
      var b = (i + 0.5) / (n * 2) * Math.PI * 2, tx = cx + Math.cos(b) * (r + 2), ty = cy + Math.sin(b) * (r + 2);
      tubes.push('<g transform="rotate(' + f(b * 180 / Math.PI + 90) + ' ' + f(tx) + ' ' + f(ty) + ')">' + R(tx - 1.4, ty - 3.2, 2.8, 6.4, BAMBOO, G, 0.5) + '</g>');
    }
    s += tubes.join('');
    // 水花：右上方几只竹筒往外倾水
    s += L('M' + f(cx + r * 0.55) + ' ' + f(cy - r * 0.9) + 'q3 4 2 10M' + f(cx + r * 0.8) + ' ' + f(cy - r * 0.6) + 'q3 4 1 9', C.tealLt, 1.1, 0.9);
    s += E(cx, cy, 4, 4, C.umber, GL, 0.8) + E(cx, cy, 1.6, 1.6, C.ochre);
    return s;
  }
  /** 水渠：一条从左到右的蓝色水带，上沿金线 + 两道水纹，带石砌岸。 */
  function channel(x0, x1, y0, y1) {
    var s = R(x0, y0 - 3, x1 - x0, 3, C.stone, G, 0.7) + R(x0, y0, x1 - x0, y1 - y0, C.navyLt, G, 0.8);
    var d = '';
    for (var k = 0; k < 2; k++) {
      var yy = y0 + (y1 - y0) * (0.35 + k * 0.35);
      d += 'M' + f(x0 + 2) + ' ' + f(yy);
      for (var x = x0 + 2; x < x1 - 8; x += 10) d += 'q2.5 -2 5 0t5 0';
    }
    return s + L(d, C.tealLt, 0.8, 0.9) + L('M' + f(x0) + ' ' + f(y0 + 0.6) + 'H' + f(x1), GL, 0.7);
  }
  /** 石磨：两扇磨盘 + 推杆。 */
  function millstone(cx, y, r) {
    return E(cx + 2, y + 0.6, r * 1.2, r * 0.36, K.SH, null, 0, ' fill-opacity="0.2"') +
      K.box(cx - r, cx + r, y - r * 0.5, y, 3, C.stoneLt, C.stone, G, 0.6) +
      E(cx, y - 5, r * 0.85, r * 0.32, C.stoneLt, G, 0.7) + R(cx - r * 0.85, y - 5, r * 1.7, 2.6, C.stone, G, 0.5) + E(cx, y - 5, r * 0.85, r * 0.32, C.stoneLt, G, 0.6) +
      E(cx - r * 0.3, y - 5, 1.2, 0.6, C.dark) + L('M' + f(cx + r * 0.5) + ' ' + f(y - 5) + 'L' + f(cx + r * 1.7) + ' ' + f(y - 7), C.umber, 1.4);
  }

  defs.push({
    kind: 'mill', variant: 1, name: '水车磨坊', facility: 'mill', category: 'special', fp: [3, 2], up: 60,
    tags: ['water_power', 'noria', 'workshop'], roof: 'gable_tile',
    note: '临渠磨坊：左侧一架竹筒筒车（辐条 + 双圈轮辋 + 一圈竹筒，下半截浸在前方水渠里），轮轴伸进三间磨房；悬山灰瓦，敞门里露出石磨；门前麻袋。需放在水边，前沿一格内是水渠。',
    draw: function (K, W, U, D) {
      var s = '', x0 = 62, x1 = W - 8, yb = U + 8, yf = U + 66, h = 28;
      s += K.shadow(x0, x1, yb, yf, 8);
      s += K.pave(x0 - 4, yf - 3, W - 2, U + D - 18, 14);
      s += K.hall(x0, x1, yb, yf, { h: h, fac: { bays: 3, doors: [1], open: true, col: C.umber, beam: C.teal, doorW: 22, doorH: 20 },
        roof: { type: 'gable', tile: TILE.grey, ov: 5, up: 5, hr: 12, ridge: 'swallow' } }).svg;
      s += millstone((x0 + x1) / 2, yf - 4, 7);
      // 轴
      s += L('M30 ' + f(U + 64) + 'H' + f(x0 + 4), G, 3.4) + L('M30 ' + f(U + 64) + 'H' + f(x0 + 4), C.umber, 2.2);
      s += K.box(56, 64, U + 58, U + 70, 12, C.stoneLt, C.stone, G, 0.7);
      s += noria(30, U + 64, 26, 10);
      // 前方水渠盖住轮子下半截
      s += channel(0, W, U + 78, U + D - 2);
      s += sacks(x0 + 8, U + 76, 3) + sacks(x1 - 18, U + 76, 2);
      return s;
    }
  });

  defs.push({
    kind: 'mill', variant: 2, name: '碾坊', facility: 'mill', category: 'special', fp: [2, 2], up: 44,
    tags: ['animal_power', 'roller_mill', 'open_front'], roof: 'hip_tile',
    note: '畜力碾坊（mill 的变体，不靠水）：四柱攒尖草亭下一盘石碾——圆形碾盘 + 立轴 + 石碾滚，一头毛驴蒙眼拉碾；亭外谷堆与簸箕。',
    draw: function (K, W, U, D) {
      var s = '', cx = W / 2, cy = U + 52;
      s += K.pave(2, U + 8, W - 2, U + D - 1, 14, C.stoneLt);
      var inner = '';
      inner += K.box(cx - 24, cx + 24, cy - 14, cy, 4, C.stoneLt, C.stone, G, 0.8);
      inner += E(cx, cy - 11, 21, 8, C.stoneLt, G, 0.8) + E(cx, cy - 11, 14, 5, null, C.stoneDk, 0.6, ' stroke-dasharray="2 2"');
      inner += R(cx - 1.6, cy - 30, 3.2, 20, C.umber, GL, 0.6);
      inner += L('M' + f(cx) + ' ' + f(cy - 22) + 'L' + f(cx + 20) + ' ' + f(cy - 14), C.umber, 1.6);
      inner += K.box(cx + 4, cx + 14, cy - 14, cy - 10, 6, C.stone, C.stoneDk, G, 0.6);
      inner += horse(cx - 10, cy - 4, 0.75, -1, C.greyLt);
      s += K.pavilion(cx - 32, cx + 32, U + 16, cy + 2, 30, { post: C.umber, roof: { type: 'spire', tile: TILE.thatch, ov: 6, up: 6, hr: 18, finial: 6 } }, inner).svg;
      var gy = U + D - 4;
      s += fruitPileGrain(14, gy) + P('M' + f(W - 22) + ' ' + f(gy) + 'Q' + f(W - 14) + ' ' + f(gy - 6) + ' ' + f(W - 6) + ' ' + f(gy) + 'Z', C.ochreLt, G, 0.6) + sacks(28, gy, 2);
      return s;
    }
  });

  // —— 导出 ——
  var API = { defs: defs, bamboo: bamboo, canopy: canopy, sacks: sacks, crate: crate, carryPole: carryPole, signBoard: signBoard };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.TownArtEastSpecialTrade = API;
})(typeof window !== 'undefined' ? window : this);
