# special-infra：东西两套工业与基础设施建筑（3/4 斜俯视，尚未接入游戏）

规范：`docs/town-art-spec.md`。CELL = 48，锚点 = 占地前沿中点 `(w*24, viewBox 高)`，category 全部 `special`，race 全部 `common`。

## 文件

| 文件 | 说明 |
|---|---|
| `infra-core.js` | 公共绘图原语（mulberry32、立方体、两坡顶、圆柱/圆台/穹顶、砖缝/毛石/木板/瓦行纹理、烟、水面、柴堆）和东西两套色板。浏览器挂 `window.TownArtInfraCore` |
| `west-infra.js` | 西式 13 个定义（木刻线描 + 羊皮纸淡彩）。浏览器挂 `window.TownArtInfraWest` |
| `east-infra.js` | 东方 11 个定义（国潮平涂 + 金线勾边）。浏览器挂 `window.TownArtInfraEast` |
| `special-infra.js` | 汇总：`list() / symbol(def) / meta(def) / sprite() / metaAll()`。浏览器挂 `window.TownArt_specialInfra`，Node 用 `module.exports` |
| `build.js` | `node build.js` 生成 `sprite.svg`、`meta.json`，同时检查 symbol id 唯一、内部 id 带前缀、meta 都有对应 symbol |
| `sprite.svg` / `meta.json` | 生成产物（24 个 symbol） |
| `preview.html` | 离线预览（file:// 可开）：分西式、东方两栏的图册，加西式工坊区、东方河埠两个小场景 |

浏览器引用顺序：`infra-core.js → west-infra.js → east-infra.js → special-infra.js`。

## 清单

| id | 占地 | 上伸 px | facility | 特征部件 |
|---|---|---|---|---|
| west-common-smelter-01 | 3×2 | 100 | smelter | 石砌四棱台高炉、炉顶火口、装料坡道、水轮皮风箱棚、出铁口砂床、矿渣堆 |
| west-common-kiln-01 | 2×2 | 62 | kiln | 砖砌圆顶蜂窝窑、火门、短烟道、柴堆、砖垛 |
| west-common-kiln-02 | 2×2 | 112 | kiln | 瓶形陶窑、铁箍、单坡坯棚、陶罐坯 |
| west-common-tannery-01 | 3×2 | 56 | tannery | 木筋茅草工棚、六口鞣池、晾皮架、木桶 |
| west-common-mine_head-01 | 2×2 | 72 | mine_head | 木构井架、天轮、罐笼、绞车、矿车轨与矿车、废石堆 |
| west-common-boiler_house-01 | 3×2 | 136 | boiler_house | 红砖机房、方形砖烟囱、铆钉铁锅炉、黄铜汽包与蒸汽管、压力表、煤堆 |
| west-common-ward_tower-01 | 2×2 | 100 | ward_tower | 三段毛石圆塔、石爪托着悬浮符文水晶、结界环、四块刻符立石 |
| west-common-dock-01 | 3×2 | 74 | dock | 石岸壁、木栈桥、吊杆、系缆柱、两条小船 |
| west-common-warehouse-01 | 3×2 | 86 | warehouse | 山墙朝前的木筋大仓、双开大木门、阁楼货门、吊货梁与滑轮 |
| west-common-warehouse-02 | 3×2 | 66 | warehouse | 毛石长仓、石板瓦、吊货老虎窗、拱门、木装卸台、手推车 |
| west-common-cemetery-01 | 3×2 | 54 | cemetery | 铁栅与铁门、十字碑与圆头碑、新坟、毛石停尸房、紫杉 |
| west-common-bridge-01 | 3×1 | 40 | bridge | 单孔毛石拱桥、券石（桥面东西向） |
| west-common-bridge-02 | 1×3 | 18 | bridge | 木栈桥、栈架、栏杆（桥面南北向） |
| east-common-smelter-01 | 3×2 | 100 | smelter | 夯土圆台高炉、竹篾箍、灰瓦风箱棚与推拉木风箱、陶风管、砂模铁锭、炭堆 |
| east-common-kiln-01 | 3×2 | 56 | kiln | 依坡龙窑：窑头火膛、分节、投柴孔、窑门、窑尾烟囱、柴垛、坛罐 |
| east-common-tannery-01 | 3×2 | 108 | tannery | 染坊：高晾布架挂彩布（含蓝印花布）、灰瓦小作坊、五口染缸 |
| east-common-mine_head-01 | 2×2 | 88 | mine_head | 青绿山壁、木撑洞口、红灯笼、木板道、竹矿篓、扁担、废石堆 |
| east-common-boiler_house-01 | 3×2 | 104 | boiler_house | 铜炉房：灰瓦房、铜烟囱、带符牌的鼎式铜锅炉 |
| east-common-ward_tower-01 | 2×2 | 112 | ward_tower | 镇妖塔：须弥座、三层翘檐塔身、封条拱门、悬空八卦符阵、飘符 |
| east-common-dock-01 | 3×2 | 30 | dock | 青石驳岸、石阶埠头、系船石桩、两条乌篷船、幌子 |
| east-common-warehouse-01 | 3×2 | 76 | warehouse | 两层货栈：二层栏杆与窗、敞开的货间、挂幌 |
| east-common-cemetery-01 | 3×2 | 56 | cemetery | 义冢：矮墙、大碑、香炉、带石圈的土坟与小碑、松、柏、纸钱 |
| east-common-bridge-01 | 3×1 | 46 | bridge | 驼峰单孔石拱桥、石阶桥面、望柱石栏、抱鼓石（桥面东西向） |
| east-common-bridge-02 | 1×3 | 66 | bridge | 廊桥：灰瓦长廊顶、中段青绿亭顶、桥头门楼（桥面南北向） |

## 摆放方向（同时写在 meta 的 note 和 tags 里）

- **桥**
  - `*-bridge-01`（3×1，tag `deck_ew` + `river_ns`）：桥面东西走向，跨南北流向的河。中间一格压在水上，东西两格落在两岸。
  - `*-bridge-02`（1×3，tag `deck_ns` + `river_ew`）：桥面南北走向，跨东西流向的河。中间一格压在水上，南北两格落在两岸。
- **码头**（tag `waterside_south`）：临水的一边朝南。地块前沿（南）贴河道或海岸，后沿接陆地道路。占地后部是岸，前部画成水面，所以水边的码头地块本身就包含一段水。
- 东方矿洞口 tag `cliff_north`：山壁在北，适合北侧接山地。龙窑 tag `slope_rises_east`：窑头在西低处，东侧接坡地更自然。

## roof 取值说明

- 窑、矿井、码头、桥、东方义冢没有屋顶，记 `none`。
- `west-common-kiln-02` 记的是坯棚的 `monopitch`；`west-common-cemetery-01` 记的是停尸房的 `steep_slate`。
- `east-common-ward_tower-01` 是多层翘檐塔，RoofId 里没有对应项，取最接近的 `hip_tile`，note 里已注明。

## 已知问题

- `west-common-bridge-02`（木栈桥）在 3/4 俯视下主要看到桥面，中段抬高只靠左侧窄条桥身和水里的桩表现，立体感偏弱。
- 码头和桥把水面画在 symbol 里面，和真实的河道瓦片叠在一起时，水色可能有色差（西式水色 `#a9b8ad`，东方 `#6cc1b3`）。接入时要以河道瓦片为准统一。
- 结界塔、东方锅炉房的"奇幻"程度靠符阵、水晶、符牌表现，没有做动画。
- 东方石拱桥压在 1 格宽的支渠上时，拱洞比水道稍宽，属于示意性比例。
- 预览页把 sprite 设成 0 尺寸隐藏，不用 `display:none`，因为 display:none 的 sprite 里 clipPath 可能失效。正式接入时也建议这样做。
