# west-base · 西式民居 + 道路 + 城墙（3/4 斜俯视，尚未接入游戏）

规范：`docs/town-art-spec.md`。生成：`node build.js` → `sprite.svg`、`meta.json`。预览：直接 file:// 打开 `preview.html`。

## 文件

| 文件 | 内容 |
|---|---|
| `common.js` | 公共绘图：配色 `PAL`、墙面材质（灰泥/木筋/毛石/方石/竖板/横板）、屋面（侧坡/四坡/半歇山 `roofSide`、正山墙 `roofFront`、单坡 `roofMono`、圆塔 `roundTower`）、门窗、烟囱、老虎窗、招牌、篱笆、菜畦、外楼梯。`window.TownArtWB_common` |
| `houses-a.js` | 民居 01–05 + 组合工具 `floors / centers / wrow / thatchHem / logs / barrel / pal`。`window.TownArtWB_housesA` |
| `houses-b.js` | 民居 06–10 + `shifted`。`window.TownArtWB_housesB` |
| `houses-c.js` | 民居 11–16。`window.TownArtWB_housesC` |
| `tiles.js` | 道路三档 × 16、城墙 × 16、gate-h / gate-v / tower-round / tower-square。`window.TownArtWB_tiles` |
| `west-base.js` | 汇总导出 `window.TownArt_westBase`（Node: `module.exports`） |
| `preview-demo.js` | 仅预览页：瓦片表 + 双网格拼接演示 |
| `build.js` | 生成 sprite/meta，检查 id 唯一、内部 id 前缀、上伸 ≤ 144 px |

浏览器引用顺序：`common.js → houses-a.js → houses-b.js → houses-c.js → tiles.js → west-base.js`。

## `TownArt_westBase` 导出（供 west-castle 等复用，保持稳定）

- `CELL`(48)、`MAX_UP`(144)、`VARIANTS`(3)、`HOUSE_TYPES`（每项 `{n, kind, name, fp, roof, tags, note, draw(ctx, v)}`）、`common`（即 TownArtWB_common）、`tileMod`
- `houseId(n, i)` → `west-common-house-NN-i`
- `house(n, i)` → `{ id, viewBox, up, body, meta }`（body 已平移到 viewBox 坐标，可直接放进 `<symbol>`）
- `houses()`、`tiles()`、`symbols()`：全部 symbol 记录
- `symbolSVG(rec)`、`spriteSVG(list)`：拼 `<symbol>` / 整个 sprite `<svg>`
- `wrap(id, fp, body, minY, meta)`：把局部坐标（y=0 为占地前沿、向上为负）的片段包成 symbol 记录并补全 meta 的 footprint/height_px/anchor/viewBox

改色复用民居：`T.draw(new common.Ctx(id), { i, flip, pal: { door, shut, plaster } })`，返回局部坐标 SVG 片段，再用 `wrap` 包装。

## 民居（style=west race=common category=house facility=null，每种 3 变体 `-1/-2/-3`，变体 2 左右翻排门窗）

| id 前缀 | 名称 | 占地 | 特征 |
|---|---|---|---|
| house-01 | 茅草小屋 | 1×1 | 一层白灰泥，厚茅草收山顶、毛边檐，石烟囱，上下分扇门 |
| house-02 | 木筋两层屋 | 1×1 | 两层木筋灰泥、上层外挑，红瓦双坡，砖烟囱，铅条窗 |
| house-03 | 毛石农舍 | 2×1 | 一层毛石 + 阁楼老虎窗，青石板陡坡，山墙端大石烟囱，门边柴堆 |
| house-04 | 长屋 | 2×1 | 矮横板墙 + 石勒脚，四坡长茅草顶、屋脊排烟口，畜栏双开大门，木桶 |
| house-05 | 窄高街屋 | 1×1 | 山墙朝街三层：方石底层 + 两层逐层外挑木筋，红瓦陡山墙，挂招牌 |
| house-06 | 方石商住楼 | 2×1 | 两层方石，底层店面拱窗 + 条纹布篷 + 招牌，四坡红瓦，两座烟囱 |
| house-07 | 外楼梯石屋 | 1×2 | 下毛石（畜圈拱门）上竖板，外楼梯通二楼，青石板山墙朝街 |
| house-08 | 塔式小楼 | 1×1 | 三层毛石圆塔、锥形青石板顶 + 旗，塔脚单坡木板披屋 |
| house-09 | 院落农家 | 2×2 | 主屋退后（竖木筋 + 木瓦顶），前院石院墙/篱笆、院门、菜畦、果树、碎石小径 |
| house-10 | 半石半木大宅 | 2×2 | 方石底层 + 外挑木筋二层，半歇山红瓦大顶、两座老虎窗、两座砖烟囱 |
| house-11 | 单坡木板屋 | 1×1 | 竖板墙，单坡木瓦（变体 3 茅草），铁烟管，长凳、雨水桶 |
| house-12 | 双山墙联排 | 2×1 | 两户并肩各自山墙朝街：红瓦木筋 + 青石板灰泥，高低错开 |
| house-13 | 跌级山墙石楼 | 1×2 | 三层方石，佛兰德式五级阶梯山墙，青石板陡顶 |
| house-14 | 谷仓农屋 | 2×1 | 山墙朝街的大茅草谷仓屋，草料门 + 吊杆滑轮，草垛 |
| house-15 | 方石塔宅 | 1×1 | 三层方塔、隅石、射孔窗，金字塔青石板顶 + 风向旗 |
| house-16 | L 形侧翼宅 | 2×2 | 后排灰泥主屋（侧坡）+ 向前伸出的木筋山墙侧翼，拐角小院与井 |

`kind` 见 meta（house_cottage / house_timber / house_stone / house_longhouse / house_townhouse / house_shop / house_stair / house_tower / house_farmyard / house_manor / house_shack / house_row / house_stepgable / house_barn / house_towerhouse / house_lplan）。

## 瓦片（双网格，mask = NW·8 + NE·4 + SW·2 + SE·1，后缀 4 位二进制）

- 道路 `west-common-road-{dirt|stone|highway}-XXXX`，各 16 张，category=road，facility=null。分界线落在逻辑格边界、过边中点且垂直于边；石板/整石按世界坐标对齐（周期整除 48）；1001/0110 两角不连通。0000 为透明占位。
- 城墙 `west-common-wall-XXXX` 16 张，category=wall，facility=city_wall。墙沿逻辑格中心线，厚 24 px、高 40 px，墙顶走道 + 垛口，正面方石错缝按瓦片坐标对齐。
- 叠加件（对齐**逻辑格**而非渲染格，锚点 = 逻辑格前沿中点）：`wall-gate-h`（东西向墙上的城门：门洞、吊闸、突堞、红瓦门楼，facility=gate）、`wall-gate-v`（南北向墙上的城门，facility=gate）、`wall-tower-round`、`wall-tower-square`（facility=watchtower）。
- 叠加件深度排序：取逻辑格底边 + 24.1，盖在所在墙段的渲染瓦片之上（见 `preview-demo.js`）。

## FacilityKind 覆盖

本目录只覆盖 `city_wall`、`gate`、`watchtower`。其余设施由 west-special（特殊建筑）与 west-castle（城堡，`lord_hall` 等）负责。

## 已知问题

- 1×2 山墙朝街的民居（07、13）屋脊沿进深，屋面按 35° 俯角压缩到约 54 px（进深 96 px），上伸 07 为 28–41 px、13 为 31–47 px。全目录最高上伸 74 px（house-05），都在 144 px 以内。
- 每种民居的变体 3 改了轮廓（加披屋 / 车棚 / 雨棚、增减一层、换屋顶形式、加老虎窗或交叉山墙、外烟囱等）；变体 1、2 仍主要是翻排与配色差异。
- 单张城墙瓦片孤立看时投影条显得突兀，拼起来正常。
- 城墙只有一种高度；城门只做了单一形制。
