/*
 * 织梦 · 阿拉伯民居 C：穹顶小屋（含蜂巢圆锥屋）、塔楼宅（也门式多层夯土高楼，白色石膏饰带 + 半月彩窗 qamariya）（美术样板，尚未接入游戏）
 * 浏览器挂 window.TownArtAB_housesC；Node 用 module.exports。依赖 core.js、parts.js、parts2.js、kit.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  function dep(file, name) { return isNode ? require(file) : root[name]; }
  var C = dep('./core.js', 'TownArtAB_core'), Q = dep('./parts.js', 'TownArtAB_parts');
  var Q2 = dep('./parts2.js', 'TownArtAB_parts2'), K = dep('./kit.js', 'TownArtAB_kit');
  var P = C.PAL, f = C.f;

  /** 蜂巢圆锥：底中点 (cx, yb)，底宽 w，高 ht；横向砌层线 + 右侧阴面 + 顶部通气孔 */
  function cone(ctx, cx, yb, w, ht, col) {
    var r = w / 2, d = 'M' + f(cx - r) + ' ' + f(yb) + 'C' + f(cx - r) + ' ' + f(yb - ht * 0.55) + ' ' + f(cx - r * 0.22) + ' ' + f(yb - ht) + ' ' + f(cx) + ' ' + f(yb - ht) +
      'C' + f(cx + r * 0.22) + ' ' + f(yb - ht) + ' ' + f(cx + r) + ' ' + f(yb - ht * 0.55) + ' ' + f(cx + r) + ' ' + f(yb) + 'Z';
    var c = '';
    for (var y = yb - 5; y > yb - ht + 4; y -= 4.5) c += 'M' + f(cx - r) + ' ' + f(y) + 'H' + f(cx + r);
    var inner = C.rect(cx + r * 0.3, yb - ht - 1, r, ht + 2, P.mud3, 0, 0.45) + C.line(c, 0.6, 0.45);
    ctx.top(yb - ht - 2);
    return C.path(d, col || P.mud, 0) + C.clipped(ctx, d, inner) + C.path(d, 'none', 1.5) + C.ell(cx, yb - ht + 1.6, 1.4, 0.8, P.hole, 0.6);
  }
  /** 穹顶小屋：v1 1×1 土坯方屋 + 白穹顶；v2 2×1 石灰白长屋双穹顶；v3 1×1 叙利亚式蜂巢圆锥屋（双锥） */
  function domehut(ctx, v) {
    var s = '', yf = -4;
    if (v === 1) {
      s += C.groundShadow(7, 41, yf, -36);
      s += Q.box(ctx, 7, 41, yf, 32, 20, { roof: { p: 2 } });
      s += Q2.dome(ctx, 24, yf - 20 - 12, 28, 3, 22, { finial: false, drum: P.mud2 });
      s += Q.door(ctx, 13, yf, 10, 15, { kind: 'pointed', col: P.ochre2, frame: P.lime2 }) + Q2.win(32, yf - 12, 3, 6, 'slit');
    } else if (v === 2) {
      s += C.groundShadow(4, 92, yf, -40);
      s += Q.box(ctx, 4, 92, yf, 36, 18, { mat: 'lime', roof: { p: 2, wall: P.lime2 } });
      s += Q2.dome(ctx, 26, yf - 18 - 14, 30, 4, 20, { finial: false, ribs: 6 }) + Q2.dome(ctx, 70, yf - 18 - 14, 30, 4, 20, { finial: false, ribs: 6 });
      s += Q2.dome(ctx, 48, yf - 18 - 24, 12, 2, 8, { finial: false, col: P.turq2, shade: P.turq });
      s += Q2.tileBand(ctx, 4, 92, yf - 15, 2.6, 'star', P.turq, P.lime);
      s += Q.door(ctx, 43, yf, 10, 13, { kind: 'pointed', col: P.cob2, frame: P.turq, studs: true });
      s += Q2.win(16, yf - 10, 4, 5, 'round') + Q2.win(28, yf - 10, 4, 5, 'round') + Q2.win(66, yf - 10, 4, 5, 'round') + Q2.win(78, yf - 10, 4, 5, 'round');
    } else {
      s += C.groundShadow(4, 44, yf, -40);
      s += Q.box(ctx, 4, 44, yf, 34, 14, { roof: { p: 0 } });
      s += cone(ctx, 33, yf - 14 - 22, 20, 32, P.mud) + cone(ctx, 17, yf - 14 - 8, 24, 38, P.mud);
      s += Q.door(ctx, 9, yf, 8, 11, { col: P.wood }) + K.jar(ctx, 38, yf, 7);
    }
    return s;
  }

  /** 半月彩窗：白石膏框 + 方窗 + 上方半圆彩色玻璃 */
  function qwin(x, yb, w, h) {
    var r = w / 2;
    var fr = 'M' + f(x - 1.6) + ' ' + f(yb + 1.4) + 'V' + f(yb - h) + 'A' + f(r + 1.6) + ' ' + f(r + 1.6) + ' 0 0 1 ' + f(x + w + 1.6) + ' ' + f(yb - h) + 'V' + f(yb + 1.4) + 'Z';
    return C.path(fr, P.lime, 0.8) + C.rect(x, yb - h, w, h, P.hole, 0.8) +
      C.path('M' + f(x) + ' ' + f(yb - h - 0.6) + 'A' + f(r) + ' ' + f(r) + ' 0 0 1 ' + f(x + w) + ' ' + f(yb - h - 0.6) + 'Z', P.turq2, 0.6) +
      C.line('M' + f(x + r) + ' ' + f(yb - h - 0.6) + 'v' + f(-r + 0.4), 0.5, 0.8);
  }
  /** 也门式塔楼：底部石砌层 + 夯土砖楼层，每层一道白色锯齿饰带与半月彩窗，屋顶白色阶梯雉堞 */
  function tower(ctx, x0, x1, yf, dp, h, o) {
    o = o || {};
    var st = o.stone || 26, fl = o.floor || 20, w = x1 - x0, n = o.wn || (w > 26 ? 2 : 1), i, y;
    var s = Q.facade(ctx, x0, x1, yf, h, 'mud', { fill: P.mud2 }) + Q.facade(ctx, x0, x1, yf, st, 'stone', { noPlinth: true });
    for (y = yf - st; y > yf - h + fl * 0.8; y -= fl) {
      s += Q2.tileBand(ctx, x0, x1, y, 2.6, 'zig', P.lime, P.mud3);
      for (i = 0; i < n; i++) { var ww = 5, xx = x0 + (w - n * ww) / (n + 1) * (i + 1) + ww * i; s += qwin(xx, y - 5, ww, 7); }
    }
    s += Q2.win(x0 + w / 2 - 1.5, yf - st + 12, 3, 6, 'slit');
    s += C.rect(x0, yf - h, w, h, 'none', 1.7);
    s += Q.flatRoof(ctx, x0, x1, yf - h, dp, { p: 4, step: 5, wall: P.mud2, mcol: P.lime });
    return s;
  }
  /** 塔楼宅：v1 1×1 单塔；v2 1×2 后高塔 + 前矮翼露台；v3 2×1 高低双塔 + 中间拱门连廊 */
  function towerhouse(ctx, v) {
    var s = '', yf = -4;
    if (v === 1) {
      s += C.groundShadow(9, 39, yf, -34);
      s += tower(ctx, 9, 39, yf, 30, 108);
      s += Q.door(ctx, 19, yf, 10, 14, { col: P.wood, studs: true, frame: P.lime });
    } else if (v === 2) {
      s += C.groundShadow(8, 40, -44, -84) + C.groundShadow(4, 44, yf, -42);
      s += tower(ctx, 8, 40, -44, 40, 116, { wn: 2 });
      s += Q.box(ctx, 4, 44, yf, 38, 20, { roof: { p: 3, step: 5, mcol: P.lime } });
      s += Q.door(ctx, 18, yf, 11, 14, { col: P.wood, studs: true, frame: P.lime }) + Q2.win(36, yf - 12, 3, 5, 'slit');
      s += K.jar(ctx, 10, yf - 20 - 8, 6) + K.laundry(ctx, 18, 40, yf - 20 - 14, [P.ochre2, P.lime, P.turq2]);
    } else {
      s += C.groundShadow(5, 91, yf, -36);
      s += Q.box(ctx, 39, 57, -10, 22, 46, { mat: 'lime', roof: { p: 3, step: 4, wall: P.lime2, mcol: P.lime } });
      s += Q.door(ctx, 42, -10, 12, 22, { kind: 'pointed', open: true, frame: P.lime2 });
      s += tower(ctx, 5, 39, yf, 30, 118);
      s += tower(ctx, 57, 91, yf, 30, 92, { stone: 30 });
      s += Q.door(ctx, 16, yf, 11, 15, { col: P.wood, studs: true, frame: P.lime }) + Q.door(ctx, 69, yf, 10, 14, { col: P.ochre, frame: P.lime });
    }
    return s;
  }

  var T = [
    { n: 6, kind: 'dome', name: '穹顶小屋', roof: 'none', tags: ['dome'], fps: [[1, 1], [2, 1], [1, 1]], draw: domehut,
      note: 'roof 无对应 RoofId（穹顶），最近为 none',
      vnote: ['土坯方屋 + 白穹顶；roof 为穹顶，RoofId 无对应', '石灰白长屋双穹顶 + 青瓷小穹', '叙利亚式蜂巢圆锥屋（双锥）'] },
    { n: 7, kind: 'tower', name: '塔楼宅', roof: 'flat_mud', tags: ['tower_house', 'multi_storey', 'yemeni'], fps: [[1, 1], [1, 2], [2, 1]], draw: towerhouse,
      vnote: ['也门式单塔，石膏饰带 + 半月彩窗', '后高塔 + 前矮翼露台', '高低双塔 + 中间拱门连廊'] }
  ];
  var API = { T: T, cone: cone, qwin: qwin, tower: tower };
  root.TownArtAB_housesC = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
