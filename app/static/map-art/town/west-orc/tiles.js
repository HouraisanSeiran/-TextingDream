/*
 * 织梦 · 兽人族尖木栅墙双网格瓦片 × 16 + 栅门 gate-h / gate-v（美术样板，尚未接入游戏）
 * 四角编码 mask = NW*8 + NE*4 + SW*2 + SE*1。瓦片内部坐标 0..48（y 向下），四角 = 四个逻辑格中心。
 * 栅墙沿逻辑格中心线走（= 渲染瓦片的边）。为了相邻瓦片不重复画同一根桩，按「归属」画：
 *   每张瓦片只画 SW 角的角柱、SW→SE（底边 = 前沿）与 NW→SW（左边）两段上的木桩；其余两边的桩归相邻瓦片。
 *   这样每段桩都由锚点最靠前的那块瓦片画，深度排序正确。桩距 4 px 整除 48，拼起来一定连续。
 *   地面土垄按四角象限画（与 west-base 的 12 px 小格一致）。
 * 栅门是「替换瓦片」：gate-h 替换东西向直段 wall-0011（门在底边那段墙上），gate-v 替换南北向直段 wall-1010（门在左边那段墙上）。
 *   门自带地面与角柱，锚点与被替换的瓦片相同，所以不存在同锚点的遮挡先后问题；门洞跨在两个相邻墙格之间。
 * 浏览器挂 window.TownArtWO_tiles；Node 用 module.exports。依赖 core.js、parts.js、forms.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWO_core;
  var K = isNode ? require('./parts.js') : root.TownArtWO_parts;
  var F = isNode ? require('./forms.js') : root.TownArtWO_forms;
  var P = C.PAL, f = C.f, S = 48, G = 12, STEP = 4, H = 33, SW_ = 4.8;
  // 桩高与色按序号循环（周期 12 根 = 48 px），保证同一位置在任何瓦片里长得一样
  var DH = [0, 2, -1, 1, 3, -2, 1, 0, 2, -1, 3, 0];
  var TONE = [P.wood, '#bf9a60', '#b48e58', P.wood, '#b48e58', '#c4a068'];
  function bin(m) { return ('000' + m.toString(2)).slice(-4); }

  /** 4×4 小格占用（同 west-base）：用于地面土垄 */
  function cells(mask) {
    var g = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]];
    var nw = mask & 8, ne = mask & 4, sw = mask & 2, se = mask & 1;
    if (nw) g[0][0] = 1; if (ne) g[0][3] = 1; if (sw) g[3][0] = 1; if (se) g[3][3] = 1;
    if (nw && ne) g[0][1] = g[0][2] = 1;
    if (sw && se) g[3][1] = g[3][2] = 1;
    if (nw && sw) g[1][0] = g[2][0] = 1;
    if (ne && se) g[1][3] = g[2][3] = 1;
    if (mask === 15) g[1][1] = g[1][2] = g[2][1] = g[2][2] = 1;
    return g;
  }
  /** 一根桩：底中心 (x, yb)，序号 k 决定高与色 */
  function stakeK(x, yb, k) {
    var h = H + DH[k % 12], w = SW_;
    var s = K.stake(x - w / 2, yb, w, h, TONE[k % TONE.length], 1);
    s += C.rect(x + w * 0.18, yb - h + 0.6, w * 0.32 - 0.4, h - 1.2, P.dark, 0, 0.22); // 右侧阴面
    return s;
  }
  /** 南北向墙段的桩（正视只见一列桩头）：更宽、左亮右暗，读作一条墙带 */
  function stakeV(x, yb, k) {
    var h = H + DH[k % 12], w = 6.6;
    var s = K.stake(x - w / 2, yb, w, h, TONE[k % TONE.length], 1);
    s += C.path(C.poly([[x + 0.3, yb - 0.6], [x + 0.3, yb - h], [x + w * 0.42, yb - h + 0.4], [x + w * 0.42, yb - 0.6]]), P.dark, 0, 0.3);
    return s;
  }
  /** 南北向一列桩：y 从 ya 到 yb2（不含端点），每 4 px 一根，绳扎两道 */
  function colV(ya, yb2, k0) {
    var s = '';
    for (var y = Math.ceil((ya + 0.01) / STEP) * STEP; y < yb2 - 0.01; y += STEP) {
      var k = y / STEP + k0;
      s += stakeV(0, y, k);
      if (k % 3 === 0) s += K.knot(0, y - 14, 6.6, 1);
    }
    return s;
  }
  /** 角柱：更粗更高，绳扎 + 一对短角 */
  function post(ctx, x, yb) {
    var w = 7, h = H + 7, s = K.stake(x - w / 2, yb, w, h, P.timber, 1.3);
    s += C.rect(x + 0.6, yb - h + 0.6, w / 2 - 1, h - 1.2, P.dark, 0, 0.25);
    s += K.knot(x, yb - h * 0.62, w, 3) + K.knot(x, yb - 9, w, 2);
    s += K.horn(x - 2, yb - h + 2, 5, -1, 1) + K.horn(x + 2, yb - h + 2, 5, 1, 1);
    ctx.top(yb - h - w * 1.1 - 5);
    return s;
  }
  function wallTile(ctx, mask) {
    if (!mask) return '';
    var g = cells(mask), ground = '', shade = '', s = '', cx, cy;
    for (cy = 0; cy < 4; cy++) for (cx = 0; cx < 4; cx++) {
      if (!g[cy][cx]) continue;
      ground += C.rect(cx * G, cy * G, G, G, P.soil2, 0, 0.42);
    }
    // 土垄边上散几块石头（按小格位置固定）
    var pebble = '';
    for (cy = 0; cy < 4; cy++) for (cx = 0; cx < 4; cx++) if (g[cy][cx] && (cx * 3 + cy * 5) % 4 === 1)
      pebble += C.ell(cx * G + 8, cy * G + 9, 1.6, 1.1, P.stone2, 0.6);
    var nw = mask & 8, sw = mask & 2, se = mask & 1, k;
    var bot = !!(sw && se), left = !!(nw && sw);
    if (bot) shade += C.shadowD(C.rectD(2, 48, 48, 4.5));
    if (left) shade += C.shadowD(C.rectD(2.4, 0, 5.5, 48));
    s += ground + pebble + shade;
    // 由后往前：左边一列（y 递增），再底边一排，最后 SW 角柱
    if (left) s += colV(0, 48, 5);
    if (bot) {
      for (k = 1; k < 12; k++) s += stakeK(k * STEP, 48, k);
      s += K.rope('M1 36H47') + K.rope('M1 23.5H47');
      s += K.skull(24, 26.5, 0.6); // 每段墙中间挂一颗头骨
    }
    if (sw) s += post(ctx, 0, 48);
    if (left) ctx.top(STEP - H - 3 - SW_ * 1.1 - 1);
    return s;
  }

  /** 栅门门柱：粗原木，底 (x, yb)，高 h，顶插长角兽头骨 */
  function gatePost(ctx, x, yb, h) {
    var w = 8, s = K.stake(x - w / 2, yb, w, h, P.timber, 1.4);
    s += C.rect(x + 0.6, yb - h + 0.6, w / 2 - 1, h - 1.2, P.dark, 0, 0.25);
    s += K.knot(x, yb - h * 0.35, w, 3) + K.knot(x, yb - h * 0.7, w, 2);
    s += K.hornSkull(x, yb - h - w * 1.1 - 2, 0.62, 8);
    ctx.top(yb - h - w * 1.1 - 12);
    return s;
  }
  /** 一扇尖桩门扇（正视）：x0..x1，底 yb，高 h */
  function leaf(x0, x1, yb, h) {
    var s = '';
    for (var x = x0; x < x1 - 1; x += 3.6) s += K.stake(x, yb, 3.6, h, x % 7.2 < 3.6 ? P.wood : '#b48e58', 0.8);
    var bar = 'M' + f(x0) + ' ' + f(yb - h * 0.3) + 'H' + f(x1) + 'M' + f(x0) + ' ' + f(yb - h * 0.72) + 'H' + f(x1) + 'M' + f(x0 + 1) + ' ' + f(yb - h * 0.3) + 'L' + f(x1 - 1) + ' ' + f(yb - h * 0.72);
    return s + C.line(bar, 2.2) + C.line(bar, 0.9, 1, P.timber);
  }
  /** 门楼：横梁上搭小平台 + 兽皮小顶 + 骨串；x0..x1，横梁底 y */
  function loft(ctx, x0, x1, y, wide) {
    var s = C.path(C.wob(ctx, [[x0 - 3, y], [x1 + 3, y], [x1 + 4, y - 6], [x0 - 2, y - 6]], 0.4), P.timber, 1.4);
    s += C.line('M' + f(x0) + ' ' + f(y - 3) + 'H' + f(x1), 0.7, 0.6);
    var n = Math.round((x1 - x0) / 7);
    for (var i = 0; i < n; i++) s += K.skull(x0 + (x1 - x0) * (i + 0.5) / n, y + 3, 0.42);
    // 平台护栏尖桩
    for (var x = x0 - 1; x < x1; x += 4) s += K.stake(x, y - 6, 3.2, 6, P.wood, 0.7);
    s += F.roofFront(ctx, { x0: x0 + 2, x1: x1 - 2, yE: y - 13, R: wide ? 10 : 8, Dp: 8, mat: 'hide', ov: 2 }).svg;
    s += K.pole(x0 + 3, y - 6, 8, 2) + K.pole(x1 - 3, y - 6, 8, 2);
    return s;
  }
  // gate-h：替换 wall-0011。底边墙段中间开门：两根门柱 + 敞开的两扇尖桩门 + 门楼
  function gateH(ctx) {
    var s = '', yb = 48, xL = 11, xR = 37;
    s += C.rect(0, 36, 48, 12, P.soil2, 0, 0.42) + C.rect(xL + 4, 30, xR - xL - 8, 18, P.soil, 0, 0.6);
    s += C.shadowD(C.rectD(2, 48, 48, 4.5));
    // 门外两侧短墙段（与 0011 的桩位一致）
    var k;
    for (k = 1; k * STEP < xL - 3; k++) s += stakeK(k * STEP, yb, k);
    for (k = 11; k * STEP > xR + 3; k--) s += stakeK(k * STEP, yb, k);
    s += K.rope('M1 36H' + f(xL - 3)) + K.rope('M' + f(xR + 3) + ' 36H47');
    s += C.path(C.rectD(xL + 3, yb - 30, xR - xL - 6, 30), P.hole, 0, 0.85);
    // 两扇门向内敞开（只露窄边，斜向后上）
    s += C.path(C.poly([[xL + 4, yb], [xL + 9, yb - 7], [xL + 9, yb - 33], [xL + 4, yb - 28]]), '#b48e58', 1) +
      C.path(C.poly([[xR - 4, yb], [xR - 9, yb - 7], [xR - 9, yb - 33], [xR - 4, yb - 28]]), P.wood, 1);
    s += gatePost(ctx, xL, yb, 44) + gatePost(ctx, xR, yb, 44);
    s += loft(ctx, xL - 2, xR + 2, yb - 34, true);
    s += post(ctx, 0, 48);
    return s;
  }
  // gate-v：替换 wall-1010。左边（南北向）墙段中间开门，门洞朝东西：正视只见门柱侧影与一扇向东敞开的门扇
  function gateV(ctx) {
    var s = '', yT = 13, yB = 37;
    s += C.rect(0, 0, 12, 48, P.soil2, 0, 0.42) + C.rect(-12, yT + 4, 30, yB - yT - 6, P.soil, 0, 0.5);
    s += C.shadowD(C.rectD(2.4, 0, 5.5, yT)) + C.shadowD(C.rectD(2.4, yB, 5.5, 48 - yB));
    s += colV(0, yT - 3, 5);
    s += gatePost(ctx, 0, yT, 40);
    // 门洞地面（东西向通道，左右各伸出一点）
    s += C.path(C.rectD(-10, yT + 3, 26, yB - yT - 6), P.hole, 0, 0.25);
    // 门楣：从后门柱顶到前门柱顶的一根横梁（南北向，正视是一段竖梁），挂骨串
    var lt = 'M0 ' + f(yT - 36) + 'L0 ' + f(yB - 36);
    s += C.line(lt, 6.4) + C.line(lt, 4, 1, P.timber) + K.knot(0, yT - 33, 6, 2) + K.knot(0, yB - 39, 6, 2);
    s += K.boneString(ctx, 3, yT - 30, 3, yB - 34, 4);
    // 向东敞开的一扇门（正视全宽）
    s += leaf(5, 23, yB - 3, 24);
    s += colV(yB + 3, 48, 5);
    s += gatePost(ctx, 0, yB, 40);
    // 门楼：脊沿南北向的兽皮小顶，正视是山墙朝前 + 屋面向后退，两门柱都罩在下面
    s += F.roofFront(ctx, { x0: -11, x1: 11, yE: yB - 44, R: 9, Dp: yB - yT, mat: 'hide', ov: 2 }).svg;
    s += K.hornSkull(0, yB - 49, 0.7, 9);
    // 门洞两侧的骨饰门牌，读作「此处可通行」
    s += K.tusk(-6, yB - 2, 10, -1) + K.tusk(6, yB - 2, 10, 1);
    s += post(ctx, 0, 48);
    return s;
  }

  function all(wrap) {
    var out = [], m;
    for (m = 0; m < 16; m++) {
      var id = 'west-orc-wall-' + bin(m), ctx = new C.Ctx(id);
      var body = '<g transform="translate(0 -48)">' + wallTile(ctx, m) + '</g>';
      out.push(wrap(id, [1, 1], body, Math.min(-48, ctx.minY - 48), {
        id: id, style: 'west', race: 'orc', category: 'wall', kind: 'wall_palisade', facility: m ? 'city_wall' : null, variant: m, mask: m,
        name: '尖木栅墙 ' + bin(m), tags: ['dual_grid', 'mask_' + bin(m), 'palisade'], roof: 'none',
        note: m === 0 ? '空瓦片（透明占位）' : '双网格渲染瓦片：四角落在逻辑格中心；每块只画 SW 角柱、底边与左边的桩'
      }));
    }
    [['west-orc-gate-h', '骨饰栅门（东西向）', gateH, '0011', 'gate_h'], ['west-orc-gate-v', '骨饰栅门（南北向）', gateV, '1010', 'gate_v']].forEach(function (g, i) {
      var ctx = new C.Ctx(g[0]), body = '<g transform="translate(0 -48)">' + g[2](ctx) + '</g>';
      out.push(wrap(g[0], [1, 1], body, Math.min(-48, ctx.minY - 48), {
        id: g[0], style: 'west', race: 'orc', category: 'wall', kind: 'gate_palisade', facility: 'gate', variant: i + 1,
        name: g[1], tags: ['dual_grid', 'replaces_' + g[3], g[4], 'bone'], roof: 'none',
        note: '替换瓦片：放在 mask=' + g[3] + ' 的位置代替 west-orc-wall-' + g[3]
      }));
    });
    return out;
  }

  var API = { all: all, wallTile: wallTile, gateH: gateH, gateV: gateV, cells: cells, bin: bin };
  root.TownArtWO_tiles = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
