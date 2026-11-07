/*
 * 织梦 · arab-base 预览：拼接验证场景定义（三档道路 L 形 + 十字、方形城墙 + 城门 + 塔楼、不规则辐条墙、绿洲水塘、街区）。
 * 叠加件（城门 / 塔楼）排序键 = 本格前沿 y + 24.5，排在同格墙瓦片（锚点在前沿下半格）之后。依赖 preview-scenes.js。
 */
(function (root) {
  'use strict';
  var K = root.ABScenesKit, OV = 24.5;
  var ROADMAP = ['#......', '#....#.', '#...###', '####.#.'];
  function roads(host) {
    ['dirt', 'stone', 'tile'].forEach(function (mat) {
      K.scene(host, '道路 ' + mat + '：L 形 + 十字路口', 7, 4, function (g, o) {
        K.dual(K.grid(ROADMAP), 'arab-common-road-' + mat + '-', g);
        K.cell('arab-common-prop-datepalm-01', 2, 1, o); K.cell('arab-common-house-mudhut-02', 3, 1, o);
      });
    });
  }
  function walls(host) {
    K.scene(host, '方形夯土城墙：gate-h（南、北）、gate-v（西）、四角圆塔', 7, 5, function (g, o) {
      K.dual(K.grid(['#######', '#.....#', '#.....#', '#.....#', '#######']), 'arab-common-wall-', o);
      K.cell('arab-common-wall-gate-h', 3, 4, o, OV); K.cell('arab-common-wall-gate-h', 3, 0, o, OV); K.cell('arab-common-wall-gate-v', 0, 2, o, OV);
      [[0, 0], [6, 0], [0, 4], [6, 4]].forEach(function (c) { K.cell('arab-common-wall-tower', c[0], c[1], o, OV); });
      K.dual(K.grid(['.......', '.......', '...#...', '.####..', '...#...']), 'arab-common-road-dirt-', g);
      K.bld('arab-common-house-courtyard-01', 4, 1, o); K.cell('arab-common-house-mudhut-01', 1, 1, o); K.cell('arab-common-house-dome-01', 2, 1, o);
      K.cell('arab-common-prop-camel-01', 2, 3, o);
    });
  }
  function spokes(host) {
    var V = [[2, 1], [6, 1], [8, 3], [8, 5], [6, 5], [5, 4], [3, 6], [1, 6], [1, 2], [2, 1]];
    K.scene(host, '不规则辐条墙：45° 斜段（NE / SE / NW / SW）+ (5,4) 处凹角；塔楼替代节点', 10, 8, function (g, o) {
      K.spokeRing(V, o, { '8,3': 1, '1,6': 1 });
      K.bld('arab-common-house-courtyard-02', 3, 2, o); K.cell('arab-common-house-tower-01', 6, 3, o); K.cell('arab-common-prop-datepalm-02', 2, 4, o);
    });
  }
  function oasis(host) {
    K.scene(host, '绿洲水塘：16 张水面瓦片 + 椰枣 / 陶罐 / 骆驼摆件', 7, 5, function (g, o) {
      K.dual(K.grid(['.......', '.###...', '.####..', '..###..', '...#...']), 'arab-common-water-oasis-', g);
      K.cell('arab-common-prop-datepalm-01', 0, 1, o); K.cell('arab-common-prop-datepalm-02', 4, 0, o); K.cell('arab-common-prop-datepalm-01', 5, 2, o);
      K.cell('arab-common-prop-camel-02', 5, 4, o); K.cell('arab-common-prop-jars-02', 1, 4, o); K.cell('arab-common-prop-camel-01', 0, 3, o);
      K.bld('arab-common-house-barasti-02', 5, 0, o); K.cell('arab-common-prop-jars-01', 6, 3, o);
    });
  }
  function block(host) {
    var R = [];
    for (var y = 0; y < 8; y++) { var r = ''; for (var x = 0; x < 12; x++) r += (y === 4 || x === 6) ? '#' : '.'; R.push(r); }
    var H = 'arab-common-house-';
    var B = [['windtower-03', 0, 0], ['mudhut-01', 2, 0], ['mudhut-03', 3, 0], ['tower-02', 4, 0], ['dovecote-01', 5, 1], ['terrace-02', 2, 1],
      ['arcade-02', 2, 2], ['dome-01', 4, 2], ['courtyard-03', 0, 2], ['mashrabiya-02', 2, 3], ['tower-01', 4, 3], ['arcade-01', 5, 3],
      ['dome-02', 7, 0], ['tower-03', 9, 0], ['terrace-01', 11, 0], ['courtyard-01', 7, 2], ['hillside-03', 9, 2], ['mashrabiya-03', 11, 2], ['arcade-03', 9, 3],
      ['windtower-02', 2, 5], ['mudhut-02', 4, 5], ['arcade-01', 5, 5], ['tent-02', 0, 6], ['barasti-02', 2, 6], ['barasti-03', 4, 6],
      ['courtyard-02', 7, 5], ['dovecote-02', 9, 5], ['terrace-03', 11, 5], ['dome-03', 9, 6], ['mashrabiya-01', 10, 6], ['windtower-01', 11, 6]];
    K.scene(host, '街区：石板路十字 + 民居按锚点 y 排序', 12, 8, function (g, o) {
      K.dual(K.grid(R), 'arab-common-road-stone-', g);
      B.forEach(function (b) { K.bld(H + b[0], b[1], b[2], o); });
      K.cell('arab-common-prop-datepalm-01', 0, 5, o); K.cell('arab-common-prop-camel-01', 1, 5, o); K.cell('arab-common-prop-jars-01', 8, 7, o);
    });
  }
  root.ABScenes = {
    render: function (list, host) {
      K.index(list);
      var h = function (t) { var e = document.createElement('h2'); e.textContent = t; host.appendChild(e); };
      h('拼接验证'); roads(host); walls(host); spokes(host); oasis(host); block(host);
    }
  };
})(window);
