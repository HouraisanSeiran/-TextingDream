/*
 * 织梦 · 东方文化地标（east-landmark）· 公共画法 —— 美术素材，尚未接入游戏
 * 由 east-special/core.js 复制而来（画风必须一致），只改了全局名；地标专用部件在 lm-parts.js。
 *
 * 3/4 斜俯视：屏幕 y = 地面 y − 高度；48 px 一格；光从左上来，投影平涂在右下。
 * 国潮不透明平涂 + 金线勾边 + 叠晕，色板与 fog-brushes/fog-xiangyun.js 的 PAL 一致。
 * 全部是原创程序化路径，不读任何外部图片。
 *
 * 浏览器挂 window.TownArtEastLandmarkCore；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var CELL = 48;

  function rng(seed) { // mulberry32
    return function () {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      var t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  function hash(s) { var h = 2166136261; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
  function f(n) { return String(Math.round(n * 100) / 100); }
  function hx(c) { return [1, 3, 5].map(function (i) { return parseInt(c.slice(i, i + 2), 16); }); }
  function mix(a, b, t) {
    var A = hx(a), B = hx(b);
    return '#' + A.map(function (v, i) { var x = Math.round(v + (B[i] - v) * t); return (x < 16 ? '0' : '') + x.toString(16); }).join('');
  }

  var G = '#c98f3c', GL = '#f3c46a', SH = '#1f3c5b';
  // 规范第 2 节东方色板；石色、砖色由色板两两混出
  var C = {
    wall: '#f1dcae', wallLt: '#fbf0d4', ochre: '#eeb24f', ochreLt: '#f8d78e', orange: '#e47c36', orangeLt: '#f3ae66',
    red: '#cd5030', redLt: '#e7864f', umber: '#8c3d22', umberLt: '#b5623a', teal: '#2e938d', tealLt: '#6cc1b3',
    navy: '#1f3c5b', navyLt: '#30697f', grey: '#5d6670', greyLt: '#7b8590',
    stone: '#cbbd9c', stoneDk: '#a8997a', stoneLt: '#e0d4b5', dark: '#4a2a1c', brick: '#a9533a',
    bronze: '#a8692c', pave: '#d6c8a4', smoke: '#e7e0cf', smokeLt: '#f8f3e6'
  };
  // 瓦色：fill 前坡、lite 受光侧坡、dark 背坡与侧影、line 瓦垄、ridge 屋脊与檐口
  var TILE = {
    grey:   { fill: '#7b8590', lite: '#9aa3ac', dark: '#5d6670', line: '#4c545d', ridge: '#3d454e' },
    teal:   { fill: '#2e938d', lite: '#6cc1b3', dark: '#21706b', line: '#195853', ridge: '#1f3c5b' },
    navy:   { fill: '#30697f', lite: '#4f8a9a', dark: '#1f3c5b', line: '#18304a', ridge: '#14283b' },
    gold:   { fill: '#eeb24f', lite: '#f8d78e', dark: '#c98a2e', line: '#b06c24', ridge: '#8c3d22' },
    thatch: { fill: '#d6ae62', lite: '#ebcb86', dark: '#b48c47', line: '#97713a', ridge: '#8c5a2a' }
  };

  function pts(a) { return 'M' + a.map(function (p) { return f(p[0]) + ' ' + f(p[1]); }).join('L') + 'Z'; }
  function P(d, fill, line, lw, extra) {
    return '<path d="' + d + '" fill="' + (fill || 'none') + '"' +
      (line ? ' stroke="' + line + '" stroke-width="' + f(lw || 1.2) + '" stroke-linejoin="round" stroke-linecap="round"' : '') + (extra || '') + '/>';
  }
  function R(x, y, w, h, fill, line, lw, extra) { return P('M' + f(x) + ' ' + f(y) + 'h' + f(w) + 'v' + f(h) + 'h' + f(-w) + 'Z', fill, line, lw, extra); }
  function E(cx, cy, rx, ry, fill, line, lw, extra) {
    return '<ellipse cx="' + f(cx) + '" cy="' + f(cy) + '" rx="' + f(rx) + '" ry="' + f(ry) + '" fill="' + (fill || 'none') + '"' +
      (line ? ' stroke="' + line + '" stroke-width="' + f(lw || 1) + '"' : '') + (extra || '') + '/>';
  }
  function L(d, line, lw, op) { return P(d, null, line, lw, op != null && op < 1 ? ' stroke-opacity="' + op + '"' : ''); }
  // 用圆头短线画一串点（门钉、瓦当）
  function dots(list, col, size) { return L(list.map(function (p) { return 'M' + f(p[0]) + ' ' + f(p[1]) + 'h0.01'; }).join(''), col, size || 1.2); }

  /** 投影：地面矩形右侧、前沿下方的一条暗色平涂（最多下伸 3 px）。先画，建筑盖住它。 */
  function shadow(x0, x1, yb, yf, s) {
    s = s || 8;
    return P(pts([[x1, yb + s * 0.5], [x1 + s, yb + s * 1.3], [x1 + s, yf + 3], [x0 + s, yf + 3], [x0 + s * 0.5, yf], [x1, yf]]), SH, null, 0, ' fill-opacity="0.2"');
  }
  /** 青石板地面（院落、铺前空地）。 */
  function pave(x0, y0, x1, y1, step, col) {
    step = step || 12;
    var s = R(x0, y0, x1 - x0, y1 - y0, col || C.pave), d = '', rh = step * 0.7, row = 0;
    for (var y = y0 + rh; y < y1 - 1; y += rh) d += 'M' + f(x0) + ' ' + f(y) + 'H' + f(x1);
    for (var y2 = y0; y2 < y1 - 1; y2 += rh, row++) {
      for (var x = x0 + (row % 2 ? step / 2 : step); x < x1 - 1; x += step) d += 'M' + f(x) + ' ' + f(y2) + 'V' + f(Math.min(y1, y2 + rh));
    }
    return s + L(d, C.stoneDk, 0.6, 0.55);
  }
  /** 一个立方体：顶面 + 正面。 */
  function box(x0, x1, yb, yf, h, top, front, line, lw) {
    return R(x0, yb - h, x1 - x0, yf - yb, top, line || G, lw || 1.1) + R(x0, yf - h, x1 - x0, h, front, line || G, lw || 1.1);
  }
  /** 台基：青石顶面 + 正面，正面中间一道石缝。 */
  function platform(x0, x1, yb, yf, p) {
    var s = R(x0, yb - p, x1 - x0, yf - yb, C.stoneLt, G, 1) + R(x0, yf - p, x1 - x0, p, C.stone, G, 1);
    if (p >= 5) s += L('M' + f(x0) + ' ' + f(yf - p / 2) + 'H' + f(x1), C.stoneDk, 0.6, 0.8);
    return s;
  }
  /** 台阶：y = 台基顶前沿，逐级向下加宽。 */
  function steps(cx, y, w, n, sh) {
    sh = sh || 2.2; var s = '';
    for (var i = 0; i < n; i++) s += R(cx - w / 2 - i, y + i * sh, w + 2 * i, sh + 0.2, i % 2 ? C.stone : C.stoneLt, G, 0.6);
    return s;
  }
  /** 砖缝：在矩形里画错缝砖纹。 */
  function bricks(x0, y0, x1, y1, col, bw, bh) {
    bw = bw || 7; bh = bh || 3.5; var d = '', row = 0;
    for (var y = y0 + bh; y < y1 - 0.5; y += bh) d += 'M' + f(x0) + ' ' + f(y) + 'H' + f(x1);
    for (var y2 = y0; y2 < y1 - 0.5; y2 += bh, row++)
      for (var x = x0 + (row % 2 ? bw / 2 : bw); x < x1 - 0.5; x += bw) d += 'M' + f(x) + ' ' + f(y2) + 'V' + f(Math.min(y1, y2 + bh));
    return L(d, col || C.dark, 0.5, 0.45);
  }

  /** 水平扫描线与多边形的交点范围 [xmin, xmax]（无交点返回 null）。 */
  function scan(poly, y) {
    var xs = [];
    for (var i = 0; i < poly.length; i++) {
      var a = poly[i], b = poly[(i + 1) % poly.length];
      if ((a[1] - y) * (b[1] - y) <= 0 && a[1] !== b[1]) xs.push(a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]));
    }
    if (xs.length < 2) return null;
    return [Math.min.apply(null, xs), Math.max.apply(null, xs)];
  }

  /**
   * 屋顶。地面矩形 x0..x1 × yb..yf，墙高 h（墙顶屏幕 y = 地面 y − h）。
   * o.type：hip（庑殿/歇山，o.hipK 控制正脊缩进）、gable（硬山/悬山，正脊通长）、spire（攒尖，正脊缩成一点）
   * o.hr 屋脊高出墙顶；o.ov 出檐；o.up 檐角起翘；o.tile 瓦色；o.ridge：chiwen（鸱吻）/ swallow（燕尾）/ plain
   * 返回 { svg, eave: 前檐中点 y, ridgeY, rL, rR }
   */
  function roof(x0, x1, yb, yf, h, o) {
    o = o || {};
    var T = o.tile || TILE.grey, ov = o.ov != null ? o.ov : 5, up = (o.up != null ? o.up : 5) + 2.5, hr = o.hr != null ? o.hr : 14;
    var type = o.type || 'hip', cx = (x0 + x1) / 2;
    var XL = x0 - ov, XR = x1 + ov, Ef = yf - h + ov * 0.6, Eb = yb - h - ov * 0.4, Ry = (yb + yf) / 2 - h - hr;
    var half = (x1 - x0) / 2, inset;
    if (type === 'gable') inset = -ov;
    else if (type === 'spire') inset = half;
    else inset = Math.min(half - 2, (yf - yb) * 0.5 * (o.hipK != null ? o.hipK : 0.8) + ov * 0.5);
    if (o.inset != null && type !== 'gable') inset = Math.min(half - 1, o.inset);
    var rL = x0 + inset, rR = x1 - inset, Ec = Ef - up;
    var halfW = (XR - XL) / 2;
    function eave(x) { var t = Math.min(1, Math.abs(x - cx) / halfW); return Ef - up * Math.pow(t, 2.2); }
    var eavePts = [];
    for (var i = 0; i <= 24; i++) { var x = XL + (XR - XL) * i / 24; eavePts.push([x, eave(x)]); }
    var s = '';
    // 背坡与侧坡（noBack：重檐的下檐只画前坡与侧坡）
    if (!o.noBack) s += P(pts([[XL, Ec], [XL + 2, Eb], [XR - 2, Eb], [XR, Ec], [rR, Ry], [rL, Ry]]), T.dark, G, 1);
    var front = [[rL, Ry]].concat(eavePts).concat([[rR, Ry]]);
    if (type !== 'gable') {
      var lh = [[XL, Ec], [XL + 2, Eb], [rL, Ry]], rh = [[XR, Ec], [XR - 2, Eb], [rR, Ry]];
      s += P(pts(lh), T.lite, G, 1) + P(pts(rh), T.dark, G, 1);
      var dl = '';
      for (var yy = Math.min(Eb, Ry) + 2.5; yy < Ec - 1; yy += 3.2) {
        var a = scan(lh, yy); if (a && a[1] - a[0] > 2) dl += 'M' + f(a[0] + 0.8) + ' ' + f(yy) + 'H' + f(a[1] - 0.8);
        var b = scan(rh, yy); if (b && b[1] - b[0] > 2) dl += 'M' + f(b[0] + 0.8) + ' ' + f(yy) + 'H' + f(b[1] - 0.8);
      }
      s += L(dl, T.line, 0.7, 0.7);
    }
    s += P(pts(front), T.fill, G, 1.2);
    // 前坡瓦垄：竖线从屋脊（或垂脊）到檐口
    var d = '', sp = o.sp || 3.4;
    for (var xx = XL + sp; xx < XR - sp * 0.5; xx += sp) {
      var top = xx < rL ? Ec + (Ry - Ec) * (xx - XL) / Math.max(1, rL - XL) : xx > rR ? Ec + (Ry - Ec) * (XR - xx) / Math.max(1, XR - rR) : Ry;
      var bot = eave(xx) - 1.2;
      if (bot - top > 1.5) d += 'M' + f(xx) + ' ' + f(top + 1.2) + 'V' + f(bot);
    }
    s += L(d, T.line, 0.75, 0.75);
    // 反宇：屋面下段（檐口一带）平缓，压一道深一档的叠晕带
    var band = [];
    for (var bi = 0; bi <= 24; bi++) band.push([eavePts[bi][0], eavePts[bi][1] - Math.min(7, (Ef - Ry) * 0.22)]);
    s += P(pts(band.concat(eavePts.slice().reverse())), T.dark, null, 0, ' fill-opacity="0.35"');
    // 檐口：深色檐板 + 金线；叠晕一道浅色
    var ed = 'M' + eavePts.map(function (p) { return f(p[0]) + ' ' + f(p[1]); }).join('L');
    var ed2 = 'M' + eavePts.map(function (p) { return f(p[0]) + ' ' + f(p[1] - 2.4); }).join('L');
    s += L(ed, T.ridge, 3.2) + L(ed2, T.lite, 1, 0.9) + L(ed, GL, 0.8);
    // 瓦当：檐口一排小圆头
    var wd = [];
    for (var wx = XL + sp * 0.5; wx < XR; wx += sp) wd.push([wx, eave(wx) + 0.4]);
    s += dots(wd, T.lite, 1.5);
    // 垂脊
    if (type !== 'gable') {
      var hd = 'M' + f(rL) + ' ' + f(Ry) + 'L' + f(XL) + ' ' + f(Ec) + 'M' + f(rR) + ' ' + f(Ry) + 'L' + f(XR) + ' ' + f(Ec);
      s += L(hd, T.ridge, 2.4) + L(hd, GL, 0.7, 0.8);
    }
    // 檐角起翘的尖
    var tip = up * 0.6 + 2;
    s += P('M' + f(XL + 3) + ' ' + f(Ec + 1) + 'Q' + f(XL - 1) + ' ' + f(Ec) + ' ' + f(XL - 3) + ' ' + f(Ec - tip) + 'Q' + f(XL) + ' ' + f(Ec - 1) + ' ' + f(XL + 3) + ' ' + f(Ec - 1.5) + 'Z', T.ridge, GL, 0.6);
    s += P('M' + f(XR - 3) + ' ' + f(Ec + 1) + 'Q' + f(XR + 1) + ' ' + f(Ec) + ' ' + f(XR + 3) + ' ' + f(Ec - tip) + 'Q' + f(XR) + ' ' + f(Ec - 1) + ' ' + f(XR - 3) + ' ' + f(Ec - 1.5) + 'Z', T.ridge, GL, 0.6);
    // 正脊
    if (o.noBack) {
      s += L('M' + f(rL) + ' ' + f(Ry) + 'H' + f(rR), T.ridge, 1.6);
    } else if (type === 'spire') {
      var fh = o.finial != null ? o.finial : 7;
      s += L('M' + f(cx) + ' ' + f(Ry + 1) + 'V' + f(Ry - fh), T.ridge, 1.4) +
        E(cx, Ry - fh * 0.45, 2.2, 2, C.ochre, G, 0.7) + E(cx, Ry - fh, 1.5, 1.6, C.ochre, G, 0.7);
    } else {
      var kind = o.ridge || 'chiwen', rh2 = o.ridgeH || 3;
      s += R(rL - 1, Ry - rh2, rR - rL + 2, rh2 + 0.8, T.ridge, GL, 0.7);
      if (kind === 'chiwen') {
        [[rL, -1], [rR, 1]].forEach(function (e) {
          var x = e[0], k = e[1];
          s += P('M' + f(x - k * 1) + ' ' + f(Ry + 0.5) + 'L' + f(x + k * 2) + ' ' + f(Ry - rh2 - 6) + 'Q' + f(x + k * 4.5) + ' ' + f(Ry - rh2 - 6) +
            ' ' + f(x + k * 3.5) + ' ' + f(Ry - rh2 - 3) + 'Q' + f(x + k * 2.5) + ' ' + f(Ry - rh2 - 1) + ' ' + f(x - k * 3) + ' ' + f(Ry - rh2) + 'Z', T.ridge, GL, 0.7);
        });
      } else if (kind === 'swallow') {
        [[rL, -1], [rR, 1]].forEach(function (e) {
          var x = e[0], k = e[1];
          s += P('M' + f(x - k * 4) + ' ' + f(Ry - rh2) + 'Q' + f(x + k * 3) + ' ' + f(Ry - rh2) + ' ' + f(x + k * 6) + ' ' + f(Ry - rh2 - 6) +
            'Q' + f(x + k * 4) + ' ' + f(Ry - 0.5) + ' ' + f(x - k * 4) + ' ' + f(Ry + 0.8) + 'Z', T.ridge, GL, 0.7);
        });
      }
      if (o.pearl) s += E(cx, Ry - rh2 - 2.2, 2.4, 2.4, C.ochre, G, 0.8) + L('M' + f(cx - 6) + ' ' + f(Ry - rh2 - 0.5) + 'Q' + f(cx - 3) + ' ' + f(Ry - rh2 - 3) + ' ' + f(cx - 2.6) + ' ' + f(Ry - rh2 - 1) + 'M' + f(cx + 6) + ' ' + f(Ry - rh2 - 0.5) + 'Q' + f(cx + 3) + ' ' + f(Ry - rh2 - 3) + ' ' + f(cx + 2.6) + ' ' + f(Ry - rh2 - 1), GL, 0.9);
    }
    return { svg: s, eave: Ef, ridgeY: Ry, rL: rL, rR: rR, XL: XL, XR: XR };
  }

  /** 格扇窗：外框 + 斜方格（或直棂）。 */
  function lattice(x, y, w, h, o) {
    o = o || {};
    var s = R(x, y, w, h, o.bg || C.umber, o.line || GL, 0.8), d = '', st = o.step || 3.2;
    if (o.straight) { for (var xx = x + st; xx < x + w - 0.5; xx += st) d += 'M' + f(xx) + ' ' + f(y + 0.6) + 'V' + f(y + h - 0.6); }
    else {
      for (var k = -h; k < w; k += st) {
        var a0 = Math.max(0, k), a1 = Math.min(w, k + h);
        if (a1 > a0) d += 'M' + f(x + a0) + ' ' + f(y + a0 - k) + 'L' + f(x + a1) + ' ' + f(y + a1 - k);
        var b0 = Math.max(0, k), b1 = Math.min(w, k + h);
        if (b1 > b0) d += 'M' + f(x + b0) + ' ' + f(y + h - (b0 - k)) + 'L' + f(x + b1) + ' ' + f(y + h - (b1 - k));
      }
    }
    return s + L(d, o.fg || C.ochreLt, 0.6, 0.85);
  }
  /** 双扇板门：朱门、门钉、门环。open=true 时画成敞开的黑洞口。 */
  function door(x, y, w, h, o) {
    o = o || {};
    if (o.open) return R(x, y, w, h, C.dark, GL, 0.9) + R(x + 1.2, y + h * 0.55, w - 2.4, h * 0.45, '#5c3624');
    var s = R(x, y, w, h, o.col || C.red, GL, 0.9) + L('M' + f(x + w / 2) + ' ' + f(y) + 'V' + f(y + h), GL, 0.7);
    if (o.studs !== false && w > 7) {
      var list = [];
      for (var r = 0; r < 4; r++) for (var c = 0; c < 2; c++) {
        list.push([x + w * (0.16 + c * 0.2), y + h * (0.2 + r * 0.18)]);
        list.push([x + w * (0.64 + c * 0.2), y + h * (0.2 + r * 0.18)]);
      }
      s += dots(list, C.ochre, 1.1);
    }
    s += E(x + w / 2 - 1.6, y + h * 0.52, 0.9, 0.9, null, C.ochre, 0.6) + E(x + w / 2 + 1.6, y + h * 0.52, 0.9, 0.9, null, C.ochre, 0.6);
    return s;
  }
  /**
   * 正立面：墙体从 yf−h 到 yf，x0..x1；o.bays 开间数；o.doors 哪几间开门（0 起）；
   * o.open 敞门；o.col 柱色；o.wall 墙色；o.win 窗类型 lattice/straight/none；o.sill 槛墙比例
   */
  function facade(x0, x1, yf, h, o) {
    o = o || {};
    var n = o.bays || 3, bw = (x1 - x0) / n, top = yf - h, s = '';
    s += R(x0, top, x1 - x0, h, o.wall || C.wall, G, 1.1);
    s += R(x0, yf - 3, x1 - x0, 3, C.stone, G, 0.7); // 墙裙石
    var doors = o.doors || [Math.floor(n / 2)];
    for (var i = 0; i < n; i++) {
      var bx = x0 + i * bw, inner = bw - 3;
      if (doors.indexOf(i) >= 0) {
        var dw = Math.min(inner - 1, o.doorW || inner * 0.8), dh = Math.min(h - 6, o.doorH || h * 0.72);
        s += door(bx + (bw - dw) / 2, yf - 3 - dh, dw, dh, { open: o.open, col: o.doorCol });
      } else if (o.win !== 'none') {
        var ww = inner * 0.72, wh = Math.min(h * 0.42, 14), wy = top + h * 0.22;
        s += lattice(bx + (bw - ww) / 2, wy, ww, wh, { straight: o.win === 'straight' });
        if (o.sill !== false) s += R(bx + (bw - ww) / 2, wy + wh + 1, ww, Math.max(2, yf - 4 - wy - wh - 1), o.sillCol || C.wallLt, G, 0.5);
      }
    }
    // 檐柱
    var cw = o.colW || 2.6;
    for (var j = 0; j <= n; j++) {
      var cx = x0 + j * bw;
      s += R(cx - cw / 2, top, cw, h - 3, o.col || C.red, GL, 0.6);
    }
    // 额枋：一道青绿彩画梁
    s += R(x0, top, x1 - x0, 3, o.beam || C.teal, GL, 0.6);
    return s;
  }
  /** 匾额：深底金框，几道短横竖暗示题字（不写真字）。 */
  function plaque(cx, cy, w, h, o) {
    o = o || {};
    var s = R(cx - w / 2 - 1, cy - h / 2 - 1, w + 2, h + 2, GL) + R(cx - w / 2, cy - h / 2, w, h, o.bg || C.navy, G, 0.6);
    var n = o.chars || 3, d = '', gw = (w - 4) / n;
    for (var i = 0; i < n; i++) {
      var gx = cx - w / 2 + 2 + gw * (i + 0.5), g = h * 0.28;
      d += 'M' + f(gx - g) + ' ' + f(cy - g * 0.6) + 'H' + f(gx + g) + 'M' + f(gx) + ' ' + f(cy - g) + 'V' + f(cy + g) + 'M' + f(gx - g * 0.8) + ' ' + f(cy + g * 0.5) + 'H' + f(gx + g * 0.8);
    }
    return s + L(d, o.ink || GL, 0.8);
  }
  /** 红灯笼：(x, y) = 挂绳顶点。 */
  function lantern(x, y, r, col) {
    r = r || 3; col = col || C.red;
    return L('M' + f(x) + ' ' + f(y) + 'V' + f(y + 2), C.dark, 0.6) +
      R(x - r * 0.55, y + 2, r * 1.1, 1.2, C.ochre) + E(x, y + 3.2 + r * 1.1, r, r * 1.15, col, GL, 0.6) +
      L('M' + f(x) + ' ' + f(y + 3.4) + 'V' + f(y + 3 + r * 2.2), C.redLt, 0.5, 0.8) +
      R(x - r * 0.55, y + 3 + r * 2.2, r * 1.1, 1.2, C.ochre) + L('M' + f(x) + ' ' + f(y + 4.4 + r * 2.2) + 'v' + f(r * 0.9), C.ochre, 0.7);
  }
  /** 幌子 / 酒旗：竖挂的布幡，下沿锯齿，可选中央一个圆标记。 */
  function banner(x, y, w, h, o) {
    o = o || {};
    var col = o.col || C.navy, z = Math.max(2, w / 3);
    var d = 'M' + f(x) + ' ' + f(y) + 'H' + f(x + w) + 'V' + f(y + h);
    for (var i = 3; i >= 0; i--) d += 'L' + f(x + w * i / 3 + (i % 2 ? 0 : 0)) + ' ' + f(y + h - (i % 2 ? z : 0));
    d += 'Z';
    var s = R(x - 1.5, y - 1, w + 3, 1.6, C.umber) + P(d, col, GL, 0.7);
    if (o.mark === 'circle') s += E(x + w / 2, y + h * 0.4, w * 0.3, w * 0.3, C.wallLt, GL, 0.5) + L('M' + f(x + w / 2) + ' ' + f(y + h * 0.4 - w * 0.18) + 'v' + f(w * 0.36), C.red, 0.9);
    else if (o.mark) s += L('M' + f(x + w * 0.25) + ' ' + f(y + h * 0.25) + 'H' + f(x + w * 0.75) + 'M' + f(x + w / 2) + ' ' + f(y + h * 0.15) + 'V' + f(y + h * 0.62) + 'M' + f(x + w * 0.28) + ' ' + f(y + h * 0.48) + 'H' + f(x + w * 0.72), o.ink || GL, 0.8);
    return s;
  }
  /** 栏杆：望柱 + 寻杖。 */
  function railing(x0, x1, y, h, col) {
    col = col || C.red; var d = 'M' + f(x0) + ' ' + f(y - h) + 'H' + f(x1) + 'M' + f(x0) + ' ' + f(y - h * 0.4) + 'H' + f(x1);
    for (var x = x0; x <= x1 + 0.1; x += 4) d += 'M' + f(x) + ' ' + f(y) + 'V' + f(y - h - 0.6);
    return L(d, G, 2.2) + L(d, col, 1.1);
  }

  /** 院墙：白墙 + 灰瓦墙帽；y = 墙脚（地面）屏幕 y，h 墙高，t 墙顶厚（斜俯视看到的顶面）。 */
  function yardWall(x0, x1, y, h, o) {
    o = o || {};
    var t = o.t || 3, T = o.tile || TILE.grey, s = '';
    s += R(x0, y - h, x1 - x0, h, o.col || C.wallLt, G, 0.9);
    s += R(x0, y - 2.5, x1 - x0, 2.5, C.stone, G, 0.5);
    s += R(x0 - 1, y - h - t, x1 - x0 + 2, t + 1.4, T.fill, G, 0.8);
    var d = '';
    for (var x = x0 + 1.6; x < x1; x += 2.6) d += 'M' + f(x) + ' ' + f(y - h - t + 0.6) + 'V' + f(y - h + 0.8);
    return s + L(d, T.line, 0.6, 0.8) + L('M' + f(x0 - 1) + ' ' + f(y - h + 1.4) + 'H' + f(x1 + 1), T.ridge, 1.2);
  }
  /** 侧院墙：纵向的一段，只露墙顶一条（左右两侧用）。 */
  function sideWall(x, y0, y1, h, o) {
    o = o || {};
    var T = o.tile || TILE.grey, w = o.t || 3.4;
    return R(x - w / 2, y1 - h, w, h, o.col || C.wallLt, G, 0.6) +
      R(x - w / 2, y0 - h, w, y1 - y0, T.fill, G, 0.8) + L('M' + f(x) + ' ' + f(y0 - h + 0.6) + 'V' + f(y1 - h - 0.6), T.ridge, 0.9);
  }
  /**
   * 一座殿堂：立面 + 屋顶。o.h 墙高；o.fac 传给 facade；o.roof 传给 roof。
   * o.double = 重檐：下层墙高 h1，下檐一圈，上层退进 o.inset，墙高 o.h2，再盖上檐。
   * 返回 { svg, roof }（roof = 最上层屋顶的 roof() 结果）。
   */
  function hall(x0, x1, yb, yf, o) {
    o = o || {};
    var h = o.h || 28, ro = o.roof || {}, s = '', r;
    if (!o.double) {
      s += facade(x0, x1, yf, h, o.fac || {});
      r = roof(x0, x1, yb, yf, h, ro);
      return { svg: s + r.svg, roof: r };
    }
    var h1 = o.h1 || Math.round(h * 0.6), h2 = o.h2 || Math.round(h * 0.5), ins = o.inset || 8;
    var ub = yb + 3, uf = yf - 5;
    s += facade(x0, x1, yf, h1, o.fac || {});
    var uo = o.upFac || { bays: o.fac && o.fac.bays || 3, doors: [], win: 'lattice', sill: false, col: (o.fac || {}).col, beam: (o.fac || {}).beam };
    s += facade(x0 + ins, x1 - ins, uf - h1, h2 + 2, uo);
    // 下檐：一道腰檐带，屋脊线压在上层墙脚上方 2 px（把地面后沿伪造成 yf − 14 + 2·sk，使 Ry = yf − 7 − h1）
    var sk = o.skirt || 7;
    s += roof(x0, x1, yf - 14 + 2 * sk, yf, h1, { type: 'hip', tile: ro.tile, ov: (ro.ov || 5) + 1, up: ro.up != null ? ro.up : 5, hr: sk, inset: ins + 2, noBack: true }).svg;
    r = roof(x0 + ins, x1 - ins, ub, uf, h1 + h2, ro);
    return { svg: s + r.svg, roof: r };
  }
  /** 一棵树：几枚圆冠金线勾边并集 + 叠晕一圈，树干在下。(cx, cy) = 树根。 */
  function tree(cx, cy, r, seed, o) {
    o = o || {};
    var rr = rng(seed || 1), col = o.col || C.teal, lite = o.lite || C.tealLt, Cs = [];
    var n = o.n || 5;
    for (var i = 0; i < n; i++) {
      var a = i / n * Math.PI * 2 + rr() * 0.6;
      Cs.push([cx + Math.cos(a) * r * 0.55, cy - r * 1.55 + Math.sin(a) * r * 0.4, r * (0.5 + rr() * 0.2)]);
    }
    Cs.push([cx, cy - r * 1.7, r * 0.62]);
    function disc(k, pad, fill, dy) {
      return '<g fill="' + fill + '">' + Cs.map(function (c) { return '<circle cx="' + f(c[0]) + '" cy="' + f(c[1] + dy) + '" r="' + f(Math.max(0.5, c[2] * k + pad)) + '"/>'; }).join('') + '</g>';
    }
    return E(cx + r * 0.5, cy + 0.5, r * 0.9, r * 0.28, SH, null, 0, ' fill-opacity="0.2"') +
      R(cx - 1.4, cy - r * 1.1, 2.8, r * 1.1, C.umber, GL, 0.5) +
      disc(1, 1.3, G, 0) + disc(1, 0, col, 0) + disc(0.6, 0, lite, -r * 0.18);
  }
  /** 炊烟 / 炉烟：一串由小到大、向右上飘的云头。 */
  function smoke(x, y, s, seed) {
    var rr = rng(seed || 7), o = '';
    for (var i = 0; i < 4; i++) {
      var cx = x + i * s * 0.55 + rr() * s * 0.2, cy = y - i * s * 0.9, r = s * (0.32 + i * 0.12);
      o += E(cx, cy, r + 0.9, r * 0.85 + 0.9, G) + E(cx, cy, r, r * 0.85, C.smoke) + E(cx - r * 0.2, cy - r * 0.2, r * 0.55, r * 0.45, C.smokeLt);
    }
    return '<g opacity="0.92">' + o + '</g>';
  }
  /** 火苗：三瓣叠晕火焰。(x, y) = 火根。 */
  function fire(x, y, s) {
    function lobe(k, col) {
      return P('M' + f(x - s * 0.9 * k) + ' ' + f(y) + 'Q' + f(x - s * 0.9 * k) + ' ' + f(y - s * 0.9 * k) + ' ' + f(x - s * 0.2 * k) + ' ' + f(y - s * 1.6 * k) +
        'Q' + f(x - s * 0.05) + ' ' + f(y - s * 0.9 * k) + ' ' + f(x + s * 0.25 * k) + ' ' + f(y - s * 1.9 * k) +
        'Q' + f(x + s * 0.95 * k) + ' ' + f(y - s * 0.9 * k) + ' ' + f(x + s * 0.9 * k) + ' ' + f(y) + 'Z', col, k === 1 ? GL : null, 0.6);
    }
    return lobe(1, C.red) + lobe(0.68, C.orange) + lobe(0.38, C.ochreLt);
  }
  /** 箩筐：编竹的圆筐，满筐时顶上一堆货（菜、果、谷）。 */
  function basket(cx, cy, r, fill) {
    var s = E(cx + 1.5, cy + 0.6, r * 1.05, r * 0.35, SH, null, 0, ' fill-opacity="0.2"');
    s += P('M' + f(cx - r) + ' ' + f(cy - r * 0.9) + 'L' + f(cx - r * 0.8) + ' ' + f(cy) + 'Q' + f(cx) + ' ' + f(cy + r * 0.3) + ' ' + f(cx + r * 0.8) + ' ' + f(cy) + 'L' + f(cx + r) + ' ' + f(cy - r * 0.9) + 'Z', C.ochre, G, 0.7);
    s += L('M' + f(cx - r * 0.9) + ' ' + f(cy - r * 0.45) + 'Q' + f(cx) + ' ' + f(cy - r * 0.2) + ' ' + f(cx + r * 0.9) + ' ' + f(cy - r * 0.45), C.umberLt, 0.6, 0.8);
    s += E(cx, cy - r * 0.9, r, r * 0.38, C.umberLt, G, 0.7);
    if (fill) {
      var a = typeof fill === 'string' ? [fill] : fill;
      for (var i = 0; i < 5; i++) {
        var px = cx + (i - 2) * r * 0.36, py = cy - r * 1.05 - (i % 2 ? r * 0.25 : 0);
        s += E(px, py, r * 0.32, r * 0.26, a[i % a.length], G, 0.4);
      }
    }
    return s;
  }
  /** 一个酒坛 / 水缸。 */
  function jar(cx, cy, r, col) {
    col = col || C.umberLt;
    return E(cx + 1.2, cy + 0.4, r, r * 0.3, SH, null, 0, ' fill-opacity="0.2"') +
      P('M' + f(cx - r * 0.5) + ' ' + f(cy) + 'Q' + f(cx - r * 1.15) + ' ' + f(cy - r * 0.9) + ' ' + f(cx - r * 0.55) + ' ' + f(cy - r * 1.6) + 'H' + f(cx + r * 0.55) +
        'Q' + f(cx + r * 1.15) + ' ' + f(cy - r * 0.9) + ' ' + f(cx + r * 0.5) + ' ' + f(cy) + 'Z', col, G, 0.7) +
      E(cx, cy - r * 1.6, r * 0.55, r * 0.2, C.dark, G, 0.5) + L('M' + f(cx - r * 0.8) + ' ' + f(cy - r * 0.95) + 'Q' + f(cx) + ' ' + f(cy - r * 0.75) + ' ' + f(cx + r * 0.8) + ' ' + f(cy - r * 0.95), GL, 0.5, 0.8);
  }

  /**
   * 敞亭 / 棚子：四柱 + 屋顶，无墙。inner = 棚下的内容（在前柱和屋顶之前画）。返回 roof() 的结果，svg 是整体。
   */
  function pavilion(x0, x1, yb, yf, h, o, inner) {
    o = o || {};
    var pc = o.post || C.red, pw = o.pw || 2.6, dk = mix(pc, '#000000', 0.25), s = '';
    s += R(x0 + 1, yb - h + 2, pw, h - 2, dk, GL, 0.5) + R(x1 - 1 - pw, yb - h + 2, pw, h - 2, dk, GL, 0.5);
    s += inner || '';
    s += R(x0 + 0.5, yf - h, pw, h, pc, GL, 0.6) + R(x1 - 0.5 - pw, yf - h, pw, h, pc, GL, 0.6);
    var r = roof(x0, x1, yb, yf, h, o.roof || {});
    r.svg = s + r.svg;
    return r;
  }

  /**
   * 生成一个 symbol。def：{ kind, variant, fp:[w,d], up, draw(K, W, U, D) }；draw 在 viewBox 坐标里画，
   * 占地矩形 x 0..W、y U..U+D。返回 { id, viewBox, anchor, body }。
   */
  function symbolOf(def, style, race) {
    var W = def.fp[0] * CELL, D = def.fp[1] * CELL, U = def.up, H = D + U;
    var id = style + '-' + race + '-' + def.kind.replace(/_/g, '-') + '-' + (def.variant < 10 ? '0' : '') + def.variant;
    return { id: id, W: W, H: H, U: U, D: D, viewBox: [0, 0, W, H], anchor: [W / 2, H], body: def.draw(API, W, U, D, id) };
  }

  var API = {
    CELL: CELL, C: C, TILE: TILE, G: G, GL: GL, SH: SH,
    rng: rng, hash: hash, f: f, mix: mix, pts: pts, P: P, R: R, E: E, L: L, dots: dots,
    shadow: shadow, pavilion: pavilion, pave: pave, box: box, platform: platform, steps: steps, bricks: bricks, scan: scan, roof: roof,
    lattice: lattice, door: door, facade: facade, plaque: plaque, lantern: lantern, banner: banner, railing: railing,
    yardWall: yardWall, sideWall: sideWall, hall: hall, tree: tree, smoke: smoke, fire: fire, basket: basket, jar: jar, symbolOf: symbolOf
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.TownArtEastLandmarkCore = API;
})(typeof window !== 'undefined' ? window : this);
