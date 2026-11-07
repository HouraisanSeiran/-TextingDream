# race-fort-2：三族棱垒 / 棱堡 / 要塞地标（美术样板，尚未接入游戏）

接在 `../race-fort/` 之后补齐的防御工事。按 `docs/town-art-spec.md` 第 1–6、11–13 节画：3/4 斜俯视、48 px 网格、锚点 = 占地前沿中点。`../race-fort/` 没有改动，只读 require 它的 `core.js`、`spoke.js`、`elf.js`、`dwarf.js`、`orc.js`（色板、编藤 / 巨石 / 尖桩画法都直接复用）。

## 文件
| 文件 | 内容 |
|---|---|
| `bastion.js` | 棱垒 / 棱堡公共几何（`TownArtRF2_bastion`）：外形、attach 墙格、凹多边形实体 `solid`、沿边排垛 |
| `elf2.js` | 精灵荆棘棱垒 8 向 + 树冠要塞（`TownArtRF2_elf`） |
| `dwarf2.js` | 矮人石棱堡 8 向 + 阶梯山城（`TownArtRF2_dwarf`） |
| `orc2.js` | 兽人尖桩大寨（`TownArtRF2_orc`） |
| `race-fort-2.js` | 入口（`window.TownArt_raceFort2` / `module.exports`） |
| `build.js` | `node build.js` → `sprite.svg` + `meta.json`，同时做自检 |
| `preview.html`、`preview-scene2.js`、`preview-cfg2.js` | 离线预览：图册 + 三族拼接场景（`RF2_scene`、`RF2_CFG`） |

## symbol 清单（19 个）
| id | 占地 | 上伸 | category | facility |
|---|---|---|---|---|
| `west-elf-thornbastion-{n,ne,e,se,s,sw,w,nw}` | 2×2 | 38–62 | fort | watchtower |
| `west-dwarf-bastion-{n,ne,e,se,s,sw,w,nw}` | 3×3 | 50–80 | fort | watchtower |
| `west-elf-fortress-01` | 6×6 | 180 | landmark（culture elf） | barracks |
| `west-dwarf-fortress-01` | 6×6 | 200 | landmark（culture dwarf） | lord_hall |
| `west-orc-fortress-01` | 6×6 | 70 | landmark（culture orc） | barracks |

## 棱垒 / 棱堡怎么接墙
- 棱垒 / 棱堡会**替换**一段直墙。墙格（meta `attach_cells`，占地内 `[列, 行]`，行 0 = 最北）沿占地的一条边（正交朝向）或一条对角线（斜向朝向）排开。
- 堡体自带一条与同族辐条墙同高、同厚（24）的墙带，两端切在格边中点（正交）或格角（斜向），与相邻格的 `wallspoke-<dir>` 端头重合。meta 里的 `joins_spokes` 写的是接的那对辐条方向，例如尖角朝 n 时为 `w / e`，尖角朝 ne 时为 `nw / se`。
- 放置时，attach 墙格里的辐条和节点全部跳过。棱堡按普通建筑排序（前沿 y + 0.5）。`preview-scene2.js` 会校验 attach 格在墙环上，且该格的辐条方向正好等于 `joins_spokes`。
- 尖角朝哪个方向就是 id 后缀，尖角朝城外。

## 形制
- **荆棘棱垒**：编藤墙带 + 五边形垒身。侧翼和棱面的外缘有一圈外挑的银尖弯刺。顶上两肩各有一丛荆棘，中央是银桩撑起的叶顶小望台。
- **石棱堡**：巨石墙带 + 厚重五边形堡身，比墙高 10。侧翼和棱面开铜铆炮门，棱面刻符文带。尖角有八角铜顶哨亭和红旗，堡内是铜座矮人炮。北沿垛矮、南沿垛厚，与城墙一致。
- **树冠要塞**：荆棘藤墙八角台基；中央古树三层环台，配树屋；左右两株卫树；四道藤桥；活枝拱前门、月光池、银桩灌木。
- **阶梯山城**：后方山体；三层凿山石台逐层后退升高；中轴台阶；底层有符文巨门和守门石像柱；配铜烟囱、台面石屋（锻炉房）、铁砧；顶层是铜坡顶议事厅。roof 取最近的 `gable_tile`。
- **尖桩大寨**：两层夯土台地；外圈尖桩寨墙；前沿双桩塔战帐门楼，门洞上方吊着头骨；上台有酋长大帐和侧帐；另有图腾柱、头骨堆、火塘、战旗。roof 取最近的 `monopitch`。

## 已知问题
- 兽人这批没有新棱堡。预览里兽人墙外挂的是 race-fort 已有的尖桩土垒：它不替换墙格，只是贴着墙外放。
- 斜向棱堡墙带两端切在格角，沿用 race-fort 辐条的切线收口。端头会伸出本格几 px，与 race-fort 的已知问题相同。
- 树冠要塞上伸 180，阶梯山城上伸 200。这两座都画进了占地后半部，深度排序按单个 6×6 建筑处理；城墙北段若贴着要塞后沿，会被要塞的高部压住，这是预期行为。
- 阶梯山城的山体是装饰性背景，不代表地形高度。
