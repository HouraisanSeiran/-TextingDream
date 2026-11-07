# race-fort：精灵 / 矮人 / 兽人三族不规则城墙与防御工事（西式，美术样板，尚未接入游戏）

`node build.js` 生成 `sprite.svg`、`meta.json`、`preview-refs.js`，并自检（id 唯一、内部 id 带前缀、facility 在 28 种内、与 town/ 其他目录不撞名、上伸上限、XML 标签配对），有错时退出码为 1。
`preview.html` 可以直接用 file:// 打开。

## 文件
- `core.js`：色板（逐项取自三族的 core.js）、mulberry32、SVG 小画笔
- `spoke.js`：辐条几何（规范第 11 节）、通用棱柱 `prism`（顶面上移 + 朝南立面错切贴纹理）
- `elf.js` / `dwarf.js` / `orc.js`：各族的辐条、节点、塔、工事
- `race-fort.js`：入口，挂 `window.TownArt_raceFort`
- `preview-scene.js` / `preview-cfg.js`：拼接引擎和三族场景配置；`preview-refs.js` 是从三族 sprite.svg 只读摘出的城门（生成产物）

## 清单
| 种族 | id | 占地 | facility |
|---|---|---|---|
| 三族各一套 | `west-<race>-wallspoke-{n,ne,e,se,s,sw,w,nw}` | 1×1 | city_wall |
| 三族各一套 | `west-<race>-wallnode-01/02` | 1×1 | city_wall |
| elf | `west-elf-walltower-01` 树冠哨塔（可替代节点） | 1×1 | watchtower |
| elf | `west-elf-vineoutpost-01` 藤木哨台 | 2×2 | watchtower |
| dwarf | `west-dwarf-walltower-01` 八角矮堡塔 | 1×1 | watchtower |
| dwarf | `west-dwarf-mountainfort-01` 嵌山石堡 | 3×3 | barracks |
| orc | `west-orc-walltower-01` 图腾瞭望塔 | 1×1 | watchtower |
| orc | `west-orc-earthwork-{8 个朝向}` 尖桩土垒 | 2×2 | barracks |

同一格内的排序偏移写在 meta 的 `sort_offset` 字段：n/ne/nw 0.1，node 和塔 0.2，e/w 0.3，s/se/sw 0.4。

## 墙体参数（和已有双网格城墙一致）
- 精灵：墙高 34，墙厚 24，编藤周期 12，带银白木桩，叶面墙顶，北沿苔团、南沿垂叶
- 矮人：墙高 44，墙厚 24，巨石层高 11、块长 24、错缝 12，深岩勒脚，走道色 #a8a397，北沿矮垛、南沿厚垛加压顶石
- 兽人：桩高 33，按 DH 起伏，桩距 4，桩宽 4.8（南北向 6.6），两道绳扎，墙段中间挂头骨，角柱带一对短角

## 已知问题 / 未完成
- 斜段辐条的端头按垂直于墙向的切线收口，所以会伸出本格最多约 8.5 px。两格在格角处切线重合，拼起来没有缝。
- **未做**：精灵荆棘棱垒 `west-elf-thornbastion-*`、矮人石棱堡 `west-dwarf-bastion-*`、三族整体要塞地标 `west-<race>-fortress-01`。
- 精灵、矮人场景里各只接了 1 个外凸工事，要求是 2–3 个，因为棱垒还没画。
- 兽人场景用 gate-v 替换瓦片。它原本是双网格瓦片，和辐条墙并排放时门柱位置会略有错位。
- 嵌山石堡和土垒都没有专门的 FacilityKind，暂填 barracks，note 里写明了。
