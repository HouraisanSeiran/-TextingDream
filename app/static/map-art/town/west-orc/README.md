# 织梦 · 城镇兽人族素材（west / orc，美术样板，尚未接入游戏）

3/4 斜俯视，48 px 网格，光从左上。西式木刻线描 + 羊皮纸淡彩的兽人变种：不透明平涂 + 墨线 `#4a3826` + 少量短排线，不用渐变、高光、模糊。
追加色：兽皮褐 `#9b7550`、深皮 `#6e4e33`、骨白 `#e6dcc2`、锈红 `#8f3a26`、苔绿 `#6f7a4a`。规范见 `docs/town-art-spec.md`。

## 文件

| 文件 | 内容 |
|---|---|
| `core.js` | 色板、mulberry32、Ctx、基础图元；投影统一带 `class="sh"` |
| `parts.js` | 部件：兽皮/茅草/粗石/原木纹理，头骨、长角、獠牙、尖桩、绳结、图腾柱、战旗、篝火坑、粗刀斧、骨串 |
| `forms.js` | 体块：圆顶帐、圆筒墙、圆锥顶、矩形立面、侧墙条、长坡顶、山墙朝前坡顶、门洞 |
| `houses-a.js` / `houses-b.js` | 民居 01–05 / 06–10 |
| `special-a.js` | 铁匠铺 ×2、交易场、摊位 ×2、酋长大帐 |
| `special-b.js` | 兵营、瞭望塔、神殿、座狼圈 |
| `tiles.js` | 尖木栅墙 16 张 + gate-h / gate-v |
| `west-orc.js` | 汇总，浏览器 `window.TownArt_westOrc`，Node `module.exports` |
| `build.js` | `node build.js` 生成 `sprite.svg`、`meta.json` |
| `preview.html` + `preview-demo.js` | 图册 + 兽人营地示意（file:// 可开） |

浏览器引入顺序：core、parts、forms、houses-a、houses-b、special-a、special-b、tiles、west-orc。

## 清单（58 个 symbol）

民居 10 种 × 3 变体（`west-orc-house-NN-i`），每种至少一个变体改了轮廓：

| NN | 名称 | 占地 | 变体差异 |
|---|---|---|---|
| 01 | 圆顶兽皮帐 | 1×1 | 矮宽 / 高尖深皮 + 战旗 / 主帐 + 后侧小帐 |
| 02 | 长条兽皮帐 | 2×1 | A 字落地 / 收山歪斜 + 小帐 / 原木矮墙上的帐 |
| 03 | 粗石圆屋 | 1×1 | 茅草锥顶 + 长角头骨 / 两层锥顶 + 旗 / 矮墙草皮圆顶 + 石烟囱 |
| 04 | 半地穴屋 | 1×1 | 皮锥顶 / 草皮顶 + 烟道 / 撑杆高帐 |
| 05 | 原木长屋 | 2×1 | 茅草补丁顶 / 加山墙门廊 + 战旗 / 石基竖木墙 + 皮顶收山 + 晾皮架 |
| 06 | 骨架棚屋 | 1×1 | 宽 / 窄高 / 深皮 + 头骨冠 |
| 07 | 高脚瞭望屋 | 1×1 | 茅草顶 / 更高 + 苔绿旗 / 矮脚圆锥皮顶 |
| 08 | 带畜栏的帐屋 | 2×2 | 帐 + 野猪圈，左右布置与附件不同 |
| 09 | 皮草混顶小屋 | 1×1 | 茅草与兽皮各半的坡顶，墙材不同 |
| 10 | 图腾院落帐 | 2×1 | 单坡帐 + 图腾柱 + 篝火，布置互换 / 翼顶图腾 |

特殊建筑与瓦片：

| id | 中文名 | facility | 占地 |
|---|---|---|---|
| west-orc-forge-01 | 露天铁匠场 | forge | 2×2 |
| west-orc-forge-02 | 粗石炼炉棚 | forge | 2×1 |
| west-orc-market-01 | 兽皮篷交易场 | market_hall | 3×2 |
| west-orc-stall-01 | 毛皮摊（prop，open_air） | market_hall | 1×1 |
| west-orc-stall-02 | 骨角陶器摊（prop，open_air） | market_hall | 1×1 |
| west-orc-town-hall-01 | 酋长大帐 | town_hall | 3×3 |
| west-orc-barracks-01 | 战士营帐 | barracks | 3×2 |
| west-orc-watchtower-01 | 木架哨塔 | watchtower | 1×1（上伸 98 px） |
| west-orc-temple-01 | 萨满祭坛 | temple | 2×2 |
| west-orc-stable-01 | 座狼圈 | stable | 3×2 |
| west-orc-wall-0000…1111 | 尖木栅墙（16 张，0000 透明） | city_wall | 1×1 |
| west-orc-gate-h | 骨饰栅门（东西向） | gate | 1×1 |
| west-orc-gate-v | 骨饰栅门（南北向） | gate | 1×1 |

未覆盖的 FacilityKind：lord_hall、granary、cistern、well、mill、smelter、kiln、tannery、academy、infirmary、inn、caravanserai、dock、warehouse、mine_head、boiler_house、ward_tower、cemetery、bridge。

## 栅墙与栅门的约定

- 桩沿逻辑格中心线（= 渲染瓦片的边）走。每张瓦片只画 **SW 角柱、底边（SW→SE）、左边（NW→SW）** 的桩，另外两条边的桩归相邻瓦片，这样同一根桩不会画两次，并且由锚点最靠前的瓦片来画，排序正确。桩距 4 px，桩高按序号以 12 根为一周期循环，拼接处连续。
- 因此像 0100、1000、1100 这类只含北侧角的瓦片只有地面土垄、没有桩，这是正常的。
- 栅门是**替换瓦片**：`gate-h` 放在原本 `wall-0011` 的位置，`gate-v` 放在原本 `wall-1010` 的位置，锚点和被替换的瓦片相同。
- 角柱和门柱的中心在瓦片边上，横向会伸出瓦片 3–12 px，属于双网格的正常重叠。

## meta 说明

- `roof`：圆顶帐、骨架棚、半地穴、交易场、大帐等没有对应的 RoofId，写 `none`；兽皮 A 字帐写最接近的 `gable_thatch`，并在 note 里说明。
- `kind` 是自定义的描述名（`house_yurt`、`orc_forge_open` 等）。

## 已知问题

- 南北向墙段（1010 等）正面只露一列桩头，读作一条竖带，比东西向墙段单薄。
- gate-v 的门楼顶向西多伸出约 12 px，和西侧格子重叠。
- 08 号三个变体的轮廓接近，主要差在布置。
- 营地示意里有几处建筑挨得很近，只是摆放示意，不是规划结果。
