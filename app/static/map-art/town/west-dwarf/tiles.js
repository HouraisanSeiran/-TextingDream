/*
 * 织梦 · 矮人巨石城墙：双网格 16 张（0000–1111）+ 城门 gate-h / gate-v + 矮堡塔（美术样板，尚未接入游戏）
 * 四角编码 mask = NW*8 + NE*4 + SW*2 + SE*1。瓦片内部坐标 0..48（y 向下），四角 = 四个逻辑格中心。
 * 墙沿逻辑格中心线走，墙厚 24 px（每块瓦片里占 12 px 宽的带），高 WALL_H。按 12 px 小格计算（与 west-base 同一套规则）。
 * 巨石：层高 11、块长 24、错缝 12，周期整除 48，按瓦片坐标对齐，相邻瓦片石缝接得上。墙顶方整厚垛口。
 * 浏览器挂 window.TownArtWD_tiles；Node 用 module.exports。依赖 core.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWD_core;
  var P = C.PAL, f = C.f, S = 48, G = 12, WALL_H = 44, WALK = '#a8a397';
  function bin(m) { return ('000' + m.toString(2)).slice(-4); }

  /** 4×4 小格占用：四角是墙 → 角上一格；相邻两角都是墙 → 连成边带；四角全是 → 填满 */
  function wallCells(mask) {
    var g = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]];
    var nw = mask & 8, ne = mask & 4, sw = mask & 2, se = mask & 1;
    if (nw) g[0][0] = 1; if (ne) g[0][3] = 1; if (sw) g[3][0] = 1; if (se) g[3][3] = 1;
    if (nw && ne) g[0][1] = g[0][2] = 1;
    if (sw && se) g[3][1] = g[3][2] = 1;
    if (nw && sw) g[1][0] = g[2][0] = 1;
    if (ne && se) g[1][3] = g[2][3] = 1;
    if (mask === 15) g[1][1] = g[1][2] = g[2][1] = g[2][2] = 1;
    return g;
  }
  /** 墙正面：巨石按瓦片坐标对齐；底层一道深岩勒脚；x=24 处（若在段内）开一道箭缝 */
  function stoneFace(x0, x1, yb, h, endL, endR) {
    var s = '', tones = [P.granite2, P.granite, '#a29d93', P.granite3], joints = '', courses = '', r = 0, course = 11;
    for (var y = yb; y > yb - h + 0.1; y -= course, r++) {
      var y0 = Math.max(yb - h, y - course), off = (r % 2) * 12;
      for (var k = Math.floor((x0 - off) / 24); off + k * 24 < x1; k++) {
        var bx0 = Math.max(x0, off + k * 24), bx1 = Math.min(x1, off + (k + 1) * 24);
        if (bx1 - bx0 < 0.5) continue;
        var tone = r === 0 ? P.deep : tones[((((k * 3 + r) % 4) + 4) % 4)];
        s += C.rect(bx0, y0, bx1 - bx0, y - y0, tone, 0) + C.rect(bx0, y - 1.8, bx1 - bx0, 1.8, P.shadow, 0, 0.14);
        var jx = off + k * 24;
        if (jx > x0 + 0.1 && jx < x1 - 0.1) joints += 'M' + f(jx) + ' ' + f(y) + 'V' + f(y0);
        // 凿痕：每块右下角两道短斜线，位置由块坐标决定（相邻瓦片一致）
        var hx = off + (k + 1) * 24 - 6;
        if (r > 0 && hx > x0 + 1 && hx < x1 - 3) courses += 'M' + f(hx) + ' ' + f(y - 2.5) + 'l1.8 -2.6M' + f(hx + 2) + ' ' + f(y - 2.5) + 'l1.8 -2.6';
      }
      if (y0 > yb - h + 0.1) courses += 'M' + f(x0) + ' ' + f(y0) + 'H' + f(x1);
    }
    s += C.line(courses + joints, 0.9, 0.6);
    if (x0 <= 18 && x1 >= 30) s += C.rect(22.5, yb - h * 0.72, 3, 12, P.hole, 1) + C.rect(20.5, yb - h * 0.72 - 3, 7, 3, P.granite3, 0.9);
    s += C.rect(x0, yb - h, x1 - x0, 3, P.shadow, 0, 0.16);
    var ol = 'M' + f(x0) + ' ' + f(yb) + 'H' + f(x1);
    if (endL) ol += 'M' + f(x0) + ' ' + f(yb) + 'V' + f(yb - h);
    if (endR) ol += 'M' + f(x1) + ' ' + f(yb) + 'V' + f(yb - h);
    return s + C.line(ol, 1.8);
  }
  function wallTile(ctx, mask) {
    if (!mask) return '';
    var g = wallCells(mask), H = WALL_H, s = '', cx, cy;
    function at(x, y) { return x >= 0 && x < 4 && y >= 0 && y < 4 ? g[y][x] : 2; }
    var shade = '', faces = '', tops = '', grid = '', edge = '', back = '', front = '';
    for (cy = 0; cy < 4; cy++) for (cx = 0; cx < 4; cx++) {
      if (!g[cy][cx]) continue;
      var x = cx * G, y = cy * G, ty = y - H;
      if (at(cx + 1, cy) === 0) shade += C.rect(x + G, y + 2, 6, G, P.shadow, 0, 0.18);
      if (at(cx, cy + 1) === 0) shade += C.rect(x + 3, y + G, G, 4, P.shadow, 0, 0.18);
      tops += C.rect(x, ty, G, G, WALK, 0);
      grid += 'M' + f(x) + ' ' + f(ty) + 'v' + G + 'M' + f(x) + ' ' + f(ty) + 'h' + G;
      if (at(cx, cy - 1) === 0) { // 北沿：矮垛口
        edge += 'M' + f(x) + ' ' + f(ty) + 'h' + G;
        back += C.rect(x, ty, G, 3, P.granite, 0) + C.rect(x + 1.5, ty - 6, 9, 7, P.granite2, 1.1);
      }
      if (at(cx - 1, cy) === 0) {
        edge += 'M' + f(x) + ' ' + f(ty) + 'v' + G;
        back += C.rect(x, ty, 4, G, P.granite2, 0) + C.rect(x, ty + 1.5, 4, 9, P.granite3, 1) + C.line('M' + f(x) + ' ' + f(ty + 6) + 'h4', 0.7, 0.6);
      }
      if (at(cx + 1, cy) === 0) {
        edge += 'M' + f(x + G) + ' ' + f(ty) + 'v' + G;
        back += C.rect(x + G - 4, ty, 4, G, P.granite, 0) + C.rect(x + G - 4, ty + 1.5, 4, 9, P.deep, 1) + C.line('M' + f(x + G - 4) + ' ' + f(ty + 6) + 'h4', 0.7, 0.6);
      }
      if (at(cx, cy + 1) === 0) { // 南沿：厚方垛 + 压顶石
        var e = ty + G;
        front += C.rect(x, e - 4, G, 4, P.granite, 0) + C.rect(x + 1.5, e - 12, 9, 12, P.granite2, 1.2) +
          C.rect(x + 0.8, e - 13.5, 10.4, 2.6, P.granite3, 1) + C.rect(x + 7.5, e - 11, 3, 11, P.shadow, 0, 0.15);
      }
    }
    for (cy = 0; cy < 3; cy++) {
      cx = 0;
      while (cx < 4) {
        if (g[cy][cx] && g[cy + 1][cx] === 0) {
          var a = cx;
          while (cx < 4 && g[cy][cx] && g[cy + 1][cx] === 0) cx++;
          faces += stoneFace(a * G, cx * G, (cy + 1) * G, H, a > 0, cx < 4);
        } else cx++;
      }
    }
    s += shade + faces + tops + C.line(grid, 0.6, 0.35) + back + front + C.line(edge, 1.5);
    ctx.top(-H - 8);
    return s;
  }

  // ---------- 叠加件（对齐逻辑格；局部坐标 y = 0 为逻辑格前沿，墙带在 y -36..-12） ----------
  /** 巨石门洞：梯形收口 + 巨石过梁，铜门板（两扇，铆钉铜箍） */
  function bigDoor(ctx, cx, yb, w, h, open) {
    var s = '', x0 = cx - w / 2, x1 = cx + w / 2, y = yb - h;
    var outer = C.poly([[x0 - 5, yb], [x0 - 3, y - 4], [x1 + 3, y - 4], [x1 + 5, yb]]);
    var hole = C.poly([[x0, yb], [x0 + 2, y], [x1 - 2, y], [x1, yb]]);
    s += C.path(outer, P.granite3, 1.4) + C.path(hole, P.hole, 1.2);
    if (!open) s += C.door(ctx, cx, yb, w - 1, h - 1, 'trap', { fill: P.copper, band: P.iron, bands: 3, frame: 0, step: false });
    else { // 门扇向内开，只露两条窄边
      s += C.rect(x0 + 1, y + 2, 3.5, h - 2, P.copper, 1) + C.rect(x1 - 4.5, y + 2, 3.5, h - 2, P.copper2, 1);
      s += C.rivets(x0 + 2.75, x0 + 2.75, y + h * 0.4, 1, 0.6) + C.rivets(x1 - 2.75, x1 - 2.75, y + h * 0.4, 1, 0.6);
    }
    s += C.rect(x0 - 8, y - 9, w + 16, 7, P.granite2, 1.5) + C.rivets(x0 - 5, x1 + 5, y - 5.5, 5, 0.7);
    s += C.rect(cx - 4, y - 10, 8, 9, P.granite3, 1.2);
    return s;
  }
  /** 门楼顶：平顶厚垛口 + 铜绿铜牌 */
  function keepTop(ctx, x0, x1, yt, dg) {
    var s = C.slabTop(ctx, x0, x1, yt, dg, { parapet: 3 }), n = Math.max(3, Math.round((x1 - x0) / 10)), st = (x1 - x0) / n;
    for (var i = 0; i < n; i++) if (i % 2 === 0 || n < 4) s += C.rect(x0 + i * st + 0.5, yt - 7, st - 1, 7.5, P.granite2, 1.2);
    ctx.top(yt - dg - 2);
    ctx.top(yt - 7);
    return s;
  }
  function gateH(ctx) {
    var s = '', H = WALL_H, x0 = 1, x1 = 47, yb = -6, gh = H + 20;
    s += C.groundShadow(x0, x1, yb, -42);
    s += C.blocks(ctx, x0, x1, yb, gh, { course: 11, minW: 14, maxW: 23 });
    s += bigDoor(ctx, 24, yb, 20, 30, false);
    s += C.runes(ctx, 6, 42, yb - 47, 6);
    s += C.path('M24 ' + f(yb - 58) + 'l5 4l-5 4l-5 -4Z', P.verd, 1) + C.circle(24, yb - 54, 1.3, P.ember, 0.5);
    s += keepTop(ctx, x0 - 1, x1 + 1, yb - gh, 24);
    return s;
  }
  function gateV(ctx) {
    var s = '', H = WALL_H, x0 = 9, x1 = 39, yb = -2, gh = H + 16;
    s += C.groundShadow(x0, x1, yb, -46);
    // 南北向墙段：正面是门楼侧墙，门洞朝东西，正视只看到侧壁上的门洞透光与两侧铜门扇的窄边
    s += C.blocks(ctx, x0, x1, yb, gh, { course: 11, minW: 10, maxW: 18 });
    s += bigDoor(ctx, 24, yb, 14, 26, true);
    s += C.win(ctx, 22, yb - 46, 4, 8, 'slit');
    s += keepTop(ctx, x0 - 1, x1 + 1, yb - gh, 40);
    return s;
  }
  /** 矮堡塔：方整巨石塔，四角压角石，平顶厚垛口 + 铜烟口（拐角 / 端点） */
  function towerKeep(ctx) {
    var s = '', H = WALL_H, x0 = 4, x1 = 44, yb = -4, th = H + 24;
    s += C.groundShadow(x0, x1, yb, -44);
    s += C.blocks(ctx, x0, x1, yb, th, { course: 11, minW: 12, maxW: 20 });
    s += C.rect(x0, yb - th, 5, th, P.granite3, 1.1) + C.rect(x1 - 5, yb - th, 5, th, P.deep, 1.1);
    s += C.win(ctx, 22, yb - 30, 4, 9, 'slit') + C.win(ctx, 20, yb - 54, 8, 8, 'port');
    s += C.rect(x0 - 1, yb - 40, x1 - x0 + 2, 3, P.copper, 1) + C.rivets(x0 + 3, x1 - 3, yb - 38.5, 5, 0.55);
    s += keepTop(ctx, x0 - 2, x1 + 2, yb - th, 34);
    return s;
  }

  // ---------- 汇总 ----------
  function all(wrap) {
    var out = [], m;
    for (m = 0; m < 16; m++) {
      var wid = 'west-dwarf-wall-' + bin(m), wctx = new C.Ctx(wid);
      var wb = '<g transform="translate(0 -48)">' + wallTile(wctx, m) + '</g>';
      out.push(wrap(wid, [1, 1], wb, m ? -48 - WALL_H - 8 : -48, {
        id: wid, style: 'west', race: 'dwarf', category: 'wall', kind: 'wall_dwarf_megalith', facility: 'city_wall', variant: m, mask: m,
        name: '巨石城墙 ' + bin(m), tags: ['dual_grid', 'mask_' + bin(m), 'crenellated', 'megalith'], roof: 'none',
        note: m === 0 ? '空瓦片（透明占位）' : '墙厚 24 px、高 ' + WALL_H + ' px；巨石层高 11、块长 24，按瓦片坐标对齐'
      }));
    }
    var OV = [
      ['gate-h', gateH, 'gate', 'wall_gate_h', '巨石城门（东西向墙段）', ['overlay', 'logical_cell', 'copper_door', 'gatehouse'], 'flat_mud', '放在东西向直墙的逻辑格上；梯形巨石门洞 + 铜门板，门楼平顶厚垛口'],
      ['gate-v', gateV, 'gate', 'wall_gate_v', '巨石城门（南北向墙段）', ['overlay', 'logical_cell', 'gatehouse'], 'flat_mud', '放在南北向直墙的逻辑格上；门洞朝东西，正视只露敞开的铜门扇窄边'],
      ['tower', towerKeep, 'watchtower', 'wall_tower_keep', '矮堡塔', ['overlay', 'logical_cell', 'square_tower', 'crenellated'], 'flat_mud', '放在墙的拐角或端点；方整巨石塔，平顶垛口']
    ];
    OV.forEach(function (o, k) {
      var id = 'west-dwarf-wall-' + o[0], ctx = new C.Ctx(id);
      var body = o[1](ctx);
      out.push(wrap(id, [1, 1], body, ctx.minY, {
        id: id, style: 'west', race: 'dwarf', category: 'wall', kind: o[3], facility: o[2], variant: k + 1,
        name: o[4], tags: o[5], roof: o[6], note: o[7] + '。叠加件对齐逻辑格（不是渲染格），锚点 = 逻辑格前沿中点；石板平顶最近 RoofId flat_mud'
      }));
    });
    return out;
  }

  var API = { WALL_H: WALL_H, bin: bin, wallCells: wallCells, wallTile: wallTile, gateH: gateH, gateV: gateV, towerKeep: towerKeep, all: all };
  root.TownArtWD_tiles = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
