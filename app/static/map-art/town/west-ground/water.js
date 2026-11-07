/*
 * 织梦 · 西式水面双网格：自然河岸 bank × 16、石砌码头岸 quay × 16（美术样板，尚未接入游戏）
 * 水色 = special-infra 西式码头 / 石拱桥的 #a9b8ad（波纹同为墨线 0.35 不透明度的短排线），接上去看不出两种水。
 * 波纹是周期 48 的固定排布，所有水面瓦片共用，跨左右边的笔画在对边补画 → 按世界坐标对齐、接缝连续。
 * 岸壁：把陆地形状下移几像素、裁切在水里，只在「陆北水南」处露出（3/4 俯视看得到的那一面），≤ 6 px。
 * 浏览器挂 window.TownArtWG_water；Node 用 module.exports。依赖 core.js、dual.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWG_core;
  var D = isNode ? require('./dual.js') : root.TownArtWG_dual;
  var P = C.P, f = C.f;

  var RIPPLES = (function () {
    var r = C.rng(4807), out = [];
    for (var y = 4; y < 46; y += 7) {
      var x = r() * 48, n = r() < 0.6 ? 2 : 1;
      for (var i = 0; i < n; i++) { out.push([x, y + r() * 2.4 - 1.2, 5 + r() * 4]); x = (x + 17 + r() * 12) % 48; }
    }
    return out;
  })();
  function ripples() {
    var d = '';
    RIPPLES.forEach(function (rp) {
      [-48, 0, 48].forEach(function (ox) {
        var x = rp[0] + ox, L = rp[2];
        if (x + L < 0 || x > 48) return;
        d += 'M' + f(x) + ' ' + f(rp[1]) + 'h' + f(L);
      });
    });
    return C.line(d, 0.9, 0.35);
  }
  function landRule(sh) { return sh.rule === 'evenodd' ? 'nonzero' : 'evenodd'; }
  /** 陆地形状下移 dy 后的平涂（由调用方裁切在水里） */
  function shifted(sh, dy, fill) {
    return '<path d="' + sh.land + '" transform="translate(0 ' + dy + ')" fill="' + fill + '" fill-rule="' + landRule(sh) + '"/>';
  }
  function down(dy, inner) { return '<g transform="translate(0 ' + dy + ')">' + inner + '</g>'; }
  function waterBase(ctx, sh) {
    return C.path(sh.fill, P.water, 0, null, ' fill-rule="' + sh.rule + '"') + C.clip(ctx, sh.fill, sh.rule, ripples());
  }

  // ---------- 岸边小物 ----------
  function reeds(ctx, x, y) {
    var d = '', h = '', n = ctx.int(4, 6);
    for (var i = 0; i < n; i++) {
      var dx = (i - (n - 1) / 2) * 1.5 + ctx.rnd(-0.4, 0.4), hh = ctx.rnd(6, 10.5), lean = dx * 0.35 + ctx.rnd(-0.6, 0.6);
      d += 'M' + f(x + dx) + ' ' + f(y) + 'Q' + f(x + dx) + ' ' + f(y - hh * 0.6) + ' ' + f(x + dx + lean) + ' ' + f(y - hh);
      if (i % 2 && ctx.chance(0.7)) h += C.ell(x + dx + lean * 0.9, y - hh + 1.6, 0.85, 1.9, P.dark, 0);
    }
    var blade = 'M' + f(x - 1) + ' ' + f(y) + 'q-3 -3 -4.5 -5.5M' + f(x + 1) + ' ' + f(y) + 'q3 -2.5 4.6 -4.6';
    return C.line(blade, 1, 0.9, P.leaf) + C.line(d, 0.9, 1, P.leaf3) + h +
      C.line('M' + f(x - 4) + ' ' + f(y + 0.8) + 'q4 1.4 8 0', 0.7, 0.4);
  }
  function stone(ctx, x, y, s) {
    var rx = ctx.rnd(1.8, 3.4) * (s || 1), ry = rx * ctx.rnd(0.55, 0.7);
    return C.ell(x + 0.8, y + 0.6, rx, ry * 0.8, P.shadow, 0, 0.18) +
      C.ell(x, y, rx, ry, ctx.pick([P.stone, P.stone2, P.stone3]), 0.8);
  }
  function tufts(ctx, pts) {
    return pts.map(function (p) { return C.tuft(ctx, p[0], p[1], ctx.rnd(3, 5), ctx.int(3, 4), P.leaf3, 0.8); }).join('');
  }
  function bollard(x, y) {
    return C.ell(x + 1.6, y + 0.6, 2.8, 1.1, P.shadow, 0, 0.18) + C.rect(x - 2, y - 5, 4, 5, P.dark, 0.9) +
      C.ell(x, y - 5, 2.4, 1.1, P.iron, 0.9) + C.line(C.seg(x - 2, y - 2.5, x + 2, y - 2.5), 0.6, 0.5);
  }
  function lowEnough(p) { return p[1] >= 13; }

  // ---------- 自然河岸 ----------
  function bankTile(mask) {
    var id = 'west-common-water-bank-' + D.bin(mask), ctx = new C.Ctx(id), o = '';
    if (!mask) return { id: id, kind: 'water_bank', mask: 0, body: '' };
    var sh = D.shape(ctx, mask, { rad: 12, wig: 2.2, diagRad: 15 });
    if (sh.k < 4) o += C.clip(ctx, sh.land, landRule(sh), D.stripe(sh.outline, 13, P.mud) + D.stripe(sh.outline, 5, P.soil, 0.55));
    o += waterBase(ctx, sh);
    if (sh.k < 4) {
      o += C.clip(ctx, sh.fill, sh.rule, D.stripe(sh.outline, 9.5, P.paper, 0.6) + D.stripe(sh.outline, 7.5, P.water) +
        shifted(sh, 2.5, P.soil2) + down(2.5, C.line(sh.outline, 0.8, 0.45)));
      o += C.line(sh.outline, 1.3, 0.85);
      var diag = mask === 9 || mask === 6;
      o += tufts(ctx, D.band(ctx, mask, diag ? 3 : 2, 7.5, 11, 5, 9));
      D.band(ctx, mask, ctx.int(1, 2), 2.5, 6.5, 6, 8).forEach(function (p) { o += stone(ctx, p[0], p[1]); });
      D.band(ctx, mask, diag ? 2 : ctx.int(1, 2), -2.5, 2, 7, 13).filter(lowEnough).forEach(function (p) { o += reeds(ctx, p[0], p[1]); });
    }
    return { id: id, kind: 'water_bank', mask: mask, body: C.clip(ctx, D.TILE, 'nonzero', o) };
  }

  // ---------- 石砌码头岸 ----------
  function quayTile(mask) {
    var id = 'west-common-water-quay-' + D.bin(mask), ctx = new C.Ctx(id), o = '';
    if (!mask) return { id: id, kind: 'water_quay', mask: 0, body: '' };
    var sh = D.shape(ctx, mask, { rad: 6, wig: 0, diagRad: 14 });
    o += waterBase(ctx, sh);
    if (sh.k < 4) {
      // 岸壁正面（下移 6 px）：条石层、竖缝、水线
      o += C.clip(ctx, sh.fill, sh.rule, shifted(sh, 6, P.stone2) +
        down(3, C.line(sh.outline, 0.8, 0.5) + D.stripe(sh.outline, 6, P.ink, 0.45, '0.9 11.1')) +
        down(6, D.stripe(sh.outline, 2.6, P.water2, 0.9) + C.line(sh.outline, 0.9, 0.6)));
      // 压顶条石（陆地一侧 9.5 px）
      o += C.clip(ctx, sh.land, landRule(sh), D.stripe(sh.outline, 21, P.ink, 0.7) + D.stripe(sh.outline, 19, P.stone) +
        D.stripe(sh.outline, 19, P.ink, 0.42, '0.9 11.1'));
      o += C.line(sh.outline, 1.6, 1);
      if (ctx.chance(sh.k === 2 ? 0.9 : 0.5)) D.band(ctx, mask, 1, 4, 5.5, 10, 0).forEach(function (p) { o += bollard(p[0], p[1]); });
    }
    return { id: id, kind: 'water_quay', mask: mask, body: C.clip(ctx, D.TILE, 'nonzero', o) };
  }

  function all() {
    var out = [];
    for (var m = 0; m < 16; m++) out.push(bankTile(m));
    for (var q = 0; q < 16; q++) out.push(quayTile(q));
    return out;
  }
  var api = { RIPPLES: RIPPLES, ripples: ripples, bankTile: bankTile, quayTile: quayTile, all: all };
  root.TownArtWG_water = api;
  if (isNode) module.exports = api;
})(typeof window !== 'undefined' ? window : this);
