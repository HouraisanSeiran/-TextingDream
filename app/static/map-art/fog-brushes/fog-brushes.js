/*
 * 织梦 · 地图迷雾卷云笔刷（美术样板，尚未接入游戏）
 *
 * 每枚笔刷 = 一到三个“云团”(clump)。云团上沿是一串手工摆放的“云头尖点”，
 * 相邻尖点之间用一段圆弧鼓出（b = 弓高 / 弦长），所以轮廓是连续的扇贝曲线，
 * 不是一颗颗独立的圆饼。只有上沿描墨线；下沿柔和地淡出，交给下一排云去盖。
 *
 * curl 指定每个云头里的纹样：
 *    1 / -1  顺 / 逆时针螺旋墨线（从云头尖点起笔，卷进云头里）
 *    2 / -2  短钩（半圈的小卷）
 *    0       两道短弧
 *
 * 浏览器里挂到 window.FogBrushes；Node 里 module.exports（给 export-svg.js 用）。
 */
(function (root) {
  'use strict';

  // 色板：内缘浅灰蓝 → 中灰蓝 → 暖灰蓝 → 灰褐 → 旧纸灰褐。
  // 外层按中世纪手绘地图的画法：淡彩打底、靠墨线和排线出细节，不靠压暗。
  //   detail —— 云体里额外的鱼鳞状叠层线条数（0 = 只有云头纹样）
  var TONES = {
    // 方案 B：淡羊皮纸 → 暖灰褐，同一色系由内到外逐渐加深；平涂不透明，明暗只靠墨线、叠层线和淡彩积色。
    //   back —— 双层笔刷里后排云的平涂色（比 body 深半档，前后层靠它分开）
    light: { name: '浅羊皮纸', top: '#e1d5ba', body: '#e1d5ba', back: '#d8cbae', shade: '#cdbd9c', pool: '#cdbd9c', seam: '#bba987', ink: '#5b4630', inkA: 0.85, detail: 0 },
    mid:   { name: '羊皮纸',   top: '#ddd0b3', body: '#ddd0b3', back: '#d3c5a6', shade: '#c2b190', pool: '#c2b190', seam: '#ad9b79', ink: '#4f3d2a', inkA: 0.88, detail: 1 },
    dark:  { name: '旧纸黄褐', top: '#cfc0a2', body: '#cfc0a2', back: '#c5b596', shade: '#b4a281', pool: '#b4a281', seam: '#a08d6c', ink: '#4a3826', inkA: 0.88, detail: 1 },
    dusk:  { name: '暖灰褐',   top: '#bfb093', body: '#bfb093', back: '#b5a587', shade: '#a69575', pool: '#a69575', seam: '#938262', ink: '#433323', inkA: 0.88, detail: 3 },
    coal:  { name: '灰褐',     top: '#b1a287', body: '#b1a287', back: '#a7977b', shade: '#9a8a6c', pool: '#9a8a6c', seam: '#87785b', ink: '#3e2f21', inkA: 0.86, detail: 3 }
  };
  var TONE_ORDER = ['light', 'mid', 'dark', 'dusk', 'coal'];

  // 手工设计的六枚笔刷（坐标是笔刷自身的 viewBox 像素；headY = 云头基线，排云墙时对齐探索边界）
  var BRUSHES = [
    { id: 'a', key: 'scallop', name: '扇贝长带', w: 300, h: 150, headY: 62,
      note: '低矮、细碎的一串扇贝云头，给贴地图的最内一排用',
      clumps: [{ pts: [[6, 84], [36, 64], [70, 54], [108, 47], [146, 52], [184, 45], [222, 53], [258, 60], [294, 80]],
                 b: [0.56, 0.6, 0.62, 0.58, 0.62, 0.6, 0.56, 0.52], curl: [2, 1, 0, -1, 0, 1, -2, 0],
                 bottom: [[298, 112], [230, 134], [150, 140], [70, 134], [2, 114]] }] },
    { id: 'b', key: 'billow', name: '大云岸', w: 300, h: 184, headY: 80,
      note: '中间一团高耸的大云头，两侧小扇贝收尾；中层云岸的主角',
      clumps: [{ pts: [[4, 118], [28, 100], [56, 90], [94, 78], [196, 72], [232, 86], [262, 98], [296, 118]],
                 b: [0.5, 0.56, 0.52, 0.64, 0.55, 0.56, 0.5], curl: [0, 2, 0, 1, -2, 0, 0],
                 bottom: [[298, 152], [220, 174], [150, 180], [80, 174], [2, 154]] }] },
    { id: 'c', key: 'tiered', name: '双层卷云', w: 300, h: 176, headY: 80,
      note: '后排一道高云、前排两小团压在它的下身上，一枚笔刷里就有前后层次',
      clumps: [
        { back: true, pts: [[44, 92], [82, 62], [126, 46], [174, 52], [212, 74], [246, 92]],
          b: [0.58, 0.6, 0.62, 0.6, 0.55], curl: [0, 1, 0, -1, 0],
          bottom: [[250, 130], [150, 142], [40, 130]] },
        { pts: [[4, 124], [30, 104], [64, 94], [102, 96], [134, 112]],
          b: [0.56, 0.62, 0.6, 0.55], curl: [2, 1, -2, 0],
          bottom: [[138, 150], [70, 166], [2, 152]] },
        { pts: [[150, 124], [178, 104], [214, 92], [254, 96], [296, 118]],
          b: [0.55, 0.6, 0.62, 0.55], curl: [0, -1, 1, -2],
          bottom: [[298, 150], [230, 168], [146, 154]] }
      ] },
    { id: 'd', key: 'surge', name: '斜卷浪头', w: 300, h: 170, headY: 76,
      note: '左低右高、云头越卷越大，像一道涌起的浪；打破整圈等高',
      clumps: [{ pts: [[6, 120], [26, 108], [50, 98], [80, 88], [114, 76], [154, 62], [206, 50], [256, 58], [294, 90]],
                 b: [0.5, 0.52, 0.55, 0.56, 0.58, 0.62, 0.62, 0.55], curl: [0, 0, 2, 0, 1, 1, -1, 0],
                 bottom: [[298, 128], [220, 152], [130, 160], [40, 152], [2, 140]] }] },
    { id: 'e', key: 'puff', name: '小簇云', w: 210, h: 140, headY: 64,
      note: '短而圆的一小簇，填缝、打断节奏',
      clumps: [{ pts: [[6, 96], [28, 76], [56, 62], [90, 52], [124, 56], [154, 66], [180, 80], [204, 98]],
                 b: [0.55, 0.6, 0.62, 0.64, 0.6, 0.58, 0.52], curl: [0, 2, 1, 0, -1, -2, 0],
                 bottom: [[206, 118], [150, 134], [60, 134], [4, 118]] }] },
    { id: 'f', key: 'bank', name: '低平云脚', w: 320, h: 150, headY: 62,
      note: '宽而平缓的大云脚，给外侧暗层铺底',
      clumps: [{ pts: [[4, 84], [52, 66], [112, 56], [178, 52], [244, 58], [316, 80]],
                 b: [0.36, 0.38, 0.36, 0.38, 0.34], curl: [2, 1, 0, -1, 0],
                 bottom: [[318, 112], [240, 138], [160, 144], [80, 138], [2, 114]] }] }
  ];

  var PI2 = Math.PI * 2;
  // 第一轮修改：云头弓高统一压低（0.6 → 约 0.37），相邻云头连成一道起伏的云岸，不再是一串圆珠
  var BOW = 0.62;

  function f(n) { return String(Math.round(n * 100) / 100); }
  function P(p) { return f(p[0]) + ' ' + f(p[1]); }

  // 一段鼓起的云头弧：p → q，向“上”（行进方向的左手）鼓出
  function segInfo(p, q, b) {
    b = Math.max(0.24, b * BOW);
    var dx = q[0] - p[0], dy = q[1] - p[1];
    var c = Math.hypot(dx, dy), s = b * c;
    var r = (c * c / 4 + s * s) / (2 * s);
    var nx = dy / c, ny = -dx / c;                 // 向外（朝上）的法线
    var mx = (p[0] + q[0]) / 2, my = (p[1] + q[1]) / 2;
    var apex = [mx + nx * s, my + ny * s];
    var re = Math.min(r, Math.max(s * 1.05, c * 0.34));   // 纹样用的有效半径（扁云头不让螺旋过大）
    return {
      p: p, q: q, c: c, s: s, r: r, re: re, n: [nx, ny], apex: apex,
      cx: apex[0] - nx * r, cy: apex[1] - ny * r,
      ec: [apex[0] - nx * re, apex[1] - ny * re],
      cmd: 'A' + f(r) + ' ' + f(r) + ' 0 ' + (b > 0.5 ? 1 : 0) + ' 1 ' + P(q)
    };
  }

  // Catmull-Rom → 三次贝塞尔（不含起点 M）
  function catmull(pts) {
    var d = '';
    for (var i = 0; i < pts.length - 1; i++) {
      var p0 = pts[i - 1] || pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] || p2;
      d += 'C' + P([p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6]) + ' ' +
        P([p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6]) + ' ' + P(p2);
    }
    return d;
  }

  // 粗细渐变的笔触（墨线两头尖、中间实），画成填充形
  function ribbon(pts, ws) {
    var L = [], R = [], n = pts.length;
    for (var i = 0; i < n; i++) {
      var a = pts[Math.max(i - 1, 0)], c = pts[Math.min(i + 1, n - 1)];
      var tx = c[0] - a[0], ty = c[1] - a[1], len = Math.hypot(tx, ty) || 1;
      var nx = -ty / len, ny = tx / len, h = ws[i] / 2;
      L.push([pts[i][0] + nx * h, pts[i][1] + ny * h]);
      R.push([pts[i][0] - nx * h, pts[i][1] - ny * h]);
    }
    R.reverse();
    return 'M' + P(L[0]) + catmull(L) + 'L' + P(R[0]) + catmull(R) + 'Z';
  }

  function spiral(cx, cy, a0, dir, turns, rho0, rho1, wmax, N) {
    var pts = [], ws = [];
    for (var i = 0; i <= N; i++) {
      var t = i / N, a = a0 + dir * t * turns * PI2;
      var rho = rho0 + (rho1 - rho0) * Math.pow(t, 0.8);
      pts.push([cx + Math.cos(a) * rho, cy + Math.sin(a) * rho]);
      ws.push(wmax * (0.18 + 0.82 * Math.sin(Math.PI * Math.min(1, 0.08 + t * 1.05))));
    }
    return ribbon(pts, ws);
  }

  function arcStroke(cx, cy, rho, a0, a1, wmax, N) {
    var pts = [], ws = [];
    for (var i = 0; i <= N; i++) {
      var t = i / N, a = a0 + (a1 - a0) * t;
      pts.push([cx + Math.cos(a) * rho, cy + Math.sin(a) * rho]);
      ws.push(wmax * (0.15 + 0.85 * Math.sin(Math.PI * t)));
    }
    return ribbon(pts, ws);
  }

  function circlePath(cx, cy, r) {
    return 'M' + f(cx - r) + ' ' + f(cy) + 'a' + f(r) + ' ' + f(r) + ' 0 1 0 ' + f(2 * r) + ' 0' +
      'a' + f(r) + ' ' + f(r) + ' 0 1 0 ' + f(-2 * r) + ' 0Z';
  }

  function inkWidth(re) { return Math.max(1.05, Math.min(2.5, re * 0.078)); }

  // 云头里的纹样
  function ornament(seg, kind) {
    var re = seg.re, cx = seg.ec[0], cy = seg.ec[1] + re * 0.12, w = inkWidth(re);
    var out = [];
    if (kind === 1 || kind === -1 || kind === 2 || kind === -2) {
      var dir = kind > 0 ? 1 : -1;
      var cusp = dir > 0 ? seg.p : seg.q;
      var a0 = Math.atan2(cusp[1] - cy, cusp[0] - cx);
      if (Math.abs(kind) === 1) {
        out.push({ d: spiral(cx, cy, a0, dir, 1.32, re * 0.84, re * 0.13, w, 44), o: 0.86 });
      } else {
        out.push({ d: spiral(cx, cy, a0, dir, 0.62, re * 0.8, re * 0.42, w * 0.9, 22), o: 0.78 });
      }
    } else {
      var am = Math.atan2(-seg.n[1], -seg.n[0]) + Math.PI; // 指向云头顶
      out.push({ d: arcStroke(cx, cy, re * 0.68, am - 0.62, am + 0.38, w * 0.85, 18), o: 0.62 });
      out.push({ d: arcStroke(cx, cy + re * 0.06, re * 0.44, am - 0.2, am + 0.5, w * 0.7, 14), o: 0.5 });
    }
    return out;
  }

  // 两个云头交界处：向云体里拖一道阴影 + 一小截墨线
  function seam(sa, sb, cusp) {
    var inx = -(sa.n[0] + sb.n[0]), iny = -(sa.n[1] + sb.n[1]);
    var len = Math.hypot(inx, iny) || 1; inx /= len; iny /= len;
    var small = sa.re < sb.re ? -1 : 1;              // 往小云头那边弯
    var latx = -iny * small, laty = inx * small;
    var mr = Math.min(sa.re, sb.re), L = mr * 0.62;
    var pts = [], ws = [], ipts = [], iws = [];
    for (var i = 0; i <= 12; i++) {
      var t = i / 12;
      var p = [cusp[0] + inx * L * t + latx * L * 0.28 * t * t, cusp[1] + iny * L * t + laty * L * 0.28 * t * t];
      pts.push(p); ws.push(mr * 0.42 * (1 - t) + 0.6);
      if (t <= 0.56) { ipts.push(p); iws.push(inkWidth(mr) * 0.9 * (1 - t / 0.56) + 0.2); }
    }
    return { shade: ribbon(pts, ws), ink: ribbon(ipts, iws) };
  }

  // 鱼鳞状叠层：把上沿轮廓整体下移、横向错开半个云头，再在每隔一个云头处加一枚小钩
  function strata(segs, top, avgRe, T) {
    var avgC = segs.reduce(function (a, s) { return a + s.c; }, 0) / segs.length;
    var out = [];
    for (var k = 1; k <= T.detail; k++) {
      var dx = (k % 2 ? 0.5 : 0.15) * avgC, dy = avgRe * (1.75 + 1.05 * (k - 1));
      var op = (k === 1 ? 0.62 : 0.42) * T.inkA;
      // 线条本身：稍细的扇贝线
      out.push('<path d="' + top + '" transform="translate(' + f(dx) + ' ' + f(dy) + ')" fill="none" stroke="' + T.ink +
        '" stroke-opacity="' + f(op) + '" stroke-width="' + f(k === 1 ? 1.2 : 1) + '" stroke-linecap="round" stroke-linejoin="round"/>');
      // 线条上方一窄条淡积色，让每一层像被下一层压住
      out.push('<path d="' + top + '" transform="translate(' + f(dx) + ' ' + f(dy - avgRe * 0.12) + ')" fill="none" stroke="' + T.pool +
        '" stroke-opacity="0.2" stroke-width="' + f(avgRe * 0.16) + '" stroke-linejoin="round"/>');
      // 每隔一个云头加一枚小钩（方向交替）
      segs.forEach(function (s, i) {
        if ((i + k) % 2) return;
        var sh = {
          re: s.re * 0.62, n: s.n,
          ec: [s.ec[0] + dx, s.ec[1] + dy + s.re * 0.1],
          p: [s.p[0] + dx, s.p[1] + dy], q: [s.q[0] + dx, s.q[1] + dy]
        };
        ornament(sh, (i % 4 < 2) ? 2 : -2).forEach(function (o) {
          out.push('<path d="' + o.d + '" fill="' + T.ink + '" fill-opacity="' + f(o.o * op) + '"/>');
        });
      });
    }
    return out.join('');
  }

  /**
   * 渲染一枚笔刷的一个色调。返回 { defs, body }：
   *   defs —— 该笔刷用到的 mask / clipPath / 渐变（id 全部带 prefix，保证全页唯一）
   *   body —— 图形本身（笔刷自身坐标）
   */
  function render(brush, toneName, prefix) {
    var T = TONES[toneName];
    var defs = [], body = [];
    // 不再用淡出遮罩：笔刷是不透明平涂的剪影，层次只靠前后遮挡。
    // 同一色调的笔刷互相重叠时平涂色连成一片，只剩上沿墨线可见。

    brush.clumps.forEach(function (cl, ci) {
      var segs = [], top = 'M' + P(cl.pts[0]), minY = Infinity;
      for (var i = 0; i < cl.pts.length - 1; i++) {
        var s = segInfo(cl.pts[i], cl.pts[i + 1], cl.b[i]);
        segs.push(s); top += s.cmd; minY = Math.min(minY, s.apex[1]);
      }
      var last = cl.pts[cl.pts.length - 1];
      var shape = top + catmull([last].concat(cl.bottom, [cl.pts[0]])) + 'Z';
      var kid = prefix + '-k' + ci;
      defs.push('<clipPath id="' + kid + '"><path d="' + shape + '"/></clipPath>');

      var avgRe = segs.reduce(function (a, s) { return a + s.re; }, 0) / segs.length;
      var g = [];
      // 平涂：不透明、无渐变、无高光
      g.push('<path d="' + shape + '" fill="' + (cl.back ? T.back : T.body) + '"/>');
      g.push('<g clip-path="url(#' + kid + ')">');
      // 淡彩积色：只沿上沿墨线内侧压一道窄色带（手绘淡彩的“勾边晕染”）
      g.push('<path d="' + top + '" fill="none" stroke="' + T.pool + '" stroke-opacity="0.38" stroke-width="' + f(avgRe * 0.2) + '" stroke-linejoin="round"/>');
      // 云头交界的阴影与墨线
      var seamShade = [], seamInk = [];
      for (var j = 1; j < segs.length; j++) {
        var sm = seam(segs[j - 1], segs[j], cl.pts[j]);
        seamShade.push(sm.shade); seamInk.push(sm.ink);
      }
      if (seamShade.length) {
        g.push('<path d="' + seamShade.join('') + '" fill="' + T.seam + '" fill-opacity="0.32"/>');
      }
      // 外层细节：在云头纹样下方再叠一到两道错开半个云头的扇贝线（鱼鳞状叠层），
      // 交界处配小钩，像木刻 / 手抄本里一层压一层的云。
      if (T.detail) g.push(strata(segs, top, avgRe, T));
      // 卷云纹样
      segs.forEach(function (s, k) {
        ornament(s, cl.curl[k]).forEach(function (o) {
          g.push('<path d="' + o.d + '" fill="' + T.ink + '" fill-opacity="' + f(o.o * T.inkA) + '"/>');
        });
      });
      if (seamInk.length) g.push('<path d="' + seamInk.join('') + '" fill="' + T.ink + '" fill-opacity="' + f(0.72 * T.inkA) + '"/>');
      g.push('</g>');
      // 只描上沿的墨线
      g.push('<path d="' + top + '" fill="none" stroke="' + T.ink + '" stroke-opacity="' + f(0.95 * T.inkA) + '" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>');
      body.push('<g>' + g.join('') + '</g>');
    });

    return {
      defs: defs.join(''),
      body: '<g>' + body.join('') + '</g>'
    };
  }

  /** 独立 SVG 文件（单枚笔刷、单个色调）。 */
  function standalone(brush, toneName) {
    var prefix = 'fb-' + brush.id + '-' + toneName;
    var r = render(brush, toneName, prefix);
    return '<?xml version="1.0" encoding="UTF-8"?>\n' +
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + brush.w + ' ' + brush.h + '" width="' + brush.w + '" height="' + brush.h + '">\n' +
      '<title>织梦迷雾卷云笔刷 ' + brush.id.toUpperCase() + ' · ' + brush.name + '（' + TONES[toneName].name + '；美术样板，未接入游戏）</title>\n' +
      '<defs>' + r.defs + '</defs>\n' + r.body + '\n</svg>\n';
  }

  var API = { TONES: TONES, TONE_ORDER: TONE_ORDER, BRUSHES: BRUSHES, render: render, standalone: standalone };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.FogBrushes = API;
})(this);
