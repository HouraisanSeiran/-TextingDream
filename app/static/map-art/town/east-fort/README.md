# east-fort · 东方玄幻（人族）不规则城墙与防御工事

美术素材，**尚未接入游戏**。style = east，race = common。全部原创程序化路径，`node build.js` 生成 `sprite.svg` 与 `meta.json`。

## 文件

| 文件 | 内容 |
|---|---|
| `core.js` | 共用画笔：east-base 同款砖面 / 垛口 / 女墙 / 海墁（重写，east-base/tiles.js 未导出），斜向立面 `diagFace`、斜向垛墙 `diagPar`、砖墩 `block`、门洞、箭窗 |
| `spoke.js` | 城墙辐条 8 向 + 八角墙墩 45 个变体 |
| `forts.js` | 马面 4 向、敌楼、箭楼、十字脊角楼 |
| `forts-b.js` | 方瓮城 4 向、月城 4 向 |
| `moat.js` | 护城河辐条（岸层 + 水面层两遍） |
| `passfort.js` | 关城地标 |
| `east-fort.js` | 汇总入口（浏览器 `window.TownArt_eastFort`，Node `module.exports`） |
| `preview.html` / `preview-scenes.js` | 图册 + 场景 a / b / c |

浏览器加载顺序：`../east-base/east-core.js` → `../east-base/houses-a.js` →（预览用 `../east-base/tiles.js`）→ core → spoke → forts → forts-b → moat → passfort → east-fort。

## 清单（87 个 symbol）

| id | 占地 | facility | 说明 |
|---|---|---|---|
| `east-common-wallspoke-{n,ne,e,se,s,sw,w,nw}` | 1×1 | city_wall | 半段墙，category=wall |
| `east-common-wallnode`、`-02` … `-45` | 1×1 | city_wall | 八角墙墩，按露边组合选 |
| `east-common-mamian-{s,e,w}` | 1×1 | watchtower | 马面，category=fort |
| `east-common-mamian-n` | 1×2 | watchtower | 前排那格是墙格 |
| `east-common-dilou-01` | 1×1 | watchtower | 敌楼：砖楼两层箭窗 + 垛口 + 攒尖楼橹 |
| `east-common-jianlou-01` | 1×1 | watchtower | 箭楼：重檐歇山，正面 4×4 箭窗 |
| `east-common-cornertower-01` | 1×1 | watchtower | 十字脊角楼（青绿琉璃） |
| `east-common-wengcheng-square-{n,s}` / `-{e,w}` | 3×2 / 2×3 | gate | 方瓮城 |
| `east-common-wengcheng-moon-{n,s}` / `-{e,w}` | 3×2 / 2×3 | gate | 月城（半椭圆） |
| `east-common-moatbank-{8 向}`、`-node` | 1×1 | null | 护城河岸，category=water，draw_pass 0 |
| `east-common-moatspoke-{8 向}`、`east-common-moatnode` | 1×1 | null | 护城河水面，category=water，draw_pass 1 |
| `east-common-passfort-01` | 6×4 | gate | 关城，category=landmark，上伸 176 |

## 拼接规则

- **墙格**：每个墙格画本格所有方向的 `wallspoke-<dir>` + 一个墙墩。墙墩 id 用 `TownArtFort_spoke.nodeId(本格辐条方向数组)` 取。规则是八角墩的边 i 露出，当且仅当方向 i-1、i、i+1 都没有辐条。方向顺序为 n ne e se s sw w nw，可能的组合共 45 种。
- **同格排序偏移**（规范第 11 节）：n/ne/nw +0.1，node +0.2，e/w +0.3，s/se/sw +0.4。
- **敌楼 / 箭楼 / 角楼**：叠在墙墩上，墙墩照画，偏移 +0.45。
- **马面**：放在墙格外侧相邻格（s / e / w）。`mamian-n` 的占地左前角对齐墙格本身。
- **瓮城 / 月城**：s 向的占地左前角在 gate-h 所在三格正南。n 向在正北两行。e / w 向在 gate-v 那格的东 / 西侧，向南错一格居中，见预览场景 b。
- **城门**沿用 east-base 的 `east-common-wall-gate-h` / `gate-v`，只放正交直段。
- **护城河**：先画全部 `moatbank-*`（含 node），再画全部 `moatspoke-*` / `moatnode`，两遍都在立体物之前。水色 `#6cc1b3` 同 east-ground。

## 已知问题

- 斜向辐条是满厚 36 的 45° 带子，在格角两侧各伸出本格约 12.7 px。几何上无法完全留在格内，相邻格的斜带会盖住这部分。护城河斜段同理。
- 墙墩变体有 45 个，数量多，但每个都只是八角墩按露边组合裁剪，生成系统只需调用 `nodeId()`。
- 斜墙立面的竖缝周期是 6（正交墙是 8），只保证斜段之间对齐；斜段与正交段在八角墩处对接，砖缝不连续，画面上不明显。
- 瓮城 n / e / w 向的外门在看不见的立面上，只用墙顶门楼示意。
- 关城的山体只是三圈叠晕加皴线，比较简单。
- 马面没有斜墙段专用朝向，只能贴正交墙。
