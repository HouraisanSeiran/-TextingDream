/* 预览小地图配置（10×8 格）：items = [symbolId, 左上格 x, 占地顶行 y]；ground = 专用地面区域；water = [x,y,w,h]；road = 格坐标折线 */
(function (root) {
  'use strict';
  var I = function (k, v) { return 'west-common-' + k + '-' + (v < 10 ? '0' + v : v || '01'); };
  var SC = [];
  SC.push({
    name: '青金石露天矿', resource: 'lapis', subtype: 'open_pit',
    ground: [{ kind: 'lapisrubble', x: 2, y: 1, w: 6, h: 5 }],
    road: [[0, 6.5], [3, 6.5], [4.5, 5.6]],
    items: [[I('site-lapispit', 1), 3, 2], [I('prop-lapis-basket', 1), 7, 5], [I('prop-lapis-spoil', 1), 2, 1],
      [I('prop-lapis-spoil', 1), 7, 1], [I('prop-lapis-cart', 1), 2, 4]]
  });
  SC.push({
    name: '稀有金属矿', resource: 'rare_metals', subtype: 'adit',
    ground: [{ kind: 'lapisrubble', x: 2, y: 3, w: 5, h: 3 }],
    road: [[0, 6.5], [3, 6.5], [3.8, 5.6]],
    items: [[I('site-raremetal-adit', 1), 2, 2], [I('prop-raremetal-sluice', 1), 7, 4], [I('prop-raremetal-panstack', 1), 6, 5],
      [I('prop-raremetal-orebag', 1), 1, 4], [I('prop-raremetal-orebag', 1), 6, 1]]
  });
  SC.push({
    name: '露天煤坑', resource: 'coal', subtype: 'open_pit',
    ground: [{ kind: 'coalpitfloor', x: 2, y: 1, w: 6, h: 5 }],
    road: [[0, 6.5], [3, 6.5], [4.5, 5.6]],
    items: [[I('site-coal-openpit', 1), 3, 2], [I('prop-coal-heap', 1), 2, 2], [I('prop-coal-heap', 1), 7, 1],
      [I('prop-coal-basket', 1), 2, 4], [I('prop-coal-basket', 1), 7, 5]]
  });
  SC.push({
    name: '烧炭窑场', resource: 'coal', subtype: 'charcoal_kiln',
    ground: [{ kind: 'coalpitfloor', x: 3, y: 2, w: 4, h: 3 }],
    road: [[0, 6.5], [3, 6.5], [4.5, 5.6]],
    items: [[I('site-charcoal-kiln', 1), 3, 2], [I('prop-charcoal-meiler', 1), 7, 2], [I('prop-charcoal-woodpile', 1), 2, 2],
      [I('prop-charcoal-woodpile', 1), 2, 3], [I('prop-charcoal-sacks', 1), 7, 4]]
  });
  SC.push({
    name: '番红花香料园', resource: 'spices', subtype: 'saffron_garden',
    road: [[0, 6.5], [3, 6.5], [5.5, 5.6]],
    items: [[I('site-saffron-garden', 1), 3, 2], [I('prop-spice-flowerbasket', 1), 2, 4], [I('prop-spice-sieve', 1), 7, 3],
      [I('prop-spice-jars', 1), 7, 4], [I('prop-spice-flowerbasket', 1), 7, 5]]
  });
  SC.push({
    name: '养蚕缫丝坊', resource: 'silk', subtype: 'sericulture',
    road: [[0, 6.5], [3, 6.5], [6, 5.6]],
    items: [[I('site-silk-filature', 1), 3, 2], [I('prop-silk-mulberry', 1), 1, 1], [I('prop-silk-mulberry', 1), 2, 1],
      [I('prop-silk-mulberry', 1), 1, 2], [I('prop-silk-mulberry', 1), 8, 1], [I('prop-silk-cocoontray', 1), 7, 4],
      [I('prop-silk-reel', 1), 7, 5], [I('prop-silk-cocoontray', 1), 2, 4]]
  });
  SC.push({
    name: '采珠场', resource: 'pearls', subtype: 'oyster_bed',
    water: [[0, 0, 10, 4]],
    ground: [{ kind: 'pearlsand', x: 0, y: 4, w: 10, h: 2 }],
    road: [[0, 6.5], [3, 6.5], [4.5, 5.4]],
    items: [[I('site-pearl-oysterbed', 1), 3, 2], [I('prop-pearl-skiff', 1), 1, 1], [I('prop-pearl-skiff', 1), 8, 0],
      [I('prop-pearl-shucktable', 1), 2, 4], [I('prop-pearl-shellheap', 1), 7, 5], [I('prop-pearl-net', 1), 8, 4]]
  });
  SC.push({
    name: '象牙作坊与牙料仓', resource: 'ivory', subtype: 'carving_workshop',
    road: [[0, 6.5], [3, 6.5], [5, 5.6]],
    items: [[I('site-ivory-workshop', 1), 3, 2], [I('prop-ivory-stack', 1), 2, 3], [I('prop-ivory-scale', 1), 2, 4],
      [I('prop-ivory-crate', 1), 7, 4], [I('prop-ivory-crate', 1), 7, 3]]
  });
  SC.push({
    name: '染料场', resource: 'dye', subtype: 'woad_madder',
    ground: [{ kind: 'dyeyard', x: 2, y: 1, w: 7, h: 5 }],
    road: [[0, 6.5], [3, 6.5], [5, 5.6]],
    items: [[I('site-dye-works', 1), 3, 2], [I('prop-dye-vat', 1), 7, 4], [I('prop-dye-madderrack', 1), 7, 2],
      [I('prop-dye-clothpole', 1), 2, 3], [I('prop-dye-clothpole', 1), 2, 4]]
  });
  SC.push({
    name: '麦田农庄', resource: 'grain', subtype: 'wheat_farm',
    road: [[0, 6.5], [3, 6.5], [5, 5.6]],
    items: [[I('site-wheat-farmstead', 1), 3, 2], [I('prop-grain-sheaves', 1), 1, 1], [I('prop-grain-sheaves', 1), 2, 1],
      [I('prop-grain-rick', 1), 7, 2], [I('prop-grain-rick', 1), 8, 3], [I('prop-grain-cart', 1), 7, 5]]
  });
  SC.push({
    name: '菜园', resource: 'grain', subtype: 'vegetable_farm',
    road: [[0, 6.5], [3, 6.5], [5.5, 5.6]],
    items: [[I('site-vegetable-garden', 1), 3, 2], [I('prop-veg-cabbagebed', 1), 2, 2], [I('prop-veg-cabbagebed', 1), 2, 3],
      [I('prop-veg-beanpoles', 1), 7, 2], [I('prop-veg-scarecrow', 1), 7, 4]]
  });
  SC.push({
    name: '苹果园', resource: 'grain', subtype: 'orchard',
    road: [[0, 6.5], [3, 6.5], [6, 5.6]],
    items: [[I('site-apple-orchard', 1), 3, 2], [I('prop-orchard-appletree', 1), 1, 1], [I('prop-orchard-appletree', 1), 2, 3],
      [I('prop-orchard-appletree', 1), 8, 1], [I('prop-orchard-crates', 1), 7, 4], [I('prop-orchard-ladder', 1), 2, 4]]
  });
  SC.push({
    name: '橄榄园', resource: 'grain', subtype: 'olive_grove',
    road: [[0, 6.5], [3, 6.5], [6, 5.6]],
    items: [[I('site-olive-grove', 1), 3, 2], [I('prop-olive-tree', 1), 1, 1], [I('prop-olive-tree', 1), 2, 3],
      [I('prop-olive-tree', 1), 8, 1], [I('prop-olive-press', 1), 7, 4], [I('prop-olive-amphorae', 1), 8, 5]]
  });
  SC.push({
    name: '亚麻田', resource: 'grain', subtype: 'flax_farm',
    road: [[0, 6.5], [3, 6.5], [5, 5.6]],
    items: [[I('site-flax-field', 1), 3, 2], [I('prop-flax-stooks', 1), 7, 3], [I('prop-flax-stooks', 1), 8, 4],
      [I('prop-flax-rettingpit', 1), 2, 4], [I('prop-flax-rettingpit', 1), 2, 3]]
  });
  SC.push({
    name: '牛场', resource: 'livestock', subtype: 'cattle_ranch',
    road: [[0, 6.5], [3, 6.5], [4.5, 5.6]],
    items: [[I('site-cattle-ranch', 1), 3, 2], [I('prop-cattle-hayrick', 1), 1, 1], [I('prop-cattle-hayrick', 1), 2, 1],
      [I('prop-cattle-trough', 1), 1, 4], [I('prop-cattle-cow', 1), 8, 5], [I('prop-cattle-cow', 1), 2, 3]]
  });
  SC.push({
    name: '奶牛场', resource: 'livestock', subtype: 'dairy_farm',
    road: [[0, 6.5], [3, 6.5], [5, 5.6]],
    items: [[I('site-dairy-farm', 1), 3, 2], [I('prop-dairy-churns', 1), 7, 4], [I('prop-dairy-cheeserack', 1), 7, 3],
      [I('prop-dairy-cow', 1), 2, 2], [I('prop-dairy-cow', 1), 2, 3]]
  });
  SC.push({
    name: '猪圈', resource: 'livestock', subtype: 'pig_farm',
    road: [[0, 6.5], [3, 6.5], [5, 5.6]],
    items: [[I('site-pig-farm', 1), 3, 2], [I('prop-pig-trough', 1), 7, 4], [I('prop-pig-pig', 1), 7, 3],
      [I('prop-pig-wallow', 1), 2, 3], [I('prop-pig-pig', 1), 2, 4]]
  });
  SC.push({
    name: '山羊场', resource: 'livestock', subtype: 'goat_farm',
    road: [[0, 6.5], [3, 6.5], [5, 5.6]],
    items: [[I('site-goat-farm', 1), 3, 2], [I('prop-goat-goats', 1), 7, 3], [I('prop-goat-goats', 1), 2, 3]]
  });
  SC.push({
    name: '鸡鸭场', resource: 'livestock', subtype: 'poultry_farm',
    road: [[0, 6.5], [3, 6.5], [5.5, 5.6]],
    items: [[I('site-poultry-yard', 1), 3, 2], [I('prop-poultry-coop', 1), 2, 2], [I('prop-poultry-hens', 1), 2, 4],
      [I('prop-poultry-duckpond', 1), 7, 3], [I('prop-poultry-hens', 1), 7, 5]]
  });
  SC.push({
    name: '养蜂场', resource: 'livestock', subtype: 'apiary',
    road: [[0, 6.5], [3, 6.5], [5, 5.6]],
    items: [[I('site-apiary', 1), 3, 2], [I('prop-apiary-honeypots', 1), 7, 4]]
  });
  SC.push({
    name: '羊场', resource: 'wool', subtype: 'sheep_station',
    road: [[0, 6.5], [3, 6.5], [5, 5.6]],
    items: [[I('site-sheep-station', 1), 3, 2], [I('prop-wool-bales', 1), 1, 2], [I('prop-wool-flock', 1), 1, 4],
      [I('prop-wool-shearstand', 1), 2, 3], [I('prop-wool-flock', 1), 8, 5]]
  });
  SC.push({
    name: '种马场', resource: 'horses', subtype: 'horse_stud',
    road: [[0, 6.5], [3, 6.5], [5, 5.6]],
    items: [[I('site-horse-stud', 1), 3, 2], [I('prop-horse-mare', 1), 1, 3], [I('prop-horse-saddlerack', 1), 2, 4],
      [I('prop-horse-haynet', 1), 2, 2], [I('prop-horse-mare', 1), 8, 5]]
  });
  root.TownArtWS2_scenes = SC;
})(typeof window !== 'undefined' ? window : this);
