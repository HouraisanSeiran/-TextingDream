# west-elf · 西式精灵族城镇素材（3/4 斜俯视，尚未接入游戏）

规范：`docs/town-art-spec.md`。生成：`node build.js` → `sprite.svg`、`meta.json`。预览：file:// 打开 `preview.html`（可加 `?sc=2.5` 放大图册）。

style=`west`，race=`elf`。画风是西式木刻线描 + 羊皮纸淡彩的精灵变种：不透明平涂 + 墨线 `#4a3826` + 少量短排线，不用渐变、高光、模糊。全部程序化手写路径，随机由 symbol id 派生的 mulberry32 种子决定。本目录不依赖其他子代理目录的代码。

## 文件

| 文件 | 内容 |
|---|---|
| `core.js` | 色板 `P`、种子随机 `Ctx`、基础 SVG 画笔、投影、短排线、平滑曲线。`window.TownArtWE_core` |
| `parts.js` | 长尖叶片、藤蔓、尖弧拱 `archD`、尖拱窗 / 月窗 / 尖拱门、月光石灯柱、藤编栏杆（直线 / 椭圆弧）。`window.TownArtWE_parts` |
| `forms.js` | 银白木 / 月光石 / 树皮墙面，圆屋身 `cyl`，叶舟顶 `roofLeaf`，叶尖山墙 `roofGable`，花瓣穹顶 / 尖塔顶 `cap`，树干 `trunk`、枝 `branch`、树冠 `canopy`，环形平台 `ring`。`window.TownArtWE_forms` |
| `houses-a.js` | 民居 01–04 + 组合工具 `column / ladder / steps / hut / pod / mush`。`window.TownArtWE_housesA` |
| `houses-b.js` | 民居 05–08 + `leafCrown / bridge / flowerBed / pond / twoStorey / pavilion / slimTower`。`window.TownArtWE_housesB` |
| `special-a.js` | 铁匠铺、藤棚市场、叶篷摊位、议事古树殿。`window.TownArtWE_specialA` |
| `special-b.js` | 月神祠、树荫客栈。`window.TownArtWE_specialB` |
| `tiles.js` | 荆棘藤墙双网格 16 张、gate-h、gate-v、树冠哨台。`window.TownArtWE_tiles` |
| `west-elf.js` | 汇总导出 `window.TownArt_westElf`（Node: `module.exports`），API 与 west-base 同形：`symbols() / houses() / specials() / tiles() / wrap() / symbolSVG() / spriteSVG()` |
| `preview-scene.js` | 仅预览页：精灵村落示意 |
| `build.js` | 生成 sprite/meta；检查 id 唯一与命名、内部 id 前缀、上伸 ≤ 144 px、facility 在 28 种内、民居 facility=null、NaN、回读 symbol↔meta 一一对应 |

浏览器引用顺序：`core.js → parts.js → forms.js → houses-a.js → houses-b.js → special-a.js → special-b.js → tiles.js → west-elf.js`。

## 补色（规范西式色板之外）

任务指定：银白木 `#e8e4d4`、浅苔绿 `#a7b48a`、叶绿 `#7f9a5c`、月光石 `#cfd8d6`、暗树皮 `#6b5a44`。
由它们派生的阴面色：`#d8d3c0`、`#c2bca5`（银白木暗面）、`#677f4a`（叶绿暗面）、`#86735a`（树皮受光面）、`#aebbb8`（月光石暗面）、`#a9b8b2`（水面）、`#8f9c72`（苔瓣暗面）；货摊布料一处用了淡紫 `#b7a3c4`。


## 民居（category=house，facility=null，每种 3 变体 `-1/-2/-3`，每个变体都改轮廓）

| id 前缀 | 名称 | 变体（占地） | 特征 |
|---|---|---|---|
| house-01 | 巨树树屋 | 叶尖山墙屋 1×1 / 花瓣圆舱 1×1 / 双层台 1×1 | 树干上环形木台 + 藤编栏杆，台上小屋，绳梯落地，树冠挂月光石珠 |
| house-02 | 树根洞屋 | 活树根洞 1×1 / 树桩苔顶 1×1 / 根拱长洞 2×1 | 门开在树根间，月窗，攀藤开花，月光蘑菇 |
| house-03 | 环形平台屋 | 高脚环台 2×2 / 挑梁高台 2×2 / 地面环台 2×1 | 绕巨树主干的大环台，台上山墙屋 + 圆舱，悬空台阶或绳梯 |
| house-04 | 藤拱小屋 | 门前藤拱 1×1 / 藤拱罩屋 1×1 / 藤拱连廊 2×1 | 两根藤拱成尖弧，挂叶开银白小花 |
| house-05 | 叶顶圆屋 | 单层叶冠 1×1 / 两层叶冠 1×1 / 双圆屋连廊 2×1 | 圆屋身顶上一圈放射长尖叶，顶心卷芽 |
| house-06 | 双层吊桥连屋 | 屋台吊桥 2×1 / 双树台吊桥 2×1 / 前后错台 2×2 | 两处上层之间挂吊桥，桥板、扶手绳、吊索 |
| house-07 | 花园亭屋 | 半敞亭屋 1×1 / 小屋带亭 2×1 / 庭院长屋 2×2 | 花瓣穹顶圆亭，花畦，月光石边小水池，踏石 |
| house-08 | 细塔屋 | 单塔 1×1 / 塔靠小屋 1×1 / 双塔吊桥 2×1 | 细高银白木圆塔、腰箍、内凹尖叶顶，塔腰阳台或吊桥 |

## 特殊建筑 / 道具

| id | 名称 | facility | 占地 | 特征部件 |
|---|---|---|---|---|
| west-elf-forge-01 | 铁匠铺（月光熔炉） | forge | 2×2 | 月光石穹顶熔炉（银箍、月白火苗）、树桩银砧 + 锤、淬火槽、风箱、月光石烟塔冒银烟、叶舟顶作坊 |
| west-elf-market-01 | 藤棚市场 | market_hall | 3×2 | 银白木藤棚架（只有梁和藤，能看见下面）、5 个货摊（果 / 布 / 罐 / 草药）、中央月光石泉、叶幡 |
| west-elf-stall-01 | 叶篷摊位 | market_hall（prop，tags 含 open_air） | 1×1 | 单摊位，苔叶篷 |
| west-elf-townhall-01 | 议事古树殿 | town_hall | 3×3 | 古树主干 + 高处议事环台挂月牙叶幡，尖拱柱廊长殿，正中叶尖山墙门廊，两侧月光石细塔 |
| west-elf-temple-01 | 月神祠 | temple | 2×2 | 两级月光石圆台、环形银白柱廊挂藤、中央尖塔圣坛顶上月牙、月池 |
| west-elf-inn-01 | 树荫客栈 | inn | 2×2 | 两层叶尖山墙客栈 + 屋后树上环台，侧边马棚 |

## 城墙瓦片与叠加件（category=wall）

- `west-elf-wall-0000` … `-1111`（16 张，facility=city_wall）：活体荆棘藤编墙，墙厚 24 px、高 34 px。正面是暗树皮底 + 两组交叉编藤 + 银白小刺 + 苔石勒脚，墙顶叶丛，银白木尖桩代替垛口。编藤周期 12、尖桩周期 24，都整除 48；最南一行小格的正面由下方瓦片负责画，所以拼接处不会重复。0000 是透明占位。
- `west-elf-wall-gate-h`（gate）：东西向墙段城门。尖弧藤拱门洞，藤帘升起一半，两侧银白木门柱挂月光石灯，门上月牙石徽，叶舟顶门楼。
- `west-elf-wall-gate-v`（gate）：南北向墙段城门。两侧敞开的藤编门扇，叶尖山墙门楼。
- `west-elf-wall-tower`（watchtower）：树冠哨台。细树干撑环台，台上叶舟小顶，绳梯。
- 叠加件对齐逻辑格，锚点在逻辑格前沿中点。

## 规范映射说明

- 叶形屋顶没有对应的 RoofId：叶舟顶、叶尖山墙、花瓣穹顶取 `gable_tile`，叶冠取 `gable_thatch`，尖塔顶取 `steep_slate`，藤棚市场为 `none`。每项 note 里都写了。
- 已覆盖的 FacilityKind：town_hall、market_hall、forge、temple、inn、watchtower、city_wall、gate。其余 20 种本目录没画。

## 自检

- `node --check` 全部 JS；`node build.js` 退出码 0（49 个 symbol，最高上伸 130 px）。
- 截图脚本在会话 scratch 目录：校验所有图册卡片的几何包围盒不低于前沿 6 px，并统计 pageerror / console error。最终结果是 0 越界、0 错误。

## 已知问题

- 包围盒检查用的 `getBBox` 不计 clipPath，所以只查上下方向；横向有些部件（叶舟顶两端叶尖、灯钩、蘑菇）会伸出占地左右边几像素，规范没有禁止这一点。
- 藤拱小屋 04 和树桩屋 02-2 上伸很少，在村落里比树屋矮得多。这是有意保持的体量差。
- 铁匠铺、市场、行政厅、神殿、客栈各只有 1 个变体。
- 村落示意只放了城墙南段和西段；L 形接缝和带城门的直墙都验证过，没有拼完整的方形城墙。
