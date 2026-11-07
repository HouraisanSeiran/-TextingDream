# east-site-2：东方（人族）资源点第二批

国潮平涂 + 金线勾边，3/4 斜俯视，48 px 格；style=east、race=common。**素材尚未接入游戏。**
画风、色板、水色（`#6cc1b3`）与第一批 `east-site/` 一致：`core.js`、`kit.js`、`kit2.js` 复制自 east-site，只把全局名改成 `TownArtES2_*`，并给 `core.make` 加了 `subtype` 字段；原目录未改。

## 文件
- `core.js` 画笔色板 + `make()`（组装 symbol 与 meta）
- `kit.js` / `kit2.js` 共用部件（复制自 east-site）；`kit3.js` 本批新部件（栅栏、侧视牲畜、树、缸、旗、小房、崖面、毡房、可平铺碎屑地面、轨道、矿车、敞棚）
- `s-wool.js` 羊场；`s-mine.js` 稀有金属矿、青金石矿；`s-stone.js` 汉白玉采石场；`s-hot.js` 硫磺矿；`s-craft.js` 牙行作坊、琥珀坑；`s-wine.js` 酒坊；`s-coal.js` 露天煤场、木炭窑；`s-field.js` 稻作、粟黍、菜园；`s-field2.js` 果园、棉田、苎麻田；`s-herd.js` 牛栏、奶场、猪圈；`s-herd2.js` 山羊、鸡鸭、养蜂、牧马
- `east-site-2.js` 汇总入口：浏览器挂 `window.TownArt_eastSite2`，Node 用 `module.exports`；`buildAll()` 返回 `{ items, scenes, spriteSvg() }`
- `build.js`：`node build.js` 生成 `sprite.svg` + `meta.json` 并自检（id 唯一、不和 `town/` 下其他目录撞名、facility 在 28 种之内或 null、resource / subtype 合法、尺寸范围、内部 id 带前缀、场景引用存在）
- `preview.html` + `preview-scenes.js`：离线预览（file:// 可开），23 张 10×8 格示意小地图 + 图册；底纹只读引用 `../east-ground/` 的黄土 earth-01..04

## 主体清单（共 123 项：site 23 / prop 69 / ground 31）

| id | resource | subtype | 占地 | facility |
|---|---|---|---|---|
| east-common-site-sheepstation-01 | wool | sheep_station | 4×3 | null |
| east-common-site-raremetal-adit-01 | rare_metals | adit | 4×3 | mine_head |
| east-common-site-lapis-pit-01 | lapis | open_pit | 4×3 | mine_head |
| east-common-site-marble-quarry-01 | marble | open_pit | 4×3 | null |
| east-common-site-sulfur-pit-01 | sulfur | open_pit | 4×3 | kiln |
| east-common-site-ivory-workshop-01 | ivory | carving_workshop | 4×3 | warehouse |
| east-common-site-amber-dig-01 | amber | forest_dig | 4×3 | null |
| east-common-site-wine-distillery-01 | wine | distillery | 4×3 | null |
| east-common-site-coal-openpit-01 | coal | open_pit | 4×3 | mine_head |
| east-common-site-charcoal-kiln-01 | coal | charcoal_kiln | 4×3 | kiln |
| east-common-site-ricefarm-01 | grain | rice_paddy | 4×3 | null |
| east-common-site-milletfarm-01 | grain | millet_farm | 4×3 | granary |
| east-common-site-vegfarm-01 | grain | vegetable_farm | 4×3 | well |
| east-common-site-orchard-01 | grain | orchard | 4×3 | warehouse |
| east-common-site-cottonfarm-01 | grain | cotton_farm | 4×3 | null |
| east-common-site-ramiefarm-01 | grain | flax_farm | 4×3 | null |
| east-common-site-cattlebarn-01 | livestock | cattle_ranch | 4×3 | null |
| east-common-site-yakdairy-01 | livestock | dairy_farm | 4×3 | null |
| east-common-site-pigfarm-01 | livestock | pig_farm | 3×3 | null |
| east-common-site-goatfarm-01 | livestock | goat_farm | 4×3 | null |
| east-common-site-poultryfarm-01 | livestock | poultry_farm | 4×3 | null |
| east-common-site-apiary-01 | livestock | apiary | 4×3 | null |
| east-common-site-horsestud-01 | horses | horse_stud | 5×3 | stable |

facility 为 null 的主体在 meta `note` 里写了原因。摆件（每个资源点 2–4 个，1×1、上伸 ≤ 48 px）和专用地面（1×1 可平铺）见 `meta.json`。

## 已知问题
- `subtype` 里 `carving_workshop`、`forest_dig`、`distillery`、`charcoal_kiln` 是本批自拟的形制名，规范 16.2 没有列出（非农牧资源允许自填）。
- `flax_farm` 画成东方苎麻 + 沤麻池，没有画亚麻。
- `sulfur` 主体按炼磺土灶归 `kiln`，`ivory` / `orchard` 按仓储归 `warehouse`，`vegetable_farm` 按辘轳井归 `well`。这几项属于近似归类，接入时需要再确认。
- 牲畜和人物都是 10–18 px 的小剪影，缩小到 0.75 倍后细节有限。
- 羊场的草场底纹原想叫 `pasture`，和第一批撞名，改成了 `steppe`。
