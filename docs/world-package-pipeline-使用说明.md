# 由地理 + 百科生成故事包：使用说明（首轮单地区）

设计稿见 `docs/world-package-pipeline.md`。本文说明已实现的代码怎么用、选地区的规则、数据缺口与换引擎时要补什么。

## 1. 文件

| 文件 | 作用 | 可以 import 引擎模块吗 |
|---|---|---|
| `app/world_source.py` | `WorldSource` 协议、`RegionSnapshot`、稳定 `event_id`（`make_event_id`）、`classify_cells`（封装 `terrain_rules.classify_cell`）、`validate_snapshot`、`identity_matches` | 否 |
| `app/world_source_civ_atlas.py` | civ-atlas 适配器 `CivAtlasSource` | **是（唯一一处）** |
| `app/world_package_pipeline.py` | 与引擎无关的流程 `WorldPackagePipeline` | 否（测试用 AST 扫描保证） |
| `tests/test_world_package_pipeline.py` | 20 个用例 | — |

## 2. 流程与草稿

草稿存在 `service.store` 的 `world_package_draft` 里，确认前不写任何故事包。

```python
from app.world_source_civ_atlas import CivAtlasSource
from app.world_package_pipeline import WorldPackagePipeline

source = CivAtlasSource.from_store(service.store, data_root)   # 或 CivAtlasSource.from_path(path)
pipe = WorldPackagePipeline(service)
d = pipe.propose(source, region_id=None, setting={
        'genres': [{'tag': 'western_fantasy', 'weight': 3}], 'tech': 'medieval', 'magic': 'rare'})
d = pipe.select(d['id'], ['ns/element_id', ...], acknowledge_candidates=True)
d = await pipe.generate(d['id'])            # 写历史 → 定政治 → 写设定与知识点
d = pipe.edit(d['id'], content)            # 可选：作者改写，按同样规则重新校验
pipe.freshness(d['id'], source)            # 引擎数据是否已变
d = pipe.confirm(d['id'], source)          # 过期检查 → 编译 → 写故事包目录
```

1. **propose（挑元素）**：只读元素库。推荐条件为三项同时成立：类型命中设定的 `genre:*`；不越 `tech:` / `magic:` 档（判定复用 `world_setting.conflicts`）；元素 `terrain:*` 里的地理产地与地区产地有交集（没有产地标签的条目视为不受产地约束）。只越档、其余合格的放进 `hinted`，只提示、不推荐。只有作坊 / 远途输入产地的条目不推荐，因为本地产地无从核对。`kind:polity` 不进候选，在“定政治”一步单独处理。这一步还会做政体模板匹配，并按上下文预算挑历史输入事件。
2. **select（勾选）**：只能从候选里选（推荐或越档提示都行）。选完交给 `element_assembly.build_manifest` 锁定，库里的版本与内容在这里核对，须 `acknowledge_candidates=True`。
3. **generate**：模型调用复用 `service.ai_drafts._run`，与 `app/ai_drafts.py` 同口径。离线时用快照确定性生成的示例；在线时至多两次，第二次带上错误；两次都失败抛 `DraftRejected`，草稿不变。
4. **confirm**：比对来源身份（`engine/world_id/version/content_hash`）与地区快照摘要，不一致就拒绝（过期）。之后调 `world_generator.compile_package` 编译，经 `runtime.validate_package`（含 `world_setting.validate`）校验，最后写故事包目录。写法与 `WorldGenerator.save` 同口径，不另造编译。

## 3. 代码层面的校验（不靠提示词自觉）

- **历史**：每段必须带 `event_ids`，且只能引用本次输入的事件。段落里出现的国家名必须是所引事件的参与方。出现的“N年”必须是所引事件的年份。形如“××王国 / 帝国 / 王朝”而引擎里没有的名字一律拒绝。
- **政治**：每个地区内国家给一个 `polities.json` 模板作 `element_ref`，模板须在允许清单内。种族、文化只能取已选元素。
- **设定与知识点**：`element_refs` 只能取已选元素；`event_ids` 只能取历史段落引用过的事件。正文出现候选清单里未选元素的名字也拒绝。
- **政体匹配**：按引擎的 `form_hint` 找同名 `polity:*` 模板，越档的跳过；没有合适的就按 `FORM_FALLBACK` 试相近政体（状态 `fallback`）；都没有时为 `no_template`，由作者处理。

## 4. civ-atlas 适配器：地区选择规则

1. 基准年默认取 `endYear`。政区归属用 `civ_atlas_history.build` 回放到基准年。
2. 每个在基准年有领土的国家 P 出一个候选地区 `civ-polity-<P.id>`。P 的邻国是：与 P 的州在 `regions.adj` 上相邻、且归属其他国家的州所属的国家。邻国按“相邻州对数”降序、国家 id 升序排列，取前 3 个。地区 = P 加这些邻国在基准年的全部州，共 2–4 国。
3. `list_regions()` 按核心国家 id 升序排列；首轮默认取第一项。
4. 事件取窗口 `[基准年−300, 基准年]` 内的 annals，条件是 `a` / `b` 列为国家、且至少一方在地区内。`event_id = 'ev_' + sha256(engine|world_id|version|content_hash|annal/<下标>)[:16]`，同一份数据重复读取结果一致。

首轮实测（`989970517e07….civsnap`，基准年 3000）：共 14 个候选地区；默认地区 `civ-polity-0`“科罗里亚及其邻国”，地区内 2 国：科罗里亚（26 州，lineage=republic）、博加维亚（138 州，realm）。地区有 1156 个地块、143 个聚落、362 条事件。事件涉及的其他国家只作为参与方列出，`in_region=false`。

## 5. 数据缺口（标 `missing`，不猜）

| 项 | civ-atlas 现状 | 处理 |
|---|---|---|
| 河流 `layers.river` | 河网是折线，未映射到地块 | missing；不把 `flux` 当河流判据 |
| 聚落等级 | 导出没有等级 | 只有基准年国都记 `capital`，其余 `missing` |
| 人口 | 没有逐年序列 | missing |
| 名字 | 导出时（endYear）的名字 | 基准年早于 endYear 时不当事实 |
| 坡度 / 起伏 | 格距百余公里 | 是区域值，不是建筑坡度 |
| 距海 | 与海格相邻记 0；否则取 3 跳内格心距离，3 跳内没有海时取下界 | 写在快照 `notes` |
| 政体 | 只有 lineage（republic/realm/khanate） | 映射为 republic/monarchy/tribal，原值留 `native_form` |
| bbox | 经度直接取最值 | 跨日界线的地区会显得很宽（首轮地区 lon −174…4.9） |

**元素库的产地过滤目前在真实库上不起作用**：正式百科库（1100 条）里，带 `genre:western_fantasy` / `genre:historical` 的 206 条与带 `terrain:*` 的 411 条**交集为 0**（食物、药材有产地但没有类型标签；奇幻条目有类型但没有产地）。所以按“西幻 + 历史”设定扫描时，推荐只受类型与档位约束，`excluded.terrain = 0`。产地交集逻辑本身由测试的临时库覆盖。要让它在真实库上生效，需要给有产地的条目补 `genre:*`，或给奇幻物产补 `game.terrains`，两条路都要改数据，需作者决定。

## 6. 换成 Terragenesis 冻结产品时要补什么

只新写一个适配器（例如 `app/world_source_terragenesis.py`，读 `app/terrain_source.py`），流程不改：

- `identity()`：engine、产品 schema / 版本、内容哈希。
- `cells`：海拔、坡度、起伏、距海可由点查询得到；温度、降水若无气候层就填 `None`，并在 `missing_fields` 写明。`classify_cells` 缺降水时只给群落候选，候选不参与产地交集。
- `settlements` / `polities` / `events`：新引擎暂无，写 `ws.missing(原因)`。这时地区里没有国家，`propose` 会因为“首轮只做 2–4 国”而拒绝，历史章节也会跳过。要用新引擎走完整流程，须先由作者或后续生成提供国家与聚落，届时再放宽这条限制。
- `capabilities()` 只声明真有的字段。

## 7. 已接入的 HTTP（2026-11-08）

作者侧接口（全部需要 `X-TextileDream-Token`）：

| 方法 | 路径 | 作用 |
|---|---|---|
| GET | `/api/inner/world-package/imports` | 列出已登记的 `.civsnap` |
| GET | `/api/inner/world-package/regions?import_id=…` | 列出候选地区与来源身份 |
| POST | `/api/inner/world-package/propose` | 挑元素，存草稿（不调模型） |
| GET | `/api/inner/world-package/drafts` | 草稿摘要列表 |
| GET | `/api/inner/world-package/drafts/{id}` | 草稿全文 |
| PUT | `/api/inner/world-package/drafts/{id}/select` | 勾选元素并锁定清单 |
| POST | `/api/inner/world-package/drafts/{id}/generate` | 写历史、政治、设定与知识点 |
| PUT | `/api/inner/world-package/drafts/{id}` | 作者改写并重新校验 |
| GET | `/api/inner/world-package/drafts/{id}/freshness` | 来源是否过期 |
| POST | `/api/inner/world-package/drafts/{id}/confirm` | 编译并写入 `StoryPackage/地区_<id>/` |

前端入口本轮未接（2026-11-08 用户要求不改前端）；接口可用于后续作者面板或外部客户端。多地区、跨地区拼接、Terragenesis 适配器、河网到地块映射仍未实现。HTTP 回归见 `tests/test_world_package_http.py`；真实 civsnap 的纯 Python 端到端见 `tests/test_world_package_pipeline.py::RealCivAtlasTests`。

## 8. 测试

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest tests.test_world_package_pipeline -v
echo $LASTEXITCODE   # 以退出码为准；unittest 输出走 stderr
```

真实地区用例使用 `data/map_imports/989970517e07cd9f27ab0947cd7ad767.civsnap`，以及正式百科库的临时**副本**。文件不在时该用例明确失败，不会 skip。
