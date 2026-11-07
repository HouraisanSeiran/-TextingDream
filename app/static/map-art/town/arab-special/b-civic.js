/*
 * 公共类：行政厅、宫殿、学院、医院、公共浴室、蓄水池、井亭。
 * 浏览器追加到 window.TownArtAS_defs；Node 用 module.exports 导出数组。
 */
(function (root) {
  'use strict';
  var N = typeof module !== 'undefined' && module.exports;
  var K = N ? require('./core.js') : root.TownArtAS_core;
  var P = N ? require('./parts.js') : root.TownArtAS_parts;
  var Ms = N ? require('./mass.js') : root.TownArtAS_mass;
  var T = N ? require('./towers.js') : root.TownArtAS_towers;
  var G = N ? require('./ground.js') : root.TownArtAS_ground;
  var F = N ? require('./facade.js') : root.TownArtAS_facade;
  var C = K.C, f = K.f;
  var defs = [];

  /** 旗杆 + 三角旗 */
  function flag(x, by, h, col) {
    return K.ln(K.seg(x, by, x, by - h), 1.1, 1, C.wood) +
      K.poly([[x, by - h], [x + 11, by - h + 3], [x, by - h + 6]], col || C.palm, 0.8) + K.circle(x, by - h - 1, 1.2, C.gold, 0.4);
  }

  defs.push({
    id: 'arab-common-townhall-01', name: '行政厅（迪万）', fp: [3, 2], up: 92, kind: 'diwan', facility: 'town_hall',
    tags: ['two_storey', 'mashrabiya', 'arcade', 'flag'], roof: 'flat_mud',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, cx = W / 2, s = '';
      var x0 = 8, x1 = W - 8, yf = H - 5, h = 56, ty = gy + 6 - h;
      s += Ms.block({ x0: x0, x1: x1, yb: gy + 6, yf: yf, h: h, lip: 3, band: 4, W: W, H: H });
      // 屋顶小亭（八角穹顶）+ 旗
      s += K.rect(cx - 14, ty + 4, 28, 16, C.lime, 1.2) + F.arcade(cx - 12, cx + 12, ty + 20, 10, 3, C.hole);
      s += K.rect(cx - 16, ty + 1, 32, 3, C.lime2, 0.9) + Ms.dome(cx, ty + 1, 13, 17, C.palm2, 'pointed');
      s += flag(x0 + 10, ty + 14, 30, C.palm) + flag(x1 - 10, ty + 14, 30, C.palm);
      // 二层木格窗 + 底层拱廊 + 门
      s += F.windows(x0 + 8, cx - 18, yf - h + 10, 11, 14, 2, true) + F.windows(cx + 18, x1 - 8, yf - h + 10, 11, 14, 2, true);
      s += F.arcade(x0 + 4, x1 - 4, yf - 1, 20, 6, C.hole, C.lime2);
      s += F.pishtaq(cx - 18, cx + 18, yf, yf - h + 6, { alt: true });
      return s;
    }
  });

  defs.push({
    id: 'arab-common-palace-01', name: '宫殿（总督府）', fp: [4, 3], up: 124, kind: 'palace', facility: 'lord_hall',
    tags: ['dome', 'iwan', 'towers', 'mashrabiya', 'garden_front', 'crenellated'], roof: 'flat_mud', note: '穹顶无对应 RoofId，按 flat_mud 记',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, cx = W / 2, s = '';
      // 后殿：高块 + 洋葱穹顶 + 两侧小穹
      s += Ms.block({ x0: 30, x1: W - 30, yb: gy + 4, yf: gy + 62, h: 62, lip: 3, band: 5, bandAlt: true, W: W, H: H });
      var ty = gy + 4 - 62;
      s += Ms.drum(cx, ty + 12, 24, 10, C.lime) + Ms.dome(cx, ty + 2, 26, 46, C.gold, 'onion', C.ochre2);
      s += Ms.drum(50, ty + 14, 9, 5, C.lime, 0) + Ms.dome(50, ty + 9, 10, 14, C.turq, 'onion');
      s += Ms.drum(W - 50, ty + 14, 9, 5, C.lime, 0) + Ms.dome(W - 50, ty + 9, 10, 14, C.turq, 'onion');
      s += F.windows(36, W - 36, gy + 18, 12, 15, 5, true);
      // 前翼：低块 + 中央伊旺 + 雉堞
      s += Ms.block({ x0: 10, x1: W - 10, yb: gy + 64, yf: H - 6, h: 40, lip: 0, W: W, H: H });
      s += P.merlons(10, W - 10, H - 46, 5, C.lime);
      s += F.arcade(16, cx - 28, H - 7, 22, 3, C.hole, C.lime2) + F.arcade(cx + 28, W - 16, H - 7, 22, 3, C.hole, C.lime2);
      s += F.pishtaq(cx - 26, cx + 26, H - 6, H - 74, { alt: false });
      s += P.merlons(cx - 26, cx + 26, H - 74, 6, C.lime);
      // 两角塔
      [[2, 20], [W - 20, W - 2]].forEach(function (t) {
        s += K.rect(t[0], H - 96, t[1] - t[0], 90, C.lime, 1.5) + P.tileBand(t[0] + 1, t[1] - 1, H - 86, 4);
        s += K.flat([[t[1] - 6, H - 95], [t[1] - 0.8, H - 95], [t[1] - 0.8, H - 7], [t[1] - 6, H - 7]], C.adobe3, 0.22);
        s += P.mashrabiya(t[0] + 5, H - 72, 8, 12) + K.rect(t[0] - 1.5, H - 99, t[1] - t[0] + 3, 3, C.lime2, 1);
        s += P.merlons(t[0] - 1, t[1] + 1, H - 99, 5, C.lime, 1.4);
      });
      return s;
    }
  });

  defs.push({
    id: 'arab-common-madrasa-01', name: '学院（四伊旺经学院）', fp: [3, 3], up: 112, kind: 'madrasa', facility: 'academy',
    tags: ['courtyard', 'four_iwan', 'twin_minaret_portal', 'dome'], roof: 'flat_mud',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, cx = W / 2, s = '';
      // 后部讲堂穹顶
      s += Ms.drum(cx, gy - 2, 20, 9, C.lime) + Ms.dome(cx, gy - 11, 21, 34, C.turq, 'pointed');
      s += Ms.court({
        x0: 6, x1: W - 6, yb: gy + 4, yf: H - 4, h: 34, t: 12, riwaq: false, lip: 2, band: 4, W: W, H: H,
        content: function (q) {
          var t = F.pishtaq(q.cx - 16, q.cx + 16, q.fy, q.fy - 26 < q.fy - 30 ? q.fy - 26 : q.fy - 26, { door: false, star: false });
          t += F.arcade(q.ix0 + 2, q.cx - 18, q.fy, 12, 2, C.hole) + F.arcade(q.cx + 18, q.ix1 - 2, q.fy, 12, 2, C.hole);
          t += G.basin(q.cx - 12, q.cy - 4, 24, 14) + G.bed(q.ix0 + 4, q.cy - 2, 16, 12, 3) + G.bed(q.ix1 - 20, q.cy - 2, 16, 12, 4);
          return t;
        }
      });
      // 门楼 + 双小塔
      s += T.minaret(cx - 30, H - 50, 4, 58, { kind: 'round', tiers: 1, capFill: C.turq });
      s += T.minaret(cx + 30, H - 50, 4, 58, { kind: 'round', tiers: 1, capFill: C.turq });
      s += F.pishtaq(cx - 24, cx + 24, H - 4, H - 64, { alt: true });
      return s;
    }
  });

  defs.push({
    id: 'arab-common-bimaristan-01', name: '医院（比马里斯坦）', fp: [3, 2], up: 84, kind: 'bimaristan', facility: 'infirmary',
    tags: ['courtyard', 'dome', 'herb_garden', 'arcade'], roof: 'flat_mud',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, cx = W / 2, s = '';
      s += Ms.court({
        x0: 6, x1: W - 6, yb: gy + 4, yf: H - 4, h: 32, t: 10, riwaq: true, lip: 2, W: W, H: H,
        content: function (q) {
          return G.bed(q.ix0 + 4, q.fy + 4, 22, q.iyB - q.fy - 8, 17) + G.bed(q.ix1 - 26, q.fy + 4, 22, q.iyB - q.fy - 8, 19) +
            G.pool(q.cx, q.cy, 11, 7, false);
        }
      });
      s += Ms.drum(28, gy - 20, 12, 6, C.lime, 2) + Ms.dome(28, gy - 26, 13, 20, C.palm2, 'pointed');
      s += P.tileBand(8, W - 8, H - 30, 4, true);
      s += F.windows(14, cx - 22, H - 22, 5, 9, 3) + F.windows(cx + 22, W - 14, H - 22, 5, 9, 3);
      s += F.pishtaq(cx - 18, cx + 18, H - 4, H - 54, {});
      // 门旁药罐
      s += K.ellipse(cx - 24, H - 8, 3, 4, C.turq, 0.7) + K.ellipse(cx + 24, H - 8, 3, 4, C.turq, 0.7);
      return s;
    }
  });

  /** 小穹顶带星形天窗（浴室） */
  function starDome(cx, by, r, hh, fill) {
    var s = Ms.dome(cx, by, r, hh, fill || C.lime2, 'flat');
    // 去掉金尖不可行，改为在穹面加星形天窗玻璃
    var d = '';
    [[-0.45, 0.55], [0.1, 0.42], [0.5, 0.62], [-0.15, 0.78], [0.25, 0.85]].forEach(function (p) {
      var x = cx + p[0] * r, y = by - hh * p[1];
      d += K.pd([[x, y - 1.8], [x + 0.6, y - 0.6], [x + 1.8, y], [x + 0.6, y + 0.6], [x, y + 1.8], [x - 0.6, y + 0.6], [x - 1.8, y], [x - 0.6, y - 0.6]]);
    });
    return s + K.path(d, C.turq2, 0.4);
  }

  defs.push({
    id: 'arab-common-hammam-01', name: '公共浴室（哈曼）', fp: [3, 2], up: 70, kind: 'hammam', facility: 'cistern',
    tags: ['bathhouse', 'multi_dome', 'star_skylight', 'boiler'], roof: 'flat_mud',
    note: 'FacilityKind 无浴室，按用水设施 cistern 记；穹顶屋面按 flat_mud 记',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, cx = W / 2, s = '';
      var yf = H - 4, h = 34, ty = gy + 8 - h;
      s += Ms.block({ x0: 6, x1: W - 6, yb: gy + 8, yf: yf, h: h, lip: 2, W: W, H: H });
      // 后排小穹 + 前排大穹（热室 / 温室 / 更衣厅）
      // 屋面铺满：后排两小穹、中排两中穹、前排中央大穹（落在门楼之后）
      s += G.pavers(8, ty + 2, W - 8, yf - h - 2, 14, 23, 0.22);
      [[30, ty + 24, 10, 12], [W - 30, ty + 24, 10, 12], [26, ty + 54, 12, 14], [W - 26, ty + 54, 12, 14], [cx, ty + 24, 11, 12]].forEach(function (p) { s += starDome(p[0], p[1], p[2], p[3], C.lime2); });
      s += Ms.drum(cx, ty + 66, 20, 6, C.lime, 0) + starDome(cx, ty + 60, 22, 26, C.lime2);
      // 锅炉烟囱（右后）
      s += K.rect(W - 18, ty - 6, 8, 22, C.adobe2, 1.1) + K.rect(W - 19.5, ty - 8, 11, 2.4, C.adobe3, 0.8);
      s += K.ln('M' + f(W - 14) + ' ' + f(ty - 10) + 'q-3 -5 1 -9q4 -4 0 -9', 0.8, 0.45);
      s += P.tileBand(8, W - 8, yf - h + 4, 4);
      s += F.windows(14, cx - 20, yf - 22, 4, 7, 3) + F.windows(cx + 20, W - 14, yf - 22, 4, 7, 3);
      s += F.pishtaq(cx - 16, cx + 16, yf, yf - h - 8, { alt: true });
      // 门口挂的毛巾绳
      s += K.ln(K.seg(12, yf - 12, cx - 20, yf - 12), 0.7, 0.7);
      s += K.rect(16, yf - 12, 5, 7, C.turq2, 0.6) + K.rect(26, yf - 12, 5, 8, C.ochre2, 0.6) + K.rect(36, yf - 12, 5, 6, C.lime, 0.6);
      return s;
    }
  });

  defs.push({
    id: 'arab-common-abanbar-01', name: '蓄水池（阿布安巴，穹顶风塔）', fp: [2, 2], up: 104, kind: 'ab_anbar', facility: 'cistern',
    tags: ['dome', 'windtower', 'underground_tank', 'stair_portal'], roof: 'flat_mud', note: '地下蓄水池，地面上只露穹顶与风塔',
    draw: function (c) {
      var W = c.W, H = c.H, gy = c.gy, cx = W / 2, s = '';
      s += T.windtower(14, gy + 30, 12, 74, C.adobe) + T.windtower(W - 14, gy + 30, 12, 74, C.adobe);
      s += K.boxShadow(18, W - 18, gy + 20, H - 18, 6, W, H);
      s += K.ellipse(cx, gy + 40, 30, 10, C.adobe2, 1.3);
      s += Ms.dome(cx, gy + 40, 28, 38, C.adobe, 'pointed', C.adobe3);
      // 台基与下行台阶门
      s += K.rect(10, H - 22, W - 20, 18, C.adobe, 1.4) + P.merlons(10, W - 10, H - 22, 4, C.adobe);
      s += F.pishtaq(cx - 14, cx + 14, H - 4, H - 44, { door: false, star: false });
      var d = ''; for (var i = 0; i < 4; i++) d += K.seg(cx - 6 + i, H - 8 - i * 4, cx + 6 - i, H - 8 - i * 4);
      s += K.ln(d, 0.8, 0.8, C.lime2);
      return s;
    }
  });

  defs.push({
    id: 'arab-common-well-01', name: '水井与井亭（萨比尔）', fp: [1, 1], up: 52, kind: 'well_kiosk', facility: 'well',
    tags: ['well', 'kiosk', 'dome', 'public_water'], roof: 'none', note: '四柱小穹顶井亭；roof 按 none 记',
    draw: function (c) {
      var W = c.W, H = c.H, s = K.boxShadow(6, 42, H - 30, H - 4, 6, W, H);
      s += K.ellipse(24, H - 14, 13, 6, C.lime2, 1.2) + K.ellipse(24, H - 15, 9, 3.5, C.water, 0.9);
      s += K.rect(11, H - 14, 26, 8, C.lime2, 1.2) + P.tileBand(12, 36, H - 12, 3.5, true);
      [6, 39].forEach(function (x) { s += K.rect(x, H - 40, 3, 34, C.lime, 0.9); });
      s += K.rect(4, H - 44, 40, 5, C.lime, 1.1) + P.tileBand(5, 43, H - 43.5, 3.5);
      s += Ms.dome(24, H - 44, 16, 14, C.turq, 'pointed');
      s += K.ln(K.seg(24, H - 39, 24, H - 22), 0.7, 0.9, C.wood) + K.rect(21.5, H - 22, 5, 4, C.ochre, 0.7);
      return s;
    }
  });

  if (N) module.exports = defs;
  else root.TownArtAS_defs = (root.TownArtAS_defs || []).concat(defs);
})(this);
