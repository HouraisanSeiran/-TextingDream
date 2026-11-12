# 由地理 + 百科生成故事包的流程（引擎无关设计）

**2026-11-12 定义更新**：故事包与城镇生成的目标职责以 [故事包定义与层级](story-package-definition.md) 为准。本文保留现有单地区流水线的设计与实现记录；其中城市计划和事件编译仍与背景装配耦合，尚未按新层级拆分。

状态：首轮单地区版本**已实现**（2026-11-05；作者 HTTP 于 2026-11-08 接入，前端面板未接，用法见 `docs/world-package-pipeline-使用说明.md`）。已实现：WorldSource 协议与 RegionSnapshot（`app/world_source.py`）、civ-atlas 适配器（`app/world_source_civ_atlas.py`）、引擎无关流程（挑元素 / 写历史 / 定政治 / 写设定与知识点 / 校验 / 草稿 / 过期判定 / 确认编译，`app/world_package_pipeline.py`）、作者 API（`app/web.py`）、测试 `tests/test_world_package_pipeline.py` 与 `tests/test_world_package_http.py`。未实现：前端面板、多地区、Terragenesis 适配器、河网到地块映射、聚落等级推断。用户决定：
- 先用 civ-atlas 世界做**单一地区**测试；地图引擎以后要换源（见 `docs/terrain-source-adapter.md`，Terragenesis 冻结产品将替代 civ-atlas），所以流程不能绑死 civ-atlas。
- 历史**严格跟模拟走**：AI 只把模拟事件写成叙述，不新增事件、王朝或战争。
- 生成结果一律先存草稿，作者确认后才编译成故事包（与 `app/ai_drafts.py` 同口径）。

## 1. 分层

```
世界引擎（civ-atlas / 以后的新引擎）
        │  只经适配器读
        ▼
WorldSource 适配器 ──► 统一的“地区快照” RegionSnapshot（纯数据、带来源身份）
        ▼
与引擎无关的流程：挑元素 → 写历史 → 定政治 → 写设定与知识点 → 校验 → 草稿
```

流程代码只认识 `RegionSnapshot`，不 import 任何引擎模块。换引擎时只新写一个适配器。

## 2. WorldSource 适配器接口

| 方法 | 返回 | 说明 |
|---|---|---|
| `identity()` | `{engine, world_id, version, content_hash}` | 写进草稿，用于判定数据是否过期 |
| `list_regions()` | `[{region_id, name, bbox}]` | 可选的测试地区 |
| `region(region_id)` | `RegionSnapshot` | 见下 |
| `capabilities()` | 字段名集合 | 声明能提供哪些字段（如有没有历史、有没有降水） |

缺的数据不猜：适配器没有的字段在快照里标为 `missing`，流程按 `missing` 降级或要求作者补。

## 3. RegionSnapshot

| 字段 | 内容 | civ-atlas 来源 | 新引擎（Terragenesis）预期来源 |
|---|---|---|---|
| `cells` | 地块：海拔、坡度、起伏、距海、温度、降水 | 存档地块 / 高度图取样 | `terrain_source` 点查询；气候层若无则 `missing` |
| `terrains` | 每块的产地判定结果 | `app/terrain_rules.classify_cell` | 同一函数（规则本身与引擎无关） |
| `settlements` | 聚落：名称、等级（hamlet/town/city/capital）、位置 | 城镇记录 | 暂无，`missing`，由作者或后续生成提供 |
| `polities` | 国家：名称、首都、疆域、存续年 | 文明模拟 | 暂无 |
| `events` | 史事：`{event_id, year, kind, actors, text}` | `app/civ_atlas_history.build()` | 暂无 → 历史章节跳过，不让 AI 补写 |
| `source` | `identity()` 的副本 | | |

`event_id` 必须稳定：同一世界同一版本重复读取得到同样的 id，历史叙述按它引用。

## 4. 与引擎无关的各步

1. **挑元素**：按世界设定（类型、`tech:` / `magic:` 档位）和 `terrains` 与元素 `game.terrains` 的交集，给出候选元素清单草稿；越档元素只提示不推荐。作者勾选后用现有元素装配锁定。
2. **写历史**：输入只有 `events`。AI 输出的每段叙述必须带 `event_ids`，校验：引用的 id 都存在；段落里提到的国家、年份能在所引事件里找到。不满足就拒绝。
3. **定政治**：每个 `polity` 匹配一个 `polities.json` 政体模板（`element_ref`），AI 补政府形式、主要势力、相互关系；种族、文化只能取已锁定的元素。
4. **写设定与知识点**：只能引用已锁定元素与已生成历史。
5. **校验与草稿**：复用 `world_setting.validate`、元素装配与 `world_generator` 的编译；草稿记录 `source` 身份，引擎数据变了就提示过期。

## 5. 首轮测试范围

- 引擎：当前登记的 civ-atlas 世界 `989970517e07cd9f27ab0947cd7ad767.civsnap`。
- 范围：一个地区、2–4 个国家。
- 验收：快照能重复生成且结果一致；历史段落全部能追溯到事件 id；推荐元素都满足档位与产地；生成器离线模式下也能走通整条流程。
- 前置：全库科技 / 魔法档位补齐（`python -X utf8 -m tools.catalog_overlay --check --require-tiers` 通过）。
