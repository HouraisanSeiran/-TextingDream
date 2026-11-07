/*
 * 织梦 · 东方城防工事 B：瓮城（方）wengcheng-square-{n,s,e,w}、月城（半圆）wengcheng-moon-{n,s,e,w}。
 * 朝向 = 瓮城凸出的方向：s = 接在东西向墙南侧（3×2，占墙南面两行），n = 墙北侧（3×2），e / w = 南北向墙东 / 西侧（2×3）。
 * 墙厚 36、墙高 WH，砖缝 / 垛口 / 女墙 / 海墁同 east-base。两条翼墙伸进主墙 6 px（s：向北越过占地；e / w：横向越出 6 px）
 *   与主墙墙身贴合；n 向翼墙停在占地前沿（g = 0），离主墙北沿女墙留 6 px，被主墙女墙压住大半。
 * 方瓮城用一张操作表描述（顶面 / 垛墙 / 立面 / 院坪 / 门洞 / 门楼），w 向由 e 向镜像得到。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'));
  else root.TownArtFort_fortsB = factory(root.TownArtFort_core);
})(this, function (F) {
  'use strict';
  var E = F.E, C = F.C, T = F.T, K = F.K, f = F.f, sy = F.sy, WH = F.WH, PH = F.PH, PW = F.PW, WC = F.WC, P = F.P, add = F.add;
  var YARD = F.mix(C.earthL, C.stone, 0.4);

  // 门楼：瓮城墙顶的小歇山楼（面阔 w，中心 cx, gc）
  function pavilion(ctx, cx, gc, w) {
    var x0 = cx - w / 2, x1 = cx + w / 2, gf = gc + 8, gb = gc - 8, z0 = WH, z1 = WH + 11, s = '';
    s += E.shadow(x0, x1, gb, gf, 14, 3).replace('fill-opacity="0.2"', 'fill-opacity="0.12"');
    s += E.face(x0, x1, gf, z0, z1, C.cream);
    for (var k = 0; k < 3; k++) s += E.win(x0 + k * w / 3 + w / 15, gf, z0 + 3, w / 5, 5, 'lattice');
    for (k = 0; k <= 3; k++) s += E.col(x0 + k * w / 3, gf, z0, z1, C.vermil);
    s += E.face(x0 - 0.5, x1 + 0.5, gf, z1 - 2, z1, C.teal, C.gold2, 0.5);
    return s + E.roofEW(ctx, { x0: x0, x1: x1, gb: gb, gf: gf, h: z1, rh: 9, type: 'xie', t: T.gray, ov: 4, os: 4, lift: 5, ridge: 'curl', ridgeW: 2.4 });
  }
  // 操作表：['yard',x0,x1,gb,gf] ['top',x0,x1,gb,gf] ['mH',x0,x1,yF,solid] ['mV',xa,g0,g1] ['face',x0,x1,g,endL,endR] ['arch',cx,g] ['pav',cx,gc,w]
  function run(ctx, ops) {
    var s = '';
    ops.forEach(function (o) {
      var t = o[0];
      if (t === 'yard') s += E.rect(o[1], o[3], o[2] - o[1], o[4] - o[3], YARD) + E.line('M' + f(o[1]) + ' ' + f(o[3] + 4) + 'H' + f(o[2]), C.umber, 0.5, ' stroke-opacity="0.25"');
      else if (t === 'top') s += F.topPoly(ctx, [[o[1], o[3]], [o[2], o[3]], [o[2], o[4]], [o[1], o[4]]], WH);
      else if (t === 'mH') s += F.merlonsH(o[1], o[2], o[3], PW, WH, WH + (o[4] ? 3.5 : PH), !!o[4]);
      else if (t === 'mV') s += F.merlonsV(o[1], o[2], o[3], WH, WH + PH);
      else if (t === 'face') s += F.wallFace(ctx, o[1], o[2], o[3], WH, [o[4], o[5]]);
      else if (t === 'arch') s += F.gateArch(o[1], o[2], 14, 16) + E.rect(o[1] - 8, sy(o[2], WH - 4), 16, 3.6, C.navy, C.gold2, 0.6);
      else if (t === 'pav') s += pavilion(ctx, o[1], o[2], o[3]);
      else if (t === 'shadow') s += E.shadow(o[1], o[2], o[3], o[4], WH, 5);
    });
    return s;
  }
  var SQ = {
    s: [['shadow', 6, 138, -102, -6], ['yard', 42, 102, -102, -42], ['top', 6, 42, -102, -6], ['top', 102, 138, -102, -6], ['top', 6, 138, -42, -6],
      ['mV', 6, -102, -6], ['mV', 138 - PW, -102, -6], ['mV', 42 - PW, -102, -42], ['mV', 102, -102, -42], ['mH', 42, 102, -42 + PW, true],
      ['face', 6, 138, -6, true, true], ['arch', 72, -6], ['mH', 6, 138, -6, false], ['pav', 72, -24, 30]],
    n: [['shadow', 6, 138, -90, 0], ['yard', 42, 102, -54, 0], ['top', 6, 138, -90, -54], ['top', 6, 42, -90, 0], ['top', 102, 138, -90, 0],
      ['mH', 6, 138, -90 + PW, false], ['mV', 6, -90 + PW, 0], ['mV', 138 - PW, -90 + PW, 0], ['pav', 72, -72, 30],
      ['face', 42, 102, -54, true, true], ['mH', 42, 102, -54, true], ['mV', 42 - PW, -54, 0], ['mV', 102, -54, 0],
      ['face', 6, 42, 0, true, true], ['face', 102, 138, 0, true, true]],
    e: [['shadow', -6, 90, -138, -6], ['yard', 0, 54, -102, -42], ['top', -6, 90, -138, -102], ['top', 54, 90, -138, -6], ['top', -6, 90, -42, -6],
      ['mH', -6, 90, -138 + PW, false], ['mV', 90 - PW, -138 + PW, -6], ['face', -6, 54, -102, false, false], ['mH', -6, 54, -102, true],
      ['mV', 54, -102, -42], ['mH', -6, 54, -42 + PW, true], ['pav', 72, -72, 26],
      ['face', -6, 90, -6, false, true], ['mH', -6, 90, -6, false]]
  };
  // w = e 的镜像（x → 96 - x）
  SQ.w = SQ.e.map(function (o) {
    var t = o[0], m = function (x) { return 96 - x; };
    if (t === 'mV') return ['mV', 96 - o[1] - PW, o[2], o[3]];
    if (t === 'pav') return ['pav', m(o[1]), o[2], o[3]];
    if (t === 'face') return ['face', m(o[2]), m(o[1]), o[3], o[5], o[4]];
    if (t === 'mH') return ['mH', m(o[2]), m(o[1]), o[3], o[4]];
    return [t, m(o[2]), m(o[1]), o[3], o[4]];
  });

  /* ---------- 月城：半椭圆环墙。外沿垛口、内沿女墙；朝南（法线 y>0.15）的段画砖立面 ---------- */
  var MOON = {   // c = 椭圆心（开口所在的主墙墙面），r = 外半径 [rx, ry]，a = 角度范围，gate = 门洞 / 门楼位置
    s: { fp: [3, 2], c: [72, -102], r: [66, 96], a: [0, Math.PI], arch: [72, -6], pav: [72, -24, 30] },
    n: { fp: [3, 2], c: [72, 0], r: [66, 90], a: [Math.PI, 2 * Math.PI], pav: [72, -72, 30] },
    e: { fp: [2, 3], c: [-6, -72], r: [90, 66], a: [-Math.PI / 2, Math.PI / 2], pav: [66, -72, 26] },
    w: { fp: [2, 3], c: [102, -72], r: [90, 66], a: [Math.PI / 2, 1.5 * Math.PI], pav: [30, -72, 26] }
  };
  function moon(ctx, dir) {
    var m = MOON[dir], N = 16, O = [], I = [], k, s = '';
    for (k = 0; k <= N; k++) {
      var t = m.a[0] + (m.a[1] - m.a[0]) * k / N, c = Math.cos(t), sn = Math.sin(t);
      O.push([m.c[0] + m.r[0] * c, m.c[1] + m.r[1] * sn]);
      I.push([m.c[0] + (m.r[0] - 36) * c, m.c[1] + (m.r[1] - 36) * sn]);
    }
    var ring = O.concat(I.slice().reverse());
    s += E.path(E.poly(ring.map(function (p) { return add(p, [5, 3]); })), C.shadow, null, 0, ' fill-opacity="0.2"');
    s += E.path(E.poly(I), YARD);
    s += F.topPoly(ctx, ring, WH);
    // 每段：a, b, 离开墙体的法线 out, 是否外沿
    var segs = [];
    function addSeg(a, b, outer) {
      var d = [b[0] - a[0], b[1] - a[1]], L = Math.hypot(d[0], d[1]), n = [-d[1] / L, d[0] / L];
      var mid = [(a[0] + b[0]) / 2 - m.c[0], (a[1] + b[1]) / 2 - m.c[1]], away = n[0] * mid[0] + n[1] * mid[1] > 0;
      if (away !== outer) n = [-n[0], -n[1]];
      segs.push({ a: a, b: b, n: n, outer: outer, y: (a[1] + b[1]) / 2 });
    }
    for (k = 0; k < N; k++) { addSeg(O[k], O[k + 1], true); addSeg(I[k], I[k + 1], false); }
    var ni = function (q) { return [-q.n[0], -q.n[1]]; };
    segs.filter(function (q) { return q.n[1] <= 0.15; }).forEach(function (q) { s += F.diagPar(q.a, q.b, ni(q), q.outer); });
    segs.filter(function (q) { return q.n[1] > 0.15; }).sort(function (p, q) { return p.y - q.y; }).forEach(function (q) {
      var fill = F.shadeOf(q.n);
      s += F.diagFace(ctx, q.a, q.b, WH, fill, [false, false]) + F.diagPar(q.a, q.b, ni(q), q.outer, fill);
    });
    if (m.arch) s += F.gateArch(m.arch[0], m.arch[1], 14, 16);
    if (m.pav) s += pavilion(ctx, m.pav[0], m.pav[1], m.pav[2]);
    return s;
  }

  function items() {
    var out = [], NAME = { n: '北', s: '南', e: '东', w: '西' };
    ['n', 's', 'e', 'w'].forEach(function (d, i) {
      var fp = d === 'n' || d === 's' ? [3, 2] : [2, 3];
      var id = 'east-common-wengcheng-square-' + d, sym = E.symbol(id, 9400 + i, fp[0], fp[1], function (c) { return run(c, SQ[d]); });
      out.push({ id: id, svg: sym.svg, name: '方瓮城 ' + d, meta: { id: id, style: 'east', race: 'common', category: 'fort', kind: 'wengcheng_square',
        facility: 'gate', variant: i + 1, footprint: fp, height_px: sym.up, anchor: sym.anchor, viewBox: sym.viewBox,
        tags: ['wengcheng', 'square', 'dir_' + d, 'crenellated', 'brick_faced', 'gate_pavilion'], roof: 'hip_tile', name_zh: '方瓮城', dir: d,
        note: '方形瓮城，向' + NAME[d] + '凸出，开口贴在' + (fp[0] === 3 ? '东西向' : '南北向') + '主墙的城门外；占地左前角对齐城门格' + NAME[d] + '侧。翼墙伸进主墙 6 px 贴合。' +
          (d === 's' ? '外门在南墙正中（拱门 + 门匾）' : '外门在看不见的' + NAME[d] + '墙面上，靠墙顶门楼示意') + '；墙顶门楼歇山顶，roof 按最近值写 hip_tile' } });
      id = 'east-common-wengcheng-moon-' + d;
      sym = E.symbol(id, 9410 + i, fp[0], fp[1], function (c) { return moon(c, d); });
      out.push({ id: id, svg: sym.svg, name: '月城 ' + d, meta: { id: id, style: 'east', race: 'common', category: 'fort', kind: 'wengcheng_moon',
        facility: 'gate', variant: i + 1, footprint: fp, height_px: sym.up, anchor: sym.anchor, viewBox: sym.viewBox,
        tags: ['wengcheng', 'moon_city', 'semicircle', 'dir_' + d, 'crenellated', 'brick_faced'], roof: 'hip_tile', name_zh: '月城', dir: d,
        note: '月城（半圆瓮城），向' + NAME[d] + '凸出，半椭圆环墙厚约 36；朝南的弧段画砖立面，外沿垛口、内沿女墙。' +
          (d === 's' ? '南端开门' : '门在看不见的一侧，靠门楼示意') } });
    });
    return out;
  }
  return { items: items, moon: moon, run: run, SQ: SQ, MOON: MOON };
});
