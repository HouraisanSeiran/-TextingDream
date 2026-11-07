/*
 * 织梦 · 西式资源点 —— 奇幻：魔力晶矿 mana、龙骨坑 dragonbone
 * draw(ctx, W, D) 在“地面坐标”里画：占地 x∈[0,W]、y∈[0,D]，y=D 是前沿；高度画成负 y。
 * 仍按木刻线描 + 淡彩：晶体只用平涂两色（亮面/暗面），不加发光滤镜。
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWS_core;
  var P = C.P, f = C.f, path = C.path, line = C.line, ell = C.ell, poly = C.poly, seg = C.seg, shade = C.shade;

  /** 一根晶柱：底 (x, yb)，高 h，宽 w，倾角 lean；左亮右暗 */
  function crystal(x, yb, h, w, lean, a, b) {
    var tx = x + lean, ty = yb - h, hw = w / 2;
    var L = [x - hw, yb], R = [x + hw, yb], Lt = [tx - hw * 0.8, ty + w * 0.9], Rt = [tx + hw * 0.8, ty + w * 0.9], T = [tx, ty], M = [x + lean * 0.2, yb];
    return path(poly([L, Lt, T, Rt, R]), b || P.mana2, 1.2) + path(poly([L, Lt, T, [tx, ty + w], M]), a || P.mana, 0) +
      line(poly([Lt, T, Rt], true) + seg(tx, ty + w * 0.2, x + lean * 0.2, yb - 1), 0.8, 0.6);
  }
  /** 一簇晶体 */
  function cluster(ctx, cx, yb, s0, n) {
    var s = C.shadowEll(cx + 4, yb, s0 * 1.4, s0 * 0.35);
    var ord = [];
    for (var i = 0; i < n; i++) ord.push({ dx: (i - (n - 1) / 2) * s0 * 0.45 + ctx.rnd(-2, 2), h: s0 * ctx.rnd(0.9, 1.8) * (1 - Math.abs(i - (n - 1) / 2) * 0.18) });
    ord.forEach(function (o) { s += crystal(cx + o.dx, yb - ctx.rnd(0, 2), o.h, s0 * 0.42, o.dx * 0.35, P.mana, P.mana2); });
    return s;
  }
  C.crystal = crystal; C.cluster = cluster;

  /** 刻符文的立石（守护石） */
  function runestone(ctx, x, yb, h, w) {
    var s = shade(poly([[x + w / 2, yb], [x + w / 2 + 10, yb - 3], [x + w / 2 + 6, yb - h * 0.6], [x + w / 2, yb - h * 0.6]]));
    var d = poly([[x - w / 2, yb], [x - w / 2 - 1, yb - h * 0.75], [x - w * 0.2, yb - h], [x + w * 0.3, yb - h + 2], [x + w / 2, yb - h * 0.7], [x + w / 2 + 1, yb]]);
    s += path(d, P.stone2, 1.6);
    s += path(poly([[x - w / 2 - 1, yb - h * 0.75], [x - w * 0.2, yb - h], [x + w * 0.05, yb - h * 0.6], [x - w * 0.1, yb]]).replace(/Z$/, '') + 'L' + f(x - w / 2) + ' ' + f(yb) + 'Z', P.stone, 0);
    // 符文：竖杠 + 斜枝，淡蓝填
    var r = '', cx = x + 1, y0 = yb - h * 0.78;
    r += seg(cx, y0, cx, y0 + h * 0.5) + seg(cx, y0 + 4, cx + 5, y0 - 1) + seg(cx, y0 + 10, cx - 5, y0 + 5) + seg(cx, y0 + h * 0.3, cx + 5, y0 + h * 0.36);
    s += line(r, 2.4, 1, P.mana2) + line(r, 0.9, 1);
    return s;
  }
  C.runestone = runestone;

  /* 魔力晶矿：岩坑里露出大晶簇 + 木栈道 + 围成半圈的符文守护石 */
  C.def({
    idKind: 'site-manamine', name: '魔力晶簇矿坑', cat: 'site', resource: 'mana', facility: 'mine_head',
    w: 4, d: 3, up: 64, tags: ['crystal_cluster', 'open_pit', 'runestones'],
    note: '奇幻资源：露天晶簇矿坑，矿坑后沿立一圈守护符文石；按矿井记 mine_head',
    draw: function (ctx, W, D) {
      var s = '', cx = W / 2, cy = D - 66;
      s += C.pit(ctx, cx, cy, 80, 40, P.stone2, P.stone3, '#6f6a72', 16);
      // 后排守护石（坑后沿）
      s += runestone(ctx, 26, cy - 22, 44, 14) + runestone(ctx, cx, cy - 36, 50, 16) + runestone(ctx, W - 26, cy - 22, 44, 14);
      // 坑中晶簇
      s += cluster(ctx, cx - 18, cy + 14, 22, 5) + cluster(ctx, cx + 30, cy + 10, 14, 4);
      // 下坑的木栈道（左前斜下）
      s += path(poly([[20, D - 10], [40, D - 10], [cx - 34, cy + 14], [cx - 46, cy + 14]]), P.wood, 1.3);
      var pl = '';
      for (var i = 1; i < 7; i++) { var t = i / 7; pl += seg(20 + (cx - 66) * t, D - 10 + (cy + 24 - D) * t, 40 + (cx - 74) * t, D - 10 + (cy + 24 - D) * t); }
      s += line(pl, 0.7, 0.55);
      // 采下的晶块放在木箱里
      s += C.block(W - 70, D - 8, 30, 8, 14, P.wood, P.timber, 1.3);
      s += crystal(W - 62, D - 30, 14, 7, -2) + crystal(W - 52, D - 30, 18, 8, 2) + crystal(W - 44, D - 30, 11, 6, 3);
      return s;
    }
  });
  C.def({
    idKind: 'prop-manacluster', name: '魔力晶簇', cat: 'prop', resource: 'mana', w: 1, d: 1, up: 10, tags: ['crystal'],
    draw: function (ctx, W, D) { return C.heap(ctx, 24, D - 4, 20, 8, P.stone3, P.stone2, P.stone, 5) + cluster(ctx, 24, D - 8, 16, 4); }
  });
  C.def({
    idKind: 'prop-runestone', name: '守护符文石', cat: 'prop', resource: 'mana', w: 1, d: 1, up: 12, tags: ['ward', 'runes'],
    draw: function (ctx, W, D) { return runestone(ctx, 22, D - 6, 52, 18); }
  });
  C.def({
    idKind: 'prop-manacrates', name: '晶块货箱', cat: 'prop', resource: 'mana', w: 1, d: 1, up: 0, tags: ['crate'],
    draw: function (ctx, W, D) {
      var s = shade(poly([[4, D - 4], [46, D - 4], [47, D + 2], [5, D + 2]]));
      s += C.block(4, D - 4, 22, 8, 14, P.wood, P.timber, 1.2) + C.block(24, D - 4, 20, 8, 12, P.wood, P.timber, 1.2);
      s += crystal(10, D - 24, 12, 6, -1) + crystal(18, D - 24, 16, 7, 1) + crystal(33, D - 22, 13, 6, 2);
      return s + line(seg(4, D - 12, 26, D - 12) + seg(24, D - 11, 44, D - 11), 0.7, 0.5);
    }
  });
  /* 晶屑地面：灰紫岩地 + 小晶粒 */
  C.groundSet({
    idKind: 'ground-crystalgrit', name: '晶屑岩地', resource: 'mana', base: '#b4afb0', tags: ['crystal'],
    scatter: function (ctx, v) { return C.scatter(ctx, 8 + v, 'grit'); },
    item: function (sub, it, x, y) {
      if (it.k < 0.3) return crystal(x, y, 5, 2.6, 0.6, P.mana, P.mana2).replace(/stroke-width="1.2"/, 'stroke-width="0.7"');
      return C.rect(x, y, 2, 1.4, it.k < 0.65 ? P.stone3 : P.mana2, 0, 0.8);
    }
  });

  /* ---------- 龙骨坑 dragonbone ---------- */
  /** 一根肋骨弧：从脊椎 (x, y) 弯向地面 (x + dx, yb) */
  function rib(x, y, dx, yb, w) {
    var mx = x + dx * 1.1, my = y + (yb - y) * 0.25;
    var d = 'M' + f(x - w / 2) + ' ' + f(y) + 'Q' + f(mx - w / 2) + ' ' + f(my) + ' ' + f(x + dx - w * 0.3) + ' ' + f(yb) +
      'L' + f(x + dx + w * 0.3) + ' ' + f(yb) + 'Q' + f(mx + w / 2) + ' ' + f(my + 2) + ' ' + f(x + w / 2) + ' ' + f(y) + 'Z';
    return path(d, P.bone, 1.2);
  }
  /** 龙头骨（侧面，朝左）：长吻 + 眼窝 + 角 */
  function skull(x, yb) {
    var s = path('M' + f(x) + ' ' + f(yb - 4) + 'L' + f(x + 6) + ' ' + f(yb - 16) + 'Q' + f(x + 30) + ' ' + f(yb - 22) + ' ' + f(x + 42) + ' ' + f(yb - 30) +
      'L' + f(x + 56) + ' ' + f(yb - 26) + 'L' + f(x + 58) + ' ' + f(yb - 6) + 'Q' + f(x + 30) + ' ' + f(yb + 2) + ' ' + f(x) + ' ' + f(yb - 4) + 'Z', P.bone, 1.5);
    s += path(poly([[x + 42, yb - 30], [x + 62, yb - 48], [x + 66, yb - 46], [x + 52, yb - 27]]), P.bone2, 1.2);   // 角
    s += ell(x + 44, yb - 18, 5, 4, '#2e241a', 1) + ell(x + 22, yb - 12, 3.5, 2.2, '#2e241a', 0.8);
    var t = '';
    for (var i = 0; i < 6; i++) t += seg(x + 6 + i * 5, yb - 5, x + 7 + i * 5, yb - 1);
    return s + line(t, 1, 1);
  }
  C.def({
    idKind: 'site-dragondig', name: '龙骨发掘场', cat: 'site', resource: 'dragonbone', facility: null,
    w: 5, d: 3, up: 72, tags: ['excavation', 'scaffold', 'giant_skeleton'],
    note: '发掘坑里半埋着巨龙骨架（头骨、脊椎、成排肋骨），坑边搭木脚手架与吊绳；facility 为 null',
    draw: function (ctx, W, D) {
      var s = '', i, cx = W / 2, cy = D - 56;
      s += C.pit(ctx, cx, cy, 108, 44, P.soil, P.soil2, P.mud, 14);
      // 后排脚手架（坑后沿）：立杆 + 横杆 + 斜撑
      var sx0 = 30, sx1 = W - 30, sb = cy - 30;
      var sc = '';
      for (i = 0; i <= 4; i++) sc += seg(sx0 + i * (sx1 - sx0) / 4, sb, sx0 + i * (sx1 - sx0) / 4, sb - 64);
      sc += seg(sx0, sb - 30, sx1, sb - 30) + seg(sx0, sb - 60, sx1, sb - 60);
      for (i = 0; i < 4; i++) sc += seg(sx0 + i * (sx1 - sx0) / 4, sb, sx0 + (i + 1) * (sx1 - sx0) / 4, sb - 30);
      s += line(sc, 2.6, 1, P.dark) + line(sc, 1, 1, P.wood);
      s += path(poly([[sx0, sb - 33], [sx1, sb - 33], [sx1, sb - 29], [sx0, sb - 29]]), P.wood, 1);
      // 脊椎（一串椎骨）+ 肋骨
      var spY = cy + 4, spX0 = cx - 60, spX1 = cx + 80;
      for (i = 0; i < 12; i++) { var t = i / 11; s += rib(spX0 + 10 + t * 110, spY - 2, 8 - t * 4, cy + 26 - Math.abs(t - 0.4) * 10, 5); }
      var vb = '';
      for (i = 0; i <= 18; i++) { var x = spX0 + (spX1 - spX0) * i / 18, y = spY - Math.sin(i / 18 * Math.PI) * 10; s += ell(x, y, 4.4, 3.4, P.bone, 1); vb += seg(x, y - 3, x, y - 7); }
      s += line(vb, 1.6, 1, P.bone2);
      s += skull(spX0 - 64, cy + 18);
      // 吊绳从脚手架垂下
      s += line(seg(cx + 10, sb - 60, cx + 10, spY - 10) + seg(cx + 60, sb - 60, cx + 52, spY - 6), 0.9, 1);
      // 坑边的工具：铁锹与刷子桶
      s += line(seg(W - 40, D - 6, W - 30, D - 34), 1.6, 1, P.timber) + path(poly([[W - 44, D - 8], [W - 38, D - 10], [W - 37, D - 2], [W - 43, D - 1]]), P.iron, 0.8);
      s += path(poly([[W - 26, D - 18], [W - 14, D - 18], [W - 15, D - 4], [W - 25, D - 4]]), P.wood, 1.1);
      return s;
    }
  });
  C.def({
    idKind: 'prop-bonepile', name: '龙骨堆', cat: 'prop', resource: 'dragonbone', w: 1, d: 1, up: 4, tags: ['bones'],
    draw: function (ctx, W, D) {
      var s = C.shadowEll(26, D - 5, 20, 4);
      s += path('M4 ' + f(D - 8) + 'L40 ' + f(D - 18) + 'q6 -3 6 2q0 4 -6 4L6 ' + f(D - 2) + 'q-5 1 -4 -3z', P.bone, 1.2);   // 长骨
      s += rib(12, D - 30, 22, D - 6, 4) + rib(20, D - 34, 20, D - 6, 4);
      for (var i = 0; i < 3; i++) s += ell(30 + i * 6, D - 6 - i, 4, 3, P.bone, 0.9);
      return s;
    }
  });
  C.def({
    idKind: 'prop-scaffold', name: '发掘脚手架', cat: 'prop', resource: 'dragonbone', w: 1, d: 1, up: 30, tags: ['scaffold', 'ladder'],
    draw: function (ctx, W, D) {
      var s = shade(poly([[6, D - 4], [44, D - 4], [46, D + 2], [8, D + 2]]));
      var sc = seg(8, D - 4, 8, D - 76) + seg(40, D - 4, 40, D - 76) + seg(6, D - 40, 42, D - 40) + seg(6, D - 72, 42, D - 72) + seg(8, D - 4, 40, D - 40) + seg(8, D - 40, 40, D - 72);
      s += line(sc, 2.6, 1, P.dark) + line(sc, 1, 1, P.wood);
      s += path(poly([[4, D - 44], [44, D - 44], [44, D - 40], [4, D - 40]]), P.wood, 1);
      s += line(seg(30, D - 72, 30, D - 46), 0.9, 1) + ell(30, D - 50, 4, 3, P.bone, 0.9);
      return s;
    }
  });
  C.def({
    idKind: 'prop-tooltent', name: '发掘工具帐', cat: 'prop', resource: 'dragonbone', w: 1, d: 1, up: 18, tags: ['tent', 'tools'],
    draw: function (ctx, W, D) {
      var s = shade(poly([[6, D - 4], [46, D - 4], [47, D + 2], [7, D + 2]]));
      s += path(poly([[4, D - 4], [24, D - 58], [44, D - 4]]), P.paper, 1.5);
      s += path(poly([[24, D - 58], [44, D - 4], [30, D - 4]]), P.wash, 1);
      s += path(poly([[18, D - 4], [24, D - 26], [28, D - 4]]), '#2e241a', 1);
      return s + line(seg(24, D - 58, 24, D - 64), 1.6, 1, P.timber) + line(seg(4, D - 4, 0, D) + seg(44, D - 4, 48, D), 0.8, 0.8);
    }
  });
  /* 发掘坑土地：翻开的黄土 + 碎骨片 + 定位木桩和绳格 */
  C.groundSet({
    idKind: 'ground-digsoil', name: '发掘翻土地', resource: 'dragonbone', base: P.mud, tags: ['excavation'],
    under: function () { return line('M6 10q5 -2 9 1M28 18q6 -2 10 1M10 34q4 -2 8 1M30 40q5 -1 8 1', 0.7, 0.4, P.soil2); },
    scatter: function (ctx, v) { return C.scatter(ctx, 7 + v, 'clod'); },
    item: function (sub, it, x, y) {
      if (it.k < 0.2) return C.ell(x, y, 2.6, 1.3, P.bone, 0.6);
      return C.rect(x, y, 2.4, 1.6, it.k < 0.6 ? P.soil : P.soil2, 0, 0.9);
    }
  });
})(typeof window !== 'undefined' ? window : this);
