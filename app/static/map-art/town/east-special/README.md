# east-special：东方玄幻城镇特殊建筑（3/4 斜俯视，尚未接入游戏）

规范：`docs/town-art-spec.md`。style = `east`，race = `common`。画风与 `fog-brushes/fog-xiangyun.js` 的 PAL 统一：国潮不透明平涂 + 金线勾边 + 叠晕，屋脊鸱吻 / 燕尾、檐角起翘、瓦垄线、瓦当。全部原创程序化路径，随机由 mulberry32 种子派生。

## 文件

| 文件 | 内容 |
|---|---|
| `core.js` | 公共画法：屋顶（庑殿/歇山、硬山、攒尖、重檐下檐）、立面、门、格扇、匾额、灯笼、幌子、栏杆、院墙、树、烟、火、箩筐、坛罐；`symbolOf()` |
| `civic.js` | 打铁铺 ×2、县衙 ×2、王府 |
| `religion.js` | 佛寺、大寺（钟鼓楼）、道观、七级佛塔、牌坊 |
| `trade.js` | 摊棚 ×5、扁担箩筐、市楼 ×2、酒楼、客栈、马厩、驿站、粮仓 ×2、水车磨坊、碾坊 |
| `service.js` | 水井 ×2、蓄水池 ×2、书院、医馆、营房、鼓楼、木望楼 |
| `east-special.js` | 汇总入口：浏览器 `window.TownArt_eastSpecial`，Node `module.exports`；`list() / symbol(id) / symbolSvg(id) / spriteSvg()` |
| `build.js` | `node build.js` 生成 `sprite.svg`、`meta.json` 并自检 |
| `preview.html` | file:// 直接打开；按顺序 `<script src>` 引 core → 各模块 → east-special.js |

浏览器引用顺序：`core.js, civic.js, religion.js, trade.js, service.js, east-special.js`。

## id 约定

`east-common-<kind>-<NN>`。规范要求 id 全小写加连字符，所以 kind 里的下划线在 id 里换成连字符（`town_hall` → `east-common-town-hall-01`）；meta 的 `kind` 字段保留原值 `town_hall`。meta 另加了 `name_zh`（中文名）字段。

## 清单（35 个）

| id | 中文名 | facility | category | 占地 | 上伸 px | roof |
|---|---|---|---|---|---|---|
| east-common-forge-01 | 打铁铺 | forge | special | 2×2 | 64 | gable_tile |
| east-common-forge-02 | 铁匠作坊（带铺面） | forge | special | 3×2 | 96 | gable_tile |
| east-common-town-hall-01 | 县衙 | town_hall | special | 3×3 | 72 | hip_tile |
| east-common-town-hall-02 | 州衙（照壁大院） | town_hall | special | 4×3 | 80 | hip_tile |
| east-common-lord-hall-01 | 王府 | lord_hall | special | 4×3 | 96 | hip_tile |
| east-common-temple-01 | 佛寺 | temple | special | 3×3 | 96 | hip_tile |
| east-common-temple-02 | 大寺（钟鼓楼） | temple | special | 4×3 | 112 | hip_tile |
| east-common-temple-03 | 道观 | temple | special | 3×3 | 96 | hip_tile |
| east-common-temple-04 | 七级佛塔 | temple | special | 2×2 | 144 | hip_tile |
| east-common-paifang-01 | 三间四柱牌坊 | null | prop | 3×1 | 96 | hip_tile |
| east-common-stall-01 | 菜摊 | market_hall | prop | 1×1 | 40 | none |
| east-common-stall-02 | 果摊 | market_hall | prop | 1×1 | 40 | none |
| east-common-stall-03 | 鱼摊 | market_hall | prop | 1×1 | 40 | none |
| east-common-stall-04 | 布摊 | market_hall | prop | 1×1 | 40 | none |
| east-common-stall-05 | 点心摊 | market_hall | prop | 1×1 | 40 | none |
| east-common-carry-pole-01 | 扁担箩筐 | market_hall | prop | 1×1 | 4 | none |
| east-common-market-hall-01 | 市楼（两层商楼） | market_hall | special | 3×2 | 80 | hip_tile |
| east-common-market-hall-02 | 跨街市楼（钟鼓市楼） | market_hall | special | 3×2 | 72 | hip_tile |
| east-common-inn-01 | 酒楼 | inn | special | 3×2 | 88 | hip_tile |
| east-common-inn-02 | 三层客栈楼 | inn | special | 3×2 | 128 | hip_tile |
| east-common-stable-01 | 马厩 | stable | special | 3×2 | 56 | gable_tile |
| east-common-caravanserai-01 | 驿站 | caravanserai | special | 4×3 | 72 | gable_tile |
| east-common-granary-01 | 圆仓粮囤 | granary | special | 3×2 | 64 | gable_thatch |
| east-common-granary-02 | 官仓廒间 | granary | special | 4×2 | 60 | gable_tile |
| east-common-mill-01 | 水车磨坊 | mill | special | 3×2 | 60 | gable_tile |
| east-common-mill-02 | 碾坊 | mill | special | 2×2 | 44 | hip_tile |
| east-common-well-01 | 辘轳井 | well | prop | 1×1 | 40 | none |
| east-common-well-02 | 井亭 | well | special | 2×2 | 80 | hip_tile |
| east-common-cistern-01 | 荷花池 | cistern | special | 3×2 | 30 | none |
| east-common-cistern-02 | 石砌蓄水池（太平缸） | cistern | special | 2×2 | 40 | none |
| east-common-academy-01 | 书院 | academy | special | 3×3 | 80 | hip_tile |
| east-common-infirmary-01 | 医馆（药铺） | infirmary | special | 3×2 | 72 | gable_tile |
| east-common-barracks-01 | 营房（兵营） | barracks | special | 4×3 | 72 | gable_tile |
| east-common-watchtower-01 | 鼓楼 | watchtower | special | 2×2 | 128 | hip_tile |
| east-common-watchtower-02 | 木望楼（更楼） | watchtower | special | 2×2 | 136 | hip_tile |

露天摊棚和扁担是 `facility: market_hall` + tag `open_air`，用来和两座市楼区分。

## FacilityKind 覆盖

本目录覆盖 16 种：town_hall、lord_hall、market_hall、granary、cistern、well、mill、forge、temple、inn、caravanserai、stable、academy、infirmary、barracks、watchtower。

未覆盖的 12 种：
- **smelter、kiln、tannery、mine_head、boiler_house、ward_tower、dock、warehouse、cemetery、bridge**：按分工调整，正式版由 ⑥ 负责（目录 `special-infra/`），本目录没有画。
- **city_wall、gate**：由 ③ `east-base/` 的城墙瓦片和城门楼承担。

## 说明与已知问题

- 牌坊在 FacilityKind 里没有对应项，所以 facility 记 `null`。它可以放在街口、寺前，或墓道前作义冢入口。
- 钟鼓楼 `watchtower-01` 记作 watchtower（击鼓报时、瞭望）。佛寺里的钟楼和鼓楼是 `temple-02` 的组成部分，没有单列。
- 圆仓的圆锥草顶在 RoofId 里没有对应项，记最近的 `gable_thatch`。攒尖、重檐歇山一律记 `hip_tile`。
- 戏台、祠堂还没画。
- 投影只往下伸 3 px（规范上限 6 px）。build.js 没有逐像素检查建筑是否越过前沿，这一点靠截图目视确认。
- 字迹全部用短横竖暗示，不写真字。
