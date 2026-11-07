# west-site-2 · 西式（人族）资源点第二批

3/4 斜俯视，CELL 48，style=west，race=common。美术样板，**尚未接入游戏**。规范见 `docs/town-art-spec.md` 第 14、16 节。

## 文件
- `core.js`：公共画笔（复制自 `west-site/core.js`，全局名改为 `TownArtWS2_core`，补了第二批色值）
- `kit.js`：公共构件 `C.K`（小屋/敞棚、田垄、树、水塘、方池、木桶、草垛、晾架）
- `shapes-mine.js`：青金石露天矿 lapis/open_pit（台阶坑画法 `C.pit`）
- `shapes-mine2.js`：稀有金属平硐 rare_metals/adit、露天煤坑 coal/open_pit、烧炭窑场 coal/charcoal_kiln
- `shapes-trade.js`：番红花香料园 spices、养蚕缫丝坊 silk
- `shapes-craft.js`：象牙作坊与牙料仓 ivory（只画收购、仓储、雕刻）、染料场 dye
- `shapes-coast.js`：采珠场 pearls
- `shapes-crop.js`：grain 的 wheat_farm、vegetable_farm、flax_farm
- `shapes-tree.js`：grain 的 orchard、olive_grove
- `shapes-stock.js`：livestock 的 cattle_ranch、dairy_farm、pig_farm
- `shapes-stock2.js`：livestock 的 goat_farm、poultry_farm、apiary，wool/sheep_station，horses/horse_stud
- `west-site-2.js`：组装，浏览器挂 `window.TownArt_westSite2`，Node 用 `module.exports`
- `build.js`：生成 `sprite.svg`、`meta.json` 并自检
- `preview.html` + `preview.js` + `preview-scenes.js`：图册 + 22 张 10×8 格示意小地图（草地底纹只读引用 `../west-ground/`）

## 数量
102 个 symbol：site 22、prop 64、ground 16（4 套 × 4 变体：lapisrubble、coalpitfloor、pearlsand、dyeyard）。

## meta 说明
- 新增字段 `subtype`。农牧类按规范 16.2 必填；非农牧填形制：`open_pit`、`adit`、`charcoal_kiln`、`saffron_garden`、`sericulture`、`carving_workshop`、`woad_madder`、`oyster_bed`。
- 农牧类的摆件也带 subtype，其他资源的摆件 subtype 为 null。
- facility 对不上的填 null，note 里写了原因（香料园、缫丝坊、染料场、菜园、亚麻田、苹果园、鸡鸭场、养蜂场）。
- 牲畜棚统一归 `stable`；榨油石磨归 `mill`；采珠小栈桥归 `dock`；牙料仓归 `warehouse`；烧炭窑归 `kiln`；谷仓归 `granary`。

## 自检
```
node --check *.js
node build.js      # facility/resource/subtype 合法、占地上伸、内部 id 唯一、symbol 与 meta 一一对应、与 town/ 下其他目录不撞名
```

## 已知问题
- 水面在预览里是平涂矩形（`#a9b8ad`），不是正式水面瓦片；采珠场主体自带的岸线和预览水区的分界是手工对齐的。
- 动物都是侧身简化轮廓，朝向只有左右两种。
- 苹果园、橄榄园的树排得比较规整，后排树冠会盖住前排树干的上半截。
- 第二批 grain 的 rice_paddy、millet_farm、cotton_farm 在本批任务范围外，没有画。
