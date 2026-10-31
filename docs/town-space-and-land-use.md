# 城镇空间：建筑范围 / 用地规划 / 环境取样（三层分离）

用户决策（覆盖此前「必须填整片 hinterland」）：
> 「城镇只需要圈出建筑范围即可，地图中其他区域可以规划为矿山、农田或者荒地等，
>  不需要给整个地图都规划区域。」

这条改变了取数方式，本文定下三层结构与接口。

---

## 1. 为什么必须分三层（实读 `app/towns.py`）

现有城镇规则把 **`TownInput.terrain.area_km2` 当作粮食腹地**：

```
arable_km2 = terrain.area_km2 * _arable_fraction(terrain)      # towns.py:167
local_food = arable_km2 * FARM_PERSONS_PER_KM2  (若 arable_km2 >= 8)   # :171
staple     = arable_km2 * GRAIN_YIELD_T_PER_KM2_YEAR                    # :633
```

所以：

| 想表达的东西 | 塞进 `terrain.area_km2` 会怎样 |
|---|---|
| 建筑范围（几十公顷～几平方公里） | 粮食/人口被**严重低估**，且把「房子占地」冒充「耕地」 |
| 环境取样窗（本网格单格 14959 km²） | 粮食/人口被**严重高估**（等于说整片荒野都是耕地） |

**结论：建筑范围绝对不能填进 `terrain.area_km2`。** 这个字段只应由「已声明的生产用地」决定。

---

## 2. 三层结构

### 2.1 环境取样（已有，保持不变）
`POST /map-imports/{id}/sample` → 气候、海拔、坡度、水体、干陆地覆盖。
**只作为「这里大概是什么环境」的依据**，不用于自动推可耕面积。

### 2.2 城镇建筑范围（新，作者圈选）
```
footprint: {vertices: [[lon, lat], ...], note?}
```
- **连续经纬度多边形**，不要求 3 格窗，不受 mesh 格限制（粗格只作底图参考）。
- 严格校验：顶点数、有限数、经纬度范围、面积上下限、跨日界（±180）、自交。
- 面积上限按「建筑聚集」量级（默认 ≤ 50 km²，可配），**不**用于粮食。
- 底图精度不够时**如实标注**：`terrain_detail: 'author_planned_boundary'` +
  `unknown: ['精细道路', '微观地形']`，不伪造精细地形。

### 2.3 用地规划（新，可选、稀疏）
```
land_use: [
  {kind: 'farmland'|'mine'|'wasteland'|'forest'|'pasture'|'other',
   vertices: [[lon,lat], ...],
   note?, surveyed?: false}
]
```
规则：
- **可选、稀疏**：不要求覆盖全域；**未规划区域保留 `unplanned`**（不是"荒地"，荒地必须显式声明）。
- 农田允许与地形水体约束校验（不能整片划在海上/湖面）。
- **矿山只表达意图**：`surveyed: false`、不产生 `extractable`、不产生库存。
- **农田不是即时产粮**：只作为「已声明的生产用地」进入粮食计算，仍需通过既有规则。
- 重叠用地 → **显式冲突清单**交作者审核，不自动择一。

### 2.4 与 `terrain.area_km2` 的关系
```
terrain.area_km2 = 已声明的生产用地面积（farmland/pasture 等，按用途加权）
# 不是 footprint，不是环境窗
```
若作者只画了建筑范围、没规划农田、也没有可靠进口 →
**允许保存为「空间草稿」**，但明确标 `supply: 'unconfigured'`，
**不得**通过发布校验（现有 food/water 校验继续生效）。

---

## 3. 与现有城镇的兼容

| 场景 | 行为 |
|---|---|
| 只有 footprint，无 land_use | 保存为空间草稿，`supply='unconfigured'`，`publish` 被拒并说明缺什么 |
| footprint + 农田 | `terrain.area_km2` = 农田面积；走既有四阶段，可发布 |
| 无 footprint（旧路径：预置输入/采样点） | 完全不受影响，`area_km2` 仍由原逻辑给 |
| 旧草稿 | 不改字段、不迁移、不重新校验；新字段缺失即视为旧路径 |

**不改 `GRAIN_MIN_ARABLE_KM2`**，不自动补默认耕地。

---

## 4. 接口（最小版本，先做校验器 + 草稿）

```python
# app/land_footprint.py（纯函数，无 IO）
parse_polygon(vertices, *, name, max_area_km2, radius_km) -> Polygon
  # 校验：3..4096 顶点、finite、lon∈[-180,180]、lat∈[-90,90]、
  #       面积 ∈ (0, max_area_km2]、自交检测、跨日界归一
polygon_area_km2(polygon, radius_km) -> float   # 球面面积（近似，注明）
detect_overlaps(polygons) -> list[conflict]
summarize_land_use(items, radius_km) -> {by_kind_km2, unplanned: True, conflicts, warnings}
```

端点（下一步接）：
```
POST /map-imports/{id}/spatial-draft     # footprint + 可选 land_use → 空间草稿
  → 返回 {footprint_area_km2, land_use_summary, supply: 'unconfigured'|'configured', conflicts}
```

---

## 5. 分阶段

- **A（本次）**：`land_footprint` 校验器 + 单测（顶点/finite/范围/自交/跨日界/面积/重叠/稀疏）；文档。
- **B**：`spatial-draft` 端点 + 与 `build_town_input` 的接线（footprint 不进 area_km2；农田进）。
- **C**：UI 在地图上圈选多边形（缩放/连续坐标）、用地列表与冲突提示。
- **D**：把已声明用地接入粮食/人口只走既有规则，不新增经济算法。

## 6. 明确不做
不重构经营 tick、不改 `GRAIN_MIN_ARABLE_KM2`、不自动默认耕地、不把矿山当已勘探、
不把未规划区当荒地、不伪造精细地形、不需要用户为整张地图分区。
