# 世界地图数据源契约（dream-map-source v1）

日期：2026-11-04。状态：草案，随适配层实现同步定稿。代码入口：`app/map_source/`（实现中）。

## 1. 目的

织梦的地图（渲染、点选、旅行、选址）只通过一个统一接口读取地形和水系，不直接读任何生产方的文件格式。Terragenesis 还会继续更新产品；更新时只需新增或修改**适配器**，消费者代码不动。

适用范围：世界总览、区域图、局部故事区的高程、海陆分类、水面、汇水、河湖矢量，以及之后的气候和群系。城镇、道路、地名属于织梦玩法数据，不在本契约内。

## 2. 分层

```text
生产方（Terragenesis / 织梦内的生成器）
   ↓ 冻结产品：manifest + 数组 + 矢量，带身份
适配器（按 kind + schema 选择，每个只认它声明的版本）
   ↓ 统一接口 MapSource
目录 MapCatalog（多源、细源优先）
   ↓
消费者：app/map_render.py、world_relief/atlas.py、之后的运行地图 API 与玩法
```

规则：消费者只依赖 `MapSource` / `MapCatalog`；不得 import 某个适配器，也不得读产品文件。

## 3. 统一接口

### 3.1 来源信息 `SourceInfo`

| 字段 | 含义 |
| --- | --- |
| `kind`, `schema` | 适配器种类与产品 schema 原文 |
| `identity` | 本产品不可变身份（64 位十六进制），适配器加载时复算 |
| `lineage` | 上游来源身份列表，如板块骨架身份 |
| `producer` | 生产方与算法版本（如 `terragenesis/plate-td`、`dream/world-relief-pilot-2.0`） |
| `world_seed`, `subseeds` | 从 manifest **读取**，不由适配器硬编码 |
| `extent_m`, `spacing_m`, `first_sample_xz_m`, `shape_zx` | 格网；坐标 X 东、Z 南、米，数组 `[z,x]` |
| `grid_semantics` | `cell-centre` 或 `native-sample`（不加半格）等，原文保留 |
| `boundary` | 一律有限域、不环绕 |
| `layers` | 本产品实际提供的图层名列表（见 3.2） |
| `vectors` | 本产品提供的矢量种类（`rivers`、`lakes`），没有则为空 |
| `declared_generated`, `limitations` | 生产方声明的生成内容与局限，原样透传 |

### 3.2 标准图层词表

| 图层 | 类型 / 单位 | 含义 | 必需 |
| --- | --- | --- | --- |
| `status` | uint8 | 见 3.3 | 是 |
| `elevation_m` | float, m | 地表或床面高程；含义由 `elevation_meaning` 声明（床面 ≠ 水面） | 是 |
| `water_surface_m` | float, m | 湖、河、填洼水面；无水处 NaN | 否 |
| `drainage_area_m2` | float, m² | 汇水面积；**不是流量** | 否 |
| `discharge_m3_s` | float, m³/s | 代表流量，须声明情景 | 否 |
| `temperature_c`、`precipitation_mm_yr`、`biome` | — | 气候与群系，须声明来源与近似程度 | 否 |

请求产品没有的图层时抛 `MissingLayerError`，不返回 0 或 NaN 冒充。新增图层先加入本表再实现。

### 3.3 状态码（与现有 `app/terrain_source.py` 一致，不改编号）

`0 unprepared` · `1 out_of_bounds` · `2 unknown` · `3 ocean` · `4 closed_below_sea`（内陆负高程，不是海） · `5 land`。

海陆一律以 `status` 为准，不用 `elevation < 0` 判海。

### 3.4 查询方法

- `sample(x_m, z_m, layers=("elevation_m", "status"))`：广播点查询。高程双线性、分类最近样点；越界返回 `out_of_bounds` 与 NaN。
- `crop(x0, z0, x1, z1, layers=..., max_cells=...)`：半开矩形，输出对齐产品格；超出产品部分标 `out_of_bounds`；返回拷贝和 `SourceInfo`。
- `vectors(kind)`：返回矢量对象列表；每个对象有稳定 `id`、米制坐标折线或多边形、上下游关系（河）或出口与水面（湖），以及带单位的数值属性。
- 所有查询只读已冻结产品，**不触发生成**。

### 3.5 目录 `MapCatalog`

- 由配置文件或环境变量 `DREAM_TERRAIN_SOURCES` 加载；配置每项必须给 `kind`、`path`、`identity`，可选 `expected_world_seed`。
- 按格距从细到粗；逐点取第一个覆盖该点的产品。细源为 `unknown` 时不退回粗源。
- 同一点的所有图层取自**同一个产品**，不跨源拼图层；返回结果附带每点来源身份。
- 未配置时目录为空，查询一律 `unprepared`。

## 4. 适配器规则

1. 注册键为 `(kind, schema)`；未知 kind 或 schema 明确拒绝并报出原文，不尝试“差不多能读”。
2. 加载即校验：manifest 身份复算、所用文件或数组哈希、形状与 dtype、坐标语义。任一不符拒绝加载。
3. 种子：读取并记录 manifest 中的 `world_seed`；配置给了 `expected_world_seed` 时才比对。不再写死 20261020。
4. 不修改数据：适配器只做格式转换（重命名、状态码映射、单位声明），不平滑、不插值改形、不补洞。确需派生（如由掩膜合成 `status`）时写入 `SourceInfo` 说明。
5. 每个适配器必须通过同一套契约测试（`tests/test_map_source_contract.py`）：身份篡改被拒、越界、未知不回退、缺图层报错、坐标首样点与相邻样点、只读不可写、矢量 ID 唯一。真实产品测试用环境变量指定，可跳过。

## 5. 现有产品与适配器

| kind | schema | 生产方 | 提供图层 | 矢量 |
| --- | --- | --- | --- | --- |
| `native-terrain-v3` | `new-world-terrain-v3` | Terragenesis 一阶段 30 m | status、elevation_m（床面） | 无（河湖产品待接） |
| `tectonic-macro-v2` | `tectonic-frozen-product-v2`、`tectonic-frozen-product-v1` | Terragenesis 板块骨架 | status、elevation_m（浮力代理，**不是地表**） | 无 |
| `world-relief-pilot` | `world-relief-pilot-1.0`、`world-relief-pilot-2.0` | 织梦 `app/world_relief/` | status、elevation_m、water_surface_m（潜在填洼面，干地 NaN）、drainage_area_m2 | rivers（转为 rivers-v1） |
| `world-map-product` | `world-map-product-v1` | Terragenesis 将来的世界产品（见第 6 节） | 按 manifest 声明 | 按 manifest 声明 |
| `world-map-product` | `td-world-960m-v1` | Terragenesis（织梦侧接入）的 TD 潜空间低频世界层；约 240 m 米制高程 4×4 平均到 960 m，非 30 m 解码平均 | status、elevation_m、water_surface_m（潜在填洼面）、drainage_area_m2（非流量） | rivers-v1、lakes-v1（潜在填洼面轮廓） |

`td-world-960m-v1` 复用第 6 节的层和矢量契约及严格适配器；条件可在骨架边界外周期取样，但成品查询仍有限域、不环绕。状态 4 仅限非海洋负高程，海平面以上潜在湖面不映射为负高程闭洼。生成、填洼水面与粗算河湖在 manifest 中分别声明，不据汇水面积推断真实流量。

`tectonic-macro-v2` 只供诊断和骨架定位，不应作为世界总览底图。

## 6. 给 Terragenesis 的产品格式建议：`world-map-product-v1`

Terragenesis 以后发布世界级或区域级地图产品时，建议直接输出此格式，织梦用一个通用适配器读取，无需逐个新写适配器。

目录结构：

```text
<product>/
  manifest.json
  layers/<图层名>.npy      # 每层一个文件，[z,x]，C 顺序
  vectors/rivers.json      # 可选
  vectors/lakes.json       # 可选
```

`manifest.json` 必需字段：

| 字段 | 说明 |
| --- | --- |
| `schema` | 固定 `world-map-product-v1` |
| `producer`, `algorithm_version` | 生产方与算法版本 |
| `identity` | 去掉 `identity` 与 `source_path` 后，规范 JSON（排序键、紧凑分隔符、禁 NaN）的 SHA-256 |
| `lineage` | 上游产品身份列表 |
| `world_seed`, `subseed_method`, `subseeds` | 种子与派生方法、实际值 |
| `grid` | `{first_sample_xz_m, spacing_m, shape_zx, semantics: "cell-centre"\|"native-sample", axes: "X east, Z south; arrays [z,x]", length_unit: "m", sea_level_m: 0}` |
| `layers` | `{名称: {file, sha256, dtype, unit, meaning, nodata}}`，名称取自 3.2 词表 |
| `status_codes` | 产品自身分类到 3.3 状态码的映射；或直接提供 `status` 层 |
| `vectors` | `{rivers|lakes: {file, sha256, schema}}` |
| `declared_generated`, `limitations` | 生成内容与局限 |
| `ready` | `true` 才可消费；未完成产品不得被加载 |

矢量 `rivers.json`：`{"schema": "rivers-v1", "lines": [{"id", "points_xz_m": [[x,z],...], "downstream_id", "upstream_ids", "drainage_area_m2", "discharge_m3_s"?, "outlet": "ocean"|"lake"|"closed"|"edge"}]}`。`lakes.json`：`{"schema": "lakes-v1", "lakes": [{"id", "ring_xz_m", "surface_m", "outlet_river_id"?}]}`。ID 必须稳定、不使用局部临时编号。

## 7. 版本演进

- **兼容变更**（新增可选字段、新增图层）：同一 schema 版本内允许，适配器忽略未知字段。
- **不兼容变更**（字段改名、单位或含义改变、坐标语义改变）：生产方必须升 schema 版本，织梦新增适配器；旧适配器在仍有存档或测试夹具使用时保留。
- 适配器在 `SUPPORTED_SCHEMAS` 中显式列出版本；新版本未登记前一律拒绝。
- 每次新增适配器同时更新第 5 节表格与契约测试。

## 8. 迁移

- `app/terrain_source.py` 的公开函数与状态码保留，现有调用方（`map_render.py`、样图 CLI、测试）不需改动；新接口内部复用它的加载与校验代码。
- `app/world_relief/atlas.py` 目前自带产品加载函数，成图交付后迁移到 `MapCatalog`。
- `app/play_map.py` 等运行地图仍只接 civ-atlas；接入 `MapCatalog` 属于下一步，civ-atlas 接口保留为可选旧来源。

## 9. 未决事项

- Terragenesis 尚无世界级地图产品；第 6 节为建议格式，需对方确认后定稿。
- 基于 Terrain Diffusion 的世界地形方案（S0–S3）待用户确认，其产物将按第 6 节格式在织梦侧冻结。
- 气候、群系图层词表的具体字段待有产品后补充。

## 10. 实现状态

2026-11-04：已实现 `app/map_source/`；消费方从包入口导入 `MapSource`、`SourceInfo`、`MapCatalog`、`load_source`、`load_catalog`、`load_default_catalog`。`SUPPORTED_SCHEMAS` 与 `register_adapter(kind, schema, loader)` 提供显式版本登记。未修改渲染器、运行地图 API 或既有 atlas 加载器。

```python
from app.map_source import load_source, MapCatalog
source = load_source("world-relief-pilot", "artifacts/world-relief-pilot-v2")
result = MapCatalog([source]).sample(0, 0)
crop = source.crop(-1000, -1000, 1000, 1000)
# source.info 为 SourceInfo；sample 返回只读数组，crop 返回可写拷贝。
```

配置文件为 `{"sources": [{"kind": "...", "path": "...", "identity": "64位十六进制", "expected_world_seed": 20260903}]}`；相对路径相对于配置文件目录。环境变量 `DREAM_TERRAIN_SOURCES` 指向该文件。`expected_world_seed` 可省略；旧 `terrain_source` 的加载函数签名与 `WORLD_SEED` 常量保留，但实际种子来自产品，旧目录也支持可选期望种子。

验收命令（PowerShell，在织梦目录执行）：

```powershell
Remove-Item Env:DREAM_TERRAIN_V3_FIXTURE -ErrorAction SilentlyContinue
& .venv/Scripts/python.exe -m pytest tests/test_map_source_contract.py tests/test_terrain_source.py tests/test_map_render.py -p no:cacheprovider
$env:DREAM_TERRAIN_V3_FIXTURE = 'D:\codexwork\山川形意Terragenesis\.scratch\river-upgrade-20261101\terrain-v3'
& .venv/Scripts/python.exe -m pytest tests/test_map_source_contract.py tests/test_terrain_source.py tests/test_map_render.py -p no:cacheprovider
```

`DREAM_WORLD_RELIEF_V2_FIXTURE` 可指定真实试点目录；未设置时测试使用仓库内 `artifacts/world-relief-pilot-v2`，目录不存在则跳过。测试只读产品，不生成地形，不使用 GPU。

实现细节与已知局限：

- 范围沿用旧加载器的首样点至末样点闭区间；crop 采用格点对齐的半开矩形。高程双线性，分类最近样点；有非零插值权重的未知床面令高程 NaN，但状态仍由最近样点决定。旧 `terrain_source.sample` 的未知邻域行为保持不变。
- 可选图层当前最近样点采样，包括水面，避免跨干地插值产生虚构水面。该选择记录于适配器说明；缺图层直接抛 `MissingLayerError`，不跨来源补图层。目录只提供多源点查询与来源信息，crop/vectors 由选定的 `MapSource` 提供；多源裁片的目标格网尚未定义。
- 试点 status 由 ocean_mask 优先映射 3、inland_depression_mask 映射 4、其他 5。试点闭洼掩膜也含海平面以上洼地，状态 4 在该来源中并不保证负高程。水面限非海洋且 `lake_surface_m > elevation_m` 或闭洼掩膜的格点；是 priority-flood 潜在填洼面，不代表永久有水或已完成水量平衡。不推测海面或河道水深。
- 试点河线保留原始稳定 ID、坐标、上下游关系；`outlet_area_km2 * 1e6` 为 `drainage_area_m2`，另保留 `head_drainage_area_m2`。终端点依海洋掩膜、边界、潜在湖面、内部闭合判断 ocean/edge/lake/closed，并向上游传播；不据此声称真实流量或永久湖出口。
- 通用格式目前只有合成夹具。`status_codes` 采用源整数编码字符串到标准整数编码的字典，仍要求 `layers.status` 指定分类数组文件；仅映射而无数组位置不足以加载。标准直存 status 必须 uint8；高程和其他连续图层为浮点，biome 为整数分类。单位字符串采用 `STANDARD_LAYERS` 的 `m`、`m2`、`m3/s`、`degC`、`mm/yr`、`1`，不隐式换算。流量要求图层 metadata 的 scenario；气候/群系要求 source 与 approximation。未知新增字段/图层不暴露为标准图层，不影响已登记字段读取。
- 加载只校验实际消费文件；试点 PNG、初始高程、receiver 等不读取也不宣称已校验。未 import Terragenesis 代码。来源自身的 declared_generated/limitations 原样透传，适配派生规则另列在 SourceInfo.derivations。
