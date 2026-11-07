/*
 * 织梦 · 西式精灵族双网格城墙：活体荆棘藤墙 × 16 + 藤拱城门 gate-h / gate-v + 树冠哨台（美术样板，尚未接入游戏）
 * 四角编码 mask = NW*8 + NE*4 + SW*2 + SE*1。瓦片内部坐标 0..48（y 向下），四角 = 四个逻辑格中心。
 * 墙沿逻辑格中心线走，墙厚 24 px（每块瓦片里占 12 px 宽的带），高 WALL_H；按 12 px 小格计算。
 * 正面编藤纹理周期 12、银白木桩周期 24，都整除 48，相邻瓦片能接上。
 * 浏览器挂 window.TownArtWE_tiles；Node 用 module.exports。依赖 core.js、parts.js、forms.js、houses-a.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWE_core;
  var Q = isNode ? require('./parts.js') : root.TownArtWE_parts;
  var F = isNode ? require('./forms.js') : root.TownArtWE_forms;
  var HA = isNode ? require('./houses-a.js') : root.TownArtWE_housesA;
  var P = C.P, f = C.f, line = C.line, path = C.path, rect = C.rect, S = 48, G = 12, WALL_H = 34;
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
  /** 墙正面：暗树皮底 + 两组交叉编藤（周期 12）+ 刺 + 苔石勒脚；银白木桩单独返回（画在墙顶之后） */
  function thornFace(ctx, x0, x1, yb, h, endL, endR) {
    var d1 = '', d2 = '', th = '', posts = '', k, r;
    for (k = Math.floor(x0 / 12) * 12 - 12; k < x1 + 12; k += 12) {
      for (r = 0; r < 3; r++) {
        var y0 = yb - 7 - r * 10;
        d1 += 'M' + f(k) + ' ' + f(y0) + 'Q' + f(k + 6) + ' ' + f(y0 - 8) + ' ' + f(k + 12) + ' ' + f(y0);
        d2 += 'M' + f(k) + ' ' + f(y0 - 6) + 'Q' + f(k + 6) + ' ' + f(y0 + 2) + ' ' + f(k + 12) + ' ' + f(y0 - 6);
        th += 'M' + f(k + 5) + ' ' + f(y0 - 4) + 'l1 -2.8l1 2.8Z' + 'M' + f(k + 11) + ' ' + f(y0 - 3) + 'l1.6 1.6l-2 0.6Z';
      }
    }
    var tex = line(d2, 2.6, 1, P.bark) + line(d1, 3, 1) + line(d1, 1.8, 1, P.leaf2) + line(d2, 0.5, 0.5) +
      path(th, P.silver2, 0.5) + rect(x0, yb - h, x1 - x0, 2.5, P.shadow, 0, 0.2);
    tex += rect(x0, yb - 4, x1 - x0, 4, P.stone2, 0) + line('M' + f(x0) + ' ' + f(yb - 4) + 'H' + f(x1), 0.8, 0.6);
    var s = C.face(ctx, C.rectD(x0, yb - h, x1 - x0, h), P.bark2, tex, 0);
    var ol = 'M' + f(x0) + ' ' + f(yb) + 'H' + f(x1);
    if (endL) ol += 'M' + f(x0) + ' ' + f(yb) + 'V' + f(yb - h);
    if (endR) ol += 'M' + f(x1) + ' ' + f(yb) + 'V' + f(yb - h);
    s += line(ol, 1.6);
    // 银白木桩：x ≡ 12 (mod 24)，尖头冒出墙顶
    for (k = Math.ceil((x0 - 12) / 24) * 24 + 12; k < x1; k += 24) {
      if (k - 2 < x0 || k + 2 > x1) continue;
      posts += path('M' + f(k - 2) + ' ' + f(yb - 1) + 'V' + f(yb - h - 1) + 'L' + f(k) + ' ' + f(yb - h - 5) + 'L' + f(k + 2) + ' ' + f(yb - h - 1) + 'V' + f(yb - 1) + 'Z', P.silver, 1) +
        line('M' + f(k + 0.9) + ' ' + f(yb - 2) + 'V' + f(yb - h), 0.8, 1, P.silver3);
    }
    return { face: s, posts: posts };
  }
  function wallTile(ctx, mask) {
    if (!mask) return '';
    var g = wallCells(mask), H = WALL_H, cx, cy;
    function at(x, y) { return x >= 0 && x < 4 && y >= 0 && y < 4 ? g[y][x] : 2; }
    var shade = '', faces = '', posts = '', tops = '', tex = '', back = '', front = '';
    for (cy = 0; cy < 4; cy++) for (cx = 0; cx < 4; cx++) {
      if (!g[cy][cx]) continue;
      var x = cx * G, y = cy * G, ty = y - H;
      if (at(cx + 1, cy) === 0) shade += rect(x + G, y + 2, 5, G, P.shadow, 0, 0.18);
      if (at(cx, cy + 1) === 0) shade += rect(x + 3, y + G, G, 4, P.shadow, 0, 0.18);
      tops += rect(x - 0.3, ty - 0.3, G + 0.6, G + 0.6, P.leaf, 0);
      tex += 'M' + f(x + 2) + ' ' + f(ty + 5) + 'q2 -2.6 4 0M' + f(x + 6) + ' ' + f(ty + 10) + 'q2 -2.6 4 0';
      if ((cx + cy) % 2 === 0) front += C.circle(x + 9, ty + 4, 1.1, P.silver, 0.5);
      // 外缘叶团：北、西亮，东暗，南沿垂下
      if (at(cx, cy - 1) === 0) back += path('M' + f(x) + ' ' + f(ty + 1) + 'Q' + f(x + 3) + ' ' + f(ty - 4) + ' ' + f(x + 6) + ' ' + f(ty + 1) +
        'Q' + f(x + 9) + ' ' + f(ty - 4) + ' ' + f(x + 12) + ' ' + f(ty + 1) + 'Z', P.moss, 1.1);
      if (at(cx - 1, cy) === 0) back += path('M' + f(x + 1) + ' ' + f(ty) + 'Q' + f(x - 4) + ' ' + f(ty + 3) + ' ' + f(x + 1) + ' ' + f(ty + 6) +
        'Q' + f(x - 4) + ' ' + f(ty + 9) + ' ' + f(x + 1) + ' ' + f(ty + 12) + 'Z', P.moss, 1.1);
      if (at(cx + 1, cy) === 0) back += path('M' + f(x + 11) + ' ' + f(ty) + 'Q' + f(x + 16) + ' ' + f(ty + 3) + ' ' + f(x + 11) + ' ' + f(ty + 6) +
        'Q' + f(x + 16) + ' ' + f(ty + 9) + ' ' + f(x + 11) + ' ' + f(ty + 12) + 'Z', P.leaf2, 1.1);
      if (at(cx, cy + 1) === 0) {
        var e = ty + G;
        front += path('M' + f(x) + ' ' + f(e - 1) + 'Q' + f(x + 3) + ' ' + f(e + 4) + ' ' + f(x + 6) + ' ' + f(e - 1) +
          'Q' + f(x + 9) + ' ' + f(e + 4) + ' ' + f(x + 12) + ' ' + f(e - 1) + 'Z', P.leaf, 1.1);
        front += path('M' + f(x + 2.5) + ' ' + f(e - 1.5) + 'l1 -3l1 3ZM' + f(x + 8.5) + ' ' + f(e - 1.5) + 'l1 -3l1 3Z', P.silver2, 0.5);
      }
    }
    // 正面：每行连续的一段
    for (cy = 0; cy < 3; cy++) {
      cx = 0;
      while (cx < 4) {
        if (g[cy][cx] && g[cy + 1][cx] === 0) {
          var a = cx;
          while (cx < 4 && g[cy][cx] && g[cy + 1][cx] === 0) cx++;
          var tf = thornFace(ctx, a * G, cx * G, (cy + 1) * G, H, a > 0, cx < 4);
          faces += tf.face; posts += tf.posts;
        } else cx++;
      }
    }
    // 最南一行（cy=3）的正面属于下方瓦片的第 0 行，这里不画
    ctx.top(-H - 6);
    return shade + faces + tops + line(tex, 0.7, 0.45) + back + front + posts;
  }

  // ---------- 叠加件（对齐逻辑格；局部坐标 y = 0 为逻辑格前沿，墙带在 y -36..-12） ----------
  /** 藤拱门洞：两根粗藤柱拱成尖弧，门洞里垂一挂藤帘（升起一半） */
  function vineGate(ctx, x, yb, w, h) {
    var s = '', d = Q.archD(x, yb, w, h, 0.75), ring = Q.archD(x - 4, yb, w + 8, h + 5, 0.75);
    s += C.face(ctx, ring, P.bark2, line(Q.archD(x - 2, yb, w + 4, h + 2.5, 0.75), 1.6, 1, P.bark), 1.6);
    s += path(d, '#3b2d1f', 1.3);
    var cur = '';
    for (var cx = x + 2.5; cx < x + w - 1; cx += 3.2) cur += 'M' + f(cx) + ' ' + f(yb - h + 3) + 'V' + f(yb - h * 0.55 + Math.sin(cx) * 1.5);
    s += C.clipped(ctx, d, line(cur, 1.4, 1, P.leaf2) + line(cur, 0.4, 0.5));
    // 拱上绕藤开花
    var L = [[x - 2, yb - 1], [x - 3, yb - h * 0.45], [x + w * 0.15, yb - h * 0.85], [x + w / 2, yb - h - 3.5]];
    var R = [[x + w + 2, yb - 1], [x + w + 3, yb - h * 0.45], [x + w * 0.85, yb - h * 0.85], [x + w / 2, yb - h - 3.5]];
    s += Q.vine(ctx, L, { step: 4, sw: 1.4, flowers: true }) + Q.vine(ctx, R, { step: 4, sw: 1.4, flowers: true });
    return s;
  }
  /** 门上月光石徽：尖叶形石牌 + 月牙 */
  function crest(cx, cy) {
    return path(Q.leafD(cx, cy + 6, 12, -Math.PI / 2, 2.6), P.moon, 1) +
      path('M' + f(cx + 1.2) + ' ' + f(cy - 2.6) + 'A2.6 2.6 0 1 0 ' + f(cx + 1.2) + ' ' + f(cy + 2.6) + 'A2 2 0 1 1 ' + f(cx + 1.2) + ' ' + f(cy - 2.6) + 'Z', P.silver, 0.5);
  }
  function gateH(ctx) {
    var s = '', x0 = 2, x1 = 46, yb = -8, gh = WALL_H + 14;
    s += C.groundShadow(x0, x1, yb, -40);
    // 两侧粗银白木门柱
    s += F.wall(ctx, x0, x1, yb, gh, { mat: 'bark' });
    s += vineGate(ctx, 14, yb, 20, 30);
    [[x0 + 1, 8], [x1 - 9, 8]].forEach(function (p) {
      s += C.face(ctx, C.rectD(p[0], yb - gh - 4, p[1], gh + 4), P.silver, F.wallTex(ctx, 'silver', p[0], yb - gh - 4, p[1], gh + 4) +
        rect(p[0] + p[1] - 2.5, yb - gh - 4, 2.5, gh + 4, P.shadow, 0, 0.15), 1.4);
      s += Q.lamp(ctx, p[0] + p[1] / 2, yb - gh - 4, 6, p[0] < 20 ? -1 : 1);
    });
    s += crest(24, yb - 38);
    // 门楼叶舟顶
    s += F.roofLeaf(ctx, { x0: x0 + 4, x1: x1 - 4, yE: yb - gh, D: 22, R: 8, mat: 'leaf', curl: 6, ov: 2 }).svg;
    s += Q.vine(ctx, [[x0 + 3, yb - 2], [x0 + 5, yb - 18], [x0 + 3, yb - 34]], { step: 4.5, flowers: true });
    return s;
  }
  function gateV(ctx) {
    var s = '', x0 = 10, x1 = 38, yb = -4, gh = WALL_H + 12;
    s += C.groundShadow(x0, x1, yb, -44);
    // 东西两侧敞开的藤编门扇（门洞朝东西，正视只露门扇）
    [[2, 9], [39, 46]].forEach(function (p) {
      var d = C.rectD(p[0], yb - 24, p[1] - p[0], 24), w = '';
      for (var y = yb - 4; y > yb - 24; y -= 4) w += 'M' + f(p[0]) + ' ' + f(y) + 'q' + f((p[1] - p[0]) / 2) + ' -2 ' + f(p[1] - p[0]) + ' 0';
      s += C.face(ctx, d, P.bark2, line(w, 1, 0.7), 1.2);
    });
    s += F.wall(ctx, x0, x1, yb, gh, { mat: 'bark' });
    s += Q.win(ctx, 22, yb - 20, 4, 9) + crest(24, yb - 34);
    s += Q.vine(ctx, [[x0 + 2, yb - 2], [x0 + 3, yb - 20], [x0 + 1, yb - 40]], { step: 4.5, flowers: true });
    s += Q.vine(ctx, [[x1 - 2, yb - 2], [x1 - 3, yb - 24]], { step: 4.5 });
    s += F.roofGable(ctx, { x0: x0 - 2, x1: x1 + 2, yE: yb - gh, D: 34, R: 15, mat: 'leaf', ov: 2 }).svg;
    return s;
  }
  /** 树冠哨台：一根细树干撑起环台，台上叶舟小顶，挂月光石灯 */
  function treeTower(ctx) {
    var s = C.groundShadow(8, 40, -4, -36);
    s += F.trunk(ctx, 24, -6, 9, 6, 70, { roots: 6 }).svg;
    var R = F.ring(ctx, 24, -78, 20, 4, { railH: 6 });
    s += R.back + R.deck + HA.column(ctx, 24, -80, 6, 5, -112);
    s += line('M12 -80V-104M36 -80V-104', 2.8, 1) + line('M12 -80V-104M36 -80V-104', 1.3, 1, P.silver);
    s += R.front;
    s += F.roofLeaf(ctx, { x0: 10, x1: 38, yE: -104, D: 18, R: 6, mat: 'leaf', curl: 5, ov: 2 }).svg;
    s += line('M14 -98v4M34 -98v4', 0.6, 0.7) + C.circle(14, -92.5, 1.6, P.moon, 0.7) + C.circle(34, -92.5, 1.6, P.moon, 0.7);
    s += HA.ladder(32, -72, -2, 4);
    return s;
  }

  // ---------- 汇总 ----------
  function all(wrap) {
    var out = [], m;
    for (m = 0; m < 16; m++) {
      var wid = 'west-elf-wall-' + bin(m), wctx = new C.Ctx(wid);
      var wb = '<g transform="translate(0 -48)">' + wallTile(wctx, m) + '</g>';
      out.push(wrap(wid, [1, 1], wb, m ? -48 - WALL_H - 7 : -48, {
        id: wid, style: 'west', race: 'elf', category: 'wall', kind: 'wall_thorn', facility: 'city_wall', variant: m, mask: m,
        name: '荆棘藤墙 ' + bin(m), tags: ['dual_grid', 'mask_' + bin(m), 'living_thorn', 'silverwood_stakes'], roof: 'none',
        note: m === 0 ? '空瓦片（透明占位）' : '活体荆棘藤编墙，墙厚 24 px、高 ' + WALL_H + ' px；墙顶叶丛，银白木尖桩（周期 24）代替垛口'
      }));
    }
    var OV = [
      ['gate-h', gateH, 'gate', 'wall_gate_h', '藤拱城门（东西向墙段）', ['overlay', 'logical_cell', 'vine_arch', 'gatehouse'], 'gable_tile', '放在东西向直墙的逻辑格上；门洞朝南北，尖弧藤拱 + 半垂藤帘，两侧银白木门柱挂月光石灯，叶舟顶门楼'],
      ['gate-v', gateV, 'gate', 'wall_gate_v', '藤拱城门（南北向墙段）', ['overlay', 'logical_cell', 'gatehouse'], 'gable_tile', '放在南北向直墙的逻辑格上；门洞朝东西，正视只露两侧敞开的藤编门扇，叶尖山墙门楼'],
      ['tower', treeTower, 'watchtower', 'wall_tower_tree', '树冠哨台', ['overlay', 'logical_cell', 'treetop', 'ring_platform'], 'gable_tile', '放在墙的拐角或端点；细树干撑环台，台上叶舟小顶']
    ];
    OV.forEach(function (o, k) {
      var id = 'west-elf-wall-' + o[0], ctx = new C.Ctx(id);
      var body = o[1](ctx);
      out.push(wrap(id, [1, 1], body, ctx.minY, {
        id: id, style: 'west', race: 'elf', category: 'wall', kind: o[3], facility: o[2], variant: k + 1,
        name: o[4], tags: o[5], roof: o[6], note: o[7] + '。叠加件对齐逻辑格（不是渲染格），锚点 = 逻辑格前沿中点；叶形顶无对应 RoofId，取最近的 gable_tile'
      }));
    });
    return out;
  }

  var API = { WALL_H: WALL_H, bin: bin, wallCells: wallCells, wallTile: wallTile, gateH: gateH, gateV: gateV, treeTower: treeTower, all: all };
  root.TownArtWE_tiles = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
