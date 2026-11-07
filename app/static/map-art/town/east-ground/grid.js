/*
 * 织梦 · east-ground · 双网格区域几何（水面、院坪共用）
 *
 * 渲染瓦片 48×48，四角落在四个逻辑格中心，mask = NW*8 + NE*4 + SW*2 + SE*1。
 * 区域（水 / 铺地）与非区域的分界只连接瓦片边中点 (24,0)(48,24)(24,48)(0,24)，并在边中点处垂直于瓦片边，
 * 所以相邻瓦片的分界一定接得上。分界线以折线点列给出（pts），便于沿岸摆卵石、芦苇、石阶。
 *   round  —— 单角 / 三角用以孤立角为圆心、半径 24 的四分之一圆；半幅为带起伏的直线（自然岸）。
 *   square —— 单角 / 三角走边中点 → 瓦片中心 → 边中点的直角，中心处抹一个小圆角（条石驳岸、院坪）。
 * 对角组合 1001 / 0110 由两块单角拼成；square 模式的圆角让两块在中心互不接触。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'));
  else root.TownArtEG_grid = factory(root.TownArtEG_core);
})(this, function (K) {
  'use strict';
  var f = K.f;
  var ORDER = ['NW', 'NE', 'SE', 'SW'];                       // 顺时针
  var BIT = { NW: 8, NE: 4, SW: 2, SE: 1 };
  var CORNER = { NW: [0, 0], NE: [48, 0], SE: [48, 48], SW: [0, 48] };
  var MID = [[24, 0], [48, 24], [24, 48], [0, 24]];            // MID[i] 在 ORDER[i] 与 ORDER[i+1] 之间
  var OUT = [[0, -1], [1, 0], [0, 1], [-1, 0]];                // MID[i] 处朝瓦片外的法向

  function lerp(a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]; }
  function wob(t, amp, ph) { var s = Math.sin(Math.PI * t); return amp * s * s * Math.cos(3 * Math.PI * t + ph); }

  // 直分界（半幅）：起伏乘 sin²，两端位移与斜率为 0
  function straightPts(m1, m2, amp, ph) {
    var dx = m2[0] - m1[0], dy = m2[1] - m1[1], L = Math.hypot(dx, dy), nx = -dy / L, ny = dx / L, o = [];
    for (var i = 0; i <= 16; i++) { var t = i / 16, w = wob(t, amp, ph); o.push([m1[0] + dx * t + nx * w, m1[1] + dy * t + ny * w]); }
    return o;
  }
  // 四分之一圆：圆心 O，半径 24，可带轻微起伏
  function arcPts(m1, m2, O, amp, ph) {
    var a1 = Math.atan2(m1[1] - O[1], m1[0] - O[0]), a2 = Math.atan2(m2[1] - O[1], m2[0] - O[0]), da = a2 - a1, o = [];
    while (da > Math.PI) da -= 2 * Math.PI;
    while (da < -Math.PI) da += 2 * Math.PI;
    for (var i = 0; i <= 16; i++) {
      var t = i / 16, a = a1 + da * t, r = 24 + wob(t, amp * 0.7, ph);
      o.push([O[0] + Math.cos(a) * r, O[1] + Math.sin(a) * r]);
    }
    return o;
  }
  // 直角：m1 → 中心 → m2，中心处用二次曲线抹圆角 rr
  function squarePts(m1, m2, rr) {
    var c = [24, 24], a = lerp(c, m1, rr / 24), b = lerp(c, m2, rr / 24), o = [m1, lerp(m1, a, 0.5), a];
    for (var i = 1; i < 6; i++) { var t = i / 6, p = lerp(lerp(a, c, t), lerp(c, b, t), t); o.push(p); }
    o.push(b, lerp(b, m2, 0.5), m2);
    return o;
  }
  function polyD(pts) { return pts.map(function (p, i) { return (i ? 'L' : 'M') + K.pt(p); }).join(''); }

  /**
   * region(mask, opt) → null | { fill, edges: [{ pts, d, ext, kind, m1, m2, e1, e2 }] }
   * opt = { mode: 'round' | 'square', amp, ph, rr }。区域（水 / 铺地）在每条分界走向的右手边（屏幕坐标）。
   * ext 是两端沿瓦片外法向各延长 6 px 的分界，用来描粗线、画岸壁，跨瓦片时笔触不会断开。
   */
  function region(mask, opt) {
    opt = opt || {};
    var on = ORDER.map(function (k) { return !!(mask & BIT[k]); }), n = on.filter(Boolean).length;
    if (n === 0) return null;
    if (n === 4) return { fill: 'M0 0H48V48H0Z', edges: [] };
    if (n === 2 && on[0] === on[2]) {
      var fill = '', edges = [];
      ORDER.forEach(function (k, i) { if (on[i]) { var r = region(BIT[k], opt); fill += r.fill; edges = edges.concat(r.edges); } });
      return { fill: fill, edges: edges };
    }
    var ex = -1, en = -1, i;
    for (i = 0; i < 4; i++) { if (on[i] && !on[(i + 1) % 4]) ex = i; if (!on[i] && on[(i + 1) % 4]) en = i; }
    var m1 = MID[ex], m2 = MID[en], gap = (en - ex + 4) % 4, pts, kind;
    var amp = opt.amp || 0, ph = opt.ph || 0;
    if (gap === 2) { kind = 'straight'; pts = straightPts(m1, m2, amp, ph + mask * 0.37); }
    else {
      kind = gap === 3 ? 'convex' : 'concave';                    // convex = 区域只占一个角
      if (opt.mode === 'square') pts = squarePts(m1, m2, opt.rr == null ? 4 : opt.rr);
      else pts = arcPts(m1, m2, CORNER[ORDER[gap === 3 ? ex : en]], amp, ph + mask * 0.37);
    }
    var d = 'M' + K.pt(m2);
    for (var j = (en + 1) % 4; ; j = (j + 1) % 4) { d += 'L' + K.pt(CORNER[ORDER[j]]); if (j === ex) break; }
    d += 'L' + polyD(pts).slice(1) + 'Z';
    var e1 = OUT[ex], e2 = OUT[en];
    var ext = 'M' + K.pt([m1[0] + e1[0] * 6, m1[1] + e1[1] * 6]) + polyD(pts).replace(/^M/, 'L') + 'L' + K.pt([m2[0] + e2[0] * 6, m2[1] + e2[1] * 6]);
    return { fill: d, edges: [{ pts: pts, d: polyD(pts), ext: ext, kind: kind, m1: m1, m2: m2, ex: ex, en: en }] };
  }

  /** 沿分界取第 t（0..1，按点列下标）处的点、单位切向、指向区域内侧的单位法向。 */
  function at(edge, t) {
    var P = edge.pts, u = t * (P.length - 1), i = Math.min(P.length - 2, Math.floor(u)), k = u - i;
    var p = lerp(P[i], P[i + 1], k), dx = P[i + 1][0] - P[i][0], dy = P[i + 1][1] - P[i][1], L = Math.hypot(dx, dy) || 1;
    return { p: p, tx: dx / L, ty: dy / L, nx: -dy / L, ny: dx / L };
  }
  /** 分界折线的长度 */
  function len(edge) { var s = 0; for (var i = 1; i < edge.pts.length; i++) s += Math.hypot(edge.pts[i][0] - edge.pts[i - 1][0], edge.pts[i][1] - edge.pts[i - 1][1]); return s; }
  /** 瓦片减去区域（evenodd 裁剪用） */
  function outside(rg) { return 'M-2 -2H50V50H-2Z' + rg.fill; }

  return { ORDER: ORDER, BIT: BIT, MID: MID, region: region, at: at, len: len, outside: outside, polyD: polyD, f: f };
});
