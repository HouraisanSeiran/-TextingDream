/*
 * 织梦 · 东方特殊建筑 · 工坊与衙署：打铁铺、县衙、府邸（美术素材，尚未接入游戏）
 * 每项 def：{ kind, variant, name, facility, category, fp:[w,d], up, tags, roof, note, draw(K, W, U, D) }
 * draw 在 viewBox 坐标里画：占地矩形 x 0..W、y U..U+D；不得画出前沿 U+D 以下（投影除外，≤6 px）。
 */
(function (root) {
  'use strict';
  var K = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtEastSpecialCore;
  var C = K.C, TILE = K.TILE, G = K.G, GL = K.GL, f = K.f, P = K.P, R = K.R, E = K.E, L = K.L;

  /** 铁砧：木墩 + 带角的铁砧身。(x, y) = 着地中点。 */
  function anvil(x, y, s) {
    s = s || 1;
    return E(x + 2 * s, y + 0.5, 7 * s, 2 * s, K.SH, null, 0, ' fill-opacity="0.2"') +
      P(K.pts([[x - 4 * s, y], [x - 3 * s, y - 7 * s], [x + 3 * s, y - 7 * s], [x + 4 * s, y]]), C.umber, GL, 0.7) +
      L('M' + f(x - 3.4 * s) + ' ' + f(y - 3.5 * s) + 'H' + f(x + 3.4 * s), C.umberLt, 0.6) +
      P('M' + f(x - 3 * s) + ' ' + f(y - 7 * s) + 'L' + f(x - 2 * s) + ' ' + f(y - 10 * s) + 'L' + f(x - 9 * s) + ' ' + f(y - 11 * s) +
        'Q' + f(x - 5 * s) + ' ' + f(y - 13.5 * s) + ' ' + f(x - 2 * s) + ' ' + f(y - 13.5 * s) + 'H' + f(x + 6 * s) + 'V' + f(y - 10.5 * s) +
        'L' + f(x + 3 * s) + ' ' + f(y - 10 * s) + 'L' + f(x + 3 * s) + ' ' + f(y - 7 * s) + 'Z', C.grey, GL, 0.8) +
      L('M' + f(x - 2 * s) + ' ' + f(y - 13 * s) + 'H' + f(x + 5.5 * s), C.greyLt, 0.8);
  }
  /** 铁锤斜靠在砧上。 */
  function hammer(x, y, s) {
    s = s || 1;
    return L('M' + f(x) + ' ' + f(y) + 'L' + f(x + 7 * s) + ' ' + f(y - 7 * s), C.umberLt, 1.4 * s) +
      P(K.pts([[x + 5 * s, y - 10 * s], [x + 8 * s, y - 11 * s], [x + 11 * s, y - 6 * s], [x + 8 * s, y - 5 * s]]), C.grey, GL, 0.6);
  }
  /** 木风箱：长方木箱 + 拉杆把手。(x, y) = 箱底左前角。 */
  function bellows(x, y, w, h) {
    return K.box(x, x + w, y - 5, y, h, C.umberLt, C.umber, GL, 0.7) +
      L('M' + f(x + 2) + ' ' + f(y - h * 0.5) + 'H' + f(x + w - 2), C.umberLt, 0.6, 0.8) +
      L('M' + f(x + w) + ' ' + f(y - h * 0.62) + 'h6M' + f(x + w) + ' ' + f(y - h * 0.38) + 'h6M' + f(x + w + 6) + ' ' + f(y - h * 0.75) + 'v' + f(h * 0.5), C.dark, 1.1) +
      R(x + w + 5, y - h * 0.8, 2.2, h * 0.6, C.ochre, GL, 0.4);
  }
  /** 砖砌火炉：方炉身 + 炉口火光 + 炉顶火苗。 */
  function furnace(x0, x1, y, h, o) {
    o = o || {};
    var cx = (x0 + x1) / 2, w = x1 - x0;
    var s = K.box(x0, x1, y - 8, y, h, C.brick, C.umberLt, G, 0.9) + K.bricks(x0, y - h, x1, y, C.dark, 5, 3);
    s += P('M' + f(cx - w * 0.22) + ' ' + f(y - 1) + 'V' + f(y - h * 0.45) + 'Q' + f(cx) + ' ' + f(y - h * 0.75) + ' ' + f(cx + w * 0.22) + ' ' + f(y - h * 0.45) + 'V' + f(y - 1) + 'Z', C.dark, GL, 0.7);
    s += K.fire(cx, y - 1.5, w * 0.17);
    if (o.top !== false) s += E(cx, y - h - 4, w * 0.3, 2, C.dark, GL, 0.6) + K.fire(cx, y - h - 4, w * 0.16);
    return s;
  }
  /** 淬火水桶。 */
  function tub(x, y, r) {
    return E(x + 1.5, y + 0.5, r * 1.1, r * 0.35, K.SH, null, 0, ' fill-opacity="0.2"') +
      P('M' + f(x - r) + ' ' + f(y - r * 1.2) + 'L' + f(x - r * 0.85) + ' ' + f(y) + 'H' + f(x + r * 0.85) + 'L' + f(x + r) + ' ' + f(y - r * 1.2) + 'Z', C.umberLt, G, 0.7) +
      L('M' + f(x - r * 0.95) + ' ' + f(y - r * 0.85) + 'H' + f(x + r * 0.95) + 'M' + f(x - r * 0.88) + ' ' + f(y - r * 0.3) + 'H' + f(x + r * 0.88), C.dark, 0.8) +
      E(x, y - r * 1.2, r, r * 0.35, C.navyLt, G, 0.6) + E(x - r * 0.2, y - r * 1.25, r * 0.45, r * 0.12, C.tealLt);
  }
  /** 兵器 / 农具架：横杆上竖挂几件铁器。 */
  function rack(x0, x1, y, h, items) {
    var s = L('M' + f(x0) + ' ' + f(y) + 'V' + f(y - h) + 'M' + f(x1) + ' ' + f(y) + 'V' + f(y - h), C.umber, 1.6) + L('M' + f(x0 - 1) + ' ' + f(y - h + 1) + 'H' + f(x1 + 1), C.umber, 1.4);
    var n = items.length, gap = (x1 - x0) / (n + 1);
    items.forEach(function (it, i) {
      var x = x0 + gap * (i + 1), t = y - h + 2;
      if (it === 'sword') s += L('M' + f(x) + ' ' + f(t) + 'V' + f(t + h * 0.75), C.greyLt, 1.3) + L('M' + f(x - 2) + ' ' + f(t + 3) + 'h4', C.ochre, 1) + L('M' + f(x) + ' ' + f(t) + 'v3', C.red, 1.2);
      else if (it === 'hoe') s += L('M' + f(x) + ' ' + f(t) + 'V' + f(t + h * 0.6), C.umberLt, 1) + P(K.pts([[x - 3, t + h * 0.6], [x + 3, t + h * 0.6], [x + 2, t + h * 0.6 + 4], [x - 2, t + h * 0.6 + 4]]), C.grey, GL, 0.5);
      else if (it === 'sickle') s += L('M' + f(x) + ' ' + f(t) + 'v5', C.umberLt, 1.1) + L('M' + f(x) + ' ' + f(t + 5) + 'q4 2 1 7', C.greyLt, 1.2);
      else s += L('M' + f(x) + ' ' + f(t) + 'V' + f(t + h * 0.7), C.umberLt, 1) + P('M' + f(x - 2) + ' ' + f(t) + 'L' + f(x) + ' ' + f(t - 5) + 'L' + f(x + 2) + ' ' + f(t) + 'Z', C.greyLt, GL, 0.4);
    });
    return s;
  }
  /** 砖烟囱 + 炉烟。(x, y) = 烟囱底（压在屋面上）；返回烟囱与烟。 */
  function chimney(x, y, w, h, seed) {
    return K.box(x, x + w, y - h - 3, y - h, 0, C.dark, C.brick, G, 0.8) + R(x, y - h, w, h, C.brick, G, 0.9) + K.bricks(x, y - h, x + w, y, C.dark, 4, 3) +
      R(x - 1, y - h - 2, w + 2, 2.6, C.umber, GL, 0.6) + K.smoke(x + w / 2, y - h - 6, 8, seed);
  }

  var defs = [];
  /** 一小摞铁料（条铁）。 */
  function ironBars(x, y) {
    var s = '';
    for (var i = 0; i < 3; i++) s += R(x + i * 1.5, y - 3 - i * 2.4, 14 - i * 3, 2.4, i % 2 ? C.greyLt : C.grey, GL, 0.5);
    return s;
  }
  /** 一堆木炭。 */
  function charcoal(cx, y, r) {
    var s = E(cx + 2, y + 0.5, r * 1.2, r * 0.35, K.SH, null, 0, ' fill-opacity="0.2"') +
      P('M' + f(cx - r * 1.2) + ' ' + f(y) + 'Q' + f(cx - r * 0.6) + ' ' + f(y - r * 1.1) + ' ' + f(cx) + ' ' + f(y - r) + 'Q' + f(cx + r * 0.7) + ' ' + f(y - r * 1.05) + ' ' + f(cx + r * 1.2) + ' ' + f(y) + 'Z', '#3b2a22', GL, 0.6);
    var d = [];
    for (var i = 0; i < 6; i++) d.push([cx - r * 0.7 + i * r * 0.28, y - r * (0.3 + (i % 3) * 0.2)]);
    return s + K.dots(d, '#6b5a50', 1.6);
  }
  /** 幌子杆：竖杆 + 横挑 + 布幌（幌子挂在杆左侧）。 */
  function flagPole(x, yBase, top, bw, bh, o) {
    return L('M' + f(x) + ' ' + f(yBase) + 'V' + f(top), C.umber, 1.8) + E(x, top, 1.4, 1.4, C.ochre, G, 0.5) +
      L('M' + f(x) + ' ' + f(top + 2.5) + 'H' + f(x - bw - 5), C.umber, 1.3) + K.banner(x - bw - 3.5, top + 3.2, bw, bh, o);
  }
  /** 长条淬火水槽。 */
  function trough(x0, x1, y) {
    return K.box(x0, x1, y - 5, y, 5, C.navyLt, C.umberLt, G, 0.7) + L('M' + f(x0 + 2) + ' ' + f(y - 8) + 'H' + f(x1 - 3), C.tealLt, 0.7, 0.9);
  }

  defs.push({
    kind: 'forge', variant: 1, name: '打铁铺', facility: 'forge', category: 'special', fp: [2, 2], up: 64,
    tags: ['open_front', 'workshop', 'smoke'], roof: 'gable_tile',
    note: '开敞铺面：砖炉炉火、木风箱、农具架；门前铁砧、淬火桶、条铁；右侧挑出布幌子。硬山灰瓦，炉烟囱穿出屋面。',
    draw: function (K, W, U, D) {
      var yf = U + D, x0 = 8, x1 = W - 10, yb = U + 4, yF = U + 58, h = 32, s = '';
      s += K.shadow(x0, x1 + 2, yb, yF, 8);
      s += K.pave(2, yF - 1, W - 2, yf - 1, 12);
      // 铺内：深色进深、后墙、地面、炉火映光
      s += R(x0, yF - h, x1 - x0, h, C.dark, G, 1.1) + R(x0 + 1, yF - h + 3, x1 - x0 - 2, h * 0.45, '#6a3d27') + R(x0 + 1, yF - 7, x1 - x0 - 2, 6, '#5c3624');
      s += E(x0 + 20, yF - 13, 20, 11, C.orange, null, 0, ' fill-opacity="0.3"');
      s += furnace(x0 + 7, x0 + 31, yF - 3, 19, { top: false });
      s += bellows(x0 + 34, yF - 3, 13, 9);
      s += rack(x1 - 24, x1 - 5, yF - 3, 21, ['hoe', 'sickle', 'spear']);
      [x0 + 1.4, (x0 + x1) / 2, x1 - 1.4].forEach(function (cx) { s += R(cx - 1.6, yF - h, 3.2, h - 2, C.umber, GL, 0.6); });
      s += R(x0, yF - 2.5, x1 - x0, 2.5, C.stone, G, 0.6);
      var rf = K.roof(x0, x1, yb, yF, h, { type: 'gable', tile: TILE.grey, ov: 5, up: 4, hr: 12, ridge: 'swallow' });
      s += rf.svg;
      s += chimney(x0 + 13, rf.ridgeY + 7, 9, 22, 11);
      s += K.plaque((x0 + x1) / 2 + 8, yF - h + 9.5, 28, 8, { chars: 3 });
      s += K.lantern(x0 + 5, yF - h + 4, 2.6);
      // 门前：条铁、铁砧与锤、淬火桶、幌子
      s += ironBars(10, yf - 7);
      s += anvil(W * 0.4, yf - 13, 1.05) + hammer(W * 0.4 + 5, yf - 11, 0.8);
      s += tub(W * 0.64, yf - 9, 5.5);
      s += flagPole(W - 4, yf - 4, U + 6, 8, 21, { col: C.navy, mark: true });
      return s;
    }
  });

  defs.push({
    kind: 'forge', variant: 2, name: '铁匠作坊（带铺面）', facility: 'forge', category: 'special', fp: [3, 2], up: 96,
    tags: ['open_front', 'workshop', 'smoke', 'shop'], roof: 'gable_tile',
    note: '左为敞棚锻打间（大砖炉、风箱、铁砧），后立高砖烟囱；右为兵器农具铺面，檐下挂刀枪架；院中炭堆、水槽、铁料。',
    draw: function (K, W, U, D) {
      var yf = U + D, s = '';
      var a0 = 6, a1 = 82, ab = U + 8, aF = U + 60, ah = 30;   // 锻打敞棚
      var b0 = 90, b1 = W - 6, bb = U + 14, bF = U + 60, bh = 30; // 铺面
      s += K.shadow(a0, b1, ab, bF, 9);
      s += K.pave(2, aF - 1, W - 2, yf - 1, 12);
      // 高砖烟囱立在棚后
      var cx0 = 16, cw = 13, ctop = U - 58;
      s += R(cx0, ctop, cw, ab - ctop, C.brick, G, 1) + K.bricks(cx0, ctop, cx0 + cw, ab, C.dark, 5, 3.4) +
        R(cx0 - 1.5, ctop - 3, cw + 3, 3.6, C.umber, GL, 0.7) + R(cx0 + 1, ctop - 5, cw - 2, 2.4, C.dark, G, 0.5) +
        L('M' + f(cx0 + cw - 2) + ' ' + f(ctop + 2) + 'V' + f(ab - 2), C.umber, 1.2, 0.55);
      s += K.smoke(cx0 + cw / 2, ctop - 9, 10, 23);
      var inner = R(a0, aF - ah, a1 - a0, ah - 5, '#6a3d27') + R(a0, aF - 6, a1 - a0, 6, '#8a6a4a') +
        E(a0 + 22, aF - 12, 22, 11, C.orange, null, 0, ' fill-opacity="0.32"') +
        furnace(a0 + 8, a0 + 36, aF - 3, 22, { top: false }) + bellows(a0 + 39, aF - 3, 12, 9) +
        anvil(a1 - 14, aF - 2, 1.1) + hammer(a1 - 9, aF, 0.85);
      s += K.pavilion(a0, a1, ab, aF, ah, { post: C.umber, roof: { type: 'gable', tile: TILE.grey, ov: 5, up: 4, hr: 11, ridge: 'plain' } }, inner).svg;
      // 铺面：两间格扇，一间开门，檐下刀枪架
      s += K.facade(b0, b1, bF, bh, { bays: 2, doors: [0], col: C.red, beam: C.teal });
      s += K.roof(b0, b1, bb, bF, bh, { type: 'gable', tile: TILE.grey, ov: 4, up: 5, hr: 12, ridge: 'swallow' }).svg;
      s += K.plaque((b0 + b1) / 2, bF - bh + 9, 30, 7.5, { chars: 3, bg: C.umber });
      s += rack(b0 + 30, b1 - 4, bF + 1, 20, ['sword', 'spear', 'sword', 'spear']);
      // 院里
      s += charcoal(18, yf - 10, 8) + trough(40, 68, yf - 7) + ironBars(76, yf - 6);
      s += K.lantern(b0 + 3, bF - bh + 3, 2.6) + K.lantern(b1 - 3, bF - bh + 3, 2.6);
      s += flagPole(W - 4, yf - 4, U - 4, 8, 22, { col: C.red, mark: true });
      return s;
    }
  });

  // ====================== 衙署配件 ======================
  /** 鸣冤鼓：鼓架（两柱 + 小坡顶）上横挂一面红鼓，鼓面朝前。(x, y) = 着地中点。 */
  function drum(x, y, s) {
    s = s || 1;
    var r = 6.5 * s, cy = y - 12 * s, top = y - 23 * s, o = '';
    o += E(x + 3 * s, y + 0.5, 10 * s, 2 * s, K.SH, null, 0, ' fill-opacity="0.2"');
    o += L('M' + f(x - 8.5 * s) + ' ' + f(y) + 'V' + f(top) + 'M' + f(x + 8.5 * s) + ' ' + f(y) + 'V' + f(top), G, 2.6 * s) +
      L('M' + f(x - 8.5 * s) + ' ' + f(y) + 'V' + f(top) + 'M' + f(x + 8.5 * s) + ' ' + f(y) + 'V' + f(top), C.red, 1.6 * s);
    o += L('M' + f(x - 8.5 * s) + ' ' + f(cy - r - 1) + 'H' + f(x + 8.5 * s), C.umber, 1.2 * s);
    // 鼓身：右侧露一道朱红鼓腔，正面鼓皮叠晕两圈，周边一圈鼓钉
    o += E(x + 1.6 * s, cy, r, r, C.red, GL, 0.7) + E(x, cy, r, r, C.ochre, G, 0.9) + E(x, cy, r * 0.7, r * 0.7, C.ochreLt) + E(x, cy, r * 0.38, r * 0.38, C.wallLt);
    var st = [];
    for (var i = 0; i < 10; i++) { var a = i / 10 * Math.PI * 2; st.push([x + Math.cos(a) * r * 0.86, cy + Math.sin(a) * r * 0.86]); }
    o += K.dots(st, C.umber, 0.9 * s);
    // 小坡顶
    o += P(K.pts([[x - 12 * s, top + 1], [x - 8 * s, top - 4 * s], [x + 8 * s, top - 4 * s], [x + 12 * s, top + 1]]), TILE.grey.fill, G, 0.7) +
      L('M' + f(x - 12.5 * s) + ' ' + f(top + 1) + 'Q' + f(x) + ' ' + f(top - 1) + ' ' + f(x + 12.5 * s) + ' ' + f(top + 1), TILE.grey.ridge, 1.4) +
      L('M' + f(x - 12 * s) + ' ' + f(top + 1) + 'l-1.5 -2.5M' + f(x + 12 * s) + ' ' + f(top + 1) + 'l1.5 -2.5', TILE.grey.ridge, 1.2);
    // 鼓槌斜插在架上
    o += L('M' + f(x + 7 * s) + ' ' + f(y - 3 * s) + 'L' + f(x + 12 * s) + ' ' + f(y - 13 * s) + 'M' + f(x + 9 * s) + ' ' + f(y - 2 * s) + 'L' + f(x + 13.5 * s) + ' ' + f(y - 11 * s), C.umberLt, 1.1 * s) +
      K.dots([[x + 12 * s, y - 13 * s], [x + 13.5 * s, y - 11 * s]], C.red, 2.2 * s);
    return o;
  }
  /** 石狮：须弥座 + 蹲坐的狮身、卷鬃头；dir = 狮头朝向（1 向右）。(x, y) = 座底前中点。 */
  function lion(x, y, s, dir) {
    s = s || 1; dir = dir || 1;
    var o = E(x + 2.5 * s, y + 0.4, 6 * s, 1.6 * s, K.SH, null, 0, ' fill-opacity="0.2"');
    o += K.box(x - 5 * s, x + 5 * s, y - 3 * s, y, 4 * s, C.stoneLt, C.stone, G, 0.6);
    var b = y - 4 * s, lc = C.stoneLt, dk = C.stoneDk;
    o += E(x - dir * 1.8 * s, b - 3.6 * s, 3.8 * s, 3.8 * s, lc, G, 0.7);                       // 后臀
    o += P('M' + f(x + dir * 0.2 * s) + ' ' + f(b) + 'L' + f(x + dir * 1 * s) + ' ' + f(b - 9 * s) + 'L' + f(x + dir * 4.2 * s) + ' ' + f(b - 8 * s) + 'L' + f(x + dir * 3.8 * s) + ' ' + f(b) + 'Z', lc, G, 0.7); // 前腿胸
    o += E(x + dir * 2 * s, b - 11 * s, 3.8 * s, 3.5 * s, lc, G, 0.8);                           // 头
    var cu = [];
    for (var i = 0; i < 7; i++) { var a = -Math.PI * 0.95 + i * 0.32; cu.push([x + dir * (2 * s + Math.cos(a) * -2.6 * s), b - 11 * s + Math.sin(a) * 2.4 * s]); }
    o += K.dots(cu, dk, 1.5 * s);
    o += K.dots([[x + dir * 3.6 * s, b - 11.4 * s]], C.dark, 1.1 * s) + L('M' + f(x + dir * 3 * s) + ' ' + f(b - 9.2 * s) + 'h' + f(dir * 2.2 * s), C.red, 0.8);
    o += E(x + dir * 4.4 * s, b - 1.4 * s, 1.5 * s, 1.4 * s, C.ochre, G, 0.5);                    // 绣球
    return o;
  }
  /** 照壁：须弥座 + 墙身 + 小庑殿瓦帽；中央菱形斗方，四角岔角。y = 座底。 */
  function screenWall(x0, x1, y, h, o) {
    o = o || {};
    var cx = (x0 + x1) / 2, wy = y - 3, s = '';
    s += E(x1 + 3, y + 0.3, 6, 1.6, K.SH, null, 0, ' fill-opacity="0.2"');
    s += R(x0 - 2, wy, x1 - x0 + 4, 3, C.stone, G, 0.6);
    s += R(x0, wy - h, x1 - x0, h, o.col || C.red, G, 0.9) + R(x0 + 3, wy - h + 3, x1 - x0 - 6, h - 5, o.panel || C.redLt, GL, 0.6);
    var m = h * 0.32, my = wy - h * 0.48;
    s += P(K.pts([[cx, my - m], [cx + m * 1.5, my], [cx, my + m], [cx - m * 1.5, my]]), C.wallLt, GL, 0.7) +
      E(cx, my, m * 0.55, m * 0.55, C.ochre, G, 0.6) + E(cx, my, m * 0.28, m * 0.28, C.red);
    [[x0 + 3, wy - h + 3, 1, 1], [x1 - 3, wy - h + 3, -1, 1], [x0 + 3, wy - 2, 1, -1], [x1 - 3, wy - 2, -1, -1]].forEach(function (c) {
      s += P(K.pts([[c[0], c[1]], [c[0] + c[2] * 6, c[1]], [c[0], c[1] + c[3] * 4]]), C.teal, GL, 0.4);
    });
    s += K.roof(x0, x1, wy - 4, wy, h, { type: 'hip', tile: o.tile || TILE.grey, ov: 3, up: 3, hr: 4, ridge: 'plain', ridgeH: 2, sp: 2.8 }).svg;
    return s;
  }
  /** 告示牌：两根立柱 + 白板墙（几行暗示字迹）+ 小坡顶。(x, y) = 着地中点。 */
  function notice(x, y, w, h) {
    var o = E(x + 3, y + 0.4, w * 0.6, 1.6, K.SH, null, 0, ' fill-opacity="0.2"');
    o += L('M' + f(x - w / 2) + ' ' + f(y) + 'V' + f(y - h - 4) + 'M' + f(x + w / 2) + ' ' + f(y) + 'V' + f(y - h - 4), C.umber, 1.8);
    o += R(x - w / 2 + 1, y - h - 2, w - 2, h * 0.62, C.wallLt, G, 0.7);
    var d = '';
    for (var i = 0; i < 4; i++) d += 'M' + f(x - w / 2 + 3 + i * (w - 6) / 4) + ' ' + f(y - h) + 'v' + f(h * 0.45);
    o += L(d, C.dark, 0.6, 0.6) + R(x + w / 2 - 6, y - h - 1, 3.2, 3.2, C.red);
    o += P(K.pts([[x - w / 2 - 3, y - h - 3], [x - w / 2, y - h - 7], [x + w / 2, y - h - 7], [x + w / 2 + 3, y - h - 3]]), TILE.grey.fill, G, 0.6) +
      L('M' + f(x - w / 2 - 3.5) + ' ' + f(y - h - 3) + 'H' + f(x + w / 2 + 3.5), TILE.grey.ridge, 1.2);
    return o;
  }
  /** 旗杆：细高杆 + 半腰方斗 + 顶端三角令旗。(x, y) = 杆脚。 */
  function mast(x, y, h, col) {
    return R(x - 3, y - 3, 6, 3, C.stone, G, 0.5) + L('M' + f(x) + ' ' + f(y - 2) + 'V' + f(y - h), C.red, 1.6) +
      P(K.pts([[x - 3.5, y - h * 0.62], [x + 3.5, y - h * 0.62], [x + 2.2, y - h * 0.62 + 3.5], [x - 2.2, y - h * 0.62 + 3.5]]), C.umber, GL, 0.5) +
      P('M' + f(x) + ' ' + f(y - h + 1) + 'L' + f(x + 11) + ' ' + f(y - h + 4) + 'L' + f(x) + ' ' + f(y - h + 8) + 'Z', col || C.ochre, GL, 0.6) +
      E(x, y - h, 1.3, 1.3, C.ochre, G, 0.4);
  }
  /** 八字墙：从门侧 (xi, yi) 斜向前方展开到 (xo, yo)，墙高 h；白墙心 + 灰瓦帽。 */
  function splayWall(xi, yi, xo, yo, h) {
    var T = TILE.grey;
    var s = P(K.pts([[xi, yi - h], [xo, yo - h * 0.85], [xo, yo], [xi, yi]]), C.wall, G, 0.9);
    var k = 0.22, mx0 = xi + (xo - xi) * k, mx1 = xi + (xo - xi) * (1 - k), my0 = yi + (yo - yi) * k, my1 = yi + (yo - yi) * (1 - k);
    s += P(K.pts([[mx0, my0 - h * 0.75], [mx1, my1 - h * 0.65], [mx1, my1 - h * 0.2], [mx0, my0 - h * 0.22]]), C.wallLt, GL, 0.5);
    s += P(K.pts([[xi, yi - 3], [xo, yo - 3], [xo, yo], [xi, yi]]), C.stone, G, 0.5);
    s += P(K.pts([[xi, yi - h - 3.5], [xo + (xo > xi ? 2 : -2), yo - h * 0.85 - 3.5], [xo + (xo > xi ? 2 : -2), yo - h * 0.85 + 0.8], [xi, yi - h + 0.8]]), T.fill, G, 0.7);
    return s + L('M' + f(xi) + ' ' + f(yi - h + 0.8) + 'L' + f(xo + (xo > xi ? 2 : -2)) + ' ' + f(yo - h * 0.85 + 0.8), T.ridge, 1.3);
  }

  /** 门屋：一座三间门楼，中间朱门、门上匀额，左右两间白墙。返回 svg。 */
  function gateHouse(x0, x1, yb, yf, h, o) {
    o = o || {};
    var cx = (x0 + x1) / 2, w = x1 - x0, s = '';
    s += K.platform(x0 - 2, x1 + 2, yb, yf + 3, 3);
    s += R(x0, yf - h, w, h, C.wall, G, 1);
    s += R(x0, yf - 3, w, 3, C.stone, G, 0.6);
    var dw = w * 0.36, dh = h * 0.72;
    s += R(cx - dw / 2 - 2, yf - dh - 2, dw + 4, dh + 2, C.dark, GL, 0.7);
    s += K.door(cx - dw / 2, yf - dh, dw, dh - 0.5, { col: o.doorCol || C.red });
    // 门当：门前两枚圆鼓石
    s += E(cx - dw / 2 - 3, yf - 3.5, 2.6, 3, C.stoneLt, G, 0.6) + E(cx + dw / 2 + 3, yf - 3.5, 2.6, 3, C.stoneLt, G, 0.6);
    [x0, cx - dw / 2 - 2, cx + dw / 2 + 2, x1].forEach(function (px) { s += R(px - 1.4, yf - h, 2.8, h - 3, o.col || C.red, GL, 0.5); });
    s += R(x0, yf - h, w, 3, o.beam || C.teal, GL, 0.6);
    var rf = K.roof(x0, x1, yb, yf, h, o.roof || { type: 'gable', tile: TILE.grey, ov: 5, up: 5, hr: 9, ridge: 'chiwen' });
    s += rf.svg;
    s += K.plaque(cx, yf - dh - 6, Math.min(w * 0.55, 30), 7, { chars: o.chars || 2, bg: o.plaqueBg || C.navy });
    if (o.lanterns !== false) s += K.lantern(x0 + 4, yf - h + 3, 2.6) + K.lantern(x1 - 4, yf - h + 3, 2.6);
    return s;
  }

  defs.push({
    kind: 'town_hall', variant: 1, name: '县衙', facility: 'town_hall', category: 'special', fp: [3, 3], up: 72,
    tags: ['compound', 'courtyard', 'administration'], roof: 'hip_tile',
    note: '一进院：前为三间大门（朱门门钉、门当、匀额），两侧八字墙，门前石狮一对；左前鸣冤鼓架、右前告示牌；院后五间大堂，歇山灰瓦。',
    draw: function (K, W, U, D) {
      var yf = U + D, s = '';
      s += K.shadow(6, W - 6, U + 6, U + 120, 9);
      s += K.pave(4, U + 6, W - 4, yf - 1, 12);
      // 大堂
      s += K.platform(14, W - 14, U + 8, U + 70, 5);
      s += K.steps(W / 2, U + 70, 20, 3);
      s += K.hall(18, W - 18, U + 8, U + 65, { h: 28, fac: { bays: 5, doors: [2], col: C.red, beam: C.teal, win: 'lattice' },
        roof: { type: 'hip', tile: TILE.grey, ov: 6, up: 6, hr: 14, ridge: 'chiwen', hipK: 0.55 } }).svg;
      s += K.plaque(W / 2, U + 65 - 28 + 8, 26, 7, { chars: 3 });
      // 院墙与大门
      s += K.sideWall(6, U + 22, U + 118, 16) + K.sideWall(W - 6, U + 22, U + 118, 16);
      s += K.yardWall(5, 48, U + 118, 16) + K.yardWall(W - 48, W - 5, U + 118, 16);
      s += gateHouse(48, W - 48, U + 98, U + 122, 25, { chars: 2 });
      s += splayWall(46, U + 122, 32, U + 134, 15) + splayWall(W - 46, U + 122, W - 32, U + 134, 15);
      s += lion(52, U + 137, 1, 1) + lion(W - 52, U + 137, 1, -1);
      s += drum(18, U + 141, 0.95) + notice(W - 17, U + 140, 20, 18);
      return s;
    }
  });

  defs.push({
    kind: 'town_hall', variant: 2, name: '州衙（照壁大院）', facility: 'town_hall', category: 'special', fp: [4, 3], up: 80,
    tags: ['compound', 'courtyard', 'administration', 'large'], roof: 'hip_tile',
    note: '门前一堵红照壁（菱形斗方、岔角），两根令旗杆；歇山顶大门 + 八字墙 + 石狮；院内东西厢房、重檐大堂；左侧鸣冤鼓。',
    draw: function (K, W, U, D) {
      var yf = U + D, s = '';
      s += K.shadow(6, W - 6, U + 6, U + 118, 10);
      s += K.pave(4, U + 6, W - 4, yf - 1, 12);
      // 重檐大堂
      s += K.platform(32, W - 32, U + 6, U + 66, 5);
      s += K.steps(W / 2, U + 66, 24, 3);
      s += K.hall(36, W - 36, U + 6, U + 61, { double: true, h1: 22, h2: 14, inset: 8, skirt: 6,
        fac: { bays: 5, doors: [2], col: C.red, beam: C.teal }, roof: { type: 'hip', tile: TILE.grey, ov: 6, up: 7, hr: 13, ridge: 'chiwen', hipK: 0.5 } }).svg;
      // 东西厢房（正对院子，只露山墙一侧的短立面）
      s += K.hall(10, 40, U + 58, U + 104, { h: 19, fac: { bays: 2, doors: [1], col: C.red, beam: C.teal }, roof: { type: 'gable', tile: TILE.grey, ov: 4, up: 4, hr: 9, ridge: 'plain' } }).svg;
      s += K.hall(W - 40, W - 10, U + 58, U + 104, { h: 19, fac: { bays: 2, doors: [0], col: C.red, beam: C.teal }, roof: { type: 'gable', tile: TILE.grey, ov: 4, up: 4, hr: 9, ridge: 'plain' } }).svg;
      // 院墙与大门
      s += K.sideWall(5, U + 20, U + 114, 16) + K.sideWall(W - 5, U + 20, U + 114, 16);
      s += K.yardWall(4, 68, U + 114, 16) + K.yardWall(W - 68, W - 4, U + 114, 16);
      s += gateHouse(68, W - 68, U + 92, U + 118, 27, { chars: 2, roof: { type: 'hip', tile: TILE.grey, ov: 6, up: 6, hr: 11, ridge: 'chiwen', hipK: 0.6 } });
      s += splayWall(66, U + 118, 52, U + 128, 15) + splayWall(W - 66, U + 118, W - 52, U + 128, 15);
      s += lion(72, U + 132, 1, 1) + lion(W - 72, U + 132, 1, -1);
      s += mast(46, U + 136, 66, C.red) + mast(W - 46, U + 136, 66, C.red);
      s += drum(20, U + 140, 1) + notice(W - 20, U + 139, 20, 18);
      s += screenWall(W / 2 - 22, W / 2 + 22, U + 143, 13);
      return s;
    }
  });

  defs.push({
    kind: 'lord_hall', variant: 1, name: '王府', facility: 'lord_hall', category: 'special', fp: [4, 3], up: 96,
    tags: ['compound', 'courtyard', 'residence', 'noble'], roof: 'hip_tile',
    note: '王府制式：绿琉璃瓦重檐正殿坐在高台基上，前有汉白玉样栏杆；五间府门朱门金钉、绿瓦；院中古树两株、石狮一对；红墙黄瓦帽。',
    draw: function (K, W, U, D) {
      var yf = U + D, s = '', red = C.red;
      s += K.shadow(6, W - 6, U + 4, U + 120, 10);
      s += K.pave(4, U + 4, W - 4, yf - 1, 12, '#ddd0ad');
      // 高台基 + 样栏杆
      s += K.platform(26, W - 26, U + 4, U + 74, 9);
      s += K.steps(W / 2, U + 74, 26, 4, 2);
      s += K.railing(26, W / 2 - 16, U + 66, 5, C.wallLt) + K.railing(W / 2 + 16, W - 26, U + 66, 5, C.wallLt);
      s += K.hall(34, W - 34, U + 6, U + 64, { double: true, h1: 24, h2: 16, inset: 9, skirt: 6,
        fac: { bays: 7, doors: [2, 3, 4], col: red, beam: C.teal, doorCol: red }, roof: { type: 'hip', tile: TILE.teal, ov: 7, up: 8, hr: 15, ridge: 'chiwen', hipK: 0.35, pearl: true } }).svg;
      s += K.plaque(W / 2, U + 64 - 24 - 9, 24, 7, { chars: 3, bg: C.navy });
      // 院中古树
      s += K.tree(16, U + 100, 11, 5) + K.tree(W - 16, U + 100, 11, 9);
      // 红墙黄瓦帽
      s += K.sideWall(5, U + 18, U + 114, 18, { tile: TILE.gold, col: red }) + K.sideWall(W - 5, U + 18, U + 114, 18, { tile: TILE.gold, col: red });
      s += K.yardWall(4, 58, U + 114, 18, { col: red, tile: TILE.gold }) + K.yardWall(W - 58, W - 4, U + 114, 18, { col: red, tile: TILE.gold });
      s += gateHouse(58, W - 58, U + 92, U + 118, 28, { chars: 2, plaqueBg: C.navy, roof: { type: 'hip', tile: TILE.teal, ov: 6, up: 7, hr: 12, ridge: 'chiwen', hipK: 0.6 } });
      s += lion(54, U + 134, 1.15, 1) + lion(W - 54, U + 134, 1.15, -1);
      s += K.lantern(30, U + 92, 3) + K.lantern(W - 30, U + 92, 3);
      return s;
    }
  });

  // —— 导出 ——
  var API = { defs: defs, anvil: anvil, furnace: furnace, banner: K.banner };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.TownArtEastSpecialCivic = API;
})(typeof window !== 'undefined' ? window : this);
