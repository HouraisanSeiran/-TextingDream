/*
 * 织梦 · 城镇内部地图 · 东方玄幻（east-base）共用画笔（美术素材，尚未接入游戏）
 *
 * 画法：国潮不透明平涂 + 金线勾边 + 叠晕，与 fog-brushes/fog-xiangyun.js 的 PAL 统一。
 * 投影：3/4 斜俯视。局部坐标里地面前后用 g（越往南越大），高度用 z；屏幕 y = g - z*K。
 *       每个 symbol 的局部原点在占地矩形左前角：占地 x∈[0, w*48]，g∈[-d*48, 0]。
 * 全部是原创程序化路径，不读外部图片。浏览器挂 window.TownArtEast_core，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory();
  else root.TownArtEast_core = factory();
})(this, function () {
  'use strict';
  var CELL = 48, K = 0.85;

  function rng(seed) { // mulberry32
    return function () {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      var t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  function f(n) { return String(Math.round(n * 100) / 100); }
  function hx(c) { return [1, 3, 5].map(function (i) { return parseInt(c.slice(i, i + 2), 16); }); }
  function mix(a, b, t) {
    var A = hx(a), B = hx(b);
    return '#' + A.map(function (v, i) { var x = Math.round(v + (B[i] - v) * t); return (x < 16 ? '0' : '') + x.toString(16); }).join('');
  }

  // 色板（与规范第 2 节东方表一致；thatch / earth 两组是由赭黄、赭褐、米白调出来的）
  var C = {
    gold: '#c98f3c', gold2: '#f3c46a', cream: '#f1dcae', creamL: '#fbf0d4', ochre: '#eeb24f', ochreL: '#f8d78e',
    orange: '#e47c36', vermil: '#cd5030', vermilL: '#e7864f', umber: '#8c3d22', umberL: '#b5623a',
    teal: '#2e938d', tealL: '#6cc1b3', navy: '#1f3c5b', navyL: '#30697f', gray: '#5d6670', grayL: '#7b8590',
    grass: '#d9c58f', shadow: '#1f3c5b'
  };
  C.earth = mix(C.ochre, C.umber, 0.25);   // 夯土
  C.earthL = mix(C.ochre, C.cream, 0.45);
  C.stone = mix(C.grayL, C.cream, 0.45);   // 青石 / 台基
  C.stoneL = mix(C.grayL, C.creamL, 0.68);
  C.leaf = mix(C.teal, '#5f7d3a', 0.45);   // 树叶（青绿偏草绿）
  C.leafL = mix(C.tealL, '#a9c46a', 0.4);
  C.water = mix(C.teal, C.navyL, 0.3);

  var TILE = {
    gray:   { name: '灰瓦', fill: '#5d6670', lite: '#7b8590', dark: '#454d56', line: '#c98f3c' },
    teal:   { name: '青绿琉璃', fill: '#2e938d', lite: '#6cc1b3', dark: '#1d6b67', line: '#f3c46a' },
    navy:   { name: '藏青', fill: '#1f3c5b', lite: '#30697f', dark: '#14283e', line: '#e9bb5a' },
    thatch: { name: '茅草', fill: mix(C.ochre, C.umber, 0.32), lite: mix(C.ochre, C.cream, 0.3), dark: mix(C.ochre, C.umber, 0.58), line: C.umber },
    bamboo: { name: '竹篾', fill: mix(C.ochre, '#7d8a3a', 0.35), lite: mix(C.ochreL, C.cream, 0.3), dark: mix(C.ochre, C.umber, 0.5), line: C.umber }
  };

  function sy(g, z) { return g - z * K; }
  function P(x, g, z) { return [x, g - z * K]; }
  function pt(p) { return f(p[0]) + ' ' + f(p[1]); }
  function poly(pts, open) { return pts.map(function (p, i) { return (i ? 'L' : 'M') + pt(p); }).join('') + (open ? '' : 'Z'); }
  function path(d, fill, line, lw, extra) {
    return '<path d="' + d + '" fill="' + (fill || 'none') + '"' +
      (line ? ' stroke="' + line + '" stroke-width="' + f(lw || 1.2) + '" stroke-linejoin="round" stroke-linecap="round"' : '') + (extra || '') + '/>';
  }
  function line(d, color, lw, extra) { return path(d, 'none', color, lw, extra); }
  function rect(x, y, w, h, fill, ln, lw) { return path(poly([[x, y], [x + w, y], [x + w, y + h], [x, y + h]]), fill, ln, lw); }
  function circle(x, y, r, fill, ln, lw) {
    return '<circle cx="' + f(x) + '" cy="' + f(y) + '" r="' + f(r) + '" fill="' + (fill || 'none') + '"' +
      (ln ? ' stroke="' + ln + '" stroke-width="' + f(lw || 1) + '"' : '') + '/>';
  }

  // 每个 symbol 一个 ctx：内部 clipPath id 都带 symbol id 前缀，全目录唯一；top 记录画到的最高处（算 viewBox 上伸）
  function Ctx(id, seed) { this.id = id; this.n = 0; this.top = 0; this.r = rng(seed || 1); }
  Ctx.prototype.uid = function (s) { return this.id + '-' + (s || 'k') + (this.n++); };
  Ctx.prototype.up = function (y) { if (y < this.top) this.top = y; };
  function clip(ctx, d, inner) {
    var id = ctx.uid('clip');
    return '<clipPath id="' + id + '"><path d="' + d + '"/></clipPath><g clip-path="url(#' + id + ')">' + inner + '</g>';
  }

  // 投影：光从左上来，投影平涂在右下；向右最多 7 px、向下 3 px（不超出 6 px 的限制）
  function shadow(x0, x1, gb, gf, h, sx) {
    sx = sx == null ? Math.min(7, 2 + h * 0.12) : sx;
    return path(poly([[x0 + sx, gb + 2], [x1 + sx, gb + 2], [x1 + sx, gf + 3], [x0 + sx * 0.6, gf + 3]]), C.shadow, null, 0, ' fill-opacity="0.2"');
  }

  // 当前正在画的 symbol：poly / rect / circle 都把画到的最高点记进来，用来算 viewBox 的上伸像素
  var CUR = null;
  function begin(ctx) { CUR = ctx; }
  function track(y) { if (CUR && y < CUR.top) CUR.top = y; }

  // ---------- 屋顶 ----------
  // 檐口：中段平直，两端起翘（|2t-1|³ 曲线），L = 起翘像素
  function eavePts(xa, xb, y, L, n) {
    var o = [];
    for (var i = 0; i <= n; i++) { var t = i / n, u = Math.abs(2 * t - 1); o.push([xa + (xb - xa) * t, y - L * u * u * u]); }
    return o;
  }
  function rowsV(x0, x1, y0, y1, step, color, lw, op) {
    var d = '';
    for (var x = x0 + step / 2; x < x1; x += step) d += 'M' + f(x) + ' ' + f(y0) + 'V' + f(y1);
    return d ? line(d, color, lw || 0.9, ' stroke-opacity="' + (op || 0.6) + '"') : '';
  }
  function rowsH(x0, x1, y0, y1, step, color, lw, op) {
    var d = '';
    for (var y = y0 + step / 2; y < y1; y += step) d += 'M' + f(x0) + ' ' + f(y) + 'H' + f(x1);
    return d ? line(d, color, lw || 0.9, ' stroke-opacity="' + (op || 0.6) + '"') : '';
  }
  function slope(ctx, pts, fill, rows, ln) {
    var d = poly(pts);
    return path(d, fill) + (rows ? clip(ctx, d, rows) : '') + path(d, 'none', ln, 1.1);
  }
  function lerp(a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]; }
  // 屋脊：金线外圈 + 瓦色 + 一道浅色（叠晕）
  function ridgeLine(d, t, w) {
    w = w || 3;
    return line(d, t.line, w + 1.6) + line(d, t.dark, w) + line(d, t.lite, Math.max(0.6, w * 0.3), ' stroke-opacity="0.8"');
  }
  // 脊端：horn = 南方燕尾起翘；curl = 鸱吻；plain = 无
  function ridgeEnd(x, y, dir, kind, t) {
    if (!kind || kind === 'plain') return '';
    var d;
    // 燕尾：从脊上往外收、末端向上外翘，最多伸出脊端 2.5 px（不让建筑横向画出占地太多）
    if (kind === 'horn') d = 'M' + f(x + dir * 7) + ' ' + f(y) + 'Q' + f(x + dir * 1) + ' ' + f(y) + ' ' + f(x - dir * 2.5) + ' ' + f(y - 6.5);
    else d = 'M' + f(x - dir * 1) + ' ' + f(y) + 'L' + f(x - dir * 1) + ' ' + f(y - 6) + 'Q' + f(x - dir * 1) + ' ' + f(y - 9.5) + ' ' + f(x - dir * 4.5) + ' ' + f(y - 8.5) +
      'Q' + f(x - dir * 6.5) + ' ' + f(y - 7.5) + ' ' + f(x - dir * 4.5) + ' ' + f(y - 5.5);
    track(y - 10);
    return line(d, t.line, 4) + line(d, t.dark, 2.4);
  }

  /**
   * 东西向屋脊的屋顶（正房、铺面等，坡面朝南北）。
   * o: x0,x1 墙体左右；gb,gf 墙体前后；h 檐口高；rh 举高；type = hard 硬山 / hang 悬山 / hip 庑殿 / xie 歇山 / juan 卷棚
   *    t 瓦色；ov 前后出檐；os 两山出际；lift 起翘；ridge 脊端
   */
  function roofEW(ctx, o) {
    var t = o.t || TILE.gray, h = o.h, rh = o.rh, type = o.type || 'hard';
    var ov = o.ov == null ? 4 : o.ov;
    var os = o.os == null ? ({ hard: 1.5, hang: 5, juan: 2, hip: 3, xie: 3 }[type]) : o.os;
    var L = o.lift == null ? ({ hard: 1.2, hang: 2, juan: 1.5, hip: 5, xie: 6 }[type]) : o.lift;
    var ex0 = o.x0 - os, ex1 = o.x1 + os, gm = (o.gb + o.gf) / 2;
    var yF = sy(o.gf + ov, h), yB = sy(o.gb - ov, h), yR = sy(gm, h + rh);
    if (yB > yR - 2) yB = yR - 2;
    var hipLike = type === 'hip' || type === 'xie';
    var ins = hipLike ? Math.min((ex1 - ex0) / 2 - 3, (type === 'hip' ? 0.55 : 0.32) * (yF - yB)) : 0;
    var rx0 = ex0 + ins, rx1 = ex1 - ins;
    var F = eavePts(ex0, ex1, yF, L, 24), B = eavePts(ex0, ex1, yB, L * 0.6, 16);
    var lf = F[0], rf = F[F.length - 1], lb = B[0], rb = B[B.length - 1];
    track(Math.min(lb[1], yR) - 3);
    var s = '', step = o.step || 3.4, rr = o.rows !== false;
    var R0 = [[rx0, yR], [rx1, yR]];
    s += slope(ctx, R0.concat(B.slice().reverse()), t.lite, rr && rowsV(ex0, ex1, yB - L, yR, step, t.dark), t.line);
    if (hipLike) {
      s += slope(ctx, [lb, [rx0, yR], lf], t.lite, rr && rowsH(ex0, rx0, yB - L, yF, 3, t.dark), t.line);
      s += slope(ctx, [rb, [rx1, yR], rf], t.dark, rr && rowsH(rx1, ex1, yB - L, yF, 3, t.fill), t.line);
      if (type === 'xie') { // 山花：侧坡上部的三角形山面
        [[rx0, lf, lb], [rx1, rf, rb]].forEach(function (q) {
          var a = [q[0], yR], p1 = lerp(a, q[1], 0.5), p2 = lerp(a, q[2], 0.5);
          s += path(poly([a, p1, p2]), C.vermil, C.gold2, 0.9) + circle((a[0] + p1[0] * 2) / 3, (a[1] + p1[1] + p2[1]) / 3, 0.9, C.gold2);
        });
      }
    }
    s += slope(ctx, R0.concat(F.slice().reverse()), t.fill, rr && rowsV(ex0, ex1, yR, yF + 1, step, t.dark), t.line);
    // 檐口：一道深色滴水 + 金线；瓦当小点
    s += line(poly(F, true), t.dark, 2.2) + line(poly(F, true), t.line, 0.9);
    if (o.dots !== false) {
      var dd = '';
      for (var i = 1; i < F.length - 1; i += 2) dd += circle(F[i][0], F[i][1] + 0.4, 0.75, t.lite);
      s += dd;
    }
    if (type === 'juan') {
      s += path(poly([[ex0 + 1, yR - 2.2], [ex1 - 1, yR - 2.2], [ex1 - 1, yR + 2.2], [ex0 + 1, yR + 2.2]]), t.lite, t.line, 0.8);
    } else {
      if (hipLike) s += [[rx0, lf], [rx0, lb], [rx1, rf], [rx1, rb]].map(function (q) {
        var d = 'M' + f(q[0]) + ' ' + f(yR) + 'L' + pt(q[1]);
        return line(d, t.line, 2.6) + line(d, t.dark, 1.5);
      }).join('');
      else s += [[ex0, lf], [ex0, lb], [ex1, rf], [ex1, rb]].map(function (q) {
        var d = 'M' + f(q[0]) + ' ' + f(yR) + 'L' + pt(q[1]);
        return line(d, t.line, 2.4) + line(d, t.dark, 1.3);
      }).join('');
      s += ridgeLine('M' + f(rx0) + ' ' + f(yR) + 'H' + f(rx1), t, o.ridgeW || 3);
      s += ridgeEnd(rx0, yR, 1, o.ridge, t) + ridgeEnd(rx1, yR, -1, o.ridge, t);
    }
    return s;
  }

  /**
   * 南北向屋脊的屋顶（厢房、窄高楼等，山面朝南）。看得到朝南的山墙三角、左右两坡。
   * o: x0,x1,gb,gf,h,rh,t；gable = 'board' 悬山博风+山花 / 'wall' 硬山（山墙同墙色）；os 山面出际；ov 两侧出檐
   */
  function roofNS(ctx, o) {
    var t = o.t || TILE.gray, h = o.h, rh = o.rh, ov = o.ov == null ? 3 : o.ov, os = o.os == null ? 3 : o.os;
    var xm = (o.x0 + o.x1) / 2, e0 = o.x0 - ov, e1 = o.x1 + ov, gF = o.gf + os, gB = o.gb - os;
    var A = P(xm, gF, h + rh), Bk = P(xm, gB, h + rh);
    var LF = P(e0, gF, h), LB = P(e0, gB, h), RF = P(e1, gF, h), RB = P(e1, gB, h);
    LF[1] -= o.lift || 1; RF[1] -= o.lift || 1;
    track(Bk[1] - 3);
    var s = '';
    // 山墙三角（在出际后面，露出来的部分在博风板下面）
    var gw = [[o.x0, sy(o.gf, h)], [xm, sy(o.gf, h + rh)], [o.x1, sy(o.gf, h)]];
    s += path(poly(gw), o.gable === 'board' ? C.vermil : (o.wall || C.cream), o.gable === 'board' ? C.gold2 : C.gold, 0.9);
    if (o.gable === 'board') { // 山花：悬鱼 + 一枚金点
      var py = sy(o.gf, h + rh * 0.55);
      s += path('M' + f(xm) + ' ' + f(py - 3) + 'L' + f(xm + 2.4) + ' ' + f(py + 1.5) + 'L' + f(xm) + ' ' + f(py + 4) + 'L' + f(xm - 2.4) + ' ' + f(py + 1.5) + 'Z', C.gold2);
    }
    var st = 3.2;
    s += slope(ctx, [Bk, A, LF, LB], t.lite, rowsH(e0, xm, Bk[1], LF[1] + 2, st, t.dark), t.line);
    s += slope(ctx, [A, Bk, RB, RF], t.fill, rowsH(xm, e1, Bk[1], RF[1] + 2, st, t.dark), t.line);
    // 博风板（前沿两条斜线）与正脊
    var vd = 'M' + pt(LF) + 'L' + pt(A) + 'L' + pt(RF);
    s += line(vd, t.line, 3) + line(vd, o.gable === 'board' ? C.umber : t.dark, 1.6);
    s += ridgeLine('M' + pt(A) + 'L' + pt(Bk), t, 2.6);
    return s;
  }

  /**
   * 攒尖顶（四角）。o: x0,x1,gb,gf,h,rh,t,ov,lift；finial 宝顶
   */
  function roofPyr(ctx, o) {
    var t = o.t || TILE.gray, h = o.h, rh = o.rh, ov = o.ov == null ? 4 : o.ov, L = o.lift == null ? 6 : o.lift;
    var e0 = o.x0 - ov, e1 = o.x1 + ov, gF = o.gf + ov, gB = o.gb - ov, xm = (o.x0 + o.x1) / 2, gm = (o.gb + o.gf) / 2;
    var Ap = P(xm, gm, h + rh), F = eavePts(e0, e1, sy(gF, h), L, 20), B = eavePts(e0, e1, sy(gB, h), L * 0.6, 12);
    var LF = F[0], RF = F[F.length - 1], LB = B[0], RB = B[B.length - 1];
    track(Math.min(Ap[1], LB[1]) - 8);
    var s = '';
    if (Ap[1] > LB[1] + 1) s += slope(ctx, [Ap].concat(B), t.lite, rowsV(e0, e1, LB[1] - L, Ap[1], 3.2, t.dark), t.line);
    s += slope(ctx, [LB, Ap, LF], t.lite, rowsH(e0, xm, LB[1] - L, LF[1] + 1, 3, t.dark), t.line);
    s += slope(ctx, [RB, Ap, RF], t.dark, rowsH(xm, e1, RB[1] - L, RF[1] + 1, 3, t.fill), t.line);
    s += slope(ctx, [Ap].concat(F), t.fill, rowsV(e0, e1, Ap[1], LF[1] + L + 1, 3.2, t.dark), t.line);
    s += line(poly(F, true), t.dark, 2.2) + line(poly(F, true), t.line, 0.9);
    [LF, RF, LB, RB].forEach(function (q) { var d = 'M' + pt(Ap) + 'L' + pt(q); s += line(d, t.line, 2.6) + line(d, t.dark, 1.4); });
    if (o.finial !== false) { // 宝顶：一颗金珠 + 托座
      s += path(poly([[Ap[0] - 2.2, Ap[1] + 0.5], [Ap[0] + 2.2, Ap[1] + 0.5], [Ap[0] + 1.2, Ap[1] - 2], [Ap[0] - 1.2, Ap[1] - 2]]), t.dark, t.line, 0.7);
      s += circle(Ap[0], Ap[1] - 4.2, 2.4, C.ochre, C.gold, 0.8) + circle(Ap[0] - 0.7, Ap[1] - 4.9, 0.8, C.ochreL);
    }
    return s;
  }

  // ---------- 墙体与立面 ----------
  // 正立面（朝南的一块墙面）：x0..x1，地面线 g，高 z0..z1
  function face(x0, x1, g, z0, z1, fill, ln, lw) {
    var y0 = sy(g, z1), y1 = sy(g, z0);
    track(y0);
    return rect(x0, y0, x1 - x0, y1 - y0, fill, ln === undefined ? C.gold : ln, lw || 1);
  }
  // 台基：一条石阶前脸 + 顶面浅条
  function plinth(x0, x1, g, hz) {
    var y0 = sy(g, hz);
    return rect(x0, y0 - 2, x1 - x0, 2, C.stoneL, null) + rect(x0, y0, x1 - x0, g - y0, C.stone, C.gold, 0.8) +
      line('M' + f(x0 + 1) + ' ' + f(y0) + 'H' + f(x1 - 1), C.grayL, 0.6, ' stroke-opacity="0.6"');
  }
  // 朱红立柱
  function col(x, g, z0, z1, c) {
    return rect(x - 1.2, sy(g, z1), 2.4, (z1 - z0) * K, c || C.vermil, C.gold2, 0.5);
  }
  // 门：double 朱红双扇带门钉 / plank 木板门 / moon 月洞门 / arch 拱门 / shop 铺面排门
  function door(x, g, z0, w, hz, kind) {
    var y1 = sy(g, z0), y0 = sy(g, z0 + hz), s = '', cx = x + w / 2;
    kind = kind || 'double';
    if (kind === 'moon') {
      var r = w / 2;
      return circle(cx, y1 - r, r + 1.2, C.gold) + circle(cx, y1 - r, r, C.navy) + rect(x - 1, y1 - 1.2, w + 2, 1.2, C.stone);
    }
    if (kind === 'arch') {
      var ra = w / 2, d = 'M' + f(x) + ' ' + f(y1) + 'V' + f(y0 + ra) + 'A' + f(ra) + ' ' + f(ra) + ' 0 0 1 ' + f(x + w) + ' ' + f(y0 + ra) + 'V' + f(y1) + 'Z';
      return path(d, C.navy, C.gold, 1.2);
    }
    if (kind === 'shop') { // 排门板：一溜竖板，中间两扇卸下露出店内
      s += rect(x, y0, w, y1 - y0, C.umberL, C.gold, 0.8);
      for (var i = 1; i < 6; i++) s += line('M' + f(x + w * i / 6) + ' ' + f(y0) + 'V' + f(y1), C.umber, 0.6);
      s += rect(x + w * 2 / 6, y0 + 0.8, w * 2 / 6, y1 - y0 - 0.8, C.navy);
      return s;
    }
    var c = kind === 'plank' ? C.umberL : C.vermil;
    s += rect(x, y0, w, y1 - y0, c, kind === 'plank' ? C.umber : C.gold2, 0.9);
    s += line('M' + f(cx) + ' ' + f(y0) + 'V' + f(y1), kind === 'plank' ? C.umber : C.umber, 0.7);
    if (kind === 'double' && w >= 6) {
      s += circle(cx - 1.4, (y0 + y1) / 2, 0.7, C.gold2) + circle(cx + 1.4, (y0 + y1) / 2, 0.7, C.gold2);
      if (w >= 9) for (var r2 = 0; r2 < 3; r2++) {
        var yy = y0 + (y1 - y0) * (0.2 + r2 * 0.12);
        s += circle(x + w * 0.25, yy, 0.45, C.gold2) + circle(x + w * 0.75, yy, 0.45, C.gold2);
      }
    }
    return s;
  }

  // 窗：lattice 方格棂窗 / round 圆窗 / slit 窄窗 / hex 冰裂纹（简化斜格）
  function win(x, g, z, w, hz, kind) {
    var y1 = sy(g, z), y0 = sy(g, z + hz), s = '', cx = x + w / 2, cy = (y0 + y1) / 2;
    kind = kind || 'lattice';
    if (kind === 'round') {
      var r = Math.min(w, y1 - y0) / 2;
      return circle(cx, cy, r + 0.9, C.gold) + circle(cx, cy, r, C.navy) +
        line('M' + f(cx - r) + ' ' + f(cy) + 'H' + f(cx + r) + 'M' + f(cx) + ' ' + f(cy - r) + 'V' + f(cy + r), C.ochre, 0.6);
    }
    if (kind === 'slit') return rect(x, y0, w, y1 - y0, C.navy, C.gold, 0.6);
    s += rect(x, y0, w, y1 - y0, C.navy, C.gold, 0.8);
    var d = '';
    if (kind === 'hex') {
      for (var i = -2; i < 4; i++) d += 'M' + f(x + w * i / 3) + ' ' + f(y1) + 'L' + f(x + w * (i + 1) / 3) + ' ' + f(y0);
      s += clipRaw(x, y0, w, y1 - y0, line(d, C.ochre, 0.55));
      return s;
    }
    var nx = Math.max(2, Math.round(w / 3)), ny = Math.max(2, Math.round((y1 - y0) / 3));
    for (var a = 1; a < nx; a++) d += 'M' + f(x + w * a / nx) + ' ' + f(y0) + 'V' + f(y1);
    for (var b = 1; b < ny; b++) d += 'M' + f(x) + ' ' + f(y0 + (y1 - y0) * b / ny) + 'H' + f(x + w);
    return s + line(d, C.ochre, 0.55);
  }
  // 冰裂纹窗用的矩形裁剪（需要 CUR 提供 id）
  function clipRaw(x, y, w, h, inner) {
    if (!CUR) return inner;
    return clip(CUR, poly([[x, y], [x + w, y], [x + w, y + h], [x, y + h]]), inner);
  }
  // 灯笼：朱红椭圆 + 金色上下箍 + 穗
  function lantern(x, y, r) {
    r = r || 2.4;
    return line('M' + f(x) + ' ' + f(y - r * 1.6) + 'V' + f(y - r), C.umber, 0.5) +
      '<ellipse cx="' + f(x) + '" cy="' + f(y) + '" rx="' + f(r) + '" ry="' + f(r * 1.15) + '" fill="' + C.vermil + '" stroke="' + C.gold2 + '" stroke-width="0.5"/>' +
      rect(x - r * 0.5, y - r * 1.25, r, r * 0.3, C.ochre) + rect(x - r * 0.5, y + r * 0.95, r, r * 0.3, C.ochre) +
      line('M' + f(x) + ' ' + f(y + r * 1.25) + 'V' + f(y + r * 2), C.ochre, 0.6);
  }
  // 树：几团叠在一起的圆冠，金线勾边，内收一圈浅色叠晕；x,g 是树根位置，hz 冠心高度
  function tree(ctx, x, g, hz, R, kind) {
    var r = ctx.r, s = '', y = sy(g, hz), C0 = [];
    var n = kind === 'pine' ? 3 : 4 + Math.floor(r() * 2);
    s += path(poly([[x - 1.2, g], [x + 1.2, g], [x + 0.8, y + R * 0.3], [x - 0.8, y + R * 0.3]]), C.umber);
    if (kind === 'pine') { // 松：三层平展的扁云状冠
      for (var i = 0; i < n; i++) {
        var yy = y + R * 0.45 - i * R * 0.5, ww = R * (1.25 - i * 0.3);
        C0.push([x - ww * 0.4, yy, ww * 0.55], [x + ww * 0.4, yy + 0.5, ww * 0.5], [x, yy - ww * 0.15, ww * 0.55]);
      }
    } else {
      for (var j = 0; j < n; j++) {
        var a = j / n * Math.PI * 2 + r() * 0.6;
        C0.push([x + Math.cos(a) * R * 0.5, y + Math.sin(a) * R * 0.35, R * (0.5 + r() * 0.15)]);
      }
      C0.push([x, y - R * 0.25, R * 0.6]);
    }
    var disc = function (pad, fill, dy) {
      return '<g fill="' + fill + '">' + C0.map(function (c) { return '<circle cx="' + f(c[0]) + '" cy="' + f(c[1] + (dy || 0)) + '" r="' + f(Math.max(0.5, c[2] + pad)) + '"/>'; }).join('') + '</g>';
    };
    track(y - R * 1.4);
    s += disc(1, C.gold, 0) + disc(0, C.leaf, 0) + disc(-R * 0.28, C.leafL, -R * 0.12);
    return s;
  }
  // 竹丛：几根竹竿 + 竹叶短撇
  function bamboo(ctx, x, g, hz, n) {
    var r = ctx.r, s = '';
    for (var i = 0; i < (n || 4); i++) {
      var bx = x + (i - (n || 4) / 2) * 2.4 + r() * 1.2, top = sy(g, hz * (0.75 + r() * 0.35)), lean = (r() - 0.5) * 4;
      s += line('M' + f(bx) + ' ' + f(g) + 'Q' + f(bx + lean * 0.3) + ' ' + f((g + top) / 2) + ' ' + f(bx + lean) + ' ' + f(top), mix(C.teal, '#6f8a2c', 0.4), 1.3);
      for (var k = 0; k < 4; k++) {
        var ly = top + k * (g - top) * 0.18, lx = bx + lean * (1 - k * 0.2), sd = k % 2 ? 1 : -1;
        s += path('M' + f(lx) + ' ' + f(ly) + 'Q' + f(lx + sd * 3) + ' ' + f(ly - 2) + ' ' + f(lx + sd * 5.5) + ' ' + f(ly + 0.6) + 'Q' + f(lx + sd * 3) + ' ' + f(ly + 0.6) + ' ' + f(lx) + ' ' + f(ly) + 'Z', C.teal, C.gold2, 0.3);
      }
      track(top - 3);
    }
    return s;
  }

  /**
   * 包装成 symbol。draw(ctx) 在局部坐标里画（原点 = 占地左前角，g 向南为正，占地 g∈[-d*48,0]）。
   * 返回 { id, svg, viewBox, anchor, up }；up = 占地矩形以上伸出的像素（规范上限 144）。
   */
  // 扫一遍生成的 SVG 文本，取所有绝对坐标里最小的 y（含圆、椭圆、矩形），兜底 track 漏记的部件
  function scanTop(svg) {
    var top = 0, m, re = /\bd="([^"]*)"/g;
    while ((m = re.exec(svg))) {
      var tok = m[1].match(/[A-Za-z]|-?\d*\.?\d+(?:e-?\d+)?/g) || [], cmd = '', nums = [];
      var flush = function () {
        var i, per = { M: 2, L: 2, T: 2, Q: 4, S: 4, C: 6, A: 7, V: 1 }[cmd];
        if (!per) return;
        for (i = 0; i + per <= nums.length; i += per) {
          var y = cmd === 'V' ? nums[i] : cmd === 'A' ? nums[i + 6] : null;
          if (y !== null) { if (y < top) top = y; continue; }
          for (var k = 1; k < per; k += 2) if (nums[i + k] < top) top = nums[i + k];
        }
      };
      tok.forEach(function (t) { if (/[A-Za-z]/.test(t)) { flush(); cmd = t; nums = []; } else nums.push(parseFloat(t)); });
      flush();
    }
    var rc = /<(circle|ellipse)\b[^>]*?\bcy="([-\d.]+)"[^>]*?\br[y]?="([-\d.]+)"/g;
    while ((m = rc.exec(svg))) { var yy = parseFloat(m[2]) - parseFloat(m[3]); if (yy < top) top = yy; }
    return top;
  }

  function symbol(id, seed, w, d, draw) {
    var ctx = new Ctx(id, seed);
    begin(ctx);
    var body = draw(ctx);
    begin(null);
    var W = w * CELL, D = d * CELL;
    ctx.top = Math.min(ctx.top, scanTop(body) - 2);
    var up = Math.max(0, Math.ceil(-ctx.top - D + 1));
    if (up > 144) up = 144;
    var H = D + up;
    return {
      id: id, up: up, viewBox: [0, 0, W, H], anchor: [W / 2, H],
      svg: '<symbol id="' + id + '" viewBox="0 0 ' + W + ' ' + H + '" overflow="visible"><g transform="translate(0 ' + H + ')">' + body + '</g></symbol>',
      over: Math.ceil(-ctx.top - D + 1) > 144
    };
  }

  return {
    CELL: CELL, K: K, C: C, TILE: TILE, rng: rng, f: f, mix: mix, sy: sy, P: P, pt: pt, poly: poly, path: path, line: line,
    rect: rect, circle: circle, Ctx: Ctx, clip: clip, clipRaw: clipRaw, shadow: shadow, track: track, eavePts: eavePts,
    rowsV: rowsV, rowsH: rowsH, slope: slope, lerp: lerp, ridgeLine: ridgeLine, ridgeEnd: ridgeEnd,
    roofEW: roofEW, roofNS: roofNS, roofPyr: roofPyr, face: face, plinth: plinth, col: col, door: door, win: win,
    lantern: lantern, tree: tree, bamboo: bamboo, symbol: symbol
  };
});
