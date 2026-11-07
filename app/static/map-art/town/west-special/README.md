# west-special：西式奇幻特殊建筑（3/4 斜俯视；美术样板，尚未接入游戏）

规范：`docs/town-art-spec.md`。木刻线描 + 羊皮纸淡彩，画法与 `fog-brushes/fog-celestial.js` 的船只一致：不透明平涂 + 墨线勾边 + 少量短排线，不用渐变、高光、模糊。全部是原创程序化路径，随机由 mulberry32 种子派生。

## 文件

| 文件 | 内容 |
|---|---|
| `prims.js` | 共用画笔：墙（灰泥/木筋/毛石/方整石/砖/木板）、门窗、坡顶/山墙朝前/四坡/攒尖/圆锥、圆柱体、烟囱、炊烟、酒桶、木箱、铁砧、旗、石板地坪等。`window.TownArtWS_prims` |
| `civic.js` | 铁匠铺、行政厅、领主府、教堂。`window.TownArtWS_civic` |
| `trade.js` | 摊位、市集厅、酒馆客栈、商队驿站、粮仓、马厩。`window.TownArtWS_trade` |
| `service.js` | 水井、蓄水池、水磨、风车、学院、医馆、兵营、瞭望塔。`window.TownArtWS_service` |
| `west-special.js` | 汇总：`list() / symbol(def) / meta(def) / svg(def)`。`window.TownArt_westSpecial` |
| `build.js` | `node build.js` 生成 `sprite.svg`、`meta.json`，并检查 id 唯一、facility 合法、占地范围、内部 id 前缀 |
| `preview.html` | file:// 直接打开：全部建筑网格（2 倍）+ 小广场示意（按锚点 y 排序） |

浏览器引入顺序：`prims.js → civic.js → trade.js → service.js → west-special.js`。

meta 在规范字段外多一个 `name_zh`（中文名）。

## 清单（27 个：special 24，prop 3）

| id | 中文名 | facility | 占地 | 上伸 px | roof |
|---|---|---|---|---|---|
| west-common-forge-01 | 铁匠铺·作坊棚 | forge | 3×2 | 76 | gable_tile |
| west-common-forge-02 | 铁匠铺·山墙作坊 | forge | 2×2 | 70 | gable_tile |
| west-common-town-hall-01 | 市政厅·钟楼 | town_hall | 3×2 | 120 | gable_tile |
| west-common-town-hall-02 | 议事厅·阶梯山墙 | town_hall | 3×2 | 100 | steep_slate |
| west-common-lord-hall-01 | 领主府 | lord_hall | 4×3 | 100 | hip_tile |
| west-common-temple-01 | 大教堂·尖塔 | temple | 3×3 | 144 | steep_slate |
| west-common-temple-02 | 教区教堂·钟塔 | temple | 3×2 | 128 | gable_tile |
| west-common-temple-03 | 小礼拜堂 | temple | 2×2 | 84 | steep_slate |
| west-common-stall-01 | 菜摊·红白篷（prop） | market_hall | 1×1 | 34 | none |
| west-common-stall-02 | 果摊·青白篷（prop） | market_hall | 1×1 | 34 | none |
| west-common-stall-03 | 粮面摊·帆布帐（prop） | market_hall | 1×1 | 34 | none |
| west-common-market-hall-01 | 市集厅·拱廊 | market_hall | 3×2 | 70 | hip_tile |
| west-common-market-hall-02 | 市集厅·木柱敞厅 | market_hall | 3×2 | 58 | hip_tile |
| west-common-inn-01 | 客栈·酒桶招牌 | inn | 3×2 | 92 | gable_tile |
| west-common-inn-02 | 酒馆·茅草驿道店 | inn | 3×2 | 84 | gable_thatch |
| west-common-caravanserai-01 | 商队驿站·围院 | caravanserai | 4×3 | 62 | gable_tile |
| west-common-granary-01 | 粮仓·垫石木仓 | granary | 2×2 | 58 | gable_thatch |
| west-common-granary-02 | 粮仓·什一税谷仓 | granary | 3×2 | 60 | gable_tile |
| west-common-stable-01 | 马厩 | stable | 3×2 | 56 | gable_thatch |
| west-common-well-01 | 水井·辘轳亭 | well | 2×2 | 46 | gable_tile |
| west-common-cistern-01 | 蓄水池·狮口水槽 | cistern | 3×2 | 30 | none |
| west-common-watermill-01 | 水磨坊 | mill | 3×2 | 70 | gable_tile |
| west-common-windmill-02 | 风车磨坊 | mill | 2×2 | 144 | none |
| west-common-academy-01 | 学院·观星塔 | academy | 3×2 | 96 | steep_slate |
| west-common-infirmary-01 | 医馆·药圃 | infirmary | 3×2 | 70 | gable_tile |
| west-common-barracks-01 | 兵营·操练场 | barracks | 4×2 | 70 | gable_tile |
| west-common-watchtower-01 | 瞭望塔·烽火 | watchtower | 2×2 | 144 | monopitch |

- 露天摊位按规范用 `facility: market_hall` + `tags: open_air`，category 为 `prop`，1×1 可散放。
- 水车、风车都属于 `mill`，用 kind（watermill / windmill）区分，variant 分别为 1、2。
- roof 对不上 RoofId 的（水井木瓦顶、风车圆锥帽、瞭望塔四坡小顶）在 meta.note 里写了说明。

## FacilityKind 覆盖

本目录覆盖 16 种：town_hall、lord_hall、market_hall、granary、cistern、well、mill、forge、barracks、watchtower、temple、academy、infirmary、inn、caravanserai、stable。

不在本目录的 12 种：
- smelter、kiln、tannery、mine_head、boiler_house、ward_tower、dock、warehouse、cemetery、bridge：分工调整后由子代理 ⑥（`special-infra/`）负责正式版，本目录没有画。
- city_wall、gate：规范规定由城墙瓦片与城门叠加件承担（`west-base/`）。

## 配色

全部取自规范西式色表，另加两种补色：叶绿 `#8f9a5c`（菜蔬、灌木、药草）和水面灰蓝 `#8e9a9c`（井水、蓄水池、溪水）。规范色表里没有这两类用途的颜色。炊烟用 `#e6dccb`。

## 已知问题

- 广场示意里的石板路面块只是预览用的一整块平铺，不是道路瓦片。
- 大教堂、风车、瞭望塔上伸都顶到 144 px 上限，排到前排时会遮挡后排较多。
- 小摊位、马厩里的马头、药圃这类细节按 1 倍（48 px/格）显示时很小，靠颜色块才认得出。
- 斜俯视是"屋顶 + 正立面"的近似画法，侧面不露；圆塔、风车塔用椭圆底近似，与方形建筑的透视不完全一致。
