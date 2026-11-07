/*
 * 织梦 · 东方特殊建筑 · 宗教与礼制：佛寺、道观、佛塔、牌坊、戏台（美术素材，尚未接入游戏）
 * def 格式同 civic.js。
 */
(function (root) {
  'use strict';
  var K = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtEastSpecialCore;
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

  defs.push({
    kind: 'temple', variant: 1, name: '佛寺', facility: 'temple', category: 'special', fp: [3, 3], up: 96,
    tags: ['compound', 'courtyard', 'buddhist'], roof: 'hip_tile',
    note: '一进院：红墙三洞山门（歇山、匾额），土黄院墙；院中三足铜香炉青烟袅袅、两棵古柏；后为重檐大雄宝殿，正脊中央宝珠。',
    draw: function (K, W, U, D) {
      var s = '';
      s += K.shadow(6, W - 6, U + 8, U + 136, 9);
      s += K.pave(4, U + 8, W - 4, U + 140, 12);
      s += K.platform(14, W - 14, U + 10, U + 70, 6);
      s += K.steps(W / 2, U + 70, 22, 3);
      s += K.hall(20, W - 20, U + 10, U + 64, { double: true, h1: 24, h2: 16, inset: 9, skirt: 6,
        fac: { bays: 5, doors: [1, 2, 3], col: C.red, beam: C.teal, doorCol: C.red },
        roof: { type: 'hip', tile: TILE.grey, ov: 6, up: 8, hr: 14, ridge: 'chiwen', hipK: 0.55, pearl: true } }).svg;
      s += K.plaque(W / 2, U + 64 - 5 - 24 - 8, 24, 6.5, { chars: 4, bg: C.navy });
      s += K.sideWall(6, U + 24, U + 132, 18, { col: C.ochre }) + K.sideWall(W - 6, U + 24, U + 132, 18, { col: C.ochre });
      s += K.tree(26, U + 104, 9, 5, { col: C.teal }) + K.tree(W - 26, U + 104, 9, 9, { col: C.teal });
      s += censer(W / 2, U + 100, 1.05, 13);
      s += templeWall(5, 42, U + 134, 18) + templeWall(W - 42, W - 5, U + 134, 18);
      s += shanmen(42, W - 42, U + 112, U + 137, 27, { arches: 3, chars: 3 });
      return s;
    }
  });

  defs.push({
    kind: 'temple', variant: 2, name: '大寺（钟鼓楼）', facility: 'temple', category: 'special', fp: [4, 3], up: 112,
    tags: ['compound', 'courtyard', 'buddhist', 'large', 'bell_tower', 'drum_tower'], roof: 'hip_tile',
    note: '黄琉璃瓦重檐大殿居中，前院左钟楼右鼓楼（砖台基 + 敞亭）；红墙三洞山门、土黄院墙、香炉与经幢长幡。',
    draw: function (K, W, U, D) {
      var s = '';
      s += K.shadow(6, W - 6, U + 8, U + 136, 10);
      s += K.pave(4, U + 8, W - 4, U + 140, 12);
      s += K.platform(34, W - 34, U + 8, U + 70, 7);
      s += K.steps(W / 2, U + 70, 26, 3);
      s += K.hall(40, W - 40, U + 8, U + 63, { double: true, h1: 26, h2: 18, inset: 10, skirt: 7,
        fac: { bays: 5, doors: [1, 2, 3], col: C.red, beam: C.teal },
        roof: { type: 'hip', tile: TILE.gold, ov: 7, up: 9, hr: 16, ridge: 'chiwen', hipK: 0.5, pearl: true } }).svg;
      s += K.plaque(W / 2, U + 63 - 5 - 26 - 9, 26, 7, { chars: 4, bg: C.navy });
      s += K.sideWall(6, U + 20, U + 132, 18, { col: C.ochre }) + K.sideWall(W - 6, U + 20, U + 132, 18, { col: C.ochre });
      s += bellTower(12, 40, U + 74, U + 102, { kind: 'bell', hb: 18, hp: 16, spire: false });
      s += bellTower(W - 40, W - 12, U + 74, U + 102, { kind: 'drum', hb: 18, hp: 16, spire: false });
      s += pennant(62, U + 112, U + 50, 6, 30, C.ochre) + pennant(W - 62, U + 112, U + 50, 6, 30, C.ochre);
      s += censer(W / 2, U + 104, 1.1, 17);
      s += templeWall(5, 58, U + 134, 18) + templeWall(W - 58, W - 5, U + 134, 18);
      s += shanmen(58, W - 58, U + 112, U + 137, 28, { arches: 3, chars: 3 });
      return s;
    }
  });

  /** 宝葫芦：道观正脊中央的葫芦宝顶。(cx, y) = 脊上着点。 */
  function gourd(cx, y, s) {
    s = s || 1;
    return R(cx - 2.4 * s, y - 2 * s, 4.8 * s, 2.4 * s, C.umber, GL, 0.5) +
      E(cx, y - 6 * s, 4 * s, 4 * s, C.ochre, G, 0.8) + E(cx, y - 12.5 * s, 2.7 * s, 2.9 * s, C.ochre, G, 0.8) +
      E(cx - 1.2 * s, y - 7 * s, 1.6 * s, 1.8 * s, C.ochreLt) + L('M' + f(cx) + ' ' + f(y - 15.4 * s) + 'v' + f(-2.6 * s), C.umber, 1);
  }

  defs.push({
    kind: 'temple', variant: 3, name: '道观', facility: 'temple', category: 'special', fp: [3, 3], up: 96,
    tags: ['compound', 'courtyard', 'taoist', 'bagua'], roof: 'hip_tile',
    note: '道观：青绿琉璃歇山三清殿，正脊中央宝葫芦，门额太极；院中八卦石坛（先天八卦爻纹 + 太极）、三足香炉；左右杏黄长幡；白粉院墙、单洞红山门。',
    draw: function (K, W, U, D) {
      var s = '', cx = W / 2;
      s += K.shadow(6, W - 6, U + 8, U + 136, 9);
      s += K.pave(4, U + 8, W - 4, U + 140, 12);
      s += K.platform(18, W - 18, U + 10, U + 66, 5);
      s += K.steps(cx, U + 66, 20, 3);
      var hl = K.hall(22, W - 22, U + 10, U + 61, { h: 28, fac: { bays: 5, doors: [2], col: C.red, beam: C.teal, win: 'lattice' },
        roof: { type: 'hip', tile: TILE.teal, ov: 6, up: 9, hr: 15, ridge: 'chiwen', hipK: 0.55 } });
      s += hl.svg + gourd(cx, hl.roof.ridgeY - 3, 1);
      s += taiji(cx, U + 61 - 28 + 9, 5);
      s += K.sideWall(6, U + 24, U + 132, 16) + K.sideWall(W - 6, U + 24, U + 132, 16);
      s += K.tree(22, U + 116, 8, 31, { col: C.teal }) + K.tree(W - 22, U + 116, 8, 37, { col: C.teal });
      s += pennant(36, U + 120, U + 62, 6, 28, C.ochre) + pennant(W - 42, U + 120, U + 62, 6, 28, C.ochre);
      s += bagua(cx, U + 87, 21, 0.42, 4) + censer(cx, U + 89, 0.75, 21);
      s += K.yardWall(5, 54, U + 136, 14) + K.yardWall(W - 54, W - 5, U + 136, 14);
      s += shanmen(54, W - 54, U + 120, U + 137, 22, { arches: 1, chars: 2 });
      return s;
    }
  });

  /** 塔刹：刹杆 + 相轮（一串由大到小的金环）+ 宝珠。(cx, y) = 刹座底。 */
  function tasha(cx, y, s) {
    s = s || 1;
    var o = R(cx - 3.5 * s, y - 3 * s, 7 * s, 3 * s, C.ochre, G, 0.6) + L('M' + f(cx) + ' ' + f(y - 2) + 'V' + f(y - 22 * s), C.umber, 1.4);
    for (var i = 0; i < 6; i++) o += E(cx, y - 6 * s - i * 2.4 * s, (3.2 - i * 0.35) * s, 0.9 * s, C.ochre, G, 0.5);
    o += E(cx, y - 23 * s, 2 * s, 2.2 * s, C.ochreLt, G, 0.7);
    return o;
  }

  defs.push({
    kind: 'temple', variant: 4, name: '七级佛塔', facility: 'temple', category: 'special', fp: [2, 2], up: 144,
    tags: ['pagoda', 'buddhist', 'landmark'], roof: 'hip_tile',
    note: '七级楼阁式小佛塔：青石须弥座 + 栏杆，底层开朱门，上六层每层一个佛龛、层层出檐起翘、逐层收分；顶为攒尖 + 相轮塔刹。可单独立在寺后或街口。',
    draw: function (K, W, U, D) {
      var s = '', cx = W / 2, yF = U + 80;
      s += K.shadow(cx - 26, cx + 26, U + 46, yF + 4, 10);
      s += K.pave(6, U + 40, W - 6, U + D - 1, 12);
      s += K.platform(cx - 30, cx + 30, U + 44, yF + 6, 6);
      s += K.steps(cx, yF + 6, 12, 3, 2);
      var hs = [18, 10, 9.5, 9, 8.5, 8, 7.5], y = yF, w = 42;
      hs.forEach(function (h, i) {
        var x0 = cx - w / 2, x1 = cx + w / 2, d = w * 0.55, top = y - h;
        s += R(x0, top, w, h, i ? C.wallLt : C.wall, G, 0.9);
        if (i === 0) s += K.door(cx - 5, y - 13, 10, 12.5, { col: C.red });
        else s += P('M' + f(cx - 2.6) + ' ' + f(y - 1) + 'V' + f(top + 4.5) + 'A2.6 2.6 0 0 1 ' + f(cx + 2.6) + ' ' + f(top + 4.5) + 'V' + f(y - 1) + 'Z', C.dark, GL, 0.6) +
          E(cx, y - h * 0.42, 1.2, 1.4, C.ochre);
        s += R(x0, top, 2.2, h, C.red, GL, 0.5) + R(x1 - 2.2, top, 2.2, h, C.red, GL, 0.5) + R(x0, top, w, 2, C.teal, GL, 0.4);
        var last = i === hs.length - 1;
        var rf = K.roof(x0, x1, y - d, y, h, last ? { type: 'spire', tile: TILE.grey, ov: 5, up: 6, hr: 13, finial: 0 }
          : { type: 'hip', tile: TILE.grey, ov: 5 - i * 0.3, up: 6, hr: 4, inset: w / 2 - 6, ridge: 'plain', ridgeH: 1.5 });
        s += rf.svg;
        if (last) s += tasha(cx, rf.ridgeY + 1, 1);
        y = top - 1.5; w -= 4;
      });
      s += K.railing(cx - 29, cx + 29, yF + 1, 3, C.red);
      return s;
    }
  });

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

  defs.push({
    kind: 'paifang', variant: 1, name: '三间四柱牌坊', facility: null, category: 'prop', fp: [3, 1], up: 96,
    tags: ['gateway', 'landmark', 'street_arch'], roof: 'hip_tile',
    note: '街口 / 寺前 / 墓道的三间四柱五楼木牌坊：朱柱、抱鼓石、青绿额枋、中间匾额，明楼高、次楼低、两端边楼。FacilityKind 里没有牌坊，facility = null；放在墓道前也可作义冢入口（义冢正式版由 ⑥ 负责）。',
    draw: function (K, W, U, D) {
      var s = '', gy = U + 30, xs = [16, 52, 92, 128];
      s += P(K.pts([[8, gy - 3], [W - 8, gy - 3], [W - 4, gy + 4], [12, gy + 4]]), K.SH, null, 0, ' fill-opacity="0.2"');
      // 柱
      xs.forEach(function (x, i) {
        var top = (i === 1 || i === 2) ? gy - 74 : gy - 56;
        s += R(x - 2.8, top, 5.6, gy - top, C.red, GL, 0.8) + R(x - 3.6, gy - 4, 7.2, 4, C.stone, G, 0.6);
      });
      // 次间额枋 + 雀替 + 次楼
      [[xs[0], xs[1]], [xs[2], xs[3]]].forEach(function (p) {
        s += R(p[0], gy - 50, p[1] - p[0], 4, C.teal, GL, 0.6) + R(p[0], gy - 44, p[1] - p[0], 3, C.red, GL, 0.5) +
          R(p[0] + 4, gy - 49, p[1] - p[0] - 8, 2.4, C.tealLt) +
          P(K.pts([[p[0] + 2.8, gy - 41], [p[0] + 9, gy - 41], [p[0] + 2.8, gy - 36]]), C.ochre, G, 0.5) +
          P(K.pts([[p[1] - 2.8, gy - 41], [p[1] - 9, gy - 41], [p[1] - 2.8, gy - 36]]), C.ochre, G, 0.5);
        s += capRoof(p[0] - 2, p[1] + 2, gy - 53, { tile: TILE.teal });
      });
      // 明间：两道额枋夹匾额 + 明楼
      s += R(xs[1], gy - 66, xs[2] - xs[1], 4, C.teal, GL, 0.6) + R(xs[1], gy - 46, xs[2] - xs[1], 4, C.teal, GL, 0.6) +
        R(xs[1] + 4, gy - 45, xs[2] - xs[1] - 8, 2.2, C.tealLt) + R(xs[1], gy - 40, xs[2] - xs[1], 3, C.red, GL, 0.5);
      s += K.plaque((xs[1] + xs[2]) / 2, gy - 54, 24, 10, { chars: 2, bg: C.navy });
      s += P(K.pts([[xs[1] + 2.8, gy - 37], [xs[1] + 10, gy - 37], [xs[1] + 2.8, gy - 31]]), C.ochre, G, 0.5) +
        P(K.pts([[xs[2] - 2.8, gy - 37], [xs[2] - 10, gy - 37], [xs[2] - 2.8, gy - 31]]), C.ochre, G, 0.5);
      s += capRoof(xs[1] - 4, xs[2] + 4, gy - 69, { tile: TILE.teal, up: 8, hr: 8 });
      // 柱脚抱鼓石
      xs.forEach(function (x) { s += guShi(x - 5, gy + 1, 0.75) + guShi(x + 5, gy + 1, 0.75); });
      return s;
    }
  });

  // —— 导出 ——
  var API = { defs: defs, censer: censer, taiji: taiji, bagua: bagua, bellTower: bellTower, bell: bell, shanmen: shanmen, pennant: pennant, capRoof: capRoof };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.TownArtEastSpecialReligion = API;
})(typeof window !== 'undefined' ? window : this);
