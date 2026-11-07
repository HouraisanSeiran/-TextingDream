# 西式 · 矮人族城镇建筑素材（west-dwarf）

3/4 斜俯视，木刻线描 + 羊皮纸淡彩的矮人变种。规范见 `docs/town-art-spec.md`。**美术样板，尚未接入游戏。**

## 文件

| 文件 | 内容 |
|---|---|
| `core.js` | 色板、mulberry32、Ctx、基本图元；巨石立面 `blocks`、平顶 `slabTop`、岩坡 `rockSlope`、铜铆门 `door`、窗 `win`、符文带 `runes`（`TownArtWD_core`） |
| `parts.js` | 烟囱 + 烟团、齿轮、矿车轨道、矿车、粗石柱、低坡石板顶、石穹顶（`TownArtWD_parts`） |
| `houses-a.js` / `houses-b.js` / `houses-c.js` | 民居 01–03 / 04–06 / 07–09 |
| `civic-a.js` | 铁匠铺 ×2、石拱市场厅、露天货摊 ×2、氏族议事厅 |
| `civic-b.js` | 矿井口、啤酒厅、祖先祠、石库房 |
| `tiles.js` | 巨石城墙双网格 16 张 + gate-h / gate-v + 矮堡塔 |
| `west-dwarf.js` | 汇总，浏览器 `window.TownArt_westDwarf`，Node `module.exports` |
| `build.js` | `node build.js` 生成 `sprite.svg` 与 `meta.json`，并做静态自检 |
| `preview.html` + `preview-scene.js` | 离线预览：聚落示意 + 图册 |

浏览器引用顺序：`core.js → parts.js → houses-a/b/c.js → civic-a.js → civic-b.js → tiles.js → west-dwarf.js`。

新增色（在规范西式色板上）：花岗岩 `#9a958c`、深岩 `#6f6a62`、铜 `#b8763a`、铜绿 `#5f8f7e`、熔火橙 `#e07a2f`。墨线 `#4a3826`。

## 清单（共 56 个 symbol）

民居 9 种 × 3 变体（每种至少一个变体改占地或轮廓）：

| 编号 | 名称 | 变体占地 | 特征 |
|---|---|---|---|
| 01 | 嵌山石屋 | 1×1 / 2×1 / 1×1 | 后半截埋进岩坡，只露巨石正立面；v2 加轨道、v3 加矿车 |
| 02 | 拱顶石穹屋 | 1×1 / 2×1 / 1×1 | 矮鼓墙 + 扁石穹；v2 双穹、v3 铜宝珠 + 铜帽烟囱 |
| 03 | 阶梯石屋 | 2×1 / 2×1 / 1×1 | 退台平顶、外挂石阶；v1/v2 退台方向相反 |
| 04 | 圆石塔屋 | 1×1 / 2×1 / 1×1 | 圆鼓石塔；v1 尖锥石板顶、v2 垛口塔 + 侧翼、v3 矮胖铜绿锥顶 |
| 05 | 矿工长屋 | 2×1 / 2×2 / 2×1 | 横长低坡石板顶；v3 一端埋进岩坡 + 矿门 + 矿车 |
| 06 | 铜烟囱作坊宅 | 1×1 / 2×1 / 2×2 | 铜箍铜烟道、熔火映窗、墙上齿轮 |
| 07 | 石门洞宅 | 1×1 / 2×1 / 1×1 | 岩壁凿出的穴居；v3 铜圈圆门 |
| 08 | 双层厚墙宅 | 1×1 / 2×1 / 2×2 | 两层巨石墙 + 斜扶壁；v3 带前院矮墙 |
| 09 | 齿轮磨坊宅 | 1×1 / 2×1 / 2×1 | 立面大铜齿轮组 |

特殊建筑与叠加件：

| id | 名称 | facility | 占地 |
|---|---|---|---|
| west-dwarf-forge-01 | 铁匠铺（嵌山熔炉坊）：三烟囱、大拱炉口、风箱、巨砧、水轮驱动锻锤 | forge | 3×2 |
| west-dwarf-forge-02 | 铁匠铺（圆鼓高炉）：圆鼓炉身 + 收分烟囱、锻锤棚、水轮 | forge | 2×2 |
| west-dwarf-market-01 | 石拱市场厅：三开间半圆拱、粗方柱、屋脊铜钟亭 | market_hall | 3×2 |
| west-dwarf-stall-01 / -02 | 露天货摊（category=prop，tags 含 open_air） | market_hall | 1×1 |
| west-dwarf-town-hall-01 | 氏族议事厅：巨大铜石门、四根符文巨柱、山花齿轮纹章 | town_hall | 4×3 |
| west-dwarf-mine-head-01 | 矿井口：岩坡矿门、木井架绞轮、轨道矿车 | mine_head | 3×2 |
| west-dwarf-inn-01 | 啤酒厅：拱门、酒桶 | inn | 3×2 |
| west-dwarf-temple-01 | 祖先祠：半嵌山体、符文柱门廊、祖先石像、长明火盆 | temple | 3×2 |
| west-dwarf-warehouse-01 | 石库房：无窗厚墙、宽铜门、屋顶吊臂 | warehouse | 2×2 |
| west-dwarf-wall-0000 … 1111 | 巨石城墙 16 张（墙高 44，层高 11、块长 24，按瓦片坐标对齐） | city_wall | 1×1 |
| west-dwarf-wall-gate-h / gate-v | 巨石城门（东西向 / 南北向墙段） | gate | 1×1 |
| west-dwarf-wall-tower | 矮堡塔（拐角 / 端点） | watchtower | 1×1 |

叠加件对齐逻辑格，锚点 = 逻辑格前沿中点。预览场景里叠加件的排序键取前沿 + 24.5，确保压在同格后半的墙瓦片之上。

## roof 对照

石板平顶、退台记 `flat_mud`；低坡石板顶记 `gable_tile`（石板代瓦）；嵌山、穹顶、凿岩记 `none`；圆塔锥顶记 `steep_slate`；货摊布篷记 `monopitch`。每项 note 里都写了原因。

## 已知问题

- 上伸最高 60 px（矮堡塔），全部 ≤ 144；按 getBBox 统计，前沿以下只有投影，且下伸不超过 6 px。
- 挑檐、压檐石、台基会比 viewBox 左右边多出 2.7–3.6 px，涉及 house-07-3、forge-01、town-hall-01、temple-01。west-base 的挑檐也是同样做法；邻格紧贴时会稍微压到邻居。
- 未覆盖的 FacilityKind：lord_hall、granary、cistern、well、mill（齿轮磨坊宅是民居，没有标 mill）、smelter、kiln、tannery、barracks、academy、infirmary、caravanserai、stable、dock、boiler_house、ward_tower、cemetery、bridge。
- 道路瓦片不在本目录，沿用 west-base 的三档道路。
