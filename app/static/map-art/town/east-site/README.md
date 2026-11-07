# east-site · 东方（人族）资源点素材

国潮平涂 + 金线勾边，3/4 斜俯视，style=east，race=common。**尚未接入游戏。**
规范见 `docs/town-art-spec.md` 第 1–6、9、14 节。水色 `#6cc1b3`，与 `east-ground` 的驳岸水面一致。

## 文件

| 文件 | 内容 |
|---|---|
| `core.js` | 画笔、色板、mulberry32、`make()`（组装 symbol 与 meta），挂 `window.TownArtES_core` |
| `kit.js` / `kit2.js` | 共用部件：棚顶、木柱、原木、树桩、石块、堆、方块、竹筐、坑、梯、轮、水面、竹竿、烟 |
| `sites-wood.js` | 伐木场 timber |
| `sites-stone.js` | 采石场 stone、黏土坑 clay |
| `sites-mine.js` | 铁/铜/锡/金/银/煤矿 |
| `sites-water.js` | 盐场 salt（海盐 + 井盐）、渔场 fish、芦苇荡 reed、珍珠 pearls |
| `sites-farm.js` | 茶园/药圃 herb、花椒 spices、桑蚕 silk、稻田 grain、牧场 livestock/wool、马场 horses、染料 dye |
| `sites-rare.js` | 玉石矿 gems、灵石矿 mana、龙骨坑 dragonbone |
| `east-site.js` | 汇总入口，挂 `window.TownArt_eastSite`；`buildAll()` 返回 `{ items, spriteSvg() }` |
| `build.js` | `node build.js` 生成 `sprite.svg`、`meta.json`，校验 id、facility、resource、尺寸 |
| `preview.html` + `preview-scenes.js` + `scenes.js` | 离线预览：25 张 10×8 格示意小地图 + 按 resource 分组的图册 |

共 117 个 symbol：site 35、prop 56、ground 26。meta 每项多出 `resource` 和 `name`（中文名）两个字段。

## 按资源

- **timber**：锯木棚（3×2）；溜木槽、原木排；树桩地 ×2
- **stone**：凿石崖面（4×3，带吊杆）；石料垛、碎石堆、石料木轮车；碎石地 ×2
- **clay**：取土坑、晾坯场；泥料堆、土坯垛、挑泥担
- **iron / copper / tin / gold / silver / coal**：每种矿有山腹矿洞口（3×2，木支护）、辘轳竖井（2×2），两者 facility=mine_head；矿石筐；一个特征件（铁：焙矿堆，铜：洗矿槽，锡：淘锡簸箕架，金：淘金溜槽，银：炼银小炉，煤：黑煤堆）；矿渣地。矿石色、山岩色和矿脉色按矿种区分。
- **salt**：海盐晒场格 ×3（卤水 / 半结晶 / 结满盐）；盐廪棚（warehouse）；卤井天车（2×2，上伸 140）；熬盐灶棚（boiler_house）；刮盐木耙、卤水桶担、盐包垛
- **fish**：渔家栈桥（3×3，dock）；晒网竹架、鱼篓、鸬鹚竹排；浅水滩 ×2
- **reed**：割苇滩；苇捆、芦苇丛
- **pearls**：采珠渔船；蚌壳堆、晒蚌竹匾
- **herb**：梯田茶垄 ×2（tags 含 tea）、炒茶棚、采茶背篓、茶丛；药田 ×2、晒药棚、晒药竹匾、药碾与药篓
- **spices**：花椒园晒椒场、香料麻袋
- **silk**：蚕房；桑树行、缫丝车、蚕茧箩
- **grain**：水田格 ×3；筒车（mill）、谷仓（granary）；稻草垛、晒谷席
- **livestock / wool**：草场木栏羊圈；草场地 ×2、草料槽、羊群、毛包
- **horses**：马厩（4×2，stable）；拴马桩
- **dye**：蓝靛池；晒布架、染缸、蓼蓝田垄
- **gems**：玉料坑（mine_head）、琢玉棚；玉料堆、解玉砂盆、玉坯木箱
- **mana**：发光灵石矿脉（mine_head）；镇守符箓石柱、灵石晶簇、灵石玉匣；灵脉裸岩 ×2
- **dragonbone**：巨骨发掘坑（4×3）；祭龙香案、龙骨堆、发掘工具架

## 已知问题

- 专用地面（盐田、水田、茶垄、药田）按整格平铺。格边的埂或垄靠底纹自带，没有做双网格过渡，与黄土交界处是直边。
- 草场、矿渣地、碎石地的底色与 east-ground 黄土同色，散斑离边 ≥3 px。但它们和黄土格之间没有过渡，边界只能靠散斑密度区分。
- 预览里的土路是直接画的矩形，没有用 east-base 的 `road-dirt` 双网格瓦片。
- 晒盐格、水田格的水面不带描边，与 east-ground 水面同色，但没有和驳岸瓦片放在一起实拼过。
- 羊、牛、马是很小的侧身剪影，只够认出种类。
- 对不上 FacilityKind 的（伐木、采石、黏土、芦苇、珍珠、茶、药、桑蚕、牧场、染料、琢玉、龙骨）facility 填 null，原因写在 note 里。
