/*
 * 织梦 · 矮人特殊建筑 B 组：矿井口、啤酒厅、祖先祠、仓库（美术样板，尚未接入游戏）
 * 局部坐标同 civic-a.js。浏览器挂 window.TownArtWD_civicB；Node 用 module.exports。
 * 依赖 core.js、parts.js、houses-b.js、civic-a.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWD_core;
  var K = isNode ? require('./parts.js') : root.TownArtWD_parts;
  var HB = isNode ? require('./houses-b.js') : root.TownArtWD_housesB;
  var SA = isNode ? require('./civic-a.js') : root.TownArtWD_civicA;
  var P = C.PAL, f = C.f;

  /** 木桶（横放，端面朝外）：中心 cx,cy 半径 r */
  function cask(cx, cy, r) {
    return C.circle(cx, cy, r, P.wood, 1) + C.circle(cx, cy, r * 0.62, 'none', 0.8, 0.7) +
      C.line('M' + f(cx - r) + ' ' + f(cy) + 'h' + f(2 * r), 0.7, 0.5) + C.circle(cx, cy, 0.9, P.iron, 0);
  }
  /** 井架：两根斜木腿 + 顶横梁 + 大绞轮 + 吊索吊斗 */
  function headframe(ctx, cx, yb, h, wr) {
    var yt = yb - h, s = '';
    s += C.line('M' + f(cx - 16) + ' ' + f(yb) + 'L' + f(cx - 5) + ' ' + f(yt) + 'M' + f(cx + 16) + ' ' + f(yb) + 'L' + f(cx + 5) + ' ' + f(yt), 3.4, 1, P.timber);
    s += C.line('M' + f(cx - 16) + ' ' + f(yb) + 'L' + f(cx - 5) + ' ' + f(yt) + 'M' + f(cx + 16) + ' ' + f(yb) + 'L' + f(cx + 5) + ' ' + f(yt), 0.7, 0.6);
    s += C.line('M' + f(cx - 12.5) + ' ' + f(yb - h * 0.33) + 'H' + f(cx + 12.5) + 'M' + f(cx - 9) + ' ' + f(yb - h * 0.64) + 'H' + f(cx + 9) +
      'M' + f(cx - 12.5) + ' ' + f(yb - h * 0.33) + 'L' + f(cx + 9) + ' ' + f(yb - h * 0.64), 2, 1, P.dark);
    s += C.rect(cx - 9, yt - 2, 18, 4, P.dark, 1.1);
    s += SA.wheel(ctx, cx, yt - wr + 1, wr, 8);
    s += C.line('M' + f(cx + wr - 1) + ' ' + f(yt - wr + 1) + 'V' + f(yb - h * 0.25), 0.9, 1, P.iron);
    s += C.path(C.poly([[cx + wr - 5, yb - h * 0.25], [cx + wr + 3, yb - h * 0.25], [cx + wr + 2, yb - h * 0.25 + 6], [cx + wr - 4, yb - h * 0.25 + 6]]), P.iron, 1);
    ctx.top(yt - 2 * wr - 4);
    return s;
  }

  var S = [];

  // mine_head：3×2 矿井口。岩坡里凿出的巨石矿门（大过梁 + 铜门敞开）、门前高木井架绞轮，矿车轨道从洞里伸出，矿石堆
  S.push({
    id: 'west-dwarf-mine-head-01', name: '矮人矿井口', facility: 'mine_head', kind: 'mine_portal', fp: [3, 2], variant: 1,
    roof: 'none', tags: ['mine', 'headframe', 'mine_track', 'embedded', 'ore'], note: '岩坡凿门 + 井架绞轮，无屋顶记 none',
    draw: function (ctx) {
      var s = '';
      s += C.groundShadow(4, 140, 0, -66);
      s += C.rockSlope(ctx, 0, 144, -6, 92, { lo: 0.5, moss: 4 });
      // 矿门：巨石门框 + 深洞 + 两扇敞开的铜门窄边
      var cx = 58, w = 30, h = 34, yb = -6, y = yb - h;
      s += C.path(C.poly([[cx - w / 2 - 8, yb], [cx - w / 2 - 5, y - 6], [cx + w / 2 + 5, y - 6], [cx + w / 2 + 8, yb]]), P.granite3, 1.5);
      s += C.blocks(ctx, cx - w / 2 - 12, cx + w / 2 + 12, y - 6, 12, { course: 12, minW: 14, maxW: 20 });
      s += C.runes(ctx, cx - w / 2 - 6, cx + w / 2 + 6, y - 12, 6);
      s += C.path(C.poly([[cx - w / 2, yb], [cx - w / 2 + 3, y], [cx + w / 2 - 3, y], [cx + w / 2, yb]]), P.hole, 1.3);
      s += C.rect(cx - w / 2 + 1, y + 3, 4, h - 3, P.copper, 1) + C.rect(cx + w / 2 - 5, y + 3, 4, h - 3, P.copper2, 1);
      s += C.circle(cx, y + 8, 1.6, P.ember, 0.6) + C.line('M' + f(cx) + ' ' + f(y) + 'v6', 0.7);
      // 门前石台 + 轨道 + 矿车
      s += C.rect(cx - w / 2 - 10, -6, w + 20, 6, P.granite2, 1.2);
      s += K.rails(cx - 12, 142, -3) + K.cart(ctx, 86, -1, 13) + K.cart(ctx, 104, -1, 12, P.copper);
      s += HB.ore(ctx, 8, -0.5, 5) + HB.ore(ctx, 20, -0.5, 4);
      // 井架（左后）
      s += headframe(ctx, 22, -10, 58, 9);
      s += K.chimney(ctx, 120, -62, 8, 16, { cap: 'ring', smoke: 3 });
      s += C.win(ctx, 96, -40, 6, 7, 'fire') + C.win(ctx, 112, -36, 6, 6, 'square');
      return s;
    }
  });

  // inn：3×2 啤酒厅。宽而矮的巨石厅，低坡石板顶 + 一排粗烟囱，大圆拱门，门边酒桶垛，挂酒杯招牌
  S.push({
    id: 'west-dwarf-inn-01', name: '矮人啤酒厅', facility: 'inn', kind: 'beer_hall', fp: [3, 2], variant: 1,
    roof: 'gable_tile', tags: ['tavern', 'casks', 'sign', 'smoke'], note: '石板低坡顶，最近 RoofId 为 gable_tile（石板代瓦）',
    draw: function (ctx) {
      var s = '', x0 = 6, x1 = 138, h = 32;
      s += C.groundShadow(x0, x1, 0, -66);
      s += C.blocks(ctx, x0, x1, 0, h, { minW: 16, maxW: 28 });
      var R = K.slabRoof(ctx, x0, x1, -h, 52, 12, { ov: 4, rivet: true });
      s += R.svg;
      [30, 72, 114].forEach(function (x, k) { s += K.chimney(ctx, x, R.yR + 6, k === 1 ? 10 : 8, k === 1 ? 18 : 13, { cap: k === 1 ? 'copper' : 'ring', smoke: 3 }); });
      s += C.runes(ctx, x0 + 4, x1 - 4, -h + 5, 5);
      s += C.door(ctx, 72, 0, 22, 24, 'arch', { fill: P.timber, band: P.copper, bands: 2, frame: 5 });
      [22, 40, 104, 122].forEach(function (x) { s += C.win(ctx, x - 4, -20, 8, 8, 'fire'); });
      // 酒杯招牌：铁臂 + 铜牌 + 一只泡沫酒杯
      s += C.line('M54 -24h-10', 1.6, 1, P.iron) + C.line('M46 -24v3M50 -24v3', 0.8);
      s += C.rect(42, -21, 12, 10, P.copper, 1) + C.rect(45, -19, 5, 6, P.wash, 0.8) + C.path('M45 -19q2.5 -2.5 5 0Z', P.paper, 0.6) +
        C.line('M50 -18q2 1 0 3', 0.8);
      // 酒桶垛：左三右二
      s += cask(14, -4.5, 4.5) + cask(23.5, -4.5, 4.5) + cask(18.75, -12.5, 4.5);
      s += cask(118, -4.5, 4.5) + cask(127.5, -4.5, 4.5);
      s += C.rect(92, -8, 14, 8, P.wood, 1) + C.line('M92 -4h14', 0.6, 0.5);
      return s;
    }
  });

  /** 祖先石像：方底座 + 敦实矮人胸像（宽肩、方盔、长须），石色 */
  function ancestor(ctx, cx, yb, sc) {
    sc = sc || 1;
    var s = C.rect(cx - 7 * sc, yb - 6 * sc, 14 * sc, 6 * sc, P.granite2, 1.1), y = yb - 6 * sc;
    s += C.path(C.poly([[cx - 8 * sc, y], [cx - 7 * sc, y - 9 * sc], [cx + 7 * sc, y - 9 * sc], [cx + 8 * sc, y]]), P.granite3, 1.2);
    s += C.path(C.poly([[cx - 4.5 * sc, y - 9 * sc], [cx - 4 * sc, y - 17 * sc], [cx + 4 * sc, y - 17 * sc], [cx + 4.5 * sc, y - 9 * sc]]), P.granite3, 1.1);
    s += C.path(C.poly([[cx - 4 * sc, y - 12 * sc], [cx + 4 * sc, y - 12 * sc], [cx + 2.5 * sc, y - 4 * sc], [cx, y - 2.5 * sc], [cx - 2.5 * sc, y - 4 * sc]]), P.granite2, 1);
    s += C.line('M' + f(cx - 1.5 * sc) + ' ' + f(y - 10 * sc) + 'v4M' + f(cx + 1.5 * sc) + ' ' + f(y - 10 * sc) + 'v4', 0.7, 0.6);
    s += C.path(C.poly([[cx - 5.5 * sc, y - 16 * sc], [cx, y - 21 * sc], [cx + 5.5 * sc, y - 16 * sc]]), P.copper, 1);
    ctx.top(y - 21 * sc);
    return s;
  }

  // temple：3×2 祖先祠。半嵌山体；台基 + 粗符文柱门廊、三角石山花与铜铸先祖纹章，两侧祖先石像，长明火盆
  S.push({
    id: 'west-dwarf-temple-01', name: '矮人祖先祠', facility: 'temple', kind: 'ancestor_shrine', fp: [3, 2], variant: 1,
    roof: 'gable_tile', tags: ['shrine', 'ancestor_statues', 'rune_pillars', 'eternal_flame', 'embedded'],
    note: '石板山花顶，最近 RoofId 为 gable_tile；后半截埋进岩坡',
    draw: function (ctx) {
      var s = '', cx = 72, x0 = 28, x1 = 116, base = 8, h = 34;
      s += C.groundShadow(6, 138, 0, -70);
      s += C.rockSlope(ctx, 0, 144, -24, 88, { lo: 0.55, moss: 3 });
      // 台基三级
      s += C.rect(16, -4, 112, 4, P.granite2, 1.2) + C.rect(20, -8, 104, 4, P.granite3, 1.2);
      s += C.blocks(ctx, x0, x1, -base, h, { minW: 14, maxW: 22 });
      s += C.door(ctx, cx, -base, 18, 24, 'arch', { fill: P.verd, band: P.copper, bands: 2, frame: 4, step: false });
      // 山花：厚石三角 + 铜纹章（锤与山）
      var yp = -base - h;
      s += C.rect(x0 - 6, yp - 5, x1 - x0 + 12, 6, P.granite2, 1.4);
      s += C.face(ctx, C.poly([[x0 - 8, yp - 5], [cx, yp - 26], [x1 + 8, yp - 5]]), P.granite3,
        C.path(C.poly([[cx, yp - 26], [x1 + 8, yp - 5], [cx + 4, yp - 5]]), P.shadow, 0, 0.15), 1.6);
      s += C.path(C.poly([[x0 - 11, yp - 4], [cx, yp - 29], [x1 + 11, yp - 4], [x1 + 7, yp - 4], [cx, yp - 25], [x0 - 7, yp - 4]]), P.slate, 1.3);
      s += C.circle(cx, yp - 13, 6, P.copper, 1.1) + C.path(C.poly([[cx - 4, yp - 10], [cx - 1, yp - 16], [cx + 1, yp - 13], [cx + 2.5, yp - 15.5], [cx + 4.5, yp - 10]]), P.verd, 0.8);
      ctx.top(yp - 29);
      // 符文柱四根
      [x0 + 6, x0 + 24, x1 - 24, x1 - 6].forEach(function (x) { s += K.pillar(ctx, x, -base, 10, h, { rune: true, band: true }); });
      // 两侧祖先像 + 长明火盆
      s += ancestor(ctx, 12, -1, 1.15) + ancestor(ctx, 132, -1, 1.15);
      [cx - 20, cx + 20].forEach(function (x) {
        s += C.rect(x - 1.2, -18, 2.4, 10, P.iron, 0.8) + C.path('M' + f(x - 4.5) + ' -18h9l-2 3h-5Z', P.copper, 0.9) +
          C.path('M' + f(x - 3) + ' -18q1 -4 3 -6q0 3 1.5 2q1 2 -1.5 4Z', P.fire, 0.6) + C.path('M' + f(x - 1) + ' -18q0.5 -2 1.4 -3q0.4 1.6 0.8 3Z', P.ember, 0);
      });
      return s;
    }
  });

  // warehouse：2×2 石库房。厚墙无窗，宽铜卷帘式大门，屋顶吊臂起重架，门前货箱和矿锭垛
  S.push({
    id: 'west-dwarf-warehouse-01', name: '矮人石库房', facility: 'warehouse', kind: 'stone_storehouse', fp: [2, 2], variant: 1,
    roof: 'flat_mud', tags: ['storage', 'crane', 'crates', 'ingots'], note: '石板平顶 + 吊臂，最近 RoofId flat_mud',
    draw: function (ctx) {
      var s = '', x0 = 4, x1 = 88, h = 40;
      s += C.groundShadow(x0, x1, 0, -70);
      s += C.blocks(ctx, x0, x1, 0, h, { minW: 18, maxW: 30 }) + C.slabTop(ctx, x0, x1, -h, 50);
      s += HA_cornice(x0, x1, -h);
      s += C.door(ctx, 46, 0, 30, 26, 'lintel', { fill: P.copper, band: P.iron, bands: 4, frame: 5, split: false });
      s += C.win(ctx, 14, -30, 4, 8, 'slit') + C.win(ctx, 76, -30, 4, 8, 'slit');
      // 吊臂：屋顶立柱 + 斜臂 + 吊钩货包
      s += C.line('M70 ' + f(-h - 6) + 'V' + f(-h - 34), 3, 1, P.timber) + C.line('M70 ' + f(-h - 32) + 'L92 ' + f(-h - 24), 2.4, 1, P.timber);
      s += C.line('M70 ' + f(-h - 6) + 'V' + f(-h - 34) + 'M70 ' + f(-h - 32) + 'L92 ' + f(-h - 24), 0.6, 0.6);
      s += C.line('M90 ' + f(-h - 24.5) + 'V' + f(-h + 6), 0.8, 1, P.iron) + C.rect(86, -h + 6, 8, 7, P.wood, 1) + C.line('M86 ' + f(-h + 9.5) + 'h8', 0.6, 0.6);
      ctx.top(-h - 36);
      // 门前货箱 + 铜锭垛
      s += C.rect(8, -9, 9, 9, P.wood, 1) + C.rect(17, -7, 7, 7, P.wood, 1) + C.rect(10, -15, 7, 6, P.timber, 1);
      var ing = '';
      for (var r = 0; r < 3; r++) for (var k = 0; k < 3 - r; k++) {
        var ix = 68 + k * 5.5 + r * 2.75, iy = -3 * (r + 1);
        ing += C.path(C.poly([[ix, iy + 3], [ix + 0.8, iy], [ix + 4.2, iy], [ix + 5, iy + 3]]), (k + r) % 2 ? P.copper : P.copper2, 0.7);
      }
      s += ing;
      return s;
    }
  });
  function HA_cornice(x0, x1, y) {
    var s = C.rect(x0 - 2, y - 4, x1 - x0 + 4, 4.5, P.granite2, 1.3);
    for (var x = x0 + 6; x < x1 - 2; x += 12) s += C.rect(x - 1.8, y + 0.5, 3.6, 2.6, P.granite, 0.8);
    return s;
  }

  var API = { S: S, cask: cask, headframe: headframe, ancestor: ancestor };
  root.TownArtWD_civicB = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
