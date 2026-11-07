# east-landmark · 东方玄幻（人族）文化地标

城镇内部地图（3/4 斜俯视，48 px 一格）用的大型文化地标，规范见 `docs/town-art-spec.md` 第 1–6、13 节。style = east，race = common，category = landmark。**美术素材，尚未接入游戏。**

## 文件

| 文件 | 说明 |
|---|---|
| `lm-core.js` | 公共画法（屋顶、立面、台基、院墙、树、烟……），由 `east-special/core.js` 原样复制，只改全局名 `TownArtEastLandmarkCore`，保证画风一致 |
| `lm-parts.js` | 宗教部件（香炉、太极、八卦坛、钟鼓楼、山门、长幡、宝葫芦、塔刹、抱鼓石），由 `east-special/religion.js` 复制并去掉建筑定义 |
| `lm-extra.js` | 地标专用部件：斗拱带、带斗拱的单 / 重檐殿堂、汉白玉须弥座与栏杆、御路台阶、石狮、碑与碑亭、水池荷花、拱桥、祥云、青绿山石、松、柏、平座回廊、多层楼阁（可八角） |
| `lm-taoist.js` | 大型道观、山顶道观（另导出 `crag`、`crane`） |
| `lm-buddhist.js` | 大型佛寺、楼阁式木塔、密檐砖塔、喇嘛白塔 |
| `lm-civic.js` | 文庙、名楼、宫城正殿 |
| `lm-fantasy.js` | 浮空仙阁 |
| `east-landmark.js` | 汇总入口：浏览器 `window.TownArt_eastLandmark`，Node `module.exports`；`list() / symbol(id) / symbolSvg(id) / spriteSvg()` |
| `build.js` | `node build.js` 生成 `sprite.svg`、`meta.json` 并自检 |
| `preview.html` + `preview-scene.js` | 离线预览：图册（0.6 倍缩略，点击 1.5 倍大图）+ 城镇一角示意场景（只读引用 `east-base`、`east-special` 的 js，按锚点 y 排序绘制） |

浏览器引入顺序：`lm-core → lm-parts → lm-extra → lm-taoist → lm-buddhist → lm-civic → lm-fantasy → east-landmark`。

## 清单

| id | 名称 | culture | 占地 | 上伸 px | facility |
|---|---|---|---|---|---|
| east-common-taoist-temple-01 | 大型道观（三清宫） | taoist | 5×6 | 56 | temple |
| east-common-taoist-temple-02 | 山顶道观（仙山宫观） | taoist | 5×5 | 240 | temple |
| east-common-buddhist-temple-01 | 大型佛寺（丛林） | buddhist | 6×6 | 32 | temple |
| east-common-pagoda-01 | 楼阁式木塔 | buddhist | 3×3 | 132 | temple |
| east-common-pagoda-02 | 密檐砖塔 | buddhist | 2×2 | 160 | temple |
| east-common-pagoda-03 | 喇嘛白塔（覆钵式） | buddhist | 3×3 | 94 | temple |
| east-common-confucian-temple-01 | 文庙（孔庙） | confucian | 5×6 | 24 | academy |
| east-common-famous-tower-01 | 名楼（临江高阁） | chinese_classical | 4×4 | 84 | watchtower |
| east-common-palace-hall-01 | 宫城正殿（王府大殿） | chinese_imperial | 6×5 | 44 | lord_hall |
| east-common-floating-pavilion-01 | 浮空仙阁 | taoist | 3×3 | 180 | null |

上伸值按浏览器实测图形顶边收紧过（留约 5 px），不再有大片空白。

## 已知问题 / 说明

- **culture 取值**：规范例子里没有名楼和宫殿对应的值，名楼填 `chinese_classical`，宫城正殿填 `chinese_imperial`。接入时如需统一词表请改这两个值。
- **facility**：名楼没有直接对应，按登高望远归 `watchtower`（note 已写明，实际更像文化景观）；浮空仙阁（仙门道场）对不上，填 `null`。
- **roof**：塔的攒尖顶没有 RoofId，按最近的 `hip_tile` 填，木塔 note 已写明；白塔填 `none`。
- **山顶道观、浮空仙阁**的山体 / 云柱高出占地很多，是有意的玄幻造型；浮空仙阁的浮岛整个在占地上空，地面部分只有石台、八卦坛、长幡和云影，生成系统放置时不要在它的占地内放别的建筑。
- **斜俯视进深**：大型院落为了在 6 格进深内放下多进院子，各殿前后距离压缩过，比例偏紧。
- 没画的可选项：石窟寺、宗族祠堂、戏台、牌坊群。
- `lm-core.js`、`lm-parts.js` 是复制件，`east-special` 以后若改了画法不会自动同步。
