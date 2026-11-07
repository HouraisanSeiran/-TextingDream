/*
 * 织梦 · 东方文化地标（east-landmark）· 宗教部件：香炉、太极、八卦坛、钟鼓楼、山门、长幡、宝葫芦、塔刹、抱鼓石、小屋檐
 * 由 east-special/religion.js 复制而来（去掉了那边的建筑定义，只留部件），保证与 east-special 画风一致。
 * 浏览器挂 window.TownArtEastLandmarkParts；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var K = (typeof module !== 'undefined' && module.exports) ? require('./lm-core.js') : root.TownArtEastLandmarkCore;
  var C = K.C, TILE = K.TILE, G = K.G, GL = K.GL, f = K.f, P = K.P, R = K.R, E = K.E, L = K.L;
  var SHF = ' fill-opacity="0.2"';

  /** 香炉：三足双耳铜鼎，插三炷香，香烟上飘。(x, y) = 着地中点。 */
  function censer(x, y, s, seed) {
    s = s || 1;
    var o = E(x + 3 * s, y + 0.5, 10 * s, 2.4 * s, K.SH, null, 0, SHF);
    var legs = 'M' + f(x - 5 * s) + ' ' + f(y - 6 * s) + 'L' + f(x - 6.5 * s) + ' ' + f(y) + 'M' + f(x + 5 * s) + ' ' + f(y - 6 * s) + 'L' + f(x + 6.5 * s) + ' ' + f(y) +
      'M' + f(x) + ' ' + f(y - 5 * s) + 'V' + f(y + 0.3);
    o += L(legs, G, 3 * s) + L(legs, C.bronze, 1.8 * s);
    o += R(x - 6.6 * s, y - 20 * s, 2.4 * s, 6 * s, C.bronze, GL, 0.6) + R(x + 4.2 * s, y - 20 * s, 2.4 * s, 6 * s, C.bronze, GL, 0.6);
    o += P('M' + f(x - 8.5 * s) + ' ' + f(y - 15 * s) + 'Q' + f(x - 8.5 * s) + ' ' + f(y - 4.5 * s) + ' ' + f(x) + ' ' + f(y - 4.5 * s) +
      'Q' + f(x + 8.5 * s) + ' ' + f(y - 4.5 * s) + ' ' + f(x + 8.5 * s) + ' ' + f(y - 15 * s) + 'Z', C.bronze, GL, 0.9);
    o += L('M' + f(x - 7.6 * s) + ' ' + f(y - 11 * s) + 'Q' + f(x) + ' ' + f(y - 8.6 * s) + ' ' + f(x + 7.6 * s) + ' ' + f(y - 11 * s), GL, 0.8);
    o += E(x - 2.5 * s, y - 9 * s, 1.6 * s, 2.4 * s, C.ochre, null, 0, ' fill-opacity="0.5"');
    o += E(x, y - 15 * s, 8.5 * s, 2.4 * s, C.dark, GL, 0.8);
    o += L('M' + f(x - 2.4 * s) + ' ' + f(y - 15 * s) + 'V' + f(y - 22 * s) + 'M' + f(x) + ' ' + f(y - 15.5 * s) + 'V' + f(y - 24 * s) + 'M' + f(x + 2.4 * s) + ' ' + f(y - 15 * s) + 'V' + f(y - 22 * s), C.red, 0.9 * s);
    o += K.dots([[x - 2.4 * s, y - 22 * s], [x, y - 24 * s], [x + 2.4 * s, y - 22 * s]], C.ochreLt, 1.4 * s);
    o += K.smoke(x + 0.5 * s, y - 28 * s, 5 * s, seed || 3);
    return o;
  }
  /** 太极图：(cx, cy) 圆心，r 半径。 */
  function taiji(cx, cy, r) {
    return E(cx, cy, r + 0.8, r + 0.8, GL) + E(cx, cy, r, r, C.wallLt) +
      P('M' + f(cx) + ' ' + f(cy - r) + 'A' + f(r) + ' ' + f(r) + ' 0 0 0 ' + f(cx) + ' ' + f(cy + r) + 'A' + f(r / 2) + ' ' + f(r / 2) + ' 0 0 0 ' + f(cx) + ' ' + f(cy) +
        'A' + f(r / 2) + ' ' + f(r / 2) + ' 0 0 1 ' + f(cx) + ' ' + f(cy - r) + 'Z', C.navy) +
      E(cx, cy - r / 2, r * 0.16, r * 0.16, C.wallLt) + E(cx, cy + r / 2, r * 0.16, r * 0.16, C.navy);
  }
  /** 八卦坛：地面上一个压扁的八角石坛，八边各刻一组卦爻，中心太极。(cx, cy) 坛面中心；r 半径；k 纵向压缩。 */
  function bagua(cx, cy, r, k, ht) {
    k = k || 0.55; ht = ht || 4;
    var top = [], i, o = '';
    for (i = 0; i < 8; i++) { var a = (i + 0.5) / 8 * Math.PI * 2; top.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r * k]); }
    var front = [top[0], top[1], top[2], top[3], [top[3][0], top[3][1] + ht], [top[2][0], top[2][1] + ht], [top[1][0], top[1][1] + ht], [top[0][0], top[0][1] + ht]];
    o += E(cx + 4, cy + r * k + ht, r * 0.9, r * k * 0.35, K.SH, null, 0, SHF);
    o += P(K.pts(front), C.stone, G, 0.8) + P(K.pts(top), C.stoneLt, G, 1);
    var inner = top.map(function (p) { return [cx + (p[0] - cx) * 0.62, cy + (p[1] - cy) * 0.62]; });
    o += P(K.pts(inner), C.navy, GL, 0.7);
    // 卦爻：每边三道短横，阴爻中间断开（按先天八卦给定的阴阳）
    var GUA = ['111', '011', '101', '001', '110', '010', '100', '000'], d = '';
    for (i = 0; i < 8; i++) {
      var a2 = (i + 0) / 8 * Math.PI * 2, ux = Math.cos(a2), uy = Math.sin(a2) * k, tx = -Math.sin(a2), ty = Math.cos(a2) * k;
      var tl = Math.sqrt(tx * tx + ty * ty) || 1; tx /= tl; ty /= tl;
      for (var j = 0; j < 3; j++) {
        var rr = r * (0.7 + j * 0.09), px = cx + ux * rr, py = cy + uy * rr, hl = r * 0.17;
        if (GUA[i][j] === '1') d += 'M' + f(px - tx * hl) + ' ' + f(py - ty * hl) + 'L' + f(px + tx * hl) + ' ' + f(py + ty * hl);
        else d += 'M' + f(px - tx * hl) + ' ' + f(py - ty * hl) + 'L' + f(px - tx * hl * 0.25) + ' ' + f(py - ty * hl * 0.25) + 'M' + f(px + tx * hl * 0.25) + ' ' + f(py + ty * hl * 0.25) + 'L' + f(px + tx * hl) + ' ' + f(py + ty * hl);
      }
    }
    o += L(d, C.dark, 1);
    o += '<g transform="translate(' + f(cx) + ' ' + f(cy) + ') scale(1 ' + f(k) + ')">' + taiji(0, 0, r * 0.42) + '</g>';
    return o;
  }
  /**
   * 山门：台基 + 红墙门屋，开 1 或 3 个拱门洞，歇山顶，门上匾额。
   * o.arches 1|3；o.wall 墙色；o.tile 瓦色。
   */
  function shanmen(x0, x1, yb, yf, h, o) {
    o = o || {};
    var cx = (x0 + x1) / 2, w = x1 - x0, s = '', n = o.arches || 3;
    s += K.platform(x0 - 2, x1 + 2, yb, yf + 3, 3);
    s += R(x0, yf - h, w, h, o.wall || C.red, G, 1) + R(x0, yf - 3, w, 3, C.stone, G, 0.6);
    var list = n === 3 ? [[cx - w * 0.31, w * 0.16, h * 0.56], [cx, w * 0.22, h * 0.7], [cx + w * 0.31, w * 0.16, h * 0.56]] : [[cx, w * 0.3, h * 0.7]];
    list.forEach(function (a) {
      var ax = a[0], aw = a[1], ah = a[2], y1 = yf - 3, y0 = y1 - ah;
      var d = 'M' + f(ax - aw / 2) + ' ' + f(y1) + 'V' + f(y0 + aw / 2) + 'A' + f(aw / 2) + ' ' + f(aw / 2) + ' 0 0 1 ' + f(ax + aw / 2) + ' ' + f(y0 + aw / 2) + 'V' + f(y1) + 'Z';
      s += P(d, C.dark, C.stoneLt, 2.4) + L(d, G, 0.6);
      s += R(ax - aw / 2 + 0.8, y0 + aw / 2, aw * 0.22, ah - aw / 2, C.red, GL, 0.5) + R(ax + aw / 2 - 0.8 - aw * 0.22, y0 + aw / 2, aw * 0.22, ah - aw / 2, C.red, GL, 0.5);
      s += R(ax - aw * 0.27, y1 - (ah - aw / 2) * 0.45, aw * 0.54, (ah - aw / 2) * 0.45, '#6a3d27');
    });
    s += R(x0, yf - h, w, 3, o.beam || C.teal, GL, 0.6);
    s += K.roof(x0, x1, yb, yf, h, { type: 'hip', tile: o.tile || TILE.grey, ov: 5, up: 6, hr: 10, ridge: 'chiwen', hipK: 0.6 }).svg;
    s += K.plaque(cx, yf - h + 7, Math.min(w * 0.42, 26), 7, { chars: o.chars || 3, bg: o.plaqueBg || C.navy });
    return s;
  }
  /** 长幡：高杆顶一枚宝珠，挂一条窄长幡，幡上几道符纹。 */
  function pennant(x, yBase, top, w, h, col, seed) {
    var s = L('M' + f(x) + ' ' + f(yBase) + 'V' + f(top), G, 2.6) + L('M' + f(x) + ' ' + f(yBase) + 'V' + f(top), C.umber, 1.6) +
      E(x, top - 1.5, 1.8, 1.8, C.ochre, G, 0.6) + R(x - 3, yBase - 4, 6, 4, C.stone, G, 0.6);
    var d = 'M' + f(x + 1) + ' ' + f(top + 2) + 'H' + f(x + 1 + w) + 'V' + f(top + 2 + h) + 'L' + f(x + 1 + w / 2) + ' ' + f(top + h - 2) + 'L' + f(x + 1) + ' ' + f(top + 2 + h) + 'Z';
    s += P(d, col || C.ochre, G, 0.7);
    var m = '';
    for (var i = 0; i < 3; i++) { var yy = top + 6 + i * h * 0.26; m += 'M' + f(x + 2.5) + ' ' + f(yy) + 'H' + f(x + w - 0.5) + 'M' + f(x + 1 + w / 2) + ' ' + f(yy - 1.5) + 'v3'; }
    return s + L(m, C.red, 0.8);
  }

  var defs = [];

  /** 铜钟：钟纽 + 钟身 + 钟口一道唇，身上两道箍与几枚钟乳。(cx, top) = 挂点。 */
  function bell(cx, top, s) {
    s = s || 1;
    var o = L('M' + f(cx) + ' ' + f(top) + 'v' + f(2 * s), C.dark, 1);
    var y0 = top + 2 * s, y1 = y0 + 10 * s;
    o += P('M' + f(cx - 2.6 * s) + ' ' + f(y0) + 'Q' + f(cx - 4.2 * s) + ' ' + f(y0 + 1 * s) + ' ' + f(cx - 4.4 * s) + ' ' + f(y0 + 4 * s) + 'L' + f(cx - 5.4 * s) + ' ' + f(y1) +
      'H' + f(cx + 5.4 * s) + 'L' + f(cx + 4.4 * s) + ' ' + f(y0 + 4 * s) + 'Q' + f(cx + 4.2 * s) + ' ' + f(y0 + 1 * s) + ' ' + f(cx + 2.6 * s) + ' ' + f(y0) + 'Z', C.bronze, GL, 0.8);
    o += L('M' + f(cx - 4.6 * s) + ' ' + f(y0 + 5.5 * s) + 'H' + f(cx + 4.6 * s) + 'M' + f(cx - 5.2 * s) + ' ' + f(y1 - 1.2 * s) + 'H' + f(cx + 5.2 * s), GL, 0.7);
    o += K.dots([[cx - 2.2 * s, y0 + 3 * s], [cx, y0 + 3 * s], [cx + 2.2 * s, y0 + 3 * s]], C.ochreLt, 1.1);
    return o;
  }
  /** 钟楼 / 鼓楼：砖台基（开一个拱券门洞）上起一座敞亭，亭里挂钟或架鼓，攒尖或歇山顶。 */
  function bellTower(x0, x1, yb, yf, o) {
    o = o || {};
    var hb = o.hb || 16, hp = o.hp || 15, cx = (x0 + x1) / 2, w = x1 - x0, s = '';
    s += K.box(x0, x1, yb, yf, hb, C.stoneLt, o.base || C.red, G, 1);
    s += K.bricks(x0, yf - hb, x1, yf, C.dark, 6, 3.4);
    var aw = Math.min(10, w * 0.32), ah = hb * 0.72;
    s += P('M' + f(cx - aw / 2) + ' ' + f(yf) + 'V' + f(yf - ah + aw / 2) + 'A' + f(aw / 2) + ' ' + f(aw / 2) + ' 0 0 1 ' + f(cx + aw / 2) + ' ' + f(yf - ah + aw / 2) + 'V' + f(yf) + 'Z', C.dark, C.stoneLt, 1.6);
    var inner = o.kind === 'drum'
      ? E(cx + 1.5, yf - hb - hp * 0.45, 5.5, 5.5, C.red, GL, 0.6) + E(cx, yf - hb - hp * 0.45, 5.5, 5.5, C.ochre, G, 0.8) + E(cx, yf - hb - hp * 0.45, 3.4, 3.4, C.ochreLt) +
        L('M' + f(cx - 5) + ' ' + f(yf - hb - 1) + 'L' + f(cx - 3) + ' ' + f(yf - hb - hp * 0.45 + 3) + 'M' + f(cx + 5) + ' ' + f(yf - hb - 1) + 'L' + f(cx + 3) + ' ' + f(yf - hb - hp * 0.45 + 3), C.umber, 1.2)
      : L('M' + f(x0 + 3) + ' ' + f(yf - hb - hp + 3) + 'H' + f(x1 - 3), C.umber, 1.2) + bell(cx, yf - hb - hp + 3, Math.min(1.1, w / 30));
    s += R(x0 + 1, yf - hb - 0.5, w - 2, 1.4, C.umber);
    s += K.pavilion(x0 + 2, x1 - 2, yb - hb, yf - hb, hp, { post: C.red, roof: { type: o.spire ? 'spire' : 'hip', tile: o.tile || TILE.grey, ov: 4, up: 6, hr: o.spire ? 14 : 9, ridge: 'chiwen', finial: 6 } }, inner).svg;
    s += K.railing(x0 + 1, x1 - 1, yf - hb, 3.2, C.red);
    return s;
  }
  /** 黄墙院：佛寺院墙刷土黄，墙上一道深色腰线。 */
  function templeWall(x0, x1, y, h) {
    return K.yardWall(x0, x1, y, h, { col: C.ochre }) + L('M' + f(x0) + ' ' + f(y - h + 4.5) + 'H' + f(x1), C.red, 1.1, 0.8);
  }


  /** 宝葫芦：道观正脊中央的葫芦宝顶。(cx, y) = 脊上着点。 */
  function gourd(cx, y, s) {
    s = s || 1;
    return R(cx - 2.4 * s, y - 2 * s, 4.8 * s, 2.4 * s, C.umber, GL, 0.5) +
      E(cx, y - 6 * s, 4 * s, 4 * s, C.ochre, G, 0.8) + E(cx, y - 12.5 * s, 2.7 * s, 2.9 * s, C.ochre, G, 0.8) +
      E(cx - 1.2 * s, y - 7 * s, 1.6 * s, 1.8 * s, C.ochreLt) + L('M' + f(cx) + ' ' + f(y - 15.4 * s) + 'v' + f(-2.6 * s), C.umber, 1);
  }


  /** 塔刹：刹杆 + 相轮（一串由大到小的金环）+ 宝珠。(cx, y) = 刹座底。 */
  function tasha(cx, y, s) {
    s = s || 1;
    var o = R(cx - 3.5 * s, y - 3 * s, 7 * s, 3 * s, C.ochre, G, 0.6) + L('M' + f(cx) + ' ' + f(y - 2) + 'V' + f(y - 22 * s), C.umber, 1.4);
    for (var i = 0; i < 6; i++) o += E(cx, y - 6 * s - i * 2.4 * s, (3.2 - i * 0.35) * s, 0.9 * s, C.ochre, G, 0.5);
    o += E(cx, y - 23 * s, 2 * s, 2.2 * s, C.ochreLt, G, 0.7);
    return o;
  }


  /** 抱鼓石：牌坊柱脚两侧夹柱的圆鼓石。 */
  function guShi(x, y, s) {
    s = s || 1;
    return R(x - 5 * s, y - 3 * s, 10 * s, 3 * s, C.stone, G, 0.6) + E(x, y - 7 * s, 4 * s, 4 * s, C.stoneLt, G, 0.7) + E(x, y - 7 * s, 2.2 * s, 2.2 * s, null, C.stoneDk, 0.6);
  }
  /** 一座小屋檐（牌坊、门楼用）：檐口落在 e，x0..x1。 */
  function capRoof(x0, x1, e, o) {
    o = o || {};
    return K.roof(x0, x1, e - (o.d || 8), e, 0, { type: 'hip', tile: o.tile || TILE.teal, ov: 4, up: o.up || 6, hr: o.hr || 6, ridge: 'chiwen', inset: o.inset, hipK: 0.4 }).svg;
  }


  // —— 导出 ——
  var API = { censer: censer, taiji: taiji, bagua: bagua, bellTower: bellTower, bell: bell, shanmen: shanmen, pennant: pennant,
    templeWall: templeWall, gourd: gourd, tasha: tasha, guShi: guShi, capRoof: capRoof };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.TownArtEastLandmarkParts = API;
})(typeof window !== 'undefined' ? window : this);
