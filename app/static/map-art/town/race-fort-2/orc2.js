/*
 * 织梦 · race-fort-2 兽人族：夯土台地尖桩大寨要塞地标（landmark，6×6）（美术样板，尚未接入游戏）
 * 尖桩、绳扎、头骨、长角头骨、战旗、图腾配色全部沿用 ../race-fort/orc.js（只读 require）。
 * 浏览器挂 window.TownArtRF2_orc；Node 用 module.exports。依赖 race-fort 的 core.js、spoke.js、orc.js 与本目录 bastion.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('../race-fort/core.js') : root.TownArtRF_core;
  var K = isNode ? require('../race-fort/spoke.js') : root.TownArtRF_spoke;
  var O = isNode ? require('../race-fort/orc.js') : root.TownArtRF_orc;
  var B = isNode ? require('./bastion.js') : root.TownArtRF2_bastion;
  var P = C.P, f = C.f, line = C.line, path = C.path, rect = C.rect;
  var TONE = [P.wood, '#bf9a60', '#b48e58', P.wood, '#b48e58', '#c4a068'];
  var DH = [0, 2, -1, 1, 3, -2, 1, 0, 2, -1, 3, 0];

  /** 夯土层立面纹：水平夯层线 + 斜向草筋 */
  function rammed(x0, x1, h) {
    var d = '', g = '';
    for (var y = -6; y > -h + 2; y -= 6) d += 'M' + f(x0) + ' ' + f(y) + 'H' + f(x1);
    for (var x = Math.floor(x0 / 9) * 9; x < x1; x += 9) g += 'M' + f(x + 2) + ' ' + f(-3 - (x % 18 ? 6 : 12)) + 'l3 -2';
    return line(d, 0.8, 0.5) + line(g, 0.7, 0.45) + rect(x0, -h, x1 - x0, 2.5, P.shadow, 0, 0.16);
  }
  /** 一排尖桩（沿地面线 A→B，墙脚抬到 z）：桩距 5，跳过 gap 区间（x 范围） */
  function palisade(A, B2, z, hBase, gap) {
    var s = '', L = Math.hypot(B2[0] - A[0], B2[1] - A[1]), n = Math.max(1, Math.round(L / 5));
    for (var i = 0; i <= n; i++) {
      var x = A[0] + (B2[0] - A[0]) * i / n, y = A[1] + (B2[1] - A[1]) * i / n - z;
      if (gap && x > gap[0] && x < gap[1]) continue;
      var k = ((Math.round(x / 5) + Math.round(y / 5) * 5) % 12 + 12) % 12, h = hBase + DH[k];
      s += O.stake(x - 2.4, y, 4.8, h, TONE[k % TONE.length], 1) + rect(x - 1.5, y - h + 0.6, 1.5, h - 1.2, P.dark, 0, 0.2);
      if (k % 7 === 3) s += O.skull(x, y - h - 3, 0.55);
    }
    var r = '';
    [10, 21].forEach(function (zz) {
      if (!gap) { r += 'M' + f(A[0]) + ' ' + f(A[1] - z - zz) + 'L' + f(B2[0]) + ' ' + f(B2[1] - z - zz); return; }
      var t0 = (gap[0] - A[0]) / (B2[0] - A[0]), t1 = (gap[1] - A[0]) / (B2[0] - A[0]);
      r += 'M' + f(A[0]) + ' ' + f(A[1] - z - zz) + 'L' + f(gap[0]) + ' ' + f(A[1] + (B2[1] - A[1]) * t0 - z - zz) +
        'M' + f(gap[1]) + ' ' + f(A[1] + (B2[1] - A[1]) * t1 - z - zz) + 'L' + f(B2[0]) + ' ' + f(B2[1] - z - zz);
    });
    return s + O.rope(r);
  }
  /** 兽皮战帐：中心 (x, yb)，半宽 w，高 h：锥顶 + 撑杆 + 缝线 + 门帘 */
  function tent(x, yb, w, h, col) {
    var ty = yb - h, s = path('M' + f(x - w) + ' ' + f(yb) + 'L' + f(x) + ' ' + f(ty) + 'L' + f(x + w) + ' ' + f(yb) + 'Q' + f(x) + ' ' + f(yb + w * 0.18) + ' ' + f(x - w) + ' ' + f(yb) + 'Z', col || P.hide, 1.5);
    s += path('M' + f(x) + ' ' + f(ty) + 'L' + f(x + w) + ' ' + f(yb) + 'Q' + f(x + w * 0.5) + ' ' + f(yb + w * 0.12) + ' ' + f(x + w * 0.15) + ' ' + f(yb + w * 0.08) + 'Z', P.hide2, 0, 0.45);
    s += line('M' + f(x) + ' ' + f(ty) + 'L' + f(x - w * 0.5) + ' ' + f(yb + w * 0.06) + 'M' + f(x) + ' ' + f(ty) + 'L' + f(x + w * 0.5) + ' ' + f(yb + w * 0.06), 0.8, 0.55);
    s += path('M' + f(x - w * 0.18) + ' ' + f(yb + w * 0.1) + 'L' + f(x) + ' ' + f(yb - h * 0.45) + 'L' + f(x + w * 0.18) + ' ' + f(yb + w * 0.1) + 'Z', P.hole, 0.9);
    s += line('M' + f(x - 3) + ' ' + f(ty + 2) + 'l-3 -9M' + f(x + 2) + ' ' + f(ty + 2) + 'l4 -10M' + f(x) + ' ' + f(ty + 1) + 'v-8', 1.6, 1, P.timber);
    return s;
  }
  /** 图腾柱：底 (x, yb)，n 段兽首 + 顶上长角头骨 */
  function totem(ctx, x, yb, n) {
    var cols = [P.wood, '#b48e58', P.hide3], s = '';
    for (var i = 0; i < n; i++) {
      var y1 = yb - i * 14, y0 = y1 - 14;
      s += rect(x - 5, y0, 10, 14, cols[i % 3], 1.2) + rect(x + 1, y0 + 0.6, 3.4, 12.8, P.dark, 0, 0.25);
      s += C.ell(x - 2.2, y0 + 4.5, 1.3, 1.1, P.hole, 0) + C.ell(x + 2.2, y0 + 4.5, 1.3, 1.1, P.hole, 0) + path('M' + f(x - 3.5) + ' ' + f(y0 + 8) + 'h7l-1 3h-5Z', P.hole, 0.6);
      if (i % 2) s += path('M' + f(x - 5) + ' ' + f(y0 + 3) + 'l-5 -3l5 6ZM' + f(x + 5) + ' ' + f(y0 + 3) + 'l5 -3l-5 6Z', P.rust, 0.8);
    }
    var ty = yb - n * 14;
    s += O.hornSkull(x, ty - 4, 0.75, 10);
    ctx.top(ty - 14);
    return s;
  }
  /** 火塘：石圈 + 火焰 */
  function firePit(x, y) {
    return C.ell(x, y, 9, 5, P.stone2, 1.2) + C.ell(x, y - 0.5, 6, 3.2, P.hole, 0) +
      path('M' + f(x - 5) + ' ' + f(y) + 'Q' + f(x - 4) + ' ' + f(y - 10) + ' ' + f(x) + ' ' + f(y - 15) + 'Q' + f(x + 5) + ' ' + f(y - 9) + ' ' + f(x + 5) + ' ' + f(y) + 'Z', P.fire, 1) +
      path('M' + f(x - 2) + ' ' + f(y) + 'Q' + f(x - 1) + ' ' + f(y - 6) + ' ' + f(x + 1) + ' ' + f(y - 9) + 'Q' + f(x + 3) + ' ' + f(y - 5) + ' ' + f(x + 2) + ' ' + f(y) + 'Z', P.ember, 0);
  }
  /** 头骨堆 */
  function skullPile(x, y) {
    return O.skull(x - 5, y - 2, 0.7) + O.skull(x + 5, y - 2, 0.7) + O.skull(x, y - 7, 0.75) + line('M' + f(x - 10) + ' ' + f(y + 2) + 'l6 -1M' + f(x + 4) + ' ' + f(y + 2) + 'l7 1', 1.4, 1, P.bone2);
  }
  var Z1 = 22, Z2 = 46;
  var LOW = [[30, -270], [258, -270], [280, -240], [280, -36], [262, -12], [26, -12], [8, -36], [8, -240]];
  var PAL = [[34, -264], [254, -264], [274, -238], [274, -38], [258, -18], [30, -18], [14, -38], [14, -238]];
  var UPP = [[70, -236], [218, -236], [232, -218], [232, -112], [218, -96], [70, -96], [56, -112], [56, -218]];
  /** 夯土台地尖桩大寨（landmark，6×6）：两层夯土台 + 外圈尖桩寨墙 + 前沿战帐门楼 + 上台酋长大帐 + 图腾、头骨堆、战旗、火塘 */
  function fortress(ctx) {
    var s = '';
    s += B.shadow(LOW, 8, 5, 0.16);
    s += B.solid(ctx, LOW, null, 0, Z1, { face: P.soil2, top: P.soil, sw: 1.8, tex: rammed });
    // 后沿与两侧寨墙（由远到近）
    s += palisade(PAL[7], PAL[0], Z1, 30) + palisade(PAL[0], PAL[1], Z1, 30) + palisade(PAL[1], PAL[2], Z1, 30);
    s += palisade(PAL[7], PAL[6], Z1, 30) + palisade(PAL[2], PAL[3], Z1, 30);
    // 后排：两根大图腾 + 战旗
    s += totem(ctx, 40, -250 - Z1, 5) + totem(ctx, 248, -250 - Z1, 5);
    s += O.banner(72, -252 - Z1, 46, -1) + O.banner(216, -252 - Z1, 46, 1);
    // 上层夯土台
    s += B.solid(ctx, UPP, null, Z1, Z2 - Z1, { face: P.soil2, top: P.soil, sw: 1.7, tex: rammed });
    s += line('M76 ' + f(-200 - Z2) + 'h18M190 ' + f(-210 - Z2) + 'h20M100 ' + f(-130 - Z2) + 'h14', 0.8, 0.45);
    // 上台：两顶侧帐（后）+ 酋长大帐 + 帐前图腾
    s += tent(92, -206 - Z2, 22, 40, P.hide3) + tent(196, -206 - Z2, 22, 40, P.hide3);
    s += tent(144, -170 - Z2, 44, 76, P.hide);
    var ty = -170 - Z2 - 76;
    s += O.hornSkull(144, ty - 4, 1, 14) + line('M144 ' + f(ty - 12) + 'V' + f(ty - 34), 1.8) +
      path('M144 ' + f(ty - 34) + 'h16v14l-8 -4l-8 4Z', P.rust, 1.1);
    ctx.top(ty - 38);
    s += skullPile(100, -132 - Z2) + skullPile(188, -132 - Z2) + firePit(144, -112 - Z2);
    s += totem(ctx, 116, -110 - Z2, 3) + totem(ctx, 172, -110 - Z2, 3);
    // 上台前沿台阶
    s += path('M128 ' + f(-96 - Z1) + 'L160 ' + f(-96 - Z1) + 'L160 ' + f(-96 - Z2) + 'L128 ' + f(-96 - Z2) + 'Z', P.soil, 1.3);
    var d = ''; for (var y = -96 - Z1 - 5; y > -96 - Z2; y -= 5) d += 'M128 ' + f(y) + 'H160';
    s += line(d, 0.9, 0.65);
    // 下台：前排两侧战帐 + 武器架
    s += tent(54, -60 - Z1, 24, 42) + tent(234, -60 - Z1, 24, 42);
    // 第一轮截图：火塘被前寨墙挡住只露火尖，挪到帐篷与门楼之间
    s += firePit(88, -82 - Z1) + skullPile(200, -78 - Z1);
    return s + fortressFront(ctx);
  }
  /** 前沿：两侧前寨墙 + 前寨墙（留门洞）+ 战帐门楼（两座桩塔 + 横梁瞭台 + 兽皮帐顶 + 长角头骨 + 吊头骨） */
  function fortressFront(ctx) {
    var s = '';
    s += palisade(PAL[5], PAL[6], Z1, 30) + palisade(PAL[3], PAL[4], Z1, 30);
    // 门洞地面：夯土坡道（从台地前沿伸到地面）
    s += path('M122 -12L166 -12L162 ' + f(-18 - Z1) + 'L126 ' + f(-18 - Z1) + 'Z', P.soil, 1.3) + line('M124 -20h40M125 -28h38M126 -36h36', 0.8, 0.5);
    s += palisade(PAL[4], PAL[5], Z1, 30, [118, 170]);
    var by = -18 - Z1, Z = 70;
    [112, 176].forEach(function (x, i) {
      // 桩塔：四根粗原木 + 绳扎
      s += line('M' + f(x - 8) + ' ' + f(by) + 'L' + f(x - 5) + ' ' + f(by - Z) + 'M' + f(x + 8) + ' ' + f(by) + 'L' + f(x + 5) + ' ' + f(by - Z), 6, 1) +
        line('M' + f(x - 8) + ' ' + f(by) + 'L' + f(x - 5) + ' ' + f(by - Z) + 'M' + f(x + 8) + ' ' + f(by) + 'L' + f(x + 5) + ' ' + f(by - Z), 4.2, 1, i ? '#b48e58' : P.wood);
      s += O.knot(x - 6.5, by - 22, 5, 2) + O.knot(x + 6.5, by - 22, 5, 2) + O.rope('M' + f(x - 7) + ' ' + f(by - 40) + 'L' + f(x + 7) + ' ' + f(by - 44));
      s += O.skull(x, by - 30, 0.8);
    });
    // 横梁瞭台
    s += rect(98, by - Z - 6, 92, 7, P.timber, 1.4) + line('M100 ' + f(by - Z - 2.5) + 'H188', 0.8, 0.5);
    for (var x = 100; x <= 188; x += 4.5) s += O.stake(x - 1.6, by - Z - 5, 3.2, 10 + DH[(x / 4.5 | 0) % 12] * 0.6, TONE[(x / 4.5 | 0) % TONE.length], 0.8);
    // 吊在门洞上方的一串头骨
    s += O.rope('M126 ' + f(by - Z + 2) + 'Q144 ' + f(by - Z + 16) + ' 162 ' + f(by - Z + 2));
    s += O.skull(134, by - Z + 10, 0.6) + O.skull(144, by - Z + 13, 0.65) + O.skull(154, by - Z + 10, 0.6);
    // 兽皮战帐顶（门楼）
    var ty = by - Z - 14;
    s += line('M104 ' + f(ty + 8) + 'V' + f(ty - 8) + 'M184 ' + f(ty + 8) + 'V' + f(ty - 8), 1.8);
    s += path('M92 ' + f(ty - 4) + 'L144 ' + f(ty - 40) + 'L196 ' + f(ty - 4) + 'L186 ' + f(ty) + 'L170 ' + f(ty - 5) + 'L156 ' + f(ty + 1) + 'L144 ' + f(ty - 4) + 'L132 ' + f(ty + 1) + 'L118 ' + f(ty - 5) + 'L102 ' + f(ty) + 'Z', P.hide, 1.6);
    s += path('M144 ' + f(ty - 40) + 'L196 ' + f(ty - 4) + 'L186 ' + f(ty) + 'L170 ' + f(ty - 5) + 'L156 ' + f(ty + 1) + 'L144 ' + f(ty - 4) + 'Z', P.hide2, 0, 0.45);
    s += line('M118 ' + f(ty - 16) + 'l8 -6M160 ' + f(ty - 24) + 'l8 6M132 ' + f(ty - 8) + 'l6 -5', 0.8, 0.6);
    s += O.hornSkull(144, ty - 42, 0.95, 13);
    s += O.banner(100, ty - 6, 30, -1) + O.banner(188, ty - 6, 30, 1);
    ctx.top(ty - 56);
    return s;
  }

  function types() {
    return [{ id: 'west-orc-fortress-01', race: 'orc', category: 'landmark', kind: 'stake_warcamp', facility: 'barracks', fp: [6, 6], roof: 'monopitch', culture: 'orc',
      tags: ['landmark', 'fortress', 'rammed_earth', 'palisade', 'war_tent', 'totem', 'skull'],
      note: '尖桩大寨（6×6）：两层夯土台地 + 外圈尖桩寨墙 + 前沿双桩塔战帐门楼（吊头骨）+ 上台酋长大帐与侧帐 + 图腾柱、头骨堆、火塘、战旗。roof 为兽皮帐顶，取最近的 monopitch；facility 取 barracks（战帮驻地）',
      draw: fortress }];
  }
  var API = { types: types, fortress: fortress, tent: tent, totem: totem, palisade: palisade };
  root.TownArtRF2_orc = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
