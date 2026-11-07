/*
 * 织梦 · east-site · 田园类资源点：茶园（herb，tags 含 tea）、药圃（herb）、花椒（spices）、桑园蚕房（silk）、
 * 稻田（grain）、牧场马场（livestock / wool / horses）、染坊原料（dye）。
 * 浏览器挂 window.TownArtES_farm，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./kit.js'), require('./kit2.js'));
  else root.TownArtES_farm = factory(root.TownArtES_core, root.TownArtES_kit, root.TownArtES_kit2);
})(this, function (C, K, K2) {
  'use strict';
  var S = C.S, f = C.f, poly = C.poly, path = C.path, rect = C.rect, ell = C.ell, circ = C.circ, ln = C.ln;
  var G = S.ink, G2 = S.ink2, LW = S.lw, LD = S.lwd;
  var defs = [];
  function def(o) { defs.push(o); }
  /** 一道灌木垄（沿 x，扇贝形顶边，周期 8 px，左右贯穿 0..48 以便平铺）。 */
  function hedgeRow(y, h, col, col2) {
    var d = 'M-0.5 ' + f(y);
    for (var x = 0; x < 48; x += 8) d += 'Q' + f(x + 4) + ' ' + f(y - h * 1.6) + ' ' + f(x + 8) + ' ' + f(y);
    d += 'L48.5 ' + f(y + 3) + 'L-0.5 ' + f(y + 3) + 'Z';
    var o = path(d, col, null, 0);
    for (x = 2; x < 48; x += 8) o += path('M' + f(x) + ' ' + f(y - h * 0.4) + 'q2 -' + f(h * 0.5) + ' 4 0', null, col2, 0.9);
    return o;
  }

  // ---------------- 茶园（herb + tea） ----------------
  function teaTile(v) {
    return { id: 'east-common-ground-teaterrace-0' + v, name: '梯田茶垄 ' + v, category: 'ground', kind: 'ground_tea_terrace', resource: 'herb', facility: null,
      variant: v, w: 1, d: 1, up: 0, tags: ['tileable', 'tea', 'terrace'], note: '每格三级梯坎，每级一道茶垄；垄与坎都横贯整格、周期 8 px，左右上下平铺无缝',
      draw: function () {
        var o = rect(-0.5, -0.5, 49, 49, S.grass), k;
        for (k = 0; k < 3; k++) {
          var y = k * 16;
          o += rect(-0.5, y + 12, 49, 4, S.earth2) + ln(-0.5, y + 12, 48.5, y + 12, S.earth3, 0.9);
          o += hedgeRow(y + 11, 4 + (v === 2 ? 1 : 0), v === 2 ? S.leaf2 : S.leaf, S.leaf3);
        }
        return o;
      } };
  }
  def(teaTile(1)); def(teaTile(2));

  def({ id: 'east-common-site-teashed-01', name: '茶园·炒茶棚', category: 'site', kind: 'site_tea_roasting', resource: 'herb', facility: null,
    w: 3, d: 2, up: 54, tags: ['tea', 'roasting', 'wok', 'shed'], roof: 'gable_tile', note: '敞口瓦棚，砖灶上斜嵌两口炒茶铁锅，旁有揉茶竹匾与萎凋竹架；无对应 FacilityKind',
    draw: function (W, D, r, id) {
      var o = K2.pad(2, 4, W - 2, D - 2, S.earth, 0.5);
      o += C.shadow([[118, 22], [128, 28], [128, 66], [118, 60]]);
      o += rect(12, 20, 106, 42, S.cream, G, LD) + rect(12, 20, 106, 42, S.shadow, null, 0, C.fop(0.15));
      // 萎凋竹架（后墙前）
      for (var k = 0; k < 3; k++) o += ell(92, 30 + k * 8, 12, 2.6, S.thatch, G, 0.7) + ell(92, 29.6 + k * 8, 8, 1.4, S.leaf, null, 0);
      o += K2.bamboo(80, 52, 80, 26, 1.2) + K2.bamboo(104, 52, 104, 26, 1.2);
      // 砖灶 + 两口斜锅 + 灶门火
      o += K2.box(16, 72, 66, 14, 12, S.brown2, S.brown);
      [30, 58].forEach(function (x) {
        o += ell(x, 46, 11, 4.4, '#2e3036', G, LD) + ell(x, 46, 7, 2.6, S.leaf, null, 0);
        o += path('M' + (x - 4) + ' 66 L' + (x - 4) + ' 59 Q' + x + ' 55 ' + (x + 4) + ' 59 L' + (x + 4) + ' 66 Z', '#1d1b20', G, 0.8) + circ(x, 63, 2, S.orange, null, 0);
      });
      [12, 65, 118].forEach(function (x) { o += K.post(x, 18, 64, 3.2, S.vermil); });
      o += K.roof(id, 10, 120, -18, 20, 6, S.navy2, 'tile', 4);
      // 前方：揉茶竹匾、两只茶篓
      o += ell(36, 84, 16, 5, S.thatch, G, LD) + ell(36, 83.6, 11, 3, S.leaf2, null, 0);
      o += K2.basket(104, 90, 12, 10, S.leaf2, S.leaf, r) + K2.basket(124, 88, 12, 10, S.leaf2, S.leaf, r);
      return o;
    } });
  def({ id: 'east-common-prop-tea-pickbasket-01', name: '采茶背篓', category: 'prop', kind: 'prop_tea_basket', resource: 'herb', facility: null,
    w: 1, d: 1, up: 20, tags: ['tea', 'basket'], note: '高腰竹背篓装满鲜叶，旁放一顶竹斗笠',
    draw: function (W, D, r) {
      var o = K2.basket(18, 44, 16, 20, S.leaf2, S.leaf, r);
      return o + path('M28 42 Q38 30 48 42 Z', S.thatch, G, LD) + ln(38, 34, 38, 41, S.thatch2, 0.8);
    } });
  def({ id: 'east-common-prop-tea-bush-01', name: '茶丛', category: 'prop', kind: 'prop_tea_bush', resource: 'herb', facility: null,
    w: 1, d: 1, up: 14, tags: ['tea', 'plant'], note: '修剪成半球形的单株茶树，可散放在茶垄之间',
    draw: function (W, D, r) {
      var o = C.shadowEll(27, 44, 18, 3.6) + path('M8 44 Q8 22 24 20 Q40 22 40 44 Z', S.leaf, G, LD);
      for (var i = 0; i < 7; i++) { var x = 12 + r() * 24, y = 26 + r() * 14; o += path('M' + f(x) + ' ' + f(y) + 'q2 -3 4 0', null, S.leaf2, 1); }
      return o;
    } });

  // ---------------- 药圃（herb）与花椒（spices） ----------------
  function herbTile(v) {
    return { id: 'east-common-ground-herbbed-0' + v, name: '药田 ' + v, category: 'ground', kind: 'ground_herb_bed', resource: 'herb', facility: null,
      variant: v, w: 1, d: 1, up: 0, tags: ['tileable', 'herb', 'bed'], note: '两畦药苗、中间一道垄沟，畦沿格边对齐，左右上下平铺无缝；1=绿叶药苗，2=开紫花',
      draw: function (W, D, r) {
        var o = rect(-0.5, -0.5, 49, 49, S.earth2), k, i;
        for (k = 0; k < 2; k++) {
          var y = 3 + k * 24;
          o += rect(-0.5, y, 49, 18, S.earth3) + ln(-0.5, y, 48.5, y, S.brown2, 0.8);
          for (i = 0; i < 6; i++) {
            var x = 4 + i * 8, yy = y + 9;
            o += path('M' + x + ' ' + yy + 'q-3 -4 -1 -7 M' + x + ' ' + yy + 'q3 -4 1 -7 M' + x + ' ' + yy + 'l0 -8', null, S.leaf, 1.2);
            if (v === 2) o += circ(x, yy - 8, 1.4, '#9a6fb0', null, 0);
          }
        }
        return o;
      } };
  }
  def(herbTile(1)); def(herbTile(2));

  def({ id: 'east-common-site-herbgarden-01', name: '药圃·晒药棚', category: 'site', kind: 'site_herb_garden', resource: 'herb', facility: null,
    w: 3, d: 2, up: 46, tags: ['herb', 'medicine', 'drying', 'shed'], roof: 'gable_thatch', note: '竹篱围着两畦药田，后侧茅棚檐下挂成串药材，前有晒药竹匾架；药铺本身另见 infirmary',
    draw: function (W, D, r, id) {
      var o = K2.pad(2, 2, W - 2, D - 2, S.earth, 0.45);
      o += C.shadow([[100, 20], [110, 26], [110, 44], [100, 38]]);
      o += rect(12, 18, 88, 22, S.cream, G, LD) + rect(46, 24, 12, 16, S.wood3, G, LD);
      [12, 56, 100].forEach(function (x) { o += K.post(x, 16, 42, 3); });
      o += K.roof(id, 10, 102, -12, 18, 5, S.thatch, 'thatch', 3);
      for (var k = 0; k < 5; k++) { var x = 20 + k * 16; o += ln(x, 18, x, 28, S.thatch2, 0.8) + ell(x, 30, 2.6, 4, k % 2 ? S.brown2 : S.leaf3, G, 0.6); }
      // 两畦药田
      [[10, 50], [72, 50]].forEach(function (p) {
        o += rect(p[0], p[1], 56, 32, S.earth3, G, LD);
        for (var i = 0; i < 6; i++) for (var j = 0; j < 3; j++) { var xx = p[0] + 5 + i * 9, yy = p[1] + 9 + j * 10; o += path('M' + xx + ' ' + yy + 'q-3 -4 -1 -6 M' + xx + ' ' + yy + 'q3 -4 1 -6', null, j === 1 ? S.leaf2 : S.leaf, 1.2); }
      });
      // 竹篱（前沿）
      for (x = 6; x < W - 4; x += 6) o += K2.bamboo(x, 92, x, 82, 1);
      o += K2.bamboo(4, 85, W - 4, 85, 1);
      return o;
    } });
  def({ id: 'east-common-prop-herb-trays-01', name: '晒药竹匾', category: 'prop', kind: 'prop_herb_trays', resource: 'herb', facility: null,
    w: 1, d: 1, up: 30, tags: ['herb', 'drying', 'bamboo'], note: '竹架三层，每层一只圆竹匾摊晒药材',
    draw: function (W, D, r) {
      var o = C.shadow([[8, 44], [42, 42], [46, 46], [10, 48]]);
      o += K2.bamboo(8, 44, 8, 12, 1.4) + K2.bamboo(40, 44, 40, 12, 1.4);
      var cols = [S.brown2, S.leaf3, S.ochre];
      for (var k = 0; k < 3; k++) {
        var y = 16 + k * 11;
        o += ell(24, y, 18, 4, S.thatch, G, LD) + ell(24, y - 0.4, 13, 2.4, cols[k], null, 0);
        for (var i = 0; i < 5; i++) o += circ(15 + i * 4.5, y - 0.6 + (i % 2) * 0.8, 0.9, S.cream2, null, 0, C.op(0.7));
      }
      return o;
    } });
  def({ id: 'east-common-prop-herb-mortar-01', name: '药碾与药篓', category: 'prop', kind: 'prop_herb_grinder', resource: 'herb', facility: null,
    w: 1, d: 1, up: 14, tags: ['herb', 'grinder'], note: '船形铁药碾配碾轮，旁边一只药篓',
    draw: function (W, D, r) {
      var o = C.shadow([[4, 42], [32, 40], [34, 44], [6, 46]]);
      o += path('M4 36 L32 36 L28 44 L8 44 Z', S.gray, G, LD) + ell(18, 36, 14, 2.6, S.gray2, G, 0.8) + ell(18, 35.4, 9, 1.4, S.brown2, null, 0);
      o += K2.wheel(18, 30, 6, 4, S.gray) + K2.bar(8, 30, 28, 30, 1.2, S.wood2);
      return o + K2.basket(40, 44, 10, 10, S.leaf3, S.leaf, r);
    } });

  def({ id: 'east-common-site-pepperyard-01', name: '花椒园·晒椒场', category: 'site', kind: 'site_spice_drying', resource: 'spices', facility: null,
    w: 3, d: 2, up: 40, tags: ['spices', 'pepper', 'drying', 'trees'], note: '后排两株花椒树，前方竹席上摊晒红花椒，竹竿上挂成串干辣椒；无对应 FacilityKind',
    draw: function (W, D, r) {
      var o = K2.pad(2, 2, W - 2, D - 2, S.earth, 0.5);
      [[30, 34], [110, 30]].forEach(function (p) {
        o += C.shadowEll(p[0] + 6, p[1] + 2, 20, 4) + K2.bar(p[0], p[1], p[0] - 2, p[1] - 14, 2.6, S.wood3);
        o += path('M' + (p[0] - 24) + ' ' + (p[1] - 14) + ' Q' + (p[0] - 22) + ' ' + (p[1] - 40) + ' ' + p[0] + ' ' + (p[1] - 40) + ' Q' + (p[0] + 24) + ' ' + (p[1] - 40) + ' ' + (p[0] + 24) + ' ' + (p[1] - 14) + ' Z', S.leaf, G, LD);
        for (var i = 0; i < 9; i++) o += circ(p[0] - 16 + r() * 32, p[1] - 34 + r() * 18, 1.6, S.vermil, null, 0);
      });
      // 晒席
      [[12, 54], [76, 54]].forEach(function (p) {
        o += poly([[p[0], p[1]], [p[0] + 56, p[1]], [p[0] + 58, p[1] + 26], [p[0] - 2, p[1] + 26]], S.thatch, G, LD);
        for (var i = 0; i < 26; i++) o += circ(p[0] + 4 + r() * 50, p[1] + 4 + r() * 18, 1.4, i % 3 ? S.vermil : '#9a3020', null, 0);
      });
      // 挂辣椒的竹竿
      o += K2.bamboo(60, 50, 60, 6, 1.2) + K2.bamboo(84, 50, 84, 6, 1.2) + K2.bamboo(56, 8, 88, 8, 1.2);
      for (var k = 0; k < 4; k++) { var x = 64 + k * 6; o += ln(x, 8, x, 30, S.thatch2, 0.6); for (var j = 0; j < 5; j++) o += ell(x, 12 + j * 4, 1.6, 2.2, S.vermil, null, 0); }
      return o;
    } });
  def({ id: 'east-common-prop-spice-sacks-01', name: '香料麻袋', category: 'prop', kind: 'prop_spice_sacks', resource: 'spices', facility: null,
    w: 1, d: 1, up: 16, tags: ['spices', 'sacks'], note: '敞口麻袋盛花椒、桂皮，袋口翻卷',
    draw: function () {
      var o = C.shadow([[4, 44], [44, 42], [47, 47], [7, 48]]);
      [[14, 44, S.vermil], [34, 44, S.brown2]].forEach(function (p) {
        o += path('M' + (p[0] - 10) + ' ' + p[1] + ' Q' + (p[0] - 12) + ' ' + (p[1] - 18) + ' ' + (p[0] - 8) + ' ' + (p[1] - 20) + ' L' + (p[0] + 8) + ' ' + (p[1] - 20) + ' Q' + (p[0] + 12) + ' ' + (p[1] - 18) + ' ' + (p[0] + 10) + ' ' + p[1] + ' Z', S.thatch, G, LD);
        o += ell(p[0], p[1] - 20, 8, 2.6, S.thatch2, G, 0.8) + ell(p[0], p[1] - 20.4, 6, 1.6, p[2], null, 0);
      });
      return o;
    } });

  // ---------------- 桑园蚕房 silk ----------------
  /** 一株矮桑（截干养成的拳桑）：短粗干 + 几簇圆叶团。 */
  function mulberry(x, yb, s, r) {
    var o = C.shadowEll(x + 4, yb + 1, 12 * s, 3 * s) + K2.bar(x, yb, x, yb - 12 * s, 3 * s, S.wood3);
    o += K2.bar(x, yb - 10 * s, x - 7 * s, yb - 16 * s, 1.6 * s, S.wood3) + K2.bar(x, yb - 10 * s, x + 7 * s, yb - 17 * s, 1.6 * s, S.wood3);
    [[-8, -20, 7], [8, -21, 7], [0, -26, 8]].forEach(function (p) { o += circ(x + p[0] * s, yb + p[1] * s, p[2] * s, S.leaf, G, LD) + circ(x + p[0] * s - 2 * s, yb + p[1] * s - 2 * s, p[2] * 0.45 * s, S.leaf2, null, 0); });
    for (var i = 0; i < 3; i++) o += circ(x - 6 * s + r() * 12 * s, yb - 24 * s + r() * 8 * s, 1.1 * s, '#5a2a4a', null, 0);
    return o;
  }
  def({ id: 'east-common-site-silkhouse-01', name: '桑园·蚕房', category: 'site', kind: 'site_silkworm_house', resource: 'silk', facility: null,
    w: 3, d: 2, up: 62, tags: ['silk', 'sericulture', 'house', 'racks'], roof: 'gable_tile', note: '粉墙小瓦蚕房，前檐敞开露出层层蚕匾竹架，檐下挂一串蚕簇；门前一株矮桑与采叶筐；无对应 FacilityKind',
    draw: function (W, D, r, id) {
      var o = K2.pad(2, 4, W - 2, D - 2, S.earth, 0.5);
      o += C.shadow([[112, 18], [124, 24], [124, 62], [112, 56]]);
      o += rect(12, 16, 100, 44, S.cream2, G, LD);
      // 敞开的前檐下：竹架三层蚕匾，匾里白蚕
      o += rect(26, 22, 60, 36, S.brown2, G, LD) + K2.bamboo(28, 58, 28, 22, 1.2) + K2.bamboo(84, 58, 84, 22, 1.2);
      for (var k = 0; k < 3; k++) {
        var y = 30 + k * 10;
        o += ell(56, y, 26, 3, S.thatch, G, 0.8) + ell(56, y - 0.3, 21, 1.8, S.leaf2, null, 0);
        for (var i = 0; i < 8; i++) o += ell(38 + i * 5, y - 0.6, 1.4, 0.7, S.salt, null, 0);
      }
      o += rect(94, 30, 12, 16, S.brown, G, 0.8) + ln(100, 30, 100, 46, S.wood2, 0.8);
      [12, 62, 112].forEach(function (x) { o += K.post(x, 14, 62, 3.2); });
      o += K.roof(id, 10, 114, -20, 16, 6, S.gray, 'tile', 4);
      // 檐下蚕簇（稻草扎的山字簇，挂白茧）
      for (k = 0; k < 4; k++) { var x = 20 + k * 28; o += ln(x, 16, x, 22, S.thatch2, 0.7) + poly([[x - 4, 22], [x + 4, 22], [x, 14 + 14]], S.thatch, G, 0.6) + ell(x, 25, 1.6, 1.2, S.salt, null, 0); }
      o += mulberry(126, 82, 0.9, r) + K2.basket(30, 90, 13, 10, S.leaf, S.leaf3, r) + K2.basket(60, 92, 12, 9, S.salt, S.cream, r);
      return o;
    } });
  def({ id: 'east-common-prop-silk-mulberry-01', name: '桑树行', category: 'prop', kind: 'prop_mulberry_row', resource: 'silk', facility: null,
    w: 1, d: 1, up: 34, tags: ['silk', 'mulberry', 'tree'], note: '两株截干拳桑一前一后，紫黑桑葚点缀；可沿格排成桑行',
    draw: function (W, D, r) { return mulberry(30, 36, 0.8, r) + mulberry(16, 46, 0.85, r); } });
  def({ id: 'east-common-prop-silk-reel-01', name: '缫丝车', category: 'prop', kind: 'prop_silk_reel', resource: 'silk', facility: null,
    w: 1, d: 1, up: 30, tags: ['silk', 'reeling', 'wheel'], note: '小灶上一锅煮茧，丝从锅里引上木框大丝軖，脚踏摇转',
    draw: function () {
      var o = C.shadow([[4, 44], [44, 42], [47, 47], [7, 48]]);
      o += K2.box(2, 18, 46, 10, 6, S.brown2, S.brown) + ell(10, 30, 7, 2.4, '#2e3036', G, 0.8) + ell(10, 30, 5, 1.4, S.water2, null, 0);
      for (var i = 0; i < 3; i++) o += ell(7 + i * 3, 30, 1.2, 0.8, S.salt, null, 0);
      o += K.post(24, 14, 46, 2.2, S.wood3) + K.post(44, 14, 46, 2.2, S.wood3);
      o += K2.wheel(34, 20, 9, 6, S.wood) + circ(34, 20, 7, null, S.salt, 1.6, C.op(0.8));
      o += pl10();
      return o + K2.bar(30, 46, 40, 40, 1.4, S.wood2);
      function pl10() { return C.pl([[11, 29], [22, 14], [27, 15]], S.salt, 0.7); }
    } });
  def({ id: 'east-common-prop-silk-cocoons-01', name: '蚕茧箩', category: 'prop', kind: 'prop_cocoon_baskets', resource: 'silk', facility: null,
    w: 1, d: 1, up: 12, tags: ['silk', 'cocoon', 'basket'], note: '两只圆竹箩盛满白茧，一只翻倒撒出几颗',
    draw: function (W, D, r) {
      var o = K2.basket(14, 44, 15, 10, S.salt, S.cream, r) + K2.basket(34, 42, 15, 10, S.salt, S.cream, r);
      for (var i = 0; i < 3; i++) o += ell(26 + i * 5, 46 - i, 1.8, 1.1, S.salt, G, 0.4);
      return o;
    } });

  // ---------------- 稻田 grain ----------------
  function paddyTile(v) {
    return { id: 'east-common-ground-paddy-0' + v, name: '水田格 ' + v, category: 'ground', kind: 'ground_paddy', resource: 'grain', facility: null,
      variant: v, w: 1, d: 1, up: 0, tags: ['tileable', 'paddy', 'water'], note: '田埂沿格边（每格左、上两边各 3px），相邻格拼成连续埂网；格内水面同 east-ground 水色，1=新插秧，2=稻浪青，3=稻熟金黄',
      draw: function (W, D, r, id) {
        var o = rect(-0.5, -0.5, 49, 49, S.earth2), i, j;
        o += K2.water([[3, 3], [48.5, 3], [48.5, 48.5], [3, 48.5]], id, r).replace(/stroke="[^"]+" stroke-width="[^"]+"/, '');
        var col = v === 1 ? S.leaf2 : v === 2 ? S.leaf : S.ochre, col2 = v === 3 ? S.thatch2 : S.leaf3;
        for (j = 0; j < 5; j++) for (i = 0; i < 5; i++) {
          var x = 7.5 + i * 9, y = 11 + j * 9;
          if (v === 1) o += path('M' + x + ' ' + y + 'l-1.6 -4 M' + x + ' ' + y + 'l0 -4.6 M' + x + ' ' + y + 'l1.6 -4', null, col, 1);
          else o += path('M' + (x - 3.6) + ' ' + y + 'Q' + x + ' ' + (y - 9) + ' ' + (x + 3.6) + ' ' + y + 'Z', col, col2, 0.6);
        }
        return o + ln(1.5, 0, 1.5, 48, S.earth, 1) + ln(0, 1.5, 48, 1.5, S.earth, 1);
      } };
  }
  def(paddyTile(1)); def(paddyTile(2)); def(paddyTile(3));

  def({ id: 'east-common-site-waterwheel-01', name: '稻田·龙骨水车', category: 'site', kind: 'site_waterwheel', resource: 'grain', facility: 'mill',
    w: 2, d: 2, up: 60, tags: ['grain', 'irrigation', 'waterwheel', 'water'], roof: 'none', note: '溪边立轮式筒车：大轮挂竹筒提水入木槽，槽通向水田；facility 取 mill（水力设施）',
    draw: function (W, D, r, id) {
      var o = K2.water([[0, 50], [W, 50], [W, D], [0, D]], id, r, true) + ln(0, 50.5, W, 50.5, S.earth3, 2);
      o += K2.pad(0, 0, W, 48, S.earth, 0.5);
      // 两根立柱 + 轮轴
      o += K.post(22, 8, 72, 4, S.wood3) + K.post(74, 8, 72, 4, S.wood3);
      o += K2.wheel(48, 30, 34, 12, S.wood) + circ(48, 30, 28, null, S.wood3, 1.2);
      for (var i = 0; i < 12; i++) {
        var a = i / 12 * Math.PI * 2, x = 48 + Math.cos(a) * 34, y = 30 + Math.sin(a) * 34;
        o += rect(x - 2.4, y - 3, 4.8, 6, S.leaf2, G, 0.7);
      }
      o += K2.bar(20, 12, 76, 12, 2.4, S.wood2);
      // 引水木槽（右上向后通到田里）
      o += poly([[56, -6], [96, -12], [96, -6], [56, 0]], S.wood, G, LD) + ln(58, -4, 94, -9.6, S.water, 1.6);
      o += ell(72, 82, 18, 4, S.water2, null, 0, C.fop(0.6));
      return o;
    } });

  def({ id: 'east-common-site-granary-01', name: '稻田·谷仓', category: 'site', kind: 'site_granary', resource: 'grain', facility: 'granary',
    w: 3, d: 2, up: 64, tags: ['grain', 'granary', 'raised_floor'], roof: 'gable_thatch', note: '木柱架空防潮的田头谷仓，木板墙，前有木梯与晒谷竹席、稻草垛',
    draw: function (W, D, r, id) {
      var o = K2.pad(2, 4, W - 2, D - 2, S.earth, 0.5);
      o += C.shadow([[108, 30], [120, 36], [120, 72], [108, 66]]);
      // 架空柱脚 + 柱头防鼠石盘
      [22, 52, 82, 104].forEach(function (x) { o += K.post(x, 44, 70, 3.2, S.wood3) + ell(x, 44, 5, 1.6, S.gray3, G, 0.7); });
      o += K2.box(14, 112, 44, 30, 6, S.wood2, S.wood);
      for (var x = 20; x < 112; x += 7) o += ln(x, 14, x, 44, S.wood3, 0.8, C.op(0.7));
      o += rect(56, 20, 16, 22, S.wood3, G, LD) + ln(64, 20, 64, 42, S.wood2, 0.8);
      o += K.roof(id, 12, 114, -24, 10, 7, S.thatch, 'thatch', 3);
      o += K2.ladder(64, 42, 76, 8);
      // 晒谷竹席 + 稻草垛
      o += poly([[6, 78], [56, 78], [60, 94], [2, 94]], S.thatch2, G, LD) + poly([[9, 81], [53, 81], [56, 91], [6, 91]], S.ochre, null, 0);
      o += path('M112 92 Q114 66 128 62 Q142 66 144 92 Z', S.thatch, G, LD) + path('M118 74 Q128 68 138 74', null, S.thatch2, 1.2) + ln(120, 82, 136, 82, S.wood3, 1.4);
      return o;
    } });
  def({ id: 'east-common-prop-grain-sheaves-01', name: '稻草垛', category: 'prop', kind: 'prop_straw_stack', resource: 'grain', facility: null,
    w: 1, d: 1, up: 30, tags: ['grain', 'straw'], note: '打完谷的稻草围成圆垛，顶上扎一束',
    draw: function () {
      var o = C.shadowEll(27, 44, 19, 4) + path('M8 44 Q8 20 24 12 Q40 20 40 44 Z', S.thatch, G, LD);
      for (var i = 0; i < 4; i++) o += path('M' + (10 + i) + ' ' + (38 - i * 7) + ' Q24 ' + (32 - i * 8) + ' ' + (38 - i) + ' ' + (38 - i * 7), null, S.thatch2, 0.9);
      return o + poly([[21, 14], [27, 14], [24, 2]], S.thatch2, G, 0.7) + ln(19, 15, 29, 15, S.wood3, 1.4);
    } });
  def({ id: 'east-common-prop-grain-dryingmat-01', name: '晒谷席与木耙', category: 'prop', kind: 'prop_grain_mat', resource: 'grain', facility: null,
    w: 1, d: 1, up: 8, tags: ['grain', 'drying'], note: '竹席摊晒稻谷，一把木推耙',
    draw: function () {
      var o = poly([[4, 18], [44, 18], [46, 44], [2, 44]], S.thatch2, G, LD) + poly([[7, 21], [41, 21], [43, 41], [5, 41]], S.ochre, null, 0);
      for (var y = 25; y < 40; y += 4) o += ln(7, y, 42, y, S.thatch2, 0.6, C.op(0.6));
      return o + K2.bar(16, 34, 30, 34, 2.4, S.wood3) + K2.bar(23, 34, 34, 10, 1.4, S.wood2);
    } });

  // ---------------- 牧场 livestock / wool / horses ----------------
  /** 一段木栅栏（沿 x），x0..x1，脚底 yb，高 h。 */
  function fence(x0, x1, yb, h) {
    var o = K2.bar(x0, yb - h * 0.75, x1, yb - h * 0.75, 1.6, S.wood2) + K2.bar(x0, yb - h * 0.3, x1, yb - h * 0.3, 1.6, S.wood2);
    for (var x = x0; x <= x1 + 0.1; x += 12) o += K.post(x, yb - h, yb, 2.6, S.wood3);
    return o;
  }
  /** 小牲口（侧身）：kind = 'sheep' / 'cow' / 'horse'。 */
  function beast(x, yb, kind, s) {
    s = s || 1;
    var body = kind === 'sheep' ? S.cream2 : kind === 'cow' ? S.brown2 : S.brown, o = C.shadowEll(x + 2, yb, 9 * s, 2 * s);
    var ly = kind === 'horse' ? 9 : 6;
    [-5, -2, 3, 6].forEach(function (dx) { o += ln(x + dx * s, yb - ly * s, x + dx * s, yb, S.wood3, 1.4 * s); });
    o += ell(x, yb - (ly + 3) * s, 8 * s, 4 * s, body, G, 0.8);
    var hx = x + 8 * s, hy = yb - (ly + (kind === 'horse' ? 8 : 4)) * s;
    o += K2.bar(x + 5 * s, yb - (ly + 4) * s, hx, hy, 2.2 * s, body) + ell(hx + 1.6 * s, hy, 2.6 * s, 1.8 * s, kind === 'sheep' ? S.gray2 : body, G, 0.6);
    if (kind === 'horse') o += ln(hx - 1, hy, x + 4 * s, yb - (ly + 6) * s, S.coal, 1.4 * s) + ln(x - 8 * s, yb - (ly + 3) * s, x - 10 * s, yb - ly * s + 2, S.coal, 1.6 * s);
    return o;
  }
  function grassTile(v) {
    return { id: 'east-common-ground-pasture-0' + v, name: '草场 ' + v, category: 'ground', kind: 'ground_pasture', resource: 'livestock', facility: null,
      variant: v, w: 1, d: 1, up: 0, tags: ['tileable', 'pasture', 'grass'], note: '放牧草场：比黄土底色偏绿的草地，草丛离边 ≥3 px，任意排列无缝',
      draw: function (W, D, r) {
        var o = rect(-0.5, -0.5, 49, 49, S.grass) + rect(-0.5, -0.5, 49, 49, S.leaf2, null, 0, C.fop(0.32)), i;
        for (i = 0; i < 10 + v * 3; i++) { var x = 5 + r() * 38, y = 6 + r() * 38; o += path('M' + f(x) + ' ' + f(y) + 'l-1.4 -3.4 M' + f(x) + ' ' + f(y) + 'l1.2 -3.8', null, S.leaf3, 0.9, C.op(0.8)); }
        if (v === 2) for (i = 0; i < 4; i++) o += circ(8 + r() * 32, 8 + r() * 32, 1.2, S.ochre, null, 0);
        return o;
      } };
  }
  def(grassTile(1)); def(grassTile(2));

  def({ id: 'east-common-site-pasture-01', name: '草场木栏·羊圈', category: 'site', kind: 'site_sheepfold', resource: 'livestock', facility: null,
    w: 3, d: 2, up: 40, tags: ['pasture', 'fold', 'sheep', 'cattle', 'wool'], roof: 'gable_thatch', note: '木栅栏围出的草场，后侧茅草羊棚，栏里几只羊一头牛，门边草料槽；毛料与肉畜共用此主体；无对应 FacilityKind',
    draw: function (W, D, r, id) {
      var o = K2.pad(2, 2, W - 2, D - 2, S.leaf2, 0.3);
      o += C.shadow([[70, 14], [80, 20], [80, 38], [70, 32]]);
      o += rect(14, 12, 56, 24, S.brown2, G, LD) + rect(14, 12, 56, 24, S.shadow, null, 0, C.fop(0.25));
      [14, 42, 70].forEach(function (x) { o += K.post(x, 10, 38, 3); });
      o += K.roof(id, 12, 72, -10, 12, 5, S.thatch, 'thatch', 3);
      o += fence(4, 140, 30, 14).replace(/<g[^>]*>/, '');
      o += beast(30, 56, 'sheep') + beast(56, 64, 'sheep', 0.9) + beast(98, 58, 'cow', 1.1) + beast(78, 76, 'sheep');
      o += K2.box(110, 136, 76, 6, 6, S.leaf2, S.wood) + ln(112, 69, 134, 69, S.leaf3, 1);
      o += fence(4, 52, 90, 14) + fence(88, 140, 90, 14);
      return o;
    } });
  def({ id: 'east-common-site-horsefarm-01', name: '马场·马厩', category: 'site', kind: 'site_horse_stable', resource: 'horses', facility: 'stable',
    w: 4, d: 2, up: 56, tags: ['horses', 'stable', 'paddock'], roof: 'gable_tile', note: '一排五间敞口马厩，瓦顶朱柱，每间一匹马与料槽，前有拴马桩与跑马木栏',
    draw: function (W, D, r, id) {
      var o = K2.pad(2, 2, W - 2, D - 2, S.earth, 0.5);
      o += C.shadow([[176, 16], [188, 22], [188, 58], [176, 52]]);
      o += rect(12, 14, 164, 40, S.brown2, G, LD) + rect(12, 14, 164, 40, S.shadow, null, 0, C.fop(0.22));
      for (var k = 0; k < 5; k++) {
        var x0 = 12 + k * 32.8;
        o += beast(x0 + 14, 50, 'horse', 1) + K2.box(x0 + 4, x0 + 28, 54, 5, 3, S.leaf2, S.wood3, 0.7);
      }
      for (k = 0; k <= 5; k++) o += K.post(12 + k * 32.8, 12, 56, 3.2, S.vermil);
      o += K.roof(id, 10, 178, -20, 14, 7, S.navy2, 'tile', 5);
      o += fence(6, 186, 90, 14);
      o += K.post(96, 62, 84, 3.4, S.wood3) + circ(96, 66, 2, null, S.gray3, 1);
      return o;
    } });
  def({ id: 'east-common-prop-pasture-trough-01', name: '草料槽与草垛', category: 'prop', kind: 'prop_fodder_trough', resource: 'livestock', facility: null,
    w: 1, d: 1, up: 24, tags: ['pasture', 'fodder', 'trough'], note: '木料槽装青草，后面一小垛干草',
    draw: function () {
      var o = C.shadowEll(26, 44, 20, 3.6) + path('M18 34 Q22 12 34 12 Q44 16 44 34 Z', S.thatch, G, LD) + path('M24 24 Q32 18 40 24', null, S.thatch2, 1);
      return o + K2.box(4, 38, 44, 7, 7, S.leaf2, S.wood) + ln(6, 36, 36, 36, S.leaf3, 1.2);
    } });
  def({ id: 'east-common-prop-pasture-sheep-01', name: '羊群', category: 'prop', kind: 'prop_sheep', resource: 'wool', facility: null,
    w: 1, d: 1, up: 16, tags: ['pasture', 'sheep', 'wool'], note: '三只绵羊，可散放在草场格上',
    draw: function () { return beast(14, 30, 'sheep', 0.9) + beast(34, 36, 'sheep', 0.9) + beast(18, 46, 'sheep', 1); } });
  def({ id: 'east-common-prop-pasture-woolbales-01', name: '剪毛台与毛包', category: 'prop', kind: 'prop_wool_bales', resource: 'wool', facility: null,
    w: 1, d: 1, up: 16, tags: ['wool', 'shearing'], note: '木台上一堆剪下的羊毛，旁边两只麻布毛包',
    draw: function () {
      var o = C.shadow([[4, 44], [44, 42], [47, 47], [7, 48]]) + K2.box(4, 26, 44, 6, 10, S.wood2, S.wood);
      o += circ(10, 26, 4, S.cream2, G, 0.6) + circ(16, 25, 4.6, S.cream2, G, 0.6) + circ(21, 27, 3.6, S.cream2, G, 0.6);
      [[34, 44], [40, 34]].forEach(function (p) { o += rect(p[0] - 6, p[1] - 10, 12, 10, S.thatch, G, LD) + ln(p[0] - 6, p[1] - 5, p[0] + 6, p[1] - 5, S.wood3, 1); });
      return o;
    } });
  def({ id: 'east-common-prop-horse-post-01', name: '拴马桩与马', category: 'prop', kind: 'prop_horse_post', resource: 'horses', facility: null,
    w: 1, d: 1, up: 30, tags: ['horses', 'hitching'], note: '石雕拴马桩上拴一匹鞍马',
    draw: function () {
      var o = beast(28, 44, 'horse', 1.25) + rect(22, 26, 10, 3, S.vermil, G, 0.6);
      return o + rect(4, 12, 6, 32, S.gray2, G, LD) + circ(7, 10, 4, S.gray3, G, LD) + ln(10, 20, 36, 26, S.wood3, 0.8);
    } });

  // ---------------- 染坊原料 dye ----------------
  var INDIGO = '#2c4f86', INDIGO2 = '#4a6fa8';
  def({ id: 'east-common-site-indigopit-01', name: '蓝靛池', category: 'site', kind: 'site_indigo_vats', resource: 'dye', facility: null,
    w: 3, d: 2, up: 30, tags: ['dye', 'indigo', 'vat', 'pool'], note: '石砌长方沤靛池两口：蓼蓝叶浸泡成靛泥，池边木耙打靛，后侧堆待沤的蓝草捆与靛泥缸；无对应 FacilityKind',
    draw: function (W, D, r, id) {
      var o = K2.pad(2, 2, W - 2, D - 2, S.earth3, 0.4);
      // 后侧蓝草捆
      for (var k = 0; k < 6; k++) o += path('M' + (12 + k * 14) + ' 20 Q' + (16 + k * 14) + ' 2 ' + (22 + k * 14) + ' 20 Z', S.leaf, G, 0.8) + ln(14 + k * 14, 14, 21 + k * 14, 14, S.thatch2, 1);
      [[8, 28, 64, 76], [74, 28, 130, 76]].forEach(function (p, i) {
        o += rect(p[0], p[1], p[2] - p[0], p[3] - p[1], S.gray2, G, LW) + rect(p[0] + 4, p[1] + 4, p[2] - p[0] - 8, p[3] - p[1] - 10, S.gray, null, 0);
        o += rect(p[0] + 6, p[1] + 8, p[2] - p[0] - 12, p[3] - p[1] - 16, i ? INDIGO : S.waterDeep, G, LD);
        for (var j = 0; j < 4; j++) o += path('M' + (p[0] + 12 + j * 10) + ' ' + (p[1] + 18 + (j % 2) * 10) + 'q3 -2 6 0', null, i ? INDIGO2 : S.water, 1);
        o += rect(p[0], p[3] - 6, p[2] - p[0], 6, S.gray3, G, LD);
      });
      o += K2.bar(110, 44, 90, 86, 1.6, S.wood2) + poly([[86, 84], [96, 86], [94, 90], [84, 88]], S.wood3, G, 0.7);
      // 靛泥缸
      o += ell(138, 74, 7, 2.4, INDIGO, G, LD) + path('M131 74 Q130 90 138 92 Q146 90 145 74', S.brown2, G, LD);
      return o;
    } });
  def({ id: 'east-common-prop-dye-clothrack-01', name: '晒布架', category: 'prop', kind: 'prop_cloth_rack', resource: 'dye', facility: null,
    w: 1, d: 1, up: 44, tags: ['dye', 'cloth', 'drying', 'bamboo'], note: '高竹架挂两幅长布：一幅靛蓝、一幅蓝白扎染',
    draw: function () {
      var o = C.shadow([[6, 44], [44, 42], [46, 46], [8, 48]]);
      o += K2.bamboo(6, 44, 6, 0, 1.8) + K2.bamboo(42, 44, 42, 0, 1.8) + K2.bamboo(2, 2, 46, 2, 1.6);
      o += path('M9 3 L23 3 L23 38 Q16 41 9 38 Z', INDIGO, G, LD) + path('M25 3 L39 3 L39 34 Q32 37 25 34 Z', S.cream2, G, LD);
      for (var i = 0; i < 3; i++) o += circ(32, 10 + i * 9, 3, INDIGO2, null, 0) + circ(32, 10 + i * 9, 1.2, S.cream2, null, 0);
      return o + ln(12, 8, 12, 36, INDIGO2, 0.8) + ln(19, 8, 19, 36, INDIGO2, 0.8);
    } });
  def({ id: 'east-common-prop-dye-vats-01', name: '染缸', category: 'prop', kind: 'prop_dye_vats', resource: 'dye', facility: null,
    w: 1, d: 1, up: 14, tags: ['dye', 'vat'], note: '两口陶染缸，一口靛蓝、一口红花色，缸沿搭一根挑布棍',
    draw: function () {
      var o = C.shadowEll(26, 44, 20, 3.6);
      [[14, INDIGO], [34, S.vermil]].forEach(function (p) { o += path('M' + (p[0] - 9) + ' 30 Q' + (p[0] - 10) + ' 44 ' + p[0] + ' 45 Q' + (p[0] + 10) + ' 44 ' + (p[0] + 9) + ' 30 Z', S.brown2, G, LD) + ell(p[0], 30, 9, 3, p[1], G, LD); });
      return o + K2.bar(6, 24, 44, 32, 1.2, S.wood2);
    } });
  def({ id: 'east-common-prop-dye-indigoplants-01', name: '蓼蓝田垄', category: 'prop', kind: 'prop_indigo_plants', resource: 'dye', facility: null,
    w: 1, d: 1, up: 12, tags: ['dye', 'indigo', 'plant'], note: '两垄蓼蓝，开红色穗花',
    draw: function (W, D, r) {
      var o = '';
      [24, 42].forEach(function (y) {
        o += ell(24, y, 21, 3, S.earth3, null, 0);
        for (var i = 0; i < 5; i++) { var x = 6 + i * 9; o += circ(x, y - 4, 4, S.leaf3, G, 0.6) + circ(x - 1, y - 5, 2, S.leaf, null, 0) + ln(x + 1, y - 7, x + 2, y - 11, S.vermil, 1.4); }
      });
      return o;
    } });

  return { defs: defs, all: function () { return defs.map(C.make); } };
});
