/* 预览小地图配置（10×8 格）：items = [symbolId, 左上格 x, 占地顶行 y]；ground = 专用地面区域；road = 格坐标折线 */
(function (root) {
  'use strict';
  var I = function (k, v) { return 'west-common-' + k + '-' + (v < 10 ? '0' + v : v); };
  var SC = [];
  SC.push({
    name: '伐木场', resource: 'timber',
    ground: [{ kind: 'stumpfield', x: 0, y: 0, w: 4, h: 4 }, { kind: 'stumpfield', x: 6, y: 0, w: 4, h: 2 }],
    road: [[10, 6.5], [6.5, 6.5], [5.5, 5.5], [5.5, 4.2]],
    items: [
      [I('site-sawshed', 1), 4, 1], [I('site-watersaw', 1), 0, 4],
      [I('prop-logpile', 1), 7, 2], [I('prop-logpile', 1), 8, 2], [I('prop-logcart', 1), 7, 4],
      [I('prop-chopblock', 1), 3, 2], [I('prop-logpile', 1), 8, 7]
    ]
  });
  SC.push({
    name: '采石场', resource: 'stone',
    ground: [{ kind: 'bedrock', x: 1, y: 0, w: 7, h: 6 }],
    road: [[10, 6.5], [6, 6.5], [4.5, 5.6]],
    items: [
      [I('site-quarry', 1), 2, 1], [I('prop-stonestack', 1), 6, 4], [I('prop-stonestack', 1), 7, 3],
      [I('prop-rubble', 1), 1, 4], [I('prop-rubble', 1), 2, 5], [I('prop-stonestack', 1), 8, 7]
    ]
  });
  SC.push({
    name: '大理石场', resource: 'marble',
    ground: [{ kind: 'marblechips', x: 1, y: 0, w: 7, h: 6 }],
    road: [[0, 6.5], [4, 6.5], [5, 5.6]],
    items: [
      [I('site-marblequarry', 1), 2, 1], [I('prop-marbleblock', 1), 6, 4], [I('prop-marbleblock', 1), 7, 4],
      [I('prop-rubble', 1), 1, 4], [I('prop-marbleblock', 1), 8, 6]
    ]
  });
  // 六种矿：主体 + 本矿种矿石堆/矿车 + 专属配套
  var MINES = [['iron', '铁矿', 'roastclamp', 'slag'], ['copper', '铜矿', 'leachpit', 'slag'], ['tin', '锡矿', 'buddle', 'slag'],
    ['gold', '金矿', 'sluice', 'slag'], ['silver', '银矿', 'cupel', 'slag'], ['coal', '煤矿', 'coalbaskets', 'coaldust']];
  MINES.forEach(function (m) {
    SC.push({
      name: m[1], resource: m[0],
      ground: [{ kind: m[3], x: 2, y: 1, w: 6, h: 5 }],
      road: [[0, 6.5], [3.5, 6.5], [3.5, 4.3]],
      items: [
        [I('site-mine-' + m[0], 1), 2, 1], [I('prop-ore-' + m[0], 1), 6, 4], [I('prop-ore-' + m[0], 1), 7, 4],
        [I('prop-minecart-' + m[0], 1), 5, 4], [I('prop-' + m[2], 1), 1, 3], [I('prop-' + m[2], 1), 8, 2],
        [I('prop-ore-' + m[0], 1), 7, 6]
      ]
    });
  });
  SC.push({
    name: '黏土坑', resource: 'clay', road: [[10, 6.5], [6, 6.5], [5, 5.6]],
    items: [[I('site-claypit', 1), 1, 1], [I('site-brickyard', 1), 5, 3], [I('prop-brickstack', 1), 8, 2],
      [I('prop-brickstack', 1), 1, 4], [I('prop-brickstack', 1), 2, 4]]
  });
  SC.push({
    name: '盐场', resource: 'salt', ground: [{ kind: 'saltpan', x: 0, y: 0, w: 5, h: 4 }], road: [[10, 6.5], [7, 6.5], [6.5, 5.6]],
    items: [[I('site-saltboil', 1), 6, 2], [I('prop-saltheap', 1), 1, 5], [I('prop-saltheap', 1), 2, 5], [I('prop-saltheap', 1), 3, 4]]
  });
  SC.push({
    name: '硫磺坑', resource: 'sulfur', ground: [{ kind: 'sulfurcrust', x: 1, y: 0, w: 7, h: 5 }], road: [[0, 6.5], [4, 6.5], [4.5, 4.4]],
    items: [[I('site-sulfurpit', 1), 3, 2], [I('prop-sulfurlumps', 1), 7, 3], [I('prop-sulfurlumps', 1), 2, 3], [I('prop-sulfurlumps', 1), 8, 6]]
  });
  SC.push({
    name: '宝石矿', resource: 'gems', road: [[10, 6.5], [5.5, 6.5], [4.5, 5.6]],
    items: [[I('site-gempit', 1), 3, 2], [I('prop-gemsieve', 1), 6, 3], [I('prop-gemsieve', 1), 2, 4], [I('prop-rubble', 1), 7, 2]]
  });
  SC.push({
    name: '琥珀', resource: 'amber', road: [[0, 6.5], [4, 6.5], [4.5, 5.6]],
    items: [[I('site-amberpit', 1), 3, 2], [I('prop-ambersieve', 1), 6, 3], [I('prop-ambersieve', 1), 7, 4], [I('prop-logpile', 1), 1, 3]]
  });
  SC.push({
    name: '渔场', resource: 'fish', water: [[0, 6, 10, 2]], road: [[10, 3.5], [7, 3.5], [6.5, 4.5]],
    items: [[I('site-fishjetty', 1), 3, 5 - 1], [I('prop-netrack', 1), 1, 4], [I('prop-netrack', 1), 2, 4],
      [I('prop-fishbasket', 1), 8, 4], [I('prop-fishbasket', 1), 1, 2], [I('prop-netrack', 1), 8, 2]]
  });
  SC.push({
    name: '芦苇荡', resource: 'reed', water: [[0, 0, 10, 3]], road: [[10, 6.5], [6, 6.5], [5, 5.2]],
    items: [[I('site-reedcut', 1), 3, 2], [I('prop-reedclump', 1), 0, 2], [I('prop-reedclump', 1), 1, 2], [I('prop-reedclump', 1), 8, 2],
      [I('prop-reedclump', 1), 9, 2], [I('prop-reedstook', 1), 1, 4], [I('prop-reedstook', 1), 2, 5], [I('prop-reedstook', 1), 8, 5]]
  });
  SC.push({
    name: '牧场', resource: 'livestock', road: [[10, 6.5], [6, 6.5], [4, 5.5]],
    items: [[I('site-sheepfold', 1), 2, 2], [I('prop-hayrack', 1), 7, 2], [I('prop-hayrack', 1), 8, 3], [I('prop-sheep', 1), 7, 5],
      [I('prop-sheep', 1), 1, 6], [I('prop-sheep', 1), 0, 2]]
  });
  SC.push({
    name: '剪毛场', resource: 'wool', road: [[0, 6.5], [4, 6.5], [4.5, 5.2]],
    items: [[I('site-shearshed', 1), 3, 2], [I('prop-woolbales', 1), 7, 3], [I('prop-woolbales', 1), 8, 4], [I('prop-sheep', 1), 1, 2],
      [I('prop-sheep', 1), 2, 4], [I('prop-hayrack', 1), 8, 1]]
  });
  SC.push({
    name: '马场', resource: 'horses', road: [[10, 6.5], [6, 6.5], [4.5, 5.2]],
    items: [[I('site-horsecorral', 1), 1, 2], [I('prop-hitchtrough', 1), 6, 4], [I('prop-hitchtrough', 1), 7, 4], [I('prop-hayrack', 1), 8, 2]]
  });
  SC.push({
    name: '农庄', resource: 'grain', ground: [{ kind: 'wheatfield', x: 0, y: 0, w: 4, h: 5 }, { kind: 'wheatfield', x: 7, y: 0, w: 3, h: 3 }],
    road: [[10, 6.5], [6.5, 6.5], [5.5, 5.4]],
    items: [[I('site-barn', 1), 4, 2], [I('prop-threshfloor', 1), 7, 4], [I('prop-sheafstook', 1), 1, 1], [I('prop-sheafstook', 1), 2, 3],
      [I('prop-sheafstook', 1), 8, 1], [I('prop-sheafstook', 1), 3, 5]]
  });
  SC.push({
    name: '药圃', resource: 'herb', road: [[0, 6.5], [3.5, 6.5], [4.5, 5.2]],
    items: [[I('site-herbgarden', 1), 3, 2], [I('prop-herbrack', 1), 7, 2], [I('prop-herbrack', 1), 8, 3], [I('prop-herbbasket', 1), 6, 4],
      [I('prop-herbbasket', 1), 2, 4]]
  });
  SC.push({
    name: '葡萄园', resource: 'wine', ground: [{ kind: 'vinerows', x: 0, y: 0, w: 10, h: 2 }, { kind: 'vinerows', x: 0, y: 2, w: 3, h: 3 }],
    road: [[10, 6.5], [6.5, 6.5], [5.5, 5.4]],
    items: [[I('site-winepress', 1), 4, 3], [I('prop-winebarrels', 1), 7, 4], [I('prop-winebarrels', 1), 8, 4], [I('prop-grapebasket', 1), 3, 5],
      [I('prop-grapebasket', 1), 1, 5]]
  });
  SC.push({
    name: '魔力晶矿', resource: 'mana', ground: [{ kind: 'crystalgrit', x: 1, y: 0, w: 7, h: 6 }], road: [[0, 6.5], [3, 6.5], [3.5, 5.6]],
    items: [[I('site-manamine', 1), 2, 1], [I('prop-manacluster', 1), 7, 2], [I('prop-runestone', 1), 1, 2], [I('prop-runestone', 1), 8, 4],
      [I('prop-manacrates', 1), 6, 4], [I('prop-manacluster', 1), 1, 5]]
  });
  SC.push({
    name: '龙骨坑', resource: 'dragonbone', ground: [{ kind: 'digsoil', x: 1, y: 0, w: 8, h: 5 }], road: [[10, 6.5], [6, 6.5], [5, 5.2]],
    items: [[I('site-dragondig', 1), 2, 1], [I('prop-bonepile', 1), 1, 4], [I('prop-scaffold', 1), 8, 2], [I('prop-tooltent', 1), 8, 4],
      [I('prop-bonepile', 1), 2, 5]]
  });
  root.TownArtWS_scenes = SC;
  root.TownArtWS_sceneId = I;
})(window);
