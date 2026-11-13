# 文明模拟 / 历史生成

第一版骨架。读冻结的 `world-map-product`，在陆地上步进政体，写出编年史。不改地形床面，不跑 Terragenesis，也不把结果接进默认故事包。

2026-11-13：固定世界背景的城镇输入新增 `civilization`，提供背景年该国快照、当前君主／王朝／国祀、当前及历史人物、本国史事。历史人物不充当当前镇民；未模拟的人口明确为未知，不从国家面积推算实测人口。空的旧年份信仰快照不再回退后期记录。文明独立运行仍可输出 `truncated`；背景链路发现史事已达容量上限时拒绝继续补写或发布，提示缩短区间或提高 `max_annals`，避免把缺失记录当完整历史。城镇连接见[城镇生成](town-generation.md)。

## 职责

| 模块 | 做什么 |
|---|---|
| `app/civ_sim/geography.py` | 只读栖居栅格：陆地 / 海洋 / 封闭低地、高程带、粗坡度、到岸距离、河网邻近。可选气温、降水（产品里有才读） |
| `app/civ_sim/config.py` | 文明种子、起止年、政体上限、扩张成本。种子与地形 `world_seed` 分开 |
| `app/civ_sim/engine.py` | 确定性逐年步进：政区占有 +（可选）社会层 |
| `app/civ_sim/society.py` | 王朝、人物、国祀；事件 `dynasty` / `succession` / `appoint` / `faith_adopt` / `convert` |
| `app/civ_sim/catalog.py` | 百科姓名池 + 王朝风格 / 人名用字 / 宗教信仰名 |
| `app/civ_sim/chronicle.py` | 有界编年史 + 每年年末政体快照，可写成 JSON |
| `app/civ_sim/history_bridge.py` | 编年史 → 作者侧候选（含 people / dynasties / religion） |
| `app/civ_sim/run.py`、`tools/run_civ_sim.py` | 读产品目录，把 `manifest.json` 与 `chronicle.json` 写到另一目录 |

「州」是陆地上的粗网格（默认16格一边），不是汇水盆地，也不是球面mesh。海洋与 `closed_below_sea` 不进任何州。编年史中沿用 `roads`／`road_version` 字段的无向边只是占领邻州时记录的连接，不能解释为已建道路；真实地形上的道路候选由下级城镇规划另行生成。首都定在立国那一州，这一版不迁都。

### 社会层（王朝 / 人物 / 宗教）

- **数据**：优先只读百科库。`civ-dynasty-styles`、`civ-given-names`（`--with-civ-lore` 或增量 `import_file`），信仰名来自已有 `religions`（61 条，随 `--with-culture`）。库里有 ≠ 正典，也不等于神迹真实。
- **立国**：抽国号/家族名 → 开朝；抽君主名与称号；抽一国祀；再生成储君与一名廷臣（相/将/祭司）。
- **逐年**：届满或概率继位；小概率篡换新朝；偶发任命；小概率改国祀。
- **灭亡**：王朝结束，在位人物记死亡年。
- **关闭**：`CivSimConfig(society=False)` 回到纯政区战争层。

## 输入 / 输出

输入是 `map_source.load_source('world-map-product', path, expected_identity=...)`。选址与扩张用的是 elevation、status、rivers（以及产品若自带的 `temperature_c` / `precipitation_mm_yr`），不读 PNG。

**姓名**：可选只读复用已有 `artifacts/human-encyclopedia/encyclopedia.sqlite3` 的 `names-asian` / `names-european` 别名池（`app/civ_sim/catalog.py`）。库里有 ≠ 世界正典；不写库。缺库或缺池时回退内置音节。`--require-catalog` 可强制失败。

输出目录与地形目录分开，例如 `artifacts/civ-sim/<运行名>/`：

- `manifest.json`：算法名、地图 identity / schema / world_seed、本次配置、可选 `name_catalog`、编年史哈希。`terrain_modified` 固定为 false
- `chronicle.json`：`annals[]` 为 `{year, kind, polity_a, polity_b, region, road_version, note}`，外加每年 `snapshots`。`provenance.map_identity` 是世界层 identity；`provenance.name_catalog` 记录池来源

同一种子、同一张图、同一配置（含同一姓名池）→ 同一份编年史。起止年跨度最多 2000 年。

示例（仓库根目录，80–120 年一般几秒内结束）：

```text
.venv\Scripts\python.exe tools/run_civ_sim.py ^
    --product artifacts/fast-world/tg-speed-archipelago-1600-20261108 ^
    --identity db09ec0f6a166d311a0055adeee3601868e618f81e7cdc92f28117524fcbc199 ^
    --seed 20261108 --start-year 0 --end-year 120 --name archipelago-demo ^
    --encyclopedia-db artifacts/human-encyclopedia/encyclopedia.sqlite3
```

## 与 civ-atlas、Terragenesis 的边界

- **Terragenesis / 世界层**：只读。不改 `elevation`、`status`、`identity`，不调用地形子进程。
- **civ-atlas**：上游 <https://github.com/guaner-334/civ-atlas> 是 AGPL-3.0-only。本模块只借鉴概念：地图生成与文明推演种子可以分开；编年史按年份、政体、事件种类记录。实现是织梦自己的 Python，不是把 `src/gen/civ/` 或 `history.ts` 翻译过来。
- 没有把 civ-atlas 加进依赖，也没有把上游源码拷进这个包。
- 已有的 `app/civ_atlas_history.py` 仍是「读别人导出的快照」。两边并列，互不替换。

## 和 `world_history_store` 的衔接

`to_history_candidate` 产出 store 可分页的文档（`annals` / `polities` / 首都代理 `settlements`），带诚实的 `field_status`，**kind 仍是** `zhimeng_civ_sim_history_candidate`（不是 civ-atlas 背景）。

作者链：

1. `POST /api/inner/history/civ-sim/previews`（`run_dir` 必须在 `artifacts/civ-sim/`）→ `history_preview`，`source_kind=civ_sim`
2. 既有 `page` / `review` / `commit` → 快照 kind `zhimeng_civ_sim_history_snapshot`
3. 既有 `adopt` → 写入故事包 `mechanics.history`

服务入口：`WorldHistoryService.preview_civ_sim`。若故事包已关联 `world_map_product`，采用时校验 `product_identity` 与编年史 `map_identity` 一致。

## 这一版明确不做

完整家谱树、教派分裂谱系、国旗、球面UI、道路运力、汇水州界、默认故事包自动切换。下级单镇生成已通过固定背景与王国规划接线，不因此增加人口迁移、经济或法术战争模拟。
