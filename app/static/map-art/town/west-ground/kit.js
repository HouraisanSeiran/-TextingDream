/*
 * 织梦 · 西式地面摆件的小零件：圆柱（桶、树桩）、方箱、地面投影、木板纹（美术样板，尚未接入游戏）
 * 摆件局部坐标：x 0..48；y = 0 是脚底（= 占地前沿 = 锚点所在高度），向上为负。
 * 浏览器挂 window.TownArtWG_kit；Node 用 module.exports。依赖 core.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWG_core;
  var P = C.P, f = C.f;

  /** 地面投影：偏右下的扁椭圆，最低点不超过 yb + 4（规范：投影最多下伸 6 px） */
  function gshadow(cx, yb, rx, ry) {
    ry = Math.min(ry, 4);
    return C.ell(cx + rx * 0.22, yb - ry * 0.1, rx, ry, P.shadow, 0, 0.18);
  }
  /** 竖放圆柱：侧面 side、顶面 top；右侧压一条暗面 */
  function cyl(cx, yb, rx, ry, h, side, top, sw) {
    sw = sw == null ? 1.2 : sw;
    var d = 'M' + f(cx - rx) + ' ' + f(yb - h) + 'L' + f(cx - rx) + ' ' + f(yb) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + rx) + ' ' + f(yb) +
      'L' + f(cx + rx) + ' ' + f(yb - h) + 'Z';
    var x1 = cx + rx * 0.45, y1 = yb + ry * 0.893;
    var dark = 'M' + f(x1) + ' ' + f(yb - h) + 'L' + f(x1) + ' ' + f(y1) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + rx) + ' ' + f(yb) +
      'L' + f(cx + rx) + ' ' + f(yb - h) + 'Z';
    return C.path(d, side, sw) + C.path(dark, P.shadow, 0, 0.16) + C.ell(cx, yb - h, rx, ry, top || side, sw);
  }
  /** 木桶：圆柱 + 两道铁箍 + 桶板缝 */
  function barrel(cx, yb, rx, h, top) {
    var ry = rx * 0.42, o = cyl(cx, yb, rx, ry, h, P.wood, top || P.timber, 1.2), hoop = '';
    [0.22, 0.78].forEach(function (t) {
      var y = yb - h * t;
      hoop += 'M' + f(cx - rx) + ' ' + f(y) + 'A' + f(rx) + ' ' + f(ry) + ' 0 0 0 ' + f(cx + rx) + ' ' + f(y);
    });
    var st = '';
    [-0.5, 0, 0.5].forEach(function (k) { st += C.seg(cx + rx * k, yb - h + ry * 0.9, cx + rx * k, yb + ry * 0.85 * Math.sqrt(1 - k * k) - 0.6); });
    return o + C.line(st, 0.7, 0.4) + C.line(hoop, 1.3, 0.9, P.iron) +
      (top ? '' : C.ell(cx, yb - h, rx * 0.7, ry * 0.7, 'none', 0.6).replace('/>', ' stroke-opacity="0.5"/>'));
  }
  /** 方箱：正面 x0..x1 × (yb-h..yb)，顶面向后 dep 像素 */
  function box(x0, x1, yb, dep, h, front, top, sw) {
    sw = sw == null ? 1.2 : sw;
    return C.rect(x0, yb - h - dep, x1 - x0, dep, top || P.paper, sw) + C.rect(x0, yb - h, x1 - x0, h, front || P.wood, sw);
  }
  /** 木箱：方箱 + 板缝 + 斜撑 */
  function crate(x0, yb, s, dep) {
    dep = dep == null ? s * 0.45 : dep;
    var x1 = x0 + s, yt = yb - s * 0.8, o = box(x0, x1, yb, dep, s * 0.8, P.wood, '#d8b77c', 1.2);
    o += C.line(C.seg(x0 + 1.6, yb - 1.6, x1 - 1.6, yt + 1.6) + C.seg(x0, yt + 2, x1, yt + 2) + C.seg(x0, yb - 2, x1, yb - 2), 0.8, 0.55);
    o += C.line(C.seg(x0 + s * 0.33, yt - dep, x0 + s * 0.33, yt) + C.seg(x0 + s * 0.66, yt - dep, x0 + s * 0.66, yt), 0.7, 0.4);
    return o;
  }
  /** 横放圆木截面一堆 */
  function logs(x, yb, n, rows, r) {
    var o = '';
    for (var j = 0; j < rows; j++) for (var i = 0; i < n - j; i++) {
      var cx = x + i * r * 2 + j * r + r, cy = yb - r - j * r * 1.7;
      o += C.ell(cx, cy, r, r, P.wood, 0.9) + C.ell(cx, cy, r * 0.55, r * 0.55, 'none', 0.6).replace('/>', ' stroke-opacity="0.5"/>') +
        C.ell(cx, cy, r * 0.18, r * 0.18, P.timber, 0);
    }
    return o;
  }
  /** 一根立柱（木桩）：正面 + 顶面 */
  function post(x, yb, w, h, fill, top) {
    return C.rect(x - w / 2, yb - h, w, h, fill || P.timber, 1) + C.ell(x, yb - h, w / 2, w * 0.28, top || P.wood, 0.8);
  }
  /** 平涂叶团：底色 + 右下暗面月牙 + 左上亮斑 + 轮廓；返回 [svg, d] */
  function foliage(ctx, cx, cy, rx, ry, n, base, dark, light, sw) {
    var d = C.blob(ctx, cx, cy, rx, ry, n, 0.18);
    var inner = C.rect(cx - rx * 2, cy - ry * 2, rx * 4, ry * 4, dark, 0) +
      '<path d="' + d + '" transform="translate(' + f(-rx * 0.22) + ' ' + f(-ry * 0.26) + ')" fill="' + base + '"/>' +
      C.path(C.blob(ctx, cx - rx * 0.32, cy - ry * 0.34, rx * 0.42, ry * 0.36, 5, 0.2), light, 0);
    var hatch = '';
    for (var i = 0; i < 3; i++) {
      var a = 0.25 + i * 0.32, hx = cx + Math.cos(a) * rx * 0.62, hy = cy + Math.sin(a) * ry * 0.62;
      hatch += 'M' + f(hx - 2) + ' ' + f(hy) + 'q2 -1.6 4 0';
    }
    return [C.clip(ctx, d, 'nonzero', inner + C.line(hatch, 0.8, 0.45)) + C.path(d, 'none', sw == null ? 1.4 : sw), d];
  }
  /** 石块：顶面浅、正面深的多边形 */
  function rock(ctx, cx, yb, w, h, fills) {
    fills = fills || [P.stone, P.stone3];
    var j = function (a) { return ctx.rnd(-a, a); };
    var L = cx - w / 2, R = cx + w / 2, yt = yb - h, ym = yb - h * 0.45;
    var outer = C.poly([[L + j(1), yb - 1], [L - 1 + j(0.8), ym], [L + w * 0.2 + j(1), yt + j(1)], [R - w * 0.3 + j(1), yt - 1 + j(1)],
      [R + 0.5 + j(0.6), ym - 1], [R - 1 + j(1), yb - 0.5], [cx + j(2), yb + 0.6]]);
    var top = C.poly([[L - 0.6, ym], [L + w * 0.2, yt], [R - w * 0.3, yt - 1], [R + 0.4, ym - 1], [cx + w * 0.1, ym + h * 0.12]]);
    var id = ctx.uid();
    return gshadow(cx + 2, yb, w * 0.55, 3) + C.path(outer, fills[1], 0) +
      '<defs><clipPath id="' + id + '"><path d="' + outer + '"/></clipPath></defs><g clip-path="url(#' + id + ')">' +
      C.path(top, fills[0], 0) + C.line('M' + f(cx - w * 0.1) + ' ' + f(ym + 1) + 'l' + f(w * 0.12) + ' ' + f(h * 0.3), 0.7, 0.5) + '</g>' +
      C.path(outer, 'none', 1.3);
  }

  var api = { gshadow: gshadow, cyl: cyl, barrel: barrel, box: box, crate: crate, logs: logs, post: post, foliage: foliage, rock: rock };
  root.TownArtWG_kit = api;
  if (isNode) module.exports = api;
})(typeof window !== 'undefined' ? window : this);
