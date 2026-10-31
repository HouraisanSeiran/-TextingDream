# 空间草稿 API（`app/spatial_draft.py`）

只圈建筑范围也能保存；农田/牧场/矿山/林地/荒地是**可选、稀疏**的规划，未规划区域一律
记为「未规划」，既不当作荒地也不当作农田。本文件是接线说明，模块本身不改任何现有文件。

---

## 1. 三层与唯一纪律

| 层 | 存在哪 | 进不进 `TownInput.terrain.area_km2` |
|---|---|---|
| 环境取样 | `environment_ref`（import id + 内容哈希）+ `sampling`（选点与窗格/半径） | **不进** |
| 城镇建筑范围 | `footprint`（作者圈的 lon/lat 环，≤ 50 km²） | **不进** |
| 用地规划 | `land_use[]`（稀疏、可选） | 只有 `farmland` 进；`pasture` 明确不进 |

`area_km2` 只有两个来源：`land_use` 里已声明的 **farmland** 面积，或作者显式给的
`hinterland_km2`。两者都没有 → `supply.state = 'unconfigured'`：草稿可以存，转换不出城镇。

## 2. 存储

`documents` 表，`kind = 'spatial_draft'`，`id = sd_` + 16 位随机十六进制（与 `runtime.uid()`
同一风格）。不新建库、不迁移、**不写故事包 pointer**。写入只用 `Store.transact()` 短事务。

文档字段：`id / kind / schema / revision / created / updated / request_id /
story_base_revision / site_name / note / footprint / land_use / land_use_summary /
footprint_conflicts / area_plan / supply / hinterland_km2 / sampling / environment_ref /
world_basis_ref / geometry_budget / area_approximation / content_hash / warnings`。

- `revision` 从 0 起，每次 `update` +1，是唯一的乐观并发凭据（CAS）。
- `content_hash`：保存内容的摘要（不含 id/revision/时间戳/story base）。
- 源身份**不新造哈希**：直接引用导入记录已有的 `sha256` 与 `world_basis.digest`。

## 3. 请求体（严格，未知字段一律拒）

```json
{
  "site_name": "必填，≤80",
  "footprint": {"vertices": [[lon, lat], ...], "note": ""},
  "land_use": [{"kind": "farmland|pasture|mine|forest|wasteland|other",
                "vertices": [[lon, lat], ...], "note": ""}],
  "environment_ref": {"import_id": "mi_…/sn_…", "source_sha256": "64 位十六进制"},
  "world_basis_ref": "wb_…（可选）",
  "hinterland_km2": null,
  "sampling": {"lon": 0.0, "lat": 0.0, "window_px": 3, "radius_km": 6371.0088},
  "note": "",
  "request_id": "可选的幂等键（≤64 位字母数字/_/-）"
}
```

- `footprint` 与 `land_use` 至少要有一个。
- 只认 `import_id + source_sha256`；`path`、`url` 这类字段是**未知字段**，直接拒。
- `sampling` 缺省时按建筑范围顶点的圆均值给出一个初始选点，并标
  `source: 'footprint_vertex_mean'`（明确说明它可能落在凹多边形外，转换时必须真实取样）。
- `land_use[].surveyed` 不接受：草稿里的矿山只表达意图。
- 重名地点不是约束：两次保存得到两个独立草稿。

## 4. 冻结的调用签名

```python
spatial_draft.save(store, body, *, story_base_revision, resolver=None)
    -> {'draft': doc, 'created': bool}
spatial_draft.update(store, draft_id, body, *, expected_revision, resolver=None) -> doc
spatial_draft.get(store, draft_id) -> doc                    # 只读
spatial_draft.list_drafts(store) -> [doc]                    # 只读
spatial_draft.prepare_conversion(draft, *, current_story_revision=None) -> report
spatial_draft.to_town_input(store, draft_id, *, author, current_story_revision,
                            sample=None, sampler=None, resolver=None,
                            expected_revision=None) -> result
spatial_draft.validate_sample(sample) -> dict
spatial_draft.check_sample_matches(draft, checked_sample) -> True
spatial_draft.summary(doc) -> dict

class SpatialDraftService(service)      # 薄接线，供 app.service.Service 持有
    .save(body) / .update(id, body, expected) / .get(id) / .list()
    .prepare(id, current_story_revision=None)
    .to_town_input(id, *, author, current_story_revision=None, sample=None,
                   expected_revision=None)
    .sampler(draft_or_id) -> callable(draft_snapshot, lon, lat, window_px, radius_km)
    .base_revision() / .root() / .view(doc)
```

`resolver(import_id) -> import record` 默认是 `map_import.get_import(store, id)`；只在
测试或沙箱里替换。`sampler` 是服务端取样函数：收到的是**已经读好的草稿快照**，
它不会再去读一遍草稿（按 id 直调时才自己读一回）。

## 5. `to_town_input` 的结果

```json
{"status": "ready" | "blocked",
 "draft_id": "sd_…", "draft_revision": 3,
 "missing": ["farmland_or_hinterland" | "footprint_overlaps_land_use"
             | "overlapping_farmland" | "overlap_undetermined"
             | "sampling_point" | "story_base_revision_mismatch"],
 "spatial": {"supply": "...", "area_source": "declared_farmland|author_declared_hinterland",
             "terrain_area_km2": 12.3, "farmland_km2": 12.3, "planned_km2": 12.3,
             "footprint_area_km2": 0.4, "conflicts": [...], "blocking_conflicts": [...],
             "undetermined_pairs": [], "overlap_scan": {...},
             "footprint_conflicts": [...], "sampling": {...},
             "area_approximation": {...}, "geometry_budget": {...}},
 "input": { TownInput … } | null,
 "provenance": { … build_town_input 的 provenance + "spatial_draft": {…} } | null,
 "warnings": [...]}
```

- `blocked` 时**草稿一个字节都不动**（不删、不改、不降级）。作者可以继续编辑。
- `ready` 时也不改草稿：转换是纯读的。发布正文仍由调用方走原有 towns 流程。
- 走过 `map_import.build_town_input`，所以缺气候/缺作者字段等拒绝**照原样**抛出。
- 转换要求 `current_story_revision == draft['story_base_revision']`，否则抛
  `SpatialDraftError`（旧故事包改过就拒，不悄悄挂到新世界）。

### 取样来源与快照固定

- 传 `sampler`：`sampler(draft_snapshot, lon, lat, window_px, radius_km)`（也接受旧的
  四参数形式），参数与来源都取自**同一次读到的草稿快照**，不会中途重读：
  `sample_source='server_recomputed'`。
- 只传 `sample`：结构校验 + 必须与草稿保存的 lon/lat/window_px/radius_km 一致，
  `sample_source='caller_supplied_checked_against_draft'`，结果里带一条警告。
  **本模块无法验证一个 dict 来自哪里**，也不这么说——来源由调用方的 resolver/sampler 负责。
- 可选 `expected_revision`：进来先校一次，取样与 build 之后、交出 `input` **之前**
  再校一次（`_check_unchanged` 重读比对 revision + content_hash）。中途被改就抛
  `SpatialDraftError`，不写任何东西，也不加长事务或锁。

## 6. 几何预算与面积口径

- 单面 ≤ 256 顶点、总顶点 ≤ 512、面数 ≤ 64（复用 `land_footprint.MAX_LAND_USE_ITEMS`）。
  这些检查跑在解析器**之前**：`is_self_intersecting` 是 O(n²)，4096 顶点 × 64 面必须挡住。
- 正常城镇小 polygon（< 1 km²）不会被为难，只有超上限才拒。
- 纬度带：`|lat| ≤ 78°` 且纬度跨度 ≤ 30°。`polygon_area_km2` 用平均纬度余弦的平面近似，
  这两个限制是该近似有据的范围；超了就拒，不冒充精确面积。
- `area_approximation.planned_is_not_cultivated = true`：规划面积不是实际耕作面积，
  粮食仍只由既有 `_arable_fraction` / `GRAIN_MIN_ARABLE_KM2` 决定。**不改任何经济常数。**
- 重叠检测**只消费** `land_footprint` 的既有能力：`summarize_land_use`（顶点包含筛查）
  ＋ `_segments_cross`（同一套线段相交判定，用在环与环之间）。不做精确求交/求差，
  不做并集或面积扣减；共边/共点不算重叠。
  - **建筑范围与任何其它用地重叠 → 阻断转换**（`footprint_overlaps_land_use`）：
    草稿可以存、可以继续改，但交不出 TownInput——不能把房子算成粮田，也不自动做差集。
  - **农田与任何用地重叠（含十字交叉）→ 阻断**（`overlapping_farmland`），不按 sum 双算。
  - 边相交筛查有预算（`MAX_EDGE_PAIRS = 200000` 边对）；超预算的配对记成
    `overlap_scan.complete=false` + `undetermined_pairs`，转换报 `overlap_undetermined`——
    **不明不等于干净**。

## 7. 已接线的端点（`app/web.py`，已实现）

```python
GET  /api/inner/spatial-drafts                       # summary 列表
GET  /api/inner/spatial-drafts/{draft_id}            # summary + 几何 + prepare 摘要
POST /api/inner/spatial-drafts                       # {"draft": {...}} → save
PUT  /api/inner/spatial-drafts/{draft_id}            # {"expected_revision": int, "draft": {...}}
GET  /api/inner/spatial-drafts/{draft_id}/conversion # 纯读 prepare
POST /api/inner/spatial-drafts/{draft_id}/town-input # {"expected_revision": int, "author": {...}}
```

全部走 `/api/inner/*`，沿用现有 token + 本机 Origin 中间件，没有新增鉴权面。要点：

1. `Service.__init__` 里 `self.spatial = SpatialDraftService(self)`。
2. 几何 schema 只在服务层一处：`SpatialDraftBody.draft` 是 `dict`，严格校验全在
   `spatial_draft.parse_request`，web 不重复一层。
3. **转换请求模型里没有 `sample` 字段**（`extra='forbid'`），客户端送 sample 直接 422。
4. `expected_revision` 在 API 层就是必填 `int`（`strict=True`），缺失/字符串 → 422。
5. 取样 CPU（重读原件 + 重算哈希）走 `run_in_threadpool`；数据库只有短 transact，
   **不持 `service.lock`**。
6. 转换产物 `provenance.spatial_draft` 带 `draft_id / draft_revision / content_hash /
   sample_source / mapping_source='author_spatial_draft'`；**不自动 publish、不动 pointer**。

另修正了一处既有缺陷：CSP 的 `img-src` 原来只有 `'self' data:`，而地图预览是带 token 头
取回后转的 `blob:` ObjectURL，被 CSP 拦掉——整张底图根本画不出来。现为
`img-src 'self' data: blob:`。

## 8. 作者侧 UI（`app/static/spatial-planner.js`）

接在已有「世界地图工具」页，复用它的底图与图层：**不新增游玩常驻图、不另造底图**。

- **模式分离**：选点取样 / 圈建筑范围 / 圈用地。画多边形时 SVG 覆盖层接管点击并
  `stopPropagation`，原有取样 handler 未改，两种模式不互相误触。
- **必须能放大**：整幅世界图上 1px ≈ 50 km，而建筑范围上限 50 km²，不放大根本画不出来。
  提供放大/缩小/看全图 + 滚轮缩放 + 拖动画布；图片与覆盖层共用同一变换，所以框选不偏。
- **图像真实矩形**：经纬度按 `#map-preview` 实际绘制区域换算（等比留白不计），不用容器框。
- 连续经纬圈选，不受粗 mesh 最少格数限制；结束多边形 / 撤销最后一点 / 清除这圈；
  用途 farmland / pasture / mine / forest / wasteland / other，已加的可改用途或删除。
- 未规划不分类：没画的区域不会被当成荒地或农田（页面文本明写）。
- 已存草稿下拉载入 → 带 `revision` 的 CAS 保存；过期 400 提示重新载入，不静默覆盖。
  载入时若草稿声明的地图不是当前图，会先切到那张图；换图时未结束的点被丢弃并告知。
- 转换前先调 `/conversion`，缺项逐条翻译成人话（缺农田/重叠/建筑压用地/缺选点/故事包已更新）；
  无供给时明说「能存不能转换，缺农田或腹地」，**不逼填整片腹地**（显式 hinterland 只在高级区）。
- 作者字段（水源/材料/技术）默认折叠且明说「地图不会告诉你这些」，不冒充地图事实。
- 视觉分层集中在本页 CSS：中性炭灰面 / 阅读面 / 浮层三层，青绿只给主操作·选中·焦点，
  暖金留给地图标记；沿现有 `:root` 变量，不新建主题引擎、不引字体、不加装饰动画。

## 9. 未做（明确留白）

- 没有把草稿列进城镇草稿面板（四阶段/发布/绑定仍在既有城镇页）。
- 没有把 `land_use` 接入经济/生产 tick；牧场还没有独立生产模型。
- 没有历史回放：`world_basis_ref` 只固定来源与年份。
- `api/inner/towns` 仍接受任意 `TownInput`（作者显式输入路径），本模块不声称堵住了它。
