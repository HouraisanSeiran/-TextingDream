# west-castle：西式中世纪城堡（城镇内部地图美术，尚未接入游戏）

规范：`docs/town-art-spec.md`。风格 west，race common，3/4 斜俯视，48 px 地面格，光从左上，锚点 = 占地前沿中点。

## 文件

| 文件 | 内容 |
|---|---|
| `core.js` | 公共画笔：配色、mulberry32、石缝、垛口、箭窗、尖拱/半圆拱、门、吊闸、旗、盾徽、带垛方台、圆柱、锥顶、双坡顶、单坡顶、投影 |
| `walls.js` | 双网格瓦片：幕墙 `castlewall`、护城河 `moat`、内院石板 `yard`（各 16 张） |
| `keep.js` | 主楼：方形诺曼式、圆形塔式 |
| `towers.js` | 塔楼（圆/方）、城门楼 `gatehouse-h` / `gatehouse-v`、吊桥（两向 × 放下/收起） |
| `annex.js` | 大厅、礼拜堂、兵营、厨房、粮仓、马厩、铁匠棚、井 |
| `west-castle.js` | 汇总导出：浏览器 `window.TownArt_westCastle`，Node `module.exports`；`entries() / symbol() / sprite() / meta()` |
| `build.js` | `node build.js` 生成 `sprite.svg`、`meta.json` |
| `preview.html` + `preview.js` | 离线预览：示范城堡（双网格真实拼接）+ 全部 symbol 图册（占地虚线格 + 红点锚点） |

浏览器引入顺序：`core.js → walls.js → keep.js → towers.js → annex.js → west-castle.js`。
内部 clipPath id 在生成时用 `__ID__` 占位，`symbol()` 替换成 `<symbol id>-` 前缀，全目录唯一。

## symbol 清单（66 个）

| id | 占地 | facility | 说明 |
|---|---|---|---|
| west-common-keep-01 | 3×3 | lord_hall | 方形主楼：四角小塔、托臂突堞、扶壁、双联拱窗、十字箭窗、二层入口木梯、旗 |
| west-common-keep-02 | 3×3 | lord_hall | 圆形主楼：勒脚、突堞一圈、箭窗、拱门 + 盾徽、楼梯小塔锥顶 + 旗 |
| west-common-greathall-01 | 4×2 | lord_hall | 大厅（tags 含 great_hall）：成对尖拱高窗、阶梯扶壁、门廊、陡坡青石板顶、排烟亭、烟囱 |
| west-common-chapel-01 | 2×3 | temple | 礼拜堂：山墙朝前、玫瑰窗、尖拱门、山尖钟架 + 十字 |
| west-common-castlebarracks-01 | 3×2 | barracks | 兵营：石砌底层 + 半木二层、兵器架、挂盾、红瓦顶 |
| west-common-castlekitchen-01 | 2×2 | null | 厨房：两座大烟囱、送菜窗台、木柴垛、水桶（FacilityKind 无对应） |
| west-common-castlegranary-01 | 2×2 | granary | 粮仓：蘑菇石墩架空、木梯高门、麻袋、茅草顶 |
| west-common-castlestable-01 | 3×1 | stable | 马厩：贴墙单坡披屋，三间厩位、两匹马探头、草料架、水槽 |
| west-common-castleforge-01 | 2×1 | forge | 铁匠棚：贴墙敞口披屋，炉火、风箱、铁砧、淬火桶、穿顶烟囱 |
| west-common-castlewell-01 | 1×1 | well | 井：石井栏、辘轳、小坡顶 |
| west-common-tower-round-01 | 3×3 | watchtower | 圆塔：突堞、箭窗、垛口、青石板锥顶 + 旗；塔心对准中格 |
| west-common-tower-square-01 | 3×3 | watchtower | 方塔：隅石、突堞、十字箭窗、楼梯小塔 + 旗 |
| west-common-gatehouse-h | 3×2 | gate | 东西向墙段城门楼：双 D 形塔夹门、吊闸、突堞箱、链孔、门前坡道 |
| west-common-gatehouse-v | 2×3 | gate | 南北向墙段城门楼：城门朝东，双 D 形塔 |
| west-common-drawbridge-ns-down / -ns-up | 1×2 | bridge | 南北向吊桥（跨 2 格护城河）放下 / 收起 |
| west-common-drawbridge-ew-down / -ew-up | 2×1 | bridge | 东西向吊桥放下 / 收起 |
| west-common-castlewall-0000…1111 | 1×1 | city_wall | 幕墙 16 张：走道高 60 px + 垛 10 px，厚一整格，墙顶走道石板，外立面箭窗与勒脚 |
| west-common-moat-0000…1111 | 1×1 | null | 护城河 16 张：水面低于地面，北岸露石砌驳岸立面，岸顶压顶条石 |
| west-common-yard-0000…1111 | 1×1 | null | 内院石板地 16 张（category road），边缘路缘石 |

各 `-0000` 是透明占位。完整字段见 `meta.json`。

## 拼装约定（preview.js 的示范城堡就按这个拼）

- 双网格：渲染瓦片 (i,j) 四角 = 逻辑格 (i,j)(i+1,j)(i,j+1)(i+1,j+1)，`mask = NW*8+NE*4+SW*2+SE*1`，瓦片左上角画在 `(i*48+24, j*48+24)`。
- 绘制顺序：内院 / 护城河 / 道路瓦片先画；幕墙瓦片、建筑、叠加件按锚点 y、再按 x 排序。
- 塔楼 3×3，左上角 = 墙角格 − (1,1)。
- gate-h 3×2：中列对准门洞格，第 1 行是墙格；墙逻辑格在门洞那 3 格留空，门洞格下铺内院。
- gate-v 2×3：中行对准门洞格，第 1 列是墙格。
- 吊桥 ns 1×2 放在南门外的两格护城河上；ew 2×1 同理。
- 马厩、铁匠棚是单坡披屋，后沿贴**北墙内侧**，开口朝南。贴南墙放会被幕墙挡住。

## 民居复用

预览页只读引用 `../west-base/` 的 js（子代理 ①，没改它的文件）。本次截图时 west-base 已存在，城外拼了它的民居和土路；文件不存在时预览会跳过并在状态栏写明。本目录不画民居。

## 已知问题

- 斜俯视看不到朝东 / 朝西的立面。gatehouse-v 的门洞朝东，所以看不到门洞，只能靠双塔和收起的吊桥认出是城门。
- 圆形部件的椭圆压扁比固定 0.6，和方形部件的 3/4 投影没有严格统一。
- 补充色（水面 `#a9b7a6` 系、洞口 `#4f3c29`、炉火 `#e39a4a`）不在规范色表里，取的是邻近暖灰。
- 厨房 facility 为 null（FacilityKind 没有 kitchen）。
- 为了避免和 `west-special/` 撞名，附属建筑 id 加了 `castle` 前缀（`castlebarracks`、`castlewell` 等）。
