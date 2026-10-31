# civ-atlas 历史契约（按年有界背景候选）

实现：`app/civ_atlas_history.py`　测试：`tests/test_civ_atlas_history.py`（69 项）+ `tests/test_civ_atlas_part_refs.py`（9 项）

只读：不联网、不读文件/URL、不跑上游、不写入任何数据。输入是调用方已验过的 `.civsnap` 字节（或其解码后的 `civ` 块）。

**定位**：作者选了「这张地图 + 这段结构化推演」，再选一个**基准年**与**分支**，本模块给出这一年可核的背景**候选**。不自动正典，不直接改会话，默认不进玩家侧。

---

## 1. 上游与授权

- 上游：`guaner-334/civ-atlas`，commit `0939c5f1622a5e45cfc16f645ea3845993ab3985`，AGPL-3.0-only。
- 读的格式：**generator 45 / snapshot format 1**；`Civ` 按 `src/gen/civ/types.ts`。不回推更早或更晚版本的同名字段。
- **未复制上游代码**：本模块从 `types.ts` / `snapshot.ts` 的**字段定义**（数据语义）独立写成，没有逐行移植或翻译上游实现。导出的世界数据归作者。

## 2. 调用面（已冻结）

```python
decode_civ_part(manifest, parts) -> dict          # 复用 parse_container/parse_part/_inflate
load_civ(data) -> (civ_dict, manifest)
identity_from(manifest, record=None, branch=None, terrain_seed=None) -> dict
inspect(civ) -> dict                              # 只有计数与年份，不含判断
build(civ, *, base_year, window=None, identity=None, terrain=None,
      hidden_refs=(), include_regions=False,
      max_events=240, max_entities=200) -> dict
public_view(document, *, allow=(), max_events=None) -> dict
```

预算常量在 `LIMITS`（窗口 150 年、事件 240、实体 200、日志 4 000 000 条、州 40 000…）；越硬上限**拒收**，不静默采样；软预算只截 `items` 列表，`counts` 始终精确。

## 3. 字段实测与支持度

`civ` 块实测（本工程真实导出，4 609 307 B，`world.id=wmvrpuwi29m3yi`）：

| 字段 | 真实值 | 支持度 |
|---|---|---|
| `seed` | **531844**（在导出里） | 直接采用，标 `civ_seed_source='civ.seed'` |
| `endYear` | 3000 | — |
| `regions.count` | **870**（≠ map 的 34097 地块） | — |
| `log.size` | 4549（= 数组长，有效前缀） | 只用前 `size` 条 |
| 日志年份 | 0.0…2996.36328125，**4549 条里 4522 条非整年** | 浮点、不截断 |
| `checkpoints` | 30 个，100…3000 | 锚定快照 |
| `annals` | 5430 条，41 种 kind | `exact` |
| `upheavals` | **缺失** | 地形 unknown |
| religion log/checkpoints | 1772 / 31 | **不回放**（各州信仰 unknown） |

`field_status` 每项带 `status` / `evidence` / `note`，与 `world_basis.FIELD_CAPABILITY` 同名同集合（9 实 / 4 unknown）：

| 字段 | 状态 | 依据 |
|---|---|---|
| `region_culture` / `region_polity` | `as_of_interval` | 检查点 + 日志回放，并独立对 endYear 自检 |
| `annals` | `exact` | 每条自带年份 |
| `polity_founded` / `polity_capital_spans` | `as_of_interval` | `founded ≤ Y < ended`；国都只取 `capitals[]` |
| `settlement_lifespan` / `settlement_capital_spans` | `as_of_interval` | `founded ≤ Y < ended`；`capitalSpans[]` |
| `people_lifespan` | `as_of_interval` | `born ≤ Y < died`，在位看 `from/until` |
| `religion_events` | `exact` | 按年筛 |
| `population` / `resources` / `routes` / `terrain` | **`unknown`** | 导出无逐年序列：人口是现算公式、物产是 0–3 档储量、路是逐格路径、地形只在大事变 |

**基准年的实体名字**也是 unknown（只有导出时的名字，见 `display_name_basis='export_time'`）。

## 4. 年份语义（关键）

- 基准年 **接受浮点、全程数值比较**。真实年份是 `511.9765625` 这样：实体在该年**尚不存在**，不能截断成 511。
- 对照：`Y=511.0` → 0 国；`Y=511.9765625` → 1 国；`Y=512` → 1 国。
- 统一口径：实体存在当且仅当 `founded ≤ Y < ended`；国都段 `from ≤ Y < until`。
- 窗口默认 `[Y−150, Y]`，**结束年不得晚于基准年**（看不到自己的未来），也不得晚于 `endYear`。

## 5. 政区/民族层：回放与自检

```
Y 年的归属 = year ≤ Y 的最近检查点 + (检查点年, Y] 的日志，按 layer 叠到对应州
```

- 检查点年 C 的快照**已含 C 年及以前**的变化（上游快照的是当时的数组），所以日志从 `C` 之后开始。
- **endYear 自检独立于基准年**：锚点取 **严格早于** `endYear` 的最近检查点，把余下日志回放到 `endYear`，与导出的 `civ.culture` / `civ.polity` **逐州**比对。选早期年份不会让这个判定变差。
- 真实结果：锚点 2900，叠 254 条日志，`exact`，`mismatched_layers=[]`。
- 只有 endYear 当头的检查点时，记 `mode='checkpoint_only'` 并明写「**未验证**」，不冒称已核。
- **早于第一个检查点**：报 `unknown`。上游 `timeline.ts` 从全 `-1` 翻日志是另一种主张（「首个检查点前全空」），本工程不拿它冒充历史。
- 日志/检查点对不上 → `unknown` + 异常记录，**不给错值**。

## 6. 事件列语义（不统一当国家索引）

`Annal.a / b / region / war` 的含意**随 `kind` 变**（`types.ts:312-402` 那张表）：

- `ANNAL_AB[kind]` 逐 kind 声明每列是 `polity` 还是 `culture`；`None` = 该 kind 这一列不是实体编号（计数/下标/代码），此时输出 `*_raw` 原值 + `*_means=null`，**不猜**。
- `ANNAL_COLUMN_NOTES[kind]` 给跨列警告：`peace.region` 是割让州数、`council.war` 是议题编号、`collapse.war` 是散出去几块、`plague.war` 是第几场瘟疫、`regent`/`treaty`/`neutral`/`marry`/`stand` 等同理。
- **不认识的 kind**（比上游新）：`kind_known=false` + `unresolved` 说明，列原样保留。

## 7. 地形

`eras` 块是**地形演化版本，不是历史**。

| 情况 | `terrain.state` |
|---|---|
| 没有地形大事，无 eras 段 | `same_terrain_all_years` |
| `Y ≥` 最后一件地形大事 | `current_terrain` |
| `Y <` 最后一件大事，或有 eras 段 | **`unmatched`** + 「未关联」 |

`unmatched` 明说我们手上的图是大事**以后**的地形，**不冒称**把该年地形复原了。

## 8. 身份与 ref

```
casnap:<content_sha256 前16>:<world_id>/<branch>/<kind>/<id>
```

- `kind` ∈ `polity` / `culture` / `settlement` / `person` / `faith` / `annal` / `faith-event`。
- **名字绝不当 id**：`display_name` 只供显示，并自带「可能晚于基准年」说明。
- 缺 `branch` / `civ_seed` / `terrain_seed` 就 `null` + `*_known=false`；**不从 recipe 指纹反推**。
- `civ.seed` 是真字段 → 直接采用；外来 `identity['civ_seed']` **不能覆盖**数据值，只记 `caller_supplied_civ_seed_ignored`。

## 9. 公开投影（`public_view`）

> **范围说明**：本节是**作者内部**的白名单投影（给作者看“如果披露会是什么样”）。
> **运行期**的玩家侧历史走 §14.1 的 `WorldHistoryService.public_view`，它是按**逐条选中的 ref**
> 再筛的——**绝不把类别当授权**给玩家全部条目。

纯函数。**默认 `allow=()` → 什么都不投**：只有年份、窗口、地形关联、字段状态。

授权某类**不等于**能看未来——每类实体过自己的白名单 `PUBLIC_ENTITY_FIELDS`：

| 类 | 可投影 |
|---|---|
| `polities` | `ref, id, display_name(_note), founded, capital_ref, capital_status` |
| `settlements` | `ref, id, display_name(_note), founded, region` |
| `people` | `ref, id, display_name(_note), role, born, polity_ref, in_office_at_base_year` |

**永不进玩家侧**：`died`、`fate`、`until`、`ended`、`capital_spans`、`dynasties`、`titles`、`sacks`、`reshaped`、`rebuilds`、`devCap`、`regencies`、`exile`、`claim`。
某个人在基准年**活着**、但 `died > Y` → 公开视图里看不到他的死年与结局（有专项测试）。

`hidden_refs` 里的项从所有列表剔除，且**不给玩家侧报 hidden 的数量**。`allow` 里有不认识的项目 → 拒收。

## 10. 明确不做

- 不做通用模拟器、不做经营 tick、不重算上游公式（人口/国号/发展度）。
- 不把「选年事件清单」当该年的完整状态（`is_full_state=False`）。
- 不采 AI 扩写史书当事件事实（`ai_chronicle_used=False`；事实只来自结构化 `annals`）。
- 不读 `development` / `routes` / 信仰回放；不读存档、不碰 `data/`、百科。
- 不另造 checksum 体系：源 pin 沿用既有 `content_sha256` + part sums。

## 11. 上游共享解码器的一处真实缺陷（已修）

`app/civ_atlas_snapshot.py` 的 `_decode_structure` 解 `{"$$":"a"}`（类型化数组）时**没有登记到 `refs`**，而上游 `unpackValue` 的 `case 'a'` 会 `objs.push(out)`。后果：只要有一个数组被第二次引用，后续所有 `{"$$":"r"}` 编号整体偏移。

真实样本里的触发点：`civ` 块有 2597 个 `$$:a`、22 个 `$$:r`，全部指向 `.religion.faiths[0].color`（编号 28645 / 上游总对象 29676；不登记时只有 27079，越界）。`map` / `eras` 块没有跨对象共享数组，所以之前从未暴露。

修复：`tag == 'a'` 分支在 `return` 前 `refs.append(out)`，登记的就是返回的**同一个 list**，重复引用 `is` 同一对象；其余分支、对齐、越界、未来引用、负/布尔编号的拒收全部保留。回归：`tests/test_civ_atlas_part_refs.py`（9 项，含真实形态的共享 color）。

## 12. 验证

```powershell
$py = "D:\Vantaloom\tmp\scratch\venv312\Scripts\python.exe"
& $py -X utf8 -m pytest tests/test_civ_atlas_history.py tests/test_civ_atlas_part_refs.py tests/test_civ_atlas_import.py tests/test_world_basis.py -q
```

当前：**44（采纳服务）+ 19（world_basis）+ 69（回放）+ 9（解码器引用）= 141 passed**（合跑 exit 0）；导入套 47 项另跑也是全绗，合计 188。

真实解析 probe（`RealExportProbeTests`，11 项）读旧代理真实导出的 `.civsnap`（只读，不拷进 `data/`）：
路径 `D:/Vantaloom/data/temp/project-proj-1792851796-712e540fb0/scratch/real-verify-data/map_imports/2f364872015835be5a905876c6bdf5ae.civsnap`；文件不在时 `skip` 并明写「**未验真**」，不会假装通过。

## 13. 接线留待（不在本模块）

本模块只负责「给定 `civ` + 基准年 + 身份 → 有界候选文档」。以下由后续串行接线完成：

1. `world_basis.REPLAY_IMPLEMENTED` 按本模块实际能力置位，`field_status` 直接取本模块结果；
2. Web 端点把 `build` 的输出当成作者侧草稿，并给 `public_view` 单独的授权参数；
3. 作者审核后才写进故事包快照（`for_author_review=True` / `auto_canonical=False` 就是为此留的）。

---

# 14. 采纳服务：预览 → 审阅 → 快照 → 采纳

实现：`app/world_history_store.py`（`WorldHistoryService`）　测试：`tests/test_world_history_store.py`（44 项）

作者层面把「回放出来的候选」变成「故事包里固定的历史背景」。全程只写自己的三种文档，用现有 `Store` 命名空间，没有第二个数据库。

## 14.1 调用面

```python
svc = WorldHistoryService(runtime, load_civ=None)   # load_civ 仅供测试注入；默认读字节
svc.preview(record, *, base_year, branch=None, window=None,
            max_events=None, max_entities=None)  -> {preview, reused, document}
svc.get_preview(preview_id) -> draft
svc.page(preview_id, category, page=0, size=25) -> {items, total, pages, truncated_by_page}
svc.review(preview_id, *, entries, disclosure=None, local_links=None, max_entries=None) -> draft
svc.commit(preview_id, what_changed='', max_entries=None) -> {snapshot, created, world_basis, reused}
svc.get_snapshot(snapshot_id) -> snapshot
svc.adopt(snapshot_id, expected_story_revision, note='') -> {revision, adoption, reused, note}
svc.authored(snapshot_id) -> 作者视图（全部选中条目）
svc.public_view(snapshot_id) -> 玩家视图（仅逐条披露的）
svc.adoption_for(snapshot_id, story_id, revision=None) -> adoption | None
```

三种文档：`history_preview`（可变草稿）、`history_snapshot`（不可变、自包含）、`history_adoption`（不可变索引）。

## 14.2 四个不变量

1. **预览不动故事、不动会话。**`preview` 只写一行 `history_preview`；同请求键返回原草稿不新建。
2. **全史不进 prompt。**快照受 `max_events` / `max_entities` 约束；超了用 `page` 逐页走，`total` 与 `pages` 始终精确，`truncated_by_page` 明确标出——**不静默截断**。
3. **披露是逐条，不是按类别。**`disclosure.public_refs` 是显式 ref 列表；授权一个类别不等于放出该类全部。未选中的不得写摘要（拒收）。
4. **采纳不动地图。**`mechanics.map` 一字不改；不默改地图 source/world，不给玩家全员历史。

## 14.3 采纳所写入的机械字段

```json
{"mechanics": {"history": {
  "schema": 1,
  "entries": [{
    "snapshot_id": "hs_…", "import_id": "sn_…", "base_year": 1500.0,
    "branch": "main", "digest": "…", "world_basis_id": "wb_…",
    "content_sha256": "…", "adopted_from_revision": "…",
    "snapshot": { …完整快照（entries/disclosure/source/field_status/terrain）… }
  }]
}}}
```

快照里带 `source.content_sha256` + `source.parts[]`（每块 sum 与 `sum_verified_by`）+ `world_basis`（含 `civ_seed` 与 `civ_seed_source='civ.seed'`）——**导出的包可以导进空库，删掉原 `.civsnap` 后采纳历史仍可读**（有专项测试）。

## 14.4 幂等与失败

| 情况 | 行为 |
|---|---|
| 同预览请求 | 返回原草稿，`reused=true` |
| 同快照内容 `commit` 两次 | 同一 `snapshot_id`，`created=false` |
| 同快照 `adopt` 两次 | 同一 revision，`reused=true`，条目不重复，索引不重复 |
| 已包内但丢了索引 | 下次相同请求补齐索引，**不新建 revision** |
| `expected_story_revision` 已落后 | 拒收（不把旧历史悄悄挂到新世界上） |
| 快照 digest 被篡改 | 采纳时拒收 |
| 基准年越界 / 超 `endYear` | 预览时拒收（`HistoryError`） |
| 源哈希不符 | 预览时拒收 |
| 两个上游城镇关联到同一本地地点 | 拒收 |
| 摘要写给未公开条目 | 拒收 |

## 14.5 读文件只用自己那一份数据根

`_data_root()` 与 `Runtime` 同一规则：**只有生产库**（`<root>/data/textiledream.sqlite3`）读项目根，临时/沙箱库读自己的目录。所以测试永不碰用户 `data/`。读字节前重算 SHA-256 与记录对不上就拒收。

## 14.6 `world_basis` 的两条路径

| | `build()` | `build_from_history()` |
|---|---|---|
| 年份 | 整数（旧契约不变，`1.5` 拒收） | **浮点可**（真实年份是 `511.9765625`） |
| `history.state` | 永远 `unresolved` | 按回放文档填 `replayed` / `unresolved` |
| `field_status` | 全部回落 `unknown` | 取回放文档的逐字段状态 |
| `world.civ_seed` | `null` | 真 `civ.seed` + `civ_seed_source` |
| 年份/分支/源哈希与文档不符 | — | 拒收 |

两条路径并存：旧调用与旧 19 项测试一字不差，新路径才声称「回放过」。

---

# 15. 作者页组件与路由（已接线）

独立组件：`app/static/world-history.js`（自定义元素 `<world-history-panel>`，classic script + `defer`）。
已挂在 `index.html` 的 map-tools 页侧栏里（`map-import.js` 里一块 `#map-history-block` 容器）；
**未改任何既有地图控件、未动 play-ui.js、未改 CSS**。

## 15.1 真实路由（全部作者侧、全部要 token）

| 方法 | 路径 | 服务端 |
|---|---|---|
| GET | `/api/inner/history/imports` | 可回放的导入列表 |
| POST | `/api/inner/history/previews` | `service.history.preview(...)`（body 只收 `import_id`/`base_year`/`branch`） |
| GET | `/api/inner/history/previews/{id}` | `get_preview` |
| GET | `/api/inner/history/previews/{id}/page` | `page` |
| POST | `/api/inner/history/previews/{id}/review` | `review(..., expected_revision=)` |
| POST | `/api/inner/history/previews/{id}/commit` | `commit(..., expected_revision=)` |
| GET | `/api/inner/history/snapshots/{id}` | `authored` |
| POST | `/api/inner/history/snapshots/{id}/adopt` | `adopt(..., expected_story_revision=)` |

**读预览也要 token**：预览是未公开的作者草稿。`/api/history/...`（无 `inner`）**不存在**，
有专项测试钉着（匿名读/写 = 403，旧前缀 = 404）。

### 请求体是严格模型

`HistoryPreviewRequest` 只有 `import_id` / `base_year` / `branch` / `window` / 两个预算。
`record` / `file` / `url` / `civ` 这类额外字段一律 **422**（`extra='forbid'`）：服务端自己按
`import_id` 取 `map_import` 记录、自己核 hash、自己读字节。解码在 `run_in_threadpool` 里做，不拿全局锁。

### 两个 CAS 都由作者带上来

- `expected_revision`（草稿）——review 与 commit 都要，服务端**不**用“当前值”代填。
- `expected_story_revision`（故事包）——adopt 要，且必须等于快照里冻结的 `base_story_revision`；
  组件把它存在 `this.storyRevision`，提交时不重新读当前 revision。

## 15.2 包内运行期投影（给行动席接 Runtime）

两个**纯函数**在 `world_history_store.py`，不访问 store、不读库：

```python
package_history_public(story, session, audience='player')  -> [ {ref, category, ...} ]
validate_package_history(story)                           -> True / 拒收
```

- 玩家侧历史**只从 `story.mechanics.history` 读**：快照在采纳时已拷进包里，删掉 store 里的
  `history_snapshot` 行、或库里有更新的同名快照，都改不了这段旅程读到的东西。
- `session` 只用于“这个人/这趟旅程知道什么”：`known_by` 限定受众、`location_id` 需已到访、
  `reveal` 旗需已置位。未受限的条目就是公开常识。
- 字段白名单同 §9；**死年、结局、后来的国都**永远不出包。
- `validate_package_history` 检查形状、每份嵌入快照的 digest、重复绑定、公开 ref 必须真在快照里；
  缺 `mechanics.history` = 无操作，旧包行为不变。

**行动席接管 Runtime 时的最小钩子**（一行一处，本轮不动 runtime.py）：

```python
# app/runtime.py: validate_package 里，紧跟 towns_store.validate_package(story) 之后
world_history_store.validate_package_history(story)
```

玩家读取处（surface / context 里需要历史时）：

```python
rows = world_history_store.package_history_public(package['story'], session)
```

## 15.3 来源一致性

- 包已链 `mechanics.map.import_id` 时，历史快照的 `import_id` 必须相同；否则拒收（两个世界）。
- 快照里关联的 `location_id` 必须真在当前包里存在；不按名字匹配。
- 采纳**不改** `mechanics.map`；未链地图的故事包可以只采纳历史（不暗中绑定地图）。

独立组件：`app/static/world-history.js`（自定义元素 `<world-history-panel>`）。
**不挂 index 脚本、不改共享 static/CSS/service/web/runtime**；插上就是：

```html
<script type="module" src="/static/world-history.js"></script>
<world-history-panel preview-id="hp_…"></world-history-panel>
```

它只做一件事：把服务端算好的草稿逐页展示，让作者按 ref 选、标公开范围、确认采纳；
不自己算历史、不猜年、不改地图，也不编默认值。

## 15.1 它调的五个接口（最小形态）

| 方法 | 路径 | 服务端应做的事 |
|---|---|---|
| GET | `/api/history/previews/{id}` | `svc.get_preview(id)` |
| GET | `/api/history/previews/{id}/page?category=&page=&size=` | `svc.page(...)` |
| POST | `/api/history/previews/{id}/review` | `svc.review(id, entries=…, disclosure=…, local_links=…, expected_revision=…)` |
| POST | `/api/history/previews/{id}/commit` | `svc.commit(id, expected_revision=…)` |
| POST | `/api/history/snapshots/{id}/adopt` | `svc.adopt(id, runtime.package()['id'], note=…)` |

接线要点（全部已在模块里，不需要再写逻辑）：

1. `WorldHistoryService(runtime)` —— 生产路径不要传 `load_civ`（它是测试注入用的）。
2. 路由里只做 `try/except ValueError → 400`，**不要**吞掉中文拒收原因；组件直接把 `detail` 原样显示。
3. `adopt` 的 `expected_story_revision` 必须取**当前** `runtime.package()['id']`；
   它会自己拒绝跨世界与跨版本采纳（不隐式 rebase）。
4. `preview` 需要一个已登记的导入记录（`sn.compat`：`store.get('map_import', id)`）。
5. 玩家侧历史**不能**用 `civ_atlas_history.public_view`（那是作者内部白名单）；
   运行期用 `svc.public_view(snapshot_id)`，它按逐条 `disclosure.public_refs` 再筛。
