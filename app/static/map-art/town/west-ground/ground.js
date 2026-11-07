/*
 * 织梦 · 西式地面：草地底纹 grass-01..04 + 踩实土地/院坪双网格 dirt × 16（美术样板，尚未接入游戏）
 * 草地：底色 #c9c79a 铺满整格；所有笔触离瓦片边至少 4 px，不跨边 → 任意排列都无缝。
 *       四个变体疏密不同（01 最素），深浅只做轻微变化，不和建筑抢眼。
 * 土地：分界线规则同道路（过边中点、垂直于边）；土面纹理是周期 48 的固定排布、四向回绕补画，按世界坐标对齐。
 * 浏览器挂 window.TownArtWG_ground；Node 用 module.exports。依赖 core.js、dual.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWG_core;
  var D = isNode ? require('./dual.js') : root.TownArtWG_dual;
  var P = C.P, f = C.f;
  var GRASS_DARK = '#bdbb8b', GRASS_LIGHT = '#d1cfa4', FLOWERS = ['#efdfb2', '#e3c47a', '#b5654a', '#d9cfe0'];

  // ---------- 草地底纹 ----------
  var GRASS = [
    { n: 1, name: '草地·素', patches: 1, tufts: 3, pebbles: 1, flowers: 0 },
    { n: 2, name: '草地·草丛', patches: 2, tufts: 6, pebbles: 0, flowers: 1 },
    { n: 3, name: '草地·碎石', patches: 1, tufts: 4, pebbles: 4, flowers: 0 },
    { n: 4, name: '草地·野花', patches: 2, tufts: 4, pebbles: 1, flowers: 3 }
  ];
  function spots(ctx, n, margin, gap, have) {
    var out = [], t = 0;
    while (out.length < n && t++ < 300) {
      var x = ctx.rnd(margin, 48 - margin), y = ctx.rnd(margin + 4, 48 - margin);
      if (have.concat(out).some(function (p) { return Math.hypot(p[0] - x, p[1] - y) < gap; })) continue;
      out.push([x, y]);
    }
    have.push.apply(have, out);
    return out;
  }
  function pebble(ctx, x, y) {
    var rx = ctx.rnd(0.9, 1.7);
    return C.ell(x, y, rx, rx * 0.65, ctx.pick([P.stone, P.stone2, '#b9a47c']), 0.5, null).replace('/>', ' stroke-opacity="0.6"/>');
  }
  function flower(ctx, x, y) {
    var c = ctx.pick(FLOWERS), o = C.line(C.seg(x, y, x + ctx.rnd(-0.6, 0.6), y - 2.6), 0.7, 0.8, P.leaf3);
    for (var i = 0; i < 3; i++) o += C.ell(x - 1.6 + i * 1.6 + ctx.rnd(-0.3, 0.3), y - 3 + (i % 2) * 0.8, 0.9, 0.8, c, 0);
    return o;
  }
  function grassTile(g) {
    var id = 'west-common-ground-grass-' + (g.n < 10 ? '0' : '') + g.n, ctx = new C.Ctx(id), o = C.rect(0, 0, 48, 48, P.grass, 0), have = [];
    // 深浅斑：位置大范围随机、尺寸不一、不透明度低，避免「一格一个椭圆」的重复感；离边 ≥ 4 px
    for (var i = 0; i < g.patches; i++) {
      var rx = ctx.rnd(4, 9), ry = rx * ctx.rnd(0.4, 0.6), dark = (i + g.n) % 2 === 0;
      var cx = ctx.rnd(5 + rx * 1.2, 43 - rx * 1.2), cy = ctx.rnd(5 + ry * 1.2, 43 - ry * 1.2);
      o += C.path(C.blob(ctx, cx, cy, rx, ry, 6, 0.25), dark ? GRASS_DARK : GRASS_LIGHT, 0, dark ? 0.32 : 0.38);
    }
    spots(ctx, g.tufts, 5, 7, have).forEach(function (p, k) {
      o += C.tuft(ctx, p[0], p[1], ctx.rnd(2.6, 4.2), ctx.int(3, 5), k % 3 ? P.leaf3 : P.leaf, 0.75).replace('/>', ' stroke-opacity="0.75"/>');
    });
    spots(ctx, g.pebbles, 5, 5, have).forEach(function (p) { o += pebble(ctx, p[0], p[1]); });
    spots(ctx, g.flowers, 6, 6, have).forEach(function (p) { o += flower(ctx, p[0], p[1]); });
    return { id: id, kind: 'ground_grass', variant: g.n, name: g.name, body: o };
  }

  // ---------- 踩实土地 / 院坪 ----------
  var DIRT_TEX = (function () {
    var r = C.rng(9341), out = [];
    for (var i = 0; i < 9; i++) out.push({ t: 'p', x: r() * 48, y: r() * 48, s: 0.8 + r() * 0.9, c: Math.floor(r() * 3) });
    for (var j = 0; j < 7; j++) out.push({ t: 's', x: r() * 48, y: r() * 48, L: 3 + r() * 4 });
    for (var k = 0; k < 2; k++) out.push({ t: 'b', x: r() * 48, y: r() * 48, rx: 6 + r() * 4, ry: 2.5 + r() * 1.5 });
    return out;
  })();
  function dirtTex() {
    var o = '', d = '', fills = [P.stone, P.stone2, '#b9a47c'];
    DIRT_TEX.forEach(function (e) {
      [-48, 0, 48].forEach(function (ox) {
        [-48, 0, 48].forEach(function (oy) {
          var x = e.x + ox, y = e.y + oy;
          if (x < -12 || x > 60 || y < -6 || y > 54) return;
          if (e.t === 'b') o = C.ell(x, y, e.rx, e.ry, P.yard2, 0, 0.45) + o;
          else if (e.t === 'p') o += C.ell(x, y, e.s, e.s * 0.65, fills[e.c], 0.5).replace('/>', ' stroke-opacity="0.55"/>');
          else d += 'M' + f(x) + ' ' + f(y) + 'h' + f(e.L);
        });
      });
    });
    return o + C.line(d, 0.8, 0.3);
  }
  function dirtTile(mask) {
    var id = 'west-common-ground-dirt-' + D.bin(mask), ctx = new C.Ctx(id), o = '';
    if (!mask) return { id: id, kind: 'ground_dirt', mask: 0, body: '' };
    var sh = D.shape(ctx, mask, { rad: 11, wig: 1.8, diagRad: 15 });
    var landRule = sh.rule === 'evenodd' ? 'nonzero' : 'evenodd';
    if (sh.k < 4) o += C.clip(ctx, sh.land, landRule, D.stripe(sh.outline, 7, GRASS_DARK, 0.6));
    o += C.path(sh.fill, P.yard, 0, null, ' fill-rule="' + sh.rule + '"');
    var tex = dirtTex();
    if (sh.k < 4) tex += D.stripe(sh.outline, 8, P.yard2, 0.75) + D.stripe(sh.outline, 2.2, P.soil, 0.35);
    o += C.clip(ctx, sh.fill, sh.rule, tex);
    if (sh.k < 4) {
      o += C.line(sh.outline, 0.9, 0.45);
      D.band(ctx, mask, mask === 9 || mask === 6 ? 2 : ctx.int(1, 2), 3.5, 7, 6, 10).forEach(function (p) {
        o += C.tuft(ctx, p[0], p[1], ctx.rnd(2.6, 3.8), ctx.int(3, 4), P.leaf3, 0.75).replace('/>', ' stroke-opacity="0.8"/>');
      });
    }
    return { id: id, kind: 'ground_dirt', mask: mask, body: C.clip(ctx, D.TILE, 'nonzero', o) };
  }

  function all() {
    var out = GRASS.map(grassTile);
    for (var m = 0; m < 16; m++) out.push(dirtTile(m));
    return out;
  }
  var api = { GRASS: GRASS, grassTile: grassTile, dirtTile: dirtTile, all: all };
  root.TownArtWG_ground = api;
  if (isNode) module.exports = api;
})(typeof window !== 'undefined' ? window : this);
