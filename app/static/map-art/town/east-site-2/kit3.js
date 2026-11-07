/*
 * 织梦 · east-site-2 本批新部件：栅栏、牲畜、树、缸、旗、土窑、崖面等。
 * 坐标同 kit.js：地面坐标，y 大 = 靠前，高度画成负 y。
 * 浏览器挂 window.TownArtES2_kit3，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./kit.js'), require('./kit2.js'));
  else root.TownArtES2_kit3 = factory(root.TownArtES2_core, root.TownArtES2_kit, root.TownArtES2_kit2);
})(this, function (C, K, K2) {
  'use strict';
  var S = C.S, f = C.f, poly = C.poly, pl = C.pl, path = C.path, rect = C.rect, ell = C.ell, circ = C.circ, ln = C.ln;
  var G = S.ink, G2 = S.ink2, LW = S.lw, LD = S.lwd;

  /** 一段木栅栏：从 (x1,y1) 到 (x2,y2)，柱高 h，柱距约 step。 */
  function fence(x1, y1, x2, y2, h, step, col) {
    h = h || 9; step = step || 9; col = col || S.wood;
    var len = Math.hypot(x2 - x1, y2 - y1), n = Math.max(1, Math.round(len / step)), o = '', i;
    o += ln(x1, y1 - h * 0.75, x2, y2 - h * 0.75, G, 3) + ln(x1, y1 - h * 0.75, x2, y2 - h * 0.75, col, 1.6);
    o += ln(x1, y1 - h * 0.35, x2, y2 - h * 0.35, G, 3) + ln(x1, y1 - h * 0.35, x2, y2 - h * 0.35, col, 1.6);
    for (i = 0; i <= n; i++) {
      var x = x1 + (x2 - x1) * i / n, y = y1 + (y2 - y1) * i / n;
      o += rect(x - 1.2, y - h, 2.4, h, S.wood3, G, 0.7);
    }
    return o;
  }
  /** 矩形围栏（后、左、右三边先画，前边最后由 fenceFront 画）。 */
  function penBack(x0, y0, x1, y1, h, col) { return fence(x0, y0, x1, y0, h, 9, col) + fence(x0, y0, x0, y1, h, 7, col) + fence(x1, y0, x1, y1, h, 7, col); }
  function penFront(x0, x1, y1, h, col, gap) {
    if (!gap) return fence(x0, y1, x1, y1, h, 9, col);
    var m = (x0 + x1) / 2;
    return fence(x0, y1, m - gap / 2, y1, h, 9, col) + fence(m + gap / 2, y1, x1, y1, h, 9, col);
  }
  /**
   * 侧视四足兽：脚底 (cx, yb)，体长 L，朝向 dir（1 向右、-1 向左）。
   * o = { body, dark, head, horn:'sheep'|'goat'|'cow'|'yak'|null, tall, tail, spots, fluffy, mane }
   */
  function beast(cx, yb, L, dir, o) {
    o = o || {};
    var hh = L * (o.tall || 0.42), bh = L * 0.42, by = yb - hh - bh * 0.35, s = '', k;
    var hx = cx + dir * L * 0.55, hy = by - bh * (o.headUp == null ? 0.45 : o.headUp);
    s += C.shadowEll(cx + 2, yb, L * 0.55, 2.2);
    // 腿
    [-0.32, -0.18, 0.2, 0.34].forEach(function (t, i) {
      var lx = cx + t * L, c = i === 1 || i === 2 ? (o.dark || S.brown) : (o.leg || o.dark || S.brown);
      s += rect(lx - 1, by + bh * 0.2, 2, yb - by - bh * 0.2, c, null, 0);
    });
    if (o.tail) s += ln(cx - dir * L * 0.48, by - 1, cx - dir * L * 0.6, by + bh * 0.5, o.dark || S.brown, 1.4);
    // 身
    if (o.fluffy) {
      var d = 'M' + f(cx - L / 2) + ' ' + f(by);
      for (k = 0; k < 6; k++) { var a = Math.PI + k * Math.PI / 5, a2 = Math.PI + (k + 1) * Math.PI / 5; d += 'Q' + f(cx + Math.cos((a + a2) / 2) * L * 0.62) + ' ' + f(by + Math.sin((a + a2) / 2) * bh * 0.95) + ' ' + f(cx + Math.cos(a2) * L / 2) + ' ' + f(by + Math.sin(a2) * bh * 0.6); }
      d += 'Q' + f(cx) + ' ' + f(by + bh * 0.85) + ' ' + f(cx - L / 2) + ' ' + f(by) + 'Z';
      s += path(d, o.body || S.cream2, G, LD);
    } else {
      s += ell(cx, by, L / 2, bh / 2, o.body || S.wood, G, LD);
    }
    if (o.spots) s += ell(cx - L * 0.1, by - bh * 0.1, L * 0.14, bh * 0.22, o.dark || S.navy, null, 0) + ell(cx + L * 0.2, by + bh * 0.05, L * 0.1, bh * 0.16, o.dark || S.navy, null, 0);
    if (o.mane) s += path('M' + f(cx + dir * L * 0.3) + ' ' + f(by - bh * 0.45) + 'Q' + f(hx - dir * 1) + ' ' + f(hy - 4) + ' ' + f(hx) + ' ' + f(hy - 2), null, o.dark, 2.2);
    // 颈 + 头
    s += path('M' + f(cx + dir * L * 0.32) + ' ' + f(by - bh * 0.3) + 'L' + f(hx) + ' ' + f(hy) + 'L' + f(hx + dir * 0.5) + ' ' + f(hy + bh * 0.45) + 'L' + f(cx + dir * L * 0.4) + ' ' + f(by + bh * 0.1) + 'Z', o.body || S.wood, null, 0);
    s += ell(hx + dir * L * 0.08, hy + 1, L * (o.headL || 0.14), L * 0.1, o.head || o.body || S.wood, G, LD);
    if (o.horn === 'sheep') s += path('M' + f(hx) + ' ' + f(hy - 1) + 'q' + f(-dir * 3) + ' -1 ' + f(-dir * 2) + ' 3', null, S.earth3, 1.4);
    if (o.horn === 'goat') s += path('M' + f(hx) + ' ' + f(hy - 1.5) + 'q' + f(-dir * 1) + ' -4 ' + f(-dir * 4) + ' -5', null, S.gray, 1.3) + ln(hx + dir * L * 0.14, hy + 3, hx + dir * L * 0.14, hy + 6, S.cream, 1.2);
    if (o.horn === 'cow' || o.horn === 'yak') s += path('M' + f(hx + dir * 1) + ' ' + f(hy - 1.5) + 'q' + f(dir * 2) + ' -4 ' + f(dir * 5) + ' -3', null, S.cream2, 1.4) + path('M' + f(hx - dir * 1) + ' ' + f(hy - 1.5) + 'q' + f(-dir * 2) + ' -4 ' + f(-dir * 5) + ' -3', null, S.cream2, 1.4);
    if (o.horn === 'yak') s += path('M' + f(cx - L / 2) + ' ' + f(by + 1) + 'L' + f(cx - L * 0.45) + ' ' + f(by + bh * 0.75) + 'L' + f(cx + L * 0.45) + ' ' + f(by + bh * 0.75) + 'L' + f(cx + L / 2) + ' ' + f(by + 1) + 'Z', o.dark, null, 0, C.fop(0.8));
    s += circ(hx + dir * L * 0.12, hy, 0.7, S.navy, null, 0);
    return s;
  }
  var A = {
    sheep: function (x, y, d, s) { return beast(x, y, s || 12, d, { body: S.cream2, head: S.navy, dark: S.navy, leg: S.navy, fluffy: true, horn: 'sheep', tall: 0.3 }); },
    goat: function (x, y, d, s) { return beast(x, y, s || 11, d, { body: S.cream, head: S.cream, dark: S.brown, horn: 'goat', tall: 0.45, tail: true, headUp: 0.7 }); },
    cow: function (x, y, d, s) { return beast(x, y, s || 17, d, { body: S.wood, head: S.wood, dark: S.brown, horn: 'cow', tall: 0.4, tail: true, headUp: 0.1, headL: 0.13 }); },
    milk: function (x, y, d, s) { return beast(x, y, s || 17, d, { body: S.cream2, head: S.cream2, dark: S.navy, spots: true, horn: 'cow', tall: 0.4, tail: true, headUp: 0.1 }); },
    yak: function (x, y, d, s) { return beast(x, y, s || 17, d, { body: S.coal2, head: S.coal2, dark: S.coal, horn: 'yak', tall: 0.34, tail: true, headUp: 0 }); },
    pig: function (x, y, d, s) { return beast(x, y, s || 13, d, { body: '#e6a58c', head: '#e6a58c', dark: S.brown2, tall: 0.22, headUp: -0.05, headL: 0.16 }); },
    horse: function (x, y, d, s, col) { return beast(x, y, s || 17, d, { body: col || S.wood, head: col || S.wood, dark: S.brown, mane: true, tall: 0.62, tail: true, headUp: 1.0, headL: 0.15 }); }
  };
  /** 圆冠树：脚底 (cx, yb)，冠半径 rr，fruit 为果色（null 不画果）。 */
  function tree(cx, yb, rr, col, col2, fruit, r) {
    var cy = yb - rr * 1.5, o = C.shadowEll(cx + 3, yb, rr * 0.9, rr * 0.3);
    o += rect(cx - 1.6, cy, 3.2, yb - cy, S.wood3, G, 0.8);
    o += circ(cx, cy, rr, col || S.leaf, G, LD);
    o += circ(cx - rr * 0.25, cy - rr * 0.25, rr * 0.6, col2 || S.leaf2, null, 0);
    if (fruit) for (var i = 0; i < 6; i++) {
      var a = (r ? r() : i / 6) * Math.PI * 2, d = rr * (0.35 + (r ? r() : 0.3) * 0.5);
      o += circ(cx + Math.cos(a) * d, cy + Math.sin(a) * d, 1.6, fruit, G, 0.5);
    }
    return o;
  }
  /** 酒缸 / 水缸：脚底 (cx, yb)，最宽 w，高 h，lid 为盖色（null 则敞口）。 */
  function jar(cx, yb, w, h, col, lid) {
    var t = w * 0.36, o = C.shadowEll(cx + 2, yb, w * 0.55, 2.2);
    o += path('M' + f(cx - t) + ' ' + f(yb - h) + 'C' + f(cx - w * 0.62) + ' ' + f(yb - h * 0.7) + ' ' + f(cx - w * 0.5) + ' ' + f(yb) + ' ' + f(cx - w * 0.25) + ' ' + f(yb) +
      'L' + f(cx + w * 0.25) + ' ' + f(yb) + 'C' + f(cx + w * 0.5) + ' ' + f(yb) + ' ' + f(cx + w * 0.62) + ' ' + f(yb - h * 0.7) + ' ' + f(cx + t) + ' ' + f(yb - h) + 'Z', col || S.brown2, G, LD);
    o += path('M' + f(cx - w * 0.47) + ' ' + f(yb - h * 0.55) + 'Q' + f(cx) + ' ' + f(yb - h * 0.45) + ' ' + f(cx + w * 0.47) + ' ' + f(yb - h * 0.55), null, G2, 0.8);
    o += ell(cx, yb - h, t + 1, 2.2, lid || S.coal, G, LD);
    if (lid) o += path('M' + f(cx - t) + ' ' + f(yb - h) + 'Q' + f(cx) + ' ' + f(yb - h - 5) + ' ' + f(cx + t) + ' ' + f(yb - h) + 'Z', lid, G, LD) + ln(cx, yb - h - 3.5, cx, yb - h - 5.5, G, 1.2);
    return o;
  }
  /** 挂旗（酒旗等）：杆 x，杆顶 yt，杆底 yb，旗宽 w 高 h，col 旗色，edge 为锯齿边色。 */
  function flag(x, yt, yb, w, h, col, edge, mark) {
    var o = rect(x - 1.4, yt, 2.8, yb - yt, S.wood3, G, 0.8) + ln(x, yt + 3, x + w + 2, yt + 3, S.wood3, 1.6);
    var d = 'M' + f(x + 2) + ' ' + f(yt + 4) + 'L' + f(x + w) + ' ' + f(yt + 4) + 'L' + f(x + w) + ' ' + f(yt + 4 + h);
    for (var i = 0; i < 4; i++) d += 'L' + f(x + w - (i + 0.5) * (w - 2) / 4) + ' ' + f(yt + 4 + h + (i % 2 ? 0 : 4)) + 'L' + f(x + w - (i + 1) * (w - 2) / 4) + ' ' + f(yt + 4 + h);
    o += path(d + 'Z', col || S.cream2, G, LD);
    if (edge) o += rect(x + 2, yt + 4, w - 2, 3, edge, null, 0);
    if (mark) o += mark;
    return o;
  }
  /** 一栋小房（土墙 + 门 + 前坡顶）：x0..x1，脚底 yb，墙高 wh，屋脊 ry（绝对 y）。 */
  function house(id, x0, x1, yb, wh, ry, wall, roofCol, kind, door) {
    var o = C.shadow([[x1, yb - wh], [x1 + 8, yb - wh + 4], [x1 + 8, yb + 3], [x1, yb]]);
    o += rect(x0, yb - wh, x1 - x0, wh, wall || S.cream, G, LD);
    var dx = door == null ? (x0 + x1) / 2 : door;
    o += rect(dx - 4, yb - wh * 0.72, 8, wh * 0.72, S.brown, G, LD) + ln(dx, yb - wh * 0.72, dx, yb, G2, 0.6);
    o += K.roof(id, x0, x1, ry, yb - wh + 1, 4, roofCol || S.thatch, kind || 'thatch', kind === 'tile' ? 4 : 2);
    return o;
  }
  /** 崖面：多边形 a（顶边在上），带横向岩层线，col 面色、col2 层线色。 */
  function cliff(a, id, col, col2, r) {
    var ys = a.map(function (p) { return p[1]; }), xs = a.map(function (p) { return p[0]; });
    var y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys), x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs), s = '';
    for (var y = y0 + 6; y < y1; y += 6 + (r ? r() * 4 : 2)) s += path('M' + f(x0) + ' ' + f(y) + 'q' + f((x1 - x0) / 3) + ' ' + f(r ? r() * 3 - 1.5 : 1) + ' ' + f((x1 - x0) / 1.5) + ' 0t' + f((x1 - x0) / 3) + ' 0', null, col2, 0.9);
    for (var i = 0; i < 5; i++) { var cx = x0 + (r ? r() : i / 5) * (x1 - x0); s += ln(cx, y0 + (r ? r() : 0.3) * (y1 - y0), cx + 1.5, y0 + (r ? r() : 0.6) * (y1 - y0) + 6, col2, 0.8); }
    return poly(a, col, G, LW) + C.clip(id + '-cl', poly(a, '#000'), s);
  }
  /** 毡房（蒙古包）：脚底中点 (cx, yb)，半宽 rw，墙高 h。 */
  function yurt(cx, yb, rw, h, felt) {
    var o = C.shadowEll(cx + 4, yb, rw + 3, rw * 0.3), top = yb - h;
    o += path('M' + f(cx - rw) + ' ' + f(top) + 'L' + f(cx - rw) + ' ' + f(yb - rw * 0.15) + 'Q' + f(cx) + ' ' + f(yb + rw * 0.2) + ' ' + f(cx + rw) + ' ' + f(yb - rw * 0.15) + 'L' + f(cx + rw) + ' ' + f(top) + 'Z', felt || S.cream2, G, LW);
    o += path('M' + f(cx - rw) + ' ' + f(top + h * 0.45) + 'Q' + f(cx) + ' ' + f(top + h * 0.45 + rw * 0.3) + ' ' + f(cx + rw) + ' ' + f(top + h * 0.45), null, S.vermil, 2);
    o += path('M' + f(cx - rw - 1) + ' ' + f(top) + 'Q' + f(cx - rw * 0.6) + ' ' + f(top - rw * 0.55) + ' ' + f(cx) + ' ' + f(top - rw * 0.62) + 'Q' + f(cx + rw * 0.6) + ' ' + f(top - rw * 0.55) + ' ' + f(cx + rw + 1) + ' ' + f(top) +
      'Q' + f(cx) + ' ' + f(top + rw * 0.3) + ' ' + f(cx - rw - 1) + ' ' + f(top) + 'Z', felt || S.cream2, G, LW);
    for (var k = -2; k <= 2; k++) o += ln(cx + k * rw * 0.18, top - rw * 0.6 + Math.abs(k) * 0.4, cx + k * rw * 0.45, top + rw * 0.18 - Math.abs(k) * 1.2, S.teal, 0.9, C.op(0.7));
    o += ell(cx, top - rw * 0.58, rw * 0.18, rw * 0.07, S.wood3, G, 0.8);
    o += path('M' + f(cx - 4.5) + ' ' + f(yb + rw * 0.05) + 'L' + f(cx - 4.5) + ' ' + f(yb - h * 0.62) + 'L' + f(cx + 4.5) + ' ' + f(yb - h * 0.62) + 'L' + f(cx + 4.5) + ' ' + f(yb + rw * 0.05) + 'Z', S.vermil, G, LD);
    return o;
  }
  /** 可平铺碎屑地面 def：底色 base，n 个碎块（颜色轮换 cols），specks 为亮点色；全部落在格内距边 ≥4 px，可任意平铺。 */
  function speckTile(o) {
    return { id: o.id, name: o.name, category: 'ground', kind: o.kind, resource: o.resource, subtype: o.subtype, facility: null, variant: o.v, w: 1, d: 1, up: 0,
      tags: ['tileable'].concat(o.tags || []), note: o.note || '碎块与亮点都在格内（距边 ≥4 px），四边同一底色，可任意平铺',
      draw: function (W, D, r) {
        var s = rect(-0.5, -0.5, 49, 49, o.base), i;
        if (o.under) s += o.under(r);
        for (i = 0; i < o.n; i++) {
          var x = 6 + r() * 36, y = 6 + r() * 36, k = 1.4 + r() * (o.size || 2.4), c = o.cols[i % o.cols.length];
          s += poly([[x - k, y], [x - k * 0.2, y - k * 0.9], [x + k, y - k * 0.3], [x + k * 0.5, y + k * 0.6]], c, null, 0);
        }
        (o.specks || []).forEach(function (c) { for (var q = 0; q < 4; q++) s += circ(6 + r() * 36, 6 + r() * 36, 0.9, c, null, 0); });
        return s;
      } };
  }
  /** 矿车轨道：从后 (x1,y1) 到前 (x2,y2)，轨距 gw。 */
  function rails(x1, y1, x2, y2, gw) {
    gw = gw || 12;
    var L = Math.hypot(x2 - x1, y2 - y1), n = Math.max(1, Math.floor(L / 7)), o = '', i;
    for (i = 0; i <= n; i++) { var t = i / n, x = x1 + (x2 - x1) * t, y = y1 + (y2 - y1) * t; o += rect(x - gw / 2 - 3, y - 1.2, gw + 6, 2.4, S.wood3, null, 0); }
    return o + ln(x1 - gw / 2, y1, x2 - gw / 2, y2, S.gray, 1.6) + ln(x1 + gw / 2, y1, x2 + gw / 2, y2, S.gray, 1.6);
  }
  /** 矿车：中心 cx，脚底 yb，斗宽 w，ore/ore2 为矿色（null 则空车）。 */
  function cart(cx, yb, w, ore, ore2, r) {
    var o = C.shadowEll(cx + 2, yb, w * 0.6, 2.4);
    if (ore) o += K.heap(cx, yb - 13, w / 2 - 2, 2.8, ore, ore2 || ore, r, 7);
    o += poly([[cx - w / 2, yb - 14], [cx + w / 2, yb - 14], [cx + w / 2 - 3, yb - 4], [cx - w / 2 + 3, yb - 4]], S.wood, G, LD);
    o += ln(cx - w / 2 + 1.5, yb - 9.5, cx + w / 2 - 1.5, yb - 9.5, S.wood3, 0.8);
    return o + circ(cx - w / 2 + 6, yb - 3, 3, S.coal2, G, 0.8) + circ(cx + w / 2 - 6, yb - 3, 3, S.coal2, G, 0.8);
  }
  /** 敞棚：x0..x1，后墙 yBack、前沿 yb，檐高 h；inner 为棚下内容（在后墙与前柱之间画）。 */
  function shed(id, x0, x1, yBack, yb, h, roofCol, kind, inner, wall) {
    var o = C.shadow([[x1 + 4, yb - h], [x1 + 12, yb - h + 5], [x1 + 12, yb + 4], [x1 + 4, yb]]);
    o += rect(x0, yBack - h, x1 - x0, h, wall || S.cream, G, LD) + rect(x0, yBack - h, x1 - x0, h, S.shadow, null, 0, C.fop(0.15));
    o += rect(x0, yBack, x1 - x0, yb - yBack, S.earth, null, 0, C.fop(0.6));
    o += inner || '';
    var n = Math.max(2, Math.round((x1 - x0) / 40));
    for (var i = 0; i <= n; i++) o += K.post(x0 + (x1 - x0) * i / n, yb - h, yb, 3.2, kind === 'tile' ? S.vermil : S.wood);
    return o + K.roof(id, x0, x1, yBack - h - 12, yb - h + 1, 5, roofCol || S.thatch, kind || 'thatch', kind === 'tile' ? 4 : 2);
  }
  return { fence: fence, penBack: penBack, penFront: penFront, beast: beast, A: A, tree: tree, jar: jar, flag: flag, house: house, cliff: cliff, yurt: yurt,
    speckTile: speckTile, rails: rails, cart: cart, shed: shed };
});
