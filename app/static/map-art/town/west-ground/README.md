# west-ground · 西式水面与地面素材（美术样板，尚未接入游戏）

3/4 斜俯视，木刻线描 + 羊皮纸淡彩，遵守 `docs/town-art-spec.md`（第 3、4、6、9 节）。style = west。

## 文件

| 文件 | 内容 |
|---|---|
| `core.js` | 色板、mulberry32、SVG 基本画笔（`window.TownArtWG_core`） |
| `dual.js` | 双网格公共几何：象限形状、分界线、距离带取点（照 `west-base/tiles.js` 的分界线规则） |
| `water.js` | 水面双网格：自然河岸 bank × 16、石砌码头岸 quay × 16 |
| `ground.js` | 草地底纹 grass-01..04、踩实土地/院坪双网格 dirt × 16 |
| `kit.js` | 摆件零件：圆柱、木桶、方箱、木箱、圆木堆、立柱、叶团、石块、地面投影 |
| `props-a.js` | 植物与石头：草丛、野花丛、灌木、小橡树、小松树、小果树、石块、水洼 |
| `props-b.js` | 货物与车具：木桶堆、木箱、干草堆、木柴堆、手推车、马车、水槽 |
| `props-c.js` | 院落小件：栅栏横/竖/转角、菜畦、晾衣绳、鸡群、路标、长凳、花坛、井台小件、篝火堆 |
| `props-race.js` | 精灵 5 种、矮人 5 种 |
| `props-orc.js` | 兽人 5 种 |
| `west-ground.js` | 汇总，`window.TownArt_westGround`：`symbols()`、`symbolSVG()`、`spriteSVG()`、`byId()` |
| `build.js` | `node build.js` 生成 `sprite.svg`、`meta.json`，并检查 id 格式、唯一、内部 id 前缀、与 `town/` 其他目录不重名 |
| `preview.html` + `preview-scene.js` + `preview-atlas.js` | 离线预览（file:// 可开） |

浏览器引用顺序：core → dual → water → ground → kit → props-a → props-b → props-c → props-race → props-orc → west-ground。

## 清单（110 个 symbol）

- **water（32）**：`west-common-water-bank-0000..1111`（自然河岸：泥岸、芦苇、石子、短波纹）、`west-common-water-quay-0000..1111`（条石压顶、岸壁、系船柱）。0000 为透明占位。
- **ground（20）**：`west-common-ground-grass-01..04`（素 / 草丛 / 碎石 / 野花），`west-common-ground-dirt-0000..1111`（院坪）。
- **prop 通用（42 个，26 种）**：grass-tuft ×3、flower-clump ×2、bush ×3、tree-oak ×2、tree-pine ×2、tree-fruit ×2、rock ×3、puddle、barrel-stack ×3、crate ×3、hay-bale ×2、woodpile ×2、handcart、wagon、trough、fence-h、fence-v、fence-corner、vegetable-bed、clothesline、chickens、signpost、bench、flower-bed、well-bits、campfire。id 形如 `west-common-prop-<kind>-<nn>`。
- **prop elf（6）**：mushroom-ring、moonstone-lamp、flower-arch、mossy-stone、silverleaf-tree ×2。
- **prop dwarf（5）**：ore-heap、minecart、mossy-boulder、iron-ingots、ale-casks。
- **prop orc（5）**：bone-pile、totem-small、fire-pit、stake-row、hide-rack。

中文名、占地、上伸像素见 `meta.json` 的 `name` / `footprint` / `height_px`。

## 规则

- **双网格**：`mask = NW*8 + NE*4 + SW*2 + SE*1`。渲染瓦片左上角 = (i*48-24, j*48-24)，四角 = 逻辑格 (i-1,j-1)(i,j-1)(i-1,j)(i,j) 的中心。分界线过瓦片边中点（24 px）且垂直于边，只在内部起伏。对角组合 1001 / 0110 用更大的中心圆角，画成两块不连通的水 / 土地。
- **水色**：`#a9b8ad`，取自 `special-infra/infra-core.js` 的西式 `WEST.water`（码头 west-common-dock-01、石拱桥用的就是它），波纹同为墨线 0.35 不透明度短横线。
  注意：`west-special/prims.js` 的磨坊/蓄水池用的是 `#8e9a9c`，`west-castle` 护城河 `#a9b7a6`，`west-elf` `#a9b8b2`。后两者和本目录几乎一致；`#8e9a9c` 偏深偏灰，和本目录、码头都对不上，属于 west-special 自身的不统一，本目录没改它。
- **波纹 / 土面纹理**：周期 48 的固定排布，所有瓦片共用，跨边笔画在对边补画，按世界坐标对齐。
- **岸壁**：只在「陆北水南」处向下露出，≤ 6 px（规范第 9 节）。
- **草地底纹**：底色 `#c9c79a`，所有笔触离瓦片边 ≥ 4 px，任意排列无缝；斑块不透明度 0.32–0.38，只做轻微变化。
- **摆件**：占地 1×1，锚点 = 脚底中点 `(24, H)`，上伸 ≤ 48 px（最高的小松树上伸 24 px）。按锚点 y 排序绘制。
- **栅栏拼接**：横段沿 y = -16 贯穿 0..48，竖段沿 x = 24 贯穿整格，转角 = 东段 + 南段，可首尾相接。

## 已知问题

- 码头岸是直角条石，转角只有 6 px 圆角，大港池的外凸角看起来比较硬。
- `west-common-dock-01` 自带的岸壁和本目录码头岸的压顶宽度不同，预览里把码头放在港池北沿时要手动下移约 18 px 才对齐；正式接入时码头地块前沿应落在水格上，需要渲染端约定。
- 摆件在 48 px 下：草丛、野花丛、水洼、鸡群较小，远看只是小色点；铁锭垛、骨堆偏暗小，辨识度一般。
- 木栅栏竖段（fence-v）上伸 10 px，因为竖段要画满一整格进深。
- 草地 4 种变体在大面积铺设时仍能隐约看出草簇的固定排布（每种变体内部位置固定），预览用格坐标哈希挑变体、01 素面占一半来冲淡。
