/*
 * 织梦 · east-site · 水边类资源点：盐场（salt：海盐晒场 + 井盐天车/熬盐灶棚）、渔场（fish）、芦苇荡（reed）、珍珠（pearls）。
 * 水色统一 S.water = #6cc1b3（与 east-ground 驳岸水面一致）。
 * 浏览器挂 window.TownArtES_water，Node 用 module.exports。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory(require('./core.js'), require('./kit.js'), require('./kit2.js'));
  else root.TownArtES_water = factory(root.TownArtES_core, root.TownArtES_kit, root.TownArtES_kit2);
})(this, function (C, K, K2) {
  'use strict';
  var S = C.S, f = C.f, poly = C.poly, path = C.path, rect = C.rect, ell = C.ell, circ = C.circ, ln = C.ln;
  var G = S.ink, G2 = S.ink2, LW = S.lw, LD = S.lwd;
  var defs = [];
  function def(o) { defs.push(o); }

  // ---------------- 盐场 salt ----------------
  /** 海盐晒场格（专用地面）：泥埂围成方格，格内卤水 / 结晶白盐，可平铺（埂沿格边，左右上下对称）。 */
  function saltTile(v) {
    return { id: 'east-common-ground-saltpan-0' + v, name: '海盐晒场格 ' + v, category: 'ground', kind: 'ground_saltpan', resource: 'salt', facility: null,
      variant: v, w: 1, d: 1, up: 0, tags: ['tileable', 'saltpan', 'brine'], note: '泥埂方格晒盐池：埂宽 4px 沿格边，相邻格拼成连续埂网；1=卤水，2=半结晶，3=结满白盐',
      draw: function (W, D, r, id) {
        var o = rect(-0.5, -0.5, 49, 49, S.earth2);
        var inner = [[4, 4], [44, 4], [44, 44], [4, 44]];
        if (v === 1) o += K2.water(inner, id, r);
        else if (v === 2) { o += K2.water(inner, id, r); for (var i = 0; i < 7; i++) o += ell(10 + r() * 28, 10 + r() * 28, 3 + r() * 4, 1.6 + r() * 2, S.salt, null, 0, C.fop(0.9)); }
        else { o += poly(inner, S.salt, G, LD); for (var k = 0; k < 6; k++) o += ln(8 + r() * 30, 8 + r() * 30, 12 + r() * 30, 9 + r() * 30, S.gray3, 0.6, C.op(0.6)); o += path('M14 40 Q24 26 34 40 Z', S.cream2, G, 0.7); }
        o += ln(4, 4.6, 44, 4.6, S.earth, 1.2) + ln(4.6, 4, 4.6, 44, S.earth, 1.2);
        return o;
      } };
  }
  def(saltTile(1)); def(saltTile(2)); def(saltTile(3));

  def({ id: 'east-common-site-saltfield-01', name: '海盐晒场·盐廪棚', category: 'site', kind: 'site_salt_shed', resource: 'salt', facility: 'warehouse',
    w: 3, d: 2, up: 50, tags: ['salt', 'sea_salt', 'shed', 'heap'], roof: 'gable_thatch', note: '晒场边的茅草盐廪，棚下白盐堆成尖堆，前有刮盐木耙与盐担；facility 取 warehouse（存盐），晒池本身用 ground_saltpan',
    draw: function (W, D, r, id) {
      var o = K2.pad(2, 4, W - 2, D - 2, S.earth, 0.5);
      o += C.shadow([[118, 24], [128, 30], [128, 66], [118, 60]]);
      o += rect(12, 22, 106, 40, S.brown2, G, LD) + rect(12, 22, 106, 40, S.shadow, null, 0, C.fop(0.2));
      // 棚内两座尖盐堆
      [[40, 60, 22], [88, 60, 20]].forEach(function (p) {
        o += path('M' + (p[0] - p[2]) + ' ' + p[1] + ' Q' + p[0] + ' ' + (p[1] - p[2] * 1.7) + ' ' + (p[0] + p[2]) + ' ' + p[1] + ' Z', S.salt, G, LD);
        o += path('M' + (p[0] - p[2] * 0.4) + ' ' + (p[1] - 6) + ' Q' + p[0] + ' ' + (p[1] - p[2] * 1.2) + ' ' + (p[0] + p[2] * 0.2) + ' ' + (p[1] - 10), null, S.gray3, 0.8);
      });
      [12, 65, 118].forEach(function (x) { o += K.post(x, 20, 64, 3.2); });
      o += K.roof(id, 10, 120, -20, 22, 6, S.thatch, 'thatch', 3);
      // 前方：刮盐木耙、盐担、一小堆盐
      o += K2.bar(20, 90, 44, 72, 1.6, S.wood2) + K2.bar(14, 86, 26, 94, 2.4, S.wood3);
      o += K2.basket(110, 92, 13, 9, S.salt, S.cream2, r) + K2.basket(132, 90, 13, 9, S.salt, S.cream2, r) + K2.bar(100, 76, 142, 74, 1.4, S.wood2);
      o += C.shadowEll(70, 92, 14, 3) + path('M56 92 Q70 74 84 92 Z', S.salt, G, LD);
      return o;
    } });

  def({ id: 'east-common-site-brinewell-01', name: '井盐·卤井天车', category: 'site', kind: 'site_brine_derrick', resource: 'salt', facility: 'well',
    w: 2, d: 2, up: 140, tags: ['salt', 'well_salt', 'derrick', 'tianche'], note: '川式卓筒井天车：四根杉木捆扎成高架，顶上天滚，竹篾索吊汲卤竹筒入井；地面绞车（大车）收索；facility 取 well',
    draw: function (W, D, r) {
      var o = K2.pad(2, 6, W - 2, D - 2, S.earth3, 0.4);
      o += C.shadow([[56, 88], [92, 92], [92, 96], [56, 92]]);
      // 井口：石井圈 + 竹筒
      o += ell(38, 72, 10, 4, S.gray2, G, LW) + ell(38, 72, 6, 2.2, '#1d1b20', null, 0);
      // 天车高架：四条腿向上收拢成塔（前两条腿实画，后两条稍暗）
      o += K2.bar(22, 62, 34, -132, 2.4, S.wood3) + K2.bar(54, 62, 42, -132, 2.4, S.wood3);
      o += K2.bar(16, 80, 33, -134, 3, S.wood) + K2.bar(60, 80, 43, -134, 3, S.wood);
      for (var i = 0; i < 6; i++) { var y = 60 - i * 32, t = (80 - y) / 214; o += K2.bar(16 + 17 * t, y + 10, 60 - 17 * t, y + 10, 1.4, S.wood2); }
      for (i = 0; i < 5; i++) { var ya = 70 - i * 32, yb = ya - 32, ta = (80 - ya) / 214, tb = (80 - yb) / 214; o += ln(16 + 17 * ta, ya, 60 - 17 * tb, yb, S.wood3, 0.9, C.op(0.8)); }
      // 天滚与汲卤竹筒
      o += circ(38, -134, 5, S.wood2, G, LD) + circ(38, -134, 1.6, S.wood3, null, 0);
      o += ln(36, -132, 36, 40, S.thatch2, 1) + ln(42, -134, 80, 70, S.thatch2, 1);
      o += K2.bamboo(36, 40, 36, 66, 3.2);
      // 地面绞车（大车）
      o += K2.box(70, 90, 86, 8, 6, S.wood2, S.wood3) + K2.wheel(80, 66, 12, 8) + K.post(68, 58, 86, 2.6) + K.post(92, 58, 86, 2.6);
      // 卤水木桶
      o += rect(8, 80, 12, 10, S.wood, G, LD) + ell(14, 80, 6, 2, S.water, G, 0.8);
      return o;
    } });

  def({ id: 'east-common-site-boilhouse-01', name: '井盐·熬盐灶棚', category: 'site', kind: 'site_salt_boiling', resource: 'salt', facility: 'boiler_house',
    w: 3, d: 2, up: 66, tags: ['salt', 'well_salt', 'boiling', 'pan', 'smoke'], roof: 'gable_tile', note: '长条灶台上并排三口熬盐铁锅（牢盆），灶门朝前烧柴，屋脊开气窗出蒸汽，右侧砖烟囱；facility 取 boiler_house',
    draw: function (W, D, r, id) {
      var o = K2.pad(2, 4, W - 2, D - 2, S.earth3, 0.45);
      o += C.shadow([[112, 20], [124, 26], [124, 66], [112, 60]]);
      // 砖烟囱（后）
      o += rect(118, -36, 12, 62, S.brown2, G, LW) + rect(116, -40, 16, 5, S.gray, G, LD);
      for (var y = -30; y < 24; y += 6) o += ln(118, y, 130, y, S.brown, 0.6, C.op(0.6));
      o += K2.smoke(124, -40, 0.9);
      // 后墙
      o += rect(10, 18, 102, 44, S.cream, G, LD) + rect(10, 18, 102, 44, S.shadow, null, 0, C.fop(0.18));
      // 灶台 + 三口锅 + 灶门火光
      o += K2.box(14, 108, 72, 12, 14, S.gray2, S.gray);
      [32, 61, 90].forEach(function (x) {
        o += ell(x, 53, 12, 4.5, '#2e3036', G, LD) + ell(x, 53, 9, 3, S.salt, null, 0) + ell(x, 52.5, 5, 1.6, S.water2, null, 0);
        o += path('M' + (x - 5) + ' 72 L' + (x - 5) + ' 65 Q' + x + ' 61 ' + (x + 5) + ' 65 L' + (x + 5) + ' 72 Z', '#1d1b20', G, 0.8) + circ(x, 69, 2.4, S.orange, null, 0);
      });
      [10, 61, 112].forEach(function (x) { o += K.post(x, 16, 64, 3.2, S.vermil); });
      o += K.roof(id, 8, 114, -18, 18, 6, S.gray, 'tile', 4);
      // 气窗：屋脊上一段小屋顶 + 白汽
      o += rect(48, -26, 26, 8, S.gray2, G, LD) + K2.bar(46, -27, 76, -27, 2, S.navy);
      o += circ(56, -32, 4, S.cream2, G, 0.7, C.fop(0.7)) + circ(66, -36, 5, S.cream2, G, 0.7, C.fop(0.6));
      // 前方柴垛
      o += K.log(20, 50, 86, 3.4) + K.log(24, 54, 80, 3.4) + K.log(20, 50, 92, 3.4);
      o += K2.basket(128, 90, 12, 9, S.salt, S.cream2, r);
      return o;
    } });

  def({ id: 'east-common-prop-salt-rake-01', name: '刮盐木耙与盐堆', category: 'prop', kind: 'prop_salt_heap', resource: 'salt', facility: null,
    w: 1, d: 1, up: 20, tags: ['salt', 'heap', 'rake'], note: '晒场边刮拢的白盐尖堆，斜靠一把长柄木耙',
    draw: function () {
      var o = C.shadowEll(26, 44, 18, 3.6) + path('M8 44 Q22 18 40 44 Z', S.salt, G, LD) + path('M16 38 Q22 28 28 32', null, S.gray3, 0.8);
      return o + K2.bar(40, 10, 34, 42, 1.4, S.wood2) + K2.bar(34, 10, 46, 12, 2, S.wood3);
    } });
  def({ id: 'east-common-prop-salt-brinetub-01', name: '卤水桶担', category: 'prop', kind: 'prop_brine_tubs', resource: 'salt', facility: null,
    w: 1, d: 1, up: 18, tags: ['salt', 'brine', 'bucket'], note: '一副扁担两只木桶装卤水',
    draw: function () {
      var o = C.shadow([[6, 44], [44, 42], [46, 46], [8, 48]]);
      [14, 34].forEach(function (x) { o += rect(x - 7, 30, 14, 14, S.wood, G, LD) + ln(x - 7, 34, x + 7, 34, S.wood3, 1.2) + ln(x - 7, 40, x + 7, 40, S.wood3, 1.2) + ell(x, 30, 7, 2.2, S.water, G, 0.8); });
      return o + K2.bar(4, 22, 44, 20, 1.6, S.wood2) + ln(14, 22, 14, 30, S.thatch2, 0.8) + ln(34, 20, 34, 30, S.thatch2, 0.8);
    } });
  def({ id: 'east-common-prop-salt-sacks-01', name: '盐包垛', category: 'prop', kind: 'prop_salt_sacks', resource: 'salt', facility: null,
    w: 1, d: 1, up: 14, tags: ['salt', 'sacks'], note: '蒲包装盐，三包一垛，盖朱红盐引印',
    draw: function () {
      var o = C.shadow([[6, 44], [44, 42], [47, 47], [9, 48]]);
      [[14, 44], [34, 44], [24, 34]].forEach(function (p) {
        o += path('M' + (p[0] - 10) + ' ' + p[1] + ' Q' + (p[0] - 11) + ' ' + (p[1] - 12) + ' ' + p[0] + ' ' + (p[1] - 13) + ' Q' + (p[0] + 11) + ' ' + (p[1] - 12) + ' ' + (p[0] + 10) + ' ' + p[1] + ' Z', S.thatch, G, LD);
        o += rect(p[0] - 2.5, p[1] - 8, 5, 4, S.vermil, null, 0) + ln(p[0] - 8, p[1] - 3, p[0] + 8, p[1] - 3, S.thatch2, 0.8);
      });
      return o;
    } });

  // ---------------- 渔场 fish ----------------
  /** 前半占地是水面：从 y0 到 D 画一片水（与 east-ground 同色），给栈桥、竹排等用。 */
  function waterFront(W, D, y0, id, r) { return K2.water([[0, y0], [W, y0], [W, D], [0, D]], id, r, true) + ln(0, y0 + 0.5, W, y0 + 0.5, S.earth3, 2); }

  def({ id: 'east-common-site-fishpier-01', name: '渔家栈桥', category: 'site', kind: 'site_fishing_pier', resource: 'fish', facility: 'dock',
    w: 3, d: 3, up: 52, tags: ['fishing', 'pier', 'hut', 'water'], roof: 'gable_thatch', note: '岸上一间茅草渔寮，木栈桥伸进水里，桥头拴一条小舢板；占地后 1 格是岸、前 2 格是水',
    draw: function (W, D, r, id) {
      var o = K2.pad(0, 0, W, 46, S.earth, 0.5) + waterFront(W, D, 46, id, r);
      // 渔寮（左后）
      o += C.shadow([[70, 6], [80, 12], [80, 44], [70, 40]]);
      o += rect(10, 10, 60, 32, S.cream, G, LD) + rect(34, 22, 12, 20, S.wood3, G, LD) + rect(16, 20, 10, 8, S.brown, G, 0.8) + ln(21, 20, 21, 28, S.wood2, 0.8);
      o += K.roof(id, 10, 70, -14, 12, 5, S.thatch, 'thatch', 3);
      // 栈桥：桥桩 + 桥面板，向前伸出
      for (var y = 52; y < 140; y += 14) o += K.post(96, y - 2, y + 8, 3, S.wood3) + K.post(124, y - 2, y + 8, 3, S.wood3);
      o += rect(94, 36, 32, 100, S.wood2, G, LW);
      for (y = 40; y < 136; y += 5) o += ln(95, y, 125, y, S.wood3, 0.8, C.op(0.7));
      // 舢板
      o += path('M60 112 Q70 100 92 104 L92 122 Q70 126 60 112 Z', S.wood, G, LW) + path('M66 112 Q72 106 88 108 L88 118 Q72 120 66 112 Z', S.wood3, null, 0);
      o += ln(92, 112, 98, 104, S.thatch2, 0.9);
      // 桥头竹篙、鱼篓
      o += K2.bamboo(132, 40, 140, 8, 1.6) + K2.basket(112, 50, 10, 8, S.teal2, S.teal, r);
      return o;
    } });

  def({ id: 'east-common-prop-fish-netrack-01', name: '晒网竹架', category: 'prop', kind: 'prop_net_rack', resource: 'fish', facility: null,
    w: 1, d: 1, up: 34, tags: ['fishing', 'net', 'bamboo'], note: '两根竹竿一道横杆，渔网搭在上面晾晒',
    draw: function () {
      var o = C.shadow([[8, 44], [42, 42], [46, 46], [10, 48]]);
      o += K2.bamboo(8, 44, 8, 4, 1.8) + K2.bamboo(40, 44, 40, 4, 1.8) + K2.bamboo(4, 8, 44, 8, 1.6);
      var net = path('M8 9 Q12 30 10 40 L38 40 Q36 30 40 9 Z', S.navy2, G, 0.8, C.fop(0.35)), m = '';
      for (var x = 10; x < 40; x += 4) m += ln(x, 9, x + 1, 40, S.navy, 0.6);
      for (var y = 13; y < 40; y += 4) m += ln(9, y, 39, y, S.navy, 0.6);
      return o + net + m + ell(14, 40, 1.6, 1.6, S.gray3, G, 0.5) + ell(26, 40, 1.6, 1.6, S.gray3, G, 0.5) + ell(36, 40, 1.6, 1.6, S.gray3, G, 0.5);
    } });
  def({ id: 'east-common-prop-fish-creel-01', name: '鱼篓', category: 'prop', kind: 'prop_fish_creel', resource: 'fish', facility: null,
    w: 1, d: 1, up: 12, tags: ['fishing', 'basket'], note: '两只细颈竹鱼篓，一只倒着露出鱼尾',
    draw: function () {
      var o = C.shadowEll(26, 44, 18, 3.4);
      o += path('M8 44 Q4 32 12 28 L14 22 L20 22 L22 28 Q30 32 26 44 Z', S.thatch, G, LD) + ln(8, 36, 26, 36, S.thatch2, 0.8);
      o += path('M28 44 Q24 36 34 32 L42 34 Q46 40 42 44 Z', S.thatch, G, LD);
      return o + path('M42 34 L48 30 L47 38 Z', S.gray3, G, 0.7) + ell(36, 40, 4, 2, S.gray2, G, 0.6);
    } });
  def({ id: 'east-common-prop-fish-cormorant-01', name: '鸬鹚竹排', category: 'prop', kind: 'prop_cormorant_raft', resource: 'fish', facility: null,
    w: 1, d: 1, up: 18, tags: ['fishing', 'raft', 'cormorant', 'water'], note: '五根竹子扎成的窄排，两只鸬鹚立在排头；放在水面格上',
    draw: function (W, D, r, id) {
      var o = K2.water([[0, 0], [48, 0], [48, 48], [0, 48]], id, r, true);
      o += ell(24, 38, 22, 5, S.waterDeep, null, 0, C.fop(0.5));
      for (var i = 0; i < 5; i++) o += K2.bamboo(4, 30 + i * 2.2, 44, 30 + i * 2.2, 1.6);
      [[12, 28], [22, 27]].forEach(function (p) {
        o += ell(p[0], p[1] - 4, 3.4, 5, S.navy, G2, 0.7) + circ(p[0] + 1, p[1] - 10, 2, S.navy, G2, 0.6) + poly([[p[0] + 2.6, p[1] - 10.6], [p[0] + 6, p[1] - 9.4], [p[0] + 2.6, p[1] - 9.4]], S.ochre, null, 0);
      });
      return o + K2.bamboo(36, 34, 30, 12, 1.4);
    } });

  /** 浅水格（专用地面）：整格水面，水色同 east-ground；可平铺，波纹离边 ≥3 px。 */
  function shallowTile(v) {
    return { id: 'east-common-ground-shallows-0' + v, name: '浅水滩 ' + v, category: 'ground', kind: 'ground_shallows', resource: 'fish', facility: null,
      variant: v, w: 1, d: 1, up: 0, tags: ['tileable', 'water'], note: '渔场、芦苇荡、采珠场用的整格浅水，水色 #6cc1b3 与 east-ground 驳岸水面一致；无勾边，任意排列无缝',
      draw: function (W, D, r) {
        var o = rect(-0.5, -0.5, 49, 49, S.water), i;
        for (i = 0; i < 4 + v; i++) { var x = 6 + r() * 30, y = 6 + r() * 36; o += path('M' + f(x) + ' ' + f(y) + 'q3 -2 6 0 q3 2 6 0', null, S.water2, 1); }
        return o;
      } };
  }
  def(shallowTile(1)); def(shallowTile(2));

  // ---------------- 芦苇荡 reed ----------------
  /** 一丛芦苇：几根细秆 + 芦花穗。 */
  function reedClump(x, yb, h, n, r) {
    var o = '';
    for (var i = 0; i < n; i++) {
      var dx = (i - n / 2) * 2.2 + r() * 1.5, hh = h * (0.75 + r() * 0.3), tx = x + dx + (r() - 0.4) * 5, ty = yb - hh;
      o += path('M' + f(x + dx) + ' ' + f(yb) + 'Q' + f(x + dx) + ' ' + f(yb - hh * 0.5) + ' ' + f(tx) + ' ' + f(ty), null, S.leaf3, 1.1);
      if (i % 2 === 0) o += path('M' + f(x + dx) + ' ' + f(yb - hh * 0.3) + 'q' + f(4 + r() * 3) + ' -4 ' + f(8 + r() * 3) + ' -3', null, S.leaf2, 1);
      o += ell(tx + 1, ty - 3, 1.6, 4, S.thatch, G, 0.5);
    }
    return o;
  }
  def({ id: 'east-common-site-reedbed-01', name: '芦苇荡·割苇滩', category: 'site', kind: 'site_reed_bed', resource: 'reed', facility: null,
    w: 3, d: 2, up: 40, tags: ['reed', 'marsh', 'water', 'boat'], note: '浅水里密生芦苇，中间割开一条水道，泊一只装满苇捆的平底小船，岸边立苇捆；无对应 FacilityKind',
    draw: function (W, D, r, id) {
      var o = K2.water([[0, 0], [W, 0], [W, D], [0, D]], id, r, true);
      for (var y = 14; y <= 86; y += 12) for (var x = 8; x < W; x += 13) {
        if (x > 54 && x < 98 && y > 34) continue; // 水道
        o += reedClump(x + (y % 24 ? 5 : 0), y, 26, 4, r);
      }
      o += path('M58 82 Q62 66 78 64 L100 64 Q104 74 98 84 Z', S.wood, G, LW) + path('M64 78 Q66 70 78 69 L96 69 Q98 74 94 80 Z', S.wood3, null, 0);
      for (var k = 0; k < 3; k++) o += rect(68 + k * 9, 58, 7, 14, S.thatch, G, 0.8) + ln(68 + k * 9, 64, 75 + k * 9, 64, S.wood3, 1);
      o += K2.bamboo(104, 86, 120, 50, 1.6);
      return o;
    } });
  def({ id: 'east-common-prop-reed-bundles-01', name: '苇捆', category: 'prop', kind: 'prop_reed_bundles', resource: 'reed', facility: null,
    w: 1, d: 1, up: 36, tags: ['reed', 'bundle'], note: '割下的芦苇扎成捆，三捆互相斜靠成垛',
    draw: function () {
      var o = C.shadow([[10, 44], [42, 42], [46, 47], [12, 48]]);
      [[12, 44, -4], [36, 44, 4], [24, 44, 0]].forEach(function (p) {
        o += poly([[p[0] - 5, p[1]], [p[0] + 5, p[1]], [p[0] + 3 + p[2], p[1] - 34], [p[0] - 3 + p[2], p[1] - 34]], S.thatch, G, LD);
        for (var i = -2; i <= 2; i++) o += ln(p[0] + i * 1.6, p[1] - 1, p[0] + i * 1.2 + p[2], p[1] - 33, S.thatch2, 0.6);
        o += ln(p[0] - 4.4 + p[2] * 0.4, p[1] - 14, p[0] + 4.4 + p[2] * 0.4, p[1] - 14, S.wood3, 1.6);
        o += ell(p[0] + p[2], p[1] - 36, 4, 3, S.cream2, G, 0.6);
      });
      return o;
    } });
  def({ id: 'east-common-prop-reed-clump-01', name: '芦苇丛', category: 'prop', kind: 'prop_reed_clump', resource: 'reed', facility: null,
    w: 1, d: 1, up: 30, tags: ['reed', 'plant'], note: '水边一丛芦苇，可散放在浅水格上',
    draw: function (W, D, r) { return reedClump(14, 42, 32, 5, r) + reedClump(32, 44, 28, 4, r); } });

  // ---------------- 珍珠 pearls ----------------
  def({ id: 'east-common-site-pearlboat-01', name: '采珠渔船', category: 'site', kind: 'site_pearl_boat', resource: 'pearls', facility: null,
    w: 3, d: 2, up: 46, tags: ['pearls', 'boat', 'diving', 'water'], note: '整片占地是水面；篷船船尾立绞绳木架，系绳下潜采珠，船头一筐珠蚌；无对应 FacilityKind',
    draw: function (W, D, r, id) {
      var o = K2.water([[0, 0], [W, 0], [W, D], [0, D]], id, r, true);
      o += ell(72, 76, 64, 10, S.waterDeep, null, 0, C.fop(0.45));
      // 船身
      o += path('M10 58 Q20 76 70 78 Q118 78 136 56 L128 54 Q100 64 70 64 Q34 64 18 54 Z', S.wood, G, LW);
      o += path('M18 54 Q34 62 70 62 Q100 62 128 54 L122 48 Q96 56 70 56 Q40 56 24 48 Z', S.wood3, G, LD);
      // 竹篷
      o += path('M44 54 L44 30 Q70 16 96 30 L96 54 Z', S.thatch2, G, LW);
      for (var x = 48; x < 96; x += 6) o += ln(x, 28 - (x > 70 ? (96 - x) : (x - 44)) * 0.2, x, 54, S.thatch, 1);
      // 船尾绞绳架 + 入水绳 + 水花
      o += K2.bar(116, 52, 116, 14, 2.2, S.wood3) + K2.bar(108, 16, 128, 16, 1.8, S.wood2) + K2.wheel(116, 24, 5, 4);
      o += ln(126, 16, 134, 82, S.thatch2, 0.9) + ell(134, 84, 6, 2, S.water2, G, 0.6);
      // 船头珠蚌筐
      o += K2.basket(28, 56, 12, 8, S.cream2, S.gray3, r);
      return o;
    } });
  def({ id: 'east-common-prop-pearl-shells-01', name: '蚌壳堆', category: 'prop', kind: 'prop_shell_heap', resource: 'pearls', facility: null,
    w: 1, d: 1, up: 14, tags: ['pearls', 'shell'], note: '剖过的珠蚌壳堆成小丘，内壁珠光，前面一只盛珍珠的小木盘',
    draw: function (W, D, r) {
      var o = C.shadowEll(26, 44, 20, 4) + path('M6 42 Q16 26 26 26 Q38 26 44 42 Z', S.gray3, G, LD);
      for (var i = 0; i < 9; i++) {
        var x = 10 + r() * 28, y = 30 + r() * 11;
        o += ell(x, y, 4.4, 2.6, S.navy2, G, 0.6) + ell(x + 0.6, y - 0.4, 3, 1.6, S.cream2, null, 0);
      }
      o += ell(36, 44, 7, 2.6, S.wood2, G, LD);
      for (var k = 0; k < 4; k++) o += circ(33 + k * 2, 43.4, 1, '#fffaf0', G, 0.3);
      return o;
    } });
  def({ id: 'east-common-prop-pearl-drying-01', name: '晒蚌竹匾', category: 'prop', kind: 'prop_shell_tray', resource: 'pearls', facility: null,
    w: 1, d: 1, up: 12, tags: ['pearls', 'tray', 'bamboo'], note: '竹凳上架一只大竹匾，晒着剖开的蚌肉与蚌壳',
    draw: function (W, D, r) {
      var o = C.shadowEll(26, 44, 20, 3.6) + K.post(12, 30, 44, 2, S.wood3) + K.post(36, 30, 44, 2, S.wood3);
      o += ell(24, 28, 20, 8, S.thatch, G, LD) + ell(24, 28, 16, 6, null, S.thatch2, 0.8);
      for (var i = 0; i < 6; i++) o += ell(14 + i * 4, 27 + (i % 2) * 2, 2.6, 1.6, S.cream2, G, 0.5);
      return o;
    } });

  return { defs: defs, all: function () { return defs.map(C.make); } };
});
