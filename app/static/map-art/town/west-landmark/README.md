# west-landmark：西式（人族）文化地标

3/4 斜俯视，48 px 网格，木刻线描 + 羊皮纸淡彩，`style=west`、`race=common`、`category=landmark`。按 `docs/town-art-spec.md` 第 1–6、13 节制作。**尚未接入游戏。**

## 文件

| 文件 | 说明 |
|---|---|
| `core.js` | 共用画笔（`window.TownArtWL_core`）：墙、石缝、门窗、拱廊、古典柱、山花、玫瑰窗、各种屋顶、圆锥、圆柱塔、垛口、扶壁、小尖塔、岩石山体、树木、菜畦、烟囱、炊烟 |
| `sacred.js` | 哥特大教堂、罗曼式修道院、山顶岛式修道院 |
| `castles.js` | 两座童话式山顶城堡 |
| `roman.js` | 斗兽场、罗马神庙、引水渠 6 件、公共浴场、凯旋门、广场柱廊 |
| `extra.js` | 意大利式独立钟楼 |
| `west-landmark.js` | 汇总（浏览器 `window.TownArt_westLandmark`，Node `module.exports`）：`list / idOf / dims / symbol / meta / svg / spriteSVG` |
| `build.js` | `node build.js` 生成 `sprite.svg`、`meta.json` 并自检 |
| `sprite.svg` / `meta.json` | 生成产物 |
| `preview.html` + `preview-scene.js` | 离线预览：图册（0.6 倍，点击放大 1.5 倍）、引水渠拼接测试、城镇一角示意场景（只读引用 `../west-base/`、`../west-special/` 的 js） |

## 清单

| id | 中文名 | culture | 占地 | 上伸 | facility |
|---|---|---|---|---|---|
| west-common-cathedral-01 | 哥特大教堂 | gothic | 5×5 | 240 | temple |
| west-common-abbey-01 | 罗曼式修道院 | romanesque | 6×5 | 170 | temple |
| west-common-abbey-02 | 山顶岛式修道院 | gothic | 6×6 | 240 | temple |
| west-common-castle-hill-01 | 白墙童话城堡 | romantic | 6×6 | 240 | lord_hall |
| west-common-castle-hill-02 | 暖石多塔山城 | gothic | 6×6 | 240 | lord_hall |
| west-common-amphitheatre-01 | 圆形斗兽场 | roman | 6×5 | 112 | null |
| west-common-roman-temple-01 | 罗马神庙 | roman | 3×3 | 104 | temple |
| west-common-aqueduct-ew-01 | 引水渠·东西段 | roman | 1×1 | 124 | null |
| west-common-aqueduct-end-w-01 | 引水渠·西端头 | roman | 1×1 | 124 | null |
| west-common-aqueduct-end-e-01 | 引水渠·东端头 | roman | 1×1 | 124 | null |
| west-common-aqueduct-ns-01 | 引水渠·南北段 | roman | 1×1 | 124 | null |
| west-common-aqueduct-end-n-01 | 引水渠·北端头 | roman | 1×1 | 124 | null |
| west-common-aqueduct-end-s-01 | 引水渠·南端头（分水塔） | roman | 1×1 | 124 | null |
| west-common-thermae-01 | 公共浴场 | roman | 4×3 | 110 | cistern |
| west-common-triumphal-arch-01 | 凯旋门 | roman | 3×1 | 120 | null |
| west-common-forum-01 | 广场柱廊 | roman | 5×4 | 96 | market_hall |
| west-common-campanile-01 | 意大利式独立钟楼 | romanesque | 1×1 | 200 | temple |

facility 为 null 的原因都写在 meta 的 `note` 里：FacilityKind 没有剧场 / 竞技场、引水渠、纪念门。浴场取最接近的 `cistern`，广场取 `market_hall`（兼作集市）。

## 引水渠拼接

- 东西段：`end-w` + 若干 `ew` + `end-e` 放在同一行。每格一跨，拱墩中心落在格的左右边上，石缝按 12 px 周期对齐，相邻格之间没有接缝。
- 南北段：`end-n` + 若干 `ns` + `end-s` 放在同一列（渠身在格中线 x 19..29，与东西段同厚、同高）。按锚点 y 排序时南边的格后画，会盖住北边格的南端面。
- 暂无拐角件和十字件：东西段与南北段不能直接转接。

## 规范外补色

`core.js` 的 `C` 里有 `rock #a49678`（岩石暗面）、`leaf #8f9a5c` / `leaf2 #76814b`（植物）、`water #a9b8ad` / `water2 #8fa49a`（与 special-infra 西式水色一致）、`sand #dccb9c`（沙洲、步道）。`roman.js` 另有石灰华 `#e6d6ae`；钟楼砖色用 `#cfae86`；菜畦土色用 `#b9a479`；回廊草地用 `#b3b47c`；炊烟用 `#e6dccb`（与 west-special 相同）；材质 `lead`（铅皮尖顶、穹顶）用 `#8f989c` / `#6f787d`。

## 已知问题

- 两座山顶城堡和岛式修道院的山体、林木、山城民居都画在 symbol 里，占满 6×6；放进城镇时这块地不能再放别的建筑。
- 哥特大教堂的中殿屋顶面积大，青石板色块在缩略图里偏重；侧廊和飞扶壁只露出一窄条。
- 斗兽场是正面看的椭圆，内侧看台环由程序等距生成，没有区分座席分区。
- 南北向引水渠是近似画法：侧面只露 4 px 受光窄条，看不到完整拱券。
- 广场两翼柱廊是顺进深方向的窄条，柱子很细，缩略图里不明显。
- 凯旋门只有 3×1，上伸 120，与大地标相比体量较小，属于有意为之（街口小地标）。
- 规范里「有余力」的大学、修道院葡萄园、巨石阵未做。
