/*
 * 织梦 · 阿拉伯风格 1×1 地面摆件：椰枣树、陶罐组、骆驼（美术样板，尚未接入游戏）
 * 锚点 = 脚底中点（本格前沿中点），上伸 ≤ 48 px（规范第 9 节）。
 * 浏览器挂 window.TownArtAB_props；Node 用 module.exports。依赖 core.js、parts2.js、kit.js。
 */
(function (root) {
  'use strict';
  var isNode = typeof module !== 'undefined' && module.exports;
  function dep(file, name) { return isNode ? require(file) : root[name]; }
  var C = dep('./core.js', 'TownArtAB_core'), Q2 = dep('./parts2.js', 'TownArtAB_parts2'), K = dep('./kit.js', 'TownArtAB_kit');
  var P = C.PAL, f = C.f, CAMEL = '#c79a62', CAMEL2 = '#a97a48';

  function palms(ctx, v) {
    if (v === 1) return Q2.palm(ctx, 22, -14, 64, 5, { dates: true, sc: 1.2 });
    return Q2.palm(ctx, 30, -18, 58, 4, { dates: true, sc: 1.1 }) + Q2.palm(ctx, 16, -10, 44, -5, { fronds: 7 }) + C.ell(36, -8, 5, 2.4, P.palm, 0.8) + C.ell(32, -9, 3, 1.8, P.palm2, 0.6);
  }
  function jars(ctx, v) {
    var s = C.ell(24, -14, 16, 6, '#d8bf8c', 0, 0.6);
    if (v === 1) return s + K.jar(ctx, 18, -16, 14, P.ochre2) + K.jar(ctx, 30, -13, 11, P.mud2) + K.jar(ctx, 23, -9, 8, P.ochre);
    // 釉面储水罐：钴蓝 / 绿松石罐 + 木架上倒扣的小罐
    s += C.line('M8 -10v-10M18 -10v-10M7 -20h12', 1.2, 1, P.wood) + K.jar(ctx, 13, -20, 7, P.turq);
    return s + K.jar(ctx, 29, -14, 15, P.cob2) + K.jar(ctx, 37, -9, 9, P.turq) + C.line('M25 -24h8', 0.8, 0.9, P.turq2);
  }
  /** 骆驼：侧身朝左，单峰；v1 站立带鞍毯；v2 卧姿 */
  function camel(ctx, v) {
    var s = C.ell(26, -9, 16, 3, P.ink, 0, 0.18);
    if (v === 1) {
      var legs = 'M16 -22L15 -9M20 -22L21 -9M32 -22L31 -9M36 -21L38 -9';
      s += C.line(legs, 2.2, 1, CAMEL2) + C.line(legs, 2.2 - 1.2, 1, CAMEL);
      s += C.line('M14.5 -9h2M20.5 -9h2M30.5 -9h2M37 -9h2', 1.4, 1, P.ink);
      // 躯干 + 驼峰 + 长颈 + 头
      s += C.path('M14 -24Q13 -30 18 -31Q22 -40 28 -39Q33 -37 35 -31Q39 -30 39 -25Q38 -20 33 -20H18Q14 -20 14 -24Z', CAMEL, 1.4);
      s += C.path('M15 -27Q10 -30 9 -38Q8 -42 5 -42Q2 -42 2 -40Q3 -38 6 -38Q7 -33 12 -24Z', CAMEL, 1.3);
      s += C.ell(4.2, -40.6, 0.6, 0.6, P.ink, 0) + C.line('M39 -26q3 2 2 7', 0.9, 1);
      // 鞍毯：赭红 + 金穗
      s += C.path('M21 -36Q28 -39 33 -35L34 -26H21Z', P.ochre, 1) + C.line('M21.5 -28H33.5', 0.9, 1, P.gold) + C.line('M22 -26v2M25 -26v2M28 -26v2M31 -26v2', 0.7, 1, P.gold);
      ctx.top(-44);
    } else {
      s += C.path('M10 -12Q10 -18 16 -19Q21 -28 28 -27Q34 -26 36 -19Q42 -18 42 -13Q42 -10 38 -10H13Q10 -10 10 -12Z', CAMEL, 1.4);
      s += C.line('M16 -11h6M30 -11h7', 1, 0.6, CAMEL2);
      s += C.path('M13 -16Q8 -20 8 -27Q7 -31 4 -31Q1 -31 1 -29Q2 -27 5 -27Q5 -22 10 -14Z', CAMEL, 1.3) + C.ell(3.2, -29.6, 0.6, 0.6, P.ink, 0);
      s += C.path('M20 -22Q28 -25 33 -21L33 -16H20Z', P.cob2, 0.9) + C.line('M20.5 -18H32.5', 0.8, 1, P.gold);
      s += K.jar(ctx, 44, -10, 7, P.mud2);
      ctx.top(-33);
    }
    return s;
  }
  var DEF = [
    ['datepalm', '椰枣树', palms, ['plant', 'palm', 'oasis'], ['单株挂果', '双株 + 灌丛']],
    ['jars', '陶罐', jars, ['pottery', 'water_jar'], ['素陶罐组', '釉面储水罐 + 木架']],
    ['camel', '骆驼', camel, ['animal', 'camel', 'caravan'], ['站立带鞍毯', '卧姿 + 货罐']]
  ];
  function all(wrap) {
    var out = [];
    DEF.forEach(function (d) {
      [1, 2].forEach(function (v) {
        var id = 'arab-common-prop-' + d[0] + '-' + C.pad2(v), ctx = new C.Ctx(id), body = d[2](ctx, v);
        out.push(wrap(id, [1, 1], body, Math.min(ctx.minY, -48), {
          id: id, style: 'arab', race: 'common', category: 'prop', kind: 'prop_' + d[0], facility: null, variant: v, maxUp: 48,
          name: d[1] + ' ' + v, tags: d[3].slice(), roof: 'none', note: d[4][v - 1] + '；锚点在脚底中点，上伸 ≤ 48 px'
        }));
      });
    });
    return out;
  }
  var API = { all: all, camel: camel };
  root.TownArtAB_props = API;
  if (isNode) module.exports = API;
})(typeof window !== 'undefined' ? window : this);
