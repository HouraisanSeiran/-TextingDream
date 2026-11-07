/*
 * 织梦 · east-site 预览：各资源点示意小地图的摆放（10×8 格）。项 [symbolId, gx, gy] 为占地左上角格。
 * 依赖 preview-scenes.js（window.ES_SCENES）。
 */
(function (root) {
  'use strict';
  var Z = root.ES_SCENES, R = Z.rect, road = Z.road, sc = Z.scene;

  sc({ title: '伐木场 timber', ground: [['east-common-ground-stumps-0', 2, R(0, 0, 3, 3).concat(R(6, 0, 9, 1))]],
    road: road([[4, 4], [4, 6], [9, 6]]),
    items: [['east-common-prop-pine-01', 0, 0], ['east-common-prop-pine-02', 7, 0], ['east-common-prop-pine-01', 9, 1],
      ['east-common-prop-lumber-slide-01', 1, 1], ['east-common-prop-lumber-slide-01', 2, 2],
      ['east-common-site-lumber-01', 3, 2], ['east-common-prop-lumber-logrow-01', 7, 3], ['east-common-prop-lumber-logrow-01', 7, 4],
      ['east-common-prop-pine-02', 0, 6], ['east-common-prop-bamboo-01', 1, 7]] });

  var P = 'east-common-prop-', T = 'east-common-site-', GD = 'east-common-ground-';
  sc({ title: '采石场 stone', ground: [[GD + 'rubble-0', 2, R(0, 3, 6, 5)]],
    road: road([[3, 6], [3, 7], [9, 7]]),
    items: [[T + 'quarry-01', 1, 0], ['east-common-prop-pine-01', 0, 0], ['east-common-prop-pine-02', 8, 0],
      [P + 'stone-blocks-01', 6, 2], [P + 'stone-blocks-01', 6, 3], [P + 'stone-rubble-01', 0, 4], [P + 'stone-trolley-01', 5, 5],
      [P + 'stone-rubble-01', 7, 5], ['east-common-prop-taihurock-01', 8, 4]] });

  sc({ title: '黏土坑 clay', road: road([[5, 4], [5, 7]]),
    items: [[T + 'claypit-01', 1, 1], [T + 'brickyard-01', 6, 1], [P + 'clay-mud-01', 0, 4], [P + 'clay-baskets-01', 3, 4],
      [P + 'clay-adobe-01', 6, 4], [P + 'clay-adobe-01', 7, 4], [P + 'clay-mud-01', 8, 5], ['east-common-prop-willow-01', 0, 6]] });

  // 六种矿共用布局：洞口 + 竖井 + 矿渣地 + 矿石筐 + 特征件
  var SPK = { iron: 'oreroast', copper: 'orewash', tin: 'tinpan', gold: 'goldsluice', silver: 'silverfurnace', coal: 'coalheap' };
  var CN = { iron: '铁矿', copper: '铜矿', tin: '锡矿', gold: '金矿', silver: '银矿', coal: '煤矿' };
  Object.keys(SPK).forEach(function (m) {
    var M = P + 'mine-' + m + '-';
    sc({ title: CN[m] + ' ' + m, ground: [[GD + 'slag-' + m + '-0', 1, R(1, 3, 7, 4)]],
      road: road([[2, 5], [2, 7]]),
      items: [['east-common-prop-pine-01', 0, 0], [T + 'mine-' + m + '-01', 1, 1], [T + 'mine-' + m + '-02', 6, 1], ['east-common-prop-pine-02', 9, 0],
        [M + 'basket-01', 4, 3], [M + SPK[m] + '-01', 5, 4], [M + SPK[m] + '-01', 7, 4], [M + 'basket-01', 3, 4], [M + 'basket-01', 8, 3],
        ['east-common-prop-taihurock-02', 9, 6]] });
  });

  sc({ title: '海盐晒场 salt', ground: [[GD + 'saltpan-0', 3, R(0, 4, 9, 7)]], road: road([[4, 3], [9, 3]]),
    items: [[T + 'saltfield-01', 1, 1], [P + 'salt-rake-01', 5, 2], [P + 'salt-sacks-01', 6, 1], [P + 'salt-sacks-01', 7, 1], [P + 'salt-rake-01', 8, 2]] });
  sc({ title: '井盐 salt', road: road([[3, 6], [3, 7], [9, 7]]),
    items: [[T + 'brinewell-01', 1, 1], [T + 'boilhouse-01', 4, 1], [P + 'salt-brinetub-01', 1, 4], [P + 'salt-brinetub-01', 2, 5],
      [P + 'salt-sacks-01', 7, 4], [P + 'salt-sacks-01', 8, 4], [P + 'lumber-logrow-01', 5, 4], ['east-common-prop-bamboo-02', 9, 1]] });

  var SH = [GD + 'shallows-0', 2, R(0, 5, 9, 7)];
  sc({ title: '渔场 fish', ground: [SH], road: road([[0, 3], [9, 3]]),
    items: [[T + 'fishpier-01', 3, 4], [P + 'fish-netrack-01', 1, 2], [P + 'fish-netrack-01', 2, 2], [P + 'fish-creel-01', 7, 4],
      [P + 'fish-cormorant-01', 8, 6], [P + 'fish-cormorant-01', 1, 6], ['east-common-prop-willow-02', 0, 1], [P + 'reed-clump-01', 0, 5]] });
  sc({ title: '芦苇荡 reed', ground: [[GD + 'shallows-0', 2, R(0, 0, 9, 3)]], road: road([[0, 6], [9, 6]]),
    items: [[P + 'reed-clump-01', 0, 1], [P + 'reed-clump-01', 1, 3], [T + 'reedbed-01', 3, 1], [P + 'reed-clump-01', 7, 2], [P + 'reed-clump-01', 8, 0],
      [P + 'reed-bundles-01', 3, 4], [P + 'reed-bundles-01', 4, 4], [P + 'reed-bundles-01', 7, 5], ['east-common-prop-willow-01', 9, 4]] });
  sc({ title: '珍珠 pearls', ground: [[GD + 'shallows-0', 2, R(0, 3, 9, 7)]], road: road([[0, 1], [9, 1]]),
    items: [[T + 'pearlboat-01', 3, 4], [P + 'pearl-shells-01', 2, 2], [P + 'pearl-shells-01', 6, 2], [P + 'pearl-drying-01', 4, 2],
      [P + 'fish-netrack-01', 8, 2], [P + 'fish-cormorant-01', 8, 6]] });

  sc({ title: '茶园 herb·tea', ground: [[GD + 'teaterrace-0', 2, R(0, 0, 9, 3)]], road: road([[3, 4], [3, 7]]),
    items: [[P + 'tea-bush-01', 0, 3], [P + 'tea-bush-01', 8, 3], [T + 'teashed-01', 4, 4], [P + 'tea-pickbasket-01', 2, 5], [P + 'tea-pickbasket-01', 8, 6],
      ['east-common-prop-bamboo-01', 0, 6]] });
  sc({ title: '药圃 herb', ground: [[GD + 'herbbed-0', 2, R(5, 4, 9, 7)]], road: road([[0, 3], [9, 3]]),
    items: [[T + 'herbgarden-01', 1, 1], [P + 'herb-trays-01', 5, 1], [P + 'herb-trays-01', 6, 1], [P + 'herb-mortar-01', 7, 2],
      [P + 'herb-trays-01', 1, 5], [P + 'herb-mortar-01', 2, 6], ['east-common-prop-plum-01', 8, 0]] });
  sc({ title: '花椒园 spices', road: road([[4, 4], [4, 7]]),
    items: [[T + 'pepperyard-01', 2, 1], [P + 'spice-sacks-01', 6, 2], [P + 'spice-sacks-01', 7, 2], [P + 'spice-sacks-01', 6, 4],
      ['east-common-prop-pine-01', 0, 0], ['east-common-prop-pine-02', 9, 5]] });
  sc({ title: '桑园蚕房 silk', road: road([[0, 4], [9, 4]]),
    items: [[P + 'silk-mulberry-01', 0, 1], [P + 'silk-mulberry-01', 1, 1], [P + 'silk-mulberry-01', 7, 1], [P + 'silk-mulberry-01', 8, 1],
      [T + 'silkhouse-01', 3, 1], [P + 'silk-reel-01', 2, 5], [P + 'silk-cocoons-01', 3, 5],
      [P + 'silk-mulberry-01', 0, 6], [P + 'silk-mulberry-01', 1, 6], [P + 'silk-mulberry-01', 5, 6], [P + 'silk-mulberry-01', 6, 6], [P + 'silk-mulberry-01', 7, 6]] });
  sc({ title: '稻田 grain', ground: [[GD + 'paddy-01', 0, R(0, 4, 4, 5)], [GD + 'paddy-02', 0, R(5, 4, 9, 7)], [GD + 'paddy-03', 0, R(0, 6, 4, 7)], [GD + 'shallows-0', 2, R(0, 2, 1, 3)]], road: road([[2, 3], [9, 3]]),
    items: [[T + 'waterwheel-01', 0, 2], [T + 'granary-01', 4, 0], [P + 'grain-sheaves-01', 2, 1], [P + 'grain-sheaves-01', 8, 1], [P + 'grain-dryingmat-01', 7, 2]] });
  sc({ title: '牧场 livestock·wool', ground: [[GD + 'pasture-0', 2, R(0, 0, 9, 5)]], road: road([[4, 6], [4, 7]]),
    items: [[T + 'pasture-01', 3, 2], [P + 'pasture-sheep-01', 0, 1], [P + 'pasture-sheep-01', 1, 3], [P + 'pasture-trough-01', 7, 2],
      [P + 'pasture-woolbales-01', 6, 5], [P + 'pasture-woolbales-01', 7, 5], [P + 'pasture-sheep-01', 8, 4]] });
  sc({ title: '马场 horses', ground: [[GD + 'pasture-0', 2, R(0, 4, 9, 7)]], road: road([[0, 3], [9, 3]]),
    items: [[T + 'horsefarm-01', 3, 1], [P + 'horse-post-01', 1, 2], [P + 'horse-post-01', 8, 2], [P + 'pasture-trough-01', 4, 5], [P + 'horse-post-01', 6, 6]] });
  sc({ title: '染坊原料 dye', road: road([[0, 4], [9, 4]]),
    items: [[P + 'dye-indigoplants-01', 0, 0], [P + 'dye-indigoplants-01', 1, 0], [P + 'dye-indigoplants-01', 8, 0], [T + 'indigopit-01', 3, 1],
      [P + 'dye-clothrack-01', 2, 5], [P + 'dye-clothrack-01', 3, 5], [P + 'dye-clothrack-01', 4, 5], [P + 'dye-vats-01', 6, 5], [P + 'dye-vats-01', 7, 6]] });
  sc({ title: '玉石矿 gems', road: road([[0, 4], [9, 4]]),
    items: [[T + 'jadepit-01', 1, 1], [T + 'jadeshop-01', 5, 5], [P + 'gems-rawjade-01', 5, 2], [P + 'gems-rawjade-01', 6, 2],
      [P + 'gems-sandtub-01', 3, 6], [P + 'gems-cutjade-01', 8, 6], ['east-common-prop-pine-01', 8, 0]] });
  sc({ title: '灵石矿 mana', ground: [[GD + 'manarock-0', 2, R(2, 1, 7, 4)]], road: road([[4, 5], [4, 7]]),
    items: [[T + 'manavein-01', 3, 2], [P + 'mana-pillar-01', 1, 3], [P + 'mana-pillar-01', 7, 3], [P + 'mana-crystals-01', 2, 1],
      [P + 'mana-crystals-01', 6, 1], [P + 'mana-chest-01', 5, 5], ['east-common-prop-pine-02', 0, 0], ['east-common-prop-pine-01', 9, 6]] });
  sc({ title: '龙骨坑 dragonbone', ground: [[GD + 'rubble-0', 2, R(2, 1, 7, 4)]], road: road([[4, 5], [4, 7]]),
    items: [[T + 'dragonpit-01', 3, 1], [P + 'dragon-altar-01', 1, 4], [P + 'dragon-bones-01', 7, 4], [P + 'dragon-tools-01', 2, 2],
      [P + 'dragon-bones-01', 8, 2], ['east-common-prop-pine-01', 0, 0], ['east-common-prop-stonelantern-01', 6, 5]] });
})(this);
