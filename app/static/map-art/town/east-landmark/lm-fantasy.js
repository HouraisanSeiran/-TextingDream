/*
 * 织梦 · 东方文化地标（east-landmark）· 玄幻：浮空仙阁（美术素材，尚未接入游戏）
 * def 格式同 lm-taoist.js。浏览器挂 window.TownArtEastLandmarkFantasy；Node 用 module.exports。
 */
(function (root) {
  'use strict';
  var node = typeof module !== 'undefined' && module.exports;
  var K = node ? require('./lm-core.js') : root.TownArtEastLandmarkCore;
  var PT = node ? require('./lm-parts.js') : root.TownArtEastLandmarkParts;
  var X = node ? require('./lm-extra.js') : root.TownArtEastLandmarkExtra;
  var TT = node ? require('./lm-taoist.js') : root.TownArtEastLandmarkTaoist;
  var C = K.C, TILE = K.TILE, G = K.G, GL = K.GL, f = K.f, P = K.P, R = K.R, E = K.E, L = K.L;
  var defs = [];

  defs.push({
    kind: 'floating_pavilion', variant: 1, name: '浮空仙阁', facility: null, culture: 'taoist', category: 'landmark',
    fp: [3, 3], up: 180, tags: ['fantasy', 'floating', 'clouds', 'waterfall', 'cranes', 'immortal'], roof: 'hip_tile',
    note: '玄幻地标：一块倒锥形青绿山石浮在半空，底下层层祥云托举，岩边垂一道细瀑；岛面汉白玉栏杆，上立两层青绿琉璃楼阁' +
      '（平座回廊、斗拱、宝葫芦），阁前铜鼎香炉，两只仙鹤绕飞。地面只有一座石台、一对长幡与云影。FacilityKind 无对应（仙门 / 宗门道场），facility = null。',
    draw: function (K, W, U, D) {
      var s = '', cx = W / 2, B = U + D;
      // 地面：云影 + 石台 + 长幡
      s += E(cx + 8, B - 36, 54, 14, K.SH, null, 0, ' fill-opacity="0.2"');
      s += K.platform(cx - 30, cx + 30, B - 40, B - 10, 5) + K.steps(cx, B - 10, 18, 3);
      s += PT.bagua(cx, B - 26, 20, 0.42, 3);
      s += PT.pennant(cx - 44, B - 8, B - 70, 5, 26, C.ochre) + PT.pennant(cx + 44, B - 8, B - 70, 5, 26, C.ochre);
      // 托举的祥云柱：从地面一路叠到岛底
      s += X.cloud(cx - 6, B - 48, 50, { op: 0.9 }) + X.cloud(cx + 10, B - 70, 44, { flip: true, op: 0.9 });
      s += X.cloud(cx - 12, B - 92, 40, { op: 0.92 });
      // 瀑布：从岛右沿垂下，消失在云里
      var yT = U + 4;
      s += P('M' + f(cx + 40) + ' ' + f(yT + 10) + 'Q' + f(cx + 44) + ' ' + f(yT + 60) + ' ' + f(cx + 41) + ' ' + f(B - 96) + 'L' + f(cx + 47) + ' ' + f(B - 96) + 'Q' + f(cx + 50) + ' ' + f(yT + 60) + ' ' + f(cx + 46) + ' ' + f(yT + 10) + 'Z', '#cfe8e2', G, 0.6);
      s += L('M' + f(cx + 42.5) + ' ' + f(yT + 14) + 'Q' + f(cx + 46) + ' ' + f(yT + 60) + ' ' + f(cx + 43.5) + ' ' + f(B - 98), X.WATER, 0.7, 0.7);
      // 浮岛下半：倒锥山石
      s += X.rock([[cx - 62, yT], [cx + 62, yT], [cx + 54, yT + 22], [cx + 34, yT + 46], [cx + 14, yT + 74], [cx + 2, yT + 96], [cx - 8, yT + 80],
        [cx - 30, yT + 56], [cx - 50, yT + 30]], { seed: 21, k: 0.3, side: C.stoneDk });
      s += X.cloud(cx - 44, yT + 40, 46) + X.cloud(cx + 40, yT + 70, 40, { flip: true });
      // 岛面
      s += P(K.pts([[cx - 62, yT], [cx - 58, yT - 40], [cx + 58, yT - 40], [cx + 62, yT]]), C.teal, G, 1);
      s += K.pave(cx - 54, yT - 38, cx + 54, yT - 3, 12, C.stoneLt);
      s += X.pine(cx - 50, yT - 6, 0.8, 1) + X.cypress(cx + 52, yT - 8, 0.8);
      var tw = X.tower(cx, yT - 12, 22, [
        { w: 72, h: 22, bays: 3, doors: [1], dg: 4, ov: 7, up: 10, hr: 6, tile: TILE.teal, ridgeW: 12 },
        { w: 58, h: 18, bays: 3, doors: [], balcony: true, dg: 4, ov: 8, up: 12, hr: 16, tile: TILE.teal, roof: 'hip', plaque: 3 }
      ]);
      s += tw.svg + PT.gourd(cx, tw.roof.ridgeY - 3, 1);
      s += PT.censer(cx - 26, yT - 4, 0.55, 81) + PT.censer(cx + 26, yT - 4, 0.55, 83);
      s += X.marbleRail(cx - 58, cx + 58, yT, 5);
      // 仙鹤与高处祥云
      s += X.cloud(cx + 30, U - 150, 38, { flip: true, op: 0.92 });
      s += TT.crane(cx - 40, U - 120, 0.9, 1) + TT.crane(cx + 44, U - 96, 0.75, -1);
      return s;
    }
  });

  var API = { defs: defs };
  if (node) module.exports = API;
  else root.TownArtEastLandmarkFantasy = API;
})(typeof window !== 'undefined' ? window : this);
