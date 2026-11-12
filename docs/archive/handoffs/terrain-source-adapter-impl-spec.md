# terrain_source 实现规格（给实现代理）

> **实现任务书（2026-11-08 整理）**：目标文件已经存在。本文是当时交给实现代理的规格，不是现行地图架构。读取契约见 [world-map-source-contract.md](world-map-source-contract.md)。

目标文件：`app/terrain_source.py`、`tests/test_terrain_source.py`。只用 numpy + 标准库，Python 3.12。只读：不写盘、不联网、不 print，不 import Terragenesis。

## 常量与错误
- `WORLD_SEED = 20261020`，`NATIVE_SPACING_M = 30`
- 状态码（uint8）：`UNPREPARED=0`（目录无产品覆盖）、`OUT_OF_BOUNDS=1`（某产品范围外）、`UNKNOWN=2`、`OCEAN=3`、`CLOSED_BELOW_SEA=4`（内陆负高程，**不是海**）、`LAND=5`；`STATUS_NAMES` 码→小写名。
- `class TerrainSourceError(ValueError)`。

## 规范 JSON 与身份
- `_canon(obj) = json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False)`，哈希 `sha256(text.encode()).hexdigest()`。
- `_file_sha256(path)`：1 MiB 分块流式。
- JSON 读取拒绝重复键（object_pairs_hook 抛 TerrainSourceError）。

## native-terrain-v3：`load_native_terrain(path, *, expected_identity=None, verify_files=True)`
- path 为目录，含 `manifest.json`（utf-8）。
- 校验：`schema=='new-world-terrain-v3'`、`world_seed==20261020`、`spacing_m==30`、`sea_m==0`、`shape_zx` 两个正整数、`origin_native_xz` 两个 int（非 bool）、`files` 至少含 `bed_m, valid_mask, ocean_mask, unknown_mask, closed_below_sea_mask`（64 位十六进制）。
- 身份 = sha256(_canon(manifest 去掉 `identity` 与 `source_path`))，须等于 `manifest['identity']`；给了 expected_identity 也须相等。
- verify_files：5 个所用 `.npy` 文件哈希须匹配；其余 files 名（如 climate_base）不加载不校验，记入属性 `unverified_files`（排序列表）。
- `np.load(mmap_mode='r', allow_pickle=False)`；bed_m 须 float32 且形状 == shape_zx，掩膜为 bool 同形。缺文件 → TerrainSourceError。
- 网格：样点 (iz, ix) 在 x=(ox+ix)*30、z=(oz+iz)*30 米，**不加半格**。X 东 Z 南，数组 [z,x]。
- 分类：非 valid 或 unknown → UNKNOWN；ocean → OCEAN；closed → CLOSED_BELOW_SEA；否则 LAND。UNKNOWN 处高程 NaN。

## tectonic-macro-v2：`load_tectonic_product(path, *, expected_identity=None)`
- .npz，`np.load(allow_pickle=False)`；`manifest_json` 须是 0 维 unicode 数组，JSON 拒绝重复键。
- schema ∈ (`tectonic-frozen-product-v2`, `tectonic-frozen-product-v1`)；身份 = sha256(_canon(manifest 去掉 `identity`))。
- `config`：shape [nz,nx]、cell_size_m、origin_x_m、origin_z_m、world_seed==20261020；`coordinates['grid']` 以 `'cell centres'` 开头。
- 读 `final/elevation_m`（float64）与 `final/ocean_connected`（bool），各自 `sha256(arr.tobytes(order='C'))` 须等于 `manifest['arrays'][key]['sha256']`。
- 网格：x=origin_x_m+(ix+0.5)*cell，z 同理。源是周期平面，但本层按**有限域**处理，绝不 wrap。
- 分类：ocean_connected → OCEAN；elev<0 → CLOSED_BELOW_SEA；否则 LAND；无 UNKNOWN。

## 公共接口（基类 `_GridProduct`）
属性：kind、identity、path(str)、spacing_m(float)、first_xz_m（样点[0,0]坐标）、shape_zx、grid_semantics(str)。
- `extent_m` → (x_min, z_min, x_max, z_max)，为首末样点坐标（含端点）。
- `provenance()` → dict(kind, identity, path, spacing_m, first_sample_xz_m, shape_zx, grid_semantics, elevation_meaning, axes='X east, Z south; arrays [z,x]', length_unit='m', sea_level_m=0, world_seed=20261020, boundary='finite; no wrap')；native 另加 unverified_files。`elevation_meaning`：native 为 `'bed: terrain/river/lake bed, not water surface'`，tectonic 为 `'macro buoyancy surface elevation'`。本层没有湖面高程，不得把床面当水面。
- `sample(x_m, z_m)` → dict(elevation_m=float64 数组, status=uint8 数组, identity=str)。广播；非有限坐标 → TerrainSourceError。fx=(x-first_x)/spacing。fx<0 或 >nx-1（z 同理）→ OUT_OF_BOUNDS、NaN。内部：状态取最近样点（rint 后 clip）；高程为四邻双线性（上界 clip 到 n-1）；四邻任一 UNKNOWN → NaN + UNKNOWN。只取需要的元素，不把整幅数组读进内存。
- `crop(x0_m, z0_m, x1_m, z1_m, *, max_cells=16_777_216)`：半开框 [x0,x1)×[z0,z1)，要求 x1>x0、z1>z0 且有限。输出格对齐产品格，可越出产品：ix 从 ceil((x0-first_x)/s) 到 ceil((x1-first_x)/s)-1（z 同理）。格数 > max_cells → 错误。返回 dict(elevation_m=float32（非 LAND/OCEAN/CLOSED 处 NaN）, status=uint8（产品外 OUT_OF_BOUNDS）, first_sample_xz_m, spacing_m, shape_zx, complete=无 OUT_OF_BOUNDS, provenance=provenance())。只复制相交切片；返回的是拷贝。

## 坐标工具
- `native_index_to_m(ix, iz)` → (ix*30.0, iz*30.0)
- `m_to_native_index(x_m, z_m)` → (round(x/30), round(z/30)) 整数；偏离 30 m 格点超过 1e-6 m → TerrainSourceError。

## 目录
- `TerrainCatalog(products)`：按 spacing_m 升序（细在前，稳定排序）。`products` 属性（tuple），`provenance()` → list。
- `sample(x_m, z_m)` → dict(elevation_m, status, source=object 数组，元素为 identity 或 None)：逐点取第一个状态不为 OUT_OF_BOUNDS 的产品；都不覆盖 → UNPREPARED、NaN、None。
- `load_catalog(config_path)`：JSON `{"sources":[{"kind":"native-terrain-v3"|"tectonic-macro-v2","path":str,"identity":64hex}]}`；identity 必填；相对路径按配置文件目录解析；未知 kind → 错误。
- `load_default_catalog()`：读环境变量 `DREAM_TERRAIN_SOURCES`；未设置 → 空目录（没有默认数据依赖）。
- 提供 `__all__`。

## 测试（unittest，可被 pytest 运行；临时目录造小数组夹具，如 4×5）
1. native 正常加载；身份正确；改 source_path 不改身份；files 多出 climate_base 时 unverified_files 含它。
2. 篡改 manifest（加键）→ 身份不符；expected_identity 错 → 抛；manifest 重复键 → 抛。
3. manifest 写好后改 npy 字节 → verify_files 抛。
4. native sample：样点坐标返回精确值且 LAND；中点双线性；ocean/closed/unknown 状态（unknown 为 NaN）；超出末样点 → OUT_OF_BOUNDS；origin (-2,-2) 首样点 (-60,-60)。
5. native crop：全内部（形状、值等于切片、complete、first_sample_xz_m）；半开 [x0,x0+90) 恰 3 列；部分越界 complete=False 且外侧 OUT_OF_BOUNDS；max_cells 小 → 抛；改 crop 结果不影响再次采样。
6. tectonic：格(0,0)中心值等于 elev[0,0]；ocean/closed/land；不 wrap（首格心左侧 → OUT_OF_BOUNDS）；篡改数组哈希 → 抛。
7. 坐标工具（含偏格抛错）；非有限坐标抛错。
8. 目录：30 m native 落在 10 km tectonic 内 → 内部用 native、外部用 tectonic、两者外 UNPREPARED，source 正确；load_catalog 相对路径；缺 identity 抛；未设 DREAM_TERRAIN_SOURCES → 无产品（只移除该键）。
9. 可选真实样本：环境变量 `DREAM_TERRAIN_V3_FIXTURE` 指向目录时，按身份 `c751a09a6f02e8c336b6b9b8fb4b11b5dc67386e9a8470b0b1d90858bf1ffb72` 加载，检查 (4096,4096)、首样点 (-61440,-61440)、(0,0) 处高程有限；否则 skipTest。
