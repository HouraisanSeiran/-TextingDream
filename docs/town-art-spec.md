# 城镇建筑美术规范（城镇内部地图，3/4 斜俯视）

所有城镇建筑素材的子代理都按这份规范画。素材只放在 `app/static/map-art/town/` 下各自的目录里，**尚未接入游戏**。

## 1. 视角与网格

- **视角**：3/4 斜俯视（俯角约 35°）。看得到屋顶和**正面（朝南、朝屏幕下方）**的立面，侧面只露一窄条或完全不露。不做等距菱形，地面格是**正方形**。
- **光照**：光从左上来。屋顶左坡、立面左侧偏亮；投影落在建筑右下方，一律用半透明暗色平涂（西式 `#3a2c1e` 不透明度 0.18，东方 `#1f3c5b` 不透明度 0.2），不用模糊滤镜。
- **地面格**：48×48 px（`CELL = 48`）。
- **占地**：建筑占地按整格计 `w×d`（宽 × 进深）。民居 1×1 到 2×2；特殊建筑 2×2 到 4×3；城堡部件可更大。
- **高度**：建筑可向上伸出占地矩形之外，最多 3 格（144 px）。
- **symbol 的 viewBox**：`0 0 (w*48) (d*48 + 上伸像素)`。占地矩形位于 viewBox 底部，即占地区从 `y = 上伸像素` 到底边。
- **锚点**：占地矩形**前沿中点**（底边中点），即 viewBox 坐标 `(w*24, 高度)`。放置时把锚点对齐到地块前沿中点。
- **深度排序**：渲染时按锚点 y 从小到大画（后排先画），同 y 按 x。所以建筑不能画出自己占地矩形的前沿（底边）以下，投影除外，投影最多下伸 6 px。

## 2. 画风与配色

### 西式奇幻（木刻线描 + 羊皮纸淡彩）
与已定稿的迷雾素材 `app/static/map-art/fog-brushes/fog-brushes.js`、`fog-celestial.js` 统一。

| 用途 | 颜色 |
|---|---|
| 墨线 | `#4a3826`（主轮廓 1.6–2 px，细节 0.8–1.2 px，细节线可降不透明度到 0.5） |
| 纸色 / 灰泥墙 | `#efdfb2`、`#e9dcc0` |
| 淡彩黄 / 木料 | `#e3c47a`、`#c9a46a` |
| 暖灰褐（石、阴面） | `#cfc0a2`、`#bfb093`、`#b1a287` |
| 木筋 / 深木 | `#8a6a44`、`#6b4f32` |
| 红瓦 / 旗帜红 | `#b5654a`、`#9a3b2a` |
| 青石板瓦 | `#7d8790`、`#5f6870` |
| 茅草 | `#d2b46c`、`#b8954e` |
| 草地底色（只用于预览） | `#c9c79a` |

画法：不透明平涂 + 墨线勾边；明暗只靠平涂色块和少量短排线（屋顶瓦行、石缝、木纹），不用渐变、不用高光、不用模糊。

### 东方玄幻（国潮平涂 + 金线勾边）
与 `app/static/map-art/fog-brushes/fog-xiangyun.js` 的 `PAL` 统一。

| 用途 | 颜色 |
|---|---|
| 勾边金线 | `#c98f3c`（主轮廓）、`#f3c46a`（深色块上的勾线） |
| 米白墙 | `#f1dcae`、`#fbf0d4` |
| 赭黄 | `#eeb24f` |
| 橘红 / 朱红（柱、门、栏） | `#e47c36`、`#cd5030` |
| 赭褐（木、阴面） | `#8c3d22` |
| 青绿（瓦、彩画） | `#2e938d`、`#6cc1b3` |
| 藏青（瓦、深色屋顶） | `#1f3c5b`、`#30697f` |
| 灰瓦 | `#5d6670`、`#7b8590` |
| 草地底色（只用于预览） | `#d9c58f` |

画法：不透明平涂；轮廓用金线；屋脊、檐角起翘；瓦面用平行瓦垄线；局部可用一两圈"叠晕"（同色由深到浅缩一圈）。不用渐变、不用模糊。

## 3. 文件与交付格式

每个子代理目录内：

```
<dir>/
  build.js          node 运行，生成 sprite.svg 与 meta.json（纯程序化手写路径，不读任何外部图片）
  <dir>.js          形状生成函数（浏览器挂 window.TownArt_<dirCamel>，Node 用 module.exports）
  sprite.svg        生成产物：一个 <svg> 里若干 <symbol>
  meta.json         生成产物：元数据数组
  preview.html      离线预览（file:// 可开，直接 <script src> 引 .js 现场生成，或 <object>/内联 sprite）
  README.md         清单 + 已知问题
```

- **symbol id 命名**：`<style>-<race>-<kind>-<variant>`，全部小写、连字符。
  - style：`west` / `east`
  - race：`common`（无种族）/ `elf` / `dwarf` / `orc`
  - 例：`west-common-house-03`、`east-common-forge-01`、`west-common-wall-0b1010`
- 每个 symbol 内部用到的 `id`（clipPath 等）必须带 symbol id 前缀，全目录唯一。
- 所有随机都由种子派生（mulberry32），同一种子画出来完全一样。

### meta.json 每项

```json
{
  "id": "west-common-house-03",
  "style": "west",
  "race": "common",
  "category": "house | special | road | wall | castle | prop",
  "kind": "house_timber",
  "facility": "forge",
  "variant": 3,
  "footprint": [2, 1],
  "height_px": 70,
  "anchor": [48, 118],
  "viewBox": [0, 0, 96, 118],
  "tags": ["two_storey", "shop"],
  "roof": "gable_tile",
  "note": "可选说明"
}
```

- `facility`：对应 `app/town_schema.py` 里 `FacilityKind` 的取值（见第 5 节）。民居和瓦片填 `null`。
- `roof`：尽量对应 `RoofId`：`flat_mud`、`gable_thatch`、`gable_tile`、`steep_slate`、`hip_tile`、`monopitch`、`none`。对不上的写最近的一个并在 note 里说明。

## 4. 双网格瓦片（道路、城墙）

- **逻辑格**：每个 48×48 地面格记录一个布尔值（是不是路 / 是不是墙）。
- **渲染格**：与逻辑格错开半格。每个渲染瓦片 48×48，它的四个角正好落在四个逻辑格中心，按四角状态选瓦片。
- **四角编码**：`mask = NW*8 + NE*4 + SW*2 + SE*1`（1 = 该角是路/墙）。id 后缀写成 4 位二进制，例：`west-common-road-dirt-1100`（北边两角是路）。
- **数量**：每种材质 16 张（0000–1111），0000 是空瓦片可以只给透明占位。
- 斜俯视下城墙的正面、侧面不能靠旋转得到，所以城墙 16 种全画；道路也 16 种全画，不用旋转。
- **道路**：三档 `dirt`（土路）、`stone`（石板路）、`highway`（官道/青石大道）。
  - 路面与非路面的分界线落在**逻辑格的边界**上。渲染瓦片的每条边连接两个角；若两角一个是路一个不是，分界线**必须正好穿过这条边的中点（24 px 处），并垂直于这条边**；分界线在瓦片内部可以有手绘起伏，但在边上的位置和方向固定，这样相邻瓦片一定能接上。
  - 两角都是路的边：整条边都是路面；两角都不是的边：整条边都不是路面。
  - 路面纹理（石板缝、车辙）按世界坐标对齐或在瓦片边上保持周期一致，避免接缝处错开。
  - 一条单格宽的路因此宽 48 px；对角相邻的两种对角组合（1001、0110）画成两块互不相连的角，不要连通。
- **城墙**：一种城墙一套 16 张；墙体有高度，向上伸出（viewBox 高度按需，锚点仍是瓦片底边中点）。墙顶有垛口。另加叠加件：`gate`（城门，放在直段墙上，分东西向墙段 `gate-h` 与南北向墙段 `gate-v` 两种）、`tower`（角楼/塔楼，放在拐角或端点）。
- 预览页必须拼一小段验证拼接：一个 L 形 + 一个十字路口 + 一段带城门的方形城墙。

## 5. FacilityKind 对照

`app/town_schema.py` 里的 28 种：

`town_hall, lord_hall, market_hall, granary, cistern, well, mill, forge, smelter, kiln, tannery, barracks, watchtower, city_wall, gate, temple, academy, infirmary, inn, caravanserai, stable, dock, warehouse, mine_head, boiler_house, ward_tower, cemetery, bridge`

- `city_wall`、`gate` 由城墙瓦片与叠加件承担，meta 里写对应 facility。
- 露天菜市场的摊位用 `facility: "market_hall"` 并在 tags 里加 `open_air`。
- 没有直接对应的建筑（例如风车属于 `mill`）在 note 写明。
- 尽量每种 FacilityKind 至少一个建筑，实在对不上的在 README 列出。

## 6. 自检（每个子代理交付前必须做）

1. `node --check` 所有 JS。
2. `node build.js` 生成 sprite 与 meta，XML 能解析，symbol id 全目录唯一，meta 每项都有对应 symbol。
3. 用 Playwright + 本机 Edge 截预览页（脚本写在 `temp://scratch/`），**亲眼看截图**，按截图至少修改一轮。读不到图就如实说"未能目视确认"，不许编造画面。
4. 页面 pageerror / console error 为 0。

截图方法：

```js
const { createRequire } = require('module');
const req = createRequire('D:/codexwork/织梦/external/civ-atlas/package.json');
const { chromium } = req('playwright');
const b = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true });
```

## 7. 边界

- 只写自己的目录；不改 `map-fog.js`、`play-ui.js`、`towns.py`、`town_schema.py` 等正式代码，不碰别的子代理目录。
- 不执行 git stash / reset / commit；不启停 8000 服务；不安装依赖。
- 原创手绘路径，不复制、不描摹任何游戏或网络图片。

## 8. 参考资料（用户已允许）

- 可以用 `vantaloom_search` 查建筑的真实形制作参考：百科一律用**百度百科**（`vantaloom_search` mode=read 读 `https://baike.baidu.com/item/<词条>`），也可以 search 找其他资料。
- 参考只用来弄清结构和比例（例如徽派马头墙的阶数、卡拉克船式木筋墙的排布、鼓楼的檐层数），画出来的仍是原创程序化路径。
- 质量优先：每个建筑要有可辨认的特征部件（铁匠铺的烟囱与铁砧、钟鼓楼的鼓、磨坊的水轮），不能只是换颜色的同一个方盒子。


## 9. 第二批补充：水面、地面、防御工事

- 新增 meta `category`：`water`（水面双网格瓦片）、`ground`（地面底纹与地面双网格）、`fort`（棱堡、星堡等防御工事部件）。地面小摆件仍用 `prop`。
- **水面瓦片**：规则同第 4 节道路，四角编码 `NW*8+NE*4+SW*2+SE*1`，水岸分界线过瓦片边中点并垂直于边。水面是地面层，不向上伸出；岸边可以向下画出岸壁（属于投影范围，最多 6 px）。
- **水色必须统一**：水面颜色要和已有的码头、桥（`special-infra/`、`west-special/` 的 watermill、`east-special/` 的荷花池）里的水色对齐，接缝处看不出两种水。
- **地面底纹**：可平铺的 48×48 底纹至少 4 种变体，任意排列都无缝；地面双网格（踩实的土地、院坪等）规则同道路。
- **地面摆件**：占地 1×1 或更小，锚点在脚底中点，上伸不超过 48 px。种族专属摆件用对应的 race 值（elf / dwarf / orc）。


## 10. 种族归类（用户已确认）

- 西式（`style: west`）和东方（`style: east`）都是**人族**建筑的两种文化风格。现有 id 里的 `race: common` 就是人族，不改 id；生成系统里 `race = human` 与 `common` 等价。
- 精灵 / 矮人 / 兽人（`elf` / `dwarf` / `orc`）只有西式底子，东方不出三族变种。

## 11. 不规则城墙：辐条（spoke）画法

双网格只能画横平竖直的墙。不规则城墙（任意多边形、星堡尖角）改用**辐条**：

- 城墙走在**逻辑格中心**连成的折线上，相邻两个墙格只能是 8 邻接之一，所以墙段方向只有 8 种：N、NE、E、SE、S、SW、W、NW（正交与 45° 斜向）。
- 每个墙格画：一个**墙节点** `wallnode`（墙格中心的墩子 / 拐点）+ 朝每个相连邻格方向的**半段墙** `wallspoke-<dir>`。半段墙从格中心画到格边中点（正交）或格角（斜向），**完全落在本格 48×48 之内**；邻格画另一半，在格边中点或格角对接。
- 每个 spoke / node 都是 1×1 的 symbol，锚点仍是本格前沿中点；墙体向上伸出，墙厚（垂直于墙段方向）与同风格的双网格城墙一致，斜段也一样厚。
- **同一格内的绘制顺序**（排序键 = 本格前沿 y + 下面的偏移）：`n`、`ne`、`nw` 先画（+0.1），`node` 次之（+0.2），`e`、`w`（+0.3），`s`、`se`、`sw` 最后（+0.4）。斜段对接处（格角）两边墙顶的走道、垛口必须连续。
- 命名：`<style>-<race>-wallspoke-<dir>`、`<style>-<race>-wallnode`（可多个变体加 `-NN`），`category: "wall"`，`facility: "city_wall"`。
- **城门只放在正交直段上**（`gate-h` 用在 E-W 直段，`gate-v` 用在 N-S 直段），沿用已有城门；生成系统保证城门不落在斜段或拐点上。
- 角楼 / 塔楼放在墙节点上，可替代 `wallnode`。

## 12. 防御工事（`category: "fort"`）

- **棱堡**（bastion）：五边形尖角堡，占地 3×3 或 4×4，尖角朝外。要画 8 个朝向（N、NE、E、SE、S、SW、W、NW 尖角朝向），两侧侧翼接上相邻幕墙的辐条。
- **星堡**：由棱堡 + 斜向幕墙拼出；另交一个整体的小星堡 symbol（6×6 左右）作地标用。
- **半月堡 / 三角堡**（ravelin）：放在城门外护城河里的三角小堡，至少 N、S、E、W 四个朝向。
- 东方对应形制：马面（墙外凸出的墩台）、瓮城（城门外的半圆或方形小城）、敌楼、箭楼、角楼、月城。朝向要求同上。
- 锚点、排序、上伸上限（144 px）同第 1 节。

## 13. 文化地标建筑（`category: "landmark"`）

- 每座城镇可以出现少量文化上独特的大型建筑。占地可到 6×6，上伸可到 **240 px**（地标例外，其他类别仍是 144 px）。
- meta 加 `"culture"`（例如 `roman`、`gothic`、`romanesque`、`buddhist`、`taoist`、`confucian`）。`facility` 能对上就填（修道院、教堂填 `temple`，书院文庙填 `academy`），对不上填 `null` 并写 note。
- 用户给的参考照片在 `artifacts/town-art/ref/`：霍亨索伦城堡、新天鹅堡、圣米歇尔山。只用来理解形制（山顶城堡层层叠叠的塔楼与尖顶、修道院岛山下民居、山上教堂），画的仍是原创程序化路径，不描摹照片。


## 14. 资源点（`category: "site"`）

资源点是城镇之外的**独立地点**（伐木场、矿山、采石场等），玩家可以前往。每个资源点有自己的小地图，所以素材分两层：

- **主体建筑**（`category: "site"`）：资源点的核心构筑物，占地 2×2 到 5×4，上伸 ≤ 144 px。例：伐木场的锯木棚与原木堆、矿山的井架与矿道口、采石场的阶梯采面与吊杆。
- **配套摆件**（`category: "prop"`，id 里带资源类型）：原木垛、矿车、碎石堆、晒盐池格、网架等，1×1，上伸 ≤ 48 px。
- **专用地面**（`category: "ground"`）：采石场裸岩、矿渣地、盐田水格、伐木后的树桩地等，可平铺底纹或双网格，规则同第 9 节。

meta 加 `"resource"`：对应 `app/town_schema.py` 的 `ResourceCandidate.kind`（grain、timber、stone、clay、iron、copper、tin、coal、salt、livestock、fish、herb、wool、gold、rare_metals、reed），或 `manifest.json` 的 `trade_kinds`（silver、gems、marble、sulfur、spices、silk、horses、ivory、amber、pearls、wine、dye、mana、dragonbone）。`facility` 能对上就填（矿井 `mine_head`、冶炼 `smelter`、窑 `kiln`、马厩 `stable` 等），对不上填 `null`。

id 例：`west-common-site-lumber-01`、`east-common-site-saltfield-01`、`west-common-prop-logpile-01`。

每个目录的预览页要为每种资源拼一个**资源点示意小地图**（约 10×8 格）：主体 + 摆件 + 专用地面 + 一条通往外面的土路。


## 15. 阿拉伯风格（`style: "arab"`，人族第三种文化风格）

- 与 west / east 并列，都是人族建筑；`race` 一律 `common`，不出精灵 / 矮人 / 兽人变种。
- 画法：细墨线勾边 + 不透明平涂（接近波斯细密画的平面感），不用渐变、不用模糊。装饰靠几何纹瓷砖带、尖拱 / 马蹄拱、木格窗（mashrabiya）、雉堞，不靠明暗。
- 形制特征：平顶屋面（可上人，带矮女儿墙）、穹顶、宣礼塔、风塔（barjeel）、内院、厚土坯墙、小窗、遮阳布棚、拱廊。
- 色板：

| 用途 | 颜色 |
|---|---|
| 墨线 | `#4a3020`（主轮廓 1.6–2 px，细节 0.8–1.2 px） |
| 石灰白墙 | `#f2ead8`、`#e8dcc2` |
| 土坯 / 夯土 | `#d9b98a`、`#c79d66`、`#a97f4c`（阴面） |
| 沙色 | `#e6cf9e` |
| 绿松石 / 青瓷砖 | `#3a9fa8`、`#7cc6c2` |
| 钴蓝瓷砖 | `#24467a`、`#3d64a0` |
| 金饰（穹顶尖、灯） | `#c9a046` |
| 赭红（门、布棚） | `#a8502e`、`#c86b3c` |
| 椰枣绿 | `#5f7a3a`、`#86a052` |
| 投影 | `#4a3020` 不透明度 0.18 |
| 地面底色（只用于预览） | `#e3cf9f` |

- 水面颜色与 `west-ground` 的水色 `#a9b8ad` 对齐（绿洲、蓄水池、水渠同一种水）。
- id 例：`arab-common-house-courtyard-01`、`arab-common-mosque-01`、`arab-common-wall-1100`、`arab-common-wallspoke-ne`。


## 16. 资源点第二批：缺口补齐、农牧细分、青金石

### 16.1 新增 resource 值
- `lapis`（青金石）：新加的贸易品，和 `manifest.json` 的 `trade_kinds` 同级。
- 其余仍用第 14 节的取值。

### 16.2 meta 新增 `subtype`
同一种 resource 下按经营方式细分，用 `subtype` 区分（小写下划线）。农牧类必须填：

| resource | subtype（至少这些） |
|---|---|
| grain | `wheat_farm` 麦田农庄、`rice_paddy` 水稻田、`millet_farm` 粟黍旱田、`vegetable_farm` 菜园、`orchard` 果园、`olive_grove` 橄榄园、`flax_farm` 亚麻 / 麻田、`cotton_farm` 棉田 |
| livestock | `cattle_ranch` 牛场、`dairy_farm` 奶牛场、`pig_farm` 猪圈、`goat_farm` 山羊场、`poultry_farm` 鸡鸭场、`apiary` 养蜂场 |
| wool | `sheep_station` 羊场（与剪毛棚配套） |
| horses | `horse_stud` 种马场 |

非农牧资源可以不填 `subtype`，或填形制（例如 `open_pit` 露天、`shaft` 竖井、`adit` 平硐）。

### 16.3 目录
第二批写新目录 `west-site-2/`、`east-site-2/`，不改 `west-site/`、`east-site/`。规则、预览小地图要求同第 14 节。
