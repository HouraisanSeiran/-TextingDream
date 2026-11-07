# 游戏字段规范 game_fields_v1（价格 / 产地 / 季节）

状态：设计口径，供食物、药材、菜品、方剂补字段。**数值是游戏行情估计，不是历史物价考证**；不改变任何条目的 `review_status` / `detail_status`。

## 1. 写在哪里

每个元素加一个顶层对象 `game`，并同步写检索标签。引擎会原样保留 payload，标签可用 `--all-tag` 检索。

```json
"game": {
  "schema": "game_fields_v1",
  "price": {"min": 1, "max": 3, "per": "一升", "tier": "penny"},
  "terrains": ["farmland", "temperate_forest"],
  "seasons": ["autumn"],
  "keeps": "months",
  "sold_by": ["market", "grocer"],
  "note": "一句话说明估价依据或例外（可空字符串）"
}
```

对应标签（必须与 `game` 一致，一个不多一个不少）：

- `price:<tier>` 恰好 1 个
- `terrain:<值>` 每个 terrains 一个
- `season:<值>` 每个 seasons 一个
- `sold_by:<值>` 每个 sold_by 一个

`keeps` 只写在 `game` 里，不做标签。

## 2. 价格（以便士记）

币制沿用工程约定：**12 便士 = 1 先令，20 先令 = 1 镑 = 240 便士**。`min` / `max` 为整数便士（不足 1 便士写 0，并在 tier 用 farthing）。`per` 写计价单位（一杯、一条、一磅、一把、一剂、一份、一只……）。

已有短篇的锚点，估价必须与之不冲突：麦酒一杯 2 便士；渡船 12 便士；半日短工 6–12 便士；一袋干麦 12 便士；桥费 8 便士。

| tier | 区间（按 max 判断） | 图标 |
|---|---|---|
| `farthing` | max < 1 | 法寻（¼ 便士铜币） |
| `penny` | 1–3 | 便士铜币 |
| `groat` | 4–11 | 格罗特（4 便士银币） |
| `shilling` | 12–239 | 先令银币 |
| `pound` | ≥ 240 | 镑金币 |
| `not_for_sale` | 不可合法买卖（受保护物种、违禁、管制） | 禁售封印；min/max 写 null |
| `priceless` | 传说层、无市价 | 无价；min/max 写 null |

tier 由 max 推出，不得自相矛盾。贵重香料、远途进口、药铺成药可以落到 shilling 甚至 pound。

## 3. 产地 terrains（1–3 个）

与 civ-atlas 群落（`external/civ-atlas/src/gen/biomes.ts`）对齐，另加地形与生产用地：

- 群落：`ocean` 海洋、`lake` 湖泊、`tundra` 苔原、`taiga` 针叶林、`cold_desert` 寒漠、`temperate_desert` 温带荒漠、`steppe` 草原、`temperate_forest` 温带森林、`temperate_rainforest` 温带雨林、`hot_desert` 热带荒漠、`savanna` 稀树草原、`tropical_dry_forest` 热带季雨林、`rainforest` 热带雨林、`wetland` 湿地
- 地形：`mountain` 山地、`plateau` 高原（海拔高、顶面平缓的台地，如青藏、安第斯高原；与尖峰山地区分）、`coast` 海岸、`river` 河流
- 生产用地：`farmland` 农田、`orchard` 果园菜圃、`pasture` 牧场、`mine` 矿坑、`workshop` 作坊厨房（加工成品：菜品、成药、酒、酱）、`import` 远途输入（本地不产，只能经商路买到）

原料写自然产地或生产用地；菜品与方剂一般写 `workshop`，再加一个最能代表原料来源的产地。

**地图判定**：`app/terrain_rules.py` 给每个取值规定了怎么从 civ-atlas 高度图 / DEM 判定（`RULES`），供后续地图玩法把地块和元素的 `terrains` 对上：

- 高度图直接判定：`ocean`、`coast`（距海 ≤25 km）、`mountain`（起伏 ≥600 m 或区域坡度 ≥15°）、`plateau`（海拔 ≥1500 m、起伏 <600 m、坡度 <8°）。
- 气候群落：阈值照抄 civ-atlas `classifyBiome`。没有降水数据时只给候选，不定论；没有温度时按纬度和 6.5 ℃/km 递减率估算，并标为估算。
- 需要专门图层：`lake`、`river`、`wetland`，单靠高度图不判。
- 生产用地只判“适宜”，不等于已有田地或矿；`workshop`、`import` 不是地理属性。
- 阈值是本项目设计口径，不是地理学标准分类。

## 4. 季节 seasons

`spring` / `summer` / `autumn` / `winter` / `all_year`。写**当季上市或采收**的季节；耐储存、全年供应的写 `all_year`（不与四季混用）。节令菜写其节令。

## 5. 保存期 keeps

`hours` / `days` / `weeks` / `months` / `years`。

## 6. 谁在卖 sold_by（1–3 个）

`tavern` 酒馆、`inn_kitchen` 客栈伙房、`market` 集市、`grocer` 杂货铺、`butcher` 肉铺、`fishmonger` 鱼贩、`baker` 面包房、`dairy` 乳品铺、`spice_merchant` 香料商、`apothecary` 药铺、`herbalist` 草药采集人、`farmer` 农户直卖、`noble_kitchen` 贵族厨房、`street_vendor` 街头小贩、`none` 不出售（与 not_for_sale / priceless 搭配）。

## 7. 已有分区怎么补（旁挂文件）

已有 13 个食物/药材/菜品文件格式不统一（CRLF/LF、缩进不一），直接改写会产生无法审阅的整文件 diff。所以**已有分区不直接改源 JSON**，而是写旁挂文件：

`docs/element-catalog/game-fields/<group>.json`

```json
{
  "schema": "game_fields_v1",
  "group": "staples",
  "entries": {
    "staples_wheat": {"price": {...}, "terrains": [...], "seasons": [...], "keeps": "...", "sold_by": [...], "note": "..."}
  }
}
```

`entries` 的键必须是该组真实存在的元素 id，且覆盖该组全部元素。`entries` 里不写 `schema`（由合并工具补上）。合并工具 `tools/apply_game_fields.py` 把它写回源 JSON 的 `game` 并加对应标签。

**新建的分区**（如新增中餐、西餐）直接在每个元素里写 `game` 与标签，不用旁挂文件。

## 8. 边界

- 估价是本项目设计数值，`note` 里不要写成史实。
- 不写剂量与医疗用途；药材的价格是“一两/一把药材的柜台价”，方剂是“一剂成药或一包配好的药”的柜台价。
- 不改条目正文、来源与审核状态，只加 `game` 与对应标签。
- 校验：`python -X utf8 -m unittest tests.test_encyclopedia_game_fields`。
