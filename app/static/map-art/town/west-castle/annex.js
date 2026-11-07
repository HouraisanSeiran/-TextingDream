/*
 * 织梦 · 西式城堡 —— 内院建筑：大厅、礼拜堂、兵营、厨房、粮仓、马厩、铁匠棚、井。尚未接入游戏。
 * 返回格式同 keep.js；内部 clipPath id 用 "__ID__" 占位。
 * 附属建筑尺度比城镇版小：马厩、铁匠棚是贴着幕墙内侧的单坡披屋（进深 1 格）。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  var C = isNode ? require('./core.js') : root.TownArtWC.core;
  var PAL = C.PAL, rect = C.rect, path = C.path, seg = C.seg, lines = C.lines, poly = C.poly, f = C.f, P = C.P;

  function rec(id, kind, facility, fp, up, tags, roof, note, body) {
    return { id: id, category: 'castle', kind: kind, facility: facility, variant: 1, footprint: fp, up: up, tags: tags, roof: roof, note: note, body: body };
  }

  /** 阶梯扶壁（正面看）：x 处宽 w，从 yTop 到 yBot，两道斜收的披水。 */
  function buttress(x, w, yTop, yBot) {
    var ym = yTop + (yBot - yTop) * 0.45, o = '';
    o += rect(x, ym, w, yBot - ym, PAL.st1, 1) + C.ashlar(x, ym, w, yBot - ym, 8, 12, 0, 0, 0.4);
    o += rect(x + 1.5, yTop + 4, w - 3, ym - yTop - 4, PAL.st1, 1);
    o += poly([[x, ym], [x + w, ym], [x + w - 1.5, ym - 4], [x + 1.5, ym - 4]], PAL.st3, 0.9);
    o += poly([[x + 1.5, yTop + 4], [x + w - 1.5, yTop + 4], [x + w / 2, yTop - 1]], PAL.st3, 0.9);
    return o;
  }
  /** 烟囱：x0..x1，从 yBot 起高 hh；顶上压檐石和一缕烟。 */
  function chimney(x0, x1, yBot, hh, smoke) {
    var yt = yBot - hh, o = rect(x0, yt, x1 - x0, hh, PAL.st2, 1.2) + C.ashlar(x0, yt, x1 - x0, hh, 5, 7, 0, 0, 0.45);
    o += rect(x0 - 1.5, yt - 3, x1 - x0 + 3, 3.5, PAL.st1, 1) + rect(x0 + 1.5, yt - 4.5, x1 - x0 - 3, 1.6, PAL.hole, 0.6);
    if (smoke) {
      var cx = (x0 + x1) / 2;
      o += path('M' + P(cx, yt - 6) + 'C' + P(cx - 6, yt - 12) + ' ' + P(cx + 6, yt - 17) + ' ' + P(cx, yt - 23) +
        'C' + P(cx - 5, yt - 28) + ' ' + P(cx + 5, yt - 31) + ' ' + P(cx + 1, yt - 36), 'none', 1, 0.45);
    }
    return o;
  }
  /** 单坡披屋顶（monopitch）：背高 hb（后沿 g0）、前低 hf（前沿 g1）。 */
  function monoRoof(up, x0, x1, g0, g1, hb, hf, fill, rowsStep, vertical) {
    var yB = up + g0 - hb, yF = up + g1 - hf + 2;
    var d = C.pts([[x0, yB], [x1, yB], [x1, yF], [x0, yF]]);
    return { svg: path(d, fill, 1.4) + C.roofRows(d, x0, yB, x1, yF, rowsStep || 5, !!vertical, 0.45) + path(seg(x0, yF, x1, yF), 'none', 1.8), yB: yB, yF: yF };
  }

  /** 大厅（great hall）：4×2。石墙、成对尖拱高窗、阶梯扶壁、居中门廊、陡坡青石板顶、屋脊排烟亭与端烟囱。 */
  function greatHall() {
    var up = 64, x0 = 8, x1 = 184, g0 = 10, g1 = 88, hw = 58, rh = 30, o = '';
    var yb = up + g1, yw = up + g1 - hw;
    o += C.dropShadow(x0, x1, yw - 20, yb, 192, up + 96);
    o += C.stoneFace(x0, x1, yw, yb, PAL.st2);
    o += rect(x0, yb - 8, x1 - x0, 8, PAL.st3, 1) + lines(C.hatchD(x0, x1, yb - 7.5, yb - 0.5, 16), 0.8, 0.4);
    // 高窗：每开间一对尖拱窗，窗台一道石线
    var bays = [30, 62, 130, 162];
    bays.forEach(function (x) { o += C.windowA(x - 7, yw + 9, 14, 30, true, true); });
    o += path(seg(x0, yw + 41, x1, yw + 41), 'none', 1, 0.7);
    // 扶壁
    [x0, 44, 78, 108, 142, x1 - 8].forEach(function (x) { o += buttress(x, 8, yw + 8, yb); });
    // 门廊：小山墙门头 + 尖拱门 + 台阶
    var px0 = 84, px1 = 104;
    o += rect(px0, yw + 16, px1 - px0, yb - yw - 16, PAL.st1, 1.2);
    o += poly([[px0 - 2, yw + 17], [94, yw + 4], [px1 + 2, yw + 17]], PAL.sl1, 1.2);
    o += C.doorA(88, yb - 3, 12, 22, true);
    o += C.shield(94, yw + 23, 3.6, PAL.red, 'chevron');
    o += rect(84, yb - 3, 20, 3, PAL.st3, 1);
    // 屋顶
    var r = C.gableX(up, x0, x1, g0, g1, hw, rh, PAL.sl1, PAL.sl2, 4);
    o += r.svg;
    // 端烟囱（东端，后坡上冒出）
    o += chimney(160, 172, r.ridge + 8, 26, true);
    // 屋脊排烟亭：小木亭 + 小坡顶
    var lx = 92, ly = r.ridge;
    o += rect(lx - 7, ly - 11, 14, 11, PAL.wood, 1.1) + lines(C.hatchD(lx - 7, lx + 7, ly - 10, ly - 1, 3.5), 0.7, 0.55);
    o += poly([[lx - 10, ly - 10], [lx, ly - 19], [lx + 10, ly - 10]], PAL.sl2, 1.2);
    o += path(seg(lx, ly - 19, lx, ly - 24), 'none', 1.2) + C.ell(lx, ly - 25, 1.5, 1.5, PAL.wash, 0.7);
    // 西端山墙顶的十字小尖饰
    o += path(seg(x0 - 2, r.ridge, x0 - 2, r.ridge - 8) + seg(x0 - 5, r.ridge - 5, x0 + 1, r.ridge - 5), 'none', 1.4);
    return rec('west-common-greathall-01', 'great_hall', 'lord_hall', [4, 2], up,
      ['great_hall', 'stone', 'lancet_windows', 'buttress', 'louver', 'chimney'], 'steep_slate',
      '城堡大厅：长条石砌厅堂，成对尖拱高窗，陡坡青石板顶，屋脊排烟亭', o);
  }

  /** 城堡礼拜堂：2×3，山墙朝前。玫瑰窗、尖拱门、两侧尖窗、角扶壁、山尖钟架（钟 + 十字）。 */
  function chapel() {
    var up = 84, x0 = 14, x1 = 82, g0 = 14, g1 = 136, hw = 46, rh = 34, o = '';
    var yb = up + g1, yw = yb - hw;
    o += C.dropShadow(x0, x1, up + g0 - hw - rh, yb, 96, up + 144);
    var gr = C.gableG(up, x0, x1, g0, g1, hw, rh, PAL.sl1, PAL.sl2, 4);
    o += gr.svg;
    // 后山墙尖上的小十字
    o += path(seg(48, up + g0 - hw - rh, 48, up + g0 - hw - rh - 7) + seg(45, up + g0 - hw - rh - 4.5, 51, up + g0 - hw - rh - 4.5), 'none', 1.3);
    // 前立面
    o += C.stoneFace(x0, x1, yw, yb, PAL.st2);
    o += C.gableFront(gr, x0, x1, PAL.st2);
    o += rect(x0, yb - 7, x1 - x0, 7, PAL.st3, 1);
    // 玫瑰窗（山墙里）：石框圆 + 深色 + 六瓣花格
    var rx = 48, ryy = gr.base - 11, rr = 7.5, pd = '';
    o += C.ell(rx, ryy, rr + 2, rr + 2, PAL.st1, 1) + C.ell(rx, ryy, rr, rr, PAL.hole, 1);
    for (var k = 0; k < 6; k++) { var a = k * Math.PI / 3; pd += seg(rx, ryy, rx + rr * Math.cos(a), ryy + rr * Math.sin(a)); }
    o += '<path d="' + pd + '" fill="none" stroke="' + PAL.wash + '" stroke-width="1.1" stroke-linecap="round"/>' + C.ell(rx, ryy, rr, rr, 'none', 1) + C.ell(rx, ryy, 2.4, 2.4, PAL.wash, 0.7);
    // 尖拱门 + 两侧尖窗 + 门上一道山形门头
    o += C.doorA(41, yb - 4, 14, 26, true);
    o += path('M' + P(38, yb - 31) + 'L' + P(48, yb - 41) + 'L' + P(58, yb - 31), 'none', 1.3);
    [26, 70].forEach(function (x) { o += C.windowA(x - 4, yw + 8, 8, 22, true, false); });
    o += rect(37, yb - 4, 22, 4, PAL.st1, 1);
    // 角扶壁
    o += buttress(x0, 7, yw + 4, yb) + buttress(x1 - 7, 7, yw + 4, yb);
    // 山尖钟架：小石山墙 + 拱洞 + 钟 + 十字
    var ax = gr.apex[0], ay = gr.apex[1];
    o += poly([[ax - 9, ay + 6], [ax - 9, ay - 12], [ax, ay - 21], [ax + 9, ay - 12], [ax + 9, ay + 6]], PAL.st1, 1.2);
    o += path(C.archD(ax - 4.5, ay - 12, 9, 14), PAL.hole, 1);
    o += path('M' + P(ax - 3.4, ay + 1) + 'Q' + P(ax - 3, ay - 7) + ' ' + P(ax, ay - 7.5) + 'Q' + P(ax + 3, ay - 7) + ' ' + P(ax + 3.4, ay + 1) + 'Z', PAL.wash, 0.9);
    o += path(seg(ax, ay - 21, ax, ay - 31) + seg(ax - 4, ay - 27, ax + 4, ay - 27), 'none', 1.6);
    return rec('west-common-chapel-01', 'chapel', 'temple', [2, 3], up,
      ['chapel', 'stone', 'rose_window', 'bell_cote', 'lancet_windows', 'cross'], 'steep_slate',
      '城堡礼拜堂：山墙朝前，玫瑰窗、尖拱门、山尖钟架；青石板陡坡顶', o);
  }

  /** 兵营：3×2。石砌底层（箭窗、拱门、兵器架、挂盾）+ 半木结构二层（带护窗板的小窗）+ 红瓦双坡顶 + 烟囱。 */
  function barracks() {
    var up = 80, x0 = 8, x1 = 136, g0 = 10, g1 = 90, hw = 52, o = '';
    var yb = up + g1, yw = yb - hw, ys = yb - 24;
    o += C.dropShadow(x0, x1, yw - 20, yb, 144, up + 96);
    o += C.stoneFace(x0, x1, ys, yb, PAL.st2);
    o += C.timberFace(x0, x1, yw, ys, true);
    o += path(seg(x0, ys, x1, ys), 'none', 1.8);
    [24, 52, 92, 120].forEach(function (x) {
      o += rect(x - 4.5, yw + 7, 9, 10, PAL.hole, 1) + rect(x - 9.5, yw + 7, 5, 10, PAL.grain, 0.9) + rect(x + 4.5, yw + 7, 5, 10, PAL.grain, 0.9) +
        lines(seg(x, yw + 7, x, yw + 17) + seg(x - 4.5, yw + 12, x + 4.5, yw + 12), 0.8, 0.7);
    });
    [28, 116].forEach(function (x) { o += C.arrowSlit(x, ys + 5, 12, false); });
    o += C.doorA(65, yb, 14, 19, false);
    // 兵器架：两道横杆 + 三支长矛
    o += path(seg(84, yb - 20, 108, yb - 20) + seg(84, yb - 8, 108, yb - 8) + seg(85, yb - 21, 85, yb - 1) + seg(107, yb - 21, 107, yb - 1), 'none', 1.4);
    [90, 96, 102].forEach(function (x, i) {
      var lean = (i - 1) * 1.2;
      o += path(seg(x, yb - 2, x + lean, yb - 32), 'none', 1.1) + poly([[x + lean - 1.8, yb - 32], [x + lean, yb - 39], [x + lean + 1.8, yb - 32]], PAL.sl1, 0.8);
    });
    o += C.shield(42, ys + 11, 4.5, PAL.red, 'cross') + C.shield(54, ys + 11, 4.5, PAL.sl1, 'chevron');
    var r = C.gableX(up, x0, x1, g0, g1, hw, 24, PAL.tile, PAL.red, 3);
    o += r.svg + chimney(110, 120, r.ridge + 6, 20, true);
    return rec('west-common-castlebarracks-01', 'barracks', 'barracks', [3, 2], up,
      ['barracks', 'stone_ground_floor', 'half_timber', 'weapon_rack', 'shields', 'chimney'], 'gable_tile',
      '城堡兵营：石砌底层 + 半木结构二层，门旁兵器架与挂盾，红瓦双坡顶', o);
  }

  /** 城堡厨房：2×2。厚石墙、宽拱门、送菜窗台、两座大烟囱冒烟、木柴垛、水桶。无对应 FacilityKind。 */
  function kitchen() {
    var up = 84, x0 = 8, x1 = 88, g0 = 14, g1 = 90, hw = 40, rh = 22, o = '';
    var yb = up + g1, yw = yb - hw;
    o += C.dropShadow(x0, x1, yw - 16, yb, 96, up + 96);
    o += C.stoneFace(x0, x1, yw, yb, PAL.st2);
    o += rect(x0, yb - 6, x1 - x0, 6, PAL.st3, 1);
    o += C.doorA(16, yb, 18, 24, false);
    o += path(C.archD(52, yw + 9, 20, 14), PAL.hole, 1) + rect(49, yw + 23, 26, 3, PAL.wood, 1);
    o += C.ell(57, yw + 21, 3.4, 2.2, PAL.wash, 0.8) + rect(64, yw + 15.5, 4.5, 6.5, PAL.tile, 0.8);
    // 木柴垛（圆木截面）
    for (var row = 0; row < 3; row++) for (var c = 0; c < 3 - row; c++) {
      var lx = 70 + c * 6 + row * 3, ly = yb - 3.5 - row * 6;
      o += C.ell(lx, ly, 3, 3, PAL.wood, 0.8) + C.ell(lx, ly, 1.2, 1.2, 'none', 0.6, 0.6);
    }
    // 水桶：箍桶 + 两道铁箍
    o += rect(39, yb - 12, 9, 12, PAL.wood, 1) + lines(seg(39, yb - 9, 48, yb - 9) + seg(39, yb - 3, 48, yb - 3), 1, 0.8) + C.ell(43.5, yb - 12, 4.5, 1.6, PAL.water, 0.8);
    var r = C.gableX(up, x0, x1, g0, g1, hw, rh, PAL.tile, PAL.red, 3);
    o += r.svg + chimney(16, 28, r.ridge + 10, 30, true) + chimney(66, 78, r.ridge + 12, 36, true);
    return rec('west-common-castlekitchen-01', 'kitchen', null, [2, 2], up,
      ['kitchen', 'stone', 'twin_chimney', 'woodpile', 'serving_hatch'], 'gable_tile',
      '城堡厨房：FacilityKind 无对应项，facility 填 null；两座大烟囱、送菜窗台、木柴垛', o);
  }

  /** 麻袋：束口粗麻袋，底边在 yG。 */
  function sack(cx, yG) {
    var d = 'M' + P(cx - 5, yG) + 'L' + P(cx - 6, yG - 6) + 'Q' + P(cx - 5, yG - 10) + ' ' + P(cx - 1.2, yG - 10) + 'L' + P(cx - 2, yG - 13) +
      'L' + P(cx + 2, yG - 13) + 'L' + P(cx + 1.2, yG - 10) + 'Q' + P(cx + 5, yG - 10) + ' ' + P(cx + 6, yG - 6) + 'L' + P(cx + 5, yG) + 'Z';
    return path(d, PAL.paper, 1) + lines(seg(cx - 2, yG - 10, cx + 2, yG - 10), 1, 0.8);
  }

  /** 粮仓：2×2。蘑菇石墩架空（防潮防鼠）、竖板墙身、百叶通风口、木梯上高门、麻袋、茅草陡顶。 */
  function granary() {
    var up = 72, x0 = 12, x1 = 84, g0 = 16, g1 = 86, lift = 12, hw = 46, rh = 30, o = '';
    var yb = up + g1, yf = yb - lift, yw = yb - hw;
    o += C.dropShadow(x0, x1, yw - 20, yb, 96, up + 96);
    o += rect(x0 + 2, yf, x1 - x0 - 4, lift, PAL.st3, 0).replace('/>', ' fill-opacity="0.55"/>'); // 架空层下的阴影
    [17, 37, 59, 79].forEach(function (x) { o += rect(x - 2.5, yf + 2, 5, lift - 2, PAL.st2, 1) + C.ell(x, yf + 2, 6, 2.4, PAL.st1, 1); });
    o += C.timberFace(x0, x1, yw, yf - 2, false);
    o += rect(x0 - 2, yf - 3, x1 - x0 + 4, 4, PAL.dark, 1);
    [22, 74].forEach(function (x) {
      o += rect(x - 4, yw + 8, 8, 9, PAL.hole, 1) + lines(seg(x - 4, yw + 11, x + 4, yw + 11) + seg(x - 4, yw + 14, x + 4, yw + 14), 1, 0.9).replace(PAL.ink, PAL.wood);
    });
    o += rect(40, yw + 8, 16, yf - yw - 11, PAL.dark, 1.1) + lines(C.hatchD(40, 56, yw + 9, yf - 4, 4), 0.7, 0.5) + C.ell(52.5, yw + 22, 0.9, 0.9, PAL.wash, 0.5);
    var lad = seg(44, yf - 3, 40, yb) + seg(52, yf - 3, 56, yb);
    for (var t = 1; t < 3; t++) { var u = t / 3, y = yf - 3 + (yb - yf + 3) * u; lad += seg(44 - 4 * u, y, 52 + 4 * u, y); }
    o += path(lad, 'none', 1.3);
    o += sack(28, yb) + sack(66, yb) + sack(72, yb - 1);
    var r = C.gableX(up, x0, x1, g0, g1, hw, rh, PAL.th1, PAL.th2, 5);
    o += r.svg;
    // 茅草秆：前坡上随机的短竖笔触；屋脊压一道草把
    var rr = C.rng(C.seedOf('west-common-castlegranary-01')), sd = '';
    for (var k = 0; k < 70; k++) { var sx = x0 - 3 + rr() * (x1 - x0 + 6), sy = r.ridge + 4 + rr() * (r.eave - r.ridge - 9); sd += seg(sx, sy, sx + 0.6, sy + 4); }
    o += lines(sd, 0.7, 0.45);
    o += rect(x0 - 5, r.ridge - 2.5, x1 - x0 + 10, 5, PAL.th2, 1.1) + lines(C.hatchD(x0 - 5, x1 + 5, r.ridge - 2, r.ridge + 2, 8), 0.8, 0.6);
    return rec('west-common-castlegranary-01', 'granary_raised', 'granary', [2, 2], up,
      ['granary', 'raised', 'staddle_stones', 'thatch', 'ladder', 'sacks'], 'gable_thatch',
      '城堡粮仓：蘑菇石墩架空的木板仓，木梯上高门，茅草陡顶', o);
  }

  /** 马头（侧脸朝右），从厩门上沿探出：cx 为脖根中点，yDoor 为半截门顶。 */
  function horseHead(cx, yDoor, yOpen, fill) {
    var d = 'M' + P(cx - 7, yDoor) + 'L' + P(cx - 6, yOpen + 12) + 'Q' + P(cx - 5, yOpen + 5) + ' ' + P(cx, yOpen + 4) +
      'L' + P(cx + 1, yOpen) + 'L' + P(cx + 3.5, yOpen + 4.5) + 'Q' + P(cx + 9, yOpen + 7) + ' ' + P(cx + 13, yOpen + 15) +
      'Q' + P(cx + 14, yOpen + 19) + ' ' + P(cx + 10.5, yOpen + 19.5) + 'Q' + P(cx + 6, yOpen + 18) + ' ' + P(cx + 3, yOpen + 15) + 'L' + P(cx + 4, yDoor) + 'Z';
    var o = path(d, fill, 1.1);
    o += C.ell(cx + 4, yOpen + 9, 0.9, 0.9, PAL.ink, 0) + lines(seg(cx - 5.5, yOpen + 7, cx - 6.5, yDoor - 2), 1.6, 0.7);
    return o + lines(seg(cx + 11, yOpen + 17, cx + 12.5, yOpen + 16.5), 0.8, 0.8);
  }
  /** 单坡披屋的骨架：前立面 yF..yb、角柱、单坡顶。返回 { svg, yF, yB, yb }。 */
  function leanTo(up, x0, x1, g0, g1, hb, hf, roofFill, vertical) {
    var yb = up + g1, o = '';
    var r = monoRoof(up, x0, x1, g0, g1, hb, hf, roofFill, 5, vertical);
    // 后沿：贴墙的一道压顶木
    o += r.svg + rect(x0, r.yB - 2, x1 - x0, 3, PAL.dark, 1);
    return { svg: o, yF: r.yF, yB: r.yB, yb: yb };
  }

  /** 马厩：3×1，贴幕墙内侧的单坡披屋。三间厩位：半截门 + Z 形撑、两匹马探头、草料架、门前水槽。 */
  function stable() {
    var up = 64, x0 = 4, x1 = 140, g0 = 4, g1 = 44, hb = 56, hf = 36, o = '';
    var yb = up + g1, yF = up + g1 - hf + 2;
    o += C.dropShadow(x0, x1, yF - 30, yb, 144, up + 48);
    o += rect(x0, yF, x1 - x0, yb - yF, PAL.wood, 1.3);
    for (var i = 0; i < 3; i++) {
      var sx = x0 + 4 + i * 45, ex = sx + 40, yDoor = yb - 15;
      o += rect(sx + 2, yF + 3, 36, yDoor - yF - 3, PAL.hole, 1);
      if (i === 1) { // 中间厩位：草料架 + 干草
        o += poly([[sx + 8, yF + 6], [sx + 32, yF + 6], [sx + 28, yF + 15], [sx + 12, yF + 15]], PAL.th1, 1) + lines(C.hatchD(sx + 9, sx + 31, yF + 6.5, yF + 14.5, 3), 0.8, 0.6);
      } else {
        o += horseHead(sx + 14, yDoor, yF + 3, i === 0 ? PAL.grain : PAL.paper);
      }
      o += rect(sx + 2, yDoor, 36, 15, PAL.wood, 1.2) + lines(C.hatchD(sx + 2, sx + 38, yDoor + 1, yb - 1, 6), 0.7, 0.45);
      o += path(seg(sx + 3, yDoor + 2, sx + 37, yDoor + 2) + seg(sx + 3, yb - 2, sx + 37, yb - 2) + seg(sx + 4, yb - 2, sx + 36, yDoor + 2), 'none', 1.3).replace(PAL.ink, PAL.dark);
    }
    [x0, x0 + 44, x0 + 89, x1 - 4].forEach(function (x) { o += rect(x, yF, 4, yb - yF, PAL.dark, 1); });
    // 门前水槽（木槽 + 水面）与一捆干草
    o += rect(58, yb - 7, 26, 7, PAL.grain, 1) + rect(60, yb - 7, 22, 2, PAL.water, 0.7);
    o += rect(114, yb - 9, 16, 9, PAL.th1, 1) + lines(C.hatchD(114, 130, yb - 8.5, yb - 0.5, 2.5) + seg(114, yb - 5, 130, yb - 5), 0.7, 0.6);
    o += leanTo(up, x0 - 3, x1 + 3, g0, g1, hb, hf, PAL.th1, true).svg;
    return rec('west-common-castlestable-01', 'stable_leanto', 'stable', [3, 1], up,
      ['stable', 'lean_to', 'wall_side', 'horses', 'hay', 'trough'], 'monopitch',
      '城堡马厩：贴幕墙内侧的单坡披屋（后沿贴墙），三间厩位、两匹马探头、草料架、门前水槽', o);
  }

  /** 铁匠棚：2×1，贴幕墙内侧的敞口单坡披屋。石砌炉膛 + 炉火、风箱、穿顶石烟囱、铁砧、淬火桶、挂墙工具。 */
  function forge() {
    var up = 72, x0 = 4, x1 = 92, g0 = 4, g1 = 44, hb = 56, hf = 36, o = '';
    var yb = up + g1, yF = up + g1 - hf + 2;
    o += C.dropShadow(x0, x1, yF - 30, yb, 96, up + 48);
    o += rect(x0, yF, x1 - x0, yb - yF, PAL.hole, 1.3);
    // 挂墙工具：火钳、锤
    o += path(seg(52, yF + 4, 50, yF + 16) + seg(55, yF + 4, 57, yF + 16) + seg(64, yF + 4, 64, yF + 15) + seg(61, yF + 15, 67, yF + 15), 'none', 1.2).replace(PAL.ink, PAL.st1);
    // 炉膛：石台 + 炉口 + 火 + 风箱
    o += rect(10, yb - 22, 30, 22, PAL.st2, 1.2) + C.ashlar(10, yb - 22, 30, 22, 6, 10, 0, 0, 0.45);
    o += path(C.archD(17, yb - 19, 16, 11), PAL.hole, 1);
    o += path('M' + P(19, yb - 8) + 'Q' + P(21, yb - 15) + ' ' + P(23, yb - 11) + 'Q' + P(25, yb - 19) + ' ' + P(27, yb - 12) + 'Q' + P(29, yb - 16) + ' ' + P(31, yb - 8) + 'Z', PAL.glow, 0.8);
    o += path('M' + P(22, yb - 8) + 'Q' + P(25, yb - 13) + ' ' + P(28, yb - 8) + 'Z', PAL.wash, 0);
    o += poly([[40, yb - 18], [54, yb - 15], [54, yb - 11], [40, yb - 8]], PAL.grain, 1) + path(seg(54, yb - 13, 59, yb - 13), 'none', 1.4);
    // 角柱 + 中柱
    [x0, 46, x1 - 4].forEach(function (x) { o += rect(x, yF, 4, yb - yF, PAL.dark, 1); });
    // 铁砧（木墩上）+ 淬火桶
    o += rect(62, yb - 8, 8, 8, PAL.wood, 1);
    o += path('M' + P(56, yb - 14) + 'L' + P(76, yb - 14) + 'Q' + P(74, yb - 11) + ' ' + P(70, yb - 11) + 'L' + P(69, yb - 8) + 'L' + P(63, yb - 8) + 'L' + P(62, yb - 11) +
      'L' + P(59, yb - 11) + 'Q' + P(55, yb - 12) + ' ' + P(52, yb - 14) + 'Z', PAL.sl2, 1.1);
    o += rect(78, yb - 11, 9, 11, PAL.wood, 1) + lines(seg(78, yb - 8, 87, yb - 8) + seg(78, yb - 3, 87, yb - 3), 1, 0.8) + C.ell(82.5, yb - 11, 4.5, 1.5, PAL.water3, 0.8);
    var lt = leanTo(up, x0 - 3, x1 + 3, g0, g1, hb, hf, PAL.sl1, false);
    o += lt.svg + chimney(16, 30, lt.yB + 18, 40, true);
    return rec('west-common-castleforge-01', 'forge_leanto', 'forge', [2, 1], up,
      ['forge', 'lean_to', 'wall_side', 'anvil', 'hearth', 'bellows', 'chimney'], 'monopitch',
      '城堡铁匠棚：贴幕墙内侧的敞口单坡披屋，炉火、风箱、铁砧、淬火桶、穿顶石烟囱', o);
  }

  /** 井：1×1。圆形石砌井栏 + 井水、两根立柱、辘轳与摇把、吊绳木桶、小双坡顶。 */
  function well() {
    var up = 44, cx = 24, cg = 26, r = 14, o = '';
    o += C.shadow(C.ellD(cx + 4, up + cg + 2, r + 3, (r + 3) * C.K));
    var cyl = C.cylinder(up, cx, cg, r, 0, 13, PAL.st2, true);
    o += cyl.svg + C.ell(cx, cyl.yt, r, r * C.K, PAL.st1, 1.3) + C.ell(cx, cyl.yt, r - 3.5, (r - 3.5) * C.K, PAL.water3, 1);
    var yTop = cyl.yt - 32;
    o += rect(cx - r - 1, yTop, 3.5, 32 + r * C.K * 0.6, PAL.dark, 1) + rect(cx + r - 2.5, yTop, 3.5, 32 + r * C.K * 0.6, PAL.dark, 1);
    // 辘轳：圆木 + 缠绳 + 摇把
    o += rect(cx - r + 2, yTop + 7, 2 * r - 4, 5, PAL.wood, 1) + lines(C.hatchD(cx - 5, cx + 5, yTop + 7.5, yTop + 11.5, 1.6), 0.8, 0.7);
    o += path(seg(cx + r + 1, yTop + 9.5, cx + r + 5, yTop + 9.5) + seg(cx + r + 5, yTop + 9.5, cx + r + 5, yTop + 16) + seg(cx + r + 5, yTop + 16, cx + r + 8, yTop + 16), 'none', 1.4);
    o += path(seg(cx, yTop + 12, cx, yTop + 22), 'none', 0.9);
    o += poly([[cx - 4, yTop + 22], [cx + 4, yTop + 22], [cx + 3, yTop + 29], [cx - 3, yTop + 29]], PAL.wood, 1) + lines(seg(cx - 3.6, yTop + 25, cx + 3.6, yTop + 25), 0.8, 0.8);
    // 小坡顶（木瓦）
    var rd = C.pts([[cx - r - 7, yTop + 3], [cx, yTop - 10], [cx + r + 7, yTop + 3], [cx + r + 4, yTop + 5], [cx, yTop - 6], [cx - r - 4, yTop + 5]]);
    o += path(rd, PAL.tile, 1.2) + C.roofRows(rd, cx - r - 7, yTop - 10, cx + r + 7, yTop + 5, 3, true, 0.45);
    return rec('west-common-castlewell-01', 'well_windlass', 'well', [1, 1], up,
      ['well', 'windlass', 'bucket', 'stone_curb'], 'gable_tile',
      '内院水井：圆石井栏、辘轳摇把、吊桶、小坡顶', o);
  }

  function list() { return [greatHall, chapel, barracks, kitchen, granary, stable, forge, well]; }

  var API = { list: list, greatHall: greatHall, chapel: chapel, barracks: barracks, kitchen: kitchen, granary: granary, stable: stable, forge: forge, well: well, buttress: buttress, chimney: chimney };
  if (isNode) module.exports = API;
  else { root.TownArtWC = root.TownArtWC || {}; root.TownArtWC.annex = API; }
})(this);
