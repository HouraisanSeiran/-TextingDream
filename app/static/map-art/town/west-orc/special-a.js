/*
 * 织梦 · 兽人族特殊建筑 A 组（美术样板，尚未接入游戏）：铁匠铺 ×2、兽皮篷交易场、摊位 ×2、酋长大帐。
 * 局部坐标：x 0..w*48，y = 0 为占地前沿，向上为负。每项 draw(ctx) 返回 svg 片段。
 * 浏览器挂 window.TownArtWO_specialA；Node 用 module.exports。依赖 core.js、parts.js、forms.js、houses-a.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWO_core;
  var K = isNode ? require('./parts.js') : root.TownArtWO_parts;
  var F = isNode ? require('./forms.js') : root.TownArtWO_forms;
  var HA = isNode ? require('./houses-a.js') : root.TownArtWO_housesA;
  var P = C.PAL, f = C.f;
  if (!F.MAT.rubble) F.MAT.rubble = { a: P.stone, b: P.stone3, tex: function (ctx, x, y, w, h) { return K.texRubble(ctx, x, y, w, h, true); } };

  /** 踩实的土场 */
  function yard(ctx, cx, cy, rx, ry) {
    var s = C.path(C.ellD(cx, cy, rx, ry), P.soil, 0, 0.4), d = '';
    for (var i = 0; i < 10; i++) { var x = cx + ctx.rnd(-rx, rx) * 0.8, y = cy + ctx.rnd(-ry, ry) * 0.8; d += 'M' + f(x) + ' ' + f(y) + 'q1.5 -0.8 3 0'; }
    return s + C.line(d, 0.6, 0.35);
  }
  /** 小火苗：底中心 (cx, yb)，缩放 k */
  function flame(cx, yb, k) {
    k = k || 1;
    var d = 'M' + f(cx - 3.5 * k) + ' ' + f(yb) + 'q' + f(-0.5 * k) + ' ' + f(-5 * k) + ' ' + f(3 * k) + ' ' + f(-8.5 * k) + 'q0 ' + f(3 * k) + ' ' + f(2 * k) + ' ' + f(4 * k) +
      'q' + f(1.5 * k) + ' ' + f(-2 * k) + ' ' + f(1 * k) + ' ' + f(-4 * k) + 'q' + f(3 * k) + ' ' + f(4 * k) + ' ' + f(1 * k) + ' ' + f(8.5 * k) + 'Z';
    return C.path(d, P.fire, 0.7) + C.path('M' + f(cx - 1.5 * k) + ' ' + f(yb) + 'q0 ' + f(-3 * k) + ' ' + f(1.5 * k) + ' ' + f(-4.5 * k) + 'q1 ' + f(2.5 * k) + ' ' + f(0.5 * k) + ' ' + f(4.5 * k) + 'Z', P.fire2, 0);
  }
  /** 方体（粗石）：正面 + 右侧窄条 + 顶面 */
  function box(ctx, x0, x1, yb, h, dp, wdt, mat) {
    var s = C.groundShadow(x0, x1 + wdt, yb, yb - h - dp);
    s += F.facade(ctx, x0, x1, yb, h, mat || 'rubble') + F.sideStrip(ctx, x1, yb, h, dp, wdt);
    var t = C.poly([[x0, yb - h], [x1, yb - h], [x1 + wdt, yb - h - dp], [x0 + wdt, yb - h - dp]]);
    s += C.face(ctx, t, P.stone3, K.texRubble(ctx, x0, yb - h - dp - 2, x1 - x0 + wdt, dp + 4), 1.4);
    ctx.top(yb - h - dp);
    return s;
  }
  /** 粗石砧：一块粗石墩上架一只带角铁砧 */
  function anvil(ctx, cx, yb) {
    var s = C.shadowD(C.poly([[cx - 4, yb], [cx + 10, yb], [cx + 13, yb - 4], [cx + 11, yb - 12]]));
    s += F.facade(ctx, cx - 8, cx + 8, yb, 8, 'rubble');
    s += C.path(C.wob(ctx, [[cx - 8, yb - 8], [cx + 8, yb - 8], [cx + 10, yb - 13], [cx - 6, yb - 13]], 0.4), P.stone2, 1.3);
    s += C.path(C.poly([[cx - 2.5, yb - 10.5], [cx + 4.5, yb - 10.5], [cx + 3, yb - 14], [cx - 1, yb - 14]]), P.iron, 1);
    s += C.path('M' + f(cx - 10) + ' ' + f(yb - 15.5) + 'Q' + f(cx - 5) + ' ' + f(yb - 14) + ' ' + f(cx - 3) + ' ' + f(yb - 14) + 'H' + f(cx + 7) + 'V' + f(yb - 17.5) +
      'H' + f(cx - 3) + 'Q' + f(cx - 6) + ' ' + f(yb - 17.5) + ' ' + f(cx - 10) + ' ' + f(yb - 15.5) + 'Z', P.iron, 1.1);
    s += C.line('M' + f(cx - 3) + ' ' + f(yb - 17) + 'H' + f(cx + 6.5), 0.8, 1, P.iron2);
    // 搁在砧上的锤
    s += C.line('M' + f(cx + 1) + ' ' + f(yb - 18) + 'l9 -4', 1.8) + C.line('M' + f(cx + 1) + ' ' + f(yb - 18) + 'l9 -4', 0.7, 1, P.wood) +
      C.path(C.poly([[cx - 1, yb - 20], [cx + 2.5, yb - 21.5], [cx + 3.6, yb - 18], [cx + 0.2, yb - 16.6]]), P.iron, 0.8);
    ctx.top(yb - 23);
    return s;
  }
  /** 皮风箱：楔形皮囊 + 上下木板 + 铁嘴（朝右） */
  function bellows(ctx, x, yb) {
    var s = C.path('M' + f(x) + ' ' + f(yb - 1) + 'Q' + f(x) + ' ' + f(yb - 9) + ' ' + f(x + 7) + ' ' + f(yb - 9) + 'L' + f(x + 12) + ' ' + f(yb - 5) + 'L' + f(x + 7) + ' ' + f(yb - 0.5) + 'Z', P.hide3, 1);
    s += C.line('M' + f(x + 1) + ' ' + f(yb - 7) + 'Q' + f(x + 5) + ' ' + f(yb - 5) + ' ' + f(x + 9) + ' ' + f(yb - 5) + 'M' + f(x + 2) + ' ' + f(yb - 3) + 'Q' + f(x + 5) + ' ' + f(yb - 4) + ' ' + f(x + 9) + ' ' + f(yb - 4.6), 0.7, 0.7);
    s += C.line('M' + f(x - 3) + ' ' + f(yb - 9.5) + 'L' + f(x + 8) + ' ' + f(yb - 9) + 'M' + f(x - 3) + ' ' + f(yb - 0.5) + 'L' + f(x + 8) + ' ' + f(yb - 0.5), 1.8, 1, P.timber);
    s += C.line('M' + f(x + 12) + ' ' + f(yb - 5) + 'h5', 1.8, 1, P.iron);
    return s;
  }
  /** 淬火水槽 */
  function trough(ctx, x0, x1, yb) {
    var s = F.facade(ctx, x0, x1, yb, 6, 'plank');
    s += C.path(C.poly([[x0, yb - 6], [x1, yb - 6], [x1 + 3, yb - 10], [x0 + 3, yb - 10]]), '#5f6870', 1.1);
    s += C.line('M' + f(x0 + 6) + ' ' + f(yb - 8) + 'h5M' + f(x0 + 15) + ' ' + f(yb - 8.5) + 'h4', 0.7, 0.6, '#c9d0d4');
    return s + C.line('M' + f(x1 - 4) + ' ' + f(yb - 9) + 'l6 -10M' + f(x1 - 2) + ' ' + f(yb - 9) + 'l5 -10', 1.1, 1, P.iron); // 斜靠的火钳
  }
  /** 兵器架：两柱一横杆，横杆下挂一排粗刀斧 */
  function weaponRack(ctx, x0, x1, yb, h, kinds) {
    var s = K.pole(x0, yb, h, 2.4) + K.pole(x1, yb, h, 2.4), bar = 'M' + f(x0 - 2) + ' ' + f(yb - h + 2) + 'H' + f(x1 + 2);
    s += C.line(bar, 2.8) + C.line(bar, 1.2, 1, P.wood) + K.knot(x0, yb - h + 1.5, 2.4, 2) + K.knot(x1, yb - h + 1.5, 2.4, 2);
    s += hangRow(x0 + 2, x1 - 2, yb - h + 2, h * 0.5, kinds);
    ctx.top(yb - h - 2);
    return s;
  }
  function hangRow(x0, x1, y, L, kinds) {
    var s = '', n = kinds.length;
    kinds.forEach(function (k, i) { var x = x0 + (x1 - x0) * (i + 0.5) / n; s += C.line('M' + f(x) + ' ' + f(y) + 'v2', 0.8) + K.weapon(k, x, y + 2, L); });
    return s;
  }

  var S = [];
  /** 兽皮篷布面：pts 四角（左前、右前、右后、左后），tone 'L'|'D' */
  function sheet(ctx, pts, dark) {
    var d = C.wob(ctx, pts, 0.6), xs = pts.map(function (p) { return p[0]; }), ys = pts.map(function (p) { return p[1]; });
    var x0 = Math.min.apply(null, xs), y0 = Math.min.apply(null, ys);
    var tex = K.texHide(ctx, x0 - 2, y0 - 2, Math.max.apply(null, xs) - x0 + 4, Math.max.apply(null, ys) - y0 + 4, dark ? K.HIDE_D : K.HIDE_L);
    // 前缘一条翻边
    var fr = 'M' + f(pts[0][0]) + ' ' + f(pts[0][1]) + 'L' + f(pts[1][0]) + ' ' + f(pts[1][1]);
    return C.face(ctx, d, P.hide, tex, 1.6) + C.line(fr, 3, 1) + C.line(fr, 1.4, 1, P.hide2);
  }
  /** 炉口：拱门洞 + 火 */
  function mouth(ctx, cx, yb, w, h) { return F.door(ctx, cx, yb, w, h, 'arch', false) + flame(cx, yb - 0.5, w / 9); }

  // 铁匠铺 01：露天炉坑（粗石炉台 + 顶面炭床 + 石烟囱）+ 兽皮遮篷下的粗石砧，篷檐挂满粗刀斧
  S.push({
    id: 'west-orc-forge-01', name: '露天铁匠场', kind: 'orc_forge_open', facility: 'forge', fp: [2, 2], roof: 'monopitch',
    tags: ['open_air', 'smithy', 'hide', 'rubble'], note: '兽皮单坡遮篷 + 露天粗石炉台',
    draw: function (ctx) {
      var s = yard(ctx, 48, -44, 46, 40);
      // 后排：粗石炉台 + 烟囱
      s += box(ctx, 8, 40, -50, 18, 12, 6);
      s += C.face(ctx, C.wob(ctx, [[30, -76], [42, -76], [41, -114], [31, -114]], 0.7), P.stone2, K.texRubble(ctx, 29, -116, 15, 42, true), 1.6);
      s += C.rect(29, -118, 14, 4, P.stone3, 1.3) + C.ell(36, -118, 5, 1.6, P.hole, 0.8);
      s += K.hornSkull(36, -104, 0.6, 7);
      ctx.top(-120);
      s += C.ell(20, -74, 10, 4, P.hole, 1.1) + C.line('M13 -74h3M18 -72.6h4M24 -75h3', 1.4, 1, P.rust) + flame(19, -73, 1.05);
      s += mouth(ctx, 22, -50, 11, 11);
      s += bellows(ctx, 44, -51);
      // 右侧兽皮遮篷：前柱 + 篷面 + 篷檐挂兵器
      s += anvil(ctx, 70, -24);
      s += sheet(ctx, [[50, -48], [92, -50], [90, -84], [54, -82]], false);
      s += K.pole(53, -12, 37, 2.6) + K.pole(89, -12, 39, 2.6) + K.knot(53, -47, 2.6, 2) + K.knot(89, -49, 2.6, 2);
      s += hangRow(57, 86, -48, 9, ['cleaver', 'axe', 'club', 'axe']);
      s += K.skull(71, -51, 0.55);
      ctx.top(-86);
      // 前排：兵器架 + 淬火水槽
      s += weaponRack(ctx, 8, 32, -6, 24, ['axe', 'spear', 'cleaver']);
      s += trough(ctx, 36, 52, -5);
      return s;
    }
  });

  // 铁匠铺 02：2×1 粗石半墙铁匠棚——兽皮单坡顶架在原木柱上，右侧粗石蜂巢炼炉，炉口火光，前沿粗石砧
  S.push({
    id: 'west-orc-forge-02', name: '粗石炼炉棚', kind: 'orc_forge_shed', facility: 'forge', fp: [2, 1], roof: 'monopitch', variant: 2,
    tags: ['smithy', 'rubble', 'hide', 'furnace'], note: '单坡兽皮顶棚 + 蜂巢形粗石炼炉',
    draw: function (ctx) {
      var s = C.groundShadow(4, 92, -4, -44);
      s += F.facade(ctx, 6, 62, -32, 16, 'rubble');
      s += C.rect(8, -36, 52, 28, P.soil, 0, 0.35);
      // 炼炉：粗石圆筒 + 粗石锥顶 + 顶口
      s += F.cylinder(ctx, 78, -18, 13, 9, 16, 'rubble');
      s += F.cone(ctx, 78, -34, 13, 9, 20, 'rubble', 1);
      s += C.ell(79, -52, 3.5, 1.6, P.hole, 1) + C.line('M77 -55q-1 -3 1 -5M81 -56q1 -2 0 -4', 0.9, 0.5);
      s += mouth(ctx, 78, -10, 9, 10) + K.hornSkull(78, -27, 0.55, 7);
      ctx.top(-60);
      s += bellows(ctx, 54, -9);
      // 单坡顶 + 前柱
      s += sheet(ctx, [[2, -40], [64, -42], [62, -64], [6, -62]], true);
      s += K.pole(6, -6, 34, 2.6) + K.pole(60, -6, 36, 2.6) + K.knot(6, -38, 2.6, 2) + K.knot(60, -40, 2.6, 2);
      s += hangRow(10, 56, -40, 8, ['axe', 'cleaver', 'spear', 'axe', 'cleaver']);
      ctx.top(-66);
      s += anvil(ctx, 28, -4);
      return s;
    }
  });

  /** 一捆叠放的毛皮（前沿 yb，左 x） */
  function furPile(ctx, x, yb, w) {
    var s = '', tones = [P.hide, P.hide2, P.hide3, '#a8825a'];
    for (var i = 0; i < 3; i++) {
      var y = yb - i * 3.2, ww = w - i * 2;
      s += C.path(C.wob(ctx, [[x + i, y], [x + i + ww, y], [x + i + ww - 1, y - 3.4], [x + i + 1, y - 3.4]], 0.4), tones[(i + ctx.int(0, 3)) % 4], 0.9);
    }
    return s + C.line('M' + f(x + 2) + ' ' + f(yb - 8) + 'l2 -1.4l2 1.4', 0.7, 0.7);
  }
  /** 陶罐 */
  function pot(cx, yb, r, fill) {
    return C.path('M' + f(cx - r * 0.6) + ' ' + f(yb) + 'Q' + f(cx - r * 1.3) + ' ' + f(yb - r) + ' ' + f(cx - r * 0.5) + ' ' + f(yb - r * 1.7) + 'H' + f(cx + r * 0.5) +
      'Q' + f(cx + r * 1.3) + ' ' + f(yb - r) + ' ' + f(cx + r * 0.6) + ' ' + f(yb) + 'Z', fill || P.tile, 0.9) +
      C.ell(cx, yb - r * 1.7, r * 0.5, r * 0.18, P.hole, 0.7) + C.line('M' + f(cx - r * 0.9) + ' ' + f(yb - r * 0.9) + 'h' + f(r * 1.8), 0.6, 0.6);
  }
  /** 晾挂的干肉条 / 干鱼一排（横杆 y） */
  function dryLine(ctx, x0, x1, y) {
    var s = K.rope('M' + f(x0) + ' ' + f(y) + 'Q' + f((x0 + x1) / 2) + ' ' + f(y + 3) + ' ' + f(x1) + ' ' + f(y)), d = '';
    for (var x = x0 + 3; x < x1 - 2; x += 4) {
      var yy = y + 1.5 + 3 * Math.sin(Math.PI * (x - x0) / (x1 - x0));
      s += C.path('M' + f(x - 1) + ' ' + f(yy) + 'h2l-0.4 ' + f(ctx.rnd(4, 6)) + 'h-1.2Z', ctx.pick([P.rust, P.hide2, '#a0603d']), 0.6);
    }
    return s + d;
  }
  /** 摊棚：两根前柱 + 兽皮小篷 + 货台；x0..x1，前沿 yb */
  function stall(ctx, x0, x1, yb, h, dark, goods) {
    var s = C.groundShadow(x0, x1, yb, yb - 22);
    s += F.facade(ctx, x0 + 1, x1 - 1, yb - 1, 7, 'plank');
    s += C.path(C.poly([[x0 + 1, yb - 8], [x1 - 1, yb - 8], [x1 + 1, yb - 13], [x0 + 3, yb - 13]]), P.wood, 1.1);
    if (goods === 'fur') s += furPile(ctx, x0 + 3, yb - 9.5, (x1 - x0) * 0.45) + pot(x1 - 6, yb - 9.5, 2.6);
    else if (goods === 'pots') s += pot(x0 + 6, yb - 9.5, 2.8) + pot(x0 + 12, yb - 9.5, 2.2, P.stone2) + pot(x1 - 7, yb - 9.5, 3, P.tile);
    else s += K.skull(x0 + 7, yb - 12, 0.55) + K.horn(x0 + 13, yb - 10.5, 6, 1, 0.5) + furPile(ctx, x1 - 13, yb - 9.5, 9);
    s += K.pole(x0 + 2, yb - 1, h, 2.2) + K.pole(x1 - 2, yb - 1, h, 2.2);
    s += sheet(ctx, [[x0 - 2, yb - h + 2], [x1 + 2, yb - h + 1], [x1, yb - h - 14], [x0 + 1, yb - h - 13]], dark);
    s += K.knot(x0 + 2, yb - h + 1, 2.2, 2) + K.knot(x1 - 2, yb - h, 2.2, 2);
    ctx.top(yb - h - 15);
    return s;
  }

  // 市场：3×2 兽皮篷交易场——中央一根高图腾柱挂旗，四座兽皮篷摊围一圈，前沿留出通道，场心篝火
  S.push({
    id: 'west-orc-market-01', name: '兽皮篷交易场', kind: 'orc_market', facility: 'market_hall', fp: [3, 2], roof: 'none',
    tags: ['open_air', 'market', 'hide', 'totem'], note: '露天交易场，篷顶是兽皮遮阳篷',
    draw: function (ctx) {
      var s = yard(ctx, 72, -46, 68, 40);
      // 后排两座长篷
      s += stall(ctx, 6, 50, -62, 24, true, 'pots') + stall(ctx, 94, 138, -64, 24, false, 'fur');
      s += dryLine(ctx, 50, 94, -86) + K.pole(50, -62, 26, 2) + K.pole(94, -64, 26, 2);
      // 中央图腾柱 + 篝火坑 + 旗
      s += K.totem(ctx, 66, -48, 9, 56, 'wings');
      s += K.firepit(ctx, 92, -38, 7, true);
      s += K.banner(ctx, 58, -46, 50, P.rust, -1);
      // 前排两座小篷，中间留通道
      s += stall(ctx, 4, 44, -6, 22, false, 'bone') + stall(ctx, 100, 140, -6, 22, true, 'fur');
      s += furPile(ctx, 52, -10, 12) + pot(86, -8, 3, P.stone2);
      return s;
    }
  });
  // 摊位 prop ×2：1×1 兽皮小篷摊（open_air）
  [['west-orc-stall-01', '毛皮摊', 'fur', false], ['west-orc-stall-02', '骨角陶器摊', 'pots', true]].forEach(function (a, i) {
    S.push({
      id: a[0], name: a[1], kind: 'orc_stall', facility: 'market_hall', category: 'prop', fp: [1, 1], roof: 'none', variant: i + 1,
      tags: ['open_air', 'stall', 'hide'], note: '露天摊位，可散放在交易场或路边',
      draw: function (ctx) { return stall(ctx, 6, 42, -6, i ? 24 : 21, a[3], i ? (ctx.chance(0.5) ? 'pots' : 'bone') : 'fur'); }
    });
  });

  /** 头骨王座门：粗木门框 + 门楣一排头骨 + 顶上大长角兽头骨 + 两侧獠牙 */
  function skullGate(ctx, cx, yb, w, h) {
    var s = '', x0 = cx - w / 2, x1 = cx + w / 2;
    s += F.door(ctx, cx, yb, w, h, 'rect', false);
    s += K.pole(x0 - 2, yb, h + 6, 4, P.dark) + K.pole(x1 + 2, yb, h + 6, 4, P.dark);
    s += C.path(C.wob(ctx, [[x0 - 6, yb - h - 2], [x1 + 6, yb - h - 3], [x1 + 5, yb - h - 8], [x0 - 5, yb - h - 7]], 0.5), P.timber, 1.4);
    var n = Math.max(3, Math.round(w / 6));
    for (var i = 0; i < n; i++) s += K.skull(x0 - 2 + (w + 4) * (i + 0.5) / n, yb - h - 3.2, 0.5);
    s += K.hornSkull(cx, yb - h - 12, 1, 14);
    s += K.tusk(x0 - 4, yb - 2, 12, -1) + K.tusk(x1 + 4, yb - 2, 12, 1);
    s += K.knot(x0 - 2, yb - h * 0.5, 4, 3) + K.knot(x1 + 2, yb - h * 0.5, 4, 3);
    ctx.top(yb - h - 26);
    return s;
  }

  // 行政厅：3×3 酋长大帐——主体是大型圆顶兽皮帐，前接原木门廊与头骨王座门，两侧图腾柱，战旗、篝火坑
  S.push({
    id: 'west-orc-town-hall-01', name: '酋长大帐', kind: 'orc_chieftain_hall', facility: 'town_hall', fp: [3, 3], roof: 'none',
    tags: ['chieftain', 'hide', 'dome', 'totem', 'banner'], note: '圆顶大兽皮帐 + 原木门廊，RoofId 无对应写 none',
    draw: function (ctx) {
      var s = yard(ctx, 72, -60, 68, 52);
      // 后侧两座小附帐
      s += F.dome(ctx, 22, -104, 16, 11, 22, { mat: 'hide2', ribs: 3, bands: 1, smoke: false });
      s += F.dome(ctx, 124, -106, 15, 10, 20, { mat: 'hide2', ribs: 3, bands: 1, smoke: false });
      // 主帐
      s += F.dome(ctx, 72, -76, 50, 34, 74, { mat: 'hide', ribs: 7, bands: 3 });
      s += K.boneString(ctx, 34, -86, 72, -128, 6) + K.boneString(ctx, 72, -128, 110, -86, 6);
      // 门廊：粗石基座 + 原木立柱 + 兽皮坡顶
      s += F.facade(ctx, 46, 98, -30, 5, 'rubble');
      s += K.pole(48, -30, 26, 3.4) + K.pole(96, -30, 26, 3.4);
      s += F.roofFront(ctx, { x0: 44, x1: 100, yE: -54, R: 18, Dp: 14, mat: 'hide', ov: 3 }).svg;
      s += skullGate(ctx, 72, -30, 18, 20);
      // 门前台阶
      s += C.path(C.poly([[60, -24], [84, -24], [86, -30], [58, -30]]), P.stone2, 1.2) + C.path(C.poly([[56, -18], [88, -18], [86, -24], [58, -24]]), P.stone, 1.2);
      // 两侧图腾柱、战旗、篝火
      s += K.totem(ctx, 24, -20, 10, 62, 'skull') + K.totem(ctx, 112, -20, 10, 62, 'wings');
      s += K.banner(ctx, 8, -8, 54, P.rust, 1) + K.banner(ctx, 138, -8, 54, P.rust, -1);
      s += K.firepit(ctx, 40, -12, 7, true) + K.firepit(ctx, 104, -12, 7, true);
      return s;
    }
  });

  var API = { S: S, yard: yard, flame: flame, box: box, anvil: anvil, bellows: bellows, trough: trough, weaponRack: weaponRack, hangRow: hangRow,
    sheet: sheet, mouth: mouth, furPile: furPile, pot: pot, dryLine: dryLine, stall: stall, skullGate: skullGate };
  root.TownArtWO_specialA = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
