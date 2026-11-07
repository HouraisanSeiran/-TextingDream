/*
 * 织梦 · 阿拉伯风格双网格道路三档：dirt（沙土路）/ stone（石板路）/ tile（几何纹砖铺大道）× 16（美术样板，尚未接入游戏）
 * 四角编码 mask = NW*8 + NE*4 + SW*2 + SE*1。瓦片内部坐标 0..48（y 向下），四角 = 四个逻辑格中心。
 * 路面 = 是路的角所在的象限；分界线过边中点（24）并垂直于边，中心处圆角；纹理周期整除 48，跨瓦片对齐。
 * 浏览器挂 window.TownArtAB_road；Node 用 module.exports。依赖 core.js、parts2.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtAB_core;
  var Q2 = isNode ? require('./parts2.js') : root.TownArtAB_parts2;
  var P = C.PAL, f = C.f, S = 48, M = 24, RAD = 10, BITS = [8, 4, 2, 1];
  function on(mask, qx, qy) { return !!(mask & BITS[qy * 2 + qx]); }

  /** a→b 手绘线段：两端切线沿线段方向，中点偏 w */
  function curve(a, b, w) {
    var dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1, nx = -dy / L, ny = dx / L;
    var m = [(a[0] + b[0]) / 2 + nx * w, (a[1] + b[1]) / 2 + ny * w];
    return 'C' + f(a[0] + dx * 0.25) + ' ' + f(a[1] + dy * 0.25) + ' ' + f(m[0] - dx * 0.18) + ' ' + f(m[1] - dy * 0.18) + ' ' + f(m[0]) + ' ' + f(m[1]) +
      'S' + f(b[0] - dx * 0.25) + ' ' + f(b[1] - dy * 0.25) + ' ' + f(b[0]) + ' ' + f(b[1]);
  }
  /** 象限 (qx,qy) 的内侧边界：边中点 → 中心圆角 → 另一条边中点 */
  function inner(qx, qy, r, w1, w2) {
    var ox = qx * S, oy = qy * S, sx = qx ? 1 : -1, sy = qy ? 1 : -1;
    var A = [M, oy], E1 = [M, M + sy * r], E2 = [M + sx * r, M], B = [ox, M];
    return 'M' + f(A[0]) + ' ' + f(A[1]) + curve(A, E1, w1) + 'Q' + M + ' ' + M + ' ' + f(E2[0]) + ' ' + f(E2[1]) + curve(E2, B, w2);
  }
  function quadFill(qx, qy, r, w1, w2) { return inner(qx, qy, r, w1, w2) + 'L' + qx * S + ' ' + qy * S + 'Z'; }
  /** 路面形状 { fill, rule, outline }；wob = 分界线起伏幅度 */
  function shape(ctx, mask, wob) {
    var k = 0, i, qs = [], w = function () { return ctx.rnd(-wob, wob); };
    for (i = 0; i < 4; i++) if (on(mask, i % 2, i >> 1)) { k++; qs.push([i % 2, i >> 1]); }
    if (!k) return null;
    if (k === 4) return { fill: C.rectD(0, 0, S, S), rule: 'nonzero', outline: '' };
    if (k === 3) {
      for (i = 0; i < 4; i++) if (!on(mask, i % 2, i >> 1)) break;
      var a = w(), b = w();
      return { fill: C.rectD(0, 0, S, S) + quadFill(i % 2, i >> 1, RAD, a, b), rule: 'evenodd', outline: inner(i % 2, i >> 1, RAD, a, b) };
    }
    if (k === 2 && mask !== 9 && mask !== 6) {
      var c = w(), seg;
      if (mask === 12) seg = ['M0 0L48 0L48 24', [48, 24], [0, 24]];
      else if (mask === 3) seg = ['M0 48L48 48L48 24', [48, 24], [0, 24]];
      else if (mask === 10) seg = ['M0 0L0 48L24 48', [24, 48], [24, 0]];
      else seg = ['M48 0L48 48L24 48', [24, 48], [24, 0]];
      var cv = curve(seg[1], seg[2], c);
      return { fill: seg[0] + cv + 'Z', rule: 'nonzero', outline: 'M' + seg[1].join(' ') + cv };
    }
    var fl = '', ol = '';
    qs.forEach(function (p) { var a1 = w(), b1 = w(); fl += quadFill(p[0], p[1], RAD, a1, b1); ol += inner(p[0], p[1], RAD, a1, b1); });
    return { fill: fl, rule: 'nonzero', outline: ol };
  }
  function band(d, w, col, op) { return d ? '<path d="' + d + '" fill="none" stroke="' + col + '" stroke-width="' + f(w) + '"' + (op != null ? ' stroke-opacity="' + f(op) + '"' : '') + ' stroke-linejoin="round"/>' : ''; }
  function dash(d, w, col, op, da) { return d ? '<path d="' + d + '" fill="none" stroke="' + col + '" stroke-width="' + f(w) + '" stroke-opacity="' + f(op) + '" stroke-dasharray="' + da + '"/>' : ''; }

  var ROAD = {
    dirt: { name: '沙土路', base: '#e0c895', wob: 2 },
    stone: { name: '石板路', base: '#d6c6a2', wob: 1.4 },
    tile: { name: '几何纹砖铺大道', base: '#c9a26c', wob: 0 }
  };
  /** 石板：行高 rowH、板长 slabW、错缝 off（都整除 48） */
  function slabs(rowH, slabW, off, tones) {
    var o = '', d = '';
    for (var j = 0; j * rowH < S; j++) {
      var y = j * rowH, ox = (j % 2) * off;
      for (var k = -1; ox + k * slabW < S; k++) {
        o += C.rect(ox + k * slabW, y, slabW, rowH, tones[(((k % tones.length) + tones.length) + j) % tones.length], 0);
        d += 'M' + f(ox + k * slabW) + ' ' + f(y) + 'v' + rowH;
      }
      d += 'M0 ' + f(y) + 'H48';
    }
    return o + C.line(d, 0.8, 0.5);
  }
  /** 砖铺大道：12 px 砖方格，每 24 px 一个八角星瓷砖（钴蓝 + 绿松石），砖缝按世界网格对齐 */
  function tilePave() {
    var o = '', d = '', x, y;
    for (y = 0; y < S; y += 12) for (x = 0; x < S; x += 12) o += C.rect(x, y, 12, 12, ((x + y) / 12) % 2 ? '#c9a26c' : '#d4b07a', 0);
    for (x = 0; x <= S; x += 12) d += 'M' + x + ' 0V48M0 ' + x + 'H48';
    o += C.line(d, 0.7, 0.45);
    for (y = 12; y < S; y += 24) for (x = 12; x < S; x += 24) {
      var a = 5.4, b = 2.3;
      o += C.path('M' + (x - a) + ' ' + (y - b) + 'L' + (x - b) + ' ' + (y - a) + 'L' + (x + b) + ' ' + (y - a) + 'L' + (x + a) + ' ' + (y - b) + 'L' + (x + a) + ' ' + (y + b) +
        'L' + (x + b) + ' ' + (y + a) + 'L' + (x - b) + ' ' + (y + a) + 'L' + (x - a) + ' ' + (y + b) + 'Z', P.cob2, 0.7);
      o += C.path('M' + x + ' ' + (y - 3.6) + 'L' + (x + 3.6) + ' ' + y + 'L' + x + ' ' + (y + 3.6) + 'L' + (x - 3.6) + ' ' + y + 'Z', P.turq2, 0.5);
    }
    return o;
  }
  function tex(ctx, mat, mask, ol) {
    var o = '', i;
    if (mat === 'dirt') {
      for (i = 0; i < 10; i++) o += C.ell(ctx.rnd(4, 44), ctx.rnd(4, 44), ctx.rnd(0.8, 1.7), ctx.rnd(0.6, 1.1), ctx.pick([P.stone, P.stone2, '#c7ab78']), 0.5);
      var dd = '';
      for (i = 0; i < 6; i++) { var x = ctx.rnd(4, 40), y = ctx.rnd(4, 44); dd += 'M' + f(x) + ' ' + f(y) + 'q2 -1 4 0'; }
      o += C.line(dd, 0.6, 0.35) + band(ol, 7, '#d2b47c', 1);
    } else if (mat === 'stone') {
      o += slabs(12, 16, 8, ['#d6c6a2', '#cbb994', '#ddd0b0']) + band(ol, 7, P.stone2, 1) + dash(ol, 7, P.ink, 0.4, '1 5');
    } else {
      o += tilePave() + band(ol, 12, P.ink, 0.85) + band(ol, 10, P.cob, 1) + dash(ol, 10, P.turq2, 1, '3 3');
    }
    return o;
  }
  function roadTile(ctx, mat, mask) {
    var sh = shape(ctx, mask, ROAD[mat].wob);
    if (!sh) return '';
    var s = '<path d="' + sh.fill + '" fill="' + ROAD[mat].base + '" fill-rule="' + sh.rule + '"/>';
    s += C.clipped(ctx, sh.fill, tex(ctx, mat, mask, sh.outline), sh.rule);
    return s + (sh.outline ? C.line(sh.outline, 1.4, 0.9) : '');
  }
  function all(wrap) {
    var out = [];
    ['dirt', 'stone', 'tile'].forEach(function (mat) {
      for (var m = 0; m < 16; m++) {
        var id = 'arab-common-road-' + mat + '-' + C.bin(m), ctx = new C.Ctx(id);
        out.push(wrap(id, [1, 1], '<g transform="translate(0 -48)">' + roadTile(ctx, mat, m) + '</g>', -48, {
          id: id, style: 'arab', race: 'common', category: 'road', kind: 'road_' + mat, facility: null, variant: m, mask: m,
          name: ROAD[mat].name + ' ' + C.bin(m), tags: ['dual_grid', 'mask_' + C.bin(m)], roof: 'none',
          note: m === 0 ? '空瓦片（透明占位）' : '双网格渲染瓦片：四角落在逻辑格中心'
        }));
      }
    });
    return out;
  }
  var API = { all: all, shape: shape, on: on, ROAD: ROAD };
  root.TownArtAB_road = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
