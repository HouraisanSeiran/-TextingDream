# 世界地图数据源契约（dream-map-source v1）

首版：2026-11-04；现状更新：2026-11-11。`app/map_source/` 已实现，玩家默认支持 `world_map_product`、civ-atlas 为 opt-in 旧来源。当前同源地形/环境/月气候/雪冰水文/独立洋流已接**现有作者世界地图**，接手入口见 [现世界地图接入交接](world-map-integration-handoff-20261111.md)。月数组登记读取由 `app/map_bundle.py` 单独负责，不塞入二维 MapCatalog，也不自动换玩家默认/故事/saves。

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
- 玩家运行地图已默认支持 `world_map_product`（`map_policy.py/play_map_world.py`），civ-atlas 接口保留为 opt-in 旧来源。2026-11-11 同源登记链只改作者现世界地图，玩家依原 play-map 与服务端 fog，不自动迁移默认或存档。

## 9. 未决事项

- 原首版“尚无世界产品 / TD方案待确认 / 气候词表待产品”的状态已被实际冻结产品取代，见第11–13节；第6节保留格式契约。
- 待办仍包括潜在湖的常年水量验证、全域动态冰川/长期自然气候与海洋收敛、天气/旅行/文明的显式消费，不从读取接通推断它们已完成。

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

## 11. 山地、原生冰川与地表排水派生产品（2026-11-11）

通用格式已存在实际冻结产品，不再仅限合成夹具：`artifacts/mountain-glacier-hydrology-20261111/world/`，身份见其manifest。本次原生冰川字段沿用 `glacier_ice_thickness_m`（m）、`glacier_ice_surface_m`（m）、`glacier_ice_volume_m3`（m3 ice）、`glacier_coverage_fraction`（1）。新增标准词 `glacier_simulated_fraction`（1）：0为未模拟、不是确认无冰；域外H/surface/volume/coverage为NaN。

`elevation_m`保持地形床；额外`routing_surface_m`为床+原生H（模拟区内）/床（域外），`hydro_bed_m`仅几何排水切槽，不回写地形与冰库存。新增 `glacier_melt_mean_m3_s`（m3/s）只表示所有声明区域共同物理时窗的累计融水沿最终receiver累积后的平均分量，不是总径流或某年流量。源时间和未模拟区限制须随metadata透传；pending与累计融水不可相加，诊断图层不执行native库存交接扣账。

原生冰川为工程生成线供雪的固定床有界2D SIA，不冒称实际气候/冰蚀/冰下排水。新water_surface仅发布原始排水表面可容水的同水位连通子域，湖位仍潜在填洼面、非永久湖。通用适配器加载身份/图层/矢量，忽略的非标准receiver等额外层不据此自动宣称已验证；本次发布与独立验收另行核对80万receiver无环与湖面不埋床。

玩家现已默认支持world_map_product（app/map_policy.py与play_map_world.py），本文旧章节中“仅civ-atlas”的历史状态不能用来否认当前接线；本次新产品只做独立读取/裁片/底图试读，不自动改故事包或默认。

## 12. 独立气候年与环境派生读取（2026-11-11）

本批真实链另存 `artifacts/world-climate-integration-20261111/`，不改原 `mountain-glacier-hydrology-20261111/world/`：已选 `climate-dry-continuous-year` → `hydrology-dry-continuous-year` → `environment-world`，身份分别 `70d36369…ae4c`、`61783b0a…e129`、`9fda7cc8…f0c1`，全身份见各manifest与本批README。用户20:52接受的是连续纬度季节项+原k=1e-5的极干旱工程情景，不是气候自然度标定或完整TG二阶段认证。

- `SavedClimateMap(source_map, climate_product, expected_source_identity=…, expected_climate_identity=…)` 校验同源床面/海陆/receiver/order/格网/seed/config/reference与产品身份，支持只读 `query(fields, months=…, window=…)` 与 `point`；月为1–12，窗口为半开 `[z0,x0,z1,x1]`。`SavedClimateHydrology` 另绑定水文身份并提供同样的月/窗口读取，不隐式重算缺失月。
- 气候由200×250/40km共同母场映射到800×1000/10km产品；这是粗气候强迫映射，不是10km独立大气求解或TD30m产品。日历noleap365，月深mm/month、月路由体积m3/month、月Q m3/s；年Q严格以月体积和除365日秒数。
- 两有限冰区本年动态H实际求解，旧H仅初值；逐月雨/融雪/融冰m3水换为mm后**替换**当地液水入口，不能再加P、旧累计融水或pending。区外雪冰是逐格非动态诊断。旧20年高度供雪与本次气候年为不同情景，不伪装旧native时间续算。
- `environment-world`仍为`world-map-product-v1`。`temperature_c/precipitation_mm_yr/biome`来自已存气候，biome保留原生整数ID；`discharge_m3_s`为本年体积积分栅格Q。末态`soil_water_mm/snow_swe_mm/year_end_ice_swe_mm`不是月通量；本批末态词 `soil_water_mm`（mm）、`snow_swe_mm`（mm）、`year_end_ice_swe_mm`（mm）及保留冰体积词 `glacier_ice_volume_m3`（m3）均按实际manifest声明，不能混为库存新增或月通量。`year_end_ice_swe_mm`区外可含逐格非动态冰库存，不能转换成全域动态冰川H；`glacier_simulated_fraction=0`为未动态模拟而非无冰，动态H域外NaN。
- 原床/status/saved receiver及河湖矢量字节不变，`routing_surface_m/hydro_bed_m`继承旧几何，非本年冰面；潜在湖没有蓄水/调洪/延迟动力。栅格Q未绑定每条河矢量，现有矢量显示仍是面积符号宽，不推断物理河宽。潜在群系不是真实森林库存。
- `climate_world_stage.prepare(..., recover=True)`仅已完成品只读恢复，不能称中断月续算/多年耦合restart；本批未接故事默认、saves或正式restart链，未提交。真实独立读取/发布通过不等于atlas最终出图或玩家默认已经采用。

实际年链的同源身份、月窗口逐位、年Q积分、原生biome ID、床/receiver/矢量不变见 `environment-validation.json`。闭边水汽/单格迎风集中和未标定强迫限制须随来源保留；历史候选目录与源码批准修订不得覆盖。最终自然图`atlas-final/simple-atlas.png`与`topics/`三专题已实际出图并主看图；atlas实际保存群系/年末雪/新动态H逐格消费核对通过，分类最近邻、RGB柔化仅显示。身份与时间见atlas-source.json/topic-source.json，联合验收见joint-acceptance.json，不等于玩家默认或天气玩法自动改接。

## 13. 现世界地图同源登记读取（2026-11-11）

现有作者 `native-map-host` 已通过 `app/map_bundle.py` + `map_bundle_routes.py` 读取 `config/map-bundles.json` 中 `terragenesis-world-20261111`；不新增页面或多包浏览入口。地形/环境/气候/水文10km产品与独立40km海洋，暴露 detail、米制point、格索引半开window、全12月数组、已存preview及分页vectors；`order`与海洋face拓扑形状非格中心场，登记为descriptor-only不可query。点检最近保存格无插值，不改变本文底层MapSource原有采样契约。完整路径/身份/字段/时间/API/维护/验收见 [接入交接](world-map-integration-handoff-20261111.md)。

线上只读已冻结源并核身份/格网/receiver/时间/文件变化，不触发生成、numba planner或TG子进程。历史H20不混入当前月水文，route geometry仍旧冻结几何；湖为potential/unvalidated而非permanent，约9.6%陆地潜在面问题尚未修复；气候仍极干工程年、洋流为未长期收敛首年且1月带初始化。PNG地理框可点，三专题panel不可点，洋流图/路线仅1/7月，其余月不伪造。

本次只改变作者世界地图消费；player卸载作者全图，继续原play-map/fog，未改默认故事、saves或restart，也未自动接天气/道路/文明。Node UI、真实HTTP/Edge及主31项新旧地图回归已过；5组字段/8类图、点窗月查询、透明配准和player隔离证据在artifacts/map-integration-20261111/，详情见交接第8节。不以旧生成验证代替前端验收；用户在用服务未重启，新后端需下一次正常启动加载。
