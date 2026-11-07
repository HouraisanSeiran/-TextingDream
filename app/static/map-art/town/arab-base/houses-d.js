/*
 * 织梦 · 阿拉伯民居 D：拱廊铺面住宅（下店上宅）、贝都因黑帐篷（美术样板，尚未接入游戏）
 * 浏览器挂 window.TownArtAB_housesD；Node 用 module.exports。依赖 core.js、parts.js、parts2.js、kit.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  function dep(file, name) { return isNode ? require(file) : root[name]; }
  var C = dep('./core.js', 'TownArtAB_core'), Q = dep('./parts.js', 'TownArtAB_parts');
  var Q2 = dep('./parts2.js', 'TownArtAB_parts2'), K = dep('./kit.js', 'TownArtAB_kit');
  var P = C.PAL, f = C.f, FROND = '#c9a46a', FROND2 = '#b08850';

  /** 铺面货物：拱洞里堆的布匹 / 陶罐 / 香料筐 */
  function wares(ctx, x, yb, w, kind) {
    if (kind === 0) return C.rect(x + 1, yb - 5, w * 0.4, 5, P.ochre2, 0.7) + C.rect(x + w * 0.45, yb - 7, w * 0.45, 7, P.turq2, 0.7) + C.rect(x + 2, yb - 9, w * 0.35, 4, P.cob2, 0.7);
    if (kind === 1) return K.jar(ctx, x + w * 0.3, yb, 6, P.ochre2) + K.jar(ctx, x + w * 0.7, yb, 7.5, P.mud2);
    return C.path('M' + f(x + 1) + ' ' + f(yb) + 'l1 -4h' + f(w - 4) + 'l1 4Z', P.wood2, 0.7) + C.ell(x + w / 2, yb - 4.5, w / 2 - 2, 1.6, P.gold, 0.6) + C.ell(x + w / 2, yb - 5, w / 4, 1, P.ochre, 0);
  }
  /** 拱廊铺面住宅：v1 1×1 单拱铺 + 白楼；v2 2×1 三拱铺 + 二层木格窗 + 布棚；v3 2×1 三层，二层退进带露台 */
  function arcade(ctx, v, fp) {
    var W = fp[0] * 48, s = '', yf = -3, x0 = 4, x1 = W - 4, g = 20, dp = 34;
    var hTot = v === 3 ? 42 : 40;
    s += C.groundShadow(x0, x1, yf, yf - dp);
    s += Q.box(ctx, x0, x1, yf, dp, hTot, { mat: 'lime', fill: P.lime, roof: { p: 4, step: v === 2 ? 5 : 0, wall: P.lime2, mcol: P.lime, spouts: v !== 2 } });
    // 底层铺面：石砌墙裙 + 拱洞 + 货物
    s += Q.facade(ctx, x0, x1, yf, g, 'stone', { noPlinth: true });
    var n = v === 1 ? 1 : 3, pier = 4, aw = (x1 - x0 - pier * (n + 1)) / n;
    s += K.arcade(ctx, x0 + 0.8, x1 - 0.8, yf, g - 2, n, v === 3 ? 'horseshoe' : 'pointed', P.lime2);
    for (var i = 0; i < n; i++) s += wares(ctx, x0 + pier + i * (aw + pier) + 1, yf, aw - 2, (i + v) % 3);
    s += C.rect(x0 - 0.5, yf - g - 2.5, x1 - x0 + 1, 2.5, P.stone2, 0.9);
    if (v === 1) {
      s += Q2.mashrabiya(ctx, 17, yf - g - 6, 14, 11);
    } else if (v === 2) {
      s += Q2.mashrabiya(ctx, 14, yf - g - 6, 12, 11) + Q2.mashrabiya(ctx, 42, yf - g - 7, 12, 12) + Q2.mashrabiya(ctx, 70, yf - g - 6, 12, 11);
      s += Q2.awning(ctx, x0 + 2, x1 - 2, yf - g - 1, 5, P.ochre2, P.lime);
    } else {
      s += Q2.tileBand(ctx, x0, x1, yf - g - 6, 3, 'star', P.cob, P.turq2) + Q2.win(16, yf - g - 10, 4, 6, 'pointed') + Q2.win(76, yf - g - 10, 4, 6, 'pointed');
      var ty = yf - hTot - 12;
      s += Q.box(ctx, 26, 72, ty, 18, 22, { mat: 'lime', roof: { p: 3, step: 5, wall: P.lime2, mcol: P.lime } });
      s += Q2.mashrabiya(ctx, 42, ty - 6, 12, 11) + Q2.awning(ctx, 74, 88, ty - 12, 8, P.cob2, P.lime, ty);
    }
    return s;
  }

  /** 黑帐篷顶：前沿 yf、进深 dp，n 根中柱把顶撑出峰；返回顶面 + 正面帘 */
  function tentTop(ctx, x0, x1, yf, dp, n, h, col) {
    var front = yf - h, back = front - dp, pk = 7, w = (x1 - x0) / n, d = 'M' + f(x0) + ' ' + f(front), r = 'M' + f(x0) + ' ' + f(back + 3);
    for (var i = 0; i < n; i++) {
      var cx = x0 + w * (i + 0.5);
      d += 'Q' + f(cx - w * 0.3) + ' ' + f(front - 1) + ' ' + f(cx) + ' ' + f(front - pk) + 'Q' + f(cx + w * 0.3) + ' ' + f(front - 1) + ' ' + f(x0 + w * (i + 1)) + ' ' + f(front);
      r += 'Q' + f(cx - w * 0.3) + ' ' + f(back + 2) + ' ' + f(cx) + ' ' + f(back - pk + 2) + 'Q' + f(cx + w * 0.3) + ' ' + f(back + 2) + ' ' + f(x0 + w * (i + 1)) + ' ' + f(back + 3);
    }
    // 顶面：前峰线、后峰线之间平涂；用前后两条线围合
    var poly = d + 'L' + f(x1) + ' ' + f(back + 3) + 'L' + f(x0) + ' ' + f(back + 3) + 'Z';
    var s = C.path(poly, col, 0) + C.path(r + 'L' + f(x1) + ' ' + f(front) + 'L' + f(x0) + ' ' + f(front) + 'Z', col, 0);
    // 羊毛毡的竖向织条（黑白相间，沿坡向）+ 每根中柱顶出的脊线
    var st = '', rg = '', area = poly + r + 'L' + f(x1) + ' ' + f(front) + 'L' + f(x0) + ' ' + f(front) + 'Z';
    for (var sx = x0 + 4; sx < x1 - 2; sx += 8) st += C.rect(sx, back - pk, 2.6, dp + pk + 2, '#c8b28c', 0, 0.55);
    for (i = 0; i < n; i++) { var px = x0 + w * (i + 0.5); rg += 'M' + f(px) + ' ' + f(front - pk) + 'L' + f(px) + ' ' + f(back - pk + 2); }
    for (var k = 1; k < 4; k++) rg += 'M' + f(x0 + 2) + ' ' + f(front - dp * k / 4) + 'H' + f(x1 - 2);
    s += C.clipped(ctx, area, st) + C.line(rg, 0.8, 0.5, '#d9c6a0') + C.line(r + 'M' + f(x0) + ' ' + f(front) + 'L' + f(x0) + ' ' + f(back + 3) + 'M' + f(x1) + ' ' + f(front) + 'L' + f(x1) + ' ' + f(back + 3), 1.4);
    ctx.top(back - pk);
    return { svg: s, ridge: d, front: front };
  }
  /** 贝都因黑帐篷：羊毛毡顶被中柱顶出峰，正面帘子卷起露出地毯与靠垫 */
  function tent(ctx, v, fp) {
    var W = fp[0] * 48, D = fp[1] * 48, s = '', yf = -5, x0 = 3, x1 = W - 3, n = [0, 2, 3, 4][v], h = 13, dp = D - 18;
    s += C.groundShadow(x0, x1, yf, yf - dp - 6, 6);
    // 帐内：后帘 + 地毯 + 靠垫
    s += C.rect(x0 + 2, yf - h, x1 - x0 - 4, h, P.felt, 1);
    s += C.rect(x0 + 5, yf - 3, x1 - x0 - 10, 3, P.ochre, 0.8) + C.line('M' + f(x0 + 7) + ' ' + f(yf - 1.5) + 'H' + f(x1 - 7), 0.8, 0.8, P.gold);
    for (var i = 0; i < n; i++) s += C.rect(x0 + 6 + i * (x1 - x0 - 14) / n, yf - 7, 6, 4, i % 2 ? P.cob2 : P.ochre2, 0.6);
    var T = tentTop(ctx, x0, x1, yf, dp, n, h, P.felt2);
    s += T.svg;
    // 正面：两端垂帘 + 卷起的门帘 + 中柱
    var w = (x1 - x0) / n, poles = '';
    for (i = 0; i < n; i++) poles += 'M' + f(x0 + w * (i + 0.5)) + ' ' + f(yf) + 'V' + f(T.front - 6);
    s += C.line(poles, 1.4, 1, P.wood2);
    s += C.path('M' + f(x0) + ' ' + f(yf) + 'V' + f(T.front) + 'h7l-2 ' + f(h) + 'Z', P.felt, 1.1) + C.path('M' + f(x1) + ' ' + f(yf) + 'V' + f(T.front) + 'h-7l2 ' + f(h) + 'Z', P.felt, 1.1);
    s += C.path(T.ridge + 'L' + f(x1) + ' ' + f(T.front + 3) + 'L' + f(x0) + ' ' + f(T.front + 3) + 'Z', P.felt, 1.3);
    s += C.line('M' + f(x0 + 2) + ' ' + f(T.front + 1.5) + 'H' + f(x1 - 2), 0.8, 0.6, P.ochre2);
    // 拉绳与木桩
    s += C.line('M' + f(x0) + ' ' + f(T.front) + 'L' + f(x0 - 2) + ' ' + f(yf + 1) + 'M' + f(x1) + ' ' + f(T.front) + 'L' + f(x1 + 2) + ' ' + f(yf + 1), 0.6, 0.8);
    if (v === 3) s += K.jar(ctx, x1 - 8, yf + 2, 6) + C.ell(x0 + 10, yf - dp - h - 1, 4, 2, P.hole, 0.6, 0.6);
    return s;
  }

  var T = [
    { n: 8, kind: 'arcade', name: '拱廊铺面住宅', roof: 'flat_mud', tags: ['shop', 'arcade', 'two_storey'], fps: [[1, 1], [2, 1], [2, 1]], draw: arcade,
      vnote: ['单拱铺 + 木格窗白楼', '三拱铺 + 二层三挑窗 + 布棚', '马蹄拱铺 + 三层退台露台'] },
    { n: 9, kind: 'tent', name: '贝都因黑帐篷', roof: 'none', tags: ['tent', 'nomad', 'bedouin'], fps: [[1, 1], [2, 1], [2, 2]], draw: tent,
      note: '羊毛毡帐篷，RoofId 无对应，最近为 none', vnote: ['双柱小帐', '三柱长帐', '四柱大帐，进深两格'] }
  ];
  var API = { T: T, wares: wares, FROND: FROND, FROND2: FROND2 };
  root.TownArtAB_housesD = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
