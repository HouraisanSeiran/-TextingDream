# east-ground · 东方玄幻城镇地面层（美术素材，尚未接入游戏）

3/4 斜俯视，国潮平涂 + 金线勾边，遵守 `docs/town-art-spec.md` 第 2、3、4、6、9 节。style=east，race=common。
`node build.js` 生成 `sprite.svg`（95 个 symbol）与 `meta.json`；`preview.html` 可直接用 file:// 打开。

## 文件

| 文件 | 内容 |
|---|---|
| core.js | 色板、画笔、mulberry32、symbol 包装（`TownArtEG_core`） |
| grid.js | 双网格区域几何：round（自然岸）/ square（驳岸、院坪），分界过边中点并垂直于边 |
| water.js | 水纹（周期 48，世界对齐）、岸壁、卵石 / 芦苇 / 菖蒲 / 拴船石 |
| water-tiles.js | bank × 16、quay × 16、驳岸石阶叠加件 2 张 |
| ground.js | 黄土底纹 earth-01..04、青砖院坪 paving × 16 |
| prop-kit.js | 摆件画笔（缸、筐、箱体、树冠、湖石、车轮、叶片） |
| props-plants / props-stone / props-farm / props-yard.js | 摆件定义 |
| props.js | 摆件包装成 symbol + meta |
| east-ground.js | 汇总入口，浏览器挂 `window.TownArt_eastGround`；导出 `buildAll()`、`maskAt(grid, i, j)`、`bits()` |
| build.js | 生成 + 自检（id 唯一、内部 id 带前缀、meta↔symbol、上伸 ≤ 48、与 town/ 其他目录不重复） |
| preview.html / preview-scenes.js | 图册 + 拼接验证 + 示意街区 |

## 水色

水面 `#6cc1b3`、水纹米白 `#fbf0d4`，与 `special-infra/` 东方码头 `east-common-dock-01`、拱桥水面（`EAST.water`）同色。
预览的港池场景把码头直接放在驳岸港池里对色。east-special 荷花池（`#4f8a9a` 叠 `#30697f`）和 east-base 的 `C.water`（青绿混藏青）比它们深，本目录跟的是码头 / 桥。

## symbol 清单

### 水面（category=water，占地 1×1，height_px 0）
- `east-common-water-bank-0000..1111` 自然河岸 16 张：圆弧 / 带起伏直线岸线，湿土带、泥岸壁（只在北岸朝南面露出，≤ 3.2 px）、卵石、芦苇、菖蒲，水面平行短水纹 + 小卷浪。
- `east-common-water-quay-0000..1111` 条石驳岸 16 张：直角岸线（中心抹小圆角），压顶条石（石缝每 12 px）、北岸条石岸壁 8 px（在水面内侧画，不出瓦片）、直段中点拴船石。
- `east-common-water-quay-steps-s` / `-n` 驳岸石阶叠加件：分别盖在 quay-0011（北岸南水）、quay-1100（南岸北水）上。
- mask 1 = 水，`NW*8+NE*4+SW*2+SE*1`；陆地一侧透明，下面铺任何地面都行；1001 / 0110 是两块不连通的水；0000 是透明占位。

### 地面（category=ground，占地 1×1，height_px 0）
- `east-common-ground-earth-01..04` 黄土地面：底色 `#d9c58f`，淡斑、土粒、碎石、零星草丛（草丛只在 03），点缀离边 ≥ 1.5 px，任意排列无缝。
- `east-common-ground-paving-0000..1111` 青砖院坪：12 px 方砖按周期 48 世界对齐，沿边一圈压边条砖 + 金线；mask 1 = 铺地。

### 摆件（category=prop，占地 1×1，锚点 = 格子前沿中点 [24, 48+上伸]）

| id | 中文名 | 上伸 px |
|---|---|---|
| east-common-prop-bamboo-01 / 02 / 03 | 竹丛（中 / 大 / 小） | 23 / 40 / 10 |
| east-common-prop-plantain-01 | 芭蕉 | 2 |
| east-common-prop-plum-01 / 02 | 梅树（红梅 / 白梅） | 20 / 20 |
| east-common-prop-willow-01 / 02 | 柳树（大 / 小） | 17 / 8 |
| east-common-prop-pine-01 / 02 | 松（三层 / 四层） | 4 / 14 |
| east-common-prop-vegbed-01 | 菜畦 | 0 |
| east-common-prop-taihurock-01 / 02 / 03 | 湖石（立 / 卧带小石 / 瘦高） | 0 / 0 / 8 |
| east-common-prop-stonelantern-01 | 石灯笼 | 10 |
| east-common-prop-stonelion-01 / 02 | 小石狮（朝东 / 朝西，成对） | 0 |
| east-common-prop-taipingvat-01 | 太平缸 | 0 |
| east-common-prop-waterjar-01 / 02 | 水缸（陶缸带木瓢桶 / 青釉缸带竹盖） | 0 |
| east-common-prop-stonetable-01 | 石桌石凳 | 0 |
| east-common-prop-hitchingpost-01 | 拴马桩 | 6 |
| east-common-prop-tudishrine-01 | 路边土地庙 | 0 |
| east-common-prop-lanternpost-01 | 灯笼柱 | 21 |
| east-common-prop-bamboobasket-01 / 02 | 竹筐（装菜 / 两只） | 0 |
| east-common-prop-luobasket-01 / 02 | 箩筐（谷 / 棉） | 0 |
| east-common-prop-carrypole-01 | 扁担挑筐 | 0 |
| east-common-prop-wheelbarrow-01 | 独轮车 | 0 |
| east-common-prop-oxcart-01 | 牛车 | 0 |
| east-common-prop-woodpile-01 / 02 | 柴垛（三层 / 两层带柴捆） | 0 |
| east-common-prop-haystack-01 / 02 | 稻草垛（尖顶 / 平顶） | 0 |
| east-common-prop-dryingmat-01 | 晒谷席 | 0 |
| east-common-prop-bamboofence-01 / 02 / 03 | 竹篱笆（横段 / 竖段 / 转角东南） | 0 / 13 / 0 |
| east-common-prop-dryingpole-01 | 晾衣竹竿 | 1 |
| east-common-prop-chickens-01 | 鸡群 | 0 |

共 26 种（kind）41 个 symbol。上伸 = 超出占地格顶（y=-48）的像素，全部 ≤ 48。

## 已知问题

- 底纹只有 4 张、每张点缀固定，14×6 大片随机铺时仍能隐约看出相同的淡斑位置，但已没有明显的格子排列；需要更碎可以再加变体。
- 竹篱笆按格心拼接：横段在 y=-24、竖段在 x=24，转角只给东南一种（其余方向可用横竖段凑，或后续补 3 种转角）。
- 自然岸的岸线是圆弧 + 轻起伏，大片河道看起来比较规整（双网格固有的格子感）。
- 摆件的锚点放在格子前沿中点，实际"脚底"在格内 y≈-14 处；按锚点 y 排序时同格前后关系正确，但若要把摆件挤到格子前沿，需要放置方另算偏移。
- east-special 荷花池、east-base 渔家棚屋的水色比本目录深，放在一起能看出差别（截图里渔家棚屋前一小块深水），需要那两个目录统一或在 meta 里注明。
