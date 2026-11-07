# arab-base · 阿拉伯风格（人族）民居与基础设施（美术样板，尚未接入游戏）

style = `arab`，race = `common`。按 `docs/town-art-spec.md` 第 1–6、9、11、15 节绘制：3/4 斜俯视，48 px 网格，锚点 = 占地前沿中点，细墨线 `#4a3020` + 不透明平涂，无渐变 / 模糊。

## 文件
- `build.js`：`node build.js` 生成 `sprite.svg`、`meta.json`。它会检查 id 唯一、内部 id 前缀、上伸上限（民居与墙 144 px，摆件 48 px）、facility 取值、NaN。
- `arab-base.js`：汇总入口。浏览器挂 `window.TownArt_arabBase`，Node 用 `module.exports`。
- 形状模块：`core.js`（色板与工具）、`parts.js` / `parts2.js`（体块、平顶女儿墙、阶梯雉堞、尖拱 / 马蹄拱、门、木格窗、瓷砖带、穹顶、椰枣、布棚、风塔）、`kit.js`（内院、水池、拱廊、楼梯、陶罐、晾布）、`houses-a..e.js`、`tiles-road.js`、`tiles-wall.js`、`spoke.js`、`water.js`、`props.js`。
- 预览：`preview.html`（file:// 直接打开），配套 `preview-atlas.js`、`preview-scenes.js`、`preview-scenes2.js`。

## 清单（136 个 symbol）
| 类别 | id | 占地 | facility |
|---|---|---|---|
| 民居 12 种 × 3 变体 | `arab-common-house-<kind>-01..03`，kind = courtyard / mudhut / windtower / mashrabiya / terrace / dome / tower / arcade / tent / barasti / hillside / dovecote | 1×1、2×1、1×2、2×2（见 meta） | null |
| 道路 3 档 × 16 | `arab-common-road-{dirt,stone,tile}-0000..1111` | 1×1 | null |
| 城墙 16 + 叠加件 | `arab-common-wall-0000..1111`、`-wall-gate-h`、`-wall-gate-v`、`-wall-tower` | 1×1 | city_wall / gate / watchtower |
| 辐条墙 | `arab-common-wallspoke-{n,ne,e,se,s,sw,w,nw}`、`arab-common-wallnode-01..03` | 1×1 | city_wall |
| 绿洲水面 16 | `arab-common-water-oasis-0000..1111`（水色 `#a9b8ad`） | 1×1 | null |
| 摆件 | `arab-common-prop-{datepalm,jars,camel}-01..02` | 1×1 | null |

wallnode 的变体：01 用于东西直段，和墙平齐，垛口与 e / w 段对齐；02 用于拐点或斜段，是凸起的八角墩，带瓷砖带和小旗；03 用于南北直段，和墙平齐。墙节点可以用 `wall-tower` 替代。

## 拼接约定
- 双网格编码 `NW*8+NE*4+SW*2+SE*1`，分界线过瓦片边中点并垂直于边。纹理周期整除 48。
- 城墙：墙厚 24 px，墙高 38 px，墙顶两侧有阶梯雉堞。辐条墙的墙厚、墙高和双网格城墙相同，斜段一样厚。
- 辐条排序偏移写在 meta 的 `sort_offset` 里（n/ne/nw +0.1，node +0.2，e/w +0.3，s/se/sw +0.4）。
- 预览里城门和塔楼的排序键是本格前沿 y + 24.5，保证它们画在同格墙瓦片之后。

## 已知问题
- 斜向辐条的端头按垂直于墙向收口，会伸出本格最多 8.5 px（与 race-fort 相同）。
- 穹顶小屋、黑帐篷没有对应的 RoofId，roof 填 `none`；棕榈茅屋的 roof 取最近的 `gable_thatch`。这些都写在 note 里。
- 1×1 民居的立面细节很小，缩放到 1 倍时木格窗的格线和瓷砖纹几乎看不清。
- 南北向墙段的墙顶只画压顶条，没有雉堞，与双网格城墙一致；从正面看雉堞不连续是有意这样画的。
