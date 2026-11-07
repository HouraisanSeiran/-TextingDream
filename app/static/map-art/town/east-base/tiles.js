/*
 * 织梦 · 东方城镇双网格瓦片：道路三档（黄土路 / 青石板路 / 官道）× 16，城墙 16 + 城门楼 gate-h / gate-v + 角楼
 *
 * 双网格（规范第 4 节）：渲染瓦片 48×48，四个角落在四个逻辑格中心，mask = NW*8 + NE*4 + SW*2 + SE*1。
 * 每个逻辑格内部状态一致，所以路 / 墙的分界线只会落在瓦片内 x = 24 或 y = 24 这两条线上，且必定穿过边中点。
 * 纹理（石板缝、墙砖缝、垛口）都按周期 48 摆放，并在瓦片边上做环绕，任意相邻瓦片的纹理都对得上。
 * 瓦片本地坐标：左上角 (0,0)，y 向下到 48；生成 symbol 时整体平移到 east-core 的约定（占地 g∈[-48,0]）。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./east-core.js'), require('./houses-a.js'));
  else root.TownArtEast_tiles = factory(root.TownArtEast_core, root.TownArtEast_housesA);
})(this, function (E, HA) {
  'use strict';
  var C = E.C, T = E.TILE, f = E.f, K = E.K, mix = E.mix;

  function bits(m) { return ('000' + m.toString(2)).slice(-4); }
  var ORDER = ['NW', 'NE', 'SE', 'SW'];                       // 顺时针
  var BIT = { NW: 8, NE: 4, SW: 2, SE: 1 };
  var CORNER = { NW: [0, 0], NE: [48, 0], SE: [48, 48], SW: [0, 48] };
  var MID = [[24, 0], [48, 24], [24, 48], [0, 24]];            // MID[i] 位于 ORDER[i] 与 ORDER[i+1] 之间的那条边的中点

  // 四分之一圆弧（圆心 = 孤立的那个角），两端分别垂直于所在的瓦片边
  function arcSeg(m1, m2, c) {
    var k = 0.5523;
    return 'C' + E.pt([m1[0] + (m2[0] - c[0]) * k, m1[1] + (m2[1] - c[1]) * k]) + ' ' +
      E.pt([m2[0] + (m1[0] - c[0]) * k, m2[1] + (m1[1] - c[1]) * k]) + ' ' + E.pt(m2);
  }
  // 手绘起伏的直分界线：起伏量乘 sin²，两端位移与斜率都为 0，所以在边中点处仍垂直于瓦片边
  function wobSeg(m1, m2, amp, ph) {
    var d = '', n = 14, dx = m2[0] - m1[0], dy = m2[1] - m1[1], L = Math.sqrt(dx * dx + dy * dy), nx = -dy / L, ny = dx / L;
    for (var i = 1; i <= n; i++) {
      var t = i / n, s = Math.sin(Math.PI * t), o = amp * s * s * Math.cos(3 * Math.PI * t + ph);
      d += 'L' + E.pt([m1[0] + dx * t + nx * o, m1[1] + dy * t + ny * o]);
    }
    return d;
  }
  /**
   * 路面区域：返回 { fill: 闭合路径, edges: [分界线路径...] }。
   * 单角 → 圆角块（圆心在该角）；相邻两角 → 半幅；三角 → 整块减去一个圆角缺口；对角 1001 / 0110 → 两块互不相连的圆角。
   */
  function region(mask, amp, ph) {
    var on = ORDER.map(function (k) { return !!(mask & BIT[k]); }), n = on.filter(Boolean).length;
    if (n === 0) return null;
    if (n === 4) return { fill: 'M0 0H48V48H0Z', edges: [] };
    if (n === 2 && on[0] === on[2]) {
      var fill = '', edges = [];
      ORDER.forEach(function (k, i) { if (on[i]) { var r = region(BIT[k], amp, ph); fill += r.fill; edges = edges.concat(r.edges); } });
      return { fill: fill, edges: edges };
    }
    var ex = -1, en = -1, i;
    for (i = 0; i < 4; i++) { if (on[i] && !on[(i + 1) % 4]) ex = i; if (!on[i] && on[(i + 1) % 4]) en = i; }
    var m1 = MID[ex], m2 = MID[en], gap = (en - ex + 4) % 4, bd;
    if (gap === 1) bd = arcSeg(m1, m2, CORNER[ORDER[en]]);          // 三角是路：凹缺口
    else if (gap === 3) bd = arcSeg(m1, m2, CORNER[ORDER[ex]]);     // 单角是路：凸圆角
    else bd = wobSeg(m1, m2, amp, ph);                              // 半幅：直分界
    var d = 'M' + E.pt(m2);
    for (var j = (en + 1) % 4; ; j = (j + 1) % 4) { d += 'L' + E.pt(CORNER[ORDER[j]]); if (j === ex) break; }
    d += 'L' + E.pt(m1) + bd + 'Z';
    return { fill: d, edges: ['M' + E.pt(m1) + bd] };
  }

  // 周期 48 的环绕：元素 bbox 越过瓦片边时，在对边再画一份
  function wrap(x, y, w, h, draw) {
    var s = '';
    [-48, 0, 48].forEach(function (ox) {
      [-48, 0, 48].forEach(function (oy) {
        if (x + ox < 48 && x + ox + w > 0 && y + oy < 48 && y + oy + h > 0) s += draw(x + ox, y + oy);
      });
    });
    return s;
  }
  // 错缝条石：每行若干块，长度之和正好 48，行起点随机；种子固定（与瓦片无关），所以全图是同一张连续的铺装
  function slabs(seed, rowH, avgL, cols, grout, crack) {
    var r = E.rng(seed), s = E.rect(-1, -1, 50, 50, grout), rows = Math.round(48 / rowH), gp = 0.7;
    for (var j = 0; j < rows; j++) {
      var n = Math.max(2, Math.round(48 / avgL)), L = [], sum = 0, k;
      for (k = 0; k < n; k++) { L.push(0.65 + r() * 0.7); sum += L[k]; }
      var x = r() * 48, y = j * rowH;
      for (k = 0; k < n; k++) {
        var w = L[k] / sum * 48, c = cols[Math.floor(r() * cols.length)], ck = r() < (crack || 0);
        s += wrap(x, y, w, rowH, function (xx, yy) {
          var o = E.rect(xx + gp, yy + gp, w - gp * 2, rowH - gp * 2, c) + E.line('M' + f(xx + gp + 0.6) + ' ' + f(yy + gp + 0.5) + 'H' + f(xx + w - gp - 0.6), C.creamL, 0.6, ' stroke-opacity="0.45"');
          if (ck) o += E.line('M' + f(xx + w * 0.3) + ' ' + f(yy + gp) + 'l' + f(w * 0.12) + ' ' + f(rowH * 0.45) + 'l' + f(w * 0.15) + ' ' + f(rowH * 0.2), grout, 0.5, ' stroke-opacity="0.7"');
          return o;
        });
        x = (x + w) % 48;
      }
    }
    return s;
  }
  // 黄土路面：底色 + 周期性的土粒、小石子、浅色踩实斑
  function dirtTex(seed) {
    var r = E.rng(seed), base = mix(C.ochre, C.cream, 0.42), s = E.rect(-1, -1, 50, 50, base), i;
    for (i = 0; i < 7; i++) {
      var px = r() * 48, py = r() * 48, rw = 5 + r() * 7, rh2 = 2 + r() * 2.5;
      s += wrap(px - rw, py - rh2, rw * 2, rh2 * 2, function (xx, yy) {
        return '<ellipse cx="' + f(xx + rw) + '" cy="' + f(yy + rh2) + '" rx="' + f(rw) + '" ry="' + f(rh2) + '" fill="' + C.ochreL + '" fill-opacity="0.55"/>';
      });
    }
    for (i = 0; i < 34; i++) {
      var dx = r() * 48, dy = r() * 48, rr = 0.4 + r() * 0.6, cc = r() < 0.6 ? C.umberL : C.umber;
      s += wrap(dx - rr, dy - rr, rr * 2, rr * 2, function (xx, yy) { return E.circle(xx + rr, yy + rr, rr, cc).replace('/>', ' fill-opacity="0.5"/>'); });
    }
    for (i = 0; i < 6; i++) {
      var sx = r() * 48, sy2 = r() * 48, sr = 0.9 + r() * 0.8;
      s += wrap(sx - sr, sy2 - sr, sr * 2, sr * 2, function (xx, yy) {
        return '<ellipse cx="' + f(xx + sr) + '" cy="' + f(yy + sr) + '" rx="' + f(sr * 1.3) + '" ry="' + f(sr) + '" fill="' + C.stone + '" stroke="' + C.gold + '" stroke-width="0.35"/>';
      });
    }
    return s;
  }

  var ROADS = {
    dirt: { name: '黄土路', amp: 1.8, tex: function () { return dirtTex(9101); } },
    stone: { name: '青石板路', amp: 0.9, tex: function () {
      return slabs(9202, 8, 12, [mix(C.grayL, C.tealL, 0.22), mix(C.grayL, C.cream, 0.28), mix(C.grayL, C.tealL, 0.08), mix(C.gray, C.tealL, 0.3)], C.gray, 0.12);
    } },
    highway: { name: '官道', amp: 0.4, tex: function () {
      return slabs(9303, 16, 22, [mix(C.stoneL, C.grayL, 0.2), C.stone, mix(C.stone, C.ochreL, 0.25), mix(C.stoneL, C.grayL, 0.4)], mix(C.gray, C.navy, 0.3), 0.18);
    } }
  };

  // 分界线的长度（用来让路缘石缝的周期整除每段边界，跨瓦片接缝处石缝正好对上）
  function edgeLen(d) {
    if (d.indexOf('C') >= 0) return 24 * Math.PI / 2;
    var nums = d.match(/-?\d*\.?\d+/g).map(parseFloat), L = 0;
    for (var i = 2; i + 1 < nums.length; i += 2) L += Math.hypot(nums[i] - nums[i - 2], nums[i + 1] - nums[i - 1]);
    return L;
  }
  // 路缘：两道描边裁进路面内侧（外层深色、内层石色，内侧留一线深缝），再横切石缝；最后一道金线压在分界上
  function curb(ctx, rg, w, dark, stoneC, grout, jointP) {
    var inside = '', s = '';
    rg.edges.forEach(function (d) {
      var L = edgeLen(d), n = Math.max(1, Math.round(L / jointP)), p = L / n;
      inside += E.line(d, dark, w + 2) + E.line(d, stoneC, w) +
        E.path(d, 'none', grout, w, ' stroke-dasharray="0.7 ' + f(p - 0.7) + '" stroke-dashoffset="0.35"');
    });
    s += E.clip(ctx, rg.fill, inside);
    return s;
  }
  function tileSym(id, wc, dc, up, body) {
    var W = wc * 48, H = dc * 48 + up;
    return { id: id, viewBox: [0, 0, W, H], anchor: [W / 2, H], up: up,
      svg: '<symbol id="' + id + '" viewBox="0 0 ' + W + ' ' + H + '" overflow="visible"><g transform="translate(0 ' + up + ')">' + body + '</g></symbol>' };
  }

  function roadTile(kind, mask) {
    var R = ROADS[kind], id = 'east-common-road-' + kind + '-' + bits(mask), ctx = new E.Ctx(id, 1), rg = region(mask, R.amp, 0.7), body = '';
    if (rg) {
      body += E.clip(ctx, rg.fill, R.tex());
      if (kind === 'dirt') {
        var rim = '';
        rg.edges.forEach(function (d) { rim += E.line(d, C.umber, 5, ' stroke-opacity="0.18"') + E.line(d, C.umberL, 2, ' stroke-opacity="0.35"'); });
        body += E.clip(ctx, rg.fill, rim);
        rg.edges.forEach(function (d) { body += E.line(d, C.gold, 0.9, ' stroke-opacity="0.85"'); });
      } else if (kind === 'stone') {
        body += curb(ctx, rg, 5, C.gray, mix(C.grayL, C.cream, 0.15), C.gray, 8);
        rg.edges.forEach(function (d) { body += E.line(d, C.gold, 1); });
      } else {
        body += curb(ctx, rg, 9, mix(C.gray, C.navy, 0.3), mix(C.stone, C.grayL, 0.35), mix(C.gray, C.navy, 0.3), 12);
        rg.edges.forEach(function (d) { body += E.line(d, C.gold2, 2.2) + E.line(d, C.gold, 1); });
      }
    }
    var sym = tileSym(id, 1, 1, 0, body);
    return { id: id, svg: sym.svg, name: R.name + ' ' + bits(mask), meta: {
      id: id, style: 'east', race: 'common', category: 'road', kind: 'road_' + kind, facility: null, variant: mask,
      footprint: [1, 1], height_px: 0, anchor: sym.anchor, viewBox: sym.viewBox,
      tags: ['dual_grid', 'mask_' + bits(mask)].concat(mask === 0 ? ['empty'] : []), roof: 'none',
      note: R.name + '双网格瓦片，四角 NW NE SW SE = ' + bits(mask) + (mask === 0 ? '（空瓦片，透明占位）' : '') + '；渲染格与逻辑格错开半格',
      name_zh: R.name, mask: mask
    } };
  }

  /* ---------- 城墙 ----------
   * 墙体在平面里比逻辑格各边收进 IN px（墙厚 48 - 2*IN），相邻两格都是墙时补上中间的连接段。
   * 于是一张瓦片可以看成 3×3 小格：列 / 行宽 [24-IN, 2*IN, 24-IN]。四角格 = 四个逻辑格的四分之一；
   * 边中格 = 相邻两角都是墙时的连接段；中心格 = 四角都是墙时才填。瓦片边上的小格与邻瓦片的对应小格是同一块墙，所以一定接得上。
   */
  var IN = 6, WH = 26, PH = 6, MH = 3, WUP = WH + PH + MH + 3;
  var XS = [0, 24 - IN, 24 + IN, 48];
  var WC = {
    face: mix(C.grayL, C.cream, 0.32), faceD: mix(C.gray, C.grayL, 0.5), top: mix(C.stoneL, C.earthL, 0.35), base: C.stone,
    joint: mix(C.gray, C.navy, 0.2), par: mix(C.grayL, C.cream, 0.42)
  };
  function wallGrid(mask) {
    var nw = !!(mask & 8), ne = !!(mask & 4), sw = !!(mask & 2), se = !!(mask & 1);
    return [[nw, nw && ne, ne], [nw && sw, nw && ne && sw && se, ne && se], [sw, sw && se, se]];
  }

  var PW = 3;
  // 砖面：横缝贴着底边（地面线）往上排，竖缝按世界 x 周期 8 错缝，相邻瓦片 / 叠加件的砖缝对得上
  function brickFace(ctx, x0, x1, yT, yB, fill) {
    var d = E.poly([[x0, yT], [x1, yT], [x1, yB], [x0, yB]]), j = '', row = 0, y;
    for (y = yB - 3.4; y > yT + 0.5; y -= 3.4) j += 'M' + f(x0) + ' ' + f(y) + 'H' + f(x1);
    for (y = yB; y > yT; y -= 3.4, row++) {
      var off = row % 2 ? 4 : 0, ya = Math.max(yT, y - 3.4);
      for (var x = Math.floor((x0 - off) / 8) * 8 + off; x < x1; x += 8) if (x > x0 + 0.3) j += 'M' + f(x) + ' ' + f(y) + 'V' + f(ya);
    }
    return E.path(d, fill || WC.face) + E.clip(ctx, d, E.line(j, WC.joint, 0.5, ' stroke-opacity="0.55"'));
  }
  // 墙正面：yE = 墙脚地面线；ends = [左端是真端头, 右端是真端头]（瓦片边上不描竖线，免得拼接处出现缝）
  function wallFace(ctx, x0, x1, yE, zTop, ends) {
    var yT = yE - zTop * K, s = '';
    s += E.path(E.poly([[x0 + 3, yE], [x1 + 3, yE], [x1 + 3, yE + 3], [x0 + 2, yE + 3]]), C.shadow, null, 0, ' fill-opacity="0.2"');
    s += brickFace(ctx, x0, x1, yT, yE - 3 * K);
    s += E.rect(x0, yE - 3 * K, x1 - x0, 3 * K, WC.base) + E.rect(x0, yT, x1 - x0, 1.6, WC.faceD);
    var d = 'M' + f(x0) + ' ' + f(yT) + 'H' + f(x1) + 'M' + f(x0) + ' ' + f(yE) + 'H' + f(x1) + 'M' + f(x0) + ' ' + f(yE - 3 * K) + 'H' + f(x1);
    if (ends && ends[0]) d += 'M' + f(x0) + ' ' + f(yT) + 'V' + f(yE);
    if (ends && ends[1]) d += 'M' + f(x1) + ' ' + f(yT) + 'V' + f(yE);
    return s + E.line(d, C.gold, 0.8);
  }
  // 沿 x 的垛墙：yF = 垛墙前脸所在的地面线，向北厚 depth；solid = 女墙（连续矮墙、灰瓦压顶），否则 = 垛口（下段连续，上段一个个垛子，垛子上开望孔）
  function merlonsH(x0, x1, yF, depth, zb, zt, solid) {
    var s = '', zc = solid ? zt : zb + 2.4, tile = T.gray;
    s += E.rect(x0, yF - depth - zc * K, x1 - x0, depth, solid ? tile.fill : WC.par);
    s += E.rect(x0, yF - zc * K, x1 - x0, (zc - zb) * K, WC.face) + E.line('M' + f(x0) + ' ' + f(yF - zc * K) + 'H' + f(x1), solid ? tile.line : C.gold, 0.6);
    if (solid) return s + E.line('M' + f(x0) + ' ' + f(yF - depth - zc * K) + 'H' + f(x1), tile.lite, 0.6);
    for (var k = Math.floor(x0 / 8) - 1; k * 8 < x1; k++) {
      var xa = Math.max(x0, k * 8 + 1.5), xb = Math.min(x1, k * 8 + 6.5), w = xb - xa;
      if (w < 1) continue;
      s += E.rect(xa - 0.4, yF - depth - zt * K - 0.6, w + 0.8, depth + 0.6, tile.fill, tile.line, 0.4);
      s += E.rect(xa, yF - zt * K, w, (zt - zc) * K, WC.face, C.gold, 0.45);
      if (w > 4) s += E.rect(xa + w / 2 - 0.7, yF - (zc + (zt - zc) * 0.6) * K, 1.4, 1.4, C.navy);
    }
    return s;
  }
  // 沿 y 的垛口（东西两侧的垛墙）：只看得到垛子顶和每个垛子朝南的小端面
  function merlonsV(xa, y0, y1, zb, zt) {
    var s = '', zc = zb + 2.4, tile = T.gray;
    s += E.rect(xa, y0 - zc * K, PW, y1 - y0, WC.par) + E.line('M' + f(xa) + ' ' + f(y0 - zc * K) + 'V' + f(y1 - zc * K) + 'M' + f(xa + PW) + ' ' + f(y0 - zc * K) + 'V' + f(y1 - zc * K), C.gold, 0.4);
    for (var k = Math.floor(y0 / 8) - 1; k * 8 < y1; k++) {
      var ya = Math.max(y0, k * 8 + 1.5), yb = Math.min(y1, k * 8 + 6.5);
      if (yb - ya < 1) continue;
      s += E.rect(xa - 0.3, ya - zt * K, PW + 0.6, yb - ya, tile.fill, tile.line, 0.4);
      s += E.rect(xa, yb - zt * K, PW, (zt - zc) * K, WC.face, C.gold, 0.4);
    }
    return s;
  }
  // 墙顶海墁：横缝周期 6、竖缝周期 12 错缝（都按世界坐标）
  function walkTex(x0, x1, y0, y1) {
    var d = '', y;
    for (y = Math.ceil(y0 / 6) * 6; y < y1; y += 6) d += 'M' + f(x0) + ' ' + f(y) + 'H' + f(x1);
    for (y = Math.floor(y0 / 6) * 6; y < y1; y += 6) {
      var off = (Math.round(y / 6) % 2 + 2) % 2 ? 6 : 0;
      for (var x = Math.floor((x0 - off) / 12) * 12 + off; x < x1; x += 12) d += 'M' + f(x) + ' ' + f(Math.max(y0, y)) + 'V' + f(Math.min(y1, y + 6));
    }
    return E.line(d, WC.joint, 0.45, ' stroke-opacity="0.4"');
  }

  function wallTile(mask) {
    var id = 'east-common-wall-' + bits(mask), ctx = new E.Ctx(id, 1), G = wallGrid(mask), body = '', up = 30, sh = WH * K;
    var filled = function (i, j) { return i < 0 || i > 2 || j < 0 || j > 2 ? null : G[j][i]; };
    if (mask) {
      var tops = '', N = [], V = [], S = [], i, j;
      for (j = 0; j < 3; j++) for (i = 0; i < 3; i++) {
        if (!G[j][i]) continue;
        tops += E.poly([[XS[i], XS[j] - sh], [XS[i + 1], XS[j] - sh], [XS[i + 1], XS[j + 1] - sh], [XS[i], XS[j + 1] - sh]]);
        if (filled(i + 1, j) === false) V.push([XS[i + 1] - PW, XS[j], XS[j + 1], XS[i + 1]]);
        if (filled(i - 1, j) === false) V.push([XS[i], XS[j], XS[j + 1], XS[i]]);
        if (filled(i, j + 1) === false) S.push([XS[i], XS[i + 1], XS[j + 1], i, j]);
        if (filled(i, j - 1) === false) N.push([XS[i], XS[i + 1], XS[j]]);
      }
      body += E.path(tops, WC.top) + E.clip(ctx, tops, walkTex(0, 48, -sh, 48 - sh));
      var ed = '';
      V.forEach(function (v) { ed += 'M' + f(v[3]) + ' ' + f(v[1] - sh) + 'V' + f(v[2] - sh); });
      N.forEach(function (n) { ed += 'M' + f(n[0]) + ' ' + f(n[2] - sh) + 'H' + f(n[1]); });
      body += E.line(ed, C.gold, 0.8);
      N.forEach(function (n) { body += merlonsH(n[0], n[1], n[2] + PW, PW, WH, WH + 3.5, true); });
      V.forEach(function (v) { body += merlonsV(v[0], v[1], v[2], WH, WH + PH); });
      S.forEach(function (q) {
        // 南面墙段的真端头：左 / 右邻小格不是墙
        var ends = [filled(q[3] - 1, q[4]) === false, filled(q[3] + 1, q[4]) === false];
        body += wallFace(ctx, q[0], q[1], q[2], WH, ends) + merlonsH(q[0], q[1], q[2], PW, WH, WH + PH, false);
      });
    }
    var sym = tileSym(id, 1, 1, up, body);
    return { id: id, svg: sym.svg, name: '城墙 ' + bits(mask), meta: {
      id: id, style: 'east', race: 'common', category: 'wall', kind: 'wall_city', facility: 'city_wall', variant: mask,
      footprint: [1, 1], height_px: up, anchor: sym.anchor, viewBox: sym.viewBox,
      tags: ['dual_grid', 'mask_' + bits(mask), 'crenellated', 'brick_faced'].concat(mask === 0 ? ['empty'] : []), roof: 'none',
      note: '夯土包砖城墙双网格瓦片，NW NE SW SE = ' + bits(mask) + '；墙体比逻辑格四边各收 ' + IN + ' px，墙高 ' + WH +
        '，南沿与东西沿是垛口（灰瓦压顶、开望孔），北沿是女墙' + (mask === 0 ? '；空瓦片，透明占位' : ''),
      name_zh: '城墙', mask: mask
    } };
  }

  /* ---------- 叠加件：城门楼 gate-h / gate-v、角楼 tower ----------
   * 局部坐标同 east-core.symbol：原点 = 占地左前角，g 向南，占地 g∈[-d*48, 0]。墙体平面在逻辑格内 g∈[-42,-6]（东西向）或 x∈[6,42]（南北向）。
   * 砖缝、垛口按 x 周期 8、海墁按 12 / 6 摆放；占地起点都落在逻辑格边上（48 的倍数），所以与底下的城墙瓦片纹理对齐。
   */
  var shed = HA.H.shed, sy = E.sy;
  function archPath(x, yb, w, hh) {
    var r = w / 2;
    return 'M' + f(x) + ' ' + f(yb) + 'V' + f(yb - hh + r) + 'A' + f(r) + ' ' + f(r) + ' 0 0 1 ' + f(x + w) + ' ' + f(yb - hh + r) + 'V' + f(yb) + 'Z';
  }
  function wallTop(ctx, x0, x1, gb, gf, z) {
    var y0 = sy(gb, z), y1 = sy(gf, z);
    return E.rect(x0, y0, x1 - x0, y1 - y0, WC.top) + E.clipRaw(x0, y0, x1 - x0, y1 - y0, walkTex(x0, x1, y0, y1));
  }
  // 一层楼身：墙面 + 开间（窗 / 门）+ 柱 + 额枋
  function storey(x0, x1, g, z0, z1, n, wall, doorAt, winKind) {
    var s = E.face(x0, x1, g, z0, z1, wall || C.cream), bw = (x1 - x0) / n, k;
    for (k = 0; k < n; k++) {
      var bx = x0 + k * bw;
      if (k === doorAt) s += E.door(bx + bw * 0.18, g, z0, bw * 0.64, Math.min(11, z1 - z0 - 3), 'double');
      else s += E.win(bx + bw * 0.2, g, z0 + (z1 - z0) * 0.3, bw * 0.6, (z1 - z0) * 0.42, winKind || 'lattice');
    }
    for (k = 0; k <= n; k++) s += E.col(x0 + k * bw, g, z0, z1, C.vermil);
    return s + E.face(x0 - 0.5, x1 + 0.5, g, z1 - 2.2, z1, C.teal, C.gold2, 0.5);
  }
  function plaque(cx, g, z, w) { return E.rect(cx - w / 2, sy(g, z), w, 4.2, C.navy, C.gold2, 0.7) + E.line('M' + f(cx - w / 2 + 2.5) + ' ' + f(sy(g, z) + 2.1) + 'H' + f(cx + w / 2 - 2.5), C.gold2, 0.9, ' stroke-dasharray="2.2 1.4"'); }

  // 东西向墙段上的城门楼：占 3 格，中间一格开拱形门洞；墙顶重檐歇山城楼（下层腰檐 + 上层歇山），城门匾
  function gateH() {
    return E.symbol('east-common-wall-gate-h', 8801, 3, 1, function (ctx) {
      var s = '', Z = WH, W = 144, gF = -6, gB = -42, t = T.gray, z1 = Z + 15, z2 = Z + 32;
      s += wallTop(ctx, 0, W, gB, gF, Z) + merlonsH(0, W, gB + PW, PW, Z, Z + 3.5, true);
      // 城楼：台明 → 下层 7 间 → 腰檐 → 上层 5 间带平座栏杆 → 歇山顶
      s += E.rect(12, sy(-40, Z + 1), 120, sy(-12, Z + 1) - sy(-40, Z + 1), C.stoneL, C.gold, 0.6); // 城台上的台明
      s += storey(16, 128, -16, Z + 1, z1, 7, C.cream, 3, 'lattice');
      s += shed(ctx, 14, 130, -16, z1 - 2, t, 6, 4);
      s += storey(26, 118, -20, z1 + 2, z2, 5, C.vermil, -1, 'hex');
      s += HA.H.railing(26, 118, -18, z1 + 2, z1 + 5.5, C.vermil, 2.6);
      s += E.roofEW(ctx, { x0: 26, x1: 118, gb: -36, gf: -20, h: z2, rh: 14, type: 'xie', t: t, ov: 7, os: 6, lift: 8, ridge: 'curl', ridgeW: 3.4 });
      // 南面墙身 + 门洞（石券 + 门洞 + 两扇开启的朱门）+ 城门匾 + 垛口
      s += wallFace(ctx, 0, W, gF, Z, [false, false]);
      var yb = gF, hh = 19 * K;
      s += E.path(archPath(58, yb, 28, hh + 3), C.stone, C.gold, 0.9) + E.path(archPath(61, yb, 22, hh), C.navy, C.gold, 1);
      s += E.rect(61, yb - hh * 0.62, 3, hh * 0.62, C.vermil, C.gold2, 0.4) + E.rect(80, yb - hh * 0.62, 3, hh * 0.62, C.vermil, C.gold2, 0.4);
      s += plaque(72, gF, Z - 3, 18);
      s += merlonsH(0, W, gF, PW, Z, Z + PH, false);
      return s;
    });
  }

  // 南北向墙段上的城门楼：门洞东西向穿墙（斜俯视看不到侧面，靠城楼与匾辨认）；城楼屋脊南北向，山面朝南，向北伸出占地格
  function gateV() {
    return E.symbol('east-common-wall-gate-v', 8802, 1, 1, function (ctx) {
      var s = '', Z = WH, t = T.gray, gb = -40, gf = -10, z1 = Z + 13, z2 = Z + 25;
      // 门洞侧壁暗口：南北向墙的东西侧壁在斜俯视下是一条线，这里只在门洞处露出 4 px 窄条：
      // 石券框 + 拱顶暗口（门洞 g∈[-36,-12]、高 17，在侧壁上投成 y∈[-50,-12]），告诉人路从这里穿墙而过
      [[2, 6, C.stone], [42, 46, mix(C.stone, C.gray, 0.35)]].forEach(function (q) {
        var xa = q[0], xb = q[1], w = xb - xa;
        s += E.path('M' + f(xa) + ' -7V-53Q' + f(xa + w / 2) + ' -57 ' + f(xb) + ' -53V-7Z', q[2], C.gold, 0.6);
        s += E.path('M' + f(xa + 0.6) + ' -12V-48.5Q' + f(xa + w / 2) + ' -51.5 ' + f(xb - 0.6) + ' -48.5V-12Z', C.navy, C.gold2, 0.4);
        s += E.rect(xa + 0.6, -14, w - 1.2, 2, mix(C.navy, C.stone, 0.35));
      });
      s += wallTop(ctx, 6, 42, -56, 0, Z);
      s += merlonsV(6, -56, 0, Z, Z + PH) + merlonsV(42 - PW, -56, 0, Z, Z + PH);
      s += E.shadow(10, 38, gb, gf, 20, 4).replace('fill-opacity="0.2"', 'fill-opacity="0.12"');
      // 下层：楼身 + 两侧下檐（斜坡条）
      s += storey(10, 38, gf, Z, z1, 3, C.cream, 1, 'lattice');
      [[5, 14], [34, 43]].forEach(function (q, i) {
        var d = i === 0 ? E.poly([[q[0], sy(gf + 4, z1 - 1)], [q[1], sy(gf + 4, z1 + 3)], [q[1], sy(gb - 4, z1 + 3)], [q[0], sy(gb - 4, z1 - 1)]])
          : E.poly([[q[0], sy(gf + 4, z1 + 3)], [q[1], sy(gf + 4, z1 - 1)], [q[1], sy(gb - 4, z1 - 1)], [q[0], sy(gb - 4, z1 + 3)]]);
        s += E.path(d, i ? t.dark : t.lite) + E.clip(ctx, d, E.rowsH(q[0], q[1], sy(gb - 4, z1 + 4), sy(gf + 4, z1 - 2), 3, t.dark)) + E.path(d, 'none', t.line, 0.9);
      });
      s += shed(ctx, 9, 39, gf, z1 - 1, t, 4, 3);
      // 上层 + 悬山（博风板、悬鱼）
      s += storey(14, 34, gf - 6, z1 + 2, z2, 2, C.vermil, -1, 'hex');
      s += plaque(24, gf - 6, z2 - 6, 12);
      s += E.roofNS(ctx, { x0: 14, x1: 34, gb: gb + 4, gf: gf - 6, h: z2, rh: 11, t: t, ov: 6, os: 4, gable: 'board', lift: 3 });
      return s;
    });
  }

  // 角楼：比墙体略宽的方墩台（四面包砖、垛口），台上两层楼阁；kind = pyr 重檐攒尖 / xie 重檐歇山
  function tower(kind) {
    var id = 'east-common-wall-tower' + (kind === 'xie' ? '-xieshan' : '');
    return E.symbol(id, kind === 'xie' ? 8804 : 8803, 1, 1, function (ctx) {
      var s = '', Z = WH + 2, t = kind === 'xie' ? T.navy : T.gray, z1 = Z + 13, z2 = Z + 24;
      s += wallTop(ctx, 2, 46, -46, -2, Z) + merlonsH(2, 46, -46 + PW, PW, Z, Z + 3.5, true);
      s += merlonsV(2, -46, -2, Z, Z + PH) + merlonsV(46 - PW, -46, -2, Z, Z + PH);
      s += storey(11, 37, -15, Z, z1, 3, C.cream, 1, 'lattice');
      s += shed(ctx, 9, 39, -15, z1 - 1, t, 5, 4);
      s += storey(15, 33, -20, z1 + 1, z2, 2, C.vermil, -1, 'hex');
      if (kind === 'xie') s += E.roofEW(ctx, { x0: 15, x1: 33, gb: -36, gf: -20, h: z2, rh: 13, type: 'xie', t: t, ov: 6, os: 5, lift: 7, ridge: 'curl', ridgeW: 2.6 });
      else s += E.roofPyr(ctx, { x0: 15, x1: 33, gb: -36, gf: -20, h: z2, rh: 15, t: t, ov: 5, lift: 6 });
      s += wallFace(ctx, 2, 46, -2, Z, [true, true]) + merlonsH(2, 46, -2, PW, Z, Z + PH, false);
      return s;
    });
  }

  function overlayItem(sym, kind, facility, roof, tags, note, name, variant) {
    return { id: sym.id, svg: sym.svg, name: name, over: sym.over, meta: {
      id: sym.id, style: 'east', race: 'common', category: 'wall', kind: kind, facility: facility, variant: variant,
      footprint: [sym.viewBox[2] / 48, Math.round((sym.viewBox[3] - sym.up) / 48)], height_px: sym.up, anchor: sym.anchor, viewBox: sym.viewBox,
      tags: ['overlay', 'logical_cell'].concat(tags), roof: roof, note: note, name_zh: name
    } };
  }

  function items() {
    var out = [], m;
    ['dirt', 'stone', 'highway'].forEach(function (k) { for (m = 0; m < 16; m++) out.push(roadTile(k, m)); });
    for (m = 0; m < 16; m++) out.push(wallTile(m));
    out.push(overlayItem(gateH(), 'wall_gate_h', 'gate', 'hip_tile', ['gatehouse', 'double_eave', 'arch_gate'],
      '东西向墙段城门楼，占 3 个逻辑格、门洞在中间格；锚点 = 中间格前沿中点。重檐歇山（RoofId 无歇山，取 hip_tile）。叠加件画在城墙瓦片之后', '城门楼（东西向墙）', 1));
    out.push(overlayItem(gateV(), 'wall_gate_v', 'gate', 'gable_tile', ['gatehouse', 'double_eave'],
      '南北向墙段城门楼，锚点 = 门洞所在逻辑格前沿中点；城楼向北伸出约 1 格（画在上伸区）。门洞东西向穿墙，斜俯视下侧面不可见；上层悬山（gable_tile）', '城门楼（南北向墙）', 2));
    out.push(overlayItem(tower('pyr'), 'wall_tower', 'watchtower', 'hip_tile', ['corner_tower', 'double_eave', 'pyramid_roof'],
      '角楼：包砖方墩台 + 两层楼阁，重檐攒尖（RoofId 无攒尖，取 hip_tile）；放在城墙拐角或端点的逻辑格上', '角楼（攒尖）', 3));
    out.push(overlayItem(tower('xie'), 'wall_tower', 'watchtower', 'hip_tile', ['corner_tower', 'double_eave'],
      '角楼变体：藏青瓦重檐歇山（取 hip_tile）', '角楼（歇山）', 4));
    return out;
  }

  return { items: items, region: region, bits: bits, ROADS: ROADS, roadTile: roadTile, wallTile: wallTile, IN: IN, WH: WH };
});
