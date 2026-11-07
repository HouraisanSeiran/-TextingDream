/*
 * 织梦 · 阿拉伯风格双网格城墙：厚夯土墙 × 16 + 城门 gate-h / gate-v + 圆形夯土塔（美术样板，尚未接入游戏）
 * 墙沿逻辑格中心线走，墙厚 24 px（每块瓦片里占 12 px 宽的带），高 WALL_H；墙顶两侧阶梯雉堞。按 12 px 小格计算。
 * 夯土层线每 8 px、脚手架孔每 24 px，按世界坐标对齐，跨瓦片连续。
 * 浏览器挂 window.TownArtAB_wall；Node 用 module.exports。依赖 core.js、parts.js、parts2.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtAB_core;
  var Q = isNode ? require('./parts.js') : root.TownArtAB_parts;
  var Q2 = isNode ? require('./parts2.js') : root.TownArtAB_parts2;
  var P = C.PAL, f = C.f, S = 48, G = 12, WALL_H = 38, WALK = '#dcc08e', MER = P.mud;

  /** 单个阶梯雉堞：底中点 (cx, yb)，宽 w，高 h */
  function merlon(cx, yb, w, h, col, sw) {
    var q = w / 4, x = cx - w / 2;
    return C.path('M' + f(x) + ' ' + f(yb) + 'v' + f(-h * 0.55) + 'h' + f(q) + 'v' + f(-h * 0.45) + 'h' + f(w - 2 * q) + 'v' + f(h * 0.45) + 'h' + f(q) + 'v' + f(h * 0.55) + 'Z', col || MER, sw == null ? 0.9 : sw);
  }
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
  /** 夯土墙正面：x0..x1、底 yb、高 h；层线与脚手架孔按瓦片（世界）坐标对齐 */
  function mudFace(x0, x1, yb, h, endL, endR) {
    var s = C.rect(x0, yb - h, x1 - x0, h, P.mud, 0), d = '', holes = '';
    for (var y = yb - 8; y > yb - h + 3; y -= 8) d += 'M' + f(x0) + ' ' + f(y) + 'H' + f(x1);
    s += C.line(d, 0.7, 0.4);
    for (var x = 6; x < S; x += 24) if (x > x0 + 1 && x < x1 - 2) holes += C.rect(x, yb - 17, 2, 2, P.hole, 0) + C.rect(x + 12, yb - 33, 2, 2, P.hole, 0);
    s += holes;
    s += C.rect(x0, yb - 4, x1 - x0, 4, P.mud2, 0) + C.line('M' + f(x0) + ' ' + f(yb - 4) + 'H' + f(x1), 0.8, 0.6);
    s += C.rect(x0, yb - h, x1 - x0, 2.5, P.mud3, 0, 0.5);
    var ol = 'M' + f(x0) + ' ' + f(yb) + 'H' + f(x1);
    if (endL) ol += 'M' + f(x0) + ' ' + f(yb) + 'V' + f(yb - h);
    if (endR) ol += 'M' + f(x1) + ' ' + f(yb) + 'V' + f(yb - h);
    return s + C.line(ol, 1.6);
  }
  function wallTile(ctx, mask) {
    if (!mask) return '';
    var g = wallCells(mask), H = WALL_H, cx, cy;
    function at(x, y) { return x >= 0 && x < 4 && y >= 0 && y < 4 ? g[y][x] : 2; }
    var shade = '', faces = '', tops = '', edge = '', back = '', front = '', walk = '';
    for (cy = 0; cy < 4; cy++) for (cx = 0; cx < 4; cx++) {
      if (!g[cy][cx]) continue;
      var x = cx * G, y = cy * G, ty = y - H;
      if (at(cx + 1, cy) === 0) shade += C.rect(x + G, y + 2, 5, G, P.ink, 0, 0.18);
      if (at(cx, cy + 1) === 0) shade += C.rect(x + 3, y + G, G, 4, P.ink, 0, 0.18);
      tops += C.rect(x, ty, G, G, WALK, 0);
      walk += 'M' + f(x) + ' ' + f(ty + 6) + 'h' + G;
      if (at(cx, cy - 1) === 0) { edge += 'M' + f(x) + ' ' + f(ty) + 'h' + G; back += C.rect(x, ty, G, 2.6, P.mud2, 0) + merlon(x + 6, ty + 1, 7, 6, P.mud2, 0.8); }
      if (at(cx - 1, cy) === 0) { edge += 'M' + f(x) + ' ' + f(ty) + 'v' + G; back += C.rect(x, ty, 3, G, P.lime2, 0.8); }
      if (at(cx + 1, cy) === 0) { edge += 'M' + f(x + G) + ' ' + f(ty) + 'v' + G; back += C.rect(x + G - 3, ty, 3, G, P.mud3, 0.8); }
      if (at(cx, cy + 1) === 0) {
        var e = ty + G;
        edge += 'M' + f(x) + ' ' + f(e) + 'h' + G;
        front += C.rect(x, e - 3, G, 3, P.mud, 0) + merlon(x + 6, e, 8, 9, MER, 1);
      }
    }
    for (cy = 0; cy < 3; cy++) {
      cx = 0;
      while (cx < 4) {
        if (g[cy][cx] && g[cy + 1][cx] === 0) {
          var a = cx;
          while (cx < 4 && g[cy][cx] && g[cy + 1][cx] === 0) cx++;
          faces += mudFace(a * G, cx * G, (cy + 1) * G, H, a > 0, cx < 4);
        } else cx++;
      }
    }
    // 第 4 行（瓦片底边）有墙时正面在瓦片外 —— 由下方瓦片的上半画；此处无需处理
    ctx.top(-H - 10);
    return shade + faces + tops + C.line(walk, 0.6, 0.3) + back + front + C.line(edge, 1.4);
  }
  // ---------- 叠加件（对齐逻辑格；局部 y = 0 为逻辑格前沿，E-W 墙带在 y -36..-12，N-S 墙带在 x 12..36） ----------
  function pennant(ctx, x, y, col) {
    ctx.top(y - 15);
    return C.line('M' + f(x) + ' ' + f(y) + 'v-15', 1.2) + C.path('M' + f(x) + ' ' + f(y - 15) + 'l9 2.6l-9 2.8Z', col || P.ochre, 0.7);
  }
  /** 门楼顶：平台 + 前后两排阶梯雉堞 */
  function gateTop(ctx, x0, x1, yt, dp) {
    var s = C.rect(x0, yt - dp, x1 - x0, dp, WALK, 1.3), n = Math.round((x1 - x0) / 7), w = (x1 - x0) / n, i;
    for (i = 0; i < n; i++) s += merlon(x0 + w * (i + 0.5), yt - dp + 1, w * 0.72, 6, P.mud2, 0.8);
    s += C.rect(x0, yt - dp, 3, dp, P.lime2, 0.8) + C.rect(x1 - 3, yt - dp, 3, dp, P.mud3, 0.8);
    for (i = 0; i < n; i++) s += merlon(x0 + w * (i + 0.5), yt + 0.5, w * 0.78, 9, MER, 1);
    ctx.top(yt - dp - 6);
    return s;
  }
  /** 城门洞：马蹄拱（或尖拱）+ 钴蓝瓷砖拱框 + 带门钉的双扇木门 */
  function gateway(ctx, x, yb, w, h, kind) {
    var fr = C.rect(x - 6, yb - h - 6, w + 12, h + 6, P.cob, 1.1) + Q2.tileBand(ctx, x - 6, x + w + 6, yb - h - 3, 4, 'star', P.cob2, P.turq2);
    return fr + Q.door(ctx, x, yb, w, h, { kind: kind, col: P.wood, studs: true, frame: P.turq });
  }
  function gateH(ctx) {
    var x0 = 2, x1 = 46, yb = -8, gh = WALL_H + 14, s = '';
    s += C.groundShadow(x0, x1, yb, -40);
    s += Q.facade(ctx, x0, x1, yb, gh, 'mud', { fill: P.mud });
    s += C.rect(x0, yb - gh, x1 - x0, gh, 'none', 1.7);
    s += gateway(ctx, 16, yb, 16, 28, 'horseshoe');
    s += Q2.win(7, yb - 38, 3, 8, 'slit') + Q2.win(38, yb - 38, 3, 8, 'slit');
    s += gateTop(ctx, x0 - 1, x1 + 1, yb - gh, 30);
    return s + pennant(ctx, 24, yb - gh - 24, P.ochre);
  }
  function gateV(ctx) {
    var x0 = 6, x1 = 42, yb = -3, gh = WALL_H + 12, s = '';
    s += C.groundShadow(x0, x1, yb, -46);
    s += Q.facade(ctx, x0, x1, yb, gh, 'mud', { fill: P.mud });
    s += C.rect(x0, yb - gh, x1 - x0, gh, 'none', 1.7);
    // 门道东西向，正面是门楼端墙：尖拱盲龛 + 瓷砖带 + 箭窗
    s += C.path(Q.pointedD(14, yb - 6, 20, 22, 12), P.mud2, 1.1) + C.path(Q.pointedD(17, yb - 6, 14, 18, 9), P.cob, 0.9);
    s += Q2.tileBand(ctx, x0, x1, yb - gh + 9, 3.4, 'zig', P.turq, P.lime);
    s += Q2.win(22.5, yb - 26, 3, 8, 'slit');
    s += gateTop(ctx, x0 - 1, x1 + 1, yb - gh, 42);
    return s + pennant(ctx, 24, yb - gh - 30, P.ochre);
  }
  function towerRound(ctx) {
    var cx = 24, cy = -24, r = 19, h = WALL_H + 20, yt = cy - h, s = '', i;
    s += C.shadow('M' + f(cx + 4) + ' ' + f(cy - r + 4) + 'A' + r + ' ' + r + ' 0 0 1 ' + f(cx + 4) + ' ' + f(cy + r + 3) + 'L' + f(cx - 6) + ' ' + f(cy + r + 3) + 'Z');
    var body = 'M' + f(cx - r) + ' ' + f(yt) + 'V' + f(cy) + 'A' + r + ' ' + r + ' 0 0 0 ' + f(cx + r) + ' ' + f(cy) + 'V' + f(yt) + 'Z';
    var tex = '', d = '';
    for (var y = cy - 8; y > yt + 2; y -= 8) d += 'M' + f(cx - r) + ' ' + f(y) + 'A' + r + ' ' + r + ' 0 0 0 ' + f(cx + r) + ' ' + f(y);
    tex += C.line(d, 0.7, 0.4) + C.rect(cx + r * 0.35, yt, r, h + r + 2, P.mud3, 0, 0.45) + C.rect(cx - r, cy - 4 + r - 6, 2 * r, 10, P.mud2, 0);
    s += C.path(body, P.mud, 0) + C.clipped(ctx, body, tex) + C.path(body, 'none', 1.7);
    s += Q2.win(cx - 1.5, cy - 6, 3, 9, 'slit') + Q2.win(cx - 13, cy - 30, 3, 8, 'slit') + Q2.win(cx + 10, cy - 30, 3, 8, 'slit');
    // 塔顶：圆形平台 + 一圈阶梯雉堞（后半先画、前半后画）
    var back = '', front = '';
    for (i = 0; i < 12; i++) {
      var t = Math.PI * 2 * (i + 0.5) / 12, mx = cx + Math.cos(t) * (r - 2.5), my = yt + Math.sin(t) * (r - 2.5);
      if (Math.sin(t) < 0) back += merlon(mx, my + 1, 6, 6, P.mud2, 0.8); else front += merlon(mx, my + 2, 7, 8, MER, 1);
    }
    s += C.ell(cx, yt, r, r, WALK, 1.4) + C.ell(cx, yt, r - 5, r - 5, 'none', 0.7) + back + C.ell(cx, yt - 1, 3, 3, P.mud3, 0.7) + front;
    ctx.top(yt - r - 6);
    return s + pennant(ctx, cx, yt - 4, P.ochre);
  }

  function all(wrap) {
    var out = [], m;
    for (m = 0; m < 16; m++) {
      var id = 'arab-common-wall-' + C.bin(m), ctx = new C.Ctx(id);
      out.push(wrap(id, [1, 1], '<g transform="translate(0 -48)">' + wallTile(ctx, m) + '</g>', m ? ctx.minY - 48 : -48, {
        id: id, style: 'arab', race: 'common', category: 'wall', kind: 'wall_rammed_earth', facility: 'city_wall', variant: m, mask: m,
        name: '夯土城墙 ' + C.bin(m), tags: ['dual_grid', 'mask_' + C.bin(m), 'rammed_earth', 'stepped_merlons'], roof: 'none',
        note: m === 0 ? '空瓦片（透明占位）' : '双网格渲染瓦片：墙沿逻辑格中心线，墙厚 24 px，高 ' + WALL_H + ' px'
      }));
    }
    var X = [['gate-h', gateH, 'gate', '城门（东西向墙段）', '马蹄拱门洞、钴蓝瓷砖拱框、门钉木门'], ['gate-v', gateV, 'gate', '城门（南北向墙段）', '门道东西向，正面为端墙尖拱盲龛'],
      ['tower', towerRound, 'watchtower', '圆形夯土塔', '放在墙拐角 / 端点 / 辐条墙节点上']];
    X.forEach(function (x) {
      var id = 'arab-common-wall-' + x[0], c2 = new C.Ctx(id);
      out.push(wrap(id, [1, 1], x[1](c2), c2.minY, { id: id, style: 'arab', race: 'common', category: 'wall', kind: 'wall_' + x[0].replace('-', '_'), facility: x[2], variant: 1,
        name: x[3], tags: ['overlay', 'rammed_earth'], roof: 'none', note: '叠加件，锚点 = 所在逻辑格前沿中点；' + x[4] }));
    });
    return out;
  }
  var API = { WALL_H: WALL_H, WALK: WALK, merlon: merlon, wallTile: wallTile, mudFace: mudFace, towerRound: towerRound, all: all };
  root.TownArtAB_wall = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
