/*
 * 织梦 · 西式资源点第二批 —— 牲畜（一）：livestock/cattle_ranch 牛场、livestock/dairy_farm 奶牛场、livestock/pig_farm 猪圈
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWS2_core;
  var P = C.P, K = C.K, f = C.f, path = C.path, line = C.line, ell = C.ell, poly = C.poly, seg = C.seg, shade = C.shade;

  /** 牛（侧身）：fill 主色，spot 斑色（null 无斑），horn 是否带角 */
  function cow(ctx, x, yb, fill, spot, flip, horn) {
    var k = flip ? -1 : 1, X = function (d) { return x + k * d; };
    var s = C.shadowEll(x + 2, yb, 14, 3);
    s += line(seg(X(-9), yb - 9, X(-9), yb) + seg(X(-5), yb - 9, X(-5), yb) + seg(X(6), yb - 9, X(6), yb) + seg(X(10), yb - 9, X(10), yb), 2, 1, P.dark);
    s += path(poly([[X(-12), yb - 20], [X(11), yb - 20], [X(13), yb - 9], [X(-12), yb - 9]]), fill, 1.2);
    if (spot) s += path(C.blob(ctx, X(-3), yb - 15, 4, 3, 5, 0.2), spot, 0) + path(C.blob(ctx, X(6), yb - 13, 3, 2.4, 5, 0.2), spot, 0);
    s += path(poly([[X(11), yb - 22], [X(18), yb - 20], [X(19), yb - 13], [X(13), yb - 13]]), fill, 1.1);
    s += ell(X(18), yb - 14, 1.6, 1.2, P.pig2, 0);
    if (horn) s += line(seg(X(12), yb - 22, X(10), yb - 26) + seg(X(15), yb - 22, X(17), yb - 26), 1.2, 1, P.bone);
    s += line(seg(X(-12), yb - 19, X(-15), yb - 10), 1.1, 1, P.dark);
    return s;
  }
  /** 猪（圆胖侧身） */
  function pig(ctx, x, yb, flip) {
    var k = flip ? -1 : 1;
    var s = C.shadowEll(x + 2, yb, 10, 2.4);
    s += line(seg(x - 5, yb - 5, x - 5, yb) + seg(x - 1, yb - 5, x - 1, yb) + seg(x + 3, yb - 5, x + 3, yb) + seg(x + 6, yb - 5, x + 6, yb), 1.6, 1, P.pig2);
    s += ell(x, yb - 8, 9, 5.5, P.pig, 1.1) + ell(x + k * 9.5, yb - 8, 2, 2.2, P.pig2, 0.8);
    s += path(poly([[x + k * 5, yb - 13], [x + k * 7, yb - 16], [x + k * 8, yb - 12]]), P.pig2, 0.6);
    return s + line('M' + f(x - k * 9) + ' ' + f(yb - 9) + 'q' + f(-k * 3) + ' -2 ' + f(-k * 1) + ' -4', 0.8, 1);
  }
  C.cow = cow; C.pig = pig;
  /** 围栏一圈（矩形，前栏低一点） */
  function pen(x0, y0, x1, y1, n) {
    return C.fence(x0, y0, x1, y0, n, 12) + C.fence(x0, y0, x0, y1, 3, 12) + C.fence(x1, y0, x1, y1, 3, 12);
  }
  C.pen = pen;

  /* 牛场：大围栏草场 + 后排牛棚（木板墙、茅顶）+ 牛群 + 饮水槽 + 干草堆 */
  C.def({
    idKind: 'site-cattle-ranch', name: '牛场', cat: 'site', resource: 'livestock', subtype: 'cattle_ranch', facility: 'stable',
    w: 5, d: 3, up: 48, roof: 'gable_thatch', tags: ['cattle', 'paddock', 'cowshed', 'water_trough', 'hay'],
    note: '牛棚 + 围栏草场；牲畜棚最近 FacilityKind 为 stable',
    draw: function (ctx, W, D) {
      var s = path(K.q(8, D - 112, W - 8, D - 6), P.leaf2, 0, 0.35);
      s += K.shed(ctx, 18, D - 108, 110, 28, 24, { wall: P.wood, roof: P.thatch, roof2: P.thatch2, door: 'open', win: 3 });
      s += pen(8, D - 106, W - 8, D - 6, 14);
      s += K.stack(ctx, 160, D - 110, 15, P.straw, P.thatch2) + K.stack(ctx, 194, D - 108, 12, P.straw, P.thatch2);
      s += C.block(150, D - 50, 46, 7, 7, P.wood, P.timber, 1.2) + path(K.q(153, D - 61, 193, D - 58), P.water, 0.8);
      var cows = [[40, 66, 0], [80, 52, 1], [118, 70, 0], [70, 26, 1], [130, 34, 0], [200, 30, 1], [214, 70, 0]];
      cows.forEach(function (c, i) { s += cow(ctx, c[0], D - c[1], i % 3 ? P.cow2 : P.wood, i % 2 ? P.cow : null, c[2], true); });
      s += C.fence(8, D - 6, 60, D - 6, 4, 12) + C.fence(96, D - 6, W - 8, D - 6, 10, 12);
      return s;
    }
  });
  C.def({
    idKind: 'prop-cattle-trough', name: '饮水槽', cat: 'prop', resource: 'livestock', subtype: 'cattle_ranch', w: 1, d: 1, up: 2, tags: ['trough', 'water'],
    draw: function (ctx, W, D) { return shade(K.q(8, D - 9, 46, D - 5)) + C.block(4, D - 8, 40, 8, 8, P.wood, P.timber, 1.2) + path(K.q(7, D - 21, 41, D - 18), P.water, 0.8); }
  });
  C.def({
    idKind: 'prop-cattle-cow', name: '牛', cat: 'prop', resource: 'livestock', subtype: 'cattle_ranch', w: 1, d: 1, up: 0, tags: ['animal', 'cattle'],
    draw: function (ctx, W, D) { return cow(ctx, 22, D - 10, P.wood, null, false, true); }
  });
  C.def({
    idKind: 'prop-cattle-hayrick', name: '干草垛', cat: 'prop', resource: 'livestock', subtype: 'cattle_ranch', w: 1, d: 1, up: 26, tags: ['hay'],
    draw: function (ctx, W, D) { return K.stack(ctx, 24, D - 8, 16, P.straw, P.thatch2); }
  });

  /** 奶罐（锡制高罐，带盖与提手） */
  function churn(x, yb, h) {
    h = h || 14;
    return C.shadowEll(x + 2, yb, 5, 1.6) + path(poly([[x - 4, yb], [x - 4, yb - h * 0.7], [x - 2.4, yb - h], [x + 2.4, yb - h], [x + 4, yb - h * 0.7], [x + 4, yb]]), P.tin, 1.1) +
      ell(x, yb - h, 2.6, 1, P.silver, 0.8) + line(seg(x - 4, yb - h * 0.35, x + 4, yb - h * 0.35), 0.8, 0.8);
  }
  /** 奶酪架：小木架 + 两层圆奶酪轮 */
  function cheeseRack(x, yb, w) {
    var s = C.post(x, yb, 26, 2.4) + C.post(x + w, yb, 26, 2.4);
    s += path(K.q(x - 2, yb - 13, x + w + 2, yb - 11), P.wood, 0.9) + path(K.q(x - 2, yb - 25, x + w + 2, yb - 23), P.wood, 0.9);
    for (var i = 0; i < Math.floor(w / 9); i++) s += path(K.q(x + 1 + i * 9, yb - 19, x + 8 + i * 9, yb - 13), P.cheese, 0.9) + path(K.q(x + 1 + i * 9, yb - 31, x + 8 + i * 9, yb - 25), P.cheese, 0.9);
    return s;
  }
  /* 奶牛场：后排挤奶棚（敞面，里有奶牛与挤奶凳）+ 左侧放牧小围场 + 前排奶罐、奶酪架 */
  C.def({
    idKind: 'site-dairy-farm', name: '奶牛场', cat: 'site', resource: 'livestock', subtype: 'dairy_farm', facility: 'stable',
    w: 4, d: 3, up: 48, roof: 'gable_thatch', tags: ['milking_shed', 'churns', 'cheese_rack', 'dairy_cows'],
    note: '挤奶棚 + 奶罐 + 奶酪架；牲畜棚最近 FacilityKind 为 stable',
    draw: function (ctx, W, D) {
      var s = path(K.q(6, D - 118, 96, D - 30), P.leaf2, 0, 0.35) + pen(6, D - 116, 96, D - 30, 6);
      s += cow(ctx, 30, D - 72, P.cow, P.cow2, false, false) + cow(ctx, 66, D - 46, P.cow, P.cow2, true, false);
      // 挤奶棚（敞面）
      s += K.shed(ctx, 108, D - 64, 78, 30, 24, { open: true, roof: P.thatch, roof2: P.thatch2 });
      s += cow(ctx, 136, D - 66, P.cow, P.cow2, false, false);
      s += path(K.q(160, D - 74, 168, D - 70), P.wood, 0.8) + churn(172, D - 66, 10);
      // 前排：乳品小屋（灰泥墙）+ 奶罐 + 奶酪架
      s += K.shed(ctx, 112, D - 8, 40, 22, 16, { wall: P.plaster, roof: P.thatch, roof2: P.thatch2, win: 1 });
      s += churn(18, D - 10) + churn(28, D - 8) + churn(40, D - 12, 12);
      s += cheeseRack(60, D - 8, 36) + cheeseRack(162, D - 8, 26);
      return s + C.tuft(ctx, 6, D - 4, 5, 3);
    }
  });
  C.def({
    idKind: 'prop-dairy-churns', name: '奶罐组', cat: 'prop', resource: 'livestock', subtype: 'dairy_farm', w: 1, d: 1, up: 4, tags: ['churn', 'milk'],
    draw: function (ctx, W, D) { return churn(14, D - 14, 16) + churn(30, D - 16, 18) + churn(23, D - 6, 15); }
  });
  C.def({
    idKind: 'prop-dairy-cheeserack', name: '奶酪架', cat: 'prop', resource: 'livestock', subtype: 'dairy_farm', w: 1, d: 1, up: 4, tags: ['cheese'],
    draw: function (ctx, W, D) { return shade(K.q(8, D - 9, 44, D - 6)) + cheeseRack(7, D - 8, 34); }
  });
  C.def({
    idKind: 'prop-dairy-cow', name: '奶牛', cat: 'prop', resource: 'livestock', subtype: 'dairy_farm', w: 1, d: 1, up: 0, tags: ['animal', 'dairy_cow'],
    draw: function (ctx, W, D) { return cow(ctx, 22, D - 10, P.cow, P.cow2, false, false); }
  });

  /* 猪圈：后排石墙低矮猪舍（石板顶）+ 泥塘围栏 + 猪群 + 食槽 + 泔水桶 */
  C.def({
    idKind: 'site-pig-farm', name: '猪圈', cat: 'site', resource: 'livestock', subtype: 'pig_farm', facility: 'stable',
    w: 4, d: 3, up: 36, roof: 'monopitch', tags: ['pigsty', 'mud_wallow', 'trough', 'swill'],
    note: '石砌猪舍 + 泥塘围栏；牲畜棚最近 FacilityKind 为 stable；猪舍为单坡石板顶',
    draw: function (ctx, W, D) {
      var s = path(C.blob(ctx, W * 0.5, D - 50, W * 0.42, 36, 9, 0.08), P.mud, 1, 0.9);
      s += K.pond(ctx, 70, D - 44, 28, 10);
      // 猪舍（三间，单坡石板顶）
      var hx = 14, hy = D - 100, hw = W - 28;
      s += shade(poly([[hx + hw, hy], [hx + hw + 8, hy - 4], [hx + hw + 8, hy - 24], [hx + hw, hy - 22]]));
      s += path(K.q(hx, hy - 22, hx + hw, hy), P.stone, 1.4);
      for (var i = 0; i < 3; i++) s += path(K.q(hx + 12 + i * hw / 3, hy - 14, hx + 28 + i * hw / 3, hy), '#2e241a', 1);
      var d = ''; for (i = 0; i < 8; i++) d += seg(hx + 4 + i * hw / 8, hy - 8 - (i % 2) * 6, hx + 10 + i * hw / 8, hy - 8 - (i % 2) * 6);
      s += line(d, 0.7, 0.5);
      s += path(poly([[hx - 4, hy - 20], [hx + hw + 4, hy - 20], [hx + hw + 2, hy - 38], [hx - 2, hy - 34]]), P.slate, 1.5);
      s += line(seg(hx, hy - 27, hx + hw, hy - 29), 0.8, 0.5);
      // 围栏
      s += pen(8, D - 96, W - 8, D - 8, 12) + C.fence(8, D - 8, W - 8, D - 8, 12, 12);
      [[40, 60, 0], [104, 70, 1], [130, 44, 0], [56, 26, 1], [150, 24, 0], [96, 22, 1]].forEach(function (p) { s += pig(ctx, p[0], D - p[1], p[2]); });
      // 食槽 + 泔水桶
      s += C.block(150, D - 66, 30, 6, 6, P.wood, P.timber, 1.2) + path(K.q(153, D - 76, 177, D - 73), P.mud, 0.7);
      s += K.barrel(28, D - 14, 6, P.wood, 10);
      return s;
    }
  });
  C.def({
    idKind: 'prop-pig-trough', name: '猪食槽', cat: 'prop', resource: 'livestock', subtype: 'pig_farm', w: 1, d: 1, up: 2, tags: ['trough'],
    draw: function (ctx, W, D) { return shade(K.q(8, D - 9, 44, D - 5)) + C.block(6, D - 8, 36, 7, 6, P.wood, P.timber, 1.2) + path(K.q(9, D - 18, 39, D - 15), P.mud, 0.7); }
  });
  C.def({
    idKind: 'prop-pig-pig', name: '猪', cat: 'prop', resource: 'livestock', subtype: 'pig_farm', w: 1, d: 1, up: 0, tags: ['animal', 'pig'],
    draw: function (ctx, W, D) { return pig(ctx, 18, D - 18, false) + pig(ctx, 30, D - 6, true); }
  });
  C.def({
    idKind: 'prop-pig-wallow', name: '泥塘', cat: 'prop', resource: 'livestock', subtype: 'pig_farm', w: 1, d: 1, up: 0, tags: ['mud'],
    draw: function (ctx, W, D) { return path(C.blob(ctx, 24, D - 20, 20, 12, 8, 0.1), P.mud, 1.1) + path(C.blob(ctx, 24, D - 20, 13, 7, 7, 0.1), P.soil2, 0.8); }
  });
})(typeof window !== 'undefined' ? window : this);
