/*
 * 织梦 · east-ground · 摆件汇总：把 props-plants / props-stone / props-farm / props-yard 的 def 包装成 symbol 与 meta
 *
 * id = east-common-prop-<kind 去下划线>-<两位变体号>。占地 1×1，锚点 = 脚底中点（格子前沿中点）。
 * 上伸 = 画到的最高点超出占地格顶（y = -48）的像素，按 scanTop 估算再加 3 px 余量，规范上限 48。
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = factory(require('./core.js'), [require('./props-plants.js'), require('./props-stone.js'), require('./props-farm.js'), require('./props-yard.js')]);
  } else {
    root.TownArtEG_props = factory(root.TownArtEG_core, [root.TownArtEG_propsPlants, root.TownArtEG_propsStone, root.TownArtEG_propsFarm, root.TownArtEG_propsYard]);
  }
})(this, function (K, groups) {
  'use strict';
  var MAXUP = 48;

  function build(def, v, vi, seed) {
    var id = 'east-common-prop-' + def.kind.replace(/_/g, '') + '-' + K.pad2(vi + 1), ctx = new K.Ctx(id, seed);
    var body = def.draw.call({ ctx: ctx }, ctx.r, v);
    var top = K.scanTop(body), up = Math.max(0, Math.ceil(-top - 48 + 3)), over = up > MAXUP;
    up = Math.min(up, MAXUP);
    var sym = K.propSym(id, up, body);
    return { id: id, svg: sym.svg, over: over, name: def.name, meta: {
      id: id, style: 'east', race: 'common', category: 'prop', kind: 'prop_' + def.kind, facility: null, variant: vi + 1,
      footprint: [1, 1], height_px: up, anchor: sym.anchor, viewBox: sym.viewBox,
      tags: (def.tags || []).concat(v.tags || []), roof: 'none',
      note: def.name + (v.note ? '：' + v.note : '') + '；锚点在脚底中点（格子前沿中点），按锚点 y 排序绘制',
      name_zh: def.name
    } };
  }

  function all() {
    var out = [], seed = 8200;
    groups.forEach(function (g, gi) {
      if (!g) return;
      g.defs.forEach(function (def, di) {
        def.variants.forEach(function (v, vi) { out.push(build(def, v, vi, seed + gi * 1000 + di * 37 + vi * 7)); });
      });
    });
    return out;
  }
  return { all: all };
});
