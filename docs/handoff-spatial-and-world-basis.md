# 交接：世界基础 / 空间三层 / 取样语义 的当前状态

本文件是给下一位接手者的最短路径说明。**只写实测过的事实**与**明确未做的事**。

## 1. 测试与命令

```powershell
$py = "D:\Vantaloom\tmp\scratch\venv312\Scripts\python.exe"
& $py -X utf8 -m pytest tests/test_civ_atlas_import.py tests/test_world_basis.py tests/test_land_footprint.py -q
# 当前：85 passed
```

| 文件 | 数量 | 守什么 |
|---|---|---|
| `tests/test_civ_atlas_import.py` | ~49 | 容器跨语言契约、篡改拒收、隔离数据根、图层、取样语义、严格请求体、事件循环、footprint/供给 |
| `tests/test_world_basis.py` | 19 | 能力 vs 实现分离、part sum 必须服务端算、不可变保存、伪造 digest/id 拒、同身份不同内容拒 |
| `tests/test_land_footprint.py` | 19 | 多边形校验（自交/跨日界/面积/顶点/极点）、稀疏用地、重叠只报告、未规划≠荒地、牧场不算谷物 |

## 2. 三个必须记住的不变量

1. **`TownInput.terrain.area_km2` 是粮食腹地**（`app/towns.py:167` 用它乘 `_arable_fraction`）。
   建筑范围、环境取样窗、矿山、荒地**都不能**进这个字段。
   目前只允许两个来源：已声明的 `farmland`，或作者显式填的 `hinterland_km2`。
2. **格式能力 ≠ 已实现**。`world_basis.FIELD_CAPABILITY` 说上游导出能带什么；
   `REPLAY_IMPLEMENTED` 全 `False`，所以 `field_status` 全是 `unknown`、`restorable` 是空。
   不要把 `capability.annals == 'exact'` 读成「已经能按年查事件」。
3. **part sum 由服务端算**：`app/civ_atlas_snapshot.py` 在解析时对**解压后**的 part 字节算
   SHA-256，写 `sum` 与 `sum_verified_by='server'`。客户端传来的 sum 不被采信。

## 3. 已完成

- **取样语义**：中心必须**干陆地**（海 `1` / 湖 `2` 都拒）；`dryland_km2` / `lake_km2` /
  `ocean_km2` / `dry_fraction` / `lake_fraction` / `water_known` 分列；
  `area_km2` 只算干陆地；`span_km.widest_pair_km` 是窗内实际最大球面距离。
- **空间三层**：`app/land_footprint.py` 提供 `parse_footprint` / `parse_land_use` /
  `summarize_land_use`（纯函数、无 IO）。footprint 上限 50 km²，标注
  `boundary_source='author_planned_boundary'`、`terrain_detail='coarse_mesh_reference_only'`
  并列出 `unknown`（精细道路、微观地形）。
- **供给判定**：`map_import.build_town_input` —— 只有 farmland 或显式 hinterland 才生成
  TownInput；只给 footprint / 只给矿山 / 只给牧场 → **拒绝**并指向「空间草稿」。
- **世界基础**：`app/world_basis.py`，身份 = `(world, branch, base_year, content_sha256)`；
  `save()` 在一个 `IMMEDIATE` 事务里 SELECT→INSERT，先校验 digest 与 id 自洽，
  同身份不同 digest **拒绝覆盖**。

## 4. 明确未完成（接手请从这里挑）

| # | 事项 | 为什么重要 |
|---|---|---|
| 1 | `SpatialDraft` 严格 schema + `POST /map-imports/{id}/spatial-draft` | 目前「只圈建筑范围」的草稿无处可存，只能被拒 |
| 2 | **服务端强制转换**：空间→TownInput 时缺供给必须拒 | `POST /api/inner/towns` 仍接受任意 `TownInput`，客户端可绕过 adapter 直接提交，`provenance.supply` 不是可信 guard |
| 3 | 几何运算预算 | 4096 顶点 × 64 面是 O(n²)，没有总预算 |
| 4 | 极区面积标注 | `polygon_area_km2` 用 `cos(mean_lat)` 平面近似，高纬偏大，未标注 |
| 5 | Phase D 历史回放 | `annals` 按年过滤、`checkpoints`+`log` 回放都未实现 |
| 6 | UI 地图圈选与截图 | 多边形圈选/缩放/冲突提示未做；**旧截图不代表当前布局** |

## 5. 环境与红线

- 服务：**5188 / 8898 均无监听**。启动服务前须先报主代理。
- 不 commit / 不 push；`external/` 整体被根 `.gitignore` 忽略。
- 上游改动三副本 SHA-256 必须一致（`tools/` ↔ `external/civ-atlas/public/` ↔
  `docs/civ-atlas-patch/files/`），当前 `2264D200…8A67`。
- 不改 `GRAIN_MIN_ARABLE_KM2`，不自动默认耕地，不把未规划区当荒地，
  不把矿山当已勘探，不伪造精细地形。

## 6. 已知的量化事实（避免再算一遍）

- 我们那份真实 `.civsnap`：`mesh.n = 34097`、`sea_cells = 22798`、`lake_cells = 73`、
  `generator = 45`、`snapshot_format = 1`、`recipe = dc9e079d0cb8`、
  `world_id = wmvrpuwi29m3yi`，文件 4 609 307 字节，`map`/`eras`/`civ` 三块。
- 按 `units.area` 声明的 R=6371.0088：单格 ≈ **14959 km²**；最小 3 格窗 ≈ **44878 km²**，
  已超 `TownInput` 的 20000 上限 —— 这是「必须由作者声明腹地/农田」的结构性原因。
- 温带陆地点（经度 67.19 / 纬度 27.05）：`arable_fraction = 0.135`，`arable_km2 ≈ 12154`，
  远大于 `GRAIN_MIN_ARABLE_KM2 = 8` —— 之前的「粮食承载为零」是选到了极地（T = −22.56 ℃）。
