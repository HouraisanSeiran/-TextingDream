/*
 * 织梦 · 西式城堡 —— 双网格瓦片：幕墙（castlewall）、护城河（moat）、内院地面（yard）。尚未接入游戏。
 *
 * 双网格：渲染瓦片 48×48，四角落在四个逻辑格中心；mask = NW*8 + NE*4 + SW*2 + SE*1。
 * 每个角象限（24×24）就是对应逻辑格的四分之一，所以墙 / 水 / 内院的边界只出现在瓦片中线上，
 * 正好穿过瓦片各边中点并垂直于该边；瓦片外沿永远是同一逻辑格的延续，相邻瓦片必然接得上。
 *
 * 幕墙用 6 px 小格的高度场画：每小格一个高度（0 地面、60 走道、70 垛、65 垛口），
 * 按行从北往南画顶面和朝南的立面（斜俯视里朝东 / 朝西的面没有宽度），墨线只画在高度不同的边上。
 * 垛口周期 12 px、石缝块长 16 px，都能整除 48，相邻瓦片纹理对齐。
 */
(function (root) {
  'use strict';
  var C = (typeof module !== 'undefined' && module.exports) ? require('./core.js') : root.TownArtWC.core;
  var PAL = C.PAL, f = C.f, P = C.P, rect = C.rect, path = C.path, seg = C.seg, lines = C.lines;
  var CS = 6, N = 8; // 小格边长、每边小格数
  var WALL = { h: 60, ph: 10, cut: 5, up: 72 };

  function bit(mask, q) { return (mask >> (3 - q)) & 1; } // q: 0 NW, 1 NE, 2 SW, 3 SE
  function bin4(m) { return ('000' + m.toString(2)).slice(-4); }
  function odd(n) { return ((n % 2) + 2) % 2 === 1; }

  /**
   * 小格 (i, j) 的邻接关系（i, j 可取 -1..8，瓦片外按同一逻辑格延续）。
   * 返回 { on, side, fb, corner }：on = 本象限是否有该材质；side / fb / corner = 是否贴着中线且对面没有该材质。
   */
  function cellInfo(mask, i, j) {
    var qx = i < 4 ? 0 : 1, qy = j < 4 ? 0 : 1, q = qy * 2 + qx;
    var on = !!bit(mask, q);
    var cx = (i === 3 || i === 4), cy = (j === 3 || j === 4);
    var hq = qy * 2 + (1 - qx), vq = (1 - qy) * 2 + qx, dq = (1 - qy) * 2 + (1 - qx);
    return {
      on: on, qx: qx, qy: qy,
      side: cx && !bit(mask, hq), fb: cy && !bit(mask, vq), corner: cx && cy && !bit(mask, dq),
      vqOn: !!bit(mask, vq)
    };
  }

  // ======================= 幕墙 =======================
  function wallHeight(mask, i, j) {
    var c = cellInfo(mask, i, j);
    if (!c.on) return 0;
    if (!c.side && !c.fb && !c.corner) return WALL.h;
    var emb;
    if (c.corner || (c.side && c.fb)) emb = false; // 转角一律是实垛
    else if (c.fb) emb = odd(i);                    // 前 / 后女墙：沿 x 方向交替
    else emb = odd(j);                              // 侧女墙：沿进深方向交替
    return WALL.h + WALL.ph - (emb ? WALL.cut : 0);
  }

  /**
   * 高度场渲染（斜俯视、只有朝南立面）。Hf(i, j) 给高度；paint 提供配色与纹理钩子。
   * 每行：先填顶面与南立面，再画这一行的墨线；后画的行自然盖住前面被挡住的部分。
   */
  function hfRender(Hf, up, paint) {
    var o = '';
    for (var j = 0; j < N; j++) {
      var Y = up + j * CS, fills = '', tex = '', d = '', i, x0;
      // ---- 填色（同高度、同南邻高度的相邻小格合成一段）
      i = 0;
      while (i < N) {
        var H = Hf(i, j), Hs = Math.min(Hf(i, j + 1), H);
        x0 = i;
        while (i < N && Hf(i, j) === H && Math.min(Hf(i, j + 1), Hf(i, j)) === Hs) i++;
        if (H <= 0) continue;
        var xa = x0 * CS, xb = i * CS;
        fills += rect(xa, Y - H, xb - xa, CS + 0.5, paint.top(H, j), 0);
        if (paint.topTex) tex += paint.topTex(xa, xb, Y - H, j, H);
        if (Hs < H) {
          fills += rect(xa, Y + CS - H, xb - xa, H - Hs + 0.4, paint.face(H, Hs), 0);
          if (paint.faceTex) tex += paint.faceTex(xa, xb, Y + CS - H, Y + CS - Hs, H, Hs, Y + CS);
        }
      }
      // ---- 墨线：北沿（与北邻高度不同处）
      for (i = 0; i < N; i++) {
        var h0 = Hf(i, j);
        if (Hf(i, j - 1) !== h0) d += seg(i * CS, Y - h0, (i + 1) * CS, Y - h0);
      }
      // ---- 墨线：左右两小格高度不同处的竖边
      for (i = 0; i <= N; i++) {
        var Ha = Hf(i - 1, j), Hb = Hf(i, j);
        var Sa = Math.min(Hf(i - 1, j + 1), Ha), Sb = Math.min(Hf(i, j + 1), Hb), x = i * CS;
        if (Ha !== Hb) d += seg(x, Y - Math.max(Ha, Hb), x, Y + CS - Math.min(Ha, Hb));
        if (Sa !== Sb) d += seg(x, Y + CS - Math.max(Sa, Sb), x, Y + CS - Math.min(Sa, Sb));
      }
      o += fills + tex + (paint.rowExtra ? paint.rowExtra(j, Y) : '') + (d ? path(d, 'none', 1.2) : '');
    }
    return o;
  }

  function wallPaint(mask) {
    var H = WALL.h;
    return {
      top: function (h) { return h > H ? PAL.plaster : PAL.st1; },
      face: function (h, hs) { return hs >= H ? PAL.st3 : PAL.st2; },
      // 走道石板：每 12 px 一道横缝，竖缝块长 16、隔排错半块（按世界坐标）
      topTex: function (xa, xb, y, j, h) {
        if (h !== H) return '';
        var dd = '', band = Math.floor(j / 2);
        if (j % 2 === 0) dd += seg(xa, y, xb, y);
        var off = odd(band) ? 8 : 0;
        for (var x = Math.ceil((xa - off) / 16) * 16 + off; x < xb; x += 16) if (x > xa) dd += seg(x, y, x, y + CS);
        return dd ? lines(dd, 0.7, 0.35) : '';
      },
      // 到地面的外立面：方整石 + 墙脚勒脚
      faceTex: function (xa, xb, yt, yb, h, hs, ground) {
        if (hs > 0 || yb - yt < 30) return '';
        var o = C.ashlar(xa, yt, xb - xa, yb - yt, C.CH, C.CW, 0, -ground);
        o += rect(xa, ground - 8, xb - xa, 8, PAL.st3, 0) + lines(seg(xa, ground - 8, xb, ground - 8), 1, 0.7);
        for (var x = Math.ceil(xa / 16) * 16 + 8; x < xb; x += 16) o += lines(seg(x, ground - 7.4, x, ground - 0.6), 0.8, 0.5);
        return o;
      },
      // 箭窗：每 24 px 一个，十字 / 直缝交替
      rowExtra: function (j, Y) {
        var o = '';
        [[1, 2, 12, true], [5, 6, 36, false]].forEach(function (s) {
          var a = wallHeight(mask, s[0], j), b = wallHeight(mask, s[1], j);
          if (a > H && b > H && wallHeight(mask, s[0], j + 1) === 0 && wallHeight(mask, s[1], j + 1) === 0) {
            o += C.arrowSlit(s[2], Y + CS - 46, 16, s[3]);
          }
        });
        return o;
      }
    };
  }

  /** 墙脚投影：墙东侧、南侧紧邻的一圈 6 px 地面（单一 path，避免半透明叠色）。 */
  function wallShadow(mask, up) {
    var d = '';
    for (var j = 0; j < N; j++) for (var i = 0; i < N; i++) {
      if (wallHeight(mask, i, j)) continue;
      if (wallHeight(mask, i, j - 1) || wallHeight(mask, i - 1, j) || wallHeight(mask, i - 1, j - 1)) d += C.rectD(i * CS, up + j * CS, CS, CS);
    }
    return d ? C.shadow(d) : '';
  }

  function wallTile(mask) {
    var up = WALL.up, body = '';
    if (mask) {
      var Hf = function (i, j) { return wallHeight(mask, i, j); };
      body = wallShadow(mask, up) + hfRender(Hf, up, wallPaint(mask));
    }
    return {
      id: 'west-common-castlewall-' + bin4(mask), category: 'wall', kind: 'castle_wall', facility: 'city_wall',
      variant: mask, footprint: [1, 1], up: up, tags: ['dual_grid', 'mask_' + bin4(mask)], roof: 'none',
      note: mask ? '幕墙双网格瓦片：走道高 60 px、垛高 10 px，厚一整格' : '空瓦片（透明占位）',
      body: body
    };
  }

  // ======================= 护城河 =======================
  // 水面低于地面：北岸露出一段石砌驳岸立面（朝南）；四周岸顶一圈压顶条石。瓦片不向上伸出。
  var BANK = { face: 11, cope: 4 };
  function quadRect(q) { return [(q & 1) * 24, (q >> 1) * 24]; }
  function moatTile(mask) {
    if (!mask) return { body: '', up: 0, w: 48, h: 48 };
    var o = '', wd = '', i, q;
    for (q = 0; q < 4; q++) if (bit(mask, q)) { var r0 = quadRect(q); wd += C.rectD(r0[0], r0[1], 24, 24); }
    o += path(wd, PAL.water, 0);
    // 水纹：按世界坐标每 12 px 一格的短浪，逐行错开半格（48 的约数，跨瓦片对齐）
    var tex = '', hi = '';
    for (var y = 4; y < 48; y += 8) {
      var off = ((y / 8) | 0) % 2 ? 6 : 0;
      for (var x = off + 2; x < 48; x += 12) {
        var qq = (y < 24 ? 0 : 2) + (x + 4 < 24 ? 0 : 1);
        if (!bit(mask, qq) || (x < 24 && x + 8 > 24)) continue;
        tex += 'M' + P(x, y + 1.2) + 'Q' + P(x + 2, y - 1) + ' ' + P(x + 4, y + 1.2) + 'Q' + P(x + 6, y - 1) + ' ' + P(x + 8, y + 1.2);
      }
    }
    o += path(tex, 'none', 0.8, 0.4);
    // 北岸驳岸立面（水面象限的北邻是岸）与其下方一道暗水带
    var face = '', dark = '', cope = '', edge = '', outer = '';
    for (q = 0; q < 4; q++) {
      if (!bit(mask, q)) continue;
      var r = quadRect(q);
      if (q >= 2 && !bit(mask, q - 2)) { face += C.rectD(r[0], 24, 24, BANK.face); dark += C.rectD(r[0], 24 + BANK.face, 24, 3); }
    }
    if (dark) o += path(dark, PAL.water2, 0);
    if (face) {
      o += path(face, PAL.st2, 0);
      // 立面石缝：层高 5.5、块长 12，左右按世界坐标对齐
      var fd = '';
      for (q = 2; q < 4; q++) if (bit(mask, q) && !bit(mask, q - 2)) {
        var x0 = (q & 1) * 24;
        fd += seg(x0, 29.5, x0 + 24, 29.5);
        for (var xx = x0 + 6; xx < x0 + 24; xx += 12) fd += seg(xx, 24.5, xx, 29);
        for (var xx2 = x0; xx2 < x0 + 24; xx2 += 12) if (xx2 > x0 || xx2 % 48 !== 0) fd += seg(xx2, 30, xx2, 34.5);
        fd += seg(x0 + 12, 30, x0 + 12, 34.5);
        edge += seg(x0, 24 + BANK.face, x0 + 24, 24 + BANK.face);
      }
      o += lines(fd, 0.8, 0.5) + path(edge, 'none', 1, 0.8);
    }
    // 岸顶压顶条石：陆地象限里贴着水面的 4 px 宽条，块长 8；对角只连水时补一个角块
    function landQ(qq) { return !bit(mask, qq); }
    var c = BANK.cope, jd = '';
    for (q = 0; q < 4; q++) {
      if (!landQ(q)) continue;
      var rq = quadRect(q), qx = q & 1, qy = q >> 1;
      var hq = q ^ 1, vq = q ^ 2, dq = q ^ 3;
      var hx = qx ? 24 : 24 - c;          // 贴竖中线的条
      var vy = qy ? 24 : 24 - c;          // 贴横中线的条
      if (!landQ(hq)) { cope += C.rectD(hx, rq[1], c, 24); edge += seg(24, rq[1], 24, rq[1] + 24); outer += seg(qx ? 24 + c : 24 - c, rq[1], qx ? 24 + c : 24 - c, rq[1] + 24); for (var yy = rq[1] + 8; yy < rq[1] + 24; yy += 8) jd += seg(hx, yy, hx + c, yy); }
      if (!landQ(vq)) { cope += C.rectD(rq[0], vy, 24, c); edge += seg(rq[0], 24, rq[0] + 24, 24); outer += seg(rq[0], qy ? 24 + c : 24 - c, rq[0] + 24, qy ? 24 + c : 24 - c); for (var x3 = rq[0] + 8; x3 < rq[0] + 24; x3 += 8) jd += seg(x3, vy, x3, vy + c); }
      if (!landQ(dq) && landQ(hq) && landQ(vq)) {
        cope += C.rectD(hx, vy, c, c);
        outer += seg(qx ? 24 + c : 24 - c, vy, qx ? 24 + c : 24 - c, vy + c) + seg(hx, qy ? 24 + c : 24 - c, hx + c, qy ? 24 + c : 24 - c);
        edge += seg(24, qy ? 24 : 24 - c, 24, qy ? 24 + c : 24) + seg(qx ? 24 : 24 - c, 24, qx ? 24 + c : 24, 24);
      }
    }
    if (cope) o += path(cope, PAL.st1, 0) + lines(jd, 0.8, 0.5) + path(outer, 'none', 0.9, 0.75);
    o += path(edge, 'none', 1.5);
    return { body: o, up: 0, w: 48, h: 48 };
  }

  // ======================= 内院石板地 =======================
  // 每个逻辑格用同一套 48×48 石板排布（以格中心为原点），所以任意拼接都无缝。
  var FLAGS = (function () {
    var r = C.rng(C.seedOf('west-castle-yard')), rows = [0, 11, 23, 36, 48], out = [];
    for (var k = 0; k < 4; k++) {
      var x = -r() * 10, y0 = rows[k], y1 = rows[k + 1];
      while (x < 48) { var w = 10 + r() * 9; out.push([x, y0, w, y1 - y0]); x += w; }
    }
    return out;
  })();
  function yardTile(mask) {
    if (!mask) return { body: '', up: 0, w: 48, h: 48 };
    var o = '', fill = '', jd = '', curb = '', edge = '', q;
    for (q = 0; q < 4; q++) {
      if (!bit(mask, q)) continue;
      var r = quadRect(q);
      fill += C.rectD(r[0], r[1], 24, 24);
      // 该象限属于以瓦片角 (cx, cy) 为中心的逻辑格；逻辑格左上角 = (cx-24, cy-24)
      var cx = (q & 1) * 48, cy = (q >> 1) * 48, lx = cx - 24, ly = cy - 24;
      FLAGS.forEach(function (s) {
        var x0 = Math.max(r[0], lx + s[0]), x1 = Math.min(r[0] + 24, lx + s[0] + s[2]);
        var y0 = Math.max(r[1], ly + s[1]), y1 = Math.min(r[1] + 24, ly + s[1] + s[3]);
        if (x1 - x0 < 0.5 || y1 - y0 < 0.5) return;
        if (Math.abs(x1 - (lx + s[0] + s[2])) < 0.01 && x1 < r[0] + 23.5) jd += seg(x1, y0, x1, y1);
        if (Math.abs(y1 - (ly + s[1] + s[3])) < 0.01 && y1 < r[1] + 23.5) jd += seg(x0, y1, x1, y1);
      });
    }
    o += path(fill, PAL.st1, 0) + lines(jd, 0.8, 0.45);
    // 边缘：贴着中线的一道路缘石（在院内一侧）
    for (q = 0; q < 4; q++) {
      if (!bit(mask, q)) continue;
      var rq = quadRect(q), qx = q & 1, qy = q >> 1;
      if (!bit(mask, q ^ 1)) { var ex = qx ? 24 : 21; curb += C.rectD(ex, rq[1], 3, 24); edge += seg(24, rq[1], 24, rq[1] + 24); }
      if (!bit(mask, q ^ 2)) { var ey = qy ? 24 : 21; curb += C.rectD(rq[0], ey, 24, 3); edge += seg(rq[0], 24, rq[0] + 24, 24); }
    }
    if (curb) o += path(curb, PAL.st3, 0);
    if (edge) o += path(edge, 'none', 1.3);
    return { body: o, up: 0, w: 48, h: 48 };
  }

  var API = { WALL: WALL, bit: bit, bin4: bin4, wallHeight: wallHeight, hfRender: hfRender, wallTile: wallTile, moatTile: moatTile, yardTile: yardTile };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else { root.TownArtWC = root.TownArtWC || {}; root.TownArtWC.walls = API; }
})(this);
