# west-site · 西式（人族）资源点素材

3/4 斜俯视，CELL 48，木刻线描 + 羊皮纸淡彩；水色 `#a9b8ad`（与码头统一）。美术样板，**尚未接入游戏**。
规范：`docs/town-art-spec.md` 第 1–6、9、14 节。style=west，race=common。

## 文件
- `core.js`：画笔、配色、mulberry32 种子随机、`def()` 登记、`groundSet()` 平铺地面（元素按 ±48 平移复制后裁切，保证无缝）
- `shapes-timber.js` 伐木场 · `shapes-stone.js` 采石/大理石 · `shapes-mine.js` 铁铜锡金银煤 · `shapes-earth.js` 黏土/盐/硫磺/宝石/琥珀 · `shapes-water.js` 渔场/芦苇 · `shapes-farm.js` 牧场/剪毛/马场/农庄/药圃/葡萄园 · `shapes-fantasy.js` 魔力晶矿/龙骨坑
- `west-site.js`：组装，浏览器 `window.TownArt_westSite`（`build()` / `sprite()`），Node `module.exports`
- `build.js`：`node build.js` 生成 `sprite.svg`、`meta.json` 并做基础校验
- `preview.html` + `preview.js` + `preview-scenes.js`：图册 + 24 张 10×8 格示意小地图（草地底纹只读引用 `../west-ground/*.js` 现场生成）

## 数量
119 个 symbol：site 26、prop 49、ground 44（11 种专用地面 × 4 变体）。meta 每项含 `resource`、`name`（中文）。

## 资源 → 主体 / 摆件 / 地面
| resource | site | prop | ground |
|---|---|---|---|
| timber | 锯木棚、水力锯坊 | 原木垛、运木车、劈柴墩 | 树桩地 |
| stone | 阶梯采石面 | 石块垛、碎石堆 | 采石场裸岩 |
| marble | 大理石采面 | 精切大理石块（+碎石堆） | 大理石碎屑地 |
| iron | 铁矿井架 | 矿石堆、矿车、焙烧矿堆 | 矿渣地 |
| copper | 铜矿矿道口（绿锈） | 矿石堆、矿车、淋铜池 | 矿渣地（共用） |
| tin | 锡矿矿道口 | 矿石堆、矿车、洗矿圆池 | 矿渣地（共用） |
| gold | 金矿矿道口（溪流） | 矿石堆、矿车、淘金槽 | 矿渣地（共用） |
| silver | 银矿井架（马拉绞盘） | 矿石堆、矿车、灰吹炉 | 矿渣地（共用） |
| coal | 煤矿矿道口（煤层） | 煤堆、矿车、煤筐 | 煤尘地 |
| clay | 取土坑、晒坯场 | 砖坯垛 | — |
| salt | 熬盐棚 | 盐堆 | 盐田格 |
| sulfur | 硫磺喷气坑 | 硫磺块堆 | 硫华地 |
| gems / amber | 宝石手工矿坑 / 琥珀挖掘坑 | 筛矿台 | — |
| fish | 渔村栈桥 | 晒网架、鱼篓 | — |
| reed | 芦苇割场 | 捆苇垛、芦苇丛 | — |
| livestock / wool | 羊圈 / 剪毛棚 | 干草架、羊群 / 羊毛捆 | — |
| horses | 驯马场 | 拴马桩与饮马槽 | — |
| grain | 谷仓 | 打谷场、麦捆垛 | 麦田格 |
| herb | 药草田 | 晒药架、药草篮 | — |
| wine | 压榨坊 | 酒桶、葡萄采摘筐 | 葡萄架行列 |
| mana | 魔力晶簇矿坑 | 魔力晶簇、守护符文石、晶块货箱 | 晶屑岩地 |
| dragonbone | 龙骨发掘场 | 龙骨堆、发掘脚手架、发掘工具帐 | 发掘翻土地 |

facility：矿山 6 种 + 宝石坑 + 晶矿 → `mine_head`；羊圈、驯马场 → `stable`；谷仓 → `granary`；渔村栈桥 → `dock`；其余 null（锯木坊、采石场、压榨坊、盐棚等无对应 FacilityKind）。

## 已知问题
- 专用地面只做了平铺底纹，没做双网格过渡；与草地交界是硬直边（预览小地图里看得出方块边）。
- 预览里的土路是粗描边折线，不是 west-ground/west-base 的正式道路瓦片；水面也是预览用平涂矩形。
- clay、gems、amber、fish、reed、herb、horses、wool 摆件只有 1–2 种（规范要 3–5），靠重复摆放凑场景。
- 矿渣地 4 种矿共用一套；每个 symbol 只有 1 个变体。
- 铜/锡/金三个矿道口共用同一山体轮廓，主要靠绿锈、溪流和专属摆件区分。
